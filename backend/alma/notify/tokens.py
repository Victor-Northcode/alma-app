"""Device tokens: registering them, and — the part that matters — retiring them.

Registration is the easy half and nobody gets it wrong. The half every push
system gets wrong is the other one: a token that has stopped working is
retried every morning forever, the table grows monotonically, the vendor's
error rate climbs, and nothing anywhere reports a problem because each
individual failure is handled. That is the leak this module exists to close,
and it closes it in three separate ways because no single one of them is
enough:

1. **A dead token is deleted the moment the vendor says so.** `410` from Apple
   or `UNREGISTERED` from Google is not an error to log, it is a fact about a
   row.
2. **A token nobody has re-registered in ninety days is deleted whether or not
   it ever errored.** Apple expires nothing on our behalf and Google's 270-day
   collection is far too patient to be useful. The client re-registers on every
   launch, so a stale `last_seen_at` means the app is gone or the person is —
   and either way we are holding an identifier we cannot use.
3. **A token that is alive but unreachable is disabled rather than deleted.**
   Wrong environment, wrong topic, wrong Firebase project: the device is fine
   and the client will hand us the identical token on its next launch, so
   deleting it produces a loop instead of a fix.

**Ninety days, and not thirty.** Google's own guidance for non-Android
platforms suggests sweeping registrations idle for about a month. That number
is written for apps people open daily, and it would delete the token of a
subscriber who did not open Alma for six weeks — who is precisely the person
this feature exists for. Ninety still bounds the retention, still satisfies
"do not hold what you cannot use", and is comfortably longer than the sixty
days at which `rules.py` stops sending to a dormant person anyway. The order
of those two numbers is the design: **we go quiet first and forget second.**

**The row is the consent.** Turning the daily off deletes it. Not a flag
consulted before sending — the row, because Apple's guideline 4.5.4 requires
an in-app way to stop receiving push and the only unarguable proof that off
means off is that there is nothing left to send to.

`forget` is the sentence `accounts.erase` has to say. It is a function here
rather than a seventh table in that function's loop for the same reason
`funnel.forget` is: this module owns which table its rows live in.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import DeviceToken, as_utc, utcnow
from .transport import PLATFORMS, Receipt, Verdict

log = logging.getLogger("alma.notify.tokens")

#: How long a token survives without the client saying hello again.
SWEEP_AFTER = timedelta(days=90)

#: The two words `DeviceToken.environment` may hold. Android has no such
#: distinction and is written "production" rather than left null, so nothing
#: downstream has to treat the column as a three-state.
ENVIRONMENTS = ("production", "sandbox")

#: A device token is opaque, but it is not free text. Apple's is 64 hex
#: characters today and has been longer before; Google's is base64url with a
#: colon in it and runs past 160. Both are ASCII and neither contains
#: whitespace. The bound exists because this string is interpolated into a URL
#: path and stored in a column, and "opaque" is not a reason to accept 40 kB.
_TOKEN = re.compile(r"^[A-Za-z0-9_:.\-]{32,512}$")


class BadToken(ValueError):
    """The client sent something that cannot be a device token."""


def clean(platform: str, token: str, *, environment: str | None = None) -> tuple[str, str, str]:
    """Normalise and check a registration, or refuse it with a reason."""
    key = (platform or "").strip().lower()
    if key not in PLATFORMS:
        raise BadToken(f"platform must be one of {', '.join(PLATFORMS)}")
    value = (token or "").strip()
    if not _TOKEN.match(value):
        raise BadToken("that is not a device token")
    if key == "android":
        # Meaningless on Android; written rather than nulled — see ENVIRONMENTS.
        return key, value, "production"
    where = (environment or "").strip().lower() or "production"
    if where not in ENVIRONMENTS:
        raise BadToken(f"environment must be one of {', '.join(ENVIRONMENTS)}")
    return key, value, where


async def register(
    session: AsyncSession,
    *,
    user_id: str,
    platform: str,
    token: str,
    environment: str | None = None,
    timezone: str | None = None,
    locale: str | None = None,
    app_version: str | None = None,
    os_version: str | None = None,
) -> DeviceToken:
    """Record this install, or update what we already knew about it.

    **Keyed on the token, not on the user**, and that is what makes the second
    account on one phone safe. A person who signs out and signs in as somebody
    else hands us the same device token under a new `user_id`; a row per
    (user, token) would leave the old account still pointing at the phone, and
    the phone would get two dailies about two different charts. The row moves.

    Every field is refreshed on every call, because the client re-registers on
    every launch and that is the only moment a travelling person's timezone,
    a changed system language or a new OS version becomes knowable. Google's
    guidance is to stamp a timestamp on every upload whether or not the token
    changed, and this is that stamp.

    Re-registering also **clears a disabled row**. If the reason it was
    disabled was an environment mismatch, a fresh registration from a rebuilt
    app is exactly the event that fixes it, and leaving the row disabled would
    make the fix invisible.
    """
    key, value, where = clean(platform, token, environment=environment)

    row = (
        await session.execute(
            select(DeviceToken).where(
                DeviceToken.platform == key, DeviceToken.token == value
            )
        )
    ).scalars().first()

    if row is None:
        row = DeviceToken(user_id=user_id, platform=key, token=value)
        session.add(row)
    elif row.user_id != user_id:
        log.info("device token moved from user %s to %s", row.user_id, user_id)
        row.user_id = user_id

    row.environment = where
    row.last_seen_at = utcnow()
    row.disabled_at = None
    row.disabled_reason = None
    row.fail_count = 0
    if timezone:
        row.timezone = timezone
    if locale:
        row.locale = locale
    if app_version:
        row.app_version = app_version
    if os_version:
        row.os_version = os_version
    await session.flush()
    return row


async def remove(session: AsyncSession, *, platform: str, token: str, user_id: str) -> bool:
    """Turn it off. Scoped to the owner so a token id is not a weapon.

    Without the `user_id` condition this endpoint would let anybody who
    learned a token silence somebody else's notifications — and a device token
    is exactly the sort of string that turns up in a crash log.
    """
    key, value, _ = clean(platform, token)
    result = await session.execute(
        delete(DeviceToken).where(
            DeviceToken.platform == key,
            DeviceToken.token == value,
            DeviceToken.user_id == user_id,
        )
    )
    return bool(result.rowcount)


async def forget(session: AsyncSession, user_id: str) -> None:
    """Delete every device this account ever registered.

    **`accounts.erase` must call this.** `db/models.py` says in its own opening
    paragraph that a table holding a `user_id` and missing from that function
    is "a promise this project has broken without noticing", and a push token
    is a persistent per-device identifier — the most obviously personal thing
    in the schema after the birth data itself. The call is one line in
    `erase`, and it is not made here because that file belongs to another
    workflow; until it lands, this table is the exception that file's docstring
    warns about.
    """
    await session.execute(delete(DeviceToken).where(DeviceToken.user_id == user_id))


async def for_user(session: AsyncSession, user_id: str) -> list[DeviceToken]:
    """Every device this person can be reached on right now."""
    rows = await session.execute(
        select(DeviceToken).where(
            DeviceToken.user_id == user_id, DeviceToken.disabled_at.is_(None)
        )
    )
    return list(rows.scalars().all())


async def succeeded(session: AsyncSession, row: DeviceToken) -> None:
    """The vendor accepted it. Which is not the same as it having arrived."""
    row.last_success_at = utcnow()
    row.fail_count = 0
    await session.flush()


async def retire(session: AsyncSession, row: DeviceToken, receipt: Receipt) -> str:
    """Apply one vendor answer to one row. Returns what was done, for the log.

    **The 410 rule is the whole reason this is a function and not two lines.**
    Apple's own wording is "no need to retry unless the app retrieves the same
    device token again", and that sentence is a comparison, not a delete: the
    body carries the millisecond timestamp at which the token stopped being
    valid, and if the client has registered *since* then, the app is alive and
    has told us so more recently than APNs told us otherwise.

    Getting this wrong is not theoretical and it is silent. Somebody deletes
    the app on Monday, reinstalls on Tuesday, the app registers the same token,
    and a queue drained on Wednesday deletes the row on the strength of
    Monday's 410. They stop receiving the thing they are paying for and nothing
    anywhere reports an error.
    """
    if receipt.verdict is Verdict.sent:
        await succeeded(session, row)
        return "sent"

    if receipt.verdict is Verdict.dead:
        seen = as_utc(row.last_seen_at)
        if receipt.dead_since is not None and seen is not None and seen > receipt.dead_since:
            log.info(
                "keeping device token %s: %s says it died at %s, the app "
                "registered again at %s",
                row.id, receipt.reason, receipt.dead_since.isoformat(), seen.isoformat(),
            )
            return "kept"
        await session.delete(row)
        await session.flush()
        return "deleted"

    if receipt.verdict is Verdict.disable:
        row.disabled_at = utcnow()
        # Truncated because it is a vendor's word going into a fixed column,
        # and the width of somebody else's vocabulary is not ours to promise.
        row.disabled_reason = (receipt.reason or "refused")[:64]
        row.fail_count += 1
        await session.flush()
        return "disabled"

    # `retry` and `fatal` both leave the row alone. A vendor having a bad
    # afternoon is not evidence about a device, and a wrong credential is
    # evidence about us.
    row.fail_count += 1
    await session.flush()
    return receipt.verdict.value


async def sweep(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Delete every token nobody has re-registered inside `SWEEP_AFTER`.

    Run from the same hourly job. It is a single `DELETE … WHERE` rather than
    a walk, because it must stay cheap enough that nobody is ever tempted to
    run it "occasionally" — a retention rule that runs occasionally is a
    retention rule that is false on the day somebody checks.
    """
    cutoff = (now or utcnow()) - SWEEP_AFTER
    result = await session.execute(
        delete(DeviceToken).where(DeviceToken.last_seen_at < cutoff),
        # Not a performance flag. SQLAlchemy's default is to work out which
        # already-loaded objects the DELETE matched by evaluating the criteria
        # in Python — and on SQLite the loaded value is naive while `cutoff` is
        # aware, so the comparison raises `can't compare offset-naive and
        # offset-aware datetimes` and takes the whole run with it. The same
        # statement is fine on Postgres, which is exactly the shape of bug
        # `as_utc` exists for. Nothing in this job reads a token after the
        # sweep, so there is no session state worth synchronising.
        execution_options={"synchronize_session": False},
    )
    count = int(result.rowcount or 0)
    if count:
        log.info("swept %d device tokens unseen since %s", count, cutoff.date())
    return count
