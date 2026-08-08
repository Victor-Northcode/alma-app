import Foundation
import Observation
import SwiftUI

/// What the journey collects, what it does with it, and nothing else.
///
/// It is separate from the views for the reason the house style gives: UI is a
/// function of state and there is no networking in a view. It is also separate
/// from `AlmaSessionModel`, which is deliberate — everything here is *in
/// progress* and most of it will never be saved, because most people abandon a
/// funnel. The session holds what is true about an account; this holds what
/// somebody has typed so far, and the one moment they meet is
/// `session.saveOwnBirth`.
///
/// **Nothing starts filled in.** Every field below is `nil` or empty, and there
/// is no default date, no default place and no assumed birth time. Each of
/// those was found in the web app and removed; reintroducing one here would be
/// the same bug in a new language.
@MainActor
@Observable
final class JourneyModel {

    /// The one journey in flight.
    ///
    /// A shared instance rather than `@State` on the cover, and it is the same
    /// decision the web app makes with its journey store: **✕ returns with
    /// state kept.** A `fullScreenCover` destroys its content when it is
    /// dismissed, so a model owned by the view would throw away five answers
    /// every time somebody closed the cover to check something — which is the
    /// exact moment they are least willing to type them all again.
    ///
    /// It is not a cache and it does not outlive the app: there is one journey
    /// per run, `reset()` empties it when one completes, and nothing is written
    /// to disk. A birth that has not been saved is a birth nobody asked us to
    /// keep.
    static let inFlight = JourneyModel()

    // MARK: — where we are

    /// Which scene is showing. It lives here rather than in the view for the
    /// same reason the answers do — closing the cover on step V and reopening
    /// it should not start again at step I.
    var step: JourneyStep = .name

    /// Whether the funnel has already been told this journey started. Opening
    /// and closing the cover is the same person on the same visit, and counting
    /// it twice makes the first drop-off rate look better than it is.
    private(set) var announced = false

    func announceStart(to client: AlmaClient) async {
        guard !announced else { return }
        announced = true
        await client.track(.quizStart)
    }

    /// Empty it, once a journey has run its course. Called on the way out, so
    /// that somebody who opens the journey again is asked rather than shown
    /// their own stale half-answers.
    func reset() {
        work?.cancel()
        work = nil
        step = .name
        name = ""
        gender = nil
        aboutAnswered = false
        day = nil
        month = nil
        year = nil
        hour = nil
        minute = nil
        meridiem = nil
        timeUnknown = false
        place = nil
        portrait = .loading
        savedProfile = nil
        announced = false
    }

    // MARK: — what has been collected

    /// Which of the four questions was loudest. `nil` until asked, and it stays
    /// `nil` if the step is skipped — the offer then falls back to the natal
    /// chart, which is what the web app does.

    /// Not an account and not required. An empty name means the portrait says
    /// "Sun in Pisces" rather than "Sofia · Sun in Pisces", and that is all.
    var name: String = ""

    /// "female" | "male" | nil — volunteered, never required. With it Alma's
    /// Russian agrees («ты родилась»); without it the genderless register
    /// stands, as it always did.
    var gender: String?
    /// Whether the "about you" step was answered at all — «не скажу» is an
    /// answer and deserves its selected state, which a bare nil cannot carry.
    var aboutAnswered: Bool = false
    var day: Int?
    /// 1…12. The *index*, never the word: "März" has to reach the backend as 3.
    var month: Int?
    var year: Int?

    var hour: Int?
    var minute: Int?
    var meridiem: Meridiem?

    /// Declared, rather than inferred from an empty hour. Both produce the same
    /// `nil` birth time, but only one of them is a person telling us something.
    var timeUnknown: Bool = false

    /// The whole place, not its name. The coordinate sets the horizon and the
    /// zone sets the instant; asking again later would be asking a question
    /// somebody already answered.
    var place: Place?

    // MARK: — what came back

    /// The saved birth and everything free that could be read from it. Starts
    /// `.loading` because the ceremony starts it — there is no state in which
    /// this screen is idle.
    private(set) var portrait: ScreenState<Portrait> = .loading

    /// Set once the birth is saved, so that a skipped-and-returned-to ceremony
    /// does not save a second profile.
    private(set) var savedProfile: Profile?

    // MARK: — derived

