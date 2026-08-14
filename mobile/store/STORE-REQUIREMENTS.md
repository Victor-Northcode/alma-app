# What the stores actually require

Written 7 August 2026 against the live rule pages, not from memory. Every claim below
carries the URL it came from and, where the wording decides something, the operative
sentence itself. Where a rule is moving under litigation it is marked **UNSTABLE**. Where
I could not find an authoritative page for something, it says **UNSOURCED** rather than a
confident guess.

Entity: **Pazl LLC**. Both developer accounts exist. Nothing in this file touches them —
this is the material that gets filled *into* them.

---

## 0. Two deadlines that are three weeks away

These are the only items here with a clock on them, and both land on the same day.

**Play — Billing Library 8.** *"By August 31, 2026, all new apps and updates must use
Billing Library version 8 or later"*, with an extension available to 1 November 2026.
<https://developer.android.com/google/play/billing/subscriptions>

**Play — target API 36.** *"Starting August 31, 2026: New apps and app updates must
target Android 16 (API level 36) or higher."* Existing apps must target Android 15 (API 35)
or higher to stay available to new users on newer devices. An extension to 1 November 2026
can be requested.
<https://support.google.com/googleplay/android-developer/answer/11926878>

A first Play submission after 31 August 2026 must satisfy both. Check
`mobile/android` against them before anything else in this file matters.

---

# APPLE

## 1. The guidelines that bite

All quotations in this section are from <https://developer.apple.com/app-store/review/guidelines/>.

### 4.3(b) Spam — the one this app is submitted against

> Don't submit apps that are indistinguishable from what's already widely available.
> Opportunistically creating variants of existing app categories or popular apps degrades
> App Store discovery, reduces overall app quality, and harms both users and developers.
> **Certain kinds of apps, such as dating, flashlight, sound effects, wallpaper, simple
> timers, and fortune telling, are well established on the App Store and we will not accept
> new submissions unless they offer a meaningfully different or improved experience.** We
> may remove these apps from the App Store going forward if they are not updated, improved,
> or do not attract customers.

Two things follow that shape everything else we write.

The test is **"meaningfully different or improved experience"** — an *experience* claim, not
a technology claim. So the reviewer notes cannot simply assert "we use JPL ephemerides".
They have to name a thing the reviewer can *do in the app* that they cannot do in the
established category, and then point at the code that makes it true. The three we have are:
the eight systems are computed independently and the app shows where they **disagree**;
every sentence cites the placement it was read from; and the writer refuses to publish a
paragraph citing a placement absent from the chart — `backend/alma/ai/validator.py`.

And note the second sentence: *"We may remove these apps from the App Store going forward
if they... do not attract customers."* Passing review once is not a permanent state for
this category.

### 1.1.6 — the escape hatch that is closed

> False information and features, including inaccurate device data or trick/joke
> functionality, such as fake location trackers. **Stating that the app is "for
> entertainment purposes" won't overcome this guideline.**

Consequence for us: no "for entertainment purposes only" line anywhere — not in the
description, not in the app, not in the reviewer notes, not in any of the six localisations.
The disclaimer buys nothing and reads as an admission. What replaces it is the product's own
position: it does not predict, and it says so.

### 3.1.1 In-App Purchase

> If you want to unlock features or functionality within your app, (by way of example:
> subscriptions, in-game currencies, game levels, access to premium content, or unlocking a
> full version), you must use in-app purchase. Apps may not use their own mechanisms to
> unlock content or functionality, such as license keys, augmented reality markers, QR
> codes, cryptocurrencies and cryptocurrency wallets, etc.

> Any credits or in-game currencies purchased via in-app purchase may not expire, and **you
> should make sure you have a restore mechanism for any restorable in-app purchases**.

Restore is mandatory in practice: eleven of our twelve products are permanent, and the door
and the archive are exactly the "restorable in-app purchase" the sentence names.

3.1.1 also describes the *only* sanctioned non-subscription free trial:

> Non-subscription apps may offer a free time-based trial period before presenting a full
> unlock option by setting up a Non-Consumable IAP item at Price Tier 0 that follows the
> naming convention: "XX-day Trial."

**We are not using this.** The free chapter is free permanently and is not an IAP at all, so
none of the "XX-day Trial" naming or duration-disclosure obligations attach. Worth stating
plainly in the reviewer notes so nobody looks for a trial product that does not exist.

### 3.1.2 Subscriptions

> Apps may offer auto-renewable in-app purchase subscriptions, regardless of category on the
> App Store.

3.1.2(a) sets the bar the monthly/annual tier has to clear:

> If you offer an auto-renewable subscription, **you must provide ongoing value to the
> customer**, and the subscription period must last at least seven days and be available
> across all of the user's devices. ... examples of appropriate subscriptions include: new
> game levels; episodic content; multiplayer support; apps that offer consistent,
> substantive updates; **access to large collections of, or continually updated, media
> content**; software as a service ("SAAS"); and cloud support.

> Subscriptions may be offered alongside à la carte offerings (e.g. you may offer a
> subscription to an entire library of films as well the purchase or rental of a single
> movie).

