# Submission checklist

Every step, in the order it has to happen, from "nothing is configured" to "both
stores are reviewing". Written 7 August 2026 against the same commit as
`REVIEW-NOTES.md`, `DATA-INVENTORY.md` and `STORE-REQUIREMENTS.md`.

**How to read the marks.**

- **`[OWNER]`** — only the owner can do it. A signing certificate, a bank account, a
  tax form, a legal identity, a password. Nothing in this repository and no agent can
  perform these, and pretending otherwise is how a submission stalls on a Friday.
- **`[REPO]`** — a change in this repository. Somebody who is not the owner can do it.
- **`[DECIDE]`** — a judgement call with no correct answer. It blocks the steps under
  it, so it is listed where it blocks rather than in a pile at the end.

Order matters more than it looks. Three things in particular are not retroactive: the
Small Business Program (B3), the Play merchant account (C3), and the ephemeris kernel
being present on the production host (A6). Getting any of them late costs money or
credibility rather than time.

---

# 0. The decisions that block everything

Nothing below can start until these are answered. They are all `[DECIDE]` and they are
all the owner's.

> **Three things were added on 7 August 2026, after three checkers read this packet against
> a running backend and a simulator build. Two of them come before every other line in this
> file.**
>
> **0.0 — `[OWNER]` The domain does not exist.** `nslookup alma.pazl.ai` and
> `nslookup api.pazl.ai` both return **NXDOMAIN**; only the apex `pazl.ai` resolves, to
> `95.81.101.52`. General network access from the same shell was fine. A1 below is written as
> though the hosts merely need to be pointed somewhere — they need to be *created*. Apple
> fetches the Privacy Policy URL during review and rejects on a dead one before anybody opens
> the build, so this is not "before launch", it is **before any field is typed into either
> console.**
>
> **0.0b — `[DECIDE]` The product-id prefix, and it is the one irreversible decision here.**
> The binary asks StoreKit for `alma.natal`, `alma.archive` and the rest
> (`LadderKey.swift:115`); `PRODUCTS.md` §2 recommends `ai.pazl.alma.`. If the console is
> filled in from the document while the binary still ships the old prefix,
> `Product.products(for:)` returns an empty set and the build comes back as Guideline 2.1 —
> and neither store lets a product id be changed or reused, so the recovery is a second set of
> products and a migration for everybody who already bought. Decide first, land all five files
> in one commit, add the build assertion. `APP-CHANGES-NEEDED.md` §7.
>
> **0.0c — `[DECIDE]` Guest deletion: fix the code, or answer Apple differently.** A guest
> cannot delete their account, a guest is the default state, and §3 of the reviewer notes
> recommends telling Apple no sign-in is required — so App Review will be holding an
> undeletable account containing a birth time and a birthplace. Guideline 5.1.1(v).
> `APP-CHANGES-NEEDED.md` §1 has the fix; the alternatives are worse. **Not optional, and it
> is a code change, so it needs a slot in somebody's week rather than a decision at fill-in
> time.**

