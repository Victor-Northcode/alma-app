import SwiftUI

/// VII · the portrait. The moment the product first says "here is you".
///
/// **Every line on this screen was fetched.** In the web app this screen once
/// said it about somebody else: the pills were literal constants — `☽ 8° ♏︎`,
/// `ASC 11° ♌︎` — shown to every visitor whatever their birth, the paragraph
/// under them was one fixed interpretation, and three rows claimed "16 chapters
/// ready · 9 axes ready · 3 active today" without anything having been counted.
/// On the one screen whose entire job is to prove the calculation is real, all
/// of it was decoration. It was found and removed, and this is the port of what
/// replaced it: a row appears when its request answered and is simply absent
/// when it did not. An empty row is honest; a filled one is true.
///
/// **The free things are handed over here, not promised.** Numerology and the
/// Birth Card cost nothing ever — that is `FREE_SYSTEMS` in the backend, not a
/// trial — and showing them in full before the offer is what makes the offer an
/// offer rather than a toll. The one addition to the web app's version is the
/// free chapter: exactly one written chapter per system is free, and this is
/// where it stops being a sentence in the pricing copy and becomes a row you
/// can open.
struct StepPortrait: View {

    let journey: JourneyModel
    let onNext: () -> Void
    /// Opening the free chapter leaves the journey — the chapter reader is a
    /// cabinet screen and the wait for a chapter to be written belongs on the
    /// screen built to explain it.
    let onOpenChapter: (SystemSlug, String) -> Void

    @Environment(AlmaSessionModel.self) private var session

    var body: some View {
        ScreenStateView(journey.portrait) { portrait in
            if portrait.isEmpty {
                // Saved, but nothing came back. Not a blank screen with a
                // button on it: the chart exists and can be asked for again.
                AlmaFailure(error: .unavailable(message: "")) {
                    journey.retry(with: session)
                }
                .frame(minHeight: 420)
            } else {
                document(portrait)
            }
        } retry: {
            journey.retry(with: session)
        }
        .task {
            AlmaHaptics.arrival()
            await session.client.track(.portraitView)
        }
    }

    private func document(_ portrait: Portrait) -> some View {
        JourneyDocument {
            VStack(alignment: .leading, spacing: 0) {
                head(portrait)
                FadedRule().padding(.vertical, 22)
                freeRows(portrait)
                freeChapter(portrait)
                needsTime
            }
        } controls: {
            Button(action: onNext) {
                Text(JourneyL10n.keepMySky)
            }
            .buttonStyle(.almaGold)

            JourneyFineprint(text: JourneyL10n.staysFree)
        }
    }

    // MARK: — who this is

