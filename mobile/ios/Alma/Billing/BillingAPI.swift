import Foundation
import OSLog

/// The two billing calls `AlmaClient` does not have, and the failures they can
/// answer with.
///
/// **Why this is not a method on `AlmaClient`.** It should be, eventually.
/// `/v1/billing/iap/verify` arrived with the store work after the client was
/// written, and the client's request plumbing is `private` — so adding it there
/// means editing a file another agent owns while three of us are building on top
/// of it. This type holds the smallest possible copy of that plumbing (build a
/// URL, attach the bearer token, capture `X-Alma-Token`, decode or classify) and
/// nothing else. When the seams settle, the two methods below move into
/// `AlmaClient` and this file becomes a `typealias`; no call site changes.
///
/// **Why the errors are not `AlmaError`.** A store purchase fails in ways the
/// shared enum has no case for, and the difference between them decides whether
/// the app may call `Transaction.finish()` — which is irreversible. `401
/// invalid_transaction` must never finish; `409 product_mismatch` must, or the
/// same rejected transaction is re-sent on every launch forever; `503` must not,
/// because it means we could not ask the store at all and the money may still be
/// real. Flattening those three into `.http(status:message:)` and letting the
/// screen decide from a number is exactly how a paid-for transaction gets thrown
/// away.
final class AlmaBillingAPI: Sendable {

    private let baseURL: URL
    private let tokens: any TokenStoring
    private let installation: any InstallationIdentifying
    private let session: URLSession
    private let log = Logger(subsystem: "ai.pazl.alma", category: "billing")

    init(
        baseURL: URL = AlmaClient.configuredBaseURL,
        // The *same* store `AlmaClient` uses. A second instance here was a
        // second view of the account that stopped agreeing with the session's
        // the first time the token changed — see `KeychainTokenStore.shared`.
        tokens: any TokenStoring = KeychainTokenStore.shared,
        // And the same installation id, for the same reason one step further
        // on: `iap/verify` is one of the requests allowed to mint an account,
        // so it is one of the requests the server may claim the id on. A second
        // instance here would hand it a different id from the one every other
        // call has been sending, and the claim would join the purchase to a
        // funnel nobody walked.
        installation: any InstallationIdentifying = DefaultsInstallationId.shared,
        session: URLSession = .almaDefault
    ) {
        self.baseURL = baseURL
        self.tokens = tokens
        self.installation = installation
        self.session = session
    }

    // MARK: — the shelf

    /// What is on the shelf for this account, and who is selling it.
    ///
    /// The prices in it are ours, in our currency, and **the paywall does not
    /// render them** — Apple sets the price per storefront and its string is
    /// what the buyer is charged. What this call is for is everything the store
    /// cannot tell us: which keys this account may be offered at all, whether
    /// the archive has been substituted by the upgrade, and the URL where a
    /// subscriber goes to stop paying.
    func shelf(country: String? = nil) async throws(StoreProblem) -> StoreShelf {
        try await get("/v1/billing/catalogue", query: country.map { ["country": $0] } ?? [:])
    }

    // MARK: — the receipt

    /// Hand one signed StoreKit transaction to the server and be told what it
    /// bought.
    ///
    /// Three things about this call that a reader should not have to infer.
    ///
    /// **`transaction` is the JWS verbatim**, not a decoded payload and not a
    /// transaction id: the whole point is that the server checks Apple's
    /// signature over it, against a root certificate pinned in
    /// `alma/billing/appstore.py`. Anything this app decoded first is something
    /// this app could have been made to decode differently.
    ///
    /// **`product` is our catalogue slug, not the store product id** — the
    /// server looks it up in its own price list. It is derived from the *signed*
    /// product id rather than from whichever button was tapped, so a mismatch
    /// between the two is impossible by construction rather than caught by the
    /// server's 409.
    ///
    /// **A replay is a success.** StoreKit re-delivers unfinished transactions
    /// on every launch and a restore replays everything the Apple ID ever
    /// bought; the server answers `already_claimed` with a truthful `unlocked`
    /// and writes nothing. The caller switches on `unlocked`, never on `status`.
    func verify(
        product: LadderKey,
        transaction jws: String
    ) async throws(StoreProblem) -> StoreVerification {
        try await post(
            "/v1/billing/iap/verify",
            body: VerifyRequest(platform: "appstore", product: product.rawValue, transaction: jws)
        )
    }

    // MARK: — the request

    private struct VerifyRequest: Encodable {
        let platform: String
        let product: String
        let transaction: String
    }

