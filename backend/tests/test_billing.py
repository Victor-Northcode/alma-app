"""Billing, tested as an adversary would probe it.

A webhook endpoint that grants paid access is, until the signature is checked,
an endpoint that grants paid access to anyone who can send it a POST. So most
of this file is about refusal: an unsigned request, a wrong secret, a replayed
signature, a body altered after signing, and — the one that costs real money —
the same event delivered twice.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from conftest import read_async

from alma.billing import catalogue as prices
from alma.billing.paddle import Event, InvalidSignature, entitlement_for, parse, verify
from alma.billing.provider import stamp

SECRET = "pdl_ntfset_test_secret"


def _sign(body: bytes, *, secret: str = SECRET, timestamp: int | None = None) -> str:
    stamp = timestamp if timestamp is not None else int(time.time())
    digest = hmac.new(secret.encode(), f"{stamp}:".encode() + body, hashlib.sha256).hexdigest()
    return f"ts={stamp};h1={digest}"


def _event(
    event_type: str = "transaction.completed",
    *,
    event_id: str = "evt_1",
    user_id: str | None = "user-1",
    product: str = "door.natal",
    total: str = "899",
) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "data": {
            "id": "txn_1",
            "currency_code": "USD",
            # Sealed, exactly as `open_session` seals it. A blob of plain
            # `{"user_id": …, "product": …}` is what a payer can write from a
            # console, and nothing reads one any more — so a fixture that
            # wrote one would be testing the attack rather than the purchase.
            "custom_data": stamp(user_id, product) if user_id else {},
            "details": {"totals": {"grand_total": total}},
            "billing_details": {"address": {"country_code": "IT"}},
        },
    }


# ── signature verification ─────────────────────────────────────────────────

def test_a_correctly_signed_body_verifies():
    body = json.dumps(_event()).encode()
    verify(body, _sign(body), secret=SECRET)


def test_an_unsigned_request_is_refused():
    with pytest.raises(InvalidSignature, match="no signature"):
        verify(b"{}", "", secret=SECRET)


def test_a_malformed_header_is_refused():
    for header in ("garbage", "ts=123", "h1=abc", "ts=;h1="):
        with pytest.raises(InvalidSignature):
            verify(b"{}", header, secret=SECRET)


def test_the_wrong_secret_is_refused():
    body = json.dumps(_event()).encode()
    with pytest.raises(InvalidSignature, match="does not match"):
        verify(body, _sign(body, secret="someone-elses-secret"), secret=SECRET)


def test_a_body_altered_after_signing_is_refused():
    """The whole point: the amount cannot be edited in flight."""
    body = json.dumps(_event()).encode()
    signature = _sign(body)
    tampered = json.dumps(_event(total="999999")).encode()
    with pytest.raises(InvalidSignature):
        verify(tampered, signature, secret=SECRET)


def test_a_replayed_signature_expires():
    """A valid signature from last week is still a replay."""
    body = json.dumps(_event()).encode()
    old = _sign(body, timestamp=int(time.time()) - 3600)
    with pytest.raises(InvalidSignature, match="replay"):
        verify(body, old, secret=SECRET)


def test_a_missing_secret_refuses_rather_than_accepting():
    """No configuration must never mean 'accept everything'."""
    body = json.dumps(_event()).encode()
    with pytest.raises(InvalidSignature, match="PADDLE_WEBHOOK_SECRET"):
        verify(body, _sign(body), secret="")


def test_the_comparison_is_constant_time():
    """Byte-at-a-time comparison leaks the signature to a patient attacker."""
    import inspect

    from alma.billing import paddle

    assert "compare_digest" in inspect.getsource(paddle.verify)


# ── event interpretation ───────────────────────────────────────────────────

def test_a_completed_transaction_grants_the_product():
    grant = entitlement_for(parse(_event(product="door.natal")))
    assert (grant.system, grant.kind, grant.duration) == ("natal", "one_time", None)
    assert grant.scope == "system"


def test_a_month_bought_is_a_month_granted_and_not_the_shelf_forever():
    """The defect this replaces cost $29 of goods for $9.99, permanently.

    `entitlement_for` branched on `kind == "annual"` and let everything else
    fall through to a one-time grant with no expiry. The plan's slug is "*", so
    a month's payment wrote an everything-grant that never lapsed, had no
    subscription id to cancel against, and reported itself as working.

    `scope` теперь `all`, а не `live`: подписка v3 продаёт всё, пока за неё
    платят. Срок — единственное, что отличает её от бандла, и он проверяется
    здесь же.
    """
    grant = entitlement_for(parse(_event(product="sub.monthly", total="999")))
    assert grant.system == "*" and grant.kind == "monthly"
    assert grant.scope == "all"
    assert grant.duration is not None and 28 <= grant.duration.days <= 31


def test_the_bundle_is_bought_once_and_never_expires():
    """Пара к тесту выше: та же строка `system="*"`, и всё отличие — в scope и в
    сроке. Бандл со сроком был бы подпиской, подписка без срока — платежом,
    который больше никогда не надо делать."""
    grant = entitlement_for(parse(_event(product="bundle.static", total="1999")))
    assert (grant.system, grant.kind, grant.duration) == ("*", "one_time", None)
    assert grant.scope == "static"


def test_every_recurring_product_is_granted_with_an_expiry():
    """Stated over the catalogue rather than over the two plans we have today.

    A recurring plan granted without a duration is a payment that never has to
    be made again, and `grant()` raises for exactly that — but only if the
    kind reaching it is the recurring one, which is what went wrong.
    """
    for key, item in prices.PRODUCTS.items():
        # Priced at what the catalogue asks. A money event carrying less than
        # the product costs grants nothing, so passing 899 for everything here
        # would have been the relabelling attack wearing a loop.
        grant = entitlement_for(parse(_event(product=key, total=str(item.cents))))
        if item.scope == "pair":
            # Единственная строка, которая намеренно не грантит отсюда: партнёра
            # называет PairIntent (А4, Ф0.3), а не прайс-лист. См. комментарий в
            # `provider.entitlement_for`.
            assert grant is None, key
            continue
        assert grant is not None, key
        if item.interval:
            assert grant.duration is not None, key
            assert grant.kind == item.kind, key
        else:
            assert grant.duration is None, key


def test_a_refund_grants_nothing():
    assert entitlement_for(parse(_event("transaction.refunded"))) is None


def test_an_unknown_event_type_grants_nothing():
    assert entitlement_for(parse(_event("subscription.paused"))) is None


def test_an_unknown_product_grants_nothing():
    assert entitlement_for(parse(_event(product="a-thing-we-do-not-sell"))) is None


def test_the_owner_comes_from_custom_data_not_the_email():
    """A family shares an address; a payment must not attach to a relative."""
    event = parse(_event(user_id="user-42"))
    assert event.user_id == "user-42"


def test_the_amount_and_country_are_read():
    event = parse(_event(total="5900"))
    assert event.amount_cents() == 5900
    assert event.currency() == "USD"
    assert event.country == "IT"


def test_a_missing_total_does_not_raise():
    event = Event(id="e", type="transaction.completed", payload={"data": {}})
    assert event.amount_cents() == 0


# ── the catalogue ──────────────────────────────────────────────────────────

def test_every_static_system_has_a_door_and_the_living_ones_have_none():
    """Раньше здесь стояло «у каждой из восьми систем есть цена». В v3 их пять:
    транзиты и соляр пересчитываются и продаются только подпиской, а
    совместимость покупается на человека (`pair.check`), а не системой. Продать
    любую из этих трёх «навсегда» — значит отдать подписку одним платежом."""
    from alma.calc import SYSTEMS

    doors = {item.slug for item in prices.PRODUCTS.values() if item.band == "door"}
    assert doors == {"natal", "numerology", "birth-card", "astrocartography", "synthesis"}
    assert doors | prices.LIVING_SYSTEMS == set(SYSTEMS)


def test_the_prices_match_the_interface():
    """One door price for every system, one bundle, one plan."""
    assert prices.PRODUCTS["door.natal"].display() == "$4.99"
    assert prices.PRODUCTS["door.synthesis"].display() == "$4.99"
    assert prices.PRODUCTS["pair.check"].display() == "$4.99"
    assert prices.PRODUCTS["bundle.static"].display() == "$19.99"
    assert prices.PRODUCTS["sub.monthly"].display() == "$9.99"


def test_regional_pricing_is_the_same_price_not_a_discount():
    """Charging US dollars in São Paulo is charging four times as much."""
    bundle = prices.PRODUCTS["bundle.static"]
    assert bundle.cents_in("BRL") > bundle.cents_in("USD")
    assert bundle.cents_in("MXN") > bundle.cents_in("USD")


def test_a_country_maps_to_a_currency():
    assert prices.currency_for("BR") == "BRL"
    assert prices.currency_for("mx") == "MXN"
    assert prices.currency_for("DE") == "EUR"
    assert prices.currency_for("US") == "USD"
    assert prices.currency_for(None) == "USD"


# Здесь стояли два теста кредитного добора — «свежая покупка подставляет
# `archive-upgrade` вместо архива» и «кредит в реалах не тратится против
# долларовой цены». Оба удалены вместе с механизмом: v3 сняла с продажи и архив,
# и обе условные цены (ТЗ §2), а `catalogue()` больше не принимает кредит вовсе.
# Правило, которое они охраняли — «в списке нет числа, посчитанного из другого
# числа», — проверяется в `test_prices.py`.


def test_an_unknown_product_is_refused():
    with pytest.raises(ValueError, match="nothing on sale"):
        prices.product("astrology-lessons")


# ══════════════════════════════════════════════════════════════════════════
#  Over HTTP
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def paid_api(api, monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("PADDLE_API_KEY", "pdl_test_key")
    config_module.settings.cache_clear()
    yield api
    config_module.settings.cache_clear()


def _post_webhook(api, payload: dict, *, signature: str | None = None):
    body = json.dumps(payload).encode()
    return api.post(
        "/v1/billing/webhook",
        content=body,
        headers={
            "Paddle-Signature": signature if signature is not None else _sign(body),
            "Content-Type": "application/json",
        },
    )


def test_the_catalogue_is_public(api, auth_headers):
    body = api.get("/v1/billing/catalogue", headers=auth_headers).json()
    assert body["currency"] == "USD"
    # Пять дверей, пара, бандл и план — вся полка, план в том числе, потому что
    # план, нарисованный вне списка, — это план, который клиент отрисует
    # разовым платежом.
    shelf = [key for key, item in prices.PRODUCTS.items() if item.on_the_shelf]
    assert [item["slug"] for item in body["items"]] == shelf
    assert {item["slug"] for item in body["items"]} == {
        "door.natal", "door.numerology", "door.birth-card",
        "door.astrocartography", "door.synthesis",
        "pair.check", "bundle.static", "sub.monthly",
    }
    plan = next(item for item in body["items"] if item["slug"] == "sub.monthly")
    assert plan["display"] == "$9.99"


def test_a_product_that_is_not_on_the_shelf_cannot_be_bought_by_naming_it(api, auth_headers):
    """Чекаут принимает имя товара от клиента, а клиент — не та сторона, которой
    мы верим.

    Условных цен в v3 нет, поэтому пример — ключи снятой полки и слаг системы
    вместо ключа каталога: ровно то, что придёт от пересобранного клиента или
    от старой сборки. Дыра, ради которой проверка написана, была настоящей:
    `archive-bump` за $29.99 выдавал то же, что архив за $38.99.
    """
    for product in ("archive", "archive-upgrade", "natal", "door.transits"):
        response = api.post(
            "/v1/billing/checkout", json={"product": product}, headers=auth_headers
        )
        assert response.status_code == 404, product
        detail = response.json()["detail"]
        # 404 приходит двумя путями: «такого товара нет вовсе» отвечает строкой,
        # «такой есть, но не на полке» — телом с кодом. Оба — отказ.
        if isinstance(detail, dict):
            assert detail["error"] == "not_offered"


def test_the_catalogue_is_localised(api, auth_headers):
    body = api.get(
        "/v1/billing/catalogue", params={"country": "BR"}, headers=auth_headers
    ).json()
    assert body["currency"] == "BRL"


def test_an_unsigned_webhook_is_refused(paid_api):
    response = _post_webhook(paid_api, _event(), signature="")
    assert response.status_code == 401


def test_a_forged_webhook_is_refused(paid_api):
    body = json.dumps(_event()).encode()
    response = paid_api.post(
        "/v1/billing/webhook",
        content=body,
        headers={"Paddle-Signature": _sign(body, secret="not-the-secret")},
    )
    assert response.status_code == 401


def test_a_valid_webhook_unlocks_the_system(paid_api, auth_headers):
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]

    before = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert "natal" not in before["unlocked"]

    response = _post_webhook(paid_api, _event(user_id=user_id, product="door.natal"))
    assert response.status_code == 200
    assert response.json()["status"] == "granted natal"

    after = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert "natal" in after["unlocked"]


def test_a_retried_webhook_does_nothing_the_second_time(paid_api, auth_headers):
    """Providers retry. A duplicate grant is our bug, not theirs."""
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]

    first = _post_webhook(paid_api, _event(user_id=user_id, event_id="evt_same"))
    second = _post_webhook(paid_api, _event(user_id=user_id, event_id="evt_same"))

    assert first.json()["status"] == "granted natal"
    assert second.json()["status"] == "already processed"

    held = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert len(held["entitlements"]) == 1, "the retry granted a second entitlement"


def test_an_annual_purchase_unlocks_everything(paid_api, auth_headers):
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    _post_webhook(paid_api, _event(user_id=user_id, product="sub.monthly", total="7899"))

    unlocked = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()["unlocked"]
    assert len(unlocked) == 8


def test_a_purchase_actually_opens_the_reading(paid_api, auth_headers):
    """The end-to-end claim: money in, chapter out."""
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]

    locked = paid_api.get("/v1/readings/natal/chapters", headers=auth_headers).json()
    assert sum(1 for c in locked["chapters"] if c["open"]) == 1

    _post_webhook(paid_api, _event(user_id=user_id, product="door.natal"))

    opened = paid_api.get("/v1/readings/natal/chapters", headers=auth_headers).json()
    assert all(c["open"] for c in opened["chapters"])


def test_a_refund_closes_it_again(paid_api, auth_headers):
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    _post_webhook(paid_api, _event(user_id=user_id, event_id="evt_buy"))
    assert "natal" in paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()["unlocked"]

    _post_webhook(
        paid_api, _event("transaction.refunded", user_id=user_id, event_id="evt_refund")
    )
    after = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert "natal" not in after["unlocked"]


def test_a_month_bought_is_a_month_and_not_a_permanent_grant(paid_api, auth_headers):
    """$9.99 once, everything forever — reproduced end to end.

    `entitlement_for` had a branch for "annual" and nothing for the monthly,
    so the payment fell through to a permanent one-time grant of `system="*"`.
    Nothing reported it: the row simply kept working.

    В v3 подписка честно открывает всё (`scope="all"`), поэтому проверяется не
    ширина, а **срок**: он и есть единственное, что отличает подписку от
    бандла, и именно его отсутствие стоило бы нам всей регулярной выручки.
    """
    from alma.calc import SYSTEMS

    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    _post_webhook(
        paid_api, _event(user_id=user_id, product="sub.monthly", total="999")
    )

    body = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert set(body["unlocked"]) == set(SYSTEMS)

    row = body["entitlements"][0]
    assert row["kind"] == "monthly"
    assert row["scope"] == "all"
    assert row["expires_at"] is not None, "a subscription with no expiry never renews"
    assert row["active"] is True


def _subscription_event(
    event_type: str,
    *,
    event_id: str,
    user_id: str | None = None,
    subscription_id: str = "sub_1",
    product: str = "sub.monthly",
    transaction_id: str | None = None,
) -> dict:
    """A subscription-lifecycle event: the plan's id in `data.id`, no payment."""
    data: dict = {
        "id": subscription_id,
        "status": "active" if "activated" in event_type else "canceled",
        "currency_code": "USD",
    }
    if user_id:
        data["custom_data"] = stamp(user_id, product)
    if transaction_id:
        data["transaction_id"] = transaction_id
    return {"event_id": event_id, "event_type": event_type, "data": data}


