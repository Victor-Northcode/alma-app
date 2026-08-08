package ai.pazl.alma.data.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject

/**
 * The wire shapes, one file, mirroring `backend/alma/api/schemas.py`.
 *
 * Two rules hold throughout.
 *
 * **Optional means absent, not null.** Several request bodies on the backend
 * are `ConfigDict(extra="forbid")` Pydantic models, and a few of the fields
 * they accept are validated patterns with defaults. Sending an explicit `null`
 * where the server expects the field to be missing is a 422 that reads like a
 * server bug. The `Json` instance in `AlmaHttp` is configured with
 * `encodeDefaults = false` and `explicitNulls = false` so that a Kotlin default
 * simply does not appear on the wire — which is why every optional below has
 * one.
 *
 * **A calculation's `data` is not typed here, and that is deliberate.** Each of
 * the eight systems returns a different `data` object, several of them nested
 * three deep, and all of them are the *engine's* shape rather than the API's —
 * they change when the ephemeris code changes. Typing them here would mean this
 * file has to be edited in lockstep with the calculation service, and a screen
 * that renders a field the engine renamed would fail to compile rather than
 * fail to draw. The escape hatch is `JsonObject`, and the screens that read one
 * are expected to decode the slice they need. What *is* typed is everything the
 * skeleton and the paywall depend on: `access`, `factors`, `locked`.
 */

/* ── session and account ───────────────────────────────────────────────── */

@Serializable
data class SessionDto(
    val token: String,
    @SerialName("user_id") val userId: String,
    @SerialName("is_guest") val isGuest: Boolean,
    val email: String? = null,
    @SerialName("display_name") val displayName: String? = null,
    val locale: String = "en",
)

@Serializable
data class MagicLinkSent(
    val sent: Boolean = true,
    /** Only ever populated by a development backend. Never shown in a store build. */
    @SerialName("debug_token") val debugToken: String? = null,
)

@Serializable
data class GoogleSignInBody(val credential: String)

@Serializable
data class AppleSignInBody(
    @SerialName("identity_token") val identityToken: String,
    @SerialName("full_name") val fullName: String? = null,
)

@Serializable
data class MagicLinkBody(val email: String, val locale: String = "en")

@Serializable
data class MagicLinkConsumeBody(val token: String)

@Serializable
data class LocaleBody(val locale: String)

/* ── places ────────────────────────────────────────────────────────────── */

@Serializable
data class PlaceDto(
    val id: Int,
    val name: String,
    val region: String? = null,
    val country: String,
    @SerialName("country_code") val countryCode: String,
    /** What the picker shows: "Kyiv, Ukraine". Already assembled by the server. */
    val label: String,
    val latitude: Double,
    val longitude: Double,
    val timezone: String,
)

@Serializable
data class TimezoneDto(
    val timezone: String,
    val offset: String,
    @SerialName("offset_hours") val offsetHours: Double,
)

/* ── birth data and profiles ───────────────────────────────────────────── */

/**
 * One birth, as this app sends it.
 *
 * [birthTime] is nullable and the null means *not known* rather than midnight.
 * The distinction is the whole reason several systems can be marked unavailable
 * instead of being computed from an assumed noon — an invented time puts an
 * Ascendant in the wrong sign about half the time, and the product's first rule
 * is that nothing is shown that was not calculated.
 *
 * [onAmbiguous] defaults to `"raise"`, which is what makes a daylight-saving
 * ambiguity come back as a question the interface asks. Send `"earlier"` or
 * `"later"` only after the person has actually chosen one.
 */
@Serializable
data class BirthInput(
    @SerialName("birth_date") val birthDate: String,
    @SerialName("birth_time") val birthTime: String? = null,
    val latitude: Double,
    val longitude: Double,
    val timezone: String,
    @SerialName("place_label") val placeLabel: String? = null,
    @SerialName("place_id") val placeId: Int? = null,
    val name: String? = null,
    @SerialName("on_ambiguous") val onAmbiguous: String? = null,
    @SerialName("is_self") val isSelf: Boolean? = null,
    val relation: String? = null,
    /** The language a refusal should arrive in — the partner-limit 402 answers
     * from this rather than from the account's stored locale. */
    val locale: String? = null,
)

