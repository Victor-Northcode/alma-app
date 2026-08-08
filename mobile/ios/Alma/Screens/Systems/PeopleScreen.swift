import SwiftUI

/// The people this account has saved. Compatibility needs at least one.
///
/// It also answers the finding that `SystemScreen(.compatibility)` silently
/// compared against `session.people.first` with no picker and no name shown —
/// fine with one saved person, wrong with three. The chosen person lives here,
/// in the session's own list order, and the compatibility screen names whoever
/// it read.
struct PeopleScreen: View {

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router

    @State private var removing: Profile?

    var body: some View {
        ScreenScaffold(
            eyebrow: ScreenL10n.peopleEyebrow,
            title: ScreenL10n.peopleTitle,
            seed: 0x5045_4F50
        ) {
            Text(ScreenL10n.peopleLead).almaBody().almaReadingWidth()

            if session.people.isEmpty {
                NeedMore(
                    message: L10nCabinet.compatNeedsPerson,
                    actionTitle: L10nCabinet.addAPerson
                ) {
                    router.push(.addPerson)
                }
            } else {
                CabinetSection(label: ScreenL10n.peopleSaved, trailing: String(session.people.count)) {
                    ForEach(session.people) { person in
                        PersonRow(person: person) {
                            removing = person
                        }
                    }
                }

                Button { router.push(.addPerson) } label: {
                    Text(L10nCabinet.addAPerson)
                }
                .buttonStyle(.alma(.outline, fills: false))
                .padding(.top, AlmaMetrics.gapLarge)
            }

            // Whose birth data this is, and what we did about asking. The terms
            // ask the person entering it to have asked first; saying so at the
            // point of entry is worth more than saying it in a document.
            Text(ScreenL10n.peopleConsent)
                .almaMeta()
                .almaReadingWidth()
                .padding(.top, AlmaMetrics.gapLarge)
        }
        .task { await session.reloadProfiles() }
        // A birth is not something to delete on a single tap: every reading
        // keyed to it goes with it, and those are chapters somebody paid for.
        .confirmationDialog(
            Text(ScreenL10n.removePersonTitle),
            isPresented: Binding(get: { removing != nil }, set: { if !$0 { removing = nil } }),
            titleVisibility: .visible
        ) {
            Button(role: .destructive) {
                if let person = removing { Task { await remove(person) } }
            } label: {
                Text(ScreenL10n.removePerson)
            }
            Button(role: .cancel) { removing = nil } label: { Text(ScreenL10n.keep) }
        } message: {
            Text(ScreenL10n.removePersonWhat)
        }
    }

    private func remove(_ person: Profile) async {
        removing = nil
        try? await session.client.deleteProfile(id: person.id)
        await session.reloadProfiles()
        await session.refreshHub()
    }
}

/// One saved birth. Everything shown is what was entered — nothing computed,
/// nothing filled in.
private struct PersonRow: View {

    let person: Profile
    let remove: () -> Void

    var body: some View {
        AlmaRow {
            VStack(alignment: .leading, spacing: 4) {
                Text(verbatim: person.name?.isEmpty == false
                     ? person.name!
                     : String(localized: ScreenL10n.unnamedPerson))
                    .almaHeadingM()

                Text(verbatim: [
                    AlmaDate.readable(civil: person.birthDate),
                    person.birthTime.map { "\($0)" } ?? String(localized: L10nCabinet.unknownTime),
                    person.placeLabel,
                ].compactMap { $0 }.joined(separator: " · "))
                    .almaMeta()

                if let relation = person.relation, !relation.isEmpty {
                    Text(verbatim: relation).almaTag(.muted)
                }
            }
        } trailing: {
            Button(action: remove) {
                Text(ScreenL10n.remove)
                    .font(AlmaFonts.ui(13.5, weight: .medium))
                    .foregroundStyle(Color.almaDisagree.opacity(0.85))
            }
            .buttonStyle(.plain)
        }
    }
}

// MARK: — adding one

/// A second birth.
///
/// It asks the same five things the journey asks and in the same order, with two
/// differences that both come from what this is *for*: there is no ceremony
/// (nothing is being revealed, a comparison is being enabled), and it ends in
/// `session.addPerson(_:relation:)`, which sends `is_self: false` — the one call
/// in the app where that flag must be explicit, because "not said" on a second
/// birth would overwrite the account owner's own chart and every reading keyed
/// to it.
struct AddPersonScreen: View {

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router
    @Environment(\.dismiss) private var dismiss

