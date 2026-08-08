package ai.pazl.alma.ui.sky

import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.rememberReducedMotion
import android.graphics.Bitmap
import androidx.compose.animation.core.InfiniteTransition
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.State
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.ImageShader
import androidx.compose.ui.graphics.ShaderBrush
import androidx.compose.ui.graphics.TileMode
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.clearAndSetSemantics
import kotlin.math.PI
import kotlin.math.sin
import kotlin.random.Random

/**
 * The ambient sky.
 *
 * "The sky moves, the UI doesn't" is one of the five rules and this file is the
 * whole of the moving half. Everything here is *drawn* — no images, no Lottie,
 * no shipped assets — for two reasons that both turned out to matter: a
 * starfield as a PNG has to exist at four densities and still bands against
 * this navy, and a drawn field can be seeded per screen so that no two screens
 * show the same stars while every screen shows the same kind of sky.
 *
 * Three things move and there is a hard budget on each, taken from the web
 * app's own comment: **two star layers, at most three motes, one comet, at most
 * two auras.** The budget is a taste limit rather than a performance one. A sky
 * with six comets in it is a screensaver.
 *
 * ## Cost
 *
 * Every layer drives exactly **one** animated float. Forty-four stars twinkling
 * out of phase are forty-four `sin` calls inside a single draw pass, not
 * forty-four animations — the difference between one invalidation per frame and
 * forty-four. Nothing here allocates while drawing.
 *
 * ## Reduced motion
 *
 * Honoured by *not creating the animation*, not by animating to nowhere. When
 * the device asks for stillness the stars are drawn once at a fixed opacity and
 * the motes and the comet are not composed at all, so there is no frame clock
 * subscription left running behind a screen that is supposed to be still.
 */

/* ── the field ─────────────────────────────────────────────────────────── */

@Immutable
private data class Star(
    val x: Float,
    val y: Float,
    /** In dp. Stars are the same size on every density, like type. */
    val radius: Float,
    val color: Color,
    /** Where in its own twinkle this star starts, so the field never pulses in unison. */
    val phase: Float,
)

/**
 * Star colours in the proportion the CSS uses: mostly near-white, some warm
 * ivory, a few in the aged gold itself. A field of one colour reads as a
 * texture; three colours reads as a sky.
 */
private val StarColours = listOf(
    Color(0xFFFFF8E6), Color(0xFFFFF8E6), Color(0xFFFFF8E6),
    Color(0xFFE6D9B4), Color(0xFFE6D9B4),
    AlmaPalette.Gold,
)

private fun field(seed: Int, count: Int, minRadius: Float, maxRadius: Float): List<Star> {
    val random = Random(seed)
    return List(count) {
        Star(
            x = random.nextFloat(),
            y = random.nextFloat(),
            radius = minRadius + random.nextFloat() * (maxRadius - minRadius),
            color = StarColours[random.nextInt(StarColours.size)],
            phase = random.nextFloat(),
        )
    }
}

/**
 * Two layers of stars, twinkling out of phase.
 *
 * The near layer is brighter and larger and breathes over six seconds; the far
 * layer is dimmer, smaller and takes nine. Both numbers are the CSS's, and the
 * gap between them is what stops the field reading as one flashing sheet.
 *
 * @param seed distinct per screen. Two screens sharing a seed share a sky,
 *   which is right for a pair that should feel continuous and wrong for two
 *   screens a person navigates between.
 * @param density scales the star count. Below 1 for a screen that is mostly
 *   text; above it for a screen that is mostly sky.
 */
@Composable
fun Starfield(
    modifier: Modifier = Modifier,
    seed: Int = 0,
    density: Float = 1f,
) {
    val stars = rememberStars(seed, density)

    if (rememberReducedMotion()) {
        Canvas(modifier.sky()) { drawStarfield(stars, nearPhase = null, farPhase = null) }
        return
    }
    val transition = rememberInfiniteTransition(label = "starfield")
    val near = transition.turns(6_000, label = "near")
    val far = transition.turns(9_000, label = "far")
    Canvas(modifier.sky()) { drawStarfield(stars, near.value, far.value) }
}

