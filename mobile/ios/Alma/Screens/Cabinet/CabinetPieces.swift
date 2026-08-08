import SwiftUI

/// The pieces four cabinet screens are made of.
///
/// They live together because they are the same three or four shapes repeated —
/// a row with a tag on the right, a wrap of gold pills, a prompt with one
/// button — and four screens each inventing their own spacing for those is how
/// a product stops looking like one thing.

// MARK: — layout

/// A wrap. Pills of positions are variable-width and there are between one and
/// nine of them, so they cannot be an `HStack` (which clips) or a `Grid`
/// (which forces a column width on a chart factor).
///
/// Written as a `Layout` rather than assembled from `GeometryReader` and
/// preference keys, because that is the arrangement that measures its children
/// once and does not need a second render pass to settle.
struct FlowLayout: Layout {

    var spacing: CGFloat = 8
    var lineSpacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? .infinity
        let rows = arrange(subviews: subviews, width: width)
        let height = rows.reduce(0) { $0 + $1.height } +
            lineSpacing * CGFloat(max(rows.count - 1, 0))
        let widest = rows.map(\.width).max() ?? 0
        return CGSize(width: min(width, widest), height: height)
    }

    func placeSubviews(
        in bounds: CGRect,
        proposal: ProposedViewSize,
        subviews: Subviews,
        cache: inout ()
    ) {
        var y = bounds.minY
        for row in arrange(subviews: subviews, width: bounds.width) {
            var x = bounds.minX
            for index in row.indices {
                let size = subviews[index].sizeThatFits(.unspecified)
                subviews[index].place(
                    at: CGPoint(x: x, y: y),
                    anchor: .topLeading,
                    proposal: ProposedViewSize(size)
                )
                x += size.width + spacing
            }
            y += row.height + lineSpacing
        }
    }

    private struct Row {
        var indices: [Int] = []
        var width: CGFloat = 0
        var height: CGFloat = 0
    }

    private func arrange(subviews: Subviews, width: CGFloat) -> [Row] {
        var rows: [Row] = []
        var row = Row()
        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            let needed = row.indices.isEmpty ? size.width : row.width + spacing + size.width
            if needed > width, !row.indices.isEmpty {
                rows.append(row)
                row = Row()
            }
            row.width = row.indices.isEmpty ? size.width : row.width + spacing + size.width
            row.height = max(row.height, size.height)
            row.indices.append(index)
        }
        if !row.indices.isEmpty { rows.append(row) }
        return rows
    }
}

/// A wrap of gold pills — chart positions, cited factors, a card's numbers.
struct PillWrap: View {

    let items: [String]
    var tone: AlmaPill.Tone = .gold

    var body: some View {
        FlowLayout(spacing: 8, lineSpacing: 8) {
            ForEach(items, id: \.self) { item in
                // Spoken in the reader's language at display time; the data
                // underneath stays the engine's identifiers — see
                // `localizedFactor`.
                AlmaPill(text: L10nCabinet.localizedFactor(item), tone: tone)
            }
        }
    }
}

// MARK: — rows

/// The status of a system, in the hub's own vocabulary.
///
/// Gold when the system is ready and muted when it names something missing —
/// never red. "needs birth time" is not an error, it is an instruction, and
/// colouring it as a failure would make a person think they had broken
/// something.
struct StatusTag: View {

    let status: String

    var body: some View {
        Group {
            if let label = HubStatus.label(status) {
                Text(label)
            } else {
                // A state this build has never seen prints the backend's own
                // token rather than blanking the row. The hub is deliberately
                // allowed to add one.
                Text(verbatim: status)
            }
        }
        .almaTag(HubStatus.isReady(status) ? .gold : .muted)
    }
}

/// One of the eight, as a row in the hub.
struct SystemRow: View {

