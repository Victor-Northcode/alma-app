import SwiftUI

/// The living celestial art at the top of each scene.
///
/// Six drawings, one per question, redrawn from the SVGs and CSS in
/// `JourneyOverlay.tsx` and `screens.css` — the same radii, the same opacities,
/// the same periods. They are not decoration: the journey asks for a birth date
/// and a birth time and a birth place, and the drawing above each question is a
/// dial, a clock and a globe. Somebody who cannot read the sentence still knows
/// what is being asked.
///
/// **All motion comes off one clock.** Each drawing wraps its moving parts in a
/// single `CelestialTime`, which is one `TimelineView` for the whole scene
/// rather than one per rotating ring. Six `repeatForever` animations would
/// drift apart from each other and from the sky behind them; a rotation derived
/// from the wall clock cannot.
///
/// **Reduce Motion stops the sky, not the scene.** Every rotation freezes at
/// its starting angle, which is a still drawing that still says dial, clock,
/// globe. The one thing that keeps moving is the line-drawing in the
/// constellation and the ceremony, because that is a transition rather than a
/// loop — it happens once and ends, and removing it would leave a diagram that
/// never appears.

// MARK: — the clock everything hangs off

/// Hands the wall clock to a drawing, once per scene.
private struct CelestialTime<Content: View>: View {

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @ViewBuilder var content: (TimeInterval) -> Content

    var body: some View {
        if reduceMotion {
            content(0)
        } else {
            TimelineView(.animation) { timeline in
                content(timeline.date.timeIntervalSinceReferenceDate)
            }
        }
    }
}

/// One turn every `seconds`. Negative for the rings that run the other way —
/// two rings turning the same way read as one thick ring.
private func spin(_ time: TimeInterval, seconds: Double, reversed: Bool = false) -> Angle {
    let turns = (time / seconds).truncatingRemainder(dividingBy: 1)
    return .degrees((reversed ? -turns : turns) * 360)
}

/// A 0…1 cycle for anything that breathes or ripples.
private func cycle(_ time: TimeInterval, seconds: Double, phase: Double = 0) -> Double {
    ((time / seconds) + phase).truncatingRemainder(dividingBy: 1)
}

/// How far a line has drawn itself in, on the same clock as everything else.
///
/// **This was `@State` and `withAnimation` first, and it did not survive
/// contact with the simulator.** An implicit animation on a `@State` value is
/// committed in the view's own transaction; a `TimelineView(.animation)`
/// re-renders its subtree every frame in a *different* one, and one of those
/// frames snapshots the in-flight animation to whatever it had reached and
/// stops it. The constellation drew about half of itself and then sat there.
/// Deriving the progress from the same wall clock that drives the rotations
/// cannot be interrupted, because there is nothing to interrupt.
///
/// `start` is `.nan` until the view appears, which is the honest spelling of
/// "not yet": before then there is no elapsed time to measure and nothing is
/// drawn.
private func drawn(_ time: TimeInterval, since start: TimeInterval, over seconds: Double) -> CGFloat {
    guard !start.isNaN else { return 0 }
    let linear = min(1, max(0, (time - start) / seconds))
    // Ease-out cubic: the line arrives quickly and settles, which is what
    // `ease-out` does in the CSS this came from.
    return 1 - pow(1 - linear, 3)
}

// MARK: — drawing in a fixed box

/// Draw at the size the SVG was drawn at, then scale to whatever room there is.
///
/// The alternative — recomputing every coordinate against the available width —
/// is how a drawing ends up with its rings elliptical on one phone. Scaling a
/// finished drawing keeps every proportion, and the only cost is that a
/// hairline stroke scales with it, which at these ratios is under a quarter of
/// a point.
private struct DesignBox<Content: View>: View {

    let side: CGFloat
    @ViewBuilder var content: Content

    var body: some View {
        GeometryReader { geometry in
            let scale = min(geometry.size.width / side, geometry.size.height / side, 1)
            content
                .frame(width: side, height: side)
                .scaleEffect(scale)
                .frame(width: geometry.size.width, height: geometry.size.height)
        }
    }
}

