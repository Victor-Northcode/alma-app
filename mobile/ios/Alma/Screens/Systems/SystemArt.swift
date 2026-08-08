import SwiftUI

/// One hero diagram per system — the picture the natal wheel set the bar for.
///
/// The natal screen opens with its chart drawing itself, and the other seven
/// systems opened with a table of contents. This file closes that gap, under
/// the same law the wheel obeys: **everything here is read from the system's
/// own payload.** A date on the transit ring is a real `exact`, a line on the
/// map is a real computed meridian, a number in the life ring is this person's
/// pinnacle. When a datum is absent, its stroke is simply not drawn — a
/// thinner picture, honestly thinner.
///
/// Every diagram constructs itself over two seconds in the wheel's manner and
/// then the `TimelineView` pauses, so a settled diagram costs what a static
/// one would. Reduce Motion skips straight to the settled picture.
struct SystemHeroArt: View {

    let system: SystemSlug
    let data: JSONValue
    /// The account owner's age in whole years, when the client knows the
    /// birth date — the "you are here" mark on the numerology life ring.
    var age: Int? = nil

    var body: some View {
        switch system {
        case .natal:
            // The wheel already lives on the natal screen.
            EmptyView()
        case .solarReturn:
            // The return *is* a chart — the same wheel, this year's sky.
            if let chart = data["chart"] {
                NatalWheel(data: chart)
                    .padding(.vertical, 6)
            }
        case .compatibility:
            // The relationship's own sky, as the real wheel. The Davison chart
            // when both birth times are known; the composite positions when
            // they are not — a thinner chart without houses or angles, which
            // is exactly what an unknown hour honestly leaves.
            if let chart = relationshipChart {
                NatalWheel(data: chart)
                    .padding(.vertical, 6)
            }
        case .transits:
            SelfDrawing { TransitYearRing(data: data, progress: $0) }
        case .astrocartography:
            SelfDrawing { LinesMapArt(data: data, progress: $0) }
        case .numerology:
            SelfDrawing { NumerologyRing(data: data, age: age, progress: $0) }
        case .birthCard:
            SelfDrawing { BirthCardArt(data: data, progress: $0) }
        case .synthesis:
            SelfDrawing { SynthesisStar(data: data, progress: $0) }
        }
    }

    /// `davison` carries its angles at the top level; the wheel expects them
    /// under `angles`. Reassembled, not invented — every value is the payload's.
    ///
    /// Without both birth times there is no Davison chart, and the fallback is
    /// the `composite` block: bare midpoint longitudes. The glyphs added to
    /// them are the same notation the engine prints everywhere else — writing
    /// ☽ next to the moon's own longitude is spelling, not invention.
    private var relationshipChart: JSONValue? {
        if let davison = data["davison"], let placements = davison["placements"] {
            var chart: [String: JSONValue] = ["placements": placements]
            var angles: [String: JSONValue] = [:]
            if let asc = davison["ascendant"] { angles["ascendant"] = asc }
            if let mc = davison["midheaven"] { angles["midheaven"] = mc }
            if !angles.isEmpty { chart["angles"] = .object(angles) }
            return .object(chart)
        }

        guard let composite = data["composite"]?.objectValue else { return nil }
        let glyphs: [String: String] = [
            "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀", "mars": "♂",
            "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆",
            "pluto": "♇", "true_node": "☊", "lilith": "⚸", "chiron": "⚷",
        ]
        var placements: [String: JSONValue] = [:]
        for (name, value) in composite {
            guard let glyph = glyphs[name], let longitude = value.doubleValue else { continue }
            placements[name] = .object([
                "longitude": .number(longitude),
                "glyph": .string(glyph),
            ])
        }
        guard !placements.isEmpty else { return nil }
        var chart: [String: JSONValue] = ["placements": .object(placements)]
        if let asc = composite["ascendant"]?.doubleValue {
            chart["angles"] = .object(["ascendant": .number(asc)])
        }
        return .object(chart)
    }
}

