import SwiftUI

/// One of the five legal documents.
///
/// Reached from Settings → DATA & LEGAL and from the three links at the foot of
/// the paywall. Both of those were pushing a placeholder that said "This screen
/// has not been built yet", which is a guaranteed rejection twice over:
/// Guideline 3.1.2 requires functional links to the terms and the privacy policy
/// from the screen a subscription is sold on, and 5.1.1 requires the privacy
/// policy to be reachable at all. Links that are present and dead are worse than
/// absent, because they read as an attempt to satisfy the checklist.
///
/// The text is in the binary — see `LegalText` for why — so this screen has no
/// state, no loading and no failure. It is the only screen in the app that
/// cannot fail, and that is deliberate.
struct LegalScreen: View {

    let document: LegalDocument

    private var doc: LegalDoc { LegalText.document(document) }

    var body: some View {
        ScreenScaffold(
            eyebrow: LocalizedStringResource(stringLiteral: "Alma · \(LegalText.operatorName)"),
            title: L10nCabinet.legal(document),
            mood: .reading,
            seed: 0x4C45_4741
        ) {
            Text(verbatim: "Last updated \(LegalText.updated)")
                .almaMeta()

            // The admission, before the document rather than under it.
            Text(verbatim: LegalText.preamble)
                .almaMeta()
                .almaReadingWidth()
                .padding(.top, 2)

            FadedRule().padding(.vertical, 6)

            Text(verbatim: doc.lead)
                .almaVoice()
                .almaReadingWidth()

            ForEach(doc.sections) { section in
                CabinetSection(label: LocalizedStringResource(stringLiteral: section.title)) {
                    ForEach(Array(section.blocks.enumerated()), id: \.offset) { _, block in
                        BlockView(block: block)
                    }
                }
            }

            FadedRule().padding(.top, AlmaMetrics.gapLarge)

            Text(verbatim: LegalText.footer)
                .almaMeta()
                .almaReadingWidth()
                .padding(.top, 10)

            Text(verbatim: "\(LegalText.operatorName) · Wyoming, United States")
                .almaMeta()
        }
    }
}

/// One paragraph, list, fact or gap.
private struct BlockView: View {

    let block: LegalBlock

    var body: some View {
        switch block {
        case .para(let text):
            Text(verbatim: text)
                .almaBody()
                .almaReadingWidth()
                .padding(.vertical, 6)

        case .points(let items):
            VStack(alignment: .leading, spacing: 12) {
                ForEach(Array(items.enumerated()), id: \.offset) { _, item in
                    HStack(alignment: .firstTextBaseline, spacing: 10) {
                        // The same gold interpunct the paywall's honesty plate
                        // uses. Not a system bullet: a filled disc is a list in
                        // a settings app.
                        Text(verbatim: "·").almaPositions()
                        Text(verbatim: item).almaBody()
                    }
                }
            }
            .almaReadingWidth()
            .padding(.vertical, 6)

        case .fact(let label, let value):
            FactRow(label: label, value: value)

        case .factBlank(let label, let value):
            FactRow(label: label, value: "[\(value)]")

        case .blank(let what):
            Text(verbatim: "[\(what)]")
                .font(.almaBodyFont)
                .foregroundStyle(Color.almaDisagree.opacity(0.8))
                .padding(.vertical, 2)
        }
    }
}

#Preview("Terms") {
    NavigationStack { LegalScreen(document: .terms) }
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}

#Preview("Imprint") {
    NavigationStack { LegalScreen(document: .imprint) }
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}
