"""The paywall's rules, tested as rules rather than as arithmetic.

Each test here names a decision that money depends on: what an upgrade credit
is worth, what a subscription does *not* include, and which of three tiers a
person is in. None of them re-runs the implementation and compares it to
itself — the numbers are derived from the catalogue and the definitions, so a
change that quietly reverses a rule fails here instead of in a bank statement.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from conftest import database_url, run_async

from alma.auth import accounts, entitlements
from alma.calc.contract import SYSTEMS
from alma.db import session as session_module
from alma.db.models import Entitlement, EntitlementKind, utcnow


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A fresh database, driven synchronously through a small runner."""
    from alma import config as config_module

    # Disposed before the URL is chosen: on Postgres `database_url` empties
    # the schema, and a connection still pooled from the previous test would
    # turn that drop into a lock wait.
    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "ents.db"))
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


DOOR_CENTS = entitlements.list_price_cents("natal")


# ── the upgrade credit ─────────────────────────────────────────────────────

def test_the_credit_is_the_largest_purchase_and_not_the_sum(db, monkeypatch):
    """Buying twice does not credit twice.

    Summing put someone who bought a door and then a second one close enough
    to the year's price that the year's generation cost stopped being covered.
    The promise is that we hand back the reading they already paid for — one
    of them, the biggest. The two prices are invented here rather than taken
    from the catalogue, which prices every door the same: with equal prices
    the sum and the maximum can be told apart, but a rule that returned the
    *first* purchase would pass anyway.
    """
    prices = {"natal": 500, "transits": 1_200}
    monkeypatch.setattr(
        entitlements, "list_price_cents", lambda system, currency="USD", *, scope=None: prices[system]
    )

    async def work(session):
        user = await accounts.create_guest(session)
        # The dearer one second, so "the last one wins" fails too.
        for index, system in enumerate(("natal", "transits")):
            await entitlements.grant(
                session, user, system=system, kind="one_time", transaction_id=f"t{index}"
            )
        first_order = await entitlements.annual_credit(session, user)

        other = await accounts.create_guest(session)
        for index, system in enumerate(("transits", "natal")):
            await entitlements.grant(
                session, other, system=system, kind="one_time", transaction_id=f"o{index}"
            )
        return first_order, await entitlements.annual_credit(session, other)

    assert db(work) == (1_200, 1_200)


def test_a_second_purchase_does_not_raise_the_credit(db):
    """Told through the real catalogue, where every door costs the same."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t1"
        )
        after_one = await entitlements.annual_credit(session, user)
        await entitlements.grant(
            session, user, system="transits", kind="one_time", transaction_id="t2"
        )
        return after_one, await entitlements.annual_credit(session, user)

    after_one, after_two = db(work)
    assert after_one == DOOR_CENTS
    assert after_two == after_one


def test_the_credit_stops_at_the_cap(db, monkeypatch):
    """However dear the thing bought, the credit has a ceiling."""
    monkeypatch.setattr(
        entitlements, "list_price_cents", lambda system, currency="USD", *, scope=None: 9_999
    )

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t1"
        )
        return await entitlements.annual_credit(session, user)

    assert db(work) == entitlements.CREDIT_CAP_CENTS


def test_the_cap_is_a_price_and_not_a_number_of_cents(db, monkeypatch):
    """2999 øre is three dollars. The cap has to mean the same thing everywhere.

    So it is quoted per currency from the band the catalogue prices it on,
    and a euro buyer's cap is the euro price of that band rather than the US
    integer wearing a euro sign.
    """
    from alma.billing.catalogue import PRODUCTS

    band = next(
        item for item in PRODUCTS.values() if item.band == entitlements.CREDIT_CAP_BAND
    )
    monkeypatch.setattr(
        entitlements, "list_price_cents", lambda system, currency="USD", *, scope=None: 999_999
    )

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="one_time",
            transaction_id="t1", currency="EUR",
        )
        return await entitlements.annual_credit(session, user, currency="EUR")

    capped = db(work)
    assert capped == band.cents_in("EUR")
    assert capped != band.cents


def test_a_purchase_in_another_currency_does_not_credit(db):
    """A credit is subtracted, never converted.

    NOK 109 taken off a $78.99 plan reads as $109 and buys the year for
    nothing, so a purchase charged in one currency simply does not count
    toward a price quoted in another.
    """

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="one_time",
            transaction_id="t1", currency="NOK",
        )
        return (
            await entitlements.annual_credit(session, user),
            await entitlements.annual_credit(session, user, currency="NOK"),
        )

    against_dollars, against_kroner = db(work)
    assert against_dollars == 0
    assert against_kroner == entitlements.list_price_cents("natal", "NOK")


def test_only_purchases_inside_the_window_credit(db):
    """The window is about recency, and a purchase outside it carries nothing."""
    window = entitlements.CREDIT_WINDOW

    async def work(session):
        user = await accounts.create_guest(session)
        stale = await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t1"
        )
        stale.granted_at = utcnow() - window - timedelta(minutes=1)
        await session.flush()
        outside = await entitlements.annual_credit(session, user)

        stale.granted_at = utcnow() - window + timedelta(minutes=1)
        await session.flush()
        return outside, await entitlements.annual_credit(session, user)

    assert db(work) == (0, DOOR_CENTS)


def test_the_credit_ignores_what_the_processor_collected(db):
    """We credit our published price, not the total the processor took.

    `amount_cents` is the grand total, so it carries the tax that has already
    gone to a tax authority. Crediting it refunds someone else's tax out of
    our own margin, on a reading the buyer still has.
    """

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t1",
            amount_cents=DOOR_CENTS * 3,
        )
        return await entitlements.annual_credit(session, user)

    assert db(work) == DOOR_CENTS


def test_a_grant_of_something_we_do_not_sell_is_not_money_back(db):
    """An entitlement nobody was charged for cannot become a discount."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="a-system-we-do-not-sell", kind="one_time",
            transaction_id="t1", amount_cents=4_900,
        )
        return await entitlements.annual_credit(session, user)

    assert db(work) == 0


