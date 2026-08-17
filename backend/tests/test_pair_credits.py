"""Месячный кредит подписчика, и что события подписки не имеют права трогать.

Две темы, и они об одном обещании с двух сторон.

**Кредит** — одна новая проверка пары в расчётный период. Период считается по
`renews_at` подписки, а не по календарю, и новый открывается только тогда,
когда дата уехала вперёд — то есть после оплаты. Всё остальное (отмена, grace
period, повторная доставка того же продления) обязано не начислять ничего:
каждое ошибочное начисление — это отчёт за 26¢, розданный за событие, за
которое никто не заплатил.

**Купленное навсегда** — дверь, бандл и пара — не закрывается ничем, кроме
возврата денег именно за него. Ни истечением подписки, ни её отменой, ни
возвратом за соседнюю покупку. Это строка над кнопкой на экране подписки
(«разборы, купленные навсегда, остаются твоими»), и нарушить её молча можно
одним лишним совпадением по `subscription_id`.

Тесты идут по матрице А7: случаи 4, 5, 6, 7 и «истечение не трогает статичное
и парное» названы в докстроках поимённо.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from conftest import database_url, run_async

from alma.api.routers import billing as billing_router
from alma.auth import accounts, entitlements
from alma.billing import credits
from alma.billing.provider import EventKind, NormalisedEvent
from alma.db import session as session_module
from alma.db.models import Entitlement, EntitlementKind, PairCredit, as_utc, utcnow


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A fresh database, driven synchronously through a small runner."""
    from alma import config as config_module

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "credits.db"))
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()
    run_async(session_module.create_all)

    def run(coro_factory):
        async def wrapper():
            async with session_module.session_scope() as session:
                return await coro_factory(session)

        return run_async(wrapper)

    yield run
    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


async def _subscriber(session, *, renews_in_days: int = 31, subscription_id: str = "sub_1"):
    """Аккаунт с живой месячной подпиской, как её пишет `_apply`."""
    user = await accounts.create_guest(session)
    moment = utcnow()
    await entitlements.grant(
        session, user,
        system=entitlements.EVERYTHING,
        kind=EntitlementKind.monthly.value,
        scope=entitlements.SCOPE_ALL,
        subscription_id=subscription_id,
        transaction_id="txn_first",
        renews_at=moment + timedelta(days=renews_in_days),
        duration=timedelta(days=renews_in_days),
        source="appstore",
    )
    return user


async def _plan_of(session, user):
    for held in await entitlements.for_user(session, user):
        if held.kind == EntitlementKind.monthly.value:
            return held
    raise AssertionError("no plan")


# ══════════════════════════════════════════════════════════════════════════
#  Период считается по подписке, а не по календарю
# ══════════════════════════════════════════════════════════════════════════

def test_the_period_ends_when_the_subscription_renews(db):
    """Не первого числа. Подписавшийся 31 января не получает вторую проверку
    первого февраля, а подписавшийся первого — не ждёт дольше остальных."""

    async def work(session):
        user = await _subscriber(session, renews_in_days=31)
        plan = await _plan_of(session, user)
        row = await credits.ensure_period(session, user)
        return row.period_end, plan.renews_at

    period_end, renews_at = db(work)
    assert as_utc(period_end) == as_utc(renews_at)


def test_a_person_without_a_subscription_has_no_credits(db):
    async def work(session):
        user = await accounts.create_guest(session)
        return await credits.state(session, user)

    assert db(work) == {"granted": 0, "used": 0, "remaining": 0, "period_end": None}


def test_the_plan_decides_how_many_are_included(db):
    """Число читается из каталога, а не написано в модуле кредитов: обещание на
    экране и начисление обязаны править одной строкой."""
    from alma.billing.catalogue import PRODUCTS

    async def work(session):
        user = await _subscriber(session)
        return (await credits.state(session, user))["granted"]

    assert db(work) == PRODUCTS["sub.monthly"].pair_credits_monthly == 1


# ══════════════════════════════════════════════════════════════════════════
#  Трата — А7, случай 4
# ══════════════════════════════════════════════════════════════════════════

def test_the_included_check_becomes_an_ordinary_pair_grant(db):
    """Потраченный кредит неотличим от покупки везде, где спрашивают доступ.

    Отличается ровно одним — колонкой `source`, по которой «Мои пары» говорят
    «входит в подписку». Доступ от неё не зависит: отчёт открыт навсегда.
    """

    async def work(session):
        user = await _subscriber(session)
        grant = await credits.spend(session, user, "partner-1")
        access = await entitlements.check(
            session, user, "compatibility", partner_id="partner-1"
        )
        return grant.scope, grant.source, grant.expires_at, access.allowed

    scope, source, expires_at, allowed = db(work)
    assert scope == entitlements.SCOPE_PAIR
    assert source == "credit"
    assert expires_at is None, "оплаченный отчёт не истекает"
    assert allowed is True


