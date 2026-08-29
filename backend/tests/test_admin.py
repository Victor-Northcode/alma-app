"""Админка: пароль, сессия, подарок по почте, отзыв — и все её отказы.

Появилась 25.08.2026. Самое важное здесь — негативные ветки: админка это
дверь в чужие аккаунты, и каждый способ пройти мимо пароля обязан быть
закрыт тестом, который падал бы на дыре.
"""

from __future__ import annotations

import hashlib

import pytest

from alma.auth import admin_password

PASSWORD = "correct horse"


@pytest.fixture()
def admin_on(monkeypatch):
    """Включённая админка: в конфиге — солёный scrypt-хэш тестового пароля."""
    from alma import config

    monkeypatch.setenv(
        "ALMA_ADMIN_PASSWORD_HASH",
        admin_password.hash_password(PASSWORD),
    )
    config.settings.cache_clear()
    yield
    config.settings.cache_clear()


@pytest.fixture()
def admin_on_legacy_sha256(monkeypatch):
    """Админка со старым голым SHA-256 в конфиге — деплой, который надо перенастроить."""
    from alma import config

    monkeypatch.setenv(
        "ALMA_ADMIN_PASSWORD_HASH",
        hashlib.sha256(PASSWORD.encode()).hexdigest(),
    )
    config.settings.cache_clear()
    yield
    config.settings.cache_clear()


def _token(api) -> str:
    out = api.post("/admin/api/login", json={"password": PASSWORD})
    assert out.status_code == 200, out.text
    return out.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_without_a_hash_the_admin_does_not_exist(api):
    refused = api.post("/admin/api/login", json={"password": "anything"})
    assert refused.status_code == 503


def test_a_wrong_password_is_refused_and_attempts_hit_a_ceiling(api, admin_on):
    for _ in range(5):
        assert (
            api.post("/admin/api/login", json={"password": "nope"}).status_code == 401
        )
    walled = api.post("/admin/api/login", json={"password": PASSWORD})
    assert walled.status_code == 429, (
        "шестая попытка обязана упереться в потолок — даже с верным паролем: "
        "иначе перебор бесплатен"
    )


def test_the_stored_hash_is_salted_and_slow_not_bare_sha256(api, admin_on):
    """Пароль хранится солёным scrypt, а не голым SHA-256 (BUG-005).

    Голый несолёный SHA-256 перебирается по словарю за минуты, стоит хэшу
    утечь. Проверяем свойства, а не строку: два хэша одного пароля различны
    (соль), формат — `scrypt$…`, и верный пароль всё же пускает внутрь.
    """
    one = admin_password.hash_password(PASSWORD)
    two = admin_password.hash_password(PASSWORD)
    assert one != two, "две одинаковые пароли дали одинаковый хэш — соли нет"
    assert one.startswith("scrypt$")
    assert admin_password.hash_password(PASSWORD) != hashlib.sha256(PASSWORD.encode()).hexdigest()
    assert admin_password.verify(PASSWORD, one) is True
    assert admin_password.verify("wrong", one) is False
    # И через HTTP: верный пароль за scrypt-хэшем действительно открывает вход.
    assert api.post("/admin/api/login", json={"password": PASSWORD}).status_code == 200


def test_a_legacy_sha256_hash_is_refused_not_accepted(api, admin_on_legacy_sha256):
    """Старый голый SHA-256 в конфиге больше не пускает — деплой перенастраивают.

    Принять его по-тихому значило бы оставить дыру, ради которой всё написано.
    На старом коде (сравнение с `sha256(password)`) верный пароль тут открывал
    бы вход — теперь отвечает 401, а лог просит перегенерировать хэш.
    """
    refused = api.post("/admin/api/login", json={"password": PASSWORD})
    assert refused.status_code == 401


def test_an_app_token_does_not_open_the_admin(api, admin_on):
    # Свежий токен обычного гостя — валидный, но без метки adm.
    guest = api.get("/v1/auth/session").json()["token"]
    refused = api.get("/admin/api/overview", headers=_auth(guest))
    assert refused.status_code == 401


