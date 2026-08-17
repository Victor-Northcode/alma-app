# Alma — how a push actually reaches a phone

**7 August 2026.** Every specification below was fetched today from Apple's and Google's own
documentation rather than recalled; the sources are listed at the end and linked inline where
a number or a header name is load-bearing. Nothing in this document is code. It is the thing
that has to be true before any is written.

There is no notification code anywhere in this repository. No APNs, no FCM, no device tokens,
no scheduler. `alma/billing/renewals.py` already needs a daily cron nobody has set up, and
`alma/funnel.py --purge` needs a second one. **The daily inherits that problem and makes it a
third.** §8 is about that, and it is the section most likely to decide whether this feature
works in production, because a transport that is wired correctly and never invoked looks
exactly like one that was never wired at all.

> **Read `docs/THE-DAILY.md` first if you have not.** It is the sibling to this file and the
> two divide the work: **that one decides what is sent and how often**, from measurements it
> ran over real charts — how many days a year contain something, what a piece costs, what
> cadence is defensible, what the person controls. **This one decides how it gets there** —
> the two transports, the two stores' rules, the privacy declarations, and what runs the job.
>
> Where they touch — cadence, permission timing, delivery hour, timezone — **THE-DAILY.md is
> authoritative and this file defers to it.** Its numbers were measured; any I proposed
> independently would be guesses wearing decimal points. §5, §6 and §8.4 below therefore state
> the *mechanism* those decisions run on and cite THE-DAILY.md for the decisions themselves.
> Where an earlier draft of this file disagreed, it has been corrected rather than left as a
> second opinion: two documents in one repository quietly contradicting each other is how a
> build agent ends up implementing the average of them.

---

## 0 · What is being built, in one paragraph, so the rest reads against it

A subscriber gets, on the days there is something to say, one notification naming what is
happening in their own chart — *"Mars crosses your Ascendant today at 14:20"* — which opens a
screen that says it at length. `engine/transits.py` already computes the exact instant an
aspect perfects, by root-finding rather than sampling, and its `Hit` dataclass already carries
`exact_jd`, `enters_jd`, `leaves_jd`, `orb_now`, `applying`, `retrograde` and a `weight`. So
the notification is not a new kind of content. It is a pointer, on the right morning, to
content the engine can already produce and the validator already polices.

The two consequences that shape everything below:

**There are days with nothing to say, and on those days nothing is sent.** A daily that
arrives every morning regardless is a horoscope with extra steps, and it is also the thing
that gets an app's notifications switched off in week two. The silence is a feature and §6
gives it numbers.

**Push is never the only way to read it.** Apple's Guideline 4.5.4 opens with *"Push
Notifications must not be required for the app to function"* and 5.1.2(i) forbids requiring a
user to enable push *"in order to access functionality, content, use the app"*. A subscriber
who denies notifications must still get the daily on the Today screen. That is both the
guideline and the correct product: we are renting them a living layer, not a delivery
mechanism.

---

## 1 · Apple — APNs

### 1.1 Token-based (.p8), not certificates, and why

Two ways exist to authenticate to APNs: a TLS client certificate, or a JWT signed with a p8
key. Take the key.

- **A certificate expires in a year and takes the feature down when it does.** A signing key
  does not expire; it can only be revoked. The failure mode of a certificate is a silent
  outage on a date nobody has in a calendar, discovered by a customer.
- **One certificate is one app in one environment.** A team-scoped key covers every topic on
  the team, so adding a second app or a Notification Service Extension later is a
  configuration line rather than a new credential and a new renewal date.
- **A certificate has to be exported from a Keychain to be useful on a server**, which is a
  ceremony involving a `.p12`, a password, and a Mac. A `.p8` is a text file you paste into a
  secret store.
- The JWT is minted per-process and carries an issue time, so a leaked *token* is worth at
  most an hour. A leaked certificate is worth until you notice.

The one real cost is that the p8 file is a bearer credential of the same class as
`ALMA_JWT_SECRET`: **anyone holding the .p8 plus the Team ID can push to every app on the
team.** It is not a per-app secret and should not be stored as if it were.

### 1.2 What the owner creates, exactly

At `developer.apple.com/account/resources/keys/list`:

1. **A key** with the **Apple Push Notifications service (APNs)** capability ticked.
2. Apple asks for the key's **scope**. The current documentation offers two shapes, and the
   numbers differ:
   - **Team-scoped** — generates tokens for any topic on the team, restricted to **one
     environment**, maximum **2 keys per environment**. Older keys that work in both
     environments continue to function, but Apple now recommends environment-specific keys.
   - **Topic-specific** — up to **200 keys per environment**, up to **400 topics per key**.
   For one app, take **team-scoped**, and create **two**: one Sandbox, one Production. Two
   keys makes the environment a property of the credential rather than of a boolean somebody
   can get wrong, which is exactly the failure §1.7 is about.
3. **Download the `.p8`.** Apple serves it once. There is no second download, and a lost key
   means revoke-and-reissue.
4. Record the **Key ID** — 10 characters, shown next to the key — and the **Team ID**, also 10
   characters, shown in the account's Membership details.

Separately, in **Identifiers → the App ID**, enable the **Push Notifications** capability.
The app's entitlement (`aps-environment`) is what Xcode writes when the capability is on, and
a build signed without it fails registration at
`application(_:didFailToRegisterForRemoteNotificationsWithError:)` rather than at send time.

> **This is blocked by an existing decision.** `apns-topic` *is* the bundle identifier, and
> `STATUS.md §4②` records that the product-id prefix — `alma.` versus `ai.pazl.alma.` — has
> not been chosen. You cannot enable push on an App ID that does not exist yet, and you should
> not create one under a prefix you intend to change.

### 1.3 The key file, and what it holds

A `.p8` is a PEM-armoured PKCS#8 private key on the P-256 curve:

```
-----BEGIN PRIVATE KEY-----
MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg…
-----END PRIVATE KEY-----
```

Roughly 250 bytes. It is not encrypted and it has no password. Store it in the same place as
`ANTHROPIC_API_KEY` — the environment or the host's secret store — and never in the
repository. The `.gitignore` should carry `*.p8` before the file exists, not after.

Proposed configuration names, following `config.py`'s convention that `ALMA_` prefixes
everything we own:

| Variable | What it is |
| --- | --- |
| `ALMA_APNS_KEY_P8` | The PEM contents, or a path to them |
| `ALMA_APNS_KEY_ID` | 10 characters, from the key's page |
| `ALMA_APNS_TEAM_ID` | 10 characters, from Membership |
| `ALMA_APNS_TOPIC` | The bundle identifier — see §1.2's blocker |
| `ALMA_APNS_ENVIRONMENT` | `sandbox` \| `production`; picks the host in §1.5 |

`config.py`'s `/ready` route lists by name everything still missing before real money can
change hands. These belong on the same list: a push transport that is half-configured should
be reported as such rather than discovered by silence.

### 1.4 The JWT

Header and claims, both exactly as Apple specifies:

```json
{ "alg": "ES256", "kid": "<Key ID>" }
{ "iss": "<Team ID>", "iat": 1754563200 }
```

- **`alg` must be `ES256`.** It is the only algorithm APNs supports.
- **A token is valid for at most one hour** from `iat`. Older, and APNs answers `403
  ExpiredProviderToken`.
- **Refresh no more often than once every 20 minutes** and no less often than once an hour.
  Minting a fresh JWT per send earns `429 TooManyProviderTokenUpdates`.

That second rule is a live trap for the shape of job we are building. A daily runner that
starts, sends a few hundred notifications and exits will mint one token and be fine — but a
naive `sign_jwt()` inside the per-notification function will trip it on the second send.
**Cache the token for ~50 minutes in module state.** It costs one variable and it is the
difference between a job that works and a job that works for one user.

The token goes on every request as `authorization: bearer <jwt>`.

### 1.5 The request

```
POST https://api.push.apple.com/3/device/<device-token>       # production
POST https://api.sandbox.push.apple.com/3/device/<device-token>  # development
```

Ports **443** or **2197** — 2197 exists so a network can allow APNs without allowing all
outbound HTTPS. HTTP/2 only, one connection multiplexing many requests, which is why a
sequential job over one connection is fine at our volume and a connection per notification is
not.

| Header | Value for Alma's daily | Note |
| --- | --- | --- |
| `apns-topic` | the bundle identifier | Required. |
| `apns-push-type` | `alert` | Apple's reference marks it required on watchOS 6+ and recommended elsewhere. **Send it always.** The full value set is `alert`, `background`, `complication`, `controls`, `fileprovider`, `liveactivity`, `location`, `mdm`, `pushtotalk`, `voip`, `widgets`; a wrong one is `400 InvalidPushType`. |
| `apns-priority` | **`5`** | `10` is immediate delivery, `5` is power-considerate, `1` defers to the device's own power state. The daily is not urgent and claiming `10` for it is a small lie told to the operating system. `5` also lets APNs coalesce delivery, which is what a person actually wants from a morning notification. |
| `apns-expiration` | end of the recipient's local day, as UNIX epoch seconds | `0` means attempt once and never store. A daily that lands at 23:40 because the phone was off all day is worse than one that never lands, so it should expire rather than queue. |
| `apns-collapse-id` | `daily-<YYYY-MM-DD>`, ≤ 64 bytes | Two sends for the same day replace each other on the lock screen instead of stacking. Cheap insurance against a retry. |
| `apns-id` | a UUID we generate | Optional — APNs mints one otherwise — but generating it ourselves means the id in our log and the id in Apple's Push Notifications Console are the same string. Worth the line. |