That second sentence is the explicit blessing of our ladder: permanent one-time purchases
sitting next to a subscription is a named, permitted shape. The "ongoing value" test is met
by the living layer specifically — transits, solar return, compatibility recompute; the
41 chapters do not. That is why the subscription must be described as the *living* layer and
never as "access to Alma", which would invite the question of what the $38.99 archive was
for.

> As with all apps, those offering subscriptions should allow a user to get what they've paid
> for without performing additional tasks, such as posting on social media, uploading
> contacts, checking in to the app a certain number of times, etc.

The 40-questions-a-month cap is a quantity of a purchased thing, not a task demanded of the
user. Still, the cap must be stated at the point of purchase (see §4) — an undisclosed cap
is the "bait-and-switch" 3.1.2(a) also names.

3.1.2(b):

> Users should have a seamless upgrade/downgrade experience and should not be able to
> inadvertently subscribe to multiple variations of the same thing.

Monthly and annual therefore go in **one subscription group**, so StoreKit handles the
crossgrade and nobody ends up holding both.

### 2.1 App Completeness — the reviewer needs a way in

> Submissions to App Review... should be final versions with all necessary metadata and
> fully functional URLs included; placeholder text, empty websites, and other temporary
> content should be scrubbed before submission. Make sure your app has been tested on-device
> for bugs and stability before you submit it, and **include demo account info (and turn on
> your back-end service!) if your app includes a login**.

> **2.1(b)** If you offer in-app purchases in your app, make sure they are complete,
> up-to-date, visible to the reviewer and functional. If any configured in-app purchase items
> cannot be found or reviewed in your app, explain the reason in your review notes.

Two of our products are structurally invisible to a reviewer poking at the app: `archive-bump`
($29.99, `offered="in-checkout"`) and `archive-upgrade` ($33.00, `offered="after-door"`).
2.1(b) is the sentence that obliges the reviewer notes to explain exactly when each surfaces.
`backend/alma/billing/catalogue.py` — the `offered` field and the `on_the_shelf` property —
is where that behaviour is enforced.

### 2.3 Accurate Metadata

> **2.3.1(a)** Don't include any hidden, dormant, or undocumented features in your app; your
> app's functionality should be clear to end users and App Review. **All new features,
> functionality, and product changes must be described with specificity in the Notes for
> Review section of App Store Connect (generic descriptions will be rejected)** and
> accessible for review.

> **2.3.2** If your app includes in-app purchases, make sure your app description,
> screenshots, and previews clearly indicate whether any featured items, levels,
> subscriptions, etc. require additional purchases.

Screenshots showing a written reading must make it visible that readings are purchased. The
free calculation is free; the prose is not, and the screenshots have to carry that.

> **2.3.7** ... **App names must be limited to 30 characters.** Metadata such as app names,
> subtitles, screenshots, and previews should not include prices, terms, or descriptions that
> are not specific to the metadata type. App subtitles... should not include inappropriate
> content, reference other apps, or **make unverifiable product claims**.

"Unverifiable product claims" in the subtitle is a live risk for us — "NASA JPL ephemeris"
is verifiable and defensible; anything implying accuracy of prediction is not.

> **2.3.8** Metadata should be appropriate for all audiences, so make sure your app and
> in-app purchase icons, screenshots, and previews **adhere to a 4+ age rating even if your
> app is rated higher**.

> **2.3.10** ... don't include names, icons, or imagery of other mobile platforms or
> alternative app marketplaces in your app or metadata.

No Play badge, no Android imagery, anywhere in the iOS listing or the app.

### 5.1.1 Data Collection and Storage

**(i) Privacy Policies:**

> All apps must include a link to their privacy policy in the App Store Connect metadata
> field **and within the app in an easily accessible manner**. The privacy policy must
> clearly and explicitly:
> - Identify what data, if any, the app/service collects, how it collects that data, and all
>   uses of that data.
> - Confirm that any third party with whom an app shares user data... will provide the same
>   or equal protection of user data...
> - **Explain its data retention/deletion policies and describe how a user can revoke consent
>   and/or request deletion of the user's data.**

Note the third bullet: the privacy policy itself must describe deletion, not merely the app.
Birth date, birth time and birth place are the collection to describe; so is whatever the
written interpretations are generated by.

**(ii) Permission:**

> Apps that collect user or usage data must secure user consent for the collection... **Paid
> functionality must not be dependent on or require a user to grant access to this data.**
> Apps must also provide the customer with an easily accessible and understandable way to
> withdraw consent.

**(v) Account Sign-In:**

> **If your app doesn't include significant account-based features, let people use it without
> a login. If your app supports account creation, you must also offer account deletion within
> the app.** Apps may not require users to enter personal information to function, except when
> directly relevant to the core functionality of the app or required by law.

The deletion requirement has its own page:
<https://developer.apple.com/support/offering-account-deletion-in-your-app/>

> Starting June 30, 2022, apps submitted to the App Store that support account creation must
> also let users initiate deletion of their account within the app. Deleting an account
> removes the account from the developer's records, along with any data associated with the
> account that the developer isn't legally required to maintain.

> Offer to delete the entire account record, along with associated personal data. You may
> include additional options, but **only offering to temporarily deactivate or disable an
> account is insufficient**.

