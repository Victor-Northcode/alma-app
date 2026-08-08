import SwiftUI

/// Tab 4 — settings, and everything three legal pages promise is reachable.
///
/// The subscription terms say cancelling takes two taps; the privacy page
/// promises an export; the deletion page promises erasure. All three are real
/// calls here, with real outcomes, because a page that describes a flow that
/// does not exist is worse than no page.
///
/// **Cancelling, on a store.** Apple does not let a server cancel an
/// auto-renewable subscription, and `/v1/billing/subscription/cancel` answers
/// 409 for one — deliberately, since a second cancellation path is how somebody
/// who cancelled in the App Store gets told by us that their plan renews. So
/// the screen offers both, in the right order: the App Store link, which is the
/// route for anything bought in this app *and* what the guideline requires to
/// be present, and underneath it the two-tap server cancel, which is the route
/// for a plan bought on the web with a card. When the server answers 409 the
/// copy says so and points back at the store, and nothing was written.
struct SettingsScreen: View {

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router
    @Environment(\.openURL) private var openURL

    @State private var model: AccountModel?

    /// The transits, for the one row on this screen that checks a claim rather
    /// than making one.
    ///
    /// A second request on a settings screen needs a defence, and this is it:
    /// the cadence sentence under *Occasionally* — "about once a week" — was
    /// measured on 24 charts, none of which is this reader's, by a rule no
    /// running job applies yet. The counted row underneath it is the same rule
    /// applied to *their* chart, on this device, and it is the only part of the
    /// promise a client can honestly verify. The result is cached server-side
    /// (`compute_cached`) and this is the same payload Today already asked for,
    /// so in practice it is one cheap round trip rather than a recomputation.
    @State private var dailyContacts: [DailyContact] = []

    /// Where Apple keeps subscriptions. A constant rather than the catalogue's
    /// `manage_url`, because that field is not on the `Catalogue` type this
    /// client decodes — and this is an iOS app, so for anything bought in it
    /// the answer is this URL whatever the catalogue says.
    private static let appleSubscriptions = URL(string: "https://apps.apple.com/account/subscriptions")!

    var body: some View {
        ScreenScaffold(seed: 0x5345_5454) {
            Text(L10nCabinet.settingsTitle).almaDisplayL()

            identity
            birthData
            // Above the plan and the legal doors, below the birth data.
            //
            // It is the only thing on this screen that changes what the app
            // *does* rather than describing what it holds, and it is the one a
            // person arrives here looking for after a notification they did not
            // want — so it is above the fold rather than under four sections of
            // export, deletion and imprint links. `THE-DAILY.md §5`: anything
            // that cannot be turned off in one tap is a defect.
            DailySettingsSection(contacts: dailyContacts)
            language

            if let model {
                PlanSection(model: model, hasAddress: session.account?.email?.isEmpty == false) {
                    openURL(Self.appleSubscriptions)
                }
                // The cheapest high-intent visitor this app will ever have is
                // somebody who opened Settings to look at their plan — and the
                // free state used to *describe* the plan with nothing to tap.
                if !session.entitlements.isSubscriber {
                    Button {
                        router.push(.offer(system: nil))
                    } label: {
                        Text(L10nCabinet.plansCta)
                    }
                    .buttonStyle(.alma(.outline, fills: false))
                    .padding(.top, AlmaMetrics.gap)
                }
                // Restore, in the one place it is always reachable — regardless
                // of what the store answered, what this account holds, and
                // whether a paywall was ever opened. Guideline 3.1.1 expects a
                // restore mechanism for non-consumables and reviewers look for
                // it somewhere durable; more practically, the person who needs
                // it most is on a new phone with a fresh guest account, and the
                // only route we gave them was "open a screen that tries to sell
                // you what you already own".
                RestorePurchasesButton()
                    .padding(.top, AlmaMetrics.gap)

                dataAndLegal(model)
            }

            finePrint
        }
        .task {
            let model = model ?? AccountModel(client: session.client)
            self.model = model
            await model.loadPlan()
        }
        // Separate from the plan, and allowed to fail on its own. A transits
        // request that 503s must leave the three positions usable — the switch
        // is what somebody came here for, and a screen that hides it because a
        // verification number could not be computed has its priorities exactly
        // backwards.
        .task(id: session.profile?.id) {
            guard session.hasBirthData, dailyContacts.isEmpty else { return }
            let result = try? await session.client.compute(
                .transits, locale: session.locale, extra: ["days": .number(30)]
            )
            dailyContacts = result.map { DailyContact.all(in: $0.data) } ?? []
        }
    }

