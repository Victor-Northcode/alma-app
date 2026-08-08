import SwiftUI

/// V · where.
///
/// The one step the whole chart hangs on: the coordinate sets the horizon and
/// the zone sets the instant, so this is the only field in the journey that is
/// genuinely required. It searches the real gazetteer rather than accepting
/// free text, because "Springfield" typed into a box is a place we cannot draw
/// a chart from.
///
/// **Debounce and cancellation come from `.task(id:)` and not from a timer.**
/// SwiftUI cancels the previous task the moment the id changes, which cancels
/// the sleep *and* the in-flight `URLSession` request underneath it — exactly
/// what the web app builds by hand with a `setTimeout` and an `AbortController`.
/// Writing it as a timer here would mean also writing the cancellation, and the
/// bug that version has is that a slow answer for "Mil" lands after a fast one
/// for "Milan" and overwrites it.
struct StepPlace: View {

    @Bindable var journey: JourneyModel
    let onNext: () -> Void

    @Environment(AlmaSessionModel.self) private var session

    @State private var query: String = ""
    /// `nil` before anything worth searching for has been typed — which is a
    /// third state and needs to exist, because "no results" and "you have typed
    /// one letter" must not say the same thing.
    @State private var results: ScreenState<[Place]>?

    /// Whether the field holds the keyboard. Owned here rather than inside
    /// `JourneyTextField` because this step has to *give it up* — see `choose`.
    @FocusState private var typing: Bool

    /// How many suggestions are drawn. The backend is asked for eight; eight
    /// rows is 350 points of pinned control, which on a 874-point screen leaves
    /// no room for the button they lead to.
    private static let visibleSuggestions = 4

    var body: some View {
        JourneyScene(
            artHeight: 292,
            title: JourneyL10n.placeTitle,
            sub: JourneyL10n.placeSub
        ) {
            GlobeArt()
        } controls: {
            JourneyTextField(
                text: $query,
                placeholder: nil,
                label: JourneyL10n.searchPlace,
                submitLabel: .search,
                focus: $typing
            )
            .textContentType(.addressCity)

            suggestions

            Button(action: onNext) {
                Text(JourneyL10n.buildMySky)
            }
            .buttonStyle(.almaGold)
            .disabled(journey.place == nil)
        }
        .task(id: query) {
            await search()
        }
        .onAppear {
            // Coming back to this step shows what was chosen, rather than an
            // empty box under a filled-in answer.
            if query.isEmpty, let chosen = journey.place { query = chosen.label }
        }
    }

    @ViewBuilder
    private var suggestions: some View {
        VStack(spacing: 2) {
            // The optional is matched explicitly rather than through a
            // pattern promotion: "nothing has been asked yet" is a different
            // screen from "we asked and got nothing", and writing the `.none`
            // out is what keeps them from collapsing into each other.
            switch results {
            case .some(.loaded(let places)) where !places.isEmpty:
                ForEach(places.prefix(Self.visibleSuggestions)) { place in
                    JourneySuggestionRow(place: place, selected: journey.place?.id == place.id) {
                        choose(place)
                    }
                }

            case .some(.loaded):
                empty(JourneyL10n.noPlaces)

            case .some(.failed):
                // Offline and "no such place" look the same to somebody typing,
                // and the interface says the same thing about both — except
                // that this one is ours, so it says so.
                empty(L10n.stateOffline)

            case .some(.loading), .none:
                EmptyView()
            }
        }
        .padding(.horizontal, 6)
        .frame(maxWidth: .infinity, alignment: .leading)
        .animation(AlmaMotion.ui, value: journey.place?.id)
    }

    private func empty(_ text: LocalizedStringResource) -> some View {
        Text(text)
            .font(AlmaFonts.ui(14))
            .lineSpacing(3)
            .foregroundStyle(Color.almaMuted3)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 16)
            .padding(.vertical, 13)
    }

    /// A place was picked. The step collapses to the one filled field and the
    /// one enabled button.
    ///
    /// **All three of these are the fix, and the third is the one that matters.**
    /// Choosing used to fill the field and leave everything else exactly as it
    /// was: the keyboard stayed up, and because writing the label back into
    /// `query` re-ran the search, the list re-expanded to eight rows and covered
    /// "Build my sky" completely. Somebody who had just typed their birth city
    /// was left with no visible way forward on the last step before the ceremony.
    ///
    /// Clearing `results` is what collapses the list; `search()` then declines
    /// to refill it, because the query now equals the chosen label.
    private func choose(_ place: Place) {
        // The whole place, not just its name. The chart needs the coordinate
        // and the zone, and asking for either again later would be asking a
        // question this person has already answered.
        journey.place = place
        query = place.label
        results = nil
        typing = false
    }

    private func search() async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)

        // Two characters is the floor the backend's index is built for, and
        // asking for one is asking for every city on earth beginning with "a".
        guard trimmed.count >= 2 else {
            results = nil
            return
        }

        // Somebody who has just tapped a suggestion has not typed a new query;
        // re-running the search would replace their choice with the same list
        // and flash it. A cancelled `Task.sleep` throws, which is the signal
        // that a newer keystroke has arrived, and there is nothing to do.
        if trimmed == journey.place?.label { return }

        results = ScreenState<[Place]>.loading
        do {
            try await Task.sleep(for: .milliseconds(180))
        } catch {
            return
        }
        // Written out rather than through `ScreenState.load`, and it is not a
        // style choice: the closure that helper takes is `throws(AlmaError)`,
        // and a closure that also has to hop to the main actor to read
        // `session` loses the typed throw on the way — the compiler widens it
        // to `any Error` and then refuses the conversion back. A `do`/`catch`
        // here keeps `error` typed, which is the whole point of the enum.
        do {
            results = .loaded(try await session.client.searchPlaces(trimmed))
        } catch {
            results = .failed(error)
        }
    }
}
