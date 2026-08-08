import Foundation

/// Which installation of the app this is, before there is an account to be.
///
/// **Why it exists.** The account used to be minted by the first request the
/// app made, which on both platforms was `GET /v1/auth/session` from
/// `start()` — so opening the app *was* creating an account, on 100% of
/// installs, before anybody had typed anything. The account is now created by an
/// act: saving a birth, signing in, verifying a purchase. That leaves the
/// question the funnel cannot do without — *of the people who opened the app,
/// how many finished the journey* — with nothing to answer it, and this is the
/// answer. It is sent as `X-Alma-Anon` on every request, and the request that
/// finally mints an account is the one the server records the join on.
///
/// **Not the keychain.** `TokenStore.swift` argues at length for why a bearer
/// credential lives there, and every word of it is about the token being the
/// account: whoever holds it *is* the person, including everything they have
/// paid for. This is the opposite kind of string. It authorises nothing, it buys
/// nothing, and losing it costs a line in a report — so it lives in
/// `UserDefaults`, which is also what stops it acquiring a credential's
/// behaviours by proximity. Keeping it in the keychain would additionally make
/// it survive an app deletion and reinstall on some configurations, which is a
/// stronger identifier than anything on the privacy page describes.
///
/// **It expires.** The privacy page promises that the step labels *and the id*
/// are deleted after `retentionDays`, and an identifier with no end that is
/// eventually joined to a person is the one thing that page exists to promise we
/// do not keep. The server purges the rows; this is the other half, and without
/// it the same install would be re-identified under the same string in year
/// three and a purged id could be claimed afresh by a different account.
///
/// **There is no opt-out to sit behind on this platform**, which is the one
/// place this differs from `src/lib/track.ts` and from Android. The web mints
/// the id inside `track()`, after Do Not Track and GPC have been checked;
/// Android mints it only while the Measurement toggle is on. iOS has neither
/// signal — there is no OS-level do-not-track, and this app has no toggle of its
/// own yet — so the id is created by the first request. The day a toggle lands,
/// `ensure()` moves behind it and this becomes a `read()`.
protocol InstallationIdentifying: Sendable {
    /// The stored id, or nothing. Creates nothing.
    func read() -> String?
    /// The stored id, or a fresh one, re-minted when the old one is spent.
    func ensure() -> String
    /// Forget it. Called wherever the token is cleared, never on its own.
    func clear()
}

/// The real one, in `UserDefaults`.
///
/// `@unchecked Sendable` and not an actor, for the same reason
/// `KeychainTokenStore` is not one: this is read from inside the request
/// builder on a network thread, and an actor would make every call site
/// `async`. `UserDefaults` is documented as thread-safe; the lock guards only
/// the compare-and-mint, so two requests racing at first launch cannot write two
/// ids and send one visitor twice to the top of the funnel.
final class DefaultsInstallationId: InstallationIdentifying, @unchecked Sendable {

    /// **The one installation id the app uses.** Same reasoning as
    /// `KeychainTokenStore.shared`: two instances would race to mint at first
    /// launch, and two ids from one install is two rows at the top of the
    /// funnel for one person.
    static let shared = DefaultsInstallationId()

    /// The same key the web uses in local storage. One name for one idea across
    /// the three clients, so that a person reading the privacy page — which
    /// names it — finds the same word wherever they look.
    private static let key = "alma.anon"
    /// When the current id was minted, as seconds since 1970.
    private static let mintedKey = "alma.anon.minted"

    /// How long one id lives, in days.
    ///
    /// The same number as `PURGE_AFTER_DAYS` in `backend/alma/funnel.py` and
    /// `FUNNEL_RETENTION_DAYS` in `src/lib/legal.ts`, which is the number the
    /// privacy page prints. It is a fourth copy of one fact, so
    /// `src/lib/legal-truth.test.ts` reads this line and fails if it ever
    /// disagrees with the other three.
    static let retentionDays = 180

    private let defaults: UserDefaults
    private let lock = NSLock()

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    func read() -> String? {
        let stored = defaults.string(forKey: Self.key)
        return (stored?.isEmpty ?? true) ? nil : stored
    }

    func ensure() -> String {
        lock.lock()
        defer { lock.unlock() }

        let now = Date().timeIntervalSince1970
        if let existing = read(), !spent(at: now) { return existing }

        // `uuidString` matches the backend's `ANON_ID` pattern, which is
        // deliberately a little wider than a UUID but is written against one.
        let minted = UUID().uuidString
        defaults.set(minted, forKey: Self.key)
        defaults.set(now, forKey: Self.mintedKey)
        return minted
    }

    func clear() {
        lock.lock()
        defer { lock.unlock() }
        defaults.removeObject(forKey: Self.key)
        defaults.removeObject(forKey: Self.mintedKey)
    }

    /// Whether the stored id has outlived the retention the product promises.
    ///
    /// A missing timestamp counts as spent. That is the direction that fails
    /// safe: an id whose age cannot be established is one whose age might be
    /// anything, and re-minting costs one install's joined visit while keeping
    /// it costs the sentence on the privacy page.
    private func spent(at now: TimeInterval) -> Bool {
        let minted = defaults.double(forKey: Self.mintedKey)
        guard minted > 0 else { return true }
        return now - minted >= Double(Self.retentionDays) * 24 * 60 * 60
    }
}

/// An in-memory one, for previews and tests.
///
/// It exists for the reason `EphemeralTokenStore` does: a test that wrote to
/// `UserDefaults.standard` would change the funnel identity of whoever is
/// running the app on the same simulator, and that failure shows up hours later
/// somewhere unrelated.
final class EphemeralInstallationId: InstallationIdentifying, @unchecked Sendable {
    private let lock = NSLock()
    private var id: String?

    init(id: String? = nil) { self.id = id }

    func read() -> String? {
        lock.lock(); defer { lock.unlock() }
        return id
    }

    func ensure() -> String {
        lock.lock(); defer { lock.unlock() }
        if let id { return id }
        let minted = UUID().uuidString
        id = minted
        return minted
    }

    func clear() {
        lock.lock(); defer { lock.unlock() }
        id = nil
    }
}
