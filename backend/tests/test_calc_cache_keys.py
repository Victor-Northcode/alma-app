"""What a cache key is allowed to depend on, and what it must not.

A key that carries too little serves January's transits in June. A key that
carries too much is quieter and more expensive: it drifts under a result that
has not changed, so the calculation is redone and — since `Reading.calc_key`
is how a written chapter is matched — the chapter is written again on the
paid model. The archive is sold as "written once, yours forever", so a key
that moves on a day the answer does not is a refund waiting to happen.

Every test here asserts against the *definition* rather than against the
implementation: the keys of two moments must be equal exactly when the
results computed for those two moments are equal. freezegun is not installed
and is not worth a dependency, so the clock is moved by passing the reference
explicitly — which is the shape every caller in `api/routers` already uses.
"""

from __future__ import annotations

import inspect
from datetime import date, datetime, timedelta, timezone

import pytest

from alma.calc import BirthData, SYSTEMS, compute
from alma.calc.cache import TIME_DEPENDENT, TIME_SCOPE, key_for
from alma.calc.contract import cache_key

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

#: Sofia's birthday is 14 March, so none of these three boundaries coincide.
MIDNIGHT = (
    datetime(2026, 6, 30, 23, 59, 59, tzinfo=timezone.utc),
    datetime(2026, 7, 1, 0, 0, 1, tzinfo=timezone.utc),
)
NEW_YEAR = (
    datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
    datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
)
BIRTHDAY = (
    datetime(2026, 3, 13, 23, 59, 59, tzinfo=timezone.utc),
    datetime(2026, 3, 14, 0, 0, 1, tzinfo=timezone.utc),
)


def _days(first: date, last: date):
    day = first
    while day <= last:
        yield day
        day += timedelta(days=1)


def _transitions(system: str, birth: BirthData, first: date, last: date) -> set[date]:
    """The days on which the key for `system` changes, over a closed range."""
    moved: set[date] = set()
    previous = None
    for day in _days(first, last):
        key = key_for(system, birth, {"reference": day})
        if previous is not None and key != previous:
            moved.add(day)
        previous = key
    return moved


# ── the table itself ───────────────────────────────────────────────────────

def test_the_table_covers_only_real_systems():
    assert set(TIME_SCOPE) <= set(SYSTEMS)
    assert TIME_DEPENDENT == frozenset(TIME_SCOPE)


def test_the_table_agrees_with_the_builders_about_who_reads_a_clock():
    """The engine decides this, not the cache.

    A builder that accepts a reference moment has an answer that moves; one
    that does not, cannot. If someone gives `natal_result` a `reference`
    argument, this fails on the same commit rather than a month later when a
    natal chapter starts regenerating.
    """
    from alma.calc import service

    for system, builder in service._BUILDERS.items():
        takes_a_moment = bool(
            set(inspect.signature(builder).parameters) & {"reference", "start", "year"}
        )
        assert takes_a_moment == (system in TIME_SCOPE), system


# ── systems that never consult a clock ─────────────────────────────────────

@pytest.mark.parametrize(
    "system, options",
    [
        ("natal", {"house_system": "placidus"}),
        ("astrocartography", {"house_system": "placidus", "include_parans": True}),
    ],
)
def test_a_dateless_system_gets_no_stamp_at_all(system, options):
    """Nothing about today may reach a key for an answer fixed at birth."""
    assert key_for(system, SOFIA, options) == cache_key(system, SOFIA, **options)


def test_a_partner_is_folded_in_by_fingerprint_and_nothing_else():
    assert key_for("compatibility", SOFIA, {"other": LUCAS}) == cache_key(
        "compatibility", SOFIA, other=LUCAS.fingerprint()
    )
    assert key_for("compatibility", SOFIA, {"other": LUCAS}) != key_for(
        "compatibility", SOFIA, {"other": SOFIA}
    )


# ── the key moves exactly when the answer moves ────────────────────────────

@pytest.mark.parametrize("system", ["numerology", "birth-card", "synthesis"])
@pytest.mark.parametrize(
    "boundary, moment",
    [("midnight", MIDNIGHT), ("new year", NEW_YEAR), ("birthday", BIRTHDAY)],
)
def test_two_moments_share_a_key_exactly_when_they_share_an_answer(
    system, boundary, moment
):
    """The whole doctrine of this file in one assertion.

    Computed, not asserted from a table: whatever the engine does on either
    side of the boundary is the truth, and the key has to agree with it in
    both directions. A key that changes without the answer changing is a
    chapter rewritten for nothing; a key that holds still while the answer
    moves is a stale reading served as fresh.
    """
    before, after = moment
    same_key = key_for(system, SOFIA, {"reference": before}) == key_for(
        system, SOFIA, {"reference": after}
    )
    same_answer = (
        compute(system, SOFIA, reference=before.date()).data
        == compute(system, SOFIA, reference=after.date()).data
    )
    assert same_key == same_answer, (
        f"{system} across {boundary}: key {'held' if same_key else 'moved'} "
        f"while the answer {'held' if same_answer else 'moved'}"
    )


# ── birth card: one key per birthday-to-birthday period ────────────────────

def test_a_birth_card_key_survives_midnight():
    before, after = MIDNIGHT
    assert key_for("birth-card", SOFIA, {"reference": before}) == key_for(
        "birth-card", SOFIA, {"reference": after}
    )


