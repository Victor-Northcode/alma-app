"""What a person is allowed to read, decided in one place.

Every paywall in the product asks this module and nothing else. That is the
only way the answer stays consistent between the hub, a chapter, the chat and
the API — three of those being generous where the fourth is strict is how a
paywall becomes both annoying and leaky at the same time.

The rules, and **the order they are asked in is itself a rule**:

* Is the grant still alive at all — not revoked, not expired? Nothing else is
  worth asking first, because a cancelled subscription that answers the second
  question works forever.
* Then, how wide is it? `scope` decides, before any older sentinel does. A
  live plan is written the way the catalogue produces it — `system="*"`,
  `scope="live"` — so reading the `"*"` first matches a subscription and
  answers "everything". That is not a hypothetical: the hub did exactly that
  while `covers()` did not, so a subscriber saw the natal report drawn as
  owned and was refused when they opened it. Every function here that walks
  entitlements asks scope before the sentinel, and they are the same order on
  purpose.
* A live subscription covers the systems that keep moving — and nothing in
  the archive, which is bought once and kept.
* A one-time purchase covers exactly the system it was bought for, forever,
  or exactly the one chapter when a chapter is what was bought.
* One chapter of every system is free, named by the chapter definitions
  rather than by a second list here.

What this module is *not* about is worth saying, because the boundary is the
product: every **calculation** is free and always will be. The chart, the
numbers, the cards, the lines on the map cost us nothing to produce — the
ephemeris and the gazetteer are static files on our own disk. What is sold,
and therefore the only thing any answer here is about, is the written
interpretation.

So a caller that takes a `False` from here and hides the numbers as well has
misread it. There is no answer in this module that means "do not show them
their chart" — and one caller was reading it that way. `systems.PREVIEW_FIELDS`
now has an entry for all eight systems, with a test, because the two that had
none went blank the day the last free system did.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Entitlement, EntitlementKind, User, as_utc, utcnow

#: Whole systems given away, of which there are now none.
#:
#: This used to open numerology and birth-card in their entirety. Against the
#: per-system free chapters in `ai/chapters.py` that was fourteen written
#: chapters handed to every quiz-completer on the most expensive model — about
#: $0.29 a head, against a cohort that converts at one or two percent. A free
#: tier is an argument for the paid one; it is not an argument if it loses
#: money on people who were never going to buy.
#:
#: The boundary, so nobody re-opens this by halves: **calculations stay free
#: forever** — they are computed from static local files and cost nothing —
#: and **one written chapter per system stays free**, via `free_chapters()`.
#: What ended is whole free *systems*, which is the only thing this constant
#: ever meant. The mechanism is kept rather than deleted because re-opening a
#: system for a campaign should be a one-line, one-place decision.
FREE_SYSTEMS: frozenset[str] = frozenset()

#: How wide a grant is, spelled the way the `scope` column spells it. Three
#: values and no more: one system, everything, or the living systems a
#: subscription rents. Named here because a paywall that compares against a
#: bare string is a paywall one typo away from opening.
SCOPE_SYSTEM = "system"
SCOPE_ALL = "all"
SCOPE_LIVE = "live"

#: The older spelling of an everything-grant, written in the `system` column
#: before `scope` existed. Still accepted on the way in and still understood
#: on the way out, because rows written under it are in the database.
EVERYTHING = "*"


#: Within a paid system, one chapter stays open as the sample. Which one is
#: declared alongside the chapter itself rather than duplicated here — a
#: second copy of this list is a list that drifts, and a drifted exemption
#: locks the very chapter that is supposed to sell the rest.
def free_chapters(system: str) -> frozenset[str]:
    from ..ai.chapters import BY_SYSTEM, free_chapters as declared

    return declared(system) if system in BY_SYSTEM else frozenset()


#: A one-time purchase inside this window counts toward the plan that
#: supersedes it. A month rather than a week: the upgrade prompt is shown
#: after a reading has been read and thought about, and a week put the offer
#: in front of people who had not finished the thing they bought yet.
CREDIT_WINDOW = timedelta(days=30)

#: And no further, however much was bought — the credit is never worth more
#: than the price at which we would have sold the whole archive inside a
#: checkout. Held as a *band* and not only as a number, because a cap written
#: as cents means a different amount in every currency: 2999 øre is $3.
CREDIT_CAP_BAND = "archive-bump"
CREDIT_CAP_CENTS = 2999


@dataclass(frozen=True, slots=True)
class Access:
    """Whether a person may read something, and why."""

    allowed: bool
    reason: str
    kind: str | None = None            # "free" | "one_time" | "annual"
    expires_at: datetime | None = None

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "kind": self.kind,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


def living_systems() -> frozenset[str]:
    """Which systems a live subscription includes.

    The list belongs to the catalogue, because "what does the subscription
    contain" is a decision about what we sell rather than about who may read
    what. Read through a function so that this module holds a name and not a
    copy: a second list of systems is a list that drifts, and this one drifts
    in the expensive direction — the archive given away for a month's rent.

    Imported inside the call for the same reason `Entitlement.covers` does
    it: identity should not have to drag the billing package in behind it.
    """
    from ..billing.catalogue import LIVING_SYSTEMS

    return frozenset(LIVING_SYSTEMS)


def subscription_kinds() -> frozenset[str]:
    """Which entitlement kinds mean "this renews".

    Read off the catalogue rather than listed here, because the question is
    only ever "does the thing we sold under this kind bill again", and the
    catalogue is where an interval is declared. The alternative — a set of
    strings in this file — was already one plan behind the day the monthly
    was priced, and a subscriber read as free gets the free tier's model and
    the free tier's three questions while paying us every month.

    Deliberately not "anything with an expiry": a grant made by hand to put
    something right also expires, and it is not a subscription.
    """
    from ..billing.catalogue import PRODUCTS

    return frozenset(item.kind for item in PRODUCTS.values() if item.interval)


def is_in_force(entitlement: Entitlement, at: datetime | None = None) -> bool:
    """Whether this grant still counts at all, before asking what it covers.

    Two questions live inside `Entitlement.covers`: is this row still alive,
    and does it reach this system. They have to be separable, because the
    second one for a live subscription is answered by the catalogue — "what is
    in the plan" is a decision about what we sell — and the tier, the hub, the
    renewal and the account screen all need the first question on its own.

    Public because the account screen needs exactly this and was asking for it
    the wrong way: `entitlement.covers(entitlement.system)` probes coverage
    using the row's own `system` column as a slug, and for a live subscription
    that column holds "live" or "*" — neither of which is a living system. A
    paying subscriber was shown "active: false" on the one screen a person
    opens when they are already wondering whether to cancel.
    """
    if entitlement.revoked_at is not None:
        return False
    moment = at or utcnow()
    expires = as_utc(entitlement.expires_at)
    return expires is None or expires > moment


async def for_user(session: AsyncSession, user: User) -> list[Entitlement]:
    result = await session.execute(
        select(Entitlement).where(
            Entitlement.user_id == user.id, Entitlement.revoked_at.is_(None)
        )
    )
    return list(result.scalars().all())


async def check(
    session: AsyncSession,
    user: User,
    system: str,
    *,
    chapter: str | None = None,
    at: datetime | None = None,
) -> Access:
    """The single authority on whether this person may read this thing."""
    moment = at or utcnow()

    if system in FREE_SYSTEMS:
        return Access(True, "this system is free", kind="free")
    if chapter and chapter in free_chapters(system):
        return Access(True, "this chapter is free", kind="free")

    for entitlement in await for_user(session, user):
        if not entitlement.covers(system, chapter=chapter, at=moment):
            continue
        # Scope first, in the order `covers` and `unlocked_systems` ask it: a
        # live plan is granted with `system="*"`, so testing the everything
        # sentinel first would tell a monthly subscriber they hold the annual
        # plan — on the screen where they are deciding whether it is worth it.
        return Access(
            True,
            "covered by your subscription"
            if entitlement.scope == SCOPE_LIVE
            else "covered by your annual plan"
            if entitlement.scope == SCOPE_ALL or entitlement.system == EVERYTHING
            else "you own this chapter"
            if ":" in entitlement.system
            else f"you own {system}",
            kind=entitlement.kind,
            expires_at=entitlement.expires_at,
        )

    return Access(False, f"{system} has not been unlocked yet")


async def unlocked_systems(session: AsyncSession, user: User) -> set[str]:
    """Everything this person can read right now — for the hub."""
    from ..calc.contract import SYSTEMS

    # One clock for the whole answer: asking the time again per row lets two
    # grants that expire in the same second disagree about whether they did.
    moment = utcnow()
    unlocked = set(FREE_SYSTEMS)
    everything = set(SYSTEMS)
    for entitlement in await for_user(session, user):
        if not is_in_force(entitlement, moment):
            continue
        # Scope is asked *first*, in the same order `Entitlement.covers` asks
        # it, and that order is the whole rule. A monthly plan is granted the
        # way the catalogue describes it — `system="*"`, `scope="live"` — so
        # testing the legacy `system == "*"` sentinel first matched the
        # subscription and returned the entire archive. The two functions then
        # disagreed about one row: the hub drew the natal report as owned and
        # `check()` refused it on the way in. A subscriber who finds the natal
        # report already open never buys it, and finding out it was a lie is
        # worse than never having been offered it.
        if entitlement.scope == SCOPE_LIVE:
            unlocked |= living_systems() & everything
            continue
        if entitlement.scope == SCOPE_ALL or entitlement.system == EVERYTHING:
            return everything
        # A single chapter does not unlock its system on the hub — it is one
        # chapter, and showing the whole system as owned would be a promise
        # the reader finds out about at the second chapter.
        if ":" not in entitlement.system:
            unlocked.add(entitlement.system)
    return unlocked


async def tier_of(session: AsyncSession, user: User, *, at: datetime | None = None) -> str:
    """Which commercial tier this person is in: free, owner, or subscriber.

    The chat allowances and the spend ledger both key off this, and they have
    to agree — a person the ledger thinks is free and the chat thinks is paid
    gets a conversation that stops mid-answer. So the definition lives here
    once: a live subscription outranks a purchase, because someone who has
    both is paying us monthly and should be treated as the more valuable of
    the two states.

    Anything else — a grant made by hand to put something right, a kind we
    have stopped selling — reads as free. This number decides how much of our
    money a person may spend on generation, and only a kind we know we were
    paid for may raise it.
    """
    moment = at or utcnow()
    recurring = subscription_kinds()

    tier = "free"
    for entitlement in await for_user(session, user):
        if not is_in_force(entitlement, moment):
            continue
        if entitlement.kind in recurring:
            return "subscriber"
        if entitlement.kind == EntitlementKind.one_time.value:
            tier = "owner"
    return tier


async def may_be_offered(
    session: AsyncSession, user: User, key: str, *, at: datetime | None = None
) -> bool:
    """Whether this person may be sold the catalogue product named `key`.

    Every shelf price is always offerable. The conditional ones are the whole
    reason this exists: `archive-bump` and `archive-upgrade` grant exactly what
    `archive` grants and cost nine dollars less, so while the checkout accepted
    any key by name, one HTTP call bought the archive at a discount nobody had
    earned. `Product.offered` documented the intent and enforced nothing.

    `archive-bump` is never offerable here. It is the second line item inside a
    door checkout — 899 + 2999 is a cent under the shelf — and this checkout
    sells one product at a time, so on its own it is simply the archive at a
    discount. It becomes offerable the day the checkout can carry two items.

    `archive-upgrade` is the credit promise: it is the shelf price less the
    door, so it is offerable exactly when there is a door to have been paid
    for and nothing wider already held.
    """
    from ..billing.catalogue import PRODUCTS

    item = PRODUCTS.get(key)
    if item is None:
        return False
    if item.on_the_shelf:
        return True
    if key != "archive-upgrade":
        return False

    moment = at or utcnow()
    holds_a_door = False
    for entitlement in await for_user(session, user):
        if not is_in_force(entitlement, moment):
            continue
        # Scope before the sentinel, as everywhere else: a live plan is granted
        # with `system="*"`, and reading that as an everything-grant would tell
        # a subscriber who bought a door that they already own the archive.
        if entitlement.scope == SCOPE_LIVE:
            continue
        if entitlement.scope == SCOPE_ALL or entitlement.system == EVERYTHING:
            return False
        if entitlement.kind == EntitlementKind.one_time.value and ":" not in entitlement.system:
            holds_a_door = True
    return holds_a_door


async def grant(
    session: AsyncSession,
    user: User,
    *,
    system: str,
    kind: str,
    transaction_id: str | None = None,
    subscription_id: str | None = None,
    scope: str | None = None,
    status: str | None = None,
    renews_at: datetime | None = None,
    amount_cents: int = 0,
    currency: str = "USD",
    # Not a processor name. Every caller that knows one passes it; a grant
    # made by hand to put something right genuinely has no processor, and
    # saying "paddle" for it is a row that lies about where money came from.
    source: str = "unknown",
    duration: timedelta | None = None,
) -> Entitlement:
    """Give access. Idempotent per transaction, and per subscription.

    The transaction check is what makes a retried webhook safe. Payment
    providers retry, and a second grant for the same money is a real bug —
    the kind that turns a refund into a support conversation.

    The subscription check is what makes a *renewal* safe, and it cannot be
    the transaction check: every renewal is a new charge with a new
    transaction id, so keying on that wrote one row a month. Two things went
    wrong with that. The rows accumulated, so every paywall check walked a
    longer list each month; and a cancellation only ever caught the row
    belonging to the charge it named, leaving the earlier ones with future
    expiry dates, still granting what had just been cancelled. One
    subscription is one row, extended in place.

    This is also the only writer of `scope`, which is why it is derived here
    when the caller does not say: both spellings of an everything-grant — the
    old `system="*"` and the explicit scope — have to end up as the same row,
    or the hub and the paywall disagree about the same purchase.
    """
    moment = utcnow()
    span = duration or (
        timedelta(days=365) if kind == EntitlementKind.annual.value else None
    )
    if span is None and kind in subscription_kinds():
        # No expiry means forever, and forever is what a subscription is sold
        # *instead of*. A monthly plan granted with no duration would be a
        # month's payment that never has to be made again, and nothing would
        # ever report it as wrong — the row simply keeps working.
        raise ValueError(
            f"a {kind!r} grant needs a duration: a recurring plan written "
            "without an expiry never has to be renewed"
        )
    width = scope or (
        SCOPE_ALL if system == EVERYTHING
        else SCOPE_LIVE if system == SCOPE_LIVE
        else SCOPE_SYSTEM
    )

    if subscription_id:
        # Revoked rows included on purpose: a subscription that is cancelled
        # and started again is the same subscription to the provider, and a
        # second row for it would be a second thing to cancel later.
        found = (
            await session.execute(
                select(Entitlement).where(
                    Entitlement.user_id == user.id,
                    Entitlement.subscription_id == subscription_id,
                )
            )
        ).scalars().first()
        if found is not None:
            # **One period per transaction, and that condition is the fix.**
            #
            # A store subscription arrives twice for one payment and under two
            # different idempotency keys, so insert-before-process cannot
            # collapse them: the app hands us the signed transaction the instant
            # the sheet closes and `/billing/iap/verify` files it as
            # `appstore:<transactionId>`, then Apple's own SUBSCRIBED
            # notification for the same purchase arrives filed under
            # `notificationUUID`. Both reached here, and this branch used to
            # extend by a whole period every time it was called — so every
            # subscriber silently got two months for one month's money, or two
            # years for one year's, with a correct-looking money trail (the
            # `Purchase` row *does* dedupe on transaction id) and nothing wrong
            # anywhere but an expiry date nobody reads until somebody reconciles
            # against Apple's payout report.
            #
            # A genuine renewal carries a *fresh* transaction id — DID_RENEW
            # always does — so it still extends. A replay of the transaction
            # that last extended this row does not.
            already_extended = (
                transaction_id is not None and found.transaction_id == transaction_id
            )
            if span is not None and not already_extended:
                # Extend from whichever is later: a renewal charged a day
                # early must not cost the payer that day, and a subscription
                # resumed after a lapse must not be handed the weeks it was
                # not paying for.
                found.expires_at = max(as_utc(found.expires_at) or moment, moment) + span
            if transaction_id:
                # Recorded on every extension, because it is the only thing that
                # can answer "has this charge already been honoured?" next time.
                found.transaction_id = transaction_id
            # A plan change is the same subscription, so it is the same row.
            # Writing a second one would leave the old scope open for as long
            # as its expiry lasted, which is how a downgrade keeps paying out.
            found.system = system
            found.kind = kind
            found.scope = width
            found.revoked_at = None
            if amount_cents:
                # **Only when the event actually carried a figure**, and that
                # condition is the whole fix. This row is where the pre-renewal
                # notice reads the amount it is about to warn somebody about,
                # and on one of the two processors a subscription grant is
                # written from `subscription.active`/`renewed`, whose amount is
                # deliberately zero — the money arrives on its own payment
                # event. So the column stayed at nought for the life of every
                # Dodo plan, and the letter whose entire job is to say what is
                # about to be taken would have said "$0.00 will be charged"
                # three days before taking $78.99. Writing the zero back over a
                # good figure would be the same bug facing the other way, which
                # is why this is a condition and not an assignment.
                found.amount_cents = amount_cents
                found.currency = currency
            if status is not None:
                found.status = status
            if renews_at is not None:
                found.renews_at = renews_at
            await session.flush()
            return found
    elif transaction_id:
        existing = await session.execute(
            select(Entitlement).where(
                Entitlement.transaction_id == transaction_id,
                Entitlement.user_id == user.id,
                Entitlement.system == system,
            )
        )
        found = existing.scalar_one_or_none()
        if found is not None:
            return found

    entitlement = Entitlement(
        user_id=user.id,
        system=system,
        kind=kind,
        scope=width,
        expires_at=moment + span if span is not None else None,
        transaction_id=transaction_id,
        subscription_id=subscription_id,
        status=status,
        renews_at=renews_at,
        amount_cents=amount_cents,
        currency=currency,
        source=source,
    )
    session.add(entitlement)
    await session.flush()
    return entitlement


async def revoke(session: AsyncSession, entitlement: Entitlement) -> None:
    """Used on refund and chargeback. The row stays; access stops."""
    entitlement.revoked_at = utcnow()
    await session.flush()


def list_price_cents(system: str, currency: str = "USD", *, scope: str | None = None) -> int:
    """What we ask for the thing an entitlement unlocked, in `currency`.

    Resolved to a catalogue **key**, never by scanning for a product whose
    `slug` matches. Five products share the slug `"*"` — the archive, the two
    upgrade bands, the monthly and the annual — so a scan answered with
    whichever of them came first in the dict literal. That is a money lookup
    decided by the order somebody happened to type the catalogue in: moving
    the monthly above the archive would have quietly changed every archive
    holder's credit from $38.99 to $9.99, and nothing would have failed.

    Zero for anything we do not sell in that currency, and zero for anything
    we never published a price for at all. Both are deliberate: a credit has
    to be a number we advertised, because it is set against a price id that
    carries that number, and inventing one is how the two stop matching.
    """
    from ..billing.catalogue import PRODUCTS, WITHDRAWN_CENTS, NotSold

    if ":" in system:
        # A chapter grant names its pair ("natal:core"). The chapter SKU has
        # been withdrawn, so its price lives in the withdrawn table rather
        # than in PRODUCTS — see the comment there for why not `amount_cents`.
        return WITHDRAWN_CENTS.get("chapter", {}).get(currency, 0)

    if scope == SCOPE_LIVE:
        # Scope before the sentinel, as everywhere else. A live plan is granted
        # with `system="*"`, so reading the sentinel first would value a
        # month's rental at the archive's price and hand it back as credit.
        return 0
    if scope == SCOPE_ALL or system == EVERYTHING:
        item = PRODUCTS.get("archive")
    else:
        item = PRODUCTS.get(system)
        if item is not None and item.scope != SCOPE_SYSTEM:
            # `system` matched a key that is not a door — one of the
            # everything-bands named in the system column by hand. Not a door
            # and not the archive, so there is nothing published to hand back.
            item = None
    if item is None:
        return 0
    try:
        return item.cents_in(currency)
    except NotSold:
        return 0


def _cap_cents(currency: str) -> int | None:
    """The most a credit may be worth here, or `None` where nothing caps it.

    `None` rather than a large number: in the purchasing-power markets we
    sell no upgrade band at all, and the only one-time purchase on offer
    there is one we are content to credit in full. A sentinel amount would
    have to be a number of cents, which is the thing this avoids.
    """
    from ..billing.catalogue import PRODUCTS, NotSold

    for item in PRODUCTS.values():
        if item.band != CREDIT_CAP_BAND:
            continue
        try:
            return item.cents_in(currency)
        except NotSold:
            return None
    return CREDIT_CAP_CENTS if currency == "USD" else None


async def annual_credit(
    session: AsyncSession,
    user: User,
    *,
    currency: str = "USD",
    at: datetime | None = None,
) -> int:
    """How much of a recent one-time purchase counts toward the plan above it.

    Someone who buys a single reading, likes it, and upgrades within the month
    should not pay for that reading twice. Anything older than the window is a
    separate decision they already made and does not carry.

    **The largest qualifying purchase, not the sum.** Summing was generous in
    a way that ran past the margin: someone who bought the door and then the
    in-checkout upgrade credited both against the year and paid a little over
    forty dollars for it, which for a European buyer — whose price carries VAT
    inside it — lands under the floor where a year of generation is covered.
    Refunding the reading they already bought is the promise; refunding every
    reading they ever bought is a different and unfunded one. A second
    purchase therefore does not raise the credit.

    **Capped, and the cap is a price rather than a number.** `CREDIT_CAP_BAND`
    is the band we would have charged to add the whole archive inside a
    checkout, so the cap means the same thing in every currency it is quoted
    in. A cap held only as US cents would have been 2999 øre in Norway.

    **Only purchases charged in the currency being priced.** A credit is never
    converted — `catalogue.catalogue` refuses one whose currency does not
    match, and nothing anywhere multiplies it by a regional factor any more —
    so a purchase made in another currency is skipped rather than compared.
    NOK 109 set against a $78.99 plan reads as $109 and buys the year for
    nothing.

    What the answer is *for* is one decision: whether this person qualifies to
    be shown `archive-upgrade` in place of the archive, and by how much it is
    lower. It is not subtracted from a price at request time — a discount
    computed here is a number no price id carries and no processor charges.

    **The credit is our list price, not the total the processor collected.**
    `Entitlement.amount_cents` is the grand total, which carries the sales tax
    we have already handed to a tax authority; crediting it refunds that tax
    out of our own margin, on a reading the buyer keeps. The list price is the
    number we published, it is the number on the price id the upgrade will be
    charged against, and in the markets where the published price is already
    tax-inclusive it is the same figure the buyer paid — so this is the only
    choice that is honest in every market rather than in one.
    """
    moment = at or utcnow()
    cutoff = moment - CREDIT_WINDOW

    best = 0
    for entitlement in await for_user(session, user):
        if entitlement.kind != EntitlementKind.one_time.value:
            continue
        if entitlement.currency != currency:
            continue
        granted = as_utc(entitlement.granted_at)
        if granted is None or granted < cutoff:
            continue
        best = max(
            best,
            list_price_cents(entitlement.system, currency, scope=entitlement.scope),
        )

    cap = _cap_cents(currency)
    return best if cap is None else min(best, cap)
