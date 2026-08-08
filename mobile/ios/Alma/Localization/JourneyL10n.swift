import Foundation

/// Every word the journey says, named once.
///
/// **Why a second String Catalog instead of adding to `Localizable.xcstrings`.**
/// Three agents are building screens into this project at the same time, and a
/// String Catalog is a single JSON document with one `strings` object — two
/// agents adding keys to it are editing the same lines of the same file, which
/// is the one merge conflict that cannot be resolved by taking either side. A
/// catalog is also just a *table*, and `LocalizedStringResource` takes the table
/// name, so a second file costs one parameter and removes the conflict
/// entirely. `Alma/Resources/Journey.xcstrings` is mine and nobody else writes
/// to it. The discipline is unchanged — a constant per string, all six
/// languages, `extractionState: "manual"`, no literal at a call site.
///
/// **Where the wording comes from.** `src/lib/i18n/{en,es,de,it,fr,pt-BR}.ts`,
/// copied across rather than re-translated, so that the web app and the app say
/// the same sentence to the same person. Five strings are new — the close
/// button, the step counter VoiceOver reads, the free-chapter label, the
/// price-less buy verb and nothing else — and the note beside each says why it
/// had to be.
///
/// **Two shapes, and the split is not arbitrary.** A constant whose key is
/// fixed is a `LocalizedStringResource`, which defers the lookup to the moment
/// the view draws. A lookup whose *key* is computed from data — a sign name, a
/// month index, a ceremony beat — cannot be one of those, because that
/// initialiser takes a `StaticString`; those resolve to `String` here, through
/// `text(_:fallback:)`, which is also the only place a fallback can be chosen
/// deliberately instead of rendering a raw key at somebody.
enum JourneyL10n {

    /// The table is the file name. Written once so a typo in it is one broken
    /// constant rather than 115 silent fallbacks to the key.
    private static let table = "Journey"

    // MARK: — the cover itself

    static let dialogLabel = LocalizedStringResource(
        "journey.dialogLabel", defaultValue: "Getting to know you", table: table)

    /// The ✕. The web's label is "Back to the landing", which is a place this
    /// app does not have — and a translated lie is still a lie.
    static let close = LocalizedStringResource(
        "journey.close", defaultValue: "Close", table: table)

    /// The back arrow's name. The journey has no exit now, so this is the only
    /// way out of a screen and it has to be announced as movement rather than
    /// as leaving.
    static let back = LocalizedStringResource(
        "journey.back", defaultValue: "Back", table: table)

    /// What VoiceOver reads instead of the Roman numerals.
    ///
    /// The numerals are typography, and "VII" is read out as three letters,
    /// which tells somebody who cannot see the screen nothing about how far
    /// through they are. The numerals stay; this is what is announced.
    static func step(_ index: Int, of total: Int) -> LocalizedStringResource {
        LocalizedStringResource(
            "journey.step", defaultValue: "Step \(String(index)) of \(String(total))", table: table)
    }

    static let continueCta = LocalizedStringResource(
        "journey.continueCta", defaultValue: "Continue", table: table)

    // MARK: — I · what's loudest

    static let intentTitle = LocalizedStringResource(
        "journey.intentTitle", defaultValue: "What's loudest in you right now?", table: table)

    static let intentSkip = LocalizedStringResource(
        "journey.intentSkip", defaultValue: "Skip — I know what I want", table: table)

    static let intentSelf = LocalizedStringResource(
        "journey.intent.self", defaultValue: "Who am I, really", table: table)
    static let intentShifting = LocalizedStringResource(
        "journey.intent.shifting", defaultValue: "Something's shifting and I don't know why",
        table: table)
    static let intentUs = LocalizedStringResource(
        "journey.intent.us", defaultValue: "Us — will this work", table: table)
    static let intentWhere = LocalizedStringResource(
        "journey.intent.where", defaultValue: "Where I should live", table: table)

    // MARK: — II · a name isn't an account

