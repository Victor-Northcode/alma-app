package ai.pazl.alma.data

import ai.pazl.alma.data.dto.AppleSignInBody
import ai.pazl.alma.data.dto.CalcRequest
import ai.pazl.alma.data.dto.CatalogueDto
import ai.pazl.alma.data.dto.CalcResultDto
import ai.pazl.alma.data.dto.CancelResultDto
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
import ai.pazl.alma.data.dto.BirthInput
import ai.pazl.alma.data.dto.PlaceDto
import ai.pazl.alma.data.dto.ProfileDto
import ai.pazl.alma.data.dto.ReadingEnvelope
import ai.pazl.alma.data.dto.ReadingRequest
import ai.pazl.alma.data.dto.SessionDto
import ai.pazl.alma.data.dto.SpheresResponseDto
import ai.pazl.alma.data.dto.TimezoneDto
import kotlinx.serialization.json.JsonObject
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Every route the app calls, one per method, in the order the backend declares
 * them.
 *
 * Two things about the shape.
 *
 * **Every method returns `Response<T>` rather than `T`.** Retrofit throws
 * `HttpException` for a non-2xx when the return type is bare, and half the
 * non-2xx answers this API gives are not errors — a 402 is a paywall, a 409 is
 * a question about daylight saving. Wrapping in `Response` keeps the body and
 * the status together so [AlmaHttp] can turn them into an [ApiFailure] instead
 * of an exception.
 *
 * **This interface is internal to `data`.** Screens talk to [AlmaClient], which
 * is where the typed failures and the token rules live. A screen that had a
 * `AlmaService` in it could accidentally get a raw 402 and treat it as a crash.
 */
internal interface AlmaService {

    /* ── auth ──────────────────────────────────────────────────────────── */

    /**
     * The account, minting one if this caller has no token.
     *
     * Safe to call at launch every time. It is also the only route the app
     * calls before it has a token at all, which is why nothing else has to
     * handle "no session yet".
     */
    @GET("/v1/auth/session")
    suspend fun session(): Response<SessionDto>

    @POST("/v1/auth/refresh")
    suspend fun refresh(): Response<SessionDto>

    @POST("/v1/auth/magic-link")
    suspend fun requestMagicLink(@Body body: MagicLinkBody): Response<MagicLinkSent>

    @POST("/v1/auth/magic-link/consume")
    suspend fun consumeMagicLink(@Body body: MagicLinkConsumeBody): Response<SessionDto>

    /**
     * A Google ID token, handed straight over.
     *
     * Never decoded in this app. A token verified on the device is a token
     * verified by whoever controls the device; the signature check against
     * Google's published keys and the audience check that it was minted for
     * *us* both happen server-side.
     */
    @POST("/v1/auth/google")
    suspend fun googleSignIn(@Body body: GoogleSignInBody): Response<SessionDto>

    @POST("/v1/auth/apple")
    suspend fun appleSignIn(@Body body: AppleSignInBody): Response<SessionDto>

    /* ── account ───────────────────────────────────────────────────────── */

    @GET("/v1/account")
    suspend fun account(): Response<JsonObject>

    @PATCH("/v1/account")
    suspend fun setLocale(@Body body: LocaleBody): Response<JsonObject>

    @GET("/v1/account/export")
    suspend fun export(): Response<JsonObject>

    /**
     * The body is required and used to be absent.
     *
     * `confirm` is declared `Body(embed=True)` on the route, so a call with no
     * body was refused 422 by FastAPI before the handler's own check ran — and
     * arrived in the app as `ApiFailure.Invalid`, which reads like a server
     * fault on the one action Play requires every account-creating app to
     * provide. A second, lazily-built `OkHttpClient` in `data/AccountDeletion.kt`
     * used to carry the body around this; that file is gone.
     */
    @POST("/v1/account/delete")
    suspend fun deleteAccount(@Body body: ConfirmBody): Response<JsonObject>

    /* ── places ────────────────────────────────────────────────────────── */

    @GET("/v1/places/search")
    suspend fun searchPlaces(
        @Query("q") query: String,
        @Query("limit") limit: Int = 8,
    ): Response<List<PlaceDto>>

    @GET("/v1/places/timezone")
    suspend fun timezoneAt(
        @Query("latitude") latitude: Double,
        @Query("longitude") longitude: Double,
        @Query("on") on: String? = null,
    ): Response<TimezoneDto>

    /* ── profiles ──────────────────────────────────────────────────────── */

    @GET("/v1/profiles")
    suspend fun profiles(): Response<List<ProfileDto>>

    @POST("/v1/profiles")
    suspend fun saveProfile(@Body body: BirthInput): Response<ProfileDto>

    @GET("/v1/profiles/{id}")
    suspend fun profile(@Path("id") id: String): Response<ProfileDto>

    @PATCH("/v1/profiles/{id}")
    suspend fun updateProfile(@Path("id") id: String, @Body body: BirthInput): Response<ProfileDto>

    @DELETE("/v1/profiles/{id}")
    suspend fun deleteProfile(@Path("id") id: String): Response<Unit>

    /* ── the eight systems ─────────────────────────────────────────────── */

    @POST("/v1/systems/natal")
    suspend fun natal(@Body body: CalcRequest): Response<CalcResultDto>

    @POST("/v1/systems/numerology")
    suspend fun numerology(@Body body: CalcRequest): Response<CalcResultDto>

