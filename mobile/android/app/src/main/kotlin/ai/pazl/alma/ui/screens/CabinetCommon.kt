package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.ui.components.Hairline
import ai.pazl.alma.ui.components.Overline
import ai.pazl.alma.ui.components.animatePressGive
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaSpacing
import ai.pazl.alma.ui.theme.AlmaTheme
import ai.pazl.alma.ui.theme.PillShape
import androidx.compose.foundation.LocalIndication
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.unit.Velocity
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.roundToInt
import kotlin.math.sin

/**
 * The parts every cabinet screen needs and none of them should own.
 *
 * Three kinds of thing live here, and they are together because they are all
 * answers to the same question — *how does a screen turn what the server said
 * into something a person can read?*
 *
 * 1. **Reading an engine payload.** `CalcResultDto.data` is a `JsonObject` on
 *    purpose (see the note on the DTO), so every screen that opens one narrows
 *    by hand. Doing that narrowing once, here, is what stops six screens each
 *    inventing their own idea of what a missing field means. Every helper below
 *    answers null rather than a default, because on a **locked** system the
 *    fields really are absent — the server trims the payload to its preview —
 *    and a zero in place of an absent orb is an invented fact.
 * 2. **Naming things in the reader's language.** Sign names, moon phases,
 *    elements and axis names all arrive from the engine *in English* — they are
 *    data, not copy — and are translated at the point they become a sentence. A
 *    value the string table has never heard of prints itself rather than
 *    vanishing: readable and wrong-language beats blank.
 * 3. **The two or three visual atoms** this design has instead of cards: a
 *    ruled label, a hairline row, a pill.
 *
 * There is deliberately no fixture fallback anywhere in the cabinet. The web app
 * has one and marks it with a "sample data" badge; this app simply does not
 * carry a second copy of somebody's chart, so there is nothing to badge and no
 * way for an unmarked sample to reach a screen.
 */

/* ── reading an engine payload ─────────────────────────────────────────── */

internal fun JsonObject.obj(key: String): JsonObject? = this[key] as? JsonObject

internal fun JsonObject.array(key: String): JsonArray? = this[key] as? JsonArray

/**
 * A string field, or null when it is absent, null, blank or not a string.
 *
 * The `isString` guard matters: without it a numeric `3` would read as the text
 * "3", and a field the engine sends as a number would start appearing in places
 * that are only meant to print prose.
 */
internal fun JsonObject.text(key: String): String? =
    (this[key] as? JsonPrimitive)
        ?.takeIf { it.isString }
        ?.contentOrNull
        ?.takeIf { it.isNotBlank() }

internal fun JsonObject.number(key: String): Double? =
    (this[key] as? JsonPrimitive)?.takeIf { !it.isString }?.doubleOrNull

internal fun JsonObject.int(key: String): Int? = number(key)?.roundToInt()

internal fun JsonObject.bool(key: String): Boolean? =
    (this[key] as? JsonPrimitive)?.booleanOrNull

/** 0.7 → "0°42′", the way a chart prints an orb. */
internal fun formatOrb(orb: Double): String {
    var degrees = floor(orb).toInt()
    var minutes = ((orb - degrees) * 60).roundToInt()
    if (minutes == 60) {
        degrees += 1
        minutes = 0
    }
    return "$degrees°${minutes.toString().padStart(2, '0')}′"
}

/** The engine's own notation, so a transit row prints the way a chart does. */
internal val BodyGlyphs: Map<String, String> = mapOf(
    "sun" to "☉", "moon" to "☽", "mercury" to "☿", "venus" to "♀", "mars" to "♂",
    "jupiter" to "♃", "saturn" to "♄", "uranus" to "♅", "neptune" to "♆", "pluto" to "♇",
    "true_node" to "☊", "mean_node" to "☊", "chiron" to "⚷", "lilith" to "⚸",
    // Not bodies, and with no glyph of their own: ASC and MC are what the
    // engine itself calls them.
    "ascendant" to "ASC", "midheaven" to "MC",
)

