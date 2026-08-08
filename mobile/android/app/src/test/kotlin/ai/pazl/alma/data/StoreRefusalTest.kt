package ai.pazl.alma.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The four billing refusals whose status codes lie about what they mean.
 *
 * These belong beside `AlmaHttpClassifyTest` in spirit and in their own file in
 * practice, because they were all one bug: the classifier read the `error` key
 * for eight cases and not for these, so every one of them fell through to a
 * status-code branch written for something else. Every payload below is copied
 * from the `raise HTTPException(...)` in `alma/api/routers/billing.py` that
 * emits it.
 */
class StoreRefusalTest {

    /**
     * The dangerous one, and the reason this file exists.
     *
     * `invalid_transaction` is a **401**, and 401 everywhere else in the app
     * means "the token was rejected — mint a new session". Nothing acts on it
     * today, which is exactly what makes it worth pinning: the first screen to
     * add a generic session-recovery handler would sign somebody out, and drop
     * their token, because a purchase signature failed.
     */
    @Test
    fun `a forged purchase is not a dead session`() {
        val body = """
            {"detail":{"error":"invalid_transaction",
                       "message":"the signature does not verify",
                       "platform":"googleplay"}}
        """.trimIndent()

        val failure = AlmaHttp.classify(401, body)

        assertFalse(
            "a 401 about a purchase must never read as an expired token",
            failure is ApiFailure.Unauthenticated,
        )
        assertTrue(failure is ApiFailure.StoreRefused)
        failure as ApiFailure.StoreRefused
        assertEquals("invalid_transaction", failure.reason)
        assertFalse(failure.pending)
    }

    @Test
    fun `a token that bought something else is a refusal, not an unexpected 409`() {
        val body = """
            {"detail":{"error":"product_mismatch",
                       "message":"Google says this token bought 'natal'; 'archive' was claimed",
                       "product":"archive"}}
        """.trimIndent()

        val failure = AlmaHttp.classify(409, body)

        assertTrue(failure is ApiFailure.StoreRefused)
        assertEquals("product_mismatch", (failure as ApiFailure.StoreRefused).reason)
    }

    /**
     * Not a refusal at all: a Play cash payment can sit unsettled for days.
     * `pending` is what lets the paywall say "not yet" rather than "no".
     */
    @Test
    fun `a purchase that has not settled says so`() {
        val body = """
            {"detail":{"error":"purchase_incomplete",
                       "message":"the purchase is pending","product":"natal"}}
        """.trimIndent()

        val failure = AlmaHttp.classify(409, body)

        assertTrue(failure is ApiFailure.StoreRefused)
        assertTrue((failure as ApiFailure.StoreRefused).pending)
    }

    /**
     * The 409 that answers `/subscription/cancel` for a store subscription
     * carries the deep link to the right row in Play, and the URL is the one
     * thing a client cannot work out for itself. It used to be discarded.
     */
    @Test
    fun `cancel at store keeps the url it arrived with`() {
        val body = """
            {"detail":{"error":"cancel_at_store",
                       "message":"this subscription is managed by Google Play",
                       "provider":"googleplay",
                       "manage_url":"https://play.google.com/store/account/subscriptions"}}
        """.trimIndent()

        val failure = AlmaHttp.classify(409, body)

        assertTrue(failure is ApiFailure.CancelAtStore)
        assertEquals(
            "https://play.google.com/store/account/subscriptions",
            (failure as ApiFailure.CancelAtStore).manageUrl,
        )
    }

    /**
     * The gate that has not moved: a real 401 about the *session* still has to
     * be `Unauthenticated`, or adding the four cases above would have traded
     * one wrong answer for another.
     */
    @Test
    fun `an ordinary 401 is still an expired session`() {
        val failure = AlmaHttp.classify(401, """{"detail":"token expired"}""")
        assertTrue(failure is ApiFailure.Unauthenticated)
    }
}
