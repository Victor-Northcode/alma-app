package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.notify.DailyClockSource
import ai.pazl.alma.notify.DailyContact
import ai.pazl.alma.notify.DailyPreference
import ai.pazl.alma.notify.DailyRule
import ai.pazl.alma.notify.DailyState
import ai.pazl.alma.notify.DailyStore
import ai.pazl.alma.ui.components.QuietButton
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import ai.pazl.alma.ui.theme.PillShape
import android.content.Context
import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale
import java.util.TimeZone

/**
 * The control, in Settings, in one tap from anywhere.
 *
 * **Everything this section claims has to be true, and most of it is checked
 * rather than asserted.** That is not general good practice here, it is specific
 * history — and the note at the top of `SettingsScreen.kt` is the record of it:
 * the web app once shipped four notification toggles, three of them defaulted
 * on, for letters no sender existed for. They were removed. This is the same
 * feature built the other way round: every line below is derived from something
 * observable, and the one claim that cannot be — the weekly cadence, measured on
 * 24 charts that are not this reader's — is put next to a count taken from the
 * reader's own chart.
 */
@Composable
internal fun DailySettings(
    state: DailyState,
    /**
     * The transits, when Today has fetched them. Empty is a supported state:
     * the counted row is simply omitted rather than showing a number this
     * screen has not computed.
     */
    contacts: List<DailyContact>,
    onChoose: (DailyPreference) -> Unit,
    onHour: (Int) -> Unit,
    onOffer: () -> Unit,
) {
    val context = LocalContext.current

    RuledLabel(stringResource(R.string.daily_title))

    // Three positions, as pills, matching the language picker directly below —
    // one control, three states, no on/off switch anywhere near it. A `Switch`
    // would say this is binary, and the whole argument of `THE-DAILY.md §5.1`
    // is that it is not: the distance between "about once a week" and "a few
    // times a year" is what stands between a quieter subscriber and an
    // uninstall.
    FlowRow(
        modifier = Modifier.fillMaxWidth().padding(top = 14.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        DailyPreference.entries.forEach { position ->
            val selected = state.preference == position
            Box(
                modifier = Modifier
                    .border(
                        width = 1.dp,
                        color = if (selected) AlmaPalette.Gold else AlmaPalette.Hairline,
                        shape = PillShape,
                    )
                    .clickable(role = Role.RadioButton) {
                        // A free reader gets the door, not a broken switch.
                        // `THE-DAILY.md §5.1` puts the paywall exactly here: the
                        // Today page and every calculation on it stay free, and
                        // what is being sold is the living layer arriving
                        // unprompted.
                        if (!state.isSubscriber && position != DailyPreference.OFF) {
                            onOffer()
                        } else {
                            onChoose(position)
                        }
                    }
                    .padding(horizontal = 16.dp, vertical = 10.dp),
            ) {
                Text(
                    text = stringResource(position.title),
                    style = AlmaTheme.type.meta,
                    color = if (selected) AlmaPalette.GoldBright else AlmaPalette.Muted,
                )
            }
        }
    }

    // One detail line, for whichever position is selected, rather than three
    // stacked under three pills. Three would leave "No notifications. Today is
    // still here whenever you open it" permanently on screen beside two others,
    // and the reason those three sentences exist is to be read at the moment of
    // choosing — which is when this one changes.
    Text(
        text = stringResource(state.preference.detail),
        style = AlmaTheme.type.meta,
        modifier = Modifier.padding(top = 12.dp),
    )

    Status(state, context, onOffer)

    if (state.preference.wantsDelivery && state.isSubscriber) {
        Spacer(Modifier.height(18.dp))
        Arrival(state, onHour)
        Verified(state, contacts)
    }
}

/**
 * The honest answer to "will anything arrive".
 *
 * Four states, and they are genuinely different situations rather than four ways
 * of saying the same thing:
 *
 * * **not a subscriber** — the daily is part of the plan, and Today is not.
 * * **denied or silenced** — Android said no, or the channel was turned off in
 *   the system's own settings. Said once, never nagged, with the one action that
 *   can undo it. `PUSH.md §5.5(3)`.
 * * **not delivering** — permitted, but no server has accepted a token. This is
 *   the state every build is in today, because the route in `PUSH.md §3` is a
 *   contract nobody has implemented and `PushTokens` explains at length why
 *   Firebase is not wired yet. Saying so is the whole reason this block exists.
 * * **registered** — arriving.
 */
@Composable
private fun Status(state: DailyState, context: Context, onOffer: () -> Unit) {
    when {
        !state.isSubscriber && state.preference.wantsDelivery ->
            Note(stringResource(R.string.daily_subscriber_only))

        state.preference == DailyPreference.OFF -> Unit

        !state.permitted || state.channelSilenced -> {
            Note(stringResource(R.string.daily_status_denied))
            Spacer(Modifier.height(12.dp))
            QuietButton(
                text = stringResource(R.string.daily_status_open_settings),
                onClick = {
                    // The app's own notification page, not the generic settings
                    // list. `ACTION_APP_NOTIFICATION_SETTINGS` lands on the
                    // screen with the channels on it, which is where somebody
                    // who silenced only the daily has to go — a generic
                    // "settings" link makes them hunt, and a person hunting
                    // through system settings to fix our notification is a
                    // person about to uninstall instead.
                    context.startActivity(
                        Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                            .putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName)
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    )
                },
            )
        }

        // «Пока ничего не отправляется. Этот телефон не зарегистрирован…» was
        // here and is gone on both platforms: it explains our plumbing to
        // somebody who came for a switch, and the daily appears on Today either
        // way.
        !state.deliverable -> Unit

        else -> Note(stringResource(R.string.daily_status_registered))
    }
}

