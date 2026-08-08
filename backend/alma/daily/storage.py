"""Where a written daily lives, and why it lives in the `reading` table.

**The rule is the chapter's rule, for the chapter's reason.** Somebody who
reads today's piece in the morning and opens the app again at lunch must find
the same words. `Reading`'s own docstring puts it exactly: *"Regenerating on
every view would be cheaper to build and would quietly destroy the product."*
A daily has that failure available to it twice over, because it is also *about*
a day — two different texts for the same date is not a stale cache, it is the
product contradicting itself about what is happening to somebody.

**Why not a `DailyPiece` table.** A sibling table beside `Reading` was the
obvious model and it was rejected for one concrete reason:
`alma/auth/accounts.erase` deletes a person's data by walking an explicit list
of tables, and that function lives in a file another workflow owns and this one
may not edit. `alma/db/models.py` states the consequence in its own opening
paragraph — *"a new table that holds a `user_id` and is not in it is a promise
this project has broken without noticing"* — and it would have been broken
silently, because nothing fails when a table is missing from that list. The
same is true of `GET /v1/account/export`, which reads `Reading` and would not
have read a new table, and of `merge_into`, which folds a guest account into a
signed-in one.

Storing the daily as a `Reading` gets all three correct on the day it ships,
with no contract to ask anybody for. It also inherits the `cost_cents`,
`input_tokens` and `output_tokens` columns that the spend ledger and any future
per-feature cost question both need, and the `reading_once` unique constraint
turns "written once per person per day" into a database guarantee rather than
an application convention.

**The identity is the day, not the calculation.** `readings.py` keys a stored
chapter on the facts it was written from, so that a chapter is rewritten when —
and only when — it has something new to say. The daily is the opposite: its
identity is *the date*, and it must survive the birth data being corrected, the
engine version being bumped and the scan being re-run. If the calculation were
part of the lookup, an engine bump at midnight would produce a second piece for
a day the reader has already read, which is precisely the thing being
prevented. So the lookup is `(user, system, chapter, locale)` with the date
inside `chapter`, and `calc_key` is written for provenance and never used to
find the row.

**Locale is part of the identity.** Two locales for the same day are two rows,
the same rule chapters follow. A reader who switches their phone to French gets
a French piece about the same event rather than an English one they cannot
read, and neither replaces the other.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai import cost
from ..calc.contract import cache_key
from ..db.models import Reading, UsageCounter, User

#: The daily is a transits reading, because that is what it is: the same
#: engine, the same factors, the same citable strings. Filing it under a
#: system of its own would put a ninth entry in `contract.SYSTEMS`, which is
#: the list the calculation cache, the entitlement check and the API's route
#: validation all read.
SYSTEM = "transits"

#: `Reading.chapter` is `String(64)`; "daily:2026-08-07" is sixteen.
CHAPTER_PREFIX = "daily:"

#: Day-keyed counters in `UsageCounter`, the same table and the same shape
#: `alma/billing/renewals.py` uses to make a job that runs twice send once
#: (§6.9). A row here means "a notification for this person on this day has
#: already been sent", and the primary key is `user:day:metric`, so the second
#: run of an hourly job cannot double-send even if it races the first.
PUSH_METRIC = "daily_push"


def chapter_for(on: date) -> str:
    return f"{CHAPTER_PREFIX}{on.isoformat()}"


def date_of(chapter: str) -> date | None:
    """The day a stored daily belongs to, or None if this is not one."""
    if not chapter or not chapter.startswith(CHAPTER_PREFIX):
        return None
    try:
        return date.fromisoformat(chapter[len(CHAPTER_PREFIX):])
    except ValueError:
        return None


def provenance_key(birth, *, on: date, kernel: str) -> str:
    """What this piece was written from, recorded but never looked up by.

    Kept because a reader who writes in about a piece deserves an answer better
    than "we no longer know", and because it is what would make a future
    "regenerate the ones written from the wrong ephemeris" possible. It is
    emphatically not the lookup key — see the module docstring.
    """
    return cache_key(SYSTEM, birth, chapter="daily", day=on.isoformat(), kernel=kernel)


async def stored(
    session: AsyncSession, user: User, *, on: date, locale: str
) -> Reading | None:
    """Today's piece, if it has already been written for this person."""
    return (
        await session.execute(
            select(Reading).where(
                Reading.user_id == user.id,
                Reading.system == SYSTEM,
                Reading.chapter == chapter_for(on),
                Reading.locale == locale,
            )
        )
    ).scalar_one_or_none()


def record(
    *,
    user: User,
    profile_id: str,
    on: date,
    locale: str,
    calc_key: str,
    engine_version: str,
    written,
    kernel: str = "",
) -> Reading:
    """The row, ready to be added to the session.

    `kernel` goes into the body as well as into `calc_key`, and it is not
    redundant. `calc_key` is a hash — it proves two pieces came from the same
    inputs and cannot be asked *which contact was this about*. `recent_kernels`
    asks exactly that, to stop the same contact being announced twice in a
    fortnight, and a JSON key on a column that already exists is the entire
    cost of being able to.
    """
    body = written.as_dict()
    if kernel:
        body["kernel"] = kernel
    return Reading(
        user_id=user.id,
        profile_id=profile_id,
        system=SYSTEM,
        chapter=chapter_for(on),
        locale=locale,
        calc_key=calc_key,
        engine_version=engine_version,
        model=written.model,
        body=body,
        cited_factors=list(written.cited_factors),
        input_tokens=written.spend.input_tokens,
        output_tokens=written.spend.output_tokens,
        cost_cents=written.spend.cents,
    )


