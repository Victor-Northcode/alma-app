"""The daily, end to end: is there anything, write it once, keep it, price it.

One function does the work — `piece_for` — and the shape of it is deliberately
the same as the readings router's: look for the stored row, refuse on the month
ceiling before spending anything, generate through the validating writer, store
and charge in the same transaction, and charge anyway when the generation is
refused after three paid attempts.

**What this module does not decide.** It does not decide whether a person is
allowed a daily, and it does not send anything. `may_receive` is exported for
the first and returns `docs/THE-DAILY.md §5.1`'s answer, but the call belongs
at the caller so the open product question — whether a free user who has saved
a birth gets a taste of this — stays visible at the place it would be answered
rather than buried in a helper. There is no transport here at all: APNs and FCM
are `docs/PUSH.md`'s subject, they need a device-token table that does not
exist, and this package's contract with them is a `Notification` object.

**The scan is an input, not something this module does.** §6.2: scan a year
ahead once, store the ~470 rows, re-scan monthly and on any change to birth
data. Re-scanning nightly is the same answer at 30× the cost, and a second
scanner living in this package would be a second set of numbers to keep in step
with `transits.scan`. `hits_for` exists as the convenience that does it
correctly for a caller that has nothing stored yet, and it is one line.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Sequence
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from ..ai import cost, voice, writer
from ..ai.provider import Provider
from ..ai.writer import ReadingRefused
from ..calc.contract import BirthData
from ..calc.service import chart_for
from ..db.models import Reading, User
from ..engine import transits
from ..engine.natal import NatalChart
from ..engine.transits import Hit
from . import clock, notification, selection, storage, writing
from .notification import Notification
from .selection import Decision, Occasion

log = logging.getLogger("alma.daily")

#: How far ahead a scan runs. A year, because §2.4 measured `transits.scan` at
#: 1.35 s for one — 2,663 chart-years per core-hour — and because the selection
#: rule needs to see a contact's `enters_jd` and `leaves_jd`, which a short
#: window truncates into `None` and makes unwritable-about.
SCAN_DAYS = 365


@dataclass(frozen=True, slots=True)
class Daily:
    """One person's day: what there is, what was written, and whether to push."""

    on: date
    locale: str
    occasion: Occasion
    #: `writer.Written.as_dict()`, whether freshly generated or read back.
    body: dict
    #: False when this call generated it, True when the stored row was served.
    cached: bool
    push: bool
    reason: str

    #: The local hour this is delivered at. Carried on the piece because it is
    #: what decides the *tense* of the notification title — an aspect that
    #: perfects at 03:42 has already happened when the phone buzzes at 08:00,
    #: and 39% of exact hits are in that position.
    hour: int = selection.DELIVERY_HOUR

    @property
    def teaser(self) -> str:
        return str(self.body.get("teaser") or "")

    def notification(self, *, locale: str | None = None) -> Notification:
        """The line for a lock screen. Raises if the piece has no teaser."""
        return notification.compose(
            self.occasion,
            teaser=self.teaser,
            locale=locale or self.locale,
            read_at=self.hour,
        )


def may_receive(tier: str) -> bool:
    """Whether this tier gets pushed notifications at all (§5.1).

    The owner said «для подписчиков» and `LIVING_SYSTEMS` already contains
    `transits`, so the gate is `tier_of() == "subscriber"` and nothing new is
    needed from billing. Note what is *not* gated: the Today page and its
    calculations are free per the 4.3(b) work, and §5.1 is explicit that Off is
    a delivery preference rather than a feature gate. This function answers one
    question — may we interrupt this person — and a free user who turns
    notifications on should meet the paywall, not a switch that silently does
    nothing.

    `docs/PUSH.md` leaves open whether a monthly taste should be an argument
    for the paid tier. If that is ever decided yes, this is the one line that
    changes.
    """
    return tier == "subscriber"