    @POST("/v1/systems/birth-card")
    suspend fun birthCard(@Body body: CalcRequest): Response<CalcResultDto>

    @POST("/v1/systems/transits")
    suspend fun transits(@Body body: CalcRequest): Response<CalcResultDto>

    @POST("/v1/systems/solar-return")
    suspend fun solarReturn(@Body body: CalcRequest): Response<CalcResultDto>

    @POST("/v1/systems/compatibility")
    suspend fun compatibility(@Body body: CalcRequest): Response<CalcResultDto>

    @POST("/v1/systems/astrocartography")
    suspend fun astrocartography(@Body body: CalcRequest): Response<CalcResultDto>

    @POST("/v1/systems/synthesis")
    suspend fun synthesis(@Body body: CalcRequest): Response<CalcResultDto>

    @GET("/v1/systems/hub")
    suspend fun hub(): Response<HubDto>

    /* ── chapters and readings ─────────────────────────────────────────── */

    /**
     * The table of contents for a system, in the reader's language.
     *
     * `locale` is the same field `ReadingRequest` carries and takes the same
     * six tags; a GET has no body to put it in, so it is a query parameter and
     * nothing else about the convention changes. Without it the backend
     * answers English, which is what every device got until this line existed
     * — and this list is where somebody decides what to read, so the title and
     * the question on it are the two strings that most need to be theirs.
     *
     * Not nullable and not defaulted: a caller has to say. The two screens
     * that call this both hold the account's locale already, and a default of
     * `"en"` here would be a silent way to ship the old bug back.
     */
    @GET("/v1/readings/{system}/chapters")
    suspend fun chapters(
        @Path("system") system: String,
        @Query("locale") locale: String,
    ): Response<ChaptersDto>

    /**
     * Fetch a chapter, writing it the first time it is asked for.
     *
     * This is the call that costs real money — an unwritten chapter goes to the
     * model — and it is the slowest thing in the app. A screen calling it needs
     * a state for "Alma is writing this chapter…", not a spinner.
     */
    @GET("/v1/natal/spheres")
    suspend fun natalSpheres(@Query("locale") locale: String): Response<SpheresResponseDto>

    @POST("/v1/readings")
    suspend fun reading(@Body body: ReadingRequest): Response<ReadingEnvelope>

    /* ── chat ──────────────────────────────────────────────────────────── */

    @POST("/v1/chat")
    suspend fun ask(@Body body: ChatRequest): Response<ChatReplyDto>

    @GET("/v1/chat/threads")
    suspend fun threads(): Response<JsonObject>

    @GET("/v1/chat/threads/{id}")
    suspend fun thread(@Path("id") id: String): Response<JsonObject>

    @GET("/v1/memory")
    suspend fun memory(): Response<MemoryListDto>

    @DELETE("/v1/memory/{id}")
    suspend fun forget(@Path("id") id: String): Response<Unit>

    /* ── billing ───────────────────────────────────────────────────────── */

    @GET("/v1/billing/catalogue")
    suspend fun catalogue(@Query("country") country: String? = null): Response<CatalogueDto>

    @GET("/v1/billing/entitlements")
    suspend fun entitlements(@Query("country") country: String? = null): Response<EntitlementsDto>

    /**
     * Hand one Play purchase to the server to be checked with Google.
     *
     * The **only** route on Android that can result in something being
     * unlocked. There is deliberately no binding for `/v1/billing/checkout`:
     * that is the web's card flow, and an Android build that could open it
     * would be taking money outside Play.
     */
    @POST("/v1/billing/iap/verify")
    suspend fun verifyPurchase(@Body body: IapVerifyBody): Response<IapVerifyResultDto>

    @POST("/v1/billing/subscription/cancel")
    suspend fun cancelSubscription(): Response<CancelResultDto>

    @POST("/v1/billing/declined")
    suspend fun declined(@Body body: DeclinedBody): Response<DeclinedDto>

    /* ── the daily ─────────────────────────────────────────────────────── */
    //
    // The three routes the server actually mounts. All three of the paths that
    // used to be here — `/v1/notifications/device`,
    // `DELETE /v1/notifications/device/{token}` and `/v1/account/daily` —
    // answered 404, and the failures were swallowed at debug level, so the app
    // looked registered and nothing was.

    @POST("/v1/notifications/devices")
    suspend fun registerDevice(@Body body: DeviceRegistrationBody): Response<DeviceRegisteredDto>

    /**
     * Off deletes the row rather than setting a flag. `PUSH.md §6.2(6)`: it is
     * the withdrawal-of-consent obligation, and the simplest possible proof
     * that off means off.
     *
     * A POST with the token in the body. A DELETE with a body is legal and
     * inconsistently supported by proxies, and a token in a URL path is copied
     * into every access log between here and the database.
     */
    @POST("/v1/notifications/devices/delete")
    suspend fun forgetDevice(@Body body: DeviceForgetBody): Response<Unit>

    /**
     * The only writer of `User.daily_push`. Nothing was calling it, so the
     * server-side preference could never leave null and the off path on the
     * server was unreachable.
     */
    @PATCH("/v1/notifications")
    suspend fun setDailyPreference(@Body body: DailySettingsBody): Response<DailySettingsDto>

    @GET("/v1/notifications")
    suspend fun dailySettings(): Response<DailySettingsDto>

    /* ── funnel ────────────────────────────────────────────────────────── */

    @POST("/v1/events")
    suspend fun event(@Body body: EventBody): Response<JsonObject>
}
