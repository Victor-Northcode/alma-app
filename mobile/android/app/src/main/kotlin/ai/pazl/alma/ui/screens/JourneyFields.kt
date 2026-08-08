package ai.pazl.alma.ui.screens

import ai.pazl.alma.ui.theme.AlmaFonts
import ai.pazl.alma.ui.theme.AlmaMotion
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import ai.pazl.alma.ui.theme.PillShape
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.LocalTextSelectionColors
import androidx.compose.foundation.text.selection.TextSelectionColors
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * The controls the journey asks its questions with.
 *
 * All of them are built from `BasicTextField`, `Modifier.clickable` and
 * `Modifier.toggleable` rather than from Material's `TextField`, `Switch` and
 * `ExposedDropdownMenu`. That is not a rejection of the toolkit — the semantics,
 * the roles, the ripple and the touch targets underneath are all Material's, and
 * they are the parts worth having. What is not worth having is the *look*:
 * Material's text field brings a filled container, a floating label and an
 * indicator line, and there is no combination of `TextFieldDefaults` that turns
 * those into a hairline pill on a night sky. Three of the five rules — night is
 * the canvas, one gold, no boxes — are decided by exactly these five controls.
 *
 * There is no third button here either. `GoldButton` and `QuietButton` come from
 * `ui/components`, and nothing in this file competes with them.
 *
 * ## Why every style below names its font
 *
 * `MaterialTheme` fills Material's own type slots, so a `Button`'s label and a
 * `NavigationBarItem`'s caption arrive in the right family. It does **not**
 * provide `LocalTextStyle`, so a `TextStyle(fontSize = …)` handed to a bare
 * `Text` inherits `TextStyle.Default` — which is Roboto, at which point the
 * whole screen is stock Android with a gold tint. Hence [sans].
 */

/** Sans at a given size. Never a bare `TextStyle`: see the note above. */
private fun sans(
    size: TextUnit,
    color: Color,
    lineHeight: TextUnit = (size.value * 1.3f).sp,
): TextStyle = TextStyle(
    fontFamily = AlmaFonts.Sans,
    fontSize = size,
    lineHeight = lineHeight,
    color = color,
)

/* ── free text ─────────────────────────────────────────────────────────── */

/**
 * A name, a city. 58 dp, a pill, a gold hairline, and a placeholder that is a
 * *suggestion of format* rather than a value — the field itself is empty, and
 * the difference between a placeholder and a default is the difference between
 * "people write things like this here" and "we have decided this about you".
 */
@Composable
fun AlmaTextField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    label: String,
    modifier: Modifier = Modifier,
    imeAction: ImeAction = ImeAction.Done,
    capitalisation: KeyboardCapitalization = KeyboardCapitalization.Words,
) {
    val selection = TextSelectionColors(
        handleColor = AlmaPalette.Gold,
        backgroundColor = AlmaPalette.Gold.copy(alpha = 0.28f),
    )

    CompositionLocalProvider(LocalTextSelectionColors provides selection) {
        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = modifier
                .fillMaxWidth()
                .height(58.dp)
                .background(AlmaPalette.Veil, PillShape)
                .border(1.dp, AlmaPalette.Gold.copy(alpha = 0.40f), PillShape)
                .semantics { contentDescription = label },
            singleLine = true,
            textStyle = sans(17.sp, AlmaPalette.InkLight),
            keyboardOptions = KeyboardOptions(
                capitalization = capitalisation,
                imeAction = imeAction,
            ),
            cursorBrush = SolidColor(AlmaPalette.Gold),
            decorationBox = { field ->
                Box(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 22.dp),
                    contentAlignment = Alignment.CenterStart,
                ) {
                    if (value.isEmpty()) {
                        Text(text = placeholder, style = sans(17.sp, AlmaPalette.Muted3))
                    }
                    field()
                }
            },
        )
    }
}

/* ── one of four ───────────────────────────────────────────────────────── */