/// A path written in the SVG's own coordinates.
///
/// The closure receives a mapper from viewBox units to points, so the numbers
/// below can be read straight against the `<path d="…">` they came from — which
/// is the only way anybody will ever be able to check that they match.
private struct DesignPath: Shape {

    let box: CGFloat
    /// `@Sendable` because `Shape` inherits `Animatable`, which is `Sendable` —
    /// SwiftUI may evaluate a shape's path off the main actor. Every closure
    /// passed below captures nothing but its own literals, so the requirement
    /// costs nothing and is worth having stated.
    let build: @Sendable (inout Path, (CGFloat, CGFloat) -> CGPoint) -> Void

    func path(in rect: CGRect) -> Path {
        let scale = min(rect.width, rect.height) / box
        let originX = rect.midX - box * scale / 2
        let originY = rect.midY - box * scale / 2
        func point(_ x: CGFloat, _ y: CGFloat) -> CGPoint {
            CGPoint(x: originX + x * scale, y: originY + y * scale)
        }
        var path = Path()
        build(&path, point)
        return path
    }
}

/// A star at a viewBox coordinate, twinkling on its own phase.
private struct DesignStar: View {

    let box: CGFloat
    let x: CGFloat
    let y: CGFloat
    let radius: CGFloat
    let period: Double
    let phase: Double
    let time: TimeInterval

    var body: some View {
        let alpha = 0.55 + 0.45 * sin(2 * .pi * cycle(time, seconds: period, phase: phase))
        Circle()
            .fill(Color.almaStarFill)
            .frame(width: radius * 2, height: radius * 2)
            .opacity(alpha)
            .position(x: x, y: y)
            .frame(width: box, height: box)
    }
}

/// The soft bloom behind a mark. `breathe` in the CSS: an 8-second swell.
private struct Halo: View {

    var diameter: CGFloat = 262
    var period: Double = 8
    let time: TimeInterval

    var body: some View {
        let breath = 0.94 + 0.06 * sin(2 * .pi * cycle(time, seconds: period))
        Circle()
            .fill(
                RadialGradient(
                    stops: [
                        .init(color: Color.almaStarFill.opacity(0.14), location: 0),
                        .init(color: .clear, location: 0.68),
                    ],
                    center: .center,
                    startRadius: 0,
                    endRadius: diameter / 2
                )
            )
            .frame(width: diameter, height: diameter)
            .scaleEffect(breath)
    }
}

// MARK: — I · the constellation

/// Five points joined, then joined again a different way.
///
/// The second path is the argument the whole product makes, drawn: the same
/// stars, read differently. It is why this sits above the question about what
/// is loudest.
struct ConstellationArt: View {

    /// When the drawing began. `.nan` until it appears — see `drawn(_:since:over:)`.
    @State private var start: TimeInterval = .nan
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private let box: CGFloat = 320

    var body: some View {
        DesignBox(side: box) {
            CelestialTime { time in
                // Under Reduce Motion the clock is frozen at zero, so the
                // finished drawing is what is shown. It is a transition rather
                // than a loop: removing it would mean the constellation never
                // appears at all, which is not an accommodation.
                let progress = reduceMotion ? 1 : drawn(time, since: start, over: 3.4)
                ZStack {
                    DesignPath(box: box) { path, p in
                        path.move(to: p(54, 214))
                        path.addLine(to: p(112, 128))
                        path.addLine(to: p(182, 160))
                        path.addLine(to: p(232, 66))
                        path.addLine(to: p(286, 112))
                    }
                    .trim(from: 0, to: progress)
                    .stroke(Color.almaGold.opacity(0.5), lineWidth: 1)

                    DesignPath(box: box) { path, p in
                        path.move(to: p(112, 128))
                        path.addLine(to: p(142, 236))
                        path.addLine(to: p(232, 66))
                    }
                    .trim(from: 0, to: progress)
                    .stroke(Color.almaGold.opacity(0.26), lineWidth: 1)

                    DesignStar(box: box, x: 54, y: 214, radius: 3.6, period: 3.6, phase: 0.0, time: time)
                    DesignStar(box: box, x: 112, y: 128, radius: 4.8, period: 4.4, phase: 0.14, time: time)
                    DesignStar(box: box, x: 182, y: 160, radius: 3.2, period: 4.0, phase: 0.07, time: time)
                    DesignStar(box: box, x: 232, y: 66, radius: 5.4, period: 5.2, phase: 0.21, time: time)
                    DesignStar(box: box, x: 286, y: 112, radius: 3.4, period: 4.8, phase: 0.28, time: time)
                    DesignStar(box: box, x: 142, y: 236, radius: 4.0, period: 4.2, phase: 0.05, time: time)

                    Circle()
                        .stroke(Color.almaGoldBright.opacity(0.26), lineWidth: 1)
                        .frame(width: 34, height: 34)
                        .position(x: 232, y: 66)
                        .frame(width: box, height: box)
                }
            }
        }
        .onAppear {
            if start.isNaN { start = Date.timeIntervalSinceReferenceDate }
        }
        .accessibilityHidden(true)
    }
}

