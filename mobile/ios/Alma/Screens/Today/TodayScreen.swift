import SwiftUI

/// Tab 1 — what is crossing this chart right now.
///
/// This is the first screen an App Store reviewer opens, and Guideline 4.3(b)
/// names our category by name: fortune telling is refused *unless it offers a
/// meaningfully different or improved experience*, and 1.1.6 closes the "for
/// entertainment purposes" escape hatch. So what is different about Alma is put
/// here, above the fold, rather than buried three taps in:
///
/// * every transit row names **the natal placement it is read against**, and
///   prints the notation a chart prints;
/// * the cross-system block shows three named systems answering the same
///   question and, when they disagree, **says so** — the disagreement is given
///   the same weight as the agreement;
/// * the screen states in one line that nothing here is a prediction, which is
///   a claim about method rather than the disclaimer 1.1.6 refuses.
///
/// Four requests, deliberately unequal, following `src/app/(cabinet)/today`:
/// the transits are the screen; the natal chart supplies the moon line and the
/// positions; the synthesis supplies the counts and the first axis; the free
/// transits chapter supplies the one paragraph in Alma's voice. Each is allowed
/// to fail on its own — a synthesis that 503s must not take the day's transits
/// down with it.
struct TodayScreen: View {

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router
    @Environment(DailyModel.self) private var daily

    // `skyDetails` was the fold behind «Небо за словами» and is gone with it.
    // The facts it hid are no longer behind anything: the areas under the
    // horoscope name their own contacts and dates.

    @State private var model: TodayModel?

    var body: some View {
        ScreenScaffold(seed: 0x544F_4441) {
            header
                .riseIn(0)

            if session.hasBirthData {
                if let model {
                    day(of: model)
                }
            } else {
                // Nothing on this screen can be computed without a birth date —
                // but the answer is not one sentence and a button. This is the
                // first screen a reviewer opens and the one carrying the 4.3(b)
                // argument, and "Add your birth date and I can read you" is what
                // every horoscope app on the store also says. `EmptyArgument`
                // puts the eight systems, the forty-one chapters, a sample
                // citation and the refusal to predict in front of the wall.
                EmptyArgument { router.openJourney() }
            }
        }
        // **Keyed on the profile, and that is the whole fix.**
        //
        // A bare `.task` runs once per view identity, and all four tab stacks
        // stay alive for the life of the app, so this ran exactly once — at
        // launch, before anybody had entered a birth date, where it created the
        // model and returned at the `hasBirthData` guard. Finishing the journey
        // then dismissed the cover onto a screen whose identity had never
        // changed: the task did not re-fire, no request was ever issued, and
        // Today sat on "Alma is reading your chart" indefinitely. It is the
        // first thing every new user sees after handing over their birth data,
        // and a reviewer who finishes onboarding files it as a hang under 2.1.
        //
        // `.task(id:)` re-runs when the id changes, which is precisely when
        // there is something new to load: a profile arriving, or a different one
        // being selected.
        .task(id: session.profile?.id) {
            // Built here rather than in an initialiser: a `@State` initialised
            // in `init` is rebuilt on every parent render, and the session is
            // only reachable from the environment once the view exists.
            let model = model ?? TodayModel(client: session.client)
            self.model = model
            guard session.hasBirthData else { return }
            await model.load(locale: session.locale)
        }
        // The four tab stacks all stay alive, so this `task` runs once per
        // launch — which is right for a chapter and wrong for a screen called
        // Today: an app left open overnight would still be showing yesterday's
        // sky. Pulling asks the ephemeris again.
        // The daily is a subscriber feature, and the subscription can start
        // while this screen is on the stack — the paywall is a push from here,
        // and all four tab stacks stay alive for the life of the app. Keyed on
        // the flag rather than run once, so buying the plan makes the
        // invitation appear on the screen the person is standing on instead of
        // on their next cold launch.
        .task(id: session.entitlements.isSubscriber) {
            await daily.refresh(isSubscriber: session.entitlements.isSubscriber)
        }
        .refreshable {
            guard let model, session.hasBirthData else { return }
            await model.load(locale: session.locale)
        }
    }

