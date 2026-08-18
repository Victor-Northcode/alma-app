"""Accounts, and the merge that must not lose anything.

The guest-to-account path is where this product can quietly betray someone.
A person enters their birth details, gets a reading, maybe pays for one, and
then signs in — possibly into an account they already had, on a different
device. Every one of those steps has a way to go wrong that produces no error
and no complaint until the person notices their reading is gone.

So the merge is tested for what it must *never* do: lose a profile, lose a
purchase, leave two "self" profiles behind, or invalidate a token that
somebody is holding mid-checkout.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from alma.db.models import utcnow

import pytest
from conftest import database_url, run_async
from sqlalchemy import select

from alma.auth import accounts, entitlements, tokens
from alma.auth.accounts import AccountDeleted
from alma.db import session as session_module
from alma.db.models import (
    AuthProvider,
    ChatMessage,
    ChatThread,
    Consent,
    DeviceToken,
    Entitlement,
    Event,
    MagicLink,
    Profile,
    Purchase,
    Reading,
    UsageCounter,
    User,
    WebhookEvent,
)


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A fresh database, driven synchronously through a small runner."""
    from alma import config as config_module

    # Disposed before the URL is chosen: on Postgres `database_url` empties
    # the schema, and a connection still pooled from the previous test would
    # turn that drop into a lock wait.
    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "accounts.db"))
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


def _profile(user_id: str, *, is_self: bool = True, name: str = "Sofia") -> Profile:
    return Profile(
        user_id=user_id,
        name=name,
        is_self=is_self,
        birth_date=date(1998, 3, 14),
        birth_time="04:20",
        latitude=45.4642,
        longitude=9.19,
        timezone="Europe/Rome",
    )


# ── guests ─────────────────────────────────────────────────────────────────

def test_a_guest_is_a_real_account_from_the_first_request(db):
    async def work(session):
        guest = await accounts.create_guest(session)
        return guest.id, guest.is_guest, guest.is_active

    user_id, is_guest, is_active = db(work)
    assert user_id and is_guest and is_active


def test_signing_in_turns_the_guest_into_the_account(db):
    """Nothing moves — the row the person has been using gains an email."""

    async def work(session):
        guest = await accounts.create_guest(session)
        session.add(_profile(guest.id))
        await session.flush()

        signed_in = await accounts.sign_in(
            session, email="sofia@example.com", provider="google", subject="g-1", guest=guest
        )
        return guest.id, signed_in.id, signed_in.email

    guest_id, user_id, email = db(work)
    assert user_id == guest_id, "the guest should have become the account, not been copied"
    assert email == "sofia@example.com"


def test_signing_in_twice_lands_on_the_same_account(db):
    async def work(session):
        first = await accounts.sign_in(
            session, email="a@example.com", provider="google", subject="g-1"
        )
        second = await accounts.sign_in(
            session, email="a@example.com", provider="google", subject="g-1"
        )
        return first.id, second.id

    first, second = db(work)
    assert first == second


def test_the_email_is_normalised(db):
    async def work(session):
        created = await accounts.sign_in(
            session, email="  Sofia@Example.COM ", provider="email"
        )
        found = await accounts.by_email(session, "sofia@example.com")
        return created.email, found.id if found else None, created.id

    email, found_id, created_id = db(work)
    assert email == "sofia@example.com"
    assert found_id == created_id


# ── the merge ──────────────────────────────────────────────────────────────

