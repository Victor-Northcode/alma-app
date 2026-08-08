import SwiftUI

/// The ladder, as a screen.
///
/// Reached through `Route.offer(system:)` from three places, and it is the same
/// screen in all three because the decision is the same one: from a locked
/// chapter, where `system` is the door that chapter belongs to; from Today's
/// offer, where `system` is the one the quiz chose; and from settings, where
/// `system` is `nil` and the whole ladder is on the shelf.
///
/// Everything that is actually about money lives in `PaywallView` and
/// `AlmaStore`. What this file adds is the two things a *screen* owns: the title
/// at the top, and what happens after a purchase — which is to leave, because a
/// paywall that stays up after it has been paid is a paywall that looks like it
/// failed.
///
/// **Prices come from StoreKit, never from the catalogue's `display`.** Apple is
/// the merchant of record, its localised price string is what the buyer is
/// charged, and App Review rejects a price drawn from anywhere else.
/// `AlmaBillingAPI.shelf()` is still what says *which* keys are on the shelf for
/// this account and what each grants — including the archive being substituted
/// by the upgrade for somebody who already bought a door.
///
/// After a purchase: the transaction is verified server-side and
/// `session.refreshEntitlements()` runs, both inside `AlmaStore`. The client
/// never decides what somebody owns.
@MainActor
struct OfferScreen: View {

    /// The door being offered, or `nil` for the whole ladder.
    let system: SystemSlug?

    @Environment(AlmaSessionModel.self) private var session
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScreenScaffold(eyebrow: PaywallL10n.label, title: title, seed: 0x0FFE_2026) {
            PaywallView(intent: intent, onPurchased: { dismiss() }, onDeclined: { dismiss() })
        }
    }

    /// The door somebody reached for, unless they already own it.
    ///
    /// Somebody who owns natal and taps through to the offer from a natal
    /// chapter should not be sold natal again — the ladder above it is the
    /// honest answer, and `Storefront.offers` would have dropped the row anyway,
    /// leaving a screen titled with a system it was not selling.
    private var intent: PaywallIntent {
        guard let system, !session.unlocked(system) else { return .everything }
        return .door(system)
    }

    private var title: LocalizedStringResource {
        switch intent {
        case .door(let system): PaywallL10n.systemName(system)
        case .everything: PaywallL10n.everythingTitle
        }
    }
}

#Preview("Offer · one door") {
    NavigationStack { OfferScreen(system: .natal) }
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}

#Preview("Offer · the whole ladder") {
    NavigationStack { OfferScreen(system: nil) }
        .environment(AlmaSessionModel.preview())
        .environment(AppRouter())
}
