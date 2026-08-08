import SwiftUI

/// One comet, once every eighteen seconds, and never two.
///
/// The whole point of a comet is that it is a *surprise*. The CSS gets this by
/// making the animation 18 seconds long and the visible part of it 60% — the
/// comet crosses, then the screen is empty for seven seconds before it comes
/// round again. That gap is the design; a comet on a two-second loop is a
/// loading spinner.
///
/// **Where it goes is a parameter, and that is the fix.** The first version
/// hard-coded one trajectory into the shared sky: origin (0.14, 0.08), travel
/// +480/+340. On a 402×874 phone that runs the head from about (-4, 30) to
/// (476, 370) and sweeps a 180-point streak through the top 42% of the canvas —
/// which is exactly where the eyebrow, the display title and the first paragraph
/// sit. It cut through the account name on Today, through "WHO AM I" on the hub,
/// through "II / IX" in the journey and through the sun-sign glyph on the
/// portrait. `Sky.tsx` states the rule it was breaking in its own file header:
/// *never behind body copy*. On the web that is achievable by placing the comet
/// per screen; here one shared sky means one path unless the path is derived,
/// so it is derived — from the screen's own seed, and only ever through the
/// lower band, below where a title and its first paragraph can reach.
struct Comet: View {

    /// The screen's sky seed. Two screens get two different crossings, which is
    /// half of what makes moving between them feel like moving.
    var seed: UInt64 = 0x414C_4D41

    /// Seconds for one crossing plus the pause after it.
    var period: Double = 18

    /// Length of the streak in points.
    var length: Double = 180

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        // A still comet is a gold scratch across the screen. Removed entirely
        // under Reduce Motion, for the same reason as the motes.
        if !reduceMotion {
            let path = Trajectory(seed: seed)

            TimelineView(.animation) { timeline in
                let now = timeline.date.timeIntervalSinceReferenceDate
                Canvas { context, size in
                    let t = (now / period).truncatingRemainder(dividingBy: 1)

                    // Past 60% the comet is gone and there is nothing to draw.
                    // Checking here rather than drawing at zero opacity saves
                    // the gradient work for seven seconds of every eighteen.
                    guard t < 0.60 else { return }

                    let opacity: Double =
                        switch t {
                        case ..<0.08: t / 0.08 * 0.9
                        case ..<0.42: 0.9
                        default: 0.9 * (1 - (t - 0.42) / 0.18)
                        }

                    let travel = t / 0.60
                    let head = CGPoint(
                        x: (path.from.x + (path.to.x - path.from.x) * travel) * size.width,
                        y: (path.from.y + (path.to.y - path.from.y) * travel) * size.height
                    )
                    let radians = path.angle(in: size)
                    let tail = CGPoint(
                        x: head.x - cos(radians) * length,
                        y: head.y - sin(radians) * length
                    )

                    var streak = Path()
                    streak.move(to: tail)
                    streak.addLine(to: head)

                    context.stroke(
                        streak,
                        with: .linearGradient(
                            Gradient(stops: [
                                // Transparent at the tail, brightest just short
                                // of the head, and softened again at the very
                                // tip. Without the last stop a 1-point line with
                                // no falloff terminates bluntly and reads as a
                                // mis-drawn rule or a scratch on the lens — the
                                // CSS gradient runs transparent → 0.8 and gets
                                // away with it because the web comet also
                                // carries a blurred glow behind it.
                                .init(color: .almaStarFill.opacity(0), location: 0),
                                .init(color: .almaStarFill.opacity(0.62 * opacity), location: 0.86),
                                .init(color: .almaStarFill.opacity(0.22 * opacity), location: 1),
                            ]),
                            startPoint: tail,
                            endPoint: head
                        ),
                        lineWidth: 1
                    )
                }
            }
            .allowsHitTesting(false)
        }
    }
}

/// Where one screen's comet crosses, in fractions of the canvas.
///
/// Four crossings, chosen by the seed, all of them in the **upper third** —
/// which is where the ceremony's art is, and the ceremony is now the only mood
/// that has a comet at all (see `NightSky.Mood.hasComet`). The head never goes
/// below 0.34 and the streak trails *up* behind it, so the whole thing stays
/// clear of the question and the controls underneath.
///
/// A table rather than arithmetic on the seed, because "somewhere random"
/// eventually lands somewhere bad and nobody finds out for a month. Four
/// hand-placed diagonals can be looked at once and trusted.
private struct Trajectory {

    let from: CGPoint
    let to: CGPoint

    init(seed: UInt64) {
        // Mixed rather than taken modulo directly: the seeds in this app are
        // four-character ASCII constants ("JOUR", "TODA"), which differ mostly
        // in their high bytes, and `% 4` on the raw value gives several screens
        // the same crossing.
        var x = seed &* 0x9E37_79B9_7F4A_7C15
        x ^= x >> 29
        switch Int(truncatingIfNeeded: x &>> 33) & 3 {
        case 0: self.init(from: CGPoint(x: -0.10, y: 0.06), to: CGPoint(x: 0.68, y: 0.34))
        case 1: self.init(from: CGPoint(x: 0.30, y: 0.04), to: CGPoint(x: 1.10, y: 0.30))
        case 2: self.init(from: CGPoint(x: 1.08, y: 0.08), to: CGPoint(x: 0.28, y: 0.33))
        default: self.init(from: CGPoint(x: -0.05, y: 0.30), to: CGPoint(x: 0.72, y: 0.05))
        }
    }

    private init(from: CGPoint, to: CGPoint) {
        self.from = from
        self.to = to
    }

    /// The streak lies along the direction of travel, so the tail is genuinely
    /// behind the head. Computed in points rather than in fractions: a fraction
    /// space on a 402×874 screen is not square, and an angle taken in it would
    /// leave the tail off the line the head is actually moving down.
    func angle(in size: CGSize) -> Double {
        atan2((to.y - from.y) * size.height, (to.x - from.x) * size.width)
    }
}