def test_the_second_check_in_one_period_is_not_included(db):
    """**А7, случай 4.** Первая — включена, вторая — за деньги."""

    async def work(session):
        user = await _subscriber(session)
        first = await credits.spend(session, user, "partner-1")
        second = await credits.spend(session, user, "partner-2")
        return first is not None, second is not None, await credits.state(session, user)

    first, second, state = db(work)
    assert first is True
    assert second is False, "вторая проверка в том же цикле обязана быть платной"
    assert state["used"] == 1
    assert state["remaining"] == 0


def test_an_unused_credit_does_not_roll_over(db):
    """«1 проверка в этом месяце» — это обещание копирайта. Накопление
    превратило бы подписку в счёт, который однажды предъявят целиком."""

    async def work(session):
        user = await _subscriber(session, renews_in_days=31)
        await credits.ensure_period(session, user)          # период 1, не тронут
        plan = await _plan_of(session, user)
        plan.renews_at = utcnow() + timedelta(days=62)      # продление
        await session.flush()
        await credits.ensure_period(session, user)          # период 2
        return await credits.state(session, user)

    state = db(work)
    assert state["granted"] == 1, "неиспользованный кредит не переносится"
    assert state["used"] == 0


def test_a_renewal_opens_a_new_period_and_the_spend_starts_again(db):
    """Продление — единственное событие, которое возвращает включённую проверку."""

    async def work(session):
        user = await _subscriber(session, renews_in_days=31)
        await credits.spend(session, user, "partner-1")
        spent = await credits.state(session, user)

        plan = await _plan_of(session, user)
        plan.renews_at = utcnow() + timedelta(days=62)
        plan.expires_at = utcnow() + timedelta(days=62)
        await session.flush()
        await credits.ensure_period(session, user)

        renewed = await credits.state(session, user)
        again = await credits.spend(session, user, "partner-2")
        return spent, renewed, again is not None

    spent, renewed, again = db(work)
    assert spent["remaining"] == 0
    assert renewed["remaining"] == 1
    assert again is True


def test_the_same_renewal_delivered_twice_gives_one_credit(db):
    """Магазин доставляет как минимум однажды, а иногда дважды. Второй кредит
    за один платёж — это $4.99, розданные молча."""

    async def work(session):
        user = await _subscriber(session)
        first = await credits.ensure_period(session, user)
        second = await credits.ensure_period(session, user)
        rows = (await session.execute(
            __import__("sqlalchemy").select(PairCredit).where(PairCredit.user_id == user.id)
        )).scalars().all()
        return first.id == second.id, len(rows)

    same, count = db(work)
    assert same is True
    assert count == 1


# ══════════════════════════════════════════════════════════════════════════
#  Отмена и grace — А7, случай 5
# ══════════════════════════════════════════════════════════════════════════

def test_a_cancelled_period_keeps_its_credit_until_it_expires(db):
    """**А7, случай 5.** Отмена — не возврат: период оплачен, кредит в нём тоже.

    Отмена стирает `renews_at`, и границей становится `expires_at`. Ни новый
    кредит не начисляется (даты вперёд не двигались), ни старый не отбирается.
    """

    async def work(session):
        user = await _subscriber(session, renews_in_days=31)
        opened = await credits.ensure_period(session, user)

        plan = await _plan_of(session, user)
        plan.renews_at = None          # ровно то, что делает `_note_the_plan`
        plan.status = "cancelled"
        await session.flush()

        state = await credits.state(session, user)
        spent = await credits.spend(session, user, "partner-1")
        rows = (await session.execute(
            __import__("sqlalchemy").select(PairCredit).where(PairCredit.user_id == user.id)
        )).scalars().all()
        return opened.id, state, spent is not None, len(rows)

    _opened, state, spent, count = db(work)
    assert state["remaining"] == 1, "кредит доживает до конца оплаченного периода"
    assert spent is True
    assert count == 1, "отмена не открывает новый период"


def test_an_expired_subscription_has_no_credits_left(db):
    async def work(session):
        user = await _subscriber(session, renews_in_days=31)
        plan = await _plan_of(session, user)
        plan.renews_at = utcnow() - timedelta(days=1)
        plan.expires_at = utcnow() - timedelta(days=1)
        await session.flush()
        return await credits.state(session, user)

    assert db(work)["remaining"] == 0


def test_a_failed_payment_does_not_hand_out_a_new_credit(db):
    """Grace period, А5. Списание не прошло — значит период не начался.

    Потраченный при этом не отзывается: человек уже прочитал отчёт, и забирать
    его из-за того, что банк отклонил платёж, — наказание за чужую ошибку.
    """

    async def work(session):
        user = await _subscriber(session, renews_in_days=31)
        await credits.spend(session, user, "partner-1")

        plan = await _plan_of(session, user)
        # Dunning: срок доступа продлён на время попыток, дата списания — нет.
        plan.status = "past_due"
        plan.expires_at = utcnow() + timedelta(days=45)
        await session.flush()
        await credits.ensure_period(session, user)

        state = await credits.state(session, user)
        opened = await credits.spend(session, user, "partner-2")
        held = await entitlements.unlocked_pairs(session, user)
        return state, opened is not None, held

    state, opened, held = db(work)
    assert state["remaining"] == 0, "в grace новый кредит не начисляется"
    assert opened is False
    assert held == ["partner-1"], "потраченный кредит не отзывается"


