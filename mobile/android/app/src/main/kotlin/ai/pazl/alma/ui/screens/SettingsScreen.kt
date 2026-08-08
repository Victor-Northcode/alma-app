package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.data.dto.EntitlementDto
import ai.pazl.alma.notify.DailyContact
import ai.pazl.alma.notify.DailyState
import ai.pazl.alma.ui.components.Hairline
import ai.pazl.alma.ui.components.QuietButton
import ai.pazl.alma.ui.components.StateHost
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import ai.pazl.alma.ui.theme.PillShape
import android.app.Activity
import android.app.LocaleManager
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.ContextWrapper
import android.net.Uri
import android.os.Build
import android.os.LocaleList
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Settings: what Alma holds, what you pay, and both of the doors out.
 *
 * The two doors are the reason this screen is not a list of switches. Export and
 * deletion are promised by three legal pages and required by Play for any app
 * that creates an account — and this one creates one silently on first launch,
 * before anybody has typed a word. Cancelling is required by law in the medium
 * the subscription was entered into, which on Android means Google Play's own
 * screen rather than a sentence telling somebody to go and find it.
 *
 * What is deliberately **not** here is a notifications section. The web app had
 * four toggles — three of them defaulted on — for letters that no sender exists
 * for, backed by nothing that persisted. They were removed there and are not
 * rebuilt here: `alma/mail.py` sends exactly three messages, all of them about
 * something the person did, and this screen says so instead of switching it.
 */
@Composable
fun SettingsScreen(
    container: AppContainer,
    onSignIn: () -> Unit,
    onOffer: () -> Unit,
) {
    val vm: SettingsViewModel = viewModel {
        SettingsViewModel(
            container.client,
            container.session,
            container.tokens,
            container.measurement,
        )
    }
    val state by vm.state.collectAsStateWithLifecycle()
    val restart by vm.restart.collectAsStateWithLifecycle()
    val daily by container.daily.state.collectAsStateWithLifecycle()
    val dailyContacts by vm.dailyContacts.collectAsStateWithLifecycle()
    val context = LocalContext.current

    // The OS is the truth and our stored flag is not, so it is re-read every
    // time this screen appears: a person can revoke the permission, or silence
    // the channel, in Android's own settings and will never tell us they did.
    // `docs/PUSH.md §5.6`. Without this the control would sit here claiming On
    // over a permission that has been off for a month.
    LaunchedEffect(Unit) { container.daily.refresh() }

    // The destination the whole graph was built around — cabinet or journey —
    // was chosen from a profile that has just stopped being true, and a
    // `NavHost` cannot change its start destination underneath somebody. So the
    // activity is rebuilt rather than the route.
    LaunchedEffect(restart) {
        if (restart) context.findActivity()?.recreate()
    }

    NightSky(config = SkyConfig(seed = 4, motes = 1, comet = false)) {
        StateHost(state, onRetry = vm::reload) { settings ->
            SettingsBody(
                settings = settings,
                vm = vm,
                daily = daily,
                dailyContacts = dailyContacts,
                container = container,
                onSignIn = onSignIn,
                onOffer = onOffer,
            )
        }
    }
}

