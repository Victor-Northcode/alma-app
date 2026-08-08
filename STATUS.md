# Alma — where it actually stands

**7 August 2026.** Written after a full pass over all three surfaces against the live
backend. Everything below was run on this machine today; nothing is recalled from an earlier
session's notes. Where I could not verify something, it says so in those words.

Read §5 before you read anything else if you only have five minutes. It is the list of things
that are not done, and it is not softened.

---

## 1 · What exists

| Surface | State | Where |
|---|---|---|
| **Backend** | Complete. 1490 tests pass. Live AI, live ephemeris, live geocoder. | `backend/` |
| **Web** | A storefront: landing, the free journey, portrait, sign-in, six legal pages, six languages. Nothing is sold here and no paid chapter can be read here. | `src/` |
| **iOS** | Builds and runs. SwiftUI. All payment through StoreKit. | `mobile/ios/` |
| **Android** | Builds debug and release, 43 unit tests pass, runs on a real emulator. Compose. All payment through Play Billing. | `mobile/android/` |
| **Store paperwork** | Twelve listings, review notes, data-safety, privacy delta, submission checklist. `check-listing.py` green. | `mobile/store/` |

The ladder is unchanged: door **$5.99** · archive **$38.99** · archive-bump **$29.99**
(only inside another checkout) · archive-upgrade **$33.00** · monthly **$9.99** · annual
**$78.99**. No trial, no introductory price. `backend/alma/billing/catalogue.py` is the only
place a price is written, and `src/lib/prices.test.ts` fails the build if a number is typed
into an interface.

---

## 2 · Every gate, run today, real output

```
$ cd backend && .venv/bin/python -m pytest -q
1490 passed, 618 warnings in 147.92s (0:02:27)

$ cd backend && .venv/bin/python tools/license_gate.py
license gate: 56 packages checked
  accepted by exception: certifi (Mozilla Public License 2.0 (MPL 2.0))
clean: no GPL / AGPL / LGPL, direct or transitive

$ npx tsc --noEmit && node scripts/check-locales.mjs && npx vitest run
tsc: clean
locales: 5 translated, no English left behind
 Test Files  16 passed (16)
      Tests  255 passed (255)

$ npm run verify                                 # exit 0
 ✓ Compiled successfully
 ✓ Generating static pages (13/13)
 /  ·  /_not-found  ·  /delete-account  ·  /imprint  ·  /manifest.webmanifest
 /privacy  ·  /refunds  ·  /sign-in  ·  /subscription-terms  ·  /support  ·  /terms

$ cd mobile/ios && xcodebuild -scheme Alma \
    -destination 'platform=iOS Simulator,name=iPhone 17' build
** BUILD SUCCEEDED **        (0 warnings from our code)

$ cd mobile/android && ./gradlew :app:assembleDebug :app:testDebugUnitTest
BUILD SUCCESSFUL             (67 tests, 0 failures)

$ python3 mobile/store/check-listing.py
42 fields checked
OK
```

Seven gates, seven green.

**And two that are not gates, because they cost money and reach the network.** They are the
only way to know whether the writing is *true*, which no scripted provider can answer:

```
$ cd backend && .venv/bin/python tools/daily/a_real_week.py --from 2026-08-24
2026-08-24  Monday    —  nothing.
2026-08-25  Tuesday   —  nothing.
2026-08-26  Wednesday —  nothing.
2026-08-27  Thursday  PUSH  saturn:opposition:pluto   (129 words, attempt 1, advice '')
2026-08-28  Friday    ·  jupiter:opposition:midheaven in the sky, no notification
                         (a daily went out inside the last 3 days)
2026-08-29  Saturday  —  nothing.
2026-08-30  Sunday    —  nothing.
FROM THE LEDGER: 1.3944 cents total

$ cd backend && .venv/bin/python tools/daily/the_pluto_case.py --runs 5
5/5 generations state the geometry correctly
```

