package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.core.ScreenState
import ai.pazl.alma.core.SessionHolder
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.data.dto.CalcRequest
import ai.pazl.alma.data.dto.CalcResultDto
import ai.pazl.alma.data.dto.ChapterEntryDto
import ai.pazl.alma.data.dto.SphereBlockDto
import ai.pazl.alma.ui.components.GoldButton
import ai.pazl.alma.ui.components.StateHost
import ai.pazl.alma.ui.components.riseIn
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaSpacing
import ai.pazl.alma.ui.theme.AlmaTheme
import ai.pazl.alma.ui.theme.PillShape
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonObject
import java.util.Locale

/**
 * One system, in full: its free calculated data, its chapter list, and the price
 * of the words.
 *
 * The split down the middle of this screen *is* the product. Every calculation
 * is free forever, because the ephemeris and the gazetteer are static files and
 * computing a chart costs us nothing; what is sold is the writing. So the
 * numbers are shown in full, always, even to somebody who has bought nothing —
 * and a locked system still answers with its preview fields, which is why the
 * block above the chapter list is never empty.
 *
 * Three requests. The chapter list is the frame. The calculation is the free
 * half. The catalogue is the *price* — read from `display`, never formatted
 * here, because the ladder is regional and a hardcoded "$5.99" is wrong in
 * twelve currencies before it is wrong in the thirteenth.
 *
 * Cross-synthesis comes through this same screen rather than getting a route of
 * its own, because on Android it is one of the eight rows in `systems/{slug}`
 * and a second destination for it would be a second back stack for the same
 * place. What differs is only what its free data looks like: nine axes and
 * three counts instead of placements.
 */
@Composable
fun SystemDetailScreen(
    container: AppContainer,
    system: String,
    onOpenChapter: (String) -> Unit,
    onOffer: () -> Unit,
    onBack: () -> Unit,
) {
    val vm: SystemDetailViewModel = viewModel(key = system) {
        SystemDetailViewModel(container.client, container.session, system)
    }
    val state by vm.state.collectAsStateWithLifecycle()
    val spheres by vm.spheres.collectAsStateWithLifecycle()
    val sessionState by container.session.state.collectAsStateWithLifecycle()
    // Whole years since the owner's birth date, for the numerology ring's
    // "you are here" tick. Null when unparsable — the ring then simply draws
    // no tick rather than guessing one.
    val age = sessionState.profile?.birthDate?.let { birth ->
        runCatching {
            java.time.Period.between(java.time.LocalDate.parse(birth), java.time.LocalDate.now()).years
        }.getOrNull()?.takeIf { it >= 0 }
    }

    // A distinct sky per system, and a **non-negative** one: `FusedSky` derives
    // the comet's stagger from `seed % 5` and hands it to `tween` as a delay, so
    // a negative seed would be a negative delay and a crash. The slug's index is
    // small, stable and never negative.
    NightSky(config = SkyConfig.Reader.copy(seed = 20 + AlmaSystem.ALL.indexOf(system).coerceAtLeast(0))) {
        StateHost(state, onRetry = vm::reload) { detail ->
            SystemDetailBody(
                detail,
                spheres = spheres,
                age = age,
                onOpenChapter = onOpenChapter,
                onOffer = onOffer,
                onBack = onBack,
            )
        }
    }
}

/* ── what the screen holds ─────────────────────────────────────────────── */

@Immutable
data class SystemDetailView(
    val slug: String,
    val chapters: List<ChapterEntryDto>,
    val total: Int,
    /**
     * The calculation, or null because its request failed.
     *
     * The chapter list survives without it — a person can still open what they
     * have paid for — so a failed chart hides the free-data block rather than
     * taking the screen down with it.
     */
    val result: CalcResultDto?,
    /**
     * The price of this system's door, already formatted by the server in this
     * account's currency. Blank when the catalogue could not be read, and then
     * the button says what it opens without quoting a figure — a remembered
     * price is a quote, and a wrong one is a quote we would have to honour.
     */
    val price: String,
)

