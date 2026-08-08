package ai.pazl.alma.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

/**
 * The palette, transcribed from `src/app/globals.css`.
 *
 * Two lists rather than one, and the split is the point. [AlmaPalette] is the
 * *raw* tokens — the names the brand book uses, the names a designer says out
 * loud — and it is what a screen reaches for when it needs "the aged gold" or
 * "the disagreement red". Material 3's [androidx.compose.material3.ColorScheme]
 * is derived from it below and is what the toolkit's own components read.
 *
 * Deriving one from the other rather than maintaining both is what keeps a
 * button that was styled by hand and a button that came out of the box the same
 * colour. Where the two disagree the raw token wins, because Material's slot
 * names were invented for a different design and several of them have no honest
 * counterpart here — there is no secondary accent to put in `secondary`, so
 * `secondary` holds the *bright* gold rather than a second hue. One gold, aged.
 */
@Immutable
object AlmaPalette {

    /* ── night & indigo ────────────────────────────────────────────────── */

    /** Below the canvas: scrims, the launcher field, the deepest vignette. */
    val Void = Color(0xFF04060E)
    val Night900 = Color(0xFF070A16)
    val Night850 = Color(0xFF090C1A)

    /** The canvas. Everything sits on this; it is not a "dark mode" of a light design. */
    val Night800 = Color(0xFF0A0D1C)
    val Night700 = Color(0xFF101636)

    val Indigo = Color(0xFF3A3484)
    val IndigoBright = Color(0xFF604EC4)
    val IndigoDeep = Color(0xFF1E3A96)

    /* ── one gold, aged ────────────────────────────────────────────────── */

    val Gold = Color(0xFFC9AE6B)
    val GoldDeep = Color(0xFFA8873C)
    val GoldBright = Color(0xFFE4D3A2)

    /** Star fill — the lightest the gold is ever allowed to go. */
    val StarFill = Color(0xFFF6E7BC)

    /* ── light & ink ───────────────────────────────────────────────────── */

    val InkLight = Color(0xFFF6F1E4)

    /** Body copy on night. Not white: white on this navy vibrates. */
    val Body = Color(0xFFEDE7DA)

    /** What sits on a gold surface. Near-black with a violet cast, never pure black. */
    val InkOnGold = Color(0xFF141019)

    /** The one light surface in the product. */
    val Parchment = Color(0xFFF1E9D6)
    val ParchmentA = Color(0xFFF6EEDB)
    val ParchmentB = Color(0xFFE8DBBE)
    val Ink = Color(0xFF1C1A17)

    /* ── semantic ──────────────────────────────────────────────────────── */

    /** Systems that agree. */
    val Agree = Color(0xFF8FBF9A)

    /** Systems that disagree — and the error colour, because a contradiction is
     *  material rather than a fault, and the product never shouts in red. */
    val Disagree = Color(0xFFE0917F)

    /* ── surfaces: veils over night, not boxes on it ───────────────────── */

    val Veil = Body.copy(alpha = 0.07f)
    val VeilStrong = Body.copy(alpha = 0.09f)
    val Hairline = Body.copy(alpha = 0.10f)
    val HairlineGold = Gold.copy(alpha = 0.16f)
    val Panel = Color.White.copy(alpha = 0.04f)

    /* ── muted ink · hard floor 62 % ───────────────────────────────────── */

    val Muted = Body.copy(alpha = 0.72f)
    val Muted2 = Body.copy(alpha = 0.68f)

    /** The floor. Nothing readable is ever fainter than this on night. */
    val Muted3 = Body.copy(alpha = 0.62f)
    val InkMuted = Ink.copy(alpha = 0.72f)
    val InkMuted2 = Ink.copy(alpha = 0.62f)

    /* ── gradients ─────────────────────────────────────────────────────── */

    /** The gold button. Top-lit, so it reads as a struck surface rather than a fill. */
    val GoldButton = Brush.verticalGradient(listOf(Color(0xFFDCC48A), GoldDeep))
    val GoldButtonPressed = Brush.verticalGradient(listOf(Color(0xFF8F7233), Color(0xFF8F7233)))

    /** The mark's gradient, and the only place four gold stops appear together. */
    val GoldGradient = Brush.linearGradient(
        0.00f to Color(0xFFFBEDC4),
        0.34f to Color(0xFFE0C077),
        0.70f to Color(0xFFB3913F),
        1.00f to Color(0xFF8A6F2E),
    )

    val ParchmentGradient = Brush.verticalGradient(listOf(ParchmentA, ParchmentB))
}
