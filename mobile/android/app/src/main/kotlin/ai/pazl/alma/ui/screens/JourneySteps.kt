package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.core.ScreenState
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.data.dto.PlaceDto
import ai.pazl.alma.ui.components.AlmaHaptics
import ai.pazl.alma.ui.components.AlmaPresence
import ai.pazl.alma.ui.components.FailureNotice
import ai.pazl.alma.ui.components.GoldButton
import ai.pazl.alma.ui.components.Hairline
import ai.pazl.alma.ui.components.Overline
import ai.pazl.alma.ui.components.QuietButton
import ai.pazl.alma.ui.components.Waiting
import ai.pazl.alma.ui.theme.AlmaFonts
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import ai.pazl.alma.ui.theme.PillShape
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.isImeVisible
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.delay
import java.time.Year

/**
 * The eight steps.
 *
 * Each one is a `@Composable` that reads the draft and calls the `ViewModel`.
 * None of them fetches anything: the ceremony *asks* the `ViewModel` to begin,
 * and the `ViewModel` decides whether that has already happened. A
 * `LaunchedEffect` that made the request itself would re-fire on a configuration
 * change and save the birth twice.
 */

/* ══ I · a name is not an account ═════════════════════════════════════ */

/**
 * A name, and the sentence under it is doing real work: nothing has been sent
 * anywhere yet, and saying so is what makes the field feel like a greeting
 * rather than the first half of a registration form.
 *
 * The web app puts a "continue with Google" button here that only advances the
 * step — it signs nobody in. It is deliberately not reproduced: a control that
 * looks like an account and is not one is the same lie as a pre-filled birthday,
 * and sign-in on Android has its own screen once the ID token is wired up.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun ColumnScope.NameStep(
    draft: JourneyDraft,
    onName: (String) -> Unit,
    onNext: () -> Unit,
) {
    JourneyScene(
        artHeight = 302.dp,
        art = { NameArt() },
        title = stringResource(R.string.journey_name_title),
        sub = stringResource(R.string.journey_name_sub),
        // Read from the window rather than from a focus flag: the keyboard is
        // what the art is making room for, and the window is the only thing
        // that knows whether it is actually up.
        keyboardUp = WindowInsets.isImeVisible,
        controls = {
            AlmaTextField(
                value = draft.name,
                onValueChange = onName,
                placeholder = "",
                label = stringResource(R.string.journey_name_aria),
                imeAction = ImeAction.Next,
            )
            // Required now — the owner's rule: nothing in this sequence may
            // be skipped except the birth time. Asking and then shrugging is
            // the worst of the three options.
            GoldButton(
                text = stringResource(R.string.journey_continue_cta),
                onClick = onNext,
                enabled = draft.name.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            )
        },
    )
}

/* ══ II · a date ══════════════════════════════════════════════════════ */

/**
 * Three pickers, none of them pre-set.
 *
 * The month is stored as a *number* and never as a word: "März" has to become 3
 * for the backend, and the word it came from is different in all six locales.
 *
 * A date that does not exist is caught here rather than nine seconds later.
 * Three independent lists can name 31 February between them, and the alternative
 * to refusing it now is a 422 arriving under the ceremony — which deliberately
 * does not surface failures, so the first the person hears of it is a portrait
 * with nothing on it.
 */
@Composable
internal fun ColumnScope.DateStep(draft: JourneyDraft, vm: JourneyViewModel) {
    val months = stringArrayResource(R.array.months).toList()
    val days = remember { (1..31).map(Int::toString) }
    // Ninety-two years, newest first, starting ten back — the range the web app
    // offers, and the one that makes the common case a short scroll.
    val years = remember { List(92) { (Year.now().value - 10 - it).toString() } }

    val impossible = draft.dateChosen && draft.birthDate == null

    JourneyScene(
        artHeight = 300.dp,
        art = { DateArt() },
        title = stringResource(R.string.journey_date_title),
        sub = stringResource(R.string.journey_date_sub),
        controls = {
            // Wheels, not menus — the owner's reference: three spinning
            // columns under a big title, a value always in the window.
            Row {
                WheelColumn(
                    values = days,
                    selectedIndex = draft.day?.minus(1),
                    onSelect = { vm.setDay(it + 1) },
                    modifier = Modifier.weight(1f),
                )
                WheelColumn(
                    values = months,
                    selectedIndex = draft.month?.minus(1),
                    onSelect = { vm.setMonth(it + 1) },
                    modifier = Modifier.weight(1.6f),
                )
                WheelColumn(
                    values = years,
                    selectedIndex = draft.year?.let { years.indexOf(it.toString()).takeIf { i -> i >= 0 } },
                    onSelect = { vm.setYear(years[it].toInt()) },
                    modifier = Modifier.weight(1.3f),
                )
            }
            if (impossible) Problem(stringResource(R.string.capture_impossible_date))

            GoldButton(
                text = stringResource(R.string.journey_continue_cta),
                onClick = vm::next,
                enabled = draft.birthDate != null,
                modifier = Modifier.fillMaxWidth(),
            )
        },
    )
}

