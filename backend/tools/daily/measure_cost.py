"""Fourth pass: price one daily piece through alma.ai.cost at real rates.

Builds the prompt a daily would actually send — the voice system prompt plus
the day's active transit factors — measures its size, and prices it at each
model tier. Then scales to cadences and compares against the ceilings that
already exist.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

sys.path.insert(0, "/Users/anatoliymikhaylow/alma_project1/backend")

from alma.ai import cost, voice  # noqa: E402
from alma.engine import natal, transits  # noqa: E402
from alma.engine.timeutil import _julian_day, resolve  # noqa: E402

START = _julian_day(datetime(2026, 8, 7, tzinfo=timezone.utc))
END = _julian_day(datetime(2027, 8, 7, tzinfo=timezone.utc))

moment = resolve(year=1990, month=11, day=2, hour=14, minute=40,
                 tz_name="America/Argentina/Buenos_Aires", on_ambiguous="earlier")
chart = natal.compute(moment=moment, latitude=-34.6037, longitude=-58.3816)
hits = transits.scan(chart, start_jd=START, end_jd=END, reference_jd=START)

system_prompt = voice.system_prompt(locale="en", paid=True, memory=None)
print(f"voice.system_prompt(paid=True): {len(system_prompt)} chars "
      f"≈ {len(system_prompt)//4} tokens")

# One day's brief. Two shapes, priced separately.
#
# SHAPE A — "the whole day": everything in orb, as the app's Today surface
#           would want it.
# SHAPE B — "one event": the single hit that earned the interruption, plus a
#           handful of natal context lines so the sentence can place it.
sizes_a, sizes_b = [], []
for d in range(0, 365, 7):
    j = START + d + 0.5
    live = transits.active(hits, j)
    factors_a = transits.factors(live)
    natal_ctx = chart.factors()

    brief_a = "\n".join(
        [f"- {f}" for f in factors_a]
        + [f"- {f}" for f in natal_ctx]
    )
    sizes_a.append(len(brief_a))

    top = [h for h in live if h.weight >= 0.30][:1]
    if top:
        h = top[0]
        # only the natal lines the hit actually touches
        touched = [f for f in natal_ctx if h.natal.replace("_", " ") in f.lower()]
        brief_b = "\n".join([f"- {h.describe()}"] + [f"- {f}" for f in touched[:6]])
        sizes_b.append(len(brief_b))

def stats(v, name):
    v = sorted(v)
    print(f"{name}: median {v[len(v)//2]} chars, min {v[0]}, max {v[-1]}")
    return v[len(v)//2]

med_a = stats(sizes_a, "SHAPE A brief (all in-orb + full natal factors)")
med_b = stats(sizes_b, "SHAPE B brief (one hit + touched natal lines)")

# Scaffolding around the brief — instructions, length rule, locale line.
SCAFFOLD = 900

print("\n### priced through alma.ai.cost.estimate (worst case: full max_tokens)")
print("A daily piece is 90–140 words. The writer's envelope repeats each cited")
print("factor verbatim, so output ≈ words*3 + the citations.")
for name, chars, out_tokens in (
    ("A · whole day, 140 words", med_a + SCAFFOLD, 700),
    ("B · one event, 110 words", med_b + SCAFFOLD, 500),
    ("B-lite · one event, 60 words", med_b + SCAFFOLD, 300),
):
    print(f"\n{name}  (prompt {chars + len(system_prompt)} chars "
          f"≈ {(chars + len(system_prompt))//4} in-tokens, {out_tokens} out-tokens)")
    for model in ("claude-haiku-4-5", "claude-sonnet-5", "claude-opus-5"):
        est = cost.estimate(model, prompt_chars=chars + len(system_prompt),
                            max_output_tokens=out_tokens)
        print(f"   {model:20s} ${est:.5f}  = {est*100:.3f}¢")

print("\n### realistic (not worst-case) cost: measured token shape of a chapter")
print("The one real chapter measured live was 1822 in / 1437 out at $0.0270 on")
print("claude-sonnet-5. A daily at ~40% of a chapter's output:")
for model in ("claude-haiku-4-5", "claude-sonnet-5", "claude-opus-5"):
    for label, i, o in (("whole day", 2400, 600), ("one event", 1400, 420)):
        c = cost.cost(model, i, o)
        print(f"   {model:20s} {label:10s} {i} in / {o} out → ${c.dollars:.5f} "
              f"= {c.cents:.3f}¢")

print("\n### per subscriber per month, at cadence (sonnet-5, 'one event' shape)")
unit = cost.cost("claude-sonnet-5", 1400, 420).dollars
unit_haiku = cost.cost("claude-haiku-4-5", 1400, 420).dollars
unit_day = cost.cost("claude-sonnet-5", 2400, 600).dollars
US_NET, EU_NET = 8.99, 7.33
CEILING = 3.50
CHAT = 40 * 0.0472   # the subscriber's advertised 40 chat turns
print(f"  subscriber month ceiling (cost.month_ceiling): ${CEILING:.2f}")
print(f"  already committed: 40 chat turns × $0.0472 = ${CHAT:.2f}")
print(f"  headroom left for a daily: ${CEILING - CHAT:.2f}")
print(f"\n{'cadence':>22s} {'/mo':>5s} {'sonnet':>9s} {'%US':>6s} {'%EU':>6s} "
      f"{'haiku':>9s} {'%US':>6s} {'fits ceiling?':>14s}")
for label, per_month in (
    ("every day", 30), ("6×/week", 26), ("every other day", 15),
    ("2×/week", 8.7), ("weekly", 4.3), ("event-driven ≈5.5/mo", 5.5),
    ("event-driven ≈4.1/mo", 4.1), ("event-driven ≈2.9/mo", 2.9),
):
    s = unit * per_month
    hk = unit_haiku * per_month
    fits = "yes" if CHAT + s <= CEILING else "NO"
    print(f"{label:>22s} {per_month:5.1f} ${s:8.4f} {100*s/US_NET:5.1f}% "
          f"{100*s/EU_NET:5.1f}% ${hk:8.4f} {100*hk/US_NET:5.1f}% {fits:>14s}")

print("\n### whole-day shape (SHAPE A), same table")
for label, per_month in (("every day", 30), ("every other day", 15), ("weekly", 4.3)):
    s = unit_day * per_month
    fits = "yes" if CHAT + s <= CEILING else "NO"
    print(f"{label:>22s} {per_month:5.1f} ${s:8.4f} {100*s/US_NET:5.1f}% "
          f"{100*s/EU_NET:5.1f}%  ceiling: {fits}")

print("\n### the kernel-cache idea, priced")
KERNELS = 570          # measured over a 24-chart cohort
LOCALES = 6
print(f"  {KERNELS} distinct (transiting, aspect, natal) kernels seen in a "
      f"24-chart cohort")
print(f"  full vocabulary bound: 10 × 16 × 5 = 800 (with retro/direct: 1600)")
for model, per in (("claude-sonnet-5", cost.cost("claude-sonnet-5", 1200, 500).dollars),
                   ("claude-opus-5", cost.cost("claude-opus-5", 1200, 500).dollars)):
    print(f"  writing all 800 × {LOCALES} locales once on {model}: "
          f"${800 * LOCALES * per:.2f}  (one-off)")
print(f"  amortised over 1000 subscribers: "
      f"${800*LOCALES*cost.cost('claude-sonnet-5',1200,500).dollars/1000:.4f} each, one-off")
