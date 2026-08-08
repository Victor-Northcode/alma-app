"""Transits are claims about dates, so the dates are what get tested.

Each assertion recomputes the sky at the instant the engine named and checks
the definition directly: at `exact_jd` the separation *is* the aspect angle;
at `enters_jd` and `leaves_jd` it *is* the orb. Nothing is compared against a
second implementation, because the definition is stricter than any of them.

The retrograde cases matter most. A slow planet crossing a natal degree three
times — direct, retrograde, direct again — is the shape a whole year of a
person's life gets hung on, and a search that finds only the first pass would
look completely plausible.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from alma.engine import ephemeris, natal, transits
from alma.engine.timeutil import _julian_day, resolve

MILAN = dict(latitude=45.4642, longitude=9.19)


def _jd(year, month=1, day=1) -> float:
    return _julian_day(datetime(year, month, day, tzinfo=timezone.utc))


@pytest.fixture(scope="module")
def chart():
    moment = resolve(year=1998, month=3, day=14, hour=4, minute=20, tz_name="Europe/Rome")
    return natal.compute(moment=moment, **MILAN)


@pytest.fixture(scope="module")
def year(chart):
    return transits.scan(
        chart, start_jd=_jd(2026), end_jd=_jd(2027), reference_jd=_jd(2026, 8, 6)
    )


def _separation_at(body: str, natal_longitude: float, jd: float) -> float:
    longitude = float(ephemeris.longitudes(body, [jd])[0])
    return abs(transits._wrap180(transits._wrap180(longitude - natal_longitude)))


# ── the exact date is the whole product ────────────────────────────────────

def test_every_exact_hit_really_is_exact(chart, year):
    """At `exact_jd` the separation must equal the aspect angle."""
    points = transits.natal_points(chart)
    worst = 0.0
    for hit in year:
        longitude = float(ephemeris.longitudes(hit.transiting, [hit.exact_jd])[0])
        offset = transits._wrap180(longitude - points[hit.natal])
        error = abs(float(transits._wrap180(offset - hit.target_offset)))
        worst = max(worst, error)
    assert worst < 1e-4, f"the worst 'exact' hit is {worst * 3600:.1f}\" from exact"


def test_every_hit_lands_inside_the_requested_window(year):
    for hit in year:
        assert _jd(2026) <= hit.exact_jd <= _jd(2027)


def test_orb_boundaries_are_where_the_orb_is_reached(chart, year):
    """At `enters_jd` and `leaves_jd` the offset must equal the orb exactly."""
    points = transits.natal_points(chart)
    for hit in year:
        orb = transits.TRANSIT_ORBS[hit.transiting]
        for edge in (hit.enters_jd, hit.leaves_jd):
            if edge is None:
                continue
            longitude = float(ephemeris.longitudes(hit.transiting, [edge])[0])
            offset = transits._wrap180(longitude - points[hit.natal])
            reached = abs(float(transits._wrap180(offset - hit.target_offset)))
            assert reached == pytest.approx(orb, abs=1e-3), (
                f"{hit.transiting}/{hit.natal} boundary is at {reached:.4f}°, not {orb}°"
            )


def test_the_window_brackets_the_exact_hit(year):
    for hit in year:
        if hit.enters_jd is not None:
            assert hit.enters_jd < hit.exact_jd
        if hit.leaves_jd is not None:
            assert hit.exact_jd < hit.leaves_jd


def test_the_hit_is_inside_orb_at_exactness_and_outside_beyond_the_window(chart, year):
    points = transits.natal_points(chart)
    for hit in year[:40]:
        orb = transits.TRANSIT_ORBS[hit.transiting]
        assert _offset_from_target(hit, points, hit.exact_jd) < orb
        if hit.enters_jd is not None:
            just_before = hit.enters_jd - 0.5
            assert _offset_from_target(hit, points, just_before) > orb * 0.98


def _offset_from_target(hit, points, jd) -> float:
    longitude = float(ephemeris.longitudes(hit.transiting, [jd])[0])
    offset = transits._wrap180(longitude - points[hit.natal])
    return abs(float(transits._wrap180(offset - hit.target_offset)))


# ── retrograde passes ──────────────────────────────────────────────────────

def test_a_retrograde_planet_produces_three_passes_over_the_same_degree(chart):
    """The triple pass is the shape a year of a life is hung on.

    Neptune opposes this chart's Moon in 2026; a search that stopped at the
    first crossing would report one date and miss two, which would read
    exactly as confidently as the truth.
    """
    hits = transits.scan(
        chart, start_jd=_jd(2026), end_jd=_jd(2028), bodies=("neptune",)
    )
    passes = [
        h for h in hits
        if h.natal == "moon" and h.aspect == "opposition"
    ]
    assert len(passes) >= 3, f"expected a triple pass, found {len(passes)}"
    directions = {h.retrograde for h in passes}
    assert directions == {True, False}, "a triple pass must contain both directions"


def test_direction_is_read_at_each_hit_not_once_per_scan(chart):
    """Two passes months apart can have opposite directions — and must."""
    hits = transits.scan(chart, start_jd=_jd(2026), end_jd=_jd(2027), bodies=("pluto",))
    by_pair: dict[tuple[str, str], list[transits.Hit]] = {}
    for hit in hits:
        by_pair.setdefault((hit.natal, hit.aspect), []).append(hit)
    multi = [group for group in by_pair.values() if len(group) >= 2]
    assert multi, "no repeated contact to check direction against"
    assert any(len({h.retrograde for h in group}) == 2 for group in multi)


# ── ordering and filtering ─────────────────────────────────────────────────

def test_weight_does_not_depend_on_todays_orb(year):
    """A heavy transit that perfects in November is heavy in January too."""
    same_kind = [
        h for h in year
        if h.transiting == "saturn" and h.natal == "moon" and h.aspect == "opposition"
    ]
    if len(same_kind) >= 2:
        assert len({h.weight for h in same_kind}) == 1


def test_active_returns_only_what_is_in_orb(chart, year):
    when = _jd(2026, 8, 6)
    points = transits.natal_points(chart)
    for hit in transits.active(year, when):
        orb = transits.TRANSIT_ORBS[hit.transiting]
        assert _offset_from_target(hit, points, when) <= orb + 1e-6


def test_active_is_ordered_by_urgency(year):
    live = transits.active(year, _jd(2026, 8, 6))
    urgencies = [h.urgency for h in live]
    assert urgencies == sorted(urgencies, reverse=True)


def test_the_moon_is_excluded_unless_asked_for(chart):
    without = transits.scan(chart, start_jd=_jd(2026, 8, 1), end_jd=_jd(2026, 8, 8))
    with_moon = transits.scan(
        chart, start_jd=_jd(2026, 8, 1), end_jd=_jd(2026, 8, 8), include_moon=True
    )
    assert not any(h.transiting == "moon" for h in without)
    assert any(h.transiting == "moon" for h in with_moon)


def test_a_backwards_window_is_refused(chart):
    with pytest.raises(ValueError):
        transits.scan(chart, start_jd=_jd(2027), end_jd=_jd(2026))


# ── the unknown-time contract carries through ──────────────────────────────

def test_angles_are_not_transited_when_the_birth_time_is_unknown():
    moment = resolve(year=1998, month=3, day=14, hour=None, minute=None, tz_name="Europe/Rome")
    chart = natal.compute(moment=moment, **MILAN)
    hits = transits.scan(chart, start_jd=_jd(2026), end_jd=_jd(2027), bodies=("saturn",))
    assert not any(h.natal in ("ascendant", "midheaven") for h in hits)


# ── sanity on the sampling grid ────────────────────────────────────────────

def test_a_finer_grid_finds_the_same_hits(chart, monkeypatch):
    """If halving the step finds new contacts, the default grid is too coarse."""
    window = dict(start_jd=_jd(2026), end_jd=_jd(2026, 7, 1), bodies=("mars", "jupiter"))
    coarse = transits.scan(chart, **window)

    fine_steps = {k: v / 2 for k, v in transits.STEPS.items()}
    monkeypatch.setattr(transits, "STEPS", fine_steps)
    fine = transits.scan(chart, **window)

    def key(hit):
        return (hit.transiting, hit.natal, hit.aspect, round(hit.exact_jd, 2))

    missed = {key(h) for h in fine} - {key(h) for h in coarse}
    assert not missed, f"the default grid missed {len(missed)} contacts: {sorted(missed)[:5]}"


def test_the_moon_on_today_is_todays_moon_not_the_birth_moon(chart):
    """`sky_now` is the sky at the window's start, never at the birth.

    The Today screen prints a moon line under today's date, and it used to be
    read from the natal chart — the moon this person was born under, presented
    as tonight's. The transits result now carries `sky_now`, and this pins it
    to the right instant: the phase recomputed from the window-start ephemeris
    must match, and the birth moon (14 March 1998, a full-moon week) must not.
    """
    from datetime import date

    from alma.calc.service import transits_result
    from alma.calc.contract import BirthData
    from alma.engine import zodiac

    birth = BirthData(
        date=date(1998, 3, 14), time="04:20",
        latitude=45.4642, longitude=9.19, timezone="Europe/Rome",
    )
    start = datetime(2026, 8, 6, tzinfo=timezone.utc)
    result = transits_result(birth, start=start, days=30)
    sky_now = result.data["sky_now"]

    now = ephemeris.positions(_julian_day(start), ("sun", "moon"))
    expected = zodiac.moon_phase(now["sun"].longitude, now["moon"].longitude)
    assert sky_now["moon_phase"] == expected
    assert 1 <= sky_now["lunar_day"] <= 30

    born_under = natal.compute(
        moment=resolve(year=1998, month=3, day=14, hour=4, minute=20, tz_name="Europe/Rome"),
        **MILAN,
    ).moon_phase
    assert sky_now["moon_phase"]["phase"] != born_under["phase"]


def test_the_sun_returns_to_every_natal_point_once_a_year(chart):
    """A cheap completeness check the search cannot fake.

    The Sun conjoins each natal degree exactly once per year, never twice and
    never zero times, because it never retrogrades.
    """
    hits = transits.scan(chart, start_jd=_jd(2026), end_jd=_jd(2027), bodies=("sun",))
    conjunctions = [h for h in hits if h.aspect == "conjunction"]
    seen: dict[str, int] = {}
    for hit in conjunctions:
        seen[hit.natal] = seen.get(hit.natal, 0) + 1
    assert seen, "the Sun conjoined nothing in a whole year"
    assert all(count == 1 for count in seen.values()), seen
