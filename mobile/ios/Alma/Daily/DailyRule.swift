import Foundation

/// The one rule that decides whether today has anything to say.
///
/// **It is the same rule on both surfaces, and that is the entire point.** The
/// notification and the Today block must never disagree about what today is —
/// a push that says Mars crosses your Ascendant and a screen that says nothing
/// is exact would destroy the only claim this feature makes. So the thresholds
/// live here, in one place, transcribed from `docs/THE-DAILY.md §6.3`, and the
/// Android copy in `notify/DailyRule.kt` carries the same numbers with the same
/// comment.
///
/// **Why it runs on the client at all.** `alma/api/routers/systems.py` returns
/// the transits payload *whole* even when the system is locked — `weight`,
/// `urgency`, `exact`, `enters` and `leaves` are all in `_hit_dict`, for every
/// reader, free or paying. So the day's event can be derived from a request the
/// Today screen already makes, with no new endpoint, no new cost, and no
/// dependency on a backend job that does not exist yet. The push, when it
/// exists, will apply this rule server-side to the same fields; the client
/// applying it is not a duplicate of a decision made elsewhere, it is the same
/// arithmetic on the same numbers.
///
/// **What it is not.** It is not a scoring system. `weight` and `urgency` are
/// the engine's own — `alma/engine/transits.py` computes `_weight` as the
/// product of aspect, transiting body and natal point, and THE-DAILY §1.3
/// measured that it already encodes the slow-versus-fast distinction the daily
/// needs. Nothing here invents a number.
enum DailyRule {

    // MARK: — the thresholds, from THE-DAILY §6.3

    /// A contact perfecting today qualifies at this weight. Measured over a
    /// 24-chart cohort: median 45.5 admissions a year, 0.88 a week.
    static let exactFloor: Double = 0.35

    /// A slow body *entering orb* qualifies lower, because entering orb is the
    /// only news a Pluto square ever generates — it perfects once and then sits
    /// in orb for years, so waiting for the instant would mean never mentioning
    /// it at all.
    static let orbEntryFloor: Double = 0.30

    /// "Only what matters": exact hits only, no orb entries, no valve. The
    /// Saturn returns and the Pluto squares, 7–13 times a year (§1.4).
    static let onlyWhatMattersFloor: Double = 0.50

    /// `alma/engine/transits.py::SLOW_BODIES`, copied rather than derived —
    /// there is nothing to derive it from on a phone. If the engine's tuple
    /// changes, this changes.
    static let slowBodies: Set<String> = [
        "jupiter", "saturn", "uranus", "neptune", "pluto", "chiron",
    ]

    /// The five aspects `ASPECT_TARGETS` actually scans. A sixth would need a
    /// sixth `push.daily.*` key, which is why the set is written down rather
    /// than accepted from the payload.
    static let aspects: Set<String> = [
        "conjunction", "opposition", "square", "trine", "sextile",
    ]

    // MARK: — the decision

    /// Everything today could be about, most important first.
    ///
    /// Returns all qualifying contacts rather than only the winner, because the
    /// Today block shows the day and the notification shows one line of it. The
    /// caller takes `.first`; nothing here decides that one is all there is.
    static func candidates(
        among hits: [DailyContact],
        on day: Date,
        preference: DailyPreference,
        calendar: Calendar = .current
    ) -> [DailyContact] {
        guard preference != .off else { return [] }

        let qualifying = hits.filter { hit in
            switch preference {
            case .off:
                return false

            case .onlyWhatMatters:
                // No orb entries and no valve: this position exists for people
                // who asked for the slow ones and nothing else, and an orb
                // entry is the loosest signal the rule has.
                return hit.weight >= onlyWhatMattersFloor
                    && hit.exact.map { calendar.isDate($0, inSameDayAs: day) } == true

            case .occasionally:
                if let exact = hit.exact,
                   calendar.isDate(exact, inSameDayAs: day),
                   hit.weight >= exactFloor {
                    return true
                }
                if slowBodies.contains(hit.transiting),
                   hit.weight >= orbEntryFloor,
                   let enters = hit.enters,
                   calendar.isDate(enters, inSameDayAs: day) {
                    return true
                }
                return false
            }
        }

        // Highest weight wins, and `urgency` breaks the tie — it is weight
        // discounted by how far out of orb the contact is, so between two
        // equally heavy contacts it prefers the tighter one. Both are the
        // engine's; neither is computed here.
        return qualifying.sorted {
            $0.weight == $1.weight ? $0.urgency > $1.urgency : $0.weight > $1.weight
        }
    }

    /// How many of the next `days` days have something in them.
    ///
    /// This is the app checking its own claim. The settings screen says the
    /// daily arrives "about once a week"; that number was measured over 24
    /// charts and none of them is the reader's. Counting the reader's own
    /// window with the reader's own rule turns a claim into an observation,
    /// and it is the only part of the cadence promise a client can honestly
    /// verify — see the note in `DailySettingsSection`.
    ///
    /// It is a **lower bound and says so at the call site**: the server sends
    /// at most 60 future contacts (`service.py`'s `hits[:60]`), so a chart with
    /// a dense month can have days this count cannot see.
    static func exactDays(
        among hits: [DailyContact],
        from start: Date,
        days: Int,
        preference: DailyPreference,
        calendar: Calendar = .current
    ) -> Int {
        guard preference != .off else { return 0 }
        var counted = Set<Date>()
        for offset in 0..<days {
            guard let day = calendar.date(byAdding: .day, value: offset, to: start) else { continue }
            let startOfDay = calendar.startOfDay(for: day)
            if !candidates(among: hits, on: day, preference: preference, calendar: calendar).isEmpty {
                counted.insert(startOfDay)
            }
        }
        return counted.count
    }
}

