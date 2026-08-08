import Foundation

/// Reading the eight payloads.
///
/// `CalcResult.data` is `JSONValue` because the eight systems answer in eight
/// shapes; this file is where the four or five facts each screen prints are
/// narrowed out of it, in one place rather than inside a view body.
///
/// **Everything returns an optional and nothing invents a fallback.** A locked
/// system answers with its preview fields only — no `placements`, no `active`,
/// no `axes` — so a reader that cannot find its field returns `nil` and the
/// caller *drops the element*. That is the whole rule: an absent Ascendant is
/// an Ascendant nobody could compute, and printing a plausible one is the
/// single worst thing this app could do.
///
/// **Locked is not an error.** Every calculation is free forever; what is sold
/// is the writing. A locked `CalcResult` is a real result with fewer fields in
/// it, and the screens show every field it does carry.
enum ChartFacts {

    // MARK: — notation

    /// Sign name → glyph. Design metadata, not somebody's chart: a locked natal
    /// answer names the three signs and carries no glyphs, and this product is
    /// drawn in symbols. The names are the engine's own, always English.
    static let signGlyphs: [String: String] = [
        "Aries": "♈︎", "Taurus": "♉︎", "Gemini": "♊︎", "Cancer": "♋︎",
        "Leo": "♌︎", "Virgo": "♍︎", "Libra": "♎︎", "Scorpio": "♏︎",
        "Sagittarius": "♐︎", "Capricorn": "♑︎", "Aquarius": "♒︎", "Pisces": "♓︎",
    ]

    /// Body name → glyph, for the places where the payload carries a name and
    /// not a placement to read a glyph off.
    ///
    /// The angles are not bodies and have no glyph in any of the notations —
    /// ASC and MC are what an ephemeris prints and what the engine itself uses.
    static let bodyGlyphs: [String: String] = [
        "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀", "mars": "♂",
        "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆", "pluto": "♇",
        "true_node": "☊", "mean_node": "☊", "chiron": "⚷", "lilith": "⚸",
        "ascendant": "ASC", "midheaven": "MC",
    ]

    static func bodyGlyph(_ name: String) -> String {
        bodyGlyphs[name] ?? name
    }

    static func signGlyph(_ name: String?) -> String? {
        guard let name else { return nil }
        return signGlyphs[name]
    }

    /// 0.7 → "0°42′". The engine reports an orb as a decimal degree; a chart
    /// prints degrees and minutes, and this screen is a chart.
    static func orb(_ value: Double) -> String {
        var degrees = Int(value.rounded(.down))
        var minutes = Int(((value - Double(degrees)) * 60).rounded())
        if minutes == 60 {
            degrees += 1
            minutes = 0
        }
        return "\(degrees)°\(String(format: "%02d", minutes))′"
    }

    // MARK: — the natal chart

    /// "☉ 23°38′ ♓︎ · H10" — glyph, degree, sign, house, the way a chart prints
    /// it. `nil` when the chart is locked (no `placements`) or the body was not
    /// computed.
    static func placement(_ data: JSONValue, body: String) -> String? {
        guard let placement = data["placements"]?[body],
              let formatted = placement["formatted"]?.stringValue
        else { return nil }
        // **Words, not glyphs, and the owner is right about why.**
        //
        // This read "⊙ 9°52′ ♑ · H3" and expected a reader to know four
        // notations at once: the planet's symbol, the sign's symbol, arcminutes,
        // and H for house. Astrologers know all four. Nobody else knows any of
        // them, and this string is on the front page of the app, above the
        // fold, on the first day. The whole product's claim is that it explains
        // where a sentence came from — a citation nobody can read cites nothing.
        //
        // "Sun 9°52′ Capricorn · 3rd house" is longer and is the point. The
        // degrees stay: they are the part that proves this is a real
        // calculation rather than a sun sign, which is the argument the pill
        // exists to make.
        let name = L10nCabinet.bodyName(body)
        let readable = spellSigns(in: formatted)
        let house = placement["house"]?.intValue.map { " · \(L10nCabinet.houseName($0))" } ?? ""
        return "\(name) \(readable)\(house)"
    }

    /// A sign glyph inside an engine-formatted position, replaced by its name.
    ///
    /// The engine formats "9°52′ ♑︎" and the glyph is the only part a reader
    /// cannot decode. Substituted rather than reformatted, so the degrees and
    /// minutes remain exactly what the engine printed and this layer never
    /// becomes a second opinion about a number.
    static func spellSigns(in formatted: String) -> String {
        var out = formatted
        for (name, glyph) in signGlyphs {
            if out.contains(glyph) {
                out = out.replacingOccurrences(of: glyph, with: L10nCabinet.signName(name))
            }
        }
        // The engine appends a variation selector to some glyphs; the
        // replacement above leaves it behind.
        return out.replacingOccurrences(of: "\u{FE0E}", with: "")
            .trimmingCharacters(in: .whitespaces)
    }