    // MARK: — the top of the page

    private var header: some View {
        HStack(alignment: .top, spacing: 12) {
            headerText
            Spacer(minLength: 12)
            // The seal of the day: tonight's actual moon, with a spark per
            // contact perfecting today. New data every morning — the reason
            // to open this screen is drawn in its corner.
            if let moon = model?.moonNow {
                MoonMedallion(
                    illumination: moon.illumination,
                    waxing: moon.waxing,
                    sparks: model?.todaysSparks ?? []
                )
                .frame(width: 68, height: 68)
                .padding(.top, 26)
                .almaBreathing()
            }
        }
        .padding(.bottom, 4)
    }

    private var headerText: some View {
        VStack(alignment: .leading, spacing: 10) {
            // **The device's calendar day, not the server's window start.**
            //
            // The scan is run for `now` in UTC, so anybody far enough east of
            // Greenwich was shown yesterday's date on a screen called Today —
            // every evening, on the screen that also claims every line names the
            // placement it came from. A small wrongness there makes the large
            // claims beside it read as less careful.
            //
            // The transit window itself is still the server's and is still
            // printed on the section that owns it; what the scan is run *for*
            // is a backend question and is in the open problems.
            Text(verbatim: Date.now.formatted(.dateTime.day().month(.wide)))
                .almaOverline()

            Group {
                if let name = session.account?.displayName, !name.isEmpty {
                    Text(verbatim: name)
                } else {
                    Text(L10n.tabToday)
                }
            }
            .almaDisplayXL()

            if let moon = model?.moonLine {
                HStack(spacing: 8) {
                    Text(verbatim: "☽")
                        .font(AlmaFonts.display(19, relativeTo: .title3))
                        .foregroundStyle(Color.almaGoldBright)
                    Text(verbatim: moon).almaMeta()
                }
            }
        }
    }

    // MARK: — the day

