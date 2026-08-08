package ai.pazl.alma.ui.screens

import ai.pazl.alma.core.ScreenState
import ai.pazl.alma.core.SessionHolder
import ai.pazl.alma.core.toScreenState
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.data.FunnelStage
import ai.pazl.alma.data.dto.BirthInput
import ai.pazl.alma.data.dto.CalcRequest
import ai.pazl.alma.data.dto.CalcResultDto
import ai.pazl.alma.data.dto.PlaceDto
import androidx.compose.runtime.Immutable
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeFormatter

/**
 * The onboarding journey, as state.
 *
 * Everything the person types lives here and nowhere else, which is what lets
 * the whole funnel be one navigation destination: a half-entered birth has no
 * meaning outside the flow, and eight routes would have meant either eight
 * copies of it or a `ViewModel` hoisted above the graph.
 *
 * ## The one rule this file exists to keep
 *
 * **Nothing is invented.** A birth time that was not given is `null`, never
 * midnight and never noon — the backend treats null as a first-class state and
 * refuses the systems that need a horizon, whereas an assumed hour produces
 * confident, wrong houses and an Ascendant in the wrong sign about half the
 * time. Every field starts empty for the same reason: the web app's birthday
 * used to sit pre-filled in every visitor's form, which meant the first chart a
 * person saw was somebody else's.
 */
