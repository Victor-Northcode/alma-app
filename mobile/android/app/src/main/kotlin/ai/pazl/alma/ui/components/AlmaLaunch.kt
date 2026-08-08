package ai.pazl.alma.ui.components

import ai.pazl.alma.R
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaFonts
import ai.pazl.alma.ui.theme.AlmaPalette
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathMeasure
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import androidx.compose.ui.util.lerp
import android.provider.Settings
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.sin
import kotlinx.coroutines.android.awaitFrame

/**
 * The first two and a half seconds: a star chart drawing itself, then folding
 * into the mark. The iOS `AlmaLaunch`, on Compose.
 *
 * One clock, five overlapping movements, 2.8 seconds: the field of stars fades
 * up, six nodes light one after another, the lines between them draw
 * themselves, one comet crosses as the chart contracts, and the mark blooms
 * where the brightest node was — then the wordmark, Alma's own light, and the
 * quietest possible progress hairline.
 *
 * It overlaps on purpose. Five things each starting when the last has finished
 * is a slideshow; five whose curves cross is a single movement, and that
 * difference is most of what "expensive" means in motion.
 *
 * **The mark does not spin.** `AlmaStar`'s own documentation forbids it, and a
 * rotating four-pointed sparkle is the exact cliché the mark was drawn to
 * avoid. It blooms in place, out of the chart it belongs to.
 *
 * [done] is called once the arrival has finished *and* [ready] is true. Both,
 * not either: leaving early is the jump cut this replaces, and when the session
 * is genuinely slower the screen simply stays.
 */
@Composable
fun AlmaLaunch(ready: Boolean, done: () -> Unit) {
    val context = LocalContext.current
    // The platform's "remove animations" accessibility setting zeroes the
    // animator scale. The same picture, finished, with nothing moving —
    // removing the screen entirely would not be an accommodation, it would be
    // the flash this exists to prevent.
    val still = remember {
        Settings.Global.getFloat(
            context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f
        ) == 0f
    }

    // The one clock every movement reads. Stops advancing shortly after the
    // run so a slow backend does not keep a whole screen invalidating at 120Hz
    // for nothing — `AlmaPresence` breathes on its own animation.
    val t by produceState(if (still) Runtime else 0f) {
        if (still) return@produceState
        val start = awaitFrame()
        while (value < Runtime + 0.1f) {
            val now = awaitFrame()
            value = ((now - start) / 1e9).toFloat()
        }
    }

    val dwelt = t >= Runtime
    LaunchedEffect(dwelt, ready) {
        if (dwelt && ready) done()
    }

    val loading = stringResource(R.string.state_loading)
    NightSky(config = SkyConfig(seed = 0x414C, motes = 0, comet = false)) {
        Box(
            Modifier
                .fillMaxSize()
                .alpha(if (still) 1f else eased(0f, 0.9f, t))
                .clearAndSetSemantics { contentDescription = loading },
            contentAlignment = Alignment.Center,
        ) {
            // How far the chart has folded away, and how far the mark has come
            // up — derived from the one clock so the two can never drift apart.
            val fold = eased(1.55f, 2.20f, t)
            val bloom = eased(1.70f, 2.45f, t)
            val word = eased(2.00f, 2.55f, t)

            StarChartCanvas(
                lines = eased(0.30f, 1.70f, t),
                nodes = eased(0.20f, 1.55f, t),
                comet = eased(1.50f, 2.30f, t),
                modifier = Modifier
                    .size(300.dp)
                    // Almost all the way out, not most of the way: at less the
                    // chart stays legible behind the mark and the two read as
                    // clutter rather than as one resolving into the other.
                    .alpha(1f - fold * 0.97f)
                    .scale(1.04f - eased(0f, 0.9f, t) * 0.04f - fold * 0.10f),
            )

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Box(Modifier.alpha(bloom).scale(0.72f + bloom * 0.28f)) {
                    AlmaStar(size = 46.dp)
                }

                Spacer(Modifier.height(24.dp))
                Text(
                    text = "ALMA",
                    style = TextStyle(
                        fontFamily = AlmaFonts.Sans,
                        fontSize = 15.sp,
                        letterSpacing = 0.45.em,
                        color = AlmaPalette.Parchment.copy(alpha = 0.9f),
                    ),
                    modifier = Modifier.alpha(word),
                )

                // The part that says "loading": Alma's own light, breathing —
                // the one loop the brand allows, because stillness here reads
                // as a hang — and under it a hairline that fills over the run.
                Spacer(Modifier.height(24.dp))
                Box(Modifier.alpha(word * 0.9f)) {
                    AlmaPresence(size = 18.dp, ring = false)
                }
                Spacer(Modifier.height(16.dp))
                Canvas(Modifier.size(width = 84.dp, height = 1.dp).alpha(eased(0.55f, 1.20f, t))) {
                    drawLine(
                        color = AlmaPalette.Gold.copy(alpha = 0.16f),
                        start = Offset(0f, 0f),
                        end = Offset(size.width, 0f),
                        strokeWidth = size.height,
                        cap = StrokeCap.Round,
                    )
                    drawLine(
                        color = AlmaPalette.GoldBright.copy(alpha = 0.75f),
                        start = Offset(0f, 0f),
                        end = Offset(size.width * min(t / Runtime, 1f), 0f),
                        strokeWidth = size.height,
                        cap = StrokeCap.Round,
                    )
                }
            }
        }
    }
}

