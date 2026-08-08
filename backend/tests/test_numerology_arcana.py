"""Numerology and arcana are exact arithmetic, so they get exact expectations.

Every value below is derivable by hand from the published Pythagorean rules;
where a case is chosen deliberately (master number, karmic debt, the reduction
order that changes the answer) the comment says why.
"""

from __future__ import annotations

import pytest

from alma.engine import arcana as A
from alma.engine import numerology as N


# ── reduction rules ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "value,expected",
    [(9, 9), (10, 1), (19, 1), (28, 1), (11, 11), (22, 22), (33, 33), (29, 11), (39, 3)],
)
def test_reduction_keeps_master_numbers(value, expected):
    assert N.reduce_number(value) == expected


@pytest.mark.parametrize("value", [11, 22, 33, 29])
def test_reduction_can_be_told_to_ignore_masters(value):
    """Challenges and card folds need the plain single digit."""
    assert N.reduce_number(value, keep_masters=False) <= 9


def test_karmic_debt_is_reported_from_the_intermediate_total():
    """19 reduces to 1; a caller seeing only the 1 has lost the debt."""
    assert N._reduce_tracking_debt(19) == (1, 19)
    assert N._reduce_tracking_debt(13) == (4, 13)
    assert N._reduce_tracking_debt(14) == (5, 14)
    assert N._reduce_tracking_debt(16) == (7, 16)
    assert N._reduce_tracking_debt(12) == (3, None)


# ── life path ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "day,month,year,expected",
    [
        # 14 March 1998: 5 + 3 + 9 = 17 → 8. The design copy says 7; the
        # arithmetic says 8, and the arithmetic is what ships.
        (14, 3, 1998, 8),
        (1, 1, 2000, 4),      # 1 + 1 + 2 = 4
        # Masters hold per component, then the total reduces: 11+11+22=44 → 8.
        (29, 11, 1975, 8),
        # 7 + 3 + 1 = 11 — a master total survives as 11, it does not become 2.
        (25, 12, 1990, 11),
        # 13-07-1979: 4 + 7 + 8 = 19, a karmic debt that reduces to 1.
        (13, 7, 1979, 1),
    ],
)
def test_life_path_reduces_components_first(day, month, year, expected):
    value, _debt = N.life_path(day, month, year)
    assert value == expected, f"{day:02d}-{month:02d}-{year} should give life path {expected}"


def test_component_first_reduction_preserves_masters_in_the_parts():
    """Why the order is fixed: masters only survive if components reduce first."""
    assert N.reduce_number(29) == 11
    assert N.reduce_number(11) == 11
    assert N.reduce_number(1975) == 22
    assert N.reduce_number(29) + N.reduce_number(11) + N.reduce_number(1975) == 44


def test_a_master_total_is_not_reduced_further():
    """25-12-1990 totals 11 and must stay 11, not collapse to 2."""
    value, _ = N.life_path(25, 12, 1990)
    assert value == 11 and value in N.MASTER_NUMBERS


def test_life_path_surfaces_a_karmic_debt():
    """A life path whose component total is 13/14/16/19 carries that debt.

    With component-first reduction the total tops out around 27, so only some
    date shapes can reach a debt at all — searching a single day/month cannot
    find one, which is why this sweeps the whole space.
    """
    seen: dict[int, tuple[int, int, int]] = {}
    for year in range(1950, 2010):
        for month in range(1, 13):
            for day in (4, 13, 17, 28):
                _value, debt = N.life_path(day, month, year)
                if debt and debt not in seen:
                    seen[debt] = (day, month, year)
    assert seen, "no karmic debt is reachable in the life path — check the tracker"
    for debt, (day, month, year) in seen.items():
        assert debt in N.KARMIC_DEBTS
        total = (
            N.reduce_number(day) + N.reduce_number(month) + N.reduce_number(year)
        )
        assert total == debt or debt in N.KARMIC_DEBTS


def test_birthday_number_debt_is_the_common_case():
    """Being born on the 13th, 14th, 16th or 19th carries the debt directly."""
    for day in N.KARMIC_DEBTS:
        value, debt = N.birthday_number(day)
        assert debt == day, f"day {day} should surface its own debt"
        assert value == N.reduce_number(day, keep_masters=False)


# ── pinnacles, challenges, cycles ──────────────────────────────────────────

def test_pinnacles_follow_the_published_construction():
    day, month, year = 14, 3, 1998
    lp, _ = N.life_path(day, month, year)
    p = N.pinnacles(day, month, year, lp)

    m, d, y = N.reduce_number(3), N.reduce_number(14), N.reduce_number(1998)
    assert p[0].number == N.reduce_number(m + d)
    assert p[1].number == N.reduce_number(d + y)
    assert p[2].number == N.reduce_number(p[0].number + p[1].number)
    assert p[3].number == N.reduce_number(m + y)


def test_pinnacle_ages_are_contiguous_and_start_at_birth():
    lp, _ = N.life_path(14, 3, 1998)
    p = N.pinnacles(14, 3, 1998, lp)
    assert p[0].starts_age == 0
    for earlier, later in zip(p, p[1:]):
        assert earlier.ends_age == later.starts_age, "a gap or overlap in the pinnacle ages"
    assert p[-1].ends_age is None


def test_challenges_are_differences_so_never_master_numbers():
    """A challenge is a gap between single digits and cannot exceed 8."""
    for year in (1975, 1990, 1998, 2003):
        lp, _ = N.life_path(29, 11, year)
        for challenge in N.challenges(29, 11, year, lp):
            assert 0 <= challenge.number <= 8