/* ══ IV · a time, honestly ═════════════════════════════════════════════ */

/**
 * The step "I don't know" is a first-class answer to.
 *
 * Not knowing locks the houses, the solar return and the map, and the line under
 * the toggle says so — before the choice, not after it. What it does *not* do is
 * invent a noon: an assumed hour puts the Ascendant in the wrong sign about half
 * the time and produces a chart that reads as perfectly confident.
 *
 * The note is shown for a declared unknown **and** for a step tapped straight
 * through. Both mean the same thing — we have no time — and only one of them
 * used to say so.
 */
@Composable
internal fun ColumnScope.TimeStep(draft: JourneyDraft, vm: JourneyViewModel) {
    // The system's own clock setting, not the locale: en-GB is English and
    // writes 24-hour, es-US is Spanish and writes 12-hour, and Android lets
    // the person choose either regardless. Told to the draft once so the
    // conversion on the way out matches the field on the way in.
    val context = androidx.compose.ui.platform.LocalContext.current
    val twelveHour = remember { !android.text.format.DateFormat.is24HourFormat(context) }
    LaunchedEffect(twelveHour) { vm.setTwelveHour(twelveHour) }

    val hours = remember(twelveHour) {
        (if (twelveHour) 1..12 else 0..23).map { "%02d".format(it) }
    }
    val minutes = remember { (0..59).map { "%02d".format(it) } }
    // "AM" is the same token in all six locales — it is what the list itself
    // contains rather than a word to translate.
    val meridiems = remember { listOf("AM", "PM") }

    JourneyScene(
        artHeight = 308.dp,
        art = { TimeArt() },
        title = stringResource(R.string.journey_time_title),
        controls = {
            // The same wheels the date step spins, dimmed together when the
            // person declares the hour unknown.
            Row(modifier = Modifier.alpha(if (draft.timeUnknown) 0.4f else 1f)) {
                WheelColumn(
                    values = hours,
                    selectedIndex = draft.hour?.let { if (twelveHour) it - 1 else it },
                    onSelect = { vm.setHour(if (twelveHour) it + 1 else it) },
                    modifier = Modifier.weight(1f),
                    enabled = !draft.timeUnknown,
                )
                WheelColumn(
                    values = minutes,
                    selectedIndex = draft.minute,
                    onSelect = vm::setMinute,
                    modifier = Modifier.weight(1f),
                    enabled = !draft.timeUnknown,
                )
                if (twelveHour) {
                    WheelColumn(
                        values = meridiems,
                        selectedIndex = draft.meridiem.ordinal,
                        onSelect = { vm.setMeridiem(Meridiem.entries[it]) },
                        modifier = Modifier.weight(1f),
                        enabled = !draft.timeUnknown,
                    )
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 6.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.capture_unknown_time),
                        style = TextStyle(
                            fontFamily = AlmaFonts.Sans,
                            fontSize = 15.sp,
                            lineHeight = 21.sp,
                            color = AlmaPalette.Body.copy(alpha = 0.8f),
                        ),
                    )
                    if (!draft.hasTime) {
                        Text(
                            text = stringResource(R.string.journey_locked_without_time),
                            modifier = Modifier.padding(top = 3.dp),
                            style = TextStyle(
                                fontFamily = AlmaFonts.Sans,
                                fontSize = 13.sp,
                                lineHeight = 19.sp,
                                color = AlmaPalette.Muted2,
                            ),
                        )
                    }
                }
                AlmaToggle(
                    on = draft.timeUnknown,
                    onChange = vm::setTimeUnknown,
                    label = stringResource(R.string.capture_unknown_time),
                )
            }

            GoldButton(
                text = stringResource(R.string.journey_continue_cta),
                onClick = vm::next,
                modifier = Modifier.fillMaxWidth(),
            )
        },
    )
}

