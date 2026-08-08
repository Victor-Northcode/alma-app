package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.core.SessionHolder
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.data.dto.CalcRequest
import ai.pazl.alma.data.dto.ChatMessageDto
import ai.pazl.alma.data.dto.ChatRequest
import ai.pazl.alma.ui.components.AlmaPresence
import ai.pazl.alma.ui.components.Hairline
import ai.pazl.alma.ui.components.Overline
import ai.pazl.alma.ui.components.QuietButton
import ai.pazl.alma.ui.components.riseIn
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import ai.pazl.alma.ui.theme.PillShape
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Alma, answering.
 *
 * ## Why this screen is not a `ScreenState`
 *
 * Every other screen in the cabinet fetches something and shows it, so
 * `ScreenState<T>` is the right shape for all of them. This one has nothing to
 * fetch: an empty conversation is not a loading state, it is the ordinary and
 * correct first view, and there is no thread index to list — `/v1/chat` returns
 * one thread at a time. So the state here is a list that starts empty plus one
 * flag for the answer in flight, and both are inside one immutable
 * [Conversation] rather than beside each other as booleans.
 *
 * ## What is drawn, and the one thing that must not be
 *
 * Alma's answers carry `cited_factors` and `turn_kind`. The citations are the
 * product's whole claim and are always available; `turn_kind` decides whether
 * this turn made a claim at all. See [ChatTurnKind] for why the old
 * `answered_from_chart` boolean could not do that job, and for the greeting it
 * mislabelled.
 *
 * ## The empty state
 *
 * Nothing is invented into it. The web app used to list three fixture questions
 * in its rail, with the first marked active, so it read as this person's own
 * history; they were removed there and are not rebuilt here. What sits in the
 * empty view instead is up to three questions **about this person's own chart**
 * — their sun, moon and rising, read from the free natal preview — clearly
 * offered rather than recorded, and each is a *button*, because the fastest way
 * to learn what this screen does is to ask something. A sign the payload does
 * not carry drops its question rather than being guessed at, which is the same
 * rule the whole cabinet follows.
 */
@Composable
fun AlmaScreen(
    container: AppContainer,
    onOffer: () -> Unit,
) {
    val vm: AlmaChatViewModel = viewModel {
        AlmaChatViewModel(container.client, container.session)
    }
    val chat by vm.state.collectAsStateWithLifecycle()

    NightSky(config = SkyConfig(seed = 3, motes = 1, comet = false)) {
        ChatBody(chat, onAsk = vm::ask, onOffer = onOffer)
    }
}

@Composable
private fun BoxScope.ChatBody(
    chat: Conversation,
    onAsk: (String) -> Unit,
    onOffer: () -> Unit,
) {
    var typed by remember { mutableStateOf("") }
    val listState = rememberLazyListState()

    // The newest turn, whenever one arrives. Keyed on the count rather than on
    // the list so that a re-render with the same turns does not yank the view
    // away from somebody who has scrolled up to re-read an answer.
    LaunchedEffect(chat.turns.size, chat.thinking) {
        val last = chat.turns.lastIndex
        if (last >= 0) listState.animateScrollToItem(last)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .widthIn(max = 720.dp)
            .align(Alignment.TopCenter)
            // The content clears the status bar; the sky behind it runs to the
            // top of the display. `imePadding` on the whole column rather than
            // on the composer alone, so the last answer stays visible when the
            // keyboard comes up instead of sliding under it.
            .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Top))
            .imePadding(),
    ) {
        if (chat.turns.isEmpty()) {
            Empty(openers = chat.openers, onAsk = onAsk, modifier = Modifier.weight(1f))
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).fillMaxWidth(),
                contentPadding = PaddingValues(horizontal = 22.dp, vertical = 20.dp),
                verticalArrangement = Arrangement.spacedBy(22.dp),
            ) {
                // Each message settles in as it arrives — one at a time in a
                // live conversation. In a lazy list a turn scrolled far away
                // re-enters with the same quiet fade, which suits a chat.
                items(chat.turns, key = { it.id }) { turn ->
                    Box(Modifier.riseIn(0)) { Turn(turn) }
                }
            }
        }

        Composer(
            typed = typed,
            onTyped = { typed = it },
            onSend = {
                val question = typed.trim()
                if (question.isNotEmpty()) {
                    typed = ""
                    onAsk(question)
                }
            },
            chat = chat,
            onOffer = onOffer,
        )
    }
}

