"""The hourly job, and the four ways it is asked to be careful.

Sending is the easy part and it is barely tested here. What is tested is
everything the job does *around* the send: claiming the day before it sends so
a second run cannot double up, giving the day back when nothing went out,
resolving twenty-six different mornings from one UTC instant, and refusing to
start at all rather than running to completion and sending nothing.

No vendor is reached. The transports are `transport.Transport` implementations
of four lines each, which is the point of that seam existing.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pytest
from conftest import database_url, run_async

from alma.db.models import Entitlement, UsageCounter, User, new_id, utcnow
from alma.notify import daily, rules, tokens
from alma.notify.transport import PushUnavailable, Push, Receipt, Verdict

#: The moment the whole file runs at: the default delivery hour, in Warsaw.
#:
#: Derived from `rules.DEFAULT_HOUR` rather than written as a literal. It used
#: to be `datetime(2026, 8, 7, 6, 0)` with `# 08:00 in Warsaw` beside it, and
#: when the owner moved the default to 10:00 twenty-one tests in this file
#: failed at once — none of them about the hour, all of them about a run that
#: no longer coincided with anybody's morning. A test that has to be edited
#: when a preference changes was testing the preference by accident.
#:
#: Warsaw is UTC+2 in August, so this is `DEFAULT_HOUR - 2` in UTC.
WHEN = datetime(2026, 8, 7, rules.DEFAULT_HOUR - 2, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Contact:
    transiting: str = "saturn"
    natal: str = "sun"
    aspect: str = "square"
    weight: float = 0.9
    exact: bool = True
    entering: bool = False
    exact_at: datetime = datetime(2026, 8, 7, 14, 20, tzinfo=timezone.utc)
    #: `alma.daily.Candidate` carries the chosen `Occasion` so the job can hand
    #: it to `write_for` without a second scan. Nothing here reads inside it.
    occasion: object = None


@dataclass(frozen=True)
class Piece:
    """What `alma.daily.service.write_for` gives the job back.

    Only `teaser` is read: it is the validated sentence that becomes the
    notification body. See `transport.Push.body`.
    """

    teaser: str = "Saturn squares your Sun at 14:20; it has been in orb since Tuesday."


async def wrote(session, recipient, chosen, day, tier):
    """The generation succeeded. The default for every test below.

    Passed explicitly rather than defaulted, because `run` without it builds
    the real writer and would reach for a model. A test that forgets it should
    fail loudly rather than quietly send a push with nothing behind it.
    """
    return Piece()


async def unwritten(session, recipient, chosen, day, tier):
    """The generation did not happen — refused, over budget, model down."""
    return None


class Vendor:
    """A transport that records rather than sends."""

    def __init__(self, platform: str = "ios", receipt: Receipt | None = None) -> None:
        self.platform = platform
        self.receipt = receipt or Receipt(Verdict.sent)
        self.sent: list[Push] = []

    async def send(self, token, push: Push) -> Receipt:
        self.sent.append(push)
        return self.receipt


# `zone` is part of the contract in `daily._selector`: the sender resolves the
# ladder once and hands the answer to the selection package, so a stand-in that
# refused it would pass here and fail against the real one.
async def one_contact(session, user, *, on, zone=None):
    return [Contact()]


async def nothing(session, user, *, on, zone=None):
    return []


@pytest.fixture
def db(tmp_path, monkeypatch):
    from alma import config as config_module
    from alma.db import session as session_module

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "daily.db"))
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()
    run_async(session_module.create_all)
    yield session_module
    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


async def subscriber(
    session,
    *,
    zone: str = "Europe/Warsaw",
    tier: str = "subscriber",
    seen_days_ago: int = 0,
    preference: str | None = None,
    token: str | None = None,
) -> User:
    """One person, paid up unless told otherwise, with one phone."""
    user = User(
        id=new_id(),
        provider="guest",
        locale="en",
        # Counted back from `WHEN`, which is the `now` every run in this file is
        # given, not from the real clock. Measured against the wall it was a
        # dated bomb: `seen_days_ago=70` stopped being 70 days before the run on
        # the day the real date drifted past `WHEN`, and the dormancy test went
        # red on a calendar boundary with nothing in the product changed.
        last_seen_at=WHEN - timedelta(days=seen_days_ago),
        daily_push=preference,
    )
    session.add(user)
    await session.flush()
    if tier == "subscriber":
        session.add(
            Entitlement(
                user_id=user.id,
                system="*",
                kind="monthly",
                scope="live",
                expires_at=utcnow() + timedelta(days=20),
            )
        )
    elif tier == "owner":
        session.add(Entitlement(user_id=user.id, system="natal", kind="one_time", scope="system"))
    await tokens.register(
        session,
        user_id=user.id,
        platform="ios",
        token=token or (new_id() * 3)[:64].replace("-", "a"),
        timezone=zone,
    )
    await session.flush()
    return user


# ── idempotency ────────────────────────────────────────────────────────────


def test_a_retry_does_not_double_send(db):
    """The job runs twice in the same hour. The person hears once.

    This is the property the whole hourly design rests on: the catch-up window
    means the same person is selected up to three times in a morning, and a
    deploy, a supervisor restart or a second host all produce the same shape.
    The counter row is what makes the second and third selections a no-op —
    the same pattern `renewals.py` uses, for the same reason and in the same
    table.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session)
            first = await daily.run(
                session, now=WHEN, transports={"ios": vendor}, candidates=one_contact, compose_piece=wrote
            )
            second = await daily.run(
                session, now=WHEN, transports={"ios": vendor}, candidates=one_contact, compose_piece=wrote
            )
            return first, second

    first, second = run_async(work)
    assert first["sent"] == 1
    assert second.get("sent", 0) == 0
    assert second["already"] == 1
    assert len(vendor.sent) == 1