def test_a_guest_merging_into_an_existing_account_keeps_everything(db):
    """The case that loses data if anything is missed."""

    async def work(session):
        established = await accounts.sign_in(
            session, email="sofia@example.com", provider="google", subject="g-1"
        )
        session.add(_profile(established.id, name="Sofia"))

        guest = await accounts.create_guest(session)
        session.add(_profile(guest.id, is_self=True, name="Sofia on the phone"))
        session.add(Profile(
            user_id=guest.id, name="Lucas", is_self=False, birth_date=date(1995, 7, 2),
            birth_time="18:05", latitude=-23.5, longitude=-46.6, timezone="America/Sao_Paulo",
        ))
        session.add(Entitlement(user_id=guest.id, system="natal", kind="one_time"))
        thread = ChatThread(user_id=guest.id, title="a question")
        session.add(thread)
        await session.flush()
        session.add(ChatMessage(thread_id=thread.id, role="user", body="what about work?"))
        session.add(Purchase(user_id=guest.id, transaction_id="txn-1", amount_cents=1499))
        session.add(Reading(
            user_id=guest.id, profile_id=(await session.execute(
                select(Profile.id).where(Profile.user_id == guest.id).limit(1)
            )).scalar_one(),
            system="natal", calc_key="k", engine_version="1.0.0", model="m",
        ))
        await session.flush()

        merged = await accounts.sign_in(
            session, email="sofia@example.com", provider="google", subject="g-1", guest=guest
        )

        profiles = (await session.execute(
            select(Profile).where(Profile.user_id == merged.id)
        )).scalars().all()
        purchases = (await session.execute(
            select(Purchase).where(Purchase.user_id == merged.id)
        )).scalars().all()
        grants = (await session.execute(
            select(Entitlement).where(Entitlement.user_id == merged.id)
        )).scalars().all()
        threads = (await session.execute(
            select(ChatThread).where(ChatThread.user_id == merged.id)
        )).scalars().all()
        readings = (await session.execute(
            select(Reading).where(Reading.user_id == merged.id)
        )).scalars().all()
        return {
            "merged_id": merged.id,
            "guest_id": guest.id,
            "profiles": len(profiles),
            "selves": sum(1 for p in profiles if p.is_self),
            "purchases": len(purchases),
            "grants": len(grants),
            "threads": len(threads),
            "readings": len(readings),
        }

    result = db(work)
    assert result["merged_id"] != result["guest_id"]
    assert result["profiles"] == 3, "a profile went missing in the merge"
    assert result["selves"] == 1, "the merged account has more than one 'self'"
    assert result["purchases"] == 1, "a purchase was lost"
    assert result["grants"] == 1, "a paid entitlement was lost"
    assert result["threads"] == 1
    assert result["readings"] == 1


def test_the_funnel_rows_of_a_guest_move_with_everything_else(db):
    """One person who signed in is one person, in every table that names them.

    The funnel folds merged ids when it reads, so its own report was right —
    but anything else querying `event` directly saw the same visitor twice, and
    a table left out of the merge is a table nobody remembers to fold next time.
    """
    async def work(session):
        guest = await accounts.create_guest(session)
        session.add(Event(user_id=guest.id, name="landing_view", properties={}))
        session.add(Consent(user_id=guest.id, product="door.natal", locale="en",
                            transaction_id="txn_3", statements=[]))
        await session.flush()

        target = await accounts.sign_in(session, email="b@example.com", provider="email")
        await accounts.merge(session, source=guest, target=target)

        events = (await session.execute(
            select(Event).where(Event.user_id == target.id))).scalars().all()
        consents = (await session.execute(
            select(Consent).where(Consent.user_id == target.id))).scalars().all()
        return len(events), len(consents)

    assert db(work) == (1, 1)


def test_an_old_guest_token_still_works_after_a_merge(db):
    """Being logged out mid-checkout looks exactly like a failed payment."""

    async def work(session):
        established = await accounts.sign_in(
            session, email="sofia@example.com", provider="google", subject="g-1"
        )
        guest = await accounts.create_guest(session)
        guest_id = guest.id
        await accounts.sign_in(
            session, email="sofia@example.com", provider="google", subject="g-1", guest=guest
        )
        resolved = await accounts.resolve(session, guest_id)
        return established.id, resolved.id if resolved else None

    established_id, resolved_id = db(work)
    assert resolved_id == established_id


def test_a_merge_chain_resolves_to_the_survivor(db):
    """Three devices, three guests, one person."""

    async def work(session):
        target = await accounts.sign_in(session, email="a@example.com", provider="email")
        first = await accounts.create_guest(session)
        second = await accounts.create_guest(session)
        await accounts.merge(session, source=first, target=second)
        await accounts.merge(session, source=second, target=target)
        resolved = await accounts.resolve(session, first.id)
        return target.id, resolved.id if resolved else None

    target_id, resolved_id = db(work)
    assert resolved_id == target_id


def test_merging_an_account_into_itself_does_nothing(db):
    async def work(session):
        user = await accounts.create_guest(session)
        session.add(_profile(user.id))
        await session.flush()
        await accounts.merge(session, source=user, target=user)
        profiles = (await session.execute(
            select(Profile).where(Profile.user_id == user.id)
        )).scalars().all()
        return user.merged_into_id, len(profiles), profiles[0].is_self

    merged_into, count, is_self = db(work)
    assert merged_into is None
    assert count == 1
    assert is_self is True