| # | Decision | What turns on it | Where the evidence is |
|---|---|---|---|
| 0.1 | **iPad or iPhone only at launch?** | Up to 60 extra screenshots (10 slots × 6 locales), plus a second layout pass. The project currently declares **both**: `TARGETED_DEVICE_FAMILY = "1,2"` in `mobile/ios/Alma.xcodeproj/project.pbxproj:214,240`. iPhone-only means changing it to `"1"` — a one-line `[REPO]` change, but it must happen **before** B8 and before task #38 renders anything. | `STORE-REQUIREMENTS.md` §6 |
| 0.2 | **Health or Wellness Topics: None or Infrequent?** | 4+ versus 9+. Any non-None answer gives 9+. | `STORE-REQUIREMENTS.md` §5; `REVIEW-NOTES.md` §13 |
| 0.3 | **Horror/Fear Themes**, i.e. does the birth-card system render Death/Tower *imagery* or only name the cards? | 9+ if imagery. | same |
| 0.4 | **Mature or Suggestive Themes** — how explicit compatibility gets. | 9+ (Infrequent) or 16+ (Frequent). | same |
| 0.5 | **Does birth data go in Apple's "Sensitive Info"?** | One row of the privacy label. Apple's public page does not enumerate the category; the in-console definition is the operative text and must be read at fill-in time. | `DATA-INVENTORY.md` §6 |
| 0.6 | **Are there DPAs with Anthropic and Resend?** | Play's Data safety "Shared" answer for every category. As processors under a DPA the answer is No; without one, the honest answer for Anthropic flips to **Yes** — and Anthropic receives birth date, birth time, birthplace, name and chat messages. **Do not file the Data safety form until this is answered.** | `DATA-INVENTORY.md` §6, §7.3 |
| 0.7 | **Is 16 the minimum age we file, and does a gate get added?** | Both stores' age declarations. `src/lib/legal.ts:65` says 16 and three legal pages repeat it; `backend/alma/api/schemas.py:63–70` accepts any birth date from 1900 to 2100, so nothing enforces it. The number we file and the number the code enforces have to agree. | `DATA-INVENTORY.md` §5.5 |
| 0.8 | **The analytics opt-out**: ship a Settings toggle, or narrow the DNT promise to the web in all six languages? | 5.1.1(ii) consent-withdrawal, and what may be written in either store's notes. | `REVIEW-NOTES.md` §11 |
| 0.9 | **`archive-bump` at $29.99** — the comment in `backend/alma/billing/catalogue.py:187–192` says "899 + 2999 = 3898 is one cent under the shelf", but `_DOOR_CENTS = 599` on line 165, so 599 + 2999 = 3598, which is **$3.01 under** the $38.99 shelf price. Either the price or the reasoning is stale. | It is not created in either store (B5, C7), so it does not block submission — but the web checkout charges it, and the number typed into a console is what a customer pays. Settle it before anything is priced. | `STORE-REQUIREMENTS.md` §16 |
| 0.10 | **Where is the backend hosted, and what does the host log?** | The blank at `src/app/(legal)/privacy/page.tsx:145`, the backup window at `:248`, the supervisory authority at `:271`, and both stores' diagnostics answers. Nothing in the repo stores an IP address, but every TLS terminator logs by default. | `DATA-INVENTORY.md` §1.17, §7 |

---

# A. Before either store — the things both submissions depend on

## A0. `[REPO]` The three copy reconciliations, before anything is pasted

Cheap, fast, and each one is a thing a reviewer can catch in under a minute.

- [ ] `python3 mobile/store/check-listing.py` exits 0. It now checks 42 fields against their
      limits **and** fails on four content patterns: "eight" near "axes" in any of the six
      languages, a currency figure, the other store's name in a body, and an entertainment
      disclaimer. Wire it into whatever runs before a commit.
- [ ] The free-tier list in all twelve descriptions still matches `PREVIEW_FIELDS`
      (`backend/alma/api/routers/systems.py:47-78`) key for key. If the backend widens it
      (`APP-CHANGES-NEEDED.md` §4), the list grows in the same commit.
- [ ] `mobile/ios/Alma.storekit:116` and `scr.empty.lead` no longer say eight systems on the
      axes — or the engine has been widened to make them true. `APP-CHANGES-NEEDED.md` §2.
      **These two are the last places the corrected claim has not reached, and one of them
      uploads to App Store Connect.**

## A1. `[OWNER]` Domains and hosting, decided and live

> **As of 7 August 2026 neither host exists.** `nslookup alma.pazl.ai` → NXDOMAIN.
> `nslookup api.pazl.ai` → NXDOMAIN. Only `pazl.ai` resolves. Read the rest of this step as
> work to be done, not as configuration to be verified.

Two hosts are already written into the build and both must resolve before a reviewer
touches anything.

- `https://api.pazl.ai` — the backend. `mobile/android/app/build.gradle.kts:51`
  (release `API_BASE`) and `mobile/ios/Alma.xcodeproj/project.pbxproj:221`
  (`ALMA_API_BASE` in the Release configuration).
- `https://alma.pazl.ai` — the web app. It is the magic-link host in
  `mobile/android/app/src/main/AndroidManifest.xml` (`android:host="alma.pazl.ai"`,
  `pathPrefix="/link"`).

A reviewer runs the **Release** build. A backend that answers slowly, or a certificate
that has not propagated, is a 2.1 rejection dressed as a bug.

## A2. `[OWNER]` Backend environment, complete

The variables the store adapters refuse to work without. Names from
`backend/alma/config.py`.

