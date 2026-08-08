# Apple — App Privacy, filled in

The App Store Connect questionnaire, answer by answer, ready to be typed. Every answer is
derived from `mobile/store/DATA-INVENTORY.md` and carries the file it was read out of.
Where the answer is a judgement rather than a fact, it says so and it is in the open
questions — it is not quietly resolved in the direction that looks best.

Read against the questionnaire's own definitions as quoted in
`mobile/store/STORE-REQUIREMENTS.md` §2, and against
<https://developer.apple.com/app-store/app-privacy-details/>.

**Two answers set the shape of the whole form.**

**Everything is Linked to You.** `api/deps.py:61–91` mints a `user` row on the first call
from any client and returns its token in `X-Alma-Token`, so there is no anonymous request
in this product — every category below is stored against an account identifier from the
first tap, before anybody has given us an email address. Apple's own qualifier is that data
counts as unlinked only if it was de-identified *before collection* and no attempt is made
to re-link it. Nothing here qualifies. Answering "not linked" anywhere on this form would
be a false declaration.

**Nothing is Used to Track You.** Apple's definition is linking our data to *Third-Party
Data* for advertising, or sharing with a data broker. There is no advertising identifier,
no third-party analytics SDK, no ad network and no broker anywhere in the codebase —
proved by absence in DATA-INVENTORY §4, not asserted. The consequence is that the app needs
no ATT prompt and no `NSUserTrackingUsageDescription`, and both are correctly missing from
`mobile/ios/Info.plist`. This is worth protecting: the first advertising SDK anyone adds
turns eight rows of this form to Yes and puts a permission prompt in front of the product.

---

## Threshold question

> Do you or your third-party partners collect data from this app?

**Yes.** The "Data Not Collected" answer is not available to us — birth date, birth time and
a birthplace coordinate are stored server-side against an account (`db/models.py:134–164`).

**Do not claim the optional-disclosure exemptions.** Apple exempts data that is collected
only occasionally, only at the user's initiative, in a clearly-labelled UI, and never used
for tracking or by a third-party analytics provider. The email address meets four of those
tests and fails the one that matters — it is retained as the account, not submitted once and
forgotten. Nothing else comes close.

---

## The grid

Fourteen categories, every subtype accounted for. `L` = Linked to the user, `T` = Used to
track. `T` is No on every row in this document.

### Contact Info

| Subtype | Collect | L | T | Purposes | Why, and where it is proved |
|---|---|---|---|---|---|
| **Email Address** | **Yes** | Yes | No | App Functionality | The account, and the only credential the deletion route accepts. `db/models.py:99–131`; the address is also held in clear on the sign-in row, `models.py:524–534`. Optional in practice — a guest never gives one — but Apple's form has no optional flag, so it is declared as collected. |
| **Name** | **Yes** | Yes | No | App Functionality | Two places: `user.display_name` from the identity provider or typed in Settings (`models.py:99–131`), and `profile.name`, which numerology actually reads (`calc/service.py:181`). The profile name may be a third party's — a compatibility profile is a second person's birth (`routers/readings.py:375–401`). |
| Phone Number | No | — | — | — | No column, no field, no screen. |
| Physical Address | No | — | — | — | Never collected. On a store build `buyer_email` is `None` from both adapters (`billing/appstore.py:976–987`, `billing/googleplay.py:638`) and no billing address reaches us. |
| Other User Contact Info | No | — | — | — | — |

### Health & Fitness

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| Health | **No** | — | — | — | Nothing solicits, derives or stores health data. No HealthKit, no health field in any model. A person *may* type a health worry into a chat message — that is unsolicited free text and it is declared under User Content, which is where Apple's taxonomy puts it. Declaring Health would state that we process health data, which is false in the other direction. |
| Fitness | **No** | — | — | — | — |

### Financial Info

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| Payment Info | **No** | — | — | — | The card never reaches our servers on any build (DATA-INVENTORY §4). Inside this app Apple is the merchant of record and Apple takes the payment; the signed transaction is verified locally against the pinned Apple Root CA G3 (`billing/appstore.py:106+`) and there is no App Store Server API call in that file. |
| Credit Info | No | — | — | — | — |
| Other Financial Info | **No** | — | — | — | The amount, currency and country on `purchase` (`models.py:259–315`) are the record of a sale, which Apple's taxonomy puts under Purchases → Purchase History. Declaring them twice would misdescribe them. |

