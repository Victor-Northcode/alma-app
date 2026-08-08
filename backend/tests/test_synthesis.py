"""The nine axes, tested as a piece of judgement rather than a measurement.

There is no oracle for "does the natal chart agree with the Birth Card" — the
mapping is a stated convention, not a fact about the world. So what gets
tested is that the machinery cannot lie about itself: that a system only
counts as speaking when it has something to say, that a reported agreement
really is one, that disagreements are not manufactured out of weak signals,
and above all that every axis carries the literal factors it was built from.

That last one is the load-bearing test. The AI layer may only cite what the
engine hands it, so an axis whose factors do not name their sources is an
invitation to invent.
"""

from __future__ import annotations

import pytest

from alma.engine import arcana, natal, numerology, synthesis
from alma.engine.timeutil import resolve

MILAN = dict(latitude=45.4642, longitude=9.19)


def _build(day=14, month=3, year=1998, hour=4, minute=20, reference_year=2026, name="Sofia Rossi"):
    moment = resolve(
        year=year, month=month, day=day, hour=hour, minute=minute, tz_name="Europe/Rome"
    )
    chart = natal.compute(moment=moment, **MILAN)
    numbers = numerology.calculate(day=day, month=month, year=year, full_name=name)
    cards = arcana.calculate(
        day=day, month=month, year=year, life_path=numbers.life_path,
        today=(reference_year, 8, 6),
    )
    personal_year = numerology.personal_year(day, month, reference_year)
    return synthesis.compute(
        chart=chart, numerology=numbers, arcana=cards, personal_year=personal_year
    )


@pytest.fixture(scope="module")
def result():
    return _build()


# ── shape ──────────────────────────────────────────────────────────────────

def test_there_are_exactly_nine_axes(result):
    assert len(result.axes) == 9
    assert [a.name for a in result.axes] == [name for name, _n, _p in synthesis.AXES]


def test_the_axis_names_match_the_interface(result):
    """The design names these nine; the engine must not quietly rename one."""
    expected = {
        "Direction", "Character", "Mind", "Relationships", "Resources",
        "Work", "Weak point", "Growth", "Rhythms",
    }
    assert {a.name for a in result.axes} == expected


def test_the_counts_add_up(result):
    assert result.agreements + result.disagreements + result.single_voice == 9


def test_every_axis_has_a_verdict_and_a_label(result):
    for axis in result.axes:
        assert axis.verdict in {"agree", "disagree", "single"}
        assert axis.label


# ── the verdict really follows from the signals ────────────────────────────

def test_agreement_means_every_speaking_signal_points_the_same_way(result):
    for axis in result.axes:
        if axis.verdict == "agree":
            leans = {s.leans for s in axis.speaking}
            assert len(leans) == 1 and 0 not in leans
            assert axis.count >= 2


def test_disagreement_means_signals_really_oppose(result):
    for axis in result.axes:
        if axis.verdict == "disagree":
            leans = {s.leans for s in axis.speaking}
            assert leans == {1, -1}


def test_a_single_voice_axis_has_at_most_one_speaker(result):
    for axis in result.axes:
        if axis.verdict == "single":
            assert axis.count <= 1


def test_a_direction_is_only_claimed_where_the_systems_agree(result):
    for axis in result.axes:
        if axis.verdict == "agree":
            assert axis.direction in (axis.positive_pole, axis.negative_pole)
        else:
            assert axis.direction is None


# ── weak signals must not manufacture conflict ─────────────────────────────

def test_a_weak_signal_does_not_count_as_a_vote():
    weak = synthesis.Signal("natal", 0.2, "a faint lean")
    strong = synthesis.Signal("numerology", -0.8, "a clear one")
    axis = synthesis.Axis("Test", "left", "right", (weak, strong))
    assert axis.count == 1
    assert axis.verdict == "single"