    /// Whether a real birth time was given.
    ///
    /// Declared unknown and never filled in are the same fact and both have to
    /// produce `nil` rather than a guess. The dangerous version of this reads
    /// an empty hour as zero and quietly sends midnight, which produces a
    /// confident and completely wrong Ascendant.
    /// Whether this phone writes times as 13:00 or as 1 PM.
    ///
    /// **AM/PM is a local convention and we were charging everybody for it.**
    /// The owner\'s note is the whole of it: outside the United States people
    /// do not use it and, worse, do not reliably know which half of the day
    /// "AM" is — a birth entered as 7 AM when it was 19:00 is a chart with the
    /// wrong Ascendant, the wrong houses and no way for anybody to notice. The
    /// twelve-hour clock is right for the people who think in it and a trap
    /// for everybody else.
    ///
    /// Asked of the system rather than of the language: `en-GB` is English and
    /// writes 24-hour, `es-US` is Spanish and writes 12-hour. The date format
    /// for a bare hour is what actually answers it.
    static var usesTwelveHourClock: Bool {
        let template = DateFormatter.dateFormat(fromTemplate: "j", options: 0, locale: .current)
        return template?.contains("a") ?? false
    }

    var hasTime: Bool {
        !timeUnknown && hour != nil && minute != nil
            && (!Self.usesTwelveHourClock || meridiem != nil)
    }

    /// Some of the birth time was given and some was not.
    ///
    /// A separate question from `hasTime`, and the reason it exists is that the
    /// two silences are not the same: nothing entered means "I do not know",
    /// which is a real answer, while an hour with no AM/PM means somebody was
    /// interrupted — and treating the second as the first throws away a birth
    /// time they did give us.
    var timePartiallyGiven: Bool {
        guard !timeUnknown else { return false }
        let given = Self.usesTwelveHourClock
            ? [hour != nil, minute != nil, meridiem != nil]
            : [hour != nil, minute != nil]
        return given.contains(true) && given.contains(false)
    }

    var dateComplete: Bool { day != nil && month != nil && year != nil }

    /// What the offer at the end is about. The natal chart, for everybody.
    ///
    /// This used to read the quiz's answer. With the quiz gone it is the same
    /// value the fallback always produced, and the natal chart is the right
    /// default anyway: sixteen chapters of the forty-one, and the one every
    /// other system is read against.
    var matchedSystem: SystemSlug { .natal }

    /// What the journey collected, as the backend takes it — or `nil` when a
    /// step that cannot be skipped somehow was.
    var birth: BirthInput? {
        guard let day, let month, let year, let place else { return nil }
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        return BirthInput(
            birthDate: String(format: "%04d-%02d-%02d", year, month, day),
            birthTime: twentyFourHour,
            latitude: place.latitude,
            longitude: place.longitude,
            timezone: place.timezone,
            placeLabel: place.label,
            placeId: place.id,
            name: trimmed.isEmpty ? nil : trimmed
        )
    }

    /// The clock, converted once. The arithmetic itself is on `Meridiem`, so the
    /// add-a-person form uses the same one rather than a second copy.
    private var twentyFourHour: String? {
        guard !timeUnknown, let hour, let minute else { return nil }
        // On a 24-hour phone the hour field already *is* the hour, so there is
        // nothing to convert and nothing to have got wrong.
        guard Self.usesTwelveHourClock else {
            return String(format: "%02d:%02d", hour, minute)
        }
        guard let meridiem else { return nil }
        return String(format: "%02d:%02d", meridiem.hour24(from: hour), minute)
    }

    // MARK: — the one write

    /// Save the birth and read back everything that costs nothing.
    ///
    /// **Called from under the ceremony**, which is the whole reason the
    /// ceremony is nine seconds long: it is the cover a round trip needs, so
    /// the portrait is already populated by the time anybody arrives at it.
    /// Not earlier — somebody who abandons at the time step has not asked us to
    /// keep anything. Not later — a spinner where the reward should be is the
    /// worst possible use of the moment the product first says "here is you".
    ///
    /// It is safe to call twice; the guards below are what make a skipped
    /// ceremony that is stepped back into harmless.
    ///
    /// **It is not `async`, and the task belongs to the model rather than to a
    /// view, which is the only interesting thing about it.** The obvious
    /// spelling — `await journey.begin(…)` inside the ceremony's `.task` — is
    /// wrong in a way that only shows up on a slow connection: the ceremony
    /// advances itself after nine seconds, SwiftUI tears the scene down, and
    /// tearing a scene down cancels its `.task`, which cancels the `URLSession`
    /// request underneath it. The save would be abandoned at exactly the moment
    /// it was most likely to still be running, and the portrait would say the
    /// person was offline. Owning the task here means it outlives every scene —
    /// and outlives the whole cover, deliberately: somebody who closes the
    /// journey during the ceremony has answered every question, and their birth
    /// should still be saved.
    func begin(with session: AlmaSessionModel) {
        guard work == nil else { return }
        work = Task { await self.run(with: session) }
    }

