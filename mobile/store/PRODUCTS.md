# Every purchasable thing, mapped to both stores

Written 7 August 2026. Source of truth for every number is
`/Users/anatoliymikhaylow/alma_project1/backend/alma/billing/catalogue.py`; where this file
proposes a number that is *not* in there yet, it says so and says what has to change.

Nothing here has been typed into either console. That matters more than usual, because three
of the decisions below are **irreversible once a product is saved**: the product identifier,
the product type, and — on Play — the base plan id. Apple: *"Once a product ID is assigned to
an In-App Purchase, it can't be reused for another In-App Purchase within the same app, even
if you delete the original In-App Purchase with that ID"*, and *"The product ID isn't editable
after you save the In-App Purchase."*
(<https://developer.apple.com/help/app-store-connect/reference/in-app-purchases-and-subscriptions/in-app-purchase-information/>)
Play: product IDs *"can't be changed or reused after they've been created"*, and a base plan id
*"can't be changed or reused after the base plan has been activated"*.
(<https://support.google.com/googleplay/android-developer/answer/1153481> ·
<https://support.google.com/googleplay/android-developer/answer/140504>)

So this is the one moment where all of it is free.

---

## 0. Three things the brief assumed that turned out not to be true

**There are no price tiers any more, on either store.** Apple retired them in 2023. What you
do now is pick a price in a base storefront and Apple derives the other 174: *"You can set a
price for the country or region you're familiar with as the basis for automatically generating
prices across the other 174 storefronts and 43 currencies"*, choosing from *"up to 800 price
points by default"*, and *"Alternatively, you can choose to manually manage certain storefronts
or you can manually manage them all."*
(<https://developer.apple.com/help/app-store-connect/manage-in-app-purchases/set-a-price-for-an-in-app-purchase/>)
Play never had tiers: you type a price per country, in micro-units. So §4 below is a table of
**exact amounts to type**, not tier numbers, and it is the same 13 currencies `REGIONAL_CENTS`
already holds.

**Apple's character limits are tighter than STORE-REQUIREMENTS.md says.** That file quotes the
product-page article — *"names are limited to 35 characters and descriptions are limited to 55
characters"*. The App Store Connect reference, which is the limit the text box actually
enforces, says the display name is *"at least two characters"* and *"no more than 30
characters"* and the description *"no more than 45 characters"*. Every string in §3 is written
to **30 / 45**, which fits under both. Play is roomier — title up to 55, description up to 200
— and takes the same copy without change.

**Play's manual per-country prices are tax-inclusive.** Play's default (auto-conversion from a
base price) *adds* tax on top; but *"if you don't use auto-converted pricing, prices must
include tax."* We are setting every country by hand, so the numbers in `REGIONAL_CENTS` go in
as-is and are what the buyer pays. Apple's derived prices *"account for foreign exchange rates
and certain taxes"* and are likewise the customer-facing amount. The tax arithmetic that
produced `REGIONAL_CENTS` therefore survives the move intact.
(<https://support.google.com/googleplay/android-developer/answer/6334373>)

---

## 1. The shape, in one table

| Catalogue slug | Type | Apple product id | Play product id | On the shelf? |
|---|---|---|---|---|
| `natal` | Non-consumable | `alma.natal` | `alma.natal` | yes |
| `numerology` | Non-consumable | `alma.numerology` | `alma.numerology` | yes |
| `birth-card` | Non-consumable | `alma.birth_card` | `alma.birth_card` | yes |
| `transits` | Non-consumable | `alma.transits` | `alma.transits` | yes |
| `solar-return` | Non-consumable | `alma.solar_return` | `alma.solar_return` | yes |
| `compatibility` | Non-consumable | `alma.compatibility` | `alma.compatibility` | yes |
| `astrocartography` | Non-consumable | `alma.astrocartography` | `alma.astrocartography` | yes |
| `synthesis` | Non-consumable | `alma.synthesis` | `alma.synthesis` | yes |
| `archive` | Non-consumable | `alma.archive` | `alma.archive` | yes |
| `archive-upgrade` | Non-consumable | `alma.archive_upgrade` | `alma.archive_upgrade` | no — after-door |
| `archive-bump` | **none** | **do not create** | **do not create** | no — see §6 |
| `weekly` | Auto-renewable, 1 week | `alma.weekly` | `alma.weekly` | yes |
| `monthly` | Auto-renewable, 1 month | `alma.monthly` | `alma.monthly` | yes |
| `annual` | Auto-renewable, 1 year | `alma.annual` | `alma.annual` | yes |

**Thirteen products on Apple** — ten non-consumables and three auto-renewable subscriptions.
**Thirteen on Play** — те же десять разовых и три отдельные подписки в одной группе.
Потолок карточки у Apple — 20 позиций на обе секции, так что запас есть.

**Подписки заводятся тремя отдельными продуктами, а не одним с базовыми планами.**
Так построены обе апки и файл локальных тестов покупок: клиент спрашивает у магазина
`alma.weekly`, `alma.monthly`, `alma.annual`, сервер по этим же идентификаторам выдаёт права.
Один продукт с базовыми планами потребовал бы второй карты соответствий в трёх местах —
и первая же опечатка в ней выглядела бы как исчезнувшая строка на витрине.

The weekly rung was added to the catalogue after this document was first written and spent a
day missing from it — in `LadderKey`, in `catalogue.py` and in `StoreProducts.kt`, absent
here and in `Alma.storekit`. A row missing from this table is a product nobody creates, and
a subscription the binary asks for and the console does not have renders the paywall one row
short with no error anywhere. `backend/tests/test_store_ids.py` now fails when the five
places disagree, which is the only reason to trust this table.

### Why non-consumable and not consumable

A consumable is a thing that is used up and can be bought again — Apple's own examples are
in-game currency and extra lives. Every door and the archive unlock a written interpretation
of numbers that will never change, permanently, for that account. Two consequences follow from
getting this right, and both are irreversible:

* **Restore works.** 3.1.1: *"you should make sure you have a restore mechanism for any
  restorable in-app purchases"*. Only non-consumables appear in `Transaction.currentEntitlements`
  and in Play's `queryPurchasesAsync`. A consumable is gone from the store's records the moment
  it is acknowledged, and a person reinstalling would have nothing to restore and no way to
  prove they paid.
* **Play must not consume them.** `consumeAsync` is what turns a one-time product back into
  something buyable. `PlayBilling` must only ever `acknowledgePurchase` for the ten one-time
  products. That is already how `StoreProducts.grantLanded` is used, but it is worth a test.

The subscription products are the only auto-renewables, and they clear 3.1.2(a)'s *"ongoing
value"* bar on the living layer — transits, solar return, compatibility recompute — which is
why §3 never describes either one as access to Alma.

---

## 2. The identifiers, and the change they require today

### The form

`alma.` + the catalogue key with hyphens turned into underscores. Reverse-DNS under the
Android `applicationId` / iOS bundle namespace (`mobile/android/app/build.gradle.kts:13`).
Both stores accept it: Apple allows *"letters, numbers, hyphens, periods, and underscores"* up
to 100 characters; Play requires an id that *"must start with a number or lowercase letter and
can contain numbers (0-9), lowercase letters (a-z), underscores (_), and periods (.)"* with a
**maximum of 40 characters** — our longest, `alma.astrocartography`, is 29.

### This is a change, and it has to happen before the first product is saved

The shipped clients and the backend default all use the prefix **`alma.`**:

* `backend/alma/config.py:251` — `store_product_prefix: str = Field(default="alma.", alias="ALMA_STORE_PRODUCT_PREFIX")`
* `mobile/ios/Alma/Billing/LadderKey.swift:115` — `static let prefix = "alma."`
* `mobile/android/.../billing/StoreProducts.kt:57` — `const val PREFIX: String = "alma."`

`alma.natal` is a bare, generic string in a namespace we do not own. It is legal on both
stores and it will work — but it can never be changed afterwards, on either store, and the
whole point of a reverse-DNS id is that it cannot collide with anything and reads as ours in a
sales report, a refund ticket and a Server Notification. Since nothing has been created in
either console yet, the change costs three constants and an environment variable. In a month it
costs a new set of products and every buyer's entitlement.

**Do all four together or none:**

```
ALMA_STORE_PRODUCT_PREFIX=alma.        # deployment environment
LadderKey.prefix       = "alma."       # LadderKey.swift:115
StoreProducts.PREFIX   = "alma."       # StoreProducts.kt:57
processor_ids          = see §7                # catalogue.py
```

The pinned `processor_ids` entries win over the computed rule
(`provider.py:680–684`), so the pins are the authority and the prefix constants only have to
agree with them. They must still agree: the two clients compute ids locally and never see the
server's environment.

### Five files, not four — and the failure mode if the console goes first

**`mobile/ios/Alma.storekit` is the fifth**, and it is the one nobody thinks of. It is the
local StoreKit configuration the simulator sells from, it contains `alma.natal`,
`alma.archive`, `alma.monthly` and the rest as literal strings, and its product metadata is
uploadable to App Store Connect. A rename that misses it leaves the simulator selling one set
of ids while the binary asks for another.

**The order matters more than the decision does.** Whichever prefix is chosen, the console
must be filled in from the same string the binary asks for. If somebody types the ids from
this document into App Store Connect while `LadderKey.swift:115` still holds `"alma."`, then
`Product.products(for:)` returns an empty set, the paywall renders with no rows, and the
build comes back as **Guideline 2.1 — "we were unable to locate the in-app purchases"**. And
it cannot be corrected: neither store permits a product id to be changed or reused, so the
recovery is a second set of products with different ids and a migration for anyone who
already bought. It is the only mistake in this packet that is unrecoverable rather than
merely a resubmission.

**Make the build enforce it.** Add a test asserting that the set of `productID`s in
`mobile/ios/Alma.storekit` equals `LadderKey.allStoreProductIDs`, and an equivalent on the
Android side against `StoreProducts`. A half-done rename then fails CI instead of failing
review. `APP-CHANGES-NEEDED.md` §7.

**Nothing may be typed into either console until this is decided.** It is the first item on
the owner's list in `README.md` for that reason, and `REVIEW-NOTES.md` §1 carries a matching
warning above its product list, because that block prints the ids too.

---

## 3. The twelve rows

Names are ≤30 characters, descriptions ≤45, in all six languages — verified by counting, not by
eye. They are written in each language rather than translated from English; the vocabulary is
lifted from `/Users/anatoliymikhaylow/alma_project1/src/lib/i18n/` so a person who read the
landing page recognises the words on the purchase sheet (`wholeArchive`, `archiveNote`,
`oneTimeNote`, `everythingYear` and their six translations).

Chapter counts are from `backend/alma/ai/chapters.py`: natal 16, numerology 5, birth-card 3,
transits 3, solar-return 3, compatibility 4, astrocartography 3, synthesis 4 — 41 in total, one
free chapter per system.

### 3.1 The eight doors — $5.99, non-consumable, permanent, one system

Same price and same description shape for all eight, because the quiz decides which system a
person is offered and a price that varied by system would be a price that varied by quiz answer
(`catalogue.py:167–170`).

| slug | lang | Display name | Description |
|---|---|---|---|
| `natal` | en | Natal chart | All 16 chapters. Yours permanently. |
| | es | Carta natal | Los 16 capítulos. Tuyos para siempre. |
| | de | Geburtshoroskop | Alle 16 Kapitel. Dauerhaft deins. |
| | it | Tema natale | Tutti i 16 capitoli. Tuoi per sempre. |
| | fr | Thème natal | Les 16 chapitres. À toi pour toujours. |
| | pt-BR | Mapa natal | Os 16 capítulos. Seus para sempre. |
| `numerology` | en | Numerology | All 5 chapters. Yours permanently. |
| | es | Numerología | Los 5 capítulos. Tuyos para siempre. |
| | de | Numerologie | Alle 5 Kapitel. Dauerhaft deins. |
| | it | Numerologia | Tutti i 5 capitoli. Tuoi per sempre. |
| | fr | Numérologie | Les 5 chapitres. À toi pour toujours. |
| | pt-BR | Numerologia | Os 5 capítulos. Seus para sempre. |
| `birth-card` | en | Birth Card | All 3 chapters. Yours permanently. |
| | es | Carta de nacimiento | Los 3 capítulos. Tuyos para siempre. |
| | de | Geburtskarte | Alle 3 Kapitel. Dauerhaft deins. |
| | it | Carta di nascita | Tutti i 3 capitoli. Tuoi per sempre. |
| | fr | Carte de naissance | Les 3 chapitres. À toi pour toujours. |
| | pt-BR | Carta de nascimento | Os 3 capítulos. Seus para sempre. |
| `transits` | en | Transits | All 3 chapters. Yours permanently. |
| | es | Tránsitos | Los 3 capítulos. Tuyos para siempre. |
| | de | Transite | Alle 3 Kapitel. Dauerhaft deins. |
| | it | Transiti | Tutti i 3 capitoli. Tuoi per sempre. |
| | fr | Transits | Les 3 chapitres. À toi pour toujours. |
| | pt-BR | Trânsitos | Os 3 capítulos. Seus para sempre. |
| `solar-return` | en | Solar return | All 3 chapters. Yours permanently. |
| | es | Revolución solar | Los 3 capítulos. Tuyos para siempre. |
| | de | Solarhoroskop | Alle 3 Kapitel. Dauerhaft deins. |
| | it | Rivoluzione solare | Tutti i 3 capitoli. Tuoi per sempre. |
| | fr | Révolution solaire | Les 3 chapitres. À toi pour toujours. |
| | pt-BR | Revolução solar | Os 3 capítulos. Seus para sempre. |
| `compatibility` | en | Compatibility | All 4 chapters. Yours permanently. |
| | es | Compatibilidad | Los 4 capítulos. Tuyos para siempre. |
| | de | Kompatibilität | Alle 4 Kapitel. Dauerhaft deins. |
| | it | Compatibilità | Tutti i 4 capitoli. Tuoi per sempre. |
| | fr | Compatibilité | Les 4 chapitres. À toi pour toujours. |
| | pt-BR | Compatibilidade | Os 4 capítulos. Seus para sempre. |
| `astrocartography` | en | Astrocartography | All 3 chapters. Yours permanently. |
| | es | Astrocartografía | Los 3 capítulos. Tuyos para siempre. |
| | de | Astrokartografie | Alle 3 Kapitel. Dauerhaft deins. |
| | it | Astrocartografia | Tutti i 3 capitoli. Tuoi per sempre. |
| | fr | Astrocartographie | Les 3 chapitres. À toi pour toujours. |
| | pt-BR | Astrocartografia | Os 3 capítulos. Seus para sempre. |
| `synthesis` | en | Cross-synthesis | All 4 chapters. Yours permanently. |
| | es | Síntesis cruzada | Los 4 capítulos. Tuyos para siempre. |
| | de | Quersynthese | Alle 4 Kapitel. Dauerhaft deins. |
| | it | Sintesi incrociata | Tutti i 4 capitoli. Tuoi per sempre. |
| | fr | Synthèse croisée | Les 4 chapitres. À toi pour toujours. |
| | pt-BR | Síntese cruzada | Os 4 capítulos. Seus para sempre. |

Apple **reference name** (internal, ≤64 chars, never shown to a customer): `Door — natal`,
`Door — numerology`, and so on. Play has no separate reference name; the title is the only name.

### 3.2 `archive` — $38.99, non-consumable

| lang | Display name | Description |
|---|---|---|
| en | The whole archive | All 41 chapters, eight systems. Once. |
| es | El archivo completo | Los 41 capítulos, ocho sistemas. Una vez. |
| de | Das ganze Archiv | 41 Kapitel, acht Systeme. Einmal gekauft. |
| it | L'archivio intero | 41 capitoli, otto sistemi. Una volta sola. |
| fr | L'archive entière | 41 chapitres, huit systèmes. Une seule fois. |
| pt-BR | O arquivo inteiro | 41 capítulos, oito sistemas. De uma vez. |

Reference name: `Archive — all 41 chapters`.

### 3.3 `archive-upgrade` — $33.00, non-consumable, offered only to a door owner

| lang | Display name | Description |
|---|---|---|
| en | The rest of the archive | Everything else, less the system you own. |
| es | El resto del archivo | Todo lo demás, menos el sistema que tienes. |
| de | Der Rest des Archivs | Alles Übrige, abzüglich deines Systems. |
| it | Il resto dell'archivio | Tutto il resto, meno il sistema che hai. |
| fr | Le reste de l'archive | Tout le reste, moins le système que tu as. |
| pt-BR | O resto do arquivo | Todo o resto, menos o sistema que você tem. |

Reference name: `Archive upgrade — after a door`.

**Do not promote this in-app purchase on the product page.** A $33.00 row sitting beside the
$38.99 archive on a listing that anyone can read is an offer to people who have not earned it.
Promotion is per-product and opt-in; leave it off. See §6 for what stops a modified client
buying it anyway.

**But the promoted-IAP toggle is not the only surface, and this is a gap in the reasoning
above rather than a settled answer.** A store product page can also list an app's in-app
purchases in its own right — a plain list of names and prices, which is a different feature
from a promoted IAP and is not governed by that toggle. I could not verify current behaviour
for that list from this machine, so I am flagging the hole rather than asserting the outcome.

It matters because of what the row says out of context. Read cold by somebody who owns
nothing, "The rest of the archive — $33.00" beside "The whole archive — $38.99" reads as *the
archive is $38.99, or $33.00 if you know where to look*, and the $5.99 door they were about to
buy starts to look like the tax for not reading carefully. The whole ladder depends on each
rung looking like the fair price at the moment it is offered.

**Before the first product is saved, check what a product page actually lists and whether it
can be suppressed.** If it cannot, the fallback is already in this file's own logic:
`archive-upgrade` is the one rung derived by subtraction (archive − door) rather than chosen,
so it is the rung whose visibility can be traded away. Either accept the exposure knowingly
and write it next to the $5.99-per-abuser bound in §6, or drop the product and grant the
credit server-side as a zero-priced entitlement adjustment. What must not happen is
discovering the answer from a customer.

### 3.4 `monthly` — $9.99, auto-renewable, 1 month

| lang | Display name | Description |
|---|---|---|
| en | What moves, monthly | 3 live systems + 30 questions a month. |
| es | Lo que se mueve, cada mes | 3 sistemas vivos + 30 preguntas al mes. |
| de | Was sich bewegt, monatlich | 3 lebende Systeme + 30 Fragen im Monat. |
| it | Ciò che si muove, ogni mese | 3 sistemi vivi + 30 domande al mese. |
| fr | Ce qui bouge, chaque mois | 3 systèmes vivants + 30 questions par mois. |
| pt-BR | O que se move, todo mês | 3 sistemas vivos + 30 perguntas por mês. |

The three systems are `LIVING_SYSTEMS` (`catalogue.py:150`); the forty is
`subscriber_questions_per_month` (`config.py:279–281`). The cap is stated in the description
because 3.1.2(a) treats an undisclosed cap as bait-and-switch — but the 45 characters here are a
secondary surface. The **paywall itself** still has to carry the name, the duration, the full
renewal price and the cap, per <https://developer.apple.com/app-store/subscriptions/> and
Play's *"Users should not have to perform any additional action to review the information."*

Note what this name does not say. It is not "Alma monthly" and not "access to Alma": the
monthly's scope is `"live"` (`catalogue.py:211`), not `"all"`, and a subscription described as
access to the app invites the reviewer's obvious question about what the $38.99 archive was for.

> **The app currently calls this product something else, and the two names have to be made
> one before anything is saved.**
>
> `backend/alma/billing/catalogue.py:630` and `PaywallL10n.monthlyTitle`
> (`mobile/ios/Alma/Localization/PaywallL10n.swift:63`) both say **"Everything live, monthly"**
> — German "Alles Lebendige, monatlich". That is the row a buyer taps. The name in the table
> above is what would go into App Store Connect and Play. Every other rung agrees across the
> two files; the monthly is the only divergence.
>
> Two things go wrong if it ships. First, Apple's confirmation sheet and the iOS *Manage
> Subscriptions* list both use the App Store Connect name, so a buyer taps "Alles Lebendige,
> monatlich" and is asked to authorise a recurring charge for "Was sich bewegt, monatlich" —
> as far as they can tell, a different product — and later hunts the cancellation list for a
> name that is not on it. Second, the in-app name is precisely the everything-claim this
> section argues against, sitting one row above "Alles, für ein Jahr": two rows both promising
> everything, at $9.99 and $78.99, distinguished only by a note.
>
> **Resolution: "What moves, monthly".** The reasoning above is the sound one — the scope is
> `"live"`, and the collision with the annual is real. Change `catalogue.py:630` and
> `PaywallL10n.monthlyTitle` in all six languages to match this table, then create the product.
> `APP-CHANGES-NEEDED.md` §5 carries the six strings.

### 3.5 `annual` — $78.99, auto-renewable, 1 year

| lang | Display name | Description |
|---|---|---|
| en | Everything, for a year | All 41 chapters + what moves, 12 months. |
| es | Todo, durante un año | Los 41 capítulos y lo vivo, 12 meses. |
| de | Alles, für ein Jahr | 41 Kapitel und alles Lebende, 12 Monate. |
| it | Tutto, per un anno | 41 capitoli e ciò che si muove, 12 mesi. |
| fr | Tout, pendant un an | 41 chapitres et le vivant, 12 mois. |
| pt-BR | Tudo, por um ano | 41 capítulos e o que se move, 12 meses. |

`annual` has `scope="all"` (`catalogue.py:215`), so it really does grant the 41 chapters — but
for twelve months, where the archive grants them permanently. "12 months" is in every
description for exactly that reason.

### 3.6 The subscription group

**Apple.** One group. Group reference name `alma-live` (internal); group display name **`Alma`**
in all six locales — it is the app's name, it does not translate, and it is what a person sees
on the Manage Subscriptions screen. Apple: *"A subscription group is a set of subscription
products with varying levels and durations. Users can subscribe to one subscription product per
group at a time"*, which is 3.1.2(b)'s *"should not be able to inadvertently subscribe to
multiple variations of the same thing"* enforced by the store rather than by us.

**Levels.** Apple: *"Arrange subscriptions from most content (level 1) to least."*

| Product | Level | Why |
|---|---|---|
| `annual` | **1** | `scope="all"` — 41 chapters *and* the living layer |
| `monthly` | **2** | `scope="live"` — the living layer only |

These are genuinely different levels of service, not the same service at two durations, so
they must not be stacked at one level. The consequence is the one we want: monthly → annual is
an **upgrade**, effective immediately with a prorated refund of the unused month; annual →
monthly is a **downgrade**, effective at the next renewal date. Stacking them at the same level
would make the switch a crossgrade between different durations, which waits for the existing
subscription to expire — a person paying us more would wait up to a month to get it.

**Play.** Три отдельные подписки в одной группе — так же, как у Apple, и так же, как
спрашивает клиент:

| Product id | Billing period | Renewal type |
|---|---|---|
| `alma.weekly` | P1W | auto-renewing |
| `alma.monthly` | P1M | auto-renewing |
| `alma.annual` | P1Y | auto-renewing |

Раньше здесь стоял один продукт `alma.live` с базовыми планами. От него отказались: обе
апки и сервер знают ровно эти три идентификатора, а один продукт с планами потребовал бы
второй карты соответствий в трёх местах.

Base plan ids may contain only lowercase letters, numbers and hyphens — `monthly` and `annual`
qualify. Play's default replacement mode for switching base plans within one subscription is set
in the console; the two relevant options are *Charge immediately* (`CHARGE_FULL_PRICE`) and
*Charge at the next billing date* (`WITHOUT_PRORATION`). **Set it to *Charge immediately*** so
Play behaves the way the Apple group does for the monthly → annual direction.

This is the one place the two stores are shaped differently, and §8 lists what it costs in code.
It is worth the cost: two *separate* Play subscription products would let one person hold both
at once — Play has nothing like Apple's one-per-group rule across distinct subscriptions — and
`entitlements.grant` would then carry two live subscription rows for one buyer, which is a
double charge, a refund and a complaint.

### 3.7 Family Sharing — recommend off, on every product

App Store Connect has a per-product Family Sharing toggle. Recommendation: **off** on all ten
non-consumables. A reading is written from one person's birth date, birth time and birthplace, and the
grant lives on an Alma account, not on an Apple ID — so a shared purchase would hand five other
people an entitlement to somebody else's chart, which is not a feature we have designed. It can
be turned on later; turning it off later does not take back what was already shared. The
`REVOKE` notification our Apple adapter already handles (`appstore.py:624`, `IGNORED_REASONS`
and `REVOKING`) exists precisely for family sharing ending, so if this is ever switched on the
code is ready — but the decision should be deliberate. **Owner decision.**

---

## 4. Prices

Every amount below is exactly `REGIONAL_CENTS` in `catalogue.py:225–275`, except the fifteen
PPP cells marked **new**, which §5 derives. These are the amounts to type into each console,
per country, manually — not a base price with auto-conversion, because the numbers were chosen
against each market's tax and convention rather than computed from FX (`catalogue.py:220–224`).

| | door ×8 | archive | archive-upgrade | monthly | annual |
|---|---|---|---|---|---|
| **USD** | 5.99 | 38.99 | 33.00 | 9.99 | 78.99 |
| **EUR** | 6.49 | 40.99 | 34.50 | 10.49 | 82.99 |
| **GBP** | 5.99 | 39.99 | 34.00 | 9.99 | 79.99 |
| **CHF** | 6.90 | 45.90 | 39.00 | 11.90 | 92.90 |
| **AUD** | 9.99 | 59.99 | 50.00 | 15.99 | 124.99 |
| **CAD** | 8.99 | 54.99 | 46.00 | 13.99 | 109.99 |
| **NOK** | 79 | 449 | 370 | 109 | 899 |
| **DKK** | 49 | 299 | 250 | 79 | 619 |
| **BRL** | **14.90 new** | 99.90 | **85.00 new** | **25.90 new** | 219.00 |
| **MXN** | **69.00 new** | 429.00 | **360.00 new** | **109.00 new** | 869.00 |
| **PLN** | **12.99 new** | 84.99 | **72.00 new** | **21.99 new** | 174.99 |
| **TRY** | **79.00 new** | 509.00 | **430.00 new** | **129.00 new** | 1029.00 |
| **INR** | **129.00 new** | 849.00 | **720.00 new** | **219.00 new** | 1749.00 |

Countries are mapped to currencies by `COUNTRY_CURRENCY` (`catalogue.py:349–368`): the twenty
euro-area members, GB, CH, AU, CA, NO, DK, BR, MX, PL, TR, IN. Everything else pays USD.

### The invariant that must survive the console

**`archive-upgrade` = `archive` − `door`, in every currency.** It holds today in all eight
priced currencies and in the five new PPP rows (38.99 − 5.99 = 33.00; 40.99 − 6.49 = 34.50;
99.90 − 14.90 = 85.00; and so on). It is the whole of the credit promise: *"the shelf price
less the door, in every currency where both are sold, so the person who decides late pays what
the person who decided at the checkout paid"* (`catalogue.py:26–29`).

**Apple can break it and Play cannot.** Play takes any amount you type. Apple's prices come from
a fixed grid of ~800 price points per storefront that *"follow the most common pricing
convention for each country or region"* — and the `archive-upgrade` row is the one band produced
by subtraction rather than chosen, so it lands on unconventional numbers: **$33.00, A$50.00,
kr 370, kr 250, R$85.00, MX$360.00, 72.00 zł, ₺430.00, ₹720.00**. If any of those is not an
available price point, the nearest one has to be taken **and written back into
`REGIONAL_CENTS["…"]["archive-upgrade"]` in the same commit**, or the arithmetic in
`catalogue()` (`catalogue.py:483`, `credit_cents = archive − upgrade`) states a credit the buyer
is not given. Check these nine cells first, before anything else in the pricing screen.

The `door`, `archive`, `monthly` and `annual` bands all end in local convention (x.99, x.90,
round tens) and should be on the grid without argument.

### Commission, for the record

Apple 15% under the Small Business Program (Pazl LLC is new to the App Store and qualifies) —
**enrol before the first sale**, because it takes effect *"fifteen (15) days after the end of
the fiscal calendar month in which your enrollment is approved"* and is not retroactive. Play
15% on the first $1M/year for one-time products, and 15% on subscriptions *"regardless of
revenue earned by the developer each year"*. Both are already sourced in
`mobile/store/STORE-REQUIREMENTS.md` §3 and §8.

---

## 5. The PPP markets, re-derived

`catalogue.py` sells only the archive and the annual in BRL, MXN, PLN, TRY and INR. The stated
reason (`catalogue.py:18–23`, `264–269`):

> *A PPP-fair door is small enough that local VAT plus the flat per-transaction fee takes a
> quarter to a third of it, so the door would be sold at a loss on the second-cheapest thing we
> make.*

### What changed

**The flat fee is gone, entirely.** It was the whole argument. A card processor charges a
percentage *plus* a fixed amount per transaction, and a fixed amount is a bigger fraction of a
small price — which is exactly why a R$8.99-equivalent door was uneconomic and a R$99.90 archive
was not. Neither Apple nor Google charges a per-transaction fee. Both take a percentage and
nothing else, so **the fraction we keep is now identical whether the price is R$14.90 or
R$99.90.** A cheap product is no longer structurally worse than an expensive one.

**The tax problem is gone too**, and by a different mechanism: both stores are merchant of
record, both collect and remit, and the commission is computed on the price net of tax. Google
states it plainly — in countries where the developer remits, *"Google will pass on the entire
tax amount collected to the developer, and calculate the service fee off the net price of the
product."* That is the same treatment the USD, EUR and GBP rows already get and always got.

**So the refusal has no remaining basis.** Sell the door and the monthly in all five PPP
markets, at the prices in §4. That also unlocks `archive-upgrade` there, which was unavailable
purely because the door it credits against was.

### How the fifteen new prices were derived

Not from FX — the archive and the annual in these currencies are already decided PPP prices
that somebody looked at and accepted, so they are the anchor. Each new price sits at the same
fraction of its market's archive that the US price sits at of the US archive:

| band | fraction of `archive` (US) | BRL | MXN | PLN | TRY | INR |
|---|---|---|---|---|---|---|
| `door` | 599/3899 = 15.4% | 14.9% | 16.1% | 15.3% | 15.5% | 15.2% |
| `monthly` | 999/3899 = 25.6% | 25.9% | 25.4% | 25.9% | 25.3% | 25.8% |
| `archive-upgrade` | archive − door | ✓ | ✓ | ✓ | ✓ | ✓ |

and each is then rounded onto that market's own price ending (R$14.90, MX$69.00, 12.99 zł,
₺79.00, ₹129.00). The annual-to-monthly relationship comes out at 66–70% of twelve months in
every market, against 66% in the US — the ladder keeps its shape.

This method needs no exchange rate and makes no claim I cannot support. It does inherit the
judgement in the archive prices, which is the honest thing to inherit.

### The reason to hesitate, which is not the old reason

There is a per-sale cost the stores do not touch: what it costs us to write the chapters, and —
much more dangerous — the recurring chat allowance a one-time purchase buys. `config.py:137–147`
says it out loud:

> *`tier_of` answers "owner" for any in-force one-time purchase, and a one-time grant never
> expires, so an $8.99 door buys this allowance every month for as long as the account lives.
> … `paid_questions_per_day` at the cheap model, about $0.68 a month at the measured rate …
> That is a real decision and it has not been made.*

Run that against the door as it is priced now. $5.99 less 15% is $5.09 net. Subtract the
chapters (`full_report_budget` caps a whole report at $0.50) and the 15-question bundle that
comes with a purchase (`owner_question_bundle`, `config.py:269`; at the measured $0.0472 a turn
that is about $0.71). Roughly $3.90 of headroom against $0.68 a month of open-ended chat — so a
US door that uses its full allowance stops paying for itself somewhere under six months. That is
the ceiling case and not the average, but the tail is unbounded and permanent.

At PPP prices the same door nets a fraction of that, and the allowance is identical. So the
honest conclusion is a conditional one:

> **Open the PPP markets to the door and the monthly — the flat-fee objection is dead. But cap
> or decay the owner chat allowance first.** The two options `config.py:143–146` already names
> are to let it decay after N months, or to fund it from the subscription instead. Until one of
> them is chosen, a cheap permanent door is a subscription we forgot to charge for, in every
> market including this one.

That decision is the owner's and it is in §9.

---

## 6. The two conditional prices

### `archive-upgrade` — expressible on both stores, and it is a product, not a discount

Apple has **no discount mechanism for a non-consumable.** Every offer type Apple documents —
introductory offers, offer codes, promotional offers, win-back offers — appears only under
auto-renewable subscriptions: *"Grow, retain, and re-acquire customers by giving them a free or
discounted price for a specific duration for an auto-renewable subscription"*
(<https://developer.apple.com/app-store/subscriptions/>). Apple nowhere states that these apply
to a non-consumable, and there is no field for it on one. Play's offers are attached to base
plans and are likewise subscription-only. So neither store has a way to say "this person pays
less for this permanent unlock".

We do not need one, because `catalogue.py` already decided this correctly before either store
was in the picture: *"A credit is a product, not a discount… the only way to keep that promise
is a price id that already carries the reduced amount"* (`catalogue.py:24–29`). `archive-upgrade`
is a real product at a real price. Both stores can sell it. **The gate is ours, not theirs**, in
three places that already exist:

1. The server substitutes it for `archive` in the catalogue response, and only for a buyer
   inside the 30-day window (`catalogue.py:471–484`; `CREDIT_WINDOW` in `auth/entitlements.py`).
2. The Android client refuses to open a sheet for anything the server did not list
   (`StoreProducts.sellable`).
3. The iOS client models it as a rung the server substitutes and never computes the discount
   (`LadderKey.swift:38–40`).

**The residual exposure, stated plainly.** A modified client can buy any product id it knows,
so somebody who never bought a door could buy `archive-upgrade` for $33.00 instead of the
archive for $38.99. Both grant everything, so the loss is **$5.99 per abuser — exactly the door
they did not buy.** That is bounded, small, and self-limiting, and it is the price of Apple
having no offer mechanism for non-consumables. Do not promote the product on the App Store
product page (§3.3) and the id is not discoverable from the listing.

### `archive-bump` — neither store can express it. Do not create it.

`archive-bump` at $29.99 is "the rest of the archive, added to a door **in the same checkout**"
(`catalogue.py:188–196`). Both halves of that are impossible here:

* **Neither store has a multi-item checkout.** Apple shows one product per confirmation sheet;
  Play's billing flow launches one product. There is no "same checkout" to be inside.
* **Neither store has an in-checkout upsell** for one-time products. There is no surface where a
  second, cheaper thing can be offered while the first is being paid for.

The only ways to fake it would each be worse than not having it. A combined "door + rest of
archive" product at $35.98 is just the archive at three dollars off, sitting on the shelf where
anyone can buy it — precisely what `Product.on_the_shelf` exists to prevent
(`catalogue.py:110–122`). And a bare `alma.archive_bump` product in either console is a $29.99
everything-grant that a modified client can buy directly for **$9.00 less than the archive** —
a 50% larger hole than the upgrade's, for a product no honest buyer can ever see. `LadderKey`
already refuses to model it for exactly this reason (`LadderKey.swift:17–23`), and
`StoreProducts.NEVER_ALONE` guards it on Android.

**So: no product identifier, no price, no localised copy, in either console.** Its job — that
somebody who already paid is not charged twice — is done in full by `archive-upgrade`. Its other
job — that deciding at the checkout beats deciding later — cannot be done at a store checkout
and should be dropped rather than simulated.

Two consequences to carry forward:

* **The reviewer notes must still explain it.** 2.1(b): *"If any configured in-app purchase items
  cannot be found or reviewed in your app, explain the reason in your review notes."* Strictly
  that covers configured items, and this one will not be configured — but the catalogue names
  thirteen keys and a reviewer reading `/billing/catalogue` will see twelve. One sentence.
* **The stale comment in `catalogue.py:188–192` still has to be resolved.** It claims
  `899 + 2999 = 3898` is "one cent under the shelf", but `_DOOR_CENTS = 599`, so the real sum is
  `3598` — $3.01 under, not one cent. It is now dead code for store purposes, but the number is
  still published to the web catalogue's code path and still reads as reasoned. Either fix the
  comment and the price to 3299, or delete the product. **Owner decision** (§9).

---

## 7. What changes in `catalogue.py`

`Product.processor_ids` is `dict[str, str]` keyed by processor name and every one of them is
empty today (`catalogue.py:89–92`). Here is the exact content to add — one `processor_ids=`
argument per `Product(...)` call.

```python
PRODUCTS: dict[str, Product] = {
    "natal": Product(
        "natal", "Natal chart", "one_time", _DOOR_CENTS, band="door",
        processor_ids={
            "appstore": "alma.natal",
            "googleplay": "alma.natal",
        },
    ),
    "numerology": Product(
        "numerology", "Numerology", "one_time", _DOOR_CENTS, band="door",
        processor_ids={
            "appstore": "alma.numerology",
            "googleplay": "alma.numerology",
        },
    ),
    "birth-card": Product(
        "birth-card", "Birth Card", "one_time", _DOOR_CENTS, band="door",
        processor_ids={
            "appstore": "alma.birth_card",
            "googleplay": "alma.birth_card",
        },
    ),
    "transits": Product(
        "transits", "Transits", "one_time", _DOOR_CENTS, band="door",
        processor_ids={
            "appstore": "alma.transits",
            "googleplay": "alma.transits",
        },
    ),
    "solar-return": Product(
        "solar-return", "Solar return", "one_time", _DOOR_CENTS, band="door",
        processor_ids={
            "appstore": "alma.solar_return",
            "googleplay": "alma.solar_return",
        },
    ),
    "compatibility": Product(
        "compatibility", "Compatibility", "one_time", _DOOR_CENTS, band="door",
        processor_ids={
            "appstore": "alma.compatibility",
            "googleplay": "alma.compatibility",
        },
    ),
    "astrocartography": Product(
        "astrocartography", "Astrocartography", "one_time", _DOOR_CENTS, band="door",
        processor_ids={
            "appstore": "alma.astrocartography",
            "googleplay": "alma.astrocartography",
        },
    ),
    "synthesis": Product(
        "synthesis", "Cross-synthesis", "one_time", _DOOR_CENTS, band="door",
        processor_ids={
            "appstore": "alma.synthesis",
            "googleplay": "alma.synthesis",
        },
    ),
    "archive": Product(
        "*", "The whole archive", "one_time", 3899, band="archive", scope="all",
        processor_ids={
            "appstore": "alma.archive",
            "googleplay": "alma.archive",
        },
    ),
    # Never created in either console. See mobile/store/PRODUCTS.md §6.
    "archive-bump": Product(
        "*", "The rest of the archive", "one_time", 2999,
        band="archive-bump", scope="all", offered="in-checkout",
        processor_ids={},
    ),
    "archive-upgrade": Product(
        "*", "The rest of the archive", "one_time", 3300,
        band="archive-upgrade", scope="all", offered="after-door",
        processor_ids={
            "appstore": "alma.archive_upgrade",
            "googleplay": "alma.archive_upgrade",
        },
    ),
    # Apple: two products in one subscription group. Play: two base plans on
    # one subscription, so both rows carry the *same* googleplay id and the
    # base plan is what tells them apart — see GOOGLE_BASE_PLANS below.
    "monthly": Product(
        "*", "Everything live, monthly", "monthly", 999,
        band="monthly", interval="month", scope="live",
        processor_ids={
            "appstore": "alma.monthly",
            "googleplay": "alma.monthly",
        },
    ),
    "annual": Product(
        "*", "Everything, for a year", "annual", 7899,
        band="annual", interval="year", scope="all",
        processor_ids={
            "appstore": "alma.annual",
            "googleplay": "alma.monthly",
        },
    ),
}
```

And two module-level constants beside it, because a shared Play id is not enough on its own:

```python
#: Play sells `monthly` and `annual` as two **base plans** on one subscription
#: product, which is how Play expresses what Apple expresses with a subscription
#: group: a person can hold one of them at a time and switching is a switch
#: rather than a second purchase. The consequence is that a Play product id no
#: longer identifies a catalogue row on its own — both rows carry
#: `alma.live` — so `by_price_id` would answer "monthly" for either one.
#: This table is the second half of the key.
GOOGLE_SUBSCRIPTION_ID: str = "alma.live"

#: catalogue key → Play base plan id, and back. Base plan ids may hold only
#: lowercase letters, numbers and hyphens.
GOOGLE_BASE_PLANS: dict[str, str] = {"monthly": "monthly", "annual": "annual"}
```

### The bug this creates if it is only half done

`by_price_id` (`catalogue.py:382–407`) walks `PRODUCTS` in insertion order and returns the first
key whose identifier matches. With `alma.live` on both subscription rows it will always
answer `"monthly"` — so **an annual purchase would grant the monthly's `"live"` scope and record
a year's money against a month's product.** `store_slug` (`provider.py:687–703`) delegates to it,
and `googleplay.Event.product` (`googleplay.py:485–486`) delegates to that. Three layers, one
wrong answer. §8 is what closes it, and it has to land in the same change as the dict above.

---

## 8. What else changes, so the ids and the base plans agree end to end

**`backend/alma/billing/googleplay.py`**

* `Event.product` must resolve a subscription through the base plan, not the product id:
  read `lineItems[0].offerDetails.basePlanId`, and when the product id is
  `GOOGLE_SUBSCRIPTION_ID`, map `monthly`/`annual` through `GOOGLE_BASE_PLANS` instead of
  calling `store_slug`. Everything else keeps the current path. The field is already in the
  test fixture — `backend/tests/test_billing_googleplay.py:214` has
  `"offerDetails": {"basePlanId": "monthly"}` — so the shape is known and only the reading of
  it is missing.
* `verify_purchase`'s subscription branch (`googleplay.py:1031`) then compares the resolved
  base plan against the claimed key, which restores the check the shared id would otherwise
  have broken.
* A test that a token for the annual base plan, claimed as `monthly`, raises `ProductMismatch`.
  That is the exact failure the shared id introduces and it is worth pinning.

**`mobile/android/.../billing/StoreProducts.kt`**

* `PREFIX` → `"alma."`.
* `productId(slug)` must return `GOOGLE_SUBSCRIPTION_ID` for `monthly` and `annual`, and the
  computed id for everything else — the plain rule no longer covers the two subscriptions.
* A companion `basePlanFor(slug)` returning `"monthly"` / `"annual"`.
* `slugFor(productId)` can no longer answer for the subscription id, because Play's `Purchase`
  object carries `products` but **not** the base plan. That is the real cost of this model and
  it needs a deliberate answer: on the re-delivery path the app does not know which plan it is
  holding. The cheapest correct fix is for the app to send the token and let the server, which
  *does* ask Google, answer with the slug it resolved — `/v1/billing/iap/verify` already returns
  what it granted, and `grantLanded` already compares against this account's `unlocked` list.

**`mobile/android/.../billing/PlayBilling.kt`**

* `PlayBilling.purchase` currently takes
  `details.subscriptionOfferDetails?.firstOrNull()?.offerToken` (line 289). With two base plans
  on one subscription that picks whichever Play returns first — **a person tapping Annual could
  be billed Monthly.** It must select the offer whose `basePlanId` matches the slug being bought
  and refuse rather than fall back if none does.
* Pass `SubscriptionUpdateParams` with the existing purchase token whenever the buyer already
  holds the other base plan, so Play treats it as a switch. Without it Play answers
  `ITEM_ALREADY_OWNED` and the person cannot upgrade.

**`mobile/ios/Alma/Billing/LadderKey.swift`**

* `prefix` → `"alma."` (line 115). Nothing else: Apple has no base plans, `monthly` and
  `annual` stay two product ids, and `archive-bump` is already absent.

**Environment**

* `ALMA_STORE_PRODUCT_PREFIX=alma.` so the computed fallback in
  `provider.store_product_id` agrees with the pins for any row that ever loses one.

**Tests worth adding in the same change**

* Every `processor_ids` value round-trips through `store_slug` back to its own key, for both
  processors — except the two Play subscription rows, which are asserted to share an id and to
  be told apart by base plan.
* `REGIONAL_CENTS[c]["archive-upgrade"] == REGIONAL_CENTS[c]["archive"] − REGIONAL_CENTS[c]["door"]`
  for every currency that prices all three, plus the USD row. This is the invariant §4 says
  Apple's price grid may force us to break, and a test is what makes breaking it loud.

---

## 9. What only the owner can decide

1. **Adopt `alma.` or keep `alma.`?** Free today, impossible after the first product is
   saved in either console. Recommendation: adopt, and change the four constants in §2 together.
2. **Cap or decay the owner chat allowance before opening the PPP door.** `config.py:143–146`
   already names the two options and says the decision has not been made. Opening BRL, MXN, PLN,
   TRY and INR to a $2–3 permanent door while an unbounded monthly chat allowance rides on it
   makes the smallest sale the most expensive one.
3. **`archive-bump`: fix the price to 3299, or delete the product?** It gets no store identifier
   either way (§6). But the comment at `catalogue.py:188–192` reasons from a $8.99 door that no
   longer exists, and the live number means door + bump = $35.98 against a $38.99 archive — so
   the archive is dominated by a cheaper path in the same checkout wherever that checkout still
   exists.
4. **Family Sharing on the ten non-consumables: on or off?** Recommendation off (§3.7). It is a
   per-product toggle and the consequences of turning it on later are smaller than turning it
   off later.
5. **Verify the nine `archive-upgrade` price points exist on Apple's grid** — $33.00, A$50.00,
   kr 370, kr 250, R$85.00, MX$360.00, 72.00 zł, ₺430.00, ₹720.00 — and if any does not, decide
   which way to move it. Whatever is chosen has to go back into `REGIONAL_CENTS` in the same
   commit.
6. **Confirm Play's default replacement mode** is set to *Charge immediately* on the
   `alma.live` subscription, so the monthly → annual switch behaves like Apple's
   level-1-over-level-2 upgrade rather than waiting for the next billing date.
7. **UNSOURCED — verify in Play Console:** whether Billing Library 8 requires one-time products
   to be created under the newer *purchase options and offers* model rather than as plain
   one-time products. The release notes and a dedicated one-time-products page could not be
   fetched in this pass, and Play's Billing 8 deadline is **31 August 2026**. The existing
   Android code uses `queryProductDetailsAsync` with `ProductType.INAPP`, which is the current
   API either way; what needs checking is only the console-side creation form.
8. **UNSOURCED — verify at fill-in:** the App Store Connect character limits for a *subscription*
   display name and description. The IAP reference states 30 and 45; the subscription reference
   states only the forbidden-character rules and gives no counts. All copy in §3 is written to
   30/45, so it fits whichever is true — but confirm before assuming a longer name is available.
