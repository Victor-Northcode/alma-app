"""The email that goes out before a subscription renews.

This exists because the product promises it, in writing, on the screen where
the money is taken. The honesty plate under the pay button says "email before
renewal"; the subscription-terms page says an email goes out three days before
every renewal, "not a marketing email and you cannot unsubscribe from it,
because a subscription you have forgotten about is the oldest trick in this
industry and we would rather not be in that business"; and the account screen
says "we email you 3 days before". None of that was true. `alma/mail.py` had one
sender in it and there was no scheduled job of any kind.

That is the worst shape a claim can have. A person silently charged $78.99
twelve months after a purchase they made as a guest has been told in writing
that this could not happen, *and* told why we would never do it — and the policy
page they were told it on is the document they will attach to the chargeback.

Three decisions are worth writing down.

**It is not marketing and there is no unsubscribe.** A transactional notice
about money that is about to leave somebody's account is not a newsletter, and
an unsubscribe link on it would turn the promise back into the trick. That is
also why it does not go through any list, segment or preference: it is sent to
the address on the account, for one plan, once.

**Once, per renewal date, and the record of that is a row.** Retrying a failed
send is right; sending twice because a job ran twice is not — three emails
about one charge reads as a system out of control, on the subject where trust
matters most. `UsageCounter` is the existing "we did this once" table, and the
key carries the date so that next month's renewal is a different fact rather
than the same one.

**A guest has no address, and that is not an error.** Somebody who bought
without signing in cannot be emailed. It is logged and counted so the number is
visible rather than absent, because the honest fix is upstream — asking for an
address at the checkout — and not a warning buried here.

Nothing schedules this. It is a function and a `__main__`, run as
`python -m alma.billing.renewals` from cron or the platform's scheduler once a
day; see the README. A daily job that misses a day still catches the renewal,
because the window is a range and not an equality — `renews_at` between two and
four days out — so one skipped run does not silently drop a notice.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Entitlement, Purchase, UsageCounter, User, as_utc, utcnow

log = logging.getLogger("alma.billing.renewals")

#: How long before the charge the notice goes out. Three days is what every
#: shipped surface says, so it is one number here rather than three in the copy.
NOTICE_DAYS = 3

#: The window either side of that, which is what makes a daily job safe. A job
#: that asked for renewals *exactly* three days out would send nothing at all on
#: the day it did not run, and nobody would notice until a customer did.
WINDOW = timedelta(days=1)

#: The metric name on the row that remembers a notice was sent.
METRIC = "renewal_notice"


@dataclass(frozen=True, slots=True)
class Notice:
    """One plan about to bill, and everything the letter needs.

    A record rather than the `Entitlement` itself so that sending is testable
    without a mail provider and without a database: what goes in the envelope is
    decided here, and `send` only puts it in one.
    """

    entitlement_id: str
    user_id: str
    email: str
    locale: str
    renews_at: datetime
    amount_cents: int
    currency: str
    kind: str

    @property
    def key(self) -> str:
        """One notice per plan per renewal date.

        The date is in the key, not just the entitlement id: a plan renews every
        month for years, and a key without it would send one notice ever and
        then go quiet for the life of the subscription — which is the failure
        that looks exactly like success.
        """
        return f"{self.entitlement_id}:{METRIC}:{self.renews_at.date().isoformat()}"


async def due(session: AsyncSession, *, at: datetime | None = None) -> list[Notice]:
    """The plans that will be charged in about three days, with an address to write to.

    Revoked rows are excluded and expiry is not consulted: what is being warned
    about is a *charge*, and `renews_at` is the only column that means one.
    Between a cancellation and the end of a paid period `expires_at` is still in
    the future while `renews_at` is `None` — reading the expiry here would email
    somebody who has already cancelled to say we are about to charge them.

    **A notice that cannot name the amount is not sent.** The whole promise is
    that the charge is not a surprise, and a letter saying "$0.00 will be
    charged" three days before $78.99 leaves is worse than silence: it is a
    price quoted in writing that disagrees with the one taken. The amount comes
    from the entitlement where that column holds one and from the money trail
    where it does not — `Entitlement.amount_cents` is written from the granting
    event, and on one processor the granting event for a subscription is
    deliberately a zero-amount one. That is the same reasoning the receipt
    already applies by taking its total off the payment rather than off the
    grant: the money knows what the money was.
    """
    moment = at or utcnow()
    opens = moment + timedelta(days=NOTICE_DAYS) - WINDOW
    closes = moment + timedelta(days=NOTICE_DAYS) + WINDOW

    rows = (
        await session.execute(
            select(Entitlement, User)
            .join(User, User.id == Entitlement.user_id)
            .where(
                Entitlement.revoked_at.is_(None),
                Entitlement.renews_at.is_not(None),
            )
        )
    ).all()

    notices: list[Notice] = []
    for held, owner in rows:
        renews = as_utc(held.renews_at)
        if renews is None or not (opens <= renews <= closes):
            continue
        if not owner.is_active:
            continue
        address = owner.email or await _address_from_the_payment(session, held)
        if not address:
            # Nowhere to write, from either side. Counted rather than swallowed:
            # a run of these means subscriptions are renewing with no warning at
            # all, which is the promise printed beside the pay button.
            log.warning(
                "subscription %s renews on %s and neither its owner nor its "
                "payment carries an email address",
                held.subscription_id, renews.date(),
            )
            continue
        amount, currency = await _what_it_costs(session, held)
        if amount <= 0:
            # No figure anywhere. Refused rather than sent with a nought in it,
            # because the sentence this letter exists to carry is the amount.
            log.error(
                "subscription %s renews on %s and no amount can be found for it "
                "— no notice sent rather than one quoting nothing",
                held.subscription_id, renews.date(),
            )
            continue
        notices.append(
            Notice(
                entitlement_id=held.id,
                user_id=owner.id,
                email=address,
                locale=owner.locale or "en",
                renews_at=renews,
                amount_cents=amount,
                currency=currency,
                kind=held.kind,
            )
        )
    return notices


async def _address_from_the_payment(session: AsyncSession, held: Entitlement) -> str:
    """Where to warn a buyer who never gave us an address of their own.

    A guest may buy — that is deliberate, and it is where most of this funnel
    ends up — so an owner with no `email` is the ordinary case rather than an
    edge one. The processor collected an address at the checkout to take the
    money with, the webhook wrote it onto the purchase, and that is the inbox
    the card statement is going to arrive next to.

    The account's own address still wins upstream: the contract is with the
    account, and this is the fallback rather than the preference. Nothing here
    writes to `User.email` — an unverified address promoted to a sign-in
    identity is an account takeover, not a convenience.
    """
    if not held.subscription_id:
        return ""
    paid = (
        await session.execute(
            select(Purchase)
            .where(
                Purchase.subscription_id == held.subscription_id,
                Purchase.buyer_email.is_not(None),
            )
            .order_by(Purchase.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    return (paid.buyer_email or "") if paid is not None else ""


async def _what_it_costs(session: AsyncSession, held: Entitlement) -> tuple[int, str]:
    """What this plan will be charged, in the currency it is charged in.

    The entitlement's own columns first, because on the processor that fills
    them they are the cheapest and most direct answer. The last completed
    payment for the same subscription second, because on the other one they are
    zero by design — `subscription.active` and `subscription.renewed` carry no
    total, on purpose, since the money arrives on its own `payment.succeeded`.

    The currency travels with the amount rather than being read separately: a
    figure from the money trail priced with a code from the grant is how a
    Brazilian gets told "R$78.99" for a charge of $78.99.
    """
    if held.amount_cents:
        return held.amount_cents, held.currency or "USD"
    if not held.subscription_id:
        return 0, held.currency or "USD"

    paid = (
        await session.execute(
            select(Purchase)
            .where(
                Purchase.subscription_id == held.subscription_id,
                Purchase.completed_at.is_not(None),
                Purchase.amount_cents > 0,
            )
            .order_by(Purchase.completed_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if paid is None:
        return 0, held.currency or "USD"
    return paid.amount_cents, paid.currency or held.currency or "USD"


async def already_sent(session: AsyncSession, notice: Notice) -> bool:
    return await session.get(UsageCounter, notice.key) is not None


async def mark_sent(session: AsyncSession, notice: Notice) -> None:
    """Write the row that stops a second notice for the same charge.

    Written **after** the provider accepted, never before. The other order
    protects us from a duplicate at the cost of the thing the notice exists for:
    a send that failed would be recorded as done, and the person would be
    charged with no warning at all — which is the exact outcome the promise is
    about.
    """
    session.add(
        UsageCounter(
            id=notice.key,
            user_id=notice.user_id,
            day=utcnow().date(),
            metric=METRIC,
            count=1,
            amount=0.0,
        )
    )
    await session.flush()


async def send_due_notices(session: AsyncSession, *, at: datetime | None = None) -> dict:
    """Send every notice that is owed and not yet sent. Returns what happened.

    A dict rather than `None` because this runs unattended: the only way anybody
    finds out that it has been sending nothing for a month is a number in a log
    line, and "sent 0, skipped 0" is a different sentence from "sent 0, already
    12".
    """
    from .. import mail

    outcome = {"due": 0, "sent": 0, "already": 0, "failed": 0}
    for notice in await due(session, at=at):
        outcome["due"] += 1
        if await already_sent(session, notice):
            outcome["already"] += 1
            continue
        if await mail.send_renewal_notice(notice):
            await mark_sent(session, notice)
            outcome["sent"] += 1
        else:
            # Left unmarked on purpose, so the next run tries again. The window
            # is two days wide, so a provider having a bad afternoon costs a
            # retry rather than the notice.
            outcome["failed"] += 1
    if outcome["failed"]:
        log.error("renewal notices: %s", outcome)
    else:
        log.info("renewal notices: %s", outcome)
    return outcome


async def _run() -> dict:
    from ..db.session import session_scope

    async with session_scope() as session:
        return await send_due_notices(session)


if __name__ == "__main__":  # pragma: no cover - the cron entry point
    logging.basicConfig(level=logging.INFO)
    print(asyncio.run(_run()))
