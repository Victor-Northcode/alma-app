import SwiftUI

/// One chapter. This is the product.
///
/// Three things it has to do, and each of them is why this is not a horoscope
/// feed.
///
/// **Cite.** `Reading.citedFactors` names the exact placements the text was
/// read from, and they sit above the first paragraph rather than in a footer.
/// The label above them is ours and localised; the factors are the engine's own
/// words, as they are everywhere else in the app.
///
/// **Refuse.** When Alma cannot write a chapter from the chart she does not
/// write it, and the screen says so in her words instead of filling the space.
///
/// **Be honest about the lock.** A locked chapter shows its numeral, its title
/// and the question it answers, and then says plainly that the text does not
/// exist yet — it is written from these positions the first time it is opened.
/// There is no blurred paragraph here, because live we hold no copy of an
/// unwritten chapter: blurring something would mean inventing it first, under a
/// price. `LockedText` is for the screens where the real sentences exist.
///
/// **On the parchment.** The web app sets the whole reader on parchment. Here
/// only the advice is, and that is a decision rather than an omission: the
/// shell owns the back control, it is a gold arrow with no capsule behind it,
/// and a full-bleed light sheet scrolling under it fails contrast the moment
/// the page moves. The `.reading` mood exists for exactly this screen — the sky
/// dims to 0.45 and the motes and the comet go, because the product here is the
/// words.
struct ChapterScreen: View {

    let system: SystemSlug
    /// The chapter this screen was opened on. After that the screen owns which
    /// one is showing — see `current`.
    let chapter: String

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router

    /// Which chapter is on screen.
    ///
    /// **Reading on is a change of state here, not a change of route, and that
    /// is what makes the page turn visible.** It used to be
    /// `router.replaceTop(with: .chapter(…))`, which swaps the element under a
    /// `NavigationStack` — and a stack owns how its destinations appear, so the
    /// `.transition` declared on this view was never consulted. The new chapter
    /// simply took the old one's place between two frames. The owner said it
    /// twice: still not smooth, and then that the animation went away
    /// altogether after a few turns, which is the same thing seen from further
    /// along.
    ///
    /// With the switch inside one screen, the transition is an ordinary
    /// SwiftUI one and behaves like every other animation in the app. Back
    /// still leaves for the system, because there is still exactly one chapter
    /// screen on the stack however many were read.
    @State private var current: String?

    @State private var model: ChapterModel?

    /// How far past the last line the reader has pulled, in points.
    @State private var pull: CGFloat = 0
    /// Set the moment a pull is honoured and cleared only when the next chapter
    /// has actually arrived, so one flick cannot walk through a system.
    @State private var advancing = false
    /// Whether the pull has crossed the line and is being held there.
    @State private var armed = false

    /// How far past the end counts as "take me on".
    ///
    /// **Fifty-six, and the number was measured rather than chosen.** It was 90
    /// first, on the reasoning that pull-to-refresh is about that — and the
    /// owner reported the gesture simply not working. It was working: a firm
    /// swipe from the bottom of the screen to the top produced a maximum of
    /// **86 points**, four short of the line, every time.
    ///
    /// The mistake was reading 90 points of *rubber band* as 90 points of
    /// finger. iOS damps overscroll hard — the last third of a long drag buys
    /// almost no distance — so a threshold that sounds gentle in finger terms
    /// is one an ordinary reader can never reach. 56 fires on a comfortable
    /// pull and still needs a deliberate one: letting go at the end of a
    /// chapter does not cross it.
    private static let pullThreshold: CGFloat = 56

    /// How far the pull has to go before the page actually turns.
    ///
    /// **This is the confirmation the owner asked for, and it is distance
    /// rather than time.** Crossing 56 used to turn the page immediately: one
    /// hard swipe carried enough momentum to cross, turn, land on the next
    /// chapter and cross again, so a single flick walked through a whole
    /// system — "просто смахнёшь, и пролистнёт всё сразу".
    ///
    /// A timed hold was tried first and is the obvious answer: cross the line,
    /// keep the finger there for a third of a second, and the page turns.
    /// Measured on the simulator it sat right on the edge — one held pull
    /// committed, the next one, a hundred milliseconds shorter, did not — and a
    /// gesture that works four times in five is worse than one that never
    /// works, because the reader stops trusting their own hand.
    ///
    /// Distance has no race in it. A firm flick reaches **86 points** of rubber
    /// band, measured repeatedly; a deliberate pull that keeps going reaches
    /// well past 150. 130 sits in the gap: it cannot be reached by accident and
    /// it does not have to be held, only meant. The bar under the next
    /// chapter's name fills across exactly this range, so the reader can see
    /// how much further there is to go.
    private static let commitThreshold: CGFloat = 130