/**
 * "true_node" → "True node".
 *
 * The non-composable fallback, for the rare row built outside composition.
 * Everything on a screen should prefer [bodyWord], which translates.
 */
internal fun bodyName(name: String): String =
    name.replace('_', ' ').replaceFirstChar { it.uppercase() }

private val BodyWords: Map<String, Int> = mapOf(
    "sun" to R.string.body_sun, "moon" to R.string.body_moon,
    "mercury" to R.string.body_mercury, "venus" to R.string.body_venus,
    "mars" to R.string.body_mars, "jupiter" to R.string.body_jupiter,
    "saturn" to R.string.body_saturn, "uranus" to R.string.body_uranus,
    "neptune" to R.string.body_neptune, "pluto" to R.string.body_pluto,
    "true_node" to R.string.body_true_node, "mean_node" to R.string.body_mean_node,
    "chiron" to R.string.body_chiron, "lilith" to R.string.body_lilith,
    "ascendant" to R.string.body_ascendant, "midheaven" to R.string.body_midheaven,
)

/**
 * A body, as a word, in the reader's language.
 *
 * A placement used to be printed as "⊙ 9°52′ ♑︎ · H3", which asks a reader to
 * know four notations at once. These are the same facts spelled out, because a
 * citation nobody can read cites nothing. A body this table has not caught up
 * with prints the engine's own word rather than a blank.
 */
@Composable
internal fun bodyWord(name: String): String =
    BodyWords[name]?.let { stringResource(it) } ?: bodyName(name)

private val HouseWords: List<Int> = listOf(
    R.string.house_1, R.string.house_2, R.string.house_3, R.string.house_4,
    R.string.house_5, R.string.house_6, R.string.house_7, R.string.house_8,
    R.string.house_9, R.string.house_10, R.string.house_11, R.string.house_12,
)

/** "3" → "3rd house", in the reader's language. */
@Composable
internal fun houseWord(number: Int): String =
    HouseWords.getOrNull(number - 1)?.let { stringResource(it) } ?: "house $number"

private val AspectWords: Map<String, Int> = mapOf(
    "conjunction" to R.string.aspect_conjunction, "opposition" to R.string.aspect_opposition,
    "trine" to R.string.aspect_trine, "square" to R.string.aspect_square,
    "sextile" to R.string.aspect_sextile, "quincunx" to R.string.aspect_quincunx,
    "quintile" to R.string.aspect_quintile, "biquintile" to R.string.aspect_biquintile,
    "semisextile" to R.string.aspect_semisextile, "semisquare" to R.string.aspect_semisquare,
    "sesquiquadrate" to R.string.aspect_sesquiquadrate,
)

/**
 * An aspect, as the word a sentence needs — "conjunct", "en cuadratura".
 *
 * The Romance and German entries carry their own preposition, because "Marte
 * cuadratura Venus" is not a sentence and the tables were written by someone
 * who had to read them out loud.
 */
@Composable
internal fun aspectWord(name: String): String =
    AspectWords[name]?.let { stringResource(it) } ?: name

/**
 * One contact, said the way the reader's language says it.
 *
 * **One template per language, because five of the seven cannot say this the
 * way English does.** The pieces used to be concatenated — body + aspect +
 * "your" + body — and that only works where the possessive does not decline.
 * German, French, Italian, Portuguese and Russian all agree "your" with the
 * gender of the noun after it, and the string tables solved it by making the
 * aspect word `— Konjunktion` and the word for "your" a bare `—`. On the front
 * page, in Russian, that produced «Юпитер — соединение — Асцендент»: three
 * words, two dashes, not a sentence.
 *
 * English and Spanish keep the possessive; the other five name both ends and
 * then the aspect, in the nominative, where nothing agrees with anything:
 * «Юпитер и Асцендент: соединение».
 */
@Composable
internal fun contactPhrase(transiting: String, aspect: String, natal: String, retrograde: Boolean): String {
    val mark = if (retrograde) " " + stringResource(R.string.daily_retrograde) else ""
    return stringResource(
        R.string.daily_contact_phrase,
        bodyWord(transiting) + mark,
        aspectWord(aspect),
        bodyWord(natal),
    )
}