| Variable | Why | Line |
|---|---|---|
| `ALMA_ENV=production` | Turns off the `debug_token` in the magic-link response, among other things | `:73`, `:414` |
| `ALMA_DATABASE_URL` | | `:82–84` |
| `ANTHROPIC_API_KEY` | No key, no written chapters | `:103` |
| `APPLE_BUNDLE_ID=ai.pazl.alma` | A valid Apple signature proves Apple signed it, not that it is ours. This line is the whole of what refuses somebody else's purchase | `:193` |
| `ALMA_APPLE_ACCEPT_SANDBOX=true` | **Leave it on.** Reviewers run the production build against sandbox StoreKit accounts; a build that refuses `environment: "Sandbox"` fails review for purchases that do not work | `:207` |
| `GOOGLE_PLAY_PACKAGE_NAME=ai.pazl.alma` | | `:215` |
| `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` | Credentials or a path to them. A Play purchase token proves nothing on its own — verifying it means calling the Play Developer API as us | `:216` |
| `GOOGLE_PLAY_PUBSUB_AUDIENCE` | The nearest thing the Play notification endpoint has to a webhook secret. Without it, renewals are granted to whoever finds the URL | `:229` |
| `GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT` | Optional, and worth setting anyway | `:236` |
| `RESEND_API_KEY` | Only the three letters in `alma/mail.py`. On a store build a buyer who never signed in causes no mail at all | |
| `ALMA_STORE_PRODUCT_PREFIX` | Default `alma.`. **Do not change it** — it is every product id in both consoles | `:251` |

## A3. `[REPO]` + `[OWNER]` The store-notification URL problem — resolve before C10

`POST /v1/billing/webhook` (`backend/alma/api/routers/billing.py:420`) resolves its
adapter with `billing_adapter()` and no argument, which returns **the single
processor named by `ALMA_BILLING_PROVIDER`** (`backend/alma/config.py:476–496`). There
is exactly one such route and no separate Pub/Sub endpoint anywhere in
`backend/alma/api/routers/`.

So as written, one deployment cannot receive App Store Server Notifications *and* Play
Real-time Developer Notifications: whichever one is not the configured provider fails
signature verification and is refused with a 401. `POST /v1/billing/iap/verify` is
fine — it picks its adapter from the request's `platform` field (`billing.py:578`,
`:681–693`) — which is why launch-day purchases will work on both platforms regardless.

What this actually costs: renewals, refunds and revocations arriving by notification.
On iOS the client's `Transaction.updates` listener sweeps them on next launch
(`mobile/ios/Alma/Billing/AlmaStore.swift:107–120`), so a renewal resolves when the
person next opens the app rather than at the moment it is charged. That is a degraded
flow, not a broken one — but it is not what should ship, and a subscription that
appears to lapse is a refund request.

**Verify this against a running deployment before pasting a URL into either console.**
If it holds, it is a `[REPO]` fix (a second route, or one route that picks its adapter
from the request shape) and it belongs before C10.

## A3b. ~~`[REPO]` The Support page~~ — **BUILT.** URL still needs the host.

Apple's Support URL is a required App Store Connect field and *"must lead to actual contact
info"*. The page is built: `src/app/(legal)/support/page.tsx`, returning 200, verified
7 August 2026. **File `https://<host>/support`.**

It does what this entry asked for and one thing more: it names `hello@pazl.ai`, says what to
include (the store, the order number, the account email *or* the account id a guest has), and
commits to a response time — *usually the same day and never later than three working days*.
That number is a promise written into the copy, not read from a constant, so the owner should
confirm it is one they will keep before this is filed. It links `/delete-account`, and it
states the thing that decides most refund requests: Apple and Google hold the money, so the
self-service routes are theirs and are printed as addresses.

This no longer blocks B12. What blocks B12 is A0 — the host.

## A4. ~~`[REPO]` The public account-deletion page~~ — **BUILT.** URL still needs the host.

Play validates the URL field. The page is built: `src/app/(legal)/delete-account/page.tsx`,
returning 200, verified 7 August 2026. **File `https://<host>/delete-account`.**
(`(cabinet)/settings` no longer exists — the web cabinet was deleted; the app is where a
signed-in person deletes.)

It says what deletion removes (`DATA-INVENTORY.md` §3), gives the in-app route by its real
label — **data & legal**, which is what both apps call that section — and gives
`hello@pazl.ai` for someone who has uninstalled. The guest limitation is stated, but narrower
than this entry assumed: the backend and the Android client both landed guest deletion, so it
is **iOS only**, and the page says so as a client that has not caught up rather than as
policy. It also carries the section that costs money if it is missing: deleting an Alma
account does not cancel a store subscription.