The second one is the reproduction of the only reading anybody has caught being *false*: it
put Pluto on an Ascendant 300° away. Five live generations now name both ends correctly.

---

## 3 · What I drove, and what the product actually produced

I used one birth throughout so the three surfaces could be compared against each other:
**14 March 1996, 15:00, Lisbon (38.72509, −9.1498, Europe/Lisbon)** — typed in cold, nothing
pre-filled, place resolved by the live geocoder.

### The web

Walked from an empty browser: cleared storage, loaded `/`, chose the date in the hero, took
the free first insight, opened the journey, answered the intent question, gave a name, a
birth time, a birth place, sat through the ceremony, read the portrait, skipped the account
step, and landed on the handoff.

- The hero's sky updated to **♓︎ "YOUR SKY · 14.03"** from the date alone.
- The free insight returned **Sun in Pisces · Life path 6 · The Lovers**. Life path 6 is
  1+4+3+1+9+9+6 = 33 → 6, and The Lovers is card VI — both check by hand. It is *not*
  "life path 7", the demo person's number that used to be printed under that card.
- The portrait returned **Mara · Sun in Pisces · ☽ Capricorn · Ascendant Cancer · Life path 6
  · VI The Lovers · waning crescent**. The Ascendant requires the birth time and the place,
  so the time step is genuinely feeding the engine.
- The handoff named the system the first question asked for — *"Your Compatibility is waiting
  in the app."* — quoted 41 chapters and 8 free, printed no price, and showed both store
  plates as **`<span>`s with no `<a>` or `<button>` ancestor** (checked in the DOM, not by
  eye). The "not yet" line reads *"Neither store has us yet. This is where the buttons go the
  day they do."*
- The guest carry sentence was correct for a guest: *"Nothing here is signed in, so this sky
  stays in this browser…"*
- **Console: no errors**, on the landing and through the whole journey.
- Every route returns its right status: `/`, `/sign-in`, `/support`, `/delete-account`,
  `/privacy`, `/terms`, `/refunds`, `/imprint`, `/subscription-terms`,
  `/manifest.webmanifest` → 200; `/nope` → 404.
- German is real and server-side: `Accept-Language: de` gives `<html lang="de">`,
  `<title>Alma — Acht Arten, dich zu lesen. Eine Alma.</title>`, and a German body with no
  English first paint. `/support` in German renders `lang="de"` on its own subtree inside the
  English legal chrome, exactly as designed.
- The two pre-launch switches are correctly **inert**: the web manifest carries no
  `related_applications` and no `prefer_related_applications`, and there is no
  `apple-itunes-app` meta tag. They turn on when `lib/stores.ts` gets its constants.

### Android

Built, installed on `alma_pixel`, cleared, and walked the same eight steps by injected taps
(`adb shell input`), reading the UI tree at each step rather than guessing at pixels.

It produced **the same six values as the web, from the same backend** — Sun in Pisces,
☽ Capricorn, Ascendant Cancer, Life path 6, VI The Lovers, waning crescent. Two independent
clients agreeing on one chart is the strongest evidence in this report.

Then, in the app proper:

- **A real chapter was written.** `POST /v1/readings` → 200 in **55.6 s**. Today rendered
  *"Saturn is sitting on your career point while Pluto reworks something at the root of your
  identity"*, five active transits with dates and orbs (Saturn ☌ Midheaven, 14 August, 0°10′;
  Saturn □ Jupiter, 29 August, 0°48′; Jupiter □ Venus, 11→18 August, 1°01′), and the moon at
  **waning crescent · 29%**.
