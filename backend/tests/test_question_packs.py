"""Пачки вопросов и «Год вперёд» — четыре товара волны Co-Star (01.09.2026).

Что прибито:

* размер пачки живёт в самой строке гранта (`questions:N`) и складывается по
  покупкам — смена каталога не отнимает купленного;
* пачка тратится ПОСЛЕ включённых порций и отвечает сильной моделью;
* возврат денег забирает и вопросы;
* «Год вперёд» открывает соляр на 366 дней и истекает сам — бессрочного
  доступа к пересчитываемой системе не существует (правило NOT_A_DOOR цело).
"""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta

import pytest

from tests.conftest import SOFIA, read_async

PASSWORD = "test-terminal-password"
TERMINAL = "TestTerminal1"


def _signed(body: dict) -> dict:
    flat = {
        k: ("true" if v else "false") if isinstance(v, bool) else str(v)
        for k, v in body.items()
        if k != "Token" and not isinstance(v, (dict, list)) and v is not None
    }
    flat["Password"] = PASSWORD
    body["Token"] = hashlib.sha256(
        "".join(v for _, v in sorted(flat.items())).encode()
    ).hexdigest()
    return body


@pytest.fixture
def tbank_api(api, monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("ALMA_BILLING_PROVIDER", "tbank")
    monkeypatch.setenv("TBANK_TERMINAL_KEY", TERMINAL)
    monkeypatch.setenv("TBANK_PASSWORD", PASSWORD)
    config_module.settings.cache_clear()
    yield api
    config_module.settings.cache_clear()


def _buy(api, auth_headers, product: str, *, amount: int, payment: int) -> str:
    """Купить товар через веб-путь: заказ + подписанная нотификация."""
    api.get("/v1/billing/entitlements", headers=auth_headers)

    async def user_id():
        from sqlalchemy import select

        from alma.db.models import User
        from alma.db.session import session_scope

        async with session_scope() as session:
            return (await session.execute(select(User))).scalars().one().id

    uid = read_async(user_id)

    async def order():
        import uuid

        from alma.db.models import WebOrder
        from alma.db.session import session_scope

        oid = uuid.uuid4().hex
        async with session_scope() as session:
            session.add(WebOrder(order_id=oid, user_id=uid, product=product))
        return oid

    oid = read_async(order)
    answer = api.post(
        "/v1/billing/webhook",
        content=json.dumps(_signed({
            "TerminalKey": TERMINAL,
            "OrderId": oid,
            "Success": True,
            "Status": "CONFIRMED",
            "PaymentId": payment,
            "ErrorCode": "0",
            "Amount": amount,
        })).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert answer.status_code == 200, answer.text
    return uid


# ── пачки ──────────────────────────────────────────────────────────────────

def test_pack_sizes_live_in_the_grant_itself():
    from alma.billing.catalogue import PRODUCTS

    for key, count in (("questions.5", 5), ("questions.10", 10), ("questions.25", 25)):
        item = PRODUCTS[key]
        assert item.slug == f"questions:{count}", (
            "размер обязан ехать в системе гранта — колонки количества нет"
        )
        assert item.kind == "consumable", "пачка покупается многократно"
        assert item.scope == "questions"


def test_bought_packs_add_up_and_a_refund_takes_its_questions_back(
    tbank_api, auth_headers
):
    uid = _buy(tbank_api, auth_headers, "questions.5", amount=24900, payment=910001)
    _buy(tbank_api, auth_headers, "questions.10", amount=44900, payment=910002)

    async def credits():
        from sqlalchemy import select

        from alma.api.routers.readings import _pack_credits
        from alma.db.models import User
        from alma.db.session import session_scope

        async with session_scope() as session:
            user = (
                await session.execute(select(User).where(User.id == uid))
            ).scalars().one()
            return await _pack_credits(session, user)

    assert read_async(credits) == 15, "две пачки складываются"

    # Возврат первой пачки: минус её пять вопросов, десятка остаётся.
    answer = tbank_api.post(
        "/v1/billing/webhook",
        content=json.dumps(_signed({
            "TerminalKey": TERMINAL,
            "OrderId": "x" * 32,
            "Success": True,
            "Status": "REFUNDED",
            "PaymentId": 910001,
            "ErrorCode": "0",
            "Amount": 24900,
        })).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert answer.status_code == 200, answer.text
    assert read_async(credits) == 10, "возврат забирает и вопросы"


def test_the_pack_opens_after_the_welcome_wall_and_speaks_strong(
    tbank_api, auth_headers
):
    """Бесплатный тратит приветственные, потом купленную пачку — сильной
    моделью; кончилась пачка — та же стена, что была."""
    tbank_api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    uid = _buy(tbank_api, auth_headers, "questions.5", amount=24900, payment=920001)

    async def gate_after(welcome_spent: int, pack_spent: int):
        from sqlalchemy import select

        from alma.api.routers import readings as r
        from alma.db.models import User
        from alma.db.session import session_scope

        async with session_scope() as session:
            user = (
                await session.execute(select(User).where(User.id == uid))
            ).scalars().one()
            welcome = r._welcome(mid="m")
            if welcome_spent:
                await r._count(
                    session, user, welcome.metric, welcome_spent,
                    day=r._period_start(welcome.period),
                )
            if pack_spent:
                await r._count(
                    session, user, r.PACK_QUESTIONS_METRIC, pack_spent,
                    day=r._period_start("once"),
                )
            await session.flush()
            allowance, guard_tier = await r._chat_gate(
                session, user, locale="en"
            )
            return allowance.tier, allowance.metric, guard_tier

    tier, metric, guard_tier = read_async(lambda: gate_after(3, 0))
    assert (tier, metric) == ("pack", "questions_pack"), (
        "после приветственных обязан открыться купленный запас"
    )
    assert guard_tier == "owner", (
        "пачка обязана считаться по платному потолку месяца: бесплатный "
        "резал бы купленные вопросы на середине (QA-ревью 01.09.2026)"
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as refusal:
        read_async(lambda: gate_after(0, 5))
    assert refusal.value.status_code == 429, "пустая пачка — та же честная стена"


# ── год вперёд ─────────────────────────────────────────────────────────────

def test_the_year_ahead_opens_solar_return_for_a_year_not_forever(
    tbank_api, auth_headers
):
    _buy(tbank_api, auth_headers, "report.year", amount=109900, payment=930001)

    held = tbank_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert "solar-return" in held.get("unlocked", []), held

    async def row():
        from sqlalchemy import select

        from alma.db.models import Entitlement, utcnow
        from alma.db.session import session_scope

        async with session_scope() as session:
            grant = (
                await session.execute(select(Entitlement))
            ).scalars().one()
            from alma.db.models import as_utc

            return grant.kind, (as_utc(grant.expires_at) - utcnow())

    kind, left = read_async(row)
    assert kind == "consumable", "следующий год покупается снова"
    assert timedelta(days=360) < left <= timedelta(days=366), (
        "год, а не навсегда: пересчитываемая система бессрочно не продаётся"
    )
