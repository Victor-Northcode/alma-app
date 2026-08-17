# The daily — what a day actually contains

**7 August 2026.** Every number below was measured on this machine today by running
`alma/engine/transits.py` and `alma/ai/cost.py` over real charts. Nothing is estimated from
a rule of thumb, and where a figure comes from outside the codebase it is cited and graded.
No product code was written. This file exists so that the build agents do not have to
re-decide any of it.

The scripts are kept, because a number nobody can re-run is an opinion with a decimal point:

| script | what it answers |
|---|---|
| `measure_daily.py` | how many days a year have an exact hit, an orb entry, or nothing |
| `measure_policy.py` | where the volume comes from, by body / natal point / aspect |
| `measure_share.py` | how long a contact lasts, and how shared a transit really is |
| `measure_cost.py` | one daily piece priced through `alma/ai/cost.py` |
| `measure_final.py`, `measure_valve.py` | the recommended selection rule, simulated |

They live in **`backend/tools/daily/`**, with a README of their own, and are not collected
by `testpaths`. They are kept rather than discarded because the headline figures in §1 and
§6 are exactly the sort of thing that drifts silently when `TRANSIT_ORBS`, `BODY_WEIGHT` or
`NATAL_WEIGHT` is next touched. The window is hard-coded to 2026-08-07 → 2027-08-07 and the
24-chart cohort is seeded, so a re-run is comparable to this document rather than to a
different year of sky.

---

## 0 · The one-paragraph answer

A real chart has something *technically* happening on 87–94% of days and something *worth
waking a phone for* on about 46 of them a year. Cost is not the constraint — the whole
feature is under 1% of net revenue at any cadence anybody would defend. The constraint is
the person's patience, and the outside evidence puts the safe band at **1–2 pushes per
week**. A weight-gated, event-driven rule lands the median subscriber at **0.88 pushes a
week** and the noisiest chart in a 24-chart cohort at **1.13** — inside the band, without a
cap having to do the work. So: **a pulled daily page that is always there, and a pushed
notification only when the sky earns it.**

---

## 1 · How much happens in a real chart

### 1.1 The charts

Six charts, chosen to vary the things that could plausibly change the answer — decade,
hemisphere, latitude, and whether there is a birth time at all.

| chart | born | place | lat | birth time | natal points transited |
|---|---|---|---|---|---|
| A | 1961-08-04 19:24 | Nairobi | −1.29 | yes | 15 |
| B | 1978-05-18 03:05 | Kraków | +50.06 | yes | 15 |
| C | 1990-11-02 14:40 | Buenos Aires | −34.60 | yes | 15 |
| D | 1996-02-29 08:15 | Seoul | +37.57 | yes | 15 |
| E | 2003-09-21 — | Auckland | −36.85 | **no** | **13** |
| F | 1985-12-12 23:50 | Reykjavík | +64.15 | yes | 15 |

The window is **2026-08-07 → 2027-08-07, 365 days**. Chart E loses two points because
without a birth time there is no Ascendant and no Midheaven — `natal.compute` refuses them
rather than assuming noon, and `transits.natal_points` therefore has nothing to offer.

### 1.2 Everything except the Moon — the module's own default

`transits.scan(..., include_moon=False)`.

| | A | B | C | D | E (no time) | F |
|---|---|---|---|---|---|---|
| contacts in the year | 479 | 485 | 470 | 467 | 408 | 479 |
| **days with an exact hit** | **272** | **276** | **259** | **274** | **238** | **270** |
| days with something entering orb | 272 | 277 | 259 | 274 | 238 | 265 |
| days with exact **or** entry | 339 | 338 | 330 | 343 | 319 | 341 |
| **days with neither** | **26** | **27** | **35** | **22** | **46** | **24** |
| longest run of silent days | 3 | 3 | 2 | 4 | 5 | 3 |
| longest run of consecutive event days | 56 | 63 | 37 | 68 | 35 | 51 |
| contacts in orb on an average day | 6.40 | 8.65 | 9.07 | 10.69 | 6.99 | 7.77 |
| …minimum / maximum on any day | 0 / 14 | 1 / 15 | 2 / 17 | 5 / 16 | 0 / 14 | 0 / 15 |

**The feared answer — "there are only 40 days a year with anything on them" — is wrong.**
An unfiltered chart has an exact aspect on **259–276 days a year**, and a day with literally
nothing happening is rare: 22–46 days out of 365, never more than five in a row.

Which means the problem is the opposite of the one the brief worried about. It is not
scarcity. It is that most of that volume is worthless.

### 1.3 Where the volume comes from

Mean over the six charts, one year:

| transiting body | contacts / yr | of which weight ≥ 0.30 | median days in orb |
|---|---|---|---|
| Mercury | 148.7 | 4.7 | 1.26 |
| Sun | 117.2 | 25.0 | 2.03 |
| Venus | 112.3 | 3.2 | 1.67 |
| Mars | 49.7 | 16.2 | 5.77 |
| Jupiter | 14.5 | 8.2 | 20.24 |
| Saturn | 8.7 | 6.0 | 29.58 |
| Chiron | 4.0 | 2.2 | 45.24 |
| Neptune | 3.7 | 2.7 | 86.18 |
| Uranus | 3.5 | 3.2 | 49.99 |
| Pluto | 2.5 | 2.2 | 70.93 |

**Mercury and Venus together are 55% of all contacts and 4% of the meaningful ones.** They
are what makes a chart look busy and what would make a daily feel like noise: Mercury's
median contact is live for **thirty hours**, which is not something anybody needs a plan
for. Neptune's median contact is live for **eighty-six days**, and the longest one measured
ran **190 days** — that is a season of somebody's life, and it is the kind of thing the
subscription is actually selling.