    private func get<Response: Decodable>(
        _ path: String, query: [String: String]
    ) async throws(StoreProblem) -> Response {
        try await request(path, method: "GET", query: query, body: Optional<VerifyRequest>.none)
    }

    private func post<Body: Encodable, Response: Decodable>(
        _ path: String, body: Body
    ) async throws(StoreProblem) -> Response {
        try await request(path, method: "POST", query: [:], body: body)
    }

    private func request<Body: Encodable, Response: Decodable>(
        _ path: String,
        method: String,
        query: [String: String],
        body: Body?
    ) async throws(StoreProblem) -> Response {
        guard var components = URLComponents(
            url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false
        ) else { throw .broken }
        if !query.isEmpty {
            components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        guard let url = components.url else { throw .broken }

        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = method
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token = tokens.read() {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        // The same rule as every other call, and it matters most here: a verify
        // from a device that has never had an account mints one, and this is
        // what the server joins that account to the walk that led to it.
        urlRequest.setValue(installation.ensure(), forHTTPHeaderField: AlmaClient.anonHeader)
        if let body {
            guard let encoded = try? Self.encoder.encode(body) else { throw .broken }
            urlRequest.httpBody = encoded
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: urlRequest)
        } catch {
            throw .offline
        }
        guard let http = response as? HTTPURLResponse else { throw .broken }

        // Same rule as every other call: any response may mint a guest token.
        // A verify that dropped it would leave the grant on an account this
        // device can no longer prove it owns.
        if let issued = http.value(forHTTPHeaderField: AlmaClient.tokenHeader), !issued.isEmpty {
            tokens.write(issued)
        }

        guard (200..<300).contains(http.statusCode) else {
            throw classify(status: http.statusCode, data: data)
        }
        guard let decoded = try? Self.decoder.decode(Response.self, from: data) else {
            log.error("could not decode \(path, privacy: .public)")
            throw .broken
        }
        return decoded
    }

    /// Turn a refusal into the one thing the caller has to decide: whether the
    /// transaction may be finished.
    ///
    /// The `error` string outranks the status code, exactly as it does in
    /// `AlmaClient.classify` and for the same reason — 409 is two different
    /// situations here, and one of them is a refund while the other is a product
    /// id that does not match.
    private func classify(status: Int, data: Data) -> StoreProblem {
        let payload = try? Self.decoder.decode(JSONValue.self, from: data)
        let detail = payload?["detail"]
        let object = detail?.objectValue != nil ? detail : payload
        let code = object?["error"]?.stringValue

        switch code {
        case "invalid_transaction": return .notVerified
        case "product_mismatch": return .mismatch
        case "purchase_incomplete": return .withdrawn
        case "billing_unavailable": return .serverLate
        case "unknown_platform", "not_a_store": return .notSold
        default: break
        }

        switch status {
        case 401: return .notVerified
        case 404: return .notSold
        case 410:
            // The account behind this token is gone — deleted from Settings, or
            // merged away. It has its own case because the alternative was
            // `.broken`, whose `mayFinishTransaction` is false: the transaction
            // was never finished and was re-sent on every launch, forever,
            // against an account that will never exist again.
            //
            // `AlmaClient.classify` clears the keychain on a 410, and the store
            // is now shared, so by the time this returns the next launch has a
            // fresh guest to claim against. Finishing is therefore safe: the
            // purchase is still on the Apple ID and a restore re-delivers it.
            return .accountGone
        case 503: return .serverLate
        default:
            log.error("iap/verify answered \(status, privacy: .public)")
            return .broken
        }
    }

    private static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }()

    private static let encoder = JSONEncoder()
}

// MARK: — what comes back

/// The shelf, with the three fields a store client needs and the web one did not.
///
/// `provider`, `merchant` and `manageUrl` are published by the backend rather
/// than typed into the interface, because `src/lib/legal.ts` held the merchant
/// as a build-time constant and the day the processor changed, every legal page
/// still named the old seller — including the refunds page, which is the page a
/// card issuer reads during a dispute.
struct StoreShelf: Decodable, Sendable, Equatable {
    let currency: String
    let items: [StoreShelfItem]
    /// `"appstore"` on an App Store deployment. On a backend still configured
    /// for a card processor this says so, and the app carries on selling through
    /// StoreKit anyway — see `Storefront.manageURL`.
    let provider: String?
    /// `"Apple"`. Named on the legal and refunds pages.
    let merchant: String?
    /// Apple's own subscription screen. Present only on a store.
    let manageUrl: String?
    /// The systems this account may read in full, so the paywall can drop rows
    /// it would be selling to somebody who already owns them without a second
    /// round trip.
    let unlocked: [String]?
}

