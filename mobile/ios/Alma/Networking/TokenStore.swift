import Foundation
import Security

/// Where the guest token lives.
///
/// **The keychain, not `UserDefaults`.** The token in `X-Alma-Token` is a bearer
/// credential: whoever holds it *is* the account, including everything that
/// account has paid for. `UserDefaults` is a plist in the app container — it is
/// included in unencrypted iTunes/Finder backups, it is readable by anything
/// that gets file access to a jailbroken device, and it is trivially visible to
/// anyone debugging the app on their own phone. The keychain item below is
/// encrypted at rest by the system and excluded from backups by
/// `ThisDeviceOnly`.
///
/// **`AfterFirstUnlockThisDeviceOnly`, specifically.** Not `WhenUnlocked`,
/// because a background refresh with the phone in a pocket has to be able to
/// read it; not the plain `AfterFirstUnlock`, because that migrates to a new
/// device in an encrypted backup, and a guest token silently following somebody
/// onto a second device is one account being used from two places, which the
/// backend's question allowances are not written for.
protocol TokenStoring: Sendable {
    func read() -> String?
    func write(_ token: String)
    func clear()
}

/// The real one.
///
/// `@unchecked Sendable` and not an `actor`: the Security framework's calls are
/// synchronous and thread-safe, so an actor would buy nothing but would force
/// every call site — including the one inside `URLSession`'s completion path —
/// to become `async`. The unchecked promise is kept by the lock, which guards
/// the only mutable state there is: the in-memory cache.
final class KeychainTokenStore: TokenStoring, @unchecked Sendable {

    /// **The one token store the app uses.**
    ///
    /// A shared instance, and it is not a convenience. `read()` short-circuits
    /// on an in-memory cache that only that instance's own `write()` ever
    /// updates, so two `KeychainTokenStore()`s are two views of the account that
    /// drift apart the moment either one refreshes: `AlmaClient` had one and
    /// `AlmaBillingAPI` had another, and once the paywall had been opened once
    /// the billing instance held whatever token was current at that moment for
    /// the rest of the process.
    ///
    /// The consequences were not cosmetic. Delete the account in Settings — which
    /// clears the store the *client* holds and mints a fresh guest — and the
    /// billing instance goes on sending the dead token, so a verify answers 410
    /// and the transaction is never finished and is re-sent on every launch
    /// forever. Consume a magic link requested on another device and the guest
    /// folded in is not this device's guest, so a purchase verified with the
    /// stale token grants to an account the person can no longer reach — and,
    /// because the server answers 200, the client finishes the transaction and
    /// Apple never re-delivers it. The money is taken, the grant is stranded,
    /// and restore afterwards correctly says the purchase belongs to somebody
    /// else.
    ///
    /// Both initialisers still take a store, so a preview or a test injects an
    /// `EphemeralTokenStore` and never touches the keychain.
    static let shared = KeychainTokenStore()

    /// The keychain service. The bundle id, so that two builds of Alma on one
    /// device (App Store and a local debug build) do not share an account.
    private let service: String
    private let account = "guest-token"

    private let lock = NSLock()
    /// Double optional on purpose: the outer `nil` means "not read yet", the
    /// inner means "read, and there is none". Without the distinction, an
    /// account with no token re-queries the keychain on every single request.
    private var cached: String??

    init(service: String = Bundle.main.bundleIdentifier ?? "ai.pazl.alma") {
        self.service = service
    }

    func read() -> String? {
        lock.lock()
        defer { lock.unlock() }

        if let cached { return cached }

        var query = baseQuery
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess,
              let data = item as? Data,
              let token = String(data: data, encoding: .utf8),
              !token.isEmpty
        else {
            cached = .some(nil)
            return nil
        }

        cached = .some(token)
        return token
    }

    func write(_ token: String) {
        lock.lock()
        defer { lock.unlock() }

        // No-op when it has not changed. Every response carries the header, so
        // without this check a scrolling screen would rewrite the keychain
        // dozens of times a minute for no reason.
        if case .some(.some(let existing)) = cached, existing == token { return }

        let data = Data(token.utf8)
        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]

        let status = SecItemUpdate(baseQuery as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var insert = baseQuery
            insert.merge(attributes) { _, new in new }
            SecItemAdd(insert as CFDictionary, nil)
        }

        cached = .some(token)
    }

    func clear() {
        lock.lock()
        defer { lock.unlock() }
        SecItemDelete(baseQuery as CFDictionary)
        cached = .some(nil)
    }

    private var baseQuery: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }
}

/// An in-memory store, for previews and tests.
///
/// It exists so that a `#Preview` or a unit test never touches the real
/// keychain — a test that writes to it would corrupt the token of whoever is
/// running the app on the same simulator, which is a failure that shows up
/// hours later in an unrelated place.
final class EphemeralTokenStore: TokenStoring, @unchecked Sendable {
    private let lock = NSLock()
    private var token: String?

    init(token: String? = nil) { self.token = token }

    func read() -> String? {
        lock.lock(); defer { lock.unlock() }
        return token
    }

    func write(_ token: String) {
        lock.lock(); defer { lock.unlock() }
        self.token = token
    }

    func clear() {
        lock.lock(); defer { lock.unlock() }
        token = nil
    }
}
