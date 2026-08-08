import SwiftUI

/// The ladder, drawn.
///
/// It is a component rather than a screen because the same ladder is sold in two
/// places that are not both screens: `OfferScreen`, pushed from a locked chapter
/// or from settings, and the offer step at the end of the journey, which is
/// inside a `fullScreenCover` and has no navigation stack to push onto. Both get
/// the same rows, the same disclosure and the same restore button, because a
/// paywall that differs between two entry points is two paywalls to keep honest.
///
/// **Every price on this screen comes from StoreKit.** `CatalogueItem.display` is
/// a US-dollar string computed by our own server; showing it to somebody on the
/// Japanese storefront would be a number they are not charged, which is both a
/// lie and a rejection under App Review's pricing rules. Our catalogue decides
/// *which* rows exist and what each one grants; Apple's `displayPrice` decides
/// what they cost.
///
/// **Nothing here grants anything.** The gold button opens Apple's sheet, hands
/// the signed transaction to `AlmaStore`, which hands it to the server, which
/// checks Apple's signature and writes the entitlement. The view then re-reads
/// what the account holds. There is no path through this file that unlocks a
/// chapter from a local decision — and no `import StoreKit` either, which is the
/// mechanical version of the same promise.
@MainActor
struct PaywallView: View {

    /// What is being sold, and therefore which rows appear.
    let intent: PaywallIntent

    /// Called after the server has granted. The offer screen dismisses itself;
    /// the journey moves to the next step.
    var onPurchased: (() -> Void)?

    /// Called when the person says no. Separate from `onPurchased` because the
    /// two are different funnel events and, in the journey, different destinations.
    var onDeclined: (() -> Void)?

    @Environment(AlmaSessionModel.self) private var session

    private var store: AlmaStore { AlmaStore.shared }

    var body: some View {
        VStack(alignment: .leading, spacing: AlmaMetrics.gap) {
            Text(intent.subtitle)
                .almaBody()
                .almaReadingWidth()

            // **What the money buys, before any price and before any error.**
            //
            // The owner tapped a locked chapter on a simulator with no
            // StoreKit attached and landed on a page whose entire content was
            // "The App Store is not answering" — an error screen where a
            // purchase page should be. The pitch renders unconditionally, so
            // the page is about the thing being sold whatever the store is
            // doing, and a storefront failure degrades to one quiet row below
            // instead of *being* the page.
            pitch

            switch store.storefront {
            case .loading:
                AlmaLoading(message: L10n.stateLoadingShort)
                    .frame(minHeight: 220)

            case .unavailable(let problem):
                // **The rungs stay visible when the store does not answer.**
                //
                // The prices used to take the whole ladder down with them, so
                // on a simulator — or on a train — the subscription simply did
                // not exist anywhere in the product: the owner walked the app
                // three times asking where the plans are sold, and the honest
                // answer was "on a screen that only renders when Apple picks
                // up". What we know locally — which rungs exist, what each
                // one contains — is shown; the one thing that may never be
                // invented is the number, and the number is what stays blank.
                ShelfPreview(intent: intent, held: session.entitlements)

                StoreUnavailableView(problem: problem) { await store.load() }
                // Restore survives the store not answering, because it is the
                // one control that helps somebody who already paid — and this
                // is exactly the screen a person on a flaky network reaches
                // when their chapters are locked.
                RestorePurchasesButton()

            case .ready(let storefront):
                LadderView(
                    storefront: storefront,
                    intent: intent,
                    held: session.entitlements,
                    onPurchased: onPurchased,
                    onDeclined: {
                        Task {
                            await session.client.track(.offerDeclined, meta: intent.funnelMeta)
                            onDeclined?()
                        }
                    }
                )
            }

            Text(PaywallL10n.freeNote)
                .almaMeta()
                .padding(.top, 4)
        }
        .task {
            store.attach(session)
            // Anything but a loaded shelf is worth another try — a paywall
            // reopened after a dead network has to work, and the alternative is
            // a screen that stays broken for the rest of the session because it
            // failed once.
            if case .ready = store.storefront {} else { await store.load() }
            await session.client.track(.offerView, meta: intent.funnelMeta)
        }
    }
}

