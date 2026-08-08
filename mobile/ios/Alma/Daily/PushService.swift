import Foundation
import OSLog
import UIKit
import UserNotifications

/// Everything the operating system has to be told, and everything it tells back.
///
/// One object, because the three things it owns are one thing: the
/// authorization status decides whether a token can exist, the token is what a
/// server needs, and a revoked permission has to delete the token. Split across
/// three types they drift, and the drift is invisible — a switch that says On
/// over a permission that was revoked in Settings a month ago.
///
/// **`notificationSettings()` is the truth and our flag is not.** Everything
/// below re-reads it on foreground rather than caching a boolean, because the
/// person can change it in a place we cannot observe and will not tell us they
/// did. `docs/PUSH.md §5.6`.
@MainActor
@Observable
final class PushService {

    /// What the OS currently says. `.notDetermined` until asked; `.provisional`
    /// is a *granted* state and not a lesser one — a person left there for a
    /// year is receiving the product, quietly, which is a supported outcome and
    /// not a failure to convert.
    private(set) var authorization: UNAuthorizationStatus = .notDetermined

    /// The APNs device token, hex, as Apple gives it. `nil` until
    /// `didRegisterForRemoteNotifications` lands — which on a simulator without
    /// a signed-in Apple ID may be never, and that is not an error worth
    /// showing anybody.
    private(set) var token: String?

    /// Set by the delegate when a notification is tapped. The router reads it.
    /// A date rather than a bool, because the payload names the day it is about
    /// and a person tapping Thursday's notification on Friday should be told so
    /// rather than shown Friday.
    var opened: DailyOpening?

    private let log = Logger(subsystem: "ai.pazl.alma", category: "push")
    private let store = DailyStore()

    /// The notification category every daily carries, so that the two actions
    /// ride on it.
    static let category = "ALMA_DAILY"
    static let actionTurnOff = "ALMA_DAILY_OFF"
    static let actionQuieter = "ALMA_DAILY_QUIETER"

    /// Which APNs environment this build's tokens belong to.
    ///
    /// **A build-time fact and not a runtime one.** `docs/PUSH.md §1.8`: the
    /// token is a hex string either way and the two environments' tokens are
    /// indistinguishable by inspection, so a sandbox token sent to the
    /// production endpoint comes back `400 BadDeviceToken` from a device that
    /// is working perfectly and a production token sent to sandbox is accepted
    /// with a 200 and delivered nowhere. The only reliable signal is which
    /// entitlement the binary was signed with, and that follows the
    /// configuration.
    ///
    /// The TestFlight trap is why this is `#if DEBUG` rather than
    /// `isDebuggerAttached` or a check on the receipt: a TestFlight build is a
    /// *distribution* build, its profile carries `aps-environment: production`,
    /// and its tokens are production tokens even though nothing about it feels
    /// like a release.
    static var environment: String {
        #if DEBUG
        "sandbox"
        #else
        "production"
        #endif
    }

    // MARK: — starting up

    /// Install the delegate and the category, and read the current status.
    ///
    /// Called once at launch. It asks for **nothing**: no prompt, no
    /// registration, no provisional grant. At first launch this app has no
    /// birth date, no chart and therefore nothing it could ever notify anybody
    /// about, and `PUSH.md §5.1` is unambiguous that spending the one question
    /// there is how you get the low end of a 43.9% opt-in.
    func start() async {
        // The delegate is a separate `NSObject`, and it has to be: UIKit
        // creates the application delegate before any SwiftUI value exists, so
        // `didRegisterForRemoteNotificationsWithDeviceToken` can land before
        // this object has been constructed. A static handoff is the only wire
        // that reaches across that gap — there is no environment to read from
        // inside a UIKit callback.
        AlmaAppDelegate.push = self
        UNUserNotificationCenter.current().delegate = AlmaAppDelegate.shared
        registerCategory()
        await refreshAuthorization()
        // A permission revoked while the app was closed leaves a token the
        // server would keep sending to. Reconciling here rather than only in
        // Settings means it is fixed by opening the app, which is the only
        // action we can rely on.
        await reconcileRevocation()
    }

    /// Re-read the OS. Cheap, and the only honest source.
    func refreshAuthorization() async {
        let settings = await UNUserNotificationCenter.current().notificationSettings()
        authorization = settings.authorizationStatus
    }

    // MARK: — asking