    private func run(with session: AlmaSessionModel) async {
        if savedProfile == nil {
            // The quiz completes here and not at the portrait. Every question
            // has been answered by the time the ceremony runs; the portrait is
            // the reward, and conflating "answered everything" with "saw the
            // result" hides exactly the people the save fails for.
            await session.client.track(.quizComplete)

            guard let birth else {
                // Only reachable if a required step was somehow passed empty.
                // The person is not told mid-ceremony — they are watching an
                // animation, not a form — but the portrait says so plainly a
                // moment later.
                portrait = .failed(.invalid(message: ""))
                return
            }

            do {
                savedProfile = try await session.saveOwnBirth(birth, gender: gender)
            } catch {
                portrait = .failed(error)
                return
            }
        }

        await loadPortrait(with: session)
    }

    /// The in-flight save-and-read. See `begin(with:)` for why it lives here.
    @ObservationIgnored private var work: Task<Void, Never>?

    /// Everything the cabinet opens onto, computed under the ceremony.
    ///
    /// The journey now ends in My Systems, so the nine seconds of animation
    /// cover the real work: every system that can be computed without a second
    /// person, plus the hub and the profile list the tab reads on arrival.
    /// Seven independent engines, run concurrently — in sequence they would
    /// spend seven round trips of the nine seconds available.
    ///
    /// Each is allowed to fail on its own: My Systems already knows how to say
    /// "not yet" per row, and **a missing line is honest, a placeholder is
    /// not**. Only the save fails the journey, because without a profile there
    /// is nothing to be incomplete about.
    func loadPortrait(with session: AlmaSessionModel) async {
        let client = session.client
        let locale = session.locale

        async let natal = client.compute(.natal, locale: locale)
        async let numerology = client.compute(.numerology, locale: locale)
        async let birthCard = client.compute(.birthCard, locale: locale)
        async let transits = client.compute(.transits, locale: locale, extra: ["days": .number(30)])
        async let solar = client.compute(.solarReturn, locale: locale)
        async let lines = client.compute(.astrocartography, locale: locale)
        async let synthesis = client.compute(.synthesis, locale: locale)

        let chart = try? await natal
        _ = try? await numerology
        _ = try? await birthCard
        _ = try? await transits
        _ = try? await solar
        _ = try? await lines
        _ = try? await synthesis

        // The tab the ceremony lands on reads the hub and the profile list
        // from the session — refreshed here, they are already on screen when
        // the cover lifts.
        await session.refreshHub()
        await session.reloadProfiles()

        portrait = .loaded(
            Portrait(
                system: matchedSystem,
                natal: chart,
                numerology: nil,
                birthCard: nil,
                freeChapter: nil
            )
        )
    }

    /// Ask again after the save failed. The only retry the journey offers, and
    /// the only one that could work.
    ///
    /// It drops the finished task rather than cancelling one: `begin` only ever
    /// returns after landing in `.loaded` or `.failed`, so a retry can only be
    /// tapped once there is nothing still running. A saved profile is kept — the
    /// birth is already stored and saving it twice would leave two.
    func retry(with session: AlmaSessionModel) {
        work = nil
        portrait = .loading
        begin(with: session)
    }
}


/// Half of the twelve-hour clock. An enum and not a string because "am", "AM"
/// and "a.m." are three ways to break the same comparison.
enum Meridiem: String, CaseIterable, Sendable, Identifiable {
    case am = "AM"
    case pm = "PM"

    var id: String { rawValue }

    /// The clock, converted once, in the one place that knows how.
    ///
    /// People say half past seven in the morning; the engine needs 07:30. The
    /// pair every naive conversion gets backwards is noon and midnight — 12 AM
    /// is 0 and 12 PM is 12 — and getting it backwards moves the Ascendant by
    /// half a circle while producing a chart that looks entirely reasonable.
    ///
    /// It lives on the type rather than as a private computed property on
    /// `JourneyModel` because there are now two screens that collect a birth
    /// time — the journey and "add a person" — and two copies of this arithmetic
    /// is one copy that will eventually be wrong for somebody else's chart.
    func hour24(from twelveHour: Int) -> Int {
        let hours = twelveHour % 12
        return self == .pm ? hours + 12 : hours
    }
}

