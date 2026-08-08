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

#: Cyrillic, romanised, because the table above is Latin-only and a Russian
#: reader typing their own name got nothing at all.
#:
#: **This was a dead chapter, not a rough edge.** `_letters("Анатолий")`
#: returned the empty string, `calculate` skipped the name block, and the fifth
#: of five numerology chapters — «Числа имени» — had no factors to read, so Alma
#: refused it: *"я не смогла прочитать это в твоей карте"*. Correct behaviour
#: over missing data, and it happened to every reader whose alphabet is not
#: ours, on a chapter they had paid for.
#:
#: **Why romanise rather than assign Cyrillic letters their own values.** There
#: are Russian numerological tables that number А…Я directly, and adopting one
#: would mean this product computes a different system depending on the reader's
#: keyboard — the same person, two answers, and no way to say which is the
#: product's. Pythagorean numerology is a system about the *Latin* alphabet;
#: romanising the input keeps one system for everybody and keeps the arithmetic
#: reproducible by hand, which is the whole reason this module is testable.
#:
#: **Why this particular scheme.** BGN/PCGN, the one a Russian passport and an
#: airline ticket use — Й→Y, Ю→YU, Я→YA — because it is the spelling a person
#: already recognises as their own name in Latin. ISO 9 (Â, Û, Š) is more
#: reversible and nobody writes their name that way. The chapter says which
#: spelling it counted, so the reader can check the sum by hand: see
#: `NameNumbers.romanised`.
#:
#: Ukrainian and Belarusian letters are here because they cost one line each and
#: their absence would be the same bug reported again by somebody else.
_ROMANISED = {
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "E",
    "Ж": "ZH", "З": "Z", "И": "I", "Й": "Y", "К": "K", "Л": "L", "М": "M",
    "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T", "У": "U",
    "Ф": "F", "Х": "KH", "Ц": "TS", "Ч": "CH", "Ш": "SH", "Щ": "SHCH",
    # The two signs carry no sound and therefore no value. Dropping them is the
    # same decision every romanisation makes, and it is why «Игорь» and «Игор»
    # count identically.
    "Ъ": "", "Ы": "Y", "Ь": "",
    "Э": "E", "Ю": "YU", "Я": "YA",
    # Ukrainian and Belarusian.
    "І": "I", "Ї": "YI", "Є": "YE", "Ґ": "G", "Ў": "U",
}


def romanise(full_name: str) -> str:
    """The name as Latin letters, for a reader whose alphabet is not.

    Idempotent on a name that was already Latin, which is what makes it safe to
    run on every name rather than on the ones we detect as Cyrillic — detection
    would have to guess at «Anna Ковалёва», and this does not have to guess.
    """
    return "".join(_ROMANISED.get(c, c) for c in full_name.upper())


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
    #: The letters these numbers were actually counted from — «Анатолий» read as
    #: ANATOLIY. Carried so the chapter can name the spelling instead of
    #: producing a number out of nowhere: a reader who cannot see which letters
    #: were added cannot check the sum, and this is the one system in the
    #: product that a person can check with a pencil.
    romanised: str = ""


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
    #: The arithmetic, spelled out — "14 + 3 + 1996 → 5 + 3 + 7 = 15 → 6".
    #:
    #: Carried so the chapter can open by saying where the number came from
    #: instead of announcing it. The owner's complaint was exact: reading «твоя
    #: карта души — 5», there is nothing that says how five was arrived at, and
    #: a number a reader cannot check is a number they have to take on faith —
    #: which is the one thing this product does not ask for.
    #:
    #: **Computed here rather than described by the model.** Asked to show its
    #: working, a language model will produce working that looks right; this is
    #: the same rule that keeps placements out of its hands.
    workings: tuple[str, ...] = ()

    def factors(self) -> list[str]:
        """Citable factor strings — what the AI layer is allowed to reference."""
        items = [
            f"life path {self.life_path}",
            f"birthday number {self.birthday_number}",
            f"destiny number {self.destiny_number}",
        ]
        items += list(self.workings)
        items += [f"pinnacle {p.index} is {p.number} (ages {p.starts_age}–{p.ends_age or 'on'})"
                  for p in self.pinnacles]
        items += [f"challenge {c.index} is {c.number}" for c in self.challenges]
        items += [f"karmic debt {d}" for d in self.karmic_debts_present]
        items += [f"master number {m}" for m in self.master_numbers_present]
        if self.name:
            # The letters, before the numbers read from them. A citable factor
            # rather than prose the model composes, because it is the one line
            # that lets a reader redo the sum — and because a Cyrillic name is
            # now counted from a spelling nobody typed, which has to be said out
            # loud rather than quietly assumed.
            if self.name.romanised:
                items.append(f"name counted as {self.name.romanised}")
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
    return "".join(c for c in romanise(full_name) if c in _LETTER_VALUES)


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
        romanised=letters,
    )


def _workings(day: int, month: int, year: int, name: NameNumbers | None) -> tuple[str, ...]:
    """The arithmetic behind each headline number, as sentences a model may cite.

    Written in the shape a person would check it in — the reduced parts, then
    the sum, then the fold — because that is what the chapter has to be able to
    say. `life path = 6` is a claim; "14 → 5, 3 → 3, 1996 → 7, and 5 + 3 + 7 =
    15 → 6" is the same claim with its receipt attached.

    Every string here is a *factor*, which means the validator checks that the
    prose citing it exists in this list character for character. That is the
    point: the working travels under the same rule as a placement, so a chapter
    cannot round it, restate it or quietly get it wrong.
    """
    out: list[str] = []

    d, m, y = reduce_number(day), reduce_number(month), reduce_number(year)
    total = d + m + y
    folded = reduce_number(total)
    out.append(
        f"life path working: day {day} → {d}, month {month} → {m}, "
        f"year {year} → {y}; {d} + {m} + {y} = {total} → {folded}"
    )

    bd_total = digit_sum(day) if day > 9 else day
    out.append(
        f"birthday number working: the day of the month is {day}"
        + (f", and {day} → {bd_total}" if day > 9 else "")
    )

    digits = f"{day:02d}{month:02d}{year}"
    out.append(
        "destiny number working: every digit of the date "
        f"{day:02d}.{month:02d}.{year} adds to {sum(int(c) for c in digits)} "
        f"→ {destiny_from_date(day, month, year)}"
    )

    if name is not None and name.romanised:
        vowels = [c for c in name.romanised if c in _VOWELS]
        consonants = [c for c in name.romanised if c not in _VOWELS]
        out.append(
            f"expression working: every letter of {name.romanised} adds to "
            f"{sum(_LETTER_VALUES[c] for c in name.romanised)} → {name.expression}"
        )
        if vowels:
            out.append(
                f"soul urge working: the vowels {' '.join(vowels)} add to "
                f"{sum(_LETTER_VALUES[c] for c in vowels)} → {name.soul_urge}"
            )
        if consonants:
            out.append(
                f"personality working: the consonants add to "
                f"{sum(_LETTER_VALUES[c] for c in consonants)} → {name.personality}"
            )
    return tuple(out)


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
        workings=_workings(day, month, year, name_block),
    )
