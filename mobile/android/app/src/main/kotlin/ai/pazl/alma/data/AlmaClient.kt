package ai.pazl.alma.data

import ai.pazl.alma.data.dto.AppleSignInBody
import ai.pazl.alma.data.dto.BirthInput
import ai.pazl.alma.data.dto.CalcRequest
import ai.pazl.alma.data.dto.CalcResultDto
import ai.pazl.alma.data.dto.CancelResultDto
import ai.pazl.alma.data.dto.CatalogueDto
import ai.pazl.alma.data.dto.ChaptersDto
import ai.pazl.alma.data.dto.ChatReplyDto
import ai.pazl.alma.data.dto.ChatRequest
import ai.pazl.alma.data.dto.ConfirmBody
import ai.pazl.alma.data.dto.DailySettingsBody
import ai.pazl.alma.data.dto.DailySettingsDto
import ai.pazl.alma.data.dto.DeviceRegisteredDto
import ai.pazl.alma.data.dto.DeviceForgetBody
import ai.pazl.alma.data.dto.DeviceRegistrationBody
import ai.pazl.alma.data.dto.DeclinedBody
import ai.pazl.alma.data.dto.DeclinedDto
import ai.pazl.alma.data.dto.EntitlementsDto
import ai.pazl.alma.data.dto.EventBody
import ai.pazl.alma.data.dto.GoogleSignInBody
import ai.pazl.alma.data.dto.HubDto
import ai.pazl.alma.data.dto.IapVerifyBody
import ai.pazl.alma.data.dto.IapVerifyResultDto
import ai.pazl.alma.data.dto.LocaleBody
import ai.pazl.alma.data.dto.MagicLinkBody
import ai.pazl.alma.data.dto.MagicLinkConsumeBody
import ai.pazl.alma.data.dto.MagicLinkSent
import ai.pazl.alma.data.dto.MemoryListDto
import ai.pazl.alma.data.dto.PlaceDto
import ai.pazl.alma.data.dto.ProfileDto
import ai.pazl.alma.data.dto.ReadingEnvelope
import ai.pazl.alma.data.dto.ReadingRequest
import ai.pazl.alma.data.dto.SessionDto
import ai.pazl.alma.data.dto.SpheresResponseDto
import ai.pazl.alma.data.dto.TimezoneDto
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonObject
import okhttp3.OkHttpClient
import retrofit2.Response

/**
 * The only thing screens talk to.
 *
 * Every method suspends, returns an [ApiResult], and never throws. What it adds
 * over [AlmaService] is the three responsibilities the web client's `api.ts`
 * also carries and nothing else:
 *
 * 1. **The guest token**, handled entirely inside the interceptor, so no caller
 *    has ever seen one and no caller can forget to send it.
 * 2. **Typed failures** — a locked chapter, a missing birth time, a
 *    daylight-saving ambiguity — as values rather than exceptions.
 * 3. **Nothing else.** No caching, no retries, no astrology. A screen that
 *    needs a chart asks for one; a `ViewModel` that wants to keep it keeps it.
 *
 * Retries in particular are absent on purpose. `POST /v1/readings` costs money
 * per call and a transparent retry on a timeout would write a chapter twice.
 */
