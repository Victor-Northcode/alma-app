import Foundation
import OSLog
import SwiftUI
import UserNotifications

/// The daily's state, and the one place that decides anything about it.
///
/// It sits above both surfaces on purpose. The Today block and the settings
/// section are two views of one fact — *what will arrive, and is that true* —
/// and two models would eventually disagree about it. In particular the thing
/// this type exists to prevent is a settings screen that says "about once a
/// week" while nothing is registered and nothing is sent, which is the exact
/// failure the web app shipped once (four toggles, no sender) and had to remove.
@MainActor
@Observable
final class DailyModel {

    private let client: AlmaClient
    private let push: PushService
    private let store = DailyStore()
    private let log = Logger(subsystem: "ai.pazl.alma", category: "daily")

    init(client: AlmaClient, push: PushService) {
        self.client = client
        self.push = push
        self.chosen = store.preference
        self.hour = store.hour
        self.answeredTheAsk = store.hasAnsweredTheAsk
        observeNotificationActions()
    }

    // MARK: — what the person chose

    /// The stored answer, or `nil` because they have not answered.
    private(set) var chosen: DailyPreference?

    /// Whether the invitation on Today has been dealt with, either way.
    private(set) var answeredTheAsk: Bool

    private(set) var hour: Int

    /// Whether the server has accepted a token for this device, and when.
    private(set) var registeredAt: Date?

    /// Whether this account is renting the living layer.
    ///
    /// Set by the caller from `Entitlements`, because entitlements belong to the
    /// session model and this type must not go and fetch a second copy of them.
    var isSubscriber: Bool = false

    /// The rule from `THE-DAILY.md §5.1`: **Occasionally for a subscriber, Off
    /// for everybody else**, unless the person has said otherwise.
    ///
    /// Note which way round the default falls for a lapsed subscriber: `chosen`
    /// survives, so somebody who picked *Only what matters* and then let the
    /// plan run out keeps that choice for the day they come back. What stops
    /// the sends is `deliverable`, not this.
    var preference: DailyPreference {
        chosen ?? (isSubscriber ? .occasionally : .off)
    }

    /// Whether anything can actually arrive, which is a different question from
    /// what the person chose and must never be conflated with it.
    var deliverable: Bool {
        isSubscriber && preference.wantsDelivery && registeredAt != nil
            && push.authorization != .denied
    }

    var authorization: UNAuthorizationStatus { push.authorization }

    /// Whether the invitation belongs on Today right now.
    ///
    /// Four conditions, and each one is somebody's bad experience:
    /// a chart must exist (there is nothing to promise otherwise), the person
    /// must be a subscriber (the feature is theirs — offering it to a free
    /// reader is a paywall wearing a permission dialog), they must not have
    /// answered already (asked once, not every launch), and the OS must not
    /// have said no (a denied person shown an invitation is being nagged about
    /// something they cannot act on from here).
    func shouldInvite(hasBirthData: Bool) -> Bool {
        hasBirthData && isSubscriber && !answeredTheAsk && push.authorization != .denied
    }

    // MARK: — the moment somebody says yes

    /// The person accepted the invitation on Today.
    ///
    /// On iOS this shows **no system dialog at all**: the enrolment is
    /// provisional, so the notifications arrive quietly in Notification Center
    /// with their own Keep / Turn Off buttons and the person judges the real
    /// thing rather than a promise about it. The dialog, if it ever appears, is
    /// the escalation in `letThemArriveProperly()` and it happens after they
    /// have seen a few.
    func accept() async {
        answeredTheAsk = true
        store.hasAnsweredTheAsk = true
        await choose(.occasionally)
    }

    /// The person declined the invitation. Nothing is asked of the OS.
    ///
    /// Our own question is repeatable and the platform's is not, so declining
    /// here costs nothing: the control is still in Settings and turning it on
    /// next month is the same one tap. The whole point of asking our question
    /// first is that this branch exists.
    func decline() {
        answeredTheAsk = true
        store.hasAnsweredTheAsk = true
        chosen = .off
        store.preference = .off
    }

