import SwiftUI

/// One of the eight: its free calculation, its chapter list, its door.
///
/// **Every calculation is free and is shown in full.** A locked system still
/// answers with a real `CalcResult` — trimmed to its preview fields, with
/// `locked` set — and that data is the argument for buying the writing. Hiding
/// it is the one trim that can only lose money, which is why the panel at the
/// top of this screen draws whatever the payload carries and never asks whether
/// it was paid for.
///
/// Two requests, deliberately unequal, as on the web. The chapter list is the
/// frame — what the system contains, what is open, what is written. The
/// calculation is the content. Either may fail without the other.
struct SystemScreen: View {

    let system: SystemSlug

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router

    @State private var model: SystemModel?

    var body: some View {
        ScreenScaffold(seed: seed) {
            Text(system.displayName).almaDisplayL()

            if system == .compatibility, session.people.isEmpty {
                // Compatibility with nobody to compare against is not an error
                // and not an empty screen: it is one instruction.
                NeedMore(
                    message: L10nCabinet.compatNeedsPerson,
                    actionTitle: L10nCabinet.addAPerson
                ) {
                    router.push(.people)
                }
            } else if !session.hasBirthData {
                NeedMore(
                    message: L10nCabinet.noBirthData,
                    actionTitle: L10nCabinet.addBirthData
                ) {
                    router.openJourney()
                }
            } else if let model {
                if system == .compatibility { partnerLine }
                if system == .natal {
                    // **The natal screen follows the reference, not the funnel
                    // order.** The owner chose the shape every chart product
                    // uses: the wheel first, then the placements in words,
                    // then a free taste per sphere of life — each ending at
                    // the chapter that finishes the thought — and only then
                    // the chapter list and the door. The free preview *is*
                    // the funnel here: it demonstrates the writing, which the
                    // sixteen titles alone never did.
                    wheel(model)
                        .riseIn(0)
                    placementList(model)
                        .riseIn(1)
                    spheresSection(model)
                        .riseIn(2)
                    chapters(model)
                        .riseIn(3)
                    door(model)
                        .riseIn(4)
                    freeData(model)
                        .riseIn(5)
                } else {
                    // Every other system: what is sold leads, the free
                    // calculations stay complete below.
                    chapters(model)
                        .riseIn(0)
                    door(model)
                        .riseIn(1)
                    freeData(model)
                        .riseIn(2)
                }
            }
        }
        // Keyed on the partner as well as the profile: changing who this is
        // compared against has to recompute, and a `.task` with no id would keep
        // showing the first person's scores under the second person's name.
        .task(id: partnerKey) {
            let model = model ?? SystemModel(client: session.client, system: system)
            self.model = model
            guard session.hasBirthData else { return }
            await model.load(locale: session.locale, partner: partner?.id)
        }
    }

    /// Whoever compatibility is being read against.
    ///
    /// Still the first saved person, which is the only sensible default — but it
    /// is now *named on the screen*, with a way to change it. Silently comparing
    /// against `people.first` is fine with one saved person and wrong with
    /// three, and a compatibility score with no name attached is a number about
    /// nobody.
    private var partner: Profile? { session.people.first }

    private var partnerKey: String {
        "\(session.profile?.id ?? "-")|\(system == .compatibility ? (partner?.id ?? "-") : "-")"
    }

    @ViewBuilder
    private var partnerLine: some View {
        if let partner {
            VStack(alignment: .leading, spacing: 10) {
                Text(ScreenL10n.comparedWith(
                    partner.name?.isEmpty == false
                        ? partner.name!
                        : String(localized: ScreenL10n.unnamedPerson)
                ))
                .almaMeta()

                if session.people.count > 1 {
                    Button { router.push(.people) } label: {
                        Text(ScreenL10n.chooseSomebodyElse)
                    }
                    .buttonStyle(.alma(.veil, fills: false))
                }
            }
            .padding(.top, 4)
        }
    }

    /// A different sky per screen is what makes moving between two screens
    /// visibly moving; the same sky on the same screen is what stops the stars
    /// reshuffling when the list reloads. Derived from the slug so it is stable.
    private var seed: UInt64 {
        var value: UInt64 = 0x9E37_79B9
        for byte in system.rawValue.utf8 { value = value &* 31 &+ UInt64(byte) }
        return value
    }