@Composable
private fun SettingsBody(
    settings: SettingsView,
    vm: SettingsViewModel,
    daily: DailyState,
    dailyContacts: List<DailyContact>,
    container: AppContainer,
    onSignIn: () -> Unit,
    onOffer: () -> Unit,
) {
    val isGuest = settings.account?.isGuest != false
    val email = settings.account?.email.orEmpty()
    // **The name they gave, wherever they gave it.** The journey writes the
    // name onto the *profile*, because that is what a chart is written for; a
    // sign-in writes it onto the account. Reading both, profile first, says
    // the true thing — a person who typed their name on the second screen of
    // the journey is not "Guest".
    val displayName = settings.profile?.name?.trim()?.takeIf { it.isNotEmpty() }
        ?: settings.account?.displayName
        ?: email.substringBefore('@').takeIf { it.isNotBlank() }
        ?: ""

    CabinetPage {
        ScreenTitle(stringResource(R.string.settings_title))

        Spacer(Modifier.height(18.dp))
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            Box(
                modifier = Modifier
                    .size(46.dp)
                    .border(1.dp, AlmaPalette.HairlineGold, PillShape),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    // "·" rather than a letter, for a guest who has no name. An
                    // initial invented from an email they have not given would
                    // be the first fabricated thing on the screen.
                    text = displayName.firstOrNull()?.uppercase() ?: "·",
                    style = AlmaTheme.type.headingM,
                    color = AlmaPalette.Gold,
                )
            }
            Column {
                if (displayName.isNotBlank()) {
                    Text(text = displayName, style = AlmaTheme.type.headingM)
                }
                if (email.isNotBlank()) {
                    Text(text = email, style = AlmaTheme.type.meta)
                }
            }
        }

        Spacer(Modifier.height(30.dp))
        BirthData(settings)

        // Above the plan and the legal doors, below the birth data.
        //
        // It is the only thing on this screen that changes what the app *does*
        // rather than describing what it holds, and it is the one a person
        // arrives here looking for after a notification they did not want — so
        // it is above the fold rather than under four sections of export,
        // deletion and imprint links. `THE-DAILY.md §5`: anything that cannot be
        // turned off in one tap is a defect.
        Spacer(Modifier.height(30.dp))
        DailySettings(
            state = daily,
            contacts = dailyContacts,
            onChoose = container.daily::choose,
            onHour = container.daily::setHour,
            onOffer = onOffer,
        )

        // The «Письма» section stood here and is gone on both platforms: it
        // described our mail arrangements to somebody who opened Settings to
        // change something, and there was nothing in it to change. See the
        // longer note in the iOS `SettingsScreen`.

        Spacer(Modifier.height(30.dp))
        Language(settings, vm)

        Spacer(Modifier.height(30.dp))
        Plan(settings, vm, onOffer)

        Spacer(Modifier.height(30.dp))
        MeasurementSwitch(vm)

        Spacer(Modifier.height(30.dp))
        DataAndLegal(settings, vm, onSignIn)

        Spacer(Modifier.height(30.dp))
        Text(text = stringResource(R.string.settings_fine_print), style = AlmaTheme.type.meta)
        Text(
            text = stringResource(R.string.settings_disclaimer),
            style = AlmaTheme.type.meta,
            color = AlmaPalette.Muted3,
            modifier = Modifier.padding(top = 8.dp),
        )

        Spacer(Modifier.height(20.dp))
        if (isGuest) {
            Text(text = stringResource(R.string.settings_guest_note), style = AlmaTheme.type.meta)
            Spacer(Modifier.height(12.dp))
            QuietButton(text = stringResource(R.string.nav_sign_in), onClick = onSignIn)
        } else {
            QuietButton(
                text = stringResource(R.string.settings_sign_out),
                onClick = vm::signOut,
                contentColor = AlmaPalette.Muted,
            )
        }

        Spacer(Modifier.height(36.dp))
    }
}

/* ── what Alma holds ───────────────────────────────────────────────────── */

/**
 * The birth data, exactly as it is.
 *
 * An unset field shows nothing rather than borrowing a value from somewhere, so
 * a person can tell at a glance what Alma actually has. The time row is the one
 * that says something instead of staying blank, because "unknown" is a real
 * answer there and the difference between a known minute and an assumed one
 * decides what five of the eight systems are allowed to say.
 */
