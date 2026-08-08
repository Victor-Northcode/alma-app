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
/// **`archive-bump` is deliberately absent.** It exists only as an upsell inside
/// another checkout, and there is no such thing when the store owns the sheet:
/// Apple shows one product per confirmation. The backend still prices it and
/// still refuses to offer it on the shelf, so nothing here has to enforce that
/// twice — but a build that started fetching `alma.archive_bump` from StoreKit
/// would be asking for a product that should never be created in App Store
/// Connect.
enum LadderKey: String, CaseIterable, Sendable, Hashable, Identifiable {

    case natal
    case numerology
    case birthCard = "birth-card"
    case transits
    case solarReturn = "solar-return"
    case compatibility
    case astrocartography
    case synthesis

    /// All forty-one chapters, bought outright.
    case archive
    /// The archive at the shelf price less a door already paid for. The server
    /// substitutes it for `archive` and says so with `replaces`; the client
    /// never computes the discount.
    case archiveUpgrade = "archive-upgrade"

    case weekly
    case monthly
    case annual

    var id: String { rawValue }

    /// The system this rung opens, or `nil` when it opens more than one.
    var system: SystemSlug? { SystemSlug(rawValue: rawValue) }

    /// Whether Apple will bill this again. It decides which disclosure sits
    /// above the button — a recurring charge somebody was not told about is the
    /// shape a chargeback takes, and Apple's own review guidelines ask for the
    /// statement to be adjacent to the payment action rather than in the terms.
    var isSubscription: Bool {
        switch self {
        case .weekly, .monthly, .annual: true
        default: false
        }
    }

    var title: LocalizedStringResource {
        switch self {
        case .archive: PaywallL10n.archiveTitle
        case .archiveUpgrade: PaywallL10n.upgradeTitle
        case .weekly: PaywallL10n.weeklyTitle
        case .monthly: PaywallL10n.monthlyTitle
        case .annual: PaywallL10n.annualTitle
        default: PaywallL10n.systemName(system ?? .natal)
        }
    }

    var note: LocalizedStringResource {
        switch self {
        case .archive: PaywallL10n.archiveNote
        case .archiveUpgrade: PaywallL10n.upgradeNote
        case .weekly: PaywallL10n.weeklyNote
        case .monthly: PaywallL10n.monthlyNote
        case .annual: PaywallL10n.annualNote
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
    /// The rule: the catalogue key, prefixed with `alma.`, with hyphens replaced
    /// by underscores, because neither App Store Connect nor the Play Console
    /// accepts a hyphen in a product identifier.
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
    static let prefix = "alma."

    /// What to ask `Product.products(for:)` for. Every rung, including the ones
    /// this account cannot be shown — the request is one round trip and the
    /// answer is cached by StoreKit, so fetching the full set once is cheaper
    /// than discovering halfway through the screen that the upgrade has no price.
    static let allStoreProductIDs: [String] = allCases.map(\.storeProductID)

    private static let noKeyContainsAnUnderscore = allCases.allSatisfy {
        !$0.rawValue.contains("_")
    }
}
