import Foundation

/// Every string the cabinet shows, named — and the answer to "where do the
/// translations come from".
///
/// **A second String Catalog, not the skeleton's.** `Localizable.xcstrings`
/// belongs to the shell, and three agents adding keys to one JSON file at the
/// same time is one file with three writers and one winner. `Cabinet.xcstrings`
/// is a separate table with a separate owner; the two are merged by the linker,
/// not by us, and a screen that wants a shell string still says `L10n.tabToday`.
/// The cost is one `table:` argument per constant, paid here and nowhere else.
///
/// **The wording is not invented.** Everything below that exists in
/// `src/lib/i18n/` was copied across from the dictionary in all six languages,
/// so the two clients say the same sentence to the same person — including the
/// pieces of it that were argued over (`lockedNote`, `cancelWhat`, `renews`).
/// What is new to the app is written in the same voice and translated with it:
/// the App Store cancellation lines, which have no web equivalent, and
/// `notPrediction`, which is the sentence the 4.3(b) argument rests on.
///
/// **Why a constant per string.** A key spelled at the call site can be
/// misspelled at the call site, and a misspelled key does not fail the build —
/// it ships the key itself, in English, to Brazil.
enum L10nCabinet {

    /// The table these all live in. `Cabinet.xcstrings`.
    static let table = "Cabinet"

    // MARK: — the eight

    static func system(_ slug: SystemSlug) -> LocalizedStringResource {
        switch slug {
        case .natal: LocalizedStringResource("cab.system.natal", defaultValue: "Natal chart", table: table)
        case .numerology: LocalizedStringResource("cab.system.numerology", defaultValue: "Numerology", table: table)
        case .birthCard: LocalizedStringResource("cab.system.birth-card", defaultValue: "Birth Card", table: table)
        case .transits: LocalizedStringResource("cab.system.transits", defaultValue: "Transits", table: table)
        case .solarReturn: LocalizedStringResource("cab.system.solar-return", defaultValue: "Solar return", table: table)
        case .compatibility: LocalizedStringResource("cab.system.compatibility", defaultValue: "Compatibility", table: table)
        case .astrocartography: LocalizedStringResource("cab.system.astrocartography", defaultValue: "Astrocartography", table: table)
        case .synthesis: LocalizedStringResource("cab.system.synthesis", defaultValue: "Cross-synthesis", table: table)
        }
    }

    static let groupWhoAmI = LocalizedStringResource("cab.group.whoAmI", defaultValue: "who am I", table: table)
    static let groupRightNow = LocalizedStringResource("cab.group.rightNow", defaultValue: "right now", table: table)
    static let groupThisYear = LocalizedStringResource("cab.group.thisYear", defaultValue: "this year", table: table)
    static let groupHowWeMatch = LocalizedStringResource("cab.group.howWeMatch", defaultValue: "how we match", table: table)
    static let groupWhereToBe = LocalizedStringResource("cab.group.whereToBe", defaultValue: "where to be", table: table)
    static let groupAllOfIt = LocalizedStringResource("cab.group.allOfIt", defaultValue: "all of it", table: table)

    static let statusCalculated = LocalizedStringResource("cab.status.calculated", defaultValue: "calculated", table: table)
    static let statusOpen = LocalizedStringResource("cab.status.open", defaultValue: "open", table: table)
    static let statusNeedsTime = LocalizedStringResource("cab.status.needsTime", defaultValue: "needs birth time", table: table)
    static let statusAddPerson = LocalizedStringResource("cab.status.addPerson", defaultValue: "add a person", table: table)
    static let statusNotYet = LocalizedStringResource("cab.status.notYet", defaultValue: "not yet", table: table)

    // MARK: — chapters and doors

    static let chapters = LocalizedStringResource("cab.chapters", defaultValue: "chapters", table: table)
    static let locked = LocalizedStringResource("cab.locked", defaultValue: "Unlock to read", table: table)
    static let openTag = LocalizedStringResource("cab.openTag", defaultValue: "open", table: table)
    static let freeTag = LocalizedStringResource("cab.freeTag", defaultValue: "free", table: table)
    static let calculatedWord = LocalizedStringResource("cab.calculatedWord", defaultValue: "calculated", table: table)
    static let oneTimeNote = LocalizedStringResource("cab.oneTimeNote", defaultValue: "One payment. Yours permanently.", table: table)
    static let archiveNote = LocalizedStringResource("cab.archiveNote", defaultValue: "All eight systems, bought once.", table: table)
    static let freeChapterNote = LocalizedStringResource("cab.freeChapterNote", defaultValue: "One chapter of every system is free.", table: table)
    static let lockedNote = LocalizedStringResource(
        "cab.lockedNote",
        defaultValue: "Written from your own positions the first time you open it — your chart, never a template.",
        table: table
    )
    static let writingNote = LocalizedStringResource(
        "cab.writingNote",
        defaultValue: "It is written once, and it will say the same thing tomorrow.",
        table: table
    )
    static let refused = LocalizedStringResource(
        "cab.refused",
        defaultValue: "Alma could not write this from your chart, so she did not write it.",
        table: table
    )
    static let readFrom = LocalizedStringResource("cab.readFrom", defaultValue: "read from", table: table)