// MARK: — II · the orbit

/// Alma with something going round her. The scene for the name: the mark is
/// the thing being introduced.
struct OrbitArt: View {

    private let box: CGFloat = 300

    var body: some View {
        DesignBox(side: box) {
            CelestialTime { time in
                ZStack {
                    Halo(diameter: 262, period: 8, time: time)

                    Circle()
                        .stroke(Color.almaGold.opacity(0.4), lineWidth: 1)
                        .frame(width: 214, height: 214)
                        .overlay(alignment: .top) {
                            Circle()
                                .fill(Color.almaStarFill)
                                .frame(width: 7, height: 7)
                                .shadow(color: Color.almaStarFill.opacity(0.95), radius: 6)
                                .offset(y: -3.5)
                        }
                        .rotationEffect(spin(time, seconds: 34))

                    Circle()
                        .stroke(
                            Color.almaGold.opacity(0.28),
                            style: StrokeStyle(lineWidth: 1, dash: [4, 5])
                        )
                        .frame(width: 142, height: 142)
                        .rotationEffect(spin(time, seconds: 24, reversed: true))

                    AlmaPresence(size: 62, ring: false)
                }
            }
        }
        .accessibilityHidden(true)
    }
}

// MARK: — III · the dial

/// A year, as one very slow revolution. The scene for the date.
struct DialArt: View {

    private let box: CGFloat = 262

    var body: some View {
        DesignBox(side: box) {
            CelestialTime { time in
                ZStack {
                    Circle()
                        .stroke(Color.almaGold.opacity(0.45), lineWidth: 1)
                        .frame(width: 212, height: 212)

                    Circle()
                        .stroke(
                            Color.almaGoldDeep.opacity(0.3),
                            style: StrokeStyle(lineWidth: 1, dash: [2, 5])
                        )
                        .frame(width: 172, height: 172)

                    Circle()
                        .fill(Color.almaStarFill)
                        .frame(width: 8, height: 8)
                        .offset(y: -106)
                        .rotationEffect(spin(time, seconds: 180))

                    Circle()
                        .fill(Color.almaStarFill)
                        .frame(width: 9.2, height: 9.2)
                }
            }
        }
        .accessibilityHidden(true)
    }
}

// MARK: — IV · the clock

/// Twelve hours and one minute hand. The scene for the birth time — and the
/// only scene whose drawing is also the thing being refused when somebody says
/// they do not know.
struct ClockArt: View {

    private let box: CGFloat = 262

    var body: some View {
        DesignBox(side: box) {
            CelestialTime { time in
                ZStack {
                    Circle()
                        .stroke(Color.almaGold.opacity(0.45), lineWidth: 1)
                        .frame(width: 212, height: 212)

                    Circle()
                        .stroke(
                            Color.almaGoldDeep.opacity(0.3),
                            style: StrokeStyle(lineWidth: 1, dash: [2, 5])
                        )
                        .frame(width: 172, height: 172)

                    DesignPath(box: box) { path, p in
                        path.move(to: p(131, 25)); path.addLine(to: p(131, 39))
                        path.move(to: p(131, 223)); path.addLine(to: p(131, 237))
                        path.move(to: p(25, 131)); path.addLine(to: p(39, 131))
                        path.move(to: p(223, 131)); path.addLine(to: p(237, 131))
                    }
                    .stroke(Color.almaGold.opacity(0.55), lineWidth: 1)

                    // The minute hand, one turn an hour, and the hour hand at a
                    // twelfth of that. Real periods rather than decorative ones:
                    // a clock whose hands are unrelated is a clock nobody trusts.
                    hand(length: 77, width: 1.4, colour: Color.almaStarFill.opacity(0.9))
                        .rotationEffect(spin(time, seconds: 60))

                    hand(length: 52, width: 1.8, colour: Color.almaGold.opacity(0.8))
                        .rotationEffect(spin(time, seconds: 720))

                    Circle()
                        .fill(Color.almaStarFill)
                        .frame(width: 9.2, height: 9.2)
                }
            }
        }
        .accessibilityHidden(true)
    }

