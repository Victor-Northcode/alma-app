import Foundation

/// The rungs of the ladder, as a closed set, and the one place that knows how a
/// catalogue slug becomes an App Store product id.
///
/// **Why an enum when the server sends strings.** The catalogue arrives as JSON
/// and every slug in it is a `String`; the paywall then has to ask three
/// questions of each one — what to call it, whether it renews, and which
/// StoreKit product to fetch — and a `String` answers none of them. Doing it with
/// dictionaries keyed by string means a typo compiles and shows an untitled row
/// with no price. A slug the server sends and this enum does not model is
/// *skipped*, which is the honest degradation: a rung we cannot name, cannot
/// price and cannot describe is a rung we must not put a price button under.
/// (Contrast `HubEntry.slug`, which fails to decode on purpose — a ninth system
/// is an app release, a thirteenth price is not.)
///
/// **The raw value is the catalogue key, and the catalogue key is no longer a
/// system slug.** In v3 the shelf is not "eight doors and an archive" any more,
/// so `natal` stopped being the name of a *product* and became the name of what
/// a product opens. The key is `door.natal`; the system is a separate property
/// below, and it has to be, because `SystemSlug(rawValue: "door.natal")` is nil
/// — a rung that could not name its system would render with no title.
///
/// **Only the three systems that never change have doors.** Transits and the
/// solar return recompute — a transit reading sold "permanently" is a
/// subscription nobody charged for — and compatibility is bought one partner at
/// a time as `pair.check`, not as a system. That is why five doors here and not
/// eight.
enum LadderKey: String, CaseIterable, Sendable, Hashable, Identifiable {

    case natal = "door.natal"
    case numerology = "door.numerology"
    case birthCard = "door.birth-card"
    case astrocartography = "door.astrocartography"
    case synthesis = "door.synthesis"

    /// One compatibility report, about one person. Consumable in App Store
    /// Connect: it is bought again for every partner, and a non-consumable
    /// could only ever be bought once.
    case pairCheck = "pair.check"

    /// All five readings that never change, bought outright.
    case bundleStatic = "bundle.static"

    /// Everything, for as long as it is paid for.
    case subMonthly = "sub.monthly"

    var id: String { rawValue }

    /// The system this rung opens, or `nil` when it opens more than one.
    ///
    /// A stored map rather than `SystemSlug(rawValue:)` over the raw value,
    /// which is what it used to be: the key carries a `door.` prefix now, so
    /// the old expression answered nil for every rung on the shelf.
    var system: SystemSlug? {
        switch self {
        case .natal: .natal
        case .numerology: .numerology
        case .birthCard: .birthCard
        case .astrocartography: .astrocartography
        case .synthesis: .synthesis
        // Deliberately nil, and not `.compatibility`. A pair check does not
        // open the compatibility *system* — it opens one report about one
        // person — and answering with the system here is how a screen ends up
        // drawing "compatibility unlocked" after one purchase.
        case .pairCheck: nil
        case .bundleStatic, .subMonthly: nil
        }
    }

    /// Whether Apple will bill this again. It decides which disclosure sits
    /// above the button — a recurring charge somebody was not told about is the
    /// shape a chargeback takes, and Apple's own review guidelines ask for the
    /// statement to be adjacent to the payment action rather than in the terms.
    var isSubscription: Bool {
        switch self {
        case .subMonthly: true
        default: false
        }
    }

    var title: LocalizedStringResource {
        switch self {
        case .bundleStatic: PaywallL10n.archiveTitle
        case .pairCheck: PaywallL10n.systemName(.compatibility)
        case .subMonthly: PaywallL10n.monthlyTitle
        default: PaywallL10n.systemName(system ?? .natal)
        }
    }

    var note: LocalizedStringResource {
        switch self {
        case .bundleStatic: PaywallL10n.archiveNote
        case .subMonthly: PaywallL10n.monthlyNote
        default: PaywallL10n.doorNote
        }
    }

    // MARK: — the store product id

    /// The id to create in App Store Connect, and the id to ask StoreKit for.
    ///
    /// It is **computed rather than tabulated**, and that is the same decision
    /// the backend made in `StoreProvider.store_product_id`: a store product id
    /// is *chosen* by us rather than issued by Apple, so a second table mapping
    /// slug to id is a second thing to keep in agreement with the console, and
    /// the day the two disagree the symptom is a row that silently vanishes from
    /// the paywall in one country. One rule, stated twice — here and in Python —
    /// and a test on each side is cheaper than a table.
    ///
    /// The rule: the catalogue key, prefixed with `ai.pazl.alma.`, with hyphens
    /// replaced by underscores, because neither App Store Connect nor the Play
    /// Console accepts a hyphen in a product identifier. Периоды они принимают
    /// оба, поэтому `door.birth-card` становится `ai.pazl.alma.door.birth_card`
    /// и разбирается обратно однозначно.
    var storeProductID: String { Self.prefix + rawValue.replacingOccurrences(of: "-", with: "_") }

    /// The inverse, for a transaction arriving from the store rather than from a
    /// button we drew.
    ///
    /// Unambiguous because no catalogue key contains an underscore — checked by
    /// `allSatisfy` below, which runs at first use and traps rather than letting
    /// `alma.solar_return` come back as something that is not a slug.
    static func key(forStoreProductID id: String) -> LadderKey? {
        guard id.hasPrefix(prefix) else { return nil }
        assert(noKeyContainsAnUnderscore)
        let slug = String(id.dropFirst(prefix.count)).replacingOccurrences(of: "_", with: "-")
        return LadderKey(rawValue: slug)
    }

    /// Matches `ALMA_STORE_PRODUCT_PREFIX` on the backend, whose default it is.
    /// Changing it is changing every product id in the console, so it is a
    /// constant rather than a build setting: a build setting invites somebody to
    /// change it for one configuration.
    static let prefix = "ai.pazl.alma."

    /// What to ask `Product.products(for:)` for. Every rung, including the ones
    /// this account cannot be shown — the request is one round trip and the
    /// answer is cached by StoreKit, so fetching the full set once is cheaper
    /// than discovering halfway through the screen that the upgrade has no price.
    static let allStoreProductIDs: [String] = allCases.map(\.storeProductID)

    private static let noKeyContainsAnUnderscore = allCases.allSatisfy {
        !$0.rawValue.contains("_")
    }
}
