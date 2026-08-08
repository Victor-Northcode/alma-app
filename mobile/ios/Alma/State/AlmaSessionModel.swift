import Foundation
import Observation
import SwiftUI

/// The account, the chart it belongs to, and what it has paid for.
///
/// One of these exists, it is created in `AlmaApp` and put in the environment,
/// and **every screen reads it rather than fetching any of this itself.** Three
/// things live here and nowhere else:
///
/// * **the account** — real from the first request, guest until somebody signs in;
/// * **the profile** — the account owner's own birth data, which every one of
///   the eight systems is computed from;
/// * **the entitlements** — which systems may be read in full.
///
/// They are together because they change together. A purchase changes the
/// entitlements; a sign-in can change the account *and* bring a profile with it;
/// saving a birth date changes the profile and therefore what the hub can
/// compute. Three separate observable objects would mean three screens each
/// refreshing a different two of the three.
///
/// `@MainActor` because every property here is read from a view body. `async`
/// work is done off it by `AlmaClient` and lands back here; nothing in this file
/// blocks.
///
/// A screen reaches it the `@Observable` way, which needs no key and no default:
///
/// ```swift
/// @Environment(AlmaSessionModel.self) private var session
/// ```
///
/// `AlmaApp` injects it at the root, so it is always there. A `#Preview` injects
/// `AlmaSessionModel.preview()`.
@MainActor
@Observable
final class AlmaSessionModel {

    // MARK: — what a screen reads

    /// How the app's own launch went. A screen showing content before this is
    /// `.loaded` is a screen showing an empty account.
    private(set) var bootstrap: ScreenState<Void> = .loading

    /// The account. Guest until an identity is attached — and a guest account
    /// is a real account with real purchases, not a placeholder.
    private(set) var account: AlmaSessionInfo?

    /// The account owner's birth data, or `nil` when they have not given it
    /// yet — which is the state the journey exists to leave.
    private(set) var profile: Profile?

    /// Everybody else this account has saved. Compatibility needs one.
    private(set) var people: [Profile] = []

    /// What has been paid for.
    private(set) var entitlements: Entitlements = .none

    /// Every system and its state. Refreshed after anything that could change
    /// it: a saved birth, a purchase, an added person.
    private(set) var hub: Hub?

    /// The language readings are written in. Follows the device unless the
    /// person chose otherwise, and an explicit choice is never quietly
    /// overridden.
    private(set) var locale: AppLocale = .current

    /// Whether an identity is attached. `false` for a guest, which is most
    /// people for most of the funnel.
    var isSignedIn: Bool { account.map { !$0.isGuest } ?? false }

    /// Whether the eight systems can be computed at all.
    var hasBirthData: Bool { profile != nil }

    /// Whether the five time-dependent systems can be computed.
    var birthTimeKnown: Bool { profile?.birthTimeKnown ?? false }

    // MARK: — collaborators

    let client: AlmaClient

    init(client: AlmaClient = AlmaClient()) {
        self.client = client
    }

    // MARK: — launch