    private func head(_ portrait: Portrait) -> some View {
        VStack(spacing: 0) {
            Text(JourneyL10n.calculated)
                .almaOverline()

            if let glyph = portrait.sunSign.flatMap(ZodiacGlyph.glyph(for:)) {
                Text(verbatim: glyph)
                    .font(.system(size: 88))
                    .foregroundStyle(Color.almaGoldBright)
                    .shadow(color: Color.almaGold.opacity(0.28), radius: 24)
                    .padding(.top, 10)
                    .accessibilityHidden(true)
            }

            Text(name(portrait))
                .font(AlmaFonts.display(25, relativeTo: .title2))
                .foregroundStyle(Color.almaInkLight)
                .multilineTextAlignment(.center)
                .padding(.top, 4)

            if !pills(portrait).isEmpty {
                // A flow rather than an `HStack`: "Ascendant Sagittarius" in
                // German is wider than a phone, and three of them on one line
                // would each be squeezed to nothing.
                FlowRow(spacing: 7) {
                    ForEach(pills(portrait), id: \.self) { pill in
                        AlmaPill(text: pill)
                    }
                }
                .padding(.top, 16)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 24)
    }

    /// "Sofia · Sun in Pisces", or as much of it as is true.
    private func name(_ portrait: Portrait) -> String {
        let who = journey.name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let sign = portrait.sunSign else { return who }
        let sun = String(localized: JourneyL10n.sun(JourneyL10n.sign(sign)))
        return who.isEmpty ? sun : "\(who) · \(sun)"
    }

    /// The Moon, the Ascendant and the life path — the three things a person
    /// recognises fastest. The Ascendant is present only when the birth time
    /// was given, because the backend refuses to compute a horizon without one,
    /// and this is the screen where that refusal is most worth showing.
    private func pills(_ portrait: Portrait) -> [String] {
        var pills: [String] = []
        if let moon = portrait.moonSign {
            pills.append("☽ \(JourneyL10n.sign(moon))")
        }
        if let rising = portrait.risingSign {
            pills.append("\(String(localized: JourneyL10n.ascendant)) \(JourneyL10n.sign(rising))")
        }
        if let path = portrait.lifePath {
            pills.append(String(localized: JourneyL10n.lifePath(path)))
        }
        return pills
    }

    // MARK: — what is free

    @ViewBuilder
    private func freeRows(_ portrait: Portrait) -> some View {
        let rows = freeValues(portrait)
        if !rows.isEmpty {
            Text(JourneyL10n.freeLabel)
                .almaOverline()
                .padding(.bottom, 12)

            ForEach(rows) { row in
                HStack(spacing: 14) {
                    Text(row.label)
                        .font(AlmaFonts.ui(15.5))
                        .foregroundStyle(Color.almaBody.opacity(0.8))
                        .frame(maxWidth: .infinity, alignment: .leading)
                    Text(row.value)
                        .font(AlmaFonts.ui(15))
                        .foregroundStyle(Color.almaGoldBright)
                        .multilineTextAlignment(.trailing)
                }
                .padding(.vertical, 12)
                .accessibilityElement(children: .combine)
            }

            // Not `JourneyL10n.freeNote`, which is the web's sentence and says
            // "these two systems" above three rows. See `portraitFreeNote`.
            JourneyFineprint(text: ScreenL10n.portraitFreeNote, alignment: .leading)
                .padding(.top, 2)
        }
    }

    private func freeValues(_ portrait: Portrait) -> [FreeValue] {
        var rows: [FreeValue] = []
        if let path = portrait.lifePath {
            rows.append(
                FreeValue(
                    label: JourneyL10n.systemName(.numerology),
                    value: String(localized: JourneyL10n.lifePath(path))))
        }
        if let card = portrait.birthCardName {
            let numeral = portrait.birthCardNumeral.map { "\($0) " } ?? ""
            rows.append(FreeValue(label: JourneyL10n.systemName(.birthCard), value: numeral + card))
        }
        if let phase = portrait.moonPhase.flatMap(JourneyL10n.moonPhase) {
            rows.append(FreeValue(label: String(localized: JourneyL10n.moon), value: phase))
        }
        return rows
    }

    /// One handed-over fact. A named type rather than a tuple because it is
    /// what `ForEach` identifies rows by, and a tuple cannot carry the
    /// `Identifiable` conformance that says the label is the identity.
    private struct FreeValue: Identifiable {
        let label: String
        let value: String
        var id: String { label }
    }

    // MARK: — the chapter that costs nothing

    @ViewBuilder
    private func freeChapter(_ portrait: Portrait) -> some View {
        if let chapter = portrait.freeChapter {
            VStack(alignment: .leading, spacing: 0) {
                FadedRule().padding(.vertical, 22)

                Text(JourneyL10n.freeChapterLabel)
                    .almaOverline()
                    .padding(.bottom, 12)

                Button {
                    onOpenChapter(portrait.system, chapter.slug)
                } label: {
                    HStack(alignment: .top, spacing: 14) {
                        Text(chapter.numeral)
                            .font(.almaNumeral)
                            .foregroundStyle(Color.almaGoldDeep)
                            .frame(width: 26, alignment: .leading)

                        VStack(alignment: .leading, spacing: 5) {
                            Text(chapter.title)
                                .almaHeadingM()
                                .multilineTextAlignment(.leading)
                            Text(chapter.question)
                                .almaMeta()
                                .multilineTextAlignment(.leading)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)

                        Image(systemName: "arrow.right")
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(Color.almaGold)
                            .padding(.top, 4)
                    }
                    .padding(.vertical, 4)
                }
                .buttonStyle(.plain)
                .accessibilityElement(children: .combine)
            }
        }
    }

    // MARK: — what is still shut, and why

    @ViewBuilder
    private var needsTime: some View {
        if !journey.hasTime {
            HStack(spacing: 14) {
                Text(JourneyL10n.needsTimeRow)
                    .font(AlmaFonts.ui(15.5))
                    .foregroundStyle(Color.almaInkLight.opacity(0.7))
                    .frame(maxWidth: .infinity, alignment: .leading)
                Text(JourneyL10n.needsTime)
                    .almaTag(.gold)
            }
            .padding(.top, 22)
            .padding(.vertical, 12)
            .accessibilityElement(children: .combine)
        }
    }
}

/// The twelve glyphs, by the English sign name the backend returns.
///
/// A table and not a computed offset from a zodiac index: the index would be
/// one line and would silently produce the wrong glyph the first time a name
/// arrives that this app has not seen. Twelve entries and a `nil` — and a `nil`
/// draws nothing at all, which on this screen is the correct answer.
///
/// **Every glyph carries U+FE0E, and it is not optional.** U+2648…U+2653 have
/// *emoji* presentation by default on iOS, so `"♓"` alone renders as a purple
/// rounded square from Apple Color Emoji — which is what the portrait shipped
/// with until it was looked at on a device. The variation selector asks for the
/// text presentation, and the glyph comes back as type: a gold outline in the
/// serif, which is the only form the brand has room for. The web app writes it
/// the same way, for the same reason.
enum ZodiacGlyph {
    private static let text = "\u{FE0E}"

