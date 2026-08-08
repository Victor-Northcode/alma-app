package ai.pazl.alma.core

import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.data.dto.EntitlementsDto
import ai.pazl.alma.data.dto.ProfileDto
import ai.pazl.alma.data.dto.SessionDto
import androidx.compose.runtime.Immutable
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/**
 * Who this is, what they have told us, and what they are allowed to read.
 *
 * One instance, held by [AppContainer] for the life of the process, and every
 * screen reads it. It exists because these three facts are needed by nearly
 * every screen and are expensive to fetch — a hub, a paywall, a settings page
 * and a chat all want to know whether the natal chart is unlocked, and four
 * screens each fetching entitlements is four requests and four chances to
 * disagree with each other.
 *
 * ## What it deliberately does not do
 *
 * It does not fetch charts, chapters or chat. Those belong to the screens that
 * show them: a session holder that also cached readings would become the place
 * every feature puts its state, and the first symptom is a screen that shows
 * the previous person's chapter for a frame after a sign-out.
 *
 * It also does not poll. [refreshEntitlements] is called after a purchase and
 * on resume, both of which are moments something can genuinely have changed.
 */
class SessionHolder(
    private val client: AlmaClient,
    private val scope: CoroutineScope,
) {

    private val _state = MutableStateFlow(AlmaSession())

    /** The one thing screens observe. Never null, never empty of meaning. */
    val state: StateFlow<AlmaSession> = _state.asStateFlow()

    /**
     * Guards [ensureSession].
     *
     * Two screens composing at once both want an account, and without this both
     * would call `/v1/auth/session` with no token — which mints *two* accounts,
     * the second of which wins and the first of which silently owns whatever
     * the first request recorded. That is the exact failure `funnel.py` warns
     * about, arriving through concurrency instead of through a missing header.
     */
    private val sessionLock = Mutex()

    /**
     * Make sure this device has an account, then load what hangs off it.
     *
     * Idempotent and safe to call from anywhere. The first call does the work;
     * later ones return immediately unless [force] is set.
     */
    fun start(force: Boolean = false) {
        scope.launch { ensureSession(force, mayCreateAccount = false) }
    }

    /**
     * Like [start], but it waits, and it returns whether there is an account.
     *
     * For the one caller that must not proceed without one: verifying a
     * purchase. `AlmaHttp.SessionInterceptor` attaches `Authorization` only
     * when a token already exists, and the server mints a fresh guest for any
     * request that arrives without one — so on a cold start where Play's
     * `queryPurchasesAsync` beats `GET /v1/auth/session` (a reinstall, a second
     * device), `POST /v1/billing/iap/verify` would go out bare and Google's
     * transaction would be filed against a throwaway account that the app then
     * abandons, because whichever response lands last wins the token.
     *
     * That is unrecoverable rather than merely untidy: the transaction id is a
     * primary key, so every later attempt from the real account answers
     * `already_claimed` with an `unlocked` list that does not contain the
     * product, forever. `PlayBilling.redeem` correctly refuses to acknowledge
     * it, Google refunds after three days, and the person who paid holds
     * nothing — caused by our own launch ordering rather than by the missing
     * account-link feature.
     *
     * Awaiting the *account* rather than [AlmaSession.ready] on purpose: the
     * token is what the request needs, and the profile and entitlement calls
     * that `ready` also waits for are nothing to do with it.
     */
    suspend fun awaitAccount(): Boolean {
        // The one place `mayCreateAccount` is true, and the docstring above is
        // the argument for it: a purchase is an act, the money has to land on a
        // row that exists, and a verify that goes out bare files Google's
        // transaction against a throwaway account the app then abandons —
        // permanently, because the transaction id is a primary key.
        ensureSession(force = false, mayCreateAccount = true)
        return _state.value.account != null
    }

    /**
     * @param mayCreateAccount whether this caller is allowed to bring an account
     *   into existence. `GET /v1/auth/session` mints for a device with no token,
     *   so calling it from [start] made opening the app the act that created the
     *   account — every install, before anybody had typed anything, which is the
     *   owner's rule ("not on a page view") broken on the surface where almost
     *   all real users are. Launch reads; a purchase creates.
     */
    private suspend fun ensureSession(
        force: Boolean,
        mayCreateAccount: Boolean,
    ) = sessionLock.withLock {
        if (_state.value.account != null && !force) return@withLock

        if (!mayCreateAccount && !client.hasSession) {
            // A device that has given us nothing. Ready, with no account and
            // nothing hanging off one — which is the state the journey exists to
            // leave, and exactly what every screen already draws for a person
            // who has not saved a birth yet. The three calls below are skipped
            // as well, not only the session: `/v1/profiles`,
            // `/v1/billing/entitlements` and `/v1/hub` all take `CurrentUser`
            // on the server, so any one of them would mint the row this branch
            // exists to not mint, and all three answer with nothing for a
            // brand-new account anyway.
            _state.update {
                it.copy(loading = false, ready = true, account = null, failure = null)
            }
            return@withLock
        }

        _state.update { it.copy(loading = true) }
        when (val result = client.session()) {
            is ApiResult.Ok -> {
                _state.update { it.copy(account = result.data, failure = null) }
                // Both are independent of each other and of the session that
                // just arrived, so they run together rather than chained.
                //
                // They are also **awaited**, and that is what [AlmaSession.ready]
                // is for. The first thing the app does with this state is choose
                // between the journey and the cabinet, and that choice is made
                // from `profile != null`. Publishing `ready` before the profile
                // request has answered would send every returning person into
                // the journey for the third of a second before it arrived — and
                // a `startDestination` cannot be changed afterwards without
                // rebuilding the graph under them.
                val profile = scope.launch { refreshProfile() }
                val entitlements = scope.launch { refreshEntitlements() }
                profile.join()
                entitlements.join()
                _state.update { it.copy(loading = false, ready = true) }
            }
            is ApiResult.Err -> {
                // Ready, and knowing nothing. An app that cannot reach the
                // server still has to draw something, and what it draws is the
                // journey with a failure on it rather than a permanent spinner.
                _state.update { it.copy(loading = false, ready = true, failure = result.failure) }
            }
        }
    }

    /**
     * Reload the person's own birth data.
     *
     * "Own" is `is_self`, and there is at most one. The other profiles are
     * people they are compared *with*, and they belong to the compatibility
     * screen rather than here.
     */
    suspend fun refreshProfile() {
        if (!client.hasSession) return
        when (val result = client.profiles()) {
            is ApiResult.Ok -> _state.update { current ->
                current.copy(profile = result.data.firstOrNull { it.isSelf }, people = result.data.count { !it.isSelf })
            }
            is ApiResult.Err -> Unit // A stale profile is better than none.
        }
    }

    /**
     * Reload what is unlocked.
     *
     * Call after a verified purchase and on resume. Not on a timer: a
     * subscription that lapses mid-session is a rarity, and polling would spend
     * a request every few minutes to catch it a little sooner.
     *
     * The guard is the same one [refreshProfile] carries and it matters more
     * here, because `MainActivity` calls this on every `STARTED` — so without it
     * an install that had never typed anything would mint an account by being
     * *resumed*, which is the launch bug wearing a different hat.
     */
    suspend fun refreshEntitlements() {
        if (!client.hasSession) return
        when (val result = client.entitlements()) {
            is ApiResult.Ok -> _state.update { it.copy(entitlements = result.data) }
            is ApiResult.Err -> Unit
        }
    }

    /**
     * Redeem a token from an emailed sign-in link.
     *
     * Here rather than in `SignInViewModel` because the link can arrive while
     * the person is anywhere — including with the app closed, which is the
     * ordinary case — and `MainActivity` is what receives the intent. A sign-in
     * that only worked while the sign-in screen happened to be open would be a
     * link that breaks if you navigate away while waiting for the email.
     *
     * The current token is deliberately *not* cleared first: consuming attaches
     * an identity to the account this device already has, so everything a guest
     * did — including anything they bought — stays where it is.
     */
    fun signInWithLink(token: String) {
        scope.launch {
            when (val answer = client.consumeMagicLink(token)) {
                is ApiResult.Ok -> onSignedIn(answer.data)
                is ApiResult.Err -> {
                    // Put on the session so anything watching can say it, and
                    // logged because at the moment nothing is: the link can
                    // arrive with the person standing on any screen, and none
                    // of them is a sign-in screen with somewhere to show a
                    // failure. A link that has expired therefore looks like an
                    // app that did nothing. Worth fixing with a route to
                    // `SIGN_IN` on arrival; noted rather than smuggled in here,
                    // because it needs the NavController and this class has no
                    // business holding one.
                    android.util.Log.w("SessionHolder", "sign-in link refused: ${answer.failure.message}")
                    _state.update { it.copy(failure = answer.failure) }
                }
            }
        }
    }

    /** After a sign-in. The account is the same row; the identity on it is new. */
    fun onSignedIn(session: SessionDto) {
        _state.update { it.copy(account = session, failure = null) }
        scope.launch { refreshProfile() }
        scope.launch { refreshEntitlements() }
    }

    /** After the birth data is saved, so the hub does not have to be re-fetched to notice. */
    fun onProfileSaved(profile: ProfileDto) {
        _state.update { if (profile.isSelf) it.copy(profile = profile) else it.copy(people = it.people + 1) }
        // Saving a birth is the act that mints the account for most people, and
        // until this ran the session held `account = null` afterwards — which
        // Settings reads to decide what a guest must type to confirm a
        // deletion. A guest with no account id in hand is a delete button that
        // refuses every string it is given, on the screen App Review opens
        // first. `ensureSession` is a read now, because the save came back with
        // a token.
        scope.launch { ensureSession(force = false, mayCreateAccount = false) }
    }

    /** After `verifyPurchase` — the unlocked list comes back on the same response. */
    fun onPurchaseVerified(unlocked: List<String>) {
        _state.update { current ->
            current.copy(
                entitlements = (current.entitlements ?: EntitlementsDto()).copy(unlocked = unlocked)
            )
        }
        scope.launch { refreshEntitlements() }
    }

    /**
     * Drop the token and everything that hung off it.
     *
     * It used to mint a fresh guest on the way out, which was the old rule
     * ("any request without a token is an account") having the last word on the
     * one screen where it reads worst: somebody signing out was handed a brand
     * new account for the gesture. `start` now reads and does not create, so
     * what it leaves behind is a device with no account — the state every
     * install begins in — and the journey draws for it exactly as before.
     */
    fun signOut() {
        client.signOut()
        _state.value = AlmaSession()
        start(force = true)
    }
}

