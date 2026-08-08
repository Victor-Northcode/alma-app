import SwiftUI

/// The chart itself, drawn — the thing every natal-chart product opens with
/// and this one did not have.
///
/// The reference the owner chose opens with the wheel, then the placements,
/// then the interpretations; Alma had the data and the words and no picture.
/// This is the picture: the twelve signs on the outer ring, the house cusps
/// when the birth time is known, every body at its real longitude, and the
/// major aspects drawn across the middle — all read from the same payload the
/// rest of the screen cites, so the wheel can never disagree with the text
/// beside it.
///
/// **Orientation.** The Ascendant sits at the left, as every printed chart has
/// it, and longitudes increase counter-clockwise. With no birth time there is
/// no Ascendant and no houses; the wheel then opens 0° Aries at the left and
/// simply omits the spokes — a thinner chart, honestly thinner, not a chart
/// with invented walls.
///
/// **Glyphs are allowed here and nowhere else.** The rest of the app spells
/// planets and signs out in words because a pill on the front page is read as
/// text. A wheel is a diagram: the glyph *is* the notation of the diagram, and
/// the words live in the placement list directly underneath.
///
/// **It draws itself, once.** The first two seconds are the wheel being
/// constructed in the order an astrologer would draw one — rings, signs,
/// houses, planets, aspects — the same ceremony `AlmaLaunch` opens with.
/// `TimelineView` is paused the moment the intro finishes, so the settled
/// wheel costs exactly what the static one did. Reduce Motion skips straight
/// to the settled chart.
struct NatalWheel: View {

    /// The natal payload — `placements`, `houses`, `angles`, `aspects`.
    let data: JSONValue

    /// How long the wheel takes to construct itself.
    private static let intro: TimeInterval = 2.0

