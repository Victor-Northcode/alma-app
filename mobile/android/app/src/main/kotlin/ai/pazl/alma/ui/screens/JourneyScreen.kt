package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.ui.components.Hairline
import ai.pazl.alma.ui.sky.AuraTone
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaFonts
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaSpacing
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.runtime.getValue
import androidx.compose.ui.graphics.graphicsLayer
import ai.pazl.alma.ui.theme.AlmaMotion
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlin.math.min

/**
 * The onboarding journey: everything before the cabinet, as one screen.
 *
 * Eight steps — the intent, a name, the date, the time, the place, a ceremony, a
 * portrait and the handoff — over one continuous sky. They share one piece of
 * in-progress state that has no meaning outside the flow, which is why they are
 * steps rather than routes, and why `back` from the fourth question goes to the
 * third instead of leaving.
 *
 * ## The two rules this flow was rewritten over on the web, before it existed here
 *
 * **No field starts pre-filled.** The reference chart's birthday used to sit in
 * every visitor's form. It read as a kindness, and it meant the first thing the
 * product ever said about somebody was calculated from a stranger.
 *
 * **The portrait hands over real value before any price is named.** The
 * calculations are free forever — the ephemeris is a static file on the server
 * and they cost us nothing — so the person is *given* their life path, their
 * card and their moon phase, and only then shown an offer. An offer that arrives
 * before anything has been handed over is a toll.
 *
 * ## One sky for the whole journey
 *
 * [NightSky] is composed once, outside the step, with one seed. Giving each step
 * its own would regenerate the starfield at every tap and the sky would visibly
 * jump — which breaks the rule the sky exists to serve: the sky moves, the UI
 * doesn't. What changes between steps is the art in front of it.
 */
@Composable
fun JourneyScreen(
    container: AppContainer,
    startStep: Int,
    onFinished: () -> Unit,
    onOffer: (String) -> Unit,
) {
    val vm: JourneyViewModel = viewModel {
        JourneyViewModel(container.client, container.session)
    }

    // The route's argument, handed over once. `open` is idempotent, so a
    // configuration change does not throw somebody back to the step they
    // arrived on after they have walked past it.
    LaunchedEffect(startStep) { vm.open(startStep) }

    val step by vm.step.collectAsStateWithLifecycle()
    val draft by vm.draft.collectAsStateWithLifecycle()

    BackHandler(enabled = step.canGoBack) { vm.back() }

    NightSky(config = JourneySky) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .widthIn(max = 520.dp)
                .align(Alignment.TopCenter)
                // The content clears the status bar; the sky behind it does
                // not, because the scaffold is full-bleed now. `safeDrawing`
                // covers a cutout as well as the bar.
                .windowInsetsPadding(WindowInsets.safeDrawing)
                .padding(horizontal = AlmaSpacing.Pad)
                .padding(bottom = 28.dp),
        ) {
            JourneyHeader(step = step, onBack = vm::back)

            when (step) {
                JourneyStep.Name -> NameStep(draft, vm::setName, vm::next)
                JourneyStep.About -> AboutStep(draft, vm::setGender, vm::next)
                JourneyStep.Date -> DateStep(draft, vm)
                JourneyStep.Time -> TimeStep(draft, vm)
                JourneyStep.Place -> PlaceStep(vm)
                // The last step: the ceremony computes everything under its
                // animation and lands straight in My Systems.
                JourneyStep.Ceremony -> CeremonyStep(onBegin = vm::beginCeremony, onDone = onFinished)
            }
        }
    }
}

/**
 * The sky the whole journey stands on.
 *
 * A denser field than the cabinet's and two auras, because these screens are
 * mostly sky with a question on them rather than mostly text. `SkyConfig.Reader`
 * is the other end of the same dial and belongs on a chapter.
 */
private val JourneySky = SkyConfig(
    seed = 5,
    starDensity = 1.3f,
    motes = 3,
    comet = true,
    auras = listOf(
        SkyConfig.Aurora(AuraTone.Indigo, centerX = 0.28f, centerY = 0.18f, radius = 0.85f),
        SkyConfig.Aurora(AuraTone.Deep, centerX = 0.84f, centerY = 0.80f, radius = 0.60f),
    ),
)

/* ── the chrome above every step ───────────────────────────────────────── */

/**
 * Where you are, and the way back.
 *
 * The count is *derived* from the step list. A hard-coded "/ VIII" is a number
 * that quietly starts lying the day a step is added, and on the web that had
 * already happened once.
 */
@Composable
private fun JourneyHeader(step: JourneyStep, onBack: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(top = 20.dp, bottom = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Row {
            Text(text = romanNumeral(step.ordinal + 1), style = CountStyle)
            Text(
                text = " / ${romanNumeral(JourneyStep.entries.size)}",
                style = CountStyle.copy(color = AlmaPalette.Muted3),
            )
        }

        when {
            step.canGoBack -> {
                val label = stringResource(R.string.nav_back)
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clickable(role = Role.Button, onClick = onBack)
                        // The glyph is decoration; this is the word that is read
                        // out, and it is why the arrow below clears its own.
                        .semantics { contentDescription = label },
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = "←",
                        style = TextStyle(fontSize = 19.sp, color = AlmaPalette.Muted),
                        modifier = Modifier.clearAndSetSemantics { },
                    )
                }
            }

            // The first step and the ceremony have nothing to go back to. The
            // system back gesture still leaves the app from the first step,
            // which is the right destination when there is no landing page in
            // front of this one.
            else -> Spacer(Modifier.size(44.dp))
        }
    }
}

/* ── the shape every question has ──────────────────────────────────────── */

