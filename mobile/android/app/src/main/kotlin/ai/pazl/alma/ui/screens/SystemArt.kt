package ai.pazl.alma.ui.screens

import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.ui.components.breathing
import ai.pazl.alma.ui.theme.AlmaPalette
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.ui.unit.dp
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.invisibleToUser
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.sp
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonObject
import java.time.LocalDate
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.sin

/**
 * One hero diagram per system — the iOS `SystemArt.swift` on the Compose
 * canvas, under the same law the natal wheel obeys: **everything here is read
 * from the system's own payload.** A date on the transit ring is a real
 * `exact`, a line on the map is a real computed meridian, a number in the life
 * ring is this person's pinnacle. When a datum is absent its stroke is simply
 * not drawn — a thinner picture, honestly thinner.
 *
 * Every diagram constructs itself over two seconds in the wheel's manner and
 * settles for good; the settled picture costs what a static one would.
 */
@Composable
internal fun SystemHeroArt(slug: String, data: JsonObject, age: Int?, modifier: Modifier = Modifier) {
    when (slug) {
        // The return *is* a chart — the same wheel, this year's sky.
        AlmaSystem.SOLAR_RETURN -> data.obj("chart")?.let { NatalWheel(it, modifier) }
        // The relationship's own sky: Davison when both hours are known, the
        // composite midpoints when they are not — honestly thinner.
        AlmaSystem.COMPATIBILITY -> relationshipChart(data)?.let { NatalWheel(it, modifier) }
        AlmaSystem.TRANSITS -> ArtCanvas(modifier, aspect = 1f) { m, p -> drawTransitRing(data, m, p) }
        AlmaSystem.ASTROCARTOGRAPHY -> ArtCanvas(modifier, aspect = 1.9f) { m, p -> drawLinesMap(data, m, p) }
        AlmaSystem.NUMEROLOGY -> ArtCanvas(modifier, aspect = 1f) { m, p -> drawNumerologyRing(data, age, m, p) }
        AlmaSystem.BIRTH_CARD -> {
            // The card's name is resolved here rather than inside the canvas:
            // a `DrawScope` has no access to resources, and the arcana table is
            // seven `<string>`s deep. Resolved once per composition, not per
            // frame — the art redraws sixty times a second.
            val cardName = data.obj("personality")?.text("name")?.let { arcanaWord(it) }
            ArtCanvas(modifier, aspect = 1.25f) { m, p -> drawBirthCard(data, cardName, m, p) }
        }
        AlmaSystem.SYNTHESIS -> ArtCanvas(modifier, aspect = 1f) { m, p -> drawSynthesisStar(data, m, p) }
    }
}

/**
 * `davison` carries its angles at the top level; the wheel expects them under
 * `angles`. Without both birth times there is no Davison and the fallback is
 * `composite`: bare midpoint longitudes, dressed in the same glyph notation
 * the engine prints everywhere else — spelling, not invention.
 */
private fun relationshipChart(data: JsonObject): JsonObject? {
    val davison = data.obj("davison")
    val placements = davison?.obj("placements")
    if (davison != null && placements != null) {
        return buildJsonObject {
            put("placements", placements)
            putJsonObject("angles") {
                davison.number("ascendant")?.let { put("ascendant", it) }
                davison.number("midheaven")?.let { put("midheaven", it) }
            }
        }
    }
    val composite = data.obj("composite") ?: return null
    val glyphs = mapOf(
        "sun" to "☉", "moon" to "☽", "mercury" to "☿", "venus" to "♀", "mars" to "♂",
        "jupiter" to "♃", "saturn" to "♄", "uranus" to "♅", "neptune" to "♆",
        "pluto" to "♇", "true_node" to "☊", "lilith" to "⚸", "chiron" to "⚷",
    )
    val bodies = composite.entries.mapNotNull { (name, value) ->
        val glyph = glyphs[name] ?: return@mapNotNull null
        val longitude = (value as? JsonPrimitive)?.doubleOrNull ?: return@mapNotNull null
        Triple(name, glyph, longitude)
    }
    if (bodies.isEmpty()) return null
    return buildJsonObject {
        putJsonObject("placements") {
            for ((name, glyph, longitude) in bodies) {
                putJsonObject(name) {
                    put("longitude", longitude)
                    put("glyph", glyph)
                }
            }
        }
    }
}

/* ── the shared intro clock ─────────────────────────────────────────────── */