    @State private var name = ""
    @State private var relation = ""
    @State private var day: Int?
    @State private var month: Int?
    @State private var year: Int?
    @State private var hour: Int?
    @State private var minute: Int?
    @State private var meridiem: Meridiem?
    @State private var timeUnknown = false
    @State private var place: Place?
    @State private var query = ""
    @State private var results: [Place] = []
    @State private var saving = false
    @State private var failure: String?

    @FocusState private var typingPlace: Bool

    /// Whether this device writes hours 1–12 with AM/PM. The journey asks the
    /// same question; a Russian phone shows a 24-hour pair and no meridiem
    /// field at all — «АМ или РМ» on a Russian form was the owner's finding.
    private let twelveHour = DateFormatter
        .dateFormat(fromTemplate: "j", options: 0, locale: .current)?
        .contains("a") ?? true

    /// The same 92 years the journey offers, and the same argument against a
    /// `DatePicker`: a wheel always has a value, so it opens on today and a
    /// person who taps past it has silently told us this person was born this
    /// morning.
    private static let years: [Int] = {
        let thisYear = Calendar(identifier: .gregorian).component(.year, from: .now)
        return (0..<92).map { thisYear - 10 - $0 }
    }()

    var body: some View {
        ScreenScaffold(
            eyebrow: ScreenL10n.addPersonEyebrow,
            title: ScreenL10n.addPersonTitle,
            seed: 0x4144_4450
        ) {
            Text(ScreenL10n.addPersonLead).almaBody().almaReadingWidth()

            fields

            if let failure {
                Text(verbatim: failure)
                    .almaMeta()
                    .foregroundStyle(Color.almaDisagree)
                    .almaReadingWidth()
            }

            Button {
                Task { await save() }
            } label: {
                Text(saving ? ScreenL10n.saving : ScreenL10n.savePerson)
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
            }
            .buttonStyle(.almaGold)
            .disabled(!isComplete || saving)
            .padding(.top, AlmaMetrics.gapLarge)
            // The consent note stood here and the owner cut it.
        }
        .task(id: query) { await search() }
    }

    @ViewBuilder
    private var fields: some View {
        CabinetSection(label: ScreenL10n.theirName) {
            PlainField(text: $name, placeholder: ScreenL10n.namePlaceholder)
            PlainField(text: $relation, placeholder: ScreenL10n.relationPlaceholder)
        }

        CabinetSection(label: ScreenL10n.theirBirthday) {
            HStack(spacing: 9) {
                JourneyMenuField(
                    placeholder: JourneyL10n.dayShort, label: JourneyL10n.day,
                    options: Array(1...31), title: { String($0) }, selection: $day
                )
                JourneyMenuField(
                    placeholder: JourneyL10n.monthShort, label: JourneyL10n.month,
                    options: Array(1...12), title: { JourneyL10n.monthName($0) }, selection: $month
                )
                .frame(maxWidth: .infinity)
                JourneyMenuField(
                    placeholder: JourneyL10n.yearShort, label: JourneyL10n.year,
                    options: Self.years, title: { String($0) }, selection: $year
                )
            }

            if let day, let month, let year, !JourneyDate.isReal(day: day, month: month, year: year) {
                Text(JourneyL10n.impossibleDate)
                    .almaMeta()
                    .foregroundStyle(Color.almaGoldBright)
            }
        }

        CabinetSection(label: ScreenL10n.theirBirthTime) {
            HStack(spacing: 9) {
                JourneyMenuField(
                    placeholder: JourneyL10n.hourLabel, label: JourneyL10n.hourLabel,
                    options: twelveHour ? Array(1...12) : Array(0...23),
                    title: { String(format: "%02d", $0) }, selection: $hour
                )
                JourneyMenuField(
                    placeholder: JourneyL10n.minuteLabel, label: JourneyL10n.minuteLabel,
                    options: Array(0...59), title: { String(format: "%02d", $0) }, selection: $minute
                )
                if twelveHour {
                    JourneyMenuField(
                        placeholder: JourneyL10n.meridiemLabel, label: JourneyL10n.meridiemLabel,
                        options: [0, 1], title: { $0 == 0 ? "AM" : "PM" },
                        selection: Binding(
                            get: { meridiem.map { $0 == .am ? 0 : 1 } },
                            set: { meridiem = $0.map { $0 == 0 ? .am : .pm } }
                        )
                    )
                }
            }
            .opacity(timeUnknown ? 0.4 : 1)
            .disabled(timeUnknown)

            HStack(spacing: 14) {
                JourneyToggle(isOn: $timeUnknown, label: ScreenL10n.addPersonTimeUnknown)
                Text(ScreenL10n.addPersonTimeUnknown).almaMeta()
            }
            .padding(.top, 10)

            if timeUnknown {
                Text(JourneyL10n.lockedWithoutTime).almaMeta().almaReadingWidth()
            }
        }

        CabinetSection(label: ScreenL10n.theirBirthplace) {
            PlainField(text: $query, placeholder: JourneyL10n.placePlaceholder, focus: $typingPlace)

            ForEach(results.prefix(4)) { candidate in
                JourneySuggestionRow(place: candidate, selected: place?.id == candidate.id) {
                    place = candidate
                    query = candidate.label
                    results = []
                    typingPlace = false
                }
            }
        }
    }

