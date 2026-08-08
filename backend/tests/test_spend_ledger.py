"""The cumulative ledger — the ceiling the per-call guard cannot enforce.

Every call this product makes is cheap. A chat turn on the cheapest model is
under half a cent, and the per-call guard exists to catch a prompt that grew
or a `max_tokens` somebody raised — it has never once been the thing standing
between us and a bill, because no single call is ever expensive enough to trip
it. What can empty the account is repetition: an account making the same
individually-harmless call all day, every day, forever.

So these tests are about arithmetic that spans calls. The rules asserted here
are: spend accumulates per account and per calendar month and nothing else;
it is stored in cents and compared in dollars, and the conversion happens
exactly once; a month is a calendar month, including the one that ends the
year; and paying us money can only ever raise the ceiling.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from conftest import database_url, run_async

from alma.ai import cost
from alma.auth import accounts
from alma.db import session as session_module
from alma.db.models import UsageCounter


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A fresh database, driven synchronously through a small runner."""
    from alma import config as config_module

    # Disposed before the URL is chosen: on Postgres `database_url` empties
    # the schema, and a connection still pooled from the previous test would
    # turn that drop into a lock wait.
    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "ledger.db"))
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


@pytest.fixture
def ceilings(monkeypatch):
    """Set the monthly ceilings for one test.

    Returned as a setter because the ceilings are validated against each other
    at load — a test that lowers one in isolation is a test that would ship a
    configuration the service refuses to start with.
    """
    from alma import config as config_module

    def apply(*, free: float, owner: float, subscriber: float) -> None:
        monkeypatch.setenv("ALMA_FREE_MONTH_BUDGET", str(free))
        monkeypatch.setenv("ALMA_OWNER_MONTH_BUDGET", str(owner))
        monkeypatch.setenv("ALMA_SUBSCRIBER_MONTH_BUDGET", str(subscriber))
        config_module.settings.cache_clear()

    yield apply
    config_module.settings.cache_clear()


async def _record(session, user, cents: float, *, day: date | None = None) -> None:
    """Add spend the way the request path does: one row per user per day."""
    when = day or datetime.now(timezone.utc).date()
    key = f"{user.id}:{when.isoformat()}:{cost.SPEND_METRIC}"
    row = await session.get(UsageCounter, key)
    if row is None:
        row = UsageCounter(
            id=key, user_id=user.id, day=when, metric=cost.SPEND_METRIC, count=0, amount=0.0
        )
        session.add(row)
    row.count = (row.count or 0) + 1
    row.amount = (row.amount or 0.0) + cents
    await session.flush()


# ── what counts, and what does not ─────────────────────────────────────────

def test_an_account_that_has_done_nothing_has_cost_nothing(db):
    async def work(session):
        user = await accounts.create_guest(session)
        return await cost.month_spend(session, user)

    assert db(work) == 0.0


def test_spend_is_stored_in_cents_and_answered_in_dollars(db):
    """The one place the two units meet. A hundredfold error here is a bill."""
    async def work(session):
        user = await accounts.create_guest(session)
        await _record(session, user, 45.0)          # 45 cents
        return await cost.month_spend(session, user)

    assert db(work) == pytest.approx(0.45)


def test_a_days_calls_add_up_and_so_do_the_days(db):
    async def work(session):
        user = await accounts.create_guest(session)
        today = datetime.now(timezone.utc).date()
        await _record(session, user, 1.5)
        await _record(session, user, 1.5)
        await _record(session, user, 2.0, day=today.replace(day=1))
        return await cost.month_spend(session, user)

    assert db(work) == pytest.approx(0.05)


def test_last_months_spend_is_not_charged_to_this_month(db):
    """A ceiling that never resets is a ban, not a budget."""
    async def work(session):
        user = await accounts.create_guest(session)
        first_of_this_month = datetime.now(timezone.utc).date().replace(day=1)
        await _record(session, user, 900.0, day=first_of_this_month - timedelta(days=1))
        await _record(session, user, 3.0)
        return await cost.month_spend(session, user)

    assert db(work) == pytest.approx(0.03)


