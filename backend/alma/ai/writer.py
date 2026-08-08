"""Turning a CalcResult into a chapter, and refusing to ship a bad one.

The loop is: build a prompt containing the factors this chapter may read from,
generate, validate the citations, and — if the model invented something or
wrote an unsourced paragraph — tell it exactly what was wrong and try again.
After the last attempt the reading is refused rather than degraded. Shipping a
chapter with one invented placement in it is worse than shipping nothing,
because the invented one reads exactly as confidently as the rest.

The prompt is deliberately not clever. It contains the factor list verbatim,
the question the chapter answers, and the length. Everything that makes the
writing good lives in `voice.py`, where it can be edited by someone who is
thinking about the writing rather than about the code.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from .. import i18n
from ..calc import CalcResult
from . import chapters as chapter_defs
from . import cost, geometry, validator, voice
from .provider import AnswerTruncated, Completion, ModelUnavailable, Provider
from .validator import Paragraph

log = logging.getLogger("alma.ai.writer")

MAX_ATTEMPTS = 3

#: The line below which we regenerate rather than ship, for a piece that has
#: no opinion of its own. Every `Chapter` carries `paragraphs` and this is that
#: field's default, so nothing in `chapters.py` changed when it moved there;
#: it stays here because the truncation complaint below is written in terms of
#: it and because a caller with a bare `Chapter` should not have to know.
MIN_PARAGRAPHS = 2

#: The shape every chapter comes back in. Enforced by the server, so the
#: factor arrays are always present and always arrays.
CHAPTER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "teaser": {
            "type": "string",
            "description": "One sentence, always visible, that names what this chapter found.",
        },
        "paragraphs": {
            "type": "array",
            # The API accepts only 0 or 1 here — `"minItems": 2` is rejected
            # outright with a 400, which no test caught because every test
            # drives a scripted provider that never sees the schema. The real
            # floor is two paragraphs and it is enforced in `validator.py`,
            # which is the honest place for it anyway: a schema constrains
            # what the model may emit, and a validator decides what we are
            # willing to ship. Only the second one can refuse.
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "factors": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                        "description": (
                            "The factor strings this paragraph was read from, "
                            "copied exactly from the list provided."
                        ),
                    },
                },
                "required": ["text", "factors"],
                "additionalProperties": False,
            },
        },
        "advice": {
            "type": "string",
            "description": "One concrete thing to do or stop doing. May be empty.",
        },
    },
    "required": ["title", "teaser", "paragraphs"],
    "additionalProperties": False,
}


def schema_for(chapter: chapter_defs.Chapter) -> dict:
    """`CHAPTER_SCHEMA`, minus whatever this piece does not want asked.

    Today that is one field. A piece with `advice=False` is not sent the
    property at all, rather than being sent it and having the answer thrown
    away: the second still spends the tokens, and still invites the model to
    put the instruction it was told not to write into the paragraphs beside it.

    `advice` is not in `required`, so removing the property leaves a schema of
    the same shape. `Written.advice` is forced empty in `write` regardless, so
    a provider that ignores the schema cannot put it back.
    """
    if chapter.advice:
        return CHAPTER_SCHEMA
    trimmed = dict(CHAPTER_SCHEMA)
    trimmed["properties"] = {
        key: value
        for key, value in CHAPTER_SCHEMA["properties"].items()
        if key != "advice"
    }
    return trimmed


class ReadingRefused(Exception):
    """The model could not produce a reading that only cites real factors.

    Carries what the attempts cost. The refusal path is the *expensive* one —
    three generations rather than one — and for a long time it was the only
    path that recorded nothing at all: the router turned this into a 422
    before it reached `_spend`, so a request that burned three chapters' worth
    of tokens moved the month ledger by zero. Nothing then bounded how many
    such requests an account could make, because the only thing counting them
    was skipped exactly when they failed.
    """

    def __init__(self, message: str, spend: cost.Spend | None = None) -> None:
        super().__init__(message)
        self.spend = spend or cost.cost("", 0, 0)


@dataclass(frozen=True, slots=True)
class Written:
    system: str
    chapter: str
    title: str
    teaser: str
    paragraphs: tuple[Paragraph, ...]
    advice: str
    cited_factors: tuple[str, ...]
    model: str
    attempts: int
    spend: cost.Spend
    warnings: tuple[str, ...] = ()

    def text(self) -> str:
        return "\n\n".join(p.text for p in self.paragraphs)

    def as_dict(self) -> dict:
        return {
            "system": self.system,
            "chapter": self.chapter,
            "title": self.title,
            "teaser": self.teaser,
            "body": [p.text for p in self.paragraphs],
            "paragraph_factors": [list(p.factors) for p in self.paragraphs],
            "advice": self.advice,
            "cited_factors": list(self.cited_factors),
            "read_from": "Read from: " + " · ".join(self.cited_factors[:4])
            if self.cited_factors
            else "",
            "model": self.model,
            "attempts": self.attempts,
            "warnings": list(self.warnings),
        }


def _words(system: str, chapter: chapter_defs.Chapter, locale: str) -> i18n.ChapterWords:
    """This chapter's title and question, in the reader's language.

    The chapter's own English is handed over as the fallback, so a `Chapter`
    that was never in `BY_SYSTEM` — a test fixture, a chapter being tried out
    — still has words rather than raising.
    """
    return i18n.chapter_words(
        system,
        chapter.slug,
        locale=locale,
        default=i18n.ChapterWords(chapter.title, chapter.question),
    )


def build_prompt(
    result: CalcResult,
    chapter: chapter_defs.Chapter,
    *,
    offered: list[str],
    complaint: str | None = None,
    locale: str = "en",
) -> str:
    """The user turn: this person, this chapter, these facts.

    The whole factor list is included even though the chapter only reads from
    part of it — a chapter that can see the rest of the chart writes better
    sentences about its own corner, and the `offered` list is what it is told
    to lean on.

    The chapter's title and question arrive in the reader's language while
    everything else in the prompt stays English. That is not an inconsistency:
    the factor list is identifiers, checked character by character, and the
    rest is instruction, but the question is the one line here that is a piece
    of the *product* — it is what the reader tapped, and asking it in English
    and demanding an answer in German is asking the model to translate the
    brief before it starts. It also anchors the title the model writes back to
    the one on the screen they came from.
    """
    words = _words(result.system, chapter, locale)
    subject = result.subject
    least, most = chapter.paragraphs
    shape = f"in {least} to {most} paragraphs" if most > least else (
        "in one paragraph" if least == 1 else f"in {least} paragraphs"
    )
    lines = [
        f"SYSTEM: {result.system}",
        f"CHAPTER: {words.title} — {words.question}",
        f"LENGTH: {chapter.words[0]}–{chapter.words[1]} words, {shape}.",
        # The owner's plainness rule, stated where the model can obey it:
        # the reader has never opened an astrology book, and a term used
        # without its everyday meaning is a sentence they skip.
        "PLAIN LANGUAGE: the reader knows nothing about astrology or "
        "numerology. Any technical term you use, explain in everyday words "
        "the first time — or don't use it. Short sentences beat ornate ones.",
        # The Russian rules ride in the first prompt rather than arriving as a
        # rejection: the owner watched three attempts burn on «ты был» because
        # the model only learned the rule from the complaint. Stated up front,
        # the first answer passes and the screen never says she is silent.
        *(
            [
                "ПО-РУССКИ: обращайся на «ты»; не выдавай пол читателя — никаких "
                "«ты родился», «ты был», «ты должен», «ты сама»: используй "
                "настоящее время и безличные обороты («ты появляешься на свет», "
                "«от тебя требуется»). Латиницей в тексте может быть только "
                "слово Alma — все планеты и знаки пиши по-русски."
            ]
            if i18n.resolve(locale) == "ru"
            else []
        ),
        "",
        "THE PERSON",
        f"- born {subject['date']}" + (f" at {subject['time']}" if subject["time"] else ""),
        f"- birth time known: {'yes' if subject['time_known'] else 'no'}",
    ]
    if subject.get("place"):
        lines.append(f"- birthplace: {subject['place']}")
    if subject.get("name"):
        lines.append(f"- name: {subject['name']}")

    lines += ["", "FACTORS THIS CHAPTER IS READ FROM — cite these:"]
    lines += [f"- {factor}" for factor in offered] or ["- (none)"]

    other = [f for f in result.factors if f not in offered]
    if other:
        lines += [
            "",
            "THE REST OF THE CHART — context you may cite if it genuinely belongs here:",
        ]
        lines += [f"- {factor}" for factor in other]

    if result.unavailable:
        lines += ["", "WHAT COULD NOT BE CALCULATED — say so if it is relevant:"]
        lines += [f"- {reason}" for reason in result.unavailable]

    if result.notes:
        lines += ["", "NOTES ABOUT THIS CALCULATION:"]
        lines += [f"- {note}" for note in result.notes]

    if complaint:
        lines += [
            "",
            "YOUR PREVIOUS ATTEMPT WAS REJECTED. Fix exactly this:",
            complaint,
        ]

    return "\n".join(lines)


async def write(
    *,
    result: CalcResult,
    chapter: chapter_defs.Chapter,
    provider: Provider,
    model: str,
    locale: str = "en",
    paid: bool = False,
    memory: list[str] | None = None,
    ledger: cost.Ledger | None = None,
    register: str | None = None,
) -> Written:
    """Generate one chapter, validating every claim it makes.

    `register` picks the voice block and defaults to what `paid` has always
    chosen. It exists so that a caller can spend against the tight free-tier
    ceiling while still asking for a register that is not the free sample —
    see the note on `voice.system_prompt`. Everything else here is unchanged
    and deliberately so: whatever is written through this function is
    validated, retried and refused by the same three rules, and the daily
    going through it is the point rather than a convenience.
    """
    offered = chapter_defs.relevant_factors(chapter, result.factors)
    if not offered:
        raise ReadingRefused(
            f"the {chapter.slug} chapter has no factors to read from in this "
            f"{result.system} result — the chart genuinely says nothing here"
        )

    system = voice.system_prompt(
        locale=locale, paid=paid, memory=memory, register=register
    )
    tally = ledger or cost.Ledger()
    # Where this chapter's own spending starts in a ledger it may be sharing.
    # `write_system` hands one Ledger to every chapter, so reading the whole
    # tally at the end reported chapter one's tokens inside chapter two's
    # `Written.spend`, chapter one and two inside chapter three, and so on —
    # summing sixteen of those over-counts a natal report by roughly eight
    # times. The single-chapter route already charges `written.spend` to the
    # month ledger, so the day a whole-report route exists that arithmetic
    # would refuse every account after one report.
    opening = len(tally.spends)
    # Three tokens a word is an English number. Cyrillic tokenises at roughly
    # twice that — measured live: the Russian astrocartography sample hit a
    # 1560-token ceiling three attempts in a row and the one chapter that
    # exists to sell the system answered 503 in the owner's own hands. The
    # multiplier is per-script, not per-model: every current tokenizer treats
    # non-Latin scripts about the same way.
    latin = i18n.resolve(locale) in ("en", "es", "de", "it", "fr", "pt-BR")
    per_word = 3 if latin else 6
    script_scale = 1.0 if latin else 2.0
    max_tokens = min(8192, chapter.words[1] * per_word + 600)
    least_paragraphs = chapter.paragraphs[0]
    schema = schema_for(chapter)

    complaint: str | None = None
    last: validator.Verdict | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = build_prompt(
            result, chapter, offered=offered, complaint=complaint, locale=locale
        )
        cost.guard(
            model,
            prompt_chars=len(prompt) + len(system),
            max_output_tokens=max_tokens,
            paid=paid,
        )

        try:
            completion = await _generate(
                provider, system, prompt, model, max_tokens, schema=schema
            )
        except AnswerTruncated as exc:
            # **The model wrote past the ceiling.** Retried rather than
            # surfaced, because the loop already exists for exactly this shape
            # of problem — unparseable JSON, an invented factor, a forbidden
            # claim — and "you went on too long" is another complaint the model
            # can act on. Left unhandled it propagated out of the whole call,
            # and what a reader saw on the *free sample chapter that sells
            # the other fifteen* was "Something on our side is not working".
            #
            # Found by opening chapter I of a real natal chart on a phone. No
            # test could have caught it: every test drives a scripted provider
            # that never counts tokens and never truncates.
            #
            # The other lever is a bigger ceiling, and it is deliberately not
            # pulled. The reply is a JSON envelope in which every paragraph
            # repeats its factor strings verbatim, so the cost scales with the
            # density of the chart rather than with the word count — and
            # `cost.guard` refuses a free-tier generation over
            # `ALMA_FREE_USER_BUDGET` at the *strong* model's prices, which the
            # current ceiling is already close to. Raising it would trade a
            # visible failure for an invisible one: chapters that quietly stop
            # being written for anybody on the free tier.
            complaint = (
                "Your reply ran past the length limit and was cut off. Write "
                f"noticeably shorter: at most {chapter.words[1]} words in total "
                f"across {least_paragraphs} or {least_paragraphs + 1} paragraphs, "
                "and cite only the factors each paragraph actually reads from."
            )
            log.warning(
                "chapter %s/%s attempt %d was truncated: %s",
                result.system, chapter.slug, attempt, exc,
            )
            if attempt == MAX_ATTEMPTS:
                raise
            continue

        tally.record(cost.cost(
            model, completion.input_tokens, completion.output_tokens,
            cache_read_tokens=completion.cache_read_tokens,
            cache_write_tokens=completion.cache_write_tokens,
        ))
        tally.check(paid=paid, scale=script_scale)

        try:
            payload = completion.json()
        except (ValueError, TypeError) as exc:
            complaint = "Your reply was not valid JSON in the required shape."
            log.warning("chapter %s/%s: unparseable reply: %s", result.system, chapter.slug, exc)
            continue

        title, paragraphs = validator.parse(payload)
        verdict = validator.check(
            paragraphs,
            allowed=result.factors,
            offered=offered,
            # A chapter is not a chapter at one paragraph. This used to be
            # `"minItems": 2` in CHAPTER_SCHEMA, which the API rejects with a
            # 400 — and no test caught it, because every test drives a
            # scripted provider that never sends the schema anywhere. It is
            # read off the chapter now: the daily is honestly one paragraph
            # and says so, and every chapter in `chapters.py` still says two
            # because that is the field's default.
            minimum=least_paragraphs,
        )
        last = verdict

        if not verdict.ok:
            complaint = verdict.complaint()
            log.warning(
                "chapter %s/%s attempt %d rejected: %s",
                result.system, chapter.slug, attempt, ", ".join(verdict.reasons),
            )
            continue

        body = "\n\n".join(p.text for p in paragraphs)
        breaches = validator.safety(body)
        if breaches:
            complaint = (
                "The reading broke a rule: "
                + "; ".join(breaches)
                + ". Describe the disposition, never the event, and leave the "
                "decision with the reader."
            )
            log.warning("chapter %s/%s safety: %s", result.system, chapter.slug, breaches)
            continue

        if i18n.resolve(locale) == "ru":
            leaked = validator.russian_latin_leak(body)
            if leaked:
                complaint = (
                    "В русском тексте остались английские слова: "
                    + ", ".join(leaked[:5])
                    + ". Переведи их — латиницей в прозе может быть только «Alma»."
                )
                log.warning("chapter %s/%s latin leak: %s", result.system, chapter.slug, leaked[:5])
                continue
            gendered = validator.russian_gendered(body)
            if gendered:
                complaint = (
                    "Эти обороты выдают пол читателя: "
                    + ", ".join(f"«{b.strip()}»" for b in gendered)
                    + ". Перепиши в настоящем времени или безличным оборотом."
                )
                log.warning("chapter %s/%s gendered ru: %s", result.system, chapter.slug, gendered)
                continue

        # What the prose says *about* the placements it cited.
        #
        # Checked against `result.factors` rather than the paragraph's own
        # citations, so a later paragraph may refer back to geometry an earlier
        # one established. Rejected rather than warned, on the same footing as
        # an invented factor, because it is the same failure wearing a
        # citation: measured live, "your sun is in a trine to your Saturn at
        # 1°12′, a soft aspect" carried the orb straight off `☉ ⚻ ♄ · 1°12′`
        # and renamed the aspect — a quincunx sold as a trine, with the reader
        # told in the same clause that it was soft.
        wrong = geometry.drift(body, result.factors)
        if wrong:
            complaint = wrong.complaint()
            log.warning(
                "chapter %s/%s geometry: %d contradicted, %d unsupported",
                result.system, chapter.slug,
                len(wrong.contradicted), len(wrong.unsupported),
            )
            continue

        cited = tuple(dict.fromkeys(f for p in paragraphs for f in p.factors))
        warnings = (
            (f"cites {len(verdict.off_topic)} factor(s) from outside this chapter",)
            if verdict.off_topic
            else ()
        )
        return Written(
            system=result.system,
            chapter=chapter.slug,
            # The model titles its own chapter and does so in the reading's
            # language; the fallback is for the rare reply that omits it, and
            # it has to be in that language too. It used to be `chapter.title`,
            # which is English by definition — a German reading headed "Money
            # and resources".
            title=title or _words(result.system, chapter, locale).title,
            teaser=str(payload.get("teaser") or "").strip(),
            paragraphs=tuple(paragraphs),
            # Forced empty when the chapter does not want it, not merely
            # unasked-for. The schema above is a request and a provider is
            # free to answer with more than was asked; this is the guarantee.
            advice=(
                str(payload.get("advice") or "").strip() if chapter.advice else ""
            ),
            cited_factors=cited,
            model=model,
            attempts=attempt,
            spend=_spent_since(tally, opening, model),
            warnings=warnings,
        )

    reasons = ", ".join(last.reasons) if last else "no valid reply"
    raise ReadingRefused(
        f"{result.system}/{chapter.slug} could not be written in {MAX_ATTEMPTS} "
        f"attempts ({reasons}). Refusing rather than shipping a reading that "
        "cites something the chart does not contain.",
        spend=_spent_since(tally, opening, model),
    )


def _spent_since(tally: cost.Ledger, opening: int, model: str) -> cost.Spend:
    """What this chapter cost, as distinct from what the ledger has seen.

    The ledger may be shared across a whole report, so the answer is the
    slice this call added rather than the running total.
    """
    mine = tally.spends[opening:]
    # Summed dollars, not re-priced tokens: a cached read is billed at a tenth
    # of the input rate, and re-pricing from counts would re-bill it in full.
    return cost.Spend(
        model,
        sum(s.input_tokens for s in mine),
        sum(s.output_tokens for s in mine),
        sum(s.dollars for s in mine),
    )


async def _generate(
    provider: Provider,
    system: str,
    prompt: str,
    model: str,
    max_tokens: int,
    *,
    schema: dict | None = None,
) -> Completion:
    try:
        return await provider.complete(
            system=system,
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            schema=schema or CHAPTER_SCHEMA,
            # Alma's voice is identical for every chapter of a locale; the
            # marker costs nothing when the block is under the cacheable
            # minimum and pays for itself the moment traffic exists.
            cache_system=True,
        )
    except ModelUnavailable:
        raise
    except Exception as exc:  # pragma: no cover - provider-specific
        raise ModelUnavailable(str(exc)) from exc


async def write_system(
    *,
    result: CalcResult,
    provider: Provider,
    model: str,
    locale: str = "en",
    paid: bool = False,
    only: tuple[str, ...] | None = None,
    memory: list[str] | None = None,
) -> list[Written]:
    """Every chapter of one system.

    A chapter the chart cannot support is skipped rather than failing the
    whole report — a person with no birth time should still get the twelve
    chapters that do not need one.
    """
    ledger = cost.Ledger()
    written: list[Written] = []

    for chapter in chapter_defs.for_system(result.system):
        if only and chapter.slug not in only:
            continue
        try:
            written.append(
                await write(
                    result=result,
                    chapter=chapter,
                    provider=provider,
                    model=model,
                    locale=locale,
                    paid=paid,
                    memory=memory,
                    ledger=ledger,
                )
            )
        except ReadingRefused as exc:
            log.info("skipping %s/%s: %s", result.system, chapter.slug, exc)
    return written


def preview(result: CalcResult, *, locale: str = "en") -> dict:
    """The chapter list, before anything is generated.

    What the hub and the paywall both render: how many chapters there are,
    which are free, and which cannot be written for this particular chart.
    Same two localised strings as `GET /v1/readings/{system}/chapters`, for
    the same reason — this is also a screen somebody chooses from.
    """
    listing = []
    for chapter in chapter_defs.for_system(result.system):
        offered = chapter_defs.relevant_factors(chapter, result.factors)
        words = _words(result.system, chapter, locale)
        listing.append(
            {
                "slug": chapter.slug,
                "numeral": chapter.numeral,
                "index": chapter.index,
                "title": words.title,
                "question": words.question,
                "free": chapter.free,
                "available": bool(offered),
                "factor_count": len(offered),
            }
        )
    return {
        "system": result.system,
        "chapters": listing,
        "total": len(listing),
        "available": sum(1 for c in listing if c["available"]),
    }


def as_json(written: list[Written]) -> str:
    return json.dumps([w.as_dict() for w in written], ensure_ascii=False)
