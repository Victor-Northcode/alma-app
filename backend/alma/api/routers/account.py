"""The account itself: what we hold, and getting rid of it.

Both routes are self-service and immediate. Making someone email support to
delete their data is a way of hoping they give up, and a product built on
people handing over their birth details cannot afford to look like it is
hoping that.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import JSONResponse

from ...auth import accounts, entitlements
from ..deps import CurrentUser, SessionDep

router = APIRouter(prefix="/account", tags=["account"])


@router.get("")
async def me(user: CurrentUser, session: SessionDep) -> dict:
    unlocked = await entitlements.unlocked_systems(session, user)
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "provider": user.provider,
        "locale": user.locale,
        "is_guest": user.is_guest,
        "created_at": user.created_at.isoformat(),
        "unlocked": sorted(unlocked),
    }


@router.patch("")
async def update(
    user: CurrentUser,
    session: SessionDep,
    locale: str | None = Body(default=None, embed=True, max_length=8),
    display_name: str | None = Body(default=None, embed=True, max_length=120),
) -> dict:
    if locale:
        await accounts.set_locale(session, user, locale)
    if display_name is not None:
        user.display_name = display_name.strip() or None
        await session.flush()
    return {"locale": user.locale, "display_name": user.display_name}


@router.get("/export")
async def export(user: CurrentUser, session: SessionDep) -> JSONResponse:
    """Everything we hold, as one downloadable document.

    Open to a guest, and it has to be. See `delete` below: a guest account is a
    real row holding a birth date and full-precision birth coordinates, and the
    person it describes has never been asked for an email. Demanding one before
    they may read their own file would be asking for *more* personal data as the
    price of seeing what we already took.
    """
    payload = await accounts.export(session, user)
    return JSONResponse(
        payload,
        headers={"Content-Disposition": 'attachment; filename="alma-export.json"'},
    )


@router.post("/delete", status_code=status.HTTP_200_OK)
async def delete(
    user: CurrentUser,
    session: SessionDep,
    confirm: str = Body(embed=True),
) -> dict:
    """Erase the account and everything in it.

    **A guest may delete**, and this used to be `Account` rather than
    `CurrentUser`, which meant they could not. That was the wrong shape twice
    over. Alma creates a server-side account on the very first request and
    stores a birth date and full-precision coordinates against it before anyone
    has seen a sign-in screen — so guest is not an edge case, it is the default
    state of every install, and it is the state holding the most sensitive data
    we have. Refusing deletion until an email is supplied means demanding more
    personal data as the price of removing the data already taken, which is the
    pattern the policy exists to forbid and a Play rejection on sight.

    What the confirmation string is depends on what the account actually has:

    * a signed-in account confirms with its **email**, unchanged;
    * a guest confirms with its own **account id**, which is a credential they
      have and a stranger does not, and which needs no translation.

    Either way this is a sanity check that the caller means *this* account, not
    an anti-mistap measure — the friction belongs in the interface, where the
    apps put a second deliberate tap in front of it, because that is where a
    mistap happens.
    """
    expected = user.email or user.id
    if not confirm.strip() or confirm.strip().lower() != expected.strip().lower():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                "type your email address exactly to confirm deletion"
                if user.email
                else "type your account id exactly to confirm deletion"
            ),
        )

    await accounts.erase(session, user)
    return {"deleted": True}
