import SwiftUI

/// The first two and a half seconds: a star chart drawing itself, then folding
/// into the mark.
///
/// **What was here before.** `UILaunchScreen` names a colour, so iOS drew a
/// flat night rectangle and SwiftUI replaced it in one frame with a finished
/// screen. Nothing arrived; something was simply there instead of something
/// else. Against a backend on the same machine that state lasts a few dozen
/// milliseconds, which makes it worse rather than better — the app appears to
/// flicker. The first fix faded three things up over a second, and the owner's
/// verdict was the right one: not enough happening, and none of it about stars.
///
/// **What this is.** One clock, five overlapping movements, 2.8 seconds:
///
/// | from | to | what |
/// |---|---|---|
/// | 0.00 | 0.90 | the field of stars fades up and the chart settles in from 4% larger |
/// | 0.20 | 1.55 | six nodes light one after another, along the chart |
/// | 0.30 | 1.70 | the lines between them draw themselves, `trim` 0 → 1 |
/// | 1.50 | 2.30 | one comet crosses, and the chart contracts and dims |
/// | 1.70 | 2.55 | the mark blooms where the brightest node was, then the wordmark |
///
/// It overlaps on purpose. Five things each starting when the last has finished
/// is a slideshow; five whose curves cross is a single movement, and that
/// difference is most of what "expensive" means in motion.
///
/// **The mark does not spin.** `AlmaStar`'s own documentation forbids it —
/// *never in a circle, never rotated, never used as a loading indicator* — and
/// a rotating four-pointed sparkle is the exact cliché the mark was drawn to
/// avoid. It blooms in place, out of the chart it belongs to.
///
/// **Why it may take this long.** A launch state that appears for 40ms and
/// vanishes is a flash, which reads as a fault, and this is the one screen
/// every session begins with. When the session is genuinely slower the screen
/// simply stays, so the floor costs nothing on the path it was written for.
struct AlmaLaunch: View {

    /// Called once the arrival has finished *and* the caller says the app is
    /// ready. Both, not either: leaving early is the jump cut this replaces.
    var ready: Bool
    var done: () -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// The whole arrival, and the floor on how long this screen is shown.
    /// Grew from 2.8 with the second draft: the owner's verdict on the first
    /// was "слабенькая", and the fix was not speed but density — a zodiac
    /// nine nodes instead of six, a second comet,
    /// and motes rising into the bloom all need the extra half-second.
    private static let runtime: Double = 3.4

    @State private var start = Date.timeIntervalSinceReferenceDate
    @State private var dwelt = false

