package ai.pazl.alma.ui.theme

import android.provider.Settings
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.Easing
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Durations and easings, from the `--d-*` / `--e-*` tokens in `globals.css`.
 *
 * The names describe what is moving rather than how long it takes, because the
 * numbers were chosen together: a tap that answers in 120 ms and a sheet that
 * arrives in 380 ms feel like one system, and a screen that picks 250 ms
 * because it seemed reasonable breaks it.
 */
@Immutable
object AlmaMotion {
    /** A control acknowledging a finger. */
    const val Tap: Int = 120
    val TapEasing: Easing = CubicBezierEasing(0.2f, 0f, 0.4f, 1f)

    /** Anything on screen changing state. */
    const val Ui: Int = 240
    val UiEasing: Easing = CubicBezierEasing(0.22f, 1f, 0.36f, 1f)

    /**
     * One page giving way to the next — a chapter pulled into.
     *
     * Longer than [Ui] and softer at the end, because this one is *finished* by
     * the animation rather than begun by it: the finger has already done the
     * first half of the movement, and what is left should look like the page
     * settling rather than like a new screen arriving. iOS carries the same
     * number as `AlmaMotion.turn`.
     */
    const val Page: Int = 420

    /** A sheet or overlay arriving. */
    const val Sheet: Int = 380
    val SheetEasing: Easing = CubicBezierEasing(0.16f, 1f, 0.3f, 1f)

    /** A bar filling. */
    const val Bar: Int = 420

    /** Something being revealed for the first time — a chapter, a portrait. */
    const val Reveal: Int = 620
}

/** The grid: side padding, the reading measure, the tab bar. */
@Immutable
object AlmaSpacing {
    /** Side padding on a phone. The web app widens this on tablets; so should a
     *  screen that adapts, using `WindowSizeClass` rather than a hardcoded
     *  breakpoint. */
    val Pad: Dp = 22.dp
    val PadWide: Dp = 34.dp

    /** The measure a paragraph is set to. Longer lines stop being readable. */
    val Reading: Dp = 720.dp

    /** Bottom tab bar, before the gesture inset is added. */
    val TabBar: Dp = 74.dp

    val Hairline: Dp = 1.dp
}

/**
 * Whether this device has asked for less movement, checked once per composition.
 *
 * The ambient sky is the one part of this product that never stops moving, so
 * it is also the one part that has to stop when asked. Android exposes the
 * request as the animator duration scale — the "Remove animations" toggle and
 * the developer-options scale write the same value — and a scale of zero is the
 * platform saying that animations should not run at all.
 *
 * The rejected alternative was to ignore it and rely on the system to freeze
 * animators for us. It does not: Compose's `InfiniteTransition` is driven by
 * the frame clock and runs happily at a duration scale of zero, so a starfield
 * left to itself would keep twinkling at somebody who turned animation off
 * because it makes them ill.
 */
@Composable
fun rememberReducedMotion(): Boolean {
    val context = LocalContext.current
    return remember(context) {
        val scale = Settings.Global.getFloat(
            context.contentResolver,
            Settings.Global.ANIMATOR_DURATION_SCALE,
            1f,
        )
        scale == 0f
    }
}
