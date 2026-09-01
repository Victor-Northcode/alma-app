"""Друзья: ссылка «проверь нас» и живые связи, рождённые её приёмом.

Что стерегут тесты — обещания фичи, а не её сантехника:

* одна принятая ссылка = профиль второго человека **у обоих**, и дальше вся
  существующая машинерия (совместимость, «как у него день») работает без
  единой новой ручки;
* ссылка одноразовая, но повтор тем же человеком идемпотентен;
* лестница партнёров на приглашённых не действует — рост не продаётся;
* стирание одного аккаунта не лезет в записную книжку второго.
"""

from __future__ import annotations

import pytest

from tests.conftest import SOFIA, read_async

MARCO = {
    "birth_date": "1990-07-02",
    "birth_time": "12:15",
    "latitude": 41.9,
    "longitude": 12.5,
    "timezone": "Europe/Rome",
    "place_label": "Rome, Italy",
    "name": "Marco",
}


def _second_user(api) -> dict:
    """Второй аккаунт: свежий гость, отдельный токен."""
    response = api.get("/v1/auth/session")
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _invite(api, headers) -> dict:
    api.post("/v1/profiles", json=SOFIA, headers=headers)
    answer = api.post("/v1/friends/invites", headers=headers)
    assert answer.status_code == 201, answer.text
    return answer.json()


# ── выдача ─────────────────────────────────────────────────────────────────

def test_an_invite_needs_your_own_birth_first(api, auth_headers):
    answer = api.post("/v1/friends/invites", headers=auth_headers)
    assert answer.status_code == 422
    assert answer.json()["detail"]["error"] == "no_self_birth"


def test_an_invite_carries_a_web_url_and_the_inviter_name(api, auth_headers):
    invite = _invite(api, auth_headers)
    assert "/p/" in invite["url"]
    assert invite["token"] in invite["url"]

    page = api.get(f"/v1/friends/invites/{invite['token']}")
    assert page.status_code == 200
    assert page.json() == {"inviter_name": "Sofia Rossi", "claimed": False}


def test_the_page_lookup_mints_no_account(api, auth_headers):
    """Просмотр страницы — не акт: правило `/billing/catalogue` и здесь."""
    invite = _invite(api, auth_headers)

    async def count():
        from sqlalchemy import func, select

        from alma.db.models import User
        from alma.db.session import session_scope

        async with session_scope() as session:
            return (
                await session.execute(select(func.count()).select_from(User))
            ).scalar_one()

    before = read_async(count)
    answer = api.get(f"/v1/friends/invites/{invite['token']}")
    assert answer.status_code == 200
    assert answer.headers.get("x-alma-token") is None
    assert read_async(count) == before


def test_an_unknown_token_is_a_404(api, auth_headers):
    assert api.get("/v1/friends/invites/nope").status_code == 404


# ── приём ──────────────────────────────────────────────────────────────────