    /// The quiet enrolment: `.provisional`, which shows no dialog at all.
    ///
    /// Requesting `[.alert, .sound, .badge, .provisional]` returns granted
    /// without presenting anything. Notifications then arrive in Notification
    /// Center only — no banner, no sound, no lock screen — and each one carries
    /// its own **Keep** / **Turn Off** buttons. `THE-DAILY.md §5.3` chose this
    /// and the argument is the product's own: this feature's entire claim is
    /// that its notifications are worth having, and provisional is the
    /// mechanism that lets us prove that instead of asserting it. At the
    /// measured cadence, three notifications is three weeks, not three days.
    ///
    /// Returns whether anything is now permitted, which is not the same as
    /// whether a banner will appear.
    @discardableResult
    func requestProvisional() async -> Bool {
        guard authorization == .notDetermined else { return authorization != .denied }
        do {
            let granted = try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .sound, .badge, .provisional])
            await refreshAuthorization()
            if granted { registerForRemoteNotifications() }
            return granted
        } catch {
            log.error("provisional authorization failed: \(String(describing: error), privacy: .public)")
            return false
        }
    }

    /// The escalation, which does prompt.
    ///
    /// From `.provisional` a later request *without* `.provisional` shows the
    /// system dialog, because the person has never actually been asked — that
    /// is the documented upgrade path. `.denied` is still terminal: provisional
    /// moves *when* the one shot is taken, never *whether*.
    ///
    /// There is a documented iOS 16+ defect where choosing "Deliver
    /// Immediately" from a provisional notification fails to update the sound,
    /// badge and lock-screen settings. Nothing here assumes the upgrade landed:
    /// the status is re-read from the OS afterwards and the interface draws
    /// whatever that says.
    @discardableResult
    func requestExplicit() async -> Bool {
        guard authorization == .notDetermined || authorization == .provisional else {
            return authorization == .authorized
        }
        do {
            let granted = try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .sound, .badge])
            await refreshAuthorization()
            if granted { registerForRemoteNotifications() }
            return granted
        } catch {
            log.error("authorization failed: \(String(describing: error), privacy: .public)")
            return false
        }
    }

    /// Ask APNs for a token. Idempotent and safe to call on every foreground —
    /// Apple's own guidance is to call it at every launch, because the token
    /// can change without warning and the only way to learn the new one is to
    /// ask.
    func registerForRemoteNotifications() {
        guard authorization != .denied, authorization != .notDetermined else { return }
        UIApplication.shared.registerForRemoteNotifications()
    }

    // MARK: — what the app delegate hands back

    func didRegister(deviceToken: Data) {
        token = deviceToken.map { String(format: "%02x", $0) }.joined()
    }

    func didFailToRegister(_ error: any Error) {
        // Not surfaced to anybody, and that is the right call rather than a
        // gap. On a simulator with no Apple ID signed in this fires at every
        // launch and means nothing about the app; on a device it means the
        // entitlement or the provisioning profile is wrong, which is a build
        // problem and not a reader's problem. What the *reader* needs to know
        // is that nothing will arrive, and `DailySettingsSection` says exactly
        // that from `deliverable` — which is false either way.
        token = nil
        log.error("APNs registration failed: \(String(describing: error), privacy: .public)")
    }

    // MARK: — revocation

    /// If the OS says no and we still hold a token, the server must be told.
    ///
    /// The important half is that this runs on *every* foreground rather than
    /// only when the person touches our settings. Somebody who turns Alma's
    /// notifications off in iOS Settings never opens our screen again, and
    /// without this the server would go on sending into a hole for the life of
    /// the subscription.
    private func reconcileRevocation() async {
        guard authorization == .denied, store.lastToken != nil else { return }
        NotificationCenter.default.post(name: .almaDailyRevoked, object: nil)
    }

    // MARK: — the category

    /// Register the two actions every daily carries.
    ///
    /// `THE-DAILY.md §5.2` requires a permanent turn-off *inside the
    /// notification* — an action button, not a deep link into a settings tree —
    /// and the reasoning is worth keeping next to the code: the design goal is
    /// to make the disable path so easy that nobody reaches for the uninstall
    /// path. An uninstall costs the whole subscription; a person who taps
    /// "Fewer of these" is still a subscriber.
    ///
    /// Both are `.destructive`-free and neither opens the app
    /// (`.foreground` is deliberately not set): making somebody watch a launch
    /// animation to turn a notification off is the opposite of one tap.
    private func registerCategory() {
        let off = UNNotificationAction(
            identifier: Self.actionTurnOff,
            title: String(localized: DailyL10n.turnOff),
            options: []
        )
        let quieter = UNNotificationAction(
            identifier: Self.actionQuieter,
            title: String(localized: DailyL10n.quieter),
            options: []
        )
        let category = UNNotificationCategory(
            identifier: Self.category,
            actions: [quieter, off],
            intentIdentifiers: [],
            options: []
        )
        UNUserNotificationCenter.current().setNotificationCategories([category])
    }
}