> If people need to visit a website to finish deleting their account, include a link directly
> to the page on your website where they can complete the process.

> All users should be allowed to delete their accounts, regardless of where they're located.

Global, not GDPR-scoped. And the first clause of 5.1.1(v) is worth taking seriously in its
own right: birth data and a saved archive are genuine account-based features, so an account
is justifiable — but the free chapter should not be behind one.

### 5.1.2 Data Use and Sharing

> **(i)** Unless otherwise permitted by law, you may not use, transmit, or share someone's
> personal data without first obtaining their permission. You must provide access to
> information about how and where the data will be used. **You must clearly disclose where
> personal data will be shared with third parties, including with third-party AI, and obtain
> explicit permission before doing so.** ... You must receive explicit permission from users
> via the App Tracking Transparency APIs to track their activity.

**"including with third-party AI"** is the sentence that matters most to Alma. Birth data is
personal data, and the written interpretations are produced by a model. If any part of that
runs on a third-party model provider, that must be disclosed in the privacy policy *and*
consented to. The `backend/alma/ai/` layer decides whether this applies; the answer belongs
in the privacy policy in plain words, in all six languages.

> **(ii)** Data collected for one purpose may not be repurposed without further consent
> unless otherwise explicitly permitted by law.

> **(iii)** Apps should not attempt to surreptitiously build a user profile based on collected
> data...

> **(i)** *(cont.)* Your app may not require users to enable system functionalities (e.g. push
> notifications, location services, tracking) in order to access functionality, content, use
> the app, or receive monetary or other compensation.

Transit notifications cannot be a condition of anything.

### 3.1.1(a) External purchase links — **UNSTABLE**

Today's guideline text reads:

> Developers may apply for entitlements to provide a link in their app to a website the
> developer owns or maintains responsibility for in order to purchase digital content or
> services. **These entitlements are not required for developers to include buttons, external
> links, or other calls to action in their United States storefront apps.**

> ...**In all other storefronts, except for the United States storefront, where this
> prohibition does not apply**, apps and their metadata may not include buttons, external
> links, or other calls to action that direct customers to purchasing mechanisms other than
> in-app purchase.

And 3.1.3:

> Apps in this section cannot, within the app, encourage users to use a purchasing method
> other than in-app purchase, **except for apps on the United States storefront** and as set
> forth in 3.1.1(a) and 3.1.3(a).

**Why this is unstable.** On 11 December 2025 the Ninth Circuit largely affirmed the contempt
findings against Apple but vacated the blanket ban on commissions, remanding for the district
court to set a rate "more reasonably tied to Apple's actual costs". The 0% commission on US
external-link purchases therefore holds only until that court approves a rate. On 30 June 2026
the Supreme Court granted certiorari, limited to whether a party can be held in contempt for
violating the "spirit" of an injunction.
<https://www.fenwick.com/insights/publications/ninth-circuit-largely-upholds-ruling-in-epic-v-apple>
· <https://scl-llp.com/ninth-circuit-upholds-apple-contempt-finding-but-narrows-scope-of-remedial-relief/>
· <https://www.supremecourt.gov/DocketPDF/25/25-1311/409561/20260526163506450_2026-05-26%20Apple-Epic%20--%20Cert%20Petition%20and%20Appendix.pdf>

**Recommendation: do not use it for launch.** The owner's decision is that all payments go
through Apple and Google. An external link would be legal on the US storefront today, illegal
on the other five storefronts we ship to, and priced at an unknown commission at some point in
the coming year. Building six-locale paywall logic that branches on storefront, to chase a rate
that a court has not set, is a bad trade against a 15% fee. Revisit when the district court
publishes a number.

---

## 2. The App Privacy questionnaire

<https://developer.apple.com/app-store/app-privacy-details/>

Filled in App Store Connect before you can submit. It produces the privacy label on the
product page.

**The 14 categories and their types:**

| Category | Types |
|---|---|
| Contact Info | Name · Email Address · Phone Number · Physical Address · Other User Contact Info |
| Health & Fitness | Health · Fitness |
| Financial Info | Payment Info · Credit Info · Other Financial Info |
| Location | Precise Location · Coarse Location |
| Sensitive Info | Sensitive Info |
| Contacts | Contacts |
| User Content | Emails or Text Messages · Photos or Videos · Audio Data · Gameplay Content · Customer Support · Other User Content |
| Browsing History | Browsing History · Search History |
| Identifiers | User ID · Device ID |
| Purchases | Purchase History |
| Usage Data | Product Interaction · Advertising Data · Other Usage Data |
| Diagnostics | Crash Data · Performance Data · Other Diagnostic Data |
| Surroundings | Environment Scanning · Body (Hands, Head) |
| Other Data | Other Data Types |

For each type you declare: whether it is collected, the purposes, whether it is **linked to
the user**, and whether it is **used to track**.

**"Used to Track You":**

> "Tracking" refers to linking data collected from your app about a particular end-user or
> device, such as a user ID, device ID, or profile, with Third-Party Data for targeted
> advertising or advertising measurement purposes, or sharing data collected from your app
> about a particular end-user or device with a data broker.

