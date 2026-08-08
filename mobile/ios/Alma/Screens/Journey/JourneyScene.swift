import SwiftUI

/// The shape every scene of the journey has: living celestial art in the
/// middle, the question under it, the controls at the bottom.
///
/// It is `ScreenScaffold`'s opposite number and deliberately not the same type.
/// The cabinet is a scrolling column with a title at the top; a journey scene
/// is a *stage* — the art is the largest thing on it, the controls are pinned
/// to the bottom edge where a thumb is, and there is nothing in between. Trying
/// to serve both from one view would have meant a scaffold with a mode flag,
/// which is how a layout ends up half-obeying two designs.
///
/// **Why it still scrolls.** On the shortest phone we support, with the
/// keyboard up, the art plus the question plus five controls do not fit. The
/// web app's answer is `overflow-y: auto` on the overlay, and this is the same
/// answer: a scroll view whose content is given a minimum height equal to the
/// screen, so on a normal phone nothing scrolls and `Spacer` pins the controls
/// to the bottom, and on a short one the whole scene moves instead of the
/// button sliding off the edge.
struct JourneyScene<Art: View, Controls: View>: View {

    /// How tall the art is allowed to be. The web fixes this per scene, because
    /// the constellation wants more room than the star on the offer does.
    var artHeight: CGFloat = 308
    var title: LocalizedStringResource?
    var sub: LocalizedStringResource?
    @ViewBuilder var art: Art
    @ViewBuilder var controls: Controls

    var body: some View {
        GeometryReader { geometry in
            ScrollView {
                // **Centred, and pulled down to meet the controls.**
                //
                // Every question used to sit hard against the left margin with
                // the art above it and a band of empty night between it and the
                // buttons — on a tall phone, a third of the screen of nothing.
                // The owner's note was that the questions want centring and the
                // gap wants closing, and the two are one fix: a stage this
                // sparse has one subject, and a subject belongs in the middle
                // of the frame rather than in its top-left corner.
                //
                // `minHeight` with `.center` is what closes the gap without
                // pinning: on a normal phone the block sits centred in what the
                // controls leave, and on a short one — or with the keyboard up
                // — the content is taller than the space and simply scrolls,
                // which is the behaviour this scroll view was written for.
                VStack(alignment: .center, spacing: 0) {
                    art
                        .frame(maxWidth: .infinity)
                        // 40% of the screen, exactly as the CSS caps it. Fixed
                        // art on a short phone is art that pushes the price off
                        // the bottom, and a control nobody can see is a control
                        // nobody uses.
                        .frame(height: min(artHeight, geometry.size.height * 0.4))

                    if let title {
                        Text(title)
                            .font(AlmaFonts.display(30, relativeTo: .title))
                            .foregroundStyle(Color.almaInkLight)
                            .lineSpacing(
                                AlmaFonts.leading(30, ratio: 1.08, family: .display, relativeTo: .title))
                            .multilineTextAlignment(.center)
                            .fixedSize(horizontal: false, vertical: true)
                            .padding(.top, 4)
                    }

                    if let sub {
                        Text(sub)
                            .font(AlmaFonts.ui(15))
                            .lineSpacing(5)
                            .foregroundStyle(Color.almaMuted2)
                            .multilineTextAlignment(.center)
                            .fixedSize(horizontal: false, vertical: true)
                            .padding(.top, 12)
                    }
                }
                .frame(maxWidth: .infinity)
                .almaPadding()
                .padding(.bottom, 24)
                .frame(minHeight: geometry.size.height * 0.82, alignment: .center)
            }
            .scrollIndicators(.hidden)
            .scrollContentBackground(.hidden)
            .scrollDismissesKeyboard(.interactively)
            // **The controls are a safe-area inset, not the last row of the
            // scroll view**, and that is what fixes three separate faults at
            // once.
            //
            // They used to sit inside the scroll content under a `Spacer` and a
            // bare `.padding(.bottom, 28)`, which put the primary button in a
            // different place on three consecutive steps of one flow — measured
            // on an 874-point screen with a 34-point home indicator: 811 on the
            // place step, 840 on the date step, 869 on the portrait. The last of
            // those is 29 points *inside* the indicator, where the system draws
            // its own bar over the button and the lower third of the tap target
            // fights the edge-swipe gesture. In French the intent step's skip
            // link landed underneath the indicator entirely.
            //
            // An inset also rises with the keyboard instead of being covered by
            // it. On the place step — the last screen before the ceremony and
            // the highest-intent moment in the funnel — the keyboard used to cut
            // "Build my sky" in half and then hide it completely once the
            // suggestion list opened.
            .safeAreaInset(edge: .bottom, spacing: 0) {
                VStack(spacing: 11) {
                    controls
                }
                .almaPadding()
                .padding(.top, 16)
                .padding(.bottom, 12)
            }
        }
    }
}

/// A scene that is a document rather than a stage — the portrait and the
/// handoff, both of which are read top to bottom and both of which are longer
/// than the screen.
///
/// It is a second view rather than a flag on the first because the two have
/// opposite instincts about vertical space: the stage pushes its controls to
/// the bottom edge and the document lets them follow the last line. The web app
/// has exactly this split (`journey-controls` versus
/// `journey-controls-static`) and it is the one place a shared component would
/// have been a false economy.
struct JourneyDocument<Content: View, Controls: View>: View {

    @ViewBuilder var content: Content
    @ViewBuilder var controls: Controls

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                content

                // Still in the flow, unlike the stage's: a document's controls
                // follow its last line rather than floating over it, which is
                // the `journey-controls-static` half of the web app's split.
                // What changed is only the bottom padding — `.safeAreaPadding`
                // adds the home indicator's inset to the 28, where a plain
                // `.padding` was measured putting the portrait's gold button 29
                // points inside it.
                VStack(spacing: 11) {
                    controls
                }
                .padding(.top, 24)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .almaPadding()
            .padding(.bottom, 28)
        }
        .scrollIndicators(.hidden)
        .scrollContentBackground(.hidden)
        .safeAreaPadding(.bottom, 12)
    }
}
