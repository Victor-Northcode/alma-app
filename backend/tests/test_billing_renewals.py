"""The email before a renewal — the one honesty claim that had no code.

Four shipped surfaces say this happens: the subscription-terms page, the
honesty plate under the pay button, the same plate on the landing, and the
account screen. Nothing sent it. A customer silently charged $78.99 a year
after a purchase has been told in writing that this could not happen and told
why we would never do it, and the page they read it on is what they will attach
to the chargeback.

So every test here is about a person being warned, or about not being warned
twice. What is deliberately *not* tested is the wording — that lives in six
locales and changes; what must not change is who gets a letter and when.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from conftest import database_url, run_async

from alma.billing import renewals
from alma.db.models import Entitlement, User, new_id, utcnow


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A database of our own, with no HTTP anywhere near it."""
    from alma import config as config_module
    from alma.db import session as session_module

    # Disposed before the URL is chosen: on Postgres `database_url` empties
    # the schema, and a connection still pooled from the previous test would
    # turn that drop into a lock wait.
    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "renew.db"))
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()
    run_async(session_module.create_all)
    yield session_module
    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


def _plan(session, *, email: str | None, days: float, kind: str = "annual",
          revoked: bool = False, renews: bool = True) -> tuple[User, Entitlement]:
    moment = utcnow()
    # The id is minted here rather than at INSERT: the entitlement needs it
    # before anything is flushed.
    user = User(id=new_id(), email=email,
                provider="magic" if email else "guest", locale="en")
    session.add(user)
    held = Entitlement(
        user_id=user.id,
        system="*",
        kind=kind,
        scope="all",
        expires_at=moment + timedelta(days=365),
        renews_at=moment + timedelta(days=days) if renews else None,
        revoked_at=moment if revoked else None,
        subscription_id=f"sub_{user.id[:6]}",
        amount_cents=7899,
        currency="USD",
        source="paddle",
    )
    session.add(held)
    return user, held


def _run(db, work):
    async def go():
        async with db.session_scope() as session:
            return await work(session)

    return run_async(go)


class _Postbox:
    """A mail provider that accepts, or does not, and remembers what it was given."""

    def __init__(self, accepts: bool = True) -> None:
        self.accepts = accepts
        self.sent: list = []

    async def __call__(self, notice) -> bool:
        self.sent.append(notice)
        return self.accepts


@pytest.fixture
def postbox(monkeypatch) -> _Postbox:
    from alma import mail

    box = _Postbox()
    monkeypatch.setattr(mail, "send_renewal_notice", box)
    return box


def test_a_plan_billing_in_three_days_is_written_to(db, postbox):
    def work(session):
        _plan(session, email="sofia@example.com", days=3)
        return renewals.send_due_notices(session)

    outcome = _run(db, work)
    assert outcome["sent"] == 1
    assert postbox.sent[0].email == "sofia@example.com"
    assert postbox.sent[0].amount_cents == 7899


def test_a_plan_billing_next_month_is_left_alone(db, postbox):
    """A notice three weeks early is a notice nobody connects to the charge."""
    def work(session):
        _plan(session, email="sofia@example.com", days=30)
        return renewals.send_due_notices(session)

    assert _run(db, work)["sent"] == 0
    assert postbox.sent == []


def test_the_window_is_a_range_so_a_missed_day_still_warns(db, postbox):
    """A job that asked for renewals *exactly* three days out sends nothing at
    all on the day it did not run, and nobody finds out until a customer does.

    Anything from two to four days out is inside the window, and a notice a day
    early is better than silence. The values here sit inside the boundary rather
    than on it, because a test that lands exactly on `now + 2 days` is a test
    decided by the microseconds between building the row and running the query.
    """
    for days in (2.5, 3.5):
        def work(session, days=days):
            _plan(session, email=f"buyer{days}@example.com", days=days)
            return renewals.send_due_notices(session)

        assert _run(db, work)["sent"] == 1, days


def test_nobody_is_warned_twice_about_one_charge(db, postbox):
    """Three emails about one charge reads as a system out of control."""
    def work(session):
        _plan(session, email="sofia@example.com", days=3)
        first = renewals.send_due_notices(session)
        return first

    assert _run(db, work)["sent"] == 1

    def again(session):
        return renewals.send_due_notices(session)

    outcome = _run(db, again)
    assert outcome["sent"] == 0 and outcome["already"] == 1
    assert len(postbox.sent) == 1


def test_a_send_that_failed_is_tried_again_rather_than_recorded(db, monkeypatch):
    """The dangerous order is marking first.

    A notice recorded as sent and never delivered is somebody charged with no
    warning at all, which is the exact outcome the promise is about. So the row
    is written only after the provider accepted, and a refusal leaves the next
    run something to do.
    """
    from alma import mail

    refuses = _Postbox(accepts=False)
    monkeypatch.setattr(mail, "send_renewal_notice", refuses)

    def work(session):
        _plan(session, email="sofia@example.com", days=3)
        return renewals.send_due_notices(session)

    assert _run(db, work)["failed"] == 1

    accepts = _Postbox(accepts=True)
    monkeypatch.setattr(mail, "send_renewal_notice", accepts)
    assert _run(db, lambda s: renewals.send_due_notices(s))["sent"] == 1


