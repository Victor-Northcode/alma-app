"""The check that reads what the prose says about a factor, not just its name.

Every case below is either a sentence this product actually produced, or the
correct sentence it should have produced instead. The false-positive cases are
the important half: a guard that refuses good writing spends attempts and
eventually hands somebody an error instead of an answer, and the first version
of this module flagged three correct paragraphs for every real one.
"""

from __future__ import annotations

import pytest

from alma.ai import geometry

#: The chart behind the measured failure — Portland, 1999-09-14 04:35 — as the
#: engine emits it. Mercury quintiles Mars and Pluto; the grand cross is made
#: of four other bodies entirely.
MAYA = [
    "grand cross: moon, saturn, venus, uranus (fixed)",
    "t-square: moon, jupiter, pluto (apex pluto in Sagittarius)",
    "mercury 26°21′ ♍︎ · house 2 · rulership",
    "sun 21°13′ ♍︎ · house 2",
    "moon 14°30′ ♏︎ · house 3 · fall",
    "☿ Q ♇ · 0°25′",
    "☿ Q ♂ · 0°52′",
    "♂ ☌ ♇ · 0°27′",
]

#: Moscow, 1990-06-14 09:25. `☉ ⚻ ♄ · 1°12′` is a quincunx, and the sentence
#: that shipped called it "a trine … a soft aspect" while copying its orb.
MOSCOW = [
    "sun 22°55′ ♊︎ · house 11",
    "saturn 24°06′ ♑︎ · house 6 · retrograde · rulership",
    "☉ ⚻ ♄ · 1°12′",
    "☉ △ ☽ · 5°42′",
    "☉ Q ♂ · 0°47′",
]


def _count(text: str, factors: list[str]) -> tuple[int, int]:
    verdict = geometry.drift(text, factors)
    return len(verdict.contradicted), len(verdict.unsupported)


# ── the failures this module was built for ──────────────────────────────────


def test_the_measured_sentence_is_caught_on_all_three_counts():
    """One sentence, three false claims, and every gate had passed it."""
    verdict = geometry.drift(
        "But Mercury is also caught in the tension of the grand cross — it "
        "squares Mars and Pluto in Sagittarius.",
        MAYA,
    )
    assert len(verdict.contradicted) == 3
    joined = " ".join(verdict.contradicted)
    # Both objects of the verb, not just the first: taking only Mars would
    # have let Pluto through, which is how half of it survived the first draft.
    assert "quintile mars" in joined
    assert "quintile pluto" in joined
    assert "mercury is not in it" in joined


def test_a_quincunx_sold_as_a_soft_trine():
    """The orb is copied from the real factor and the aspect renamed."""
    verdict = geometry.drift(
        "Your sun — at 22°55′ Gemini in the eleventh house — is in a trine to "
        "your Saturn at 1°12′, a soft aspect.",
        MOSCOW,
    )
    assert verdict.contradicted
    assert "quincunx saturn, not trine" in verdict.contradicted[0]


def test_an_aspect_the_engine_never_emitted_is_unsupported():
    contradicted, unsupported = _count("Your Sun trines Saturn.", MAYA)
    assert (contradicted, unsupported) == (0, 1)


def test_a_body_added_to_a_figures_own_member_list():
    verdict = geometry.drift(
        "The grand cross of moon, saturn, venus and mercury holds this chart.",
        MAYA,
    )
    assert verdict.contradicted


def test_the_subject_may_be_a_pronoun_from_the_sentence_before():
    """"It squares Mars" has to find Mercury in the sentence above it."""
    contradicted, _ = _count(
        "Mercury sits in the second house. It squares Mars.", MAYA
    )
    assert contradicted == 1


# ── correct writing that must not be refused ────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        # The same three facts, said correctly.
        "Mercury quintiles Mars and Pluto in Sagittarius, and the grand cross "
        "is carried by your moon, saturn, venus and uranus.",
        # A figure listing its own members.
        "The grand cross of moon, saturn, venus and uranus is the spine here.",
        # A t-square is a configuration; the word "square" inside its name is
        # not a claim of an aspect between its members.
        "Pluto, apex of a t-square with your moon and Jupiter, holds the chart.",
        # Somebody else's chart, which this one cannot confirm or deny.
        "Someone whose Mars squares your Venus will feel that friction.",
        # Astronomy, true of every full moon and about nobody in particular.
        "A full moon means the moon stands opposite the sun.",
        # Two bodies in one house is not an aspect claim.
        "Venus and Mars both sit in your first house, close to the Ascendant.",
        # A real aspect, named correctly.
        "Mars is conjunct Pluto, close enough to act as one force.",
    ],
)
def test_correct_prose_is_left_alone(text):
    assert not geometry.drift(text, MAYA)


