"""The CalcResult contract, which everything above the engine depends on.

Most of these are boundary tests rather than astrology tests: the arithmetic
is already covered, and what can still go wrong is the handover. A numpy
scalar that survives every engine test and then fails at the JSON encoder in
production; a factor list that quietly omits a fact the AI then invents; a
cache key that ignores the reference date and serves January's transits in
June. Each of those produces a confident wrong answer rather than an error,
which is exactly the failure mode this project cannot have.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from alma.calc import BirthData, CalcResult, ENGINE_VERSION, SYSTEMS, compute, json_safe
from alma.calc.cache import MemoryCache, NullCache, compute_cached, key_for
from alma.calc.contract import cache_key
from alma.calc.service import TimeRequired

SOFIA = BirthData(
    date=date(1998, 3, 14), time="04:20",
    latitude=45.4642, longitude=9.19, timezone="Europe/Rome",
    place_label="Milan, Italy", name="Sofia Rossi",
)
LUCAS = BirthData(
    date=date(1995, 7, 2), time="18:05",
    latitude=-23.5505, longitude=-46.6333, timezone="America/Sao_Paulo",
    place_label="São Paulo, Brazil", name="Lucas Souza",
)
TIMELESS = BirthData(
    date=date(1998, 3, 14), time=None,
    latitude=45.4642, longitude=9.19, timezone="Europe/Rome",
)

REFERENCE = date(2026, 8, 6)


def _options(system: str) -> dict:
    if system == "compatibility":
        return {"other": LUCAS}
    if system == "transits":
        return {"start": datetime(2026, 8, 6, tzinfo=timezone.utc), "days": 120}
    if system == "solar-return":
        return {"year": 2026}
    if system in ("numerology", "birth-card", "synthesis"):
        return {"reference": REFERENCE}
    return {}


@pytest.fixture(scope="module")
def results():
    return {system: compute(system, SOFIA, **_options(system)) for system in SYSTEMS}


# ── every system honours the shape ─────────────────────────────────────────

def test_all_eight_systems_are_covered(results):
    assert set(results) == set(SYSTEMS)
    assert len(SYSTEMS) == 8


@pytest.mark.parametrize("system", SYSTEMS)
def test_a_result_serialises_to_json(system, results):
    """Numpy scalars pass every local assertion and fail at the encoder."""
    blob = results[system].to_json()
    revived = json.loads(blob)
    assert revived["system"] == system
    assert revived["engine_version"] == ENGINE_VERSION


@pytest.mark.parametrize("system", SYSTEMS)
def test_a_result_carries_citable_factors(system, results):
    factors = results[system].factors
    assert factors, f"{system} produced nothing citable"
    assert all(isinstance(f, str) and f.strip() for f in factors)


@pytest.mark.parametrize("system", SYSTEMS)
def test_a_result_records_how_it_was_produced(system, results):
    """A reading that cannot be reproduced cannot be defended."""
    assert results[system].provenance
    assert results[system].computed_at


@pytest.mark.parametrize("system", SYSTEMS)
def test_the_subject_is_echoed_back(system, results):
    subject = results[system].subject
    assert subject["date"] == "1998-03-14"
    assert subject["timezone"] == "Europe/Rome"
    assert subject["time_known"] is True


# ── json_safe is the thing standing between us and a 500 ───────────────────

def test_json_safe_converts_numpy_scalars():
    numpy = pytest.importorskip("numpy")
    converted = json_safe(
        {"a": numpy.float64(1.5), "b": numpy.int64(3), "c": numpy.bool_(True)}
    )
    assert converted == {"a": 1.5, "b": 3, "c": True}
    assert type(converted["a"]) is float
    assert type(converted["b"]) is int
    json.dumps(converted)


def test_json_safe_keeps_booleans_boolean():
    """bool is a subclass of int; a careless branch turns True into 1."""
    assert json_safe({"flag": True}) == {"flag": True}
    assert type(json_safe(True)) is bool


def test_json_safe_flattens_tuples_and_sets():
    assert json_safe((1, 2)) == [1, 2]
    assert sorted(json_safe({3, 1, 2})) == [1, 2, 3]


def test_json_safe_handles_dates_and_dataclasses():
    from dataclasses import dataclass

    @dataclass
    class Thing:
        when: date
        value: float

    assert json_safe(Thing(date(2026, 8, 6), 1.0)) == {"when": "2026-08-06", "value": 1.0}


def test_json_safe_stringifies_the_unknown_rather_than_raising():
    class Opaque:
        def __repr__(self):
            return "<opaque>"

    assert json_safe(Opaque()) == "<opaque>"


def test_every_result_survives_a_strict_encoder(results):
    """No default=, no NaN — if it needs coaxing it is not safe."""
    for system, result in results.items():
        try:
            json.dumps(result.as_dict(), allow_nan=False)
        except (TypeError, ValueError) as exc:
            pytest.fail(f"{system} is not strictly encodable: {exc}")


def test_no_numpy_scalar_survives_into_a_result(results):
    """Walk the whole tree — one leaked scalar is one production 500."""
    numpy = pytest.importorskip("numpy")

    def walk(node, path="") -> list[str]:
        if isinstance(node, dict):
            return [p for k, v in node.items() for p in walk(v, f"{path}.{k}")]
        if isinstance(node, list):
            return [p for i, v in enumerate(node) for p in walk(v, f"{path}[{i}]")]
        return [f"{path}: {type(node).__name__}"] if isinstance(node, numpy.generic) else []

    for system, result in results.items():
        leaked = walk(result.as_dict(), system)
        assert not leaked, f"numpy leaked into {system}: {leaked[:5]}"


# ── the unknown-time contract, end to end ──────────────────────────────────

def test_systems_that_need_a_time_refuse_rather_than_guess():
    for system in ("solar-return", "astrocartography"):
        with pytest.raises(TimeRequired):
            compute(system, TIMELESS, **_options(system))


def test_systems_that_can_degrade_do_so_and_say_why():
    result = compute("natal", TIMELESS)
    assert result.unavailable
    assert "houses" in " ".join(result.unavailable)
    assert "angles" not in result.data
    assert result.data["rising_sign"] is None
    assert result.data["time_known"] is False


def test_a_degraded_result_never_cites_what_it_does_not_have():
    result = compute("natal", TIMELESS)
    for factor in result.factors:
        assert "house" not in factor.lower()
        assert "ascendant" not in factor.lower()


def test_numerology_says_why_the_name_numbers_are_missing():
    anonymous = BirthData(
        date=date(1998, 3, 14), time="04:20",
        latitude=45.4642, longitude=9.19, timezone="Europe/Rome",
    )
    result = compute("numerology", anonymous, reference=REFERENCE)
    assert "name" not in result.data
    assert any("birth name" in reason for reason in result.unavailable)


# ── cache keys ─────────────────────────────────────────────────────────────

def test_the_same_birth_produces_the_same_key():
    assert cache_key("natal", SOFIA) == cache_key("natal", SOFIA)


def test_different_births_produce_different_keys():
    assert cache_key("natal", SOFIA) != cache_key("natal", LUCAS)


def test_a_minute_of_birth_time_changes_the_key():
    later = BirthData(
        date=SOFIA.date, time="04:21", latitude=SOFIA.latitude,
        longitude=SOFIA.longitude, timezone=SOFIA.timezone, name=SOFIA.name,
    )
    assert cache_key("natal", SOFIA) != cache_key("natal", later)


def test_options_change_the_key():
    assert cache_key("natal", SOFIA, house_system="placidus") != cache_key(
        "natal", SOFIA, house_system="whole_sign"
    )


def test_option_order_does_not_change_the_key():
    first = cache_key("natal", SOFIA, a=1, b=2)
    second = cache_key("natal", SOFIA, b=2, a=1)
    assert first == second


def test_the_engine_version_is_part_of_the_key():
    """A change to the arithmetic must strand every stored result."""
    from alma.calc import contract

    before = cache_key("natal", SOFIA)
    original = contract.ENGINE_VERSION
    try:
        contract.ENGINE_VERSION = "9.9.9"
        assert cache_key("natal", SOFIA) != before
    finally:
        contract.ENGINE_VERSION = original


def test_time_dependent_systems_carry_their_reference_date():
    """January's transits must not be served in June."""
    january = key_for("transits", SOFIA, {"start": datetime(2026, 1, 1, tzinfo=timezone.utc)})
    june = key_for("transits", SOFIA, {"start": datetime(2026, 6, 1, tzinfo=timezone.utc)})
    assert january != june


