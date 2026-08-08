import SwiftUI

/// How much of the bottom the cabinet's bar is standing on, for the screens
/// standing under it.
///
/// **Why this is not `safeAreaInset` alone.** `RootView` applies the bar with
/// `.safeAreaInset(edge: .bottom)` on the `ZStack` of tab stacks, and the
/// comment there says every scroll view gets the inset for free. It does not:
/// each tab is a `NavigationStack`, and a navigation container takes its safe
/// area from the window rather than from the parent that wrapped it. So the
/// bar was reserved by the shell and ignored by every screen inside it, and
/// the last line of each one sat under the bar with nothing left to scroll —
/// the owner found it on the fine print in Settings, which stopped at *"For
/// self-knowledge only. Not medical, psychological, legal or"*.
///
/// An environment value rather than a constant inside `ScreenScaffold`,
/// because the scaffold is also the journey's (`JourneyScene`), and the
/// journey is a full-screen cover with no bar under it. Zero by default:
/// a screen is only pushed down by a bar that is actually there.
private struct CabinetBarHeightKey: EnvironmentKey {
    static let defaultValue: CGFloat = 0
}

extension EnvironmentValues {
    var cabinetBarHeight: CGFloat {
        get { self[CabinetBarHeightKey.self] }
        set { self[CabinetBarHeightKey.self] = newValue }
    }
}

/// The shape every screen in the cabinet has, so that none of them has to
/// rediscover it.
///
/// Three things it settles, all of which are easy to get subtly wrong per screen
/// and impossible to notice until they are wrong on four screens differently:
///
/// * **the scroll view and the side margin** — one `pad`, applied once;
/// * **the top of the page** — a gold eyebrow and a serif title, in the rhythm
///   the web app uses, with the title never in a navigation bar (a large-title
///   `UINavigationBar` on night is a grey slab that appears when you scroll);
/// * **the bottom** — enough room that the last line clears the tab bar, since
///   the bar is a safe-area inset and a screen that ignores safe areas would put
///   its final paragraph underneath it.
///
/// A screen that needs something other than a scrolling column — the map, the
/// conversation — should not use this. **It must then call `.nightSky()` on its
/// own root**, because a navigation container fills itself with an opaque
/// background: a screen that draws no sky is a screen that is flat black, and
/// there is nowhere further up the tree to put one. See the note in `RootView`.
struct ScreenScaffold<Content: View>: View {

    /// The small gold line above the title. Optional: a chapter has one, a
    /// conversation does not.
    var eyebrow: LocalizedStringResource?
    var title: LocalizedStringResource?
    /// What the sky does here. A reading turns it down.
    var mood: NightSky.Mood = .cabinet
    /// Which sky this screen gets. Different seeds on two screens is what makes
    /// moving between them visibly moving; the same seed on the same screen is
    /// what stops the stars reshuffling when the keyboard appears.
    var seed: UInt64 = 0x414C_4D41
    @ViewBuilder var content: Content

    @Environment(\.cabinetBarHeight) private var barHeight

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AlmaMetrics.gap) {
                if let eyebrow {
                    SectionLabel(text: eyebrow)
                        .padding(.top, 8)
                }
                if let title {
                    Text(title)
                        .almaDisplayL()
                        .padding(.bottom, 4)
                }
                content
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .almaPadding()
            .padding(.top, 12)
            // Half a section over the bar, not a whole one: the owner's
            // screenshot showed a band of empty night taller than the tab bar
            // under every screen's last line.
            .padding(.bottom, AlmaMetrics.gapLarge / 2 + barHeight)
        }
        .scrollIndicators(.hidden)
        // Off, so the sky below is not covered by the scroll view's own fill.
        .scrollContentBackground(.hidden)
        .nightSky(mood, seed: seed)
    }
}

// `NotBuiltYet` used to live here, and it is gone.
//
// It was the skeleton's placeholder — a star, a name, and the sentence "This
// screen has not been built yet." — and the contract was that it would be
// deleted with the last screen that referenced it. Seven screens still did:
// the whole Alma tab, one of the four in the bar, plus sign-in, one saved
// conversation, the people list, add-a-person, and all five legal documents.
// Guideline 2.1 App Completeness is the most mechanical rejection there is, and
// a tab bar item that says the screen does not exist is the clearest possible
// instance of it; the legal placeholders were a second one, under 3.1.2, since
// the paywall linked to them at the point of purchase.
//
// Nothing references it now. It is left as a comment rather than as an empty
// file so that the next person to reach for a placeholder reads why the last
// ones cost a review cycle.