class SystemDetailViewModel(
    private val client: AlmaClient,
    private val session: SessionHolder,
    private val slug: String,
) : ViewModel() {

    private val _state = MutableStateFlow<ScreenState<SystemDetailView>>(ScreenState.Loading)
    val state: StateFlow<ScreenState<SystemDetailView>> = _state.asStateFlow()

    /**
     * The free preview of the chart, natal only, loaded *after* the fast pair.
     *
     * Loading for everybody else too would be harmless — the request is never
     * made — but the state starts as Loading and a non-natal screen must not
     * sit on a spinner for a section it will never draw, so it is flipped to
     * Failed immediately for every other slug.
     */
    private val _spheres = MutableStateFlow<ScreenState<List<SphereBlockDto>>>(ScreenState.Loading)
    val spheres: StateFlow<ScreenState<List<SphereBlockDto>>> = _spheres.asStateFlow()

    private var running: Job? = null

    init {
        reload()
    }

    fun reload() {
        running?.cancel()
        running = viewModelScope.launch {
            _state.value = ScreenState.Loading
            val account = session.state.first { it.ready }

            // Fired alongside the fast pair rather than after it: the first
            // write takes seconds on the cheap model, and the section shows its
            // own quiet "reading" row until the answer lands. Everything else
            // on the screen renders without waiting for this.
            if (slug == AlmaSystem.NATAL) {
                launch {
                    _spheres.value = ScreenState.Loading
                    var answer = client.natalSpheres(account.locale)
                    // One automatic second try for weather-class failures —
                    // a person should not be the retry loop.
                    if (answer is ApiResult.Err &&
                        (answer.failure is ApiFailure.Unavailable || answer.failure is ApiFailure.Offline)
                    ) {
                        kotlinx.coroutines.delay(2_000)
                        answer = client.natalSpheres(account.locale)
                    }
                    _spheres.value = when (answer) {
                        is ApiResult.Ok -> ScreenState.Loaded(answer.data.spheres)
                        is ApiResult.Err -> ScreenState.Failed(answer.failure)
                    }
                }
            } else {
                _spheres.value = ScreenState.Failed(ApiFailure.Invalid("not natal"))
            }

            val (chapters, result, catalogue) = coroutineScope {
                val chaptersCall = async { client.chapters(slug, account.locale) }
                val resultCall = async { client.system(slug, CalcRequest(locale = account.locale)) }
                val catalogueCall = async { client.catalogue() }
                Triple(chaptersCall.await(), resultCall.await(), catalogueCall.await())
            }

            _state.value = when (chapters) {
                is ApiResult.Err -> ScreenState.Failed(chapters.failure)
                is ApiResult.Ok -> ScreenState.Loaded(
                    SystemDetailView(
                        slug = slug,
                        chapters = chapters.data.chapters,
                        total = chapters.data.total,
                        result = (result as? ApiResult.Ok)?.data,
                        // The eight system doors are keyed by the system's own
                        // slug in the catalogue, which is also what the Play
                        // product ids have to be called.
                        price = (catalogue as? ApiResult.Ok)?.data?.items
                            ?.firstOrNull { it.slug == slug }?.display.orEmpty(),
                    )
                )
            }
        }
    }
}

/* ── the screen ────────────────────────────────────────────────────────── */