/* ── the empty view ────────────────────────────────────────────────────── */

@Composable
private fun Empty(openers: ChartOpeners?, onAsk: (String) -> Unit, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier.fillMaxWidth().padding(horizontal = 22.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(Modifier.riseIn(0)) { AlmaPresence(size = 96.dp) }
        Text(
            text = stringResource(R.string.chat_lead),
            style = AlmaTheme.type.almaVoice,
            modifier = Modifier.widthIn(max = 420.dp).riseIn(1),
        )

        // Offered, not remembered. A question printed here as if it had been
        // asked would be the same fabrication as a pre-filled birthday — which
        // is why every one of these is a button and none of them is sent until
        // it is tapped.
        val questions = openerQuestions(openers)
        if (questions.isNotEmpty()) {
            Overline(stringResource(R.string.chat_could_ask), modifier = Modifier.riseIn(2))
            questions.forEachIndexed { index, question ->
                QuietButton(
                    text = question,
                    onClick = { onAsk(question) },
                    modifier = Modifier.riseIn(3 + index),
                )
            }
        }
    }
}

/**
 * Up to three questions, each naming a sign this person actually has.
 *
 * Free, and that is the argument for asking the server at all: every
 * calculation in this product is free forever, and the *preview* a locked natal
 * chart returns still names the three signs — so a reader who has bought
 * nothing gets the same three questions as a subscriber.
 *
 * A sign the payload does not carry drops its line. Somebody with no birth time
 * has no rising sign and gets two; somebody whose chart has not arrived yet, or
 * never does, gets the one written question, which is the state this screen
 * shipped with. Nothing here is ever substituted with a plausible sign.
 */
@Composable
private fun openerQuestions(openers: ChartOpeners?): List<String> {
    val written = stringResource(R.string.chat_example)
    if (openers == null) return listOf(written)
    return buildList {
        openers.moon?.let { add(stringResource(R.string.chat_prompt_moon, signWord(it))) }
        openers.sun?.let { add(stringResource(R.string.chat_prompt_sun, signWord(it))) }
        openers.rising?.let { add(stringResource(R.string.chat_prompt_rising, signWord(it))) }
        if (isEmpty()) add(written)
    }
}

/* ── one exchange ──────────────────────────────────────────────────────── */

@Composable
private fun Turn(turn: ChatTurn) {
    Column(Modifier.fillMaxWidth()) {
        // The question, in the reader's own voice: right-aligned, on a gold
        // veil, no bubble outline. The one place in the product where anything
        // sits inside a shape, and it is a lozenge rather than a card.
        Box(
            modifier = Modifier
                .align(Alignment.End)
                .widthIn(max = 520.dp)
                .background(AlmaPalette.Gold.copy(alpha = 0.10f), PillShape)
                .padding(horizontal = 16.dp, vertical = 11.dp),
        ) {
            Text(text = turn.question, style = AlmaTheme.type.meta.copy(fontSize = 15.sp))
        }

        Spacer(Modifier.height(16.dp))

        when {
            turn.answer != null -> Answer(turn.answer)
            turn.failure != null -> Text(
                text = failureLine(turn.failure),
                style = AlmaTheme.type.meta,
                color = AlmaPalette.Disagree,
            )
            else -> Thinking()
        }
    }
}

