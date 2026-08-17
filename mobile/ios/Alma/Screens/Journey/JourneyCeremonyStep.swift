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

    /// The eight have played out. Kept apart from leaving, because leaving also
    /// waits on the save — see `leaveIfBothFinished`.
    @State private var played = false

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
        // Two parties can be the last to finish and neither knows which it is:
        // the beats are a fixed nine and a half seconds, the save is not, and a
        // scene that walked out before the server answered would land somebody
        // in an empty cabinet. Whichever arrives second calls this and leaves.
        .onChange(of: played) { _, _ in leaveIfBothFinished() }
        .onChange(of: journey.working) { _, _ in leaveIfBothFinished() }
        .onChange(of: journey.fork == nil) { _, _ in leaveIfBothFinished() }
    }

    /// Already on the way out. Two parties race to call the line below and both
    /// may win in the same runloop turn; a second `onNext` would push the tail
    /// of the journey twice.
    @State private var leaving = false

    private func leaveIfBothFinished() {
        guard played, !journey.working, journey.fork == nil, !leaving else { return }
        leaving = true
        AlmaHaptics.arrival()
        onNext()
    }

    /// The eight beats, then a held breath, then the portrait.
    ///
    /// 1.15 seconds each and 1.4 on the last is the web app's timing, which
    /// totals 9.45 seconds. It is a `for` loop rather than a chain of timers
    /// because the whole sequence is cancelled at once when the view goes away
    /// — which is what happens the moment somebody taps "skip the ceremony".
    private func play() async {
        for next in 2...Self.beats {
            // **The fork pauses the beats; it does not restart them.** `beat`
            // survives the wait, so answering the question resumes the ceremony
            // where it stood rather than replaying nine seconds somebody has
            // already watched.
            await waitOutTheFork()
            guard (try? await Task.sleep(for: .milliseconds(1150))) != nil else { return }
            withAnimation(AlmaMotion.ui) { beat = next }
            // One soft tick per system lighting — the sky arriving in the
            // hand, and the only place in the product that touches it eight
            // times, because eight things are genuinely happening.
            AlmaHaptics.tick()
        }
        await waitOutTheFork()
        guard (try? await Task.sleep(for: .milliseconds(1400))) != nil else { return }
        played = true
        leaveIfBothFinished()
    }

    /// Stand still while a question is on screen.
    ///
    /// Polled rather than awaited on a continuation because there is exactly one
    /// waiter and the wait is measured in the seconds a person takes to read two
    /// options — a quarter-second granularity is invisible, and a continuation
    /// stored in the model would be one more thing to leak if the cover closes.
    private func waitOutTheFork() async {
        while journey.fork != nil {
            guard (try? await Task.sleep(for: .milliseconds(250))) != nil else { return }
        }
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
