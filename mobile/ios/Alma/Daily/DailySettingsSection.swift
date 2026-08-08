import SwiftUI
import UserNotifications

/// The control, in Settings, in one tap from anywhere.
///
/// **Everything this screen claims has to be true, and most of it is checked
/// rather than asserted.** That constraint is not general good practice here,
/// it is specific history: the web app once shipped four notification toggles,
/// three of them defaulted on, for letters no sender existed for. They were
/// removed and the Android settings screen still carries the note explaining
/// why. This section is the same feature built the other way round — every line
/// below is derived from something observable, and the one claim that cannot be
/// (the weekly cadence, which was measured on 24 charts that are not this
/// reader's) is put next to a count taken from the reader's own chart.
struct DailySettingsSection: View {

    /// The transits payload, when Today has one. Optional because Settings is
    /// reachable without ever opening Today, and the section has to draw
    /// without it — it simply omits the counted row rather than showing a
    /// number it has not computed.
    var contacts: [DailyContact] = []

    @Environment(DailyModel.self) private var daily
    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router
    @Environment(\.openURL) private var openURL
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        CabinetSection(label: DailyL10n.settingTitle) {
            positions
            detail
            status

            if daily.preference.wantsDelivery {
                arrival
                verified
            }
        }
        // The OS is the truth and the person can change it somewhere we cannot
        // watch. Re-reading on every foreground is what keeps a switch of ours
        // from claiming On over a permission that was revoked in iOS Settings.
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active else { return }
            Task { await daily.refresh(isSubscriber: session.entitlements.isSubscriber) }
        }
    }

    // MARK: — three positions

    private var positions: some View {
        VStack(spacing: 0) {
            ForEach(DailyPreference.allCases) { position in
                Button {
                    choose(position)
                } label: {
                    AlmaRow {
                        Text(position.title)
                            .font(.almaBodyFont)
                            .foregroundStyle(
                                daily.preference == position ? Color.almaGoldBright : Color.almaBody.opacity(0.85)
                            )
                    } trailing: {
                        // A tick and not a radio button. The row is the
                        // control; a second circle beside it would be a second
                        // thing to aim at for the same tap.
                        Text(verbatim: daily.preference == position ? "✓" : "")
                            .font(.almaNumeral)
                            .foregroundStyle(Color.almaGoldBright)
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(daily.preference == position ? [.isSelected] : [])
            }
        }
    }

    /// The detail line for whichever position is selected.
    ///
    /// One line rather than three stacked under three rows. Three would put the
    /// sentence *"No notifications. Today is still here whenever you open it"*
    /// permanently on screen beside two others, and the reason those three
    /// sentences exist is to be read at the moment of choosing — which is when
    /// this one changes.
    private var detail: some View {
        Text(daily.preference.detail)
            .almaMeta()
            .almaReadingWidth()
            .padding(.top, 10)
    }

    private func choose(_ position: DailyPreference) {
        // A free reader gets the door, not a broken switch. `THE-DAILY.md §5.1`
        // is explicit that this is where the paywall belongs: the Today page and
        // every calculation on it stay free, and what is being sold is the
        // living layer arriving unprompted.
        guard session.entitlements.isSubscriber || position == .off else {
            router.push(.offer(system: .transits), on: .settings)
            return
        }
        Task { await daily.choose(position) }
    }

    // MARK: — is any of this actually happening

    /// The honest answer to "will anything arrive".
    ///
    /// Four states, and they are genuinely different situations rather than
    /// four ways of saying the same thing:
    ///
    /// * **denied** — the OS said no. Said once, never again, with the one
    ///   action that can undo it. `PUSH.md §5.5(3)`: show the state once and
    ///   never nag.
    /// * **not delivering** — permitted, but no server has accepted a token.
    ///   This is the state every build is in today, because the route in
    ///   `PUSH.md §3` is a contract nobody has implemented. Saying so is the
    ///   whole reason this block exists.
    /// * **provisional** — arriving, quietly, exactly as designed, with the
    ///   escalation offered.
    /// * **registered** — arriving.
    @ViewBuilder
    private var status: some View {
        if !session.entitlements.isSubscriber && daily.preference.wantsDelivery {
            Text(DailyL10n.subscriberOnly).almaMeta().almaReadingWidth().padding(.top, 12)

        } else if daily.preference == .off {
            EmptyView()

        } else if daily.authorization == .denied {
            VStack(alignment: .leading, spacing: 10) {
                Text(DailyL10n.denied).almaMeta().almaReadingWidth()
                Button {
                    if let url = URL(string: UIApplication.openSettingsURLString) { openURL(url) }
                } label: {
                    Text(DailyL10n.openSettings)
                }
                .buttonStyle(.alma(.outline, fills: false))
            }
            .padding(.top, 12)

        } else if !daily.deliverable {
            // Nothing. «Пока ничего не отправляется. Этот телефон не
            // зарегистрирован для уведомлений…» stood here and the owner cut it:
            // it explains our plumbing to somebody who asked for a switch. The
            // switch works, the daily appears on Today either way, and a person
            // who has not been told about a registration cannot be worried by
            // one failing.
            EmptyView()

        } else if daily.authorization == .provisional {
            VStack(alignment: .leading, spacing: 10) {
                Text(DailyL10n.provisional).almaMeta().almaReadingWidth()
                Button {
                    Task { await daily.letThemArriveProperly() }
                } label: {
                    Text(DailyL10n.upgrade)
                }
                .buttonStyle(.alma(.outline, fills: false))
            }
            .padding(.top, 12)

        } else {
            Text(DailyL10n.registered).almaMeta().almaReadingWidth().padding(.top, 12)
        }
    }

    // MARK: — when

    /// The hour, the quiet hours, and where the clock came from.
    ///
    /// The hour is editable because "I get up at 05:30" is a real fact about a
    /// person and the only one they can tell us that we cannot measure. The
    /// quiet hours are shown and not editable, which is the point of showing
    /// them — it tells the person we thought about it, where making them
    /// editable invites somebody to set 03:00 and then complain about a 03:00
    /// notification.
    private var arrival: some View {
        VStack(spacing: 0) {
            AlmaRow {
                Text(DailyL10n.hour)
                    .font(.almaBodyFont)
                    .foregroundStyle(Color.almaMuted)
            } trailing: {
                // A stepper over the eligible hours rather than a time picker.
                // The picker's minutes are a precision we do not have — the job
                // runs hourly — and offering them would be claiming one.
                Picker(selection: hourBinding) {
                    ForEach(Array(DailyStore.quietUntil..<DailyStore.quietFrom), id: \.self) { hour in
                        Text(verbatim: Self.formatted(hour: hour)).tag(hour)
                    }
                } label: {
                    Text(DailyL10n.hour)
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .tint(Color.almaGoldBright)
            }

            Text(DailyL10n.quiet)
                .almaMeta()
                .almaReadingWidth()
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.top, 10)

            clock
        }
    }

    private var hourBinding: Binding<Int> {
        Binding(
            get: { daily.hour },
            set: { new in Task { await daily.setHour(new) } }
        )
    }

    /// The zone, **and where it came from**.
    ///
    /// Showing the source is what makes the override discoverable to exactly
    /// the person who needs it. Somebody born in Lisbon and living in Toronto
    /// whose notifications land at 03:00 will look here first, and "Lisbon —
    /// from your birth data" tells them in one line what is wrong; a bare
    /// "Lisbon" tells them the app is broken.
    ///
    /// Today it always reads *from your device*, because the device's own zone
    /// is what `AlmaClient` sends on every request and there is no override
    /// stored anywhere yet. The other two labels exist and are translated,
    /// waiting for `alma/auth/accounts.py` to grow the field
    /// `THE-DAILY.md §6.8` asks it for — a workflow that owns that file, not
    /// this one.
    private var clock: some View {
        AlmaRow {
            Text(DailyL10n.timezone)
                .font(.almaBodyFont)
                .foregroundStyle(Color.almaMuted)
        } trailing: {
            VStack(alignment: .trailing, spacing: 2) {
                Text(verbatim: TimeZone.current.identifier)
                    .font(.almaBodyFont)
                    .foregroundStyle(Color.almaInkLight)
                Text(DailyClockSource.device.label).almaMeta()
            }
        }
    }

    // MARK: — the claim, checked against this chart

    /// The cadence promise, verified as far as a client honestly can.
    ///
    /// The detail line above says *about once a week*. That number is real —
    /// `THE-DAILY.md §4.2` simulated the rule over 24 charts for a year and
    /// published the distribution — but it is a number about 24 people who are
    /// not this reader, produced by a rule this app cannot watch running,
    /// because the job that will run it does not exist yet.
    ///
    /// What *can* be checked is this chart, on this phone, with this rule: the
    /// count below applies `DailyRule` to the transits the Today screen already
    /// fetched and says how many of the next thirty days have something exact
    /// in them. It is a **lower bound** — the server sends at most sixty future
    /// contacts, so a dense month can hide days from it — and it is offered as
    /// what it is rather than as a promise.
    @ViewBuilder
    private var verified: some View {
        if !contacts.isEmpty {
            let days = DailyRule.exactDays(
                among: contacts,
                from: .now,
                days: 30,
                preference: daily.preference
            )
            FactRow(
                label: String(localized: DailyL10n.verifiedLabel),
                value: days.formatted(),
                isPosition: true
            )
            // The sentence under it — «Посчитано из твоей собственной карты, на
            // этом устройстве, по тому же правилу, что и уведомление» — is gone.
            // It defended a number nobody had doubted, in the vocabulary of the
            // people who wrote it. The row above says what it says.
        }
    }

    /// "08:00". Hour-of-day in the reader's own locale, so a US phone reads
    /// "8 AM" and a German one "08:00", from one integer.
    private static func formatted(hour: Int) -> String {
        var components = DateComponents()
        components.hour = hour
        components.minute = 0
        let date = Calendar.current.date(from: components) ?? .now
        return date.formatted(date: .omitted, time: .shortened)
    }
}

extension Entitlements {

    /// Whether this account is renting the living layer.
    ///
    /// Asked of `kind` rather than of `system`, for the reason `AccountModel`
    /// already documents: both recurring products are stored against
    /// `system: "*"`, so matching on that told a monthly subscriber they held
    /// the annual plan. `active` is computed server-side because a client
    /// comparing dates gets subscriptions wrong.
    var isSubscriber: Bool {
        entitlements.contains { $0.active && $0.kind != "one_time" }
    }
}