This is why the `BODY_WEIGHT × NATAL_WEIGHT × ASPECT_WEIGHT` product already in
`transits._weight` is the right filter and no new one is needed. It ranks by exactly the
distinction the table above makes.

### 1.4 Filtering by weight — the decisive table

Chart A, swept across weight floors. The other five agree to within a few days.

| weight floor | contacts | days with an exact hit | days with exact or entry | longest silence |
|---|---|---|---|---|
| 0.00 (everything) | 479 | 272 | 339 | 3 |
| 0.15 | 284 | 206 | 283 | 5 |
| 0.20 | 196 | 160 | 235 | 6 |
| **0.30** | **76** | **71** | **127** | **20** |
| 0.40 | 42 | 42 | 74 | 36 |
| 0.50 | 13 | 13 | 24 | 84 |

And across a wider cohort — 24 charts, birth years 1962–2006, eight cities across both
hemispheres, four of them without a birth time:

| | min | p25 | median | p75 | max | mean |
|---|---|---|---|---|---|---|
| exact-hit days at weight ≥ 0.30 | 38 | 64 | 68 | 73 | 82 | 65.8 |
| exact-hit days at weight ≥ 0.40 | 16 | — | 36 | — | 46 | 35.2 |

**Zero of the 24 charts had no weight ≥ 0.50 contact in the year.** Nobody's year is empty.
But at 0.50 the longest silence stretches to 84–150 days, which is a different failure: a
feature that fires four times a year is not what a subscription renews for.

The usable band is **0.30–0.40**, which is where the brief's "40 days a year" instinct
turns out to be roughly right after all — it was right about the *meaningful* count and
wrong about the raw one.

### 1.5 The Moon, measured so the decision is on the record

`transits.scan(..., bodies=("moon",))`, same window:

| | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| contacts in the year | 1603 | 1609 | 1606 | 1606 | 1392 | 1610 |
| days with an exact hit | 360 | 365 | 358 | 365 | 365 | 365 |
| days with neither | 3 | 0 | 6 | 0 | 0 | 0 |

**About 1,600 exact lunar contacts a year — 4.4 a day, on every day.** The median lunar
contact is in orb for well under a day. A daily built on the Moon would have something to
say every morning forever, which is precisely why it must not be: a system that always has
an answer is a system whose answers carry no information. `TRANSIT_ORBS` already comments
this and makes the Moon opt-in; the number above is the evidence for that comment.