class AlmaClient internal constructor(
    private val service: AlmaService,
    private val tokens: TokenStore,
    /**
     * Null in a test, and in nothing else. The production container always
     * passes one; a null here means "no preference exists", which is the same
     * as the default.
     */
    private val measurement: Measurement? = null,
    private val io: CoroutineDispatcher = Dispatchers.IO,
) {

    companion object {
        /** Build one. The only entry point outside the `data` package. */
        fun create(
            tokens: TokenStore,
            baseUrl: String? = null,
            measurement: Measurement? = null,
        ): AlmaClient {
            val http: OkHttpClient = AlmaHttp.client(tokens, measurement)
            val retrofit = baseUrl?.let { AlmaHttp.retrofit(http, it) } ?: AlmaHttp.retrofit(http)
            return AlmaClient(retrofit.create(AlmaService::class.java), tokens, measurement)
        }
    }

    /** True once the server has issued this device an account. */
    val hasSession: Boolean get() = tokens.token != null

    /* ── auth ──────────────────────────────────────────────────────────── */

    /**
     * The account, minted if this device has none.
     *
     * **Not at launch, which is what this used to say.** It is the one route
     * whose whole job is "mint or read": with a token it identifies the account
     * and creates nothing, and without one it creates a row. `SessionHolder`
     * called it from `start()` on every launch, so opening the app *was* the act
     * that created the account — on every install, before anybody had typed
     * anything — which is exactly what the owner's rule ("not on a page view")
     * forbids. The route is right; the caller was not.
     *
     * The one caller that still reaches it deliberately without a token is
     * [SessionHolder.awaitAccount], and only for verifying a purchase: the money
     * has to land on an account that exists, and a purchase is an act.
     */
    suspend fun session(): ApiResult<SessionDto> = call { service.session() }

    suspend fun refresh(): ApiResult<SessionDto> = call { service.refresh() }

    suspend fun requestMagicLink(email: String, locale: String): ApiResult<MagicLinkSent> =
        call { service.requestMagicLink(MagicLinkBody(email, locale)) }

    /**
     * Attaches an identity to the account this device already has.
     *
     * Signing in does **not** replace the account — everything a guest did,
     * including anything they bought, stays where it is. That is the reason the
     * token is not cleared before this call and must not be after it.
     */
    suspend fun consumeMagicLink(token: String): ApiResult<SessionDto> =
        call { service.consumeMagicLink(MagicLinkConsumeBody(token)) }

    suspend fun signInWithGoogle(idToken: String): ApiResult<SessionDto> =
        call { service.googleSignIn(GoogleSignInBody(idToken)) }

    suspend fun signInWithApple(identityToken: String, fullName: String? = null): ApiResult<SessionDto> =
        call { service.appleSignIn(AppleSignInBody(identityToken, fullName)) }

    /**
     * Forget the token on this device. The account itself is untouched.
     *
     * The installation id deliberately stays. Signing out is not erasure — the
     * account is still there and the person may sign back into it — and
     * re-minting the id here would break the join for somebody who signs out and
     * carries on using the app as a guest, which is the one thing the id exists
     * to hold together. It goes only where the account itself goes; see
     * [forgetThisDevice].
     */
    fun signOut() = tokens.clear()

    /**
     * Everything that identifies this device, gone.
     *
     * For the two moments the account behind the token has stopped existing: a
     * 410 on any request, and deleting the account from Settings.
     */
    private fun forgetThisDevice() {
        tokens.clear()
        measurement?.forgetInstallation()
    }

    /* ── account ───────────────────────────────────────────────────────── */

    suspend fun account(): ApiResult<JsonObject> = call { service.account() }

    suspend fun setLocale(locale: String): ApiResult<JsonObject> =
        call { service.setLocale(LocaleBody(locale)) }

    suspend fun export(): ApiResult<JsonObject> = call { service.export() }

    /**
     * Delete the account and everything in it.
     *
     * [confirm] must equal what the server expects for this account: its email
     * address if it has one, and otherwise its own id. A guest may delete —
     * that is the default state of every install and the state holding the most
     * sensitive data in the product, so requiring an email address first would
     * be demanding more personal data as the price of removing what was already
     * taken.
     *
     * The token is dropped here rather than waiting for the next request to
     * come back 410, because the next request might be minutes away and the
     * person is entitled to see themselves logged out immediately.
     */
    suspend fun deleteAccount(confirm: String): ApiResult<JsonObject> =
        call { service.deleteAccount(ConfirmBody(confirm)) }.also { forgetThisDevice() }

    /* ── places ────────────────────────────────────────────────────────── */

    suspend fun searchPlaces(query: String): ApiResult<List<PlaceDto>> =
        call { service.searchPlaces(query) }

    suspend fun timezoneAt(latitude: Double, longitude: Double, on: String? = null): ApiResult<TimezoneDto> =
        call { service.timezoneAt(latitude, longitude, on) }

    /* ── profiles ──────────────────────────────────────────────────────── */

    suspend fun profiles(): ApiResult<List<ProfileDto>> = call { service.profiles() }

    suspend fun saveProfile(birth: BirthInput): ApiResult<ProfileDto> =
        call { service.saveProfile(birth) }

    suspend fun profile(id: String): ApiResult<ProfileDto> = call { service.profile(id) }

    suspend fun updateProfile(id: String, birth: BirthInput): ApiResult<ProfileDto> =
        call { service.updateProfile(id, birth) }

    suspend fun deleteProfile(id: String): ApiResult<Unit> = call { service.deleteProfile(id) }

    /* ── the eight systems ─────────────────────────────────────────────── */

    /**
     * One system, calculated.
     *
     * Free forever, all eight of them, whether or not anything is paid for —
     * the ephemeris and the gazetteer are static local files on the server and
     * the calculation costs us nothing. What a locked system returns is the
     * *preview*: the sign, the number, the card. `factors` comes back empty and
     * `locked` is true, which is what a paywall screen reads.
     *
     * @param system one of [AlmaSystem]. An unknown slug is a programming error
     *   and fails fast rather than round-tripping to a 404.
     */
    suspend fun system(system: String, request: CalcRequest = CalcRequest()): ApiResult<CalcResultDto> =
        when (system) {
            AlmaSystem.NATAL -> call { service.natal(request) }
            AlmaSystem.NUMEROLOGY -> call { service.numerology(request) }
            AlmaSystem.BIRTH_CARD -> call { service.birthCard(request) }
            AlmaSystem.TRANSITS -> call { service.transits(request) }
            AlmaSystem.SOLAR_RETURN -> call { service.solarReturn(request) }
            AlmaSystem.COMPATIBILITY -> call { service.compatibility(request) }
            AlmaSystem.ASTROCARTOGRAPHY -> call { service.astrocartography(request) }
            AlmaSystem.SYNTHESIS -> call { service.synthesis(request) }
            else -> error("unknown system: $system — see AlmaSystem")
        }

    /** Every system and its state: what is calculated, what needs a time, what needs a person. */
    suspend fun hub(): ApiResult<HubDto> = call { service.hub() }

    /* ── chapters and readings ─────────────────────────────────────────── */

    /**
     * The table of contents, in the language the account reads in.
     *
     * `locale` comes from the session rather than from `Locale.getDefault()`,
     * and the difference is the settings screen: somebody who picked Deutsch
     * on an English phone has said which language Alma writes to them in, and
     * the chapter list has to be the same one as the chapter.
     */
    suspend fun chapters(system: String, locale: String): ApiResult<ChaptersDto> =
        call { service.chapters(system, locale) }

    /**
     * One chapter, written the first time it is asked for.
     *
     * Slow — seconds, not milliseconds — and it spends real money on the first
     * call for each chapter. A screen calling this needs a state that says
     * "Alma is writing this chapter…" and it must not fire the call twice.
     * `cached` on the envelope is true when the chapter already existed, which
     * is also the promise the interface makes: it says the same thing tomorrow.
     */
    /**
     * The free preview of the natal chart: five spheres, two sentences each.
     *
     * Written once per chart per language on the cheap model and cached in the
     * same reading table as everything else, so the second request is a read.
     */
    suspend fun natalSpheres(locale: String): ApiResult<SpheresResponseDto> =
        call { service.natalSpheres(locale) }

    suspend fun reading(request: ReadingRequest): ApiResult<ReadingEnvelope> =
        call { service.reading(request) }

    /* ── chat ──────────────────────────────────────────────────────────── */

    suspend fun ask(request: ChatRequest): ApiResult<ChatReplyDto> = call { service.ask(request) }

    suspend fun threads(): ApiResult<JsonObject> = call { service.threads() }

    suspend fun thread(id: String): ApiResult<JsonObject> = call { service.thread(id) }

    suspend fun memory(): ApiResult<MemoryListDto> = call { service.memory() }

    suspend fun forget(id: String): ApiResult<Unit> = call { service.forget(id) }

    /* ── billing ───────────────────────────────────────────────────────── */

    /**
     * The price list, in this account's currency, already formatted.
     *
     * Read `display` and put it on screen. Never format `cents` and never type
     * a price into a layout — the ladder is regional and the catalogue is the
     * source of truth for all thirteen currencies.
     */
    suspend fun catalogue(country: String? = null): ApiResult<CatalogueDto> =
        call { service.catalogue(country) }

    suspend fun entitlements(country: String? = null): ApiResult<EntitlementsDto> =
        call { service.entitlements(country) }

    /**
     * Hand a Play purchase token to the server, which checks it with Google and
     * grants what it bought.
     *
     * **This is the only way anything gets unlocked on Android, and the rule it
     * enforces is the one rule that survives every platform: entitlements are
     * granted by the server after it verifies the purchase with the store,
     * never by the app noticing that billing returned OK.**
     *
     * Anything the client can decide, the client can be made to decide. The web
     * client carried that comment from its first version and an attack review
     * later proved it right — metadata a browser carried turned out to be
     * rewritable, and the fix was a server-side seal. Android is not given a
     * weaker rule: `purchase.purchaseToken` is not evidence, it is a *lookup
     * key*, and the server exchanges it with the Play Developer API for the
     * truth. A rooted device can return anything from `BillingClient`; it
     * cannot make Google's API agree.
     *
     * A replay grants nothing twice. The event id is `"google:<order id>"` and
     * `webhook_event.id` is a primary key, so a re-delivered purchase — Play
     * re-delivers on every launch until it is acknowledged — answers
     * `already_claimed` and writes nothing. Which means this is safe, and
     * correct, to call on **every** launch for every unacknowledged purchase.
     *
     * @return the unlocked list, straight from the same request, so nothing has
     *   to guess how long to wait before re-reading entitlements.
     */
    suspend fun verifyPurchase(product: String, purchaseToken: String): ApiResult<IapVerifyResultDto> =
        // `googleplay`, and the exact spelling is the whole of this line.
        //
        // It said `"google"` and the entire Play revenue path was dead behind
        // it. `_store_adapter` resolves the adapter from this string through
        // `alma/billing/provider.py::provider_for`, which branches on
        // "paddle", "dodo", "appstore" and "googleplay" — there is no "google".
        // So every verification answered 400 `unknown_platform` *before* Google
        // was ever asked, and it failed the same way on every retry: the
        // purchase stayed unacknowledged, Play refunded it after three days,
        // and in between somebody who had paid watched a locked chapter.
        //
        // The literal stays here rather than moving to `StoreProducts.PLATFORM`
        // for two reasons. `data` must not depend on `billing` — this package
        // knows about HTTP and knows nothing about Play. And
        // `test_the_platform_name_each_client_sends_resolves_to_an_adapter`
        // reads the literal out of *this file* and feeds it to `provider_for`,
        // so it fails whichever side drifts; indirection would defeat the pin.
        call {
            service.verifyPurchase(
                IapVerifyBody(platform = "googleplay", product = product, transaction = purchaseToken)
            )
        }

    /**
     * Stop the next charge.
     *
     * On Android this is usually **not** the right control. A Play subscription
     * is cancelled in Play, and the catalogue's `manage_url` is where the
     * settings screen must send the person; an app that offers its own cancel
     * button for a Play subscription cannot honour it, and an app that only
     * *says* "cancel in Play" without linking there fails review. This binding
     * exists for an account that subscribed on the web and opened the app.
     */
    suspend fun cancelSubscription(): ApiResult<CancelResultDto> = call { service.cancelSubscription() }

    /** The one downsell we allow ourselves, about the system that was actually declined. */
    suspend fun declined(system: String? = null, country: String? = null): ApiResult<DeclinedDto> =
        call { service.declined(DeclinedBody(system, country)) }

    /* ── funnel ────────────────────────────────────────────────────────── */

    /**
     * Record that this account reached one stage of the funnel.
     *
     * Fire and forget from the caller's point of view — the result is returned
     * so a test can assert on it, and no screen should branch on it. Attributed
     * to whoever is asking, which for most of the funnel is a guest; that is
     * the measurement working as intended rather than a shortcoming, because a
     * product whose first minute needs no account has most of its funnel in
     * front of the sign-in wall.
     */
    suspend fun record(stage: FunnelStage, meta: Map<String, String>? = null): ApiResult<JsonObject> {
        // The one gate, here rather than at each of the eight call sites: the
        // privacy policy this app links to promises an opt-out, and a promise
        // kept at six call sites is a promise broken at the seventh. See
        // [Measurement] for why a switch exists at all when the payload is a
        // word from a closed set.
        //
        // The refusal is an `Ok` rather than an `Err`. Nothing branches on the
        // result of a beacon, and a screen that started showing failures
        // because measurement was off would be punishing the choice.
        if (measurement?.enabled?.value == false) return ApiResult.Ok(JsonObject(emptyMap()))
        return call { service.event(EventBody(stage = stage.wire, meta = meta)) }
    }

    /* ── the daily ─────────────────────────────────────────────────────── */

    suspend fun registerDevice(body: DeviceRegistrationBody): ApiResult<DeviceRegisteredDto> =
        call { service.registerDevice(body) }

    suspend fun forgetDevice(token: String, platform: String = "android"): ApiResult<Unit> =
        call { service.forgetDevice(DeviceForgetBody(platform = platform, token = token)) }

    suspend fun setDailyPreference(body: DailySettingsBody): ApiResult<DailySettingsDto> =
        call { service.setDailyPreference(body) }

    suspend fun dailySettings(): ApiResult<DailySettingsDto> =
        call { service.dailySettings() }

    /* ── the one place a call is actually made ─────────────────────────── */

    /**
     * Run one call on IO, and turn everything it can do into an [ApiResult].
     *
     * A 204 with no body is a success whose `body()` is null, and so is a 200
     * returning `Unit`; both would be an `Err` if this checked the body first,
     * which is why the status is checked first and the body only afterwards.
     */
    private suspend inline fun <T> call(crossinline block: suspend () -> Response<T>): ApiResult<T> =
        withContext(io) {
            try {
                val response = block()
                if (response.isSuccessful) {
                    @Suppress("UNCHECKED_CAST")
                    val body = response.body() ?: Unit as T
                    ApiResult.Ok(body)
                } else {
                    ApiResult.Err(
                        AlmaHttp.classify(
                            status = response.code(),
                            body = response.errorBody()?.string(),
                            // The token and the installation id go together,
                            // always. The id is the string this account's
                            // pre-account funnel rows are keyed to, so a device
                            // that kept it would carry an identifier belonging
                            // to somebody who has been erased straight into the
                            // next account it makes — and the server would
                            // refuse to claim it, because it is already spoken
                            // for by a row that no longer exists.
                            onAccountGone = ::forgetThisDevice,
                        )
                    )
                }
            } catch (error: Throwable) {
                ApiResult.Err(AlmaHttp.classifyThrowable(error))
            }
        }
}

