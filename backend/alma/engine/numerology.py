"""Pythagorean numerology — deterministic arithmetic, no ephemeris involved.

Every number here is reproducible by hand, which makes it the one system we
can test against exact expected values rather than tolerances. The subtlety
is entirely in *when* to stop reducing: master numbers (11/22/33) survive
reduction, and karmic debts (13/14/16/19) must be spotted at the intermediate
total before it collapses to a single digit. Reduce too eagerly and both
disappear silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MASTER_NUMBERS = (11, 22, 33)
KARMIC_DEBTS = (13, 14, 16, 19)

#: Pythagorean letter values. J=1 and S=1 are the classic collision points.
_LETTER_VALUES = {
    **{c: 1 for c in "AJS"},
    **{c: 2 for c in "BKT"},
    **{c: 3 for c in "CLU"},
    **{c: 4 for c in "DMV"},
    **{c: 5 for c in "ENW"},
    **{c: 6 for c in "FOX"},
    **{c: 7 for c in "GPY"},
    **{c: 8 for c in "HQZ"},
    **{c: 9 for c in "IR"},
}
_VOWELS = set("AEIOU")


def digit_sum(value: int) -> int:
    return sum(int(d) for d in str(abs(value)))


def reduce_number(value: int, *, keep_masters: bool = True) -> int:
    """Collapse to a single digit, stopping at a master number if asked."""
    current = abs(value)
    while current > 9:
        if keep_masters and current in MASTER_NUMBERS:
            return current
        current = digit_sum(current)
    return current


def _reduce_tracking_debt(value: int) -> tuple[int, int | None]:
    """Reduce, and report a karmic debt seen on the way down.

    The debt lives in the intermediate total: 19 reduces to 1, and a caller
    who only sees the 1 has lost the information the tradition cares about.
    """
    debt: int | None = value if value in KARMIC_DEBTS else None
    current = abs(value)
    while current > 9:
        if current in MASTER_NUMBERS:
            return current, debt
        if current in KARMIC_DEBTS and debt is None:
            debt = current
        current = digit_sum(current)
    return current, debt


@dataclass(frozen=True, slots=True)
class Pinnacle:
    index: int
    number: int
    starts_age: int
    ends_age: int | None  # None means "for the rest of life"


@dataclass(frozen=True, slots=True)
class Challenge:
    index: int
    number: int
    starts_age: int
    ends_age: int | None


@dataclass(frozen=True, slots=True)
class LifeCycle:
    index: int
    number: int
    name: str
    starts_age: int
    ends_age: int | None


@dataclass(frozen=True, slots=True)
class NameNumbers:
    expression: int
    soul_urge: int
    personality: int
    maturity: int
    missing_numbers: tuple[int, ...]
    karmic_lessons: tuple[int, ...]
    letter_counts: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NumerologyResult:
    life_path: int
    life_path_debt: int | None
    birthday_number: int
    birthday_debt: int | None
    destiny_number: int
    pinnacles: tuple[Pinnacle, ...]
    challenges: tuple[Challenge, ...]
    cycles: tuple[LifeCycle, ...]
    master_numbers_present: tuple[int, ...]
    karmic_debts_present: tuple[int, ...]
    name: NameNumbers | None = None

    def factors(self) -> list[str]:
        """Citable factor strings — what the AI layer is allowed to reference."""
        items = [
            f"life path {self.life_path}",
            f"birthday number {self.birthday_number}",
            f"destiny number {self.destiny_number}",
        ]
        items += [f"pinnacle {p.index} is {p.number} (ages {p.starts_age}–{p.ends_age or 'on'})"
                  for p in self.pinnacles]
        items += [f"challenge {c.index} is {c.number}" for c in self.challenges]
        items += [f"karmic debt {d}" for d in self.karmic_debts_present]
        items += [f"master number {m}" for m in self.master_numbers_present]
        if self.name:
            items += [
                f"expression {self.name.expression}",
                f"soul urge {self.name.soul_urge}",
                f"personality {self.name.personality}",
                f"maturity {self.name.maturity}",
            ]
            items += [f"karmic lesson {n}" for n in self.name.karmic_lessons]
        return items


def life_path(day: int, month: int, year: int) -> tuple[int, int | None]:
    """Sum the reduced date parts, keeping masters and noting debt.

    Reducing each component first is the standard Pythagorean method and is
    not equivalent to summing all the digits: 29-11-1975 gives 11 one way and
    8 the other, and only the first preserves the master number.
    """
    parts = sum(reduce_number(p) for p in (day, month, year))
    return _reduce_tracking_debt(parts)


def birthday_number(day: int) -> tuple[int, int | None]:
    return _reduce_tracking_debt(day)


def destiny_from_date(day: int, month: int, year: int) -> int:
    """Every digit of the date, reduced once — the 'what you are here to do'."""
    total = digit_sum(day) + digit_sum(month) + digit_sum(year)
    return reduce_number(total)


def personal_year(day: int, month: int, reference_year: int) -> int:
    """Where this year sits in the nine-year cycle, 1..9.

    Master numbers are deliberately *not* kept here. The personal year is a
    position in a nine-step cycle, so an 11 has to become a 2 — leaving it at
    11 breaks the cycle arithmetic downstream (the Year Card's position, the
    month and day that chain off it) and produces a tenth step that does not
    exist.
    """
    total = reduce_number(day, keep_masters=False) + reduce_number(
        month, keep_masters=False
    ) + reduce_number(reference_year, keep_masters=False)
    return reduce_number(total, keep_masters=False) or 9


def personal_month(personal_year_value: int, calendar_month: int) -> int:
    return reduce_number(personal_year_value + calendar_month, keep_masters=False) or 9


def personal_day(personal_month_value: int, calendar_day: int) -> int:
    return reduce_number(personal_month_value + calendar_day, keep_masters=False) or 9


def _pinnacle_boundaries(life_path_value: int) -> tuple[int, int, int]:
    """The first pinnacle ends at 36 minus the life path; then nine-year steps."""
    first_end = 36 - reduce_number(life_path_value, keep_masters=False)
    return first_end, first_end + 9, first_end + 18


def pinnacles(day: int, month: int, year: int, life_path_value: int) -> tuple[Pinnacle, ...]:
    m, d, y = reduce_number(month), reduce_number(day), reduce_number(year)
    p1 = reduce_number(m + d)
    p2 = reduce_number(d + y)
    p3 = reduce_number(p1 + p2)
    p4 = reduce_number(m + y)
    e1, e2, e3 = _pinnacle_boundaries(life_path_value)
    return (
        Pinnacle(1, p1, 0, e1),
        Pinnacle(2, p2, e1, e2),
        Pinnacle(3, p3, e2, e3),
        Pinnacle(4, p4, e3, None),
    )


def challenges(day: int, month: int, year: int, life_path_value: int) -> tuple[Challenge, ...]:
    """Challenges are differences, so they reduce *without* keeping masters.

    A challenge of 11 is not a master number — it is the gap between two
    single digits, which can never exceed 8.
    """
    m = reduce_number(month, keep_masters=False)
    d = reduce_number(day, keep_masters=False)
    y = reduce_number(year, keep_masters=False)
    c1 = abs(m - d)
    c2 = abs(d - y)
    c3 = abs(c1 - c2)
    c4 = abs(m - y)
    e1, e2, e3 = _pinnacle_boundaries(life_path_value)
    return (
        Challenge(1, c1, 0, e1),
        Challenge(2, c2, e1, e2),
        Challenge(3, c3, e2, e3),
        Challenge(4, c4, e3, None),
    )


def life_cycles(day: int, month: int, year: int, life_path_value: int) -> tuple[LifeCycle, ...]:
    e1, e2, _ = _pinnacle_boundaries(life_path_value)
    return (
        LifeCycle(1, reduce_number(month), "formative", 0, e1),
        LifeCycle(2, reduce_number(day), "productive", e1, e2),
        LifeCycle(3, reduce_number(year), "harvest", e2, None),
    )


def _letters(full_name: str) -> str:
    return "".join(c for c in full_name.upper() if c in _LETTER_VALUES)


def name_numbers(full_name: str, life_path_value: int) -> NameNumbers:
    letters = _letters(full_name)
    if not letters:
        raise ValueError("name contains no letters that carry a Pythagorean value")

    vowels = [c for c in letters if c in _VOWELS]
    consonants = [c for c in letters if c not in _VOWELS]

    expression = reduce_number(sum(_LETTER_VALUES[c] for c in letters))
    soul = reduce_number(sum(_LETTER_VALUES[c] for c in vowels)) if vowels else 0
    personality = reduce_number(sum(_LETTER_VALUES[c] for c in consonants)) if consonants else 0
    maturity = reduce_number(reduce_number(life_path_value) + expression)

    counts: dict[int, int] = {}
    for c in letters:
        counts[_LETTER_VALUES[c]] = counts.get(_LETTER_VALUES[c], 0) + 1
    missing = tuple(n for n in range(1, 10) if n not in counts)

    return NameNumbers(
        expression=expression,
        soul_urge=soul,
        personality=personality,
        maturity=maturity,
        missing_numbers=missing,
        karmic_lessons=missing,  # the lessons are exactly the absent values
        letter_counts=counts,
    )


def calculate(
    *, day: int, month: int, year: int, full_name: str | None = None, reference_year: int | None = None
) -> NumerologyResult:
    """The whole numerology block for one birth date."""
    lp, lp_debt = life_path(day, month, year)
    bd, bd_debt = birthday_number(day)

    debts = tuple(sorted({d for d in (lp_debt, bd_debt) if d is not None}))
    masters = tuple(
        sorted({n for n in (lp, bd) if n in MASTER_NUMBERS})
    )

    name_block = None
    if full_name and _letters(full_name):
        name_block = name_numbers(full_name, lp)
        if name_block.expression in MASTER_NUMBERS:
            masters = tuple(sorted(set(masters) | {name_block.expression}))

    del reference_year  # personal-year figures are requested per-date, not stored
    return NumerologyResult(
        life_path=lp,
        life_path_debt=lp_debt,
        birthday_number=bd,
        birthday_debt=bd_debt,
        destiny_number=destiny_from_date(day, month, year),
        pinnacles=pinnacles(day, month, year, lp),
        challenges=challenges(day, month, year, lp),
        cycles=life_cycles(day, month, year, lp),
        master_numbers_present=masters,
        karmic_debts_present=debts,
        name=name_block,
    )