/**
 * The session, as a screen sees it.
 *
 * Flat and immutable on purpose. A screen reads `session.unlocked` and
 * `session.hasBirthData` — questions about the world — rather than reaching
 * through three nullable objects to work them out for itself, which is how four
 * screens end up with four subtly different definitions of "unlocked".
 */
@Immutable
data class AlmaSession(
    val account: SessionDto? = null,
    /** The person's own birth data, or null if they have not given it yet. */
    val profile: ProfileDto? = null,
    /** How many *other* people are on file, for compatibility. */
    val people: Int = 0,
    val entitlements: EntitlementsDto? = null,
    val loading: Boolean = false,
    /**
     * The first load has finished, one way or the other.
     *
     * Nothing that branches on [hasBirthData] may run before this is true. It
     * is false-and-loading at launch, and it goes true even when the session
     * request failed — an app that cannot reach the server still has to draw
     * something, and a permanent spinner is not it.
     */
    val ready: Boolean = false,
    val failure: ai.pazl.alma.data.ApiFailure? = null,
) {
    val isGuest: Boolean get() = account?.isGuest != false

    val locale: String get() = account?.locale ?: "en"

    /** Systems this account may read in full. Decided by the server, always. */
    val unlocked: List<String> get() = entitlements?.unlocked.orEmpty()

    fun isUnlocked(system: String): Boolean = system in unlocked

    val hasBirthData: Boolean get() = profile != null

    /**
     * Whether a real birth *time* is known.
     *
     * Not the same question as [hasBirthData], and the difference decides what
     * five of the eight systems are allowed to say. Null here means unknown,
     * never midnight — an assumed noon puts an Ascendant in the wrong sign
     * about half the time, and nothing is shown that was not calculated.
     */
    val birthTimeKnown: Boolean get() = profile?.birthTime != null
}
