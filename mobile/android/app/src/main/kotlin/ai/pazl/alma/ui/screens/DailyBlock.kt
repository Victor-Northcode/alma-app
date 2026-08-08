package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.notify.DailyContact
import ai.pazl.alma.notify.DailyPreference
import ai.pazl.alma.notify.DailyRule
import ai.pazl.alma.ui.components.QuietButton
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.unit.dp
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale

/**
 * The daily, on Today, for everybody.
 *
 * **The push is a reminder; this is the product.** A person who never allows
 * notifications, or whose phone cannot receive one, still gets the whole of it —
 * and so does a free reader, because `alma/api/routers/systems.py` returns the
 * transits payload whole even when the system is locked. The arithmetic below is
 * available to everyone the same way the rest of Today's calculations are; what
 * a subscription buys is the notification, not the day.
 *
 * It cites its event the way every other screen in this app cites its factors:
 * the notation a chart prints, the natal placement it is read against, the
 * instant it perfects, and the window it has been live for. That is the
 * difference `alma/engine/transits.py`'s own docstring draws — *"'Sun' is a
 * horoscope; 'Saturn squares your Sun exactly on 14 June, in orb from…' is a
 * reading"* — and it is the whole argument for this feature existing.
 *
 * And it says nothing on a day with nothing in it. `THE-DAILY.md §1` measured
 * 22 to 46 such days a year at the honest threshold; a block that produced a
 * sentence on all of them would be a horoscope with extra steps.
 */
@Composable
internal fun DailyBlock(
    contacts: List<DailyContact>,
    /**
     * Whether the chart lost its angles for want of a birth time.
     *
     * A chart with no birth time is measurably thinner — no Ascendant and no
     * Midheaven, two of the five natal points carrying full weight, and about
     * 65 empty days a year against 0–20 for the others — and no design fixes
     * that. It is said rather than silently serving less.
     */
    missingBirthTime: Boolean,
) {
    val zone = rememberZone()
    val today = LocalDate.now(zone)
    // Always `OCCASIONALLY` here, and never the person's own position: the
    // screen shows what the day holds, and somebody who chose "only what
    // matters" for their *notifications* has not asked to be shown less when
    // they open the app on purpose.
    val event = DailyRule.candidates(contacts, today, DailyPreference.OCCASIONALLY, zone).firstOrNull()

    RuledLabel(stringResource(R.string.daily_today_label))

    if (event == null) {
        // Silence, said out loud. This is the state the whole feature is built
        // to make survivable, and it is drawn with as much care as the other
        // one: "Nothing is exact today" is an answer — it is what an ephemeris
        // says about most days — and the line under it points at the contacts
        // that *are* live, which the section below already lists.
        Column(Modifier.padding(top = 14.dp)) {
            Text(
                text = stringResource(R.string.daily_empty_title),
                style = AlmaTheme.type.headingM,
            )
            Text(
                // The count is the consolation: a quiet day is not an empty
                // chart, and the influences still running are the proof.
                text = stringResource(R.string.daily_empty_body, contacts.size),
                style = AlmaTheme.type.meta,
                modifier = Modifier.padding(top = 6.dp),
            )
            if (missingBirthTime) {
                // Not the same silence. Without a birth time there is no
                // Ascendant and no Midheaven to be crossed, so some of these
                // empty days are empty because we were never told the hour —
                // and saying so is the difference between a quiet sky and a
                // thinner chart.
                Text(
                    text = stringResource(R.string.error_needs_birth_time),
                    style = AlmaTheme.type.meta,
                    color = AlmaPalette.Muted3,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
        }
        return
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 14.dp)
            // The engine's own sentence, read out instead of three glyphs.
            // English in every locale, which is the lesser evil: the alternative
            // is a screen reader spelling out "♂ □ ASC".
            .clearAndSetSemantics { contentDescription = event.spoken },
    ) {
        // Notation, large, in the serif. The engine names its bodies in English
        // in every locale, so two glyphs say in all six languages what fourteen
        // translated planet names would — the same decision the transit rows
        // already make.
        Text(text = event.notation(BodyGlyphs), style = AlmaTheme.type.displayXl)

        // The instant. This is the line that makes it a reading rather than a
        // horoscope, so it gets its own row in gold rather than being joined
        // into a meta string with everything else.
        event.exact?.let { exact ->
            val time = exact.atZone(zone).toLocalTime()
                .format(DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT).withLocale(Locale.getDefault()))
            Text(
                text = stringResource(R.string.daily_today_at, time),
                style = AlmaTheme.type.positions,
                color = AlmaPalette.GoldBright,
                modifier = Modifier.padding(top = 8.dp),
            )
        }

        // The window. Both halves are optional and for different reasons: a
        // contact already in orb when the scan began has no `enters`, and one
        // still in orb at the end of the window has no `leaves`. Neither is
        // invented — an absent edge simply does not print.
        // The reader's own calendar day, not the instant's UTC one.
        // `dayAndMonth` reads an ISO date out of the string it is given, so what
        // it is given has to already be in the device's zone — the alternative
        // is a window that says "8 August" to somebody for whom it is the 9th,
        // on the screen whose whole argument is that its dates are exact.
        val since = event.enters?.let {
            stringResource(
                R.string.daily_today_since,
                dayAndMonth(it.atZone(zone).toLocalDate().toString()).orEmpty(),
            )
        }
        val until = event.leaves?.let {
            stringResource(
                R.string.daily_today_until,
                dayAndMonth(it.atZone(zone).toLocalDate().toString()).orEmpty(),
            )
        }
        val window = listOfNotNull(since, until).joinToString(", ")
        if (window.isNotBlank()) {
            Text(
                text = window,
                style = AlmaTheme.type.meta,
                modifier = Modifier.padding(top = 6.dp),
            )
        }

        Text(
            text = formatOrb(event.orbNow),
            style = AlmaTheme.type.meta,
            modifier = Modifier.padding(top = 4.dp),
        )
    }
}

