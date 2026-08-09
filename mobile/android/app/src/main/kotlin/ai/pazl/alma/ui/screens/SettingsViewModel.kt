package ai.pazl.alma.ui.screens

import ai.pazl.alma.core.ScreenState
import ai.pazl.alma.core.SessionHolder
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.Measurement
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.data.TokenStore
import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.data.dto.CalcRequest
import ai.pazl.alma.data.dto.CatalogueItemDto
import ai.pazl.alma.notify.DailyContact
import ai.pazl.alma.data.dto.EntitlementDto
import ai.pazl.alma.data.dto.ProfileDto
import ai.pazl.alma.data.dto.SessionDto
import androidx.compose.runtime.Immutable
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

/**
 * Settings, which is four screens wearing one hat: what Alma holds about you,
 * what you are paying, how to get your data out, and how to leave.
 *
 * The last three are not optional extras. Three legal pages promise the export
 * and the deletion, California's AB 2863 and the EU's withdrawal-function rule
 * both require cancelling to be possible in the medium the subscription was
 * entered into, and Play requires an in-app route to account deletion for any
 * app that creates an account — which this one does, silently, on first launch.
 *
 * The screen's *data* is one `ScreenState`. The four things a person can **do**
 * are separate flows, because they are transitions rather than facts: an export
 * that failed does not make the plan section stop existing, and folding them
 * into one state would mean either five booleans beside the data or a state
 * machine with twenty reachable combinations.
 */
