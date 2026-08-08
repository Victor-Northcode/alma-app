"""Measure what a real day actually contains, for docs/THE-DAILY.md.

Runs alma.engine.transits over a full year for several real charts and counts
days: exact hits, orb entries, silence, and the longest runs of each.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone

sys.path.insert(0, "/Users/anatoliymikhaylow/alma_project1/backend")

from alma.engine import natal, transits  # noqa: E402
from alma.engine.timeutil import resolve  # noqa: E402

# --- the charts -------------------------------------------------------------
# Varied by decade, hemisphere, and one deliberately without a birth time.
CHARTS = [
    # name, year, month, day, hour, minute, tz, lat, lon
    ("1961 · Nairobi (南 equatorial, time known)",
     1961, 8, 4, 19, 24, "Africa/Nairobi", -1.2921, 36.8219),
    ("1978 · Kraków (N europe, time known)",
     1978, 5, 18, 3, 5, "Europe/Warsaw", 50.0647, 19.9450),
    ("1990 · Buenos Aires (S hemisphere, time known)",
     1990, 11, 2, 14, 40, "America/Argentina/Buenos_Aires", -34.6037, -58.3816),
    ("1996 · Seoul (N hemisphere, time known)",
     1996, 2, 29, 8, 15, "Asia/Seoul", 37.5665, 126.9780),
    ("2003 · Auckland (S hemisphere, NO BIRTH TIME)",
     2003, 9, 21, None, None, "Pacific/Auckland", -36.8485, 174.7633),
    ("1985 · Reykjavík (high latitude, time known)",
     1985, 12, 12, 23, 50, "Atlantic/Reykjavik", 64.1466, -21.9426),
]

# The measurement year: today forward one year.
START = datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc)
END = datetime(2027, 8, 7, 0, 0, tzinfo=timezone.utc)


def jd(dt: datetime) -> float:
    from alma.engine.timeutil import _julian_day
    return _julian_day(dt)


START_JD = jd(START)
END_JD = jd(END)
DAYS = int(round(END_JD - START_JD))


def day_index(j: float) -> int:
    """Which day of the window a julian day falls on (0-based, UTC days)."""
    return int((j - START_JD) // 1)


def runs(flags: list[bool], value: bool) -> tuple[int, list[int]]:
    """Longest run of `value`, and every run length."""
    best = 0
    cur = 0
    lengths = []
    for f in flags:
        if f == value:
            cur += 1
            best = max(best, cur)
        else:
            if cur:
                lengths.append(cur)
            cur = 0
    if cur:
        lengths.append(cur)
    return best, lengths


def analyse(chart, label, *, bodies=None, include_moon=False, tag=""):
    hits = transits.scan(
        chart,
        start_jd=START_JD,
        end_jd=END_JD,
        bodies=bodies,
        include_moon=include_moon,
        reference_jd=START_JD,
    )
    exact_days = defaultdict(list)
    enter_days = defaultdict(list)
    leave_days = defaultdict(list)
    in_orb_days = defaultdict(list)

    for h in hits:
        d = day_index(h.exact_jd)
        if 0 <= d < DAYS:
            exact_days[d].append(h)
        if h.enters_jd is not None:
            de = day_index(h.enters_jd)
            if 0 <= de < DAYS:
                enter_days[de].append(h)
        if h.leaves_jd is not None:
            dl = day_index(h.leaves_jd)
            if 0 <= dl < DAYS:
                leave_days[dl].append(h)

    # in-orb coverage per day
    for d in range(DAYS):
        j = START_JD + d + 0.5
        live = [
            h for h in hits
            if (h.enters_jd is None or h.enters_jd <= j)
            and (h.leaves_jd is None or j <= h.leaves_jd)
        ]
        in_orb_days[d] = live

    has_exact = [d in exact_days for d in range(DAYS)]
    has_event = [(d in exact_days or d in enter_days) for d in range(DAYS)]
    has_anything = [
        (d in exact_days or d in enter_days or d in leave_days)
        for d in range(DAYS)
    ]

    longest_empty, empty_runs = runs(has_event, False)
    longest_busy, busy_runs = runs(has_event, True)

    exact_counts = Counter(len(v) for v in exact_days.values())

    # weight distribution of exact hits
    weights = sorted((h.weight for h in hits), reverse=True)

    return {
        "label": label + tag,
        "total_hits": len(hits),
        "days_with_exact": len(exact_days),
        "days_with_entry": len(enter_days),
        "days_with_exit": len(leave_days),
        "days_with_exact_or_entry": sum(has_event),
        "days_with_nothing": DAYS - sum(has_event),
        "days_with_no_event_at_all": DAYS - sum(has_anything),
        "longest_empty_run": longest_empty,
        "longest_busy_run": longest_busy,
        "empty_runs_over_7": sum(1 for r in empty_runs if r >= 7),
        "empty_runs_over_14": sum(1 for r in empty_runs if r >= 14),
        "max_exact_in_one_day": max(exact_counts) if exact_counts else 0,
        "mean_in_orb_per_day": round(
            sum(len(v) for v in in_orb_days.values()) / DAYS, 2),
        "max_in_orb": max(len(v) for v in in_orb_days.values()),
        "min_in_orb": min(len(v) for v in in_orb_days.values()),
        "heaviest_weight": weights[0] if weights else 0,
        "hits_weight_over_0_5": sum(1 for w in weights if w >= 0.5),
        "hits_weight_over_0_3": sum(1 for w in weights if w >= 0.3),
        "hits_weight_over_0_2": sum(1 for w in weights if w >= 0.2),
        "_hits": hits,
        "_exact_days": exact_days,
        "_enter_days": enter_days,
    }


def main():
    out = {}
    for (label, y, mo, d, h, mi, tz, lat, lon) in CHARTS:
        moment = resolve(year=y, month=mo, day=d, hour=h, minute=mi,
                         tz_name=tz, on_ambiguous="earlier")
        chart = natal.compute(moment=moment, latitude=lat, longitude=lon)
        print(f"\n{'='*78}\n{label}", flush=True)
        print(f"  time_known={chart.time_known} points={len(transits.natal_points(chart))}",
              flush=True)

        # 1. everything except the Moon (the product default)
        a = analyse(chart, label, include_moon=False)
        # 2. slow outer planets only
        b = analyse(chart, label, bodies=transits.SLOW_BODIES, tag=" [slow only]")
        # 3. Moon alone
        c = analyse(chart, label, bodies=("moon",), include_moon=True, tag=" [moon only]")

        for r in (a, b, c):
            print(
                f"  {r['label'][-14:]:>14} | hits {r['total_hits']:5d} | "
                f"exact-days {r['days_with_exact']:3d} | entry-days {r['days_with_entry']:3d} | "
                f"exact-or-entry {r['days_with_exact_or_entry']:3d} | "
                f"silent {r['days_with_nothing']:3d} | "
                f"longest silence {r['longest_empty_run']:3d} | "
                f"longest busy {r['longest_busy_run']:3d} | "
                f"in-orb/day avg {r['mean_in_orb_per_day']:6.2f} "
                f"(min {r['min_in_orb']}, max {r['max_in_orb']})",
                flush=True,
            )
        out[label] = {
            "all_but_moon": {k: v for k, v in a.items() if not k.startswith("_")},
            "slow_only": {k: v for k, v in b.items() if not k.startswith("_")},
            "moon_only": {k: v for k, v in c.items() if not k.startswith("_")},
        }

        # Threshold sweep on the default (no moon): how many days survive a
        # weight floor?
        for floor in (0.0, 0.15, 0.2, 0.3, 0.4, 0.5):
            kept = [h for h in a["_hits"] if h.weight >= floor]
            ed = {day_index(h.exact_jd) for h in kept
                  if 0 <= day_index(h.exact_jd) < DAYS}
            en = {day_index(h.enters_jd) for h in kept
                  if h.enters_jd is not None and 0 <= day_index(h.enters_jd) < DAYS}
            flags = [(d in ed or d in en) for d in range(DAYS)]
            le, _ = runs(flags, False)
            lb, _ = runs(flags, True)
            print(f"     weight>={floor:.2f}: hits {len(kept):4d}  exact-days {len(ed):3d}  "
                  f"exact-or-entry-days {sum(flags):3d}  longest silence {le:3d}  "
                  f"longest run {lb:3d}", flush=True)
            out[label].setdefault("weight_sweep", {})[f"{floor:.2f}"] = {
                "hits": len(kept), "exact_days": len(ed),
                "event_days": sum(flags), "longest_silence": le, "longest_run": lb,
            }

        # what the heaviest few of the year actually are
        top = sorted(a["_hits"], key=lambda h: -h.weight)[:8]
        for h in top:
            from alma.engine.timeutil import _julian_day  # noqa
            print(f"     top: {h.transiting:8s} {h.aspect:11s} natal {h.natal:10s} "
                  f"w={h.weight:.3f} exact_jd={h.exact_jd:.2f}", flush=True)

    with open("/private/tmp/claude-501/-Users-anatoliymikhaylow-paulagent/"
              "bb1619b8-d883-4b41-b312-5d67734fdf32/scratchpad/daily_measurements.json",
              "w") as f:
        json.dump(out, f, indent=2)
    print("\nwindow:", START.date(), "→", END.date(), f"({DAYS} days)")


if __name__ == "__main__":
    main()