    /// Move to a position, and make the world agree with it.
    ///
    /// The order matters: the local store first so the interface is never
    /// showing something it has not remembered, then the OS, then the server.
    /// A network failure in the third step leaves a person whose switch says
    /// what they set and whose phone sends nothing — which is the safe
    /// direction, because the unsafe direction is a person who turned it off
    /// and keeps receiving.
    func choose(_ position: DailyPreference) async {
        chosen = position
        store.preference = position

        guard position.wantsDelivery else {
            await stopDelivery()
            return
        }

        // Provisional: granted without presenting anything. Nothing is shown to
        // the person at this line, which is why it is safe to run it from a
        // settings tap rather than from a ceremony.
        if push.authorization == .notDetermined {
            await push.requestProvisional()
        } else if push.authorization != .denied {
            push.registerForRemoteNotifications()
        }
        await registerIfPossible()
    }

    /// Escalate from quiet delivery to the real thing. This one does prompt.
    func letThemArriveProperly() async {
        await push.requestExplicit()
        await registerIfPossible()
    }

    func setHour(_ newHour: Int) async {
        hour = DailyStore.clamp(newHour)
        store.hour = hour
        await syncPreferenceToServer()
    }

    // MARK: — the token

    /// Hand the token over, if there is one and it is wanted.
    ///
    /// Called after every authorization change and on every foreground. It is
    /// deliberately not conditional on the token having *changed*: Apple can
    /// rotate a token without telling anybody, the only way to learn the new
    /// one is to ask on every launch, and a re-registration of an unchanged
    /// token is one small request that also refreshes `last_seen_at` — which is
    /// the column the server's stale-token sweep reads.
    func registerIfPossible() async {
        guard preference.wantsDelivery, isSubscriber else { return }
        guard push.authorization != .denied, push.authorization != .notDetermined else { return }

        // The token arrives asynchronously from UIKit after
        // `registerForRemoteNotifications`. Nothing here waits for it — a
        // launch where it has not landed yet re-registers on the next
        // foreground, which is seconds away and costs nobody anything.
        guard let token = push.token else { return }

        let body = DeviceRegistration(
            platform: "ios",
            token: token,
            environment: PushService.environment,
            timezone: TimeZone.current.identifier,
            appVersion: Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "0",
            osVersion: UIDevice.current.systemVersion,
            locale: Locale.current.identifier
        )

        do {
            _ = try await client.registerDevice(body)
            store.lastToken = token
            store.registeredAt = .now
            registeredAt = store.registeredAt
            // The position and the hour are the *user's*, not the install's,
            // and they go up their own route. Sent after the token so that a
            // 402 for a free reader cannot cost us the registration — a person
            // who later subscribes should already be reachable.
            await syncPreferenceToServer()
        } catch {
            // Still not shown as an error, and the reason has changed. The
            // route exists now; what remains unknowable from here is whether a
            // vendor credential is configured on the server, so a registration
            // that is accepted still does not prove anything will arrive.
            // `DailySettingsSection` describes the state rather than
            // apologising for it.
            store.clearRegistration()
            registeredAt = nil
            log.debug("device registration not accepted: \(String(describing: error), privacy: .public)")
        }
    }

    /// Tell the server to forget this device, and forget it here.
    ///
    /// `PUSH.md §6.2(6)`: **off deletes the row**, it does not set a flag
    /// consulted before sending. It is the withdrawal-of-consent obligation
    /// Guideline 4.5.4 puts on us and the simplest possible proof that off
    /// means off — a flag is a thing a future job can forget to read.
    func stopDelivery() async {
        let token = store.lastToken ?? push.token
        store.clearRegistration()
        registeredAt = nil

        // **Both halves, and the second one is why this is not one call.**
        // Deleting this device stops this device. `PATCH {"daily":"off"}` is
        // what stops the *account* — it is the only writer of
        // `User.daily_push`, and it also forgets every other device on the
        // server side, which is the case a person with a phone and a tablet
        // would otherwise discover the hard way.
        await syncPreferenceToServer()

        guard let token else { return }
        do {
            try await client.forgetDevice(token: token)
        } catch {
            // Raised to an error rather than logged at debug. A failed opt-out
            // is the one network failure in this file worth noticing: it is
            // the withdrawal of consent Guideline 4.5.4 requires, and it
            // failing silently is how somebody keeps hearing from us after
            // saying stop. The account-level PATCH above has already run, so
            // the person is not actually still reachable — but a delete that
            // did not happen is a row we are keeping without a reason to.
            log.error("device delete failed, the row may survive: \(String(describing: error), privacy: .public)")
        }
    }

