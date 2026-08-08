"""Attacking the webhook and the checkout as somebody who wants a free archive.

Every test here is an attempt, not a description. The ones that pass are the
attack being refused; the ones that fail are the attack working, and each of
those names the rule it broke in its docstring rather than the line of code it
happened to hit.

The rule underneath all of it is the one written at the top of the router and
in `src/lib/checkout.ts`: **entitlements are granted by the signed webhook,
server-side, never by anything the browser decided.** A signature makes a
statement trustworthy; it does not make it *ours*. A field that reached the
processor from our own browser and came back inside a signed envelope is still
a field the browser chose, and the signature only proves the processor faithfully
echoed it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from conftest import read_async

from alma.billing.provider import SEAL_FIELD, stamp

SECRET = "pdl_ntfset_test_secret"


def _sign(body: bytes, *, secret: str = SECRET, at: int | None = None) -> str:
    when = int(time.time()) if at is None else at
    digest = hmac.new(secret.encode(), f"{when}:".encode() + body, hashlib.sha256).hexdigest()
    return f"ts={when};h1={digest}"


@pytest.fixture
def paid_api(api, monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("PADDLE_API_KEY", "pdl_test_key")
    monkeypatch.setenv("PADDLE_CLIENT_TOKEN", "live_token")
    config_module.settings.cache_clear()
    yield api
    config_module.settings.cache_clear()


def _deliver(api, payload: dict, *, headers: dict | None = None, secret: str = SECRET,
             at: int | None = None):
    body = json.dumps(payload).encode()
    return api.post(
        "/v1/billing/webhook",
        content=body,
        headers=headers if headers is not None else {"Paddle-Signature": _sign(body, secret=secret, at=at)},
    )


def _purchase(*, event_id: str, user_id: str, product: str, cents: str = "899",
              transaction_id: str | None = None, event_type: str = "transaction.completed",
              subscription_id: str | None = None, sealed: bool = True) -> dict:
    """One completed charge.

    `sealed=False` is the payer writing the metadata themselves — which they can
    do, because `Paddle.Checkout.open` takes `customData` as an argument and the
    client token that opens an overlay is published to every browser. It is the
    difference between a purchase and a claim, and several tests below turn it
    off on purpose.
    """
    data: dict = {
        "id": transaction_id or f"txn_{event_id}",
        "currency_code": "USD",
        "custom_data": (
            stamp(user_id, product)
            if sealed
            else {"user_id": user_id, "product": product}
        ),
        "details": {"totals": {"grand_total": cents}},
    }
    if subscription_id:
        data["subscription_id"] = subscription_id
    return {"event_id": event_id, "event_type": event_type, "data": data}


def _who(api, headers) -> str:
    return api.get("/v1/auth/session", headers=headers).json()["user_id"]


def _held(api, headers) -> dict:
    return api.get("/v1/billing/entitlements", headers=headers).json()


# ══════════════════════════════════════════════════════════════════════════
#  Forgery, tampering, replay
# ══════════════════════════════════════════════════════════════════════════


def test_a_signature_from_the_wrong_secret_buys_nothing(paid_api, auth_headers):
    """The whole endpoint, if this fails: anyone who can POST gets an archive."""
    me = _who(paid_api, auth_headers)
    answer = _deliver(
        paid_api,
        _purchase(event_id="evt_forged", user_id=me, product="archive"),
        secret="not-the-secret",
    )
    assert answer.status_code == 401
    assert _held(paid_api, auth_headers)["unlocked"] == []


def test_an_unsigned_delivery_buys_nothing(paid_api, auth_headers):
    me = _who(paid_api, auth_headers)
    answer = _deliver(
        paid_api, _purchase(event_id="evt_bare", user_id=me, product="archive"), headers={}
    )
    assert answer.status_code == 401
    assert _held(paid_api, auth_headers)["unlocked"] == []


def test_a_body_edited_after_signing_buys_nothing(paid_api, auth_headers):
    """Capture a real delivery, upgrade the product in it, keep the signature.

    The signed message is the raw body, so every field in the payload — the
    product, the amount, the owner, the event id — is covered. If any of them
    were outside it, the cheapest purchase in the catalogue would be a template
    for the most expensive one.
    """
    me = _who(paid_api, auth_headers)
    honest = _purchase(event_id="evt_edit", user_id=me, product="natal")
    signature = _sign(json.dumps(honest).encode())

    greedy = json.loads(json.dumps(honest))
    greedy["data"]["custom_data"]["product"] = "archive"
    answer = paid_api.post(
        "/v1/billing/webhook",
        content=json.dumps(greedy).encode(),
        headers={"Paddle-Signature": signature},
    )
    assert answer.status_code == 401
    assert _held(paid_api, auth_headers)["unlocked"] == []


def test_a_captured_delivery_replayed_grants_once(paid_api, auth_headers):
    """At-least-once delivery is the processor's promise; once is ours."""
    me = _who(paid_api, auth_headers)
    payload = _purchase(event_id="evt_replay", user_id=me, product="natal")
    body = json.dumps(payload).encode()
    signature = _sign(body)

    first = paid_api.post("/v1/billing/webhook", content=body, headers={"Paddle-Signature": signature})
    assert first.status_code == 200
    second = paid_api.post("/v1/billing/webhook", content=body, headers={"Paddle-Signature": signature})
    assert second.status_code == 200
    assert second.json()["status"] == "already processed"
    assert len(_held(paid_api, auth_headers)["entitlements"]) == 1


