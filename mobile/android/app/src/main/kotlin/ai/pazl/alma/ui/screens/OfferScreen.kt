package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.billing.PlayBilling
import ai.pazl.alma.billing.ShelfRow
import ai.pazl.alma.billing.StoreProducts
import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.ui.components.AlmaHaptics
import ai.pazl.alma.ui.components.AlmaPresence
import ai.pazl.alma.ui.components.AlmaStar
import ai.pazl.alma.ui.components.GoldButton
import ai.pazl.alma.ui.components.Hairline
import ai.pazl.alma.ui.components.QuietButton
import ai.pazl.alma.ui.components.StarVariant
import ai.pazl.alma.ui.components.StateHost
import ai.pazl.alma.ui.components.riseIn
import ai.pazl.alma.ui.sky.AuraTone
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaSpacing
import ai.pazl.alma.ui.theme.AlmaTheme
import androidx.activity.compose.LocalActivity
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel

/**
 * The paywall — the one screen in this app that takes money.
 *
 * It is the same sheet as the web checkout it was ported from, in the same
 * order, with the same pre-selection: the door for the system the person
 * reached for, then the archive, then the year. Somebody who tapped a locked
 * chapter arrives with that chapter's system selected, and somebody who arrived
 * from the chat — where the ask is *more questions* rather than a chart —
 * arrives on the archive, because that is the honest answer to "I want more
 * questions" and a `?: "natal"` in that position offers a natal purchase to
 * people who already own natal.
 *
 * ## Three things that web sheet had that this one does not
 *
 * Past tense on purpose: the browser stopped serving a paywall at all. The
 * cabinet it belonged to — tabs, hub, reader, chat, settings, the sheet and its
 * downsell — was deleted, and `src/` is the storefront now (the header of
 * `src/app/screens.css` records what went). The three differences below are
 * still why this screen is not a copy; they are recorded against that design,
 * not against anything a browser runs today.
 *
 * **The two consent boxes and the email field.** On the web we are the seller:
 * the buyer waives a 14-day withdrawal right so the writing can begin now, and
 * the receipt we send is the durable confirmation that makes the waiver stand.
 * On Play, **Google is the seller** — it takes the payment, it issues the
 * receipt, and its own terms carry the waiver. `billing.py` says so in as many
 * words and skips our receipt for store sales. Reproducing the two ticks here
 * would be quoting a contract we are not party to and recording a consent
 * nobody keeps.
 *
 * **A price of ours.** Every amount on this screen is Play's own formatted
 * string, because Play is what charges the card and does the currency and the
 * local tax. See [ai.pazl.alma.billing.buildShelf]; the consequence is that a
 * product missing from the Play Console is not shown rather than shown at our
 * price.
 *
 * **The downsell.** Nobody spends it — not this screen, and not the web sheet
 * this comment used to credit with spending it. `POST /billing/declined` hands
 * back a stored, one-time offer that is worth something only if it is *seen*,
 * and the moment a refusal happens here is the moment this screen is going
 * away. So the binding exists and has no caller ([ai.pazl.alma.data.AlmaClient.declined]),
 * which is a decision left open rather than a wire somebody forgot: which
 * surface gets that single nudge is the owner's call — `docs/REMAINING.md
 * §III.29`.
 *
 * Nothing on this screen unlocks anything. A grant closes it, and the grant
 * comes from the server having asked Google.
 */
@Composable
fun OfferScreen(
    container: AppContainer,
    system: String?,
    onClose: () -> Unit,
) {
    val vm: OfferViewModel = viewModel {
        OfferViewModel(container.client, container.session, container.billing, system)
    }
    val state by vm.state.collectAsStateWithLifecycle()
    val purchase by vm.purchase.collectAsStateWithLifecycle()
    val restore by vm.restore.collectAsStateWithLifecycle()

    // `launchBillingFlow` needs the activity Play will put its sheet over. Null
    // is possible in a preview and nowhere else, and the button is disabled
    // rather than crashing on a `!!`.
    val activity = LocalActivity.current

    // The screen closes when the **server** grants, never when Play returns OK.
    // That is the same rule stated three times in this codebase, and this is
    // the line that would break it if it read `purchase is Granted` off a
    // response code instead.
    val context = LocalContext.current
    LaunchedEffect(Unit) {
        container.billing.grants.collect {
            // The one touch money gets: the server has granted, the doors are
            // open, and the hand learns it at the same moment the screen does.
            AlmaHaptics.unlocked(context)
            onClose()
        }
    }

    NightSky(config = OfferSky) {
        StateHost(state, onRetry = vm::reload) { offer ->
            OfferSheet(
                offer = offer,
                purchase = purchase,
                restore = restore,
                onSelect = vm::select,
                onBuy = { activity?.let(vm::buy) },
                onRestore = vm::restorePurchases,
                buyable = activity != null,
                onClose = {
                    vm.declined()
                    onClose()
                },
            )
        }
    }
}