/**
 * "23°14′ ♓︎" → "23°14′ Piscis" — the engine's formatted degree with the sign
 * glyph spelled out in the reader's language. The engine appends a variation
 * selector to some glyphs; the replacement leaves it behind, so it is swept.
 */
@Composable
internal fun spellSigns(formatted: String): String {
    var out = formatted
    for ((sign, glyph) in SignGlyphs) {
        if (glyph in out) out = out.replace(glyph, signWord(sign))
        // The bare glyph without the variation selector, which some payload
        // fields use.
        val bare = glyph.removeSuffix("︎")
        if (bare in out) out = out.replace(bare, signWord(sign))
    }
    return out.replace("︎", "").trim()
}

/** Sign name to glyph. Design metadata about the zodiac, not about a person. */
internal val SignGlyphs: Map<String, String> = mapOf(
    "Aries" to "♈︎", "Taurus" to "♉︎", "Gemini" to "♊︎", "Cancer" to "♋︎",
    "Leo" to "♌︎", "Virgo" to "♍︎", "Libra" to "♎︎", "Scorpio" to "♏︎",
    "Sagittarius" to "♐︎", "Capricorn" to "♑︎", "Aquarius" to "♒︎", "Pisces" to "♓︎",
)

/* ── naming things in the reader's language ────────────────────────────── */

/**
 * Which question each system answers.
 *
 * Design metadata rather than API data: the hub sends a slug and a status and
 * nothing about how to group them, and the grouping is a product decision — a
 * newcomer does not know what a solar return is but does know "what happens
 * this year". Lifted from `src/lib/data.ts`.
 */
internal val SystemGroups: Map<String, Int> = mapOf(
    AlmaSystem.NATAL to R.string.group_who_am_i,
    AlmaSystem.NUMEROLOGY to R.string.group_who_am_i,
    AlmaSystem.BIRTH_CARD to R.string.group_who_am_i,
    AlmaSystem.TRANSITS to R.string.group_right_now,
    AlmaSystem.SOLAR_RETURN to R.string.group_this_year,
    AlmaSystem.COMPATIBILITY to R.string.group_how_we_match,
    AlmaSystem.ASTROCARTOGRAPHY to R.string.group_where_to_be,
    AlmaSystem.SYNTHESIS to R.string.group_all_of_it,
)

/** The order the groups are shown in. Synthesis has its own block and is absent. */
internal val GroupOrder: List<Int> = listOf(
    R.string.group_who_am_i,
    R.string.group_right_now,
    R.string.group_this_year,
    R.string.group_how_we_match,
    R.string.group_where_to_be,
)

private val SystemNames: Map<String, Int> = mapOf(
    AlmaSystem.NATAL to R.string.system_natal,
    AlmaSystem.NUMEROLOGY to R.string.system_numerology,
    AlmaSystem.BIRTH_CARD to R.string.system_birth_card,
    AlmaSystem.TRANSITS to R.string.system_transits,
    AlmaSystem.SOLAR_RETURN to R.string.system_solar_return,
    AlmaSystem.COMPATIBILITY to R.string.system_compatibility,
    AlmaSystem.ASTROCARTOGRAPHY to R.string.system_astrocartography,
    AlmaSystem.SYNTHESIS to R.string.system_synthesis,
)

/**
 * A system's name, in the reader's language.
 *
 * An unknown slug prints itself. That is not laziness: `AlmaSystem.ALL` is a
 * list the *backend* controls, a ninth system will appear in the hub before
 * this app is rebuilt, and a row reading "tarot" is better than a blank one.
 */
@Composable
internal fun systemName(slug: String): String =
    SystemNames[slug]?.let { stringResource(it) } ?: slug