@Composable
private fun BirthData(settings: SettingsView) {
    val me = settings.profile
    RuledLabel(stringResource(R.string.settings_birth_data))
    val rows = listOf(
        stringResource(R.string.settings_date) to readableDate(me?.birthDate),
        stringResource(R.string.settings_time) to (
            me?.birthTime?.let { "$it · ${me.timezone}" }
                ?: if (me != null) stringResource(R.string.settings_unknown_time) else ""
            ),
        stringResource(R.string.settings_place) to me?.placeLabel.orEmpty(),
        stringResource(R.string.settings_full_name) to me?.name.orEmpty(),
    )
    rows.forEachIndexed { index, (label, value) ->
        CabinetRow(rule = index < rows.lastIndex) {
            Text(text = label, style = AlmaTheme.type.meta, modifier = Modifier.weight(1f))
            Text(text = value, style = AlmaTheme.type.positions)
        }
    }
}

/* ── language ──────────────────────────────────────────────────────────── */

/**
 * The seven languages, named in themselves.
 *
 * A language picker that translates its own entries is a picker somebody who
 * cannot read the current language cannot use. These are endonyms and they stay
 * out of the string table for that reason.
 */
private data class LanguageOption(val code: String, val tag: String, val name: String)

private val Languages = listOf(
    LanguageOption("en", "en", "English"),
    LanguageOption("es", "es", "Español"),
    LanguageOption("de", "de", "Deutsch"),
    LanguageOption("it", "it", "Italiano"),
    LanguageOption("fr", "fr", "Français"),
    LanguageOption("pt-BR", "pt-BR", "Português"),
    LanguageOption("ru", "ru", "Русский"),
)

