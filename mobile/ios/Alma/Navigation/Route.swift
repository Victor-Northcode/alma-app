import SwiftUI

/// The four tabs of the cabinet.
///
/// They are the web app's `(cabinet)` routes: `/today`, `/systems`, `/alma`,
/// `/settings`. Everything else — a system, a chapter, the people list, the
/// cross-synthesis — is *pushed* onto one of these, which is why they are not in
/// this enum.
enum CabinetTab: String, CaseIterable, Hashable, Sendable, Identifiable {
    case today
    case systems
    case alma
    case settings

    var id: String { rawValue }

    var title: LocalizedStringResource {
        switch self {
        case .today: L10n.tabToday
        case .systems: L10n.tabSystems
        case .alma: L10n.tabAlma
        case .settings: L10n.tabSettings
        }
    }
}

/// Everywhere the app can push to.
///
/// One enum for the whole app rather than one per tab, because a route has to be
/// reachable from more than one place: the hub pushes a system, Today pushes the
/// same system, a chapter's "read the next one" pushes a sibling. A per-tab enum
/// would mean the same screen described three times.
///
/// `Hashable` is what `NavigationStack` needs; `Codable` is deliberately *not*
/// here. Restoring a navigation stack across launches would mean restoring a
/// chapter reader onto an account whose entitlements have not loaded yet, which
/// is a paywall flashing over something the person already owns.
enum Route: Hashable, Sendable {

    /// One of the eight: its chapters, its free calculation, its door.
    case system(SystemSlug)

    /// One chapter of one system. The thing that is sold.
    case chapter(system: SystemSlug, chapter: String)

    /// The people this account has saved — needed before compatibility can run.
    case people

    /// Adding a second person, from inside the compatibility flow.
    case addPerson

    /// One conversation.
    case thread(id: String)

    /// The ladder. Reached from a locked chapter, from Today's offer, and from
    /// settings.
    case offer(system: SystemSlug?)

    /// Sign in — which *attaches* an identity to this account rather than
    /// replacing it.
    case signIn

    /// One of the five legal documents. They are in the app rather than in a
    /// browser because App Review opens every one of them.
    case legal(LegalDocument)
}

/// The five documents the footer links to. There are five and there is nowhere
/// else to add a sixth without writing it: a link is a claim that the document
/// behind it exists.
enum LegalDocument: String, Hashable, Sendable, CaseIterable, Identifiable {
    case terms
    case privacy
    case refunds
    case subscriptionTerms = "subscription-terms"
    case imprint

    var id: String { rawValue }
}

/// Where the app is, and the one place that says so.
///
/// It holds a path per tab rather than one shared path, because that is what a
/// tab bar means: switching to Settings and back must leave the chapter you were
/// reading exactly where it was. A single `NavigationPath` would empty it.
///
/// The journey is not a route. It is a `fullScreenCover` — a modal presentation
/// path, kept separate on purpose: the journey is a linear ceremony that owns the
/// screen, and putting it on a navigation stack would give it a back button that
/// steps out of the middle of it.
@MainActor
@Observable
final class AppRouter {

    /// Which tab is showing.
    ///
    /// The debug launch argument (`-AlmaTab alma`) exists for the harness that
    /// verifies screens by screenshot: the simulator cannot be tapped from the
    /// command line on this machine, and a screen nobody can reach is a screen
    /// nobody can check. Release builds ignore it.
    var tab: CabinetTab = {
        #if DEBUG
        if let name = UserDefaults.standard.string(forKey: "AlmaTab"),
           let chosen = CabinetTab.allCases.first(where: { "\($0)" == name }) {
            return chosen
        }
        #endif
        return .today
    }()

    /// One stack per tab.
    var paths: [CabinetTab: [Route]] = {
        #if DEBUG
        // `-AlmaSystem natal` / `-AlmaOffer 1` — the same screenshot-harness
        // affordance as `-AlmaTab`: a route pre-pushed so a screen deep in a
        // stack can be photographed without a tap. Release builds ignore both.
        if let slug = UserDefaults.standard.string(forKey: "AlmaSystem"),
           let system = SystemSlug(rawValue: slug) {
            return [.systems: [Route.system(system)]]
        }
        if UserDefaults.standard.bool(forKey: "AlmaOffer") {
            return [.systems: [Route.offer(system: nil)]]
        }
        #endif
        return [:]
    }()

    /// Whether the journey is on screen. Set this rather than pushing.
    var journeyPresented: Bool = false

    /// A sheet the whole app can raise — sign-in, chiefly, which is reachable
    /// from settings and from the end of a purchase.
    var sheet: Route?

    /// The daily notification somebody tapped, if they did.
    ///
    /// Held here rather than acted on inside the notification delegate, and the
    /// reason is the cold-launch case. A tap on a notification for an app that
    /// is not running delivers the response *before* the first SwiftUI view has
    /// resolved: a delegate that navigated directly would be reaching for a
    /// router that does not exist yet, and the tap would be silently lost —
    /// which is the version of this bug that never reproduces from a
    /// backgrounded app and always reproduces from a killed one.
    ///
    /// So the delegate sets a value, this holds it, and `openDaily` below is
    /// run by the shell once there is a shell.
    var openedDaily: DailyOpening?

    /// Put the daily on screen: Today, at the top, whatever was showing.
    ///
    /// `popToRoot` and not `push`, because the daily is not a destination — it
    /// is the top of the Today tab. Somebody who was three chapters deep in
    /// Systems when the notification arrived should land on the thing they
    /// tapped, and find their chapter still there when they go back to it,
    /// which is what one stack per tab already gives them.
    func openDaily(_ opening: DailyOpening) {
        openedDaily = opening
        popToRoot(.today)
        tab = .today
        // A sheet over the screen the tap was meant to open is the same failure
        // as landing on the wrong screen, and sign-in is raised from three
        // places that could easily still be up.
        sheet = nil
    }

    // MARK: — pushing

    /// Push onto the tab that is showing.
    func push(_ route: Route) {
        paths[tab, default: []].append(route)
    }

    /// Push onto a specific tab and switch to it.
    ///
    /// **Only for flows that have no tab of their own** — the journey, a
    /// notification tap. A screen inside a tab pushes with `push(_:)` so that
    /// going back lands exactly where the person left; the owner's report on
    /// the old behaviour was that opening an offer from Today returned him to
    /// My Systems, a screen he had never been on.
    func push(_ route: Route, on tab: CabinetTab) {
        self.tab = tab
        paths[tab, default: []].append(route)
    }

    func pop() {
        _ = paths[tab]?.popLast()
    }

    /// Empty a tab's stack. What tapping an already-selected tab does.
    func popToRoot(_ tab: CabinetTab) {
        paths[tab] = []
    }

    /// A binding a `NavigationStack` can hold.
    ///
    /// A method rather than four stored properties, so that adding a fifth tab
    /// is one case in an enum and not a fifth property plus a fifth binding
    /// plus a fifth `NavigationStack`.
    func binding(for tab: CabinetTab) -> Binding<[Route]> {
        Binding(
            get: { self.paths[tab] ?? [] },
            set: { self.paths[tab] = $0 }
        )
    }

    // MARK: — the journey

    /// Open the journey. The one entry point, so that the funnel beacon for
    /// `quiz_start` has exactly one place to live when it is wired in.
    func openJourney() {
        journeyPresented = true
    }

    func closeJourney() {
        journeyPresented = false
    }
}