# ── the counters ───────────────────────────────────────────────────────────
#
# Written against `UsageCounter` rather than a table of this package's own, for
# the reason `cost.py` gives about the spend ledger: a second store of the same
# number is a second number, and they diverge on the day it matters. The id
# format is `readings.py`'s, character for character, because two formats for
# the same primary key is two rows for the same fact.


def _counter_id(user_id: str, day: date, metric: str) -> str:
    return f"{user_id}:{day.isoformat()}:{metric}"


async def spend(session: AsyncSession, user: User, cents: float) -> None:
    """Charge a generation to the month ledger `cost.month_spend` reads.

    The metric name comes from `cost.SPEND_METRIC` rather than being written
    out here, for the reason that module gives: a typo would not fail anything,
    it would just make every account look free.
    """
    if not cents:
        return
    today = datetime.now(timezone.utc).date()
    key = _counter_id(user.id, today, cost.SPEND_METRIC)
    row = await session.get(UsageCounter, key)
    if row is None:
        row = UsageCounter(
            id=key, user_id=user.id, day=today, metric=cost.SPEND_METRIC,
            count=0, amount=0.0,
        )
        session.add(row)
    row.amount = (row.amount or 0.0) + cents
    await session.flush()


async def push_history(session: AsyncSession, user: User, *, on: date) -> list[date]:
    """The local dates a daily actually went out on, oldest first.

    A list rather than the `(last_day, count_this_month)` pair this used to
    return. The pair could express the three-day gap and the monthly cap and
    **could not express the weekly one**, which is why `selection.decide` had
    no weekly cap while `rules.PER_WEEK` was quietly enforcing 2 — the same
    shape mismatch that let the two modules drift apart. `rules.too_soon` has
    always taken a list; this now hands it one.

    Rows dated after `on` are dropped. A row in the future is a clock that
    moved backwards or a job run for tomorrow; it is not a push that has
    happened, and counting it would silence a person for three days over an
    event they never received.

    Only rows with a count above zero, matching `notify.daily.history`: a
    claimed-but-unsent row is a send that failed, and letting it suppress the
    next three days would turn one vendor timeout into four days of silence.
    """
    rows = (
        await session.execute(
            select(UsageCounter.day).where(
                UsageCounter.user_id == user.id,
                UsageCounter.metric == PUSH_METRIC,
                UsageCounter.count > 0,
            )
        )
    ).scalars().all()

    days = []
    for day in rows:
        when = day.date() if isinstance(day, datetime) else day
        if not isinstance(when, date):  # pragma: no cover - driver variance
            when = date.fromisoformat(str(when))
        if when <= on:
            days.append(when)
    return sorted(days)


async def recent_kernels(
    session: AsyncSession, user: User, *, on: date, days: int
) -> set[str]:
    """The contacts this person has already been told about, inside `days`.

    Read off the stored dailies rather than off a counter, and that is the
    whole reason `Reading` was the right table. `UsageCounter` has five columns
    and none of them can hold a kernel; a sibling table could, and would have
    reintroduced exactly the erase/export/merge problem this package refused at
    the start. The written piece *is* the record of having said something, and
    it already inherits deletion, export and account merging for free.

    Note that "written" is very slightly broader than "pushed" — a piece
    written for the Today page and never notified about also counts. That is
    the semantics wanted rather than a compromise: the question this answers is
    "have we already told this person about this contact", and putting it on
    their screen is telling them.
    """
    since = chapter_for(on - timedelta(days=days))
    rows = (
        await session.execute(
            select(Reading.body).where(
                Reading.user_id == user.id,
                Reading.system == SYSTEM,
                Reading.chapter.like(f"{CHAPTER_PREFIX}%"),
                # `chapter` is "daily:YYYY-MM-DD", so a string comparison is a
                # date comparison — ISO-8601 is ordered lexicographically and
                # the prefix is constant. Cheaper than pulling a month of rows
                # back to filter them in Python, and correct for the same
                # reason `date_of` can parse them at all.
                Reading.chapter >= since,
                # Strictly *before* today. Today's own piece is not a prior
                # announcement of itself — including it made `piece_for` refuse
                # to serve back the row it had just written, which is the one
                # invariant this whole package is built on. The question is
                # "have we already said this on an earlier day".
                Reading.chapter < chapter_for(on),
            )
        )
    ).scalars().all()

    found: set[str] = set()
    for body in rows:
        kernel = (body or {}).get("kernel")
        if kernel:
            found.add(str(kernel))
    return found


async def record_push(session: AsyncSession, user: User, *, on: date) -> bool:
    """Mark that a notification went out today. False if one already had.

    This is the idempotency the hourly job needs (§6.9). The job runs 24 times
    a day because 08:00 happens 26 times around the world, and a missed run
    must cost an hour rather than a day — which means it will sometimes run
    twice over the same person. The primary key `user:day:daily_push` is what
    makes the second run a no-op, and it is the same mechanism
    `renewals.py` uses under its own metric name.

    Returns whether this call was the one that claimed the day, so the caller
    can decide *not to send* rather than discovering afterwards that it double
    sent. Callers must record before handing anything to a transport.
    """
    key = _counter_id(user.id, on, PUSH_METRIC)
    row = await session.get(UsageCounter, key)
    if row is not None and (row.count or 0) > 0:
        return False
    if row is None:
        row = UsageCounter(
            id=key, user_id=user.id, day=on, metric=PUSH_METRIC, count=0, amount=0.0
        )
        session.add(row)
    row.count = (row.count or 0) + 1
    await session.flush()
    return True


async def written_count(session: AsyncSession, user: User) -> int:
    """How many dailies this person has stored. For tests and for support."""
    return int(
        await session.scalar(
            select(func.count())
            .select_from(Reading)
            .where(
                Reading.user_id == user.id,
                Reading.system == SYSTEM,
                Reading.chapter.like(f"{CHAPTER_PREFIX}%"),
            )
        )
        or 0
    )