def test_an_hour_later_inside_the_window_still_does_not_resend(db):
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session)
            await daily.run(session, now=WHEN, transports={"ios": vendor}, candidates=one_contact, compose_piece=wrote)
            return await daily.run(
                session,
                now=WHEN + timedelta(hours=2),
                transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )

    assert run_async(work)["already"] == 1
    assert len(vendor.sent) == 1


def test_a_failed_send_gives_the_day_back(db):
    """A vendor having a bad minute costs a retry, not the notification.

    The claim is written before the send, so the only thing standing between a
    transient failure and a lost day is the release — and a release that
    quietly stopped working would look exactly like a quiet sky.
    """
    unwell = Vendor(receipt=Receipt(Verdict.retry, "ServiceUnavailable"))
    recovered = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session)
            failed = await daily.run(
                session, now=WHEN, transports={"ios": unwell}, candidates=one_contact, compose_piece=wrote
            )
            later = await daily.run(
                session,
                now=WHEN + timedelta(hours=1),
                transports={"ios": recovered},
                candidates=one_contact, compose_piece=wrote,
            )
            return failed, later

    failed, later = run_async(work)
    assert failed["failed"] == 1 and failed.get("sent", 0) == 0
    assert later["sent"] == 1


def test_a_failed_send_does_not_start_the_three_day_clock(db):
    """A claimed-but-unsent row must not suppress the next three days.

    `history` reads only rows with a count above zero, which is the difference
    between one vendor timeout and four days of silence.
    """
    unwell = Vendor(receipt=Receipt(Verdict.retry, "ServiceUnavailable"))
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session)
            await daily.run(session, now=WHEN, transports={"ios": unwell}, candidates=one_contact, compose_piece=wrote)
            return await daily.run(
                session,
                now=WHEN + timedelta(days=1),
                transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )

    assert run_async(work)["sent"] == 1


# ── the clock ──────────────────────────────────────────────────────────────


def test_quiet_hours_hold_across_the_date_line(db):
    """One UTC instant, two people, and only one of them is awake.

    One UTC instant: the delivery hour on the 8th in Kiritimati (UTC+14) is
    22:00 on the 7th in Warsaw (UTC+2) — a different hour *and* a different
    date, and Warsaw is inside quiet hours. A job that selected on a UTC hour
    would reach both or neither, and reaching Warsaw means a notification at
    ten at night.

    **The pair used to be Kiritimati and Midway** and it stopped demonstrating
    anything when the default hour moved to 10:00: the two are twenty-five
    hours apart, so Midway lands at 09:00 — awake, and simply not due. The
    property under test is that each person's clock is resolved before
    anything else happens, and it needs a partner who is genuinely asleep.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session, zone="Pacific/Kiritimati")
            await subscriber(session, zone="Europe/Warsaw")
            return await daily.run(
                session,
                now=datetime(2026, 8, 8, rules.DEFAULT_HOUR, 0, tzinfo=timezone.utc)
                - timedelta(hours=14),
                transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )

    report = run_async(work)
    assert report["sent"] == 1
    # One of the two is not even selected: `due` resolves each person's clock
    # before anything else happens, so somebody outside their morning is not a
    # refusal to be counted — they are 23/24 of the world, every hour.
    assert report["due"] == 1


def test_the_counter_is_keyed_on_the_local_day_not_the_utc_one(db):
    """Auckland's morning is the previous UTC day, and must not be counted as it."""
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session, zone="Pacific/Auckland")
            await daily.run(
                session,
                # Auckland is UTC+12 in August, so its morning of the 8th falls
                # on the 7th in UTC — which is the whole point of the test.
                now=datetime(2026, 8, 8, rules.DEFAULT_HOUR, 0, tzinfo=timezone.utc)
                - timedelta(hours=12),
                transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )
            return await session.get(
                UsageCounter, daily.counter_key(user.id, date(2026, 8, 8))
            )

    assert run_async(work) is not None


