"""One route: the client saying where in the funnel somebody has got to.

Everything with an opinion is in `alma/funnel.py` — which names are real, what
may be attached to one, how many a caller may send in a day. This file is the
HTTP shape of it, and its whole job is to turn three refusals and a ceiling into
answers a client can act on rather than into a 500.

**This route creates nothing.** It is the one that most needed saying so: it is
fired by the landing page on mount, before anybody has done anything, and while
it depended on the account-minting dependency a browser that loaded the site and
touched nothing left a user row behind. Two thirds of the rows in the dev
database were that. It now takes `Visitor`, which answers with the account
behind the token or with nobody, and a stage from nobody is recorded against the
anonymous id the client sends in `X-Alma-Anon` — a string that grants nothing,
buys nothing and is not an account. The account is minted by the act that
follows: saving a birth, or signing in. `deps.current_user` claims the anonymous
id at that moment so the two halves of the journey remain one person in the
report.

The refusals are worth stating here because they are the reason the route
exists at all.

**A stage outside the set is a 422, not a row.** The table is only worth having
if every row in it can be counted, and one misspelt name is a cohort that
silently disappears from a funnel nobody re-checks.

**A stage from nobody at all is a 422, not a row.** With no token and no usable
anonymous id there is nothing to attribute the stage to, and a row with two
nulls in it counts towards `count(*)` and towards no funnel — a table that
disagrees with itself depending on who queries it. Our own clients cannot reach
this: each of them generates its id before its first request, and a test asserts
the web one does. What reaches it is a client somebody wrote against the old
shape of this route, and it gets a message naming the header rather than a 200
that quietly discarded the event.

**`purchase` is refused however it is spelt.** The browser knows an overlay
closed, and it may say so — that is `purchase_completed`, a stage of its own.
Money is known by the processor's signed webhook, which already writes a
`Purchase` row, and that is where the funnel reads the sale from. If the client
could report a purchase, then the number that decides whether to spend money on
advertising would be a number anybody with a terminal could set.

The labels arrive as `meta`, which is the word `src/lib/track.ts` puts on the
wire, and `properties` is accepted as well because that is the word on the
column and on this API's own schema. Taking both is not indecision: a beacon
swallows its own failures, so a client sending the other name would lose every
label it ever collected and nothing anywhere would say so.

There is no read route. The funnel is the business's own numbers: published
without a credential it goes to competitors, and there is no operator
credential in this service to put in front of it. `python -m alma.funnel` is
the read side.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, status

from ... import funnel
from ..deps import ANON_ID_HEADER, AnonymousId, SessionDep, Visitor

router = APIRouter(prefix="/events", tags=["events"])


@router.post("")
async def record_stage(
    user: Visitor,
    anon: AnonymousId,
    session: SessionDep,
    stage: str = Body(embed=True),
    meta: dict | None = Body(default=None, embed=True),
    properties: dict | None = Body(default=None, embed=True),
) -> dict:
    """Record that this person reached one stage of the funnel.

    Attributed to the account where there is one and to the browser where there
    is not, which for most of the funnel is the browser — that is not a
    shortcoming to be fixed later but the measurement working as intended,
    because a product whose first minute needs no account has most of its funnel
    in front of the sign-in wall.

    **A caller that changes its anonymous id between beacons breaks the funnel
    rather than its own session.** The landing view then belongs to an id that
    never appears again and the quiz belongs to an id that was never seen
    arriving — the first conversion in the report reads as zero, on data that
    looks perfectly healthy. That failure used to arrive through a client
    ignoring `X-Alma-Token`; the header changed, the failure did not. Every
    client of this API generates one id, keeps it, and sends it on every request
    — including the ones that are not beacons, because that is what lets the
    account minted later be joined back to what happened before it.
    """
    known = funnel.BY_NAME.get(stage)
    if known is None:
        # 422 by number throughout this file, the same as `systems.py`:
        # Starlette renamed the constant and deprecated the old name, and this
        # is not a thing worth pinning a version over.
        raise HTTPException(
            422,
            detail={
                "error": "unknown_stage",
                "message": f"{stage!r} is not a funnel stage",
                # Listed back, because the client that got this wrong is the
                # one that needs to see the words it should have used.
                "stages": list(funnel.STAGE_NAMES),
            },
        )

    if known.server_known:
        raise HTTPException(
            422,
            detail={
                "error": "server_recorded",
                "message": (
                    f"{stage!r} is recorded from the payment record, not from the "
                    "browser — nothing sent here would be counted"
                ),
                "stage": stage,
            },
        )

    if user is None and anon is None:
        raise HTTPException(
            422,
            detail={
                "error": "anonymous_id_required",
                "message": (
                    f"nothing to attribute {stage!r} to: send a bearer token, or "
                    f"a random id of your own in {ANON_ID_HEADER} and the same "
                    "one on every later request"
                ),
                "header": ANON_ID_HEADER,
            },
        )

    # Labels that are not on the allowlist are dropped rather than refused,
    # and `clean_properties` says why: a beacon swallows its own errors, so
    # refusing the event would delete a whole rung of the funnel over one
    # unrecognised label and nothing anywhere would report it.
    kept = funnel.clean_properties(meta if meta is not None else properties)

    try:
        # Two ceilings for the two kinds of caller, and the same number. An
        # account is counted in `UsageCounter` beside its other allowances; a
        # visitor with no account is counted off this table directly, because
        # that column is a foreign key into `user` and the whole point of this
        # route is that it does not put anything there.
        if user is not None:
            await funnel.spend_allowance(session, user.id)
        else:
            await funnel.spend_anonymous_allowance(session, anon)
    except funnel.TooManyEvents as exc:
        # A 429 rather than a silent 200. A client told it succeeded when it
        # did not will keep sending, and the first sign of a loop writing
        # thousands of rows would be the database bill.
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "event_rate_limit", "message": str(exc)},
        ) from exc

    await funnel.record(
        session,
        user_id=user.id if user is not None else None,
        anon_id=anon,
        stage=stage,
        properties=kept,
    )
    return {"recorded": True, "stage": stage}
