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
from ..i18n import placements
from . import chapters as chapter_defs
from . import cost, geometry, validator, voice
from . import provider as provider_module
from .provider import AnswerTruncated, Completion, ModelUnavailable, Provider
from .validator import Paragraph

log = logging.getLogger("alma.ai.writer")

#: Three, and now the budget genuinely pays for three.
#:
#: A fourth attempt was tried when the plain-language gate joined the three
#: existing rejections, because the densest natal chapter was spending attempt
#: one on a truncation and attempts two and three on dashes. The answer then
#: was to make each attempt land instead — the complaint quotes the offending
#: paragraph back rather than naming its index, which is the difference between
#: "fix this sentence" and "rewrite everything and hope". That still holds.
#:
#: What did not hold was the arithmetic underneath. `cost.Ledger.check` held a
#: whole request to *one* `ceiling(paid=False)` while this constant promised
#: three generations, so a free-tier chapter could afford one and a half: the
#: second draft the prose gate itself asked for was refused after the model had
#: written it. A run may now spend `MAX_ATTEMPTS` × the ceiling; each single
#: call is still bounded by `cost.guard` at 1×, and what an account may spend in
#: a month is still bounded by `cost.guard_month`, which is the number that
#: reaches the invoice.
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
                    # **Правило прозы стоит там, где пишется поле.**
                    #
                    # Бриф говорит то же самое, но он в системном блоке, за
                    # несколькими тысячами токенов от места, где модель
                    # сочиняет именно этот абзац. `description` читается
                    # вплотную к полю, и числа сюда приезжают из самого
                    # валидатора — разойтись брифу, схеме и воротам больше
                    # нечем. Замер, ради которого это написано: 30 из 41
                    # повторных генераций 17–18 августа — это ровно
                    # порог средней длины предложения.
                    "text": {
                        "type": "string",
                        "description": (
                            "One paragraph. Its sentences average at most "
                            f"{int(validator.SENTENCE_CEILING)} words and none "
                            f"of them runs past {validator.LONGEST_SENTENCE}; a "
                            "paragraph over either is rejected before it is "
                            "read. Count within this paragraph alone."
                        ),
                    },
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
        "areas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "description": "One of: work, love, money, body.",
                    },
                    "line": {
                        "type": "string",
                        "description": (
                            "One short sentence, at most 12 words, saying what "
                            "the contact given for this area tends to feel like "
                            "in that part of life. Name the area's subject, not "
                            "the aspect: the reader already sees the date beside "
                            "it and never sees the planets. Never write "
                            "'conjunct', 'trine', 'square', 'sextile' or the "
                            "planet names here — that line is the block above. "
                            "No instructions and no predictions."
                        ),
                    },
                },
                "required": ["area", "line"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "teaser", "paragraphs"],
    "additionalProperties": False,
}


def schema_for(chapter: chapter_defs.Chapter) -> dict:
    """`CHAPTER_SCHEMA`, minus whatever this piece does not want asked.

    Two fields now. A piece with `advice=False` is not sent the property at
    all, rather than being sent it and having the answer thrown away: the
    second still spends the tokens, and still invites the model to put the
    instruction it was told not to write into the paragraphs beside it. The
    same argument covers `areas`, which exactly one piece renders: asking every
    chapter for four lines nobody shows would buy the same problem twice.

    Neither is in `required`, so removing a property leaves a schema of the
    same shape. `Written.advice` is forced empty in `write` regardless, so a
    provider that ignores the schema cannot put it back; `areas` is dropped the
    same way.
    """
    drop = {
        key
        for key, wanted in (("advice", chapter.advice), ("areas", chapter.areas))
        if not wanted
    }
    if not drop:
        return CHAPTER_SCHEMA
    trimmed = dict(CHAPTER_SCHEMA)
    trimmed["properties"] = {
        key: value
        for key, value in CHAPTER_SCHEMA["properties"].items()
        if key not in drop
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
    #: `(area, line)` for the Today screen's four life areas — empty for every
    #: piece but the transits' `active` chapter. See `Chapter.areas`.
    areas: tuple[tuple[str, str], ...]
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
            "areas": [{"area": area, "line": line} for area, line in self.areas],
            "cited_factors": list(self.cited_factors),
            "read_from": "Read from: " + " · ".join(self.cited_factors[:4])
            if self.cited_factors
            else "",
            "model": self.model,
            "attempts": self.attempts,
            "warnings": list(self.warnings),
        }


