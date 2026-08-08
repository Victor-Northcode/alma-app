"""Device tokens, and the two ways a push system leaks.

The first leak is a dead token retried every morning forever. The second is
the overcorrection: deleting a live token because a vendor's stale answer said
it was dead, which ends the notifications of somebody who is still paying and
reports nothing anywhere. Both are silent, so both are tested here rather than
noticed later.

The vendor tables get their own tests too. `APNs.read` and `FCM.read` are the
whole of `docs/PUSH.md §1.7` and §2.4 as code, they are pure functions over a
status and a body, and every row of them can be asserted without a socket.
"""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta

import pytest
from conftest import database_url, run_async

from alma.db.models import DeviceToken, User, new_id, utcnow
from alma.notify import tokens
from alma.notify.apns import APNs
from alma.notify.fcm import FCM
from alma.notify.transport import PushUnavailable, Receipt, Verdict

APPLE = "a" * 64
GOOGLE = "c" * 140


@pytest.fixture
def db(tmp_path, monkeypatch):
    from alma import config as config_module
    from alma.db import session as session_module

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "notify.db"))
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()
    run_async(session_module.create_all)
    yield session_module
    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


def _user(session, **kwargs) -> User:
    user = User(id=new_id(), provider="guest", locale="en", **kwargs)
    session.add(user)
    return user


# ── registration ───────────────────────────────────────────────────────────


def test_registering_twice_is_one_row(db):
    async def work():
        async with db.session_scope() as session:
            user = _user(session)
            await session.flush()
            first = await tokens.register(
                session, user_id=user.id, platform="ios", token=APPLE,
                timezone="Europe/Warsaw", locale="pl",
            )
            second = await tokens.register(
                session, user_id=user.id, platform="ios", token=APPLE,
                timezone="America/Toronto",
            )
            return first.id, second.id, second.timezone, second.locale

    first, second, zone, locale = run_async(work)
    assert first == second
    assert zone == "America/Toronto", "the client re-registers on every launch and it moved"
    assert locale == "pl", "a field the second call did not carry is not erased"


def test_a_phone_handed_to_a_second_account_moves_rather_than_doubling(db):
    """One device, one morning.

    A row per (user, token) would leave the first account still pointing at the
    phone, and the phone would receive two dailies about two different charts —
    which is the exact failure the whole feature is built to avoid.
    """
    async def work():
        async with db.session_scope() as session:
            one, two = _user(session), _user(session)
            await session.flush()
            await tokens.register(session, user_id=one.id, platform="ios", token=APPLE)
            await tokens.register(session, user_id=two.id, platform="ios", token=APPLE)
            return len(await tokens.for_user(session, one.id)), len(
                await tokens.for_user(session, two.id)
            )

    assert run_async(work) == (0, 1)


def test_re_registering_revives_a_disabled_row(db):
    """A rebuilt app is exactly the event that fixes an environment mismatch."""
    async def work():
        async with db.session_scope() as session:
            user = _user(session)
            await session.flush()
            row = await tokens.register(session, user_id=user.id, platform="ios", token=APPLE)
            await tokens.retire(session, row, Receipt(Verdict.disable, "BadDeviceToken"))
            assert row.disabled_at is not None
            again = await tokens.register(
                session, user_id=user.id, platform="ios", token=APPLE, environment="sandbox"
            )
            return again.disabled_at, again.environment

    disabled_at, environment = run_async(work)
    assert disabled_at is None
    assert environment == "sandbox"


@pytest.mark.parametrize(
    "platform,token",
    [("ios", "short"), ("windows", APPLE), ("ios", "has space" + "x" * 40), ("ios", "")],
)
def test_a_token_is_not_a_free_text_field(platform, token):
    with pytest.raises(tokens.BadToken):
        tokens.clean(platform, token)


def test_android_has_no_environment_and_is_not_asked_for_one():
    assert tokens.clean("android", GOOGLE, environment="sandbox")[2] == "production"


# ── retiring ───────────────────────────────────────────────────────────────


def test_a_dead_token_is_deleted(db):
    async def work():
        async with db.session_scope() as session:
            user = _user(session)
            await session.flush()
            row = await tokens.register(session, user_id=user.id, platform="ios", token=APPLE)
            outcome = await tokens.retire(
                session, row, Receipt(Verdict.dead, "Unregistered", dead_since=utcnow())
            )
            return outcome, len(await tokens.for_user(session, user.id))

    assert run_async(work) == ("deleted", 0)


