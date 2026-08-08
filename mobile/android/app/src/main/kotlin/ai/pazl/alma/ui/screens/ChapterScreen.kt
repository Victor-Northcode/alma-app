package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.core.ScreenState
import ai.pazl.alma.core.SessionHolder
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.data.dto.ChapterEntryDto
import ai.pazl.alma.data.dto.ReadingDto
import ai.pazl.alma.data.dto.ReadingRequest
import ai.pazl.alma.ui.components.GoldButton
import ai.pazl.alma.ui.components.StateHost
import ai.pazl.alma.ui.components.WritingArt
import ai.pazl.alma.ui.components.Waiting
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import ai.pazl.alma.ui.theme.PillShape
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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

/**
 * One chapter, on the only light surface in the product.
 *
 * Parchment is earned, and it is earned *literally*: the sheet appears when the
 * chapter does. While Alma is writing, and if the request fails, this screen is
 * night like everywhere else — there is nothing to read yet, so there is no
 * document. The sky still runs behind the sheet and the grain still runs over
 * it, which keeps it feeling like paper laid on the night rather than a white
 * app that opened by accident.
 *
 * Two requests, deliberately unequal. The chapter list supplies the frame — the
 * numeral, the progress, what this chapter is called — and the reading supplies
 * the prose. The reading has no fallback of any kind: where Alma has not written
 * a chapter, the sheet shows a state, never something that reads like a reading.
 *
 * **Nothing here claims text already exists.** `readings.py` writes a chapter
 * the first time it is opened, so at the moment somebody is deciding whether to
 * pay, nothing is written at all. A locked chapter therefore shows its title,
 * the question it answers and the door — no blurred paragraph, because a blurred
 * paragraph would have to be somebody else's.
 */
@Composable
fun ChapterScreen(
    container: AppContainer,
    system: String,
    chapter: String,
    onOffer: () -> Unit,
    /**
     * The plans-first ladder, for the offer at the end of a chapter in a
     * *bought* system — the door would sell what is already owned.
     */
    onPlans: () -> Unit,
    onOpenChapter: (String) -> Unit,
    onBack: () -> Unit,
) {
    val vm: ChapterViewModel = viewModel(key = "$system/$chapter") {
        ChapterViewModel(container.client, container.session, system, chapter)
    }
    val state by vm.state.collectAsStateWithLifecycle()

    NightSky(config = SkyConfig.Reader.copy(seed = 40)) {
        // `StateHost`'s waiting line is "Reading your sky…", which is the right
        // sentence nearly everywhere and the wrong one here: this is the screen
        // where a language model may genuinely be writing, and the words for
        // that are already translated. So loading is drawn here and the other
        // two states go through the shared host.
        if (state is ScreenState.Loading) {
            // The system's own drawing, alive, for as long as the model
            // writes — the same eight canvases as iOS.
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    WritingArt(system)
                    Spacer(Modifier.height(18.dp))
                    Text(
                        text = stringResource(R.string.state_writing),
                        style = AlmaTheme.type.meta,
                    )
                    // «Пишется один раз…» stood here and the owner cut it.
                }
            }
        } else {
            StateHost(state, onRetry = vm::reload) { chapterView ->
                Box(Modifier.fillMaxSize().background(AlmaPalette.ParchmentGradient)) {
                    ChapterBody(
                        chapterView,
                        onOffer = onOffer,
                        onPlans = onPlans,
                        onOpenChapter = onOpenChapter,
                        onBack = onBack,
                    )
                }
            }
        }
    }
}

/* ── what the screen holds ─────────────────────────────────────────────── */