- **A real question was asked**, and this is the single best thing I saw all day. I asked
  about "Saturn on my Midheaven" — a false premise — and Alma refused it:

  > "You have saturn 27°04′ ♓︎ · house 9, **not on the midheaven**. Your midheaven is at
  > 14°28′ ♈︎. Saturn is in the ninth house — the house of belief, travel, and the far view —
  > where it slows and hardens what it touches."

  I then pulled the chart from `POST /v1/systems/natal` and checked every figure:
  Saturn **27°04′ Pisces** ✓ · Midheaven **14°28′ Aries** ✓ · Sun 24°16′ Pisces ✓ ·
  Moon 19°00′ Capricorn ✓ · Ascendant 28°35′ Cancer ✓ · illumination 0.2909 → "29%" ✓.
  **Every number the model spoke is exactly what the engine computed.** The product's central
  promise — that every sentence names a position you can check — holds under a hostile
  question.
- The free-question counter then read **"2 questions left today"**, which matches
  `ALMA_FREE_QUESTIONS=3`. Checked, not assumed.
- The paywall, with no Play products configured on an emulator, says *"Payments are not
  working right now. Nothing has been charged and nothing was lost — write to
  hello@pazl.ai"*. It degrades honestly rather than showing an empty shelf.

### iOS — built and launched, but **not walked**. See §6.

---

## 4 · What only you can do

You have both developer accounts; the entity is **Pazl LLC**.

**① Stand up the domain. This is the first blocker and it blocks everything.**
Verified by me today, twice, from a shell where `apple.com` answered normally:

```
alma.pazl.ai   NXDOMAIN
api.pazl.ai    NXDOMAIN
pazl.ai        95.81.101.52
```

Both names are compiled into shipped builds — `alma.pazl.ai` is the deep-link host in
`AndroidManifest.xml:47` and `api.pazl.ai` is the Release API host. Every legal URL in all
twelve store descriptions points at the first one. **Apple fetches the Privacy Policy URL
during review and rejects on a dead link before a human opens the build.** Nothing else in
this document can be filed until this resolves.

Once it is up, `alma.pazl.ai` must also serve `.well-known/assetlinks.json`, or the Android
app link stays unverified and an emailed sign-in link opens the browser instead of the app.

**② Decide the product-id prefix. It is the one irreversible decision in the packet.**
The binaries and the backend default all ask for the bare prefix **`alma.`**:

- `backend/alma/config.py:251` — `store_product_prefix` default `"alma."`
- `mobile/ios/Alma/Billing/LadderKey.swift:115` — `static let prefix = "alma."`
- `mobile/android/…/billing/StoreProducts.kt:57` — `const val PREFIX = "alma."`

`PRODUCTS.md` §2 recommends changing all three to **`ai.pazl.alma.`** before the first
product is saved, because `alma.natal` is a generic string in a namespace you do not own and
neither store lets an id be changed or reused afterwards. Either answer works. **What does
not work is typing one into a console while the binary asks for the other** —
`Product.products(for:)` returns an empty set, the paywall renders with no rows, and the
build comes back as Guideline 2.1 *"unable to locate the in-app purchases"*.

**③ Run this, once, so the next session can drive the iOS simulator:**

```
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

It needs your password, which is why it is here and not done. Detail in §6.

**④ Download the two store badges on launch day.** Neither is in the repository, on purpose:
both guidelines forbid redrawing the artwork and neither permits a badge for an app that is
not on the store. Take Apple's **black** badge and Google's unmodified SVG to
`public/badges/app-store.svg` and `google-play.svg`. `stores.test.ts` fails the build if a
store URL goes in without its artwork file.

**⑤ Fill in the imprint's blanks.** Left exactly as they are, deliberately:
`imprint` — registered address · registration number · representative · person responsible
for content · VAT/tax id · EU representative (GDPR Art. 27). `terms` — governing law · venue.
`privacy` — data transfer terms per processor · hosting region · lead supervisory authority.

**⑥ Confirm the support response time.** `/support` promises *"usually the same day and never
later than three working days"* in six languages. That is a commitment somebody wrote, not
one anybody measured. It is spelled out in each language rather than interpolated from a
constant, so changing it means editing six strings — deliberate friction for changing a
promise. Confirm it is one you will keep.

**⑦ Paste the two URLs into the consoles** once the host is up: `https://<host>/support`
into App Store Connect's Support URL, and `https://<host>/delete-account` into Play Console's
data-deletion field. Both pages are built and return 200; nothing in the repository can file
them for you.

