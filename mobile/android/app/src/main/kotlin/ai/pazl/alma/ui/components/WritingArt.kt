package ai.pazl.alma.ui.components

import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.ui.theme.AlmaPalette
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.android.awaitFrame
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * What the screen does while Alma writes — one drawing per system, alive.
 * The Android half of the iOS `WritingArt`; the two are the same eight
 * drawings in the same hairline-gold language, because a person who owns both
 * phones is watching one product.
 */
@Composable
fun WritingArt(system: String, modifier: Modifier = Modifier) {
    val t by produceState(0f) {
        val start = awaitFrame()
        while (true) {
            val now = awaitFrame()
            value = ((now - start) / 1e9).toFloat()
        }
    }

    Canvas(modifier.size(240.dp).clearAndSetSemantics { }) {
        val c = Offset(size.width / 2f, size.height / 2f)
        val r = min(size.width, size.height) / 2f
        field(c, r, t, system)
        when (system) {
            AlmaSystem.NATAL -> natal(c, r, t)
            AlmaSystem.NUMEROLOGY -> numerology(c, r, t)
            AlmaSystem.BIRTH_CARD -> birthCard(c, r, t)
            AlmaSystem.TRANSITS -> transits(c, r, t)
            AlmaSystem.SOLAR_RETURN -> solarReturn(c, r, t)
            AlmaSystem.COMPATIBILITY -> compatibility(c, r, t)
            AlmaSystem.ASTROCARTOGRAPHY -> astrocartography(c, r, t)
            else -> synthesis(c, r, t)
        }
    }
}

/* ── shared vocabulary ─────────────────────────────────────────────────── */

private fun DrawScope.ring(c: Offset, radius: Float, alpha: Float, width: Float = 1f) {
    drawCircle(AlmaPalette.Gold.copy(alpha = alpha), radius, c, style = Stroke(width))
}

private fun at(c: Offset, radius: Float, angle: Float): Offset =
    Offset(c.x + radius * cos(angle), c.y + radius * sin(angle))

private fun DrawScope.star(p: Offset, size: Float, glow: Float) {
    drawCircle(
        brush = Brush.radialGradient(
            listOf(AlmaPalette.GoldBright.copy(alpha = 0.35f * glow), Color.Transparent),
            center = p, radius = size * 2.2f,
        ),
        radius = size * 2.2f, center = p,
    )
    drawCircle(AlmaPalette.StarFill.copy(alpha = glow), size, p)
}

/**
 * The field every drawing sits in: twinkling motes, a dashed outer orbit
 * turning one way and a fine tick-ring turning the other — depth, shared.
 */
private fun DrawScope.field(c: Offset, r: Float, t: Float, system: String) {
    var seed = 1469598103934665603UL
    for (b in system.encodeToByteArray()) seed = (seed xor b.toULong()) * 1099511628211UL
    repeat(16) { i ->
        seed = seed * 6364136223846793005UL + 1442695040888963407UL
        val a = (seed % 6283UL).toFloat() / 1000f
        seed = seed * 6364136223846793005UL + 1442695040888963407UL
        val rad = r * (0.15f + (seed % 1000UL).toFloat() / 1000f * 0.95f)
        val p = at(c, rad, a)
        val tw = 0.25f + 0.55f * abs(sin(t * (0.6f + (i % 5) * 0.23f) + i))
        drawCircle(AlmaPalette.StarFill.copy(alpha = tw * 0.6f), 1f * density, p)
    }
    drawCircle(
        AlmaPalette.Gold.copy(alpha = 0.22f), r, c,
        style = Stroke(
            1f,
            pathEffect = androidx.compose.ui.graphics.PathEffect.dashPathEffect(
                floatArrayOf(2f * density, 9f * density), t * 6f * density
            ),
        ),
    )
    repeat(60) { i ->
        val a = i * PI.toFloat() / 30f - t * 0.05f
        drawLine(
            AlmaPalette.Gold.copy(alpha = if (i % 5 == 0) 0.28f else 0.14f),
            at(c, r * 0.995f, a),
            at(c, r * (if (i % 5 == 0) 0.955f else 0.975f), a),
            1f,
        )
    }
}