@Serializable
data class ProfileDto(
    val id: String,
    val name: String? = null,
    val relation: String? = null,
    @SerialName("is_self") val isSelf: Boolean,
    @SerialName("birth_date") val birthDate: String,
    @SerialName("birth_time") val birthTime: String? = null,
    val latitude: Double,
    val longitude: Double,
    val timezone: String,
    @SerialName("place_label") val placeLabel: String? = null,
)

/* ── the eight systems ─────────────────────────────────────────────────── */

@Serializable
data class CalcRequest(
    @SerialName("profile_id") val profileId: String? = null,
    val birth: BirthInput? = null,
    @SerialName("house_system") val houseSystem: String? = null,
    val locale: String? = null,
    // transits
    val days: Int? = null,
    @SerialName("include_moon") val includeMoon: Boolean? = null,
    val start: String? = null,
    // solar return
    val year: Int? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    // compatibility
    @SerialName("other_profile_id") val otherProfileId: String? = null,
    val other: BirthInput? = null,
)

/**
 * Whether this account may read this thing, decided by the server.
 *
 * The client never computes one. See the note on `AlmaClient.verifyPurchase`
 * for why that rule exists and what happened the last time it was bent.
 */
@Serializable
data class AccessDto(
    val allowed: Boolean,
    val reason: String,
    val kind: String? = null,
    @SerialName("expires_at") val expiresAt: String? = null,
)

@Serializable
data class CalcResultDto(
    val system: String,
    @SerialName("engine_version") val engineVersion: String,
    @SerialName("computed_at") val computedAt: String,
    val subject: JsonObject = JsonObject(emptyMap()),
    /** The engine's own shape. Decode the slice your screen needs. */
    val `data`: JsonObject = JsonObject(emptyMap()),
    /**
     * The placements every written sentence is allowed to cite. Trimmed to
     * empty by the server when the system is locked, which is why a paywalled
     * screen can show the calculation and not the argument.
     */
    val factors: List<String> = emptyList(),
    /** What could not be computed, and is therefore not shown. Never invented. */
    val unavailable: List<String> = emptyList(),
    val notes: List<String> = emptyList(),
    val provenance: JsonObject = JsonObject(emptyMap()),
    val access: AccessDto,
    val locked: Boolean = false,
)

@Serializable
data class HubEntryDto(
    val slug: String,
    val unlocked: Boolean,
    /** "calculated" · "open" · "needs-time" · "add-person" · "not-yet". */
    val status: String,
)

@Serializable
data class HubDto(
    @SerialName("has_birth_data") val hasBirthData: Boolean,
    @SerialName("birth_time_known") val birthTimeKnown: Boolean,
    val people: Int,
    val systems: List<HubEntryDto>,
)

/* ── chapters and readings ─────────────────────────────────────────────── */

@Serializable
data class ChapterEntryDto(
    val slug: String,
    /** "I", "II", "III" — the chapter numeral, set in the serif. */
    val numeral: String,
    val index: Int,
    val title: String,
    val question: String,
    val free: Boolean,
    val `open`: Boolean,
    /**
     * Whether this chapter has been written for this account *already*.
     *
     * Not the same as `open`, and the difference is the one the copy on the
     * paywall was rewritten over: a chapter that is open has been paid for; a
     * chapter that is written exists. Nothing is written until it is first
     * opened, so an interface must never promise that text is waiting.
     */
    val written: Boolean,
    @SerialName("needs_birth_time") val needsBirthTime: Boolean,
)

@Serializable
data class ChaptersDto(
    val system: String,
    val chapters: List<ChapterEntryDto>,
    val total: Int,
)

@Serializable
data class ReadingRequest(
    val system: String,
    val chapter: String? = null,
    val locale: String? = null,
    @SerialName("profile_id") val profileId: String? = null,
    val birth: BirthInput? = null,
    @SerialName("house_system") val houseSystem: String? = null,
    @SerialName("partner_profile_id") val partnerProfileId: String? = null,
)

@Serializable
data class ReadingDto(
    val system: String,
    val chapter: String,
    val title: String,
    /** Always readable, even locked. The promise of the chapter. */
    val teaser: String,
    val body: List<String> = emptyList(),
    val advice: String = "",
    /** The placements this text was read from. Rendered in the serif, in gold. */
    @SerialName("cited_factors") val citedFactors: List<String> = emptyList(),
    @SerialName("read_from") val readFrom: String = "",
    val model: String = "",
)