def test_a_claim_gives_both_sides_each_other(api, auth_headers):
    invite = _invite(api, auth_headers)
    guest = _second_user(api)

    answer = api.post(
        f"/v1/friends/invites/{invite['token']}/claim", json=MARCO, headers=guest
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["inviter_name"] == "Sofia Rossi"
    assert body["friend_profile"]["name"] == "Sofia Rossi"
    assert body["friend_profile"]["relation"] == "friend"
    assert body["already"] is False

    # У пригласившей появился Марко…
    sofia_people = api.get("/v1/profiles", headers=auth_headers).json()
    marco_row = [p for p in sofia_people if p["name"] == "Marco"]
    assert len(marco_row) == 1 and marco_row[0]["relation"] == "friend"
    assert marco_row[0]["birth_date"] == MARCO["birth_date"]

    # …и оба видят друг друга живой связью.
    theirs = api.get("/v1/friends", headers=auth_headers).json()["friends"]
    mine = api.get("/v1/friends", headers=guest).json()["friends"]
    assert [f["name"] for f in theirs] == ["Marco"]
    assert [f["name"] for f in mine] == ["Sofia Rossi"]
    # `profile_id` — обычный профиль в СВОЁМ аккаунте: «как у него сегодня»
    # клиент считает существующим POST /v1/systems/transits с этим id.
    assert mine[0]["profile_id"] == body["friend_profile"]["id"]


def test_a_claimer_with_a_birth_of_their_own_keeps_it(api, auth_headers):
    """Форма с чужой страницы не перетирает уже рассказанное о себе."""
    invite = _invite(api, auth_headers)
    guest = _second_user(api)
    api.post("/v1/profiles", json=MARCO, headers=guest)

    fake = dict(MARCO, birth_date="1900-01-01", name="Импостер")
    answer = api.post(
        f"/v1/friends/invites/{invite['token']}/claim", json=fake, headers=guest
    )
    assert answer.status_code == 200, answer.text

    sofia_people = api.get("/v1/profiles", headers=auth_headers).json()
    marco_row = [p for p in sofia_people if p["relation"] == "friend"][0]
    assert marco_row["birth_date"] == MARCO["birth_date"], (
        "у пригласившей — настоящая дата принявшего, не поле формы"
    )


def test_your_own_invite_refuses_you(api, auth_headers):
    invite = _invite(api, auth_headers)
    answer = api.post(
        f"/v1/friends/invites/{invite['token']}/claim",
        json=MARCO, headers=auth_headers,
    )
    assert answer.status_code == 409
    assert answer.json()["detail"]["error"] == "own_invite"


def test_a_link_works_once_but_repeats_quietly_for_the_same_person(
    api, auth_headers
):
    invite = _invite(api, auth_headers)
    guest = _second_user(api)
    first = api.post(
        f"/v1/friends/invites/{invite['token']}/claim", json=MARCO, headers=guest
    )
    again = api.post(
        f"/v1/friends/invites/{invite['token']}/claim", json=MARCO, headers=guest
    )
    assert first.status_code == 200 and again.status_code == 200
    assert again.json()["already"] is True

    # Профили не плодятся: двойное «Готово» не видно.
    sofia_people = api.get("/v1/profiles", headers=auth_headers).json()
    assert len([p for p in sofia_people if p["relation"] == "friend"]) == 1

    # А третий человек получает честный отказ.
    third = _second_user(api)
    stranger = api.post(
        f"/v1/friends/invites/{invite['token']}/claim", json=MARCO, headers=third
    )
    assert stranger.status_code == 409
    assert stranger.json()["detail"]["error"] == "invite_claimed"


def test_the_partner_ladder_does_not_tax_an_invited_friend(api, auth_headers):
    """Лестница «второй партнёр — купившему» не берёт 402 за рост.

    У пригласившей уже есть сохранённый партнёр — потолок бесплатного слоя
    исчерпан (`profiles.create_profile`). Принятое приглашение всё равно
    рождает друга: это второй живой человек, пришедший в продукт, а не
    вторая запись, которую она завела сама.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    saved = api.post(
        "/v1/profiles",
        json=dict(MARCO, name="Записанный партнёр", is_self=False),
        headers=auth_headers,
    )
    assert saved.status_code == 201

    invite = api.post("/v1/friends/invites", headers=auth_headers).json()
    guest = _second_user(api)
    answer = api.post(
        f"/v1/friends/invites/{invite['token']}/claim", json=MARCO, headers=guest
    )
    assert answer.status_code == 200, (
        "приглашённый упёрся в лестницу партнёров: " + answer.text
    )


def test_a_claim_after_the_inviter_erased_the_account_finds_nothing(
    api, auth_headers
):
    """Пригласивший стёр аккаунт — ссылка умерла вместе с ним.

    Свою дату при живом аккаунте удалить нельзя (профиль отвечает 409 —
    правило продукта), так что «пригласивший исчез» в жизни — это Article 17,
    а стирание уносит и строки приглашений: принявшему отвечает 404, как
    любой несуществующей ссылке, не выдавая, что тут кто-то был. Ветка 410
    в роутере остаётся обороной на случай рассинхрона.
    """
    invite = _invite(api, auth_headers)

    async def erase_inviter():
        from sqlalchemy import select

        from alma.auth import accounts
        from alma.db.models import User
        from alma.db.session import session_scope

        async with session_scope() as session:
            inviter = (
                await session.execute(select(User))
            ).scalars().one()
            await accounts.erase(session, inviter)

    read_async(erase_inviter)
    guest = _second_user(api)
    answer = api.post(
        f"/v1/friends/invites/{invite['token']}/claim", json=MARCO, headers=guest
    )
    assert answer.status_code == 404
    assert answer.json()["detail"]["error"] == "invite_unknown"


# ── границы ────────────────────────────────────────────────────────────────

def test_the_daily_invite_ceiling_holds(api, auth_headers):
    from alma.api.routers import friends as friends_module

    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    for _ in range(friends_module.INVITES_PER_DAY):
        assert (
            api.post("/v1/friends/invites", headers=auth_headers).status_code
            == 201
        )
    over = api.post("/v1/friends/invites", headers=auth_headers)
    assert over.status_code == 429
    assert over.json()["detail"]["error"] == "invite_rate_limit"


def test_unfriending_is_deleting_the_profile(api, auth_headers):
    invite = _invite(api, auth_headers)
    guest = _second_user(api)
    api.post(
        f"/v1/friends/invites/{invite['token']}/claim", json=MARCO, headers=guest
    )
    friends = api.get("/v1/friends", headers=auth_headers).json()["friends"]
    assert len(friends) == 1
    api.delete(f"/v1/profiles/{friends[0]['profile_id']}", headers=auth_headers)
    assert api.get("/v1/friends", headers=auth_headers).json()["friends"] == []
    # У второй стороны связь живёт: расторжение — личное, не взаимное.
    assert len(api.get("/v1/friends", headers=guest).json()["friends"]) == 1


def test_erasing_one_account_leaves_the_friends_copy_alone(api, auth_headers):
    """Article 17 не тянется в чужие записные книжки.

    Принявший стирает аккаунт: приглашения уходят, а профиль-копия у
    пригласившей остаётся — это её обычная запись о человеке, как если бы
    она ввела дату руками.
    """
    invite = _invite(api, auth_headers)
    guest = _second_user(api)
    api.post(
        f"/v1/friends/invites/{invite['token']}/claim", json=MARCO, headers=guest
    )

    async def erase_guest():
        from sqlalchemy import select

        from alma.auth import accounts
        from alma.db.models import FriendInvite, User
        from alma.db.session import session_scope

        async with session_scope() as session:
            users = (await session.execute(select(User))).scalars().all()
            claimer = [
                u for u in users
                if u.id == (
                    await session.execute(select(FriendInvite))
                ).scalars().one().claimed_by_user_id
            ][0]
            await accounts.erase(session, claimer)
            left = (await session.execute(select(FriendInvite))).scalars().all()
            return len(left)

    assert read_async(erase_guest) == 0, "приглашение стёрто вместе с аккаунтом"
    # Живой связи больше нет, но запись о человеке — есть.
    assert api.get("/v1/friends", headers=auth_headers).json()["friends"] == []
    names = [p["name"] for p in api.get("/v1/profiles", headers=auth_headers).json()]
    assert "Marco" in names
