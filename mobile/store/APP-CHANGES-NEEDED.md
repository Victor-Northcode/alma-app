# Changes the store submission needs, in code nobody in this directory may touch

Written 7 August 2026, from three independent reviews of the submission packet against a
running backend, a simulator build and the repository.

**Why this file exists.** Two other teams are working in `mobile/ios/`, `mobile/android/`,
`backend/` and `src/` right now. Every finding below is real and most of them are small, but
editing those files from here would collide with work in flight. So the documents in
`mobile/store/` were corrected to describe **what ships today**, and everything that requires
a code change is collected here instead, with the file, the problem and the fix.

**The consequence of that choice, stated plainly.** Several store documents are now weaker
than they could be, on purpose — the listing enumerates a short free tier instead of claiming
a large one, and the reviewer notes tell App Review that deletion needs a sign-in. Each of
those is honest about the current build and each gets stronger the moment the corresponding
item below lands. Where that is true it says so, under **When this lands**.

Ordered by what blocks a submission, not by size.

| § | What | Where | Blocks |
|---|---|---|---|
| 1 | A guest cannot delete their account | iOS, Android, backend | **Apple 5.1.1(v)**, Play deletion policy |
| 2 | "Eight systems on nine axes" in the app and in the .storekit | `Alma.storekit`, `Screens.xcstrings` | **Apple 2.3.1**, and the 4.3(b) argument |
| 3 | The privacy policy says the name is not sent to Anthropic. It is | `LegalText.swift`, `privacy/page.tsx` | **Apple 5.1.2(i)**, GDPR Art. 13 |
| 4 | `PREVIEW_FIELDS` withholds the chart the 4.3(b) argument points at | backend | Nothing — but it is the cheapest win in the packet |
| 5 | The monthly subscription has two different names | `catalogue.py`, `PaywallL10n.swift` | Nothing formally; it misleads at the confirm sheet |
| 6 | The annual grants everything and the paywall row will not say so | `PaywallL10n.swift` | Nothing formally; it costs the $78.99 sale |
| 7 | Product-id prefix, and no build check that the ids agree | five files | **Unrecoverable** if the console is filled in first |
| 8 | Analytics posts unconditionally; no opt-out anywhere | iOS, Android | **Apple 5.1.1(ii)**, forces Play "Required" |
| 9 | `accounts.erase` leaves `buyer_email` behind | backend | GDPR Art. 17; the privacy page enumerates survivors and misses it |
| 10 | Export is narrower than erase | backend | GDPR Art. 15 |
| 11 | No retention limit, and nothing enforces one | backend | GDPR Art. 5(1)(e) |
| 12 | No lawful basis anywhere in any policy | `privacy/page.tsx`, `LegalText.swift` | GDPR Art. 13(1)(c), Art. 6, Art. 9 |
| 13 | Third-country transfer: two policies, three defects | `privacy/page.tsx`, `LegalText.swift`, `provider.py` | GDPR Art. 13(1)(f); Play's whole "Shared" column |
| 14 | Minimum age 16 is stated in three documents and enforced nowhere | `schemas.py` | Both age-rating questionnaires |
| 15 | "Three companies, and this is the complete list" is not complete | `privacy/page.tsx` | GDPR Art. 13(1)(e) |
| 16 | The consent row survives deletion and no policy says so | `accounts.py`, `privacy/page.tsx` | Accuracy of a policy that enumerates survivors |
| 17 | A second person's birth data is stored and never disclosed | `privacy/page.tsx` | GDPR Art. 14 |
| 18 | Small things: a loaded trap, a mail undercount, an unsourced EU claim | Android, iOS | Nothing on its own |

---

## 1. A guest cannot delete their account, and the reviewer is a guest

**Files.** `mobile/ios/Alma/Screens/Settings/AccountModel.swift:220-222` ·
`mobile/ios/Alma/Screens/Settings/SettingsScreen.swift:255-257, 318-329` ·
`mobile/android/.../ui/screens/SettingsViewModel.kt:241-243` ·
`backend/alma/api/routers/account.py:51, 62, 73-79` · `backend/alma/api/deps.py:95-107`

**The problem.** `beginDelete(isGuest:)` returns `.needsAccount`, which renders a "sign in"
prompt where the delete flow would be. The backend agrees twice over: `POST
/v1/account/delete` is behind `require_account`, which 401s any user with `provider='guest'`,
and `account.py:73` then requires the confirmation string to equal `user.email`, which a guest
does not have. `GET /v1/account/export` is behind the same dependency. None of it is a bug —
the guard exists so a mistap cannot destroy paid readings.