def test_a_delivery_replayed_tomorrow_is_refused(paid_api, auth_headers):
    """A valid signature lifted from a proxy log is still a replay."""
    me = _who(paid_api, auth_headers)
    payload = _purchase(event_id="evt_stale", user_id=me, product="archive")
    answer = _deliver(paid_api, payload, at=int(time.time()) - 86_400)
    assert answer.status_code == 401
    assert "replay" in answer.json()["detail"]
    assert _held(paid_api, auth_headers)["unlocked"] == []


def test_the_same_purchase_under_a_fresh_event_id_is_refused(paid_api, auth_headers):
    """Reusing a delivery under a new idempotency key.

    The id is inside the signed body, so re-keying it invalidates the
    signature. That is what stops one valid purchase being spent repeatedly by
    incrementing the one field the duplicate check reads.
    """
    me = _who(paid_api, auth_headers)
    payload = _purchase(event_id="evt_once", user_id=me, product="natal")
    body = json.dumps(payload).encode()
    signature = _sign(body)
    assert paid_api.post(
        "/v1/billing/webhook", content=body, headers={"Paddle-Signature": signature}
    ).status_code == 200

    payload["event_id"] = "evt_once_again"
    again = paid_api.post(
        "/v1/billing/webhook",
        content=json.dumps(payload).encode(),
        headers={"Paddle-Signature": signature},
    )
    assert again.status_code == 401
    assert len(_held(paid_api, auth_headers)["entitlements"]) == 1


# ══════════════════════════════════════════════════════════════════════════
#  What the browser chose, coming back inside a signature
# ══════════════════════════════════════════════════════════════════════════


def test_the_checkout_hands_the_browser_metadata_it_cannot_rewrite(paid_api, auth_headers):
    """Not an attack — the precondition for everything below, stated once.

    `custom_data` is returned to the client and `src/lib/checkout.ts` passes it
    straight into `Paddle.Checkout.open({customData})`. Paddle echoes whatever
    it was given onto the webhook and signs *that*, so the signature proves the
    processor relayed the field faithfully and proves nothing about who wrote
    it. The two readable fields are still there, because a payment in a
    dashboard that says only `alma_seal: 4f2b…` is a payment support cannot
    attribute — and beside them is the seal that makes them ours.
    """
    opened = paid_api.post(
        "/v1/billing/checkout", json={"product": "natal"}, headers=auth_headers
    )
    assert opened.status_code == 200
    body = opened.json()
    assert body["custom_data"]["product"] == "natal"
    assert body["custom_data"][SEAL_FIELD], "the browser was handed metadata it could rewrite"
    assert body["cents"] == 599


def test_a_door_cannot_be_relabelled_as_the_archive(paid_api, auth_headers):
    """What is granted must be what the money paid for.

    A buyer opens a checkout for one $8.99 door, edits `customData.product` to
    `archive` in the console before the overlay opens, and pays $8.99. Paddle
    charges the door's price id and signs a webhook carrying the browser's word
    for what was bought — so the account was given the whole $38.99 archive,
    permanently, for $8.99.

    Two independent things now refuse it, and both are needed: the metadata
    carries no seal we wrote, and the amount on the same event does not cover
    the archive.
    """
    me = _who(paid_api, auth_headers)
    answer = _deliver(
        paid_api,
        _purchase(event_id="evt_relabel", user_id=me, product="archive",
                  cents="899", sealed=False),
    )
    assert answer.status_code == 200

    held = _held(paid_api, auth_headers)
    scopes = {row["scope"] for row in held["entitlements"]}
    assert "all" not in scopes, (
        "899 cents bought a scope=all grant: the product granted came from the "
        "browser's metadata, not from anything we wrote"
    )


