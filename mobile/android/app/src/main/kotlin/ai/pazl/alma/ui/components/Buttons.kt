package ai.pazl.alma.ui.components

import ai.pazl.alma.ui.theme.AlmaMotion
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import ai.pazl.alma.ui.theme.PillShape
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp

/**
 * The two buttons this product has.
 *
 * They are written by hand rather than configured out of `Button` +
 * `ButtonDefaults`, for one reason worth stating: the gold button's fill is a
 * **gradient**, and Material's `ButtonColors` takes a `Color`. Everything else
 * — the ripple, the button role, the disabled semantics — comes from
 * `Modifier.clickable`, which is the part of the toolkit worth keeping.
 *
 * There is no third button. A screen that needs one has invented a new level of
 * emphasis, and the answer to that is nearly always fewer things on the screen.
 */

/**
 * The one that takes money, starts the journey, opens the chapter.
 *
 * 56 dp tall, a pill, gold gradient lit from the top, with a shadow in the same
 * hue as the fill — "depth is light, not shadow" means the drop is a glow the
 * surface casts rather than a grey box beneath it. The press is a 1.5 % squash
 * over 120 ms and nothing else; buttons in this product do not bounce.
 */
@Composable
fun GoldButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    leading: (@Composable () -> Unit)? = null,
) {
    val interactions = remember { MutableInteractionSource() }
    val pressed by interactions.collectIsPressedAsState()
    val squash by animateFloatAsState(
        targetValue = if (pressed) 0.985f else 1f,
        animationSpec = tween(AlmaMotion.Tap, easing = AlmaMotion.TapEasing),
        label = "press",
    )

    Row(
        modifier = modifier
            .scale(squash)
            .height(56.dp)
            .defaultMinSize(minWidth = 120.dp)
            // A disabled control casts nothing. A button that cannot be pressed
            // should not look like it is floating above the page.
            .then(
                if (enabled) {
                    Modifier.shadow(
                        elevation = 14.dp,
                        shape = PillShape,
                        ambientColor = AlmaPalette.GoldDeep,
                        spotColor = AlmaPalette.GoldDeep,
                    )
                } else {
                    Modifier
                }
            )
            .background(
                brush = if (pressed) AlmaPalette.GoldButtonPressed else AlmaPalette.GoldButton,
                shape = PillShape,
            )
            .alpha(if (enabled) 1f else 0.45f)
            .clickable(
                interactionSource = interactions,
                // Bounded to the pill, so the ripple never spills into the night.
                indication = ripple(color = AlmaPalette.InkOnGold),
                enabled = enabled,
                role = Role.Button,
                onClick = onClick,
            )
            .padding(horizontal = 28.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp, Alignment.CenterHorizontally),
    ) {
        leading?.invoke()
        Text(text = text, style = AlmaTheme.type.button, color = AlmaPalette.InkOnGold)
    }
}

/**
 * Everything else: "not now", "try again", "add my birth time".
 *
 * A hairline pill on the night, with no fill at all. Quiet on purpose — the
 * moment a secondary action gets a background, two things on the screen are
 * competing for the same tap.
 */
@Composable
fun QuietButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    contentColor: Color = AlmaPalette.GoldBright,
) {
    val interactions = remember { MutableInteractionSource() }

    Box(
        modifier = modifier
            .height(52.dp)
            .border(1.dp, AlmaPalette.HairlineGold, PillShape)
            .alpha(if (enabled) 1f else 0.45f)
            .clickable(
                interactionSource = interactions,
                indication = ripple(color = AlmaPalette.Gold),
                enabled = enabled,
                role = Role.Button,
                onClick = onClick,
            )
            .padding(horizontal = 24.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(text = text, style = AlmaTheme.type.button, color = contentColor)
    }
}

/** A section label: 11.5 sp, tracked hard, gold, uppercase. */
@Composable
fun Overline(text: String, modifier: Modifier = Modifier, wide: Boolean = false) {
    Text(
        text = text.uppercase(),
        modifier = modifier,
        style = if (wide) AlmaTheme.type.overlineWide else AlmaTheme.type.overline,
    )
}