# ── the three tiers ────────────────────────────────────────────────────────

def test_a_person_with_nothing_is_free(db):
    async def work(session):
        return await entitlements.tier_of(session, await accounts.create_guest(session))

    assert db(work) == "free"


def test_a_one_time_purchase_makes_an_owner(db):
    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t1"
        )
        return await entitlements.tier_of(session, user)

    assert db(work) == "owner"


def test_a_live_plan_makes_a_subscriber_and_an_expired_one_does_not(db):
    """The tier follows the money that is still arriving, not the money that did."""

    async def work(session):
        user = await accounts.create_guest(session)
        plan = await entitlements.grant(
            session, user, system="*", kind=EntitlementKind.annual.value,
            transaction_id="t1",
        )
        while_live = await entitlements.tier_of(session, user)

        plan.expires_at = utcnow() - timedelta(days=1)
        await session.flush()
        return while_live, await entitlements.tier_of(session, user)

    assert db(work) == ("subscriber", "free")


def test_every_recurring_product_we_sell_makes_a_subscriber(db):
    """Whatever renews, in whatever plan, reads as a subscriber.

    This used to be a set of kind strings written next to the tier function,
    and it was one plan behind the moment the monthly was priced: a person
    paying us every month was billed as a subscriber, answered as a free user
    on the cheapest model, and rationed to three questions a day.
    """
    from alma.billing.catalogue import PRODUCTS

    kinds = sorted({item.kind for item in PRODUCTS.values() if item.interval})
    assert kinds, "the catalogue must sell something that renews"

    async def work(session):
        tiers = {}
        for kind in kinds:
            user = await accounts.create_guest(session)
            await entitlements.grant(
                session, user, system="*", kind=kind,
                subscription_id=f"sub_{kind}", duration=timedelta(days=31),
            )
            tiers[kind] = await entitlements.tier_of(session, user)
        return tiers

    for kind, tier in db(work).items():
        assert tier == "subscriber", f"a {kind} plan reads as {tier}"


