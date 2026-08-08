import SwiftUI

/// Tonight's moon, drawn as she actually is — the one ornament on Today.
///
/// The disc's lit side and its width come straight from the transit payload's
/// `sky_now`: real illumination, real waxing/waning, recomputed by the
/// ephemeris every time the day loads. Around it, a thin ring carries one
/// spark per contact that perfects *today* — gold for a flowing aspect, the
/// product's red accent for a tense one. On a quiet day the ring is empty,
/// and an empty ring is the honest picture of a quiet day.
///
/// Small on purpose: this screen is a text a person reads every morning, and
/// the medallion is its seal, not its illustration. It draws itself in over a
/// second when the day opens and then holds still.
struct MoonMedallion: View {

    /// Illuminated fraction, 0…1, from `sky_now.moon_phase.illumination`.
    let illumination: Double
    /// Whether the moon is growing — decides which limb is lit.
    let waxing: Bool
    /// One entry per contact exact today; `true` means tense (square or
    /// opposition), which takes the red accent.
    let sparks: [Bool]

    private static let intro: TimeInterval = 1.2

    @State private var born: Date = .now
    @State private var settled = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 60.0, paused: settled)) { timeline in
            let raw = reduceMotion
                ? 1.0
                : min(1.0, timeline.date.timeIntervalSince(born) / Self.intro)
            let progress = 1 - pow(1 - raw, 3)
            medallion(progress: progress)
        }
        .task {
            // Re-appearing resets the clock, so the pause must lift too —
            // a paused timeline with a fresh `born` renders one frame of
            // progress zero and the art is simply gone on every revisit.
            born = .now
            settled = false
            guard !reduceMotion else { settled = true; return }
            try? await Task.sleep(nanoseconds: UInt64((Self.intro + 0.1) * 1_000_000_000))
            settled = true
        }
        .accessibilityHidden(true)
    }

    private func medallion(progress: Double) -> some View {
        Canvas { context, size in
            func phase(_ from: Double, _ to: Double) -> Double {
                min(1, max(0, (progress - from) / (to - from)))
            }

            let side = min(size.width, size.height)
            let centre = CGPoint(x: size.width / 2, y: size.height / 2)
            let ring = side * 0.47
            let r = side * 0.30

            // The ring sweeps closed first.
            let sweep = phase(0, 0.45)
            var orbit = Path()
            orbit.addArc(
                center: centre, radius: ring,
                startAngle: .degrees(-90), endAngle: .degrees(-90 + 360 * sweep),
                clockwise: false)
            context.stroke(orbit, with: .color(Color.almaGold.opacity(0.35)), lineWidth: 1)

            // The moon herself: the night side always, the lit side as wide as
            // the ephemeris says it is tonight.
            let lit = phase(0.25, 0.8)
            let disc = CGRect(x: centre.x - r, y: centre.y - r, width: r * 2, height: r * 2)
            context.fill(Path(ellipseIn: disc), with: .color(Color.almaNight700.opacity(0.9)))
            context.stroke(
                Path(ellipseIn: disc), with: .color(Color.almaGold.opacity(0.3)), lineWidth: 0.7)

            let f = max(0, min(1, illumination)) * lit
            if f > 0.005 {
                var shape = Path()
                // The lit limb: a semicircle on the bright side…
                shape.addArc(
                    center: centre, radius: r,
                    startAngle: .degrees(-90), endAngle: .degrees(90),
                    clockwise: false)
                // …closed by the terminator: the opposite semicircle scaled
                // across, which traces exactly the ellipse a sphere's shadow
                // draws. The sign is the whole optics: below half the shadow
                // bulges *into* the lit limb and leaves a sliver, above half
                // it bulges away and leaves a gibbous. It was flipped once —
                // a 23% crescent drew as a 77% gibbous — which is why the
                // check below pins the crossing point, not the pretty shape.
                // The back semicircle passes through (-r, 0); scaled by
                // (2f-1) it crosses at x = r(1-2f): +0.54r for a 23% sliver,
                // -r for a full moon.
                let terminator = max(0.001, abs(2 * f - 1)) * (f >= 0.5 ? 1 : -1)
                var back = Path()
                back.addArc(
                    center: .zero, radius: r,
                    startAngle: .degrees(90), endAngle: .degrees(270),
                    clockwise: false)
                let squeezed = back.applying(CGAffineTransform(scaleX: terminator, y: 1))
                    .applying(CGAffineTransform(translationX: centre.x, y: centre.y))
                shape.addPath(squeezed)
                // Waxing lights the right limb, waning the left — mirrored in
                // place rather than re-derived.
                let oriented = waxing
                    ? shape
                    : shape
                        .applying(CGAffineTransform(translationX: -centre.x, y: -centre.y))
                        .applying(CGAffineTransform(scaleX: -1, y: 1))
                        .applying(CGAffineTransform(translationX: centre.x, y: centre.y))
                context.fill(oriented, with: .color(Color.almaStarFill.opacity(0.92)))
            }

            // One spark per contact perfecting today, seated along the ring.
            for (index, tense) in sparks.prefix(6).enumerated() {
                let pop = phase(0.6 + Double(index) * 0.08, 0.85 + Double(index) * 0.08)
                guard pop > 0 else { continue }
                let a = (Double(index) * 32 - 52) * .pi / 180
                let at = CGPoint(
                    x: centre.x + ring * cos(a), y: centre.y + ring * sin(a))
                let radius = side * 0.030 * pop
                context.fill(
                    Path(ellipseIn: CGRect(
                        x: at.x - radius / 2, y: at.y - radius / 2,
                        width: radius, height: radius)),
                    with: .color(
                        (tense ? Color.almaDisagree : Color.almaGoldBright)
                            .opacity(0.9 * pop)))
            }
        }
    }
}