class JourneyViewModel(
    private val client: AlmaClient,
    private val session: SessionHolder,
) : ViewModel() {

    /* ── where we are ──────────────────────────────────────────────────── */

    private val _step = MutableStateFlow(JourneyStep.Name)
    val step: StateFlow<JourneyStep> = _step.asStateFlow()

    private val _draft = MutableStateFlow(JourneyDraft())
    val draft: StateFlow<JourneyDraft> = _draft.asStateFlow()

    /* ── the place search ──────────────────────────────────────────────── */

    private val _placeQuery = MutableStateFlow("")
    val placeQuery: StateFlow<String> = _placeQuery.asStateFlow()

    /**
     * Empty-and-loaded is the resting state, not a fourth case.
     *
     * A query shorter than two characters has been *answered* — with nothing —
     * rather than left pending, and the place step knows not to say "no such
     * place" until somebody has actually typed enough to look one up.
     */
    private val _places = MutableStateFlow<ScreenState<List<PlaceDto>>>(
        ScreenState.Loaded(emptyList())
    )
    val places: StateFlow<ScreenState<List<PlaceDto>>> = _places.asStateFlow()

    /* ── the portrait ──────────────────────────────────────────────────── */

    private val _portrait = MutableStateFlow<ScreenState<Portrait>>(ScreenState.Loading)
    val portrait: StateFlow<ScreenState<Portrait>> = _portrait.asStateFlow()

    /* ── funnel ────────────────────────────────────────────────────────── */

    /**
     * Which stages this journey has already reported.
     *
     * Every stage in this flow is a *first time somebody got here*, so each is
     * recorded once per journey and never again. Counting a stage twice — a
     * back-and-forward, a rotation, a process that came back — makes the drop
     * off the previous step look better than it is, which is the one direction
     * a funnel must never be wrong in.
     */
    private val recorded = mutableSetOf<FunnelStage>()

    private fun recordOnce(stage: FunnelStage, meta: Map<String, String>? = null) {
        if (!recorded.add(stage)) return
        // Fire and forget: nothing on screen may branch on whether the beacon
        // landed, and a person whose analytics request failed still has a
        // journey to walk.
        viewModelScope.launch { client.record(stage, meta) }
    }

    /* ── opening ───────────────────────────────────────────────────────── */

    private var opened = false

    /**
     * Take the step the route asked for, once.
     *
     * `LandingView` is recorded here rather than on a landing page, because on
     * Android there is no landing page: this screen *is* the front door, and it
     * is the only place mounted for exactly as long as a new person is standing
     * in it. `QuizStart` then comes on the first deliberate advance, so the drop
     * between the two still means what it means on the web — arrived, versus
     * began answering.
     *
     * A step past [JourneyStep.Place] is refused and sent back to the start.
     * Deep-linking into the ceremony would run the save with nothing to save,
     * and deep-linking into the portrait would ask the server to read a birth
     * this app never sent it.
     */
    fun open(startStep: Int) {
        if (opened) return
        opened = true
        val asked = JourneyStep.entries.getOrNull(startStep - 1) ?: JourneyStep.Name
        _step.value = if (asked > JourneyStep.Place) JourneyStep.Name else asked
        recordOnce(FunnelStage.LandingView)
    }

    /* ── moving ────────────────────────────────────────────────────────── */

    fun next() {
        recordOnce(FunnelStage.QuizStart)
        _step.update { current -> JourneyStep.entries.getOrElse(current.ordinal + 1) { current } }
    }

    fun back() {
        _step.update { current -> JourneyStep.entries.getOrElse(current.ordinal - 1) { current } }
    }

    /* ── answering ─────────────────────────────────────────────────────── */

    fun setName(name: String) = _draft.update { it.copy(name = name) }

    /** Told once by the screen, which is the only party holding a Context. */
    fun setTwelveHour(twelve: Boolean) = _draft.update { it.copy(twelveHour = twelve) }

    fun setDay(day: Int) = _draft.update { it.copy(day = day) }

    fun setMonth(month: Int) = _draft.update { it.copy(month = month) }

    fun setYear(year: Int) = _draft.update { it.copy(year = year) }

    fun setHour(hour: Int) = _draft.update { it.copy(hour = hour, timeUnknown = false) }

    fun setMinute(minute: Int) = _draft.update { it.copy(minute = minute, timeUnknown = false) }

    fun setMeridiem(meridiem: Meridiem) =
        _draft.update { it.copy(meridiem = meridiem, timeUnknown = false) }

    /**
     * "I don't know" is an answer, not a refusal to answer.
     *
     * Turning it on clears whatever was half-entered, so that the draft cannot
     * hold both a declared unknown and three-quarters of an hour. Both of those
     * are the same fact — we have no time — and only one of them used to say so.
     */
    fun setTimeUnknown(unknown: Boolean) = _draft.update {
        // The meridiem is not cleared, because it has a default and clearing it
        // to null is what this type no longer allows. Turning "I don't know"
        // back off leaves `AM` showing, which is what the field said all along.
        if (unknown) it.copy(timeUnknown = true, hour = null, minute = null)
        else it.copy(timeUnknown = false)
    }

    /* ── the gazetteer ─────────────────────────────────────────────────── */

    private var searchJob: Job? = null

    /**
     * Search the real gazetteer, debounced, with superseded requests cancelled.
     *
     * This is the one step the whole chart hangs on: the coordinate sets the
     * horizon and the timezone sets the instant, so it is worth a round trip per
     * pause in typing rather than a free-text field somebody can misspell.
     */
    fun onPlaceQuery(text: String) {
        _placeQuery.value = text
        // Cancelling first is what makes an older, slower answer unable to
        // overwrite a newer one — the same job an AbortController does on the web.
        searchJob?.cancel()
        _draft.update { it.copy(place = null) }

        val trimmed = text.trim()
        if (trimmed.length < 2) {
            _places.value = ScreenState.Loaded(emptyList())
            return
        }

        _places.value = ScreenState.Loading
        searchJob = viewModelScope.launch {
            delay(SEARCH_DEBOUNCE_MS)
            val result = client.searchPlaces(trimmed)
            // `AlmaClient` turns *every* throwable into a value, cancellation
            // included, so a cancelled search comes back as an ordinary failure
            // rather than unwinding. Without this line a superseded request
            // would publish that failure over a newer result.
            ensureActive()
            _places.value = result.toScreenState()
        }
    }

    /**
     * The whole place, not just its name.
     *
     * The chart needs the coordinate and the zone, and asking for them again
     * later would mean asking a question the person has already answered.
     */
    fun choosePlace(place: PlaceDto) {
        searchJob?.cancel()
        _placeQuery.value = place.label
        _places.value = ScreenState.Loaded(emptyList())
        _draft.update { it.copy(place = place) }
    }

    /* ── the ceremony, and the save under it ───────────────────────────── */

    private var ceremonyBegun = false

    /**
     * Start the ~9 second ceremony's real work.
     *
     * Idempotent, because the composable that calls it is re-entered on every
     * configuration change and a second call would save the birth twice.
     *
     * The quiz *completes* here rather than on the portrait. Every question has
     * been answered by the time this runs; conflating "answered everything" with
     * "saw the result" would hide exactly the people the save fails for.
     */
    fun beginCeremony() {
        if (ceremonyBegun) return
        ceremonyBegun = true
        recordOnce(FunnelStage.QuizComplete)
        loadPortrait()
    }

    fun onPortraitShown() = recordOnce(FunnelStage.PortraitView)

    /**
     * Save the birth, then read the three systems the portrait shows.
     *
     * The save happens under the ceremony and not a step earlier: somebody who
     * abandons at the time step has not asked us to keep anything. Not a step
     * later either — the ceremony runs about nine seconds, which is exactly the
     * cover a round trip needs, so the portrait usually has its answers by the
     * time it is drawn.
     *
     * The three calculations go together rather than in sequence. They are
     * independent, they are free — the ephemeris is a static local file on the
     * server — and three round trips one after another would spend the
     * ceremony's whole budget on waiting.
     */
    private fun loadPortrait() {
        viewModelScope.launch {
            _portrait.value = ScreenState.Loading

            val birth = _draft.value.toBirthInput()
            if (birth == null) {
                // Reachable only by a bug in this app: the place step will not
                // let anybody past without a place and the date step will not
                // let anybody past without a real date.
                _portrait.value = ScreenState.Failed(
                    ApiFailure.Invalid("the journey finished without a date or a place")
                )
                return@launch
            }

            // The device's language rides along so any refusal on this save
            // arrives in it — the account's stored locale may still be the
            // minting default at this point in a first run.
            val spoken = java.util.Locale.getDefault().toLanguageTag()
            when (val saved = client.saveProfile(birth.copy(locale = spoken))) {
                is ApiResult.Err -> {
                    _portrait.value = ScreenState.Failed(saved.failure)
                    return@launch
                }
                is ApiResult.Ok -> session.onProfileSaved(saved.data)
            }

            // No `birth` in the request: these read the profile that was just
            // saved, which is the same thing every cabinet screen will do
            // tomorrow. Reading the chart back out of the server is also the
            // only honest proof that it was stored at all.
            val natal = async { client.system(AlmaSystem.NATAL, CalcRequest()) }
            val numerology = async { client.system(AlmaSystem.NUMEROLOGY, CalcRequest()) }
            val card = async { client.system(AlmaSystem.BIRTH_CARD, CalcRequest()) }

            val results = listOf(natal.await(), numerology.await(), card.await())
            val firstFailure = results.filterIsInstance<ApiResult.Err>().firstOrNull()

            // A portrait with one row on it is still a portrait. Only when
            // nothing at all came back is there nothing to show, and then the
            // person is told why rather than shown an empty page.
            _portrait.value = if (results.all { it is ApiResult.Err } && firstFailure != null) {
                ScreenState.Failed(firstFailure.failure)
            } else {
                ScreenState.Loaded(
                    portraitFrom(
                        name = _draft.value.name.trim(),
                        natal = (results[0] as? ApiResult.Ok)?.data,
                        numerology = (results[1] as? ApiResult.Ok)?.data,
                        card = (results[2] as? ApiResult.Ok)?.data,
                    )
                )
            }
        }
    }

    /** Try the save and the three readings again. Safe: a second self replaces the first. */
    fun retryPortrait() = loadPortrait()

    private companion object {
        /**
         * Long enough that a fast typist makes one request instead of nine,
         * short enough that the list feels like it is keeping up. The web app
         * settled on the same number.
         */
        const val SEARCH_DEBOUNCE_MS = 180L
    }
}

