import SwiftUI

/// Tab 2 — the hub: all eight systems and the state each is in.
///
/// Two decisions carried over from `src/app/(cabinet)/systems/page.tsx`, both
/// worth keeping.
///
/// **Grouped by the person's question, not by the name of the tradition.**
/// Nobody arrives knowing what a solar return is; everybody arrives wanting to
/// know about this year. The grouping is design metadata (`SystemSlug.group`) —
/// the hub sends a slug and a status and nothing else.
///
/// **Readiness comes before payment.** "calculated" means unlocked and "open"
/// means computable but not paid for, and *both* are ready, because every
/// calculation is free forever and only the writing is sold. Only the three
/// statuses that name something missing — a birth time, a second person, a
/// system not reached yet — fall through to the last group.
struct SystemsScreen: View {

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router

    @State private var portrait: ScreenState<CalcResult> = .loading

    var body: some View {
        ScreenScaffold(eyebrow: nil, title: nil, seed: 0x5359_5354) {
            header
                .riseIn(0)

            // The order of these three matters. "Has this person given us a
            // birth date" is asked first, off the session rather than off the
            // hub, because a hub that failed to load on a fresh install used to
            // put an offline failure in front of somebody who has nothing to
            // load yet — including a reviewer on a bad connection, on the screen
            // that is supposed to make the case for the product.
            if !session.hasBirthData {
                EmptyArgument { router.openJourney() }
            } else if let hub = session.hub, hub.hasBirthData {
                pills
                    .riseIn(1)
                groups(hub)
                synthesisBlock
                    .riseIn(6)
            } else {
                // There is a birth date and the hub does not know about it: that
                // load failed. Said, with a way to ask again — not an empty list
                // of systems that reads as "you have none".
                AlmaFailure(error: .offline) { await session.refreshHub() }
                    .frame(minHeight: 220)
            }
        }
        // Keyed, for the reason `TodayScreen` gives at length: the tab stacks
        // all stay alive, so a bare `.task` runs once at launch — before the
        // journey — and never again.
        .task(id: session.profile?.id) {
            // Skipped entirely until there is birth data: firing it regardless
            // is one guaranteed-failing request on every visit by somebody who
            // has not entered a date yet.
            guard session.hasBirthData, portrait.value == nil else { return }
            let client = session.client
            let locale = session.locale
            portrait = await almaLoad { try await client.compute(.natal, locale: locale) }.value
        }
    }

    // MARK: — the top of the page

    private var header: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(L10n.tabSystems).almaDisplayL()
            Spacer(minLength: 12)
            if let tally {
                Text(verbatim: tally)
                    .font(.almaNumeral)
                    .foregroundStyle(Color.almaGold)
            }
        }
    }

    /// "5/8", plus the word for it. Nothing at all until the hub answers — a
    /// dangling "calculated" with no number beside it reads as a rendering
    /// fault.
    private var tally: String? {
        guard let hub = session.hub else { return nil }
        let ready = hub.systems.filter { HubStatus.isReady($0.status) }.count
        return "\(ready)/\(hub.systems.count) \(String(localized: L10nCabinet.calculatedWord))"
    }

    /// The portrait: the three placements everybody came to see.
    ///
    /// There is deliberately no fallback behind it. A locked natal answer still
    /// names the three signs, which is what these pills show; a wrong sun sign
    /// on the front page would be a lie about the one number the person came
    /// for, so a failed chart draws nothing rather than something plausible.
    @ViewBuilder
    private var pills: some View {
        // Rows, not capsules. The owner's verdict on the stacked ovals was
        // aesthetic and final; the same three facts read better the way the
        // rest of the product prints a citation — the name quiet on the left,
        // the position in the serif on the right, a hairline between.
        let rows = portraitRows
        if !rows.isEmpty {
            VStack(spacing: 0) {
                ForEach(Array(rows.enumerated()), id: \.offset) { index, row in
                    FactRow(label: row.0, value: row.1, isPosition: true)
                }
            }
            .padding(.top, 2)
        }
    }

    private var portraitRows: [(String, String)] {
        guard let chart = portrait.value?.data else { return [] }
        func placement(_ body: String, fallbackSign: String) -> (String, String)? {
            let label = L10nCabinet.bodyName(body)
            if let raw = chart["placements"]?[body]?["formatted"]?.stringValue {
                let house = chart["placements"]?[body]?["house"]?.intValue
                    .map { " · " + L10nCabinet.houseName($0) } ?? ""
                return (label, ChartFacts.spellSigns(in: raw) + house)
            }
            if let sign = chart[fallbackSign]?.stringValue {
                return (label, L10nCabinet.signName(sign))
            }
            return nil
        }
        var rows: [(String, String)] = []
        if let sun = placement("sun", fallbackSign: "sun_sign") { rows.append(sun) }
        if let moon = placement("moon", fallbackSign: "moon_sign") { rows.append(moon) }
        if let raw = chart["angles"]?["formatted"]?["ascendant"]?.stringValue {
            rows.append((String(localized: L10nCabinet.ascendant), ChartFacts.spellSigns(in: raw)))
        } else if let sign = chart["rising_sign"]?.stringValue {
            rows.append((String(localized: L10nCabinet.ascendant), L10nCabinet.signName(sign)))
        }
        return rows
    }

    // MARK: — the eight

    @ViewBuilder
    private func groups(_ hub: Hub) -> some View {
        let entries = hub.systems.filter { $0.slug != .synthesis }
        let ready = entries.filter { HubStatus.isReady($0.status) }
        let pending = entries.filter { !HubStatus.isReady($0.status) }

        ForEach(Array(SystemGroup.allCases.enumerated()), id: \.element) { position, group in
            let rows = ready.filter { $0.slug.group == group }
            if !rows.isEmpty {
                CabinetSection(label: group.title) {
                    ForEach(rows) { entry in row(entry) }
                }
                .riseIn(2 + position)
            }
        }

        if !pending.isEmpty {
            // One heading covers a missing birth time, a missing person and a
            // system not reached yet alike: "not yet" is the one label true of
            // all three.
            CabinetSection(label: L10nCabinet.statusNotYet) {
                ForEach(pending) { entry in row(entry) }
            }
            .riseIn(5)
        }
    }

    private func row(_ entry: HubEntry) -> some View {
        SystemRow(system: entry.slug, status: entry.status) {
            // The one status that names a missing *person* rather than a
            // missing detail of the chart goes straight to the place that adds
            // one: a compatibility screen with nobody to compare against would
            // have "add somebody" as its only content.
            if entry.status == "add-person" {
                router.push(.people)
            } else {
                router.push(.system(entry.slug))
            }
        }
    }

    private var synthesisBlock: some View {
        CabinetSection(label: L10nCabinet.groupAllOfIt) {
            SystemRow(system: .synthesis, status: statusOfSynthesis) {
                router.push(.system(.synthesis))
            }
            // «Rebuilds itself when a system is added» stood here and said
            // nothing a person shopping for a reading needed — the owner cut it.
        }
    }

    private var statusOfSynthesis: String {
        session.status(of: .synthesis)?.status ?? "not-yet"
    }
}

#Preview {
    SystemsScreen()
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}