extension PaywallView {

    /// Three facts about the purchase, in the buyer's language, drawn the same
    /// way the honesty block below the button is drawn. Facts, not adjectives:
    /// each line is checkable against the product.
    var pitch: some View {
        VStack(alignment: .leading, spacing: 7) {
            let lines: [LocalizedStringResource] =
                switch intent {
                case .door:
                    [PaywallL10n.pitchDoor1, PaywallL10n.pitchDoor2, PaywallL10n.pitchDoor3]
                case .everything:
                    [PaywallL10n.pitchPlan1, PaywallL10n.pitchPlan2, PaywallL10n.pitchPlan3]
                }
            ForEach(Array(lines.enumerated()), id: \.offset) { _, line in
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text(verbatim: "·").almaPositions()
                    Text(line).almaBody().almaReadingWidth()
                }
            }
        }
        .padding(.top, 2)
    }
}

// MARK: — the ladder

/// The rungs, the button, the disclosure and the way out.
///
/// Split from `PaywallView` because it takes only values — a `Storefront` of
/// price strings and the account's entitlements — and therefore renders in a
/// preview and in a screenshot without an App Store connection. The state it
/// keeps is the two things a person can change here: which rung is chosen, and
/// which legal document they are reading.
@MainActor
struct LadderView: View {

    let storefront: Storefront
    let intent: PaywallIntent
    let held: Entitlements
    var onPurchased: (() -> Void)?
    var onDeclined: (() -> Void)?

    private var store: AlmaStore { AlmaStore.shared }

    /// Which rung is selected. `nil` means "the first one", which is the door
    /// somebody actually reached for and never the most expensive rung — the web
    /// app opened pre-selected on the $78.99 year for anybody who had tapped one
    /// locked chapter, and that is how a paywall teaches people to close paywalls.
    @State private var chosen: LadderKey?

    /// Local rather than routed through `AppRouter.sheet`: this view can be
    /// inside a `fullScreenCover`, and a sheet raised from the root behind a
    /// cover does not appear.
    @State private var reading: LegalDocument?

    var body: some View {
        let offers = storefront.offers(for: intent, held: held)

        if offers.isEmpty {
            // Nothing left to sell. Said plainly, with the one control that is
            // still useful — where to manage a plan — rather than an empty
            // screen or, worse, a row offering what they already own.
            VStack(alignment: .leading, spacing: AlmaMetrics.gap) {
                Text(PaywallL10n.ownedAll)
                    .almaVoice()
                    .almaReadingWidth()
                ManageSubscriptionButton(url: storefront.manageURL)
                // The state that means "you own everything" was the one state
                // where you could not ask for it back — and it is also the
                // state a reviewer's already-purchased sandbox account lands
                // in, which is how "we could not locate a restore purchases
                // feature" gets written.
                RestorePurchasesButton()
            }
            .padding(.vertical, 8)
        } else {
            let selected = offers.first { $0.key == chosen } ?? offers[0]

            VStack(spacing: 0) {
                ForEach(Array(offers.enumerated()), id: \.element.key) { index, offer in
                    LadderRowView(
                        offer: offer,
                        selected: offer.key == selected.key,
                        showsRule: offer.key != offers.last?.key
                    ) {
                        chosen = offer.key
                    }
                    .disabled(store.busy != nil)
                    .riseIn(index)
                }
            }
            .padding(.top, 4)

            buyArea(selected)
                .riseIn(offers.count)
        }
    }

