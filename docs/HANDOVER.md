# Handover

Read this before anything else if this repository has just been handed to you.

Three sections: **what only the owner can supply**, **every stub waiting to be filled**, and
**what is honestly not finished**. The third one is not softened. A handover that hides a gap
costs more than one with a hole in it, because the hole gets found in week one and the trust
does not come back.

Entity: **Pazl LLC**. Both developer accounts exist — Apple Developer and Google Play Console.

---

## 1 · What only the owner can supply

Nothing else in this document can happen until the first two are done.

### ① The domain does not exist

```
alma.pazl.ai   NXDOMAIN
api.pazl.ai    NXDOMAIN
pazl.ai        95.81.101.52   ← only the apex answers
```

Verified repeatedly on 7 August 2026. Both names are **compiled into the shipped mobile
builds** — `alma.pazl.ai` is the deep-link host in the Android manifest and the site constant
in Settings; `api.pazl.ai` is the release API host. Every legal URL in all twelve store
descriptions points at the first.

**Apple fetches the privacy-policy URL during review and rejects on a dead link before a
human opens the build.** This is not launch work; it is work that precedes everything.

Three pages must answer once the host is up: `/privacy`, `/support` (a required App Store
Connect field) and `/delete-account` (a Play Console field that is validated — a submission
will not be accepted without a reachable resource). The last two are built and return 200
locally.

### ② The product-id prefix — the one irreversible decision here

The binaries ask StoreKit and Play Billing for `alma.natal`, `alma.archive`, `alma.monthly`
and the rest. `mobile/store/PRODUCTS.md` §2 recommends `ai.pazl.alma.` and hands you the
paste-ready set.

Either answer is fine. **What is not fine is typing one into a console while the binary asks
for the other** — `Product.products(for:)` returns an empty set, the paywall renders with no
rows, and the build comes back as Guideline 2.1, *"we were unable to locate the in-app
purchases"*. Neither store lets a product id be changed or reused, so the only recovery is a
second set of products plus a migration for everybody who already bought.

Decide, then land it in all five places in one commit: `backend/alma/config.py`,
`mobile/ios/.../LadderKey.swift`, `mobile/android/.../StoreProducts.kt`,
`mobile/ios/Alma.storekit`, and the `processor_ids` pins in `backend/alma/billing/catalogue.py`.

### ③ Everything else, in the order it is needed

| | What | Where it goes |
|---|---|---|
| Anthropic key | without it no chapter can be written | `backend/.env` → `ANTHROPIC_API_KEY` |
| Resend key | without it no email leaves — sign-in links included | `RESEND_API_KEY` |
| Apple signing | Team ID; archiving fails without it | `mobile/RELEASE.md` → "the two blanks" |
| Android keystore | four values; release builds refuse without them | `mobile/RELEASE.md` |
| APNs key (.p8) | push, iOS | four vars — see below |
| FCM service account | push, Android | two vars — see below |
| A cron | three jobs exist; nothing runs any of them | see below |
| Play service account | server-side purchase verification | `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` |
| Small Business Program | 15% instead of 30% — enrol before the first sale | App Store Connect |
| Imprint blanks | two: registered address, EU Art. 27 representative | `src/app/(legal)/imprint/page.tsx` |

The imprint blanks render as visible `<Blank>` markers on the page rather than as plausible
invented text. That is deliberate: a made-up address in a legal notice is worse than an
obvious gap.

There used to be six of them. Four were removed after the owner objected to publishing a tax
number and a private name, and the objection was right on the law as well as on the instinct.
*Represented by* and *responsible for content* come from German DDG §5 and MStV §18, which bind
providers **established in Germany**; a Wyoming LLC is not one, and naming a private individual
to satisfy a statute that does not reach us is a disclosure bought with nothing. *VAT / tax id*
went because there is no number: in-app purchase makes Apple and Google the deemed supplier
under Art. 9a of Implementing Regulation 282/2011, they remit the tax, and the operator holds no
EU VAT registration — the page now says so outright instead of leaving a gap that read as
withholding. *Registration number* went because the trade-register duty is likewise for
EU-established providers, and Wyoming's filing id is already public record.

**The Art. 27 representative was kept, and it is not the same kind of row.** A controller
outside the Union that offers services to people inside it must appoint one (Art. 27) and
publish who it is (Art. 13(1)(a)); the Art. 27(2) exemption covers occasional processing, and
birth data plus conversations from EU users are not occasional. It is a service you buy, so the
name that appears is a company's, not anyone's own.

One thing worth knowing before filling the address: **Apple and Google publish it themselves.**
Both stores require DSA trader details from EU-facing developers and show name, address, phone
and email on the public listing. So the address is public whatever this page does — which means
the question is not whether to show it but *which* address is on file. If the LLC's registered
address is a home address, change it at the registered agent before submitting to either store.
That is the disclosure that actually costs something, and it is not one a website can undo.

#### The three the daily needs

Everything about the daily is built — selection, writing, validation, storage, both cost
ceilings, six languages, the hourly job, both vendors, both clients. **Nothing has ever been
sent.** These are the reasons.

```
ALMA_APNS_KEY_P8       the .p8 contents, or a path to the file
ALMA_APNS_KEY_ID       the 10-character Key ID
ALMA_APNS_TEAM_ID      the 10-character Team ID
ALMA_APNS_TOPIC        the bundle identifier, exactly

ALMA_FCM_SERVICE_ACCOUNT_JSON   the JSON, or a path to it
ALMA_FCM_PROJECT_ID             the Firebase project id
```

`ALMA_APNS_TOPIC` **is** the bundle identifier, so it waits on ②, and the App ID needs the
Push Notifications capability enabled — `aps-environment` is already in `Alma.entitlements`
waiting for it, and a simulator build does not check it, so the gap is invisible until the
first device build.