/* ══ V · a place ═══════════════════════════════════════════════════════ */

/**
 * The one step the whole chart hangs on: the coordinate sets the horizon and the
 * time zone sets the instant, so the answer has to come out of the gazetteer
 * rather than out of a free-text box.
 *
 * "Build my sky" stays disabled until a place has actually been *chosen* from
 * the list. Text that merely looks like a city is not a coordinate.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun ColumnScope.PlaceStep(vm: JourneyViewModel) {
    val query by vm.placeQuery.collectAsStateWithLifecycle()
    val results by vm.places.collectAsStateWithLifecycle()
    val draft by vm.draft.collectAsStateWithLifecycle()

    JourneyScene(
        artHeight = 292.dp,
        art = { PlaceArt() },
        title = stringResource(R.string.journey_place_title),
        sub = stringResource(R.string.journey_place_sub),
        keyboardUp = WindowInsets.isImeVisible,
        controls = {
            AlmaTextField(
                value = query,
                onValueChange = vm::onPlaceQuery,
                placeholder = "",
                label = stringResource(R.string.capture_search_place),
                imeAction = ImeAction.Search,
                capitalisation = KeyboardCapitalization.Words,
            )

            // Deliberately not `StateHost`: that renders a full-screen waiting
            // state and a full-screen failure, and this is a 230 dp strip inside
            // a form that still has a button under it. The three cases are the
            // same three cases; only the treatment is local.
            Box(Modifier.fillMaxWidth().heightIn(min = 0.dp, max = 232.dp)) {
                when (val state = results) {
                    // Nothing is drawn while a search is in flight. A spinner
                    // over four rows that are about to be replaced is noise, and
                    // the debounce means it would flicker on every keystroke.
                    is ScreenState.Loading -> Unit

                    // An empty list means "we looked and found nothing" only
                    // while nothing has been chosen. Choosing a place also
                    // empties the list — it is the answer, not a dead end — and
                    // without the `place == null` guard the screen told everyone
                    // who successfully picked their birthplace that no such
                    // place exists, directly under its name. Found on a device,
                    // not in review.
                    is ScreenState.Loaded -> if (state.data.isEmpty()) {
                        if (draft.place == null && query.trim().length >= 2) {
                            SuggestionNote(stringResource(R.string.capture_no_places))
                        }
                    } else {
                        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState())) {
                            state.data.forEach { place ->
                                SuggestionRow(
                                    place = place,
                                    selected = draft.place?.id == place.id,
                                    onClick = { vm.choosePlace(place) },
                                )
                            }
                        }
                    }

                    // Offline and "no such place" look the same to somebody who
                    // is typing, and the interface says the same thing about
                    // both — except that this one is worth a retry.
                    is ScreenState.Failed -> SuggestionNote(
                        if (state.failure is ApiFailure.Offline) {
                            stringResource(R.string.state_offline)
                        } else {
                            state.failure.message.ifBlank {
                                stringResource(R.string.error_generic)
                            }
                        }
                    )
                }
            }

            GoldButton(
                text = stringResource(R.string.journey_build_my_sky),
                onClick = vm::next,
                enabled = draft.place != null,
                modifier = Modifier.fillMaxWidth(),
            )
        },
    )
}

@Composable
private fun SuggestionRow(place: PlaceDto, selected: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                color = if (selected) AlmaPalette.Veil else Color.Transparent,
                shape = PillShape,
            )
            .clickable(role = Role.Button, onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 13.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(
            text = place.label,
            modifier = Modifier.weight(1f, fill = false),
            style = TextStyle(
                fontFamily = AlmaFonts.Sans,
                fontSize = 15.5.sp,
                lineHeight = 21.sp,
                color = if (selected) AlmaPalette.InkLight else AlmaPalette.Muted,
            ),
        )
        // The tail of the zone — "Kyiv", "Berlin" — because two towns of the
        // same name in different zones are the commonest way to get a chart an
        // hour wrong, and the zone is what tells them apart at a glance.
        Text(
            // The underscore has to go: IANA writes `America/New_York`, and a
            // Lisbon, Maine result was printing "New_York" with it intact. Small,
            // and on the one screen whose entire pitch is precision — "City is
            // enough. We resolve the historical time zone ourselves." An
            // underscore in the middle of a proper noun undercuts that sentence
            // in the same glance. Inherited verbatim from the web's
            // `timezone.split("/").pop()`, which has the matching fix.
            text = place.timezone.substringAfterLast('/').replace('_', ' '),
            modifier = Modifier.padding(start = 12.dp),
            style = TextStyle(
                fontFamily = AlmaFonts.Sans,
                fontSize = 12.5.sp,
                color = AlmaPalette.Body.copy(alpha = 0.5f),
            ),
        )
    }
}

@Composable
private fun SuggestionNote(text: String) {
    Text(
        text = text,
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
        style = TextStyle(
            fontFamily = AlmaFonts.Sans,
            fontSize = 13.5.sp,
            lineHeight = 20.sp,
            color = AlmaPalette.Muted3,
        ),
    )
}

/* ══ VI · the ceremony ═════════════════════════════════════════════════ */