def test_a_renewal_extends_one_row_rather_than_writing_another(paid_api, auth_headers):
    """Every renewal is a new charge with a new transaction id.

    Keyed on that, a subscription wrote a row a month — and a cancellation
    then caught only the row belonging to the charge it named, leaving the
    earlier ones with future expiry dates, still granting what had just been
    cancelled.
    """
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    for index in range(3):
        _post_webhook(
            paid_api,
            _subscription_event(
                "subscription.activated", event_id=f"evt_{index}", user_id=user_id
            ),
        )

    held = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert len(held["entitlements"]) == 1


def test_a_cancellation_stops_the_charge_and_leaves_the_period_alone(paid_api, auth_headers):
    """This test used to assert the opposite, and the opposite was a refund.

    `subscription.canceled` was in `REVOKING`, so access ended the instant
    somebody cancelled — a month charged and three days delivered. Two shipped
    surfaces promise otherwise (`/subscription/cancel` and the
    subscription-terms page: "the plan then runs to the end of the month you
    have already paid for, and stops"), and Paddle emits this event *in reply
    to our own cancel call*, so pressing the button promised a date and then
    revoked before the page finished reloading.

    What a cancellation changes is the promise to charge. `renews_at` goes,
    `expires_at` does not, and the plan lapses on its own.
    """
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    _post_webhook(
        paid_api,
        _subscription_event("subscription.activated", event_id="evt_on", user_id=user_id),
    )
    assert paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()["unlocked"]

    response = _post_webhook(
        paid_api, _subscription_event("subscription.canceled", event_id="evt_off")
    )
    assert response.json()["status"] == "noted 1"

    after = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert after["unlocked"], "cancelling took away a period that had been paid for"
    row = after["entitlements"][0]
    assert row["active"] is True
    assert row["renews_at"] is None, "the account screen would still promise a charge"
    assert row["expires_at"] is not None