---

### The daily needs three things, and none of them can be done from this repository

The daily is built end to end — selection, writing, validation, storage, cost ceilings,
localisation, the delivery job, both vendors and both clients. **Nothing has ever been sent**,
and the three reasons are all credentials or infrastructure.

**⑧ An APNs authentication key.** Apple Developer → Certificates, Identifiers & Profiles →
Keys → new key with *Apple Push Notifications service* enabled. It downloads once, as a
`.p8`, and cannot be downloaded again. Four values go into the server's environment:

```
ALMA_APNS_KEY_P8     the .p8 contents, or a path to the file
ALMA_APNS_KEY_ID     the 10-character Key ID from the same page
ALMA_APNS_TEAM_ID    the 10-character Team ID
ALMA_APNS_TOPIC      the bundle identifier — the app's, exactly
```

`ALMA_APNS_TOPIC` **is** the bundle identifier, which means this waits on ② above: the
App ID also has to have the Push Notifications capability enabled, and `aps-environment` is
already in `Alma.entitlements` waiting for it. A simulator build does not check the
entitlement, so this is invisible until the first device build. `python -m alma.notify.daily`
refuses to start and names every missing variable, which is the intended failure.

**⑨ An FCM service account, and the decision that comes with it.** Firebase console →
Project settings → Service accounts → generate a private key, into:

```
ALMA_FCM_SERVICE_ACCOUNT_JSON   the JSON, or a path to it
ALMA_FCM_PROJECT_ID             the Firebase project id
```

**This one is not only a credential.** Android has no push transport compiled in — `PushTokens`
is an interface with `NoPushTransport` behind it — because adding `firebase-messaging` pins
`google-services.json` to a package name ② has not chosen, and because Firebase Installations
arrives with it and falsifies two disclosures that currently read clean: DATA-INVENTORY §4's
*"the only Google dependency we ask for is Play Billing"*, and the Play *Device or other IDs*
row. `PUSH.md §7` requires both rewrites to land **before** the release that adds the
dependency, not with it. iOS is unaffected: it talks to Apple directly and stays clean.

Either platform can go alone. The job logs which platforms are configured and skips tokens on
the other rather than failing them.

**⑩ A cron. Three jobs exist and nothing runs any of them.**

```
0  *  * * *   cd /srv/alma/backend && .venv/bin/python -m alma.notify.daily
15 3  * * *   cd /srv/alma/backend && .venv/bin/python -m alma.billing.renewals
30 3  * * 0   cd /srv/alma/backend && .venv/bin/python -m alma.funnel --purge
```

**The daily one is hourly and that is not negotiable.** 08:00 happens twenty-six times around
the world, so a once-a-day job can only be 08:00 somewhere. It selects the people whose local
morning has just arrived and it is idempotent — running it twice in an hour sends once — so a
missed run costs one band of longitudes one hour rather than everybody a day. `--at <ISO>`
replays a specific hour.

A renewal notice a day late is survivable; a daily a day late is a lie about what day it is.
Whoever wires the first of these should wire all three, and `PUSH.md §8` recommends a
dead-man's switch on the hourly one — a job that silently stops is indistinguishable from a
quiet sky, which is this feature's own normal state.

---

## 5 · What is not done

Plainly, and in the order I would care about them.

### 5.1 · ~~iOS blocks its own review~~ — closed after this report was written

`AccountModel.beginDelete` no longer routes a guest to a sign-in prompt, `exportEverything`
no longer refuses one, and `SettingsScreen` shows a guest the account id they must type,
because a guest has no address to remember. The confirmation is compared case-insensitively
for an address and exactly for an id — an id is generated rather than recalled, and a folded
match would accept a near miss.

