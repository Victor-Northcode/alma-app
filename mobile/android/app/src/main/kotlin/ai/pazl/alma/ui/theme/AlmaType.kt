package ai.pazl.alma.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.runtime.Immutable
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp

/**
 * The type scale, transcribed from the `.display-xl` / `.alma-voice` / `.meta`
 * rules in `src/app/globals.css`.
 *
 * Line heights in the CSS are unitless multipliers; here they are absolute, so
 * every one below is the multiplier times the size, rounded to a tenth. That is
 * a real difference and not a transcription artefact: Compose does not scale
 * line height with the font size the way a unitless CSS value does, so a person
 * who has turned the system font size up gets tighter leading than the web. It
 * is the smaller of two evils — the alternative is computing line height at
 * draw time in every composable — and it is the reason nothing here uses a line
 * height under 1.2× except the two display sizes, where tight is the intent.
 */
object AlmaFonts {

    /**
     * Playfair Display's slot, and the reason it is a `FontFamily.Serif` today.
     *
     * The web app loads Playfair and Golos Text from a font CDN. Bundling the
     * two real families is a separate decision with a real cost — roughly
     * 300 KB of the APK for weights the app actually uses — and it belongs to
     * whoever ships the store build, not to the skeleton. Until then the
     * platform serif is close enough in colour and proportion that the layout
     * does not move when the real file arrives: drop the TTFs into
     * `res/font/` and change these two lines, and nothing else in the app has
     * to know.
     */
    val Display: FontFamily = FontFamily.Serif

    /** Golos Text's slot. */
    val Sans: FontFamily = FontFamily.SansSerif
}

/**
 * The styles the brand book names, for the times Material's slots do not have
 * an honest counterpart.
 *
 * `almaVoice` is the clearest case: it is Alma speaking, italic serif at 21 sp,
 * and there is no Material slot that means "this sentence is the product's
 * voice rather than its interface". Putting it in `bodyLarge` would make every
 * paragraph italic; inventing it here keeps the two apart.
 */
@Immutable
data class AlmaTypeScale(
    /** Section labels: 11.5 sp, letterspaced hard, always gold. */
    val overline: TextStyle,
    /** Wider tracking, for the label that stands alone above a display line. */
    val overlineWide: TextStyle,
    val displayXl: TextStyle,
    val displayL: TextStyle,
    val headingM: TextStyle,
    /** Alma, speaking. Italic serif. Never used for interface copy. */
    val almaVoice: TextStyle,
    /** The day text on Today: Alma's voice set for reading standing up —
     * smaller, lighter, not italic. The italic serif at 21 sp was the owner's
     * «неудобно читать». */
    val dayVoice: TextStyle,
    /** The line under a heading: 13 sp, muted. */
    val meta: TextStyle,
    /**
     * A cited placement — "Moon in Scorpio, 8th house".
     *
     * Serif and bright gold wherever it appears, because every sentence in the
     * product cites the placement it was read from, and the citation has to be
     * visibly a different kind of thing from the prose around it.
     */
    val positions: TextStyle,
    /** The label inside a gold button. */
    val button: TextStyle,
)

