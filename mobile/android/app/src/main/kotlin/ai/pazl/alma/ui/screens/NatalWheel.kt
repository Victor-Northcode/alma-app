package ai.pazl.alma.ui.screens

import ai.pazl.alma.ui.theme.AlmaPalette
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
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
 */
@Composable
internal fun NatalWheel(data: JsonObject, modifier: Modifier = Modifier) {
    val measurer = rememberTextMeasurer()
    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            // The picture is decoration over the placement list below, which
            // carries the same facts in words a reader can hear.
            .semantics { invisibleToUser() },
    ) {
        drawWheel(data, measurer)
    }
}

private val SignGlyphList = listOf(
    "♈︎", "♉︎", "♊︎", "♋︎", "♌︎", "♍︎", "♎︎", "♏︎", "♐︎", "♑︎", "♒︎", "♓︎",
)

private fun DrawScope.drawWheel(data: JsonObject, measurer: TextMeasurer) {
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

    // ── the rings ──
    for (radius in listOf(outer, signBand)) {
        drawCircle(
            color = AlmaPalette.Gold.copy(alpha = 0.45f),
            radius = radius,
            center = centre,
            style = Stroke(width = 1f),
        )
    }
    drawCircle(
        color = AlmaPalette.Gold.copy(alpha = 0.18f),
        radius = aspectRing,
        center = centre,
        style = Stroke(width = 1f),
    )

    // ── the twelve signs ──
    for (index in 0 until 12) {
        val start = index * 30.0
        drawLine(
            color = AlmaPalette.Gold.copy(alpha = 0.35f),
            start = point(start, signBand),
            end = point(start, outer),
            strokeWidth = 1f,
        )
        glyphAt(
            SignGlyphList[index],
            point(start + 15.0, (outer + signBand) / 2f),
            sizeSp = side * 0.045f / density,
            color = AlmaPalette.GoldBright.copy(alpha = 0.8f),
        )
    }

    // ── the houses, when the horizon exists ──
    val houses = data.array("houses").orEmpty().filterIsInstance<JsonObject>()
    if (ascendant != null && houses.isNotEmpty()) {
        for (house in houses) {
            val cusp = house.number("cusp") ?: continue
            val number = house.int("number") ?: continue
            // The horizon and the meridian carry more weight than the
            // intermediate cusps, exactly as a printed chart draws them.
            val cardinal = number in listOf(1, 4, 7, 10)
            drawLine(
                color = AlmaPalette.Gold.copy(alpha = if (cardinal) 0.5f else 0.22f),
                start = point(cusp, aspectRing),
                end = point(cusp, signBand),
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
                    color = AlmaPalette.Muted3,
                )
            }
        }
    }

    // ── the bodies ──
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
    for (body in bodies) {
        val close = drawn.count {
            abs((it - body.longitude + 180.0).mod(360.0) - 180.0) < 6.0
        }
        drawn.add(body.longitude)
        val radius = planetRing - close * side * 0.045f

        drawLine(
            color = AlmaPalette.StarFill.copy(alpha = 0.8f),
            start = point(body.longitude, signBand),
            end = point(body.longitude, signBand - side * 0.015f),
            strokeWidth = 1f,
        )
        glyphAt(
            body.glyph,
            point(body.longitude, radius),
            sizeSp = side * 0.042f / density,
            color = AlmaPalette.StarFill,
        )
    }

    // ── the aspects, major only ──
    val positions = bodies.associate { it.name to it.longitude }
    for (aspect in data.array("aspects").orEmpty().filterIsInstance<JsonObject>()) {
        if (aspect.bool("major") != true) continue
        val from = positions[aspect.text("first")] ?: continue
        val to = positions[aspect.text("second")] ?: continue
        val tense = aspect.text("harmony") == "tense"
        drawLine(
            color = if (tense) {
                AlmaPalette.Disagree.copy(alpha = 0.35f)
            } else {
                AlmaPalette.Gold.copy(alpha = 0.30f)
            },
            start = point(from, aspectRing),
            end = point(to, aspectRing),
            strokeWidth = 1f,
        )
    }
}
