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
struct NatalWheel: View {

    /// The natal payload — `placements`, `houses`, `angles`, `aspects`.
    let data: JSONValue

    private struct Body_: Identifiable {
        let name: String
        let glyph: String
        let longitude: Double
        var id: String { name }
    }

    var body: some View {
        Canvas { context, size in
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

            // ── the rings ──
            for radius in [outer, signBand] {
                context.stroke(
                    Path(ellipseIn: CGRect(
                        x: centre.x - radius, y: centre.y - radius,
                        width: radius * 2, height: radius * 2)),
                    with: .color(Color.almaGold.opacity(0.45)),
                    lineWidth: 1
                )
            }
            context.stroke(
                Path(ellipseIn: CGRect(
                    x: centre.x - aspectRing, y: centre.y - aspectRing,
                    width: aspectRing * 2, height: aspectRing * 2)),
                with: .color(Color.almaGold.opacity(0.18)),
                lineWidth: 1
            )

            // ── the twelve signs ──
            let signGlyphs = ["♈︎", "♉︎", "♊︎", "♋︎", "♌︎", "♍︎", "♎︎", "♏︎", "♐︎", "♑︎", "♒︎", "♓︎"]
            for index in 0..<12 {
                let start = Double(index) * 30
                var tick = Path()
                tick.move(to: point(start, radius: signBand))
                tick.addLine(to: point(start, radius: outer))
                context.stroke(tick, with: .color(Color.almaGold.opacity(0.35)), lineWidth: 1)

                let label = point(start + 15, radius: (outer + signBand) / 2)
                context.draw(
                    Text(verbatim: signGlyphs[index])
                        .font(.system(size: side * 0.045))
                        .foregroundStyle(Color.almaGoldBright.opacity(0.8)),
                    at: label
                )
            }

            // ── the houses, when the horizon exists ──
            if ascendant != nil, let houses = data["houses"]?.arrayValue {
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
                        spoke,
                        with: .color(Color.almaGold.opacity(cardinal ? 0.5 : 0.22)),
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
                                .foregroundStyle(Color.almaMuted3),
                            at: point(mid, radius: aspectRing * 0.9)
                        )
                    }
                }
            }

            // ── the bodies ──
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
            for body in bodies {
                let close = drawn.filter {
                    abs(($0.longitude - body.longitude + 180)
                        .truncatingRemainder(dividingBy: 360) - 180) < 6
                }.count
                drawn.append((body.longitude, close))
                let radius = planetRing - Double(close) * side * 0.045

                var tick = Path()
                tick.move(to: point(body.longitude, radius: signBand))
                tick.addLine(to: point(body.longitude, radius: signBand - side * 0.015))
                context.stroke(tick, with: .color(Color.almaStarFill.opacity(0.8)), lineWidth: 1)

                context.draw(
                    Text(verbatim: body.glyph)
                        .font(.system(size: side * 0.042))
                        .foregroundStyle(Color.almaStarFill),
                    at: point(body.longitude, radius: radius)
                )
            }

            // ── the aspects, major only ──
            if let aspects = data["aspects"]?.arrayValue {
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
                        line,
                        with: .color(
                            tense
                                ? Color.almaDisagree.opacity(0.35)
                                : Color.almaGold.opacity(0.30)),
                        lineWidth: 1
                    )
                }
            }
        }
        .aspectRatio(1, contentMode: .fit)
        .frame(maxWidth: .infinity)
        .accessibilityHidden(true)
    }
}