    var body: some View {
        ZStack {
            Color.almaNight.ignoresSafeArea()

            // `NightSky` as a sibling rather than through `.nightSky()`: the
            // modifier puts the sky *behind* its content, and here the sky
            // arriving is the content. A background cannot be seen to fade.
            //
            // `.ceremony` rather than `.cabinet`, and not for brightness: the
            // cabinet mood draws its own comet, and two crossing at the same
            // moment reads as weather rather than as a sky. This screen draws
            // the only one.
            NightSky(mood: .ceremony, seed: 0x414C_4D41)
                .ignoresSafeArea()
                .opacity(reduceMotion ? 1 : eased(0, 0.9))

            if reduceMotion {
                // The same picture, finished, with nothing moving. Removing the
                // screen entirely would not be an accommodation — it would be
                // the flash this exists to prevent.
                chart(at: Self.runtime)
            } else {
                TimelineView(.animation) { timeline in
                    chart(at: timeline.date.timeIntervalSinceReferenceDate - start)
                }
            }
        }
        .task {
            try? await Task.sleep(for: .milliseconds(Int(Self.runtime * 1000)))
            dwelt = true
        }
        // **Both edges, and neither of them read from inside the task.**
        //
        // Deciding inside `.task` after the sleep hung the app. A `Task`
        // closure captures the view value it was created with, and this view is
        // created while `ready` is false; the session finished a tenth of a
        // second later, so `onChange` fired while `dwelt` was still false, and
        // the sleep then woke holding a `ready` that had been false when it was
        // captured and was never updated. Two halves each waiting for the
        // other, and a launch screen that never left — measured, still there
        // after four seconds against a local backend.
        //
        // `onChange` bodies run against a freshly-made view, so both of these
        // see both current values. Whichever lands second is the one that goes.
        .onChange(of: ready) { _, _ in handOver() }
        .onChange(of: dwelt) { _, _ in handOver() }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(L10n.stateLoading))
    }

    private func handOver() {
        guard ready, dwelt else { return }
        done()
    }

    // MARK: — the drawing

    @ViewBuilder
    private func chart(at t: Double) -> some View {
        // How far the chart has folded away, and how far the mark has come up.
        // Derived from one clock so the two can never drift apart and leave a
        // frame holding both or neither.
        let fold = eased(1.90, 2.65, at: t)
        let bloom = eased(2.05, 2.85, at: t)
        let word = eased(2.35, 3.05, at: t)

        ZStack {
            StarChart(
                lines: eased(0.35, 1.95, at: t),
                nodes: eased(0.25, 1.80, at: t),
                comet: eased(1.20, 2.20, at: t),
                cometTwo: eased(1.65, 2.60, at: t),
                time: t
            )
            .frame(width: 300, height: 300)
            // Almost all the way out, not most of the way. At 0.88 the chart
            // was still legible behind the mark and the two read as clutter
            // rather than as one resolving into the other.
            .opacity(1 - fold * 0.97)
            // Contracting rather than only fading: the chart is being drawn
            // into the mark, and a shape that merely dims has been abandoned
            // rather than resolved.
            .scaleEffect(1.04 - eased(0, 0.9, at: t) * 0.04 - fold * 0.10)

            VStack(spacing: 24) {
                AlmaStar()
                    .frame(width: 46, height: 46)
                    .opacity(bloom)
                    .scaleEffect(0.72 + bloom * 0.28)
                    .background {
                        // Six motes rising into the bloom — sparks drawn up
                        // by the mark as it lights, gone once it has.
                        ZStack {
                            ForEach(0..<6, id: \.self) { i in
                                let phase = min(max(bloom * 1.4 - Double(i) * 0.12, 0), 1)
                                Circle()
                                    .fill(Color.almaGoldBright.opacity(0.7 * phase * (1 - phase) * 4 * 0.35))
                                    .frame(width: 2.5, height: 2.5)
                                    .offset(
                                        x: CGFloat([-26, 18, -12, 30, -34, 8][i]),
                                        y: CGFloat(34 - phase * 74)
                                    )
                            }
                        }
                    }

                Text(verbatim: "ALMA")
                    .font(AlmaFonts.ui(15))
                    // The letters settle: tracking closes from scattered to
                    // set as the word fades in — type arriving, not appearing.
                    .tracking(7 + (1 - word) * 9)
                    .foregroundStyle(Color.almaParchment.opacity(0.9))
                    .opacity(word)
                    .offset(y: (1 - word) * 7)

                // **The part that says "loading", and the part I dropped.**
                //
                // The first version of this screen ended on `AlmaPresence` —
                // Alma's own light, breathing — and the rewrite replaced it
                // with a chart and forgot to put it back. The owner's report
                // was that there is no loading, twice, and both times it was
                // this: a sequence that plays and stops is a title card, and a
                // title card in front of a person who is waiting does not tell
                // them anything is happening.
                //
                // `AlmaPresence` is the one loop the brand book allows, for
                // exactly this reason — stillness there reads as a hang. Under
                // it, a hairline that fills over the run: the quietest
                // possible progress, in one gold, no box.
                VStack(spacing: 16) {
                    AlmaPresence(size: 18, ring: false)
                        .opacity(word * 0.9)

                    Capsule()
                        .fill(Color.almaGold.opacity(0.16))
                        .frame(width: 84, height: 1)
                        .overlay(alignment: .leading) {
                            Capsule()
                                .fill(Color.almaGoldBright.opacity(0.75))
                                .frame(width: 84 * min(t / Self.runtime, 1), height: 1)
                        }
                        .opacity(eased(0.55, 1.20, at: t))
                }
                .padding(.top, 6)
            }
        }
    }

    /// A value that goes 0 → 1 between two moments, on an ease-out curve.
    ///
    /// Ease-out rather than linear everywhere: a light that arrives at a
    /// constant rate reads as a progress bar. The cubic is the cheapest curve
    /// that decelerates convincingly, and using one curve for every element is
    /// what makes five movements look like one hand.
    private func eased(_ from: Double, _ to: Double, at t: Double? = nil) -> Double {
        let now = t ?? (Date.timeIntervalSinceReferenceDate - start)
        let raw = min(max((now - from) / (to - from), 0), 1)
        return 1 - pow(1 - raw, 3)
    }
}

/// Nine stars, three chains of lines, and two comets — the sky connecting
/// itself, nothing drawn around it.
///
/// **Still not a real constellation, deliberately.** A recognisable Orion on
/// the launch screen is a claim about the sky tonight, and this screen has no
/// chart to make it from. It is the same visual language as the journey's
/// `ConstellationArt`, denser: the first draft read as a sketch, and the
/// owner said so. Density, not speed, is what changed.
private struct StarChart: View {