@Immutable
data class ChapterView(
    val system: String,
    val slug: String,
    /** This chapter's entry in the list, when the list arrived. */
    val entry: ChapterEntryDto?,
    /**
     * The chapter after this one, when there is one.
     *
     * The reader used to end at "Back to chapters" and nothing else, because
     * the graph handed this screen no way to open a sibling — so finishing a
     * chapter meant going back to a list and finding your place in it. The web
     * app has a next link and it was the single biggest thing missing here.
     *
     * Null on the last chapter, and null is drawn rather than hidden: the list
     * button stays, and only the next link goes.
     */
    val next: ChapterEntryDto?,
    val total: Int,
    val reading: ReadingDto?,
    /**
     * True when this chapter is not paid for.
     *
     * A 402 about this exact chapter is the authority. Until it arrives the
     * chapter list's own flag decides, so the paywall does not flash in front of
     * a chapter that turns out to be open — and a chapter neither source knows
     * about is assumed **open** rather than sold.
     */
    val locked: Boolean,
    /** Why there is no prose, when it is a reason worth saying. */
    val failure: ApiFailure?,
    /**
     * The price of this system's door, formatted by the server. Fetched only
     * when there is something to sell; blank otherwise, and then the button says
     * what it opens without quoting a figure.
     */
    val price: String,
    /**
     * The two facts the chapter-end offer branches on. A finished chapter in a
     * system this account has not bought ends on the door; one in a bought
     * system ends on the plan — a bought chapter is written once, the living
     * layer moves. A subscriber sees neither.
     */
    val systemUnlocked: Boolean = false,
    val isSubscriber: Boolean = false,
    /** The chapter is real and unpaid: first paragraph in the clear, the rest
     * under blur with the unlock button on top. */
    val preview: Boolean = false,
)

class ChapterViewModel(
    private val client: AlmaClient,
    private val session: SessionHolder,
    private val system: String,
    private val chapter: String,
) : ViewModel() {

    private val _state = MutableStateFlow<ScreenState<ChapterView>>(ScreenState.Loading)
    val state: StateFlow<ScreenState<ChapterView>> = _state.asStateFlow()

    private var running: Job? = null

    init {
        reload()
    }

    /**
     * Ask for the chapter, once.
     *
     * The previous job is cancelled first, and that is not tidiness: the first
     * request for a chapter nobody has opened puts a language model to work and
     * spends real money, so two in flight is two charged. `AlmaClient`
     * deliberately has no retry for the same reason.
     */
    fun reload() {
        running?.cancel()
        running = viewModelScope.launch {
            _state.value = ScreenState.Loading
            val account = session.state.first { it.ready }

            val (chapters, reading) = coroutineScope {
                val chaptersCall = async { client.chapters(system, account.locale) }
                val readingCall = async {
                    client.reading(
                        ReadingRequest(system = system, chapter = chapter, locale = account.locale)
                    )
                }
                chaptersCall.await() to readingCall.await()
            }

            val list = (chapters as? ApiResult.Ok)?.data
            val entry = list?.chapters?.firstOrNull { it.slug == chapter }
            // Position in the list, not "the one with the next number": the
            // server decides the order and several systems do not number their
            // chapters consecutively.
            val next = list?.chapters
                ?.indexOfFirst { it.slug == chapter }
                ?.takeIf { it >= 0 }
                ?.let { list.chapters.getOrNull(it + 1) }
            val failure = (reading as? ApiResult.Err)?.failure
            val written = (reading as? ApiResult.Ok)?.data?.reading

            // Nothing to show and no paywall to show instead: the screen failed
            // rather than pretending to be an empty chapter. `Locked` is not
            // that case — it is the whole point of the sheet below.
            if (list == null && written == null && failure !is ApiFailure.Locked) {
                _state.value = ScreenState.Failed(
                    failure ?: (chapters as ApiResult.Err).failure
                )
                return@launch
            }

            val locked = when {
                failure is ApiFailure.Locked -> true
                written != null -> false
                else -> entry?.`open` == false
            }

            val held = account.entitlements?.entitlements.orEmpty()
            _state.value = ScreenState.Loaded(
                ChapterView(
                    system = system,
                    slug = chapter,
                    entry = entry,
                    next = next,
                    total = list?.total ?: list?.chapters?.size ?: 0,
                    reading = written,
                    locked = locked,
                    failure = failure,
                    systemUnlocked = system in account.unlocked,
                    isSubscriber = held.any {
                        it.active && (it.kind == "weekly" || it.kind == "monthly" || it.kind == "annual")
                    },
                    preview = (reading as? ApiResult.Ok)?.data?.preview == true,
                    // Asked for only when there is a door to price. A chapter
                    // somebody already owns has nothing to sell them.
                    price = if (locked) {
                        (client.catalogue() as? ApiResult.Ok)?.data?.items
                            ?.firstOrNull { it.slug == system }?.display.orEmpty()
                    } else {
                        ""
                    },
                )
            )
        }
    }
}

