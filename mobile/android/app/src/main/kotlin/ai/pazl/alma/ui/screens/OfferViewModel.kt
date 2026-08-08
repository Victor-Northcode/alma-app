package ai.pazl.alma.ui.screens

import ai.pazl.alma.billing.PlayBilling
import ai.pazl.alma.billing.Shelf
import ai.pazl.alma.billing.ShelfRow
import ai.pazl.alma.billing.buildShelf
import ai.pazl.alma.core.ScreenState
import ai.pazl.alma.core.SessionHolder
import ai.pazl.alma.core.dataOrNull
import ai.pazl.alma.core.map
import ai.pazl.alma.core.toScreenState
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.FunnelStage
import android.app.Activity
import androidx.compose.runtime.Immutable
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * The paywall's state, and the only place in the app that starts a purchase.
 *
 * ## What it does not do
 *
 * It does not unlock anything, and it cannot. `PlayBilling` hands the purchase
 * token to the server, the server checks it with Google, and the `unlocked`
 * list on that response is the only thing that changes what a person may read.
 * This class watches for that to happen and closes the screen; if it decided
 * for itself, every rule in the billing seam would be one modified APK away
 * from being free.
 *
 * ## What it sells, and what it refuses to
 *
 * Only what this account's own catalogue listed — see [buildShelf]. In
 * particular the conditional prices are not shelf items: `archive-bump` exists
 * to be added to another checkout and grants everything the archive grants for
 * nine dollars less, so it is never purchasable here or anywhere else in this
 * app. `archive-upgrade` is different and is allowed, but only when the server
 * substituted it into the catalogue for this person, which is its own statement
 * that they qualify.
 */
