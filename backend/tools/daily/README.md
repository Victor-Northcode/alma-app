# The measurements behind `docs/THE-DAILY.md`

Six scripts. Every number in `docs/THE-DAILY.md` §1, §2 and §4.2 came out of one of them,
run on 7 August 2026. They are here rather than in a scratchpad because the headline
figures — 46 pushes a year at the median, 0.88 a week — are exactly the sort of thing that
drifts silently the next time `TRANSIT_ORBS`, `BODY_WEIGHT` or `NATAL_WEIGHT` is touched,
and a number nobody can re-run is an opinion with a decimal point.

They are not tests and `testpaths` does not collect them. Run them by hand:

```
cd backend && .venv/bin/python tools/daily/measure_daily.py
```

| script | answers | runtime |
|---|---|---|
| `measure_daily.py` | days per year with an exact hit / an orb entry / nothing, per chart, and the weight sweep | ~22 s |
| `measure_policy.py` | where the volume comes from, by transiting body, natal point and aspect; the first policy sweep | ~8 s |
| `measure_share.py` | orb-window duration by body; how much a transit is really shared across a 24-chart cohort | ~28 s |
| `measure_cost.py` | one daily piece priced through `alma/ai/cost.py`, at every model and cadence | ~5 s |
| `measure_final.py` | the recommended selection rule simulated over the cohort | ~30 s |
| `measure_valve.py` | whether the 21-day starvation valve closes the long silences, and at what price | ~30 s |

The measurement window is hard-coded to **2026-08-07 → 2027-08-07** so that a re-run is
comparable to the document rather than to a different year of sky. Change it only
deliberately, and say so when you do.

The cohort in `measure_share.py`, `measure_final.py` and `measure_valve.py` is seeded
(`random.seed(11)`) for the same reason: the same 24 charts every time, or the numbers move
for reasons that have nothing to do with the code.
