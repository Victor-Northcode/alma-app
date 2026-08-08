package ai.pazl.alma.ui.screens

import ai.pazl.alma.ui.components.breathing
import ai.pazl.alma.ui.theme.AlmaPalette
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
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
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/**
 * The chart itself, drawn — the thing every natal-chart product opens with and
 * this one did not have. The iOS `NatalWheel` on the Compose canvas.
 *
 * **Orientation.** The Ascendant sits at the left, as every printed chart has
 * it, and longitudes increase counter-clockwise. With no birth time there is no
 * Ascendant and no houses; the wheel then opens 0° Aries at the left and simply
 * omits the spokes — a thinner chart, honestly thinner, not a chart with
 * invented walls.
 *
 * **Glyphs are allowed here and nowhere else.** The rest of the app spells
 * planets and signs out in words because a pill on the front page is read as
 * text. A wheel is a diagram: the glyph *is* the notation of the diagram, and
 * the words live in the placement list directly underneath.
 *
 * **It draws itself, once.** The first two seconds are the wheel being
 * constructed in the order an astrologer would draw one — rings, signs,
 * houses, planets, aspects — the same ceremony `AlmaLaunch` opens with. The
 * `Animatable` settles at 1 and never runs again, so the settled wheel costs
 * exactly what the static one did.
 */
@Composable
internal fun NatalWheel(data: JsonObject, modifier: Modifier = Modifier) {
    val measurer = rememberTextMeasurer()
    val progress = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        progress.animateTo(
            targetValue = 1f,
            // Ease-out cubic: the wheel arrives quickly and settles gently.
            animationSpec = tween(durationMillis = 2000, easing = CubicBezierEasing(0.33f, 1f, 0.68f, 1f)),
        )
    }
    Canvas(
        modifier = modifier
            .breathing()
            .fillMaxWidth()
            .aspectRatio(1f)
            // The picture is decoration over the placement list below, which
            // carries the same facts in words a reader can hear.
            .semantics { invisibleToUser() },
    ) {
        drawWheel(data, measurer, progress.value)
    }
}

private val SignGlyphList = listOf(
    "♈︎", "♉︎", "♊︎", "♋︎", "♌︎", "♍︎", "♎︎", "♏︎", "♐︎", "♑︎", "♒︎", "♓︎",
)