@Composable
private fun Answer(message: ChatMessageDto) {
    val kind = ChatTurnKind.of(message)

    Text(text = message.body, style = AlmaTheme.type.almaVoice)

    if (kind.showsCitations && message.citedFactors.isNotEmpty()) {
        Spacer(Modifier.height(14.dp))
        Citations(message.citedFactors)
    }

    if (kind.showsChartSilentNote) {
        Spacer(Modifier.height(10.dp))
        // One sentence, in her own register — not a tag. The uppercase
        // "Not from your chart" this replaces read as a compliance warning
        // stapled to somebody's conversation, in a product whose entire voice
        // is a person talking, and it appeared under refusals, where it was
        // also untrue.
        Text(
            text = stringResource(R.string.chat_silent),
            style = AlmaTheme.type.meta,
            color = AlmaPalette.Muted3,
        )
    }
}

/**
 * Where an answer was read from — one quiet line that opens into the pills.
 *
 * **Why it is not an open row of pills any more.** The factors are the engine's
 * own identifiers and they read like it: `t-square: moon, jupiter, pluto (apex
 * pluto in Sagittarius)`, `soul urge 7`. Left open under every answer they took
 * four or five lines, and they are the first thing a person scrolling back
 * meets — five lines of jargon before a sentence of Alma's. The citation is the
 * product's whole claim and is not being hidden: it is stated on one line, with
 * the first factor visible and the rest counted, and it opens on a tap.
 *
 * Collapsed per message and per appearance rather than remembered. A setting
 * called "always show my citations" would be a preference nobody asked for
 * about something they can already tap.
 */
@Composable
private fun Citations(factors: List<String>) {
    var open by remember { mutableStateOf(false) }
    val more = factors.size - 1

    Column(Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { open = !open }
                .padding(vertical = 2.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Overline(stringResource(R.string.chat_read_from))
            Text(
                text = if (more > 0) "${factors.first()}  +$more" else factors.first(),
                style = AlmaTheme.type.positions.copy(fontSize = 13.sp),
                color = AlmaPalette.GoldBright,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            Text(
                text = if (open) "−" else "+",
                style = AlmaTheme.type.positions,
                color = AlmaPalette.Gold,
            )
        }

        if (open) {
            FlowRow(
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(7.dp),
                verticalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                factors.forEach { factor ->
                    Box(
                        modifier = Modifier
                            .background(AlmaPalette.Gold.copy(alpha = 0.10f), PillShape)
                            .padding(horizontal = 11.dp, vertical = 5.dp),
                    ) {
                        Text(text = factor, style = AlmaTheme.type.positions.copy(fontSize = 13.sp))
                    }
                }
            }
        }
    }
}

/**
 * The wait, drawn.
 *
 * A turn measures twenty to thirty seconds against the live model, and a screen
 * that says one unchanging thing for half a minute stops reading as progress
 * and starts reading as a hang. So the star breathes, and after ten seconds the
 * sentence changes — the second line is what somebody sees for most of a normal
 * wait, which is intentional, because it is the reassuring one.
 *
 * The motion is [AlmaPresence]'s own rather than a second animation layered on
 * top of it: it already breathes, and it already stops breathing when the
 * system asks for reduced motion. A hand-rolled pulse here would be one more
 * thing that keeps moving for somebody who asked everything to hold still.
 */
@Composable
private fun Thinking() {
    var longWait by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        delay(10_000)
        longWait = true
    }

    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        AlmaPresence(size = 22.dp, ring = false)
        Text(
            text = stringResource(if (longWait) R.string.chat_thinking_still else R.string.chat_thinking),
            style = AlmaTheme.type.meta,
            color = AlmaPalette.Muted,
        )
    }
}

/* ── the composer ──────────────────────────────────────────────────────── */