    // MARK: — the natal preview
    static let placementsLabel = LocalizedStringResource("cab.placementsLabel", defaultValue: "your placements", table: table)
    static let spheresLabel = LocalizedStringResource("cab.spheresLabel", defaultValue: "what the chart says", table: table)
    static let fullReading = LocalizedStringResource("cab.fullReading", defaultValue: "Full reading", table: table)

    // MARK: — the day, told once
    static let yourDay = LocalizedStringResource("cab.yourDay", defaultValue: "Your day", table: table)
    static let skyBehind = LocalizedStringResource("cab.skyBehind", defaultValue: "The sky behind it", table: table)
    static let readWholeDay = LocalizedStringResource("cab.readWholeDay", defaultValue: "Read the whole day", table: table)

    // MARK: — the plan, said out loud
    //
    // The subscription was reachable and never offered: the owner walked the
    // whole app and never once saw it, or heard what it contains. A product
    // whose recurring revenue is invisible has no recurring revenue.
    static let plansTitle = LocalizedStringResource("cab.plans.title", defaultValue: "Everything open, every day", table: table)
    static let plansBody = LocalizedStringResource("cab.plans.body", defaultValue: "The plan keeps all eight systems open, sends the morning notification, rewrites your day as the sky moves — and Alma answers your questions in her deeper voice. Monthly or yearly.", table: table)
    static let plansCta = LocalizedStringResource("cab.plans.cta", defaultValue: "See the plans", table: table)
    static let skyEventBody = LocalizedStringResource(
        "cab.skyEvent.body",
        defaultValue: "Days like this are what the morning notification is for — it arrives at 08:00 when something in your chart is exact. Part of the plan.",
        table: table)

    /// The passive counter under the chat composer. Announced before the wall:
    /// the number arrives with every answer and was stored and never shown.
    static func questionsLeft(_ count: Int) -> LocalizedStringResource {
        LocalizedStringResource("cab.questionsLeft", defaultValue: "Questions left today: \(count)", table: table)
    }

    /// The row at the end of a finished chapter — door variant and plan variant.
    static let chapterEndDoor = LocalizedStringResource(
        "cab.chapterEnd.door",
        defaultValue: "The rest of this system is written the same way — from your positions, yours to keep.",
        table: table)
    static let chapterEndPlan = LocalizedStringResource(
        "cab.chapterEnd.plan",
        defaultValue: "This chapter is written once. Transits, the year and compatibility are rewritten as the sky moves — that is the plan.",
        table: table)

    /// The guest's deletion confirmation. A guest has no email to type; what
    /// they have is the account code, and the ask has to say so.
    static let deleteConfirmGuest = LocalizedStringResource(
        "cab.settings.deleteConfirmGuest", defaultValue: "Type this code to confirm", table: table)
    static let deleteGuestNote = LocalizedStringResource(
        "cab.settings.deleteGuestNote",
        defaultValue: "This account has no email attached. Its code is below — type it to confirm.",
        table: table)

    // MARK: — the chart, in words
    //
    // A placement used to be printed as "⊙ 9°52′ ♑︎ · H3", which asks a reader
    // to know four notations at once. These are the same facts spelled out, in
    // the reader's language, because a citation nobody can read cites nothing.

    static let ascendant = LocalizedStringResource("cab.ascendant", defaultValue: "Ascendant", table: table)
    /// "Sun in %@" — the free natal chapter's headline, naming the person's
    /// own sign instead of an abstract title.
    static let sunInSign = LocalizedStringResource("cab.sunInSign", defaultValue: "Sun in %@", table: table)
    /// The one line under a chapter title — what replaced the question
    /// subtitles the owner cut.
    static let fromYourPositions = LocalizedStringResource(
        "cab.fromYourPositions", defaultValue: "Written from your own positions", table: table)
    /// Over the blurred preview: what the button under it opens.
    static let previewNote = LocalizedStringResource(
        "cab.previewNote", defaultValue: "The chapter is written. The rest opens with the system.",
        table: table)
    static let unlock = LocalizedStringResource(
        "cab.unlock", defaultValue: "Unlock", table: table)