private fun DrawScope.drawWheel(data: JsonObject, measurer: TextMeasurer, progress: Float) {
    // Which stretch of the intro this element owns, as its own 0…1.
    fun phase(from: Float, to: Float): Float =
        ((progress - from) / (to - from)).coerceIn(0f, 1f)

    val side = min(size.width, size.height)
    val centre = Offset(size.width / 2f, size.height / 2f)
    val outer = side * 0.48f
    val signBand = side * 0.40f
    val planetRing = side * 0.31f
    val aspectRing = side * 0.26f

    val ascendant = data.obj("angles")?.number("ascendant")

    // Screen angle for an ecliptic longitude: the Ascendant (or 0° Aries) on
    // the left, the zodiac running counter-clockwise.
    fun angle(longitude: Double): Double =
        (180.0 - (longitude - (ascendant ?: 0.0))) * PI / 180.0

    fun point(longitude: Double, radius: Float): Offset {
        val a = angle(longitude)
        return Offset(
            centre.x + radius * cos(a).toFloat(),
            centre.y + radius * sin(a).toFloat(),
        )
    }

    fun glyphAt(text: String, at: Offset, sizeSp: Float, color: androidx.compose.ui.graphics.Color) {
        val measured = measurer.measure(text, TextStyle(fontSize = sizeSp.sp, color = color))
        drawText(
            measured,
            topLeft = Offset(
                at.x - measured.size.width / 2f,
                at.y - measured.size.height / 2f,
            ),
        )
    }

    // A line growing from its start toward its end as `grown` goes 0…1.
    fun growingLine(
        start: Offset,
        end: Offset,
        grown: Float,
        color: androidx.compose.ui.graphics.Color,
        strokeWidth: Float,
    ) {
        if (grown <= 0f) return
        drawLine(
            color = color,
            start = start,
            end = Offset(
                start.x + (end.x - start.x) * grown,
                start.y + (end.y - start.y) * grown,
            ),
            strokeWidth = strokeWidth,
        )
    }

    // ── the rings — each sweeps itself closed ──
    val ringSweep = phase(0f, 0.35f)
    for (radius in listOf(outer, signBand)) {
        drawArc(
            color = AlmaPalette.Gold.copy(alpha = 0.45f),
            startAngle = 180f,
            sweepAngle = 360f * ringSweep,
            useCenter = false,
            topLeft = Offset(centre.x - radius, centre.y - radius),
            size = Size(radius * 2f, radius * 2f),
            style = Stroke(width = 1f),
        )
    }
    drawArc(
        color = AlmaPalette.Gold.copy(alpha = 0.18f),
        startAngle = 180f,
        sweepAngle = 360f * ringSweep,
        useCenter = false,
        topLeft = Offset(centre.x - aspectRing, centre.y - aspectRing),
        size = Size(aspectRing * 2f, aspectRing * 2f),
        style = Stroke(width = 1f),
    )

    // ── the twelve signs, lighting up around the wheel ──
    for (index in 0 until 12) {
        val lit = phase(0.20f + index * 0.02f, 0.40f + index * 0.02f)
        if (lit <= 0f) continue
        val start = index * 30.0
        drawLine(
            color = AlmaPalette.Gold.copy(alpha = 0.35f * lit),
            start = point(start, signBand),
            end = point(start, outer),
            strokeWidth = 1f,
        )
        glyphAt(
            SignGlyphList[index],
            point(start + 15.0, (outer + signBand) / 2f),
            sizeSp = side * 0.045f / density,
            color = AlmaPalette.GoldBright.copy(alpha = 0.8f * lit),
        )
    }

    // ── the houses, when the horizon exists — spokes grow outward ──
    val houses = data.array("houses").orEmpty().filterIsInstance<JsonObject>()
    if (ascendant != null && houses.isNotEmpty()) {
        val grown = phase(0.40f, 0.65f)
        if (grown > 0f) {
            for (house in houses) {
                val cusp = house.number("cusp") ?: continue
                val number = house.int("number") ?: continue
                // The horizon and the meridian carry more weight than the
                // intermediate cusps, exactly as a printed chart draws them.
                val cardinal = number in listOf(1, 4, 7, 10)
                growingLine(
                    start = point(cusp, aspectRing),
                    end = point(cusp, signBand),
                    grown = grown,
                    color = AlmaPalette.Gold.copy(alpha = (if (cardinal) 0.5f else 0.22f) * grown),
                    strokeWidth = if (cardinal) 1.4f else 1f,
                )
                // The house number, just inside its own cusp.
                val next = houses.firstOrNull { it.int("number") == number % 12 + 1 }
                val nextCusp = next?.number("cusp")
                if (nextCusp != null) {
                    var span = nextCusp - cusp
                    if (span < 0) span += 360.0
                    glyphAt(
                        number.toString(),
                        point(cusp + span / 2, aspectRing * 0.9f),
                        sizeSp = side * 0.028f / density,
                        color = AlmaPalette.Muted3.copy(alpha = grown),
                    )
                }
            }
        }
    }

    // ── the bodies — each planet takes its seat in zodiac order ──
    data class Body(val name: String, val glyph: String, val longitude: Double)
    val placements = data.obj("placements")
    val bodies = placements?.keys.orEmpty().mapNotNull { name ->
        val placement = placements?.obj(name) ?: return@mapNotNull null
        val longitude = placement.number("longitude") ?: return@mapNotNull null
        val glyph = placement.text("glyph") ?: return@mapNotNull null
        Body(name, glyph, longitude)
    }.sortedBy { it.longitude }

    // Nudge glyphs apart when two bodies sit within a few degrees — a stellium
    // drawn honestly is a smudge, and a smudge reads as a rendering bug rather
    // than as three planets together.
    val drawn = mutableListOf<Double>()
    val step = if (bodies.size > 1) 0.25f / (bodies.size - 1) else 0f
    for ((order, body) in bodies.withIndex()) {
        val close = drawn.count {
            abs((it - body.longitude + 180.0).mod(360.0) - 180.0) < 6.0
        }
        drawn.add(body.longitude)

        val seated = phase(0.55f + order * step, 0.70f + order * step)
        if (seated <= 0f) continue
        val radius = planetRing - close * side * 0.045f

        drawLine(
            color = AlmaPalette.StarFill.copy(alpha = 0.8f * seated),
            start = point(body.longitude, signBand),
            end = point(body.longitude, signBand - side * 0.015f),
            strokeWidth = 1f,
        )
        glyphAt(
            body.glyph,
            point(body.longitude, radius),
            sizeSp = side * 0.042f * (0.6f + 0.4f * seated) / density,
            color = AlmaPalette.StarFill.copy(alpha = seated),
        )
    }

    // ── the aspects, major only — the web across the middle, last ──
    val woven = phase(0.78f, 1f)
    if (woven > 0f) {
        val positions = bodies.associate { it.name to it.longitude }
        for (aspect in data.array("aspects").orEmpty().filterIsInstance<JsonObject>()) {
            if (aspect.bool("major") != true) continue
            val from = positions[aspect.text("first")] ?: continue
            val to = positions[aspect.text("second")] ?: continue
            val tense = aspect.text("harmony") == "tense"
            growingLine(
                start = point(from, aspectRing),
                end = point(to, aspectRing),
                grown = woven,
                color = if (tense) {
                    AlmaPalette.Disagree.copy(alpha = 0.35f * woven)
                } else {
                    AlmaPalette.Gold.copy(alpha = 0.30f * woven)
                },
                strokeWidth = 1f,
            )
        }
    }
}