def hits_for(birth: BirthData, *, start: datetime | None = None, days: int = SCAN_DAYS) -> list[Hit]:
    """A year of contacts for one birth. The Moon is excluded and stays so."""
    begin = start or datetime.now(timezone.utc)
    start_jd = clock.to_jd(begin)
    return transits.scan(
        chart_for(birth),
        start_jd=start_jd,
        end_jd=start_jd + days,
        include_moon=False,
        reference_jd=start_jd,
    )


def look(
    hits: list[Hit],
    *,
    on: date,
    zone: ZoneInfo,
    preference: str = selection.OCCASIONALLY,
    hour: int = selection.DELIVERY_HOUR,
    history: Sequence[date] = (),
    recent_kernels: Sequence[str] = (),
) -> Decision:
    """What today holds, before anything has been written or charged.

    Separated from `piece_for` so that the astronomy can be asked without a
    database, a provider or a dollar — which is what the hourly job wants for
    the ~92% of person-days on which the answer is nothing, and what
    `backend/tools/daily/` needs to re-run §4.2's simulation.
    """
    return selection.decide(
        hits,
        on=on,
        zone=zone,
        preference=preference,
        hour=hour,
        history=history,
        recent_kernels=recent_kernels,
    )


async def piece_for(
    session: AsyncSession,
    user: User,
    *,
    birth: BirthData,
    profile_id: str,
    hits: list[Hit],
    on: date,
    zone: ZoneInfo,
    provider: Provider,
    model: str,
    tier: str,
    locale: str = "en",
    chart: NatalChart | None = None,
    preference: str = selection.OCCASIONALLY,
    hour: int = selection.DELIVERY_HOUR,
) -> Daily | None:
    """Today's piece for this person, written once and returned unchanged.

    Returns `None` when the sky has nothing to say, which is the common case
    and the correct one: §1.4 measured 20–36 day gaps between things worth
    saying at a defensible weight floor, and §4.1 sets the floor at zero
    notifications precisely so that nothing has to be manufactured to fill
    them. Nothing is generated, nothing is charged, and no row is written.

    The caller decides what to show for that — `words.words_for(locale)`
    carries `daily.empty.title` and `daily.empty.body` in all six languages —
    and the answer is never a piece.
    """
    decision = await decide_for(
        session, user, hits=hits, on=on, zone=zone, preference=preference, hour=hour
    )
    if decision.occasion is None:
        log.debug("nothing for %s on %s: %s", user.id, on, decision.reason)
        return None

    return await write_for(
        session,
        user,
        occasion=decision.occasion,
        birth=birth,
        profile_id=profile_id,
        provider=provider,
        model=model,
        tier=tier,
        locale=locale,
        chart=chart,
        hour=hour,
        push=decision.push,
        reason=decision.reason,
    )


