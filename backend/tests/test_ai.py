"""The writing layer, tested without a key and without a network.

The scripted provider returns exactly what a test says a model returned,
including deliberately bad output, so the parts that keep this product honest
— citation validation, the regeneration loop, the budget guard, the refusal to
ship — are all exercised in CI.

The single most important test in this file is the sensitivity one at the
bottom. A generation pipeline that ignores its inputs produces a product that
works perfectly in a demo and is worthless: everyone gets the same beautiful
reading. Asserting that a two-hour change of birth time rewrites the
house-derived chapters, and a different birth date rewrites nearly everything,
is what makes "this is your chart" a claim rather than a slogan.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from alma import i18n
from alma.ai import chapters, conversation, cost, validator, voice, writer
from alma.ai.provider import ScriptedProvider
from alma.ai.validator import Paragraph
from alma.ai.writer import ReadingRefused
from alma.calc import BirthData, compute

SOFIA = BirthData(
    date=date(1998, 3, 14), time="04:20", latitude=45.4642, longitude=9.19,
    timezone="Europe/Rome", place_label="Milan, Italy", name="Sofia Rossi",
)


@pytest.fixture(scope="module")
def natal():
    return compute("natal", SOFIA)


def _reply(paragraphs, *, title="Core", teaser="A teaser.", advice="") -> str:
    return json.dumps(
        {
            "title": title,
            "teaser": teaser,
            "advice": advice,
            "paragraphs": [{"text": text, "factors": list(factors)} for text, factors in paragraphs],
        }
    )


# ── the validator ──────────────────────────────────────────────────────────

def test_a_reading_that_cites_real_factors_passes():
    verdict = validator.check(
        [Paragraph("You lead with Mars.", ("mars 5°00′ ♈︎ · house 1",))],
        allowed=["mars 5°00′ ♈︎ · house 1", "sun 23°14′ ♓︎"],
    )
    assert verdict.ok
    assert not verdict.invented


def test_an_invented_factor_is_caught():
    """The failure mode this whole layer exists to prevent."""
    verdict = validator.check(
        [Paragraph("Chiron sits on your Ascendant.", ("chiron 4°00′ ♈︎ · house 1",))],
        allowed=["sun 23°14′ ♓︎"],
    )
    assert not verdict.ok
    assert verdict.invented == ("chiron 4°00′ ♈︎ · house 1",)
    assert "do not exist" in verdict.complaint()


def test_an_uncited_paragraph_is_caught():
    verdict = validator.check(
        [Paragraph("You are a deeply private person.", ())],
        allowed=["sun 23°14′ ♓︎"],
    )
    assert not verdict.ok
    assert verdict.uncited == (0,)
    assert "cite no factor" in verdict.complaint()


def test_an_empty_reading_is_caught():
    verdict = validator.check([], allowed=["sun 23°14′ ♓︎"])
    assert not verdict.ok and verdict.empty


def test_typographic_differences_do_not_reject_a_correct_citation():
    """Models reproduce a dash differently far more often than they invent."""
    for variant in (
        "mars 5°00' ♈︎ - house 1",
        "MARS 5°00′ ♈︎ · HOUSE 1",
        "mars  5°00′ ♈︎ ·  house 1",
    ):
        verdict = validator.check(
            [Paragraph("text", (variant,))], allowed=["mars 5°00′ ♈︎ · house 1"]
        )
        assert verdict.ok, f"{variant!r} was wrongly rejected"


def test_a_factor_from_another_chapter_is_a_warning_not_a_rejection():
    """A genuine cross-reference is good writing, not a fault."""
    verdict = validator.check(
        [Paragraph("Your Saturn again.", ("saturn 12°00′ ♈︎",))],
        allowed=["saturn 12°00′ ♈︎", "venus 3°00′ ♒︎"],
        offered=["venus 3°00′ ♒︎"],
    )
    assert verdict.ok
    assert verdict.off_topic == ("saturn 12°00′ ♈︎",)


@pytest.mark.parametrize(
    "text",
    [
        "You will die in your sixties.",
        "You will be diagnosed with cancer.",
        "You will win the lawsuit.",
        "This is a guaranteed profit.",
        "Your partner is cheating on you.",
    ],
)
def test_forbidden_claims_are_caught(text):
    assert validator.safety(text)


def test_ordinary_prose_is_not_flagged():
    assert not validator.safety(
        "Saturn in the seventh describes a slowness about commitment, not a verdict on it."
    )


@pytest.mark.parametrize(
    "text",
    [
        "I cannot tell you when you will die.",
        "I do not read deaths, and I will not tell you that you will be diagnosed.",
        "No one can tell you that you will be pregnant this year, and I will not.",
        "I can't promise you will win the lawsuit — I read the pattern, not the verdict.",
    ],
)
def test_a_refusal_that_names_what_it_refuses_is_not_the_thing_it_refuses(text):
    """The guard used to fire on the only correct answer to the question.

    Logged live on "when am i going to die": `chat attempt 1 broke a rule:
    predicts death or diagnosis` — on the sentence declining to predict it.
    One of two attempts spent, and the turn pushed towards the 422 the reader
    actually saw. The two blast radii overlap exactly, so the negation has to
    be part of the pattern rather than left to the prompt.
    """
    assert not validator.safety(text)


def test_the_bare_assertion_is_still_caught_even_after_a_disclaimer():
    """A negation from an earlier sentence must not launder the next one."""
    assert validator.safety(
        "I do not read the future. You will die at sixty-one, like your grandmother."
    )


def test_a_reading_may_carry_one_paragraph_that_claims_nothing():
    """The shape `CHAT_RULES` asks for and the validator used to forbid.

    Taken verbatim from the measured Portuguese turn: paragraph one says what
    could not be calculated — an absence, which no factor can ever assert —
    and paragraph two reads the nearest thing there is. Two attempts of this
    became a 422 on the model subscribers pay for, four times in one session.
    """
    verdict = validator.check(
        [
            validator.Paragraph(
                "A compatibilidade não foi calculada — adicione os dados de "
                "nascimento dele na tela de sinastria.", ()
            ),
            validator.Paragraph(
                "O que posso ler é o teu Vénus.", ("venus 6°02′ ♓︎ · house 11 · exaltation",)
            ),
        ],
        allowed=["venus 6°02′ ♓︎ · house 11 · exaltation"],
        allow_uncited=1,
    )
    assert verdict.ok, verdict.reasons


def test_two_uncited_paragraphs_are_still_a_reading_with_a_hole_in_it():
    verdict = validator.check(
        [
            validator.Paragraph("That lands hard.", ()),
            validator.Paragraph("And it has been a long week.", ()),
            validator.Paragraph("Your Moon is in Scorpio.", ("moon 14°26′ ♏︎",)),
        ],
        allowed=["moon 14°26′ ♏︎"],
        allow_uncited=1,
    )
    assert not verdict.ok
    assert verdict.uncited == (1,), "the tolerance is spent on the first, not the last"
    assert "At most 1 paragraph may carry none" in verdict.complaint()


def test_the_tolerance_buys_nothing_when_nothing_cites():
    """A reading with no chart behind it is not a reading at any tolerance."""
    verdict = validator.check(
        [validator.Paragraph("You are a deeply intuitive person.", ())],
        allowed=["moon 14°26′ ♏︎"],
        allow_uncited=1,
    )
    assert not verdict.ok and verdict.uncited == (0,)


def test_a_chapter_is_not_given_the_tolerance():
    """`allow_uncited` defaults to zero, and `writer` never passes it."""
    verdict = validator.check(
        [
            validator.Paragraph("An opening that names nothing.", ()),
            validator.Paragraph("The chapter proper.", ("moon 14°26′ ♏︎",)),
        ],
        allowed=["moon 14°26′ ♏︎"],
        minimum=2,
    )
    assert not verdict.ok and verdict.uncited == (0,)


def test_a_dignity_the_citation_does_not_carry_is_noticed():
    """True by luck is not the same as sourced.

    Measured: "Júpiter … está exaltado" is true of that chart, and the factor
    cited beside it was the eighth-house rulership, which says nothing about
    dignity. A reader who checks one citation and finds it does not support the
    sentence loses the meaning of every citation in the app.
    """
    assert validator.dignity_drift([
        validator.Paragraph(
            "Júpiter está exaltado no teu mapa.",
            ("natal: ruler of the eighth (jupiter) in house 2",),
        )
    ]) == ["exaltation"]

    assert not validator.dignity_drift([
        validator.Paragraph(
            "Júpiter está exaltado no teu mapa.",
            ("jupiter 4°06′ ♋︎ · house 2 · exaltation",),
        )
    ])


def test_the_parser_tolerates_the_shapes_a_model_actually_returns():
    _title, paragraphs = validator.parse(
        {"paragraphs": [{"text": "a", "factors": "one factor"}, "a bare string"]}
    )
    assert paragraphs[0].factors == ("one factor",)
    assert paragraphs[1].text == "a bare string"


# ── the writer ─────────────────────────────────────────────────────────────

async def test_a_chapter_is_written_from_real_factors(natal):
    chapter = chapters.find("natal", "core")
    offered = chapters.relevant_factors(chapter, natal.factors)
    provider = ScriptedProvider(
        responses=[_reply([("You lead with this.", offered[:1]), ("And this.", offered[1:2])])]
    )

    written = await writer.write(
        result=natal, chapter=chapter, provider=provider, model="claude-opus-5"
    )
    assert written.attempts == 1
    assert written.cited_factors
    assert written.text()
    assert written.as_dict()["read_from"].startswith("Read from:")


async def test_an_invented_factor_triggers_a_regeneration(natal):
    """The loop that keeps a hallucinated placement out of a paid reading."""
    chapter = chapters.find("natal", "core")
    offered = chapters.relevant_factors(chapter, natal.factors)
    provider = ScriptedProvider(
        responses=[
            _reply([("Invented.", ["chiron conjunct the vertex at 3°"]), ("More.", offered[:1])]),
            _reply([("Corrected.", offered[:1]), ("Also.", offered[1:2])]),
        ]
    )

    written = await writer.write(
        result=natal, chapter=chapter, provider=provider, model="claude-opus-5"
    )
    assert written.attempts == 2
    assert len(provider.calls) == 2
    assert "do not exist" in provider.calls[1]["prompt"]


async def test_the_complaint_names_the_invented_factor(natal):
    chapter = chapters.find("natal", "core")
    offered = chapters.relevant_factors(chapter, natal.factors)
    provider = ScriptedProvider(
        responses=[
            _reply([("Bad.", ["a placement that is not real"])]),
            _reply([("Good.", offered[:1]), ("Fine.", offered[:1])]),
        ]
    )
    await writer.write(result=natal, chapter=chapter, provider=provider, model="claude-opus-5")
    assert "a placement that is not real" in provider.calls[1]["prompt"]


async def test_a_reading_is_refused_rather_than_shipped_with_invention(natal):
    """Nothing is better than a confident lie."""
    chapter = chapters.find("natal", "core")
    provider = ScriptedProvider(
        responses=[_reply([("Invented.", ["not real"])]) for _ in range(writer.MAX_ATTEMPTS)]
    )
    with pytest.raises(ReadingRefused, match="Refusing"):
        await writer.write(result=natal, chapter=chapter, provider=provider, model="claude-opus-5")
    assert len(provider.calls) == writer.MAX_ATTEMPTS


async def test_a_forbidden_claim_triggers_a_regeneration(natal):
    chapter = chapters.find("natal", "core")
    offered = chapters.relevant_factors(chapter, natal.factors)
    provider = ScriptedProvider(
        responses=[
            _reply([("You will die in your sixties.", offered[:1]), ("More.", offered[:1])]),
            _reply([("A description, not a prediction.", offered[:1]), ("More.", offered[:1])]),
        ]
    )
    written = await writer.write(
        result=natal, chapter=chapter, provider=provider, model="claude-opus-5"
    )
    assert written.attempts == 2
    assert "broke a rule" in provider.calls[1]["prompt"]


async def test_unparseable_output_is_retried(natal):
    chapter = chapters.find("natal", "core")
    offered = chapters.relevant_factors(chapter, natal.factors)
    provider = ScriptedProvider(
        responses=["not json at all", _reply([("Fine.", offered[:1]), ("Also.", offered[:1])])]
    )
    written = await writer.write(
        result=natal, chapter=chapter, provider=provider, model="claude-opus-5"
    )
    assert written.attempts == 2


async def test_a_chapter_with_no_factors_is_refused_not_invented(natal):
    """A chart that says nothing about a subject must produce no chapter."""
    empty = chapters.Chapter(
        slug="nothing", numeral="X", index=99, title="Nothing",
        question="?", reads=("a factor no chart contains",),
    )
    provider = ScriptedProvider(responses=[])
    with pytest.raises(ReadingRefused, match="no factors to read from"):
        await writer.write(result=natal, chapter=empty, provider=provider, model="claude-opus-5")
    assert provider.calls == [], "the model was called for a chapter with no inputs"


# ── the prompt ─────────────────────────────────────────────────────────────

def test_the_prompt_contains_the_factors_verbatim(natal):
    chapter = chapters.find("natal", "core")
    offered = chapters.relevant_factors(chapter, natal.factors)
    prompt = writer.build_prompt(natal, chapter, offered=offered)
    for factor in offered:
        assert factor in prompt


def test_the_prompt_names_what_could_not_be_calculated():
    timeless = BirthData(
        date=date(1998, 3, 14), time=None, latitude=45.4642, longitude=9.19,
        timezone="Europe/Rome",
    )
    result = compute("natal", timeless)
    chapter = chapters.find("natal", "core")
    offered = chapters.relevant_factors(chapter, result.factors)
    prompt = writer.build_prompt(result, chapter, offered=offered)
    assert "COULD NOT BE CALCULATED" in prompt
    assert "birth time is unknown" in prompt


def test_the_system_prompt_carries_the_rules_and_the_language():
    prompt = voice.system_prompt(locale="it", paid=True)
    assert "Italian" in prompt
    assert "names at least one factor" in prompt
    assert "paid for this chapter" in prompt


def test_memory_reaches_the_system_prompt():
    prompt = voice.system_prompt(memory=["they changed jobs in March"])
    assert "changed jobs in March" in prompt


# ── cost ───────────────────────────────────────────────────────────────────

def test_cost_is_computed_from_the_price_table():
    spend = cost.cost("claude-opus-5", 1_000_000, 1_000_000)
    assert spend.dollars == pytest.approx(30.0)


def test_an_unknown_model_is_priced_pessimistically():
    """An unknown model must trip a budget early, not run up a bill."""
    known = cost.cost("claude-haiku-4-5", 1000, 1000).dollars
    unknown = cost.cost("some-new-model", 1000, 1000).dollars
    assert unknown > known


def test_a_free_generation_is_held_to_the_free_ceiling():
    with pytest.raises(cost.BudgetExceeded, match="ceiling"):
        cost.guard("claude-opus-5", prompt_chars=400_000, max_output_tokens=4000, paid=False)


def test_a_paid_generation_has_more_room():
    cost.guard("claude-opus-5", prompt_chars=40_000, max_output_tokens=3000, paid=True)


def test_the_ledger_adds_calls_up():
    ledger = cost.Ledger()
    ledger.record(cost.cost("claude-haiku-4-5", 1000, 500))
    ledger.record(cost.cost("claude-haiku-4-5", 1000, 500))
    assert ledger.input_tokens == 2000
    assert ledger.dollars == pytest.approx(2 * cost.cost("claude-haiku-4-5", 1000, 500).dollars)


async def test_a_chapter_reports_what_it_cost_and_not_what_the_report_cost(natal):
    """`Written.spend` is this chapter's tokens, not the shared ledger's total.

    `write_system` hands one `Ledger` to every chapter, so reading the whole
    tally at the end put chapter one's tokens inside chapter two's spend and
    both inside chapter three's — summing sixteen of those over-counts a natal
    report by roughly eight times. The single-chapter route already charges
    `written.spend` to the month ledger, so a whole-report route would refuse
    every account after one report.
    """
    shared = cost.Ledger()
    chapter = chapters.find("natal", "core")
    offered = chapters.relevant_factors(chapter, natal.factors)
    reply = _reply([("One paragraph, read from the chart.", offered[:1])] * 2)

    written = []
    for _ in range(3):
        written.append(
            await writer.write(
                result=natal,
                chapter=chapter,
                provider=ScriptedProvider(responses=[reply], input_tokens=1000, output_tokens=500),
                model="claude-haiku-4-5",
                ledger=shared,
            )
        )

    one_call = cost.cost("claude-haiku-4-5", 1000, 500).dollars
    assert [w.spend.dollars for w in written] == pytest.approx([one_call] * 3)
    assert shared.dollars == pytest.approx(one_call * 3), "the ledger still sees the whole report"


async def test_a_refusal_reports_what_the_attempts_cost(natal):
    """The refusal path spends the most and used to report nothing at all."""
    chapter = chapters.find("natal", "core")
    invented = _reply([("Invented.", ["transiting Saturn conjunct natal Vulcan"])] * 2)
    provider = ScriptedProvider(
        responses=[invented] * writer.MAX_ATTEMPTS, input_tokens=1000, output_tokens=500
    )
    with pytest.raises(writer.ReadingRefused) as refusal:
        await writer.write(
            result=natal, chapter=chapter, provider=provider, model="claude-haiku-4-5"
        )
    expected = cost.cost("claude-haiku-4-5", 1000, 500).dollars * writer.MAX_ATTEMPTS
    assert refusal.value.spend.dollars == pytest.approx(expected)


async def test_a_runaway_generation_is_stopped_by_the_ledger(natal, monkeypatch):
    """Three retries at full price must not quietly cost three times the cap."""
    from alma import config as config_module

    monkeypatch.setenv("ALMA_FREE_USER_BUDGET", "0.0001")
    config_module.settings.cache_clear()
    try:
        chapter = chapters.find("natal", "core")
        provider = ScriptedProvider(responses=[_reply([("x", ["y"])])], output_tokens=100_000)
        with pytest.raises(cost.BudgetExceeded):
            await writer.write(
                result=natal, chapter=chapter, provider=provider,
                model="claude-opus-5", paid=False,
            )
    finally:
        config_module.settings.cache_clear()


# ── conversation ───────────────────────────────────────────────────────────

async def test_a_chat_answer_cites_the_chart(natal):
    provider = ScriptedProvider(
        responses=[
            json.dumps(
                {
                    "answer": [{"text": "Because of this.", "factors": [natal.factors[0]]}],
                    "answered_from_chart": True,
                    "remember": ["they are deciding about a job"],
                }
            )
        ]
    )
    reply = await conversation.answer(
        question="Should I take the job?", results=[natal],
        provider=provider, model="claude-haiku-4-5",
    )
    assert reply.answered_from_chart
    assert reply.cited_factors == (natal.factors[0],)
    assert reply.remember == ("they are deciding about a job",)


async def test_a_chat_answer_may_say_the_chart_is_silent(natal):
    """The permission that makes every other answer believable."""
    provider = ScriptedProvider(
        responses=[
            json.dumps(
                {
                    "answer": [{"text": "Nothing in your chart speaks to this.", "factors": []}],
                    "answered_from_chart": False,
                }
            )
        ]
    )
    reply = await conversation.answer(
        question="What is the capital of Peru?", results=[natal],
        provider=provider, model="claude-haiku-4-5",
    )
    assert reply.answered_from_chart is False
    assert reply.cited_factors == ()


async def test_a_chat_answer_that_invents_is_regenerated(natal):
    provider = ScriptedProvider(
        responses=[
            json.dumps({
                "answer": [{"text": "Your Chiron says.", "factors": ["chiron on the vertex"]}],
                "answered_from_chart": True,
            }),
            json.dumps({
                "answer": [{"text": "Corrected.", "factors": [natal.factors[0]]}],
                "answered_from_chart": True,
            }),
        ]
    )
    reply = await conversation.answer(
        question="What about work?", results=[natal],
        provider=provider, model="claude-haiku-4-5",
    )
    assert len(provider.calls) == 2
    assert reply.cited_factors == (natal.factors[0],)


async def test_a_chat_answer_is_refused_after_repeated_invention(natal):
    provider = ScriptedProvider(
        responses=[
            json.dumps({
                "answer": [{"text": "Invented.", "factors": ["not real"]}],
                "answered_from_chart": True,
            })
            for _ in range(conversation.MAX_ATTEMPTS)
        ]
    )
    with pytest.raises(ValueError, match="refusing"):
        await conversation.answer(
            question="x", results=[natal], provider=provider, model="claude-haiku-4-5"
        )


async def test_a_third_attempt_stands_between_a_wobbly_answer_and_an_error(natal):
    """The two 422s that a real newcomer hit, on their second message.

    "idk i just downloaded this lol. what can you actually tell me" is a
    question about the app. The model reached for a placement anyway, twice,
    and `MAX_ATTEMPTS = 2` turned the second miss into an error screen that
    also cost one of three free questions. The third attempt is what the
    complaint's new sentence is for: cite nothing, say what you can do.
    """
    provider = ScriptedProvider(responses=[
        json.dumps({"answer": [{"text": "You are a Virgo rising.",
                                "factors": ["ascendant 12°00′ ♍︎"]}],
                    "kind": "reading"}),
        json.dumps({"answer": [{"text": "You are a Virgo rising, really.",
                                "factors": ["ascendant 12°01′ ♍︎"]}],
                    "kind": "reading"}),
        json.dumps({"answer": [{"text": "I read your birth chart, your numbers and "
                                        "your Birth Card. Ask me anything about any "
                                        "of them.", "factors": []}],
                    "kind": "aside"}),
    ])
    reply = await _ask(
        provider, natal, question="idk i just downloaded this lol. what can you actually tell me"
    )
    assert len(provider.calls) == 3
    assert reply.kind == conversation.ASIDE
    assert reply.cited_factors == ()


async def test_the_complaint_says_that_citing_nothing_is_a_way_out(natal):
    """It never did, so the model kept hunting for a placement that would fit."""
    provider = ScriptedProvider(responses=[
        json.dumps({"answer": [{"text": "Invented.", "factors": ["not a real factor"]}],
                    "kind": "reading"}),
        json.dumps({"answer": [{"text": "I read charts. What would you like to look at?",
                                "factors": []}],
                    "kind": "aside"}),
    ])
    await _ask(provider, natal, question="so is that my fault or hers")
    retry = provider.calls[1]["prompt"]
    assert "aside" in retry and "cite nothing" in retry


def test_the_chat_prompt_includes_the_history_and_the_question(natal):
    prompt = conversation.build_prompt(
        question="And what about money?",
        results=[natal],
        history=[("user", "Tell me about work"), ("alma", "Your tenth house...")],
    )
    assert "Tell me about work" in prompt
    assert "And what about money?" in prompt
    assert natal.factors[0] in prompt


# ── a claim, and a conversation ────────────────────────────────────────────
#
# The rule these assert is the one the whole taxonomy rests on: a sentence
# that says something about this person names the placement it came from, and
# a sentence that says nothing about them — a greeting, a thank-you, a refusal
# — is not forced through that gate and is not reported as a verdict on their
# chart. Each test asserts the rule, never the wording: the copy is the
# model's and it is expected to differ every time.

def _turn(payload: dict) -> ScriptedProvider:
    return ScriptedProvider(responses=[json.dumps(payload)])


async def _ask(provider, natal, question="hello", **kwargs):
    return await conversation.answer(
        question=question, results=[natal], provider=provider,
        model="claude-haiku-4-5", **kwargs,
    )


async def test_a_greeting_asserts_nothing_and_needs_no_factor(natal):
    """The bug, inverted. "Hello" is not a claim and has no placement behind it."""
    reply = await _ask(
        _turn({"answer": [{"text": "Hello. What would you like to look at?", "factors": []}],
               "kind": "aside"}),
        natal,
    )
    assert reply.kind == conversation.ASIDE
    assert reply.cited_factors == ()


async def test_an_aside_is_not_a_silence(natal):
    """The two states the old boolean fused, kept apart.

    Both still answer the legacy `answered_from_chart` with False, because two
    shipped clients read it — but "I looked and your chart has nothing to say"
    and "you said hello" are different things and the payload now says which.
    """
    aside = await _ask(
        _turn({"answer": [{"text": "Hello.", "factors": []}], "kind": "aside"}), natal
    )
    silent = await _ask(
        _turn({"answer": [{"text": "Nothing in your chart speaks to the weather — "
                                   "what it does describe is how you decide.",
                           "factors": []}],
               "kind": "silent"}),
        natal, question="what's the weather",
    )
    assert aside.kind != silent.kind
    assert aside.answered_from_chart is False and silent.answered_from_chart is False


async def test_a_reading_costs_a_question_and_a_greeting_does_not(natal):
    """You pay for a reading, not for a sentence."""
    reading = await _ask(
        _turn({"answer": [{"text": "Because of this.", "factors": [natal.factors[0]]}],
               "kind": "reading"}),
        natal, question="what does my chart say about love?",
    )
    greeting = await _ask(
        _turn({"answer": [{"text": "Hello.", "factors": []}], "kind": "aside"}), natal
    )
    assert reading.spends_a_question is True
    assert greeting.spends_a_question is False


async def test_a_reply_that_cites_is_a_reading_whatever_it_called_itself(natal):
    """The contradictory payload — declines the chart, cites five placements."""
    reply = await _ask(
        _turn({"answer": [{"text": "Not really, but here is what is there.",
                           "factors": [natal.factors[0]]}],
               "kind": "aside"}),
        natal, question="how are you",
    )
    assert reply.kind == conversation.READING
    assert reply.answered_from_chart is True
    assert reply.cited_factors == (natal.factors[0],)


async def test_an_aside_may_not_smuggle_an_invented_placement(natal):
    """Calling it an aside does not get a fabricated factor past the validator."""
    provider = ScriptedProvider(responses=[
        json.dumps({"answer": [{"text": "Hello, and your Chiron says.",
                                "factors": ["chiron on the vertex"]}],
                    "kind": "aside"}),
        json.dumps({"answer": [{"text": "Hello. What would you like to know?", "factors": []}],
                    "kind": "aside"}),
    ])
    reply = await _ask(provider, natal)
    assert len(provider.calls) == 2
    assert reply.kind == conversation.ASIDE


async def test_a_payload_from_before_the_taxonomy_still_decides_a_kind(natal):
    """Every stored fixture and both shipped clients predate `kind`."""
    reading = await _ask(
        _turn({"answer": [{"text": "Because of this.", "factors": [natal.factors[0]]}],
               "answered_from_chart": True}),
        natal,
    )
    silent = await _ask(
        _turn({"answer": [{"text": "Nothing in your chart speaks to this.", "factors": []}],
               "answered_from_chart": False}),
        natal,
    )
    assert reading.kind == conversation.READING
    assert silent.kind == conversation.SILENT


# ── the language she reads ─────────────────────────────────────────────────

async def test_she_may_not_claim_to_read_only_english(natal):
    """The sentence the owner was shown, refused before anybody sees it."""
    provider = ScriptedProvider(responses=[
        json.dumps({"answer": [{"text": "I cannot read this question — the text appears "
                                        "to be in Cyrillic script, and I read English only.",
                                "factors": []}],
                    "kind": "aside"}),
        json.dumps({"answer": [{"text": "Привет. Что бы вы хотели узнать?", "factors": []}],
                    "kind": "aside"}),
    ])
    reply = await _ask(provider, natal, question="Хелли шл/ха")
    assert len(provider.calls) == 2
    assert "English only" not in reply.text()
    assert "English" in provider.calls[1]["prompt"]  # the complaint names the breach


@pytest.mark.parametrize(
    "sentence",
    [
        "I read English only, so I cannot help with this.",
        "I read charts in English. Please ask again in English and I will answer.",
        "I cannot read your message — it does not form a clear English sentence.",
        "I do not understand this question.",
        # The same falsehood in its second costume, and this line used to be in
        # the *passing* list below. The old language block asked her to say it;
        # what she produced was "Пока я не пишу по-русски", in fluent Russian,
        # and then argued for it across three turns when the reader pointed at
        # the screen. She writes every language. The clause that asked for this
        # sentence is deleted from `voice.CHAT_LANGUAGE` and the sentence is now
        # a breach.
        "I do not yet write Russian, so this is in English — we can carry on either way.",
        "I don't write Russian, but I can answer in English.",
    ],
)
def test_every_shape_of_the_language_refusal_is_caught(sentence):
    assert conversation._breaches(sentence)


@pytest.mark.parametrize(
    "sentence",
    [
        "I cannot read your partner's mind — his half is not in your chart.",
        "You do not write much of this down, and that is the pattern.",
        "I cannot write your ending for you, and I would not want to.",
    ],
)
def test_the_language_guard_does_not_catch_a_good_sentence(sentence):
    """A guard that fires on the third-party rule would break a better rule."""
    assert not conversation._breaches(sentence)


@pytest.mark.parametrize(
    ("question", "body", "wrong"),
    [
        ("Расскажи про мою Луну", "Your Moon is in Scorpio and it is in fall.", True),
        ("Расскажи про мою Луну", "Твоя Луна в Скорпионе, и она в падении.", False),
        ("私の月について教えて", "Your Moon sits in the sixth house.", True),
        # Latin script is never faulted: a transliterated message is genuinely
        # ambiguous and answering it in English is a defensible reading.
        ("privet, kak dela", "Hello — what would you like to look at?", False),
        ("hi", "Hello — what would you like to look at?", False),
        ("Хелли шл/ха", "Привет. Что бы вы хотели узнать из карты?", False),
    ],
)
def test_answering_in_someone_elses_alphabet_is_caught_without_a_language_table(
    question, body, wrong
):
    """The half of the language guard that works when the regexes cannot.

    `CHAT_FORBIDDEN` matches English, so a false claim made *in Russian* — the
    measured failure — is invisible to it. A script is a property of the
    characters: no table, no detector, no model.
    """
    assert conversation._wrong_script(question, body) is wrong


@pytest.mark.parametrize(
    ("body", "faulty"),
    [
        # The live failure, verbatim, from the first run against the real model
        # after the language block was rewritten: "Hello. I read astrology
        # charts in English. Please write your question in English." The
        # original bug, translated into the reader's own language, where every
        # English pattern in `CHAT_FORBIDDEN` is blind and the alphabet check
        # sees nothing wrong.
        ("Привет. Я читаю астрологические карты на английском языке. "
         "Пожалуйста, напишите ваш вопрос по-английски.", True),
        ("Привет. Что бы вы хотели узнать из своей карты?", False),
        ("I read astrology charts in English. Please write in English.", True),
        # The two an early draft of the table got wrong: `ingl` is inside
        # "single" and `angl` is inside "angle".
        ("Transiting Saturn is sextile your Uranus, which is a steadying angle.", False),
        ("You are single right now, and the chart does not mind.", False),
        ("Hola. Puedo leer tu carta natal. ¿Qué quieres saber?", False),
        ("Olá. Posso ler o teu mapa. O que queres saber?", False),
    ],
)
def test_a_chat_reply_never_names_a_language(body, faulty):
    """Under the policy she answers in theirs, so naming one is always the tell."""
    assert bool(conversation._language_fault("hi", body)) is faulty


def test_a_conversation_is_told_to_answer_in_the_language_they_wrote_in():
    prompt = voice.system_prompt(locale="en", conversation=True)
    for language in ("Spanish", "German", "Italian", "French", "Brazilian Portuguese"):
        assert language in prompt
    assert "Write the reading in" not in prompt


def test_a_reader_in_an_unshipped_language_is_still_answered_in_it():
    """`ja` resolves to English — and she still replies in Japanese.

    The old block told her to open with one sentence in their language saying
    she does not write it yet. That sentence is false, it came out
    ungrammatical, and she defended it when challenged. The policy is decided
    in code now: reply in the language they wrote in, full stop. Russian used
    to be this test's example, and then Russian shipped.
    """
    assert i18n.resolve("ja") == "en"
    prompt = voice.system_prompt(locale="ja", conversation=True)
    assert "Reply in the language they wrote to you in" in prompt
    assert "Japanese, Turkish or Arabic" in prompt
    assert "you do not write it yet" not in prompt
    assert not conversation._breaches(prompt + conversation.CHAT_RULES)


def test_a_chapter_still_gets_the_chapter_language_block():
    prompt = voice.system_prompt(locale="de")
    assert "Write the reading in German" in prompt
    assert "the message is a fact about them" not in prompt


# ── not saying the same thing twice ────────────────────────────────────────

_SAID = (
    "Your Saturn in Capricorn sits in the sixth house, the house of work and "
    "the daily grind, and it is retrograde. That combination describes somebody "
    "who learned early that effort is the price of safety, and who still checks "
    "the receipts long after the debt is paid."
)


async def test_she_does_not_hand_back_the_answer_she_just_gave(natal):
    """Measured at 0.9934 similarity between an answer and its own follow-up."""
    provider = ScriptedProvider(responses=[
        json.dumps({"answer": [{"text": _SAID, "factors": [natal.factors[0]]}],
                    "kind": "reading"}),
        json.dumps({"answer": [{"text": "It is why you check twice. What you have not "
                                        "heard yet is what the sixth house costs you on "
                                        "an ordinary Tuesday, which is the part you keep "
                                        "calling laziness when it is fatigue.",
                                "factors": [natal.factors[0]]}],
                    "kind": "reading"}),
    ])
    reply = await _ask(
        provider, natal, question="is that why I'm like this?",
        history=[("user", "Tell me about my Saturn"), ("alma", _SAID)],
    )
    assert len(provider.calls) == 2
    assert "already said this" in provider.calls[1]["prompt"]
    assert conversation._similarity(reply.text(), _SAID) < conversation.REPEAT_THRESHOLD


async def test_repetition_is_never_what_refuses_a_turn(natal):
    """A dull answer is a disappointment; a 422 is a lost question and an error."""
    provider = ScriptedProvider(responses=[
        json.dumps({"answer": [{"text": _SAID, "factors": [natal.factors[0]]}],
                    "kind": "reading"})
        for _ in range(conversation.MAX_ATTEMPTS)
    ])
    reply = await _ask(
        provider, natal, question="why?", history=[("alma", _SAID)],
    )
    assert reply.text() == _SAID


async def test_a_short_reply_is_allowed_to_resemble_an_earlier_one(natal):
    """There is only one way to say "you're welcome", and it costs nothing."""
    provider = _turn({"answer": [{"text": "You're welcome.", "factors": []}], "kind": "aside"})
    reply = await _ask(
        provider, natal, question="thanks", history=[("alma", "You're welcome.")],
    )
    assert len(provider.calls) == 1
    assert reply.kind == conversation.ASIDE


#: Two consecutive refusals from a real session. 110 and 63 characters, so the
#: ratio fence never even looks at them; they score 0.4393 against each other,
#: so it would pass them if it did. Five of eighteen refusals in that session
#: used this same template.
_REFUSED_SKIES = (
    "I read charts, not skies. But I'm curious what made you ask about the "
    "weather just now."
)
_REFUSED_CALENDARS = "I read charts, not calendars. Ask me what the pattern is."


async def test_the_same_refusal_twice_is_caught_where_the_ratio_cannot_see_it(natal):
    """The failure mode changed clothes; the fence was built where it was not.

    `CHAT_FORBIDDEN` killed the two exact sentences the owner screenshotted,
    and the repetition fence was then calibrated on long readings — which are
    varied and rarely repeat — while refusals are short, formulaic and repeat
    constantly.
    """
    assert conversation._similarity(_REFUSED_SKIES, _REFUSED_CALENDARS) < \
        conversation.REPEAT_THRESHOLD
    assert conversation._repetition(_REFUSED_CALENDARS, [("alma", _REFUSED_SKIES)]) is not None

    provider = ScriptedProvider(responses=[
        json.dumps({"answer": [{"text": _REFUSED_CALENDARS, "factors": []}], "kind": "aside"}),
        json.dumps({"answer": [{"text": "That one is outside what a chart holds — but "
                                        "tell me what you were hoping it would say and "
                                        "I will read the nearest thing to it.",
                                "factors": []}],
                    "kind": "aside"}),
    ])
    reply = await _ask(
        provider, natal, question="what day is it?", history=[("alma", _REFUSED_SKIES)],
    )
    assert len(provider.calls) == 2
    assert conversation._opening(reply.text()) != conversation._opening(_REFUSED_SKIES)


async def test_a_refusal_with_no_door_in_it_is_sent_back(natal):
    """Five of eight refusals in one session offered only the half that says no."""
    assert conversation._one_sided_refusal(
        "I cannot advise you on medication. That is between you and your doctor."
    )
    assert not conversation._one_sided_refusal(
        "I cannot promise that. But I can show you what is moving in your chart this year."
    )

    provider = ScriptedProvider(responses=[
        json.dumps({"answer": [{"text": "I cannot help with that. That is a matter for a "
                                        "professional.", "factors": []}],
                    "kind": "aside"}),
        json.dumps({"answer": [{"text": "I will not weigh in on the dose — that is a "
                                        "conversation with whoever prescribed it. What I "
                                        "can do is read how you carry a decision like "
                                        "this one.", "factors": []}],
                    "kind": "aside"}),
    ])
    reply = await _ask(provider, natal, question="should i come off my medication")
    assert len(provider.calls) == 2
    assert "two halves" in provider.calls[1]["prompt"]
    assert not conversation._one_sided_refusal(reply.text())


async def test_circling_the_same_four_placements_is_sent_back(natal):
    """The machine tell one level up: not the same sentence, the same chart."""
    already = list(natal.factors[:4])
    provider = ScriptedProvider(responses=[
        json.dumps({"answer": [{"text": "Once more, from the same three places.",
                                "factors": already[:3]}],
                    "kind": "reading"}),
        json.dumps({"answer": [{"text": "There is a piece I have not mentioned yet.",
                                "factors": [natal.factors[7]]}],
                    "kind": "reading"}),
    ])
    reply = await _ask(
        provider, natal, question="and what else?", already_cited=already,
    )
    assert len(provider.calls) == 2
    assert "already used in this conversation" in provider.calls[1]["prompt"]
    assert reply.cited_factors == (natal.factors[7],)


async def test_a_follow_up_early_in_a_thread_is_not_called_a_rut(natal):
    """Below three named placements the overlap is arithmetic, not evidence."""
    provider = _turn({"answer": [{"text": "It is why you check twice, and here is how.",
                                  "factors": [natal.factors[0]]}],
                      "kind": "reading"})
    reply = await _ask(
        provider, natal, question="why?", already_cited=[natal.factors[0]],
    )
    assert len(provider.calls) == 1
    assert reply.cited_factors == (natal.factors[0],)


async def test_only_one_attempt_is_ever_spent_on_style(natal):
    """A turn that trips two quality fences must not spend the reader's budget.

    Every fence here is about how a reply reads, not whether it is true. The
    hard checks — an invented placement, a claim about somebody's death — are
    what the remaining attempts are for, and a 422 is the thing none of them
    may cause.
    """
    same = json.dumps({"answer": [{"text": _REFUSED_CALENDARS, "factors": []}], "kind": "aside"})
    provider = ScriptedProvider(responses=[same, same, same])
    reply = await _ask(
        provider, natal, question="what day is it?", history=[("alma", _REFUSED_SKIES)],
    )
    assert len(provider.calls) == 2, "one nudge, then whatever came back ships"
    assert reply.text() == _REFUSED_CALENDARS


async def test_a_reader_who_writes_in_cyrillic_is_answered_in_cyrillic(natal):
    """The exact string from the bug report, and what must not come back."""
    provider = ScriptedProvider(responses=[
        json.dumps({"answer": [{"text": "I read all languages. You wrote in Russian, and "
                                        "I am listening. What would you like to know?",
                                "factors": []}],
                    "kind": "aside"}),
        json.dumps({"answer": [{"text": "Привет. Что бы вы хотели узнать из своей карты?",
                                "factors": []}],
                    "kind": "aside"}),
    ])
    reply = await _ask(provider, natal, question="Хелли шл/ха")
    assert len(provider.calls) == 2
    assert "the language they wrote to you in" in provider.calls[1]["prompt"]
    assert not conversation._wrong_script("Хелли шл/ха", reply.text())


def test_a_thread_where_she_already_declined_says_so_in_the_prompt(natal):
    """A repeat ask is information, and nothing told her that."""
    prompt = conversation.build_prompt(
        question="i'm just going to stop it",
        results=[natal],
        history=[
            ("user", "i want to come off my medication"),
            ("alma", "I cannot advise on that. It is between you and your prescriber."),
        ],
    )
    assert "ALREADY DECLINED" in prompt
    assert "do not decline it the same way" in prompt


# ── what she cannot see ────────────────────────────────────────────────────

def test_the_prompt_names_the_systems_that_could_not_be_calculated(natal):
    """The router has always known; until now it collected the list and dropped it."""
    prompt = conversation.build_prompt(
        question="what is happening for me this week?",
        results=[natal],
        missing=["transits", "compatibility"],
    )
    assert "transits" in prompt
    assert "compatibility" in prompt


# ── chapter structure ──────────────────────────────────────────────────────

def test_every_system_has_chapters():
    from alma.calc import SYSTEMS

    for system in SYSTEMS:
        assert chapters.for_system(system), f"{system} has no chapters"


def test_the_natal_chart_has_sixteen_chapters():
    assert len(chapters.NATAL) == 16


def test_chapter_slugs_are_unique_within_a_system():
    for system, defined in chapters.BY_SYSTEM.items():
        slugs = [c.slug for c in defined]
        assert len(slugs) == len(set(slugs)), f"{system} has a duplicate chapter slug"


def test_every_system_has_exactly_one_free_chapter():
    """The sample. Two would give away the product; none would sell nothing."""
    for system, defined in chapters.BY_SYSTEM.items():
        free = [c for c in defined if c.free]
        assert len(free) == 1, f"{system} has {len(free)} free chapters"


def test_most_natal_chapters_find_something_to_read(natal):
    covered = [
        c.slug for c in chapters.NATAL if chapters.relevant_factors(c, natal.factors)
    ]
    assert len(covered) >= 14, f"only {len(covered)} of 16 chapters had factors"


def test_the_preview_lists_what_can_be_written(natal):
    listing = writer.preview(natal)
    assert listing["total"] == 16
    assert listing["available"] >= 14
    assert sum(1 for c in listing["chapters"] if c["free"]) == 1


# ══════════════════════════════════════════════════════════════════════════
#  Sensitivity — the test that proves the reading is actually about you
# ══════════════════════════════════════════════════════════════════════════

def _house_chapter_inputs(birth: BirthData) -> dict[str, set[str]]:
    """The factors each time-dependent chapter would be written from."""
    result = compute("natal", birth)
    return {
        chapter.slug: set(chapters.relevant_factors(chapter, result.factors))
        for chapter in chapters.NATAL
        if chapter.time_dependent
    }


def _difference(before: set[str], after: set[str]) -> float:
    if not before and not after:
        return 0.0
    return len(before ^ after) / len(before | after)


def test_two_hours_of_birth_time_rewrites_the_house_chapters():
    """The spec's threshold: house-derived sections must differ by ≥40%.

    Not a style check. If the inputs to a chapter barely move when the birth
    time moves two hours, then the chapter was never really about the houses,
    and every customer is getting approximately the same reading.
    """
    early = _house_chapter_inputs(SOFIA)
    later = _house_chapter_inputs(
        BirthData(
            date=SOFIA.date, time="06:20", latitude=SOFIA.latitude,
            longitude=SOFIA.longitude, timezone=SOFIA.timezone, name=SOFIA.name,
        )
    )

    changes = {slug: _difference(early[slug], later[slug]) for slug in early}
    moved = [slug for slug, delta in changes.items() if delta >= 0.40]
    assert len(moved) >= len(changes) // 2, (
        "two hours of birth time barely changed the house chapters: "
        + ", ".join(f"{slug} {delta:.0%}" for slug, delta in sorted(changes.items()))
    )


def test_a_different_birth_date_rewrites_almost_everything():
    """The spec's second threshold: ≥70% of the inputs must change."""
    mine = compute("natal", SOFIA)
    theirs = compute(
        "natal",
        BirthData(
            date=date(1975, 11, 29), time="13:05", latitude=SOFIA.latitude,
            longitude=SOFIA.longitude, timezone=SOFIA.timezone, name=SOFIA.name,
        ),
    )
    delta = _difference(set(mine.factors), set(theirs.factors))
    assert delta >= 0.70, f"two unrelated births share {1 - delta:.0%} of their factors"


