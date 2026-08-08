package ai.pazl.alma.ui.components

import ai.pazl.alma.R
import ai.pazl.alma.core.ScreenState
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

/**
 * Renders the two states a screen does not have content for, so that no screen
 * has to write them again.
 *
 * The contract: pass a [ScreenState], get the loaded branch called with the
 * data, and get a consistent waiting and failure treatment for free. What a
 * screen must **not** do is handle [ScreenState.Failed] by printing
 * `failure.message` — several failures are affordances rather than apologies,
 * and [onFailure] exists so that a screen can intercept the ones it can act on
 * (a paywall for [ApiFailure.Locked], a form for [ApiFailure.NeedsBirthTime])
 * and let the rest fall through to the default.
 */
@Composable
fun <T> StateHost(
    state: ScreenState<T>,
    modifier: Modifier = Modifier,
    onRetry: (() -> Unit)? = null,
    /** Return true to say "I drew this one myself". */
    onFailure: @Composable (ApiFailure) -> Boolean = { false },
    loaded: @Composable (T) -> Unit,
) {
    when (state) {
        is ScreenState.Loading -> Waiting(modifier)
        is ScreenState.Loaded -> loaded(state.data)
        is ScreenState.Failed -> {
            if (!onFailure(state.failure)) {
                FailureNotice(state.failure, onRetry, modifier)
            }
        }
    }
}

/**
 * Waiting.
 *
 * A breathing line of type rather than a spinner, and that is a product
 * decision rather than a stylistic one: a circular progress indicator is a
 * Material component that says "a computer is busy", and what is actually
 * happening is that Alma is reading. The words are already written and already
 * translated — "Reading your sky…" — and they set the right expectation for
 * something that takes seconds.
 *
 * The mark is never used here. It is not a loading spinner; the brand book says
 * so and it is the first thing anybody reaches for.
 */
@Composable
fun Waiting(modifier: Modifier = Modifier, text: String = stringResource(R.string.state_loading)) {
    val breath by rememberInfiniteTransition(label = "waiting").animateFloat(
        initialValue = 0.45f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            tween(1_600, easing = LinearEasing),
            RepeatMode.Reverse,
        ),
        label = "breath",
    )

    Column(
        modifier = modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = text,
            style = AlmaTheme.type.almaVoice,
            textAlign = TextAlign.Center,
            modifier = Modifier.alpha(breath),
        )
    }
}

/**
 * A failure, said plainly.
 *
 * The message comes from the server when it has one worth showing and from the
 * string table otherwise. Which of the two is chosen per case rather than
 * globally: "no connection to Alma" is a developer's sentence and the localised
 * one is a person's, whereas the message on a 503 from the AI layer is written
 * for a reader and is already the better line.
 */
@Composable
fun FailureNotice(
    failure: ApiFailure,
    onRetry: (() -> Unit)?,
    modifier: Modifier = Modifier,
) {
    val text = when (failure) {
        is ApiFailure.Offline -> stringResource(R.string.state_offline)
        is ApiFailure.NeedsBirthTime -> stringResource(R.string.error_needs_birth_time)
        is ApiFailure.QuestionLimit -> stringResource(R.string.error_question_limit)
        is ApiFailure.Unavailable -> failure.message.ifBlank { stringResource(R.string.error_ai_unavailable) }
        is ApiFailure.Unexpected, is ApiFailure.Invalid -> stringResource(R.string.error_generic)
        else -> failure.message.ifBlank { stringResource(R.string.error_generic) }
    }

    Column(
        modifier = modifier.fillMaxSize().padding(horizontal = 22.dp, vertical = 32.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = text,
            style = AlmaTheme.type.almaVoice,
            color = AlmaPalette.Body,
            textAlign = TextAlign.Center,
            modifier = Modifier.widthIn(max = 420.dp).fillMaxWidth(),
        )
        if (onRetry != null) {
            QuietButton(text = stringResource(R.string.state_retry), onClick = onRetry)
        }
    }
}