def test_a_subscriber_who_also_bought_something_is_still_a_subscriber(db):
    """Two states at once resolve to the one that keeps paying us."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t1"
        )
        await entitlements.grant(
            session, user, system="*", kind=EntitlementKind.annual.value,
            transaction_id="t2",
        )
        return await entitlements.tier_of(session, user)

    assert db(work) == "subscriber"


def test_a_kind_we_never_sold_is_not_an_owner(db):
    """A grant made by hand must not be handed the paying account's budget.

    The tier is matched against the kinds we know we were paid for, rather
    than being "anything that is not nothing" — the day support grants a
    week of something to apologise for an outage, that account should not
    acquire an owner's spending ceiling along with it.
    """

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="comp",
            transaction_id="t1", duration=timedelta(days=7),
        )
        return await entitlements.tier_of(session, user)

    assert db(work) == "free"


def test_a_revoked_purchase_drops_the_tier(db):
    async def work(session):
        user = await accounts.create_guest(session)
        held = await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t1"
        )
        await entitlements.revoke(session, held)
        return await entitlements.tier_of(session, user)

    assert db(work) == "free"


# ── the live subscription is not the archive ───────────────────────────────

def test_a_live_subscription_does_not_unlock_the_archive(db):
    """The subscription sells what changes. The archive is bought once.

    A scope the hub does not recognise used to be no scope at all, and the
    only branch that answered "everything" was the one that meant everything.
    A subscriber who found the natal report already open would never buy it.
    """
    living = entitlements.living_systems() & set(SYSTEMS)
    archive = set(SYSTEMS) - living
    assert living and archive, "a live plan must cover some systems and not others"

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE,
            kind=EntitlementKind.annual.value, subscription_id="sub_1",
        )
        unlocked = await entitlements.unlocked_systems(session, user)
        opens = await entitlements.check(session, user, sorted(living)[0])
        stays_shut = await entitlements.check(session, user, sorted(archive)[0])
        return unlocked, opens.allowed, stays_shut.allowed

    unlocked, opens, stays_shut = db(work)
    assert unlocked == living
    assert opens is True
    assert stays_shut is False


def test_a_live_plan_spelled_the_way_the_catalogue_spells_it(db):
    """The shape a real subscription actually has: `system="*"`, `scope="live"`.

    That is what `PRODUCTS["monthly"]` produces, and `unlocked_systems` tested
    the legacy `system == "*"` sentinel *before* the scope — so it matched
    first and handed the subscriber all eight systems, while `covers()`, which
    reads scope first, refused seven of them. The hub drew the natal report as
    owned and opening it was refused. The existing test above passed only
    because it grants with `system="live"`, a spelling the catalogue never
    produces.
    """
    living = entitlements.living_systems() & set(SYSTEMS)

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.EVERYTHING,
            kind=EntitlementKind.monthly.value, scope=entitlements.SCOPE_LIVE,
            subscription_id="sub_live", duration=timedelta(days=31),
        )
        return (
            await entitlements.unlocked_systems(session, user),
            (await entitlements.check(session, user, "natal")).allowed,
            (await entitlements.check(session, user, sorted(living)[0])).reason,
        )

    unlocked, natal, reason = db(work)
    assert unlocked == living
    assert natal is False
    assert "subscription" in reason, "a monthly plan is not the annual plan"


# ── which prices may be put in front of whom ───────────────────────────────

def test_the_shelf_is_offered_to_anybody(db):
    async def work(session):
        user = await accounts.create_guest(session)
        return {
            key: await entitlements.may_be_offered(session, user, key)
            for key in ("natal", "archive", "monthly", "annual")
        }

    assert all(db(work).values())


def test_the_upgrade_is_not_offered_to_somebody_with_nothing_to_upgrade(db):
    """It is the archive at nine dollars off. Offered to a stranger it is a
    discount off a purchase they have not made — and the checkout accepted it
    by name, so anyone who read the catalogue response could take it."""
    async def work(session):
        user = await accounts.create_guest(session)
        return await entitlements.may_be_offered(session, user, "archive-upgrade")

    assert db(work) is False


def test_the_upgrade_is_offered_to_somebody_who_bought_a_door(db):
    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind=EntitlementKind.one_time.value,
            transaction_id="t1",
        )
        return await entitlements.may_be_offered(session, user, "archive-upgrade")

    assert db(work) is True


def test_the_upgrade_is_not_offered_to_somebody_who_already_owns_everything(db):
    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.EVERYTHING,
            kind=EntitlementKind.one_time.value, transaction_id="t1",
        )
        return await entitlements.may_be_offered(session, user, "archive-upgrade")

    assert db(work) is False


def test_the_in_checkout_bump_is_never_offered_on_its_own(db):
    """899 + 2999 is a cent under the shelf. 2999 alone is the shelf less nine
    dollars, for the same grant, and this checkout sells one product at a
    time."""
    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind=EntitlementKind.one_time.value,
            transaction_id="t1",
        )
        return await entitlements.may_be_offered(session, user, "archive-bump")

    assert db(work) is False


def test_a_subscriber_who_bought_a_door_may_still_upgrade(db):
    """A rental is not the archive, so it does not disqualify anybody."""
    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.EVERYTHING,
            kind=EntitlementKind.monthly.value, scope=entitlements.SCOPE_LIVE,
            subscription_id="sub_1", duration=timedelta(days=31),
        )
        await entitlements.grant(
            session, user, system="natal", kind=EntitlementKind.one_time.value,
            transaction_id="t1",
        )
        return await entitlements.may_be_offered(session, user, "archive-upgrade")

    assert db(work) is True


def test_a_credit_is_looked_up_by_key_and_not_by_dict_order(db):
    """Five products share the slug "*". A scan answered with whichever came
    first in the literal, so moving the monthly above the archive would have
    changed every archive holder's credit from $38.99 to $9.99 in silence."""
    from alma.billing.catalogue import PRODUCTS

    sharing = [key for key, item in PRODUCTS.items() if item.slug == entitlements.EVERYTHING]
    assert len(sharing) > 1, "the ambiguity this guards against still exists"

    assert entitlements.list_price_cents(
        entitlements.EVERYTHING, scope=entitlements.SCOPE_ALL
    ) == PRODUCTS["archive"].cents
    # A rental is not a purchase, so there is nothing to hand back.
    assert entitlements.list_price_cents(
        entitlements.EVERYTHING, scope=entitlements.SCOPE_LIVE
    ) == 0