def test_one_minute_of_birth_time_still_changes_the_chart():
    """Precision claimed is precision that must exist."""
    mine = compute("natal", SOFIA)
    nudged = compute(
        "natal",
        BirthData(
            date=SOFIA.date, time="04:21", latitude=SOFIA.latitude,
            longitude=SOFIA.longitude, timezone=SOFIA.timezone, name=SOFIA.name,
        ),
    )
    assert mine.data["angles"]["ascendant"] != nudged.data["angles"]["ascendant"]


def test_the_prompt_itself_differs_between_two_people():
    """The end-to-end version: two people cannot be sent the same prompt."""
    chapter = chapters.find("natal", "core")

    def prompt_for(birth):
        result = compute("natal", birth)
        return writer.build_prompt(
            result, chapter, offered=chapters.relevant_factors(chapter, result.factors)
        )

    mine = prompt_for(SOFIA)
    theirs = prompt_for(
        BirthData(
            date=date(1975, 11, 29), time="13:05", latitude=-23.5505, longitude=-46.6333,
            timezone="America/Sao_Paulo", name="Someone Else",
        )
    )
    shared = set(mine.split("\n")) & set(theirs.split("\n"))
    assert len(shared) < len(mine.split("\n")) * 0.4, "two people got near-identical prompts"