def test_a_guest_with_no_prior_account_keeps_its_own_self_profile(db):
    async def work(session):
        guest = await accounts.create_guest(session)
        session.add(_profile(guest.id))
        await session.flush()
        signed_in = await accounts.sign_in(
            session, email="new@example.com", provider="email", guest=guest
        )
        profiles = (await session.execute(
            select(Profile).where(Profile.user_id == signed_in.id)
        )).scalars().all()
        return len(profiles), profiles[0].is_self

    count, is_self = db(work)
    assert count == 1 and is_self is True


def test_an_account_with_no_birth_data_adopts_the_guests(db):
    """Someone who made an account first and only later entered a birth date."""

    async def work(session):
        established = await accounts.sign_in(session, email="a@example.com", provider="email")
        guest = await accounts.create_guest(session)
        session.add(_profile(guest.id))
        await session.flush()
        await accounts.merge(session, source=guest, target=established)
        profiles = (await session.execute(
            select(Profile).where(Profile.user_id == established.id)
        )).scalars().all()
        return [(p.name, p.is_self) for p in profiles]

    profiles = db(work)
    assert profiles == [("Sofia", True)]


# ── deletion ───────────────────────────────────────────────────────────────

def test_deleting_an_account_removes_the_data(db):
    async def work(session):
        user = await accounts.sign_in(session, email="a@example.com", provider="email")
        session.add(_profile(user.id))
        session.add(Entitlement(user_id=user.id, system="natal", kind="one_time"))
        session.add(Purchase(user_id=user.id, transaction_id="txn-2", amount_cents=1499))
        await session.flush()

        await accounts.erase(session, user)

        profiles = (await session.execute(
            select(Profile).where(Profile.user_id == user.id)
        )).scalars().all()
        grants = (await session.execute(
            select(Entitlement).where(Entitlement.user_id == user.id)
        )).scalars().all()
        orphaned = (await session.execute(
            select(Purchase).where(Purchase.transaction_id == "txn-2")
        )).scalar_one()
        return len(profiles), len(grants), orphaned.user_id, user.email

    profiles, grants, purchase_user, email = db(work)
    assert profiles == 0 and grants == 0
    assert purchase_user is None, "the payment record should survive, detached"
    assert email is None


def test_nothing_that_holds_a_user_id_survives_a_deletion(db):
    """The list of tables `erase` walks is the list a person's data lives in.

    Four of them were missing, and the privacy page had been rewritten to
    disclose three of the gaps rather than close them. `Event` is the funnel,
    `UsageCounter` holds the per-day counters and the record of which one-off
    offers somebody was shown, and both are keyed to a `user` row that `erase`
    keeps as a tombstone — so no CASCADE was ever going to fire on them. The
    fourth is the one that mattered most: `MagicLink` holds the raw address, in
    the sign-in table, for ever.
    """
    async def work(session):
        user = await accounts.sign_in(session, email="a@example.com", provider="email")
        session.add(Event(user_id=user.id, name="offer_view", properties={}))
        session.add(UsageCounter(
            id=f"{user.id}:downsell", user_id=user.id,
            day=date(2026, 8, 6), metric="downsell_offered", count=1,
        ))
        session.add(MagicLink(
            token_hash="hash-1", email="a@example.com",
            expires_at=utcnow() + timedelta(minutes=10),
        ))
        await session.flush()

        await accounts.erase(session, user)

        return {
            "events": len((await session.execute(
                select(Event).where(Event.user_id == user.id))).scalars().all()),
            "counters": len((await session.execute(
                select(UsageCounter).where(UsageCounter.user_id == user.id))).scalars().all()),
            "links": len((await session.execute(
                select(MagicLink).where(MagicLink.email == "a@example.com"))).scalars().all()),
        }

    assert db(work) == {"events": 0, "counters": 0, "links": 0}