/**
 * A gold bloom low behind the mark, one mote, and no comet.
 *
 * The comet is off deliberately: it is the one thing in the sky that moves
 * across rather than in place, and a streak passing behind a price is the sort
 * of motion that reads as urgency. This product does not do urgency.
 */
private val OfferSky = SkyConfig(
    seed = 10,
    starDensity = 0.6f,
    motes = 1,
    comet = false,
    auras = listOf(SkyConfig.Aurora(AuraTone.Gold, 0.5f, 0.14f, 0.62f)),
)

@Composable
private fun OfferSheet(
    offer: Offer,
    purchase: PlayBilling.Status,
    restore: RestoreState,
    onSelect: (String) -> Unit,
    onBuy: () -> Unit,
    onRestore: () -> Unit,
    buyable: Boolean,
    onClose: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .systemBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = AlmaSpacing.Pad, vertical = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        AlmaPresence(size = 56.dp, ring = false)
        Spacer(Modifier.height(18.dp))
        Text(
            text = stringResource(R.string.paywall_title),
            style = AlmaTheme.type.displayL,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(10.dp))
        Text(
            text = stringResource(R.string.paywall_sub),
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
            modifier = Modifier.widthIn(max = 420.dp),
        )

        // **What the money buys, before any price and before any error.**
        //
        // The pitch renders unconditionally, so the page is about the thing
        // being sold whatever the store is doing, and a storefront failure
        // degrades to one quiet block below instead of *being* the page.
        Spacer(Modifier.height(18.dp))
        Pitch(door = offer.wanted != null)

        Spacer(Modifier.height(26.dp))

        if (offer.rows.isEmpty()) {
            if (offer.unpriced.isEmpty()) {
                // Everything already open is good news, said plainly.
                Text(
                    text = stringResource(R.string.paywall_all_open),
                    style = MaterialTheme.typography.bodyMedium,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.widthIn(max = 420.dp),
                )
            } else {
                // **The rungs stay visible when the store does not answer.**
                //
                // The prices used to take the whole ladder down with them, so
                // on an emulator — or on a train — the subscription simply did
                // not exist anywhere in the product. What we know locally —
                // which rungs exist, what each one contains — is shown; the
                // one thing that may never be invented is the number, and the
                // number is what stays blank.
                ShelfPreview(offer.unpriced)
                Spacer(Modifier.height(18.dp))
                Text(
                    text = stringResource(R.string.error_billing_unavailable),
                    style = MaterialTheme.typography.bodyMedium,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.widthIn(max = 420.dp),
                )
            }
        } else {
            Column(Modifier.fillMaxWidth().selectableGroup()) {
                offer.rows.forEachIndexed { index, row ->
                    Column(Modifier.riseIn(index)) {
                        OfferOption(
                            row = row,
                            selected = row.slug == offer.selected?.slug,
                            onSelect = { onSelect(row.slug) },
                        )
                        if (index != offer.rows.lastIndex) Hairline()
                    }
                }
            }

            Spacer(Modifier.height(22.dp))

            val selected = offer.selected
            if (selected != null) {
                GoldButton(
                    text = stringResource(R.string.paywall_buy, offerLabel(selected), selected.price),
                    onClick = onBuy,
                    enabled = buyable && purchase !is PlayBilling.Status.Working,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }

        OfferOutcome(purchase, restore)

        Spacer(Modifier.height(22.dp))
        OfferHonesty()

        Spacer(Modifier.height(18.dp))
        QuietButton(
            text = stringResource(R.string.paywall_restore),
            onClick = onRestore,
            enabled = restore !is RestoreState.Working,
        )

        Spacer(Modifier.height(12.dp))
        QuietButton(
            text = stringResource(R.string.paywall_not_now),
            onClick = onClose,
            contentColor = AlmaPalette.Muted,
        )
    }
}

/**
 * One rung of the ladder.
 *
 * A radio button in everything but appearance: `selectable` with
 * [Role.RadioButton] is what makes TalkBack say "selected" and what gives the
 * group arrow-key behaviour, and none of it costs a control that looks like
 * Material. What marks the selection is the mark itself, in gold — there is no
 * box around a row, because there are no boxes.
 */
@Composable
private fun OfferOption(row: ShelfRow, selected: Boolean, onSelect: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .selectable(selected = selected, role = Role.RadioButton, onClick = onSelect)
            .padding(vertical = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (selected) {
            AlmaStar(size = 13.dp, variant = StarVariant.Gold)
        } else {
            Spacer(Modifier.widthIn(min = 13.dp).height(13.dp))
        }

        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(
                text = offerLabel(row),
                style = AlmaTheme.type.headingM,
                color = if (selected) AlmaPalette.GoldBright else AlmaPalette.InkLight,
            )
            Text(text = offerNote(row), style = AlmaTheme.type.meta)
        }

        Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(
                text = row.price,
                style = AlmaTheme.type.positions,
                color = if (selected) AlmaPalette.GoldBright else AlmaPalette.Gold,
            )
            // Only when Play's own offer says the two differ. An introductory
            // price on the button and the ongoing price nowhere on the screen
            // is the shape a chargeback takes.
            row.recurringPrice?.let { ongoing ->
                Text(text = stringResource(R.string.paywall_then, ongoing), style = AlmaTheme.type.meta)
            }
        }
    }
    // The annual's arithmetic, in subordinate size under the row — the billed
    // amount above stays the most prominent price, which is the store's rule
    // about per-month equivalents and this design's preference anyway.
    if (row.perMonth != null && row.savingsPercent != null) {
        Text(
            text = stringResource(R.string.paywall_per_month_savings, row.perMonth, row.savingsPercent),
            style = AlmaTheme.type.meta,
            color = AlmaPalette.GoldBright.copy(alpha = 0.9f),
            modifier = Modifier.padding(start = 25.dp, bottom = 12.dp),
        )
    }
}