The problem is who it catches. `deps.py:61-91` mints a guest account on the first request from
any client; a checker confirmed end to end that `POST /v1/auth/session` with only an
`x-alma-anon` header returns a full working token with no credentials at all. A guest is the
product's **default and majority state**, and that account holds a birth date, a birth time to
the minute, a birthplace coordinate, a name, chat and a memory table. `REVIEW-NOTES.md` §3
recommends answering *"Sign-in required: No"*, which is correct — so App Review arrives as a
guest, holding exactly that account, unable to delete it.

> **LANDED 7 Aug 2026, both halves.** Backend: `account.py:51,68` take `CurrentUser` and a
> guest confirms with their account id — verified live, export and delete both HTTP 200 on a
> fresh guest token, token dead afterwards. iOS: `AccountModel.beginDelete` no longer routes a
> guest to a sign-in prompt and `SettingsScreen` shows the account id to type, since a guest
> has no address to remember. Android had already landed its half.
>
> The first version of this banner said LANDED when only the backend had — which is worse
> than no banner, because the packet's only Apple 5.1.1(v) blocker then looked closed on
> paper while the reviewer would still have met it on the phone. Kept with its reasoning
> rather than deleted, so a reader can tell a closed blocker from a forgotten one.

**The fix.** Let a guest delete and export against their bearer token; the token already
resolves to their row, so they are identified. Keep the confirmation gate but stop keying it
to an address they do not have: for an account with no email, confirm with a typed phrase or a
second destructive-action sheet. Concretely — change the `Account` dependency to `CurrentUser`
on both routes, and replace the `not user.email` rejection with a comparison against whatever
the client was told to type.

**When this lands.** Three documents get stronger in the same commit:
`REVIEW-NOTES.md` §1 loses its sign-in caveat paragraph (it is marked in the file);
`LISTING.md` returns "Sign in and you can export…" to a flat claim in all twelve blocks; and
the `/delete-account` page stops needing a paragraph about guests having no self-service route.

---

## 2. The cross-synthesis compares three systems. Two shipping strings still say eight

**Files.** `mobile/ios/Alma.storekit:116` · `scr.empty.lead` in
`mobile/ios/Alma/Resources/Screens.xcstrings`

**The problem.** `backend/alma/engine/synthesis.py:355-360` builds its `contributions` dict
from exactly three systems — natal, numerology, birth-card — and the axis loop reads only
those three. A checker ran `POST /v1/systems/synthesis` against the live backend with the
fixture birth and walked all nine returned axes: no fourth system ever appears in a signal.

As of this morning the submission answered the question three different ways at once. The
reviewer notes said three; all twelve store descriptions said eight; the `alma.synthesis`
product description said eight; and the app's own first screen said eight. `LISTING.md` is now
fixed in all twelve blocks and `check-listing.py` fails the build if the word returns. These
two are not:

- **`Alma.storekit:116`** — "where the eight systems agree and disagree". This string is
  uploadable to App Store Connect and is what a reviewer reads in the IAP list.
- **`scr.empty.lead`** — "Alma computes eight independent systems from a real JPL ephemeris —
  forty-one chapters in all — and shows you where they agree about you and where they do not."
  This is the first sentence on the first screen, in six languages, and it is the screen
  `EmptyArgument` exists to put the 4.3(b) argument on.

**The fix.** Either narrow both strings to three, or widen `contributions` to take signals from
the other five systems. Both are defensible; shipping both answers is not. Note that widening
the engine is the more valuable option if it is cheap — eight systems genuinely disagreeing is
a better product than three — but it must not be assumed. **Guideline 2.3.1** is metadata
accuracy, and the one claim a reviewer is most likely to open the app and verify is the one
that was overstated by 8/3.

`scr.empty.lead` can keep its eight: "Alma computes eight independent systems from a real JPL
ephemeris — forty-one chapters in all — and puts three of them side by side to show you where
they agree about you and where they do not." That preserves both true numbers.

---

## 3. The iOS privacy policy tells the reviewer the name is not sent. `writer.py` sends it

**Files.** `mobile/ios/Alma/Screens/Settings/LegalText.swift:303-307` (all six localisations) ·
the same passage in `src/app/(legal)/privacy/page.tsx`