@Composable
private fun ArtCanvas(
    modifier: Modifier,
    aspect: Float,
    draw: DrawScope.(TextMeasurer, Float) -> Unit,
) {
    val measurer = rememberTextMeasurer()
    val progress = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        progress.animateTo(
            targetValue = 1f,
            animationSpec = tween(durationMillis = 2000, easing = CubicBezierEasing(0.33f, 1f, 0.68f, 1f)),
        )
    }
    Canvas(
        modifier = modifier
            .breathing()
            .fillMaxWidth()
            .aspectRatio(aspect)
            // Decoration over the rows below, which carry the same facts in
            // words a reader can hear.
            .semantics { invisibleToUser() },
    ) {
        draw(measurer, progress.value)
    }
}

/** Which stretch of the intro an element owns, as its own 0…1. */
private fun phase(progress: Float, from: Float, to: Float): Float =
    ((progress - from) / (to - from)).coerceIn(0f, 1f)

/** "2026-08-08T10:51+00:00" → the calendar day; seconds never ride the wire. */
private fun calendarDay(iso: String?): LocalDate? =
    iso?.takeIf { it.length >= 10 }?.let { runCatching { LocalDate.parse(it.take(10)) }.getOrNull() }

private fun DrawScope.glyphAt(
    measurer: TextMeasurer, text: String, at: Offset, sizeSp: Float, color: Color,
) {
    val measured = measurer.measure(text, TextStyle(fontSize = sizeSp.sp, color = color))
    drawText(measured, topLeft = Offset(at.x - measured.size.width / 2f, at.y - measured.size.height / 2f))
}

/* ── transits: the year as a ring ───────────────────────────────────────── */

private data class YearArc(
    val glyph: String, val start: Float, val end: Float, val tense: Boolean, val weight: Float,
)

private fun yearArcs(data: JsonObject): List<YearArc> {
    val from = calendarDay(data.obj("window")?.text("from")) ?: return emptyList()
    val days = data.obj("window")?.number("days") ?: 365.0

    fun fraction(iso: String?): Float? {
        val day = calendarDay(iso) ?: return null
        return ((day.toEpochDay() - from.toEpochDay()) / days).toFloat().coerceIn(0f, 1f)
    }
    fun arc(contact: JsonObject): YearArc? {
        val exact = fraction(contact.text("exact")) ?: return null
        val start = fraction(contact.text("enters")) ?: exact
        val end = fraction(contact.text("leaves")) ?: minOf(exact + 0.02f, 1f)
        val aspect = contact.text("aspect").orEmpty()
        return YearArc(
            glyph = contact.text("glyph") ?: "·",
            start = start, end = maxOf(end, start),
            tense = aspect == "square" || aspect == "opposition",
            weight = (contact.number("weight") ?: 0.3).toFloat(),
        )
    }

    val active = data.array("active").orEmpty().filterIsInstance<JsonObject>().mapNotNull(::arc)
    val upcoming = data.array("upcoming").orEmpty().filterIsInstance<JsonObject>()
        .mapNotNull(::arc).sortedByDescending { it.weight }
    return (active + upcoming).take(9)
}

