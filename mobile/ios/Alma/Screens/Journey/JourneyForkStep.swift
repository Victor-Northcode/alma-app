import SwiftUI

/// The fork: which of the two identical times is yours.
///
/// The clocks went back that night, so the wall clock somebody gave happened
/// twice — both real, both giving a different sky. The server refuses to guess
/// and is right to: a coin flipped here lands in the houses, in the solar return
/// and in a chart the same person is later asked to pay for.
///
/// **This is an interrupt in the ceremony, not a step of the questionnaire.** It
/// can only arrive after "Build my sky", so it carries no numeral — the overline
/// says what it is about, and the arrow leads back to the time step rather than
/// one screen back in a sequence this does not belong to. The beats behind it
/// pause; they do not restart.
///
/// **The two options differ by their name, not by their time.** The time is the
/// same on both — that is the whole point — and what separates them is what the
/// clock was called that night. Those names arrive from the server: a phone
/// carries no zone-history database to work them out from.
struct JourneyForkStep: View {

    let fork: AlmaError.BirthTimeFork
    /// The wall clock the person entered, "02:30".
    let time: String
    let city: String
    let onChoose: (String) -> Void
    let onBack: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text(JourneyL10n.dstOverline).almaOverline()
                Spacer()
                Button(action: onBack) {
                    Image(systemName: "arrow.left")
                        .font(.system(size: 16, weight: .regular))
                        .foregroundStyle(Color.almaGold)
                        .frame(width: 44, height: 44)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(Text(JourneyL10n.back))
            }

            Spacer(minLength: 12)

            Text(JourneyL10n.dstTitle(time)).almaDisplayL()

            Text(JourneyL10n.dstBody(city: city, date: transitionDate, time: time))
                .almaMeta()
                .almaReadingWidth()
                .padding(.top, 18)

            choice(
                title: JourneyL10n.dstEarlier,
                note: JourneyL10n.dstEarlierSub(
                    time: time, abbreviation: fork.earlier?.abbreviation ?? ""),
                action: { onChoose("earlier") }
            )
            .padding(.top, 26)

            choice(
                title: JourneyL10n.dstLater,
                note: JourneyL10n.dstLaterSub(
                    time: time, abbreviation: fork.later?.abbreviation ?? "", delta: delta),
                action: { onChoose("later") }
            )
            .padding(.top, 14)

            // Whoever genuinely does not know needs a way through as well, and
            // an honest one: an hour moves the houses, it does not rewrite the
            // chart.
            Text(JourneyL10n.dstFooter(delta))
                .font(AlmaFonts.ui(12))
                .foregroundStyle(Color.almaBody.opacity(0.5))
                .almaReadingWidth()
                .padding(.top, 20)

            Spacer(minLength: 24)
        }
        .almaPadding()
        .padding(.top, 12)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    /// One of the two instants: the title in the serif, what tells it apart
    /// beneath.
    private func choice(
        title: LocalizedStringResource,
        note: LocalizedStringResource,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(AlmaFonts.display(17, relativeTo: .headline))
                    .foregroundStyle(Color.almaInkLight)
                Text(note).almaMeta()
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 20)
            .padding(.vertical, 14)
            .overlay(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .stroke(Color.almaHairline, lineWidth: 1)
            )
            .contentShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    /// How far apart the two instants are, said in words.
    ///
    /// A hardcoded "an hour" cannot stand here: half-hour transitions exist —
    /// Lord Howe Island and its like — and there the sentence would be false.
    private var delta: String {
        let hours = abs(fork.gapHours ?? 1)
        return String(localized: hours < 0.75 ? JourneyL10n.dstDeltaHalfHour : JourneyL10n.dstDeltaHour)
    }

    /// The night the clocks moved, written the way this locale writes a date.
    ///
    /// The server sends "1992-09-27". Showing a reader ISO is showing them the
    /// machine; a value that will not parse is shown as it came rather than
    /// replaced with a date nobody named.
    private var transitionDate: String {
        let iso = Date.ISO8601FormatStyle(dateSeparator: .dash, timeZoneSeparator: .omitted)
            .year().month().day()
        guard let parsed = try? Date(fork.transitionLocalDate, strategy: iso) else {
            return fork.transitionLocalDate
        }
        return parsed.formatted(.dateTime.year().month(.wide).day())
    }
}
