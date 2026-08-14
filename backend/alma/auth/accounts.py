"""Accounts: guest-first, no passwords, and a merge that cannot lose anything.

The flow the product needs is unusual enough to be worth stating. A person
arrives, enters a birth date, and gets a reading — with no account, no email
and no interruption. That reading has to survive them signing in later, on
possibly a different device, into an account they may already have.

So: the guest **is** an account from the first request. Signing in either
attaches an identity to that row, or — if the identity already belongs to
another row — folds the guest into it. `merge` is the interesting function
and the one place data can be lost, so it moves everything and then marks the
guest as merged rather than deleting it, which keeps old tokens working.

There are no passwords anywhere in this module. Nothing to leak, nothing to
reset, nothing to get wrong.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..funnel import forget
from ..db.models import (
    AuthProvider,
    ChatThread,
    Consent,
    DeviceToken,
    Entitlement,
    Event,
    MagicLink,
    Memory,
    Profile,
    Purchase,
    Reading,
    UsageCounter,
    User,
    WebhookEvent,
    as_utc,
    utcnow,
)


class AccountDeleted(Exception):
    """The account behind this token has been erased."""


async def create_guest(session: AsyncSession, *, locale: str = "en") -> User:
    user = User(provider=AuthProvider.guest.value, locale=locale)
    session.add(user)
    await session.flush()
    return user


async def resolve(session: AsyncSession, user_id: str) -> User | None:
    """The live user behind an id, following any merge.

    A person who used the app as a guest and then signed in on another device
    still holds a token for the guest row. Following the merge pointer keeps
    that token working instead of logging them out — which, if it happened
    during a checkout, would look exactly like the payment failing.
    """
    seen: set[str] = set()
    current = await session.get(User, user_id)
    while current is not None and current.merged_into_id and current.id not in seen:
        seen.add(current.id)
        current = await session.get(User, current.merged_into_id)

    if current is None:
        return None
    if current.deleted_at is not None:
        raise AccountDeleted(f"account {current.id} has been deleted")
    return current


async def by_email(session: AsyncSession, email: str) -> User | None:
    normalised = email.strip().lower()
    result = await session.execute(
        select(User).where(User.email == normalised, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def by_provider(session: AsyncSession, provider: str, subject: str) -> User | None:
    result = await session.execute(
        select(User).where(
            User.provider == provider,
            User.provider_subject == subject,
            User.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def sign_in(
    session: AsyncSession,
    *,
    email: str,
    provider: str,
    subject: str | None = None,
    display_name: str | None = None,
    guest: User | None = None,
) -> User:
    """Attach an identity, folding in a guest session if there is one.

    Three cases, and the third is the one that matters:

    1. Nobody has this identity and there is no guest — a new account.
    2. Nobody has this identity and there is a guest — the guest becomes the
       account. Nothing moves; the row simply gains an email.
    3. Somebody already has this identity — the guest is merged into them.
    """
    normalised = email.strip().lower()
    existing = await by_email(session, normalised)

    if existing is None and guest is not None and guest.is_guest:
        guest.email = normalised
        guest.provider = provider
        guest.provider_subject = subject
        guest.display_name = display_name or guest.display_name
        guest.last_seen_at = utcnow()
        await session.flush()
        return guest

    if existing is None:
        user = User(
            email=normalised,
            provider=provider,
            provider_subject=subject,
            display_name=display_name,
            locale=guest.locale if guest else "en",
        )
        session.add(user)
        await session.flush()
        return user

    # The identity is already ours. Keep the provider fresh — someone may have
    # started with a magic link and later used Google.
    existing.provider = provider
    existing.provider_subject = subject or existing.provider_subject
    existing.display_name = display_name or existing.display_name
    existing.last_seen_at = utcnow()

    if guest is not None and guest.id != existing.id and guest.is_guest:
        await merge(session, source=guest, target=existing)

    await session.flush()
    return existing


async def merge(session: AsyncSession, *, source: User, target: User) -> None:
    """Move everything from one account into another.

    The source is marked as merged rather than deleted so that a token issued
    for it keeps resolving — a person mid-checkout on their phone must not be
    logged out because they signed in on a laptop.

    The source's own birth profile stops being "self" on the way across:
    otherwise the target ends up with two selves and every subsequent reading
    has to guess which one the person meant.
    """
    if source.id == target.id:
        return

    await session.execute(
        update(Profile)
        .where(Profile.user_id == source.id)
        .values(user_id=target.id, is_self=False)
    )
    # `Event` and `Consent` are in this list for the same reason the other six
    # are: they carry a `user_id` and they are the same person's. The funnel
    # folds merged ids when it reads, so its numbers were right either way — but
    # anything else querying the table directly saw one person as two, and a
    # consent left behind on the guest row is evidence detached from the account
    # that holds the purchase it belongs to.
    # `DeviceToken` is in this list for a reason the others are not: a merged
    # row is not `is_active`, and `notify.daily.due()` filters on that, so a
    # phone left behind on the guest account silently stops being reachable.
    # It is self-healing — the next launch re-registers and `tokens.register`
    # is keyed on (platform, token), so the row moves by itself — but "self-
    # healing" here means the subscriber loses up to a day of the thing they
    # are paying for, and it is the same class of omission as the erase gap.
    for table in (Entitlement, Reading, ChatThread, Memory, Event, Consent, DeviceToken):
        await session.execute(
            update(table).where(table.user_id == source.id).values(user_id=target.id)
        )
    await session.execute(
        update(Purchase).where(Purchase.user_id == source.id).values(user_id=target.id)
    )
    await session.execute(
        update(WebhookEvent)
        .where(WebhookEvent.user_id == source.id)
        .values(user_id=target.id)
    )

    # If the target had no birth data of its own, the guest's becomes it.
    has_self = await session.execute(
        select(Profile.id).where(Profile.user_id == target.id, Profile.is_self.is_(True))
    )
    if has_self.first() is None:
        moved = await session.execute(
            select(Profile)
            .where(Profile.user_id == target.id)
            .order_by(Profile.created_at)
            .limit(1)
        )
        first = moved.scalar_one_or_none()
        if first is not None:
            first.is_self = True

    source.merged_into_id = target.id
    source.email = None            # free the address for the surviving row
    await session.flush()


#: How stale `last_seen_at` is allowed to get before a request rewrites it.
#:
#: Nothing reads this column to the minute — it answers "is this account still
#: in use", which an hour resolves as well as a second does.
TOUCH_INTERVAL = timedelta(hours=1)


async def touch(session: AsyncSession, user: User) -> None:
    """Note that this account is alive — at most once an hour.

    **It used to write on every single request, and that was a real fault
    rather than an inefficiency.** The iOS app opens its first screen with four
    requests at once — transits, natal, synthesis, and the free transits
    chapter — and every one of them arrived here and issued
    `UPDATE user SET last_seen_at` against the same row. On SQLite that is four
    writers on one database: the first takes the write lock, the others are
    already holding a read lock inside their own transaction, and SQLite fails
    a lock upgrade immediately rather than waiting, so `busy_timeout` does not
    save them. Two of the four blocks on the first screen of the product came
    back "database is locked", every launch, on a fresh install.

    Making it conditional removes the write from all but one request an hour,
    which removes the contention entirely for the traffic a single person
    generates. It is not a substitute for Postgres under real concurrency —
    SQLite has one writer whatever we do — but it stops a *single user* from
    colliding with themselves, which is what was actually happening.

    Comparing in Python rather than with an `UPDATE … WHERE last_seen_at <`:
    the row is already loaded and already in the session, so this costs nothing
    and issues no statement at all in the common case.
    """
    seen = as_utc(user.last_seen_at)
    now = utcnow()
    if seen is not None and now - seen < TOUCH_INTERVAL:
        return
    user.last_seen_at = now


async def set_locale(session: AsyncSession, user: User, locale: str) -> None:
    user.locale = locale
    await session.flush()


# ── the user's own data, on request ────────────────────────────────────────

async def export(session: AsyncSession, user: User) -> dict:
    """Everything we hold about one person, in one JSON document.

    Self-service and complete. A person should never have to ask a human for
    their own data, and an export that quietly omits the readings they paid
    for is not an export.
    """
    profiles = (
        await session.execute(select(Profile).where(Profile.user_id == user.id))
    ).scalars().all()
    entitlements = (
        await session.execute(select(Entitlement).where(Entitlement.user_id == user.id))
    ).scalars().all()
    readings = (
        await session.execute(select(Reading).where(Reading.user_id == user.id))
    ).scalars().all()
    # **`selectinload`, а не ленивая связь.**
    #
    # Реплики читаются ниже, при сборке словаря, и ленивая загрузка в
    # asyncio — это `MissingGreenlet`, то есть 500. Выгрузка ломалась у
    # каждого, у кого есть хоть одна беседа; тесты этого не ловили, потому что
    # экспортировали аккаунт без бесед — путь просто не выполнялся. Поймано на
    # симуляторе: «Файл не собрался».
    threads = (
        await session.execute(
            select(ChatThread)
            .where(ChatThread.user_id == user.id)
            .options(selectinload(ChatThread.messages))
        )
    ).scalars().all()
    memories = (
        await session.execute(select(Memory).where(Memory.user_id == user.id))
    ).scalars().all()
    purchases = (
        await session.execute(select(Purchase).where(Purchase.user_id == user.id))
    ).scalars().all()
    devices = (
        await session.execute(select(DeviceToken).where(DeviceToken.user_id == user.id))
    ).scalars().all()

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "account": {
            "id": user.id,
            "email": user.email,
            "provider": user.provider,
            "display_name": user.display_name,
            "locale": user.locale,
            "created_at": user.created_at.isoformat(),
        },
        "profiles": [
            {
                "id": p.id,
                "name": p.name,
                "relation": p.relation,
                "is_self": p.is_self,
                "birth_date": p.birth_date.isoformat(),
                "birth_time": p.birth_time,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "timezone": p.timezone,
                "place": p.place_label,
            }
            for p in profiles
        ],
        "entitlements": [
            {
                "system": e.system,
                "kind": e.kind,
                "granted_at": e.granted_at.isoformat(),
                "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            }
            for e in entitlements
        ],
        "purchases": [
            {
                "transaction_id": p.transaction_id,
                "product": p.product,
                "status": p.status,
                "amount_cents": p.amount_cents,
                "currency": p.currency,
                "created_at": p.created_at.isoformat(),
            }
            for p in purchases
        ],
        "readings": [
            {
                "system": r.system,
                "chapter": r.chapter,
                "locale": r.locale,
                "created_at": r.created_at.isoformat(),
                "body": r.body,
            }
            for r in readings
        ],
        # **Not the token string.** A push token is a live delivery credential
        # — anybody holding it and our APNs key can send to that phone — and
        # handing it back inside a file a person may email themselves or store
        # in a cloud drive would be creating copies of a secret in order to
        # honour a transparency request. What Article 15 asks for is that the
        # subject knows what is held about them, and "a device registered for
        # notifications, this platform, this locale, first seen then, last
        # seen then" is that, completely. It was omitted altogether, which the
        # privacy page's "everything we hold about you" made a real gap.
        "devices": [
            {
                "description": "a device registered for notifications",
                "platform": d.platform,
                "environment": d.environment,
                "timezone": d.timezone,
                "locale": d.locale,
                "app_version": d.app_version,
                "os_version": d.os_version,
                "created_at": d.created_at.isoformat(),
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
            }
            for d in devices
        ],
        "conversations": [
            {
                "id": t.id,
                "title": t.title,
                "created_at": t.created_at.isoformat(),
                "messages": [
                    {
                        "role": m.role,
                        "body": m.body,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in t.messages
                ],
            }
            for t in threads
        ],
        "memory": [
            {"kind": m.kind, "body": m.body, "created_at": m.created_at.isoformat()}
            for m in memories
        ],
    }


async def erase(session: AsyncSession, user: User) -> None:
    """Delete a person's data for real.

    `deleted_at` is set *and* the rows go. The flag exists so that a token
    presented a second later gets a clear answer instead of a confusing 404,
    not as a way to keep data somebody asked us to destroy.

    **What survives is the record of a contract, and nothing that says who
    entered into it.** A payment record is an obligation we cannot delete
    unilaterally — it is a tax record and the other side of somebody else's
    books — so `Purchase` keeps its row with `user_id` cleared. That sentence
    used to be the whole story and it was not true: `Purchase.payload` and
    `WebhookEvent.payload` store the processor's delivery **verbatim**, which
    carries the buyer's name, email address, billing country and our own
    `custom_data.user_id`. A deleted account was therefore fully
    re-identifiable from the row we described as detached, and a second table
    nothing here touched held the same thing again. So both payloads are
    redacted here, and the structured columns beside them — provider, amount,
    currency, country, transaction id, dates — are what the accounting actually
    reads.

    The two tables that predate this function and were never added to it go
    too. `Event` is the funnel, `UsageCounter` is the per-day counters and the
    record of which one-off offers a person was shown; both are keyed to the
    `user` row, and that row is kept as a tombstone so no CASCADE was ever
    going to fire on them. `MagicLink` is the one that mattered most: it holds
    the raw address, indefinitely, in the sign-in table — the address the
    person just asked us to delete.

    A `Consent` that never became a purchase is deleted rather than detached:
    somebody who ticked two boxes and closed the tab entered into nothing, so
    the row is evidence of nothing. One that a payment claimed is part of the
    contract record and is detached with the purchase it belongs to.
    """
    from sqlalchemy import delete

    await session.execute(
        update(Purchase)
        .where(Purchase.user_id == user.id)
        .values(user_id=None, payload=_REDACTED)
    )
    await session.execute(
        update(WebhookEvent)
        .where(WebhookEvent.user_id == user.id)
        .values(user_id=None, payload=_REDACTED)
    )
    await session.execute(
        update(Consent)
        .where(Consent.user_id == user.id, Consent.transaction_id.is_not(None))
        .values(user_id=None)
    )
    for table in (Reading, ChatThread, Memory, Entitlement, Profile, UsageCounter):
        await session.execute(delete(table).where(table.user_id == user.id))
    await session.execute(delete(Consent).where(Consent.user_id == user.id))
    # Through the funnel's own function rather than a seventh line in the loop
    # above: that module owns which table its rows live in, and its docstring
    # already names this as the place the call belongs.
    await forget(session, user.id)
    # And the devices, for exactly the same reason. `notify/tokens.py` says in
    # its own docstring that this call is the one line that was missing, and
    # `models.py`'s opening paragraph says a table holding a `user_id` and
    # absent from this function is "a promise this project has broken without
    # noticing" — which is what had happened: a push token survived an erasure
    # verbatim. It is a persistent per-device identifier tied to a person, so
    # retaining it after an Article 17 request is a failure, and it
    # contradicts both store filings and the privacy page, all three of which
    # say it is deleted with the account.
    #
    # Imported here rather than at the top for the reason `sqlalchemy.delete`
    # is: `alma.notify` reaches for a vendor client on the way up, and this
    # module is imported by everything.
    from ..notify.tokens import forget as forget_devices

    await forget_devices(session, user.id)
    if user.email:
        await session.execute(delete(MagicLink).where(MagicLink.email == user.email))
    await session.execute(delete(MagicLink).where(MagicLink.guest_user_id == user.id))

    user.deleted_at = utcnow()
    user.email = None
    user.provider_subject = None
    user.display_name = None
    await session.flush()


#: What replaces a stored webhook body when the person it is about is erased.
#: A marker rather than an empty dict, so that a row support opens says
#: "somebody asked us to delete this" instead of looking like a delivery that
#: arrived broken.
_REDACTED: dict = {"redacted": True, "reason": "account erased at the owner's request"}