private val SignNames: Map<String, Int> = mapOf(
    "Aries" to R.string.sign_aries,
    "Taurus" to R.string.sign_taurus,
    "Gemini" to R.string.sign_gemini,
    "Cancer" to R.string.sign_cancer,
    "Leo" to R.string.sign_leo,
    "Virgo" to R.string.sign_virgo,
    "Libra" to R.string.sign_libra,
    "Scorpio" to R.string.sign_scorpio,
    "Sagittarius" to R.string.sign_sagittarius,
    "Capricorn" to R.string.sign_capricorn,
    "Aquarius" to R.string.sign_aquarius,
    "Pisces" to R.string.sign_pisces,
)

/**
 * A sign, glyph and name, in the reader's language.
 *
 * Only ever needed when the chart is locked: an open one carries `formatted`
 * on every placement, which already reads "23°14′ ♓︎" and needs no words. The
 * fallback matters because a preview payload names the three signs and nothing
 * else, and those three are the whole of what a locked chart may show.
 */
/**
 * A sign, as a word, in the reader's language.
 *
 * [signLabel] puts the glyph in front, which is right for a pill in a row of
 * chart notation and wrong inside a sentence — "♍︎ Virgo rising" reads as a
 * paste rather than as something anybody would say. The chat's opening
 * questions need the word alone.
 *
 * An unrecognised sign prints itself, for the same reason a system does: the
 * engine's vocabulary is the backend's to change, and an untranslated sign name
 * is still a sign name.
 */
@Composable
internal fun signWord(sign: String): String =
    SignNames[sign]?.let { stringResource(it) } ?: sign

@Composable
internal fun signLabel(sign: String?): String? {
    if (sign == null) return null
    val name = SignNames[sign]?.let { stringResource(it) } ?: sign
    return SignGlyphs[sign]?.let { "$it $name" } ?: name
}

private val AxisNames: Map<String, Int> = mapOf(
    "Direction" to R.string.axis_direction,
    "Character" to R.string.axis_character,
    "Mind" to R.string.axis_mind,
    "Relationships" to R.string.axis_relationships,
    "Resources" to R.string.axis_resources,
    "Work" to R.string.axis_work,
    "Weak point" to R.string.axis_weak_point,
    "Growth" to R.string.axis_growth,
    "Rhythms" to R.string.axis_rhythms,
)

@Composable
internal fun axisName(name: String): String =
    AxisNames[name]?.let { stringResource(it) } ?: name

private val PhaseNames: Map<String, Int> = mapOf(
    "new moon" to R.string.phase_new_moon,
    "waxing crescent" to R.string.phase_waxing_crescent,
    "first quarter" to R.string.phase_first_quarter,
    "waxing gibbous" to R.string.phase_waxing_gibbous,
    "full moon" to R.string.phase_full_moon,
    "waning gibbous" to R.string.phase_waning_gibbous,
    "last quarter" to R.string.phase_last_quarter,
    "waning crescent" to R.string.phase_waning_crescent,
)

@Composable
internal fun phaseName(phase: String): String =
    PhaseNames[phase]?.let { stringResource(it) } ?: phase

private val ElementNames: Map<String, Int> = mapOf(
    "fire" to R.string.element_fire,
    "earth" to R.string.element_earth,
    "air" to R.string.element_air,
    "water" to R.string.element_water,
)

@Composable
internal fun elementName(element: String): String =
    ElementNames[element]?.let { stringResource(it) } ?: element

private val ScoreNames: Map<String, Int> = mapOf(
    "attraction" to R.string.score_attraction,
    "warmth" to R.string.score_warmth,
    "friction" to R.string.score_friction,
    "endurance" to R.string.score_endurance,
)

@Composable
internal fun scoreName(score: String): String =
    ScoreNames[score]?.let { stringResource(it) } ?: bodyName(score)

/* ── dates ─────────────────────────────────────────────────────────────── */

/**
 * "14 March 1998" from "1998-03-14", in the reader's language.
 *
 * Parsed by hand rather than with `java.time` and a localised pattern, and that
 * is a deliberate trade. `DateTimeFormatter.ofLocalizedDate` follows the
 * *device's* locale, and this app's language is an account setting that can
 * differ from it — somebody reading Alma in Spanish on an English phone would
 * get their birth date in English inside a Spanish sentence. The month names
 * come from the same string table as everything else, so the two always agree.
 *
 * A timestamp is truncated to its date: an entitlement expires at an instant,
 * but "renews 12 April" is what anybody wants to know.
 */