    // MARK: — who this is

    /// What to call this person: the name on their chart, then the one on the
    /// account, then nothing.
    private var displayName: String? {
        let onProfile = session.profile?.name?.trimmingCharacters(in: .whitespaces)
        if let onProfile, !onProfile.isEmpty { return onProfile }
        return session.account?.displayName
    }

    private var identity: some View {
        CabinetSection(label: L10nCabinet.accountLabel) {
            // A heading and a line under it rather than two labelled rows: the
            // labels would have to be "name" and "email", and this account may
            // honestly have neither — a guest is a real account with real
            // purchases and no identity, and "name: —" reads as a field
            // somebody failed to fill in.
            VStack(alignment: .leading, spacing: 4) {
                // **The name they gave, wherever they gave it.**
                //
                // This read only `account.displayName` — which is set when
                // somebody signs in — so a person who typed their name on the
                // second screen of the journey was greeted as "Guest" for ever
                // after. The owner typed *Анатолий*, walked eight screens, and
                // was told he was nobody.
                //
                // The journey writes the name onto the *profile*, because that
                // is what a chart is written for. Reading both, profile first,
                // says the true thing: the account may have no identity
                // attached and the person still has a name, and "Guest" is only
                // for somebody who has genuinely never told us one.
                if let name = displayName, !name.isEmpty {
                    Text(verbatim: name).almaHeadingM()
                } else {
                    Text(L10nCabinet.guest).almaHeadingM()
                }
                if let email = session.account?.email, !email.isEmpty {
                    Text(verbatim: email).almaMeta()
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 6)

            // A guest is not signed out of anything — their chart and their
            // purchases are attached to the token, not to a name — so the offer
            // is the thing that keeps them, not a way to throw them away.
            if !session.isSignedIn {
                VStack(alignment: .leading, spacing: 12) {
                    Text(L10nCabinet.guestNote).almaMeta().almaReadingWidth()
                    Button {
                        router.push(.signIn)
                    } label: {
                        Text(L10nCabinet.signIn)
                    }
                    .buttonStyle(.alma(.outline, fills: false))
                }
                .padding(.top, 14)
            }
        }
    }

    // MARK: — the birth

    private var birthData: some View {
        CabinetSection(label: L10nCabinet.birthDataLabel) {
            SettingRow(
                label: L10nCabinet.settingsDate,
                value: AlmaDate.readable(civil: session.profile?.birthDate) ?? ""
            )
            SettingRow(label: L10nCabinet.settingsTime, value: birthTime)
            SettingRow(label: L10nCabinet.settingsPlace, value: session.profile?.placeLabel ?? "")
            SettingRow(label: L10nCabinet.settingsFullName, value: session.profile?.name ?? "")

            if session.hasBirthData, !session.birthTimeKnown {
                // Not knowing the minute is a first-class state, not an error —
                // and it is also the one fact that unlocks three of the eight,
                // so the way to fix it is offered rather than only reported.
                NeedMore(
                    message: L10nCabinet.needsBirthTime,
                    actionTitle: L10nCabinet.addBirthTime
                ) {
                    router.openJourney()
                }
            }
        }
    }

    private var birthTime: String {
        guard let profile = session.profile else { return "" }
        guard let time = profile.birthTime else { return String(localized: L10nCabinet.unknownTime) }
        return "\(time) · \(profile.timezone)"
    }

    // MARK: — language

    /// One language, one place to change it: the phone.
    ///
    /// **There were six chips here and they were the wrong control.** They set
    /// the language Alma *writes* in, which is a real setting and did reach the
    /// server — but a person who taps a language expects the screen in front of
    /// them to change, and the screen did not, because on iOS the interface
    /// language is the phone's and an app cannot change its own in-process. The
    /// owner tapped one, watched nothing happen, and said the only thing a
    /// reader can say: *"nothing changes"*. A control that is genuinely working
    /// and universally read as broken is worse than no control, because it
    /// teaches people that the settings in this app do not do anything.
    ///
    /// So there is one language now and the phone owns it. `start()` adopts the
    /// device's language on every launch and pushes it to the server when they
    /// disagree, so changing the phone changes both halves at once — the
    /// buttons and the readings — which is what somebody meant by "change the
    /// language" in the first place.
    ///
    /// The row below is a door rather than a switch, and it is the only kind of
    /// door iOS offers: `openSettingsURLString` opens this app's own page in
    /// Settings, where iOS lists the languages the bundle carries. The current
    /// one is printed here so the row still answers the question it raises —
    /// somebody who only wanted to *know* never has to leave.
    private var language: some View {
        CabinetSection(label: L10nCabinet.settingsLanguage) {
            Button {
                guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
                UIApplication.shared.open(url)
            } label: {
                HStack(spacing: 8) {
                    // Its own name, never translated: a picker that renames
                    // every language into the current one is useless to
                    // somebody trying to escape a language they cannot read.
                    Text(verbatim: session.locale.endonym)
                        .foregroundStyle(Color.almaBody)
                    Spacer(minLength: 12)
                    Text(L10nCabinet.interfaceLanguageAction)
                        .foregroundStyle(Color.almaGoldBright)
                    Image(systemName: "arrow.up.forward")
                        .font(AlmaFonts.ui(12))
                        .foregroundStyle(Color.almaGoldBright)
                }
                .font(AlmaFonts.ui(15))
                .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            Text(L10nCabinet.languageNote).almaMeta().almaReadingWidth().padding(.top, 6)
        }
    }

    // MARK: — data, deletion, documents

    @ViewBuilder
    private func dataAndLegal(_ model: AccountModel) -> some View {
        // Which letters Alma actually sends, which is not the same list on a
        // store as it is on the web.
        //
        // The web sentence promises three: a sign-in link, a receipt for
        // anything you buy, and a warning three days before a plan renews. In
        // this app Apple sends the second and the third — Apple took the money
        // and Apple holds the payment method — so shipping the web sentence
        // would be a written promise to warn somebody before a charge we neither
        // make nor can see coming. That is the class of untruth this codebase
        // has removed everywhere else, and under Guideline 3.1.2 it is also a
        // rejection.
        CabinetSection(label: L10nCabinet.settingsLetters) {
            Text(L10nCabinet.lettersNoteStore).almaMeta().almaReadingWidth()
        }

        CabinetSection(label: L10nCabinet.dataAndLegal) {
            ActionRow(label: L10nCabinet.settingsExport) {
                Task { await model.exportEverything(isGuest: !session.isSignedIn) }
            }
            exportState(model)

            ActionRow(label: L10nCabinet.settingsDelete, danger: true) {
                model.beginDelete(isGuest: !session.isSignedIn)
            }
            deleteState(model)

            ForEach(LegalDocument.allCases) { document in
                ActionRow(label: L10nCabinet.legal(document)) {
                    router.push(.legal(document))
                }
            }
        }
    }

    @ViewBuilder
    private func exportState(_ model: AccountModel) -> some View {
        switch model.export {
        case .idle:
            Text(L10nCabinet.exportNote).almaMeta().padding(.top, 8)
        case .working:
            Text(L10nCabinet.exporting).almaMeta().padding(.top, 8)
        case .ready(let url):
            VStack(alignment: .leading, spacing: 10) {
                Text(L10nCabinet.exportReady).almaMeta()
                // The file exists before this appears, which is why it is a
                // `ShareLink` and not a button that fetches on tap: a share
                // sheet that has to wait for a network call is a share sheet
                // that opens empty.
                ShareLink(item: url) {
                    Text(L10nCabinet.saveFile)
                }
                .buttonStyle(.alma(.outline, fills: false))
            }
            .padding(.vertical, 10)
        case .failed:
            Text(L10nCabinet.exportFailed).almaMeta().padding(.top, 8)
        case .needsAccount:
            needsAccount
        }
    }

    @ViewBuilder
    private func deleteState(_ model: AccountModel) -> some View {
        @Bindable var model = model

        switch model.delete {
        case .idle, .deleted:
            EmptyView()

        case .needsAccount:
            needsAccount

        case .confirming, .working, .mismatch, .failed:
            // An email for somebody signed in, the account id for a guest —
            // the string the backend compares against, and the only one a
            // guest actually has to type.
            let confirmation = session.account?.email ?? session.account?.userId
            VStack(alignment: .leading, spacing: 12) {
                Text(L10nCabinet.deleteWarning).almaMeta().almaReadingWidth()

                if session.account?.email == nil, let id = session.account?.userId {
                    // A guest was being asked to "type your email address" —
                    // an instruction they cannot follow, next to a bare code
                    // with no explanation. Same mechanism, said honestly.
                    Text(L10nCabinet.deleteGuestNote).almaMeta().almaReadingWidth()
                    Text(id)
                        .font(AlmaFonts.ui(14).monospaced())
                        .foregroundStyle(Color.almaGoldBright)
                        .textSelection(.enabled)
                        .accessibilityLabel(Text(L10nCabinet.settingsDeleteConfirm))
                }

                TextField(
                    "",
                    text: $model.typedConfirmation,
                    prompt: Text(
                        session.account?.email == nil
                            ? L10nCabinet.deleteConfirmGuest
                            : L10nCabinet.settingsDeleteConfirm
                    )
                    .foregroundStyle(Color.almaMuted3)
                )
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .keyboardType(session.account?.email == nil ? .default : .emailAddress)
                .font(.almaBodyFont)
                .foregroundStyle(Color.almaInkLight)
                .padding(.horizontal, 16)
                .frame(height: AlmaMetrics.fieldHeight)
                .background(Capsule().fill(Color.almaVeil))
                .accessibilityLabel(Text(L10nCabinet.settingsDeleteConfirm))

                HStack(spacing: 14) {
                    Button {
                        Task {
                            await model.confirmDelete(account: confirmation) {
                                await session.start()
                            }
                        }
                    } label: {
                        Text(model.delete == .working ? L10nCabinet.deleting : L10nCabinet.deleteForever)
                    }
                    .buttonStyle(.almaDanger)
                    .disabled(
                        !model.typedConfirmationMatches(confirmation) || model.delete == .working
                    )

                    Button {
                        model.abandonDelete()
                    } label: {
                        Text(L10nCabinet.keepAccount)
                            .font(AlmaFonts.ui(14.5))
                            .foregroundStyle(Color.almaMuted2)
                    }
                    .buttonStyle(.plain)
                }

                if model.delete == .mismatch {
                    Text(L10nCabinet.deleteMismatch)
                        .almaMeta()
                        .foregroundStyle(Color.almaDisagree)
                } else if model.delete == .failed {
                    Text(L10nCabinet.deleteFailed)
                        .almaMeta()
                        .foregroundStyle(Color.almaDisagree)
                }
            }
            .padding(.vertical, 14)
        }
    }

    private var needsAccount: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(L10nCabinet.needsAccount).almaMeta().almaReadingWidth()
            Button {
                router.push(.signIn)
            } label: {
                Text(L10nCabinet.signIn)
            }
            .buttonStyle(.alma(.outline, fills: false))
        }
        .padding(.vertical, 14)
    }