    @ViewBuilder
    private func day(of model: TodayModel) -> some View {
        // **Above the paragraph, and above the strip.**
        //
        // The daily is what a person came back for, and it is the one block on
        // this screen that can be empty and still be an answer. Putting it first
        // means the day's one exact contact — or the honest absence of one — is
        // what a reader meets, and the rest of the screen (the paragraph, what
        // is still in orb, the cross-system block) is what surrounds it.
        //
        // **One telling of the day, under one name.**
        //
        // This screen used to say the same sky three times — a daily block
        // naming the exact contact, a written line describing it, and ACTIVE
        // NOW listing it again — under headers no ordinary reader could parse.
        // Two rounds of cutting later it was still three: «Твой день», a fold
        // called «Небо за словами», and «Точно сегодня». The owner asked what
        // the middle one was for and the honest answer was "the order we built
        // them in".
        //
        // Now one block called what people call it, and the plan is what opens
        // it — his decision, and the sharpest line the product has: the
        // calculations stay free for ever, the writing is what is sold.
        daySection(model)
            .riseIn(1)

        // The one contextual nudge the product allows itself: a rare sky —
        // a slow planet exact today — shown to somebody who is not paying for
        // the notification that would have told them. At most once a week,
        // silent for thirty days after a dismissal, gone for subscribers. The
        // frequency law is the design: an offer that appears on a schedule is
        // an ad; one that appears when the sky actually does something is
        // information with a door on it.
        if !session.entitlements.isSubscriber, let event = rareSkyEvent(model) {
            SkyEventCard(contact: event) {
                router.push(.offer(system: nil))
            }
            .riseIn(2)
        }

        // The second entrance to the setting, on the surface the content is on.
        //
        // `docs/PUSH.md §5.2` names a settings switch nobody finds as one of
        // the moments that look right and are not — the switch itself is
        // correct, what fails is a switch reachable *only* from a settings
        // list. This is the other entrance, and it sits **below** the day
        // rather than above it: a person who has just read what today actually
        // holds is deciding whether to be told about the next one, where a
        // person who has read nothing yet is being interrupted.
        if daily.shouldInvite(hasBirthData: session.hasBirthData) {
            DailyInvitation()
                .riseIn(3)
        }

        // Once, quietly: a guest with a chart worth keeping is invited to
        // attach an identity to it. The owner's call — «в какой-то момент
        // предложить зарегистрировать аккаунт, это действительно важно» —
        // and the second launch is the moment: the first is for the product.
        if SaveAccountCard.shouldShow(signedIn: session.isSignedIn, hasBirthData: session.hasBirthData) {
            SaveAccountCard(
                onSave: { router.push(.signIn, on: .settings) },
                onDismiss: {}
            )
            .riseIn(3)
        }

        Text(L10nCabinet.notPrediction)
            .almaMeta()
            .almaReadingWidth()
            .padding(.top, AlmaMetrics.gapLarge)
            .riseIn(4)

        ActionRow(label: L10nCabinet.askAlma) {
            router.tab = .alma
        }
        .riseIn(5)

        // **The plan, said in words, to somebody who does not have one.**
        //
        // It was reachable from a ladder that only opened if you first tapped a
        // locked chapter, and the owner\'s report is the whole finding: he
        // walked his own product end to end and never saw the subscription
        // offered, or learned what it includes. "One tap away in Settings" is
        // the sentence that turned out to be worth nothing — nobody opens
        // Settings to be sold something.
        //
        // Here, because this is the screen a subscriber would use every day and
        // therefore the screen where the reason for one is legible: the
        // transits above it move, and the chapter they bought does not. Hidden
        // the moment somebody subscribes, so it never sells what is already
        // owned.
        if !session.entitlements.isSubscriber {
            PlanInvitation {
                router.push(.offer(system: .natal))
            }
        }

        // The door, and only when there is one to offer. A system already paid
        // for must never be sold twice.
        if model.transitsLocked, !session.unlocked(.transits) {
            DoorButton(title: L10nCabinet.openSystemNamed(String(localized: SystemSlug.transits.displayName))) {
                router.push(.offer(system: .transits))
            }
        }
    }

    /// Alma's line about today, or the reason there isn't one.
    ///
    /// A locked answer draws nothing: the door at the foot of the screen is
    /// already the offer, and an error panel on top of it would say the same
    /// thing twice, worse. Everything else is said out loud — a Today with no
    /// paragraph and no explanation reads as a day with nothing in it.
    /// **«Гороскоп на сегодня».**
    ///
    /// Three blocks stood here — «Твой день», a fold-away «Небо за словами», and
    /// «Точно сегодня» underneath — and the owner read all three and asked what
    /// the middle one was for. Fairly: they were one subject cut into three by
    /// the order they were built in.
    ///
    /// This is the one block, under the name a person actually uses for what
    /// they came looking for. What is *inside* it is unchanged in kind and that
    /// is the whole point of the compromise: a horoscope by sun sign is written
    /// for one twelfth of humanity and cites nothing, and the day here is read
    /// from this person's own transits, with the date each one perfects. The
    /// word is theirs; the content stays ours.
    ///
    /// The areas below the prose are the shape borrowed from the category —
    /// work, love, money, the body — filled with real contacts and honest about
    /// the ones with nothing in them. See `engine/areas.py`.
    ///
    /// **Subscribers only**, on the owner's instruction: not the plan's opening
    /// paragraph, not a taste. A one-time purchase does not open it either.
    @ViewBuilder
    private func daySection(_ model: TodayModel) -> some View {
        CabinetSection(label: L10nCabinet.horoscopeToday) {
            if session.entitlements.isSubscriber {
                voice(model)
                if case .loaded(let result) = model.sky {
                    HoroscopeAreas(data: result.data)
                        .padding(.top, 4)
                }
            } else {
                // No first paragraph, no blur, no empty card. One sentence
                // saying what this is and where it lives, and the door.
                Text(L10nCabinet.horoscopeLocked)
                    .almaBody()
                    .almaReadingWidth()
                    .padding(.vertical, 6)
                ActionRow(label: L10nCabinet.horoscopeOpen) {
                    router.push(.offer(system: nil))
                }
            }
        }
    }

