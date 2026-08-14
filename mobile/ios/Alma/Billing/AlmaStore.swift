import Foundation
import Observation
import StoreKit
import OSLog

/// The App Store, as one object.
///
/// Everything StoreKit touches in this app happens here: loading products,
/// opening the sheet, handing the signed transaction to the server, restoring,
/// and listening for the purchases that complete when nobody is looking. No view
/// imports `StoreKit`, and no view ever decides that somebody owns something.
///
/// **The one rule this file exists to enforce.** A `Transaction` in hand is not
/// an entitlement. It goes to `/v1/billing/iap/verify`, the server checks Apple's
/// signature against a pinned root certificate, and the *server's* answer is what
/// unlocks a chapter — exactly as the web client never granted anything from a
/// closed checkout overlay. Anything the client can decide, the client can be
/// made to decide, and a jailbroken phone with a StoreKit shim is the cheapest
/// place in the world to decide it.
///
/// **Why a singleton, when everything else in this app is injected.**
/// `Transaction.updates` has to be consumed for the whole life of the process:
/// an Ask to Buy approval, a renewal, a refund and a purchase made on another
/// device all arrive there, at moments unrelated to any screen. A `@State` object
/// on a view is torn down when the view goes; a second listener would claim the
/// same transaction twice. There is exactly one App Store connection per process
/// and this is it. It would be a `@State` on `AlmaApp` if that file were mine to
/// edit — the migration is `AlmaStore.shared` becoming an initialiser and
/// `attach` becoming the `.environment` call, and no other line changes.
///
/// **`attach(_:)` is how it learns about the account**, and it is idempotent so
/// that every screen that touches the store can call it in `.task` without
/// coordinating. The reference is `weak`: `AlmaApp` owns the session for the life
/// of the process, and a strong reference here would be a singleton keeping a
/// deleted account's model alive.
@MainActor
@Observable
final class AlmaStore {

    static let shared = AlmaStore()

    // MARK: — what a screen reads

    /// The shelf and its prices. Three cases, not a `products` array plus an
    /// `isLoading` plus an `error` — a paywall with those three has six states
    /// that make no sense, and four of them are a gold button with no price on it.
    private(set) var storefront: StorefrontState = .loading

    /// Which rung the App Store sheet is open for, or `nil`. It disables the
    /// other rows rather than covering the screen with a spinner: the sheet is
    /// Apple's and it is already modal.
    private(set) var busy: LadderKey?

    /// Whether a restore is running. Separate from `busy` because a restore is
    /// not a purchase and must not make the buy button look like it is working.
    private(set) var restoring = false

    /// The last thing that happened, in a sentence. Cleared when a new attempt
    /// starts, so a stale failure never sits under a fresh purchase.
    private(set) var notice: StoreNotice?

    // MARK: — collaborators

    private let api: AlmaBillingAPI
    private weak var session: AlmaSessionModel?
    private var listener: Task<Void, Never>?

    /// Apple's own product objects, which never leave this file.
    ///
    /// `Storefront` publishes the price *strings* instead. That is not
    /// tidiness: a `Product` cannot be constructed, so any view holding one is a
    /// view that can only be seen with a StoreKit configuration attached to the
    /// Xcode scheme — no preview, no screenshot from a command line, no way to
    /// check the German row heights until somebody happens to run it by hand.
    /// Keeping `Product` here costs one dictionary lookup at purchase time and
    /// makes the whole paywall drawable from values.
    private var products: [LadderKey: Product] = [:]
    private let log = Logger(subsystem: "ai.pazl.alma", category: "store")

    init(api: AlmaBillingAPI = AlmaBillingAPI()) {
        self.api = api
    }

    // MARK: — starting