/** The two layers, generated once and shared by the fused and standalone paths. */
@Composable
private fun rememberStars(seed: Int, density: Float): Pair<List<Star>, List<Star>> =
    remember(seed, density) {
        field(seed, (26 * density).toInt(), 1.0f, 1.7f) to
            field(seed + 977, (18 * density).toInt(), 0.7f, 1.1f)
    }

/**
 * Draw both layers. A null phase means "still" — the stars stay, because they
 * are the canvas rather than the animation, pinned at the 0.6 the CSS uses in
 * the same situation, and only the twinkle goes.
 */
private fun DrawScope.drawStarfield(
    stars: Pair<List<Star>, List<Star>>,
    nearPhase: Float?,
    farPhase: Float?,
) {
    if (nearPhase == null || farPhase == null) {
        drawStars(stars.first, phase = 0f, floor = 0.60f, ceiling = 0.60f)
        drawStars(stars.second, phase = 0f, floor = 0.34f, ceiling = 0.34f)
    } else {
        drawStars(stars.first, nearPhase, floor = 0.25f, ceiling = 1.00f)
        drawStars(stars.second, farPhase, floor = 0.12f, ceiling = 0.50f)
    }
}

private fun DrawScope.drawStars(stars: List<Star>, phase: Float, floor: Float, ceiling: Float) {
    stars.forEach { star ->
        // 0.25 → 1 → 0.25, the `twinkle` keyframe exactly. A sine rather than a
        // triangle wave, because a linear fade in and out reads mechanical at
        // this size.
        val alpha = if (floor == ceiling) {
            floor
        } else {
            val t = (phase + star.phase) % 1f
            floor + (ceiling - floor) * (0.5f + 0.5f * sin(t * TAU - HALF_PI))
        }
        drawCircle(
            color = star.color,
            radius = px(star.radius),
            center = Offset(star.x * size.width, star.y * size.height),
            alpha = alpha,
        )
    }
}

/* ── dust ──────────────────────────────────────────────────────────────── */

/**
 * Drifting motes: a few specks rising and fading over fourteen seconds.
 *
 * Three is the maximum and the default, and the cap is enforced rather than
 * documented. The rule is in the web app's own comment and it is about
 * restraint rather than cost — dust you can count is atmosphere, dust you
 * cannot is snow.
 */
@Composable
fun Motes(
    modifier: Modifier = Modifier,
    count: Int = 3,
    seed: Int = 0,
    color: Color = AlmaPalette.StarFill,
) {
    if (rememberReducedMotion()) return

    val specks = rememberSpecks(seed, count)
    if (specks.isEmpty()) return

    val phase = rememberInfiniteTransition(label = "motes").turns(14_000, label = "drift")
    Canvas(modifier.sky()) { drawMotes(specks, phase.value, color) }
}

@Composable
private fun rememberSpecks(seed: Int, count: Int): List<Triple<Float, Float, Float>> =
    remember(seed, count) {
        val random = Random(seed + 4211)
        List(count.coerceIn(0, 3)) {
            Triple(random.nextFloat(), 0.55f + random.nextFloat() * 0.4f, random.nextFloat())
        }
    }

private fun DrawScope.drawMotes(
    specks: List<Triple<Float, Float, Float>>,
    phase: Float,
    color: Color,
) {
    val rise = px(120f)
    specks.forEach { (x, y, offset) ->
        val t = (phase + offset) % 1f
        // The `dust` keyframe: in over the first fifth, out over the last fifth,
        // and a long plateau between them at slightly less than the peak —
        // which is what makes a speck read as passing rather than blinking.
        val alpha = when {
            t < 0.20f -> t / 0.20f * 0.7f
            t < 0.80f -> 0.7f - (t - 0.20f) / 0.60f * 0.2f
            else -> 0.5f * (1f - (t - 0.80f) / 0.20f)
        }
        drawCircle(
            color = color,
            radius = px(1f),
            center = Offset(x * size.width, y * size.height - t * rise),
            alpha = alpha,
        )
    }
}

