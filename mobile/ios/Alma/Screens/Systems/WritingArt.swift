import SwiftUI

/// What the screen does while Alma writes — one drawing per system, alive.
///
/// The owner's verdict on the old state was exact: a small breathing dot under
/// «Alma пишет эту главу…» is not an event, and a chapter being written from a
/// real chart *is* one. So each system draws the thing it actually computes —
/// the natal wheel turning, transits overtaking natal points, two charts
/// circling each other — in the same hairline-gold language as the rest of the
/// product. Nothing here is somebody's data: every position is decorative and
/// deliberately unlabelled, so the drawing cannot lie about a chart while the
/// real one is being read.
///
/// One `TimelineView` clock per view; every element derives from `t` so the
/// eight stay one hand's work. Honors Reduce Motion by settling to a still
/// frame of the same drawing.
struct WritingArt: View {

    let system: SystemSlug

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var start = Date.timeIntervalSinceReferenceDate

    var body: some View {
        Group {
            if reduceMotion {
                canvas(at: 12.35)
            } else {
                TimelineView(.animation) { timeline in
                    canvas(at: timeline.date.timeIntervalSinceReferenceDate - start)
                }
            }
        }
        .frame(width: 260, height: 260)
        .accessibilityHidden(true)
    }

    private func canvas(at t: Double) -> some View {
        Canvas { context, size in
            let c = CGPoint(x: size.width / 2, y: size.height / 2)
            let r = min(size.width, size.height) / 2
            field(&context, c, r, t)
            switch system {
            case .natal: natal(&context, c, r, t)
            case .numerology: numerology(&context, c, r, t)
            case .birthCard: birthCard(&context, c, r, t)
            case .transits: transits(&context, c, r, t)
            case .solarReturn: solarReturn(&context, c, r, t)
            case .compatibility: compatibility(&context, c, r, t)
            case .astrocartography: astrocartography(&context, c, r, t)
            case .synthesis: synthesis(&context, c, r, t)
            }
        }
    }

    // MARK: — shared vocabulary

    private func ring(_ ctx: inout GraphicsContext, _ c: CGPoint, _ radius: CGFloat, alpha: Double, width: CGFloat = 1) {
        ctx.stroke(
            Path(ellipseIn: CGRect(x: c.x - radius, y: c.y - radius, width: radius * 2, height: radius * 2)),
            with: .color(.almaGold.opacity(alpha)),
            lineWidth: width
        )
    }

    private func at(_ c: CGPoint, _ radius: CGFloat, _ angle: Double) -> CGPoint {
        CGPoint(x: c.x + radius * cos(angle), y: c.y + radius * sin(angle))
    }

    private func star(_ ctx: inout GraphicsContext, _ p: CGPoint, _ size: CGFloat, glow: Double) {
        ctx.fill(
            Path(ellipseIn: CGRect(x: p.x - size * 2.2, y: p.y - size * 2.2, width: size * 4.4, height: size * 4.4)),
            with: .radialGradient(
                Gradient(colors: [Color.almaGoldBright.opacity(0.35 * glow), .clear]),
                center: p, startRadius: 0, endRadius: size * 2.2
            )
        )
        ctx.fill(
            Path(ellipseIn: CGRect(x: p.x - size, y: p.y - size, width: size * 2, height: size * 2)),
            with: .color(.almaStarFill.opacity(glow))
        )
    }

    /// The field every drawing sits in: sixteen twinkling motes, a dashed
    /// outer orbit turning one way and a fine tick-ring turning the other.
    /// Shared, because depth is what "expensive" looks like in motion — one
    /// figure on black is a diagram, a figure inside a sky is a place.
    private func field(_ ctx: inout GraphicsContext, _ c: CGPoint, _ r: CGFloat, _ t: Double) {
        var seed = UInt64(1469598103934665603)
        for byte in system.rawValue.utf8 { seed = (seed ^ UInt64(byte)) &* 1099511628211 }
        for i in 0..<16 {
            seed = seed &* 6364136223846793005 &+ 1442695040888963407
            let a = Double(seed % 6283) / 1000
            seed = seed &* 6364136223846793005 &+ 1442695040888963407
            let rad = r * (0.15 + CGFloat(seed % 1000) / 1000 * 0.95)
            let p = at(c, rad, a)
            let tw = 0.25 + 0.55 * abs(sin(t * (0.6 + Double(i % 5) * 0.23) + Double(i)))
            ctx.fill(
                Path(ellipseIn: CGRect(x: p.x - 1, y: p.y - 1, width: 2, height: 2)),
                with: .color(.almaStarFill.opacity(tw * 0.6))
            )
        }
        // The dashed orbit, drifting clockwise.
        var dashed = Path()
        dashed.addEllipse(in: CGRect(x: c.x - r * 1.0, y: c.y - r * 1.0, width: r * 2, height: r * 2))
        var style = StrokeStyle(lineWidth: 1, dash: [2, 9], dashPhase: CGFloat(t * 6))
        ctx.stroke(dashed, with: .color(.almaGold.opacity(0.22)), style: style)
        // The tick-ring, drifting the other way — sixty faint marks.
        for i in 0..<60 {
            let a = Double(i) * .pi / 30 - t * 0.05
            var tick = Path()
            tick.move(to: at(c, r * 0.995, a))
            tick.addLine(to: at(c, r * (i % 5 == 0 ? 0.955 : 0.975), a))
            ctx.stroke(tick, with: .color(.almaGold.opacity(i % 5 == 0 ? 0.28 : 0.14)), lineWidth: 1)
        }
        style.dash = []
    }

