import SwiftUI

/// Spacing, rhythm and motion — the numbers the web app fixes in `:root` so
/// that no screen invents its own.
///
/// They are here, together, for the reason the CSS keeps them together: a
/// padding chosen per screen becomes six paddings within a week, and the
/// difference between 20 and 22 is invisible in a diff and obvious on a page.
enum AlmaMetrics {

    /// The side margin every screen uses. One value, not a responsive ramp:
    /// the web app widens it at 700 and 1024 px, and a phone is neither.
    static let pad: CGFloat = 22

    /// The measure a reading is set to. On a phone this is never reached, but
    /// it stops an iPad from setting a chapter 900 points wide.
    static let readingWidth: CGFloat = 620

    /// The custom tab bar's own height, before the home indicator's inset.
    static let tabBarHeight: CGFloat = 58

    /// Vertical rhythm between stacked blocks.
    static let gap: CGFloat = 16
    static let gapLarge: CGFloat = 28
    static let gapSection: CGFloat = 44

    /// Controls. A gold button is 56 tall, an outline 54, a veil 50 — the
    /// hierarchy is in the height as much as in the fill.
    static let buttonHeight: CGFloat = 56
    static let buttonHeightOutline: CGFloat = 54
    static let buttonHeightVeil: CGFloat = 50
    static let fieldHeight: CGFloat = 54

    /// A hairline is one device pixel, not one point — at 3× a 1pt rule is
    /// three times heavier than the CSS it came from.
    ///
    /// `@MainActor` because the screen's scale is main-actor state. Every use
    /// of it is inside a `View.body`, which is already on the main actor, so
    /// this costs nothing at the call sites. A screen that needs the scale
    /// somewhere else should read `@Environment(\.displayScale)` rather than
    /// hop actors for a number.
    @MainActor static var hairline: CGFloat { 1.0 / UIScreen.main.scale }
}

/// The motion vocabulary. Four durations and three curves, so that a sheet and
/// a tap never disagree about how fast the product moves.
///
/// "The sky moves, the UI doesn't": these are for *controls*, and they are all
/// short. The ambient motion in `Sky/` is on its own, much slower clock and does
/// not use any of them.
enum AlmaMotion {

    /// A tap acknowledging itself.
    static let tap = Animation.timingCurve(0.2, 0, 0.4, 1, duration: 0.12)

    /// A control changing state.
    static let ui = Animation.timingCurve(0.22, 1, 0.36, 1, duration: 0.24)

    /// A sheet or a cover arriving.
    static let sheet = Animation.timingCurve(0.16, 1, 0.3, 1, duration: 0.38)

    /// A chapter unblurring after a purchase. Deliberately the slowest thing
    /// in the app that is not the sky — it is the moment the product delivers.
    static let reveal = Animation.timingCurve(0.22, 1, 0.36, 1, duration: 0.62)

    /// One page giving way to the next — a chapter pulled into, a tab swiped
    /// to.
    ///
    /// **Faster than `sheet` and slower than `ui`, and that is the whole
    /// brief.** A page change that takes as long as a sheet feels like the app
    /// thinking; one as quick as a button feels like a glitch. 0.30 with a
    /// strong ease-out is the range every reader already knows from the
    /// messaging apps this gesture was borrowed from: the new page is most of
    /// the way there in the first third of the time, and the rest is it
    /// settling.
    static let page = Animation.timingCurve(0.2, 0.9, 0.25, 1, duration: 0.30)
}

extension View {

    /// The standard side margin. A screen writes `.almaPadding()` rather than
    /// `.padding(.horizontal, 22)`, so the margin can be changed in one place.
    func almaPadding() -> some View {
        self.padding(.horizontal, AlmaMetrics.pad)
    }

    /// Constrain a reading to its measure and centre it. A no-op on a phone.
    func almaReadingWidth() -> some View {
        self.frame(maxWidth: AlmaMetrics.readingWidth, alignment: .leading)
    }
}