def test_nobody_outside_their_morning_is_selected(db):
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session, zone="Europe/Warsaw")
            return await daily.run(
                session,
                now=datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc),  # 14:00 in Warsaw
                transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )

    report = run_async(work)
    assert report.get("sent", 0) == 0
    assert vendor.sent == []


# ── the rules, end to end ──────────────────────────────────────────────────


def test_the_cap_holds_over_the_real_ledger(db):
    """Two already this week, so the third is refused — read off the rows.

    Reading the cadence off the same table that makes the job idempotent is
    what makes these limits survive a job that runs twice, on two hosts, or
    across a deploy. An in-process counter would survive none of them, and this
    test would still pass.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session)
            for days in (4, 6):
                day = (WHEN - timedelta(days=days)).date()
                session.add(
                    UsageCounter(
                        id=daily.counter_key(user.id, day),
                        user_id=user.id,
                        day=day,
                        metric=daily.METRIC,
                        count=1,
                        amount=0.0,
                    )
                )
            await session.flush()
            return await daily.run(
                session, now=WHEN, transports={"ios": vendor}, candidates=one_contact, compose_piece=wrote
            )

    report = run_async(work)
    assert report["refused:already 2 this week"] == 1
    assert vendor.sent == []


def test_a_free_user_and_an_owner_get_nothing(db):
    """And are refused for the reason that is true, which is not the same reason."""
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session, tier="free")
            await subscriber(session, tier="owner")
            return await daily.run(
                session, now=WHEN, transports={"ios": vendor}, candidates=one_contact, compose_piece=wrote
            )

    report = run_async(work)
    assert report["refused:not a subscriber"] == 2
    assert vendor.sent == []


def test_somebody_who_stopped_opening_the_app_is_left_alone(db):
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session, seen_days_ago=70)
            return await daily.run(
                session, now=WHEN, transports={"ios": vendor}, candidates=one_contact, compose_piece=wrote
            )

    assert run_async(work)["refused:dormant"] == 1


def test_a_quiet_sky_reports_itself_as_such(db):
    """"sent 0, refused 1 — nothing qualified" is a healthy job. "sent 0" is not."""
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session)
            return await daily.run(
                session, now=WHEN, transports={"ios": vendor}, candidates=nothing, compose_piece=wrote
            )

    report = run_async(work)
    assert report["due"] == 1
    assert report["refused:nothing qualified"] == 1


def test_off_means_no_notification_even_with_a_token_still_registered(db):
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session, preference="off")
            return await daily.run(
                session, now=WHEN, transports={"ios": vendor}, candidates=one_contact, compose_piece=wrote
            )

    assert run_async(work)["refused:off"] == 1


# ── the notification itself ────────────────────────────────────────────────


def test_the_payload_carries_a_key_and_words_rather_than_a_sentence(db):
    """Nothing about a person's chart is composed on the server.

    The lock screen is visible to whoever is holding the phone, and the payload
    passes through a vendor's servers on the way there. What crosses the wire
    is a key and three nouns.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session)
            await daily.run(
                session, now=WHEN, transports={"ios": vendor}, candidates=one_contact, compose_piece=wrote
            )
            return vendor.sent[0]

    push = run_async(work)
    assert push.body_key == "push.daily.exact.square"
    assert push.args == ("Saturn", "Sun", "4:20 pm")
    assert push.collapse_id == "daily-2026-08-07"
    # `type`, because `type` is what the app reads: `AppDelegate.swift` lifts
    # the string fields of `userInfo` and `main.dart` records
    # `push_opened{type: payload['type']}`. This used to say `kind` — the name
    # `docs/PUSH.md §1.6` printed and nothing on the phone has ever looked
    # for — so every tap on a daily was counted with a null type while the pair
    # push, written against the client, was counted correctly.
    assert push.data == {"type": "daily", "date": "2026-08-07"}
    # Срок жизни — конец местных суток, не 22:00: с 25.08.2026 час выбирается
    # любой, и письмо человека с 23:00 не должно умирать за час до доставки.
    assert push.expires_at is not None
    assert push.expires_at.hour == 0 and push.expires_at.day == 8