Verified: `xcodebuild` succeeded, the build was reinstalled, and the backend answered HTTP 200
to both export and delete on a fresh guest token, with the token dead afterwards.

All three surfaces now agree, which matters because App Review arrives as a guest holding a
birth time and a birthplace coordinate. The paragraphs in `/delete-account`, `/privacy` and
`/terms` that disclosed the iOS exception can be shortened; that is copy, not code.

### 5.2 · ~~Every landing page view creates an account row~~ — closed

An account is created by an act now: registering, saving a birth, or verifying a purchase.
Not by a visit, on any of the three clients.

`POST /v1/events` takes `deps.Visitor`, which resolves the bearer token and creates nothing;
`GET /v1/billing/catalogue` takes it too, which was the door left open when the first half of
this landed — `<Pricing/>` is rendered unconditionally and `useCatalogue` fetches on mount, so
a page view still minted a row through the price list. Both apps stopped calling
`GET /v1/auth/session` at launch, which is the route whose whole job is "mint or read": on
mobile every install was an account, which is 100% of the surface where almost all real users
are.

What answers "of the people who arrived, how many finished" instead is a client-generated
random id sent as `X-Alma-Anon` — `alma.anon` in local storage on the web, `UserDefaults` on
iOS, `alma.prefs` on Android, never the Keychain or the encrypted token store, because it
authorises nothing. The server claims it for the account at the one moment the join is a fact
rather than a guess: the request that mints. It is never created for a browser sending Do Not
Track or GPC, never created on Android while the Measurement switch is off, and every client
re-mints it after 180 days so the identifier cannot outlive the rows it keys.

Verified in Chrome against a pristine database: localStorage cleared, one load of `/`, nothing
clicked — 0 user rows, 1 event, no token in storage. Then the journey walked to a saved birth:
1 user, 1 profile, and `python -m alma.funnel` reporting landing_view → portrait_view at 100%
with `reached == total` throughout, which is the two halves folded into one person rather than
counted as two.

Still open, and reported rather than done: the iOS app has no Measurement switch, so on iPhone
the id is created on first launch with nothing to refuse it. Android has one and the web has
DNT. That is now the only place the three clients disagree about what a person can decline,
and it is written into `mobile/store/APP-PRIVACY.md` beside the declaration it affects.

### 5.3 · ~~The nav's primary button says "Sign up" and there is no sign-up~~ — closed

All five gold controls read one label from `journeyCta()` in `src/lib/cta.ts`: *Read myself —
free*, and its six translations. `nav.signUp`, `insight.cta`, `pricing.cta`, `final.cta` and
`ctaBar.cta` are deleted, so there is no second place for the promise to drift to. It is held
to what the journey actually does — asks for a date, a time and a place, computes the chart,
and hands over sun, moon, ascendant, life path, birth card and moon phase before charging
anything — by a six-language table in `cta.test.ts` that fails on any word offering an account.

The language picker exists, and it is reachable from every screen a person can be stuck on: the
footer, the mobile nav sheet, the desktop nav bar (the language's own name opens the same
sheet — the six endonyms measure 518 px against 320 px of slack, so the bar carries the one word
it has room for), inside the journey overlay, on `/sign-in`, and on `/support`. The five legal
documents deliberately do not get one: they render under `lang="en"` by policy, so a picker
there would offer a choice the page cannot honour.

### 5.4 · Two screens use "Saturn" to mean two different things

Today's headline reads *"Saturn is sitting on your career point"* — that is **transiting**
Saturn conjunct the natal Midheaven, correct and listed with its orb below. Natal Saturn is
27°04′ Pisces in the ninth house. Both statements are right, and I nonetheless walked
straight from one to the other and asked Alma a question with a false premise in it, which
she had to correct. The word "transiting" is missing from that headline. It is the kind of
confusion that reads to a customer as the product contradicting itself.

