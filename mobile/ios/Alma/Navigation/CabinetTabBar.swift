import SwiftUI

/// The bottom bar.
///
/// **Drawn rather than configured.** `TabView` gives a `UITabBar`, and a
/// `UITabBar` is the single most recognisable piece of iOS chrome there is: a
/// translucent white-or-grey slab with blue tint. Every part of it that would
/// have to be overridden — the material, the tint, the selected colour, the
/// icon rendering mode, the item spacing — is a global appearance proxy set from
/// somewhere far away, which is exactly the kind of code that stops working
/// each September. Forty lines of `HStack` is smaller, it is local, and it is
/// the design.
///
/// The look is the web app's: 58 points plus the home-indicator inset, a night
/// slab at 94% over a blur, one gold hairline on top, inactive glyphs at 50%
/// body, active in gold-bright with a 3-point dot beneath.
struct CabinetTabBar: View {

    @Environment(AppRouter.self) private var router

    /// How much of the screen the home indicator owns, on this device, now.
    ///
    /// Not private: the chat's composer is pinned to the bottom by its own
    /// `safeAreaInset` and has to clear the same bar, so both sides read one
    /// number. The composer was padded by `tabBarHeight` alone and sat half
    /// under the bar — the owner sent a screenshot of "Ask Alma" sliced in two
    /// by the tab labels.
    ///
    /// `UIScreen.main` is deprecated and wrong on a second display; the key
    /// window's own insets are the only value that is right in a split view,
    /// on an iPad stage, and on a phone with no indicator at all.
    static var homeIndicator: CGFloat {
        UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows)
            .first { $0.isKeyWindow }?
            .safeAreaInsets.bottom ?? 0
    }

    /// Where the finger is while it is dragging along the bar, in points from
    /// the bar's leading edge. Nil when nobody is dragging.
    @State private var dragging: CGFloat?
    /// The bar's own width, measured, because the drag has to be turned into a
    /// tab index and only a measurement knows how wide a quarter is.
    @State private var width: CGFloat = 0

    var body: some View {
        HStack(spacing: 0) {
            ForEach(CabinetTab.allCases) { tab in
                let active = router.tab == tab
                Button {
                    // Tapping the tab you are already on empties its stack —
                    // the platform behaviour, and the only way back out of a
                    // chapter four pushes deep without four taps.
                    if active {
                        router.popToRoot(tab)
                    } else {
                        router.tab = tab
                    }
                } label: {
                    VStack(spacing: 5) {
                        TabGlyph(tab: tab, active: active)
                            .frame(width: 24, height: 24)
                        Text(tab.title)
                            .font(AlmaFonts.ui(11))
                            .lineLimit(1)
                            .minimumScaleFactor(0.8)
                        Circle()
                            .fill(active ? Color.almaGold : .clear)
                            .frame(width: 3, height: 3)
                    }
                    .foregroundStyle(active ? Color.almaGoldBright : Color.almaBody.opacity(0.5))
                    .frame(maxWidth: .infinity)
                    // 48 points is the floor for a touch target; the bar is 58
                    // so this never actually clips, and it stops a future
                    // change to the label from quietly shrinking the target.
                    .frame(minHeight: 48)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(active ? [.isSelected, .isButton] : .isButton)
            }
        }
        .padding(.top, 9)
        .frame(height: AlmaMetrics.tabBarHeight)
        .onGeometryChange(for: CGFloat.self, of: \.size.width) { width = $0 }
        // **Hold and slide, the way Telegram's bar works.** The owner asked for
        // it in those words: press Today, move without letting go, and the
        // selection travels with the finger.
        //
        // A `minimumDistance` of 12 rather than 0, so an ordinary tap is still
        // handled by the buttons above and never by this: at zero the gesture
        // swallows every touch on the bar and the buttons stop firing, which is
        // the obvious way to build this and is wrong.
        //
        // `simultaneously` is not used and would be a mistake here — the drag
        // and the buttons want the same touches, and letting both win means a
        // slide that also taps whatever it started on.
        .gesture(
            DragGesture(minimumDistance: 12)
                .onChanged { value in
                    dragging = value.location.x
                    guard let tab = tab(at: value.location.x) else { return }
                    if tab != router.tab {
                        AlmaHaptics.tick()
                        withAnimation(AlmaMotion.ui) { router.tab = tab }
                    }
                }
                .onEnded { _ in dragging = nil }
        )
        // **No bottom padding here, and that is the second attempt.**
        //
        // The first fix for the eaten line added `.padding(.bottom,
        // homeIndicator)` on the theory that the bar's frame was short of what
        // it painted. It is not: `safeAreaInset(edge: .bottom)` already places
        // its content *above* the existing bottom safe area, so the indicator
        // gap is there before this view is measured. Adding it again lifted the
        // labels a whole indicator's height off the floor and left a band of
        // empty night beneath them — the owner sent the screenshot.
        //
        // The eaten line was never this. It was `NavigationStack` taking its
        // safe area from the window rather than from the shell that wrapped it,
        // so the inset the shell reserved reached no scroll view inside — fixed
        // in `ScreenScaffold` via `cabinetBarHeight`.
        .background {
            ZStack {
                Rectangle().fill(.ultraThinMaterial)
                Color.almaNight850.opacity(0.94)
            }
            .ignoresSafeArea(edges: .bottom)
        }
        .overlay(alignment: .top) {
            Rectangle()
                .fill(Color.almaGold.opacity(0.14))
                .frame(height: AlmaMetrics.hairline)
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(Text(L10n.cabinetSections))
    }

    /// Which tab the finger is over.
    ///
    /// The bar is four equal columns, so the index is the position divided by a
    /// quarter of the width — clamped rather than wrapped, because dragging off
    /// the end should stop at the end and not reappear at the other one.
    /// Returns nil before the width has been measured, which is the first frame
    /// and no drag can have started in it.
    private func tab(at x: CGFloat) -> CabinetTab? {
        guard width > 0 else { return nil }
        let column = width / CGFloat(CabinetTab.allCases.count)
        let index = min(CabinetTab.allCases.count - 1, max(0, Int(x / column)))
        return CabinetTab.allCases[index]
    }
}

/// The four glyphs, drawn as paths.
///
/// Not SF Symbols. `sun.max`, `circle.hexagongrid` and `gearshape` are the icons
/// of every app on the phone, and the sun in particular would say "weather".
/// These are the web app's: a small sun with four rays for Today, two concentric
/// circles for the eight systems, Alma's own point of light for her, and a
/// gear-less settings mark that is a dot with six short strokes.
private struct TabGlyph: View {

    let tab: CabinetTab
    let active: Bool

    var body: some View {
        switch tab {
        case .alma:
            // Alma is never a line drawing. She is the warm point of light, at
            // the one size where the ring is dropped.
            AlmaPresence(size: 20, ring: false)
                .opacity(active ? 1 : 0.65)
        case .today:
            Canvas { context, size in
                let stroke = strokeStyle(active)
                let c = CGPoint(x: size.width / 2, y: size.height / 2)
                let r = size.width * 0.1667

                context.stroke(
                    Path(ellipseIn: CGRect(x: c.x - r, y: c.y - r, width: r * 2, height: r * 2)),
                    with: .color(stroke), lineWidth: 1.25
                )
                var rays = Path()
                for angle in stride(from: 0.0, to: 360.0, by: 90.0) {
                    let radians = angle * .pi / 180
                    let inner = size.width * 0.34
                    let outer = size.width * 0.46
                    rays.move(to: CGPoint(x: c.x + cos(radians) * inner, y: c.y + sin(radians) * inner))
                    rays.addLine(to: CGPoint(x: c.x + cos(radians) * outer, y: c.y + sin(radians) * outer))
                }
                context.stroke(rays, with: .color(stroke), lineWidth: 1.25)
            }
        case .systems:
            Canvas { context, size in
                let stroke = strokeStyle(active)
                let c = CGPoint(x: size.width / 2, y: size.height / 2)
                for r in [size.width * 0.375, size.width * 0.1333] {
                    context.stroke(
                        Path(ellipseIn: CGRect(x: c.x - r, y: c.y - r, width: r * 2, height: r * 2)),
                        with: .color(stroke), lineWidth: 1.25
                    )
                }
            }
        case .settings:
            Canvas { context, size in
                let stroke = strokeStyle(active)
                let c = CGPoint(x: size.width / 2, y: size.height / 2)
                let r = size.width * 0.125
                context.stroke(
                    Path(ellipseIn: CGRect(x: c.x - r, y: c.y - r, width: r * 2, height: r * 2)),
                    with: .color(stroke), lineWidth: 1.25
                )
                var spokes = Path()
                for angle in stride(from: 30.0, to: 360.0, by: 60.0) {
                    let radians = angle * .pi / 180
                    let inner = size.width * 0.29
                    let outer = size.width * 0.42
                    spokes.move(to: CGPoint(x: c.x + cos(radians) * inner, y: c.y + sin(radians) * inner))
                    spokes.addLine(to: CGPoint(x: c.x + cos(radians) * outer, y: c.y + sin(radians) * outer))
                }
                context.stroke(spokes, with: .color(stroke), lineWidth: 1.25)
            }
        }
    }

    private func strokeStyle(_ active: Bool) -> Color {
        active ? .almaGoldBright : Color.almaBody.opacity(0.5)
    }
}

#Preview("Tab bar") {
    VStack {
        Spacer()
        CabinetTabBar()
    }
    .nightSky()
    .environment(AppRouter())
}
