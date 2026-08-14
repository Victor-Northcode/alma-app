# The App Store side of Alma

Everything the paywall needs that is not code.

## The products to create in App Store Connect

The id is the catalogue key prefixed with `alma.`, hyphens replaced by
underscores. That rule is stated twice — `LadderKey.storeProductID` here and
`StoreProvider.store_product_id` in `backend/alma/billing/provider.py` — and a
product id that does not follow it is a row that silently disappears from the
paywall.

| product id | type | US price | what it grants |
|---|---|---|---|
| `alma.natal` | Non-consumable | $5.99 | all 16 natal chapters |
| `alma.numerology` | Non-consumable | $5.99 | all 5 numerology chapters |
| `alma.birth_card` | Non-consumable | $5.99 | all 3 birth-card chapters |
| `alma.transits` | Non-consumable | $5.99 | all 3 transit chapters |
| `alma.solar_return` | Non-consumable | $5.99 | all 3 solar-return chapters |
| `alma.compatibility` | Non-consumable | $5.99 | all 4 compatibility chapters |
| `alma.astrocartography` | Non-consumable | $5.99 | all 3 astrocartography chapters |
| `alma.synthesis` | Non-consumable | $5.99 | all 4 cross-synthesis chapters |
| `alma.archive` | Non-consumable | $38.99 | all 41 chapters |
| `alma.archive_upgrade` | Non-consumable | $33.00 | all 41, for somebody who owns a door |
| `alma.monthly` | Auto-renewable, 1 month | $9.99 | the living layer + 30 questions a month |
| `alma.annual` | Auto-renewable, 1 year | $78.99 | everything, for a year |

`alma.archive_bump` is **not** created. It exists only as an upsell inside
another checkout and there is no such thing when the store owns the sheet; the
backend still prices it and still refuses to put it on the shelf.

The two subscriptions belong in **one subscription group**, so that moving
between them is an upgrade rather than two parallel plans.

Both subscriptions and both archive rows must have their non-US prices checked
against the ladder in `backend/alma/billing/catalogue.py` (`REGIONAL_CENTS`).
Nothing in code can verify that the tier chosen in the console matches the price
the catalogue publishes — the app shows Apple's number, so the console is the
truth, and the catalogue is what the web landing quotes.

## Testing locally

`Alma.storekit` in this folder describes all twelve products with the US prices
above. Attach it to the scheme:

**Product → Scheme → Edit Scheme → Run → Options → StoreKit Configuration →
`Alma.storekit`.**

It is deliberately *not* attached to a shared scheme in the repository, for two
reasons: the project has no shared scheme at all (Xcode autocreates one, which is
what `xcodebuild -scheme Alma` uses), and adding one changes how every other
agent's build resolves while three of us are working in this project at once.

The configuration only applies to launches **from Xcode**. `xcrun simctl launch`
ignores it, so a command-line run of the app sees no products and the paywall
shows "The App Store is not answering" — which is the correct, honest state for a
build that cannot reach a store, and is worth seeing once.

Sandbox testing against real App Store Connect products needs a Sandbox Apple ID
(Users and Access → Sandbox) signed in under Settings → Developer → Sandbox
Apple Account on the device.

## What the server needs

`ALMA_BILLING_PROVIDER=appstore`, plus:

- `APPLE_BUNDLE_ID=ai.pazl.alma` — checked against the `bundleId` inside every
  signed transaction, because a valid Apple signature only proves *Apple* signed
  it and Apple signs a transaction for every app on the store.
- `ALMA_APPLE_ACCEPT_SANDBOX` — on by default. App Review runs the production
  build against sandbox StoreKit, so refusing sandbox transactions fails review;
  accepting them means anybody who can create a sandbox tester for this bundle
  can mint verifiable purchases. The environment is recorded on every event.
- App Store Server Notifications V2 pointed at `/v1/billing/webhook`.

## The review argument

Guideline 3.1.2 wants the auto-renewal disclosure adjacent to the payment action
and functional links to the terms and the privacy policy from the paywall itself.
Both are in `PaywallView`: `PaywallL10n.autoRenewTerms` sits directly above the
gold button whenever a subscription row is selected, and the three legal links
open `LegalScreen` in the binary rather than a web page that can be down when a
reviewer opens it.

Restore is required for an app that sells non-consumables. `RestorePurchasesButton`
is on the paywall already; **it still has to be added to `SettingsScreen`** — that
screen has its own manage-in-the-App-Store row and its own handling of the 409
`cancel_at_store` answer, but no restore, and a reviewer looks for one outside a
paywall. One line in the settings column:

```swift
RestorePurchasesButton()
```
