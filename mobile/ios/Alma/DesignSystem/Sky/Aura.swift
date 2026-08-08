import SwiftUI

/// A blurred bloom of colour behind the night — the only place indigo appears.
///
/// Two at most on a screen, and never behind body copy: an aura under a
/// paragraph raises the background luminance unevenly, and the line that
/// crosses its edge is the one that becomes hard to read. Put them behind a
/// heading, behind the mark, behind nothing.
///
/// The drift is a 30–36 second ellipse of a few per cent. Slow enough that the
/// movement is never seen directly, present enough that the screen is not a
/// still image.
struct Aura: View {

    enum Tone: Sendable {
        /// The default: violet-indigo, the deepest colour in the palette.
        case indigo
        /// Blue, for the ceremony and the portrait.
        case deep
        /// Gold — used once, behind the mark, and nowhere near type.
        case gold
        case violet

        var stops: [Gradient.Stop] {
            switch self {
            case .indigo:
                [
                    .init(color: Color.almaIndigoBright.opacity(0.42), location: 0.00),
                    .init(color: Color.almaIndigo.opacity(0.22), location: 0.44),
                    .init(color: .clear, location: 0.70),
                ]
            case .deep:
                [
                    .init(color: Color.almaIndigoDeep.opacity(0.38), location: 0.0),
                    .init(color: .clear, location: 0.70),
                ]
            case .gold:
                [
                    .init(color: Color.almaGold.opacity(0.20), location: 0.0),
                    .init(color: .clear, location: 0.66),
                ]
            case .violet:
                [
                    .init(color: Color(hex: 0x4A3A9E).opacity(0.34), location: 0.0),
                    .init(color: .clear, location: 0.68),
                ]
            }
        }
    }

    /// Which drift an aura is on. Two auras on the same screen must not share
    /// one, or they move as a pair and the screen breathes.
    enum Drift: Sendable {
        case none
        case a
        case b

        var period: Double {
            switch self {
            case .none: 0
            case .a: 30
            case .b: 36
            }
        }
    }

    var tone: Tone = .indigo
    var diameter: CGFloat = 420
    var drift: Drift = .none

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        Group {
            if drift == .none || reduceMotion {
                bloom
            } else {
                TimelineView(.animation) { timeline in
                    let t = timeline.date.timeIntervalSinceReferenceDate / drift.period
                    let phase = t.truncatingRemainder(dividingBy: 1) * 2 * .pi
                    // The CSS translates by ±3–4% and scales by 1.05–1.07. Both
                    // are on the same sine, half a cycle apart, which is what
                    // makes the movement read as a slow tumble rather than as a
                    // pulse.
                    let sway = sin(phase)
                    let swell = 1 + (1 - cos(phase)) / 2 * 0.06

                    bloom
                        .scaleEffect(swell)
                        .offset(
                            x: (drift == .a ? -1 : 1) * sway * diameter * 0.035,
                            y: (drift == .a ? 1 : -1) * sway * diameter * 0.035
                        )
                }
            }
        }
        .allowsHitTesting(false)
    }

    private var bloom: some View {
        Circle()
            .fill(
                RadialGradient(
                    stops: tone.stops,
                    center: .center,
                    startRadius: 0,
                    endRadius: diameter / 2
                )
            )
            .frame(width: diameter, height: diameter)
            // The CSS blurs by 34px on top of an already-soft radial gradient.
            // The gradient alone banded visibly on an OLED at these opacities;
            // the blur is what removes the rings.
            .blur(radius: 34)
    }
}
