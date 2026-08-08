# Google Play — Data safety, filled in

The Play Console form, answer by answer, ready to be typed. Derived from
`mobile/store/DATA-INVENTORY.md`; every answer carries the file it was read out of. Where
the answer is a judgement it says so and it is in the open questions.

Read against Play's own definitions as quoted in `mobile/store/STORE-REQUIREMENTS.md` §11,
and against <https://support.google.com/googleplay/android-developer/answer/10787469>.

**This is not the Apple form with different labels.** Play has no "linked to you" and no
"used to track"; it has *shared*, *required vs optional*, *ephemeral processing*, and a
purpose list per data type. Apple has no "optional" and no "Messages" bucket. The two forms
describe the same reality and cannot share answers. `mobile/store/APP-PRIVACY.md` is the
Apple half; the facts under both are the same and live in DATA-INVENTORY.

**Three definitions decide most of the rows.**

**Collection** is transmitting data off the device in a way we can access. Everything below
is transmitted to our own backend and stored in our own database, so almost nothing here is
a No.

**Ephemeral processing** — held in memory only, for no longer than servicing the request —
does *not* rescue us. Birth data is written to a `profile` row (`db/models.py:134–164`) and
kept until the person changes or deletes it. Declare it collected.

**Sharing** is transfer to a third party, with a carve-out for a service provider processing
on our instructions. Every "Shared: No" on this form rests on that carve-out for Anthropic
and Resend, and the carve-out rests on having a data processing agreement with each.
**Do not file this form until those are confirmed** — see the open questions. If there is no
DPA with Anthropic, the honest answer for four rows flips to Yes, and Anthropic receives the
birth date, the birth time to the minute, the birthplace label, the name, and the last twelve
messages of a conversation (`ai/writer.py:152–164`, `ai/conversation.py:128–133`).

---

## Data types

