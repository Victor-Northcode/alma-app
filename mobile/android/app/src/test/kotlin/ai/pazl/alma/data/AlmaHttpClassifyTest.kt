package ai.pazl.alma.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The classifier, against the exact bodies `backend/alma/api` produces.
 *
 * Worth testing and worth testing here rather than through the network: these
 * are the branches that decide whether a person sees a paywall, a form, a
 * question about daylight saving, or a shrug. Every payload below was copied
 * from the `raise HTTPException(...)` that emits it, so a backend change that
 * renames one of these keys fails here rather than in the field as "the unlock
 * button does nothing".
 */
class AlmaHttpClassifyTest {

    @Test
    fun `a locked chapter names the system so the paywall can be about it`() {
        val body = """
            {"detail":{"error":"locked","message":"unlock to read",
                       "system":"natal","chapter":"iv"}}
        """.trimIndent()

        val failure = AlmaHttp.classify(402, body)

        assertTrue(failure is ApiFailure.Locked)
        failure as ApiFailure.Locked
        assertEquals("natal", failure.system)
        assertEquals("iv", failure.chapter)
    }

    @Test
    fun `a bare 402 with no body is still a paywall, not an error`() {
        val failure = AlmaHttp.classify(402, null)
        assertTrue(failure is ApiFailure.Locked)
    }

    @Test
    fun `answer_refused is an honest silence, not a validation error`() {
        // The chat route's own refusal. Its message is `str(exc)` from
        // `conversation.py` — English prose written for a traceback — so what
        // matters is that it lands somewhere the screen has its own sentence
        // for. On `Invalid` the chat printed that prose verbatim, in every
        // language.
        val body = """{"detail":{"error":"answer_refused","message":"no answer cited only real factors"}}"""
        val failure = AlmaHttp.classify(422, body)
        assertTrue(failure is ApiFailure.NothingToSay)
    }

    /**
     * The case the status code alone cannot decide. 422 is both "you did not
     * give me a birth time" — which opens a form — and an ordinary validation
     * failure, which is a bug in this app. Only the `error` key tells them
     * apart, which is why the body is read before the status.
     */
    @Test
    fun `a missing birth time is a form, and a plain 422 is not`() {
        val needsTime = AlmaHttp.classify(
            422,
            """{"detail":{"error":"birth_time_required","message":"needs a real birth time"}}""",
        )
        assertTrue(needsTime is ApiFailure.NeedsBirthTime)

        val ordinary = AlmaHttp.classify(422, """{"detail":"longitude must be <= 180"}""")
        assertTrue(ordinary is ApiFailure.Invalid)
        assertEquals("longitude must be <= 180", ordinary.message)
    }

    @Test
    fun `an ambiguous birth time carries both instants`() {
        val body = """
            {"detail":{"error":"ambiguous_birth_time","message":"that time happened twice",
                       "options":[{"choice":"earlier","utc":"1988-10-30T00:30:00+00:00"},
                                  {"choice":"later","utc":"1988-10-30T01:30:00+00:00"}]}}
        """.trimIndent()

        val failure = AlmaHttp.classify(409, body)

        assertTrue(failure is ApiFailure.AmbiguousTime)
        failure as ApiFailure.AmbiguousTime
        assertEquals(2, failure.options.size)
        assertEquals("earlier", failure.options[0].choice)
        assertEquals("1988-10-30T01:30:00+00:00", failure.options[1].utc)
    }

    @Test
    fun `the question limit carries the allowance it is limited to`() {
        val failure = AlmaHttp.classify(
            429,
            """{"detail":{"error":"question_limit","message":"that is all for today","allowance":3}}""",
        )
        assertTrue(failure is ApiFailure.QuestionLimit)
        assertEquals(3, (failure as ApiFailure.QuestionLimit).allowance)
    }

    /**
     * Four different `error` strings, one thing to say. All of them mean "we
     * could not ask" rather than "you may not"; a screen that told somebody to
     * buy something because the AI was down would be the worst version of this.
     */
    @Test
    fun `every unavailable reason collapses to one case`() {
        listOf("ai_unavailable", "billing_unavailable", "budget_exceeded", "place_index_missing")
            .forEach { reason ->
                val failure = AlmaHttp.classify(503, """{"detail":{"error":"$reason","message":"not now"}}""")
                assertTrue("$reason should be Unavailable", failure is ApiFailure.Unavailable)
            }
    }

    @Test
    fun `a deleted account clears the token exactly once`() {
        var cleared = 0
        val failure = AlmaHttp.classify(410, """{"detail":"this account is gone"}""") { cleared++ }

        assertTrue(failure is ApiFailure.AccountDeleted)
        assertEquals(1, cleared)
    }

    @Test
    fun `nothing else clears the token`() {
        var cleared = false
        listOf(401, 402, 422, 500, 503).forEach { status ->
            AlmaHttp.classify(status, null) { cleared = true }
        }
        assertFalse(cleared)
    }

    /**
     * Garbage in, something sayable out. An HTML error page from a proxy is the
     * realistic version of this, and it must not become a crash inside the
     * error path — which is the one place a crash is hardest to notice.
     */
    @Test
    fun `an unparseable body still yields a failure with a message`() {
        val failure = AlmaHttp.classify(502, "<html><body>502 Bad Gateway</body></html>")
        assertTrue(failure is ApiFailure.Unexpected)
        assertEquals(502, (failure as ApiFailure.Unexpected).status)
        assertTrue(failure.message.isNotBlank())
    }
}
