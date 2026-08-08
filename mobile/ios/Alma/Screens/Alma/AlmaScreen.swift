import SwiftUI

/// Tab 3 — the conversation.
///
/// Free forever at three questions a day; a door adds a one-time bundle of
/// fifteen on the better model, and when that runs out it falls back to the free
/// three rather than ending the conversation. The limit arrives as
/// `AlmaError.questionLimit` with the server's own sentence, which already says
/// when the questions come back — so this screen prints that rather than
/// inventing its own arithmetic about somebody's allowance.
///
/// **This is where the 4.3(b) argument is easiest to lose and easiest to keep.**
/// A chat that answers anything is a chatbot with an astrology skin. Alma's
/// answers carry `cited_factors` — the placements the answer was read from — and
/// `answered_from_chart`, which is `false` when she could not read it from the
/// chart and said so. Both are rendered: the citations under the answer, and the
/// honest admission as an admission rather than dressed up as a reading.
///
/// **Not a scaffold.** Every other cabinet screen is a scrolling column with a
/// title on top; a conversation is a transcript pinned to the bottom with a
/// composer under it, so this screen builds its own shape and calls
/// `.nightSky()` itself — which it must, because a navigation container fills
/// itself opaquely and there is nowhere further up the tree to put one.
struct AlmaScreen: View {

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router

    @State private var model: ChatModel?
    @FocusState private var composing: Bool

    /// The home indicator's height, measured rather than looked up.
    ///
    /// It used to come from `CabinetTabBar.homeIndicator`, which reads the key
    /// window — and on the first layout pass of a tab that has not been shown
    /// yet there is no key window, so it answered 0 and was never asked again.
    /// The composer then sat 34 points too low and the field was cut in half by
    /// the tab bar, which is the bug the owner photographed twice.
    ///
    /// A geometry reader is asked at the moment the view is laid out and asked
    /// again whenever that changes, which is the property the static lookup did
    /// not have. 34 as the initial value rather than 0: on the phones this ships
    /// to it is the common case, so the first frame is right rather than wrong.
    @State private var bottomInset: CGFloat = 34

    /// The keyboard's height, from the platform's own notifications.
    ///
    /// The third attempt at this layout, and the one that stops guessing. The
    /// first read the field's focus and padded to zero — focus and the
    /// keyboard's actual frame are not the same clock, and the composer fell
    /// behind the keys in the gap between them, which is what the owner
    /// photographed. The notification carries the keyboard's end frame at the
    /// moment the animation is decided, which is the one number that cannot
    /// disagree with the screen.
    @State private var keyboard: CGFloat = 0