### Location

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| **Precise Location** | **Yes** | Yes | No | App Functionality | `profile.latitude` / `profile.longitude`, stored as full-precision floats (`models.py:134–164`). It is a birthplace, not a device reading, and the whole product is arithmetic on it — but it is a coordinate about a person and Apple's definition is resolution-based, so it is declared. |
| Coarse Location | **No** | — | — | — | Considered and rejected on the record: `purchase.country` and Apple's storefront code arrive in the transaction (`models.py:259–315`), and Apple's Coarse Location means approximate *location services*, not a storefront. It is declared under Purchase History instead. If the owner prefers the belt-and-braces answer, flipping this to Yes / Linked / No-tracking costs nothing but a line on the label. |

**Say this in the review notes, because a reviewer will check.** Precise Location is declared
and the app requests no location permission — there is no `NSLocationWhenInUseUsageDescription`
in `mobile/ios/Info.plist` and no `CoreLocation` import anywhere in `mobile/ios/Alma/`. The
coordinate is chosen by the person from a search box against a bundled offline gazetteer
(`alma/geo.py:1–20`, `api/routers/places.py`), and **no geocoding request leaves the server** —
the most location-revealing interaction in the product has no network recipient at all. A
declared location type with no location entitlement reads as an inconsistency unless it is
explained; explain it.

### Sensitive Info

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| **Sensitive Info** | **Yes — owner's call, recommended Yes** | Yes | No | App Functionality | See below. |

Apple's public page does not enumerate this category; the in-console definition is the
operative text and must be read at fill-in time. The definition Apple has used covers racial
or ethnic data, sexual orientation, pregnancy, disability, religious or philosophical
beliefs, trade union membership, political opinion, genetic and biometric data.

**The case for Yes.** `chat_message.body` is `Text`, 2000 characters a turn, unfiltered
(`models.py:457–488`, `api/schemas.py:172`) — a person may put any of those categories into
it, and `memory` then stores what the model extracted from it as free text
(`models.py:491–508`, `ai/conversation.py:58–67`). Beyond that, Alma is a divination product:
choosing to consult it, and the compatibility system in particular, sits close enough to
"religious or philosophical beliefs" that a reviewer could reasonably read it that way.
Declaring costs a line on the public label and nothing else — there is no ATT consequence,
because tracking is No.

**The case for No.** We neither solicit nor infer a single one of Apple's enumerated
categories. Declaring Sensitive Info tells a shopper on the product page that the app
collects racial, sexual-orientation or biometric data, and it does not.

**Recommended: Yes.** Under-declaration is what gets an app pulled after launch;
over-declaration is a line of label copy. But it is the owner's to sign.

**Birth data is declared either way — see Other Data below.** Apple's taxonomy has no type
for a date of birth, so if Sensitive Info goes to No, birth date and birth time still have to
land somewhere. They do.

### Contacts

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| Contacts | **No** | — | — | — | No contacts permission in `Info.plist`, no address-book API anywhere in `mobile/ios/Alma/`. A compatibility profile is typed by hand. |

### User Content

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| Emails or Text Messages | **No** | — | — | — | Apple's subtype is messages with a sender and recipients. A thread here is a person and the service; there is no messaging between users anywhere in the product. Declared as Other User Content instead, where it belongs. |
| Photos or Videos | No | — | — | — | — |
| Audio Data | No | — | — | — | No microphone usage string, no audio capture. |
| Gameplay Content | No | — | — | — | — |
| Customer Support | **No** | — | — | — | There is no in-app support form; `hello@pazl.ai` is an ordinary mailbox reached by a `mailto:` link. **This flips to Yes the day an in-app contact form ships.** |
| **Other User Content** | **Yes** | Yes | No | App Functionality · Product Personalization | Three things, and each is separately worth naming. Chat messages, free text, 2000 chars a turn (`models.py:457–488`) — plus `chat_thread.title`, which is the first 80 characters of the first message (`routers/readings.py:772`), i.e. a slice of the same free text. Memory: short strings the model extracted from what a person stated about their life (`models.py:491–508`). Generated readings, stored whole (`models.py:405–438`). Product Personalization is on the list honestly: memory exists so that Alma does not ask in March what was answered in January, which is customising what the person sees. |

### Browsing History

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| Browsing History | No | — | — | — | No webview, no URL is recorded anywhere. The funnel event model has five columns and no URL field (`models.py:537–576`). |
| Search History | **No — contingent** | — | — | — | The one search in the product is the birthplace box, and it travels as a query string: `GET /v1/places/search?q=…` (`api/routers/places.py:17–27`). Nothing stores it — there is no search table and no request-logging middleware in `api/app.py` — so under Apple's definition ("retained longer than necessary to service the request") it is not collected. **That answer depends on the host.** A birthplace name in a URL query string lands in any default access log, and the hosting question is unanswered (DATA-INVENTORY §1.17). If the host retains query strings, this becomes Yes. Two ways out: get the answer, or move the query to a POST body so it never reaches a log line. |

