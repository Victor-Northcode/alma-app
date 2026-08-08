import Foundation

/// Every response shape the app reads, typed.
///
/// Three conventions run through the whole file, and they are worth stating once
/// here rather than defending eight times below.
///
/// **Snake case is converted, not spelled out.** The decoder is configured with
/// `.convertFromSnakeCase`, so `birth_time` arrives as `birthTime` with no
/// `CodingKeys` block. Hand-written key maps for forty structs is forty places
/// for a typo that compiles and fails at runtime on one field.
///
/// **Dates that are civil dates stay `String`.** `birth_date` is "1998-03-14"
/// and it is *not* an instant — it has no time zone, and turning it into a
/// `Date` attaches the device's, which is how a birthday becomes the day before
/// for anybody east of London. Timestamps that genuinely are instants
/// (`granted_at`, `created_at`) are also `String` on the wire, with a computed
/// `Date?` beside them, so one decoder configuration serves both.
///
/// **Optionals mean the field can be absent.** Nothing here is optional for
/// defensiveness. If the backend always sends a field, it is non-optional, and a
/// missing one is a `malformedResponse` — which is information, where a silent
/// `nil` is not.

// MARK: — the eight systems

/// The eight, as a closed set.
///
/// A `String` would have been less code and would have let a typo reach the
/// server as a 404 the interface has to explain. The raw values are the
/// backend's slugs in `alma/calc/contract.py`, in its order.
enum SystemSlug: String, CaseIterable, Codable, Sendable, Hashable, Identifiable {
    case natal
    case numerology
    case birthCard = "birth-card"
    case transits
    case solarReturn = "solar-return"
    case compatibility
    case astrocartography
    case synthesis

    var id: String { rawValue }

    /// How many chapters this system has. From `alma/ai/chapters.py`; forty-one
    /// in total, which is what "the archive" means.
    var chapterCount: Int {
        switch self {
        case .natal: 16
        case .numerology: 5
        case .birthCard, .transits, .solarReturn, .astrocartography: 3
        case .compatibility, .synthesis: 4
        }
    }

    /// Whether this system changes with time, and therefore whether a
    /// subscription can honestly sell it. Mirrors `LIVING_SYSTEMS` in
    /// `alma/billing/catalogue.py` — a natal chart bought monthly would be rent
    /// on a number that has not moved since birth.
    var isLiving: Bool {
        switch self {
        case .transits, .solarReturn, .compatibility: true
        case .natal, .numerology, .birthCard, .astrocartography, .synthesis: false
        }
    }

    /// The path segment on `/v1/systems/…`. The same as the slug, and named so
    /// that a call site reads as a URL rather than as a coincidence.
    var path: String { rawValue }
}

// MARK: — identity

/// What `/v1/auth/*` returns. The account is real from the first request; this
/// is what it says about itself.
struct AlmaSessionInfo: Codable, Sendable, Equatable {
    let token: String
    let userId: String
    let isGuest: Bool
    let email: String?
    let displayName: String?
    let locale: String
}

/// The fuller picture from `GET /v1/account`.
struct AlmaAccount: Codable, Sendable, Equatable {
    let id: String
    let email: String?
    let displayName: String?
    /// `"guest"`, `"apple"`, `"google"`, `"email"`.
    let provider: String?
    let locale: String
    let isGuest: Bool
    let createdAt: String
    /// Which systems this account may read in full.
    let unlocked: [String]
}

// MARK: — birth data

/// One birth, as the app sends it.
///
/// `birthTime` absent is a first-class state and the only representation of
/// not-knowing — no empty string, no `"unknown"`, no noon. The backend's
/// validator enforces the same thing from the other side.
struct BirthInput: Codable, Sendable, Equatable {
    /// "YYYY-MM-DD", civil.
    var birthDate: String
    /// "HH:MM" in 24-hour form, or `nil`.
    var birthTime: String?
    var latitude: Double
    var longitude: Double
    /// An IANA zone the backend knows. An unrecognised one is refused rather
    /// than defaulted, because a chart silently computed in UTC looks exactly
    /// like a correct one.
    var timezone: String
    var placeLabel: String?
    var placeId: Int?
    var name: String?
    /// `"raise"` asks the server to report a daylight-saving ambiguity instead
    /// of picking; the two other values answer it.
    var onAmbiguous: String?