    /// The Ascendant, which exists only when the birth time does. There is no
    /// fallback: a chart with no horizon has no rising degree, and the row
    /// leaves rather than showing the sign it would have had at noon.
    static func ascendant(_ data: JSONValue) -> String? {
        guard let formatted = data["angles"]?["formatted"]?["ascendant"]?.stringValue else {
            return nil
        }
        return "\(String(localized: L10nCabinet.ascendant)) \(spellSigns(in: formatted))"
    }

    /// The fallback pill for a locked chart, which still names the three signs:
    /// "☉ ♓︎". Degree-less, because a locked answer carries no degrees.
    static func signPill(mark: String, sign: String?) -> String? {
        guard let sign, signGlyphs[sign] != nil else { return nil }
        return "\(mark) \(L10nCabinet.signName(sign))"
    }

    /// The dominant element, as the engine's own key — translated by the caller,
    /// because it arrives in English in every locale.
    static func dominantElement(_ data: JSONValue) -> String? {
        data["balance"]?["dominant_element"]?.stringValue
    }

    /// The moon phase and how much of it is lit. Survives the lock: both are
    /// preview fields, which is why the one line under the wheel is the same
    /// line for somebody who has paid and somebody who has not.
    struct MoonPhase: Equatable {
        let name: String
        let illumination: Double?
    }

    static func moonPhase(_ data: JSONValue) -> MoonPhase? {
        guard let phase = data["moon_phase"], let name = phase["phase"]?.stringValue else {
            return nil
        }
        return MoonPhase(name: name, illumination: phase["illumination"]?.doubleValue)
    }

    /// One aspect of the natal chart, tightest first — the engine sorts them,
    /// so the first few genuinely are the strongest.
    struct Aspect: Identifiable, Equatable {
        let id: String
        /// "☉ △ ♂" — set as type, in the serif, like every other position.
        let notation: String
        let orb: String
        let harmony: Harmony
    }

    enum Harmony: Equatable {
        case harmonious
        case tense
        case neutral

        init(_ raw: String?) {
            switch raw {
            case "harmonious": self = .harmonious
            case "tense": self = .tense
            default: self = .neutral
            }
        }
    }

    static func aspects(_ data: JSONValue, limit: Int = 3) -> [Aspect] {
        guard let all = data["aspects"]?.arrayValue else { return [] }
        return all.prefix(limit).compactMap { entry in
            guard let first = entry["first"]?.stringValue,
                  let second = entry["second"]?.stringValue,
                  let orbValue = entry["orb"]?.doubleValue
            else { return nil }
            let glyph = entry["glyph"]?.stringValue ?? ""
            return Aspect(
                id: "\(first)-\(entry["type"]?.stringValue ?? "")-\(second)",
                notation: [bodyGlyph(first), glyph, bodyGlyph(second)]
                    .filter { !$0.isEmpty }
                    .joined(separator: " "),
                orb: orb(orbValue),
                harmony: Harmony(entry["harmony"]?.stringValue)
            )
        }
    }

    // MARK: — transits

    /// One contact between the sky now and the chart at birth.
    ///
    /// The title is **notation and not prose**: "♂ □ ☽", set in the serif. The
    /// engine names its bodies in English in every locale, so a translated row
    /// title would need fourteen planet names in six languages to say what two
    /// glyphs already say in all of them. The engine's own sentence travels
    /// along as the accessibility label, where English is the lesser evil.
    struct Transit: Identifiable, Equatable {
        let id: String
        let notation: String
        /// "19 March → 24 March · 0°42′"
        let meta: String
        /// The natal placement this is read against — the citation that makes
        /// the row a chart factor rather than a horoscope line.
        let readAgainst: String
        let spoken: String
    }

