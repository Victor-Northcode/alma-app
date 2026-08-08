"""Session tokens.

Long-lived by design. Alma is something people open once a week, and an
expiry that logs them out between readings would be a security theatre tax
paid entirely by the user — there is nothing here worth stealing that a
ninety-day token makes meaningfully easier to steal than a thirty-day one.

Two properties matter more than the lifetime:

* The `sub` claim is the user row's id, and a merged account resolves to the
  surviving row. Otherwise someone who signed in on a second device would be
  logged out mid-purchase, holding a token for a user that no longer exists.
* Nothing in the token is trusted for authorisation. Entitlements are read
  from the database on every request. A token that says "paid" is a token
  that can be edited to say "paid".
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from ..config import settings


class InvalidToken(Exception):
    """The token is missing, malformed, expired or not ours."""


def issue(user_id: str, *, days: int | None = None, extra: dict | None = None) -> str:
    config = settings()
    now = datetime.now(timezone.utc)
    lifetime = days if days is not None else config.access_token_days
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=lifetime)).timestamp()),
        "iss": "alma",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def read(token: str) -> dict:
    """Decode and verify. Raises `InvalidToken` for every failure mode."""
    config = settings()
    try:
        return jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.jwt_algorithm],
            issuer="alma",
            options={"require": ["exp", "sub", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc


def subject(token: str) -> str:
    return read(token)["sub"]


def bearer(header: str | None) -> str | None:
    """Pull the token out of an Authorization header, if there is one."""
    if not header:
        return None
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


# ── magic links ────────────────────────────────────────────────────────────

def new_magic_token() -> tuple[str, str]:
    """A link token and its hash.

    Only the hash is stored. A leaked database must not hand out sign-ins,
    and the plaintext exists exactly long enough to be put in an email.
    """
    token = secrets.token_urlsafe(32)
    return token, hash_magic_token(token)


def hash_magic_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def magic_link_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=settings().magic_link_minutes)