def test_a_reinstall_survives_a_stale_410(db):
    """The comparison that Apple's own wording asks for, and the obvious code omits.

    Somebody deletes the app on Monday, reinstalls on Tuesday, the app hands us
    the same token, and a queue drained on Wednesday carries Monday's 410. The
    naive handling deletes the row; the person stops receiving what they are
    paying for and nothing reports an error.
    """
    async def work():
        async with db.session_scope() as session:
            user = _user(session)
            await session.flush()
            row = await tokens.register(session, user_id=user.id, platform="ios", token=APPLE)
            died = utcnow() - timedelta(days=2)
            outcome = await tokens.retire(
                session, row, Receipt(Verdict.dead, "Unregistered", dead_since=died)
            )
            return outcome, len(await tokens.for_user(session, user.id))

    assert run_async(work) == ("kept", 1)


def test_a_dead_token_with_no_timestamp_goes(db):
    """Google does not say when. Absent evidence of a reinstall, the row goes."""
    async def work():
        async with db.session_scope() as session:
            user = _user(session)
            await session.flush()
            row = await tokens.register(
                session, user_id=user.id, platform="android", token=GOOGLE
            )
            outcome = await tokens.retire(session, row, Receipt(Verdict.dead, "UNREGISTERED"))
            return outcome, len(await tokens.for_user(session, user.id))

    assert run_async(work) == ("deleted", 0)


def test_a_misconfigured_token_is_disabled_and_not_deleted(db):
    """Deleting it would loop: the client hands us the identical token next launch."""
    async def work():
        async with db.session_scope() as session:
            user = _user(session)
            await session.flush()
            row = await tokens.register(session, user_id=user.id, platform="ios", token=APPLE)
            outcome = await tokens.retire(
                session, row, Receipt(Verdict.disable, "DeviceTokenNotForTopic")
            )
            still_there = await session.get(DeviceToken, row.id)
            return outcome, still_there is not None, still_there.disabled_reason

    assert run_async(work) == ("disabled", True, "DeviceTokenNotForTopic")


def test_a_vendor_having_a_bad_afternoon_costs_nothing_permanent(db):
    async def work():
        async with db.session_scope() as session:
            user = _user(session)
            await session.flush()
            row = await tokens.register(session, user_id=user.id, platform="ios", token=APPLE)
            await tokens.retire(session, row, Receipt(Verdict.retry, "TooManyRequests"))
            return row.disabled_at, row.fail_count, len(await tokens.for_user(session, user.id))

    assert run_async(work) == (None, 1, 1)


# ── retention and erasure ──────────────────────────────────────────────────


def test_a_token_nobody_has_re_registered_in_ninety_days_is_swept(db):
    async def work():
        async with db.session_scope() as session:
            user = _user(session)
            await session.flush()
            stale = await tokens.register(session, user_id=user.id, platform="ios", token=APPLE)
            fresh = await tokens.register(
                session, user_id=user.id, platform="android", token=GOOGLE
            )
            stale.last_seen_at = utcnow() - timedelta(days=91)
            fresh.last_seen_at = utcnow() - timedelta(days=89)
            await session.flush()
            swept = await tokens.sweep(session)
            return swept, [row.platform for row in await tokens.for_user(session, user.id)]

    assert run_async(work) == (1, ["android"])


def test_forget_takes_every_device_the_account_ever_had(db):
    """The sentence `accounts.erase` has to say, tested from this side of it.

    `db/models.py` opens by saying that a table holding a `user_id` and missing
    from `erase` is a promise broken without noticing. This proves the function
    exists and works; the one line calling it belongs in a file another
    workflow owns, and until it lands this table is that exception.
    """
    async def work():
        async with db.session_scope() as session:
            mine, theirs = _user(session), _user(session)
            await session.flush()
            await tokens.register(session, user_id=mine.id, platform="ios", token=APPLE)
            await tokens.register(session, user_id=mine.id, platform="android", token=GOOGLE)
            await tokens.register(session, user_id=theirs.id, platform="ios", token="b" * 64)
            await tokens.forget(session, mine.id)
            return len(await tokens.for_user(session, mine.id)), len(
                await tokens.for_user(session, theirs.id)
            )

    assert run_async(work) == (0, 1)