    /// Whichever chapter is showing: the one the screen was opened on until a
    /// pull moves it on.
    private var showing: String { current ?? chapter }

    var body: some View {
        // A container the transition can happen *inside*. `.id` on the page
        // makes each chapter a different view to SwiftUI, and the `ZStack` is
        // what gives the outgoing and incoming pages somewhere to overlap while
        // one leaves and the other arrives.
        ZStack {
            page
                .id(showing)
                // Up and out, down and in — the direction the pull was going,
                // so the motion continues the gesture instead of answering it.
                .transition(
                    .asymmetric(
                        insertion: .move(edge: .bottom).combined(with: .opacity),
                        removal: .move(edge: .top).combined(with: .opacity)
                    )
                )
        }
        // **Keyed on the chapter, not bare.** The screen stays in the same
        // place in the stack while the chapter under it changes, so a bare
        // `.task` would run once and leave the previous chapter's text under
        // the new chapter's title.
        .task(id: "\(system.rawValue)/\(showing)") {
            let model = ChapterModel(client: session.client, system: system, chapter: showing)
            self.model = model
            pull = 0
            armed = false
            await model.load(locale: session.locale)
            // **The guard lifts here — after the chapter has arrived, not when
            // it was asked for.** It used to lift on the next runloop tick,
            // which is instantly, so the momentum left over from a hard swipe
            // went straight into the next page and turned it too. Waiting for
            // the load means each turn costs a fresh, deliberate pull.
            advancing = false
        }
    }

    private var page: some View {
        // Which chapter this particular page is, fixed when it is built.
        //
        // **A page that is leaving must stop being listened to.** Both pages
        // exist for the length of the transition, and the finger that started
        // the turn is usually still down: the outgoing scroll view goes on
        // reporting its own overscroll, still past the mark, and turned a
        // second page. Measured — one deliberate pull jumped from chapter one
        // to chapter three, skipping the one in between. Comparing against
        // `showing` at report time is what makes the old page's voice stop
        // counting the moment it is the old page.
        let mine = showing
        return ScreenScaffold(
            mood: .reading,
            seed: 0x4348_4150,
            onOverscroll: { distance in
                guard mine == showing else { return }
                // Nothing at all while a turn is in flight: the guard lifts
                // when the next chapter has loaded, not when it was asked for.
                guard canAdvance, !advancing else { return }
                pull = distance

                // **Two beats, and they say different things.** The first is
                // the moment the pull becomes enough — a soft tick under the
                // finger, the same one the ceremony uses when a system lights
                // up. The second, in `advance`, is the page actually turning.
                // One buzz for both would make the threshold invisible, which
                // is the thing a pull gesture most needs to communicate.
                if distance >= Self.pullThreshold, !armed {
                    armed = true
                    AlmaHaptics.tick()
                } else if distance < Self.pullThreshold * 0.7, armed {
                    // Eased off: nothing happened, and pulling again gets the
                    // same tick and the same bar.
                    armed = false
                }
                // The turn itself, at the far mark. See `commitThreshold`.
                if distance >= Self.commitThreshold {
                    advance()
                }
            }
        ) {
            if let model {
                heading(model)
                content(model)
            }
        }
        // **What rises as you pull is the next chapter's name**, so the gesture
        // shows where it goes before it goes there — the owner's "see part of
        // it before you get there".
        //
        // **The page itself does not move, and that was tried.** Offsetting the
        // whole scaffold by a fraction of the pull looked right on paper and
        // broke the gesture outright: moving the view re-lays the scroll view
        // inside it, the reported overscroll resets to zero, the offset goes
        // with it, and the two chase each other without the pull ever reaching
        // its threshold. Measured on the simulator — the swipe that had just
        // been working stopped. The overlay moves; the page stays still.
        .overlay(alignment: .bottom) { peek }
    }

    // MARK: — the top of the chapter

