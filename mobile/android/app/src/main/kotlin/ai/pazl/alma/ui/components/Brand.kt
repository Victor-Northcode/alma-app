package ai.pazl.alma.ui.components

import ai.pazl.alma.R
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import ai.pazl.alma.ui.theme.rememberReducedMotion
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp

/**
 * The mark, the lockup and Alma's presence.
 *
 * All three are traced from `src/components/brand/Star.tsx` so that the site
 * and the two stores show one shape. The paths below are the same strings the
 * web component draws, parsed once and cached — a hand-drawn four-pointed star
 * with thick arms and short points, deliberately a little off-axis so it never
 * reads as a generated sparkle.
 *
 * The rules that come with it, from the brand book: never in a circle, never
 * rotated, never used as a bullet, never used as a loading spinner.
 */

/** The 64-unit design grid the paths are drawn on. */
private const val MarkViewport = 64f

private const val MarkBody =
    "M32.4 6.4 Q35.6 22.8 41.2 26.6 Q47 30 57.8 31.9 Q47 34 41 37.4 Q35.4 41 32 57.6 " +
        "Q28.6 41.2 23 37.6 Q17 34.2 6.2 32.1 Q17.2 29.8 23.2 26.4 Q28.8 22.6 32.4 6.4 Z"

private const val MarkInner =
    "M32.2 13 Q34.4 26.6 37.6 29.8 Q34.2 34.8 32 51 Q29.8 34.8 26.6 30 Q30 26.8 32.2 13 Z"

/** How the mark is finished. `Flat` is for anywhere the gradient would not survive. */
enum class StarVariant { Gold, Ink, Flat }

@Composable
fun AlmaStar(
    modifier: Modifier = Modifier,
    size: Dp = 26.dp,
    variant: StarVariant = StarVariant.Gold,
) {
    // Parsing an SVG path is not free and the mark appears on every screen, so
    // it happens once per composition rather than once per frame.
    val body = remember { PathParser().parsePathString(MarkBody).toPath() }
    val inner = remember { PathParser().parsePathString(MarkInner).toPath() }

    Canvas(modifier.size(size).clearAndSetSemantics { }) {
        val unit = this.size.minDimension / MarkViewport
        scale(scaleX = unit, scaleY = unit, pivot = Offset.Zero) {
            when (variant) {
                StarVariant.Flat -> drawPath(body, Color(0xFFE0C077))
                else -> {
                    val brush = if (variant == StarVariant.Ink) InkGradient else AlmaPalette.GoldGradient
                    drawPath(body, brush)
                    drawPath(
                        path = body,
                        color = if (variant == StarVariant.Ink) Color(0xFF4A3A16) else Color(0xFF7A6129),
                        style = Stroke(width = 0.8f, join = StrokeJoin.Round),
                    )
                    drawPath(
                        path = inner,
                        color = if (variant == StarVariant.Ink) Color(0xFF3A2D11) else Color(0xFF8A6F2E),
                        alpha = if (variant == StarVariant.Ink) 0.28f else 0.16f,
                    )
                }
            }
        }
    }
}

private val InkGradient = Brush.linearGradient(
    0.00f to Color(0xFFC2A868),
    0.42f to Color(0xFF94773A),
    1.00f to Color(0xFF5E4B20),
)

/**
 * The lockup: mark then wordmark, tracked out to 0.34 em.
 *
 * The padding after the word is not a mistake and not decoration. Letter
 * spacing in both CSS and Compose is applied *after* the last glyph too, so a
 * word tracked this hard sits visibly left of centre in whatever contains it.
 * The web component compensates with a matching `padding-left`; this does the
 * same with `Arrangement.spacedBy` and an end pad of the same size.
 */
@Composable
fun AlmaWordmark(
    modifier: Modifier = Modifier,
    fontSize: Dp = 19.dp,
    starSize: Dp = Dp(fontSize.value * 1.35f),
) {
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(11.dp),
    ) {
        AlmaStar(size = starSize)
        Text(
            text = "ALMA",
            style = AlmaTheme.type.headingM.copy(
                fontSize = fontSize.value.sp,
                letterSpacing = 0.34.em,
                color = AlmaPalette.InkLight,
            ),
        )
    }
}

