package ai.pazl.alma.data

import androidx.compose.runtime.Immutable

/**
 * The two ways a call ends, and the several ways it can fail.
 *
 * This mirrors `src/lib/api.ts` deliberately, down to the case names, so that
 * a rule fixed on the web is fixed in the same shape here. The important half
 * is [ApiFailure]: the backend answers a locked chapter with 402, a missing
 * birth time with 422, and a daylight-saving ambiguity with 409 *and two
 * candidate instants*. Each of those is something the interface has to **say**
 * — open a paywall, open a form, ask which hour — rather than an error to
 * swallow. A single `Exception` with a message in it would make all three look
 * the same at the call site, which is exactly how a person ends up tapping a
 * button that can never work.
 *
 * Nothing here throws. A failure is a value, so a screen that forgets to handle
 * one gets a compiler warning on a `when` rather than a crash in the field.
 */
sealed interface ApiResult<out T> {
    @Immutable
    data class Ok<T>(val data: T) : ApiResult<T>

    @Immutable
    data class Err(val failure: ApiFailure) : ApiResult<Nothing>
}

@Immutable
sealed interface ApiFailure {

    /** What to put on screen if nothing better is known. Always non-empty. */
    val message: String

    /**
     * The chapter, system or plan is not paid for.
     *
     * [system] is what the paywall should be about — the person was looking at
     * *this* system, and an offer screen that sells "the archive" to somebody
     * who wanted their natal chart converts worse and deserves to.
     */
    @Immutable
    data class Locked(
        val system: String,
        val chapter: String?,
        override val message: String,
    ) : ApiFailure

    /** Houses, the solar return and the map need a real minute. Show the form. */
    @Immutable
    data class NeedsBirthTime(override val message: String) : ApiFailure

    /**
     * The clocks changed that night, so the wall-clock time happened twice.
     *
     * Both [options] are real instants an hour apart. Picking one silently
     * would put a coin flip inside a paid reading, so the person is asked.
     */
    @Immutable
    data class AmbiguousTime(
        override val message: String,
        val options: List<AmbiguityOption>,
    ) : ApiFailure

    /** Out of questions for today, or for the month. [allowance] is what they get. */
    @Immutable
    data class QuestionLimit(override val message: String, val allowance: Int) : ApiFailure

    /**
     * A checkout that cannot be created without an address.
     *
     * Kept even though Android buys through Play — the same account can have
     * bought on the web, and settings screens that touch the billing seam still
     * meet it. On Android it should never be reachable from a purchase button.
     */
    @Immutable
    data class NeedsEmail(override val message: String) : ApiFailure

    /** The token was rejected. Mint a new guest session and try once. */
    @Immutable
    data class Unauthenticated(override val message: String) : ApiFailure

    /**
     * The account behind this token is gone — someone deleted it, possibly on
     * another device. The token has already been cleared by the time this
     * arrives; the interface's job is to say so and start again.
     */
    @Immutable
    data class AccountDeleted(override val message: String) : ApiFailure

    /** The AI, the billing processor or the place index is down. Not the caller's fault. */
    @Immutable
    data class Unavailable(override val message: String) : ApiFailure

    /**
     * No connection to Alma.
     *
     * A dead network and a dead backend look identical from inside the app and
     * the interface says the same thing about both, so they are one case.
     */
    @Immutable
    data class Offline(override val message: String) : ApiFailure

    /**
     * Alma read the chart and there was nothing there to say.
     *
     * A 422 like `Invalid` below, and the opposite of a bug: the writer refused
     * because the chapter's factors came back empty — "the active chapter has
     * no factors to read from in this transits result — the chart genuinely
     * says nothing here". Found on a device, on Today, where it was rendering
     * as "Something went wrong. Try again in a moment." over a screen whose
     * calculations had all succeeded. Telling somebody the app broke when what
     * happened is that their sky is quiet today is the exact inversion of
     * "honest before beautiful", and retrying will produce the same answer.
     *
     * The server's own [message] is written for a reader and is the better
     * line, which is why this case carries nothing else.
     */
    @Immutable
    data class NothingToSay(override val message: String) : ApiFailure

    /** The request was refused as malformed. A bug in this app, almost always. */
    @Immutable
    data class Invalid(override val message: String) : ApiFailure

    /**
     * The store refused a purchase verification.
     *
     * Its own case, and it exists because of one status code. `/iap/verify`
     * answers `invalid_transaction` with **401**, and 401 everywhere else in
     * this app means "the token was rejected — mint a new session". Nothing
     * acts on it today, because [ai.pazl.alma.billing.PlayBilling] treats every
     * verify failure the same way and never re-authenticates. But
     * `Unauthenticated` is precisely the failure a generic session-recovery
     * handler is built for, so the first screen to add one would have signed
     * somebody out — and dropped their token — because a purchase signature
     * failed.
     *
     * [pending] separates the one member of this family that is not a refusal
     * at all: `purchase_incomplete` covers a Play cash payment that has not
     * settled, which is a "not yet" the paywall can say something kind about.
     */
    @Immutable
    data class StoreRefused(
        override val message: String,
        /** The backend's own `error` key: what to write in a log, verbatim. */
        val reason: String,
        val pending: Boolean = false,
    ) : ApiFailure

    /**
     * This subscription belongs to a store account, so no server can stop it.
     *
     * Not a failure of anything — the 409 that carries it is the backend saying
     * "here is the door" — and [manageUrl] is the one field a client cannot
     * compute for itself. Without this case the URL was thrown away and the
     * whole thing arrived as `Unexpected(409)`.
     */
    @Immutable
    data class CancelAtStore(
        override val message: String,
        val manageUrl: String,
    ) : ApiFailure

    /** Anything else, with the status kept for the log. */
    @Immutable
    data class Unexpected(val status: Int, override val message: String) : ApiFailure
}

@Immutable
data class AmbiguityOption(
    /** "earlier" or "later" — the word the API uses and the interface echoes back. */
    val choice: String,
    /** The instant itself, ISO-8601 UTC. */
    val utc: String,
)

/* ── narrowing helpers ─────────────────────────────────────────────────── */

inline fun <T> ApiResult<T>.onOk(block: (T) -> Unit): ApiResult<T> {
    if (this is ApiResult.Ok) block(data)
    return this
}

inline fun <T> ApiResult<T>.onErr(block: (ApiFailure) -> Unit): ApiResult<T> {
    if (this is ApiResult.Err) block(failure)
    return this
}

fun <T> ApiResult<T>.getOrNull(): T? = (this as? ApiResult.Ok)?.data

inline fun <T, R> ApiResult<T>.map(transform: (T) -> R): ApiResult<R> = when (this) {
    is ApiResult.Ok -> ApiResult.Ok(transform(data))
    is ApiResult.Err -> this
}