    static let nameTitle = LocalizedStringResource(
        "journey.nameTitle", defaultValue: "What should I call you?", table: table)
    static let nameSub = LocalizedStringResource(
        "journey.nameSub", defaultValue: "Nothing is saved yet.",
        table: table)
    static let namePlaceholder = LocalizedStringResource(
        "journey.namePlaceholder", defaultValue: "Sofia", table: table)
    static let nameAria = LocalizedStringResource(
        "journey.nameAria", defaultValue: "Your name", table: table)

    // MARK: — III · the date

    static let aboutTitle = LocalizedStringResource(
        "journey.aboutTitle", defaultValue: "A little about you", table: table)
    static let aboutSub = LocalizedStringResource(
        "journey.aboutSub",
        defaultValue: "You can skip this.",
        table: table)
    static let genderFemale = LocalizedStringResource(
        "journey.genderFemale", defaultValue: "Female", table: table)
    static let genderMale = LocalizedStringResource(
        "journey.genderMale", defaultValue: "Male", table: table)
    static let genderSkip = LocalizedStringResource(
        "journey.genderSkip", defaultValue: "Prefer not to say", table: table)
    static let dateTitle = LocalizedStringResource(
        "journey.dateTitle", defaultValue: "When were you born?", table: table)
    static let dateSub = LocalizedStringResource(
        "journey.dateSub", defaultValue: "The date alone already gives three systems.",
        table: table)

    static let day = LocalizedStringResource(
        "journey.capture.day", defaultValue: "Day of birth", table: table)
    static let month = LocalizedStringResource(
        "journey.capture.month", defaultValue: "Month of birth", table: table)
    static let year = LocalizedStringResource(
        "journey.capture.year", defaultValue: "Year of birth", table: table)
    static let dayShort = LocalizedStringResource(
        "journey.capture.dayShort", defaultValue: "Day", table: table)
    static let monthShort = LocalizedStringResource(
        "journey.capture.monthShort", defaultValue: "Month", table: table)
    static let yearShort = LocalizedStringResource(
        "journey.capture.yearShort", defaultValue: "Year", table: table)

    /// The 31st of February, caught here rather than by the backend.
    ///
    /// The web app catches it on the landing capture and not in the journey, so
    /// there a bad date travels to the server and comes back a 422 — which in
    /// this app would surface during the ceremony, where nothing can be said
    /// about it, and then as an empty portrait. One `Calendar` check is cheaper
    /// than that.
    static let impossibleDate = LocalizedStringResource(
        "journey.capture.impossibleDate", defaultValue: "That date does not exist. Check the day.",
        table: table)

    /// The month as a word.
    ///
    /// A number would be shorter and would be the bug this exists to avoid: a
    /// person reading "03/14" in a locale that writes the month first enters
    /// the wrong date and gets somebody else's chart. The word is unambiguous
    /// in every language; the *index* is what travels to the backend.
    static func monthName(_ number: Int) -> String {
        text("journey.month.\(number)", fallback: String(number))
    }

    // MARK: — IV · the time, honestly

    static let timeTitle = LocalizedStringResource(
        "journey.timeTitle", defaultValue: "What time were you born?", table: table)
    static let hourLabel = LocalizedStringResource(
        "journey.hourLabel", defaultValue: "Hour", table: table)
    static let minuteLabel = LocalizedStringResource(
        "journey.minuteLabel", defaultValue: "Min", table: table)
    static let meridiemLabel = LocalizedStringResource(
        "journey.meridiemLabel", defaultValue: "AM or PM", table: table)
    static let lockedWithoutTime = LocalizedStringResource(
        "journey.lockedWithoutTime", defaultValue: "Houses, solar return and map stay locked",
        table: table)
    static let unknownTime = LocalizedStringResource(
        "journey.capture.unknownTime", defaultValue: "I don't know my birth time", table: table)

    // MARK: — V · the place