/**
 * One sphere of the free natal preview — two or three plain sentences, the
 * factors they cite, and the slug of the chapter that finishes the thought.
 */
@Serializable
data class SphereBlockDto(
    val sphere: String,
    val chapter: String,
    /** The chapter's title in this locale, added by the server. */
    val title: String,
    val text: String,
    val factors: List<String> = emptyList(),
)

@Serializable
data class SpheresResponseDto(
    val spheres: List<SphereBlockDto>,
    val cached: Boolean = false,
    val locale: String = "",
)

@Serializable
data class ReadingEnvelope(
    val reading: ReadingDto,
    /** True when this chapter had already been written. It says the same thing tomorrow. */
    val cached: Boolean = false,
    /** The chapter is real and unpaid: first paragraph in the clear, the rest
     * rendered under blur with the unlock button on top. */
    val preview: Boolean = false,
)

/* ── chat ──────────────────────────────────────────────────────────────── */

@Serializable
data class ChatRequest(
    val message: String,
    @SerialName("thread_id") val threadId: String? = null,
    @SerialName("profile_id") val profileId: String? = null,
    val locale: String? = null,
)

@Serializable
data class ChatMessageDto(
    val id: String,
    val role: String,
    val body: String,
    @SerialName("cited_factors") val citedFactors: List<String> = emptyList(),
    /**
     * Whether this answer came out of the chart or out of the model's general
     * knowledge.
     *
     * **Superseded by [turnKind], and kept only so an older backend still
     * renders.** One boolean turned out to carry two unrelated meanings — "I
     * looked and your chart is silent" and "this reply asserts nothing about
     * you at all" — and the second is what a greeting is. Rendering the second
     * as the first is how a person who typed "hello" was told their hello was
     * not in their chart.
     */
    @SerialName("answered_from_chart") val answeredFromChart: Boolean = false,
    /**
     * What kind of turn this was: `reading`, `chart_silent`, `conversation`,
     * `care`. See `ChatTurnKind`.
     *
     * A `String?` and not the enum, deliberately, and for the same reason
     * [HubDto]'s status is a string: a value this build has never heard of must
     * degrade to an ordinary reply, not throw inside the deserialiser and blank
     * a conversation somebody is in the middle of having.
     */
    @SerialName("turn_kind") val turnKind: String? = null,
    @SerialName("created_at") val createdAt: String = "",
)

@Serializable
data class ChatReplyDto(
    @SerialName("thread_id") val threadId: String,
    val message: ChatMessageDto,
    /** Null when unlimited. Zero is a real answer and not the same as null. */
    @SerialName("questions_left") val questionsLeft: Int? = null,
)

@Serializable
data class MemoryDto(val id: String, val body: String)

@Serializable
data class MemoryListDto(val memory: List<MemoryDto> = emptyList())

/* ── billing ───────────────────────────────────────────────────────────── */

/**
 * One thing on the shelf.
 *
 * [display] is the price already formatted by the server, in the currency this
 * account is priced in, and it is the **only** thing an interface may put in
 * front of a person. Never format [cents] yourself and never type a price into
 * a layout: the ladder is regional, `backend/alma/billing/catalogue.py` is the
 * source of truth for all of it, and a hardcoded "$5.99" is wrong in twelve of
 * the thirteen currencies before it is wrong in the thirteenth.
 */
@Serializable
data class CatalogueItemDto(
    val slug: String,
    val system: String? = null,
    val name: String,
    /** "one_time" or "subscription". */
    val kind: String,
    val interval: String? = null,
    val scope: String? = null,
    /**
     * Where in the funnel this price is allowed to appear: "shelf",
     * "in-checkout" or "after-door".
     *
     * A **string**, and it was typed here as a boolean — which is not a wrong
     * name for a right value, it is a decode failure. kotlinx.serialization is
     * configured with `isLenient = false`, so `"offered": "shelf"` arriving in
     * a `Boolean` throws, the exception is classified as `Unexpected`, and
     * every call to `/v1/billing/catalogue` fails. The paywall is the only
     * screen that reads this endpoint, so nothing noticed until there was one.
     *
     * In practice only "shelf" ever arrives: `catalogue()` filters on
     * `Product.on_the_shelf` before it serialises, and `archive-upgrade` is
     * substituted *in* rather than listed, carrying "after-door" with it. The
     * client does not branch on this — what may be sold is decided by whether
     * the server listed it at all, plus the app's own refusal to sell a
     * conditional price (`ai.pazl.alma.billing.StoreProducts.sellable`) — but
     * it has to be able to *parse* it.
     */
    val offered: String = "shelf",
    val cents: Int,
    val display: String,
    /** Set on `archive-upgrade`: the product it stands in for. */
    val replaces: String? = null,
    @SerialName("credit_cents") val creditCents: Int? = null,
)

