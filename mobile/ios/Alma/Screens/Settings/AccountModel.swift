import Foundation
import Observation

/// Everything the settings screen can *do*, apart from the view that draws it.
///
/// Three of the four actions here are promised by a legal page — the
/// subscription terms say cancelling takes two taps, the privacy page promises
/// an export, and the deletion page promises erasure — so each of them is a
/// real call with a real outcome rather than a row that opens a mail client.
///
/// **Phases, not booleans.** Each action is one enum with the states it can
/// actually be in. The alternative — `isCancelling`, `cancelError`,
/// `cancelDone` — has eight combinations, six of which are nonsense, and every
/// one of those six is a spinner that never stops or a button that does nothing.
@MainActor
@Observable
final class AccountModel {

    // MARK: — the plan

    /// What this account holds, and what the ladder calls it.
    ///
    /// The entitlements are the fact and the catalogue is only the naming, so a
    /// catalogue that fails degrades to a plan with no name beside it rather
    /// than taking the whole block down. **No price is read out of it**: Apple
    /// is the merchant of record and its own localised string is the only price
    /// this app may show, which is why nothing here renders `CatalogueItem`'s.
    struct Plan: Sendable, Equatable {
        let held: Entitlements
        let catalogue: Catalogue?

        /// A plan is a grant that was not bought outright. Asked of `kind`
        /// rather than of `system`, because both recurring products are stored
        /// against `system: "*"` — matching on that told a monthly subscriber
        /// they held the annual plan.
        var subscription: EntitlementRow? {
            held.entitlements.first { $0.active && $0.kind != "one_time" }
        }

        /// The doors and the archive: bought once, still held.
        var owned: [EntitlementRow] {
            held.entitlements.filter { $0.active && $0.system != "*" }
        }

        /// A plan that has run out. Worth saying out loud — showing only "Free"
        /// to somebody who paid last year reads as the record being lost rather
        /// than the year being over.
        var lapsed: EntitlementRow? {
            subscription == nil
                ? held.entitlements.first { !$0.active && $0.kind != "one_time" }
                : nil
        }

        /// The catalogue's name for a recurring product, when there is one.
        /// English — the catalogue is not translated — so the screen prefers
        /// its own words for the two rungs it knows and falls back to this for
        /// a rung added after this build shipped.
        func name(ofKind kind: String) -> String? {
            catalogue?.items.first { $0.kind == kind }?.name
        }
    }

    private(set) var plan: ScreenState<Plan> = .loading

    // MARK: — cancelling

    enum CancelPhase: Equatable {
        case idle
        /// The first tap. The second one is the danger button.
        case confirming
        case working
        case done(Outcome)

        enum Outcome: Equatable {
            /// Stopped. The period already paid for runs to its end.
            case cancelled(until: String?)
            /// The store owns this subscription and the server wrote nothing.
            case atStore
            case failed
        }
    }

    private(set) var cancel: CancelPhase = .idle

    // MARK: — exporting

    enum ExportPhase: Equatable {
        case idle
        case working
        /// The file exists on disk and can be handed to a share sheet.
        case ready(URL)
        case failed
        /// A guest has nothing we can attach an export to.
        case needsAccount
    }

    private(set) var export: ExportPhase = .idle

    // MARK: — deleting

    enum DeletePhase: Equatable {
        case idle
        case confirming
        case working
        /// What was typed is not the address on the account.
        case mismatch
        case failed
        case needsAccount
        case deleted
    }

    private(set) var delete: DeletePhase = .idle
    /// What has been typed into the confirmation field. Held here rather than
    /// in the view so that the button's enabled-ness and the comparison the
    /// backend will make live in the same place.
    var typedConfirmation: String = ""

    // MARK: — collaborators

    private let client: AlmaClient

    init(client: AlmaClient) {
        self.client = client
    }

    // MARK: — loading

    /// What this account holds — asked only of an account that exists.
    ///
    /// **The guard is the point.** `GET /v1/billing/entitlements` takes
    /// `CurrentUser`, which mints an account for a tokenless caller. That is
    /// correct for a route somebody reaches by doing something, and this one is
    /// reached by launching: `RootView.cabinet` builds all four tab stacks at
    /// once so a tab switch keeps its scroll position, so Settings' `.task`
    /// fires on every cold launch whether or not the tab is ever opened.
    /// Measured on an erased device against an empty database, a launch that
    /// touched nothing took `user` from 0 rows to 2 — this call and the chat
    /// screen's, racing, each minting, only one token survivable.
    ///
    /// The catalogue is still fetched, because `GET /v1/billing/catalogue`
    /// takes `Visitor` and answers an anonymous caller with the same rows it
    /// would answer a fresh account with. So a guest still sees the ladder
    /// named correctly; what they do not do is acquire an account for looking
    /// at it.
    ///
    /// `Entitlements.none` rather than leaving the block `.loading`: an
    /// account-less device holds nothing, `none` is exactly what the server
    /// would have returned after minting, and a screen left in `.loading`
    /// spins forever. The rest of this model already knows what a guest is —
    /// `ExportPhase.needsAccount` and `DeletePhase.needsAccount` are here for
    /// the same person.
    func loadPlan() async {
        let client = self.client
        guard client.hasAccount else {
            let sold = await almaLoad { try await client.catalogue() }.value
            plan = .loaded(Plan(held: .none, catalogue: sold.value))
            return
        }
        // Both, concurrently: the entitlements decide what is shown and the
        // catalogue only names it, and asking for them in sequence is two round
        // trips for one block.
        let held = almaLoad { try await client.entitlements() }
        let sold = almaLoad { try await client.catalogue() }

        let entitlements = await held.value
        let catalogue = await sold.value

        switch entitlements {
        case .loading:
            plan = .loading
        case .failed(let error):
            plan = .failed(error)
        case .loaded(let value):
            plan = .loaded(Plan(held: value, catalogue: catalogue.value))
        }
    }

