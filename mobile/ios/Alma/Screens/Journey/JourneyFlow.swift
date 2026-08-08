import SwiftUI

/// The journey — the modal the whole funnel lives in.
///
/// Nine scenes in a fixed order: what's loudest → what to call you → when →
/// what time → where → the ceremony → the portrait → the offer → the handoff.
/// The order is `JourneyOverlay.tsx`'s, with one difference that follows from
/// the platform rather than from taste: the web app captures the birth date on
/// the landing page and skips its own date step when it already has one. There
/// is no landing page in an app, so the date is always asked and the sequence
/// is fixed — which is why the counter in the header can be derived from the
/// enum instead of written down and left to go stale.
///
/// **A cover, not a navigation stack.** The ceremony owns the screen, and a
/// back button that steps into the middle of it is a back button into a
/// half-computed chart. The scenes advance one way; the ✕ is the only way out
/// and it keeps everything typed so far.
///
/// **The web's authorisation step is not here, and its absence is a decision.**
/// On the web the guest account lives in `localStorage`, so an account is what
/// makes a chart survive the browser being closed, and the journey has to ask
/// for one before it lets go. Here the token is in the keychain and the account
/// is real from the first request — the chart already survives — so a hard
/// sign-in gate between somebody and their own portrait would be asking for
/// something in exchange for nothing. Sign in with Apple attaches an identity
/// from the settings screen, which is where it belongs and where it actually
/// signs somebody in.
struct JourneyFlow: View {

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router

    /// Not `@State`: the journey survives the cover being closed. See
    /// `JourneyModel.inFlight`.
    private let journey = JourneyModel.inFlight

    var body: some View {
        VStack(spacing: 0) {
            header

            scene
                .id(journey.step)
                .transition(.opacity)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        // The web caps the scene at 520 points and centres it. Irrelevant on a
        // phone and the difference between a designed screen and a stretched
        // one on an iPad.
        .frame(maxWidth: 520)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .nightSky(.ceremony, seed: 0x4A4F_5552)
        .accessibilityLabel(Text(JourneyL10n.dialogLabel))
        .task {
            await journey.announceStart(to: session.client)
        }
    }

    // MARK: — the header

    private var header: some View {
        HStack {
            // **Back on every screen, and no way out.**
            //
            // The header held one control and it was a cross that abandoned the
            // journey. Two things were wrong with that. Somebody who mistypes a
            // date has to be able to go back one screen — the sequence is eight
            // screens long and the only correction available was to leave and
            // start again. And leaving at all is now the thing that must not
            // happen: every screen after this one is a chart, and there is no
            // chart without these four answers. An app that lets you in with
            // nothing to show you has nothing to show you.
            //
            // So the cross is gone and this is a back arrow, hidden on the
            // first screen because there is nowhere behind it.
            if journey.step.previous != nil {
                Button(action: retreat) {
                    Image(systemName: "arrow.left")
                        .font(.system(size: 16, weight: .regular))
                        .foregroundStyle(Color.almaMuted)
                        .frame(width: 44, height: 44)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(Text(JourneyL10n.back))
            } else {
                Color.clear.frame(width: 44, height: 44)
            }

            HStack(spacing: 4) {
                Text(verbatim: journey.step.numeral)
                Text(verbatim: "/ \(JourneyStep.last.numeral)")
                    .foregroundStyle(Color.almaMuted3)
            }
            .font(AlmaFonts.display(13, relativeTo: .footnote))
            .tracking(2.6)
            .foregroundStyle(Color.almaGold.opacity(0.8))
            .accessibilityElement()
            // "VII" is read out as three letters, which tells somebody who
            // cannot see the screen nothing about how far through they are.
            .accessibilityLabel(
                Text(JourneyL10n.step(journey.step.rawValue + 1, of: JourneyStep.allCases.count)))

            Spacer()

            // Balances the back arrow so the numeral stays where it is when
            // the arrow is not there.
            Color.clear.frame(width: 44, height: 44)
        }
        .almaPadding()
        .padding(.top, 12)
        .padding(.bottom, 4)
    }

    // MARK: — the eight

    @ViewBuilder
    private var scene: some View {
        switch journey.step {
        case .name:
            StepName(journey: journey, onNext: advance)
        case .date:
            StepDate(journey: journey, onNext: advance)
        case .time:
            StepTime(journey: journey, onNext: advance)
        case .place:
            StepPlace(journey: journey, onNext: advance)
        case .ceremony:
            StepCeremony(journey: journey, onNext: advance)
        case .portrait:
            StepPortrait(journey: journey, onNext: advance, onOpenChapter: openChapter)
        case .offer:
            StepOffer(journey: journey, onBuy: openOffer, onSkip: advance)
        case .handoff:
            StepHandoff(onFinish: finish)
        }
    }

    // MARK: — moving

    /// One screen back, keeping everything typed. `JourneyModel.inFlight` is
    /// not `@State`, so nothing is lost by moving in either direction.
    private func retreat() {
        guard let previous = journey.step.previous else { return }
        withAnimation(.easeInOut(duration: 0.28)) { journey.step = previous }
    }

    private func advance() {
        guard let next = journey.step.next else {
            finish()
            return
        }
        withAnimation(AlmaMotion.sheet) { journey.step = next }
    }

    /// The ✕. Everything typed so far stays typed.
    private func leave() {
        router.closeJourney()
    }

    /// The handoff's own button, and the end of a completed journey. The
    /// cabinet opens on Today, which is what the button says it will do.
    private func finish() {
        router.tab = .today
        router.closeJourney()
        journey.reset()
    }

    /// Take the offer.
    ///
    /// The ladder is pushed onto the Systems stack rather than presented here,
    /// because the offer screen is the app's one purchase surface: StoreKit's
    /// localised price, the sheet, the restore path and the server-side
    /// verification all live there and must not exist twice. Pushing before
    /// dismissing means the screen is already behind the cover as it goes,
    /// rather than appearing a beat later on an empty tab.
    private func openOffer(_ system: SystemSlug) {
        router.push(.offer(system: system), on: .systems)
        router.closeJourney()
        journey.reset()
    }

    /// Open the free chapter. The wait while it is written is long and has its
    /// own honest screen; that screen is not this one.
    private func openChapter(_ system: SystemSlug, _ chapter: String) {
        router.push(.chapter(system: system, chapter: chapter), on: .systems)
        router.closeJourney()
        journey.reset()
    }
}

#Preview {
    JourneyFlow()
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}
