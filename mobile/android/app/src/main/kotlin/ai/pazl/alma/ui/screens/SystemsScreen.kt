package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.core.ScreenState
import ai.pazl.alma.core.SessionHolder
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.data.dto.CalcRequest
import ai.pazl.alma.data.dto.HubEntryDto
import ai.pazl.alma.ui.components.QuietButton
import ai.pazl.alma.ui.components.StateHost
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
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
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonObject

/**
 * The eight, grouped by the question they answer rather than by the name of the
 * tradition.
 *
 * A newcomer does not know what a solar return is, but does know "what happens
 * this year". Every group is listed, because which of them has anything in it is
 * the *hub's* decision: give a person a birth time and "this year" stops being
 * empty, and a ready system with no heading to sit under would simply vanish.
 *
 * Two requests. The hub is the screen. The natal chart is only the portrait
 * strip at the top, and it is skipped entirely until there is birth data —
 * firing it regardless meant one guaranteed-failing request on every visit by
 * somebody who has not entered a date yet.
 */
@Composable
fun SystemsScreen(
    container: AppContainer,
    onOpenSystem: (String) -> Unit,
    onAddPerson: () -> Unit,
    onAddBirthData: () -> Unit,
) {
    val vm: SystemsViewModel = viewModel { SystemsViewModel(container.client, container.session) }
    val state by vm.state.collectAsStateWithLifecycle()

    NightSky(config = SkyConfig(seed = 2, motes = 2)) {
        StateHost(state, onRetry = vm::reload) { systems ->
            SystemsBody(
                systems,
                onOpenSystem = onOpenSystem,
                onAddPerson = onAddPerson,
                onAddBirthData = onAddBirthData,
            )
        }
    }
}

/* ── what the screen holds ─────────────────────────────────────────────── */

@Immutable
data class SystemsView(
    val hasBirthData: Boolean,
    /** The hub's own list, in the hub's own order, joined to nothing. */
    val entries: List<HubEntryDto>,
    /**
     * The natal preview, for the three pills at the top.
     *
     * There is deliberately no fallback behind it. A plausible-looking Sun sign
     * that belongs to nobody would be a lie about the one number most people
     * came to see, so a failed chart shows no pills at all.
     */
    val chart: JsonObject?,
)

class SystemsViewModel(
    private val client: AlmaClient,
    private val session: SessionHolder,
) : ViewModel() {

    private val _state = MutableStateFlow<ScreenState<SystemsView>>(ScreenState.Loading)
    val state: StateFlow<ScreenState<SystemsView>> = _state.asStateFlow()

    private var running: Job? = null

    init {
        reload()
    }

    fun reload() {
        running?.cancel()
        running = viewModelScope.launch {
            _state.value = ScreenState.Loading
            val account = session.state.first { it.ready }

            when (val hub = client.hub()) {
                is ApiResult.Err -> _state.value = ScreenState.Failed(hub.failure)
                is ApiResult.Ok -> {
                    // The hub is the authority on whether there is birth data;
                    // the session's own answer is the same fact one request
                    // earlier, and the two only disagree if a second device
                    // changed something mid-session.
                    val chart = if (hub.data.hasBirthData) {
                        (client.system(AlmaSystem.NATAL, CalcRequest(locale = account.locale))
                            as? ApiResult.Ok)?.data?.data
                    } else {
                        null
                    }
                    _state.value = ScreenState.Loaded(
                        SystemsView(
                            hasBirthData = hub.data.hasBirthData,
                            entries = hub.data.systems,
                            chart = chart,
                        )
                    )
                }
            }
        }
    }
}

/* ── the screen ────────────────────────────────────────────────────────── */

/**
 * "calculated" means unlocked and "open" means computable but unpaid — and the
 * numbers are free either way, so both belong under a question heading. Only the
 * three statuses that name a missing detail fall through to "not yet".
 */
private fun HubEntryDto.isReady(): Boolean = status == "calculated" || status == "open"