def test_a_grant_reaches_the_person_and_their_rights(api, admin_on):
    token = _token(api)

    granted = api.post(
        "/admin/api/grant",
        headers=_auth(token),
        json={"email": "friend@example.com", "months": 1},
    )
    assert granted.status_code == 200, granted.text
    body = granted.json()
    assert body["created_account"] is True
    assert body["entitlements"][0]["active"] is True
    assert body["entitlements"][0]["source"] == "owner_grant"

    # Человек входит этой почтой — и попадает ровно в одаренный аккаунт.
    asked = api.post(
        "/v1/auth/magic-link", json={"email": "friend@example.com", "locale": "en"}
    )
    code = asked.json()["debug_code"]
    entered = api.post(
        "/v1/auth/email-code/consume",
        json={"email": "friend@example.com", "code": code},
    )
    assert entered.status_code == 200
    assert entered.json()["user_id"] == body["user_id"], (
        "вход по почте увёл в другой аккаунт — подарок остался сиротой"
    )


def test_only_an_owner_grant_can_be_revoked(api, admin_on):
    token = _token(api)
    body = api.post(
        "/admin/api/grant",
        headers=_auth(token),
        json={"email": "revocable@example.com", "months": 1},
    ).json()
    grant_id = body["entitlements"][0]["id"]

    revoked = api.post(
        "/admin/api/revoke", headers=_auth(token), json={"entitlement_id": grant_id}
    )
    assert revoked.status_code == 200
    assert revoked.json()["entitlements"][0]["revoked_at"] is not None

    twice = api.post(
        "/admin/api/revoke", headers=_auth(token), json={"entitlement_id": grant_id}
    )
    assert twice.status_code == 409


def test_overview_answers_and_counts_the_grant(api, admin_on):
    token = _token(api)
    api.post(
        "/admin/api/grant",
        headers=_auth(token),
        json={"email": "counted@example.com", "months": 1},
    )
    stats = api.get("/admin/api/overview", headers=_auth(token))
    assert stats.status_code == 200
    assert stats.json()["owner_grants"] >= 1


def test_recent_is_real_rows_and_needs_the_admin_token(api, admin_on):
    """Лента прав — настоящие строки базы, и дверь у неё та же, что у остального."""
    token = _token(api)
    api.post(
        "/admin/api/grant",
        headers=_auth(token),
        json={"email": "feed@example.com", "months": None},
    )

    assert api.get("/admin/api/recent").status_code in (401, 403)

    feed = api.get("/admin/api/recent", headers=_auth(token)).json()
    row = next(e for e in feed["entitlements"] if e["email"] == "feed@example.com")
    assert row["system"] == "*" and row["source"] == "owner_grant" and row["active"]
    assert row["expires_at"].startswith("2099")

    stats = api.get("/admin/api/overview", headers=_auth(token)).json()
    assert stats["guests"] == stats["users_total"] - stats["with_email"]


def test_users_are_paged_people_and_guests_stay_out(api, admin_on):
    """«Люди» — страницы живых аккаунтов; гость в них не попадает без просьбы.

    Владелец, 27.08.2026: «нахера мне гостей смотреть» — лента, где на одного
    человека приходилось двадцать безымянных визитов, была нечитаема.
    """
    token = _token(api)
    for email in ("first@example.com", "second@example.com"):
        api.post(
            "/admin/api/grant", headers=_auth(token), json={"email": email, "months": 1}
        )
    # Гость: тот же путь, каким его заводит приложение.
    api.post("/v1/auth/refresh", json={})

    assert api.get("/admin/api/users").status_code in (401, 403)

    out = api.get("/admin/api/users", headers=_auth(token)).json()
    assert out["page"] == 1 and out["pages"] >= 1
    emails = [r["email"] for r in out["rows"]]
    assert "first@example.com" in emails and "second@example.com" in emails
    assert None not in emails, "гость пролез в список людей"
    assert out["total"] == len([e for e in emails if e])

    everyone = api.get(
        "/admin/api/users?guests=true", headers=_auth(token)
    ).json()
    assert everyone["total"] > out["total"], "гости не показались и по просьбе"

    narrowed = api.get(
        "/admin/api/users?q=first", headers=_auth(token)
    ).json()
    assert [r["email"] for r in narrowed["rows"]] == ["first@example.com"]


def test_revenue_shape_and_gate(api, admin_on):
    """Прибыль отвечает итогами, месяцами и страницей покупок — за той же дверью."""
    token = _token(api)
    assert api.get("/admin/api/revenue").status_code in (401, 403)

    out = api.get("/admin/api/revenue", headers=_auth(token)).json()
    assert set(out) == {"totals", "months", "purchases"}
    assert set(out["purchases"]) == {"page", "pages", "total", "rows"}
    # Подарки — не выручка: грант из соседних тестов сюда попасть не должен.
    assert out["purchases"]["total"] == 0 and out["totals"] == []


def test_the_page_itself_is_served(api):
    page = api.get("/admin")
    assert page.status_code == 200
    assert "АДМИНКА" in page.text