def test_a_subscription_event_is_not_recorded_as_a_payment(paid_api, auth_headers):
    """`data.id` on one of these is a subscription, not a transaction.

    Writing it to the money trail produced a zero-amount purchase whose
    transaction id had never identified a payment.
    """

    from sqlalchemy import select

    from alma.db.models import Purchase
    from alma.db.session import session_factory

    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    _post_webhook(
        paid_api,
        _subscription_event("subscription.activated", event_id="evt_on", user_id=user_id),
    )

    async def read():
        async with session_factory()() as session:
            return (await session.execute(select(Purchase))).scalars().all()

    assert read_async(read) == []


def test_a_subscriber_is_told_their_subscription_is_active(paid_api, auth_headers):
    """It said `false`. The field asked `covers(system)` with system == "*".

    That is a coverage probe using the row's own column as a slug, and "*" is
    not a living system — so the one screen a person opens when they are
    already wondering whether to cancel told them it was not working.
    """
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    _post_webhook(paid_api, _event(user_id=user_id, product="sub.monthly", total="999"))

    body = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert [row["active"] for row in body["entitlements"]] == [True]


def _adjustment(
    *, transaction_id: str = "txn_1", action: str = "refund",
    kind: str = "full", total: str = "899", event_id: str = "evt_adj",
) -> dict:
    """An adjustment payload, shaped the way Paddle actually sends one.

    Its own id in `data.id`, the transaction it reduces in
    `data.transaction_id`, and no `custom_data` anywhere.
    """
    return {
        "event_id": event_id,
        "event_type": "adjustment.created",
        "data": {
            "id": "adj_1",
            "transaction_id": transaction_id,
            "action": action,
            "type": kind,
            "currency_code": "USD",
            "details": {"totals": {"grand_total": total}},
        },
    }


