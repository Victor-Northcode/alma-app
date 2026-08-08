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
/// *button* is replaced. `NavigationStack` keeps the interactive swipe-back
/// gesture when a custom back button replaces the default one, and hiding the
/// bar outright is what takes that gesture away — a screen you can only leave by
/// finding a small target in the corner is a worse screen than an ugly one.
private struct AlmaScreenChrome: ViewModifier {

    @Environment(\.dismiss) private var dismiss

    func body(content: Content) -> some View {
        content
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