@Composable
private fun Language(settings: SettingsView, vm: SettingsViewModel) {
    val context = LocalContext.current
    val current = settings.account?.locale ?: "en"
    // Per-app language exists in the framework from API 33. Below it there is no
    // way to change the interface's language without `appcompat`, which this app
    // does not depend on and which would arrive with an entire second widget
    // toolkit. So the picker always sets the language Alma *writes* in — the
    // load-bearing half — and says plainly that the interface follows the phone
    // on older devices, rather than appearing to do something it cannot.
    val switchesInterface = Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU

    RuledLabel(stringResource(R.string.settings_language))
    FlowRow(
        modifier = Modifier.fillMaxWidth().padding(top = 14.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Languages.forEach { language ->
            val selected = language.code.equals(current, ignoreCase = true)
            Box(
                modifier = Modifier
                    .border(
                        width = 1.dp,
                        color = if (selected) AlmaPalette.Gold else AlmaPalette.Hairline,
                        shape = PillShape,
                    )
                    .clickable(role = Role.RadioButton) {
                        vm.setLocale(language.code)
                        if (switchesInterface) context.setApplicationLanguage(language.tag)
                    }
                    .padding(horizontal = 16.dp, vertical = 10.dp),
            ) {
                Text(
                    text = language.name,
                    style = AlmaTheme.type.meta,
                    color = if (selected) AlmaPalette.GoldBright else AlmaPalette.Muted,
                )
            }
        }
    }
    // «Я читаю и пишу на языке твоего телефона» is gone here too: the row above
    // shows the language and changes it, and a paragraph saying that a language
    // setting sets the language is a sentence written for its own sake.
}

/* ── the plan ──────────────────────────────────────────────────────────── */

@Composable
private fun Plan(settings: SettingsView, vm: SettingsViewModel, onOffer: () -> Unit) {
    val cancelling by vm.cancelling.collectAsStateWithLifecycle()
    val context = LocalContext.current

    RuledLabel(stringResource(R.string.settings_plan))
    Spacer(Modifier.height(14.dp))

    // A plan is a grant that was not bought outright, asked of the row rather
    // than of a shape: both recurring products are stored against `system: "*"`,
    // so matching on that once told a monthly subscriber they held the annual
    // plan. `kind` is what tells them apart, and it is also what names and
    // prices the row below.
    val subscription = settings.held.firstOrNull { it.active && it.kind != "one_time" }
    val owned = settings.held.filter { it.active && it.system != "*" }
    // A plan that has run out is worth saying out loud. Showing only "Free" to
    // somebody who paid last year reads as the record having been lost rather
    // than the year being over.
    val lapsed = if (subscription == null) {
        settings.held.firstOrNull { !it.active && it.kind != "one_time" }
    } else {
        null
    }

    if (subscription != null) {
        val sold = settings.plans[subscription.kind]
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = planName(subscription.kind, sold?.name),
                style = AlmaTheme.type.headingM,
                modifier = Modifier.weight(1f),
            )
            sold?.display?.takeIf { it.isNotBlank() }?.let {
                Text(text = it, style = AlmaTheme.type.positions)
            }
        }

        // "Renews" only while it does. Once `renews_at` is gone the plan is
        // still open and still paid for, and saying it renews would tell
        // somebody who has just cancelled that the cancellation did not take —
        // and the next thing they do is a chargeback.
        val note = when {
            subscription.renewsAt != null && settings.account?.email.isNullOrBlank() ->
                // `renewals.due` skips an account with no address, which a guest
                // who bought without signing in has. Promising the warning
                // loudest to the person least likely to get it is how somebody
                // is charged a year later having read that this could not happen.
                stringResource(R.string.settings_renews_no_email, readableDate(subscription.renewsAt))
            subscription.renewsAt != null ->
                stringResource(R.string.settings_renews, readableDate(subscription.renewsAt))
            subscription.expiresAt != null ->
                stringResource(R.string.settings_runs_until, readableDate(subscription.expiresAt))
            else -> null
        }
        if (note != null) {
            Text(text = note, style = AlmaTheme.type.meta, modifier = Modifier.padding(top = 8.dp))
        }

        Spacer(Modifier.height(16.dp))
        // Always offered, whatever the catalogue says, because a subscription
        // bought through this app belongs to a Google account and Play's own
        // screen is the only place it can be stopped. An app that sells
        // subscriptions through Play and does not link here fails review.
        QuietButton(
            text = stringResource(R.string.settings_manage_in_play),
            onClick = { context.openPlaySubscriptions(subscription.kind) },
        )
        Text(
            text = stringResource(R.string.settings_manage_note),
            style = AlmaTheme.type.meta,
            color = AlmaPalette.Muted3,
            modifier = Modifier.padding(top = 10.dp),
        )

        // And the server-side cancel, only where the server can actually honour
        // it: `manage_url` is filled in by the store adapters, so an empty one
        // means the live processor is ours and `/subscription/cancel` will stop
        // the charge. Where it is set, the same endpoint answers 409 with this
        // very URL, and a button that has to apologise is worse than no button.
        if (settings.manageUrl.isBlank() && subscription.renewsAt != null) {
            Spacer(Modifier.height(16.dp))
            Cancel(cancelling, vm)
        }
    } else {
        Text(
            text = if (owned.isEmpty()) {
                stringResource(R.string.settings_free_plan)
            } else {
                stringResource(R.string.settings_owned_plan)
            },
            style = AlmaTheme.type.headingM,
        )
        Text(
            text = if (owned.isEmpty()) {
                stringResource(R.string.settings_free_note)
            } else {
                stringResource(R.string.cabinet_one_time_note)
            },
            style = AlmaTheme.type.meta,
            modifier = Modifier.padding(top = 8.dp),
        )
        lapsed?.expiresAt?.let {
            Text(
                text = stringResource(R.string.settings_plan_ended, readableDate(it)),
                style = AlmaTheme.type.meta,
                modifier = Modifier.padding(top = 8.dp),
            )
        }

        // The cheapest high-intent visitor this app will ever have is somebody
        // who opened Settings to look at their plan — and the free state used
        // to *describe* the plan with nothing to tap.
        Spacer(Modifier.height(16.dp))
        QuietButton(
            text = stringResource(R.string.plans_cta),
            onClick = onOffer,
            contentColor = AlmaPalette.GoldBright,
        )
    }

    if (owned.isNotEmpty()) {
        Spacer(Modifier.height(18.dp))
        owned.forEachIndexed { index, held ->
            CabinetRow(rule = index < owned.lastIndex) {
                Text(
                    text = heldName(held, settings),
                    style = AlmaTheme.type.meta,
                    modifier = Modifier.weight(1f),
                )
                Text(text = readableDate(held.grantedAt), style = AlmaTheme.type.positions)
            }
        }
    }
}