def test_the_arguments_arrive_in_the_language_of_the_phone(db):
    """`loc-args` are substituted verbatim: an English noun in an Italian sentence.

    This is the failure `alma/i18n/placements.py` exists to stop, and the
    device's language wins over the account's because the device is what the
    operating system will resolve the key in.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session, zone="Europe/Rome")
            device = (await tokens.for_user(session, user.id))[0]
            device.locale = "it"
            await session.flush()
            await daily.run(
                session,
                # Rome keeps Warsaw's offset in August, so `WHEN` is this
                # reader's morning as well.
                now=WHEN,
                transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )
            return vendor.sent[0]

    push = run_async(work)
    assert push.args[:2] == ("Saturno", "Sole")
    assert push.args[2] == "16:20", "twenty-four hour, because Italian writes it that way"


# ── dead tokens, through the job ───────────────────────────────────────────


def test_the_job_deletes_a_token_the_vendor_calls_dead(db):
    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session)
            # The vendor's timestamp has to be *after* the registration, or the
            # reinstall rule correctly keeps the row — which is a different
            # test, two above this one.
            gone = Vendor(
                receipt=Receipt(
                    Verdict.dead, "Unregistered", dead_since=utcnow() + timedelta(seconds=1)
                )
            )
            await daily.run(session, now=WHEN, transports={"ios": gone}, candidates=one_contact, compose_piece=wrote)
            return len(await tokens.for_user(session, user.id))

    assert run_async(work) == 0


def test_a_credential_that_is_wrong_for_everybody_stops_the_run(db):
    """One 403 repeated a thousand times is a thousand requests proving one thing."""
    broken = Vendor(receipt=Receipt(Verdict.fatal, "InvalidProviderToken"))

    async def work():
        async with db.session_scope() as session:
            await subscriber(session)
            await subscriber(session)
            await daily.run(session, now=WHEN, transports={"ios": broken}, candidates=one_contact, compose_piece=wrote)

    with pytest.raises(PushUnavailable):
        run_async(work)
    assert len(broken.sent) == 1


# ── refusing to start ──────────────────────────────────────────────────────


def test_the_job_refuses_to_start_without_a_transport(db):
    """It would otherwise run to completion, log a clean zero and send nothing."""
    async def work():
        async with db.session_scope() as session:
            await daily.run(session, now=WHEN, candidates=one_contact, compose_piece=wrote)

    with pytest.raises(PushUnavailable) as refused:
        run_async(work)
    assert "ALMA_APNS_KEY_P8" in str(refused.value)


def test_the_job_refuses_to_start_without_something_to_ask(db, monkeypatch):
    """No `alma.daily` means nothing to say, which is not the same as saying nothing.

    The absence is now simulated rather than relied on. `alma.daily` exists and
    exports `candidates`, so the plain call this used to make succeeds — which
    means the assertion had quietly become "that package has not been written
    yet" rather than "this job refuses loudly when it has nothing to ask". A
    `None` in `sys.modules` makes the import raise, which is exactly the state
    a missing package produces at the one line that matters.
    """
    import sys

    vendor = Vendor()
    monkeypatch.setitem(sys.modules, "alma.daily", None)

    async def work():
        async with db.session_scope() as session:
            await daily.run(session, now=WHEN, transports={"ios": vendor})

    with pytest.raises(PushUnavailable) as refused:
        run_async(work)
    assert "alma.daily" in str(refused.value)


def test_the_job_refuses_to_start_without_a_way_to_write_the_piece(db, monkeypatch):
    """A notification is an invitation to open something.

    The job used to send a lock-screen line composed from a localisation key
    and never write the reading behind it: nothing generated, nothing
    validated, nothing charged, nothing stored. Tapping it opened an empty day.
    `write_for` is now as load-bearing as `candidates`, and its absence is as
    loud.
    """
    import sys

    vendor = Vendor()
    monkeypatch.setitem(sys.modules, "alma.daily.service", None)

    async def work():
        async with db.session_scope() as session:
            await daily.run(
                session, now=WHEN, transports={"ios": vendor}, candidates=one_contact
            )

    with pytest.raises(PushUnavailable) as refused:
        run_async(work)
    assert "write_for" in str(refused.value)


# ── what the judges found ──────────────────────────────────────────────────


def test_a_fatal_on_the_second_platform_keeps_a_claim_already_spent(db):
    """The exact reproduction: iPhone accepts, Android tablet returns fatal.

    `deliver` raised from inside the device loop and `delivered` died with the
    frame, so `run` released a claim that had already bought a real
    notification — and the next hourly run inside the three-hour window sent a
    second one to the same phone. Two notifications in one morning, which is
    the failure the claim-before-send design exists to prevent.

    It fires on any single-vendor credential fault while the other vendor is
    healthy: a rotated FCM key, a wrong SenderId, an APNs topic mismatch.
    """
    apple = Vendor(platform="ios")
    google = Vendor(platform="android", receipt=Receipt(Verdict.fatal, "SENDER_ID_MISMATCH"))

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session)
            await tokens.register(
                session, user_id=user.id, platform="android",
                token=(new_id() * 3)[:64].replace("-", "b"), timezone="Europe/Warsaw",
            )
            transports = {"ios": apple, "android": google}
            try:
                await daily.run(
                    session, now=WHEN, transports=transports,
                    candidates=one_contact, compose_piece=wrote,
                )
            except PushUnavailable:
                pass
            # An hour later, inside the catch-up window, with the FCM key fixed.
            return await daily.run(
                session, now=WHEN + timedelta(hours=1),
                transports={"ios": apple}, candidates=one_contact, compose_piece=wrote,
            )

    second = run_async(work)
    assert len(apple.sent) == 1, "the iPhone was sent to twice in one morning"
    assert second.get("already") == 1


def test_one_broken_chart_does_not_starve_everybody_behind_it(db):
    """`due()` returns recipients in stable order, so it was the same person forever.

    `candidates` calls `chart_for` and `transits.scan` on stored profile data.
    One corrupt row — bad coordinates, an unparseable timezone, an ephemeris
    edge — propagated out of `run`, discarded the partial tally, and logged
    nothing at all. A total outage that looked like a quiet sky.
    """
    vendor = Vendor()
    seen: list[str] = []

    async def poison(session, user, *, on, zone=None):
        seen.append(user.id)
        if len(seen) == 1:
            raise ValueError("this chart has impossible coordinates")
        return [Contact()]

    async def work():
        async with db.session_scope() as session:
            for _ in range(5):
                await subscriber(session)
            return await daily.run(
                session, now=WHEN, transports={"ios": vendor},
                candidates=poison, compose_piece=wrote,
            )

    report = run_async(work)
    assert report["due"] == 5
    assert report["errored"] == 1
    assert report["sent"] == 4
    assert len(vendor.sent) == 4


def test_an_unresolved_claim_is_reported_as_an_orphan_and_not_as_a_send(db):
    """A run killed between claiming and sending leaves a row nobody resolves.

    The lost day is the accepted cost of claiming first. Being unable to see it
    was not: it was counted under `already`, the same bucket as a healthy
    second run, so `already: 400` after a deploy that killed a pass mid-run
    read as a perfectly healthy job.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session)
            # The wreckage a killed process leaves: claimed, never confirmed.
            session.add(
                UsageCounter(
                    id=daily.counter_key(user.id, date(2026, 8, 7)),
                    user_id=user.id, day=date(2026, 8, 7),
                    metric=daily.METRIC, count=0, amount=0.0,
                )
            )
            await session.commit()
            return await daily.run(
                session, now=WHEN, transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )

    report = run_async(work)
    assert report.get("orphaned") == 1
    assert "already" not in report
    assert vendor.sent == []