Explicitly *not* tracking: data linked solely on-device and never sent off-device; data shared
with brokers solely for fraud prevention or security; data shared with consumer reporting
agencies for creditworthiness.

**"Data Linked to You":**

> Data collected from an app is often linked to the user's identity, unless specific privacy
> protections are put in place before collection to de-identify or anonymize it, such as:
> stripping data of any direct identifiers, such as user ID or name, before collection;
> manipulating data to break the linkage and prevent re-linkage to real-world identities.

And to qualify as *not* linked you must additionally not attempt to link it back, and not tie
it to other datasets that would enable linkage. Apple adds: *"'Personal Information' and
'Personal Data' as defined under relevant privacy laws are considered linked to the user."*

**What this means for Alma, concretely.** Birth date, birth time and birth place, stored
against an account, are Linked to You. There is no honest way to call them unlinked — they are
personal data under GDPR and they are stored against a user id. Whether birth data belongs in
**Sensitive Info** is the one judgement call in this form and the owner should make it
knowingly: Apple does not enumerate what falls under Sensitive Info on this page
(**UNSOURCED** — the in-console definition is the operative text and should be read at
fill-in time). Nothing about Alma requires tracking, so **Used to Track You: No** across the
board — which is worth protecting, because it is also what lets the app skip ATT entirely.

---

## 3. Small Business Program — 15%

<https://developer.apple.com/app-store/small-business-program/>

**Rate:** 15% on paid apps and in-app purchases.

**Eligibility:**

> To participate in the program, you and your Associated Developer Accounts must have earned
> **no more than 1 million USD in total proceeds** (sales net of Apple's commission and
> certain taxes and adjustments) during the 12 fiscal months occurring within the previous
> calendar year, and have earned no more than 1 million USD during the current year.

> Existing developers who made up to 1 million USD in proceeds in the prior calendar year for
> all their apps, **as well as developers new to the App Store**, can qualify.

Pazl LLC is new to the App Store, so it qualifies.

**Enrolment:** be the Account Holder in the Apple Developer Program; review and accept the
latest Paid Apps agreement (Schedule 2 to the Apple Developer Program License Agreement) in
App Store Connect; list all Associated Developer Accounts if any.

**When it takes effect:**

> Your proceeds will be adjusted **fifteen (15) days after the end of the fiscal calendar
> month in which your enrollment is approved**. For example, if your enrollment is approved on
> February 10, 2022, your proceeds are adjusted starting March 14, 2022.

It is not retroactive. **Enrol before the first sale**, or the first weeks are billed at 30%.

**Crossing the threshold:**

> If a participating developer surpasses the 1 million USD threshold in the current calendar
> year, the standard commission rate will apply to future sales.

> If a developer's proceeds fall below the 1 million USD threshold in a future calendar year,
> they can re-qualify for the 15% commission the year after.

---

## 4. Auto-renewable subscription requirements

<https://developer.apple.com/app-store/subscriptions/>

**Required on the sign-up screen (the paywall itself, not a link from it):**

- Subscription name and duration, with the content or services provided during the period.
- The **full renewal price**, shown clearly and prominently, localised in available
  currencies. The billing amount must be the most prominent pricing element.
- **A way for current subscribers to sign in or restore purchases.**
- Free trials, if offered, must clearly indicate duration and the price billed after — we
  offer none, so this line does not apply.

**Required in the app *and* in App Store metadata:**

- A functional link to your **Terms of Use (EULA)**.
- A functional link to your **Privacy Policy**.

If you do not supply a custom EULA, Apple's Licensed Application End User License Agreement
applies: *"Apps made available through the App Store are licensed, not sold, to you. Your
license to each App is subject to your prior acceptance of either this Licensed Application
End User License Agreement ('Standard EULA'), or a custom end user license agreement between
you and the Application Provider ('Custom EULA'), if one is provided."*
<https://www.apple.com/legal/internet-services/itunes/dev/stdeula/>

**Required in App Store Connect per subscription:**

- **Subscription display name** — *"user-friendly, self-explanatory name that differentiates
  it from others"*.
- **Description** — what subscribers receive.
- Price and duration per territory.
- Subscription group assignment — every subscription belongs to a group.