    // MARK: — the free calculation

    @ViewBuilder
    private func freeData(_ model: SystemModel) -> some View {
        switch model.result {
        case .loading:
            AlmaLoading(message: L10nCabinet.readingChart)
                .frame(height: 160)

        case .failed(let error):
            switch error {
            case .needsBirthTime:
                NeedMore(
                    message: L10nCabinet.needsBirthTime,
                    actionTitle: L10nCabinet.addBirthTime
                ) {
                    router.openJourney()
                }
            default:
                AlmaFailure(error: error) { await model.reload() }
                    .frame(minHeight: 160)
            }

        case .loaded(let result):
            switch system {
            case .natal:
                NatalPanel(result: result)
            case .transits:
                TransitsPanel(result: result)
            case .synthesis:
                SynthesisPanel(result: result)
            default:
                FactsPanel(system: system, result: result)
            }

            // What could not be computed, said out loud rather than left as a
            // gap the reader has to notice. Houses without a birth time is the
            // usual one, and it is the engine's own sentence.
            if !result.unavailable.isEmpty {
                CabinetSection(label: L10nCabinet.notCalculated) {
                    ForEach(result.unavailable, id: \.self) { note in
                        Text(verbatim: note).almaMeta()
                    }
                }
            }
        }
    }

    // MARK: — the chapters

    @ViewBuilder
    private func wheel(_ model: SystemModel) -> some View {
        if case .loaded(let result) = model.result {
            NatalWheel(data: result.data)
                .padding(.vertical, 6)
        }
    }

    /// Every body, in words: "Sun — 21°13′ Virgo · 2nd house".
    @ViewBuilder
    private func placementList(_ model: SystemModel) -> some View {
        if case .loaded(let result) = model.result,
           let placements = result.data["placements"]?.objectValue {
            let order = ["sun", "moon", "mercury", "venus", "mars", "jupiter",
                         "saturn", "uranus", "neptune", "pluto", "true_node",
                         "chiron", "lilith"]
            CabinetSection(label: L10nCabinet.placementsLabel) {
                ForEach(order, id: \.self) { name in
                    if let placement = placements[name],
                       let formatted = placement["formatted"]?.stringValue {
                        let house = placement["house"]?.intValue
                        let retro = placement["retrograde"]?.boolValue == true
                        FactRow(
                            label: L10nCabinet.bodyName(name)
                                + (retro ? " · " + DailyL10n.retrogradeWord : ""),
                            value: ChartFacts.spellSigns(in: formatted)
                                + (house.map { " · " + L10nCabinet.houseName($0) } ?? ""),
                            isPosition: true
                        )
                    }
                }
            }
        }
    }

