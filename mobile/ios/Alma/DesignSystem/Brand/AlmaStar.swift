import SwiftUI

/// The mark: a four-pointed star, drawn by hand.
///
/// The path is the web app's `Star.tsx` verbatim, point for point, on the same
/// 64×64 grid — thick arms, short points, and one arm a fraction off axis so it
/// never reads as a generated sparkle. It is not an SF Symbol and it is not
/// `Image(systemName: "sparkle")`: every product in this category ships that
/// glyph, and it is the single fastest way to look like all of them.
///
/// The rules from the brand book, restated because they are easy to break in
/// SwiftUI where any view can be rotated by anything: never in a circle, never
/// rotated, never used as a bullet, never used as a loading indicator.
struct AlmaStar: View {

    enum Variant: Sendable {
        /// On night. The default.
        case gold
        /// On parchment — a darker leaf, so it does not glare on the light
        /// surface.
        case ink
        /// One flat fill, for sizes under about 16pt where a four-stop gradient
        /// is invisible and only costs a layer.
        case flat
    }

    var size: CGFloat = 26
    var variant: Variant = .gold

    var body: some View {
        ZStack {
            switch variant {
            case .flat:
                StarBody()
                    .fill(Color(hex: 0xE0C077))
            case .gold:
                StarBody()
                    .fill(AlmaGradient.goldLeaf)
                    .overlay(StarBody().stroke(Color(hex: 0x7A6129), lineWidth: 0.8 * size / 64))
                StarFacet()
                    .fill(Color(hex: 0x8A6F2E).opacity(0.16))
            case .ink:
                StarBody()
                    .fill(
                        LinearGradient(
                            stops: [
                                .init(color: Color(hex: 0xC2A868), location: 0.00),
                                .init(color: Color(hex: 0x94773A), location: 0.42),
                                .init(color: Color(hex: 0x5E4B20), location: 1.00),
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .overlay(StarBody().stroke(Color(hex: 0x4A3A16), lineWidth: 0.9 * size / 64))
                StarFacet()
                    .fill(Color(hex: 0x3A2D11).opacity(0.28))
            }
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

/// The outline, on the 64×64 grid the SVG was drawn on.
private struct StarBody: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        let s = Scaler(rect)
        path.move(to: s.p(32.4, 6.4))
        path.addQuadCurve(to: s.p(41.2, 26.6), control: s.p(35.6, 22.8))
        path.addQuadCurve(to: s.p(57.8, 31.9), control: s.p(47.0, 30.0))
        path.addQuadCurve(to: s.p(41.0, 37.4), control: s.p(47.0, 34.0))
        path.addQuadCurve(to: s.p(32.0, 57.6), control: s.p(35.4, 41.0))
        path.addQuadCurve(to: s.p(23.0, 37.6), control: s.p(28.6, 41.2))
        path.addQuadCurve(to: s.p(6.2, 32.1), control: s.p(17.0, 34.2))
        path.addQuadCurve(to: s.p(23.2, 26.4), control: s.p(17.2, 29.8))
        path.addQuadCurve(to: s.p(32.4, 6.4), control: s.p(28.8, 22.6))
        path.closeSubpath()
        return path
    }
}

/// The darker facet down the vertical arm — what makes the mark read as struck
/// metal rather than as a flat silhouette.
private struct StarFacet: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        let s = Scaler(rect)
        path.move(to: s.p(32.2, 13.0))
        path.addQuadCurve(to: s.p(37.6, 29.8), control: s.p(34.4, 26.6))
        path.addQuadCurve(to: s.p(32.0, 51.0), control: s.p(34.2, 34.8))
        path.addQuadCurve(to: s.p(26.6, 30.0), control: s.p(29.8, 34.8))
        path.addQuadCurve(to: s.p(32.2, 13.0), control: s.p(30.0, 26.8))
        path.closeSubpath()
        return path
    }
}

/// Maps the SVG's 64-unit grid onto whatever rect the shape is handed.
private struct Scaler {
    let rect: CGRect
    init(_ rect: CGRect) { self.rect = rect }

    func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint {
        CGPoint(
            x: rect.minX + x / 64 * rect.width,
            y: rect.minY + y / 64 * rect.height
        )
    }
}

/// Mark plus word. The tracking is .34em with a matching leading pad, which is
/// what keeps ALMA optically centred under wide letterspacing — without it the
/// trailing space after the final A pulls the word left.
struct AlmaWordmark: View {
    var size: CGFloat = 19
    var starSize: CGFloat?

    private var tracking: CGFloat { size * 0.34 }

    var body: some View {
        HStack(spacing: 11) {
            AlmaStar(size: starSize ?? (size * 1.35))
            Text(verbatim: "ALMA")
                .font(AlmaFonts.display(size, relativeTo: .headline))
                .tracking(tracking)
                .padding(.leading, tracking)
                .foregroundStyle(Color.almaInkLight)
        }
        .accessibilityElement()
        .accessibilityLabel(Text(verbatim: "Alma"))
    }
}

/// Alma's presence — the warm point of light that stands in for her.
///
/// Three sizes and no others: 96 in the ceremony, 56 in a conversation, 24 in
/// the tab bar. The ring is dropped below 56 because at 24 points a 1pt ring
/// around a soft glow is just a smudge.
struct AlmaPresence: View {

    var size: CGFloat = 56
    var ring: Bool = true

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var showsRing: Bool { ring && size >= 56 }
    private var outer: CGFloat { showsRing ? size * 1.5 : size }

    var body: some View {
        ZStack {
            if showsRing && !reduceMotion {
                // The ripple is the one place a loop is allowed to be visible:
                // it is Alma listening, and stillness there reads as the app
                // having hung.
                TimelineView(.animation) { timeline in
                    let t = (timeline.date.timeIntervalSinceReferenceDate / 8)
                        .truncatingRemainder(dividingBy: 1)
                    Circle()
                        .strokeBorder(Color.almaGoldBright.opacity(0.3 * (1 - t)), lineWidth: 1)
                        .scaleEffect(0.7 + t * 0.8)
                }
            }

            glow
        }
        .frame(width: outer, height: outer)
        .accessibilityHidden(true)
    }

    private var glow: some View {
        Circle()
            .fill(
                RadialGradient(
                    stops: [
                        .init(color: Color(hex: 0xFFF6DF), location: 0.00),
                        .init(color: Color(hex: 0xF1DFAE), location: 0.34),
                        .init(color: Color.almaGold.opacity(0.45), location: 0.64),
                        .init(color: .clear, location: 0.80),
                    ],
                    center: UnitPoint(x: 0.42, y: 0.38),
                    startRadius: 0,
                    endRadius: size / 2
                )
            )
            .frame(width: size, height: size)
            .shadow(color: Color.almaGoldBright.opacity(0.34), radius: size * 0.27)
    }
}

#Preview("Mark") {
    VStack(spacing: 40) {
        AlmaStar(size: 64)
        AlmaWordmark(size: 22)
        AlmaPresence(size: 96)
    }
    .frame(maxWidth: .infinity, maxHeight: .infinity)
    .nightSky(.ceremony)
}