This no longer blocks C9. What blocks C9 is A0 — the host. Two things here still move:
`APP-CHANGES-NEEDED.md` §1 (iOS guest deletion) shortens three paragraphs when it lands, and
the page is still English while `/support` is translated.

## A5. `[REPO]` Fix the privacy policy before it is filed as a URL

Both stores require the policy URL, and 5.1.1(i) requires it to *"clearly and
explicitly identify what data the app collects… and all uses of that data"*. Five
things in `src/app/(legal)/privacy/page.tsx` are wrong or blank today. All are
enumerated with line numbers in `DATA-INVENTORY.md` §5 and §7; the two that a reviewer
could catch unaided are:

- **§5.1** — the recipient list names Paddle or Dodo, neither of which receives
  anything on a store build, and omits Apple and Google, which do.
- **§5.2** — it says what goes to Anthropic is "the calculated chart". It is also the
  **birth date, the birth time to the minute, the birthplace label and the name**,
  verbatim (`backend/alma/ai/writer.py:152–164`). Guideline 5.1.2(i) requires
  disclosure of sharing *"including with third-party AI"*, so this paragraph is the
  one Apple's newest clause reaches directly.

Then the blanks: hosting region (:145), backup window (:248), supervisory authority
(:271), transfer terms per processor (:144). Those are 0.10 and `[OWNER]`.

Whatever changes here changes in all six languages.

## A6. `[REPO]` Confirm the ephemeris kernel ships to production

`backend/alma/engine/ephemeris.py:66–84` uses `backend/data/de440s.bsp` when it exists
and otherwise falls back to the DE421 kernel bundled with `skyfield-data`. The file is
in the repository (32 MB). If the production image or the deploy step excludes
`backend/data/`, the app runs on DE421 and the sentence "NASA JPL DE440s" in the
reviewer notes and the listing stops being true.

Check it by reading `provenance.ephemeris` on any calculation response from production
— it is recorded on every result (`backend/alma/calc/service.py:64–80`) and it is the
kernel's own filename. It must read `de440s.bsp`.

## A7. `[REPO]` Fix the `alma.synthesis` product description

`mobile/ios/Alma.storekit:116` describes the cross-synthesis as *"where the eight
systems agree and disagree"*. The engine compares **three**
(`backend/alma/engine/synthesis.py:355–368`) and the app's own copy says three. That
string is what gets typed into App Store Connect at B5. Fix it there and in the
Play equivalent before the products are created. See `REVIEW-NOTES.md` §14.

## A8. `[REPO]` Publish `assetlinks.json` at `alma.pazl.ai`

The Android manifest declares `android:autoVerify="true"` on the magic-link intent
filter. Without the Digital Asset Links file at
`https://alma.pazl.ai/.well-known/assetlinks.json`, tapping a sign-in link raises the
app chooser instead of opening Alma. Not a review blocker; a first-impression one.
Needs the release signing certificate's SHA-256 from C4, so it happens after C4.

## A9. `[REPO]` Run the suite, on the production kernel

`cd backend && pytest`. The tests that carry the 4.3(b) argument are
`test_natal.py:179` and `:187` (birth-time sensitivity), `test_calc_contract.py:167`
(systems that need a time refuse rather than guess), and the whole of `test_ai.py`
(the validator). If any of them is red, the reviewer notes are making a claim the
repository does not support.

---

# B. Apple, in order

## B1. `[OWNER]` Apple Developer Program membership, as Pazl LLC

An organisation membership needs a D-U-N-S number for the legal entity and a person
with authority to bind it. If the account already exists, confirm it is the
**organisation** account and not a personal one — the entity on the App Store product
page is the one on the account, and it cannot be changed by editing metadata.

## B2. `[OWNER]` Agreements, tax, banking — all three, before anything is priced

App Store Connect → Business. The **Paid Apps agreement** (Schedule 2 to the Developer
Program License Agreement) must be accepted, the tax forms completed for every region
being sold into, and a bank account added. Until all three are green, in-app purchase
products cannot leave "Missing Metadata" and cannot be submitted.

This is the single most common multi-day stall in the whole list, and it is entirely
`[OWNER]`.