    /// Push the user-level half — position, hour, timezone override — up.
    ///
    /// `PATCH /v1/notifications`. It used to post to `/v1/account/daily`,
    /// which does not exist, so no client had ever written `User.daily_push`
    /// and the server-side preference could not leave null.
    private func syncPreferenceToServer() async {
        do {
            _ = try await client.setDailyPreference(
                DailySettingsBody(daily: preference.rawValue, hour: hour)
            )
        } catch {
            log.debug("daily preference not accepted: \(String(describing: error), privacy: .public)")
        }
    }

    // MARK: — reconciling with the world

    /// Read the OS, re-register, and repair anything that drifted.
    ///
    /// Runs on every foreground. Three things it fixes, all of which are
    /// invisible until somebody complains: a permission revoked in iOS
    /// Settings while the app was closed, a token Apple rotated, and a
    /// subscription that lapsed since the last launch.
    func refresh(isSubscriber: Bool) async {
        self.isSubscriber = isSubscriber
        registeredAt = store.registeredAt
        await push.refreshAuthorization()

        if push.authorization == .denied || !isSubscriber || !preference.wantsDelivery {
            // A lapse stops the sends and **keeps the person's choice**.
            // Deleting the stored position on cancellation would mean asking
            // again on resubscription, which spends the one-shot permission
            // twice; `PUSH.md §4` makes the same call about the token row.
            if store.lastToken != nil { await stopDelivery() }
            return
        }
        push.registerForRemoteNotifications()
        await registerIfPossible()
    }

    /// The two actions on the notification itself, and the OS-level revocation.
    ///
    /// Wired through `NotificationCenter` rather than a closure on the delegate
    /// because the delegate is created before this model exists — on a cold
    /// launch the tap arrives first — and a broadcast that nobody is listening
    /// to yet is a no-op, where a call through a nil reference is a lost tap.
    private func observeNotificationActions() {
        let centre = NotificationCenter.default
        centre.addObserver(forName: .almaDailyTurnOff, object: nil, queue: .main) { [weak self] _ in
            Task { @MainActor in await self?.choose(.off) }
        }
        centre.addObserver(forName: .almaDailyQuieter, object: nil, queue: .main) { [weak self] _ in
            // One step down rather than off. The person said "fewer", and
            // hearing "fewer" as "none" is how a quieter subscriber becomes an
            // uninstall two months later.
            Task { @MainActor in
                guard let self else { return }
                await self.choose(self.preference == .occasionally ? .onlyWhatMatters : .off)
            }
        }
        centre.addObserver(forName: .almaDailyRevoked, object: nil, queue: .main) { [weak self] _ in
            Task { @MainActor in await self?.stopDelivery() }
        }
    }
}

extension DailyModel {

    /// A model for `#Preview`, wired to nothing.
    ///
    /// It exists because `@Environment(DailyModel.self)` is a non-optional
    /// lookup: a preview that does not supply one does not draw a placeholder,
    /// it traps. Both surfaces that use the daily are inside previews other
    /// agents will open, so the absence would be found the hard way.
    @MainActor
    static func preview() -> DailyModel {
        DailyModel(
            client: AlmaClient(tokens: EphemeralTokenStore(), installation: EphemeralInstallationId()),
            push: PushService()
        )
    }
}
