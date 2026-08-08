package ai.pazl.alma.ui.components

import ai.pazl.alma.ui.theme.AlmaPalette
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Matrix
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.invisibleToUser
import androidx.compose.ui.semantics.semantics
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/**
 * Tonight's moon, drawn as she actually is — the one ornament on Today.
 * The iOS `MoonMedallion` on the Compose canvas; see that file for the
 * design reasoning. Everything drawn comes from `sky_now`: real illumination,
 * real waxing/waning, one spark per contact perfecting today.
 */
@Composable
fun MoonMedallion(
    illumination: Double,
    waxing: Boolean,
    sparks: List<Boolean>,
    modifier: Modifier = Modifier,
) {
    val progress = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        progress.animateTo(
            targetValue = 1f,
            animationSpec = tween(durationMillis = 1200, easing = CubicBezierEasing(0.33f, 1f, 0.68f, 1f)),
        )
    }
    Canvas(modifier = modifier.breathing().semantics { invisibleToUser() }) {
        fun phase(from: Float, to: Float): Float =
            ((progress.value - from) / (to - from)).coerceIn(0f, 1f)

        val side = min(size.width, size.height)
        val centre = Offset(size.width / 2f, size.height / 2f)
        val ring = side * 0.47f
        val r = side * 0.30f

        // The ring sweeps closed first.
        val sweep = phase(0f, 0.45f)
        drawArc(
            color = AlmaPalette.Gold.copy(alpha = 0.35f),
            startAngle = -90f, sweepAngle = 360f * sweep, useCenter = false,
            topLeft = Offset(centre.x - ring, centre.y - ring),
            size = Size(ring * 2f, ring * 2f),
            style = Stroke(width = 1f),
        )

        // The night side always; the lit limb as wide as the ephemeris says.
        drawCircle(AlmaPalette.Night700.copy(alpha = 0.9f), radius = r, center = centre)
        drawCircle(
            AlmaPalette.Gold.copy(alpha = 0.3f), radius = r, center = centre,
            style = Stroke(width = 0.7f),
        )

        val f = illumination.coerceIn(0.0, 1.0).toFloat() * phase(0.25f, 0.8f)
        if (f > 0.005f) {
            val lit = Path()
            // The bright semicircle…
            lit.arcTo(
                rect = androidx.compose.ui.geometry.Rect(
                    centre.x - r, centre.y - r, centre.x + r, centre.y + r),
                startAngleDegrees = -90f, sweepAngleDegrees = 180f, forceMoveTo = true,
            )
            // …closed by the terminator: the opposite semicircle scaled across.
            // The sign is the optics — below half the shadow bulges into the
            // lit limb and leaves a sliver; above half it leaves a gibbous.
            val terminator = maxOf(0.001f, abs(2f * f - 1f)) * (if (f >= 0.5f) 1f else -1f)
            val back = Path()
            back.arcTo(
                rect = androidx.compose.ui.geometry.Rect(-r, -r, r, r),
                startAngleDegrees = 90f, sweepAngleDegrees = 180f, forceMoveTo = true,
            )
            val squeeze = Matrix()
            squeeze.translate(centre.x, centre.y)
            squeeze.scale(x = terminator, y = 1f)
            back.transform(squeeze)
            lit.addPath(back)
            val oriented = if (waxing) lit else Path().apply {
                addPath(lit)
                val mirror = Matrix()
                mirror.translate(centre.x, centre.y)
                mirror.scale(x = -1f, y = 1f)
                mirror.translate(-centre.x, -centre.y)
                transform(mirror)
            }
            drawPath(oriented, AlmaPalette.StarFill.copy(alpha = 0.92f))
        }

        // One spark per contact perfecting today, seated along the ring.
        for ((index, tense) in sparks.take(6).withIndex()) {
            val pop = phase(0.6f + index * 0.08f, 0.85f + index * 0.08f)
            if (pop <= 0f) continue
            val a = (index * 32f - 52f) * (Math.PI.toFloat() / 180f)
            val at = Offset(centre.x + ring * cos(a), centre.y + ring * sin(a))
            drawCircle(
                color = (if (tense) AlmaPalette.Disagree else AlmaPalette.GoldBright)
                    .copy(alpha = 0.9f * pop),
                radius = side * 0.030f * pop / 2f,
                center = at,
            )
        }
    }
}
