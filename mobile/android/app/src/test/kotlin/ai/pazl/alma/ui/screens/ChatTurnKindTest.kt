package ai.pazl.alma.ui.screens

import ai.pazl.alma.data.dto.ChatMessageDto
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The rule that keeps a greeting from being labelled as a chart.
 *
 * Each case below is a real turn from `docs/CONVERSATION.md` — the owner's own
 * two, and the four the study measured where `answered_from_chart` and the
 * citations contradict each other. They are asserted here rather than through
 * the screen because the defect was never a layout problem: it was one boolean
 * being asked a question it could not answer.
 */
class ChatTurnKindTest {

    private val json = Json { ignoreUnknownKeys = true }

    private fun message(
        body: String = "…",
        cited: List<String> = emptyList(),
        fromChart: Boolean = true,
        kind: String? = null,
    ) = ChatMessageDto(
        id = "m",
        role = "alma",
        body = body,
        citedFactors = cited,
        answeredFromChart = fromChart,
        turnKind = kind,
    )

    /* ── the reported bug ──────────────────────────────────────────────── */

    @Test
    fun `a greeting the server names as conversation is never labelled`() {
        val kind = ChatTurnKind.of(
            message(body = "Hello. What would you like to look at?", fromChart = false, kind = "conversation")
        )
        assertEquals(ChatTurnKind.Conversation, kind)
        assertFalse(kind.showsChartSilentNote)
    }

    @Test
    fun `an uncited reply on an old payload is a conversation, not a silent chart`() {
        // This is the owner's screenshot: no `turn_kind`, no citations,
        // `answered_from_chart` false. The old code stamped NOT FROM YOUR CHART
        // on it. The two candidates are a greeting, where the label is a lie,
        // and a silent chart, where she has already said so in her own sentence
        // and the label is a duplicate — so the fallback takes the redundancy.
        val kind = ChatTurnKind.of(message(fromChart = false))
        assertEquals(ChatTurnKind.Conversation, kind)
        assertFalse(kind.showsChartSilentNote)
    }

    /* ── §8: a cited reply is never labelled NOT FROM YOUR CHART ───────── */

    @Test
    fun `citations win over answered_from_chart when they disagree`() {
        // Four turns in the measured run came back `answered_from_chart: false`
        // *with* citations — the ADHD answer cited five placements. Under the
        // old rule iOS drew the pills and the contradiction underneath them.
        val kind = ChatTurnKind.of(
            message(cited = listOf("moon 28°36′ ♒︎ · house 7", "mercury in Virgo"), fromChart = false)
        )
        assertEquals(ChatTurnKind.Reading, kind)
        assertTrue(kind.showsCitations)
        assertFalse(kind.showsChartSilentNote)
    }

    /* ── the honest note, which still has to exist ─────────────────────── */

    @Test
    fun `a silent chart is the one kind that carries the note`() {
        val kind = ChatTurnKind.of(message(fromChart = false, kind = "chart_silent"))
        assertTrue(kind.showsChartSilentNote)
    }

    @Test
    fun `a care turn shows no note and still shows what it cited`() {
        val kind = ChatTurnKind.of(message(cited = listOf("moon in Virgo"), kind = "care"))
        assertEquals(ChatTurnKind.Care, kind)
        assertTrue(kind.showsCitations)
        assertFalse(kind.showsChartSilentNote)
    }

    @Test
    fun `a conversation turn does not decorate whatever it happened to cite`() {
        val kind = ChatTurnKind.of(message(cited = listOf("life path 7"), kind = "conversation"))
        assertFalse(kind.showsCitations)
    }

    /* ── forward compatibility ─────────────────────────────────────────── */

    @Test
    fun `a kind this build has never heard of degrades to an ordinary reply`() {
        val kind = ChatTurnKind.of(message(cited = listOf("sun in Pisces"), kind = "elegy"))
        assertEquals(ChatTurnKind.Reading, kind)
    }

    @Test
    fun `a payload with no turn_kind still decodes`() {
        // The field is new. A thread written before it existed, and the thread
        // route until it catches up, both send messages without it.
        val dto = json.decodeFromString<ChatMessageDto>(
            """{"id":"m","role":"alma","body":"…","cited_factors":["sun in Pisces"],
                "answered_from_chart":true,"created_at":"2026-08-07T00:00:00Z"}"""
        )
        assertNull(dto.turnKind)
        assertEquals(ChatTurnKind.Reading, ChatTurnKind.of(dto))
    }

    @Test
    fun `an unknown kind on the wire does not throw inside the deserialiser`() {
        val dto = json.decodeFromString<ChatMessageDto>(
            """{"id":"m","role":"alma","body":"…","turn_kind":"elegy",
                "cited_factors":[],"answered_from_chart":false}"""
        )
        assertEquals("elegy", dto.turnKind)
        assertEquals(ChatTurnKind.Conversation, ChatTurnKind.of(dto))
    }
}
