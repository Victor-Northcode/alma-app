"""Birth profiles: the person themselves, and anyone they compare against."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ...db.models import Profile
from ...i18n import replies as i18n_replies
from ..deps import CurrentUser, SessionDep, load_profile
from ..schemas import ProfileInput, ProfileOut

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _fold(value: str | None) -> str | None:
    """«raise» — это не ответ, а его отсутствие; в базе ему соответствует NULL."""
    return value if value in ("earlier", "later") else None


def _out(profile: Profile) -> ProfileOut:
    return ProfileOut(
        id=profile.id,
        name=profile.name,
        relation=profile.relation,
        is_self=profile.is_self,
        gender=profile.gender,
        interest=profile.interest,
        birth_date=profile.birth_date,
        birth_time=profile.birth_time,
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone=profile.timezone,
        place_label=profile.place_label,
        on_ambiguous=profile.on_ambiguous,
    )


@router.get("", response_model=list[ProfileOut])
async def list_profiles(user: CurrentUser, session: SessionDep) -> list[ProfileOut]:
    result = await session.execute(
        select(Profile).where(Profile.user_id == user.id).order_by(
            Profile.is_self.desc(), Profile.created_at
        )
    )
    return [_out(p) for p in result.scalars().all()]


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: ProfileInput, user: CurrentUser, session: SessionDep
) -> ProfileOut:
    """Save a birth.

    Saving a second "self" replaces the first rather than adding one. A user
    with two selves is a user whose every subsequent reading has to guess
    which person they meant, and that guess is invisible when it is wrong.

    Which is why an unstated `is_self` means "mine" only for the *first* birth
    an account saves. It used to mean "mine" always, and combined with the
    replacement above that made adding a partner without the flag delete the
    owner's own chart — silently, along with every reading keyed to it. The
    first birth somebody saves is obviously theirs; after that, claiming to be
    them has to be said out loud.
    """
    mine = (
        await session.execute(
            select(Profile).where(Profile.user_id == user.id, Profile.is_self.is_(True))
        )
    ).scalars().all()

    is_self = payload.is_self if payload.is_self is not None else not mine

    # The partner ladder the owner set: one comparison free, two with the
    # compatibility door bought once, as many as you like on the plan. The
    # cap is on *saved partners*, because a saved partner is a whole second
    # chart computed free for ever — the ladder is what funds that.
    if not is_self:
        from ...auth import entitlements as _ent
        others = (
            await session.execute(
                select(Profile).where(
                    Profile.user_id == user.id, Profile.is_self.is_(False)
                )
            )
        ).scalars().all()
        tier = await _ent.tier_of(session, user)
        if tier != "subscriber":
            # **Ступень читается по купленным парам, а не по двери
            # совместимости.** Двери у совместимости в v3 нет: отчёт покупается
            # на конкретного человека (`pair.check` → грант `pair:{id}`), и
            # спросить `check(system="compatibility")` без партнёра больше
            # нельзя — это ошибка вызова, а не отсутствие прав. Смысл лестницы
            # сохранён дословно: один сохранённый партнёр бесплатно, второй —
            # тому, кто уже заплатил хотя бы за один разбор пары.
            #
            # TODO(Ф0.3): по ТЗ P4 злоупотребление бесплатным слоем ограничивает
            # серверный кап тизеров (3/мес, приложение А9), а не число
            # сохранённых профилей. Когда кап появится, эту лестницу надо
            # пересмотреть целиком — сейчас она сохраняется как есть, чтобы
            # смена каталога не стала заодно и сменой продуктового правила.
            has_bought_a_pair = bool(await _ent.unlocked_pairs(session, user))
            limit = 2 if has_bought_a_pair else 1
            if len(others) >= limit:
                raise HTTPException(
                    status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": "partner_limit",
                        "message": i18n_replies.reply(
                            "partner_limit", payload.locale or user.locale
                        ),
                        "limit": limit,
                    },
                )

    if is_self:
        for previous in mine:
            await session.delete(previous)

    profile = Profile(
        user_id=user.id,
        name=payload.name,
        relation=payload.relation,
        is_self=is_self,
        gender=payload.gender,
        interest=payload.interest if payload.is_self is not False else None,
        birth_date=payload.birth_date,
        birth_time=payload.birth_time,
        latitude=payload.latitude,
        longitude=payload.longitude,
        timezone=payload.timezone,
        place_label=payload.place_label,
        place_id=payload.place_id,
        on_ambiguous=_fold(payload.on_ambiguous),
    )
    session.add(profile)
    await session.flush()
    return _out(profile)


@router.get("/{profile_id}", response_model=ProfileOut)
async def read_profile(profile_id: str, user: CurrentUser, session: SessionDep) -> ProfileOut:
    return _out(await load_profile(session, user, profile_id))


@router.patch("/{profile_id}", response_model=ProfileOut)
async def update_profile(
    profile_id: str, payload: ProfileInput, user: CurrentUser, session: SessionDep
) -> ProfileOut:
    """Change a birth — most often to add a birth time that was looked up later."""
    profile = await load_profile(session, user, profile_id)
    profile.name = payload.name
    profile.relation = payload.relation
    if payload.gender is not None:
        profile.gender = payload.gender
    # Интерес пишется только себе: NBO читает сигнал владельца аккаунта, и
    # чужой профиль с интересом был бы данными, которые никто не собирал.
    if payload.interest is not None and profile.is_self:
        profile.interest = payload.interest
    profile.birth_date = payload.birth_date
    profile.birth_time = payload.birth_time
    profile.latitude = payload.latitude
    profile.longitude = payload.longitude
    profile.timezone = payload.timezone
    profile.place_label = payload.place_label
    profile.place_id = payload.place_id
    # **Ответ не стирается пустым запросом.** Клиент, правящий имя, шлёт форму
    # целиком и не обязан помнить про развилку; сохранённый выбор пережил бы
    # такую правку, а «raise» по умолчанию затёр бы его и спросил заново.
    if _fold(payload.on_ambiguous) is not None:
        profile.on_ambiguous = _fold(payload.on_ambiguous)
    await session.flush()
    return _out(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(profile_id: str, user: CurrentUser, session: SessionDep) -> None:
    profile = await load_profile(session, user, profile_id)
    if profile.is_self:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="this is your own birth data — edit it instead, or delete your account",
        )
    await session.delete(profile)
