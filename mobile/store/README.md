# `mobile/store` — everything that goes into App Store Connect and Play Console

Eleven documents and one script. Between them they hold every field, answer, price, string
and paragraph the two submissions need, each one traceable to a file and a line in this
repository rather than to somebody's memory of what the product does.

Read this page first. It has three parts: **what only you can do, in order**, then **what
state each document is in**, then **the rules the whole directory is written to**.

---

# 1. What the owner must do, in the order it has to happen

You have both developer accounts and the entity is Pazl LLC, so the account-opening work is
behind you. What is left is nine things, and the first four block everything after them.

### ① Create the domain. Nothing can be filed until this is done.

`nslookup alma.pazl.ai` → **NXDOMAIN**. `nslookup api.pazl.ai` → **NXDOMAIN**. Only the apex
`pazl.ai` resolves, to `95.81.101.52`. Checked 7 August 2026, from a shell where `apple.com`
answered fine.

Both names are compiled into the shipped builds — `alma.pazl.ai` is the deep-link host in
`AndroidManifest.xml:41` and the `Site` constant in `SettingsScreen.kt:724`; `api.pazl.ai` is
the Release API host. Every legal URL printed in all twelve store descriptions points at the
first one. **Apple fetches the Privacy Policy URL during review and rejects on a dead link
before anybody opens the build**, so this is not launch work, it is prerequisite work.

The two pages this document used to list as missing — **`/support`** (a required App Store
Connect field that must reach real contact information) and **`/delete-account`** (a Play
Console field that is validated, and will not accept a submission without a reachable
resource) — are **built and return 200**, checked 7 August 2026. They are
`src/app/(legal)/support/page.tsx` and `src/app/(legal)/delete-account/page.tsx`, and the
URLs to file are `https://<host>/support` and `https://<host>/delete-account`. That leaves
the host as the only thing between these fields and being fileable: a correct path on a name
that does not resolve is as unusable to a reviewer as no page at all.

### ② Decide the product-id prefix. This is the one irreversible decision in the packet.

The binary asks StoreKit for `alma.natal`, `alma.archive`, `alma.monthly` and the rest
(`LadderKey.swift:115`). `PRODUCTS.md` §2 recommends `ai.pazl.alma.` and hands you the
paste-ready set.

Either answer is fine. **What is not fine is typing one into a console while the binary asks
for the other** — `Product.products(for:)` returns an empty set, the paywall renders with no
rows, and the build comes back as Guideline 2.1 *"we were unable to locate the in-app
purchases"*. Neither store lets a product id be changed or reused, so the recovery is a
second set of products and a migration for everybody who already bought. It is the only
mistake here that cannot be fixed by resubmitting.

Decide, then land all five files in one commit (`config.py:251`, `LadderKey.swift:115`,
`StoreProducts.kt:57`, `Alma.storekit`, and the `processor_ids` pins in `catalogue.py`) with
a build assertion that the `.storekit` ids equal `LadderKey.allStoreProductIDs`.

### ③ Book the engineering time for four code fixes that block or badly weaken review.

These are not decisions, they are work, and they are in files two other teams are editing
right now. All four are in `APP-CHANGES-NEEDED.md` with the file, the line and the fix.

| | What | Why it cannot wait |
|---|---|---|
| §1 | **Let a guest delete their account.** | Guideline 5.1.1(v). The reviewer *is* a guest — we tell Apple no sign-in is required, which is true — so App Review will be holding an account containing a birth time and a birthplace coordinate that it cannot delete. |
| §2 | **Two strings still say the cross-synthesis compares eight systems.** It compares three. | `Alma.storekit:116` uploads to App Store Connect; `scr.empty.lead` is the first sentence on the first screen. Guideline 2.3.1, on the exact claim the 4.3(b) case rests on. |
| §3 | **The iOS privacy policy says the name is not sent to Anthropic. `writer.py:164` sends it.** | Guideline 5.1.2(i) names that field. The reviewer notes say the opposite, correctly — so the submission contradicts itself, one tap apart. |
| §8 | **Ship an analytics opt-out toggle.** | Guideline 5.1.1(ii). The privacy manifest declares an Analytics purpose and the app offers no control; it also forces Play's *App interactions* answer to Required. |

One more that is not a blocker and is the best-value change in the file: **§4, widen
`PREVIEW_FIELDS`**. A locked natal chart currently returns three sign names, a moon phase and
a balance — no bodies, no houses, no aspects — and a locked astrocartography returns only the
birthplace. That is the screen a reviewer holding 4.3(b) opens. Freeing it costs nothing (the
calculation is local files) and makes the store copy, the reviewer notes and the screenshots
all stronger at once. The code's own comments already argue for it twice.

### ④ Answer the four content-rating questions.