/**
 * Three facts about the purchase, in the buyer's language. Facts, not
 * adjectives: each line is checkable against the product.
 */
@Composable
private fun Pitch(door: Boolean) {
    val lines = if (door) {
        listOf(
            R.string.paywall_pitch_door_1,
            R.string.paywall_pitch_door_2,
            R.string.paywall_pitch_door_3,
        )
    } else {
        listOf(
            R.string.paywall_pitch_plan_1,
            R.string.paywall_pitch_plan_2,
            R.string.paywall_pitch_plan_3,
        )
    }
    Column(verticalArrangement = Arrangement.spacedBy(7.dp), modifier = Modifier.widthIn(max = 420.dp)) {
        lines.forEach { line ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(text = "·", style = AlmaTheme.type.positions)
                Text(text = stringResource(line), style = AlmaTheme.type.meta)
            }
        }
    }
}

/**
 * The ladder's rows without the ladder's prices — what renders while Play is
 * not answering. Same rungs, same order, same words as the real thing; the
 * price column is empty rather than guessed, and nothing here can be tapped
 * into a purchase.
 */
@Composable
private fun ShelfPreview(slugs: List<String>) {
    Column(Modifier.fillMaxWidth()) {
        slugs.forEachIndexed { index, slug ->
            Row(
                modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Spacer(Modifier.widthIn(min = 13.dp).height(13.dp))
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text(text = previewLabel(slug), style = AlmaTheme.type.headingM)
                    Text(text = previewNote(slug), style = AlmaTheme.type.meta)
                }
            }
            if (index != slugs.lastIndex) Hairline()
        }
    }
}

@Composable
private fun previewLabel(slug: String): String = when (slug) {
    StoreProducts.ARCHIVE, StoreProducts.ARCHIVE_UPGRADE -> stringResource(R.string.paywall_archive)
    StoreProducts.ANNUAL -> stringResource(R.string.paywall_everything_year)
    StoreProducts.MONTHLY -> stringResource(R.string.paywall_everything_month)
    else -> systemName(slug)
}

@Composable
private fun previewNote(slug: String): String = when (slug) {
    StoreProducts.ARCHIVE_UPGRADE -> stringResource(R.string.paywall_archive_upgrade_note)
    StoreProducts.ARCHIVE -> stringResource(R.string.paywall_archive_note)
    StoreProducts.ANNUAL -> stringResource(R.string.paywall_renews_year)
    StoreProducts.MONTHLY -> stringResource(R.string.paywall_renews_month)
    else -> stringResource(R.string.paywall_one_time_note)
}

/**
 * What just happened, in one line, under the button.
 *
 * A cancelled purchase says nothing at all. Somebody who closed Play's sheet
 * made a decision and does not need it read back to them, and an apology for it
 * is the beginning of nagging.
 */