/**
 * About nine seconds, eight lines, always skippable.
 *
 * The birth is saved underneath it. Not earlier — somebody who abandons at the
 * time step has not asked us to keep anything — and not later, because a
 * ceremony is exactly the cover a network round trip needs, so the portrait
 * usually has its answers by the time it is drawn.
 *
 * A failure is deliberately not surfaced here. The person is watching an
 * animation, not a form; the portrait is where a missing chart becomes visible,
 * and it says so honestly there.
 */
@Composable
internal fun ColumnScope.CeremonyStep(
    onBegin: () -> Unit,
    onDone: () -> Unit,
    /**
     * A question is standing over the scene — the daylight-saving fork.
     *
     * **The beats pause; they do not restart.** [index] survives, so answering
     * the question resumes the ceremony where it stood rather than replaying
     * nine seconds somebody has already watched.
     */
    paused: Boolean = false,
    /**
     * The save has not answered yet.
     *
     * The ceremony is a fixed nine and a half seconds and the network is not,
     * so whichever finishes second is the one that leaves. Walking out on a
     * slow connection lands somebody in an empty cabinet.
     */
    holding: Boolean = false,
) {
    val labels = stringArrayResource(R.array.journey_ceremony_labels)
    val lines = stringArrayResource(R.array.journey_ceremony_lines)
    var index by remember { mutableIntStateOf(0) }
    var played by remember { mutableStateOf(false) }
    val context = LocalContext.current

    // Asking rather than doing: the ViewModel decides whether this is the first
    // time, so a rotation mid-ceremony does not save the birth twice.
    LaunchedEffect(Unit) { onBegin() }

    LaunchedEffect(index, paused) {
        if (paused) return@LaunchedEffect
        if (index >= labels.lastIndex) {
            // A beat on the last line before the portrait, so the ceremony ends
            // rather than stops.
            delay(1_400)
            played = true
        } else {
            delay(1_150)
            index += 1
            // One soft tick per system lighting — the sky arriving in the
            // hand, eight times, because eight things genuinely happen here.
            AlmaHaptics.tick(context)
        }
    }

    LaunchedEffect(played, paused, holding) {
        if (!played || paused || holding) return@LaunchedEffect
        // The arrival: the chart is about to be revealed.
        AlmaHaptics.arrival(context)
        onDone()
    }

    // Laid out by hand rather than through `JourneyScene`: the line Alma is
    // saying belongs between the wheel and the progress bar, and it is the one
    // scene whose copy changes while the person watches it.
    val window = LocalConfiguration.current.screenHeightDp.dp

    Column(Modifier.weight(1f).fillMaxWidth()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(minOf(336f, window.value * 0.40f).dp),
            contentAlignment = Alignment.Center,
        ) {
            CeremonyArt()
        }
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 4.dp, vertical = 8.dp)
                // Announced as it changes, for anybody who cannot see it move.
                .semantics { liveRegion = LiveRegionMode.Polite },
        ) {
            Overline(labels[index], wide = true)
            Text(
                text = lines[index],
                modifier = Modifier.padding(top = 14.dp),
                style = TextStyle(
                    fontFamily = AlmaFonts.Display,
                    fontStyle = FontStyle.Italic,
                    fontSize = 22.sp,
                    lineHeight = 32.5.sp,
                    color = AlmaPalette.InkLight,
                ),
            )
        }
    }

    Column(
        modifier = Modifier.fillMaxWidth().padding(top = 24.dp),
        verticalArrangement = Arrangement.spacedBy(11.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(5.dp),
        ) {
            repeat(labels.size) { position ->
                Box(
                    Modifier
                        .weight(1f)
                        .height(2.dp)
                        .background(
                            if (position <= index) AlmaPalette.Gold
                            else AlmaPalette.Body.copy(alpha = 0.16f)
                        )
                )
            }
        }
        SkipAction(stringResource(R.string.journey_ceremony_skip), onDone)
    }
}

