package ai.pazl.alma.notify

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import java.time.Instant
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeParseException

/**
 * The one rule that decides whether today has anything to say.
 *
 * **The same rule on both platforms, and that is the entire point.** The
 * notification and the Today block must never disagree about what today is — a
 * push saying Mars crosses your Ascendant beside a screen saying nothing is
 * exact would destroy the only claim this feature makes. The thresholds below
 * are transcribed from `docs/THE-DAILY.md §6.3`, and the Swift copy in
 * `Alma/Daily/DailyRule.swift` carries the same numbers with the same comment.
 *
 * **Why it runs on the client at all.** `alma/api/routers/systems.py` returns
 * the transits payload *whole* even when the system is locked — `weight`,
 * `urgency`, `exact`, `enters` and `leaves` are all in `_hit_dict`, for every
 * reader, free or paying. So the day's event is derived from a request the
 * Today screen already makes: no new endpoint, no new cost, and no dependency
 * on a backend job that does not exist yet.
 *
 * **What it is not.** It is not a scoring system. `weight` and `urgency` are the
 * engine's own — `alma/engine/transits.py` computes `_weight` as the product of
 * aspect, transiting body and natal point — and `THE-DAILY.md §1.3` measured
 * that it already encodes the slow-versus-fast distinction the daily needs.
 * Nothing here invents a number.
 */
object DailyRule {

    /** A contact perfecting today qualifies at this weight. Median 45.5/year. */
    const val EXACT_FLOOR = 0.35

    /**
     * A slow body *entering orb* qualifies lower, because entering orb is the
     * only news a Pluto square ever generates — it perfects once and then sits
     * in orb for years, so waiting for the instant means never mentioning it.
     */
    const val ORB_ENTRY_FLOOR = 0.30

    /** "Only what matters": exact hits only, no orb entries. 7–13 a year. */
    const val ONLY_WHAT_MATTERS_FLOOR = 0.50

    /**
     * `alma/engine/transits.py::SLOW_BODIES`, copied rather than derived —
     * there is nothing to derive it from on a phone. If the engine's tuple
     * changes, this changes.
     */
    val SLOW_BODIES = setOf("jupiter", "saturn", "uranus", "neptune", "pluto", "chiron")

    /**
     * Everything today could be about, most important first.
     *
     * All of them rather than only the winner: the Today block shows the day and
     * the notification shows one line of it. The caller takes `first()`, and
     * nothing here decides that one is all there is.
     */
    fun candidates(
        hits: List<DailyContact>,
        day: LocalDate,
        preference: DailyPreference,
        zone: ZoneId = ZoneId.systemDefault(),
    ): List<DailyContact> {
        if (preference == DailyPreference.OFF) return emptyList()

        val qualifying = hits.filter { hit ->
            when (preference) {
                DailyPreference.OFF -> false

                // No orb entries and no valve: this position exists for people
                // who asked for the slow ones and nothing else, and an orb entry
                // is the loosest signal the rule has.
                DailyPreference.ONLY_WHAT_MATTERS ->
                    hit.weight >= ONLY_WHAT_MATTERS_FLOOR && hit.exactOn(day, zone)

                DailyPreference.OCCASIONALLY ->
                    (hit.weight >= EXACT_FLOOR && hit.exactOn(day, zone)) ||
                        (hit.transiting in SLOW_BODIES &&
                            hit.weight >= ORB_ENTRY_FLOOR &&
                            hit.entersOn(day, zone))
            }
        }

        // Highest weight wins, and `urgency` breaks the tie — it is weight
        // discounted by how far out of orb the contact is, so between two
        // equally heavy contacts it prefers the tighter one. Both are the
        // engine's; neither is computed here.
        return qualifying.sortedWith(
            compareByDescending<DailyContact> { it.weight }.thenByDescending { it.urgency }
        )
    }

    /**
     * How many of the next [days] days have something in them.
     *
     * This is the app checking its own claim. The settings screen says the daily
     * arrives "about once a week"; that number was measured over 24 charts and
     * none of them is the reader's. Counting the reader's own window with the
     * reader's own rule turns a claim into an observation.
     *
     * It is a **lower bound**: the server sends at most 60 future contacts
     * (`service.py`'s `hits[:60]`), so a chart with a dense month has days this
     * cannot see. The call site says so.
     */
    fun exactDays(
        hits: List<DailyContact>,
        from: LocalDate,
        days: Int,
        preference: DailyPreference,
        zone: ZoneId = ZoneId.systemDefault(),
    ): Int = (0 until days).count { offset ->
        candidates(hits, from.plusDays(offset.toLong()), preference, zone).isNotEmpty()
    }
}

/**
 * One contact between the sky and this chart, as the daily needs it.
 *
 * Deliberately not the display shape `TodayScreen.ActiveRows` builds inline.
 * That one formats a notation string and a joined meta line and throws away the
 * two numbers this rule is entirely made of; parsing twice is cheaper than
 * making a display type carry decision fields, which is how a view becomes the
 * place business rules hide.
 */
