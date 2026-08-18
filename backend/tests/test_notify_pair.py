"""Пуш «отчёт пары готов»: один грант — максимум один доставленный пуш.

Проверяется не отправка (она — четыре строки фейкового транспорта), а всё
вокруг неё, как и у дневной заметки: идемпотентность на повторе, тишина без
токенов и без ошибок в логе, тишина на тестовом гранте, честный запасной текст
при упавшем расчёте — и настоящий фактор из настоящего расчёта совместимости,
когда он есть.

Пары рождений — SOFIA (владелец) × LUCAS (партнёр) из conftest: у этой пары
Луна партнёра стоит в седьмом доме владельца, то есть расчёт даёт ровно тот
фактор, который рисует кадр W7. Тест на это опирается сознательно: если движок
однажды посчитает иначе, заголовок обязан измениться вместе с ним, а не
остаться заученной строкой.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

import pytest
from conftest import LUCAS, SOFIA, database_url, run_async

# Фикстура подписи Apple берётся оттуда же, откуда её берёт
# `test_billing_pairs`, и по той же причине: вторая копия помощника,
# собирающего JWS, — это вторая вещь, которую придётся держать в согласии с
# RFC 7515.
from test_billing_appstore import apple  # noqa: F401 - pytest fixture

from alma.db.models import Profile, UsageCounter, User, new_id, utcnow
from alma.notify import pair, tokens
from alma.notify.transport import Push, Receipt, Verdict


class Vendor:
    """Транспорт, который записывает вместо того, чтобы слать."""

    def __init__(self, platform: str = "ios", receipt: Receipt | None = None) -> None:
        self.platform = platform
        self.receipt = receipt or Receipt(Verdict.sent)
        self.sent: list[Push] = []

    async def send(self, token, push: Push) -> Receipt:
        self.sent.append(push)
        return self.receipt


@pytest.fixture
def db(tmp_path, monkeypatch):
    from alma import config as config_module
    from alma.db import session as session_module

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "pair_push.db"))
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()
    run_async(session_module.create_all)
    yield session_module
    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


def _profile(user_id: str, birth: dict, *, is_self: bool, name: str | None = None) -> Profile:
    return Profile(
        id=new_id(),
        user_id=user_id,
        is_self=is_self,
        name=name or birth.get("name"),
        birth_date=date.fromisoformat(birth["birth_date"]),
        birth_time=birth["birth_time"],
        latitude=birth["latitude"],
        longitude=birth["longitude"],
        timezone=birth["timezone"],
        place_label=birth.get("place_label"),
    )


async def buyer(
    session,
    *,
    with_token: bool = True,
    locale: str | None = None,
    partner_name: str = "Marcus",
) -> tuple[User, Profile]:
    """Один покупатель: свой профиль, партнёр и (обычно) один телефон."""
    user = User(id=new_id(), provider="guest", locale="en", last_seen_at=utcnow())
    session.add(user)
    await session.flush()
    me = _profile(user.id, SOFIA, is_self=True)
    partner = _profile(user.id, LUCAS, is_self=False, name=partner_name)
    session.add_all([me, partner])
    await session.flush()
    if with_token:
        await tokens.register(
            session,
            user_id=user.id,
            platform="ios",
            token=(new_id() * 3)[:64].replace("-", "a"),
            timezone="Europe/Warsaw",
            locale=locale,
        )
        await session.flush()
    return user, partner


# ── грант → ровно один пуш, с настоящим фактором ───────────────────────────


def test_a_pair_grant_sends_one_push_with_a_real_factor(db):
    """Заголовок — факт из расчёта, payload — то, что клиент уже умеет читать.

    `type: "pair_ready"` — клиент шлёт `push_opened{type}` по тапу;
    `profile_id` — чтобы однажды открывать отчёт сразу. Фактор для этой пары —
    Луна Лукаса в седьмом доме Софии, и он обязан быть в тексте, а не в
    выдуманной строке.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user, partner = await buyer(session)
            outcome = await pair.report_ready(
                session, user,
                partner_id=partner.id, source="appstore",
                transports={"ios": vendor},
            )
            return outcome, partner.id

    outcome, partner_id = run_async(work)
    assert outcome == "sent"
    assert len(vendor.sent) == 1

    push = vendor.sent[0]
    assert push.data == {"type": "pair_ready", "profile_id": partner_id}
    assert push.title == "Marcus's Moon sits in your seventh house"
    assert push.body == pair.BODIES["en"]
    # Ни одного глагола-приглашения — правило W7: заголовок остаётся фактом.
    assert "buy" not in push.title.lower() and "open" not in push.title.lower()


