"""Друзья: живые люди вместо мёртвых записей с датой.

Цикл роста, ради которого фича заведена (владелец, 31.08.2026: «делай
друзей»): человек делится ссылкой «проверь нас», приглашённый вводит на
веб-странице свою дату — и совместимость появляется **у обоих**: у каждого в
аккаунте рождается обычный профиль второго. Дальше вся машинерия продукта
работает как есть: совместимость считается бесплатно (закон «расчёт всех
восьми систем свободен навсегда»), полный отчёт пары покупается как обычно,
«как у него сегодня» — это существующий `POST /v1/systems/transits` c
`profile_id` друга.

**Ссылка одноразовая.** Приглашение — жест к одному человеку; многоразовая
ссылка в публичном чате родила бы у пригласившего толпу незнакомцев. Повтор
приёма тем же человеком идемпотентен: двойное нажатие «Готово» не видно.

**Профиль, рождённый приёмом, обходит лестницу партнёров** (один бесплатно /
второй купившему пару — `profiles.create_profile`). Это осознанное решение,
показанное владельцу при сдаче фичи: лестница ограничивает записи, которые
человек заводит САМ, а приглашение — это второй живой человек, пришедший в
продукт, и брать 402 за его приход значило бы платить за собственный рост.
Злоупотребление держит потолок приглашений в день, а не цена.

**Стирание аккаунта** (`accounts.erase`) уносит приглашения обеих сторон, но
НЕ трогает профиль-копию в чужом аккаунте: это обычная запись второго
человека, как если бы он ввёл дату руками, — Article 17 не тянется в чужие
записные книжки. Дружба расторгается удалением профиля — обычным DELETE
`/v1/profiles/{id}`, отдельного «раздружиться» нет нарочно.
"""

from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from ...config import settings
from ...db.models import FriendInvite, Profile, as_utc, utcnow
from ..deps import CurrentUser, SessionDep, Visitor, window
from ..schemas import ProfileInput

log = logging.getLogger("alma.friends")

router = APIRouter(prefix="/friends", tags=["friends"])

#: Сколько ссылок один аккаунт выдаёт в сутки. Потолок — вся защита от
#: злоупотребления бесплатным слоем (см. шапку: лестница партнёров на
#: приглашения не действует): двадцать живых знакомых в день — щедро для
#: человека и тесно для скрипта.
INVITES_PER_DAY = 20

INVITE_WINDOW_SECONDS = 86_400.0


def _invite_url(token: str) -> str:
    """Ссылка ведёт на сайт: приглашённый ещё без приложения — в этом смысл."""
    return f"{settings().web_url.rstrip('/')}/p/{token}"


async def _self_profile(session, user_id: str) -> Profile | None:
    return (
        await session.execute(
            select(Profile).where(
                Profile.user_id == user_id, Profile.is_self.is_(True)
            )
        )
    ).scalars().first()


@router.post("/invites", status_code=status.HTTP_201_CREATED)
async def create_invite(
    request: Request, user: CurrentUser, session: SessionDep
) -> dict:
    """Выдать ссылку «проверь нас».

    Требует собственной даты: приглашение обещает совместимость, а
    совместимость двух людей без первого — обещание без содержания. Клиент,
    получивший 422, ведёт человека в свою анкету, а не показывает ошибку.
    """
    me = await _self_profile(session, user.id)
    if me is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "no_self_birth",
                "message": "save your own birth before inviting someone",
            },
        )
    if not await window(
        request, "friend_invite", limit=INVITES_PER_DAY,
        seconds=INVITE_WINDOW_SECONDS,
    ).hit(session, user.id):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "invite_rate_limit",
                "message": "that is a lot of invitations for one day — "
                           "try again tomorrow",
            },
        )
    invite = FriendInvite(
        # 22 URL-safe знака — та же энтропия, что у гостевого id.
        token=secrets.token_urlsafe(16),
        inviter_user_id=user.id,
        inviter_name=me.name,
    )
    session.add(invite)
    await session.flush()
    return {"token": invite.token, "url": _invite_url(invite.token)}


@router.get("/invites/{token}")
async def read_invite(token: str, _: Visitor, session: SessionDep) -> dict:
    """Что страница приглашения знает до всякого входа.

    `Visitor`, не `CurrentUser`: открытая ссылка — это просмотр страницы, и
    минтить гостевой аккаунт на него нельзя (правило `/billing/catalogue`).
    Имя — снимок из строки приглашения: страница не имеет права ходить в
    чужой профиль.
    """
    invite = (
        await session.execute(
            select(FriendInvite).where(FriendInvite.token == token)
        )
    ).scalars().first()
    if invite is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"error": "invite_unknown", "message": "no such invitation"},
        )
    return {
        "inviter_name": invite.inviter_name,
        "claimed": invite.claimed_at is not None,
    }