    // These three return `String` rather than `LocalizedStringResource`, and
    // it is the API's constraint rather than a choice: a `LocalizedStringResource`
    // key must be a `StaticString`, and these keys are built from a sign name,
    // a body name or a house number that only exist at runtime. `String(localized:)`
    // takes a runtime key and is the supported way to ask that question.
    //
    // The fallback is the engine's own word rather than the raw key, so a body
    // this table has not caught up with prints "Chiron" and not "cab.body.chiron".

    static func signName(_ key: String) -> String {
        localised("cab.sign.\(key)", fallback: key)
    }

    /// The major arcana, translated for display. The engine speaks English —
    /// "Justice", "The Star" — because factors are verbatim identifiers; a
    /// Russian reader still meets «Справедливость» on the row. Unknown names
    /// fall back to the engine's own word rather than to silence.
    static func arcanaName(_ english: String) -> String {
        let slug = english.lowercased()
            .replacingOccurrences(of: " ", with: "_")
        return localised("cab.arcana.\(slug)", fallback: english)
    }

    static func bodyName(_ key: String) -> String {
        localised(
            "cab.body.\(key)",
            fallback: key.replacingOccurrences(of: "_", with: " ").capitalized)
    }

    static func houseName(_ number: Int) -> String {
        localised("cab.house.\(number)", fallback: "house \(number)")
    }

    /// A fact-row label — "life path", "year ruler". These were hardcoded
    /// English on the one screen every system shares, which is how a Russian
    /// solar return shipped reading "year ruler ☽ moon".
    /// A citation, spoken in the reader's language at display time.
    ///
    /// The factor strings are identifiers and stay English in the data — the
    /// validator checks them character by character. But the synthesis
    /// factors are made of *words* («Character — 2 agree»), and the owner
    /// read them as untranslated UI. The mapping happens here, at the last
    /// moment before the screen, so the data underneath never drifts.
    static func localizedFactor(_ raw: String) -> String {
        var out = raw
        let axes = ["Direction", "Character", "Mind", "Relationships",
                    "Resources", "Work", "Weak point", "Growth", "Rhythms"]
        for name in axes {
            if let word = axis(name) {
                out = out.replacingOccurrences(of: name, with: String(localized: word))
            }
        }
        for (en, key) in [
            ("systems across nine axes", "cab.factor.acrossAxes"),
            ("seen by one", "cab.factor.seenByOne"),
            ("agree", "cab.factor.agree"),
            ("disagree", "cab.factor.disagree"),
        ] {
            out = out.replacingOccurrences(
                of: en,
                with: localised(key, fallback: en))
        }
        return out
    }

    static func factLabel(_ key: String, fallback: String) -> String {
        localised("cab.fact.\(key)", fallback: fallback)
    }

    /// A synastry score's name — the engine's key, spoken.
    static func scoreName(_ key: String) -> String {
        localised("cab.score.\(key)", fallback: key.replacingOccurrences(of: "_", with: " "))
    }

    private static func localised(_ key: String, fallback: String) -> String {
        let found = String(
            localized: String.LocalizationValue(key), table: table, bundle: .main)
        return found == key ? fallback : found
    }
    static let advice = LocalizedStringResource("cab.advice", defaultValue: "what to do with it", table: table)
    static let nextChapter = LocalizedStringResource("cab.nextChapter", defaultValue: "next", table: table)

    static func chapterCount(_ count: Int) -> LocalizedStringResource {
        LocalizedStringResource("cab.chapterCount", defaultValue: "\(count) chapters", table: table)
    }

    static func chapterProgress(_ index: Int, of total: Int) -> LocalizedStringResource {
        LocalizedStringResource("cab.chapterProgress", defaultValue: "\(index) of \(total)", table: table)
    }

    /// The door. **No price in it, on purpose** — Apple is the merchant of
    /// record and the only price a screen may show is StoreKit's own localised
    /// one, which the offer screen has and this one does not. The web app's
    /// version of this label carries `· $8.99`; carrying it here would be a
    /// price we made up for the storefront the buyer is actually in.
    static func openAllChapters(_ count: Int) -> LocalizedStringResource {
        LocalizedStringResource("cab.openAllChapters", defaultValue: "Open all \(count) chapters", table: table)
    }