def test_a_detached_payment_record_no_longer_says_who_bought(db):
    """"Your account is detached from them" was not true, and it is now.

    `Purchase.payload` and `WebhookEvent.payload` keep the processor's delivery
    verbatim — which on both processors carries the buyer's name and email
    address, and on ours carries `custom_data.user_id`, the account id itself.
    So a deleted account was fully re-identifiable from the row we described as
    anonymous, and a second table nothing touched held the same body again.
    """
    async def work(session):
        user = await accounts.sign_in(session, email="a@example.com", provider="email")
        body = {
            "data": {
                "id": "txn_1",
                "custom_data": {"user_id": user.id, "product": "bundle.static"},
                "customer": {"email": "a@example.com", "name": "Sofia Bianchi"},
            }
        }
        session.add(Purchase(
            user_id=user.id, transaction_id="txn_1", amount_cents=3899,
            currency="USD", country="IT", payload=body,
        ))
        session.add(WebhookEvent(
            id="evt_1", provider="paddle", event_type="transaction.completed",
            user_id=user.id, payload=body,
        ))
        await session.flush()

        await accounts.erase(session, user)

        purchase = (await session.execute(
            select(Purchase).where(Purchase.transaction_id == "txn_1")
        )).scalar_one()
        delivery = await session.get(WebhookEvent, "evt_1")
        return {
            "user": purchase.user_id,
            # The money is still there — that is the whole reason the row stays.
            "amount": purchase.amount_cents,
            "currency": purchase.currency,
            "purchase_body": str(purchase.payload),
            "delivery_user": delivery.user_id,
            "delivery_body": str(delivery.payload),
            "id": user.id,
        }

    kept = db(work)
    assert kept["user"] is None and kept["delivery_user"] is None
    assert kept["amount"] == 3899 and kept["currency"] == "USD"
    for body in (kept["purchase_body"], kept["delivery_body"]):
        assert kept["id"] not in body
        assert "a@example.com" not in body
        assert "Sofia Bianchi" not in body


def test_a_consent_that_never_became_a_purchase_is_not_evidence_of_anything(db):
    """Two boxes ticked and a tab closed is not a contract, so the row goes.

    A consent a payment claimed is the other half of a purchase record and is
    detached with it, for the same reason the purchase itself is kept: it is
    not ours alone to delete.
    """
    async def work(session):
        user = await accounts.sign_in(session, email="a@example.com", provider="email")
        session.add(Consent(user_id=user.id, product="door.natal", locale="en",
                            statements=[{"key": "immediate_access", "text": "now"}]))
        session.add(Consent(user_id=user.id, product="bundle.static", locale="en",
                            transaction_id="txn_9",
                            statements=[{"key": "immediate_access", "text": "now"}]))
        await session.flush()

        await accounts.erase(session, user)

        rows = (await session.execute(select(Consent))).scalars().all()
        return [(row.product, row.user_id) for row in rows]

    assert db(work) == [("bundle.static", None)]


def test_a_deleted_account_says_so_rather_than_silently_becoming_someone_new(db):
    async def work(session):
        user = await accounts.sign_in(session, email="a@example.com", provider="email")
        user_id = user.id
        await accounts.erase(session, user)
        try:
            await accounts.resolve(session, user_id)
        except AccountDeleted:
            return "refused"
        return "resolved"

    assert db(work) == "refused"


def test_the_export_contains_everything_we_hold(db):
    async def work(session):
        user = await accounts.sign_in(session, email="a@example.com", provider="email")
        session.add(_profile(user.id))
        session.add(Entitlement(user_id=user.id, system="natal", kind="one_time"))
        await session.flush()
        return await accounts.export(session, user)

    exported = db(work)
    assert exported["account"]["email"] == "a@example.com"
    assert len(exported["profiles"]) == 1
    assert exported["profiles"][0]["birth_time"] == "04:20"
    assert len(exported["entitlements"]) == 1
    assert set(exported) >= {
        "account", "profiles", "entitlements", "purchases", "readings",
        "conversations", "memory",
    }


# ── entitlements ───────────────────────────────────────────────────────────

def test_no_system_is_free_in_its_entirety_any_more(db):
    """Numerology and the birth card used to be given away whole.

    Fourteen written chapters on the most expensive model, to a cohort that
    converts at a percent or two. What stayed free is every *calculation* —
    which is gated nowhere — and one sample chapter per system, which
    `test_entitlements.py` checks system by system.
    """

    async def work(session):
        user = await accounts.create_guest(session)
        return [
            (await entitlements.check(session, user, system)).allowed
            for system in ("numerology", "birth-card", "natal")
        ]

    assert db(work) == [False, False, False]