    let system: SystemSlug
    let status: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            AlmaRow {
                Text(system.displayName)
                    .almaHeadingM()
                    .opacity(HubStatus.isReady(status) ? 1 : 0.8)
            } trailing: {
                HStack(spacing: 10) {
                    StatusTag(status: status)
                    Text(verbatim: "→")
                        .font(AlmaFonts.display(15, relativeTo: .footnote))
                        .foregroundStyle(Color.almaGold.opacity(0.55))
                }
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
    }
}

/// One chapter in a table of contents.
///
/// A locked row shows its title and the question it answers, and says it is
/// locked. **It shows no blurred body**, and that is the honest choice rather
/// than a missing feature: live, we hold no copy of an unwritten chapter —
/// nothing exists until it is opened — so a blurred paragraph here would be
/// prose nobody wrote about this person, under a price. `LockedText` is for the
/// places where the real sentences exist.
struct ChapterRow: View {

    let entry: ChapterEntry
    /// Whether to warn that this one needs the minute of birth.
    ///
    /// **Not `entry.needsBirthTime` on its own.** That flag says the chapter is
    /// time-dependent, which sixteen of the natal chapters are — it is a
    /// property of the chapter, not of this person. Rendering it unconditionally
    /// put "this one needs your birth time" under every row of somebody who had
    /// given us their birth time, which reads as the app having lost it.
    var needsBirthTime: Bool = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 7) {
                HStack(alignment: .firstTextBaseline, spacing: 12) {
                    Text(verbatim: entry.numeral)
                        .font(.almaNumeral)
                        .foregroundStyle(Color.almaGold.opacity(0.7))
                        .frame(minWidth: 26, alignment: .leading)

                    Text(verbatim: entry.title)
                        .almaHeadingM()
                        .opacity(entry.open ? 1 : 0.82)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    if entry.free {
                        // Gold, not `.agree`. Green and red are the only
                        // non-gold accents in the product and `AgreementChip`'s
                        // own comment reserves them for one meaning: whether the
                        // systems agree. "Free" is not an agreement, it is the
                        // one row on this list worth reaching for — which is
                        // what gold means everywhere else.
                        Text(L10nCabinet.freeTag).almaTag(.gold)
                    } else if entry.open {
                        Text(L10nCabinet.openTag).almaTag(.gold)
                    } else {
                        Text(L10nCabinet.locked).almaTag(.muted)
                    }
                }

                // The question is the promise of the chapter and is free
                // whether the chapter is or not.
                Text(verbatim: entry.question)
                    .almaMeta()
                    .multilineTextAlignment(.leading)
                    .padding(.leading, 38)

                if needsBirthTime {
                    Text(L10nCabinet.needsBirthTime)
                        .almaTag(.muted)
                        .padding(.leading, 38)
                }
            }
            .padding(.vertical, 14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .contentShape(Rectangle())
            .overlay(alignment: .bottom) { Hairline() }
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
    }
}

/// A label and a value on one line — the shape most of settings and all of the
/// smaller systems' free data is made of.
struct FactRow: View {

    let label: String
    let value: String
    /// Positions are set in the serif and in gold; a plain value is not.
    var isPosition: Bool = false

    var body: some View {
        AlmaRow {
            Text(verbatim: label)
                .font(.almaBodyFont)
                .foregroundStyle(Color.almaMuted)
        } trailing: {
            Group {
                if isPosition {
                    Text(verbatim: value).almaPositions()
                } else {
                    Text(verbatim: value)
                        .font(.almaBodyFont)
                        .foregroundStyle(Color.almaInkLight)
                }
            }
            .multilineTextAlignment(.trailing)
        }
    }
}

/// The same, with a localised label — used where the label is ours rather than
/// the engine's.
struct SettingRow: View {

    let label: LocalizedStringResource
    let value: String