/**
 * The eight slugs, spelled the way the API spells them.
 *
 * Strings rather than an enum because they cross the wire in both directions
 * and appear in navigation routes; an enum would mean a `valueOf` at every
 * boundary and a crash on the day a ninth system ships to the server first.
 */
object AlmaSystem {
    const val NATAL = "natal"
    const val NUMEROLOGY = "numerology"
    const val BIRTH_CARD = "birth-card"
    const val TRANSITS = "transits"
    const val SOLAR_RETURN = "solar-return"
    const val COMPATIBILITY = "compatibility"
    const val ASTROCARTOGRAPHY = "astrocartography"
    const val SYNTHESIS = "synthesis"

    /** In the order the hub lists them. */
    val ALL: List<String> = listOf(
        NATAL, NUMEROLOGY, BIRTH_CARD, TRANSITS,
        SOLAR_RETURN, COMPATIBILITY, ASTROCARTOGRAPHY, SYNTHESIS,
    )

    /** How many written chapters each has. Free calculation, one free chapter. */
    val CHAPTER_COUNT: Map<String, Int> = mapOf(
        NATAL to 16,
        NUMEROLOGY to 5,
        BIRTH_CARD to 3,
        TRANSITS to 3,
        SOLAR_RETURN to 3,
        COMPATIBILITY to 4,
        ASTROCARTOGRAPHY to 3,
        SYNTHESIS to 4,
    )
}

/**
 * The funnel stages this app may report, and only these.
 *
 * The names are fixed by `backend/alma/funnel.py`; an unknown one comes back
 * 422 with the valid set listed. `purchase` is absent deliberately — the server
 * records that itself when it verifies the purchase, and a client that also
 * sent it would double-count every sale.
 */
enum class FunnelStage(val wire: String) {
    LandingView("landing_view"),
    QuizStart("quiz_start"),
    QuizComplete("quiz_complete"),
    PortraitView("portrait_view"),
    OfferView("offer_view"),
    CheckoutOpened("checkout_opened"),
    PurchaseCompleted("purchase_completed"),
    OfferDeclined("offer_declined"),
}
