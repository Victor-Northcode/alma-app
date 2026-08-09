import SwiftUI

/// The shell. Four stacks, one bar, one modal path for the journey.
///
/// **This file should never need editing when a screen arrives.** It knows about
/// four tab roots and one route-to-view function, all of which live in
/// `Screens/` and are owned by whoever builds the screens. Adding a destination
/// is a case in `Route` plus a branch in `RouteDestination`; it is not a change
/// here.
///
/// **All four stacks stay alive.** They sit side by side in a pager rather than
/// in a `switch`, because a `switch` destroys the view that leaves the screen:
/// scroll position, a half-typed question to Alma, and a chapter's place in a
/// long read all vanish on a tab switch. Four screens is a tolerable amount of
/// memory; losing somebody's place in a chapter they paid for is not.
struct RootView: View {

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router
    @Environment(PushService.self) private var push

    /// Whether the first-run question has already been answered this launch.
    ///
    /// See `openJourneyOnFirstRun`. It exists so the answer cannot be given
    /// twice, and so that it is *not* re-derived from `hasBirthData` — which
    /// changes under the person while they are still inside the journey.
    @State private var firstRunDecided = false

    /// Whether the arrival has finished. See `AlmaLaunch`.
    ///
    /// Held here rather than inside the launch view because it outlives it: the
    /// cabinet must not be built behind the launch screen and then revealed
    /// half-drawn, and the journey must not be presented over a screen the
    /// person has not seen yet.
    @State private var launched = false

    /// How far the pager has been dragged, in points, while a finger is down.
    @State private var tabDrag: CGFloat = 0
    /// Whether that finger is still down. The offset animates when it is not,
    /// and must not while it is — an animation on a value the finger is already
    /// setting is the lag people call "sluggish".
    @State private var dragging = false

    var body: some View {
        @Bindable var router = router

        // The sky is *not* drawn here, and the reason is worth writing down
        // because the obvious arrangement does not work.
        //
        // One `NightSky` under a `ZStack` of `NavigationStack`s renders
        // nothing: a navigation container fills itself with an opaque
        // background, so the sky sits behind four black rectangles and every
        // screen in the app is flat black. It is not a translucency that can be
        // turned off — there is no modifier for the container's own fill.
        //
        // So each screen carries its own sky. `ScreenScaffold` applies it, and
        // a screen that does not use the scaffold calls `.nightSky()` itself.
        // The design wanted this anyway: a different seed per screen means
        // moving between two screens is visibly moving rather than the same
        // stars twice.
        Group {
            switch session.bootstrap {
            // A failure is shown at once. Somebody whose network is down has
            // nothing to arrive *to*, and a ceremony in front of an error is
            // the app admiring itself while the person waits.
            case .failed(let error):
                AlmaFailure(error: error) {
                    launched = false
                    await session.start()
                }
                .nightSky()

            case .loading, .loaded:
                if launched {
                    cabinet.task { openJourneyOnFirstRun() }
                } else {
                    AlmaLaunch(ready: session.bootstrap.value != nil) {
                        // Slower than a screen change and slower than the fade
                        // in: this is the app opening, and the eye reads a
                        // long dissolve as deliberate where a short one reads
                        // as a stutter.
                        withAnimation(.easeInOut(duration: 0.55)) { launched = true }
                    }
                    .transition(.opacity)
                }
            }
        }
        .tint(Color.almaGoldBright)
        // StoreKit's live feed, consumed for the life of the process.
        //
        // The modifier was written for this line and never applied, so the
        // `Transaction.updates` listener and the `Transaction.unfinished` sweep
        // only started when somebody opened the paywall. Everything Apple
        // delivers asynchronously was invisible until then: an Ask to Buy a
        // parent approved an hour ago, a purchase made on another device on the
        // same Apple ID, a renewal, a refund that should close a grant — and,
        // worst, every interrupted purchase whose verify hit a 503. Somebody who
        // paid, lost the network mid-verify and relaunched saw locked chapters
        // and no path back except opening a paywall for something they already
        // owned, which is the moment they ask for a refund instead.
        //
        // It is idempotent, so the paywall and the restore button may go on
        // calling it in their own `.task` without claiming a second listener.
        .almaStoreListener(session)
        // A tapped daily, wherever the app was when it was tapped.
        //
        // `onChange(initial: true)` is the whole of the cold-launch case and is
        // easy to leave out: when a tap *launches* the app, the delegate has
        // already set `opened` by the time this view first appears, so there is
        // no change left to observe. Without `initial: true` the notification
        // works from the background and silently does nothing from a killed
        // app, which is exactly the half nobody tests.
        //
        // It is here rather than on `TodayScreen` because Today may not be the
        // tab that is showing, and a screen that is not on screen observes
        // nothing.
        .onChange(of: push.opened, initial: true) { _, opening in
            guard let opening else { return }
            router.openDaily(opening)
            // Cleared so that a second tap on a second notification is a second
            // change rather than the same value assigned twice.
            push.opened = nil
        }
        .fullScreenCover(isPresented: $router.journeyPresented) {
            JourneyFlow()
        }
        .sheet(item: $router.sheet) { route in
            NavigationStack {
                RouteDestination(route: route)
                    .almaScreenChrome()
            }
            .presentationBackground(Color.almaNight)
        }
    }