/// One contact between the sky and this chart, as the daily needs it.
///
/// Deliberately *not* `ChartFacts.Transit`. That type is about drawing a row —
/// it carries a pre-formatted notation string and a joined meta line, and it
/// throws away the two numbers this rule is entirely made of. Parsing twice is
/// cheaper than making a display type carry decision fields, which is how a
/// view model becomes the place business rules hide.
struct DailyContact: Identifiable, Equatable, Sendable {

    let transiting: String
    let natal: String
    let aspect: String
    let glyph: String
    let retrograde: Bool

    /// The instant it perfects, in the device's calendar. Optional: a contact
    /// already past exactness inside the window has none.
    let exact: Date?
    let enters: Date?
    let leaves: Date?

    let orbNow: Double
    /// `_weight` — aspect × transiting body × natal point. The admission test.
    let weight: Double
    /// Weight discounted by how far out of orb it is today. The tie-break.
    let urgency: Double

    /// The engine's own sentence, which is what the validator would cite. Used
    /// as the accessibility label so that VoiceOver reads the citation rather
    /// than three glyphs.
    let spoken: String

    var id: String { "\(transiting)-\(aspect)-\(natal)-\(exact?.timeIntervalSince1970 ?? 0)" }

    /// "Mars retrograde square your Ascendant".
    ///
    /// **This was "♂℞ □ ASC", and the argument for it did not survive
    /// contact.** The reasoning was that two glyphs say in six languages what
    /// fourteen translated planet names would — true, and irrelevant, because
    /// the row is on the front page of the app and the people reading it do not
    /// know the glyphs. The owner's verdict was the shorter one: people will
    /// not understand this. A notation that saves translation work and costs
    /// comprehension is saving the wrong thing.
    ///
    /// The names are translated now (`Cabinet.xcstrings`), so the original
    /// objection is answered rather than overruled.
    /// **One template per language, because five of the seven cannot say this
    /// the way English does.** The parts used to be concatenated —
    /// body + aspect + "your" + body — and that shape only works in a language
    /// whose possessive does not decline. German, French, Italian, Portuguese
    /// and Russian all agree "your" with the gender of the noun after it, and
    /// the string tables solved that by making the aspect word `— Konjunktion`
    /// and the word for "your" a bare `—`. The result, on the front page, in
    /// Russian: «Юпитер — соединение — Асцендент». Three words and two dashes,
    /// none of it a sentence.
    ///
    /// A template moves the punctuation into the language that needs it. English
    /// and Spanish keep their possessive ("conjunct your Ascendant"); the other
    /// five name both ends and then the aspect, in the nominative, where nothing
    /// has to agree with anything: «Юпитер и Асцендент: соединение».
    var notation: String {
        let mark = retrograde ? " \(DailyL10n.retrogradeWord)" : ""
        return String(
            format: String(localized: DailyL10n.contactPhrase),
            L10nCabinet.bodyName(transiting) + mark,
            DailyL10n.aspectWord(aspect),
            L10nCabinet.bodyName(natal)
        )
    }

    /// Which `push.daily.*` key the server would pick for this contact. Not
    /// used to send anything — the app never sends itself a real push — but it
    /// is what `DailyDebug` posts a local notification with, so the key set and
    /// the payload shape are exercised by something rather than only asserted.
    func pushKey(entering: Bool) -> String {
        entering ? "push.daily.entering.\(aspect)" : "push.daily.\(aspect)"
    }

    // MARK: — parsing

    /// Read the `active` and `upcoming` arrays out of a transits payload.
    ///
    /// Both, merged and de-duplicated. `active` is what is in orb at the scan's
    /// instant and `upcoming` is the first sixty contacts of the whole scan, so
    /// a contact that perfects later today appears in both — and one that
    /// perfects tomorrow appears only in the second. Reading one alone gets a
    /// different answer depending on the hour, which is the worst kind of bug
    /// on a screen called Today.
    static func all(in data: JSONValue) -> [DailyContact] {
        var seen = Set<String>()
        var out: [DailyContact] = []
        for key in ["active", "upcoming"] {
            for entry in data[key]?.arrayValue ?? [] {
                guard let contact = DailyContact(entry) else { continue }
                if seen.insert(contact.id).inserted { out.append(contact) }
            }
        }
        return out
    }

    init?(_ entry: JSONValue) {
        guard let transiting = entry["transiting"]?.stringValue,
              let natal = entry["natal"]?.stringValue,
              let aspect = entry["aspect"]?.stringValue
        else { return nil }

        self.transiting = transiting
        self.natal = natal
        self.aspect = aspect
        self.glyph = entry["glyph"]?.stringValue ?? aspect
        self.retrograde = entry["retrograde"]?.boolValue ?? false
        self.exact = AlmaDate.instant(entry["exact"]?.stringValue)
        self.enters = AlmaDate.instant(entry["enters"]?.stringValue)
        self.leaves = AlmaDate.instant(entry["leaves"]?.stringValue)
        self.orbNow = entry["orb_now"]?.doubleValue ?? 0
        // **Zero when absent, not one.** A payload from a backend that has not
        // learned to send `weight` must produce *no* daily rather than a daily
        // about everything: the whole feature is a filter, and a filter that
        // defaults open is a horoscope.
        self.weight = entry["weight"]?.doubleValue ?? 0
        self.urgency = entry["urgency"]?.doubleValue ?? 0
        self.spoken = entry["text"]?.stringValue ?? "\(transiting) \(aspect) \(natal)"
    }
}