def test_removing_a_token_is_scoped_to_its_owner(db):
    """A device token turns up in crash logs. It must not be a way to silence somebody."""
    async def work():
        async with db.session_scope() as session:
            mine, theirs = _user(session), _user(session)
            await session.flush()
            await tokens.register(session, user_id=mine.id, platform="ios", token=APPLE)
            stolen = await tokens.remove(
                session, platform="ios", token=APPLE, user_id=theirs.id
            )
            own = await tokens.remove(session, platform="ios", token=APPLE, user_id=mine.id)
            return stolen, own

    assert run_async(work) == (False, True)


# ── the vendor tables ──────────────────────────────────────────────────────


def test_apple_410_carries_milliseconds_and_is_read_as_such():
    """Read as seconds, a 2026 timestamp lands in 57000 AD and every 410 wins."""
    receipt = APNs.read(410, json.dumps({"reason": "Unregistered", "timestamp": 1754563200000}))
    assert receipt.verdict is Verdict.dead
    assert receipt.dead_since is not None
    assert receipt.dead_since.year == 2025


@pytest.mark.parametrize(
    "status,reason,expected",
    [
        (200, "", Verdict.sent),
        (410, "Unregistered", Verdict.dead),
        (400, "ExpiredToken", Verdict.dead),
        # The mismatch, and it is loud — a sandbox token at the production host.
        # The device is fine, so the row is kept and disabled.
        (400, "BadDeviceToken", Verdict.disable),
        (400, "DeviceTokenNotForTopic", Verdict.disable),
        (403, "BadEnvironmentKeyIdInToken", Verdict.fatal),
        (403, "InvalidProviderToken", Verdict.fatal),
        (429, "TooManyRequests", Verdict.retry),
        (429, "TooManyProviderTokenUpdates", Verdict.retry),
        (503, "ServiceUnavailable", Verdict.retry),
        (413, "PayloadTooLarge", Verdict.fatal),
        (400, "MissingTopic", Verdict.fatal),
    ],
)
def test_the_apns_status_table(status, reason, expected):
    assert APNs.read(status, json.dumps({"reason": reason}) if reason else "").verdict is expected


@pytest.mark.parametrize(
    "status,code,expected",
    [
        (200, "", Verdict.sent),
        (404, "UNREGISTERED", Verdict.dead),
        (403, "SENDER_ID_MISMATCH", Verdict.disable),
        (400, "INVALID_ARGUMENT", Verdict.disable),
        (401, "UNAUTHENTICATED", Verdict.fatal),
        (429, "QUOTA_EXCEEDED", Verdict.retry),
        (503, "UNAVAILABLE", Verdict.retry),
        (500, "INTERNAL", Verdict.retry),
    ],
)
def test_the_fcm_error_table(status, code, expected):
    body = json.dumps({"error": {"status": code, "details": [{"errorCode": code}]}}) if code else ""
    assert FCM.read(status, body).verdict is expected


# ── refusing to start ──────────────────────────────────────────────────────


def test_a_missing_credential_fails_at_boot_rather_than_at_the_first_send(monkeypatch):
    """The whole argument for this package refusing loudly.

    A transport constructed without a credential would run the job to
    completion, log a clean zero and send nothing — every number downstream
    healthy, and the first person to find out a subscriber wondering what they
    are paying for.
    """
    from alma import config as config_module

    config_module.settings.cache_clear()
    with pytest.raises(PushUnavailable) as apple:
        APNs()
    assert "ALMA_APNS_KEY_P8" in str(apple.value)

    with pytest.raises(PushUnavailable) as google:
        FCM()
    assert "ALMA_FCM_PROJECT_ID" in str(google.value)


def test_half_a_credential_is_worse_than_none_and_is_reported(monkeypatch):
    """Named on the readiness list only once somebody has started configuring it.

    Four APNs variables on a deploy that has never sent a notification would
    train whoever reads that list to skip it. A signing key with no topic is a
    different thing: it mints perfectly valid provider tokens for notifications
    Apple refuses.
    """
    from alma import config as config_module

    monkeypatch.setenv("ALMA_APNS_KEY_ID", "ABCD123456")
    config_module.settings.cache_clear()
    missing = config_module.settings().missing_for_production()
    assert "ALMA_APNS_TOPIC" in missing
    assert "ALMA_APNS_KEY_ID" not in missing
    config_module.settings.cache_clear()


def test_an_unconfigured_build_offers_no_platforms(monkeypatch):
    from alma import config as config_module
    from alma.notify.transport import configured_platforms, transport_for

    config_module.settings.cache_clear()
    assert configured_platforms() == ()
    with pytest.raises(PushUnavailable):
        transport_for("blackberry")