**The problem.** The in-binary policy — the one Apple's reviewer opens, because
`PaywallView.swift:262-281` links to in-binary documents and Android opens the web page
instead (`SettingsScreen.kt:586-596`) — states that when a reading is generated *"Your chart
factors and the chapter's question are sent; your email address and your name are not."*

`backend/alma/ai/writer.py:152-164` builds the user turn as `- born {date} at {time}`,
`- birthplace: {place}`, `- name: {name}`. The name is appended verbatim, along with the birth
date, the birth time to the minute and the birthplace label. None of those is a chart factor.

**Guideline 5.1.2(i)** is specifically about disclosing what leaves the app and to whom, and
the name is the exact field this sentence names as not sent. Beyond App Review it is an
Art. 13(1)(e)/(f) failure: the categories transferred to a US processor are misdescribed in the
only notice shown inside the app. `REVIEW-NOTES.md:189-193` states it correctly, so the
submission currently contradicts itself.

**Two fixes, and the cheaper one is the better one.**

1. *Stop sending them.* `writer.py` already sends the computed factors. If the name and the
   raw birth fields can come out of the prompt, the sentence becomes true as written and the
   Art. 13 exposure disappears. Cost this first.
2. *Or say what the code does*, in all six locales and on the web page:
   "Anthropic, who run the model that writes the readings. What is sent is your calculated
   chart, your birth date, your birth time and birthplace, the name you gave if you gave one,
   your question, and the short facts Alma remembers about you. Your email address, your
   account id and the exact coordinates are not."

`PRIVACY-DELTA.md` has sixteen deltas of this kind across the two shipped policies. This one
is the worst and should not wait for the rest.

---

## 4. `PREVIEW_FIELDS` withholds most of the evidence the 4.3(b) argument rests on

**File.** `backend/alma/api/routers/systems.py:47-78`, applied at `:114-121`

**The problem, measured.** A checker called every system as a locked guest against the running
backend. A locked **natal** returns `sun_sign, moon_sign, rising_sign, moon_phase, balance,
time_known` and `factors: []` — no planets, no houses, no aspects, no angles. A locked
**astrocartography** returns `birthplace` and nothing else; the `lines` tuple the engine
computes (`engine/astrocartography.py:287-292`) is trimmed away entirely.

That is not a policy violation on its own. It became one because the copy claimed otherwise —
"Every calculation is free forever — the whole chart, the numbers, the lines…" — and the two
nouns it named were among the paid ones. `LISTING.md` and `REVIEW-NOTES.md` are now written to
the dict rather than to the comment at `entitlements.py:61-64`, which says calculations stay
free and is contradicted by the code that runs.

**Why to widen it anyway.** The file's own comments already make the argument twice, for
transits and for the synthesis axes: *"a count with no evidence reads as a horoscope feed, and
a cited chart factor does not"*, and *"the disagreement view is the thing that makes Alma
meaningfully different, so it cannot be the thing behind the paywall"*. Exactly the same
sentence applies to the natal bodies and to the astrocartography lines. The calculation costs
nothing — static local files — and a reviewer holding Guideline 4.3(b) who opens the natal
screen and finds three sign names is looking at something indistinguishable from a horoscope
app. What is sold is the writing.

**The fix.** Add the bodies, houses, aspects and angles to `PREVIEW_FIELDS["natal"]`, and
`lines` to `PREVIEW_FIELDS["astrocartography"]`.

**When this lands.** `LISTING.md`'s free list grows in all twelve blocks; `REVIEW-NOTES.md` §1
item 4 gets its house cusps back and becomes a three-part demo again; the `SCREENSHOTS.md`
slot 6 sub-caption becomes unambiguous; and the 4.3(b) reply in §4 of the notes gets its
strongest screen. Nothing anywhere has to be narrowed. Of everything in this file, this is the
change with the best ratio of argument gained to work done.

---

## 5. The monthly subscription has two names

**Files.** `backend/alma/billing/catalogue.py:630` ·
`mobile/ios/Alma/Localization/PaywallL10n.swift:63` (`monthlyTitle`, six languages)

**The problem.** Both say **"Everything live, monthly"** (de: "Alles Lebendige, monatlich").
`PRODUCTS.md` §3.4 specifies the App Store Connect / Play display name as **"What moves,
monthly"** and argues at length that it must not be an everything-claim, because the monthly's
scope is `"live"` and not `"all"`. Every other rung agrees across the two files.

