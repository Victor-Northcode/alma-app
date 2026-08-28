"""Generated readings and the conversation with Alma.

Three rules shape these routes.

*A reading is written once.* Whatever was generated for a chapter is stored
and returned unchanged forever after. Regenerating on each view would be
simpler and would quietly destroy the product — a person who comes back to
the paragraph that landed and finds a different one has been told, clearly,
that it was never about them. What "once" means is decided by `_reading_key`:
a chapter is the same reading exactly while the facts it was written from are
the same, which is not the same question as whether the system around it has
been recomputed.

*Entitlement is checked before generation, not after.* Otherwise a locked
chapter still costs us a whole chapter, and a paywall that bills us for the
traffic it turns away is a paywall pointed the wrong way.

*A locked chapter is answered, not refused — with its opening paragraph and
nothing else.* Спека `locked-chapter-spec.md` §2.5: ≈40 слов от движка, и это
единственный текст, на который тратятся токены до оплаты. Он пишется при
первом открытии главы и кэшируется навсегда (`_opening_key` намеренно не
включает движущиеся факты), поэтому обход всех сорока закрытых глав стоит
около $0.69 в худшем случае — **один раз за жизнь аккаунта**, а не за визит.
Права проверяются прежде и здесь: без них не пишется *глава*, и это правило не
смягчилось ни на строку.

*Nothing is generated until both ceilings have been asked, and everything
generated is charged.* The per-call ceiling catches a single generation too
big to make; the monthly one catches the thousand individually-cheap
generations that a per-call ceiling cannot see. Both are asked with the model
that will actually do the work, because a budget checked against a different
model than the one that gets called is a budget that has been checked against
nothing. And the money is recorded on the refusal paths too — those are the
ones that ran three generations rather than one, and while they recorded
nothing the ledger could only see the requests that worked.

*Соединения с базой на время генерации не существует.* Каждый путь здесь
разрезан на три части: короткая транзакция на чтение (права, рождение,
воспоминания, тариф, месячный потолок, кэш) — **коммит** — генерация без
единого открытого соединения — вторая короткая транзакция на запись главы и
счётчиков. Разрез не косметический: пул по умолчанию у SQLAlchemy 2.0 — 5
соединений плюс 10 overflow, а генерация занимает 10–40 секунд, так что до
правки воркер физически не мог вести больше пятнадцати генераций, и
шестнадцатый запрос — включая `GET /v1/billing/catalogue` — ждал
`pool_timeout` и получал 500. Замерено: пятнадцать одновременных генераций,
`pool.checkedout() == 15`, дешёвый запрос умер через 30.0 секунды. Роуты
поэтому не берут `SessionDep`, а берут `SessionReleased` — см. довод там же,
в `db/session.py`: соединение держит не роут, а `deps.visitor`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ... import i18n
from ...i18n import replies as i18n_replies
from ...ai import chapters as chapter_defs
from ...ai import conversation, cost, translator, validator, voice, writer
from ...ai.provider import AnswerTruncated, ModelUnavailable, Provider, models
from ...ai.writer import ReadingRefused
from ...auth import entitlements
from ...calc import CalcResult, TimeRequired
from ...calc.cache import MOMENT_OPTIONS, compute_cached_async
from ...calc.contract import cache_key
from ...calc.service import AmbiguousBirthTime, ambiguity_detail
from ...config import settings
from ...db import counters
from ...db.models import (
    ChatMessage,
    ChatThread,
    ChatTranslation,
    Memory,
    Reading,
    UsageCounter,
    User,
    utcnow,
)
from ...db.session import SessionReleased, session_scope
from ..cache import result_cache
from ..deps import (
    STREAM_TURNS,
    CurrentUser,
    SessionDep,
    get_provider,
    partner_profile_id,
    resolve_birth,
)
from ..schemas import ChatRequest, ReadingRequest

log = logging.getLogger("alma.api.readings")
router = APIRouter(tags=["readings"])

#: Which systems a chat turn draws its facts from: the natal chart plus the
#: two number systems. Not a paywall — every calculation in this product is
#: free forever, and a conversation that could only cite numerology would be
#: a worse conversation than the product promises. It used to be described as
#: "the free systems plus natal", which stopped being true the day the free
#: systems became the empty set.
#: Everything Alma is allowed to know while she is talking to somebody, which
#: is everything the product knows about them.
#:
#: This was three — natal, numerology and birth-card — and the effect was a
#: conversationalist who could not answer five of the eight questions her own
#: product sells. "What is going on for me right now" is transits, "how is this
#: year shaped" is the solar return, "how are we together" is compatibility,
#: "where should I be" is astrocartography, and "what do they agree on" is the
#: synthesis. She had none of them, so she answered from a natal chart and a
#: life path and sounded like somebody changing the subject.
#:
#: The cost of the difference, measured rather than feared: 107 factors and
#: ~1,430 input tokens becomes 492 factors and ~5,280, which on Sonnet is
#: **$0.0253 → $0.0368 a turn**. A subscriber's thirty questions go from $0.76
#: to $1.10 a month against $8.99 of net revenue — the count was forty when
#: this was measured and the owner has since lowered it, which only widens the
#: margin the paragraph is arguing about. Input is the cheap half of a
#: generation and the output length did not change; the fear that "the whole
#: chart is too expensive to send" was worth exactly one cent a question.
#:
#: Three of these need a birth time and one needs a second person, so this is
#: what is *attempted* rather than what always arrives — see the loop below,
#: which now says what is missing instead of silently dropping it.
CHAT_SYSTEMS = (
    "natal",
    "numerology",
    "birth-card",
    "transits",
    "solar-return",
    "compatibility",
    "astrocartography",
    "synthesis",
)


#: A *factory*, not a provider. Resolving it does no work, so the paywall
#: and the birth-time checks run before anything can complain about a missing
#: API key.
ProviderDep = Annotated[Callable[[], Provider], Depends(get_provider)]


#: Приставка, под которой открывающий абзац лежит в колонке `Reading.chapter`.
#:
#: Та же уловка, что у дневной заметки (`daily/storage.CHAPTER_PREFIX`) и у
#: превью сфер (`chapter="spheres"`): своя таблица дала бы вторую копию
#: удаления аккаунта, экспорта и слияния гостя с почтой, а строка в `Reading`
#: получает всё это в тот же день, что и появляется. Двоеточие — то, чего в
#: настоящих слагах не бывает, поэтому спутать нельзя.
#:
#: Ограничение `reading_once` — (user, system, chapter, calc_key, locale), так
#: что абзац и сама глава живут в разных строках и не мешают друг другу:
#: купивший получает полную главу, а его открывающий абзац остаётся там же,
#: где лежал, и второй раз не пишется.
OPENING_PREFIX = "opening:"


def opening_chapter_id(slug: str) -> str:
    return f"{OPENING_PREFIX}{slug}"


#: One lock per reading key, in this process.
#:
#: Two requests for the same unwritten chapter used to both put a model to
#: work and both pay for it, and the second insert then hit the UNIQUE
#: constraint on `reading` and answered 500 — measured live, on the owner's
#: own first-run, as "Alma is not answering" over a chapter that had in fact
#: just been written. The lock makes the second request *wait*; it wakes to a
#: cache hit and spends nothing. The `IntegrityError` handler at the insert is
#: the cross-process half of the same defence, for a deployment with more
#: than one worker, where an in-process lock cannot reach.
#:
#: Pruned on release when nobody is waiting, so the table does not grow with
#: every chapter ever written.
_WRITE_LOCKS: dict[str, asyncio.Lock] = {}


def _write_lock(key: str) -> asyncio.Lock:
    lock = _WRITE_LOCKS.get(key)
    if lock is None:
        lock = _WRITE_LOCKS[key] = asyncio.Lock()
    return lock


def _prune_lock(key: str) -> None:
    lock = _WRITE_LOCKS.get(key)
    if lock is not None and not lock.locked():
        _WRITE_LOCKS.pop(key, None)


#: Ходы беседы, у которых больше нет читателя, — теперь общий реестр в `deps`.
#:
#: `/chat/stream` перестал отменять свою задачу, когда клиент уходит (см. довод
#: в `finally` там же), и задача, которую никто не ждёт, обязана быть где-то
#: записана: `asyncio` держит на задачи только слабые ссылки, и брошенная
#: пропадает в сборщике мусора посреди генерации — то есть ровно тем способом,
#: от которого мы уходим. Строка убирается сама, когда ход дописан.
#:
#: **Здесь стоял голый `set`, и он был на одну обязанность беднее.** Первая — та
#: же: держать ссылку. Вторая появилась вместе с остановкой процесса: множество,
#: которое некому дождаться, при выкладке исчезает вместе с процессом, а с ним и
#: ответ, за который уже заплачено. Ждать его обязан `lifespan` в `api/app.py`, а
#: тому пришлось бы импортировать приватное имя чужого роутера и подписаться под
#: тем, что имя не переименуют. Поэтому реестр живёт в `deps`, а этот псевдоним
#: оставлен ради читателя, который придёт сюда за старым именем.
#:
#: Третья обязанность — потолок: `set.add` принимает что угодно и сколько
#: угодно, `admit` отказывает после `MAX_BACKGROUND_TURNS`, потому что
#: «дописать оплаченный ответ» — обещание, которое можно дать конечное число раз
#: за окно остановки.
_STREAM_TURNS = STREAM_TURNS


#: Один замок на аккаунт, на всё время хода беседы.
#:
#: **Порция вопросов и месячный потолок читались до записи и без замка.** Обе
#: проверки — `_chat_gate` и `_guard_month` — это «прочитать счётчик, сравнить,
#: и много позже записать»; между чтением и записью лежит целая генерация, и
#: два одновременных сообщения проходили обе стены с одним и тем же нулём в
#: руках. Двойное нажатие «отправить» на телефоне даёт ровно это, и стоит оно
#: двух генераций там, где оплачена одна.
#:
#: Замок на аккаунт, а не на тред: обходятся оба ограничителя, и оба они —
#: про аккаунт. Держится он до коммита, а не до конца проверки, потому что у
#: второго запроса своя сессия и своя транзакция: отпущенный раньше коммита
#: замок показал бы ему ту же незафиксированную порцию, что и до правки.
#:
#: Одного процесса это не переживает — как и `_WRITE_LOCKS` выше; на нескольких
#: воркерах щель сужается до окна коммита, но не закрывается. Настоящее
#: лекарство там — уникальность в базе, и его стоит завести в тот день, когда
#: воркеров станет больше одного.
_CHAT_LOCKS: dict[str, asyncio.Lock] = {}
#: Сколько ходов этого аккаунта держат замок или стоят за ним. Считается, чтобы
#: строку можно было убрать безопасно: удалять «когда не заперто» нельзя —
#: ожидающий уже держит *старый* объект замка, а следующий создал бы новый, и
#: двое пошли бы через разные замки, то есть мимо замка вовсе.
_CHAT_WAITING: dict[str, int] = {}


@asynccontextmanager
async def _chat_slot(user_id: str) -> AsyncIterator[None]:
    """Пока это открыто, у аккаунта идёт ровно один ход беседы."""
    lock = _CHAT_LOCKS.get(user_id)
    if lock is None:
        lock = _CHAT_LOCKS[user_id] = asyncio.Lock()
    _CHAT_WAITING[user_id] = _CHAT_WAITING.get(user_id, 0) + 1
    try:
        async with lock:
            yield
    finally:
        left = _CHAT_WAITING.get(user_id, 1) - 1
        if left > 0:
            _CHAT_WAITING[user_id] = left
        else:
            _CHAT_WAITING.pop(user_id, None)
            _CHAT_LOCKS.pop(user_id, None)


#: The metric each allowance is counted under. The monthly one has its own
#: name rather than sharing the daily one — see `_counter`.
DAILY_QUESTIONS_METRIC = "questions"
MONTHLY_QUESTIONS_METRIC = "questions_month"
#: Своя метрика у недельной: считать её в месячном ведре значило бы дать
#: четыре недели подряд по одной порции — или отнять порцию у того, кто
#: продлился в середине месяца.
WEEKLY_QUESTIONS_METRIC = "questions_week"
#: The one-time bundle a purchase includes. Counted for the life of the
#: account rather than per period, so it runs out once and stays out.
BUNDLE_QUESTIONS_METRIC = "questions_bundle"
#: The welcome bundle's own counter, so it is not confused with either the
#: daily allowance or a purchase's bundle.
WELCOME_QUESTIONS_METRIC = "welcome_questions"


@dataclass(frozen=True, slots=True)
class Allowance:
    """What one tier gets in the chat: a model, a count, and a period."""

    tier: str
    model: str
    limit: int
    #: "day" | "week" | "month" | "once". Каждый из четырёх — ещё и ключ фразы
    #: для стены (`question_limit.{period}` в `_chat_gate`), поэтому период,
    #: добавленный без строки в `i18n/replies.py`, — это 500 вместо 429.
    #: Стережёт `test_every_period_an_allowance_can_carry_has_a_sentence_for_its_wall`.
    period: str
    metric: str


def _allowance(tier: str, *, mid: str, locale: str = "en", weekly: bool = False) -> Allowance:
    """Which model answers this person, and how many turns they get.

    The ladder the owner set: one welcome question free, a small bundle on the
    strong model with a one-time purchase, and the plan carries the whole
    conversation. **There is no cheap-model tier any more** — the owner's
    verdict on the cheap model was that it made Alma sound stupid, and a shop
    window that undersells the product is worse than a closed door. What stays
    free for ever is everything else: all eight systems, calculated in full.

    The base allowance for anybody without a plan is therefore zero — the
    welcome and purchase bundles in the route are what a non-subscriber
    actually spends — and the refusal it produces is the sentence that sells
    the plan.
    """
    config = settings()
    if tier == "subscriber":
        # **Недельная подписка получает порцию по своему сроку.**
        #
        # Она давала ту же месячную порцию за половину цены и на комиссии 30%
        # уходила в минус. Плотность разговора та же, что у месячной, — просто
        # неделя короче месяца.
        if weekly:
            return Allowance(
                tier,
                mid,
                config.weekly_questions_per_week,
                "week",
                WEEKLY_QUESTIONS_METRIC,
            )
        # Кириллица стоит примерно вдвое за тот же ответ — это измерено и
        # записано в `writer.py`. Равная маржа, а не равный счёт вопросов.
        cyrillic = i18n.resolve(locale) == "ru"
        return Allowance(
            tier,
            mid,
            config.subscriber_questions_per_month_cyrillic
            if cyrillic
            else config.subscriber_questions_per_month,
            "month",
            MONTHLY_QUESTIONS_METRIC,
        )
    return Allowance(tier, mid, config.free_questions_per_day, "day", DAILY_QUESTIONS_METRIC)


def _bundle(*, strong: str) -> Allowance:
    """The questions a purchase includes: a finite pile, on the strong model.

    A door is bought once and never expires, so an allowance that renews would
    be a subscription given away with a one-time purchase. A fixed bundle
    instead — five turns on the deepest voice, the same one the paid readings
    are written in. Someone who used all five and wants a sixth has discovered
    by using it what the subscription is for, which is a better argument than
    any sentence on the paywall.
    """
    return Allowance(
        "owner", strong, settings().owner_question_bundle, "once", BUNDLE_QUESTIONS_METRIC
    )


def _welcome(*, mid: str) -> Allowance:
    """The free tier's questions — three a month, on the model that sells.

    See `config.free_welcome_bundle` for the money. Окно — месяц, а не жизнь
    аккаунта: ТЗ v3 §2 называет бесплатный слой «3 вопроса Альме в месяц», и
    сценарий приёмки P6 начинается с «израсходованы 3 бесплатных вопроса,
    отправляет четвёртый». Прежняя форма «once» превращала строку каталога
    «Three questions a month is where free ends» в неправду со второго месяца.
    """
    return Allowance(
        "welcome", mid, settings().free_welcome_bundle, "month",
        WELCOME_QUESTIONS_METRIC,
    )


async def _stored_reading(
    session,
    *,
    user_id: str,
    system: str,
    chapter: str,
    calc_key: str,
    locale: str,
) -> Reading | None:
    """Уже написанная строка — или `None`.

    Была замыканием внутри `read` и внутри `_locked_chapter`, потому что искать
    её надо дважды: до замка и под ним. Стала функцией, когда сессия перестала
    жить весь запрос: замыкание, поймавшее сессию, — ровно тот способ, которым
    закрытая транзакция протаскивается в генерацию.
    """
    return (
        await session.execute(
            select(Reading).where(
                Reading.user_id == user_id,
                Reading.system == system,
                Reading.chapter == chapter,
                Reading.calc_key == calc_key,
                Reading.locale == locale,
            )
        )
    ).scalar_one_or_none()


async def _translation_source(
    session,
    *,
    user_id: str,
    system: str,
    chapter: str,
    calc_key: str,
    exclude_locale: str,
) -> Reading | None:
    """Та же глава на любом другом языке — исходник для перевода.

    Существует, потому что смена языка приложения стоила как первое чтение:
    локаль входит в `reading_once`, тот же `calc_key` на новой локали — промах
    кеша и полная генерация сильной моделью (11.19¢ по замеру против ~0.5¢ за
    перевод). Слова уже написаны и оплачены; меняется только язык — владелец,
    28.08.2026: переводить дёшево, не перегенерировать.

    `calc_key` нарочно не содержит локали (см. `_reading_key`), поэтому «та же
    глава» здесь — буквально те же факты.

    Порядок выбора: оригинал прежде перевода, английский прежде остальных,
    свежий прежде старого. «Оригинал прежде перевода» — не вкус: строка с
    `translated_from` сама писана дешёвой моделью, и перевод с неё — перевод
    с перевода, дрейф накапливается, а оплаченный сильной моделью исходник
    лежит строкой ниже. Перевод берётся источником только когда оригинала нет
    вовсе — чего у живых данных не бывает: оригинал не удаляется.
    """
    rows = (
        await session.execute(
            select(Reading)
            .where(
                Reading.user_id == user_id,
                Reading.system == system,
                Reading.chapter == chapter,
                Reading.calc_key == calc_key,
                Reading.locale != exclude_locale,
            )
            .order_by(Reading.created_at.desc())
        )
    ).scalars().all()
    originals = [
        row for row in rows if "translated_from" not in (row.body or {})
    ]
    pool = originals or rows
    for row in pool:
        if row.locale == "en":
            return row
    return pool[0] if pool else None


def _translation_projection(body: dict, *, locale: str) -> float:
    """Во что перевод обойдётся, в долларах, — для месячного потолка."""
    cheap, _mid, _strong = models()
    chars = len(json.dumps(body, ensure_ascii=False))
    return cost.at_measured_rate(
        cost.estimate(
            cheap,
            prompt_chars=chars + 900,
            max_output_tokens=translator.allowance(chars, target_locale=locale),
        ),
        "translation",
    )


async def _translated_body(
    user,
    provider,
    *,
    body: dict,
    pieces,
    source_locale: str,
    target_locale: str,
    paid: bool,
    factors: list | tuple = (),
    reader_gender: str | None = None,
    ledger: str = cost.SPEND_METRIC,
) -> tuple[dict, cost.Spend, str] | None:
    """Переведённое тело — или `None`, и тогда вызывающий генерирует заново.

    Любой сбой перевода — не ошибка наружу, а откат в путь, который и так
    умеет всё: обычную генерацию. Дороже, но человек получает главу, а не 503
    из-за экономии, которую он не заказывал.

    [factors] и [reader_gender] — те же разрешения и обязательства, что у
    писателя: латиница из процитированных факторов законна (глава имени
    цитирует романизированное написание), а род читателя либо уезжает в
    промпт, либо перевод сверяется на безродовой регистр. Доводы — в
    `translator.translate`.
    """
    cheap, _mid, _strong = models()
    segments, rebuild = pieces(body)
    try:
        done = await translator.translate(
            segments,
            provider=provider(),
            model=cheap,
            source_locale=source_locale,
            target_locale=target_locale,
            paid=paid,
            factors=tuple(factors),
            reader_gender=reader_gender,
            prose=True,
        )
    except translator.TranslationRefused as exc:
        # Обе попытки — настоящие вызовы; счёт двигается, как у любой другой
        # неудачи генерации, своей транзакцией.
        if exc.spend.cents:
            await _charge_anyway(user, cents=exc.spend.cents, ledger=ledger)
        log.warning(
            "translation %s→%s refused, falling back to generation: %s",
            source_locale, target_locale, exc,
        )
        return None
    except (cost.BudgetExceeded, ModelUnavailable) as exc:
        log.warning(
            "translation %s→%s fell back to generation: %s",
            source_locale, target_locale, exc,
        )
        return None
    translated = rebuild(done.segments)
    translated["translated_from"] = source_locale
    return translated, done.spend, done.model


async def _calc(system: str, birth, **options) -> CalcResult:
    # **Расчёт идёт в рабочем потоке, а не в цикле событий.**
    #
    # `async def` вокруг синхронного numpy ничего не делает асинхронным: пока
    # считается годовой скан транзитов, воркер не отвечает **никому** — ни
    # другому человеку, ни проверке живости балансировщика, ни уже открытым
    # потокам беседы. Замерено на утренней волне из двенадцати рождений:
    # худшая пауза цикла была 9.15 секунды, и за это время проверка живости
    # получила семь ответов вместо семисот. Балансировщик такой процесс
    # считает мёртвым и выводит из работы — посреди волны, которую сам же и
    # вызвал утренним уведомлением.
    #
    # После выноса в поток та же волна: пауза 0.29 секунды, проверка живости
    # отвечает без перебоев. Общее время выросло примерно на шестую часть —
    # расчёт упирается в GIL и от потоков быстрее не становится, — и это
    # честная цена за то, что сервер перестал исчезать.
    try:
        return await compute_cached_async(
            system, birth, cache=result_cache(), **options
        )
    except AmbiguousBirthTime as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail=ambiguity_detail(exc)
        ) from exc
    except TimeRequired as exc:
        raise HTTPException(
            422, detail={"error": "birth_time_required", "message": str(exc)}
        ) from exc


@router.get("/readings/{system}/chapters")
async def list_chapters(
    system: str,
    user: CurrentUser,
    session: SessionDep,
    #: The reader's language, exactly as `POST /v1/readings` takes it — same
    #: name, same default, same ceiling — because a client should not have to
    #: learn two conventions for the same fact. A GET has no body to put it
    #: in, so it is a query parameter and nothing else changes.
    locale: str = Query(default="en", max_length=i18n.MAX_TAG),
    #: Про кого оглавление, когда система — совместимость. Отчёт по паре
    #: покупается на одного человека, поэтому «открыта ли глава» без имени
    #: партнёра — вопрос без ответа; с одним сохранённым партнёром он
    #: подставляется сам (`partner_profile_id`), с несколькими его надо назвать.
    #: Необязательный: для семи остальных систем он бессмыслен.
    partner_profile_id_: str | None = Query(default=None, alias="partner_profile_id"),
) -> dict:
    """The table of contents, with what is open and what is written.

    This list is where somebody decides what to read, so the title and the
    question are the two strings that have to be in their language: the title
    is the largest type on the screen and the question is what makes them tap.
    Everything else here — the slug, the numeral, the flags — is structure the
    client acts on rather than words anybody reads.
    """
    try:
        defined = chapter_defs.for_system(system)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    # Resolved once, and reported back. A client that asked for "de-AT" and
    # was answered in "de" can see that it was; a client that asked for a
    # language we have never written can see that it got English rather than
    # discovering it by reading the words.
    language = i18n.resolve(locale)

    existing = {
        row.chapter
        for row in (
            await session.execute(
                select(Reading).where(Reading.user_id == user.id, Reading.system == system)
            )
        ).scalars().all()
    }

    # Один раз на оглавление, а не по главе: партнёр у всех строк один, а
    # запрос в базу за ним — нет.
    partner = (
        await partner_profile_id(session, user, partner_profile_id_)
        if system == "compatibility"
        else None
    )

    # Пара, которую нечем назвать (партнёров ноль или несколько, и ни один не
    # передан): платные главы закрыты — гранту не к чему привязаться, — а
    # бесплатная остаётся бесплатной, она такая для всех и партнёра не требует.
    unnameable = system == "compatibility" and partner is None

    listing = []
    for chapter in defined:
        access = (
            entitlements.PAIR_WITHOUT_PROFILE
            if unnameable and not chapter.free
            else await entitlements.check(
                session, user, system, chapter=chapter.slug, partner_id=partner
            )
        )
        words = i18n.chapter_words(system, chapter.slug, locale=language)
        listing.append(
            {
                "slug": chapter.slug,
                "numeral": chapter.numeral,
                "index": chapter.index,
                "title": words.title,
                "question": words.question,
                "free": chapter.free,
                "open": access.allowed,
                "written": chapter.slug in existing,
                "needs_birth_time": chapter.time_dependent,
            }
        )
    return {
        "system": system,
        "locale": language,
        "chapters": listing,
        "total": len(listing),
    }


@router.post("/readings")
async def read(
    payload: ReadingRequest,
    user: CurrentUser,
    provider: ProviderDep,
    _released: SessionReleased,
) -> dict:
    """Fetch a chapter, writing it the first time it is asked for.

    Сессии у этого роута нет. Всё, что читается из базы, читается короткими
    `session_scope` ниже, и последний из них закрывается **до** вызова модели —
    см. правило в шапке модуля.
    """
    try:
        chapter = (
            chapter_defs.find(payload.system, payload.chapter)
            if payload.chapter
            else chapter_defs.for_system(payload.system)[0]
        )
    except (ValueError, IndexError) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    # Narrowed to one of the six here, once, and used for the lookup, the
    # generation and the stored row alike — because those three have to agree
    # about what "this reading's language" means.
    #
    # It did not used to be narrowed at all, and that was defensible while
    # `voice.system_prompt` did `LOCALE_NAMES.get(locale, en)`: "de" and
    # "de-AT" genuinely produced different prose, so they were genuinely
    # different readings and belonged in different rows. They now produce the
    # same prompt byte for byte, so the raw tag only decides how many times we
    # pay to generate it: `reading_once` includes the locale, a lookup on the
    # raw tag misses the row written for the resolved one, and a reader whose
    # device reports "de-AT" is charged for a second copy of German they
    # already own. Rows already stored under a regional tag are untouched and
    # simply stop accumulating siblings.
    language = i18n.resolve(payload.locale)

    # **Без права глава целиком не пишется, но экран не остаётся пустым.**
    #
    # Историю надо назвать вслух, иначе следующий читающий решит, что здесь
    # потеряна щедрость, и вернёт генерацию целой главы. Сначала первые
    # несколько закрытых глав писались *по-настоящему* — сервер сочинял главу,
    # помечал ответ `preview`, клиент показывал первый абзац и размывал
    # остальное (`ALMA_PREVIEW_CHAPTERS`). Владелец это отменил по деньгам:
    # каждое превью — запись сильной моделью за $0.02–0.10 для человека,
    # который ещё ничего не решил. Осталась голая стена: 402 `locked`, а на
    # экране — заголовок, объяснение и кнопка.
    #
    # Владелец увидел и её: «чёрная стена — просят заплатить за заголовок»
    # (`locked-chapter-spec.md` §5). Обе крайности стоят продажи, и середина
    # названа спекой §2.5 — **открывающий абзац**: ≈40 слов, написанные из
    # позиций этого человека, единственный текст, за который мы платим до
    # оплаты. Не половина главы, а её первый абзац; остальное на экране —
    # размытый филлер, который рисует клиент и который не стоит ни токена.
    #
    # Стена по-прежнему стоит **до** генерации полной главы, и это не
    # изменилось ни на строку: ниже по течению `_read_or_write` вызывается
    # только для того, кому глава открыта.
    #
    # Про кого пишем, когда пишем про пару. Мягкий разбор: строгий («партнёров
    # несколько, назови») стоит ниже, в `_partner`, и обязан остаться там —
    # иначе неоплативший человек с двумя партнёрами получит 422 вместо
    # пейволла и не узнает, что глава вообще продаётся.

    # ── права и, для пары, кредит: первая короткая транзакция ──────────────
    #
    # Открывается и закрывается здесь целиком. Всё, что стоит времени —
    # расчёт карты и вызов модели, — лежит ниже и уже без соединения.
    async with session_scope() as session:
        pair = (
            await partner_profile_id(session, user, payload.partner_profile_id)
            if payload.system == "compatibility"
            else None
        )
        access = (
            entitlements.PAIR_WITHOUT_PROFILE
            if payload.system == "compatibility" and pair is None and not chapter.free
            else await entitlements.check(
                session, user, payload.system, chapter=chapter.slug, partner_id=pair
            )
        )
        # **Месячный кредит подписчика тратится здесь — на первой платной главе
        # про нового человека, и больше нигде.**
        #
        # Почему не в `entitlements.check`: тот вызывается на каждом рендере
        # оглавления и каждом обновлении хаба, и кредит, списываемый проверкой
        # прав, утекал бы от одного взгляда на экран. Почему не в `covers`: там
        # нет базы и нет права на запись. Единственное место, где «человек
        # действительно получает новый отчёт», — момент перед генерацией.
        #
        # Порядок с `access` тоже не случаен: подписка **покрывает**
        # совместимость (`scope="all"`), поэтому закрытая глава сюда не
        # доходит, и решение «включённая проверка или $4.99 сверх» принимается
        # ровно один раз — тут.
        #
        # Развилки `if chapter.free` здесь больше нет. Она вела в
        # `_teaser_or_paywall` — отдельный бесплатный тизер «Притяжение» со
        # своим капом на число новых людей в месяц. Владелец снял его
        # 17.08.2026 словами «тизер и глава I пары — одно и то же»: теперь это
        # обычная закрытая глава, и её открывающий абзац пишется тем же путём,
        # что у остальных сорока.
        #
        # **Что изменил разрез сессии:** кредит коммитится до генерации, а не
        # вместе с главой. Это к лучшему, а не поблажка — `credits.spend`
        # выписывает бессрочный грант на эту пару, поэтому повтор после
        # сорвавшейся генерации попадает в первую ветку
        # `_pair_credit_or_paywall` и не стоит второго кредита. Раньше откат
        # возвращал кредит, и человек платил им дважды за один отчёт.
        if access.allowed and payload.system == "compatibility" and pair is not None:
            await _pair_credit_or_paywall(session, user, pair)

    if not access.allowed:
        # `and not chapter.free` здесь больше нет, и это не упрощение ради
        # краткости: бесплатная глава физически не может прийти сюда с отказом —
        # `check` отвечает про неё True первой же веткой, а безымянная пара
        # выбирает `PAIR_WITHOUT_PROFILE` только для платной. Второе условие
        # означало бы, что мы допускаем «бесплатная и закрытая», а такого
        # состояния нет.
        return await _locked_chapter(
            payload, user, provider,
            chapter=chapter, language=language, access=access, pair=pair,
        )

    # ── рождение и партнёр: вторая короткая транзакция ─────────────────────
    async with session_scope() as session:
        birth = await resolve_birth(
            session, user, profile_id=payload.profile_id, birth=payload.birth
        )
        options = _options_for(payload.system, payload.house_system)
        if payload.system == "compatibility":
            options["other"] = await _partner(session, user, payload)

    # Расчёт — арифметика с кэшем в памяти, к базе не ходит. Держать ради него
    # соединение незачем, и держать было дорого: скан транзитов измерен в
    # 1.35 секунды, а это ровно тот путь, которым неподписчик открывает
    # «Сегодня».
    result = await _calc(payload.system, birth, **options)
    calc_key = _reading_key(payload.system, birth, options, result, chapter)

    lock_key = f"{user.id}:{payload.system}:{chapter.slug}:{calc_key}:{language}"
    try:
        async with _write_lock(lock_key):
            return await _read_or_write(
                payload, user, provider, chapter=chapter,
                language=language, result=result, calc_key=calc_key,
            )
    finally:
        _prune_lock(lock_key)


# ── закрытая глава: тот же роут, половина текста ───────────────────────────
#
# **Почему 200, а не 402, — решение, которое стоит объяснить один раз здесь.**
#
# Здесь стоял `raise HTTPException(402, {"error": "locked", …})`, и он был
# правдой ровно до тех пор, пока сервер на такой запрос действительно ничего не
# делал. Теперь делает: считает карту, зовёт модель, пишет строку в `Reading`,
# двигает месячный счёт аккаунта. Отвечать кодом ошибки на запрос, который
# сохранил состояние и потратил деньги, — это соврать про то, что он не удался;
# следующий, кто увидит в логе 402, решит, что генерации не было.
#
# Довод продукта — тот же и сильнее. Спека §5 снимает «отдельный маршрут
# пейволла главы» словами «залоченная глава — это сама глава, дописанная
# наполовину, а не другой экран». Дом уже так и устроен: `systems.py` на
# закрытую систему отвечает 200 с полным расчётом и флагом `locked`, и её
# докстринг объясняет почему — «paywall's job is to sell the rest, and a blank
# page sells nothing». Закрытая глава просто перестала быть исключением из
# правила, которое соседний роутер держит с самого начала.
#
# Клиентам это ломающее изменение, и оно осознанное: старый клиент на закрытую
# главу `POST /v1/readings` вообще не шлёт — он знает право заранее из
# оглавления и рисует стену сам, — а новому нужен абзац, за которым он и
# приходит.


def _locked_payload(
    system: str,
    chapter_slug: str,
    access: entitlements.Access,
    *,
    opening: dict | None = None,
    cached: bool = False,
    created_at: str | None = None,
    needs_partner: bool = False,
) -> dict:
    """Ровно то, из чего клиент рисует C2–C6.

    `reading` присутствует и равен `None` намеренно: форма ответа одна и та же
    для открытой и закрытой главы, и «главы здесь нет» сказано полем, а не его
    отсутствием. Клиент, забывший посмотреть на `locked`, наткнётся на пустоту
    сразу, а не покажет сорок слов как всю главу.

    `product` — ключ полки, которым эта система открывается, из каталога, а не
    из `if` здесь: таблица «система → цена» уже есть в `catalogue.unlocks`, и
    вторая её копия однажды предложит «$4.99 навсегда» за транзиты.

    `needs_partner` — единственное «закрыто», которое **не** чинится деньгами:
    пару нечем назвать, поэтому и абзаца нет. Отдельным полем, а не по
    `opening is None`, потому что причин для пустого абзаца несколько (модель
    молчит, месяц выбран) и все прочие лечатся повтором, а эта — вводом
    человека. Спека §1 рисует по нему «tap to add someone →» вместо цены.
    """
    from ...billing.catalogue import unlocks

    return {
        "system": system,
        "chapter": chapter_slug,
        "locked": True,
        "reading": None,
        "opening": opening,
        "access": access.as_dict(),
        "product": unlocks(system),
        "needs_partner": needs_partner,
        "cached": cached,
        "created_at": created_at,
    }


async def _locked_chapter(
    payload: ReadingRequest,
    user,
    provider,
    *,
    chapter,
    language: str,
    access: entitlements.Access,
    pair: str | None,
) -> dict:
    """Закрытая глава со своим открывающим абзацем — кроме пары.

    Совместимость уходит первой же веткой без абзаца вовсе: см. довод там.
    Всё, что ниже, — про остальные системы.

    **Массовый бесплатный путь, и потому разрезанный тщательнее прочих.** Сюда
    приходит каждый, кто открыл любую из сорока закрытых глав, — то есть
    почти весь трафик продукта. Сессии у него нет: чтения идут короткими
    `session_scope`, а `_write_opening` зовёт модель, не держа соединения.

    **Абзац — лучшее усилие, стена — обязательство.** Всё, что может пойти не
    так в генерации (модель молчит, ключа нет, месячный потолок аккаунта
    выбран, валидатор отверг три попытки, у человека не сохранена дата
    рождения), кончается здесь `opening=None` и записью в лог, а не ошибкой
    наружу. Довод простой: экран, на котором человеку показывают цену, обязан
    отрисоваться всегда. 503 вместо пейволла — это не «мы честно сказали о
    сбое», это ненайденная кнопка «купить» у человека, который уже потянулся за
    кошельком.

    Деньги при этом не теряются: путь отказа писателя платит через
    `_charge_anyway`, как и у обычной главы, — три попытки действительно
    случились.
    """
    def wall(**extra) -> dict:
        return _locked_payload(payload.system, chapter.slug, access, **extra)

    if payload.system == "compatibility":
        # **У пары бесплатного текста нет вообще, и здесь это кончается.**
        #
        # Владелец, 19.08.2026: «мы не даем бесплатно пару никакую все за деньги
        # можно писать только имя». Бесплатны расчёт синастрии и возможность
        # завести человека; любой *написанный* текст пары — платный. Открывающий
        # абзац написанный, значит его здесь нет — ни у главы I, ни у остальных.
        #
        # Почему это стоит отдельной ветки, а не настройки главы: пару можно
        # завести даром и сколько угодно раз, и каждый заход в её закрытую главу
        # звал бы сильную модель за наш счёт на человека, который не заплатил ни
        # разу. У натальной карты такого рычага нет — там абзац окупается тем,
        # что продаёт саму карту, — поэтому остальные системы ниже не меняются.
        #
        # Выход **до** расчёта и до `_opening_allowance` нарочно: пара не должна
        # ни считаться ради выброшенной строки, ни тратить месячное окно абзацев,
        # которое бережёт настоящую витрину натальной карты.
        #
        # `needs_partner` остаётся смыслом, а не следствием пустого абзаца: ноль
        # партнёров или несколько без имени — единственное «закрыто», которое не
        # чинится деньгами, и клиент рисует по нему «tap to add someone →»
        # (спека §1, карточка совместимости) вместо цены.
        return wall(needs_partner=pair is None)

    # **Ключ берётся до расчёта, и это не микрооптимизация.**
    #
    # У обычной главы иначе нельзя: её ключ включает список факторов, которых
    # без расчёта не существует. У абзаца — можно, ровно потому, что факторов
    # в его ключе нет (см. `_opening_key`), а рождение и неподвижные опции
    # известны сразу. Разница видна на транзитах: их расчёт — скан года,
    # 1.35 секунды, и он же стоит за экраном «Сегодня», в который неподписчик
    # заходит каждый день. Считать его ради строки, которая уже лежит в базе,
    # значит платить секундой за каждое открытие уже написанного.
    async with session_scope() as session:
        try:
            birth = await resolve_birth(
                session, user, profile_id=payload.profile_id, birth=payload.birth
            )
            options = _options_for(payload.system, payload.house_system)
            if payload.system == "compatibility":
                options["other"] = await _partner(session, user, payload)
        except HTTPException as exc:
            # Нет анкеты, нет времени рождения, партнёр не назван — всё это
            # законные 4xx для *открытой* главы, где человек действительно должен
            # что-то доделать. На закрытой они превращают пейволл в форму ввода, и
            # человек не узнаёт, что глава продаётся.
            log.info(
                "no opening for %s/%s — nothing to write from: %s",
                payload.system, chapter.slug, exc.detail,
            )
            return wall()

    calc_key = _opening_key(payload.system, birth, options, chapter)
    stored_chapter = opening_chapter_id(chapter.slug)

    async with session_scope() as session:
        found = await _stored_reading(
            session, user_id=user.id, system=payload.system,
            chapter=stored_chapter, calc_key=calc_key, locale=language,
        )
        if found is not None:
            # **Второй заход бесплатен, и это половина решения владельца.** Абзац
            # пишется один раз на главу и живёт вечно; человек, обошедший все сорок
            # закрытых глав по третьему разу, не стоит нам ничего сверх первого
            # обхода — ни модели, ни расчёта.
            return wall(
                opening=found.body,
                cached=True,
                created_at=found.created_at.isoformat(),
            )

    lock_key = f"{user.id}:{payload.system}:{stored_chapter}:{calc_key}:{language}"
    try:
        async with _write_lock(lock_key):
            async with session_scope() as session:
                again = await _stored_reading(
                    session, user_id=user.id, system=payload.system,
                    chapter=stored_chapter, calc_key=calc_key, locale=language,
                )
                if again is not None:
                    return wall(
                        opening=again.body,
                        cached=True,
                        created_at=again.created_at.isoformat(),
                    )
                # Абзац уже написан на другом языке — переводится, не пишется.
                # Заметно и то, чего эта ветка **не** делает: расчёта карты нет
                # вовсе — переводу факты не нужны, а скан года у транзитов
                # стоит 1.35 секунды на каждое открытие.
                source = await _translation_source(
                    session, user_id=user.id, system=payload.system,
                    chapter=stored_chapter, calc_key=calc_key,
                    exclude_locale=language,
                )
                opening_source = (
                    (
                        dict(source.body), source.locale,
                        list(source.cited_factors), source.profile_id,
                        source.engine_version,
                    )
                    if source is not None
                    else None
                )
                opening_gender = (
                    await _reader_gender(session, user, payload)
                    if opening_source is not None
                    else None
                )
            if opening_source is not None:
                translated = await _translated_opening(
                    payload, user, provider,
                    source=opening_source, language=language,
                    calc_key=calc_key, stored_chapter=stored_chapter,
                    reader_gender=opening_gender,
                )
                if translated is not None:
                    body, cached, created_at = translated
                    return wall(opening=body, cached=cached, created_at=created_at)
            try:
                result = await _calc(payload.system, birth, **options)
            except HTTPException as exc:
                # Неоднозначный час рождения, время не задано у главы, которой
                # оно нужно. Та же логика, что выше: на закрытой главе это
                # причина не написать абзац, а не причина не показать цену.
                log.info(
                    "no opening for %s/%s — the chart could not be computed: %s",
                    payload.system, chapter.slug, exc.detail,
                )
                return wall()
            written = await _write_opening(
                payload, user, provider,
                chapter=chapter_defs.opening_of(chapter), language=language,
                result=result, calc_key=calc_key, stored_chapter=stored_chapter,
            )
    finally:
        _prune_lock(lock_key)

    if written is None:
        return wall()
    body, cached, created_at = written
    return wall(opening=body, cached=cached, created_at=created_at)


async def _translated_opening(
    payload: ReadingRequest,
    user,
    provider,
    *,
    source: tuple[dict, str, list, str, str],
    language: str,
    calc_key: str,
    stored_chapter: str,
    reader_gender: str | None = None,
) -> tuple[dict, bool, str] | None:
    """Уже написанный абзац на новом языке — переводом, без модели-писателя.

    Тот же контракт, что у `_write_opening`: `None` — причина не показать
    абзац, но не причина не показать цену. Счёт витрины (`SHOWCASE_METRIC`)
    двигается и здесь: перевод — тоже наша плата за показ, только в двадцать
    раз меньшая. `_opening_allowance` не спрашивается: петля «сменил дату —
    пиши заново» сюда не ведёт, исходник обязан иметь тот же `calc_key`, а
    языков всего семь.
    """
    src_body, src_locale, src_cited, src_profile_id, src_engine = source
    translated = await _translated_body(
        user, provider,
        body=src_body,
        pieces=translator.reading_pieces,
        source_locale=src_locale,
        target_locale=language,
        paid=False,
        factors=src_cited,
        reader_gender=reader_gender,
        ledger=cost.SHOWCASE_METRIC,
    )
    if translated is None:
        return None
    t_body, t_spend, t_model = translated

    async with session_scope() as session:
        record = Reading(
            user_id=user.id,
            profile_id=src_profile_id,
            system=payload.system,
            chapter=stored_chapter,
            locale=language,
            calc_key=calc_key,
            engine_version=src_engine,
            model=t_model,
            body=t_body,
            cited_factors=src_cited,
            input_tokens=t_spend.input_tokens,
            output_tokens=t_spend.output_tokens,
            cost_cents=t_spend.cents,
        )
        session.add(record)
        await _count(session, user, "openings_translated")
        await _spend(session, user, t_spend.cents, ledger=cost.SHOWCASE_METRIC)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            log.warning(
                "lost the opening translation race for %s/%s — returning the "
                "stored copy", payload.system, stored_chapter,
            )
            await _spend(session, user, t_spend.cents, ledger=cost.SHOWCASE_METRIC)
            await session.flush()
            theirs = await _stored_reading(
                session, user_id=user.id, system=payload.system,
                chapter=stored_chapter, calc_key=calc_key, locale=language,
            )
            if theirs is None:
                return None
            return theirs.body, True, theirs.created_at.isoformat()

    return t_body, False, utcnow().isoformat()


async def _write_opening(
    payload: ReadingRequest,
    user,
    provider,
    *,
    chapter,
    language: str,
    result: CalcResult,
    calc_key: str,
    stored_chapter: str,
) -> tuple[dict, bool, str] | None:
    """Сорок слов, один раз на главу. `None`, если написать не вышло.

    **Средняя модель и бесплатный потолок**, и оба выбраны не по привычке.
    Абзац тратится до всякого решения о покупке, то есть на каждого, включая
    тех, кто не купит никогда, — это ровно тот расход, который обязан
    упираться в `free_user_budget`. А `test_the_strong_model_is_what_the_free_ceiling_refuses`
    уже доказывает, что промт астрокартографии на сильной модели в этот потолок
    не влезает: сильная модель здесь означала бы 503 на самой длинной системе.

    **Регистр — свой (`opening`), а не «бесплатный».** `paid` в этом вызове
    выбирает потолок, `register` — голос, и здесь они обязаны разойтись: платить
    надо по-бесплатному, а писать — первый абзац главы, а не законченную
    бесплатную заметку. Это ровно тот случай, ради которого `register` и
    отделён от `paid` (см. `voice.system_prompt`).

    **Три части, и середина без соединения.** Читается всё, что нужно модели;
    транзакция коммитится; модель пишет; строка и счётчики ложатся во второй
    транзакции. Это самый массовый бесплатный путь продукта — тот самый, ради
    которого пятнадцати соединений и не хватало.
    """
    _cheap, mid, _strong = models()

    # `entitlements.tier_of` отсюда убран: он читал три таблицы и никуда не
    # уходил — абзац всегда пишется на средней модели и по бесплатному потолку,
    # тир на это не влияет. Один лишний запрос на каждой закрытой главе, то
    # есть на самом массовом пути продукта.

    # ── чтения перед моделью ───────────────────────────────────────────────
    async with session_scope() as session:
        try:
            # **Спрашивается до генерации, а не после.** У обычной главы этот
            # вопрос стоит после письма, и там это безобидно: без анкеты туда не
            # дойти. Сюда — дойти можно, рождением прямо в теле запроса, и тогда
            # писать абзац, который некуда положить, значит заплатить за текст,
            # который тут же выбросят.
            profile_id = await _profile_id(session, user)
            # **Абзац не платит из потолка на чтение, и это не поблажка.**
            #
            # Здесь стоял `_guard_month` — тот же ограничитель, что бережёт деньги
            # от человека, читающего много. Но открывающий абзац не чтение: это
            # витрина, единственное, чем закрытая глава продаётся. Отказав в нём
            # ради нескольких центов, мы получаем экран, где над размытием пусто,
            # — и владелец увидел ровно это: «все эти страницы должны выглядеть
            # таким образом: кусочек текста главы и заблюренная часть».
            #
            # Пустое место вместо начала не экономит, а отменяет продажу.
            #
            # **Убрать вызов было половиной дела, и без второй половины
            # освобождение не работало.** Расход абзаца всё равно ложился в ту же
            # статью леджера, которую `_guard_month` читает на беседе, — то есть
            # витрина не платила за себя, а платила за человека вперёд. По замеру
            # (`cost.MEASURED_OVER_PROJECTED`) абзац стоит 3.556¢, а достижимы в
            # одиночку тридцать шесть стен из сорока — четыре главы совместимости
            # требуют второго человека. Это $1.28 против $1.10 `free_month_budget`:
            # тот, кто просто посмотрел витрину целиком, получал 429
            # `month_budget` на первом же бесплатном вопросе. Поэтому `_spend` ниже пишет в
            # `cost.SHOWCASE_METRIC` — отдельную статью, которую беседа не читает.
            #
            # Расход при этом ограничен, и дважды. Абзац пишется один раз на главу
            # и живёт в кэше навсегда: сорок закрытых глав — это $1.42 за всю
            # жизнь аккаунта по замеру (44 абзаца в `data/alma.db`; прежние
            # «около тридцати центов» здесь были посчитаны по проекции, которая
            # занижает счёт вдвое). А от петли (сменил дату рождения — ключ
            # расчёта другой — пиши заново) стоит [_opening_allowance] ниже: он и
            # есть потолок витрины, и в деньгах его цена названа рядом с ним.
            await _opening_allowance(session, user)
            memory = await _recall(session, user)
            reader_gender = await _reader_gender(session, user, payload)
        except HTTPException as exc:
            # 429 счётчика витрины или 400 «сначала сохрани дату рождения». И
            # то и другое — причина не написать абзац, а не причина не показать
            # цену. Ловится **внутри** транзакции нарочно: счёт попыток,
            # который `_opening_allowance` уже увеличил, обязан сохраниться, —
            # иначе ограничитель петли сам себя обнуляет на каждом отказе.
            log.warning(
                "no opening for %s/%s: %s", result.system, chapter.slug,
                getattr(exc, "detail", exc),
            )
            return None

    # Соединения здесь нет — и это те самые 10–40 секунд.
    try:
        written = await writer.write(
            result=result,
            chapter=chapter,
            provider=provider(),
            model=mid,
            locale=language,
            paid=False,
            register="opening",
            memory=memory,
            reader_gender=reader_gender,
            # Сорок слов витрины обдумывать нечего, а вызовов этих больше всех
            # прочих вместе взятых — до сорока на каждого, кто просто листает.
            # Довод и замер — у `writer.SHOWCASE_EFFORT`.
            effort=writer.SHOWCASE_EFFORT,
        )
    except ReadingRefused as exc:
        # Три попытки состоялись и стоили денег — счёт двигается, как и у
        # обычной главы. `_charge_anyway` открывает свою короткую транзакцию:
        # выбрасывать здесь больше нечего, потому что сессии на время генерации
        # не было.
        await _charge_anyway(
            user, cents=exc.spend.cents, ledger=cost.SHOWCASE_METRIC
        )
        log.warning(
            "no opening for %s/%s: %s", result.system, chapter.slug, exc
        )
        return None
    except AnswerTruncated as exc:
        # Обрезанные попытки — тоже состоявшиеся генерации, и стоят они ровно
        # столько же. Ветка стоит **выше** `ModelUnavailable`, потому что
        # `AnswerTruncated` — его наследник: попав в общий `except` ниже, три
        # оплаченные попытки уходили в лог и никуда больше. Стена всё равно
        # отдаётся — экран с ценой обязан отрисоваться, — но бесплатной она
        # больше не бывает.
        await _charge_anyway(
            user, cents=_truncated_cents(exc), ledger=cost.SHOWCASE_METRIC
        )
        log.warning(
            "no opening for %s/%s — truncated every attempt: %s",
            result.system, chapter.slug, exc,
        )
        return None
    except (cost.BudgetExceeded, ModelUnavailable, HTTPException) as exc:
        # Потолок вызова и молчащий провайдер: причина не написать абзац, а не
        # причина не показать цену.
        log.warning(
            "no opening for %s/%s: %s", result.system, chapter.slug,
            getattr(exc, "detail", exc),
        )
        return None

    # ── запись абзаца и счётчиков ──────────────────────────────────────────
    async with session_scope() as session:
        record = Reading(
            user_id=user.id,
            profile_id=profile_id,
            system=result.system,
            chapter=stored_chapter,
            locale=language,
            calc_key=calc_key,
            engine_version=result.engine_version,
            model=written.model,
            body=written.as_dict(),
            cited_factors=list(written.cited_factors),
            input_tokens=written.spend.input_tokens,
            output_tokens=written.spend.output_tokens,
            cost_cents=written.spend.cents,
        )
        session.add(record)
        await _count(session, user, "openings_written")
        await _spend(
            session, user, written.spend.cents, ledger=cost.SHOWCASE_METRIC
        )
        try:
            await session.flush()
        except IntegrityError:
            # Другой воркер написал тот же абзац между нашим поиском и вставкой.
            # Его слова побеждают, как и у обычной главы; наша генерация всё равно
            # состоялась, поэтому сумма записывается заново после отката.
            #
            # Гонка стала **шире**, а не уже: между поиском и вставкой теперь
            # лежит закрытая транзакция, а не открытая. Поэтому эта ветка и
            # обязана была остаться — она единственное, что стоит между двумя
            # воркерами и 500-й на UNIQUE.
            await session.rollback()
            log.warning(
                "lost the opening race for %s/%s — returning the stored copy",
                result.system, chapter.slug,
            )
            await _spend(
                session, user, written.spend.cents, ledger=cost.SHOWCASE_METRIC
            )
            await session.flush()
            theirs = await _stored_reading(
                session, user_id=user.id, system=result.system,
                chapter=stored_chapter, calc_key=calc_key, locale=language,
            )
            if theirs is None:
                return None
            return theirs.body, True, theirs.created_at.isoformat()

    return written.as_dict(), False, utcnow().isoformat()


def _opening_key(
    system: str,
    birth,
    options: dict,
    chapter: chapter_defs.Chapter,
) -> str:
    """Личность открывающего абзаца: **кто ты, а не что сегодня в небе.**

    Отличается от `_reading_key` ровно одним — здесь нет `factors`, — и это
    отличие и есть слово «навсегда» из решения владельца.

    Считать абзац главой было бы естественно и дорого. Ключ главы включает
    список факторов, из которых она написана, потому что глава, у которой
    появился новый повод что-то сказать, честно переписывается. Для транзитов
    этот список меняется каждый раз, когда контакт входит в орб, — то есть
    открывающий абзац закрытой главы транзитов переписывался бы раз в
    несколько дней, у каждого свободного аккаунта, вечно. Тридцать центов на
    аккаунт превратились бы в тридцать центов в месяц на аккаунт, который
    ничего не купил.

    Что осталось в ключе и почему: рождение (двое разных людей — два разных
    абзаца), дом системы и прочие неподвижные опции (плацидус и цельные знаки
    дают разные позиции), локаль — отдельной колонкой `Reading.locale`, и
    версия движка внутри `cache_key`. Последняя означает, что смена арифметики
    всё-таки перепишет абзацы; это редкое и намеренное событие, и платить за
    правильные позиции в такой день дешевле, чем цитировать факторы, которых
    движок больше не производит.
    """
    stable = {
        name: value for name, value in options.items() if name not in MOMENT_OPTIONS
    }
    if "other" in stable and hasattr(stable["other"], "fingerprint"):
        stable["other"] = stable["other"].fingerprint()
    return cache_key(
        system, birth, chapter=opening_chapter_id(chapter.slug), **stable
    )


async def _pair_credit_or_paywall(session, user, partner_id: str) -> None:
    """Пропустить дальше, если отчёт про этого человека уже оплачен или включён.

    Три состояния, и они разные:

    * **грант на эту пару уже есть** — куплен за $4.99 или выдан кредитом в
      прошлом месяце. Ничего не тратится: отчёт оплачен один раз и читается
      всегда, включая четыре его главы и все перечитывания;
    * **гранта нет, кредит периода цел** — тратится кредит и выписывается такой
      же бессрочный грант. Дальше эта пара навсегда попадает в первый случай, в
      том числе после отмены подписки: период, в котором её открыли, оплачен;
    * **гранта нет и кредит потрачен** — 402 с ценой. Это А7 §4, «вторая
      проверка в том же цикле», и копирайт на экране обязан звучать как «сверх
      месячной проверки», а не как «нет доступа»: человек платит нам каждый
      месяц и должен понимать, за что именно доплачивает.

    Свободный человек без подписки сюда не доходит вовсе — его остановил 402
    выше по течению, потому что покрыть совместимость ему нечем.

    **И четвёртое состояние, ради которого здесь стоит ранний выход:** доступ
    пришёл не от плана с включёнными проверками. Старая годовая, недельная,
    легаси-`live` — они покрывают совместимость целиком и были проданы до того,
    как «одна в месяц» вообще существовала (А6: ничего не отбираем). Считать им
    кредит значило бы предъявить пейволл человеку, которому мы обещали иначе, и
    предъявить именно в тот месяц, когда он решает, продлевать ли.
    """
    from ...billing import credits as pair_credits

    if partner_id in await entitlements.unlocked_pairs(session, user):
        return

    if await pair_credits.ensure_period(session, user) is None:
        log.info(
            "account %s opens a pair with no credit-bearing plan — access came "
            "from a grant that predates the monthly allowance, so nothing is "
            "counted", user.id,
        )
        return

    if await pair_credits.spend(session, user, partner_id) is not None:
        return

    state = await pair_credits.state(session, user)
    raise HTTPException(
        status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            # Отдельный код ошибки, а не общий `locked`, и это важнее, чем
            # кажется: экран, который нарисует «купи подписку» подписчику,
            # выглядит как поломка биллинга и приводит к отмене, а не к покупке.
            "error": "beyond_monthly_pair",
            "message": (
                "this month's included compatibility report has been used — "
                "another one is $4.99 and stays yours forever"
            ),
            "system": "compatibility",
            "product": "pair.check",
            "profile_id": partner_id,
            "period_end": state["period_end"],
        },
    )


async def _reader_gender(session, user, payload) -> str | None:
    """The reader's grammatical gender, when they volunteered one.

    From the requested profile when the request names one, from the self
    profile otherwise. `None` keeps the genderless register — absence is a
    first-class state, never a default.
    """
    from ...db.models import Profile

    query = select(Profile).where(Profile.user_id == user.id)
    if getattr(payload, "profile_id", None):
        query = query.where(Profile.id == payload.profile_id)
    else:
        query = query.where(Profile.is_self.is_(True))
    profile = (await session.execute(query)).scalars().first()
    return profile.gender if profile is not None else None


async def _read_or_write(
    payload: ReadingRequest,
    user,
    provider,
    *,
    chapter,
    language: str,
    result: CalcResult,
    calc_key: str,
) -> dict:
    """The half of `read` that must run one-at-a-time per reading key.

    Everything below happens only for somebody entitled to this chapter: the
    wall in `read` has already answered 402 otherwise, before the chart was
    even computed. No `access` argument reaches here for that reason — the one
    thing it used to decide, the blurred-preview flag, no longer exists.

    **Три части: прочитать и закоммитить, написать без соединения, записать.**
    Между чтением и записью лежит `writer.write` — 10–40 секунд и до трёх
    попыток, — и это ровно тот отрезок, который держал соединение пула. Замок
    `_write_lock` снаружи по-прежнему один на ключ главы, а защита от
    межпроцессной гонки — ветка `IntegrityError` ниже — обязана была остаться и
    осталась: между поиском и вставкой теперь закрытая транзакция, то есть окно
    гонки шире, чем было.
    """
    # ── всё, что нужно прочитать до модели ────────────────────────────────
    async with session_scope() as session:
        stored = await _stored_reading(
            session, user_id=user.id, system=payload.system,
            chapter=chapter.slug, calc_key=calc_key, locale=language,
        )
        if stored is not None:
            # Written once, returned forever. The reading a person paid for must
            # say the same thing the second time they open it — and the request
            # that lost the race to the lock wakes up exactly here, having spent
            # nothing.
            return {
                "reading": stored.body,
                "cached": True,
                "created_at": stored.created_at.isoformat(),
            }

        # Та же глава на другом языке — исходник: она переводится дёшево, а не
        # пишется заново. Довод и цена — у `_translation_source`.
        source = await _translation_source(
            session, user_id=user.id, system=payload.system,
            chapter=chapter.slug, calc_key=calc_key, exclude_locale=language,
        )

        # One fact — is this chapter the free sample? — chooses both the model
        # and the ceiling that model is spent against, so the two cannot
        # disagree. They used to. Every chapter went to the strong model while
        # `writer.write` guarded it with `paid=not chapter.free`, i.e. against
        # the $0.05 free ceiling, and the astrocartography sample carries eleven
        # thousand characters of line descriptions: $0.0530 projected on Opus 5.
        # It raised BudgetExceeded on the first attempt and answered 503, so the
        # one chapter that exists to sell astrocartography could not be read by
        # anybody, ever. The same prompt projects $0.0318 on the mid model.
        _cheap, mid, strong = models()
        model = mid if chapter.free else strong

        tier = await entitlements.tier_of(session, user)
        memory = await _recall(session, user)
        await _guard_month(
            session,
            user,
            tier=tier,
            locale=language,
            # Потолок спрашивается по цене того, что действительно будет
            # сделано: перевод, когда есть исходник, — генерация иначе. Если
            # перевод сорвётся, потолок для генерации спросится заново ниже.
            projected=(
                _translation_projection(source.body, locale=language)
                if source is not None
                else _chapter_projection(
                    result, chapter, model=model, locale=language, memory=memory
                )
            ),
        )
        reader_gender = await _reader_gender(session, user, payload)
        # **Переехал сюда с той стороны генерации, и это исправление.** Стоял
        # после письма, где «без анкеты туда не дойти» — неправда: рождение
        # можно прислать прямо в теле запроса, и тогда мы платили за главу,
        # которую некуда положить, и отвечали 400. Тот же 400, только до денег.
        profile_id = await _profile_id(session, user)
        # Снимок до конца транзакции: тело исходника читается моделью те же
        # 3–10 секунд, что и генерация, и держать ради него строку сессии
        # незачем.
        source_snapshot = (
            (dict(source.body), source.locale, list(source.cited_factors))
            if source is not None
            else None
        )

    if source_snapshot is not None:
        src_body, src_locale, src_cited = source_snapshot
        translated = await _translated_body(
            user, provider,
            body=src_body,
            pieces=translator.reading_pieces,
            source_locale=src_locale,
            target_locale=language,
            paid=not chapter.free,
            factors=src_cited,
            reader_gender=reader_gender,
        )
        if translated is not None:
            t_body, t_spend, t_model = translated
            async with session_scope() as session:
                record = Reading(
                    user_id=user.id,
                    profile_id=profile_id,
                    system=payload.system,
                    chapter=chapter.slug,
                    locale=language,
                    calc_key=calc_key,
                    engine_version=result.engine_version,
                    model=t_model,
                    body=t_body,
                    cited_factors=src_cited,
                    input_tokens=t_spend.input_tokens,
                    output_tokens=t_spend.output_tokens,
                    cost_cents=t_spend.cents,
                )
                session.add(record)
                await _count(session, user, "readings_translated")
                await _spend(session, user, t_spend.cents)
                try:
                    await session.flush()
                except IntegrityError:
                    # Та же гонка, что у генерации ниже, и тот же исход: чьи
                    # слова легли первыми, те и остаются.
                    await session.rollback()
                    log.warning(
                        "lost the translation race for %s/%s — returning the "
                        "stored copy", payload.system, chapter.slug,
                    )
                    await _spend(session, user, t_spend.cents)
                    await session.flush()
                    theirs = await _stored_reading(
                        session, user_id=user.id, system=payload.system,
                        chapter=chapter.slug, calc_key=calc_key, locale=language,
                    )
                    if theirs is not None:
                        return {
                            "reading": theirs.body,
                            "cached": True,
                            "created_at": theirs.created_at.isoformat(),
                        }
                    raise
            return {
                "reading": t_body,
                "cached": False,
                "created_at": utcnow().isoformat(),
            }
        # Перевод сорвался — дальше обычная генерация, но её месячный потолок
        # выше спрашивался по цене перевода, то есть почти не спрашивался.
        async with session_scope() as session:
            await _guard_month(
                session, user, tier=tier, locale=language,
                projected=_chapter_projection(
                    result, chapter, model=model, locale=language, memory=memory
                ),
            )

    try:
        written = await writer.write(
            result=result,
            chapter=chapter,
            provider=provider(),
            model=model,
            locale=language,
            paid=not chapter.free,
            memory=memory,
            reader_gender=reader_gender,
        )
    except ReadingRefused as exc:
        # Charged before the refusal is raised. Three attempts really happened
        # and really cost money, and a ceiling that only sees the requests
        # that succeeded is not a ceiling on what an account can spend — it is
        # a ceiling on what an account can spend *usefully*.
        await _charge_anyway(user, cents=exc.spend.cents)
        raise HTTPException(
            422, detail={"error": "reading_refused", "message": str(exc)}
        ) from exc
    except cost.BudgetExceeded as exc:
        # Цифры — в лог, читателю — фраза. Текст исключения называет
        # себестоимость и потолок; он писался для того, кто чинит, и на экране
        # не объясняет ничего.
        log.error("budget exceeded for %s/%s: %s", payload.system, chapter.slug, exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "budget_exceeded",
                "message": i18n_replies.reply("budget_exceeded", payload.locale),
            },
        ) from exc
    except AnswerTruncated as exc:
        # **Самый дорогой исход, и до этой ветки он стоил аккаунту ноль.**
        #
        # Три попытки, обрезанные все три, — это три настоящих генерации: на
        # русской главе сильной моделью около $0.6. `AnswerTruncated` наследует
        # `ModelUnavailable`, поэтому попадал в ветку ниже, отвечал 503 мимо
        # `_charge_anyway`, а откат сессии довершал дело — в леджере не
        # оставалось ничего. Месячный потолок при этом не двигался, так что
        # «повторить» можно было жать бесконечно, и каждый раз за те же деньги.
        # Ответ читателю тот же 503 с той же фразой: меняется счёт, а не экран.
        await _charge_anyway(user, cents=_truncated_cents(exc))
        log.error(
            "every attempt at %s/%s was truncated: %s", payload.system, chapter.slug, exc
        )
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ai_unavailable", "message": str(exc)},
        ) from exc
    except ModelUnavailable as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ai_unavailable", "message": str(exc)},
        ) from exc

    # ── запись главы и счётчиков ──────────────────────────────────────────
    async with session_scope() as session:
        record = Reading(
            user_id=user.id,
            profile_id=profile_id,
            system=payload.system,
            chapter=chapter.slug,
            locale=language,
            calc_key=calc_key,
            engine_version=result.engine_version,
            model=written.model,
            body=written.as_dict(),
            cited_factors=list(written.cited_factors),
            input_tokens=written.spend.input_tokens,
            output_tokens=written.spend.output_tokens,
            cost_cents=written.spend.cents,
        )
        session.add(record)
        await _count(session, user, "readings_written")
        await _spend(session, user, written.spend.cents)
        try:
            await session.flush()
        except IntegrityError:
            # Another worker wrote the same reading between our lookup and our
            # insert. Their words win — the promise is that a chapter says the
            # same thing every time it is opened, and theirs is the copy already
            # stored. Our generation still happened and still cost money, so the
            # spend is re-recorded after the rollback wipes it.
            await session.rollback()
            log.warning(
                "lost the reading race for %s/%s — returning the stored copy",
                payload.system, chapter.slug,
            )
            await _spend(session, user, written.spend.cents)
            await session.flush()
            theirs = await _stored_reading(
                session, user_id=user.id, system=payload.system,
                chapter=chapter.slug, calc_key=calc_key, locale=language,
            )
            if theirs is not None:
                return {
                    "reading": theirs.body,
                    "cached": True,
                    "created_at": theirs.created_at.isoformat(),
                }
            raise

    return {
        "reading": written.as_dict(),
        "cached": False,
        "created_at": utcnow().isoformat(),
    }


def _reading_key(
    system: str,
    birth,
    options: dict,
    result: CalcResult,
    chapter: chapter_defs.Chapter,
) -> str:
    """The identity of one written chapter: the facts it was written from.

    Not the system's cache key. That is what it used to be, and the two are
    different questions. A cache key covers the whole system's answer, so for
    a system whose answer moves daily it moves daily — correctly, because a
    transit scan really is different tomorrow. But `Reading.calc_key` is how a
    *stored chapter* is found again, and a chapter is not the system. Keying
    one on the other rewrote, and charged for, every chapter of numerology and
    transits every midnight: five numerology chapters at $0.20 a day against
    an owner whose whole month is worth less than a week of that, and the
    third or fourth day they opened a chapter they had paid for and were told
    they had run out of money. The stored-reading shortcut that exists to make
    that impossible never fired, because the row was never found.

    So the key is the chapter's own inputs. `relevant_factors` is exactly what
    `writer.write` is allowed to cite and exactly what the reader is shown
    under "Read from", so if that list is unchanged, regenerating could only
    produce another way of saying the same thing — and the product's first
    promise is that it will not. When it does change, the chapter genuinely
    has something new to say and is written again: transits' "what is active
    now" moves when a transit comes into orb, not when the clock passes
    midnight.

    The birth, the engine version and the non-moment options stay in the key
    because two people, two house systems and two engine versions are
    genuinely different readings. Only the moment is gone, replaced by what
    the moment actually changed.
    """
    stable = {
        name: value for name, value in options.items() if name not in MOMENT_OPTIONS
    }
    if "other" in stable and hasattr(stable["other"], "fingerprint"):
        stable["other"] = stable["other"].fingerprint()
    return cache_key(
        system,
        birth,
        chapter=chapter.slug,
        factors="|".join(chapter_defs.relevant_factors(chapter, result.factors)),
        **stable,
    )


async def _partner(session, user, payload: ReadingRequest):
    """The second person a compatibility reading is about.

    Without this the route was a 500 and always had been: `_options_for` fell
    through to `{"house_system": …}` and `compatibility_result` requires
    `other`, so the sample chapter that exists to sell the report raised
    TypeError for everybody who asked for it. The budget test priced that
    chapter, which read as coverage of a path that never executed.

    **Ветка 422 ниже с этого роута больше не достижима, и остаётся защитой.**
    Оба вызывающих спрашивают `deps.partner_profile_id` раньше, и «партнёров
    ноль или несколько, ни один не назван» кончается там же — стеной с
    `needs_partner: true`, а не ошибкой. Убрать 422 значило бы, что следующий
    вызывающий этой функции — а она не про HTTP — получит на том же состоянии
    TypeError из движка. Формулировка на человеческом языке нужна ровно на тот
    случай, и стоит она одного `if`.
    """
    from ...db.models import Profile
    from ..deps import birth_from_profile

    if not payload.partner_profile_id:
        # No id sent: the person the account has added is the obvious answer,
        # and with exactly one partner it is the only one. The owner added his
        # partner, opened the chapter, and was told to "send
        # partner_profile_id" — an API field name, on a reading screen.
        # Demanding the id stays right only once there are several partners to
        # be ambiguous between.
        from sqlalchemy import select as _select
        others = (
            await session.execute(
                _select(Profile)
                .where(Profile.user_id == user.id, Profile.is_self.is_(False))
                .order_by(Profile.created_at)
            )
        ).scalars().all()
        if len(others) == 1:
            from ..deps import birth_from_profile as _bfp
            return _bfp(others[0])
        raise HTTPException(
            422,
            detail={
                "error": "partner_required",
                # Читателю — фраза на его языке, зовущему эндпоинт руками —
                # код ошибки. Прежняя строка называла имя поля API и уходила
                # прямо на экран главы: снято владельцем на кадре, посреди
                # русской страницы.
                "message": i18n_replies.reply("partner_required", payload.locale),
            },
        )
    profile = await session.get(Profile, payload.partner_profile_id)
    if profile is None or profile.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no such profile")
    return birth_from_profile(profile)


async def _partner_for_chat(session, user):
    """Whoever this person has added, for a conversation rather than a reading.

    A reading names its partner explicitly — `_partner` above demands the id
    and 422s without it, which is right when somebody asked for *that* couple's
    chapter. A conversation cannot ask: they typed "how are we doing" and there
    is nobody to ask which "we".

    So it takes the most recently added other person, and takes nobody rather
    than guessing when there is none. One saved partner is the overwhelmingly
    common case; somebody with several gets the newest, and if they meant the
    other one they can say so, which is a conversation working rather than
    failing.
    """
    from ...db.models import Profile
    from ..deps import birth_from_profile

    profile = (
        await session.execute(
            select(Profile)
            .where(Profile.user_id == user.id, Profile.is_self.is_(False))
            .order_by(Profile.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    return birth_from_profile(profile) if profile else None


def _options_for(system: str, house_system: str) -> dict:
    """The calculation options for one request, at day resolution and no finer.

    Every option here names a day, a year, or nothing — never an instant. That
    is not the same as coarsening a *reference date*, which would be wrong:
    numerology puts "personal day N" in its factor list where the AI may
    assert it, and the Birth Card's year card turns on a birthday that falls on
    some day other than the first for thirty people in thirty-one. Widening
    either of those would print a number that is stale on the day it is
    written. `calc.cache.TIME_SCOPE` decides how wide a *key* is; this decides
    what is asked, and the two have to agree.

    Which is why the transit scan starts at midnight rather than at
    `now()`. Its key is already day-resolution — a year-long scan costs over a
    second and a key that moved with the clock would never hit — so passing the
    true instant made the answer finer than its own key: the stored transits of
    a day were whichever worker happened to compute them first, and every other
    worker computed a scan that differed in the second decimal of an orb. A hit
    was distinguishable from a miss, which `cache.py`'s docstring forbids, and
    once a written chapter is keyed on the facts it was written from, that
    difference is a second copy of the same chapter. `systems.py` has always
    rounded this way for the same reason.
    """
    today = datetime.now(timezone.utc)
    if system in ("numerology", "birth-card", "synthesis"):
        return {"reference": today.date()}
    if system == "transits":
        midnight = datetime.combine(today.date(), datetime.min.time(), tzinfo=timezone.utc)
        return {"start": midnight, "days": 365, "house_system": house_system}
    if system == "solar-return":
        return {"year": today.year, "house_system": house_system}
    return {"house_system": house_system}


async def _profile_id(session, user) -> str:
    from ...db.models import Profile

    row = (
        await session.execute(
            select(Profile.id).where(Profile.user_id == user.id).order_by(
                Profile.is_self.desc()
            ).limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="save your birth data before generating a reading",
        )
    return row


# ── memory and counters ────────────────────────────────────────────────────

async def _recall(session, user, limit: int = 8) -> list[str]:
    rows = (
        await session.execute(
            select(Memory)
            .where(Memory.user_id == user.id)
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [row.body for row in rows]


async def _remember(session, user, items: tuple[str, ...], source: str) -> None:
    """Store what Alma learned, without duplicating what she already knows."""
    known = {body.lower() for body in await _recall(session, user, limit=50)}
    for item in items:
        if item.lower() in known:
            continue
        session.add(Memory(user_id=user.id, kind="fact", body=item, source=source))
    await session.flush()


#: Ключ строки счётчика. Формула одна на весь сервис и живёт в `db/counters`;
#: здесь оставлено имя, которым её звали в этом файле, чтобы вторая формула не
#: завелась по недосмотру.
_counter_id = counters.counter_id


#: The date a lifetime counter is filed under. Any fixed value works; this one
#: is obviously not a real day, so a row in the table reads as "for ever"
#: rather than as a mysterious purchase in 1970.
FOREVER = date(1970, 1, 1)


def _period_start(period: str, at: datetime | None = None) -> date:
    """The day a counter covering this period is filed under."""
    if period == "once":
        return FOREVER
    today = (at or datetime.now(timezone.utc)).date()
    return today.replace(day=1) if period == "month" else today


async def _count(session, user, metric: str, amount: int = 1, *, day: date | None = None) -> int:
    """Прибавить к счётчику и вернуть, сколько стало. Один запрос.

    **Здесь стояло «прочитать строку, прибавить в питоне, сбросить», и это
    недосчитывало.** Два одновременных хода читали один и тот же ноль, оба
    писали единицу, и порция «три вопроса в день» переставала быть порцией:
    двойное нажатие «отправить» стоило двух генераций, а в счётчике оставляло
    одну. Повторяемое сколько угодно раз — то есть потолка не было вовсе.

    Замок `_chat_slot` сужал щель до одного процесса; воркеров у нас
    `min(8, cpu*2)`, и в комментарии к тому замку это записано прямо: «настоящее
    лекарство — уникальность в базе, и его стоит завести в тот день, когда
    воркеров станет больше одного». Этот день настал, лекарство — `counters.add`:
    `INSERT … ON CONFLICT DO UPDATE SET count = count + :n RETURNING count`, то
    есть без окна между чтением и записью и одинаково на всех воркерах.
    """
    when = day or datetime.now(timezone.utc).date()
    count, _cents = await counters.add(
        session, user_id=user.id, day=when, metric=metric, count=amount
    )
    return count


async def _spend(
    session, user, cents: float, *, ledger: str = cost.SPEND_METRIC
) -> None:
    """Record what a generation cost, in cents, against today.

    These rows are what `cost.month_spend` sums to decide whether an account
    has spent its month, which is why the metric name is imported from there
    rather than written out again: a typo here would not fail anything, it
    would just make every account look free.

    **`ledger` выбирает статью, а не отменяет запись.** По умолчанию это счёт
    чтения — тот, который читает `_guard_month`. Витрина (открывающий абзац
    закрытой главы) пишет в `cost.SHOWCASE_METRIC`: её расход — наша плата за
    показ, а не потребление человека, и складывать их в одно число значит
    отказывать человеку в вопросе за то, что мы ему что-то показали. Довод
    целиком — у `cost.SHOWCASE_METRIC` и на месте вызова в `_write_opening`.

    **Одним запросом по той же причине, что и `_count`, но потеря здесь
    обиднее.** Недосчитанные вопросы — это порция, отданная сверх обещанного;
    недосчитанные центы — это месячный потолок, который считает нас дешевле,
    чем мы есть, то есть предохранитель, не срабатывающий ровно под нагрузкой,
    ради которой он поставлен.
    """
    await counters.add(
        session,
        user_id=user.id,
        day=datetime.now(timezone.utc).date(),
        metric=ledger,
        cents=cents,
    )


def _truncated_cents(exc: AnswerTruncated) -> float:
    """Во сколько обошёлся прогон, кончившийся обрывом на каждой попытке.

    `AnswerTruncated.spend` проставляет тот, кто вёл цикл попыток
    (`writer.write`, `conversation.answer`), — только он знает, что попыток
    было три, а не одна. Ноль здесь означает ровно одно: исключение пришло не
    из такого цикла, а из одиночного вызова провайдера, и прогона, за который
    надо платить, не было. Отдельной функцией, а не `getattr` на трёх
    площадках, чтобы четвёртая не завела свою версию этого «ноль».
    """
    spend = getattr(exc, "spend", None)
    return spend.cents if spend is not None else 0.0


async def _charge_anyway(
    user, *, cents: float, ledger: str = cost.SPEND_METRIC
) -> None:
    """Record what a failed request already spent, in a transaction of its own.

    The money is written and committed on its own, because otherwise it would
    be rolled back with the failure — which is what used to happen: the router
    raised its 422 before reaching `_spend`, so the only requests the month
    ledger could see were the ones that worked. The refusal path spends *more*
    than the success path — it is the one that retried — so that is not a
    ceiling on what an account can spend, only on what it can spend usefully.

    **Отката больше нет, и он больше не нужен.** Раньше эта функция начиналась
    с `session.rollback()`: до разреза сессия жила весь запрос, и в ней уже
    лежала половина неудачной работы — `Reading` без тела, вопрос без ответа, —
    которую надо было выбросить до коммита денег. Теперь между чтением и
    записью транзакции нет вовсе, поэтому выбрасывать нечего: всё, что было
    прочитано, уже закоммичено, а записи ещё не начиналось. Свой
    `session_scope` — это то же «деньги отдельно от обломков», только без
    обломков.

    Отсюда же исчез и `session` в подписи: передать его значило бы пронести
    открытую транзакцию через генерацию, ради которой всё и затевалось.

    **`ledger` — та же статья, что у `_spend`, и по той же причине.** Три
    попытки, кончившиеся отказом на открывающем абзаце, — это деньги, потраченные
    на показ, и человек, которому мы не смогли ничего показать, тем более не
    должен из-за этого лишиться бесплатного вопроса. Не путать с параметром,
    которого здесь больше нет, — см. следующий абзац.

    **Money only.** This used to take a `metric` and increment the question
    counter as well, so a turn that produced an error screen cost a free reader
    one of three. The parameter is gone rather than left unused: it is one
    keyword away from being reintroduced by somebody reading the call site
    rather than this docstring, and the rule it broke — you pay a question for
    an answer about yourself — is the one the whole taxonomy was built on.
    """
    user_id = user.id
    log.warning("charging %s for a request that produced nothing: %.4f¢", user_id, cents)
    if not cents:
        return
    async with session_scope() as session:
        # `user_id` строкой, а не `user`: у этого вызывающего сессия своя, и
        # чужой объект в ней — expired, то есть чтение `user.id` полезло бы за
        # данными не в ту транзакцию. Это же и причина, по которой примитив
        # принимает идентификатор, а не пользователя.
        await counters.add(
            session,
            user_id=user_id,
            day=datetime.now(timezone.utc).date(),
            metric=ledger,
            cents=cents,
        )


async def _asked(session, user, allowance: Allowance) -> int:
    """How many questions this person has already asked in the current period."""
    key = _counter_id(user.id, _period_start(allowance.period), allowance.metric)
    row = await session.get(UsageCounter, key)
    return (row.count or 0) if row else 0


#: Сколько открывающих абзацев аккаунт может получить за месяц.
#:
#: Не про деньги в первую очередь, а про петлю: абзац кэшируется по ключу
#: расчёта, и человек, меняющий дату рождения туда-обратно, получал бы новый
#: каждый раз. Сорок одна глава — весь продукт; шестьдесят оставляют запас на
#: одну настоящую правку рождения и упираются в потолок только у того, кто
#: крутит форму по кругу.
OPENING_ALLOWANCE = 60

#: Метрика в `usage_counter`. День ставится первым числом месяца — так
#: существующая таблица «за день» даёт месячное ведро без новой схемы.
OPENING_METRIC = "opening"

#: Во что `OPENING_ALLOWANCE` обходится в деньгах: потолок витрины, выраженный
#: в долларах. В рантайме витрину держит счёт абзацев выше — отказывать по
#: деньгам там, где отказ отменяет продажу, значило бы вернуть ту самую ошибку,
#: — а это число сторожит CI: `test_readings_budget.py` умножает шестьдесят
#: абзацев на **замеренную** ставку и сверяется с ним. Сработает оно на том,
#: чего счёт абзацев не видит: удлинили абзац, подключили сильную модель,
#: добавили систему — цена шестидесяти абзацев уехала, а число осталось шесть
#: десятков.
#:
#: 60 × 3.556¢ = $2.13 по замеру на 19.08.2026; тест считает то же самое через
#: округлённый множитель и получает $2.16. Запас до $2.50 — около пятнадцати
#: процентов, то есть тест падает раньше, чем счёт удивляет.
#:
#: **Это отдельная статья, а не прибавка к `free_month_budget`.** Худший месяц
#: бесплатного аккаунта теперь читается так: до $1.10 чтения плюс до $2.50
#: показа, и второе слагаемое достаётся только тому, кто крутит дату рождения
#: по кругу; обычный человек тратит на показ $1.42 один раз за жизнь аккаунта и
#: больше никогда.
SHOWCASE_MONTH_CEILING = 2.50


async def _opening_allowance(session, user) -> None:
    """Ограничитель витрины: считает абзацы, а не доллары.

    Отдельный от месячного потолка намеренно — см. довод на месте вызова.
    Отказ здесь выглядит для клиента так же, как любая другая причина не
    написать абзац: цена показывается, начала нет. Это последняя линия и она
    срабатывать не должна; если сработала — в логе видно, у кого.

    Порядок «прибавить, потом сравнить» тут был с самого начала и был верным;
    менялось только то, чем прибавляли. Раньше — `get` → `+= 1` → `flush`, то
    есть три шага с окном между первым и третьим: восемь воркеров, каждый со
    своим нулём в руках, проходили шестидесятый абзац восемь раз. Теперь один
    запрос, и второй видит своё же увеличение.
    """
    # **Месяц по UTC, а не по часам машины.** Здесь стояло `date.today()` —
    # единственное место всей бухгалтерии, считавшее по местному времени;
    # `_period_start`, `cost.month_bounds` и `counters.add` берут
    # `datetime.now(timezone.utc)`. На сервере в UTC это совпадает и потому
    # прожило незамеченным, но совпадение — не свойство: на машине в другом
    # поясе окно витрины открывалось бы и закрывалось на несколько часов
    # раньше остальных счётчиков, и в сутки смены месяца абзацы легли бы в
    # строку другого месяца, чем деньги за них.
    month = datetime.now(timezone.utc).date().replace(day=1)
    try:
        await counters.spend_and_check(
            session,
            user_id=user.id,
            day=month,
            metric=OPENING_METRIC,
            limit=OPENING_ALLOWANCE,
        )
    except counters.QuotaExceeded as exc:
        log.warning(
            "opening allowance spent by %s: %s in %s",
            user.id, exc.spent, month.isoformat(),
        )
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "opening_allowance"},
        ) from exc


async def _guard_month(
    session, user, *, tier: str, projected: float, locale: str = "en"
) -> None:
    """Refuse a generation this account can no longer afford this month.

    Deliberately a different error from the question counter even though both
    are 429s. One means "you have used your turns and they come back"; this
    one means "we have spent what this tier is worth". A client that showed
    the same sentence for both would tell a subscriber with sixty turns left
    to come back tomorrow, and would tell a free user who has spent nothing
    that they are out of questions.
    """
    try:
        await cost.guard_month(session, user, tier=tier, projected=projected)
    except cost.BudgetExceeded as exc:
        log.error("month ledger refused %s (%s tier): %s", user.id, tier, exc)
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            # Ни себестоимости, ни потолка наружу: они для лога выше.
            detail={
                "error": "month_budget",
                "message": i18n_replies.reply("budget_exceeded", locale),
                "tier": tier,
            },
        ) from exc


# ── what a call is about to cost ───────────────────────────────────────────
#
# `writer.write` and `conversation.answer` each run `cost.guard` against the
# per-call ceiling and neither hands the figure back, so the month ledger —
# which must be consulted *before* the call, or it is a receipt rather than a
# ceiling — cannot borrow it. These two rebuild the same prompt out of the
# same public pieces and ask `cost.estimate` the same question, so both guards
# agree about what a call is expected to cost.
#
# That makes this the only code in the router that knows how those two
# functions assemble a prompt, and the duplication is real. It is checked
# rather than trusted: `test_readings_budget.py` measures every free chapter
# of every system through these helpers against the free ceiling, so a prompt
# that grows past the ceiling fails in CI instead of at a reader.

#: `conversation.answer`'s own output ceiling for one chat turn.
CHAT_MAX_TOKENS = 1200


def _chapter_projection(
    result: CalcResult,
    chapter: chapter_defs.Chapter,
    *,
    model: str,
    locale: str,
    memory: list[str] | None,
) -> float:
    offered = chapter_defs.relevant_factors(chapter, result.factors)
    # The locale is passed here for the same reason the model gets it: the
    # chapter's title and question are in the prompt in the reader's language,
    # and a projection built from the English prompt would be measuring a
    # different string than the one `writer.write` is about to send.
    prompt = writer.build_prompt(result, chapter, offered=offered, locale=locale)
    system = voice.system_prompt(locale=locale, paid=not chapter.free, memory=memory)
    return cost.estimate(
        model,
        prompt_chars=len(prompt) + len(system),
        # `writer.write`'s own formula. A chapter is allowed three tokens a
        # word plus room for the JSON scaffolding around it.
        max_output_tokens=min(4096, chapter.words[1] * 3 + 600),
    )


def _spheres_projection(result: CalcResult, *, model: str, locale: str) -> float:
    """Во что обойдётся превью пяти сфер — тем же способом, что и глава.

    Считается из тех же кусков, что соберёт `spheres.write`: его собственный
    промт, тот же системный блок и тот же стартовый потолок вывода. Отдельная
    функция, а не `_chapter_projection`, потому что у сфер нет `Chapter` — ни
    вопроса, ни числа слов, — и подстановка «какой-нибудь главы» вместо них
    измеряла бы не ту строку, которую мы собираемся отправить.
    """
    from ...ai import spheres as spheres_module

    prompt = spheres_module.build_prompt(result, locale=locale)
    system = voice.system_prompt(locale=locale, paid=False)
    latin = i18n.resolve(locale) in ("en", "es", "de", "it", "fr", "pt-BR")
    return cost.estimate(
        model,
        prompt_chars=len(prompt) + len(system),
        # Стартовый потолок `spheres.write`, а не `MAX_TOKENS`: выше него он
        # поднимается только через `affordable_output`, то есть ровно в те
        # деньги, которые уже разрешил потолок вызова. Проекция обязана
        # называть ожидаемую цену, а не худшую из мыслимых, иначе месячная
        # стена встаёт перед человеком, который до неё не дошёл.
        max_output_tokens=2600 if latin else spheres_module.MAX_TOKENS,
    )


def _chat_projection(
    *,
    question: str,
    results: list[CalcResult],
    history: list[tuple[str, str]],
    model: str,
    locale: str,
    paid: bool,
    memory: list[str] | None,
) -> float:
    prompt = conversation.build_prompt(question=question, results=results, history=history)
    # `conversation=True`, exactly as the turn itself will be generated: the
    # chat language block is longer than the chapter one, and a projection that
    # prices the wrong block under-reports the ceiling it exists to enforce.
    system = (
        voice.system_prompt(locale=locale, paid=paid, memory=memory, conversation=True)
        + "\n\n"
        + conversation.CHAT_RULES
    )
    return cost.estimate(
        model, prompt_chars=len(prompt) + len(system), max_output_tokens=CHAT_MAX_TOKENS
    )


# ── chat ───────────────────────────────────────────────────────────────────


@router.get("/natal/spheres")
async def natal_spheres(
    user: CurrentUser,
    provider: ProviderDep,
    _released: SessionReleased,
    locale: str = Query(default="en", max_length=i18n.MAX_TAG),
    profile_id: str | None = Query(default=None),
) -> dict:
    """The free preview of the natal chart: five spheres, two sentences each.

    Free for everybody and written once per chart per language, on the cheap
    model, cached in the `reading` table like everything else — the shop
    window for the sixteen chapters, shaped after the reference the owner
    chose: wheel, placements, then short interpretations per sphere with the
    full reading behind the price.

    Each block carries the slug of the chapter that finishes the thought and
    the sphere's localised title, read from the same `i18n.chapter_words`
    table the chapter list uses, so the two screens can never disagree about
    what a sphere is called.

    Разрезан так же, как глава, и по той же причине: экран натальной карты —
    первый, который видит новый человек, и генерация здесь идёт на каждого.
    """
    from ...ai import spheres as spheres_module

    language = i18n.resolve(locale)

    def _titled(blocks: list[dict]) -> list[dict]:
        out = []
        for block in blocks:
            words = i18n.chapter_words("natal", block["chapter"], locale=language)
            out.append({**block, "title": words.title})
        return out

    async with session_scope() as session:
        birth = await resolve_birth(session, user, profile_id=profile_id, birth=None)

    result = await _calc("natal", birth, house_system="placidus")
    # The same identity rule a chapter's key follows: the birth and the whole
    # factor list. The natal chart does not move, so this is stable per person
    # per house system — and if the engine gains a factor, the preview
    # genuinely has something new to say and is written again.
    calc_key = cache_key(
        "natal", birth, chapter="spheres",
        factors="|".join(result.factors), house_system="placidus",
    )

    async with session_scope() as session:
        stored = await _stored_reading(
            session, user_id=user.id, system="natal", chapter="spheres",
            calc_key=calc_key, locale=language,
        )
        if stored is not None:
            return {
                "spheres": _titled(stored.body.get("spheres", [])),
                "cached": True,
                "locale": language,
            }

    # The same race the chapter route had: the natal screen and a fast reload
    # can both arrive before the first write lands. One waits; the other pays.
    lock_key = f"{user.id}:natal:spheres:{calc_key}:{language}"
    try:
        async with _write_lock(lock_key):
            # ── чтения перед моделью ───────────────────────────────────────
            async with session_scope() as session:
                again = await _stored_reading(
                    session, user_id=user.id, system="natal", chapter="spheres",
                    calc_key=calc_key, locale=language,
                )
                if again is not None:
                    return {
                        "spheres": _titled(again.body.get("spheres", [])),
                        "cached": True,
                        "locale": language,
                    }

                # Превью уже написано на другом языке — переводится, не
                # пишется. Заголовки сфер сюда не ездят: они приходят из
                # `i18n.chapter_words` при отдаче (`_titled`) и переведены
                # руками владельца, а не моделью.
                sphere_source = await _translation_source(
                    session, user_id=user.id, system="natal",
                    chapter="spheres", calc_key=calc_key,
                    exclude_locale=language,
                )
                sphere_snapshot = (
                    (
                        dict(sphere_source.body), sphere_source.locale,
                        list(sphere_source.cited_factors),
                        sphere_source.profile_id, sphere_source.engine_version,
                    )
                    if sphere_source is not None
                    else None
                )

                # The mid model, and the cheap one is gone from here: measured on
                # the owner's own first run, the cheap model burned all three
                # attempts on rules it was told about («ты был», an invented
                # factor, «ты должен») and the natal screen said Alma is silent.
                # Three failed cheap generations cost more than one good mid one.
                _cheap, mid, _strong = models()

                # **Тот же месячный гейт, что у любой другой генерации.**
                #
                # Здесь его не было вовсе, и это единственная генерация продукта,
                # которая жила мимо `guard_month`. Расход она при этом честно
                # записывала (`_spend` ниже), так что превью сфер тратило общий
                # месячный потолок и само же в него не упиралось — оно только
                # приближало стену, за которой откажут *другим* экранам.
                #
                # Дыра открывается правкой даты рождения: `calc_key` включает весь
                # список факторов, поэтому каждая новая дата — новое превью и новая
                # генерация, сколько угодно раз подряд. Бесплатность сфер это не
                # отменяет: потолок тира и есть форма, в которой «бесплатно» здесь
                # записано, — и кэш выше проверен раньше, так что уже написанное
                # превью открывается и в месяц, потраченный до копейки.
                await _guard_month(
                    session,
                    user,
                    tier=await entitlements.tier_of(session, user),
                    locale=language,
                    # По цене того, что будет сделано: перевод при исходнике,
                    # генерация без него — как у главы в `_read_or_write`.
                    projected=(
                        _translation_projection(sphere_snapshot[0], locale=language)
                        if sphere_snapshot is not None
                        else _spheres_projection(result, model=mid, locale=language)
                    ),
                )
                profile_row_id = await _profile_id(session, user)

            if sphere_snapshot is not None:
                src_body, src_locale, src_cited, src_profile, src_engine = sphere_snapshot
                translated = await _translated_body(
                    user, provider,
                    body=src_body,
                    pieces=translator.spheres_pieces,
                    source_locale=src_locale,
                    target_locale=language,
                    paid=False,
                    factors=src_cited,
                )
                if translated is not None:
                    t_body, t_spend, t_model = translated
                    async with session_scope() as session:
                        record = Reading(
                            user_id=user.id,
                            profile_id=src_profile,
                            system="natal",
                            chapter="spheres",
                            locale=language,
                            calc_key=calc_key,
                            engine_version=src_engine,
                            model=t_model,
                            body=t_body,
                            cited_factors=src_cited,
                            input_tokens=t_spend.input_tokens,
                            output_tokens=t_spend.output_tokens,
                            cost_cents=t_spend.cents,
                        )
                        session.add(record)
                        await _count(session, user, "spheres_translated")
                        await _spend(session, user, t_spend.cents)
                        try:
                            await session.flush()
                        except IntegrityError:
                            await session.rollback()
                            log.warning(
                                "lost the spheres translation race — returning "
                                "the stored copy"
                            )
                            await _spend(session, user, t_spend.cents)
                            await session.flush()
                            theirs = await _stored_reading(
                                session, user_id=user.id, system="natal",
                                chapter="spheres", calc_key=calc_key,
                                locale=language,
                            )
                            if theirs is not None:
                                return {
                                    "spheres": _titled(theirs.body.get("spheres", [])),
                                    "cached": True,
                                    "locale": language,
                                }
                            raise
                    return {
                        "spheres": _titled(t_body.get("spheres", [])),
                        "cached": False,
                        "locale": language,
                    }
                # Перевод сорвался — генерация ниже; её потолок был спрошен по
                # цене перевода, спрашивается заново по своей.
                async with session_scope() as session:
                    await _guard_month(
                        session,
                        user,
                        tier=await entitlements.tier_of(session, user),
                        locale=language,
                        projected=_spheres_projection(result, model=mid, locale=language),
                    )

            try:
                blocks, spend = await spheres_module.write(
                    result, provider=provider(), model=mid, locale=language
                )
            except (writer.ReadingRefused, cost.BudgetExceeded) as exc:
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"error": "ai_unavailable", "message": str(exc)},
                ) from exc

            # ── запись превью ─────────────────────────────────────────────
            async with session_scope() as session:
                record = Reading(
                    user_id=user.id,
                    profile_id=profile_row_id,
                    system="natal",
                    chapter="spheres",
                    locale=language,
                    calc_key=calc_key,
                    engine_version=result.engine_version,
                    model=mid,
                    body={"spheres": blocks},
                    cited_factors=sorted({f for b in blocks for f in b["factors"]}),
                    input_tokens=spend.input_tokens,
                    output_tokens=spend.output_tokens,
                    cost_cents=spend.cents,
                )
                session.add(record)
                await _spend(session, user, spend.cents)
                try:
                    await session.flush()
                except IntegrityError:
                    await session.rollback()
                    log.warning("lost the spheres race — returning the stored copy")
                    await _spend(session, user, spend.cents)
                    await session.flush()
                    theirs = await _stored_reading(
                        session, user_id=user.id, system="natal", chapter="spheres",
                        calc_key=calc_key, locale=language,
                    )
                    if theirs is not None:
                        return {
                            "spheres": _titled(theirs.body.get("spheres", [])),
                            "cached": True,
                            "locale": language,
                        }
                    raise

            return {"spheres": _titled(blocks), "cached": False, "locale": language}
    finally:
        _prune_lock(lock_key)


async def _translated_titles(
    user, provider, rows: list[tuple[str, str | None, dict]], language: str
) -> dict[str, str]:
    """Заголовки бесед на языке приложения: `{thread_id: title}`.

    Заголовок — первые слова первого вопроса, и язык у него тот, на котором
    вопрос был задан. Кеш — `ChatThread.title_translations`, написано раз —
    живёт вечно; новый тред при создании сеет туда свой собственный язык,
    так что беседа, начатая на языке приложения, сюда не ездит вовсе.
    """
    out: dict[str, str] = {}
    need: list[tuple[str, str]] = []
    for tid, title, translations in rows:
        if not title:
            continue
        if language in translations:
            out[tid] = translations[language]
        else:
            need.append((tid, title))
    if not need:
        return out

    cheap, _mid, _strong = models()
    chars = sum(len(t) for _, t in need)
    projected = cost.at_measured_rate(
        cost.estimate(
            cheap, prompt_chars=chars + 900,
            max_output_tokens=translator.allowance(chars, target_locale=language),
        ),
        "translation",
    )
    # Из статьи показа, как и реплики, — довод у `_showcase_room`. Отказ тих:
    # заголовки уезжают как записаны, список бесед показывается.
    if not await _showcase_room(user, projected):
        return out

    # Теми же пачками, что и реплики: у аккаунта с сотнями бесед один вызов
    # на всё упёрся бы в потолок вызова, и не перевёлся бы ни один заголовок.
    for piece in _batched(need, cap=CHAT_BATCH_CHARS):
        try:
            done = await translator.translate(
                [title for _, title in piece],
                provider=provider(), model=cheap,
                source_locale=None, target_locale=language, paid=False,
            )
        except translator.TranslationRefused as exc:
            if exc.spend.cents:
                await _charge_anyway(
                    user, cents=exc.spend.cents, ledger=cost.SHOWCASE_METRIC
                )
            log.warning("a batch of thread titles stays untranslated: %s", exc)
            continue
        except (cost.BudgetExceeded, ModelUnavailable) as exc:
            log.warning("a batch of thread titles stays untranslated: %s", exc)
            continue

        async with session_scope() as session:
            await _spend(
                session, user, done.spend.cents, ledger=cost.SHOWCASE_METRIC
            )
            await _count(session, user, "chat_titles_translated", len(piece))
            for (tid, _), text in zip(piece, done.segments):
                row = await session.get(ChatThread, tid)
                if row is not None and row.user_id == user.id:
                    stamped = dict(row.title_translations or {})
                    stamped[language] = text
                    row.title_translations = stamped
                out[tid] = text
    return out


def _batched(
    pairs: list[tuple[str, str]], cap: int = translator.MAX_SEGMENT_CHARS
) -> list[list[tuple[str, str]]]:
    """Пары `(id, текст)` пачками, влезающими в один вызов перевода.

    Тред в сотню реплик одним промптом упёрся бы в потолок вызова, и перевод,
    отвергнутый целиком из-за длины, не перевёл бы ничего.
    """
    batches: list[list[tuple[str, str]]] = []
    batch: list[tuple[str, str]] = []
    size = 0
    for key, text in pairs:
        if batch and size + len(text) > cap:
            batches.append(batch)
            batch, size = [], 0
        batch.append((key, text))
        size += len(text)
    if batch:
        batches.append(batch)
    return batches


#: Пачка перевода беседы — втрое меньше общей. Ответ ручки треда ждётся
#: клиентом 30 секунд (`normalTimeout`), а пачка в 8 000 знаков — это до
#: ~6 000 токенов кириллицы на выходе: **одна** такая пачка на медленной
#: минуте съедает весь таймаут. Три тысячи знаков держат вызов в считанных
#: секундах и позволяют бюджету ниже остановиться между пачками вовремя.
CHAT_BATCH_CHARS = 3_000

#: Стенной бюджет одного запроса на перевод беседы, в секундах. Клиент ждёт
#: 30; ответ обязан выехать раньше, каким бы длинным ни был архив.
#: Непереведённый остаток уезжает как записан и доводится кешем на следующих
#: открытиях — пачки идут от свежих реплик к старым, так что первым
#: переводится то, к чему экран прокручен.
CHAT_TRANSLATION_BUDGET_SECONDS = 18.0


async def _showcase_room(user, projected: float) -> bool:
    """Есть ли у статьи показа месяц на этот перевод беседы.

    Переводы архива платят из витринной статьи (`SHOWCASE_METRIC`), а не из
    той, что читает `guard_month`, — по той же причине, по которой туда
    переехал открывающий абзац: чтение собственного архива не должно съедать
    бюджет, из которого отвечают на настоящие вопросы (витрина в $1.28 уже
    съедала месяц бесплатного тира в $1.10 целиком — замер у
    `SHOWCASE_METRIC`). Потолок статьи общий — `SHOWCASE_MONTH_CEILING`.
    Отказ тих: реплики уезжают как записаны, беседа читается.
    """
    async with session_scope() as session:
        shown = await cost.month_showcase_spend(session, user)
    if shown + projected > SHOWCASE_MONTH_CEILING:
        log.warning(
            "chat translation refused by the showcase ceiling for %s "
            "(%.2f + %.4f > %.2f)", user.id, shown, projected,
            SHOWCASE_MONTH_CEILING,
        )
        return False
    return True


async def _cache_chat_batch(
    user,
    language: str,
    entries: list[tuple[str, str]],
    *,
    model: str | None,
    total_cents: float,
    counter: str,
) -> None:
    """Строки кеша переводов + счёт, savepoint на строку.

    Savepoint, а не общий flush: гонка двух воркеров над одним тредом —
    законный случай, и общий rollback выбрасывал бы вместе с проигравшей
    строкой все соседние переводы пачки — оплаченные и уже отданные, но не
    легшие в кеш; следующий заход платил бы за них второй раз.
    """
    async with session_scope() as session:
        if total_cents:
            await _spend(session, user, total_cents, ledger=cost.SHOWCASE_METRIC)
        await _count(session, user, counter, len(entries))
        for mid, text in entries:
            try:
                async with session.begin_nested():
                    session.add(
                        ChatTranslation(
                            message_id=mid,
                            locale=language,
                            body=text,
                            model=model,
                            cost_cents=total_cents / len(entries),
                        )
                    )
                    await session.flush()
            except IntegrityError:
                # Другой воркер успел первым — его строка уже в кеше.
                pass


async def _translated_chat_bodies(
    user, provider, rows: list[tuple[str, str, str | None]], language: str
) -> dict[str, str]:
    """Тела реплик на языке приложения: `{message_id: body}`.

    Правило владельца от 28.08.2026: при смене языка на экране не остаётся ни
    строки на старом — включая архив беседы и **включая собственные вопросы
    человека**: тред читается целиком на одном языке. Исходники при этом не
    трогаются (`ChatTranslation` лежит рядом), так что возврат на прежний язык
    бесплатен и мгновенен.

    Любой сбой — месячный потолок, молчащий провайдер, отвергнутый перевод —
    отдаёт реплику как есть: беседа на старом языке лучше, чем 404 вместо
    беседы.
    """
    out: dict[str, str] = {}
    need: list[tuple[str, str]] = []
    ids = [mid for mid, _, _ in rows]
    if not ids:
        return out

    ready: dict[str, str] = {}
    async with session_scope() as session:
        # Пачками по 500: у живого треда идентификаторов сотни, а у SQLite —
        # потолок в 999 параметров на один запрос.
        for start in range(0, len(ids), 500):
            cached = (
                await session.execute(
                    select(ChatTranslation).where(
                        ChatTranslation.message_id.in_(ids[start:start + 500]),
                        ChatTranslation.locale == language,
                    )
                )
            ).scalars().all()
            ready.update({c.message_id: c.body for c in cached})

    for mid, body, loc in rows:
        if loc is not None and i18n.resolve(loc) == language:
            out[mid] = body
        elif mid in ready:
            out[mid] = ready[mid]
        elif body.strip():
            # Null-локаль (реплики до колонки) переводится наравне с чужой:
            # язык старой строки не восстановить, а модель, которой велено
            # вернуть уже-целевой текст без изменений, делает ровно это, и
            # ответ ложится в кеш — второй раз этот вопрос не задаётся.
            need.append((mid, body))
        else:
            out[mid] = body
    if not need:
        return out
    # Свежие раньше старых: бюджет времени ниже может не дать перевести всё,
    # и перевестись первым обязано то, что человек видит первым, — хвост
    # беседы, к которому экран прокручен.
    need.reverse()

    cheap, _mid, _strong = models()
    chars = sum(len(b) for _, b in need)
    projected = cost.at_measured_rate(
        cost.estimate(
            cheap, prompt_chars=chars + 900,
            max_output_tokens=translator.allowance(chars, target_locale=language),
        ),
        "translation",
    )
    if not await _showcase_room(user, projected):
        return out

    batches = _batched(need, cap=CHAT_BATCH_CHARS)
    started = time.monotonic()
    for index, piece in enumerate(batches):
        if time.monotonic() - started > CHAT_TRANSLATION_BUDGET_SECONDS:
            # Бюджет времени истрачен — остаток уезжает как записан. Клиент
            # ждёт ответа 30 секунд, и архив, переведённый целиком, но после
            # таймаута, — это экран ошибки, а не перевод. Кеш прогревается с
            # каждым открытием: следующий заход начнёт с остатка.
            log.info(
                "chat translation budget spent — %d messages wait for the "
                "next open",
                sum(len(rest) for rest in batches[index:]),
            )
            break
        try:
            done = await translator.translate(
                [body for _, body in piece],
                provider=provider(), model=cheap,
                source_locale=None, target_locale=language, paid=False,
            )
        except translator.TranslationRefused as exc:
            if exc.spend.cents:
                await _charge_anyway(
                    user, cents=exc.spend.cents, ledger=cost.SHOWCASE_METRIC
                )
            # Отказ **кешируется** — исходным текстом. Отказ детерминирован
            # (та же пачка — тот же ответ), и без записи каждый показ треда
            # платил бы за те же две неудачные попытки вечно; с записью
            # реплика честно остаётся как была, бесплатно. Появится лучший
            # переводчик — строки с `chat_translation_given_up` в счётчике
            # видно, и кеш чистится миграцией.
            await _cache_chat_batch(
                user, language, list(piece),
                model=None, total_cents=0.0,
                counter="chat_translation_given_up",
            )
            log.warning("a chat batch stays untranslated for good: %s", exc)
            continue
        except (cost.BudgetExceeded, ModelUnavailable) as exc:
            # Преходящие причины: молчащий провайдер вернётся, потолок вызова
            # у другой пачки другой. Без кеша — попробуем в следующий раз.
            log.warning("a chat batch stays untranslated: %s", exc)
            continue

        translated = list(zip((mid for mid, _ in piece), done.segments))
        for mid, text in translated:
            out[mid] = text
        await _cache_chat_batch(
            user, language, translated,
            model=done.model, total_cents=done.spend.cents,
            counter="chat_translated",
        )
    return out


def _relocalised_chapter(source_chapter: dict | None, language: str) -> dict | None:
    """`source_chapter` с заголовком на языке запроса — из каталога, не модели.

    Заголовок в строке переведён на язык того хода, в котором ответ родился
    (см. довод у колонки). При отдаче на другом языке он подменяется словом из
    `i18n.chapter_words` — тем же, каким называется сама глава, — а незнакомый
    слаг оставляет как есть: старая карточка лучше пустой.
    """
    if not source_chapter:
        return source_chapter
    try:
        words = i18n.chapter_words(
            source_chapter.get("system", ""),
            source_chapter.get("slug", ""),
            locale=language,
        )
    except Exception:
        return source_chapter
    title = getattr(words, "title", None)
    if not title:
        return source_chapter
    return {**source_chapter, "title": title}


@router.get("/chat/threads")
async def threads(
    user: CurrentUser,
    provider: ProviderDep,
    _released: SessionReleased,
    #: Язык приложения. Без него — поведение до 28.08.2026: заголовки как
    #: записаны. С ним список бесед читается целиком на языке приложения.
    locale: str | None = Query(default=None, max_length=i18n.MAX_TAG),
) -> dict:
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(ChatThread)
                .where(ChatThread.user_id == user.id)
                .order_by(ChatThread.updated_at.desc())
            )
        ).scalars().all()
        listed = [
            {"id": t.id, "title": t.title, "updated_at": t.updated_at.isoformat()}
            for t in rows
        ]
        stamped = [(t.id, t.title, dict(t.title_translations or {})) for t in rows]

    if locale is not None:
        language = i18n.resolve(locale)
        titles = await _translated_titles(user, provider, stamped, language)
        for row in listed:
            row["title"] = titles.get(row["id"], row["title"])
    return {"threads": listed}


@router.get("/chat/threads/{thread_id}")
async def thread(
    thread_id: str,
    user: CurrentUser,
    provider: ProviderDep,
    _released: SessionReleased,
    locale: str | None = Query(default=None, max_length=i18n.MAX_TAG),
) -> dict:
    # `SessionReleased`, а не `SessionDep`: при переводе между чтением и
    # записью лежит вызов модели, и держать соединение через него — ровно та
    # болезнь, от которой разрезаны все пути генерации в этом файле.
    async with session_scope() as session:
        row = await session.get(ChatThread, thread_id)
        if row is None or row.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no such conversation")

        messages = (
            await session.execute(
                select(ChatMessage)
                .where(ChatMessage.thread_id == thread_id)
                .order_by(ChatMessage.created_at)
            )
        ).scalars().all()
        title = row.title
        title_translations = dict(row.title_translations or {})
        listed = [
            {
                "id": m.id,
                "role": m.role,
                "body": m.body,
                "cited_factors": m.cited_factors,
                # Null for every turn written before the column existed, which
                # is exactly what the clients' legacy branch is for: no kind on
                # the wire means no label on the screen, which is quiet and
                # honest rather than a guess about a conversation nobody can
                # re-derive.
                "turn_kind": m.turn_kind,
                # Под тем же именем и в той же форме, что у живого `/v1/chat`,
                # — иначе у клиента два разбора одного поля и они разойдутся в
                # тот день, когда правят один. Null на всём, что главу назвать
                # не могло, и на всём, что написано до колонки.
                "source_chapter": m.source_chapter,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
        raw = [(m.id, m.body, m.locale) for m in messages]

    if locale is not None:
        language = i18n.resolve(locale)
        bodies = await _translated_chat_bodies(user, provider, raw, language)
        for item in listed:
            item["body"] = bodies.get(item["id"], item["body"])
            item["source_chapter"] = _relocalised_chapter(
                item["source_chapter"], language
            )
        titles = await _translated_titles(
            user, provider, [(thread_id, title, title_translations)], language
        )
        title = titles.get(thread_id, title)

    return {
        "id": thread_id,
        "title": title,
        "messages": listed,
    }


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    user: CurrentUser,
    provider: ProviderDep,
    _released: SessionReleased,
) -> dict:
    """One turn of conversation, answered only from the chart."""
    # Тело живёт в `_chat_turn`, потому что у хода беседы теперь два входа:
    # этот — старый контракт, один JSON после долгого молчания — и
    # `/chat/stream`, где те же шаги рассказываются по мере работы. Логика
    # одна на двоих намеренно: отдельная копия для стрима — это дыра мимо
    # квоты ровно в тот день, когда правят одну из копий.
    #
    # Передаётся идентификатор, а не строка пользователя: у хода теперь три
    # своих транзакции, и `User`, загруженный в чужой сессии, — ровно то, что
    # тянет за собой закрытую транзакцию. `/chat/stream` делал так и раньше.
    return await _chat_turn(payload, user.id, provider)


async def _chat_gate(session, user, *, locale: str, message: str = "") -> tuple[Allowance, str]:
    """Какая порция отвечает этому человеку сейчас — или честный 429.

    Вынесено из тела хода, потому что спрашивающих двое: сам `_chat_turn` и
    `/chat/stream`, которому отказ нужен **до первого байта** — SSE-ответ уже
    несёт 200, и квота, проверенная только внутри потока, превращала бы отказ
    в «ошибку внутри успешного ответа». Ничего не тратит: списание было и
    остаётся после состоявшегося ответа, поэтому второй заход этой проверки
    в одном запросе безвреден.

    `message` — только ради кризисной ветки, и она стоит стены. Человеку,
    написавшему, что он может себе навредить, ответ не генерируется вовсе
    (`validator.crisis` → `conversation.answer`): модель не зовут, токены не
    тратятся, деньги не двигаются. Дать такому сообщению упереться в «вопросы
    на сегодня кончились» значит показать счётчик тому, кто написал самое
    важное, что он тут напишет, — и показать его за фразу, которая ничего не
    стоит. Стена остаётся ровно там, где есть что ограничивать.
    """
    _cheap, mid, strong = models()
    tier = await entitlements.tier_of(session, user)
    # **Сегодня это всегда False, и оставлено оно намеренно.** Недельная
    # подписка снята с продажи вместе со всей прежней полкой (ТЗ §2), кинда
    # `weekly` больше нет ни в каталоге, ни в `EntitlementKind`, ни одной такой
    # строки в базе нет. Механизм порции по недельному сроку не выпилен, потому
    # что ТЗ §8 прямо оставляет неделю как возможный A/B после данных по
    # удержанию, а восстанавливать снесённую квоту под давлением эксперимента —
    # это как раз тот случай, когда её делают «примерно как было».
    weekly = await entitlements.has_kind(session, user, "weekly")
    allowance = _allowance(tier, mid=mid, locale=locale, weekly=weekly)

    # An owner spends the bundle their purchase included; when it is gone the
    # base allowance is the wall, and the wall's own sentence points at the
    # plan. A free account spends its one welcome question the same way.
    if tier == "owner":
        bundle = _bundle(strong=strong)
        if await _asked(session, user, bundle) < bundle.limit:
            allowance = bundle
    elif tier == "free":
        # The first conversation anybody has, on the model that can carry it.
        # Same fallback shape as the owner's bundle and for the same reason:
        # running out must not end the conversation, only quieten it.
        welcome = _welcome(mid=mid)
        if await _asked(session, user, welcome) < welcome.limit:
            allowance = welcome

    asked = await _asked(session, user, allowance)
    if asked >= allowance.limit and not validator.crisis(message):
        # Localised, first person, and it ends on what the reader can still
        # have. The English fragment this replaces — "that is 3 questions
        # today. They come back tomorrow — a subscription raises the limit." —
        # was untranslated, lowercase-first, and named only what was being
        # withheld. It landed, measured, on somebody asking what a word she had
        # just used about them meant, which reframes the subscription as the
        # price of being understood rather than the price of more.
        #
        # Rejected, and worth writing down because it is the obvious idea: not
        # counting a turn whose cited factors are a subset of the previous
        # turn's, so that "what does fixed mean" is a continuation rather than a
        # new question. It makes the daily limit bypassable by asking about the
        # same placement for ever — `test_the_free_question_limit_is_real`
        # fails on it directly — and a rule whose effect is "the limit applies
        # unless you stay on one planet" is not a rule anybody can explain.
        #
        # **The half of the taxonomy that is still not implemented, and why.**
        # An aside is free once the turn has been generated, but this gate runs
        # before generation and cannot know what kind of turn it would have
        # been. So greeting her is free only while you still have questions,
        # and the wall lands on the friendliest message in the thread —
        # measured on "sorry, that came out wrong. can we just talk?".
        #
        # The fix would be a small free-aside budget, and it does not fit. One
        # chartless aside a day on the cheapest model, capped at 250 output
        # tokens, is $0.0036 a turn and $0.108 a month; the free tier's heaviest
        # honest month already prices at $1.033 against a $1.10 ceiling, so
        # there is $0.067 of room and this needs $0.108 of it.
        # `test_no_tier_is_promised_more_than_its_ceiling_can_fund` would fail,
        # correctly. Letting the turn through and refusing it afterwards if it
        # turns out to be a reading costs the same money and adds a second wall.
        # What is affordable is this sentence: hers, in their language, ending
        # on the eight systems that stay free. Prompt caching is what buys the
        # free aside — the system block is byte-identical across every turn of
        # every conversation — and neither `ai/provider.py` nor `ai/cost.py`
        # models a cached read yet.
        message = i18n_replies.reply(
            f"question_limit.{allowance.period}",
            locale,
            limit=allowance.limit,
        )
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "question_limit",
                "message": message,
                "asked": asked,
                "allowance": allowance.limit,
                "period": allowance.period,
            },
        )
    return allowance, tier


#: Дом в строке фактора — ровно то, что печатает движок:
#: «sun 17°46′ ♓ · house 4» (`engine/natal.py::describe`).
_FACTOR_HOUSE = re.compile(r"\bhouse (\d{1,2})\b")
#: Движущееся тело транзита: «transiting saturn □ natal sun · orb …»
#: (`engine/transits.py::describe`).
_FACTOR_TRANSITING = re.compile(r"^transiting ([a-z_]+)")


def _stage_for(system: str, result: CalcResult) -> tuple[str, str] | None:
    """Что назвать вслух про этот шаг сборки карты — из настоящих данных.

    Спека беседы (§6, A2): «reading your …» показывается только с настоящими
    данными запроса; правдоподобный «четвёртый дом» здесь был бы враньём ровно
    там, где продукт обещает не выдумывать. Поэтому имя берётся из факторов
    только что посчитанной системы — дом из натальной карты этого человека,
    движущееся тело из его же первого транзита, — а если в факторах нет ни
    дома, ни тела (рождение без времени), шаг честно молчит. Сырые имена
    движка («4», «saturn») переводит клиент словами своего каталога — так же,
    как переводит цитаты.
    """
    if system == "natal":
        for factor in result.factors:
            found = _FACTOR_HOUSE.search(factor)
            if found:
                return "house", found.group(1)
    if system == "transits":
        for factor in result.factors:
            found = _FACTOR_TRANSITING.match(factor)
            if found:
                return "body", found.group(1)
    return None


async def _chat_turn(
    payload: ChatRequest,
    user_id: str,
    provider,
    *,
    stage: Callable[[str, str], Awaitable[None]] | None = None,
) -> dict:
    """Один ход беседы — под замком аккаунта.

    Тело хода живёт в `_answer_one_turn`; здесь только то, без чего оно
    считается неверно при двух одновременных отправках. См. `_chat_slot`:
    и порция вопросов, и месячный потолок — это «прочитал, сравнил, много
    позже записал», и два хода, идущие рядом, читают один и тот же ноль.

    Коммит стоит **внутри замка**, и это то же требование, что и было, просто
    записанное иначе. Раньше здесь стоял явный `session.commit()`, потому что
    сессия жила весь запрос и её коммитила зависимость — уже без замка, — и
    следующий ход читал бы счётчик, не видя чужой незафиксированной записи.
    Теперь пишущий `session_scope` внутри `_answer_one_turn` коммитит сам и
    делает это, не выходя отсюда, так что замок по-прежнему сторожит число, а
    не только порядок.
    """
    async with _chat_slot(user_id):
        return await _answer_one_turn(payload, user_id, provider, stage=stage)


async def _answer_one_turn(
    payload: ChatRequest,
    user_id: str,
    provider,
    *,
    stage: Callable[[str, str], Awaitable[None]] | None = None,
) -> dict:
    """Один ход беседы: квота, карта, модель, счёт — и готовый ответ.

    `stage` — рассказчик стрима: его зовут на настоящих шагах подготовки
    (см. `_stage_for`), и когда его нет, ход ведёт себя ровно как всегда.

    Зовётся только из `_chat_turn`, под замком аккаунта: всё, что здесь
    прочитано из счётчиков, обязано оставаться правдой до самой записи.

    **Три транзакции и восемь расчётов между ними.** Первая читает всё, что
    нужно модели, — квоту, рождение, партнёра, историю треда, воспоминания,
    список написанных глав. Затем восемь систем считаются без базы: транзиты
    одни стоят 1.35 секунды скана, и держать ради них соединение было чистым
    убытком. Вторая транзакция спрашивает месячный потолок — ей нужна проекция,
    а проекции нужны посчитанные системы. Третья пишет вопрос, ответ, счётчик и
    расход, и она же коммитит их одним куском.

    **Вопрос человека пишется в третьей, а не в первой**, и это не мелочь:
    вопрос без ответа хуже, чем ничего, — правило, которое до разреза держал
    откат в `_charge_anyway`. Теперь его держит порядок: если генерация не
    состоялась, в треде не появляется ни строки. На то, что видит модель, это
    не влияет — `history` и раньше собиралась **до** вставки вопроса.
    """
    # ── 1. всё, что нужно прочитать до модели ─────────────────────────────
    async with session_scope() as session:
        user = await session.get(User, user_id)
        if user is None:
            # Аккаунт удалён между проверкой токена и этой строкой. Раньше эта
            # ветка жила только в `/chat/stream`, где сессия запроса умирала
            # раньше генератора; теперь у обоих входов транзакция своя, и
            # проверка нужна обоим.
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, detail="no such account"
            )

        allowance, tier = await _chat_gate(
            session, user, locale=payload.locale, message=payload.message
        )
        birth = await resolve_birth(
            session, user, profile_id=payload.profile_id, birth=None
        )
        # Партнёр читается один раз и до расчётов, а не внутри цикла по восьми
        # системам: цикл — это секунды арифметики, и запрос в базу посреди него
        # означал бы соединение, занятое ими всеми.
        #
        # `except` здесь сохраняет прежнее поведение вместе с прежним местом
        # вызова: внутри цикла любой 4xx означал «эту систему не считаем» и
        # уходил в `missing`. Вынесенный наружу, он без этой ветки уронил бы
        # весь ход — 422 вместо ответа, потому что у человека две анкеты.
        try:
            partner = await _partner_for_chat(session, user)
        except HTTPException:
            partner = None

        thread_id = payload.thread_id or None
        if thread_id:
            thread_row = await session.get(ChatThread, thread_id)
            if thread_row is None or thread_row.user_id != user.id:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, detail="no such conversation"
                )

        earlier = (
            (
                await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.thread_id == thread_id)
                    .order_by(ChatMessage.created_at)
                )
            ).scalars().all()
            if thread_id
            else []
        )
        history = [(m.role, m.body) for m in earlier]

        # What she has already cited in this thread, for the fence that notices
        # she is circling the same four placements. The rows carry it and the
        # history tuples do not, which is why this is read here rather than
        # derived from `history`: the repetition people complained about after
        # ten turns is in the citations, not in the prose.
        already_cited = [
            factor
            for message in earlier[-conversation.MAX_HISTORY:]
            if message.role != "user"
            for factor in (message.cited_factors or [])
        ]

        memory = await _recall(session, user)
        written_rows = (
            await session.execute(
                select(Reading.system, Reading.chapter).where(Reading.user_id == user.id)
            )
        ).all()

    _cheap, _mid, _strong = models()

    # ── 2. восемь систем, без единого соединения ──────────────────────────
    results: list[CalcResult] = []
    missing: list[str] = []
    for system in CHAT_SYSTEMS:
        try:
            options = _options_for(system, "placidus")
            if system == "compatibility":
                # Needs a second chart, and most people have not added one. It
                # is offered rather than assumed: asking the engine for a
                # synastry with nobody in it would raise on every single turn.
                if partner is None:
                    missing.append(system)
                    continue
                options["other"] = partner
            results.append(await _calc(system, birth, **options))
            if stage is not None:
                named = _stage_for(system, results[-1])
                if named is not None:
                    await stage(*named)
        except HTTPException:
            # Three of the eight need a birth time, and a person who never gave
            # one is the common case rather than the edge. Dropping them
            # silently is what made her change the subject: asked where to
            # live, she would answer from a life path, because the map simply
            # was not in front of her and nothing said so. Now she is told what
            # is missing and can say it — "your map needs the time you were
            # born" is a useful answer, and it sells the one thing that would
            # unlock it.
            missing.append(system)
            continue

    # `paid` is the voice tier and the per-call ceiling, not the allowance:
    # anyone who has given us money is written to as someone who has. What
    # separates the tiers is the model and the count, decided above.
    # **Funded is a property of the generation, not of the tier.**
    #
    # This read `tier != "free"`, which was true while every free turn ran on
    # the cheap model. The welcome bundle broke that: a brand-new account is
    # still `free` and its first three turns are on the mid model, so the
    # $0.05 free-tier ceiling refused a generation we had deliberately decided
    # to pay for — `budget_exceeded` where the reader should have had an
    # answer, measured at $0.0788 against $0.05.
    #
    # Reading the allowance instead says the true thing: a turn on the cheap
    # model is guarded as cheap, and a turn we chose to spend money on is
    # guarded as spent. With the cheap tier gone every chat turn is a chosen
    # spend — the welcome question, the purchase bundle and the plan all run
    # on models we deliberately pay for — and the caps are what bound them.
    paid = allowance.model != _cheap

    # Alma knows which chapters already exist for this person, so she can
    # speak in their context — and offer to open the one that answers a
    # question she is about to answer thinner. Titles only, never bodies:
    # bodies would multiply the prompt by the library's size. Строки прочитаны
    # в первой транзакции; здесь только просеивание, оно к базе не ходит.
    # **Только настоящие главы, и проверяется это по каталогу, а не списком
    # исключений.** Здесь стояло `chapter != "spheres"`, и это было верно ровно
    # для одной из трёх псевдоглав, живущих в той же таблице: дневная заметка
    # пишется как `transits/daily:2026-08-07`, а открывающий абзац — как
    # `natal/opening:love`. Обе прошли бы фильтр, дошли до
    # `i18n.chapter_words`, который на неизвестной паре поднимает `KeyError`, —
    # и весь `POST /v1/chat` ответил бы 500 всякому, кто хоть раз открыл
    # закрытую главу или получил утреннюю заметку. Спрашивать «есть ли такая
    # глава в оглавлении» надёжнее любого списка: четвёртая псевдоглава не
    # обязана про этот фильтр знать.
    written_rows = [
        row for row in written_rows
        if row[1] in {c.slug for c in chapter_defs.BY_SYSTEM.get(row[0], ())}
    ]
    # **Глава-источник называется здесь, где собирается контекст, а не задним
    # числом.** Единственное, что связывает ответ с главой, — заголовки уже
    # написанных глав, уходящие в промт ниже; ничего другого про главы модель
    # не видит. Одна глава в контексте — её можно назвать честно; несколько
    # или ни одной — назвать нечего, и поле остаётся null: выбирать «самую
    # похожую» значило бы выдумывать источник ровно там, где продукт обещает
    # не выдумывать. Пары (система, глава) убираются от повторов — та же глава
    # на двух языках лежит двумя строками, а глава при этом одна.
    unique_chapters = list(dict.fromkeys((row[0], row[1]) for row in written_rows))
    source_chapter = None
    if len(unique_chapters) == 1:
        src_system, src_slug = unique_chapters[0]
        src_words = i18n.chapter_words(
            src_system, src_slug, locale=i18n.resolve(payload.locale)
        )
        source_chapter = {
            "system": src_system,
            "slug": src_slug,
            "title": src_words.title,
        }
    if written_rows:
        titles = []
        for sys_slug, ch_slug in written_rows[:24]:
            words = i18n.chapter_words(sys_slug, ch_slug, locale=i18n.resolve(payload.locale))
            titles.append(f"{sys_slug}/{ch_slug} — {words.title}")
        memory = list(memory) + [
            "Главы, уже написанные для этого человека (можно ссылаться): "
            + "; ".join(titles)
            + ". Если вопрос глубже покрыт главой, которая ещё не написана, "
            "скажи об этом и предложи открыть её на экране системы."
        ]
    # ── 3. месячный потолок: своя короткая транзакция ─────────────────────
    #
    # Отдельно от первой намеренно: проекция считается из результатов восьми
    # систем, которых до расчёта не существует. Читать нечего, кроме суммы за
    # месяц, — один запрос.
    #
    # Потолок месяца сторожит генерацию, а кризисный ход её не совершает: он
    # отвечает строкой из каталога, ноль токенов, ноль центов. Тот же довод, что
    # у квоты выше, — и здесь он даже прямее: проекция считает стоимость
    # обращения, которого не будет.
    if not validator.crisis(payload.message):
        async with session_scope() as session:
            await _guard_month(
                session,
                user,
                tier=tier,
                locale=payload.locale,
                projected=_chat_projection(
                    question=payload.message,
                    results=results,
                    history=history,
                    model=allowance.model,
                    locale=payload.locale,
                    paid=paid,
                    memory=memory,
                ),
            )

    # ── 4. сама генерация, без соединения: 10–40 секунд ───────────────────
    try:
        reply = await conversation.answer(
            question=payload.message,
            results=results,
            provider=provider(),
            model=allowance.model,
            locale=payload.locale,
            paid=paid,
            history=history,
            memory=memory,
            missing=missing,
            already_cited=already_cited,
        )
    except cost.BudgetExceeded as exc:
        log.error("budget exceeded in chat for %s: %s", user.id, exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "budget_exceeded",
                "message": i18n_replies.reply("budget_exceeded", payload.locale),
            },
        ) from exc
    except AnswerTruncated as exc:
        # Ход, обрезанный все три раза, — три оплаченные генерации, и до этой
        # ветки они уходили в 503 ниже, ничего не записав. Тот же довод, что у
        # главы: `AnswerTruncated` — наследник `ModelUnavailable`, поэтому
        # порядок веток здесь и есть починка. Вопрос из квоты по-прежнему не
        # списывается — `_charge_anyway` трогает только деньги, — потому что
        # правило «вопрос платится за ответ» ошибке не уступает.
        log.error("every attempt at a chat turn for %s was truncated: %s", user.id, exc)
        await _charge_anyway(user, cents=_truncated_cents(exc))
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "ai_unavailable",
                "message": i18n_replies.reply("ai_unavailable", payload.locale),
            },
        ) from exc
    except ModelUnavailable as exc:
        # `str(exc)` here was the provider's own error object, forwarded whole:
        # "Error code: 400 - {'type': 'error', … 'request_id':
        # 'req_011CdoZt3dWSaLemkVXSMkLs'}", shown to somebody who had just
        # written "honestly i am not okay tonight". Another company's payload
        # and an internal identifier are not a sentence for a reader. Logged
        # where an engineer will find it; the body is one of ours.
        log.error("model provider refused a chat turn for %s: %s", user.id, exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "ai_unavailable",
                "message": i18n_replies.reply("ai_unavailable", payload.locale),
            },
        ) from exc
    except conversation.AnswerRefused as exc:
        # Every attempt was paid for and the money is recorded before the 422.
        # The *question* is not, and that reversal is the point: the comment
        # here used to read "a question that keeps tripping the validator is
        # still a question", and it was written before asides became free. The
        # two rules then contradicted each other — a death question that
        # succeeds is an aside and costs nothing, the same question that fails
        # cost one of three. Measured on a free account: three questions spent
        # on one answer and two error screens (`docs/CONVERSATION.md` §13).
        # The worry the counter answered — that an unlimited re-ask makes the
        # cheapest tier the most expensive — is answered by the spend ledger
        # and the monthly ceiling, which both run on this exact path.
        log.warning("chat turn refused for %s: %s", user.id, exc)
        await _charge_anyway(user, cents=exc.spend.cents)
        raise HTTPException(
            422,
            detail={
                "error": "answer_refused",
                "message": i18n_replies.reply("answer_refused", payload.locale),
            },
        ) from exc
    except ValueError as exc:
        # The chart had no facts to answer from. Nothing was generated, so
        # nothing is charged.
        log.warning("nothing to answer a chat turn from for %s: %s", user.id, exc)
        raise HTTPException(
            422,
            detail={
                "error": "answer_refused",
                "message": i18n_replies.reply("answer_refused", payload.locale),
            },
        ) from exc

    # ── 5. вопрос, ответ, счётчик и расход — одним куском ─────────────────
    #
    # Всё, что пишет этот ход, пишется здесь и коммитится на выходе из блока,
    # не выходя из замка аккаунта (`_chat_slot` в `_chat_turn`). Ровно это
    # требовал прежний явный `commit()` под замком: следующий ход обязан
    # увидеть посчитанный вопрос своей сессией.
    async with session_scope() as session:
        thread_row = (
            await session.get(ChatThread, thread_id) if thread_id else None
        )
        if thread_row is None or thread_row.user_id != user_id:
            # Тред либо не назывался (новая беседа), либо исчез между первой
            # транзакцией и этой. Второе — гонка с удалением аккаунта или
            # беседы, и ответ у неё один: ход уже сгенерирован и оплачен,
            # выбрасывать его в 404 значит заплатить за воздух второй раз.
            if thread_id:
                log.warning(
                    "thread %s vanished mid-turn for %s — the answer goes to a "
                    "fresh thread rather than into the bin", thread_id, user_id,
                )
            thread_row = ChatThread(user_id=user_id, title=payload.message[:80])
            session.add(thread_row)
            await session.flush()

        # Вопрос человека — здесь, рядом с ответом. См. довод в докстринге:
        # вопрос без ответа хуже, чем ничего.
        session.add(
            ChatMessage(
                thread_id=thread_row.id,
                role="user",
                body=payload.message,
                # Язык хода — только у ответа Alma, и это различие, а не
                # экономия. Её реплику язык запроса описывает честно —
                # `conversation._wrong_script` не даст ей ответить на другом.
                # А человек пишет на чём хочет: русский вопрос при английском
                # интерфейсе — обычное дело, и штамп «en» на нём **вечно**
                # закрывал бы ему перевод (кеш пропускает реплики, чей язык
                # совпал с запрошенным). Null здесь честен так же, как у
                # строк до колонки: не знаем — переводчик посмотрит сам.
                locale=None,
            )
        )

        message = ChatMessage(
            thread_id=thread_row.id,
            role="alma",
            locale=i18n.resolve(payload.locale),
            body=reply.text(),
            cited_factors=list(reply.cited_factors),
            # Stored in the wire vocabulary rather than the internal one, because
            # the only consumer of the column is the client that reads it back. A
            # thread reopened a week later must render the way it rendered live —
            # before this column, `GET /v1/chat/threads/{id}` returned no kind at
            # all, so every reopened turn fell through to the legacy branch and the
            # honest note vanished on relaunch.
            turn_kind=reply.turn_kind,
            # Та же тройка, что уходит в теле ответа, — сохранённая, чтобы
            # перечитанная беседа показала ту же дверь в главу, что показала живая.
            # См. довод у колонки в `db/models.py`.
            source_chapter=source_chapter,
            model=reply.model,
            cost_cents=reply.spend.cents,
            # Токены и попытки — рядом со стоимостью, из того же `Spend`, что
            # её и посчитал. Без них восемь центов за ход неразложимы на «один
            # дорогой» и «три обычных»; довод целиком у колонок в `db/models.py`.
            input_tokens=reply.spend.input_tokens,
            output_tokens=reply.spend.output_tokens,
            attempts=reply.attempts,
        )
        session.add(message)
        thread_row.updated_at = utcnow()

        if reply.remember:
            await _remember(session, user, reply.remember, source=f"chat:{thread_row.id}")

        # A turn is only counted if it was a reading. A free reader gets three
        # questions a day, and before this line looked at `kind`, "hi" and "thanks"
        # together spent two thirds of a day's allowance and answered nothing
        # (`docs/CONVERSATION.md §3`). The money is charged either way — the
        # generation happened, and `_spend` below records it — so what this decides
        # is the promise, not the ledger: you pay a question for an answer about
        # yourself, and greeting her is free.
        if reply.spends_a_question:
            asked = await _count(
                session, user, allowance.metric, day=_period_start(allowance.period)
            )
        else:
            asked = await _asked(session, user, allowance)
        await _spend(session, user, reply.spend.cents)
        await session.flush()
        thread_row_id, message_id, message_body, message_created = (
            thread_row.id, message.id, message.body, message.created_at.isoformat()
        )

    return {
        "thread_id": thread_row_id,
        "message": {
            "id": message_id,
            "role": "alma",
            "body": message_body,
            "cited_factors": list(reply.cited_factors),
            # `turn_kind` is the field the two shipped clients decode, in the
            # vocabulary they decode it in — `reading | chart_silent |
            # conversation`. It was emitted as `kind` with `reading | silent |
            # aside`, which no client has ever heard of, so the whole taxonomy
            # was dead on arrival on both platforms and the honest note under a
            # silent turn was unreachable for everybody.
            #
            # `kind` stays beside it, in this module's own vocabulary, because
            # it is what the backend's own tests and any non-app consumer read;
            # `answered_from_chart` stays because it is the field the shipped
            # binaries in the field still fall back to. All three are derived
            # from one value, so they cannot disagree with each other.
            "turn_kind": reply.turn_kind,
            "kind": reply.kind,
            "answered_from_chart": reply.answered_from_chart,
            "created_at": message_created,
        },
        "questions_left": max(0, allowance.limit - asked),
        # The period is reported alongside the count because "two left" means
        # something different to a subscriber than to a free user, and the
        # client cannot tell which sentence to write without being told.
        "questions_period": allowance.period,
        # Глава, на которую ответ опирается, — или null, когда назвать её
        # честно нельзя. См. довод у места, где она выбирается.
        "source_chapter": source_chapter,
    }


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    user: CurrentUser,
    provider: ProviderDep,
    _released: SessionReleased,
) -> StreamingResponse:
    """Тот же ход беседы, рассказанный по мере работы — SSE.

    События:

    * ``event: stage`` — ``{"stage": "house" | "body", "name": "<имя движка>"}``,
      по настоящим шагам сборки карты (`_stage_for`);
    * ``event: done`` — ровно тот JSON, что отдаёт ``POST /v1/chat``;
    * ``event: error`` — ``{"status": <код>, "detail": <тело ошибки /v1/chat>}``,
      когда ход упал уже после старта потока.

    Ход — тот же `_chat_turn`, что у ``/v1/chat``: квота, потолки и счёт
    общие по построению, дыры мимо квоты нет, потому что нет второго пути.
    """
    # Отказ квоты — до первого байта и тем же телом, что у `/v1/chat`: SSE
    # начинается со статуса 200, и отказ, случившийся после старта потока,
    # пришлось бы выдумывать заново внутри «успешного» ответа. Проверка ничего
    # не тратит, поэтому её второй заход внутри `_chat_turn` не удваивает счёт.
    #
    # Своя короткая транзакция: соединение запроса уже возвращено пулу
    # (`SessionReleased`), и брать его на весь стрим было бы ровно тем, от чего
    # мы уходим.
    async with session_scope() as session:
        await _chat_gate(session, user, locale=payload.locale, message=payload.message)

    # Одно голое значение вместо строки пользователя: сессия запроса умрёт
    # раньше, чем генератор начнёт работать, и трогать через неё ORM-объект
    # оттуда уже нельзя.
    user_id = user.id

    async def turns() -> AsyncIterator[str]:
        # Стадии рождаются внутри `_chat_turn`, а наружу уходят отсюда —
        # очередь и есть та труба, по которой рабочая корутина рассказывает
        # генератору, что она сейчас делает.
        queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

        async def tell(kind: str, name: str) -> None:
            await queue.put(("stage", {"stage": kind, "name": name}))

        async def work() -> None:
            try:
                # Никакой сессии здесь больше нет — и не только потому, что
                # сессия запроса к этому моменту закрыта. `_chat_turn` сам
                # берёт свои три коротких транзакции и ни одну из них не держит
                # через генерацию; открытая сессия, переданная сюда, вернула бы
                # ровно ту болезнь, ради которой всё это разрезано.
                body = await _chat_turn(payload, user_id, provider, stage=tell)
                await queue.put(("done", body))
            except HTTPException as exc:
                # Тот же словарь, что ушёл бы телом ошибки на `/v1/chat`:
                # клиент собирает из него тот же отказ и показывает ту же
                # фразу — стрим не изобретает второй язык поломок.
                detail = (
                    exc.detail
                    if isinstance(exc.detail, dict)
                    else {"error": "error", "message": str(exc.detail)}
                )
                await queue.put(("error", {"status": exc.status_code, "detail": detail}))
            except Exception:  # noqa: BLE001 — поток обязан кончиться словом, а не тишиной
                log.exception("chat stream failed for %s", user_id)
                await queue.put(("error", {"status": 500, "detail": {"error": "internal"}}))

        task = asyncio.create_task(work())
        # Ссылка живёт вне генератора: задача, на которую никто не смотрит,
        # может быть собрана сборщиком мусора посреди работы — это
        # документированное поведение `asyncio.create_task`, а ниже мы как раз
        # перестаём её ждать.
        #
        # Ссылку берёт реестр, и берёт всегда: его `False` — это жалоба в лог о
        # том, что брошенных генераций стало больше, чем покрывает окно
        # остановки, а не отказ присмотреть. Отказаться здесь нельзя ничем —
        # модель уже позвана и оплачена (см. `TurnRegistry.admit`).
        STREAM_TURNS.admit(task)
        try:
            while True:
                kind, data = await queue.get()
                yield f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                if kind in ("done", "error"):
                    return
        finally:
            # **Клиент ушёл — ход дописывается, а не отменяется.**
            #
            # Здесь стоял `task.cancel()` с доводом «не жечь модель дальше», и
            # довод не выдержал арифметики. Отмена приходит в `_chat_turn` в
            # любую точку — в том числе после того, как `conversation.answer`
            # уже вернул ответ, — и уносит с собой всю транзакцию: `session_scope`
            # на `CancelledError` делает rollback. То есть генерация состоялась и
            # была оплачена, а в базе не остаётся ни расхода, ни списанного
            # вопроса, ни самого ответа. Сорванная связь — это норма мобильной
            # сети, лифт и блокировка экрана, а не редкость; при отмене за неё
            # платили мы, и месячный потолок этого не видел.
            #
            # Сэкономить отмена могла только хвост уже начатого вызова —
            # произведённые токены не возвращаются, — и меняла этот хвост на
            # потерю всей суммы и потерю ответа. Теперь задача доживает свою
            # жизнь сама: она пишет ответ в тред, считает вопрос и коммитит
            # расход своей собственной сессией. Человек, вернувшийся в беседу,
            # находит там ответ, за который мы заплатили, — деньги купили
            # написанное, а не воздух.
            #
            # Ограничитель на «сколько таких можно завести» — не отмена, а
            # квота: `_chat_turn` берёт замок аккаунта и проверяет порцию
            # внутри него, так что оборванные ходы одного человека идут
            # по одному и упираются в ту же стену, что обычные.
            if not task.done():
                log.info(
                    "chat stream for %s lost its reader mid-turn — finishing the "
                    "turn anyway so the generation it already paid for is recorded",
                    user_id,
                )

    return StreamingResponse(
        turns(),
        media_type="text/event-stream",
        # Прокси между телефоном и нами не должен ни кэшировать поток, ни
        # копить его в буфере до конца генерации — иначе стадии приедут
        # одной пачкой вместе с ответом, то есть не приедут вовсе.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/memory")
async def memory(user: CurrentUser, session: SessionDep) -> dict:
    """What Alma remembers — inspectable, because it has to be deletable."""
    rows = (
        await session.execute(
            select(Memory).where(Memory.user_id == user.id).order_by(Memory.created_at.desc())
        )
    ).scalars().all()
    return {
        "memory": [
            {"id": m.id, "kind": m.kind, "body": m.body, "created_at": m.created_at.isoformat()}
            for m in rows
        ]
    }


@router.delete("/memory/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def forget(memory_id: str, user: CurrentUser, session: SessionDep) -> None:
    row = await session.get(Memory, memory_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="nothing to forget")
    await session.delete(row)