/* ══ what the journey collects ═════════════════════════════════════════ */


enum class Meridiem { Am, Pm }

/**
 * The steps, in order, and the order is the whole navigation model.
 *
 * This is the reference implementation's own answer for the case where the date
 * was not captured before the journey opened — which on Android is every case,
 * because there is no landing page in front of the app. `Routes.journey(step)`
 * is one-based over this list, so step 3 is the date: that is the step the
 * cabinet's "enter my birth data" sends people to.
 */
enum class JourneyStep {
    // **The intent question is gone — the owner's call, ported from iOS.**
    // It asked what was loudest in you and used the answer to pick which door
    // to offer; but all eight systems are computed for everybody from the same
    // four facts, so nothing downstream needed it. One whole screen between a
    // person and the thing they came for, buying one line of copy.
    Name, Date, Time, Place, Ceremony, Portrait, Handoff;

    /**
     * Where a back gesture is a step and not an exit.
     *
     * Not on the first step — there is nothing behind it. The ceremony is
     * doing something, the portrait is the reward and the handoff is the door
     * out; backing into any of the three would replay work or unwind a birth
     * that is already saved.
     */
    val canGoBack: Boolean get() = this in Date..Place
}

/**
 * Everything typed so far. Every field starts empty, and that is the point.
 *
 * The reference chart's birthday used to sit pre-filled in every visitor's form.
 * It looked like a courtesy and it meant the first "insight" a person ever saw
 * was calculated from a stranger's birth.
 */
