package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.data.dto.BirthInput
import ai.pazl.alma.data.dto.PlaceDto
import ai.pazl.alma.data.dto.ProfileDto
import ai.pazl.alma.ui.components.GoldButton
import ai.pazl.alma.ui.components.QuietButton
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * The people this account has saved. Compatibility needs at least one.
 *
 * **This was the last stub in the app**, and what it said was worse than
 * nothing: "adding a second person is not built on Android yet — add one on the
 * web and it will be here". A screen that sends somebody to a different product
 * to finish a job is a screen that has given up, and compatibility is one of
 * the eight systems this app sells.
 *
 * iOS has had the real thing for a while and this is the same screen from the
 * same three calls — list, save, delete. What it deliberately does not do is
 * compute anything: every row is what was typed, so there is nothing here that
 * can be wrong.
 */
@Composable
fun PeopleScreen(
    container: AppContainer,
    onBack: () -> Unit,
) {
    val vm: PeopleViewModel = viewModel { PeopleViewModel(container) }
    val state by vm.state.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { vm.load() }

    NightSky(config = SkyConfig(seed = 9)) {
        CabinetPage {
            ScreenTitle(stringResource(R.string.people_title), onBack = onBack)

            if (state.adding) {
                AddPerson(
                    vm = vm,
                    onCancel = vm::stopAdding,
                )
                return@CabinetPage
            }

            Text(
                text = stringResource(R.string.people_lead),
                style = AlmaTheme.type.dayVoice,
                modifier = Modifier.padding(top = 10.dp),
            )

            Spacer(Modifier.height(24.dp))

            if (state.people.isEmpty()) {
                Text(
                    text = stringResource(R.string.people_none_yet),
                    style = AlmaTheme.type.meta,
                )
                Spacer(Modifier.height(18.dp))
            } else {
                RuledLabel(
                    stringResource(R.string.people_saved),
                    trailing = state.people.size.toString(),
                )
                state.people.forEachIndexed { index, person ->
                    PersonRow(
                        person = person,
                        last = index == state.people.lastIndex,
                        onRemove = { vm.remove(person) },
                    )
                }
                Spacer(Modifier.height(22.dp))
            }

            GoldButton(
                text = stringResource(R.string.cabinet_add_person),
                onClick = vm::startAdding,
                modifier = Modifier.fillMaxWidth(),
            )

            // Whose birth data this is, and what we did about asking. The terms
            // ask the person entering it to have asked first, and saying so at
            // the point of entry is worth more than saying it in a document.
            Text(
                text = stringResource(R.string.people_consent),
                style = AlmaTheme.type.meta,
                color = AlmaPalette.Muted3,
                modifier = Modifier.padding(top = 24.dp),
            )

            state.error?.let {
                Text(
                    text = it,
                    style = AlmaTheme.type.meta,
                    color = AlmaPalette.Disagree,
                    modifier = Modifier.padding(top = 16.dp),
                )
            }
        }
    }
}

/**
 * One saved birth. Everything shown is what was entered.
 *
 * Removing asks twice, and that is not ceremony: every reading keyed to this
 * person goes with them, and those are chapters somebody paid for.
 */
@Composable
private fun PersonRow(person: ProfileDto, last: Boolean, onRemove: () -> Unit) {
    var confirming by remember { mutableStateOf(false) }
    CabinetRow(rule = !last) {
        Column(Modifier.weight(1f)) {
            Text(
                text = person.name?.takeIf { it.isNotBlank() }
                    ?: stringResource(R.string.people_unnamed),
                style = AlmaTheme.type.headingM,
            )
            Text(
                text = listOfNotNull(
                    person.birthDate,
                    person.birthTime ?: stringResource(R.string.people_time_unknown),
                    person.placeLabel,
                ).joinToString(" · "),
                style = AlmaTheme.type.meta,
                modifier = Modifier.padding(top = 3.dp),
            )
        }
        QuietButton(
            text = if (confirming) {
                stringResource(R.string.people_remove_confirm)
            } else {
                stringResource(R.string.people_remove)
            },
            onClick = { if (confirming) onRemove() else confirming = true },
            contentColor = AlmaPalette.Disagree,
        )
    }
}

/**
 * A second birth, asked for in the journey's own order and with its own fields.
 *
 * Shorter than the journey by one thing and it is the ceremony: nothing is
 * being revealed here, a comparison is being enabled.
 *
 * **`is_self = false` is explicit and must stay explicit.** "Not said" on a
 * second birth would overwrite the account owner's own chart and every reading
 * keyed to it. iOS carries the same warning at the same line.
 */