    // MARK: — cancelling

    func beginCancel() { cancel = .confirming }
    func abandonCancel() { cancel = .idle }

    /// Stop the next charge and keep everything already paid for.
    ///
    /// The route takes no identifier — the account is the identifier — and it
    /// revokes nothing, so the plan is reloaded afterwards to pick up the
    /// cleared `renews_at` rather than to watch access disappear.
    ///
    /// A store-owned subscription answers 409: neither Apple nor Google lets a
    /// server cancel, and a second cancellation path is how somebody who
    /// cancelled in the App Store gets told by us that their plan renews. That
    /// case is not a failure and is not shown as one — it is the sentence that
    /// points at the App Store, and nothing was written on our side.
    func confirmCancel() async {
        cancel = .working
        do {
            let answer = try await client.cancelSubscription()
            cancel = .done(.cancelled(until: AlmaDate.readable(instant: answer.accessUntil)))
            await loadPlan()
        } catch {
            switch error {
            case .http(let status, _) where status == 409:
                cancel = .done(.atStore)
            default:
                cancel = .done(.failed)
            }
        }
    }

    // MARK: — exporting

    /// Everything we hold about this account, as one file.
    ///
    /// Written to a real file rather than handed to the share sheet as a
    /// string, so that what lands in Files is named `alma-export.json` and
    /// opens as JSON. The temporary directory is right: the file is a copy of
    /// something the server holds, and keeping it in the app container would
    /// mean a second place an account's data lives.
    /// A guest exports too. The backend stopped refusing them on 7 August 2026
    /// and this guard was the mirror of that refusal — written when it was
    /// true, and left behind when it stopped being.
    func exportEverything(isGuest: Bool) async {
        export = .working
        do {
            let document = try await client.exportAccount()
            let data = try JSONEncoder.almaExport.encode(document)
            let url = FileManager.default.temporaryDirectory
                .appendingPathComponent("alma-export.json")
            try data.write(to: url, options: .atomic)
            export = .ready(url)
        } catch let error as AlmaError {
            if case .unauthenticated = error {
                export = .needsAccount
            } else {
                export = .failed
            }
        } catch {
            // Encoding or writing the file. Nothing the person can act on
            // beyond trying again, and the sentence says so.
            export = .failed
        }
    }

    // MARK: — deleting

    /// A guest may delete, and this is the screen where that matters most.
    ///
    /// Alma mints a server-side account on the first request and stores a birth
    /// date, a birth time and a full-precision coordinate against it before
    /// anybody has seen a sign-in screen. So a guest is not an edge case, it is
    /// the state every install begins in and the state holding the most
    /// sensitive data we hold. This used to send them to a sign-in prompt —
    /// demanding an email address as the price of removing the data already
    /// taken, which is the pattern Guideline 5.1.1(v) exists to forbid, and
    /// which App Review meets directly because the reviewer is a guest too.
    func beginDelete(isGuest: Bool) {
        typedConfirmation = ""
        delete = .confirming
    }

    func abandonDelete() {
        typedConfirmation = ""
        delete = .idle
    }

    /// Whether what has been typed matches what this account confirms with.
    ///
    /// An email for somebody signed in, the account id for a guest — which is
    /// what the backend compares against, and which a guest actually has. The
    /// same comparison here keeps the button dim until the typing is right
    /// rather than failing after the tap. Case-insensitive for the address;
    /// an account id is compared exactly, because it is generated rather than
    /// typed from memory and a case-folded match would accept a near miss.
    func typedConfirmationMatches(_ confirmation: String?) -> Bool {
        guard let confirmation, !confirmation.isEmpty else { return false }
        let typed = typedConfirmation.trimmingCharacters(in: .whitespaces)
        if confirmation.contains("@") {
            return typed.lowercased() == confirmation.lowercased()
        }
        return typed == confirmation
    }

    /// Erase the account and everything in it.
    ///
    /// Afterwards the stored token points at a row that no longer exists. The
    /// client clears the keychain — and the installation id with it — when it
    /// sees the 410 that the next request gets, so the caller starts the session
    /// twice: the first start fails and clears, and the second finds no token
    /// and lands the app back on the journey with nothing behind it. One start
    /// would leave the whole app on a failure screen with no retry, because
    /// `accountDeleted` is deliberately not retryable.
    ///
    /// The second start used to mint a fresh guest, and now creates nothing —
    /// which is the right end state for somebody who has just asked to be
    /// erased. Handing them a brand-new account row on the way out was the
    /// old rule ("any request without a token is an account") having the last
    /// word on the one screen where it reads worst.
    func confirmDelete(account: String?, restart: () async -> Void) async {
        guard typedConfirmationMatches(account), let account else {
            delete = .mismatch
            return
        }
        delete = .working
        do {
            _ = try await client.deleteAccount(confirm: account)
            delete = .deleted
            await restart()
            await restart()
        } catch {
            switch error {
            case .unauthenticated:
                delete = .needsAccount
            case .invalid:
                delete = .mismatch
            default:
                delete = .failed
            }
        }
    }
}

private extension JSONEncoder {
    /// Pretty-printed with sorted keys: the file is meant to be *read*, by the
    /// person who asked for it and by whoever they show it to.
    static let almaExport: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        return encoder
    }()
}