    private var isComplete: Bool {
        day != nil && month != nil && year != nil && place != nil
            && (timeUnknown
                || (hour != nil && minute != nil && (!twelveHour || meridiem != nil)))
    }

    private func search() async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 2, trimmed != place?.label else {
            results = []
            return
        }
        // The same 180ms as the journey's step, and the same reason: `.task(id:)`
        // cancels the sleep and the request under it when the next keystroke
        // arrives, so a slow answer for "Mil" cannot land after a fast one for
        // "Milan".
        guard (try? await Task.sleep(for: .milliseconds(180))) != nil else { return }
        results = (try? await session.client.searchPlaces(trimmed)) ?? []
    }

    private func save() async {
        guard let day, let month, let year, let place, !saving else { return }
        saving = true
        defer { saving = false }
        failure = nil

        // The same calendar check the journey does, for the same reason: a 31st
        // of February reaches the backend as a 422 that would surface here as a
        // bare "something went wrong".
        guard JourneyDate.isReal(day: day, month: month, year: year) else {
            failure = String(localized: JourneyL10n.impossibleDate)
            return
        }

        var time: String?
        if !timeUnknown, let hour, let minute {
            if twelveHour, let meridiem {
                time = String(format: "%02d:%02d", meridiem.hour24(from: hour), minute)
            } else if !twelveHour {
                time = String(format: "%02d:%02d", hour, minute)
            }
        }

        let birth = BirthInput(
            birthDate: String(format: "%04d-%02d-%02d", year, month, day),
            birthTime: time,
            latitude: place.latitude,
            longitude: place.longitude,
            timezone: place.timezone,
            placeLabel: place.label,
            placeId: place.id,
            name: name.trimmingCharacters(in: .whitespaces).isEmpty ? nil : name
        )

        do {
            _ = try await session.addPerson(
                birth,
                relation: relation.trimmingCharacters(in: .whitespaces).isEmpty ? nil : relation
            )
            // Straight back to where the comparison lives. `dismiss()` popped
            // one screen and landed on the people list — a stop nobody asked
            // for; the owner's report was «нажать назад и опять в
            // совместимость». Both people screens come off the stack at once.
            var path = router.paths[router.tab] ?? []
            while let last = path.last, last == .addPerson || last == .people {
                path.removeLast()
            }
            router.paths[router.tab] = path
        } catch {
            failure = error.serverMessage ?? String(localized: error.displayText)
        }
    }
}

/// A plain capsule field. The journey's is the same shape but carries the gold
/// focus glow that belongs to a ceremony; a form in the cabinet is quieter.
private struct PlainField: View {

    @Binding var text: String
    let placeholder: LocalizedStringResource
    var focus: FocusState<Bool>.Binding?

    @FocusState private var owned: Bool

    var body: some View {
        Group {
            let field = TextField(
                "", text: $text,
                prompt: Text(placeholder).foregroundStyle(Color.almaMuted3)
            )
            .font(.almaBodyFont)
            .foregroundStyle(Color.almaInkLight)
            .tint(Color.almaGoldBright)
            .autocorrectionDisabled()

            if let focus { field.focused(focus) } else { field.focused($owned) }
        }
        .padding(.horizontal, 20)
        .frame(minHeight: AlmaMetrics.fieldHeight)
        .background(Capsule().fill(Color.almaVeil))
        .accessibilityLabel(Text(placeholder))
    }
}

#Preview {
    NavigationStack { PeopleScreen() }
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}