    @ViewBuilder
    private func heading(_ model: ChapterModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // **The plate is the first thing a chapter shows.**
            //
            // The map of all forty-one chapters existed, the endpoint existed,
            // the disk cache existed — and no chapter on this platform had ever
            // drawn one. In the canvas (`s5`) it stands over the overline,
            // 150×188, centred, and that is where it stands here.
            //
            // Chapters whose art is not drawn yet show their Roman numeral in
            // the same frame rather than a gap: the six holes are known and
            // marked, and filling one with somebody else's painting would be
            // worse than the hole — a picture about the wrong thing, on a
            // chapter that was paid for.
            PlateArch(
                store: session.plates,
                plate: AlmaPlates.name(system, chapter: showing),
                numeral: model.entry?.numeral ?? ""
            )
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.bottom, 14)

            HStack(spacing: 10) {
                if let entry = model.entry {
                    Text(verbatim: entry.numeral).almaOverline()
                }
                Text(system.displayName).almaOverline()
                Spacer(minLength: 8)
                if let entry = model.entry, let total = model.total {
                    Text(L10nCabinet.chapterProgress(entry.index, of: total))
                        .almaTag(.gold)
                }
            }

            Text(verbatim: model.title).almaDisplayL()
        }
    }

    // MARK: — the chapter itself

    @ViewBuilder
    private func content(_ model: ChapterModel) -> some View {
        // The first line is always readable, whether the chapter is open or
        // not: it comes from the reading when there is one and otherwise from
        // the question the chapter answers, which is catalogue metadata rather
        // than anything Alma wrote about this person.
        if let lead = model.lead {
            Text(verbatim: lead)
                .almaVoice()
                .almaReadingWidth()
                .padding(.top, 4)
        }

        switch model.reading {
        case .loading:
            // The system's own drawing, alive, for as long as the model
            // writes. A chapter being written from a real chart is an event,
            // and the old breathing dot did not look like one.
            VStack(spacing: 18) {
                Spacer(minLength: 0)
                WritingArt(system: system)
                Text(L10n.stateWriting).almaMeta()
                // «Пишется один раз — и завтра скажет то же самое» stood here
                // and the owner cut it from every page.
                Spacer(minLength: 0)
            }
            // Centred in what is left of the screen under the title — the
            // drawing is the event, and an event does not hug the header.
            .frame(maxWidth: .infinity, minHeight: 480)

        case .loaded(let answer):
            if answer.preview == true {
                previewed(answer.reading)
            } else {
                written(answer.reading)
                next(model)
                chapterEndOffer
            }

        case .failed(let error):
            failure(error, model: model)
        }
    }

    /// The blurred preview: the real first paragraph in the clear, the real
    /// rest under blur, the unlock button on top of it. Nothing here is a
    /// placeholder — the prose exists and says what it says; the blur is the
    /// only thing the purchase removes.
    @ViewBuilder
    private func previewed(_ reading: Reading) -> some View {
        if let first = reading.body.first {
            FadedRule().padding(.vertical, 14)
            Text(verbatim: first).almaBody().almaReadingWidth()
        }

        VStack(alignment: .leading, spacing: 18) {
            ForEach(Array(reading.body.dropFirst().enumerated()), id: \.offset) { _, paragraph in
                Text(verbatim: paragraph).almaBody().almaReadingWidth()
            }
            if let advice = reading.advice, !advice.isEmpty {
                AdviceBlock(text: advice)
            }
        }
        .blur(radius: 7)
        .accessibilityHidden(true)
        .allowsHitTesting(false)
        .overlay(alignment: .center) {
            VStack(spacing: 14) {
                Text(L10nCabinet.previewNote)
                    .almaMeta()
                    .multilineTextAlignment(.center)
                Button {
                    router.push(.offer(system: system))
                } label: {
                    Text(L10nCabinet.unlock)
                }
                .buttonStyle(AlmaButtonStyle(kind: .gold, fills: false))
            }
            .padding(20)
        }
    }

    @ViewBuilder
    private func written(_ reading: Reading) -> some View {
        if !reading.citedFactors.isEmpty {
            CabinetSection(label: L10nCabinet.readFrom) {
                PillWrap(items: reading.citedFactors)
            }
            .padding(.bottom, 4)
        }

        FadedRule().padding(.vertical, 14)

        VStack(alignment: .leading, spacing: 18) {
            ForEach(Array(reading.body.enumerated()), id: \.offset) { _, paragraph in
                Text(verbatim: paragraph).almaBody().almaReadingWidth()
            }
        }

        if let advice = reading.advice, !advice.isEmpty {
            AdviceBlock(text: advice)
        }
    }

    /// The end of a chapter, and the way through it.
    ///
    /// **There is no button here any more.** There was one — a row saying "next
    /// chapter" with the next chapter's title in grey underneath — and the
    /// owner cut both. A person who has just finished reading is already
    /// scrolling, and the thing under their thumb should answer the scroll
    /// rather than ask for a tap. The model is Telegram's, and it was his
    /// comparison: you reach the bottom of a channel, keep pulling, the next
    /// one opens.
    ///
    /// So this draws what the pull is doing. An arrow that fills and turns as
    /// the distance closes, the next chapter's name under it, and at the end of
    /// a system a tick instead — nothing left to pull towards, said once and
    /// quietly.
    ///
    /// Never towards a locked chapter: pulling somebody into a system they have
    /// not bought is a worse invitation than the door above, which at least
    /// names the price.
    @ViewBuilder
    private func next(_ model: ChapterModel) -> some View {
        let progress = min(1, pull / Self.pullThreshold)
        VStack(spacing: 10) {
            if let next = model.next, canAdvance {
                Image(systemName: "arrow.down")
                    .font(.system(size: 15, weight: .light))
                    .foregroundStyle(Color.almaGold.opacity(0.35 + 0.65 * progress))
                    .rotationEffect(.degrees(180 * progress))
                    .scaleEffect(1 + 0.25 * progress)
                Text(verbatim: next.title)
                    .almaMeta()
                    .opacity(0.5 + 0.5 * progress)
            } else if model.next == nil, model.chapters.value != nil {
                Image(systemName: "checkmark")
                    .font(.system(size: 15, weight: .light))
                    .foregroundStyle(Color.almaGold.opacity(0.7))
                Text(L10nCabinet.systemFinished).almaMeta()
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.top, AlmaMetrics.gapLarge)
        .animation(AlmaMotion.ui, value: progress)
    }

    /// The next chapter, showing itself from under the page being lifted.
    ///
    /// **This is the part that makes the gesture readable.** Before it, pulling
    /// moved nothing and then the screen changed: the owner's word was that it
    /// felt thrown rather than turned. Now the page rises, and this comes up
    /// behind it with the numeral and the title — you can see what you are
    /// about to open while you decide whether to open it, and letting go early
    /// puts everything back.
    ///
    /// It only exists while a pull is happening, so it costs nothing at rest.
    @ViewBuilder
    private var peek: some View {
        if pull > 4, canAdvance, let next = model?.next {
            let progress = min(1, pull / Self.pullThreshold)
            // How much of the way to the turn the pull has come. The bar is
            // this, so "how much further" is a thing the reader can see rather
            // than guess.
            let commitProgress = min(1, pull / Self.commitThreshold)
            VStack(spacing: 8) {
                // **The bar is how far there is left to pull.** Without it the
                // gesture is a guess: the reader crossed a line they felt as a
                // tick, and nothing on screen says whether one more centimetre
                // or five will do it. Full means the next page is already on
                // its way.
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color.almaGold.opacity(0.18))
                        .frame(width: 64, height: 2.5)
                    Capsule()
                        .fill(Color.almaGoldBright)
                        .frame(width: 64 * commitProgress, height: 2.5)
                }
                Text(verbatim: next.numeral)
                    .almaOverline()
                    .opacity(0.4 + 0.6 * progress)
                Text(verbatim: next.title)
                    .font(AlmaFonts.display(20 + 4 * progress, relativeTo: .title3))
                    .foregroundStyle(Color.almaInkLight.opacity(0.35 + 0.65 * progress))
                    .multilineTextAlignment(.center)
                    .almaReadingWidth()
                Text(L10nCabinet.pullToTurn)
                    .almaMeta()
                    .opacity(0.5 + 0.5 * progress)
            }
            .padding(.bottom, 26)
            // Rises from below the fold and settles as the pull completes, so
            // the two movements — the page leaving and this arriving — are one.
            .offset(y: 54 - 54 * progress)
            .opacity(progress)
            .allowsHitTesting(false)
            .transition(.opacity)
        }
    }

    /// Whether pulling should carry the reader on at all.
    ///
    /// A chapter with nothing after it, or one whose next is locked, leaves the
    /// gesture inert rather than bouncing somebody off an invitation they
    /// cannot take.
    private var canAdvance: Bool {
        guard let model, let next = model.next else { return false }
        return next.open || next.free || session.unlocked(system)
    }

    /// Hand the reader to the next chapter.
    ///
    /// `replaceTop`, so back from the fifth chapter in a row is still the
    /// system rather than the fourth. The pull is reset first: the next screen
    /// arrives at the top of its own text, and a stale `pull` would leave its
    /// arrow half-drawn before a finger has touched it.
    private func advance() {
        guard let next = model?.next else { return }
        advancing = true
        AlmaHaptics.arrival()
        // **A change of state, animated here.** The route does not move — see
        // `current` for why that was the whole problem — so this is an ordinary
        // SwiftUI transition and behaves like one every time rather than once.
        //
        // `pull` is deliberately *not* cleared before the animation: clearing
        // it retracts the peek in the same frame the page starts leaving, and
        // the two movements read as one interruption. The new page's `.task`
        // resets it once there is something to reset it for.
        withAnimation(AlmaMotion.turn) {
            current = next.slug
        }
    }

    /// One quiet row at the end of a finished chapter — the moment the writing
    /// has just proven itself, which is the definition of the right moment.
    ///
    /// Static content below the reading, never a modal, never mid-scroll. The
    /// door variant for a system this account has not bought; the plan variant
    /// for one it has — a bought chapter is written once, and the living layer
    /// is the thing that moves. A subscriber sees neither.
    @ViewBuilder
    private var chapterEndOffer: some View {
        if !session.entitlements.isSubscriber {
            if !session.unlocked(system) {
                VStack(alignment: .leading, spacing: 10) {
                    Text(L10nCabinet.chapterEndDoor).almaMeta().almaReadingWidth()
                    DoorButton(
                        title: L10nCabinet.openSystemNamed(String(localized: system.displayName))
                    ) {
                        router.push(.offer(system: system))
                    }
                }
                .padding(.top, AlmaMetrics.gapLarge)
            } else {
                VStack(alignment: .leading, spacing: 10) {
                    Text(L10nCabinet.chapterEndPlan).almaMeta().almaReadingWidth()
                    Button {
                        router.push(.offer(system: nil))
                    } label: {
                        Text(L10nCabinet.plansCta)
                    }
                    .buttonStyle(.alma(.outline, fills: false))
                }
                .padding(.top, AlmaMetrics.gapLarge)
            }
        }
    }

    @ViewBuilder
    private func failure(_ error: AlmaError, model: ChapterModel) -> some View {
        switch error {
        case .locked:
            LockedChapter(system: system) {
                router.push(.offer(system: system))
            }

        case .needsBirthTime:
            NeedMore(
                message: L10nCabinet.needsBirthTime,
                actionTitle: L10nCabinet.addBirthTime
            ) {
                router.openJourney()
            }

        // **Compatibility needs a second person — and a door to one, not a
        // sentence.**
        //
        // The server's 422 landed on `.invalid` below and printed as flat text
        // in the middle of the page: the one action that resolves it was named
        // by the sentence and offered nowhere. `SystemScreen` has drawn this
        // case as a line and a button since it was built, and a chapter of the
        // same system has no business behaving differently.
        //
        // The message is the server's own and already in the reader's language
        // — `readings.py` translates it through `i18n_replies` precisely so a
        // client does not have to invent a sentence here.
        case .partnerRequired(let message):
            NeedMore(
                verbatim: message.isEmpty
                    ? String(localized: L10nCabinet.compatNeedsPerson)
                    : message,
                actionTitle: L10nCabinet.addAPerson
            ) {
                router.push(.people)
            }

        case .invalid(let message):
            // Alma read the chart and declined to write from it. That is a
            // deliberate outcome of the writer, not a fault, and it is said in
            // her words with the server's own explanation underneath.
            VStack(alignment: .leading, spacing: 10) {
                Text(L10nCabinet.refused).almaVoice().almaReadingWidth()
                Text(verbatim: message).almaMeta().almaReadingWidth()
            }
            .padding(.vertical, 16)

        default:
            AlmaFailure(error: error) { await model.reload() }
                .frame(minHeight: 200)
        }
    }
}