def test_a_refund_arriving_as_an_adjustment_closes_what_it_paid_for(paid_api, auth_headers):
    """It closed nothing. Two things compounded.

    `transaction_id` preferred `data.id`, which on an adjustment is the
    adjustment's own id, so the purchase being reduced was never found; and
    with no `custom_data` the handler returned "recorded without an owner"
    before it reached the revocation at all. The money went back and the goods
    stayed.
    """
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    _post_webhook(paid_api, _event(user_id=user_id, event_id="evt_buy"))
    assert "natal" in paid_api.get(
        "/v1/billing/entitlements", headers=auth_headers
    ).json()["unlocked"]

    response = _post_webhook(paid_api, _adjustment())
    assert response.status_code == 200
    assert response.json()["status"] == "revoked 1"

    after = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert "natal" not in after["unlocked"]


def test_a_partial_refund_reduces_the_charge_and_takes_nothing_away(paid_api, auth_headers):
    """Five dollars back on a reading they have read is not a repossession.

    The code ignored `action` and `type` entirely, so it could not tell a
    partial refund from a full one or a credit from a chargeback.
    """
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    _post_webhook(paid_api, _event(user_id=user_id, event_id="evt_buy", total="1999",
                                   product="bundle.static"))
    _post_webhook(paid_api, _adjustment(kind="partial", total="500"))

    after = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert len(after["unlocked"]) == 5, "a partial refund closed the bundle"