@Immutable
data class JourneyDraft(
    /**
     * Whether this phone writes times as 1 PM or as 13:00.
     *
     * AM/PM is a local convention and the app was charging everybody for it:
     * outside the twelve-hour countries people do not reliably know which
     * half of the day "AM" is, and a birth entered as 7 AM when it was 19:00
     * is a chart with the wrong Ascendant and no way to notice. Read from the
     * system's own setting by the screen and stored here so `birthTime` can
     * convert correctly without a Context.
     */
    val twelveHour: Boolean = true,
    val name: String = "",
    val day: Int? = null,
    /** 1–12, never a month name: "März" has to become 3 and the word it came from is per-locale. */
    val month: Int? = null,
    val year: Int? = null,
    /** 1–12 as people say it, converted to 24-hour form only on the way out. */
    val hour: Int? = null,
    val minute: Int? = null,
    /**
     * **Defaulted, not null**, and the difference cost somebody their birth time
     * on a device before it was caught.
     *
     * The picker beside the hour and the minute shows "AM" whether or not
     * anything has been chosen — the web app does the same, `placeholder="AM"`
     * over a null value — so a person who picks 04 and 00 sees `04 · 00 · AM`
     * and has every reason to believe they have entered four in the morning.
     * With this nullable and required by [hasTime], they had entered nothing:
     * the time was silently dropped, the portrait said NEEDS BIRTH TIME, no
     * Ascendant appeared, and there was no way to tell why. Verified on the
     * emulator — the profile row came back with `birth_time: None`.
     *
     * So the field now holds what it displays. Somebody who taps straight
     * through still has no time, because [hasTime] needs an hour and a minute
     * as well, and a default meridiem cannot invent either of those.
     */
    val meridiem: Meridiem = Meridiem.Am,
    val timeUnknown: Boolean = false,
    val place: PlaceDto? = null,
) {

    /** All three parts chosen — which is not the same as the date existing. */
    val dateChosen: Boolean get() = day != null && month != null && year != null

    /**
     * The date, if there is one, as the API spells it.
     *
     * Null for 31 February. Three independent pickers can name a day that never
     * happened, and the alternative to catching it here is a 422 nine seconds
     * later, under a ceremony that deliberately does not surface failures.
     */
    val birthDate: String?
        get() {
            if (!dateChosen) return null
            return runCatching {
                LocalDate.of(year!!, month!!, day!!).format(DateTimeFormatter.ISO_LOCAL_DATE)
            }.getOrNull()
        }

    /**
     * Whether a real birth *time* was entered.
     *
     * Declared unknown and simply never filled in are the same fact, and both
     * have to produce a null rather than a guess. The dangerous version of this
     * coerces a blank hour to zero and quietly sends midnight.
     */
    val hasTime: Boolean
        get() = !timeUnknown && hour != null && minute != null

    /**
     * Twelve-hour to twenty-four hour, with the pair every naive conversion gets
     * backwards: 12 AM is midnight and 12 PM is noon. Getting it backwards moves
     * the Ascendant half a circle and still produces a chart that looks
     * perfectly reasonable.
     */
    val birthTime: String?
        get() {
            if (!hasTime) return null
            // On a 24-hour phone the hour field already is the hour; there is
            // nothing to convert and nothing to have got backwards.
            val hours = if (twelveHour) {
                (hour!! % 12) + if (meridiem == Meridiem.Pm) 12 else 0
            } else {
                hour!!
            }
            return "%02d:%02d".format(hours, minute!!)
        }

    /** Which system the offer at the end is about. The natal chart, for everybody. */
    val system: String get() = AlmaSystem.NATAL

    fun toBirthInput(): BirthInput? {
        val date = birthDate ?: return null
        val where = place ?: return null
        return BirthInput(
            birthDate = date,
            // Unknown stays unknown. The backend is built to answer honestly
            // about what it cannot compute without an hour.
            birthTime = birthTime,
            latitude = where.latitude,
            longitude = where.longitude,
            timezone = where.timezone,
            placeLabel = where.label,
            placeId = where.id,
            name = name.trim().ifBlank { null },
            // Said out loud, and it has to be: an unstated `is_self` means "mine"
            // only for the first birth an account saves, and this journey is
            // sometimes re-walked by somebody correcting their own data.
            isSelf = true,
        )
    }
}