/**
 * The two taps the subscription-terms page promises, in the order it promises
 * them: what cancelling does, then the button that does it.
 */
@Composable
private fun Cancel(cancelling: CancelState, vm: SettingsViewModel) {
    val context = LocalContext.current
    when (cancelling) {
        is CancelState.Idle -> QuietButton(
            text = stringResource(R.string.settings_cancel_subscription),
            onClick = vm::askToCancel,
            contentColor = AlmaPalette.Disagree,
        )

        is CancelState.Confirming, is CancelState.Working -> {
            Text(text = stringResource(R.string.settings_cancel_what), style = AlmaTheme.type.meta)
            Spacer(Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                QuietButton(
                    text = if (cancelling is CancelState.Working) {
                        stringResource(R.string.settings_cancelling)
                    } else {
                        stringResource(R.string.settings_cancel_subscription)
                    },
                    onClick = vm::cancelSubscription,
                    enabled = cancelling is CancelState.Confirming,
                    contentColor = AlmaPalette.Disagree,
                )
                QuietButton(
                    text = stringResource(R.string.settings_keep_plan),
                    onClick = vm::keepPlan,
                    contentColor = AlmaPalette.Muted,
                )
            }
        }

        is CancelState.Cancelled -> Text(
            text = cancelling.accessUntil?.let {
                stringResource(R.string.settings_cancelled, readableDate(it))
            } ?: stringResource(R.string.settings_cancelled_no_date),
            style = AlmaTheme.type.meta,
        )

        // The store saying "not mine to cancel", which is not a failure at all:
        // the body carries a sentence written for a reader *and* the deep link
        // to the right row in Play. Both are used. This used to match on
        // `Unexpected(409)` and print the sentence, because the classifier had
        // no case for `cancel_at_store` and the URL was being discarded on the
        // way through — an app that says "cancel in Google Play" without opening
        // it fails the subscription-management guideline.
        is CancelState.Failed -> if (cancelling.failure is ApiFailure.CancelAtStore) {
            val manage = cancelling.failure.manageUrl
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(text = cancelling.failure.message, style = AlmaTheme.type.meta)
                QuietButton(
                    text = stringResource(R.string.settings_manage_in_play),
                    onClick = {
                        if (manage.isNotBlank()) context.openWeb(manage) else context.openPlaySubscriptions("")
                    },
                )
            }
        } else {
            Text(
                text = stringResource(R.string.settings_cancel_failed),
                style = AlmaTheme.type.meta,
                color = AlmaPalette.Disagree,
            )
        }
    }
}

/**
 * What to call the plan somebody is actually on, in their own language.
 *
 * The string table first, because this is the screen a person opens when they
 * are deciding whether to keep paying. The catalogue's own name is the fallback
 * rather than a hardcoded label, so a rung added to the ladder is named rather
 * than mislabelled as one of the two we happen to know about today.
 */
@Composable
private fun planName(kind: String, sold: String?): String = when (kind) {
    "annual" -> stringResource(R.string.settings_annual_plan)
    "monthly" -> stringResource(R.string.settings_everything_monthly)
    else -> sold ?: stringResource(R.string.settings_plan)
}

@Composable
private fun heldName(held: EntitlementDto, settings: SettingsView): String {
    val translated = systemName(held.system)
    // `systemName` answers the slug itself for anything it cannot name, which is
    // the point at which the catalogue's English name is better than nothing.
    return if (translated == held.system) settings.soldNames[held.system] ?: held.system else translated
}

/* ── data and the way out ──────────────────────────────────────────────── */