def test_a_refund_is_not_stored_as_a_second_purchase(paid_api, auth_headers):
    """A refund written as its own row is a positive amount in the money trail.

    Every revenue sum over the table then counts it as revenue, while the
    purchase it reduces still reads as collected in full.
    """

    from sqlalchemy import select

    from alma.db.models import Purchase
    from alma.db.session import session_factory

    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    _post_webhook(paid_api, _event(user_id=user_id, event_id="evt_buy", total="3899",
                                   product="bundle.static"))
    _post_webhook(paid_api, _adjustment(kind="partial", total="500"))

    async def read():
        async with session_factory()() as session:
            return (await session.execute(select(Purchase))).scalars().all()

    rows = read_async(read)
    assert len(rows) == 1
    assert rows[0].amount_cents == 3899
    assert rows[0].refunded_cents == 500
    assert rows[0].refunded_at is None, "a partial refund is not a closed sale"


def test_a_credit_adjustment_is_neither_a_refund_nor_a_revocation(paid_api, auth_headers):
    """A `credit` reduces a future subscription invoice.

    Nothing comes back on the transaction, so it must not count against the
    refund column and must not close what the transaction bought.
    """

    from sqlalchemy import select

    from alma.db.models import Purchase
    from alma.db.session import session_factory

    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    _post_webhook(paid_api, _event(user_id=user_id, event_id="evt_buy"))
    _post_webhook(paid_api, _adjustment(action="credit", kind="full"))

    after = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert "natal" in after["unlocked"]

    async def read():
        async with session_factory()() as session:
            return (await session.execute(select(Purchase))).scalars().one()

    row = read_async(read)
    assert row.refunded_cents == 0
    assert row.refunded_at is None
    assert "credit" in row.status