private fun DrawScope.drawTransitRing(data: JsonObject, measurer: TextMeasurer, progress: Float) {
    val side = min(size.width, size.height)
    val centre = Offset(size.width / 2f, size.height / 2f)
    val ring = side * 0.44f

    fun point(fraction: Float, radius: Float): Offset {
        val a = (fraction * 360f - 90f) * PI.toFloat() / 180f
        return Offset(centre.x + radius * cos(a), centre.y + radius * sin(a))
    }

    // The year itself sweeps closed.
    val sweep = phase(progress, 0f, 0.3f)
    drawArc(
        color = AlmaPalette.Gold.copy(alpha = 0.4f),
        startAngle = -90f, sweepAngle = 360f * sweep, useCenter = false,
        topLeft = Offset(centre.x - ring, centre.y - ring),
        size = Size(ring * 2f, ring * 2f),
        style = Stroke(width = 1f),
    )

    // Twelve month ticks light up around it.
    for (month in 0 until 12) {
        val lit = phase(progress, 0.1f + month * 0.02f, 0.3f + month * 0.02f)
        if (lit <= 0f) continue
        val f = month / 12f
        drawLine(
            color = AlmaPalette.Gold.copy(alpha = 0.35f * lit),
            start = point(f, ring - side * 0.012f),
            end = point(f, ring + side * 0.012f),
            strokeWidth = 1f,
        )
    }

    // The contacts, strongest-first, stacked inward one band each.
    val arcs = yearArcs(data)
    val step = side * 0.032f
    for ((index, arc) in arcs.withIndex()) {
        val grown = phase(progress, 0.3f + index * 0.05f, 0.55f + index * 0.05f)
        if (grown <= 0f) continue
        val radius = ring - side * 0.05f - index * step
        val span = maxOf(arc.end - arc.start, 0.004f)
        drawArc(
            color = (if (arc.tense) AlmaPalette.Disagree else AlmaPalette.Gold)
                .copy(alpha = 0.30f + 0.5f * arc.weight),
            startAngle = arc.start * 360f - 90f,
            sweepAngle = span * grown * 360f,
            useCenter = false,
            topLeft = Offset(centre.x - radius, centre.y - radius),
            size = Size(radius * 2f, radius * 2f),
            style = Stroke(width = 2f),
        )
        glyphAt(
            measurer, arc.glyph,
            point(arc.start + span / 2f, radius),
            sizeSp = side * 0.035f / density,
            color = AlmaPalette.StarFill.copy(alpha = grown),
        )
    }

    // The needle: now, at the top, drawn last.
    val armed = phase(progress, 0.85f, 1f)
    if (armed > 0f) {
        drawLine(
            color = AlmaPalette.GoldBright.copy(alpha = 0.9f * armed),
            start = point(0f, ring - side * 0.30f),
            end = point(0f, ring + side * 0.02f),
            strokeWidth = 1.2f,
        )
        glyphAt(
            measurer, "☉", point(0f, ring + side * 0.045f),
            sizeSp = side * 0.04f / density,
            color = AlmaPalette.GoldBright.copy(alpha = armed),
        )
    }
}

/* ── astrocartography: the lines on the earth ───────────────────────────── */

private fun DrawScope.drawLinesMap(data: JsonObject, measurer: TextMeasurer, progress: Float) {
    val w = size.width
    val h = size.height

    fun project(lat: Double, lon: Double): Offset =
        Offset(((lon + 180) / 360 * w).toFloat(), ((66 - lat) / 132 * h).toFloat())

    // The graticule sketches itself first. No coastline on purpose: a
    // coastline would be decoration, the lines are the calculation.
    val grid = phase(progress, 0f, 0.35f)
    for (i in 0..12) {
        val x = i / 12f * w
        drawLine(
            color = AlmaPalette.Gold.copy(alpha = 0.10f),
            start = Offset(x, 0f), end = Offset(x, h * grid), strokeWidth = 0.5f,
        )
    }
    for (i in 0..4) {
        val y = i / 4f * h
        drawLine(
            color = AlmaPalette.Gold.copy(alpha = if (i == 2) 0.22f else 0.10f),
            start = Offset(0f, y), end = Offset(w * grid, y),
            strokeWidth = if (i == 2) 0.8f else 0.5f,
        )
    }

    // Each line traces itself. Luminaries bright, the rest quiet.
    val lines = data.array("lines").orEmpty().filterIsInstance<JsonObject>()
    for ((index, line) in lines.withIndex()) {
        val drawn = phase(progress, 0.2f + (index % 12) * 0.03f, 0.65f + (index % 12) * 0.03f)
        if (drawn <= 0f) continue
        val points = line.array("points").orEmpty().filterIsInstance<JsonObject>()
        if (points.size < 2) continue
        val body = line.text("body").orEmpty()
        val luminary = body == "sun" || body == "moon"

        val path = Path()
        val visible = maxOf(2, (points.size * drawn).toInt())
        var started = false
        for (p in points.take(visible)) {
            val lat = p.number("lat") ?: continue
            val lon = p.number("lon") ?: continue
            val at = project(lat, lon)
            if (!started) { path.moveTo(at.x, at.y); started = true } else path.lineTo(at.x, at.y)
        }
        drawPath(
            path,
            color = if (luminary) AlmaPalette.GoldBright.copy(alpha = 0.5f)
            else AlmaPalette.StarFill.copy(alpha = 0.16f),
            style = Stroke(width = if (luminary) 1.1f else 0.6f),
        )
    }

    // The birthplace, last: one star where this person began.
    val birthplace = data.obj("birthplace")
    val lat = birthplace?.number("latitude")
    val lon = birthplace?.number("longitude")
    if (lat != null && lon != null) {
        val lit = phase(progress, 0.8f, 1f)
        if (lit > 0f) {
            val at = project(lat, lon)
            val r = 3.5f * lit
            for ((dx, dy) in listOf(r * 2.2f to 0f, -r * 2.2f to 0f, 0f to r * 2.2f, 0f to -r * 2.2f)) {
                drawLine(
                    color = AlmaPalette.GoldBright.copy(alpha = 0.8f * lit),
                    start = at, end = Offset(at.x + dx, at.y + dy), strokeWidth = 0.8f,
                )
            }
            drawCircle(AlmaPalette.StarFill.copy(alpha = lit), radius = r / 2f, center = at)
            drawCircle(
                AlmaPalette.Gold.copy(alpha = 0.4f * lit), radius = r * 2.6f, center = at,
                style = Stroke(width = 0.7f),
            )
        }
    }
}