### 1.6 The payload

Maximum **4096 bytes** for a non-VoIP notification. That is far more than we need, and the
size is not the constraint. What the payload *contains* is.

**Do not put a written sentence in it.** Two reasons, and both are Alma-specific rather than
general caution:

- **The payload passes through Apple's servers and lands on a lock screen.** Apple's own
  guidance is not to include sensitive data in a payload. A sentence about a named person's
  birth chart is not a credit-card number, but it is a statement about them that we have spent
  the entire product being careful with, and a lock screen is visible to whoever is holding
  the phone.
- **It cannot be translated.** Every user-facing string in this product exists in six
  languages. A sentence composed on the server has to be composed six ways and we have to know
  which one the phone wants — and `user.locale` is what the account chose, not necessarily
  what the device is set to.

Both problems have the same answer, and it is one Apple built for exactly this:

```json
{
  "aps": {
    "alert": {
      "title-loc-key": "push.daily.title",
      "loc-key": "push.daily.transit_exact",
      "loc-args": ["Mars", "Ascendant", "14:20"]
    },
    "thread-id": "daily",
    "interruption-level": "passive",
    "relevance-score": 0.6,
    "sound": "default"
  },
  "kind": "daily",
  "date": "2026-08-07"
}
```

`loc-key` names a string in the app's own `Localizable.strings`; iOS looks it up in the
**device's** language and substitutes `loc-args`. So:

- the six translations live in the app bundle and go through the same locale gate as every
  other string in the product;
- the payload carries a key and three tokens rather than a sentence;
- the server never has to decide which language a phone is in.

`interruption-level: "passive"` is the honest level for a daily — it means the notification
does not light the screen and does not break through a Focus. `relevance-score` between 0 and
1 ranks it inside the notification summary; a daily belongs in the summary, not above it.
`thread-id: "daily"` groups consecutive dailies so a person who did not read Tuesday's does
not find three separate rows on Thursday. Custom keys (`kind`, `date`) go **beside** `aps`,
never inside it, and are what the app reads from `UNNotificationContent.userInfo` to open the
right screen.

**One thing `loc-args` does not do, and it is easy to miss.** The OS substitutes the arguments
**verbatim**. There is no nested lookup, so sending `"Ascendant"` as an argument puts an
English word inside an otherwise-Italian sentence. And the localised placement names currently
live in the *clients* — `journey.ascendant` in `mobile/ios/Alma/Localization/JourneyL10n.swift`,
`cabinet_ascendant` in `mobile/android/…/res/values-it/strings.xml` — where the server cannot
reach them.

So the arguments must arrive already translated, which means **`alma/i18n/` needs a
placement-name table**: roughly seventeen words (the ten bodies, Chiron, the node, Lilith, the
two angles, the luminaries) × six languages ≈ 102 strings. That is a new module the daily can
own outright, and it is an improvement rather than a tax: those words currently exist in three
places — iOS, Android, and nowhere on the server — and a table with a test asserting it agrees
with both clients turns three copies into one source and two mirrors.

The division of labour is then clean and worth stating once: **the `loc-key` template carries
word order and grammar**, which differ across the six languages and belong in a file a
translator opens; **the args carry single words from a closed set**, which the server
substitutes. Neither half is a generated sentence, and neither half can drift.

Which language: the device's, if the client reports it — the same argument as the timezone in
§8.4, and it should ride the same registration call. `user.locale` is the fallback, because it
is what the account chose rather than what the phone is set to.

**The rejected alternative, named because it is the one somebody will propose.** A silent push
(`content-available: 1`, `apns-push-type: background`) that wakes the app, fetches the day's
transits and posts a *local* notification composed entirely on-device would put nothing at all
about the chart into a payload. It is the maximally private design and it does not work:
background pushes are throttled by design, are permitted only at `apns-priority: 5`, and are
delivered when iOS feels like it — and Android's data-only equivalent is deferred by Doze. **A
daily that maybe arrives is not a daily.** The `loc-key` design is the compromise that keeps
the sentence off the wire while keeping the delivery contractual.

### 1.7 Status codes, and what 410 means for a stored token

| Status | What it means | What the sender does |
| --- | --- | --- |
| 200 | Accepted by APNs | Stamp `last_success_at`. Accepted is not delivered. |
| 400 | Bad request | See the reason list below. Every 400 is our bug except the two token ones. |
| 403 | Auth problem | `ExpiredProviderToken` → mint a new JWT and retry once. `InvalidProviderToken`, `BadEnvironmentKeyIdInToken` → stop and page a human; the credential is wrong and retrying will not fix it. |
| 404 | Bad `:path` | Our bug. |
| 405 | Not POST | Our bug. |
| **410** | **Device token no longer active for this topic** | Reasons `Unregistered` or `ExpiredToken`. See below. |
| 413 | `PayloadTooLarge` | Our bug; the payload in §1.6 is nowhere near 4 KB. |
| 429 | `TooManyRequests` (same token) or `TooManyProviderTokenUpdates` | Back off. The second is §1.4's trap. |
| 500 / 503 | APNs is unwell | Retry after **15 minutes** with backoff, per Apple. Not within the same job run. |

Do **not** retry `BadDeviceToken`, `DeviceTokenNotForTopic`, `ExpiredToken`, `Unregistered`,
or `PayloadTooLarge` — they are permanent by definition.

**410 in detail, because the obvious handling is wrong.** The body is:

```json
{ "reason": "Unregistered", "timestamp": 1754563200000 }
```

`timestamp` is **milliseconds** since epoch — the moment APNs confirmed the token stopped
being valid for this topic. It usually means the app was deleted, but it also fires when a
device is restored from a backup onto different hardware.

Apple's own wording is *"no need to retry unless the app retrieves the same device token
again"*, and that sentence is the whole handling rule:

> **Delete the token row only if it has not been re-registered since the `timestamp` APNs
> returned.** If `token.last_registered_at > timestamp`, the app is alive and has told us so
> more recently than APNs told us otherwise — keep the row.

Getting this wrong is not theoretical. A person deletes the app on Monday, reinstalls on
Tuesday, the app registers the same token, and a job that ran Monday's queue on Wednesday
deletes the row on the strength of a stale 410. They stop receiving the thing they are paying
for and nothing anywhere reports an error.

### 1.8 Telling a development token from a production one

This is the classic silent failure: every credential is correct, every request returns 200,
and nothing arrives. It happens because **a device token is only meaningful in the environment
that issued it**, and the two environments are chosen by two different things that can
disagree.

The environment of the **token** is decided by the `aps-environment` entitlement in the build
that produced it:

| Build | `aps-environment` | Token is valid against |
| --- | --- | --- |
| Xcode debug / development profile | `development` | `api.sandbox.push.apple.com` |
| TestFlight | **`production`** | `api.push.apple.com` |
| App Store | `production` | `api.push.apple.com` |

**TestFlight is the trap.** People reason "TestFlight is testing, therefore sandbox" and it is
not: a distribution profile's entitlement allowlist contains `production`, so a TestFlight
build's tokens are production tokens. A backend left on `ALMA_APNS_ENVIRONMENT=sandbox` for
the beta will send every TestFlight tester's notification into the void.

The environment of the **request** is decided by two things, and both must agree with the
token:

1. the host — `api.sandbox.push.apple.com` versus `api.push.apple.com`;
2. **the key**, if you followed §1.2 and made environment-specific team-scoped keys. A
   Sandbox key against the production host is `403 BadEnvironmentKeyIdInToken`.

Symptom table, which is the part worth pinning to a wall:

| What you see | What it is |
| --- | --- |
| `400 BadDeviceToken` | Sandbox token sent to the production host, or the reverse. **This is the mismatch, and it is loud.** |
| `403 BadEnvironmentKeyIdInToken` | The key belongs to the other environment. |
| `400 DeviceTokenNotForTopic` | Right environment, wrong bundle id in `apns-topic`. |
| **`200` and nothing arrives** | Not an environment mismatch — that one 400s. This is permission revoked in Settings, a Focus filter, `apns-expiration` already past, or the token belonging to a device that is off. |

Two things make this diagnosable rather than mysterious, and both should exist before the
first send:

- **Store the environment on the token row.** The client knows which build it is: on iOS,
  read `aps-environment` out of the embedded provisioning profile at runtime, or — simpler and
  more honest — send a build-configuration flag alongside the token at registration. Then the
  sender picks the host per token rather than per deployment, and a production backend can
  serve a developer's simulator without a config change. Without this column, "which
  environment is this token" is unanswerable and every mismatch is a guess.
- **Apple's Push Notifications Console**, inside the CloudKit Console, has a **Device Token
  Validator**: paste a token and a bundle id and it tells you which environment and push type
  it is valid for. It also shows per-`apns-id` delivery logs and aggregate delivery metrics.
  It settles this question in thirty seconds and it is the reason not to spend an afternoon on
  it.

One more, so nobody claims a false success: `xcrun simctl push <device> <bundle-id>
payload.json` delivers a fabricated notification straight to a simulator. It exercises the
app's handling of a payload and **proves nothing whatsoever about APNs, the key, the token or
the server.** Useful for the client, worthless as evidence the transport works.

