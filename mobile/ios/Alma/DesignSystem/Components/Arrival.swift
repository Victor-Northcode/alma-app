import SwiftUI

/// Content arriving on screen — the entrance half of the motion vocabulary.
///
/// `AlmaMotion` in Metrics.swift covers *controls*: a tap, a state change, a
/// sheet. What it deliberately did not cover was content itself appearing, and
/// the result was screens that snap from empty to full in one frame — correct,
/// and lifeless. This file adds the one entrance the product uses everywhere:
/// a rise of a few points with a fade, staggered down the page.
///
/// One entrance, not several. A slide-from-the-left here and a zoom there is
/// how an app starts to feel like a slot machine; every block arriving the
/// same way, slightly after the block above it, is how a page feels set rather
/// than loaded. The stagger is capped so that a long page's last card never
/// waits out a second of choreography — beyond the cap, blocks arrive together.
extension AlmaMotion {

    /// Content arriving. Slower than `ui`, faster than `reveal` — a paragraph
    /// settling into place, not a curtain lifting.
    static let arrive = Animation.timingCurve(0.16, 1, 0.3, 1, duration: 0.55)

    /// The pause between one block's arrival and the next one's.
    static let arriveStagger: Double = 0.07

    /// How far below its seat a block starts. Points, small on purpose: this
    /// is settling, not flying in.
    static let arriveRise: CGFloat = 16
}

private struct RiseIn: ViewModifier {

    /// Position in the cascade. Capped, so a deep row on a long page does not
    /// spend a literal second invisible waiting for its turn.
    let index: Int

    @State private var seated = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content
            .opacity(seated ? 1 : 0)
            .offset(y: seated ? 0 : AlmaMotion.arriveRise)
            .onAppear {
                guard !seated else { return }
                if reduceMotion {
                    seated = true
                } else {
                    withAnimation(
                        AlmaMotion.arrive.delay(Double(min(index, 8)) * AlmaMotion.arriveStagger)
                    ) {
                        seated = true
                    }
                }
            }
    }
}

extension View {

    /// Fade-and-rise into place on first appearance, `index` steps down the
    /// cascade. `@State` keeps it a one-shot: a data refresh re-renders the
    /// view but does not replay the entrance.
    ///
    /// Safe in a plain `VStack`/`ScrollView`, where `onAppear` fires once. In
    /// a *lazy* stack a row scrolled far away is destroyed and will re-enter
    /// when scrolled back — acceptable for a chat, wrong for a table of
    /// contents; the screens here use plain stacks.
    func riseIn(_ index: Int = 0) -> some View {
        modifier(RiseIn(index: index))
    }
}

/// A card acknowledging a finger.
///
/// The gold button sinks by a point (`AlmaButtonStyle`) because it is a key.
/// A card is paper, and paper doesn't travel — it gives, very slightly, under
/// pressure. 1.5% of scale is below the threshold where a card reads as a
/// game tile, and exactly at the threshold where a screen stops feeling inert.
struct AlmaCardPressStyle: ButtonStyle {

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.985 : 1)
            .opacity(configuration.isPressed ? 0.92 : 1)
            .animation(AlmaMotion.tap, value: configuration.isPressed)
    }
}