def test_a_sealed_checkout_paid_at_another_price_grants_nothing(paid_api, auth_headers):
    """The half of the same attack the seal cannot see.

    The seal says which product *we* opened a checkout for. It says nothing
    about which price was charged, and on this processor the browser holds the
    price id as well: open an archive checkout honestly, swap the price id for
    the door's, and a genuine seal arrives on an 899 charge. The amount is on
    the same event, and comparing them is the only thing that catches this.
    """
    me = _who(paid_api, auth_headers)
    answer = _deliver(
        paid_api,
        _purchase(event_id="evt_underpaid", user_id=me, product="archive", cents="899"),
    )
    assert answer.status_code == 200
    assert "granted" not in answer.json()["status"]

    held = _held(paid_api, auth_headers)
    assert {row["scope"] for row in held["entitlements"]} == set(), (
        "a sealed archive checkout charged at the door's price granted the archive"
    )


def test_a_door_cannot_be_relabelled_as_a_year(paid_api, auth_headers):
    """The same hole, at its most profitable.

    `annual` is 7899 with `scope="all"` and a year's duration. Naming it in
    metadata on an 899 charge writes a year of the entire archive — and, because
    the catalogue gave it an interval, a `subscription_id`-keyed row that the
    cancel endpoint will happily report as a live plan.
    """
    me = _who(paid_api, auth_headers)
    answer = _deliver(
        paid_api,
        _purchase(
            event_id="evt_year",
            user_id=me,
            product="annual",
            cents="899",
            subscription_id="sub_free_year",
            sealed=False,
        ),
    )
    assert answer.status_code == 200

    held = _held(paid_api, auth_headers)
    kinds = {row["kind"] for row in held["entitlements"]}
    assert "annual" not in kinds, (
        "899 cents bought an annual grant — the kind and the scope were taken "
        "from a field the browser controls"
    )


def test_a_conditional_price_cannot_be_claimed_through_the_webhook(paid_api, auth_headers):
    """`may_be_offered` guards the checkout, and now that guard is the only door.

    `archive-bump` is the in-checkout second line item — 899 + 2999 is a cent
    under the shelf price — and `/billing/checkout` refuses it by name for
    exactly that reason. The webhook never asks, and while a grant could be read
    out of unsigned metadata that made the checkout's guard a guard on the one
    door that was already locked. It is load-bearing now: `/checkout` is the
    only thing that seals a product, and it asks `may_be_offered` first, so a
    product it refuses is a product that can never arrive sealed.
    """
    me = _who(paid_api, auth_headers)
    refused = paid_api.post(
        "/v1/billing/checkout", json={"product": "archive-bump"}, headers=auth_headers
    )
    assert refused.status_code == 404

    _deliver(
        paid_api,
        _purchase(event_id="evt_bump", user_id=me, product="archive-bump",
                  cents="2999", sealed=False),
    )
    held = _held(paid_api, auth_headers)
    scopes = {row["scope"] for row in held["entitlements"]}
    assert "all" not in scopes, (
        "a product the checkout refuses to sell was granted by the webhook"
    )


def test_a_payment_cannot_be_pointed_at_somebody_else(paid_api, api, auth_headers):
    """`custom_data.user_id` is chosen by the browser too.

    Same envelope, same signature, different owner. The person who pays decides
    which account is credited, which is the same defect as the ones above
    pointed sideways rather than upwards — and it is the shape that lets one
    purchase be resold.
    """
    victim = api.get("/v1/auth/session").json()
    stranger_headers = {"Authorization": f"Bearer {victim['token']}"}
    stranger = victim["user_id"]
    me = _who(paid_api, auth_headers)
    assert stranger != me

    _deliver(
        paid_api,
        _purchase(event_id="evt_sideways", user_id=stranger, product="natal", sealed=False),
    )
    assert _held(paid_api, stranger_headers)["unlocked"] == [], (
        "a grant landed on an account named only by the payer's browser"
    )