    private static let glyphs: [String: String] = [
        "Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋",
        "Leo": "♌", "Virgo": "♍", "Libra": "♎", "Scorpio": "♏",
        "Sagittarius": "♐", "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓",
    ]

    static func glyph(for english: String) -> String? {
        glyphs[english].map { $0 + text }
    }
}

/// A row that wraps.
///
/// SwiftUI has no flow layout and the three pills on the portrait are the only
/// place in the journey that needs one — but it is a real need rather than a
/// nicety: "Ascendente Sagittario" beside "Sentiero di vita 9" is wider than a
/// phone, and an `HStack` answers that by squeezing both into ellipses.
struct FlowRow: Layout {

    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.replacingUnspecifiedDimensions().width
        let rows = arrange(subviews: subviews, in: width)
        let height = rows.reduce(0) { $0 + $1.height } + spacing * CGFloat(max(0, rows.count - 1))
        return CGSize(width: width, height: height)
    }

    func placeSubviews(
        in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()
    ) {
        var y = bounds.minY
        for row in arrange(subviews: subviews, in: bounds.width) {
            // Centred, because these sit under a centred name and a centred
            // glyph, and a left-aligned last row under a centred column reads
            // as a mistake.
            var x = bounds.minX + (bounds.width - row.width) / 2
            for index in row.indices {
                let size = subviews[index].sizeThatFits(.unspecified)
                subviews[index].place(
                    at: CGPoint(x: x, y: y + (row.height - size.height) / 2),
                    proposal: ProposedViewSize(size)
                )
                x += size.width + spacing
            }
            y += row.height + spacing
        }
    }

    private struct Row {
        var indices: [Int] = []
        var width: CGFloat = 0
        var height: CGFloat = 0
    }

    private func arrange(subviews: Subviews, in width: CGFloat) -> [Row] {
        var rows: [Row] = []
        var current = Row()
        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            let needed = current.indices.isEmpty ? size.width : current.width + spacing + size.width
            if needed > width, !current.indices.isEmpty {
                rows.append(current)
                current = Row()
            }
            current.width = current.indices.isEmpty ? size.width : current.width + spacing + size.width
            current.height = max(current.height, size.height)
            current.indices.append(index)
        }
        if !current.indices.isEmpty { rows.append(current) }
        return rows
    }
}
