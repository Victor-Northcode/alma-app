package ai.pazl.alma.ui.components

import ai.pazl.alma.BuildConfig
import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import android.content.Context
import android.graphics.BitmapFactory
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * Which plate opens which chapter.
 *
 * Ported from `mobile/flutter/alma/lib/design/plates.dart`, which is the map the
 * owner dictated and the one checked against the disk: thirty-five names, none
 * spare, none missing. The keys are the chapter slugs from
 * `backend/alma/ai/chapters.py`, the only source of truth about chapters.
 *
 * **Six holes are marked `null` honestly.** The art for them has not been drawn;
 * until it is, the chapter opens on an arch with its Roman numeral rather than
 * on somebody else's picture. A wrong plate is not a crooked margin — it is a
 * picture about something other than what the reader is reading, on a chapter
 * they paid for. One placeholder is live: `life-path` borrows another plate, and
 * that is written down in `docs/plates-map.md` beside the prompt that replaces it.
 */
object AlmaPlates {

    private val map: Map<String, Map<String, String?>> = mapOf(
        AlmaSystem.NATAL to mapOf(
            "core" to "plate-shape",
            "portrait" to "plate-face",
            "love" to "plate-love",
            "money" to "plate-money",
            "career" to "plate-calling",
            "mind" to "plate-speech",
            "shadow" to "plate-depths",
            "roots" to "plate-home",
            "karmic-axis" to "plate-repeats",
            "work-rhythms" to "plate-sun",
            "transformation" to "plate-crisis",
            "freedom" to "plate-freedom",
            "dreams" to "plate-dreams",
            "circle" to "plate-friends",
            "worldview" to "plate-faith",
            "milestones" to "plate-saturn",
        ),
        AlmaSystem.NUMEROLOGY to mapOf(
            // Placeholder: another chapter's plate until "the road" is drawn.
            // Recorded in docs/plates-map.md with the prompt that replaces it.
            "life-path" to "plate-soulurge",
            "birthday-number" to null,
            "personal-year" to "plate-year",
            "pinnacles" to "plate-eleven",
            "name" to "plate-expression",
        ),
        AlmaSystem.BIRTH_CARD to mapOf(
            "personality" to "plate-personality",
            "soul" to "plate-soulcard",
            "year-card" to "plate-yearcard",
        ),
        AlmaSystem.TRANSITS to mapOf(
            "active" to "plate-sky",
            "ahead" to null,
            "long" to null,
        ),
        AlmaSystem.SOLAR_RETURN to mapOf(
            "year-shape" to "plate-solar",
            "emphasis" to "plate-yeartheme",
            "contacts" to "plate-yearlesson",
        ),
        AlmaSystem.COMPATIBILITY to mapOf(
            "attraction" to "plate-pull",
            "friction" to "plate-catches",
            "overlays" to "plate-veil",
            "together" to "plate-tender",
        ),
        AlmaSystem.ASTROCARTOGRAPHY to mapOf(
            "lines" to "plate-lines",
            "here" to "plate-whereto",
            "crossings" to null,
        ),
        // Synthesis is the system "all of it together", and one picture across
        // its four chapters is a rule here rather than a hole: four different
        // paintings under "where the systems agree" and "where they part" would
        // be telling four stories instead of one.
        AlmaSystem.SYNTHESIS to mapOf(
            "agreement" to "plate-synthesis",
            "disagreement" to "plate-synthesis",
            "single" to "plate-synthesis",
            "whole" to "plate-synthesis",
        ),
    )

    /** The daily's plate. Not a chapter — it stands on Today. */
    const val TODAY = "plate-moon"

    fun name(system: String, chapter: String): String? = map[system]?.get(chapter)
}

/**
 * A plate, downloaded once and kept on disk until the app is reinstalled.
 *
 * The server promises `immutable` for a year and sends an ETag, and this cache
 * exists anyway, for the same reason the Flutter port's does: a hundred
 * kilobytes re-fetched every time a chapter opens is something the reader pays
 * for on mobile data, not us. Named files, and a name is never reused — a new
 * painting arrives under a new name — so there is nothing to invalidate, and the
 * absence of invalidation here is a consequence of that contract rather than an
 * oversight.
 *
 * No token goes out with these requests, deliberately. `api/plates.py` serves
 * them unauthenticated because the art is not about any particular person; an
 * authenticated image would need a header on every fetch and would defeat the
 * cache it is meant to protect.
 */
