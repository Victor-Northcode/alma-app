import AuthenticationServices
import SwiftUI

/// Sign in — which **attaches** an identity to this account rather than
/// replacing it.
///
/// Somebody who read three chapters as a guest and then signs in keeps the three
/// chapters, because the backend merges onto the token it was given. So the
/// client must not clear the token first, and `AlmaSessionModel.signInWithApple`
/// is the only correct way in. Nothing on this screen touches `TokenStoring`.
///
/// **Why this screen matters more on a phone than on the web.** A purchase made
/// through the App Store belongs to whichever Alma account claims it first, and a
/// fresh install is a fresh guest account. Somebody who reinstalls and taps
/// restore is told, correctly and unkindly, that their purchases belong to
/// another account. Signing in *before* restoring is what prevents that, and it
/// is why the copy here leads with durability rather than with features.
struct SignInScreen: View {

    @Environment(AlmaSessionModel.self) private var session
    @Environment(AppRouter.self) private var router
    @Environment(\.dismiss) private var dismiss

    @State private var model: SignInModel?

    var body: some View {
        ScreenScaffold(
            eyebrow: ScreenL10n.signInEyebrow,
            title: ScreenL10n.signInTitle,
            seed: 0x5349_474E
        ) {
            if session.isSignedIn {
                signedIn
            } else if let model {
                offer(model)
            }
        }
        .task {
            model = model ?? SignInModel(session: session)
        }
    }

    // MARK: — already done

    private var signedIn: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(ScreenL10n.signedInAlready).almaVoice().almaReadingWidth()
            if let email = session.account?.email, !email.isEmpty {
                Text(verbatim: email).almaMeta()
            }
            Button { dismiss() } label: { Text(ScreenL10n.done) }
                .buttonStyle(.alma(.outline, fills: false))
        }
        .padding(.top, 8)
    }

    // MARK: — the offer

    @ViewBuilder
    private func offer(_ model: SignInModel) -> some View {
        Text(ScreenL10n.signInLead).almaVoice().almaReadingWidth()

        VStack(alignment: .leading, spacing: 10) {
            ForEach(Array(ScreenL10n.signInReasons.enumerated()), id: \.offset) { _, line in
                HStack(alignment: .firstTextBaseline, spacing: 10) {
                    Text(verbatim: "·").almaPositions()
                    Text(line).almaMeta()
                }
            }
        }
        .almaReadingWidth()
        .padding(.top, 4)

        // Apple's own button, drawn by Apple. It is deliberately not restyled
        // into the gold ramp: Guideline 4.8 and the Human Interface Guidelines
        // both require this control to look like itself, and a gold "Sign in
        // with Apple" is a rejection over a colour.
        SignInWithAppleButton(.signIn) { request in
            request.requestedScopes = [.fullName, .email]
        } onCompletion: { result in
            Task { await model.finishApple(result) }
        }
        .signInWithAppleButtonStyle(.white)
        .frame(height: AlmaMetrics.buttonHeight)
        .clipShape(Capsule())
        .padding(.top, AlmaMetrics.gapLarge)
        .disabled(model.working)

        // Google, only when an OAuth client is configured (`GIDClientID` in
        // Info.plist). A sign-in button that opens an error would be worse
        // than no button, so absence of configuration removes it entirely.
        if GoogleAuth.isConfigured {
            Button {
                Task { await model.signInWithGoogle() }
            } label: {
                Text(ScreenL10n.continueWithGoogle)
            }
            .buttonStyle(.alma(.outline, fills: false))
            .padding(.top, 10)
            .disabled(model.working)
        }

        FadedRule().padding(.vertical, 6)

        emailBlock(model)

        if let notice = model.notice {
            Text(notice.text)
                .font(.almaMetaFont)
                .foregroundStyle(notice.bad ? Color.almaDisagree : Color.almaAgree)
                .almaReadingWidth()
                .padding(.top, 12)
        }

        Text(ScreenL10n.signInPrivacy)
            .almaMeta()
            .almaReadingWidth()
            .padding(.top, AlmaMetrics.gapLarge)

        HStack(spacing: 10) {
            Button { router.push(.legal(.terms)) } label: {
                Text(L10nCabinet.legal(.terms))
                    .font(.almaMetaFont)
                    .foregroundStyle(Color.almaGold)
                    .underline()
            }
            .buttonStyle(.plain)
            Text(verbatim: "·").almaMeta()
            Button { router.push(.legal(.privacy)) } label: {
                Text(L10nCabinet.legal(.privacy))
                    .font(.almaMetaFont)
                    .foregroundStyle(Color.almaGold)
                    .underline()
            }
            .buttonStyle(.plain)
        }
        .padding(.top, 8)
    }

    /// The passwordless link. No password field anywhere in this product: the
    /// inbox is the account.
    @ViewBuilder
    private func emailBlock(_ model: SignInModel) -> some View {
        @Bindable var model = model

        VStack(alignment: .leading, spacing: 14) {
            Text(ScreenL10n.orByEmail).almaOverline()

            TextField(
                "",
                text: $model.email,
                prompt: Text(ScreenL10n.emailPlaceholder).foregroundStyle(Color.almaMuted3)
            )
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .keyboardType(.emailAddress)
            .textContentType(.emailAddress)
            .submitLabel(.send)
            .onSubmit { Task { await model.sendLink() } }
            .font(.almaBodyFont)
            .foregroundStyle(Color.almaInkLight)
            .tint(Color.almaGoldBright)
            .padding(.horizontal, 20)
            .frame(minHeight: AlmaMetrics.fieldHeight)
            .background(Capsule().fill(Color.almaVeil))
            .overlay(Capsule().stroke(Color.almaGold.opacity(0.35), lineWidth: 1))
            .accessibilityLabel(Text(ScreenL10n.emailPlaceholder))

            Button {
                Task { await model.sendLink() }
            } label: {
                Text(model.working ? ScreenL10n.sending : ScreenL10n.sendLink)
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
            }
            .buttonStyle(.almaGold)
            .disabled(!model.emailLooksReal || model.working)
        }
        .padding(.top, 6)

        // A development affordance, and it cannot reach a release build: the
        // backend only returns `debug_token` when `ALMA_ENV` is not production,
        // and this branch is compiled out anyway. It exists so that sign-in can
        // actually be exercised on a simulator with no mail server, which is the
        // only way anybody was going to find out whether the merge works.
        #if DEBUG
        if let token = model.debugToken {
            Button {
                Task { await model.consume(token) }
            } label: {
                Text(verbatim: "DEBUG · open the link")
            }
            .buttonStyle(.alma(.veil, fills: false))
            .padding(.top, 10)
        }
        #endif
    }
}

