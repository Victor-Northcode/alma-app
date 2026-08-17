package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.ui.components.Overline
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaSpacing
import ai.pazl.alma.ui.theme.AlmaTheme
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale
import kotlin.math.abs

/**
 * The fork: which of the two identical times is yours.
 *
 * The clocks went back that night, so the wall clock the person gave happened
 * twice — both real, both giving a different sky. The server refuses to guess
 * and it is right to: a coin flipped here lands in the houses, in the solar
 * return and in a chart somebody is later asked to pay for.
 *
 * **This is an interrupt in the ceremony, not a step of the questionnaire.** It
 * can only arrive after "Build my sky", so it has no numeral — the overline says
 * what it is about instead, and the arrow leads back to the time step rather
 * than one screen back in a sequence this does not belong to. The beats behind
 * it pause; they do not restart.
 *
 * **The two options differ by their name, not by their time.** The time is the
 * same on both — that is the whole point — and what separates them is what the
 * clock was called that night. Those names come from the server: a phone has no
 * zone-history database to work them out from.
 */
@Composable
internal fun JourneyFork(
    fork: ApiFailure.AmbiguousTime,
    /** The wall clock the person typed, "02:30". Empty when they gave no time. */
    wallClock: String,
    city: String,
    onChoose: (String) -> Unit,
    onBack: () -> Unit,
) {
    // How far apart the two instants are, said in words. A hardcoded "an hour"
    // cannot stand here: half-hour transitions exist — Lord Howe Island and its
    // like — and there the sentence would simply be false.
    val delta = stringResource(
        if (abs(fork.gapHours ?: 1.0) < 0.75) R.string.journey_dst_delta_half_hour
        else R.string.journey_dst_delta_hour
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            // The question covers the scene rather than replacing it: the
            // ceremony lives on underneath, but two texts cannot be read at once.
            .background(AlmaPalette.Night800.copy(alpha = 0.96f))
            // And it swallows what it covers. Drawing on top is not the same as
            // being on top for a finger: without this the "skip the ceremony"
            // row underneath is still tappable through the question.
            .pointerInput(Unit) { detectTapGestures { } }
            .windowInsetsPadding(WindowInsets.safeDrawing)
            .padding(horizontal = AlmaSpacing.Pad),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Overline(stringResource(R.string.journey_dst_overline))
            val label = stringResource(R.string.nav_back)
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clickable(role = Role.Button, onClickLabel = label, onClick = onBack),
                contentAlignment = Alignment.Center,
            ) {
                Text(text = "←", style = TextStyle(fontSize = 19.sp, color = AlmaPalette.Gold))
            }
        }

        Spacer(Modifier.weight(1f))

        Text(
            text = stringResource(R.string.journey_dst_title, wallClock),
            style = AlmaTheme.type.displayL,
        )
        Text(
            text = stringResource(
                R.string.journey_dst_body, city, localDate(fork.transitionLocalDate), wallClock,
            ),
            style = AlmaTheme.type.meta,
            modifier = Modifier.padding(top = 18.dp),
        )

        Spacer(Modifier.height(26.dp))
        ForkChoice(
            title = stringResource(R.string.journey_dst_earlier),
            note = stringResource(
                R.string.journey_dst_earlier_sub, wallClock, fork.earlier?.abbreviation.orEmpty(),
            ),
            onClick = { onChoose("earlier") },
        )
        Spacer(Modifier.height(14.dp))
        ForkChoice(
            title = stringResource(R.string.journey_dst_later),
            note = stringResource(
                R.string.journey_dst_later_sub,
                wallClock,
                fork.later?.abbreviation.orEmpty(),
                delta,
            ),
            onClick = { onChoose("later") },
        )

        Spacer(Modifier.height(20.dp))
        // Whoever genuinely does not know needs a way through as well, and an
        // honest one: an hour moves the houses, it does not rewrite the chart.
        FinePrint(
            text = stringResource(R.string.journey_dst_footer, delta),
            align = TextAlign.Start,
        )

        Spacer(Modifier.weight(1f))
        Spacer(Modifier.height(24.dp))
    }
}

/** One of the two instants: the title in the serif, what tells it apart beneath. */
@Composable
private fun ForkChoice(title: String, note: String, onClick: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, AlmaPalette.Hairline, RoundedCornerShape(16.dp))
            .clickable(role = Role.Button, onClick = onClick)
            .padding(horizontal = 20.dp, vertical = 14.dp),
    ) {
        Text(text = title, style = AlmaTheme.type.headingM.copy(fontSize = 17.sp))
        Text(text = note, style = AlmaTheme.type.meta, modifier = Modifier.padding(top = 4.dp))
    }
}

/**
 * The night the clocks moved, written the way this locale writes a date.
 *
 * The server sends "1992-09-27". Showing a reader ISO is showing them the
 * machine; an unparseable or absent value is shown as it came rather than
 * replaced with a date nobody named.
 */
private fun localDate(raw: String): String = runCatching {
    LocalDate.parse(raw).format(
        DateTimeFormatter.ofLocalizedDate(FormatStyle.LONG).withLocale(Locale.getDefault())
    )
}.getOrDefault(raw)