    /// Point the store at the account, and start listening.
    ///
    /// Called from `.task` on every screen that can sell something. The first
    /// call starts the listener and sweeps whatever StoreKit is still holding;
    /// the rest are no-ops.
    func attach(_ session: AlmaSessionModel) {
        self.session = session
        guard listener == nil else { return }

        // Two separate jobs that look like one.
        //
        // `Transaction.updates` is the live feed: a renewal, a refund, an Ask to
        // Buy approval that lands while somebody is reading a chapter. It never
        // finishes, so it gets a task of its own that runs for the life of the
        // process.
        //
        // `Transaction.unfinished` is the backlog: everything StoreKit handed us
        // before and we never called `finish()` on — which, given that finishing
        // requires a round trip to our own server, is every purchase made while
        // the network was down. Sweeping it at start is what makes a failed
        // verification recoverable rather than a lost sale.
        listener = Task { [weak self] in
            for await update in Transaction.updates {
                guard let self else { return }
                _ = await self.claim(update, andRefresh: true)
            }
        }

        Task { [weak self] in
            guard let self else { return }
            var swept = false
            for await unfinished in Transaction.unfinished {
                if await self.claim(unfinished, andRefresh: false) == nil { swept = true }
            }
            if swept { await self.session?.refreshEntitlements() }
        }
    }

    // MARK: — the shelf

    /// Load the ladder: our catalogue and Apple's prices, together.
    ///
    /// The two calls run concurrently because they are independent and neither
    /// is fast — and because the paywall cannot draw a single row without both
    /// of them. A row needs our slug to know what it grants and Apple's product
    /// to know what it costs, so there is no useful half-loaded state to show.
    func load() async {
        storefront = .loading

        // Only the StoreKit half is an `async let`. Wrapping the catalogue call
        // in one as well would erase its typed `throws(StoreProblem)` back to
        // `any Error` — that is what `async let` does to a typed throw — and the
        // whole reason `StoreProblem` exists is that the catch has to be
        // exhaustive over it.
        async let asked = Self.storeProducts()

        let listing: StoreShelf
        do {
            listing = try await api.shelf()
        } catch {
            _ = try? await asked
            // Our own server, not Apple's. Retryable, and it says so.
            storefront = .unavailable(error)
            return
        }

        let priced: [LadderKey: Product]
        do {
            priced = try await asked
        } catch {
            log.error("StoreKit refused the product request: \(String(describing: error))")
            storefront = .unavailable(.storeSilent)
            return
        }

        // No products means no prices, and a price is the one thing on this
        // screen that may not come from us. An empty StoreKit answer is the
        // normal state of a simulator with no StoreKit configuration attached
        // and of a build whose products have not been created in App Store
        // Connect yet — both of which must look like a store that is not
        // answering rather than like a free app.
        guard !priced.isEmpty else {
            storefront = .unavailable(.storeSilent)
            return
        }

        self.products = priced
        storefront = .ready(
            Storefront(
                shelf: listing,
                prices: priced.mapValues(\.displayPrice),
                annualBreakdown: Self.annualBreakdown(priced)
            )
        )
    }

    /// Ask StoreKit for every rung at once.
    ///
    /// `nonisolated` and `static` so it can run off the main actor while the
    /// catalogue request is in flight — `Product.products(for:)` is a network
    /// call and there is no reason for it to be serialised behind view updates.
    /// The annual plan's per-month equivalent and saving, formatted by Apple's
    /// own currency style so it can never disagree with the price beside it.
    /// Nothing is shown unless the saving is real and positive.
    private nonisolated static func annualBreakdown(_ priced: [LadderKey: Product]) -> String? {
        guard let annual = priced[.annual], let monthly = priced[.monthly] else { return nil }
        let yearAtMonthly = monthly.price * 12
        guard yearAtMonthly > annual.price else { return nil }
        let saving = (yearAtMonthly - annual.price) / yearAtMonthly * 100
        let percent = Int((saving as NSDecimalNumber).doubleValue.rounded())
        let perMonth = annual.priceFormatStyle.format(annual.price / 12)
        return String(localized: PaywallL10n.perMonthSavings(perMonth, percent))
    }

    private nonisolated static func storeProducts() async throws -> [LadderKey: Product] {
        let fetched = try await Product.products(for: LadderKey.allStoreProductIDs)
        return fetched.reduce(into: [:]) { found, product in
            // A product id StoreKit knows and this build does not is skipped
            // rather than crashed on: it is what an App Store Connect entry
            // added ahead of an app release looks like.
            if let key = LadderKey.key(forStoreProductID: product.id) { found[key] = product }
        }
    }

    // MARK: — buying