    // MARK: — the fine print

    private var finePrint: some View {
        VStack(alignment: .leading, spacing: 10) {
            FadedRule()
            // Apple, and not Pazl, is the merchant of record for anything
            // bought inside the app — which is what a card issuer reads during
            // a dispute and what the refunds page has to name.
            Text(L10nCabinet.merchantLine("Apple")).almaMeta()
            Text(verbatim: "Pazl LLC · 16+").almaMeta()
            Text(L10nCabinet.disclaimer).almaMeta().almaReadingWidth()
        }
        .padding(.top, AlmaMetrics.gapSection)
    }
}

// MARK: — the plan

/// What this account holds, what it is called, and how to stop paying for it.
private struct PlanSection: View {

    let model: AccountModel
    /// Whether there is an address to warn before a renewal. `renewals.due`
    /// skips an account with none, and promising the warning loudest to the
    /// person least likely to receive it is how somebody is charged a year
    /// later having read that this could not happen.
    let hasAddress: Bool
    let manageAtStore: () -> Void

    var body: some View {
        CabinetSection(label: L10nCabinet.settingsPlan) {
            switch model.plan {
            case .loading:
                AlmaLoading(message: L10n.stateLoadingShort).frame(height: 120)

            case .failed(let error):
                AlmaFailure(error: error) { await model.loadPlan() }.frame(minHeight: 120)

            case .loaded(let plan):
                if let subscription = plan.subscription {
                    subscribed(plan, subscription)
                } else {
                    unsubscribed(plan)
                }
            }
        }
    }

