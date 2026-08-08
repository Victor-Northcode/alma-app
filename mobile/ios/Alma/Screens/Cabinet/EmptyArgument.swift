import SwiftUI

/// What the app says about itself before it has any of your data.
///
/// **This is the 4.3(b) argument, in front of the wall instead of behind it.**
/// Guideline 4.3(b) names fortune telling as a category that is refused *unless
/// it offers a meaningfully different or improved experience*, and 1.1.6 closes
/// the "for entertainment purposes" escape hatch. Everything that makes Alma
/// meaningfully different — eight independent systems, forty-one chapters, a
/// citation on every sentence, a refusal to predict, a view of where the systems
/// *disagree* — was true and was two screens and ninety seconds of data entry
/// away. What was in front of a reviewer for the first minute was "Add your
/// birth date and I can read you", which is what every horoscope app on the
/// store also asks for.
///
/// A reviewer judges what is in front of them. None of what is below needs
/// anybody's birth data: the eight names and their chapter counts are facts
/// about the product, the method claim is a claim about method, and the sample
/// citation is labelled as a sample.
///
/// **Nothing here is invented.** The chapter counts are `SystemSlug.chapterCount`
/// — the same numbers `alma/ai/chapters.py` defines and the same forty-one the
/// archive is sold as. The one thing on the screen that is not a fact about this
/// account is the sample citation, and it carries the word "example" on it,
/// because a plausible-looking chart position that is nobody's is exactly the
/// kind of fixture this codebase has already had to delete once.
struct EmptyArgument: View {

    /// What the button does. Both callers open the journey; it is a parameter so
    /// this view holds no router.
    let begin: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: AlmaMetrics.gap) {
            Text(ScreenL10n.emptyTitle).almaVoice().almaReadingWidth()
            Text(ScreenL10n.emptyLead).almaBody().almaReadingWidth()

            Button(action: begin) { Text(L10nCabinet.addBirthData) }
                .buttonStyle(.almaGold)
                .padding(.top, 4)

            eight
            example

            Text(L10nCabinet.notPrediction)
                .almaMeta()
                .almaReadingWidth()
                .padding(.top, AlmaMetrics.gapLarge)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    /// The eight, with the number of chapters each has. Listing them costs
    /// nothing and is honest — they exist whether or not this account has a
    /// birth date — and "0/8 calculated" above a blank screen was telling a
    /// reviewer that there are eight of something without ever saying what.
    private var eight: some View {
        CabinetSection(label: L10n.tabSystems, trailing: "41") {
            ForEach(SystemSlug.allCases) { system in
                AlmaRow {
                    Text(system.displayName).almaHeadingM()
                } trailing: {
                    Text(ScreenL10n.chapters(system.chapterCount)).almaTag(.muted)
                }
            }
        }
    }

    /// One worked citation, in the exact visual language a real one uses.
    ///
    /// The pill is the same `AlmaPill` a chapter's `cited_factors` are drawn in,
    /// so what a reviewer sees here is what they will see after onboarding. The
    /// tag under it says "example" and is not decoration: without it this is a
    /// chart position presented on a screen belonging to somebody who has not
    /// given us a birth date.
    private var example: some View {
        CabinetSection(label: ScreenL10n.emptyExample) {
            VStack(alignment: .leading, spacing: 10) {
                AlmaPill(text: "☉ 23°38′ ♓︎ · house 10")
                Text(ScreenL10n.exampleTag).almaTag(.muted)
            }
            .padding(.vertical, 4)

            Text(ScreenL10n.emptyExampleNote).almaMeta().almaReadingWidth()
        }
    }
}

#Preview {
    ScrollView {
        EmptyArgument {}
            .almaPadding()
            .padding(.vertical, 20)
    }
    .nightSky()
}