### 1.9 What App Review requires

Quoted rather than paraphrased, because these are the sentences a rejection cites.

**Guideline 4.5.4 — Push Notifications**, in full:

> Push Notifications must not be required for the app to function, and should not be used to
> send sensitive personal or confidential information. Push Notifications should not be used
> for promotions or direct marketing purposes unless customers have explicitly opted in to
> receive them via consent language displayed in your app's UI, and you provide a method in
> your app for a user to opt out from receiving such messages. Abuse of these services may
> result in revocation of your privileges.

Four obligations, and Alma's answer to each:

1. **Not required to function.** The daily reading is on the Today screen whether or not
   permission was granted. The notification is a pointer to it.
2. **No sensitive or confidential information.** §1.6's payload carries a template key and
   the names of two placements. Whether a birth chart is "sensitive personal information" is
   the same argument `DATA-INVENTORY.md §6` already has open about Apple's Sensitive Info
   category; the `loc-key` design means we do not have to win it.
3. **No promotions or direct marketing without explicit in-app opt-in.** The rule Alma should
   adopt and write into the privacy page is stronger and simpler: **we never send a
   promotional notification at all.** Not "your subscription is expiring", not "come back",
   not "new chapters". The moment one of those ships it needs its own consent screen with its
   own opt-out and its own legal basis under ePrivacy in the EU, and it will also be the
   notification that gets the daily switched off. One kind of push, one purpose, no exceptions
   — that is easier to keep than a consent matrix.
4. **An in-app method to opt out.** Strictly this attaches to marketing messages, which we do
   not send. Build it anyway: a switch in Settings for the daily, separate from the renewal
   notice, so the choice a person makes is "stop this one" rather than "delete the app". §6
   argues that this switch is worth more than any amount of tuning the content.

**Guideline 5.1.2(i)**, the sentence that governs gating:

> Your app may not require users to enable system functionalities (e.g. push notifications,
> location services, tracking) in order to access functionality, content, use the app, or
> receive monetary or other compensation…

So: a subscriber who denies notifications gets the identical product. No "enable notifications
to unlock your daily", no reduced screen, no nag banner where the content would be.

**Guideline 5.1.1(ii)** requires consent for collected data and *"an easily accessible and
understandable way to withdraw consent"*, and says purpose strings must *"clearly and
completely describe your use of the data."* iOS's notification prompt has no developer-supplied
purpose string — the system writes it, and under provisional authorization there is no prompt
at all — which is precisely why the Settings control and the pre-prompt in §5 carry
the explanation instead. And the device token is data we collect, so the withdrawal route is
the Settings switch, and turning it off must **delete the token row**, not merely stop sending
to it.

**When it may ask.** There is no review rule fixing a moment. Apple's own documentation
recommends asking *"in context"* — its example is a task app that asks after the first task is
scheduled rather than at launch — but that is guidance, not a guideline. The constraint that
*is* a review matter is 5.1.2(i) above: whenever you ask, the app must work identically if the
answer is no. The reason to ask late is product, not policy, and §5 makes it.

---

## 2 · Google — FCM v1

### 2.1 There is no alternative, and that costs something

On a device with Google Play services, FCM is the only way to wake an app that is not running.
Android's Doze and App Standby exist specifically to stop apps holding their own sockets open,
and FCM's connection is the one exempt from them. So unlike iOS — where we can talk to APNs
directly and add nothing to the binary — **Android must gain a Google SDK**, and that is a
disclosure change rather than a build detail. §7 spells out what it does to the forms.

This asymmetry is a reason to **not** route iOS through FCM even though FCM can do it. Sending
iOS notifications via FCM would give one send path and one payload shape, which is genuinely
tempting. It would also add the Firebase SDK to an iOS binary that today, per
`DATA-INVENTORY.md §4`, *"links no third-party framework at all"* — `project.pbxproj` declares
no framework build phase — and it would put Google between us and Apple for the one platform
where we do not need an intermediary. Two send paths is the smaller cost. Take it.

### 2.2 The service account

FCM v1 authenticates with OAuth 2.0 rather than the legacy server key. What the owner creates:

1. A **Firebase project**, and inside it an **Android app** registered under the package name.
   That produces **`google-services.json`**, which goes into `mobile/android/app/`. It is not
   a secret — it ships inside the APK — but it does pin the app to a project.
2. **Project settings → Service accounts → Generate new private key.** A JSON file containing
   `client_email`, `private_key` and `project_id`. **This one is a secret**, of the same class
   as the `.p8`.

Proposed configuration:

| Variable | What it is |
| --- | --- |
| `ALMA_FCM_SERVICE_ACCOUNT_JSON` | The JSON, or a path to it |
| `ALMA_FCM_PROJECT_ID` | Also readable from the JSON; named separately so a mismatch is visible |

**This is a second Google service account and must not be merged with the first.**
`billing/googleplay.py:102` already authenticates a service account against the Play Developer
API to verify purchases. Different API, different scope, different blast radius: one can
read purchase state, the other can send a notification to every user. Least privilege is not
an abstraction here — it is the difference between one compromised credential losing a
purchase-verification path and one compromised credential being able to write to every lock
screen we reach.

Minting the access token: sign a JWT with the service account key, exchange it at Google's
token endpoint for a short-lived OAuth2 access token scoped to

```
https://www.googleapis.com/auth/firebase.messaging
```

and send it as `Authorization: Bearer <access-token>`. Tokens last about an hour; the Google
auth libraries cache and refresh, and if we implement it by hand the same 50-minute cache from
§1.4 applies.

### 2.3 The request and the payload

```
POST https://fcm.googleapis.com/v1/projects/<project-id>/messages:send
Authorization: Bearer <access-token>
Content-Type: application/json
```

The mirror of §1.6 — a localisation key and arguments rather than a sentence, resolved on the
device against `strings.xml`:

```json
{
  "message": {
    "token": "<registration-token>",
    "android": {
      "priority": "normal",
      "ttl": "43200s",
      "collapse_key": "daily-2026-08-07",
      "notification": {
        "channel_id": "alma.daily",
        "title_loc_key": "push_daily_title",
        "body_loc_key": "push_daily_transit_exact",
        "body_loc_args": ["Mars", "Ascendant", "14:20"],
        "notification_priority": "PRIORITY_DEFAULT"
      }
    },
    "data": { "kind": "daily", "date": "2026-08-07" }
  }
}
```

- **`priority: "normal"`**, not `"high"`. `high` wakes a dozing device immediately; that is for
  a message a person is waiting for. A daily is not, and Android's own heuristics penalise apps
  that claim high priority for everything.
- **`ttl`** is the counterpart of `apns-expiration` — a duration string, so twelve hours is
  `"43200s"`. Same argument: better absent than late.
- **`collapse_key`** is the counterpart of `apns-collapse-id`.
- **`channel_id`** matters more than it looks. Android 8+ notification channels are the unit a
  person silences. **The daily needs its own channel, separate from the renewal notice**, so
  that "I don't want the horoscope every morning" is expressible without also switching off
  "you are about to be charged $9.99". Putting both on one channel forces a choice nobody
  should have to make and turns an annoyed person into an uninformed one.
- Note that `notification` blocks are handled by the system when the app is backgrounded,
  while `data`-only messages are delivered to the app's service. We want the system to draw
  it — that is what makes it arrive reliably — so the `notification` block is not optional
  here, and the `data` block only carries what the app needs to route the tap.

### 2.4 Errors and token rotation

| Code | HTTP | What to do |
| --- | --- | --- |
| `UNREGISTERED` | 404 | **Delete the row.** The registration is gone and will never be valid again. |
| `INVALID_ARGUMENT` | 400 | Check the payload first — size ≤ 4096 bytes, TTL within 0–2,419,200 s, valid data keys. If the payload is provably fine, the registration is malformed and the row goes. |
| `SENDER_ID_MISMATCH` | 403 | The token belongs to a different Firebase project. A configuration error, usually two projects for dev and prod. |
| `QUOTA_EXCEEDED` | 429 | Slow down; back off with a **minimum one-minute** initial delay. |
| `UNAVAILABLE` | 503 | Retry with exponential backoff and **honour `Retry-After`**. |
| `INTERNAL` | 500 | Retry with backoff. |
| `THIRD_PARTY_AUTH_ERROR` | 401 | The APNs credential *inside Firebase* is wrong. Cannot occur for us — we do not route iOS through FCM (§2.1). |
| `UNSPECIFIED_ERROR` | — | No information available. Log it and move on. |

**Rotation, which is the part with a number in it.** Google's registration-management guidance:

- **Android registrations inactive for 270 days are garbage-collected by FCM** and rejected
  thereafter. A device coming back gets a new Firebase Installation ID.
- **For non-Android platforms FCM does not expire anything automatically**; the guidance is to
  proactively remove registrations inactive for roughly **30 days**. We inherit that discipline
  for APNs tokens too, where nothing at all expires them for us.
- **Refresh monthly, and never more often than weekly.** Google's own words: monthly *"strikes
  a good balance between battery impact and detecting inactive registration tokens."*
- **Stamp a timestamp on every upload**, whether or not the token changed, and sweep on the
  timestamp rather than on the token's age.

