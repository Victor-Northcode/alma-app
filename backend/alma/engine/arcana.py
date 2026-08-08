"""Birth Card, Soul Card and Year Card — the 22 major arcana as arithmetic.

No cartomancy here: the tradition maps a date onto an arcanum by addition,
and that is all this module does. Illustrations are ours; the correspondences
(element, ruling planet) are the standard Golden Dawn attributions, carried
as data so the AI layer can cite them.
"""

from __future__ import annotations

from dataclasses import dataclass

from .numerology import digit_sum, reduce_number

#: name, roman numeral, element, planetary or zodiacal ruler.
ARCANA: tuple[tuple[str, str, str, str], ...] = (
    ("The Fool", "0", "air", "Uranus"),
    ("The Magician", "I", "air", "Mercury"),
    ("The High Priestess", "II", "water", "Moon"),
    ("The Empress", "III", "earth", "Venus"),
    ("The Emperor", "IV", "fire", "Aries"),
    ("The Hierophant", "V", "earth", "Taurus"),
    ("The Lovers", "VI", "air", "Gemini"),
    ("The Chariot", "VII", "water", "Cancer"),
    ("Strength", "VIII", "fire", "Leo"),
    ("The Hermit", "IX", "earth", "Virgo"),
    ("Wheel of Fortune", "X", "fire", "Jupiter"),
    ("Justice", "XI", "air", "Libra"),
    ("The Hanged Man", "XII", "water", "Neptune"),
    ("Death", "XIII", "water", "Scorpio"),
    ("Temperance", "XIV", "fire", "Sagittarius"),
    ("The Devil", "XV", "earth", "Capricorn"),
    ("The Tower", "XVI", "fire", "Mars"),
    ("The Star", "XVII", "air", "Aquarius"),
    ("The Moon", "XVIII", "water", "Pisces"),
    ("The Sun", "XIX", "fire", "Sun"),
    ("Judgement", "XX", "fire", "Pluto"),
    ("The World", "XXI", "earth", "Saturn"),
)


@dataclass(frozen=True, slots=True)
class Card:
    number: int
    name: str
    numeral: str
    element: str
    ruler: str

    @classmethod
    def of(cls, number: int) -> "Card":
        if not 0 <= number <= 21:
            raise ValueError(f"major arcanum out of range: {number}")
        name, numeral, element, ruler = ARCANA[number]
        return cls(number, name, numeral, element, ruler)


@dataclass(frozen=True, slots=True)
class YearCard:
    card: Card
    next_card: Card
    period_start: str   # ISO date — this birthday
    period_end: str     # ISO date — the next birthday
    position_in_cycle: int   # 1..9
    personal_year: int


@dataclass(frozen=True, slots=True)
class ArcanaResult:
    personality: Card
    soul: Card
    is_same_card: bool
    triad: tuple[Card, ...]
    life_path_link: int
    year: YearCard | None = None

    def factors(self) -> list[str]:
        items = [
            f"Personality Card {self.personality.numeral} {self.personality.name}",
            f"Soul Card {self.soul.numeral} {self.soul.name}",
            f"{self.personality.name} is {self.personality.element}, ruled by {self.personality.ruler}",
        ]
        if self.is_same_card:
            items.append(f"Personality and Soul are the same card ({self.personality.name})")
        if self.year:
            items.append(f"Year Card {self.year.card.numeral} {self.year.card.name}")
            items.append(f"year {self.year.position_in_cycle} of 9")
        return items


def _sum_date_digits(day: int, month: int, year: int) -> int:
    return digit_sum(day) + digit_sum(month) + digit_sum(year)


def personality_card(day: int, month: int, year: int) -> Card:
    """Sum the date's digits; fold back into 0..21 if it overflows.

    The single fold is what keeps XVII The Star reachable — reducing straight
    to a single digit would collapse every date onto the first ten arcana and
    throw away two thirds of the deck.
    """
    total = _sum_date_digits(day, month, year)
    while total > 21:
        total = digit_sum(total)
    return Card.of(total)


def soul_card(personality: Card) -> Card:
    """The personality reduced to a single digit — what sits underneath."""
    return Card.of(reduce_number(personality.number, keep_masters=False))


def triad(personality: Card, soul: Card) -> tuple[Card, ...]:
    """Personality, soul, and the card bridging them when they differ."""
    if personality.number == soul.number:
        return (personality,)
    bridge = abs(personality.number - soul.number)
    cards = [personality, soul]
    if 0 < bridge <= 21 and bridge not in {personality.number, soul.number}:
        cards.insert(1, Card.of(bridge))
    return tuple(cards)


def year_card(day: int, month: int, birth_year: int, reference_date: tuple[int, int, int]) -> YearCard:
    """The arcanum governing the year that runs birthday to birthday.

    Uses the birthday year, not the calendar year: someone born in December
    spends most of January still inside the previous card's period.
    """
    ref_year, ref_month, ref_day = reference_date
    had_birthday = (ref_month, ref_day) >= (month, day)
    period_year = ref_year if had_birthday else ref_year - 1

    total = digit_sum(day) + digit_sum(month) + digit_sum(period_year)
    while total > 21:
        total = digit_sum(total)
    card = Card.of(total)

    next_total = digit_sum(day) + digit_sum(month) + digit_sum(period_year + 1)
    while next_total > 21:
        next_total = digit_sum(next_total)

    py = reduce_number(
        reduce_number(day, keep_masters=False)
        + reduce_number(month, keep_masters=False)
        + reduce_number(period_year, keep_masters=False),
        keep_masters=False,
    ) or 9
    return YearCard(
        card=card,
        next_card=Card.of(next_total),
        period_start=f"{period_year:04d}-{month:02d}-{day:02d}",
        period_end=f"{period_year + 1:04d}-{month:02d}-{day:02d}",
        position_in_cycle=py,
        personal_year=py,
    )


def calculate(
    *, day: int, month: int, year: int, life_path: int, today: tuple[int, int, int] | None = None
) -> ArcanaResult:
    personality = personality_card(day, month, year)
    soul = soul_card(personality)
    return ArcanaResult(
        personality=personality,
        soul=soul,
        is_same_card=personality.number == soul.number,
        triad=triad(personality, soul),
        life_path_link=life_path,
        year=year_card(day, month, year, today) if today else None,
    )