    init(
        birthDate: String,
        birthTime: String? = nil,
        latitude: Double,
        longitude: Double,
        timezone: String,
        placeLabel: String? = nil,
        placeId: Int? = nil,
        name: String? = nil,
        onAmbiguous: String? = nil
    ) {
        self.birthDate = birthDate
        self.birthTime = birthTime
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.placeLabel = placeLabel
        self.placeId = placeId
        self.name = name
        self.onAmbiguous = onAmbiguous
    }
}

/// A saved birth — the account owner's, or somebody they are comparing against.
struct Profile: Codable, Sendable, Equatable, Identifiable {
    let id: String
    let name: String?
    /// "partner", "mother", … — free text, and `nil` when nothing was said.
    let relation: String?
    /// Whether this is the account owner. Exactly one profile has it.
    let isSelf: Bool
    let birthDate: String
    let birthTime: String?
    let latitude: Double
    let longitude: Double
    let timezone: String
    let placeLabel: String?

    var birthTimeKnown: Bool { birthTime != nil }
}

/// A place from the gazetteer.
struct Place: Codable, Sendable, Equatable, Identifiable, Hashable {
    let id: Int
    let name: String
    let region: String?
    let country: String
    let countryCode: String
    /// What the row is shown as — "Milan, Lombardy, Italy".
    let label: String
    let latitude: Double
    let longitude: Double
    let timezone: String
}

/// What `/v1/places/timezone` answers.
struct TimezoneAt: Codable, Sendable, Equatable {
    let timezone: String
    /// "+01:00".
    let offset: String
    let offsetHours: Double
}

// MARK: — calculation

/// Whether this account may read a thing, and why not.
struct Access: Codable, Sendable, Equatable {
    let allowed: Bool
    /// The server's own sentence. Rendered as-is; it arrives in the account's
    /// language.
    let reason: String
    /// `"free"`, `"door"`, `"archive"`, `"subscription"` — or `nil` when
    /// nothing grants it.
    let kind: String?
    let expiresAt: String?
}

/// One system's answer.
///
/// `data` is `JSONValue` because the eight systems return eight different
/// shapes and there is no honest common type — see `JSONValue`. A screen that
/// renders one system decodes the branch it knows.
///
/// **A locked result is still a real result.** The backend strips `data` down to
/// a preview and empties `factors`, and sets `locked`. Every calculation is free
/// forever; what is sold is the written interpretation, so a locked response is
/// not an error and must not be treated as one.
struct CalcResult: Codable, Sendable, Equatable {
    let system: String
    let engineVersion: String
    let computedAt: String
    /// The birth this was computed from, echoed back.
    let subject: JSONValue
    /// The system's own payload — trimmed to `PREVIEW_FIELDS` when locked.
    let data: JSONValue
    /// The citable positions. Empty when locked.
    let factors: [String]
    /// What could not be computed, and is honestly reported rather than faked —
    /// houses without a birth time, chiefly.
    let unavailable: [String]
    let notes: [String]
    let provenance: JSONValue
    let access: Access
    let locked: Bool?

    var isLocked: Bool { locked ?? false }

    var slug: SystemSlug? { SystemSlug(rawValue: system) }
}

// MARK: — the cabinet

/// One row of the hub.
struct HubEntry: Codable, Sendable, Equatable, Identifiable {
    /// Typed, unlike `status` below, and the asymmetry is deliberate. A ninth
    /// system is a product change — it needs a tab, an icon, a chapter list and
    /// a store product — so an app that cannot decode one is telling the truth
    /// about itself. A ninth *status* is a backend detail the hub can render as
    /// an unfamiliar word without lying to anybody.
    let slug: SystemSlug
    let unlocked: Bool
    /// `"calculated"`, `"open"`, `"needs-time"`, `"add-person"`, `"not-yet"`.
    /// A `String` and not an enum on purpose: this is the one field where the
    /// backend adding a state should degrade to showing an unfamiliar word,
    /// not to a decoding failure that blanks the whole hub.
    let status: String

    var id: SystemSlug { slug }
}

/// Everything the cabinet's front page needs in one request.
struct Hub: Codable, Sendable, Equatable {
    let hasBirthData: Bool
    let birthTimeKnown: Bool
    /// How many *other* people are saved. Compatibility needs at least one.
    let people: Int
    let systems: [HubEntry]
}

/// One chapter in a table of contents.
struct ChapterEntry: Codable, Sendable, Equatable, Identifiable {
    let slug: String
    /// "I", "II", "XVI" — set in the serif, as type.
    let numeral: String
    let index: Int
    let title: String
    /// The question this chapter answers, in the person's own language.
    let question: String
    /// Whether this is the system's one free chapter.
    let free: Bool
    /// Whether this account may open it now.
    let open: Bool
    /// Whether it has already been written. A written chapter opens instantly
    /// and says the same thing it said last time.
    let written: Bool
    let needsBirthTime: Bool