    static func openSystemNamed(_ name: String) -> LocalizedStringResource {
        LocalizedStringResource("cab.openSystemNamed", defaultValue: "Open \(name)", table: table)
    }

    // MARK: — today

    static let activeNow = LocalizedStringResource("cab.activeNow", defaultValue: "active now", table: table)
    static let upcoming = LocalizedStringResource("cab.upcoming", defaultValue: "coming up", table: table)
    static let strongestAspects = LocalizedStringResource("cab.strongestAspects", defaultValue: "strongest aspects", table: table)
    static let acrossSystems = LocalizedStringResource("cab.acrossSystems", defaultValue: "across your systems", table: table)
    static let lunarDay = LocalizedStringResource("cab.lunarDay", defaultValue: "Lunar day", table: table)
    static let askAlma = LocalizedStringResource("cab.askAlma", defaultValue: "Ask Alma a question", table: table)
    static let readingChart = LocalizedStringResource("cab.readingChart", defaultValue: "Alma is reading your chart", table: table)
    static let noneActive = LocalizedStringResource(
        "cab.noneActive",
        defaultValue: "Nothing is in orb today. That is an answer, not an empty screen.",
        table: table
    )
    static let notPrediction = LocalizedStringResource(
        "cab.notPrediction",
        defaultValue: "Nothing here is a prediction. Every line names the placement it was read from.",
        table: table
    )
    static let notCalculated = LocalizedStringResource("cab.notCalculated", defaultValue: "not calculated", table: table)

    static func transitWindow(_ days: Int) -> LocalizedStringResource {
        LocalizedStringResource("cab.transitWindow", defaultValue: "next \(days) days", table: table)
    }

    // MARK: — birth data, people

    static let noBirthData = LocalizedStringResource("cab.noBirthData", defaultValue: "Add your birth date and I can read you.", table: table)
    static let addBirthData = LocalizedStringResource("cab.addBirthData", defaultValue: "Enter my birth data", table: table)
    static let needsBirthTime = LocalizedStringResource("cab.needsBirthTime", defaultValue: "This one needs your birth time.", table: table)
    static let addBirthTime = LocalizedStringResource("cab.addBirthTime", defaultValue: "Add my birth time", table: table)
    static let compatNeedsPerson = LocalizedStringResource(
        "cab.compatNeedsPerson",
        defaultValue: "Compatibility needs a second birth. Add somebody and the whole comparison is calculated free.",
        table: table
    )
    static let addAPerson = LocalizedStringResource("cab.addAPerson", defaultValue: "Add a person", table: table)

    // MARK: — cross-synthesis

    static let synthTitle = LocalizedStringResource("cab.synth.title", defaultValue: "Where eight traditions agree about you", table: table)
    static let synthLead = LocalizedStringResource(
        "cab.synth.lead",
        defaultValue: "Three agreeing is the closest thing to proof. Two disagreeing is more useful still — that's the conflict you keep living out.",
        table: table
    )
    static let synthSingle = LocalizedStringResource("cab.synth.single", defaultValue: "seen by one", table: table)
    static let rebuilds = LocalizedStringResource("cab.rebuilds", defaultValue: "Rebuilds itself when a system is added", table: table)

    static func synthAgree(_ count: Int) -> LocalizedStringResource {
        LocalizedStringResource("cab.synth.agree", defaultValue: "\(count) agree", table: table)
    }

    static func synthDisagree(_ count: Int) -> LocalizedStringResource {
        LocalizedStringResource("cab.synth.disagree", defaultValue: "\(count) disagree", table: table)
    }

    static func synthSingleCount(_ count: Int) -> LocalizedStringResource {
        LocalizedStringResource("cab.synth.singleCount", defaultValue: "\(count) seen by one", table: table)
    }

    /// The nine axes. The engine names them in English and that name is the
    /// key — an axis this build has never heard of keeps the engine's own word
    /// rather than vanishing, which is why this returns an optional and the
    /// caller falls back.
    static func axis(_ name: String) -> LocalizedStringResource? {
        switch name {
        case "Direction": LocalizedStringResource("cab.axis.Direction", defaultValue: "Direction", table: table)
        case "Character": LocalizedStringResource("cab.axis.Character", defaultValue: "Character", table: table)
        case "Mind": LocalizedStringResource("cab.axis.Mind", defaultValue: "Mind", table: table)
        case "Relationships": LocalizedStringResource("cab.axis.Relationships", defaultValue: "Relationships", table: table)
        case "Resources": LocalizedStringResource("cab.axis.Resources", defaultValue: "Resources", table: table)
        case "Work": LocalizedStringResource("cab.axis.Work", defaultValue: "Work", table: table)
        case "Weak point": LocalizedStringResource("cab.axis.Weak-point", defaultValue: "Weak point", table: table)
        case "Growth": LocalizedStringResource("cab.axis.Growth", defaultValue: "Growth", table: table)
        case "Rhythms": LocalizedStringResource("cab.axis.Rhythms", defaultValue: "Rhythms", table: table)
        default: nil
        }
    }