They decide 4+ versus 9+ versus 16+, and none of them can be answered from the repository.
`SUBMISSION-CHECKLIST.md` §0.2–0.5, `REVIEW-NOTES.md` §13.

- **Health or Wellness Topics** — natal chapter X is "Work and rhythms: what pace can I
  sustain?" and chapter VII is "Shadow and wound". Any non-None answer gives 9+. This is the
  single answer most likely to move Alma off 4+.
- **Horror/Fear Themes** — does the birth-card system draw Death and the Tower as *imagery*,
  or only name them in text? Imagery makes Infrequent arguable. Depends on what task #38 renders.
- **Mature or Suggestive Themes** — how explicit compatibility gets. Infrequent 9+, Frequent 16+.
- **Play's IARC questionnaire** may ask about occult or fortune-telling content. Neither Play
  help page enumerates the questions; they are only visible in the console. Read them and
  answer what is there — misrepresentation is what that policy punishes.

### ⑤ Answer the three privacy questions that block the store forms.

- **Are there DPAs with Anthropic and Resend?** Play's entire "Shared" column rests on the
  service-provider carve-out, which rests on these. Without a DPA the honest answer flips to
  Yes for four rows, and Anthropic receives birth date, birth time to the minute, birthplace,
  name and the last twelve chat messages. **Do not file Data safety until this is answered.**
- **Where is the backend hosted, and what does the host keep in access logs, for how long?**
  It decides three answers currently marked contingent, and it decides which of the two
  shipped policies is wrong — the iOS text asserts "servers in the European Union" and the web
  page leaves the region blank. The birthplace search travels as a URL query string
  (`api/routers/places.py:17-27`), so it lands in any default access log.
- **Does birth data go in Apple's "Sensitive Info"?** The recommendation is Yes and the
  shipped manifest already says Yes. Apple's public page does not enumerate the category, so
  the in-console definition is operative and must be read at fill-in time. Whichever way it
  goes, the console answer and `PrivacyInfo.xcprivacy` change in the same sitting.

### ⑥ Decide iPad, before any screenshot is rendered.

`project.pbxproj:214,240` declares `TARGETED_DEVICE_FAMILY = "1,2"`, so as things stand an
iPad set is required — roughly 120 images instead of 60. iPhone-only is a one-line change but
it has to happen before task #38 starts rendering. `SCREENSHOTS.md` is written so the answer
drops in without restructuring.

### ⑦ Settle the two prices that are internally inconsistent.

- **`archive-bump` at $29.99.** The comment at `catalogue.py:187-192` justifies the price with
  "899 + 2999 = 3898 is one cent under the shelf", but `_DOOR_CENTS = 599`, so the live sum is
  $35.98 against a $38.99 archive — $3.01 under, not one cent. It is not created in either
  store, so it does not block submission, but the web checkout charges it. Either the price or
  the reasoning is stale.
- **The nine `archive-upgrade` price points** ($33.00, A$50.00, kr 370, kr 250, R$85.00,
  MX$360.00, 72.00 zł, ₺430.00, ₹720.00). That band is derived by subtraction rather than
  chosen, so it is the only one landing off local price convention, and Apple's fixed grid may
  not carry all nine. Whatever moves has to be written back into `REGIONAL_CENTS` in the same
  commit, or `catalogue.py:483` states a credit the buyer is not given.

### ⑧ The account work that is not retroactive.

Three things cost money or credibility rather than time if they are done late, so do them
before the first build is uploaded: **Small Business Program enrolment** (Apple's reduced
commission is not backdated), the **Play payments profile**, and confirming the **DE440s
kernel is actually on the production host** — `ephemeris.py:66-84` silently falls back to
DE421 when `backend/data/de440s.bsp` is missing, and the store copy claims DE440s in six
languages. `SUBMISSION-CHECKLIST.md` A6, B3, C3.

### ⑨ Fill the six blanks in the reviewer notes.

Review contact, support URL, privacy URL, deletion URL, version string, and — only if you
want a pre-seeded demo account rather than the typed birth — a mailbox and password.
`REVIEW-NOTES.md` §0. The recommendation on the last one is *don't*: Alma has no password, so
a working demo account means handing App Review a live mailbox, forever, against a
twenty-second form that produces a real computed chart in front of them.

---

# 2. The documents, and what state each is in