### Identifiers

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| **User ID** | **Yes** | Yes | No | App Functionality · Analytics | `user.id`, `secrets.token_urlsafe(16)`, minted by an **act** — a birth saved, a sign-in landed, a purchase verified — rather than by the first call from any client, which is what it used to be (`models.py:61–63`, `api/deps.py`, `current_user`). Analytics is on the list because the account id is one of the two attributions on a funnel event (`alma/funnel.py`); the other is the Device ID below, and there is nothing else to join on. |
| **Device ID** | **Yes** | Yes | No | Analytics | **New on 7 August 2026; this row said No until then.** An app-generated UUID kept in `UserDefaults` (`Networking/InstallationId.swift`) and sent as `X-Alma-Anon` on every request. It exists because the account is no longer minted by opening the app — `start()` called `GET /v1/auth/session`, which mints, so every install was an account before anybody had typed anything — and "of the people who opened the app, how many finished" needs something to tell one install from another. Still no IDFA, no `identifierForVendor`, no `ASIdentifierManager`, no `AppTrackingTransparency`, no `NSUserTrackingUsageDescription`. **Linked: Yes** — the server records the join the moment an act creates an account out of this install (`funnel.claim`), so it is unlinked only until it is not. **Tracking: No** — not an advertising id, never joined with another company's data, never leaves our backend, never sold; `NSPrivacyTracking` stays `false` and the app still needs no ATT prompt. It is not the bearer token: that is a credential and lives in the Keychain, which is precisely why this one does not. Deleted with the account, gone when the app is deleted, and re-minted by the client after `funnel.PURGE_AFTER_DAYS`. |

**The same row also covers the APNs push token, and that is why the purpose list is not just
Analytics.** Apple's form takes one entry per data type; these are two identifiers sharing
one row and they have nothing else in common. The anon UUID above is ours, minted by the app,
for Analytics. The **push token** is Apple's, issued to this install, held only while the
daily is switched on, and used for one thing: delivering it — **App Functionality**. Add that
purpose to the Device ID row on the form, and to `PrivacyInfo.xcprivacy`, where it is
already declared.

Registered by `Daily/DailyModel.registerIfPossible` through
`POST /v1/notifications/devices`; deleted by `POST /v1/notifications/devices/delete` the
moment somebody turns the daily off or iOS revokes the permission; deleted with the account
(`accounts.erase` → `notify.tokens.forget`); and swept server-side after ninety days without
the app being opened. **Linked: Yes** — it is stored against the account it was registered
by. **Tracking: No** — not an advertising identifier, never joined with another company's
data, never leaves our backend except to Apple, who issued it. It is not returned by the
account export, and that is deliberate: it is a live delivery credential, and Article 15 asks
that the subject know what is held, not that we make copies of a secret. The export names the
device instead.

### Purchases

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| **Purchase History** | **Yes** | Yes | No | App Functionality | `purchase` (`models.py:259–315`) and `entitlement` (`models.py:167–256`): what was bought, when, the amount, the currency, the country, and Apple's own `transactionId`. It is the only thing that unlocks content, and it is a tax record. Note for retention below: this is the one table that survives account deletion. |

### Usage Data

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| **Product Interaction** | **Yes** | Yes | No | Analytics · App Functionality | Two things. The funnel: nine stage names from a closed set (`funnel.py:124–142`) with an eight-key property allowlist (`funnel.py:154–156`), no IP, no user agent, no referrer, no URL, no device id, no free text of any kind — verified in the model and in the writer. And the counters (`models.py:511–521`), which are App Functionality rather than Analytics: `questions` and `questions_month` are what make a free tier countable (`routers/readings.py:75–79`), and `spend_cents` is what a generation cost *us* (`ai/cost.py:178`). |
| Advertising Data | **No** | — | — | — | There is no advertising anywhere in the product. |
| Other Usage Data | No | — | — | — | Everything measurable is above. |

**Say this on the form and in the review notes.** Product Interaction is declared with
Analytics as a purpose and **there is still no opt-out inside the iOS app.** The web build
honours Do Not Track and Global Privacy Control on every call (`src/lib/track.ts`), and
Android has a Settings toggle that suppresses the beacon *and* prevents the installation id
being created at all (`data/Measurement.kt`) — which is what lets its Data safety entries be
declared Optional. iOS has neither signal: there is no OS-level do-not-track to read and no
toggle of our own yet, so both the beacon and the installation id are unconditional there.