@Serializable
data class CatalogueDto(
    val currency: String,
    val items: List<CatalogueItemDto> = emptyList(),
    /** Which processor is live for the *web*. On Android the store is Play. */
    val provider: String? = null,
    @SerialName("requires_email") val requiresEmail: Boolean = false,
    /** Who legally sells to this person, published rather than compiled in. */
    val merchant: String? = null,
    /**
     * Where a subscriber goes to stop paying, when that is not us.
     *
     * Filled in only by the store adapters. On Android the cancel control must
     * be a link to Play's own subscription screen — an app that merely *says*
     * "cancel in Play" fails review, and an app that offers its own cancel
     * button for a Play subscription cannot honour it.
     */
    @SerialName("manage_url") val manageUrl: String? = null,
    val unlocked: List<String> = emptyList(),
)

@Serializable
data class EntitlementDto(
    val system: String,
    val kind: String,
    val scope: String,
    @SerialName("granted_at") val grantedAt: String,
    @SerialName("expires_at") val expiresAt: String? = null,
    @SerialName("renews_at") val renewsAt: String? = null,
    val active: Boolean,
)

@Serializable
data class EntitlementsDto(
    /** The list the paywall reads. Systems this account may read in full. */
    val unlocked: List<String> = emptyList(),
    val entitlements: List<EntitlementDto> = emptyList(),
    val currency: String = "USD",
    @SerialName("annual_credit_cents") val annualCreditCents: Int = 0,
)

/**
 * A Play purchase, handed to the server to be checked against Google.
 *
 * [transaction] is the Play *purchase token*. It is not evidence of anything on
 * its own — the server exchanges it with the Play Developer API and grants from
 * what Google says, never from what this app claims.
 */
@Serializable
data class IapVerifyBody(
    /**
     * Always `"googleplay"` from this app; iOS sends `"appstore"`.
     *
     * The name has to be one `alma/billing/provider.py::provider_for` branches
     * on, because one backend answers both apps and resolves the adapter from
     * this field rather than from its own configuration. This doc comment said
     * `"google"` and so did the call site, which meant every verification was
     * refused 400 `unknown_platform` before Google was contacted at all.
     */
    val platform: String,
    /** A catalogue slug: "natal", "archive", "monthly", … */
    val product: String,
    val transaction: String,
)

@Serializable
data class IapVerifyResultDto(
    /** "granted", "already_claimed", … For the log; the interface reads [unlocked]. */
    val status: String,
    val platform: String,
    val product: String,
    @SerialName("transaction_id") val transactionId: String? = null,
    @SerialName("subscription_id") val subscriptionId: String? = null,
    /**
     * What this account may now read, straight from the same request.
     *
     * Returned here so the app never has to guess how long to wait before
     * re-fetching entitlements after a purchase.
     */
    val unlocked: List<String> = emptyList(),
    @SerialName("expires_at") val expiresAt: String? = null,
)

@Serializable
data class CancelResultDto(
    val cancelled: Boolean,
    val provider: String,
    @SerialName("subscription_ids") val subscriptionIds: List<String> = emptyList(),
    /**
     * The sentence the interface has to be able to say. Not a cancellation
     * date — the period is paid for and runs to its end.
     */
    @SerialName("access_until") val accessUntil: String? = null,
)

@Serializable
data class DeclinedOfferDto(val slug: String, val display: String, val cents: Int)

@Serializable
data class DeclinedDto(val offer: DeclinedOfferDto? = null)

@Serializable
data class DeclinedBody(val system: String? = null, val country: String? = null)

/* ── funnel ────────────────────────────────────────────────────────────── */

/**
 * One funnel stage.
 *
 * The names are fixed by `backend/alma/funnel.py` and an unknown one is a 422
 * listing the valid set. See [ai.pazl.alma.data.FunnelStage] for the list this
 * app is allowed to send.
 */