    /// The pen: a comet-point sweeping a slow circle under every drawing — the
    /// one element all eight share, because all eight are the same act.
    private func pen(_ ctx: inout GraphicsContext, _ c: CGPoint, _ r: CGFloat, _ t: Double) {
        let a = t * 0.9
        let p = at(c, r * 0.97, a)
        var trail = Path()
        trail.addArc(center: c, radius: r * 0.97,
                     startAngle: .radians(a - 0.9), endAngle: .radians(a), clockwise: false)
        ctx.stroke(trail, with: .linearGradient(
            Gradient(colors: [.clear, Color.almaGoldBright.opacity(0.5)]),
            startPoint: at(c, r * 0.97, a - 0.9), endPoint: p
        ), lineWidth: 1.4)
        star(&ctx, p, 2.4, glow: 1)
    }

    // MARK: — the eight

    /// The wheel, turning: houses fixed, planets moving, aspects flickering on
    /// when their angle is right — a chart assembling itself.
    private func natal(_ ctx: inout GraphicsContext, _ c: CGPoint, _ r: CGFloat, _ t: Double) {
        ring(&ctx, c, r * 0.96, alpha: 0.5)
        ring(&ctx, c, r * 0.78, alpha: 0.3)
        for i in 0..<12 {
            let a = Double(i) * .pi / 6
            var spoke = Path()
            spoke.move(to: at(c, r * 0.78, a))
            spoke.addLine(to: at(c, r * 0.96, a))
            ctx.stroke(spoke, with: .color(.almaGold.opacity(0.28)), lineWidth: 1)
        }
        let speeds: [Double] = [0.35, 0.22, 0.5, 0.16, 0.28]
        let radii: [CGFloat] = [0.62, 0.5, 0.68, 0.4, 0.56]
        var points: [CGPoint] = []
        for (i, speed) in speeds.enumerated() {
            let a = t * speed + Double(i) * 1.7
            let p = at(c, r * radii[i], a)
            points.append(p)
            star(&ctx, p, 2.6 + CGFloat(i % 3), glow: 0.9)
        }
        // Aspects: a line appears while two bodies are near 120° apart.
        for i in 0..<points.count {
            for j in (i + 1)..<points.count {
                let ai = t * speeds[i] + Double(i) * 1.7
                let aj = t * speeds[j] + Double(j) * 1.7
                let diff = abs(((ai - aj).truncatingRemainder(dividingBy: 2 * .pi)))
                let near = min(abs(diff - 2 * .pi / 3), abs(diff - 2 * .pi + 2 * .pi / 3))
                let glow = max(0, 1 - near / 0.35)
                if glow > 0 {
                    var line = Path()
                    line.move(to: points[i]); line.addLine(to: points[j])
                    ctx.stroke(line, with: .color(.almaGoldBright.opacity(0.5 * glow)), lineWidth: 1)
                }
            }
        }
        pen(&ctx, c, r, t)
    }