That is not a violation on its own — Apple's form has no optional/required distinction — but
the shipped in-app privacy text says "there is nothing to opt out of because there is nothing
running" (`Screens/Settings/LegalText.swift:290–294`), and a person reading that inside the
app while it posts analytics beacons and keeps an installation id would reasonably feel
misled. It is now also the one place the three clients disagree about what a person can
refuse. Either ship the Settings toggle Android already has, or fix the sentence. See
PRIVACY-DELTA.

### Diagnostics

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| Crash Data | **No** | — | — | — | No Sentry, no Crashlytics, no Bugsnag, no Instabug; `project.pbxproj` declares no framework build phase at all, so the iOS binary links no third-party framework. Whatever Apple collects through App Store Connect under the user's own device-analytics setting is Apple's collection and is not declared here. |
| Performance Data | **No** | — | — | — | Same. |
| Other Diagnostic Data | **No — contingent** | — | — | — | Nothing in the repository stores an IP address, a user agent or a referrer, and there is no request-logging middleware in `api/app.py`. But every proxy and TLS terminator logs by default and **nobody has answered what the production host retains** (DATA-INVENTORY §1.17). If the host keeps access logs beyond servicing the request, the honest answer is Yes / Not Linked (a log line carries an IP and a path; the account token is a header and the account id is not in the URL). Get the answer before filing. |

### Surroundings

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| Environment Scanning | No | — | — | — | No ARKit, no camera. |
| Body (Hands, Head) | No | — | — | — | — |

### Other Data

| Subtype | Collect | L | T | Purposes | Why |
|---|---|---|---|---|---|
| **Other Data Types** | **Yes** | Yes | No | App Functionality | **Birth date and birth time.** Apple's fourteen categories have no box for a date of birth, and this is the most sensitive field in the product — `birth_date`, and `birth_time` as an exact `"HH:MM"` wall clock (`models.py:134–164`). Also `timezone`, `place_label` and `relation`. When Apple asks what "Other" is, the answer to type is: *date and time of birth, the IANA time zone derived from the birthplace, the birthplace label, and an optional one-word relationship label for a profile about another person.* |

**Do not let the taxonomy swallow the birth time.** If Sensitive Info goes to No, this row is
the only place a birth date and a birth time appear on the entire form. It stays Yes under
either branch.

---

## What that produces on the label

**Ten data types, in eight categories.** All Linked to You, none used to track. Count the
types, not the bullets: Apple's form is ticked type by type, and both Contact Info and
Identifiers hold two of them.