    @ViewBuilder
    private func voice(_ model: TodayModel) -> some View {
        switch model.line {
        case .loading:
            HStack(spacing: 12) {
                AlmaPresence(size: 24, ring: false)
                Text(L10nCabinet.readingChart).almaMeta()
            }
            .padding(.vertical, 12)

        case .loaded(let answer):
            // The whole day for a subscriber, the opening for everybody else —
            // with the rest one tap away, because the chapter it comes from is
            // the free one and pretending otherwise would be a lie with a
            // paywall drawn on it.
            if session.entitlements.isSubscriber, !answer.reading.body.isEmpty {
                VStack(alignment: .leading, spacing: 14) {
                    ForEach(Array(answer.reading.body.enumerated()), id: \.offset) { _, paragraph in
                        Text(verbatim: paragraph).almaDayVoice().almaReadingWidth()
                    }
                }
                .padding(.vertical, 6)
            } else {
                Text(verbatim: answer.reading.teaser.isEmpty
                     ? (answer.reading.body.first ?? "")
                     : answer.reading.teaser)
                    .almaDayVoice()
                    .almaReadingWidth()
                    .padding(.vertical, 6)

                ActionRow(label: L10nCabinet.readWholeDay) {
                    router.push(.chapter(system: .transits, chapter: "active"))
                }
            }

        case .failed(let error):
            switch error {
            case .locked:
                EmptyView()
            case .needsBirthTime:
                NeedMore(
                    message: L10nCabinet.needsBirthTime,
                    actionTitle: L10nCabinet.addBirthTime
                ) {
                    router.openJourney()
                }
            default:
                Text(error.displayText)
                    .almaMeta()
                    .almaReadingWidth()
                    .padding(.vertical, 6)
            }
        }
    }

    /// The day's rare event, if today has one and the frequency law allows it.
    private func rareSkyEvent(_ model: TodayModel) -> DailyContact? {
        let defaults = UserDefaults.standard
        let now = Date.now
        if let declined = defaults.object(forKey: "skyEventDeclinedAt") as? Date,
           now.timeIntervalSince(declined) < 30 * 24 * 3600 { return nil }
        if let shown = defaults.object(forKey: "skyEventShownAt") as? Date,
           now.timeIntervalSince(shown) < 7 * 24 * 3600 { return nil }

        let calendar = Calendar.current
        let event = model.dailyContacts.first { contact in
            guard let exact = contact.exact, calendar.isDateInToday(exact) else { return false }
            return DailyRule.slowBodies.contains(contact.transiting)
        }
        if event != nil { defaults.set(now, forKey: "skyEventShownAt") }
        return event
    }
}

/// The rare-sky card: one sentence, one door, one way to say no that is heard.
private struct SkyEventCard: View {

    let contact: DailyContact
    let onOpen: () -> Void

    @State private var dismissed = false