    /// Everything the app needs before it can draw a screen, in one place.
    ///
    /// Called once, from `AlmaApp`. It is safe to call again, and safe to run
    /// after returning from the background.
    ///
    /// **Launching the app is not an act, so it creates nothing.** This used to
    /// call `/v1/auth/session` unconditionally, and that route mints — so every
    /// install became an account before anybody had typed anything, which made
    /// "how many accounts are there" a count of downloads and every per-account
    /// figure in the business a figure about a different population. A device
    /// with no token is a person who has not given us anything yet, and the app
    /// draws the journey for them exactly as it did before; the account appears
    /// at the first act, which on this platform is `saveOwnBirth`, one of the
    /// sign-in calls, or verifying a purchase.
    ///
    /// All four calls are skipped in that case, not just the first. `profiles`,
    /// `entitlements` and `hub` take `CurrentUser` too, so any one of them
    /// would have minted the row the line above declines to mint — and the
    /// answers are empty for a brand-new account anyway, which is precisely
    /// what this state already is.
    ///
    /// The three calls after the session run concurrently. They are independent,
    /// none of them is fast, and running them in sequence is three round trips
    /// of launch time for no reason.
    func start() async {
        bootstrap = .loading

        #if DEBUG
        // `-AlmaSeedBirth`: walk the journey's outcome without the journey.
        // The same affordance as `-AlmaTab` — a state pre-arranged so a test
        // harness can stand on a screen deep in the app — and it goes through
        // the real client and the real API: the guest is minted by the save,
        // exactly as a finished journey would have minted it. DEBUG only, and
        // only when there is nothing yet, so it can never touch a real person.
        if UserDefaults.standard.bool(forKey: "AlmaSeedBirth"), !client.hasAccount {
            _ = try? await client.saveProfile(
                BirthInput(
                    birthDate: "1994-03-12", birthTime: "14:20",
                    latitude: 55.7522, longitude: 37.6156,
                    timezone: "Europe/Moscow", placeLabel: "Москва",
                    placeId: nil, name: "Аня", onAmbiguous: nil
                ),
                isSelf: true
            )
        }
        #endif

        guard client.hasAccount else {
            // Nothing to load and nothing to create. `account` stays `nil`,
            // which every screen already reads as "guest with no birth data" —
            // the state the journey exists to leave — and the funnel still sees
            // this launch, because `X-Alma-Anon` rides on the beacons whether
            // or not there is an account behind them.
            account = nil
            profile = nil
            people = []
            entitlements = .none
            hub = nil
            bootstrap = .loaded(())
            return
        }

        // The session call is in a `do` of its own so the caught error keeps
        // its `AlmaError` type. An `async let` erases a typed throw back to
        // `any Error`, so wrapping all four together would make the catch
        // untyped and cost the exhaustiveness that is the point of the enum.
        let info: AlmaSessionInfo
        do {
            info = try await client.session()
        } catch {
            bootstrap = .failed(error)
            return
        }

        account = info
        adoptLocaleFromDevice(stored: info.locale)

        async let profiles = client.profiles()
        async let held = client.entitlements()
        async let board = client.hub()

        // Each of the three is allowed to fail on its own. A new account has no
        // profiles and no entitlements, and a hub that 500s should not stop the
        // app from launching into a screen that can offer the journey.
        applyProfiles(try? await profiles)
        entitlements = (try? await held) ?? .none
        hub = try? await board

        bootstrap = .loaded(())
    }

    // MARK: — the profile

    /// Save the account owner's birth data. This is what the journey ends with.
    ///
    /// `isSelf` is left unsaid rather than sent as `true`: the backend resolves
    /// "not said" to the first birth an account saves and to nobody after that,
    /// and a client that insists on `true` while adding a partner deletes the
    /// owner's own chart along with every reading keyed to it.
    @discardableResult
    func saveOwnBirth(_ birth: BirthInput) async throws(AlmaError) -> Profile {
        let saved = try await client.saveProfile(birth)
        profile = saved
        await noteTheAccountThisJustCreated()
        await refreshHub()
        return saved
    }

    /// Save somebody else — the second person a compatibility reading needs.
    @discardableResult
    func addPerson(_ birth: BirthInput, relation: String?) async throws(AlmaError) -> Profile {
        let saved = try await client.saveProfile(birth, isSelf: false, relation: relation)
        people.append(saved)
        await noteTheAccountThisJustCreated()
        await refreshHub()
        return saved
    }

    /// Pick up the account an act has just minted, if there was none before.
    ///
    /// Necessary because launching no longer mints one: `start()` leaves
    /// `account` empty for a device that has given us nothing, and the row
    /// appears later, out of whichever request turned out to be the act. Without
    /// this the app works perfectly right up to Settings, where the delete
    /// confirmation asks a guest to type the account id it is holding — and
    /// holding `nil` would put App Review in front of a delete button that
    /// refuses every string it is given.
    ///
    /// `session()` here is a **read**, not a mint: it runs only when the store
    /// already has the token the act came back with, which is the condition that
    /// makes that route identify an account rather than create one. A failure is
    /// ignored on purpose — the birth is saved either way, and a display name
    /// that arrives on the next launch is not worth failing the journey over.
    /// The language everything is written in: the phone's, pushed to the server.
    ///
    /// This used to read the account's stored locale and stop there, which was
    /// right while a picker existed in Settings — the stored value *was*
    /// somebody's choice and had to survive a reinstall. The picker is gone
    /// (see `SettingsScreen.language`), so a stored value is now the fossil of
    /// whatever language the phone was in on the day the account was made.
    /// Somebody who then switches their phone to Spanish would go on being
    /// written to in English forever, with no control anywhere able to fix it.
    ///
    /// So the device wins, and the difference is pushed back on the launch that
    /// notices it. The write is fire-and-forget for the same reason `setLocale`
    /// always was: it is a preference, not a fact, and a launch that fails to
    /// send it sends it next time.
    private func adoptLocaleFromDevice(stored: String) {
        let onDevice = AppLocale.current
        locale = onDevice
        guard AppLocale(serverValue: stored) != onDevice else { return }
        Task { [client] in _ = try? await client.setLocale(onDevice) }
    }

