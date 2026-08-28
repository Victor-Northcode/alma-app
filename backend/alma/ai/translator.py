"""Перевод уже написанного — вместо второй генерации.

Смена языка приложения раньше стоила как первое чтение: у `reading` локаль
входит в уникальность (`reading_once`), поэтому та же глава на новом языке —
промах кеша и полная генерация сильной моделью, 11.19¢ по замеру. Слова при
этом уже написаны и оплачены; меняется только язык. Владелец, 28.08.2026:
при смене языка тексты не перегенерируются, а переводятся дешёвой моделью.

**Дешёвая модель здесь законна, хотя для письма владелец её отверг** (история
— у `natal_spheres`: три сожжённые попытки дешёвой генерации стоили дороже
одной средней). Перевод — не сочинение: форма выдана исходником, факты взяты
из него же, выдумывать нечем и незачем. Ровно на этом классе задач дешёвый
тир и хорош: ~0.5¢ за главу против 11.19¢ за перегенерацию.

**Обдумывание выключено целиком, а не прикручено** (`THINKING_OFF`): переводу
нечего решать, а размышление на кириллице уже съедало стены токенов у глав —
см. лестницу усилий в `provider.EFFORT_LADDER` и то, зачем её нижняя ступень
существует.

Переводится **структура, а не строка**: вызывающий разбирает тело на
пронумерованные сегменты (`reading_pieces`, `spheres_pieces` или голый список
реплик беседы), модель обязана вернуть ровно столько же сегментов той же
схемой, и собирает тело обратно вызывающий же. Так перевод физически не может
потерять абзац, склеить два или тронуть поля, которые по контракту остаются
английскими (`factors`, `cited_factors`, ключи областей «Сегодня»).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from . import voice
from .. import i18n
from . import cost
from .provider import AnswerTruncated, Provider, THINKING_OFF
from . import validator

log = logging.getLogger("alma.ai.translator")

#: Две попытки, не три. У писателя третья попытка спасает настоящую генерацию;
#: перевод, дважды не совпавший с исходником по числу сегментов, повторять в
#: третий раз незачем — вызывающий падает в обычную генерацию, которая и так
#: умеет всё.
MAX_ATTEMPTS = 2

#: Сегментов в одном вызове — потолок для беседы: тред в сотню реплик одним
#: промптом упирается в потолок вызова, а перевод половины треда бесполезен.
#: Главы в это не упираются никогда (абзацев меньше десяти).
MAX_SEGMENT_CHARS = 8_000

SEGMENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["segments"],
    # Не украшение: без него API отвечает 400 «'additionalProperties' must be
    # explicitly set to false» — на **каждый** вызов перевода, и весь модуль
    # тихо падал в дорогую генерацию. Тесты этого не видят (ScriptedProvider
    # схему не читает); поймано на проде 28.08.2026, первым же живым вызовом.
    # У всех схем структурного вывода в проекте это поле стоит — см.
    # `writer.CHAPTER_SCHEMA`, `conversation`, `spheres`.
    "additionalProperties": False,
}

#: Правила письма, которые у целевого языка есть сверх «переведи хорошо».
#: Русский и испанский регистры уже названы в `voice.LOCALE_NAMES` — они
#: приезжают оттуда, чтобы перевод и генерация не разошлись в тот день, когда
#: правят одно из двух. Французский пробел назван здесь, потому что для
#: генерации его стерегут статические каталоги, а перевод пишет прозу сам.
_EXTRA_RULES = {
    "fr": (
        "French typography: put a narrow no-break space (U+202F) before "
        "? ! ; : and inside guillemets — « like this »."
    ),
}


class TranslationRefused(Exception):
    """Перевод не сошёлся с исходником и после повтора.

    Несёт потраченное: обе попытки — настоящие вызовы, и вызывающий обязан
    записать их в леджер той же рукой, которой записал бы успех.
    """

    def __init__(self, message: str, spend: cost.Spend) -> None:
        super().__init__(message)
        self.spend = spend


@dataclass(frozen=True, slots=True)
class Translated:
    segments: tuple[str, ...]
    model: str
    spend: cost.Spend


def _system_prompt(
    source_locale: str | None,
    target_locale: str,
    *,
    reader_gender: str | None = None,
) -> str:
    target = voice.LOCALE_NAMES.get(target_locale, target_locale)
    if source_locale is None:
        # Беседа — смешанный исходник: вопросы на одном языке, ответы на
        # другом, у строк до колонки `locale` язык неизвестен вовсе. Языку
        # каждой реплики модель верит своими глазами.
        from_clause = f"Each segment may be in any language; translate every segment into {target}."
    else:
        source = voice.LOCALE_NAMES.get(source_locale, source_locale)
        from_clause = f"Translate from {source} into {target}."
    lines = [
        "You translate already-written text for Alma, an astrology reading "
        "app that speaks to one reader as an intimate, precise voice.",
        from_clause,
        "Rules:",
        "- Translate meaning faithfully: nothing added, nothing dropped, no "
        "commentary of your own.",
        "- Keep the intimate second-person voice of the original.",
        "- Astrological terms (planets, signs, houses, aspects) get their "
        "standard names in the target language.",
        "- Names of people, quoted verbatim spellings, and product names "
        "stay exactly as written — a spelling the text asks the reader to "
        "check must survive translation letter for letter.",
        "- Return exactly one translated segment per input segment, in the "
        "same order. Never merge or split segments.",
        "- A segment that is already in the target language is returned "
        "unchanged.",
    ]
    # Род читателя известен — грамматика цели обязана идти за ним. Английский
    # исходник рода не несёт («you were born»), и без этой строки дешёвая
    # модель выбирала бы род статистикой — то самое «ты родился» женщине,
    # которое у писателя ловит отдельное правило.
    if reader_gender == "female":
        lines.append(
            "- The reader is a woman: gendered forms in the target language "
            "must address her as female."
        )
    elif reader_gender == "male":
        lines.append(
            "- The reader is a man: gendered forms in the target language "
            "must address him as male."
        )
    extra = _EXTRA_RULES.get(target_locale)
    if extra:
        lines.append("- " + extra)
    return "\n".join(lines)


def _scale(locale: str) -> float:
    # То же правило письменности, что у писателя (`writer.py`): кириллица
    # токенизируется примерно вдвое дороже латиницы, и потолок вызова обязан
    # идти за письменностью, а не за аппетитом.
    return 1.0 if i18n.resolve(locale) in ("en", "es", "de", "it", "fr", "pt-BR") else 2.0


def allowance(chars: int, *, target_locale: str) -> int:
    # Потолок вывода — из длины исходника, а не из воздуха: перевод длиннее
    # оригинала не более чем в полтора раза даже у немецкого. Четыре символа
    # на токен для латиницы, два — для кириллицы (замер писателя), плюс обвязка
    # JSON. Неиспользованные токены не стоят ничего — жать потолок незачем.
    per_char = 2 if _scale(target_locale) > 1.0 else 4
    return max(600, min(8_192, (chars * 3 // 2) // per_char + 300))


async def translate(
    segments: Sequence[str],
    *,
    provider: Provider,
    model: str,
    source_locale: str | None,
    target_locale: str,
    paid: bool,
    factors: Sequence[str] = (),
    reader_gender: str | None = None,
    prose: bool = False,
) -> Translated:
    """Перевести сегменты, сохранив их число и порядок.

    Пустые сегменты не ездят к модели вовсе: их не из чего переводить, а
    модель, которой прислали пустую строку, любит заполнять её от себя.

    [prose] — «это письмо Alma одному читателю»: главы, абзацы витрины,
    сферы. Только к прозе применяются русские сетки писателя — протечка
    латиницы и род читателя; беседа сюда не ходит нарочно: там собственные
    слова человека («я родилась», «мой iPhone»), и судить их правилами прозы
    значило бы отвергать верные переводы.

    [factors] — процитированные факторы исходника, и это не украшение: у
    писателя тот же список — законное разрешение на латиницу в русской прозе
    (`validator.russian_latin_leak`). Глава имени в нумерологии **обязана**
    назвать романизированное написание («name counted as ANATOLIY…»), иначе
    читателю нечем проверить сумму; переводчик без этого списка отвергал
    верный перевод ровно той главы — и либо требовал транслитерировать имя,
    либо падал в дорогую перегенерацию, оба исхода хуже бага, который эта
    проверка ловит.

    [reader_gender] — род читателя, когда он известен: уезжает подсказкой в
    промпт (английский исходник рода не несёт, и «ты родился» женщине —
    ровно та ошибка, что у писателя записана отдельным правилом). Когда род
    неизвестен, русская проза сверяется `validator.russian_gendered`: перевод
    обязан держать безродовой регистр исходника.

    Бросает `TranslationRefused`, когда перевод дважды не совпал с исходником
    по числу сегментов; `cost.BudgetExceeded` — когда вызов не влезает в
    потолок ещё до модели; `ModelUnavailable` — когда провайдер молчит.
    Вызывающий на любом из трёх падает в обычную генерацию.
    """
    filled = [(index, text) for index, text in enumerate(segments) if text.strip()]
    if not filled:
        return Translated(tuple(segments), model, cost.cost(model, 0, 0))

    system = _system_prompt(
        source_locale, target_locale, reader_gender=reader_gender
    )
    prompt = json.dumps(
        {"segments": [text for _, text in filled]}, ensure_ascii=False
    )
    chars = len(prompt)
    max_tokens = allowance(chars, target_locale=target_locale)
    cost.guard(
        model,
        prompt_chars=chars + len(system),
        max_output_tokens=max_tokens,
        paid=paid,
        scale=_scale(target_locale),
    )

    spent = cost.cost(model, 0, 0)
    complaint = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            completion = await provider.complete(
                system=system,
                prompt=prompt + complaint,
                model=model,
                max_tokens=max_tokens,
                schema=SEGMENTS_SCHEMA,
                # Система одна на пару языков и совпадает байт в байт у всех
                # пользователей — тот же кешируемый префикс, что у голоса.
                cache_system=True,
                effort=THINKING_OFF,
            )
        except AnswerTruncated as exc:
            # Оборванный вызов — состоявшийся и оплаченный; счёт едет наверх
            # в отказе, чтобы вызывающий записал его перед второй попыткой
            # уже другим способом.
            if exc.completion is not None:
                spent = _plus(spent, exc.completion, model)
            raise TranslationRefused(str(exc), spent) from exc
        spent = _plus(spent, completion, model)

        out = _parsed(completion.text)
        problem = _mismatch(
            out, filled,
            target_locale=target_locale,
            factors=factors,
            reader_gender=reader_gender,
            prose=prose,
        )
        if problem is None:
            translated = list(segments)
            for (index, _), text in zip(filled, out):
                translated[index] = text.strip()
            return Translated(tuple(translated), completion.model or model, spent)

        log.warning(
            "translation attempt %d %s→%s rejected: %s",
            attempt, source_locale, target_locale, problem,
        )
        complaint = (
            "\n\nYour previous answer was rejected: " + problem
            + " Return the translation again, corrected."
        )

    raise TranslationRefused(problem or "translation kept failing", spent)


def _plus(spent: cost.Spend, completion, model: str) -> cost.Spend:
    theirs = cost.cost(
        completion.model or model,
        completion.input_tokens,
        completion.output_tokens,
        cache_read_tokens=completion.cache_read_tokens,
        cache_write_tokens=completion.cache_write_tokens,
    )
    return cost.Spend(
        model=theirs.model,
        input_tokens=spent.input_tokens + theirs.input_tokens,
        output_tokens=spent.output_tokens + theirs.output_tokens,
        dollars=spent.dollars + theirs.dollars,
    )


def _parsed(text: str) -> list[str] | None:
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return None
    segments = payload.get("segments") if isinstance(payload, dict) else None
    if not isinstance(segments, list):
        return None
    return [str(s) for s in segments]


def _mismatch(
    out: list[str] | None,
    filled: list[tuple[int, str]],
    *,
    target_locale: str,
    factors: Sequence[str],
    reader_gender: str | None,
    prose: bool,
) -> str | None:
    """Чем перевод не совпал с исходником — или `None`, если совпал."""
    if out is None:
        return "the reply was not the JSON object the schema asked for."
    if len(out) != len(filled):
        return (
            f"it held {len(out)} segments for {len(filled)} inputs — "
            "one translated segment per input segment, same order."
        )
    empty = [i for i, text in enumerate(out) if not text.strip()]
    if empty:
        return f"segments {empty} came back empty."
    if prose and i18n.resolve(target_locale) == "ru":
        joined = "\n\n".join(out)
        # Та же проверка, что у писателя, и с тем же списком разрешённых:
        # латинское слово посреди русской фразы — «твой natal Уран» — видели
        # живьём, но глава имени в нумерологии **обязана** цитировать
        # романизированное написание из фактора, и без [factors] верный
        # перевод отвергался бы ровно на ней (см. докстринг `translate`).
        leaked = validator.russian_latin_leak(joined, tuple(factors))
        if leaked:
            return (
                "Latin words are stranded in the Russian text: "
                + ", ".join(leaked[:5])
                + ". Translate them."
            )
        if reader_gender not in ("female", "male"):
            # Английский исходник безродовой, и перевод обязан таким и
            # остаться: «ты родился» женщине — первая строка самого личного
            # текста продукта, сообщающая, что Alma решила за неё. То же
            # правило, тем же валидатором, что у писателя.
            gendered = validator.russian_gendered(joined)
            if gendered:
                return (
                    "These Russian forms assume the reader's gender: "
                    + ", ".join(gendered[:5])
                    + ". Use present tense or impersonal constructions "
                    "instead."
                )
    return None


# ── разборка и сборка тел ──────────────────────────────────────────────────


def reading_pieces(
    body: dict,
) -> tuple[list[str], Callable[[Sequence[str]], dict]]:
    """Сегменты главы и функция, собирающая переведённое тело.

    Порядок фиксированный: заголовок, тизер, абзацы, совет, строки областей.
    Не переводятся и копируются как есть: `paragraph_factors`,
    `cited_factors`, `read_from` (мета-строка собирается клиентом из
    факторов), ключи областей (`work/love/money/body` — контракт экрана
    «Сегодня», клиент локализует подписи сам), счётчики и предупреждения.
    """
    paragraphs = [str(p) for p in (body.get("body") or [])]
    areas = [
        {"area": str(a.get("area", "")), "line": str(a.get("line", ""))}
        for a in (body.get("areas") or [])
        if isinstance(a, dict)
    ]
    segments = [
        str(body.get("title") or ""),
        str(body.get("teaser") or ""),
        *paragraphs,
        str(body.get("advice") or ""),
        *[a["line"] for a in areas],
    ]

    def rebuild(translated: Sequence[str]) -> dict:
        out = dict(body)
        cursor = iter(translated)
        out["title"] = next(cursor)
        out["teaser"] = next(cursor)
        out["body"] = [next(cursor) for _ in paragraphs]
        out["advice"] = next(cursor)
        out["areas"] = [
            {"area": a["area"], "line": next(cursor)} for a in areas
        ]
        return out

    return segments, rebuild


def spheres_pieces(
    body: dict,
) -> tuple[list[str], Callable[[Sequence[str]], dict]]:
    """Сегменты превью сфер. Переводится только `text`; `chapter` — слаг,
    по которому клиент ходит в главу, `factors` — английский контракт."""
    blocks = [b for b in (body.get("spheres") or []) if isinstance(b, dict)]
    segments = [str(b.get("text") or "") for b in blocks]

    def rebuild(translated: Sequence[str]) -> dict:
        out = dict(body)
        out["spheres"] = [
            {**block, "text": text} for block, text in zip(blocks, translated)
        ]
        return out

    return segments, rebuild
