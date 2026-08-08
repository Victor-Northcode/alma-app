"""Compatibility, checked for the errors that would be invisible in prose.

The midpoint across 0° Aries is the classic one: averaging 350 and 10 puts
the composite Sun at 180°, halfway round the zodiac from where it belongs,
and every downstream sentence would still read fluently. The overlay
direction is the other: "your Moon in my seventh" and "my Moon in your
seventh" are different statements about different people, and swapping them
produces a reading that is confidently about the wrong person.
"""

from __future__ import annotations

import pytest

from alma.engine import natal, synastry, zodiac
from alma.engine.timeutil import resolve

SOFIA = dict(latitude=45.4642, longitude=9.19)
LUCAS = dict(latitude=-23.5505, longitude=-46.6333)


def _sofia_moment(**overrides):
    params = dict(year=1998, month=3, day=14, hour=4, minute=20, tz_name="Europe/Rome")
    params.update(overrides)
    return resolve(**params)


def _lucas_moment(**overrides):
    params = dict(year=1995, month=7, day=2, hour=18, minute=5, tz_name="America/Sao_Paulo")
    params.update(overrides)
    return resolve(**params)


@pytest.fixture(scope="module")
def pair():
    a_moment, b_moment = _sofia_moment(), _lucas_moment()
    a = natal.compute(moment=a_moment, **SOFIA)
    b = natal.compute(moment=b_moment, **LUCAS)
    return a, b, a_moment, b_moment


@pytest.fixture(scope="module")
def result(pair):
    a, b, a_moment, b_moment = pair
    return synastry.compute(chart_a=a, chart_b=b, moment_a=a_moment, moment_b=b_moment)


# ── the midpoint, which is where this goes wrong ───────────────────────────

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (10.0, 50.0, 30.0),
        (350.0, 10.0, 0.0),      # across 0° Aries — the trap
        (10.0, 350.0, 0.0),      # and the same the other way round
        (359.0, 1.0, 0.0),
        (100.0, 100.0, 100.0),
    ],
)
def test_midpoint_takes_the_short_way_round(a, b, expected):
    assert synastry.midpoint(a, b) == pytest.approx(expected)


def test_midpoint_is_symmetric():
    """A composite must not change depending on who is entered first."""
    for a, b in [(10.0, 50.0), (350.0, 10.0), (200.0, 20.0), (0.0, 180.0), (123.4, 271.8)]:
        assert synastry.midpoint(a, b) == pytest.approx(synastry.midpoint(b, a))


def test_the_midpoint_is_equidistant_from_both():
    for a, b in [(10.0, 50.0), (350.0, 10.0), (123.4, 271.8), (0.0, 180.0)]:
        mid = synastry.midpoint(a, b)
        assert zodiac.separation(mid, a) == pytest.approx(zodiac.separation(mid, b), abs=1e-9)


def test_an_exact_opposition_resolves_deterministically():
    """Two valid answers exist; the same one has to come back every time."""
    assert synastry.midpoint(0.0, 180.0) == pytest.approx(90.0)
    assert synastry.midpoint(180.0, 0.0) == pytest.approx(90.0)
    assert synastry.midpoint(200.0, 20.0) == pytest.approx(110.0)


def test_composite_bodies_are_the_midpoints(pair, result):
    a, b, *_ = pair
    for body in ("sun", "moon", "venus", "mars"):
        assert result.composite[body] == pytest.approx(
            synastry.midpoint(a.placements[body].longitude, b.placements[body].longitude)
        )


# ── contacts ───────────────────────────────────────────────────────────────

def test_every_contact_is_within_its_own_orb(pair, result):
    a, b, *_ = pair
    for contact in result.contacts:
        first = _longitude(a, contact.first)
        second = _longitude(b, contact.second)
        gap = zodiac.separation(first, second)
        angle = next(t.angle for t in zodiac.ASPECT_TYPES if t.name == contact.aspect)
        assert abs(gap - angle) == pytest.approx(contact.orb, abs=1e-9)


