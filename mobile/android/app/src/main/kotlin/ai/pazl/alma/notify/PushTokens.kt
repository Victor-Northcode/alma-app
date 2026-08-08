package ai.pazl.alma.notify

/**
 * Where an Android push token comes from.
 *
 * ## Why this is an interface with no Firebase in it
 *
 * On Android there is no alternative to FCM — Google Play services is the only
 * path to a device that is asleep, and `docs/PUSH.md §2.1` says so plainly. So
 * this interface has exactly one real implementation ahead of it and would
 * ordinarily be over-engineering. It exists because **adding the dependency
 * today would be wrong in three separate ways**, and all three are somebody
 * else's decision to make:
 *
 * 1. **The package name is not settled.** `STATUS.md §4②` records that the
 *    product-id prefix is unchosen — `alma.` versus `ai.pazl.alma.` — and
 *    `google-services.json` is pinned to a package name. A Firebase project
 *    created under a name that is about to change has to be recreated, and the
 *    old sender id keeps working just long enough to be confusing.
 * 2. **The build would stop working for everybody.** The `google-services`
 *    Gradle plugin fails the build outright without a `google-services.json`,
 *    and that file cannot be committed to this repository or invented.
 * 3. **Two store disclosures would become false the day it lands.**
 *    `DATA-INVENTORY §4` currently says the only Google dependency we ask for
 *    is Play Billing; `firebase-messaging` breaks that, and it brings Firebase
 *    Installations with it — an FID plus a device fingerprint going to Google —
 *    which changes `DATA-SAFETY.md`'s "Device or other IDs" row. `PUSH.md §7`
 *    says both must be rewritten *before* the release that contains FCM, not
 *    after.
 *
 * So everything downstream of a token — the preference, the permission, the
 * channels, the tap, the registration call, the settings copy — is built and
 * working, and the token itself arrives through here. Wiring FCM is then one
 * class implementing one method, and the three decisions above are made once,
 * by whoever owns them, rather than smuggled in by this change.
 *
 * The honest consequence is stated in the interface rather than hidden: today
 * [current] returns null, `DailyController` never reaches the registration
 * call, and the settings screen says *"Nothing is being sent yet"* in six
 * languages. That sentence is true, and it is the one thing this design refuses
 * to get wrong — the web app once shipped four notification toggles for letters
 * no sender existed for, and they had to be taken back out.
 */
interface PushTokens {

    /**
     * This device's registration token, or null because there is no transport.
     *
     * Suspending because the real implementation is a network round trip to
     * Google — `FirebaseMessaging.getInstance().token` returns a `Task`, and
     * on a cold start with no cached token it does not answer immediately.
     */
    suspend fun current(): String?

    /**
     * What the server is told this token is for.
     *
     * iOS sends `sandbox` or `production` here because APNs genuinely has two
     * hosts and a token belongs to exactly one of them; FCM has no such split,
     * so Android sends `production` always. It is on the wire from both
     * platforms so that one column answers the question for both, rather than
     * a nullable column that means "iOS only" and has to be explained.
     */
    val environment: String get() = "production"
}

/**
 * The implementation there is today: none.
 *
 * Not a stub that pretends — it returns null, and every caller treats null as
 * "this phone cannot receive notifications", which is exactly true. Nothing in
 * the app claims otherwise while this is the one in the container.
 */
class NoPushTransport : PushTokens {
    override suspend fun current(): String? = null
}