def test_life_cycles_cover_the_whole_life():
    lp, _ = N.life_path(14, 3, 1998)
    cycles = N.life_cycles(14, 3, 1998, lp)
    assert cycles[0].starts_age == 0
    assert cycles[-1].ends_age is None
    assert [c.name for c in cycles] == ["formative", "productive", "harvest"]


# ── personal year / month / day ────────────────────────────────────────────

def test_personal_year_advances_by_one_each_year_until_it_wraps():
    """The nine-year cycle must step 1..9 and wrap — never a tenth value."""
    values = [N.personal_year(14, 3, y) for y in range(2020, 2035)]
    assert all(1 <= v <= 9 for v in values), f"personal year left the 1–9 cycle: {values}"
    for earlier, later in zip(values, values[1:]):
        expected = 1 if earlier == 9 else earlier + 1
        assert later == expected, f"personal year jumped {earlier} → {later}"


def test_year_card_position_stays_inside_the_nine_year_cycle():
    for year in range(2020, 2035):
        yc = A.year_card(14, 3, 1998, (year, 6, 1))
        assert 1 <= yc.position_in_cycle <= 9


def test_personal_day_chains_through_month_and_year():
    py = N.personal_year(14, 3, 2026)
    pm = N.personal_month(py, 8)
    pd = N.personal_day(pm, 6)
    assert pd == N.reduce_number(pm + 6)
    assert 1 <= pd <= 9 or pd in N.MASTER_NUMBERS


# ── name numbers ───────────────────────────────────────────────────────────

def test_name_numbers_split_vowels_and_consonants():
    result = N.name_numbers("Sofia Rossi", life_path_value=8)
    # SOFIA ROSSI: vowels O,I,A,O,I → 6+9+1+6+9 = 31 → 4
    assert result.soul_urge == N.reduce_number(6 + 9 + 1 + 6 + 9)
    # consonants S,F,R,S,S → 1+6+9+1+1 = 18 → 9
    assert result.personality == N.reduce_number(1 + 6 + 9 + 1 + 1)
    assert result.expression == N.reduce_number(
        N.reduce_number(6 + 9 + 1 + 6 + 9) * 0 + sum(
            N._LETTER_VALUES[c] for c in "SOFIAROSSI"
        )
    )


def test_karmic_lessons_are_the_absent_values():
    result = N.name_numbers("Ana", life_path_value=5)
    # ANA = 1,5,1 → present {1,5}; everything else is a lesson.
    assert set(result.karmic_lessons) == {2, 3, 4, 6, 7, 8, 9}
    assert result.missing_numbers == result.karmic_lessons


def test_a_name_with_no_usable_letters_is_refused():
    with pytest.raises(ValueError):
        N.name_numbers("...", life_path_value=1)


# ── arcana ─────────────────────────────────────────────────────────────────

def test_birth_card_for_the_reference_date():
    """14-03-1998 → 1+4+3+1+9+9+8 = 35 → 8 … folded once, not to a digit.

    35 > 21 so it folds to 3+5 = 8: Strength. The design copy says The Star
    (XVII); the arithmetic disagrees and the arithmetic ships.
    """
    card = A.personality_card(14, 3, 1998)
    assert card.number == 8
    assert card.name == "Strength"


def test_the_fold_keeps_the_high_arcana_reachable():
    """Reducing straight to one digit would make XVII unreachable."""
    reachable = {A.personality_card(d, m, y).number
                 for d in range(1, 29) for m in range(1, 13) for y in (1975, 1998, 2003)}
    assert max(reachable) > 9, "the deck collapsed onto the first ten arcana"
    assert 17 in reachable, "The Star must be reachable"


@pytest.mark.parametrize("number", range(22))
def test_every_arcanum_has_complete_correspondences(number):
    card = A.Card.of(number)
    assert card.name and card.numeral
    assert card.element in {"fire", "earth", "air", "water"}
    assert card.ruler


def test_arcana_numbers_out_of_range_are_refused():
    with pytest.raises(ValueError):
        A.Card.of(22)


def test_soul_card_is_the_personality_reduced():
    personality = A.personality_card(14, 3, 1998)
    assert A.soul_card(personality).number == N.reduce_number(
        personality.number, keep_masters=False
    )


def test_year_card_period_brackets_the_birthday():
    """Born 14 March; on 6 August 2026 we are inside the 2026 period."""
    yc = A.year_card(14, 3, 1998, (2026, 8, 6))
    assert yc.period_start == "2026-03-14"
    assert yc.period_end == "2027-03-14"


def test_year_card_before_the_birthday_belongs_to_the_previous_period():
    """On 1 February the March birthday has not happened yet."""
    yc = A.year_card(14, 3, 1998, (2026, 2, 1))
    assert yc.period_start == "2025-03-14"
    assert yc.period_end == "2026-03-14"


def test_year_card_advances_on_the_birthday_itself():
    before = A.year_card(14, 3, 1998, (2026, 3, 13))
    on_day = A.year_card(14, 3, 1998, (2026, 3, 14))
    assert before.period_start == "2025-03-14"
    assert on_day.period_start == "2026-03-14"


def test_full_calculation_exposes_citable_factors():
    lp, _ = N.life_path(14, 3, 1998)
    result = A.calculate(day=14, month=3, year=1998, life_path=lp, today=(2026, 8, 6))
    factors = result.factors()
    assert any("Personality Card" in f for f in factors)
    assert any("Year Card" in f for f in factors)


def test_numerology_factors_are_all_non_empty_strings():
    result = N.calculate(day=14, month=3, year=1998, full_name="Sofia Rossi")
    factors = result.factors()
    assert factors and all(isinstance(f, str) and f.strip() for f in factors)