async def write_for(
    session: AsyncSession,
    user: User,
    *,
    occasion: Occasion,
    birth: BirthData,
    profile_id: str,
    provider: Provider,
    model: str,
    tier: str,
    locale: str = "en",
    chart: NatalChart | None = None,
    hour: int = selection.DELIVERY_HOUR,
    push: bool = True,
    reason: str = "",
) -> Daily:
    """The piece for one occasion somebody else has already chosen.

    `piece_for` decides *and* writes. This writes for a decision already made,
    and it exists because the notification job makes that decision through
    `alma/notify/rules.py` — which is the authority, and which knows things
    `selection.decide` does not: the entitlement, the dormancy, the stored
    preference, whether this is even the person's hour.

    Without this seam the job had two bad options: call `piece_for` and have
    the astronomy decided twice by two rules that must then be kept in step, or
    send a notification with no piece behind it. It took the second, which is
    how the shipped push came to be a lock-screen line pointing at a reading
    that was never written, costing nothing and recorded nowhere.

    Everything from here down is `piece_for`'s body unchanged: the stored row
    first, the month ceiling before any spending, the validating writer, and
    the charge-anyway on a refusal.
    """
    language = _language(locale)
    on = occasion.on

    kept = await storage.stored(session, user, on=on, locale=language)
    if kept is not None:
        # Written once, returned forever — the same rule and the same reason as
        # a paid chapter. Somebody who reads this twice must not find two
        # different days.
        return Daily(
            on=on,
            locale=language,
            occasion=occasion,
            body=kept.body,
            cached=True,
            push=push,
            reason=reason,
            hour=hour,
        )

    natal = chart if chart is not None else chart_for(birth)
    result = writing.brief(occasion, chart=natal, birth=birth)
    chapter = writing.chapter_for(language)

    # Both ceilings, in the order they cost. `cost.guard` is inside
    # `writer.write` and bounds this one call; `guard_month` bounds this
    # account across the calendar month and is the only one that can catch the
    # case the daily actually creates — a subscriber for whom this runs every
    # day, each generation individually cheap. §2.3 says thirty of these is
    # $0.32 against a $3.50 ceiling with $1.89 already committed to chat, so a
    # person who somehow triggers thirty in a day meets this, not the invoice.
    await cost.guard_month(
        session, user, tier=tier, projected=_projection(result, chapter, model=model, locale=language)
    )

    try:
        written = await writing.write(
            occasion,
            chart=natal,
            birth=birth,
            provider=provider,
            model=model,
            locale=language,
        )
    except ReadingRefused as exc:
        # Three attempts really happened and really cost money. Charged and
        # committed before the refusal travels, for the reason
        # `readings._charge_anyway` gives: the refusal path spends *more* than
        # the success path — it is the one that retried — so a ledger that only
        # sees the requests that worked is a ceiling on what an account can
        # spend *usefully*, which is not a ceiling.
        #
        # Unlike `_charge_anyway` there is deliberately **no rollback** first.
        # That call has to discard a half-written `Reading` before it commits,
        # because the router builds one on the way through. This function adds
        # nothing to the session until after the generation has succeeded, so
        # there is no wreckage to throw away — and rolling back anyway would
        # discard whatever the *caller* had pending, which for the hourly job
        # walking a list of subscribers is somebody else's work.
        await storage.spend(session, user, exc.spend.cents)
        await session.commit()
        log.warning("daily refused for %s on %s: %s", user.id, on, exc)
        raise

    # Built once and both stored and returned, rather than `as_dict()` twice.
    # The row carries one key the bare dict does not — the kernel — and the
    # invariant this package exists for is that the same day asked twice is the
    # same piece. Two constructions of "the same" body is how that stops being
    # true without anything failing.
    row = storage.record(
        user=user,
        profile_id=profile_id,
        on=on,
        locale=language,
        calc_key=storage.provenance_key(birth, on=on, kernel=occasion.kernel),
        engine_version=result.engine_version,
        written=written,
        kernel=occasion.kernel,
    )
    session.add(row)
    await storage.spend(session, user, written.spend.cents)
    await session.flush()

    return Daily(
        on=on,
        locale=language,
        occasion=occasion,
        body=row.body,
        cached=False,
        push=push,
        reason=reason,
        hour=hour,
    )


async def decide_for(
    session: AsyncSession,
    user: User,
    *,
    hits: list[Hit],
    on: date,
    zone: ZoneInfo,
    preference: str = selection.OCCASIONALLY,
    hour: int = selection.DELIVERY_HOUR,
) -> Decision:
    """`look`, with the push history and what has already been said read back.

    Two reads, and they answer two different questions. `push_history` is *how
    often* we have interrupted this person, which is the cadence. `recent_kernels`
    is *what we have already told them*, which is the repeat — measured at 18%
    of all pushes before it existed, almost all of it the enters→perfects pair
    for one contact arriving a week apart.
    """
    return look(
        hits,
        on=on,
        zone=zone,
        preference=preference,
        hour=hour,
        history=await storage.push_history(session, user, on=on),
        recent_kernels=await storage.recent_kernels(
            session, user, on=on, days=selection.RECENT_KERNEL_DAYS
        ),
    )