| Category | Types to tick |
|---|---|
| Contact Info | **Email Address**, **Name** *(two)* |
| Location | **Precise Location** |
| Sensitive Info | **Sensitive Info** *(owner's call — see the open question)* |
| User Content | **Other User Content** |
| Identifiers | **User ID**, **Device ID** *(two)* |
| Purchases | **Purchase History** |
| Usage Data | **Product Interaction** |
| Other Data | **Other Data Types** |

This paragraph said "eight types" until 7 August 2026, which was Apple's *category* count
read as a type count, and "nine" for the few hours between that correction and the
installation id landing. `PrivacyInfo.xcprivacy` contains ten `NSPrivacyCollectedDataType`
dicts — verified with `plutil` and `plistlib` against the file — so anybody filling the
console form from the summary and counting wrong leaves a type unticked, and the
manifest-versus-console comparison surfaces that at upload.

**One required-reason API is now declared, and it is the other half of the same change.**
`NSPrivacyAccessedAPITypes` was an empty array under a comment saying the app touches no
`UserDefaults`; the installation id lives there now, so the manifest declares
`NSPrivacyAccessedAPICategoryUserDefaults` with reason `CA92.1` — information accessible
only to this app itself, no app group, no third-party SDK. Without it the upload is answered
with ITMS-91053 and the build is not distributable, which makes this a submission blocker
rather than a form detail.

**If Sensitive Info is decided No, two things change together, in one sitting:** the console
answer, and the corresponding dict in `PrivacyInfo.xcprivacy`. The count becomes eight types
in seven categories. The birth date and the birth time stay declared under Other Data Types
either way, so nothing goes undisclosed on either branch — that is what makes the decision
safe to take at fill-in time rather than now.

---

## The privacy manifest

Written to **`/Users/anatoliymikhaylow/alma_project1/mobile/ios/Alma/PrivacyInfo.xcprivacy`**. It declares the same
nine types with the same linked/tracking/purpose answers as the grid above, and the two
must stay in agreement — Xcode builds a privacy report from the app manifest plus every
SDK's, and that report is what you check the App Store Connect answers against.

**The manifest has already answered the Sensitive Info question and the form has not.** The
shipped file declares `NSPrivacyCollectedDataTypeSensitiveInfo`. If the console answer comes
out No while the manifest still says Yes, that is a divergence Apple surfaces at upload; if
it comes out Yes, the public nutrition label tells shoppers Alma collects sensitive
categories it does not touch. Read the in-console definition (the public page does not
enumerate the category), decide once, and change both in the same commit.

**Where it sits and why.** `mobile/ios/Alma/` is a `PBXFileSystemSynchronizedRootGroup`
(`Alma.xcodeproj/project.pbxproj:14–20`), so a file dropped into it joins the target
automatically and a resource lands in the app bundle's root — which is exactly where an app
target's privacy manifest must be. `Info.plist` is deliberately kept *outside* that folder
because it would otherwise be copied in as a stray resource; `PrivacyInfo.xcprivacy` is the
opposite case and belongs inside.

**Verify once in Xcode**, because that project file is hand-written: open the Alma target →
Build Phases → Copy Bundle Resources and confirm `PrivacyInfo.xcprivacy` is listed. If a
synchronized group has not picked it up, add it there explicitly.

**`NSPrivacyAccessedAPITypes` is an empty array, and that is a finding rather than an
oversight.** The five required-reason families are file timestamps, system boot time, disk
space, active keyboards and `NSUserDefaults`. Grepped across `mobile/ios/`: no
`UserDefaults` (the token is in the Keychain, and `TokenStore.swift:6–8` says why in its own
comment), no `creationDate` / `modificationDate` / `stat`, no `systemUptime` or
`mach_absolute_time`, no `volumeAvailableCapacity`, no `activeInputModes`. The one
`FileManager` call in the app is `temporaryDirectory` for writing the user's own data export
so the share sheet can hand it to them (`Screens/Settings/AccountModel.swift:201`), and
`temporaryDirectory` is not on any required-reason list. The array stays empty until an SDK
arrives — and the iOS app currently links no third-party framework at all, so there is no
SDK manifest to merge.

**`NSPrivacyTracking` is `false` and `NSPrivacyTrackingDomains` is empty.** Apple requires
the array to be empty when tracking is false, and if it ever stops being empty the app needs
an ATT prompt before those domains can be reached.

---

## Consistency checks before you press submit

1. **The manifest, the ASC form and the in-app policy must say the same thing.** The iOS app
   ships its own copy of the privacy policy in the binary
   (`Screens/Settings/LegalText.swift:245–378`) — that is the document a reviewer opens, and
   PRIVACY-DELTA lists five sentences in it that contradict this form today. Fix those first;
   they are the ones that reach 5.1.1(i) and 5.1.2(i).
2. **5.1.2(i) — "including with third-party AI".** Apple now requires explicit disclosure of
   personal data shared with a third-party AI provider, and consent. Anthropic receives the
   birth date, the birth time to the minute, the birthplace label and the name verbatim in
   every chapter prompt (`ai/writer.py:152–164`), the last twelve messages of a thread in
   every chat turn (`ai/conversation.py:128–133`), and the remembered free-text facts in the
   system prompt of both (`ai/voice.py:112–119`). The in-app policy currently says the name
   is *not* sent. That sentence is the single most important fix in PRIVACY-DELTA.
3. **5.1.1(i) — the policy must describe retention and deletion.** The in-app text says
   deletion is total; `auth/accounts.py:360–397` keeps the purchase rows detached, keeps the
   webhook rows redacted, and keeps the `user` row as a tombstone. The policy has to say so.
4. **5.1.1(v) — account deletion in the app.** It exists on iOS
   (`Networking/AlmaClient.swift:128`), and it requires an account: `require_account` rejects
   a guest (`api/deps.py:97–104`) and the confirmation string is compared against
   `user.email`, which a guest has not got (`api/routers/account.py:60–80`). A person who
   bought without signing in has birth data, readings and a payment record here with no
   in-app route to any of them. Apple's own words are that *all* users must be able to delete
   their accounts. The Settings screen must say what the web page already says — sign in with
   the address you paid with, or write to `hello@pazl.ai` and a person does it by hand.
5. **The privacy policy link is required in the ASC metadata field *and* in the app.** Both
   exist; the in-app route is Settings → Privacy (`Screens/Settings/LegalText.swift`).
6. **Age.** `src/lib/legal.ts:65` sets `MIN_AGE = 16` and three legal pages repeat it.
   `api/schemas.py:63–70` accepts any birth date from 1900 to 2100 and no screen asks. The
   number on this form, the number in the policy and the behaviour of the app all have to
   agree before either store's children's-data rules are answered honestly.
