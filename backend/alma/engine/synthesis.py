"""Cross-synthesis — nine questions, asked of every system that has an answer.

This is the part of the product that cannot be bought anywhere else, and it
only works if it is honest about disagreement. Averaging three traditions
into one soothing paragraph would be the easy thing and the useless thing;
where the natal chart and the Birth Card pull in opposite directions, that
contradiction is usually the most accurate sentence in the whole reading.

So each axis collects a *signal* from each system: a number in [−1, +1] on a
named polarity, plus the literal factor it came from. The verdict is then
arithmetic rather than editorial — systems agree when their signals share a
sign, disagree when they do not, and an axis only one system can see is
labelled as such instead of being padded out.

Every mapping below is a stated convention, written down so it can be argued
with. None of it is inferred at runtime and none of it is hidden in a prompt.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import zodiac
from .arcana import ArcanaResult
from .natal import NatalChart
from .numerology import NumerologyResult

#: The nine axes, in the order the interface shows them.
#:
#: Two kinds of string live in this tuple and they are not interchangeable.
#:
#: The **name** is an identifier. `compute` files each system's signal under
#: it, the synthesis chapter's `reads` tuple in `ai/chapters.py` matches on
#: it as a substring, and `Synthesis.factors()` puts it in the list the model
#: must cite from verbatim and `ai/validator.py` checks those citations
#: against character by character. It is English in every language, on both
#: clients, on purpose: translate it and the model cites "Richtung", the
#: validator cannot find it in an English factor list, calls it invented, and
#: refuses the reading after three attempts. Both clients already translate
#: the nine names themselves, keyed on the English word.
#:
#: The **poles** are copy. They never enter a prompt, a factor list or a
#: cache key; they exist to be read, and a reader who is told "2 disagree"
#: without them has been shown a number with no subject. Their translations
#: live in `alma/i18n/` under the axis name, and they are substituted at the
#: response boundary in `api/routers/systems.py` rather than here, because
#: this result is cached per birth and not per locale — the arithmetic is the
#: same in all six languages.
#:
#: `Axis.label` and `Synthesis.summary()` are inside `factors()` too, and so
#: they are data for the same reason as the name.
AXES: tuple[tuple[str, str, str], ...] = (
    # name (an identifier), negative pole (copy), positive pole (copy)
    ("Direction", "works alone, out of sight", "works in public, in front of people"),
    ("Character", "holds a position", "changes shape"),
    ("Mind", "wants proof first", "trusts the first impression"),
    ("Relationships", "wants an open door", "wants a witness"),
    ("Resources", "builds their own", "arrives through other people"),
    ("Work", "one large push", "a small repeatable practice"),
    ("Weak point", "fears being unseen", "fears being seen"),
    ("Growth", "asked to withdraw", "asked to be seen"),
    ("Rhythms", "a closing season", "an opening season"),
)

#: Elements read as a temperament: fire and air lean outward, earth and water
#: inward. Used wherever an axis needs a sign's disposition rather than its
#: name.
ELEMENT_DIRECTION = {"fire": 0.7, "air": 0.5, "earth": -0.5, "water": -0.7}
MODALITY_STEADINESS = {"fixed": -0.8, "cardinal": 0.2, "mutable": 0.8}

#: Below this a system is treated as having no opinion on the axis.
ABSTAIN_THRESHOLD = 0.3

#: Life-path temperaments, from the standard Pythagorean readings. Positive
#: is the outward pole of each axis; a life path absent from a table simply
#: does not speak on that axis, which is a real answer.
LIFE_PATH_DIRECTION = {1: 0.7, 3: 0.8, 5: 0.6, 8: 0.7, 11: 0.5, 22: 0.4, 7: -0.8, 4: -0.3, 9: 0.3}
LIFE_PATH_MIND = {7: -0.9, 4: -0.6, 8: -0.4, 3: 0.7, 11: 0.8, 2: 0.5, 9: 0.4}
LIFE_PATH_RELATIONSHIPS = {2: 0.8, 6: 0.9, 5: -0.8, 1: -0.6, 7: -0.7, 9: 0.3}
LIFE_PATH_WORK = {4: 0.8, 6: 0.6, 8: -0.6, 1: -0.7, 5: -0.5, 22: -0.4}

#: Major arcana read on each axis. Only the cards with an unambiguous reading
#: on a given axis appear; silence beats a stretched correspondence.
CARD_DIRECTION = {
    0: 0.5, 1: 0.6, 2: -0.8, 3: 0.4, 4: 0.7, 5: 0.5, 6: 0.3, 7: 0.7,
    8: 0.2, 9: -0.9, 10: 0.3, 12: -0.6, 14: -0.3, 16: 0.4, 17: -0.4,
    18: -0.7, 19: 0.8, 20: 0.6, 21: 0.5,
}
CARD_CHARACTER = {
    2: -0.6, 3: -0.4, 4: -0.8, 5: -0.7, 8: -0.7, 9: -0.5, 11: -0.6, 21: -0.5,
    0: 0.9, 1: 0.5, 6: 0.4, 7: 0.3, 10: 0.8, 12: 0.6, 13: 0.7, 14: 0.5, 18: 0.6,
}
CARD_RELATIONSHIPS = {
    2: -0.6, 6: 0.8, 9: -0.9, 11: 0.3, 14: 0.4, 15: 0.5, 17: -0.4, 19: 0.5, 21: 0.4,
    0: -0.7, 1: -0.3, 13: -0.4,
}
CARD_RESOURCES = {
    3: -0.5, 4: -0.6, 5: 0.4, 6: 0.3, 10: 0.6, 13: 0.8, 15: 0.7, 17: 0.6, 21: 0.3,
    1: -0.4, 8: -0.5, 9: -0.6,
}


@dataclass(frozen=True, slots=True)
class Signal:
    """One system's answer on one axis."""

    system: str          # "natal" | "numerology" | "birth-card" | "transits"
    value: float         # −1 … +1 on the axis's polarity
    factor: str          # the literal fact this came from — citable verbatim

    @property
    def leans(self) -> int:
        """Which pole this signal points at, or 0 for "not enough to say".

        The threshold is deliberately high. A weak signal counted as a full
        vote manufactures disagreements out of noise, and a manufactured
        disagreement is worse than silence here — the whole value of the axis
        is that when it reports a conflict, there is one.
        """
        return 0 if abs(self.value) < ABSTAIN_THRESHOLD else (1 if self.value > 0 else -1)