/* ══ VII · the portrait ════════════════════════════════════════════════ */

/**
 * The moment the product first says "here is you", and every line of it was
 * calculated.
 *
 * On the web this screen was found showing literal constants — a fixed Moon in
 * Scorpio, a fixed Ascendant, "16 chapters ready · 9 axes ready" with nothing
 * counted — to every visitor alive, on the one screen whose entire job is to
 * prove the calculation is real. Nothing here is written down: a row whose
 * request did not answer is *absent*, because an empty row is honest and a
 * filled one has to be true.
 *
 * What is handed over is the part that costs nothing: the life path, the card
 * and the moon phase are calculated from the birth and are free forever. That is
 * what makes the offer on the next screen an offer rather than a toll — the
 * person has already been given something true about themselves and can walk
 * away with it.
 */
@Composable
internal fun ColumnScope.PortraitStep(
    vm: JourneyViewModel,
    onKeep: () -> Unit,
    onLeave: () -> Unit,
) {
    val state by vm.portrait.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { vm.onPortraitShown() }

    Box(Modifier.weight(1f).fillMaxWidth()) {
        when (val current = state) {
            is ScreenState.Loading -> Waiting()

            is ScreenState.Loaded -> PortraitBody(current.data, onKeep)

            // A saved birth that cannot be read is still a saved birth, so the
            // way out is offered beside the retry. Without it, somebody whose
            // chart hits a refusal the journey cannot resolve — a daylight-saving
            // ambiguity is the real one — is stranded on the last screen before
            // the cabinet they already own.
            is ScreenState.Failed -> Column(Modifier.fillMaxSize()) {
                FailureNotice(
                    failure = current.failure,
                    onRetry = vm::retryPortrait,
                    modifier = Modifier.weight(1f),
                )
                QuietButton(
                    text = stringResource(R.string.journey_open_today),
                    onClick = onLeave,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun PortraitBody(portrait: Portrait, onKeep: () -> Unit) {
    val sun = localised(portrait.sunSign, SignNames)
    val moon = localised(portrait.moonSign, SignNames)
    val rising = localised(portrait.risingSign, SignNames)
    val phase = localised(portrait.moonPhase, PhaseNames)

    // Preferred from the engine when it survived the preview trim, derived from
    // the sun sign otherwise. The glyph is a *rendering* of `sun_sign` and not a
    // second claim, which is why deriving it is not the same as inventing it.
    val glyph = portrait.sunGlyph?.takeIf { it.isNotBlank() }
        ?: portrait.sunSign?.let { ZodiacGlyphs.getOrNull(ZodiacOrder.indexOf(it)) }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {

        Column(
            modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Overline(stringResource(R.string.journey_calculated), wide = true)

            if (glyph != null) {
                Text(
                    text = glyph,
                    modifier = Modifier.padding(top = 10.dp),
                    style = TextStyle(
                        fontFamily = AlmaFonts.Display,
                        fontSize = 84.sp,
                        lineHeight = 88.sp,
                        color = AlmaPalette.GoldBright,
                    ),
                )
            } else {
                // Nothing came back that could be drawn as a sign, so the
                // presence stands in its place rather than an empty gap or a
                // stand-in glyph belonging to nobody.
                AlmaPresence(size = 96.dp, modifier = Modifier.padding(top = 10.dp))
            }

            val heading = listOfNotNull(
                portrait.name.ifBlank { null },
                sun?.let { stringResource(R.string.insight_sun, it) },
            ).joinToString(" · ")
            if (heading.isNotBlank()) {
                Text(
                    text = heading,
                    modifier = Modifier.padding(top = 4.dp),
                    textAlign = TextAlign.Center,
                    style = TextStyle(
                        fontFamily = AlmaFonts.Display,
                        fontSize = 25.sp,
                        lineHeight = 31.sp,
                        color = AlmaPalette.InkLight,
                    ),
                )
            }

            val pills = listOfNotNull(
                moon?.let { "☽ $it" },
                // The Ascendant exists only when the birth time does — the
                // backend refuses to compute a horizon without one, and this is
                // the screen where that refusal is most worth showing.
                rising?.let { "${stringResource(R.string.cabinet_ascendant)} $it" },
                portrait.lifePath?.let { "${stringResource(R.string.num_life_path)} $it" },
            )
            if (pills.isNotEmpty()) {
                // Wrapped, not stacked. The comment this replaces had the right
                // premise and the wrong tool: three pills in German *are* wider
                // than a phone, and a `Row` that overflows would lose the life
                // path, which is the one of the three that is free. But the web
                // uses `flex-wrap: wrap`, which wraps rather than overflows and
                // therefore loses nothing — so stacking unconditionally gave
                // English a weaker layout than the web to solve a German
                // problem that wrapping already solved. Two centred lozenges of
                // unequal width on a 1080 px screen read as a layout that ran
                // out of room, on the screen whose whole job is to look like
                // real, earned value. `FlowRow` is the literal translation.
                FlowRow(
                    modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(7.dp, Alignment.CenterHorizontally),
                    verticalArrangement = Arrangement.spacedBy(7.dp),
                ) {
                    pills.forEach { CalculatedPill(it) }
                }
            }
        }

        SceneRule()

        val free = listOfNotNull(
            portrait.lifePath?.let {
                stringResource(R.string.system_numerology) to
                    "${stringResource(R.string.num_life_path)} $it"
            },
            portrait.cardName?.let {
                stringResource(R.string.system_birth_card) to
                    listOfNotNull(portrait.cardNumeral, it).joinToString(" ")
            },
            phase?.let { stringResource(R.string.cabinet_moon) to it },
        )

        if (free.isNotEmpty()) {
            Overline(stringResource(R.string.journey_free_label))
            Spacer(Modifier.height(12.dp))
            free.forEach { (label, value) -> PortraitRow(label, value) }
            FinePrint(
                text = stringResource(R.string.journey_free_note),
                modifier = Modifier.padding(top = 14.dp),
                align = TextAlign.Start,
            )
        }

        if (!portrait.timeKnown) {
            Spacer(Modifier.height(6.dp))
            PortraitRow(
                label = stringResource(R.string.journey_needs_time_row),
                value = stringResource(R.string.cabinet_needs_time),
                valueIsTag = true,
            )
        }

        Spacer(Modifier.height(24.dp))
        GoldButton(
            text = stringResource(R.string.journey_keep_my_sky),
            onClick = onKeep,
            modifier = Modifier.fillMaxWidth(),
        )
        FinePrint(
            text = stringResource(R.string.journey_stays_free),
            modifier = Modifier.padding(top = 12.dp, bottom = 8.dp),
        )
    }
}

@Composable
private fun PortraitRow(label: String, value: String, valueIsTag: Boolean = false) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(
            text = label,
            modifier = Modifier.weight(1f, fill = false),
            style = TextStyle(
                fontFamily = AlmaFonts.Sans,
                fontSize = 15.5.sp,
                lineHeight = 22.sp,
                color = AlmaPalette.Body.copy(alpha = 0.8f),
            ),
        )
        Text(
            text = if (valueIsTag) value.uppercase() else value,
            modifier = Modifier.padding(start = 14.dp),
            textAlign = TextAlign.End,
            style = if (valueIsTag) {
                TextStyle(
                    fontFamily = AlmaFonts.Sans,
                    fontSize = 10.5.sp,
                    letterSpacing = 0.12.em,
                    color = AlmaPalette.Gold,
                )
            } else {
                TextStyle(
                    fontFamily = AlmaFonts.Sans,
                    fontSize = 15.sp,
                    lineHeight = 22.sp,
                    color = AlmaPalette.GoldBright,
                )
            },
        )
    }
}

/* ══ VIII · the handoff ════════════════════════════════════════════════ */

/**
 * Three rules and a door. The only onboarding this product ever gives, and it
 * comes *after* the person already has something rather than before.
 */
@Composable
internal fun ColumnScope.HandoffStep(onOpenToday: () -> Unit) {
    val rules = stringArrayResource(R.array.journey_rules)

    Column(Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState())) {
        Spacer(Modifier.height(40.dp))
        AlmaPresence(size = 56.dp, ring = false)
        Text(
            text = stringResource(R.string.journey_handoff_title),
            modifier = Modifier.padding(top = 24.dp),
            style = JourneyTitleStyle,
        )
        Text(
            text = stringResource(R.string.journey_handoff_sub),
            modifier = Modifier.padding(top = 12.dp),
            style = JourneySubStyle,
        )

        Spacer(Modifier.height(28.dp))
        rules.forEachIndexed { index, rule ->
            if (index > 0) Hairline(Modifier.padding(vertical = 20.dp))
            Row(verticalAlignment = Alignment.Top) {
                Text(
                    text = romanNumeral(index + 1),
                    modifier = Modifier.width(26.dp),
                    style = TextStyle(
                        fontFamily = AlmaFonts.Display,
                        fontSize = 24.sp,
                        color = AlmaPalette.GoldDeep,
                    ),
                )
                Text(
                    text = rule,
                    modifier = Modifier.padding(start = 18.dp),
                    style = TextStyle(
                        fontFamily = AlmaFonts.Sans,
                        fontSize = 15.sp,
                        lineHeight = 23.7.sp,
                        color = AlmaPalette.Body.copy(alpha = 0.78f),
                    ),
                )
            }
        }
        Spacer(Modifier.height(28.dp))
    }

    GoldButton(
        text = stringResource(R.string.journey_open_today),
        onClick = onOpenToday,
        modifier = Modifier.fillMaxWidth(),
    )
}

/* ── the engine's own vocabulary ───────────────────────────────────────── */

/**
 * The calculation service names signs and moon phases in English whatever locale
 * was asked for — they are keys in the payload rather than copy — so they are
 * translated here, at the one point where they become a sentence somebody reads.
 *
 * An unrecognised key falls back to the key itself. That is deliberate: when the
 * engine ships a phase this table has not heard of, the honest thing is to show
 * what was calculated in English rather than to drop a row that exists.
 */
@Composable
private fun localised(key: String?, table: Map<String, Int>): String? {
    if (key == null) return null
    val id = table[key] ?: return key
    return stringResource(id)
}

private val SignNames: Map<String, Int> = mapOf(
    "Aries" to R.string.sign_aries,
    "Taurus" to R.string.sign_taurus,
    "Gemini" to R.string.sign_gemini,
    "Cancer" to R.string.sign_cancer,
    "Leo" to R.string.sign_leo,
    "Virgo" to R.string.sign_virgo,
    "Libra" to R.string.sign_libra,
    "Scorpio" to R.string.sign_scorpio,
    "Sagittarius" to R.string.sign_sagittarius,
    "Capricorn" to R.string.sign_capricorn,
    "Aquarius" to R.string.sign_aquarius,
    "Pisces" to R.string.sign_pisces,
)

private val PhaseNames: Map<String, Int> = mapOf(
    "new moon" to R.string.phase_new_moon,
    "waxing crescent" to R.string.phase_waxing_crescent,
    "first quarter" to R.string.phase_first_quarter,
    "waxing gibbous" to R.string.phase_waxing_gibbous,
    "full moon" to R.string.phase_full_moon,
    "waning gibbous" to R.string.phase_waning_gibbous,
    "last quarter" to R.string.phase_last_quarter,
    "waning crescent" to R.string.phase_waning_crescent,
)

/** The zodiac in its own order, for turning a calculated sign into its symbol. */
private val ZodiacOrder = SignNames.keys.toList()

/**
 * Every one of these carries U+FE0E, the variation selector that asks for the
 * *text* presentation, and it is not optional.
 *
 * Android resolves a bare U+2651 through Noto Color Emoji, which draws Capricorn
 * as a white sigil on a purple disc — a second accent colour, on the one screen
 * whose job is to prove the reading is real, in a design whose rule is one gold
 * and no other. With the selector the system falls through to the monochrome
 * glyph, which then takes whatever colour it is given. The calculation service
 * appends the same selector to the `sign_glyph` it sends, which is why the
 * cabinet's signs were already gold and this list's were not.
 */
private val ZodiacGlyphs = listOf(
    "♈︎", "♉︎", "♊︎", "♋︎", "♌︎", "♍︎",
    "♎︎", "♏︎", "♐︎", "♑︎", "♒︎", "♓︎",
)


/**
 * II · who this is for. Volunteered, never required — «не скажу» is a
 * first-class card. With an answer Alma's Russian agrees with the reader;
 * without one the genderless register stands, as it always did.
 */
@Composable
internal fun ColumnScope.AboutStep(
    draft: JourneyDraft,
    onGender: (String?) -> Unit,
    onNext: () -> Unit,
) {
    JourneyScene(
        artHeight = 240.dp,
        art = { NameArt() },
        title = stringResource(R.string.journey_about_title),
        sub = stringResource(R.string.journey_about_sub),
        controls = {
            GenderCard(
                selected = draft.gender == "female" && draft.aboutAnswered,
                label = stringResource(R.string.journey_gender_female),
            ) { onGender("female") }
            Spacer(Modifier.height(10.dp))
            GenderCard(
                selected = draft.gender == "male" && draft.aboutAnswered,
                label = stringResource(R.string.journey_gender_male),
            ) { onGender("male") }
            Spacer(Modifier.height(10.dp))
            GenderCard(
                selected = draft.gender == null && draft.aboutAnswered,
                label = stringResource(R.string.journey_gender_skip),
            ) { onGender(null) }

            Spacer(Modifier.height(22.dp))
            GoldButton(text = stringResource(R.string.journey_continue_cta), onClick = onNext)
        },
    )
}

@Composable
private fun GenderCard(selected: Boolean, label: String, onTap: () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .border(
                width = 1.dp,
                color = if (selected) AlmaPalette.Gold.copy(alpha = 0.7f)
                else AlmaPalette.Body.copy(alpha = 0.12f),
                shape = PillShape,
            )
            .background(
                if (selected) AlmaPalette.Gold.copy(alpha = 0.18f) else AlmaPalette.Veil,
                PillShape,
            )
            .clickable(role = Role.Button, onClick = onTap)
            .padding(horizontal = 20.dp, vertical = 16.dp),
    ) {
        Text(text = label, style = AlmaTheme.type.almaVoice.copy(fontSize = 17.sp, fontStyle = androidx.compose.ui.text.font.FontStyle.Normal), modifier = Modifier.weight(1f))
        if (selected) {
            Text(text = "✦", color = AlmaPalette.GoldBright)
        }
    }
}


/* ── the wheels ─────────────────────────────────────────────────────────── */

/**
 * One spinning column — the picker the owner's reference uses. The platform's
 * own `NumberPicker` wrapped for Compose: a value always in the window, the
 * neighbours fading above and below, choosing by flick.
 */
@Composable
internal fun WheelColumn(
    values: List<String>,
    selectedIndex: Int?,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    androidx.compose.ui.viewinterop.AndroidView(
        modifier = modifier,
        factory = { context ->
            android.widget.NumberPicker(context).apply {
                minValue = 0
                maxValue = values.size - 1
                displayedValues = values.toTypedArray()
                wrapSelectorWheel = false
                value = selectedIndex ?: 0
                setOnValueChangedListener { _, _, new -> onSelect(new) }
            }
        },
        update = { picker ->
            if (picker.maxValue != values.size - 1 || !picker.displayedValues.contentEquals(values.toTypedArray())) {
                picker.displayedValues = null
                picker.maxValue = values.size - 1
                picker.displayedValues = values.toTypedArray()
            }
            val want = selectedIndex ?: 0
            if (picker.value != want) picker.value = want
            picker.isEnabled = enabled
        },
    )
}