@Composable
private fun AddPerson(vm: PeopleViewModel, onCancel: () -> Unit) {
    val draft by vm.draft.collectAsStateWithLifecycle()

    Spacer(Modifier.height(18.dp))

    AlmaTextField(
        value = draft.name,
        onValueChange = vm::onName,
        placeholder = "",
        label = stringResource(R.string.journey_name_aria),
        imeAction = ImeAction.Next,
        capitalisation = KeyboardCapitalization.Words,
    )
    Spacer(Modifier.height(12.dp))

    // The date as text in the engine's own format. A wheel picker would be the
    // journey's answer, and the journey's wheels are bound to its own view
    // model; borrowing them here would mean two screens sharing one draft.
    AlmaTextField(
        value = draft.birthDate,
        onValueChange = vm::onDate,
        placeholder = "1994-03-12",
        label = stringResource(R.string.people_birth_date),
        imeAction = ImeAction.Next,
    )
    Spacer(Modifier.height(12.dp))

    AlmaTextField(
        value = draft.birthTime,
        onValueChange = vm::onTime,
        placeholder = "14:20",
        label = stringResource(R.string.people_birth_time),
        imeAction = ImeAction.Next,
    )
    Spacer(Modifier.height(12.dp))

    AlmaTextField(
        value = draft.placeQuery,
        onValueChange = vm::onPlaceQuery,
        placeholder = "",
        label = stringResource(R.string.capture_search_place),
        imeAction = ImeAction.Search,
        capitalisation = KeyboardCapitalization.Words,
    )

    // The place has to come out of the gazetteer rather than out of a text box:
    // the coordinate sets the horizon and the zone sets the instant, and text
    // that merely looks like a city is neither.
    draft.places.take(4).forEach { place ->
        Text(
            text = place.label,
            style = AlmaTheme.type.meta,
            color = if (draft.chosen?.id == place.id) AlmaPalette.GoldBright else AlmaPalette.Body,
            modifier = Modifier
                .fillMaxWidth()
                .clickable { vm.choose(place) }
                .padding(vertical = 10.dp),
        )
    }

    Spacer(Modifier.height(20.dp))
    GoldButton(
        text = stringResource(R.string.people_save),
        onClick = vm::save,
        enabled = draft.chosen != null && draft.birthDate.isNotBlank(),
        modifier = Modifier.fillMaxWidth(),
    )
    Spacer(Modifier.height(8.dp))
    QuietButton(
        text = stringResource(R.string.nav_back),
        onClick = onCancel,
        modifier = Modifier.fillMaxWidth(),
    )
}

@androidx.compose.runtime.Immutable
data class PeopleState(
    val people: List<ProfileDto> = emptyList(),
    val adding: Boolean = false,
    val error: String? = null,
)

@androidx.compose.runtime.Immutable
data class PersonDraft(
    val name: String = "",
    val birthDate: String = "",
    val birthTime: String = "",
    val placeQuery: String = "",
    val places: List<PlaceDto> = emptyList(),
    val chosen: PlaceDto? = null,
)

class PeopleViewModel(private val container: AppContainer) : ViewModel() {

    private val _state = MutableStateFlow(PeopleState())
    val state: StateFlow<PeopleState> = _state.asStateFlow()

    private val _draft = MutableStateFlow(PersonDraft())
    val draft: StateFlow<PersonDraft> = _draft.asStateFlow()

    fun load() {
        viewModelScope.launch {
            when (val result = container.client.profiles()) {
                // Only the others. The account owner's own birth is edited in
                // Settings and must never appear in a list with a "remove"
                // button beside it.
                is ApiResult.Ok -> _state.value = _state.value.copy(
                    people = result.data.filterNot { it.isSelf },
                    error = null,
                )
                is ApiResult.Err -> _state.value =
                    _state.value.copy(error = result.failure.message)
            }
        }
    }

    fun remove(person: ProfileDto) {
        viewModelScope.launch {
            when (val result = container.client.deleteProfile(person.id)) {
                is ApiResult.Ok -> {
                    load()
                    container.session.refreshProfile()
                }
                is ApiResult.Err -> _state.value =
                    _state.value.copy(error = result.failure.message)
            }
        }
    }

    fun startAdding() {
        _draft.value = PersonDraft()
        _state.value = _state.value.copy(adding = true, error = null)
    }

    fun stopAdding() { _state.value = _state.value.copy(adding = false) }

    fun onName(value: String) { _draft.value = _draft.value.copy(name = value) }
    fun onDate(value: String) { _draft.value = _draft.value.copy(birthDate = value) }
    fun onTime(value: String) { _draft.value = _draft.value.copy(birthTime = value) }

    fun onPlaceQuery(value: String) {
        _draft.value = _draft.value.copy(placeQuery = value, chosen = null)
        if (value.length < 2) {
            _draft.value = _draft.value.copy(places = emptyList())
            return
        }
        viewModelScope.launch {
            when (val result = container.client.searchPlaces(value)) {
                is ApiResult.Ok -> _draft.value = _draft.value.copy(places = result.data)
                is ApiResult.Err -> Unit  // a failed search is an empty list, not an error banner
            }
        }
    }

    fun choose(place: PlaceDto) {
        _draft.value = _draft.value.copy(chosen = place, placeQuery = place.label, places = emptyList())
    }

    fun save() {
        val draft = _draft.value
        val place = draft.chosen ?: return
        viewModelScope.launch {
            val input = BirthInput(
                birthDate = draft.birthDate.trim(),
                birthTime = draft.birthTime.trim().ifBlank { null },
                latitude = place.latitude,
                longitude = place.longitude,
                timezone = place.timezone,
                placeLabel = place.label,
                placeId = place.id,
                name = draft.name.trim().ifBlank { null },
                // **Explicit, always.** See the note on `AddPerson`.
                isSelf = false,
            )
            when (val result = container.client.saveProfile(input)) {
                is ApiResult.Ok -> {
                    _state.value = _state.value.copy(adding = false, error = null)
                    load()
                    container.session.refreshProfile()
                }
                is ApiResult.Err -> _state.value =
                    _state.value.copy(error = result.failure.message)
            }
        }
    }
}