Which gives the token table's operational rule, one sentence: *the client re-registers on every
launch and we bump `last_seen_at`; a row whose `last_seen_at` is older than 90 days is deleted
whether or not it has ever errored.* Ninety rather than thirty because a subscriber who does
not open the app for six weeks is exactly the person the daily exists for; thirty days would
delete the token of the customer we most want to reach. Ninety still bounds the retention and
still satisfies "do not hold what you cannot use."

### 2.5 What Play requires

**The runtime permission.** Since Android 13 (API 33), posting a notification requires
`POST_NOTIFICATIONS`, declared in the manifest and granted at runtime:

```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
```

Android's build already declares only `INTERNET` and `com.android.vending.BILLING`
(`AndroidManifest.xml:4–7`), so this is a visible, reviewable addition to a very short list.
It is an ordinary runtime permission — not one of Play's "sensitive" permissions requiring a
declaration form — so it adds no Console paperwork. It does add a Data safety obligation, via
the SDK rather than the permission; §7 has it.

Behaviour, which drives §5:

- **Fresh install on Android 13+: notifications are OFF by default.** Nothing is delivered
  until the permission is granted.
- **Upgrade from 12L or lower:** if the app already had a notification channel and the user had
  not disabled notifications, the permission is pre-granted silently. Irrelevant for a first
  release, but it means a future channel change is not a re-consent.
- **Target 13 or higher** — Android's build already targets 36 (`app/build.gradle.kts:15`) —
  and the app controls *when* the dialog appears. Target 12L or lower and the system fires it
  automatically on the first activity after a channel is created, i.e. at launch, with no
  context. We have the good version of this by default.
- **After a denial the system does not prompt again** until the app is reinstalled or its
  target SDK is raised. Practically: one shot, same as iOS.

**The Data safety form** must be updated before the release that contains FCM. §7.3 lists the
rows.

**The User Data policy** requires an in-app **prominent disclosure** *before* requesting a
permission that accesses sensitive data, and requires a privacy policy at an *"active,
publicly accessible and non-geofenced URL"* both in the Console and inside the app. The
notification permission is not itself sensitive-data access, so the formal prominent-disclosure
requirement is not triggered — but the Settings-first sequence in §5.5 is exactly that
disclosure and it
costs nothing to write it as if it were. Play also requires permissions to be *"necessary for
the app's core functionalities as promoted in your Google Play listing"*, which means
`LISTING.md` should mention the daily. A permission the listing never explains is a permission
a reviewer asks about.

**Ads.** Play's Ads policy requires that ads display only inside the app serving them and not
*"make changes outside the app without the user's knowledge or consent."* We send no ads and no
promotions, per §1.9's rule, so this is a line to stay on the right side of rather than a
requirement to satisfy.

---

## 3 · The contract between the app and the backend

Not code, and deliberately shaped so it can be built without touching a file another workflow
owns.

**A new table, `device_token`:**

| Column | Why |
| --- | --- |
| `id`, `user_id` | Whose. Indexed; a person has several devices. |
| `platform` | `ios` \| `android`. |
| `token` | Apple's device token or FCM's registration token. Unique with `platform`. |
| `environment` | `sandbox` \| `production`, iOS only. §1.8's whole argument. |
| `timezone` | The device's own IANA zone, persisted rather than read per-request. Rung 1 of `THE-DAILY.md §3.3`'s ladder, and the reason §8.4 can send at 08:00 local. |
| `app_version`, `os_version` | So a bug can be scoped to a build. |
| `created_at`, `last_seen_at` | `last_seen_at` bumped on every re-registration; §2.4's sweep reads it. |
| `last_success_at`, `fail_count`, `disabled_at`, `disabled_reason` | So "it stopped working on the 14th" is answerable. |

**Three obligations that are easy to forget and expensive to forget:**

1. **`accounts.erase` must delete these rows**, and `DATA-INVENTORY.md §3`'s retention table
   must gain the line. That file's own §5.4 already warns that a table holding a person's data
   and absent from `erase` is *"a promise this project has broken without noticing."* Do not
   add the second instance of it.
2. **`GET /v1/account/export` should include them** — device, platform, when it registered.
   `DATA-INVENTORY.md §5.6` already records four categories the export omits; do not make it
   five.
3. **A `UsageCounter` row keyed `user:date:daily_push`** is what makes the job idempotent. This
   is not a new pattern: `renewals.py` uses exactly it under `METRIC = "renewal_notice"`, for
   exactly the same reason — *"retrying a failed send is right; sending twice because a job ran
   twice is not."* Add `daily_push` to the metric table in `DATA-INVENTORY.md §1.11` alongside
   it.

**Three things I need from files another workflow currently owns.** Stated as contracts rather
than edits, per the brief. The first two are the same asks `THE-DAILY.md §6.8` makes; they are
listed once in each file on purpose, so that whoever reads either one knows the whole request.

- **`alma/api/deps.py`** — an **`X-Alma-Timezone`** request header, an IANA identifier,
  validated through the existing `geo.is_known_timezone()`, ignored silently when absent or
  unrecognised, exactly as the country header is. **It must be persisted onto the device-token
  row, not merely read per-response**, because the notification job runs on a server at 03:00
  and has no request to read a header from. Separately: the register and delete routes want
  `require_account` as it already stands — a token is only useful joined to a user — so no
  change is needed for that half, and it is named here so nobody adds a second dependency.
  **Landed** as `deps.device_timezone`, with the persisting done by
  `POST /v1/notifications/devices`; `THE-DAILY.md §3.2` carries the detail.
- **`alma/auth/accounts.py`** — the notification preference (`THE-DAILY.md §5.1`'s three
  positions), the delivery hour and the timezone override belong on the **user**, not the
  profile: a person has one phone and several charts. And `erase` must walk the token table,
  per obligation 1 above.
- **`alma/funnel.py`** — measuring the daily needs two new stage names, something like
  `daily_sent` and `daily_opened`, added to the closed set at `funnel.py:124–142`. The set is
  closed on purpose and an unknown name is a 422 rather than a row, so this cannot be worked
  around from outside the file. **Until those two names exist, the daily is unmeasured** — and
  §6.3's switch-off ratio, which is the only number that measures the thing the owner actually
  asked for, does not exist either. Ask for them in the same change that lands the schedule.

---

## 4 · Who gets it

The owner's words were *«для подписчиков»*. So: `tier_of()` returns `subscriber`, and the
daily is a subscriber feature, matching `LIVING_SYSTEMS = {transits, solar-return,
compatibility}` — the daily is the transits layer arriving on its own.

Two consequences worth stating rather than assuming:

- **When a subscription lapses, the daily stops.** Not at the next renewal date but at the
  moment `is_in_force` goes false, which is what `entitlements.py` already computes. A person
  who has stopped paying and keeps receiving the paid feature learns that the paid feature was
  never the reason to pay.
- **The token row survives a lapse.** Deleting it on cancellation and re-asking for permission
  on resubscription would spend the one-shot permission twice. Keep the row, stop the sends.

Whether a *free* user who has saved a birth should get, say, one a month as an argument for the
paid tier is a real product question and it is not mine to answer. Flagged, not decided.

---

## 5 · Permission timing — where in Alma's journey somebody says yes

### 5.1 Why the first launch is the wrong moment, with the mechanism

On **iOS**, `requestAuthorization` prompts once. Ever. After a denial the status is `.denied`
and subsequent calls return the recorded answer without showing anything; the only route back
is the person going to Settings → Alma → Notifications, which effectively nobody does. On
**Android 13+**, after a denial the system does not prompt again until the app is reinstalled
or its target SDK is raised.

So this is not a prompt that can be retried until it lands. **It is one question, asked once,
for the life of the install.** Every argument below follows from that single fact.

At first launch we have, specifically, nothing. No birth date, no birth time, no place, no
chart. There is nothing we could notify anybody about, because the entire content of a daily
is derived from a chart that does not exist yet. Asking at that moment spends the one question
on a promise we cannot describe, to a person with no reason to believe it, and the reflexive
answer to a system dialog from an unknown app is no.

### 5.2 The moments that look right and are not

- **The portrait.** The end of the free journey, the first time the product proves it computed
  something real — sun, moon, ascendant, life path, birth card, moon phase. It is the highest
  point of goodwill in the funnel and that is exactly why not: it is also the moment we are
  asking them to go to a store, and interrupting the payoff with a system dialog spends the
  best thirty seconds the product has on the wrong ask.
- **Immediately after purchase.** The receipt screen is where a person is most alert to being
  sold something else. A permission dialog there reads as the second half of a transaction.
- **A buried settings switch nobody finds.** Note the qualifier — the setting itself is right
  and `THE-DAILY.md §5.1` builds the feature around it. What fails is a switch reachable only
  from a settings list. It needs a second entrance from the surface the content is on, which
  is the Today page, worded as what it is: *tell me the morning it happens*. The setting is the
  control; the Today page is where a person discovers there is one.

### 5.3 The two platforms need different answers, and THE-DAILY.md picked them

`THE-DAILY.md §5.3` settles the shape, and it is not symmetric:

> **iOS: provisional authorization.** No prompt, ever, at the start. **Android: ask
> `POST_NOTIFICATIONS` at the moment the person turns the setting on, never at launch.**