@dataclass(frozen=True, slots=True)
class Axis:
    """One of the nine questions, with everything that answered it."""

    name: str
    negative_pole: str
    positive_pole: str
    signals: tuple[Signal, ...]

    @property
    def speaking(self) -> tuple[Signal, ...]:
        return tuple(s for s in self.signals if s.leans != 0)

    @property
    def count(self) -> int:
        return len(self.speaking)

    @property
    def verdict(self) -> str:
        leans = {s.leans for s in self.speaking}
        if self.count <= 1:
            return "single"
        return "agree" if len(leans) == 1 else "disagree"

    @property
    def label(self) -> str:
        if self.verdict == "single":
            return "seen by one" if self.count == 1 else "not seen"
        if self.verdict == "agree":
            return f"{self.count} agree"
        return f"{self.count} disagree"

    @property
    def direction(self) -> str | None:
        """Which pole the axis lands on, when it lands anywhere."""
        if self.verdict != "agree" or not self.speaking:
            return None
        return self.positive_pole if self.speaking[0].leans > 0 else self.negative_pole

    def factors(self) -> list[str]:
        return [f"{s.system}: {s.factor}" for s in self.signals]


@dataclass(frozen=True, slots=True)
class Synthesis:
    axes: tuple[Axis, ...]
    agreements: int
    disagreements: int
    single_voice: int
    systems_present: tuple[str, ...]

    def summary(self) -> str:
        return (
            f"{len(self.systems_present)} systems across nine axes: "
            f"{self.agreements} agree, {self.disagreements} disagree, "
            f"{self.single_voice} seen by one"
        )

    def factors(self) -> list[str]:
        items = [self.summary()]
        for axis in self.axes:
            items.append(f"{axis.name} — {axis.label}")
            items += [f"  {f}" for f in axis.factors()]
        return items


