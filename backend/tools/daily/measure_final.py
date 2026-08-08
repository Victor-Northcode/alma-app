"""Fifth pass: the recommended rule, simulated over a 24-chart cohort.

The rule under test:
  * candidate = an exact hit whose weight ≥ FLOOR, on the day it perfects
  * plus a "window opens" candidate for slow bodies (jupiter and outward)
    when a contact enters orb and its weight ≥ SLOW_FLOOR
  * at most one push a day, at most CAP a month, never two within GAP days
  * ties broken by weight
Reports pushes per year, per month, worst-case gaps, and how many charts fall
below a floor of interest.
"""
from __future__ import annotations

import random
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, "/Users/anatoliymikhaylow/alma_project1/backend")

from alma.engine import natal, transits  # noqa: E402
from alma.engine.timeutil import _julian_day, resolve  # noqa: E402

random.seed(11)
PLACES = [
    ("Europe/Warsaw", 50.06, 19.94), ("America/New_York", 40.71, -74.01),
    ("Asia/Seoul", 37.57, 126.98), ("Australia/Sydney", -33.87, 151.21),
    ("America/Sao_Paulo", -23.55, -46.63), ("Africa/Lagos", 6.52, 3.38),
    ("Europe/Madrid", 40.42, -3.70), ("Asia/Kolkata", 19.08, 72.88),
]
COHORT = []
for i in range(24):
    y, mo, d = random.randint(1962, 2006), random.randint(1, 12), random.randint(1, 28)
    tz, lat, lon = PLACES[i % len(PLACES)]
    h, mi = (None, None) if i % 7 == 0 else (random.randint(0, 23),
                                             random.choice([0, 15, 30, 45]))
    COHORT.append((f"c{i:02d}", y, mo, d, h, mi, tz, lat, lon))

START = _julian_day(datetime(2026, 8, 7, tzinfo=timezone.utc))
END = _julian_day(datetime(2027, 8, 7, tzinfo=timezone.utc))
DAYS = 365
SLOW = set(transits.SLOW_BODIES)


def simulate(hits, *, floor, slow_floor, gap, cap):
    cand = {}
    for h in hits:
        d = int(h.exact_jd - START)
        if 0 <= d < DAYS and h.weight >= floor:
            if h.weight > cand.get(d, (0, None))[0]:
                cand[d] = (h.weight, ("exact", h))
        if (h.transiting in SLOW and h.enters_jd is not None
                and h.weight >= slow_floor):
            de = int(h.enters_jd - START)
            if 0 <= de < DAYS and h.weight > cand.get(de, (0, None))[0]:
                cand[de] = (h.weight, ("opens", h))
    fired, kinds = [], Counter()
    month = Counter()
    for d in sorted(cand):
        if fired and d - fired[-1] < gap:
            continue
        m = d // 30
        if month[m] >= cap:
            continue
        month[m] += 1
        fired.append(d)
        kinds[cand[d][1][0]] += 1
    gaps = [b - a for a, b in zip(fired, fired[1:])]
    lead = fired[0] if fired else DAYS
    tail = DAYS - fired[-1] if fired else DAYS
    return {
        "pushes": len(fired),
        "max_gap": max(gaps + [lead, tail]) if fired else DAYS,
        "median_gap": statistics.median(gaps) if gaps else DAYS,
        "kinds": kinds,
        "months_at_cap": sum(1 for m in range(13) if month[m] >= cap),
    }


def main():
    charts = {}
    for (label, y, mo, d, h, mi, tz, lat, lon) in COHORT:
        m = resolve(year=y, month=mo, day=d, hour=h, minute=mi,
                    tz_name=tz, on_ambiguous="earlier")
        charts[label] = natal.compute(moment=m, latitude=lat, longitude=lon)
    all_hits = {
        k: transits.scan(c, start_jd=START, end_jd=END, reference_jd=START)
        for k, c in charts.items()
    }

    print("cohort of 24 charts (1962–2006, 8 places, 4 without a birth time)\n")
    print(f"{'floor':>6s} {'slow':>6s} {'gap':>4s} {'cap':>4s} | "
          f"{'push/yr med':>12s} {'min':>4s} {'max':>4s} | "
          f"{'push/mo':>8s} | {'worst silence':>14s} {'median gap':>11s} | "
          f"{'exact/opens':>12s}")
    for floor, slow_floor, gap, cap in (
        (0.30, 0.30, 3, 10),
        (0.30, 0.25, 3, 10),
        (0.35, 0.30, 3, 10),
        (0.35, 0.30, 4, 8),
        (0.40, 0.30, 3, 10),
        (0.40, 0.35, 4, 8),
        (0.45, 0.35, 4, 8),
    ):
        rows = [simulate(h, floor=floor, slow_floor=slow_floor, gap=gap, cap=cap)
                for h in all_hits.values()]
        p = sorted(r["pushes"] for r in rows)
        e = sum(r["kinds"]["exact"] for r in rows)
        o = sum(r["kinds"]["opens"] for r in rows)
        print(f"{floor:6.2f} {slow_floor:6.2f} {gap:4d} {cap:4d} | "
              f"{statistics.median(p):12.0f} {p[0]:4d} {p[-1]:4d} | "
              f"{statistics.median(p)/12:8.1f} | "
              f"{max(r['max_gap'] for r in rows):14d} "
              f"{statistics.median([r['median_gap'] for r in rows]):11.1f} | "
              f"{e:5d}/{o:<6d}")

    print("\n### the recommended rule in detail: floor 0.35 / slow 0.30 / gap 3 / cap 10")
    rows = {k: simulate(h, floor=0.35, slow_floor=0.30, gap=3, cap=10)
            for k, h in all_hits.items()}
    p = sorted(r["pushes"] for r in rows.values())
    print(f"  pushes per year across 24 charts: {p}")
    print(f"  median {statistics.median(p):.0f}/yr = {statistics.median(p)/52:.2f}/week")
    print(f"  worst chart {max(p)}/yr = {max(p)/52:.2f}/week; "
          f"best {min(p)}/yr = {min(p)/52:.2f}/week")
    print(f"  worst single silence in the cohort: "
          f"{max(r['max_gap'] for r in rows.values())} days")
    weeks = []
    for k, h in all_hits.items():
        cand = simulate(h, floor=0.35, slow_floor=0.30, gap=3, cap=10)
        weeks.append(cand["pushes"] / 52)
    print(f"  every chart under 2/week? "
          f"{'yes' if max(weeks) < 2 else 'NO — max %.2f' % max(weeks)}")
    print(f"  every chart under 1.5/week? "
          f"{'yes' if max(weeks) < 1.5 else 'NO — max %.2f' % max(weeks)}")

    # cost of that cadence
    from alma.ai import cost  # noqa: E402
    unit = cost.cost("claude-sonnet-5", 1400, 420).dollars
    unit_day = cost.cost("claude-sonnet-5", 2400, 600).dollars
    med = statistics.median(p)
    print(f"\n  push text at {med:.0f}/yr on sonnet-5: "
          f"${unit*med:.3f}/yr = ${unit*med/12:.4f}/month "
          f"({100*unit*med/12/8.99:.2f}% of $8.99 US net)")
    print(f"  plus a pulled 'today' page generated only when opened, 12×/month: "
          f"${unit_day*12:.4f}/month ({100*unit_day*12/8.99:.2f}% of US net)")
    print(f"  worst case, both, every month: "
          f"${unit*max(p)/12 + unit_day*30:.4f} "
          f"— against $3.50 ceiling minus $1.89 chat = $1.61 headroom")


if __name__ == "__main__":
    main()