/**
 * Alma's presence — the soft light that stands in for a face.
 *
 * Never a photograph, never an avatar with eyes. Two motions, both from the
 * CSS: the light *breathes* on a six-second cycle, and above 56 dp a ring
 * *ripples* outward every eight seconds. Below 56 dp the ring is dropped
 * entirely rather than drawn thinner, because a one-pixel ring at 24 dp is
 * dirt on the screen.
 *
 * Sizes are 96 / 56 / 24 and nothing between; anything else and it stops
 * reading as the same presence at a different distance.
 */
@Composable
fun AlmaPresence(
    modifier: Modifier = Modifier,
    size: Dp = 56.dp,
    ring: Boolean = true,
) {
    val still = rememberReducedMotion()
    val transition = rememberInfiniteTransition(label = "presence")

    val breath by if (still) {
        remember { androidx.compose.runtime.mutableFloatStateOf(0.5f) }
    } else {
        transition.animateFloat(
            initialValue = 0f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(
                tween(6_000, easing = LinearEasing),
                RepeatMode.Reverse,
            ),
            label = "breathe",
        )
    }

    val ripple by if (still || !ring || size < 56.dp) {
        remember { androidx.compose.runtime.mutableFloatStateOf(0f) }
    } else {
        transition.animateFloat(
            initialValue = 0f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(tween(8_000, easing = LinearEasing)),
            label = "ripple",
        )
    }

    val outer = if (ring && size >= 56.dp) Dp(size.value * 1.5f) else size
    val description = stringResource(R.string.cd_alma_mark)

    // One announcement for the whole presence. The layers underneath clear
    // their own semantics, so a screen reader hears "Alma" once rather than
    // three times or — the alternative that was there first — not at all.
    Box(
        modifier = modifier.size(outer).semantics { contentDescription = description },
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.size(outer).clearAndSetSemantics { }) {
            val centre = Offset(this.size.width / 2f, this.size.height / 2f)

            if (ripple > 0f) {
                // 0.7 → 1.5 scale, fading out by 70 % of the way. The ring is a
                // hairline and it is the only circle in the product.
                val progress = ripple
                val r = this.size.minDimension / 2f * (0.7f + 0.8f * progress)
                val alpha = 0.3f * (1f - (progress / 0.7f).coerceAtMost(1f))
                if (alpha > 0.01f) {
                    drawCircle(
                        color = AlmaPalette.GoldBright,
                        radius = r,
                        center = centre,
                        alpha = alpha,
                        style = Stroke(width = 1.dp.toPx()),
                    )
                }
            }

            // `breathe`: scale 1 → 1.06, opacity 0.86 → 1.
            val swell = 1f + 0.06f * breath
            val radius = size.toPx() / 2f * swell
            translate(centre.x, centre.y) {
                drawCircle(
                    brush = Brush.radialGradient(
                        colorStops = arrayOf(
                            0.00f to Color(0xFFFFF6DF),
                            0.34f to Color(0xFFF1DFAE),
                            0.64f to AlmaPalette.Gold.copy(alpha = 0.45f),
                            0.80f to Color.Transparent,
                        ),
                        // Off-centre highlight, so it reads as lit rather than
                        // as a disc that glows on its own.
                        center = Offset(-radius * 0.16f, -radius * 0.24f),
                        radius = radius,
                    ),
                    radius = radius,
                    center = Offset.Zero,
                    alpha = 0.86f + 0.14f * breath,
                )
            }
        }
    }
}

/** A hairline gold rule. What separates content here, instead of a card. */
@Composable
fun Hairline(modifier: Modifier = Modifier, color: Color = AlmaPalette.HairlineGold) {
    Canvas(modifier.fillMaxWidth().height(1.dp)) {
        drawLine(
            color = color,
            start = Offset(0f, size.height / 2f),
            end = Offset(size.width, size.height / 2f),
            strokeWidth = size.height,
        )
    }
}

/**
 * A drawn path from the mark, exposed for anything that needs the silhouette
 * without the finish — a mask, a clip, a motif behind a heading.
 */
fun almaStarPath(): Path = PathParser().parsePathString(MarkBody).toPath()