@Composable
private fun Note(text: String) {
    Text(text = text, style = AlmaTheme.type.meta, modifier = Modifier.padding(top = 12.dp))
}

/**
 * The hour, the quiet hours, and where the clock came from.
 *
 * The hour is editable because "I get up at 05:30" is a real fact about a person
 * and the only one they can tell us that we cannot measure. The quiet hours are
 * shown and not editable, which is the point of showing them — it tells the
 * person we thought about it, where making them editable invites somebody to set
 * 03:00 and then complain about a 03:00 notification.
 */
@Composable
private fun Arrival(state: DailyState, onHour: (Int) -> Unit) {
    // The eligible hours as pills rather than a time picker. A picker's minutes
    // are a precision we do not have — the job runs hourly — and offering them
    // would be claiming one.
    RuledLabel(stringResource(R.string.daily_hour))
    FlowRow(
        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        (DailyStore.QUIET_UNTIL until DailyStore.QUIET_FROM).forEach { hour ->
            val selected = state.hour == hour
            Box(
                modifier = Modifier
                    .border(
                        width = 1.dp,
                        color = if (selected) AlmaPalette.Gold else AlmaPalette.Hairline,
                        shape = PillShape,
                    )
                    .clickable(role = Role.RadioButton) { onHour(hour) }
                    .padding(horizontal = 12.dp, vertical = 8.dp),
            ) {
                Text(
                    text = formattedHour(hour),
                    style = AlmaTheme.type.meta,
                    color = if (selected) AlmaPalette.GoldBright else AlmaPalette.Muted,
                )
            }
        }
    }

    Text(
        text = stringResource(R.string.daily_quiet),
        style = AlmaTheme.type.meta,
        modifier = Modifier.padding(top = 12.dp),
    )

    // The zone, **and where it came from**.
    //
    // Showing the source is what makes the override discoverable to exactly the
    // person who needs it. Somebody born in Lisbon and living in Toronto whose
    // notifications land at 03:00 will look here first, and "Lisbon — from your
    // birth data" tells them in one line what is wrong; a bare "Lisbon" tells
    // them the app is broken.
    //
    // Today it always reads *from your device*, because the device's own zone is
    // what `SessionInterceptor` sends on every request and no override is stored
    // anywhere yet. The other two labels exist and are translated, waiting for
    // `alma/auth/accounts.py` to grow the field `THE-DAILY.md §6.8` asks it
    // for — a workflow that owns that file, not this one.
    CabinetRow(rule = false) {
        Text(
            text = stringResource(R.string.daily_timezone),
            style = AlmaTheme.type.meta,
            modifier = Modifier.weight(1f),
        )
        Column {
            Text(text = TimeZone.getDefault().id, style = AlmaTheme.type.positions)
            Text(
                text = stringResource(DailyClockSource.DEVICE.label),
                style = AlmaTheme.type.meta,
                color = AlmaPalette.Muted3,
            )
        }
    }
}

/**
 * The cadence promise, verified as far as a client honestly can.
 *
 * The detail line above says *about once a week*. That number is real —
 * `THE-DAILY.md §4.2` simulated the rule over 24 charts for a year and published
 * the whole distribution — but it is a number about 24 people who are not this
 * reader, produced by a rule this app cannot watch running, because the job that
 * will run it does not exist yet.
 *
 * What *can* be checked is this chart, on this phone, with this rule: the count
 * below applies [DailyRule] to the transits Today already fetched and says how
 * many of the next thirty days have something exact in them. It is a **lower
 * bound** — the server sends at most sixty future contacts, so a dense month can
 * hide days from it — and it is offered as what it is rather than as a promise.
 */
@Composable
private fun Verified(state: DailyState, contacts: List<DailyContact>) {
    if (contacts.isEmpty()) return
    val zone = remember { ZoneId.systemDefault() }
    val days = remember(contacts, state.preference) {
        DailyRule.exactDays(contacts, LocalDate.now(zone), 30, state.preference, zone)
    }
    CabinetRow(rule = false) {
        Text(
            text = stringResource(R.string.daily_verified_label),
            style = AlmaTheme.type.meta,
            modifier = Modifier.weight(1f),
        )
        Text(text = days.toString(), style = AlmaTheme.type.positions)
    }
    // The sentence under the number — «Посчитано из твоей собственной карты, на
    // этом устройстве, по тому же правилу…» — is gone on both platforms. It
    // defended a figure nobody had doubted, in the vocabulary of the people who
    // wrote it.
}

/**
 * "08:00", in the reader's own locale, from one integer — so a US phone reads
 * "8 AM" and a German one "08:00" without two strings existing.
 */
private fun formattedHour(hour: Int): String =
    LocalTime.of(hour, 0).format(
        DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT).withLocale(Locale.getDefault())
    )