    var body: some View {
        VStack(spacing: 0) {
            header
            if let model {
                transcript(model)
                composerBlock(model)
            }
        }
        // With the keyboard up the composer sits on the keys; at rest it sits
        // above the tab bar. One padding, from two measured numbers — the
        // keyboard's frame and the home indicator — and no third state.
        .padding(.bottom, keyboard > 0
                 ? max(keyboard - bottomInset, 0) + 8
                 : AlmaMetrics.tabBarHeight)
        .ignoresSafeArea(.keyboard, edges: .bottom)
        .onReceive(NotificationCenter.default.publisher(
            for: UIResponder.keyboardWillChangeFrameNotification)
        ) { note in
            guard
                let end = note.userInfo?[UIResponder.keyboardFrameEndUserInfoKey] as? CGRect,
                let screen = UIApplication.shared.connectedScenes
                    .compactMap({ ($0 as? UIWindowScene)?.screen.bounds }).first
            else { return }
            let overlap = max(screen.maxY - end.minY, 0)
            withAnimation(.easeOut(duration: 0.25)) { keyboard = overlap }
        }
        .onReceive(NotificationCenter.default.publisher(
            for: UIResponder.keyboardWillHideNotification)
        ) { _ in
            withAnimation(.easeOut(duration: 0.25)) { keyboard = 0 }
        }
        .background {
            GeometryReader { proxy in
                Color.clear
                    .onAppear { bottomInset = proxy.safeAreaInsets.bottom }
                    .onChange(of: proxy.safeAreaInsets.bottom) { _, new in bottomInset = new }
            }
            .ignoresSafeArea()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .nightSky(.reading, seed: 0x414C_4D43)
        .task {
            let model = model ?? ChatModel(client: session.client)
            self.model = model
            await model.loadThreads()
        }
    }

    /// The composer and the quiet counter above it — a sibling of the
    /// transcript, never an inset: an inset's position is negotiated with the
    /// scroll view and the safe area, and that negotiation is exactly where
    /// three attempts at this screen have gone wrong. A sibling is where the
    /// VStack puts it, full stop.
    @ViewBuilder
    private func composerBlock(_ model: ChatModel) -> some View {
        // **The wall is visible the moment the last question is spent.** The
        // field used to stay open at zero and the refusal arrived only on the
        // next tap — so the owner asked three things and concluded there is
        // no limit at all. A composer that takes typing it will refuse is a
        // lie of layout; at zero the block *is* the wall, and the wall sells
        // the plan.
        if model.questionsLeft == 0, !session.entitlements.isSubscriber {
            VStack(spacing: 12) {
                Text(ScreenL10n.chatOutOfQuestions)
                    .almaMeta()
                    .multilineTextAlignment(.center)
                Button {
                    router.sheet = .offer(system: nil)
                } label: {
                    Text(L10nCabinet.plansCta)
                }
                .buttonStyle(.alma(.outline, fills: false))
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 6)
        } else {
            VStack(spacing: 8) {
                if let left = model.questionsLeft, (1...3).contains(left) {
                    Text(L10nCabinet.questionsLeft(left))
                        .almaMeta()
                        .frame(maxWidth: .infinity)
                }

                Composer(
                    text: Binding(get: { model.draft }, set: { model.draft = $0 }),
                    sending: model.sending,
                    focus: $composing
                ) {
                    await model.send(profileID: session.profile?.id, locale: session.locale)
                }
            }
        }
    }

    // MARK: — the top

    private var header: some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(L10n.tabAlma).almaOverline()
            Rectangle()
                .fill(Color.almaGold.opacity(0.28))
                .frame(height: AlmaMetrics.hairline)
                .alignmentGuide(.firstTextBaseline) { _ in -4 }

            // Every earlier conversation, as a menu rather than a second screen
            // listing them. There are only ever a handful, each is one line, and
            // a list screen whose every row is a title would be a screen that
            // exists to hold a list of one thing.
            if let past = model?.threads.value?.threads, past.count > 1 {
                Menu {
                    ForEach(past) { thread in
                        Button {
                            router.push(.thread(id: thread.id))
                        } label: {
                            Text(verbatim: thread.title ?? String(localized: ScreenL10n.untitledThread))
                        }
                    }
                } label: {
                    Text(ScreenL10n.pastQuestions).almaTag(.gold)
                }
            }
        }
        .almaPadding()
        .padding(.top, 14)
        .padding(.bottom, 10)
    }

    // MARK: — the transcript

    @ViewBuilder
    private func transcript(_ model: ChatModel) -> some View {
        ScrollViewReader { scroller in
            ScrollView {
                VStack(alignment: .leading, spacing: AlmaMetrics.gapLarge) {
                    if model.messages.isEmpty {
                        opening(model)
                    }

                    ForEach(model.messages) { message in
                        ChatMessageView(message: message)
                            .id(message.id)
                    }

                    if model.sending {
                        ThinkingLine()
                            .id(ChatModel.bottomAnchor)
                    }

                    if let refusal = model.refusal {
                        RefusalView(error: refusal) {
                            // A sheet over the conversation, selling the thing
                            // that was actually exhausted. This used to push a
                            // *natal door* onto the *Systems tab* — it yanked
                            // the person off their own conversation to offer a
                            // product that does not grant a single question.
                            // `.offer(system: nil)` is the plans-first ladder:
                            // annual, monthly, then the archive.
                            router.sheet = .offer(system: nil)
                        }
                        .id(ChatModel.bottomAnchor)
                    }

                    Color.clear.frame(height: 1).id(ChatModel.bottomAnchor)
                }
                .almaPadding()
                .padding(.top, 6)
                .padding(.bottom, AlmaMetrics.gapLarge)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .scrollIndicators(.hidden)
            .scrollContentBackground(.hidden)
            .scrollDismissesKeyboard(.interactively)
            .onChange(of: model.messages.count) {
                withAnimation(AlmaMotion.ui) { scroller.scrollTo(ChatModel.bottomAnchor, anchor: .bottom) }
            }
            .onChange(of: model.sending) {
                withAnimation(AlmaMotion.ui) { scroller.scrollTo(ChatModel.bottomAnchor, anchor: .bottom) }
            }
        }
    }

    /// What the screen says before anybody has asked anything.
    ///
    /// It is not an empty state with an illustration. It states, in Alma's voice,
    /// the one rule that makes this different from a chatbot — she answers from
    /// the chart and says so when she cannot — and then offers three questions
    /// that are worth asking.
    ///
    /// **The three are about this person.** `ChatOpeners` reads their sun, moon
    /// and rising out of the free natal preview and phrases a question about
    /// each; until that arrives, or if it never does, the written three stand in.
    /// Tapping one fills the field rather than sending it — a question that
    /// spends one of three free questions a day on a tap somebody made to see
    /// what it said would be a trap.
    @ViewBuilder
    private func opening(_ model: ChatModel) -> some View {
        VStack(alignment: .leading, spacing: 18) {
            AlmaPresence(size: 56)
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.vertical, 8)

            Text(session.hasBirthData ? ScreenL10n.chatOpening : ScreenL10n.chatNoChart)
                .almaVoice()
                .almaReadingWidth()

            Text(ScreenL10n.chatRule).almaMeta().almaReadingWidth()

            if session.hasBirthData {
                VStack(alignment: .leading, spacing: 0) {
                    Text(ScreenL10n.chatCouldAsk)
                        .almaOverline()
                        .padding(.bottom, 10)

                    ForEach(Array(model.openers.enumerated()), id: \.offset) { _, prompt in
                        Button {
                            model.draft = prompt
                            composing = true
                        } label: {
                            AlmaRow {
                                Text(verbatim: prompt)
                                    .font(.almaBodyFont)
                                    .foregroundStyle(Color.almaBody.opacity(0.9))
                                    .multilineTextAlignment(.leading)
                            } trailing: {
                                Text(verbatim: "→")
                                    .font(AlmaFonts.display(15, relativeTo: .footnote))
                                    .foregroundStyle(Color.almaGold.opacity(0.55))
                            }
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.top, 4)
            } else {
                NeedMore(
                    message: L10nCabinet.noBirthData,
                    actionTitle: L10nCabinet.addBirthData
                ) {
                    router.openJourney()
                }
            }
        }
        // **Attached here rather than beside `loadThreads`, and keyed on the
        // profile.** The launch sequence races: `RootView` builds all four tab
        // stacks at once, so this screen's `.task` can run before
        // `AlmaSessionModel.start()` has fetched the profile, and a one-shot
        // load would see `nil`, skip, and leave the written questions up for
        // the rest of the session. Keyed on the id, it runs again the moment
        // the profile arrives — and again after somebody adds their birth data
        // in the journey, which is the other way this goes from nothing to a
        // chart.
        .task(id: session.profile?.id) {
            await model.loadOpeners(profileID: session.profile?.id, locale: session.locale)
        }
    }
}

// MARK: — when there is no answer

/// Something went wrong, said the way Alma would say it.
///
/// **A status code is not a voice.** The three failures a person actually meets
/// here — no network, the model unavailable, and a question she could not answer
/// without inventing a placement — used to print `error.serverMessage`, which
/// for the last of those is `str(exc)`: untranslated engineering prose from
/// `conversation.py`, shown verbatim to a reader in Portuguese. Each of them now
/// has a sentence of our own, in six languages, in the first person.
///
/// The one exception is the question limit, which keeps the backend's sentence:
/// it is already localised there, and it already says *when the questions come
/// back* — a number this screen would have to re-derive from the tier to say
/// itself, and get wrong the day the tiers change.
private struct RefusalView: View {

    let error: AlmaError
    let openOffer: () -> Void

    private var sentence: String {
        switch error {
        case .questionLimit:
            error.serverMessage ?? String(localized: ScreenL10n.chatOutOfQuestions)
        case .needsBirthTime, .locked:
            error.serverMessage ?? String(localized: error.displayText)
        case .refused:
            String(localized: ScreenL10n.chatRefused)
        case .offline:
            String(localized: ScreenL10n.chatOffline)
        case .unavailable:
            String(localized: ScreenL10n.chatUnavailable)
        default:
            String(localized: ScreenL10n.chatWentWrong)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(verbatim: sentence)
                .almaBody()
                .almaReadingWidth()

            switch error {
            case .questionLimit:
                // The server's sentence already sells the plan; the button
                // is the door. Plans-first, because the plan is the only
                // thing that carries the conversation on.
                Button(action: openOffer) { Text(ScreenL10n.moreQuestions) }
                    .buttonStyle(.alma(.outline, fills: false))
            default:
                EmptyView()
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: — the composer

/// The field and the one button.
///
/// A `safeAreaInset` on the transcript rather than the last row of it, so the
/// keyboard lifts it instead of covering it — the same fix, for the same reason,
/// as the journey's controls.
private struct Composer: View {

    @Binding var text: String
    let sending: Bool
    var focus: FocusState<Bool>.Binding
    let send: () async -> Void

    private var canSend: Bool {
        !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !sending
    }

    var body: some View {
        HStack(alignment: .bottom, spacing: 10) {
            TextField(
                "",
                text: $text,
                prompt: Text(ScreenL10n.askPlaceholder).foregroundStyle(Color.almaMuted3),
                axis: .vertical
            )
            .lineLimit(1...5)
            .font(.almaBodyFont)
            .foregroundStyle(Color.almaInkLight)
            .tint(Color.almaGoldBright)
            .focused(focus)
            // No `.submitLabel(.send)`. The field is `axis: .vertical` with
            // `lineLimit(1...5)`, so Return inserts a newline and there is no
            // `onSubmit` to fire — the keyboard was promising a send key that
            // did nothing, which is a worse lie than a plain Return key. The
            // alternative was to add `onSubmit` and send on Return, and it was
            // rejected: someone typing a long message about their week needs
            // the line break more than they need to save one tap on the arrow,
            // and the longest question in the study was 1,990 characters.
            .padding(.horizontal, 18)
            .padding(.vertical, 12)
            .frame(minHeight: AlmaMetrics.buttonHeightVeil)
            .background(
                RoundedRectangle(cornerRadius: 24, style: .continuous).fill(Color.almaVeil)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .stroke(Color.almaGold.opacity(focus.wrappedValue ? 0.55 : 0.28), lineWidth: 1)
            )
            .accessibilityLabel(Text(ScreenL10n.askPlaceholder))

            Button {
                Task { await send() }
            } label: {
                // The arrow is type, in the serif, like every other arrow in the
                // product — not `Image(systemName:)`, which would be the one SF
                // Symbol on a screen full of drawn marks.
                Text(verbatim: "→")
                    .font(AlmaFonts.display(20, relativeTo: .title3))
                    .foregroundStyle(canSend ? Color.almaInkOnGold : Color.almaMuted3)
                    .frame(width: 46, height: 46)
                    .background(
                        Circle().fill(
                            canSend ? AnyShapeStyle(AlmaGradient.goldButton)
                                    : AnyShapeStyle(Color.almaVeil))
                    )
            }
            .buttonStyle(.plain)
            .disabled(!canSend)
            .accessibilityLabel(Text(ScreenL10n.send))
        }
        .almaPadding()
        .padding(.top, 10)
        .padding(.bottom, 8)
        .background(alignment: .top) { Hairline() }
    }
}

// MARK: — the state behind it

@MainActor
@Observable
final class ChatModel {

    /// The id the transcript scrolls to. A constant rather than the last
    /// message's id, because the thing to keep in view is the *bottom* — which
    /// during a send is a spinner with no message behind it.
    static let bottomAnchor = "alma.bottom"

    private(set) var messages: [ChatMessage] = []
    private(set) var sending = false
    /// The last refusal, kept out of `messages` because it is not something Alma
    /// said — it is something the system did.
    private(set) var refusal: AlmaError?
    private(set) var threads: ScreenState<ChatThreadList> = .loading
    private(set) var questionsLeft: Int?

    /// The three questions the empty state offers. The written three until the
    /// natal preview arrives, then three about this person's own chart. Never
    /// empty, so the opening never draws a heading with nothing under it.
    private(set) var openers: [String] = ChatOpeners.written

    var draft: String = ""

    private var threadID: String?
    private let client: AlmaClient

    init(client: AlmaClient) {
        self.client = client
    }

    /// The conversations on this account, if there is an account.
    ///
    /// **The guard is the whole point of it.** `GET /v1/chat/threads` takes
    /// `CurrentUser`, and `CurrentUser` mints an account for a caller that
    /// arrives without a token — that is what it is for, and it is right for
    /// every route somebody reaches by doing something. This one is reached by
    /// launching the app: `RootView.cabinet` builds all four tab stacks at once
    /// in a `ZStack` so that a tab switch does not throw away scroll position
    /// and half-typed text, which means this screen's `.task` runs on a cold
    /// launch whether or not anybody ever opens the Alma tab.
    ///
    /// Measured on an erased iPhone 17 Pro against an empty database: a launch
    /// issued `/v1/billing/catalogue`, `/v1/billing/entitlements` and
    /// `/v1/chat/threads`, and `select count(*) from user` went from 0 to 2.
    /// Two, because the last two race and only one of the tokens they mint can
    /// be kept — so every install also left an orphan account that nothing
    /// could ever reach again, and the installation id was claimed by whichever
    /// won. `AlmaSessionModel.start()` had already been fixed not to mint and
    /// was not the leak; these two screens were, and they leak on 100% of
    /// installs because a launch is 100% of installs.
    ///
    /// A device with no account has no threads to list, so there is nothing to
    /// ask and nothing is lost by not asking. `.loaded` with an empty list
    /// rather than leaving `.loading`: the initial state is `.loading` by
    /// design and a screen that returns without resolving it is a spinner that
    /// never stops. This is not an empty answer we are inventing — it is
    /// exactly what the server would have said, one account later.
    ///
    /// The same guard, in the same words, is in `AccountModel.loadPlan` and in
    /// the four refreshers on `AlmaSessionModel`.
    func loadThreads() async {
        let client = self.client
        guard client.hasAccount else {
            threads = .loaded(ChatThreadList(threads: []))
            return
        }
        threads = await almaLoad { try await client.threads() }.value

        // Resume the most recent conversation rather than opening an empty one.
        // A chat that forgets every launch is a chat nobody builds anything in,
        // and the backend keeps the thread precisely so it does not have to.
        guard messages.isEmpty,
              let latest = threads.value?.threads.first
        else { return }
        if let thread = try? await client.thread(id: latest.id) {
            threadID = thread.id
            messages = thread.messages
        }
    }

    /// The opening questions, made this person's own.
    ///
    /// **Free, and that is the argument for doing it at all.** `/v1/systems/natal`
    /// costs nothing — every calculation in this product is free forever, which
    /// is the whole 4.3(b) position — and the preview it returns for a locked
    /// chart still names the three signs, so a reader who has bought nothing
    /// gets the same three questions as a subscriber.
    ///
    /// Skipped entirely when there is no birth data or no account: there is no
    /// chart to read, the empty state is showing `chatNoChart` and a button into
    /// the journey instead, and the request would mint an account for somebody
    /// who has given us nothing. Failure is silent by design — the written three
    /// are already on screen and an error banner over a set of example questions
    /// would be noise about something nobody asked for.
    func loadOpeners(profileID: String?, locale: AppLocale) async {
        guard client.hasAccount, profileID != nil, messages.isEmpty else { return }
        guard let natal = try? await client.compute(.natal, profileId: profileID, locale: locale)
        else { return }
        openers = ChatOpeners.fromChart(natal.data)
    }

    func send(profileID: String?, locale: AppLocale) async {
        let question = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !question.isEmpty, !sending else { return }

        draft = ""
        refusal = nil
        sending = true
        defer { sending = false }

        // Shown immediately, before the round trip. It is the person's own
        // words — nothing is invented by echoing them — and a question that
        // vanishes for eight seconds reads as a send that failed.
        let pending = ChatMessage(
            id: "local-\(UUID().uuidString)",
            role: "user",
            body: question,
            citedFactors: [],
            answeredFromChart: nil,
            turnKind: nil,
            createdAt: ISO8601DateFormatter().string(from: Date())
        )
        messages.append(pending)

        do {
            let reply = try await client.ask(
                question, threadId: threadID, profileId: profileID, locale: locale
            )
            threadID = reply.threadId
            questionsLeft = reply.questionsLeft
            messages.append(reply.message)
        } catch {
            // The question comes back into the field rather than being lost.
            // Somebody who has just been told they are out of questions should
            // not also have to retype the one they asked.
            messages.removeAll { $0.id == pending.id }
            draft = question
            refusal = error
        }
    }
}

#Preview {
    AlmaScreen()
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}