@Composable
private fun SystemDetailBody(
    detail: SystemDetailView,
    spheres: ScreenState<List<SphereBlockDto>>,
    age: Int?,
    onOpenChapter: (String) -> Unit,
    onOffer: () -> Unit,
    onBack: () -> Unit,
) {
    val name = systemName(detail.slug)
    val locked = detail.result?.locked ?: detail.chapters.any { !it.`open` }
    val natal = detail.slug == AlmaSystem.NATAL

    Box(Modifier.fillMaxSize()) {
        CabinetPage {
            Box(Modifier.riseIn(0)) { ScreenTitle(name, onBack = onBack) }

            // The natal screen opens the way the reference the owner chose
            // does: the wheel, then the placements in words, then short free
            // interpretations per sphere — and only then the chapter list.
            if (natal) {
                detail.result?.let { result ->
                    Spacer(Modifier.height(22.dp))
                    NatalWheel(result.`data`, modifier = Modifier.riseIn(1))
                    Column(Modifier.riseIn(2)) {
                        PlacementList(result.`data`)
                        // The spheres block («что говорит карта») stood here
                        // and was cut whole — the chapters follow directly.
                    }
                }
            } else {
                detail.result?.let { result ->
                    Spacer(Modifier.height(22.dp))
                    // The system's own diagram first — the picture the natal
                    // reference opens with, honest to this system's payload.
                    // See `SystemArt.kt` for the seven designs.
                    SystemHeroArt(detail.slug, result.`data`, age, modifier = Modifier.riseIn(1))
                    if (detail.slug == AlmaSystem.COMPATIBILITY) {
                        Spacer(Modifier.height(14.dp))
                        // The four axes as gauges — the number the category
                        // sells with, honestly ours.
                        CompatGauges(result.`data`, modifier = Modifier.riseIn(2))
                    }
                    Spacer(Modifier.height(10.dp))
                    Column(Modifier.riseIn(2)) {
                        RuledLabel(stringResource(R.string.cabinet_free_data))
                        Spacer(Modifier.height(14.dp))
                        FreeData(detail.slug, result)
                    }
                }
            }

            Spacer(Modifier.height(28.dp))
            Column(Modifier.riseIn(3)) {
                RuledLabel(
                    text = stringResource(R.string.cabinet_chapter_count, detail.total),
                    trailing = "${detail.chapters.count { it.`open` }} " +
                        stringResource(R.string.cabinet_open),
                )
                val sunSign = detail.result?.`data`?.text("sun_sign")
                detail.chapters.forEachIndexed { index, chapter ->
                    // The free natal chapter carries the person's own headline
                    // — «Солнце — Овен» — instead of an abstract title.
                    val entry = if (natal && chapter.free && sunSign != null) {
                        chapter.copy(
                            title = stringResource(R.string.sun_in_sign, signWord(sunSign))
                        )
                    } else chapter
                    ChapterRow(
                        chapter = entry,
                        last = index == detail.chapters.lastIndex,
                        onClick = { onOpenChapter(chapter.slug) },
                    )
                }
            }

            // The raw free data still closes the natal page — the pills and the
            // strongest aspects, below the doors, for whoever wants notation.
            if (natal) {
                detail.result?.let { result ->
                    Spacer(Modifier.height(28.dp))
                    Column(Modifier.riseIn(4)) {
                        RuledLabel(stringResource(R.string.cabinet_free_data))
                        Spacer(Modifier.height(14.dp))
                        FreeData(detail.slug, result)
                    }
                }
            }

            // Room for the bar, so the last chapter is reachable rather than
            // permanently under it.
            Spacer(Modifier.height(if (locked) 132.dp else 24.dp))
        }

        if (locked) {
            OpenAllBar(detail, name, onOffer, Modifier.align(Alignment.BottomCenter))
        }
    }
}

/**
 * The one gold button on the screen, with the price printed on it.
 *
 * It sells the **system**, never the chapter. Single chapters were withdrawn
 * from the ladder, so a per-chapter figure here would either be the whole
 * system's price beside one sixteenth of it or a number from a tier that no
 * longer exists — and the checkout behind it would answer 404.
 */
