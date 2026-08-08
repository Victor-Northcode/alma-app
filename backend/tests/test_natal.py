"""The assembled natal chart, checked for internal consistency.

The parts were already verified separately — the ephemeris against JPL, the
houses against the Placidus definition, the node against its own geometry.
What is left to prove is that composing them does not introduce a lie: that
houses agree with cusps, that aspects agree with longitudes, that the sect
agrees with the horizon, and above all that an unknown birth time removes
every time-dependent claim instead of quietly guessing one.
"""

from __future__ import annotations

import math

import pytest

from alma.engine import natal, zodiac
from alma.engine.houses import house_of
from alma.engine.timeutil import resolve

# Milan, 14 March 1998, 04:20 — the reference birth the design fixtures use.
MILAN = dict(latitude=45.4642, longitude=9.1900)


def _moment(hour=4, minute=20, *, tz="Europe/Rome", year=1998, month=3, day=14):
    return resolve(year=year, month=month, day=day, hour=hour, minute=minute, tz_name=tz)


def _chart(**overrides):
    params = dict(moment=_moment(), **MILAN)
    params.update(overrides)
    return natal.compute(**params)


@pytest.fixture(scope="module")
def chart():
    return _chart()


# ── composition ────────────────────────────────────────────────────────────

def test_every_body_is_present(chart):
    for body in natal.CHART_BODIES:
        assert body in chart.placements
    for point in natal.DERIVED_POINTS:
        assert point in chart.placements


def test_placements_agree_with_their_own_longitudes(chart):
    for placement in chart.placements.values():
        assert placement.sign == zodiac.sign_of(placement.longitude)
        assert placement.degree_in_sign == pytest.approx(placement.longitude % 30.0)
        assert placement.retrograde == (placement.speed < 0)


def test_houses_agree_with_the_cusps(chart):
    """A body's house must be the one its longitude actually falls in."""
    assert chart.house_cusps is not None
    for placement in chart.placements.values():
        assert placement.house == house_of(placement.longitude, chart.house_cusps)


def test_aspects_agree_with_the_longitudes(chart):
    """Every reported aspect must survive being recomputed from scratch."""
    for aspect in chart.aspects:
        first = _longitude(chart, aspect.first)
        second = _longitude(chart, aspect.second)
        gap = zodiac.separation(first, second)
        assert abs(gap - aspect.angle) == pytest.approx(aspect.orb, abs=1e-9)


def _longitude(chart, name: str) -> float:
    if name == "ascendant":
        return chart.angles.ascendant
    if name == "midheaven":
        return chart.angles.midheaven
    return chart.placements[name].longitude


def test_no_pair_is_aspected_twice(chart):
    pairs = [frozenset((a.first, a.second)) for a in chart.aspects]
    assert len(pairs) == len(set(pairs))


def test_the_two_nodes_are_not_aspected_to_each_other(chart):
    """They are one axis measured two ways; their conjunction says nothing."""
    for aspect in chart.aspects:
        assert {aspect.first, aspect.second} != {"true_node", "mean_node"}


def test_the_nodes_stay_within_two_degrees_of_each_other(chart):
    """True and mean node differ by at most ~1.6° — a cross-check on both."""
    gap = zodiac.separation(
        chart.placements["true_node"].longitude,
        chart.placements["mean_node"].longitude,
    )
    assert gap < 2.0


# ── derived points ─────────────────────────────────────────────────────────

def test_sect_matches_the_sun_relative_to_the_horizon(chart):
    """A day birth means the Sun sits in houses 7 through 12."""
    sun_house = chart.placements["sun"].house
    expected = "day" if 7 <= sun_house <= 12 else "night"
    assert chart.sect == expected


def test_part_of_fortune_follows_its_formula(chart):
    asc = chart.angles.ascendant
    sun = chart.placements["sun"].longitude
    moon = chart.placements["moon"].longitude
    expected = (asc + moon - sun) if chart.sect == "day" else (asc + sun - moon)
    assert chart.part_of_fortune == pytest.approx(expected % 360.0)


def test_part_of_fortune_keeps_its_distance_from_the_ascendant():
    """The Moon's distance from the Sun equals Fortune's from the Ascendant.

    That equality is the whole point of the part: it transposes the lunar
    phase onto the horizon. If it fails, the sect branch is inverted.
    """
    chart = _chart()
    moon_from_sun = (
        chart.placements["moon"].longitude - chart.placements["sun"].longitude
    ) % 360.0
    fortune_from_asc = (chart.part_of_fortune - chart.angles.ascendant) % 360.0
    if chart.sect == "day":
        assert fortune_from_asc == pytest.approx(moon_from_sun, abs=1e-9)
    else:
        assert fortune_from_asc == pytest.approx((-moon_from_sun) % 360.0, abs=1e-9)


