"""Sign-in. No passwords anywhere.

Three ways in — Google, Apple, and a link in an email — and all three land in
the same place: `accounts.sign_in`, which either attaches the identity to the
guest row the person is already using or folds that guest into an account
they already had.

The magic-link flow deliberately gives the same answer whether or not an
address is known to us. "We sent you a link" for an unknown address is a
white lie that costs nothing; "no account with that email" is an oracle that
tells anyone who asks which addresses have accounts here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ...auth import accounts, tokens
from ...auth.providers import InvalidIdentityToken, verify_apple, verify_google
from ...config import settings
from ...db.models import AuthProvider, MagicLink, User, as_utc, utcnow
from ...mail import send_magic_link
from ..deps import CurrentUser, SessionDep
from ..schemas import (
    AppleSignIn,
    GoogleSignIn,
    MagicLinkConsume,
    MagicLinkRequest,
    SessionOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_out(user: User) -> SessionOut:
    return SessionOut(
        token=tokens.issue(user.id),
        user_id=user.id,
        is_guest=user.is_guest,
        email=user.email,
        display_name=user.display_name,
        locale=user.locale,
    )


@router.get("/session", response_model=SessionOut)
async def whoami(user: CurrentUser) -> SessionOut:
    """Who this token belongs to — and a guest account if it belonged to nobody."""
    return _session_out(user)


@router.post("/google", response_model=SessionOut)
async def google(payload: GoogleSignIn, user: CurrentUser, session: SessionDep) -> SessionOut:
    try:
        identity = verify_google(payload.credential)
    except InvalidIdentityToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    signed_in = await accounts.sign_in(
        session,
        email=identity.email,
        provider=identity.provider,
        subject=identity.subject,
        display_name=identity.display_name,
        guest=user,
    )
    return _session_out(signed_in)


@router.post("/apple", response_model=SessionOut)
async def apple(payload: AppleSignIn, user: CurrentUser, session: SessionDep) -> SessionOut:
    try:
        identity = verify_apple(payload.identity_token, full_name=payload.full_name)
    except InvalidIdentityToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    signed_in = await accounts.sign_in(
        session,
        email=identity.email,
        provider=identity.provider,
        subject=identity.subject,
        display_name=identity.display_name,
        guest=user,
    )
    return _session_out(signed_in)


@router.post("/magic-link", status_code=status.HTTP_202_ACCEPTED)
async def request_magic_link(
    payload: MagicLinkRequest, user: CurrentUser, session: SessionDep
) -> dict:
    """Send a sign-in link.

    Always answers the same way. Whether the address has an account here is
    not information this endpoint is willing to hand out.
    """
    token, token_hash = tokens.new_magic_token()
    session.add(
        MagicLink(
            token_hash=token_hash,
            email=payload.email,
            guest_user_id=user.id if user.is_guest else None,
            expires_at=tokens.magic_link_expiry(),
        )
    )
    await session.flush()

    delivered = await send_magic_link(
        to=payload.email, token=token, locale=payload.locale
    )
    response: dict = {
        "sent": True,
        "expires_in_minutes": settings().magic_link_minutes,
    }
    if not delivered and not settings().is_production:
        # Development has no mail provider configured. Returning the link
        # keeps the flow usable locally; production never reaches this.
        response["debug_token"] = token
    return response


@router.post("/magic-link/consume", response_model=SessionOut)
async def consume_magic_link(
    payload: MagicLinkConsume, user: CurrentUser, session: SessionDep
) -> SessionOut:
    result = await session.execute(
        select(MagicLink).where(MagicLink.token_hash == tokens.hash_magic_token(payload.token))
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="this link is not valid")

    expires = as_utc(link.expires_at)
    if link.used_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="this link has already been used")
    if expires <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="this link has expired")

    # Single use, marked before the account work so a double submit cannot
    # produce two sign-ins from one email.
    link.used_at = utcnow()
    await session.flush()

    guest = user if user.is_guest else None
    if link.guest_user_id and (guest is None or guest.id != link.guest_user_id):
        # The link was requested in another tab or on another device; prefer
        # the guest that actually did the work over whoever is clicking.
        stored = await accounts.resolve(session, link.guest_user_id)
        if stored is not None and stored.is_guest:
            guest = stored

    signed_in = await accounts.sign_in(
        session,
        email=link.email,
        provider=AuthProvider.email.value,
        subject=None,
        guest=guest,
    )
    return _session_out(signed_in)


@router.post("/refresh", response_model=SessionOut)
async def refresh(user: CurrentUser) -> SessionOut:
    """A fresh token for the same person. No state changes."""
    return _session_out(user)
