# Alma — backend

Eight systems of self-knowledge, calculated rather than guessed, and written
about only from what was calculated.

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env.local          # then fill in the keys you have
.venv/bin/python -m uvicorn alma.api.app:app --reload --port 8000
```

`GET /ready` lists, by name, everything still missing before real money can
change hands. Nothing else needs to be discovered by trying it.

## What is where

```
alma/
  engine/      the arithmetic — no I/O, no database, no network
  calc/        CalcResult: the one shape everything above the engine reads
  geo.py       places and historical timezones, offline
  db/          models and sessions
  auth/        guest-first accounts, tokens, entitlements
  ai/          the writing layer, and the validator that keeps it honest
  billing/     prices, the processor seam, and one adapter per processor
  api/         HTTP
tools/         the licence gate and the data builders
```

The dependency arrow only ever points down. Nothing above `calc/` imports
`engine/` directly, which is what makes "the AI can only cite facts the
engine produced" a checkable claim rather than an intention.

## The three rules the code is built around

**Nothing is asserted that was not calculated.** Every generated paragraph
carries the factor strings it was read from, and `ai/validator.py` checks
them against the CalcResult character by character. An invented factor
triggers a regeneration with the offending string quoted back; three failures
refuse the reading. A hallucinated placement reads exactly as confidently as
a real one, and there is no way for a reader to tell them apart — so the
check has to be mechanical.

**Not knowing is a state, not a missing value.** A birth time is either known
or it is not. Every system that depends on the horizon checks and refuses
rather than assuming noon, because an assumed noon does not produce a weaker
answer — it produces a different person's chart, with the same confidence.
The same applies to Chiron outside 1900–2100, to Placidus above the polar
circle, and to a daylight-saving overlap, which is answered with a question
and two candidate instants rather than a coin flip.

**Correctness is asserted against definitions.** Swiss Ephemeris is banned by
the specification, so there is no oracle to diff against — which turned out
to be an advantage. Placidus is verified by recovering the trisection of the
semi-arc; the lunar node by checking it equals the Moon's longitude at the
latitude zero-crossing; the astrocartography lines by asking Skyfield's own
topocentric machinery for the hour angle and altitude at the point the line
claims. A comparison-based test reports "differs by 68 arcseconds", which is
easy to wave away as a difference of method. A definition-based one does not
leave that door open — and both of the real frame bugs in this engine were
found that way after being waved away exactly once.

## The three things that have to be scheduled

```cron
# Every hour, on the hour, and the hour is the point: 08:00 happens twenty-six
# times around the world, so a once-a-day job can only be 08:00 somewhere. Each
# run selects the people whose local morning has just arrived. It is idempotent
# per person per local day — the row is claimed before the send — so a run that
# happens twice sends once, and a run that is missed costs one band of
# longitudes one hour rather than everybody a day.
0 * * * *   cd /srv/alma/backend && .venv/bin/python -m alma.notify.daily

# Once a day. The window is a range — renewals between two and four days out —
# so a missed run still catches the notice, but a run that never happens sends
# nothing at all, for ever, and looks exactly like success.
17 9 * * *  cd /srv/alma/backend && .venv/bin/python -m alma.billing.renewals

