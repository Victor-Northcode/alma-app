"""Birth profiles: the person themselves, and anyone they compare against."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ...db.models import Profile
from ...i18n import replies as i18n_replies
from ..deps import CurrentUser, SessionDep, load_profile
from ..schemas import ProfileInput, ProfileOut

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _out(profile: Profile) -> ProfileOut:
    return ProfileOut(
        id=profile.id,
        name=profile.name,
        relation=profile.relation,
        is_self=profile.is_self,
        birth_date=profile.birth_date,
        birth_time=profile.birth_time,
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone=profile.timezone,
        place_label=profile.place_label,
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
            access = await _ent.check(session, user, "compatibility", chapter=None)
            owns_door = access.allowed and access.kind not in (None, "free")
            limit = 2 if owns_door else 1
            if len(others) >= limit:
                raise HTTPException(
                    status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": "partner_limit",
                        "message": i18n_replies.reply("partner_limit", user.locale),
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
        birth_date=payload.birth_date,
        birth_time=payload.birth_time,
        latitude=payload.latitude,
        longitude=payload.longitude,
        timezone=payload.timezone,
        place_label=payload.place_label,
        place_id=payload.place_id,
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
    profile.birth_date = payload.birth_date
    profile.birth_time = payload.birth_time
    profile.latitude = payload.latitude
    profile.longitude = payload.longitude
    profile.timezone = payload.timezone
    profile.place_label = payload.place_label
    profile.place_id = payload.place_id
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
