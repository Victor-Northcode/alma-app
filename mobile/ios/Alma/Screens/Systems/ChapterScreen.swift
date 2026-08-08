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
    let chapter: String

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router

    @State private var model: ChapterModel?

    var body: some View {
        ScreenScaffold(mood: .reading, seed: 0x4348_4150) {
            if let model {
                heading(model)
                content(model)
            }
        }
        // **Keyed on the chapter, not bare.** Reading on now *replaces* this
        // screen rather than stacking a new one (`AppRouter.replaceTop`), so the
        // view stays in the same place in the stack and SwiftUI keeps its
        // `@State` — a bare `.task` would run once and leave the previous
        // chapter's text under the new chapter's title. The id is what makes
        // the swap reload.
        .task(id: "\(system.rawValue)/\(chapter)") {
            let model = ChapterModel(client: session.client, system: system, chapter: chapter)
            self.model = model
            await model.load(locale: session.locale)
        }
    }

    // MARK: — the top of the chapter

    @ViewBuilder
    private func heading(_ model: ChapterModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
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

    /// Where to go after the last paragraph.
    ///
    /// Only after a chapter that was actually written: offering "next" under a
    /// paywall would be inviting somebody deeper into a system they have not
    /// bought, and the door above is the honest next step there.
    @ViewBuilder
    private func next(_ model: ChapterModel) -> some View {
        if let next = model.next {
            // `replaceTop`, not `push`: see the comment there. Back from any
            // chapter is back to the system, however many were read in a row.
            ActionRow(label: L10nCabinet.nextChapter) {
                router.replaceTop(with: .chapter(system: system, chapter: next.slug))
            }
            .padding(.top, AlmaMetrics.gapLarge)

            Text(verbatim: next.title).almaMeta()
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