// MARK: — the shared intro clock

/// The wheel's two-second construction, as a reusable frame: drives an eased
/// 0…1 progress through its content once, then pauses the timeline for good.
private struct SelfDrawing<Content: View>: View {

    private static var intro: TimeInterval { 2.0 }

    @ViewBuilder let content: (Double) -> Content

    @State private var born: Date = .now
    @State private var settled = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 60.0, paused: settled)) { timeline in
            let raw = reduceMotion
                ? 1.0
                : min(1.0, timeline.date.timeIntervalSince(born) / Self.intro)
            content(1 - pow(1 - raw, 3))
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
    }
}

/// Which stretch of the intro an element owns, as its own 0…1.
private func phase(_ progress: Double, _ from: Double, _ to: Double) -> Double {
    min(1, max(0, (progress - from) / (to - from)))
}

/// "2026-08-08T10:51+00:00" → the calendar day. Seconds are absent from the
/// wire format, so only the date part is parsed — a year ring cannot show a
/// minute anyway.
private func calendarDay(_ iso: String?) -> Date? {
    guard let iso, iso.count >= 10 else { return nil }
    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd"
    formatter.timeZone = TimeZone(identifier: "UTC")
    return formatter.date(from: String(iso.prefix(10)))
}

// MARK: — transits: the year as a ring

/// The 365-day window as a circle, with every contact drawn as an arc from the
/// day it enters orb to the day it leaves. "Now" is the needle at the top;
/// what is close is what is about to happen. Square and opposition arcs carry
/// the one non-gold accent, exactly as the aspect lines in the wheel do.
private struct TransitYearRing: View {

    let data: JSONValue
    let progress: Double

    private struct Arc: Identifiable {
        let id = UUID()
        let glyph: String
        let start: Double   // 0…1 of the year
        let end: Double
        let tense: Bool
        let weight: Double
    }

    var body: some View {
        Canvas { context, size in
            let side = min(size.width, size.height)
            let centre = CGPoint(x: size.width / 2, y: size.height / 2)
            let ring = side * 0.44

            func point(_ fraction: Double, radius: Double) -> CGPoint {
                let a = (fraction * 360 - 90) * .pi / 180
                return CGPoint(x: centre.x + radius * cos(a), y: centre.y + radius * sin(a))
            }

            // The year itself sweeps closed.
            let sweep = phase(progress, 0, 0.3)
            var year = Path()
            year.addArc(
                center: centre, radius: ring,
                startAngle: .degrees(-90), endAngle: .degrees(-90 + 360 * sweep),
                clockwise: false)
            context.stroke(year, with: .color(Color.almaGold.opacity(0.4)), lineWidth: 1)

            // Twelve month ticks light up around it.
            for month in 0..<12 {
                let lit = phase(progress, 0.1 + Double(month) * 0.02, 0.3 + Double(month) * 0.02)
                guard lit > 0 else { continue }
                let f = Double(month) / 12
                var tick = Path()
                tick.move(to: point(f, radius: ring - side * 0.012))
                tick.addLine(to: point(f, radius: ring + side * 0.012))
                context.stroke(tick, with: .color(Color.almaGold.opacity(0.35 * lit)), lineWidth: 1)
            }

            // The contacts, strongest-first, stacked inward one band each.
            let arcs = self.arcs
            let step = side * 0.032
            for (index, arc) in arcs.enumerated() {
                let grown = phase(progress, 0.3 + Double(index) * 0.05, 0.55 + Double(index) * 0.05)
                guard grown > 0 else { continue }
                let radius = ring - side * 0.05 - Double(index) * step
                let span = max(arc.end - arc.start, 0.004)
                var path = Path()
                path.addArc(
                    center: centre, radius: radius,
                    startAngle: .degrees(arc.start * 360 - 90),
                    endAngle: .degrees((arc.start + span * grown) * 360 - 90),
                    clockwise: false)
                let colour = arc.tense ? Color.almaDisagree : Color.almaGold
                context.stroke(
                    path,
                    with: .color(colour.opacity(0.30 + 0.5 * arc.weight)),
                    lineWidth: 2)

                let glyphAt = point(arc.start + span / 2, radius: radius)
                context.draw(
                    Text(verbatim: arc.glyph)
                        .font(.system(size: side * 0.035))
                        .foregroundStyle(Color.almaStarFill.opacity(grown)),
                    at: glyphAt)
            }

            // The needle: now, at the top, drawn last.
            let armed = phase(progress, 0.85, 1)
            if armed > 0 {
                var needle = Path()
                needle.move(to: point(0, radius: ring - side * 0.30))
                needle.addLine(to: point(0, radius: ring + side * 0.02))
                context.stroke(
                    needle, with: .color(Color.almaGoldBright.opacity(0.9 * armed)),
                    lineWidth: 1.2)
                let head = point(0, radius: ring + side * 0.045)
                context.draw(
                    Text(verbatim: "☉")
                        .font(.system(size: side * 0.04))
                        .foregroundStyle(Color.almaGoldBright.opacity(armed)),
                    at: head)
            }
        }
        .aspectRatio(1, contentMode: .fit)
        .frame(maxWidth: .infinity)
        .accessibilityHidden(true)
    }

