import SwiftUI

/// Two layers of stars, twinkling on two clocks.
///
/// **One `Canvas`, not a `ForEach` of circles.** A hundred and sixty animated
/// `View`s is a hundred and sixty nodes SwiftUI diffs on every frame; a `Canvas`
/// inside a `TimelineView` is one. On a screen that also has to scroll a
/// chapter, that difference is the difference between the sky being ambient and
/// the sky being the reason scrolling stutters.
///
/// **Each star has its own phase.** The CSS animates the *layer* — every star in
/// `.starfield` brightens and dims together, which on a 9-star field reads as
/// twinkling and on a 160-star field would read as the whole sky breathing.
/// Same period, per-star offset: the effect the CSS was reaching for, at the
/// density a phone screen needs.
struct Starfield: View {

    /// The field to draw. Generated once by the caller and held, so that a
    /// re-layout does not reshuffle the sky.
    let field: SkyField

    /// Overall opacity. A reading screen turns this down; the ceremony leaves
    /// it at 1.
    var intensity: Double = 1.0

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// Seconds for one full brighten-and-dim of the near layer. The far layer
    /// runs at 1.5× this and starts 1.6s in, so the two never coincide.
    private let nearPeriod: Double = 6.0
    private let farPeriod: Double = 9.0
    private let farOffset: Double = 1.6

    var body: some View {
        if reduceMotion {
            // Reduce Motion does not mean "no sky" — the stars are the canvas,
            // and removing them would change the design rather than calm it.
            // It means the stars stop moving: drawn once, at the steady middle
            // of their range, which is what the CSS does with `animation: none`
            // and a raised base opacity.
            Canvas { context, size in
                draw(field.far, in: context, size: size, time: nil, base: 0.5, period: farPeriod, offset: 0)
                draw(field.near, in: context, size: size, time: nil, base: 1.0, period: nearPeriod, offset: 0)
            }
            .opacity(intensity)
            .allowsHitTesting(false)
        } else {
            TimelineView(.animation) { timeline in
                let now = timeline.date.timeIntervalSinceReferenceDate
                Canvas { context, size in
                    draw(field.far, in: context, size: size, time: now, base: 0.5, period: farPeriod, offset: farOffset)
                    draw(field.near, in: context, size: size, time: now, base: 1.0, period: nearPeriod, offset: 0)
                }
            }
            .opacity(intensity)
            .allowsHitTesting(false)
        }
    }

    /// - Parameters:
    ///   - time: `nil` draws the still frame Reduce Motion asks for.
    ///   - base: the layer's own ceiling — the far layer never reaches full.
    private func draw(
        _ stars: [SkyStar],
        in context: GraphicsContext,
        size: CGSize,
        time: TimeInterval?,
        base: Double,
        period: Double,
        offset: Double
    ) {
        for star in stars {
            let brightness: Double
            if let time {
                // The CSS curve is `ease-in-out` between 0.25 and 1. A raised
                // cosine is the same shape without a keyframe table, and it is
                // continuous, so a star never jumps when the clock wraps.
                let t = ((time + offset) / period + star.phase).truncatingRemainder(dividingBy: 1)
                let eased = (1 - cos(t * 2 * .pi)) / 2
                brightness = 0.25 + eased * 0.75
            } else {
                brightness = 0.7
            }

            let point = CGPoint(x: star.x * size.width, y: star.y * size.height)
            let r = star.radius
            let rect = CGRect(x: point.x - r, y: point.y - r, width: r * 2, height: r * 2)
            context.fill(
                Path(ellipseIn: rect),
                with: .color(star.tint.colour.opacity(brightness * base))
            )
        }
    }
}

#Preview("Starfield") {
    ZStack {
        Color.almaNight
        Starfield(field: SkyField())
    }
    .ignoresSafeArea()
}
