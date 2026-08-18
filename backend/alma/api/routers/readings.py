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
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ... import i18n
from ...i18n import replies as i18n_replies
from ...ai import chapters as chapter_defs
from ...ai import conversation, cost, voice, writer
from ...ai.provider import ModelUnavailable, Provider, models
from ...ai.writer import ReadingRefused
from ...auth import entitlements
from ...calc import CalcResult, TimeRequired
from ...calc.cache import MOMENT_OPTIONS, compute_cached
from ...calc.contract import cache_key
from ...calc.service import AmbiguousBirthTime, ambiguity_detail
from ...config import settings
from ...db.models import ChatMessage, ChatThread, Memory, Reading, UsageCounter, utcnow
from ..cache import result_cache
from ..deps import (
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
    period: str      # "day" | "month"
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
    """The first few questions of a new account, on the model that sells.

    See `config.free_welcome_bundle` for the money. The shape is the owner's
    bundle exactly — a finite pile, counted for the life of the account rather
    than per day — because it is the same idea aimed at the other end: that
    bundle is the thanks for a purchase, and this one is the reason to make it.
    """
    return Allowance("welcome", mid, settings().free_welcome_bundle, "once", WELCOME_QUESTIONS_METRIC)


async def _calc(system: str, birth, **options) -> CalcResult:
    try:
        return compute_cached(system, birth, cache=result_cache(), **options)
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
    session: SessionDep,
    provider: ProviderDep,
) -> dict:
    """Fetch a chapter, writing it the first time it is asked for."""
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
    if not access.allowed:
        # `and not chapter.free` здесь больше нет, и это не упрощение ради
        # краткости: бесплатная глава физически не может прийти сюда с отказом —
        # `check` отвечает про неё True первой же веткой, а безымянная пара
        # выбирает `PAIR_WITHOUT_PROFILE` только для платной. Второе условие
        # означало бы, что мы допускаем «бесплатная и закрытая», а такого
        # состояния нет.
        return await _locked_chapter(
            payload, user, session, provider,
            chapter=chapter, language=language, access=access, pair=pair,
        )

    # **Месячный кредит подписчика тратится здесь — на первой платной главе про
    # нового человека, и больше нигде.**
    #
    # Почему не в `entitlements.check`: тот вызывается на каждом рендере
    # оглавления и каждом обновлении хаба, и кредит, списываемый проверкой прав,
    # утекал бы от одного взгляда на экран. Почему не в `covers`: там нет базы и
    # нет права на запись. Единственное место, где «человек действительно
    # получает новый отчёт», — момент перед генерацией, и он здесь.
    #
    # Порядок с `access` тоже не случаен: подписка **покрывает** совместимость
    # (`scope="all"`), поэтому закрытая глава выше до этой строки не доходит, и
    # решение «включённая проверка или $4.99 сверх» принимается ровно один
    # раз — тут.
    #
    # Развилки `if chapter.free` здесь больше нет. Она вела в
    # `_teaser_or_paywall` — отдельный бесплатный тизер «Притяжение» со своим
    # капом на число новых людей в месяц. Владелец снял его 17.08.2026 словами
    # «тизер и глава I пары — одно и то же»: теперь это обычная закрытая глава,
    # и её открывающий абзац пишется тем же путём, что у остальных сорока.
    if payload.system == "compatibility" and pair is not None:
        await _pair_credit_or_paywall(session, user, pair)

    birth = await resolve_birth(
        session, user, profile_id=payload.profile_id, birth=payload.birth
    )
    options = _options_for(payload.system, payload.house_system)
    if payload.system == "compatibility":
        options["other"] = await _partner(session, user, payload)
    result = await _calc(payload.system, birth, **options)
    calc_key = _reading_key(payload.system, birth, options, result, chapter)

    async def _lookup() -> Reading | None:
        return (
            await session.execute(
                select(Reading).where(
                    Reading.user_id == user.id,
                    Reading.system == payload.system,
                    Reading.chapter == chapter.slug,
                    Reading.calc_key == calc_key,
                    Reading.locale == language,
                )
            )
        ).scalar_one_or_none()

    lock_key = f"{user.id}:{payload.system}:{chapter.slug}:{calc_key}:{language}"
    try:
        async with _write_lock(lock_key):
            return await _read_or_write(
                payload, user, session, provider, chapter=chapter,
                language=language, result=result, calc_key=calc_key,
                lookup=_lookup,
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
    session,
    provider,
    *,
    chapter,
    language: str,
    access: entitlements.Access,
    pair: str | None,
) -> dict:
    """Закрытая глава со своим открывающим абзацем.

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

    if payload.system == "compatibility" and pair is None:
        # Пару не о ком считать: партнёров ноль или несколько и ни один не
        # назван. Синастрию построить не из чего, значит и позиций, из которых
        # пишется абзац, не существует — это не сбой, а честное «сначала
        # скажи, про кого». Стена всё равно отдаётся: на ней клиент рисует
        # «tap to add someone →» (спека §1, карточка совместимости).
        return wall(needs_partner=True)

    # **Ключ берётся до расчёта, и это не микрооптимизация.**
    #
    # У обычной главы иначе нельзя: её ключ включает список факторов, которых
    # без расчёта не существует. У абзаца — можно, ровно потому, что факторов
    # в его ключе нет (см. `_opening_key`), а рождение и неподвижные опции
    # известны сразу. Разница видна на транзитах: их расчёт — скан года,
    # 1.35 секунды, и он же стоит за экраном «Сегодня», в который неподписчик
    # заходит каждый день. Считать его ради строки, которая уже лежит в базе,
    # значит платить секундой за каждое открытие уже написанного.
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

    async def _lookup() -> Reading | None:
        return (
            await session.execute(
                select(Reading).where(
                    Reading.user_id == user.id,
                    Reading.system == payload.system,
                    Reading.chapter == stored_chapter,
                    Reading.calc_key == calc_key,
                    Reading.locale == language,
                )
            )
        ).scalar_one_or_none()

    found = await _lookup()
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
            again = await _lookup()
            if again is not None:
                return wall(
                    opening=again.body,
                    cached=True,
                    created_at=again.created_at.isoformat(),
                )
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
                payload, user, session, provider,
                chapter=chapter_defs.opening_of(chapter), language=language,
                result=result, calc_key=calc_key, stored_chapter=stored_chapter,
                lookup=_lookup,
            )
    finally:
        _prune_lock(lock_key)

    if written is None:
        return wall()
    body, cached, created_at = written
    return wall(opening=body, cached=cached, created_at=created_at)


async def _write_opening(
    payload: ReadingRequest,
    user,
    session,
    provider,
    *,
    chapter,
    language: str,
    result: CalcResult,
    calc_key: str,
    stored_chapter: str,
    lookup,
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
    """
    _cheap, mid, _strong = models()
    tier = await entitlements.tier_of(session, user)
    memory = await _recall(session, user)

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
        # ради семи десятых цента, мы получаем экран, где над размытием пусто,
        # — и владелец увидел ровно это: «все эти страницы должны выглядеть
        # таким образом: кусочек текста главы и заблюренная часть».
        #
        # Пустое место вместо начала не экономит, а отменяет продажу.
        #
        # Расход всё равно ограничен, и дважды. Абзац пишется один раз на главу
        # и живёт в кэше навсегда — сорок одна глава это около тридцати центов
        # за всю жизнь аккаунта. А от петли (сменил дату рождения — ключ расчёта
        # другой — пиши заново) стоит [_opening_allowance] ниже.
        await _opening_allowance(session, user)
        written = await writer.write(
            result=result,
            chapter=chapter,
            provider=provider(),
            model=mid,
            locale=language,
            paid=False,
            register="opening",
            memory=memory,
            reader_gender=await _reader_gender(session, user, payload),
        )
    except ReadingRefused as exc:
        # Три попытки состоялись и стоили денег — счёт двигается, как и у
        # обычной главы. `_charge_anyway` откатывает сессию и коммитит сумму
        # отдельно, поэтому после него возвращать можно только константу.
        await _charge_anyway(session, user, cents=exc.spend.cents)
        log.warning(
            "no opening for %s/%s: %s", result.system, chapter.slug, exc
        )
        return None
    except (cost.BudgetExceeded, ModelUnavailable, HTTPException) as exc:
        # `HTTPException` здесь — это 429 месячного потолка из `_guard_month`
        # или 400 «сначала сохрани дату рождения» из `_profile_id`. Ловятся
        # вместе с остальными намеренно: и то и другое — причина не написать
        # абзац, а не причина не показать цену.
        log.warning(
            "no opening for %s/%s: %s", result.system, chapter.slug,
            getattr(exc, "detail", exc),
        )
        return None

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
    await _spend(session, user, written.spend.cents)
    try:
        await session.flush()
    except IntegrityError:
        # Другой воркер написал тот же абзац между нашим поиском и вставкой.
        # Его слова побеждают, как и у обычной главы; наша генерация всё равно
        # состоялась, поэтому сумма записывается заново после отката.
        await session.rollback()
        log.warning(
            "lost the opening race for %s/%s — returning the stored copy",
            result.system, chapter.slug,
        )
        await _spend(session, user, written.spend.cents)
        await session.flush()
        theirs = await lookup()
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
    session,
    provider,
    *,
    chapter,
    language: str,
    result: CalcResult,
    calc_key: str,
    lookup,
) -> dict:
    """The half of `read` that must run one-at-a-time per reading key.

    Everything below happens only for somebody entitled to this chapter: the
    wall in `read` has already answered 402 otherwise, before the chart was
    even computed. No `access` argument reaches here for that reason — the one
    thing it used to decide, the blurred-preview flag, no longer exists.
    """
    stored = await lookup()
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

    # One fact — is this chapter the free sample? — chooses both the model and
    # the ceiling that model is spent against, so the two cannot disagree.
    # They used to. Every chapter went to the strong model while `writer.write`
    # guarded it with `paid=not chapter.free`, i.e. against the $0.05 free
    # ceiling, and the astrocartography sample carries eleven thousand
    # characters of line descriptions: $0.0530 projected on Opus 5. It raised
    # BudgetExceeded on the first attempt and answered 503, so the one chapter
    # that exists to sell astrocartography could not be read by anybody, ever.
    # The same prompt projects $0.0318 on the mid model.
    _cheap, mid, strong = models()
    model = mid if chapter.free else strong

    tier = await entitlements.tier_of(session, user)
    memory = await _recall(session, user)
    await _guard_month(
        session,
        user,
        tier=tier,
        locale=language,
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
            reader_gender=await _reader_gender(session, user, payload),
        )
    except ReadingRefused as exc:
        # Charged before the refusal is raised. Three attempts really happened
        # and really cost money, and a ceiling that only sees the requests
        # that succeeded is not a ceiling on what an account can spend — it is
        # a ceiling on what an account can spend *usefully*.
        await _charge_anyway(session, user, cents=exc.spend.cents)
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
    except ModelUnavailable as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ai_unavailable", "message": str(exc)},
        ) from exc

    profile_id = await _profile_id(session, user)
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
        theirs = await lookup()
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