    static let placeTitle = LocalizedStringResource(
        "journey.placeTitle", defaultValue: "Where were you born?", table: table)
    static let placeSub = LocalizedStringResource(
        "journey.placeSub",
        defaultValue: "City is enough.", table: table)
    static let placePlaceholder = LocalizedStringResource(
        "journey.placePlaceholder", defaultValue: "Milan", table: table)
    static let searchPlace = LocalizedStringResource(
        "journey.capture.searchPlace", defaultValue: "Where were you born?", table: table)
    static let noPlaces = LocalizedStringResource(
        "journey.capture.noPlaces",
        defaultValue: "No place by that name. Try the nearest larger town.", table: table)
    static let buildMySky = LocalizedStringResource(
        "journey.buildMySky", defaultValue: "Build my sky", table: table)

    // MARK: — VI · the ceremony

    /// One beat: the overline naming the system, and Alma's line under it.
    /// Eight of each, in the order the eight systems are computed.
    static func ceremonyLabel(_ beat: Int) -> String { text("journey.ceremony.\(beat).label") }
    static func ceremonyLine(_ beat: Int) -> String { text("journey.ceremony.\(beat).line") }

    static let ceremonySkip = LocalizedStringResource(
        "journey.ceremonySkip", defaultValue: "Skip the ceremony", table: table)

    // MARK: — VII · the portrait

    static let calculated = LocalizedStringResource(
        "journey.calculated", defaultValue: "all eight systems · calculated", table: table)
    static let freeLabel = LocalizedStringResource(
        "journey.freeLabel", defaultValue: "yours, free, forever", table: table)
    static let freeNote = LocalizedStringResource(
        "journey.freeNote",
        defaultValue: "These two systems never cost anything. They are yours whether you read further or not.",
        table: table)

    /// New. The web portrait describes the free chapter in the offer copy and
    /// never shows one; here it is a row you can open, so it needed a name.
    static let freeChapterLabel = LocalizedStringResource(
        "journey.freeChapterLabel", defaultValue: "your first chapter · free", table: table)

    static let needsTimeRow = LocalizedStringResource(
        "journey.needsTimeRow", defaultValue: "Solar return · map", table: table)
    static let needsTime = LocalizedStringResource(
        "journey.needsTime", defaultValue: "needs birth time", table: table)
    static let ascendant = LocalizedStringResource(
        "journey.ascendant", defaultValue: "Ascendant", table: table)
    static let moon = LocalizedStringResource(
        "journey.moon", defaultValue: "Moon", table: table)
    static let keepMySky = LocalizedStringResource(
        "journey.keepMySky", defaultValue: "Keep my sky", table: table)
    static let staysFree = LocalizedStringResource(
        "journey.staysFree", defaultValue: "Everything above stays free, forever", table: table)

    static func sun(_ sign: String) -> LocalizedStringResource {
        LocalizedStringResource("journey.insight.sun", defaultValue: "Sun in \(sign)", table: table)
    }

    static func lifePath(_ number: Int) -> LocalizedStringResource {
        LocalizedStringResource(
            "journey.insight.lifePath", defaultValue: "Life path \(String(number))", table: table)
    }

    // MARK: — VIII · the offer

    /// "Your natal chart, written".
    ///
    /// The system name is lowercased for the four Romance locales and left
    /// alone for English and German, which is exactly what the web app does
    /// with `system.toLowerCase()` in those four dictionaries and not in the
    /// other two. It is a property of the sentence, not of the system: German
    /// capitalises nouns mid-sentence and English capitalises this one as a
    /// proper name.
    static func offerTitle(_ system: SystemSlug) -> LocalizedStringResource {
        let name = systemName(system)
        let inline = lowercasesInlineNouns ? name.lowercased() : name
        return LocalizedStringResource(
            "journey.offerTitle", defaultValue: "Your \(inline), written", table: table)
    }

    static let offerSub = LocalizedStringResource(
        "journey.offerSub",
        defaultValue: "The numbers above are yours and stay free. This opens the whole system — every chapter of the reading, written from your positions, not a template.",
        table: table)