/* ── the comet ─────────────────────────────────────────────────────────── */

/**
 * One comet, once every eighteen seconds, and never two on a screen.
 *
 * It is a gradient line rather than a head with a tail, rotated 34° and
 * travelling down and to the right. The opacity keyframes matter more than the
 * path: it is invisible for the first 8 % and the last 40 % of the cycle, so
 * what a person sees is a streak that appears, crosses and is gone — about
 * seven seconds of movement inside an eighteen-second cycle. A comet that is
 * always somewhere on screen is a loading spinner.
 */
@Composable
fun Comet(
    modifier: Modifier = Modifier,
    startX: Float = 0.14f,
    startY: Float = 0.12f,
    lengthDp: Float = 180f,
    durationMillis: Int = 18_000,
    delayMillis: Int = 0,
) {
    if (rememberReducedMotion()) return

    val t = rememberInfiniteTransition(label = "comet")
        .turns(durationMillis, delayMillis = delayMillis, label = "travel")

    Canvas(modifier.sky()) { drawComet(t.value, startX, startY, lengthDp) }
}

private fun DrawScope.drawComet(progress: Float, startX: Float, startY: Float, lengthDp: Float) {
    val alpha = when {
        progress < 0.08f -> progress / 0.08f * 0.9f
        progress < 0.42f -> 0.9f
        progress < 0.60f -> 0.9f * (1f - (progress - 0.42f) / 0.18f)
        else -> 0f
    }
    // Sixty per cent of every cycle costs nothing at all, which is most of what
    // makes one comet cheap enough to be on every screen.
    if (alpha <= 0.01f) return

    // The CSS travels (-60,-40) → (420,300) in CSS pixels. Held in dp here,
    // which is the same distance on a phone and the right one on a tablet: a
    // comet crossing a fixed *fraction* of the screen would be twice as fast on
    // a large one.
    val travel = (progress / 0.60f).coerceIn(0f, 1f)
    val x = startX * size.width + px(lerp(-60f, 420f, travel))
    val y = startY * size.height + px(lerp(-40f, 300f, travel))
    val length = px(lengthDp)

    translate(x, y) {
        rotate(degrees = 34f, pivot = Offset.Zero) {
            drawRect(
                brush = Brush.horizontalGradient(
                    colors = listOf(Color.Transparent, AlmaPalette.StarFill.copy(alpha = 0.8f)),
                    startX = 0f,
                    endX = length,
                ),
                topLeft = Offset.Zero,
                size = Size(length, px(1f)),
                alpha = alpha,
            )
        }
    }
}

/* ── auras ─────────────────────────────────────────────────────────────── */

/**
 * Which coloured light a blob is.
 *
 * Three, and there was a fourth. `Violet` was `Color(0x574A3A9E)` — hue ~250°,
 * far more saturated than `Indigo` (#1B244A) or `IndigoBright` (#2E3C6E), which
 * is to say a purple rather than a deep night blue. No screen selected it, and
 * that is exactly why it was worth deleting rather than leaving: "one gold,
 * aged — never a second accent" is a palette rule, and a named, ready-to-use
 * violet sitting in the sky API is how a second accent gets introduced by a
 * future screen author acting entirely in good faith. It is the same colour
 * family as the Capricorn emoji-disc that was already caught and fixed once on
 * the portrait.
 *
 * If a fourth tone is ever genuinely needed, derive it from [AlmaPalette.IndigoDeep]
 * so it stays inside the night rather than beside it.
 */
enum class AuraTone { Indigo, Deep, Gold }

/**
 * A soft coloured light behind the content.
 *
 * The CSS blurs a filled circle by 34 px. This draws a radial gradient with the
 * falloff already in the stops, which is not a shortcut: `Modifier.blur` is a
 * no-op below API 31, so a real blur would have shown half our install base a
 * hard circle of indigo sitting behind the copy.
 *
 * The rule the web app holds to and this inherits: **never behind body copy.**
 * An aura goes behind a heading, under the mark, off the edge of the screen. It
 * does not go under a paragraph somebody has to read.
 */