def test_a_platform_we_cannot_send_to_is_not_a_vendor_failure(db):
    """An Android-only subscriber during an iOS-only deployment.

    Claimed, silently skipped, released, and counted under `failed` — which
    drives `log.error` and reads as something to escalate to Google, when it is
    our own missing credential. Every hour of their window, every day, for the
    length of a store review.
    """
    apple = Vendor(platform="ios")

    async def work():
        async with db.session_scope() as session:
            user = User(id=new_id(), provider="guest", locale="en", last_seen_at=utcnow())
            session.add(user)
            await session.flush()
            session.add(
                Entitlement(
                    user_id=user.id, system="*", kind="monthly", scope="live",
                    expires_at=utcnow() + timedelta(days=20),
                )
            )
            await tokens.register(
                session, user_id=user.id, platform="android",
                token=(new_id() * 3)[:64].replace("-", "c"), timezone="Europe/Warsaw",
            )
            await session.flush()
            return await daily.run(
                session, now=WHEN, transports={"ios": apple},
                candidates=one_contact, compose_piece=wrote,
            )

    report = run_async(work)
    assert report.get("no transport") == 1
    assert "failed" not in report
    # And no day was claimed, so tomorrow is not affected either.
    assert report.get("sent") is None


def test_no_piece_means_no_push_and_the_day_is_given_back(db):
    """The ceiling bit, or the model refused three times, or it is unreachable.

    A notification with nothing behind it is worse than the silence this
    feature already treats as a supported state — and the day has to be
    released so a later run inside the window can try again.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session)
            report = await daily.run(
                session, now=WHEN, transports={"ios": vendor},
                candidates=one_contact, compose_piece=unwritten,
            )
            held = await session.get(
                UsageCounter, daily.counter_key(user.id, date(2026, 8, 7))
            )
            return report, held

    report, held = run_async(work)
    assert report.get("unwritten") == 1
    assert vendor.sent == []
    assert held is None, "the day must be given back so a later run can try"


def test_the_notification_body_is_the_validated_teaser(db):
    """The merge of the two designs that arrived at this from different sides.

    The body is the piece's own opening sentence, which went through
    `validator.check` with the paragraph it belongs to — rather than a key
    pointing at a reading that was never written.

    **The title used to be a key here too, and the key resolved against
    nothing.** iOS looks `title-loc-key` up in `Localizable.strings` in the
    app's native bundle; the Flutter port has no such file — `knownRegions` is
    `(en, Base)` — and an unresolved key is rendered as the raw key, so every
    daily would have arrived headed `push.daily.title`. The headline is composed
    from `message.TITLES` now, whose seven strings are the app's own
    `pushDailyTitle` and are held to it by `test_notify_strings.py`. The key is
    still carried, so putting a native catalogue in the bundle is a one-line
    revert.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session)
            await daily.run(
                session, now=WHEN, transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )
            return vendor.sent[0]

    from alma.notify import message

    push = run_async(work)
    assert push.title_key == "push.daily.title", "the key is still carried"
    assert push.title == message.TITLES["en"]
    assert push.body == Piece().teaser

    from alma.notify.apns import APNs

    alert = APNs.payload(push)["aps"]["alert"]
    assert alert["title"] == message.TITLES["en"]
    # One or the other, never both, on either half of the alert: Apple resolves
    # `loc-key` against the bundle and takes the literal literally, and a
    # payload carrying both means two different things depending on which the
    # system reaches for first.
    assert "title-loc-key" not in alert
    assert alert["body"] == Piece().teaser
    assert "loc-key" not in alert