/// The one light surface in the app, used where a document is earned: the line
/// of advice a chapter ends with.
private struct AdviceBlock: View {

    let text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(L10nCabinet.advice)
                .font(.almaOverline)
                .textCase(.uppercase)
                .tracking(2.5)
                .foregroundStyle(Color.almaInkMuted2)

            Text(verbatim: text)
                .font(.almaVoiceFont.italic())
                .lineSpacing(6)
                .foregroundStyle(Color.almaInk)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 22)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AlmaGradient.parchment)
        .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
        .padding(.top, AlmaMetrics.gapLarge)
    }
}

/// What a locked chapter is, said without pretending the text already exists.
private struct LockedChapter: View {

    let system: SystemSlug
    let open: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            FadedRule().padding(.vertical, 10)

            Text(L10nCabinet.lockedNote)
                .almaBody()
                .almaReadingWidth()

            // The door is the system, not the chapter: single chapters are not
            // sold, so a price beside this title would be the price of the
            // whole system printed next to one sixteenth of it.
            DoorButton(title: L10nCabinet.openSystemNamed(String(localized: system.displayName)), action: open)

            Text(L10nCabinet.archiveNote)
                .almaMeta()
                .frame(maxWidth: .infinity, alignment: .center)
        }
        .padding(.top, 8)
    }
}