    @ViewBuilder
    private func subscribed(_ plan: AccountModel.Plan, _ row: EntitlementRow) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(name(ofKind: row.kind, in: plan)).almaHeadingM()

            // "Renews" only while it does. Once `renews_at` is gone the plan is
            // still open and still paid for, and saying it renews would tell
            // somebody who has just cancelled that the cancellation did not
            // take — which reads as a reason to call the bank.
            //
            // **Which sentence, and the branch that was wrong.** This used to
            // choose on `hasAddress` — whether we hold an email — and print "we
            // email you 3 days before". For a plan bought in this app that is
            // false whatever address we hold: Apple charges it, Apple receipts
            // it and Apple warns about it. The question is who sold the plan,
            // which is what `source` now answers, and the address only decides
            // between the two web sentences.
            if let renews = AlmaDate.readable(instant: row.renewsAt) {
                Text(renewalLine(renews, row: row)).almaMeta()
            } else if let until = AlmaDate.readable(instant: row.expiresAt) {
                Text(L10nCabinet.runsUntil(until)).almaMeta()
            }

            Button(action: manageAtStore) {
                Text(L10nCabinet.manageInStore)
            }
            .buttonStyle(.almaOutline)
            .padding(.top, 6)

            // The two-tap server cancel is offered only for a plan we can
            // actually stop. On a store plan `/v1/billing/subscription/cancel`
            // answers 409 and writes nothing — correctly — so a button that
            // leads there is a button whose only outcome is a sentence pointing
            // back at the link directly above it.
            if !row.boughtInAStore {
                cancelBlock(row)
            } else {
                Text(L10nCabinet.managedByApple).almaMeta().almaReadingWidth().padding(.top, 2)
            }
        }
        .padding(.vertical, 6)
    }

    /// Three true sentences, one per seller.
    ///
    /// A store plan is Apple's to charge, receipt and warn about; a web plan is
    /// ours, and there the address decides whether the warning can reach
    /// anybody. A grant with no `source` — an older backend, or one made by hand
    /// — falls into the web branch, which is the conservative direction: it
    /// promises the *less* automatic thing.
    private func renewalLine(_ date: String, row: EntitlementRow) -> LocalizedStringResource {
        if row.boughtInAStore { return L10nCabinet.renewsAtStore(date) }
        return hasAddress ? L10nCabinet.renews(date) : L10nCabinet.renewsNoEmail(date)
    }

    @ViewBuilder
    private func cancelBlock(_ row: EntitlementRow) -> some View {
        switch model.cancel {
        case .idle:
            // Only while there is a next charge to stop. A plan that has
            // already been cancelled has nothing behind this button.
            if row.renewsAt != nil {
                Button {
                    model.beginCancel()
                } label: {
                    Text(L10nCabinet.planCancel)
                }
                .buttonStyle(.almaDanger)
                .padding(.top, 4)
            }

        case .confirming, .working:
            VStack(alignment: .leading, spacing: 12) {
                Text(L10nCabinet.planCancelWhat).almaMeta().almaReadingWidth()
                HStack(spacing: 14) {
                    Button {
                        Task { await model.confirmCancel() }
                    } label: {
                        Text(model.cancel == .working ? L10nCabinet.planCancelling : L10nCabinet.planCancel)
                    }
                    .buttonStyle(.almaDanger)
                    .disabled(model.cancel == .working)

                    Button {
                        model.abandonCancel()
                    } label: {
                        Text(L10nCabinet.planKeep)
                            .font(AlmaFonts.ui(14.5))
                            .foregroundStyle(Color.almaMuted2)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.top, 6)

        case .done(let outcome):
            VStack(alignment: .leading, spacing: 10) {
                switch outcome {
                case .cancelled(let until):
                    Text(until.map { L10nCabinet.cancelled(until: $0) } ?? L10nCabinet.planCancelledNoDate)
                        .almaMeta()
                case .atStore:
                    Text(L10nCabinet.managedByApple).almaMeta().almaReadingWidth()
                    Button(action: manageAtStore) {
                        Text(L10nCabinet.manageInStore)
                    }
                    .buttonStyle(.alma(.outline, fills: false))
                case .failed:
                    Text(L10nCabinet.planCancelFailed).almaMeta().foregroundStyle(Color.almaDisagree)
                }
            }
            .padding(.top, 6)
        }
    }

    @ViewBuilder
    private func unsubscribed(_ plan: AccountModel.Plan) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(plan.owned.isEmpty ? L10nCabinet.planFree : L10nCabinet.planOwned).almaHeadingM()
            Text(plan.owned.isEmpty ? L10nCabinet.planFreeNote : L10nCabinet.planOwnedNote)
                .almaMeta()
                .almaReadingWidth()

            if let lapsed = plan.lapsed, let ended = AlmaDate.readable(instant: lapsed.expiresAt) {
                Text(L10nCabinet.planEnded(ended)).almaMeta()
            }
        }
        .padding(.vertical, 6)

        // Each door, and when it was bought. The dates are the receipt this
        // screen can show without asking the store for one.
        ForEach(plan.owned, id: \.grantedAt) { row in
            FactRow(
                label: name(ofSystem: row.system, in: plan),
                value: AlmaDate.readable(instant: row.grantedAt) ?? ""
            )
        }
    }

    /// What to call the plan somebody is actually on, in their own language.
    ///
    /// Ours first, because this is the screen a person opens when they are
    /// deciding whether to keep paying. The catalogue's English name is the
    /// fallback rather than a hardcoded label, so a rung added to the ladder is
    /// named rather than mislabelled as one of the two we happen to know today.
    private func name(ofKind kind: String, in plan: AccountModel.Plan) -> LocalizedStringResource {
        switch kind {
        case "annual": L10nCabinet.planAnnual
        case "monthly": L10nCabinet.settingsMonthly
        default:
            plan.name(ofKind: kind).map { LocalizedStringResource(stringLiteral: $0) }
                ?? L10nCabinet.settingsPlan
        }
    }

    private func name(ofSystem system: String, in plan: AccountModel.Plan) -> String {
        guard let slug = SystemSlug(rawValue: system) else {
            // "*" — the archive — and anything a later backend adds.
            return plan.catalogue?.items.first { $0.system == system }?.name ?? system
        }
        return String(localized: slug.displayName)
    }
}

#Preview {
    SettingsScreen()
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
        .environment(PushService())
        .environment(DailyModel.preview())
}