@Composable
private fun OpenAllBar(
    detail: SystemDetailView,
    name: String,
    onOffer: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val label = when {
        detail.price.isBlank() && detail.slug == AlmaSystem.NATAL ->
            stringResource(R.string.cabinet_open_all_chapters_no_price, detail.total)
        detail.price.isBlank() ->
            stringResource(R.string.cabinet_open_system_no_price, name)
        detail.slug == AlmaSystem.NATAL ->
            stringResource(R.string.cabinet_open_all_chapters, detail.total, detail.price)
        else ->
            stringResource(R.string.cabinet_open_system, name, detail.price)
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            // A wash rather than a filled bar: content scrolling underneath has
            // to stay legible without the button sitting in a box. Three stops
            // and not two — a straight fade left the top of the button sitting
            // over a chapter title at about 40 % opacity, which read as a
            // rendering fault rather than as depth. The night is fully arrived
            // by the time the button starts.
            .background(
                Brush.verticalGradient(
                    0.00f to Color.Transparent,
                    0.32f to AlmaPalette.Night800.copy(alpha = 0.86f),
                    1.00f to AlmaPalette.Night800.copy(alpha = 0.98f),
                )
            )
            .padding(start = AlmaSpacing.Pad, end = AlmaSpacing.Pad, top = 34.dp, bottom = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        GoldButton(text = label, onClick = onOffer, modifier = Modifier.fillMaxWidth())
        Text(
            text = stringResource(R.string.cabinet_one_time_note),
            style = AlmaTheme.type.meta,
            textAlign = TextAlign.Center,
        )
    }
}

/**
 * One chapter in the list.
 *
 * A locked row shows what the chapter is and that it is closed, and nothing
 * else. It does not show a blurred paragraph: we hold no copy of a chapter this
 * account has not opened, because nothing is written until it is first asked
 * for — blurring a sentence here would mean blurring a sentence written about
 * somebody else.
 */
@Composable
private fun ChapterRow(chapter: ChapterEntryDto, last: Boolean, onClick: () -> Unit) {
    CabinetRow(rule = !last, onClick = onClick) {
        Column(Modifier.weight(1f)) {
            Text(
                text = "${chapter.numeral} · ${chapter.title}",
                style = AlmaTheme.type.headingM,
                color = if (chapter.`open`) AlmaPalette.InkLight else AlmaPalette.Muted,
            )
            // The question subtitles are gone — the owner's verdict was that
            // half of them read as broken grammar and none of them helped.
        }
        // The status tag is gone too, on both platforms and for the same
        // reason: «Бесплатно» / «Разблокировано» / «Заблокировано» at the end
        // of every row turned a table of contents into a price list. What is
        // open stays legible in the title's colour above, which is as loud as
        // this distinction needs to be. Nothing replaces the tag.
    }
}

/* ── the natal page's own sections ─────────────────────────────────────── */

/** The order a printed chart lists bodies in, which the payload does not carry. */
private val PlacementOrder = listOf(
    "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
    "uranus", "neptune", "pluto", "true_node", "chiron", "lilith",
)

/**
 * Every placement, in words: "Moon — 23°14′ Pisces · 8th house".
 *
 * The same facts the wheel just drew, spelled out in the reader's language,
 * because a citation nobody can read cites nothing.
 */
@Composable
private fun ColumnScope.PlacementList(chart: JsonObject) {
    val placements = chart.obj("placements") ?: return
    val planets = PlacementOrder.mapNotNull { name ->
        val placement = placements.obj(name) ?: return@mapNotNull null
        val formatted = placement.text("formatted") ?: return@mapNotNull null
        val retro = placement.bool("retrograde") == true
        val label = bodyWord(name) +
            if (retro) " · " + stringResource(R.string.daily_retrograde) else ""
        val value = spellSigns(formatted) +
            (placement.int("house")?.let { " · " + houseWord(it) } ?: "")
        label to value
    }
    // The derived points after the planets — the Midheaven, the south node,
    // the Part of Fortune, the Vertex — from the payload's `points` block. A
    // point the engine could not compute (no birth time) simply has no row.
    val points = chart.obj("points")
    val derived = listOf(
        "midheaven" to R.string.body_midheaven,
        "south_node" to R.string.body_south_node,
        "part_of_fortune" to R.string.body_part_of_fortune,
        "vertex" to R.string.body_vertex,
    ).mapNotNull { (name, labelRes) ->
        val point = points?.obj(name) ?: return@mapNotNull null
        val formatted = point.text("formatted") ?: return@mapNotNull null
        val value = spellSigns(formatted) +
            (point.int("house")?.let { " · " + houseWord(it) } ?: "")
        stringResource(labelRes) to value
    }
    val rows = planets + derived
    if (rows.isEmpty()) return

    Spacer(Modifier.height(28.dp))
    RuledLabel(stringResource(R.string.cabinet_placements_label))
    rows.forEachIndexed { index, (label, value) ->
        CabinetRow(rule = index < rows.lastIndex) {
            Text(text = label, style = AlmaTheme.type.meta, modifier = Modifier.weight(1f))
            Text(text = value, style = AlmaTheme.type.positions)
        }
    }
}

/**
 * The free taste of the chart: five spheres, two or three plain sentences each,
 * every one ending on the door to the chapter that finishes the thought.
 *
 * The preview is a bonus, not a wall: a screen that has the wheel, the
 * placements and the chapters loses nothing it cannot live without, so a failed
 * request draws silence rather than an error block.
 */
@Composable
private fun ColumnScope.SpheresSection(
    spheres: ScreenState<List<SphereBlockDto>>,
    onOpenChapter: (String) -> Unit,
) {
    when (spheres) {
        is ScreenState.Loading -> {
            Spacer(Modifier.height(28.dp))
            RuledLabel(stringResource(R.string.cabinet_spheres_label))
            Spacer(Modifier.height(14.dp))
            Text(
                text = stringResource(R.string.state_reading_chart),
                style = AlmaTheme.type.meta,
            )
        }
        is ScreenState.Failed -> Unit
        is ScreenState.Loaded -> {
            if (spheres.data.isEmpty()) return
            Spacer(Modifier.height(28.dp))
            RuledLabel(stringResource(R.string.cabinet_spheres_label))
            spheres.data.forEach { sphere ->
                Column(Modifier.padding(vertical = 10.dp)) {
                    Text(text = sphere.title, style = AlmaTheme.type.headingM)
                    Text(
                        text = sphere.text,
                        style = AlmaTheme.type.almaVoice,
                        modifier = Modifier.padding(top = 6.dp),
                    )
                    CabinetRow(onClick = { onOpenChapter(sphere.chapter) }, rule = false) {
                        Text(
                            text = stringResource(R.string.cabinet_full_reading),
                            style = AlmaTheme.type.meta,
                            color = AlmaPalette.Gold,
                            modifier = Modifier.weight(1f),
                        )
                        Text(text = "→", style = AlmaTheme.type.positions)
                    }
                }
            }
        }
    }
}

/* ── the free half, one shape per system ───────────────────────────────── */

/**
 * What each system shows for nothing.
 *
 * The eight branches mirror `PREVIEW_FIELDS` in `alma/api/routers/systems.py`,
 * which is the list of fields the server keeps when it trims a locked payload.
 * Anything read here that is *not* in that list simply does not arrive while the
 * system is locked, and every reader below answers null rather than a default —
 * so a locked screen loses rows instead of filling them with zeros.
 */
@Composable
private fun ColumnScope.FreeData(slug: String, result: CalcResultDto) {
    val data = result.`data`
    when (slug) {
        AlmaSystem.NATAL -> NatalFreeData(data)
        AlmaSystem.NUMEROLOGY -> ValueRows(
            listOf(
                stringResource(R.string.num_life_path) to data.int("life_path")?.toString(),
                stringResource(R.string.num_birthday) to data.int("birthday_number")?.toString(),
                stringResource(R.string.num_destiny) to data.int("destiny_number")?.toString(),
            )
        )
        AlmaSystem.BIRTH_CARD -> BirthCardFreeData(data)
        AlmaSystem.TRANSITS -> ValueRows(
            listOf(
                stringResource(R.string.cabinet_active_now) to
                    data.int("active_count")?.toString(),
                dayAndMonth(data.obj("window")?.text("from")).orEmpty() to
                    data.obj("window")?.int("days")
                        ?.let { stringResource(R.string.transits_days, it) },
            )
        )
        AlmaSystem.SOLAR_RETURN -> ValueRows(
            listOf(
                stringResource(R.string.sr_year) to data.int("year")?.toString(),
                stringResource(R.string.sr_return_at) to readableDate(data.text("return_at"))
                    .ifBlank { null },
                stringResource(R.string.sr_ruler) to data.text("year_ruler")?.let { bodyWord(it) },
            )
        )
        AlmaSystem.COMPATIBILITY -> ScoreRows(data.obj("scores"))
        AlmaSystem.ASTROCARTOGRAPHY -> {
            val place = data.obj("birthplace")
            ValueRows(listOf(stringResource(R.string.geo_birthplace) to place?.text("text")))
        }
        AlmaSystem.SYNTHESIS -> SynthesisFreeData(data)
        // A ninth system the backend serves and this build has never heard of.
        // Its chapters still list and still open; only the free block is blank,
        // which is better than guessing at the shape of its payload.
        else -> Unit
    }

    // What could not be computed, said rather than left as a gap. These are the
    // engine's own English phrases — "houses (no birth time)" — and translating
    // them would mean translating a set that changes with the ephemeris code.
    if (result.unavailable.isNotEmpty()) {
        Text(
            text = result.unavailable.joinToString(" · "),
            style = AlmaTheme.type.meta,
            color = AlmaPalette.Muted3,
            modifier = Modifier.padding(top = 14.dp),
        )
    }
}

/**
 * The tightest aspects, and nothing above them.
 *
 * Three pills — Sun, Moon, Ascendant — and a fourth for the dominant element
 * used to open this block, which sits *below* the chapter list. The wheel draws
 * all three at the top of the screen and `PlacementList` spells them out in
 * words in between, so this was a third printing in the one place a reader has
 * stopped looking for a summary. The owner's question about the element pill —
 * «Огонь, что это, к чему оно тут?» — is the argument: a word alone in a
 * capsule says nothing about what was counted or why it matters.
 *
 * iOS lost the same four pills in the same commit; see `NatalPanel`.
 */
@Composable
private fun ColumnScope.NatalFreeData(chart: JsonObject) {
    val placements = chart.obj("placements")
    val aspects = chart.array("aspects").orEmpty().filterIsInstance<JsonObject>().take(3)
    if (aspects.isNotEmpty()) {
        Spacer(Modifier.height(22.dp))
        RuledLabel(stringResource(R.string.cabinet_strongest_aspects))
        aspects.forEachIndexed { index, aspect ->
            val orb = aspect.number("orb") ?: return@forEachIndexed
            CabinetRow(rule = index < aspects.lastIndex) {
                Text(
                    text = listOfNotNull(
                        glyphOf(placements, aspect.text("first")),
                        aspect.text("glyph"),
                        glyphOf(placements, aspect.text("second")),
                    ).joinToString(" "),
                    style = AlmaTheme.type.positions,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = formatOrb(orb),
                    style = AlmaTheme.type.positions,
                    // Agreement green, disagreement red, gold for everything
                    // between. A contradiction is material here rather than an
                    // error, which is why the product has no other red.
                    color = when (aspect.text("harmony")) {
                        "harmonious" -> AlmaPalette.Agree
                        "tense" -> AlmaPalette.Disagree
                        else -> AlmaPalette.GoldBright
                    },
                )
            }
        }
    }
}

@Composable
private fun ColumnScope.BirthCardFreeData(data: JsonObject) {
    val card = data.obj("personality") ?: return
    val numeral = card.text("numeral")
    val cardName = card.text("name") ?: return
    Text(
        text = stringResource(R.string.card_personality),
        style = AlmaTheme.type.meta,
    )
    Text(
        // The engine speaks English — "Justice", "The Star" — because factors
        // are verbatim identifiers; the reader meets their own language here.
        text = listOfNotNull(numeral, arcanaWord(cardName)).joinToString(" · "),
        style = AlmaTheme.type.displayL,
        modifier = Modifier.padding(top = 6.dp),
    )
    val meta = listOfNotNull(
        card.text("element")?.let { elementNameOrSelf(it) },
        card.text("ruler")?.let(::bodyName),
    ).joinToString(" · ")
    if (meta.isNotBlank()) {
        Text(text = meta, style = AlmaTheme.type.positions, modifier = Modifier.padding(top = 6.dp))
    }
}

/**
 * The card's element is a tarot element rather than an astrological one, and the
 * two vocabularies only partly overlap. Anything the string table names is
 * translated; anything else keeps the engine's word.
 */
@Composable
private fun elementNameOrSelf(element: String): String = elementName(element.lowercase())

/** The major arcana, translated for display; an unknown name keeps the
 * engine's own word rather than falling to silence. */
@Composable
internal fun arcanaWord(english: String): String {
    val id = when (english) {
        "The Fool" -> R.string.arcana_the_fool
        "The Magician" -> R.string.arcana_the_magician
        "The High Priestess" -> R.string.arcana_the_high_priestess
        "The Empress" -> R.string.arcana_the_empress
        "The Emperor" -> R.string.arcana_the_emperor
        "The Hierophant" -> R.string.arcana_the_hierophant
        "The Lovers" -> R.string.arcana_the_lovers
        "The Chariot" -> R.string.arcana_the_chariot
        "Strength" -> R.string.arcana_strength
        "The Hermit" -> R.string.arcana_the_hermit
        "Wheel of Fortune" -> R.string.arcana_wheel_of_fortune
        "Justice" -> R.string.arcana_justice
        "The Hanged Man" -> R.string.arcana_the_hanged_man
        "Death" -> R.string.arcana_death
        "Temperance" -> R.string.arcana_temperance
        "The Devil" -> R.string.arcana_the_devil
        "The Tower" -> R.string.arcana_the_tower
        "The Star" -> R.string.arcana_the_star
        "The Moon" -> R.string.arcana_the_moon
        "The Sun" -> R.string.arcana_the_sun
        "Judgement" -> R.string.arcana_judgement
        "The World" -> R.string.arcana_the_world
        else -> return english
    }
    return stringResource(id)
}

@Composable
private fun ColumnScope.ScoreRows(scores: JsonObject?) {
    if (scores == null) return
    val rows = scores.keys.mapNotNull { key -> scores.number(key)?.let { key to it } }
    rows.forEachIndexed { index, (key, value) ->
        CabinetRow(rule = index < rows.lastIndex) {
            Text(text = scoreName(key), style = AlmaTheme.type.meta, modifier = Modifier.weight(1f))
            // One decimal, in the device's own number format so a German reader
            // gets a comma. These are weight sums rather than percentages, and
            // rounding one to "8" would invite reading it as a score out of ten.
            Text(
                text = String.format(Locale.getDefault(), "%.1f", value),
                style = AlmaTheme.type.positions,
            )
        }
    }
}

/**
 * The synthesis: three counts that survive the lock, and the nine axes that do
 * not.
 *
 * An absent `axes` means "not paid for yet", never "the systems had nothing to
 * say" — the server trims it to the counts before the response leaves. So a
 * locked screen shows the counts and the door, rather than an empty list of axes
 * that would read as a calculation with nothing in it.
 */
@Composable
private fun ColumnScope.SynthesisFreeData(data: JsonObject) {
    Text(text = stringResource(R.string.synthesis_title), style = AlmaTheme.type.headingM)
    Text(
        text = stringResource(R.string.synthesis_lead),
        style = AlmaTheme.type.meta,
        modifier = Modifier.padding(top = 8.dp),
    )

    val agree = data.int("agreements")
    val disagree = data.int("disagreements")
    val single = data.int("single_voice")
    if (agree != null || disagree != null || single != null) {
        FlowRow(
            modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            agree?.let { Chip(stringResource(R.string.synthesis_agree, it), AlmaPalette.Agree) }
            disagree?.let {
                Chip(stringResource(R.string.synthesis_disagree, it), AlmaPalette.Disagree)
            }
            single?.let {
                Chip(stringResource(R.string.synthesis_single_count, it), AlmaPalette.GoldBright)
            }
        }
    }

    val axes = data.array("axes").orEmpty().filterIsInstance<JsonObject>()
    if (axes.isEmpty()) return

    Spacer(Modifier.height(20.dp))
    axes.forEachIndexed { index, axis ->
        val name = axis.text("name") ?: return@forEachIndexed
        val verdict = axis.text("verdict")
        val count = axis.int("count") ?: 0
        // An axis whose verdict this build does not recognise is dropped rather
        // than coloured and labelled by a guess.
        val tone = when (verdict) {
            "agree" -> AlmaPalette.Agree
            "disagree" -> AlmaPalette.Disagree
            "single" -> AlmaPalette.GoldBright
            else -> return@forEachIndexed
        }
        val label = when (verdict) {
            "agree" -> stringResource(R.string.synthesis_agree, count)
            "disagree" -> stringResource(R.string.synthesis_disagree, count)
            else -> stringResource(R.string.synthesis_single)
        }

        CabinetRow(rule = index < axes.lastIndex) {
            Column(Modifier.weight(1f)) {
                Text(text = axisName(name), style = AlmaTheme.type.headingM)
                // The signals, not a paragraph. The calculation produces no
                // prose about an axis — the chapters do — and the citations are
                // the thing that is actually in this response.
                val signals = axis.array("signals").orEmpty()
                    .filterIsInstance<JsonObject>()
                    .mapNotNull { signal ->
                        val system = signal.text("system") ?: return@mapNotNull null
                        val factor = signal.text("factor") ?: return@mapNotNull null
                        "${systemName(system)}: $factor"
                    }
                if (signals.isNotEmpty()) {
                    Text(
                        text = signals.joinToString(" · "),
                        style = AlmaTheme.type.meta,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }
            }
            Text(text = label, style = AlmaTheme.type.meta, color = tone)
        }
    }
}

@Composable
private fun Chip(text: String, tone: Color) {
    Box(
        modifier = Modifier
            .background(tone.copy(alpha = 0.10f), PillShape)
            .padding(horizontal = 13.dp, vertical = 7.dp),
    ) {
        Text(text = text, style = AlmaTheme.type.meta, color = tone)
    }
}

/** Label-and-value rows, where a value that is not there takes its row with it. */
@Composable
private fun ColumnScope.ValueRows(rows: List<Pair<String, String?>>) {
    val present = rows.mapNotNull { (label, value) ->
        value?.takeIf { it.isNotBlank() && label.isNotBlank() }?.let { label to it }
    }
    present.forEachIndexed { index, (label, value) ->
        CabinetRow(rule = index < present.lastIndex) {
            Text(text = label, style = AlmaTheme.type.meta, modifier = Modifier.weight(1f))
            Text(text = value, style = AlmaTheme.type.positions)
        }
    }
}

// `pill()` lived here — "☉ 23°14′ ♓︎ H8" — and went with the three pills it
// built. `PlacementList` says the same thing in the reader's own words and is
// the only place that should.

/** The angles are not bodies and have no placement to read a glyph from. */
private fun glyphOf(placements: JsonObject?, name: String?): String? {
    if (name == null) return null
    return placements?.obj(name)?.text("glyph") ?: BodyGlyphs[name] ?: name
}
