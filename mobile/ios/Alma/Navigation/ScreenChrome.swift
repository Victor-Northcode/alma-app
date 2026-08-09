import SwiftUI

/// The navigation chrome for a pushed screen, decided once.
///
/// **Why this exists at all.** A `NavigationStack` supplies a back button of its
/// own, and on current iOS that is a white chevron inside a translucent glass
/// capsule. It is the single most recognisable control on the platform, it is a
/// box, and it is not gold — three of the four rules in the brand book, broken
/// by a control nobody wrote. Left alone, each screen would restyle it
/// differently, which is exactly the divergence a skeleton exists to prevent.
///
/// **What it does instead**, following `ScreenBar` in the web app: hides the
/// system button, draws an arrow in gold with no capsule behind it, and leaves
/// the bar itself transparent so the sky runs unbroken to the top of the screen.
///
/// **What it deliberately does not do**: hide the navigation bar. Only the
/// *button* is replaced.
///
/// This paragraph used to claim `NavigationStack` keeps the interactive
/// swipe-back when a custom back button replaces the default one. It does not,
/// and the owner found that out by trying to use his own app. The gesture below
/// is what gives it back.
private struct AlmaScreenChrome: ViewModifier {

    @Environment(\.dismiss) private var dismiss

    /// How far the screen has been dragged out of the way, in points.
    @State private var dragged: CGFloat = 0

    /// Only a drag that *starts* at the very edge is a back gesture. 24 points
    /// is the width UIKit uses for its own, and it is what keeps this off the
    /// conversation's scroll view and off the natal wheel.
    private static let edge: CGFloat = 24
    /// Past this, letting go leaves.
    private static let commit: CGFloat = 90

    func body(content: Content) -> some View {
        content
            // **The back swipe, written rather than restored.**
            //
            // The comment on this file used to say `NavigationStack` keeps the
            // interactive pop when a custom back button replaces the default
            // one, and the owner reported it did not work. It does not: hiding
            // the system item is what disables UIKit's recogniser, and on this
            // OS handing `interactivePopGestureRecognizer` its delegate back —
            // the standard fix, tried first and tested on the simulator —
            // changes nothing, because SwiftUI's stack is no longer that
            // recogniser's owner.
            //
            // So the gesture is ours. It follows the finger, which is the part
            // that makes it feel like the platform's rather than like a
            // shortcut: the page moves as you pull, and past 90 points it
            // leaves. Under that it springs back, and nothing has happened.
            .offset(x: dragged)
            .animation(AlmaMotion.page, value: dragged)
            .simultaneousGesture(
                DragGesture(minimumDistance: 12, coordinateSpace: .global)
                    .onChanged { value in
                        guard value.startLocation.x <= Self.edge else { return }
                        guard value.translation.width > 0 else { return }
                        // Damped past the commit point: the page keeps moving
                        // so the gesture never feels stuck, but slowly enough
                        // that the threshold is felt rather than guessed.
                        let raw = value.translation.width
                        dragged = raw <= Self.commit ? raw : Self.commit + (raw - Self.commit) * 0.35
                    }
                    .onEnded { value in
                        guard value.startLocation.x <= Self.edge else { return }
                        let far = value.translation.width > Self.commit
                        let fast = value.predictedEndTranslation.width > 220
                        if far || fast {
                            dismiss()
                        }
                        dragged = 0
                    }
            )
            // Inline, because a large title is a slab of UIKit type that
            // appears and disappears as you scroll — and every screen already
            // sets its own title in the serif, on the night, where the design
            // puts it.
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(.hidden, for: .navigationBar)
            .navigationBarBackButtonHidden(true)
            .toolbar {
                // Two spellings of the same item. From iOS 26 the toolbar draws
                // a glass capsule behind every item unless it is told not to,
                // and `sharedBackgroundVisibility` is the only thing that turns
                // it off — `.buttonStyle(.plain)` shrinks the capsule but does
                // not remove it. Tinting the arrow gold inside a grey pill is
                // not the design; the pill has to go.
                if #available(iOS 26.0, *) {
                    ToolbarItem(placement: .topBarLeading) { backButton }
                        .sharedBackgroundVisibility(.hidden)
                } else {
                    ToolbarItem(placement: .topBarLeading) { backButton }
                }
            }
    }

    private var backButton: some View {
        Button {
            dismiss()
        } label: {
            // The arrow the web app uses, set in the serif as type rather than
            // drawn as an icon — the same decision as the astrological glyphs.
            Text(verbatim: "←")
                .font(AlmaFonts.display(22, relativeTo: .title3))
                .foregroundStyle(Color.almaGoldBright)
                // 44×44 is the floor for a touch target, and a bare arrow is
                // about 16 points wide.
                .frame(width: 44, height: 44, alignment: .leading)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(Text(L10n.cabinetBack))
    }
}

extension View {
    /// Applied by the shell to every pushed destination. A screen does not call
    /// this itself, and does not need to know it happened.
    func almaScreenChrome() -> some View {
        modifier(AlmaScreenChrome())
    }
}

// The UIKit route out of this is gone, and it is worth saying why rather than
// leaving the next reader to rediscover it. `UINavigationController` conforming
// to `UIGestureRecognizerDelegate` and taking `interactivePopGestureRecognizer`
// back is the answer everywhere on the internet and the answer this file tried
// first. It was swept from the window on every screen's appear — so the timing
// excuse does not apply — and the swipe still did nothing, because SwiftUI's
// `NavigationStack` on this OS does not pop through that recogniser. The
// gesture in `AlmaScreenChrome` is what actually works, and it is ours.