// MARK: — the state behind it

/// Two ways in, one outcome: an identity attached to the account this device
/// already has.
@MainActor
@Observable
final class SignInModel {

    var email: String = ""
    private(set) var working = false
    private(set) var notice: Notice?
    private(set) var debugToken: String?

    private let session: AlmaSessionModel

    init(session: AlmaSessionModel) {
        self.session = session
    }

    struct Notice: Sendable, Equatable {
        let text: String
        let bad: Bool
    }

    /// Good enough to send to, and no stricter. A regular expression that
    /// refuses a valid address is worse than one that lets a typo through — the
    /// typo produces a letter that does not arrive, which the person can see;
    /// the refusal produces a button that will not work and no explanation.
    var emailLooksReal: Bool {
        let trimmed = email.trimmingCharacters(in: .whitespaces)
        guard let at = trimmed.firstIndex(of: "@"), at != trimmed.startIndex else { return false }
        let domain = trimmed[trimmed.index(after: at)...]
        return domain.contains(".") && !domain.hasSuffix(".") && !domain.contains("@")
    }

    // MARK: — Apple

    func finishApple(_ result: Result<ASAuthorization, any Error>) async {
        switch result {
        case .failure(let error):
            // A cancellation is not a failure and must not be reported as one.
            // It is the single most common outcome of this button.
            if (error as? ASAuthorizationError)?.code == .canceled { return }
            notice = Notice(text: String(localized: ScreenL10n.signInFailed), bad: true)

        case .success(let authorization):
            guard
                let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                let data = credential.identityToken,
                let token = String(data: data, encoding: .utf8)
            else {
                notice = Notice(text: String(localized: ScreenL10n.signInFailed), bad: true)
                return
            }

            // Apple hands over the name exactly once, on the very first
            // authorisation, and never again. Sent when it is there and left
            // alone when it is not — an empty string written over a name the
            // account already has is how somebody becomes anonymous by signing
            // in a second time.
            let name = [credential.fullName?.givenName, credential.fullName?.familyName]
                .compactMap { $0 }
                .joined(separator: " ")

            working = true
            defer { working = false }
            do {
                try await session.signInWithApple(
                    identityToken: token, fullName: name.isEmpty ? nil : name
                )
                notice = Notice(text: String(localized: ScreenL10n.signedIn), bad: false)
            } catch {
                notice = Notice(text: error.displayLine, bad: true)
            }
        }
    }

    // MARK: — Google

    func signInWithGoogle() async {
        working = true
        defer { working = false }
        do {
            let token = try await GoogleAuth.idToken()
            try await session.signInWithGoogle(credential: token)
            notice = Notice(text: String(localized: ScreenL10n.signedIn), bad: false)
        } catch GoogleAuth.Failure.cancelled {
            // The most common outcome of the button, and not a failure.
        } catch {
            notice = Notice(text: String(localized: ScreenL10n.signInFailed), bad: true)
        }
    }

    // MARK: — the link

    func sendLink() async {
        guard emailLooksReal, !working else { return }
        working = true
        defer { working = false }
        do {
            let sent = try await session.client.requestMagicLink(
                email: email.trimmingCharacters(in: .whitespaces), locale: session.locale
            )
            debugToken = sent.debugToken
            notice = Notice(text: String(localized: ScreenL10n.linkSent), bad: false)
        } catch {
            notice = Notice(text: error.displayLine, bad: true)
        }
    }

    func consume(_ token: String) async {
        working = true
        defer { working = false }
        do {
            try await session.consumeMagicLink(token: token)
            debugToken = nil
            notice = Notice(text: String(localized: ScreenL10n.signedIn), bad: false)
        } catch {
            notice = Notice(text: error.displayLine, bad: true)
        }
    }
}

private extension AlmaError {
    /// The server's own already-translated sentence when there is one, and our
    /// generic line when there is not.
    var displayLine: String {
        if let detail = serverMessage, !detail.isEmpty { return detail }
        return String(localized: displayText)
    }
}

#Preview {
    NavigationStack { SignInScreen() }
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}