    @ViewBuilder
    private func buyArea(_ selected: LadderOffer) -> some View {
        // The disclosure sits immediately above the button rather than in the
        // terms, and it changes with the selection. Adjacency is the
        // requirement, not a layout preference: App Review asks for the
        // auto-renewal statement next to the payment action, and a person who
        // opened this by tapping one locked chapter must not discover a yearly
        // charge on a statement.
        Text(selected.key.isSubscription ? PaywallL10n.autoRenewTerms : PaywallL10n.oneTimeFine)
            .almaMeta()
            .almaReadingWidth()
            .padding(.top, 18)

        Button {
            Task { await buy(selected) }
        } label: {
            if store.busy == selected.key {
                Text(L10n.stateLoadingShort)
            } else {
                // One line, shrinking if it has to. The button hierarchy in this
                // design is carried by height — gold 56, outline 54, veil 50 —
                // and "Tout ce qui bouge, chaque mois · $9.99" wraps to two
                // lines and grows the capsule to eighty points, which reads as a
                // different control. Shrinking the type is the smaller loss.
                Text(verbatim: "\(String(localized: selected.key.title)) · \(selected.price)")
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
            }
        }
        .buttonStyle(.almaGold)
        .disabled(store.busy != nil || store.restoring)
        .padding(.top, 12)

        if let notice = store.notice {
            Text(notice.text)
                .font(.almaMetaFont)
                .foregroundStyle(notice.tone.colour)
                .almaReadingWidth()
                .padding(.top, 10)
        }

        honesty
            .padding(.top, 22)

        legalRow
            .padding(.top, 14)

        // Apple rejects an app that sells non-consumables and cannot restore
        // them. It is also the only thing that helps somebody on a new phone,
        // which is the case that actually happens.
        RestorePurchasesButton(showsOutcome: false)
            .padding(.top, 18)

        Button {
            onDeclined?()
        } label: {
            Text(intent.declineLabel)
                .almaMeta()
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.plain)
        .padding(.top, 16)
    }

    private func buy(_ offer: LadderOffer) async {
        switch await store.buy(offer.key) {
        case .unlocked:
            onPurchased?()
        case .pending, .cancelled, .failed:
            // Every one of these has already said what it needs to say — the
            // pending sentence, silence, or the specific failure — and none of
            // them is a reason to leave the screen.
            break
        }
    }

    // MARK: — the small print

    /// The three promises, corrected for a store.
    ///
    /// The web app's third line is "cancel in two taps" from our own settings,
    /// and its second is an email before every renewal. Both are things *we* do
    /// when we are the merchant. Apple is the merchant here: Apple takes the
    /// money, Apple sends the receipt, and Apple owns the cancel control. The
    /// same three promises, told truthfully about a different seller.
    private var honesty: some View {
        VStack(alignment: .leading, spacing: 7) {
            let lines = [PaywallL10n.honestyOnce, PaywallL10n.honestySeller, PaywallL10n.honestyCancel]
            ForEach(Array(lines.enumerated()), id: \.offset) { _, line in
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text(verbatim: "·").almaPositions()
                    Text(line).almaMeta()
                }
            }
        }
    }

    /// Terms, privacy and the subscription terms, in the binary.
    ///
    /// Guideline 3.1.2 asks for functional links to the first two from the
    /// paywall itself, and the documents are screens rather than web links
    /// because App Review opens every one of them and a link out to a site that
    /// is down is a rejection.
    private var legalRow: some View {
        HStack(spacing: 10) {
            legalLink(PaywallL10n.terms, .terms)
            Text(verbatim: "·").almaMeta()
            legalLink(PaywallL10n.privacy, .privacy)
            Text(verbatim: "·").almaMeta()
            legalLink(PaywallL10n.subscriptionTerms, .subscriptionTerms)
        }
        .frame(maxWidth: .infinity)
        .sheet(item: $reading) { document in
            NavigationStack { LegalScreen(document: document) }
                .presentationBackground(Color.almaNight)
        }
    }

    private func legalLink(
        _ label: LocalizedStringResource, _ document: LegalDocument
    ) -> some View {
        Button { reading = document } label: {
            Text(label)
                .font(.almaMetaFont)
                .foregroundStyle(Color.almaGold)
                .underline()
        }
        .buttonStyle(.plain)
    }
}

// MARK: — one rung