/**
 * An answer to a question with a fixed set of answers.
 *
 * Unselected it is a veil on the night; selected it takes the gold hairline and
 * the bright gold text. There is no radio dot — a whole row changing colour is
 * the clearer signal at arm's length, and `Role.RadioButton` tells a screen
 * reader what the row is without one being drawn.
 */
@Composable
fun ChoiceRow(
    text: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 54.dp)
            .background(
                color = if (selected) AlmaPalette.Gold.copy(alpha = 0.12f) else AlmaPalette.Veil,
                shape = PillShape,
            )
            .border(
                width = 1.dp,
                color = if (selected) AlmaPalette.Gold.copy(alpha = 0.55f) else Color.Transparent,
                shape = PillShape,
            )
            .clickable(role = Role.RadioButton, onClick = onClick)
            .padding(horizontal = 22.dp, vertical = 14.dp),
        contentAlignment = Alignment.CenterStart,
    ) {
        Text(
            text = text,
            style = sans(
                size = 15.5.sp,
                color = if (selected) AlmaPalette.GoldBright else AlmaPalette.Body.copy(alpha = 0.85f),
                lineHeight = 21.sp,
            ),
        )
    }
}

/**
 * "Skip", "not now". The quietest thing on the screen and deliberately not a
 * button: it has no border and no fill, because an escape hatch that competes
 * with the answer is an escape hatch people take by accident.
 */
@Composable
fun SkipAction(text: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 44.dp)
            .clickable(role = Role.Button, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(text = text, style = sans(13.5.sp, AlmaPalette.Body.copy(alpha = 0.5f)))
    }
}

/* ── picking from a list ───────────────────────────────────────────────── */

/**
 * One third of a date, or one third of a clock.
 *
 * Tapping it does not open a menu over the screen; it expands [OptionList]
 * underneath, in the same column, on the same night. A dropdown would have been
 * a floating raised surface with an elevation shadow — a box, in a product whose
 * layout rule is that there are none — and a wheel picker would have been
 * Android's own dialog in Android's own accent colour.
 */
@Composable
fun RowScope.PickerField(
    value: String?,
    placeholder: String,
    label: String,
    open: Boolean,
    onClick: () -> Unit,
    weight: Float,
    enabled: Boolean = true,
) {
    Row(
        modifier = Modifier
            .weight(weight)
            .height(56.dp)
            .background(AlmaPalette.Veil, PillShape)
            .border(
                width = 1.dp,
                color = if (open) AlmaPalette.Gold.copy(alpha = 0.55f) else AlmaPalette.HairlineGold,
                shape = PillShape,
            )
            .alpha(if (enabled) 1f else 0.4f)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label }
            .padding(start = 18.dp, end = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(
            text = value ?: placeholder,
            style = sans(
                size = 16.sp,
                color = if (value == null) AlmaPalette.Muted3 else AlmaPalette.InkLight,
            ),
        )
        Caret(open)
    }
}

/** Two strokes. Drawn rather than shipped, so it is the gold and not an icon set's grey. */
@Composable
private fun Caret(open: Boolean) {
    Canvas(Modifier.size(10.dp).clearAndSetSemantics { }) {
        val width = size.width
        val drop = size.height * 0.6f
        val top = (size.height - drop) / 2f
        val thickness = 1.4.dp.toPx()
        val apex = if (open) top else top + drop
        val ends = if (open) top + drop else top
        drawLine(AlmaPalette.Gold, Offset(0f, ends), Offset(width / 2f, apex), thickness)
        drawLine(AlmaPalette.Gold, Offset(width / 2f, apex), Offset(width, ends), thickness)
    }
}

/**
 * The options for whichever picker is open.
 *
 * Capped at 244 dp and scrolled, because one of these lists is ninety-two years
 * long. It opens *at* the current selection rather than at the top — with
 * nothing selected that is the top, which is where somebody who has chosen
 * nothing expects to start.
 */