/// A tap, with the day it was about.
///
/// `Identifiable` so a view can react to it with `.onChange`, and carrying the
/// payload's own date rather than "now": a notification sent on Thursday and
/// tapped on Friday is about Thursday, and the screen it opens should be able
/// to say so instead of quietly showing a different day's sky.
struct DailyOpening: Identifiable, Equatable, Sendable {
    let day: String?
    let at: Date = .now
    var id: String { "\(day ?? "-")-\(at.timeIntervalSince1970)" }
}

extension Notification.Name {
    /// Posted when the OS says permission is gone but we still hold a token.
    static let almaDailyRevoked = Notification.Name("alma.daily.revoked")
    /// Posted from the notification's own "Turn these off" action.
    static let almaDailyTurnOff = Notification.Name("alma.daily.turnOff")
    /// Posted from "Fewer of these".
    static let almaDailyQuieter = Notification.Name("alma.daily.quieter")
}

// MARK: — the object UIKit and UserNotifications talk to

/// The two delegates, in one `NSObject`, forwarding to `PushService`.
///
/// **Why it is not `PushService` itself.** `PushService` is `@Observable`, which
/// is what lets a SwiftUI view redraw when the authorization status changes.
/// Delegates are `NSObject` subclasses held by UIKit for the life of the
/// process, and merging the two roles would tie an observable value type's
/// lifetime to UIKit's — which is also the reason the static below is not a
/// singleton smell: UIKit already owns exactly one of these, and this is how
/// the SwiftUI half finds it.
///
/// Nothing else is routed through here. The app's launch sequence is still
/// `AlmaApp.task`; this object exists because three APNs callbacks have no
/// SwiftUI equivalent and never will.
final class AlmaAppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {

    /// The instance `UIApplicationDelegateAdaptor` created. Assigned in
    /// `application(_:didFinishLaunchingWithOptions:)`, which UIKit calls
    /// before anything else.
    nonisolated(unsafe) static var shared: AlmaAppDelegate?

    /// The observable half. Set by `PushService.start()`.
    @MainActor static var push: PushService?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        Self.shared = self
        return true
    }

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        Self.push?.didRegister(deviceToken: deviceToken)
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: any Error
    ) {
        Self.push?.didFailToRegister(error)
    }

    // MARK: — delivery and taps

    /// What happens when one arrives while the app is open.
    ///
    /// **`.list` and `.banner`, but never `.sound`.** The person is already
    /// looking at the app; a chime for a thing they can see is the small
    /// rudeness that makes somebody turn all of it off. The banner is worth
    /// showing rather than swallowing — if they are on Systems, the daily is
    /// still news, and the tap on it still has to land on the right screen.
    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        [.list, .banner]
    }

    /// What happens when one is tapped, or one of its actions is.
    ///
    /// This is the only path that opens the daily, and it has to work in three
    /// states the system does not distinguish for you: the app cold-launched by
    /// the tap, the app resumed from the background, and the app already
    /// foreground on the very screen the notification points at.
    ///
    /// It works in all three for one structural reason — **it sets a value on a
    /// long-lived object rather than performing navigation**. `RootView`
    /// observes that value and acts on it when it can. A delegate that called
    /// `router.push` directly would fire before the router existed on a cold
    /// launch, which is the classic version of this bug and the one that only
    /// ever reproduces from a killed app.
    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        let info = response.notification.request.content.userInfo
        // The payload's custom keys sit *beside* `aps`, never inside it —
        // `docs/PUSH.md §1.6` — and this is the one place the app reads them.
        let day = info["date"] as? String
        let action = response.actionIdentifier

        await MainActor.run {
            switch action {
            case PushService.actionTurnOff:
                NotificationCenter.default.post(name: .almaDailyTurnOff, object: nil)
            case PushService.actionQuieter:
                NotificationCenter.default.post(name: .almaDailyQuieter, object: nil)
            case UNNotificationDefaultActionIdentifier:
                Self.push?.opened = DailyOpening(day: day)
            default:
                // A dismissal. That is an answer, and not a request to open
                // anything — a swiped-away notification that still launched the
                // app would be the rudest thing in the product.
                break
            }
        }
    }
}