struct StoreShelfItem: Decodable, Sendable, Equatable, Identifiable {
    let slug: String
    let system: String
    let kind: String
    let scope: String
    /// `"shelf"`, `"in-checkout"`, `"after-door"`. Anything but `"shelf"` must
    /// never be rendered on its own: the conditional prices are cheaper than the
    /// shelf item they stand in for and grant exactly the same thing.
    let offered: String
    /// Set when this row substitutes another — the upgrade shown where the
    /// archive would be.
    let replaces: String?

    var id: String { slug }
    var isOnTheShelf: Bool { offered == "shelf" }
    var key: LadderKey? { LadderKey(rawValue: slug) }
}

/// What `/v1/billing/iap/verify` answers with.
///
/// `status` is `"granted <system>"` on a first claim and `"already_claimed"` on
/// a replay, and **the client must not switch on it**: both are 200, both carry
/// a truthful `unlocked`, and a restore is nothing but replays. `unlocked` is the
/// same list `/v1/billing/entitlements` returns, so a purchase needs no second
/// round trip to know what it opened.
struct StoreVerification: Decodable, Sendable, Equatable {
    let status: String
    let product: String
    let transactionId: String?
    let subscriptionId: String?
    let unlocked: [String]
    /// `nil` for a permanent purchase, a date for a subscription.
    let expiresAt: String?
}

// MARK: — what can go wrong

/// Everything the paywall can fail with, and the two questions the app has to
/// ask of a failure.
///
/// It is a separate enum from `AlmaError` because of `mayFinishTransaction`.
/// That property is the only irreversible decision in this whole feature: a
/// transaction finished too early is a purchase that can never be re-sent, and a
/// transaction never finished is one StoreKit re-delivers on every launch until
/// the app is deleted. No number in a status code carries that; a named case
/// does.
enum StoreProblem: Error, Sendable, Equatable {

    /// StoreKit gave us no products at all, so there is no price to show and
    /// nothing honest to put a button under.
    case storeSilent

    /// 401 `invalid_transaction`. A forged signature, a chain that does not
    /// reach Apple's root, or another app's bundle id. The alert-worthy one.
    case notVerified

    /// 409 `product_mismatch`. The store signed a different product than the
    /// slug claimed — which this client makes impossible by deriving the slug
    /// from the signed product id, so seeing one means the two ends disagree
    /// about the product-id rule.
    case mismatch

    /// 409 `purchase_incomplete`. On Apple: refunded or revoked.
    case withdrawn

    /// 400 or 404. A platform this build does not ship, or a slug the price list
    /// does not sell — an app newer than its server, or the other way round.
    case notSold

    /// 503. Credentials absent, or Apple could not be reached from our side.
    /// Safe and correct to retry; Apple's own notification grants independently,
    /// so the person gets what they paid for either way.
    case serverLate

    /// 410. The Alma account this device was holding has been deleted. The
    /// keychain has already been cleared by the time this arrives, so the next
    /// launch mints a fresh guest — and the purchase is still on the Apple ID,
    /// so a restore re-delivers it to that one.
    case accountGone

    /// No network between the tap and us.
    case offline

    /// Something we have no name for. Deliberately last, and deliberately not a
    /// catch-all that swallows the six above.
    case broken

    /// Whether `Transaction.finish()` may be called.
    ///
    /// **Only on a refusal that will never become an acceptance.** A mismatched
    /// product and a revoked purchase are permanent facts about that
    /// transaction, so keeping it unfinished buys nothing but a request on every
    /// launch for the life of the install. Everything else — an unverifiable
    /// signature, a server that did not answer, a dead network — might succeed
    /// on the next try, and the transaction is the only evidence that the money
    /// moved.
    var mayFinishTransaction: Bool {
        switch self {
        case .mismatch, .withdrawn, .accountGone: true
        case .storeSilent, .notVerified, .notSold, .serverLate, .offline, .broken: false
        }
    }

    /// Whether a retry button can work.
    var isRetryable: Bool {
        switch self {
        case .storeSilent, .serverLate, .offline, .broken: true
        case .notVerified, .mismatch, .withdrawn, .notSold, .accountGone: false
        }
    }

    var displayText: LocalizedStringResource {
        switch self {
        case .storeSilent: PaywallL10n.storeUnavailable
        case .notVerified: PaywallL10n.notVerified
        case .mismatch, .notSold: PaywallL10n.refused
        case .withdrawn: PaywallL10n.withdrawn
        case .serverLate: PaywallL10n.verifyLater
        case .offline: PaywallL10n.offline
        case .accountGone: L10n.stateAccountDeleted
        case .broken: L10n.stateSomethingWrong
        }
    }
}