def _can_try_again(attempt: int, tally: cost.Ledger, *, paid: bool, scale: float) -> bool:
    """Whether another generation is both permitted and affordable.

    Two limits, and only the first one is obvious. `MAX_ATTEMPTS` is the count;
    `cost.Tally.check` is a ceiling on what one *request* may spend across all
    of them, and on the free tier a dense Russian chapter reaches it after two.
    A retry that would exceed it does not fail politely — it raises
    `BudgetExceeded` out of the loop, which the router turns into a 503 over a
    chapter that was already written and merely inelegant.

    Only the prose gate asks this question. Citation, safety and geometry
    failures refuse regardless of budget, because what they catch is untrue
    rather than unlovely.

    **The two limits have to be the same limit.** This gate used the
    single-call ceiling while `tally.check` applied that ceiling to the sum, so
    the gate would permit a second draft that the check then refused *after the
    model had written it* — a paid-for chapter thrown away and a 503 handed to
    the reader. That is exactly what `numerology/life-path` did on 16 August
    2026: $0.0250, gate says yes at $0.05, second draft costs $0.0344, total
    $0.0594, refused. Both now ask `MAX_ATTEMPTS` × the ceiling, which is what
    a loop advertising three attempts always needed.
    """
    if attempt >= MAX_ATTEMPTS:
        return False
    if not tally.spends:
        return True
    limit = cost.ceiling(paid=paid) * scale * MAX_ATTEMPTS
    average = tally.dollars / len(tally.spends)
    return tally.dollars + average <= limit


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
    reader_gender: str | None = None,
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
        # Числа — только из данных. Живой скрин 29.08.2026: глава пары
        # объявила «накал страстей N», сняв N с сырой внутренней суммы из
        # блока остальной карты, — шкалы, которой продукт никому не обещал и
        # которую некому объяснить. Правило общее, а не только паре: любое
        # выдуманное число читается как измерение, которого не было. Строка
        # коротка не случайно: промпт бесплатной главы стоит впритык к своему
        # потолку, и лишняя сотня знаков здесь — это BudgetExceeded там.
        "NUMBERS: only numbers present in the data; never invent scores, "
        "scales or percentages.",
        # Особые правила этой главы — из её собственного определения
        # (`Chapter.guidance`): цикл 1–9 у личного года, выкладка у чисел
        # имени, честность про место у астрокартографии.
        *([f"THIS CHAPTER: {chapter.guidance}"] if chapter.guidance else []),
        # The Russian rules ride in the first prompt rather than arriving as a
        # rejection: the owner watched three attempts burn on «ты был» because
        # the model only learned the rule from the complaint. Stated up front,
        # the first answer passes and the screen never says she is silent.
        *(
            (
                [
                    "ПО-РУССКИ: обращайся на «ты». Читатель — "
                    + ("женщина: согласуй род («ты родилась», «ты сама», «готова»)."
                       if reader_gender == "female"
                       else "мужчина: согласуй род («ты родился», «ты сам», «готов»).")
                    + " Латиницей в тексте может быть только слово Alma — все "
                    "планеты и знаки пиши по-русски."
                ]
                if reader_gender in ("female", "male")
                else [
                    "ПО-РУССКИ: обращайся на «ты»; не выдавай пол читателя — никаких "
                    "«ты родился», «ты был», «ты должен», «ты сама»: используй "
                    "настоящее время и безличные обороты («ты появляешься на свет», "
                    "«от тебя требуется»). Латиницей в тексте может быть только "
                    "слово Alma — все планеты и знаки пиши по-русски."
                ]
            )
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

    # **Четыре области Today — и ровно те контакты, что покажет экран.**
    #
    # Выбор здесь повторяет выбор клиента буква в букву (`today_model.nearest`):
    # оба списка, `active` и `upcoming`, срочный первым. Иначе модель написала
    # бы строку про один контакт, а строка над ней назвала бы другой — и это
    # расхождение никто бы не заметил, потому что обе фразы по отдельности
    # верны.
    if chapter.areas:
        nearest = _area_hits(result)
        if nearest:
            lines += [
                "",
                "THE FOUR AREAS OF THE TODAY SCREEN — write one line for each:",
                *(f"- {area}: {hit}" for area, hit in nearest.items()),
                "Each line: at most 12 words, about that part of life, in the "
                "reader's language. The screen already prints the planets and "
                "the date above your line — do not repeat them, and never use "
                "aspect words. Say what it tends to feel like, not what to do "
                "and not what will happen.",
                # Первая же живая генерация: строка «work» повторила лид почти
                # дословно — «An old question about your direction is
                # resurfacing» вверху карточки и «An old question about your
                # direction resurfaces» под заголовком «Работа», в одном
                # экране, друг под другом. Не ошибка модели: сильнейший контакт
                # дня и сильнейший контакт области — часто один и тот же, и,
                # не сказав иного, она дважды пишет про него лучшее, что может.
                "These four lines sit on the same screen as the teaser and the "
                "paragraphs above. Do not restate them: if an area's contact is "
                "the one the paragraphs already cover, write its line about "
                "that part of life specifically, in words the paragraphs do not "
                "use.",
            ]

    # **The factor list is English, and the chapter is not.**
    #
    # Every identifier the engine emits is English by contract, and the prose
    # rule above says to write the planets and signs in the reader's language —
    # but a rule is not a dictionary. `midheaven` has no obvious Russian form to
    # guess at, and the model did what anybody would: «транзитный Сатурн стоит
    # на твоём Midheaven», in the day text, which is the one paragraph every
    # reader sees. Answering that with a rejection costs a whole generation and
    # the account has budget for two.
    #
    # So the spellings ride in the first prompt, the same argument the Russian
    # gender rules above are here for. Only the points this chapter actually
    # cites are listed — fifteen rows would be noise on a chapter that names
    # three — and `PLACEMENTS` is the table the notifications and both client
    # apps already agree on, so there is no second vocabulary to keep in step.
    if i18n.resolve(locale) != "en":
        spellings = [
            f"- {key.replace('_', ' ')} → {placements.placement(key, locale)}"
            for key in placements.PLACEMENTS
            if any(key in factor for factor in offered)
        ]
        if spellings:
            lines += [
                "",
                "HOW TO SPELL THESE POINTS IN THE READER'S LANGUAGE — "
                "use these words, never the English ones:",
                *spellings,
            ]

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


#: Ступени обдумывания и переход между ними живут в `provider.py`: они про
#: контракт с API, а не про то, как пишутся главы. Здесь остаётся политика —
#: с чего начинать, и почему именно с этого.
EFFORT_LADDER = provider_module.EFFORT_LADDER
_turn_down = provider_module.turn_down
_at_the_bottom = provider_module.at_the_bottom

#: С чего начинает глава. `medium`, а не `low`: на замере `low` давал главу
#: короче заказанного (412 слов против 518 при заказанных ~480), то есть
#: экономил на том, за что человек заплатил.
DEFAULT_EFFORT = "medium"

#: С чего начинает открывающий абзац витрины — с того же, что и глава.
#:
#: **Здесь стояло `low`, и большой замер это опроверг.** Довод был складный:
#: сорок слов обдумывать нечего, а вызовов витрины больше всех прочих вместе
#: взятых. Замер 20.08.2026, по пять прогонов полным циклом:
#:
#:     низкое   2.60 попытки   26.5 с   4.17¢   223 слова
#:     среднее  1.40 попытки   17.4 с   3.00¢    47 слов
#:
#: Двести двадцать три слова там, где заказано сорок (`OPENING_WORDS`). На
#: низкой ступени модель перестаёт держать длину, абзац отвергают, пишут
#: заново — и сэкономленное на обдумывании возвращается повторами с лихвой.
#: Среднее лучше по всем трём осям сразу, поэтому отдельного значения у
#: витрины больше нет.
SHOWCASE_EFFORT = DEFAULT_EFFORT


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
    reader_gender: str | None = None,
    effort: str = DEFAULT_EFFORT,
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
    #
    # **The Cyrillic multiplier was measured against the wrong thing and has
    # been raised.** Six tokens a word covers Cyrillic *prose*; what is actually
    # produced is a JSON envelope in which every paragraph repeats its factor
    # strings verbatim, and the model reasons before it writes any of it. Read
    # off the 53 Russian chapters this product has written: mean 2050 output
    # tokens, maximum 4479, against a ceiling of 2520 — so roughly half of them
    # were writing into a wall, and the reader met that as «Alma сейчас не
    # отвечает» after three attempts and three real generations spent.
    #
    # Nine and 900 put a 320-word Russian chapter at 3780, which covers the mean
    # comfortably and most of the tail; `AnswerTruncated.wrote_nothing` handles
    # the rest by raising this call's own ceiling. It is a ceiling and not a
    # spend — tokens are paid for when produced — so the only thing it moves is
    # `cost.guard`'s estimate: $0.0659 for a free chapter on the mid model
    # against a $0.10 Cyrillic-scaled ceiling, and $0.1098 for a paid one on the
    # strong model against $1.00. Both fit.
    #
    # **The headroom is for thinking, and thinking does not get shorter when
    # the chapter does.** The term after the multiplication was 600 and 900 —
    # sized as slack around the prose — and that made the shortest chapter the
    # one most likely to fail. `transits/active` is 150 words by the owner's
    # own instruction («слишком длинно»), which bought it 2250 tokens; it is
    # also the densest chart in the product, forty-six live influences to weigh
    # before choosing the two worth a morning note. Measured on this machine on
    # 13 August 2026: 28 of the 34 refusals this product has ever logged were
    # this one chapter, thinking past 2250, past 3375 and once past 5062 with
    # nothing written. The reader met that as «твой день» simply never arriving.
    #
    # Reasoning cost tracks the *chart*, not the word count, so it belongs in a
    # term that does not scale with words. 1800 for Cyrillic puts this chapter
    # at 3150 and a 320-word one at 4680 — $0.059 and $0.082 against the
    # $0.10 Cyrillic-scaled free ceiling, so both still fit and both still leave
    # room for `afford` to raise on a truncation.
    #
    # **The Latin term stays at 600, and that is arithmetic rather than
    # neglect.** Latin gets no scale multiplier, so its ceiling is the bare
    # $0.05, and a paid chapter is written by the strong model at five times
    # the output price: 320 words at 1200 headroom projects $0.064 on
    # `claude-opus-5` and `cost.guard` refuses the call outright. Every refusal
    # this product has logged was Cyrillic, so this raises the term where the
    # failures are and leaves the one that has never failed alone.
    #
    # **And a floor under the short ones.** With the headroom alone, the first
    # attempt at this chapter stopped being "nothing was written" and became
    # "the answer was cut off" — the model now reasons and starts writing, and
    # runs out mid-prose at 3150. The retry at 4095 succeeded, measured live on
    # 13 August 2026, so the floor is set just above where the successful
    # attempt landed. It binds only on chapters short enough that words × 9
    # cannot pay for the deliberation the chart demands; a 320-word chapter
    # computes 4680 on its own and is untouched. 4100 projects $0.074 against
    # the $0.10 Cyrillic ceiling, which still leaves `afford` a raise to make.
    latin = i18n.resolve(locale) in ("en", "es", "de", "it", "fr", "pt-BR")
    per_word = 3 if latin else 9
    script_scale = 1.0 if latin else 2.0
    # **Области стоят места, и первая же живая генерация это доказала.**
    #
    # Дневная глава просит четыре строки сверх прозы (`Chapter.areas`), а
    # бюджет считался по одной прозе. Ответ обрезался на 2553 токенах, поднять
    # потолок было не на что, три попытки сгорели, и подписчик получил 422 —
    # то есть сломалась ровно та генерация, которую видит каждый и каждый день.
    # Найдено в логе на симуляторе владельца через час после правки.
    #
    # Четыре строки по двенадцать слов — сорок восемь слов, плюс ключи JSON.
    # Считаем тем же `per_word`, что и прозу: по-русски слово стоит втрое
    # дороже, и allowance обязан ехать за скриптом, а не быть константой.
    areas_room = (4 * 12 * per_word + 80) if chapter.areas else 0
    # Потолок стоимости поднимается вместе с просьбой, иначе первое же
    # переполнение упирается в отказ вместо добавки. Четверть — это ровно
    # `areas_room` против прежней высоты в худшем случае (кириллица), и
    # ложится на ту же ручку `scale`, которой уже пользуется скрипт.
    if chapter.areas:
        script_scale *= 1.25
    max_tokens = min(
        8192, chapter.words[1] * per_word + (600 if latin else 1800) + areas_room
    )
    if not latin:
        max_tokens = max(max_tokens, 4100 + areas_room)
    #: The allowance this chapter needs whatever the budget thinks, kept apart
    #: from `max_tokens` because the loop below recomputes that one every
    #: attempt. Going under this is truncation; the truncation branch raises it
    #: so a proven need survives the recomputation.
    floor = max_tokens
    least_paragraphs = chapter.paragraphs[0]
    schema = schema_for(chapter)

    complaint: str | None = None
    last: validator.Verdict | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = build_prompt(
            result, chapter, offered=offered, complaint=complaint, locale=locale,
            reader_gender=reader_gender,
        )
        # **Start at the ceiling the budget already pays for, not below it.**
        #
        # The arithmetic above sizes the allowance from the target word count,
        # which was right when the model wrote as soon as it was asked. With
        # adaptive thinking it reasons first, and an English `natal/core` — 320
        # words, so 1560 tokens — was truncated on *every* first attempt in the
        # live log of 16 August 2026. That attempt is not a draft anybody
        # judged: it is one of three gone before a word exists, and when the
        # plain-language critic then asked for a second draft the reader got
        # "Something on our side is not working" on the free sample chapter
        # that sells the other fifteen.
        #
        # Raising it costs nothing. `max_tokens` is an allowance, not a bill —
        # the comment in the truncation branch below has said so all along —
        # and the same free-tier call affords 2800.
        #
        # **Recomputed every attempt, and allowed to come back down.** A retry
        # carries the complaint, so its prompt is longer and buys fewer output
        # tokens for the same money. A first attempt that claimed *exactly* what
        # the ceiling affords therefore puts the retry over it, and `guard`
        # refuses — trading truncation for a 503, which is worse. That is not
        # hypothetical: `transits/active` was refused at $0.0501 against $0.05,
        # four hundredths of a cent over, on 16 August 2026.
        #
        # Reserving a fixed slab of characters was the first attempt at this and
        # is the wrong shape — it guesses at a complaint whose length nobody
        # controls. Asking the question again with the prompt actually in hand
        # needs no guess. `floor` keeps the recomputation from starving a
        # chapter that genuinely needs the room; when even the floor is beyond
        # the ceiling, `guard` refuses below, in one voice, as it always did.
        max_tokens = max(floor, min(8192, cost.affordable_output(
            model,
            prompt_chars=len(prompt) + len(system),
            paid=paid,
            scale=script_scale,
            most=8192,
        )))
        cost.guard(
            model,
            prompt_chars=len(prompt) + len(system),
            max_output_tokens=max_tokens,
            paid=paid,
            # **The script scale belongs here too, and was missing.** The month
            # tally below has always been scaled — `tally.check(scale=…)` — and
            # `guard`'s own comment says the ceiling scales with the writing
            # system; this call site simply never passed it. A Russian chapter
            # was therefore given a Cyrillic-sized token budget and judged
            # against a Latin-sized price ceiling, which is a contradiction that
            # only stayed invisible while the budget was too small to reach it.
            # `spheres.py` had it right.
            scale=script_scale,
        )

        try:
            completion = await _generate(
                provider, system, prompt, model, max_tokens, schema=schema, effort=effort
            )
        except AnswerTruncated as exc:
            # **Оборванная попытка оплачена, поэтому она записывается здесь, а
            # не ниже.**
            #
            # `tally.record` стоял после этого `except`, и это была единственная
            # ветка, по которой настоящий вызов модели проходил мимо счёта.
            # Обрыв по `max_tokens` не отменяет счёт — модель подумала и
            # произвела токены, — а прогон, обрезанный все три раза, стоил
            # русской главой на сильной модели около $0.6 и двигал месячный
            # потолок на ноль. Дальше человек жал «повторить», и повтор стоил
            # столько же: ограничитель, который видит только удачные вызовы,
            # ограничивает не расход, а пользу.
            #
            # `tally.check` здесь намеренно **не** зовётся: он поднял бы
            # `BudgetExceeded` вместо `AnswerTruncated`, и цикл потерял бы обе
            # свои починки — прибавку потолка и убавку размышления, — то есть
            # ровно то, ради чего эта ветка написана. Потраченное всё равно
            # войдёт в сумму: следующая удачная попытка спросит `check` уже с
            # ним внутри, а `Written.spend` и `ReadingRefused.spend` считаются
            # по тому же `tally`.
            if exc.completion is not None:
                tally.record(cost.cost(
                    model, exc.completion.input_tokens, exc.completion.output_tokens,
                    cache_read_tokens=exc.completion.cache_read_tokens,
                    cache_write_tokens=exc.completion.cache_write_tokens,
                ))

            def afford(desired: int) -> int:
                """As much of the raise as the per-call ceiling will pay for.

                Without this, recovering from a truncation could walk straight
                into `BudgetExceeded` on the next attempt — trading a failure
                the loop knows how to fix for one it does not. The headroom is
                for the complaint the next prompt carries and this one does not.
                """
                limit = cost.ceiling(paid=paid) * script_scale
                projected = cost.estimate(
                    model,
                    prompt_chars=len(prompt) + len(system) + 400,
                    max_output_tokens=desired,
                )
                return desired if projected <= limit else max_tokens

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
            if exc.wrote_nothing:
                # **Nothing was written at all**, which means the allowance went
                # on reasoning before a word of prose existed. Asking this one to
                # be shorter is asking it to solve a problem it does not have,
                # and it truncates again on the next attempt — two of three
                # attempts lost that way, live, on 8 August 2026.
                #
                # So the ceiling moves instead, once, by half. The argument
                # above against a *global* raise still holds — cost scales with
                # the density of the chart and `cost.guard` refuses a free-tier
                # generation over its budget — but this is not a global raise:
                # it is one call that has already proven it needs the room, and
                # the alternative is paying for the same generation three times
                # and handing the reader a 503 at the end of it.
                raised = afford(min(8192, int(max_tokens * 1.5)))

                # **A bigger ceiling is not always available, and a retry that
                # changes nothing is a retry that fails identically.**
                #
                # `afford` returns the *current* ceiling when the raise would
                # cost more than this call may spend, and a Cyrillic chapter on
                # the free tier reaches that wall almost at once: $0.05 × 2 buys
                # about 5670 output tokens of Sonnet, so the second raise is
                # refused and the third attempt re-runs a call already proven to
                # produce nothing. That is what happened to `natal/core` in
                # Russian on 9 August 2026 — 3780, then 5670, then 5670 again,
                # three paid generations, no chapter, and three minutes of
                # "Alma пишет эту главу…" ending in an error.
                #
                # So when the room cannot grow, the deliberation shrinks
                # instead. `effort` is the only other lever that changes the
                # split between thinking and prose, and turning it down is
                # strictly better than spending the same money on the same
                # failure. Ordered rather than jumped: `medium` first, and
                # `low` only if the model manages to think past even that.
                if raised > max_tokens:
                    # Through `floor`, so the recomputation at the top of the
                    # next attempt cannot quietly undo a raise this call has
                    # already proven it needs.
                    max_tokens = floor = raised
                    reason = "ceiling raised to %d" % max_tokens
                elif _at_the_bottom(effort):
                    # Ни потолка поднять, ни обдумывание убавить: следующая
                    # попытка попросила бы ровно то же. Отказываемся сейчас,
                    # а не после ещё одной оплаченной копии того же провала.
                    log.warning(
                        "chapter %s/%s attempt %d: nothing left to change, "
                        "refusing instead of repeating the request",
                        result.system, chapter.slug, attempt,
                    )
                    # Тем же исключением, а не своим: оно уже называет модель и
                    # потолок — то единственное, по чему оператор понимает,
                    # какое число менять. Обернуть его в общий отказ значило бы
                    # сэкономить генерацию ценой диагноза.
                    #
                    # **И обязательно с ценой прогона.** Ниже она прикрепляется
                    # на последней попытке; выходя раньше, мимо той строки, я
                    # унёс отказ без цены — роутер увидел бы обычную
                    # недоступность, ответил 503 мимо `_charge_anyway`, и
                    # состоявшиеся генерации исчезли бы из счёта целиком. Ровно
                    # тот случай, когда самый дорогой исход стоит аккаунту ноль,
                    # а «повторить» можно жать бесконечно.
                    exc.spend = _spent_since(tally, opening, model)
                    raise
                else:
                    effort = _turn_down(effort)
                    reason = "no ceiling left to buy, thinking turned down to %s" % effort
                complaint = None
                log.warning(
                    "chapter %s/%s attempt %d spent its whole allowance thinking; %s: %s",
                    result.system, chapter.slug, attempt, reason, exc,
                )
            else:
                # Cut off mid-sentence: the model went on too long, so it is
                # asked for something shorter — *and* given more room, because
                # the two are not alternatives. A retry that is only told to be
                # brief writes into the same wall when the chart is dense, and
                # the ceiling is an allowance rather than a bill: unused tokens
                # cost nothing.
                raised = afford(min(8192, int(max_tokens * 1.3)))
                # **When the room cannot grow, the deliberation shrinks.**
                #
                # The `wrote_nothing` branch below has had this ladder for a
                # while; this one did not, and a Cyrillic chapter is exactly
                # where the difference shows. `natal/core` in Russian was cut
                # off at 5403, `afford` refused the raise — $0.10 of Sonnet
                # buys about that many tokens and no more — and the retry ran
                # into the identical wall with the identical allowance. Two
                # attempts spent, no chapter, 503 on 16 August 2026.
                #
                # Asking for a shorter answer is still right and still done.
                # It is simply not enough on its own when thinking and prose
                # together will not fit: `effort` is the only other lever that
                # changes how the allowance is split, and turning it down beats
                # paying again for the same overrun.
                if raised > max_tokens:
                    max_tokens = floor = raised
                    reason = "ceiling now %d" % max_tokens
                elif _at_the_bottom(effort):
                    # Та же причина, что и в ветке выше: жалоба здесь одна и та
                    # же на каждой попытке, поэтому без нового потолка и без
                    # ступени обдумывания следующий запрос повторяет прошлый.
                    log.warning(
                        "chapter %s/%s attempt %d: nothing left to change after a "
                        "cut-off, refusing instead of repeating the request",
                        result.system, chapter.slug, attempt,
                    )
                    # Тем же исключением и с ценой прогона — см. довод в ветке
                    # выше; без цены самый дорогой исход стоит аккаунту ноль.
                    exc.spend = _spent_since(tally, opening, model)
                    raise
                else:
                    effort = _turn_down(effort)
                    reason = (
                        "no ceiling left to buy at %d, thinking turned down to %s"
                        % (max_tokens, effort)
                    )
                complaint = (
                    "Your reply ran past the length limit and was cut off. Write "
                    f"noticeably shorter: at most {chapter.words[1]} words in total "
                    f"across {least_paragraphs} or {least_paragraphs + 1} paragraphs, "
                    "and cite only the factors each paragraph actually reads from."
                )
                log.warning(
                    "chapter %s/%s attempt %d was truncated, %s: %s",
                    result.system, chapter.slug, attempt, reason, exc,
                )
            if attempt == MAX_ATTEMPTS:
                # **Наружу уходит вместе с ценой прогона.** Без неё роутер
                # ловил это как обычный `ModelUnavailable`, отвечал 503 мимо
                # `_charge_anyway`, и откат сессии стирал даже то, что успели
                # записать соседние шаги запроса. Три настоящих генерации
                # исчезали из счёта целиком — самый дорогой исход стоил
                # аккаунту ноль.
                exc.spend = _spent_since(tally, opening, model)
                raise
            continue

        tally.record(cost.cost(
            model, completion.input_tokens, completion.output_tokens,
            cache_read_tokens=completion.cache_read_tokens,
            cache_write_tokens=completion.cache_write_tokens,
        ))
        tally.check(paid=paid, scale=script_scale, attempts=MAX_ATTEMPTS)

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
            # Полтора заказанных потолка — см. довод в `validator.check`.
            most_words=int(chapter.words[1] * 1.5),
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

        # **Одна попытка — одна жалоба, но жалоба обо всём сразу.**
        #
        # Раньше каждые ворота стояли своим `continue`, и черновик, провалив
        # двое ворот, стоил две генерации: первая жалоба называла только
        # первую беду, модель чинила ровно её, и вторые ворота срабатывали на
        # уже оплаченном втором черновике. В логе это `transits/long`: попытка
        # 1 — проза, попытка 2 — геометрия, попытка 3 — последняя. Проверки
        # здесь чистые функции над уже полученным текстом, спросить их все
        # стоит ноль, а сэкономленная попытка — это целая генерация.
        #
        # Что публикуется, от этого не меняется: принятый черновик обязан
        # пройти все ворота и в старом порядке, и в новом. Меняется только
        # число оплаченных попыток на пути к нему.
        #
        # Две породы жалоб, и разница между ними прежняя. `hard` — про правду
        # (выдуманная позиция, запрещённое обещание, переврана геометрия,
        # латиница в русской прозе): такое переписывается независимо от
        # бюджета, а на последней попытке кончается отказом. Проза — про то,
        # как это читается, и на исходе бюджета публикуется как есть.
        complaints: list[str] = []
        hard = False

        if not verdict.ok:
            complaints.append(verdict.complaint())
            hard = True
            log.warning(
                "chapter %s/%s attempt %d rejected: %s",
                result.system, chapter.slug, attempt, ", ".join(verdict.reasons),
            )

        body = "\n\n".join(p.text for p in paragraphs)
        breaches = validator.safety(body)
        if breaches:
            complaints.append(
                "The reading broke a rule: "
                + "; ".join(breaches)
                + ". Describe the disposition, never the event, and leave the "
                "decision with the reader."
            )
            hard = True
            log.warning("chapter %s/%s safety: %s", result.system, chapter.slug, breaches)

        # How it is written, on the same footing as what it says.
        #
        # The owner read his own chapters and the verdict was that they are
        # ornate and machine-made — «многие люди, кто захочет с этим
        # поработать, просто не смогут почитать». The voice was told to write
        # plainly long before this and did not; an instruction nobody checks is
        # a preference. This is the check. It costs a regeneration when it
        # fires, which is the price of the rule being real.
        ornate = validator.plain_language(body, i18n.resolve(locale))
        # **And the title, which is the largest line on the page.**
        #
        # `body` is the paragraphs and only the paragraphs, so the model titled
        # its own chapter outside every gate this file runs. It used that
        # freedom: «Ядро — что во мне настоящее, под всем остальным?» went out
        # as the heading of the free chapter that sells the other fifteen,
        # carrying both the banned word and the banned phrase. The word list
        # applies; the dash budget and the sentence ceiling do not, which is why
        # this calls `purple_words` and not `plain_language`.
        in_title = validator.purple_words(title or "", i18n.resolve(locale))
        if in_title:
            ornate = ornate + [
                "The title uses words this product does not use: "
                + ", ".join(in_title[:4])
                + ". Title it with what the chapter actually says."
            ]
        if i18n.resolve(locale) == "ru":
            leaked = validator.russian_latin_leak(body, result.factors)
            if leaked:
                complaints.append(
                    "В русском тексте остались английские слова: "
                    + ", ".join(leaked[:5])
                    + ". Переведи их — латиницей в прозе может быть только «Alma»."
                )
                hard = True
                log.warning("chapter %s/%s latin leak: %s", result.system, chapter.slug, leaked[:5])
            # With a known reader the grammar is *supposed* to agree — the
            # gate only stands when the gender is unknown.
            gendered = [] if reader_gender in ("female", "male") else validator.russian_gendered(body)
            if gendered:
                complaints.append(
                    "Эти обороты выдают пол читателя: "
                    + ", ".join(f"«{b.strip()}»" for b in gendered)
                    + ". Перепиши в настоящем времени или безличным оборотом."
                )
                hard = True
                log.warning("chapter %s/%s gendered ru: %s", result.system, chapter.slug, gendered)

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
            complaints.append(wrong.complaint())
            hard = True
            log.warning(
                "chapter %s/%s geometry: %d contradicted, %d unsupported",
                result.system, chapter.slug,
                len(wrong.contradicted), len(wrong.unsupported),
            )

        # **Проза считается последней, потому что она единственная умеет
        # сдаться.** Всё выше — про правду и переписывается всегда; эта — про
        # то, как читается, и на исходе попыток или бюджета публикуется как
        # есть. Раз мы всё равно возвращаемся к модели из-за жёсткой жалобы,
        # добавить к ней прозаическую стоит ноль: попытка уже потрачена.
        if ornate and (hard or _can_try_again(attempt, tally, paid=paid, scale=script_scale)):
            complaints.append(
                "The writing has to change before this can be published: "
                + "; ".join(ornate[:4])
                + ". Say the same things the same way you would to one person "
                "across a table."
            )
            log.warning(
                "chapter %s/%s plain-language: %s",
                result.system, chapter.slug, "; ".join(ornate[:2]),
            )
        elif ornate:
            # **Out of attempts or out of budget, and this one publishes anyway.**
            #
            # The difference between this gate and the ones above it is the
            # difference between wrong and ugly. An invented placement is a lie
            # about a person and is refused however much it cost to get here; a
            # paragraph with three dashes in it is worse writing than we want
            # and better than the alternative, which is the reader meeting «Alma
            # сейчас не отвечает» over a chapter that exists.
            #
            # It is not hypothetical. `natal/core` is the free sample of the
            # natal system, and two Russian generations of it cost $0.148
            # against the free tier's $0.10 — so the gate had budget for one
            # attempt and, having spent it, was turning a working chapter into a
            # 503. Measured on 9 August 2026.
            log.info(
                "chapter %s/%s published with prose warnings (no budget to retry): %s",
                result.system, chapter.slug, "; ".join(ornate[:2]),
            )

        # Один `continue` на все ворота. Пустой жалобы здесь быть не может:
        # каждая ветка выше кладёт в список текст, а `Verdict.complaint`
        # обязали говорить и про «слишком мало абзацев» — молчаливая жалоба
        # означала повтор с тем же промтом и тем же ответом.
        if complaints:
            complaint = "\n".join(part for part in complaints if part)
            continue

        # **The workings are cited but not displayed**, and the difference
        # matters on screen. `cited_factors` is what the clients render as the
        # gold "read from" pills under the title, and those are placements: "life
        # path 11", "☉ □ ♄ · 2°14′" — short, English by contract, and read as
        # identifiers rather than as prose. A working is a whole sentence —
        # "life path working: day 12 → 3, month 3 → 3, year 1994 → 5…" — and as
        # a pill it is a paragraph of untranslated English running off the edge
        # of a Russian screen. Photographed on the simulator the day it landed.
        #
        # It stays a factor for the validator, which is the whole point: the
        # chapter must quote the arithmetic verbatim and is checked against it.
        # The reader meets that arithmetic in the first paragraph, in their own
        # language, which is where it belongs.
        cited = tuple(
            dict.fromkeys(
                f for p in paragraphs for f in p.factors if "working:" not in f
            )
        )
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
            # Тем же правилом, что и `advice`: не спрошено — значит пусто, а не
            # «пришло, и ладно». Порядок областей задаём мы, а не ответ: экран
            # печатает их в своём порядке, и пришедшая пятая или повторная
            # область не должна появляться на нём вовсе.
            areas=_areas_of(payload) if chapter.areas else (),
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


#: The four areas of the Today screen, in the order that screen prints them.
AREAS: tuple[str, ...] = ("work", "love", "money", "body")


def _area_hits(result: CalcResult) -> dict[str, str]:
    """The contact each area will actually show, described for the prompt.

    Mirrors `today_model.nearest` on the client, and the mirroring is the whole
    point: the screen prints one contact per area and the model writes one line
    per area, and if the two picked differently the line would quietly be about
    something the reader cannot see. Both lists — what is in orb now and what is
    on the way — most urgent first.

    Areas with nothing in either list are simply absent: the screen says «здесь
    сегодня тихо» on its own, and a line written about no contact would be the
    invented interpretation this product exists not to print.
    """
    rows: list[dict] = []
    for key in ("active", "upcoming"):
        value = result.data.get(key)
        if isinstance(value, list):
            rows += [row for row in value if isinstance(row, dict)]
    out: dict[str, str] = {}
    for area in AREAS:
        mine = [row for row in rows if row.get("area") == area]
        if not mine:
            continue
        mine.sort(key=lambda row: row.get("urgency") or 0, reverse=True)
        hit = mine[0]
        described = (
            f"{hit.get('transiting', '?')} {hit.get('aspect', '?')} "
            f"natal {hit.get('natal', '?')}"
        )
        out[area] = described
    return out


def _areas_of(payload: dict) -> tuple[tuple[str, str], ...]:
    """The four area lines, keyed by us rather than by the reply.

    **The reply is read, not trusted.** A model asked for four objects can
    return three, five, the same area twice, or an area spelled `Work`. None of
    those should reach a screen that renders a fixed list of four rows: a
    duplicate would print the same sentence under two headings, and an unknown
    key would print nothing while the caller believed it had a line. So the
    keys come from [AREAS] and the reply only fills them.

    A line the model did not write stays absent rather than becoming an empty
    string: the screen already knows how to say «здесь сегодня тихо», and an
    empty line under a heading is that state rendered as a blank.
    """
    written: dict[str, str] = {}
    for item in payload.get("areas") or ():
        if not isinstance(item, dict):
            continue
        key = str(item.get("area") or "").strip().lower()
        line = str(item.get("line") or "").strip()
        if key in AREAS and line and key not in written:
            written[key] = line
    return tuple((area, written[area]) for area in AREAS if area in written)


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
    effort: str | None = None,
) -> Completion:
    try:
        return await provider.complete(
            system=system,
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            schema=schema or CHAPTER_SCHEMA,
            effort=effort,
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
