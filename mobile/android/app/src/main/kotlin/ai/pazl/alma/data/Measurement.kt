package ai.pazl.alma.data

import android.content.Context
import android.content.SharedPreferences
import java.util.UUID
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Whether this device reports which step of the funnel it reached, and — while
 * it does — which installation it is.
 *
 * ## Why there is a switch at all
 *
 * Not because the payload is dangerous. It is a stage word from a closed set
 * (`landing_view`, `quiz_start`, …) plus a product slug — no IP, no user agent,
 * no device id, no free text — and it goes to our own backend and nowhere else.
 * There is no analytics SDK in this app, no crash reporter, and no
 * `AD_ID` permission.
 *
 * The switch exists because the privacy policy the app links to promises one:
 * *"If your browser sends Do Not Track or Global Privacy Control, the step
 * labels are not recorded at all."* That carve-out is implemented in
 * `src/lib/track.ts` and had no Android equivalent, which left the app offering
 * an opt-out that did not exist on the platform the reader was holding — and
 * forced the Data safety form to declare App interactions as *Required* rather
 * than *Optional* purely because the toggle was missing.
 *
 * ## Why it lives in `data` and not in `core`
 *
 * Because [AlmaClient] is what has to check it, and `data` may not depend on
 * `core`. It is deliberately not part of [TokenStore]: that file is a keystore
 * round-trip for a bearer credential, and a preference about measurement is not
 * a secret. Plain [SharedPreferences] is the honest storage for it.
 *
 * ## Default
 *
 * On. The web records the same stages for everyone who has not asked otherwise,
 * and a measurement that is off by default is a measurement nobody has — which
 * would make the two platforms' funnels incomparable for a reason that has
 * nothing to do with the product.
 *
 * ## The installation id, and why it lives behind the same switch
 *
 * Launching the app used to mint an account: `SessionHolder.start()` called
 * `GET /v1/auth/session`, which mints, so every install *was* an account before
 * anybody had typed anything. The account is created by an act now — a birth
 * saved, a sign-in, a verified purchase — which leaves the question the funnel
 * cannot do without, *of the people who opened the app, how many finished the
 * journey*, with nothing to answer it. [anonId] is the answer: a random string
 * this install keeps, sent as `X-Alma-Anon`, that is not an account and grants
 * nothing.
 *
 * It is **created only while the switch is on**, which is the whole reason it is
 * in this class rather than beside the token. This mirrors `src/lib/track.ts`,
 * where `ensureAnonId` sits behind the Do Not Track and GPC check so that a
 * person who opted out gets no identifier written to their storage at all
 * rather than one created and then politely unused. It is also the condition
 * Google's Data safety form requires before *Device or other IDs* may be
 * declared Optional: turning the switch off has to prevent the collection, not
 * merely stop the sending. Turning it off therefore forgets the id as well.
 *
 * ## And it expires
 *
 * The privacy page promises that the step labels *and the id* are deleted after
 * [RETENTION_DAYS], and an identifier with no end that is eventually joined to a
 * person is the one thing that page exists to promise we do not keep. The
 * server purges its rows on that schedule; this is the other half.
 */
class Measurement(context: Context) {

    private val prefs: SharedPreferences =
        context.applicationContext.getSharedPreferences(FILE, Context.MODE_PRIVATE)

    private val _enabled = MutableStateFlow(prefs.getBoolean(KEY, true))

    /** Observed by the settings screen; read by [AlmaClient] before every beacon. */
    val enabled: StateFlow<Boolean> = _enabled.asStateFlow()

    /**
     * Read once, at construction, and kept in memory thereafter.
     *
     * The same reasoning [TokenStore] gives for its own cache: this is read from
     * an OkHttp interceptor on a network thread, for every request, and a disk
     * read per request in the hot path of a chat stream is a cost paid for
     * nothing. The file stays the durable copy.
     */
    private val cachedId = AtomicReference(readStoredId())

    fun set(on: Boolean) {
        // Written before the flow is updated, so a process killed between the
        // two lines comes back with the setting the person chose rather than
        // with the one they turned off.
        prefs.edit().putBoolean(KEY, on).apply()
        _enabled.value = on
        // Switching off forgets the id rather than merely stopping its use. An
        // identifier kept "just in case" is an identifier collected, and the
        // Data safety declaration says it is not.
        if (!on) forgetInstallation()
    }

    /**
     * Which installation this is, or null when nobody may be measured.
     *
     * Minted on demand rather than at first launch, which comes to the same
     * thing — the first request the app makes is the first caller — while
     * keeping the mint behind the switch instead of beside it.
     */
    fun anonId(): String? {
        if (!_enabled.value) return null
        cachedId.get()?.let { if (!spent()) return it }
        return mint()
    }

    /**
     * Forget it.
     *
     * Two callers, and they are the two that clear the token: a 410 saying the
     * account behind it is gone, and deleting the account from Settings. The id
     * is the string that account's pre-account funnel rows are keyed to, so a
     * device that kept it would carry an identifier belonging to somebody who
     * asked to be erased straight into the next account it makes — and the
     * server would refuse the claim, because the id is already spoken for by a
     * row that no longer exists.
     */
    fun forgetInstallation() {
        cachedId.set(null)
        prefs.edit().remove(ID_KEY).remove(MINTED_KEY).apply()
    }

    @Synchronized
    private fun mint(): String {
        // Re-checked under the lock: two requests racing at first launch would
        // otherwise write two ids for one install, which is one person arriving
        // twice at the top of the funnel.
        cachedId.get()?.let { if (!spent()) return it }
        val minted = UUID.randomUUID().toString()
        cachedId.set(minted)
        prefs.edit()
            .putString(ID_KEY, minted)
            .putLong(MINTED_KEY, System.currentTimeMillis())
            .apply()
        return minted
    }

    /**
     * Whether the stored id has outlived the retention the product promises.
     *
     * A missing timestamp counts as spent, which is the direction that fails
     * safe: an id whose age cannot be established is one whose age might be
     * anything, and re-minting costs one install's joined visit while keeping it
     * costs the sentence on the privacy page.
     */
    private fun spent(): Boolean {
        val minted = prefs.getLong(MINTED_KEY, 0L)
        if (minted <= 0L) return true
        return System.currentTimeMillis() - minted >= RETENTION_DAYS * 24L * 60 * 60 * 1000
    }

    private fun readStoredId(): String? = prefs.getString(ID_KEY, null)?.takeIf { it.isNotBlank() }

    companion object {
        /**
         * How long one installation id lives, in days.
         *
         * The same number as `PURGE_AFTER_DAYS` in `backend/alma/funnel.py` and
         * `FUNNEL_RETENTION_DAYS` in `src/lib/legal.ts`, which is the number the
         * privacy page prints. It is a fourth copy of one fact, so
         * `src/lib/legal-truth.test.ts` reads this line and fails if it ever
         * disagrees with the other three.
         */
        const val RETENTION_DAYS = 180

        private const val FILE = "alma.prefs"
        private const val KEY = "measurement"

        /**
         * The same key the web uses in local storage and iOS uses in
         * `UserDefaults`. One name for one idea across the three clients, so
         * that a person reading the privacy page — which names it — finds the
         * same word wherever they look.
         */
        private const val ID_KEY = "alma.anon"
        private const val MINTED_KEY = "alma.anon.minted"
    }
}