def test_a_payment_with_no_owner_is_kept_not_dropped(paid_api):
    """Losing the record would lose the money."""
    response = _post_webhook(paid_api, _event(user_id=None, event_id="evt_orphan"))
    assert response.status_code == 200
    assert "without an owner" in response.json()["status"]


def test_an_event_with_no_id_is_refused(paid_api):
    payload = _event()
    del payload["event_id"]
    assert _post_webhook(paid_api, payload).status_code == 400


# ── checkout and the downsell ──────────────────────────────────────────────

def test_the_checkout_no_longer_demands_an_account(paid_api, auth_headers):
    """This test used to assert the opposite, and the opposite was the bug.

    Requiring a signed-in account put a registration form between deciding to
    pay and paying. Kept as a named test rather than deleted, so that anyone
    reinstating the wall has to come here and argue with it.
    """
    response = paid_api.post(
        "/v1/billing/checkout", json={"product": "door.natal"}, headers=auth_headers
    )
    assert response.status_code != 401


def test_a_checkout_carries_the_owner_in_custom_data(paid_api, auth_headers):
    link = paid_api.post(
        "/v1/auth/magic-link", json={"email": "sofia@example.com"}, headers=auth_headers
    ).json()["debug_token"]
    session = paid_api.post(
        "/v1/auth/magic-link/consume", json={"token": link}, headers=auth_headers
    ).json()
    signed_in = {"Authorization": f"Bearer {session['token']}"}

    body = paid_api.post(
        "/v1/billing/checkout", json={"product": "door.natal"}, headers=signed_in
    ).json()
    assert body["custom_data"]["user_id"] == session["user_id"]
    assert body["custom_data"]["product"] == "door.natal"
    assert body["cents"] == 499


def test_the_downsell_is_offered_exactly_once(api, auth_headers):
    """A second nudge turns someone still thinking into someone who declined."""
    first = api.post("/v1/billing/declined", headers=auth_headers).json()
    second = api.post("/v1/billing/declined", headers=auth_headers).json()
    third = api.post("/v1/billing/declined", headers=auth_headers).json()

    assert first["offer"] is not None
    assert second["offer"] is None
    assert third["offer"] is None
    assert "already offered" in second["reason"]


def test_the_downsell_offers_the_door_that_was_declined(api, auth_headers):
    """The doors are one price now, so "the cheapest" is not an answer.

    `min(PRODUCTS, key=cents)` resolved to whichever door came first in the
    dict literal, so a person who declined a numerology reading was offered a
    natal chart at the price they had just refused — the one downsell this
    product allows, spent on a stranger's product by an accident of insertion
    order.

    Совместимость сюда больше не годится примером: двери у неё нет, а
    `pair.check` исключён из даунселла намеренно — предложить проверку пары
    можно только тому, у кого партнёр есть, а здесь это неизвестно.
    """
    offer = api.post(
        "/v1/billing/declined", json={"system": "numerology"}, headers=auth_headers
    ).json()["offer"]
    assert offer["slug"] == "door.numerology"
    assert offer["system"] == "numerology"
    assert offer["cents"] == prices.PRODUCTS["door.numerology"].cents