@Composable
fun Aura(
    modifier: Modifier = Modifier,
    tone: AuraTone = AuraTone.Indigo,
    /** Centre as a fraction of the box; values outside 0..1 push it off-screen. */
    centerX: Float = 0.5f,
    centerY: Float = 0.5f,
    /** Radius as a fraction of the box's smaller side. */
    radius: Float = 0.64f,
    drift: Boolean = true,
) {
    val stops = remember(tone) { tone.stops() }
    val moving = drift && !rememberReducedMotion()

    // Thirty seconds there and thirty back. Slow enough that it is never caught
    // moving, large enough that a screenshot and the live screen are visibly
    // different things.
    val wander: State<Float>? = if (moving) {
        rememberInfiniteTransition(label = "aura")
            .turns(30_000, repeatMode = RepeatMode.Reverse, label = "wander")
    } else {
        null
    }

    Canvas(
        modifier
            .sky()
            // **The drift is a layer translation, not a redraw**, and this is the
            // single most expensive thing in the file if it is got wrong.
            //
            // The obvious version recomputes the gradient's centre each frame
            // and calls `drawCircle` with a new `Brush.radialGradient`. That
            // re-rasterises a full-screen radial gradient sixty times a second,
            // for a movement of three per cent that takes half a minute — and
            // with two auras on a screen it was, measurably, most of the frame.
            //
            // A drift *is* a translation, so it belongs in `graphicsLayer`: the
            // gradient is rasterised once into a layer and afterwards the
            // compositor only moves it. Identical on screen, and the draw below
            // stops depending on the animation at all.
            //
            // Reading `wander` inside the lambda rather than outside is the
            // other half: `graphicsLayer` with a lambda defers the read to the
            // draw phase, so a new frame never invalidates composition or
            // layout.
            //
            // `clip = true` because a `graphicsLayer` does not clip by default
            // and this one is *translated*: the gradient was drawing outside its
            // own layout bounds, into whatever the parent had not covered. What
            // that produced in practice was a lighter band with a hard edge
            // across the top of several screens, in the strip the navigation
            // host's inset padding left uncovered — the aura leaking upward and
            // reading as a top app bar.
            .graphicsLayer {
                clip = true
                val drifted = wander?.value ?: 0.5f
                translationX = (drifted - 0.5f) * 0.06f * size.width
                translationY = (0.5f - drifted) * 0.08f * size.height
            }
    ) {
        val r = radius * minOf(size.width, size.height)
        val centre = Offset(centerX * size.width, centerY * size.height)
        drawCircle(
            brush = Brush.radialGradient(colorStops = stops, center = centre, radius = r),
            radius = r,
            center = centre,
        )
    }
}

private fun AuraTone.stops(): Array<Pair<Float, Color>> = when (this) {
    AuraTone.Indigo -> arrayOf(
        0.00f to AlmaPalette.IndigoBright.copy(alpha = 0.42f),
        0.44f to AlmaPalette.Indigo.copy(alpha = 0.22f),
        0.70f to Color.Transparent,
        1.00f to Color.Transparent,
    )
    AuraTone.Deep -> arrayOf(
        0.00f to AlmaPalette.IndigoDeep.copy(alpha = 0.38f),
        0.70f to Color.Transparent,
        1.00f to Color.Transparent,
    )
    AuraTone.Gold -> arrayOf(
        0.00f to AlmaPalette.Gold.copy(alpha = 0.20f),
        0.66f to Color.Transparent,
        1.00f to Color.Transparent,
    )
}

/* ── grain ─────────────────────────────────────────────────────────────── */

/**
 * Film grain over everything, at 26 %, blended `Overlay`.
 *
 * The cheapest thing in the file and the one that does the most work: a flat
 * navy on an OLED panel bands visibly across a large gradient, and grain is
 * what breaks the bands up.
 *
 * Draw it **last**, above the content, the way `.grain` sits at z-index 60 in
 * the web app. Grain under the type looks like a dirty screen; grain over it
 * looks like film.
 */