// MARK: — the state behind it

@MainActor
@Observable
final class ChapterModel {

    private(set) var reading: ScreenState<ReadingResponse> = .loading
    private(set) var chapters: ScreenState<ChapterList> = .loading

    private let client: AlmaClient
    private let system: SystemSlug
    private let chapter: String
    private var locale: AppLocale = .current

    init(client: AlmaClient, system: SystemSlug, chapter: String) {
        self.client = client
        self.system = system
        self.chapter = chapter
    }

    func load(locale: AppLocale) async {
        self.locale = locale
        await reload()
    }

    func reload() async {
        let client = self.client
        let system = self.system
        let chapter = self.chapter
        let locale = self.locale

        // The two are independent and the reading is the slow one — a model
        // writing three hundred words. Asking for the table of contents first
        // and the chapter afterwards would put that wait behind a request that
        // returns in milliseconds.
        let reading = almaLoad {
            try await client.reading(system: system, chapter: chapter, locale: locale)
        }
        let chapters = almaLoad { try await client.chapters(of: system, locale: locale) }

        self.reading = await reading.value
        self.chapters = await chapters.value

        // One automatic second try, and only for the faults a retry can change.
        //
        // The same guard `TodayModel` already carries, for the same reason and
        // now for a second one: when a generation *does* fall over transport,
        // the server has usually finished writing anyway and stored the chapter
        // — so the retry returns instantly from the database rather than paying
        // for a second write. The owner watched exactly that happen by hand,
        // twice, and the button he had to press for it is the thing being
        // removed here. A refusal or a lock is an answer, and is left alone.
        if case .failed(let error) = self.reading, error.isTransient {
            try? await Task.sleep(for: .seconds(2))
            self.reading = await almaLoad {
                try await client.reading(system: system, chapter: chapter, locale: locale)
            }.value
        }
    }

    var entry: ChapterEntry? {
        chapters.value?.chapters.first { $0.slug == chapter }
    }

    var total: Int? { chapters.value?.total }

    /// The chapter after this one, by the engine's own index rather than by
    /// position in the array — the list is ordered, but an ordering assumed is
    /// an ordering that breaks silently the day a chapter is inserted.
    var next: ChapterEntry? {
        guard let index = entry?.index else { return nil }
        return chapters.value?.chapters.first { $0.index == index + 1 }
    }

    var title: String {
        reading.value?.reading.title ?? entry?.title ?? ""
    }

    /// The first line a chapter is allowed to show before it is paid for.
    ///
    /// From the reading when there is one; otherwise the one standing line —
    /// "written from your own positions". The question subtitles that stood
    /// here were cut with the rest of them: half read as broken grammar and
    /// none of them explained anything.
    var lead: String? {
        if let teaser = reading.value?.reading.teaser, !teaser.isEmpty { return teaser }
        return String(localized: L10nCabinet.fromYourPositions)
    }
}

#Preview {
    NavigationStack { ChapterScreen(system: .natal, chapter: "core") }
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}