    /// The free taste: five spheres, two sentences each, the full reading one
    /// tap away. This is the screen's shop window and it is honestly free.
    @ViewBuilder
    private func spheresSection(_ model: SystemModel) -> some View {
        if system == .natal {
            switch model.spheres {
            case .loading:
                CabinetSection(label: L10nCabinet.spheresLabel) {
                    HStack(spacing: 12) {
                        AlmaPresence(size: 22, ring: false)
                        Text(L10nCabinet.readingChart).almaMeta()
                    }
                    .padding(.vertical, 10)
                }

            case .failed:
                // The preview is a bonus, not a wall: a screen that has the
                // wheel, the placements and the chapters loses nothing it
                // cannot live without. Silence over an error block here.
                EmptyView()

            case .loaded(let response):
                CabinetSection(label: L10nCabinet.spheresLabel) {
                    ForEach(response.spheres) { sphere in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(verbatim: sphere.title).almaHeadingM()
                            Text(verbatim: sphere.text)
                                .almaBody()
                                .almaReadingWidth()
                            ActionRow(label: L10nCabinet.fullReading) {
                                router.push(.chapter(system: .natal, chapter: sphere.chapter))
                            }
                        }
                        .padding(.vertical, 8)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func chapters(_ model: SystemModel) -> some View {
        CabinetSection(
            label: L10nCabinet.chapters,
            trailing: model.chapters.value.map { "\($0.total)" }
        ) {
            switch model.chapters {
            case .loading:
                AlmaLoading(message: L10n.stateLoadingShort).frame(height: 140)
            case .failed(let error):
                AlmaFailure(error: error) { await model.reload() }.frame(minHeight: 140)
            case .loaded(let list):
                ForEach(list.chapters) { entry in
                    ChapterRow(
                        entry: entry,
                        needsBirthTime: entry.needsBirthTime && !session.birthTimeKnown
                    ) {
                        router.push(.chapter(system: system, chapter: entry.slug))
                    }
                }
            }
        }
    }

    // MARK: — the door

    @ViewBuilder
    private func door(_ model: SystemModel) -> some View {
        if !session.unlocked(system), let total = model.chapters.value?.total {
            DoorButton(
                title: system == .natal
                    ? L10nCabinet.openAllChapters(total)
                    : L10nCabinet.openSystemNamed(String(localized: system.displayName))
            ) {
                router.push(.offer(system: system))
            }
            .padding(.top, AlmaMetrics.gap)
        }
    }
}

// MARK: — the panels

/// The natal chart: the positions everything else is read from, the dominant
/// element, and the tightest aspects.
private struct NatalPanel: View {

    let result: CalcResult

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            PillWrap(items: pills)

            if let element {
                PillWrap(items: [element], tone: .plain)
            }

            let aspects = ChartFacts.aspects(result.data, limit: 3)
            if !aspects.isEmpty {
                CabinetSection(label: L10nCabinet.strongestAspects) {
                    ForEach(aspects) { aspect in
                        AlmaRow {
                            Text(verbatim: aspect.notation)
                                .font(AlmaFonts.display(19, relativeTo: .headline))
                                .foregroundStyle(Color.almaInkLight)
                        } trailing: {
                            Text(verbatim: aspect.orb)
                                .font(.almaNumeral)
                                .foregroundStyle(colour(of: aspect.harmony))
                        }
                    }
                }
            }
        }
        .padding(.top, 6)
    }

    private var pills: [String] {
        let chart = result.data
        return [
            ChartFacts.placement(chart, body: "sun")
                ?? ChartFacts.signPill(mark: "☉", sign: chart["sun_sign"]?.stringValue),
            ChartFacts.placement(chart, body: "moon")
                ?? ChartFacts.signPill(mark: "☽", sign: chart["moon_sign"]?.stringValue),
            ChartFacts.ascendant(chart)
                ?? ChartFacts.signPill(mark: "ASC", sign: chart["rising_sign"]?.stringValue),
        ].compactMap { $0 }
    }

    /// The element arrives from the engine in English in every locale — it is
    /// data, not copy — so it is translated here, at the point it becomes a
    /// word on screen, and an element nobody has a name for prints its own.
    private var element: String? {
        guard let raw = ChartFacts.dominantElement(result.data) else { return nil }
        return L10nCabinet.element(raw).map { String(localized: $0) } ?? raw
    }

    /// The two semantic colours are reserved for agreement and disagreement,
    /// and a harmonious or tense aspect is exactly that: the chart agreeing or
    /// disagreeing with itself.
    private func colour(of harmony: ChartFacts.Harmony) -> Color {
        switch harmony {
        case .harmonious: .almaAgree
        case .tense: .almaDisagree
        case .neutral: .almaGoldBright
        }
    }
}

/// The transits, as a scan: how wide the window was, how many contacts are in
/// orb, and the first few of them.
private struct TransitsPanel: View {

    let result: CalcResult

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                if let days = ChartFacts.transitWindowDays(result.data) {
                    AlmaPill(text: String(localized: L10nCabinet.transitWindow(days)), tone: .plain)
                }
                if let count = ChartFacts.activeCount(result.data) {
                    AlmaPill(text: "\(count) \(String(localized: L10nCabinet.activeNow))")
                }
            }

            let active = ChartFacts.transits(result.data, key: "active", limit: 5)
            let ahead = ChartFacts.transits(result.data, key: "upcoming", limit: 5)

            ForEach(active) { row in contact(row) }

            if !ahead.isEmpty {
                SectionLabel(text: L10nCabinet.upcoming).padding(.top, 8)
                ForEach(ahead) { row in contact(row) }
            }
        }
        .padding(.top, 6)
    }

    private func contact(_ row: ChartFacts.Transit) -> some View {
        AlmaRow {
            VStack(alignment: .leading, spacing: 4) {
                Text(verbatim: row.notation)
                    .font(AlmaFonts.display(18, relativeTo: .headline))
                    .foregroundStyle(Color.almaInkLight)
                if !row.meta.isEmpty {
                    Text(verbatim: row.meta).almaMeta()
                }
            }
        } trailing: {
            Text(verbatim: ChartFacts.bodyGlyph(row.readAgainst)).almaPositions()
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(verbatim: row.spoken))
    }
}