    var body: some View {
        AlmaRow {
            Text(label)
                .font(.almaBodyFont)
                .foregroundStyle(Color.almaMuted)
        } trailing: {
            // Empty rather than borrowed. An unset field shows nothing, so a
            // person can tell at a glance what Alma actually holds.
            Text(verbatim: value)
                .font(.almaBodyFont)
                .foregroundStyle(Color.almaInkLight)
                .multilineTextAlignment(.trailing)
        }
    }
}

/// A row that does something, with an arrow instead of a value.
struct ActionRow: View {

    let label: LocalizedStringResource
    var danger: Bool = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            AlmaRow {
                Text(label)
                    .font(.almaBodyFont)
                    .foregroundStyle(danger ? Color.almaDisagree : Color.almaBody.opacity(0.85))
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

// MARK: — prompts

/// Something is missing and there is one thing to do about it.
///
/// Not `AlmaFailure`: nothing here has gone wrong. A chart with no birth date
/// is a chart nobody has given us yet, and the answer is a form rather than an
/// apology with a retry button on it.
struct NeedMore: View {

    let message: LocalizedStringResource
    let actionTitle: LocalizedStringResource
    let action: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(message)
                .almaVoice()
                .almaReadingWidth()

            Button(action: action) {
                Text(actionTitle)
            }
            .buttonStyle(.alma(.outline, fills: false))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 12)
    }
}

/// One block of a screen failed while the rest of it worked.
///
/// `AlmaFailure` owns the whole screen — a star, a sentence, a button, 200
/// points of it — and is right when there is nothing else to show. Today has
/// four requests and any one of them can fail on its own, and the first version
/// of this screen simply drew nothing where a failed one would have gone. That
/// is the same untruth as inventing the data: a section that vanishes reads as
/// a section with nothing in it, and nobody knows there is anything to retry.
struct SectionFailure: View {

    let error: AlmaError
    let retry: () async -> Void

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(error.displayText)
                .almaMeta()
                .frame(maxWidth: .infinity, alignment: .leading)

            if error.isRetryable {
                Button {
                    Task { await retry() }
                } label: {
                    Text(L10n.stateRetry)
                        .font(AlmaFonts.ui(13.5, weight: .medium))
                        .foregroundStyle(Color.almaGoldBright)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.vertical, 12)
    }
}

/// The door, at the foot of a system or a locked chapter.
///
/// **There is no price on it.** Apple is the merchant of record; the only price
/// that may appear in this app is StoreKit's own localised string for the
/// storefront the buyer is actually in, and that lives on the offer screen. A
/// number from `/v1/billing/catalogue` rendered here would be the wrong number
/// in most countries and a rejection in review.
struct DoorButton: View {

    let title: LocalizedStringResource
    /// **No note by default, and the default used to be a claim.**
    ///
    /// It was "One payment. Yours permanently." under every door — true of a
    /// door and false of everything else on the same screen, and the owner
    /// caught it sitting under a button that leads to a ladder with two
    /// subscriptions on it. A line that is true of one rung and printed under
    /// all of them is worse than no line: it is the kind of sentence somebody
    /// quotes back after their card is charged again.
    ///
    /// The offer screen states the terms per rung, from StoreKit, which is the
    /// only place they can be stated correctly.
    var note: LocalizedStringResource? = nil
    let action: () -> Void

    var body: some View {
        VStack(spacing: 10) {
            Button(action: action) {
                Text(title)
            }
            .buttonStyle(.almaGold)

            if let note {
                Text(note)
                    .almaMeta()
                    .multilineTextAlignment(.center)
            }
        }
        .padding(.top, 8)
    }
}

/// A titled block with a gold rule, and the standard gap under it.
struct CabinetSection<Content: View>: View {

    let label: LocalizedStringResource
    /// The number or word that rides at the right-hand end of the rule.
    var trailing: String?
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 12) {
                SectionLabel(text: label)
                if let trailing {
                    Text(verbatim: trailing)
                        .font(.almaNumeral)
                        .foregroundStyle(Color.almaGoldBright)
                }
            }
            content
        }
        .padding(.top, AlmaMetrics.gapLarge)
    }
}

