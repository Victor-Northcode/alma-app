"""The job that sends the daily. Hourly, idempotent, and happy to send nothing.

**Hourly, not daily.** 08:00 happens twenty-six times around the world, so a
once-a-day job can only be 08:00 somewhere. This one runs every hour and
selects the people whose local morning has just arrived. The shape is also the
failure story: a once-daily job that fails has taken out everybody for a day,
where an hourly job that fails has taken out one band of longitudes for one
hour — and the next run, inside `rules.WINDOW_HOURS`, picks them up. For a
product whose content is *"here is what today contains"*, that distinction is
the whole difference between late and wrong.

**Idempotent, and the row comes before the send.** `renewals.py` writes its
"we did this" row *after* the provider accepts, because for a renewal notice
the unforgivable failure is silence about money. Here the unforgivable failure
is the opposite one: two notifications in one morning to somebody the entire
design is built around not annoying. So the row is claimed first, published so
that a second worker sees it, and *deleted* if the send fails — which means a
crash between the claim and the send costs one person one day of a feature
whose floor is already zero, and a job that runs twice costs nothing at all.
That is the right way round for this feature and the wrong way round for that
one, and the two files disagreeing on purpose is worth more than a shared
helper that is wrong for one of them.

**Nothing schedules this**, exactly as nothing schedules `renewals.py` or
`funnel.py --purge`. It is a function and a `__main__`, run as
`python -m alma.notify.daily`. `docs/PUSH.md §8` recommends a systemd timer
with a dead-man's switch, and makes the point that matters more than the
choice: three jobs that do not run is one operations problem, and whoever
wires the first should wire all three. A renewal notice a day late is
survivable; a daily a day late is a lie about what day it is.

**What this file refuses to do quietly.** It will not start without a push
credential, and it will not start without something to ask what today
contains. Both refusals are loud and both name what is missing, because a push
system that appears to work and sends nothing is the worst failure available
here: every log line reads "sent 0", every counter is healthy, and the first
person to notice is a subscriber wondering what they are paying for.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Mapping
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import DeviceToken, Profile, UsageCounter, User, as_utc, utcnow
from . import message, rules, tokens as token_store
from .transport import (
    PushUnavailable,
    Receipt,
    Transport,
    Verdict,
    configured_platforms,
    transport_for,
)

log = logging.getLogger("alma.notify.daily")

#: The `UsageCounter.metric` this job writes. Same table and same idea as
#: `renewals.METRIC`; a different word so the two never share a row.
METRIC = "daily_push"

#: How far back the cadence rules need to see. The longest window any of them
#: asks about is the starvation valve's twenty-one days; a month is read
#: because the monthly cap is a calendar month and the first of the month is
#: not thirty days after the first of the last one.
HISTORY_DAYS = 40

#: The two funnel stages this feature needs, named here so the ask is in the
#: code as well as in the handover. `alma/funnel.py` keeps a closed set of
#: stage names and answers 422 to anything outside it, which is deliberate and
#: cannot be worked around from here — so until these two are added there,
#: `_measure` degrades to a single log line and the daily is unmeasured. The
#: consequence is worth stating plainly: `THE-DAILY.md §7` says the only metric
#: that measures what the owner actually asked for is the ratio of Off to
#: Occasionally after thirty days, and without these names it does not exist.
FUNNEL_STAGES = ("daily_sent", "daily_opened")

_warned_about_funnel = False


def moment_of(now: datetime | None) -> datetime:
    """The instant this pass is running at, and it is always UTC-aware.

    **One function, called by everything that takes a `now`, because a naive
    datetime is how a daily ends up in somebody's night.** The value arrives
    from four places — `utcnow()`, the `--at` replay, a test, and a caller in
    another module — and only the first two are guaranteed to carry a zone.
    A naive one is not merely untidy: `rules.local_now` reads it as UTC and
    resolves a plausible-looking local morning from it, while `is_dormant`
    subtracts it from an aware `last_seen_at` and raises `TypeError` — so the
    same missing `tzinfo` produces a silent wrong answer on one line and a
    crash three lines later. Treating it as UTC is correct rather than merely
    convenient: every instant this job is ever handed is UTC, and the ones the
    database returns are UTC with the zone stripped by SQLite (`as_utc` exists
    for exactly that).
    """
    if now is None:
        return utcnow()
    return now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)


def counter_key(user_id: str, day: date) -> str:
    """One send per person per local day, and the local day is the point.

    `renewals.py` puts the renewal date in its key so that next month is a
    different fact rather than the same one; the same argument applies here to
    the date the notification is *about*. It is the recipient's local date, not
    UTC's: for somebody in Auckland the two disagree for a third of every day,
    and keying on UTC would let them be sent to twice inside one of their
    mornings.
    """
    return f"{user_id}:{day.isoformat()}:{METRIC}"


@dataclass(slots=True)
class Recipient:
    """One person, their devices, and the clock their morning happens in."""

    user: User
    devices: list[DeviceToken] = field(default_factory=list)
    zone: ZoneInfo = field(default_factory=lambda: ZoneInfo("UTC"))
    local: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hour: int = rules.DEFAULT_HOUR
    locale: str | None = None


async def due(session: AsyncSession, *, now: datetime | None = None) -> list[Recipient]:
    """Everybody whose local morning is happening, with their devices attached.

    Loads every live token and resolves each person's clock in Python rather
    than selecting on a timezone in SQL. That is a scan, and it is the right
    trade at this size: the table holds one row per install, the whole of it is
    a few megabytes at a hundred thousand subscribers, and the expensive part
    of this job is the transit work that happens afterwards for the fraction
    who are actually due. The zone-set query is the optimisation to reach for
    when that stops being true, and it is not needed to be correct.

    Deleted and merged accounts are dropped here rather than refused later:
    they are a row that should have had its tokens deleted, and counting them
    as "refused" would hide that.
    """
    moment = moment_of(now)

    rows = (
        await session.execute(
            select(DeviceToken, User)
            .join(User, User.id == DeviceToken.user_id)
            .where(DeviceToken.disabled_at.is_(None))
        )
    ).all()

    by_user: dict[str, Recipient] = {}
    for device, owner in rows:
        if not owner.is_active:
            continue
        recipient = by_user.get(owner.id)
        if recipient is None:
            recipient = Recipient(user=owner)
            by_user[owner.id] = recipient
        recipient.devices.append(device)

    if not by_user:
        return []

    births = dict(
        (
            await session.execute(
                select(Profile.user_id, Profile.timezone).where(
                    Profile.user_id.in_(by_user.keys()), Profile.is_self.is_(True)
                )
            )
        ).all()
    )

    ready: list[Recipient] = []
    skipped: list[str] = []
    for recipient in by_user.values():
        # The most recently seen device decides the clock and the language. A
        # person with a phone and a tablet has one morning, and the device they
        # last opened is the best evidence of where they are — an old iPad left
        # in a drawer in the country they moved away from must not decide when
        # the phone in their pocket buzzes.
        newest = max(recipient.devices, key=lambda d: as_utc(d.last_seen_at) or moment)
        zone = rules.zone_for(
            device=newest.timezone,
            chosen=recipient.user.daily_timezone,
            birth=births.get(recipient.user.id),
        )
        if zone is None:
            # Skipped rather than sent to in a guessed zone. `zone_for` used to
            # end in UTC, which sends somebody in Anchorage a good-morning
            # piece at half past midnight — see its docstring. Reachable
            # without any bug: an unrecognised zone is dropped silently at
            # registration, `tokens.register` only overwrites the stored one
            # when the client sends it, and a subscriber may have no `is_self`
            # profile to take a birth zone from.
            skipped.append(recipient.user.id)
            continue
        recipient.zone = zone
        recipient.locale = newest.locale or recipient.user.locale
        recipient.local = rules.local_now(recipient.zone, moment)
        recipient.hour = rules.delivery_hour(recipient.user.daily_hour)
        if rules.due_now(recipient.local, recipient.hour):
            ready.append(recipient)

    if skipped:
        log.error(
            "%d recipient(s) have no usable timezone and were skipped: %s. "
            "Nothing is sent to them until one resolves — a daily in the "
            "middle of somebody's night is the one thing this feature must "
            "never do.",
            len(skipped), ", ".join(sorted(skipped)[:20]),
        )
    return ready


async def history(session: AsyncSession, user_id: str, *, before: date) -> list[date]:
    """The local dates this person was last sent a daily on.

    Read off the same rows that make the job idempotent, which is what makes
    the three-day gap and the two caps survive a job that runs twice, a job
    that runs on two hosts, and a deploy mid-run. An in-process counter would
    survive none of them.

    Only rows with a `count` above zero: a claimed-but-unsent row is a send
    that failed, and letting it suppress the next three days would turn one
    vendor timeout into four days of silence.
    """
    since = before - timedelta(days=HISTORY_DAYS)
    rows = (
        await session.execute(
            select(UsageCounter.day).where(
                UsageCounter.user_id == user_id,
                UsageCounter.metric == METRIC,
                UsageCounter.count > 0,
                UsageCounter.day >= since,
            )
        )
    ).scalars().all()
    return [day if isinstance(day, date) else date.fromisoformat(str(day)) for day in rows]


async def claim(
    session: AsyncSession, *, user_id: str, day: date
) -> tuple[UsageCounter | None, str]:
    """Reserve this person's day, or say who already has it and in what state.

    A savepoint around the insert, exactly as `funnel.claim` does it and for
    the same reason: the race is real, losing it is the correct answer rather
    than an error, and the primary key is what decides — a rule the database
    enforces rather than one this module hopes callers keep.

    **Losing the race has two meanings and the report has to tell them apart.**
    A row with `count > 0` is a notification that went out: healthy, and the
    same fact whether this run or another host recorded it. A row with
    `count == 0` is a *claim that was never resolved* — a process killed
    between the claim and the send, leaving a day nobody will ever get and
    nothing will ever clean up. Both used to be counted as `already`, so an
    operator reading `already: 400` after a deploy that killed a run mid-pass
    saw a perfectly healthy job.

    The lost day itself is the documented and accepted cost of claiming before
    sending. Being unable to see it was not.
    """
    row = UsageCounter(
        id=counter_key(user_id, day),
        user_id=user_id,
        day=day,
        metric=METRIC,
        count=0,
        amount=0.0,
    )
    try:
        async with session.begin_nested():
            session.add(row)
    except IntegrityError:
        held = await session.get(UsageCounter, counter_key(user_id, day))
        if held is not None and not (held.count or 0):
            # Indistinguishable, inside the window, from a live claim on
            # another host — so it is reported rather than re-taken. Past the
            # window it is unambiguously an orphan, and a later run of this
            # same function will say so again.
            return None, "orphaned"
        return None, "already"
    await session.commit()
    return row, "claimed"


async def confirm(session: AsyncSession, row: UsageCounter) -> None:
    """A vendor accepted it. The claim becomes the record."""
    row.count = 1
    await session.commit()


async def release(session: AsyncSession, row: UsageCounter) -> None:
    """Nothing went out. Give the day back so a later run inside the window can try.

    Deleting rather than leaving a zero row: `history` already ignores zeroes,
    but a row left behind would make a second attempt in the same hour
    impossible, and the window exists precisely so that a vendor having a bad
    minute costs a retry rather than the notification.
    """
    await session.delete(row)
    await session.commit()


def _selector() -> Callable:
    """Where "what is happening in this chart today" comes from.

    The contract, which `alma/daily/` owns and this module only consumes:

        async def candidates(
            session, user, *, on: date, zone: ZoneInfo | None = None
        ) -> Sequence[Candidate]

    Everything the sky offers this person on that local date, unfiltered by
    weight, each item carrying `transiting`, `natal`, `aspect`, `weight`,
    `exact`, `entering` and `exact_at` — see `rules.Candidate`. **The astronomy
    is theirs and the cadence is this package's**, which is why the caps below
    can be tested without an ephemeris and the ephemeris can be tested without
    a calendar.

    **The zone travels with the date, and that is not a convenience.** A local
    date is meaningless without the clock it was read on, and the two packages
    do not rank the rungs the same way: `rules.zone_for` puts a zone chosen in
    settings above the device's, `daily/clock.zone_for` follows
    `THE-DAILY.md §3.3` and puts the device first. Whoever holds the device rows
    resolves once — this package — and the other is told the answer. Letting the
    selection package decide again would bracket the day on the *birth* zone,
    which is the rung that is wrong by however many hours somebody has moved.

    Resolved once at the start of a run and refused loudly when absent, rather
    than caught per user. A job that cannot ask what today contains has nothing
    to send and must say so, not send nothing.
    """
    try:
        from ..daily import candidates  # type: ignore[attr-defined]
    except ImportError as exc:
        raise PushUnavailable(
            "the daily selection package is not available "
            f"({exc}). `alma.daily.candidates(session, user, on=…, zone=…)` is what "
            "decides what today contains; without it this job would run to "
            "completion and send nothing, which is the failure that looks "
            "exactly like success."
        ) from exc
    return candidates


def _writer() -> Callable:
    """Where the piece behind the notification comes from.

    The second half of the seam `_selector` describes. That one asks *what is
    happening in this chart today*; this one asks for **the reading about it**,
    validated and stored, so that the notification has something to open.

        async def write_for(session, user, *, occasion, birth, profile_id,
                            provider, model, tier, locale, hour) -> Daily

    It takes the occasion `rules.pick` already chose rather than choosing
    again. Two modules deciding the same day's event by two rules is how they
    start disagreeing, and `alma/daily/candidates` hands the `Occasion` back on
    every candidate precisely so this call needs no second scan.

    Refused loudly at the start of a run, like the selector, and for the same
    reason: a job that can name a transit but cannot write about it would send
    a notification pointing at an empty day, and every counter would look fine.
    """
    try:
        from ..daily.service import write_for  # type: ignore[attr-defined]
    except ImportError as exc:
        raise PushUnavailable(
            "the daily writing package is not available "
            f"({exc}). `alma.daily.service.write_for(...)` is what turns the "
            "chosen transit into the validated piece the notification opens; "
            "without it every push would be an invitation to read nothing."
        ) from exc
    return write_for


def piece_writer(write_for: Callable | None = None) -> Callable:
    """The `compose_piece` callable `run` uses. Injected in tests, built here.

    Every failure it swallows is an *expected state* rather than a fault: the
    month ceiling has bitten, the model refused after three attempts and was
    charged for them, the provider is unreachable. In every one of those the
    correct answer is to send nothing — silence is a supported state of this
    feature, and a notification with no reading behind it is not. A genuine
    fault still raises and `run`'s per-recipient guard catches it.

    **The model is `model_mid`.** `cost.guard(paid=False)` inside the writer
    bounds this one call against the $0.05 free ceiling and `guard_month`
    bounds the account across the month; both are already in `write_for`, and
    wiring this path is what finally puts a live caller behind them. Measured
    live: $0.0128–$0.0175 a piece.
    """
    writer = write_for or _writer()

    async def compose(session: AsyncSession, recipient: Recipient, chosen, day: date, tier: str):
        from ..ai import cost
        from ..ai.provider import ModelUnavailable, default_provider
        from ..ai.writer import ReadingRefused
        from ..config import settings
        from ..daily import service as daily_service

        profile = await daily_service.self_profile(session, recipient.user)
        if profile is None:  # pragma: no cover - `candidates` already returned []
            return None

        try:
            return await writer(
                session,
                recipient.user,
                occasion=chosen.candidate.occasion,
                birth=daily_service.birth_of(profile),
                profile_id=profile.id,
                provider=default_provider(),
                model=settings().model_mid,
                tier=tier,
                locale=recipient.locale or recipient.user.locale or "en",
                hour=recipient.hour,
            )
        except (ReadingRefused, cost.BudgetExceeded, ModelUnavailable) as exc:
            log.warning("no daily written for %s on %s: %s", recipient.user.id, day, exc)
            return None

    return compose


async def _measure(session: AsyncSession, user_id: str) -> None:
    """Record that a daily went out, if the funnel knows the name yet."""
    global _warned_about_funnel
    from .. import funnel

    try:
        await funnel.record(session, user_id=user_id, stage=FUNNEL_STAGES[0])
    except funnel.UnknownStage:
        if not _warned_about_funnel:
            log.warning(
                "the daily is unmeasured: alma/funnel.py's closed stage set has "
                "no %s. Until it does, nothing counts how often this fires or "
                "how many people switch it off.",
                " or ".join(FUNNEL_STAGES),
            )
            _warned_about_funnel = True


class Aborted(PushUnavailable):
    """A `fatal` verdict, carrying whether anything had already gone out.

    **The flag is the whole point of this class existing.** `deliver` walks a
    person's devices in turn. If the iPhone accepts and the Android token then
    returns `fatal`, the old code raised from inside the loop and `delivered`
    died with the stack frame — so `run` released a claim that had already been
    spent on a real notification, and the next hourly run inside the three-hour
    window sent a second one to the same phone. Two notifications in one
    morning, to somebody the entire design is built around not annoying, which
    is the exact failure the claim-before-send design exists to prevent.

    It fires on any single-vendor credential fault while the other vendor is
    healthy — a rotated FCM key, a wrong SenderId, an APNs topic mismatch —
    i.e. the ordinary half-broken state, at four in the morning, silently, for
    every dual-platform subscriber at once.
    """

    def __init__(self, message: str, *, delivered: bool = False) -> None:
        super().__init__(message)
        self.delivered = delivered


async def deliver(
    session: AsyncSession,
    recipient: Recipient,
    push,
    transports: Mapping[str, Transport],
) -> bool:
    """Send to every device this person has. True if any vendor accepted.

    **Any, not all.** A person with an iPhone and an Android tablet whose
    tablet token has gone stale should still get their morning; requiring
    every device to succeed would let one dead row silence a live one.

    A `fatal` verdict aborts the whole run rather than the person: it means
    the credential is wrong for everybody, and continuing would spend a
    thousand requests proving the same thing to the same vendor. It aborts
    *carrying* what had already been delivered — see `Aborted`.

    **A socket that dies is one device's answer, not one person's.** Every
    verdict below is a sentence a vendor said; a `ReadTimeout`, a DNS failure
    or a TLS reset is the vendor saying nothing, and it used to travel as an
    exception — out of this loop, past the second phone, up into `run`'s
    per-recipient guard. Which was survivable for the run and wrong twice for
    the person: their iPhone was never tried because their tablet's connection
    dropped, and the day stayed *claimed* rather than released, so it was lost
    outright and the next run reported it as an orphaned claim — the log line
    that means "a process was killed mid-pass", printed for a routine network
    blip. Read as `retry`, which is what it is: nothing is known about the
    token, the row is untouched, and the day goes back for the next hourly run
    inside the window.
    """
    delivered = False
    for device in recipient.devices:
        transport = transports.get(device.platform)
        if transport is None:
            # A platform we hold tokens for and cannot send to — one half of
            # the product configured and the other not, which is a legitimate
            # state while one store is still in review. Not logged per token:
            # the fix is a credential, and one line per phone would bury the
            # run's own report under it. `run` names the configured platforms
            # once, at the start, which is where an operator would look.
            continue
        try:
            receipt = await transport.send(device, push)
        except PushUnavailable:
            # A credential the sender only discovers when it reaches for it —
            # an unreadable `.p8`, a provider token Apple called expired inside
            # its own refresh floor. True of every token, so it is the run's
            # problem and it goes up as one.
            raise
        except Exception as exc:
            log.warning(
                "device %s (%s) could not be reached: %s", device.id, device.platform, exc
            )
            receipt = Receipt(Verdict.retry, exc.__class__.__name__, str(exc)[:200])
        if receipt.verdict is Verdict.fatal:
            await token_store.retire(session, device, receipt)
            raise Aborted(
                f"{device.platform} refused every notification: "
                f"{receipt.reason} ({receipt.detail}). Stopping the run rather "
                "than repeating it for everybody else.",
                delivered=delivered,
            )
        outcome = await token_store.retire(session, device, receipt)
        if receipt.verdict is Verdict.sent:
            delivered = True
        else:
            log.info(
                "device %s (%s): %s → %s", device.id, device.platform, receipt.reason, outcome
            )
    return delivered


def reachable(recipient: Recipient, transports: Mapping[str, Transport]) -> bool:
    """Whether any of this person's devices is on a platform we can send to.

    Asked *before* the day is claimed and before a generation is paid for.
    An Android-only subscriber during an iOS-only deployment used to be
    claimed, silently skipped inside `deliver`, released, and counted under
    `failed` — which drives `log.error` and reads as a vendor problem an
    operator should escalate to Apple or Google, when it is our own missing
    credential. Every hour of their window, every day, for the whole of a store
    review. That is how a standing error line teaches whoever is on call to
    ignore it.
    """
    return any(device.platform in transports for device in recipient.devices)


async def run(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    transports: Mapping[str, Transport] | None = None,
    candidates: Callable | None = None,
    compose_piece: Callable | None = None,
) -> dict:
    """One hourly pass. Returns what happened, which is the only report there is.

    A dict rather than `None` for `renewals.py`'s reason: this runs unattended,
    and "sent 0, refused 0" is a completely different sentence from "sent 0,
    refused 412 — nothing qualified". The first is a broken job and the second
    is a quiet sky, and a log line that cannot tell them apart is a log line
    nobody can act on.
    """
    if transports is None:
        platforms = configured_platforms()
        if not platforms:
            raise PushUnavailable(
                "no push transport is configured — set the APNs four "
                "(ALMA_APNS_KEY_P8, ALMA_APNS_KEY_ID, ALMA_APNS_TEAM_ID, "
                "ALMA_APNS_TOPIC) or the FCM two (ALMA_FCM_SERVICE_ACCOUNT_JSON, "
                "ALMA_FCM_PROJECT_ID). Refusing to start: a push job with no "
                "transport runs to completion, logs a clean zero and sends "
                "nothing."
            )
        transports = {name: transport_for(name) for name in platforms}
    if candidates is None:
        candidates = _selector()
    if compose_piece is None:
        compose_piece = piece_writer()

    missing = [name for name in ("ios", "android") if name not in transports]
    if missing:
        log.info(
            "sending to %s only; no transport for %s, so tokens on it are "
            "skipped rather than failed",
            ", ".join(sorted(transports)), ", ".join(missing),
        )

    from ..auth import entitlements

    moment = moment_of(now)
    outcome: dict[str, int] = defaultdict(int)
    outcome["due"] = 0

    for recipient in await due(session, now=moment):
        outcome["due"] += 1
        try:
            await _one(
                session,
                recipient,
                transports=transports,
                candidates=candidates,
                compose_piece=compose_piece,
                entitlements=entitlements,
                moment=moment,
                outcome=outcome,
            )
        except Aborted as exc:
            log.error("daily notifications aborted after %s", dict(outcome))
            raise exc
        except Exception:
            # **One bad chart must not starve everybody behind it.** There was
            # no guard here, and `due()` returns recipients in stable query
            # order — so an exception from `candidates()` (which calls
            # `chart_for` and `transits.scan` on stored profile data) or from
            # `compose` poisoned the same position on every subsequent hourly
            # run, forever, discarding the partial tally and logging nothing at
            # all. One corrupt row — bad coordinates, an unparseable timezone,
            # an ephemeris edge — was a total outage that looked like a quiet
            # sky. `Aborted` still propagates above: that one is about
            # everybody, and this one is about one chart.
            log.exception("the daily failed for %s", recipient.user.id)
            outcome["errored"] += 1
            await _recover(session)

    swept = await token_store.sweep(session, now=moment)
    if swept:
        outcome["swept"] = swept
    await session.commit()

    report = dict(outcome)
    if outcome["failed"] or outcome["errored"]:
        log.error("daily notifications: %s", report)
    else:
        log.info("daily notifications: %s", report)
    return report


async def _recover(session: AsyncSession) -> None:
    """Put the session back in a usable state after one recipient failed.

    **Only when it actually has to**, which is the whole content of this
    function. An unconditional `rollback()` here would discard whatever the
    *caller* had pending — for a job walking a list of subscribers that is
    somebody else's work, and it is the same argument `daily.piece_for` makes
    about not rolling back on its refusal path. It also loses nothing useful:
    an exception from `candidates` never wrote anything, and a session whose
    transaction is still active can carry straight on to the next person.

    What does need a rollback is a transaction the database has already
    invalidated — a failed flush leaves the session inactive, and every
    subsequent statement raises `PendingRollbackError` until somebody clears
    it. There the pending work is lost whatever we do, so clearing it is
    strictly better than turning one bad chart into an error for everybody
    behind it, which is the failure this guard exists to prevent.
    """
    transaction = session.sync_session.get_transaction()
    if transaction is not None and not transaction.is_active:
        log.warning("the session was left unusable; rolling back to continue the run")
        await session.rollback()


async def _one(
    session: AsyncSession,
    recipient: Recipient,
    *,
    transports: Mapping[str, Transport],
    candidates: Callable,
    compose_piece: Callable | None,
    entitlements,
    moment: datetime,
    outcome: dict,
) -> None:
    """One person's morning. Every exit records why, and `run` counts them."""
    day = recipient.local.date()

    tier = await entitlements.tier_of(session, recipient.user, at=moment)
    past = await history(session, recipient.user.id, before=day)
    decision = rules.may_send(
        tier=tier,
        stored_preference=recipient.user.daily_push,
        last_seen=as_utc(recipient.user.last_seen_at),
        local=recipient.local,
        hour=recipient.hour,
        history=past,
        # The zone goes with the day. `day` was resolved on `recipient.zone`,
        # and the selection package would otherwise bracket it on the birth
        # zone — the one rung that is wrong for everybody who has moved.
        candidates=await candidates(session, recipient.user, on=day, zone=recipient.zone),
        now=moment,
    )
    if not decision.send or decision.chosen is None:
        outcome[f"refused:{decision.reason}"] += 1
        return

    if not reachable(recipient, transports):
        # Asked before the claim and before any generation is paid for. This
        # is our missing credential, not a vendor's refusal, and it is counted
        # under its own name rather than under `failed`.
        outcome["no transport"] += 1
        return

    row, state = await claim(session, user_id=recipient.user.id, day=day)
    if row is None:
        outcome[state] += 1
        if state == "orphaned":
            log.warning(
                "user %s holds an unresolved claim for %s — a run was killed "
                "between claiming the day and sending it, and that day is lost",
                recipient.user.id, day,
            )
        return

    # **The piece, before the push.** This is the half that was never wired:
    # the job composed a lock-screen line from a localisation key and sent it,
    # and the reading it pointed at was never written, never validated, never
    # charged and never stored. Tapping the notification opened an empty day.
    #
    # It is generated after the claim, deliberately. The claim is what stops
    # two hosts both spending money on the same person's morning, and the
    # accepted cost of claiming first — a crash here loses one day of a feature
    # whose floor is already zero — is the cost this job already documented.
    piece = None
    if compose_piece is not None:
        piece = await compose_piece(session, recipient, decision.chosen, day, tier)
        if piece is None:
            # No piece, no push. The daily package's rule, and the reason is
            # not squeamishness: a notification is an invitation to open
            # something, and an invitation to open nothing is worse than the
            # silence this feature already treats as a supported state.
            await release(session, row)
            outcome["unwritten"] += 1
            return

    push = message.compose(
        decision.chosen,
        zone=recipient.zone,
        local=recipient.local,
        locale=recipient.locale,
        teaser=piece.teaser if piece is not None else "",
    )
    try:
        delivered = await deliver(session, recipient, push, transports)
    except Aborted as exc:
        # A person already reached today keeps their claim even though the run
        # is being abandoned. Releasing it would let the next run inside the
        # catch-up window send them a second notification in one morning.
        if exc.delivered:
            await confirm(session, row)
            await _measure(session, recipient.user.id)
            outcome["sent"] += 1
        else:
            await release(session, row)
        raise

    if delivered:
        await confirm(session, row)
        await _measure(session, recipient.user.id)
        await session.commit()
        outcome["sent"] += 1
    else:
        await release(session, row)
        outcome["failed"] += 1


async def _run(now: datetime | None = None) -> dict:
    from ..db.session import session_scope

    async with session_scope() as session:
        return await run(session, now=now)


if __name__ == "__main__":  # pragma: no cover - the cron entry point
    parser = argparse.ArgumentParser(description="Send the daily to whoever is due.")
    parser.add_argument(
        "--at",
        default=None,
        help="an ISO instant to run as, for replaying an hour that was missed",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    at = datetime.fromisoformat(args.at) if args.at else None
    if at is not None and at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    print(asyncio.run(_run(at)))