@Composable
fun OptionList(
    options: List<String>,
    selectedIndex: Int,
    modifier: Modifier = Modifier,
    // Last, so that picking is the trailing lambda at every call site. Compose's
    // own convention puts `modifier` second for exactly this reason.
    onPick: (Int) -> Unit,
) {
    val state = rememberLazyListState(
        initialFirstVisibleItemIndex = (selectedIndex - 1).coerceAtLeast(0)
    )

    LazyColumn(
        modifier = modifier.fillMaxWidth().heightIn(max = 244.dp),
        state = state,
    ) {
        items(options.size) { index ->
            val chosen = index == selectedIndex
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(46.dp)
                    .clickable(role = Role.RadioButton) { onPick(index) }
                    .padding(horizontal = 20.dp),
                contentAlignment = Alignment.CenterStart,
            ) {
                Text(
                    text = options[index],
                    style = sans(
                        size = 16.sp,
                        color = if (chosen) AlmaPalette.GoldBright else AlmaPalette.Muted,
                    ),
                )
            }
        }
    }
}

/* ── the one switch in the product ─────────────────────────────────────── */

/**
 * "I don't know my birth time".
 *
 * A 52 × 30 pill with a 24 dp knob, drawn by hand for one reason: Material's
 * `Switch` renders its track and thumb from the scheme's primary, and the
 * scheme's primary here is the aged gold — which produces a switch that is
 * correct in colour and still unmistakably a Material switch in shape, weight
 * and travel. Everything underneath is the platform's, including the
 * `Role.Switch` a screen reader reads and the on/off state it announces.
 */
@Composable
fun AlmaToggle(
    on: Boolean,
    onChange: (Boolean) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
) {
    val knob by animateDpAsState(
        targetValue = if (on) 25.dp else 3.dp,
        animationSpec = tween(AlmaMotion.Ui, easing = AlmaMotion.UiEasing),
        label = "knob",
    )

    // Every colour below is the web's `.toggle` rule, line for line, and every
    // one of them was subtly off.
    //
    // The off knob was `Body` at 55 %, which measures #8A8886 on a device — a
    // neutral grey, and there is no grey anywhere in Alma's palette. On the
    // birth-time step every other control is hand-built and correct, so the one
    // toolkit-looking widget was exactly where the eye went. The web uses `Body`
    // at full opacity.
    //
    // The border was ours and the web sets `border: 0` explicitly, which is the
    // no-boxes rule applied to the one control that would most easily have got
    // an outline by default.
    //
    // The track was `Veil` (Body at 7 %) against the web's 14 %, and the on
    // track was `Gold` at 85 % against `GoldDeep` — the aged gold rather than a
    // faded bright one.
    Box(
        modifier = modifier
            .width(52.dp)
            .height(30.dp)
            .background(
                color = if (on) AlmaPalette.GoldDeep else AlmaPalette.Body.copy(alpha = 0.14f),
                shape = PillShape,
            )
            .toggleable(value = on, role = Role.Switch, onValueChange = onChange)
            .semantics { contentDescription = label },
        contentAlignment = Alignment.CenterStart,
    ) {
        Spacer(
            Modifier
                .padding(start = knob)
                .size(24.dp)
                .background(
                    color = if (on) AlmaPalette.InkOnGold else AlmaPalette.Body,
                    shape = CircleShape,
                )
        )
    }
}

/* ── the portrait's chips ──────────────────────────────────────────────── */

/** A calculated placement, set in the serif. Gold on a gold veil, never a border. */
@Composable
fun CalculatedPill(text: String, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .background(AlmaPalette.Gold.copy(alpha = 0.12f), PillShape)
            .padding(horizontal = 13.dp, vertical = 7.dp),
    ) {
        Text(
            text = text,
            style = AlmaTheme.type.positions.copy(fontSize = 14.sp, lineHeight = 18.sp),
        )
    }
}
