"""Placidus is verified against its own definition, not against another library.

A Placidus cusp is the ecliptic degree whose hour angle equals a fixed
fraction of its own semi-arc. If our solver is right, measuring that fraction
back out of the answer must return 1/3 and 2/3. This catches sign errors,
quadrant errors and non-convergence in a way that eyeballing numbers cannot —
and it is the only verification available to us now that comparing against
Swiss Ephemeris is off the table on licence grounds.
"""

from __future__ import annotations

import math

import pytest

from alma.engine import houses as H
from alma.engine.ephemeris import true_obliquity
from alma.engine.timeutil import resolve

# lat, lon, tz, and a date — deliberately spread across hemispheres and seasons.
PLACES = [
    ("Milan", 45.4642, 9.1900, "Europe/Rome", 1998, 3, 14, 4, 20),
    ("Quito", -0.1807, -78.4678, "America/Guayaquil", 1990, 9, 2, 6, 0),
    ("Sydney", -33.8688, 151.2093, "Australia/Sydney", 2010, 7, 4, 16, 15),
    ("Reykjavik", 64.1466, -21.9426, "Atlantic/Reykjavik", 1966, 12, 21, 23, 30),
    ("Nairobi", -1.2921, 36.8219, "Africa/Nairobi", 1984, 5, 9, 11, 45),
]


def _setup(place):
    _name, lat, lon, tz, y, mo, d, h, mi = place
    moment = resolve(year=y, month=mo, day=d, hour=h, minute=mi, tz_name=tz)
    jd = moment.julian_day_utc
    from alma.engine.ephemeris import _skyfield_time  # internal on purpose

    tt = _skyfield_time(jd).tt
    ang = H.angles(jd, tt, lat, lon)
    return ang, lat, tt


@pytest.mark.parametrize("place", PLACES, ids=lambda p: p[0])
def test_first_and_tenth_cusps_are_the_angles(place):
    """Houses 1 and 10 are the Ascendant and the Midheaven by construction."""
    ang, lat, _tt = _setup(place)
    cusps = H.compute(ang, lat).cusps
    assert _sep(cusps[0], ang.ascendant) < 1e-9
    assert _sep(cusps[9], ang.midheaven) < 1e-9


@pytest.mark.parametrize("place", PLACES, ids=lambda p: p[0])
def test_placidus_cusps_trisect_their_own_semi_arc(place):
    """The defining property: recover 1/3 and 2/3 from the solved cusps."""
    ang, lat, tt = _setup(place)
    result = H.compute(ang, lat)
    if result.system != "placidus":
        pytest.skip(f"Placidus undefined here: {result.fallback_reason}")

    eps = true_obliquity(tt)
    expected = {10: (1 / 3, False), 11: (2 / 3, False), 1: (2 / 3, True), 2: (1 / 3, True)}

    for index, (fraction, nocturnal) in expected.items():
        lon = result.cusps[index]
        dec = H._declination_of_ecliptic_point(lon, eps)
        ad = H.ascensional_difference(dec, lat)
        semi_arc = (90.0 - ad) if nocturnal else (90.0 + ad)

        ra = _right_ascension_of(lon, eps)
        hour_angle = (ra - ang.ramc) % 360.0
        if nocturnal:
            hour_angle = (180.0 - hour_angle) % 360.0
            if hour_angle > 180.0:
                hour_angle -= 360.0

        measured = hour_angle / semi_arc
        assert measured == pytest.approx(fraction, abs=1e-6), (
            f"house {index + 1}: hour angle is {measured:.6f} of its semi-arc, "
            f"expected {fraction:.6f}"
        )


@pytest.mark.parametrize("place", PLACES, ids=lambda p: p[0])
def test_cusps_run_forward_without_gaps(place):
    """Twelve cusps in zodiacal order covering exactly 360°."""
    ang, lat, _tt = _setup(place)
    cusps = H.compute(ang, lat).cusps
    spans = [(cusps[(i + 1) % 12] - cusps[i]) % 360.0 for i in range(12)]
    assert all(s > 0.0 for s in spans), "a cusp ran backwards"
    assert sum(spans) == pytest.approx(360.0, abs=1e-7)


def test_polar_latitude_falls_back_and_says_so():
    """Above the polar circle Placidus is undefined — we substitute, loudly."""
    moment = resolve(year=1975, month=6, day=21, hour=2, minute=0, tz_name="Europe/Oslo")
    from alma.engine.ephemeris import _skyfield_time

    jd = moment.julian_day_utc
    ang = H.angles(jd, _skyfield_time(jd).tt, 69.6496, 18.9560)
    result = H.compute(ang, 69.6496)

    assert result.system == "porphyry"
    assert result.requested_system == "placidus"
    assert result.fallback_reason and "undefined" in result.fallback_reason
    # The substitute still has to be a valid house circle.
    spans = [(result.cusps[(i + 1) % 12] - result.cusps[i]) % 360.0 for i in range(12)]
    assert sum(spans) == pytest.approx(360.0, abs=1e-7)


def _sep(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def _right_ascension_of(lon_deg: float, eps: float) -> float:
    lon = math.radians(lon_deg)
    ra = math.degrees(math.atan2(math.sin(lon) * math.cos(eps), math.cos(lon))) % 360.0
    return ra