@Composable
private fun Composer(
    typed: String,
    onTyped: (String) -> Unit,
    onSend: () -> Unit,
    chat: Conversation,
    onOffer: () -> Unit,
) {
    val exhausted = chat.questionsLeft == 0
    val placeholder = stringResource(R.string.chat_placeholder)

    Column(Modifier.fillMaxWidth().padding(horizontal = 22.dp, vertical = 14.dp)) {
        Hairline()
        Spacer(Modifier.height(12.dp))

        if (exhausted) {
            // No input at all rather than a field that refuses. A composer that
            // takes typing and then apologises is worse than one that is
            // honestly not there.
            Text(text = stringResource(R.string.chat_no_questions), style = AlmaTheme.type.meta)
            Spacer(Modifier.height(12.dp))
            QuietButton(
                text = stringResource(R.string.chat_get_more),
                onClick = onOffer,
                contentColor = AlmaPalette.GoldBright,
            )
            return@Column
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            BasicTextField(
                value = typed,
                onValueChange = onTyped,
                textStyle = AlmaTheme.type.meta.copy(color = AlmaPalette.Body, fontSize = 16.sp),
                cursorBrush = SolidColor(AlmaPalette.Gold),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { onSend() }),
                enabled = !chat.thinking,
                modifier = Modifier.weight(1f),
                decorationBox = { field ->
                    if (typed.isEmpty()) {
                        Text(
                            text = placeholder,
                            style = AlmaTheme.type.meta.copy(fontSize = 16.sp),
                            color = AlmaPalette.Muted3,
                        )
                    }
                    field()
                },
            )
            QuietButton(
                text = stringResource(R.string.chat_send),
                onClick = onSend,
                enabled = typed.isNotBlank() && !chat.thinking,
            )
        }

        // A count only when there is one. Null means unlimited, and printing
        // "null questions left" or inventing a number for a subscriber would
        // both be worse than saying nothing.
        chat.questionsLeft?.let { left ->
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.chat_questions_left, left),
                style = AlmaTheme.type.meta,
                color = AlmaPalette.Muted3,
            )
        }
    }
}

/**
 * What there is to say when there is no answer, said the way Alma would say it.
 *
 * **A status code is not a voice.** Three of these used to borrow the app-wide
 * error strings, which talk about calculations and sample data — sentences
 * written for a screen full of numbers, not for somebody mid-conversation. Each
 * one now says what happened in the first person and says that the question was
 * not lost, because it is not: the composer keeps what was typed.
 *
 * [ApiFailure.NothingToSay] is the one that mattered. It carries
 * `answer_refused`, whose message from the backend is `str(exc)` — untranslated
 * engineering prose out of `conversation.py` — and until this branch existed it
 * fell to the generic line. It is not a fault: an honest silence is exactly
 * what the validator is for.
 */
@Composable
private fun failureLine(failure: ApiFailure): String = when (failure) {
    // The backend's own sentence here, and only here: it is localised there and
    // it already says *when* the questions come back — an allowance this screen
    // would otherwise have to re-derive from the tier, and get wrong the day
    // the tiers change.
    is ApiFailure.QuestionLimit -> failure.message.ifBlank { stringResource(R.string.error_question_limit) }
    is ApiFailure.NeedsBirthTime -> stringResource(R.string.error_needs_birth_time)
    is ApiFailure.NothingToSay -> stringResource(R.string.chat_refused)
    is ApiFailure.Offline -> stringResource(R.string.chat_offline)
    is ApiFailure.Unavailable -> stringResource(R.string.chat_unavailable)
    else -> stringResource(R.string.chat_went_wrong)
}

/* ── state ─────────────────────────────────────────────────────────────── */

/**
 * One question and whatever came back for it.
 *
 * The question is kept beside the answer rather than as a separate row, because
 * they are one exchange: a failed answer still has to be shown *under the thing
 * that was asked*, and a flat list of messages makes that a lookup.
 */
@Immutable
data class ChatTurn(
    val id: Long,
    val question: String,
    val answer: ChatMessageDto? = null,
    val failure: ApiFailure? = null,
)

/**
 * The three signs the empty state asks about, or as many of them as this chart
 * actually has.
 *
 * Nullable per field rather than a nullable triple: a birth with no time has no
 * rising sign, and the honest shape of that is one missing field, not a missing
 * object. The values are the engine's English keys — `"Virgo"` — and are
 * translated at the point they are drawn, never here.
 */
@Immutable
data class ChartOpeners(
    val sun: String? = null,
    val moon: String? = null,
    val rising: String? = null,
)