async def claim_push(session: AsyncSession, user: User, *, on: date) -> bool:
    """Take today's one send slot, or report that it was already taken.

    Call this *before* handing anything to a transport, never after. The hourly
    job (§6.9) will sometimes run twice over the same person — that is the
    price of a job whose missed run costs an hour instead of a day — and the
    difference between claiming first and recording afterwards is the
    difference between a no-op and a second notification.
    """
    return await storage.record_push(session, user, on=on)


def _language(locale: str) -> str:
    """The resolved tag, decided once and used for the prompt and the row.

    `Reading.locale` is a `String(8)` column, and `readings.py` learned the
    rest of this the expensive way: a lookup on the raw tag misses the row
    written for the resolved one, so a reader whose phone reports "de-AT" is
    charged for a second copy of German they already have. Here that would be a
    second piece about the same day, which is worse than a duplicate charge.
    """
    from .. import i18n

    return i18n.resolve(locale)


def _projection(result, chapter, *, model: str, locale: str) -> float:
    """What this generation is expected to cost, for the month ceiling.

    Built from the real prompt rather than an average, because the whole point
    of checking before the call is that the estimate and the call agree about
    what is being priced. `paid=False` and `register="daily"` mirror
    `writing.write` exactly; a projection computed against a different system
    prompt would be a projection of a call nobody makes.
    """
    offered = [f for f in result.factors if any(r in f.lower() for r in writing.READS)]
    prompt = writer.build_prompt(result, chapter, offered=offered, locale=locale)
    system = voice.system_prompt(locale=locale, paid=False, register="daily")
    return cost.estimate(
        model,
        prompt_chars=len(prompt) + len(system),
        max_output_tokens=min(4096, chapter.words[1] * 3 + 600),
    )


def stored_body(row: Reading) -> dict:
    return row.body or {}


# ── the contract `alma/notify/` consumes ───────────────────────────────────
#
# `alma/notify/daily.py::_selector` names it exactly:
#
#     async def candidates(session, user, *, on: date) -> Sequence[Candidate]
#
# and states the boundary it draws — **the astronomy is this package's and the
# cadence is that one's**. That split is worth honouring rather than
# renegotiating: it is what lets their caps be tested without an ephemeris and
# these scans be tested without a calendar, and their job raises
# `PushUnavailable` rather than silently sending nothing when this function is
# missing, which is the right failure and one somebody has to answer.
#
# Note what "unfiltered by weight" means here and why it is right. Everything
# the sky offers on the day goes back, including the Mercury contacts §1.3
# measured as 55% of the volume and 4% of the meaning. `rules.pick` applies the
# floors, and it must be the only thing that does — two modules each dropping
# "the obviously irrelevant ones" is how a floor of 0.35 quietly becomes 0.35
# applied twice to different sets.


@dataclass(frozen=True, slots=True)
class Candidate:
    """One contact on one local day, in the shape `notify.rules` expects.

    The seven fields above `hit` are `rules.Candidate`'s protocol, named as it
    names them — which is `Hit`'s names where `Hit` has them, because the
    engine is the source and renaming a field between two packages is how the
    two stop meaning the same thing.

    `hit` and `occasion` are extra and deliberately so. A structural protocol
    ignores them, and they are what lets the job hand the chosen contact
    straight back to `piece_for` without a second scan of the same sky.
    """

    transiting: str
    natal: str
    aspect: str
    weight: float
    exact: bool
    entering: bool
    exact_at: datetime

    hit: Hit
    occasion: Occasion


