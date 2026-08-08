package ai.pazl.alma.ui.screens

import ai.pazl.alma.ui.components.AlmaPresence
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.rememberReducedMotion
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.State
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.unit.dp
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * The living art that stands over each question.
 *
 * Every scene in the journey is the same three things stacked: celestial art in
 * the middle, a title under it, controls at the bottom, and no boxes anywhere.
 * The art is what makes each question feel like a different room, and it is
 * *drawn* — the web app's scenes are inline SVG with CSS keyframes, and these
 * are the same geometry transcribed onto a `Canvas`, coordinate for coordinate,
 * so that the two products show the same constellation rather than two
 * interpretations of one brief.
 *
 * ## The budget
 *
 * One infinite transition per scene, at most two. Every moving part in a scene
 * reads the same 0→1 ramp at a different rate or phase, which is one
 * invalidation per frame rather than one per element. Nothing here allocates
 * while drawing: the point lists are `remember`ed and the maths is arithmetic.
 *
 * ## Reduced motion
 *
 * Honoured by *not creating the animation*, the way the sky does it. A scene
 * asked to be still subscribes to no frame clock at all, so an idle screen
 * renders zero frames rather than sixty identical ones.
 */

/* ── the shared driver ─────────────────────────────────────────────────── */

/**
 * A 0→1 ramp that repeats forever, or a fixed value when the device has asked
 * for stillness. Linear on purpose: the easing belongs in the drawing, where it
 * can differ per element, rather than in the driver, where it could not.
 */
@Composable
private fun ramp(
    durationMillis: Int,
    label: String,
    repeatMode: RepeatMode = RepeatMode.Restart,
    still: Float = 0f,
): State<Float> {
    if (rememberReducedMotion()) return remember { mutableFloatStateOf(still) }
    return rememberInfiniteTransition(label = label).animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis, easing = LinearEasing),
            repeatMode = repeatMode,
        ),
        label = label,
    )
}

/**
 * A one-shot 0→1 that runs once when the scene appears — the `dash` keyframe
 * that draws a constellation on. Still devices get the finished line, because
 * the drawn-on line is the *content* and only the drawing of it is decoration.
 */
@Composable
private fun drawOn(durationMillis: Int, label: String): Float {
    if (rememberReducedMotion()) return 1f
    var started by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { started = true }
    val progress by animateFloatAsState(
        targetValue = if (started) 1f else 0f,
        animationSpec = tween(durationMillis, easing = LinearEasing),
        label = label,
    )
    return progress
}

/**
 * Draw in the SVG's own coordinates, centred and scaled to whatever box the
 * scene was given. Transcribing 320×290 of hand-placed stars is only sane if the
 * numbers stay the numbers.
 */
private inline fun DrawScope.inViewBox(box: Float, body: DrawScope.() -> Unit) {
    val unit = size.minDimension / box
    translate(
        left = (size.width - box * unit) / 2f,
        top = (size.height - box * unit) / 2f,
    ) {
        scale(scaleX = unit, scaleY = unit, pivot = Offset.Zero) { body() }
    }
}

/** Twinkle: 0.25 → 1 → 0.25 on a sine, the `twinkle` keyframe exactly. */
private fun twinkle(phase: Float, offset: Float, floor: Float = 0.4f): Float {
    val t = (phase + offset) % 1f
    return floor + (1f - floor) * (0.5f + 0.5f * sin(t * TAU - HALF_PI))
}

/**
 * A polyline drawn to [progress] of its total length.
 *
 * This is what `stroke-dasharray` + an animated `stroke-dashoffset` does in the
 * web app. Doing it by length rather than by segment count matters: the segments
 * of a constellation are wildly uneven, and animating per segment makes the
 * short ones snap while the long ones crawl.
 */
private fun DrawScope.drawConstellation(
    points: List<Offset>,
    progress: Float,
    colour: Color,
    alpha: Float,
    width: Float,
) {
    if (progress <= 0f || points.size < 2) return

    // Two passes with indices rather than `zipWithNext`, because this runs
    // inside a draw: the tidy version allocates two lists a frame for a shape
    // with six segments in it.
    var total = 0f
    for (index in 0 until points.lastIndex) {
        total += hypot(points[index + 1].x - points[index].x, points[index + 1].y - points[index].y)
    }

    var remaining = total * progress
    for (index in 0 until points.lastIndex) {
        if (remaining <= 0f) return
        val from = points[index]
        val to = points[index + 1]
        val length = hypot(to.x - from.x, to.y - from.y)
        val share = if (length <= 0f) 1f else (remaining / length).coerceAtMost(1f)
        drawLine(
            color = colour,
            start = from,
            end = Offset(from.x + (to.x - from.x) * share, from.y + (to.y - from.y) * share),
            strokeWidth = width,
            alpha = alpha,
            cap = StrokeCap.Round,
        )
        remaining -= length
    }
}

