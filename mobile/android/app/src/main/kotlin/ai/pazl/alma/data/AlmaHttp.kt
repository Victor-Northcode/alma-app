package ai.pazl.alma.data

import ai.pazl.alma.BuildConfig
import ai.pazl.alma.data.dto.ErrorEnvelope
import android.util.Log
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Response
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * The HTTP plumbing: one OkHttp client, one Retrofit, one JSON configuration,
 * and the classifier that turns a refusal into an [ApiFailure].
 *
 * Nothing above this file knows about OkHttp and nothing below it knows about
 * screens.
 */
internal object AlmaHttp {

    /** The header the server mints a guest token in, on *every* response. */
    const val TOKEN_HEADER = "X-Alma-Token"

    /**
     * The header this app *sends* to say which installation it is, while it has
     * no account.
     *
     * The server never mints one and never sends one back — there is nothing to
     * read off a response. That is deliberate on its side: a server that issued
     * these would issue one per tokenless request, and a launch that fires a
     * beacon while three other calls are in flight would turn one install into
     * four visitors at the top of the funnel. A client that generates its own
     * has exactly one before it makes its first request.
     */
    const val ANON_HEADER = "X-Alma-Anon"

    /**
     * The header this app sends to say what clock the phone is on.
     *
     * An IANA zone identifier — "Europe/Warsaw" — and never an offset, because
     * an offset cannot survive a daylight-saving change and a daily is a thing
     * about a day. See the note where it is set.
     */
    const val TIMEZONE_HEADER = "X-Alma-Timezone"

