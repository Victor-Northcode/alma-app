package ai.pazl.alma.core

import ai.pazl.alma.data.ApiFailure
import androidx.compose.runtime.Immutable

/**
 * What a screen is, at any moment. Three cases and no fourth.
 *
 * Every screen in this app uses this rather than inventing `isLoading` and
 * `error` beside its data. That is a rule about *representable states* rather
 * than about tidiness: a screen holding three independent fields can be
 * loading-and-failed-and-loaded at once, and the bug that produces — a spinner
 * over a stale chart with an error underneath it — is not one anybody notices
 * in review. Here it cannot be written down.
 *
 * [Loaded] carries the data because there is no other place it can live. A
 * nullable `data` field beside the state is the boolean problem with extra
 * steps: every read of it needs a `!!` or an `?:`, and the fallback branch is
 * dead code that the compiler cannot tell you is dead.
 *
 * ## Why there is no `Empty`
 *
 * "No birth data yet" and "no second person yet" are *loaded* states, not
 * missing ones — the server answered, and what it said was that this account
 * has nothing yet. They are modelled inside the screen's own data type, where
 * the screen can say something useful about them ("add your birth date and I
 * can read you"). An `Empty` case here would collapse eight different reasons
 * for a sparse screen into one blank one.
 *
 * ## Why there is no `Refreshing`
 *
 * A screen that has data and is fetching again stays [Loaded]. It shows what it
 * has and a quiet indicator; it does not throw away a chart the person is
 * reading in order to show a spinner. Screens that need to say so carry a
 * `refreshing` flag inside their own loaded type.
 */
@Immutable
sealed interface ScreenState<out T> {

    /** Nothing has arrived yet. The only state a screen may start in. */
    data object Loading : ScreenState<Nothing>

    /** The server answered. */
    @Immutable
    data class Loaded<T>(val data: T) : ScreenState<T>

    /**
     * It did not.
     *
     * [failure] is the typed one from the API layer, not a string, because
     * several of these are things the interface has to *say* rather than
     * errors to apologise for: a locked chapter opens a paywall, a missing
     * birth time opens a form, an ambiguous birth time asks a question. A
     * screen that renders `failure.message` for all of them has thrown away
     * every one of those affordances.
     */
    @Immutable
    data class Failed(val failure: ApiFailure) : ScreenState<Nothing>
}

/** The data if there is any, null otherwise. For the places where a null is honest. */
fun <T> ScreenState<T>.dataOrNull(): T? = (this as? ScreenState.Loaded)?.data

/** Map the loaded value, leaving loading and failure alone. */
inline fun <T, R> ScreenState<T>.map(transform: (T) -> R): ScreenState<R> = when (this) {
    is ScreenState.Loading -> ScreenState.Loading
    is ScreenState.Failed -> this
    is ScreenState.Loaded -> ScreenState.Loaded(transform(data))
}

/** Turn an [ApiResult] into the state a screen holds. */
fun <T> ai.pazl.alma.data.ApiResult<T>.toScreenState(): ScreenState<T> = when (this) {
    is ai.pazl.alma.data.ApiResult.Ok -> ScreenState.Loaded(data)
    is ai.pazl.alma.data.ApiResult.Err -> ScreenState.Failed(failure)
}