@Composable
fun Grain(modifier: Modifier = Modifier, alpha: Float = 0.26f) {
    val brush = rememberGrainBrush()
    Canvas(modifier.sky()) {
        drawRect(brush = brush, alpha = alpha, blendMode = BlendMode.Overlay)
    }
}

@Composable
private fun rememberGrainBrush(): ShaderBrush = remember {
    ShaderBrush(ImageShader(noiseTile(), TileMode.Repeated, TileMode.Repeated))
}

/**
 * A 160 × 160 tile of monochrome noise.
 *
 * Fixed seed on purpose: a tile that differed between launches would make two
 * screenshots of one screen differ, and there is nothing to buy with that.
 * `ARGB_8888` rather than the smaller `ALPHA_8` because `Overlay` needs a
 * colour to blend against — an alpha-only tile darkens rather than textures.
 */
private fun noiseTile(size: Int = 160): ImageBitmap {
    val random = Random(0x5EED)
    val pixels = IntArray(size * size) {
        val v = 96 + random.nextInt(64)
        (0xFF shl 24) or (v shl 16) or (v shl 8) or v
    }
    return Bitmap.createBitmap(pixels, size, size, Bitmap.Config.ARGB_8888).asImageBitmap()
}

/* ── the whole sky, composed ───────────────────────────────────────────── */

/** What a screen asks for when it wants "the usual sky, but mine". */
@Immutable
data class SkyConfig(
    val seed: Int = 0,
    val stars: Boolean = true,
    val starDensity: Float = 1f,
    val motes: Int = 3,
    val comet: Boolean = true,
    val auras: List<Aurora> = listOf(Aurora(AuraTone.Indigo, 0.18f, 0.10f, 0.72f)),
    val grain: Boolean = true,
) {
    @Immutable
    data class Aurora(
        val tone: AuraTone,
        val centerX: Float,
        val centerY: Float,
        val radius: Float,
        val drift: Boolean = true,
    )

    companion object {
        /** A reading screen: fewer stars, no comet, nothing behind the words. */
        val Reader: SkyConfig = SkyConfig(
            starDensity = 0.45f,
            motes = 1,
            comet = false,
            auras = emptyList(),
        )

        /** The ceremony and the portrait: everything on. */
        val Ceremony: SkyConfig = SkyConfig(
            starDensity = 1.4f,
            auras = listOf(
                Aurora(AuraTone.Indigo, 0.30f, 0.22f, 0.85f),
                Aurora(AuraTone.Deep, 0.82f, 0.78f, 0.60f),
            ),
        )
    }
}

/**
 * The night canvas with its sky on it and the screen's content above.
 *
 * Every screen in the cabinet and every step of the journey sits inside one of
 * these. Layer order is the contract: auras, stars, motes, comet, **content**,
 * grain. Content above the sky and below the grain is what lets text stay
 * legible over a moving background without a scrim over the whole screen.
 *
 * At most two auras are drawn however many are passed. The budget is enforced
 * here rather than trusted to callers, because "just one more light" is exactly
 * the change that gets made on one screen and then copied to eight.
 */