async def test_a_truncated_attempt_is_retried_shorter(natal):
    """The model running past `max_tokens` is a complaint, not a dead end.

    Found on a phone rather than in a test: chapter I of a real natal chart —
    the free sample that has to sell the other fifteen — came back cut off, the
    provider refused the truncated JSON, and the reader showed "Something on our
    side is not working". Nothing here could see it, because a scripted provider
    never counts tokens.

    Raising the ceiling is the other lever and is deliberately not pulled: the
    reply repeats every paragraph's factor strings verbatim, so its size scales
    with the density of the chart, and `cost.guard` already refuses a free-tier
    generation near the current ceiling at the strong model's prices.
    """
    from alma.ai.provider import AnswerTruncated

    chapter = chapters.find("natal", "core")
    offered = chapters.relevant_factors(chapter, natal.factors)
    provider = ScriptedProvider(
        responses=[
            AnswerTruncated("claude-sonnet-5 reached max_tokens=1560"),
            _reply([("Fine.", offered[:1]), ("Also.", offered[:1])]),
        ]
    )

    written = await writer.write(
        result=natal, chapter=chapter, provider=provider, model="claude-opus-5"
    )

    assert written.attempts == 2
    assert "ran past the length limit" in provider.calls[1]["prompt"], (
        "the second attempt has to be told what was wrong, like every other retry"
    )