    /// Open Apple's sheet for one rung and see it through.
    ///
    /// Returns rather than only setting `notice`, because the caller usually has
    /// something to do on success — the offer screen dismisses itself, the
    /// journey moves on — and reading that out of an observable string would be
    /// guessing.
    @discardableResult
    func buy(_ key: LadderKey) async -> PurchaseOutcome {
        // A rung with no product is a row that should not have been drawn —
        // `Storefront.offers` only builds one where StoreKit answered — so this
        // is a broken invariant rather than a state the interface has to
        // explain. It still refuses rather than crashing, because crashing at
        // the moment somebody presses "buy" is the worst possible time.
        guard busy == nil, let product = products[key] else { return .failed(.storeSilent) }
        busy = key
        notice = nil
        defer { busy = nil }

        await session?.client.track(.checkoutOpened, meta: ["product": .string(key.rawValue)])

        let result: Product.PurchaseResult
        do {
            // No `appAccountToken`. It is the obvious thing to attach — a UUID
            // that would follow the purchase into Apple's own records — but our
            // account ids are 22-character base64url and not UUIDs, and the
            // backend deliberately takes the owner from the session token rather
            // than from anything the client sets. Sending a second, weaker claim
            // of identity that nothing reads is noise; making it *mean*
            // something is the account-linking work in `open_problems`.
            result = try await product.purchase()
        } catch {
            log.error("purchase of \(key.rawValue, privacy: .public) threw: \(String(describing: error))")
            // Cancelling reaches this app as a thrown `StoreKitError` on some
            // paths and as `.userCancelled` in the result on others; both mean
            // the same thing and neither is worth a sentence on screen.
            if let storeKit = error as? StoreKitError, case .userCancelled = storeKit {
                return .cancelled
            }
            notice = .bad(StoreProblem.storeSilent.displayText)
            return .failed(.storeSilent)
        }

        switch result {
        case .success(let signed):
            if let problem = await claim(signed, andRefresh: true) { return .failed(problem) }
            await session?.client.track(
                .purchaseCompleted, meta: ["product": .string(key.rawValue)]
            )
            // The one touch money gets: the server has granted, the doors are
            // open, and the hand learns it at the same moment the screen does.
            AlmaHaptics.unlocked()
            return .unlocked(session?.entitlements.unlocked ?? [])

        case .pending:
            // Ask to Buy, or a payment method that needs a step outside the app.
            // Nothing has been charged and there is nothing to finish; the
            // transaction arrives on `Transaction.updates` if and when it is
            // approved, which is why the listener is not optional.
            notice = .waiting(PaywallL10n.pending)
            return .pending

        case .userCancelled:
            // Silence, deliberately. Somebody who closed the sheet has said no,
            // and an app that answers that with a message has started arguing.
            await session?.client.track(
                .offerDeclined, meta: ["product": .string(key.rawValue)]
            )
            return .cancelled

        @unknown default:
            notice = .bad(L10n.stateSomethingWrong)
            return .failed(.broken)
        }
    }

    // MARK: — restoring

    /// What Apple requires every app selling non-consumables to have, and what
    /// somebody on a new phone actually needs.
    ///
    /// `AppStore.sync()` first, because it is the only thing that forces a fresh
    /// authentication against the Apple ID — without it `currentEntitlements`
    /// answers from a local cache that a reinstalled app does not have. It can
    /// throw when the person cancels the password prompt, and that is not a
    /// failure worth reporting: the loop below still runs, against whatever
    /// StoreKit already knows.
    func restore() async {
        guard !restoring else { return }
        restoring = true
        // No "asking…" notice: the button's own label already says that, and two
        // copies of the same sentence on one screen is how a screen starts
        // looking like it is repeating itself.
        notice = nil
        defer { restoring = false }

        do {
            try await AppStore.sync()
        } catch {
            log.info("AppStore.sync() ended early: \(String(describing: error))")
        }

        var found = 0
        var granted = 0
        var lastProblem: StoreProblem?
        for await entitlement in Transaction.currentEntitlements {
            found += 1
            if let problem = await claim(entitlement, andRefresh: false) {
                lastProblem = problem
            } else {
                granted += 1
            }
        }
        await session?.refreshEntitlements()

        // Four outcomes, and the last one is the one that matters.
        //
        // The distinction between "found nothing" and "found something and
        // could not claim it" is the whole value of counting both: a restore
        // that hit a 503 and reported "the App Store has nothing to restore"
        // would send somebody who has paid to support, believing their
        // purchases were gone.
        //
        // Transactions found and *nothing* unlocked means this Apple ID's
        // purchases are held by a different Alma account — the first account to
        // claim a transaction wins it, which is the safe direction and not the
        // kind one. The answer is signing in with the account that holds them,
        // never a second grant, so the sentence says that rather than "nothing
        // found".
        let holds = session?.entitlements.unlocked.isEmpty == false
        if found == 0 {
            notice = .waiting(PaywallL10n.restoredNone)
        } else if granted == 0, let lastProblem {
            notice = .bad(lastProblem.displayText)
        } else if holds {
            notice = .good(PaywallL10n.restored)
        } else {
            notice = .bad(PaywallL10n.restoredOther)
        }
    }

