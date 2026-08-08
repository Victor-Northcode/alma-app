package ai.pazl.alma.notify

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate
import java.time.ZoneId

/**
 * The rule, asserted.
 *
 * These tests are about the two ways this feature can be wrong, and both of them
 * are silent:
 *
 * * **It says something on a day with nothing in it** — which turns the product
 *   into the horoscope it exists not to be, and which is what happens the moment
 *   a threshold is dropped or a missing `weight` defaults open.
 * * **It says nothing on a day with something in it** — which happens if the
 *   engine's date format stops parsing, and which produces no error anywhere:
 *   the dates simply become null and every day looks empty.
 *
 * The payloads below are the backend's real shape, copied from
 * `alma/calc/service.py::_hit_dict`, including the detail that catches people
 * out: `isoformat(timespec="minutes")` writes **no seconds**, which
 * `Instant.parse` refuses outright.
 */
class DailyRuleTest {

    private val json = Json { ignoreUnknownKeys = true }
    private val utc: ZoneId = ZoneId.of("UTC")

    private fun hit(
        transiting: String = "saturn",
        natal: String = "sun",
        aspect: String = "square",
        exact: String? = "2026-08-07T14:20+00:00",
        enters: String? = "2026-07-20T00:00+00:00",
        leaves: String? = "2026-08-25T00:00+00:00",
        weight: Double = 0.9,
        urgency: Double = 0.8,
    ): DailyContact {
        val fields = buildList {
            add(""""transiting":"$transiting"""")
            add(""""natal":"$natal"""")
            add(""""aspect":"$aspect"""")
            add(""""glyph":"□"""")
            if (exact != null) add(""""exact":"$exact"""")
            if (enters != null) add(""""enters":"$enters"""")
            if (leaves != null) add(""""leaves":"$leaves"""")
            add(""""orb_now":0.4""")
            add(""""retrograde":false""")
            add(""""weight":$weight""")
            add(""""urgency":$urgency""")
            add(""""text":"transiting $transiting □ natal $natal · orb 0.40°"""")
        }
        val entry = json.parseToJsonElement("{${fields.joinToString(",")}}") as JsonObject
        return DailyContact.from(entry)!!
    }

    /**
     * The engine's own instant format, which is the one that breaks parsers.
     *
     * `isoformat(timespec="minutes")` produces "2026-08-06T21:10+00:00" and
     * `Instant.parse` throws on it. Left unhandled the failure is invisible —
     * the date becomes null, no exception reaches anybody, and the daily quietly
     * decides that nothing is ever exact.
     */
    @Test
    fun `parses the minute-precision instants the engine emits`() {
        val parsed = DailyContact.instant("2026-08-06T21:10+00:00")
        assertEquals("2026-08-06T21:10:00Z", parsed.toString())
        assertNull(DailyContact.instant(null))
        assertNull(DailyContact.instant("not a date"))
    }

    @Test
    fun `a heavy contact perfecting today is the day`() {
        val today = LocalDate.of(2026, 8, 7)
        val picked = DailyRule.candidates(listOf(hit()), today, DailyPreference.OCCASIONALLY, utc)
        assertEquals(1, picked.size)
        assertEquals("saturn", picked.first().transiting)
    }

    @Test
    fun `nothing is said on a day nothing perfects`() {
        val tomorrow = LocalDate.of(2026, 8, 8)
        val picked = DailyRule.candidates(listOf(hit()), tomorrow, DailyPreference.OCCASIONALLY, utc)
        assertTrue(picked.isEmpty())
    }

    /**
     * The filter is the feature. Mercury and Venus are 55% of all contacts and
     * 4% of the meaningful ones (`THE-DAILY.md §1.3`), and admitting them is
     * exactly how a daily becomes a horoscope.
     */
    @Test
    fun `a light contact perfecting today is not the day`() {
        val today = LocalDate.of(2026, 8, 7)
        val mercury = hit(transiting = "mercury", natal = "venus", weight = 0.21)
        assertTrue(DailyRule.candidates(listOf(mercury), today, DailyPreference.OCCASIONALLY, utc).isEmpty())
    }

    /**
     * A payload with no `weight` must produce **no** daily rather than a daily
     * about everything. A filter that defaults open is a horoscope, and the day
     * this matters is the day somebody changes `_hit_dict`.
     */
    @Test
    fun `a payload without a weight admits nothing`() {
        val today = LocalDate.of(2026, 8, 7)
        val entry = json.parseToJsonElement(
            """{"transiting":"pluto","natal":"sun","aspect":"square","exact":"2026-08-07T09:00+00:00"}"""
        ) as JsonObject
        val contact = DailyContact.from(entry)!!
        assertEquals(0.0, contact.weight, 0.0)
        assertTrue(DailyRule.candidates(listOf(contact), today, DailyPreference.OCCASIONALLY, utc).isEmpty())
    }

    /**
     * A slow body entering orb qualifies without perfecting, because entering
     * orb is the only news a Pluto square ever generates: it perfects once and
     * then sits in orb for years.
     */
    @Test
    fun `a slow body entering orb today qualifies`() {
        val today = LocalDate.of(2026, 8, 7)
        val entering = hit(
            transiting = "pluto",
            exact = "2026-11-02T00:00+00:00",
            enters = "2026-08-07T06:00+00:00",
            weight = 0.34,
        )
        val picked = DailyRule.candidates(listOf(entering), today, DailyPreference.OCCASIONALLY, utc)
        assertEquals(1, picked.size)
    }

    /** A *fast* body entering orb is not news. Only the slow list qualifies. */
    @Test
    fun `a fast body entering orb today does not qualify`() {
        val today = LocalDate.of(2026, 8, 7)
        val entering = hit(
            transiting = "mars",
            exact = "2026-08-11T00:00+00:00",
            enters = "2026-08-07T06:00+00:00",
            weight = 0.34,
        )
        assertTrue(DailyRule.candidates(listOf(entering), today, DailyPreference.OCCASIONALLY, utc).isEmpty())
    }

    /**
     * "Only what matters" is exact hits at 0.50 and nothing else — no orb
     * entries, whatever the body. Somebody who picked this asked for the Saturn
     * returns and the Pluto squares, and an orb entry is the loosest signal the
     * rule has.
     */
    @Test
    fun `only what matters admits no orb entries and no light hits`() {
        val today = LocalDate.of(2026, 8, 7)
        val entering = hit(
            transiting = "neptune",
            exact = "2026-12-01T00:00+00:00",
            enters = "2026-08-07T06:00+00:00",
            weight = 0.9,
        )
        val middling = hit(weight = 0.4)
        val heavy = hit(transiting = "pluto", weight = 0.95)

        val picked = DailyRule.candidates(
            listOf(entering, middling, heavy), today, DailyPreference.ONLY_WHAT_MATTERS, utc
        )
        assertEquals(listOf("pluto"), picked.map { it.transiting })
    }

    /** Off is off. Not "off unless something is very big". */
    @Test
    fun `off admits nothing at all`() {
        val today = LocalDate.of(2026, 8, 7)
        val heavy = hit(transiting = "pluto", weight = 1.0)
        assertTrue(DailyRule.candidates(listOf(heavy), today, DailyPreference.OFF, utc).isEmpty())
    }

    /** Heaviest first, and `urgency` breaks a tie between equal weights. */
    @Test
    fun `the heaviest contact wins and urgency breaks the tie`() {
        val today = LocalDate.of(2026, 8, 7)
        val lighter = hit(transiting = "jupiter", weight = 0.5, urgency = 0.5)
        val heavier = hit(transiting = "pluto", weight = 0.95, urgency = 0.4)
        val tiedButTighter = hit(transiting = "saturn", weight = 0.95, urgency = 0.9)

        val picked = DailyRule.candidates(
            listOf(lighter, heavier, tiedButTighter), today, DailyPreference.OCCASIONALLY, utc
        )
        assertEquals(listOf("saturn", "pluto", "jupiter"), picked.map { it.transiting })
    }

    /**
     * `active` and `upcoming` overlap, and reading one alone gets a different
     * answer depending on the hour — the worst possible bug on a screen called
     * Today. Both are read and the union is de-duplicated.
     */
    @Test
    fun `active and upcoming are merged and de-duplicated`() {
        val payload = json.parseToJsonElement(
            """
            {
              "active": [
                {"transiting":"saturn","natal":"sun","aspect":"square","exact":"2026-08-07T14:20+00:00","weight":0.9,"urgency":0.8}
              ],
              "upcoming": [
                {"transiting":"saturn","natal":"sun","aspect":"square","exact":"2026-08-07T14:20+00:00","weight":0.9,"urgency":0.8},
                {"transiting":"pluto","natal":"moon","aspect":"trine","exact":"2026-09-01T08:00+00:00","weight":0.7,"urgency":0.3}
              ]
            }
            """.trimIndent()
        ) as JsonObject

        val all = DailyContact.all(payload)
        assertEquals(2, all.size)
        assertEquals(setOf("saturn", "pluto"), all.map { it.transiting }.toSet())
    }

    /**
     * The count the settings screen shows. It is the rule applied day by day,
     * so it can never disagree with what Today draws — which is the point of
     * putting a number next to a cadence claim at all.
     */
    @Test
    fun `exactDays counts days and not contacts`() {
        val today = LocalDate.of(2026, 8, 7)
        val twoOnOneDay = listOf(
            hit(transiting = "saturn", exact = "2026-08-07T09:00+00:00"),
            hit(transiting = "pluto", exact = "2026-08-07T21:00+00:00"),
            hit(transiting = "uranus", exact = "2026-08-19T12:00+00:00"),
            // Outside the window, and must not be counted.
            hit(transiting = "neptune", exact = "2026-10-19T12:00+00:00"),
        )
        assertEquals(2, DailyRule.exactDays(twoOnOneDay, today, 30, DailyPreference.OCCASIONALLY, utc))
    }

    /**
     * The `push_daily_*` names, which nothing in Kotlin references — FCM names
     * them in the payload and Android resolves them against `strings.xml`. A
     * rename on either side without the other produces a notification that shows
     * nothing, so the shape is pinned here.
     */
    @Test
    fun `push keys match the resource names`() {
        assertEquals("push_daily_square", hit().pushKey(entering = false))
        assertEquals("push_daily_entering_square", hit().pushKey(entering = true))
    }

    /**
     * The delivery hour is clamped outside quiet hours rather than validated
     * with an error, so that no path can store 03:00 — including a future one
     * that writes the field without going through the picker.
     */
    @Test
    fun `the delivery hour cannot land inside quiet hours`() {
        // Asserted against `DEFAULT_HOUR` rather than against the literal it
        // happens to hold. The default moved from 08:00 to 10:00 and this test
        // failed on six lines that were only ever asserting "falls back to the
        // default" in a spelling that also pinned which default it was.
        val fallback = DailyStore.DEFAULT_HOUR
        assertEquals(fallback, DailyStore.clamp(3))
        assertEquals(fallback, DailyStore.clamp(23))
        assertEquals(fallback, DailyStore.clamp(22))
        assertEquals(9, DailyStore.clamp(9))
        assertEquals(21, DailyStore.clamp(21))
        assertEquals(fallback, DailyStore.clamp(-1))

        // The default itself has to survive its own clamp, or every fallback
        // above is a value the picker cannot show.
        assertEquals(fallback, DailyStore.clamp(fallback))

        // **05:00 is refused, and this line is the resolution of a real tension
        // in `THE-DAILY.md §5.2`.** That section justifies an editable delivery
        // hour with "I get up at 05:30 is a real fact about a person" and, two
        // sentences later, clamps the hour outside quiet hours of 22:00–08:00 —
        // which excludes 05:30. Both cannot hold, and the clamp wins: quiet
        // hours are the promise made to everybody, the delivery hour is a
        // preference, and a person who genuinely wakes at 05:30 loses two and a
        // half hours of freshness rather than the whole design losing its floor.
        //
        // The picker only offers 08:00–21:00, so nobody meets this through the
        // interface. It is pinned here because a future path that writes the
        // field directly must not be able to store 05:00 either.
        assertEquals(fallback, DailyStore.clamp(5))
    }
}