def _longitude(chart, name):
    if name == "ascendant":
        return chart.angles.ascendant
    if name == "midheaven":
        return chart.angles.midheaven
    return chart.placements[name].longitude


def test_outer_planet_pairs_are_not_reported(result):
    """Two people of an age share Uranus, Neptune and Pluto — that is a
    generation, not a relationship."""
    for contact in result.contacts:
        assert not (
            contact.first in synastry.GENERATIONAL and contact.second in synastry.GENERATIONAL
        )


def test_contacts_are_ordered_by_weight(result):
    weights = [c.weight for c in result.contacts]
    assert weights == sorted(weights, reverse=True)


def test_a_chart_compared_with_itself_is_all_conjunctions(pair):
    a, *_ = pair
    same = synastry.contacts(a, a)
    exact = [c for c in same if c.first == c.second]
    assert exact, "a chart compared with itself found no self-conjunctions"
    for contact in exact:
        assert contact.aspect == "conjunction"
        assert contact.orb == pytest.approx(0.0, abs=1e-9)


# ── overlays, which must not be swapped ────────────────────────────────────

def test_overlays_run_in_both_directions(result):
    owners = {overlay.owner for overlay in result.overlays}
    assert owners == {"a", "b"}


def test_an_overlay_really_falls_in_that_house(pair, result):
    from alma.engine.houses import house_of

    a, b, *_ = pair
    for overlay in result.overlays:
        if overlay.owner == "b":
            longitude = a.placements[overlay.body].longitude
            cusps = b.house_cusps
        else:
            longitude = b.placements[overlay.body].longitude
            cusps = a.house_cusps
        assert overlay.house == house_of(longitude, cusps)


def test_overlay_descriptions_name_the_right_person(result):
    a_owned = [o for o in result.overlays if o.owner == "a"]
    assert a_owned
    assert a_owned[0].describe().startswith("B's ")


# ── davison ────────────────────────────────────────────────────────────────

def test_davison_is_a_real_chart_at_a_real_moment(pair, result):
    a, b, a_moment, b_moment = pair
    assert result.davison is not None
    assert result.davison.time_known
    assert result.davison.angles is not None
    middle = a_moment.utc + (b_moment.utc - a_moment.utc) / 2
    from alma.engine.timeutil import _julian_day

    assert result.davison.julian_day == pytest.approx(_julian_day(middle))


def test_davison_latitude_is_the_average(pair, result):
    a, b, *_ = pair
    assert result.davison.latitude == pytest.approx((a.latitude + b.latitude) / 2)


def test_davison_longitude_takes_the_short_way_round_the_globe():
    """Tokyo and Los Angeles meet in the Pacific, not over Africa."""
    assert synastry._midpoint_longitude(139.7, -118.2) == pytest.approx(-169.25, abs=0.01)
    assert synastry._midpoint_longitude(-118.2, 139.7) == pytest.approx(-169.25, abs=0.01)


def test_davison_is_refused_when_a_birth_time_is_missing():
    a = natal.compute(moment=_sofia_moment(), **SOFIA)
    b = natal.compute(moment=_lucas_moment(hour=None, minute=None), **LUCAS)
    outcome = synastry.compute(
        chart_a=a, chart_b=b,
        moment_a=_sofia_moment(), moment_b=_lucas_moment(hour=None, minute=None),
    )
    assert outcome.davison is None
    assert any("birth times" in reason for reason in outcome.unavailable)


# ── scoring ────────────────────────────────────────────────────────────────

def test_scores_are_named_rather_than_a_single_percentage(result):
    assert set(result.scores) == {"attraction", "warmth", "friction", "endurance"}
    assert all(isinstance(v, float) for v in result.scores.values())
    assert all(v >= 0 for v in result.scores.values())


def test_scores_are_json_safe(result):
    """Numpy scalars would serialise into CalcResult and break the encoder."""
    import json

    json.dumps(result.scores)
    json.dumps({k: v for k, v in result.composite.items() if k != "balance"})


def test_factors_are_usable_strings(result):
    factors = result.factors()
    assert factors and all(isinstance(f, str) and f.strip() for f in factors)
    assert any("composite sun" in f for f in factors)