@Composable
internal fun readableDate(iso: String?): String {
    if (iso == null || iso.length < 10) return ""
    val months = stringArrayResource(R.array.months)
    val year = iso.substring(0, 4).toIntOrNull() ?: return iso
    val month = iso.substring(5, 7).toIntOrNull() ?: return iso
    val day = iso.substring(8, 10).toIntOrNull() ?: return iso
    val name = months.getOrNull(month - 1) ?: return iso
    return "$day $name $year"
}

/**
 * "19 March" — the day inside a window that is thirty days wide, so the year
 * would be noise. The weekday is left off because the string table names months
 * and not days.
 */
@Composable
internal fun dayAndMonth(iso: String?): String? {
    if (iso == null || iso.length < 10) return null
    val months = stringArrayResource(R.array.months)
    val month = iso.substring(5, 7).toIntOrNull() ?: return null
    val day = iso.substring(8, 10).toIntOrNull() ?: return null
    val name = months.getOrNull(month - 1) ?: return null
    return "$day $name"
}

/* ── the visual atoms this design has instead of cards ─────────────────── */

/**
 * A section label with a rule running to the edge, and optionally a number at
 * the end of it.
 *
 * This is the product's heading. There is no card, no filled header bar and no
 * elevation anywhere in the cabinet — "no boxes" means content sits on the night
 * and what separates it is a hairline.
 */
@Composable
internal fun RuledLabel(
    text: String,
    modifier: Modifier = Modifier,
    trailing: String? = null,
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Overline(text)
        Hairline(Modifier.weight(1f))
        if (!trailing.isNullOrBlank()) {
            Text(text = trailing, style = AlmaTheme.type.meta, color = AlmaPalette.Gold)
        }
    }
}

/**
 * One row on the night, with a hairline under it.
 *
 * The line is drawn rather than composed so a row costs one layout node instead
 * of two, and so the last row in a list can drop it without the caller having
 * to know it is the last.
 */
@Composable
internal fun CabinetRow(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    rule: Boolean = true,
    content: @Composable RowScope.() -> Unit,
) {
    val hairline = AlmaPalette.Hairline
    // The give of paper under a finger — see `Arrival.kt`. The interaction
    // source is watched here so the whole row (hairline included) gives,
    // not only the ripple's bounds.
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val give = animatePressGive(pressed)
    Row(
        modifier = modifier
            .fillMaxWidth()
            .graphicsLayer {
                scaleX = give
                scaleY = give
            }
            .then(
                if (onClick != null) {
                    Modifier.clickable(
                        interactionSource = interaction,
                        indication = LocalIndication.current,
                        role = Role.Button,
                        onClick = onClick,
                    )
                } else {
                    Modifier
                }
            )
            .drawBehind {
                if (rule) {
                    drawLine(
                        color = hairline,
                        start = Offset(0f, size.height),
                        end = Offset(size.width, size.height),
                        strokeWidth = 1f,
                    )
                }
            }
            .padding(vertical = 15.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp),
        content = content,
    )
}

/**
 * A cited placement, set in the serif and bounded by a hairline pill.
 *
 * Every one of these is something the engine calculated. Nothing decorative is
 * ever put in one — a pill is the shape this product uses to say "this is a
 * fact from your chart".
 */
@Composable
internal fun Pill(text: String, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .border(1.dp, AlmaPalette.HairlineGold, PillShape)
            .padding(horizontal = 13.dp, vertical = 7.dp),
    ) {
        Text(text = text, style = AlmaTheme.type.positions)
    }
}

/** The word at the end of a system row: gold when it is ready, muted when not. */
@Composable
internal fun StatusTag(text: String, ready: Boolean, modifier: Modifier = Modifier) {
    Text(
        text = text,
        style = AlmaTheme.type.meta,
        color = if (ready) AlmaPalette.GoldBright else AlmaPalette.Muted3,
        textAlign = TextAlign.End,
        modifier = modifier,
    )
}

