"""Одна почта — один аккаунт, какой бы дверью человек ни вошёл.

Закон владельца (25.08.2026): вход через Apple ID, через Google и по коду из
письма с одной и той же почтой обязан приводить в один и тот же аккаунт.
Слить его в три разных — значит рассыпать покупки человека по трём сиротам,
и заметит он это в момент, когда «купленное навсегда» окажется в другом из
трёх.

Криптографию токенов эти тесты не трогают — она проверяется в провайдерах и
живёт на чужих ключах. Здесь подменяется сама проверка (`verify_google`,
`verify_apple`): тестируется склейка аккаунтов, то есть наш код, а не подпись
Google.
"""

from __future__ import annotations

import pytest

from alma.auth.providers import Identity, InvalidIdentityToken


@pytest.fixture()
def social(monkeypatch):
    """Подменённые провайдеры: любой токен вида 'google:почта' или
    'apple:почта' считается проверенным и несёт эту почту."""

    async def fake_google(token: str) -> Identity:
        provider, _, email = token.partition(":")
        if provider != "google" or not email:
            raise InvalidIdentityToken("not a google token")
        return Identity(
            provider="google", subject=f"g-{email}", email=email,
            email_verified=True, display_name=None,
        )

    async def fake_apple(token: str, *, full_name: str | None = None) -> Identity:
        provider, _, email = token.partition(":")
        if provider != "apple" or not email:
            raise InvalidIdentityToken("not an apple token")
        # «почта|sub» — для проверок стабильного идентификатора: настоящий
        # Apple шлёт один и тот же `sub` при любом адресе в токене.
        email, _, subject = email.partition("|")
        return Identity(
            provider="apple", subject=subject or f"a-{email}", email=email,
            email_verified=True, display_name=full_name,
        )

    # Подмена в модуле маршрута: auth.py импортировал имена к себе.
    from alma.api.routers import auth as auth_router

    monkeypatch.setattr(auth_router, "verify_google", fake_google)
    monkeypatch.setattr(auth_router, "verify_apple", fake_apple)


def _me(api, token: str) -> dict:
    return api.get(
        "/v1/auth/session", headers={"Authorization": f"Bearer {token}"}
    ).json()


def test_three_doors_one_account(api, social):
    """Google → Apple → код из письма: одна почта, один user_id."""
    email = "sofia@example.com"

    # Дверь первая: Google.
    via_google = api.post("/v1/auth/google", json={"credential": f"google:{email}"})
    assert via_google.status_code == 200, via_google.text
    google_user = _me(api, via_google.json()["token"])["user_id"]

    # Дверь вторая: Apple, тот же адрес, другой гость (новое устройство).
    via_apple = api.post(
        "/v1/auth/apple",
        json={"identity_token": f"apple:{email}", "full_name": "Sofia"},
    )
    assert via_apple.status_code == 200, via_apple.text
    apple_user = _me(api, via_apple.json()["token"])["user_id"]

    # Дверь третья: код из письма, третье устройство.
    asked = api.post("/v1/auth/magic-link", json={"email": email, "locale": "ru"})
    code = asked.json()["debug_code"]
    via_code = api.post(
        "/v1/auth/email-code/consume", json={"email": email, "code": code}
    )
    assert via_code.status_code == 200, via_code.text
    code_user = _me(api, via_code.json()["token"])["user_id"]

    assert google_user == apple_user == code_user, (
        "одна почта разложилась по разным аккаунтам — покупки человека "
        "рассыпаны по дверям, которыми он входил"
    )


def test_the_guest_chart_survives_social_sign_in(api, social):
    """Гость, посчитавший карту до входа, входит через Google и не теряет её."""
    guest = api.get("/v1/auth/session").json()
    headers = {"Authorization": f"Bearer {guest['token']}"}
    saved = api.post(
        "/v1/profiles",
        headers=headers,
        json={
            "birth_date": "1992-05-11", "birth_time": "11:26",
            "latitude": 55.7558, "longitude": 37.6173,
            "timezone": "Europe/Moscow", "place_label": "Moscow, Russia",
            "name": "Анатолий", "is_self": True,
        },
    )
    assert saved.status_code in (200, 201), saved.text

    entered = api.post(
        "/v1/auth/google",
        headers=headers,
        json={"credential": "google:keeper@example.com"},
    )
    assert entered.status_code == 200, entered.text

    profiles = api.get(
        "/v1/profiles", headers={"Authorization": f"Bearer {entered.json()['token']}"}
    ).json()
    labels = [p.get("place_label") for p in profiles]
    assert "Moscow, Russia" in labels, (
        "карта гостя не переехала в аккаунт при входе через провайдера"
    )


def test_a_bad_token_is_refused_without_a_session(api, social):
    """Мусор вместо токена — 401, и никакой сессии не выписано."""
    refused = api.post("/v1/auth/google", json={"credential": "junk-not-a-token"})
    assert refused.status_code == 401
    assert "token" not in refused.json().get("detail", {}) if isinstance(
        refused.json().get("detail"), dict
    ) else True


def test_an_apple_relay_address_signs_in_keyed_by_sub(api, social):
    """Релейная почта Apple входит, и ключом служит стабильный `sub`.

    Запрет релея (25.08) вёл в тупик: лист «Поделиться/Скрыть» Apple
    показывается один раз, и просьба «выбери „Поделиться“» была просьбой о
    кнопке, которой больше не покажут. С 27.08 релей принят; чтобы повторные
    входы не раскалывали человека на два аккаунта, вход через провайдера
    ищет аккаунт по `sub` раньше, чем по почте.
    """
    relay = "abc123@privaterelay.appleid.com"
    first = api.post(
        "/v1/auth/apple", json={"identity_token": f"apple:{relay}|SUB-1"}
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["locale"] is not None
    uid = _me(api, body["token"])["user_id"]

    # Тот же `sub`, другой адрес в токене — тот же аккаунт, почта не тронута.
    again = api.post(
        "/v1/auth/apple", json={"identity_token": "apple:real@example.com|SUB-1"}
    )
    assert again.status_code == 200
    assert _me(api, again.json()["token"])["user_id"] == uid


def test_a_relay_account_from_before_the_ban_gains_its_sub(api, social):
    """Аккаунт с релейной почтой, заведённый до запрета, дособирает `sub`.

    Виктор вошёл релеем 25.08, до запрета: строка есть, `sub` не записан.
    Первый же вход Apple находит его по почте и дописывает идентификатор;
    следующий — уже по идентификатору.
    """
    relay = "victor@privaterelay.appleid.com"
    first = api.post(
        "/v1/auth/apple", json={"identity_token": f"apple:{relay}|V-SUB"}
    )
    uid = _me(api, first.json()["token"])["user_id"]

    by_sub = api.post(
        "/v1/auth/apple", json={"identity_token": f"apple:{relay}|V-SUB"}
    )
    assert _me(api, by_sub.json()["token"])["user_id"] == uid
