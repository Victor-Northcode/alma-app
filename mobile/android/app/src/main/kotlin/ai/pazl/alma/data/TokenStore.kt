package ai.pazl.alma.data

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import android.util.Log
import java.security.KeyStore
import java.util.concurrent.atomic.AtomicReference
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Where the bearer token lives.
 *
 * The token **is** the account. It is minted on the first request the app makes,
 * before anybody has signed in — that is what lets the whole funnel run without
 * a registration wall — and everything the person then does, including anything
 * they buy, hangs off it. Whoever holds it is them.
 *
 * So it is encrypted with a key that lives in the platform keystore and, on
 * every device shipped in the last several years, inside a secure element that
 * the key material never leaves. What is written to disk is `IV ‖ ciphertext`,
 * base64, in an ordinary preferences file. Reading that file — with root, with
 * a stolen backup, with a forensic image — yields nothing without the device
 * itself.
 *
 * ## Why not `EncryptedSharedPreferences`
 *
 * It was the obvious choice and it is what this file used first. It is
 * **deprecated** as of `androidx.security:security-crypto:1.1.0`: Jetpack
 * Security is no longer developed, the class is marked `@Deprecated` in the
 * release it stabilised in, and it drags Tink in behind it. Shipping a
 * credential store that is already end-of-life, and eleven deprecation warnings
 * on every build that teach the team to stop reading warnings, was the worse
 * trade. What it did for us is thirty lines of `Cipher` — this file — against
 * the same `AndroidKeyStore` primitive it was calling itself.
 *
 * ## The in-memory cache is not an optimisation
 *
 * Every outgoing request reads the token from an OkHttp interceptor running on
 * a network thread. A keystore-backed decrypt is on the order of a millisecond
 * but it *can* block, and doing it per request would put a secure-element round
 * trip in the hot path of a chat stream. [cached] is therefore the read path,
 * the file is the durable copy, and the file is only ever read once — at
 * construction.
 *
 * ## Failure
 *
 * A keystore that will not open must not stop the app working, and this does
 * happen: removing the device lock screen invalidates keys, and some OEM
 * keystores throw from inside their own provider. The fallback is memory-only,
 * which costs the person their guest session when the process dies and is
 * survivable. Crashing at launch is not.
 */
class TokenStore(context: Context) {

    private val prefs: SharedPreferences =
        context.applicationContext.getSharedPreferences(FILE, Context.MODE_PRIVATE)

    /** Null when the keystore refused. Everything degrades to memory-only from there. */
    private val key: SecretKey? = loadOrCreateKey()

    private val cached = AtomicReference<String?>(readFromDisk())

    /** The current token, or null before the first response has been seen. */
    val token: String?
        get() = cached.get()

    /**
     * Remember a token the server just issued.
     *
     * Called from the interceptor for **every** response that carries the
     * header, not only from sign-in. That is what makes the guest account real
     * from the first request — whichever request happens to be first — and it is
     * also how a refreshed token replaces an old one without anything else in
     * the app needing to know.
     */
    fun save(value: String) {
        if (value.isBlank() || value == cached.get()) return
        cached.set(value)

        val sealed = encrypt(value)
        if (sealed == null) {
            // Better to hold nothing than to hold a token in the clear. The
            // session lasts until the process dies, which is a bad day rather
            // than a leaked credential.
            prefs.edit().remove(KEY).apply()
            return
        }
        prefs.edit().putString(KEY, sealed).apply()
    }

    /**
     * Forget it.
     *
     * Two callers: signing out, and a 410 from the server saying the account
     * behind this token no longer exists. Holding on to a dead token would make
     * every later request fail identically, which reads as a broken app rather
     * than as a deleted account.
     */
    fun clear() {
        cached.set(null)
        prefs.edit().remove(KEY).apply()
    }

    /* ── the keystore ──────────────────────────────────────────────────── */

    private fun loadOrCreateKey(): SecretKey? = try {
        val store = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (store.getEntry(ALIAS, null) as? KeyStore.SecretKeyEntry)?.secretKey ?: generateKey()
    } catch (error: Exception) {
        // Deliberately broad. This throws GeneralSecurityException, IOException
        // and — on more than one OEM build — an IllegalStateException from
        // inside the provider. Catching them individually would still miss the
        // next one, and every one of them means the same thing here.
        Log.w(TAG, "no keystore; this session will not survive the process", error)
        null
    }

    private fun generateKey(): SecretKey {
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                // No `setUserAuthenticationRequired`. The token has to be
                // readable by a background refresh and by the OkHttp
                // interceptor, neither of which can put a fingerprint prompt on
                // screen — and a product whose first minute needs no account
                // cannot demand a biometric to keep one.
                .build()
        )
        return generator.generateKey()
    }

    private fun encrypt(value: String): String? {
        val secret = key ?: return null
        return try {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.ENCRYPT_MODE, secret)
            // The IV is generated by the keystore and must be stored with the
            // ciphertext. Reusing one under GCM with the same key is the
            // catastrophic failure mode of this cipher, which is exactly why it
            // is never chosen here.
            val sealed = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
            Base64.encodeToString(cipher.iv + sealed, Base64.NO_WRAP)
        } catch (error: Exception) {
            Log.w(TAG, "could not seal the token", error)
            null
        }
    }

    private fun readFromDisk(): String? {
        val secret = key ?: return null
        val stored = prefs.getString(KEY, null) ?: return null
        return try {
            val bytes = Base64.decode(stored, Base64.NO_WRAP)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(
                Cipher.DECRYPT_MODE,
                secret,
                GCMParameterSpec(TAG_BITS, bytes, 0, IV_BYTES),
            )
            String(cipher.doFinal(bytes, IV_BYTES, bytes.size - IV_BYTES), Charsets.UTF_8)
        } catch (error: Exception) {
            // The key was rotated or invalidated — removing a lock screen does
            // this — so the stored bytes can never be read again. Drop them
            // rather than failing every launch from here on; the person signs
            // in again, or gets a fresh guest account, and the account itself
            // is untouched on the server.
            Log.w(TAG, "stored token could not be opened; discarding it", error)
            prefs.edit().remove(KEY).apply()
            null
        }
    }

    private companion object {
        const val TAG = "TokenStore"
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val ALIAS = "alma.session.v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val FILE = "alma.session"
        const val KEY = "token"

        /** GCM's nonce is 12 bytes and the keystore always emits exactly that. */
        const val IV_BYTES = 12
        const val TAG_BITS = 128
    }
}
