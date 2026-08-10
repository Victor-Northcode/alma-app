# Alma

Eight ways of reading a birth chart, and one voice that will not make anything up.

Alma computes eight independent systems — a natal chart of sixteen chapters, numerology,
the tarot birth card, transits, the solar return, compatibility, astrocartography, and a
cross-synthesis that shows where three of them agree about a person and where they do not.
Positions come from NASA's **JPL DE440s** ephemeris through Skyfield: a real integration of
the solar system, not a table of sun signs. Forty-one chapters in all, in **seven languages** — en, es, de, it, fr, pt-BR, ru.

What makes it different from the category is a rule the code enforces rather than a promise
the marketing makes. Every paragraph names the placement it was read from, and
`backend/alma/ai/validator.py` **refuses to publish** one that cites a placement absent from
the chart — the reading is regenerated, and after three attempts it is refused rather than
degraded. Asked whether to take a job abroad, Alma answers *"nothing in the chart tells you
to go or to stay — that choice is yours to make."* It describes; it does not predict.

**Every calculation is free, forever.** A locked natal chart still returns its houses, its
aspects with their orbs and all seventy-eight factors. What is sold is the writing.

---

## What is here

| | |
|---|---|
| `backend/` | FastAPI, Python 3.13. The engine, the writing layer, billing, the API. **1479 tests.** |
| `src/` | Next.js storefront: the free reading, six legal pages, six languages. Sells nothing. |
| `mobile/ios/` | SwiftUI. Payment through StoreKit. **The reference the Flutter port is measured against.** |
| `mobile/android/` | Jetpack Compose. Payment through Play Billing. |
| `mobile/flutter/alma/` | The port, in progress. One codebase for both phones — see [`docs/FLUTTER-PORT.md`](docs/FLUTTER-PORT.md). |
| `mobile/store/` | The completed App Store and Play submissions — twelve listings, privacy answers, review notes. |
| `docs/` | How to deploy it, how to release it, and what is not finished. |

Payment is Apple and Google in-app purchase. Two card processors sit behind a provider seam
as a fallback and sell nothing today — the seam exists because Paddle's acceptable-use policy
prohibits this category outright, which is the fact that decided the whole payment
architecture.

## Prove it works

```bash
cd backend && .venv/bin/python -m pytest -q          # 1584 tests
cd backend && .venv/bin/python tools/license_gate.py # no GPL/AGPL/LGPL, direct or transitive
npx tsc --noEmit && node scripts/check-locales.mjs && npx vitest run
rm -rf .next-verify && npm run verify
cd mobile/android && ./gradlew :app:assembleDebug    # read mobile/TOOLCHAIN.md first
```

The licence gate is not ceremony. Swiss Ephemeris, pyswisseph, libephemeris and Kerykeion are
banned from this repository because AGPL §13 would compel publishing the whole service, and
that single constraint shaped the entire astronomy stack.

## Where to go next

- **The Flutter port** → [`docs/FLUTTER-PORT.md`](docs/FLUTTER-PORT.md) — where it stands, every
  decision taken along the way, and what is honestly missing. The two native apps still work
  and are still the only thing shippable until the port catches up.
- **Releasing the apps** → [`mobile/RELEASE.md`](mobile/RELEASE.md), then
  [`mobile/store/README.md`](mobile/store/README.md)
- **Building them** → [`mobile/TOOLCHAIN.md`](mobile/TOOLCHAIN.md) — every line in it was run
  on the machine it describes, and two of that machine's defaults are wrong for Android.
- **Taking it over** → [`docs/HANDOVER.md`](docs/HANDOVER.md) — read this first if somebody
  has just handed you this repository. It lists what only the owner can supply, every stub
  waiting to be filled, and what is honestly not finished.
- **The daily and its notifications** → [`docs/THE-DAILY.md`](docs/THE-DAILY.md) and
  [`docs/PUSH.md`](docs/PUSH.md)

**`docs/DEPLOYMENT.md` and `docs/ARCHITECTURE.md` were linked here and have never existed.**
A link to a document nobody wrote is worse than no link: it costs the next reader the time
it takes to discover the absence, and it makes the rest of this list less believable. The
deployment half is genuinely missing and is worth writing the day there is a server to
deploy to; the architecture half is, for now, the module docstrings, which are unusually
long on purpose.

## The house rules

Four, and they are the reason the code reads the way it does.

**Nothing is shown that was not calculated.** Invented reviews, fabricated counts, a
pre-filled birth date, a claim that eight systems agree where three do — every one of those
was found in this repository and removed. Apple's Guideline 4.3(b) turns on exactly this
distinction, and so does whether anybody believes the product.

**Correctness is asserted against definitions.** There is no oracle to compare against, so
Placidus is checked by trisecting the semi-arc, the lunar node by finding where the Moon's
latitude crosses zero, and astrocartography against Skyfield's own independent topocentric
machinery. Two real reference-frame bugs were caught that way.

**A comment explains why, and what was rejected.** The code is unusually commented on
purpose: most of what looks like a small choice here was argued over, and several were bug
fixes whose reasoning is the only thing stopping the bug from coming back.

**Seven languages or none.** Every user-facing string exists in en, es, de, it, fr, pt-BR
and ru. The web dictionaries are typed against English so a missing key is a build error;
`check-locales.mjs` and `tests/test_locales.py` fail the build rather than shipping an
English sentence to a Brazilian — and the Russian prose is additionally gated at generation
time: no glyph notation, no Latin words, no grammatical gender pinned on the reader.

## Who writes what

| Surface | Model | Cadence |
|---|---|---|
| Paid chapters (41) | Opus 5 (`ALMA_MODEL_STRONG`) | written once, kept forever |
| Free sample chapters, natal spheres, the day text, the daily | Sonnet 5 (`ALMA_MODEL_MID`) | once per chart / per day |
| Chat: the 1 welcome question | Sonnet 5 | the shop window |
| Chat: 5 questions with a one-time door | Opus 5 | the deeper voice |
| Chat: 40/month on the plan | Sonnet 5 | subscription economics |

The cheap tier is deliberately absent — it undersold the product and was removed. Models are
set in `backend/.env`; ceilings scale with the writing system (Cyrillic costs roughly double
per word and the budgets know it).