def test_the_same_day_at_a_different_hour_is_one_cache_entry():
    """Otherwise every page view is a miss and the cache is decoration."""
    morning = key_for("transits", SOFIA, {"start": datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)})
    evening = key_for("transits", SOFIA, {"start": datetime(2026, 6, 1, 21, 0, tzinfo=timezone.utc)})
    assert morning == evening


def test_a_partner_changes_the_compatibility_key():
    with_lucas = key_for("compatibility", SOFIA, {"other": LUCAS})
    with_self = key_for("compatibility", SOFIA, {"other": SOFIA})
    assert with_lucas != with_self


# ── the cache itself ───────────────────────────────────────────────────────

def test_a_cached_result_matches_the_computed_one():
    cache = MemoryCache()
    first = compute_cached("numerology", SOFIA, cache=cache, reference=REFERENCE)
    second = compute_cached("numerology", SOFIA, cache=cache, reference=REFERENCE)
    assert cache.hits == 1 and cache.misses == 1
    assert second.as_dict() == first.as_dict()


def test_the_cache_hands_out_independent_copies():
    """A caller mutating what it got back must not poison the next reader."""
    cache = MemoryCache()
    first = compute_cached("numerology", SOFIA, cache=cache, reference=REFERENCE)
    first.data["life_path"] = 999
    second = compute_cached("numerology", SOFIA, cache=cache, reference=REFERENCE)
    assert second.data["life_path"] != 999