Two consequences, both the buyer's. Apple's confirmation sheet and the iOS *Manage
Subscriptions* list use the App Store Connect name, so a person taps one name and is asked to
authorise a recurring charge under another — then later hunts the cancellation list for a name
that is not there. And the in-app name is the everything-claim, sitting one row above
"Everything, for a year": two rows both promising everything, at $9.99 and $78.99.

**The fix.** Adopt `PRODUCTS.md`'s name in all three places. The six strings:

| | `monthlyTitle` |
|---|---|
| en | What moves, monthly |
| es | Lo que se mueve, cada mes |
| de | Was sich bewegt, monatlich |
| it | Ciò che si muove, ogni mese |
| fr | Ce qui bouge, chaque mois |
| pt-BR | O que se move, todo mês |

---

## 6. The annual row will not say what a year buys

**File.** `mobile/ios/Alma/Localization/PaywallL10n.swift:69-72` (`annualNote`)

**The problem.** `annualNote` is *"Renews every year until you cancel. Cancel any time in your
Apple ID settings."* — renewal mechanics and nothing else. Its only content signal is the title,
"Everything, for a year". The monthly row directly above does the opposite: `monthlyNote` lists
the three live systems and the 40-question cap.

`AlmaStore.swift:472-488` puts the door, the archive and both plans on one screen, so a buyer
is comparing "The whole archive · $38.99" against "Everything, for a year · $78.99" with
nothing on the annual row telling them the year contains the archive. It does —
`catalogue.py:215` gives `annual` `scope="all"` — but the safe read is "a rental of the same
thing at twice the price", which pushes the buyer down to the archive or off the screen.
`PRODUCTS.md:275-277` already states why "12 months" must appear in the store description; the
app's own row is the surface people actually read before tapping.