async def test_a_chapter_truncated_every_time_is_still_reported(natal):
    """Three cut-off attempts is a real failure and must reach the reader.

    The retry above must not turn an out-of-budget chapter into a silent
    infinite loop, and it must not be swallowed into a generic refusal either:
    the message names the model and the ceiling, which is what tells an operator
    which number to change.
    """
    from alma.ai.provider import AnswerTruncated

    chapter = chapters.find("natal", "core")
    provider = ScriptedProvider(
        responses=[AnswerTruncated("cut off") for _ in range(writer.MAX_ATTEMPTS)]
    )

    with pytest.raises(AnswerTruncated):
        await writer.write(
            result=natal, chapter=chapter, provider=provider, model="claude-opus-5"
        )
    assert len(provider.calls) == writer.MAX_ATTEMPTS


async def test_her_own_broken_sentences_are_not_read_back_to_her(natal):
    """A thread that already contains the bug must not keep producing it.

    The owner's own thread carries both refusals from the screenshot. Handed
    twelve turns of that as its own past behaviour, the live model reproduced
    it — in Russian, where none of the English patterns can see it — and took
    three attempts and a 422 to stop. These sentences are already known to be
    false and are the exact thing `CHAT_FORBIDDEN` refuses to ship; putting
    them back in front of her is teaching.
    """
    poisoned = "I cannot read this question — the text appears to be in Cyrillic script, " \
               "and I read English only."
    prompt = conversation.build_prompt(
        question="Хелли шл/ха",
        results=[natal],
        history=[
            ("user", "Хелли шл/ха"),
            ("alma", poisoned),
            ("user", "Hello Shaka a"),
            ("alma", "Your Moon is in Pisces, which is worth talking about."),
        ],
    )
    assert "English only" not in prompt
    assert "Your Moon is in Pisces" in prompt, "the good turns still carry"
    assert "Hello Shaka a" in prompt, "and so does everything they said"


