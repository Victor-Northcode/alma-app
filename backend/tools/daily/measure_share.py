"""Third pass: how shared is a transit, really — and how long do they last.

1. Orb-window duration by transiting body: how many days a contact is live.
2. Collision rate: do two unrelated charts ever get the same (triple, day)?
   This is the ceiling on any "generate once, serve many" strategy keyed on
   the day. Compared against the same-triple-any-day reuse, which is the
   ceiling on a strategy keyed on the *kernel* instead.
"""
from __future__ import annotations

import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, "/Users/anatoliymikhaylow/alma_project1/backend")

from alma.engine import natal, transits  # noqa: E402
from alma.engine.timeutil import _julian_day, resolve  # noqa: E402

# A larger cohort — 24 synthetic-but-real birth moments spread over 45 years
# and both hemispheres, because collision rate is a population statistic and
# six charts cannot measure one.
import random  # noqa: E402
random.seed(11)

PLACES = [
    ("Europe/Warsaw", 50.06, 19.94), ("America/New_York", 40.71, -74.01),
    ("Asia/Seoul", 37.57, 126.98), ("Australia/Sydney", -33.87, 151.21),
    ("America/Sao_Paulo", -23.55, -46.63), ("Africa/Lagos", 6.52, 3.38),
    ("Europe/Madrid", 40.42, -3.70), ("Asia/Kolkata", 19.08, 72.88),
]

COHORT = []
for i in range(24):
    y = random.randint(1962, 2006)
    mo = random.randint(1, 12)
    d = random.randint(1, 28)
    tz, lat, lon = PLACES[i % len(PLACES)]
    if i % 7 == 0:          # one in seven has no birth time
        h = mi = None
    else:
        h, mi = random.randint(0, 23), random.choice([0, 15, 30, 45])
    COHORT.append((f"c{i:02d}", y, mo, d, h, mi, tz, lat, lon))

START = _julian_day(datetime(2026, 8, 7, tzinfo=timezone.utc))
END = _julian_day(datetime(2027, 8, 7, tzinfo=timezone.utc))
DAYS = 365


def main():
    charts = {}
    for (label, y, mo, d, h, mi, tz, lat, lon) in COHORT:
        moment = resolve(year=y, month=mo, day=d, hour=h, minute=mi,
                         tz_name=tz, on_ambiguous="earlier")
        charts[label] = natal.compute(moment=moment, latitude=lat, longitude=lon)

    all_hits = {
        label: transits.scan(c, start_jd=START, end_jd=END, reference_jd=START)
        for label, c in charts.items()
    }

    # ── 1. how long a contact is live ─────────────────────────────────────
    print("### orb-window duration in days, by transiting body")
    print(f"{'body':10s} {'n':>5s} {'median':>8s} {'mean':>8s} {'p90':>8s} {'max':>8s}")
    spans = defaultdict(list)
    for hits in all_hits.values():
        for h in hits:
            if h.enters_jd is not None and h.leaves_jd is not None:
                spans[h.transiting].append(h.leaves_jd - h.enters_jd)
    for body in ("moon", "mercury", "venus", "sun", "mars", "jupiter",
                 "saturn", "chiron", "uranus", "neptune", "pluto"):
        v = spans.get(body)
        if not v:
            continue
        v.sort()
        print(f"{body:10s} {len(v):5d} {statistics.median(v):8.2f} "
              f"{statistics.mean(v):8.2f} {v[int(len(v)*0.9)]:8.2f} {max(v):8.2f}")

    # ── 2. collision rate ─────────────────────────────────────────────────
    # keyed on the day: (transiting, aspect, natal, exact-day)
    day_keys = defaultdict(set)
    kernel_keys = defaultdict(set)
    for label, hits in all_hits.items():
        for h in hits:
            d = int(h.exact_jd - START)
            if not (0 <= d < DAYS):
                continue
            day_keys[(h.transiting, h.aspect, h.natal, d)].add(label)
            kernel_keys[(h.transiting, h.aspect, h.natal)].add(label)

    n = len(charts)
    total_events = sum(
        1 for hits in all_hits.values() for h in hits
        if 0 <= int(h.exact_jd - START) < DAYS
    )
    print(f"\n### cohort of {n} charts, {total_events} exact hits in the year")
    print(f"  distinct (triple, exact-day) keys : {len(day_keys)}"
          f"   → reuse {total_events/len(day_keys):.2f}x")
    shared_day = sum(1 for v in day_keys.values() if len(v) > 1)
    print(f"  keys shared by >1 chart           : {shared_day} "
          f"({100*shared_day/len(day_keys):.1f}%)")
    print(f"  distinct (triple) kernels         : {len(kernel_keys)}"
          f"   → reuse {total_events/len(kernel_keys):.2f}x")
    shared_kernel = sum(1 for v in kernel_keys.values() if len(v) > 1)
    print(f"  kernels shared by >1 chart        : {shared_kernel} "
          f"({100*shared_kernel/len(kernel_keys):.1f}%)")
    sizes = Counter(len(v) for v in kernel_keys.values())
    print(f"  kernel population coverage        : "
          f"{sum(k*c for k, c in sizes.items())/len(kernel_keys):.2f} charts per kernel")

    # ── 3. how much of the *text* is chart-specific ───────────────────────
    # A daily piece names: the transiting body + its current sign/degree
    # (shared), the natal point + its sign/degree/house (personal), the exact
    # instant in the reader's clock (personal), and the window (personal).
    print("\n### degrees are personal: spread of natal longitudes hit by one kernel")
    for key in list(kernel_keys)[:1]:
        pass
    spread = []
    for (tb, asp, nat), labels in kernel_keys.items():
        if len(labels) < 4:
            continue
        lons = []
        for label in labels:
            pts = transits.natal_points(charts[label])
            if nat in pts:
                lons.append(pts[nat])
        if len(lons) >= 4:
            spread.append(max(lons) - min(lons))
    print(f"  {len(spread)} kernels shared by 4+ charts; mean natal-longitude "
          f"span within a kernel {statistics.mean(spread):.1f}° "
          f"(median {statistics.median(spread):.1f}°)")

    # ── 4. per-chart event-day counts across the cohort ───────────────────
    print("\n### per-chart event days at weight>=0.30 (exact hits only), cohort")
    counts = []
    for label, hits in all_hits.items():
        ed = {int(h.exact_jd - START) for h in hits
              if h.weight >= 0.30 and 0 <= int(h.exact_jd - START) < DAYS}
        counts.append(len(ed))
    counts.sort()
    print(f"  min {counts[0]}  p25 {counts[len(counts)//4]}  median "
          f"{statistics.median(counts):.0f}  p75 {counts[3*len(counts)//4]}  "
          f"max {counts[-1]}  mean {statistics.mean(counts):.1f}")

    print("\n### per-chart event days at weight>=0.40, cohort")
    counts = []
    for label, hits in all_hits.items():
        ed = {int(h.exact_jd - START) for h in hits
              if h.weight >= 0.40 and 0 <= int(h.exact_jd - START) < DAYS}
        counts.append(len(ed))
    counts.sort()
    print(f"  min {counts[0]}  median {statistics.median(counts):.0f}  "
          f"max {counts[-1]}  mean {statistics.mean(counts):.1f}")

    print("\n### charts with NO weight>=0.50 hit at all in the year: "
          f"{sum(1 for hits in all_hits.values() if not any(h.weight >= 0.5 for h in hits))}"
          f" of {n}")


if __name__ == "__main__":
    main()
