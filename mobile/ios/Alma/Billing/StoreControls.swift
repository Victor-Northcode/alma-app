import StoreKit
import SwiftUI
import UIKit

/// The two store controls that belong outside the paywall, as separate pieces so
/// that whoever owns a screen takes only the one they are missing.
///
/// `SettingsScreen` already draws its own "manage in the App Store" row and
/// already handles the 409 `cancel_at_store` answer from
/// `POST /v1/billing/subscription/cancel` — which is the right shape, because
/// neither Apple nor Google lets a server stop a subscription that belongs to an
/// Apple ID, and a local flag saying "cancelled" does not stop a card being
/// charged. What it does not have is **restore**, and Apple rejects an app that
/// sells non-consumables without one that is reachable outside a paywall.
///
/// So: drop `RestorePurchasesButton()` into the settings column. Take
/// `ManageSubscriptionButton` only if the in-app sheet is wanted in place of the
/// link — see its own note.

/// Restore purchases, as a control anything can place.
///
/// The work is `AlmaStore.restore()`: `AppStore.sync()` to force a fresh
/// authentication against the Apple ID, then every entitlement Apple reports is
/// re-verified server-side. Nothing is granted locally, and a transaction that
/// another Alma account already claimed answers with the sentence that says so
/// rather than with silence.
@MainActor
struct RestorePurchasesButton: View {

    /// Whether to show the outcome underneath. The paywall does; a dense
    /// settings list may prefer the button alone.
    var showsOutcome = true

    @Environment(AlmaSessionModel.self) private var session

    private var store: AlmaStore { AlmaStore.shared }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Button {
                Task { await store.restore() }
            } label: {
                Text(store.restoring ? PaywallL10n.restoring : PaywallL10n.restore)
            }
            .buttonStyle(.almaVeil)
            .disabled(store.restoring || store.busy != nil)

            if showsOutcome, let notice = store.notice {
                Text(notice.text)
                    .font(.almaMetaFont)
                    .foregroundStyle(notice.tone.colour)
                    .almaReadingWidth()
            }
        }
        .task { store.attach(session) }
    }
}

/// Opens Apple's subscription management.
///
/// It tries the in-app sheet first — `AppStore.showManageSubscriptions(in:)`
/// presents Apple's own screen without leaving the app, which is materially
/// better than being thrown into Settings and losing your place — and falls back
/// to the URL. The fallback is not decoration: the sheet throws when there is no
/// active subscription and on a device signed out of the App Store, and the link
/// still works in both.
@MainActor
struct ManageSubscriptionButton: View {

    /// Apple's own URL, or whatever `manage_url` the backend published.
    var url: URL = Storefront.appleSubscriptionsURL

    @Environment(\.openURL) private var openURL

    var body: some View {
        Button {
            Task { await open() }
        } label: {
            Text(PaywallL10n.manage)
        }
        .buttonStyle(.almaOutline)
    }

    private func open() async {
        guard let scene = UIApplication.shared.connectedScenes
            .compactMap({ $0 as? UIWindowScene })
            .first(where: { $0.activationState == .foregroundActive })
        else {
            openURL(url)
            return
        }
        do {
            try await AppStore.showManageSubscriptions(in: scene)
        } catch {
            openURL(url)
        }
    }
}

extension Storefront {
    /// Apple's documented subscription screen. Used when the backend has not
    /// published a `manage_url` — which is the state of any deployment whose
    /// `ALMA_BILLING_PROVIDER` still names a card processor, and of one backend
    /// serving an iOS app and an Android app from one configuration.
    static let appleSubscriptionsURL = URL(string: "https://apps.apple.com/account/subscriptions")!
}

#Preview("Store controls") {
    VStack(alignment: .leading, spacing: 22) {
        ManageSubscriptionButton()
        Text(PaywallL10n.manageNote).almaMeta()
        RestorePurchasesButton()
    }
    .almaPadding()
    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    .nightSky()
    .environment(AlmaSessionModel.preview())
}