def _counter_id(user_id: str, day, metric: str) -> str:
    return f"{user_id}:{day.isoformat()}:{metric}"


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


async def _counter_row(session, user_id: str, metric: str, *, day: date | None = None) -> UsageCounter:
    """The counter for one account, one metric and one period.

    Keyed on the id rather than on the `User` instance, because one caller —
    `_charge_anyway` — has just rolled its session back and every attribute of
    that instance is expired: reading `user.id` there would attempt lazy IO in
    the wrong place and raise.
    """
    when = day or datetime.now(timezone.utc).date()
    key = _counter_id(user_id, when, metric)
    row = await session.get(UsageCounter, key)
    if row is None:
        row = UsageCounter(
            id=key, user_id=user_id, day=when, metric=metric, count=0, amount=0.0
        )
        session.add(row)
    return row


async def _counter(session, user, metric: str, *, day: date | None = None) -> UsageCounter:
    """One period's counter for one metric, created if this is the first tick.

    Both numeric fields are set explicitly rather than left to the column
    default: SQLAlchemy applies those at INSERT, so a freshly constructed row
    reads back as None and the first `+=` raises.

    `day` is the *start* of whatever period the counter covers, which for a
    monthly one is the first of the month. That is also why a monthly counter
    carries its own metric name rather than reusing the daily one with a
    month-start day — on the first of every month the two would land on the
    same primary key, and one turn would be charged to both allowances.
    """
    return await _counter_row(session, user.id, metric, day=day)