/* ── numerology: the life as a ring ─────────────────────────────────────── */

private fun DrawScope.drawNumerologyRing(
    data: JsonObject, age: Int?, measurer: TextMeasurer, progress: Float,
) {
    val side = min(size.width, size.height)
    val centre = Offset(size.width / 2f, size.height / 2f)

    fun segments(key: String, span: Float): List<Triple<Int, Float, Float>> =
        data.array(key).orEmpty().filterIsInstance<JsonObject>().mapNotNull { item ->
            val number = item.int("number") ?: return@mapNotNull null
            val from = item.number("starts_age")?.toFloat() ?: return@mapNotNull null
            val to = item.number("ends_age")?.toFloat() ?: span
            Triple(number, from, to)
        }

    val lastPinnacle = data.array("pinnacles").orEmpty().filterIsInstance<JsonObject>()
        .mapNotNull { it.number("ends_age") }.maxOrNull() ?: 0.0
    val span = maxOf(lastPinnacle.toFloat() + 9f, 81f, ((age ?: 0) + 9).toFloat())

    fun angle(years: Float): Float = years / span * 360f - 90f
    fun point(years: Float, radius: Float): Offset {
        val a = angle(years) * PI.toFloat() / 180f
        return Offset(centre.x + radius * cos(a), centre.y + radius * sin(a))
    }

    fun band(
        rows: List<Triple<Int, Float, Float>>, radius: Float, colour: Color,
        opening: Float, upTo: Float,
    ) {
        for ((index, segment) in rows.withIndex()) {
            val (number, fromAge, toAge) = segment
            val grown = phase(progress, opening + index * 0.06f, upTo + index * 0.06f)
            if (grown <= 0f) continue
            // A hair of a gap between segments, so they read as chapters of a
            // life rather than one unbroken line.
            val from = fromAge + span * 0.006f
            val to = fromAge + (toAge - fromAge - span * 0.006f) * grown
            drawArc(
                color = colour.copy(alpha = 0.55f),
                startAngle = angle(from), sweepAngle = angle(to) - angle(from),
                useCenter = false,
                topLeft = Offset(centre.x - radius, centre.y - radius),
                size = Size(radius * 2f, radius * 2f),
                style = Stroke(width = 1.6f),
            )
            glyphAt(
                measurer, number.toString(),
                point((fromAge + toAge) / 2f, radius + side * 0.045f),
                sizeSp = side * 0.045f / density,
                color = colour.copy(alpha = grown),
            )
        }
    }

    band(segments("pinnacles", span), side * 0.40f, AlmaPalette.Gold, 0.1f, 0.4f)
    band(segments("cycles", span), side * 0.28f, AlmaPalette.StarFill, 0.3f, 0.6f)

    // Today's tick — only when the age is actually known.
    if (age != null) {
        val lit = phase(progress, 0.75f, 0.9f)
        if (lit > 0f) {
            drawLine(
                color = AlmaPalette.GoldBright.copy(alpha = 0.8f * lit),
                start = point(age.toFloat(), side * 0.245f),
                end = point(age.toFloat(), side * 0.44f),
                strokeWidth = 1f,
            )
        }
    }

    // The life path, breathing in at the centre.
    data.int("life_path")?.let { path ->
        val seated = phase(progress, 0.45f, 0.8f)
        if (seated > 0f) {
            if (path in listOf(11, 22, 33)) {
                // The aura only a master number earns.
                drawCircle(
                    AlmaPalette.Gold.copy(alpha = 0.30f * seated),
                    radius = side * 0.13f, center = centre, style = Stroke(width = 0.8f),
                )
            }
            glyphAt(
                measurer, path.toString(), centre,
                sizeSp = side * 0.17f * (0.7f + 0.3f * seated) / density,
                color = AlmaPalette.InkLight.copy(alpha = seated),
            )
        }
    }

    // The personal year, quietly under the centre.
    data.obj("personal")?.int("year")?.let { year ->
        val lit = phase(progress, 0.85f, 1f)
        if (lit > 0f) {
            glyphAt(
                measurer, "· $year ·",
                Offset(centre.x, centre.y + side * 0.15f),
                sizeSp = side * 0.05f / density,
                color = AlmaPalette.Gold.copy(alpha = 0.7f * lit),
            )
        }
    }
}

