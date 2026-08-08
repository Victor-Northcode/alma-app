package ai.pazl.alma.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ProvidableCompositionLocal
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.text.TextStyle

/**
 * Alma's Material 3 colour scheme.
 *
 * There is one, and it is night. [isSystemInDarkTheme] is deliberately not
 * consulted anywhere in this file: night is the canvas, not a dark theme laid
 * over a light design, and a light variant would be a different product. The
 * one light surface — parchment — is a *surface*, and it lives in
 * `inverseSurface` where a component that needs it can find it.
 *
 * Dynamic colour is also refused. It is the best thing Material 3 added and it
 * is wrong here for one reason: it would put a second accent on screen, chosen
 * by somebody's wallpaper.
 */
private val AlmaColorScheme: ColorScheme = darkColorScheme(
    // One gold. `primary` is the aged one; `secondary` is the *same* gold
    // brighter, which is why there is no second hue anywhere below.
    primary = AlmaPalette.Gold,
    onPrimary = AlmaPalette.InkOnGold,
    primaryContainer = AlmaPalette.GoldDeep,
    onPrimaryContainer = AlmaPalette.InkLight,

    secondary = AlmaPalette.GoldBright,
    onSecondary = AlmaPalette.InkOnGold,
    secondaryContainer = AlmaPalette.Night700,
    onSecondaryContainer = AlmaPalette.GoldBright,

    // Indigo is the sky, not an accent: it appears in auras and gradients and
    // never on a control. It sits in `tertiary` so that nothing Material draws
    // by default picks it up.
    tertiary = AlmaPalette.IndigoBright,
    onTertiary = AlmaPalette.InkLight,
    tertiaryContainer = AlmaPalette.IndigoDeep,
    onTertiaryContainer = AlmaPalette.InkLight,

    background = AlmaPalette.Night800,
    onBackground = AlmaPalette.Body,

    // Surface *is* background. "No boxes" means a surface that differs from the
    // canvas is the exception, so the container ramp barely moves and what
    // separates content is a hairline rather than a step in luminance.
    surface = AlmaPalette.Night800,
    onSurface = AlmaPalette.Body,
    surfaceVariant = AlmaPalette.Night850,
    onSurfaceVariant = AlmaPalette.Muted,
    surfaceContainerLowest = AlmaPalette.Void,
    surfaceContainerLow = AlmaPalette.Night900,
    surfaceContainer = AlmaPalette.Night850,
    surfaceContainerHigh = AlmaPalette.Night800,
    surfaceContainerHighest = AlmaPalette.Night700,

    // The disagreement red. A contradiction between two systems is material
    // rather than a fault, and the product has exactly one warm colour for
    // both — an alarm red would be the second accent this design refuses.
    error = AlmaPalette.Disagree,
    onError = AlmaPalette.InkOnGold,
    errorContainer = AlmaPalette.Night700,
    onErrorContainer = AlmaPalette.Disagree,

    outline = AlmaPalette.Hairline,
    outlineVariant = AlmaPalette.HairlineGold,
    scrim = AlmaPalette.Void,

    // The parchment band, reachable by name.
    inverseSurface = AlmaPalette.Parchment,
    inverseOnSurface = AlmaPalette.Ink,
    inversePrimary = AlmaPalette.GoldDeep,
)

/**
 * The raw tokens, for the things Material has no slot for.
 *
 * A screen reads `MaterialTheme.colorScheme.primary` when it wants "the accent"
 * and `AlmaTheme.palette.StarFill` when it wants "the colour of a star". Both
 * are correct; the second exists because there is no Material slot that means
 * that, and inventing one by abusing `tertiaryContainer` is how palettes rot.
 */
val LocalAlmaPalette: ProvidableCompositionLocal<AlmaPalette> =
    staticCompositionLocalOf { AlmaPalette }

val LocalAlmaTypeScale: ProvidableCompositionLocal<AlmaTypeScale> =
    staticCompositionLocalOf { AlmaTypography }

/** Namespace for the tokens Material does not carry. */
object AlmaTheme {
    val palette: AlmaPalette
        @Composable @ReadOnlyComposable get() = LocalAlmaPalette.current

    val type: AlmaTypeScale
        @Composable @ReadOnlyComposable get() = LocalAlmaTypeScale.current
}

/**
 * Wraps the whole app exactly once, in [ai.pazl.alma.MainActivity].
 *
 * `LocalContentColor` is set alongside the scheme because Material only applies
 * `onSurface` inside its own containers, and this app spends most of its time
 * drawing directly on the canvas with no container at all — which is what "no
 * boxes" means in practice. Without this line a bare `Text` outside a `Surface`
 * inherits black.
 */
@Composable
fun AlmaTheme(content: @Composable () -> Unit) {
    CompositionLocalProvider(
        LocalAlmaPalette provides AlmaPalette,
        LocalAlmaTypeScale provides AlmaTypography,
        LocalContentColor provides AlmaPalette.Body,
    ) {
        MaterialTheme(
            colorScheme = AlmaColorScheme,
            typography = AlmaMaterialTypography,
            shapes = AlmaShapes,
            content = content,
        )
    }
}

/** Convenience for the styles Material cannot name. */
val MaterialTheme.almaType: AlmaTypeScale
    @Composable @ReadOnlyComposable get() = LocalAlmaTypeScale.current

/** The one style every cited placement uses. */
val positionsStyle: TextStyle
    @Composable @ReadOnlyComposable get() = LocalAlmaTypeScale.current.positions