## B3. `[OWNER]` Small Business Program — enrol now, not after the first sale

15% instead of 30%. Pazl LLC is new to the App Store and therefore qualifies.

The rule that makes the timing matter: *"Your proceeds will be adjusted fifteen (15)
days after the end of the fiscal calendar month in which your enrollment is
approved."* It is **not retroactive**. Enrolling after launch means the first weeks
are billed at 30%.

Requirements: be the Account Holder, accept the latest Paid Apps agreement (B2), list
any Associated Developer Accounts.
<https://developer.apple.com/app-store/small-business-program/>

## B4. `[OWNER]` Identifier, capabilities, signing

- App ID `ai.pazl.alma` — matches `PRODUCT_BUNDLE_IDENTIFIER` at
  `mobile/ios/Alma.xcodeproj/project.pbxproj:209,235` and `APPLE_BUNDLE_ID` in A2.
  All three must be the same string.
- Enable **In-App Purchase** on the App ID.
- **Distribution certificate** and the App Store provisioning profile. `[OWNER]` — a
  private key that must not leave the owner's keychain or the owner's CI secret store.
- Set `DEVELOPMENT_TEAM` in the Xcode project. It is unset today; `CODE_SIGN_STYLE`
  is `Automatic` (`project.pbxproj:198,224`), so once the team is set Xcode manages
  the rest.

## B5. `[OWNER]` Create the twelve in-app purchase products

App Store Connect → your app → Monetization → In-App Purchases and Subscriptions.

Ids are computed, not chosen freshly: the catalogue key, prefixed `alma.`, hyphens
turned into underscores (`mobile/ios/Alma/Billing/LadderKey.swift:80–96`). Typing a
different string here produces a row that silently vanishes from the paywall.

**Non-consumable, ten of them:**

| Product ID | US price | What it grants |
|---|---|---|
| `alma.natal` | $5.99 | all 16 natal chapters |
| `alma.numerology` | $5.99 | all 5 numerology chapters |
| `alma.birth_card` | $5.99 | all 3 birth-card chapters |
| `alma.transits` | $5.99 | all 3 transit chapters |
| `alma.solar_return` | $5.99 | all 3 solar-return chapters |
| `alma.compatibility` | $5.99 | all 4 compatibility chapters |
| `alma.astrocartography` | $5.99 | all 3 astrocartography chapters |
| `alma.synthesis` | $5.99 | all 4 cross-synthesis chapters |
| `alma.archive` | $38.99 | all 41 chapters, all eight systems |
| `alma.archive_upgrade` | $33.00 | the archive, for someone who already bought one door |

**Auto-renewable, two of them, in one subscription group** (3.1.2(b), so nobody can
hold both):

| Product ID | US price | Period |
|---|---|---|
| `alma.monthly` | $9.99 | 1 month |
| `alma.annual` | $78.99 | 1 year |

**Do not create `alma.archive_bump`.** It exists only for the web checkout, where a
second item can be added to a cart in flight. StoreKit shows one product per
confirmation, so it has no meaning here, and the iOS build cannot request it
(`LadderKey.swift:17–23`). A Play or App Store product id, once created, is
purchasable whether or not our server listed it — and `archive-bump` grants exactly
what `archive` grants, nine dollars cheaper.

**No introductory offers and no promotional offers on either subscription.** This is
the decision, not an oversight. `mobile/ios/Alma.storekit` already has
`"introductoryOffer": null` on both.

Regional prices: `backend/alma/billing/catalogue.py` `REGIONAL_CENTS` holds the exact
minor units per currency and per band. Those integers must equal what App Store
Connect charges. Use Apple's price points nearest to them and, where a point does not
exist, **change the number in `catalogue.py` to match Apple** rather than the other
way round — a displayed price and a charged price that disagree is a chargeback.

## B6. `[OWNER]` `[DECIDE]` Localise the products — 35 and 55 characters, six times

Each of the twelve needs a display name (**≤35 characters**) and a description
(**≤55 characters**) in en, es, de, it, fr, pt-BR. That is 144 strings, and 55
characters is genuinely tight in German.

Write them natively per language against `src/lib/i18n/`. Do not translate the English
— a 55-character English sentence becomes a 70-character German one and gets truncated
in the middle of a word on the product page.

The English source of truth is `mobile/ios/Alma.storekit` (see A7 — one of them is
wrong).

