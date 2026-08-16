"""The free taste of the natal chart: a few plain sentences per sphere of life.

The owner's brief, from the reference he chose (a Russian natal-chart site the
whole category copies): the chart page opens with the wheel, then the placements,
then **short free interpretations per sphere — love, money, career — with the
full reading behind the price**. Alma had the wheel's data and the paid chapters
and nothing in between: a visitor saw sixteen titles and one free chapter, and
the titles do not demonstrate the writing.

So this writes the in-between, once per chart per language: five spheres, two or
three sentences each, every one citing the placement it was read from, on the
cheap model, cached in the same `reading` table as everything else. It is the
shop window for the sixteen doors above it — which is why each sphere carries
the slug of the chapter that finishes the thought.

The rules are the product's rules, not marketing's:

* **Plain language.** These are read by somebody who does not know what a
  quincunx is and never will. The prompt forbids jargon outright; a term that
  cannot be avoided must be explained in the same sentence.
* **Cited, like everything else.** Each sphere names its factors, the validator
  refuses an uncited block, and `geometry.drift` refuses a described aspect the
  chart contradicts — the same three gates a paid chapter passes.
* **One generation for all five.** Five separate calls would be five times the
  latency and five times the per-call overhead for ~150 words of output each;
  one call returns a JSON array and the validator walks it block by block.
"""

from __future__ import annotations

import logging

from .. import i18n
from ..calc import CalcResult
from . import cost, geometry, validator, voice
from .provider import AnswerTruncated, Completion, ModelUnavailable, Provider
from .validator import Paragraph
from .writer import ReadingRefused

log = logging.getLogger("alma.ai.spheres")

MAX_ATTEMPTS = 3


#: The chart notation that must never reach the prose. The factor strings the
#: model is shown are full of it — that is what a citation looks like — and
#: the model pastes them into sentences unless refused. The prompt already
#: forbids it; this is the gate that makes the prohibition true, the same way
#: `geometry.drift` makes the no-contradictions rule true.
_GLYPHS = frozenset("☉☽☿♀♂♃♄♅♆♇☊☋⚷⚸□△☍⚹⚺⚻☌℞")

#: The spheres, in the order they are shown, each naming the natal chapter that
#: sells the full version. The slugs are `chapters.NATAL` slugs and a test pins
#: that, because a sphere pointing at a chapter that does not exist is a "Full
#: reading" button that 404s.
SPHERES: tuple[tuple[str, str], ...] = (
    ("core", "core"),
    ("love", "love"),
    ("money", "money"),
    ("career", "career"),
    ("mind", "mind"),
)

#: Room for five short blocks plus the JSON around them. Measured: a full
#: five-sphere answer is ~700 output tokens; 2048 leaves room for the model
#: to think without inviting an essay. Doubled once the mid model took
#: over: it reasons before it writes, and the reasoning spent the whole
#: old ceiling before a word landed — measured as an 87-second empty
#: answer on the owner's own test.
MAX_TOKENS = 6000

SPHERES_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "spheres": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sphere": {"type": "string"},
                    "text": {"type": "string"},
                    "factors": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                    },
                },
                "required": ["sphere", "text", "factors"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["spheres"],
    "additionalProperties": False,
}


def build_prompt(result: CalcResult, *, locale: str, complaint: str | None = None) -> str:
    lines: list[str] = []
    lines.append(
        "Write the free preview of this person's natal chart: one short block "
        "for each sphere listed below, in the language of this reading."
    )
    lines.append("")
    lines.append("SPHERES, in order: " + ", ".join(key for key, _ in SPHERES) + ".")
    lines.append("")
    lines.append(
        "Each block is TWO or THREE short sentences. Plain words only — this is "
        "read by somebody who has never opened an astrology book. No jargon: if "
        "a placement must be named, say what it means in the same breath "
        "('Venus in your seventh house — the house of partners — …'). Never "
        "paste glyph notation into the text — no ☉, □ or ♄; spell every body "
        "and aspect out in words. The glyphs belong only in the `factors` "
        "array, copied exactly. Each block must copy at least one factor from "
        "the list below into its `factors` array, exactly as written. Say "
        "something specific enough to be worth reading; never predict events; "
        "never mention what is not in the list."
    )
    if locale == "ru":
        lines.append("")
        lines.append(
            "ПО-РУССКИ: обращайся на «ты» и не выдавай пол человека — никаких "
            "«ты рождён», «ты должна», «ты сам». Используй настоящее время и "
            "безличные обороты: «ты появляешься на свет», «от тебя требуется»."
        )
    lines.append("")
    lines.append("THE FACTORS — the entire world for this reading:")
    for factor in result.factors:
        lines.append(f"- {factor}")
    if complaint:
        lines.append("")
        lines.append(f"YOUR PREVIOUS REPLY WAS REJECTED. Fix exactly this: {complaint}")
    return "\n".join(lines)