/**
 * The invitation, and the second entrance to the setting.
 *
 * `docs/PUSH.md §5.2` is specific that a switch reachable only from a settings
 * list is a switch nobody finds, and that the second entrance belongs on the
 * surface the content is on, worded as what it is: *tell me the morning it
 * happens*. This is that.
 *
 * **On Android this card is the pre-prompt, and it is not optional.** There is
 * no provisional mode here: after a `POST_NOTIFICATIONS` denial the system does
 * not ask again until the app is reinstalled or its target SDK is raised. So
 * our question — which explains what will arrive and how often, is in six
 * languages, and can be asked again next month — goes first, every time, and
 * the platform's is launched only from [onYes]. `PUSH.md §5.5`.
 */
@Composable
internal fun DailyInvitation(onYes: () -> Unit, onNo: () -> Unit) {
    Column(Modifier.fillMaxWidth().padding(top = 30.dp)) {
        Text(text = stringResource(R.string.daily_ask_title), style = AlmaTheme.type.headingM)
        Text(
            text = stringResource(R.string.daily_ask_body),
            style = AlmaTheme.type.meta,
            modifier = Modifier.padding(top = 8.dp),
        )
        Spacer(Modifier.height(14.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            QuietButton(text = stringResource(R.string.daily_ask_yes), onClick = onYes)
            // Declining is one tap and costs nothing, because it is *our*
            // question rather than the platform's. That asymmetry is the whole
            // reason to ask ours first: a person who taps this and changes their
            // mind next month has the same one tap waiting in Settings, where
            // somebody who denies the system dialog has to go digging through
            // Android's own settings tree instead.
            QuietButton(
                text = stringResource(R.string.daily_ask_no),
                onClick = onNo,
                contentColor = AlmaPalette.Muted,
            )
        }
    }
}

/**
 * The device's zone, resolved once per composition.
 *
 * A tiny helper with a real job: `ZoneId.systemDefault()` reads a system
 * property on every call, and this is inside a list that recomposes.
 */
@Composable
private fun rememberZone(): ZoneId = remember { ZoneId.systemDefault() }