    /// Somebody with no birth data has a journey to walk, not a tab bar.
    ///
    /// **This was missing entirely, and the owner found it by opening the app.**
    /// Every one of the eight callers of `openJourney` is a button — the empty
    /// state on Today, the one on My systems, Settings, a locked chapter — so
    /// the journey was reachable only by someone who had already decided to
    /// look for it. A person who had just installed Alma was dropped straight
    /// into the cabinet: four tabs of empty states, a list of forty-one
    /// chapters they cannot open, and a gold button. The questions that make
    /// the product feel like it is about *them* — "what's loudest in you right
    /// now" — were never shown. Android had this from the start
    /// (`MainActivity.kt`, `startDestination`); iOS never did.
    ///
    /// **Decided once, on the edge, and never re-derived.** That is the whole
    /// reason for `firstRunDecided`, and Android's comment records what it cost
    /// to learn: `hasBirthData` does not only turn true when the profile
    /// request answers, it turns true the moment the journey *saves* a birth —
    /// which happens under the ceremony, three steps before the journey ends.
    /// Bound live, the cover would dismiss itself mid-animation and the person
    /// would land in Today having never seen their portrait, which is the free
    /// value the entire offer rests on.
    ///
    /// A `.task` on the loaded branch is that edge: the cabinet is built when
    /// `bootstrap` becomes `.loaded` and is not rebuilt when the journey
    /// closes, so this runs exactly once per launch. Returning users — anybody
    /// with a profile — never see it.
    private func openJourneyOnFirstRun() {
        guard !firstRunDecided else { return }
        firstRunDecided = true
        guard !session.hasBirthData else { return }
        router.openJourney()
    }

    /// Move one tab along, if there is one to move to.
    ///
    /// No wrapping: Settings does not lead back to Today. A carousel makes the
    /// end of the bar invisible, and the bar is four items — a person can see
    /// where they are and there is nothing to discover by looping.
    /// Where a tab sits in the bar, left to right.
    private func position(of tab: CabinetTab) -> Int {
        CabinetTab.allCases.firstIndex(of: tab) ?? 0
    }

    /// Whether a drag starting here may page between tabs.
    ///
    /// Not inside a stack — there the gesture is back. Not from the left edge —
    /// that is `AlmaScreenChrome`'s, and when both owned it one swipe popped a
    /// screen *and* changed tab.
    private func canPage(from startX: CGFloat) -> Bool {
        guard router.paths[router.tab]?.isEmpty ?? true else { return false }
        return startX > 28
    }

