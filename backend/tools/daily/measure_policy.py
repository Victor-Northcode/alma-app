"""Second pass: where the noise comes from, and how much a shared kernel buys.

1. Which transiting bodies produce the hits — the noise budget by body.
2. How many distinct (transiting, aspect, natal) triples a year contains, and
   how much overlap there is between unrelated charts — the reuse ceiling for
   any shared-generation strategy.
3. A simulated selection policy: weight floor + minimum gap + monthly cap, run
   day by day over the year, reporting how many pushes actually fire.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, "/Users/anatoliymikhaylow/alma_project1/backend")

from alma.engine import natal, transits  # noqa: E402
from alma.engine.timeutil import _julian_day, resolve  # noqa: E402

CHARTS = [
    ("Nairobi 1961", 1961, 8, 4, 19, 24, "Africa/Nairobi", -1.2921, 36.8219),
    ("Krakow 1978", 1978, 5, 18, 3, 5, "Europe/Warsaw", 50.0647, 19.9450),
    ("BuenosAires 1990", 1990, 11, 2, 14, 40, "America/Argentina/Buenos_Aires", -34.6037, -58.3816),
    ("Seoul 1996", 1996, 2, 29, 8, 15, "Asia/Seoul", 37.5665, 126.9780),
    ("Auckland 2003 (no time)", 2003, 9, 21, None, None, "Pacific/Auckland", -36.8485, 174.7633),
    ("Reykjavik 1985", 1985, 12, 12, 23, 50, "Atlantic/Reykjavik", 64.1466, -21.9426),
]

START = _julian_day(datetime(2026, 8, 7, tzinfo=timezone.utc))
END = _julian_day(datetime(2027, 8, 7, tzinfo=timezone.utc))
DAYS = 365


def build(spec):
    label, y, mo, d, h, mi, tz, lat, lon = spec
    moment = resolve(year=y, month=mo, day=d, hour=h, minute=mi,
                     tz_name=tz, on_ambiguous="earlier")
    return label, natal.compute(moment=moment, latitude=lat, longitude=lon)


def main():
    all_hits = {}
    for spec in CHARTS:
        label, chart = build(spec)
        hits = transits.scan(chart, start_jd=START, end_jd=END, reference_jd=START)
        all_hits[label] = hits

    # ── 1. where the volume comes from ────────────────────────────────────
    print("\n### hits per transiting body (mean over 6 charts, one year)")
    per_body = Counter()
    per_body_heavy = Counter()
    for hits in all_hits.values():
        for h in hits:
            per_body[h.transiting] += 1
            if h.weight >= 0.3:
                per_body_heavy[h.transiting] += 1
    n = len(all_hits)
    print(f"{'body':10s} {'hits/yr':>8s} {'w>=0.30/yr':>11s}")
    for body, count in per_body.most_common():
        print(f"{body:10s} {count/n:8.1f} {per_body_heavy[body]/n:11.1f}")

    print("\n### hits per natal point (mean, one year)")
    per_natal = Counter()
    for hits in all_hits.values():
        for h in hits:
            per_natal[h.natal] += 1
    for pt, c in per_natal.most_common():
        print(f"{pt:12s} {c/n:8.1f}")

    print("\n### aspect mix (mean, one year)")
    per_aspect = Counter()
    for hits in all_hits.values():
        for h in hits:
            per_aspect[h.aspect] += 1
    for a, c in per_aspect.most_common():
        print(f"{a:12s} {c/n:8.1f}")

    # ── 2. the reuse ceiling ──────────────────────────────────────────────
    print("\n### distinct (transiting, aspect, natal) triples")
    triples = {}
    for label, hits in all_hits.items():
        t = {(h.transiting, h.aspect, h.natal) for h in hits}
        triples[label] = t
        print(f"  {label:26s} {len(t):4d} distinct triples from {len(hits):4d} hits "
              f"(reuse {len(hits)/len(t):.2f}x within one chart-year)")
    union = set().union(*triples.values())
    print(f"  union over 6 unrelated charts: {len(union)} distinct triples")
    total = sum(len(t) for t in triples.values())
    print(f"  sum of per-chart sets:         {total}  →  cross-chart reuse "
          f"{total/len(union):.2f}x at 6 charts")
    # pairwise overlap
    labels = list(triples)
    overlaps = []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            a, b = triples[labels[i]], triples[labels[j]]
            overlaps.append(len(a & b) / len(a | b))
    print(f"  mean pairwise Jaccard between two unrelated charts: "
          f"{sum(overlaps)/len(overlaps):.3f}")

    # the theoretical vocabulary
    print(f"  theoretical vocabulary: {len(transits.BODY_WEIGHT)-1} transiting "
          f"× {len(transits.NATAL_WEIGHT)+1} natal × 5 aspects = "
          f"{(len(transits.BODY_WEIGHT)-1)*(len(transits.NATAL_WEIGHT)+1)*5}")

    # ── 3. the policy simulation ──────────────────────────────────────────
    print("\n### policy simulation: weight floor + minimum gap + monthly cap")
    print(f"{'floor':>6s} {'gap':>4s} {'cap':>4s} | "
          f"{'pushes/yr':>10s} {'pushes/mo':>10s} {'max gap':>8s} {'months at cap':>14s}")
    for floor in (0.25, 0.3, 0.35, 0.4, 0.5):
        for gap in (2, 3):
            for cap in (8, 10, 12):
                per_chart = []
                for label, hits in all_hits.items():
                    # candidate events: exact hits at or above the floor
                    events = defaultdict(list)
                    for h in hits:
                        if h.weight < floor:
                            continue
                        d = int(h.exact_jd - START)
                        if 0 <= d < DAYS:
                            events[d].append(h)
                    fired = []
                    month_count = Counter()
                    for d in range(DAYS):
                        if d not in events:
                            continue
                        if fired and d - fired[-1] < gap:
                            continue
                        month = d // 30
                        if month_count[month] >= cap:
                            continue
                        month_count[month] += 1
                        fired.append(d)
                    gaps = [b - a for a, b in zip(fired, fired[1:])]
                    per_chart.append((
                        len(fired),
                        max(gaps) if gaps else DAYS,
                        sum(1 for m in range(12) if month_count[m] >= cap),
                    ))
                mean_fired = sum(p[0] for p in per_chart) / len(per_chart)
                max_gap = max(p[1] for p in per_chart)
                capped = sum(p[2] for p in per_chart) / len(per_chart)
                print(f"{floor:6.2f} {gap:4d} {cap:4d} | {mean_fired:10.1f} "
                      f"{mean_fired/12:10.1f} {max_gap:8d} {capped:14.1f}")

    # ── 4. what the pull-open (non-push) surface would contain daily ──────
    print("\n### 'open the app' surface: hits in orb on an average day")
    for label, hits in all_hits.items():
        counts = []
        heavy = []
        for d in range(DAYS):
            j = START + d + 0.5
            live = transits.active(hits, j)
            counts.append(len(live))
            heavy.append(sum(1 for h in live if h.weight >= 0.3))
        print(f"  {label:26s} in orb {sum(counts)/DAYS:5.2f}/day "
              f"(min {min(counts)}, max {max(counts)}) · "
              f"w>=0.30 {sum(heavy)/DAYS:5.2f}/day "
              f"(days with none: {sum(1 for x in heavy if x == 0)})")


if __name__ == "__main__":
    main()