    static func transits(_ data: JSONValue, key: String, limit: Int = 3) -> [Transit] {
        guard let rows = data[key]?.arrayValue else { return [] }
        return rows.prefix(limit).compactMap { entry in
            guard let transiting = entry["transiting"]?.stringValue,
                  let natal = entry["natal"]?.stringValue
            else { return nil }

            // Words rather than glyphs, for the reason the placements above
            // carry: this row is on the front page and "♇℞ ☌ ☊" asks a reader
            // to know three notations before it says anything. The engine's
            // aspect key is what names the word; the glyph is the fallback for
            // an aspect the table has not caught up with.
            let aspectKey = entry["aspect"]?.stringValue ?? ""
            let aspect = aspectKey.isEmpty
                ? (entry["glyph"]?.stringValue ?? "")
                : DailyL10n.aspectWord(aspectKey)
            let retrograde = entry["retrograde"]?.boolValue == true
                ? " \(DailyL10n.retrogradeWord)" : ""
            let dates = [
                AlmaDate.dayAndMonth(instant: entry["exact"]?.stringValue),
                AlmaDate.dayAndMonth(instant: entry["leaves"]?.stringValue),
            ].compactMap { $0 }.joined(separator: " → ")
            let orbNow = entry["orb_now"]?.doubleValue.map(orb) ?? ""

            return Transit(
                id: "\(transiting)-\(entry["aspect"]?.stringValue ?? "")-\(natal)",
                notation: "\(L10nCabinet.bodyName(transiting))\(retrograde) \(aspect) "
                    + "\(DailyL10n.yourWord) \(L10nCabinet.bodyName(natal))",
                meta: [dates, orbNow].filter { !$0.isEmpty }.joined(separator: " · "),
                readAgainst: natal,
                spoken: entry["text"]?.stringValue ?? "\(transiting) \(aspect) \(natal)"
            )
        }
    }

    /// How wide the scan was, in days. Part of the preview, so it is known even
    /// when the events behind it are not.
    static func transitWindowDays(_ data: JSONValue) -> Int? {
        data["window"]?["days"]?.intValue
    }

    static func activeCount(_ data: JSONValue) -> Int? {
        data["active_count"]?.intValue
    }

    // MARK: — cross-synthesis

    enum Verdict: String, Equatable {
        case agree
        case disagree
        case single

        var tone: AlmaTagTone {
            switch self {
            case .agree: .agree
            case .disagree: .disagree
            case .single: .gold
            }
        }
    }

    struct Signal: Identifiable, Equatable {
        /// Built from the raw slug rather than the decoded one: two signals on
        /// the same axis from the same system would otherwise collide, and the
        /// optional's debug description is not an identity.
        var id: String { "\(systemRaw)-\(factor)" }
        let system: SystemSlug?
        /// The engine's own words for what it read — "midheaven in Pisces".
        let factor: String
        /// The raw slug, kept for the case where a ninth system appears.
        let systemRaw: String
    }

    /// One of the nine axes, and the whole argument that this app is not a
    /// horoscope feed: three systems asked the same question and here is what
    /// each of them answered.
    struct Axis: Identifiable, Equatable {
        var id: String { name }
        /// The English name, which is also the dictionary key.
        let name: String
        let verdict: Verdict
        let count: Int
        /// The two ends of the axis, in the engine's words. Shown for a
        /// disagreement because that is what the systems are disagreeing
        /// *about*; without them "2 disagree" is a number with no subject.
        let positivePole: String?
        let negativePole: String?
        let signals: [Signal]
    }

    static func axes(_ data: JSONValue) -> [Axis] {
        guard let rows = data["axes"]?.arrayValue else { return [] }
        return rows.compactMap { entry in
            guard let name = entry["name"]?.stringValue,
                  let verdict = entry["verdict"]?.stringValue.flatMap(Verdict.init(rawValue:))
            else { return nil }  // an unfamiliar verdict is dropped, never guessed at
            let signals = (entry["signals"]?.arrayValue ?? []).compactMap { signal -> Signal? in
                guard let system = signal["system"]?.stringValue,
                      let factor = signal["factor"]?.stringValue
                else { return nil }
                return Signal(system: SystemSlug(rawValue: system), factor: factor, systemRaw: system)
            }
            return Axis(
                name: name,
                verdict: verdict,
                count: entry["count"]?.intValue ?? signals.count,
                positivePole: entry["positive_pole"]?.stringValue,
                negativePole: entry["negative_pole"]?.stringValue,
                signals: signals
            )
        }
    }

    /// The three counts. Preview fields, so they survive the lock — which is
    /// why the chips are shown to somebody who has not paid: the shape of the
    /// answer is free, the reading of it is not.
    struct SynthesisCounts: Equatable {
        let agree: Int
        let disagree: Int
        let single: Int
    }

    static func synthesisCounts(_ data: JSONValue) -> SynthesisCounts? {
        guard let agree = data["agreements"]?.intValue,
              let disagree = data["disagreements"]?.intValue,
              let single = data["single_voice"]?.intValue
        else { return nil }
        return SynthesisCounts(agree: agree, disagree: disagree, single: single)
    }

    // MARK: — the smaller five

    /// A label and a value, which is what numerology, the birth card, the solar
    /// return and astrocartography each amount to on a phone. The value is
    /// notation or a number; the label is ours and localised.
    struct Fact: Identifiable, Equatable {
        var id: String { "\(label)-\(value)" }
        /// Kept as a plain `String` because most of these labels are the
        /// engine's own vocabulary — "life path", "year ruler" — which the
        /// dictionary has never had a word for in any language, on the web
        /// either.
        let label: String
        let value: String
    }