def test_the_payload_reaches_apns_as_a_literal_title_not_a_key(db):
    """Ключей пары в замороженном бандле клиента нет — на провод едет
    предложение, и рядом с ним не должно быть `title-loc-key`, который iOS
    показал бы сырой строкой."""
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user, partner = await buyer(session)
            await pair.report_ready(
                session, user,
                partner_id=partner.id, source="appstore",
                transports={"ios": vendor},
            )
            return vendor.sent[0]

    push = run_async(work)

    from alma.notify.apns import APNs

    alert = APNs.payload(push)["aps"]["alert"]
    assert alert["title"] == push.title
    assert "title-loc-key" not in alert
    assert alert["body"] == push.body and "loc-key" not in alert


# ── повтор ─────────────────────────────────────────────────────────────────


def test_a_repeated_verification_does_not_push_again(db):
    """Одна покупка приходит дважды: /verify и нотификация магазина.

    Оба пути зовут хук, счётчик «одна пара — один пуш» пропускает первый и
    молчит на втором — что бы ни было источником повтора.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user, partner = await buyer(session)
            first = await pair.report_ready(
                session, user, partner_id=partner.id, source="appstore",
                transports={"ios": vendor},
            )
            second = await pair.report_ready(
                session, user, partner_id=partner.id, source="appstore",
                transports={"ios": vendor},
            )
            return first, second

    first, second = run_async(work)
    assert first == "sent"
    assert second == "already"
    assert len(vendor.sent) == 1


def test_a_second_partner_is_a_second_push(db):
    """Дедупликация — по паре, а не по человеку: второй оплаченный партнёр —
    это второй готовый отчёт, и о нём молчать нельзя."""
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user, partner = await buyer(session)
            other = _profile(user.id, SOFIA, is_self=False, name="Katya")
            session.add(other)
            await session.flush()
            await pair.report_ready(
                session, user, partner_id=partner.id, source="appstore",
                transports={"ios": vendor},
            )
            outcome = await pair.report_ready(
                session, user, partner_id=other.id, source="appstore",
                transports={"ios": vendor},
            )
            return outcome

    assert run_async(work) == "sent"
    assert len(vendor.sent) == 2


# ── тишина там, где она положена ───────────────────────────────────────────


def test_no_device_tokens_means_silence_without_errors(db, caplog):
    """Человек без токенов (или выключивший уведомления — это удаление
    токенов) просто не получает пуш. Ни ошибки, ни занятой строки счётчика."""
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user, partner = await buyer(session, with_token=False)
            with caplog.at_level(logging.DEBUG, logger="alma.notify.pair"):
                outcome = await pair.report_ready(
                    session, user, partner_id=partner.id, source="appstore",
                    transports={"ios": vendor},
                )
            claimed = await session.get(
                UsageCounter, pair.counter_key(user.id, partner.id)
            )
            return outcome, claimed

    outcome, claimed = run_async(work)
    assert outcome == "unreachable"
    assert vendor.sent == []
    assert claimed is None, "день не занят: токен может появиться позже"
    worst = [r for r in caplog.records if r.levelno > logging.WARNING]
    assert worst == [], f"тишина не должна стоить ошибок в логе: {worst}"


def test_a_dev_grant_is_silent(db):
    """Грант, выписанный руками или тестово, — не продажа. `source` решает."""
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user, partner = await buyer(session)
            outcomes = []
            for source in ("unknown", "manual", "dev-console"):
                outcomes.append(
                    await pair.report_ready(
                        session, user, partner_id=partner.id, source=source,
                        transports={"ios": vendor},
                    )
                )
            return outcomes

    assert run_async(work) == ["skipped: source"] * 3
    assert vendor.sent == []


def test_no_configured_transport_is_quiet_not_fatal(db, caplog):
    """Главное расхождение с daily.run: без APNs-ключа платёжный путь обязан
    жить дальше, а не падать в `PushUnavailable`."""

    async def work():
        async with db.session_scope() as session:
            user, partner = await buyer(session)
            with caplog.at_level(logging.DEBUG, logger="alma.notify.pair"):
                # transports=None → configured_platforms(), а креденшалов в
                # тестовом окружении нет — ровно прод без ALMA_APNS_*.
                return await pair.report_ready(
                    session, user, partner_id=partner.id, source="appstore"
                )

    assert run_async(work) == "no transport"
    worst = [r for r in caplog.records if r.levelno > logging.WARNING]
    assert worst == []


# ── честность текста ───────────────────────────────────────────────────────


def test_a_broken_calc_falls_back_to_an_honest_line(db, monkeypatch):
    """Расчёт упал — фактор не выдумывается, пуш всё равно уходит."""
    vendor = Vendor()

    def broken(*args, **kwargs):
        raise RuntimeError("the ephemeris is on fire")

    monkeypatch.setattr(pair, "_factor_for", broken)

    async def work():
        async with db.session_scope() as session:
            user, partner = await buyer(session)
            return await pair.report_ready(
                session, user, partner_id=partner.id, source="googleplay",
                transports={"ios": vendor},
            )

    assert run_async(work) == "sent"
    push = vendor.sent[0]
    assert push.title == "Marcus — your reading is ready"
    assert push.data["type"] == "pair_ready"


def test_a_deleted_partner_profile_keeps_the_push_but_not_a_name(db):
    """Грант живёт дольше профиля (А7 §12): пуш уходит, чужих и удалённых
    имён в нём нет."""
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user, partner = await buyer(session)
            await session.delete(partner)
            gone = partner.id
            await session.flush()
            return await pair.report_ready(
                session, user, partner_id=gone, source="appstore",
                transports={"ios": vendor},
            )

    assert run_async(work) == "sent"
    assert vendor.sent[0].title == "Your reading is ready"


def test_the_title_arrives_in_the_language_of_the_device(db):
    """Локаль — правилом дневной заметки: устройство раньше аккаунта."""
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user, partner = await buyer(session, locale="ru")
            await pair.report_ready(
                session, user, partner_id=partner.id, source="credit",
                transports={"ios": vendor},
            )
            return vendor.sent[0]

    push = run_async(work)
    assert push.title == "Marcus: Луна в вашем седьмом доме"
    assert push.body == pair.BODIES["ru"]


# ── неудачная отправка ─────────────────────────────────────────────────────


def test_a_failed_send_gives_the_pair_back(db):
    """«Максимум один пуш» считает доставленные, а не попытки: вендор в
    плохую минуту не съедает уведомление навсегда — повтор события шлёт."""
    unwell = Vendor(receipt=Receipt(Verdict.retry, "ServiceUnavailable"))
    recovered = Vendor()

    async def work():
        async with db.session_scope() as session:
            user, partner = await buyer(session)
            failed = await pair.report_ready(
                session, user, partner_id=partner.id, source="appstore",
                transports={"ios": unwell},
            )
            later = await pair.report_ready(
                session, user, partner_id=partner.id, source="appstore",
                transports={"ios": recovered},
            )
            return failed, later

    failed, later = run_async(work)
    assert failed == "failed"
    assert later == "sent"
    assert len(recovered.sent) == 1


# ── через настоящий триггер ────────────────────────────────────────────────


def test_binding_a_purchase_by_hand_fires_the_push(api, monkeypatch):
    """Сквозной путь: /billing/pair/bind выписывает грант — и хук в роутере
    шлёт ровно один пуш, а повтор привязки не добавляет второго."""
    from alma.db.models import Purchase
    from alma.db.session import session_factory

    vendor = Vendor()
    monkeypatch.setattr(pair, "_transports", lambda: {"ios": vendor})

    headers = {
        "Authorization": f"Bearer {api.get('/v1/auth/session').json()['token']}"
    }
    mine = api.post(
        "/v1/profiles", json={**SOFIA, "is_self": True}, headers=headers
    )
    assert mine.status_code == 201, mine.text
    partner = api.post(
        "/v1/profiles",
        json={**LUCAS, "is_self": False, "relation": "partner", "name": "Marcus"},
        headers=headers,
    )
    assert partner.status_code == 201, partner.text
    partner_id = partner.json()["id"]

    device = api.post(
        "/v1/notifications/devices",
        json={"platform": "ios", "token": "a" * 64},
        headers=headers,
    )
    assert device.status_code == 201, device.text

    # Оплаченная и не привязанная покупка — состояние, ради которого /bind
    # существует. Пишется напрямую: путь её появления проверен в
    # test_billing_pairs, здесь интересен только хук после гранта.
    async def plant():
        async with session_factory()() as session:
            from sqlalchemy import select

            owner = (await session.execute(select(User))).scalars().first()
            session.add(
                Purchase(
                    user_id=owner.id,
                    provider="appstore",
                    transaction_id="2000000600009999",
                    product="pair.check",
                    status="unbound",
                    amount_cents=4990,
                )
            )
            await session.commit()

    run_async(plant)

    bound = api.post(
        "/v1/billing/pair/bind",
        json={"transaction": "2000000600009999", "profile_id": partner_id},
        headers=headers,
    )
    assert bound.status_code == 200, bound.text
    assert len(vendor.sent) == 1

    push = vendor.sent[0]
    assert push.data == {"type": "pair_ready", "profile_id": partner_id}
    assert push.title == "Marcus's Moon sits in your seventh house"

    again = api.post(
        "/v1/billing/pair/bind",
        json={"transaction": "2000000600009999", "profile_id": partner_id},
        headers=headers,
    )
    assert again.status_code == 200
    assert len(vendor.sent) == 1, "повторная привязка не шлёт второго пуша"


def test_a_verified_store_purchase_fires_the_push_once(api, apple, monkeypatch):
    """Второй роутерный хук — `_apply` за `/iap/verify`: покупка с токеном
    intent'а выписывает грант и шлёт один пуш; повторная верификация той же
    транзакции (StoreKit пере-доставляет незакрытые) не добавляет второго."""
    from test_billing_appstore import BUNDLE, _sign, _transaction

    from alma import config as config_module

    monkeypatch.setenv("APPLE_BUNDLE_ID", BUNDLE)
    config_module.settings.cache_clear()

    vendor = Vendor()
    monkeypatch.setattr(pair, "_transports", lambda: {"ios": vendor})

    headers = {
        "Authorization": f"Bearer {api.get('/v1/auth/session').json()['token']}"
    }
    assert (
        api.post("/v1/profiles", json={**SOFIA, "is_self": True}, headers=headers)
        .status_code == 201
    )
    partner_id = api.post(
        "/v1/profiles",
        json={**LUCAS, "is_self": False, "relation": "partner", "name": "Marcus"},
        headers=headers,
    ).json()["id"]
    assert (
        api.post(
            "/v1/notifications/devices",
            json={"platform": "ios", "token": "b" * 64},
            headers=headers,
        ).status_code == 201
    )

    opened = api.post(
        "/v1/billing/pair/intent", json={"profile_id": partner_id}, headers=headers
    ).json()
    payload = _transaction(
        product="pair.check",
        transaction_id="2000000600008888",
        kind="Consumable",
        price=4990,
    )
    payload["appAccountToken"] = opened["app_account_token"]
    signed = _sign(payload, apple["key"], apple["chain"])

    body = {
        "platform": "appstore",
        "product": "pair.check",
        "transaction": signed,
    }
    first = api.post("/v1/billing/iap/verify", json=body, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["status"].startswith("granted")
    assert len(vendor.sent) == 1
    assert vendor.sent[0].data == {"type": "pair_ready", "profile_id": partner_id}
    assert vendor.sent[0].title == "Marcus's Moon sits in your seventh house"

    second = api.post("/v1/billing/iap/verify", json=body, headers=headers)
    assert second.status_code == 200
    assert len(vendor.sent) == 1, "повторная верификация не шлёт второго пуша"

    config_module.settings.cache_clear()