/* ── the birth card ─────────────────────────────────────────────────────── */

/**
 * Two removals here, matching iOS and made on the owner's reading of the screen.
 *
 * The **inner stroke** — a second rounded rectangle 5% inside the first — read
 * at this size as brackets around the numeral rather than as a card's border.
 * One line now.
 *
 * The **twenty-two dots** of the year cycle are gone, and the card's name in
 * words stands where they were. A row of points with one lit explains nothing
 * without a caption; «Умеренность» says what XIV is, which is what the picture
 * was missing. The numeral is not repeated in it — it is drawn on the card
 * directly above.
 */
private fun DrawScope.drawBirthCard(
    data: JsonObject,
    cardName: String?,
    measurer: TextMeasurer,
    progress: Float,
) {
    val side = min(size.width, size.height)
    val centre = Offset(size.width / 2f, size.height / 2f - side * 0.04f)
    val cardW = side * 0.38f
    val cardH = cardW * 1.55f

    fun cardFrame(at: Offset, w: Float, h: Float, trim: Float, alpha: Float) {
        if (trim <= 0f) return
        fun rounded(rect: Rect, corner: Float): Path = Path().apply {
            addRoundRect(RoundRect(rect, CornerRadius(corner)))
        }
        // Compose paths have no trim; the frame fades in with a slight grow
        // instead — the same arrival, spelled in this canvas's vocabulary.
        val grow = 0.94f + 0.06f * trim
        val outer = Rect(at.x - w / 2f * grow, at.y - h / 2f * grow, at.x + w / 2f * grow, at.y + h / 2f * grow)
        drawPath(
            rounded(outer, w * 0.07f),
            color = AlmaPalette.Gold.copy(alpha = alpha * trim),
            style = Stroke(width = 1.2f),
        )
        // The inner stroke lived here and read as brackets. See the note above.
    }

    // The soul card first, behind and to the side — the quieter twin.
    val soul = data.obj("soul")?.text("numeral")
    if (soul != null && data.bool("is_same_card") != true) {
        val shown = phase(progress, 0.35f, 0.7f)
        val at = Offset(centre.x + cardW * 0.62f, centre.y + cardH * 0.10f)
        cardFrame(at, cardW * 0.72f, cardH * 0.72f, shown, 0.35f)
        if (shown > 0.5f) {
            glyphAt(
                measurer, soul, at,
                sizeSp = side * 0.07f / density,
                color = AlmaPalette.Gold.copy(alpha = 0.5f * (shown - 0.5f) * 2f),
            )
        }
    }

    // The personality card draws itself in.
    val frame = phase(progress, 0f, 0.5f)
    val mainAt = Offset(centre.x - cardW * 0.18f, centre.y)
    cardFrame(mainAt, cardW, cardH, frame, 0.8f)

    val numeral = data.obj("personality")?.text("numeral")
    if (numeral != null) {
        val seated = phase(progress, 0.4f, 0.75f)
        if (seated > 0f) {
            glyphAt(
                measurer, numeral, mainAt,
                sizeSp = side * 0.13f * (0.8f + 0.2f * seated) / density,
                color = AlmaPalette.InkLight.copy(alpha = seated),
            )
        }
        data.obj("personality")?.text("element")?.let { element ->
            val drawn = phase(progress, 0.6f, 0.9f)
            drawElementMotif(
                element,
                at = Offset(mainAt.x, mainAt.y + cardH * 0.28f),
                width = cardW * 0.4f, progress = drawn,
            )
        }
    }

    // The card's name, last, after the frame has closed and the numeral has
    // seated — the picture finishes by saying what it is.
    val said = phase(progress, 0.7f, 1f)
    if (said > 0f && cardName != null) {
        glyphAt(
            measurer, cardName,
            Offset(centre.x, centre.y + cardH * 0.72f),
            sizeSp = side * 0.062f / density,
            color = AlmaPalette.Gold.copy(alpha = 0.85f * said),
        )
    }
}