def test_one_account_is_never_billed_for_another(db):
    async def work(session):
        mine = await accounts.create_guest(session)
        theirs = await accounts.create_guest(session)
        await _record(session, theirs, 400.0)
        return await cost.month_spend(session, mine)

    assert db(work) == 0.0


def test_only_money_is_counted_not_the_other_counters(db):
    """`UsageCounter` holds questions asked and downsells offered too.

    Those rows carry an `amount` column like every other row. Summing the
    table without filtering on the metric would price a question at a dollar.
    """
    async def work(session):
        user = await accounts.create_guest(session)
        today = datetime.now(timezone.utc).date()
        session.add(
            UsageCounter(
                id=f"{user.id}:{today.isoformat()}:questions",
                user_id=user.id, day=today, metric="questions", count=3, amount=999.0,
            )
        )
        await session.flush()
        return await cost.month_spend(session, user)

    assert db(work) == 0.0


def test_the_ledger_reads_exactly_what_the_request_path_writes(db):
    """The write and the read must agree about the unit, or nothing else here holds.

    Deliberately imports the router's own writer rather than reproducing it:
    a test that records spend its own way and then reads it back is a test
    that agrees with itself and proves nothing about production.
    """
    from alma.api.routers.readings import _spend

    spend = cost.cost("claude-haiku-4-5", 3000, 900)

    async def work(session):
        user = await accounts.create_guest(session)
        await _spend(session, user, spend.cents)
        return await cost.month_spend(session, user)

    assert db(work) == pytest.approx(spend.dollars)


# ── the guard ──────────────────────────────────────────────────────────────

def test_cheap_calls_that_no_per_call_guard_would_stop_still_run_out(db, ceilings):
    """The whole reason this module exists.

    Seventy-five chat turns on the cheapest model, each costing well under a
    cent. Every one of them passes the per-call guard with room to spare —
    that guard looks at one call, and one call is never the problem. The
    seventy-sixth is refused, entirely because of what the others cost.
    """
    ceilings(free=0.45, owner=0.70, subscriber=1.00)
    turn = cost.estimate("claude-haiku-4-5", prompt_chars=12_000, max_output_tokens=600)
    assert turn < 0.05, "a chat turn must be far below the per-call ceiling for this to mean anything"

    async def work(session):
        user = await accounts.create_guest(session)
        for _ in range(75):
            cost.guard(
                "claude-haiku-4-5", prompt_chars=12_000, max_output_tokens=600, paid=False
            )
            await _record(session, user, turn * 100.0)
        # The per-call guard is still perfectly happy with the next one.
        cost.guard("claude-haiku-4-5", prompt_chars=12_000, max_output_tokens=600, paid=False)
        with pytest.raises(cost.BudgetExceeded):
            await cost.guard_month(session, user, tier="free", projected=turn)

    db(work)


def test_the_guard_weighs_the_month_not_the_call(db, ceilings):
    """A two-cent call is refused at $0.44 spent and allowed at $0.10."""
    ceilings(free=0.45, owner=0.70, subscriber=1.00)

    async def work(session):
        thin = await accounts.create_guest(session)
        await _record(session, thin, 10.0)
        await cost.guard_month(session, thin, tier="free", projected=0.02)

        full = await accounts.create_guest(session)
        await _record(session, full, 44.0)
        with pytest.raises(cost.BudgetExceeded, match="ceiling"):
            await cost.guard_month(session, full, tier="free", projected=0.02)

    db(work)


def test_paying_can_only_ever_raise_the_ceiling(db, ceilings):
    """The same account, the same spend, three tiers — an upgrade never takes away."""
    ceilings(free=0.45, owner=0.70, subscriber=1.00)

    async def work(session):
        user = await accounts.create_guest(session)
        await _record(session, user, 50.0)          # $0.50 this month

        with pytest.raises(cost.BudgetExceeded):
            await cost.guard_month(session, user, tier="free", projected=0.02)
        await cost.guard_month(session, user, tier="owner", projected=0.02)
        await cost.guard_month(session, user, tier="subscriber", projected=0.02)

        await _record(session, user, 25.0)          # $0.75 this month
        with pytest.raises(cost.BudgetExceeded):
            await cost.guard_month(session, user, tier="owner", projected=0.02)
        await cost.guard_month(session, user, tier="subscriber", projected=0.02)

    db(work)