`Req` = required (the person cannot use the app without it) or optional (a feature they can
choose not to use, per Play's own test). `Eph` = processed ephemerally.

### Location

| Type | Collected | Shared | Eph | Req | Purposes | Why, and where it is proved |
|---|---|---|---|---|---|---|
| **Precise location** | **Yes** | No | No | Required | App functionality | `profile.latitude` / `profile.longitude`, full-precision floats (`models.py:134–164`). Every position in every chapter is computed from that coordinate against the JPL DE440s ephemeris; there is no product without it. |
| Approximate location | No | — | — | — | — | We do not separately collect a coarse location. `purchase.country` and Google's `regionCode` (`billing/googleplay.py:610–612`) come from the transaction, not from location services, and are declared under Financial info → Purchase history. |

**Note it in the form's free-text and in the review notes.** This is a *birthplace*, not a
device position. `AndroidManifest.xml:4–7` declares two permissions — `INTERNET` and
`com.android.vending.BILLING` — and neither `ACCESS_FINE_LOCATION` nor `ACCESS_COARSE_LOCATION`
appears in the manifest or in the merged manifest. The coordinate is chosen by the person
from a search box against a bundled offline SQLite gazetteer (`alma/geo.py:1–20`,
`api/routers/places.py`), and **no geocoding request leaves the server**. Declaring precise
location with no location permission looks inconsistent unless it is explained.

### Personal info

| Type | Collected | Shared | Eph | Req | Purposes | Why |
|---|---|---|---|---|---|---|
| **Name** | **Yes** | No | No | Optional | App functionality | `user.display_name` (`models.py:99–131`) and `profile.name`, which numerology reads (`calc/service.py:181`). Alma works without either. The profile name may be a third party's — compatibility needs a second birth (`routers/readings.py:375–401`) and nothing asks whether that person consented. |
| **Email address** | **Yes** | No | No | Optional | App functionality · Account management | The account, and the only credential the deletion route accepts (`api/routers/account.py:73`). Null until somebody signs in; the app is fully usable without one, which is what "reading Alma without signing in" is. Also held in clear on the sign-in link row (`models.py:524–534`) and transmitted to Resend as the envelope address (`alma/mail.py:40`). |
| **User IDs** | **Yes** | No | No | **Required** | App functionality · Analytics | `user.id`, `secrets.token_urlsafe(16)` (`models.py:61–63`), minted on the first call from any client (`api/deps.py:61–91`). There is no way to use the app without one, so this is required, not optional. Analytics because the account id is the only attribution a funnel event carries (`funnel.py:26–28`). |
| **Other info** | **Yes** | No | No | **Required** | App functionality | **This is where the birth date and the birth time go.** Play's own examples for this subtype are date of birth and the like, and that is exactly what it is: `birth_date`, and `birth_time` as an exact `"HH:MM"` wall clock (`models.py:134–164`), plus the derived IANA `timezone`, the `place_label`, and the optional `relation` word on a profile about somebody else. Type that list into the description field; do not leave the most sensitive datum in the product described as "other". |
| Address | No | — | — | — | — | Never collected. `buyer_email` is `None` from the Play adapter (`billing/googleplay.py:638`) and no billing address reaches us. |
| Phone number | No | — | — | — | — | No column, no field. |
| Race and ethnicity | No | — | — | — | — | Never solicited, never inferred. |
| Political or religious beliefs | **No** | — | — | — | — | Never solicited and never inferred. A person may state one inside a chat message, which is unfiltered free text — that is declared under Messages, which is the type Play provides for it. Declaring this row Yes would say we ask about beliefs, and we do not. *(See the note below: this is the row that pairs with Apple's Sensitive Info question, and the two answers are allowed to differ because the two forms are built differently.)* |
| Sexual orientation | **No** | — | — | — | — | Same reasoning. Compatibility takes two births and asks nothing about who the second person is. |

**On the belief question, and why Play and Apple can differ here.** Apple's Sensitive Info
is one undifferentiated bucket and its in-console definition sweeps in "religious or
philosophical beliefs", which is why APP-PRIVACY recommends declaring it. Play splits the
same territory into a *belief* type and a *messages* type, and gives us the honest place to
put unfiltered free text. Declaring Play's belief row would assert something about our
collection that is not true; declaring Messages asserts exactly what is. If the owner
answers Apple's Sensitive Info question No, nothing on this form changes.

### Financial info

| Type | Collected | Shared | Eph | Req | Purposes | Why |
|---|---|---|---|---|---|---|
| **Purchase history** | **Yes** | No | No | Optional | App functionality | `purchase` (`models.py:259–315`) and `entitlement` (`models.py:167–256`): what was bought, when, the amount, the currency, the country, and Google's own order id. Optional under Play's test — a person who never buys never generates a row. Note for the retention question below: this is the one table that survives account deletion. |
| Payment info | **No** | — | — | — | — | The card never reaches our servers. Google is the merchant of record; the backend sends Google a package name and a purchase token and gets a purchase state back (`billing/googleplay.py:102`). |
| Credit score / Other financial info | No | — | — | — | — | — |

### Health and fitness

| Type | Collected | Shared | Eph | Req | Purposes | Why |
|---|---|---|---|---|---|---|
| Health info | **No** | — | — | — | — | Nothing solicits, derives or stores health data; no health field in any model and no health permission. A health worry typed into a chat message is unsolicited free text and is declared under Messages. |
| Fitness info | No | — | — | — | — | — |

### Messages

| Type | Collected | Shared | Eph | Req | Purposes | Why |
|---|---|---|---|---|---|---|
| **Other in-app messages** | **Yes** | **No — conditional on the DPA** | No | Optional | App functionality · Personalization | `chat_message.body` is `Text`, whatever the person typed, up to 2000 characters a turn (`models.py:457–488`, `api/schemas.py:172`), and `chat_thread.title` is the first 80 characters of the first message (`routers/readings.py:772`). This is the highest-risk field in the product and nothing filters it. **The last twelve messages of a thread, both sides, are transmitted verbatim to Anthropic on every turn** (`ai/conversation.py:128–133`, `MAX_HISTORY = 12`). That is the transfer the "Shared: No" answer depends on the DPA to justify. |
| Emails | No | — | — | — | — | No mailbox access of any kind. |
| SMS or MMS | No | — | — | — | — | No SMS permission in the manifest. |

### Photos and videos · Audio files · Files and docs · Calendar · Contacts

**All No.** No such permission in `AndroidManifest.xml` and no such API anywhere in
`app/src/main/kotlin/ai/pazl/alma/`.

### App activity

| Type | Collected | Shared | Eph | Req | Purposes | Why |
|---|---|---|---|---|---|---|
| **App interactions** | **Yes** | No | No | **Required** | Analytics · App functionality | Two things. The funnel: nine stage names from a closed set (`funnel.py:124–142`) with an eight-key property allowlist (`funnel.py:154–156`) — no IP, no user agent, no referrer, no URL, no device id, no session id, no free-text field, verified in the model and in the writer, and an unknown name is a 422 rather than a row. And the daily counters (`models.py:511–521`), which are App functionality rather than Analytics: `questions` and `questions_month` are what make a free tier countable (`routers/readings.py:75–79`). **Now Optional** — Settings has a Measurement switch (`settings_measurement`), backed by `data/Measurement.kt`, and `AlmaClient.record` returns without sending when it is off. That closes the gap this row used to describe: the web build honours Do Not Track and GPC on every call (`src/lib/track.ts:106–120`) and the app had no equivalent, so the linked privacy policy was offering an opt-out that did not exist on the platform the reader was holding. **Declare App interactions as Optional, not Required.** |
| **Other user-generated content** | **Yes** | No | No | Required | App functionality · Personalization | The remembered facts — short strings the model extracted from what a person stated about their life, at most two a turn (`models.py:491–508`, `ai/conversation.py:58–67`) — and the generated readings, stored whole (`models.py:405–438`). Memory is free text of the person's own, restated; it is not chart data and must not be folded into it. **The eight most recent memories are transmitted to Anthropic in the system prompt of every generation, chapters and chat alike** (`ai/voice.py:112–119`, `routers/readings.py:458–467`). Personalization is honest: memory exists so Alma does not ask in March what was answered in January. |
| In-app search history | **No — contingent** | — | — | — | — | The one search in the product is the birthplace box, and it travels as a query string: `GET /v1/places/search?q=…` (`api/routers/places.py:17–27`). Nothing stores it — no search table, no request-logging middleware in `api/app.py` — so it is not collected. **That depends on the host.** A birthplace name in a URL query string lands in a default access log, and nobody has answered what the production host retains (DATA-INVENTORY §1.17). Either get the answer or move the query into a POST body so it never reaches a log line. |
| Installed apps | No | — | — | — | — | No `QUERY_ALL_PACKAGES`, no `<queries>` block. |
| Other actions | No | — | — | — | — | Everything measurable is above. |

### Web browsing

**No.** No webview in the app; the legal links open the browser at the public site
(`ui/screens/SettingsScreen.kt:586–596`), which is a hand-off, not a collection. Nothing
records a URL: the `event` model has five columns and no URL field (`models.py:537–576`).

### App info and performance

| Type | Collected | Shared | Eph | Req | Purposes | Why |
|---|---|---|---|---|---|---|
| Crash logs | **No** | — | — | — | — | No Crashlytics, no Sentry, no Bugsnag, no Instabug; `firebase-crashlytics` is not in `libs.versions.toml` or `app/build.gradle.kts`. Whatever Play Console collects on its own is Google's collection, not ours. |
| Diagnostics | **No** | — | — | — | — | No performance SDK. Server access logs are a hosting question, and Play's type list has no category for an IP address in a proxy log — which means the unanswered hosting question changes the *privacy policy text* more than it changes this form. It still has to be answered. |
| Other app performance data | No | — | — | — | — | — |

### Device or other IDs

| Type | Collected | Shared | Eph | Req | Purposes | Why |
|---|---|---|---|---|---|---|
| **Device or other IDs** | **Yes** | No | No | **Optional** | Analytics | **New on 7 August 2026; this section said No until then.** An app-generated `UUID.randomUUID()` kept in the ordinary `alma.prefs` file (`data/Measurement.kt`) and sent as `X-Alma-Anon` on every request by `AlmaHttp.SessionInterceptor`. It exists because the account is no longer minted by opening the app — `SessionHolder.start()` called `GET /v1/auth/session`, which mints, so every install was an account before anybody had typed anything — and "of the people who opened the app, how many finished the journey" needs something to tell one install from another. **Not an advertising identifier**, and everything below about `AD_ID` still holds unchanged. |

**A second identifier now lives under this type, and it is not optional.** The **FCM
registration token**, held while the daily is switched on. It is a different thing from the
anon id in every way that matters to this form: issued by Google rather than minted by us,
used for **App functionality** rather than Analytics, and *not* preventable by a switch —
which is Play's own test for Optional. Turning the daily off does not stop a collection from
being useful, it **deletes the row** (`notify/tokens.forget`, called from
`PATCH /v1/notifications` and from `accounts.erase`), so there is nothing left to be optional
about. Play takes one row per data type, so the row above must be filed as **Collected: Yes,
Optional: No, Purposes: Analytics + App functionality** — the union of the two identifiers.

Retention differs too, and it is shorter: a token is deleted on sight when Google reports the
registration gone, swept after **90 days** without the app being opened, and deleted with the
account. The 60-day figure people will also see is `rules.DORMANT_AFTER`, which is when we
stop *sending*. Go quiet first, forget second.

**Nothing here is live yet on Android.** `PushTokens` is an interface with `NoPushTransport`
behind it and `firebase-messaging` is not in the build, so no token is minted on this
platform today. This row must be filed as Yes **for the release that adds the dependency**,
not before, and adding it also falsifies §4's "the only Google dependency we ask for is Play
Billing" — Firebase Installations arrives with it. `PUSH.md §7` requires both rewrites to
land *before* that release, not with it.

**Optional, and it is the toggle that earns that word.** Play's test for Optional is that the
person can prevent the collection, not merely stop it being useful — so the Measurement switch
in Settings does not gate the *sending*, it gates the *minting*: with it off, `Measurement.anonId()`
returns null, the interceptor sets no header, and turning it off deletes the id already stored
(`forgetInstallation`). Nothing is written to the device at all. That is the same shape as the
App interactions row above and for the same reason, and it is the one place the Android build is
ahead of iOS, which has no such switch and therefore declares its Device ID unconditionally on
Apple's form.

**Not the bearer token, and deliberately not stored beside it.** The token is a credential and
lives in encrypted `SharedPreferences` behind an `AndroidKeyStore` key (`data/TokenStore.kt`);
this id authorises nothing, buys nothing, and signs into nothing, which is exactly why it is in
plain preferences instead. It is deleted with the account (a 410 or a Settings deletion clears
both), it goes when the app is uninstalled, and the client re-mints it after
`funnel.PURGE_AFTER_DAYS` so it cannot outlive the rows it keys.

**Two verification steps before you answer the advertising-id question.** Play Billing 8.3.0 pulls
`com.google.android.gms:play-services-*`, `com.google.android.datatransport:*` and
`com.google.firebase:firebase-encoders*` in transitively; the only Google dependency we ask
for is `com.android.billingclient:billing-ktx 8.3.0` (`libs.versions.toml:26`, `:48`), and
nothing in our code calls any of them. That is the answer if Play's review asks.

1. **Check the merged *release* manifest for `AD_ID`.** The merged debug manifest is clean —
   `app/build/intermediates/merged_manifests/debug/…/AndroidManifest.xml` contains
   `INTERNET`, `com.android.vending.BILLING`, `ACCESS_NETWORK_STATE` (merged in
   transitively) and a debug-only receiver permission, and no advertising-id permission. Run
   the same check on a release build. If `AD_ID` ever appears, remove it explicitly rather
   than declaring it:
   `<uses-permission android:name="com.google.android.gms.permission.AD_ID" tools:node="remove" />`
2. **`ACCESS_NETWORK_STATE` arrived transitively and is not ours.** It is a normal
   permission with no runtime prompt and no privacy surface, and nothing in our Kotlin reads
   connectivity state. Worth knowing before somebody asks why the listing shows a permission
   the app never requested.

---

## Security practices

| Question | Answer | Evidence |
|---|---|---|
| Is all of the user data collected by your app encrypted in transit? | **Yes** | Every client call is HTTPS to `API_BASE`. There is no `usesCleartextTraffic` attribute and no network security config in `AndroidManifest.xml` — on `targetSdk = 36` (`app/build.gradle.kts:15`) cleartext is off by default, so the Android build has no plaintext path at all. The one plaintext exception in the product is on iOS and is scoped to `localhost` and `127.0.0.1` for the simulator (`mobile/ios/Info.plist`), which never ships as a reachable host. |
| Do you provide a way for users to request that their data be deleted? | **Yes** | Both halves — see below. |
| Have you completed an independent security review? | **No** | Optional, and we have not. Do not claim it. |

---

## Account deletion — both obligations

Play asks for two things and Apple only asks for one of them, so this is the half that gets
forgotten. Both must be live *before* submission.

### 1. In-app — done, with one caveat that has to be said out loud

`POST /v1/account/delete` (`api/routers/account.py:60–80`), reached from Settings on Android
through `AccountDeleter` (`data/AccountDeletion.kt`). It is a real deletion, not a
deactivation: `auth/accounts.py:erase` hard-deletes profiles, readings, conversations and
their messages, memory, entitlements, counters, funnel events, sign-in links and unpaid
consent records (`accounts.py:375–384`, `funnel.py:294–304`).

**~~The caveat.~~ FIXED.** This used to read: deletion requires an account with an email
address, `require_account` rejects a guest, and the confirmation is compared against
`user.email` which a guest has not got — so a person who bought through Play without ever
signing in had birth data, readings and a payment record here with no self-service route to
any of them.

That was a rejection on sight and it is closed. `POST /v1/account/delete` now takes
`CurrentUser` rather than `Account`, and the confirmation is `user.email or user.id`: a
signed-in account types its address, a guest types the account id the screen shows them. The
Android screen no longer has a `DeleteState.NeedsAccount` at all — the state that told a
guest to sign in before deleting the birth data we had already taken from them is gone from
the type. `GET /v1/account/export` opened on the same terms and for the same reason.
`tests/test_api.py::test_a_guest_can_export_and_delete` pins it; it is the inverted form of
the test that used to assert the two 401s. The `hello@pazl.ai` sentence is now on the
Settings screen as well (`settings_delete_help`), beside a link to the web page below.

### 2. Web — **BUILT**. `src/app/(legal)/delete-account/page.tsx`.

Play requires *"an accessible external web resource for account deletion"*, and the URL goes
into the designated field in Play Console (App content → Data deletion, and again in the Data
safety form). It must work **without installing the app**.

The page now exists at `https://<domain>/delete-account`, built to the specification below —
inside the `(legal)` route group, instructions plus `mailto:` rather than a form, no
JavaScript needed, not added to `LEGAL_DOCS`. **The owner still has to paste the URL into
Play Console**; nothing in the repository can do that.

**The specification it was built to.**

- **Route**: `src/app/(legal)/delete-account/page.tsx` → `https://<domain>/delete-account`.
  Inside the `(legal)` route group so it inherits the document chrome (`DocHead`, `Sec`,
  `Para`, `Points`, `DocFoot`) and the same shared constants from `src/lib/legal.ts`. It does
  **not** go into `LEGAL_DOCS` — that array is the five-document footer nav, and this is a
  sixth page with a different job.
- **It must be readable signed-out, with no app, no account and no JavaScript.** Google's
  reviewer opens it in a browser. A page that redirects to a login is a rejection.
- **Use the instructions-plus-email form, not a web form.** Google explicitly accepts *"a
  customer service email or a form they can submit a request through."* A web form here would
  collect an email address from an unauthenticated visitor, which is a new collection to
  declare on this very form and a new abuse surface for deleting somebody else's account. The
  `mailto:` route collects nothing new and reuses the manual process the privacy page already
  promises.
- **What it must say**, and every one of these is checkable against the code, so none of it
  can be softened:
  1. The two routes: in the app, Settings → **data & legal** → Delete account, which asks you
     to type back what identifies you — the account email, or the account id a guest is shown
     — to confirm; or write to `hello@pazl.ai` from the address on the account.
  2. ~~That the in-app button needs an account.~~ **Narrowed since this was written.** The
     backend takes `CurrentUser` and confirms against `user.email or user.id`, so a guest can
     delete, and the Android client followed. **iOS has not** —
     `AccountModel.beginDelete(isGuest:)` still returns `.needsAccount`. So the page discloses
     an *iOS-only* exception, as a client that has not caught up rather than as policy, and
     routes those people to the letter. Three paragraphs there get shorter when
     `APP-CHANGES-NEEDED.md` §1 lands on iOS.
  3. What is deleted: birth data, readings, conversations, the remembered facts,
     entitlements, counters, funnel events and sign-in links — rows removed, not flagged
     (`accounts.py:375–384`).
  4. What survives and why: the payment records, detached from the account with the
     processor's message redacted, because a record of a sale is a legal obligation
     (`accounts.py:360–369`); and a stub of the account row with the address and name removed,
     so a link clicked a minute later gets a clear answer rather than silently becoming a new
     person (`accounts.py:386–390`, `api/deps.py:80–83`).
  5. Timing: immediate for the in-app route; a person and a working day for the email route.
  6. The backup window, once the owner has answered it — the one place deleted data survives
     for a while. It is a `<Blank>` on the privacy page today (`privacy/page.tsx:248`) and it
     cannot be a blank on this page, because Play's reviewer reads it as the deletion promise.
- **Link to it** from the app's Settings screen beside the delete button, and from the site
  footer, so that "readily discoverable" is true from both directions.
- **Language**: the five shipped legal documents are English-only, deliberately and for a
  stated reason — a legal argument has to be checked against the law of the country it is
  read in (`mobile/ios/Alma/Screens/Settings/LegalText.swift:23–31`). This page is
  instructions rather than an argument, so it is the one document in the set that *can* be
  translated safely, and it should be: it is the page a person in Brazil or Germany reads
  when they want their birth data gone. Six locales, written natively, matching the voice
  already in `src/lib/i18n/`.

**Then**: paste the URL into Play Console → App content → Data deletion, and into the Data
safety form's deletion question. Apple does not require the URL, but Apple's own guidance
says that if people must visit a website to finish deleting, link directly to that page — so
the same link belongs in the iOS Settings screen too.

---

## Consistency checks before you press submit

1. **The policy the Play listing points at is the web page, and it is wrong today.** Android
   opens `$Site/privacy` for the legal documents (`ui/screens/SettingsScreen.kt:586–596`), so
   `src/app/(legal)/privacy/page.tsx` *is* the Android app's privacy policy. It names
   Paddle or Dodo as the merchant (`src/lib/legal.ts:44–50`) — neither of which the Play build
   ever touches, because both `open_session` implementations refuse — and it does not name
   Google, which is the merchant of record and which receives a purchase token from our
   backend on every purchase (`billing/googleplay.py:102`). A policy that names the wrong
   recipient and omits the real one is the first thing to fix. See PRIVACY-DELTA.
2. **The DPA question gates six rows.** Every "Shared: No" above rests on Anthropic and
   Resend being service providers under agreement. Confirm before filing.
3. **Target audience.** Select adults only. Selecting any group under 13 pulls the app into
   the Families Policy Requirements, which is not appropriate for a paid product built on a
   person's birth data. `src/lib/legal.ts:65` sets `MIN_AGE = 16`; `api/schemas.py:63–70`
   enforces nothing, accepting any birth date from 1900 to 2100. The number on the form, the
   number in the policy, and the behaviour of the app have to agree.
4. **Nothing here is used for advertising, and there is no advertising in the product.** If
   the Data safety form's advertising purpose is ever ticked, this whole document is void.