def test_a_birth_card_key_survives_new_year():
    """The Year Card runs birthday to birthday, so 1 January is a normal day.

    This is the case the old day-stamped key got most obviously wrong: the
    calendar rolled, the card did not, and the chapter was rewritten anyway.
    """
    before, after = NEW_YEAR
    assert key_for("birth-card", SOFIA, {"reference": before}) == key_for(
        "birth-card", SOFIA, {"reference": after}
    )


def test_a_birth_card_key_moves_on_the_birthday_and_on_no_other_day():
    assert _transitions("birth-card", SOFIA, date(2025, 1, 1), date(2026, 12, 31)) == {
        date(2025, 3, 14),
        date(2026, 3, 14),
    }


def test_the_birthday_boundary_follows_the_subject_not_the_calendar():
    """Lucas was born on 2 July; his card must turn over then, not in March."""
    assert _transitions("birth-card", LUCAS, date(2026, 1, 1), date(2026, 12, 31)) == {
        date(2026, 7, 2)
    }


# ── synthesis: two clocks, so two stamps ───────────────────────────────────

def test_a_synthesis_key_survives_an_ordinary_midnight():
    before, after = MIDNIGHT
    assert key_for("synthesis", SOFIA, {"reference": before}) == key_for(
        "synthesis", SOFIA, {"reference": after}
    )


def test_a_synthesis_key_moves_on_both_of_the_days_it_reads():
    """The Year Card turns on the birthday, the personal year on 1 January.

    Stamping only one of the two would serve a stale axis for up to a year,
    and the axis would still be cited as a fact.
    """
    assert _transitions("synthesis", SOFIA, date(2025, 1, 1), date(2026, 12, 31)) == {
        date(2025, 3, 14),
        date(2026, 1, 1),
        date(2026, 3, 14),
    }


# ── numerology: genuinely daily, because a personal day is ─────────────────

def test_a_numerology_key_moves_every_midnight_because_its_answer_does():
    """Not a concession to convenience — the builder emits a personal day.

    `numerology_result` chains personal day off personal month off personal
    year and lists all three in `factors`, so a key that held still overnight
    would let the AI assert yesterday's personal day as today's. The cost of
    that honesty is that all five numerology chapters regenerate daily even
    though four of them are fixed at birth; the fix for that belongs in
    `service.py`, not here.
    """
    days = list(_days(date(2026, 1, 1), date(2026, 12, 31)))
    keys = {key_for("numerology", SOFIA, {"reference": day}) for day in days}
    assert len(keys) == len(days)


# ── transits: day resolution, deliberately ─────────────────────────────────

def test_transits_are_one_entry_per_day_and_a_new_entry_per_day():
    morning = key_for("transits", SOFIA, {"start": datetime(2026, 6, 1, 9, tzinfo=timezone.utc)})
    evening = key_for("transits", SOFIA, {"start": datetime(2026, 6, 1, 21, tzinfo=timezone.utc)})
    tomorrow = key_for("transits", SOFIA, {"start": datetime(2026, 6, 2, 9, tzinfo=timezone.utc)})
    assert morning == evening
    assert morning != tomorrow


def test_the_window_length_is_part_of_the_transit_key():
    """120 days of transits is not a prefix of 365 — it is a different answer."""
    short = key_for("transits", SOFIA, {"start": datetime(2026, 6, 1, tzinfo=timezone.utc), "days": 120})
    long = key_for("transits", SOFIA, {"start": datetime(2026, 6, 1, tzinfo=timezone.utc), "days": 365})
    assert short != long


# ── solar return: one per calendar year ────────────────────────────────────

def test_a_solar_return_key_is_the_year_and_nothing_finer():
    assert key_for("solar-return", SOFIA, {"year": 2026}) != key_for(
        "solar-return", SOFIA, {"year": 2027}
    )
    assert key_for("solar-return", SOFIA, {"year": 2026, "latitude": 51.5}) != key_for(
        "solar-return", SOFIA, {"year": 2026, "latitude": None}
    )


def test_asking_for_this_year_explicitly_hits_the_same_entry_as_not_asking():
    """`solar_return_result` defaults to the current UTC year; so must the key.

    Two entries for one answer is how a cache quietly stops paying for
    itself — the API sends the year, a background job does not, and each
    recomputes what the other already has.
    """
    now_year = datetime.now(timezone.utc).year
    assert key_for("solar-return", SOFIA, {"year": now_year}) == key_for(
        "solar-return", SOFIA, {}
    )


def test_omitting_the_reference_means_today_for_a_daily_system():
    today = datetime.now(timezone.utc).date()
    assert key_for("numerology", SOFIA, {"reference": today}) == key_for(
        "numerology", SOFIA, {}
    )


# ── the moment never survives alongside its stamp ──────────────────────────

@pytest.mark.parametrize(
    "system, first, second",
    [
        ("birth-card", {"reference": date(2026, 6, 30)}, {"reference": date(2026, 7, 1)}),
        ("synthesis", {"reference": date(2026, 6, 30)}, {"reference": date(2026, 7, 1)}),
    ],
)
def test_the_raw_reference_is_consumed_rather_than_carried(system, first, second):
    """Leaving `reference` in the key would reintroduce the drift under it."""
    assert key_for(system, SOFIA, first) == key_for(system, SOFIA, second)


def test_a_reference_we_cannot_read_is_refused_rather_than_guessed():
    """Falling back to `now()` is how a typo becomes an invisible daily miss."""
    with pytest.raises(TypeError, match="date or datetime"):
        key_for("birth-card", SOFIA, {"reference": "2026-08-06"})