def test_the_downsell_never_offers_a_pair_check(api, auth_headers):
    """Единственный оффер, который человек получит, нельзя тратить на товар,
    который он не может принять: проверка пары требует партнёра, а здесь не
    известно, есть ли он вообще."""
    offer = api.post(
        "/v1/billing/declined", json={"system": "transits"}, headers=auth_headers
    ).json()["offer"]
    assert offer["slug"] != "pair.check"


def test_the_downsell_is_priced_in_the_currency_the_person_would_pay_in(api, auth_headers):
    """It read `item.cents` and `display()`, which are the US figures.

    A German declining was quoted $8.99 for a door that costs €9.49.
    """
    offer = api.post(
        "/v1/billing/declined",
        json={"system": "natal", "country": "DE"},
        headers=auth_headers,
    ).json()["offer"]
    assert offer["currency"] == "EUR"
    assert offer["cents"] == prices.PRODUCTS["door.natal"].cents_in("EUR")
    assert offer["display"].startswith("€")


def test_a_downsell_is_priced_in_the_market_it_is_offered_in(api, auth_headers):
    """Бразилия теперь получает всю полку (`PRODUCTS.md` §5), поэтому прежний
    случай «на этом рынке двери нет вовсе» исчез. Правило, ради которого тест
    написан, не изменилось: предлагать можно только то, что на этом рынке
    продаётся, и по цене этого рынка — иначе человек уходит в чекаут, который
    отвечает `NotSold`, и сжигает единственный оффер, который у него был.
    """
    body = api.post(
        "/v1/billing/declined",
        json={"system": "natal", "country": "BR"},
        headers=auth_headers,
    ).json()
    assert body["offer"]["slug"] == "door.natal"
    assert body["offer"]["currency"] == "BRL"
    assert body["offer"]["cents"] == prices.PRODUCTS["door.natal"].cents_in("BRL")


