import SwiftUI

// MARK: — what kind of turn this was

/// What Alma just did, as opposed to what she found.
///
/// **The bug this type exists to make impossible.** Until now a reply carried
/// one boolean, `answered_from_chart`, and both clients stamped
/// `NOT FROM YOUR CHART` whenever it was false. The field turned out to carry
/// two unrelated meanings — *"I looked at your chart and it does not speak to
/// this"* and *"this reply does not assert anything about you at all"* — so a
/// greeting, which is the second, was labelled as though it were the first.
/// A person who typed "hello" was told, in an uppercase system tag, that their
/// hello was not in their chart. `docs/CONVERSATION.md` §5.4 has the four
/// measured turns where the flag and the citations flatly contradict each
/// other.
///
/// So the wire field the clients render is `turn_kind`, and it names the
/// **shape of the turn**, not the outcome of a search. The rules agent owns the
/// values; this enum owns what each one looks like.
///
/// **Unknown values are not an error.** A new branch of the taxonomy arriving
/// from a newer backend must degrade to "a reply", never to a decoding failure
/// that blanks a conversation somebody is having. `init(rawValue:)` failing
/// falls through to [resolve], which is also the whole of the pre-`turn_kind`
/// path.
enum ChatTurnKind: String, Sendable, Equatable, Codable {

    /// A claim about this person, read from their placements. The one kind that
    /// must show its citations — that is the entire difference between Alma and
    /// a chatbot wearing an astrologer's hat.
    case reading

    /// She read the chart and it genuinely has nothing to say about this. She
    /// has already said so in words; the interface adds a quiet footnote so a
    /// general answer is not mistaken for a reading.
    case chartSilent = "chart_silent"

    /// A turn that asserts nothing about anybody: a greeting, a thank-you, a
    /// question about what she can do, a message in a language we do not write
    /// yet. Taxonomy group A and most of E. **Never labelled**, because there
    /// is no claim here to qualify.
    case conversation

    /// Distress, a medical question, anything in taxonomy group D. Rendered as
    /// prose with nothing decorating it — a person who has just said they feel
    /// awful should not be handed a row of uppercase metadata.
    case care

    /// What to draw, from whatever the server actually sent.
    ///
    /// **The legacy branch is the interesting one**, because the old payload
    /// cannot distinguish a greeting from a silent chart — that is precisely
    /// the ambiguity `turn_kind` was added to remove. Given citations, it is a
    /// reading. Given none, the two candidates are "she greeted you", where the
    /// label is a lie, and "the chart is silent", where `CHAT_RULES` already
    /// requires her to have said so in her own sentence, so the label is a
    /// duplicate. Choosing `.conversation` therefore trades a redundancy for a
    /// falsehood, which is the right way round. The rejected alternative —
    /// keeping `.chartSilent` as the fallback — is what shipped the screenshot
    /// in the bug report.
    ///
    /// Consequence worth stating plainly: **the "not from your chart" note now
    /// renders only when the server names the kind.** Silence on the wire buys
    /// silence on the screen.
    static func resolve(
        raw: String?,
        citedFactors: [String],
        answeredFromChart: Bool?
    ) -> ChatTurnKind {
        if let raw, let known = ChatTurnKind(rawValue: raw) {
            return known
        }
        if !citedFactors.isEmpty {
            return .reading
        }
        _ = answeredFromChart  // deliberately not consulted; see above
        return .conversation
    }

    /// Whether the "read from" line belongs under this answer. Citations are
    /// shown wherever they exist — a `care` reply that cited a placement still
    /// made a claim — with one exception: `.conversation` asserts nothing, so
    /// anything it cited is decoration.
    var showsCitations: Bool { self != .conversation }

    /// Whether the honest footnote belongs under this answer.
    var showsChartSilentNote: Bool { self == .chartSilent }
}

// MARK: — one message, on both screens that show one