@Composable
private fun OfferOutcome(purchase: PlayBilling.Status, restore: RestoreState) {
    val message: String? = when {
        restore is RestoreState.Working -> stringResource(R.string.state_loading_short)
        restore is RestoreState.NothingFound -> stringResource(R.string.paywall_restore_none)
        // Three answers a restore can give that are not "nothing found", and
        // each of them used to arrive as silence.
        restore is RestoreState.Restored -> stringResource(R.string.paywall_restore_done)
        restore is RestoreState.Settling -> stringResource(R.string.paywall_pending)
        restore is RestoreState.Unconfirmed -> stringResource(R.string.paywall_unverified)
        purchase is PlayBilling.Status.Working -> stringResource(R.string.paywall_working)
        purchase is PlayBilling.Status.Pending -> stringResource(R.string.paywall_pending)
        purchase is PlayBilling.Status.Failed -> offerFailureLine(purchase)
        else -> null
    }
    if (message == null) return

    Spacer(Modifier.height(14.dp))
    Text(
        text = message,
        style = MaterialTheme.typography.bodyMedium,
        textAlign = TextAlign.Center,
        modifier = Modifier.widthIn(max = 420.dp),
    )
}

/**
 * A billing failure, said in a sentence a person can act on.
 *
 * Three cases and they are genuinely different things.
 *
 * [ApiFailure.Locked] from a *purchase* means Google confirmed the payment and
 * our server granted this account nothing — all but always one Google account
 * holding two Alma accounts. It is not "something went wrong" and it is not the
 * buyer's mistake, and the purchase has deliberately been left unacknowledged so
 * Google's three-day refund still stands behind it.
 *
 * Anything else with [PlayBilling.Status.Failed.paid] set means the money moved
 * and we could not confirm it. `error_billing_unavailable` — "nothing has been
 * charged and nothing was lost" — is the right sentence before a payment and a
 * falsehood after one, and it is the kind of falsehood the reader can check
 * against their bank.
 *
 * Everything else happened before the sheet closed, so no money moved.
 */
@Composable
private fun offerFailureLine(failed: PlayBilling.Status.Failed): String = when {
    failed.failure is ApiFailure.Locked -> stringResource(R.string.paywall_claimed)
    failed.paid -> stringResource(R.string.paywall_unverified)
    failed.failure is ApiFailure.Offline -> stringResource(R.string.state_offline)
    failed.failure is ApiFailure.Unavailable || failed.failure is ApiFailure.Invalid ->
        stringResource(R.string.error_billing_unavailable)
    else -> stringResource(R.string.error_generic)
}

/**
 * The honesty plate, the same three promises as the landing — and one of them
 * had to be rewritten rather than translated.
 *
 * "cancel in two taps, from Settings" is true on the web, where we hold the
 * subscription. A Play subscription is cancelled in Play and nowhere else, so
 * the line says Play. Printing the web's sentence here would be a promise this
 * app cannot keep, on the screen where somebody is deciding whether to trust it.
 */
@Composable
private fun OfferHonesty() {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        listOf(
            R.string.paywall_honesty_once,
            R.string.paywall_honesty_free,
            R.string.paywall_honesty_cancel,
        ).forEach { line ->
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                AlmaStar(size = 9.dp, variant = StarVariant.Flat)
                Text(text = stringResource(line), style = AlmaTheme.type.meta)
            }
        }
    }
}

/* ── naming the things on sale ─────────────────────────────────────────── */

/**
 * What a row is called.
 *
 * The system names are localised here rather than taken from the catalogue's
 * `name`, which the server sends in English only — it is a field for our own
 * logs and for a currency-agnostic price list, not a label for a Portuguese
 * paywall.
 */
@Composable
private fun offerLabel(row: ShelfRow): String = when (row.slug) {
    StoreProducts.ARCHIVE, StoreProducts.ARCHIVE_UPGRADE -> stringResource(R.string.paywall_archive)
    StoreProducts.ANNUAL -> stringResource(R.string.paywall_everything_year)
    StoreProducts.MONTHLY -> stringResource(R.string.paywall_everything_month)
    else -> systemName(row.system ?: row.slug)
}

@Composable
private fun offerNote(row: ShelfRow): String = when {
    // The upgrade is the archive at the shelf price less the door already paid
    // — a different price id rather than a discount applied to this one — so
    // the row can say *why* it is cheaper instead of inventing a struck-through
    // price of its own.
    row.replaces != null -> stringResource(R.string.paywall_archive_upgrade_note)
    row.interval == "year" -> stringResource(R.string.paywall_renews_year)
    row.interval == "month" -> stringResource(R.string.paywall_renews_month)
    row.slug == StoreProducts.ARCHIVE -> stringResource(R.string.paywall_archive_note)
    else -> stringResource(R.string.paywall_one_time_note)
}