    // MARK: — the engine's English enums

    /// Element and phase arrive from the engine in English in every locale —
    /// they are data, not copy — so they are translated at the point they
    /// become a sentence, and an unknown value prints the engine's own word.
    static func element(_ name: String) -> LocalizedStringResource? {
        switch name {
        case "fire": LocalizedStringResource("cab.element.fire", defaultValue: "fire", table: table)
        case "earth": LocalizedStringResource("cab.element.earth", defaultValue: "earth", table: table)
        case "air": LocalizedStringResource("cab.element.air", defaultValue: "air", table: table)
        case "water": LocalizedStringResource("cab.element.water", defaultValue: "water", table: table)
        default: nil
        }
    }

    static func moonPhase(_ name: String) -> LocalizedStringResource? {
        switch name {
        case "new moon": LocalizedStringResource("cab.phase.new-moon", defaultValue: "new moon", table: table)
        case "waxing crescent": LocalizedStringResource("cab.phase.waxing-crescent", defaultValue: "waxing crescent", table: table)
        case "first quarter": LocalizedStringResource("cab.phase.first-quarter", defaultValue: "first quarter", table: table)
        case "waxing gibbous": LocalizedStringResource("cab.phase.waxing-gibbous", defaultValue: "waxing gibbous", table: table)
        case "full moon": LocalizedStringResource("cab.phase.full-moon", defaultValue: "full moon", table: table)
        case "waning gibbous": LocalizedStringResource("cab.phase.waning-gibbous", defaultValue: "waning gibbous", table: table)
        case "last quarter": LocalizedStringResource("cab.phase.last-quarter", defaultValue: "last quarter", table: table)
        case "waning crescent": LocalizedStringResource("cab.phase.waning-crescent", defaultValue: "waning crescent", table: table)
        default: nil
        }
    }

    // MARK: — settings

    static let settingsTitle = LocalizedStringResource("cab.settings.title", defaultValue: "Settings", table: table)
    static let settingsDate = LocalizedStringResource("cab.settings.date", defaultValue: "Date", table: table)
    static let settingsTime = LocalizedStringResource("cab.settings.time", defaultValue: "Time", table: table)
    static let settingsPlace = LocalizedStringResource("cab.settings.place", defaultValue: "Place", table: table)
    static let settingsFullName = LocalizedStringResource("cab.settings.fullName", defaultValue: "Full name at birth", table: table)
    static let settingsLanguage = LocalizedStringResource("cab.settings.language", defaultValue: "Language", table: table)
    static let languageNote = LocalizedStringResource(
        "cab.languageNote",
        defaultValue: "This is the language Alma writes in. The app itself follows your phone.",
        table: table
    )
    /// The door the note above describes.
    ///
    /// iOS gives an app no supported way to change its own interface language
    /// in-process, and the note alone named a setting on the phone without
    /// saying where. `openSettingsURLString` lands on this app's own page,
    /// where iOS lists every language the bundle carries.
    static let interfaceLanguageAction = LocalizedStringResource(
        "cab.settings.interfaceLanguageAction",
        defaultValue: "Change it in Settings",
        table: table
    )
    /// Not an empty field and not a guess: a birth with no time is a birth
    /// nobody knows the time of, and three of the eight systems say so.
    static let unknownTime = LocalizedStringResource("cab.unknownTime", defaultValue: "birth time unknown", table: table)
    static let settingsPlan = LocalizedStringResource("cab.settings.plan", defaultValue: "Plan", table: table)
    static let settingsMonthly = LocalizedStringResource("cab.settings.everythingMonthly", defaultValue: "Everything, monthly", table: table)
    static let settingsLetters = LocalizedStringResource("cab.settings.letters", defaultValue: "Letters", table: table)
    static let settingsLettersNote = LocalizedStringResource(
        "cab.settings.lettersNote",
        defaultValue: "Alma sends three: your sign-in link, a receipt for anything you buy, and a warning three days before a plan renews. All three are about something you did. There is no newsletter and nothing to unsubscribe from.",
        table: table
    )
    static let settingsExport = LocalizedStringResource("cab.settings.exportData", defaultValue: "Export my data", table: table)
    static let settingsDelete = LocalizedStringResource("cab.settings.deleteAccount", defaultValue: "Delete account", table: table)
    static let settingsDeleteConfirm = LocalizedStringResource("cab.settings.deleteConfirm", defaultValue: "Type your email address to confirm", table: table)