    /// Active contacts first, then the heaviest of what is coming — at most
    /// nine bands, because a ring with thirty arcs is a smudge, and the rows
    /// below the picture list everything anyway.
    private var arcs: [Arc] {
        guard let from = calendarDay(data["window"]?["from"]?.stringValue) else { return [] }
        let days = data["window"]?["days"]?.doubleValue ?? 365

        func fraction(_ iso: String?) -> Double? {
            guard let day = calendarDay(iso) else { return nil }
            return max(0, min(1, day.timeIntervalSince(from) / (days * 86400)))
        }
        func arc(_ contact: JSONValue) -> Arc? {
            guard let exact = fraction(contact["exact"]?.stringValue) else { return nil }
            let start = fraction(contact["enters"]?.stringValue) ?? exact
            let end = fraction(contact["leaves"]?.stringValue) ?? min(exact + 0.02, 1)
            let aspect = contact["aspect"]?.stringValue ?? ""
            return Arc(
                glyph: contact["glyph"]?.stringValue ?? "·",
                start: start, end: max(end, start),
                tense: aspect == "square" || aspect == "opposition",
                weight: contact["weight"]?.doubleValue ?? 0.3)
        }

        let active = (data["active"]?.arrayValue ?? []).compactMap(arc)
        let upcoming = (data["upcoming"]?.arrayValue ?? [])
            .compactMap(arc)
            .sorted { $0.weight > $1.weight }
        return Array((active + upcoming).prefix(9))
    }
}

// MARK: — astrocartography: the lines on the earth

/// An equirectangular graticule with every computed planetary line drawn at
/// its real coordinates, and the birthplace as the one bright star. There is
/// deliberately no coastline: a coastline would be decoration, the lines are
/// the calculation.
private struct LinesMapArt: View {

    let data: JSONValue
    let progress: Double