async def _count(session, user, metric: str, amount: int = 1, *, day: date | None = None) -> int:
    row = await _counter(session, user, metric, day=day)
    row.count = (row.count or 0) + amount
    await session.flush()
    return row.count


async def _spend(session, user, cents: float) -> None:
    """Record what a generation cost, in cents, against today.

    These rows are what `cost.month_spend` sums to decide whether an account
    has spent its month, which is why the metric name is imported from there
    rather than written out again: a typo here would not fail anything, it
    would just make every account look free.
    """
    row = await _counter(session, user, cost.SPEND_METRIC)
    row.amount = (row.amount or 0.0) + cents
    await session.flush()


async def _charge_anyway(session, user, *, cents: float) -> None:
    """Record what a failed request already spent, and commit it.

    Two things have to happen in this order. The half-written request is
    thrown away first — a `Reading` row with no body, or a question with no
    answer, is worse than nothing — and *then* the money is written and
    committed on its own. Without the rollback the money would be committed
    alongside the wreckage; without the commit it would be rolled back with
    it, which is what used to happen: the router raised its 422 before
    reaching `_spend`, so the only requests the month ledger could see were
    the ones that worked. The refusal path spends *more* than the success path
    — it is the one that retried — so that is not a ceiling on what an account
    can spend, only on what it can spend usefully.

    **Money only.** This used to take a `metric` and increment the question
    counter as well, so a turn that produced an error screen cost a free reader
    one of three. The parameter is gone rather than left unused: it is one
    keyword away from being reintroduced by somebody reading the call site
    rather than this docstring, and the rule it broke — you pay a question for
    an answer about yourself — is the one the whole taxonomy was built on.
    """
    user_id = user.id
    await session.rollback()

    if cents:
        row = await _counter_row(session, user_id, cost.SPEND_METRIC)
        row.amount = (row.amount or 0.0) + cents
    log.warning("charging %s for a request that produced nothing: %.4f¢", user_id, cents)
    await session.commit()


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