/// A question or an answer, drawn the same way in the live transcript and in a
/// conversation read back a week later.
///
/// **Shared rather than duplicated, and that is the fix, not a tidy-up.** The
/// two screens had two copies of this and they disagreed in a way nobody could
/// see from either file: `GET /v1/chat/threads/{id}` does not return
/// `answered_from_chart`, so the same message rendered a tag live and no tag
/// after a relaunch. One view means one rule, and the rule is above.
struct ChatMessageView: View {

    let message: ChatMessage

    private var isAlma: Bool { message.role != "user" }

    private var kind: ChatTurnKind {
        ChatTurnKind.resolve(
            raw: message.turnKind,
            citedFactors: message.citedFactors,
            answeredFromChart: message.answeredFromChart
        )
    }

    var body: some View {
        // **Sides, because this is a conversation and people read them by
        // side before they read a word.**
        //
        // Both turns used to be left-aligned, told apart by a gold hairline
        // down the left of what the reader had said — a page of transcript
        // rather than an exchange. The owner\'s note was that his own text
        // belongs on the right and Alma\'s on the left, as in every messaging
        // app anybody has ever used, and the convention is worth more than the
        // typography it replaces: it costs nothing to learn because it has
        // already been learned.
        //
        // Alma keeps the full reading width and no bubble — her turns are
        // paragraphs and a chat bubble round three of them is a wall. The
        // reader\'s turn is short by nature, so it gets the bubble.
        VStack(alignment: isAlma ? .leading : .trailing, spacing: 10) {
            if isAlma {
                Text(verbatim: message.body)
                    .almaVoice()
                    .almaReadingWidth()
                    .textSelection(.enabled)

                if kind.showsCitations, !message.citedFactors.isEmpty {
                    CitationNote(factors: message.citedFactors)
                }

                if kind.showsChartSilentNote {
                    // A sentence, in her register, in the first person — not a
                    // tag. `NOT FROM YOUR CHART` in uppercase gold read as a
                    // compliance warning stapled to a person's conversation,
                    // in a product whose entire voice is somebody talking.
                    Text(ScreenL10n.chatSilent)
                        .almaMeta()
                        .almaReadingWidth()
                        .padding(.top, 2)
                }
            } else {
                Text(verbatim: message.body)
                    .font(.almaBodyFont)
                    .foregroundStyle(Color.almaBody)
                    .multilineTextAlignment(.leading)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                            .fill(Color.almaVeil)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                            .stroke(Color.almaGold.opacity(0.22), lineWidth: 1)
                    )
                    // Never the full width: a bubble that reaches both margins
                    // has stopped being a side and is just a paragraph with a
                    // border round it.
                    .frame(maxWidth: 300, alignment: .trailing)
            }
        }
        .frame(maxWidth: .infinity, alignment: isAlma ? .leading : .trailing)
    }
}

// MARK: — the citations

/// Where an answer was read from — one quiet line that opens into the pills.
///
/// **Why it is not five pills any more.** The factors are the engine's own
/// identifiers and they read like it: `t-square: moon, jupiter, pluto (apex
/// pluto in Sagittarius)`, `soul urge 7`. Stacked open under every answer they
/// took four or five lines of jargon, and because the tab resumes the last
/// conversation, a person opening the chat met that block *before* a single
/// sentence of Alma's. The citation is the product's whole claim and it is not
/// being hidden — it is being stated in one line, with the first factor
/// visible, and it opens on a tap.
///
/// Collapsed by default rather than remembered: this is per message and per
/// appearance, and a preference switch for "show my citations" would be a
/// setting nobody asked for about a thing they can already tap.
struct CitationNote: View {

    let factors: [String]

    @State private var open = false