# ── the natal chart's answers ──────────────────────────────────────────────

def _natal_signals(chart: NatalChart) -> dict[str, Signal]:
    out: dict[str, Signal] = {}
    sun = chart.placements["sun"]

    if chart.angles:
        mc_sign = zodiac.sign_of(chart.angles.midheaven)
        out["Direction"] = Signal(
            "natal",
            ELEMENT_DIRECTION[zodiac.element_of(chart.angles.midheaven)],
            f"midheaven in {mc_sign}",
        )
    else:
        # Without an angle the Sun's element still speaks, more quietly.
        out["Direction"] = Signal(
            "natal", ELEMENT_DIRECTION[zodiac.element_of(sun.longitude)] * 0.6,
            f"sun in {sun.sign}",
        )

    out["Character"] = Signal(
        "natal",
        MODALITY_STEADINESS[chart.balance["dominant_modality"]],
        f"dominant modality {chart.balance['dominant_modality']}",
    )

    mercury = chart.placements["mercury"]
    mercury_lean = -0.7 if zodiac.element_of(mercury.longitude) in ("earth",) else (
        0.7 if zodiac.element_of(mercury.longitude) in ("water", "fire") else -0.2
    )
    out["Mind"] = Signal("natal", mercury_lean, f"mercury in {mercury.sign}")

    venus = chart.placements["venus"]
    relationship_lean = ELEMENT_DIRECTION[zodiac.element_of(venus.longitude)] * -1.0
    if venus.house in (7, 8):
        relationship_lean = 0.8
    elif venus.house in (11, 9, 12):
        relationship_lean = -0.6
    out["Relationships"] = Signal(
        "natal",
        relationship_lean,
        f"venus in {venus.sign}" + (f", house {venus.house}" if venus.house else ""),
    )

    if chart.house_cusps:
        eighth_ruler = zodiac.SIGN_RULERS[zodiac.sign_of(chart.house_cusps[7])]
        ruler = eighth_ruler[1] or eighth_ruler[0]
        ruler_house = chart.placements[ruler].house if ruler in chart.placements else None
        out["Resources"] = Signal(
            "natal",
            0.7 if ruler_house in (2, 8, 11) else -0.4,
            f"ruler of the eighth ({ruler}) in house {ruler_house}",
        )
        sixth = [n for n, p in chart.placements.items() if p.house == 6]
        out["Work"] = Signal(
            "natal",
            0.7 if sixth else -0.4,
            f"house six holds {', '.join(sixth)}" if sixth else "house six is empty",
        )

    # The weak point: Chiron if we have it, otherwise Saturn's hard contacts.
    if "chiron" in chart.placements:
        chiron = chart.placements["chiron"]
        seen = chiron.house in (1, 10, 7) if chiron.house else False
        out["Weak point"] = Signal(
            "natal", 0.8 if seen else -0.6,
            f"chiron in {chiron.sign}" + (f", house {chiron.house}" if chiron.house else ""),
        )
    else:
        saturn = chart.placements["saturn"]
        out["Weak point"] = Signal(
            "natal", -0.5, f"saturn in {saturn.sign}",
        )

    node = chart.placements["true_node"]
    node_lean = ELEMENT_DIRECTION[zodiac.element_of(node.longitude)]
    if node.house:
        node_lean = 0.8 if node.house in (1, 5, 7, 10, 11) else -0.7
    out["Growth"] = Signal(
        "natal", node_lean,
        f"north node in {node.sign}" + (f", house {node.house}" if node.house else ""),
    )

    # Rhythms: a waxing birth opens, a waning birth closes.
    out["Rhythms"] = Signal(
        "natal",
        0.7 if chart.moon_phase["waxing"] else -0.7,
        f"born on a {chart.moon_phase['phase']}",
    )
    return out


# ── numerology's answers ───────────────────────────────────────────────────