The asymmetry is not an inconsistency — it is the two operating systems offering different
instruments. iOS has a trial mode; Android has none. The rest of this section is the mechanism
each rests on, which is what this file is for.

### 5.4 iOS — how provisional actually behaves

Requesting `[.alert, .sound, .badge, .provisional]` returns granted **without showing
anything**. `authorizationStatus` becomes `.provisional`, and:

- Notifications are delivered **quietly to Notification Center only** — no banner, no sound,
  no lock screen, no badge.
- Each one carries **Keep** / **Turn Off** buttons. Choosing *Keep* then offers **Deliver
  Immediately** or **Deliver in Scheduled Summary**.
- The person decides after seeing two or three real ones what a real one is like.

That last point is why THE-DAILY.md chose it, and the argument is the product's own: this
feature's entire claim is that its notifications are worth having, and provisional is the
mechanism that lets us *prove* that instead of asserting it up front. It is also why the
measured cadence in §6 makes it work — at roughly one a week, three notifications is three
weeks, not three days.

**Four mechanical facts that shape the build:**

1. **`.provisional` is not `.authorized`.** Check `notificationSettings()` before assuming a
   banner will appear. A person left in `.provisional` for a year is a supported state, not a
   failure — they are receiving the product, quietly.
2. **Provisional is an escalator, not a dead end.** From `.provisional` you may later call
   `requestAuthorization([.alert, .sound, .badge])` *without* `.provisional`, and the system
   **does** show the prompt, because the person has never actually been asked. That is the
   documented upgrade pattern and it is the moment §5.2's reasoning applies: ask it attached
   to a specific dated transit on the Today screen, not on a timer.
3. **`.denied` is still terminal.** If somebody taps *Turn Off* on a notification or denies
   the later prompt, provisional cannot rescue it. The one-shot rule survives; provisional only
   moves *when* the shot is taken.
4. **Known defect worth designing around**: on iOS 16 and later there are recurring reports
   that choosing *Deliver Immediately* does not fully update the settings — sound, badge and
   lock-screen stay off. Do not build anything that assumes the upgrade landed. Read
   `notificationSettings()`, believe it, and let the explicit request in (2) be the reliable
   path.

**One store consequence, and it is the reason §1.9(3) matters more than it looks.**
Provisional authorization is **not** an explicit opt-in. Guideline 4.5.4 requires promotions
and direct marketing to have *"explicitly opted in… via consent language displayed in your
app's UI"*, and a permission the person was never asked for cannot be that consent. So under
provisional, **a promotional push is not merely against our own rule — it has no consent basis
at all.** The no-promotions rule is what makes provisional safe to use.

### 5.5 Android — the pre-prompt, which is not optional

Android has no trial mode, so the one-shot problem is undiluted: after a denial the system does
not prompt again until reinstall or a target-SDK bump. Never call the platform API first. The
sequence:

1. **The person turns the daily on**, in Settings — one of the three positions in
   `THE-DAILY.md §5.1`. That act *is* the pre-prompt; it is in our own UI, in six languages,
   with the frequency described honestly beside it.
2. **Then** launch the `POST_NOTIFICATIONS` request.
3. If the system answer is no, that is final, and the app must not nag. Show the state once —
   *"Notifications are off. You can turn them on in Settings."* — and never again. Reflect it
   in the switch rather than leaving a control that claims to be on and delivers nothing.

The point of the ordering is that our own question is repeatable and the platform's is not. A
person who taps the setting off and on again next month costs us nothing; a person who denies
the system dialog costs us the install. Never spend the second on a moment that could have been
the first.

### 5.6 What both platforms need regardless

- The **denied state** must be visible and honest, once. `THE-DAILY.md §5.4` already names the
  strings.
- **`areNotificationsEnabled()` / `notificationSettings()` are the truth**, not our own flag.
  A person who revokes permission in the OS must not leave us with a switch that says On.
  Check on foreground and reconcile.
- **Nothing is gated on the answer.** Guideline 5.1.2(i), §1.9 above. The Today page is the
  product; the notification is a pointer to it.

---

## 6 · "Not annoying" — the numbers, and the mechanisms that enforce them

### 6.1 The numbers are THE-DAILY.md's, and they were measured

`THE-DAILY.md §4` simulated a selection rule over 24 charts for a year and published the whole
distribution. Restated here so this file is usable on its own, **not re-derived**:

| | |
| --- | --- |
| Hard cap | **2 per week, 10 per calendar month** |
| Floor | **zero** — a month with nothing in it is a correct month |
| Qualifies | `Hit.weight ≥ 0.35` **and** something true today that was not true yesterday — it perfects today, or (Jupiter and outward, weight ≥ 0.30) it enters orb today |
| Minimum gap | **3 days** |
| Measured result | median **46/year = 0.88/week**; noisiest chart in the cohort **1.13/week**; the cap never binds |
| Longest silence | 60 days, and that is the rule working |

The finding worth carrying into the transport layer: **the astronomy, filtered honestly,
already produces a cadence inside the safe band.** The cap is a guard against a chart nobody
has seen, not a mechanism the design leans on. A cap that does the work is a cap lying about
the content.

The economics behind why the direction is one-sided, since they belong to this file: a
subscription nets **$8.99/month** in the US and **$7.33** in the EU; sending costs **$0** on
both platforms; an uninstall costs **the entire remaining lifetime of that subscription** and
is not recoverable, because there is no channel to an app that is no longer installed. The
expected value of a marginal notification is negative unless it is clearly worth reading.

### 6.2 The mechanisms this file owns

Numbers are policy; these are the parts that have to be true in the transport or the numbers
are decoration.

1. **Idempotency is a row, not a convention.** A `UsageCounter` keyed `user:date:daily_push`,
   exactly as `renewals.py` keys `renewal_notice` and for the identical reason — *"retrying a
   failed send is right; sending twice because a job ran twice is not."* The 3-day gap and the
   monthly cap are both read off these rows, so they survive a job that runs twice, a job that
   runs on two hosts, and a deploy mid-run.
2. **`apns-priority: 5` and `android.priority: normal`.** Claiming urgency for something that
   is not urgent is a small dishonesty both operating systems eventually charge for in
   delivery heuristics.
3. **Expire rather than queue.** `apns-expiration` at the end of the local day; `ttl` on the
   FCM side. `THE-DAILY.md §3.5` makes the same call from the product direction — a daily that
   lands inside quiet hours is **dropped, not deferred**, because a daily is about a day.
4. **Collapse on the date.** `apns-collapse-id` / `collapse_key` = `daily-<YYYY-MM-DD>`, so a
   retry replaces rather than stacks.
5. **Separate Android notification channels.** The daily and the renewal notice must never
   share one. The renewal notice is a promise the subscription-terms page makes in six
   languages — *"not a marketing email and you cannot unsubscribe from it"* — and a shared
   channel would let a person silence a legal commitment by silencing a horoscope. This is a
   one-line decision at build time that is very expensive to change afterwards, because
   channel ids are permanent for an install.
6. **Off deletes the token row.** Not a flag consulted before sending — the row. It is §1.9's
   withdrawal-of-consent obligation and the simplest possible proof that off means off. Note
   the interaction with `THE-DAILY.md §5.1`'s three positions: *Occasionally* and *Only what
   matters* both keep the token; only **Off** deletes it.
7. **No promotional push, ever.** §1.9(3), and under provisional authorization on iOS there is
   no consent basis for one anyway (§5.4).

### 6.3 What to watch

`THE-DAILY.md §7` already names the right metric and it is worth repeating because the wrong
one is so much easier to collect:

> the ratio of **Off** to **Occasionally** after 30 days

Not the open rate. An open rate can be flattered by sending more; a switch-off cannot. Add to
it, from the transport side, **permission revocations per hundred sends** — a person who
silences us in the OS never touches our setting and would be invisible to the first metric
alone. If either number rises, the weight floor goes up. Not the volume.

Both need the two `funnel.py` stage names in §3, which another workflow owns.

### 6.4 What it costs to produce

The notification body is **assembled, not generated**. `Hit.describe()` already produces the
citable string and §1.6's payload needs three tokens out of it. So the push itself costs
nothing, cannot hallucinate, and — because it is a `loc-key` — goes through the same
six-language gate as every other string in the product. Three wins from one decision, and the
reason not to ask a model to write a lock-screen sentence.

The **reading behind it** is a generation. `THE-DAILY.md §2` priced it properly through
`ai/cost.py`; at the measured cadence it is a rounding error against $8.99 net and against the
`ALMA_SUBSCRIBER_MONTH_BUDGET` ceiling of $3.50 that `ai/cost.py` enforces before the call
rather than regretting after it. It must still be counted through `cost.guard_month` like
everything else rather than around it — a budget with an exception in it is not a budget.

---

## 7 · Privacy — a device token is personal data

A push token is a persistent identifier for a specific installation on a specific device,
stored against a `user_id`, and it is only useful joined to one. It is personal data in the
GDPR sense, a **Device ID** on Apple's form, and **Device or other IDs** on Play's. The
declarations have to move with the code, and `DATA-INVENTORY.md` is the file every other
disclosure is derived from, so it moves first.

**These files are not edited here — they belong to the store package.** This is the list of
what each has to say.

### 7.1 `mobile/store/DATA-INVENTORY.md`

**A new category in §1**, in the same seven-question shape as the rest:

> **§1.18 Push tokens — `device_token`**
> - **What**: an APNs device token (iOS) or an FCM registration token (Android), plus
>   `platform`, the APNs `environment`, app and OS version, and the four timestamps in §3
>   above.
> - **Stored**: our database. On the device, iOS holds nothing — Apple's own guidance is
>   *never cache device tokens in local storage* — while Android's FCM SDK maintains its own
>   registration in app-private storage.
> - **Sent to**: **Apple**, as the `:path` of every APNs request; **Google**, as the `token`
>   field of every FCM send. In both cases the identifier is *theirs*, returned to them.
> - **Why**: to deliver the daily, and nothing else.
> - **Kept**: until the switch is turned off, the token 410s / `UNREGISTERED`s, 90 days of
>   silence pass, or the account is erased.
> - **Linked to identity**: **yes**, necessarily.
> - **Tracking**: no. Not an advertising identifier, never joined with another company's data,
>   never leaves our backend except to the transport that issued it.

**§1.11's metric table** gains `daily_push` — written by the daily job, one row per user per
day, the idempotency record.

**§2.2 is currently false the day the first push is sent.** It reads *"Apple: nothing
outbound."* It must be rewritten to name `api.push.apple.com` as an outbound destination and
say what travels: the device token and the §1.6 payload — a template key, the names of the
placements involved, a clock time, and a date. Nothing about identity, no name, no birth date,
no coordinate.

**A new §2.7, Google — FCM**, with the same precision, and one extra paragraph that has
nothing to do with the notification itself: adding `firebase-messaging` to the Android build
brings the **Firebase Installations service** in transitively. It mints a **Firebase
Installation ID (FID)** and sends it, along with the Firebase user agent — device metadata,
OS version, SDK versions — to Google. Firebase's own Play-disclosure page says a FID *"does not
uniquely identify a user or physical device"*, that FIDs rotate on reinstall or cache clear,
that they are deleted after **270 days of inactivity**, and that deleting an installation
removes the associated data from live and backup systems **within 180 days**. All of that is
Google's collection, on our behalf, and it is declarable whether or not we ever read a FID.

**§3's retention table** gains: *Push tokens — **Deleted** — `accounts.erase`*. And the `erase`
walk must actually delete them; see §3's first obligation above.

**§4's absence table needs two qualifications**, and they are the honest cost of this feature:

- *"No third-party analytics SDK"* stays true — `firebase-messaging` is not analytics and
  `firebase-analytics` must not be added — but the **"one honest qualification"** at the end
  of §4 changes materially. Today it says the only Google dependency we ask for is Play
  Billing and the rest arrive transitively behind it. After this, `firebase-messaging` is a
  **declared** dependency in `libs.versions.toml`, `google-services.json` ships inside the
  APK, and the Google Services Gradle plugin is in the build. Rewrite that paragraph rather
  than leaving it to be discovered during a Data safety review.
- *"iOS links no third-party framework at all"* **stays true**, and §2.1's decision to talk to
  APNs directly is what keeps it true. That sentence is worth defending.

**§7's open questions** gain two:
- Are Apple and Google **processors** for the token and the payload, or independent
  controllers of an identifier they issued? The `shared` answer on Play's form turns on the
  same reasoning the Anthropic DPA question already turns on.
- Does the host's access log record anything about the registration route? Same unanswered
  hosting question as `§1.17`.

### 7.2 `mobile/store/APP-PRIVACY.md`

- **Identifiers → Device ID** already reads **Yes / Linked / Not tracking**, for the
  `X-Alma-Anon` UUID in `Networking/InstallationId.swift`. The **APNs device token is a second
  thing in that box** and the row's prose must name it: what it is, that it exists only after
  an explicit grant, that it is linked because it is stored against a `user_id`, and that
  tracking stays **No** — it is not an advertising identifier, `NSPrivacyTracking` stays
  `false`, and the app still needs no ATT prompt.
- **The privacy manifest** (`PrivacyInfo.xcprivacy`): `NSPrivacyCollectedDataTypeDeviceID`
  should already be present for the anon id. Confirm it, and confirm its purpose array covers
  App Functionality as well as Analytics — the token's purpose is functionality, the anon id's
  is analytics, and they now share a box.
- **A new note beside the grid**: the shipped binary carries the `aps-environment` entitlement
  and the Push Notifications capability on the App ID. Reviewers can see both.
- **The 4.5.4 paragraph** the file does not yet have: what we send, that it is never
  promotional, that there is an in-app switch, and that the app is fully functional with
  notifications denied. That paragraph is also the text `REVIEW-NOTES.md` should carry, since
  it is what a reviewer reads before deciding whether to ask.
- **Nothing else on the grid moves.** No new user content, no new contact info, no location.
  The daily reads a chart we already hold and sends a key and three words about it.

### 7.3 `mobile/store/DATA-SAFETY.md`

- **Device or other IDs** — currently **Yes / Optional / Analytics** for the `X-Alma-Anon`
  UUID from `data/Measurement.kt`. Three additions to the same row: the **FCM registration
  token**, the **Firebase Installation ID**, and the **Firebase user agent**. Purposes gain
  **App functionality** and — this is the row a reviewer looks for — **Developer
  communications**, which is Play's own name for exactly what a daily is. Stays **Optional**:
  a person who denies `POST_NOTIFICATIONS` never generates one.
- **App info and performance** — currently **No** across the board. Firebase's Play-disclosure
  page lists *"Application version"* as collected by Cloud Messaging for topic
  subscription/unsubscription. **We do not use topics** — we send to individual tokens — so
  that specific collection should not occur, and the honest answer is a documented *No, with
  the reason*, not a silent No. The Firebase user agent is a separate matter and belongs under
  Device or other IDs above.
- **The "one honest qualification"** about transitively-arriving Google libraries must be
  rewritten for the same reason as §7.1: `firebase-messaging` becomes a declared dependency.
- **Security practices → deletion** is unchanged **provided** the token row is in
  `accounts.erase`. It is a false declaration otherwise.
- **A note on the permission**: `POST_NOTIFICATIONS` is an ordinary runtime permission, not one
  of Play's sensitive permissions, so no declaration form. But Play requires permissions to be
  necessary for core functionality *as promoted in the listing* — so `LISTING.md` has to
  mention the daily, in all twelve listings.

### 7.4 `src/app/(legal)/privacy/page.tsx`

The page renders under `lang="en"` by policy and does not get a language picker
(`STATUS.md §5.3`), so this is English only — but see §7.5 for the strings that are not.

- **"What Alma holds"** (line 36) gains a bullet: a push token, what it is in one clause
  (*"a number the phone's operating system gives us so it can be told to show you something"*),
  that it exists only if notifications were turned on, and that turning them off deletes it.
- **"What leaves the service"** (line 163) gains **Apple** and **Google** as recipients, with
  what each sees: a token that is their own identifier, and a notification consisting of a
  template name plus the names of the placements involved and a time. The page's
  *"Three companies, and this is the complete list"* sentence at line 112 is already wrong for
  a different reason — `DATA-INVENTORY.md §5.1` documents that it names a card processor the
  app never touches and omits the two stores — and this is the second reason to fix it in the
  same pass rather than the third time.
- **"What Alma never does"** (line 227) gains the sentence that makes §1.9(3) a commitment
  rather than an intention: *we never send a promotional notification.* This is also what
  settles the ePrivacy question in the EU before anyone asks it — consent for direct marketing
  by electronic means is not required for messages that are not direct marketing, and the way
  to keep that true is to write it down where it costs something to break.
- **"Taking it back"** (line 272) gains the two off switches: ours, in the app, which deletes
  the token; and the operating system's, which stops delivery and leaves us holding a token we
  will sweep in 90 days.
- **"How long it is kept"** (line 357) gains the 90-day silent-token sweep, and it must agree
  with whatever constant the code uses. `src/lib/legal.ts` already holds the funnel's 180 days
  with a vitest that fails if the two disagree; the token window should be held the same way
  rather than typed into prose.

### 7.5 The six languages

Every user-facing string here exists in en, es, de, it, fr, pt-BR. `LOCALES` is
`("en", "es", "de", "it", "fr", "pt-BR")` in both `alma/i18n/__init__.py:89` and
`src/lib/i18n/index.ts:41`, and `scripts/check-locales.mjs` fails the build on English left
behind. Three places, three different owners:

**In the app bundles** — `mobile/ios/Alma/…/Localizable.strings` and
`mobile/android/app/src/main/res/values*/strings.xml`:

- **The notification templates** — every `loc-key` in §1.6 and `body_loc_key` in §2.3. The
  shape a translator needs is a format string with *positional* placeholders, because the six
  languages put the words in different orders. That is the whole reason for `loc-args` rather
  than a pre-composed sentence, and it is easy to undo by accident.
- **The Settings control** — `THE-DAILY.md §5.4` already writes the English source set for the
  three positions and their detail lines, and says who should translate them and against what
  reasoning. Do not invent a second set.
- **The denied state**, shown once (§5.6).

**On the server** — the new placement-name table in `alma/i18n/` from §1.6. Roughly 102
strings, and the test that matters is not "is it translated" but **"does it agree with the two
clients"**, since the same seventeen words already exist in `JourneyL10n.swift` and
`strings.xml` and a disagreement would show up as one Italian sentence with one English noun in
it.