class PlateStore(
    context: Context,
    private val baseUrl: String = BuildConfig.API_BASE,
) {

    private val folder = File(context.filesDir, "plates")

    private val http: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(12, TimeUnit.SECONDS)
        .build()

    /**
     * The file for a plate, fetching it the first time it is wanted.
     *
     * `null` means there is no picture and there will not be one — the server
     * answered 404, or there is no network. Both are drawn the same way, with
     * the numeral, because to a reader they are the same thing.
     *
     * No in-flight table guards against two screens asking at once, and that is
     * a choice rather than an omission: the partial file is uniquely named, so
     * two racing fetches of the same plate write two temporary files and rename
     * both onto identical bytes. The cost is one wasted download in a case that
     * needs two chapters open at the same instant; the alternative is a map of
     * deferred results whose only failure mode — a cancelled winner nobody
     * releases — leaves a chapter shimmering for ever.
     */
    suspend fun file(name: String): File? {
        val target = File(folder, "$name.webp")
        if (target.isFile && target.length() > 0) return target
        return withContext(Dispatchers.IO) { download(name, target) }
    }

    private fun download(name: String, target: File): File? = runCatching {
        folder.mkdirs()
        val url = "${baseUrl.trimEnd('/')}/static/plates/$name.webp"
        http.newCall(Request.Builder().url(url).build()).execute().use { response ->
            val bytes = response.body?.bytes()
            if (!response.isSuccessful || bytes == null || bytes.isEmpty()) return@use null
            // Written aside and then renamed: an interrupted download must not
            // leave half a painting on disk for the next launch to mistake for
            // a whole one.
            val partial = File(folder, "$name.webp.${System.nanoTime()}.part")
            partial.writeBytes(bytes)
            if (partial.renameTo(target)) target else null.also { partial.delete() }
        }
    }.getOrNull()
}

/**
 * The arch: a chapter's painting in a frame with a rounded top.
 *
 * 85 above and 12 below, a gold edge and an inner stroke set in — the numbers
 * from the design canvas, the same ones the Flutter port draws. Three states,
 * and none of them is an empty hole:
 *
 * * loading — a parchment shimmer inside the arch, no spinner: a spinner says
 *   "wait", and there is almost nothing to wait for here;
 * * never arrived — the chapter's Roman numeral on parchment;
 * * arrived — a 260 ms fade.
 */
@Composable
fun PlateArch(
    /**
     * Where to fetch from. `null` goes straight to the fallback, which is what a
     * preview draws.
     */
    store: PlateStore?,
    /** The plate's file name, or `null` where the art has not been drawn yet. */
    plate: String?,
    /** The chapter's Roman numeral — what stands in the arch instead of a picture. */
    numeral: String,
    modifier: Modifier = Modifier,
    width: Dp = 150.dp,
    height: Dp = 188.dp,
) {
    var art by remember(plate) { mutableStateOf<ImageBitmap?>(null) }
    var settled by remember(plate) { mutableStateOf(false) }

    LaunchedEffect(plate, store) {
        if (store == null || plate == null) {
            settled = true
            return@LaunchedEffect
        }
        val file = store.file(plate)
        art = file?.let {
            withContext(Dispatchers.IO) {
                runCatching { BitmapFactory.decodeFile(it.path)?.asImageBitmap() }.getOrNull()
            }
        }
        settled = true
    }

    Box(modifier.size(width, height)) {
        Box(Modifier.fillMaxSize().clip(ArchShape)) {
            val bitmap = art
            when {
                bitmap != null -> Image(
                    bitmap = bitmap,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize().plateFade(),
                )
                settled -> Numeral(numeral)
                else -> Shimmer()
            }
        }
        // The edge and the inner stroke sit over the picture: the frame belongs
        // to the arch rather than to what is in it, and must not fade in with it.
        Box(
            Modifier
                .fillMaxSize()
                .border(1.dp, AlmaPalette.Gold.copy(alpha = 0.5f), ArchShape)
                .padding(5.5.dp)
                .border(1.dp, AlmaPalette.StarFill.copy(alpha = 0.4f), ArchShape)
                .clearAndSetSemantics { },
        )
    }
}

/** The top is a half circle across the width; the bottom is barely rounded. */
private val ArchShape = RoundedCornerShape(
    topStart = 75.dp,
    topEnd = 75.dp,
    bottomStart = 14.dp,
    bottomEnd = 14.dp,
)

/** 260 ms, the same reveal the port uses. */
@Composable
private fun Modifier.plateFade(): Modifier {
    var shown by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { shown = true }
    val fade by androidx.compose.animation.core.animateFloatAsState(
        targetValue = if (shown) 1f else 0f,
        animationSpec = tween(260),
        label = "plate-fade",
    )
    return this.alpha(fade)
}

/** The fallback: the chapter's numeral on parchment. */
@Composable
private fun Numeral(numeral: String) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.linearGradient(
                    0f to Color(0xFFEDE3CC),
                    0.6f to Color(0xFFEFE3C9),
                    1f to Color(0xFFDFD0AF),
                )
            ),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = numeral,
            style = AlmaTheme.type.displayL.copy(color = AlmaPalette.GoldDeep, fontSize = 34.sp),
        )
    }
}

/** A parchment sheen while the painting travels. No spinner — a spinner promises a wait. */
@Composable
private fun Shimmer() {
    val transition = rememberInfiniteTransition(label = "plate-shimmer")
    val t by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1_900, easing = LinearEasing), RepeatMode.Restart),
        label = "plate-shimmer-sweep",
    )
    Canvas(Modifier.fillMaxSize()) {
        val sweep = t * 2f - 0.5f
        drawRect(
            brush = Brush.linearGradient(
                colors = listOf(Color(0xFFE6DCC2), Color(0xFFF3E9D2), Color(0xFFE6DCC2)),
                start = Offset((sweep - 0.6f) * size.width, 0f),
                end = Offset((sweep + 0.6f) * size.width, size.height),
            )
        )
    }
}