    // MARK: — the claim

    /// Send one signed transaction to the server, and finish it if the server's
    /// answer means it will never be worth sending again.
    ///
    /// Answers `nil` on success and the reason otherwise — so a caller sweeping
    /// a dozen transactions can refresh the entitlements once instead of a dozen
    /// times, and `buy` can return the specific failure rather than a boolean it
    /// would have to re-describe.
    private func claim(
        _ result: VerificationResult<Transaction>, andRefresh: Bool
    ) async -> StoreProblem? {
        // The unverified branch is *not* discarded, and that is the point of the
        // whole design. StoreKit's local check can fail for reasons that have
        // nothing to do with fraud — a device clock weeks out of date is the
        // common one — and the client is not the authority here anyway. The JWS
        // goes to the server either way and the server, which pins Apple's root
        // certificate, decides. Refusing it here would be this app deciding what
        // somebody owns, which is the one thing it must never do.
        let transaction: Transaction
        switch result {
        case .verified(let value): transaction = value
        case .unverified(let value, let why):
            log.warning("StoreKit could not verify \(value.id) locally: \(String(describing: why))")
            transaction = value
        }

        guard let key = LadderKey.key(forStoreProductID: transaction.productID) else {
            // A product this build does not sell. Left unfinished on purpose:
            // finishing it would throw away a real purchase of a product a newer
            // build knows about, and the cost of leaving it is one skipped
            // iteration per launch.
            log.error("no ladder key for store product \(transaction.productID, privacy: .public)")
            return .notSold
        }

        do {
            let verified = try await api.verify(product: key, transaction: result.jwsRepresentation)
            // Finish only now: the transaction is Apple's record that the money
            // moved, and until our server has written the grant it is the only
            // copy of that fact this device holds.
            await transaction.finish()
            if andRefresh { await session?.refreshEntitlements() }
            log.info("claimed \(key.rawValue, privacy: .public): \(verified.status, privacy: .public)")
            return nil
        } catch {
            if error.mayFinishTransaction { await transaction.finish() }
            notice = .bad(error.displayText)
            log.error("claim of \(key.rawValue, privacy: .public) failed: \(String(describing: error))")
            return error
        }
    }
}

// MARK: — the state

/// What the store is doing. The paywall's three cases.
///
/// Not `ScreenState<Storefront>`: that carries an `AlmaError`, and none of
/// `AlmaError`'s cases can say "Apple is not answering" — the nearest is
/// `.unavailable`, whose sentence is "something on our side is not working",
/// which is the wrong side and is the kind of small lie that turns into a support
/// ticket. Three cases, exhaustive, and a failure that knows whether retrying
/// could work.
enum StorefrontState: Sendable {
    case loading
    case ready(Storefront)
    case unavailable(StoreProblem)
}

/// The shelf, priced.
///
/// It carries Apple's price *strings* and not Apple's `Product`s — see the note
/// on `AlmaStore.products`. That is what lets a preview and a command-line
/// screenshot show a populated ladder, which is the only way the row heights of
/// the German copy were ever going to get looked at.
struct Storefront: Sendable, Equatable {

    let shelf: StoreShelf
    /// Apple's own localised price per rung, in the buyer's storefront currency.
    /// Never formatted by us — the whole reason it is fetched is that we do not
    /// know what Apple charges in Japan.
    let prices: [LadderKey: String]