/** The pen: a comet-point sweeping a slow circle under every drawing. */
private fun DrawScope.pen(c: Offset, r: Float, t: Float) {
    val a = t * 0.9f
    val p = at(c, r * 0.97f, a)
    val trail = Path().apply {
        val box = Rect(c - Offset(r * 0.97f, r * 0.97f), Size(r * 1.94f, r * 1.94f))
        arcTo(box, Math.toDegrees((a - 0.9f).toDouble()).toFloat(), Math.toDegrees(0.9).toFloat(), true)
    }
    drawPath(trail, AlmaPalette.GoldBright.copy(alpha = 0.35f), style = Stroke(1.4f))
    star(p, 2.4f * density, 1f)
}

/* ── the eight ─────────────────────────────────────────────────────────── */

private fun DrawScope.natal(c: Offset, r: Float, t: Float) {
    ring(c, r * 0.96f, 0.5f)
    ring(c, r * 0.78f, 0.3f)
    repeat(12) { i ->
        val a = i * PI.toFloat() / 6f
        drawLine(AlmaPalette.Gold.copy(alpha = 0.28f), at(c, r * 0.78f, a), at(c, r * 0.96f, a), 1f)
    }
    val speeds = floatArrayOf(0.35f, 0.22f, 0.5f, 0.16f, 0.28f)
    val radii = floatArrayOf(0.62f, 0.5f, 0.68f, 0.4f, 0.56f)
    val points = Array(5) { i -> at(c, r * radii[i], t * speeds[i] + i * 1.7f) }
    points.forEachIndexed { i, p -> star(p, (2.6f + (i % 3)) * density, 0.9f) }
    for (i in points.indices) for (j in i + 1 until points.size) {
        val diff = abs(((t * speeds[i] + i * 1.7f) - (t * speeds[j] + j * 1.7f)).mod(2f * PI.toFloat()))
        val third = 2f * PI.toFloat() / 3f
        val near = min(abs(diff - third), abs(diff - 2f * PI.toFloat() + third))
        val glow = (1f - near / 0.35f).coerceAtLeast(0f)
        if (glow > 0f) drawLine(AlmaPalette.GoldBright.copy(alpha = 0.5f * glow), points[i], points[j], 1f)
    }
    pen(c, r, t)
}

private fun DrawScope.numerology(c: Offset, r: Float, t: Float) {
    ring(c, r * 0.9f, 0.35f)
    // Nine marks orbiting; one at a time pulls to the centre and brightens —
    // digits without glyph-drawing, the same rhythm as iOS.
    val phase = t.mod(9f)
    for (n in 1..9) {
        val a = n * 2f * PI.toFloat() / 9f - PI.toFloat() / 2f + t * 0.1f
        val active = abs(phase - (n - 1)) < 0.8f
        val pull = if (active) 0.35f + 0.25f * abs(sin(t * 2f)) else 0.72f
        star(at(c, r * pull, a), (if (active) 4f else 2f) * density, if (active) 1f else 0.35f)
    }
    star(c, 3f * density, 0.5f + 0.5f * abs(sin(t * 2f)))
    pen(c, r, t)
}

private fun DrawScope.birthCard(c: Offset, r: Float, t: Float) {
    ring(c, r * 0.92f, 0.25f)
    val w = (r * 0.62f * abs(cos(t * 0.8f))).coerceAtLeast(2f)
    val h = r * 0.98f
    drawRoundRect(
        AlmaPalette.Gold.copy(alpha = 0.6f),
        topLeft = Offset(c.x - w / 2f, c.y - h / 2f),
        size = Size(w, h),
        cornerRadius = androidx.compose.ui.geometry.CornerRadius(8f * density),
        style = Stroke(1.2f),
    )
    if (cos(t * 0.8f) > 0.15f) star(c, 4f * density * cos(t * 0.8f), cos(t * 0.8f))
    repeat(4) { i -> star(at(c, r * 0.8f, t * 0.4f + i * PI.toFloat() / 2f), 1.6f * density, 0.6f) }
    pen(c, r, t)
}

private fun DrawScope.transits(c: Offset, r: Float, t: Float) {
    ring(c, r * 0.55f, 0.4f)
    ring(c, r * 0.92f, 0.4f)
    val natalAngles = floatArrayOf(0.4f, 1.9f, 3.6f, 5.1f)
    natalAngles.forEach { star(at(c, r * 0.55f, it), 2.4f * density, 0.7f) }
    repeat(3) { i ->
        val a = t * (0.5f - i * 0.14f) + i * 2.2f
        val p = at(c, r * 0.92f, a)
        star(p, 3f * density, 1f)
        natalAngles.forEach { n ->
            val d = abs((a - n).mod(2f * PI.toFloat()))
            val near = min(d, 2f * PI.toFloat() - d)
            val glow = (1f - near / 0.3f).coerceAtLeast(0f)
            if (glow > 0f)

                drawLine(AlmaPalette.GoldBright.copy(alpha = 0.6f * glow), p, at(c, r * 0.55f, n), 1.2f)
        }
    }
    pen(c, r, t)
}