    var id: String { slug }
}

struct ChapterList: Codable, Sendable, Equatable {
    let system: String
    let chapters: [ChapterEntry]
    let total: Int
}

/// One written chapter. This is the product.
struct Reading: Codable, Sendable, Equatable {
    let system: String
    let chapter: String
    let title: String
    /// The first line, which is free even when the chapter is not.
    let teaser: String
    let body: [String]
    /// Optional because not every chapter ends with one, and an empty string
    /// rendered as a heading with nothing under it is worse than no heading.
    let advice: String?
    /// The positions this text was read from. Every sentence cites one — it is
    /// the thing that makes Alma different from a horoscope feed, and the
    /// screen must show it rather than bury it.
    let citedFactors: [String]
    /// The same, pre-formatted: "Read from: Sun 23° Pisces in the 8th · …".
    let readFrom: String
    let model: String
}

struct ReadingResponse: Codable, Sendable, Equatable {
    let reading: Reading
    /// Whether it came from storage. A chapter is written once and returned
    /// forever; `false` means the person just paid for the writing to happen.
    let cached: Bool
    let createdAt: String?
}

// MARK: — conversation

struct ChatMessage: Codable, Sendable, Equatable, Identifiable {
    let id: String
    /// `"user"` or `"alma"`.
    let role: String
    let body: String
    let citedFactors: [String]
    /// Whether the answer came out of the chart.
    ///
    /// **Superseded, and kept only so an older backend still renders.** It is a
    /// single boolean carrying two unrelated meanings — "I looked and the chart
    /// is silent" and "this reply asserts nothing about you" — which is how a
    /// greeting came to be stamped NOT FROM YOUR CHART. `turnKind` is what the
    /// interface reads; see `ChatTurnKind`.
    let answeredFromChart: Bool?
    /// What kind of turn this was: `reading`, `chart_silent`, `conversation`,
    /// `care`. Optional because a thread written before the field existed has
    /// none, and because `GET /v1/chat/threads/{id}` may lag `/v1/chat`.
    /// Decoded as a `String` rather than as `ChatTurnKind` on purpose: a value
    /// this build has never heard of must degrade to an ordinary reply, not
    /// fail the decode and blank somebody's conversation.
    let turnKind: String?
    let createdAt: String
}

struct ChatReply: Codable, Sendable, Equatable {
    let threadId: String
    let message: ChatMessage
    /// `nil` when there is no ceiling. Zero means the next question is refused.
    let questionsLeft: Int?
}

struct ChatThreadSummary: Codable, Sendable, Equatable, Identifiable {
    let id: String
    let title: String?
    let updatedAt: String
}

struct ChatThreadList: Codable, Sendable, Equatable {
    let threads: [ChatThreadSummary]
}

struct ChatThread: Codable, Sendable, Equatable, Identifiable {
    let id: String
    let title: String?
    let messages: [ChatMessage]
}

// MARK: — the ladder

/// One price.
///
/// Prices on iOS are shown from StoreKit, not from `display` — Apple is the
/// merchant of record and its localised price string is the one the buyer is
/// actually charged. This entry is still needed for everything *around* the
/// price: which key the ladder offers, what it grants, whether it renews, and
/// whether it may be shown at all.
struct CatalogueItem: Codable, Sendable, Equatable, Identifiable {
    /// The catalogue key — "natal", "archive", "monthly", "annual".
    let slug: String
    /// What it unlocks: a system slug, or "*" for everything.
    let system: String
    let name: String
    /// `"one_time"`, `"monthly"`, `"annual"`.
    let kind: String
    /// `""`, `"month"`, `"year"`.
    let interval: String
    /// `"system"`, `"all"`, `"live"`.
    let scope: String
    /// `"shelf"`, `"in-checkout"`, `"after-door"`. Anything that is not
    /// `"shelf"` must never be rendered on its own — the conditional prices are
    /// cheaper than the shelf item they stand in for and grant the same thing.
    let offered: String
    let cents: Int
    /// The server's formatted price. Kept for parity with the web app and for
    /// support tooling; **the store's own price string is what a screen shows.**
    let display: String
    /// Set when this row substitutes another — the upgrade shown where the
    /// archive would be.
    let replaces: String?
    let creditCents: Int?