/** One gesture per element — arcs for air, waves for water, flames for fire,
 * ground for earth. Nothing zodiacal: the card's element is its own word. */
private fun DrawScope.drawElementMotif(element: String, at: Offset, width: Float, progress: Float) {
    if (progress <= 0f) return
    val colour = AlmaPalette.Gold.copy(alpha = 0.55f * progress)
    when (element) {
        "air" -> for (i in 0 until 3) {
            val y = at.y + (i - 1) * width * 0.14f
            val path = Path().apply {
                moveTo(at.x - width / 2f, y)
                quadraticTo(at.x, y - width * 0.08f, at.x - width / 2f + width * progress, y)
            }
            drawPath(path, colour, style = Stroke(width = 0.8f))
        }
        "water" -> for (i in 0 until 2) {
            val y = at.y + i * width * 0.14f
            val path = Path().apply {
                moveTo(at.x - width / 2f, y)
                cubicTo(
                    at.x - width / 4f, y - width * 0.1f,
                    at.x + width / 4f, y + width * 0.1f,
                    at.x + width / 2f * (2f * progress - 1f), y,
                )
            }
            drawPath(path, colour, style = Stroke(width = 0.8f))
        }
        "fire" -> for (i in 0 until 3) {
            val x = at.x + (i - 1) * width * 0.22f
            val path = Path().apply {
                moveTo(x, at.y + width * 0.12f)
                quadraticTo(
                    x + width * 0.1f, at.y - width * 0.05f,
                    x, at.y + width * 0.12f - width * 0.3f * progress,
                )
            }
            drawPath(path, colour, style = Stroke(width = 0.8f))
        }
        else -> for (i in 0 until 2) {
            val y = at.y + i * width * 0.12f
            val span = width * (1f - i * 0.35f) * progress
            drawLine(colour, Offset(at.x - span / 2f, y), Offset(at.x + span / 2f, y), strokeWidth = 0.8f)
        }
    }
}

/* ── synthesis: nine axes as a star ─────────────────────────────────────── */

private fun DrawScope.drawSynthesisStar(data: JsonObject, measurer: TextMeasurer, progress: Float) {
    val side = min(size.width, size.height)
    val centre = Offset(size.width / 2f, size.height / 2f)
    val reach = side * 0.40f

    val axes = data.array("axes").orEmpty().filterIsInstance<JsonObject>()
    if (axes.isEmpty()) return

    for ((index, axis) in axes.withIndex()) {
        val grown = phase(progress, 0.05f + index * 0.06f, 0.4f + index * 0.06f)
        if (grown <= 0f) continue
        val a = (index.toFloat() / axes.size * 360f - 90f) * PI.toFloat() / 180f
        val tip = Offset(centre.x + reach * grown * cos(a), centre.y + reach * grown * sin(a))

        val verdict = axis.text("verdict").orEmpty()
        val agree = verdict == "agree"

        drawLine(
            color = AlmaPalette.Gold.copy(alpha = if (agree) 0.45f else 0.2f),
            start = Offset(centre.x + side * 0.05f * cos(a), centre.y + side * 0.05f * sin(a)),
            end = tip,
            strokeWidth = if (agree) 1.1f else 0.7f,
        )

        val pop = phase(progress, 0.35f + index * 0.06f, 0.6f + index * 0.06f)
        if (pop <= 0f) continue

        when (verdict) {
            "agree" -> {
                val r = side * 0.020f * pop
                drawCircle(AlmaPalette.GoldBright.copy(alpha = 0.9f * pop), radius = r, center = tip)
                drawCircle(
                    AlmaPalette.Gold.copy(alpha = 0.35f * pop), radius = r * 2f, center = tip,
                    style = Stroke(width = 0.7f),
                )
            }
            "disagree" -> {
                // The two accents the product reserves for exactly this.
                val r = side * 0.012f * pop
                val off = side * 0.018f
                val perp = a + PI.toFloat() / 2f
                for ((colour, sign) in listOf(AlmaPalette.Agree to 1f, AlmaPalette.Disagree to -1f)) {
                    drawCircle(
                        colour.copy(alpha = 0.85f * pop), radius = r,
                        center = Offset(tip.x + off * cos(perp) * sign, tip.y + off * sin(perp) * sign),
                    )
                }
            }
            else -> drawCircle(
                AlmaPalette.StarFill.copy(alpha = 0.5f * pop),
                radius = side * 0.010f * pop, center = tip,
            )
        }
    }

    // The centre: the product's four-point star, last.
    val seated = phase(progress, 0.8f, 1f)
    if (seated > 0f) {
        val r = side * 0.035f * seated
        val star = Path().apply {
            moveTo(centre.x, centre.y - r)
            quadraticTo(centre.x, centre.y, centre.x + r, centre.y)
            quadraticTo(centre.x, centre.y, centre.x, centre.y + r)
            quadraticTo(centre.x, centre.y, centre.x - r, centre.y)
            quadraticTo(centre.x, centre.y, centre.x, centre.y - r)
        }
        drawPath(star, AlmaPalette.GoldBright.copy(alpha = seated))
    }
}