/**
 * The scrolling column every cabinet screen is.
 *
 * **It pads for the status bar and the sky does not**, which is the whole point
 * of the arrangement. `AlmaNavHost` used to hand the `NavHost` the scaffold's
 * insets, so every screen — sky included — started below the status bar and a
 * flat strip sat above it. The scaffold is full-bleed now, `NightSky` runs to
 * the top of the display, and the inset is applied *here*, to the content only.
 *
 * `safeDrawing` rather than `statusBars`: it also covers a display cutout and a
 * caption bar, which `statusBars` alone does not, and `only(Top)` because the
 * bottom belongs to the tab bar and is already handled by the scaffold.
 */
@Composable
internal fun CabinetPage(
    modifier: Modifier = Modifier,
    horizontalPadding: Dp = AlmaSpacing.Pad,
    /**
     * Whether text is allowed to scroll *under* the status bar.
     *
     * True on the night screens and it is the nicer behaviour there: the first
     * line starts below the bar, and what has already been read slides beneath
     * it against the starfield.
     *
     * False on the one parchment surface, because the status bar's glyphs are
     * drawn light for the night canvas — `MainActivity` forces
     * `SystemBarStyle.dark` for the whole app — and light glyphs over cream
     * paper are illegible on top of the reader's own ink. Seen on the emulator:
     * the wifi and battery icons sitting inside the words of a chapter. With
     * this false the inset is applied *outside* the scroll, so the viewport
     * starts below the bar and nothing passes under it; the parchment
     * background still runs to the top of the display, which is the part worth
     * keeping.
     */
    contentUnderStatusBar: Boolean = true,
    /**
     * How far the reader has pulled past the last line, in pixels. Null on
     * every screen that does not ask — a page that wants nothing pays nothing.
     *
     * Here rather than in the one screen that wants it because this owns the
     * scroll, and a chapter that built its own would have to re-derive the
     * margins, the insets and the reading width. See `ChapterBody`: pulling
     * past the end of a chapter opens the next one, the way a channel hands you
     * to the next channel.
     */
    onOverscroll: ((Float) -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val inset = Modifier.windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Top))
    val scroll = rememberScrollState()
    // The drag the scroll could not use, accumulated. At the bottom of the
    // content there is nowhere left to scroll, so everything the finger asks
    // for arrives here unconsumed — which is exactly the distance past the end.
    var pulled by remember { mutableFloatStateOf(0f) }
    val overscroll = remember(onOverscroll, scroll) {
        object : NestedScrollConnection {
            override fun onPostScroll(
                consumed: Offset,
                available: Offset,
                source: NestedScrollSource,
            ): Offset {
                val report = onOverscroll ?: return Offset.Zero
                // **A page with nothing to scroll has no end to pull past, and
                // a page not yet at its end is not being pulled past it.**
                // Without both tests a chapter still being written — a title
                // and a drawing, nothing to scroll — reported the top bounce as
                // a pull, and one flick turned a page nobody had read. iOS
                // carries the same guard; see `OverscrollReport`.
                if (scroll.maxValue <= 0 || scroll.value < scroll.maxValue) {
                    if (pulled > 0f) {
                        pulled = 0f
                        report(0f)
                    }
                    return Offset.Zero
                }
                if (available.y < 0f) {
                    pulled += -available.y
                    report(pulled)
                } else if (available.y > 0f && pulled > 0f) {
                    pulled = 0f
                    report(0f)
                }
                return Offset.Zero
            }

            override suspend fun onPreFling(available: Velocity): Velocity {
                // Letting go resets it: the arrow should relax rather than stay
                // fully drawn on a page nobody is touching.
                if (pulled > 0f) {
                    pulled = 0f
                    onOverscroll?.invoke(0f)
                }
                return Velocity.Zero
            }
        }
    }
    Column(
        modifier = modifier
            .fillMaxWidth()
            .then(if (onOverscroll != null) Modifier.nestedScroll(overscroll) else Modifier)
            // Modifier order *is* the behaviour here. Before `verticalScroll`
            // the inset shrinks the viewport; after it, the inset is part of
            // the scrolling content and scrolls away with it.
            .then(if (contentUnderStatusBar) Modifier else inset)
            .verticalScroll(scroll)
            .then(if (contentUnderStatusBar) inset else Modifier)
            .padding(horizontal = horizontalPadding, vertical = 18.dp)
            .widthIn(max = AlmaSpacing.Reading),
        content = content,
    )
}

