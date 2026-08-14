"""The solar return is a root, so the root is what gets checked.

The definition is exact and unforgiving: at the return instant the Sun's
apparent longitude equals its natal longitude. Everything else in the chart
follows from that one number, which makes it the only thing worth asserting
directly — and the reason the return is refused outright when the birth time
is unknown.
"""

from __future__ import annotations

import pytest

from alma.engine import ephemeris, natal, solar_return
from alma.engine.timeutil import resolve

MILAN = dict(latitude=45.4642, longitude=9.19)


def _moment(**overrides):
    params = dict(year=1998, month=3, day=14, hour=4, minute=20, tz_name="Europe/Rome")
    params.update(overrides)
    return resolve(**params)


@pytest.fixture(scope="module")
def chart():
    return natal.compute(moment=_moment(), **MILAN)


@pytest.mark.parametrize("year", [2020, 2026, 2031, 2044])
def test_the_sun_really_returns(chart, year):
    """At the return instant the Sun is back where it started, to the arcsecond."""
    moment = _moment()
    result = solar_return.compute(natal_chart=chart, birth_moment=moment, year=year)
    natal_sun = chart.placements["sun"].longitude
    return_sun = float(ephemeris.longitudes("sun", [result.return_jd])[0])
    error = abs((return_sun - natal_sun + 180.0) % 360.0 - 180.0) * 3600.0
    assert error < 0.1, f"the {year} return is {error:.3f}\" off the natal Sun"


def test_the_return_lands_near_the_birthday(chart):
    """A return is always within a couple of days of the anniversary."""
    result = solar_return.compute(natal_chart=chart, birth_moment=_moment(), year=2026)
    assert result.return_utc.month == 3
    assert 12 <= result.return_utc.day <= 16


def test_consecutive_returns_are_one_tropical_year_apart(chart):
    """365.2422 days, give or take the hours the Earth's orbit is not circular."""
    moment = _moment()
    first = solar_return.compute(natal_chart=chart, birth_moment=moment, year=2026)
    second = solar_return.compute(natal_chart=chart, birth_moment=moment, year=2027)
    gap = second.return_jd - first.return_jd
    assert 365.0 < gap < 365.5, f"consecutive returns are {gap:.4f} days apart"


def test_the_return_chart_carries_the_natal_sun(chart):
    result = solar_return.compute(natal_chart=chart, birth_moment=_moment(), year=2026)
    assert result.chart.placements["sun"].longitude == pytest.approx(
        chart.placements["sun"].longitude, abs=1e-5
    )
    assert result.chart.sun_sign() == chart.sun_sign()


# ── relocation ─────────────────────────────────────────────────────────────

def test_relocating_moves_the_angles_but_not_the_instant(chart):
    """The Sun returns at the same moment everywhere; only the horizon differs."""
    moment = _moment()
    home = solar_return.compute(natal_chart=chart, birth_moment=moment, year=2026)
    away = solar_return.compute(
        natal_chart=chart, birth_moment=moment, year=2026,
        latitude=-33.8688, longitude=151.2093,   # Sydney
    )
    assert away.return_jd == pytest.approx(home.return_jd)
    assert away.relocated is True
    assert home.relocated is False
    assert away.chart.angles.ascendant != pytest.approx(home.chart.angles.ascendant)
    for body in natal.CHART_BODIES:
        assert away.chart.placements[body].longitude == pytest.approx(
            home.chart.placements[body].longitude
        )


# ── the unknown-time refusal ───────────────────────────────────────────────

def test_a_solar_return_is_refused_without_a_birth_time():
    """Six hours of uncertainty is a whole quadrant of the return Ascendant."""
    timeless = natal.compute(moment=_moment(hour=None, minute=None), **MILAN)
    with pytest.raises(solar_return.BirthTimeRequired):
        solar_return.compute(
            natal_chart=timeless, birth_moment=_moment(hour=None, minute=None), year=2026
        )


# ── derived readings ───────────────────────────────────────────────────────

def test_the_year_ruler_is_the_ruler_of_the_return_ascendant(chart):
    from alma.engine import zodiac

    result = solar_return.compute(natal_chart=chart, birth_moment=_moment(), year=2026)
    rising = zodiac.sign_of(result.chart.angles.ascendant)
    traditional, modern = zodiac.SIGN_RULERS[rising]
    assert result.year_ruler == (modern or traditional)


def test_angular_bodies_really_sit_on_an_angle(chart):
    from alma.engine import zodiac

    result = solar_return.compute(natal_chart=chart, birth_moment=_moment(), year=2026)
    angles = (
        result.chart.angles.ascendant, result.chart.angles.midheaven,
        result.chart.angles.descendant, result.chart.angles.imum_coeli,
    )
    for body in result.angular_bodies:
        longitude = result.chart.placements[body].longitude
        assert min(zodiac.separation(longitude, a) for a in angles) <= 8.0


def test_factors_are_usable_strings(chart):
    result = solar_return.compute(natal_chart=chart, birth_moment=_moment(), year=2026)
    factors = result.factors()
    assert factors and all(isinstance(f, str) and f.strip() for f in factors)
    assert any("solar return 2026" in f for f in factors)


@pytest.mark.parametrize("year", [2023, 2024, 2025, 2026])
def test_a_leap_day_birth_gets_its_year_chart(year):
    """29 February has no anniversary in three years out of four.

    `birthday.replace(year=…)` raised `ValueError: day is out of range for
    month` for every common year, so a person born on a leap day lost the
    solar return three years in four — the whole system, not a field of it.

    The anniversary is only the centre of a ±5-day bracket around a crossing
    the Sun makes regardless of the calendar, so the assertion is the same one
    the rest of this file makes: the Sun is back where it started.
    """
    moment = resolve(year=2000, month=2, day=29, hour=12, minute=0, tz_name="Europe/Rome")
    leap_chart = natal.compute(moment=moment, **MILAN)
    result = solar_return.compute(natal_chart=leap_chart, birth_moment=moment, year=year)

    natal_sun = leap_chart.placements["sun"].longitude
    return_sun = float(ephemeris.longitudes("sun", [result.return_jd])[0])
    error = abs((return_sun - natal_sun + 180.0) % 360.0 - 180.0) * 3600.0
    assert error < 0.1, f"the {year} return is {error:.3f}\" off the natal Sun"