/// A row of the ladder: what it is on the left, what Apple charges on the right.
///
/// No box, no card, no `GroupBox`. Content sits on the night and rows are
/// separated by a hairline; selection is a filled gold dot rather than a tinted
/// panel, because a tinted panel is the second accent this design does not have.
@MainActor
struct LadderRowView: View {

    let offer: LadderOffer
    let selected: Bool
    let showsRule: Bool
    let choose: () -> Void

    var body: some View {
        Button(action: choose) {
            VStack(spacing: 0) {
                HStack(alignment: .top, spacing: 14) {
                    dot
                        .padding(.top, 6)

                    VStack(alignment: .leading, spacing: 4) {
                        Text(offer.key.title)
                            .almaHeadingM()
                        Text(offer.key.note)
                            .almaMeta()
                            .fixedSize(horizontal: false, vertical: true)
                        if let subnote = offer.subnote {
                            // The annual's arithmetic. Smaller than the billed
                            // price on the right — Apple requires the billed
                            // amount to stay the most prominent price here.
                            Text(verbatim: subnote)
                                .font(.almaMetaFont)
                                .foregroundStyle(Color.almaGoldBright.opacity(0.9))
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    Text(offer.price)
                        .almaPositions()
                        .opacity(selected ? 1 : 0.7)
                        .layoutPriority(1)
                }
                .padding(.vertical, 15)

                if showsRule { Hairline() }
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(selected ? [.isButton, .isSelected] : .isButton)
        .animation(AlmaMotion.ui, value: selected)
    }

    private var dot: some View {
        Circle()
            .fill(selected ? Color.almaGold : Color.clear)
            .frame(width: 8, height: 8)
            .overlay(Circle().stroke(Color.almaGold.opacity(selected ? 0 : 0.45), lineWidth: 1))
    }
}

// MARK: — the shelf, price-less

/// The ladder's rows without the ladder's prices — what renders while the App
/// Store is not answering. Same rungs, same order, same words as the real
/// thing; the price column is empty rather than guessed, and nothing here can
/// be tapped into a purchase.
@MainActor
private struct ShelfPreview: View {

    let intent: PaywallIntent
    let held: Entitlements

    private var keys: [LadderKey] {
        let ownsArchive = held.entitlements.contains {
            $0.active && $0.scope == "all" && $0.kind == "one_time"
        }
        let hasPlan = held.entitlements.contains {
            $0.active && ($0.kind == "monthly" || $0.kind == "annual")
        }
        var keys: [LadderKey] = []
        if case .everything = intent, !hasPlan {
            keys.append(contentsOf: [.annual, .monthly])
        }
        if case .door(let system) = intent, !held.unlocked.contains(system.rawValue) {
            keys.append(contentsOf: LadderKey.allCases.filter { $0.system == system })
        }
        if !ownsArchive { keys.append(.archive) }
        if case .door = intent, !hasPlan {
            keys.append(contentsOf: [.annual, .monthly])
        }
        return keys
    }

    var body: some View {
        VStack(spacing: 0) {
            ForEach(Array(keys.enumerated()), id: \.element) { index, key in
                LadderRowView(
                    offer: LadderOffer(key: key, price: ""),
                    selected: false,
                    showsRule: index != keys.count - 1
                ) {}
                .disabled(true)
            }
        }
        .opacity(0.85)
        .padding(.top, 4)
    }
}

// MARK: — the store is not answering

/// What the paywall shows when there is no price to show.
///
/// Its own view rather than `AlmaFailure`, because `AlmaError` cannot say this:
/// its nearest case is "something on our side is not working", and this failure
/// is on Apple's side. Nothing here is guessed and nothing is sold — which is the
/// same rule the rest of the app follows when a calculation is missing.
@MainActor
struct StoreUnavailableView: View {

    let problem: StoreProblem
    let retry: () async -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text(problem.displayText)
                .almaBody()
                .almaReadingWidth()

            if problem.isRetryable {
                Button {
                    Task { await retry() }
                } label: {
                    Text(L10n.stateRetry)
                }
                .buttonStyle(.alma(.outline, fills: false))
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 24)
    }
}

// MARK: — starting the listener at launch

extension View {

    /// Start listening for App Store transactions for the life of the app.
    ///
    /// **Applied by `RootView`**, one line under `.tint`, which is where the
    /// life of the app actually is. It was written for that and left unapplied,
    /// and the cost was that nothing Apple delivered asynchronously reached us
    /// until somebody opened the paywall — see the comment at the call site.
    ///
    /// It stays idempotent, so the paywall and the restore button go on calling
    /// `AlmaStore.attach` in their own `.task`: the sweep is worth running again
    /// when a purchase surface opens, and a second call claims no second
    /// listener.
    func almaStoreListener(_ session: AlmaSessionModel) -> some View {
        task { AlmaStore.shared.attach(session) }
    }
}

// MARK: — small helpers

extension PaywallIntent {

    var subtitle: LocalizedStringResource {
        switch self {
        case .door: PaywallL10n.doorSub
        case .everything: PaywallL10n.everythingSub
        }
    }

    /// "Not now — take me in" leads somewhere (the cabinet, at the end of the
    /// journey); "Not now" leads back. Two different sentences because they are
    /// two different promises about what the button does.
    var declineLabel: LocalizedStringResource {
        switch self {
        case .door: PaywallL10n.skip
        case .everything: PaywallL10n.notNow
        }
    }

    var funnelMeta: [String: JSONValue] {
        switch self {
        case .door(let system): ["product": .string(system.rawValue)]
        case .everything: [:]
        }
    }
}

extension StoreNotice.Tone {
    /// The only two non-gold accents in the product are reserved for agreement
    /// and disagreement between systems. A purchase that worked and one that did
    /// not are the one other place where "it went well" and "it did not" have to
    /// be readable at a glance, and reusing them here is cheaper than inventing
    /// a fourth and fifth colour.
    var colour: Color {
        switch self {
        case .good: .almaAgree
        case .waiting: .almaGold
        case .bad: .almaDisagree
        }
    }
}

// MARK: — previews

// Behind `#if DEBUG` on purpose. The fixture below contains typed-in prices, and
// "no invented numbers in the product" is a rule this codebase has already had
// to enforce once by deleting them. A fixture that cannot be linked into a
// release build cannot be reached from one by accident.
#if DEBUG

/// A shelf with every rung on it, priced as the US storefront prices them.
///
/// These numbers are **only** ever seen in a preview. The running app takes
/// every price from `Product.displayPrice`, and this exists so that the row
/// heights, the German line wrapping and the disclosure switching can be looked
/// at without an App Store connection — which is exactly the thing a simulator
/// driven from a command line does not have.
extension Storefront {
    static func preview(offering keys: [LadderKey] = LadderKey.allCases) -> Storefront {
        let usd: [LadderKey: String] = [
            .archive: "$38.99", .archiveUpgrade: "$33.00",
            .monthly: "$9.99", .annual: "$78.99",
        ]
        return Storefront(
            shelf: StoreShelf(
                currency: "USD",
                items: keys.map {
                    StoreShelfItem(
                        slug: $0.rawValue, system: $0.system?.rawValue ?? "*",
                        kind: $0.isSubscription ? "monthly" : "one_time",
                        scope: $0.system == nil ? "all" : "system",
                        offered: "shelf", replaces: nil
                    )
                },
                provider: "appstore", merchant: "Apple",
                manageUrl: nil, unlocked: []
            ),
            prices: Dictionary(uniqueKeysWithValues: keys.map { ($0, usd[$0] ?? "$5.99") })
        )
    }
}

#Preview("Ladder · one door") {
    ScrollView {
        LadderView(storefront: .preview(), intent: .door(.natal), held: .none)
            .almaPadding()
    }
    .nightSky()
    .environment(AlmaSessionModel.preview())
}

#Preview("Ladder · the whole shelf") {
    ScrollView {
        LadderView(storefront: .preview(), intent: .everything, held: .none)
            .almaPadding()
    }
    .nightSky()
    .environment(AlmaSessionModel.preview())
}

#endif