def test_a_recipient_with_no_usable_timezone_is_skipped_rather_than_guessed(db):
    """`zone_for` used to end in UTC and the job sent anyway.

    At 08:30 UTC the guess reads as 08:30 local and passes every check; the
    same instant is 00:30 in Anchorage. Reachable without any bug — an
    unrecognised zone is dropped silently at registration and a subscriber may
    have no `is_self` profile to take a birth zone from.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session, zone="Europe/Warsaw")
            for row in await tokens.for_user(session, user.id):
                row.timezone = None
            await session.commit()
            return await daily.run(
                session, now=WHEN, transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )

    report = run_async(work)
    assert report["due"] == 0
    assert vendor.sent == []


# ── десять тысяч человек: порядок, параллельность, отказ вендора ────────────


class Counting:
    """`candidates`, который считает, сколько раз его позвали.

    Единственный способ проверить порядок работ: «эфемериды не считались» — это
    утверждение о том, что этой функции не касались, и никакой отчёт о прогоне
    его не содержит.
    """

    def __init__(self, answer=None) -> None:
        self.calls: list[str] = []
        self.answer = [Contact()] if answer is None else answer

    async def __call__(self, session, user, *, on, zone=None):
        self.calls.append(user.id)
        return list(self.answer)


def test_a_non_subscriber_costs_no_ephemeris_at_all(db):
    """Порядок отказов — это счёт за прогон, а не стиль.

    `candidates()` вызывался *аргументом* внутри `rules.may_send`, то есть
    вычислялся раньше, чем правило успевало сказать «не подписчик». Измерено на
    машине разработки: `chart_for` — 33 мс, трёхдневный `transits.scan` —
    112 мс, то есть ~145 мс процессорного времени на человека, которому по
    правилам ничего не полагается. На десяти тысячах подписчиков в пиковый час
    это минуты ядра, потраченные впустую, — и `rules.PER_MONTH` (десять записей
    в месяц против тридцати с лишним утр) делает такое большинство.
    """
    vendor = Vendor()
    sky = Counting()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session, tier="free")
            await subscriber(session, preference="off")
            await subscriber(session, seen_days_ago=70)
            return await daily.run(
                session, now=WHEN, transports={"ios": vendor},
                candidates=sky, compose_piece=wrote,
            )

    report = run_async(work)
    assert report["due"] == 3
    assert sky.calls == [], "небо считали для тех, кому по правилам ничего не полагается"
    assert vendor.sent == []


def test_a_day_already_sent_costs_no_ephemeris_either(db):
    """«Уже отправлено» — чтение по первичному ключу, и оно дешевле неба.

    До перестановки это выяснялось только в `claim`, то есть после расчёта. При
    ежечасном задании и окне в три часа каждый получатель выбирается трижды за
    утро — значит две трети расчётов приходились на дни, которые уже отправлены.
    """
    vendor = Vendor()
    sky = Counting()

    async def work():
        async with db.session_scope() as session:
            await subscriber(session)
            first = await daily.run(
                session, now=WHEN, transports={"ios": vendor},
                candidates=sky, compose_piece=wrote,
            )
            second = await daily.run(
                session, now=WHEN + timedelta(hours=1), transports={"ios": vendor},
                candidates=sky, compose_piece=wrote,
            )
            return first, second

    first, second = run_async(work)
    assert first["sent"] == 1
    assert second["already"] == 1
    assert len(sky.calls) == 1, "второй час пересчитал небо для уже отправленного дня"


def test_a_claim_left_by_a_killed_run_is_taken_back_the_next_hour(db):
    """Деплой посреди прогона больше не стоит человеку целого утра.

    Захват дня пишется до отправки, и процесс, убитый между ними, оставляет
    строку с `count == 0`, которую никто не разрешит. Внутри своего часа она
    неотличима от живого захвата на другом хосте — и остаётся сиротой. Но
    задание ежечасное, поэтому *следующий* час, застающий её неразрешённой,
    застаёт её от процесса, которого уже нет: час — это и есть та отметка
    времени, которой у `usage_counter` нет.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session)
            session.add(
                UsageCounter(
                    id=daily.counter_key(user.id, date(2026, 8, 7)),
                    user_id=user.id, day=date(2026, 8, 7),
                    metric=daily.METRIC, count=0, amount=0.0,
                )
            )
            await session.commit()
            same_hour = await daily.run(
                session, now=WHEN, transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )
            next_hour = await daily.run(
                session, now=WHEN + timedelta(hours=1), transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )
            return same_hour, next_hour

    same_hour, next_hour = run_async(work)
    assert same_hour.get("orphaned") == 1, "внутри часа захват может быть живым"
    assert next_hour.get("reclaimed") == 1
    assert next_hour["sent"] == 1
    assert len(vendor.sent) == 1