The FCM half is not only a credential: Android has no push transport compiled in, because
adding `firebase-messaging` pins `google-services.json` to the package name ② has not chosen
*and* brings Firebase Installations with it, which falsifies two disclosures that currently
read clean. `PUSH.md §7` requires those rewrites **before** that release. iOS talks to Apple
directly and is unaffected. Either platform can go alone; the job names which are configured
and skips tokens on the other rather than failing them.

And the cron, which is the one nobody thinks of until a subscriber asks what they are paying
for:

```
0  *  * * *   .venv/bin/python -m alma.notify.daily      # hourly, and it must be
15 3  * * *   .venv/bin/python -m alma.billing.renewals
30 3  * * 0   .venv/bin/python -m alma.funnel --purge
```

08:00 happens twenty-six times around the world, so a once-a-day job can only be 08:00
somewhere. The daily job selects whoever's local morning has just arrived, is idempotent, and
carries a three-hour catch-up window — a missed run costs one band of longitudes one hour
instead of everybody a day. A renewal notice a day late is survivable; a daily a day late is
a lie about what day it is.

---

## 2 · Every stub, and how it behaves

The rule throughout: **a stub refuses loudly and names what is missing.** Nothing here
silently pretends to work, because a payment system that appears to work and takes no money,
or a push system that appears to work and sends nothing, is the worst available failure —
it is discovered by customers rather than by us.

| Stub | What happens today | To finish it |
|---|---|---|
| `processor_ids` — thirteen empty | Both adapters refuse by name at checkout | Fill from the store consoles after ① and ② |
| iOS production host | `xcodebuild install` **errors** with the setting to change; ordinary Release builds warn | Set it once the domain exists |
| Android signing | `:app:checkReleasePrerequisites` fails in 1s listing all four missing values | `mobile/RELEASE.md` |
| Paddle / Dodo credentials | Service refuses to boot half-configured | Only if you ever sell outside the stores |
| APNs / FCM | Refuses at boot rather than dropping notifications | Keys from the two accounts |
| Cron | **Nothing runs on a schedule at all.** `python -m alma.billing.renewals` is written and never called | `docs/DEPLOYMENT.md` |
| Postgres | Installed and **run**; SQLite is still the default for a laptop | Set `ALMA_DATABASE_URL` |

### The database is no longer a stub — it is a setting

SQLite is the default and it is right for a laptop. It is not right for a server, and this is
not theoretical: iOS opens Today with four parallel requests that each wrote `last_seen_at`,
and **two of the four returned "database is locked" on every cold launch** until the write was
made conditional and WAL was turned on. The comments in `backend/alma/db/session.py` and
`auth/accounts.py` say plainly that neither fix is a substitute — SQLite has one writer
whatever the journal mode.

This document previously said the Postgres path had never been run, and that was the most
dangerous line in it. It has now been run: `asyncpg` is installed, and the whole suite passes
against a real Postgres as well as against SQLite. Point `ALMA_DATABASE_URL` at the server and
run the suite yourself before you believe this paragraph — the command is in `docs/DEPLOYMENT.md`,
and a claim about somebody else's database is worth exactly what re-running it costs.

---

## 3 · What is not finished

Ordered by what I would care about.

**No purchase has ever completed, on either platform.** StoreKit ships no simulator slice on
the build machine and `simctl` ignores a scheme's StoreKit configuration, so everything past
the tap is verified by construction rather than by observation. Open `Alma.storekit` in Xcode
and buy each rung once before TestFlight.

**The legal documents inside the apps are English only.** So is the web's route group, for the
reason its own comment gives: machine-translating an indemnity clause is worse than not
translating it. Everything else in both apps is in six languages.

**The daily and its notifications are mid-flight.** Whatever state `git status` shows there is
the truth; this document was written while that work was running. The landing pass has since
landed and is verified.

**The landing needs a country header from the edge to quote the right currency.** The page
reads `CF-IPCountry` and falls back to dollars when it is absent — which is honest, and
indistinguishable from the bug it replaced, so it will not announce itself. Name the header as
a requirement in whatever sits in front of the app; `/ready` reports `edge_country`
(`asked` / `answered` / `seen`) and the service warns once on the first blind request, so the
fallback is visible rather than silent.

**Two workflows died mid-run today** and each left verified findings unapplied — one of them
for three hours. If something in this repository looks half-done, check
`mobile/store/APP-CHANGES-NEEDED.md` and `STATUS.md` before assuming it was a decision.

**Smaller, real:** the receipt's "manage your plan" button lands on an explanatory paragraph
rather than a control, because under in-app purchase the real route is the store's own account
page and the receipt does not carry which store; `POST /v1/billing/subscription/cancel` is
live with no caller, since nothing sells through the card processors; and the funnel has no
rung below `portrait_view` — deliberately, because the store links are empty and a stage that
cannot fire reads as a collapse in conversion rather than as a missing constant.

---

## 4 · The first hour

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
cp .env.example .env          # then fill ANTHROPIC_API_KEY and ALMA_JWT_SECRET
.venv/bin/python -m pytest -q # 1509 tests, no key needed — the suite is sealed from .env
.venv/bin/python -m uvicorn alma.api.app:app --port 8018

npm install && npm run dev    # http://localhost:3000
```

The test suite reads no `.env` on purpose. It used to, and the day a real key was added
**59 tests failed** — including the one asserting that a *missing* key produces an honest 503,
which had been passing because the key was absent rather than because the code was right. A
test that changes its answer when somebody edits an untracked file is not a test.

Then read [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) before changing anything in
`backend/alma/engine/` or `backend/alma/ai/`. Both carry decisions that look arbitrary and
are not.