**The fix.** Give `annualNote` the shape `monthlyNote` has:
"All 41 chapters and everything live, for twelve months. Renews every year until you cancel."
(de: "Alle 41 Kapitel und alles Lebendige, zwölf Monate lang. Verlängert sich jedes Jahr, bis
du kündigst.") The Apple-ID sentence is redundant — `autoRenewTerms` already sits immediately
above the button (`PaywallView.swift:173`).

**Related, same file.** `paywall.doorSub` and `journey.offerSub` open with *"The numbers above
are yours and stay free"* and there are no numbers above them on either screen where they
render: `StepOffer` (`JourneyCloseSteps.swift:47-56`) draws the art, the title and the
subtitle, with the portrait a step behind; `OfferScreen.swift:37` puts `PaywallView` inside
`ScreenScaffold`, which renders only an eyebrow and a title above the content. Reached from a
locked chapter — the commonest route — there has never been a number on the screen. It is the
first sentence on the screen where money is decided, and it points at nothing. Make it
self-contained: *"Your chart, your numbers and your positions stay free. This opens the whole
system — every chapter of the reading, written from your positions, not a template."* Same edit
in all six languages in `Paywall.xcstrings` and `Journey.xcstrings`.

---

## 7. The product-id prefix, and nothing that makes a half-done rename fail

**Files.** `backend/alma/config.py:251` · `mobile/ios/Alma/Billing/LadderKey.swift:115` ·
`mobile/android/.../billing/StoreProducts.kt:57` · `mobile/ios/Alma.storekit` ·
`backend/alma/billing/catalogue.py` (`processor_ids`)

**The problem.** The binary asks StoreKit for products under `alma.`. `PRODUCTS.md` §2 hands
the owner a paste-ready set under `ai.pazl.alma.` and recommends adopting it. Nothing forces
the two to be reconciled before somebody starts typing into App Store Connect.

If the console is filled in from `PRODUCTS.md` while the binary still ships `alma.`, then
`Product.products(for:)` returns an empty set, the paywall renders with no rows, and the build
comes back as **Guideline 2.1 — "we were unable to locate the in-app purchases"**. And it
cannot be corrected, because neither store permits a product id to be changed or reused. This
is the only mistake in the packet that is unrecoverable rather than merely a resubmission.

**The fix, in two parts.** The owner decides the prefix before the first product is saved —
that is item 1 on the list in `README.md`. Then one commit changes all five files together;
`Alma.storekit` is the one that gets forgotten, and a rename that misses it leaves the
simulator selling ids the binary does not ask for.

And make the build enforce it: a test asserting that the set of `productID`s in
`mobile/ios/Alma.storekit` equals `LadderKey.allStoreProductIDs`, with an Android equivalent
against `StoreProducts`. A half-done rename then fails CI instead of failing review.

---

## 8. Analytics posts unconditionally, on both platforms, with no opt-out

**Files.** `mobile/ios/Alma/Networking/AlmaClient.swift:310-318` ·
`mobile/android/.../data/AlmaClient.kt:280-281`

**The problem.** `track` posts every funnel beacon to `POST /v1/events` with no gate, no
setting and no Settings row that suppresses it. Meanwhile:

- `mobile/ios/Alma/PrivacyInfo.xcprivacy` declares `NSPrivacyCollectedDataTypeUserID` and
  `ProductInteraction` with `NSPrivacyCollectedDataTypePurposeAnalytics`;
- `LegalText.swift:292-293` tells iOS users *"There is nothing to opt out of because there is
  nothing running"*, which is false while nine beacons post;
- `privacy/page.tsx:104-108` promises DNT/GPC suppression — true on the web
  (`src/lib/track.ts:211-213`) and with no phone equivalent — and Android's Settings opens
  that very page (`SettingsScreen.kt:590-595`);
- `DATA-SAFETY.md:110` concedes that Play's *App interactions* row must therefore be
  **Required** rather than Optional.

**Guideline 5.1.1(ii)** asks for an accessible way to withdraw consent for collected usage
data. The app declares an analytics purpose in its own manifest and provides no control. Under
GDPR it also removes the objection right (Art. 21) that a legitimate-interest basis would need
— see §12.

**The fix.** One Settings toggle, default on, short-circuiting `track` before the POST, on both
platforms. It resolves the Apple consent point, lets the Play answer become Optional, makes
`LegalText.swift:292-293` true, and lets the DNT sentence stand on both platforms. Until it
ships, `REVIEW-NOTES.md` §11 correctly forbids writing any sentence about an analytics opt-out
into either store's notes — and `LegalText.swift:292-293` should be deleted rather than left
standing.

---

## 9. `accounts.erase` leaves the buyer's email address behind

**File.** `backend/alma/auth/accounts.py:360-364`

**The problem.** A checker ran `accounts.erase` against a real SQLite database with a full
fixture. `purchase.user_id` came back `None` and both payloads were redacted — and
`purchase.buyer_email` read back as `'sofia@example.com'` verbatim. The update sets only
`user_id=None, payload=_REDACTED`; `Purchase.buyer_email` (`models.py:294`) is never touched.

The function's own docstring at `:333-334` says what survives is "nothing that says who entered
into it", and `privacy/page.tsx:220-229` tells the public that what is left is "a date, an
amount, a currency, a country and the processor's reference". Both statements are false. The
column is populated by web checkouts (`paddle.py:263`, `dodo.py:475` via
`billing.py:1253-1254`); the Apple and Play adapters write `None` (`appstore.py:531`,
`googleplay.py:638`), so this bites web buyers who later delete.

An erasure that leaves a direct identifier is not an erasure under Art. 17, and the policy
enumerates the survivors and omits this one — so it is simultaneously a failed deletion and a
false statement. It is the same class of defect already found and fixed here once (the verbatim
webhook payloads); that fix stopped one column short.

**The fix.** Add `buyer_email=None` to the `Purchase` update at `:361-364`. If the address is
needed for the renewal-notice lookup (`renewals.py:200-206`), note that the lookup is for live
subscriptions, which an erased account does not have. Then re-run the erase test and confirm
every column on the surviving row is non-identifying.

---

## 10. The export returns less than the erase deletes

**File.** `backend/alma/auth/accounts.py:220-321` (`export`) against `:324-390` (`erase`)

**The problem.** `export` returns profiles, entitlements, readings, conversations, memory,
purchases and the account row. `erase` additionally reaches `Consent`, `UsageCounter`, `Event`
(via `funnel.forget`) and `MagicLink` — four categories the product holds, admits to holding on
the privacy page (`:44-60` covers counters, consent statements and step labels explicitly), and
does not hand back. The export also omits `Purchase.buyer_email` and `Profile.place_id`.

Art. 15(1) is "all personal data concerning him or her". The function's own docstring says "an
export that quietly omits the readings they paid for is not an export" and then omits four
other tables. `models.py:13-18` names the erase list as the authoritative inventory of where a
person's data lives, so the gap between the two lists is the size of the shortfall.

**The fix.** Add consents, counters and funnel events to the export payload, and drive both
functions from one shared list of tables so the next table added to one is added to the other.
A test asserting that every table named in `erase` appears in `export` makes it structural.

---

## 11. There is no retention limit and no code that enforces one

**Files.** `backend/alma/` (no purge job exists) · `src/app/(legal)/privacy/page.tsx:243-249`

**The problem.** A grep of the whole backend for a purge, prune, retention or age-out job finds
nothing: the only `__main__` entry points in the package are `funnel.py:469`,
`billing/renewals.py:308` and `billing/withdrawal.py:211`. Nothing deletes an old `Event` row,
an old `Reading`, an expired `Memory` (`models.py:508` has an `expires_at` column that nothing
reads), or an abandoned guest account. The privacy page answers "How long it is kept" with
"While your account exists" — and a guest account exists forever and, per §1, cannot be deleted
by its owner. The one concrete number on the page, the backup window at `:247`, is a `<Blank>`.

Art. 5(1)(e), storage limitation. In practice: somebody who tried the app once as a guest has
their birth time, birthplace coordinate and any chat they typed held indefinitely, with no
expiry and no self-service route. "While your account exists" reads as a limit and is not one.

**The fix.** Pick and implement two numbers — an inactivity window after which a guest account
with no purchase is erased through `accounts.erase`, and a retention period for `Event` rows
independent of the account — and wire both as `python -m alma.retention` alongside
`renewals.py`. Fill `privacy/page.tsx:247` with the host's actual backup cycle before either
store form is filed; the `/delete-account` page Play requires is read as the deletion promise
and cannot ship with a blank where the one place deleted data survives should be.

---

## 12. No lawful basis appears anywhere in any shipped document

**Files.** `src/app/(legal)/privacy/page.tsx` · `mobile/ios/.../LegalText.swift` ·
`src/lib/legal.ts`

**The problem.** A grep across both policies and `legal.ts` for "lawful basis", "legal basis",
"legitimate interest", "Art. 6", "Article 6", "special categor" and "Art. 9" returns zero hits
outside an unrelated CRD Art. 6(1)(h) comment in `refunds/page.tsx:278` and an Italian
consumer-code reference in `LegalText.swift:28`. The page explains why each field exists and
never states the basis for any of it, and never addresses Art. 9 at all — despite storing an
exact birth time, a birthplace coordinate, unfiltered 2000-character chat
(`models.py:474-488`, `schemas.py:172`) and a `memory` table of what the model extracted from
that chat (`models.py:491-508`).

Analytics is the sharpest gap: funnel events are written for every account including guests,
with no consent step anywhere, which is neither contract-necessary nor covered by any consent
this product collects — and per §8 there is no opt-out, which makes legitimate interest hard to
argue. The Art. 9 exposure is not theoretical: the project has already reasoned that beliefs
and health may land in the chat field (it declares Sensitive Info on Apple's manifest and "No"
on Play's beliefs row) and has no Art. 9(2) condition for them.

**The fix.** Add a "Why we are allowed to hold this" section mapping each category to a basis:
contract for birth data, readings, entitlements and purchases; legal obligation for the payment
record; explicit consent (Art. 9(2)(a)) for anything typed into chat or memory, collected at
first use of chat rather than assumed. Analytics needs consent or a documented
legitimate-interest balancing test, and §8 first.

---

## 13. Third-country transfers: two policies, three defects, and they contradict each other

**Files.** `src/app/(legal)/privacy/page.tsx:143-147` · `LegalText.swift:328` ·
`backend/alma/ai/provider.py:86`

1. The web page ships with both blanks unfilled: *"Where those companies hold data, and under
   which transfer terms, is being confirmed: `<Blank>`. Alma itself is hosted in `<Blank>`."*
2. `LegalText.swift:328` asserts **"On servers in the European Union"** — an unqualified factual
   claim the web page declines to make. One of the two is wrong and nothing in the repo settles
   it. Related and handled well: `Alma.xcodeproj` sets the Release `ALMA_API_BASE` to
   `https://api.pazl.ai.INVALID-SET-THIS-BEFORE-TESTFLIGHT` and a build phase hard-fails the
   archive on the placeholder — so it cannot ship by accident, but it does confirm that no
   production host has been chosen, which is what the EU sentence asserts.
3. `provider.py:86` constructs `AsyncAnthropic(api_key=key)` with no `base_url`, so every
   generation goes to `api.anthropic.com` in the US carrying the birth date, birth time,
   birthplace, name (`writer.py:152-164`), the last twelve chat messages verbatim
   (`conversation.py:128-133`) and the remembered facts (`voice.py:112-119`). No Art. 46
   safeguard is named anywhere.

Art. 13(1)(f) requires the fact of the transfer, the mechanism, and how to get a copy of the
safeguards. A blank is not a disclosure, and an EU-hosting claim in the binary sitting next to
a US model call reads as a representation rather than an oversight.

**The fix.** Confirm the Anthropic and Resend DPAs and their transfer mechanism before either
store form is filed, then fill `privacy/page.tsx:144-146`. Either substantiate
`LegalText.swift:328` or replace it with the web page's sentence. If the Anthropic DPA does not
exist, four rows on Play's Data safety form flip to "Shared: Yes" and the "not used to train
anyone's model" sentence at `privacy/page.tsx:160-163` cannot stay. Keep the `ALMA_API_BASE`
build guard exactly as it is.

---

## 14. The minimum age is stated in three documents and enforced nowhere

**File.** `backend/alma/api/schemas.py:63-70`

`src/lib/legal.ts:65` says 16, and `privacy/page.tsx:252-257` and `LegalText.swift:362-366`
repeat it. The validator accepts any birth date whose year falls between 1900 and 2100 — the
only check is that the ephemeris covers it — and no screen asks. The app will compute and sell
a chart for a birth date in 2018.

The number filed on both age-rating questionnaires, the number in three legal documents and the
number the code enforces have to be the same number; today two of three agree. A children's-data
finding is the one category where both stores and every supervisory authority escalate rather
than ask for a correction.

**The fix.** Reject a `birth_date` for a *self* profile that is under `MIN_AGE` at the point of
entry, with a message that says why. One line next to the existing range validator, and the app
already holds the datum. It is the cheapest item in this file.

---

## 15. "Three companies, and this is the complete list" is not the complete list

**File.** `src/app/(legal)/privacy/page.tsx:112`

The sentence names Anthropic, MERCHANT and Resend. It omits the hosting provider — which the
iOS text *does* name, as a fourth recipient (`LegalText.swift:316-318`) — and it omits Apple
and Google. MERCHANT resolves from `NEXT_PUBLIC_BILLING_PROVIDER` to "Paddle.com Market Ltd" or
"Dodo Payments" (`src/lib/legal.ts:44-51`), while inside the apps Apple and Google are the
merchants of record (`LegalText.swift:49` hard-codes `merchant = "Apple"`). This is the page
Android opens for "Privacy" and the URL that goes on the Play listing, so a Play reviewer
following the link from a Google-billed app finds Paddle named as the seller and Google absent.

Art. 13(1)(e) asks for the recipients or categories of recipients. A sentence that says "this is
the complete list" and is not complete is worse than a vague one, and the two shipped policies
disagree about the count — three on the web, four on iOS.

**The fix.** Make the web list four categories and name the store: hosting provider, model
provider, payment processor (naming Apple and Google for app purchases and the card processor
for the web), and mail provider. Read the merchant from the API's `merchant` field rather than a
build-time constant on any page a store app can reach.

---

## 16. A third thing survives deletion and the page says two

**Files.** `backend/alma/auth/accounts.py:370-374` · `src/app/(legal)/privacy/page.tsx:220-229`

The page says "Two things survive" — the payment record and the account stub. Running erase
showed a third: `accounts.py:370-374` *detaches* rather than deletes any `Consent` row carrying
a `transaction_id`, and a checker's run left exactly one standing. It holds `statements` — the
exact sentences the person ticked — plus the locale they read them in, the product key and
`agreed_at`. Nothing on the page mentions it surviving; `:53-56` discusses consent records only
to say the unpaid ones are deleted. Counting `buyer_email` from §9, the true number is four.

The page goes out of its way to enumerate the survivors — the comment block at `:211-219` says
the previous version of this paragraph was wrong and this one is right — so an unlisted survivor
is a specific, checkable misstatement. Keeping the row is defensible; it is the CRD Art. 16(m)
evidence. Keeping it undisclosed is not.

**The fix.** Change "Two things survive" to three and add a sentence: the record of what you
agreed to at a checkout stays, detached from your account, because it is part of the same
contract as the payment. Fix `buyer_email` per §9 so the count is genuinely three.

---

## 17. The policy never mentions that Alma stores a second person's birth data

**File.** `src/app/(legal)/privacy/page.tsx`

The privacy policy is written entirely in the second person. `Profile` (`models.py:134-164`)
carries name, relation, birth_date, birth_time, coordinates and place for anyone a user compares
themselves against, and compatibility requires a second birth. `DATA-SAFETY.md:60` concedes it:
"The profile name may be a third party's … and nothing asks whether that person consented." The
only trace on the policy page is the plural in "every profile with its birth data" at `:202-204`.

Art. 14 governs data not obtained from the data subject and requires notice to that person, with
a lawful basis of its own. The data in question is a second individual's exact birth time and
birthplace — the most identifying pair in the product. The store forms describe this correctly;
the policy the user actually reads does not mention it.

**The fix.** Add a section on comparing with someone else: what is stored about them, that they
are not told, that the person entering it is responsible for having their agreement, and that
deleting the profile deletes their data. Consider a one-line acknowledgement on the add-person
screen — it costs nothing and it is the only record that a basis was asserted.

---

## 18. Three smaller ones

**A loaded trap on Android.** `AlmaClient.kt:124-125` is
`suspend fun deleteAccount(): ApiResult<JsonObject> = call { service.deleteAccount() }.also { tokens.clear() }`.
`AlmaService.deleteAccount()` (`AlmaService.kt:106-107`) sends no body, so
`POST /v1/account/delete` answers 422 before it reaches the confirmation check — and
`.also { tokens.clear() }` runs regardless of the result, so the caller is signed out and shown
a fresh guest while nothing was deleted. The settings screen does not use it
(`SettingsViewModel.kt:247` goes through `AccountDeleter`, which does send the body —
`AccountDeletion.kt:69-84`), so this is a trap rather than a live defect. The next person wiring
a delete button reaches for the method on the client, not the separate class, and the failure is
invisible. **Fix:** delete `AlmaClient.deleteAccount` and `AlmaService.deleteAccount`, or give
the service the `@Body` parameter and fold `AccountDeleter` back in. Either way `tokens.clear()`
must be inside the success branch, never in an `.also`.

**The iOS policy undercounts the letters we send.** `LegalText.swift:313-315` says the mail
provider carries "the two letters Alma sends: a sign-in link, and — for a plan bought outside
the App Store — a notice before a renewal." `backend/alma/mail.py` has three senders:
`send_magic_link` (`:115`), `send_renewal_notice` (`:220`) and `send_receipt` (`:928`), the last
with localised subjects in all six languages. The web page was already corrected for this — the
comment at `privacy/page.tsx:129-133` says so and lists all three — and the iOS copy was not.
**Fix:** make it three and name the receipt, matching `privacy/page.tsx:134-141`.

**The App Store icon.** Apple's current help page gives no pixel dimensions and says only that
the icon comes from the build. Verify 1024×1024 in Xcode's asset-catalog inspector against this
project before archiving; `SUBMISSION-CHECKLIST.md` carries it as a step.

---

## What is *not* in this file

Findings that were about the documents in `mobile/store/` have been fixed in place rather than
collected here. For the record, so nobody looks for them twice:

- "All eight systems on nine axes" in all twelve store descriptions — fixed in `LISTING.md`,
  and `check-listing.py` now fails the build on the pattern in all six languages.
- "Every calculation is free forever — the whole chart, the numbers, the lines" — replaced in
  all twelve blocks with an enumeration transcribed from `PREVIEW_FIELDS`.
- "A subscription writes to you three days before every renewal" — replaced in all twelve
  blocks with what the store does and what Alma does conditionally, using the app's own shipped
  strings (`cab.plan.renewsAtStore`, `cab.plan.renewsNoEmail`, `cab.settings.lettersNoteStore`).
- "Cancels from Settings" (Apple) and "cancelled from inside the app" (Play) — replaced with the
  Apple ID settings and the Google Play account, per `cab.managedByApple` and
  `StoreProducts.kt:178`.
- "The subscription does not buy the 41 archive chapters" — `REVIEW-NOTES.md` now distinguishes
  monthly (`scope="live"`) from annual (`scope="all"`).
- The §1 script's first screen, the birth-time demo, and the deletion paragraph — corrected
  against a simulator and a live backend.
- The Play descriptions were missing "it is not how the app is unlocked" — added in all six.
- `APP-PRIVACY.md` said eight types where the manifest declares nine — corrected to nine types
  in eight categories.
