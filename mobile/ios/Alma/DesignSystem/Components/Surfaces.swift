import SwiftUI

/// The small pieces that hold a screen together: rules, rows, section labels,
/// pills, tags.
///
/// All of them exist to make the "no boxes" rule easy to obey. Content sits on
/// the night and is separated by a hairline; the temptation on iOS is
/// `GroupBox`, `.background(.regularMaterial)` and rounded cards, and every one
/// of those turns Alma into a settings app. What follows is what a screen uses
/// instead.

/// A full-width hairline. One device pixel, so it is the same weight at 2× and
/// 3× as it is in the CSS.
struct Hairline: View {
    var body: some View {
        Rectangle()
            .fill(Color.almaHairline)
            .frame(height: AlmaMetrics.hairline)
    }
}

/// A rule that fades at both ends — used between sections, where a hard line
/// across the night would look like a border.
struct FadedRule: View {
    var body: some View {
        Rectangle()
            .fill(AlmaGradient.fadedRule)
            .frame(height: AlmaMetrics.hairline)
    }
}

/// A section eyebrow with a gold rule running off to the right.
struct SectionLabel: View {
    let text: LocalizedStringResource

    var body: some View {
        // Baseline-aligned, not centre-aligned, and the difference only shows in
        // the five languages that are longer than English. "ÜBER DEINE SYSTEME
        // HINWEG" wraps to two lines, and a centred rule then hangs beside the
        // *second* line with the first one unruled — on the repeating structural
        // motif of the whole cabinet, and the first thing a German reader's eye
        // lands on. Giving the rule a baseline of its own (4 points above its
        // top edge, which sits it near the middle of the eyebrow's cap height)
        // pins it to the first line however many there are.
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(text).almaOverline()
            Rectangle()
                .fill(Color.almaGold.opacity(0.28))
                .frame(height: AlmaMetrics.hairline)
                .alignmentGuide(.firstTextBaseline) { _ in -4 }
        }
        .accessibilityElement()
        .accessibilityLabel(Text(text))
        .accessibilityAddTraits(.isHeader)
    }
}

/// A list row: a label on the left, a value or a status on the right, a
/// hairline under it. The whole of the settings screen and most of the hub is
/// made of these.
struct AlmaRow<Leading: View, Trailing: View>: View {

    @ViewBuilder var leading: Leading
    @ViewBuilder var trailing: Trailing

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 14) {
                leading
                    // The label yields before it can shove the value off the
                    // edge. Without this a long system name in German pushes
                    // the status out of the screen.
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .layoutPriority(0)
                trailing
                    .layoutPriority(1)
            }
            .padding(.vertical, 15)

            Hairline()
        }
    }
}

/// A gold pill — a chart position, a count, a price.
struct AlmaPill: View {
    let text: String
    var tone: Tone = .gold

    enum Tone: Sendable {
        case gold
        case plain
    }

    var body: some View {
        Text(text)
            .font(tone == .gold ? AlmaFonts.display(14, relativeTo: .footnote) : AlmaFonts.ui(13))
            .foregroundStyle(tone == .gold ? Color.almaGoldBright : Color.almaMuted2)
            .padding(.horizontal, 13)
            .padding(.vertical, 7)
            .background(
                Capsule().fill(
                    tone == .gold ? Color.almaGold.opacity(0.12) : Color.almaBody.opacity(0.06)
                )
            )
    }
}

/// The agreement marker. Its two colours are the only non-gold accents in the
/// product, and they are reserved for exactly this: whether the systems agree.
struct AgreementChip: View {
    let text: String
    let tone: AlmaTagTone

    var body: some View {
        Text(text)
            .almaTag(tone)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Capsule().fill(tone.colour.opacity(0.16)))
    }
}

/// Locked text: the real sentences, blurred.
///
/// It is the real text and not a placeholder on purpose — a blurred paragraph
/// with the right shape, the right length and the right line breaks is honest
/// about there being something there, and lorem ipsum under a price is not.
/// The first line stays readable; that is the teaser, and it is free.
struct LockedText: View {
    let lines: [String]
    /// How many lines are shown unblurred before the veil comes down.
    var readableLines: Int = 1

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            ForEach(Array(lines.enumerated()), id: \.offset) { index, line in
                Text(line)
                    .almaBody()
                    .blur(radius: index < readableLines ? 0 : 5)
                    .accessibilityHidden(index >= readableLines)
            }
        }
        // Selection is disabled on the blurred part in the web app; on iOS the
        // equivalent is refusing the text-selection gesture entirely, since a
        // long press that copies unblurred text would hand over the thing that
        // is being sold.
        .textSelection(.disabled)
    }
}

#Preview("Surfaces") {
    VStack(alignment: .leading, spacing: 0) {
        SectionLabel(text: "the eight")
        AlmaRow {
            Text(verbatim: "Natal chart").almaHeadingM()
        } trailing: {
            AgreementChip(text: "calculated", tone: .agree)
        }
        AlmaRow {
            Text(verbatim: "Solar return").almaHeadingM()
        } trailing: {
            Text(verbatim: "needs birth time").almaTag(.gold)
        }
        HStack {
            AlmaPill(text: "☉ 23° ♓︎")
            AlmaPill(text: "life path 7", tone: .plain)
        }
        .padding(.top, 20)
    }
    .almaPadding()
    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    .nightSky()
}
