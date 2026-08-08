import SwiftUI

/// One saved conversation, read back.
///
/// Reached from the "earlier" menu on the Alma tab. It is deliberately
/// **read-only**: the composer lives on one screen, and a second place that can
/// send a question is a second place that can spend somebody's allowance, get
/// the thread id wrong, and disagree with the first about what was said. What
/// this screen is for is going back and finding the sentence again — which is
/// most of what anybody does with a conversation they had a week ago.
struct ThreadScreen: View {

    let threadID: String

    @Environment(AlmaSessionModel.self) private var session

    @State private var state: ScreenState<ChatThread> = .loading

    var body: some View {
        ScreenScaffold(
            eyebrow: L10n.tabAlma,
            title: nil,
            mood: .reading,
            seed: 0x5448_5244
        ) {
            ScreenStateView(state) { thread in
                Text(verbatim: thread.title ?? String(localized: ScreenL10n.untitledThread))
                    .almaDisplayL()
                    .padding(.bottom, 8)

                ForEach(thread.messages) { message in
                    ChatMessageView(message: message)
                        .padding(.bottom, AlmaMetrics.gapLarge)
                }
            } retry: {
                await load()
            }
        }
        .task { await load() }
    }

    private func load() async {
        let client = session.client
        let id = threadID
        state = .loading
        state = await almaLoad { try await client.thread(id: id) }.value
    }
}

// The copy of the message view that used to live here is gone: `ChatMessageView`
// in `ChatPieces.swift` draws both screens now. The two had silently diverged —
// this route's payload carries no `answered_from_chart`, so the same message
// showed a NOT FROM YOUR CHART tag in the live transcript and none when the
// thread was reopened. One view is what makes that class of disagreement
// impossible rather than merely fixed once.

#Preview {
    NavigationStack { ThreadScreen(threadID: "preview") }
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}