# ══════════════════════════════════════════════════════════════════════════
#  Что события подписки не имеют права трогать — А7, случаи 6 и 7
# ══════════════════════════════════════════════════════════════════════════

def _revocation(*, subscription_id: str | None = None, transaction_id: str | None = None):
    """Событие, которое закрывает то, что называет: возврат или истечение."""
    return NormalisedEvent(
        provider="appstore",
        id=f"appstore:{transaction_id or subscription_id}",
        type="REFUND" if transaction_id else "EXPIRED",
        kind=EventKind.SUBSCRIPTION_ENDED,
        subscription_id=subscription_id,
        transaction_id=transaction_id,
        revokes=True,
    )


def test_a_refunded_pair_closes_that_report_and_no_other(db):
    """**А7, случай 6.** Возврат за одну пару не трогает вторую."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.pair_system("partner-1"),
            kind="consumable", transaction_id="txn_pair_1",
        )
        await entitlements.grant(
            session, user, system=entitlements.pair_system("partner-2"),
            kind="consumable", transaction_id="txn_pair_2",
        )
        closed = await billing_router._revoke_for(
            session, _revocation(transaction_id="txn_pair_1"), user
        )
        return closed, await entitlements.unlocked_pairs(session, user)

    closed, left = db(work)
    assert closed == 1
    assert left == ["partner-2"]


def test_a_refunded_bundle_leaves_a_door_that_was_bought_separately(db):
    """**А7, случай 7.** Возвращены деньги за бандл — дверь остаётся куплённой."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="txn_door",
        )
        await entitlements.grant(
            session, user, system=entitlements.EVERYTHING, kind="one_time",
            scope=entitlements.SCOPE_STATIC, transaction_id="txn_bundle",
        )
        closed = await billing_router._revoke_for(
            session, _revocation(transaction_id="txn_bundle"), user
        )
        return closed, await entitlements.unlocked_systems(session, user)

    closed, unlocked = db(work)
    assert closed == 1
    assert unlocked == {"natal"}, "дверь пережила возврат за бандл"


def test_an_expiring_subscription_leaves_static_and_pair_grants_alone(db):
    """Истечение подписки — это конец аренды, а не изъятие купленного.

    Строка «разборы, купленные навсегда, остаются твоими» стоит над кнопкой на
    экране подписки. Нарушить её можно одним лишним совпадением по
    `subscription_id`, и увидит это каждый подписчик в конце месяца.
    """

    async def work(session):
        user = await accounts.create_guest(session)
        # Строки собираются напрямую, а не через `grant()`, и это часть
        # постановки: `grant()` продлевает существующую подписку **на месте**,
        # поэтому три вызова с одним `subscription_id` дали бы одну строку, а
        # проверяется здесь именно случай, когда постоянный грант почему-то
        # несёт идентификатор подписки — миграция, ручная правка, смена схемы у
        # магазина. Он не должен встречаться и обязан быть безвредным.
        session.add_all([
            Entitlement(
                user_id=user.id, system=entitlements.EVERYTHING,
                kind=EntitlementKind.monthly.value, scope=entitlements.SCOPE_ALL,
                subscription_id="sub_1", transaction_id="txn_plan",
                expires_at=utcnow() + timedelta(days=31), source="appstore",
            ),
            Entitlement(
                user_id=user.id, system=entitlements.EVERYTHING, kind="one_time",
                scope=entitlements.SCOPE_STATIC, subscription_id="sub_1",
                transaction_id="txn_bundle",
            ),
            Entitlement(
                user_id=user.id, system=entitlements.pair_system("partner-1"),
                kind="consumable", scope=entitlements.SCOPE_PAIR,
                subscription_id="sub_1", transaction_id="txn_pair",
            ),
        ])
        await session.flush()

        closed = await billing_router._revoke_for(
            session, _revocation(subscription_id="sub_1", transaction_id="txn_plan"), user
        )
        return (
            closed,
            await entitlements.unlocked_systems(session, user),
            await entitlements.unlocked_pairs(session, user),
        )

    closed, unlocked, pairs = db(work)
    assert closed == 1, "закрыт только сам план"
    assert unlocked == entitlements.STATIC_SYSTEMS
    assert pairs == ["partner-1"]


def test_a_plan_notice_never_writes_a_renewal_date_onto_a_door(db):
    """`_note_the_plan` тоже ходит по `subscription_id`. Дверь с `renews_at`
    заставила бы экран аккаунта обещать списание за купленное навсегда."""

    async def work(session):
        user = await accounts.create_guest(session)
        door = await entitlements.grant(
            session, user, system="natal", kind="one_time",
            subscription_id="sub_1", transaction_id="txn_door",
        )
        noted = await billing_router._note_the_plan(
            session,
            NormalisedEvent(
                provider="appstore", id="evt", type="DID_CHANGE_RENEWAL_STATUS",
                kind=EventKind.SUBSCRIPTION_CANCELLED, subscription_id="sub_1",
                status="cancelled",
            ),
            user,
        )
        return noted, door.status, door.renews_at

    noted, status, renews_at = db(work)
    assert noted == 0
    assert status is None
    assert renews_at is None