def test_somebody_who_cancelled_is_not_told_we_are_about_to_charge_them(db, postbox):
    """`renews_at` is cleared on a cancellation and `expires_at` is not.

    Reading the expiry here would email a person who has just cancelled to say
    their card is about to be charged — which reads as the cancellation having
    failed, and the next thing they do is a chargeback.
    """
    def work(session):
        _plan(session, email="sofia@example.com", days=3, renews=False)
        return renewals.send_due_notices(session)

    assert _run(db, work)["due"] == 0
    assert postbox.sent == []


def test_a_revoked_plan_is_not_warned_about(db, postbox):
    def work(session):
        _plan(session, email="sofia@example.com", days=3, revoked=True)
        return renewals.send_due_notices(session)

    assert _run(db, work)["due"] == 0


def test_a_guest_is_warned_at_the_address_they_paid_with(db, postbox):
    """"Email before renewal" was printed loudest where it was least true.

    It is on the honesty plate beside the pay button, on the paywall and in the
    FAQ — and `due()` skipped any account with no address, which is exactly the
    guest reading it there. The processor collected one to take the money with
    and the webhook keeps it on the purchase, so there is somewhere to write
    after all. Never `User.email`: that column is the sign-in identity.
    """
    async def work(session):
        from alma.db.models import Purchase

        user, held = _plan(session, email=None, days=3)
        await session.flush()
        session.add(Purchase(
            user_id=user.id, transaction_id="txn_guest",
            subscription_id=held.subscription_id, amount_cents=7899,
            currency="USD", buyer_email="paid.with@example.com",
            completed_at=utcnow() - timedelta(days=362),
        ))
        return await renewals.due(session)

    due = _run(db, work)
    assert [n.email for n in due] == ["paid.with@example.com"]


def test_a_guest_with_no_address_is_counted_rather_than_crashed_on(db, postbox):
    """Somebody who bought a subscription without signing in cannot be written to.

    Not an error and not a silent skip: the honest fix is upstream, at the
    checkout, and that decision needs the number to be visible.
    """
    def work(session):
        _plan(session, email=None, days=3)
        return renewals.send_due_notices(session)

    outcome = _run(db, work)
    assert outcome == {"due": 0, "sent": 0, "already": 0, "failed": 0}
    assert postbox.sent == []


def test_a_plan_whose_grant_carries_no_amount_is_priced_from_the_money(db, postbox):
    """The letter's whole job is the amount, so it comes from what was paid.

    `Entitlement.amount_cents` is written from the granting event, and on one of
    the two processors the granting event for a subscription is deliberately a
    zero-amount one — `subscription.active` carries no total, because the money
    arrives on its own `payment.succeeded`. So the column stayed at nought for
    the life of every plan on that processor, and this letter would have said
    "$0.00 will be charged" three days before taking $78.99. A price quoted in
    writing that disagrees with the one taken is the exact surprise the notice
    exists to prevent.
    """
    async def work(session):
        from alma.db.models import Purchase

        user, held = _plan(session, email="sofia@example.com", days=3)
        held.amount_cents = 0
        # Flushed before the money row: the purchase points at the user, and a
        # foreign key cannot be satisfied by a row still sitting in the session.
        await session.flush()
        session.add(Purchase(
            user_id=user.id, transaction_id="txn_sub_1",
            subscription_id=held.subscription_id, amount_cents=7899,
            currency="USD", completed_at=utcnow() - timedelta(days=362),
        ))
        return await renewals.due(session)

    due = _run(db, work)
    assert [(n.amount_cents, n.currency) for n in due] == [(7899, "USD")]


def test_a_notice_that_cannot_name_the_amount_is_not_sent(db, postbox):
    """Silence is better than a nought, and both are worse than the fix.

    There is no grant amount and no payment to read one off, so there is no
    honest sentence to send. Logged at error rather than shrugged at: a run of
    these means subscriptions are renewing with no warning at all.
    """
    def work(session):
        user, held = _plan(session, email="sofia@example.com", days=3)
        held.amount_cents = 0
        return renewals.due(session)

    assert _run(db, work) == []


def test_the_key_carries_the_date_so_next_month_is_a_different_notice(db):
    """A key without the renewal date sends one letter ever, then goes quiet
    for the life of the subscription — which looks exactly like working."""
    moment = utcnow()
    first = renewals.Notice(
        entitlement_id="e1", user_id="u1", email="a@b.c", locale="en",
        renews_at=moment, amount_cents=999, currency="USD", kind="monthly",
    )
    next_month = renewals.Notice(
        entitlement_id="e1", user_id="u1", email="a@b.c", locale="en",
        renews_at=moment + timedelta(days=31), amount_cents=999, currency="USD",
        kind="monthly",
    )
    assert first.key != next_month.key


def test_the_amount_is_written_the_way_the_statement_will_show_it(monkeypatch):
    """A Brazilian shown "R$78.99" is being shown something that is not a price,
    and this number is the one that appears on a card statement."""
    from alma import mail

    body = mail._renewal_html(
        date="2026-09-06", amount="R$ 219,00", url="https://x", locale="pt-BR"
    )
    assert "R$ 219,00" in body
    assert "2026-09-06" in body


def test_the_notice_offers_no_unsubscribe(monkeypatch):
    """It is not marketing. An unsubscribe link here turns the promise back into
    the trick it was made against, and the letter says so in its own words."""
    body = mail_html()
    lowered = body.lower()
    assert "unsubscribe" not in lowered or "nothing to unsubscribe" in lowered


def mail_html() -> str:
    from alma import mail

    return mail._renewal_html(
        date="2026-09-06", amount="$78.99", url="https://x", locale="en"
    )