**Product page IAP limits** (<https://developer.apple.com/app-store/product-page/>):

> In-app purchases and subscriptions are shown in two separate sections on your product page,
> and you can showcase up to **20 total items** across both of these sections.

> In-app purchase **names are limited to 35 characters and descriptions are limited to 55
> characters**.

We have twelve products, so 20 is not binding. **35 and 55 characters are binding** and are
tight in German — write those strings natively per locale, do not translate the English.

### The ladder, mapped to StoreKit product types

Source of truth for every number: `/Users/anatoliymikhaylow/alma_project1/backend/alma/billing/catalogue.py`.

| Catalogue slug | Price (USD) | StoreKit type | Notes |
|---|---|---|---|
| `natal`, `numerology`, `birth-card`, `transits`, `solar-return`, `compatibility`, `astrocartography`, `synthesis` | $5.99 each | Non-consumable | 8 doors, one per system. Restorable. |
| `archive` | $38.99 | Non-consumable | All 41 chapters. |
| `archive-bump` | $29.99 | Non-consumable | `offered="in-checkout"` — never on the shelf. Must be explained under 2.1(b). |
| `archive-upgrade` | $33.00 | Non-consumable | `offered="after-door"` — offered once to a door owner, inside a 30-day window (`CREDIT_WINDOW` in `auth/entitlements.py`). Must be explained under 2.1(b). |
| `monthly` | $9.99 | Auto-renewable | The living layer + 30 questions/month. |
| `annual` | $78.99 | Auto-renewable | Same group as `monthly` (3.1.2(b)). |

Every one of the twelve needs a display name ≤35 and a description ≤55 in each of the six
locales, plus a review screenshot for each promoted item.

---

## 5. Age rating

<https://developer.apple.com/help/app-store-connect/manage-app-information/set-an-app-age-rating/>
· <https://developer.apple.com/help/app-store-connect/reference/app-information/age-ratings-values-and-definitions>

The tiers are **4+, 9+, 13+, 16+, 18+** (plus Unrated, which cannot ship on the App Store).
The old 12+/17+ labels are gone. Answers are None / Infrequent / Frequent, and the rating is
the maximum triggered by any answer.

| Descriptor | None | Infrequent | Frequent |
|---|---|---|---|
| Profanity or Crude Humor | 4+ | 9+ | 13+ |
| Horror/Fear Themes | 4+ | 9+ | 13+ |
| Alcohol, Tobacco, or Drug Use | 4+ | 13+ | 18+ |
| Mature or Suggestive Themes | 4+ | 9+ | 16+ |
| Sexual Content or Nudity | 4+ | 13+ | 18+ |
| Cartoon or Fantasy Violence | 4+ | 9+ | 13+ |
| Realistic Violence | 4+ | 13+ | 18+ |
| Guns or Other Weapons | 4+ | 9+ | 13+ |
| Medical or Treatment Information | 4+ | 13+ | 16+ |
| Health or Wellness Topics | 4+ | 9+ | 9+ |
| Simulated Gambling | 4+ | 13+ | 18+ |
| Contests | 4+ | 4+ | 13+ |
| Loot Boxes | 4+ | 9+ | 9+ |

Capabilities that raise the floor regardless of content: **Social Media → 13+**,
**Unrestricted Web Access → 16+**. User-Generated Content, Messaging and Chat, and
Advertising are all 4+ on their own.

### What Alma should answer, and the three that are judgement calls

Everything in the violence, sexuality, substance, gambling and contest rows is **None** —
there is nothing in an ephemeris-driven reading that touches them. That leaves four rows and
two capabilities that need an actual decision:

- **Horror/Fear Themes — likely None, but check the tarot art.** The birth-card system draws
  on the Major Arcana. If the app renders a Death or Tower card image, an "Infrequent" answer
  is arguable and costs 9+. If the cards are named in text without ominous imagery, None
  holds. **Owner decision.**
- **Health or Wellness Topics — the expensive one.** Note this row is unusual: *any* non-None
  answer gives 9+, Infrequent and Frequent alike. If a chapter discusses wellbeing, sleep,
  stress or the body, Infrequent is the honest answer and the app is 9+. **Owner decision**,
  and it is the single answer most likely to move the rating off 4+.
- **Medical or Treatment Information — None.** This must stay None, which means no chapter may
  read as health guidance. That is a content constraint, not just a form answer.
- **Mature or Suggestive Themes — likely None.** Compatibility readings describe relationships.
  If they describe sex, this becomes Infrequent (9+). **Owner decision.**
- **Messaging and Chat capability — probably No.** Alma's chat is the user talking to a model,
  not to another person. The descriptor is about person-to-person messaging. **UNSOURCED** —
  Apple's page does not define the boundary; if in doubt, answering Yes costs nothing (it is
  4+ on its own).
- **Unrestricted Web Access — must be No.** Opening the privacy policy in Safari is fine.
  A general-purpose in-app WKWebView pointed at arbitrary URLs would trigger 16+. Do not
  ship one.

**Expected result: 4+ if Health/Wellness is None; 9+ if it is Infrequent.** Either is fine
commercially. Answer honestly — 2.3.1(a) makes a wrong answer a metadata accuracy problem,
not a rounding error.

Also from 2.3.8: **screenshots and IAP art must be 4+ regardless of the app's rating.**

---

## 6. Apple listing spec

| Field | Limit / spec | Source |
|---|---|---|
| App Name | **2–30 characters**, localisable | <https://developer.apple.com/help/app-store-connect/reference/app-information> |
| Subtitle | **30 characters** max, localisable | same |
| Promotional Text | **170 characters**, optional, editable without a new version | <https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information/> |
| Description | **4,000 characters**, required, localisable, **plain text only — no HTML** | same |
| Keywords | **100 bytes**, comma-separated, no spaces after commas; don't repeat the app name, subtitle or category | same · <https://developer.apple.com/app-store/product-page/> |
| What's New in This Version | **4,000 characters**, required after the first version | platform-version-information |
| Support URL | **Required**, localisable, full URL with protocol; *"must lead to actual contact info"* | same |
| Marketing URL | Optional, localisable, full URL with protocol | same |
| Privacy Policy URL | **Required** for iOS; must also be linked inside the app (5.1.1(i)) | app-information · guidelines 5.1.1(i) |
| Copyright | Required; format `YYYY Company Name, Inc.` — the © is added automatically | platform-version-information |
| Screenshots | **1 to 10 per localisation**; `.jpeg`, `.jpg` or `.png`; **no alpha channel or transparency** | <https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications/> |
| App Previews | Up to **3**, up to **30 seconds** each | <https://developer.apple.com/app-store/product-page/> |
| App Icon | Delivered **in the build** — asset catalog or Icon Composer, then upload to App Store Connect. Not a separate App Store Connect upload any more. | <https://developer.apple.com/help/app-store-connect/manage-app-information/add-an-app-icon/> |