    /**
     * The JSON contract with the backend, and every setting here is load-bearing.
     *
     * - `ignoreUnknownKeys` — the server adds fields; an app in the store must
     *   not start crashing because a new one appeared.
     * - `encodeDefaults = false` and `explicitNulls = false` — several request
     *   bodies are Pydantic models with `extra="forbid"` and validated defaults.
     *   Sending `"house_system": null` where the server expects the field to be
     *   absent is a 422 that reads like a server bug.
     * - `coerceInputValues = false` — a null arriving in a non-null field should
     *   fail loudly here rather than silently become a zero three screens later.
     */
    val json: Json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = false
        explicitNulls = false
        coerceInputValues = false
        isLenient = false
    }

    fun client(tokens: TokenStore, measurement: Measurement? = null): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            // Generous, and it has to be: `POST /v1/readings` writes a chapter
            // with a language model on the other end of it. A 30-second read
            // timeout would cancel a purchase the person has already paid for
            // and leave them looking at an error over a chapter that is being
            // written anyway.
            //
            // 180 rather than 120, matching `AlmaClient.writingTimeout` on iOS:
            // that platform had this exact bug — a chapter cancelled mid-write
            // and reported as offline while the server finished and stored it —
            // and the two clients disagreeing about how long a chapter may take
            // is how the same report comes back on one phone and not the other.
            .readTimeout(180, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(SessionInterceptor(tokens, measurement))

        // Empty in release, and *empty by not existing*: `diagnosticInterceptors`
        // is declared once per build type, so the release binary contains no
        // logging code and does not link okhttp's logging artifact at all. An
        // `if (BuildConfig.DEBUG)` here would have been a runtime check around
        // code that shipped anyway — and it would not compile, because the
        // dependency is `debugImplementation`.
        diagnosticInterceptors().forEach(builder::addInterceptor)

        return builder.build()
    }

    fun retrofit(client: OkHttpClient, baseUrl: String = BuildConfig.API_BASE): Retrofit =
        Retrofit.Builder()
            .baseUrl(if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/")
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    /**
     * Attaches the two identities going out and captures the token coming back.
     *
     * **The token, from every response and not only from the sign-in call.**
     * Which request turns out to be the one that mints an account depends on
     * what the person does — saving a birth, landing a sign-in link, verifying a
     * purchase — so whichever it is has to keep the header, or the account is
     * created and immediately abandoned.
     *
     * This paragraph used to say the opposite of what is true now, and it was
     * true when it was written: `POST /v1/events` minted an account for any
     * tokenless caller, so the funnel beacon fired before the first screen had
     * finished drawing was usually the request that created the row, and the
     * comment warned that ignoring the header would mint an account per beacon.
     * A beacon mints nothing today — the route takes `deps.Visitor`, reads an
     * account from the bearer token if there is one, and creates nothing if
     * there is not — and neither does launching the app.
     *
     * **What replaced it is the header going the other way.** `X-Alma-Anon`
     * carries the installation id on *every* request, not only on beacons,
     * because the request that finally mints the account is the one the server
     * records the join on: that is the only moment "this install became that
     * account" is something we watched happen rather than inferred. Sent only
     * on beacons, the minting request would arrive bare, nothing would be
     * claimed, and the stages before the account and the stages after it would
     * be two people for ever — which reads as 0% conversion on data that looks
     * perfectly healthy.
     *
     * It is absent when [Measurement] is off, and a request with no token and no
     * id is answered 422 `anonymous_id_required` by that one route and by no
     * other. That is the opt-out working: nothing is measured, nothing is
     * stored, and nothing else in the app changes.
     */
    private class SessionInterceptor(
        private val tokens: TokenStore,
        private val measurement: Measurement?,
    ) : Interceptor {
        override fun intercept(chain: Interceptor.Chain): Response {
            val request = chain.request().newBuilder()
                .header("Accept", "application/json")
                // The device's own IANA zone, on every request.
                //
                // `Profile.timezone` is the **birth** timezone — it is derived
                // from the birthplace — so a person born in Lisbon and living
                // in Toronto would be sent their daily at 03:00 if that were
                // the only clock we had. There is no other source: nothing in
                // this app has ever told the server where the phone is.
                //
                // `deps.py` is owned by another workflow and does not read this
                // header yet. Sending it now costs one line and means the day
                // it starts reading, every build already in the field is
                // supplying it — ignored silently when unrecognised, exactly as
                // the country header is. `THE-DAILY.md §6.8`, `PUSH.md §3`.
                //
                // Unconditional, unlike the anon id above: a timezone is not a
                // measurement and turning measurement off must not stop a
                // notification arriving at the right hour. It is also not an
                // identifier — there are 38 distinct offsets and several
                // hundred million people in the busiest zone.
                .header(TIMEZONE_HEADER, java.util.TimeZone.getDefault().id)
                // The device's language, on every request — OkHttp, unlike the
                // platform HTTP stacks, sends no Accept-Language of its own.
                // The server reads it in one place only: the request that mints
                // a guest account, so a new reader's `user.locale` starts as
                // the phone's language instead of English-until-the-settings-
                // screen. Unconditional for the same reason the timezone is —
                // a language is not a measurement, and it is even less of an
                // identifier than 38 timezone offsets are.
                .header("Accept-Language", java.util.Locale.getDefault().toLanguageTag())
                .apply {
                    tokens.token?.let { header("Authorization", "Bearer $it") }
                    measurement?.anonId()?.let { header(ANON_HEADER, it) }
                }
                .build()

            val response = chain.proceed(request)
            response.header(TOKEN_HEADER)?.let(tokens::save)
            return response
        }
    }

    /* ── turning a refusal into something the interface can say ────────── */

    /**
     * Classify a non-2xx answer.
     *
     * The `error` string in the body is checked **before** the status code,
     * deliberately. The backend reuses statuses across meanings — 409 is both a
     * daylight-saving ambiguity and a store product mismatch, 422 is both a
     * missing birth time and an ordinary validation failure — so the code alone
     * cannot tell them apart, while the `error` key always can.
     *
     * `detail` is sometimes a string and sometimes an object, depending on which
     * line in the backend raised it. Both shapes are all over `alma/api`, so
     * both are unpicked here rather than declared as a type.
     */
    fun classify(status: Int, body: String?, onAccountGone: () -> Unit = {}): ApiFailure {
        val envelope = runCatching {
            body?.takeIf { it.isNotBlank() }?.let { json.decodeFromString<ErrorEnvelope>(it) }
        }.getOrNull()

        val detail: JsonObject? = envelope?.detail as? JsonObject
        val plain: String? = (envelope?.detail as? JsonPrimitive)?.contentOrNull

        val message = detail?.string("message") ?: plain ?: "something went wrong"

        when (detail?.string("error")) {
            "locked" -> return ApiFailure.Locked(
                system = detail.string("system").orEmpty(),
                chapter = detail.string("chapter"),
                message = message,
            )

            "birth_time_required" -> return ApiFailure.NeedsBirthTime(message)

            // Not an "invalid" 422 like any other: a processor that will not
            // create a session without an address turns this into something the
            // offer screen has to *ask for*, and a generic "something went
            // wrong" leaves a person tapping a button that can never work.
            "email_required" -> return ApiFailure.NeedsEmail(message)

            "ambiguous_birth_time" -> return ApiFailure.AmbiguousTime(
                message = message,
                options = detail.options(),
                transitionLocalDate = detail.string("transition_local_date").orEmpty(),
            )

            // Compatibility with nobody saved. A 422, so it landed on `Invalid`
            // and the chapter printed the sentence with no way to act on it —
            // while the one thing that resolves it is a screen this app has.
            "partner_required" -> return ApiFailure.PartnerRequired(message)

            "question_limit" -> return ApiFailure.QuestionLimit(
                message = message,
                allowance = detail.int("allowance") ?: 0,
            )

            "ai_unavailable", "billing_unavailable", "budget_exceeded", "place_index_missing" ->
                return ApiFailure.Unavailable(message)

            // Not a fault. `readings.py` raises this when the chapter's factors
            // came back empty — the chart genuinely has nothing to say there —
            // and it is a 422, so without this branch it landed on `Invalid`
            // and Today printed "Something went wrong. Try again in a moment."
            // over a screen whose calculations had all succeeded. Seen on a
            // device: a quiet transit window on 7 August.
            //
            // `answer_refused` is the same thing on the chat route, and it was
            // missing: `conversation.AnswerRefused` is raised when no reply
            // could be produced that cites only real placements, and the 422 it
            // becomes carries `str(exc)` — English engineering prose meant for
            // whoever reads the traceback. Without this branch it landed on
            // `Invalid`, whose message the chat prints verbatim, so a reader in
            // Portuguese was shown a sentence from `conversation.py`.
            "reading_refused", "answer_refused" -> return ApiFailure.NothingToSay(message)

            // The three store refusals `/v1/billing/iap/verify` raises, and the
            // reason they need naming here rather than falling through.
            //
            // `invalid_transaction` is a **401**. Without this branch it landed
            // on `401 -> Unauthenticated` below, which everywhere else in the
            // app means "the session was rejected" — so a purchase signature
            // that failed would look identical to a dead token, and the first
            // screen to recover from `Unauthenticated` generically would sign
            // somebody out over it. `product_mismatch` and `purchase_incomplete`
            // are both 409s that would otherwise read as `Unexpected`.
            //
            // The `error`-before-status ordering this file already documents is
            // exactly the mechanism for it: every one of these carries a
            // self-naming `detail.error`, so the information is on the wire and
            // was simply not being read.
            "invalid_transaction", "product_mismatch" ->
                return ApiFailure.StoreRefused(message, reason = detail.string("error").orEmpty())

            "purchase_incomplete" ->
                return ApiFailure.StoreRefused(message, reason = "purchase_incomplete", pending = true)

            // `POST /billing/subscription/cancel` on a store subscription. The
            // 409 is not a failure — the server is answering "here is where you
            // do that" and putting the deep link in the body. Falling through
            // to `Unexpected(409)` kept the sentence and dropped the URL, which
            // is the only part of it the app cannot work out for itself.
            "cancel_at_store" -> return ApiFailure.CancelAtStore(
                message = message,
                manageUrl = detail.string("manage_url").orEmpty(),
            )
        }

        return when (status) {
            401 -> ApiFailure.Unauthenticated(message)
            402 -> ApiFailure.Locked(system = "", chapter = null, message = message)
            410 -> {
                // The account behind this token is gone. Keeping it would make
                // every later request fail identically, which reads as a broken
                // app rather than a deleted account. Handed out as a callback
                // rather than reaching for the TokenStore, so that classifying
                // a response is a pure function and can be tested as one.
                onAccountGone()
                ApiFailure.AccountDeleted(message)
            }
            422 -> ApiFailure.Invalid(message)
            503 -> ApiFailure.Unavailable(message)
            else -> ApiFailure.Unexpected(status, message)
        }
    }

    /** What a thrown network error means. There is only ever one answer. */
    fun classifyThrowable(error: Throwable): ApiFailure = when (error) {
        is IOException -> {
            // A dead network and a dead backend are indistinguishable from here
            // and the interface says the same thing about both.
            ApiFailure.Offline("no connection to Alma")
        }
        else -> {
            Log.w("AlmaHttp", "unexpected failure", error)
            ApiFailure.Unexpected(0, error.message ?: "something went wrong")
        }
    }

    private fun JsonObject.string(key: String): String? =
        runCatching { this[key]?.jsonPrimitive?.contentOrNull }.getOrNull()

    private fun JsonObject.int(key: String): Int? =
        runCatching { this[key]?.jsonPrimitive?.intOrNull }.getOrNull()

    private fun JsonObject.double(key: String): Double? =
        runCatching { this[key]?.jsonPrimitive?.doubleOrNull }.getOrNull()

    private fun JsonObject.options(): List<AmbiguityOption> = runCatching {
        (this["options"] as? JsonArray)?.map { element ->
            val row = element.jsonObject
            AmbiguityOption(
                choice = row.string("choice").orEmpty(),
                utc = row.string("utc").orEmpty(),
                // The zone names and offsets were on the wire from the day
                // `calc/service.py` grew one builder for this body, and were
                // simply not read. Without them the fork screen shows the same
                // time twice with nothing to choose between.
                abbreviation = row.string("abbreviation").orEmpty(),
                offsetHours = row.double("offset_hours") ?: 0.0,
            )
        }.orEmpty()
    }.getOrDefault(emptyList())
}