@Composable
fun NightSky(
    modifier: Modifier = Modifier,
    config: SkyConfig = SkyConfig(),
    content: @Composable BoxScope.() -> Unit,
) {
    Box(modifier.fillMaxSize()) {
        // **The night, first and on its own.**
        //
        // This used to be the opening `drawRect` inside `FusedSky`, which sat
        // *below* the auras in source and therefore *above* them on screen —
        // an opaque `Night800` painted straight over every aura in the app. The
        // measured result was a background that was flat #0A0D1C at every point
        // of every screen, and the only aura pixels that reached a display were
        // the ones drifting out of bounds into the status-bar strip, where they
        // read as a lighter indigo header band with a hard edge: a Material top
        // bar by any other name, on a design whose first rule is that there are
        // no boxes.
        //
        // It moved rather than being deleted because it still has to exist:
        // without it the auras composite against whatever the window happens to
        // be. The fusion below keeps everything it was for — the stars, the
        // motes and the comet are still one draw — and only the fill left.
        Canvas(Modifier.sky()) { drawRect(AlmaPalette.Night800) }

        // Auras keep their own layers, because each is a cached raster that is
        // only translated — see the comment in [Aura]. Merging them into the
        // canvas below would put the gradient back in the per-frame path, which
        // is the opposite of what is wanted.
        config.auras.take(2).forEach { aura ->
            Aura(
                tone = aura.tone,
                centerX = aura.centerX,
                centerY = aura.centerY,
                radius = aura.radius,
                drift = aura.drift,
            )
        }

        // Stars, dust and the comet in **one** draw.
        //
        // They were three full-screen composables to begin with, which is three
        // layers to allocate and composite every frame for what amounts to
        // fifty circles and a rect. They are fused here — and only here — while
        // `Starfield`, `Motes` and `Comet` stay usable on their own for a screen
        // that wants one without the others. The shared `drawX` functions mean
        // the two paths cannot drift apart.
        FusedSky(config)

        content()

        // Above the content, always. Grain under the type looks like a dirty
        // screen; grain over it looks like film.
        if (config.grain) Grain()
    }
}

@Composable
private fun FusedSky(config: SkyConfig) {
    val stars = if (config.stars) rememberStars(config.seed, config.starDensity) else null
    val specks = if (config.motes > 0) rememberSpecks(config.seed, config.motes) else emptyList()
    val still = rememberReducedMotion()

    if (still) {
        // No transition is created at all, so nothing subscribes to the frame
        // clock and an idle screen renders exactly zero frames. Animating to
        // nowhere would have kept the whole pipeline awake.
        //
        // No `drawRect` here either: the night is drawn by `NightSky`, under
        // the auras. It was drawn twice, and the second one was opaque.
        Canvas(Modifier.sky()) {
            stars?.let { drawStarfield(it, null, null) }
        }
        return
    }

    val transition = rememberInfiniteTransition(label = "sky")
    val near = transition.turns(6_000, label = "near")
    val far = transition.turns(9_000, label = "far")
    val drift = transition.turns(14_000, label = "drift")
    // The delay staggers the comet per screen, so tabbing between two of them
    // does not restart the same streak from the same place twice.
    val comet = transition.turns(
        18_000,
        delayMillis = (config.seed % 5) * 1_400,
        label = "comet",
    )

    Canvas(Modifier.sky()) {
        stars?.let { drawStarfield(it, near.value, far.value) }
        if (specks.isNotEmpty()) drawMotes(specks, drift.value, AlmaPalette.StarFill)
        if (config.comet) drawComet(comet.value, startX = 0.14f, startY = 0.12f, lengthDp = 180f)
    }
}

/* ── small things ──────────────────────────────────────────────────────── */

private const val TAU = (2.0 * PI).toFloat()
private const val HALF_PI = (PI / 2.0).toFloat()

/** Everything in this file is decoration; none of it is worth announcing. */
private fun Modifier.sky(): Modifier = this
    .fillMaxSize()
    .clearAndSetSemantics { }

/**
 * A 0 → 1 ramp that repeats forever, which is all any of these layers needs.
 * Linear on purpose: the easing lives in the keyframe maths, where it can
 * differ per layer, rather than in the driver, where it could not.
 */
@Composable
private fun InfiniteTransition.turns(
    durationMillis: Int,
    delayMillis: Int = 0,
    repeatMode: RepeatMode = RepeatMode.Restart,
    label: String,
): State<Float> = animateFloat(
    initialValue = 0f,
    targetValue = 1f,
    animationSpec = infiniteRepeatable(
        animation = tween(durationMillis, delayMillis = delayMillis, easing = LinearEasing),
        repeatMode = repeatMode,
    ),
    label = label,
)

private fun DrawScope.px(dp: Float): Float = dp * density

private fun lerp(from: Float, to: Float, t: Float): Float = from + (to - from) * t