def test_one_dead_vendor_does_not_cancel_the_morning_of_the_other(db):
    """Протухший ключ FCM отменял утро и всем владельцам iPhone заодно.

    Отказ учётных данных верен для всех токенов **одного** вендора и ни о чём
    не говорит про второго — а прогон останавливался целиком. Обычное
    полусломанное состояние (проворот ключа, чужой SenderId, не тот topic) в
    четыре утра, молча, для всех.
    """
    apple = Vendor(platform="ios")
    google = Vendor(platform="android", receipt=Receipt(Verdict.fatal, "SENDER_ID_MISMATCH"))

    async def work():
        async with db.session_scope() as session:
            for _ in range(3):
                user = await subscriber(session)
                await tokens.register(
                    session, user_id=user.id, platform="android",
                    token=(new_id() * 3)[:64].replace("-", "d"), timezone="Europe/Warsaw",
                )
            await session.flush()
            return await daily.run(
                session, now=WHEN, transports={"ios": apple, "android": google},
                candidates=one_contact, compose_piece=wrote,
            )

    report = run_async(work)
    assert report["sent"] == 3, "утро iPhone отменил чужой вендор"
    assert report["vendor down:android"] == 1
    # И вендор, объявленный негодным, больше не опрашивается: три получателя,
    # одна попытка.
    assert len(google.sent) == 1
    assert len(apple.sent) == 3


def test_when_the_last_vendor_goes_the_run_ends_with_an_error(db):
    """Ненулевой код возврата — это то, чем `ExecStartPost` отличает беду.

    Таймер пингует мониторинг только после успешного `ExecStart`. Прогон,
    которому некуда отправлять и который вернул отчёт как ни в чём не бывало, —
    это зелёная галочка в мониторинге поверх молчащего продукта.
    """
    apple = Vendor(platform="ios", receipt=Receipt(Verdict.fatal, "InvalidProviderToken"))
    google = Vendor(platform="android", receipt=Receipt(Verdict.fatal, "SENDER_ID_MISMATCH"))

    async def work():
        async with db.session_scope() as session:
            for _ in range(4):
                user = await subscriber(session)
                await tokens.register(
                    session, user_id=user.id, platform="android",
                    token=(new_id() * 3)[:64].replace("-", "e"), timezone="Europe/Warsaw",
                )
            await session.flush()
            await daily.run(
                session, now=WHEN, transports={"ios": apple, "android": google},
                candidates=one_contact, compose_piece=wrote,
            )

    with pytest.raises(PushUnavailable):
        run_async(work)
    # По одной попытке на вендора, а не по четыре: выбывший не опрашивается.
    assert len(apple.sent) == 1
    assert len(google.sent) == 1


