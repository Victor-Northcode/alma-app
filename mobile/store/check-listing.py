#!/usr/bin/env python3
"""Check every listing field in LISTING.md against its store limit — and against
the three claims that have already had to be corrected once.

A field silently truncated at 30 characters is how a German app name ends up
reading "Alma: Horoskop & 8 Syste". Run this before anything is pasted into a
console.

The content guards exist because a store review is lost on a single overstatement
and every one of these was live in this file at some point:

  1. EIGHT ON THE AXES. `backend/alma/engine/synthesis.py:355-360` builds its
     contributions dict from exactly three systems — natal, numerology,
     birth-card — so "all eight systems on nine axes" overstated the one claim
     the 4.3(b) argument rests on by 8/3. If the engine is ever widened to take
     signals from the other five, widen this guard in the same commit.
  2. A PRICE IN THE METADATA. Apple 2.3.7. Thirteen currencies also go stale.
  3. THE OTHER STORE. Apple 2.3.10 and its Play mirror.

Exit code is non-zero if any of it fails, so this is safe in a pre-commit hook.
"""
import re
import sys
from pathlib import Path

src = Path(__file__).with_name("LISTING.md").read_text(encoding="utf-8")
pattern = re.compile(
    r"<!--\s*field:\s*(?P<name>[\w.\-]+)\s*\|\s*limit:\s*(?P<limit>\d+)"
    r"(?P<unit>\s*bytes)?\s*-->\s*\n```\n(?P<body>.*?)\n```",
    re.DOTALL,
)

#: "eight" and "axes" in all six languages. Word-bounded on purpose: "weights"
#: contains "eight" and the German "gemacht" contains "acht".
EIGHT = r"\b(?:eight|ocho|acht|otto|huit|oito)\b"
AXES = r"\b(?:axes|ejes|Achsen|assi|eixos)\b"
NEAR = r"(?:\W+\w+){0,10}\W+"
SYNTHESIS_DRIFT = (
    re.compile(EIGHT + NEAR + AXES, re.I),
    re.compile(AXES + NEAR + EIGHT, re.I),
)
#: A currency figure of any shape. `€9,99`, `$5.99`, `9,99 EUR`, `R$ 38,99`.
PRICE = re.compile(r"(?:[$€£¥]|R\$|CHF|kr)\s?\d|\d+[.,]\d\d\s?(?:€|£|\$|EUR|USD|GBP)")
#: What may never appear in a body belonging to the other store.
FOREIGN = {
    "apple": re.compile(r"\b(?:android|google\s*play|play\s*store)\b", re.I),
    "play": re.compile(r"\b(?:apple|app\s*store|iphone|ipad|ios)\b", re.I),
}
#: 1.1.6 — the disclaimer that buys nothing, in every language a translator
#: would reach for it in.
ENTERTAINMENT = re.compile(
    r"entertainment purposes|fines de entretenimiento|Unterhaltungszwecken|"
    r"scopo di intrattenimento|fins de divertissement|fins de entretenimento",
    re.I,
)

bad = 0
seen = 0
notes: list[str] = []

for m in pattern.finditer(src):
    name, body, limit = m["name"], m["body"], int(m["limit"])
    size = len(body.encode("utf-8")) if m["unit"] else len(body)
    unit = "bytes" if m["unit"] else "chars"
    over = size > limit
    bad += over
    seen += 1
    print(f"{name:<28} {size:>5}/{limit} {unit}{'  <-- OVER' if over else ''}")

    for rx in SYNTHESIS_DRIFT:
        for hit in rx.finditer(body):
            notes.append(
                f"{name}: the cross-synthesis compares THREE systems, not eight "
                f"— {hit.group()[:70]!r}"
            )
    if PRICE.search(body):
        notes.append(f"{name}: a price figure (Apple 2.3.7 — no numbers in metadata)")
    store = "apple" if ".apple." in name else "play" if ".play." in name else None
    if store and (hit := FOREIGN[store].search(body)):
        notes.append(f"{name}: names the other store — {hit.group()!r} (2.3.10)")
    if hit := ENTERTAINMENT.search(body):
        notes.append(f"{name}: entertainment disclaimer — {hit.group()!r} (1.1.6)")

print(f"\n{seen} fields checked")
if notes:
    print("\nCONTENT:")
    for n in notes:
        print("  " + n)
if bad:
    print(f"\n{bad} field(s) over limit")
print("\nOK" if not (bad or notes) else "")
sys.exit(1 if (bad or notes) else 0)