    /// The drag, with the ends made heavy.
    ///
    /// There is nothing to the left of Today or to the right of Settings, so
    /// pulling that way moves a third as far — enough to say "this is the end"
    /// without the wall a hard stop would be.
    private func damped(_ translation: CGFloat, width: CGFloat) -> CGFloat {
        let index = position(of: router.tab)
        let atStart = index == 0 && translation > 0
        let atEnd = index == CabinetTab.allCases.count - 1 && translation < 0
        return (atStart || atEnd) ? translation * 0.32 : translation
    }

    private func step(_ direction: Int) {
        let tabs = CabinetTab.allCases
        guard let current = tabs.firstIndex(of: router.tab) else { return }
        let next = current + direction
        guard tabs.indices.contains(next) else { return }
        AlmaHaptics.tick()
        withAnimation(AlmaMotion.page) { router.tab = tabs[next] }
    }

    /// **Four stacks side by side, moved as one.**
    ///
    /// They used to be a `ZStack` with three of them at `opacity(0)` and no
    /// animation at all: switching was instantaneous, which reads as a
    /// screenshot being swapped rather than as moving through an app. A short
    /// cross-fade with a nudge was tried next and it is the wrong shape — what
    /// the eye wants here is the thing it already knows from every messaging
    /// app, where the page follows the finger and the next one is visibly
    /// arriving from the side.
    ///
    /// So this is a pager. The row is four screens wide, offset to the active
    /// one, and the drag moves the offset directly — which is what makes it
    /// feel like paper rather than like a decision being submitted.
    ///
    /// All four stay alive, which was the reason for the `ZStack` and has not
    /// changed: a `switch` destroys the view that leaves, taking scroll
    /// position, a half-typed question and somebody's place in a long chapter
    /// with it.
    private var cabinet: some View {
        GeometryReader { screen in
            let width = screen.size.width
            let index = CGFloat(position(of: router.tab))
            HStack(spacing: 0) {
                ForEach(CabinetTab.allCases) { tab in
                    let active = router.tab == tab
                    stack(for: tab)
                        .frame(width: width)
                        // A stack that is not showing must not take taps, and
                        // must not be read out by VoiceOver — three off-screen
                        // tabs in the accessibility tree is three screens of
                        // duplicated content.
                        .allowsHitTesting(active)
                        .accessibilityHidden(!active)
                }
            }
            .frame(width: width * CGFloat(CabinetTab.allCases.count), alignment: .leading)
            .offset(x: -index * width + tabDrag)
            .animation(dragging ? nil : AlmaMotion.page, value: router.tab)
            .animation(dragging ? nil : AlmaMotion.page, value: tabDrag)
            .contentShape(Rectangle())
            // **The pager's own gesture, and the three things it must not do.**
            //
            // It must not fire inside a stack: there the same movement is back,
            // and a screen where sliding right sometimes leaves and sometimes
            // changes tab is worse than one that only ever does one of them.
            //
            // It must not fire from the left edge, because that *is* the back
            // gesture — `AlmaScreenChrome` owns the first 24 points, and when
            // both ran the owner's swipe popped a screen and changed tab in one
            // movement. Found on the simulator, once the gesture existed to be
            // found.
            //
            // And it must not fire on a drag that is taller than it is wide,
            // which is how it stays off every scroll view underneath it.
            .simultaneousGesture(
                DragGesture(minimumDistance: 18, coordinateSpace: .global)
                    .onChanged { value in
                        guard canPage(from: value.startLocation.x) else { return }
                        guard abs(value.translation.width) > abs(value.translation.height) else { return }
                        dragging = true
                        tabDrag = damped(value.translation.width, width: width)
                    }
                    .onEnded { value in
                        defer { dragging = false; tabDrag = 0 }
                        guard dragging else { return }
                        let travelled = value.translation.width
                        let predicted = value.predictedEndTranslation.width
                        // A third of the screen, or a flick that would have got
                        // there. The flick is what makes it feel quick.
                        let far = abs(travelled) > width / 3 || abs(predicted) > width * 0.8
                        guard far else { return }
                        step(travelled < 0 ? 1 : -1)
                    }
            )
        }
        // **An overlay that ignores the keyboard, not an inset.** As a
        // `safeAreaInset` the bar joined the keyboard's safe area, so when a
        // keyboard rose the bar rode up on top of it — and the chat composer,
        // which sits above the bar, was carried a whole bar-height above the
        // keys. The owner photographed exactly that band twice. An overlay
        // pinned to the bottom that ignores the keyboard stays where a tab bar
        // belongs, and the keyboard simply covers it — which is what every
        // system app does. Screens never relied on the inset for their own
        // layout anyway: a `NavigationStack` reads its safe area from the
        // window, which is why `cabinetBarHeight` below exists.
        .overlay(alignment: .bottom) {
            CabinetTabBar()
                .ignoresSafeArea(.keyboard, edges: .bottom)
        }
        // The one standing invitation — a small gold seal above the bar on
        // the two content tabs, gone the moment a plan exists. The competitor
        // set floats «Get Full Access» over every screen; this is the same
        // door at a volume this product can say with a straight face.
        .overlay(alignment: .bottomTrailing) {
            if !session.entitlements.isSubscriber,
               router.tab == .today || router.tab == .systems,
               session.hasBirthData {
                Button {
                    router.sheet = .offer(system: nil)
                } label: {
                    HStack(spacing: 6) {
                        Text(verbatim: "✦")
                            .font(.system(size: 12))
                        Text(L10nCabinet.allAlmaPill)
                            .font(AlmaFonts.ui(13, weight: .medium))
                    }
                    .foregroundStyle(Color.almaInkOnGold)
                    .padding(.horizontal, 14)
                    .frame(height: 34)
                    .background(Capsule().fill(Color.almaGold))
                    .shadow(color: AlmaShadow.button, radius: AlmaShadow.buttonRadius, y: 4)
                }
                .buttonStyle(AlmaCardPressStyle())
                .padding(.trailing, AlmaMetrics.pad)
                .padding(.bottom, AlmaMetrics.tabBarHeight + 18)
                .ignoresSafeArea(.keyboard, edges: .bottom)
                .transition(.opacity)
            }
        }
        // The inset above is not enough on its own — see `cabinetBarHeight`.
        // A `NavigationStack` reads its safe area from the window, so the bar
        // this shell reserved was invisible to every scroll view inside it.
        // This is the same number, handed to the screens directly.
        .environment(\.cabinetBarHeight, AlmaMetrics.tabBarHeight)
    }

    @ViewBuilder
    private func stack(for tab: CabinetTab) -> some View {
        @Bindable var router = router

        NavigationStack(path: router.binding(for: tab)) {
            root(for: tab)
                // The roots have nothing to go back to, so they get the bar
                // hidden rather than a back button pointing nowhere.
                .toolbar(.hidden, for: .navigationBar)
                .navigationDestination(for: Route.self) { route in
                    RouteDestination(route: route)
                        .almaScreenChrome()
                }
        }
    }

    /// The four tab roots. The only place the shell names a screen type.
    @ViewBuilder
    private func root(for tab: CabinetTab) -> some View {
        switch tab {
        case .today: TodayScreen()
        case .systems: SystemsScreen()
        case .alma: AlmaScreen()
        case .settings: SettingsScreen()
        }
    }
}

/// `sheet(item:)` needs identity, and `Route` is a value. Deriving it from the
/// hash is enough here: the sheet holds one route at a time, so the only thing
/// the identity has to do is change when the route does.
extension Route: Identifiable {
    var id: Int { hashValue }
}

#Preview("Shell") {
    RootView()
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
        .environment(PushService())
        .environment(DailyModel.preview())
}