def birth_of(profile) -> BirthData:
    """A `Profile` row as birth data.

    Mirrors `api/deps.birth_from_profile` rather than importing it. That module
    is FastAPI's — it raises `HTTPException` and pulls the whole HTTP layer in
    with it — and this package's principal caller is a background job with no
    request anywhere near it. It is also a file another workflow owns, so an
    import would be a dependency on something that can change underneath this.
    Eight lines of duplication is the cheaper of the two.
    """
    when = profile.birth_date
    if not isinstance(when, date):  # pragma: no cover - driver variance
        when = date.fromisoformat(str(when))
    return BirthData(
        date=when,
        time=profile.birth_time,
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone=profile.timezone,
        place_label=profile.place_label,
        name=profile.name,
    )


async def self_profile(session: AsyncSession, user: User):
    """The chart the daily is about: this person's own.

    Not any of the others. `Profile` also holds the partners and friends
    somebody added to compare against, and a daily about a friend's transits
    would be both wrong and, per `voice.py`'s third rule, a claim about
    somebody who did not ask.
    """
    from sqlalchemy import select

    from ..db.models import Profile

    rows = (
        await session.execute(
            select(Profile).where(Profile.user_id == user.id).order_by(Profile.created_at)
        )
    ).scalars().all()
    for profile in rows:
        if profile.is_self:
            return profile
    return rows[0] if rows else None


async def candidates(
    session: AsyncSession, user: User, *, on: date, zone: ZoneInfo | None = None
):
    """Everything the sky offers this person on this local date, unfiltered.

    A three-day scan rather than the year `piece_for` is given, and the reason
    is worth stating because it looks like a shortcut. §6.2's year-ahead scan
    exists so the *windows* are known — `enters_jd` and `leaves_jd` are only
    populated when the boundary falls inside the scanned span, and a piece that
    says "in orb since March" needs that. This function is asked a narrower
    question: what perfects or opens today. Both are answered by a window that
    brackets the day, at 1/100th of the cost — which matters because the job
    that calls this runs hourly over every due subscriber, and §1.2 measured
    that ~92% of those calls will find nothing worth a notification.

    Returns `[]` for a person with no saved birth rather than raising. The job
    walks a list of device tokens and one profile-less account must not stop
    the run.

    **`zone` is the sender's answer, not a preference.** `on` is a date the
    caller already resolved in somebody's clock, and bracketing it in a
    different one is how a piece gets filed under the wrong day. The sender has
    the better answer — it holds the device rows, so its ladder reaches the
    rung this one cannot: `Profile.timezone` is the *birth* zone, and for
    everybody who has moved it is wrong by however many hours they flew. Left
    out, the ladder here still resolves, which keeps a direct caller and a test
    honest without a device table.
    """
    profile = await self_profile(session, user)
    if profile is None:
        return []

    birth = birth_of(profile)
    if zone is None:
        zone, _source = clock.zone_for(
            chosen=getattr(user, "daily_timezone", None), birth=profile.timezone
        )
    start_jd, end_jd = clock.day_bounds(on, zone)
    hits = transits.scan(
        chart_for(birth),
        start_jd=start_jd - 1.0,
        end_jd=end_jd + 1.0,
        include_moon=False,
        reference_jd=start_jd,
    )

    found: list[Candidate] = []
    for hit in hits:
        exact = clock.local_date(hit.exact_jd, zone) == on
        entering = (
            hit.enters_jd is not None and clock.local_date(hit.enters_jd, zone) == on
        )
        if not (exact or entering):
            continue
        occasion = selection.occasion_for(
            [hit], on=on, zone=zone, floor=0.0, slow_entry_floor=0.0
        )
        if occasion is None:  # pragma: no cover - defensive
            continue
        found.append(
            Candidate(
                transiting=hit.transiting,
                natal=hit.natal,
                aspect=hit.aspect,
                weight=hit.weight,
                exact=exact,
                entering=entering,
                exact_at=clock.from_jd(hit.exact_jd),
                hit=hit,
                occasion=occasion,
            )
        )
    return found