async def write(
    result: CalcResult,
    *,
    provider: Provider,
    model: str,
    locale: str = "en",
) -> tuple[list[dict], cost.Spend]:
    """Five cited blocks, or `ReadingRefused` — never four and a shrug.

    All five or nothing, because the client renders the set as one section and
    a missing sphere reads as a broken screen, not as an editorial choice.
    """
    system = voice.system_prompt(locale=locale, paid=False)
    latin = i18n.resolve(locale) in ("en", "es", "de", "it", "fr", "pt-BR")
    script_scale = 1.0 if latin else 2.0
    # The mid model reasons before it writes; the ceiling carries that head
    # room, and Cyrillic carries double — the same words, twice the tokens.
    max_tokens = floor = 2600 if latin else MAX_TOKENS
    tally = cost.Ledger()
    complaint: str | None = None
    #: See the `wrote_nothing` branch: `None` until a call proves it thinks
    #: until the allowance is gone, and turned down from there.
    effort: str | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = build_prompt(result, locale=locale, complaint=complaint)
        # As much of the allowance as the ceiling already pays for — see
        # `cost.affordable_output`. Unused output tokens cost nothing, so a
        # ceiling set below what the budget affords buys no saving and only
        # buys truncation; the 800 characters are headroom for the complaint a
        # later attempt carries. Raises only, so every refusal below stands.
        # Recomputed every attempt with the prompt in hand, and allowed back
        # down: a retry carries the complaint, so it buys fewer output tokens
        # for the same money, and a first attempt that claimed exactly what the
        # ceiling affords would put the retry over it. `floor` keeps the
        # recomputation from starving the call. See `cost.affordable_output`.
        max_tokens = max(floor, min(MAX_TOKENS, cost.affordable_output(
            model, prompt_chars=len(prompt) + len(system),
            paid=False, scale=script_scale, most=MAX_TOKENS,
        )))
        cost.guard(model, prompt_chars=len(prompt) + len(system), max_output_tokens=max_tokens, paid=False, scale=script_scale)
        try:
            completion: Completion = await provider.complete(
                system=system,
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                schema=SPHERES_SCHEMA,
                # Alma's voice is identical for every reader of a locale; at
                # any real traffic the system block is a cache read, not a
                # fresh bill.
                cache_system=True,
                effort=effort,
            )
        except AnswerTruncated as exc:
            if exc.wrote_nothing:
                # **Not a length problem, so "be shorter" is not an answer.**
                #
                # Nothing was written at all: the whole allowance went on
                # deliberation before a word of prose existed. Asking that run
                # to be brief is asking it to fix a problem it does not have,
                # and it burns the remaining attempts writing nothing again —
                # which is exactly how a Russian daily failed three times in a
                # row. Turn the thinking down instead; that is the one lever
                # that changes the split between reasoning and words.
                effort = "low" if effort == "medium" else "medium"
                complaint = None
                log.warning(
                    "spheres attempt %d spent its whole allowance thinking; "
                    "thinking turned down to %s: %s",
                    attempt, effort, exc,
                )
            else:
                complaint = (
                    "Your reply ran past the length limit. Two sentences per "
                    "sphere, no more."
                )
                log.warning("spheres attempt %d truncated: %s", attempt, exc)
            if attempt == MAX_ATTEMPTS:
                raise
            continue

        tally.record(cost.cost(
            model, completion.input_tokens, completion.output_tokens,
            cache_read_tokens=completion.cache_read_tokens,
            cache_write_tokens=completion.cache_write_tokens,
        ))
        tally.check(paid=False, scale=script_scale, attempts=MAX_ATTEMPTS)

        try:
            payload = completion.json()
        except (ValueError, TypeError):
            complaint = "Your reply was not valid JSON in the required shape."
            continue

        blocks = payload.get("spheres") or []
        wanted = [key for key, _ in SPHERES]
        by_key = {
            str(block.get("sphere", "")).strip(): block
            for block in blocks
            if isinstance(block, dict)
        }
        if sorted(by_key) != sorted(wanted):
            complaint = (
                "Return exactly one block per sphere, with `sphere` set to one "
                f"of: {', '.join(wanted)}."
            )
            continue

        paragraphs = [
            Paragraph(
                text=str(by_key[key].get("text", "")).strip(),
                factors=tuple(
                    str(f).strip() for f in (by_key[key].get("factors") or [])
                ),
            )
            for key in wanted
        ]
        verdict = validator.check(paragraphs, allowed=result.factors, minimum=len(wanted))
        if not verdict.ok:
            complaint = verdict.complaint()
            log.warning("spheres attempt %d rejected: %s", attempt, ", ".join(verdict.reasons))
            continue

        joined = " ".join(p.text for p in paragraphs)
        breaches = validator.safety(joined)
        if breaches:
            complaint = "The text broke a rule: " + "; ".join(breaches)
            continue
        leaked = sorted({c for c in joined if c in _GLYPHS})
        if leaked:
            complaint = (
                "Glyph notation leaked into the text: " + " ".join(leaked)
                + ". Spell every body and aspect out in words; glyphs belong "
                "only in the `factors` array."
            )
            log.warning("spheres attempt %d glyphs in prose: %s", attempt, leaked)
            continue
        # The same plain-language gate the chapters carry — see `writer.py`.
        # The spheres are the free taste, which makes ornate writing more
        # expensive here than anywhere: it is the first prose most people read.
        ornate = validator.plain_language(joined, locale)
        if ornate:
            complaint = (
                "The writing has to change before this can be published: "
                + "; ".join(ornate[:4])
                + ". Say the same things the same way you would to one person "
                "across a table."
            )
            log.warning("spheres attempt %d plain-language: %s", attempt, ornate[:2])
            continue

        if locale == "ru":
            leaked = validator.russian_latin_leak(joined, result.factors)
            if leaked:
                complaint = (
                    "В русском тексте остались английские слова: "
                    + ", ".join(leaked[:5]) + ". Переведи их."
                )
                log.warning("spheres latin leak: %s", leaked[:5])
                continue
            caught = validator.russian_gendered(joined)
            if caught:
                complaint = (
                    "Эти обороты выдают пол читателя: "
                    + ", ".join(f"«{b.strip()}»" for b in caught)
                    + ". Перепиши в настоящем времени или безличным оборотом."
                )
                log.warning("spheres attempt %d gendered ru: %s", attempt, caught)
                continue
        wrong = geometry.drift(joined, result.factors)
        if wrong:
            complaint = wrong.complaint()
            log.warning(
                "spheres attempt %d geometry: %d contradicted, %d unsupported",
                attempt, len(wrong.contradicted), len(wrong.unsupported),
            )
            continue

        written = [
            {
                "sphere": key,
                "chapter": chapter,
                "text": paragraphs[index].text,
                "factors": list(paragraphs[index].factors),
            }
            for index, (key, chapter) in enumerate(SPHERES)
        ]
        return written, _spent(tally, model)

    raise ReadingRefused(
        "the spheres could not be written from this chart", spend=_spent(tally, model)
    )


def _spent(tally: cost.Ledger, model: str) -> cost.Spend:
    """The whole run as one `Spend`, keeping the dollars already priced."""
    return tally.total(model)