@Composable
private fun DataAndLegal(
    settings: SettingsView,
    vm: SettingsViewModel,
    onSignIn: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val exporting by vm.exporting.collectAsStateWithLifecycle()
    val deleting by vm.deleting.collectAsStateWithLifecycle()
    var pendingExport by remember { mutableStateOf<String?>(null) }

    // The system's own file picker, so the document lands wherever the person
    // keeps their documents. No `FileProvider`, no storage permission and no
    // app-private directory they would have to be told how to find.
    val saveFile = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("application/json")
    ) { uri: Uri? ->
        val json = pendingExport
        pendingExport = null
        if (uri == null || json == null) {
            vm.exportDismissed()
            return@rememberLauncherForActivityResult
        }
        scope.launch {
            val written = withContext(Dispatchers.IO) {
                runCatching {
                    context.contentResolver.openOutputStream(uri)?.use { stream ->
                        stream.write(json.toByteArray())
                    } ?: error("no stream")
                }.isSuccess
            }
            if (written) vm.exportSaved() else vm.exportFailed()
        }
    }

    LaunchedEffect(exporting) {
        val ready = exporting as? ExportState.Ready ?: return@LaunchedEffect
        pendingExport = ready.json
        saveFile.launch("alma-export.json")
    }

    RuledLabel(stringResource(R.string.settings_data_legal))

    ActionRow(stringResource(R.string.settings_export)) { vm.startExport() }
    when (exporting) {
        is ExportState.NeedsAccount -> NeedsAccount(onSignIn)
        is ExportState.Working -> Note(stringResource(R.string.settings_exporting))
        is ExportState.Saved -> Note(stringResource(R.string.settings_export_saved))
        is ExportState.Failed -> Note(stringResource(R.string.settings_export_failed))
        else -> Unit
    }

    // No `isGuest` here any more, and its absence is the fix. This used to open
    // a panel that said "This needs an account we can attach to you" with a
    // single Sign in button on it — to somebody whose birth date and birth
    // coordinates were already on our server, written there by the journey
    // before a sign-in screen existed. Play requires an in-app deletion route
    // from every app that creates an account, and "create a different kind of
    // account first" is not one; asking for an email address in order to remove
    // data taken without one is the pattern the policy exists to forbid.
    ActionRow(stringResource(R.string.settings_delete_account), danger = true) {
        vm.askToDelete()
    }
    when (deleting) {
        is DeleteState.Idle -> Unit
        else -> DeleteConfirm(settings, vm, deleting)
    }

    // The other half of "readily discoverable": a page a person can open from a
    // browser, signed out, without the app — which is also the URL Play Console
    // requires in App content → Data deletion.
    Spacer(Modifier.height(10.dp))
    Text(
        text = stringResource(R.string.settings_delete_page),
        style = AlmaTheme.type.meta,
        color = AlmaPalette.Gold,
        modifier = Modifier.clickable(role = Role.Button) {
            context.openWeb("$Site/delete-account")
        },
    )
    Text(
        text = stringResource(R.string.settings_delete_help),
        style = AlmaTheme.type.meta,
        color = AlmaPalette.Muted3,
        modifier = Modifier.padding(top = 8.dp),
    )

    Spacer(Modifier.height(22.dp))
    // Five documents, five routes. The labels are translated so the row reads in
    // the person's own language; the documents themselves are English until they
    // have been reviewed against the law of each country, which is the one place
    // a translation would do more harm than good.
    FlowRow(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        listOf(
            stringResource(R.string.legal_terms) to "terms",
            stringResource(R.string.legal_privacy) to "privacy",
            stringResource(R.string.legal_refunds) to "refunds",
            stringResource(R.string.legal_subscription_terms) to "subscription-terms",
            stringResource(R.string.legal_imprint) to "imprint",
        ).forEach { (label, path) ->
            Text(
                text = label,
                style = AlmaTheme.type.meta,
                color = AlmaPalette.Gold,
                modifier = Modifier.clickable(role = Role.Button) { context.openWeb("$Site/$path") },
            )
        }
    }
}

