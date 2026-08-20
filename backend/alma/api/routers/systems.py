"""The eight systems, over HTTP.

Every route here is the same three steps: work out whose birth we are talking
about, ask the calculation service, and hand back a CalcResult. No astrology
happens in this file and none ever should — the moment a route computes
something itself, the promise that the AI can only cite engine facts stops
being checkable.

Entitlements are applied *after* the calculation, by trimming the response
rather than by refusing it. A locked system still returns its free surface —
which sign, how many chapters, what the first insight says — because the
paywall's job is to sell the rest, and a blank page sells nothing.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from ... import i18n
from ...auth import entitlements
from ...calc import BirthData, CalcResult, TimeRequired
from ...calc.cache import compute_cached_async
from ...calc.service import AmbiguousBirthTime, ambiguity_detail
from ...db.models import Profile
from ..cache import result_cache
from ..deps import (
    CurrentUser,
    SessionDep,
    birth_from_input,
    partner_profile_id,
    resolve_birth,
    throttle_expensive_calc,
)
from ..schemas import (
    CalcRequest,
    CompatibilityRequest,
    SolarReturnRequest,
    TransitsRequest,
)

router = APIRouter(prefix="/systems", tags=["systems"])

#: What a locked system still shows: **everything it calculated**.
#:
#: This used to be a per-system whitelist that trimmed a locked natal chart down
#: to six keys — three sign names, a moon phase, an element balance — and emptied
#: `factors` for every system. Two things were wrong with that, and they are the
#: same thing said twice.
#:
#: It contradicted the product's own promise. "Every calculation is free — you
#: pay only for the words" is on the landing page, in the pricing block and in
#: the hero, in all six languages, and has been since the first version. A
#: reader who was shown three sign names had not been shown the calculation; a
#: promise that is true only for buyers is not a promise, it is a headline.
#:
#: And it hid the only argument that gets this app past App Review's Guideline
#: 4.3(b), which refuses fortune-telling apps that are not "meaningfully
#: different". What makes Alma different is *visible arithmetic*: houses,
#: aspects with their orbs, a transit exact to the day, nine axes where three
#: systems disagree. A reviewer who opened a locked chart saw a sun sign and a
#: moon phase — indistinguishable from the category being refused.
#:
#: Two keys of this were already widened, for transits and for synthesis, and
#: the comments left behind made this exact argument each time. This is the same
#: decision applied to the remaining six rather than a seventh exception.
#:
#: **What is still sold is the writing**, which is where it always was: the 41
#: chapters come from `POST /v1/readings`, are stored per account, and are
#: unaffected by anything here. `factors` are the mechanical strings the writer
#: reads *from* — "sun 14°44′ ♋︎", "house 11" — not a word of interpretation.
#:
#: If a future reader wants to trim again, the thing to weigh is that the
#: calculation costs us nothing — a static ephemeris file and a static gazetteer,
#: no per-request cost at all — while the writing costs real money per chapter.
#: Charging for the free half and giving away the expensive half is the trade
#: this file used to make.


def _ambiguous(exc: AmbiguousBirthTime) -> HTTPException:
    """A DST-ambiguous wall clock is a question, not a failure.

    Both instants are real and an hour apart. Picking one silently would put
    a coin flip inside a paid reading, so the client is told what happened
    and given the two options to offer.
    """
    return HTTPException(status.HTTP_409_CONFLICT, detail=ambiguity_detail(exc))


async def _run(system: str, birth: BirthData, **options) -> CalcResult:
    """Расчёт — в рабочем потоке, и это здесь единственная нефункциональная строка.

    Раньше это была прямая `compute_cached(...)` внутри `async def`, то есть
    синхронная работа в событийном цикле. Замер на этой машине, изнутри
    работающего приложения: пока шёл `POST /systems/transits`, цикл стоял
    1.257 с, астрокартография — 0.306 с, и всё это время `/health` не
    отвечал. `compute_cached_async` — та же функция в потоке; тот же замер
    даёт 0.022 с. Почему поток помогает при одном GIL и почему это выигрыш
    задержки, а не пропускной способности, — в докстринге `calc.cache`.
    """
    try:
        return await compute_cached_async(system, birth, cache=result_cache(), **options)
    except AmbiguousBirthTime as exc:
        raise _ambiguous(exc) from exc
    except TimeRequired as exc:
        # 422 by number: Starlette renamed the constant and deprecated the
        # old name, and this is not a thing worth pinning a version over.
        raise HTTPException(
            422, detail={"error": "birth_time_required", "message": str(exc)}
        ) from exc


async def _respond(
    session, user, system: str, result: CalcResult, chapter=None, partner_id=None
) -> dict:
    if system == "compatibility" and partner_id is None:
        # Партнёра назвать нечем: его прислали «сырой» датой, а не профилем.
        # Спрашивать `check` в этом состоянии нельзя — она справедливо считает
        # безымянную пару ошибкой вызова, — а ответ и так известен: гранту не к
        # чему привязаться, значит написанные главы закрыты. Расчёт при этом
        # отдаётся целиком, как и у всех остальных систем: считать мы не
        # продаём.
        access = entitlements.PAIR_WITHOUT_PROFILE
    else:
        access = await entitlements.check(
            session, user, system, chapter=chapter, partner_id=partner_id
        )
    payload = result.as_dict()
    payload["access"] = access.as_dict()

    if not access.allowed:
        # `data` and `factors` are left whole on purpose — see the note above.
        # The lock is about the written chapters, and those live behind
        # `POST /v1/readings`, which checks the same entitlement.
        payload["locked"] = True
    return payload


@router.post("/natal", dependencies=[Depends(throttle_expensive_calc)])
async def natal(payload: CalcRequest, user: CurrentUser, session: SessionDep) -> dict:
    birth = await resolve_birth(
        session, user, profile_id=payload.profile_id, birth=payload.birth
    )
    result = await _run("natal", birth, house_system=payload.house_system)
    return await _respond(session, user, "natal", result)


@router.post("/numerology")
async def numerology(payload: CalcRequest, user: CurrentUser, session: SessionDep) -> dict:
    birth = await resolve_birth(
        session, user, profile_id=payload.profile_id, birth=payload.birth
    )
    result = await _run("numerology", birth, reference=datetime.now(timezone.utc).date())
    return await _respond(session, user, "numerology", result)


@router.post("/birth-card")
async def birth_card(payload: CalcRequest, user: CurrentUser, session: SessionDep) -> dict:
    birth = await resolve_birth(
        session, user, profile_id=payload.profile_id, birth=payload.birth
    )
    result = await _run("birth-card", birth, reference=datetime.now(timezone.utc).date())
    return await _respond(session, user, "birth-card", result)


@router.post("/transits", dependencies=[Depends(throttle_expensive_calc)])
async def transits(payload: TransitsRequest, user: CurrentUser, session: SessionDep) -> dict:
    """Годовой скан — самый дорогой вызов в сервисе, и он обязан быть один на день.

    **Один экран «Сегодня» считал его дважды.** Экран открывает два запроса
    сразу (`today_model._loadSky` и `_loadLine`): `POST /systems/transits` и
    `POST /v1/readings` для главы `transits/active`. Обе ручки зовут
    `compute_cached` с одним и тем же рождением и одним и тем же годом — но
    ключи расходились на двух мелочах, и обе были здесь:

    * `include_moon=False` уезжал в опции всегда, а `readings._options_for`
      его не шлёт вовсе. `contract.cache_key` собирает ключ из **переданных**
      опций, так что `include_moon=False` и «ничего не передано» — два разных
      ключа под один и тот же ответ (`transits_result` подставляет ровно этот
      же `False`). Поэтому опция кладётся, только когда её просили;
    * `start` по умолчанию был `now()`, а тот же скан из `readings` начинается
      с полуночи. На ключ это не влияло — `MOMENT_OPTIONS` схлопывает `start`
      в дату, — а вот на ответ влияло: две ручки считали **разные** числа под
      один ключ, и содержимое дня решал тот воркер, который успел первым.
      Ровно то, что запрещает `cache.py`: промах обязан быть неотличим от
      попадания. `readings.py` в своём комментарии уже утверждал, что
      «`systems.py` округляет так же»; теперь это правда.

    Цена ошибки, замерено на этой машине: годовой скан — 1.26 с процессорного
    времени, то есть каждое открытие «Сегодня» стоило 2.5 с вместо 1.26 с и
    вдвое больше места в кэше. При десяти тысячах читателей утром это ровно
    вдвое больше железа под ту же волну.
    """
    birth = await resolve_birth(
        session, user, profile_id=payload.profile_id, birth=payload.birth
    )
    start = datetime.combine(
        payload.start or datetime.now(timezone.utc).date(),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    options: dict = {
        "start": start,
        "days": payload.days,
        "house_system": payload.house_system,
    }
    if payload.include_moon:
        options["include_moon"] = True
    result = await _run("transits", birth, **options)
    return await _respond(session, user, "transits", result)


@router.post("/solar-return", dependencies=[Depends(throttle_expensive_calc)])
async def solar_return(
    payload: SolarReturnRequest, user: CurrentUser, session: SessionDep
) -> dict:
    birth = await resolve_birth(
        session, user, profile_id=payload.profile_id, birth=payload.birth
    )
    result = await _run(
        "solar-return",
        birth,
        year=payload.year or datetime.now(timezone.utc).year,
        latitude=payload.latitude,
        longitude=payload.longitude,
        house_system=payload.house_system,
    )
    return await _respond(session, user, "solar-return", result)


@router.post("/compatibility", dependencies=[Depends(throttle_expensive_calc)])
async def compatibility(
    payload: CompatibilityRequest, user: CurrentUser, session: SessionDep
) -> dict:
    birth = await resolve_birth(
        session, user, profile_id=payload.profile_id, birth=payload.birth
    )

    if payload.other_profile_id:
        other_profile = await session.get(Profile, payload.other_profile_id)
        if other_profile is None or other_profile.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no such profile")
        from ..deps import birth_from_profile

        other = birth_from_profile(other_profile)
    elif payload.other is not None:
        other = birth_from_input(payload.other)
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="compatibility needs a second person — send `other` or `other_profile_id`",
        )

    result = await _run(
        "compatibility", birth, other=other, house_system=payload.house_system
    )
    # Партнёр — тот, кого назвал запрос; если он назван датой, а не профилем,
    # `None` уходит дальше сознательно: см. `_respond`.
    return await _respond(
        session, user, "compatibility", result,
        partner_id=await partner_profile_id(session, user, payload.other_profile_id),
    )


@router.post("/astrocartography", dependencies=[Depends(throttle_expensive_calc)])
async def astrocartography(payload: CalcRequest, user: CurrentUser, session: SessionDep) -> dict:
    birth = await resolve_birth(
        session, user, profile_id=payload.profile_id, birth=payload.birth
    )
    result = await _run("astrocartography", birth, house_system=payload.house_system)
    return await _respond(session, user, "astrocartography", result)


@router.post("/synthesis", dependencies=[Depends(throttle_expensive_calc)])
async def synthesis(payload: CalcRequest, user: CurrentUser, session: SessionDep) -> dict:
    """The nine axes, with their poles in the reader's language.

    `CalcRequest.locale` has been on this request since the first version and
    nothing had ever read it, because until now every string in a CalcResult
    was either a number or an identifier. Synthesis is the exception: the two
    poles of each axis — "works alone, out of sight" against "works in public,
    in front of people" — are prose, they are shown verbatim under an axis the
    reader's three systems disagree about, and they arrived in English in all
    six languages.

    The translation happens here rather than in `engine/synthesis.py` because
    the engine's answer is cached per birth and not per locale, and it should
    stay that way: the arithmetic is the same in every language. So the poles
    are computed once in English and dressed at the boundary.
    `i18n.localise_synthesis` copies rather than mutates for exactly that
    reason — the dictionary it is handed belongs to the cache.
    """
    birth = await resolve_birth(
        session, user, profile_id=payload.profile_id, birth=payload.birth
    )
    result = await _run(
        "synthesis",
        birth,
        reference=datetime.now(timezone.utc).date(),
        house_system=payload.house_system,
    )
    payload_out = await _respond(session, user, "synthesis", result)
    payload_out["data"] = i18n.localise_synthesis(payload_out["data"], locale=payload.locale)
    payload_out["locale"] = i18n.resolve(payload.locale)
    return payload_out


@router.get("/hub")
async def hub(user: CurrentUser, session: SessionDep) -> dict:
    """What the cabinet's front page needs: every system and its state."""
    from ...calc.contract import SYSTEMS
    from sqlalchemy import select

    unlocked = await entitlements.unlocked_systems(session, user)
    own = (
        await session.execute(
            select(Profile).where(Profile.user_id == user.id, Profile.is_self.is_(True)).limit(1)
        )
    ).scalar_one_or_none()

    people = (
        await session.execute(
            select(Profile).where(Profile.user_id == user.id, Profile.is_self.is_(False))
        )
    ).scalars().all()

    def status_of(system: str) -> str:
        """Whether we *could* compute this, which is not whether it is paid for.

        Readiness first, deliberately. A system that is missing a birth time
        should say so even while it is locked — "add your birth time" is a
        thing the person can act on, and "unlock for $9.99" hides it behind a
        purchase that would not actually produce a reading.
        """
        if own is None:
            return "not-yet"
        if system in ("solar-return", "astrocartography") and not own.birth_time:
            return "needs-time"
        if system == "compatibility" and not people:
            return "add-person"
        return "calculated" if system in unlocked else "open"

    return {
        "has_birth_data": own is not None,
        "birth_time_known": bool(own and own.birth_time),
        "people": len(people),
        "systems": [
            {"slug": system, "unlocked": system in unlocked, "status": status_of(system)}
            for system in SYSTEMS
        ],
    }