private fun DrawScope.ring(
    centre: Offset,
    radius: Float,
    colour: Color,
    alpha: Float,
    width: Float = 0.9f,
    dash: FloatArray? = null,
) {
    drawCircle(
        color = colour,
        radius = radius,
        center = centre,
        alpha = alpha,
        style = Stroke(
            width = width,
            pathEffect = dash?.let { PathEffect.dashPathEffect(it, 0f) },
        ),
    )
}

/* ══ I · what's loudest ════════════════════════════════════════════════ */

/**
 * A constellation drawing itself: five stars joined, then a second line back
 * through a sixth, with one node ringed. The nodes twinkle out of phase forever;
 * the lines draw once and stay.
 */
@Composable
fun IntentArt(modifier: Modifier = Modifier) {
    val nodes = remember {
        listOf(
            Offset(54f, 214f) to 3.6f,
            Offset(112f, 128f) to 4.8f,
            Offset(182f, 160f) to 3.2f,
            Offset(232f, 66f) to 5.4f,
            Offset(286f, 112f) to 3.4f,
            Offset(142f, 236f) to 4.0f,
        )
    }
    val spine = remember { nodes.take(5).map { it.first } }
    val branch = remember { listOf(nodes[1].first, nodes[5].first, nodes[3].first) }

    val first = drawOn(3_400, "spine")
    val second = drawOn(4_200, "branch")
    val glimmer by ramp(4_400, "glimmer")

    Canvas(modifier.fillMaxSize().clearAndSetSemantics { }) {
        inViewBox(320f) {
            drawConstellation(spine, first, AlmaPalette.Gold, 0.5f, 1.1f)
            drawConstellation(branch, second, AlmaPalette.Gold, 0.26f, 1.1f)
            nodes.forEachIndexed { index, (centre, radius) ->
                drawCircle(
                    color = AlmaPalette.StarFill,
                    radius = radius,
                    center = centre,
                    alpha = twinkle(glimmer, index * 0.17f),
                )
            }
            // The brightest star wears the ring: the question has one answer per
            // person and the scene says so before the buttons do.
            ring(nodes[3].first, 17f, AlmaPalette.GoldBright, 0.26f)
        }
    }
}

/* ══ II · a name ═══════════════════════════════════════════════════════ */

/** Alma's light, with something small in orbit around it. */
@Composable
fun NameArt(modifier: Modifier = Modifier) {
    val orbit by ramp(18_000, "orbit")
    val breath by ramp(8_000, "halo", RepeatMode.Reverse, still = 0.5f)

    Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize().clearAndSetSemantics { }) {
            inViewBox(280f) {
                val centre = Offset(140f, 140f)
                val halo = 110f * (0.96f + 0.08f * breath)
                drawCircle(
                    brush = Brush.radialGradient(
                        colorStops = arrayOf(
                            0.00f to AlmaPalette.StarFill.copy(alpha = 0.14f),
                            0.68f to Color.Transparent,
                            1.00f to Color.Transparent,
                        ),
                        center = centre,
                        radius = halo,
                    ),
                    radius = halo,
                    center = centre,
                )
                ring(centre, 92f, AlmaPalette.Gold, 0.34f)
                ring(centre, 118f, AlmaPalette.GoldDeep, 0.30f, dash = floatArrayOf(2f, 6f))

                val angle = orbit * TAU
                drawCircle(
                    color = AlmaPalette.StarFill,
                    radius = 3.4f,
                    center = Offset(centre.x + 92f * cos(angle), centre.y + 92f * sin(angle)),
                )
            }
        }
        // Never a face and never a photograph — the presence is the light itself.
        AlmaPresence(size = 56.dp, ring = false)
    }
}

/* ══ III · a date ══════════════════════════════════════════════════════ */

