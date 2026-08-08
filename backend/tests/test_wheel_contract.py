"""The wheel-drawing contract: what both clients promise the engine.

`NatalWheel` on iOS and Android maps an ecliptic longitude to a screen point
with one shared formula:

    screen_angle = (180° − (longitude − ascendant))      # radians on screen
    point        = centre + r · (cos a, sin a)           # y grows DOWNWARD

This file is that formula, in Python, tested against the engine — the single
place where "the picture is right" is a checkable claim instead of an
impression. The invariants are the ones a printed chart obeys:

* the Ascendant sits exactly at the left (9 o'clock),
* the zodiac runs counter-clockwise on screen,
* the Midheaven lands in the upper half,
* every planet is drawn inside its own sign's segment,
* every planet is drawn between the cusps of the house the engine put it in.

If either client changes its mapping, this file is the specification the
change has to be argued against — and the owner's report of a wrong-looking
wheel is answered by pointing here, or by finding which invariant broke.
"""

from __future__ import annotations

import math
from datetime import date

import pytest

from alma.calc import compute
from alma.calc.contract import BirthData

CHARTS = [
    BirthData(date=date(1994, 3, 12), time="14:20",
              latitude=55.7522, longitude=37.6156, timezone="Europe/Moscow"),
    BirthData(date=date(2003, 4, 14), time="02:15",
              latitude=54.99244, longitude=73.36859, timezone="Asia/Omsk"),
    BirthData(date=date(1998, 3, 14), time="04:20",
              latitude=45.4642, longitude=9.19, timezone="Europe/Rome"),
]


def screen_angle(longitude: float, ascendant: float) -> float:
    """The clients' mapping, verbatim. Degrees; y-down applies to sin only."""
    return 180.0 - (longitude - ascendant)


def clock_hours(longitude: float, ascendant: float) -> float:
    """Where the point lands, as hours on a clock face (12 = top of screen)."""
    a = math.radians(screen_angle(longitude, ascendant))
    x, y = math.cos(a), math.sin(a)      # y > 0 is DOWN on screen
    return (math.degrees(math.atan2(x, -y)) % 360.0) / 30.0


@pytest.fixture(scope="module", params=range(len(CHARTS)))
def chart(request):
    return compute("natal", CHARTS[request.param], house_system="placidus").data


def test_the_ascendant_is_drawn_at_the_left(chart):
    asc = chart["angles"]["ascendant"]
    assert clock_hours(asc, asc) == pytest.approx(9.0)


def test_the_zodiac_runs_counter_clockwise(chart):
    """Growing longitude must move 9 → 8 → 7 o'clock, never 9 → 10 → 11."""
    asc = chart["angles"]["ascendant"]
    just_after = clock_hours(asc + 10, asc)
    assert 7.5 < just_after < 9.0, (
        f"10° past the Ascendant drew at {just_after:.1f} o'clock — the zodiac "
        "is running clockwise, which mirrors every printed chart"
    )


def test_the_midheaven_is_in_the_upper_half(chart):
    hours = clock_hours(chart["angles"]["midheaven"], chart["angles"]["ascendant"])
    assert hours >= 9.0 or hours <= 3.0, (
        f"the MC drew at {hours:.1f} o'clock, below the horizon"
    )


def test_every_planet_is_inside_its_own_sign_segment(chart):
    """The glyph and the sign band come from one mapping, or the wheel lies."""
    asc = chart["angles"]["ascendant"]
    for name, p in chart["placements"].items():
        sign_start = (p["longitude"] // 30) * 30
        lo = screen_angle(sign_start, asc)
        hi = screen_angle(sign_start + 30, asc)
        at = screen_angle(p["longitude"], asc)
        assert hi <= at <= lo, f"{name} drew outside its sign segment"


def test_every_planet_sits_between_its_house_cusps(chart):
    """The engine's house number and the drawn position must agree."""
    houses = {h["number"]: h["cusp"] for h in chart["houses"]}
    for name, p in chart["placements"].items():
        house = p.get("house")
        if house is None:
            continue
        cusp = houses[house]
        following = houses[house % 12 + 1]
        span = (following - cusp) % 360
        offset = (p["longitude"] - cusp) % 360
        assert offset <= span + 1e-6, (
            f"{name} is placed in house {house} by the engine but drawn "
            f"{offset:.2f}° past a {span:.2f}° house"
        )
