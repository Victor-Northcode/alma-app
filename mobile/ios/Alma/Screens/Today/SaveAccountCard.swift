import SwiftUI

/// The one invitation to attach an identity to the account that already
/// exists.
///
/// A guest's chart lives in a keychain token, and a lost phone is a lost
/// chart plus every purchase on it. The invitation appears **once a person
/// has something to lose** — a chart, from the second launch — and it can be
/// put away for good with one tap, because a card that keeps coming back is
/// nagging, and nagging sells nothing.
///
/// The launch counting and the dismissal both live in `UserDefaults`: this is
/// a preference about being asked, not account state, and it should reset
/// with a reinstall — a fresh install genuinely is a fresh chance to ask.
struct SaveAccountCard: View {

    let onSave: () -> Void
    let onDismiss: () -> Void

    @State private var dismissed = false

    private static let dismissedKey = "saveAccountDismissed"
    private static let launchesKey = "saveAccountLaunches"

    /// Counted once per cold launch, from the app delegate's side of life —
    /// calling it from the card itself would count screen visits instead.
    static func noteLaunch() {
        let defaults = UserDefaults.standard
        defaults.set(defaults.integer(forKey: launchesKey) + 1, forKey: launchesKey)
    }

    static func shouldShow(signedIn: Bool, hasBirthData: Bool) -> Bool {
        let defaults = UserDefaults.standard
        return !signedIn
            && hasBirthData
            && !defaults.bool(forKey: dismissedKey)
            && defaults.integer(forKey: launchesKey) >= 2
    }

    var body: some View {
        if !dismissed {
            VStack(alignment: .leading, spacing: 10) {
                Text(ScreenL10n.saveAccountTitle).almaHeadingM()
                Text(ScreenL10n.saveAccountBody).almaMeta().almaReadingWidth()
                HStack(spacing: 18) {
                    Button(action: onSave) {
                        Text(ScreenL10n.saveAccountCta)
                    }
                    .buttonStyle(.alma(.veil, fills: false))

                    Button {
                        UserDefaults.standard.set(true, forKey: Self.dismissedKey)
                        withAnimation(AlmaMotion.ui) { dismissed = true }
                        onDismiss()
                    } label: {
                        Text(ScreenL10n.saveAccountLater).almaMeta()
                    }
                    .buttonStyle(.plain)
                }
                .padding(.top, 2)
            }
            .padding(.vertical, 14)
        }
    }
}