def test_the_cache_evicts_the_least_recently_used():
    cache = MemoryCache(capacity=2)
    for index in range(4):
        cache.put(f"key{index}", compute("numerology", SOFIA, reference=REFERENCE))
    assert cache.size == 2
    assert cache.get("key0") is None
    assert cache.get("key3") is not None


def test_the_null_cache_never_hits():
    cache = NullCache()
    compute_cached("numerology", SOFIA, cache=cache, reference=REFERENCE)
    assert cache.get(key_for("numerology", SOFIA, {"reference": REFERENCE})) is None


def test_caching_actually_saves_the_expensive_work():
    """Transits are the reason the cache exists — a second must not be paid twice."""
    import time

    cache = MemoryCache()
    options = {"start": datetime(2026, 8, 6, tzinfo=timezone.utc), "days": 365}

    started = time.perf_counter()
    compute_cached("transits", SOFIA, cache=cache, **options)
    cold = time.perf_counter() - started

    started = time.perf_counter()
    compute_cached("transits", SOFIA, cache=cache, **options)
    warm = time.perf_counter() - started

    assert warm < cold / 5, f"cold {cold:.3f}s, warm {warm:.3f}s — the cache is not working"


# ── the dispatcher ─────────────────────────────────────────────────────────

def test_an_unknown_system_is_refused():
    with pytest.raises(ValueError, match="unknown system"):
        compute("astrology", SOFIA)


def test_building_a_result_for_an_unknown_system_is_refused():
    from alma.calc import build

    with pytest.raises(ValueError, match="unknown system"):
        build(system="palmistry", birth=SOFIA, data={}, factors=[])


def test_cites_finds_a_referenced_factor(results):
    result = results["numerology"]
    factor = result.factors[0]
    assert result.cites(f"Because your {factor}, the year asks for patience.")
    assert not result.cites("Because Mars is in the ninth house of a different chart.")


# ── the fingerprint ────────────────────────────────────────────────────────

def test_a_fingerprint_is_stable_across_equal_births():
    twin = BirthData(
        date=date(1998, 3, 14), time="04:20", latitude=45.4642, longitude=9.19,
        timezone="Europe/Rome", place_label="somewhere else entirely", name="Sofia Rossi",
    )
    # The label is presentation; the coordinates are the fact.
    assert twin.fingerprint() == SOFIA.fingerprint()


def test_a_fingerprint_changes_with_the_coordinates():
    moved = BirthData(
        date=SOFIA.date, time=SOFIA.time, latitude=45.4643, longitude=SOFIA.longitude,
        timezone=SOFIA.timezone, name=SOFIA.name,
    )
    assert moved.fingerprint() != SOFIA.fingerprint()


def test_hour_minute_parses_and_reports_absence():
    assert SOFIA.hour_minute == (4, 20)
    assert TIMELESS.hour_minute == (None, None)
    assert TIMELESS.time_known is False
