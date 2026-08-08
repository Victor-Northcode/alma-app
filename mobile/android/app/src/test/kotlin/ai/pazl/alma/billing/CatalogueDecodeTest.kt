package ai.pazl.alma.billing

import ai.pazl.alma.data.AlmaHttp
import ai.pazl.alma.data.dto.CatalogueDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The price list, decoded from the bytes the running backend actually sends.
 *
 * The payload below was copied out of `GET /v1/billing/catalogue` on the live
 * development server rather than written from the schema, because the one thing
 * that has already gone wrong here is the schema and the server disagreeing:
 * `offered` is a **string** — "shelf", "in-checkout", "after-door" — and this
 * app declared it a `Boolean`. With `isLenient = false` that is not a mislabel,
 * it is an exception, classified as `Unexpected`, on the only endpoint the
 * paywall reads. Every purchase in the product went through a screen that could
 * not load.
 *
 * Two details in this payload are worth keeping even though nothing branches on
 * them today: `interval` arrives as `""` rather than absent on a one-time
 * product, and there is a top-level `annual` key that duplicates a row inside
 * `items` — a transitional alias the server's own comment marks for removal.
 * Both are shapes a stricter parser would reject.
 */
class CatalogueDecodeTest {

    private val live = """
        {"currency":"USD","items":[
        {"slug":"natal","system":"natal","name":"Natal chart","kind":"one_time","interval":"","scope":"system","offered":"shelf","cents":899,"display":"${'$'}8.99"},
        {"slug":"birth-card","system":"birth-card","name":"Birth Card","kind":"one_time","interval":"","scope":"system","offered":"shelf","cents":899,"display":"${'$'}8.99"},
        {"slug":"archive","system":"*","name":"The whole archive","kind":"one_time","interval":"","scope":"all","offered":"shelf","cents":3899,"display":"${'$'}38.99"},
        {"slug":"monthly","system":"*","name":"Everything live, monthly","kind":"monthly","interval":"month","scope":"live","offered":"shelf","cents":999,"display":"${'$'}9.99"},
        {"slug":"annual","system":"*","name":"Everything, for a year","kind":"annual","interval":"year","scope":"all","offered":"shelf","cents":7899,"display":"${'$'}78.99"}],
        "annual":{"slug":"annual","system":"*","name":"Everything, for a year","kind":"annual","interval":"year","scope":"all","offered":"shelf","cents":7899,"display":"${'$'}78.99"},
        "provider":"paddle","requires_email":false,"merchant":"Paddle.com Market Ltd","unlocked":[]}
    """.trimIndent()

    @Test
    fun `the catalogue as the server sends it decodes`() {
        val catalogue = AlmaHttp.json.decodeFromString<CatalogueDto>(live)

        assertEquals("USD", catalogue.currency)
        assertEquals(5, catalogue.items.size)
        assertEquals("shelf", catalogue.items.first().offered)
        // An empty interval is how a one-time product says "does not renew".
        assertEquals("", catalogue.items.first { it.slug == "natal" }.interval)
        assertEquals("year", catalogue.items.first { it.slug == "annual" }.interval)
    }

    @Test
    fun `the ladder built from this catalogue is the door, the archive and both plans`() {
        val catalogue = AlmaHttp.json.decodeFromString<CatalogueDto>(live)
        val offered = catalogue.items.map { it.slug }.toSet()

        // The monthly used to be left off to keep the sheet short; the owner's
        // monetisation pass put it back — annual above monthly, under the
        // archive on a door intent — so the person can see what the plan costs
        // without leaving the screen they reached a door from.
        assertEquals(
            listOf("birth-card", "archive", "annual", "monthly"),
            ladder("birth-card", offered, emptyList()),
        )
    }

    @Test
    fun `every price this app could show comes from the server, never from a constant`() {
        val catalogue = AlmaHttp.json.decodeFromString<CatalogueDto>(live)
        // Not an assertion about the numbers — they are regional and they move.
        // It is an assertion that the field a screen would reach for exists and
        // is already formatted, so nobody is tempted to divide `cents` by 100
        // and put a dollar sign in front of it.
        catalogue.items.forEach { item ->
            assertNotNull(item.display)
            assertTrue(item.display.isNotBlank())
        }
    }
}
