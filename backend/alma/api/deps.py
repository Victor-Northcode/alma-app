"""Shared request plumbing: who is asking, and what they may see.

Guest-first was a deliberate design and most of it is right: a person can use
the whole product before they have decided to tell us anything, the guest **is**
an account rather than a session that gets migrated later, and signing in
attaches an identity to the row that already exists. None of that changes here.

What changed is **when the row appears**, and it was wrong in a way that made
every per-account number in the business a different number from the one it was
named after. `current_user` minted an account for any request that arrived
without a token, and `POST /v1/events` — the funnel beacon, fired by the landing
page on mount — went through it like everything else. So a browser that loaded
the site and touched nothing left an account behind. The dev database showed 143
users against 46 profiles: two thirds of the accounts had never saved a birth,
because they were page views.

The rule now:

* **`visitor` never creates anything.** It answers with the account behind the
  token, or with nothing. Measurement uses it, and so should anything else whose
  answer is the same whether or not a row exists. Two routes take it today:
  `POST /v1/events`, the beacon the landing fires on mount, and
  `GET /v1/billing/catalogue`, which the landing's pricing section fetches on
  mount as well. The second was found after the first was fixed and is the
  reason this list exists rather than a sentence naming one route: the rule is
  about *every* call a page view makes, and blaming the loudest one left a
  quieter one minting the same rows through a different door.
* **`current_user` still mints, and that is now a statement about the route
  rather than about the request.** A route that depends on it is a route where
  something is being kept — a birth saved, a sign-in landed, a purchase
  verified — and minting there is the account being created *by an act*.
* **The anonymous id is claimed at exactly that moment.** The request that mints
  the account is the request that came from that browser, which is the only
  moment the join between the two is a fact rather than a guess. See
  `funnel.claim`; without it, the stages recorded before the account and the
  stages recorded after it are two people, and the conversion rate the pricing
  model rests on reads as zero.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import funnel, region
from ..auth import accounts, tokens
from ..auth.accounts import AccountDeleted
from ..calc import BirthData
from ..db import User, get_session
from ..db.models import Profile
from .schemas import BirthInput

#: The header a client reads to pick up a freshly minted guest token.
ISSUED_TOKEN_HEADER = "X-Alma-Token"

#: The header a client *sends* to say which browser or installation this is,
#: when it has no account yet.
#:
#: It is never minted here, and that is not an oversight. A server that issued
#: it would issue one per request that arrived without one — and the very first
#: thing the landing does is fire a beacon while three other calls are in
#: flight, so a single visitor would collect four ids and appear four times at
#: the top of the funnel. A client that generates its own has exactly one before
#: it makes its first request. `funnel.clean_anon_id` is what stops that being a
#: free-text field.
ANON_ID_HEADER = "X-Alma-Anon"


def get_provider():
    """The model provider, as a dependency so tests can substitute one.

    Everything above the AI layer takes its provider through here, which is
    what lets the whole generation path — prompts, validation, regeneration,
    refusal — run in CI against a scripted provider with no key and no
    network.

    Constructed lazily rather than eagerly. FastAPI resolves every dependency
    before the route body runs, so building the provider here would make an
    unconfigured API key outrank the paywall: asking for a chapter you have
    not bought would answer "the AI is unavailable" instead of "this is
    locked". Returning a factory puts the entitlement check first, where it
    belongs.
    """
    from ..ai.provider import ModelUnavailable, default_provider

    def build():
        try:
            return default_provider()
        except ModelUnavailable as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "ai_unavailable", "message": str(exc)},
            ) from exc

    return build


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def anonymous_id(
    x_alma_anon: Annotated[str | None, Header()] = None,
) -> str | None:
    """The caller's own id for this browser or installation, if it sent one.

    Validated in `alma/funnel.py` rather than here, because that module is
    where the rule about what may be written to that table lives and a second
    copy of it is a second thing to get wrong. Anything unrecognisable comes
    back as `None`, which callers treat as "did not send one".
    """
    return funnel.clean_anon_id(x_alma_anon)


AnonymousId = Annotated[str | None, Depends(anonymous_id)]


async def edge_country(request: Request, response: Response) -> str | None:
    """Which country the network says this request came from, or `None`.

    A dependency rather than a line in each route, because the country is a
    property of the request and every route that prices anything needs the same
    answer to it. The rule about *which* header and whose word wins lives in
    `alma/region.py`; this is only the wire into FastAPI.

    Nothing here fails. An edge that did not set a header, a value that is not a
    country code, and Cloudflare's own `XX` for an address it could not place
    all come back as `None`, which every caller already handles: `currency_for`
    answers USD, and USD is a stated fallback rather than a guess.

    **The `Vary` is not decoration.** `GET /v1/billing/catalogue` is a plain
    cacheable GET whose body now depends on a request header, which is the exact
    shape of the bug where a CDN serves one country's prices to the next
    country's visitor — a wrong price, shown confidently, to somebody about to
    decide to spend money. Nothing caches this today, and that is precisely why
    it has to be declared here rather than remembered on the day somebody puts a
    cache in front of the API. `append` rather than assignment because the CORS
    middleware writes its own `Vary: Origin` on credentialed responses, and an
    overwrite would trade one cache poisoning for another.
    """
    for name in region.EDGE_COUNTRY_HEADERS:
        response.headers.append("Vary", name)
    country = region.from_headers(request.headers)
    # Counted, and warned about once, so that a deployment with no edge in front
    # of it can be told apart from one where everybody genuinely is in the
    # United States. See `region.observe` — the two answers look identical on
    # the wire and only one of them is a working configuration.
    region.observe(country)
    return country


#: The country the network reports. Routes that also accept a client-supplied
#: one pass both through `region.resolve`, which prefers this — see the security
#: note there.
EdgeCountry = Annotated[str | None, Depends(edge_country)]


async def visitor(
    request: Request,
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    """The account behind this request, or nothing. Creates no rows.

    A missing, expired or forged token is not an error — it is somebody who has
    not given us anything yet. Refusing it would put a sign-in wall in front of
    a product whose entire first impression depends on there not being one; and
    inventing an account for it is what this dependency exists to not do.

    A *deleted* account is the one hard answer: 410, so the client drops the
    token instead of silently becoming somebody new.
    """
    raw = tokens.bearer(authorization) or request.cookies.get("alma_token")
    if not raw:
        return None

    try:
        user = await accounts.resolve(session, tokens.subject(raw))
    except tokens.InvalidToken:
        return None
    except AccountDeleted as exc:
        raise HTTPException(status.HTTP_410_GONE, detail=str(exc)) from exc

    if user is not None:
        await accounts.touch(session, user)
    return user


Visitor = Annotated[User | None, Depends(visitor)]


async def current_user(
    response: Response,
    session: SessionDep,
    known: Visitor,
    anon: AnonymousId,
) -> User:
    """The user behind this request, creating a guest if there is none.

    **Depending on this is a claim about the route: something here is worth
    keeping.** Saving a birth, landing a sign-in link, verifying a purchase — an
    act, in the owner's words, rather than a visit. The routes that only look at
    something should take `Visitor` and answer for nobody. Two were getting this
    wrong and both fired on page load: `POST /v1/events`, the funnel beacon, and
    `GET /v1/billing/catalogue`, which the pricing section fetches on mount and
    which the browser actually issues *first* — so after the beacon was fixed a
    page view still minted a row, and minted it on the one request that had no
    anonymous id to claim yet.

    When a row is minted, the anonymous id that came with the request is claimed
    for it, so that everything the person did before this moment can still be
    counted as the same person afterwards. The claim is deliberately not made
    anywhere else: this is the only point in the system where "that browser
    became this account" is something we watched happen.
    """
    if known is not None:
        return known

    user = await accounts.create_guest(session)
    await funnel.claim(session, anon_id=anon, user_id=user.id)
    response.headers[ISSUED_TOKEN_HEADER] = tokens.issue(user.id)
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def require_account(user: CurrentUser) -> User:
    """For routes that genuinely need a signed-in person — billing, export."""
    if user.is_guest:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="sign in first — this needs an account we can attach to you",
        )
    return user


Account = Annotated[User, Depends(require_account)]


def birth_from_input(payload: BirthInput) -> BirthData:
    return BirthData(
        date=payload.birth_date,
        time=payload.birth_time,
        latitude=payload.latitude,
        longitude=payload.longitude,
        timezone=payload.timezone,
        place_label=payload.place_label,
        name=payload.name,
        on_ambiguous=payload.on_ambiguous,
    )


def birth_from_profile(profile: Profile) -> BirthData:
    birth_date = profile.birth_date
    if not isinstance(birth_date, date_type):  # pragma: no cover - driver variance
        birth_date = date_type.fromisoformat(str(birth_date))
    return BirthData(
        date=birth_date,
        time=profile.birth_time,
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone=profile.timezone,
        place_label=profile.place_label,
        name=profile.name,
    )


async def load_profile(session: AsyncSession, user: User, profile_id: str) -> Profile:
    profile = await session.get(Profile, profile_id)
    # Same answer for "does not exist" and "belongs to someone else": a
    # different one would turn this endpoint into a way to enumerate ids.
    if profile is None or profile.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no such profile")
    return profile


async def resolve_birth(
    session: AsyncSession,
    user: User,
    *,
    profile_id: str | None,
    birth: BirthInput | None,
) -> BirthData:
    """Take a birth from either a saved profile or the request body."""
    if profile_id:
        return birth_from_profile(await load_profile(session, user, profile_id))
    if birth is not None:
        return birth_from_input(birth)

    from sqlalchemy import select

    result = await session.execute(
        select(Profile).where(Profile.user_id == user.id, Profile.is_self.is_(True)).limit(1)
    )
    own = result.scalar_one_or_none()
    if own is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="no birth data — send `birth`, or save a profile first",
        )
    return birth_from_profile(own)
