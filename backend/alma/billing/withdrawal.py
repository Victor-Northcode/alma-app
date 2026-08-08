"""Executing a withdrawal from a plan, which nothing could do.

The refunds page promises the Art. 14(3) remedy: withdraw from a year inside
fourteen days and what comes back is the part of the period not used, and the
plan ends there. The first half is a refund somebody issues in the processor's
dashboard. **The second half had no code at all.**

A pro-rata refund is a *partial* refund, and a partial refund deliberately
revokes nothing — `NormalisedEvent.closes_the_grant` is true only for a full
return, because somebody refunded five dollars of a thirty-nine dollar archive
keeps the archive. That rule is right and is not what this changes. What it
means, though, is that the one remedy the page promises for the annual could not
be carried out: the money went back and the plan kept granting until its own
expiry, and there was no route anywhere that called `entitlements.revoke`. In
practice that made the promise a hand-written database change nobody had
written down.

So this is the revocation step, and it is deliberately **a command and not an
endpoint**. Ending somebody's paid access is the most destructive thing this
system can do to a customer, there is no operator credential in `config.py` to
put in front of an HTTP route, and an unauthenticated one would be a button
anybody on the internet could press. A person at a terminal, naming one
subscription, is the right shape for a remedy that is exercised a handful of
times a year and always alongside a refund issued by hand.

It refuses to guess. It will not find the subscription from an email address, it
will not revoke every plan an account holds, and it prints what it is about to
do and asks before doing it unless told otherwise — because the failure mode of
the opposite is a paying subscriber locked out by a typo.

    python -m alma.billing.withdrawal sub_01hz…            # ask first
    python -m alma.billing.withdrawal sub_01hz… --yes      # in a script
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import entitlements
from ..db.models import Entitlement, Purchase, as_utc, utcnow

log = logging.getLogger("alma.billing.withdrawal")


@dataclass(frozen=True, slots=True)
class Withdrawal:
    """What one plan looks like at the moment of being withdrawn from.

    A record rather than the `Entitlement` so that the arithmetic is testable
    without a database and so that the operator sees the same numbers the
    refund is calculated from. `unused_cents` is stated rather than charged:
    the money is returned by the merchant of record, not by us, and this is the
    figure to type into their dashboard.
    """

    subscription_id: str
    user_id: str
    kind: str
    amount_cents: int
    currency: str
    granted_at: datetime
    expires_at: datetime | None
    days_used: int
    days_total: int

    @property
    def unused_cents(self) -> int:
        """The part of the period that has not been performed, in minor units.

        Rounded **down**, so a rounding error is a cent in the customer's
        favour rather than a cent of ours they have to ask for. Zero days used
        returns the whole amount; a period already over returns nothing, which
        is the case where a withdrawal is out of time anyway.
        """
        if self.days_total <= 0 or self.amount_cents <= 0:
            return 0
        left = max(self.days_total - self.days_used, 0)
        return self.amount_cents * left // self.days_total


async def prepare(session: AsyncSession, subscription_id: str, *, at: datetime | None = None):
    """The one plan this subscription id names, and the sum owed on it.

    Returns `None` when nothing matches, which is a real answer rather than an
    error: an operator typing an id from a support ticket needs to be told the
    id is wrong, not handed a stack trace.

    The amount comes from the grant where that column holds one and from the
    money trail where it does not — the same fallback the renewal notice uses,
    and for the same reason: on one processor a subscription grant is written
    from a zero-amount event on purpose.
    """
    moment = at or utcnow()
    held = (
        await session.execute(
            select(Entitlement).where(Entitlement.subscription_id == subscription_id)
        )
    ).scalars().first()
    if held is None:
        return None

    amount, currency = held.amount_cents or 0, held.currency or "USD"
    if not amount:
        paid = (
            await session.execute(
                select(Purchase)
                .where(
                    Purchase.subscription_id == subscription_id,
                    Purchase.amount_cents > 0,
                )
                .order_by(Purchase.created_at.desc())
                .limit(1)
            )
        ).scalars().first()
        if paid is not None:
            amount, currency = paid.amount_cents, paid.currency or currency

    granted = as_utc(held.granted_at) or moment
    expires = as_utc(held.expires_at)
    total = max((expires - granted).days, 0) if expires else 0
    used = max((moment - granted).days, 0)
    return Withdrawal(
        subscription_id=subscription_id,
        user_id=held.user_id,
        kind=held.kind,
        amount_cents=amount,
        currency=currency,
        granted_at=granted,
        expires_at=expires,
        days_used=min(used, total) if total else used,
        days_total=total,
    )


async def execute(session: AsyncSession, subscription_id: str) -> int:
    """End every grant this subscription wrote. Returns how many.

    `revoke` and not a delete: the row stays and `revoked_at` is set, so the
    money trail and the access trail still line up afterwards and support can
    see that access ended rather than that it never existed. `renews_at` is
    cleared as well, because a withdrawn plan that still advertises a charge on
    the account screen is the sentence that produces a chargeback.
    """
    rows = (
        await session.execute(
            select(Entitlement).where(Entitlement.subscription_id == subscription_id)
        )
    ).scalars().all()
    for held in rows:
        held.renews_at = None
        held.status = "withdrawn"
        await entitlements.revoke(session, held)
    if rows:
        log.info("withdrew %s — %d grant(s) revoked", subscription_id, len(rows))
    return len(rows)


def _describe(plan: Withdrawal) -> str:
    from .catalogue import format_price

    return (
        f"subscription {plan.subscription_id}\n"
        f"  account      {plan.user_id}\n"
        f"  plan         {plan.kind}\n"
        f"  paid         {format_price(plan.amount_cents, plan.currency)}\n"
        f"  period       {plan.days_used} of {plan.days_total} days used\n"
        f"  owed back    {format_price(plan.unused_cents, plan.currency)}"
        " (ask the merchant of record to return this)\n"
        f"  access ends  immediately, on confirming"
    )


async def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m alma.billing.withdrawal",
        description="End a subscription because the buyer withdrew from it.",
    )
    parser.add_argument("subscription_id", help="the processor's subscription id")
    parser.add_argument(
        "--yes", action="store_true",
        help="do it without asking — for a script, never for a first attempt",
    )
    args = parser.parse_args(argv)

    from ..db.session import session_scope

    async with session_scope() as session:
        plan = await prepare(session, args.subscription_id)
        if plan is None:
            print(f"no subscription here with the id {args.subscription_id!r}")
            return 1
        print(_describe(plan))
        if not args.yes:
            # Typed in full rather than "y". The cost of the wrong answer here
            # is a paying customer locked out of something they still own.
            if input("\ntype 'withdraw' to end this plan: ").strip() != "withdraw":
                print("nothing changed")
                return 1
        revoked = await execute(session, args.subscription_id)
        print(f"revoked {revoked} grant(s); the refund itself is issued by the merchant")
    return 0


if __name__ == "__main__":  # pragma: no cover - the operator's entry point
    raise SystemExit(asyncio.run(_main()))