    /// The first factor, and how many more there are. Never a translated noun:
    /// "3 placements" needs a plural rule in six languages to say what "+2"
    /// says in all of them, and the factor itself is the interesting part.
    private var summary: String {
        guard let first = factors.first else { return "" }
        return factors.count > 1 ? "\(first)  +\(factors.count - 1)" : first
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button {
                withAnimation(AlmaMotion.ui) { open.toggle() }
            } label: {
                HStack(alignment: .firstTextBaseline, spacing: 10) {
                    Text(L10nCabinet.readFrom).almaOverline().fixedSize()
                    Text(verbatim: summary)
                        .font(.almaNumeral)
                        .foregroundStyle(Color.almaGoldBright.opacity(0.85))
                        .lineLimit(1)
                        .truncationMode(.tail)
                    Spacer(minLength: 0)
                    Text(verbatim: open ? "−" : "+")
                        .font(AlmaFonts.display(14, relativeTo: .footnote))
                        .foregroundStyle(Color.almaGold.opacity(0.6))
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(Text(ScreenL10n.chatReadFromAll))
            .accessibilityValue(Text(verbatim: factors.joined(separator: ", ")))

            if open {
                PillWrap(items: factors)
            }
        }
        .padding(.top, 2)
    }
}

// MARK: — while she thinks

/// Twenty to thirty seconds of nothing is indistinguishable from a send that
/// failed, so the wait is drawn rather than left blank.
///
/// **Two sentences, not one.** The first is the honest description of what is
/// happening; after ten seconds it is replaced, because a line that has not
/// changed in half a minute stops reading as progress and starts reading as a
/// hang. The threshold is under the measured floor of a real turn, so the
/// second line is what somebody sees for most of a normal wait — that is
/// intentional, it is the reassuring one.
struct ThinkingLine: View {

    @State private var pulse = false
    @State private var longWait = false

    var body: some View {
        HStack(spacing: 12) {
            AlmaPresence(size: 24, ring: false)
                .opacity(pulse ? 1.0 : 0.45)
                .animation(
                    .easeInOut(duration: 1.1).repeatForever(autoreverses: true),
                    value: pulse
                )
            Text(longWait ? ScreenL10n.thinkingStill : ScreenL10n.thinking).almaMeta()
        }
        .accessibilityElement(children: .combine)
        .task {
            pulse = true
            try? await Task.sleep(for: .seconds(10))
            withAnimation(AlmaMotion.ui) { longWait = true }
        }
    }
}

// MARK: — the four turns, side by side

/// The whole rule, visible in one canvas.
///
/// The four cases below are real turns from `docs/CONVERSATION.md`: the
/// greeting the old code labelled, the ordinary cited answer, an answer that
/// cited five placements *and* reported `answered_from_chart: false`, and a
/// genuinely silent chart. There is no test target on this project, so this
/// preview is where the rule is checked by eye — only the last one carries a
/// note, and none of them carries a tag.
#Preview("turn kinds") {
    ScrollView {
        VStack(alignment: .leading, spacing: 28) {
            ChatMessageView(message: .preview(role: "user", body: "Hello Shaka a"))
            ChatMessageView(message: .preview(
                body: "Hello. What would you like to look at?",
                kind: "conversation"
            ))
            ChatMessageView(message: .preview(
                body: "When you are alone, you are less the public figure and more the editor.",
                cited: ["sun 23°38′ ♓︎ · house 10", "moon 28°36′ ♒︎ · house 7", "mercury in Virgo"],
                kind: "reading"
            ))
            ChatMessageView(message: .preview(
                body: "A chart describes temperament, not neurology.",
                cited: ["mercury in Virgo", "moon 28°36′ ♒︎ · house 7"],
                fromChart: false
            ))
            ChatMessageView(message: .preview(
                body: "Nothing in your chart speaks to whether to take this job — what it does describe is how you decide.",
                kind: "chart_silent"
            ))
            ThinkingLine()
        }
        .almaPadding()
    }
    .frame(maxWidth: .infinity, maxHeight: .infinity)
    .nightSky(.reading, seed: 0x4348_5450)
}

extension ChatMessage {
    /// Preview data, and named so nothing can mistake it for something fetched.
    static func preview(
        role: String = "alma",
        body: String,
        cited: [String] = [],
        fromChart: Bool? = nil,
        kind: String? = nil
    ) -> ChatMessage {
        ChatMessage(
            id: UUID().uuidString,
            role: role,
            body: body,
            citedFactors: cited,
            answeredFromChart: fromChart,
            turnKind: kind,
            createdAt: "2026-08-07T00:00:00Z"
        )
    }
}
