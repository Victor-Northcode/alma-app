# Alma — data inventory

**Every store privacy disclosure is derived from this file.** Apple's App Privacy
questionnaire, Google Play's Data safety form and the privacy policy all have to be
answerable from what is written here, so nothing below is a summary of intent — every
claim names the file and the line it was read out of, and a claim that could not be read
out of code is marked as such.

Read at commit state of 7 August 2026. Backend at `backend/alma/`, iOS at
`mobile/ios/Alma/`, Android at `mobile/android/app/src/main/kotlin/ai/pazl/alma/`,
web at `src/`.

Two facts frame everything below.

**There is no anonymous request.** `backend/alma/api/deps.py:61–91` mints a `user` row on
the first call from any client and returns its token in `X-Alma-Token`. So every category
in this document is linked to an account identifier from the first tap, whether or not a
person has ever given us an email address. "Not linked to identity" is therefore false for
almost everything here, and saying otherwise on either store form would be a false
declaration.

**Birth date, birth time and birth place are the product.** A birth time is a precise
personal datum and a birth place is a location. They are collected, stored, and — as exact
strings — sent to Anthropic on every chapter generation. Section 2 says exactly how.

---

## 1. Categories, one per table

Each entry answers the seven questions in order: **what · where stored · who receives it ·
why · how long · linked to identity · used for tracking**. "Tracking" throughout means the
store definition — linking to third-party data for advertising, or sharing with a data
broker. The answer is **no** everywhere in this document, and section 4 proves it by
absence rather than asserting it.

### 1.1 Account identity — `user`

`backend/alma/db/models.py:99–131`

| Column | What it is |
| --- | --- |
| `id` | Opaque URL-safe id, `secrets.token_urlsafe(16)` (`models.py:61–63`) |
| `email` | Sign-in address. Null until somebody signs in |
| `provider` | `guest` \| `google` \| `apple` \| `email` |
| `provider_subject` | Google's or Apple's own subject id for this person |
| `display_name` | Optional; taken from the identity provider or typed in Settings |
| `locale` | One of the six language codes |
| `created_at`, `last_seen_at`, `deleted_at`, `merged_into_id` | Lifecycle |

- **Stored**: our own database, `ALMA_DATABASE_URL` (`config.py:82–84`). No column here is
  copied anywhere else.
- **Sent to**: nobody. The email address goes to Resend only as the *envelope address* of a
  letter the person's own action triggered (§2.3). It is never sent to Anthropic —
  `writer.build_prompt` and `conversation.build_prompt` have no access to a `User`.
- **Why**: the account. `email` is the only way a second device reaches the same readings,
  and the only credential the deletion route accepts (`routers/account.py:73`).
- **Kept**: while the account exists. On erase, `email`, `provider_subject` and
  `display_name` are nulled and `deleted_at` is set; the row itself survives as a tombstone
  so a token presented a second later gets a clear 410 rather than silently becoming a new
  person (`auth/accounts.py:386–390`, `api/deps.py:80–83`).
- **Identity**: it *is* the identity.
- **Tracking**: no.

There is no password anywhere. `auth/` contains no hashing of a user secret; sign-in is
Google, Apple, or a single-use link (`routers/auth.py`). Magic-link tokens are stored only
as SHA-256 (`auth/tokens.py:79–90`).

### 1.2 Birth data — `profile` · **the sensitive core**

`backend/alma/db/models.py:134–164`, written by `routers/profiles.py:40–83`, validated by
`api/schemas.py:24–82`.

| Column | What it is | Sensitivity |
| --- | --- | --- |
| `birth_date` | A date | Personal data. Also the user's date of birth in the ordinary case |
| `birth_time` | `"HH:MM"` local wall clock, **or NULL** | Precise personal data — a minute of a day |
| `latitude`, `longitude` | Float degrees, stored to full precision | **Location** — the coordinate of a birthplace |
| `timezone` | IANA zone name | Derived from the coordinate |
| `place_label` | e.g. `"Milan, Lombardy, Italy"` | Human-readable location |
| `place_id` | Row id in the bundled gazetteer | Not personal on its own |
| `name` | Optional given name | Personal data. Used by numerology (`calc/service.py:181`) |
| `relation` | Free-ish short string — "partner", "friend" | About a third party |
| `is_self` | Whether this birth is the account holder's own | Distinguishes the user from other people |

**A profile may be about somebody else.** Compatibility requires a second birth
(`routers/readings.py:375–401`), and nothing asks whether that person consented. For the
store forms this is still "personal information collected", and it should be disclosed as
such rather than as "the user's own data only".

- **Stored**: our database only. Never written to any device-side store by the native apps
  (§1.15). On the web it is held in `sessionStorage` during the journey (§1.16).
- **Sent to**: **Anthropic**, in the exact form described in §2.1 — `birth_date`,
  `birth_time`, `place_label` and `name` appear verbatim in every chapter prompt.
  Latitude and longitude do **not** leave; they are consumed by the ephemeris and only their
  results travel.