/* ── the sheet ─────────────────────────────────────────────────────────── */

/**
 * Ink on parchment.
 *
 * The palette inverts wholesale here rather than element by element: gold on
 * parchment is unreadable at body size, so the citation colour becomes the dark
 * end of the same single gold — one gold, aged, seen against light instead of
 * against night. It is the stroke colour the mark itself is drawn with.
 */
private val InkGold = Color(0xFF7A6129)

@Composable
private fun ChapterBody(
    chapter: ChapterView,
    onOffer: () -> Unit,
    onPlans: () -> Unit,
    onOpenChapter: (String) -> Unit,
    onBack: () -> Unit,
) {
    val name = systemName(chapter.system)

    // The one screen where text must not pass under the status bar; see the
    // parameter's own comment for what it looked like when it did.
    CabinetPage(contentUnderStatusBar = false) {
        ReaderBar(chapter, onBack)

        Spacer(Modifier.height(20.dp))
        Text(
            text = listOfNotNull(chapter.entry?.numeral, name.lowercase()).joinToString(" · "),
            style = AlmaTheme.type.overline.copy(color = InkGold),
        )
        Text(
            text = chapter.reading?.title ?: chapter.entry?.title.orEmpty(),
            style = AlmaTheme.type.displayXl.copy(color = AlmaPalette.Ink),
            modifier = Modifier.padding(top = 10.dp),
        )

        // The placements this text was read from. No reading, no citations —
        // assembling them from the chapter list would be inventing the citation,
        // which is the one thing this product cannot do.
        val factors = chapter.reading?.citedFactors.orEmpty()
        if (factors.isNotEmpty()) {
            FlowRow(
                modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                factors.forEach { factor ->
                    Box(
                        modifier = Modifier
                            .border(1.dp, InkGold.copy(alpha = 0.35f), PillShape)
                            .padding(horizontal = 12.dp, vertical = 6.dp),
                    ) {
                        Text(text = factor, style = AlmaTheme.type.positions.copy(color = InkGold))
                    }
                }
            }
        }

        InkRule(Modifier.padding(vertical = 22.dp))

        // The first line is always readable, locked or not. It comes from the
        // reading when there is one and otherwise from the chapter's own
        // question, which is catalogue metadata rather than anything Alma wrote.
        val lead = chapter.reading?.teaser?.takeIf { it.isNotBlank() } ?: chapter.entry?.question
        if (lead != null) {
            Text(text = lead, style = AlmaTheme.type.almaVoice.copy(color = AlmaPalette.Ink))
        }

        ChapterTrouble(chapter)

        val bodyStyle = AlmaTheme.type.almaVoice.copy(
            color = AlmaPalette.InkMuted,
            // Alma's italic serif is her *voice*; the body of a chapter
            // is the document, and setting six paragraphs in italic
            // would make a reading tiring to read.
            fontStyle = FontStyle.Normal,
            fontSize = 17.sp,
            lineHeight = 28.sp,
        )

        if (chapter.preview) {
            // The blurred preview: the real first paragraph in the clear, the
            // real rest under blur, the unlock button on top. Nothing here is
            // a placeholder — the prose exists; the blur is the only thing
            // the purchase removes.
            chapter.reading?.body?.firstOrNull()?.let { first ->
                Text(text = first, style = bodyStyle, modifier = Modifier.padding(top = 18.dp))
            }
            Box {
                Column(Modifier.blur(7.dp)) {
                    chapter.reading?.body?.drop(1)?.forEach { paragraph ->
                        Text(
                            text = paragraph, style = bodyStyle,
                            modifier = Modifier.padding(top = 18.dp),
                        )
                    }
                }
                Column(
                    modifier = Modifier.align(Alignment.Center).padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    Text(
                        text = stringResource(R.string.chapter_preview_note),
                        style = AlmaTheme.type.meta.copy(color = AlmaPalette.Ink),
                        textAlign = TextAlign.Center,
                    )
                    GoldButton(
                        text = stringResource(R.string.chapter_unlock),
                        onClick = onOffer,
                    )
                }
            }
        } else {
            chapter.reading?.body?.forEach { paragraph ->
                Text(
                    text = paragraph, style = bodyStyle,
                    modifier = Modifier.padding(top = 18.dp),
                )
            }

            chapter.reading?.advice?.takeIf { it.isNotBlank() }?.let { advice ->
                Row(modifier = Modifier.padding(top = 24.dp).height(IntrinsicSize.Min)) {
                    Box(Modifier.width(2.dp).fillMaxHeight().background(InkGold))
                    Text(
                        text = advice,
                        style = AlmaTheme.type.almaVoice.copy(color = AlmaPalette.Ink),
                        modifier = Modifier.padding(start = 16.dp),
                    )
                }
            }
        }

        InkRule(Modifier.padding(vertical = 22.dp))

        // What the text was read from, in the server's own words — or, for a
        // chapter nobody has opened yet, what is true about writing one.
        val source = chapter.reading?.readFrom?.takeIf { it.isNotBlank() }
            ?: if (chapter.locked) stringResource(R.string.state_locked_note) else null
        if (source != null) {
            Text(text = source, style = AlmaTheme.type.meta.copy(color = AlmaPalette.InkMuted2))
        }

        if (chapter.locked) {
            ChapterPaywall(chapter, name, onOffer)
        } else {
            // One quiet block at the end of a finished chapter — the moment
            // the writing has just proven itself, which is the definition of
            // the right moment. Static content below the reading, never a
            // modal, never mid-scroll. A subscriber sees neither variant.
            if (chapter.reading != null && !chapter.isSubscriber) {
                Spacer(Modifier.height(26.dp))
                if (chapter.systemUnlocked) {
                    Text(
                        text = stringResource(R.string.chapter_end_plan),
                        style = AlmaTheme.type.meta.copy(color = AlmaPalette.InkMuted2),
                    )
                    Spacer(Modifier.height(12.dp))
                    InkButton(
                        text = stringResource(R.string.plans_cta),
                        onClick = onPlans,
                    )
                } else {
                    Text(
                        text = stringResource(R.string.chapter_end_door),
                        style = AlmaTheme.type.meta.copy(color = AlmaPalette.InkMuted2),
                    )
                    Spacer(Modifier.height(12.dp))
                    InkButton(
                        text = stringResource(R.string.cabinet_open_system_no_price, name),
                        onClick = onOffer,
                    )
                }
            }

            // The chapter after this one, then the list. Both, in that order,
            // because reading straight on is what somebody who has just
            // finished a chapter wants and going back to choose is what they
            // want second.
            Spacer(Modifier.height(26.dp))
            chapter.next?.let { following ->
                InkButton(
                    text = stringResource(R.string.chapter_next, following.title),
                    onClick = { onOpenChapter(following.slug) },
                )
                Spacer(Modifier.height(12.dp))
            }
            InkButton(
                text = stringResource(R.string.cabinet_back_to_chapters),
                onClick = onBack,
            )
        }

        Spacer(Modifier.height(36.dp))
    }
}