    private func hand(length: CGFloat, width: CGFloat, colour: Color) -> some View {
        Capsule()
            .fill(colour)
            .frame(width: width, height: length)
            .offset(y: -length / 2)
    }
}

// MARK: — V · the globe

/// Meridians turning, and one point on them. The scene for the birthplace.
struct GlobeArt: View {

    private let box: CGFloat = 280

    var body: some View {
        DesignBox(side: box) {
            CelestialTime { time in
                ZStack {
                    ZStack {
                        Circle()
                            .stroke(Color.almaGold.opacity(0.5), lineWidth: 1)
                            .frame(width: 208, height: 208)

                        // Two meridians and two parallels — enough for a sphere,
                        // and four fewer than the SVG, because at this size the
                        // extra ones close up into a grey ring.
                        DesignPath(box: box) { path, p in
                            path.move(to: p(36, 140)); path.addLine(to: p(244, 140))
                            path.move(to: p(140, 36))
                            path.addCurve(to: p(140, 244), control1: p(178, 70), control2: p(178, 210))
                            path.move(to: p(140, 36))
                            path.addCurve(to: p(140, 244), control1: p(102, 70), control2: p(102, 210))
                            path.move(to: p(61, 83))
                            path.addCurve(to: p(219, 83), control1: p(109, 107), control2: p(171, 107))
                            path.move(to: p(61, 197))
                            path.addCurve(to: p(219, 197), control1: p(109, 173), control2: p(171, 173))
                        }
                        .stroke(Color.almaGold.opacity(0.28), lineWidth: 1)
                    }
                    .rotationEffect(spin(time, seconds: 120))

                    Circle()
                        .stroke(Color.almaGold.opacity(0.18), lineWidth: 1)
                        .frame(width: 208, height: 208)

                    // The pin does not turn with the globe: it is where the
                    // question is being answered, and a marker that wanders off
                    // the edge of the sphere every minute is a marker that means
                    // nothing.
                    let ripple = cycle(time, seconds: 4)
                    Circle()
                        .stroke(Color.almaStarFill.opacity(0.4 * (1 - ripple)), lineWidth: 1)
                        .frame(width: 28, height: 28)
                        .scaleEffect(0.6 + ripple * 1.6)
                        .position(x: 167, y: 101)
                        .frame(width: box, height: box)

                    Circle()
                        .fill(Color.almaStarFill)
                        .frame(width: 11.2, height: 11.2)
                        .position(x: 167, y: 101)
                        .frame(width: box, height: box)
                }
            }
        }
        .accessibilityHidden(true)
    }
}

// MARK: — VI · the ceremony

/// The chart being drawn. Two rings turning against each other, the aspect
/// grid, and one triangle that finds itself while you watch.
struct CeremonyArt: View {

    @State private var start: TimeInterval = .nan
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private let box: CGFloat = 340