/** The whole arrival, and the floor on how long this screen is shown. */
private const val Runtime = 2.8f

/**
 * A value that goes 0 → 1 between two moments, on an ease-out cubic.
 *
 * Ease-out rather than linear everywhere: a light that arrives at a constant
 * rate reads as a progress bar. One curve for every element is what makes five
 * movements look like one hand.
 */
private fun eased(from: Float, to: Float, at: Float): Float {
    val raw = ((at - from) / (to - from)).coerceIn(0f, 1f)
    return 1f - (1f - raw).pow(3)
}

/**
 * Six stars, four lines between them, and one comet.
 *
 * **Not a real constellation, deliberately.** A recognisable Orion on the
 * launch screen is a claim about the sky tonight, and this screen has no chart
 * to make it from — the whole product is built on not saying things it has not
 * calculated.
 */
@Composable
private fun StarChartCanvas(
    lines: Float,
    nodes: Float,
    comet: Float,
    modifier: Modifier = Modifier,
) {
    // On a 300-point grid, so the coordinates read as a drawing.
    val points = remember {
        listOf(
            Offset(48f, 196f) to 3.2f, Offset(104f, 118f) to 4.6f,
            Offset(168f, 152f) to 3.0f, Offset(214f, 58f) to 5.2f,
            Offset(268f, 104f) to 3.4f, Offset(132f, 224f) to 3.8f,
        )
    }
    val spine = remember {
        Path().apply {
            moveTo(48f, 196f); lineTo(104f, 118f); lineTo(168f, 152f)
            lineTo(214f, 58f); lineTo(268f, 104f)
        }
    }
    val branch = remember {
        Path().apply {
            moveTo(104f, 118f); lineTo(132f, 224f); lineTo(214f, 58f)
        }
    }
    val spineMeasure = remember { PathMeasure().apply { setPath(spine, false) } }
    val branchMeasure = remember { PathMeasure().apply { setPath(branch, false) } }
    val trimmed = remember { Path() }

    Canvas(modifier) {
        val unit = size.minDimension / 300f
        fun at(p: Offset) = Offset(p.x * unit, p.y * unit)

        fun draw(measure: PathMeasure, share: Float, color: Color) {
            if (share <= 0f) return
            trimmed.reset()
            measure.getSegment(0f, measure.length * share, trimmed, true)
            scale(unit, unit, pivot = Offset.Zero) {
                drawPath(trimmed, color, style = Stroke(width = 1f / unit))
            }
        }
        draw(spineMeasure, lines, AlmaPalette.Gold.copy(alpha = 0.5f))
        // A quarter-run behind the spine, so the branch is still being drawn
        // when the spine arrives at its last node.
        draw(branchMeasure, (lines * 1.3f - 0.3f).coerceIn(0f, 1f), AlmaPalette.Gold.copy(alpha = 0.24f))

        points.forEachIndexed { index, (p, r) ->
            // Each node opens in its own slice of the run, so they light
            // *along* the chart rather than together.
            val share = index / points.size.toFloat()
            val lit = ((nodes - share * 0.55f) / 0.45f).coerceIn(0f, 1f)
            if (lit <= 0f) return@forEachIndexed
            val centre = at(p)
            val radius = r * unit * (0.4f + lit * 0.6f)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        AlmaPalette.GoldBright.copy(alpha = 0.5f * lit),
                        Color.Transparent,
                    ),
                    center = centre,
                    radius = radius * 3.2f,
                ),
                radius = radius * 3.2f,
                center = centre,
            )
            drawCircle(
                color = AlmaPalette.StarFill.copy(alpha = lit),
                radius = radius,
                center = centre,
            )
        }

        // The ring around the brightest node — the place the mark blooms from,
        // marked before it is used, and closing as the chart lights.
        drawCircle(
            color = AlmaPalette.GoldBright.copy(alpha = 0.22f * nodes),
            radius = (15f + (1f - nodes) * 7f) * unit,
            center = at(Offset(214f, 58f)),
            style = Stroke(width = 1f),
        )

        if (comet > 0f && comet < 1f) {
            // Brightest at the middle of its crossing rather than at the
            // edges, so it is never seen to appear or to stop.
            val head = at(
                Offset(
                    lerp(-40f, 340f, comet),
                    lerp(250f, 40f, comet),
                )
            )
            rotate(degrees = 28f, pivot = head) {
                drawLine(
                    brush = Brush.horizontalGradient(
                        colors = listOf(
                            Color.Transparent,
                            AlmaPalette.StarFill.copy(alpha = 0.75f * sin(comet * Math.PI).toFloat()),
                            Color.Transparent,
                        ),
                        startX = head.x - 45f * unit,
                        endX = head.x + 45f * unit,
                    ),
                    start = Offset(head.x - 45f * unit, head.y),
                    end = Offset(head.x + 45f * unit, head.y),
                    strokeWidth = 1.2f * unit,
                    cap = StrokeCap.Round,
                )
            }
        }
    }
}