/**
 * Art, a title, and controls pinned to the bottom.
 *
 * ## The art gives up height before the question does
 *
 * This is the whole of the layout and it was the other way round. The scene used
 * to be a scrolling column holding an art box of fixed height — `min(ideal, 40 %
 * of the *window*)`, transcribed from the web's `max-height: 40vh` — with the
 * title below it. Inside a `verticalScroll` a child has unbounded height to grow
 * into, so the art always took its full share whatever was left, and the title
 * was simply cut off at the viewport edge.
 *
 * German found it on step one. `Etwas verschiebt sich und ich weiß nicht warum`
 * wraps to two lines, the controls column grew by that line, the weighted scroll
 * column lost the same height, and `Was ist gerade am / lautesten in dir?`
 * rendered with the top 40 % of its second line and nothing else. It reads as a
 * rendering fault rather than as "scroll me": the clip lands mid-glyph and
 * nothing indicates the column moves. English at font scale 1.15 had about 25 dp
 * of slack, so it was one accessibility step from the same failure.
 *
 * So the order of measurement is now the order of importance. The title column
 * is unweighted and is measured first, against the space actually available; the
 * art is `weight(1f, fill = false)` and takes whatever is left, up to its ideal.
 * The 40 %-of-window cap is gone because it was a guess at "the space that
 * remains" and the weight is that number rather than an estimate of it.
 *
 * The title keeps a `verticalScroll` of its own for the extreme case — a title
 * taller than the whole scene, which needs about font scale 2 — so the last
 * thing that can ever be truncated is the question being asked.
 *
 * The controls do not scroll, and that has not changed. Somebody who has to
 * scroll to find the button is somebody who has not seen it.
 */
@Composable
internal fun ColumnScope.JourneyScene(
    artHeight: Dp,
    art: @Composable BoxScope.() -> Unit,
    title: String?,
    sub: String? = null,
    /**
     * Whether the keyboard is up on this step.
     *
     * **The art shrinks instead of being run over.** With the keyboard open on
     * the place step the controls grow by a field and four suggestions, and the
     * pinned block climbed over the picture: the owner's screenshot showed the
     * globe with a list of cities across the middle of it, and his instruction
     * was that everything should move together rather than one thing sliding
     * under another. iOS carries the same flag and the same numbers.
     */
    keyboardUp: Boolean = false,
    controls: @Composable ColumnScope.() -> Unit,
) {
    val artScale by animateFloatAsState(
        if (keyboardUp) 0.34f else 1f,
        animationSpec = tween(AlmaMotion.Ui, easing = AlmaMotion.UiEasing),
        label = "journey-art",
    )
    Column(
        modifier = Modifier
            .weight(1f)
            .fillMaxWidth(),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                // `fill = false` matters: it lets the art be *smaller* than its
                // share when its ideal height is less than the space left, which
                // is the ordinary case on a tall phone.
                .weight(1f, fill = false)
                .heightIn(max = artHeight * artScale)
                .graphicsLayer { alpha = 0.55f + 0.45f * ((artScale - 0.34f) / 0.66f) },
            contentAlignment = Alignment.Center,
            content = art,
        )
        if (title != null) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 4.dp),
            ) {
                Text(text = title, style = JourneyTitleStyle)
                if (sub != null) {
                    Text(
                        text = sub,
                        style = JourneySubStyle,
                        modifier = Modifier.padding(top = 12.dp),
                    )
                }
            }
        }
    }

    Column(
        modifier = Modifier.fillMaxWidth().padding(top = 24.dp),
        verticalArrangement = Arrangement.spacedBy(11.dp),
        content = controls,
    )
}

/* ── the type this flow uses, named once ───────────────────────────────── */

internal val JourneyTitleStyle = TextStyle(
    fontFamily = AlmaFonts.Display,
    fontSize = 30.sp,
    lineHeight = 34.sp,
    color = AlmaPalette.InkLight,
)

internal val JourneySubStyle = TextStyle(
    fontFamily = AlmaFonts.Sans,
    fontSize = 15.sp,
    lineHeight = 24.sp,
    color = AlmaPalette.Muted2,
)

private val CountStyle = TextStyle(
    fontFamily = AlmaFonts.Display,
    fontSize = 13.sp,
    letterSpacing = 0.2.em,
    color = AlmaPalette.Gold.copy(alpha = 0.8f),
)

private val Numerals = listOf("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")

/** Roman numerals, as far as this product ever counts. */
internal fun romanNumeral(value: Int): String =
    Numerals.getOrElse(value - 1) { value.toString() }

/** The fine print under a control: 13 sp, half-lit, centred by default. */
@Composable
internal fun FinePrint(
    text: String,
    modifier: Modifier = Modifier,
    align: TextAlign = TextAlign.Center,
) {
    Text(
        text = text,
        modifier = modifier.fillMaxWidth(),
        textAlign = align,
        style = TextStyle(
            fontFamily = AlmaFonts.Sans,
            fontSize = 13.sp,
            lineHeight = 20.sp,
            color = AlmaPalette.Body.copy(alpha = 0.5f),
        ),
    )
}

/**
 * Something is wrong with what was just entered.
 *
 * The disagreement red, which is also the error colour: a contradiction is
 * material rather than a fault here, and the product never shouts.
 */
@Composable
internal fun Problem(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text,
        modifier = modifier.fillMaxWidth().heightIn(min = 20.dp),
        style = TextStyle(
            fontFamily = AlmaFonts.Sans,
            fontSize = 13.5.sp,
            lineHeight = 20.sp,
            color = AlmaPalette.Disagree,
        ),
    )
}

/** What separates content here, since there are no cards to separate with. */
@Composable
internal fun SceneRule(modifier: Modifier = Modifier) {
    Hairline(modifier.padding(vertical = 22.dp))
}
