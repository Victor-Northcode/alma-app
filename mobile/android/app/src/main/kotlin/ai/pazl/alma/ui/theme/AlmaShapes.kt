package ai.pazl.alma.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

/**
 * Shapes, and the reason most of them are barely rounded.
 *
 * Material's default ramp goes up to 28 dp, which produces the soft rectangles
 * that make an app read as stock Material. This design has two shapes and no
 * middle: a **pill** — every button, every chip, every focus ring, radius 999 —
 * and a **plain edge** for the rare surface that has to be one, at 14 dp.
 *
 * `extraLarge` stays generous because it is what `ModalBottomSheet` reads, and a
 * sheet arriving from the bottom of a night canvas needs a visible top corner
 * or its edge disappears.
 */
val AlmaShapes: Shapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(14.dp),
    large = RoundedCornerShape(20.dp),
    extraLarge = RoundedCornerShape(28.dp),
)

/** The pill. `--radius: 999px` in the CSS; every control in the product is one. */
val PillShape: RoundedCornerShape = RoundedCornerShape(percent = 50)