    /// "$6.58 a month · save 34%" — computed from Apple's own decimals at load
    /// time, in the buyer's currency, or nothing when either plan is missing.
    /// A string rather than numbers for the same reason `prices` is: this
    /// struct renders in previews with no StoreKit behind it.
    var annualBreakdown: String? = nil

    /// Where a subscriber goes to stop paying.
    ///
    /// Published by the backend when it is configured for a store, and defaulted
    /// to Apple's own URL when it is not — which is the state of a development
    /// backend still set to a card processor, and of any deployment serving both
    /// apps from one configuration. Hard-coding it as the *fallback* rather than
    /// as the value keeps one place to change it while making the screen work
    /// today: the App Store guideline that requires selling through StoreKit also
    /// requires this link to exist, and an app that only describes where to
    /// cancel fails review.
    var manageURL: URL {
        shelf.manageUrl.flatMap(URL.init(string:)) ?? Self.appleSubscriptionsURL
    }

    /// The rungs to draw, in the order somebody climbs them.
    ///
    /// Four rules, each of which was a bug somewhere before it was a rule:
    ///
    /// * **only what the server calls `shelf`** — `archive-bump` and
    ///   `archive-upgrade` are cheaper than the item they stand in for and grant
    ///   the same thing, so rendering one on its own is selling the archive at a
    ///   discount to everybody;
    /// * **only what StoreKit priced** — a row whose product Apple did not
    ///   return has no price we may show, and the catalogue's own `display` is a
    ///   US-dollar string that would be wrong in most countries and rejected in
    ///   review;
    /// * **never what this account already holds** — an offer to buy what you
    ///   own is the fastest way to look like a scam;
    /// * **the door first** — pre-selected on the rung the person actually
    ///   reached for. The web app opened on the $78.99 year for somebody who had
    ///   tapped one locked chapter, which is how a paywall teaches people to
    ///   close paywalls.
    func offers(for intent: PaywallIntent, held: Entitlements) -> [LadderOffer] {
        // Read off the grant rows rather than off `unlocked`, and the difference
        // matters. `unlocked` is a flat list of system slugs — the backend
        // expands an everything-grant into the eight rather than sending a `*`
        // sentinel — so "owns eight systems" is true both of somebody who bought
        // the archive and of somebody who bought five doors while renting the
        // three living ones. Hiding the archive from the second person is
        // hiding the thing they are about to want.
        let ownsArchive = held.entitlements.contains {
            $0.active && $0.scope == "all" && $0.kind == "one_time"
        }
        // Any live plan removes both plan rows. Selling an annual to a monthly
        // subscriber is a real thing somebody might want, but on a store it is a
        // *change* inside one subscription group rather than a second purchase,
        // and it is done on Apple's own subscription screen — which is one tap
        // away through `manage_url`. A gold button that says "buy" and produces
        // a plan change is the kind of surprise a chargeback is made of.
        // `EntitlementKind` in `alma/db/models.py`: one_time | weekly | monthly | annual.
        let hasPlan = held.entitlements.contains {
            $0.active && ($0.kind == "weekly" || $0.kind == "monthly" || $0.kind == "annual")
        }

        let onTheShelf = Set(shelf.items.filter(\.isOnTheShelf).compactMap(\.key))

        var keys: [LadderKey] = []
        if case .door(let system) = intent, !held.unlocked.contains(system.rawValue) {
            keys.append(contentsOf: LadderKey.allCases.filter { $0.system == system })
        }
        // **Plans first when nobody reached for a door.** The `.everything`
        // intent is now every plans-first surface — settings, the chat limit,
        // the whole-ladder route — and research is unambiguous that the plan
        // sells best led by the annual with the monthly under it (annual takes
        // 60–70% of plan sales when it leads, and annual subscribers retain
        // 19.9% at day 380 against 14.2% monthly). On a door intent the door
        // stays first and pre-selected: selling what somebody reached for is
        // this ladder's own oldest law.
        if !hasPlan, case .everything = intent {
            // The annual leads; the week sits directly under it — the honest
            // version of the impulse the category's weekly plans monetise.
            keys.append(contentsOf: [.annual, .weekly, .monthly])
        }
        if !ownsArchive {
            // Exactly one of the two, and `first(where:)` is what guarantees it.
            // The server substitutes the upgrade for the archive by itself, for
            // somebody who already bought a door, and reading that choice off
            // the response rather than deciding it here is what keeps the price
            // shown and the price charged the same one. But appending both and
            // letting the shelf filter sort it out puts two rows that grant
            // *identical* access at two different prices side by side the moment
            // a catalogue change marks both as `shelf` — which is the same
            // mistake, in the same product, that `on_the_shelf` exists on the
            // server to prevent.
            if let archive = [LadderKey.archive, .archiveUpgrade].first(where: onTheShelf.contains) {
                keys.append(archive)
            }
        }
        if !hasPlan, case .door = intent {
            // The plans stay on the shelf even for somebody who owns the
            // archive: the archive is forty-one written chapters, and the living
            // layer is transits that move. They are not the same purchase.
            // Annual above monthly here too — same argument, subordinate spot.
            keys.append(contentsOf: [.annual, .weekly, .monthly])
        }

        var seen = Set<LadderKey>()
        return keys.compactMap { key -> LadderOffer? in
            guard onTheShelf.contains(key), seen.insert(key).inserted,
                  let price = prices[key]
            else { return nil }
            return LadderOffer(
                key: key,
                price: price,
                // The annual's arithmetic, stated under it in subordinate
                // size: "$6.58 a month · save 34%". Apple permits exactly
                // this — per-month equivalent and savings — provided the
                // billed amount stays the most prominent price on the row.
                subnote: key == .annual ? annualBreakdown : nil
            )
        }
    }
}