    /// The verb, without a price.
    ///
    /// The web button reads "Read it · $8.99" because the web knows what it
    /// charges. Here it must not: Apple is the merchant of record, and the only
    /// honest price is StoreKit's localised one for this storefront, which the
    /// offer screen reads off the product. A number typed into this button
    /// would be wrong in most countries, and being wrong about the price on the
    /// screen where somebody decides to pay is the kind of thing App Review
    /// rejects even when it is only a rounding error.
    static let offerCta = LocalizedStringResource(
        "journey.offerCta", defaultValue: "Read it", table: table)

    static let offerSkip = LocalizedStringResource(
        "journey.offerSkip", defaultValue: "Not now — take me in", table: table)
    static let offerFine = LocalizedStringResource(
        "journey.offerFine", defaultValue: "One payment. Yours permanently. No account needed to buy.",
        table: table)

    // MARK: — IX · the handoff

    static let handoffTitle = LocalizedStringResource(
        "journey.handoffTitle", defaultValue: "Saved. Now read yourself slowly.", table: table)
    static let handoffSub = LocalizedStringResource(
        "journey.handoffSub",
        defaultValue: "Three rules that make this work — the only onboarding we'll ever give you.",
        table: table)

    static func rule(_ number: Int) -> String { text("journey.rule.\(number)") }

    static let openToday = LocalizedStringResource(
        "journey.openToday", defaultValue: "Open my Today", table: table)

    // MARK: — the closed sets

    static func systemName(_ system: SystemSlug) -> String {
        text("journey.system.\(system.rawValue)", fallback: system.rawValue)
    }

    /// The sign, keyed by the English name the backend returns.
    ///
    /// Falls back to that English name rather than to the key, because an
    /// untranslated sign name is at least a sign name. The set has been closed
    /// at twelve since Ptolemy, so the fallback should never run.
    static func sign(_ english: String) -> String {
        text("journey.sign.\(english)", fallback: english)
    }

    /// The moon phase, keyed by the backend's wire spelling ("waning gibbous").
    /// `nil` for anything not in the eight — the portrait then shows no moon
    /// row at all, which is the rule the whole screen is built on.
    static func moonPhase(_ wire: String) -> String? {
        guard let key = MoonPhase.key(for: wire) else { return nil }
        return text("journey.phase.\(key)", fallback: wire)
    }

    // MARK: — resolving a computed key

    /// Look up a key built at runtime, and choose what happens when it misses.
    ///
    /// `String(localized:)` answers with the key itself when there is no entry,
    /// which is how "journey.sign.Ophiuchus" ends up on somebody's screen. The
    /// comparison here is the whole point of routing every dynamic key through
    /// one function.
    private static func text(_ key: String, fallback: String = "") -> String {
        let resolved = String(localized: String.LocalizationValue(stringLiteral: key), table: table)
        return resolved == key ? fallback : resolved
    }

    /// Whether this interface language writes a system name in running text in
    /// lower case. Read from the *bundle's* resolved localisation rather than
    /// from `Locale.current`, because that is the language the sentence around
    /// it is drawn in — a French device with the app in English would otherwise
    /// lowercase an English noun.
    private static var lowercasesInlineNouns: Bool {
        let resolved = Bundle.main.preferredLocalizations.first ?? "en"
        return ["es", "it", "fr", "pt"].contains { resolved.hasPrefix($0) }
    }
}

/// The eight phase names, mapped from the wire spelling to a catalog key.
///
/// A table rather than a string transform. `"waning gibbous"` → `waningGibbous`
/// is one `split` and a `capitalized` away, and that transform would happily
/// mint a key for anything the backend ever sends — including a typo — and then
/// render it in English forever, in six languages, with nobody the wiser. Eight
/// entries and a `nil` is a phase we find out about.
private enum MoonPhase {
    private static let keys: [String: String] = [
        "new moon": "newMoon",
        "waxing crescent": "waxingCrescent",
        "first quarter": "firstQuarter",
        "waxing gibbous": "waxingGibbous",
        "full moon": "fullMoon",
        "waning gibbous": "waningGibbous",
        "last quarter": "lastQuarter",
        "waning crescent": "waningCrescent",
    ]

    static func key(for wire: String) -> String? {
        keys[wire.lowercased()]
    }
}