def test_a_payment_with_no_metadata_of_ours_is_kept_and_grants_nothing(paid_api, auth_headers):
    """The honest version of the same shape, and it must not be an error.

    A checkout opened from a support console, or by somebody using our public
    client token directly, arrives carrying nothing we set. Losing the record
    would lose the money, so it is written down and left for a person — the one
    thing it may not do is guess an owner.
    """
    me = _who(paid_api, auth_headers)
    answer = _deliver(
        paid_api,
        _purchase(event_id="evt_bare_meta", user_id=me, product="natal", sealed=False),
    )
    assert answer.status_code == 200
    assert "without an owner" in answer.json()["status"]
    assert _held(paid_api, auth_headers)["unlocked"] == []


# ══════════════════════════════════════════════════════════════════════════
#  One charge, several events
# ══════════════════════════════════════════════════════════════════════════


def test_one_month_of_money_extends_a_plan_by_one_month(paid_api, auth_headers):
    """Paddle emits `transaction.paid` and `transaction.completed` per charge.

    Both strings are in `GRANTING`, both carry the same `subscription_id`, and
    `entitlements.grant` extends the row by a whole period every time it is
    called against that id. So one renewal's money buys two periods, every
    month, with the expiry drifting further ahead of the payments and nothing
    reporting it. The Dodo adapter guards against exactly this shape in
    `Event._grants`; the Paddle one does not.
    """
    from datetime import datetime

    me = _who(paid_api, auth_headers)
    for index, kind in enumerate(("transaction.paid", "transaction.completed")):
        answer = _deliver(
            paid_api,
            _purchase(
                event_id=f"evt_double_{index}",
                user_id=me,
                product="monthly",
                cents="999",
                transaction_id="txn_one_charge",
                event_type=kind,
                subscription_id="sub_one_plan",
            ),
        )
        assert answer.status_code == 200

    rows = _held(paid_api, auth_headers)["entitlements"]
    assert len(rows) == 1
    expires = datetime.fromisoformat(rows[0]["expires_at"])
    days = (expires - datetime.now(expires.tzinfo)).days
    assert days < 40, (
        f"one month's money granted {days} days: two granting events for one "
        "charge each extended the subscription by a full period"
    )


# ══════════════════════════════════════════════════════════════════════════
#  The checkout endpoint
# ══════════════════════════════════════════════════════════════════════════


def test_a_product_that_is_not_on_the_shelf_is_refused(paid_api, auth_headers):
    for slug in ("everything", "../archive", "", "chapter"):
        answer = paid_api.post(
            "/v1/billing/checkout", json={"product": slug}, headers=auth_headers
        )
        assert answer.status_code == 404, slug


def test_the_upgrade_price_is_refused_to_somebody_who_owns_no_door(paid_api, auth_headers):
    """`archive-upgrade` is the shelf price less the door already paid for.

    Claimed without a door it is simply the archive for $30 — the credit half
    of the promise, taken without the purchase half.
    """
    answer = paid_api.post(
        "/v1/billing/checkout", json={"product": "archive-upgrade"}, headers=auth_headers
    )
    assert answer.status_code == 404
    assert answer.json()["detail"]["error"] == "not_offered"


# ══════════════════════════════════════════════════════════════════════════
#  Cancelling
# ══════════════════════════════════════════════════════════════════════════


def test_cancelling_cannot_be_aimed_at_a_subscription_you_do_not_own(paid_api, api, auth_headers, monkeypatch):
    """The endpoint takes no identifier, and a body naming one must not change that.

    An id parameter here would be an IDOR against a payment processor: a
    stranger's plan stopped from an account that never paid for it.
    """
    from alma.billing import paddle as paddle_module

    calls: list[str] = []

    async def _never_reaches_the_network(self, subscription_id: str) -> None:
        calls.append(subscription_id)

    monkeypatch.setattr(
        paddle_module.PaddleProvider, "cancel_subscription", _never_reaches_the_network
    )

    victim = api.get("/v1/auth/session").json()
    victim_headers = {"Authorization": f"Bearer {victim['token']}"}
    _deliver(
        paid_api,
        {
            "event_id": "evt_victim_plan",
            "event_type": "subscription.activated",
            "data": {
                "id": "sub_victims",
                "status": "active",
                "currency_code": "USD",
                "custom_data": stamp(victim["user_id"], "monthly"),
            },
        },
    )
    assert len(_held(paid_api, victim_headers)["entitlements"]) == 1

    answer = paid_api.post(
        "/v1/billing/subscription/cancel",
        json={"subscription_id": "sub_victims"},
        headers=auth_headers,
    )
    assert answer.status_code == 404
    assert calls == []
    still = _held(paid_api, victim_headers)["entitlements"][0]
    assert still["renews_at"] is None or still["active"] is True