/* ── compatibility: the four scores as gauges ───────────────────────────── */

/**
 * The four synastry scores as dials — the number the category sells with,
 * honestly ours: the arc *is* `score / 5`, friction keeps the red accent, a
 * missing score has no gauge. Mirrors iOS `CompatGauges`.
 */
@Composable
internal fun CompatGauges(data: JsonObject, modifier: Modifier = Modifier) {
    val scores = listOf(
        "attraction" to false, "warmth" to false, "friction" to true, "endurance" to false,
    ).mapNotNull { (key, tense) ->
        val value = data.obj("scores")?.number(key) ?: return@mapNotNull null
        Triple(key, (value / 5.0).coerceIn(0.0, 1.0).toFloat(), tense)
    }
    if (scores.isEmpty()) return

    val progress = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        progress.animateTo(1f, tween(1200, easing = CubicBezierEasing(0.33f, 1f, 0.68f, 1f)))
    }
    val measurer = rememberTextMeasurer()

    androidx.compose.foundation.layout.Row(modifier = modifier.breathing().fillMaxWidth()) {
        scores.forEachIndexed { index, (key, fraction, tense) ->
            androidx.compose.foundation.layout.Column(
                horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally,
                modifier = Modifier.weight(1f),
            ) {
                val local = ((progress.value - index * 0.12f) / 0.6f).coerceIn(0f, 1f)
                Canvas(Modifier.size(74.dp)) {
                    val centre = Offset(size.width / 2f, size.height / 2f)
                    val radius = size.minDimension * 0.42f
                    drawArc(
                        color = AlmaPalette.Body.copy(alpha = 0.14f),
                        startAngle = 135f, sweepAngle = 270f, useCenter = false,
                        topLeft = Offset(centre.x - radius, centre.y - radius),
                        size = Size(radius * 2f, radius * 2f),
                        style = Stroke(width = 3f, cap = androidx.compose.ui.graphics.StrokeCap.Round),
                    )
                    val swept = 270f * fraction * local
                    if (swept > 0f) {
                        drawArc(
                            color = if (tense) AlmaPalette.Disagree else AlmaPalette.Gold,
                            startAngle = 135f, sweepAngle = swept, useCenter = false,
                            topLeft = Offset(centre.x - radius, centre.y - radius),
                            size = Size(radius * 2f, radius * 2f),
                            style = Stroke(width = 3f, cap = androidx.compose.ui.graphics.StrokeCap.Round),
                        )
                    }
                    val pct = "${(fraction * 100 * local).toInt()}%"
                    val measured = measurer.measure(
                        pct,
                        TextStyle(fontSize = 15.sp, color = Color(0xFFF6F1E4).copy(alpha = 0.4f + 0.6f * local)),
                    )
                    drawText(
                        measured,
                        topLeft = Offset(
                            centre.x - measured.size.width / 2f,
                            centre.y - measured.size.height / 2f,
                        ),
                    )
                }
                Text(
                    text = scoreName(key),
                    style = ai.pazl.alma.ui.theme.AlmaTheme.type.meta,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                )
            }
        }
    }
}