@Composable
private fun SystemsBody(
    systems: SystemsView,
    onOpenSystem: (String) -> Unit,
    onAddPerson: () -> Unit,
    onAddBirthData: () -> Unit,
) {
    CabinetPage {
        val ready = systems.entries.count { it.isReady() }
        // "5/8" rather than "5 of 8": the total is however many systems the hub
        // lists, and the only translatable part is the word beside it.
        val tally = if (systems.entries.isEmpty()) {
            null
        } else {
            "$ready/${systems.entries.size} ${stringResource(R.string.cabinet_calculated)}"
        }

        ScreenTitle(stringResource(R.string.nav_systems))
        if (tally != null) {
            Text(
                text = tally,
                style = AlmaTheme.type.meta,
                color = AlmaPalette.Gold,
                modifier = Modifier.padding(top = 4.dp),
            )
        }

        if (!systems.hasBirthData) {
            // Nothing here can be computed without a birth date. The graph gives
            // this screen no route to the form — `TodayScreen` is the one that
            // carries `onAddBirthData` — so it says the sentence rather than
            // drawing a button that cannot lead anywhere.
            // A button, not just a sentence. This said "Add your birth date and
            // I can read you." with nothing to tap, because the graph handed
            // this screen no route to the form — `TodayScreen` was the only one
            // given `onAddBirthData`. The state is nearly unreachable (the start
            // destination sends anybody without a profile into the journey) and
            // it was a dead end whenever it did happen.
            NeedBirthData {
                QuietButton(
                    text = stringResource(R.string.state_add_birth_data),
                    onClick = onAddBirthData,
                )
            }
            return@CabinetPage
        }

        Spacer(Modifier.height(22.dp))
        Portrait(systems.chart)
        Spacer(Modifier.height(10.dp))

        // Synthesis has its own block at the bottom and never doubles up here.
        val listed = systems.entries.filter { it.slug != AlmaSystem.SYNTHESIS }

        GroupOrder.forEach { group ->
            val rows = listed.filter { SystemGroups[it.slug] == group && it.isReady() }
            if (rows.isEmpty()) return@forEach
            Spacer(Modifier.height(22.dp))
            RuledLabel(stringResource(group))
            rows.forEachIndexed { index, entry ->
                SystemRow(entry, last = index == rows.lastIndex, onOpenSystem, onAddPerson)
            }
        }

        val pending = listed.filterNot { it.isReady() }
        if (pending.isNotEmpty()) {
            Spacer(Modifier.height(22.dp))
            // One heading covers a missing birth time, a missing person and a
            // system not reached yet alike — "not yet" is the one label true of
            // all three.
            RuledLabel(stringResource(R.string.cabinet_not_yet))
            pending.forEachIndexed { index, entry ->
                SystemRow(entry, last = index == pending.lastIndex, onOpenSystem, onAddPerson)
            }
        }

        systems.entries.firstOrNull { it.slug == AlmaSystem.SYNTHESIS }?.let { synthesis ->
            Spacer(Modifier.height(22.dp))
            RuledLabel(stringResource(R.string.group_all_of_it))
            CabinetRow(onClick = { onOpenSystem(AlmaSystem.SYNTHESIS) }, rule = false) {
                Column(Modifier.weight(1f)) {
                    Text(text = systemName(synthesis.slug), style = AlmaTheme.type.headingM)
                }
                Text(text = "→", style = AlmaTheme.type.positions)
            }
        }

        Spacer(Modifier.height(26.dp))
        Text(text = stringResource(R.string.cabinet_eight_tail), style = AlmaTheme.type.meta)
        Spacer(Modifier.height(24.dp))
    }
}

/**
 * Where a row goes.
 *
 * Almost always to its own system screen. The exception is the status that names
 * a missing *person* rather than a missing detail of the chart: compatibility
 * with nobody to compare against would open a screen whose only content is "add
 * somebody", so the row goes straight to the place that adds one.
 */
