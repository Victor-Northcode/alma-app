"""Verifying a sign-in from Google or Apple.

Both hand the browser a signed JWT. The only safe thing to do with it is
verify the signature against the provider's published keys and check that the
audience is us — a decoded-but-unverified token is a note from a stranger
claiming to be someone.

The two failure modes this guards against are the ones that actually happen:
accepting a token minted for a *different* application (which any developer
can obtain), and accepting an unverified email address (Apple in particular
will hand over an address the user has not proved they control).

── и третий: чужой запрос, вешающий весь сервис ──────────────────────────────

Проверка ходит по сети за ключами провайдера, а разбор JWT — синхронный. Пока
эти две вещи выполнялись **в событийном цикле**, любой висящий вызов к Google
или Apple останавливал не один запрос, а все: один поток на воркер обслуживает
все соединения сразу. Дальше выяснялось хуже: у `PyJWKClient` таймаут по
умолчанию тридцать секунд, а незнакомый `kid` заставляет его сходить за
ключами **мимо кэша** — то есть строка `{"kid": "<случайное>"}` в заголовке
токена была бесплатным способом устроить нам поход в сеть на каждый свой
запрос, а тридцати таких хватало, чтобы сервис перестал отвечать кому бы то ни
было. Токен при этом даже не обязан быть похожим на настоящий: до проверки
подписи дело не доходит.

Три ответа, ровно на три части беды: работа уезжает в поток (`to_thread`),
таймаут ставится человеческий (`JWKS_TIMEOUT_SECONDS`), а поход мимо кэша
разрешён не чаще раза в `JWKS_REFRESH_INTERVAL` на провайдера — ротацию ключей
это переживает (она редкая и оба провайдера публикуют новый ключ заранее), а
перебор `kid` упирается в кэш и отвечает отказом, ничего не спросив у сети.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from functools import partial

import httpx
import jwt
from anyio import to_thread
from jwt import PyJWKClient

from ..config import settings

GOOGLE_JWKS = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

APPLE_JWKS = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

#: Сколько ждать ответа от провайдера за ключами. Умолчание библиотеки —
#: тридцать секунд; столько не ждёт ни один живой человек на экране входа, зато
#: столько прекрасно ждёт занятый поток. Пять секунд — это «сеть работает»;
#: всё, что дольше, честнее назвать отказом и дать человеку нажать ещё раз.
JWKS_TIMEOUT_SECONDS = 5.0

#: Как часто незнакомый `kid` имеет право отправить нас в сеть за ключами.
#:
#: Ротация ключей у обоих провайдеров происходит раз в недели и объявляется
#: заранее — минута задержки на неё не влияет вообще. А вот перебор случайных
#: `kid` без этого ограничения — сетевой вызов на каждый чужой запрос, из цикла
#: событий, с таймаутом библиотеки: способ уронить сервис одним curl'ом.
JWKS_REFRESH_INTERVAL = 60.0

_clients: dict[str, PyJWKClient] = {}
#: Когда по каждому адресу JWKS в последний раз ходили мимо кэша.
_refreshed_at: dict[str, float] = {}
#: Оба словаря теперь трогаются из рабочих потоков, а не только из цикла.
_lock = threading.Lock()


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
    with _lock:
        if url not in _clients:
            # PyJWKClient caches keys and refetches on an unknown kid, which is
            # exactly the rotation behaviour both providers expect — но именно
            # этот перезапрос и надо было взять под уздцы, см. `_signing_key`.
            _clients[url] = PyJWKClient(
                url, cache_keys=True, lifespan=3600, timeout=JWKS_TIMEOUT_SECONDS
            )
        return _clients[url]


def _may_refetch(jwks_url: str) -> bool:
    """Можно ли прямо сейчас сходить за ключами мимо кэша.

    Один разрешённый поход на провайдера в минуту, и отметка ставится **до**
    самого похода: иначе десяток одновременных запросов с незнакомым `kid`
    отправились бы в сеть все разом, что и есть тот самый залп.
    """
    now = time.monotonic()
    with _lock:
        last = _refreshed_at.get(jwks_url)
        if last is not None and now - last < JWKS_REFRESH_INTERVAL:
            return False
        _refreshed_at[jwks_url] = now
        return True


def _signing_key(client: PyJWKClient, token: str, jwks_url: str):
    """Ключ, которым подписан токен, — из кэша, и только потом из сети.

    `get_signing_key_from_jwt` делает то же самое, но **всегда** идёт в сеть,
    когда `kid` не нашёлся: библиотека решает за нас, что незнакомый ключ — это
    ротация. Здесь это решение принимается по времени, а не по факту промаха, —
    ротация от перебора отличается частотой и ничем больше.
    """
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except jwt.PyJWTError as exc:
        raise InvalidIdentityToken(str(exc)) from exc
    if not kid:
        raise InvalidIdentityToken("the token names no signing key")

    found = client.match_kid(client.get_signing_keys(), kid)
    if found is not None:
        return found

    if not _may_refetch(jwks_url):
        # Отказ без похода в сеть. Настоящему человеку в момент ротации это
        # стоит одной неудачной попытки входа в течение минуты; перебору —
        # всего смысла затеи.
        raise InvalidIdentityToken("unknown signing key")

    found = client.match_kid(client.get_signing_keys(refresh=True), kid)
    if found is None:
        raise InvalidIdentityToken("unknown signing key")
    return found


def _verify(token: str, *, jwks_url: str, audience: str, issuers: set[str]) -> dict:
    """Разбор и проверка подписи. **Синхронная, зовётся только из потока.**"""
    if not audience:
        raise InvalidIdentityToken(
            "no client id configured for this provider — set it in the environment"
        )
    try:
        signing_key = _signing_key(_jwk_client(jwks_url), token, jwks_url)
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


async def _verified_claims(token: str, *, jwks_url: str, audience: str, issuers: set[str]) -> dict:
    """`_verify` в рабочем потоке.

    Обёртка, а не два одинаковых `to_thread.run_sync` в двух функциях ниже:
    забыть её в третьем провайдере — значит вернуть блокировку цикла обратно, и
    заметить это можно будет только по графику задержек.
    """
    return await to_thread.run_sync(
        partial(_verify, token, jwks_url=jwks_url, audience=audience, issuers=issuers)
    )


async def verify_google(token: str) -> Identity:
    claims = await _verified_claims(
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


async def verify_apple(token: str, *, full_name: str | None = None) -> Identity:
    """Verify an Apple identity token.

    Apple only sends the user's name on the very first authorisation, and
    never again, so the caller passes it through from that one response. It
    is display data and is treated as such — the identity is the `sub` claim.
    """
    claims = await _verified_claims(
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
