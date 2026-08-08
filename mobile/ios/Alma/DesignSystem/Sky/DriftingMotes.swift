import SwiftUI

/// Three specks of dust, rising and fading.
///
/// The count is the brand book's ceiling and not a parameter with a sensible
/// default: four motes is the point at which the eye starts tracking them
/// instead of the type, and a ceiling that can be raised is a ceiling that gets
/// raised. `SkyField` generates exactly three.
///
/// The rise is 120 points over 12–17 seconds, which is slow enough that a mote
/// is only ever noticed in peripheral vision — the intended effect. Opacity
/// ramps in over the first fifth and out over the last fifth, so nothing ever
/// pops into or out of existence.
struct DriftingMotes: View {

    let field: SkyField
    var intensity: Double = 1.0

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// How far a mote travels, in points. From the CSS `dust` keyframes.
    private let rise: Double = 120

    var body: some View {
        // Under Reduce Motion the motes are removed rather than frozen. A
        // frozen mote is a dot of dirt on the screen: the whole of what it is,
        // is the movement, so with the movement gone there is nothing left that
        // belongs in the design.
        if !reduceMotion {
            TimelineView(.animation) { timeline in
                let now = timeline.date.timeIntervalSinceReferenceDate
                Canvas { context, size in
                    for mote in field.motes {
                        let t = ((now + mote.delay) / mote.duration)
                            .truncatingRemainder(dividingBy: 1)

                        let opacity: Double =
                            switch t {
                            case ..<0.20: t / 0.20 * 0.70
                            case ..<0.80: 0.70 - (t - 0.20) / 0.60 * 0.20
                            default: 0.50 * (1 - (t - 0.80) / 0.20)
                            }

                        let x = mote.x * size.width
                        let y = mote.y * size.height - t * rise
                        let r = mote.size / 2
                        context.fill(
                            Path(ellipseIn: CGRect(x: x - r, y: y - r, width: r * 2, height: r * 2)),
                            with: .color(Color.almaStarFill.opacity(opacity * intensity))
                        )
                    }
                }
            }
            .allowsHitTesting(false)
        }
    }
}