    var body: some View {
        Canvas { context, size in
            let w = size.width
            let h = size.height

            func project(lat: Double, lon: Double) -> CGPoint {
                CGPoint(x: (lon + 180) / 360 * w, y: (66 - lat) / 132 * h)
            }

            // The graticule sketches itself first.
            let grid = phase(progress, 0, 0.35)
            for i in 0...12 {
                let x = Double(i) / 12 * w
                var meridian = Path()
                meridian.move(to: CGPoint(x: x, y: 0))
                meridian.addLine(to: CGPoint(x: x, y: h * grid))
                context.stroke(
                    meridian, with: .color(Color.almaGold.opacity(0.10)), lineWidth: 0.5)
            }
            for i in 0...4 {
                let y = Double(i) / 4 * h
                var parallel = Path()
                parallel.move(to: CGPoint(x: 0, y: y))
                parallel.addLine(to: CGPoint(x: w * grid, y: y))
                context.stroke(
                    parallel,
                    with: .color(Color.almaGold.opacity(i == 2 ? 0.22 : 0.10)),
                    lineWidth: i == 2 ? 0.8 : 0.5)
            }

            // The lines, each tracing itself top to bottom. Luminaries bright,
            // the rest quiet — the same hierarchy the chapter uses.
            let lines = data["lines"]?.arrayValue ?? []
            for (index, line) in lines.enumerated() {
                let drawn = phase(
                    progress,
                    0.2 + Double(index % 12) * 0.03,
                    0.65 + Double(index % 12) * 0.03)
                guard drawn > 0 else { continue }
                let points = line["points"]?.arrayValue ?? []
                guard points.count > 1 else { continue }
                let body = line["body"]?.stringValue ?? ""
                let luminary = body == "sun" || body == "moon"

                var path = Path()
                let visible = max(2, Int(Double(points.count) * drawn))
                for (i, p) in points.prefix(visible).enumerated() {
                    guard let lat = p["lat"]?.doubleValue,
                          let lon = p["lon"]?.doubleValue else { continue }
                    let at = project(lat: lat, lon: lon)
                    if i == 0 { path.move(to: at) } else { path.addLine(to: at) }
                }
                context.stroke(
                    path,
                    with: .color(
                        luminary
                            ? Color.almaGoldBright.opacity(0.5)
                            : Color.almaStarFill.opacity(0.16)),
                    lineWidth: luminary ? 1.1 : 0.6)
            }

            // The birthplace, last: one star where this person began.
            if let lat = data["birthplace"]?["latitude"]?.doubleValue,
               let lon = data["birthplace"]?["longitude"]?.doubleValue {
                let lit = phase(progress, 0.8, 1)
                if lit > 0 {
                    let at = project(lat: lat, lon: lon)
                    let r = 3.5 * lit
                    for (dx, dy) in [(r * 2.2, 0.0), (-r * 2.2, 0.0), (0.0, r * 2.2), (0.0, -r * 2.2)] {
                        var ray = Path()
                        ray.move(to: at)
                        ray.addLine(to: CGPoint(x: at.x + dx, y: at.y + dy))
                        context.stroke(
                            ray, with: .color(Color.almaGoldBright.opacity(0.8 * lit)),
                            lineWidth: 0.8)
                    }
                    context.fill(
                        Path(ellipseIn: CGRect(x: at.x - r / 2, y: at.y - r / 2, width: r, height: r)),
                        with: .color(Color.almaStarFill.opacity(lit)))
                    context.stroke(
                        Path(ellipseIn: CGRect(
                            x: at.x - r * 2.6, y: at.y - r * 2.6,
                            width: r * 5.2, height: r * 5.2)),
                        with: .color(Color.almaGold.opacity(0.4 * lit)),
                        lineWidth: 0.7)
                }
            }
        }
        .aspectRatio(1.9, contentMode: .fit)
        .frame(maxWidth: .infinity)
        .accessibilityHidden(true)
    }
}

// MARK: — numerology: the life as a ring

/// A life drawn as one circle: the four pinnacles as the outer band, the
/// three cycles as the inner, each segment carrying its own number, and the
/// life path in the centre — with the quiet gold breath master numbers get.
/// When the client knows the birth date, a tick marks where in all of it this
/// person is standing today.
private struct NumerologyRing: View {

    let data: JSONValue
    let age: Int?
    let progress: Double

