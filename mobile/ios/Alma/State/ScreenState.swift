import SwiftUI

/// What a screen is doing. Three cases, and every screen in the app uses these
/// three rather than inventing its own booleans.
///
/// The rule this exists to enforce: **loading and failure are states, not flags
/// bolted on.** A screen with `isLoading` and `error` and `data` has eight
/// possible combinations, six of which are nonsense — loading *and* failed,
/// loaded *and* failed, neither loading nor loaded nor failed — and every one of
/// those six is a blank screen or a spinner that never stops. Here there are
/// three, they are exhaustive, and the compiler says so.
///
/// `.loading` is the initial value, deliberately: there is no `.idle`. A screen
/// that has not asked for its data yet is a screen that is about to, and giving
/// it a fourth state to sit in is how a screen ends up never asking.
enum ScreenState<Value: Sendable>: Sendable {
    case loading
    case loaded(Value)
    case failed(AlmaError)

    var value: Value? {
        if case .loaded(let value) = self { return value }
        return nil
    }

    var error: AlmaError? {
        if case .failed(let error) = self { return error }
        return nil
    }

    var isLoading: Bool {
        if case .loading = self { return true }
        return false
    }

    /// Run an async load and land in the right case, once, in one line.
    ///
    /// ```swift
    /// state = await ScreenState.load { try await client.hub() }
    /// ```
    ///
    /// The closure's typed `throws(AlmaError)` is what makes this total: there
    /// is no `catch` for an error the enum has no case for.
    static func load(
        _ work: () async throws(AlmaError) -> Value
    ) async -> ScreenState<Value> {
        do {
            return .loaded(try await work())
        } catch {
            return .failed(error)
        }
    }
}

extension ScreenState: Equatable where Value: Equatable {}

/// The one rendering of the three states, so that loading looks the same on
/// every screen and a failure always offers the same way out.
///
/// A screen passes what to draw when it has something, and gets the other two
/// for free:
///
/// ```swift
/// ScreenStateView(state) { hub in
///     HubBody(hub: hub)
/// } retry: {
///     await load()
/// }
/// ```
struct ScreenStateView<Value: Sendable, Content: View>: View {

    let state: ScreenState<Value>
    @ViewBuilder let content: (Value) -> Content
    /// Called when the person taps "Try again". Omitted when there is nothing
    /// sensible to retry.
    var retry: (() async -> Void)?

    init(
        _ state: ScreenState<Value>,
        @ViewBuilder content: @escaping (Value) -> Content,
        retry: (() async -> Void)? = nil
    ) {
        self.state = state
        self.content = content
        self.retry = retry
    }

    var body: some View {
        switch state {
        case .loading:
            AlmaLoading()
        case .loaded(let value):
            content(value)
        case .failed(let error):
            AlmaFailure(error: error, retry: retry)
        }
    }
}

/// Waiting.
///
/// Not a `ProgressView`. A spinner is the house style of every app, and this one
/// is asked to wait while a chart is computed from an ephemeris and a chapter is
/// written — a wait with a *reason*, which is what the sentence says. Alma's own
/// point of light breathes; nothing spins, because the mark is never a loader.
struct AlmaLoading: View {
    /// Overridable so a chapter can say "Alma is writing this chapter…" where
    /// the hub says "Reading your sky…". The two waits are different lengths
    /// and the person deserves to know which one they are in.
    var message: LocalizedStringResource = L10n.stateLoading

    var body: some View {
        VStack(spacing: 22) {
            AlmaPresence(size: 56)
            Text(message)
                .almaMeta()
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .almaPadding()
        .accessibilityElement(children: .combine)
        .accessibilityLabel(Text(message))
    }
}

/// Something went wrong, said honestly.
///
/// The retry button appears only when retrying could work — `AlmaError`
/// answers that. A locked chapter does not unlock by asking again, and a button
/// that cannot succeed is worse than no button.
struct AlmaFailure: View {

    let error: AlmaError
    var retry: (() async -> Void)?

    var body: some View {
        VStack(spacing: 20) {
            AlmaStar(size: 28, variant: .flat)
                .opacity(0.5)

            Text(error.displayText)
                .almaBody()
                .multilineTextAlignment(.center)
                .almaReadingWidth()

            // The server's own sentence, underneath, when it said something
            // more specific than our generic line. Two sentences beat one
            // vague one, and this one arrives already translated.
            if let detail = error.serverMessage, !detail.isEmpty {
                Text(detail)
                    .almaMeta()
                    .multilineTextAlignment(.center)
            }

            if let retry, error.isRetryable {
                Button {
                    Task { await retry() }
                } label: {
                    Text(L10n.stateRetry)
                }
                .buttonStyle(.alma(.outline, fills: false))
                .padding(.top, 4)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .almaPadding()
    }
}

#Preview("States") {
    VStack(spacing: 0) {
        AlmaLoading()
        FadedRule()
        AlmaFailure(error: .offline, retry: {})
    }
    .nightSky()
}
