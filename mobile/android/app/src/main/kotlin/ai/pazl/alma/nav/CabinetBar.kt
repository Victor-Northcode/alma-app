package ai.pazl.alma.nav

import ai.pazl.alma.ui.theme.AlmaPalette
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.layout.onSizeChanged
import android.view.HapticFeedbackConstants

/**
 * The bottom tabs.
 *
 * Written rather than taken from `NavigationBar`, and the reason is the design
 * rather than the toolkit: Material's navigation bar draws a filled *pill*
 * behind the active item, which is a box, and this design has no boxes. The
 * active state here is what the web app uses — the label and glyph go to bright
 * gold and a 3 dp gold dot appears underneath — and there is no way to express
 * that through `NavigationBarItemColors`.
 *
 * What is kept from Material: the 48 dp minimum target, the `selectable`
 * semantics with `Role.Tab`, and the insets handling. Those are the parts of
 * the toolkit that are about accessibility rather than about looks.
 */
@Composable
fun CabinetBar(
    current: CabinetTab?,
    onSelect: (CabinetTab) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            // Not opaque. The sky keeps moving behind the bar, which is the
            // point of the rule — the UI is still, the sky is not, and a solid
            // bar would cut the sky off at a hard line across the screen.
            .background(AlmaPalette.Night850.copy(alpha = 0.94f))
            .windowInsetsPadding(WindowInsets.navigationBars)
    ) {
        Canvas(Modifier.fillMaxWidth().height(1.dp)) {
            drawLine(
                color = AlmaPalette.Gold.copy(alpha = 0.14f),
                start = Offset(0f, 0f),
                end = Offset(size.width, 0f),
                strokeWidth = size.height,
            )
        }
        // **Hold and slide, the way Telegram's bar works.** The owner asked for
        // it in those words: press Today, move without letting go, and the
        // selection travels with the finger.
        //
        // `detectHorizontalDragGestures` rather than a tap-aware gesture:
        // the items keep their own `selectable`, so an ordinary tap is still
        // theirs and this only ever sees a finger that has already moved.
        var barWidth by remember { mutableFloatStateOf(0f) }
        val view = LocalView.current
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 62.dp)
                .padding(top = 9.dp, bottom = 12.dp)
                .onSizeChanged { barWidth = it.width.toFloat() }
                .pointerInput(current) {
                    detectHorizontalDragGestures { change, _ ->
                        if (barWidth <= 0f) return@detectHorizontalDragGestures
                        val column = barWidth / CabinetTab.entries.size
                        val index = (change.position.x / column).toInt()
                            .coerceIn(0, CabinetTab.entries.lastIndex)
                        val tab = CabinetTab.entries[index]
                        if (tab != current) {
                            view.performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK)
                            onSelect(tab)
                        }
                    }
                },
            horizontalArrangement = Arrangement.SpaceAround,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            CabinetTab.entries.forEach { tab ->
                TabItem(tab = tab, selected = tab == current, onSelect = { onSelect(tab) })
            }
        }
    }
}

@Composable
private fun TabItem(tab: CabinetTab, selected: Boolean, onSelect: () -> Unit) {
    val label = stringResource(tab.label)
    Column(
        modifier = Modifier
            .width(74.dp)
            .heightIn(min = 48.dp)
            .selectable(
                selected = selected,
                role = Role.Tab,
                onClick = onSelect,
            ),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(5.dp, Alignment.CenterVertically),
    ) {
        TabGlyph(tab, selected)
        Text(
            text = label,
            fontSize = 11.sp,
            color = if (selected) AlmaPalette.GoldBright else AlmaPalette.Body.copy(alpha = 0.5f),
        )
        // The active marker: a 3 dp dot, not a pill behind the item.
        Box(
            Modifier
                .size(3.dp)
                .background(
                    color = if (selected) AlmaPalette.Gold else Color.Transparent,
                    shape = CircleShape,
                )
        )
    }
}

/**
 * The four glyphs, drawn.
 *
 * Line work at 1.25 dp, matching the web app's SVGs stroke for stroke. Alma's
 * is not a line drawing at all — it is her presence in miniature, the same soft
 * light the chat screen shows at 56 dp — because she is a person in this
 * product and the other three are places.
 */
@Composable
private fun TabGlyph(tab: CabinetTab, selected: Boolean) {
    val stroke = if (selected) AlmaPalette.GoldBright else AlmaPalette.Body.copy(alpha = 0.5f)

    Canvas(Modifier.size(24.dp)) {
        val w = size.width
        val line = Stroke(width = 1.25.dp.toPx(), cap = StrokeCap.Round)
        val unit = w / 24f

        when (tab) {
            CabinetTab.Today -> {
                // A sun: the day, and the only glyph with rays.
                drawCircle(stroke, radius = 4f * unit, center = Offset(w / 2f, w / 2f), style = line)
                listOf(
                    Offset(12f, 2f) to Offset(12f, 4.5f),
                    Offset(12f, 19.5f) to Offset(12f, 22f),
                    Offset(2f, 12f) to Offset(4.5f, 12f),
                    Offset(19.5f, 12f) to Offset(22f, 12f),
                ).forEach { (from, to) ->
                    drawLine(stroke, from * unit, to * unit, strokeWidth = 1.25.dp.toPx(), cap = StrokeCap.Round)
                }
            }

            CabinetTab.Systems -> {
                // Concentric circles: eight systems around one person.
                drawCircle(stroke, radius = 9f * unit, center = Offset(w / 2f, w / 2f), style = line)
                drawCircle(stroke, radius = 3.2f * unit, center = Offset(w / 2f, w / 2f), style = line)
            }

            CabinetTab.Alma -> {
                drawCircle(
                    brush = Brush.radialGradient(
                        colorStops = arrayOf(
                            0.00f to Color(0xFFFFF6DF),
                            0.40f to Color(0xFFF1DFAE),
                            0.70f to AlmaPalette.Gold.copy(alpha = 0.30f),
                            0.84f to Color.Transparent,
                        ),
                        center = Offset(w * 0.42f, w * 0.38f),
                        radius = w / 2f,
                    ),
                    radius = w / 2f,
                    center = Offset(w / 2f, w / 2f),
                    alpha = if (selected) 1f else 0.65f,
                )
            }

            CabinetTab.Settings -> {
                // Two sliders: the settings themselves, and *not* a second sun.
                //
                // This was a ring of radius 3 with six rays — two vertical, four
                // diagonal — transcribed stroke for stroke from the web's SVG.
                // Faithful, and wrong here. At 24 dp it has the same silhouette
                // as Today's ring of radius 4 with four rays: a small sun, twice,
                // on the two furthest-apart destinations in the product. On the
                // web those bottom tabs are a mobile-only affordance sitting
                // behind a labelled sidebar, so the ambiguity never had to carry
                // weight; on Android this bar is the whole of navigation.
                //
                // Rays are Today's alone now — the comment on that branch has
                // always claimed as much. What replaces them is the one shape in
                // the web's own vocabulary that means "adjust": two rules with a
                // handle on each, at different positions, which is a hairline
                // slider and reads as nothing else at this size.
                listOf(7.5f to 9.5f, 16.5f to 14.5f).forEach { (y, handle) ->
                    drawLine(
                        stroke,
                        Offset(4f, y) * unit,
                        Offset(20f, y) * unit,
                        strokeWidth = 1.25.dp.toPx(),
                        cap = StrokeCap.Round,
                    )
                    drawCircle(
                        stroke,
                        radius = 2.4f * unit,
                        center = Offset(handle, y) * unit,
                        style = line,
                    )
                }
            }
        }
    }
}