def test_a_cancelled_subscription_closes_what_it_opened(db):
    async def work(session):
        user = await accounts.create_guest(session)
        plan = await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE,
            kind=EntitlementKind.annual.value, subscription_id="sub_1",
        )
        await entitlements.revoke(session, plan)
        return await entitlements.unlocked_systems(session, user)

    assert db(work) == set()


# ── renewals ───────────────────────────────────────────────────────────────

def test_a_recurring_grant_without_a_duration_is_refused(db):
    """A subscription with no expiry is one payment for permanent access."""

    async def work(session):
        user = await accounts.create_guest(session)
        try:
            await entitlements.grant(
                session, user, system="*", kind="monthly", subscription_id="sub_1"
            )
        except ValueError as exc:
            return str(exc)
        return None

    message = db(work)
    assert message is not None and "duration" in message

def test_a_renewal_extends_one_row_rather_than_writing_another(db):
    """Every renewal is a new charge, so the charge id cannot be the identity.

    Keying on it wrote a row a month, and cancelling then caught only the row
    belonging to the cancelled charge — the other eleven kept their future
    expiry dates and kept granting access.
    """
    from sqlalchemy import select

    month = timedelta(days=30)

    async def work(session):
        user = await accounts.create_guest(session)
        first = await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE, kind="annual",
            subscription_id="sub_1", transaction_id="txn_1", duration=month,
        )
        first_expiry = first.expires_at
        second = await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE, kind="annual",
            subscription_id="sub_1", transaction_id="txn_2", duration=month,
        )
        rows = (
            await session.execute(
                select(Entitlement).where(Entitlement.user_id == user.id)
            )
        ).scalars().all()
        return first.id, second.id, len(rows), first_expiry, second.expires_at

    first_id, second_id, count, before, after = db(work)
    assert first_id == second_id and count == 1
    assert after - before >= month - timedelta(seconds=1)


def test_a_lapsed_subscription_does_not_get_backdated_time(db):
    """Renewing after a gap buys the period from now, not from when it lapsed."""
    month = timedelta(days=30)

    async def work(session):
        user = await accounts.create_guest(session)
        plan = await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE, kind="annual",
            subscription_id="sub_1", duration=month,
        )
        plan.expires_at = utcnow() - timedelta(days=90)
        await session.flush()
        resumed = await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE, kind="annual",
            subscription_id="sub_1", duration=month,
        )
        return resumed.expires_at - utcnow()

    assert abs(db(work) - month) < timedelta(minutes=1)


def test_a_plan_change_moves_the_scope_instead_of_keeping_both(db):
    """Upgrading a subscription must not leave the old scope open behind it."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE, kind="annual",
            subscription_id="sub_1", duration=timedelta(days=30),
        )
        await entitlements.grant(
            session, user, system=entitlements.EVERYTHING, kind="annual",
            subscription_id="sub_1", duration=timedelta(days=30),
        )
        rows = await entitlements.for_user(session, user)
        return len(rows), await entitlements.unlocked_systems(session, user)

    count, unlocked = db(work)
    assert count == 1
    assert unlocked == set(SYSTEMS)


# ── what is free ───────────────────────────────────────────────────────────

def test_no_whole_system_is_free_but_one_chapter_of_each_still_is(db):
    """The free tier is a sample of everything, not the whole of anything."""
    from alma.ai.chapters import BY_SYSTEM, free_chapters

    async def work(session):
        user = await accounts.create_guest(session)
        results = {}
        for system in BY_SYSTEM:
            sample = next(iter(free_chapters(system)))
            whole = await entitlements.check(session, user, system)
            opened = await entitlements.check(session, user, system, chapter=sample)
            results[system] = (whole.allowed, opened.allowed)
        return results

    for system, (whole, opened) in db(work).items():
        assert whole is False, f"{system} is being given away entirely"
        assert opened is True, f"{system} has no free sample chapter"