/// The cross-synthesis: the counts, then every axis with the systems that
/// answered it.
///
/// This is the screen the 4.3(b) argument points at, so a *disagreement* is
/// never hidden behind a "see more" and the counts are shown even when the
/// axes behind them are locked — the shape of the answer is free, the reading
/// of it is what is sold.
private struct SynthesisPanel: View {

    let result: CalcResult

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(L10nCabinet.synthTitle).almaHeadingM()
            Text(L10nCabinet.synthLead).almaBody().almaReadingWidth()

            if let counts = ChartFacts.synthesisCounts(result.data) {
                SynthesisChips(counts: counts)
            }

            let axes = ChartFacts.axes(result.data)
            if !axes.isEmpty {
                CabinetSection(label: L10nCabinet.acrossSystems) {
                    ForEach(axes) { axis in AxisView(axis: axis) }
                }
            } else if let summary = result.data["summary"]?.stringValue {
                // Locked: the counts and the engine's one-line summary are all
                // that is left, and they are true. Nothing is dressed up to
                // fill the space the axes would have taken.
                Text(verbatim: summary).almaMeta().almaReadingWidth()
            }
        }
        .padding(.top, 6)
    }
}

/// Numerology, the birth card, the solar return, astrocartography,
/// compatibility: a handful of labelled facts each. The labels are the
/// engine's own vocabulary, which the dictionary has never had a word for in
/// any language — on the web either.
private struct FactsPanel: View {

    let system: SystemSlug
    let result: CalcResult

    var body: some View {
        let facts = ChartFacts.facts(for: system, data: result.data)
        VStack(alignment: .leading, spacing: 0) {
            ForEach(facts) { fact in
                FactRow(label: fact.label, value: fact.value, isPosition: true)
            }
        }
        .padding(.top, 6)
    }
}

// MARK: — the state behind it

@MainActor
@Observable
final class SystemModel {

    private(set) var result: ScreenState<CalcResult> = .loading
    private(set) var chapters: ScreenState<ChapterList> = .loading
    /// The free natal preview. Loaded for the natal system only; every other
    /// system leaves it `.loading` and never shows it.
    private(set) var spheres: ScreenState<SpheresResponse> = .loading

    private let client: AlmaClient
    private let system: SystemSlug
    private var locale: AppLocale = .current
    private var partner: String?

    init(client: AlmaClient, system: SystemSlug) {
        self.client = client
        self.system = system
    }

    func load(locale: AppLocale, partner: String?) async {
        self.locale = locale
        self.partner = partner
        await reload()
    }

    func reload() async {
        let client = self.client
        let system = self.system
        let locale = self.locale
        let extra = self.extra

        let result = almaLoad {
            try await client.compute(system, locale: locale, extra: extra)
        }
        let chapters = almaLoad { try await client.chapters(of: system, locale: locale) }

        self.result = await result.value
        self.chapters = await chapters.value

        // After the fast pair, not beside them: the first ask writes five
        // blocks with a model and takes seconds, and the wheel and chapter
        // list must not wait behind it.
        if system == .natal {
            self.spheres = await almaLoad { try await client.natalSpheres(locale: locale) }.value
            // One automatic second try, only for weather-class failures. The
            // owner's report was that the section needed a manual retry to
            // appear at all — a person should not be the retry loop.
            if case .failed(let error) = self.spheres, error.isTransient {
                try? await Task.sleep(for: .seconds(2))
                self.spheres = await almaLoad { try await client.natalSpheres(locale: locale) }.value
            }
        }
    }

    /// The per-system arguments. Loose JSON rather than a struct with every
    /// optional field on it, because the backend's request models forbid extra
    /// keys — `days` sent to numerology is a 422, not a shrug.
    private var extra: [String: JSONValue] {
        switch system {
        case .transits:
            ["days": .number(30)]
        case .compatibility:
            partner.map { ["other_profile_id": .string($0)] } ?? [:]
        default:
            [:]
        }
    }
}

#Preview {
    NavigationStack { SystemScreen(system: .natal) }
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}
