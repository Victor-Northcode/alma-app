package ai.pazl.alma.ui.components

import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp

/**
 * Content arriving on screen — the entrance half of the motion vocabulary,
 * mirroring iOS `Arrival.swift`.
 *
 * `AlmaMotion` covers *controls*: a tap, a state change, a sheet. What it did
 * not cover was content itself appearing, and the result was screens that snap
 * from empty to full in one frame — correct, and lifeless. This is the one
 * entrance the product uses everywhere: a rise of a few dp with a fade,
 * staggered down the page.
 *
 * One entrance, not several — every block arriving the same way, slightly
 * after the block above it, is how a page feels set rather than loaded. The
 * stagger is capped so a long page's last card never waits out a second of
 * choreography.
 */
private val ArriveEasing = CubicBezierEasing(0.16f, 1f, 0.3f, 1f)
private const val ArriveMillis = 550
private const val StaggerMillis = 70
private val ArriveRise = 16.dp

/**
 * Fade-and-rise into place on first composition, [index] steps down the
 * cascade. `remember` keeps it a one-shot: recomposition on a data refresh
 * does not replay the entrance; leaving the screen and coming back does —
 * the same lifetime iOS `@State` gives the same modifier there.
 */
fun Modifier.riseIn(index: Int = 0): Modifier = composed {
    var seated by remember { mutableStateOf(false) }
    val progress by animateFloatAsState(
        targetValue = if (seated) 1f else 0f,
        animationSpec = tween(
            durationMillis = ArriveMillis,
            delayMillis = minOf(index, 8) * StaggerMillis,
            easing = ArriveEasing,
        ),
        label = "riseIn",
    )
    LaunchedEffect(Unit) { seated = true }
    graphicsLayer {
        alpha = progress
        translationY = (1f - progress) * ArriveRise.toPx()
    }
}

/**
 * A card acknowledging a finger — the give of paper, not the sink of a key.
 *
 * 1.5% of scale is below the threshold where a row reads as a game tile and
 * exactly at the threshold where a list stops feeling inert. Used by
 * `CabinetRow`, which is every tappable row in the cabinet; the buttons keep
 * their own press language in `Buttons.kt`.
 */
@Composable
fun animatePressGive(pressed: Boolean): Float {
    val give by animateFloatAsState(
        targetValue = if (pressed) 0.985f else 1f,
        animationSpec = tween(durationMillis = 120, easing = CubicBezierEasing(0.2f, 0f, 0.4f, 1f)),
        label = "pressGive",
    )
    return give
}


/**
 * The quiet life of a settled diagram — the owner's finding was that a paused
 * canvas reads as *gone*. A slow breath of scale and light over the settled
 * frame; the canvas itself never redraws.
 */
fun Modifier.breathing(): Modifier = composed {
    val transition = rememberInfiniteTransition(label = "breath")
    val t by transition.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(
            tween(durationMillis = 3400, easing = FastOutSlowInEasing),
            RepeatMode.Reverse,
        ),
        label = "breath",
    )
    graphicsLayer {
        val s = 0.996f + 0.012f * t
        scaleX = s
        scaleY = s
        alpha = 0.965f + 0.035f * t
    }
}