    var body: some View {
        Canvas { context, size in
            let side = min(size.width, size.height)
            let centre = CGPoint(x: size.width / 2, y: size.height / 2)

            let span = lifeSpan
            func angle(_ years: Double) -> Double { (years / span) * 360 - 90 }
            func point(_ years: Double, radius: Double) -> CGPoint {
                let a = angle(years) * .pi / 180
                return CGPoint(x: centre.x + radius * cos(a), y: centre.y + radius * sin(a))
            }

            func band(
                _ segments: [(number: Int, from: Double, to: Double)],
                radius: Double, colour: Color, opening: Double, upTo: Double
            ) {
                for (index, segment) in segments.enumerated() {
                    let grown = phase(
                        progress,
                        opening + Double(index) * 0.06,
                        upTo + Double(index) * 0.06)
                    guard grown > 0 else { continue }
                    // A hair of a gap between segments, so they read as chapters
                    // of a life rather than one unbroken line.
                    let from = segment.from + span * 0.006
                    let to = segment.from + (segment.to - segment.from - span * 0.006) * grown
                    var arc = Path()
                    arc.addArc(
                        center: centre, radius: radius,
                        startAngle: .degrees(angle(from)),
                        endAngle: .degrees(angle(to)),
                        clockwise: false)
                    context.stroke(arc, with: .color(colour.opacity(0.55)), lineWidth: 1.6)

                    let mid = (segment.from + segment.to) / 2
                    context.draw(
                        Text(verbatim: "\(segment.number)")
                            .font(AlmaFonts.display(side * 0.045, relativeTo: .footnote))
                            .foregroundStyle(colour.opacity(grown)),
                        at: point(mid, radius: radius + side * 0.045))
                }
            }

            band(pinnacles, radius: side * 0.40, colour: .almaGold, opening: 0.1, upTo: 0.4)
            band(cycles, radius: side * 0.28, colour: .almaStarFill, opening: 0.3, upTo: 0.6)

            // Today's tick — only when the age is actually known.
            if let age {
                let lit = phase(progress, 0.75, 0.9)
                if lit > 0 {
                    var tick = Path()
                    tick.move(to: point(Double(age), radius: side * 0.245))
                    tick.addLine(to: point(Double(age), radius: side * 0.44))
                    context.stroke(
                        tick, with: .color(Color.almaGoldBright.opacity(0.8 * lit)),
                        lineWidth: 1)
                }
            }

            // The life path, breathing in at the centre.
            if let path = data["life_path"]?.intValue {
                let seated = phase(progress, 0.45, 0.8)
                if seated > 0 {
                    let master = [11, 22, 33].contains(path)
                    if master {
                        // The aura only a master number earns.
                        context.stroke(
                            Path(ellipseIn: CGRect(
                                x: centre.x - side * 0.13, y: centre.y - side * 0.13,
                                width: side * 0.26, height: side * 0.26)),
                            with: .color(Color.almaGold.opacity(0.30 * seated)),
                            lineWidth: 0.8)
                    }
                    context.draw(
                        Text(verbatim: "\(path)")
                            .font(AlmaFonts.display(side * 0.17 * (0.7 + 0.3 * seated), relativeTo: .largeTitle))
                            .foregroundStyle(Color.almaInkLight.opacity(seated)),
                        at: centre)
                }
            }

            // The personal year, quietly under the centre — the number that
            // changes, against the number that never does.
            if let year = data["personal"]?["year"]?.intValue {
                let lit = phase(progress, 0.85, 1)
                if lit > 0 {
                    context.draw(
                        Text(verbatim: "· \(year) ·")
                            .font(AlmaFonts.display(side * 0.05, relativeTo: .footnote))
                            .foregroundStyle(Color.almaGold.opacity(0.7 * lit)),
                        at: CGPoint(x: centre.x, y: centre.y + side * 0.15))
                }
            }
        }
        .aspectRatio(1, contentMode: .fit)
        .frame(maxWidth: .infinity)
        .accessibilityHidden(true)
    }

