"""Birth profiles: the person themselves, and anyone they compare against."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ...auth import entitlements
from ...db.models import Profile, User
from ...engine.sunsign import sun_sign_of_date
from ...i18n import replies as i18n_replies
from ..deps import CurrentUser, SessionDep, load_profile
from ..schemas import ProfileInput, ProfileOut

log = logging.getLogger("alma.api.profiles")

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
        current_latitude=profile.current_latitude,
        current_longitude=profile.current_longitude,
        current_place_label=profile.current_place_label,
        on_ambiguous=profile.on_ambiguous,
        sun_sign=_sun_sign(profile),
    )


def _sun_sign(profile: Profile) -> str | None:
    """Знак Солнца для строки списка — дёшево и с правом промолчать.

    Полный расчёт ради одного глифа был бы десятком эфемеридных проходов на
    экран «Мои пары»; здесь хватает даты. Отказ эфемериды (нет ядра, дата вне
    диапазона) — не повод ронять список людей: профиль важнее украшения.
    """
    try:
        return sun_sign_of_date(profile.birth_date)
    except Exception:  # noqa: BLE001 — украшение не имеет права ломать список
        log.warning("не смог назвать знак для профиля %s", profile.id, exc_info=True)
        return None


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
        current_latitude=payload.current_latitude,
        current_longitude=payload.current_longitude,
        current_place_label=payload.current_place_label,
        on_ambiguous=_fold(payload.on_ambiguous),
    )
    session.add(profile)
    await session.flush()
    return _out(profile)


@router.get("/{profile_id}", response_model=ProfileOut)
async def read_profile(profile_id: str, user: CurrentUser, session: SessionDep) -> ProfileOut:
    return _out(await load_profile(session, user, profile_id))


def _birth_moved(profile: Profile, payload: ProfileInput) -> bool:
    """Сдвинулось ли то, из чего считается карта.

    Имя, пол, родство и развилка часов сюда не входят: расчёт их не видит, и
    запрещать их правку значило бы наказывать за опечатку в имени.
    """
    return (
        profile.birth_date != payload.birth_date
        or (profile.birth_time or "") != (payload.birth_time or "")
        or abs((profile.latitude or 0) - payload.latitude) > 1e-6
        or abs((profile.longitude or 0) - payload.longitude) > 1e-6
        or (profile.timezone or "") != (payload.timezone or "")
    )


async def _paid_pair_report(session, profile: Profile) -> bool:
    """Есть ли живой грант проверки пары про этого человека."""
    held = await entitlements.for_user(session, await session.get(User, profile.user_id))
    wanted = entitlements.pair_system(profile.id)
    return any(
        row.scope == entitlements.SCOPE_PAIR
        and row.system == wanted
        and row.revoked_at is None
        for row in held
    )


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
    # **Рождение, за которое заплатили, не переписывается.**
    #
    # Грант пары назван профилем (`pair:<id>`), а не рождением, — и пока
    # рождение можно было править, одна покупка за $4.99 (или одна включённая
    # в подписку проверка) превращалась в сколько угодно отчётов: подменил
    # дату и место в профиле, попросил совместимость снова — id тот же, доступ
    # разрешён, а кэш расчёта не срабатывает, потому что рождение другое.
    # Каждый такой запрос — новая полная генерация, самая дорогая в продукте.
    #
    # Отказ, а не молчаливое игнорирование полей: человек, правящий дату
    # рождения человека, за отчёт о котором заплачено, обязан узнать, что
    # правка не прошла. Имя, пол и развилку часов менять по-прежнему можно —
    # они в расчёт не входят.
    if _birth_moved(profile, payload) and await _paid_pair_report(session, profile):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "error": "birth_locked_by_purchase",
                "message": i18n_replies.reply(
                    "birth_locked_by_purchase", payload.locale or user.locale
                ),
            },
        )
    profile.birth_date = payload.birth_date
    profile.birth_time = payload.birth_time
    profile.latitude = payload.latitude
    profile.longitude = payload.longitude
    profile.timezone = payload.timezone
    profile.place_label = payload.place_label
    profile.place_id = payload.place_id
    # Текущее место — только когда названо: PATCH шлёт форму целиком, и
    # клиент, правящий имя, не знает про город; None здесь значит «не менять»,
    # а не «стереть» (довод у поля в `schemas.ProfileInput`).
    if payload.current_latitude is not None and payload.current_longitude is not None:
        profile.current_latitude = payload.current_latitude
        profile.current_longitude = payload.current_longitude
        profile.current_place_label = payload.current_place_label
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
