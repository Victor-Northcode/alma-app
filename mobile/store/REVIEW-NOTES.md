# What we tell the reviewer

Two stores, two audiences, one argument. Apple's reviewer opens the app holding
Guideline 4.3(b), which names fortune telling by name and refuses it *"unless
[the apps] offer a meaningfully different or improved experience"*
(<https://developer.apple.com/app-store/review/guidelines/>). Google's reviewer holds
Spam / Repetitive content and Minimum functionality, which ask a different question —
does this do something, and does it do it well — and get the same answer.

The rule that governs every sentence below: **nothing here is a claim a reviewer
cannot check inside the app in ninety seconds**, and everything the owner might be
tempted to assert on adjectives has been replaced with a screen to open or a file to
read. Two of the three claims in the brief needed correcting against the code before
they could go in front of a reviewer — §14 lists what changed and why. A reviewer who
catches one overstatement stops believing the rest.

Written 7 August 2026, against the same commit as `DATA-INVENTORY.md` and
`STORE-REQUIREMENTS.md`. Read those first; this file assumes them.

---

## 0. The blanks only the owner can fill

Everything below is ready to paste **except** these. Each appears in the paste blocks
as `⟨LIKE THIS⟩`. None of them can be guessed, and a placeholder shipped into App
Store Connect reads as a placeholder.

| Placeholder | What it is | Where it is needed |
|---|---|---|
| `⟨REVIEW CONTACT⟩` | Name, email, phone for App Review contact | Apple §1, Play §9 |
| `⟨SUPPORT URL⟩` | Support page that reaches a human. **Route built** — `src/app/(legal)/support/page.tsx`, 200 on 7 Aug 2026. The value is `https://⟨HOST⟩/support`; only the host is undecided | Both listings |
| `⟨PRIVACY URL⟩` | Where `src/app/(legal)/privacy/page.tsx` is published | Both listings, both paste blocks |
| `⟨DELETE URL⟩` | **Public** account-deletion page. **Route built** — `src/app/(legal)/delete-account/page.tsx`, 200 on 7 Aug 2026. The value is `https://⟨HOST⟩/delete-account`; only the host is undecided — see §12 | Play Console, §12 |
| `⟨DEMO MAILBOX⟩` / `⟨DEMO PASSWORD⟩` | Only if the owner wants a pre-seeded account rather than a typed birth — see §3 | Apple demo fields |
| `⟨VERSION⟩` | Version string being submitted | Both paste blocks' first line |

**And one that is not a placeholder but a prerequisite: the domain does not resolve.**
`nslookup alma.pazl.ai` and `nslookup api.pazl.ai` both returned NXDOMAIN on 7 August 2026
(only the apex `pazl.ai` answers, at `95.81.101.52`; `apple.com` answered 200 from the same
shell, so it is the domain and not the connection). Three of the four URLs above therefore
cannot be filled in with anything true yet, and Apple fetches the Privacy Policy URL during
review. Nothing in this file can be filed until the host is up. `SUBMISSION-CHECKLIST.md`
step A0.

---

# PART ONE — APPLE

## 1. The block to paste into **Notes for Review**

Guideline 2.3.1(a) requires specificity here — *"generic descriptions will be
rejected"* — and 2.1(b) requires an explanation of any in-app purchase the reviewer
cannot find by tapping around. Both are handled below.

English only. App Review reads English; the six-locale obligation is on the listing,
not on this field.

```text
Alma ⟨VERSION⟩ — notes for App Review

WHY THIS IS NOT ANOTHER HOROSCOPE APP (Guideline 4.3(b))

We know what category this looks like from the icon. Guideline 4.3(b) names fortune
telling, and it is right to. Below are four things to check inside the app. They take
about ninety seconds and none of them requires a purchase.

Before you start: no sign-in is required. The app creates an account for the device on
first launch and everything works from there. Signing in only moves an existing
account to a second device. There is no password anywhere in the product.

1. GETTING TO A CHART (about 20 seconds)
The app opens on the Today tab. There is no onboarding sequence: the first screen
states what the app does and offers one button, "Enter my birth data". Tap it and the
app asks four things — a birth date, a birth time, a birthplace and a name. Nothing is
pre-written; the chart is computed from what you type. Use:

    date   14 March 1998
    time   04:20
    place  Milan, Italy
    name   Sofia Rossi

(Any birth works. This one is the fixture our test suite runs against, so what you see
is what CI checks.) If you would rather not enter a time there is an "I don't know my
birth time" toggle, and the app then refuses every reading that depends on the horizon
rather than guessing at it — that refusal is visible on the Systems tab.

A purchase screen appears at the end of that form. It can be declined. Nothing behind
it is needed for anything below.

2. THE FIRST SCREEN — "Today"
Every transit row names the natal placement it is read against and prints it in chart
notation, not as a mood. Under them is one line: "Nothing here is a prediction. Every
line names the placement it was read from." That is a statement about method, not a
disclaimer — item 4 is the code that enforces it.

3. THE CROSS-SYNTHESIS SCREEN — Systems tab, at the bottom
This is the part of Alma that does not exist elsewhere, and it is free: no purchase is
needed to see it. Nine named questions, each with two stated poles — "Direction: works
alone, out of sight ↔ works in public, in front of people". Three systems computed
independently (the natal chart, numerology, the tarot birth card) each answer each
question, each printing the exact factor it read, and each axis is labelled "3 agree",
"2 disagree" or "seen by one".

Where they disagree, the app says so and shows both sides. It does not average them
into one soothing paragraph. That averaging is the thing 4.3(b) is aimed at, and
declining to do it is most of what makes this a different product.

4. THE CHART IS ACTUALLY COMPUTED (about 30 seconds)
Systems > Compatibility > People > Add person. Enter the SAME date and place as above
with the birth time set to 06:20 instead of 04:20. Open that person's natal chart.

The rising sign changes from Capricorn to Pisces. Same date, same city, two hours
apart. Nothing else about the two people differs, and no sun-sign app can produce that
difference because it does not depend on the sun.

Positions come from NASA JPL's DE440s ephemeris kernel read through Skyfield, with
IAU 2006/2000A precession-nutation from pyerfa — not a lookup table. The house cusps
and the bodies' houses move too, by roughly thirty degrees of rising; those are behind
the paywall on a free account, so the rising sign is the part you can check for
nothing, and it is the part that makes the point.

5. THE WRITING CANNOT INVENT A PLACEMENT
Open any chapter — chapter I of each of the eight systems is free and permanent. At
the foot of the chapter, under "Read from", are the exact placements that chapter
cites. That list is not decoration. The generator returns each paragraph together with
the factor strings it was written from, and those strings are compared character for
character against the computed chart. A paragraph citing a placement the chart does
not contain is rejected and regenerated; a paragraph citing nothing at all is rejected
too; after three attempts the chapter is refused rather than published. A fluent
invented placement is exactly what this category is made of, and it is the specific
thing this product refuses to ship.

Alma also declines to predict, by design. Asked "should I take the job abroad?" it
answers that nothing in the chart tells you to go or to stay. A list of things it will
never say — a death, a diagnosis, a pregnancy, the outcome of a lawsuit, a guaranteed
financial return — is enforced in code, not left to the model.

WHAT IS FREE, EXACTLY
No account and no purchase is needed for any of this, and it does not expire: the sun,
moon and rising signs, the moon phase and the chart's elemental balance; the life path,
birthday and destiny numbers; the tarot birth card; every transit currently in effect,
each printing the day it is exact and the natal placement it is read against; the solar
return date and its ruler; the four compatibility weights; and the whole cross-synthesis
— all nine axes, each system's own cited factor, and the agreement counts. Plus one
complete written chapter in each of the eight systems, permanently.

What is sold is the written interpretation of the other thirty-three chapters, and with
each system the rest of its computed detail — the twelve houses and the aspects behind
the natal chart, the pinnacles and cycles behind the numbers, the lines behind the map.
The exact free surface is one dict, `PREVIEW_FIELDS` in
`backend/alma/api/routers/systems.py:47-78`, applied to every response at `:114-121`.

IN-APP PURCHASES
(The ids below are written with the `alma.` prefix the binary ships today. If the owner
adopts `ai.pazl.alma.` — `PRODUCTS.md` §2, still open — every id in this block changes
with it, in the same commit as the four source files. Do not paste this section without
checking which prefix `LadderKey.swift:115` holds.)

Twelve products, all in the build, all functional in sandbox:
- Eight "doors" at $5.99, one per system (alma.natal, alma.numerology,
  alma.birth_card, alma.transits, alma.solar_return, alma.compatibility,
  alma.astrocartography, alma.synthesis). Non-consumable, permanent, restorable.
  Each unlocks every chapter of that one system.
- alma.archive, $38.99 — all 41 chapters of all eight systems. Non-consumable.
- alma.archive_upgrade, $33.00 — see below.
- alma.monthly $9.99 and alma.annual $78.99 — one subscription group.

There is no free trial and no introductory offer, deliberately. The free tier is the
computed evidence listed above plus one permanently free chapter in each of the eight
systems; it is not a countdown. Nothing in the app uses the "XX-day Trial" mechanism
of 3.1.1.

PER GUIDELINE 2.1(b) — a product you will not find by tapping around:
alma.archive_upgrade is offered ONLY to someone who has already bought a door, and
only within thirty days of that purchase. It is the archive at $38.99 less the $5.99
already paid, so that deciding later costs the same as deciding at the checkout. The
server substitutes it for alma.archive in the catalogue it sends the app; the app
never computes a discount. To see it: buy any $5.99 door in sandbox, then open the
purchase screen again — the archive row is replaced by the upgrade row at $33.00.

Our internal price list also contains a thirteenth item, "archive-bump" at $29.99.
It is NOT created in App Store Connect and the iOS build cannot request it. It exists
only for the web checkout, where a second item can be added to a cart in flight;
StoreKit shows one product per confirmation, so it has no meaning here. We mention it
only so that a difference between our published price list and the App Store Connect
list is not read as something withheld.

THE SUBSCRIPTION — THE TWO PLANS SELL DIFFERENT THINGS
Monthly ($9.99) buys the LIVING layer and only that: transits, the solar return and
compatibility recomputed as they move, plus forty questions a month in the chat. It
does not include the 41 archive chapters. A natal chart does not change, and renting
it would be rent on a number fixed at birth.

Annual ($78.99) is the wider plan: the living layer AND all 41 chapters, for twelve
months. That is why its product description reads "All 41 chapters + what moves, 12
months" while the monthly's reads "3 live systems + 40 questions a month". The
difference is not duration, it is scope — `annual` is granted `scope="all"` and
`monthly` `scope="live"` in `backend/alma/billing/catalogue.py:207-216` — which is also
why they are levels 1 and 2 of one subscription group rather than two options at one
level. Nobody can hold both; switching from monthly to annual is an upgrade that takes
effect immediately.

The permanent archive at $38.99 is a separate, one-time purchase and is the only way to
keep the 41 chapters after a subscription ends.

The renewal terms sit immediately above the purchase button on the purchase screen
itself, not behind a link, and they change with the selected row. Terms of Use,
Privacy Policy and Subscription terms are three links on that same screen; all three
open documents shipped inside the binary, so none of them can be a dead URL. The
privacy policy is also at ⟨PRIVACY URL⟩ and in Settings.

IF A PURCHASE DOES NOT SEEM TO UNLOCK
Entitlements are granted by our server, never by the app. StoreKit hands the app a
signed transaction; the app posts it to our backend; the backend verifies the
signature against a pinned Apple Root CA - G3 and against our bundle id, writes the
grant, and only then does the app re-read what the account holds. So a sandbox
purchase resolves a second or so after the sheet closes rather than instantly — if a
chapter still looks locked, pull to refresh or leave the screen and come back. This is
deliberate: a client that could decide what it owns is a client that can be made to
decide it.

Sandbox transactions are accepted for exactly this reason. "Restore purchases" is on
the purchase screen and in Settings; it replays every transaction on the Apple ID
through the same server check.

WHY THE APP ASKS FOR WHAT IT ASKS FOR
Birth date, birth time, birthplace and name are the calculation — there is no product
without them. The birthplace is chosen from a search box against a gazetteer bundled
inside our own server; no geocoder is called and the app never asks iOS for a
location. There is no CoreLocation import and no location usage string in the plist.

The written interpretations are generated by a third-party model provider (Anthropic).
Per Guideline 5.1.2(i) this is disclosed in the privacy policy in plain words, in all
six languages: the birth date, the birth time, the birthplace label and the name are
sent with each chapter request, and chat messages are sent with each chat turn. The
email address, the account id and the coordinates are not.

ACCOUNT DELETION, TRACKING
Settings > Delete account erases the account and everything in it — profiles,
readings, conversations, memory, entitlements, analytics events. It is a real
deletion, not a deactivation. Payment records survive detached, with the user id
removed and the payload redacted, because they are a tax record. Settings > Export
your data returns everything as one JSON file.

Deletion asks you to confirm by typing the email address on the account, so it needs a
signed-in account. If you are testing as a guest — which is the default, since no
sign-in is required — Settings will offer to sign you in first. Sign-in is a one-time
emailed link to any address you control; there is no password to create.

There is no tracking. No advertising identifier, no ATT prompt, no third-party
analytics SDK, no crash SDK, no remote script. The app records nine named funnel
stages against our own account id and nothing else — no IP address, no user agent, no
referrer, no device id, no free text. "Used to Track You" is No on every row of our
privacy label.

CONTACT
⟨REVIEW CONTACT⟩ — we will answer within a working day and would much rather answer a
question than receive a rejection.
```

> **Two paragraphs in that block are written to what ships today and should be rewritten
> before it is pasted, if the code moves first.**
>
> **ACCOUNT DELETION.** The sign-in caveat is there because a guest genuinely cannot
> delete: `beginDelete(isGuest:)` returns `.needsAccount`
> (`mobile/ios/Alma/Screens/Settings/AccountModel.swift:220-222`), `POST /v1/account/delete`
> sits behind `require_account` (`backend/alma/api/deps.py:95-99`), and
> `backend/alma/api/routers/account.py:74-79` additionally rejects any account with no
> email. The reviewer *is* a guest, because §3 recommends answering "Sign-in required: No".
> So the reviewer holds an account containing a birth date, a birth time to the minute, a
> birthplace coordinate, a name, chat and memory, and cannot delete it — which is what
> Guideline 5.1.1(v) exists to prevent. Telling them to sign in first is honest but it is
> still a wall, and the fix is small: `APP-CHANGES-NEEDED.md` §1. **When it lands, delete
> the caveat paragraph** and the block goes back to a flat claim that survives any test.
>
> **WHAT IS FREE, EXACTLY.** If `PREVIEW_FIELDS` is widened (`APP-CHANGES-NEEDED.md` §4),
> the list gets longer and item 4's demo gets its house cusps back. Widen the paragraph in
> the same commit — but never ahead of it.

## 2. Where each claim in that block is checkable

For the owner, so that a reviewer's follow-up question is answered in one message
rather than in a week of guessing.

| Claim in the notes | Where it is true |
|---|---|
| The app opens on Today with an "Enter my birth data" button, not on an onboarding sequence | `mobile/ios/Alma/Screens/Today/TodayScreen.swift:35–49` — `EmptyArgument` when `session.hasBirthData` is false; the button is `L10nCabinet.addBirthData` (`Screens/Cabinet/EmptyArgument.swift:37–40`). Verified on a simulator, 7 Aug 2026 |
| No sign-in required; account minted on first call | `backend/alma/api/deps.py:61–91` |
| No password anywhere | `backend/alma/auth/` — no hashing of a user secret; `DATA-INVENTORY.md` §1.1 |
| Birth time may be unknown, and systems refuse rather than guess | `backend/alma/calc/contract.py:54–74`; test `backend/tests/test_calc_contract.py:167`; the toggle is `JourneyL10n.unknownTime`, `mobile/ios/Alma/Localization/JourneyL10n.swift:148` |
| Chart facts never mention houses when the time is unknown | `backend/tests/test_natal.py:169` |
| The "not a prediction" line on Today | `mobile/ios/Alma/Screens/Today/TodayScreen.swift:111`; string at `mobile/ios/tools/gen_cabinet_strings.py:314` |
| Nine axes, three systems, agree/disagree computed arithmetically | `backend/alma/engine/synthesis.py:28–39` (the axes), `:118–131` (the verdict), `:347–375` (the three contributors) |
| The disagreement screen is free even when the system is locked | `backend/alma/api/routers/systems.py:47–78` — `"synthesis"` keeps `summary, agreements, disagreements, single_voice, axes` through the paywall trim at `:114–121` |
| The disagreement view in the app | `mobile/ios/Alma/Screens/Cabinet/CabinetPieces.swift:410–476` (`AxisView`), `mobile/ios/Alma/Screens/Cabinet/ChartFacts.swift:244–280` |
| DE440s via Skyfield, pyerfa for precession-nutation | `backend/alma/engine/ephemeris.py:1–14`, `:66–84`; the kernel is at `backend/data/de440s.bsp` (32 MB) |
| Two hours of birth time moves the Ascendant | `backend/tests/test_natal.py:179–185` — asserts the Ascendant moves more than 20°. For the fixture birth specifically, Capricorn at 04:20 and Pisces at 06:20, run against a live backend on 7 Aug 2026 |
| …and moves bodies between houses — **but a free account cannot see it** | `backend/tests/test_natal.py:187–195` asserts at least three bodies change house. `PREVIEW_FIELDS["natal"]` has no houses and no bodies, so the notes send the reviewer to look only at the rising sign. Item 4 said "the rising sign, the house cusps and the house of most bodies are different" until 7 Aug 2026, and two thirds of that was invisible to the person being asked to check it |
| A different birthplace rotates the houses and not the planets | `backend/tests/test_natal.py:209–216` |
| Per-paragraph citations, checked character for character | `backend/alma/ai/validator.py:85–146`; normalisation at `:66–82` |
| Rejected, regenerated, then refused | `backend/alma/ai/writer.py:30` (`MAX_ATTEMPTS = 3`), `:304–306` (`ReadingRefused`) |
| "Read from" in the chapter reader | `mobile/ios/Alma/Screens/Systems/ChapterScreen.swift:111–113` |
| The refusal to predict, as code rather than as a promise | `backend/alma/ai/validator.py:153–167` (`FORBIDDEN_PATTERNS`); the voice rules at `backend/alma/ai/voice.py:56–64` |
| The nine-item free list, exactly | `backend/alma/api/routers/systems.py:47–78` (`PREVIEW_FIELDS`), applied at `:114–121`. **Not** `entitlements.py:61–64` — that comment says "calculations stay free forever" and the code disagrees with it: a locked natal returns six keys and `factors: []`, and a locked astrocartography returns only `birthplace` with the computed `lines` trimmed. The notes now transcribe the dict rather than the comment |
| One free chapter per system, permanent, 8 of 41 | `backend/alma/ai/chapters.py` — `free=True` on lines 43, 78, 91, 100, 110, 119, 130, 139 |
| Twelve products, ids computed not tabulated | `mobile/ios/Alma/Billing/LadderKey.swift:24–121`; the same rule in Python at `backend/alma/billing/provider.py::store_product_id` |
| archive-bump absent from the iOS build on purpose | `mobile/ios/Alma/Billing/LadderKey.swift:17–23` — the comment is explicit that it must never be created in App Store Connect |
| archive-upgrade offered once, inside 30 days | `backend/alma/billing/catalogue.py:197–206`; `CREDIT_WINDOW` in `backend/alma/auth/entitlements.py` |
| Monthly = the living layer; **annual = the living layer and the 41 chapters, for a year** | `backend/alma/billing/catalogue.py:146–150` (`LIVING_SYSTEMS`), `:211` (`monthly`, `scope="live"`), `:215` (`annual`, `scope="all"`). The notes described the subscription as buying only the living layer until 7 Aug 2026, while `alma.annual`'s own App Store description — in the same submission — read "Every system, every chapter, and the transits as they move." `PRODUCTS.md` §3.5 has always had it right |
| Forty questions a month | `backend/alma/config.py:279–281` |
| Deletion needs a signed-in account, and the reviewer is a guest | `mobile/ios/Alma/Screens/Settings/AccountModel.swift:220–222`; `backend/alma/api/deps.py:95–99`; `backend/alma/api/routers/account.py:74–79`. This is the one row in this table that is a *problem* rather than a citation — `APP-CHANGES-NEEDED.md` §1 |
| Renewal terms adjacent to the button | `mobile/ios/Alma/Billing/PaywallView.swift:155–166`; the string at `mobile/ios/Alma/Localization/PaywallL10n.swift:157–160` |
| Three legal links on the paywall, in the binary | `mobile/ios/Alma/Billing/PaywallView.swift:262–281` |
| Restore on the paywall and in Settings | `mobile/ios/Alma/Billing/StoreControls.swift:20–45`; `PaywallView.swift:201–205` |
| Server-side grant, pinned root, bundle-id check | `mobile/ios/Alma/Billing/AlmaStore.swift:13–19, 341–383`; `backend/alma/api/routers/billing.py:532–560`; `backend/alma/config.py:185–193` |
| Sandbox accepted, and why | `backend/alma/config.py:195–207` (`ALMA_APPLE_ACCEPT_SANDBOX`, default true) |
| Offline gazetteer, no geocoder call | `backend/alma/geo.py:1–20`, `:75–80` |
| No CoreLocation, no location usage string | `mobile/ios/Info.plist` (no `NSLocationWhenInUseUsageDescription`); grep of `mobile/ios/Alma/` |
| What goes to Anthropic, exactly | `backend/alma/ai/writer.py:152–164`; `backend/alma/ai/conversation.py:120–145`; `DATA-INVENTORY.md` §2.1 |
| Deletion is real, and what survives | `backend/alma/auth/accounts.py:360–397`; `DATA-INVENTORY.md` §3 |
| Export | `backend/alma/auth/accounts.py:220–321` |
| No ad id, no ATT, no analytics or crash SDK | `DATA-INVENTORY.md` §4 — every claim there is a grep that came back empty |
| Nine funnel stages, eight allowed properties, nothing else | `backend/alma/funnel.py:124–142`, `:154–156`, `:179–223` |

## 3. The demo-account fields

**Recommended answer: "Sign-in required" = No.** It is the truth. `deps.py:61–91`
mints an account on the first request from any client and hands back a token; the
whole product — chart, cross-synthesis, free chapters, chat, purchases — works without
anyone ever typing an address. Guideline 5.1.1(v) prefers exactly this, and answering
Yes would invite a reviewer to hunt for a login screen that gates nothing.

Then the birth record in §1 does the work the demo account would have done. Typing it
takes about twenty seconds and produces a real chart, which is better evidence than a
seeded one: the reviewer watched it get computed.

**If the owner wants a genuinely pre-seeded account anyway**, understand what it
costs. Alma has no password. Sign-in is Google, Apple, or a single-use emailed link
(`backend/alma/api/routers/auth.py:55–130`), and a magic link is single-use and
short-lived. So a working demo account means handing App Review a **mailbox** —
`⟨DEMO MAILBOX⟩` / `⟨DEMO PASSWORD⟩` in the demo fields, with a note saying "request a
sign-in link in the app, then read it in this mailbox at ⟨webmail URL⟩". That is three
extra steps for the reviewer against a twenty-second form, and a mailbox credential
sitting in App Store Connect forever. Recommendation: don't. It is listed here because
it is the only honest way to do it, not because it is better.

There is no third option. There is no URL scheme in the build (`mobile/ios/Info.plist`
declares no `CFBundleURLTypes`), so a pre-filling deep link does not exist and would be
a code change, not a metadata one.

## 4. The three rejections most likely to come back, and the reply

**"Guideline 4.3(b) — your app duplicates existing apps."** Do not argue and do not
add adjectives. Reply with the two screens: the cross-synthesis axis view, which no
app in this category ships, and the birth-time sensitivity check from §1 item 4.
Attach a screen recording of the second one — the same date and place, two birth
times, Capricorn rising and Pisces rising — because it takes eleven seconds and it is
not something a template app can produce. Both are visible on a free account, which
matters: an argument a reviewer has to buy something to see is an argument they will
not check. Then name `backend/alma/ai/validator.py` and offer to walk through it.

The claim to make is an *experience* claim ("here is what you can do here that you
cannot do there"), never a technology claim ("we use JPL ephemerides"); 4.3(b)'s own
words are "meaningfully different or improved **experience**".

Say **three** systems on the axes, never eight. Eight are computed; three are compared
(`engine/synthesis.py:355–360`). Overstating the differentiation argument by 8/3 in
front of the guideline it is meant to answer is how a defensible 4.3(b) case becomes a
credibility problem, and the one number a reviewer can verify by opening the screen is
the one that was wrong.

**"Guideline 2.1 — we were unable to locate in-app purchases."** Almost certainly
`archive-upgrade`, which by design does not appear until a door is owned. The §1 block
pre-empts this; if it still comes back, the reply is the four-step recipe: buy any
$5.99 door in sandbox → reopen the purchase screen → the archive row is replaced by
the upgrade row → the price is $33.00 and the server, not the app, made that
substitution.

**"Guideline 3.1.2 — subscription information is missing."** Point at the purchase
screen: the renewal statement sits directly above the button (`PaywallView.swift:155`),
it names the charge, the period, the 24-hour rule and where to cancel, and Terms,
Privacy and Subscription terms are three links on the same screen opening documents
inside the binary. If the reviewer saw the *journey's* offer step rather than the
Settings one, both are the same component and carry the same block — say so.

---

# PART TWO — GOOGLE PLAY

## 5. Where Play asks, and what goes in each field

Play has no single "notes for review" box. The same material is split:

| Play Console field | What goes in it |
|---|---|
| **App content → App access** | Whether login is required, and instructions. Answer: **"All functionality is available without special access."** No credentials. Add the birth record as a note anyway — see §6. |
| **Store listing → Full description** | Not a review note, but Play's reviewers read it and Spam / Minimum functionality are judged partly from it. Lead with what the app *computes*. |
| **App content → Data safety** | Derived entirely from `DATA-INVENTORY.md` §6. Do not fill it from the Apple answers; the definitions differ. |
| **App content → Content rating (IARC)** | See §13. |
| **App content → Target audience** | Adults only. Selecting any group under 13 pulls Alma into the Families Policy. |
| **Policy declarations** | No ads, no financial features, no news, no government affiliation, no health claims. |

## 6. The block to paste into **App access → instructions**

Shorter than Apple's, because Play's reviewer is answering "can I get in" rather than
"is this a duplicate". The differentiation argument belongs in the full description
and in §7.

```text
No login is required. The app creates an account for the device on first launch;
every feature — the eight computed systems, the cross-synthesis, the free chapters,
the chat, purchases and restore — works without anyone signing in. Sign-in exists only
to move an account to a second device, and it is passwordless (Google, or a one-time
emailed link).

To reach a chart on first launch, enter any birth. This one is the fixture our test
suite runs against:

    date   14 March 1998
    time   04:20
    place  Milan, Italy
    name   Sofia Rossi

The app opens on the Today tab with an "Enter my birth data" button; the form is one tap
behind it. A purchase screen appears at the end of that form and can be declined.

Account deletion is in the app at Settings > Delete account, and also at ⟨DELETE URL⟩
without installing the app. Both erase the account and everything held against it —
profiles, readings, conversations, memory, entitlements and analytics events. Deletion
confirms against the email address on the account, so it asks you to sign in first if you
have not; sign-in is a one-time emailed link, with no password to create.

In-app purchases: eight one-time system unlocks at $5.99, an archive at $38.99, a
conditional upgrade at $33.00 offered only to someone who already owns one system, and
a subscription with monthly ($9.99) and annual ($78.99) base plans in one subscription
product. Entitlements are granted server-side after we verify the purchase token
against the Play Developer API, so a test purchase unlocks a second or so after the
sheet closes rather than instantly.
```

## 7. What Play's two policies actually ask, and the answer

Play's framing is **utility and engagement**, where Apple's is **differentiation**
(`STORE-REQUIREMENTS.md` §14). So the Play answer leads with what the app computes
rather than with how it differs from competitors. If a Play review requires a written
reply, this is it:

> Alma computes eight independent systems from one birth moment: a full natal chart
> (ten bodies, twelve houses, aspects, angles, Chiron and the lunar nodes), Pythagorean
> numerology, the tarot birth card, a transit scan, the solar return, compatibility
> between two charts, astrocartography lines, and a cross-synthesis that puts three of
> those systems side by side on nine named questions and reports where they agree and
> where they contradict each other. Positions are computed from NASA JPL's DE440s
> ephemeris kernel through Skyfield, against the exact minute and coordinate of birth,
> with historical time-zone handling — not from a static table. Forty-one written
> chapters, each of which cites the specific placements it was read from; the generator
> refuses to publish a paragraph citing a placement that is not in the computed chart.
> Every system opens on computed evidence that costs nothing and does not expire — the
> three signs and the chart's balance, three of the numbers, the birth card, every transit
> with its exact date and the natal placement it is read against, the solar return and its
> ruler, the four compatibility weights, and all nine axes of the cross-synthesis with each
> system's cited factor — plus one complete written chapter in each of the eight systems.
> The written interpretation is the product.
> The app is in six languages and holds no static content — every screen is generated
> from the person's own data.

That answers *"apps that are static without app-specific functionalities, for example,
text only or PDF file apps"* directly.

## 8. The Play differences worth knowing before you write anything

- **Cancel inside the app is a policy requirement**, not a nicety. It is there:
  `mobile/android/app/src/main/kotlin/ai/pazl/alma/ui/screens/SettingsScreen.kt:361–367`
  opens `play.google.com/store/account/subscriptions` with the product id attached
  (`billing/StoreProducts.kt:176–181`). Keep it, whatever the catalogue says.
- **The deletion web URL is a second, separate obligation.** Apple does not have it.
  See §12 — it is the one item in this file that is not yet true.
- **archive-bump is a purchasable Play product id if it is ever created**, and unlike
  StoreKit, Play would happily sell it standalone at $29.99 for the same grant the
  $38.99 archive gives. The Android build blocks it in `PlayBilling.purchase` via
  `StoreProducts.NEVER_ALONE` rather than only on the paywall. Simplest correct
  answer: **do not create `alma.archive_bump` in the Play Console either.**
- **Both August 31 deadlines are already met** in the repo: `targetSdk = 36` and
  `compileSdk = 36` (`mobile/android/app/build.gradle.kts:10,15`), Play Billing
  `8.3.0` (`mobile/android/gradle/libs.versions.toml:26`). Verify, don't assume, at
  upload time.

---

# PART THREE — THE SENTENCES THAT MUST NEVER APPEAR

## 9. No entertainment disclaimer, anywhere, in any language

Guideline 1.1.6: *"Stating that the app is 'for entertainment purposes' won't overcome
this guideline."* It buys nothing and reads as an admission that the rest is not meant
seriously — which, for a product whose entire argument is that it refuses to invent,
is the most expensive sentence available.

So: not in the description, not in the app, not in the reviewer notes, not in a
tooltip, and not in `es`, `de`, `it`, `fr` or `pt-BR`. Anyone localising the listing
should be told this explicitly, because "solo con fines de entretenimiento" and "nur
zu Unterhaltungszwecken" are exactly what a translator reaches for in this category.

What replaces it is already written and already true: *"Nothing here is a prediction.
Every line names the placement it was read from."*
(`mobile/ios/tools/gen_cabinet_strings.py:315`).

## 10. Three other things that must not be written

- **Any claim of predictive accuracy.** 2.3.7 forbids *"unverifiable product claims"*
  in metadata. "NASA JPL ephemeris" is verifiable and defensible. "Know what's coming"
  is neither, and it contradicts the product.
- **"Access to Alma" as a description of the subscription.** It would invite the
  obvious question of what the $38.99 archive was for, and 3.1.2(a) is where that
  question gets asked. The **monthly** is *the living layer*: transits, the solar
  return, compatibility, plus forty questions a month.

  The **annual** is a different product and must be described as one — it is
  `scope="all"` (`catalogue.py:215`), so it does include the 41 chapters, for twelve
  months. Say that, and say "for twelve months" every time, because the thing that
  distinguishes it from the permanent $38.99 archive is the duration and nothing else.
  What must never be written is a sentence that describes *the subscription* as a
  single thing: the two plans sell different scopes, and any sentence covering both is
  wrong about one of them. That is exactly how the block in §1 came to deny, in one
  paragraph, what `alma.annual`'s own store description asserted in one line.
- **Any mention of Android, Google Play, or a Play badge in the Apple listing or the
  iOS app** (2.3.10), and the mirror of it on Play.

---

# PART FOUR — THE THINGS THAT ARE NOT TRUE YET

## 11. The Do Not Track promise has no equivalent in the apps

`src/app/(legal)/privacy/page.tsx:104–108` promises that funnel steps are not recorded
when the browser sends DNT or GPC. True on the web (`src/lib/track.ts:106–120`); there
is no such signal on a phone and no toggle in either app —
`AlmaClient.track` posts unconditionally on both
(`mobile/ios/Alma/Networking/AlmaClient.swift:308–318` and its Android twin).

The sentence is scoped to "your browser" so it is not false, but a person reading it
inside the app would reasonably conclude they have an opt-out they do not have — and
5.1.1(ii) requires *"an easily accessible and understandable way to withdraw consent"*
for collected usage data. **Do not paste any sentence about an analytics opt-out into
either store's notes until this is settled.** Two ways out, both fine, one required:
ship a Settings toggle that suppresses `POST /v1/events`, or scope the promise to the
web explicitly in all six languages.

## 11b. A guest cannot delete their account, and the reviewer is a guest

This is an **Apple** blocker as well as a Play one, and until 7 August 2026 this file
recorded it only as the second.

`beginDelete(isGuest:)` returns `.needsAccount`
(`mobile/ios/Alma/Screens/Settings/AccountModel.swift:220-222`), which renders a "sign in"
prompt where the delete flow would be (`SettingsScreen.swift:255-257, 318-329`). The
backend agrees: `POST /v1/account/delete` is behind `require_account`
(`backend/alma/api/deps.py:95-99`) and `account.py:74-79` rejects any account with no
email, because the confirmation string is compared against it. Android refuses the same
way, on a null email (`SettingsViewModel.kt:241-243`). None of this is a bug; it is a
deliberate guard against a mistap destroying paid readings.

The problem is who it catches. `deps.py:61-91` mints a guest account on the first request
from any client, and §3 of this file recommends answering **"Sign-in required: No"** —
which is true and is the right answer. So App Review arrives as a guest, holding an
account that contains a birth date, a birth time to the minute, a birthplace coordinate, a
name, chat and memory, and finds no way to delete it. Guideline 5.1.1(v) is precisely
about that.

Until it is fixed, §1's deletion paragraph has to carry the sign-in caveat, which is
honest and weak. **The fix is cheap and is the better answer**: let a guest delete against
their bearer token, and replace the email-confirmation guard with a typed phrase for
accounts that have no address. `APP-CHANGES-NEEDED.md` §1 has the shape of it. Neither
alternative is attractive — rewriting the notes to say deletion needs sign-in invites the
guideline, and answering "Sign-in required: Yes" means handing App Review a mailbox
forever (§3 explains why).

## 12. The public account-deletion URL — page built, host still missing

Play requires two things (<https://support.google.com/googleplay/android-developer/answer/13316080>):
an in-app route, and *"an accessible external web resource for account deletion"*
whose URL goes in a designated Play Console field. Apple asks only for the first.

**Both now exist in the repository.** The web resource is
`src/app/(legal)/delete-account/page.tsx`, returning 200 on 7 August 2026; the value for
the field is `https://⟨HOST⟩/delete-account`. It explains what deletion removes
(`DATA-INVENTORY.md` §3 is the source), routes into the app by the section's real label —
**data & legal**, not "Leaving", which no build has ever called it — and gives
`hello@pazl.ai` for someone who has uninstalled. It is also discoverable rather than
known only to Play Console: it is linked from the site footer, which is what
*"readily discoverable"* asks for.

The in-app route is done on both platforms for a signed-in account, and on Android for a
guest as well. **iOS still refuses a guest** — see §11b — and the page states that
exception plainly, as a client that has not caught up rather than as policy, and routes
those people to the letter. When `APP-CHANGES-NEEDED.md` §1 lands on iOS, three paragraphs
there get shorter.

What is still missing is the host. On 7 August 2026 `nslookup alma.pazl.ai` returned
NXDOMAIN, and so did `api.pazl.ai`; only the apex `pazl.ai` answers, at 95.81.101.52.
A correct path on a name that does not resolve fails this field exactly as a missing page
would, and **it must be live before Play submission** — the field is validated.

## 13. Age rating and content rating — four answers nobody has given yet

`STORE-REQUIREMENTS.md` §5 has the full table. Four rows decide the rating, and none
of them is mine to answer:

- **Health or Wellness Topics.** Any non-None answer gives 9+; Infrequent and Frequent
  cost the same. Read `backend/alma/ai/chapters.py` — chapter X of the natal system is
  "Work and rhythms: what pace can I sustain?" and chapter VII is "Shadow and wound".
  Whether that counts is a judgement call. It is the single answer most likely to move
  the app off 4+.
- **Medical or Treatment Information — must stay None.** That is a content constraint
  as much as a form answer, and it is already enforced: "you will be diagnosed" and
  "do not see a doctor" are in `FORBIDDEN_PATTERNS`
  (`backend/alma/ai/validator.py:153–161`).
- **Horror/Fear Themes.** The birth-card system draws on the Major Arcana. If Death or
  the Tower is rendered as *imagery*, Infrequent is arguable and costs 9+; if the cards
  are named in text, None holds. Check what task #38 actually renders.
- **Mature or Suggestive Themes.** How explicit compatibility gets. Infrequent gives
  9+, Frequent gives 16+.

For Play's IARC questionnaire there is a fifth unknown that cannot be resolved outside
the console: **whether it asks about occult or fortune-telling content.** Neither Play
help page enumerates the questions. Read them in Play Console and answer what is there
— misrepresentation is what that policy actually punishes.

## 14. Three claims from the brief that had to be corrected before a reviewer saw them

Recorded because a reviewer who catches one overstatement stops believing the rest,
and because the owner should know the shape of the product has drifted from the shape
of the pitch.

**"Eight systems that genuinely disagree with each other."** Eight systems are
computed. The cross-synthesis compares **three** — natal, numerology, birth card —
across nine axes (`backend/alma/engine/synthesis.py:355–368`). The app's own copy
already says three: *"Three agreeing is the closest thing to proof. Two disagreeing is
more useful still"* (`mobile/ios/Alma/Resources/Cabinet.xcstrings:5352`), and the code
comment on the view says *"three named systems disagreeing"*
(`mobile/ios/Alma/Screens/Cabinet/CabinetPieces.swift:417`). So the notes above say
three.

**This was corrected here and left uncorrected in three other places, which was worse
than not catching it.** As of 7 August 2026 the count was: *three* in these notes,
*eight* in all twelve store descriptions, *eight* in the `alma.synthesis` product
description, and *eight* on the app's own first screen. One submission, three answers.
Now fixed in `LISTING.md` (all twelve blocks, and `check-listing.py` fails the build if
the word returns) — and **still open in two files nobody on this side of the wall may
edit**: `mobile/ios/Alma.storekit:116`, which ships to App Store Connect, and
`scr.empty.lead` in `mobile/ios/Alma/Resources/Screens.xcstrings`, which is the first
sentence on the first screen. `APP-CHANGES-NEEDED.md` §2. Widening the engine instead
is equally fine; shipping both answers is not.

**"NASA JPL DE440s ephemeris."** True on any deployment carrying
`backend/data/de440s.bsp` — it is in the repo. But `ephemeris.py:66–84` falls back to
the DE421 kernel bundled with `skyfield-data` when the file is absent, and records
which one answered in every result's provenance. The claim is safe for production
because the kernel ships; it would quietly stop being true on a host that did not
copy the data directory. **Checklist item, not a notes item** — see the submission
checklist, step A6.

**"A birth time moved two hours changes the text, and there is an automated test
asserting exactly that."** The tests assert the *chart* changes: the Ascendant moves
more than 20° (`test_natal.py:179`) and at least three bodies change house
(`test_natal.py:187`). The text follows because every paragraph must cite a factor
from that chart and the validator enforces it — but no test asserts generated prose
differs, and no test could without calling a model. The notes above therefore promise
what a reviewer can see on screen (the rising sign and the houses change) and name the
validator separately. Do not write "a test asserts the text changes" in front of
somebody who might ask which test.

### And four more, found on 7 August by three checkers reading this file against a running build

**"Every calculation in Alma is free and permanent."** Not true of the shipped app, and
the two nouns the store copy named — *the whole chart*, *the lines* — were among the
paid ones. A locked natal returns six keys and `factors: []`; a locked astrocartography
returns `birthplace` and nothing else, with the computed `lines` trimmed away
(`api/routers/systems.py:47–78`). The comment at `entitlements.py:61–64` does say
calculations stay free; `PREVIEW_FIELDS` is what runs. §1 now enumerates the nine free
things instead of generalising, which is checkable in fifteen seconds and therefore
better evidence than the slogan was.

**"On first launch the app asks four things."** It does not. The app opens on Today with
a hero block and one button, "Enter my birth data"
(`Screens/Today/TodayScreen.swift:35–49`); the form is one tap behind it. Verified on a
simulator. The value of a step-by-step script is that a reviewer under time pressure can
follow it without improvising, and the first sentence did not match the first screen.

**"The rising sign, the house cusps and the house of most bodies are different."** The
rising sign genuinely changes — Capricorn at 04:20, Pisces at 06:20, same date, same
city, confirmed against a live backend. The other two are not in `PREVIEW_FIELDS["natal"]`,
so the reviewer this demo is aimed at cannot see them. This is the demo §4 leans on
hardest against the guideline most likely to reject the app, so two thirds of it being
unverifiable was the most expensive sentence in the file. It now promises the rising sign
and names both signs.

**"The subscription does not buy the 41 archive chapters."** True of monthly, false of
annual (`catalogue.py:215`, `scope="all"`) — and `alma.annual`'s own product description,
in the same submission, read "Every system, every chapter, and the transits as they move."
The notes denied in one paragraph what a product record asserted in one line, on the
guideline (3.1.2(a)) that is judged on exactly that comparison.

The pattern in all four is the same and worth naming: **this file was checked against the
brief and against the code's comments, but not against the code that runs or the app that
launches.** Three of the four were found by opening the product. Before the next
submission, walk §1 on a clean install with a stopwatch and delete anything you cannot
see.

---

## 15. One more thing, for whoever files these

Both stores' notes are living documents. `⟨VERSION⟩` changes every submission, and
2.3.1(a) requires *"all new features, functionality, and product changes"* to be
described with specificity each time — so the block in §1 is a starting point that
gains a paragraph per release, not a form filled in once. Keep it in this file, keep
it under a page, and keep every sentence in it checkable.