def test_a_one_time_purchase_unlocks_exactly_one_system(db):
    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t1"
        )
        natal = await entitlements.check(session, user, "natal")
        transits = await entitlements.check(session, user, "transits")
        return natal.allowed, transits.allowed

    assert db(work) == (True, False)


def test_an_annual_plan_unlocks_everything(db):
    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(session, user, system="*", kind="annual", transaction_id="t2")
        unlocked = await entitlements.unlocked_systems(session, user)
        return len(unlocked)

    assert db(work) == 8


def test_an_expired_plan_stops_working(db):
    from alma.db.models import utcnow

    async def work(session):
        user = await accounts.create_guest(session)
        grant = await entitlements.grant(
            session, user, system="*", kind="annual", transaction_id="t3"
        )
        grant.expires_at = utcnow() - timedelta(days=1)
        await session.flush()
        return (await entitlements.check(session, user, "natal")).allowed

    assert db(work) is False


def test_a_revoked_entitlement_stops_working(db):
    async def work(session):
        user = await accounts.create_guest(session)
        grant = await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t4"
        )
        await entitlements.revoke(session, grant)
        return (await entitlements.check(session, user, "natal")).allowed

    assert db(work) is False


def test_a_retried_webhook_does_not_grant_twice(db):
    """Payment providers retry. A double grant is our bug, not theirs."""

    async def work(session):
        user = await accounts.create_guest(session)
        first = await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="same"
        )
        second = await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="same"
        )
        rows = (await session.execute(
            select(Entitlement).where(Entitlement.user_id == user.id)
        )).scalars().all()
        return first.id, second.id, len(rows)

    first, second, count = db(work)
    assert first == second and count == 1


# Здесь стояли два теста кредитного добора: «свежая разовая покупка засчитывается
# в апгрейд по нашей прайс-цене» и «покупка старше окна не засчитывается». Оба
# удалены вместе с самим механизмом — монетизация v3 сняла с продажи `archive`,
# `archive-upgrade` и `archive-bump` (ТЗ §2), а с ними ушли `annual_credit`,
# `list_price_cents` и `CREDIT_WINDOW`. Проверять нечего: нет цены, в которую
# кредит можно превратить.


def test_a_free_chapter_opens_inside_a_paid_system(db):
    """The sample chapter, named by the chapter definitions rather than here.

    This used to be a second hand-written list of slugs, and it had drifted:
    it exempted a chapter called "sun" that the natal system calls "core", so
    the exemption never matched and the sample that sells the report was
    silently behind the paywall.
    """
    from alma.ai.chapters import free_chapters

    sample = next(iter(free_chapters("natal")))

    async def work(session):
        user = await accounts.create_guest(session)
        opened = await entitlements.check(session, user, "natal", chapter=sample)
        rest = await entitlements.check(session, user, "natal", chapter="career")
        return opened.allowed, rest.allowed

    assert db(work) == (True, False)


def test_the_one_free_chapter_opens_and_every_other_chapter_does_not(db):
    """One source of truth, verified through the paywall rather than beside it.

    Раньше здесь требовалась открывающаяся глава-образец у **каждой** системы.
    Правило сменилось 17.08.2026: свободна ровно одна глава во всём продукте,
    натал I. Проверяется по-прежнему через `entitlements.check`, а не рядом с
    ним, — вопрос ведь тот же: совпадает ли объявленное в `chapters.py` с тем,
    что решает пейволл. Разъехавшись, эти двое запирают именно ту главу,
    которая продаёт остальные, — так уже было со слагом «sun»/«core».
    """
    from alma.ai.chapters import BY_SYSTEM

    async def work(session):
        user = await accounts.create_guest(session)
        opened = []
        for system, defined in BY_SYSTEM.items():
            for chapter in defined:
                access = await entitlements.check(
                    session, user, system, chapter=chapter.slug,
                    # Совместимость покупается поштучно, поэтому «открыта ли
                    # глава» без имени партнёра — вопрос без ответа; имя даётся
                    # заведомо несуществующее, чтобы отказ был про права.
                    partner_id="nobody" if system == "compatibility" else None,
                )
                if access.allowed:
                    opened.append(f"{system}/{chapter.slug}")
        return opened

    assert db(work) == ["natal/core"]


