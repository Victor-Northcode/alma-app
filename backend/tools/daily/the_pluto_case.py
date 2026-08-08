"""The one reading that shipped a false astronomical fact, generated again.

A live generation for a Kraków chart wrote, of the occasion
`pluto:sextile:ascendant`:

    "transiting Pluto reaches your Ascendant at 3°31′ Aries exactly, orb 0.00°"
    "Pluto crossed this same degree earlier, moving forward, and has since
     turned back"

Pluto was at 3°31′ **Aquarius**. The separation was 300° — a sextile. Pluto is
not on that Ascendant and will not be for about two centuries. The validator
passed it on the first attempt and was right to: it compares cited factor
strings against the allowed set and never reads the paragraph, so this class of
error is structurally outside what it can catch.

The prompt caused it, in two compounding ways. The aspect arrived **only as a
glyph** — and not even the right one, U+2736 SIX POINTED BLACK STAR rather than
U+26B9 SEXTILE — with the word "sextile" nowhere in the prompt. And the brief
carried **no position for the moving body at all**, so the single degree
anywhere in it was the Ascendant's. Given "orb 0.00°", one degree, and no other
candidate, "Pluto is at 3°31′ Aries" is the inference the prompt invited.

This script finds that exact contact in a real scan and writes about it again,
five times, printing what the model says and checking the arithmetic against
the ephemeris rather than against the prose. Five because one clean generation
proves nothing about an intermittent failure.

    .venv/bin/python tools/daily/the_pluto_case.py [--runs 5]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _load_env() -> None:
    path = Path(__file__).resolve().parents[2] / ".env"
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()
os.environ["ALMA_DATABASE_URL"] = f"sqlite+aiosqlite:///{tempfile.mkdtemp()}/pluto.db"
os.environ.setdefault("ALMA_JWT_SECRET", "the-pluto-case-not-the-default-secret")

from alma.ai.provider import default_provider  # noqa: E402
from alma.ai.writer import build_prompt  # noqa: E402
from alma.calc.service import chart_for  # noqa: E402
from alma.config import settings  # noqa: E402
from alma.calc.contract import BirthData  # noqa: E402
from alma.daily import selection, service, writing  # noqa: E402
from alma.engine import zodiac  # noqa: E402
from tools.daily.a_real_week import ZONE  # noqa: E402

RULE = "─" * 78

#: **Not the test fixture's birth time.** The judges' chart had an Ascendant at
#: 3°31′ Aries, which is what put it 60° from Pluto's 2026 position in early
#: Aquarius — and the fixture's 04:20 puts it at 18°21′ Gemini, which Pluto
#: never aspects. Kraków, the same date, **01:19** local gives an Ascendant of
#: 3°37′ Aries and a real `pluto:sextile:ascendant` in the scanned year, found
#: by sweeping birth times against this machine's own ephemeris rather than by
#: copying a number out of a report. Pluto is at 3°31′ Aquarius on 2026-08-31,
#: exactly as the report said, which is the check that this is the same sky.
BIRTH = BirthData(
    date=date(1978, 6, 14),
    time="01:19",
    latitude=50.0647,
    longitude=19.9450,
    timezone="Europe/Warsaw",
    place_label="Kraków, Poland",
    name="Anna",
)

#: Words that place one body *at* another. If the aspect is not a conjunction,
#: any of these next to the natal point's name is worth looking at by eye.
ON_TOP = re.compile(
    r"\b(reaches|reaching|sits on|sitting on|lands on|arrives at|meets|meeting|"
    r"conjunct|conjunction|crosses your|on your|at your)\b",
    re.IGNORECASE,
)

SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)


def sign_of(longitude: float) -> str:
    return SIGNS[int(longitude % 360 // 30)]


def misattributed(text: str, *, moving_sign: str, natal_sign: str) -> bool:
    """Is the transiting body given the natal point's sign?

    **The obvious check is wrong and it is worth saying why**, because the
    first version of this script used it and called five correct readings
    failures. A sextile is exactly 60° — two whole signs — so the two ends
    always share the same *degree within sign*: 3°37′ Aquarius and 3°37′ Aries.
    Comparing degrees alone therefore matches every correct sentence ever
    written about a sextile.

    What distinguishes the true statement from the false one is the **sign**.
    "Pluto ... 3°37′ Aquarius" is right; "Pluto ... 3°37′ Aries" is the reading
    that shipped. So this looks for the natal sign inside a short window after
    a mention of the moving body, and nothing else.
    """
    window = r"[^.]{0,80}"
    wrong = re.search(rf"\bpluto\b{window}\b{natal_sign}\b", text, re.IGNORECASE)
    if wrong is None:
        return False
    # One more guard: "Pluto sextiles your Ascendant in Aries" is correct
    # English about the *Ascendant's* sign. Only count it when the moving sign
    # is absent from the same sentence, which is the shape of the real failure.
    sentence = wrong.group(0)
    return moving_sign.lower() not in sentence.lower()


def find_contact(hits, *, transiting: str, aspect: str, natal: str):
    for hit in hits:
        if (hit.transiting, hit.aspect, hit.natal) == (transiting, aspect, natal):
            return hit
    return None


async def run(runs: int) -> None:
    chart = chart_for(BIRTH)
    provider = default_provider()
    model = settings().model_mid

    start = datetime(2026, 8, 7, tzinfo=timezone.utc)
    hits = service.hits_for(BIRTH, start=start)
    hit = find_contact(hits, transiting="pluto", aspect="sextile", natal="ascendant")

    print(RULE)
    print("THE PLUTO CASE — pluto ⚹ ascendant, generated again")
    print(RULE)
    if hit is None:
        print("this chart has no pluto:sextile:ascendant inside the scanned year;")
        print("nothing to reproduce here — run it against the chart that failed.")
        return

    from alma.daily import clock

    day = clock.local_date(hit.exact_jd, ZONE)
    occasion = selection.occasion_for([hit], on=day, zone=ZONE, floor=0.0)
    assert occasion is not None

    moving = writing.moving_longitude(occasion)
    natal = writing.natal_longitude(chart, "ascendant")
    apart = zodiac.separation(moving, natal)

    print(f"the day        : {day}  ({occasion.at:%H:%M} {occasion.zone})")
    print(f"transiting     : pluto at {zodiac.format_position(moving)}")
    print(f"natal          : ascendant at {zodiac.format_position(natal)}")
    print(f"separation     : {apart:.3f}°  — a sextile is 60°")
    print(f"weight         : {occasion.hit.weight:.2f}   orb cited: {occasion.orb:.2f}°")
    print()

    result = writing.brief(occasion, chart=chart, birth=BIRTH)
    offered = [f for f in result.factors if f.startswith("transiting")]
    prompt = build_prompt(result, writing.chapter_for("en"), offered=offered)

    print("WHAT THE PROMPT NOW CONTAINS THAT IT DID NOT")
    print(f"  the word 'sextile'          : {'sextile' in prompt.lower()}")
    print(f"  pluto's own degree          : "
          f"{zodiac.format_position(moving) in prompt}")
    print(f"  the separation in degrees   : {'60' in prompt}")
    print(f"  the sentence forbidding it  : {'DIFFERENT SIGNS' in prompt}")
    print()
    for line in result.notes:
        if "aspect is a" in line:
            print(f"  the geometry note: {line}")
    print()

    moving_sign, natal_sign = sign_of(moving), sign_of(natal)
    clean = 0
    for attempt in range(1, runs + 1):
        piece = await writing.write(
            occasion, chart=chart, birth=BIRTH,
            provider=provider, model=model, locale="en",
        )
        text = piece.teaser + " " + piece.text()

        # The check the validator structurally cannot make: does the prose give
        # Pluto the Ascendant's sign?
        wrong = misattributed(text, moving_sign=moving_sign, natal_sign=natal_sign)
        names_both = (
            moving_sign.lower() in text.lower() and natal_sign.lower() in text.lower()
        )
        on_top = bool(ON_TOP.search(text)) and "ascendant" in text.lower()
        clean += not wrong

        print(f"── run {attempt}  attempt={piece.attempts}  "
              f"{'OK' if not wrong else '*** PLUTO GIVEN THE ASCENDANT SIGN ***'}")
        print(f"   teaser: {piece.teaser}")
        for para in piece.paragraphs:
            print(f"   {para.text}")
        print(f"   [names both signs correctly: {names_both}] "
              f"[gives pluto the natal sign: {wrong}] "
              f"[placement verb near 'ascendant': {on_top}]")
        print()

    print(RULE)
    print(f"{clean}/{runs} generations state the geometry correctly")
    print(RULE)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(run(args.runs))


if __name__ == "__main__":
    main()