def test_ten_recipients_are_written_in_parallel_and_no_more_than_three_at_once(db):
    """Строго по одному — это часы там, где могут быть минуты.

    Одна утренняя запись — вызов модели на ~8–12 секунд ожидания сети
    (`docs/THE-DAILY.md §2.2`), из которых процесс занят долями секунды.
    Последовательный цикл складывает эти ожидания в сумму; предел — в том,
    чтобы складывать их не все сразу, потому что «все сразу» — это 429 от
    модели и исчерпанный пул базы, то есть не параллельность, а отказ.

    Проверяется и то и другое: что генерации накладываются друг на друга, и
    что их одновременно не больше, чем разрешено.
    """
    vendor = Vendor()
    live = {"now": 0, "peak": 0}

    async def slow(session, recipient, chosen, day, tier):
        live["now"] += 1
        live["peak"] = max(live["peak"], live["now"])
        try:
            await asyncio.sleep(0.02)
            return Piece()
        finally:
            live["now"] -= 1

    async def work():
        async with db.session_scope() as session:
            for _ in range(10):
                await subscriber(session)
            await session.commit()
            return await daily.run(
                session, now=WHEN, transports={"ios": vendor},
                candidates=one_contact, compose_piece=slow,
                sessions=db.session_factory(), concurrency=3,
            )

    report = run_async(work)
    assert report["sent"] == 10, "параллельный путь потерял получателей"
    assert len(vendor.sent) == 10
    assert live["peak"] > 1, "генерации так и идут по одной"
    assert live["peak"] <= 3, "предел одновременности не соблюдён — это и есть «все разом»"


def test_the_parallel_path_still_sends_each_person_exactly_once(db):
    """Идемпотентность — свойство строки в базе, а не цикла.

    Захват дня решает гонку между двумя хостами; здесь та же гонка устроена
    внутри одного процесса — десять задач по одному и тому же списку. Если бы
    он решался переменной цикла, второй прогон отправил бы всё заново.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            for _ in range(6):
                await subscriber(session)
            await session.commit()
            first = await daily.run(
                session, now=WHEN, transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
                sessions=db.session_factory(), concurrency=4,
            )
            second = await daily.run(
                session, now=WHEN + timedelta(hours=1), transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
                sessions=db.session_factory(), concurrency=4,
            )
            return first, second

    first, second = run_async(work)
    assert first["sent"] == 6
    assert second.get("sent", 0) == 0
    assert second["already"] == 6
    assert len(vendor.sent) == 6


def test_a_broken_chart_in_the_parallel_path_does_not_take_the_others(db):
    """То же ограждение, что и в последовательном пути, и оно должно быть одним.

    Ветвей стало две, а правило «одна плохая карта не морит голодом очередь за
    собой» — по-прежнему одно: `_attempt` общий для обеих.
    """
    vendor = Vendor()
    seen: list[str] = []

    async def poison(session, user, *, on, zone=None):
        seen.append(user.id)
        if len(seen) == 1:
            raise ValueError("this chart has impossible coordinates")
        return [Contact()]

    async def work():
        async with db.session_scope() as session:
            for _ in range(5):
                await subscriber(session)
            await session.commit()
            return await daily.run(
                session, now=WHEN, transports={"ios": vendor},
                candidates=poison, compose_piece=wrote,
                sessions=db.session_factory(), concurrency=2,
            )

    report = run_async(work)
    assert report["due"] == 5
    assert report["errored"] == 1
    assert report["sent"] == 4


def test_two_runs_cannot_overlap(db, tmp_path, monkeypatch):
    """Прогон, идущий дольше часа, встречает следующий запуск таймера.

    Захват дня не даст отправить дважды — это его работа, — но не спасёт от
    второго прогона остальное: удвоенный расход на модель на тех, кто попал в
    щель между чтением списка и захватом, вдвое больше соединений к базе и
    вдвое больше запросов к вендору.
    """
    from alma import config as config_module

    monkeypatch.setenv("ALMA_RUN_LOCK_DIR", str(tmp_path / "locks"))
    config_module.settings.cache_clear()

    with daily.single_run("daily") as first:
        assert first is True
        with daily.single_run("daily") as second:
            assert second is False, "второй прогон начался поверх первого"

    # И замок отпускается: следующий час должен получить его снова.
    with daily.single_run("daily") as later:
        assert later is True