/** The bar over the sheet: back, and where in the system this chapter sits. */
@Composable
private fun ReaderBar(chapter: ChapterView, onBack: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        val label = stringResource(R.string.cabinet_back_to_chapters)
        Box(
            modifier = Modifier
                .size(44.dp)
                .clickable(role = Role.Button, onClickLabel = label, onClick = onBack),
            contentAlignment = Alignment.Center,
        ) {
            Text(text = "←", style = AlmaTheme.type.displayL.copy(color = AlmaPalette.Ink))
        }
        val entry = chapter.entry
        if (entry != null && chapter.total > 0) {
            Text(
                text = "${entry.index} / ${chapter.total}",
                style = AlmaTheme.type.meta.copy(color = AlmaPalette.InkMuted2),
            )
        }
    }
}

/**
 * What the sheet says when there is no prose on it and the reason is worth
 * saying.
 *
 * A locked chapter is not one of those: the door at the foot of the sheet
 * already says it, and saying it twice would be saying it worse.
 */
@Composable
private fun ChapterTrouble(chapter: ChapterView) {
    if (chapter.reading != null) return
    when (val failure = chapter.failure) {
        null, is ApiFailure.Locked -> Unit
        is ApiFailure.NeedsBirthTime -> InkNote(stringResource(R.string.error_needs_birth_time))
        // Never `failure.message` here. The writing layer's 503 carries a
        // sentence for whoever deploys the backend — the emulator's said
        // "ANTHROPIC_API_KEY is not set" — and every server message is English
        // in all six locales. The translated line says the half that matters:
        // the calculations are unaffected.
        is ApiFailure.Unavailable -> InkNote(stringResource(R.string.error_ai_unavailable))
        else -> InkNote(stringResource(R.string.error_generic))
    }
}