/// Whether a day, month and year name a date that exists.
///
/// One place, for the same reason as `Meridiem.hour24`: the journey's date step
/// and the add-a-person form both have to catch the 31st of February before it
/// is sent, because the backend answers a 422 that would surface here as a bare
/// "something went wrong" and, in the journey, during a ceremony where nothing
/// can be said about it at all.
enum JourneyDate {
    static func isReal(day: Int, month: Int, year: Int) -> Bool {
        var components = DateComponents()
        components.year = year
        components.month = month
        components.day = day
        return Calendar(identifier: .gregorian).date(from: components) != nil
    }
}

/// The nine scenes, in order.
///
/// The web app inserts the date step conditionally, because there the date is
/// captured on the landing page and carried over. There is no landing here, so
/// the date is always asked and the sequence is fixed — which also means the
/// counter in the header can be derived from this enum instead of written down
/// and left to go stale.
enum JourneyStep: Int, CaseIterable, Sendable, Identifiable {
    // **The intent question is gone, and it was the owner's call.**
    //
    // It asked what was loudest in you right now and used the answer to pick
    // which system to offer at the end. The reasoning was sound and the
    // premise was not: all eight systems are computed for everybody, from the
    // same four facts, so nothing downstream actually needed the answer. It
    // bought one line of copy on the offer screen at the price of a whole
    // screen standing between somebody and the thing they came for.
    //
    // `matchedSystem` now answers `natal` for everyone, which is what the
    // fallback already did for anybody who skipped.
    case name
    case about
    case date
    case time
    case place
    case ceremony
    // The portrait, the offer and the handoff stood after the ceremony and
    // were cut whole — the owner's design: data in, one beautiful loading
    // ceremony while everything computes, then straight into My Systems,
    // where the portrait's three lines already live.

    var id: Int { rawValue }

    /// Roman, because the whole product numbers its chapters that way and this
    /// is the first place somebody meets that.
    var numeral: String {
        ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"][rawValue]
    }

    static var last: JourneyStep { .ceremony }

    /// The screen behind this one, or nothing on the first.
    var previous: JourneyStep? { JourneyStep(rawValue: rawValue - 1) }

    var next: JourneyStep? { JourneyStep(rawValue: rawValue + 1) }
}

/// Everything free that could be read from the birth, and nothing else.
///
/// It holds the raw `CalcResult`s rather than a flattened set of strings so
/// that the "was it calculated" question has exactly one answer per row: the
/// field is absent, or it is real. There is no place to put a default.
struct Portrait: Sendable, Equatable {

    let system: SystemSlug
    let natal: CalcResult?
    let numerology: CalcResult?
    let birthCard: CalcResult?
    let freeChapter: ChapterEntry?

    // MARK: — the natal preview
    //
    // Natal is not free, so this result arrives locked and trimmed to
    // `PREVIEW_FIELDS`: the three signs, the moon phase, the elemental balance
    // and whether the time was known. That is exactly what this screen shows,
    // which is not a coincidence — the preview was chosen to make this screen
    // possible without paying for it.

    var sunSign: String? { natal?.data["sun_sign"]?.stringValue }
    var moonSign: String? { natal?.data["moon_sign"]?.stringValue }
    /// Present only when the birth time was given: the backend refuses to
    /// compute a horizon without one, and this is the screen where that refusal
    /// is most worth showing rather than hiding.
    var risingSign: String? { natal?.data["rising_sign"]?.stringValue }
    var moonPhase: String? { natal?.data["moon_phase"]?["phase"]?.stringValue }

    var lifePath: Int? { numerology?.data["life_path"]?.intValue }

    var birthCardName: String? { birthCard?.data["personality"]?["name"]?.stringValue }
    var birthCardNumeral: String? { birthCard?.data["personality"]?["numeral"]?.stringValue }

    /// Whether there is anything at all to show. Every request can fail, and a
    /// portrait of nobody is a screen that has to say so rather than draw an
    /// empty frame around a name.
    var isEmpty: Bool {
        sunSign == nil && lifePath == nil && birthCardName == nil && freeChapter == nil
    }
}