### 5.5 · Smaller, real, and pre-existing

- **A returning visitor's date field comes back empty.** `JourneyProvider` hydrates
  `sessionStorage` in a `useEffect`, but `DateCapture` seeds its `useState` from `state.date`
  on first render, so it never sees the restored value. After a reload the hero's sky
  correctly shows ♓︎ 14.03 while the three selects sit blank underneath it, and the gold
  button nudges for a date already given.
- **The receipt's "Manage your plan" button lands on a paragraph.** `RECEIPT_PLAN_PATH` now
  points at `/subscription-terms#cancel`, which explains cancellation but is not a control.
  Under IAP the real route is the store's own account page, and the letter cannot choose
  which because `Receipt` does not carry the buyer's platform.
- **`POST /v1/billing/subscription/cancel` is live with no caller anywhere.** Nothing sells
  through the card processors, so nobody has a subscription to cancel through it.
- ~~**There is no language picker on the web.**~~ Closed with 5.3 — `LanguagePicker` is in the
  footer, the nav sheet, the desktop bar, the journey overlay, `/sign-in` and `/support`.
- **The funnel has no rung below `portrait_view`.** Tapping through to a store is the
  storefront's only conversion and it is unmeasured. Deliberate: the stage cannot fire while
  `lib/stores.ts` has no URLs, and a rung that cannot fire reads as a collapse in conversion.
  Add it in the same change that fills in the store constants.
- **`/delete-account` is still English** while `/support` is translated. Worth doing in the
  same change that lands 5.1, since the iOS paragraph is about to be deleted from it.
- **`pricing.renewsNote`** ("cancel … Two taps, from Settings") now means the *app's*
  Settings and reads on the web as if it meant this website's.

---

## 6 · What I could not verify, and why

**I did not walk the iOS app.** It builds clean and it launches — I have a screenshot of a
correct cold start: *"Eight systems, one chart"*, the 4.3(b) argument, "Enter my birth data",
and the system list totalling 41 chapters. Its Debug build is correctly wired to
`http://localhost:8018` with the matching ATS exception (`ALMAAPIBase` in the built
`Info.plist`). But I could not tap anything, so the journey, a chapter and a question were
**not** exercised on iOS. Four routes, all closed:

1. The dedicated simulator MCP refuses to attach: *"Xcode is installed but not selected."* It
   looks for `/var/db/xcode_select_link`, which does not exist on this machine — I checked
   directly. `xcode-select -p` prints the right path, but the symlink the tool needs is
   absent. Fix is §4③ and it needs your password.
2. `xcrun simctl` has no tap, swipe or key subcommand. It installed, launched and
   screenshotted, and that is all it can do. **It is not equivalent to driving the app, and I
   am not presenting it as such.**
3. `idb` / `idb_companion` are not installed.
4. AppleScript UI-scripting is blocked: System Events returns
   *"Accessibility features for osascript are not allowed"* (−1719). That also needs you, in
   System Settings → Privacy & Security → Accessibility.

What this means practically: **Android is the platform whose end-to-end behaviour was proven
today.** iOS shares the same backend, the same catalogue and the same six locales, and its
own build is green — but the last time anyone drove its screens was a previous session, and
the guest-deletion blocker in §5.1 was found by reading its code, not by using it. Walk iOS
before submitting.

**Other things I did not verify:**

- **Ephemeris accuracy against an external source.** I verified that every number the AI
  spoke matches what the engine computed, and that the engine is internally consistent across
  three surfaces. I did not check the engine's positions against JPL myself; the backend's
  1490 tests are the evidence there.
- **The `carrySent` branch** of the handoff ("open the link we just sent to …"). Development
  has no mail provider, so the backend returns `debug_token` and the panel consumes it
  immediately, which makes the "sent" state unreachable locally. It is the common ending in
  production. One look on staging with mail configured.