    var body: some View {
        if !dismissed {
            VStack(alignment: .leading, spacing: 10) {
                Text(verbatim: contact.notation)
                    .almaHeadingM()
                Text(L10nCabinet.skyEventBody)
                    .almaMeta()
                    .almaReadingWidth()
                HStack(spacing: 14) {
                    Button(action: onOpen) { Text(L10nCabinet.plansCta) }
                        .buttonStyle(.alma(.outline, fills: false))
                    Button {
                        // Thirty days of silence — a no that is remembered is
                        // the whole difference between an offer and a nag.
                        UserDefaults.standard.set(Date.now, forKey: "skyEventDeclinedAt")
                        withAnimation(AlmaMotion.ui) { dismissed = true }
                    } label: {
                        Text(PaywallL10n.notNow).almaMeta()
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.top, AlmaMetrics.gapLarge)
        }
    }
}

/// One transit, in notation.
///
/// **The title is words, and it used to be glyphs.** The old argument was that
/// two glyphs say in six languages what fourteen translated planet names would
/// — true, and beside the point, because the row is on the front page and the
/// people reading it do not know the glyphs. The names are translated now, so
/// the objection is answered rather than overruled.
private struct TransitRowView: View {

    let row: ChartFacts.Transit

    var body: some View {
        AlmaRow {
            VStack(alignment: .leading, spacing: 4) {
                Text(verbatim: row.notation)
                    .font(AlmaFonts.display(19, relativeTo: .headline))
                    .foregroundStyle(Color.almaInkLight)
                if !row.meta.isEmpty {
                    Text(verbatim: row.meta).almaMeta()
                }
            }
        } trailing: {
            // The natal factor the transit is read against. This is the
            // citation, and it is on the row rather than in a footnote.
            // The natal point this is read against, named. It was a glyph
            // beside a row that is now words, which read as a leftover.
            Text(verbatim: L10nCabinet.bodyName(row.readAgainst))
                .almaPositions()
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(verbatim: row.spoken))
    }
}

/// The horoscope's four headings, each holding this person's own sky.
///
/// **The form is borrowed and the content is not.** Work, love, money, the body
/// are the questions people arrive with, and every horoscope in the category
/// answers them in that order — so the order is taken and the sentences under
/// it are the reader's real transits, named, with the day each perfects. An
/// area with nothing in it says so, which is the line no sun-sign horoscope can
/// write and the clearest single proof that this one is computed.
///
/// The mapping from a natal point to an area lives on the server
/// (`engine/areas.py`), because it is a judgement about astrology rather than
/// about layout and both apps have to agree on it.
private struct HoroscopeAreas: View {

    let data: JSONValue

    /// The order the server reads them in, mirrored here so the two cannot
    /// silently disagree about which comes first.
    private static let order = ["work", "love", "money", "body"]

    var body: some View {
        let hits = (data["active"]?.arrayValue ?? [])
        VStack(alignment: .leading, spacing: 14) {
            ForEach(Self.order, id: \.self) { area in
                let mine = hits
                    .filter { $0["area"]?.stringValue == area }
                    .sorted { ($0["urgency"]?.doubleValue ?? 0) > ($1["urgency"]?.doubleValue ?? 0) }
                VStack(alignment: .leading, spacing: 3) {
                    Text(L10nCabinet.areaName(area))
                        .font(AlmaFonts.ui(13, weight: .medium))
                        .foregroundStyle(Color.almaGoldBright)
                    if let first = mine.first {
                        Text(verbatim: sentence(for: first))
                            .almaMeta()
                            .almaReadingWidth()
                    } else {
                        // Said plainly. An empty area filled with something
                        // would be the exact failure this screen exists to
                        // avoid.
                        Text(L10nCabinet.areaQuiet).almaMeta()
                    }
                }
            }
        }
    }

    /// "Сатурн и Середина неба: соединение, 14 августа."
    ///
    /// The same phrase template the transit rows and the daily use — see
    /// `DailyContact.notation` — so one contact reads identically wherever it
    /// appears. A date only when the engine has one: a contact already past
    /// exactness has none, and inventing "today" for it would be a small lie in
    /// the place this screen is least allowed one.
    private func sentence(for hit: JSONValue) -> String {
        let phrase = String(
            format: String(localized: DailyL10n.contactPhrase),
            L10nCabinet.bodyName(hit["transiting"]?.stringValue ?? ""),
            DailyL10n.aspectWord(hit["aspect"]?.stringValue ?? ""),
            L10nCabinet.bodyName(hit["natal"]?.stringValue ?? "")
        )
        guard let day = AlmaDate.dayAndMonth(instant: hit["exact"]?.stringValue) else {
            return phrase + "."
        }
        return "\(phrase), \(day)."
    }
}

// MARK: — the state behind it

/// Today's four requests and the handful of facts drawn out of them.
///
/// A model rather than four `@State`s in the view, for the reason the house
/// style gives: a view is a function of state and does no networking. It also
/// makes the four calls genuinely concurrent — in sequence they are four round
/// trips of latency before anything appears, and none of them is fast.
@MainActor
@Observable
final class TodayModel {

    private(set) var sky: ScreenState<CalcResult> = .loading
    private(set) var natal: ScreenState<CalcResult> = .loading
    private(set) var synthesis: ScreenState<CalcResult> = .loading
    private(set) var line: ScreenState<ReadingResponse> = .loading

    private let client: AlmaClient
    private var locale: AppLocale = .current

    init(client: AlmaClient) {
        self.client = client
    }

    func load(locale: AppLocale) async {
        self.locale = locale
        let client = self.client

        // Thirty days, matching the web app: the window is what the count on
        // the rule counts, and a year-wide scan reports a number about next
        // spring on a screen headed "today".
        let sky = almaLoad {
            try await client.compute(.transits, locale: locale, extra: ["days": .number(30)])
        }
        let natal = almaLoad { try await client.compute(.natal, locale: locale) }
        let synthesis = almaLoad { try await client.compute(.synthesis, locale: locale) }
        let line = almaLoad {
            try await client.reading(system: .transits, chapter: "active", locale: locale)
        }

        self.sky = await sky.value
        self.natal = await natal.value
        self.synthesis = await synthesis.value
        self.line = await line.value

        // One automatic second try for the day's text, and only for the
        // failures that a retry can actually change — the writing layer
        // hiccuping. The owner's word for the button was «бесит»: a person
        // should not be the retry loop for a transient fault. One retry,
        // never a loop; a refusal or a lock is an answer and is left alone.
        if case .failed(let error) = self.line,
           error.isTransient {
            try? await Task.sleep(for: .seconds(2))
            self.line = await almaLoad {
                try await client.reading(system: .transits, chapter: "active", locale: locale)
            }.value
        }
    }

    func reloadSky() async {
        let client = self.client
        let locale = self.locale
        sky = .loading
        sky = await almaLoad {
            try await client.compute(.transits, locale: locale, extra: ["days": .number(30)])
        }.value
    }

    /// One block at a time, because one block at a time is how they fail.
    ///
    /// Four requests leave together at launch and the dev backend, on SQLite,
    /// answers some of them with "database is locked" — which is a real thing
    /// that happens to a real person on a bad connection too. Retrying the
    /// whole screen would re-charge the reading; retrying the part that failed
    /// costs one request.
    func reloadNatal() async {
        let client = self.client
        let locale = self.locale
        natal = .loading
        natal = await almaLoad { try await client.compute(.natal, locale: locale) }.value
    }

    func reloadSynthesis() async {
        let client = self.client
        let locale = self.locale
        synthesis = .loading
        synthesis = await almaLoad { try await client.compute(.synthesis, locale: locale) }.value
    }

    // MARK: — what the screen reads

    /// The day the sky was computed for.
    var day: String? {
        guard let from = sky.value?.data["window"]?["from"]?.stringValue else { return nil }
        return AlmaDate.dayAndMonth(instant: from)
    }

    /// "full moon · 99%". The phase is an English enum from the engine and is
    /// translated here, where it becomes a sentence; the percentage is
    /// formatted by the system, so it reads as a percentage in every locale.
    var moonLine: String? {
        guard let moon = moonNow else { return nil }
        let name = L10nCabinet.moonPhase(moon.name).map { String(localized: $0) } ?? moon.name
        return "\(name) · \(moon.illumination.formatted(.percent.precision(.fractionLength(0))))"
    }

    /// Tonight's moon, from the transit payload's `sky_now` — the sky at the
    /// moment the day was computed, never the natal chart. The natal moon
    /// phase used to stand here, under today's date: the moon this person was
    /// born under, presented as tonight's.
    var moonNow: (name: String, illumination: Double, waxing: Bool)? {
        guard let moon = sky.value?.data["sky_now"]?["moon_phase"],
              let name = moon["phase"]?.stringValue,
              let lit = moon["illumination"]?.doubleValue else { return nil }
        return (name, lit, moon["waxing"]?.boolValue ?? true)
    }

    /// One flag per contact perfecting *today* — the medallion's sparks.
    /// `true` is a tense aspect, which takes the red accent.
    var todaysSparks: [Bool] {
        dailyContacts
            .filter { contact in
                contact.exact.map { Calendar.current.isDateInToday($0) } == true
            }
            .map { ["square", "opposition"].contains($0.aspect) }
    }

    /// True whether or not the chart is locked — it is one of the preview
    /// fields, which is exactly why the count on the rule stays honest while
    /// the events behind it are trimmed away.
    var activeCount: Int? {
        sky.value.flatMap { ChartFacts.activeCount($0.data) }
    }

    var transitsLocked: Bool { sky.value?.isLocked ?? false }

    /// Every contact in the payload, parsed for the daily's rule.
    ///
    /// Computed rather than stored, and read from the same `sky` result the
    /// strip below already draws from — so the daily block and the transit rows
    /// can never be about different requests. `DailyContact.all` merges
    /// `active` and `upcoming` and de-duplicates, because a contact perfecting
    /// later today is in both and one perfecting tomorrow is only in the second.
    var dailyContacts: [DailyContact] {
        sky.value.map { DailyContact.all(in: $0.data) } ?? []
    }

    var positions: [String] {
        guard let chart = natal.value?.data else { return [] }
        return [
            ChartFacts.placement(chart, body: "sun")
                ?? ChartFacts.signPill(mark: "☉", sign: chart["sun_sign"]?.stringValue),
            ChartFacts.placement(chart, body: "moon")
                ?? ChartFacts.signPill(mark: "☽", sign: chart["moon_sign"]?.stringValue),
            ChartFacts.ascendant(chart)
                ?? ChartFacts.signPill(mark: "ASC", sign: chart["rising_sign"]?.stringValue),
        ].compactMap { $0 }
    }

    var lunarDay: String? {
        natal.value?.data["lunar_day"]?.intValue.map(String.init)
    }

    var counts: ChartFacts.SynthesisCounts? {
        synthesis.value.flatMap { ChartFacts.synthesisCounts($0.data) }
    }

    /// The axis worth putting on the front page: a disagreement if there is
    /// one, because that is the more useful half of the promise — "two
    /// disagreeing is the conflict you keep living out" — and otherwise the
    /// first axis the engine returned.
    ///
    /// Empty for a locked synthesis, where `axes` is trimmed away entirely.
    var headlineAxis: ChartFacts.Axis? {
        guard let data = synthesis.value?.data else { return nil }
        let all = ChartFacts.axes(data)
        return all.first { $0.verdict == .disagree } ?? all.first
    }
}

#Preview {
    TodayScreen()
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
        .environment(PushService())
        .environment(DailyModel.preview())
}

/// The plan, offered where somebody can see why they would want it.
///
/// Not a ladder and not a price: the price is StoreKit's and belongs on the
/// offer screen, which is one tap away. This is the sentence that was missing
/// — what the plan contains and why a chapter bought once is not the same
/// thing.
private struct PlanInvitation: View {

    let onOpen: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(L10nCabinet.plansTitle).almaHeadingM()
            Text(L10nCabinet.plansBody).almaMeta().almaReadingWidth()

            Button(action: onOpen) {
                Text(L10nCabinet.plansCta)
            }
            .buttonStyle(.alma(.outline, fills: false))
            .padding(.top, 2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, AlmaMetrics.gapLarge)
    }
}