val AlmaTypography: AlmaTypeScale = AlmaTypeScale(
    overline = TextStyle(
        fontFamily = AlmaFonts.Sans,
        fontSize = 11.5.sp,
        lineHeight = 16.sp,
        letterSpacing = 0.22.em,
        fontWeight = FontWeight.SemiBold,
        color = AlmaPalette.Gold,
    ),
    overlineWide = TextStyle(
        fontFamily = AlmaFonts.Sans,
        fontSize = 11.5.sp,
        lineHeight = 16.sp,
        letterSpacing = 0.24.em,
        fontWeight = FontWeight.SemiBold,
        color = AlmaPalette.Gold,
    ),
    displayXl = TextStyle(
        fontFamily = AlmaFonts.Display,
        fontSize = 39.sp,
        lineHeight = 38.2.sp,
        letterSpacing = (-0.03).em,
        fontWeight = FontWeight.Normal,
        color = AlmaPalette.InkLight,
    ),
    displayL = TextStyle(
        fontFamily = AlmaFonts.Display,
        fontSize = 29.sp,
        lineHeight = 31.3.sp,
        fontWeight = FontWeight.Normal,
        color = AlmaPalette.InkLight,
    ),
    headingM = TextStyle(
        fontFamily = AlmaFonts.Display,
        fontSize = 17.5.sp,
        lineHeight = 21.7.sp,
        fontWeight = FontWeight.Normal,
        color = AlmaPalette.InkLight,
    ),
    almaVoice = TextStyle(
        fontFamily = AlmaFonts.Display,
        fontStyle = FontStyle.Italic,
        fontSize = 21.sp,
        lineHeight = 31.5.sp,
        fontWeight = FontWeight.Normal,
        color = AlmaPalette.InkLight,
    ),
    dayVoice = TextStyle(
        fontFamily = AlmaFonts.Display,
        fontSize = 17.5.sp,
        lineHeight = 27.sp,
        fontWeight = FontWeight.Light,
        color = AlmaPalette.InkLight.copy(alpha = 0.95f),
    ),
    meta = TextStyle(
        fontFamily = AlmaFonts.Sans,
        fontSize = 13.sp,
        lineHeight = 19.sp,
        color = AlmaPalette.Muted2,
    ),
    positions = TextStyle(
        fontFamily = AlmaFonts.Display,
        fontSize = 15.5.sp,
        lineHeight = 25.1.sp,
        color = AlmaPalette.GoldBright,
    ),
    button = TextStyle(
        fontFamily = AlmaFonts.Sans,
        fontSize = 16.5.sp,
        lineHeight = 20.sp,
        fontWeight = FontWeight.SemiBold,
    ),
)

/**
 * Material's slots, filled from the scale above.
 *
 * Every Material component the app uses — a `Text` with no style, a
 * `NavigationBarItem`'s label, a `Snackbar` — reads one of these, so filling
 * them is what stops stock components from arriving in Roboto. The mapping is
 * deliberate rather than mechanical: `bodyLarge` is body copy at 15.5/25.1
 * because that is what a paragraph in this product is, and Material's default
 * 16/24 Roboto would be a different product.
 */
val AlmaMaterialTypography: Typography = Typography(
    displayLarge = AlmaTypography.displayXl,
    displayMedium = AlmaTypography.displayL,
    displaySmall = AlmaTypography.displayL.copy(fontSize = 24.sp, lineHeight = 26.sp),
    headlineLarge = AlmaTypography.displayL,
    headlineMedium = AlmaTypography.headingM.copy(fontSize = 22.sp, lineHeight = 27.sp),
    headlineSmall = AlmaTypography.headingM.copy(fontSize = 20.sp, lineHeight = 25.sp),
    titleLarge = AlmaTypography.headingM.copy(fontSize = 19.sp, lineHeight = 24.sp),
    titleMedium = AlmaTypography.headingM,
    titleSmall = AlmaTypography.headingM.copy(fontSize = 15.sp, lineHeight = 20.sp),
    bodyLarge = TextStyle(
        fontFamily = AlmaFonts.Sans,
        fontSize = 15.5.sp,
        lineHeight = 25.1.sp,
        color = AlmaPalette.Body,
    ),
    bodyMedium = TextStyle(
        fontFamily = AlmaFonts.Sans,
        fontSize = 14.5.sp,
        lineHeight = 23.sp,
        color = AlmaPalette.Muted,
    ),
    bodySmall = AlmaTypography.meta,
    labelLarge = AlmaTypography.button,
    labelMedium = TextStyle(
        fontFamily = AlmaFonts.Sans,
        fontSize = 12.5.sp,
        lineHeight = 16.sp,
        fontWeight = FontWeight.Medium,
    ),
    labelSmall = AlmaTypography.overline,
)