    private func noteTheAccountThisJustCreated() async {
        guard account == nil, client.hasAccount else { return }
        account = try? await client.session()
        if let stored = account?.locale {
            adoptLocaleFromDevice(stored: stored)
        }
    }

    func reloadProfiles() async {
        guard client.hasAccount else { return }
        applyProfiles(try? await client.profiles())
    }

    private func applyProfiles(_ all: [Profile]?) {
        guard let all else { return }
        profile = all.first(where: \.isSelf)
        people = all.filter { !$0.isSelf }
    }

    // MARK: — money

    /// Re-read what this account holds.
    ///
    /// **Call this after every completed purchase**, and only after the store's
    /// transaction has been verified server-side. The client never decides what
    /// somebody owns; it asks.
    func refreshEntitlements() async {
        guard client.hasAccount else { return }
        if let held = try? await client.entitlements() { entitlements = held }
        // A purchase is the other act that can create the account, and on a
        // device that bought before it typed anything this is the first moment
        // there is one to pick up.
        await noteTheAccountThisJustCreated()
        await refreshHub()
    }

    /// Whether a system may be read in full. The single question the paywall
    /// asks, in one place, so that no screen re-implements it from the
    /// entitlement rows.
    func unlocked(_ system: SystemSlug) -> Bool {
        entitlements.unlocks(system)
    }

    // MARK: — the hub

    /// Reload the board.
    ///
    /// The three refreshers above and this one all guard on `hasAccount` for
    /// one reason: `/v1/profiles`, `/v1/billing/entitlements` and `/v1/hub` all
    /// take `CurrentUser` on the server, so any of them would mint the account
    /// that `start()` deliberately declines to mint. Today none of them is
    /// reachable without a birth already saved, which means without an account —
    /// but that is a fact about the navigation graph, and a rule that depends on
    /// a navigation graph is a rule that the next screen breaks. Each of them
    /// answers with what a brand-new account would answer with anyway: nothing.
    func refreshHub() async {
        guard client.hasAccount else { return }
        hub = try? await client.hub()
    }

    /// One system's row, for a screen that wants the status without holding the
    /// whole hub.
    func status(of system: SystemSlug) -> HubEntry? {
        hub?.systems.first { $0.slug == system }
    }

    // MARK: — identity

    /// Attach an Apple identity to *this* account.
    ///
    /// It does not replace the account, and that is the whole design of the
    /// guest-first funnel: somebody who reads three chapters and then signs in
    /// keeps the three chapters. The backend merges onto the token it was
    /// given, so the client must not clear the token first.
    func signInWithApple(identityToken: String, fullName: String?) async throws(AlmaError) {
        let info = try await client.signInWithApple(identityToken: identityToken, fullName: fullName)
        await adopt(info)
    }

    func signInWithGoogle(credential: String) async throws(AlmaError) {
        let info = try await client.signInWithGoogle(credential: credential)
        await adopt(info)
    }

    func consumeMagicLink(token: String) async throws(AlmaError) {
        let info = try await client.consumeMagicLink(token: token)
        await adopt(info)
    }

    private func adopt(_ info: AlmaSessionInfo) async {
        account = info
        adoptLocaleFromDevice(stored: info.locale)
        await reloadProfiles()
        await refreshEntitlements()
    }

    /// Change the language readings are written in.
    ///
    /// Optimistic, and it stays changed even if the write fails: the person
    /// picked a language and the interface must obey immediately. The server
    /// copy is a preference that will be re-sent on the next successful call.
    func setLocale(_ new: AppLocale) async {
        locale = new
        _ = try? await client.setLocale(new)
    }
}

extension AlmaSessionModel {

    /// A model wired to in-memory identity — for `#Preview` and for tests.
    ///
    /// It exists so that a preview is one line rather than four, and so that no
    /// preview ever writes a token, or an installation id, that the app running
    /// on the same simulator would then pick up. Both stores are substituted:
    /// leaving the id on the real `UserDefaults` would make a preview change
    /// which visitor the running app is measured as.
    static func preview() -> AlmaSessionModel {
        AlmaSessionModel(
            client: AlmaClient(
                tokens: EphemeralTokenStore(),
                installation: EphemeralInstallationId()
            )
        )
    }
}