    static let birthDataLabel = LocalizedStringResource("cab.birthDataLabel", defaultValue: "birth data", table: table)
    static let dataAndLegal = LocalizedStringResource("cab.dataAndLegal", defaultValue: "data & legal", table: table)
    static let accountLabel = LocalizedStringResource("cab.accountLabel", defaultValue: "account", table: table)
    static let guest = LocalizedStringResource("cab.guest", defaultValue: "Guest", table: table)
    static let signIn = LocalizedStringResource("cab.signIn", defaultValue: "Sign in", table: table)

    static let planFree = LocalizedStringResource("cab.plan.freePlan", defaultValue: "Free", table: table)
    static let planFreeNote = LocalizedStringResource(
        "cab.plan.freeNote",
        defaultValue: "Every calculation is free. You pay for the words, one reading at a time.",
        table: table
    )
    static let planOwned = LocalizedStringResource("cab.plan.ownedPlan", defaultValue: "What you own", table: table)
    static let planOwnedNote = LocalizedStringResource("cab.plan.oneTimeNote", defaultValue: "Bought once. Yours permanently.", table: table)
    static let planAnnual = LocalizedStringResource("cab.plan.annualPlan", defaultValue: "Everything, for a year", table: table)
    static let planCancel = LocalizedStringResource("cab.plan.cancelSubscription", defaultValue: "Cancel subscription", table: table)
    static let planCancelWhat = LocalizedStringResource(
        "cab.plan.cancelWhat",
        defaultValue: "The next charge stops. Everything you have already paid for stays open until the end of the period — cancelling is not a refund, and we are not taking anything back.",
        table: table
    )
    static let planCancelling = LocalizedStringResource("cab.plan.cancelling", defaultValue: "Stopping the next charge…", table: table)
    static let planCancelledNoDate = LocalizedStringResource("cab.plan.cancelledNoDate", defaultValue: "Cancelled. Nothing more will be charged.", table: table)
    static let planCancelFailed = LocalizedStringResource(
        "cab.plan.cancelFailed",
        defaultValue: "We could not reach the payment processor, so nothing has changed. Try again in a moment.",
        table: table
    )
    static let planKeep = LocalizedStringResource("cab.plan.keepPlan", defaultValue: "Keep my plan", table: table)
    static let manageInStore = LocalizedStringResource("cab.manageInStore", defaultValue: "Manage this subscription in the App Store", table: table)
    static let managedByApple = LocalizedStringResource(
        "cab.managedByApple",
        defaultValue: "This plan was bought in the App Store, so Apple holds the payment method and the cancellation happens there.",
        table: table
    )

    static let exporting = LocalizedStringResource("cab.plan.exporting", defaultValue: "Preparing your file…", table: table)
    static let exportReady = LocalizedStringResource("cab.exportReady", defaultValue: "Your file is ready.", table: table)
    static let exportFailed = LocalizedStringResource("cab.plan.exportFailed", defaultValue: "The file could not be made. Try again in a moment.", table: table)
    static let exportNote = LocalizedStringResource("cab.exportNote", defaultValue: "Everything we hold about you, as one file.", table: table)
    static let saveFile = LocalizedStringResource("cab.saveFile", defaultValue: "Save the file", table: table)
    static let needsAccount = LocalizedStringResource("cab.plan.needsAccount", defaultValue: "This needs an account we can attach to you.", table: table)
    /// The web app's version of this says "in this browser". On a phone that
    /// is not merely wrong, it is confusing — so this one is written for the
    /// app rather than copied across, and translated with the rest.
    static let guestNote = LocalizedStringResource(
        "cab.guestNoteApp",
        defaultValue: "You are not signed in. Your chart lives on this phone only.",
        table: table
    )

    static let deleteWarning = LocalizedStringResource(
        "cab.plan.deleteWarning",
        defaultValue: "This erases your chart, your readings and your questions. Readings you paid for cannot be written again word for word.",
        table: table
    )
    static let deleteForever = LocalizedStringResource("cab.plan.deleteForever", defaultValue: "Delete everything, permanently", table: table)
    static let deleteMismatch = LocalizedStringResource("cab.plan.deleteMismatch", defaultValue: "That is not the address on this account.", table: table)
    static let deleteFailed = LocalizedStringResource("cab.plan.deleteFailed", defaultValue: "The account could not be deleted. Try again in a moment.", table: table)
    static let deleting = LocalizedStringResource("cab.plan.deleting", defaultValue: "Deleting…", table: table)
    static let keepAccount = LocalizedStringResource("cab.plan.keepAccount", defaultValue: "Keep my account", table: table)