    private var lifeSpan: Double {
        let last = (data["pinnacles"]?.arrayValue ?? [])
            .compactMap { $0["ends_age"]?.doubleValue }.max() ?? 0
        return max(last + 9, 81, Double((age ?? 0) + 9))
    }

    private func segments(_ key: String) -> [(number: Int, from: Double, to: Double)] {
        (data[key]?.arrayValue ?? []).compactMap { item in
            guard let number = item["number"]?.intValue,
                  let from = item["starts_age"]?.doubleValue else { return nil }
            let to = item["ends_age"]?.doubleValue ?? lifeSpan
            return (number, from, to)
        }
    }

    private var pinnacles: [(number: Int, from: Double, to: Double)] { segments("pinnacles") }
    private var cycles: [(number: Int, from: Double, to: Double)] { segments("cycles") }
}

// MARK: — the birth card

/// The card itself: the personality card's frame drawing itself closed around
/// its numeral, the soul card standing quietly behind, and the 22-year cycle
/// as a ring of points under both with this year's position lit.
private struct BirthCardArt: View {

    let data: JSONValue
    let progress: Double

    var body: some View {
        Canvas { context, size in
            let side = min(size.width, size.height)
            let centre = CGPoint(x: size.width / 2, y: size.height / 2 - side * 0.04)
            let cardW = side * 0.38
            let cardH = cardW * 1.55

            func cardFrame(at: CGPoint, w: Double, h: Double, trim: Double, alpha: Double) {
                guard trim > 0 else { return }
                let rect = CGRect(x: at.x - w / 2, y: at.y - h / 2, width: w, height: h)
                let frame = Path(roundedRect: rect, cornerRadius: w * 0.07)
                    .trimmedPath(from: 0, to: trim)
                context.stroke(frame, with: .color(Color.almaGold.opacity(alpha)), lineWidth: 1.2)
                let inner = CGRect(
                    x: rect.minX + w * 0.05, y: rect.minY + w * 0.05,
                    width: w * 0.9, height: h - w * 0.1)
                context.stroke(
                    Path(roundedRect: inner, cornerRadius: w * 0.045).trimmedPath(from: 0, to: trim),
                    with: .color(Color.almaGold.opacity(alpha * 0.4)),
                    lineWidth: 0.6)
            }

            // The soul card first, behind and to the side — the quieter twin.
            if let soul = data["soul"]?["numeral"]?.stringValue,
               data["is_same_card"]?.boolValue != true {
                let shown = phase(progress, 0.35, 0.7)
                let at = CGPoint(x: centre.x + cardW * 0.62, y: centre.y + cardH * 0.10)
                cardFrame(at: at, w: cardW * 0.72, h: cardH * 0.72, trim: shown, alpha: 0.35)
                if shown > 0.5 {
                    context.draw(
                        Text(verbatim: soul)
                            .font(AlmaFonts.display(side * 0.07, relativeTo: .title3))
                            .foregroundStyle(Color.almaGold.opacity(0.5 * (shown - 0.5) * 2)),
                        at: at)
                }
            }

            // The personality card draws itself closed.
            let frame = phase(progress, 0, 0.5)
            let mainAt = CGPoint(x: centre.x - cardW * 0.18, y: centre.y)
            cardFrame(at: mainAt, w: cardW, h: cardH, trim: frame, alpha: 0.8)

            if let numeral = data["personality"]?["numeral"]?.stringValue {
                let seated = phase(progress, 0.4, 0.75)
                if seated > 0 {
                    context.draw(
                        Text(verbatim: numeral)
                            .font(AlmaFonts.display(side * 0.13 * (0.8 + 0.2 * seated), relativeTo: .largeTitle))
                            .foregroundStyle(Color.almaInkLight.opacity(seated)),
                        at: mainAt)
                }
                // The element's own stroke under the numeral.
                if let element = data["personality"]?["element"]?.stringValue {
                    let drawn = phase(progress, 0.6, 0.9)
                    elementMotif(
                        element, context: &context,
                        at: CGPoint(x: mainAt.x, y: mainAt.y + cardH * 0.28),
                        width: cardW * 0.4, progress: drawn)
                }
            }

            // The 22-year cycle, with this year lit.
            let cycle = phase(progress, 0.7, 1)
            if cycle > 0 {
                let ringY = centre.y + cardH * 0.72
                let position = data["year"]?["position_in_cycle"]?.intValue
                for i in 0..<22 {
                    let lit = Double(i) / 22 <= cycle
                    guard lit else { continue }
                    let x = centre.x + (Double(i) - 10.5) * side * 0.032
                    let current = position == i
                    let r: Double = current ? 3.4 : 1.6
                    context.fill(
                        Path(ellipseIn: CGRect(x: x - r / 2, y: ringY - r / 2, width: r, height: r)),
                        with: .color(
                            current
                                ? Color.almaGoldBright.opacity(cycle)
                                : Color.almaGold.opacity(0.35 * cycle)))
                }
            }
        }
        .aspectRatio(1.25, contentMode: .fit)
        .frame(maxWidth: .infinity)
        .accessibilityHidden(true)
    }

