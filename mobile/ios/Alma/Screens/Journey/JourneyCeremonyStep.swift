import SwiftUI

/// VI · the ceremony. Eight beats, about nine seconds, always skippable.
///
/// **It is not a loading screen wearing a costume, and it is not theatre
/// either.** The birth is saved under it and the three free systems and the
/// free chapter are fetched under it, which is exactly what the nine seconds
/// are for: a round trip needs cover, and the alternative is a spinner where
/// the reward should be. The eight lines are true — they name the eight systems
/// in the order they exist — and each one is on screen for about as long as it
/// takes to read.
///
/// **A failure is deliberately not surfaced here.** The person is watching an
/// animation, not a form, and there is nothing they could do about it mid-beat.
/// The portrait is where a missing chart becomes visible and where it says so,
/// with the one retry that could work.
struct StepCeremony: View {

    let journey: JourneyModel
    let onNext: () -> Void

    @Environment(AlmaSessionModel.self) private var session

    /// Which beat is showing, 1…8.
    @State private var beat: Int = 1

    private static let beats = 8

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            CeremonyArt()
                .frame(maxWidth: .infinity)
                .frame(height: 360)

            VStack(alignment: .leading, spacing: 14) {
                Text(JourneyL10n.ceremonyLabel(beat))
                    .almaOverline()

                Text(JourneyL10n.ceremonyLine(beat))
                    .font(AlmaFonts.display(22, relativeTo: .title3).italic())
                    .lineSpacing(7)
                    .foregroundStyle(Color.almaInkLight)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            // The lines are different lengths and the drawing above them must
            // not jump when one of them wraps to three. Reserving the height of
            // the longest is cheaper than measuring, and steadier than either.
            .frame(minHeight: 116, alignment: .top)
            .accessibilityElement(children: .combine)
            // Announced as it changes, because somebody using VoiceOver is
            // otherwise sitting in nine seconds of silence.
            .accessibilityAddTraits(.updatesFrequently)

            Spacer(minLength: 20)

            progressBar
                .padding(.bottom, 16)

            // The skip is gone. It jumped past the one screen where the eight
            // systems are actually computed and straight to the portrait,
            // which is the payoff — and a payoff nobody waited for reads as a
            // template rather than as their own chart.
        }
        .almaPadding()
        .padding(.bottom, 28)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .task {
            // Two independent jobs, and only one of them is this screen's.
            //
            // The save is started and let go: it belongs to `JourneyModel` and
            // must survive this scene, because this scene deletes itself after
            // nine seconds and a cancelled `.task` cancels the request under it.
            // The beats are a fixed nine seconds and the network is not, so a
            // slow save must not hold the animation and a fast one must not
            // make the ceremony pointless.
            journey.begin(with: session)
            await play()
        }
    }

    /// The eight beats, then a held breath, then the portrait.
    ///
    /// 1.15 seconds each and 1.4 on the last is the web app's timing, which
    /// totals 9.45 seconds. It is a `for` loop rather than a chain of timers
    /// because the whole sequence is cancelled at once when the view goes away
    /// — which is what happens the moment somebody taps "skip the ceremony".
    private func play() async {
        for next in 2...Self.beats {
            guard (try? await Task.sleep(for: .milliseconds(1150))) != nil else { return }
            withAnimation(AlmaMotion.ui) { beat = next }
            // One soft tick per system lighting — the sky arriving in the
            // hand, and the only place in the product that touches it eight
            // times, because eight things are genuinely happening.
            AlmaHaptics.tick()
        }
        guard (try? await Task.sleep(for: .milliseconds(1400))) != nil else { return }
        AlmaHaptics.arrival()
        onNext()
    }

    private var progressBar: some View {
        HStack(spacing: 5) {
            ForEach(1...Self.beats, id: \.self) { index in
                Capsule()
                    .fill(index <= beat ? Color.almaGold : Color.almaBody.opacity(0.16))
                    .frame(height: 2)
            }
        }
        .animation(AlmaMotion.ui, value: beat)
        .accessibilityElement()
        .accessibilityLabel(Text(JourneyL10n.step(beat, of: Self.beats)))
    }
}