    @State private var born: Date = .now
    @State private var settled = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private struct Body_: Identifiable {
        let name: String
        let glyph: String
        let longitude: Double
        var id: String { name }
    }

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 60.0, paused: settled)) { timeline in
            let raw = reduceMotion
                ? 1.0
                : min(1.0, timeline.date.timeIntervalSince(born) / Self.intro)
            // Ease-out cubic: the wheel arrives quickly and settles gently.
            let progress = 1 - pow(1 - raw, 3)
            wheel(progress: progress)
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
        .aspectRatio(1, contentMode: .fit)
        .frame(maxWidth: .infinity)
        .accessibilityHidden(true)
    }

    private func wheel(progress: Double) -> some View {
        Canvas { context, size in
            // Which stretch of the intro this element owns, as its own 0…1.
            func phase(_ from: Double, _ to: Double) -> Double {
                min(1, max(0, (progress - from) / (to - from)))
            }

            let side = min(size.width, size.height)
            let centre = CGPoint(x: size.width / 2, y: size.height / 2)
            let outer = side * 0.48
            let signBand = side * 0.40
            let planetRing = side * 0.31
            let aspectRing = side * 0.26

            let ascendant = data["angles"]?["ascendant"]?.doubleValue

            // Screen angle for an ecliptic longitude: the Ascendant (or 0°
            // Aries) on the left, the zodiac running counter-clockwise.
            func angle(_ longitude: Double) -> Double {
                (180 - (longitude - (ascendant ?? 0))) * .pi / 180
            }
            func point(_ longitude: Double, radius: Double) -> CGPoint {
                let a = angle(longitude)
                return CGPoint(x: centre.x + radius * cos(a), y: centre.y + radius * sin(a))
            }

            // ── the rings — each sweeps itself closed ──
            let ringSweep = phase(0.0, 0.35)
            for radius in [outer, signBand] {
                context.stroke(
                    Path(ellipseIn: CGRect(
                        x: centre.x - radius, y: centre.y - radius,
                        width: radius * 2, height: radius * 2))
                        .trimmedPath(from: 0, to: ringSweep),
                    with: .color(Color.almaGold.opacity(0.45)),
                    lineWidth: 1
                )
            }
            context.stroke(
                Path(ellipseIn: CGRect(
                    x: centre.x - aspectRing, y: centre.y - aspectRing,
                    width: aspectRing * 2, height: aspectRing * 2))
                    .trimmedPath(from: 0, to: ringSweep),
                with: .color(Color.almaGold.opacity(0.18)),
                lineWidth: 1
            )

            // ── the twelve signs, lighting up around the wheel ──
            let signGlyphs = ["♈︎", "♉︎", "♊︎", "♋︎", "♌︎", "♍︎", "♎︎", "♏︎", "♐︎", "♑︎", "♒︎", "♓︎"]
            for index in 0..<12 {
                let lit = phase(0.20 + Double(index) * 0.02, 0.40 + Double(index) * 0.02)
                guard lit > 0 else { continue }
                let start = Double(index) * 30
                var tick = Path()
                tick.move(to: point(start, radius: signBand))
                tick.addLine(to: point(start, radius: outer))
                context.stroke(
                    tick, with: .color(Color.almaGold.opacity(0.35 * lit)), lineWidth: 1)

                let label = point(start + 15, radius: (outer + signBand) / 2)
                context.draw(
                    Text(verbatim: signGlyphs[index])
                        .font(.system(size: side * 0.045))
                        .foregroundStyle(Color.almaGoldBright.opacity(0.8 * lit)),
                    at: label
                )
            }

            // ── the houses, when the horizon exists — spokes grow outward ──
            if ascendant != nil, let houses = data["houses"]?.arrayValue {
                let grown = phase(0.40, 0.65)
                if grown > 0 {
                    for house in houses {
                        guard let cusp = house["cusp"]?.doubleValue,
                              let number = house["number"]?.intValue else { continue }
                        var spoke = Path()
                        spoke.move(to: point(cusp, radius: aspectRing))
                        spoke.addLine(to: point(cusp, radius: signBand))
                        // The horizon and the meridian carry more weight than the
                        // intermediate cusps, exactly as a printed chart draws them.
                        let cardinal = [1, 4, 7, 10].contains(number)
                        context.stroke(
                            spoke.trimmedPath(from: 0, to: grown),
                            with: .color(
                                Color.almaGold.opacity((cardinal ? 0.5 : 0.22) * grown)),
                            lineWidth: cardinal ? 1.4 : 1
                        )
                        // The house number, just inside its own cusp.
                        if let next = houses.first(where: { $0["number"]?.intValue == number % 12 + 1 }),
                           let nextCusp = next["cusp"]?.doubleValue {
                            var span = nextCusp - cusp
                            if span < 0 { span += 360 }
                            let mid = cusp + span / 2
                            context.draw(
                                Text(verbatim: "\(number)")
                                    .font(.system(size: side * 0.028))
                                    .foregroundStyle(Color.almaMuted3.opacity(grown)),
                                at: point(mid, radius: aspectRing * 0.9)
                            )
                        }
                    }
                }
            }

            // ── the bodies — each planet takes its seat in zodiac order ──
            var bodies: [Body_] = []
            if let placements = data["placements"]?.objectValue {
                for (name, placement) in placements {
                    guard let longitude = placement["longitude"]?.doubleValue,
                          let glyph = placement["glyph"]?.stringValue else { continue }
                    bodies.append(Body_(name: name, glyph: glyph, longitude: longitude))
                }
            }
            bodies.sort { $0.longitude < $1.longitude }

            // Nudge glyphs apart when two bodies sit within a few degrees —
            // a stellium drawn honestly is a smudge, and a smudge reads as a
            // rendering bug rather than as three planets together.
            var drawn: [(longitude: Double, offset: Int)] = []
            for (order, body) in bodies.enumerated() {
                let close = drawn.filter {
                    abs(($0.longitude - body.longitude + 180)
                        .truncatingRemainder(dividingBy: 360) - 180) < 6
                }.count
                drawn.append((body.longitude, close))

                let step = bodies.count > 1 ? 0.25 / Double(bodies.count - 1) : 0
                let seated = phase(0.55 + Double(order) * step, 0.70 + Double(order) * step)
                guard seated > 0 else { continue }
                let radius = planetRing - Double(close) * side * 0.045

                var tick = Path()
                tick.move(to: point(body.longitude, radius: signBand))
                tick.addLine(to: point(body.longitude, radius: signBand - side * 0.015))
                context.stroke(
                    tick, with: .color(Color.almaStarFill.opacity(0.8 * seated)), lineWidth: 1)

                context.draw(
                    Text(verbatim: body.glyph)
                        .font(.system(size: side * 0.042 * (0.6 + 0.4 * seated)))
                        .foregroundStyle(Color.almaStarFill.opacity(seated)),
                    at: point(body.longitude, radius: radius)
                )
            }

            // ── the aspects, major only — the web across the middle, last ──
            if let aspects = data["aspects"]?.arrayValue {
                let woven = phase(0.78, 1.0)
                if woven > 0 {
                    let positions = Dictionary(
                        uniqueKeysWithValues: bodies.map { ($0.name, $0.longitude) })
                    for aspect in aspects {
                        guard aspect["major"]?.boolValue == true,
                              let first = aspect["first"]?.stringValue,
                              let second = aspect["second"]?.stringValue,
                              let from = positions[first], let to = positions[second]
                        else { continue }
                        let tense = aspect["harmony"]?.stringValue == "tense"
                        var line = Path()
                        line.move(to: point(from, radius: aspectRing))
                        line.addLine(to: point(to, radius: aspectRing))
                        context.stroke(
                            line.trimmedPath(from: 0, to: woven),
                            with: .color(
                                tense
                                    ? Color.almaDisagree.opacity(0.35 * woven)
                                    : Color.almaGold.opacity(0.30 * woven)),
                            lineWidth: 1
                        )
                    }
                }
            }
        }
    }
}
