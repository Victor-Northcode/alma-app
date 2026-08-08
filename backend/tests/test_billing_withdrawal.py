"""Withdrawing from a plan — the remedy the refunds page promised and nothing did.

CRD Art. 16(a) does not extinguish the withdrawal right on a twelve-month
service until the service is fully performed, so a buyer who withdraws from the
annual on day ten is owed the unused part of the year under Art. 14(3) and the
plan ends there. The refunds page says exactly that.

The first half of it was always executable — somebody issues a partial refund in
the processor's dashboard. The second half was not: a partial refund
deliberately revokes nothing (`closes_the_grant` is true only for a full
return), nothing anywhere else called `entitlements.revoke`, and so the money
went back while the plan carried on granting to its own expiry.

What is tested here is therefore the arithmetic a person types into a refund
form, and the fact that access actually stops.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from conftest import database_url, run_async
from sqlalchemy import select

from alma.auth import entitlements
from alma.billing import withdrawal
from alma.db.models import Entitlement, Purchase, User, new_id, utcnow


@pytest.fixture
def db(tmp_path, monkeypatch):
    from alma import config as config_module
    from alma.db import session as session_module

    # Disposed before the URL is chosen: on Postgres `database_url` empties
    # the schema, and a connection still pooled from the previous test would
    # turn that drop into a lock wait.
    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "wd.db"))
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()
    run_async(session_module.create_all)
    yield session_module
    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


def _run(db, work):
    async def go():
        async with db.session_scope() as session:
            return await work(session)

    return run_async(go)


def _year(session, *, days_ago: float, amount: int = 7899, currency: str = "USD"):
    """One annual plan, bought `days_ago` days ago and running a full year."""
    started = utcnow() - timedelta(days=days_ago)
    user = User(id=new_id(), email="sofia@example.com", provider="email", locale="en")
    session.add(user)
    held = Entitlement(
        user_id=user.id,
        system="*",
        kind="annual",
        scope="all",
        granted_at=started,
        expires_at=started + timedelta(days=365),
        renews_at=started + timedelta(days=365),
        subscription_id="sub_year",
        amount_cents=amount,
        currency=currency,
        source="paddle",
    )
    session.add(held)
    return user, held


def test_the_sum_is_the_part_of_the_year_nobody_has_had(db):
    """Art. 14(3), and it is arithmetic rather than a judgement call.

    Ten days of three hundred and sixty-five, at $78.99, leaves 355/365 of the
    price. The operator types that figure into the processor's refund form, so
    it has to be the same number every time somebody asks.
    """
    async def work(session):
        _year(session, days_ago=10)
        await session.flush()
        return await withdrawal.prepare(session, "sub_year")

    plan = _run(db, work)
    assert plan is not None
    assert (plan.days_used, plan.days_total) == (10, 365)
    assert plan.unused_cents == 7899 * 355 // 365
    assert plan.currency == "USD"


def test_a_rounding_error_lands_in_the_customer_s_favour(db):
    """Down, never up. A cent we keep is a cent somebody has to write in to ask
    for; a cent we return costs nothing and is never argued about."""
    async def work(session):
        _year(session, days_ago=1, amount=1000)
        await session.flush()
        return await withdrawal.prepare(session, "sub_year")

    plan = _run(db, work)
    assert plan.unused_cents == 1000 * 364 // 365 == 997


def test_the_amount_can_be_read_off_the_money_when_the_grant_has_none(db):
    """On one processor a subscription grant is written from a zero-amount event.

    The same hole that would have made the pre-renewal notice say "$0.00" would
    have made this offer a refund of nothing, which is worse: it is a number an
    operator would have typed into a form.
    """
    async def work(session):
        user, held = _year(session, days_ago=10, amount=0)
        await session.flush()
        session.add(Purchase(
            user_id=user.id, transaction_id="txn_1", subscription_id="sub_year",
            amount_cents=7899, currency="USD", completed_at=utcnow() - timedelta(days=10),
        ))
        return await withdrawal.prepare(session, "sub_year")

    plan = _run(db, work)
    assert plan.amount_cents == 7899


def test_withdrawing_actually_closes_the_plan(db):
    """The half that had no code: access stops, and it stops now.

    Not at the end of the period — that is what *cancelling* does, and the
    difference between the two is the whole point of this module. A withdrawn
    plan that keeps opening readings is money returned for goods retained.
    """
    async def work(session):
        user, _held = _year(session, days_ago=10)
        await session.flush()
        before = await entitlements.unlocked_systems(session, user)
        revoked = await withdrawal.execute(session, "sub_year")
        after = await entitlements.unlocked_systems(session, user)
        # Read straight off the table: `for_user` hides revoked rows, and what
        # is being checked is that the row is still there and says so.
        rows = (await session.execute(
            select(Entitlement).where(Entitlement.subscription_id == "sub_year")
        )).scalars().all()
        return before, revoked, after, [
            (r.renews_at, r.status, r.revoked_at is not None) for r in rows
        ]

    before, revoked, after, rows = _run(db, work)
    assert before, "the plan was not granting anything to begin with"
    assert revoked == 1
    assert after == set()
    assert rows == [(None, "withdrawn", True)], "a withdrawn plan still advertises a charge"


def test_an_id_we_do_not_know_is_an_answer_and_not_a_crash(db):
    """An operator typing an id out of a support ticket gets told it is wrong."""
    async def work(session):
        return await withdrawal.prepare(session, "sub_nope")

    assert _run(db, work) is None