def test_a_product_not_sold_here_is_refused_rather_than_crashing(paid_api, auth_headers, monkeypatch):
    """The pricing lines used to sit outside the try, so this was a 500.

    Прежде отсутствующий товар брался с бразильского рынка: PPP-рынки не
    получали дверь. В v3 полка продаётся во всех тринадцати валютах, а страна,
    которой мы цену не назначали, платит в долларах, — так что состояние «здесь
    это не продаётся» через страну больше не воспроизвести. Оно всё равно
    достижимо и всё равно обязано быть 404, а не 500: полосу из валюты убирают
    здесь руками, ровно как это сделает первая же правка `REGIONAL_CENTS`.
    """
    from alma.billing import catalogue as _prices

    monkeypatch.setitem(
        _prices.REGIONAL_CENTS, "EUR",
        {k: v for k, v in _prices.REGIONAL_CENTS["EUR"].items() if k != "door"},
    )
    response = paid_api.post(
        "/v1/billing/checkout", json={"product": "door.natal", "country": "DE"}, headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "not_sold_here"
    assert response.json()["detail"]["currency"] == "EUR"


def test_billing_says_so_when_it_is_not_configured(api, auth_headers):
    """No keys must mean a clear 503, not a broken checkout."""
    link = api.post(
        "/v1/auth/magic-link", json={"email": "a@example.com"}, headers=auth_headers
    ).json()["debug_token"]
    session = api.post(
        "/v1/auth/magic-link/consume", json={"token": link}, headers=auth_headers
    ).json()
    signed_in = {"Authorization": f"Bearer {session['token']}"}

    response = api.post("/v1/billing/checkout", json={"product": "door.natal"}, headers=signed_in)
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "billing_unavailable"


# ── prices have to look like prices ────────────────────────────────────────

def test_every_price_looks_like_a_price_somebody_set():
    """R$38.97 is a currency conversion; R$99,90 is a decision.

    Nothing is converted at request time any more, so this checks the table
    itself: every published amount ends on a figure a shop would print.
    """
    familiar = ("0", "9")
    for currency, table in prices.REGIONAL_CENTS.items():
        for band, cents in table.items():
            assert str(cents)[-1] in familiar, f"{currency} {band} at {cents} is a conversion"


def test_prices_are_written_the_way_each_locale_writes_them():
    """A Brazilian shown a full stop is being shown something that is not a price."""
    assert prices.format_price(1499, "USD") == "$14.99"
    assert prices.format_price(1499, "EUR") == "€14,99"
    assert prices.format_price(3990, "BRL") == "R$ 39,90"
    assert prices.format_price(5900, "USD") == "$59"
    assert prices.format_price(149_90, "BRL") == "R$ 149,90"


def test_large_prices_group_their_thousands():
    assert prices.format_price(1_234_500, "USD") == "$12,345"
    assert prices.format_price(1_234_500, "EUR") == "€12.345"


def test_the_ordering_of_prices_survives_the_currency():
    """A ladder that reorders in one market is a ladder with a cheaper top step."""
    ordered = sorted(prices.PRODUCTS.values(), key=lambda item: item.cents)
    for currency in ("USD", *prices.REGIONAL_CENTS):
        local = [item.cents_in(currency) for item in ordered if item.sold_in(currency)]
        assert local == sorted(local), f"{currency} reordered the catalogue"


# ── the chapter tier, withdrawn ────────────────────────────────────────────

def test_a_single_chapter_is_no_longer_on_sale():
    """Kept as a named test rather than deleted, so that reinstating the tier
    means arguing with this comment first.

    A chapter at $4.99 sold the cheapest thing we make against the same
    checkout as the door, and every buyer who took it was a buyer who did not
    take the $8.99 system. The door is now one price for a whole system, and
    the ladder above it is the archive.
    """
    with pytest.raises(ValueError, match="nothing on sale"):
        prices.product("chapter")


def test_a_payment_naming_the_withdrawn_tier_grants_nothing(paid_api, auth_headers):
    """A checkout opened before the change must not unlock anything after it.

    The money is still recorded — support can honour it by hand — but a slug
    we no longer sell cannot be turned into an entitlement by guesswork.
    """
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]

    payload = _event(user_id=user_id, product="chapter", total="499")
    payload["data"]["custom_data"]["system"] = "natal"
    payload["data"]["custom_data"]["chapter"] = "career"
    assert _post_webhook(paid_api, payload).json()["status"] == "ignored"

    chapters = paid_api.get("/v1/readings/natal/chapters", headers=auth_headers).json()
    assert not any(c["slug"] == "career" and c["open"] for c in chapters["chapters"])


# ── the funnel: a guest may pay ────────────────────────────────────────────

def test_a_guest_can_reach_the_checkout(paid_api, auth_headers):
    """The most expensive wall in the funnel, removed deliberately.

    Someone arriving from a link has decided to spend five dollars, not to
    fill in a registration form. A guest is already an account row with an id,
    so the payment has something real to attach to — signing in afterwards
    buys durability, not permission.
    """
    response = paid_api.post(
        "/v1/billing/checkout", json={"product": "door.natal"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["custom_data"]["user_id"], "the payment has nobody to attach to"
    assert body["cents"] == 499


def test_a_guest_purchase_unlocks_for_that_guest(paid_api, auth_headers):
    """End to end, without an email address anywhere in the story."""
    session = paid_api.get("/v1/auth/session", headers=auth_headers).json()
    assert session["is_guest"] is True

    _post_webhook(paid_api, _event(user_id=session["user_id"], product="door.natal"))

    held = paid_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert "natal" in held["unlocked"]


def test_what_a_guest_bought_survives_signing_in(paid_api, auth_headers):
    """The purchase must follow the person into their account.

    This is the whole reason a guest is a real row rather than a cookie: the
    merge moves entitlements across, so buying first and registering second
    cannot lose what was paid for.
    """
    session = paid_api.get("/v1/auth/session", headers=auth_headers).json()
    _post_webhook(paid_api, _event(user_id=session["user_id"], product="door.natal"))

    link = paid_api.post(
        "/v1/auth/magic-link", json={"email": "buyer@example.com"}, headers=auth_headers
    ).json()["debug_token"]
    signed_in = paid_api.post(
        "/v1/auth/magic-link/consume", json={"token": link}, headers=auth_headers
    ).json()
    assert signed_in["is_guest"] is False

    after = paid_api.get(
        "/v1/billing/entitlements",
        headers={"Authorization": f"Bearer {signed_in['token']}"},
    ).json()
    assert "natal" in after["unlocked"], "the purchase did not survive registration"
