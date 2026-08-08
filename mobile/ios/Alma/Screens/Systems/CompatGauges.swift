import SwiftUI

/// The four synastry scores as gauges — the picture the category leads with,
/// drawn honestly.
///
/// The competitor's best screenshot is a big green «87%», and it sells; ours
/// are the same numbers the engine already computes (0–5 per axis), shown as
/// arcs with a large percentage. Nothing is invented: the arc *is*
/// `score / 5`, friction keeps the product's red accent because high friction
/// is the one number a couple should read as a warning, and a missing score
/// simply has no gauge.
///
/// Each gauge sweeps itself in over a second and then breathes with the rest
/// of the settled diagrams.
struct CompatGauges: View {

    let data: JSONValue

    private static let intro: TimeInterval = 1.2

    @State private var born: Date = .now
    @State private var settled = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// The engine's four axes, in the order a couple reads them.
    private static let axes: [(key: String, tense: Bool)] = [
        ("attraction", false),
        ("warmth", false),
        ("friction", true),
        ("endurance", false),
    ]

    private var scores: [(key: String, fraction: Double, tense: Bool)] {
        guard let raw = data["scores"]?.objectValue else { return [] }
        return Self.axes.compactMap { axis in
            guard let value = raw[axis.key]?.doubleValue else { return nil }
            return (axis.key, min(max(value / 5.0, 0), 1), axis.tense)
        }
    }

    var body: some View {
        let scores = self.scores
        if !scores.isEmpty {
            TimelineView(.animation(minimumInterval: 1.0 / 60.0, paused: settled)) { timeline in
                let raw = reduceMotion
                    ? 1.0
                    : min(1.0, timeline.date.timeIntervalSince(born) / Self.intro)
                let progress = 1 - pow(1 - raw, 3)

                HStack(alignment: .top, spacing: 0) {
                    ForEach(Array(scores.enumerated()), id: \.element.key) { index, score in
                        gauge(
                            fraction: score.fraction,
                            tense: score.tense,
                            label: L10nCabinet.scoreName(score.key),
                            progress: min(1, max(0, (progress - Double(index) * 0.12) / 0.6))
                        )
                        .frame(maxWidth: .infinity)
                    }
                }
            }
            .task {
                // Re-appearing resets the clock, so the pause must lift too —
                // a paused timeline with a fresh `born` renders one frame of
                // progress zero and the art is simply gone on every revisit.
                born = .now
                settled = false
                guard !reduceMotion else { settled = true; return }
                try? await Task.sleep(nanoseconds: UInt64((Self.intro + 0.6) * 1_000_000_000))
                settled = true
            }
            .almaBreathing()
            .padding(.vertical, 8)
        }
    }

    private func gauge(fraction: Double, tense: Bool, label: String, progress: Double) -> some View {
        VStack(spacing: 8) {
            ZStack {
                Canvas { context, size in
                    let side = min(size.width, size.height)
                    let centre = CGPoint(x: size.width / 2, y: size.height / 2)
                    let radius = side * 0.42
                    // A 270° dial, opening downward — the shape a meter has.
                    let start = Angle.degrees(135)
                    let full = 270.0

                    var track = Path()
                    track.addArc(
                        center: centre, radius: radius,
                        startAngle: start, endAngle: .degrees(135 + full),
                        clockwise: false)
                    context.stroke(
                        track, with: .color(Color.almaBody.opacity(0.14)),
                        style: StrokeStyle(lineWidth: 3, lineCap: .round))

                    let swept = full * fraction * progress
                    if swept > 0 {
                        var arc = Path()
                        arc.addArc(
                            center: centre, radius: radius,
                            startAngle: start, endAngle: .degrees(135 + swept),
                            clockwise: false)
                        context.stroke(
                            arc,
                            with: .color(tense ? Color.almaDisagree : Color.almaGold),
                            style: StrokeStyle(lineWidth: 3, lineCap: .round))
                    }
                }

                Text(verbatim: "\(Int((fraction * 100 * progress).rounded()))%")
                    .font(AlmaFonts.display(19, relativeTo: .title3))
                    .foregroundStyle(Color.almaInkLight.opacity(0.4 + 0.6 * progress))
                    .monospacedDigit()
            }
            .frame(width: 74, height: 74)

            Text(verbatim: label)
                .almaMeta()
                .multilineTextAlignment(.center)
                .lineLimit(2)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(Text(verbatim: "\(label): \(Int((fraction * 100).rounded()))%"))
    }
}
