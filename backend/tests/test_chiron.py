"""Chiron comes from a sampled table, so the sampling itself needs proving.

Two separate claims are tested here. First, that the interpolation reproduces
JPL: the apparent right ascension and declination below were fetched from JPL
Horizons (geocentric, apparent of date) and are pasted in so CI needs no
network. Second, that the interpolation is not the weak link — a table
sampled twice as coarsely must land in the same place, which it only can if
the four-day grid is already far finer than necessary.

Chiron is also the one body that can legitimately be missing, so its absence
is tested as a first-class outcome rather than an error.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from alma.engine import ephemeris as E
from alma.engine import smallbody
from alma.engine.timeutil import _julian_day

#: date → (apparent RA, apparent Dec) in degrees, geocentric, equinox of date.
#: Source: JPL Horizons, target 2060 Chiron, CENTER=500@399, QUANTITIES=2.
HORIZONS_APPARENT = {
    (1998, 3, 14): (226.70093, -15.62576),
    (1930, 6, 1): (43.97430, 14.88378),
    (2026, 8, 6): (28.65234, 11.99547),
    (2075, 11, 20): (20.48019, 9.45061),
}

TOLERANCE_ARCSEC = 1.0


def _jd(year: int, month: int, day: int, hour: int = 12) -> float:
    return _julian_day(datetime(year, month, day, hour, 0, tzinfo=timezone.utc))


def _requires_table():
    if smallbody.chiron_body() is None:
        pytest.skip("Chiron table is not installed in this checkout")


@pytest.mark.parametrize("date,expected", sorted(HORIZONS_APPARENT.items()))
def test_chiron_matches_jpl_horizons(date, expected):
    _requires_table()
    ra_ref, dec_ref = expected
    jd = _jd(*date)
    eph, _ts, _ = E._loaded()
    t = E._skyfield_time(jd)
    ra, dec, _ = eph["earth"].at(t).observe(E._resolve("chiron")).apparent().radec(epoch="date")

    d_ra = (ra._degrees - ra_ref) * math.cos(math.radians(dec_ref)) * 3600.0
    d_dec = (dec.degrees - dec_ref) * 3600.0
    separation = math.hypot(d_ra, d_dec)
    assert separation < TOLERANCE_ARCSEC, (
        f"Chiron is {separation:.3f}\" from JPL on {date} — the table or the "
        "interpolation has drifted"
    )


def test_the_sampling_grid_is_far_finer_than_it_needs_to_be():
    """Dropping every other sample must not move Chiron measurably.

    If it does, the four-day grid is doing real work and the interpolation
    error is inside our answer rather than far below it.
    """
    _requires_table()
    full = smallbody.chiron_body()
    coarse = smallbody.SampledSmallBody(
        "chiron-coarse",
        smallbody.CHIRON_ID,
        full._jd[::2],
        # the table stores position and velocity side by side
        [list(p) + list(v) for p, v in zip(full._pos[::2], full._vel[::2])],
    )

    eph, _ts, _ = E._loaded()
    for date in HORIZONS_APPARENT:
        t = E._skyfield_time(_jd(*date))
        fine_ra, fine_dec, _ = eph["earth"].at(t).observe(full).apparent().radec(epoch="date")
        coarse_ra, coarse_dec, _ = eph["earth"].at(t).observe(coarse).apparent().radec(epoch="date")
        gap = math.hypot(
            (fine_ra._degrees - coarse_ra._degrees) * math.cos(math.radians(fine_dec.degrees)),
            fine_dec.degrees - coarse_dec.degrees,
        ) * 3600.0
        assert gap < 0.01, f"halving the sampling moved Chiron {gap:.4f}\" on {date}"


def test_chiron_is_refused_outside_the_tabulated_range():
    """Before 1900 and after 2100 we have no data, and we say so."""
    assert E.chiron(_jd(1850, 1, 1)) is None
    assert E.chiron(_jd(2150, 1, 1)) is None


def test_chiron_inside_the_range_answers():
    _requires_table()
    position = E.chiron(_jd(1998, 3, 14))
    assert position is not None
    assert 0.0 <= position.longitude < 360.0
    assert abs(position.latitude) < 12.0        # Chiron's inclination is ~6.9°
    assert abs(position.speed_longitude) < 0.2  # a slow body, retrograde or not


def test_a_missing_table_degrades_instead_of_raising(monkeypatch, tmp_path):
    """No table must mean 'Chiron unavailable', never a failed reading."""
    smallbody.chiron_body.cache_clear()
    monkeypatch.setenv("ALMA_CHIRON_TABLE", str(tmp_path / "absent.npz"))
    try:
        assert smallbody.chiron_body() is None
        assert E.chiron_available(_jd(1998, 3, 14)) is False
        assert E.chiron(_jd(1998, 3, 14)) is None
    finally:
        smallbody.chiron_body.cache_clear()


def test_interpolation_reproduces_the_samples_exactly():
    """Hermite interpolation is exact at the knots — a cheap sanity anchor."""
    _requires_table()
    body = smallbody.chiron_body()
    for index in (0, 1000, len(body._jd) - 1):
        position, velocity = body._interpolate(body._jd[index : index + 1])
        for axis in range(3):
            assert position[axis][0] == pytest.approx(body._pos[index][axis], abs=1e-12)
            assert velocity[axis][0] == pytest.approx(body._vel[index][axis], abs=1e-14)