// MARK: — cross-synthesis

/// One axis: what the systems were asked, what each answered, and whether they
/// agreed.
///
/// This view is the 4.3(b) argument in one screen's worth of code. A reviewer
/// who opens the app and finds a daily horoscope applies the spam guideline; one
/// who finds three named systems disagreeing about a stated question, each
/// citing the factor it read, does not. So the disagreement is shown at least as
/// prominently as the agreement, and never smoothed over.
struct AxisView: View {

    let axis: ChartFacts.Axis

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(name)
                    .font(.almaHeadingM)
                    .foregroundStyle(Color.almaInkLight)
                    .frame(maxWidth: .infinity, alignment: .leading)
                AgreementChip(text: chipText, tone: axis.verdict.tone)
            }

            // The two ends of the axis, so that "2 disagree" has a subject.
            // The engine writes these in English, like every other factor.
            if let positive = axis.positivePole, let negative = axis.negativePole {
                Text(verbatim: "\(negative)  ↔  \(positive)")
                    .almaMeta()
            }

            ForEach(axis.signals) { signal in
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Group {
                        if let system = signal.system {
                            Text(system.displayName)
                        } else {
                            Text(verbatim: signal.systemRaw)
                        }
                    }
                    .font(.almaMetaFont)
                    .foregroundStyle(Color.almaMuted3)

                    Text(verbatim: signal.factor)
                        .almaPositions()
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        .padding(.vertical, 14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .overlay(alignment: .bottom) { Hairline() }
    }

    private var name: LocalizedStringResource {
        // An axis the app has no name for keeps the engine's own: readable and
        // in the wrong language beats blank.
        L10nCabinet.axis(axis.name) ?? LocalizedStringResource(stringLiteral: axis.name)
    }

    private var chipText: String {
        switch axis.verdict {
        case .agree: String(localized: L10nCabinet.synthAgree(axis.count))
        case .disagree: String(localized: L10nCabinet.synthDisagree(axis.count))
        case .single: String(localized: L10nCabinet.synthSingle)
        }
    }
}

/// The three counts, as chips. They survive the lock, so this is what somebody
/// who has not paid sees — the shape of the answer, free.
struct SynthesisChips: View {

    let counts: ChartFacts.SynthesisCounts

    var body: some View {
        FlowLayout(spacing: 8, lineSpacing: 8) {
            AgreementChip(text: String(localized: L10nCabinet.synthAgree(counts.agree)), tone: .agree)
            AgreementChip(
                text: String(localized: L10nCabinet.synthDisagree(counts.disagree)),
                tone: .disagree
            )
            AgreementChip(
                text: String(localized: L10nCabinet.synthSingleCount(counts.single)),
                tone: .gold
            )
        }
    }
}

#Preview("Pieces") {
    ScrollView {
        VStack(alignment: .leading, spacing: 0) {
            CabinetSection(label: L10nCabinet.groupWhoAmI) {
                SystemRow(system: .natal, status: "calculated") {}
                SystemRow(system: .compatibility, status: "add-person") {}
            }
            CabinetSection(label: L10nCabinet.acrossSystems) {
                SynthesisChips(counts: .init(agree: 4, disagree: 4, single: 1))
                AxisView(axis: .init(
                    name: "Direction",
                    verdict: .disagree,
                    count: 2,
                    positivePole: "works in public, in front of people",
                    negativePole: "works alone, out of sight",
                    signals: [
                        .init(system: .natal, factor: "midheaven in Pisces", systemRaw: "natal"),
                        .init(system: .numerology, factor: "life path 8", systemRaw: "numerology"),
                    ]
                ))
            }
            PillWrap(items: ["☉ 23°38′ ♓︎ · H10", "☽ 7°05′ ♎︎ · H4", "ASC 11°02′ ♋︎"])
                .padding(.top, 20)
        }
        .almaPadding()
    }
    .nightSky()
}