@Serializable
data class EventBody(
    val stage: String,
    val meta: Map<String, String>? = null,
    val properties: Map<String, JsonElement>? = null,
)

/**
 * The one field `POST /v1/account/delete` requires.
 *
 * What goes in it is whatever this account can be asked for: its email address
 * when it has one, and otherwise its own id — a guest has no address, and the
 * whole point of the route is that they may still delete what we hold about
 * them. The server makes the same comparison; see `account.py::delete`.
 */
@Serializable
data class ConfirmBody(val confirm: String)

/* ── errors ────────────────────────────────────────────────────────────── */

/**
 * The body of a refusal.
 *
 * FastAPI wraps everything in `detail`, and `detail` is *sometimes a string and
 * sometimes an object* depending on which line raised it — both shapes are all
 * over the backend. That is why this is a `JsonElement` and why the classifier
 * in `AlmaHttp` unpicks it by hand rather than by declaring a type.
 */
@Serializable
data class ErrorEnvelope(val detail: JsonElement? = null)

/* ── the daily ─────────────────────────────────────────────────────────── */

/**
 * What `POST /v1/notifications/device` carries.
 *
 * The shape is `docs/PUSH.md §3`'s table, minus the columns the server fills in
 * for itself. Every field earns its place: [environment] is §1.8's whole
 * argument, [timezone] is what lets an hourly job find 08:00 in this person's
 * day, and the two version strings are what makes "it stopped working on the
 * 14th" answerable.
 *
 * **`preference` and `hour` are deliberately not here, and they used to be.**
 * The route's `DeviceIn` sets `extra="forbid"`, so sending them answered
 * `422 extra_forbidden` and the whole registration failed — which
 * [ai.pazl.alma.notify.DailyController] then swallowed at debug level. They
 * belong on the user rather than the install anyway: a person has one
 * preference and possibly several phones, and two devices disagreeing about
 * the delivery hour is a question with no correct answer. They go through
 * `PATCH /v1/notifications` instead.
 */
@Serializable
data class DeviceRegistrationBody(
    val platform: String,
    val token: String,
    /**
     * `sandbox` or `production`. Always `production` from Android — FCM has one
     * host — and on the wire from both platforms so that one column answers the
     * question for both rather than a nullable one that means "iOS only".
     */
    val environment: String,
    /** An IANA identifier. Never an offset: an offset cannot survive a DST change. */
    val timezone: String,
    @SerialName("app_version") val appVersion: String,
    @SerialName("os_version") val osVersion: String,
    /**
     * The device's language, which is what decides which `body_loc_key`
     * translation Android will substitute. `PUSH.md §1.6`: the account's locale
     * is the fallback, the device is the truth.
     */
    val locale: String,
)

/** What the server answers a registration with: the row it kept. */
@Serializable
data class DeviceRegisteredDto(val platform: String = "", val token: String = "")

/**
 * What `POST /v1/notifications/devices/delete` carries.
 *
 * **A body, not a path segment.** The token used to be interpolated into the
 * URL, which writes a persistent device identifier into access logs, proxy
 * logs and APM traces — none of them covered by the retention rules in
 * `notify/tokens.py`, none cleared by `accounts.erase`, and none described in
 * the privacy documentation. The route that created those copies was the one a
 * person hits to *withdraw* consent.
 */
@Serializable
data class DeviceForgetBody(val platform: String, val token: String)

/**
 * What `PATCH /v1/notifications` carries — the user-level half.
 *
 * These belong on the **user** and not the profile: a person has one phone and
 * several charts. Every field is optional because the route treats each
 * independently — somebody turning the daily off is not also restating their
 * delivery hour. `daily` is the server's name for the position; `preference`
 * was ours and nothing answered to it.
 */
@Serializable
data class DailySettingsBody(
    val daily: String? = null,
    val hour: Int? = null,
    /** An override. Null means "use the ladder": chosen → device → birth. */
    val timezone: String? = null,
)

/** What `GET|PATCH /v1/notifications` answers with. */
@Serializable
data class DailySettingsDto(
    val daily: String = "off",
    val chosen: Boolean = false,
    val hour: Int = 8,
    @SerialName("quiet_hours") val quietHours: List<Int> = emptyList(),
    val timezone: String? = null,
    @SerialName("timezone_source") val timezoneSource: String = "device",
    val entitled: Boolean = false,
)
