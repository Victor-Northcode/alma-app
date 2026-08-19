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
    aspects, configurations, frames = geometry.relations(
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
    # Одна и та же пара тел в двух рамках — два разных утверждения, и рамка
    # снимается с той же строки, что и аспект.
    assert frames[frozenset(("venus", "saturn"))] == {"natal"}
    assert frames[frozenset(("uranus", "neptune"))] == {"transit"}


def test_the_node_answers_to_either_computation():
    """`true_node` and `mean_node` are one point and prose names it once."""
    aspects, _, _ = geometry.relations(["☉ ⚼ ☊ · 0°11′"])
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


# ── натальное и транзитное — два разных утверждения ────────────────────────
#
# Проверки выше спрашивают «есть ли такой аспект», и на этот вопрос
# `transiting saturn □ natal ascendant` отвечает «есть» ровно так же, как
# `♄ □ ASC`. Но чат получает карту рождения и сегодняшнее небо одним списком,
# и это тот самый случай, где вопрос стоит иначе: не «есть ли», а «в них ли».
# `voice.py` говорит об этом прямее всего: «"Transiting Saturn is on your
# Midheaven" is true; "Saturn is on your Midheaven" is a claim about the birth
# chart» — и до сих пор эту разницу не сторожило ничего.

#: Карта рождения и транзиты вместе — ровно так, как их видит ход беседы.
BOTH_FRAMES = [
    "venus 7°40′ ♒︎ · house 1",
    "saturn 24°06′ ♑︎ · house 6",
    "ascendant 20°24′ ♌︎",
    "♀ △ ♄ · 6°50′",
    "transiting saturn □ natal ascendant · orb 11.52°",
]


def test_a_transit_described_as_a_birth_chart_aspect_is_caught():
    """Временное небо, поданное как свойство человека."""
    verdict = geometry.drift("Your Saturn squares your Ascendant.", BOTH_FRAMES)
    assert verdict.contradicted
    assert "transit passing now" in verdict.contradicted[0]


def test_naming_the_transit_makes_the_same_sentence_true():
    assert not geometry.drift(
        "Transiting Saturn squares your Ascendant right now.", BOTH_FRAMES
    )


def test_two_claims_in_one_sentence_do_not_share_a_frame():
    """Обратное направление снято, и вот прозой, на которой оно ошибалось.

    Первая версия читала слово «transiting» по предложению, а не по
    утверждению: здесь их два, оба верны, и второе получало рамку первого — ход
    уходил на попытку из-за верного текста. Цена ошибки в эту сторону —
    потерянный вопрос; цена пропуска — ошибка в слове.
    """
    assert not geometry.drift(
        "Transiting Saturn squares your Ascendant, and your Venus trines your "
        "Saturn underneath it.",
        BOTH_FRAMES,
    )


def test_a_natal_aspect_named_plainly_is_left_alone():
    assert not geometry.drift("Your Venus trines your Saturn.", BOTH_FRAMES)


def test_a_reply_that_talks_about_transits_keeps_its_pronouns():
    """Осознанная слепота, и без неё проверка ловила бы хорошую прозу.

    `claims` намеренно тянет подлежащее через границу предложения, поэтому во
    втором предложении слова «transiting» нет, а утверждение — о транзите.
    Спрашивать с него рамку значит отвергать верный текст, и правило «названо
    натальным» выключено везде, где ответ про транзиты вообще говорит.
    """
    assert not geometry.drift(
        "Transiting Saturn is the weather this month. Your Saturn squares your "
        "Ascendant while it passes.",
        BOTH_FRAMES,
    )


def test_a_chart_with_only_one_frame_is_never_faulted_for_the_other():
    """У главы транзитов нет натального списка, и наоборот — рамка одна."""
    natal_only = ["venus 7°40′ ♒︎ · house 1", "saturn 24°06′ ♑︎ · house 6",
                  "♀ △ ♄ · 6°50′"]
    assert not geometry.drift("Your Venus trines your Saturn.", natal_only)


# ── подлежащее, а не ближайшее слово ───────────────────────────────────────
#
# Измерено на живом `/v1/chat` 19 августа 2026, вопрос «что сейчас движется в
# моём небе и при чём тут мой натальный Сатурн». Модель написала верную фразу —
# три аспекта от одного подлежащего-местоимения, — а разбор взял подлежащим
# ближайшее тело слева, то есть дополнение предыдущей клаузы, и обвинил карту
# в аспекте, которого никто не заявлял. Две попытки из трёх умерли так, и
# человек получил 422 на совершенно обычный вопрос.

#: Транзитный Юпитер в трёх контактах — та самая форма, что сломалась.
SKY = [
    "mars 25°20′ ♑︎ · house 6",
    "ascendant 20°24′ ♌︎",
    "neptune 12°55′ ♒︎ · house 6",
    "transiting jupiter △ natal ascendant · orb 2°04′",
    "transiting jupiter □ natal mars · orb 3°11′",
    "transiting jupiter ⚹ natal neptune · orb 1°22′",
]

#: Два подлежащих в одном предложении, и оба говорят правду.
TWO_SUBJECTS = ["venus 7°40′ ♒︎", "saturn 24°06′ ♑︎", "mars 25°20′ ♑︎",
                "pluto 12°00′ ♐︎", "♀ △ ♄ · 1°02′", "♂ □ ♇ · 2°14′"]


def test_a_list_of_aspects_from_one_pronoun_is_read_from_its_antecedent():
    """Дословно фраза, на которой ход умирал."""
    assert not geometry.drift(
        "Transiting Jupiter is the loud one this month. It's trine your "
        "ascendant, it squares your natal Mars, and, retrograde, it's sextile "
        "your natal Neptune.",
        SKY,
    )


def test_the_same_list_with_one_aspect_wrong_is_still_caught():
    """Разбор стал точнее, а не мягче: проверка обязана остаться проверкой."""
    verdict = geometry.drift(
        "Transiting Jupiter is loud. It's trine your ascendant, it trines your "
        "natal Mars.",
        SKY,
    )
    assert verdict.contradicted
    assert "jupiter square mars, not trine" in verdict.contradicted[0]


def test_two_subjects_in_one_sentence_keep_their_own_verbs():
    """Клауза, а не предложение: после запятой с союзом подлежащее новое."""
    assert not geometry.drift(
        "Venus trines Saturn, and Mars squares Pluto.", TWO_SUBJECTS
    )
    assert geometry.drift(
        "Venus trines Saturn, and Mars trines Pluto.", TWO_SUBJECTS
    ).contradicted