- **Why**: this is the calculation. `engine/` computes every position from the JPL DE440s
  ephemeris against the coordinate and the instant; a missing birth time is a first-class
  state and every system that needs the horizon refuses rather than guessing
  (`calc/contract.py:54–74`).
- **Kept**: until the person changes or deletes it. `Profile` rows are hard-deleted on
  erase (`auth/accounts.py:375–376`), and editing overwrites in place
  (`routers/profiles.py:91–107`).
- **Identity**: yes — `profile.user_id`, indexed.
- **Tracking**: no.

**Location precision, stated honestly.** These are not device-location readings — no client
in this repository asks the OS for a location. The Android manifest declares only
`INTERNET` and `com.android.vending.BILLING`
(`mobile/android/app/src/main/AndroidManifest.xml:4–7`); the iOS `Info.plist` carries no
`NSLocationWhenInUseUsageDescription` and there is no `CoreLocation` import anywhere in
`mobile/ios/Alma/`. The coordinate is chosen by the person from a search box against a
bundled offline gazetteer (`backend/alma/geo.py:1–20`, `routers/places.py`). It is
nevertheless a precise coordinate about a person and must be declared as location on both
forms.

### 1.3 Generated readings — `reading`

`models.py:405–438`. `body` is the full generated chapter (title, teaser, paragraphs,
advice, the per-paragraph factor arrays); `cited_factors` is the list of chart facts it was
read from; `model`, `input_tokens`, `output_tokens`, `cost_cents` are our own accounting.

- **Stored**: our database. **Sent to**: nobody — a reading is generated *by* Anthropic and
  then stored; it is never sent back out.
- **Why**: a reading a person paid for must say the same thing the second time
  (`routers/readings.py:243–246`).
- **Kept**: until account deletion; hard-deleted there (`accounts.erase`). Included in the
  export (`accounts.py:291–300`).
- **Identity**: yes, `user_id` + `profile_id`. **Tracking**: no.

### 1.4 Conversations — `chat_thread`, `chat_message`

`models.py:457–488`. `ChatMessage.body` is `Text` and holds **whatever the person typed**,
up to 2000 characters per turn (`api/schemas.py:172`). `ChatThread.title` is the first 80
characters of the first message (`routers/readings.py:772`) — i.e. a slice of free text.

This is the highest-risk field in the product. It is free text a person may put anything
into: a health worry, a relationship, a name, a job. Nothing filters it and nothing should
pretend to.

- **Stored**: our database.
- **Sent to**: **Anthropic**. The prompt for one turn carries the last twelve messages of
  the thread verbatim, both sides (`ai/conversation.py:128–133`, `MAX_HISTORY = 12`), plus
  the current question (`:143–145`).
- **Why**: the conversation is the product; the history is what makes turn six coherent
  with turn one.
- **Kept**: until account deletion; hard-deleted (`ChatThread` cascade-deletes its
  messages, `models.py:469–471`). Included in the export.
- **Identity**: yes. **Tracking**: no.

### 1.5 Memory — `memory`

`models.py:491–508`. Short strings the model extracted from a conversation — at most two
per turn, capped by the schema at "things they stated about their life"
(`ai/conversation.py:58–67`, `routers/readings.py:470–477`).

- **Sent to**: **Anthropic**, in the *system* prompt, on every generation — chapters and
  chat alike (`ai/voice.py:112–119`, called from `writer.write:214` and
  `conversation.answer:164`). The eight most recent are sent (`readings.py:458–467`).
- **Why**: so Alma does not ask in March what was answered in January.
- **Kept**: until deleted. Inspectable at `GET /v1/memory` and individually deletable at
  `DELETE /v1/memory/{id}` (`routers/readings.py:890–912`). Hard-deleted on erase; in the
  export.
- **Identity**: yes. **Tracking**: no.

This is free text of the person's own, restated. It should be declared as user content, not
folded into "chart data".

### 1.6 Entitlements — `entitlement`

`models.py:167–256`. What was bought: `system`, `kind`, `scope`, `granted_at`,
`expires_at`, `revoked_at`, `source` (which processor), `transaction_id`,
`subscription_id`, `status`, `renews_at`, `amount_cents`, `currency`.

- **Stored**: our database. **Sent to**: nobody. **Why**: it is the only thing that unlocks
  content. **Kept**: hard-deleted on erase. In the export (a reduced view —
  `accounts.py:271–279`). **Identity**: yes. **Tracking**: no.

### 1.7 Payment records — `purchase`

`models.py:259–315`, written by `routers/billing.py:1174–1261`.