/**
 * The confirmation, which is the same comparison the backend makes.
 *
 * Doing it here as well keeps the button dim until the typing is right, rather
 * than failing after the tap on the one action in this app that cannot be
 * undone. The warning above it says what is actually lost: paid readings cannot
 * be written again word for word, because they were written once, from this
 * chart, and never from a template.
 */
@Composable
private fun DeleteConfirm(settings: SettingsView, vm: SettingsViewModel, deleting: DeleteState) {
    var typed by remember { mutableStateOf("") }

    // What this account can actually be asked for. An address if it has one;
    // otherwise its own id, which a guest has and a stranger does not, and which
    // needs no translation. The server makes the identical comparison.
    val email = settings.account?.email?.takeIf { it.isNotBlank() }
    val expected = email ?: settings.account?.userId
    val matches = !expected.isNullOrBlank() &&
        typed.trim().lowercase() == expected.trim().lowercase()

    Spacer(Modifier.height(14.dp))
    Text(text = stringResource(R.string.settings_delete_warning), style = AlmaTheme.type.meta)

    // The id is shown *because* it is what has to be typed. A confirmation
    // string a person cannot see is not a confirmation, it is a lockout.
    if (email == null && expected != null) {
        Spacer(Modifier.height(14.dp))
        // A guest has no email to type; what they have is the account code,
        // and the ask has to say so rather than demand an address that does
        // not exist.
        Text(
            text = stringResource(R.string.settings_delete_guest_note),
            style = AlmaTheme.type.meta,
        )
        Spacer(Modifier.height(10.dp))
        Text(
            text = stringResource(R.string.settings_account_id),
            style = AlmaTheme.type.overline,
            color = AlmaPalette.Muted3,
        )
        Text(
            text = expected,
            style = AlmaTheme.type.positions.copy(fontSize = 15.sp),
            modifier = Modifier.padding(top = 4.dp),
        )
    }

    Spacer(Modifier.height(14.dp))
    val hint = stringResource(
        if (email == null) R.string.settings_delete_confirm_guest else R.string.settings_delete_confirm
    )
    Box(Modifier.fillMaxWidth()) {
        BasicTextField(
            value = typed,
            onValueChange = {
                typed = it
                vm.typingChanged()
            },
            singleLine = true,
            textStyle = AlmaTheme.type.meta.copy(color = AlmaPalette.Body, fontSize = 15.sp),
            cursorBrush = SolidColor(AlmaPalette.Gold),
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Email,
                imeAction = ImeAction.Done,
            ),
            modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp),
            decorationBox = { field ->
                Column {
                    if (typed.isEmpty()) {
                        Text(text = hint, style = AlmaTheme.type.meta, color = AlmaPalette.Muted3)
                    }
                    field()
                    Spacer(Modifier.height(8.dp))
                    Hairline()
                }
            },
        )
    }

    Spacer(Modifier.height(16.dp))
    // `FlowRow`, because a `Row` clipped the second button. "Delete everything,
    // permanently" beside "Keep my account" does not fit on a 1080 px screen in
    // English, let alone in German: the row gave the first button what it asked
    // for and the second whatever was left, which rendered as "Kee / p / my"
    // inside a pill. Seen on the emulator on the one panel where both choices
    // have to be legible.
    FlowRow(
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        QuietButton(
            text = if (deleting is DeleteState.Working) {
                stringResource(R.string.settings_deleting)
            } else {
                stringResource(R.string.settings_delete_forever)
            },
            onClick = { vm.deleteAccount(typed, expected) },
            enabled = matches && deleting !is DeleteState.Working,
            contentColor = AlmaPalette.Disagree,
        )
        QuietButton(
            text = stringResource(R.string.settings_keep_account),
            onClick = {
                typed = ""
                vm.keepAccount()
            },
            contentColor = AlmaPalette.Muted,
        )
    }

    when (deleting) {
        is DeleteState.Mismatch -> Note(
            stringResource(
                if (email == null) {
                    R.string.settings_delete_mismatch_id
                } else {
                    R.string.settings_delete_mismatch
                }
            ),
            AlmaPalette.Disagree,
        )
        is DeleteState.Failed -> Note(
            stringResource(R.string.settings_delete_failed),
            AlmaPalette.Disagree,
        )
        else -> Unit
    }
}

