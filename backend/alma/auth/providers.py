"""Verifying a sign-in from Google or Apple.

Both hand the browser a signed JWT. The only safe thing to do with it is
verify the signature against the provider's published keys and check that the
audience is us — a decoded-but-unverified token is a note from a stranger
claiming to be someone.

The two failure modes this guards against are the ones that actually happen:
accepting a token minted for a *different* application (which any developer
can obtain), and accepting an unverified email address (Apple in particular
will hand over an address the user has not proved they control).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
import jwt
from jwt import PyJWKClient

from ..config import settings

GOOGLE_JWKS = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

APPLE_JWKS = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

_clients: dict[str, PyJWKClient] = {}


class InvalidIdentityToken(Exception):
    """The provider's token did not verify, or is not for us."""


@dataclass(frozen=True, slots=True)
class Identity:
    provider: str
    subject: str
    email: str
    email_verified: bool
    display_name: str | None = None


def _jwk_client(url: str) -> PyJWKClient:
    if url not in _clients:
        # PyJWKClient caches keys and refetches on an unknown kid, which is
        # exactly the rotation behaviour both providers expect.
        _clients[url] = PyJWKClient(url, cache_keys=True, lifespan=3600)
    return _clients[url]


def _verify(token: str, *, jwks_url: str, audience: str, issuers: set[str]) -> dict:
    if not audience:
        raise InvalidIdentityToken(
            "no client id configured for this provider — set it in the environment"
        )
    try:
        signing_key = _jwk_client(jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=audience,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except (jwt.PyJWTError, httpx.HTTPError) as exc:
        raise InvalidIdentityToken(str(exc)) from exc

    if claims.get("iss") not in issuers:
        raise InvalidIdentityToken(f"unexpected issuer: {claims.get('iss')!r}")
    if claims.get("exp", 0) < time.time():
        raise InvalidIdentityToken("token has expired")
    return claims


def verify_google(token: str) -> Identity:
    claims = _verify(
        token,
        jwks_url=GOOGLE_JWKS,
        audience=settings().google_client_id,
        issuers=GOOGLE_ISSUERS,
    )
    email = claims.get("email")
    if not email:
        raise InvalidIdentityToken("the token carries no email address")
    # Google marks this false for addresses on domains it has not verified;
    # trusting it would let someone claim an address they do not own.
    if not claims.get("email_verified", False):
        raise InvalidIdentityToken("the email address on this token is not verified")

    return Identity(
        provider="google",
        subject=claims["sub"],
        email=email.lower(),
        email_verified=True,
        display_name=claims.get("name"),
    )


def verify_apple(token: str, *, full_name: str | None = None) -> Identity:
    """Verify an Apple identity token.

    Apple only sends the user's name on the very first authorisation, and
    never again, so the caller passes it through from that one response. It
    is display data and is treated as such — the identity is the `sub` claim.
    """
    claims = _verify(
        token,
        jwks_url=APPLE_JWKS,
        audience=settings().apple_client_id,
        issuers={APPLE_ISSUER},
    )
    email = claims.get("email")
    if not email:
        raise InvalidIdentityToken("the token carries no email address")

    verified = claims.get("email_verified", False)
    if isinstance(verified, str):     # Apple sends the string "true"
        verified = verified.lower() == "true"
    if not verified:
        raise InvalidIdentityToken("the email address on this token is not verified")

    return Identity(
        provider="apple",
        subject=claims["sub"],
        email=email.lower(),
        email_verified=True,
        display_name=full_name,
    )