    static let disclaimer = LocalizedStringResource(
        "cab.disclaimer",
        defaultValue: "For self-knowledge only. Not medical, psychological, legal or financial advice, and not a prediction of events.",
        table: table
    )

    /// **Which letters Alma sends, on a build where Apple is the merchant.**
    ///
    /// `settingsLettersNote` is the web's sentence and promises three, two of
    /// which Apple sends here. It is kept — a build selling through a card
    /// processor still needs it — and this is the one the app renders.
    static let lettersNoteStore = LocalizedStringResource(
        "cab.settings.lettersNoteStore",
        defaultValue: "Alma sends one: your sign-in link. Apple sends the receipt for anything you buy in the app and the warning before a plan renews, because Apple takes the payment. There is no newsletter and nothing to unsubscribe from.",
        table: table
    )

    static func renews(_ date: String) -> LocalizedStringResource {
        LocalizedStringResource("cab.plan.renews", defaultValue: "Renews \(date) · we email you 3 days before", table: table)
    }

    /// The same line for a plan Apple sold, which is the one this app usually
    /// shows. Apple charges it, Apple receipts it and Apple warns before it
    /// renews; saying we do would be a written promise about somebody else's
    /// charge.
    static func renewsAtStore(_ date: String) -> LocalizedStringResource {
        LocalizedStringResource(
            "cab.plan.renewsAtStore",
            defaultValue: "Renews \(date) · Apple charges it and warns you before it does",
            table: table
        )
    }

    static func renewsNoEmail(_ date: String) -> LocalizedStringResource {
        LocalizedStringResource(
            "cab.plan.renewsNoEmail",
            defaultValue: "Renews \(date) · add an email to be warned before it charges",
            table: table
        )
    }

    static func cancelled(until date: String) -> LocalizedStringResource {
        LocalizedStringResource("cab.plan.cancelled", defaultValue: "Cancelled. Your plan stays open until \(date).", table: table)
    }

    static func runsUntil(_ date: String) -> LocalizedStringResource {
        LocalizedStringResource("cab.plan.runsUntil", defaultValue: "Runs until \(date). It will not renew.", table: table)
    }

    static func planEnded(_ date: String) -> LocalizedStringResource {
        LocalizedStringResource("cab.plan.planEnded", defaultValue: "Your plan ended on \(date).", table: table)
    }

    static func merchantLine(_ merchant: String) -> LocalizedStringResource {
        LocalizedStringResource(
            "cab.merchantLine",
            defaultValue: "Payments processed by \(merchant) as merchant of record · VAT/GST included where applicable",
            table: table
        )
    }

    static func legal(_ document: LegalDocument) -> LocalizedStringResource {
        switch document {
        case .terms: LocalizedStringResource("cab.legal.terms", defaultValue: "Terms", table: table)
        case .privacy: LocalizedStringResource("cab.legal.privacy", defaultValue: "Privacy", table: table)
        case .refunds: LocalizedStringResource("cab.legal.refunds", defaultValue: "Refunds", table: table)
        case .subscriptionTerms: LocalizedStringResource("cab.legal.subscriptionTerms", defaultValue: "Subscription terms", table: table)
        case .imprint: LocalizedStringResource("cab.legal.imprint", defaultValue: "Imprint", table: table)
        }
    }
}

// MARK: — the eight, grouped

extension SystemSlug {

    /// What this system is called, in the reader's language.
    var displayName: LocalizedStringResource { L10nCabinet.system(self) }

    /// Which question it answers. The hub is grouped by the person's question
    /// and not by the name of the tradition — somebody who has never heard of a
    /// solar return still knows they want to know about this year.
    ///
    /// This is design metadata rather than API: the hub sends a slug and a
    /// status and nothing about grouping, exactly as it does on the web, where
    /// the same table lives in `src/lib/data.ts`.
    var group: SystemGroup {
        switch self {
        case .natal, .numerology, .birthCard: .whoAmI
        case .transits: .rightNow
        case .solarReturn: .thisYear
        case .compatibility: .howWeMatch
        case .astrocartography: .whereToBe
        case .synthesis: .allOfIt
        }
    }
}

