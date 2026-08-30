"""Т-Банк: третий адаптер шва — карта и СБП для страницы «Как оплатить».

Фикстуры здесь — документированные формы нотификаций эквайринга Т-Банка, а
не пойманный трафик. Подпись собирается локальной функцией, написанной по
спецификации (SHA-256 отсортированной конкатенации значений с добавленным
`Password`), а не вызовом `tbank.sign`: тест, который просит `verify`
проверить собственный вывод, доказывает лишь детерминизм.

Ключевое отличие от Paddle/Dodo, которое стерегут тесты владельца платежа:
нотификация Т-Банка не возвращает метаданных, и мост к владельцу — строка
`WebOrder`, созданная нашим сервером при `Init`. Нотификация без такой
строки обязана не выдать ничего.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from alma.billing import tbank
from alma.billing.provider import InvalidSignature
from tests.conftest import read_async

PASSWORD = "test-terminal-password"
TERMINAL = "TestTerminal1"


def _sign(payload: dict, password: str = PASSWORD) -> str:
    """Подпись по спецификации Т-Банка, написанная руками.

    Все корневые скалярные поля без `Token` и вложенных объектов, плюс пара
    `Password`; сортировка по имени ключа, конкатенация значений, SHA-256.
    Булевы — строчными, как их сериализует их сторона.
    """
    flat = {}
    for key, value in payload.items():
        if key == "Token" or isinstance(value, (dict, list)) or value is None:
            continue
        flat[key] = ("true" if value else "false") if isinstance(value, bool) else str(value)
    flat["Password"] = password
    return hashlib.sha256(
        "".join(v for _, v in sorted(flat.items())).encode()
    ).hexdigest()


def _notification(**extra) -> dict:
    body = {
        "TerminalKey": TERMINAL,
        "OrderId": "o" * 32,
        "Success": True,
        "Status": "CONFIRMED",
        "PaymentId": 700001,
        "ErrorCode": "0",
        "Amount": 49900,
        **extra,
    }
    body["Token"] = _sign(body)
    return body


# ── подпись ────────────────────────────────────────────────────────────────

def test_a_valid_token_passes():
    body = _notification()
    tbank.verify(json.dumps(body).encode(), {}, secret=PASSWORD)


def test_a_missing_token_is_refused():
    body = _notification()
    del body["Token"]
    with pytest.raises(InvalidSignature):
        tbank.verify(json.dumps(body).encode(), {}, secret=PASSWORD)


def test_a_wrong_password_is_refused():
    body = _notification()
    with pytest.raises(InvalidSignature):
        tbank.verify(json.dumps(body).encode(), {}, secret="other-password")


def test_a_body_changed_after_signing_is_refused():
    body = _notification()
    body["Amount"] = 1
    with pytest.raises(InvalidSignature):
        tbank.verify(json.dumps(body).encode(), {}, secret=PASSWORD)


def test_no_password_configured_refuses_rather_than_accepts(monkeypatch):
    from alma import config as config_module

    monkeypatch.delenv("TBANK_PASSWORD", raising=False)
    config_module.settings.cache_clear()
    with pytest.raises(InvalidSignature):
        tbank.verify(json.dumps(_notification()).encode(), {})
    config_module.settings.cache_clear()


def test_booleans_sign_lowercase_and_nested_objects_stay_out():
    """`Success: true` подписывается словом `true`, `DATA`/`Receipt` — нет.

    Токен, собранный из питоньего `True`, не совпадает никогда, и отказ
    неотличим от неверного пароля — против этого и закреплено.
    """
    body = _notification(DATA={"Email": "x@y.z"})
    assert _sign({k: v for k, v in body.items() if k != "DATA"}) == body["Token"]
    tbank.verify(json.dumps(body).encode(), {}, secret=PASSWORD)


# ── словарь событий ────────────────────────────────────────────────────────

def test_every_documented_status_is_classified():
    """Каждый статус из таблицы Т-Банка — в одном из трёх множеств.

    Статус, которого нет ни в GRANTING, ни в REVOKING, ни в IGNORED_REASONS,
    — это статус, о котором никто не подумал; следующий человек обязан
    прочитать причину, прежде чем добавить строку в REVOKING.
    """
    documented = {
        "NEW", "FORM_SHOWED", "3DS_CHECKING", "AUTHORIZED", "CONFIRMED",
        "REVERSED", "REFUNDED", "PARTIAL_REFUNDED", "REJECTED",
        "DEADLINE_EXPIRED", "CANCELED", "CHECKED", "COMPLETED",
    }
    named = tbank.GRANTING | tbank.REVOKING | set(tbank.IGNORED_REASONS)
    assert documented <= named, documented - named


def test_the_idempotency_key_separates_states_of_one_payment():
    confirmed = tbank.parse(_notification()).normalise()
    refunded = tbank.parse(_notification(Status="REFUNDED")).normalise()
    assert confirmed.id != refunded.id, "возврат — не дубль оплаты"
    again = tbank.parse(_notification()).normalise()
    assert confirmed.id == again.id, "ретрай той же нотификации — дубль"


def test_amounts_are_kopecks_and_the_currency_is_rub():
    event = tbank.parse(_notification()).normalise()
    assert event.amount_cents == 49900
    assert event.currency == "RUB"
    assert event.priced_by_us is True


def test_a_partial_refund_does_not_close_the_grant():
    event = tbank.parse(_notification(Status="PARTIAL_REFUNDED")).normalise()
    assert event.revokes is True and event.closes_the_grant is False


# ── сквозняк через /v1/billing/webhook ─────────────────────────────────────

@pytest.fixture
def tbank_api(api, monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("ALMA_BILLING_PROVIDER", "tbank")
    monkeypatch.setenv("TBANK_TERMINAL_KEY", TERMINAL)
    monkeypatch.setenv("TBANK_PASSWORD", PASSWORD)
    config_module.settings.cache_clear()
    yield api
    config_module.settings.cache_clear()


def _post(api, payload: dict):
    return api.post(
        "/v1/billing/webhook",
        content=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )


def _user_id(api, auth_headers) -> str:
    async def who():
        from sqlalchemy import select

        from alma.db.models import User
        from alma.db.session import session_scope

        async with session_scope() as session:
            return (await session.execute(select(User))).scalars().one().id

    api.get("/v1/billing/entitlements", headers=auth_headers)
    return read_async(who)


def _order(user_id: str, product: str, order_id: str = "o" * 32) -> str:
    async def put():
        from alma.db.models import WebOrder
        from alma.db.session import session_scope

        async with session_scope() as session:
            session.add(WebOrder(order_id=order_id, user_id=user_id, product=product))
        return order_id

    return read_async(put)


def test_a_confirmed_payment_with_an_order_grants_the_door(tbank_api, auth_headers):
    owner = _user_id(tbank_api, auth_headers)
    _order(owner, "door.natal")

    answer = _post(tbank_api, _notification())
    assert answer.status_code == 200, answer.text

    held = tbank_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert "natal" in held.get("unlocked", []), held


def test_a_notification_without_an_order_grants_nothing(tbank_api, auth_headers):
    """Мост к владельцу — только наша строка заказа.

    Нотификация с чужим `OrderId` на наш адрес — подписанная нашим же
    паролем — всё равно не выдаёт ничего: заказа нет, владельца нет.
    """
    _user_id(tbank_api, auth_headers)
    answer = _post(tbank_api, _notification(OrderId="f" * 32))
    assert answer.status_code in (200, 500), answer.text

    held = tbank_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert held.get("unlocked", []) == [], held


def test_a_recurrent_payment_grants_the_month_and_keeps_the_rebill_id(
    tbank_api, auth_headers
):
    owner = _user_id(tbank_api, auth_headers)
    _order(owner, "sub.monthly")

    answer = _post(
        tbank_api,
        _notification(Amount=99900, RebillId=555001, PaymentId=700002),
    )
    assert answer.status_code == 200, answer.text

    async def plan():
        from sqlalchemy import select

        from alma.db.models import Entitlement
        from alma.db.session import session_scope

        async with session_scope() as session:
            return (
                await session.execute(select(Entitlement))
            ).scalars().one()

    held = read_async(plan)
    assert held.kind == "monthly" and held.source == "tbank"
    assert held.subscription_id == "555001", (
        "RebillId и есть подписка: им ключуются продления"
    )
    assert held.expires_at is not None and held.renews_at is not None


def test_a_replayed_notification_is_a_duplicate(tbank_api, auth_headers):
    owner = _user_id(tbank_api, auth_headers)
    _order(owner, "door.natal")
    first = _post(tbank_api, _notification())
    second = _post(tbank_api, _notification())
    assert first.status_code == 200 and second.status_code == 200

    async def rows():
        from sqlalchemy import select

        from alma.db.models import Entitlement
        from alma.db.session import session_scope

        async with session_scope() as session:
            return len((await session.execute(select(Entitlement))).scalars().all())

    assert read_async(rows) == 1, "повтор нотификации не выдаёт второй грант"


def test_a_full_refund_takes_the_door_back(tbank_api, auth_headers):
    owner = _user_id(tbank_api, auth_headers)
    _order(owner, "door.natal")
    _post(tbank_api, _notification())
    answer = _post(tbank_api, _notification(Status="REFUNDED"))
    assert answer.status_code == 200, answer.text

    held = tbank_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert held.get("unlocked", []) == [], held


def test_an_unsigned_notification_is_refused(tbank_api):
    body = _notification()
    body["Token"] = "0" * 64
    assert _post(tbank_api, body).status_code == 401


# ── продления ──────────────────────────────────────────────────────────────

def test_cancel_subscription_is_a_local_decision():
    """У Т-Банка нет подписки — списывает наш джоб; отмена = снять renews_at,
    и это делает роутер. Адаптер обязан ответить успехом без сети."""
    import asyncio

    asyncio.run(tbank.TBankProvider().cancel_subscription("555001"))


def test_the_charge_job_skips_cancelled_and_future_plans(tbank_api, auth_headers):
    from datetime import timedelta

    owner = _user_id(tbank_api, auth_headers)
    _order(owner, "sub.monthly")
    _post(tbank_api, _notification(Amount=99900, RebillId=555001, PaymentId=700003))

    async def check():
        from alma.billing import tbank_charges
        from alma.db.models import Entitlement, utcnow
        from alma.db.session import session_scope
        from sqlalchemy import select

        async with session_scope() as session:
            plan = (await session.execute(select(Entitlement))).scalars().one()
            # Свежая подписка — продлевать рано.
            assert await tbank_charges.due(session) == []
            # Наступил срок — подписка в списке.
            plan.renews_at = utcnow() - timedelta(hours=1)
            await session.flush()
            assert len(await tbank_charges.due(session)) == 1
            # Отменена (роутер снял renews_at) — списывать некому и нечего.
            plan.renews_at = None
            await session.flush()
            assert await tbank_charges.due(session) == []

    read_async(check)