    /// Digits condensing out of orbit into the centre, one at a time.
    private func numerology(_ ctx: inout GraphicsContext, _ c: CGPoint, _ r: CGFloat, _ t: Double) {
        ring(&ctx, c, r * 0.9, alpha: 0.35)
        let phase = t.truncatingRemainder(dividingBy: 9)
        for n in 1...9 {
            let a = Double(n) * 2 * .pi / 9 - .pi / 2 + t * 0.1
            let active = abs(phase - Double(n - 1)) < 0.8
            let pull = active ? CGFloat(0.35 + 0.25 * abs(sin(t * 2))) : 0.72
            let p = at(c, r * pull, a)
            let text = Text(verbatim: "\(n)")
                .font(AlmaFonts.display(active ? 24 : 15, relativeTo: .title3))
                .foregroundStyle(Color.almaStarFill.opacity(active ? 1 : 0.35))
            ctx.draw(ctx.resolve(text), at: p)
        }
        star(&ctx, c, 3, glow: 0.5 + 0.5 * abs(sin(t * 2)))
        pen(&ctx, c, r, t)
    }

    /// A card turning in place — its face a star, its rhythm a slow flip.
    private func birthCard(_ ctx: inout GraphicsContext, _ c: CGPoint, _ r: CGFloat, _ t: Double) {
        ring(&ctx, c, r * 0.92, alpha: 0.25)
        let w = r * 0.62 * abs(cos(t * 0.8))
        let h = r * 0.98
        let card = Path(roundedRect: CGRect(x: c.x - w / 2, y: c.y - h / 2, width: max(w, 2), height: h), cornerRadius: 8)
        ctx.stroke(card, with: .color(.almaGold.opacity(0.6)), lineWidth: 1.2)
        if cos(t * 0.8) > 0.15 {
            star(&ctx, c, 4 * cos(t * 0.8), glow: Double(cos(t * 0.8)))
        }
        for i in 0..<4 {
            let a = t * 0.4 + Double(i) * .pi / 2
            star(&ctx, at(c, r * 0.8, a), 1.6, glow: 0.6)
        }
        pen(&ctx, c, r, t)
    }

    /// Two rings: the outer sky moving over fixed natal points — an overtaking
    /// that flares exactly when they align, which is what a transit is.
    private func transits(_ ctx: inout GraphicsContext, _ c: CGPoint, _ r: CGFloat, _ t: Double) {
        ring(&ctx, c, r * 0.55, alpha: 0.4)
        ring(&ctx, c, r * 0.92, alpha: 0.4)
        let natalAngles: [Double] = [0.4, 1.9, 3.6, 5.1]
        for a in natalAngles {
            star(&ctx, at(c, r * 0.55, a), 2.4, glow: 0.7)
        }
        for i in 0..<3 {
            let a = t * (0.5 - Double(i) * 0.14) + Double(i) * 2.2
            let p = at(c, r * 0.92, a)
            star(&ctx, p, 3, glow: 1)
            for n in natalAngles {
                let d = abs(((a - n).truncatingRemainder(dividingBy: 2 * .pi)))
                let near = min(d, 2 * .pi - d)
                let glow = max(0, 1 - near / 0.3)
                if glow > 0 {
                    var line = Path()
                    line.move(to: p); line.addLine(to: at(c, r * 0.55, n))
                    ctx.stroke(line, with: .color(.almaGoldBright.opacity(0.6 * glow)), lineWidth: 1.2)
                }
            }
        }
        pen(&ctx, c, r, t)
    }

    /// The Sun breathing, and one planet completing its year around it.
    private func solarReturn(_ ctx: inout GraphicsContext, _ c: CGPoint, _ r: CGFloat, _ t: Double) {
        let breath = 0.85 + 0.15 * sin(t * 1.4)
        for i in 0..<12 {
            let a = Double(i) * .pi / 6 + t * 0.05
            var ray = Path()
            ray.move(to: at(c, r * 0.3 * breath, a))
            ray.addLine(to: at(c, r * (0.42 + 0.05 * sin(t * 1.4 + Double(i))), a))
            ctx.stroke(ray, with: .color(.almaGoldBright.opacity(0.5)), lineWidth: 1)
        }
        star(&ctx, c, 9 * breath, glow: 1)
        ring(&ctx, c, r * 0.86, alpha: 0.35)
        let yearly = at(c, r * 0.86, t * 0.6 - .pi / 2)
        star(&ctx, yearly, 3, glow: 1)
        var trail = Path()
        trail.addArc(center: c, radius: r * 0.86,
                     startAngle: .radians(t * 0.6 - .pi / 2 - 1.2),
                     endAngle: .radians(t * 0.6 - .pi / 2), clockwise: false)
        ctx.stroke(trail, with: .linearGradient(
            Gradient(colors: [.clear, Color.almaGoldBright.opacity(0.45)]),
            startPoint: at(c, r * 0.86, t * 0.6 - .pi / 2 - 1.2), endPoint: yearly
        ), lineWidth: 1.2)
    }