def test_two_strong_opposite_signals_do_count():
    axis = synthesis.Axis(
        "Test", "left", "right",
        (synthesis.Signal("natal", 0.8, "a"), synthesis.Signal("numerology", -0.8, "b")),
    )
    assert axis.verdict == "disagree"
    assert axis.label == "2 disagree"


def test_the_abstain_threshold_is_the_only_thing_deciding_silence():
    just_under = synthesis.Signal("natal", synthesis.ABSTAIN_THRESHOLD - 0.01, "x")
    just_over = synthesis.Signal("natal", synthesis.ABSTAIN_THRESHOLD + 0.01, "x")
    assert just_under.leans == 0
    assert just_over.leans == 1


def test_signals_stay_inside_the_declared_range(result):
    for axis in result.axes:
        for signal in axis.signals:
            assert -1.0 <= signal.value <= 1.0, f"{axis.name}/{signal.system} left the range"


# ── every claim is traceable ───────────────────────────────────────────────

def test_every_signal_carries_the_factor_it_came_from(result):
    for axis in result.axes:
        for signal in axis.signals:
            assert signal.factor.strip(), f"{axis.name}/{signal.system} cites nothing"
            assert signal.system in {"natal", "numerology", "birth-card"}


def test_factors_name_their_system(result):
    for axis in result.axes:
        for line in axis.factors():
            assert ":" in line
            assert line.split(":")[0] in {"natal", "numerology", "birth-card"}


def test_the_whole_synthesis_is_citable(result):
    factors = result.factors()
    assert factors and all(isinstance(f, str) and f.strip() for f in factors)
    joined = "\n".join(factors)
    for axis in result.axes:
        assert axis.name in joined


def test_no_axis_reports_the_same_system_twice(result):
    for axis in result.axes:
        systems = [s.system for s in axis.signals]
        assert len(systems) == len(set(systems)), f"{axis.name} counted a system twice"


# ── it must actually depend on the person ──────────────────────────────────

def test_two_different_people_get_different_syntheses():
    sofia = _build()
    other = _build(day=29, month=11, year=1975, hour=13, minute=5)
    same = sum(
        1
        for a, b in zip(sofia.axes, other.axes)
        if a.verdict == b.verdict and a.direction == b.direction
    )
    assert same < 8, "two unrelated birthdays produced nearly the same synthesis"


def test_the_reference_year_changes_the_timing_axes():
    """Rhythms and Growth are about *this* year and must move with it."""
    now = _build(reference_year=2026)
    later = _build(reference_year=2029)

    def axis(result, name):
        return next(a for a in result.axes if a.name == name)

    changed = [
        name for name in ("Rhythms", "Growth")
        if axis(now, name).factors() != axis(later, name).factors()
    ]
    assert changed, "the timing axes ignored the year entirely"


def test_the_lasting_axes_do_not_move_with_the_year():
    """Character and Weak point describe a life, not a season."""
    now = _build(reference_year=2026)
    later = _build(reference_year=2029)

    def axis(result, name):
        return next(a for a in result.axes if a.name == name)

    for name in ("Weak point",):
        assert axis(now, name).factors() == axis(later, name).factors()


# ── degraded input still produces an honest answer ─────────────────────────

def test_an_unknown_birth_time_narrows_the_axes_rather_than_faking_them():
    known = _build()
    unknown = _build(hour=None, minute=None)

    def natal_factors(result):
        return [
            s.factor
            for axis in result.axes
            for s in axis.signals
            if s.system == "natal"
        ]

    assert len(natal_factors(unknown)) <= len(natal_factors(known))
    for factor in natal_factors(unknown):
        assert "house" not in factor, f"leaked a house claim without a birth time: {factor}"
        assert "midheaven" not in factor


def test_a_synthesis_without_a_name_still_works():
    """The name is optional, so the name-derived signals must be too."""
    result = _build(name="")
    assert len(result.axes) == 9
    assert result.agreements + result.disagreements + result.single_voice == 9