/// One rung, with a price that came from Apple.
struct LadderOffer: Identifiable, Sendable, Equatable {
    let key: LadderKey
    let price: String
    /// The smaller line under the price — today only the annual's per-month
    /// arithmetic. Optional with a default so nothing else has to know.
    var subnote: String? = nil

    var id: LadderKey { key }
}

/// What the paywall is for.
///
/// Two intents, because the two moments are different sales. After the portrait
/// somebody has just been shown their own free numbers and is being offered the
/// writing for the one system their quiz answer chose — one door, one decision.
/// In the cabinet they have already read something and are deciding how much of
/// the rest they want, which is a ladder.
enum PaywallIntent: Sendable, Equatable {
    case door(SystemSlug)
    case everything

    /// **The plans are shown everywhere now, and the old reasoning was half
    /// right.**
    ///
    /// It used to be `.everything` only, on the argument that a recurring
    /// charge beside a $5.99 door is how a first purchase becomes a
    /// subscription nobody meant to start. That risk is real — and the defence
    /// against it is *selection*, not *concealment*. The rung a person reached
    /// for stays pre-selected, the plans sit below it as a separate choice, and
    /// each one says what it contains: the monthly is transits, the solar
    /// return and compatibility while they move, plus thirty questions a month.
    ///
    /// What concealment actually bought was a product whose recurring revenue
    /// was invisible. The owner walked the whole app and never once saw the
    /// subscription offered or heard what it includes — and "it is one tap away
    /// in Settings" is exactly the sentence that turned out to be worth
    /// nothing, because nobody opens Settings to be sold something.
    ///
    /// Hiding a price is not consumer protection. Pre-selecting one is.
    var showsPlans: Bool { true }
}

/// How a purchase ended.
enum PurchaseOutcome: Sendable, Equatable {
    /// The server granted, or said it had already granted. Carries what this
    /// account now holds.
    case unlocked([String])
    /// Ask to Buy. Nothing charged, nothing to do, and it may still arrive.
    case pending
    /// The sheet was closed. Say nothing.
    case cancelled
    case failed(StoreProblem)
}

/// A sentence under the button, with the only three tones this product has.
struct StoreNotice: Sendable {
    enum Tone: Sendable { case good, waiting, bad }

    let text: LocalizedStringResource
    let tone: Tone

    static func good(_ text: LocalizedStringResource) -> StoreNotice { .init(text: text, tone: .good) }
    static func waiting(_ text: LocalizedStringResource) -> StoreNotice { .init(text: text, tone: .waiting) }
    static func bad(_ text: LocalizedStringResource) -> StoreNotice { .init(text: text, tone: .bad) }
}