    /// One gesture per element — arcs for air, waves for water, flames for
    /// fire, ground for earth. Nothing zodiacal: the card's element is the
    /// card's own vocabulary.
    private func elementMotif(
        _ element: String, context: inout GraphicsContext,
        at: CGPoint, width: Double, progress: Double
    ) {
        guard progress > 0 else { return }
        let colour = Color.almaGold.opacity(0.55 * progress)
        switch element {
        case "air":
            for i in 0..<3 {
                let y = at.y + Double(i - 1) * width * 0.14
                var breeze = Path()
                breeze.move(to: CGPoint(x: at.x - width / 2, y: y))
                breeze.addQuadCurve(
                    to: CGPoint(x: at.x - width / 2 + width * progress, y: y),
                    control: CGPoint(x: at.x, y: y - width * 0.08))
                context.stroke(breeze, with: .color(colour), lineWidth: 0.8)
            }
        case "water":
            for i in 0..<2 {
                let y = at.y + Double(i) * width * 0.14
                var wave = Path()
                wave.move(to: CGPoint(x: at.x - width / 2, y: y))
                wave.addCurve(
                    to: CGPoint(x: at.x + width / 2 * (2 * progress - 1), y: y),
                    control1: CGPoint(x: at.x - width / 4, y: y - width * 0.1),
                    control2: CGPoint(x: at.x + width / 4, y: y + width * 0.1))
                context.stroke(wave, with: .color(colour), lineWidth: 0.8)
            }
        case "fire":
            for i in 0..<3 {
                let x = at.x + Double(i - 1) * width * 0.22
                var flame = Path()
                flame.move(to: CGPoint(x: x, y: at.y + width * 0.12))
                flame.addQuadCurve(
                    to: CGPoint(x: x, y: at.y + width * 0.12 - width * 0.3 * progress),
                    control: CGPoint(x: x + width * 0.1, y: at.y - width * 0.05))
                context.stroke(flame, with: .color(colour), lineWidth: 0.8)
            }
        default: // earth
            for i in 0..<2 {
                let y = at.y + Double(i) * width * 0.12
                let span = width * (1 - Double(i) * 0.35) * progress
                var ground = Path()
                ground.move(to: CGPoint(x: at.x - span / 2, y: y))
                ground.addLine(to: CGPoint(x: at.x + span / 2, y: y))
                context.stroke(ground, with: .color(colour), lineWidth: 0.8)
            }
        }
    }
}

// MARK: — synthesis: nine axes as a star

/// The nine axes as spokes. An axis the systems agree on blooms gold; one
/// they disagree on splits into the product's two accent dots; one voice
/// alone is a single quiet point. The picture *is* the summary line above it.
private struct SynthesisStar: View {

    let data: JSONValue
    let progress: Double