# ── tokens ─────────────────────────────────────────────────────────────────

def test_a_token_round_trips(db):
    token = tokens.issue("user-123")
    assert tokens.subject(token) == "user-123"


def test_an_expired_token_is_refused(db):
    token = tokens.issue("user-123", days=-1)
    with pytest.raises(tokens.InvalidToken):
        tokens.read(token)


def test_a_tampered_token_is_refused(db):
    token = tokens.issue("user-123")
    head, body, signature = token.split(".")
    with pytest.raises(tokens.InvalidToken):
        tokens.read(f"{head}.{body}.{signature[:-2]}xx")


def test_the_bearer_header_is_parsed_strictly():
    assert tokens.bearer("Bearer abc") == "abc"
    assert tokens.bearer("bearer abc") == "abc"
    assert tokens.bearer("Basic abc") is None
    assert tokens.bearer("abc") is None
    assert tokens.bearer(None) is None
    assert tokens.bearer("Bearer ") is None


def test_magic_link_tokens_are_stored_hashed():
    token, digest = tokens.new_magic_token()
    assert token != digest
    assert tokens.hash_magic_token(token) == digest
    assert len(digest) == 64


# ── the device token, which is personal data like everything else ──────────

def _register(session, user_id: str, token: str):
    from alma.notify import tokens as device_tokens

    return device_tokens.register(
        session,
        user_id=user_id,
        platform="ios",
        token=token,
        timezone="Europe/Warsaw",
        locale="en",
    )


def test_erasing_an_account_deletes_its_device_tokens(db):
    """A push token survived an erasure verbatim, and three filings said otherwise.

    `models.py`'s opening paragraph calls a table holding a `user_id` and
    absent from `erase` "a promise this project has broken without noticing" —
    which is exactly what had happened, because nothing fails when a table is
    missing from that list. A push token is a persistent per-device
    identifier, so retaining it past an Article 17 request is a failure, and
    DATA-INVENTORY's retention table, APP-PRIVACY and the privacy page all say
    it is deleted with the account.
    """
    async def work(session):
        user = await accounts.sign_in(session, email="a@example.com", provider="email")
        await _register(session, user.id, "d" * 64)
        await session.flush()
        before = len((await session.execute(
            select(DeviceToken).where(DeviceToken.user_id == user.id))).scalars().all())

        await accounts.erase(session, user)

        after = len((await session.execute(
            select(DeviceToken).where(DeviceToken.user_id == user.id))).scalars().all())
        return before, after

    before, after = db(work)
    assert before == 1
    assert after == 0


def test_a_merge_takes_the_phone_with_it(db):
    """A token left on the guest row stops being reachable, silently.

    `notify.daily.due()` filters on `User.is_active`, and a merged row is not.
    It self-heals on the next launch — `tokens.register` is keyed on (platform,
    token) — but "self-heals" means a subscriber loses a day of the thing they
    are paying for.
    """
    async def work(session):
        target = await accounts.sign_in(session, email="a@example.com", provider="email")
        guest = await accounts.create_guest(session)
        await _register(session, guest.id, "e" * 64)
        await session.flush()

        await accounts.merge(session, source=guest, target=target)

        rows = (await session.execute(
            select(DeviceToken).where(DeviceToken.user_id == target.id))).scalars().all()
        return len(rows)

    assert db(work) == 1


def test_the_export_names_the_device_but_never_the_token(db):
    """Article 15 asks that the subject knows what is held, not for the secret.

    A push token is a live delivery credential — anybody holding it and our
    APNs key can send to that phone — so handing it back inside a file a person
    may email themselves would be creating copies of a secret in order to
    honour a transparency request. Omitting the row altogether was the other
    error, and the privacy page's "everything we hold about you" made it a real
    gap.
    """
    async def work(session):
        user = await accounts.sign_in(session, email="a@example.com", provider="email")
        await _register(session, user.id, "f" * 64)
        await session.flush()
        return await accounts.export(session, user)

    exported = db(work)
    assert len(exported["devices"]) == 1
    device = exported["devices"][0]
    assert device["platform"] == "ios"
    assert device["timezone"] == "Europe/Warsaw"
    assert "f" * 64 not in repr(exported)
    assert "token" not in device