    static func numerology(_ data: JSONValue) -> [Fact] {
        var facts: [Fact] = []
        if let lifePath = data["life_path"]?.intValue {
            let debt = data["life_path_debt"]?.intValue.map {
                " · \(L10nCabinet.factLabel("karmicDebt", fallback: "karmic debt")) \($0)"
            } ?? ""
            facts.append(Fact(
                label: L10nCabinet.factLabel("lifePath", fallback: "life path"),
                value: "\(lifePath)\(debt)"))
        }
        if let birthday = data["birthday_number"]?.intValue {
            facts.append(Fact(
                label: L10nCabinet.factLabel("birthdayNumber", fallback: "birthday number"),
                value: "\(birthday)"))
        }
        if let destiny = data["destiny_number"]?.intValue {
            facts.append(Fact(
                label: L10nCabinet.factLabel("destinyNumber", fallback: "destiny number"),
                value: "\(destiny)"))
        }
        return facts
    }

    static func birthCard(_ data: JSONValue) -> [Fact] {
        guard let card = data["personality"] else { return [] }
        var facts: [Fact] = []
        if let name = card["name"]?.stringValue {
            let numeral = card["numeral"]?.stringValue.map { "\($0) · " } ?? ""
            facts.append(Fact(
                label: L10nCabinet.factLabel("personalityCard", fallback: "personality card"),
                value: "\(numeral)\(L10nCabinet.arcanaName(name))"))
        }
        if let element = card["element"]?.stringValue {
            let word = L10nCabinet.element(element.lowercased())
                .map { String(localized: $0) } ?? element
            facts.append(Fact(
                label: L10nCabinet.factLabel("element", fallback: "element"),
                value: word))
        }
        if let ruler = card["ruler"]?.stringValue {
            facts.append(Fact(
                label: L10nCabinet.factLabel("ruler", fallback: "ruler"),
                value: L10nCabinet.bodyName(ruler.lowercased())))
        }
        return facts
    }

    static func solarReturn(_ data: JSONValue) -> [Fact] {
        var facts: [Fact] = []
        if let year = data["year"]?.intValue {
            facts.append(Fact(
                label: L10nCabinet.factLabel("year", fallback: "year"),
                value: "\(year)"))
        }
        if let at = AlmaDate.readable(instant: data["return_at"]?.stringValue) {
            facts.append(Fact(
                label: L10nCabinet.factLabel("return", fallback: "return"),
                value: at))
        }
        if let ruler = data["year_ruler"]?.stringValue {
            // The word, not "☽ moon": the ruler is prose on this row, and the
            // rest of the product already spells bodies out.
            facts.append(Fact(
                label: L10nCabinet.factLabel("yearRuler", fallback: "year ruler"),
                value: L10nCabinet.bodyName(ruler.lowercased())))
        }
        return facts
    }

    static func astrocartography(_ data: JSONValue) -> [Fact] {
        var facts: [Fact] = []
        if let text = data["birthplace"]?["text"]?.stringValue {
            facts.append(Fact(
                label: L10nCabinet.factLabel("birthplace", fallback: "birthplace"),
                value: text))
        }
        if let lines = data["lines"]?.arrayValue, !lines.isEmpty {
            facts.append(Fact(
                label: L10nCabinet.factLabel("lines", fallback: "lines"),
                value: "\(lines.count)"))
        }
        if let parans = data["parans"]?.arrayValue, !parans.isEmpty {
            facts.append(Fact(
                label: L10nCabinet.factLabel("crossings", fallback: "crossings"),
                value: "\(parans.count)"))
        }
        return facts
    }

    /// The synastry scores, which are the one part of a compatibility result
    /// that survives the lock. They are percentages in the engine's own
    /// vocabulary; the key is its label.
    static func compatibility(_ data: JSONValue) -> [Fact] {
        guard let scores = data["scores"]?.objectValue else { return [] }
        return scores
            .sorted { $0.key < $1.key }
            .compactMap { key, value in
                guard let number = value.doubleValue else { return nil }
                return Fact(
                    label: L10nCabinet.scoreName(key),
                    value: "\(Int(number.rounded()))"
                )
            }
    }

    /// Whichever of the five above fits this system. Natal and the two that
    /// have screens of their own are handled by the screen; this is the shared
    /// fallback so a system nobody has designed a panel for still shows its
    /// free calculation instead of an empty page.
    static func facts(for system: SystemSlug, data: JSONValue) -> [Fact] {
        switch system {
        case .numerology: numerology(data)
        case .birthCard: birthCard(data)
        case .solarReturn: solarReturn(data)
        case .astrocartography: astrocartography(data)
        case .compatibility: compatibility(data)
        case .natal, .transits, .synthesis: []
        }
    }
}
