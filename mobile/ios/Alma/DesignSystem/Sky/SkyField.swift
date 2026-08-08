import SwiftUI

/// A deterministic random source, and the star and mote fields drawn from it.
///
/// **Why seeded rather than `Double.random`.** The sky is regenerated whenever a
/// view's geometry changes — a rotation, a keyboard, a sheet resizing the
/// screen behind it. With an unseeded source every one of those events silently
/// reshuffles the entire star field, which reads as a flicker at exactly the
/// moment the interface is asking for attention elsewhere. With a seed, the same
/// screen has the same sky for as long as the app is running, and two screens
/// with different seeds have visibly different skies.
///
/// SplitMix64 rather than `SystemRandomNumberGenerator`: it is eight lines, it is
/// well-distributed enough for scattering dots, and it has no state we have to
/// think about across threads.
struct SkyRandom: RandomNumberGenerator {
    private var state: UInt64

    init(seed: UInt64) {
        // A zero seed would make SplitMix64 produce a fixed sequence, so it is
        // pushed off zero rather than rejected — a caller passing 0 wants "the
        // default sky", not a crash.
        self.state = seed &+ 0x9E37_79B9_7F4A_7C15
    }

    mutating func next() -> UInt64 {
        state = state &+ 0x9E37_79B9_7F4A_7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }

    mutating func unit() -> Double {
        Double(next() >> 11) * (1.0 / 9_007_199_254_740_992.0)
    }

    mutating func between(_ low: Double, _ high: Double) -> Double {
        low + unit() * (high - low)
    }
}

/// One star. Positions are *fractions* of the canvas, not points, so a field
/// generated once survives every layout change without being regenerated.
struct SkyStar: Sendable {
    let x: Double
    let y: Double
    let radius: Double
    /// Where in its own twinkle cycle this star starts, 0...1.
    let phase: Double
    /// Which of the three star colours this one is.
    let tint: Tint

    enum Tint: Sendable {
        /// Almost white — the majority.
        case white
        /// Aged parchment.
        case warm
        /// Gold, and rare: more than a few and the sky starts to look yellow.
        case gold

        var colour: Color {
            switch self {
            case .white: Color(hex: 0xFFF8E6)
            case .warm: Color(hex: 0xE6D9B4)
            case .gold: .almaGold
            }
        }
    }
}

/// One drifting mote of dust.
struct SkyMote: Sendable {
    let x: Double
    /// Where it starts, as a fraction of the canvas height.
    let y: Double
    let size: Double
    /// Seconds for one rise. The web app uses 14; varying it stops the motes
    /// from moving as a group, which is the thing that gives away an animation.
    let duration: Double
    let delay: Double
}

/// A generated sky: the two star layers and the motes, produced once from a
/// seed and then held.
///
/// The counts come straight from the brand book's ceiling — "≤3 dust motes, one
/// comet per screen, at most two aura blobs". The star counts are ours, because
/// the CSS expresses its field as nine hand-placed radial gradients and nine
/// stars on a 900-point canvas is a diagram of a sky rather than a sky.
struct SkyField: Sendable {

    let near: [SkyStar]
    let far: [SkyStar]
    let motes: [SkyMote]

    /// - Parameters:
    ///   - seed: anything stable for the screen. `Route`-derived values are
    ///     ideal; the default is the one every ambient background uses.
    ///   - density: 1.0 is the standard field. The journey's ceremony turns it
    ///     up; a reading screen turns it down so the text is never competing
    ///     with the background.
    init(seed: UInt64 = 0x414C_4D41, density: Double = 1.0) {
        var rng = SkyRandom(seed: seed)

        let nearCount = Int(64 * density)
        let farCount = Int(96 * density)

        func star(minRadius: Double, maxRadius: Double, goldChance: Double) -> SkyStar {
            let roll = rng.unit()
            let tint: SkyStar.Tint = roll < goldChance ? .gold : (roll < 0.34 ? .warm : .white)
            return SkyStar(
                x: rng.unit(),
                y: rng.unit(),
                radius: rng.between(minRadius, maxRadius),
                phase: rng.unit(),
                tint: tint
            )
        }

        // The near layer is the one the eye reads: fewer, larger, brighter.
        self.near = (0..<nearCount).map { _ in
            star(minRadius: 0.7, maxRadius: 1.05, goldChance: 0.10)
        }
        // The far layer is a wash. Uniformly 0.5pt and half-lit, on a slower
        // and offset clock, so the two layers never pulse together.
        self.far = (0..<farCount).map { _ in
            star(minRadius: 0.45, maxRadius: 0.62, goldChance: 0.06)
        }

        self.motes = (0..<3).map { index in
            SkyMote(
                x: rng.between(0.06, 0.94),
                y: rng.between(0.45, 0.95),
                size: rng.between(1.6, 2.4),
                duration: rng.between(12, 17),
                delay: Double(index) * rng.between(3.0, 6.0)
            )
        }
    }
}