/* ══ the portrait ══════════════════════════════════════════════════════ */

/**
 * What the portrait is allowed to say, and every field of it was calculated.
 *
 * Nullable throughout on purpose. A row whose request has not answered is
 * *dropped*, never filled with a plausible stand-in — this is the one screen
 * whose entire job is to prove the calculation is real, and it is the screen
 * where the web app was found showing a fixed Moon in Scorpio and a fixed
 * Ascendant to every visitor alive.
 */
@Immutable
data class Portrait(
    val name: String,
    /** The engine's English sign name — translated for display, kept raw here. */
    val sunSign: String? = null,
    val sunGlyph: String? = null,
    val moonSign: String? = null,
    /**
     * Present only when a birth time was given: the backend refuses to compute a
     * horizon without one, and this is the screen where that refusal is most
     * worth showing rather than hiding.
     */
    val risingSign: String? = null,
    val lifePath: Int? = null,
    val cardNumeral: String? = null,
    val cardName: String? = null,
    val moonPhase: String? = null,
    val timeKnown: Boolean = false,
)

private fun portraitFrom(
    name: String,
    natal: CalcResultDto?,
    numerology: CalcResultDto?,
    card: CalcResultDto?,
): Portrait {
    // Locked is the ordinary case here — nobody has paid yet — and the trimmed
    // payload still carries the three signs, the life path and the card, which
    // is all this screen shows. See `PREVIEW_FIELDS` in the backend's systems
    // router for exactly what survives the trim.
    val chart = natal?.data
    val numbers = numerology?.data
    val cardData = card?.data

    // `text`, `int`, `bool` and `obj` come from `CabinetCommon.kt`: the `data`
    // object on a calculation is deliberately untyped — each of the eight
    // systems returns a different engine-shaped payload that changes when the
    // ephemeris code does — and the cabinet already had to decode slices of it
    // by hand. One set of readers, so the portrait and the chart screen cannot
    // disagree about what an absent field means.
    return Portrait(
        name = name,
        sunSign = chart?.text("sun_sign"),
        sunGlyph = chart?.obj("placements")?.obj("sun")?.text("sign_glyph"),
        moonSign = chart?.text("moon_sign"),
        risingSign = chart?.text("rising_sign"),
        lifePath = numbers?.int("life_path"),
        cardNumeral = cardData?.obj("personality")?.text("numeral"),
        cardName = cardData?.obj("personality")?.text("name"),
        moonPhase = chart?.obj("moon_phase")?.text("phase"),
        timeKnown = chart?.bool("time_known") == true,
    )
}
