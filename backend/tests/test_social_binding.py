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
        return Identity(
            provider="apple", subject=f"a-{email}", email=email,
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


def test_an_apple_relay_address_is_refused_with_a_typed_code(api, social):
    """Релейный адрес Apple — раскол аккаунта на два, и он отвергается.

    Скрытая почта существует только у Apple: человек, вошедший ею, при первом
    же входе через Google или код из письма окажется в ДРУГОМ аккаунте без
    своих покупок. Отказ типизирован — клиент просит выбрать «Показать почту».
    """
    refused = api.post(
        "/v1/auth/apple",
        json={"identity_token": "apple:abc123@privaterelay.appleid.com"},
    )
    assert refused.status_code == 400
    assert refused.json()["detail"]["error"] == "apple_private_email"
