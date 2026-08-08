"""Registering a device, and the one control that turns the daily off.

Four routes, and the shape of them is decided by two sentences from elsewhere.

`deps.current_user`'s own rule is *"depending on this is a claim about the
route: something here is worth keeping"*. Registering a phone is exactly that,
so these routes take `CurrentUser` rather than `Account`. `docs/PUSH.md §3`
asked for `require_account` and it is wrong for this product: a guest **is** an
account here, guests can and do buy, and demanding a sign-in before somebody
may receive the thing they are paying for would lock out most of the paying
population to solve nothing. Entitlement is checked when the notification is
sent, by `tier_of`, which is where it belongs.

`docs/THE-DAILY.md §5` requires the whole of this to be reachable **in one tap
from inside a notification** — Apple's guideline 4.5.4 requires an in-app
opt-out, and the design goal is a disable path so easy that nobody reaches for
the uninstall path. `PATCH` with `{"daily": "off"}` is that one tap, and it
deletes the tokens rather than setting a flag something remembers to check.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from ...auth import entitlements
from ...geo import is_known_timezone
from ...notify import rules, tokens
from ..deps import CurrentUser, SessionDep

router = APIRouter(prefix="/notifications", tags=["notifications"])

#: The header a client sends to say which zone the *device* is in, as opposed
#: to the zone somebody was born in. `docs/PUSH.md §3` and `THE-DAILY.md §6.8`
#: both ask `alma/api/deps.py` for this as a request-wide dependency, so that
#: every call refreshes it and a person who moves is caught within a day.
#: That file belongs to another workflow; until it lands, this route reads the
#: header itself, which covers the registration call — the one that matters,
#: because the client re-registers on every launch.
TIMEZONE_HEADER = "X-Alma-Timezone"


class DeviceIn(BaseModel):
    """One installation, as the client describes it."""

    model_config = ConfigDict(extra="forbid")

    platform: str = Field(pattern="^(ios|android)$")
    token: str = Field(min_length=32, max_length=512)
    #: iOS only, and it is not a nicety — see `docs/PUSH.md §1.8`. A TestFlight
    #: build's tokens are *production* tokens however much TestFlight feels
    #: like testing, so the client says which build it is and the sender picks
    #: the host per token instead of per deployment.
    environment: str | None = Field(default=None, pattern="^(sandbox|production)$")
    timezone: str | None = Field(default=None, max_length=64)
    #: The language the *phone* is set to, which is not always the language the
    #: account chose. The notification's arguments are translated into this.
    locale: str | None = Field(default=None, max_length=16)
    app_version: str | None = Field(default=None, max_length=32)
    os_version: str | None = Field(default=None, max_length=32)


class DeviceOut(BaseModel):
    platform: str
    token: str


class SettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    daily: str | None = Field(default=None, pattern="^(off|occasionally|only_what_matters)$")
    hour: int | None = Field(default=None, ge=0, le=23)
    timezone: str | None = Field(default=None, max_length=64)


def _zone_from(payload_zone: str | None, request: Request) -> str | None:
    """The device's zone, from the body or the header, or nothing.

    Validated through `geo.is_known_timezone` and **ignored silently when
    unrecognised**, exactly as the country header is. A client on an old
    Android with a stale tzdata should lose the optimisation, not the
    registration.
    """
    for value in (payload_zone, request.headers.get(TIMEZONE_HEADER)):
        candidate = (value or "").strip()
        if candidate and is_known_timezone(candidate):
            return candidate
    return None


@router.post("/devices", status_code=status.HTTP_201_CREATED)
async def register(
    payload: DeviceIn, request: Request, user: CurrentUser, session: SessionDep
) -> DeviceOut:
    """Record this install, or refresh what we already knew about it.

    Called on every launch, not once. That is Google's own guidance — stamp a
    timestamp on every upload whether or not the token changed — and it is
    also what keeps the timezone honest for somebody who has just landed
    somewhere else.
    """
    try:
        row = await tokens.register(
            session,
            user_id=user.id,
            platform=payload.platform,
            token=payload.token,
            environment=payload.environment,
            timezone=_zone_from(payload.timezone, request),
            locale=payload.locale,
            app_version=payload.app_version,
            os_version=payload.os_version,
        )
    except tokens.BadToken as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return DeviceOut(platform=row.platform, token=row.token)


@router.post("/devices/delete")
async def unregister(
    user: CurrentUser,
    session: SessionDep,
    platform: str = Body(embed=True),
    token: str = Body(embed=True),
) -> dict:
    """Forget one device. A POST rather than a DELETE with a body.

    DELETE with a request body is legal and is inconsistently supported by
    proxies and HTTP clients, and this is the route a person hits when they
    have decided to stop hearing from us. It has to work the first time.
    """
    try:
        gone = await tokens.remove(
            session, platform=platform, token=token, user_id=user.id
        )
    except tokens.BadToken as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {"removed": gone}


@router.get("")
async def read(user: CurrentUser, session: SessionDep) -> dict:
    """What the settings screen shows, including why it says what it says.

    The timezone's **source** is returned alongside it, and that is the field
    that makes the override discoverable to exactly the person who needs it:
    somebody who moved and whose notifications are landing at the wrong hour
    will look here first, and "Auckland — from your birth data" tells them what
    went wrong in four words.
    """
    tier = await entitlements.tier_of(session, user)
    devices = await tokens.for_user(session, user.id)
    device_zone = next((d.timezone for d in devices if d.timezone), None)

    # The same order `rules.zone_for` actually resolves in, and it has to be
    # the same order. This used to report "chosen" whenever `daily_timezone`
    # was set while the sender preferred the device's zone — and since the
    # clients send `X-Alma-Timezone` on every launch, the device rung always
    # resolved. The one control a person has over when they are woken up was
    # inert, and this screen told them it was working.
    if user.daily_timezone:
        source, zone = "chosen", user.daily_timezone
    elif device_zone:
        source, zone = "device", device_zone
    else:
        source, zone = "birth", None

    return {
        "daily": rules.preference_of(user.daily_push, tier).value,
        "chosen": user.daily_push is not None,
        "hour": rules.delivery_hour(user.daily_hour),
        "quiet_hours": [rules.QUIET_START, rules.QUIET_END],
        "timezone": zone,
        "timezone_source": source,
        "entitled": rules.entitled(tier),
        "devices": [{"platform": d.platform, "registered_at": d.created_at.isoformat()} for d in devices],
    }


@router.patch("")
async def update(
    payload: SettingsIn, user: CurrentUser, session: SessionDep
) -> dict:
    """Change the control. Turning it off deletes the tokens.

    **Off is a deletion, not a flag.** It is the simplest possible proof that
    off means off, and it is the withdrawal of consent Apple's 4.5.4 requires
    a route for. *Occasionally* and *Only what matters* both keep the row;
    only Off removes it.

    **Turning it on without a subscription answers 402, not 200.** A switch
    that accepts a preference nothing will ever honour is the one behaviour
    `THE-DAILY.md §5.1` names as indefensible — the person believes they have
    turned something on, hears nothing for a month, and concludes the feature
    is broken rather than that it is paid for.
    """
    tier = await entitlements.tier_of(session, user)

    if payload.daily is not None:
        wanted = rules.Preference(payload.daily)
        if wanted is not rules.Preference.off and not rules.entitled(tier):
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "locked",
                    "message": "the daily is part of the subscription",
                },
            )
        user.daily_push = wanted.value
        if wanted is rules.Preference.off:
            await tokens.forget(session, user.id)

    if payload.hour is not None:
        # Stored as asked and clamped on the way out by `rules.delivery_hour`,
        # so that the guarantee "never between 22:00 and 08:00" holds even for
        # a value written by something that is not this route.
        user.daily_hour = payload.hour
    if payload.timezone is not None:
        zone = payload.timezone.strip()
        if zone and not is_known_timezone(zone):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unknown timezone"
            )
        user.daily_timezone = zone or None

    await session.flush()
    return await read(user, session)