/// The five questions plus the one that is all of them. In the order the hub
/// lists them.
enum SystemGroup: String, CaseIterable, Hashable, Sendable, Identifiable {
    case whoAmI
    case rightNow
    case thisYear
    case howWeMatch
    case whereToBe
    case allOfIt

    var id: String { rawValue }

    var title: LocalizedStringResource {
        switch self {
        case .whoAmI: L10nCabinet.groupWhoAmI
        case .rightNow: L10nCabinet.groupRightNow
        case .thisYear: L10nCabinet.groupThisYear
        case .howWeMatch: L10nCabinet.groupHowWeMatch
        case .whereToBe: L10nCabinet.groupWhereToBe
        case .allOfIt: L10nCabinet.groupAllOfIt
        }
    }
}

/// The five states the hub reports, and what each one is called.
///
/// The hub's `status` is a `String` and not an enum on the wire on purpose — a
/// state this build has never seen must degrade to an unfamiliar word rather
/// than blank the screen — so this returns an optional and the row prints the
/// backend's own token when it has no name for it.
enum HubStatus {

    static func label(_ status: String) -> LocalizedStringResource? {
        switch status {
        case "calculated": L10nCabinet.statusCalculated
        case "open": L10nCabinet.statusOpen
        case "needs-time": L10nCabinet.statusNeedsTime
        case "add-person": L10nCabinet.statusAddPerson
        case "not-yet": L10nCabinet.statusNotYet
        default: nil
        }
    }

    /// "calculated" means unlocked and "open" means computable but unpaid — and
    /// every calculation is free either way, so both are ready. Only the three
    /// that name something missing are not.
    static func isReady(_ status: String) -> Bool {
        status == "calculated" || status == "open"
    }
}

// MARK: — dates

/// Dates, said the way a person says them.
///
/// **A civil date is not an instant.** `birth_date` is "1998-03-14" with no
/// time zone; parsing it as a `Date` in the device's zone and formatting it
/// back makes it the 13th for anybody west of London. Everything here formats
/// civil dates in UTC and instants in the device's own zone, and the two
/// entry points are named so a call site cannot silently pick the wrong one.
///
/// **No month table.** The web app carries twelve month names per locale
/// because a browser cannot be trusted to have the right ones; iOS can, and
/// `Date.FormatStyle` also gets the *order* right — "14 March 1998" here,
/// "March 14, 1998" in the United States, "14. März 1998" in Germany — which a
/// hand-assembled string never does.
enum AlmaDate {

    private static let civilParser: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "UTC")
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    /// "1998-03-14" → "14 March 1998".
    static func readable(civil: String?) -> String? {
        guard let civil, let date = civilParser.date(from: String(civil.prefix(10))) else { return nil }
        return date.formatted(
            Date.FormatStyle(date: .long, timeZone: TimeZone(identifier: "UTC") ?? .gmt)
        )
    }

    /// An ISO-8601 instant → "12 April 2026". Truncated to the day: an
    /// entitlement expires at a moment, but "renews 12 April" is what anybody
    /// wants to know.
    static func readable(instant: String?) -> String? {
        guard let date = self.instant(instant) else { return nil }
        return date.formatted(date: .long, time: .omitted)
    }

    /// An instant → "19 March". No year, because everything it is used for
    /// sits inside a window of weeks; no weekday, because the strip is already
    /// dense.
    static func dayAndMonth(instant: String?) -> String? {
        guard let date = self.instant(instant) else { return nil }
        return date.formatted(.dateTime.day().month(.wide))
    }

    /// Parse one of the backend's instants.
    ///
    /// `String.almaInstant` handles the two shapes `ISO8601DateFormatter`
    /// knows, and the engine emits a third: `isoformat(timespec="minutes")`,
    /// which is "2026-08-06T21:10+00:00" — **no seconds**. The transit window,
    /// every transit's exact and leaves dates and the solar return's own moment
    /// are all written that way, and `ISO8601DateFormatter` refuses every one
    /// of them.
    ///
    /// Left alone it is not an error anywhere: the date simply disappears off
    /// the row, which is how it survived being written until somebody looked at
    /// the running app and saw a transit with no dates on it.
    ///
    /// Repaired here rather than in `String.almaInstant`, which belongs to the
    /// networking layer and is not this screen's to change.
    static func instant(_ value: String?) -> Date? {
        guard let value else { return nil }
        if let date = value.almaInstant { return date }
        return minutePrecision.date(from: value)
    }

    private static let minutePrecision: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mmXXXXX"
        return formatter
    }()
}