## B7. `[OWNER]` The App Privacy questionnaire

App Store Connect → App Privacy. Every answer is derived in `DATA-INVENTORY.md` §6,
with the file and line it was read from.

The two that need a person: **Sensitive Info** (decision 0.5) and confirming
**"Used to Track You: No"** on every row — which is what lets the app skip App
Tracking Transparency entirely, and which is only true as long as nobody adds an
analytics SDK.

Declare **Precise Location: Yes**. It is not a device reading — nobody asks iOS for a
location and there is no CoreLocation import — but a birthplace coordinate stored to
full precision against an account is a precise location about a person, and saying
otherwise would be a false declaration.

## B8. `[OWNER]` `[DECIDE]` Age rating

Answer decisions 0.2, 0.3 and 0.4. Everything in the violence, sexuality, substance,
gambling and contest rows is None. **Medical or Treatment Information must stay
None** — that is a content constraint as much as a form answer, and
`backend/alma/ai/validator.py:153–161` already enforces the hard cases.

**Unrestricted Web Access: No.** Opening the privacy policy is fine; a general-purpose
in-app browser would trigger 16+, and there isn't one.

Expected result: 4+ if Health/Wellness is None, 9+ if it is Infrequent. Either is
fine commercially. Remember 2.3.8: **screenshots and IAP art must be 4+ regardless of
the app's rating.**

## B9. `[OWNER]` Listing metadata, six locales

Limits and sources in `STORE-REQUIREMENTS.md` §6. Name ≤30, subtitle ≤30, promotional
text ≤170, description ≤4,000 plain text, keywords ≤100 bytes. Support URL and
Privacy Policy URL are required and must resolve; the support URL *"must lead to
actual contact info"*.

Copyright field format: `2026 Pazl LLC` — the © is added automatically.

Read `REVIEW-NOTES.md` §9 and §10 before writing a word of this in any language.

## B10. `[REPO]` Screenshots

1–10 per localisation, JPEG or PNG, **no alpha channel**. Required: iPhone 6.9"
(1320 × 2868) and, if 0.1 says iPad ships, iPad 13" (2064 × 2752). Full table in
`STORE-REQUIREMENTS.md` §6.

2.3.2 requires screenshots to make clear that readings require purchase. The free
calculation is free and the prose is not, and the screenshots have to carry that
distinction rather than implying everything shown is included.

This is task #38's output. Decide 0.1 first — it is the difference between 60 images
and 120.

## B11. `[REPO]` The app icon

Delivered **in the build**, from the asset catalog or Icon Composer — not a separate
App Store Connect upload any more. Apple's current help page states no pixel
dimensions (`STORE-REQUIREMENTS.md` §6 marks this **UNSOURCED**); 1024 × 1024 is what
the asset catalog has historically required for the App Store slot. **Verify it in
Xcode's asset catalog inspector against this project** rather than trusting the number.

No transparency. Play's icon wants alpha and is a different file — do not export one
from the other.

## B12. `[OWNER]` Build, upload, TestFlight

Set `MARKETING_VERSION` and `CURRENT_PROJECT_VERSION` (`project.pbxproj:208,234` — both
currently `1.0` / `1`). Archive against the **Release** configuration so the build
points at `https://api.pazl.ai` and not at localhost.

Export compliance is already answered in the binary:
`ITSAppUsesNonExemptEncryption = false` in `mobile/ios/Info.plist`. No custom
cryptography, so the question does not reappear on every upload.

Install from TestFlight on a real device and walk `REVIEW-NOTES.md` §1 end to end,
including a sandbox purchase and a restore, before submitting. A reviewer finding a
broken purchase is a 2.1 rejection and a week.

## B13. `[OWNER]` Reviewer notes and demo fields

Paste `REVIEW-NOTES.md` §1, with the placeholders filled. Set **Sign-in required:
No** — see §3 for why that is both true and the better answer.

Attach a screen recording of the birth-time sensitivity check (same date and place,
04:20 and 06:20, two different rising signs). It takes eleven seconds and it is the
single most persuasive artefact available against 4.3(b).

## B14. `[OWNER]` Submit

Submit the app and the twelve in-app purchases **together**, in one submission. IAPs
submitted separately from a first version sit in "Waiting for Review" behind the app
and it is not obvious that they are blocked.

---

# C. Google Play, in order

## C1. `[OWNER]` Developer account and identity verification

