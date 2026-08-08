import SwiftUI

/// The daily, on Today, for everybody.
///
/// **The push is a reminder; this is the product.** A person who never allows
/// notifications, or who is on a phone where none can be delivered, still gets
/// the whole of it — and so does a free reader, because
/// `alma/api/routers/systems.py` returns the transits payload whole even when
/// the system is locked, so the arithmetic below is available to everyone the
/// same way the rest of Today's calculations are.
///
/// It cites its event the way every other screen in this app cites its factors:
/// the notation a chart prints, the natal placement it is read against, the
/// instant it perfects, and the window it has been live for. That is the
/// difference `alma/engine/transits.py`'s own docstring draws — *"'Sun' is a
/// horoscope; 'Saturn squares your Sun exactly on 14 June, in orb from…' is a
/// reading"* — and it is the whole argument for this feature existing at all.
///
/// And it says nothing on a day with nothing in it. `THE-DAILY.md §1` measured
/// 22 to 46 such days a year at the honest threshold; a block that produced a
/// sentence on all of them would be a horoscope with extra steps.
struct DailyBlock: View {

    /// Everything the transits payload contains, already parsed.
    let contacts: [DailyContact]
    /// Whether the chart lost its angles for want of a birth time. A chart with
    /// no birth time is measurably thinner — it has no Ascendant and no
    /// Midheaven, two of the five natal points carrying full weight, and gets
    /// about 65 empty days a year against 0–20 for the others — and no design
    /// fixes that. It is said rather than silently served less.
    let missingBirthTime: Bool

    private var event: DailyContact? {
        DailyRule.candidates(among: contacts, on: .now, preference: .occasionally).first
    }

    var body: some View {
        CabinetSection(label: DailyL10n.todayLabel) {
            if let event {
                exact(event)
            } else {
                empty
            }
        }
    }

    // MARK: — a day with something in it

    private func exact(_ contact: DailyContact) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            // Notation, large, in the serif. The engine names its bodies in
            // English in every locale, so two glyphs say in all six languages
            // what fourteen translated planet names would — the same decision
            // the transit rows already make, and the engine's own sentence
            // travels along as the accessibility label.
            Text(verbatim: contact.notation)
                .font(AlmaFonts.display(30, relativeTo: .title))
                .foregroundStyle(Color.almaInkLight)

            // The instant. This is the line that makes it a reading rather than
            // a horoscope, so it is set in gold and given its own row rather
            // than joined into a meta string with everything else.
            if let exactAt = contact.exact {
                Text(DailyL10n.exactAt(exactAt.formatted(date: .omitted, time: .shortened)))
                    .font(.almaNumeral)
                    .foregroundStyle(Color.almaGoldBright)
            }

            if let window = windowLine(contact) {
                Text(verbatim: window).almaMeta()
            }

            Text(verbatim: ChartFacts.orb(contact.orbNow)).almaMeta()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 8)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(verbatim: contact.spoken))
    }

    /// "In orb since 4 August, in orb until 19 August".
    ///
    /// Both halves are optional and for different reasons: a contact already in
    /// orb when the scan began has no `enters`, and one still in orb at the end
    /// of the window has no `leaves`. Neither is invented — an absent edge
    /// simply does not print, which is this app's rule everywhere.
    private func windowLine(_ contact: DailyContact) -> String? {
        let since = contact.enters.map {
            String(localized: DailyL10n.inOrbSince($0.formatted(.dateTime.day().month(.wide))))
        }
        let until = contact.leaves.map {
            String(localized: DailyL10n.inOrbUntil($0.formatted(.dateTime.day().month(.wide))))
        }
        let parts = [since, until].compactMap { $0 }
        return parts.isEmpty ? nil : parts.joined(separator: ", ")
    }

    // MARK: — a day with nothing in it

    /// Silence, said out loud.
    ///
    /// This is the state the whole feature is built to make survivable, and it
    /// is drawn with as much care as the other one. "Nothing is exact today"
    /// is an answer — it is what an ephemeris says about most days — and the
    /// second line points at the contacts that *are* live, which the section
    /// below this one already lists.
    private var empty: some View {
        // Two different silences, and only one of them is a silence.
        //
        // With contacts still in orb the day is not empty at all — it simply
        // has no *exact* aspect, which is true of most days and is the reason
        // an exact one is worth a notification. Saying "nothing is exact
        // today" and stopping there put a sentence about absence at the top of
        // the front page, and the owner read it, reasonably, as a product that
        // does nothing unless you pay.
        let live = contacts.count
        return VStack(alignment: .leading, spacing: 8) {
            if live > 0 {
                Text(DailyL10n.runningTitle).almaHeadingM()
                Text(DailyL10n.runningBody(live)).almaMeta().almaReadingWidth()
            } else {
                Text(DailyL10n.emptyTitle).almaHeadingM()
                Text(DailyL10n.emptyBody).almaMeta().almaReadingWidth()
            }
            if missingBirthTime {
                // Not the same silence. Without a birth time the chart has no
                // Ascendant and no Midheaven to be crossed, so some of these
                // empty days are empty because we were never told the hour —
                // and saying so is the difference between a quiet sky and a
                // thinner chart.
                Text(L10nCabinet.needsBirthTime).almaMeta().almaReadingWidth()
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 6)
    }
}

/// The invitation, and the second entrance to the setting.
///
/// `docs/PUSH.md §5.2` is specific that a switch reachable only from a settings
/// list is a switch nobody finds, and that the second entrance belongs on the
/// surface the content is on, worded as what it is: *tell me the morning it
/// happens*. This is that.
///
/// **It explains what will arrive and how often before anything is asked.** A
/// system dialog on its own is a coin flip; a person who has just read "one
/// notification, at 08:00, about once a week, never at night, and you can turn
/// it off from inside the notification itself" is making a decision instead of
/// guessing. On iOS the acceptance shows no dialog at all — the enrolment is
/// provisional — so this card is the entire ask.
struct DailyInvitation: View {

    @Environment(DailyModel.self) private var daily

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(DailyL10n.askTitle).almaHeadingM()
            Text(DailyL10n.askBody).almaMeta().almaReadingWidth()

            HStack(spacing: 12) {
                Button {
                    Task { await daily.accept() }
                } label: {
                    Text(DailyL10n.askYes)
                }
                .buttonStyle(.alma(.outline, fills: false))

                // Declining is one tap and costs nothing, because it is *our*
                // question rather than the platform's. That asymmetry is the
                // whole reason to ask ours first: a person who taps this and
                // changes their mind next month has the same one tap waiting in
                // Settings, where somebody who denies an iOS dialog has to go
                // digging through the system's own settings tree instead.
                Button {
                    daily.decline()
                } label: {
                    Text(DailyL10n.askNo).almaMeta()
                }
                .buttonStyle(.plain)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, AlmaMetrics.gapLarge)
    }
}