async def test_a_truncated_chat_turn_is_retried_rather_than_thrown(natal):
    """A two-part question cost the reader their whole turn.

    Reproduced live against the real model: *"How does my mind work? Tell me
    about my Mercury and the hard aspects in my chart"* — an ordinary thing to
    type — reached `max_tokens` and `AnswerTruncated` travelled all the way out
    of `answer`, so the reply was an error rather than a sentence. `writer.write`
    had handled this since a free sample chapter died of it on a phone; this
    path never did.

    The complaint has to say more than "be shorter": told only that, a model
    answers half a two-part question well and drops the other half in silence.
    """
    from alma.ai.provider import AnswerTruncated

    provider = ScriptedProvider(
        responses=[
            AnswerTruncated("claude-sonnet-5 reached max_tokens=4096"),
            json.dumps(
                {
                    "answer": [{"text": "Shorter.", "factors": [natal.factors[0]]}],
                    "answered_from_chart": True,
                }
            ),
        ]
    )

    reply = await conversation.answer(
        question="How does my mind work, and what are my hard aspects?",
        results=[natal], provider=provider, model="claude-haiku-4-5",
    )

    assert reply.cited_factors == (natal.factors[0],)
    retry = provider.calls[1]["prompt"]
    assert "ran past the length limit" in retry
    assert "answer every part of it" in retry, (
        "being told only to shorten invites her to silently drop the second question"
    )


async def test_a_chat_turn_truncated_every_time_still_reaches_the_operator(natal):
    """The retry must not hide a ceiling that is genuinely too low."""
    from alma.ai.provider import AnswerTruncated

    provider = ScriptedProvider(
        responses=[AnswerTruncated("cut off") for _ in range(conversation.MAX_ATTEMPTS)]
    )

    with pytest.raises(AnswerTruncated):
        await conversation.answer(
            question="Tell me everything.", results=[natal],
            provider=provider, model="claude-haiku-4-5",
        )
    assert len(provider.calls) == conversation.MAX_ATTEMPTS