/** A year, as one slow circuit. The dot takes three minutes to come back. */
@Composable
fun DateArt(modifier: Modifier = Modifier) {
    val year by ramp(180_000, "year")

    Canvas(modifier.fillMaxSize().clearAndSetSemantics { }) {
        inViewBox(230f) {
            val centre = Offset(115f, 115f)
            ring(centre, 106f, AlmaPalette.Gold, 0.45f)
            ring(centre, 86f, AlmaPalette.GoldDeep, 0.30f, dash = floatArrayOf(2f, 5f))
            val angle = year * TAU - HALF_PI
            drawCircle(
                color = AlmaPalette.StarFill,
                radius = 4f,
                center = Offset(centre.x + 95f * cos(angle), centre.y + 95f * sin(angle)),
            )
            drawCircle(AlmaPalette.StarFill, radius = 4.6f, center = centre)
        }
    }
}

/* ══ IV · a time ═══════════════════════════════════════════════════════ */

/**
 * A clock running at real speed. The long hand takes a minute and the short one
 * takes twelve, which is the point: this screen is asking for a *minute*, and a
 * dial that sweeps in three seconds would be asking for a mood.
 */
@Composable
fun TimeArt(modifier: Modifier = Modifier) {
    val minute by ramp(60_000, "minute")
    val hour by ramp(720_000, "hour")

    Canvas(modifier.fillMaxSize().clearAndSetSemantics { }) {
        inViewBox(230f) {
            val centre = Offset(115f, 115f)
            ring(centre, 106f, AlmaPalette.Gold, 0.45f)
            ring(centre, 86f, AlmaPalette.GoldDeep, 0.30f, dash = floatArrayOf(2f, 5f))

            // Four marks, not twelve. Twelve at this size is a texture.
            repeat(4) { quarter ->
                val angle = quarter * (TAU / 4f) - HALF_PI
                drawLine(
                    color = AlmaPalette.Gold,
                    start = Offset(centre.x + 106f * cos(angle), centre.y + 106f * sin(angle)),
                    end = Offset(centre.x + 92f * cos(angle), centre.y + 92f * sin(angle)),
                    strokeWidth = 1f,
                    alpha = 0.55f,
                )
            }

            val minuteAngle = minute * TAU - HALF_PI
            drawLine(
                color = AlmaPalette.StarFill,
                start = centre,
                end = Offset(centre.x + 77f * cos(minuteAngle), centre.y + 77f * sin(minuteAngle)),
                strokeWidth = 1.4f,
                alpha = 0.9f,
                cap = StrokeCap.Round,
            )
            val hourAngle = hour * TAU - HALF_PI
            drawLine(
                color = AlmaPalette.Gold,
                start = centre,
                end = Offset(centre.x + 56f * cos(hourAngle), centre.y + 56f * sin(hourAngle)),
                strokeWidth = 1.8f,
                alpha = 0.8f,
                cap = StrokeCap.Round,
            )
            drawCircle(AlmaPalette.StarFill, radius = 4.6f, center = centre)
        }
    }
}

/* ══ V · a place ═══════════════════════════════════════════════════════ */

/**
 * A globe turning, with one place on it rippling.
 *
 * One deliberate departure from the SVG: the web app rotates a *fixed*
 * graticule, which at 250 px in a browser reads as a globe and at 260 dp on a
 * phone reads as a spinning pinwheel. Here the meridians are ellipses whose
 * width is modulated by the rotation instead — the same silhouette, the same
 * two-minute period, and it unmistakably reads as a sphere.
 */
