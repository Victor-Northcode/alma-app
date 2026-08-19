"""Восемь мест, где сервис отдавал больше, чем собирался.

Общего кода у этих правок нет — общее у них то, **чем за них платили**, и
каждый тест здесь падает на коде, который был до правки:

* гость заводился любому запросу без токена, а месячный бюджет генераций
  отмерян на `user.id` — значит, бюджетов было столько, сколько раз позвонил
  скрипт;
* `POST /v1/auth/magic-link` слал письмо на любой названный адрес без счёта —
  чужой почтовый ящик и наш счёт за рассылку;
* полная ссылка входа с живым токеном писалась в лог на INFO — строка в логе,
  которая является входом в аккаунт;
* `/ready` без токена называл окружение и **поимённо** ненастроенные секреты;
* дневной потолок событий у анонима считался по заголовку, который присылает
  сам клиент, — то есть не считался;
* проверка токена Google и Apple шла в событийном цикле, а незнакомый `kid`
  гнал её в сеть мимо кэша;
* `is_known_timezone` перечисляла все зоны tzdata на каждом запросе;
* `User.profiles` и `User.entitlements` грузились жадно, и ни одна строка кода
  их не читала.

Половина проверок ниже подменяет сами потолки на маленькие числа. Проверяется
механизм, а не цифра: цифра — решение владельца и живёт рядом с объяснением, а
тест, зашивший тридцать, ломался бы от каждого пересмотра политики.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import pathlib
import threading
from datetime import date

import jwt
import pytest
from conftest import database_url, run_async
from sqlalchemy import func, inspect as sa_inspect, select

from alma import geo, mail
from alma.api import deps
from alma.api.routers import auth as auth_router
from alma.api.routers import events as events_router
from alma.auth import providers
from alma.config import settings
from alma.db import session as session_module
from alma.db.models import MagicLink, Profile, User


# ── 1. гость перестал быть бесконечным ресурсом ────────────────────────────

def test_a_script_cannot_mint_guest_accounts_without_end(api, monkeypatch):
    """Каждый гость — это месячный бюджет генераций. Их не бесконечно много."""
    monkeypatch.setattr(deps, "GUEST_MINTS_PER_HOUR", 3)

    for _ in range(3):
        assert api.get("/v1/auth/session").status_code == 200

    refused = api.get("/v1/auth/session")
    assert refused.status_code == 429
    assert refused.json()["detail"]["error"] == "guest_rate_limit"
    # Срок ожидания назван: клиент, которому отказали молча, повторяет сразу.
    assert refused.headers["Retry-After"]


def test_the_guest_ceiling_never_touches_somebody_who_already_has_an_account(api, monkeypatch):
    """Потолок стоит на *рождении* строки, а не на запросах.

    Иначе первая же правка про деньги стала бы правкой про то, что человек с
    открытым приложением получает 429 на ровном месте.
    """
    monkeypatch.setattr(deps, "GUEST_MINTS_PER_HOUR", 1)
    token = api.get("/v1/auth/session").json()["token"]

    assert api.get("/v1/auth/session").status_code == 429
    mine = api.get("/v1/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert mine.status_code == 200
    assert mine.json()["token"]


def test_each_source_carries_its_own_budget(api, monkeypatch):
    """Один исчерпавший потолок адрес не закрывает дверь всему миру."""
    monkeypatch.setattr(deps, "GUEST_MINTS_PER_HOUR", 1)
    busy = {"CF-Connecting-IP": "203.0.113.1"}
    other = {"CF-Connecting-IP": "203.0.113.2"}

    assert api.get("/v1/auth/session", headers=busy).status_code == 200
    assert api.get("/v1/auth/session", headers=busy).status_code == 429
    assert api.get("/v1/auth/session", headers=other).status_code == 200


def test_forwarded_for_is_not_taken_as_the_source(api, monkeypatch):
    """`X-Forwarded-For` прокси **дописывают**, а не перезаписывают.

    Поэтому первый элемент цепочки — текст вызывающего, и если бы потолок
    считался по нему, он снимался бы одной строкой в заголовке. Ровно та
    болезнь, от которой лечится дневной потолок событий ниже.
    """
    monkeypatch.setattr(deps, "GUEST_MINTS_PER_HOUR", 1)
    assert api.get("/v1/auth/session").status_code == 200

    refused = api.get("/v1/auth/session", headers={"X-Forwarded-For": "203.0.113.9"})
    assert refused.status_code == 429


def test_a_window_counts_per_key_and_then_refuses():
    window = deps.FixedWindow(limit=2, seconds=60)
    assert window.hit("a") is True
    assert window.hit("a") is True
    assert window.hit("a") is False
    assert window.hit("b") is True, "у другого ключа свой счёт"


def test_a_window_does_not_grow_into_a_way_to_exhaust_memory():
    """Ключей столько, сколько адресов, и платит за них память процесса."""
    window = deps.FixedWindow(limit=1, seconds=3600, max_keys=10)
    for number in range(500):
        window.hit(f"198.51.100.{number}")
    assert len(window._counts) <= 10


# ── 2. письма входа под счётом ─────────────────────────────────────────────

def _magic_links_stored() -> int:
    from conftest import read_async

    async def count():
        async with session_module.session_scope() as session:
            return (await session.execute(select(func.count()).select_from(MagicLink))).scalar_one()

    return read_async(count)


def test_one_address_cannot_be_buried_in_sign_in_letters(api, auth_headers):
    """Адрес в теле запроса — чужой ровно так же легко, как свой."""
    victim = {"email": "victim@example.com"}
    for _ in range(auth_router.MAGIC_LINKS_PER_EMAIL_PER_HOUR):
        assert api.post("/v1/auth/magic-link", json=victim, headers=auth_headers).status_code == 202

    before = _magic_links_stored()
    refused = api.post("/v1/auth/magic-link", json=victim, headers=auth_headers)
    assert refused.status_code == 429
    assert refused.json()["detail"]["error"] == "magic_link_rate_limit"
    # Отказ раньше `new_magic_token`: иначе в таблице копились бы живые ссылки,
    # которых никто не заказывал, и каждая из них — вход в аккаунт.
    assert _magic_links_stored() == before


def test_a_list_of_addresses_does_not_get_around_the_letter_ceiling(api, auth_headers):
    """Потолок по адресу сам по себе не мешает пройтись списком по разу."""
    for number in range(auth_router.MAGIC_LINKS_PER_SOURCE_PER_HOUR):
        response = api.post(
            "/v1/auth/magic-link",
            json={"email": f"person{number}@example.com"},
            headers=auth_headers,
        )
        assert response.status_code == 202

    refused = api.post(
        "/v1/auth/magic-link", json={"email": "one-more@example.com"}, headers=auth_headers
    )
    assert refused.status_code == 429


def test_the_case_of_an_address_does_not_reset_its_ceiling(api, auth_headers, monkeypatch):
    """`Sofia@` и `sofia@` — один почтовый ящик и один потолок."""
    monkeypatch.setattr(auth_router, "MAGIC_LINKS_PER_EMAIL_PER_HOUR", 1)
    assert api.post(
        "/v1/auth/magic-link", json={"email": "sofia@example.com"}, headers=auth_headers
    ).status_code == 202
    assert api.post(
        "/v1/auth/magic-link", json={"email": "SOFIA@example.com"}, headers=auth_headers
    ).status_code == 429


def test_the_refusal_says_nothing_about_who_has_an_account(api, auth_headers, monkeypatch):
    """Оба потолка отвечают одинаково — иначе это оракул наоборот."""
    monkeypatch.setattr(auth_router, "MAGIC_LINKS_PER_EMAIL_PER_HOUR", 1)
    monkeypatch.setattr(auth_router, "MAGIC_LINKS_PER_SOURCE_PER_HOUR", 2)

    api.post("/v1/auth/magic-link", json={"email": "known@example.com"}, headers=auth_headers)
    by_email = api.post(
        "/v1/auth/magic-link", json={"email": "known@example.com"}, headers=auth_headers
    )
    api.post("/v1/auth/magic-link", json={"email": "second@example.com"}, headers=auth_headers)
    by_source = api.post(
        "/v1/auth/magic-link", json={"email": "third@example.com"}, headers=auth_headers
    )

    assert by_email.status_code == by_source.status_code == 429
    assert by_email.json() == by_source.json()


# ── 3. ссылка входа не попадает в лог ──────────────────────────────────────

def test_the_sign_in_link_never_reaches_the_log(caplog):
    """Строка лога со ссылкой — это вход в аккаунт.

    Логи живут дольше двадцати минут, на которые выписана ссылка, и ходят туда,
    куда почта не ходит: в агрегатор, в тикет, в чат поддержки.
    """
    caplog.set_level(logging.DEBUG, logger="alma.mail")
    token = "TOKEN-THAT-OPENS-THE-ACCOUNT"

    delivered = asyncio.run(mail.send_magic_link(to="sofia@example.com", token=token))

    assert delivered is False, "почтовик в тестах не настроен — это та самая ветка"
    assert token not in caplog.text
    assert "/sign-in?token=" not in caplog.text
    # А то, ради чего строку читают, осталось: письмо не ушло и кому.
    assert "sofia@example.com" in caplog.text
    assert "mail not configured" in caplog.text


# ── 4. /ready перестал быть картой сервиса ─────────────────────────────────

def test_ready_outside_the_sandbox_says_only_whether_it_is_ready(api, monkeypatch):
    """`missing` — это перечень ещё не повешенных замков, по именам."""
    detailed = api.get("/ready").json()
    assert "missing" in detailed, "локально подробности на месте — они там для человека"

    monkeypatch.setenv("ALMA_ENV", "production")
    monkeypatch.setenv("ALMA_BASE_URL", "https://api.alma.example")
    settings.cache_clear()

    public = api.get("/ready")
    assert public.status_code == 200
    assert set(public.json()) == {"ready"}
    assert public.json()["ready"] is True


def test_liveness_stays_public_and_uninformative(api, monkeypatch):
    """Балансировщику отвечаем всегда — но и ему говорить нечего."""
    monkeypatch.setenv("ALMA_ENV", "production")
    monkeypatch.setenv("ALMA_BASE_URL", "https://api.alma.example")
    settings.cache_clear()

    body = api.get("/health").json()
    assert body["status"] == "ok"
    assert set(body) == {"status", "uptime_seconds"}


# ── 5. дневной потолок анонима нельзя снять сменой заголовка ───────────────

def test_a_fresh_anonymous_id_does_not_reset_the_daily_event_ceiling(api, monkeypatch):
    """`X-Alma-Anon` клиент генерирует сам — потолок по нему был подсказкой."""
    monkeypatch.setattr(events_router, "ANON_EVENTS_PER_SOURCE_PER_DAY", 2)
    beacon = {"stage": "landing_view"}

    for _ in range(2):
        assert api.post(
            "/v1/events", json=beacon, headers={"X-Alma-Anon": "aaaaaaaa-1111"}
        ).status_code == 200

    refused = api.post("/v1/events", json=beacon, headers={"X-Alma-Anon": "bbbbbbbb-2222"})
    assert refused.status_code == 429
    assert refused.json()["detail"]["error"] == "event_rate_limit"

    # Другой источник считается отдельно: потолок стоит против скрипта, а не
    # против второго человека в том же продукте.
    elsewhere = api.post(
        "/v1/events",
        json=beacon,
        headers={"X-Alma-Anon": "cccccccc-3333", "CF-Connecting-IP": "203.0.113.4"},
    )
    assert elsewhere.status_code == 200


def test_an_account_keeps_its_own_event_allowance(api, auth_headers, monkeypatch):
    """Потолок по источнику — про вызывающих без аккаунта.

    У аккаунта счёт свой, в `UsageCounter`, и он переживает перезапуск; смешать
    их значило бы, что один скрипт в кафе выключает воронку всем посетителям.
    """
    monkeypatch.setattr(events_router, "ANON_EVENTS_PER_SOURCE_PER_DAY", 1)
    beacon = {"stage": "landing_view"}

    assert api.post("/v1/events", json=beacon, headers={"X-Alma-Anon": "dddddddd-4444"}).status_code == 200
    assert api.post("/v1/events", json=beacon, headers={"X-Alma-Anon": "eeeeeeee-5555"}).status_code == 429
    assert api.post("/v1/events", json=beacon, headers=auth_headers).status_code == 200


# ── 6. проверка Google и Apple не вешает сервис ────────────────────────────

class _FakeJWKS:
    """Клиент ключей, который считает походы в сеть и никогда не находит `kid`."""

    def __init__(self) -> None:
        self.from_cache = 0
        self.refetched = 0

    def get_signing_keys(self, refresh: bool = False) -> list:
        if refresh:
            self.refetched += 1
        else:
            self.from_cache += 1
        return []

    @staticmethod
    def match_kid(keys: list, kid: str):
        return None


def test_verifying_an_identity_token_leaves_the_event_loop(monkeypatch):
    """Синхронный разбор JWT плюс поход в сеть — на одном потоке все запросы."""
    seen: dict = {}

    def fake_verify(token, *, jwks_url, audience, issuers):
        seen["thread"] = threading.current_thread()
        return {"sub": "abc", "email": "Sofia@Example.com", "email_verified": True, "name": "Sofia"}

    monkeypatch.setattr(providers, "_verify", fake_verify)

    identity = asyncio.run(providers.verify_google("token"))

    assert identity.email == "sofia@example.com"
    assert seen["thread"] is not threading.main_thread()


def test_apple_is_verified_off_the_loop_too(monkeypatch):
    """Обёртка одна на обоих провайдеров — иначе её забывают во втором."""
    seen: dict = {}

    def fake_verify(token, *, jwks_url, audience, issuers):
        seen["thread"] = threading.current_thread()
        return {"sub": "abc", "email": "l@example.com", "email_verified": "true"}

    monkeypatch.setattr(providers, "_verify", fake_verify)

    identity = asyncio.run(providers.verify_apple("token", full_name="Lucas"))

    assert identity.display_name == "Lucas"
    assert seen["thread"] is not threading.main_thread()


def test_an_unknown_key_id_cannot_send_us_to_the_network_every_time(monkeypatch):
    """`{"kid": "<случайное>"}` был бесплатным способом заказать нам поход в сеть."""
    fake = _FakeJWKS()
    monkeypatch.setattr(providers, "_jwk_client", lambda url: fake)
    monkeypatch.setattr(providers, "_refreshed_at", {})
    token = jwt.encode({"sub": "x"}, "a-secret-long-enough-for-sha256-hmac", headers={"kid": "made-up"})

    for _ in range(20):
        with pytest.raises(providers.InvalidIdentityToken):
            providers._verify(
                token,
                jwks_url=providers.GOOGLE_JWKS,
                audience="client-id",
                issuers=providers.GOOGLE_ISSUERS,
            )

    assert fake.refetched == 1, "двадцать чужих запросов — один поход за ключами"
    assert fake.from_cache == 20, "а кэш спрашивается каждый раз, и это бесплатно"


def test_a_token_without_a_key_id_is_refused_without_asking_anybody(monkeypatch):
    fake = _FakeJWKS()
    monkeypatch.setattr(providers, "_jwk_client", lambda url: fake)
    monkeypatch.setattr(providers, "_refreshed_at", {})
    token = jwt.encode({"sub": "x"}, "a-secret-long-enough-for-sha256-hmac")

    with pytest.raises(providers.InvalidIdentityToken):
        providers._verify(
            token,
            jwks_url=providers.GOOGLE_JWKS,
            audience="client-id",
            issuers=providers.GOOGLE_ISSUERS,
        )
    assert fake.refetched == 0 and fake.from_cache == 0


def test_the_key_fetch_waits_no_longer_than_a_person_would(monkeypatch):
    """Умолчание библиотеки — тридцать секунд занятого потока на запрос."""
    monkeypatch.setattr(providers, "_clients", {})
    client = providers._jwk_client(providers.APPLE_JWKS)
    assert client.timeout == providers.JWKS_TIMEOUT_SECONDS
    assert providers.JWKS_TIMEOUT_SECONDS <= 10


# ── 7. список часовых зон собирается один раз ──────────────────────────────

def test_the_timezone_list_is_built_once_and_not_per_request(monkeypatch):
    """`device_timezone` — зависимость без маршрута: её проходит каждый запрос.

    То есть десятки миллисекунд обхода каталога tzdata платились не за проверку
    зоны, а за факт обращения к API.
    """
    calls = []

    def counted():
        calls.append(1)
        return {"Europe/Rome", "Pacific/Auckland"}

    geo._zone_names.cache_clear()
    monkeypatch.setattr(geo, "available_timezones", counted)
    try:
        assert geo.is_known_timezone("Europe/Rome")
        assert geo.is_known_timezone("Pacific/Auckland")
        assert not geo.is_known_timezone("Middle/Earth")
        assert len(calls) == 1
    finally:
        # Кэш держит подменённый список — следующий тест должен увидеть
        # настоящий tzdata, а не два города.
        geo._zone_names.cache_clear()


def test_the_cached_list_is_the_real_one():
    assert geo.is_known_timezone("America/Sao_Paulo")
    assert not geo.is_known_timezone("Middle/Earth")


# ── 8. коллекции пользователя больше не грузятся жадно ─────────────────────

def test_nothing_in_the_codebase_reads_the_user_collections():
    """Основание правки: их не читает ни одна строка.

    Разбором дерева, а не поиском по тексту: `"alma.api.profiles"` в имени
    логгера и `from ..auth.entitlements import …` — это не чтение коллекции, и
    grep путал бы их с ним каждый раз.
    """
    import alma

    package = pathlib.Path(alma.__file__).parent  # не от текущего каталога:
    readers = []                                  # набор запускают и из корня
    for path in sorted(package.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Attribute) and node.attr in {"profiles", "entitlements"}:
                readers.append(f"{path}:{node.lineno}: {ast.unparse(node)}")

    assert readers == [], (
        "кто-то начал читать User.profiles/User.entitlements — тогда либо "
        "просите их явным selectinload в своём запросе, либо возвращайте "
        "жадность вместе с объяснением, чем она окупается: " + "; ".join(readers)
    )


def test_a_user_row_arrives_without_two_extra_queries(tmp_path, monkeypatch):
    """`lazy="selectin"` — это два лишних запроса на **каждое** чтение `user`.

    А читается строка `user` на каждом запросе к API: `deps.visitor` →
    `accounts.resolve`.
    """
    from alma import config as config_module

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "lazy.db"))
    config_module.settings.cache_clear()
    run_async(session_module.create_all)

    async def make() -> str:
        async with session_module.session_scope() as session:
            user = User(id="u-lazy-1", provider="guest")
            session.add(user)
            session.add(
                Profile(
                    user_id=user.id,
                    name="Sofia",
                    is_self=True,
                    birth_date=date(1998, 3, 14),
                    birth_time="04:20",
                    latitude=45.4642,
                    longitude=9.19,
                    timezone="Europe/Rome",
                )
            )
            return user.id

    async def read(user_id: str) -> set[str]:
        async with session_module.session_scope() as session:
            fresh = await session.get(User, user_id)
            return set(sa_inspect(fresh).unloaded)

    user_id = run_async(make)
    unloaded = run_async(lambda: read(user_id))
    asyncio.run(session_module.dispose())

    assert "profiles" in unloaded
    assert "entitlements" in unloaded