@router.post("/invites/{token}/claim")
async def claim_invite(
    token: str, payload: ProfileInput, user: CurrentUser, session: SessionDep
) -> dict:
    """Принять приглашение: одна дата — совместимость у обоих.

    `CurrentUser` минтит гостя — и это правильно: приём и есть тот акт,
    которым в продукте появляются аккаунты (правило «аккаунт создаёт акт, а
    не просмотр»). Телом едет рождение принимающего — той же формой, что
    сохраняет обычный профиль, со всей её валидацией.
    """
    invite = (
        await session.execute(
            select(FriendInvite).where(FriendInvite.token == token)
        )
    ).scalars().first()
    if invite is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"error": "invite_unknown", "message": "no such invitation"},
        )
    if invite.inviter_user_id == user.id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "error": "own_invite",
                "message": "this is your own invitation",
            },
        )
    if invite.claimed_at is not None:
        if invite.claimed_by_user_id == user.id:
            # Двойное «Готово». Отвечаем тем же, чем ответили в первый раз.
            mine = await session.get(Profile, invite.claimer_profile_id or "")
            return {
                "inviter_name": invite.inviter_name,
                "friend_profile": _maybe_out(mine),
                "already": True,
            }
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "error": "invite_claimed",
                "message": "this invitation has already been used",
            },
        )

    their_self = await _self_profile(session, invite.inviter_user_id)
    if their_self is None:
        # Пригласивший стёр аккаунт или свою дату между выдачей и приёмом.
        raise HTTPException(
            status.HTTP_410_GONE,
            detail={
                "error": "invite_gone",
                "message": "the person who sent this is no longer here",
            },
        )

    # Своя дата принимающего: существующая — вернее присланной. Человек с
    # аккаунтом, открывший ссылку, уже рассказал о себе, и перетирать его
    # рождение формой с чужой страницы нельзя.
    my_self = await _self_profile(session, user.id)
    if my_self is None:
        my_self = Profile(
            user_id=user.id,
            name=payload.name,
            is_self=True,
            gender=payload.gender,
            birth_date=payload.birth_date,
            birth_time=payload.birth_time,
            latitude=payload.latitude,
            longitude=payload.longitude,
            timezone=payload.timezone,
            place_label=payload.place_label,
            place_id=payload.place_id,
        )
        session.add(my_self)
        await session.flush()

    # Копии друг друга — прямыми вставками, мимо лестницы партнёров
    # (см. шапку файла: приглашение — приход человека, а не запись про него).
    friend_of_inviter = Profile(
        user_id=invite.inviter_user_id,
        name=my_self.name or payload.name,
        relation="friend",
        is_self=False,
        birth_date=my_self.birth_date,
        birth_time=my_self.birth_time,
        latitude=my_self.latitude,
        longitude=my_self.longitude,
        timezone=my_self.timezone,
        place_label=my_self.place_label,
        place_id=my_self.place_id,
        on_ambiguous=my_self.on_ambiguous,
    )
    inviter_for_me = Profile(
        user_id=user.id,
        name=invite.inviter_name or their_self.name,
        relation="friend",
        is_self=False,
        birth_date=their_self.birth_date,
        birth_time=their_self.birth_time,
        latitude=their_self.latitude,
        longitude=their_self.longitude,
        timezone=their_self.timezone,
        place_label=their_self.place_label,
        place_id=their_self.place_id,
        on_ambiguous=their_self.on_ambiguous,
    )
    session.add_all([friend_of_inviter, inviter_for_me])
    await session.flush()

    invite.claimed_at = utcnow()
    invite.claimed_by_user_id = user.id
    invite.inviter_profile_id = friend_of_inviter.id
    invite.claimer_profile_id = inviter_for_me.id
    await session.flush()

    log.info("friend invite claimed: %s -> %s", invite.inviter_user_id, user.id)
    return {
        "inviter_name": invite.inviter_name,
        "friend_profile": _maybe_out(inviter_for_me),
        "already": False,
    }


@router.get("")
async def my_friends(user: CurrentUser, session: SessionDep) -> dict:
    """Живые связи: с кем совместимость появилась через приглашение.

    Отдаёт метаданные и id профиля друга В МОЁМ аккаунте — «как у него
    сегодня» клиент считает существующим `POST /v1/systems/transits` с этим
    `profile_id`, ничего нового на сервере для этого нет. Профиль удалён —
    связи нет: удаление профиля и есть «раздружиться».
    """
    rows = (
        await session.execute(
            select(FriendInvite).where(
                FriendInvite.claimed_at.is_not(None),
                (FriendInvite.inviter_user_id == user.id)
                | (FriendInvite.claimed_by_user_id == user.id),
            )
        )
    ).scalars().all()
    out = []
    for invite in rows:
        profile_id = (
            invite.inviter_profile_id
            if invite.inviter_user_id == user.id
            else invite.claimer_profile_id
        )
        profile = await session.get(Profile, profile_id or "")
        if profile is None or profile.user_id != user.id:
            continue
        out.append({
            "profile_id": profile.id,
            "name": profile.name,
            "since": as_utc(invite.claimed_at).isoformat(),
        })
    return {"friends": out}


def _maybe_out(profile: Profile | None) -> dict | None:
    """Та же форма, каким профиль отдаёт его собственный роутер.

    Через `profiles._out`, а не второй копией полей: копия разошлась бы с
    оригиналом в первый же раз, когда профилю добавят колонку (солнечный
    знак в `_out` уже считается — вторая сборка его бы молча потеряла).
    """
    if profile is None:
        return None
    from .profiles import _out

    return _out(profile).model_dump(mode="json")