class OfferViewModel(
    private val client: AlmaClient,
    private val session: SessionHolder,
    private val billing: PlayBilling,
    /** The system the person reached for, or null if they reached for nothing. */
    private val wanted: String?,
) : ViewModel() {

    private val _shelf = MutableStateFlow<ScreenState<Shelf>>(ScreenState.Loading)

    /**
     * Which row is selected, once somebody has chosen one.
     *
     * Null means "whatever the ladder puts first", which is the door for the
     * system they reached for and the archive when there was none. Keeping the
     * two apart matters: an explicit choice must survive a reload, and a
     * default must not.
     */
    private val _selected = MutableStateFlow<String?>(null)

    private val _restore = MutableStateFlow<RestoreState>(RestoreState.Idle)
    val restore: StateFlow<RestoreState> = _restore.asStateFlow()

    /** Where a purchase is. Owned by the billing client, mirrored here for the screen. */
    val purchase: StateFlow<PlayBilling.Status> = billing.status

    val state: StateFlow<ScreenState<Offer>> =
        combine(_shelf, _selected) { shelf, chosen ->
            shelf.map { loaded ->
                Offer(
                    wanted = wanted,
                    rows = loaded.rows,
                    selected = loaded.rows.firstOrNull { it.slug == chosen } ?: loaded.rows.firstOrNull(),
                    unpriced = loaded.unpriced,
                    manageUrl = loaded.manageUrl,
                )
            }
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), ScreenState.Loading)

    init {
        reload()

        // Recorded once per screen rather than per composition — a `ViewModel`
        // survives a rotation and a `LaunchedEffect` does not, and a funnel
        // stage counted twice for one person is a conversion rate that reads
        // low for a reason nobody can find.
        viewModelScope.launch {
            client.record(FunnelStage.OfferView, mapOf("product" to (wanted ?: "archive")))
        }

        // The other half of "the server grants": this is told about it rather
        // than deciding it. The stage is reported here because the *server*
        // records the money — sending a purchase event from the client as well
        // would double-count every sale — and what this adds is the client's
        // side of a gap worth watching: somebody whose sheet said "done" and
        // whose grant never arrived is a person who believes they paid.
        viewModelScope.launch {
            billing.grants.collect { granted ->
                client.record(FunnelStage.PurchaseCompleted, mapOf("product" to granted.product))
            }
        }
    }

    fun reload() {
        _shelf.value = ScreenState.Loading
        viewModelScope.launch {
            // What is already open is not offered again. Read from the
            // session rather than re-fetched, because the session holder is
            // the one place entitlements live and four screens each fetching
            // their own is four chances to disagree. The two `kind` facts are
            // read off the entitlement rows because the flat `unlocked` list
            // cannot tell an annual subscriber from an archive owner.
            val held = session.state.value.entitlements?.entitlements.orEmpty()
            _shelf.value = buildShelf(
                client = client,
                billing = billing,
                wanted = wanted,
                owned = session.state.value.unlocked,
                hasPlan = held.any { it.active && (it.kind == "monthly" || it.kind == "annual") },
                ownsArchive = held.any { it.active && it.scope == "all" && it.kind == "one_time" },
            ).toScreenState()
        }
    }

    fun select(slug: String) {
        _selected.value = slug
        // A refusal shown against the previous selection is not a refusal
        // against this one, and neither is the answer to a restore.
        billing.clear()
        _restore.value = RestoreState.Idle
    }

    /**
     * Open Play's sheet for the selected row.
     *
     * The stage is recorded at the tap rather than at the outcome, which is the
     * web app's decision and for the same reason: what it counts is people who
     * decided to pay, and waiting for the sheet to report back loses everybody
     * who wandered off inside it — precisely the population the next drop
     * measures.
     */
    fun buy(activity: Activity) {
        val row = state.value.dataOrNull()?.selected ?: return
        viewModelScope.launch {
            client.record(FunnelStage.CheckoutOpened, mapOf("product" to row.slug))
            billing.purchase(activity, row.details, row.offerToken)
        }
    }

    /**
     * Ask Play what this Google account already owns.
     *
     * Every launch does this anyway. The button exists because a person who has
     * reinstalled, or signed in on a second device, looks for one — and because
     * a store review expects it. Finding nothing is an answer worth saying out
     * loud rather than a silent no-op.
     */
    fun restorePurchases() {
        _restore.value = RestoreState.Working
        viewModelScope.launch {
            val found = billing.restore()
            // Four outcomes rather than two, because "we found nothing" and
            // "we found something and could not confirm it" send a person to
            // completely different places and this used to say the first for
            // both. It read a single counter that was incremented for every
            // purchase Play returned — before anything had been verified, and
            // including pending ones and product ids this build cannot map — so
            // anybody holding one of those got no message, a reload that
            // changed nothing, and no way to tell what had happened.
            _restore.value = when {
                found.granted > 0 -> RestoreState.Restored(found.granted)
                found.pending > 0 -> RestoreState.Settling
                found.unconfirmed > 0 -> RestoreState.Unconfirmed
                !found.any -> RestoreState.NothingFound
                // Play returned only purchases of products this build does not
                // sell. Nothing to restore *here*, which is the same sentence
                // as nothing at all from the reader's side.
                else -> RestoreState.NothingFound
            }
            if (found.granted > 0) reload()
        }
    }

    /**
     * They said no.
     *
     * Recorded, and nothing else. The web app also spends its single stored
     * downsell here, and this does not: the answer to `POST /billing/declined`
     * is a one-time offer that has to be *shown* to be worth anything, and this
     * screen is closing. Spending it into a screen that is going away would
     * burn the one nudge the product allows itself and show nobody anything.
     */
    fun declined() {
        val product = state.value.dataOrNull()?.selected?.slug ?: wanted ?: "archive"
        billing.clear()
        viewModelScope.launch {
            client.record(FunnelStage.OfferDeclined, mapOf("product" to product, "variant" to "skipped"))
        }
    }
}

@Immutable
data class Offer(
    /** The system the person reached for, or null — decides which pitch is told. */
    val wanted: String?,
    val rows: List<ShelfRow>,
    val selected: ShelfRow?,
    val unpriced: List<String>,
    val manageUrl: String?,
)

/**
 * What the last restore found. Four answers, because they are four next steps.
 *
 * The version this replaced had two — running, or "nothing found" — and derived
 * the second from a counter of purchases Play had *returned* rather than of
 * purchases that had been *granted*. So a pending cash payment or a product id
 * from an older price list produced a screen that said nothing at all.
 */
@Immutable
sealed interface RestoreState {
    data object Idle : RestoreState
    data object Working : RestoreState

    /** Google has no purchase on this account. A real answer, not a failure. */
    data object NothingFound : RestoreState

    /** Granted. The paywall is about to have fewer rows on it. */
    @Immutable
    data class Restored(val count: Int) : RestoreState

    /** A Play cash payment that has not settled. Nothing is owed yet. */
    data object Settling : RestoreState

    /**
     * Play has it and our server would not confirm it.
     *
     * The unhappy middle, and the one that must not read as "nothing found":
     * the purchase is deliberately left unacknowledged, so Google refunds it
     * after three days if this never resolves.
     */
    data object Unconfirmed : RestoreState
}