**Not translated, deliberately** — `src/app/(legal)/privacy/page.tsx`. The five legal documents
render under `lang="en"` by policy (`STATUS.md §5.3`); a picker there would offer a choice the
page cannot honour. §7.4's additions are English only, and that is the existing rule rather
than an exception made for this feature.

---

## 8 · What sends them

### 8.1 The actual problem

There is no job runner in this repository. There is no scheduler, no queue, no worker, no
broker. `backend/README.md` documents **two** commands that must run daily and are not
scheduled anywhere:

```cron
17 9 * * *  cd /srv/alma/backend && .venv/bin/python -m alma.billing.renewals
41 3 * * *  cd /srv/alma/backend && .venv/bin/python -m alma.funnel --purge
```

The first sends the letter three days before a subscription is charged — a promise printed on
the paywall, in the FAQ, on the subscription-terms page and beside the pay button. The second
is the whole of what makes the privacy page's 180-day deletion true. **Neither is running.**
The daily makes three, and the README already wrote the sentence that matters:

> a run that never happens sends nothing at all, for ever, and looks exactly like success.

So the requirement is not "something that runs a job". It is **something that runs a job and
tells you when it did not.**

### 8.2 What was considered

**A queue and workers — Celery or RQ, with Redis.** Buys retries, concurrency, a scheduler
(`beat`), and a dashboard. Costs a broker to run, a worker process to supervise, a beat
process that must be a singleton or every job doubles, and a Redis whose durability settings
are now part of whether a customer gets warned about a charge. Rejected: there is no queue
here. There is one job, once a day, over a few thousand rows, and every job in it is already
idempotent by design. Three new failure modes bought a feature we do not need.

**Airflow, Dagster, Temporal.** Rejected without argument. Three cron lines.

**GitHub Actions `schedule:`** hitting an authenticated endpoint. Free, keeps a run history,
emails on failure. Rejected: Actions cron is explicitly best-effort and is routinely delayed
during peak load, schedules are disabled on repositories inactive for 60 days, and it puts a
production trigger behind a CI credential — a compromised Actions secret would be able to fire
the notification job. A cron that is sometimes forty minutes late is survivable; one that
silently stops after two quiet months is the exact failure we are trying to design out.

**A managed scheduler on the hosting platform** — Render cron jobs, Fly machines with a
schedule, Railway cron. Genuinely good: logs and run history in the same dashboard as the app,
nothing new to operate. The reason it is not the recommendation is that the host is not chosen
yet (`DATA-INVENTORY.md §1.17` and `STATUS.md §4` both have the hosting question open), and on
most of these platforms a scheduled job runs as a **separate instance** — which means the
`.p8` and the FCM service-account JSON exist in a second place, with a second chance to be the
wrong environment. If the owner picks a platform whose scheduler shares the app's secret store
and its environment, this becomes at least as good as the recommendation below. It is a close
second, not a wrong answer.

**A loop inside the API process** — `asyncio` sleeping until 08:00. Rejected: it runs N times
when the API runs N replicas, it dies with a deploy, and "did the job run" becomes a question
about which process was alive at 08:00.

### 8.3 The recommendation

**systemd timers on the same host as the API, plus a dead-man's switch.**

```ini
# /etc/systemd/system/alma-daily.service
[Unit]
Description=Alma — the daily push
After=network-online.target

[Service]
Type=oneshot
User=alma
WorkingDirectory=/srv/alma/backend
EnvironmentFile=/etc/alma/env
ExecStart=/srv/alma/backend/.venv/bin/python -m alma.notify.daily
```

```ini
# /etc/systemd/system/alma-daily.timer
[Unit]
Description=Alma — the daily push; hourly, sends to whoever's local clock says 08:00

[Timer]
OnCalendar=*-*-* *:00:00
Persistent=true
RandomizedDelaySec=120

[Install]
WantedBy=timers.target
```

**Hourly, not daily** — 08:00 happens twenty-six times around the world and §8.4 is the whole
argument. The two existing jobs stay daily; nothing about a renewal notice or a retention purge
cares what hour it is.

Why this and not `crontab`, which is one line shorter:

- **`systemctl list-timers` prints the last run and the next run** for every job, in one table.
  `crontab -l` prints what you *intended*. That difference is the entire "reasoned about at
  three in the morning" property, and it is worth six lines of ini.
- **`journalctl -u alma-daily` has the output**, with timestamps and exit codes, rotated by the
  system. Cron's answer is mail to a local mailbox nobody reads, on a host that probably has no
  MTA configured.
- **`Persistent=true` runs a missed job when the machine comes back.** This is the same
  property `renewals.py`'s ±1-day window was designed around, and it is the property crontab
  does not have — a box down at 09:17 simply skips the day.
- **`RandomizedDelaySec`** stops three jobs from starting on the same second forever.
- **Nothing new is deployed.** No broker, no second instance, no additional network dependency,
  no second copy of the `.p8`. The failure surface is the box, and the box is already the
  failure surface for the API.

Run all three the same way, so there is one mechanism to understand:

| Timer | Command | When | Status today |
| --- | --- | --- | --- |
| `alma-daily` | `python -m alma.notify.daily` | **hourly**, on the hour (§8.4) | does not exist |
| `alma-renewals` | `python -m alma.billing.renewals` | 09:17 UTC | **written, documented, never scheduled** |
| `alma-funnel-purge` | `python -m alma.funnel --purge` | 03:41 UTC | **written, documented, never scheduled** |

That third column is the reason this section is long. Two of the three jobs already exist, are
already documented in `backend/README.md`, and have never run — and one of them is the only
thing making the privacy page's 180-day deletion promise true. Wire all three at once, or
the daily just becomes the third entry on a list of things somebody meant to do.

**The dead-man's switch is not optional and it is the actual recommendation.** A timer that
stops firing is invisible; that is the whole problem this section exists for. Each job pings a
URL on success, and the monitor alerts when a ping does not arrive inside its window:

```
ExecStartPost=/usr/bin/curl -fsS -m 10 --retry 3 https://hc-ping.com/<uuid>
```

`ExecStartPost` only runs if `ExecStart` succeeded, so a crash is a missed ping and a missed
ping is an email. Healthchecks.io's free tier covers 20 checks; it is also open-source and
self-hostable if the owner would rather not add a third party for this. **Cost: $0.**

### 8.4 The daily timer is hourly, not daily

`THE-DAILY.md §3.4` fixes delivery at **08:00 in the person's own clock**, and §3.3 gives the
timezone ladder — device-reported zone, then a chosen override, then `Profile.timezone`, then
an unreachable UTC fallback. §3.5 adds hard quiet hours, 22:00–08:00 local, **dropped rather
than deferred**.

08:00 happens twenty-six times around the world, so a once-a-day job can only be 08:00
somewhere. The correct shape — and `THE-DAILY.md §6.9` reaches it independently — is **one job
that runs hourly and selects the people whose local hour is now 08:00**:

```ini
OnCalendar=*-*-* *:00:00
Persistent=true
RandomizedDelaySec=120
```

It is safe because it is idempotent per user per day by construction: the `UsageCounter` row in
§3 makes a second selection of the same person a no-op. Twenty-four cheap runs a day, each
touching one band of longitudes.

The failure mode is the real argument for it. A once-daily job that fails has taken out
everybody for a day. **An hourly job that fails has taken out one band of longitudes for one
hour**, and the next hour's run, with a widened window, picks them up — provided the widened
window stays inside quiet hours, which the drop rule handles. A missed run costs an hour
instead of a day, and for a product whose content is *"here is what today contains"*, that
distinction is the whole difference between late and wrong.

The other two timers stay daily; nothing about a renewal notice or a retention purge cares
what hour it is.

> **`Profile.timezone` is the wrong clock and this file previously said otherwise.** It is
> derived from the *birthplace*. Somebody born in Lisbon and living in Toronto would get an
> 08:00 Lisbon push at 03:00 their time. It is third on THE-DAILY.md's ladder as a fallback,
> not a default, and the device-reported zone is first. The contract that makes that possible
> is the `X-Alma-Timezone` header in §3 below.

### 8.5 What it costs to operate

| Item | Cost |
| --- | --- |
| APNs | $0. Apple charges nothing to send. |
| FCM | $0. Google charges nothing to send. |
| systemd timers | $0. They run on the host already paying for the API. |
| Dead-man's-switch monitoring | $0 on Healthchecks.io's free tier; self-hostable. |
| Compute | One `transits.scan` per subscriber per day. The module is vectorised — a whole year of transits is a handful of array evaluations — so a few thousand subscribers is minutes, not hours, on one core. |
| Generation | $0.32 per subscriber per month at 12 dailies × $0.027, against $8.99 net and a $3.50 ceiling (§6). |
| **Total marginal operating cost** | **effectively zero**, which is the correct answer and is also why the only thing worth spending care on is *not sending the wrong ones*. |

---

## 9 · What the owner has to do, in order

`[OWNER ONLY]` marks the steps nobody else can do — they need an account, a password, or a
decision that is not a code decision.

**Before anything else**

1. `[OWNER ONLY]` **Decide the product-id prefix** — `alma.` or `ai.pazl.alma.`
   (`STATUS.md §4②`). The bundle identifier is `apns-topic` and the Android package name is
   what `google-services.json` is pinned to. Nothing in §1 or §2 can be created under a name
   that is about to change.