data class DailyContact(
    val transiting: String,
    val natal: String,
    val aspect: String,
    val glyph: String,
    val retrograde: Boolean,
    /** The instant it perfects. Null for a contact already past exactness. */
    val exact: Instant?,
    val enters: Instant?,
    val leaves: Instant?,
    val orbNow: Double,
    /** `_weight` — aspect × transiting body × natal point. The admission test. */
    val weight: Double,
    /** Weight discounted by how far out of orb it is today. The tie-break. */
    val urgency: Double,
    /** The engine's own sentence — what the validator would cite. */
    val spoken: String,
) {
    fun exactOn(day: LocalDate, zone: ZoneId): Boolean =
        exact?.atZone(zone)?.toLocalDate() == day

    fun entersOn(day: LocalDate, zone: ZoneId): Boolean =
        enters?.atZone(zone)?.toLocalDate() == day

    /** "♂℞ □ ASC" — the notation a chart prints, in every locale. */
    fun notation(glyphs: Map<String, String>): String {
        val mark = if (retrograde) "℞" else ""
        return "${glyphs[transiting] ?: transiting}$mark $glyph ${glyphs[natal] ?: natal}"
    }

    /**
     * Which `push_daily_*` resource the server would name for this contact.
     *
     * Nothing in the app sends itself a push, so this is not used to notify
     * anybody — it is what the developer-build "post one of these" path uses,
     * which is how the key set and the payload shape get exercised by something
     * rather than only asserted in a document.
     */
    fun pushKey(entering: Boolean): String =
        if (entering) "push_daily_entering_$aspect" else "push_daily_$aspect"

    companion object {

        /**
         * Read the `active` and `upcoming` arrays out of a transits payload.
         *
         * Both, merged and de-duplicated. `active` is what is in orb at the
         * scan's instant; `upcoming` is the first sixty contacts of the whole
         * scan. A contact perfecting later today is in both and one perfecting
         * tomorrow is only in the second, so reading one alone gets a different
         * answer depending on the hour — which is the worst possible bug on a
         * screen called Today.
         */
        fun all(data: JsonObject?): List<DailyContact> {
            if (data == null) return emptyList()
            val seen = mutableSetOf<String>()
            val out = mutableListOf<DailyContact>()
            for (key in listOf("active", "upcoming")) {
                val rows = data[key] as? JsonArray ?: continue
                for (entry in rows.filterIsInstance<JsonObject>()) {
                    val contact = from(entry) ?: continue
                    val id = "${contact.transiting}-${contact.aspect}-${contact.natal}-${contact.exact}"
                    if (seen.add(id)) out += contact
                }
            }
            return out
        }

        fun from(entry: JsonObject): DailyContact? {
            val transiting = entry.str("transiting") ?: return null
            val natal = entry.str("natal") ?: return null
            val aspect = entry.str("aspect") ?: return null
            return DailyContact(
                transiting = transiting,
                natal = natal,
                aspect = aspect,
                glyph = entry.str("glyph") ?: aspect,
                retrograde = (entry["retrograde"] as? JsonPrimitive)?.booleanOrNull == true,
                exact = instant(entry.str("exact")),
                enters = instant(entry.str("enters")),
                leaves = instant(entry.str("leaves")),
                orbNow = entry.num("orb_now") ?: 0.0,
                // **Zero when absent, not one.** A payload from a backend that
                // has not learned to send `weight` must produce *no* daily
                // rather than a daily about everything: the whole feature is a
                // filter, and a filter that defaults open is a horoscope.
                weight = entry.num("weight") ?: 0.0,
                urgency = entry.num("urgency") ?: 0.0,
                spoken = entry.str("text") ?: "$transiting $aspect $natal",
            )
        }

        /**
         * Parse one of the engine's instants.
         *
         * `isoformat(timespec="minutes")` produces "2026-08-06T21:10+00:00" —
         * **no seconds** — which `Instant.parse` refuses outright and
         * `OffsetDateTime.parse` accepts. Every transit's exact, enters and
         * leaves is written that way. Left unhandled it is not an error
         * anywhere: the date silently disappears and the daily quietly decides
         * that nothing is ever exact.
         */
        fun instant(value: String?): Instant? {
            if (value.isNullOrBlank()) return null
            return try {
                OffsetDateTime.parse(value).toInstant()
            } catch (_: DateTimeParseException) {
                try {
                    Instant.parse(value)
                } catch (_: DateTimeParseException) {
                    null
                }
            }
        }

        private fun JsonObject.str(key: String): String? =
            (this[key] as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull

        private fun JsonObject.num(key: String): Double? =
            (this[key] as? JsonPrimitive)?.doubleOrNull
    }
}
