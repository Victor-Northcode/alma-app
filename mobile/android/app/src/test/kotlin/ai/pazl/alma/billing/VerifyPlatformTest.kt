package ai.pazl.alma.billing

import ai.pazl.alma.data.dto.IapVerifyBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * The platform name in the verify body, pinned from the Kotlin side.
 *
 * `backend/tests/test_billing_iap_attack.py::test_the_platform_name_each_client_sends_resolves_to_an_adapter`
 * already reads this literal out of `AlmaClient.kt` and feeds it to
 * `provider_for`, which is the check that matters — it fails whichever side
 * drifts. This is the cheap half of the same pin, and it exists because the
 * Python one only runs when somebody runs the backend suite, and an Android
 * developer changing a string in a Kotlin file has no reason to.
 *
 * What went wrong: the literal was `"google"`. `_store_adapter` branches on
 * "paddle", "dodo", "appstore" and "googleplay", so every Android verification
 * answered `400 unknown_platform` **before Google was contacted at all** — the
 * whole Play revenue path, dead, and permanently: each relaunch replayed the
 * purchase, each replay 400ed, `redeem` correctly left it unacknowledged, and
 * Play auto-refunded three days later while the buyer looked at a locked
 * chapter.
 */
class VerifyPlatformTest {

    private val source = File(
        "src/main/kotlin/ai/pazl/alma/data/AlmaClient.kt"
    )

    @Test
    fun `the client sends a platform name the backend has an adapter for`() {
        val text = source.readText()
        val literal = Regex("""platform\s*=\s*"([a-z]+)"""").find(text)?.groupValues?.get(1)

        assertEquals(
            "AlmaClient must send a platform name `provider_for` branches on. " +
                "\"google\" is not one of them and answers 400 unknown_platform.",
            "googleplay",
            literal,
        )
    }

    @Test
    fun `the body carries the product slug and the purchase token separately`() {
        // A shape test rather than a value test: `/iap/verify` looks the product
        // up in the catalogue by key, so sending the Play id — `alma.natal` —
        // answers 404, which is money taken and nothing granted.
        val body = IapVerifyBody(
            platform = "googleplay",
            product = StoreProducts.slugFor("alma.birth_card").orEmpty(),
            transaction = "opaque-play-token",
        )
        assertEquals("birth-card", body.product)
        assertTrue(body.transaction.isNotBlank())
    }
}