# Also once a day, and for the same reason it is written down here rather than
# left to somebody's memory: the privacy page tells a reader that the step
# labels and the browser id beside them are deleted after 180 days, and this
# command is the whole of what makes that true.
41 3 * * *  cd /srv/alma/backend && .venv/bin/python -m alma.funnel --purge
```

The second one is `alma/funnel.py`. It deletes every funnel row past the
retention `src/lib/legal.ts` prints on the privacy page — a vitest fails if
those two numbers ever disagree — and it deletes the anonymous ids nothing
references any more. It is idempotent and safe to run twice: it deletes by age,
so a second run in the same day finds nothing new.

It deletes the whole window rather than only the rows that never became an
account, which is worth knowing before somebody "optimises" it: keeping the
purchases and dropping the visitors above them would leave every historical
conversion rate divided by a denominator that had been quietly shrunk.

`alma/billing/renewals.py` sends the letter that goes out three days before a
subscription is charged. **Nothing schedules it.** It is a `__main__`, and until
this section existed an operator could deploy the entire product without ever
running it — in which case the promise printed on the paywall, in the FAQ, on
the subscription-terms page and beside the pay button silently sends nothing,
and the first person to find out is a customer looking at a charge they were
told they would be warned about.

It is idempotent: one notice per plan per renewal date, recorded only after the
mail provider accepted it, so running it twice in a day sends nothing twice and
a failed send is retried tomorrow rather than marked done.

`alma/notify/daily.py` is the third, and it is the one that **refuses to run**
rather than running quietly. Without a push credential — the APNs four or the
FCM two, listed in `config.py` — and without `alma/daily/` to ask what today
contains, it raises at the first line instead of walking every subscriber and
logging a clean zero. That refusal is deliberate: a push system that appears to
work and sends nothing is the worst failure this feature has, because every
number downstream looks healthy and the first person to find out is a
subscriber wondering what they are paying for.

It also sweeps device tokens nobody has re-registered in ninety days, on the
same run, so the retention rule is a thing that happens rather than a thing
somebody remembers.

**Wire all three at once.** Two of them have been written, documented here and
never run; the daily makes three, and a renewal notice a day late is survivable
where a daily a day late is a lie about what day it is. `docs/PUSH.md §8`
recommends systemd timers with a dead-man's switch over crontab, for one
reason worth repeating: `systemctl list-timers` prints the last and next run of
every job and cron's failure notification is mail to a mailbox nobody reads.

Two other commands exist and are not scheduled, deliberately:

```bash
.venv/bin/python -m alma.funnel --days 30            # the conversion report
.venv/bin/python -m alma.billing.withdrawal sub_…    # end a plan withdrawn from
```

The second is the revocation half of an Art. 14(3) withdrawal from the annual —
the refund itself is issued in the processor's dashboard, and this closes the
plan. It prints the unused part of the period to refund, and asks before doing
anything. It is a command rather than a route because there is no operator
credential in `config.py` and an unauthenticated endpoint that ends somebody's
paid access is a button anybody could press.

## Licences

`tools/license_gate.py` runs in CI and fails the build on any GPL, AGPL or
LGPL dependency, direct or transitive, including anything it cannot classify.
The engine is Skyfield + jplephem (MIT), pyerfa (BSD-3) and NASA JPL kernels
(public data). Swiss Ephemeris, pyswisseph, libephemeris and Kerykeion are
banned by name — AGPL §13 would oblige us to publish the whole service.

GeoNames data is CC BY 4.0; the attribution is in `data/ATTRIBUTION.md`. That
is a licence on data rather than on our source, and the gate does not see it,
which is why it is written down here too.

## Verifying

```bash
.venv/bin/python -m pytest -q          # 583 tests
.venv/bin/python tools/license_gate.py # exit 1 on copyleft, 2 on unknown
```

Three of those tests are worth knowing about by name, because they are what
stops the product quietly becoming a horoscope generator:

- `test_two_hours_of_birth_time_rewrites_the_house_chapters` — the inputs to
  the house-derived chapters must differ by at least 40% when the birth time
  moves two hours.
- `test_a_different_birth_date_rewrites_almost_everything` — at least 70% of
  the factors differ between two unrelated births.
- `test_an_invented_factor_never_reaches_the_reader` — the full generate →
  reject → regenerate loop, driven by a scripted model that invents.

## Rebuilding the bundled data

Neither is needed for development; both are committed.

```bash
python tools/build_places.py --source /path/to/geonames   # data/places.sqlite
```

The Chiron table is sampled from JPL Horizons because the SPK that Horizons
emits for small bodies is data type 21, which neither Skyfield nor jplephem
can read. `tests/test_chiron.py` pins it against Horizons' own apparent
positions and separately proves the sampling grid is far finer than it needs
to be.