    /// Two charts circling one another; the thread between them brightens as
    /// they close and thins as they part.
    private func compatibility(_ ctx: inout GraphicsContext, _ c: CGPoint, _ r: CGFloat, _ t: Double) {
        let spread = r * (0.34 + 0.1 * sin(t * 0.7))
        let a = t * 0.45
        let one = at(c, spread, a)
        let two = at(c, spread, a + .pi)
        ring(&ctx, one, r * 0.34, alpha: 0.4)
        ring(&ctx, two, r * 0.34, alpha: 0.4)
        star(&ctx, one, 3.4, glow: 1)
        star(&ctx, two, 3.4, glow: 1)
        let closeness = 1 - Double((spread - r * 0.24) / (r * 0.2))
        var thread = Path()
        thread.move(to: one)
        thread.addQuadCurve(to: two, control: CGPoint(x: c.x, y: c.y - r * 0.2))
        ctx.stroke(thread, with: .color(.almaGoldBright.opacity(0.25 + 0.45 * max(0, min(closeness, 1)))), lineWidth: 1.2)
        pen(&ctx, c, r, t)
    }

    /// Meridians of a slowly turning globe, and one bright line crossing the
    /// map — a place lighting where it lands.
    private func astrocartography(_ ctx: inout GraphicsContext, _ c: CGPoint, _ r: CGFloat, _ t: Double) {
        ring(&ctx, c, r * 0.9, alpha: 0.5)
        for i in 0..<5 {
            let phase = (t * 0.12 + Double(i) / 5).truncatingRemainder(dividingBy: 1)
            let w = r * 0.9 * CGFloat(abs(cos(phase * .pi)))
            let meridian = Path(ellipseIn: CGRect(x: c.x - w, y: c.y - r * 0.9, width: w * 2, height: r * 1.8))
            ctx.stroke(meridian, with: .color(.almaGold.opacity(0.22)), lineWidth: 1)
        }
        for dy in [-0.45, 0.0, 0.45] {
            let half = r * 0.9 * CGFloat((1 - dy * dy).squareRoot())
            var lat = Path()
            lat.move(to: CGPoint(x: c.x - half, y: c.y + r * 0.9 * CGFloat(dy)))
            lat.addLine(to: CGPoint(x: c.x + half, y: c.y + r * 0.9 * CGFloat(dy)))
            ctx.stroke(lat, with: .color(.almaGold.opacity(0.18)), lineWidth: 1)
        }
        let sweep = (t * 0.25).truncatingRemainder(dividingBy: 2) - 1
        let x = c.x + r * 0.9 * CGFloat(sweep)
        let half = r * 0.9 * CGFloat(max(0, (1 - sweep * sweep)).squareRoot())
        var line = Path()
        line.move(to: CGPoint(x: x, y: c.y - half))
        line.addLine(to: CGPoint(x: x, y: c.y + half))
        ctx.stroke(line, with: .color(.almaGoldBright.opacity(0.7)), lineWidth: 1.4)
        star(&ctx, CGPoint(x: x, y: c.y - half * 0.3), 2.6, glow: 1)
    }

    /// Eight threads pulling in from the rim to one point — the systems
    /// becoming one reading, with a bloom when they meet.
    private func synthesis(_ ctx: inout GraphicsContext, _ c: CGPoint, _ r: CGFloat, _ t: Double) {
        ring(&ctx, c, r * 0.94, alpha: 0.35)
        let pulse = (t * 0.5).truncatingRemainder(dividingBy: 1)
        for i in 0..<8 {
            let a = Double(i) * .pi / 4 + t * 0.06
            let rim = at(c, r * 0.94, a)
            var thread = Path()
            thread.move(to: rim)
            thread.addLine(to: c)
            ctx.stroke(thread, with: .color(.almaGold.opacity(0.22)), lineWidth: 1)
            star(&ctx, rim, 2, glow: 0.7)
            let travelled = at(c, r * 0.94 * CGFloat(1 - pulse), a)
            star(&ctx, travelled, 1.8, glow: Double(1 - pulse) * 0.9)
        }
        star(&ctx, c, 4 + 3 * CGFloat(pulse > 0.9 ? (1 - pulse) * 10 : 0), glow: 0.6 + 0.4 * sin(t * 2))
    }
}

#Preview {
    VStack(spacing: 0) {
        WritingArt(system: .natal)
    }
    .frame(maxWidth: .infinity, maxHeight: .infinity)
    .background(Color.almaNight)
}