@Immutable
data class Conversation(
    val turns: List<ChatTurn> = emptyList(),
    /** The server's thread, once it has told us which one this is. */
    val threadId: String? = null,
    /** Null means unlimited. Zero is a real answer and is not the same as null. */
    val questionsLeft: Int? = null,
    val thinking: Boolean = false,
    /** Null until the free natal preview arrives, and if it never does. */
    val openers: ChartOpeners? = null,
)

/**
 * Asking, and the two rules that keep it honest.
 *
 * **One question at a time.** [ask] refuses while an answer is in flight rather
 * than queueing, because every question costs money and a double tap on a slow
 * network would spend twice for one intent.
 *
 * **The thread id comes back from the server and is sent with the next
 * question.** Without it every question starts a new conversation and Alma
 * forgets what was said a minute ago, which is the thing a person is paying not
 * to get.
 */
class AlmaChatViewModel(
    private val client: AlmaClient,
    private val session: SessionHolder,
) : ViewModel() {

    private val _state = MutableStateFlow(Conversation())
    val state: StateFlow<Conversation> = _state.asStateFlow()

    private var nextId = 0L

    init {
        loadOpeners()
    }

    /**
     * The three signs the opening questions are about.
     *
     * **Free, which is the whole argument for doing it.** `/v1/systems/natal`
     * costs nothing — every calculation in this product is free forever — and
     * the preview a locked chart returns still names the three signs, so a
     * reader who has bought nothing gets the same opening as a subscriber.
     *
     * Skipped when there is no birth data and when there is no account: there
     * would be no chart to read, and the request would mint an account for
     * somebody who has given us nothing, which is the leak `SessionHolder` was
     * fixed to stop. Failure is silent by design — the written question is
     * already on screen, and an error over a set of *examples* would be a
     * complaint about something nobody asked for.
     */
    private fun loadOpeners() {
        viewModelScope.launch {
            val ready = session.state.first { it.ready }
            if (ready.account == null || ready.profile == null) return@launch

            val natal = client.system(
                AlmaSystem.NATAL,
                CalcRequest(profileId = ready.profile.id, locale = ready.locale),
            )
            if (natal !is ApiResult.Ok) return@launch

            val chart = natal.data.data
            val openers = ChartOpeners(
                sun = chart.text("sun_sign"),
                moon = chart.text("moon_sign"),
                rising = chart.text("rising_sign"),
            )
            // Every field null is the same as no answer, and drawing a heading
            // over nothing is worse than drawing the written question.
            if (openers.sun == null && openers.moon == null && openers.rising == null) return@launch
            _state.update { it.copy(openers = openers) }
        }
    }

    fun ask(question: String) {
        if (_state.value.thinking) return
        val id = nextId++

        _state.update {
            it.copy(turns = it.turns + ChatTurn(id = id, question = question), thinking = true)
        }

        viewModelScope.launch {
            // The locale Alma writes in belongs to the account rather than to
            // the phone: somebody reading the interface in English who chose to
            // be written to in Italian gets Italian.
            val locale = session.state.first { it.ready }.locale

            val answer = client.ask(
                ChatRequest(
                    message = question,
                    threadId = _state.value.threadId,
                    locale = locale,
                )
            )

            _state.update { current ->
                val turns = current.turns.map { turn ->
                    if (turn.id != id) {
                        turn
                    } else {
                        when (answer) {
                            is ApiResult.Ok -> turn.copy(answer = answer.data.message)
                            is ApiResult.Err -> turn.copy(failure = answer.failure)
                        }
                    }
                }
                current.copy(
                    turns = turns,
                    thinking = false,
                    threadId = (answer as? ApiResult.Ok)?.data?.threadId ?: current.threadId,
                    questionsLeft = when (answer) {
                        is ApiResult.Ok -> answer.data.questionsLeft
                        // The allowance arrives on the refusal too, and it is
                        // the number the composer needs in order to stop
                        // offering a field that cannot work.
                        is ApiResult.Err ->
                            (answer.failure as? ApiFailure.QuestionLimit)?.let { 0 }
                                ?: current.questionsLeft
                    },
                )
            }
        }
    }
}