/**
 * The door, and it is the **system's** door rather than the chapter's.
 *
 * Single chapters are not on sale — that tier was withdrawn — so a per-chapter
 * price here would come from nowhere and the checkout behind it would 404. What
 * opens this chapter is the system it belongs to.
 */
@Composable
private fun ChapterPaywall(chapter: ChapterView, name: String, onOffer: () -> Unit) {
    Spacer(Modifier.height(28.dp))
    Row(
        modifier = Modifier.fillMaxWidth().padding(bottom = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = name,
            style = AlmaTheme.type.headingM.copy(color = AlmaPalette.Ink),
            modifier = Modifier.weight(1f),
        )
        if (chapter.price.isNotBlank()) {
            // Straight from the catalogue, already formatted by the server in
            // this account's currency. Never assembled here.
            Text(text = chapter.price, style = AlmaTheme.type.positions.copy(color = InkGold))
        }
    }
    GoldButton(
        text = if (chapter.price.isBlank()) {
            stringResource(R.string.cabinet_open_system_no_price, name)
        } else {
            stringResource(R.string.cabinet_open_system, name, chapter.price)
        },
        onClick = onOffer,
        modifier = Modifier.fillMaxWidth(),
    )
    Text(
        text = stringResource(R.string.cabinet_archive_note),
        style = AlmaTheme.type.meta.copy(color = AlmaPalette.InkMuted2),
        modifier = Modifier.padding(top = 10.dp),
    )
}

/* ── the few atoms that only exist on parchment ────────────────────────── */

@Composable
private fun InkNote(text: String) {
    Text(
        text = text,
        style = AlmaTheme.type.meta.copy(color = AlmaPalette.InkMuted2),
        modifier = Modifier.padding(top = 14.dp),
    )
}

@Composable
private fun InkRule(modifier: Modifier = Modifier) {
    Box(modifier.fillMaxWidth().height(1.dp).background(InkGold.copy(alpha = 0.22f)))
}

/** The quiet button, inverted for parchment. There is still no third button. */
@Composable
private fun InkButton(text: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .border(1.dp, InkGold.copy(alpha = 0.40f), PillShape)
            .clickable(role = Role.Button, onClick = onClick)
            .padding(horizontal = 24.dp, vertical = 15.dp),
    ) {
        Text(text = text, style = AlmaTheme.type.button.copy(color = InkGold))
    }
}