**App Store icon pixel size: UNSOURCED.** Apple's current help page for the icon says only
*"You can create your app icon using Icon Composer or add your app icon to an asset catalog
within your Xcode project. After adding icons in Xcode, upload the build to App Store
Connect."* — it gives no dimensions, and the Human Interface Guidelines page did not render
for fetching. The 1024×1024 figure is what the Xcode asset catalog has historically required
for the App Store slot; **verify it in Xcode's asset catalog inspector against the actual
project before treating it as settled.**

### Screenshot dimensions

Required: **iPhone 6.9"** (or 6.5" if 6.9" is not provided) and **iPad** if the app runs on
iPad.

| Display | Devices | Portrait | Landscape |
|---|---|---|---|
| iPhone 6.9" | 17 Pro Max, 16 Pro Max, 15 Pro Max | 1320 × 2868 | 2868 × 1320 |
| iPhone 6.5" | 14 Plus, 13 Pro Max, 12 Pro Max | 1284 × 2778 | 2778 × 1284 |
| iPhone 6.3" | 17 Pro, 16 Pro, 15 Pro, 14 Pro | 1179 × 2556 | 2556 × 1179 |
| iPhone 6.1" | 17e, 14, 13, 12, 11 Pro, XS, X | 1170 × 2532 | 2532 × 1170 |
| iPad 13" | iPad Pro M5/M4/6th–1st gen, iPad Air M4/M3/M2 | 2064 × 2752 | 2752 × 2064 |
| iPad 12.9" | iPad Pro (2nd gen) | 2048 × 2732 | 2732 × 2048 |
| iPad 11" | iPad Pro M5/M4/4th–1st gen, iPad Air, iPad (A16), iPad mini | 1488 × 2266 | 2266 × 1488 |

<https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications/>

Ten slots × six locales = up to 60 iPhone screenshots, and the same again for iPad if we ship
iPad. That is a real production cost — decide the count before task #38 renders anything.

---

# GOOGLE

## 7. Payments — what must go through Play billing

<https://support.google.com/googleplay/android-developer/answer/10281818>

Play's billing system is required for: *"Digital items (such as virtual currencies, extra
lives, additional playtime, add-on items, characters, or avatars)"*, **subscription
services**, **app functionality or content**, and cloud software and services.

Not required for: physical goods and services, financial transactions, peer-to-peer payments,
certain regulated services, gift card sales, loyalty point exchanges, some 1:1 online
services, and consumption-only apps where the user accesses content purchased elsewhere.