Play now requires verified organisation details — legal name, address, D-U-N-S,
a verified contact. Verification has taken weeks for some organisations. Start it
before anything else in section C.

## C2. `[OWNER]` Confirm the two 31 August 2026 deadlines are met

Three weeks out at the time of writing, and a **first** submission after that date
must satisfy both.

- **Target API 36.** `mobile/android/app/build.gradle.kts:10` (`compileSdk = 36`) and
  `:15` (`targetSdk = 36`). ✅ in the repo — verify at upload.
- **Billing Library 8.** `mobile/android/gradle/libs.versions.toml:26` — `billing =
  "8.3.0"`. ✅ in the repo — verify at upload.

Both have an extension available to 1 November 2026 if something slips.

## C3. `[OWNER]` Payments profile — before the first sale

Play Console → Setup → Payments profile. Merchant account, tax details, bank account.
In-app products cannot be activated without it.

Note the asymmetry worth knowing (`STORE-REQUIREMENTS.md` §8): Play charges **15% on
auto-renewing subscriptions permanently, with no $1M cliff**, where Apple reverts to
30% above $1M. There is no Play equivalent of the Small Business Program to enrol in —
the 15%-under-$1M rate on one-time purchases is automatic.

## C4. `[OWNER]` App signing

Create the upload key, enrol in **Play App Signing**. `mobile/android/app/build.gradle.kts`
declares no `signingConfig` for the release build type today, so this is both an
`[OWNER]` key-generation step and a `[REPO]` wiring step.

Take the release certificate's SHA-256 fingerprint from Play Console → Setup → App
signing and use it for A8 (`assetlinks.json`). It is Play's key, not the upload key —
getting that wrong is the usual reason app links stay unverified.

## C5. `[OWNER]` Service account for the Play Developer API

`backend/alma/billing/googleplay.py:102` calls
`https://androidpublisher.googleapis.com/androidpublisher/v3` to verify every purchase
token. Without this, **no Android purchase grants anything**.

1. Google Cloud project, service account, JSON key. `[OWNER]` — it is a credential.
2. Link the Cloud project to Play Console (Setup → API access).
3. Grant the service account "View financial data" and "Manage orders and
   subscriptions" for this app.
4. Put the JSON in `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` (A2). The setting accepts either
   the credentials themselves or a path to a file holding them.

## C6. `[OWNER]` Real-time Developer Notifications

Create the Pub/Sub topic, set the push subscription to the backend, set the audience,
and put it in `GOOGLE_PLAY_PUBSUB_AUDIENCE` (A2). The audience is configured on our
subscription and nowhere else, which is the only thing that makes an unsigned
notification body ours — Google will mint a valid OIDC token for any of its customers.

**Resolve A3 first.** As the code stands, this endpoint and Apple's cannot both be
live on one deployment.

## C7. `[OWNER]` Create the products

Same id rule as Apple: catalogue key, `alma.` prefix, hyphens to underscores
(`mobile/android/app/src/main/kotlin/ai/pazl/alma/billing/StoreProducts.kt:11–27`).

- **In-app products (one-time):** the same ten as B5 — eight doors at $5.99,
  `alma.archive` at $38.99, `alma.archive_upgrade` at $33.00.
- **Subscription:** one subscription product with **two base plans** — monthly at
  $9.99 and annual at $78.99. Base plans are Play's equivalent of Apple's subscription
  group. No offers, no free trial, no introductory pricing.
- **Do not create `alma.archive_bump`.** Play is worse than StoreKit here: a Play
  product id exists in the console whether or not our server listed it, so a
  standalone `archive-bump` purchase would grant the full archive at $29.99. The app
  blocks it in `PlayBilling.purchase` via `StoreProducts.NEVER_ALONE`, but the
  cheapest defence is never creating it.

## C8. `[OWNER]` `[DECIDE]` Data safety form

Every answer is derived in `DATA-INVENTORY.md` §6, against **Play's** definitions —
which are not Apple's. Play has no "linked to you", no "used to track", and no
"Sensitive Info" bucket; it has "required vs optional" and per-type purposes, which
Apple does not. Fill each form against its own definitions; do not copy answers across.

Blocked on decision 0.6. Also required here:

- **Encrypted in transit: Yes.** HTTPS everywhere; the only ATS exception is scoped to
  `localhost` and `127.0.0.1` for the simulator (`mobile/ios/Info.plist`).