@Composable
fun PlaceArt(modifier: Modifier = Modifier) {
    val spin by ramp(120_000, "spin")
    val ripple by ramp(4_000, "ripple")

    Canvas(modifier.fillMaxSize().clearAndSetSemantics { }) {
        inViewBox(250f) {
            val centre = Offset(125f, 125f)
            val radius = 104f

            ring(centre, radius, AlmaPalette.Gold, 0.50f)

            // Three meridians, 60° apart in longitude. A meridian seen edge-on is
            // a straight line, which is what a zero-width ellipse draws.
            repeat(3) { index ->
                val phase = spin * TAU + index * (PI.toFloat() / 3f)
                // Never quite zero: a stroked oval of no width draws nothing at
                // all, and a meridian that blinks out edge-on is a hole in the
                // globe rather than a meridian.
                val halfWidth = (abs(cos(phase)) * radius).coerceAtLeast(0.5f)
                drawOval(
                    color = AlmaPalette.Gold,
                    topLeft = Offset(centre.x - halfWidth, centre.y - radius),
                    size = Size(halfWidth * 2f, radius * 2f),
                    alpha = 0.28f,
                    style = Stroke(width = 0.9f),
                )
            }

            // Two latitudes and the equator: fixed, because a sphere spinning on
            // its own axis does not move them.
            Latitudes.forEach { band ->
                val y = band * radius
                val halfWidth = radius * sqrt(1f - band * band)
                val squash = radius * 0.22f
                drawOval(
                    color = AlmaPalette.Gold,
                    topLeft = Offset(centre.x - halfWidth, centre.y + y - squash),
                    size = Size(halfWidth * 2f, squash * 2f),
                    alpha = 0.22f,
                    style = Stroke(width = 0.9f),
                )
            }

            val pin = Offset(152f, 86f)
            drawCircle(AlmaPalette.StarFill, radius = 5.6f, center = pin)
            // Out and gone, once every four seconds. A ring that never fades is
            // a target; a ring that arrives and leaves is a signal.
            val out = 14f + ripple * 22f
            drawCircle(
                color = AlmaPalette.StarFill,
                radius = out,
                center = pin,
                alpha = 0.4f * (1f - ripple),
                style = Stroke(width = 0.9f),
            )
        }
    }
}

/* ══ VI · the ceremony ═════════════════════════════════════════════════ */

/**
 * The wheel: three rings, the axes, an inscribed hexagon, and one triangle drawn
 * on over three seconds — an aspect pattern being found rather than displayed.
 *
 * This is the busiest thing in the product and the only place that is allowed to
 * be. It is on screen for nine seconds, once, while the birth is being saved
 * under it, and its whole job is to make a network round trip feel like an act.
 */
@Composable
fun CeremonyArt(modifier: Modifier = Modifier) {
    val turn by ramp(40_000, "wheel")
    val aspect = drawOn(3_000, "aspect")
    val glimmer by ramp(4_000, "nodes")

    val triangle = remember {
        listOf(Offset(74f, 66f), Offset(172f, 158f), Offset(96f, 178f), Offset(74f, 66f))
    }
    // Built once rather than per frame: the wheel is fixed and only the bodies
    // on it move.
    val hexagon = remember {
        List(7) { index ->
            val angle = index * (TAU / 6f) - HALF_PI
            Offset(120f + 86f * cos(angle), 120f + 86f * sin(angle))
        }
    }

    Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize().clearAndSetSemantics { }) {
            inViewBox(240f) {
                val centre = Offset(120f, 120f)
                ring(centre, 112f, AlmaPalette.Gold, 0.55f)
                ring(centre, 86f, AlmaPalette.GoldDeep, 0.50f, dash = floatArrayOf(2f, 4f))
                ring(centre, 44f, AlmaPalette.Gold, 0.35f)

                // The axes: vertical, horizontal and both diagonals.
                repeat(4) { index ->
                    val angle = index * (PI.toFloat() / 4f)
                    drawLine(
                        color = AlmaPalette.Gold,
                        start = Offset(centre.x - 112f * cos(angle), centre.y - 112f * sin(angle)),
                        end = Offset(centre.x + 112f * cos(angle), centre.y + 112f * sin(angle)),
                        strokeWidth = 0.7f,
                        alpha = 0.4f,
                    )
                }

                // The hexagon inscribed at 86, vertex uppermost.
                drawConstellation(hexagon, 1f, AlmaPalette.Gold, 0.4f, 0.7f)

                drawConstellation(triangle, aspect, AlmaPalette.GoldBright, 0.85f, 1f)
                triangle.take(3).forEachIndexed { index, point ->
                    drawCircle(
                        color = AlmaPalette.StarFill,
                        radius = 4f,
                        center = point,
                        alpha = twinkle(glimmer, index * 0.3f, floor = 0.55f),
                    )
                }

                // Two bodies on a slow circuit, half a turn apart.
                rotate(degrees = turn * 360f, pivot = centre) {
                    drawCircle(AlmaPalette.GoldBright, 3f, Offset(centre.x, centre.y - 98f))
                    drawCircle(AlmaPalette.Gold, 2.4f, Offset(centre.x, centre.y + 98f))
                }
            }
        }
        AlmaPresence(size = 56.dp, ring = false)
    }
}

private const val TAU = (2.0 * PI).toFloat()
private const val HALF_PI = (PI / 2.0).toFloat()

/** Where the globe's latitude circles sit, as a fraction of its radius. */
private val Latitudes = listOf(-0.5f, 0f, 0.5f)