class SettingsViewModel(
    private val client: AlmaClient,
    private val session: SessionHolder,
    private val tokens: TokenStore,
    private val measurementStore: Measurement,
) : ViewModel() {

    /** Whether the funnel beacon is sent. See [Measurement] for why it is a choice. */
    val measurement: StateFlow<Boolean> = measurementStore.enabled

    fun setMeasurement(on: Boolean) = measurementStore.set(on)

    private val _state = MutableStateFlow<ScreenState<SettingsView>>(ScreenState.Loading)
    val state: StateFlow<ScreenState<SettingsView>> = _state.asStateFlow()

    /**
     * The transits, for the one row on this screen that checks a claim rather
     * than makes one.
     *
     * A second request on a settings screen needs a defence, and this is it: the
     * cadence sentence under *Occasionally* — "about once a week" — was measured
     * on 24 charts, none of which is this reader's, by a rule no running job
     * applies yet. The counted row underneath it is the same rule applied to
     * *their* chart, on this device, and it is the only part of the promise a
     * client can honestly verify.
     *
     * Its own flow rather than a field on [SettingsView], and its own failure:
     * a transits request that 503s must leave the three positions usable. The
     * switch is what somebody came here for, and a screen that hides it because
     * a verification number could not be computed has its priorities exactly
     * backwards.
     */
    private val _dailyContacts = MutableStateFlow<List<DailyContact>>(emptyList())
    val dailyContacts: StateFlow<List<DailyContact>> = _dailyContacts.asStateFlow()

    private val _cancelling = MutableStateFlow<CancelState>(CancelState.Idle)
    val cancelling: StateFlow<CancelState> = _cancelling.asStateFlow()

    private val _exporting = MutableStateFlow<ExportState>(ExportState.Idle)
    val exporting: StateFlow<ExportState> = _exporting.asStateFlow()

    private val _deleting = MutableStateFlow<DeleteState>(DeleteState.Idle)
    val deleting: StateFlow<DeleteState> = _deleting.asStateFlow()

    /**
     * Set when the account this app was holding no longer exists or no longer
     * belongs to this device. The screen watches it and restarts the activity,
     * because the destination the whole graph was built around — cabinet or
     * journey — was decided from a profile that has just stopped being true.
     */
    private val _restart = MutableStateFlow(false)
    val restart: StateFlow<Boolean> = _restart.asStateFlow()

    private var running: Job? = null

    init {
        reload()
    }

    fun reload() {
        running?.cancel()
        running = viewModelScope.launch {
            _state.value = ScreenState.Loading
            val account = session.state.first { it.ready }

            // The entitlements are the fact and the catalogue is only the price,
            // so a catalogue that fails degrades to a plan with no figure beside
            // it rather than taking the block down — and it never falls back to
            // a remembered number, because a stale price on a settings screen is
            // a quote.
            val (entitlements, catalogue, profiles) = coroutineScope {
                val held = async { client.entitlements() }
                val prices = async { client.catalogue() }
                val people = async { client.profiles() }
                Triple(held.await(), prices.await(), people.await())
            }

            // Deliberately after the block above and not inside it: it must not
            // make the screen wait, and the server has it cached
            // (`compute_cached`) from Today's identical request minutes earlier.
            if (account.hasBirthData) {
                launch {
                    val sky = client.system(
                        AlmaSystem.TRANSITS,
                        CalcRequest(days = 30, locale = account.locale),
                    )
                    _dailyContacts.value = DailyContact.all((sky as? ApiResult.Ok)?.data?.data)
                }
            }

            _state.value = when (entitlements) {
                is ApiResult.Err -> ScreenState.Failed(entitlements.failure)
                is ApiResult.Ok -> {
                    val items = (catalogue as? ApiResult.Ok)?.data?.items.orEmpty()
                    ScreenState.Loaded(
                        SettingsView(
                            account = account.account,
                            profile = (profiles as? ApiResult.Ok)?.data
                                ?.firstOrNull { it.isSelf }
                                ?: account.profile,
                            held = entitlements.data.entitlements,
                            // Anything not bought outright is a plan, asked of
                            // the catalogue rather than matched against a list
                            // of kinds written here. A hand-written list is what
                            // once let a monthly product be sold as a yearly one
                            // on this very screen.
                            plans = items
                                .filter { it.kind.isNotBlank() && it.kind != "one_time" }
                                .associateBy { it.kind },
                            soldNames = items
                                .mapNotNull { item -> item.system?.let { it to item.name } }
                                .toMap(),
                            manageUrl = (catalogue as? ApiResult.Ok)?.data?.manageUrl.orEmpty(),
                        )
                    )
                }
            }
        }
    }

    /* ── language ──────────────────────────────────────────────────────── */

    /**
     * Tell the backend which language to write in.
     *
     * Only the backend. Which language the *interface* speaks is the platform's
     * business and is set by the screen, because below API 33 there is no
     * framework way to do it without an activity restart the person did not ask
     * for. The two are genuinely different settings and it is worth saying so:
     * this one decides the language of the next chapter Alma writes, and it has
     * to survive to a server that will still be writing chapters tomorrow.
     */
    fun setLocale(code: String) {
        viewModelScope.launch {
            client.setLocale(code)
            session.start(force = true)
            // **And say so on the screen, which it did not.**
            //
            // `reload()` runs once, in `init`, and reads the session with
            // `first { it.ready }` — a single value, not a subscription. So the
            // PATCH landed, the session refreshed, the server started writing
            // in the new language, and the picker went on drawing the gold ring
            // around the old one. Tapping your own language and watching
            // nothing happen reads as a broken control; the natural next move
            // is to tap it again. Seen on a device: the account was already
            // `de` while «Русский» was still the selected chip.
            //
            // Patched in place rather than by calling `reload()`, which would
            // drop the whole screen to its loading state — a settings page that
            // blinks out and rebuilds itself is a heavy answer to a chip tap,
            // and the two extra requests it makes have nothing to do with
            // language.
            val shown = _state.value
            if (shown is ScreenState.Loaded) {
                val account = shown.data.account
                if (account != null) {
                    _state.value = ScreenState.Loaded(
                        shown.data.copy(account = account.copy(locale = code))
                    )
                }
            }
        }
    }

    /* ── the plan ──────────────────────────────────────────────────────── */

    fun askToCancel() {
        _cancelling.value = CancelState.Confirming
    }

    fun keepPlan() {
        _cancelling.value = CancelState.Idle
    }

    /**
     * The second tap.
     *
     * The endpoint takes no identifier — the account is the identifier — and
     * nothing is revoked: the period has been paid for and runs to its end. What
     * comes back is the date access actually stops, which is the sentence the
     * interface has to be able to say. The list is reloaded afterwards to pick
     * up the cleared `renews_at` rather than to watch anything disappear.
     */
    fun cancelSubscription() {
        viewModelScope.launch {
            _cancelling.value = CancelState.Working
            when (val answer = client.cancelSubscription()) {
                is ApiResult.Ok -> {
                    _cancelling.value = CancelState.Cancelled(answer.data.accessUntil)
                    reload()
                }
                is ApiResult.Err -> _cancelling.value = CancelState.Failed(answer.failure)
            }
        }
    }

    /* ── export ────────────────────────────────────────────────────────── */

    /**
     * Fetch everything the account holds, as one document.
     *
     * **Open to a guest**, and it used to refuse them with `NeedsAccount`
     * because the backend did. Both changed together and for the same reason as
     * deletion below: a guest account is a real row holding a birth date and
     * full-precision coordinates, and demanding an email address before the
     * person may read their own file is asking for more personal data as the
     * price of seeing what was already taken.
     *
     * The bytes are held here and written by the screen, because where they go
     * is a `Uri` the person picks in the system's own file picker and this class
     * has no business knowing about `ContentResolver`.
     */
    fun startExport() {
        viewModelScope.launch {
            _exporting.value = ExportState.Working
            _exporting.value = when (val answer = client.export()) {
                is ApiResult.Ok -> ExportState.Ready(answer.data.toString())
                is ApiResult.Err ->
                    if (answer.failure is ApiFailure.Unauthenticated) {
                        ExportState.NeedsAccount
                    } else {
                        ExportState.Failed
                    }
            }
        }
    }

    fun exportSaved() {
        _exporting.value = ExportState.Saved
    }

    /** The file picker was dismissed. Not a failure, and not worth a sentence. */
    fun exportDismissed() {
        _exporting.value = ExportState.Idle
    }

    fun exportFailed() {
        _exporting.value = ExportState.Failed
    }

    /* ── deletion ──────────────────────────────────────────────────────── */

    /**
     * Open the confirmation. There is no longer a state where it refuses.
     *
     * This used to answer `NeedsAccount` for a guest, so the one control Play
     * requires every account-creating app to provide led to a screen that said
     * "This needs an account we can attach to you" and offered a Sign in button
     * — to somebody whose birth date and coordinates were already on our server,
     * put there by the journey before any sign-in screen existed. Requiring an
     * email address in order to delete data taken without one is the exact
     * pattern the policy forbids, and it is a rejection on sight.
     */
    fun askToDelete() {
        _deleting.value = DeleteState.Confirming
    }

    fun keepAccount() {
        _deleting.value = DeleteState.Idle
    }

    /** Clears a mismatch as soon as the typing changes, so it is not shouted at. */
    fun typingChanged() {
        if (_deleting.value is DeleteState.Mismatch) _deleting.value = DeleteState.Confirming
    }

    /**
     * Erase everything.
     *
     * [expected] is whatever this account can actually be asked for: its email
     * address if it has one, and otherwise its own id, which a guest has and a
     * stranger does not. The server makes the same comparison — see
     * `alma/api/routers/account.py::delete` — and doing it here as well is not
     * duplication for its own sake: it keeps the button dim until the typing is
     * right, instead of failing after the tap on the one action in the app that
     * cannot be undone.
     */
    fun deleteAccount(typed: String, expected: String?) {
        if (expected.isNullOrBlank() || typed.trim().lowercase() != expected.trim().lowercase()) {
            _deleting.value = DeleteState.Mismatch
            return
        }
        viewModelScope.launch {
            _deleting.value = DeleteState.Working
            when (client.deleteAccount(typed.trim())) {
                is ApiResult.Ok -> {
                    // Everything in memory still belongs to an account that no
                    // longer exists, so the whole activity goes rather than the
                    // route: `signOut` mints a fresh guest and the graph is
                    // rebuilt around a person with no birth data, which is the
                    // journey.
                    session.signOut()
                    _restart.value = true
                }
                is ApiResult.Err -> _deleting.value = DeleteState.Failed
            }
        }
    }

    /**
     * Forget the token on this device.
     *
     * A guest is never offered this. Their chart is attached to the token rather
     * than to a name, so clearing it would not sign them out of anything — it
     * would mint them a new, empty account and lose the one they have.
     */
    fun signOut() {
        session.signOut()
        _restart.value = true
    }
}