Alma's readings are "app functionality or content" and the subscription is a subscription
service. Both are squarely in scope. Alternative billing exists in India, South Korea and the
EEA with a 4% fee reduction (*"when the service fee is 15% for transactions through Google
Play's billing system, it will be 11% for transactions made through an alternative billing
system"*) — not worth the integration at our volume, and it conflicts with the owner's
decision that all payments go through the stores.

## 8. Service fee — 15%

<https://support.google.com/googleplay/android-developer/answer/112622>

> **15%** for the first $1M (USD) revenue earned by the developer each year

> **30%** for earnings in excess of $1M (USD) revenue earned by the developer each year

> **15%** for automatically renewing subscription products purchased by subscribers,
> **regardless of revenue earned by the developer each year**

The subscription line is the important asymmetry against Apple: on Play, `monthly` and
`annual` are 15% permanently, with no $1M cliff and no annual programme to re-qualify for.
On Apple the same subscriptions revert to 30% the moment Pazl LLC crosses $1M in a calendar
year. Worth knowing when the ladder gets re-tuned.

## 9. Subscriptions policy

<https://support.google.com/googleplay/android-developer/answer/9900533>

Required disclosure before purchase — *"Users should not have to perform any additional action
to review the information"*, meaning it is on the paywall itself, not behind a tap:

- *"clearly and explicitly disclosing your offer terms, the cost of your subscription, the
  frequency of your billing cycle, the automatic renewal terms"*
- If a trial or intro offer exists: *"clearly and accurately describe the terms of your offer,
  including the duration, pricing, and description of accessible content or services"* and
  *"let your users know how and when a free trial will convert to a paid subscription, how much
  the paid subscription will cost"*. **We offer neither, so neither applies** — which is a
  small, real simplification of the paywall in six languages.
- *"clearly disclose how a user can manage or cancel their subscription. You must also include
  in your app access to an easy-to-use, online method to cancel the subscription"*

That last clause requires a cancel path **inside the app** — in practice a deep link to the
Play subscriptions centre. It is not satisfied by a support email.

Technical model: subscriptions are built from **base plans and offers**; `monthly` and
`annual` should be two base plans on one subscription product, which is Play's equivalent of
Apple's subscription group.
<https://developer.android.com/google/play/billing/subscriptions>

## 10. Account deletion — two separate obligations

<https://support.google.com/googleplay/android-developer/answer/13316080>
· <https://support.google.com/googleplay/android-developer/answer/13327111>

**In-app:** *"Users must have a readily discoverable option to initiate app account deletion
from within your app"*, without hidden obstacles.

**Web:** an *"accessible external web resource for account deletion"*, and *"a link to this web
resource must be entered in the designated URL form field within Play Console."* This is the
requirement Apple does not have — a **publicly reachable deletion URL that works without
installing the app**, and it must be live before submission. Google accepts several forms:
*"an additional link that initiates account deletion, a customer service email or a form they
can submit a request through."*

**Deletion means deletion:** *"Temporary account deactivation, disabling, or 'freezing' the app
account does not qualify as account deletion."* And *"When users request account removal, you
must also delete the user data associated with that app account."*

**In the Data safety form:** *"all developers will be prompted and required to answer a new set
of questions in the Data safety form focused around deletion practices"*, and you must
*"disclose if your app provides account deletion and provide the web link within your Data
safety form in Play Console."*

## 11. Data safety form

<https://support.google.com/googleplay/android-developer/answer/10787469>

Definitions that decide the answers:

> **Collection:** Transmitting data from your app off a user's device.

> **Sharing:** Transferring user data collected from your app to a third party.

> **Ephemeral processing:** Accessing and using it while the data is only stored in memory and
> retained for no longer than necessary to service the specific request.

Ephemeral processing is the escape from declaring "collection" — and it does **not** apply to
Alma's birth data, which is stored server-side against an account. Declare it collected.

**Data types (Play's list, which is not Apple's):** Location · Personal info · Financial info ·
Health and fitness · Messages · Photos and videos · Audio files · Files and docs · Calendar ·
Contacts · App activity · Web browsing · App info and performance · Device or other IDs.

For each: collected? shared? required or optional? and the purposes (app functionality,
analytics, advertising, fraud prevention/security/compliance, personalisation, account
management).

**Security practices questions:**
- Whether data collected or shared is **encrypted in transit**.
- Whether the app **provides a way for users to request deletion of their data**.
- An optional declaration of an **independent security review** against OWASP standards.

The form covers third-party SDKs too: *"data from libraries, SDKs, and webviews your app
controls"* counts as your collection. Every analytics or crash SDK in `mobile/android` must be
accounted for.

**Note the shape mismatch with Apple.** Play has no "linked to you" / "used to track"
distinction and no "Sensitive Info" bucket; Apple has no "required vs optional" and no
"purposes per type" in the same form. The two forms must describe the same reality, but they
cannot be filled in with the same answers. Fill each against its own definitions.

## 12. Content rating and target audience

**Content rating questionnaire** — <https://support.google.com/googleplay/android-developer/answer/9898843>
· <https://support.google.com/googleplay/android-developer/answer/9859655>

> Apps without a content rating will be removed from the Play Store.

> Misrepresentation of your app's content may result in removal or suspension.

Ratings are issued via IARC by: **ESRB** (Americas), **PEGI** (Europe and the Middle East),
**USK** (Germany), **Australian Classification Board**, **ClassInd** (Brazil), **GRAC** (South
Korea), plus IARC Generic elsewhere. One questionnaire produces all of them — which matters
for us because we ship to Brazil (ClassInd) and Germany (USK) and their thresholds differ from
ESRB's.

**Whether IARC asks about the occult or fortune telling: UNSOURCED.** Neither Play help page
enumerates the questions, and the questionnaire itself is only visible inside Play Console.
Read it there before answering — some IARC forms have historically included references-to-the-
occult items that would be directly relevant to a divination app, and guessing here is exactly
the "misrepresentation" the policy penalises.

**Target audience and content** — <https://support.google.com/googleplay/android-developer/answer/9285070>

> Select the age group(s) that your app targets. You can make multiple selections if
> appropriate.

> You should only select more than one age group for your app's target audience if you have
> designed your app for and ensured that your app is appropriate for users within each of the
> selected age group(s).

**Alma should select adults only.** Selecting any group under 13 pulls the app into the
Families Policy Requirements, including *"the requirement to use only Families Self-Certified
Ads SDKs to serve ads"* and, for mixed audiences, a neutral age screen. None of that is
appropriate for a paid product about a person's birth data. Selecting only "Ages 18 and over"
also enables the **Restrict Minor Access** feature.

## 13. Play listing spec

| Field | Limit / spec | Source |
|---|---|---|
| App name | **30 characters** | <https://support.google.com/googleplay/android-developer/answer/9859152> |
| Short description | **80 characters** | same |
| Full description | **4,000 characters** | same |
| App icon | **512 × 512 px**, 32-bit PNG **with alpha**, max **1024 KB** | <https://support.google.com/googleplay/android-developer/answer/9866151> |
| Feature graphic | **1024 × 500 px**, JPEG or 24-bit PNG, **no alpha** — required | same |
| Phone screenshots | **min 2, max 8** per device type; JPEG or 24-bit PNG; min side 320 px, max side 3840 px; 16:9 landscape / 9:16 portrait | same |
| Tablet screenshots | **minimum 4** suggested; 1,080–7,680 px; 16:9 / 9:16 | same |
| Privacy policy URL | Required, *"available on an active URL"* | <https://support.google.com/googleplay/android-developer/answer/9859455> |
| Account deletion URL | Required, entered in the designated Play Console field | <https://support.google.com/googleplay/android-developer/answer/13316080> |

Note the icon divergence: **Play wants alpha, Apple's icon comes from the build and
historically forbids transparency.** They are two different files. Do not export one from the
other.

Tablet screenshots are optional unless the app targets tablets, but omitting them can limit
tablet visibility — I could not find that stated on an official Google page in this pass, only
on third-party ASO writeups, so treat "Google may limit tablet visibility without them" as
**UNSOURCED**.

## 14. Play's own 4.3(b) analogue

Google has no fortune-telling clause, but it has two policies that reach the same place.

**Spam / Repetitive content** — <https://support.google.com/googleplay/android-developer/answer/9899034>

> We don't allow apps that merely provide the same experience as other apps already on Google
> Play. Apps should provide value to users through the creation of unique content or services.

**Minimum functionality** — <https://support.google.com/googleplay/android-developer/answer/9898783>

> Apps should provide a stable, responsive, and engaging user experience. Apps that crash, do
> not have the basic degree of adequate utility as mobile apps, lack engaging content, or
> exhibit other behavior that is not consistent with a functional and engaging user experience
> are not allowed.

Named violations include *"apps that are static without app-specific functionalities, for
example, text only or PDF file apps"*.

The same evidence answers both: unique content and services, computed on device-independent
ephemerides, not a text file. But note that Play's phrasing is about *engagement and utility*
where Apple's is about *differentiation* — the Play notes should lead with what the app
computes and does, not with how it differs from competitors.

---

# 15. The two listings, side by side

| | Apple | Google |
|---|---|---|
| Name | 30 chars | 30 chars |
| Second line | Subtitle, 30 chars | Short description, 80 chars |
| Body | Description, 4,000 chars, plain text | Full description, 4,000 chars |
| Above the body | Promotional text, 170 chars, editable any time | — |
| Search terms | Keywords, 100 bytes, comma-separated | — (indexed from the description) |
| Screenshots | 1–10 per locale, no alpha | 2–8 per device type |
| Hero image | — | Feature graphic 1024 × 500, required |
| Icon | From the build | 512 × 512 PNG with alpha, ≤1024 KB |
| Video | Up to 3 previews, ≤30s | YouTube URL |
| Privacy policy | Required in Connect **and** in-app | Required, active URL |
| Support | Support URL required, must reach real contact info | Contact email required |
| Deletion | In-app deletion required | In-app deletion **and** a public web URL |

Six locales — en, es, de, it, fr, pt-BR — multiply every localisable field on both sides.
`/Users/anatoliymikhaylow/alma_project1/src/lib/i18n/` holds the established voice; the 30- and
35-character fields in particular have to be written in each language rather than translated,
because German will not fit an English sentence.

---

# 16. Open items — decisions and unsourced things

Collected so nothing here gets treated as settled when it isn't.

**Needs a decision from the owner:**
1. Age rating — Health or Wellness Topics: None or Infrequent? Infrequent makes the app 9+.
2. Age rating — Horror/Fear Themes: does the birth-card system render Death/Tower imagery?
3. Age rating — Mature or Suggestive Themes: how explicit do compatibility readings get?
4. App Privacy — does birth data go in **Sensitive Info**, and does any third-party AI provider
   touch it (5.1.2(i) requires disclosure and explicit consent if so)?
5. Whether to ship iPad at launch. It doubles the screenshot production.

**Unsourced, verify before relying on:**
- Apple's App Store icon pixel dimensions. Apple's current help page states no size. Check
  Xcode's asset catalog.
- Whether the IARC questionnaire asks about occult / fortune-telling content. Only visible in
  Play Console.
- Whether omitting Play tablet screenshots limits tablet visibility. Third-party claim only.
- Apple's in-console definition of "Sensitive Info".

**Unstable:**
- US-storefront external purchase links (3.1.1(a) / 3.1.3). Legal today at 0% commission;
  the Ninth Circuit vacated the commission ban on 11 December 2025 and remanded for a rate,
  and the Supreme Court granted cert on 30 June 2026 on the contempt question. Recommendation
  above: do not build against it for launch.

**A discrepancy in our own catalogue, noticed while checking the prices.** The comment above
`archive-bump` in `catalogue.py` reads *"899 + 2999 = 3898 is the sum that is one cent under
the shelf"* — but `_DOOR_CENTS = 599` on line 165, and 599 + 2999 = 3598, which is $3.01 under
the $38.99 shelf price rather than one cent under. The comment is stale from the $8.99 door.
Either the bump price or the comment needs revisiting before these numbers are typed into
App Store Connect and Play Console, because whatever is entered there is what customers are
charged.