| Column | What it is |
| --- | --- |
| `provider` | `appstore` \| `googleplay` \| `paddle` \| `dodo` |
| `transaction_id` | The store's or processor's own id — Apple's `transactionId`, Google's `orderId` |
| `subscription_id`, `checkout_id`, `price_id`, `product` | What was bought |
| `buyer_email` | **The address the processor collected**, never our sign-in identity (see the column's own note, `models.py:284–294`) |
| `amount_cents`, `refunded_cents`, `currency`, `country` | The money |
| `payload` | **The delivery verbatim** — see below |
| `user_id` | Nullable; detached rather than deleted on erase |

- **`payload` is the sharp edge.** It is whatever the processor sent, stored whole. On the
  stores that is `{"notification": …, "transaction": …}` (`billing/appstore.py:539`) and
  `{"notification": …, "purchase": …}` (`billing/googleplay.py:646`) — Apple's decoded
  transaction and Google's purchase state, which carry a transaction id, a product id, a
  storefront/`regionCode`, and no name or address. On the card processors it also carried
  the buyer's name, email and billing country, which is why `erase` redacts it
  (`accounts.py:360–369`).
- **`buyer_email` is `None` from both stores.** Apple tells us nothing about the buyer
  (`appstore.buyer_address` returns `None`, `:976–987`); Google's adapter sets
  `buyer_email=None` (`googleplay.py:638`). On a store build we therefore hold **no payment
  email at all** unless the person separately signed in.
- **Sent to**: nobody. Card details never reach us on any build.
- **Why**: it is a tax record and the other side of somebody else's books.
- **Kept**: **survives account deletion**, detached — `user_id` nulled and `payload`
  replaced with a redaction marker (`accounts.py:360–364`, `:393–397`). What is left is a
  date, an amount, a currency, a country and a reference.
- **Identity**: while the account lives, yes. After erase, no.
- **Tracking**: no.

### 1.8 Consent records — `consent`

`models.py:318–367`, written by `routers/billing.py:334–394`. The exact sentences a buyer
ticked at a **web** checkout, the locale they read them in, the client's timestamp, and the
transaction the webhook later joined to them. Capped at 8 statements × 400 characters and
reduced to `{key, text}` before storage, deliberately so a free-text field cannot one day
hold a birth date (`billing.py:344–348`).

- **Relevance to the store builds**: none today. It is written only from `POST
  /v1/billing/checkout`, which the store adapters refuse to serve
  (`appstore.open_session`, `googleplay.open_session` both raise). On Apple and Google the
  store is the merchant of record and issues the receipt itself.
- **Kept**: a consent that never became a purchase is deleted on erase; one a payment
  claimed is detached with the purchase (`accounts.py:370–377`).
- **Identity**: yes, until detached. **Tracking**: no. **Not in the export** — see §5.6.

### 1.9 Webhook deliveries — `webhook_event`

`models.py:370–402`. Every store notification and processor webhook, stored verbatim
against its own id so a retry cannot grant twice (`routers/billing.py:508–516`). Carries a
`user_id` when we can work out whose it is.

- **Kept**: 180 days, then deleted outright by `backend/tools/prune.py` (scheduled daily,
  `docs/DEPLOY.md §5`). Before that: on erase the payload is redacted and `user_id` nulled
  (`accounts.py:365–369`), so an erased person's delivery is already anonymous while the
  row waits out its retention.
- **Identity**: yes, until erased. **Tracking**: no.

### 1.10 Sign-in links — `magic_link`

`models.py:524–534`. SHA-256 of the token, the **email address in clear**, the guest id that
asked, created/expires/used timestamps.

- **Sent to**: **Resend**, as the recipient of the letter (§2.3).
- **Kept**: until the link expires. `backend/tools/prune.py` (scheduled daily,
  `docs/DEPLOY.md §5`) deletes every row past its own `expires_at` — the row is unreadable
  after that point anyway, since `consume_magic_link` refuses an expired or used link.
  Rows for the person's address are additionally hard-deleted on erase, as are rows created
  by their guest id (`accounts.py:382–384`). Before that sweep existed, the address of
  somebody who asked for a letter and never finished signing in stayed with us for ever.
- **Identity**: yes. **Tracking**: no.

### 1.11 Counters — `usage_counter`

`models.py:511–521`. Keyed `user_id:day:metric`. Every metric that exists, read out of the
code:

| Metric | Written by | What it counts |
| --- | --- | --- |
| `questions` | `routers/readings.py:75` | Chat turns today (free tier) |
| `questions_month` | `readings.py:76` | Chat turns this month (subscriber) |
| `questions_bundle` | `readings.py:79` | Turns from the bundle a purchase included, for life |
| `readings_written` | `readings.py:319` | Chapters generated |
| `spend_cents` | `ai/cost.py:178` | What generations cost **us**, in cents |
| `events` | `funnel.py:173` | Funnel beacons today, as a per-account cap |
| `renewal_notice` | `billing/renewals.py:68` | That one renewal warning was sent, once |
| `downsell_offered` | `routers/billing.py:1436` | That the one cheaper offer has been shown |

Numbers, dates and single words. No text of the person's. Hard-deleted on erase
(`accounts.py:375`). Identity: yes. Tracking: no.

### 1.12 Funnel events — `event`

`models.py:537–576`, written by `funnel.record` and `POST /v1/events`
(`routers/events.py`). Five columns: `id`, `user_id`, `name`, `properties`, `created_at`.

- **`name` is a closed set of nine** (`funnel.py:124–142`): `landing_view`, `quiz_start`,
  `quiz_complete`, `portrait_view`, `offer_view`, `checkout_opened`, `purchase_completed`,
  `purchase` (server-only, refused from any client), `offer_declined`. An unknown name is a
  422, not a row.
- **`properties` is an allowlist of eight keys** (`funnel.py:154–156`): `system`, `chapter`,
  `product`, `locale`, `step`, `variant`, `currency`, `how`. Values must be a string ≤ 64
  characters, an int or a bool; anything else is dropped and logged
  (`funnel.clean_properties:179–223`). Anything not on the list is dropped.
- **What is deliberately absent**, verified by reading the model and the writer: no IP
  address, no user agent, no referrer, no URL, no device id, no session id, no advertising
  id, no free-text field of any kind.
- **Kept**: hard-deleted on erase, through `funnel.forget` (`accounts.py:381`,
  `funnel.py:294–304`).
- **Identity**: yes — the account id, and nothing else, is the attribution
  (`funnel.py:26–28`).
- **Tracking**: no. Nothing leaves our database; there is no third-party analytics
  destination anywhere in the codebase (§4).

**The opt-out is web-only.** `src/lib/track.ts:106–120` honours Do Not Track in three
spellings and Global Privacy Control, checked on every call. **The native apps have no
equivalent** — `AlmaClient.track` (`mobile/ios/Alma/Networking/AlmaClient.swift:308–318`)
and its Android twin (`data/AlmaClient.kt:360…`, `data/AlmaService.kt:229`) post
unconditionally. This is not a defect in itself (there is no DNT on a phone), but it means
the app collects product-interaction analytics with no user-facing off switch, and both
store forms must be answered on that basis. See §5.3.

### 1.13 Calculation cache

Two things share a name and only one of them exists at runtime.

- **`calc_cache` table** (`models.py:441–454`) is declared and created by `create_all`, and
  **nothing writes to it**: `grep -rn CalcCacheEntry alma` returns only the model definition
  and the `db/__init__` re-export. It is dead schema.
- **The live cache is `MemoryCache`** — in-process, bounded at 2048 entries, lost on restart
  (`api/cache.py:16–18`, `calc/cache.py:65–103`). It holds serialised `CalcResult`s, and a
  `CalcResult.subject` contains the birth date, the birth time, latitude, longitude,
  timezone, place label and name (`calc/contract.py:99–109`, `:170`).

So: birth data does sit in RAM, keyed by a content hash, shared across requests, and it
outlives an account deletion until the entry is evicted or the process restarts. That is a
transient technical fact rather than a storage disclosure, but it is named here because §5.4
records the latent version of it.

### 1.14 Operator settings — `setting`

`models.py:579–593`. Prices, prompts, limits. No user data. Named only so this inventory can
claim to cover every table in the schema.

### 1.15 On-device storage — the native apps

| Platform | What is stored | Where |
| --- | --- | --- |
| iOS | The bearer token, and nothing else | Keychain, `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`, service = bundle id (`mobile/ios/Alma/Networking/TokenStore.swift:1–60`) |
| Android | The bearer token, and nothing else | `IV ‖ ciphertext`, base64, in `SharedPreferences`, encrypted with an `AndroidKeyStore` key (`data/TokenStore.kt:20–80`) |

No birth data, no readings and no messages are persisted on either device — no
`UserDefaults`, `CoreData`, `SwiftData`, Room or DataStore usage exists outside the token
stores (grepped). Android sets `allowBackup="false"` and `fullBackupContent="false"`
(`AndroidManifest.xml`), so nothing goes to Google's backup service. The iOS keychain item
is `ThisDeviceOnly`, so it is excluded from encrypted backups.

`AccountModel.swift:201` writes to `FileManager.default.temporaryDirectory` — that is the
data-export JSON, written so the share sheet can hand it to the person. It is the user's own
export, at their own request, in the OS temp directory.

### 1.16 On-device storage — the web build

- `localStorage["alma.token"]` — the bearer token (`src/lib/api.ts:26–55`).
- `sessionStorage["alma.journey"]` — **the journey state, which includes the birth date, the
  name, the hour and minute, and the chosen place with its coordinates**
  (`src/lib/journey-store.tsx:33–64`, `:93–104`).
- Cookie `alma.locale` — a language code, so the server can render in the right language
  (`src/lib/i18n/index.ts:42`, `:97–110`).

No other cookie is set anywhere in `src/`.

### 1.17 Network metadata — **unresolved**

Nothing in this repository stores an IP address, a user agent or a referrer; there is no
request-logging middleware in `api/app.py` and no such column in any model. But every host,
proxy and TLS terminator keeps access logs by default, and the privacy page already leaves
the hosting region blank (`privacy/page.tsx:144–147`). **The owner has to answer what the
production host retains and for how long** before either store form can claim "no diagnostic
data collected". See open questions.

---

## 2. What leaves our servers, precisely

### 2.1 Anthropic — the reading and the conversation

`ai/provider.py:67–142` is the only outbound call. Two prompts are built, and this is
exactly what is in them.

**A chapter** (`ai/writer.build_prompt:137–192`) — the *user* turn contains, in order:

1. The system slug and the chapter's title and question.
2. A `THE PERSON` block: **`- born {birth_date}` and, when a birth time is known, `at
   {HH:MM}`; `- birth time known: yes/no`; `- birthplace: {place_label}` when there is one;
   `- name: {name}` when there is one.** These four are the raw stored values, not
   derivatives.
3. The factor list this chapter may cite — plain strings such as `"life path 7"`,
   `"birthday number 22"` (`engine/numerology.py:117–133`) or a placement line.
4. The rest of the chart's factors as context.
5. What could not be calculated, and any notes about the calculation.

The *system* turn (`ai/voice.system_prompt:100–121`) contains Alma's voice rules, the tier
paragraph, the target language, and — when there is any — **the remembered facts, which are
free text of the person's own** (§1.5).

**A chat turn** (`ai/conversation.build_prompt:120–145`) contains: the last twelve messages
of the thread verbatim, both sides; the factor lists for natal, numerology and birth-card;
and the current question. It carries **no** `THE PERSON` block — no date, no time, no place,
no name — because it is built from `CalcResult.factors` only. The system turn is the same as
above, memory included.

**What never goes to Anthropic**: the email address, the account id, latitude and longitude,
any payment detail, any token. Verified by reading both prompt builders — neither has access
to a `User` row, and `Purchase`/`Entitlement` are never imported into `ai/`.

**Retention at Anthropic** is Anthropic's own commercial terms, not something this codebase
can assert. The privacy page's sentence that readings are not used to train a model is a
claim about a contract; it belongs in a DPA reference, not in code. See open questions.

### 2.2 Apple and Google — purchases

- **Apple: nothing outbound.** The signed StoreKit transaction is verified locally against
  the pinned Apple Root CA G3 (`billing/appstore.py:106+`); there is no App Store Server API
  call anywhere in that file. The *app* talks to Apple through StoreKit, and Apple learns
  what Apple learns about any purchase — that is Apple's collection, not ours.
- **Google: one outbound call per purchase.** `billing/googleplay.py:102` — the backend
  sends the **package name and the purchase token** to
  `https://androidpublisher.googleapis.com/androidpublisher/v3`, authenticated by a service
  account against `https://oauth2.googleapis.com/token`, and receives the purchase state
  back, including `regionCode` (`googleplay.py:610–612`), an order id and a product id. No
  birth data, no email address, no name is sent — the purchase token is the only user-linked
  value, and it is Google's own.
- Neither store sends us a buyer identity: `buyer_email` is `None` on both adapters
  (§1.7).

### 2.3 Resend — three letters, and there is no fourth

`alma/mail.py:40` posts to `https://api.resend.com/emails`. Resend receives the recipient
address and the letter body:

| Letter | Written by | What Resend sees |
| --- | --- | --- |
| Sign-in link | `send_magic_link:115` | Address, and a one-time URL |
| Renewal notice, three days before a charge | `send_renewal_notice:220` | Address, the date, the amount and currency |
| Purchase receipt | `send_receipt:928` | Address, product name, amount, currency, date, merchant, transaction reference, and — where one was recorded — the consent sentences verbatim (`Receipt`, `mail.py:356–400`) |

No newsletter, no campaign, no list: there is no fourth sender in the module.

**On a store build the receipt is Apple's or Google's**, not ours — `appstore.buyer_address`
returns `None` and the adapter documents that the store issues the receipt. So an
App Store or Play buyer who never signed in causes no mail at all.

### 2.4 Google and Apple — sign-in verification

`auth/providers.py:26–29` fetches the providers' **public keys** from
`https://www.googleapis.com/oauth2/v3/certs` and `https://appleid.apple.com/auth/keys`. The
identity token is then verified locally. **Nothing of ours is sent to either.** They learn
that a JWKS endpoint was fetched from our server's IP — nothing about the person.

Both are currently disabled by configuration; the privacy page already carries the sentence
that switching either on makes them a recipient (`privacy/page.tsx:176–182`).

### 2.5 Paddle and Dodo — web only

`billing/paddle.py`, `billing/dodo.py`. Reachable only through `POST /v1/billing/checkout`,
which both store adapters refuse. Under the decision that all app payments go through Apple
and Google, **neither is a recipient for anything the mobile apps do**. §5.1 records that
the privacy page has not caught up with this.

### 2.6 The gazetteer is offline

Place search and timezone lookup run against a bundled SQLite index and `zoneinfo`
(`geo.py:1–20`, `_index_path:75–80`). **No geocoding request leaves the server**, so no
third party learns a birthplace at the moment it is typed. This is worth stating on the
store forms: the most location-revealing interaction in the product has no network
recipient.

---

## 3. Retention, in one table

| Data | On account deletion | Mechanism |
| --- | --- | --- |
| Profiles (birth data) | **Deleted** | `accounts.erase:375` |
| Readings | **Deleted** | same |
| Conversations and messages | **Deleted** | same, cascade |
| Memory | **Deleted** | same |
| Entitlements | **Deleted** | same |
| Counters | **Deleted** | same |
| Funnel events | **Deleted** | `funnel.forget`, `accounts.erase:381` |
| Magic links | **Deleted** | `accounts.erase:382–384` |
| Consent with no payment | **Deleted** | `accounts.erase:377` |
| Consent joined to a payment | **Detached** (`user_id` nulled) | `accounts.erase:370–374` |
| Purchases | **Kept, detached, payload redacted** | `accounts.erase:360–364` |
| Webhook deliveries | **Detached, payload redacted**, then deleted at 180 days | `accounts.erase:365–369`, `tools/prune.py` |
| Device tokens (push) | **Deleted** | `notify.tokens.forget`, called from `accounts.erase` |
| The `user` row | **Kept as a tombstone**, email/name/subject nulled | `accounts.erase:386–390` |

**Device tokens have a second, shorter clock.** They are deleted on account deletion like
everything above, and they are *also* swept after **90 days** without the app being opened
(`notify/tokens.SWEEP_AFTER`, run from the hourly daily job), plus deleted on sight when a
vendor reports the registration gone. A token nobody has used in three months is a
credential for a phone that may have been sold, and holding it serves nobody. The related
number is `rules.DORMANT_AFTER`, 60 days, at which we stop *sending*: go quiet first, forget
second.

**Deletion is self-service and immediate** — `POST /v1/account/delete`, confirmed by typing
the account's own email address (`routers/account.py:60–80`). **It requires an account**:
`require_account` rejects a guest (`api/deps.py:97–104`), and the confirmation string is
compared to `user.email`, which a guest does not have. A guest who bought without signing in
has birth data, readings and a payment record here with no self-service route to any of it.
The privacy page discloses this (`privacy/page.tsx:190–199`); the store listings and the
in-app account screen must not imply otherwise.

**Export**: `GET /v1/account/export` returns account, profiles, entitlements, purchases,
readings, conversations, memory and registered devices as one JSON file. Also account-only.

The device rows carry the platform, environment, timezone, locale, app and OS versions and
the two timestamps — **and deliberately not the token string**. A push token is a live
delivery credential: anybody holding it together with our APNs key can send to that phone.
Returning it inside a file a person may email to themselves would be manufacturing copies of
a secret in order to honour a transparency request. What Article 15 requires is that the
subject knows what is held about them, and "a device registered for notifications, this
platform, first seen then, last seen then" is that, completely.

**Backups** are undisclosed — the privacy page leaves the window blank. Open question.

---

## 4. What we do **not** collect, and the absence each claim rests on

Every line below is a grep that came back empty (or came back with only the thing named),
not an assumption.

| Claim | How it was verified |
| --- | --- |
| **No advertising identifier** | No `AdvertisingIdClient`, no `ASIdentifierManager`, no `IDFA`, no `AppTrackingTransparency`/`ATTrackingManager` anywhere in `mobile/`. No `com.google.android.gms.permission.AD_ID` in the manifest; no `NSUserTrackingUsageDescription` in `Info.plist`. Grepped across `src`, `mobile`, `backend/alma`. |
| **No third-party analytics SDK** | No Firebase Analytics, GA4, `gtag`, Google Tag Manager, Segment, Amplitude, Mixpanel, PostHog, Hotjar, Clarity, AppsFlyer, Adjust, Branch, OneSignal in any dependency file or source file. `package.json` has exactly three runtime dependencies: `next`, `react`, `react-dom`. |
| **No crash/diagnostics SDK** | No Sentry, Crashlytics, Bugsnag, Instabug. Android has no `firebase-crashlytics`; iOS links no third-party framework at all (`project.pbxproj` declares no framework build phase). Whatever Apple and Google collect on their own via App Store Connect and Play Console is theirs and happens without our code. |
| **No cross-app or cross-site tracking** | Nothing loads a remote script. The web app sets exactly one cookie (`alma.locale`) and no third-party cookie; the native apps make requests to `API_BASE` only. |
| **No data sold or shared for advertising** | There is no recipient other than the four in §2, and none of them receives anything for advertising purposes. |
| **No password stored** | No hashing of a user secret anywhere in `auth/`; sign-in is Google, Apple or a hashed single-use link. |
| **No card data** | The card never reaches our servers on any build. On the stores, Apple and Google take the payment; on the web the processor is the merchant of record. |
| **No IP address, user agent, referrer or URL in analytics** | The `event` table has five columns and a closed property allowlist (§1.12). No request-logging middleware in `api/app.py`. |
| **No contacts, photos, microphone, camera, calendar** | No such permission in the manifest and no such usage string in `Info.plist`. |

**One honest qualification.** Android's dependency graph pulls
`com.google.android.gms:play-services-*`, `com.google.android.datatransport:*` and
`com.google.firebase:firebase-encoders*` in **transitively behind
`com.android.billingclient:billing 8.3.0`** (visible in the resolved dependency list under
`app/build/`). They are declared nowhere in `libs.versions.toml` or `app/build.gradle.kts` —
the only Google dependency we ask for is Play Billing. If Play's Data safety review asks
about them, that is the answer: they arrive with the billing library and nothing in our code
calls them.

---

## 5. Defects — where the code and `privacy/page.tsx` disagree

Each of these is a disclosure that is wrong today. All belong in the same pass that files
the store forms.

### 5.1 The recipient list names a card processor the app never touches, and omits the two it does

`src/app/(legal)/privacy/page.tsx:112` — *"Three companies, and this is the complete list"* —
then names Anthropic, `{MERCHANT}` and Resend. `MERCHANT` resolves to
`"Paddle.com Market Ltd"` or `"Dodo Payments"` (`src/lib/legal.ts:44–50`). On an App Store or
Play build:

- Neither Paddle nor Dodo receives anything. Both `open_session` implementations refuse.
- **Apple** and **Google** are the merchants of record and the actual recipients of the
  purchase — and for Android we additionally send Google a purchase token over the Play
  Developer API (§2.2). Neither is named on the page.

The page is wrong in the direction that flatters us on one count and understates the
recipient list on another. Fix: make the recipient list conditional on the platform, or name
all five and say which applies where.

### 5.2 "What is sent to Anthropic" understates it

`privacy/page.tsx:114–122` says what is sent is *"the calculated chart — positions, aspects,
the numbers — the question you asked, and the short facts Alma remembers about you"*.

`ai/writer.build_prompt:152–164` also sends, verbatim, in every chapter prompt:

- the **birth date**,
- the **birth time**, to the minute,
- the **birthplace label**,
- the **name**, when one was given.

Those are the four most sensitive fields in the product, and the page currently describes
them as being folded into "the chart". They are not derived — they are the stored strings.
The paragraph has to say so. (It is right that the email address is not sent.)

### 5.3 The Do Not Track promise is untrue in the apps

`privacy/page.tsx:104–108`: *"If your browser sends Do Not Track or Global Privacy Control,
the step labels are not recorded at all."* True on the web (`src/lib/track.ts`). There is no
equivalent in either native client — `AlmaClient.track` posts unconditionally on both
platforms (§1.12). The sentence is scoped to "your browser", so it is not strictly false,
but a person reading it inside the app would reasonably conclude they had an opt-out they do
not have. Either ship a settings toggle that suppresses `POST /v1/events`, or say plainly
that the apps have no such signal to read.

### 5.4 A dead table in the schema would hold birth data outside every deletion path

`CalcCacheEntry` (`models.py:441–454`) has no `user_id`, is not in `accounts.erase`'s walk,
and would store `CalcResult.payload` — which includes `subject`: birth date, birth time,
coordinates, timezone, place label and name (`calc/contract.py:99–109`). Nothing writes to
it today (§1.13), so no promise is broken **yet**. But `models.py`'s own docstring says a
table holding a person's data and absent from `erase` is "a promise this project has broken
without noticing", and this table is one wiring change away from being exactly that. Either
delete the model or give it a deletion story before anyone switches the cache over.

### 5.5 Nothing enforces the stated minimum age

`src/lib/legal.ts:65` sets `MIN_AGE = 16` and three legal pages repeat it. No code checks it:
`BirthInput._in_range` (`api/schemas.py:63–70`) accepts any birth date from 1900 to 2100, so
a date implying a nine-year-old saves without complaint, and no screen asks. This matters
twice — it is the age declaration on both store forms, and both stores' children's-data
rules turn on whether a product knowingly collects data from children
(Play: https://support.google.com/googleplay/android-developer/answer/9893335;
Apple, Guideline 1.3 and the Kids Category:
https://developer.apple.com/app-store/review/guidelines/).

### 5.6 The export omits four categories the same page says we hold

`accounts.export:220–321` returns account, profiles, entitlements, purchases, readings,
conversations, memory. The "What Alma holds" list also names the **counters**, the
**consent statements**, the **sign-in links** and the **funnel step labels**
(`privacy/page.tsx:44–71`). None of the four is in the export. The page's own description of
the export is accurate about its contents, so this is not a contradiction on its face — but
a GDPR Art. 15 request covers all of it, and "Export in Settings is the fastest route" to
the right of access (`privacy/page.tsx:260–267`) overstates what the button returns.

### 5.7 The privacy page has three blanks that block filing

`privacy/page.tsx` renders `<Blank>` in three places: *data transfer terms per processor*
(:144), *hosting region* (:145), *backup retention window* (:248), plus *lead supervisory
authority* (:271). Every one of them is required by at least one of the two store forms or
by the GDPR notice itself. They are owner decisions, not code findings — listed here so they
are not discovered on the day of submission.

---

## 6. Mapping to the two store forms

Proposed answers, derived from sections 1–4. The final declaration is the owner's; this is
the evidence it should be made from.

### Apple — App Privacy (App Store Connect)

Categories per Apple's App Privacy Details
(https://developer.apple.com/app-store/app-privacy-details/).

| Apple data type | Collected | Linked to identity | Used for tracking | Purpose | Source |
| --- | --- | --- | --- | --- | --- |
| Contact Info → Email Address | Yes, **optional** | Yes | No | App Functionality | §1.1 |
| Contact Info → Name | Yes, optional | Yes | No | App Functionality | §1.1, §1.2 |
| Location → Precise Location | **Yes** — birthplace coordinate, entered by the person, not read from the device | Yes | No | App Functionality | §1.2 |
| Sensitive Info | **Yes** — see note | Yes | No | App Functionality | §1.2 |
| User Content → Other User Content | **Yes** — chat messages, memory, generated readings | Yes | No | App Functionality | §1.4, §1.5, §1.3 |
| Identifiers → User ID | Yes — our own account id | Yes | No | App Functionality | §1.1 |
| Purchases → Purchase History | Yes | Yes | No | App Functionality | §1.6, §1.7 |
| Usage Data → Product Interaction | Yes — the nine funnel stages | Yes | No | Analytics | §1.12 |
| Everything else (Health, Financial Info, Contacts, Browsing/Search History, Device ID, Diagnostics, Advertising Data) | **No** | — | — | — | §4 |

**The Sensitive Info question needs the owner's judgement.** Apple's own examples of that
category are racial or ethnic data, sexual orientation, pregnancy, disability, religious or
philosophical beliefs, trade union membership, political opinion, genetic and biometric
data. A birth date, a birth time and a birthplace are none of those. But chat messages are
free text a person may put any of them into, and Alma's memory then stores what the model
extracted. Declaring **User Content** is unarguable; whether to *also* declare Sensitive Info
is a defensible call in either direction, and the conservative answer is yes.

### Google Play — Data safety

Categories per https://support.google.com/googleplay/android-developer/answer/10787469.

| Play data type | Collected | Shared | Processed ephemerally | Optional | Purpose |
| --- | --- | --- | --- | --- | --- |
| Personal info → Email address | Yes | No | No | **Yes** | Account management |
| Personal info → Name | Yes | No | No | **Yes** | App functionality |
| Personal info → User IDs | Yes | No | No | No | App functionality |
| Personal info → **Other info** (date of birth, birth time) | Yes | No | No | No | App functionality |
| Location → Approximate / Precise location | Yes (precise; user-entered birthplace) | No | No | No | App functionality |
| Messages → Other in-app messages | Yes | No | No | No | App functionality |
| App activity → Other user-generated content | Yes (readings, memory) | No | No | No | App functionality, personalisation |
| App activity → App interactions | Yes (funnel stages) | No | No | No | Analytics |
| Financial info → Purchase history | Yes | No | No | No | App functionality |
| Device or other IDs | **Yes** (push token) | No | No | No | App functionality |
| App info and performance (crash logs, diagnostics) | **No** — we ship no crash SDK | — | — | — | — |

**The Device ID row is the push token, and it is not the anon id.** The two are different
identifiers and only one of them belongs in this table. `X-Alma-Anon` — the funnel's
installation UUID from `Measurement.kt` / `InstallationId.swift` — is a *self-assigned*
identifier for analytics that a Settings switch prevents the minting of, which is what makes
the App activity row above Optional. The **push token** is a per-device identifier issued by
Apple or Google, held only while notifications are on, and used for one thing: delivering
the daily. That is **App functionality**, not Analytics, and it is **not Optional in Play's
sense** — turning it off does not merely stop the collection being used, it deletes the row
(`notify/tokens.forget`, called from `PATCH /v1/notifications` and from `accounts.erase`), so
there is nothing collected to be optional about. Filing this row as No, as it read until the
push work landed, would declare an identifier the app does collect.

**"Shared" is No throughout, and that is a decision that needs stating rather than
assuming.** Play defines sharing as transfer to a third party. Anthropic and Resend are
**processors acting on our instructions**, which Play's own guidance treats as not "shared"
provided the transfer is for processing on the developer's behalf. That framing depends on
having a data processing agreement with each of them. If those DPAs are not in place, the
honest answer for Anthropic flips to Yes — and Anthropic receives birth date, birth time,
birthplace, name and chat messages. **Do not file this form until the DPAs are confirmed.**

Both forms also require: data is encrypted in transit (yes — HTTPS everywhere; the only ATS
exception is scoped to `localhost` and `127.0.0.1` for the simulator,
`mobile/ios/Info.plist`), and users can request deletion (yes, in-app, §3 — with the guest
caveat).

---

## 7. Open questions — the owner's to answer

1. **Where is the backend hosted, and what does the host log?** Access logs holding IP
   addresses are the one category this codebase cannot see. Needed for `privacy/page.tsx`
   (:145) and for both store forms' diagnostics answers.
2. **What is the backup retention window?** `privacy/page.tsx:248` is blank, and it is the
   one place deleted data survives.
3. **Are there DPAs with Anthropic and Resend?** The Play "shared" answer turns on it
   (§6), and so does the claim that readings are not used to train a model
   (`privacy/page.tsx:160–163`).
4. **Which supervisory authority?** `privacy/page.tsx:271`.
5. **Age.** Is 16 the number we file, and do we add a gate (§5.5)? The two have to agree.
6. **Sensitive Info on Apple's form** — declare it or not (§6).
7. **Do the apps get an analytics opt-out** (§5.3), or does the disclosure change instead?