async def _opening_allowance(session, user) -> None:
    """Ограничитель витрины: считает абзацы, а не доллары.

    Отдельный от месячного потолка намеренно — см. довод на месте вызова.
    Отказ здесь выглядит для клиента так же, как любая другая причина не
    написать абзац: цена показывается, начала нет. Это последняя линия и она
    срабатывать не должна; если сработала — в логе видно, у кого.
    """
    from ...db.models import UsageCounter

    month = date.today().replace(day=1)
    key = f"{user.id}:{month.isoformat()}:{OPENING_METRIC}"
    row = await session.get(UsageCounter, key)
    if row is None:
        row = UsageCounter(
            id=key, user_id=user.id, day=month, metric=OPENING_METRIC,
            count=0, amount=0.0,
        )
        session.add(row)
    row.count = (row.count or 0) + 1
    await session.flush()
    if row.count > OPENING_ALLOWANCE:
        log.warning(
            "opening allowance spent by %s: %s in %s",
            user.id, row.count, month.isoformat(),
        )
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "opening_allowance"},
        )


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
    session: SessionDep,
    provider: ProviderDep,
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
    """
    from ...ai import spheres as spheres_module

    language = i18n.resolve(locale)
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

    stored = (
        await session.execute(
            select(Reading).where(
                Reading.user_id == user.id,
                Reading.system == "natal",
                Reading.chapter == "spheres",
                Reading.calc_key == calc_key,
                Reading.locale == language,
            )
        )
    ).scalar_one_or_none()

    def _titled(blocks: list[dict]) -> list[dict]:
        out = []
        for block in blocks:
            words = i18n.chapter_words("natal", block["chapter"], locale=language)
            out.append({**block, "title": words.title})
        return out

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
            again = (
                await session.execute(
                    select(Reading).where(
                        Reading.user_id == user.id,
                        Reading.system == "natal",
                        Reading.chapter == "spheres",
                        Reading.calc_key == calc_key,
                        Reading.locale == language,
                    )
                )
            ).scalar_one_or_none()
            if again is not None:
                return {
                    "spheres": _titled(again.body.get("spheres", [])),
                    "cached": True,
                    "locale": language,
                }

            # The mid model, and the cheap one is gone from here: measured on
            # the owner's own first run, the cheap model burned all three
            # attempts on rules it was told about («ты был», an invented
            # factor, «ты должен») and the natal screen said Alma is silent.
            # Three failed cheap generations cost more than one good mid one.
            _cheap, mid, _strong = models()
            try:
                blocks, spend = await spheres_module.write(
                    result, provider=provider(), model=mid, locale=language
                )
            except (writer.ReadingRefused, cost.BudgetExceeded) as exc:
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"error": "ai_unavailable", "message": str(exc)},
                ) from exc

            profile_row_id = await _profile_id(session, user)
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
                theirs = (
                    await session.execute(
                        select(Reading).where(
                            Reading.user_id == user.id,
                            Reading.system == "natal",
                            Reading.chapter == "spheres",
                            Reading.calc_key == calc_key,
                            Reading.locale == language,
                        )
                    )
                ).scalar_one_or_none()
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


@router.get("/chat/threads")
async def threads(user: CurrentUser, session: SessionDep) -> dict:
    rows = (
        await session.execute(
            select(ChatThread)
            .where(ChatThread.user_id == user.id)
            .order_by(ChatThread.updated_at.desc())
        )
    ).scalars().all()
    return {
        "threads": [
            {"id": t.id, "title": t.title, "updated_at": t.updated_at.isoformat()} for t in rows
        ]
    }


@router.get("/chat/threads/{thread_id}")
async def thread(thread_id: str, user: CurrentUser, session: SessionDep) -> dict:
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
    return {
        "id": row.id,
        "title": row.title,
        "messages": [
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
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    user: CurrentUser,
    session: SessionDep,
    provider: ProviderDep,
) -> dict:
    """One turn of conversation, answered only from the chart."""
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
    allowance = _allowance(tier, mid=mid, locale=payload.locale, weekly=weekly)

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
    if asked >= allowance.limit:
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
            payload.locale,
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

    birth = await resolve_birth(session, user, profile_id=payload.profile_id, birth=None)
    results: list[CalcResult] = []
    missing: list[str] = []
    for system in CHAT_SYSTEMS:
        try:
            options = _options_for(system, "placidus")
            if system == "compatibility":
                # Needs a second chart, and most people have not added one. It
                # is offered rather than assumed: asking the engine for a
                # synastry with nobody in it would raise on every single turn.
                other = await _partner_for_chat(session, user)
                if other is None:
                    missing.append(system)
                    continue
                options["other"] = other
            results.append(await _calc(system, birth, **options))
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

    thread_row = None
    if payload.thread_id:
        thread_row = await session.get(ChatThread, payload.thread_id)
        if thread_row is None or thread_row.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no such conversation")
    if thread_row is None:
        thread_row = ChatThread(user_id=user.id, title=payload.message[:80])
        session.add(thread_row)
        await session.flush()

    earlier = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_row.id)
            .order_by(ChatMessage.created_at)
        )
    ).scalars().all()
    history = [(m.role, m.body) for m in earlier]

    # What she has already cited in this thread, for the fence that notices she
    # is circling the same four placements. The rows carry it and the history
    # tuples do not, which is why this is read here rather than derived from
    # `history`: the repetition people complained about after ten turns is in
    # the citations, not in the prose.
    already_cited = [
        factor
        for message in earlier[-conversation.MAX_HISTORY:]
        if message.role != "user"
        for factor in (message.cited_factors or [])
    ]

    session.add(ChatMessage(thread_id=thread_row.id, role="user", body=payload.message))

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
    memory = await _recall(session, user)

    # Alma knows which chapters already exist for this person, so she can
    # speak in their context — and offer to open the one that answers a
    # question she is about to answer thinner. Titles only, never bodies:
    # bodies would multiply the prompt by the library's size.
    from ...db.models import Reading as _Reading
    written_rows = (
        await session.execute(
            select(_Reading.system, _Reading.chapter).where(_Reading.user_id == user.id)
        )
    ).all()
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
        await _charge_anyway(session, user, cents=exc.spend.cents)
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

    message = ChatMessage(
        thread_id=thread_row.id,
        role="alma",
        body=reply.text(),
        cited_factors=list(reply.cited_factors),
        # Stored in the wire vocabulary rather than the internal one, because
        # the only consumer of the column is the client that reads it back. A
        # thread reopened a week later must render the way it rendered live —
        # before this column, `GET /v1/chat/threads/{id}` returned no kind at
        # all, so every reopened turn fell through to the legacy branch and the
        # honest note vanished on relaunch.
        turn_kind=reply.turn_kind,
        model=reply.model,
        cost_cents=reply.spend.cents,
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

    return {
        "thread_id": thread_row.id,
        "message": {
            "id": message.id,
            "role": "alma",
            "body": message.body,
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
            "created_at": message.created_at.isoformat(),
        },
        "questions_left": max(0, allowance.limit - asked),
        # The period is reported alongside the count because "two left" means
        # something different to a subscriber than to a free user, and the
        # client cannot tell which sentence to write without being told.
        "questions_period": allowance.period,
    }


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