2. `[OWNER ONLY]` **Stand up the domain** (`STATUS.md §4①`). Independent of push, but the
   backend has nowhere to run until it resolves, and the backend is what sends.
3. `[OWNER ONLY]` **Choose the host, and answer what it logs** (`DATA-INVENTORY.md §1.17`).
   This is now also the question of where the `.p8` and the FCM service-account JSON live.

**Apple**

4. `[OWNER ONLY]` `developer.apple.com` → Certificates, Identifiers & Profiles → **Identifiers**
   → the App ID → enable **Push Notifications**.
5. `[OWNER ONLY]` → **Keys** → new key with **APNs** ticked, **team-scoped**, **Production**.
   Download the `.p8` — **Apple serves it once**. Repeat for **Sandbox**. Record both **Key
   IDs** and the **Team ID**.
6. `[OWNER ONLY]` Put the two keys into the host's secret store as `ALMA_APNS_KEY_P8` /
   `ALMA_APNS_KEY_ID` / `ALMA_APNS_TEAM_ID` / `ALMA_APNS_TOPIC` / `ALMA_APNS_ENVIRONMENT`. Add
   `*.p8` to `.gitignore` before the file exists.

**Google**

7. `[OWNER ONLY]` Firebase console → create a project → add an **Android app** under the
   package name → download **`google-services.json`** into `mobile/android/app/`.
8. `[OWNER ONLY]` Firebase console → Project settings → **Service accounts** → **Generate new
   private key**. Store as `ALMA_FCM_SERVICE_ACCOUNT_JSON`. **Do not reuse the Play Developer
   API service account** that `billing/googleplay.py` already holds (§2.2).

**Decisions only the owner makes**

9. `[OWNER ONLY]` **Confirm subscribers-only** (§4), and decide whether a free user who has
   saved a birth gets anything.
10. `[OWNER ONLY]` **Sign off the cadence in `THE-DAILY.md §4.1`**, restated in §6.1: weight
    floor 0.35 plus novelty, 3-day minimum gap, 2/week and 10/month caps, 08:00 local, hard
    quiet hours. "Not annoying" is his requirement, these are the numbers that implement it,
    and they were measured rather than guessed — but they should still be his numbers.
11. `[OWNER ONLY]` **Confirm the no-promotional-push rule** (§1.9(3)), because it is a
    commitment that goes on the privacy page, it is expensive to walk back, and under
    provisional authorization on iOS there is no consent basis for a promotional push at all
    (§5.4).

**Paperwork, after the code and before submission**

12. `[OWNER ONLY]` Update **App Privacy** in App Store Connect from the amended
    `APP-PRIVACY.md` (§7.2).
13. `[OWNER ONLY]` Update **Data safety** in Play Console from the amended `DATA-SAFETY.md`
    (§7.3).
14. `[OWNER ONLY]` Add a line about the daily to all twelve store listings (`LISTING.md`) —
    Play requires a permission to be necessary for functionality *as promoted in the listing*
    (§2.5).

**Operations**

15. `[OWNER ONLY]` Install the three systemd timers (§8.3) and enable them. `systemctl
    list-timers` must show all three, including the two that have been documented and unrun
    since `renewals.py` was written.
16. `[OWNER ONLY]` Create the three dead-man's-switch checks and confirm an alert arrives when
    a job is deliberately stopped. **Test the alarm, not just the job** — an untested alarm is
    the same as no alarm, with more confidence.

**Verification, which anyone can do once the above exists**

17. Register a device from a **development** build; confirm the token row carries
    `environment = sandbox`.
18. Paste that token into Apple's **Push Notifications Console → Device Token Validator** and
    confirm it reports sandbox for the bundle id (§1.8).
19. Send one, deliberately, to the **production** host and confirm `400 BadDeviceToken` — the
    mismatch must be *reproducible on demand*, because that is what makes it recognisable when
    it happens by accident.
20. Repeat 17–19 with a **TestFlight** build, which will report **production** (§1.8). This is
    the step that catches the classic failure before a beta tester does.
21. Delete the app, wait, send, and confirm the 410 handling in §1.7 deletes the row — and that
    reinstalling before the send *does not*.

---

## 10 · Open questions this document cannot close

1. **Are Apple and Google processors or controllers** for a token they issued? §7.1. It is the
   same question the Anthropic DPA already has open in `DATA-INVENTORY.md §6`, and Play's
   "Shared" answer turns on it.
2. **Does a free user who has saved a birth get anything?** §4.
3. **Which of the two send paths is written first.** They are independent — the Android one
   needs a Firebase project and a Data safety amendment, the iOS one needs a `.p8` and nothing
   else. Doing iOS first gets the harder half of the *product* question (provisional
   authorization, §5.4) answered on the platform where the transport is simpler.
4. **What the host retains**, which is now also the question of where the `.p8` and the FCM
   service-account JSON live. `DATA-INVENTORY.md §1.17`, `STATUS.md §4`.

Two things that were open in an earlier draft of this file and are **closed** by
`THE-DAILY.md`, recorded so nobody reopens them: the weight floor (0.35, measured over 24
charts, §4.2 there) and the delivery clock (device timezone first, `Profile.timezone` only as a
fallback, §3.3 there — see the correction at the end of §8.4).

---

## Sources

**In this repository**, and authoritative over this file where they overlap:

- `docs/THE-DAILY.md` — what is sent and how often, measured. §3 (timing), §4 (cadence), §5
  (what the person controls), §6 (the recommendation).
- `backend/README.md` — "The two things that have to be scheduled", and the sentence this
  file's §8 is built around.
- `mobile/store/DATA-INVENTORY.md` — the file every store disclosure is derived from; §7 above
  is a list of amendments to it.
- `backend/alma/engine/transits.py` — `Hit`, `_weight`, `active`, `describe`.
- `backend/alma/billing/renewals.py` — the idempotency pattern §3 and §6.2 reuse.

**Fetched from Apple and Google on 7 August 2026:**

- [Sending notification requests to APNs](https://developer.apple.com/documentation/usernotifications/sending-notification-requests-to-apns) — endpoints, ports, `:path`, every header and its values
- [Handling notification responses from APNs](https://developer.apple.com/documentation/usernotifications/handling-notification-responses-from-apns) — status codes, every reason string, the 410 `timestamp`
- [Establishing a token-based connection to APNs](https://developer.apple.com/documentation/usernotifications/establishing-a-token-based-connection-to-apns) — the `.p8`, the JWT, the 20/60-minute refresh window, key scopes and limits
- [Generating a remote notification](https://developer.apple.com/documentation/usernotifications/generating-a-remote-notification) — the `aps` dictionary, `loc-key`/`loc-args`, the 4 KB limit
- [Registering your app with APNs](https://developer.apple.com/documentation/usernotifications/registering-your-app-with-apns) — token instability, "never cache device tokens", `aps-environment`
- [Asking permission to use notifications](https://developer.apple.com/documentation/usernotifications/asking-permission-to-use-notifications) — one prompt only, provisional authorization, ask in context
- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) — 4.5.4, 5.1.1(ii), 5.1.2(i)
- [Push Notifications Console](https://developer.apple.com/notifications/push-notifications-console) — the Device Token Validator and delivery logs
- [Send a message using FCM HTTP v1](https://firebase.google.com/docs/cloud-messaging/send/v1-api) — endpoint, OAuth scope, message shape
- [FCM error codes](https://firebase.google.com/docs/cloud-messaging/error-codes) — every code, status and remedy
- [Best practices for FCM registration management](https://firebase.google.com/docs/cloud-messaging/manage-tokens) — the 270-day expiry, the 30-day sweep, monthly refresh
- [Prepare for Google Play's data disclosure requirements](https://firebase.google.com/docs/android/play-data-disclosure) — what Cloud Messaging and Firebase Installations collect
- [Manage Firebase installations](https://firebase.google.com/docs/projects/manage-installations) — FID lifetime, rotation, the 180-day deletion
- [Notification runtime permission](https://developer.android.com/develop/ui/views/notifications/notification-permission) — `POST_NOTIFICATIONS`, install vs upgrade, one-shot denial
- [Google Play — Data safety section](https://support.google.com/googleplay/android-developer/answer/10787469) — categories, purposes, security practices
- [Google Play — User Data policy](https://support.google.com/googleplay/android-developer/answer/10144311) — prominent disclosure, privacy policy, purpose limitation
- [Google Play — Ads policy](https://support.google.com/googleplay/android-developer/answer/9857753) — ads inside the app only

**Secondary, and graded**, for the one mechanism Apple's reference does not spell out — the
provisional→explicit upgrade path in §5.4. Both are practitioner write-ups against Apple's API,
not Apple documentation; the API behaviour they describe (`.provisional` status, later
`requestAuthorization` without `.provisional` showing the prompt) is consistent between them
and with Apple's own statement that the system prompts only when the person *"has not yet made
a choice"*. **Verify on a device before relying on it**, and note the iOS 16+ defect they both
report:

- [Use Your Loaf — Provisional Authorization of User Notifications](https://useyourloaf.com/blog/provisional-authorization-of-user-notificatons/)
- [Nil Coalescing — Sending trial notifications with provisional authorization on iOS](https://nilcoalescing.com/blog/TrialNotificationsWithProvisionalAuthorizationOnIOS/)