def test_a_tier_nobody_recognises_is_charged_the_free_allowance(db, ceilings):
    """The conservative answer is the only one that cannot cost money."""
    ceilings(free=0.45, owner=0.70, subscriber=1.00)
    assert cost.month_ceiling("nonsense") == cost.month_ceiling("free")

    async def work(session):
        user = await accounts.create_guest(session)
        await _record(session, user, 50.0)
        with pytest.raises(cost.BudgetExceeded):
            await cost.guard_month(session, user, tier="nonsense", projected=0.02)

    db(work)


def test_the_guard_refuses_before_the_call_rather_than_reporting_after(db, ceilings):
    """The projection is part of the sum. A ceiling checked on spent-so-far
    alone always allows one more call, and that call is the expensive one."""
    ceilings(free=0.45, owner=0.70, subscriber=1.00)

    async def work(session):
        user = await accounts.create_guest(session)
        await _record(session, user, 40.0)          # $0.40, still under $0.45
        await cost.guard_month(session, user, tier="free", projected=0.01)
        with pytest.raises(cost.BudgetExceeded):
            await cost.guard_month(session, user, tier="free", projected=0.30)

    db(work)


# ── the month itself ───────────────────────────────────────────────────────

def test_december_rolls_into_january():
    """Month arithmetic that adds one to the month number breaks once a year."""
    first, following = cost.month_bounds(datetime(2025, 12, 15, tzinfo=timezone.utc))
    assert first == date(2025, 12, 1)
    assert following == date(2026, 1, 1)


def test_february_ends_where_february_ends():
    """The upper bound is found by stepping into the next month, so no month
    length — leap year or otherwise — has to be known here."""
    assert cost.month_bounds(datetime(2024, 2, 29, tzinfo=timezone.utc)) == (
        date(2024, 2, 1), date(2024, 3, 1),
    )
    assert cost.month_bounds(datetime(2025, 2, 3, tzinfo=timezone.utc)) == (
        date(2025, 2, 1), date(2025, 3, 1),
    )


def test_the_last_day_of_the_month_is_inside_the_month(db):
    """The half-open bound exists so that this day is not silently free."""
    async def work(session):
        user = await accounts.create_guest(session)
        _first, following = cost.month_bounds()
        await _record(session, user, 12.0, day=following - timedelta(days=1))
        return await cost.month_spend(session, user)

    assert db(work) == pytest.approx(0.12)


# ── the ceilings themselves ────────────────────────────────────────────────

def test_monthly_ceilings_that_cross_are_refused_at_startup(monkeypatch):
    """An upgrade that lowers somebody's allowance must not be deployable.

    It is a configuration mistake with no visible symptom until a subscriber
    is cut off sooner than a free user was, so it is caught where it is made.
    """
    from pydantic import ValidationError

    from alma.config import Settings

    monkeypatch.setenv("ALMA_FREE_MONTH_BUDGET", "0.90")
    monkeypatch.setenv("ALMA_OWNER_MONTH_BUDGET", "0.70")
    monkeypatch.setenv("ALMA_SUBSCRIBER_MONTH_BUDGET", "1.00")
    with pytest.raises(ValidationError, match="must not cross"):
        Settings()


def test_a_ceiling_of_zero_is_refused(monkeypatch):
    """Almost always a mistyped variable, and it fails as a service that
    silently declines to write anything for anyone."""
    from pydantic import ValidationError

    from alma.config import Settings

    monkeypatch.setenv("ALMA_FREE_MONTH_BUDGET", "0")
    with pytest.raises(ValidationError, match="refuses everything"):
        Settings()