def test_moon_phase_matches_the_elongation(chart):
    elongation = (
        chart.placements["moon"].longitude - chart.placements["sun"].longitude
    ) % 360.0
    assert chart.moon_phase["elongation"] == pytest.approx(elongation, abs=1e-4)
    assert chart.moon_phase["waxing"] == (elongation < 180.0)


def test_lunar_day_is_in_range(chart):
    assert 1 <= chart.lunar_day <= 30


# ── the unknown-time contract ──────────────────────────────────────────────

def test_an_unknown_birth_time_removes_every_time_dependent_claim():
    """No houses, no angles, no fortune, no sect — and a reason given."""
    chart = _chart(moment=_moment(hour=None, minute=None))

    assert chart.time_known is False
    assert chart.angles is None
    assert chart.house_cusps is None
    assert chart.part_of_fortune is None
    assert chart.sect is None
    assert all(p.house is None for p in chart.placements.values())
    assert any("birth time is unknown" in reason for reason in chart.unavailable)


def test_an_unknown_time_still_reports_the_sun_and_moon():
    """The bodies are still measurable; only the horizon is not."""
    chart = _chart(moment=_moment(hour=None, minute=None))
    assert chart.placements["sun"].sign
    assert chart.placements["moon"].sign
    assert chart.moon_phase["phase"]


def test_factors_never_mention_houses_when_the_time_is_unknown():
    """The AI layer may only cite these strings, so they must not lie."""
    chart = _chart(moment=_moment(hour=None, minute=None))
    for factor in chart.factors():
        assert "house" not in factor.lower(), f"leaked a house claim: {factor!r}"
        assert "ascendant" not in factor.lower()


# ── sensitivity: the chart must actually depend on its inputs ──────────────

def test_moving_the_birth_time_two_hours_moves_the_ascendant():
    """Two hours is roughly 30° of rising — a whole sign, usually more."""
    early = _chart(moment=_moment(hour=4, minute=20))
    late = _chart(moment=_moment(hour=6, minute=20))
    shift = zodiac.separation(early.angles.ascendant, late.angles.ascendant)
    assert shift > 20.0, f"the Ascendant only moved {shift:.1f}° in two hours"


def test_moving_the_birth_time_two_hours_moves_bodies_between_houses():
    early = _chart(moment=_moment(hour=4, minute=20))
    late = _chart(moment=_moment(hour=6, minute=20))
    moved = sum(
        1
        for body in natal.CHART_BODIES
        if early.placements[body].house != late.placements[body].house
    )
    assert moved >= 3, f"only {moved} bodies changed house across two hours"


def test_a_different_birth_date_changes_the_whole_chart():
    reference = _chart()
    other = _chart(moment=_moment(year=1975, month=11, day=29, hour=4, minute=20))
    same = sum(
        1
        for body in natal.CHART_BODIES
        if reference.placements[body].sign == other.placements[body].sign
    )
    assert same <= 3, "two unrelated birthdays produced nearly the same chart"


def test_longitude_changes_the_houses_but_not_the_bodies():
    """Where you were born rotates the horizon; it does not move the planets."""
    milan = _chart()
    tokyo = _chart(latitude=35.6762, longitude=139.6503)
    for body in natal.CHART_BODIES:
        assert milan.placements[body].longitude == pytest.approx(
            tokyo.placements[body].longitude
        )
    assert zodiac.separation(milan.angles.ascendant, tokyo.angles.ascendant) > 10.0


# ── the polar case ─────────────────────────────────────────────────────────

def test_a_polar_birth_falls_back_and_says_so():
    """Placidus is undefined above the polar circle; we substitute and record it."""
    chart = _chart(latitude=78.2232, longitude=15.6469)  # Longyearbyen
    assert chart.house_cusps is not None
    if chart.house_system != "placidus":
        assert chart.house_fallback
        assert "Placidus" in chart.house_fallback
        assert chart.house_fallback in chart.notes


def test_whole_sign_houses_start_at_the_ascendants_sign():
    chart = _chart(house_system="whole_sign")
    assert chart.house_system == "whole_sign"
    assert chart.house_cusps[0] == pytest.approx(
        math.floor(chart.angles.ascendant / 30.0) * 30.0
    )


# ── the citable surface ────────────────────────────────────────────────────

def test_factors_are_non_empty_strings(chart):
    factors = chart.factors()
    assert len(factors) > 25
    assert all(isinstance(f, str) and f.strip() for f in factors)


def test_factors_mention_every_body(chart):
    joined = " ".join(chart.factors())
    for body in natal.CHART_BODIES:
        assert body in joined, f"{body} is not citable"


def test_chiron_is_either_placed_or_declared_unavailable(chart):
    if "chiron" in chart.placements:
        assert chart.placements["chiron"].sign
        assert not any("chiron" in reason for reason in chart.unavailable)
    else:
        assert any("chiron" in reason for reason in chart.unavailable)


def test_the_kernel_is_recorded(chart):
    """Every chart says which ephemeris answered it — reproducibility."""
    assert chart.ephemeris_kernel.endswith(".bsp")