    /// 0 → 1 as the lines draw themselves.
    var lines: Double
    /// 0 → 1 as the nodes light, one after another.
    var nodes: Double
    /// The two comets. Off screen at both ends of their runs.
    var comet: Double
    var cometTwo: Double
    /// The raw clock, for the twinkle that never stops.
    var time: Double

    private let box: CGFloat = 300

    private let points: [(x: CGFloat, y: CGFloat, r: CGFloat)] = [
        (48, 196, 3.2), (104, 118, 4.6), (168, 152, 3.0),
        (214, 58, 5.2), (268, 104, 3.4), (132, 224, 3.8),
        (76, 64, 2.6), (232, 186, 3.0), (176, 250, 2.4),
    ]

    var body: some View {
        ZStack {
            // No dial and no ring — the owner's call: the arrival is the sky
            // connecting itself, nothing drawn around it.
            spine.trim(from: 0, to: lines)
                .stroke(Color.almaGold.opacity(0.5), lineWidth: 1)
            branch.trim(from: 0, to: max(0, lines * 1.3 - 0.3))
                .stroke(Color.almaGold.opacity(0.24), lineWidth: 1)
            branchTwo.trim(from: 0, to: max(0, lines * 1.5 - 0.5))
                .stroke(Color.almaGold.opacity(0.18), lineWidth: 1)

            ForEach(points.indices, id: \.self) { i in
                let share = Double(i) / Double(points.count)
                let lit = min(max((nodes - share * 0.55) / 0.45, 0), 1)
                // The twinkle: each star breathes on its own beat once lit,
                // so the finished chart is alive rather than printed.
                let breathe = 0.75 + 0.25 * sin(time * (1.1 + Double(i % 4) * 0.4) + Double(i) * 2)
                let p = points[i]
                Circle()
                    .fill(Color.almaStarFill)
                    .frame(width: p.r * 2, height: p.r * 2)
                    .shadow(color: Color.almaGoldBright.opacity(0.55 * breathe), radius: 6)
                    .scaleEffect((0.4 + lit * 0.6) * breathe)
                    .opacity(lit)
                    .position(x: p.x, y: p.y)
            }

            // The ring around the brightest node — where the mark blooms from.
            Circle()
                .stroke(Color.almaGoldBright.opacity(0.22 * nodes), lineWidth: 1)
                .frame(width: 30 + (1 - nodes) * 14, height: 30 + (1 - nodes) * 14)
                .position(x: 214, y: 58)

            cometView(comet, width: 90, angle: 28,
                      from: CGPoint(x: -40, y: 250), to: CGPoint(x: 340, y: 40))
            cometView(cometTwo, width: 64, angle: -16,
                      from: CGPoint(x: 330, y: 210), to: CGPoint(x: -30, y: 120))
        }
        .frame(width: box, height: box)
        .compositingGroup()
    }

    @ViewBuilder
    private func cometView(_ phase: Double, width: CGFloat, angle: Double,
                           from: CGPoint, to: CGPoint) -> some View {
        if phase > 0 && phase < 1 {
            Capsule()
                .fill(
                    LinearGradient(
                        colors: [.clear, Color.almaStarFill.opacity(0.75), .clear],
                        startPoint: .leading, endPoint: .trailing
                    )
                )
                .frame(width: width, height: 1.2)
                .rotationEffect(.degrees(angle))
                .position(
                    x: from.x + (to.x - from.x) * phase,
                    y: from.y + (to.y - from.y) * phase
                )
                .opacity(sin(phase * .pi))
        }
    }

    private var spine: Path {
        Path { p in
            p.move(to: CGPoint(x: 48, y: 196))
            p.addLine(to: CGPoint(x: 104, y: 118))
            p.addLine(to: CGPoint(x: 168, y: 152))
            p.addLine(to: CGPoint(x: 214, y: 58))
            p.addLine(to: CGPoint(x: 268, y: 104))
        }
    }

    private var branch: Path {
        Path { p in
            p.move(to: CGPoint(x: 104, y: 118))
            p.addLine(to: CGPoint(x: 132, y: 224))
            p.addLine(to: CGPoint(x: 214, y: 58))
        }
    }

    private var branchTwo: Path {
        Path { p in
            p.move(to: CGPoint(x: 76, y: 64))
            p.addLine(to: CGPoint(x: 104, y: 118))
            p.move(to: CGPoint(x: 232, y: 186))
            p.addLine(to: CGPoint(x: 268, y: 104))
            p.move(to: CGPoint(x: 132, y: 224))
            p.addLine(to: CGPoint(x: 176, y: 250))
        }
    }
}