/**
 * What a chart screen says when there is no birth data behind it.
 *
 * The action is optional because the graph does not hand every screen a route
 * to the form: `TodayScreen` is given `onAddBirthData` and can offer the button,
 * `SystemsScreen` is not and says the sentence alone rather than drawing a
 * control that cannot do anything. A cabinet reached without birth data is a
 * rare state — the start destination sends anybody without a profile into the
 * journey instead — so the sentence is what matters and the button is a
 * convenience.
 */
@Composable
internal fun NeedBirthData(modifier: Modifier = Modifier, action: (@Composable () -> Unit)? = null) {
    Column(
        modifier = modifier.fillMaxWidth().padding(vertical = 22.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(
            text = stringResource(R.string.state_no_birth_data),
            style = AlmaTheme.type.almaVoice,
        )
        action?.invoke()
    }
}

/**
 * The zodiac ring: two hairline circles with twelve ticks between them, and
 * whatever the screen wants at the centre.
 *
 * Decoration, and honest decoration — twelve divisions are a fact about the
 * zodiac rather than a claim about the person. Nothing on it is positioned from
 * anybody's chart, which is exactly why it can be drawn before the calculation
 * arrives without lying about anything. The web app's `ChartWheel` is the same
 * idea with more line work.
 */
@Composable
internal fun ZodiacRing(
    modifier: Modifier = Modifier,
    diameter: Dp = 168.dp,
    content: @Composable () -> Unit,
) {
    val ring = AlmaPalette.HairlineGold
    val tick = AlmaPalette.Gold.copy(alpha = 0.30f)
    val glow = AlmaPalette.Gold
    Box(
        modifier = modifier.size(diameter).drawBehind {
            val centre = Offset(size.width / 2f, size.height / 2f)
            val outer = size.minDimension / 2f
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(glow.copy(alpha = 0.13f), Color.Transparent),
                    center = centre,
                    radius = outer,
                ),
                radius = outer,
                center = centre,
            )
            drawCircle(color = ring, radius = outer, center = centre, style = HairlineStroke)
            drawCircle(color = ring, radius = outer * 0.84f, center = centre, style = HairlineStroke)
            repeat(12) { index ->
                val angle = index * 30.0 * PI / 180.0
                val dx = cos(angle).toFloat()
                val dy = sin(angle).toFloat()
                drawLine(
                    color = tick,
                    start = Offset(centre.x + dx * outer * 0.84f, centre.y + dy * outer * 0.84f),
                    end = Offset(centre.x + dx * outer, centre.y + dy * outer),
                    strokeWidth = 1f,
                )
            }
        },
        contentAlignment = Alignment.Center,
        content = { content() },
    )
}

private val HairlineStroke = Stroke(width = 1f)

/** A screen title, and the back arrow when there is somewhere to go back to. */
@Composable
internal fun ScreenTitle(
    title: String,
    modifier: Modifier = Modifier,
    onBack: (() -> Unit)? = null,
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (onBack != null) {
            val label = stringResource(R.string.nav_back)
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clickable(role = Role.Button, onClickLabel = label, onClick = onBack),
                contentAlignment = Alignment.Center,
            ) {
                Text(text = "←", style = AlmaTheme.type.displayL, color = AlmaPalette.Gold)
            }
        }
        Text(text = title, style = AlmaTheme.type.displayL, modifier = Modifier.weight(1f))
    }
}