/**
 * The one switch on this screen, and the reason it is not a row of them.
 *
 * The web privacy policy promises that step labels are not recorded when a
 * browser sends Do Not Track or Global Privacy Control. There is no such signal
 * on Android, so without this control the app was offering an opt-out that did
 * not exist on the platform the reader was holding — and the Data safety form
 * had to declare App interactions as Required rather than Optional purely
 * because nothing could turn it off.
 *
 * `AlmaToggle` rather than Material's `Switch`, and the same one the birth-time
 * step uses: there is exactly one switch shape in this product.
 */
@Composable
private fun MeasurementSwitch(vm: SettingsViewModel) {
    val on by vm.measurement.collectAsStateWithLifecycle()
    val label = stringResource(R.string.settings_measurement)

    RuledLabel(label)
    Row(
        modifier = Modifier.fillMaxWidth().padding(top = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(
            text = stringResource(R.string.settings_measurement_note),
            style = AlmaTheme.type.meta,
            modifier = Modifier.weight(1f),
        )
        AlmaToggle(on = on, onChange = vm::setMeasurement, label = label)
    }
}

/** A row that does something, rather than reporting something. */
@Composable
private fun ActionRow(label: String, danger: Boolean = false, onClick: () -> Unit) {
    CabinetRow(onClick = onClick) {
        Text(
            text = label,
            style = AlmaTheme.type.meta.copy(fontSize = 15.sp),
            color = if (danger) AlmaPalette.Disagree else AlmaPalette.Body,
            modifier = Modifier.weight(1f),
        )
        Text(text = "→", style = AlmaTheme.type.positions, color = AlmaPalette.Muted3)
    }
}

/** The prompt a guest gets where an account is genuinely required. */
@Composable
private fun NeedsAccount(onSignIn: () -> Unit) {
    Column(
        modifier = Modifier.padding(vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(text = stringResource(R.string.settings_needs_account), style = AlmaTheme.type.meta)
        QuietButton(text = stringResource(R.string.nav_sign_in), onClick = onSignIn)
    }
}

@Composable
private fun Note(text: String, colour: Color = AlmaPalette.Muted) {
    Text(
        text = text,
        style = AlmaTheme.type.meta,
        color = colour,
        modifier = Modifier.padding(vertical = 12.dp),
    )
}

/* ── leaving the app ───────────────────────────────────────────────────── */

/** Where the five legal documents live. The same host the magic link uses. */
private const val Site = "https://alma.pazl.ai"

/**
 * Play's own subscription screen, deep-linked to this product where possible.
 *
 * The `sku` has to be the Play product id, which for the two plans is the same
 * word the catalogue uses. If it is anything else the link still opens — Play
 * falls back to the full list — which is why the parameter is added rather than
 * guarded behind a check that could leave somebody with no link at all.
 */
private fun Context.openPlaySubscriptions(kind: String) {
    openWeb(
        "https://play.google.com/store/account/subscriptions" +
            "?sku=$kind&package=$packageName"
    )
}

private fun Context.openWeb(url: String) {
    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
    // A device with no browser and no Play app is unusual and is not worth a
    // crash. Nothing is said about it because there is nothing the person could
    // do, and an error toast about a missing browser is noise.
    runCatching { startActivity(intent) }
        .onFailure { if (it !is ActivityNotFoundException) throw it }
}

/** The activity under whatever wrappers the theme and the locale put in the way. */
private tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}

/**
 * Switch the interface's language, from API 33 on.
 *
 * The framework restarts the activity for us, which is why nothing here has to.
 */
private fun Context.setApplicationLanguage(tag: String) {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
    getSystemService(LocaleManager::class.java)?.applicationLocales =
        LocaleList.forLanguageTags(tag)
}