@Composable
private fun SystemRow(
    entry: HubEntryDto,
    last: Boolean,
    onOpenSystem: (String) -> Unit,
    onAddPerson: () -> Unit,
) {
    val ready = entry.isReady()
    CabinetRow(
        rule = !last,
        onClick = {
            if (entry.status == "add-person") onAddPerson() else onOpenSystem(entry.slug)
        },
    ) {
        Text(
            text = systemName(entry.slug),
            style = AlmaTheme.type.headingM,
            color = if (ready) AlmaPalette.InkLight else AlmaPalette.Muted,
            modifier = Modifier.weight(1f),
        )
        // The hub carries a slug and a status and nothing else. A second line
        // here — "life path 7", "3 active today" — would be a fact about the
        // person that no request on this screen makes.
        StatusTag(statusLabel(entry.status), ready)
    }
}

@Composable
private fun statusLabel(status: String): String = when (status) {
    "calculated" -> stringResource(R.string.cabinet_calculated)
    "open" -> stringResource(R.string.cabinet_open)
    "needs-time" -> stringResource(R.string.cabinet_needs_time)
    "add-person" -> stringResource(R.string.cabinet_add_person)
    "not-yet" -> stringResource(R.string.cabinet_not_yet)
    // A status this build has not heard of. The hub is the backend's list and
    // it can grow; printing it is more use than printing nothing.
    else -> status
}

/**
 * The portrait: the ring, the sun's glyph inside it, and the three placements a
 * locked chart is still allowed to name.
 *
 * "☉ 23° ♓︎" when the chart is open, "☉ ♓︎" when only the sign names came back.
 * No sign, no pill — the ring stays bare rather than showing a placement nobody
 * calculated.
 */
@Composable
private fun Portrait(chart: JsonObject?) {
    val placements = chart?.obj("placements")
    val sunGlyph = placements?.obj("sun")?.text("sign_glyph")
        ?: chart?.text("sun_sign")?.let { SignGlyphs[it] }

    // Rows, not capsules — the owner's verdict on the stacked ovals was
    // aesthetic and final. The same three facts, printed the way the rest of
    // the product prints a citation: name quiet on the left, position in the
    // serif on the right, a hairline between. Mirrors the iOS front page.
    val rows = listOfNotNull(
        portraitRow(stringResource(R.string.cabinet_sun), chart?.text("sun_sign"), placements?.obj("sun")),
        portraitRow(stringResource(R.string.cabinet_moon), chart?.text("moon_sign"), placements?.obj("moon")),
        chart?.obj("angles")?.obj("formatted")?.text("ascendant")
            ?.let { stringResource(R.string.cabinet_ascendant) to spellSigns(it) }
            ?: chart?.text("rising_sign")?.let {
                stringResource(R.string.cabinet_ascendant) to signWord(it)
            },
    )

    Column(Modifier.fillMaxWidth()) {
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            ZodiacRing(diameter = 150.dp) {
                if (sunGlyph != null) {
                    Text(
                        text = sunGlyph,
                        style = AlmaTheme.type.displayXl,
                        color = AlmaPalette.StarFill,
                    )
                }
            }
        }
        rows.forEachIndexed { index, (label, value) ->
            CabinetRow(rule = index < rows.lastIndex) {
                Text(text = label, style = AlmaTheme.type.meta, modifier = Modifier.weight(1f))
                Text(text = value, style = AlmaTheme.type.positions)
            }
        }
    }
}

@Composable
private fun portraitRow(
    label: String,
    sign: String?,
    placement: JsonObject?,
): Pair<String, String>? {
    val formatted = placement?.text("formatted")
    if (formatted != null) {
        val house = placement.int("house")?.let { " · " + houseWord(it) }.orEmpty()
        return label to spellSigns(formatted) + house
    }
    return sign?.let { label to signWord(it) }
}