private fun DrawScope.solarReturn(c: Offset, r: Float, t: Float) {
    val breath = 0.85f + 0.15f * sin(t * 1.4f)
    repeat(12) { i ->
        val a = i * PI.toFloat() / 6f + t * 0.05f
        drawLine(
            AlmaPalette.GoldBright.copy(alpha = 0.5f),
            at(c, r * 0.3f * breath, a),
            at(c, r * (0.42f + 0.05f * sin(t * 1.4f + i)), a),
            1f,
        )
    }
    star(c, 9f * density * breath, 1f)
    ring(c, r * 0.86f, 0.35f)
    val yearly = at(c, r * 0.86f, t * 0.6f - PI.toFloat() / 2f)
    star(yearly, 3f * density, 1f)
}

private fun DrawScope.compatibility(c: Offset, r: Float, t: Float) {
    val spread = r * (0.34f + 0.1f * sin(t * 0.7f))
    val a = t * 0.45f
    val one = at(c, spread, a)
    val two = at(c, spread, a + PI.toFloat())
    ring(one, r * 0.34f, 0.4f)
    ring(two, r * 0.34f, 0.4f)
    star(one, 3.4f * density, 1f)
    star(two, 3.4f * density, 1f)
    val closeness = (1f - (spread - r * 0.24f) / (r * 0.2f)).coerceIn(0f, 1f)
    val thread = Path().apply {
        moveTo(one.x, one.y)
        quadraticTo(c.x, c.y - r * 0.2f, two.x, two.y)
    }
    drawPath(thread, AlmaPalette.GoldBright.copy(alpha = 0.25f + 0.45f * closeness), style = Stroke(1.2f))
    pen(c, r, t)
}

private fun DrawScope.astrocartography(c: Offset, r: Float, t: Float) {
    ring(c, r * 0.9f, 0.5f)
    repeat(5) { i ->
        val phase = (t * 0.12f + i / 5f).mod(1f)
        val w = r * 0.9f * abs(cos(phase * PI.toFloat()))
        drawOval(
            AlmaPalette.Gold.copy(alpha = 0.22f),
            topLeft = Offset(c.x - w, c.y - r * 0.9f),
            size = Size(w * 2f, r * 1.8f),
            style = Stroke(1f),
        )
    }
    floatArrayOf(-0.45f, 0f, 0.45f).forEach { dy ->
        val half = r * 0.9f * sqrt(1f - dy * dy)
        drawLine(
            AlmaPalette.Gold.copy(alpha = 0.18f),
            Offset(c.x - half, c.y + r * 0.9f * dy),
            Offset(c.x + half, c.y + r * 0.9f * dy),
            1f,
        )
    }
    val sweep = (t * 0.25f).mod(2f) - 1f
    val x = c.x + r * 0.9f * sweep
    val half = r * 0.9f * sqrt((1f - sweep * sweep).coerceAtLeast(0f))
    drawLine(AlmaPalette.GoldBright.copy(alpha = 0.7f), Offset(x, c.y - half), Offset(x, c.y + half), 1.4f)
    star(Offset(x, c.y - half * 0.3f), 2.6f * density, 1f)
}

private fun DrawScope.synthesis(c: Offset, r: Float, t: Float) {
    ring(c, r * 0.94f, 0.35f)
    val pulse = (t * 0.5f).mod(1f)
    repeat(8) { i ->
        val a = i * PI.toFloat() / 4f + t * 0.06f
        val rim = at(c, r * 0.94f, a)
        drawLine(AlmaPalette.Gold.copy(alpha = 0.22f), rim, c, 1f)
        star(rim, 2f * density, 0.7f)
        star(at(c, r * 0.94f * (1f - pulse), a), 1.8f * density, (1f - pulse) * 0.9f)
    }
    star(c, (4f + if (pulse > 0.9f) (1f - pulse) * 30f else 0f) * density, 0.6f + 0.4f * sin(t * 2f))
}