# ══════════════════════════════════════════════════════════════════════════
#  The other processor, through the same route
# ══════════════════════════════════════════════════════════════════════════

DODO_SECRET = "whsec_" + base64.b64encode(b"dodo-signing-key").decode()


def _dodo_headers(webhook_id: str, body: bytes, *, secret: str = DODO_SECRET,
                  at: int | None = None) -> dict:
    when = str(int(time.time()) if at is None else at)
    key = base64.b64decode(secret[len("whsec_"):] + "==")
    digest = hmac.new(key, f"{webhook_id}.{when}.".encode() + body, hashlib.sha256).digest()
    return {
        "webhook-id": webhook_id,
        "webhook-timestamp": when,
        "webhook-signature": "v1," + base64.b64encode(digest).decode(),
    }


@pytest.fixture
def dodo_api(api, monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("ALMA_BILLING_PROVIDER", "dodo")
    monkeypatch.setenv("DODO_PAYMENTS_API_KEY", "dodo_test_key")
    monkeypatch.setenv("DODO_PAYMENTS_WEBHOOK_KEY", DODO_SECRET)
    config_module.settings.cache_clear()
    yield api
    config_module.settings.cache_clear()


def _dodo_payment(*, payment_id: str, user_id: str, product: str, cents: int = 899,
                  emitted: str = "2026-08-06T10:00:00Z", subscription_id: str | None = None,
                  event_type: str = "payment.succeeded") -> dict:
    data: dict = {
        "payload_type": "Payment",
        "payment_id": payment_id,
        "currency": "USD",
        "total_amount": cents,
        "metadata": stamp(user_id, product),
    }
    if subscription_id:
        data["subscription_id"] = subscription_id
    return {"business_id": "biz_1", "type": event_type, "timestamp": emitted, "data": data}


def _dodo_deliver(api, payload: dict, *, webhook_id: str, **kwargs):
    body = json.dumps(payload).encode()
    return api.post(
        "/v1/billing/webhook", content=body,
        headers=_dodo_headers(webhook_id, body, **kwargs),
    )


def test_a_dodo_delivery_signed_with_the_wrong_key_buys_nothing(dodo_api, auth_headers):
    me = _who(dodo_api, auth_headers)
    answer = _dodo_deliver(
        dodo_api,
        _dodo_payment(payment_id="pay_1", user_id=me, product="archive"),
        webhook_id="wh_forged",
        secret="whsec_" + base64.b64encode(b"not-the-key").decode(),
    )
    assert answer.status_code == 401
    assert _held(dodo_api, auth_headers)["unlocked"] == []


def test_a_dodo_webhook_id_swapped_after_signing_buys_nothing(dodo_api, auth_headers):
    """`webhook-id` is inside the signed message, and that is what stops a
    captured delivery being spent again under a fresh idempotency key."""
    me = _who(dodo_api, auth_headers)
    payload = _dodo_payment(payment_id="pay_2", user_id=me, product="natal")
    body = json.dumps(payload).encode()
    headers = _dodo_headers("wh_original", body)
    assert dodo_api.post("/v1/billing/webhook", content=body, headers=headers).status_code == 200

    headers["webhook-id"] = "wh_fresh"
    again = dodo_api.post("/v1/billing/webhook", content=body, headers=headers)
    assert again.status_code == 401


def test_a_dodo_renewal_is_granted_once_not_twice(dodo_api, auth_headers):
    """The pair Dodo emits for one renewal: the payment and the lifecycle event.

    Only the second may grant. This is the guard the Paddle adapter does not
    have — see `test_one_month_of_money_extends_a_plan_by_one_month`.
    """
    from datetime import datetime

    me = _who(dodo_api, auth_headers)
    _dodo_deliver(
        dodo_api,
        _dodo_payment(payment_id="pay_r1", user_id=me, product="monthly", cents=999,
                      subscription_id="sub_dodo"),
        webhook_id="wh_r1",
    )
    renewed = {
        "business_id": "biz_1", "type": "subscription.renewed",
        "timestamp": "2026-08-06T10:00:01Z",
        "data": {
            "payload_type": "Subscription", "subscription_id": "sub_dodo",
            "status": "active", "currency": "USD",
            "metadata": stamp(me, "monthly"),
        },
    }
    _dodo_deliver(dodo_api, renewed, webhook_id="wh_r2")

    rows = _held(dodo_api, auth_headers)["entitlements"]
    assert len(rows) == 1
    expires = datetime.fromisoformat(rows[0]["expires_at"])
    assert (expires - datetime.now(expires.tzinfo)).days < 40


def test_two_dodo_deliveries_of_one_event_grant_once(dodo_api, auth_headers):
    """A retry carries the same `webhook-id`, and the same body identity."""
    me = _who(dodo_api, auth_headers)
    payload = _dodo_payment(payment_id="pay_3", user_id=me, product="natal")
    _dodo_deliver(dodo_api, payload, webhook_id="wh_retry")
    second = _dodo_deliver(dodo_api, payload, webhook_id="wh_retry")
    assert second.json()["status"] == "already processed"
    assert len(_held(dodo_api, auth_headers)["entitlements"]) == 1


def test_the_dodo_idempotency_key_is_the_one_dodo_sent(dodo_api, auth_headers):
    """The router calls `adapter.parse(payload)` with no headers.

    Dodo puts no id in the body, so the delivery is recorded under a hash of
    `(type, emission timestamp, resource id)` instead of under `webhook-id`.
    Two genuinely distinct deliveries that share those three collapse into one
    — the second is answered "already processed" and never happens. Two refunds
    of the same payment inside one second is the shape that reaches it.
    """
    from sqlalchemy import select

    me = _who(dodo_api, auth_headers)
    payload = _dodo_payment(payment_id="pay_4", user_id=me, product="natal")
    _dodo_deliver(dodo_api, payload, webhook_id="wh_the_real_id")

    from alma.db.models import WebhookEvent
    from alma.db.session import session_scope

    async def _ids():
        async with session_scope() as session:
            return [row.id for row in (await session.execute(select(WebhookEvent))).scalars()]

    assert read_async(_ids) == ["wh_the_real_id"], (
        "the delivery was keyed on a hash of the body's identity rather than on "
        "the `webhook-id` header Dodo signed"
    )


def test_a_dodo_retry_of_one_event_cannot_grant_a_second_period(dodo_api, auth_headers):
    """The retry Dodo documents, arriving with a refreshed body.

    Dodo states that a retry carries "the latest payload at the time of
    delivery", and it carries the *same* `webhook-id` — which is precisely why
    that header is the idempotency key. The router never reads it: it hands
    `adapter.parse(payload)` no headers, so the delivery is filed under a hash
    of the body's identity instead. Any field of that identity moving between
    attempts makes the retry a new event, and a granting event granted twice is
    a period of access nobody paid for.
    """
    from datetime import datetime

    me = _who(dodo_api, auth_headers)
    first = {
        "business_id": "biz_1", "type": "subscription.renewed",
        "timestamp": "2026-08-06T10:00:00.100Z",
        "data": {
            "payload_type": "Subscription", "subscription_id": "sub_retry",
            "status": "active", "currency": "USD",
            "metadata": stamp(me, "monthly"),
        },
    }
    assert _dodo_deliver(dodo_api, first, webhook_id="wh_retried").status_code == 200

    # The same delivery, retried. Same signed id; one field of the body has
    # been refreshed by the sender between attempts.
    retried = json.loads(json.dumps(first))
    retried["timestamp"] = "2026-08-06T10:00:00.400Z"
    second = _dodo_deliver(dodo_api, retried, webhook_id="wh_retried")

    assert second.json()["status"] == "already processed", (
        "a retry under the same webhook-id was processed as a new event"
    )
    rows = _held(dodo_api, auth_headers)["entitlements"]
    expires = datetime.fromisoformat(rows[0]["expires_at"])
    assert (expires - datetime.now(expires.tzinfo)).days < 40


def test_nothing_the_browser_can_call_grants_anything(paid_api, auth_headers):
    """Every endpoint a client can reach, called as greedily as it allows.

    None of them may hand out access. The checkout opens a session, the
    downsell offers a price, and the entitlement list reads. If any of them
    ever writes a grant, the signature on the webhook stops being the thing
    that decides who has paid.
    """
    paid_api.post("/v1/billing/checkout", json={"product": "natal"}, headers=auth_headers)
    paid_api.post("/v1/billing/checkout", json={"product": "annual"}, headers=auth_headers)
    paid_api.post("/v1/billing/declined", json={"system": "natal"}, headers=auth_headers)
    paid_api.post("/v1/billing/declined", json={"system": "natal"}, headers=auth_headers)
    paid_api.get("/v1/billing/catalogue", headers=auth_headers)

    held = _held(paid_api, auth_headers)
    assert held["unlocked"] == []
    assert held["entitlements"] == []


# ══════════════════════════════════════════════════════════════════════════
#  Renewals, which must survive things that have nothing to do with billing
# ══════════════════════════════════════════════════════════════════════════


def test_a_renewal_extends_the_plan_even_when_the_seal_no_longer_verifies(
    paid_api, auth_headers, monkeypatch
):
    """Not an attack — the failure mode the seal introduces, closed on purpose.

    The seal is keyed on `ALMA_JWT_SECRET`, and processors echo our metadata
    onto every event for the life of a plan. So rotating that secret — a thing
    an operator does after an incident, without thinking about billing — would
    leave every live subscription renewing into nothing: charged and not
    extended, silently, until a subscriber who had paid noticed.

    A renewal is therefore matched by the subscription id the processor sent,
    and the plan it renews into is the plan we already hold.
    """
    from datetime import datetime

    me = _who(paid_api, auth_headers)
    assert _deliver(
        paid_api,
        {
            "event_id": "evt_plan_on",
            "event_type": "subscription.activated",
            "data": {
                "id": "sub_rotate",
                "status": "active",
                "currency_code": "USD",
                "custom_data": stamp(me, "monthly"),
            },
        },
    ).status_code == 200
    rows = _held(paid_api, auth_headers)["entitlements"]
    assert [row["kind"] for row in rows] == ["monthly"]
    first = datetime.fromisoformat(rows[0]["expires_at"])

    # The month's renewal, arriving with metadata sealed under the old secret.
    stale = _purchase(
        event_id="evt_renewal",
        user_id=me,
        product="monthly",
        cents="999",
        subscription_id="sub_rotate",
        sealed=False,
    )
    assert _deliver(paid_api, stale).json()["status"] == "granted *"

    rows = _held(paid_api, auth_headers)["entitlements"]
    assert len(rows) == 1
    assert datetime.fromisoformat(rows[0]["expires_at"]) > first


def test_a_renewal_we_hold_no_plan_for_grants_nothing(paid_api, api, auth_headers):
    """The rule above must not become a second way in.

    A charge naming a subscription nobody holds has no plan to renew, so there
    is nothing to extend and nothing to guess at.
    """
    me = _who(paid_api, auth_headers)
    answer = _deliver(
        paid_api,
        _purchase(
            event_id="evt_ghost_renewal",
            user_id=me,
            product="annual",
            cents="999",
            subscription_id="sub_nobody_holds",
            sealed=False,
        ),
    )
    assert "granted" not in answer.json()["status"]
    assert _held(paid_api, auth_headers)["unlocked"] == []


def test_a_renewal_charged_less_than_the_plan_costs_extends_nothing(paid_api, auth_headers):
    """The plan we hold names the product; the price check still applies to it."""
    from datetime import datetime

    me = _who(paid_api, auth_headers)
    _deliver(
        paid_api,
        {
            "event_id": "evt_year_on",
            "event_type": "subscription.activated",
            "data": {
                "id": "sub_year_cheap",
                "status": "active",
                "currency_code": "USD",
                "custom_data": stamp(me, "annual"),
            },
        },
    )
    before = datetime.fromisoformat(
        _held(paid_api, auth_headers)["entitlements"][0]["expires_at"]
    )

    _deliver(
        paid_api,
        _purchase(
            event_id="evt_year_cheap",
            user_id=me,
            product="annual",
            cents="100",
            subscription_id="sub_year_cheap",
            sealed=False,
        ),
    )
    after = datetime.fromisoformat(
        _held(paid_api, auth_headers)["entitlements"][0]["expires_at"]
    )
    assert after == before, "a dollar bought another year"