- **Real store billing.** No products exist in either console, so every purchase path
  degrades to the billing-unavailable message. That message is correct; the purchase is not
  tested and cannot be until §4②.
- **Anything about performance on real hardware.** The emulator has no GPU
  (`lavapipe`/`swangle`, software rasterisers). Do not judge the ambient sky on it.
- **The browser pane spent much of the session backgrounded** (`document.visibilityState:
  "hidden"`), which made screenshots blank and swallowed some clicks. I drove and verified via
  the accessibility tree and the DOM instead, which is stronger for content and behaviour and
  weaker for layout. **I am not claiming pixel-level visual verification of the web.** Layout
  was last eyeballed in a previous session at 1280×720 and 375×812.

---

## 7 · What I changed today

Small and deliberate. Everything else in this document is a report, not an edit.

**1. The portrait told everybody they had two free systems. They do not.**
`journey.freeNote` read *"These two systems never cost anything"* in all six languages, under
a list of three rows. `FREE_SYSTEMS` in `backend/alma/auth/entitlements.py:67` is an **empty
frozenset** — whole free systems ended; what stayed free is every calculation plus one
written chapter per system. So the sentence promised more than the product delivers, on the
one screen whose entire job is proving the numbers are handled carefully.

Both apps had already caught it and fixed it on their own surface, each leaving a note
pointing at the web:

- `mobile/ios/…/ScreenL10n.swift:118` — *"The web's says 'These two systems never cost
  anything' and sits under three rows…"*
- `mobile/android/…/values/strings.xml:257` — *"…which stopped being true when the backend's
  `FREE_SYSTEMS` emptied… Only the false half was changed; the sentence after it is the
  web's, word for word."*

The web was the last surface carrying it. I took Android's already-translated replacement, in
which the second sentence is identical to the web's in every language, so only the false half
moved:

> **These numbers cost nothing, ever.** They are yours whether you read further or not.

Applied to all six dictionaries and confirmed live in the browser. I also rewrote the stale
comment above it in `JourneyOverlay.tsx`, which still told the next reader that `FREE_SYSTEMS`
enforced the promise.

**2. Four store documents said two pages did not exist. They do.**
`/support` and `/delete-account` are built and return 200. `README.md`, `LISTING.md`,
`SUBMISSION-CHECKLIST.md` (A3b, A4) and `REVIEW-NOTES.md` (§12 and the placeholder table) all
still described them as unbuilt and undecided — the packet was not edited when they landed
because two sessions were working in the repository at once. Corrected, each one now naming
the file, the URL to file, and the fact that the host is what remains. I also narrowed
`DATA-SAFETY.md` §2's claim that in-app deletion needs an account: it is iOS-only now.

Every gate in §2 was run **after** these edits.

---

## 8 · What today cost

**$0.037** of the $10 approved — one real chapter (2.70¢, `claude-sonnet-5`, 1822 in / 1437
out) and one real chat answer (0.99¢, `claude-haiku-4-5`), read from the `reading` and
`chat_message` cost ledgers rather than estimated.

I did not spend more because I did not need to. One generation of each proved the pipeline,
and both were checkable against the engine — which is what made them worth anything. A
hundred more would have produced a bigger number in this line and no additional confidence.
The model tiering visible in those two rows is also the intended behaviour: the chapter went
to Sonnet, the free guest's question went to Haiku.

---

## 9 · The shortest honest summary

The product works. A person can arrive on the web knowing nothing, be told something true and
checkable about themselves for free, and be handed to an app that computes the same chart and
writes about it in a voice that will correct you rather than flatter you. Seven gates are
green across four codebases.

Three things stand between here and a store: **the domain does not resolve**, **the
product-id prefix has not been decided**, and **iOS will not let a guest delete their
account**. The first two are yours. The third is code.

And one thing that is nobody's fault and worth knowing: nothing on iOS has been driven since
the last session, because this machine will not let an agent tap its simulator without a sudo
you have not run.