/* ── what the screen holds ─────────────────────────────────────────────── */

@Immutable
data class SettingsView(
    val account: SessionDto?,
    /** The person's own birth data. There is at most one `is_self` profile. */
    val profile: ProfileDto?,
    val held: List<EntitlementDto>,
    /** Every recurring product on sale, keyed by the kind its grant is written under. */
    val plans: Map<String, CatalogueItemDto>,
    /** The catalogue's own English names, as a fallback for a system this build cannot name. */
    val soldNames: Map<String, String>,
    /**
     * Where a subscriber goes to stop paying, when that is not us.
     *
     * Filled in only by the store adapters. Its presence is what decides whether
     * this screen may draw a cancel button at all: on a store, no server can
     * cancel a subscription that belongs to a Google account, and a button that
     * cannot honour itself is worse than no button.
     */
    val manageUrl: String,
)

@Immutable
sealed interface CancelState {
    data object Idle : CancelState
    data object Confirming : CancelState
    data object Working : CancelState

    /** [accessUntil] is the day the reading stops opening, not the day it stopped renewing. */
    @Immutable
    data class Cancelled(val accessUntil: String?) : CancelState

    @Immutable
    data class Failed(val failure: ApiFailure) : CancelState
}

@Immutable
sealed interface ExportState {
    data object Idle : ExportState
    data object Working : ExportState

    /** The document, waiting for somewhere to be written. */
    @Immutable
    data class Ready(val json: String) : ExportState
    data object Saved : ExportState
    data object Failed : ExportState
    data object NeedsAccount : ExportState
}

@Immutable
sealed interface DeleteState {
    data object Idle : DeleteState
    data object Confirming : DeleteState
    data object Working : DeleteState
    data object Mismatch : DeleteState
    data object Failed : DeleteState
    // There is no `NeedsAccount` here any more, and there must not be one: it
    // was the state that told a guest to sign in before they could delete the
    // birth data we had already taken from them.
}
