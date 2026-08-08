import SwiftUI

/// The app.
///
/// Everything it does is here and there is not much of it, which is the point:
/// two objects are created, put in the environment, and started. No screen
/// creates a client, and no screen fetches the account.
///
/// The launch sequence is deliberately one call. `AlmaSessionModel.start()`
/// mints or reads the account, then loads the profile, the entitlements and the
/// hub concurrently — and until it lands, `RootView` shows the one wait. Drawing
/// a cabinet before the entitlements arrive is a paywall flashing over something
/// the person already paid for.
@main
struct AlmaApp: App {

    /// One session model for the process. `@State` on the `App` is what keeps it
    /// alive across the whole run without a singleton — and without the two
    /// instances a `StateObject` in a view would create on the first render.
    @State private var session: AlmaSessionModel
    @State private var router = AppRouter()

    /// Three APNs callbacks have no SwiftUI equivalent, so UIKit's delegate is
    /// adopted for exactly those and nothing else. See `AlmaAppDelegate`.
    @UIApplicationDelegateAdaptor(AlmaAppDelegate.self) private var appDelegate

    /// What the operating system says about notifications, live.
    @State private var push: PushService

    /// What the person chose, whether it can be honoured, and the one place
    /// that decides either. Built here rather than inside a screen because both
    /// Today and Settings draw from it and two copies would disagree.
    @State private var daily: DailyModel

    init() {
        // Before the first view resolves a face, so that a bundled Playfair or
        // Golos is picked up on the very first frame rather than after a flash
        // of the system serif. See `AlmaFonts`.
        AlmaFonts.registerBundledFonts()

        // Constructed in one place and handed down, because `DailyModel` needs
        // the same client the session uses — a second `AlmaClient` would be a
        // second token cache — and the same `PushService` the delegate forwards
        // to. Locals first, then the three `State` wrappers, because a `State`
        // property initialiser cannot read another one.
        let session = AlmaSessionModel()
        let push = PushService()
        _session = State(initialValue: session)
        _push = State(initialValue: push)
        _daily = State(initialValue: DailyModel(client: session.client, push: push))
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(session)
                .environment(router)
                .environment(push)
                .environment(daily)
                // Night is the canvas, and the window itself has to be told —
                // otherwise the gap behind a sheet's rubber-band scroll is
                // system grey.
                .background(Color.almaNight)
                .task {
                    // The delegate and the category, before anything can be
                    // tapped. It asks the OS for **nothing** — no prompt, no
                    // provisional grant, no registration — because at first
                    // launch there is no birth date and therefore nothing this
                    // app could ever notify anybody about. `docs/PUSH.md §5.1`.
                    await push.start()
                    await session.start()
                    // Once the entitlements have landed, reconcile: a
                    // subscription that lapsed while the app was closed stops
                    // the sends, a permission revoked in iOS Settings deletes
                    // the token, and a token Apple rotated is re-registered.
                    await daily.refresh(isSubscriber: session.entitlements.isSubscriber)
                }
        }
    }
}