    var body: some View {
        Canvas { context, size in
            let side = min(size.width, size.height)
            let centre = CGPoint(x: size.width / 2, y: size.height / 2)
            let reach = side * 0.40

            let axes = data["axes"]?.arrayValue ?? []
            guard !axes.isEmpty else { return }

            for (index, axis) in axes.enumerated() {
                let grown = phase(
                    progress,
                    0.05 + Double(index) * 0.06,
                    0.4 + Double(index) * 0.06)
                guard grown > 0 else { continue }
                let a = (Double(index) / Double(axes.count) * 360 - 90) * .pi / 180
                let tip = CGPoint(
                    x: centre.x + reach * grown * cos(a),
                    y: centre.y + reach * grown * sin(a))

                let verdict = axis["verdict"]?.stringValue ?? ""
                let agree = verdict == "agree"

                var spoke = Path()
                spoke.move(to: CGPoint(
                    x: centre.x + side * 0.05 * cos(a),
                    y: centre.y + side * 0.05 * sin(a)))
                spoke.addLine(to: tip)
                context.stroke(
                    spoke,
                    with: .color(Color.almaGold.opacity(agree ? 0.45 : 0.2)),
                    lineWidth: agree ? 1.1 : 0.7)

                let pop = phase(
                    progress,
                    0.35 + Double(index) * 0.06,
                    0.6 + Double(index) * 0.06)
                guard pop > 0 else { continue }

                switch verdict {
                case "agree":
                    let r = side * 0.020 * pop
                    context.fill(
                        Path(ellipseIn: CGRect(
                            x: tip.x - r, y: tip.y - r, width: r * 2, height: r * 2)),
                        with: .color(Color.almaGoldBright.opacity(0.9 * pop)))
                    context.stroke(
                        Path(ellipseIn: CGRect(
                            x: tip.x - r * 2, y: tip.y - r * 2, width: r * 4, height: r * 4)),
                        with: .color(Color.almaGold.opacity(0.35 * pop)),
                        lineWidth: 0.7)
                case "disagree":
                    // The two accents the product reserves for exactly this.
                    let r = side * 0.012 * pop
                    let off = side * 0.018
                    let perp = a + .pi / 2
                    for (colour, sign) in [(Color.almaAgree, 1.0), (Color.almaDisagree, -1.0)] {
                        let at = CGPoint(
                            x: tip.x + off * cos(perp) * sign,
                            y: tip.y + off * sin(perp) * sign)
                        context.fill(
                            Path(ellipseIn: CGRect(
                                x: at.x - r, y: at.y - r, width: r * 2, height: r * 2)),
                            with: .color(colour.opacity(0.85 * pop)))
                    }
                default:
                    let r = side * 0.010 * pop
                    context.fill(
                        Path(ellipseIn: CGRect(
                            x: tip.x - r, y: tip.y - r, width: r * 2, height: r * 2)),
                        with: .color(Color.almaStarFill.opacity(0.5 * pop)))
                }
            }

            // The centre: the product's four-point star, last.
            let seated = phase(progress, 0.8, 1)
            if seated > 0 {
                let r = side * 0.035 * seated
                var star = Path()
                star.move(to: CGPoint(x: centre.x, y: centre.y - r))
                star.addQuadCurve(
                    to: CGPoint(x: centre.x + r, y: centre.y), control: centre)
                star.addQuadCurve(
                    to: CGPoint(x: centre.x, y: centre.y + r), control: centre)
                star.addQuadCurve(
                    to: CGPoint(x: centre.x - r, y: centre.y), control: centre)
                star.addQuadCurve(
                    to: CGPoint(x: centre.x, y: centre.y - r), control: centre)
                context.fill(star, with: .color(Color.almaGoldBright.opacity(seated)))
            }
        }
        .aspectRatio(1, contentMode: .fit)
        .frame(maxWidth: .infinity)
        .accessibilityHidden(true)
    }
}