    var body: some View {
        DesignBox(side: box) {
            CelestialTime { time in
                let progress = reduceMotion ? 1 : drawn(time, since: start, over: 3)
                ZStack {
                    Circle()
                        .stroke(Color.almaGold.opacity(0.16), lineWidth: 1)
                        .frame(width: 330, height: 330)
                        .rotationEffect(spin(time, seconds: 44, reversed: true))

                    Circle()
                        .stroke(Color.almaGold.opacity(0.42), lineWidth: 1)
                        .frame(width: 272, height: 272)
                        .overlay(alignment: .top) {
                            Circle()
                                .fill(Color.almaStarFill)
                                .frame(width: 7, height: 7)
                                .shadow(color: Color.almaStarFill.opacity(0.9), radius: 6)
                                .offset(y: -3.5)
                        }
                        .overlay(alignment: .bottomTrailing) {
                            Circle()
                                .fill(Color.almaGold)
                                .frame(width: 5, height: 5)
                                .shadow(color: Color.almaGold.opacity(0.9), radius: 4.5)
                                .offset(x: -14, y: -20)
                        }
                        .rotationEffect(spin(time, seconds: 36))

                    // The wheel itself, still: houses do not rotate, and a
                    // spinning aspect grid is a chart nobody could read.
                    Circle()
                        .stroke(Color.almaGold.opacity(0.55), lineWidth: 1)
                        .frame(width: 224, height: 224)
                    Circle()
                        .stroke(
                            Color.almaGoldDeep.opacity(0.5),
                            style: StrokeStyle(lineWidth: 1, dash: [2, 4])
                        )
                        .frame(width: 172, height: 172)
                    Circle()
                        .stroke(Color.almaGold.opacity(0.35), lineWidth: 1)
                        .frame(width: 88, height: 88)

                    DesignPath(box: box) { path, p in
                        path.move(to: p(170, 58)); path.addLine(to: p(170, 282))
                        path.move(to: p(58, 170)); path.addLine(to: p(282, 170))
                        path.move(to: p(90, 90)); path.addLine(to: p(250, 250))
                        path.move(to: p(250, 90)); path.addLine(to: p(90, 250))
                        path.move(to: p(170, 84)); path.addLine(to: p(256, 134))
                        path.move(to: p(170, 84)); path.addLine(to: p(84, 134))
                        path.move(to: p(256, 206)); path.addLine(to: p(170, 256))
                        path.move(to: p(84, 206)); path.addLine(to: p(170, 256))
                        path.move(to: p(256, 134)); path.addLine(to: p(256, 206))
                        path.move(to: p(84, 134)); path.addLine(to: p(84, 206))
                    }
                    .stroke(Color.almaGold.opacity(0.4), lineWidth: 0.7)

                    DesignPath(box: box) { path, p in
                        path.move(to: p(124, 116))
                        path.addLine(to: p(222, 208))
                        path.addLine(to: p(146, 228))
                        path.closeSubpath()
                    }
                    .trim(from: 0, to: progress)
                    .stroke(Color.almaGoldBright.opacity(0.85), lineWidth: 1)

                    Group {
                        Circle().fill(Color.almaStarFill).frame(width: 8, height: 8)
                            .position(x: 124, y: 116)
                        Circle().fill(Color.almaStarFill).frame(width: 8, height: 8)
                            .position(x: 222, y: 208)
                        Circle().fill(Color.almaStarFill).frame(width: 8, height: 8)
                            .position(x: 146, y: 228)
                    }
                    .frame(width: box, height: box)

                    AlmaPresence(size: 58, ring: false)
                }
            }
        }
        .onAppear {
            if start.isNaN { start = Date.timeIntervalSinceReferenceDate }
        }
        .accessibilityHidden(true)
    }
}

// MARK: — VIII · the offer

/// The mark, a halo and one ring going out. Half the height of the other
/// scenes, because the controls under it grew and the price must never be
/// below the fold.
struct OfferArt: View {

    private let box: CGFloat = 190

    var body: some View {
        DesignBox(side: box) {
            CelestialTime { time in
                ZStack {
                    Halo(diameter: 170, period: 7, time: time)

                    let ripple = cycle(time, seconds: 7)
                    Circle()
                        .stroke(Color.almaGoldBright.opacity(0.3 * (1 - ripple)), lineWidth: 1)
                        .frame(width: 92, height: 92)
                        .scaleEffect(0.7 + ripple * 0.9)

                    AlmaStar(size: 60)
                }
            }
        }
        .accessibilityHidden(true)
    }
}

#Preview("Journey art") {
    ScrollView {
        VStack(spacing: 0) {
            ConstellationArt().frame(height: 300)
            OrbitArt().frame(height: 300)
            DialArt().frame(height: 280)
            ClockArt().frame(height: 280)
            GlobeArt().frame(height: 300)
            CeremonyArt().frame(height: 360)
            OfferArt().frame(height: 150)
        }
    }
    .nightSky(.ceremony)
}