- **Users can request deletion: Yes** — plus the URL from A4.
- **Third-party SDKs count as our collection.** The honest note from
  `DATA-INVENTORY.md` §4: `play-services-*`, `datatransport` and `firebase-encoders`
  arrive **transitively behind Play Billing 8.3.0** and are declared nowhere in
  `libs.versions.toml` or `app/build.gradle.kts`. Nothing in our code calls them. If
  the form asks, that is the answer.

## C9. `[OWNER]` Account deletion declaration

Enter `⟨DELETE URL⟩` from A4 in the designated Play Console field, and confirm the
in-app route. Both are required and they are two different obligations. The in-app
route is
`mobile/android/app/src/main/kotlin/ai/pazl/alma/ui/screens/SettingsScreen.kt:565`.

## C10. `[OWNER]` `[DECIDE]` Content rating (IARC) and target audience

One questionnaire produces ESRB, PEGI, USK, ACB, ClassInd, GRAC and IARC Generic. We
ship to Brazil (ClassInd) and Germany (USK), whose thresholds differ from ESRB's.

**Read the questions in the console before answering.** Whether IARC asks about occult
or fortune-telling content could not be sourced from any Play help page
(`STORE-REQUIREMENTS.md` §12 marks it **UNSOURCED**), and it is directly relevant to a
divination app. Guessing is what that policy punishes as misrepresentation.

**Target audience: adults only.** Selecting any group under 13 pulls Alma into the
Families Policy Requirements. Selecting only "Ages 18 and over" also enables Restrict
Minor Access.

Policy declarations, all straightforward: no ads, no financial features, no news app,
no government affiliation, no health claims.

## C11. `[OWNER]` Store listing, six locales

App name ≤30, short description ≤80, full description ≤4,000. Feature graphic
1024 × 500, no alpha, **required**. Icon 512 × 512 PNG **with alpha**, ≤1024 KB —
a different file from Apple's. Phone screenshots 2–8 per device type.

Play's reviewers read the full description, and Spam / Minimum functionality are
judged partly from it. Lead with what the app computes — `REVIEW-NOTES.md` §7 is the
paragraph.

## C12. `[OWNER]` Test the purchase path with a licence tester

Play Console → Setup → License testing. Add the tester accounts, upload to internal
testing, and buy each rung end to end: door, archive, the upgrade after a door, both
base plans, and a restore.

Purchases are granted **server-side** after the backend verifies the token against the
Play Developer API, so an unlock lands a second or so after the sheet closes. If it
never lands, look at C5 before looking at the app: a missing or under-privileged
service account produces exactly this symptom — Google has taken money and our server
grants nothing.

## C13. `[OWNER]` Paste the App access instructions and release

`REVIEW-NOTES.md` §6, with `⟨DELETE URL⟩` filled. Answer **"All functionality is
available without special access."**

Roll out through internal → closed → production rather than straight to production.
A first release to production cannot be un-shipped, only superseded.

---

# D. After both are approved

1. `[OWNER]` **Verify the Small Business Program adjustment actually applied.** It
   starts fifteen days after the end of the fiscal month of approval, and it is the
   difference between 15% and 30% on everything before that date.
2. `[OWNER]` **Watch the first real purchase end to end** on each platform: sheet →
   `iap/verify` → entitlement written → chapter unlocked. Sandbox and production
   differ in exactly one way that matters, which is that production transactions are
   real.
3. `[REPO]` **Confirm renewals are being granted** without anyone opening the app.
   That is the A3 question, answered by observation a month after launch rather than
   by reading code.
4. `[OWNER]` **4.3(b) does not end at approval.** The guideline's own second sentence:
   *"We may remove these apps from the App Store going forward if they are not
   updated, improved, or do not attract customers."* Passing once is not a permanent
   state in this category. Ship something.

---

# What is missing from this checklist, and why

Three things a complete checklist would contain and this one deliberately does not,
because inventing them would be worse than naming the gap:

- **Exact Apple price points.** Apple's price tiers change, and matching
  `REGIONAL_CENTS` to them is a console exercise done with the console open. B5 says
  which direction to reconcile in.
- **A screenshot storyboard.** That is task #38's, and it depends on decision 0.1.
- **The web landing page's handoff to the stores.** Task #30. It affects the listing's
  marketing URL and the conversion path, not whether either submission passes.