**Decision: the Moon is excluded from the daily, in every form, permanently.** It may
appear as *context* inside a piece the outer planets earned ("with the Moon in your
seventh house tonight"), because that costs nothing and is true. It may never be the reason
a notification fires.

### 1.6 What this settles

- A **pull** surface — open the app, see today — is honest every single day. There are
  6.4–10.7 contacts in orb on an average day and only 0–65 days a year with nothing at
  weight ≥ 0.30 (chart E, the one without a birth time, is the worst at 65).
- A **push** every morning is dishonest. At the floor that makes a push worth reading there
  is something on ~127 days, and the gaps between them are real: up to 20 days at floor
  0.30, up to 36 at 0.40.
- Therefore the daily is **two products in one feature**: a page that is always there, and
  an interruption that is not. The rest of this document assumes that split.

---

## 2 · What it would cost

### 2.1 The measured inputs

| quantity | value | where from |
|---|---|---|
| one chapter, live | **$0.0270** — `claude-sonnet-5`, 1822 in / 1437 out | `STATUS.md:415` |
| one chat turn, live | **$0.0472** | `alma/config.py:274` |
| `voice.system_prompt(paid=True)` | 3,061 chars ≈ 765 tokens | measured today |
| whole-day brief (everything in orb + full natal factor list) | median 2,324 chars | measured today |
| one-event brief (the hit + the natal lines it touches) | median 167 chars | measured today |
| subscriber monthly ceiling | **$3.50** | `config.subscriber_month_budget` |
| already committed to a subscriber | 40 chat turns × $0.0472 = **$1.89** | `config.subscriber_questions_per_month` |
| **headroom** | **$1.61 / month** | |
| US net on $9.99 | $8.99 | the brief |
| EU net on $9.99 | $7.33 | the brief |

The two brief shapes matter more than they look. A whole-day piece has to carry the natal
factor list so the validator has something to check citations against, and that list alone
is ~2.3 kB. A single-event piece needs only the hit and the handful of natal lines it
touches — 167 characters at the median. **The input is 14× smaller, and the input is most
of the bill at these output lengths.**

### 2.2 One daily piece, priced

Priced with `cost.cost()` at the token shape a 90–140-word piece actually produces (scaled
from the one chapter that was measured live — the writer's JSON envelope repeats each cited
factor verbatim, so output tracks citation density more than word count):

| shape | model | tokens | cost |
|---|---|---|---|
| whole day (140 w) | `claude-haiku-4-5` | 2400 / 600 | $0.00540 |
| whole day (140 w) | **`claude-sonnet-5`** | 2400 / 600 | **$0.01620** |
| whole day (140 w) | `claude-opus-5` | 2400 / 600 | $0.02700 |
| one event (110 w) | `claude-haiku-4-5` | 1400 / 420 | $0.00350 |
| one event (110 w) | **`claude-sonnet-5`** | 1400 / 420 | **$0.01050** |
| one event (110 w) | `claude-opus-5` | 1400 / 420 | $0.01750 |

`cost.guard`'s worst case — the full `max_tokens` allowance spent — is $0.0152 (whole day)
and $0.0106 (one event) on Sonnet, both comfortably inside `full_report_budget` of $0.50 and
even inside `free_user_budget` of $0.05. **The per-call guard will never fire on a daily.**

> **Measured live, 7 August 2026, and the estimate above is low.** Fourteen real generations
> on `claude-sonnet-5`, read back out of the spend ledger rather than added up from what the
> calls claimed: **mean $0.0143, range $0.0128–$0.0175**. That is 1.36× the modelled $0.0105
> and 1.65× the "worst case" of $0.0106 — the row above was projected from a token estimate
> that turned out to be smaller than the real prompt, and the prompt has since grown by the
> geometry note and the moving body's position that §1.1 now requires.
>
> **Nothing about the argument changes and the number still matters.** $0.0175 is 2.9× under
> the $0.05 free-tier ceiling, and thirty a month is $0.43 against $8.99 net US revenue. What
> is lost is the *detector*: the reason for keeping the ceiling tight was that a prompt which
> quietly grew should stop being affordable long before the invoice notices, and a stated
> worst case that is routinely exceeded cannot do that job. Treat **$0.018** as the figure to
> watch, re-measure with `tools/daily/a_real_week.py`, and if it passes $0.025 go and find
> out what got longer.

### 2.3 Per subscriber per month, at every cadence

One-event shape on `claude-sonnet-5`, which is what §6 recommends:

| cadence | pieces/mo | cost/mo | % of $8.99 US net | % of $7.33 EU net | fits the $3.50 ceiling? |
|---|---|---|---|---|---|
| every day | 30 | $0.3150 | 3.5% | 4.3% | yes ($1.89 + $0.32 = $2.21) |
| 6× / week | 26 | $0.2730 | 3.0% | 3.7% | yes |
| every other day | 15 | $0.1575 | 1.8% | 2.1% | yes |
| 2× / week | 8.7 | $0.0914 | 1.0% | 1.2% | yes |
| **event-driven, ~3.8/mo** | **3.8** | **$0.0399** | **0.44%** | **0.54%** | yes |
| weekly | 4.3 | $0.0452 | 0.5% | 0.6% | yes |

And the fatter whole-day shape:

| cadence | pieces/mo | cost/mo | % US net | % EU net |
|---|---|---|---|---|
| every day | 30 | $0.4860 | 5.4% | 6.6% |
| every other day | 15 | $0.2430 | 2.7% | 3.3% |
| weekly | 4.3 | $0.0697 | 0.8% | 1.0% |

**Say it plainly: there is no cadence at which this stops being affordable.** Even the
worst case — a whole-day piece generated every single day on Sonnet, *plus* an event push,
*plus* all forty chat turns — is $1.89 + $0.49 + $0.04 = **$2.42 against a $3.50 ceiling**,
and 5.9% of the EU net. Only Opus at a daily whole-day piece ($0.81/mo) starts to feel like
a real line item, and even that fits.

This is the finding that should change how the feature is argued about. **Money is not the
reason to send fewer notifications. The person is.** Anyone who proposes a cadence in this
document should be made to defend it on §4's evidence, not on the bill.

### 2.4 The compute side, since somebody will ask

Measured on this machine, single core:

| operation | time |
|---|---|
| `natal.compute` | 35 ms |
| `transits.scan`, one week | 114 ms |
| `transits.scan`, five weeks | 246 ms |
| `transits.scan`, one year | 1,352 ms |

That is **2,663 chart-years per core-hour**. Re-scanning a full year for every subscriber
once a month costs 0.38 core-hours at 1,000 subscribers and 37.6 at 100,000. Negligible —
and it means the right design is to scan a *year* ahead once and store the hits, not to
scan a window every night. A year of hits for one chart is ~470 rows.

### 2.5 The cheaper idea, judged honestly

The brief's observation is correct and worth stating precisely: **the transiting body's
position is shared; the natal point it touches is not.** Transiting Saturn is at the same
degree for everybody on earth at the same instant. Two people only share an *event* if
they also share a natal degree, to within the orb.

I measured how much that is worth, over the 24-chart cohort (11,012 exact hits in the year):

| keyed on | distinct keys | reuse | keys used by more than one chart |
|---|---|---|---|
| (transiting, aspect, natal point, **exact day**) | 10,348 | **1.06×** | **593 — 5.7%** |
| (transiting, aspect, natal point) — the *kernel* | 570 | **19.32×** | 435 — 76.3% |

**Generating one piece per day per transit-event and serving it to everyone who has that
event today buys essentially nothing: 1.06× reuse.** Two unrelated people almost never have
Saturn perfecting to the same natal point on the same day, because their natal degrees
differ. This idea should be dropped.

**Generating one piece per *kernel* — per (transiting body, aspect, natal point) combination,
ignoring the date — buys 19.3×.** Each kernel is shared by 11.5 charts in a 24-chart cohort,
and the vocabulary is bounded: 10 transiting bodies × 16 natal points × 5 aspects = **800
combinations**, or 1,600 if retrograde is a separate voice. Writing all 800 in all six
languages once, on Sonnet, costs **$53.28 one-off** — $0.053 per subscriber at a thousand
subscribers, and nothing thereafter.

**But a kernel is not a daily piece, and pretending it is would be the generic-horoscope
failure with extra steps.** Here is the measurement that proves it: among the 335 kernels
shared by four or more charts in the cohort, the natal longitudes those charts bring to the
same kernel span a mean of **240°** and a median of **304°**. "Saturn square your Moon" is
one kernel; one person's Moon is at 3° Aries and another's at 27° Capricorn, their squares
perfect eleven months apart, and the sign, the house, the dispositor and the dates are all
different. Everything that makes the sentence *Alma's* rather than a horoscope's is in the
part the kernel does not contain.

So the honest verdict:

- **A kernel cache preserves**: the interpretive stance toward a combination — what a Saturn
  square to a natal Moon *means*, in Alma's voice, at Alma's length, in six languages.
  That is genuinely shared and genuinely reusable, and writing it once at Opus quality
  rather than 46 times a year at Sonnet quality is a straight upgrade.
- **A kernel cache does not preserve**: the degree, the sign, the house, the exact instant,
  the orb window, the retrograde status, the other contacts live at the same time, or the
  fact that this is the second of three passes. All of those are the citable facts
  `validator.py` exists to enforce, and none survive sharing.
- **Therefore**: if a kernel cache is built, it must be an *input to the prompt*, not the
  output served. It becomes another line in the brief — "the established reading of this
  combination is …" — and the model still writes this person's piece, with this person's
  degrees, through the same validator.

And the cost analysis in §2.3 says that upgrade is **optional**, because the per-piece cost
it would save is $0.0105. Recommend building the daily without it, and revisiting only if
quality — not cost — argues for it. A cache is a second source of truth about what a
transit means, and §2.3 says we are not being paid enough in savings to take on that
liability.

---

## 3 · When it should arrive

### 3.1 What we actually know

| fact | do we have it? | where |
|---|---|---|
| birth timezone (IANA) | **yes** | `Profile.timezone`, `String(64)`, `alma/db/models.py:179` |
| current device timezone | **no** | no client sends it; grep confirms |
| device locale | yes, indirectly | `Accept-Language` and the `alma.locale` cookie |
| coarse country | yes | `alma/region.py`, from edge headers, `Vary`-ed in `deps.py` |
| device push token | **no** | there is no notification code anywhere in this project |

**The birth timezone is not where the person is.** Chart E in §1.1 is a plausible customer:
born in Auckland, and no part of the system knows whether they still live there. Using
`Profile.timezone` as the delivery clock would send a "good morning" at 8pm to anyone who
emigrated — and emigration correlates with being interested in one's own chart more than it
correlates with nothing.

The coarse country from `region.py` is worse than it looks: it is right for Poland and
useless for the United States, Russia, Brazil, Canada and Australia — four of which are in
our six-language footprint.

### 3.2 What the clients can tell us, and what to ask for

Both native clients have the answer already and are simply not sending it:

- **iOS**: `TimeZone.current.identifier` → `"Europe/Warsaw"`. Updates automatically on
  travel; `NSSystemTimeZoneDidChangeNotification` fires when it changes.
- **Android**: `ZoneId.systemDefault().getId()`, same value, same semantics.
- **Web**: `Intl.DateTimeFormat().resolvedOptions().timeZone`, same value.

**Contract needed from a file another workflow owns** (`backend/alma/api/deps.py`) — do not
edit it; ask for this:

> A request header `X-Alma-Timezone`, an IANA zone identifier, validated with the existing
> `geo.is_known_timezone()`. Ignored silently when absent or unrecognised, exactly as the
> country header is. It is not a `Vary` concern for cached GETs because it should be
> persisted on the device row rather than read per-response.

Persisting it, not just reading it, is the point: the notification job runs at 03:00 on a
server and has no request to read a header from.

**Landed.** `deps.device_timezone` is that dependency, and `POST /v1/notifications/devices`
does the persisting. The ladder is climbed once, by `notify/rules.zone_for`, and the answer
is handed to `daily.candidates(…, zone=…)` — the selection package does not re-derive it,
because the two ladders rank the rungs differently and a person with an override would
otherwise have their day bracketed on one clock and their morning chosen on another.

### 3.3 The honest default and the fallback ladder

In order of preference, first one that resolves wins:

1. **The device timezone last reported by this installation.** Correct by construction,
   updates on travel, requires the header above.
2. **The timezone the person picked in settings.** Only appears if they have overridden it.
3. **The birth timezone** — `Profile.timezone`. Right for the majority who never moved,
   defensible, and already in the database.
4. **UTC+0 at 09:00**, if a profile somehow has no usable zone. This should be
   unreachable — `Profile.timezone` is `NOT NULL` — and if it is ever reached it is a bug
   worth logging rather than a case worth designing for.

The ladder is a fallback, not a merge. Never average two zones and never guess from
country.

### 3.4 What hour

The outside evidence on send time is real but weak and contradictory, and it is dominated
by retail and news apps whose economics are nothing like ours:

- CleverTap reports peak reaction between **06:00–08:00 and 22:00–midnight**
  ([MobiLoud's compilation](https://www.mobiloud.com/blog/push-notification-statistics)) —
  grade: **secondary source, no sample size published**.
- Other 2025–26 compilations put the click-through peak at **21:00–23:00** and the trough
  at 15:00 and 18:00 — grade: **vendor blog, methodology not disclosed, treat as folklore**.
- The one claim that recurs across sources and is mechanically plausible: **publishers who
  send at the same hour every day see higher CTR than those who vary it**, because the
  habit is the product.

**Recommendation: 08:00 in the person's own clock, fixed, not optimised.** The reasoning is
not the CTR data, which does not deserve that weight. It is that this product's content is
*"here is what today contains"*, and a piece about today that arrives at 22:00 is a piece
about a day the person has already had. The late-evening CTR peak is measuring retail
impulse, not usefulness, and optimising toward it would be optimising toward the metric
that made Co-Star's notifications famous and its reviews unkind.

Do not build send-time optimisation. A fixed hour is a habit; a moving hour is a surprise,
and surprise is the thing the owner asked twice to avoid.

### 3.5 Travel, and quiet hours

**Travel.** The device timezone changes; the next job run picks it up. This is correct for
almost everyone. It has one visible edge: a person who flies east across enough zones can
receive two dailies in about 30 hours, or none for 40. The fix is not a special case — it
is the *global* rule in §6 that no two notifications may fall within 3 days of each other,
which absorbs the double-send for free.

Somebody who travels constantly and lands wherever they land will get a notification at
08:00 wherever they are, which is the right answer and the only one we can defend.

**Quiet hours.** In the person's own clock — the same clock the delivery hour is in, from
the same ladder. **22:00–08:00, never sendable, no override, not even a user override.**

Concretely: the job computes each person's local send instant. If it lands inside quiet
hours because a timezone changed between scheduling and delivery, the notification is
**dropped, not deferred**. A daily is about a day; a daily that arrives at 02:00 to tell
you about yesterday is worse than one that never arrives. Silence is a supported state of
this feature (§1.6) and must be a supported state of the delivery layer too.

There is a compliance dimension worth one sentence: EU ePrivacy analysis treats push as
electronic direct marketing when it is promotional, and France enforces quiet hours at the
carrier level. Ours is transactional content the person subscribed to, not marketing, so
the analysis is not binding — but a hard 22:00–08:00 floor means the question never has to
be argued in front of a regulator or a store reviewer.

---

## 4 · How often is "not annoying"

The owner said it twice, so it needs a number. Here is the outside evidence, graded, because
this field is thick with numbers that get recycled for a decade without a source.

| finding | figure | grade |
|---|---|---|
| Users receiving **>6 push/week** from one brand were **3.4× more likely to uninstall within 30 days** than users receiving 1–2/week (Braze / Klaviyo) | **3.4×** | **B — the strongest figure here.** Behavioural, large-panel, from a vendor with the data to know. Still vendor-published, not peer-reviewed. |
| **46%** will opt out at 2–5 messages/week; **32%** at 6–10/week (Localytics) | 46% / 32% | **D — cite with caution.** Originally a Localytics survey, recycled through every push-marketing blog since. The inversion (fewer messages → *more* opt-out) is a survey artefact, not a behaviour, and it is the tell that this is a self-report. Directionally it says "2–5/week already hurts". |
| When notifications become excessive: **42%** change settings, **39%** disable entirely, **8%** uninstall, **9%** do nothing | — | **D — source not attributed** in any compilation I could reach. Directionally useful for one thing only: **the modal response to over-notification is to silence you, not to leave.** |
| Top two reasons for opting out, consistent across seven countries: **too frequent** and **not relevant/personalised** (Airship consumer survey) | — | **B.** Large multi-country survey; the finding is stable and matches every other source. |
| Braze's own staff survey: irrelevance **30%**, frequency **25%** | — | **F — do not cite.** n = 14 employees; Braze says in the article it is "clearly not statistically significant". Included here only so nobody re-finds it and mistakes it for evidence. |
| iOS opt-in **43.9%**, Android **91.1%**, overall **67.5%** | — | **C.** Widely repeated, plausible, methodology unpublished. Matters for forecasting reach, not for cadence. |
| Airship, 63M users across 1,500 apps: retention ~3× higher for users who got ≥1 push in their first 90 days | 3× | **B.** Large. Correlational — engaged users both receive and tolerate more. Do not read it as "send more". |

**What the stores say.** Apple's App Store Review Guideline 4.5.4:

> "Push Notifications must not be required for the app to function… should not be used for
> promotions or direct marketing purposes unless customers have explicitly opted in… and you
> provide a method in your app for a user to opt out from receiving such messages."

Neither store sets a frequency limit. Both prohibit spam and both require an in-app opt-out
for anything promotional. Guideline 3.1.2(a) is the one that actually bears on this feature:
an auto-renewable subscription "must provide ongoing value to the customer" — which is the
same argument the owner made, arriving from Apple's direction.

Google Play's 2025 policies are stricter on mechanism than on volume: no full-screen intents
to force interaction, foreground service types declared and justified. None of that binds a
plain remote push.

**The competitor evidence, which is the most instructive thing in this section.** Co-Star
began with a weekly brand-voice push and reviews loved it. Reviews now report **2–3 per
day**, including upsell prompts framed as horoscope previews, with copy like "Big energy
shift today, open to see". The reviews that describe the messages as *bullying* are the
predictable end of that road. This is the exact product adjacent to ours, running the exact
experiment, and the result is on the record: engagement-optimised astrology notifications
work in the short run and corrode the thing being sold.

### 4.1 The numbers to build to

**Hard cap: 2 per week, 10 per calendar month.** Above 2/week the Braze/Klaviyo uninstall
risk turns over (3.4× at >6/week, measured against a 1–2/week baseline), and every survey
agrees frequency is one of the two reasons people leave. An uninstall costs the whole
subscription, not the notification.

**Floor: zero.** There is no minimum. §1 measured 20–36 day gaps between things worth
saying at a defensible weight floor, and manufacturing something to fill them is the
horoscope failure. A month with nothing in it is a correct month.

The floor being zero is only tolerable because the *pull* surface is always there. That is
the trade: we can afford to say nothing precisely because opening the app always shows
something.

**What earns an interruption.** Both conditions:

1. `Hit.weight ≥ 0.35` — the product of `BODY_WEIGHT × NATAL_WEIGHT × ASPECT_WEIGHT` already
   in `transits._weight`. No new scoring. In practice this admits the outer planets and
   Mars to the personal points, and excludes essentially all of Mercury and Venus (§1.3).
2. **Something is true today that was not true yesterday** — either the aspect perfects
   today, or (for Jupiter and outward only, at weight ≥ 0.30) it enters orb today. A transit
   that has been sitting in orb for six weeks is not news, and Neptune's median window is
   86 days (§1.3) — pushing it more than twice would be pushing the same fact.

Both conditions matter. Weight alone would fire on a heavy slow transit every day for three
months; novelty alone would fire on Mercury forever.

### 4.2 The rule, simulated

24 charts, one year, the rule from §4.1 plus a minimum 3-day gap and a 10/month cap:

| pushes/year | | |
|---|---|---|
| median | **45.5** | **0.88 / week** |
| minimum chart | 28 | 0.54 / week |
| maximum chart | 59 | **1.13 / week** |
| longest silence, any chart | 60 days | |

Full distribution across the 24: 28, 32, 36, 40, 42, 42, 43, 43, 44, 45, 45, 45, 46, 47,
48, 49, 49, 50, 50, 51, 51, 53, 55, 59.

**Every chart in the cohort lands under 1.5 pushes a week without the cap ever binding.**
That is the result worth pausing on: the astronomy, filtered honestly, already produces a
cadence inside the safe band. The cap is a guard against a chart we have not seen, not a
mechanism the design depends on. A cap that does the work is a cap that is lying about the
content.

Alternatives, for the record:

| floor / slow-floor / gap / cap | median/yr | max/yr | max per week | worst silence |
|---|---|---|---|---|
| 0.30 / 0.30 / 3 / 10 | 57 | 73 | 1.40 | 60 d |
| **0.35 / 0.30 / 3 / 10** | **46** | **59** | **1.13** | **60 d** |
| 0.35 / 0.30 / 4 / 8 | 40 | 52 | 1.00 | 60 d |
| 0.40 / 0.35 / 4 / 8 | 37 | 45 | 0.87 | 60 d |
| 0.45 / 0.35 / 4 / 8 | 30 | 39 | 0.75 | 73 d |

### 4.3 The 60-day silence, and the one valve

A 60-day gap is the rule working correctly — that chart genuinely had nothing at that
weight — but two months of silence from a $9.99/month subscription reads as a broken
feature rather than an honest one.

The measured fix: if nothing has fired for **21 days**, admit the next candidate at weight
**≥ 0.20** instead of 0.35, once.

| variant | median/yr | max/yr | max/week | worst silence | valve fires (24 chart-years) |
|---|---|---|---|---|---|
| no valve | 46 | 59 | 1.13 | 60 d | — |
| 21 days → 0.25 | 47 | 59 | 1.13 | 43 d | 34 |
| **21 days → 0.20** | **47** | **59** | **1.13** | **33 d** | **42** |
| 14 days → 0.20 | 50 | 59 | 1.13 | 26 d | 111 |

**Take 21 days → 0.20.** It halves the worst silence, moves the median by one notification
a year, does not move the maximum at all, and fires 1.75 times per chart-year — rare enough
that it stays a valve rather than becoming the rule. The 14-day version fires 111 times and
is the beginning of manufacturing content.

The valve must be visibly different in the copy. A piece that only cleared 0.20 should read
as the quiet week it is — "nothing is pressing this week; the thing still moving is…" —
rather than as an announcement. If that cannot be written honestly, drop the valve and keep
the 60-day silence.

---

## 5 · What the person controls

**Everything here must be reachable in one tap from the notification itself and from
Settings. Anything that cannot be turned off in one tap is a defect and should fail review.**

### 5.1 The three states

One control, three positions, default **Occasionally** for a subscriber and **Off** for
everybody else.

| position | what it means, concretely | measured cadence |
|---|---|---|
| **Off** | No push, ever. The Today page still works. Nothing is withheld — this is a delivery preference, not a feature gate. | 0 |
| **Occasionally** *(default)* | The §4.1 rule: weight ≥ 0.35, novel today, ≥3 days apart, ≤10/month, 21-day valve at 0.20. | median 46/yr, max 59/yr |
| **Only what matters** | Weight ≥ 0.50, exact hits only, no valve, no orb-entry pushes. The Saturn returns and the Pluto squares and nothing else. | 7–13/yr (§1.4) |

Three positions and not five. Every additional position is a decision the person has no
basis for making, and a state the build agents have to test in six languages.

**Note the asymmetry with the free tier.** The Today page and its calculations are already
free per the 4.3(b) work (task #37). Notifications should follow the entitlement: available
to subscribers, because a push about a transit is the living layer arriving unprompted, and
that *is* the thing being rented. A free user who turns notifications on should get the
paywall, not a broken switch.

### 5.2 The other controls

- **Quiet hours: 22:00–08:00, shown, not editable.** Displaying it is the point — it tells
  the person we thought about it. Making it editable invites somebody to set 03:00 and then
  file a complaint about a 03:00 notification.
- **Delivery hour: one field, default 08:00.** Editable, because "I get up at 05:30" is a
  real fact about a person and the only one they can tell us that we cannot measure.
  Clamped to outside quiet hours.
- **Timezone: shown, with its source, and overridable.** "Warsaw — from your device" or
  "Auckland — from your birth data". Showing the *source* is what makes the override
  discoverable to exactly the person who needs it: somebody who moved and whose
  notifications are landing at the wrong hour will look here first.
- **A permanent "turn these off" action inside every notification** — an action button, not
  a deep link into a settings tree. Apple 4.5.4 requires an in-app opt-out; making it one
  tap from the notification is both the compliant answer and the one that converts an
  annoyed person into a quieter subscriber instead of an uninstall. §4's evidence is that
  39% disable and 8% uninstall — the design goal is to make the disable path so easy that
  nobody reaches for the uninstall path.

### 5.3 The permission ask

**Do not ask on first launch.** iOS opt-in averages 43.9% and a cold prompt is how you get
the low end of that.

Use **provisional authorisation** (`UNAuthorizationOptions.provisional`) on iOS: the app may
send without a prompt, notifications land quietly in Notification Center only — no banner,
no sound, no lock screen — and each one carries its own *Keep / Turn Off* prompt. The person
decides after seeing two or three real ones what a real one is like. That is the honest
version of a permission ask for this specific product, because the product's whole claim is
that its notifications are worth having, and provisional authorisation is the mechanism that
lets us prove it instead of asserting it.

Android has no equivalent trial; ask `POST_NOTIFICATIONS` at the moment the person turns the
setting on, never at launch.

### 5.4 Strings

Every user-facing string here needs all six locales — **en, es, de, it, fr, pt-BR** — under
the same rule as `alma/i18n/`. `LOCALES` is `("en", "es", "de", "it", "fr", "pt-BR")` and
`scripts/check-locales.mjs` fails the build on English left behind. The English source set,
so that nobody invents a seventh string later:

```
daily.setting.title              "The daily"
daily.setting.off                "Off"
daily.setting.occasionally       "Occasionally"
daily.setting.only_what_matters  "Only what matters"
daily.setting.off.detail         "No notifications. Today is still here whenever you open it."
daily.setting.occasionally.detail
    "About once a week, when something in your chart is actually exact."
daily.setting.only_matters.detail
    "A few times a year. The slow ones only — the transits that last months."
daily.setting.hour               "Arrives at"
daily.setting.quiet              "Never between 22:00 and 08:00, in your time."
daily.setting.timezone           "Your time"
daily.setting.timezone.device    "from your device"
daily.setting.timezone.birth     "from your birth data"
daily.setting.timezone.chosen    "you chose this"
daily.action.turn_off            "Turn these off"
daily.action.quieter             "Fewer of these"
daily.empty.title                "Nothing is exact today"
daily.empty.body                 "What is still in orb is below. Nothing perfects today."
```

The three detail lines carry the honesty this feature is built on — *"Today is still here
whenever you open it"* is what makes Off a safe choice rather than a loss — and they are
the ones most likely to be flattened in translation. They should be translated by whoever
did the chapter metadata, against the reasoning in this file, not from the English alone.

---

## 6 · The recommendation

Implementable as written. No decision below needs re-deriving.

### 6.1 Shape

**Two surfaces, one engine.**

- **Today** — a pulled page, always available, generated on open and cached for the day.
  It shows what is in orb (6.4–10.7 contacts on an average day, §1.2), ranked by
  `Hit.urgency`, with the exact instants and the windows. On a day with nothing exact it
  says so, in the reader's language, and shows what is still live. This is what makes
  silence survivable.
- **The notification** — pushed only when §6.3's rule fires. Median 46 times a year.

### 6.2 Engine

- `transits.scan` over **one year ahead**, `include_moon=False`, stored. 1.35 s and ~470
  rows per chart (§2.4). Re-scan monthly, and on any change to birth data. Do not scan
  nightly — it is the same answer at 30× the cost.
- **The Moon is excluded, permanently** (§1.5). It may be cited as context inside a piece
  another body earned; it may never be the reason one fires.
- Ranking is `transits._weight` and `Hit.urgency`, unchanged. Do not add a second scoring
  system; the one that exists already encodes the distinction §1.3 measured.

### 6.3 The push rule

```
candidate on day D  ⟺  weight ≥ 0.35 and the aspect perfects on D
                    ∨  transiting body ∈ SLOW_BODIES and weight ≥ 0.30
                       and the contact enters orb on D
admit               ⟸  no push in the previous 3 days
                     ∧  fewer than 10 pushes this calendar month
                     ∧  local time is outside 22:00–08:00
valve               ⟸  if 21 days have passed with no push, the floor for the
                       next candidate only drops to 0.20
tie-break           ⟸  highest weight; at most one push per day
```

Measured: median **45.5/yr (0.88/week)**, max **59/yr (1.13/week)**, worst silence **33 days**
with the valve. Every chart in a 24-chart cohort under 1.5/week (§4.2, §4.3).

### 6.4 Generation

- Model **`claude-sonnet-5`**. $0.0105 per push, $0.0162 per Today page (§2.2).
- The one-event brief shape: the hit plus the natal lines it touches. 167 chars at the
  median against 2,324 for the whole-day shape (§2.1).
- Through `writer.py` → `validator.py` unchanged. **The daily cites like a chapter or it is
  not published.** `transits.factors()` already returns citable strings; that is the
  contract and nothing new is needed.
- Six languages, from `alma/i18n/`, same as everything else.
- **No kernel cache in v1** (§2.5). It saves $0.0105 a piece, and the liability of a second
  source of truth about what a transit means is not worth that.

### 6.5 Budget

Per subscriber per month, worst case: $0.0398 (pushes) + $0.1944 (Today opened 12×) =
**$0.234**, which is **2.6% of the $8.99 US net** and **3.2% of the $7.33 EU net**. Against
`subscriber_month_budget` of $3.50 with $1.89 already committed to chat, this lands at
**$2.13 of $3.50**.

**Do not raise `subscriber_month_budget`.** The daily fits inside it with $1.37 to spare,
and a ceiling that gets raised whenever a feature is added is a ceiling that has stopped
being one.

### 6.6 Delivery

- **08:00** in the person's own clock, fixed, no send-time optimisation (§3.4).
- Timezone from the ladder in §3.3: device → chosen → birth → (unreachable) UTC.
- **Quiet hours 22:00–08:00, hard, dropped not deferred** (§3.5).
- The 3-day minimum gap absorbs the travel double-send for free.

### 6.7 Settings

Three positions — Off / Occasionally / Only what matters — default **Occasionally** for
subscribers and **Off** for everyone else. One tap to Off from inside any notification.
Provisional authorisation on iOS; ask on Android only at the moment the setting is turned
on. Six languages (§5).

### 6.8 What the build agents must ask for rather than edit

Another workflow owns `src/`, `alma/api/deps.py`, `funnel.py`, `accounts.py`, `billing.py`
and `geo.py`. Three things are needed from them, and until they exist the daily should be
coded against these as contracts:

1. **`deps.py`** — an `X-Alma-Timezone` request header, IANA identifier, validated through
   the existing `geo.is_known_timezone()`, ignored silently when absent or unknown. Same
   shape as the country header. Persisted to the device row, not just read per-request,
   because the notification job has no request to read. **Landed** as
   `deps.device_timezone`; see the note at the end of §3.2.
2. **`accounts.py`** — the notification preference (three positions), the delivery hour, and
   the timezone override, on the user rather than the profile. A person has one phone and
   several charts; the preference belongs to the phone's owner.
3. **`billing.py` / entitlements** — nothing new. `tier_of()` returning `subscriber` is the
   gate, and `LIVING_SYSTEMS` already contains `transits`.

New modules the daily needs and owns outright: the selection rule, the notification
transport (APNs + FCM — neither exists today), the device-token table, and the job.

### 6.9 The scheduler, which is somebody's problem already

`alma/billing/renewals.py` runs as `python -m alma.billing.renewals` and its docstring says
plainly that nothing schedules it. **The daily inherits that gap and doubles it** — a
renewal notice that is a day late is survivable; a daily that is a day late is a lie about
what day it is.

Build the daily job the same way and with the same discipline: idempotent, keyed on
`(user, date)` in `UsageCounter` exactly as `renewals.py` keys on the renewal date, so that
a job run twice sends once. But it needs to run **hourly**, not daily, because 08:00 happens
26 times around the world and a once-a-day run can only be 08:00 somewhere. An hourly job
that selects the users whose local hour is now 08:00 is the correct shape, and it is also
the shape that makes a missed run cost one hour rather than one day.

**Whoever wires the cron for `renewals.py` should wire this at the same time.** Two jobs
that do not exist is one operations problem, not two.

---

## 7 · What is still open

Written down rather than left to be rediscovered:

- **The valve's voice.** §4.3 recommends a 21-day valve at weight 0.20, on the condition
  that the resulting piece reads as a quiet week rather than an announcement. Nobody has
  written one yet. If it cannot be written honestly in six languages, drop the valve and
  accept the 60-day silence — that is the honest failure and the manufactured piece is not.
- **Chart E.** The no-birth-time chart loses the Ascendant and Midheaven, which are two of
  the five natal points carrying `NATAL_WEIGHT` 1.0. It gets 65 days a year with nothing at
  weight ≥ 0.30 against 0–20 for the others (§1.2). The daily will be measurably thinner for
  these people and no design here changes that. What it should do is *say* so — the Today
  page for a chart without a birth time should carry the existing `unavailable` note, which
  `natal.compute` already produces. Do not silently serve a thinner product.
- **Compatibility and solar return are in `LIVING_SYSTEMS` and are not in this design.** A
  synastry transit — something perfecting to a partner's chart — is arguably the most
  interesting daily this product could send, and `synastry.py` exists. It is out of scope
  here because nobody has measured how often it fires, and it should get its own §1 before
  anybody builds it.
- **Nobody has measured whether people want this.** Every number in this file is about
  supply. The demand side is a funnel stage that does not exist yet, and the first honest
  thing to instrument after launch is not open rate but **the ratio of Off to Occasionally
  after 30 days**, because that is the only metric that measures the thing the owner
  actually asked for.

---

## Sources

- [Braze — Don't Push Me: What Makes Users Opt Out of Push Notifications](https://www.braze.com/resources/articles/opt-out-of-push-notifications-why-users-do-it)
- [MobiLoud — 50+ Push Notification Statistics for 2025](https://www.mobiloud.com/blog/push-notification-statistics) (compiles the Localytics and CleverTap figures)
- [Airship — Mobile App Push Notification Benchmarks for 2025](https://www.airship.com/resources/benchmark-report/mobile-app-push-notification-benchmarks-for-2025/)
- [Airship — How Push Notifications Impact Mobile App Retention Rates](https://grow.urbanairship.com/rs/313-QPJ-195/images/airship-how-push-notifications-impact-mobile-app-retention-rates.pdf)
- [Apple — App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) (4.5.4, 3.1.2(a), 5.1.1)
- [Google Play — Developer Program Policy](https://support.google.com/googleplay/android-developer/answer/17190352)
- [Apple — Provisional authorization for quiet notifications](https://useyourloaf.com/blog/provisional-authorization-of-user-notificatons/)
- [Aurae — Co-Star App Review 2026](https://www.auraeastrology.com/blog/co-star-app-review-2026-an-astrologers-honest-opinion) and [Unstar — 5 Astrology Apps Ranked](https://unstar.app/blog/co-star-sanctuary-pattern-nebula-stellium-astrology-apps-ranked-2026) (the 2–3/day figure and the review reaction)
- [JIPITEC — Push Notifications under E-Privacy Law (2025)](https://www.jipitec.eu/jipitec/article/view/423)