def _numerology_signals(result: NumerologyResult, personal_year: int | None) -> dict[str, Signal]:
    out: dict[str, Signal] = {}
    life_path = result.life_path

    for axis, table in (
        ("Direction", LIFE_PATH_DIRECTION),
        ("Mind", LIFE_PATH_MIND),
        ("Relationships", LIFE_PATH_RELATIONSHIPS),
        ("Work", LIFE_PATH_WORK),
    ):
        if life_path in table:
            out[axis] = Signal("numerology", table[life_path], f"life path {life_path}")

    if result.karmic_debts_present:
        debt = result.karmic_debts_present[0]
        out["Resources"] = Signal(
            "numerology",
            0.7 if debt in (13, 16) else -0.5,
            f"karmic debt {debt}",
        )

    if result.name and result.name.karmic_lessons:
        lesson = result.name.karmic_lessons[0]
        out["Weak point"] = Signal(
            "numerology", 0.6 if lesson in (1, 3, 5) else -0.6,
            f"karmic lesson {lesson}",
        )

    challenge = result.challenges[0].number if result.challenges else None
    if challenge is not None:
        out["Character"] = Signal(
            "numerology",
            0.6 if challenge in (3, 5, 0) else -0.6,
            f"first challenge {challenge}",
        )

    if personal_year is not None:
        # 1–4 open a cycle, 8–9 close it, the middle is neither.
        lean = 0.8 if personal_year <= 4 else (-0.8 if personal_year >= 8 else 0.0)
        out["Rhythms"] = Signal("numerology", lean, f"personal year {personal_year}")
        out["Growth"] = Signal(
            "numerology",
            0.7 if personal_year in (1, 3, 5, 8) else -0.6,
            f"personal year {personal_year}",
        )
    return out


# ── the Birth Card's answers ───────────────────────────────────────────────

def _arcana_signals(result: ArcanaResult) -> dict[str, Signal]:
    out: dict[str, Signal] = {}
    card = result.personality
    label = f"{card.numeral} {card.name}"

    for axis, table in (
        ("Direction", CARD_DIRECTION),
        ("Character", CARD_CHARACTER),
        ("Relationships", CARD_RELATIONSHIPS),
        ("Resources", CARD_RESOURCES),
    ):
        if card.number in table:
            out[axis] = Signal("birth-card", table[card.number], label)

    if result.soul.number != card.number and result.soul.number in CARD_DIRECTION:
        out["Mind"] = Signal(
            "birth-card",
            CARD_DIRECTION[result.soul.number] * 0.6,
            f"soul card {result.soul.numeral} {result.soul.name}",
        )

    if result.year:
        year_card = result.year.card
        out["Growth"] = Signal(
            "birth-card",
            CARD_DIRECTION.get(year_card.number, 0.0),
            f"year card {year_card.numeral} {year_card.name}",
        )
        position = result.year.position_in_cycle
        out["Rhythms"] = Signal(
            "birth-card",
            0.8 if position <= 4 else (-0.8 if position >= 8 else 0.0),
            f"year {position} of 9",
        )
    return out


def compute(
    *,
    chart: NatalChart,
    numerology: NumerologyResult,
    arcana: ArcanaResult,
    personal_year: int | None = None,
) -> Synthesis:
    """The nine axes, with every system that has something to say on each."""
    contributions = {
        "natal": _natal_signals(chart),
        "numerology": _numerology_signals(numerology, personal_year),
        "birth-card": _arcana_signals(arcana),
    }

    axes: list[Axis] = []
    for name, negative, positive in AXES:
        signals = tuple(
            contributions[system][name]
            for system in ("natal", "numerology", "birth-card")
            if name in contributions[system]
        )
        axes.append(Axis(name, negative, positive, signals))

    return Synthesis(
        axes=tuple(axes),
        agreements=sum(1 for a in axes if a.verdict == "agree"),
        disagreements=sum(1 for a in axes if a.verdict == "disagree"),
        single_voice=sum(1 for a in axes if a.verdict == "single"),
        systems_present=tuple(contributions),
    )