| File | What it is | State |
|---|---|---|
| **`README.md`** | This page. | — |
| **`APP-CHANGES-NEEDED.md`** | Eighteen findings that need code, not documents: file, problem, fix. Ordered by what blocks a submission. | **New, 7 Aug.** Nothing in it has been done. Four items block review. |
| **`LISTING.md`** | All 42 store fields in six languages — Apple name, subtitle, promotional text, keywords, description; Play short and full description. | **Paste-ready.** 42/42 within limit; `check-listing.py` exits 0 including four content guards. Two sentences are deliberately understated pending `APP-CHANGES-NEEDED.md` §1 and §4, and say so. |
| **`PRODUCTS.md`** | Twelve products mapped to both stores: ids, types, 144 name/description strings in six languages, exact per-currency prices for 13 currencies, subscription group and levels, the paste-ready `processor_ids` dict. | **Paste-ready except the prefix**, which is owner item ②. Three things must be checked in-console before saving: the prefix, the monthly's display name, and what a product page lists. |
| **`REVIEW-NOTES.md`** | What we say to each store's reviewer. An English paste block for Apple's *Notes for Review*, a Play *App access* block, a file:line table under every sentence, and the three likeliest rejections with the reply to each. | **Paste-ready**, with two paragraphs marked to be rewritten if the code lands first. §14 now records seven claims corrected before a reviewer saw them. |
| **`SUBMISSION-CHECKLIST.md`** | Every step in order, marked `[OWNER]` / `[REPO]` / `[DECIDE]`, from nothing configured to both stores reviewing. | **Current.** Now opens on 0.0 (the domain), 0.0b (the prefix) and 0.0c (guest deletion), and carries new steps A0 and A3b. |
| **`SCREENSHOTS.md`** | Six shots in order, with the screen and Swift file each comes from, the state the app must be in, what must be visible and what must not; captions in six languages, mostly reused from shipped i18n strings; exact dimensions for both stores. | **Ready to render**, pending owner item ⑥. Slot 6's sub-caption carries a note to re-read against `PREVIEW_FIELDS` first. |
| **`APP-PRIVACY.md`** | Apple's App Privacy questionnaire filled in: all 14 categories, every subtype, with collect / linked / tracking / purposes and a file:line per row. | **Ready to type**, except the Sensitive Info row (owner item ⑤) and two rows contingent on the hosting answer. Corrected to nine types in eight categories. |
| **`DATA-SAFETY.md`** | Play's Data safety form against Play's own definitions — not a relabelled copy of Apple's. Plus the spec for the deletion URL page. | **Blocked on the DPA question.** Every "Shared: No" rests on it. |
| **`DATA-INVENTORY.md`** | The source both privacy forms are derived from. Every field the product stores, where it is written, where it goes, what deletion removes. | Current. Read it before touching either form. |
| **`PRIVACY-DELTA.md`** | Sixteen places where the two shipped privacy policies disagree with what we are about to declare — the exact sentence, the code that contradicts it, and a replacement. | Current, **and none of it is fixed yet.** The worst one is `APP-CHANGES-NEEDED.md` §3. |
| **`STORE-REQUIREMENTS.md`** | What the stores actually require, quoted from the live rule pages with URLs, marked UNSTABLE where litigation is moving a rule and UNSOURCED where no authoritative page could be found. | Current. Note that `PRODUCTS.md` §0 corrects its character limits: 30/45, not 35/55. |
| **`check-listing.py`** | Parses every field marker in `LISTING.md`, counts characters (bytes for the keyword field), and fails on four content patterns. | **Exits 0.** Wire it into whatever runs before a commit. |

---

# 3. How everything here is written, and why it matters

**Every claim carries a file and a line.** Not because it is tidy, but because a reviewer who
catches one overstatement stops believing the rest — and this packet had four overstatements
in it as of yesterday morning, each caught by opening the product rather than by reading the
brief. The claim tables at the top of `LISTING.md` and in `REVIEW-NOTES.md` §2 are the
mechanism: if a sentence cannot be pointed at a line, it does not ship.

**Nothing is translated.** Each of the six locales was written against the voice already
shipping in `src/lib/i18n/`, then checked back against the English for facts only. Where a
language would not carry an English construction, the line changed rather than the language —
the French subtitle and the German app name are both documented where they appear.

**No entertainment disclaimer, in any language, anywhere.** Guideline 1.1.6 explicitly voids
it, and reaching for it concedes the 4.3(b) argument. `check-listing.py` fails on it in all
six languages, because *"solo con fines de entretenimiento"* and *"nur zu
Unterhaltungszwecken"* are exactly what a translator reaches for in this category.

**No prices in any listing text.** Guideline 2.3.7, and thirteen currencies going stale. The
numbers live only on the product records, where the store keeps them current.

**The comment is not the code.** Two of the four blockers found yesterday came from trusting a
comment that had stopped being true — `entitlements.py:61-64` says calculations stay free and
`PREVIEW_FIELDS` says otherwise; `catalogue.py:187-192` reasons from a door price that no
longer exists. When a document here cites a comment, it now also cites the code that runs.

**When the code moves, these documents move with it.** Four sentences are currently written to
a weaker truth than we would like, each marked in place with what it becomes once the
corresponding item in `APP-CHANGES-NEEDED.md` lands. Understating what the product does is
safe. Overstating it is a rejection.