def test_a_second_clause_is_not_an_object_of_the_first_verb():
    """A comma and a conjunction end the list rather than extending it.

    *"Saturn squares your Midheaven, and your Mercury rules that same
    Midheaven"* is two statements. Reading Mercury as a third object of
    `squares` accused the chart of an aspect nobody had claimed.
    """
    claims = geometry.claims(
        "Saturn also squares your Midheaven, and your Mercury rules that "
        "same Midheaven."
    )
    assert [(c.first, c.relation, c.second) for c in claims] == [
        ("saturn", "square", "midheaven")
    ]


# ── the parts underneath ────────────────────────────────────────────────────


def test_relations_reads_both_factor_spellings():
    """Glyph pairs and the transiting/natal sentence form are one vocabulary."""
    aspects, configurations = geometry.relations(
        [
            "♀ △ ♄ · 6°50′",
            "transiting uranus retrograde □ natal neptune · orb 0.17°",
            "☿ Q ♇ · 0°25′",
            "grand cross: moon, saturn, venus, uranus (fixed)",
        ]
    )
    assert aspects[frozenset(("venus", "saturn"))] == {"trine"}
    assert aspects[frozenset(("uranus", "neptune"))] == {"square"}
    # Quintile is a letter rather than a glyph and needs its own path.
    assert aspects[frozenset(("mercury", "pluto"))] == {"quintile"}
    assert configurations["grand cross"] == {"moon", "saturn", "venus", "uranus"}


def test_the_node_answers_to_either_computation():
    """`true_node` and `mean_node` are one point and prose names it once."""
    aspects, _ = geometry.relations(["☉ ⚼ ☊ · 0°11′"])
    pair = next(iter(aspects))
    assert "sun" in pair
    assert pair & {"true_node", "mean_node"}


def test_an_empty_chart_makes_no_claims():
    assert not geometry.drift("Mercury squares Mars.", [])


@pytest.mark.parametrize(
    "text,factors,expect",
    [
        # German: the aspect is a noun behind a preposition.
        ("Merkur steht im Quadrat zu Mars.", MAYA, True),
        # Spanish.
        ("Mercurio está en cuadratura con Marte.", MAYA, True),
        # Italian, said correctly — a quintile is what the chart has.
        ("Mercurio è in quintile con Marte.", MAYA, False),
    ],
)
def test_the_check_reads_more_than_english(text, factors, expect):
    assert bool(geometry.drift(text, factors)) is expect


# ── the conjunction nobody names ────────────────────────────────────────────

MOSCOW_MC = [
    "sun 22°55′ ♊︎ · house 11",
    "midheaven 22°50′ ♈︎",
    "☉ ⚹ MC · 0°05′",
]


def test_sits_on_is_a_conjunction_claim():
    """The orb of a sextile reprinted as the distance between two points.

    `docs/CONVERSATION.md` §4.4: *"your sun … sits almost exactly on your
    Midheaven — 0°05′ apart"*. The factor is `☉ ⚹ MC · 0°05′` — sixty degrees
    apart, five arcminutes from exact. No aspect word appears in the sentence.
    """
    verdict = geometry.drift(
        "Your sun in Gemini sits almost exactly on your Midheaven — 0°05′ apart.",
        MOSCOW_MC,
    )
    assert verdict.contradicted
    assert "sextile midheaven, not conjunction" in verdict.contradicted[0]


@pytest.mark.parametrize(
    "text,factors",
    [
        # A real conjunction, said this way, is correct writing.
        ("Venus sits right on your Ascendant, seven degrees from exact.",
         ["venus 14°02′ ♌︎ · house 1", "ascendant 20°24′ ♌︎", "♀ ☌ ASC · 7°04′"]),
        # A house is not a body, so "sits on the cusp" forms no pair.
        ("Your Mercury sits on the cusp of the second house.",
         ["mercury 26°21′ ♍︎ · house 2"]),
        # The same fact named with its aspect word, correctly.
        ("Your sun sextiles your Midheaven, five arcminutes from exact.",
         MOSCOW_MC),
    ],
)
def test_the_conjunction_phrasing_does_not_overreach(text, factors):
    assert not geometry.drift(text, factors)