    var id: String { slug }
    var isOnTheShelf: Bool { offered == "shelf" }
}

struct Catalogue: Codable, Sendable, Equatable {
    let currency: String
    let items: [CatalogueItem]
}

/// One grant.
struct EntitlementRow: Codable, Sendable, Equatable {
    /// A system slug, or "*".
    let system: String
    let kind: String
    let scope: String
    let grantedAt: String
    let expiresAt: String?
    let renewsAt: String?
    /// Whether this grant is still in force. Computed server-side; a client
    /// comparing dates would get subscriptions wrong.
    let active: Bool
    /// Who sold it — `"appstore"`, `"googleplay"`, a card processor's name, or
    /// `"unknown"` for a grant made by hand.
    ///
    /// Optional because a backend older than this build does not send it, and a
    /// missing seller must degrade to saying less rather than to failing the
    /// whole entitlements decode. The account screen uses it to choose between
    /// two true sentences about a renewal: Apple sends the receipt and the
    /// warning for a plan bought in this app, and we send both for one bought on
    /// the web with a card.
    let source: String?

    /// Whether a store owns this grant, and therefore owns its cancellation.
    var boughtInAStore: Bool {
        source == "appstore" || source == "googleplay"
    }
}

/// What this account holds.
struct Entitlements: Codable, Sendable, Equatable {
    /// The systems that may be read in full. The one field most screens want.
    let unlocked: [String]
    let entitlements: [EntitlementRow]
    let currency: String
    /// A credit toward the archive, from a door bought inside the window.
    let annualCreditCents: Int?

    static let none = Entitlements(
        unlocked: [], entitlements: [], currency: "USD", annualCreditCents: nil
    )

    func unlocks(_ system: SystemSlug) -> Bool {
        unlocked.contains(system.rawValue) || unlocked.contains("*")
    }
}

// MARK: — small replies

struct MagicLinkSent: Codable, Sendable, Equatable {
    let sent: Bool
    /// Only present in development builds of the backend.
    let debugToken: String?
}

struct SubscriptionCancelled: Codable, Sendable, Equatable {
    let cancelled: Bool
    let provider: String
    let subscriptionIds: [String]
    /// The period is paid for and runs to the end. This is that date — not a
    /// cancellation date, and the sentence the settings screen has to be able
    /// to say.
    let accessUntil: String?
}

struct AccountDeleted: Codable, Sendable, Equatable {
    let deleted: Bool
}

struct LocaleUpdated: Codable, Sendable, Equatable {
    let locale: String
    let displayName: String?
}

// MARK: — the funnel

/// Where somebody has got to. A closed set, because the table is only worth
/// having if every row can be counted and one misspelt name is a cohort that
/// silently disappears.
///
/// `purchase` is deliberately absent: money is known from the store's signed
/// transaction, never from the client. The client may say the sheet closed,
/// which is `purchaseCompleted`.
enum FunnelStage: String, Sendable, CaseIterable {
    case landingView = "landing_view"
    case quizStart = "quiz_start"
    case quizComplete = "quiz_complete"
    case portraitView = "portrait_view"
    case offerView = "offer_view"
    case checkoutOpened = "checkout_opened"
    case purchaseCompleted = "purchase_completed"
    case offerDeclined = "offer_declined"
}

// MARK: — instants

extension String {
    /// An ISO-8601 timestamp from the backend as a `Date`.
    ///
    /// Both formats are tried because the backend's `isoformat()` emits
    /// fractional seconds for some columns and not for others, and
    /// `ISO8601DateFormatter` will not parse one with the options for the
    /// other — a mismatch that shows up as a missing renewal date on the
    /// settings screen and nowhere else.
    var almaInstant: Date? {
        let withFraction = ISO8601DateFormatter()
        withFraction.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = withFraction.date(from: self) { return date }

        let plain = ISO8601DateFormatter()
        plain.formatOptions = [.withInternetDateTime]
        return plain.date(from: self)
    }
}

// MARK: — the natal spheres

/// One free sphere of the natal preview: two plain sentences, the factors they
/// were read from, and the chapter that finishes the thought.
struct SphereBlock: Decodable, Identifiable, Sendable, Equatable {
    let sphere: String
    let chapter: String
    let title: String
    let text: String
    let factors: [String]

    var id: String { sphere }
}

struct SpheresResponse: Decodable, Sendable {
    let spheres: [SphereBlock]
    let cached: Bool
    let locale: String
}
