"""The billing endpoints, and the configuration that decides who is behind them.

`test_billing.py` proves the Paddle path end to end. This file is about the two
things that are true whichever processor is running: that **which** processor is
running is a configuration decision the code refuses to guess at, and that the
endpoints above the seam never learn one processor's vocabulary.

The most expensive rule here is the one about cancelling. Cancelling is not
refunding: someone who cancels a year in month two has paid for ten more months
and keeps them. Every test below that touches `/subscription/cancel` is really
asking the same question — did anything take away access that had been paid
for — because that is the failure a customer discovers immediately and a
regulator discovers later.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from conftest import read_async

from alma.billing.provider import (
    BillingUnavailable,
    EventKind,
    InvalidSignature,
    NormalisedEvent,
    SessionHandle,
    header_value,
    provider_for,
    stamp,
)

SECRET = "pdl_ntfset_test_secret"


def _sign(body: bytes, *, secret: str = SECRET) -> str:
    at = int(time.time())
    digest = hmac.new(secret.encode(), f"{at}:".encode() + body, hashlib.sha256).hexdigest()
    return f"ts={at};h1={digest}"


@pytest.fixture
def paid_api(api, monkeypatch):
    """The app with a processor configured, and the settings cache cleared."""
    from alma import config as config_module

    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("PADDLE_API_KEY", "pdl_test_key")
    config_module.settings.cache_clear()
    yield api
    config_module.settings.cache_clear()


def _post_webhook(api, payload: dict, *, headers: dict | None = None):
    body = json.dumps(payload).encode()
    return api.post(
        "/v1/billing/webhook",
        content=body,
        headers=headers or {"Paddle-Signature": _sign(body)},
    )


def _subscription_event(
    event_type: str,
    *,
    event_id: str,
    subscription_id: str,
    user_id: str | None = None,
    product: str = "sub.monthly",
    next_billed_at: str | None = None,
) -> dict:
    """A subscription-lifecycle event: the plan's id in `data.id`, no payment."""
    data: dict = {
        "id": subscription_id,
        "status": "active" if "activated" in event_type else "canceled",
        "currency_code": "USD",
    }
    if user_id:
        data["custom_data"] = stamp(user_id, product)
    if next_billed_at:
        data["next_billed_at"] = next_billed_at
    return {"event_id": event_id, "event_type": event_type, "data": data}


def _purchase_event(*, event_id: str, user_id: str, product: str = "door.natal") -> dict:
    return {
        "event_id": event_id,
        "event_type": "transaction.completed",
        "data": {
            "id": f"txn_{event_id}",
            "currency_code": "USD",
            "custom_data": stamp(user_id, product),
            "details": {"totals": {"grand_total": "899"}},
        },
    }


def _session(api, headers) -> str:
    return api.get("/v1/auth/session", headers=headers).json()["user_id"]


def _held(api, headers) -> dict:
    return api.get("/v1/billing/entitlements", headers=headers).json()


# ══════════════════════════════════════════════════════════════════════════
#  Choosing a processor
# ══════════════════════════════════════════════════════════════════════════

def _settings(monkeypatch, **environment: str):
    """A fresh `Settings` built from a named environment, cache cleared after."""
    from alma import config as config_module

    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    config_module.settings.cache_clear()
    try:
        return config_module.Settings()
    finally:
        config_module.settings.cache_clear()


def test_a_processor_this_build_cannot_talk_to_refuses_to_start(monkeypatch):
    """A typo must not route real money through the default.

    Falling back would be the worst possible failure of this particular knob:
    the default is Paddle, and Paddle's acceptable-use policy names our category
    as prohibited. A misspelled `ALMA_BILLING_PROVIDER` that quietly kept
    working would be discovered by an account being closed.
    """
    with pytest.raises(Exception, match="not a processor this build can talk to"):
        _settings(monkeypatch, ALMA_BILLING_PROVIDER="stripe")


def test_billing_configured_by_halves_refuses_to_start(monkeypatch):
    """An API key with no webhook secret takes money and grants nothing.

    Checkouts open, the payment succeeds, and every webhook that would have
    turned it into a reading is refused for having no verifiable signature. The
    person who finds out is the one who paid.
    """
    with pytest.raises(Exception, match="half configured"):
        _settings(
            monkeypatch,
            ALMA_BILLING_PROVIDER="paddle",
            PADDLE_API_KEY="pdl_test_key",
            PADDLE_WEBHOOK_SECRET="",
        )


def test_no_credentials_at_all_is_a_service_that_simply_is_not_selling(monkeypatch):
    """The asymmetry with the test above is deliberate.

    All eight calculations work without a processor, so a deploy with nothing
    configured is a legitimate state that boots and answers 503 at the
    checkout. Half of one is somebody who believed they had finished.
    """
    config = _settings(
        monkeypatch,
        ALMA_BILLING_PROVIDER="paddle",
        PADDLE_API_KEY="",
        PADDLE_WEBHOOK_SECRET="",
    )
    assert config.billing_enabled is False
    assert config.missing_billing_credentials() == [
        "PADDLE_API_KEY",
        "PADDLE_WEBHOOK_SECRET",
    ]


def test_readiness_is_asked_of_the_selected_processor_not_of_paddle(monkeypatch):
    """A switchover carries the old keys for a while, and that is the trap.

    `billing_enabled` read `paddle_api_key and paddle_webhook_secret` outright,
    so a deploy that had moved to Dodo and still held its Paddle credentials
    reported billing as working, opened checkouts, and could not verify a single
    webhook. What is asked now is whether the processor *in use* is configured.
    """
    config = _settings(
        monkeypatch,
        ALMA_BILLING_PROVIDER="dodo",
        PADDLE_API_KEY="pdl_test_key",
        PADDLE_WEBHOOK_SECRET="pdl_secret",
        DODO_PAYMENTS_API_KEY="",
        DODO_PAYMENTS_WEBHOOK_KEY="",
    )
    assert config.billing_enabled is False
    assert config.missing_billing_credentials() == [
        "DODO_PAYMENTS_API_KEY",
        "DODO_PAYMENTS_WEBHOOK_KEY",
    ]
    # And what `/ready` lists is what an operator has to go and fill in.
    missing = config.missing_for_production()
    assert "DODO_PAYMENTS_WEBHOOK_KEY" in missing
    assert not any(name.startswith("PADDLE_") for name in missing)


def test_dodo_configured_is_dodo_ready(monkeypatch):
    config = _settings(
        monkeypatch,
        ALMA_BILLING_PROVIDER="dodo",
        DODO_PAYMENTS_API_KEY="dodo_test_key",
        DODO_PAYMENTS_WEBHOOK_KEY="whsec_test",
    )
    assert config.billing_enabled is True
    assert config.missing_billing_credentials() == []


def test_the_factory_hands_back_the_processor_the_configuration_names(monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("ALMA_BILLING_PROVIDER", "paddle")
    config_module.settings.cache_clear()
    try:
        assert config_module.billing_adapter().name == "paddle"
    finally:
        config_module.settings.cache_clear()


def test_asking_for_dodo_never_hands_back_paddle():
    """The one answer that must never come out of the factory.

    Whether the Dodo adapter is installed in this build is not the point — a
    missing adapter has to raise. Silently returning the processor whose policy
    prohibits our category, on a deployment that asked for the other one, is the
    failure this seam exists to prevent.
    """
    try:
        chosen = provider_for("dodo")
    except BillingUnavailable as exc:
        assert "dodo" in str(exc).lower()
    else:
        assert chosen.name == "dodo"


# ══════════════════════════════════════════════════════════════════════════
#  A processor that is not Paddle
# ══════════════════════════════════════════════════════════════════════════

#: The three Standard Webhooks headers, which is what Dodo signs across and
#: what nothing above the adapter is allowed to know about.
THREE_HEADERS = ("webhook-id", "webhook-timestamp", "webhook-signature")


class ThreeHeaderProvider:
    """A stand-in processor that signs across three headers and sells sessions.

    Deliberately not the Dodo adapter. What is being tested here is the
    *router*: that it asks the configured processor to verify, asks it whether
    an email address is a precondition, and returns whatever session shape it
    produced. Using the real Dodo adapter would test the adapter instead, and
    would tie these cases to a file that is allowed to change.
    """

    name = "not-paddle"
    granting = frozenset({"payment.succeeded"})
    revoking = frozenset({"subscription.expired"})
    requires_email = True
    merchant = "Not Paddle Ltd"
    #: A card processor: ours is the receipt that carries the ticked sentences,
    #: so this stand-in claims what Paddle and Dodo claim. The stores are the
    #: other answer, and `test_billing_appstore.py` covers that side.
    issues_the_receipt = False

    def verify(self, raw_body: bytes, headers, *, secret: str | None = None) -> None:
        missing = [name for name in THREE_HEADERS if not header_value(headers, name)]
        if missing:
            raise InvalidSignature(f"missing {', '.join(missing)}")

    def parse(self, payload: dict, headers=None) -> NormalisedEvent:
        # The headers are part of the protocol because Standard Webhooks puts
        # the per-delivery id in one. This stand-in takes them and reads its id
        # from the body, which is the shape a Paddle-like processor has.
        data = payload.get("data") or {}
        return NormalisedEvent(
            provider=self.name,
            id=str(payload.get("event_id") or ""),
            type=str(payload.get("event_type") or ""),
            kind=EventKind.PAYMENT,
            owner_id=data.get("user_id"),
            product=data.get("product"),
            transaction_id=data.get("payment_id"),
            amount_cents=899,
            currency="USD",
            grants=True,
            moves_money=True,
            payload=payload,
        )

    async def enrich(self, event: NormalisedEvent) -> NormalisedEvent:
        # A processor whose delivery says everything. Google's does not, which
        # is why this is on the protocol at all.
        return event

    async def open_session(
        self, *, product, user_id, currency, country=None, email=None
    ) -> SessionHandle:
        return SessionHandle(
            provider=self.name,
            product=product,
            currency=currency,
            cents=899,
            display="$8.99",
            custom_data={},
            url=f"https://checkout.example/{product}",
            environment="sandbox",
        )

    async def cancel_subscription(self, subscription_id: str) -> None:
        return None


@pytest.fixture
def other_processor(paid_api, monkeypatch):
    """Run the endpoints against a processor that is not the one we ship."""
    from alma.api.routers import billing as router

    monkeypatch.setattr(router, "billing_adapter", lambda *_, **__: ThreeHeaderProvider())
    return paid_api


def test_the_webhook_verifies_the_way_the_configured_processor_signs(other_processor):
    """The endpoint used to declare `Paddle-Signature` in its own signature.

    One processor's header in the parameter list of the route every processor
    has to call: on any other scheme the header is absent, the value handed to
    the verifier is empty, and every real delivery is refused as unsigned.
    """
    refused = _post_webhook(
        other_processor,
        {"event_id": "evt_1", "event_type": "payment.succeeded", "data": {}},
        headers={"Paddle-Signature": "ts=1;h1=whatever"},
    )
    assert refused.status_code == 401
    assert "webhook-id" in refused.json()["detail"]


def test_a_grant_records_which_processor_paid_for_it(other_processor, auth_headers):
    """`entitlement.source` and `purchase.provider` both defaulted to "paddle".

    A row that cannot say which processor wrote it is a row nobody can
    reconcile the month a business runs two of them — which is exactly what a
    migration between processors looks like from the inside.
    """

    from sqlalchemy import select

    from alma.db.models import Entitlement, Purchase
    from alma.db.session import session_factory

    user_id = _session(other_processor, auth_headers)
    response = _post_webhook(
        other_processor,
        {
            "event_id": "evt_paid",
            "event_type": "payment.succeeded",
            "data": {"user_id": user_id, "product": "door.natal", "payment_id": "pay_1"},
        },
        headers={name: "x" for name in THREE_HEADERS},
    )
    assert response.json()["status"] == "granted natal"

    async def read():
        async with session_factory()() as session:
            purchases = (await session.execute(select(Purchase))).scalars().all()
            grants = (await session.execute(select(Entitlement))).scalars().all()
            return [p.provider for p in purchases], [e.source for e in grants]

    providers, sources = read_async(read)
    assert providers == ["not-paddle"]
    assert sources == ["not-paddle"]


def test_a_processor_that_needs_an_email_says_so_before_the_button(
    other_processor, auth_headers
):
    """Dodo cannot create a session for a customer it has never seen.

    That turns the email field on the offer screen from a nice-to-have into an
    API precondition, and the interface has to be told which it is *before*
    somebody decides to pay — hence a named error rather than a 500 from the
    processor after the fact. A guest has no address, so this is the ordinary
    path for the funnel this product is built around.
    """
    refused = other_processor.post(
        "/v1/billing/checkout", json={"product": "door.natal"}, headers=auth_headers
    )
    assert refused.status_code == 400
    assert refused.json()["detail"]["error"] == "email_required"

    typo = other_processor.post(
        "/v1/billing/checkout",
        json={"product": "door.natal", "email": "sofia.example.com"},
        headers=auth_headers,
    )
    assert typo.status_code == 400, "an address with no @ is not an address"


def test_a_session_selling_processor_hands_back_no_price_identifier(
    other_processor, auth_headers
):
    """The better of the two checkout shapes, and the reason the seam exists.

    When the server creates the session, the browser is handed a URL and never
    a price id — so there is nothing in the client for a determined person to
    change and be charged a different amount. The response is discriminated by
    `provider`, which is how the interface knows which SDK to open.
    """
    body = other_processor.post(
        "/v1/billing/checkout",
        json={"product": "door.natal", "email": "sofia@example.com"},
        headers=auth_headers,
    ).json()

    assert body["provider"] == "not-paddle"
    assert body["checkout_url"] == "https://checkout.example/door.natal"
    assert "price_id" not in body
    assert body["cents"] == 899


def test_the_catalogue_names_the_processor_and_its_email_requirement(
    other_processor, auth_headers
):
    """The offer screen has to collect the address while the person is deciding."""
    listing = other_processor.get("/v1/billing/catalogue", headers=auth_headers).json()
    assert listing["provider"] == "not-paddle"
    assert listing["requires_email"] is True
    # ...and who legally sells to this person, because the processor is the
    # merchant of record and the legal pages held that as a build-time constant
    # naming one of them. The refunds page is what a card issuer reads.
    assert listing["merchant"] == "Not Paddle Ltd"


# ══════════════════════════════════════════════════════════════════════════
#  Cancelling, which is not refunding
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def cancels(monkeypatch) -> list[str]:
    """What the processor was asked to cancel, without calling anybody."""
    from alma.billing.paddle import PaddleProvider

    asked: list[str] = []

    async def stub(self, subscription_id: str) -> None:
        asked.append(subscription_id)

    monkeypatch.setattr(PaddleProvider, "cancel_subscription", stub)
    return asked


@pytest.fixture
def cancel_refused(monkeypatch) -> None:
    from alma.billing.paddle import PaddleProvider

    async def stub(self, subscription_id: str) -> None:
        raise BillingUnavailable("paddle unreachable")

    monkeypatch.setattr(PaddleProvider, "cancel_subscription", stub)


def _subscribe(api, headers, *, subscription_id: str = "sub_1", product: str = "sub.monthly"):
    user_id = _session(api, headers)
    response = _post_webhook(
        api,
        _subscription_event(
            "subscription.activated",
            event_id=f"evt_on_{subscription_id}",
            subscription_id=subscription_id,
            user_id=user_id,
            product=product,
            next_billed_at="2026-09-06T10:00:00Z",
        ),
    )
    assert response.status_code == 200, response.text
    return user_id


def test_cancelling_stops_the_charge_and_keeps_the_period(paid_api, auth_headers, cancels):
    """The rule, stated once: the entitlement is not revoked.

    Someone who cancels a year in month two has paid for ten more months. Taking
    the reading away at the moment they cancel is a refund we never agreed to
    give, arriving as a punishment for leaving — and since 1 July 2025 in
    California and 19 June 2026 in the EU, refusing to cancel in the same medium
    is not lawful either. So the row keeps its expiry and loses only its promise
    to charge again.
    """
    _subscribe(paid_api, auth_headers)
    before = _held(paid_api, auth_headers)["entitlements"][0]
    assert before["renews_at"] is not None
    assert before["active"] is True

    response = paid_api.post("/v1/billing/subscription/cancel", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert cancels == ["sub_1"], "the processor was not told, or was told the wrong id"
    assert body["subscription_ids"] == ["sub_1"]
    assert body["renews_at"] is None
    # The sentence the interface has to be able to say: your plan runs to this
    # date. It is the expiry that was already on the row, unchanged.
    assert body["access_until"] == before["expires_at"]

    after = _held(paid_api, auth_headers)
    assert after["entitlements"][0]["active"] is True, "cancelling revoked what was paid for"
    assert after["entitlements"][0]["renews_at"] is None
    assert set(after["unlocked"]), "the reading closed the moment they cancelled"


def test_the_processor_is_told_the_subscription_id_and_not_the_transaction(
    paid_api, auth_headers, cancels
):
    """A renewal is a new transaction every month; the plan is the stable thing.

    Cancelling against a transaction id cancels one month's charge — which the
    processor has already collected — and leaves the plan billing.
    """
    _subscribe(paid_api, auth_headers, subscription_id="sub_stable")
    paid_api.post("/v1/billing/subscription/cancel", headers=auth_headers)
    assert cancels == ["sub_stable"]


def test_a_processor_that_will_not_cancel_is_never_reported_as_success(
    paid_api, auth_headers, cancel_refused
):
    """A cancellation the customer believes in and the processor never heard of.

    That is the shape of a chargeback and of a complaint to a regulator, and it
    is what writing our own row first would produce. Nothing is written unless
    the processor accepted it.
    """
    _subscribe(paid_api, auth_headers)

    response = paid_api.post("/v1/billing/subscription/cancel", headers=auth_headers)
    assert response.status_code == 502
    assert response.json()["detail"]["error"] == "cancel_failed"

    still = _held(paid_api, auth_headers)["entitlements"][0]
    assert still["renews_at"] is not None, "we recorded a cancellation that never happened"
    assert still["active"] is True


def test_an_account_with_nothing_to_cancel_is_told_so(paid_api, auth_headers):
    response = paid_api.post("/v1/billing/subscription/cancel", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "no_subscription"


def test_a_one_time_purchase_is_not_a_subscription_to_cancel(
    paid_api, auth_headers, cancels
):
    """A door is bought once and kept forever; there is no next charge to stop.

    Worth pinning because the row looks similar from the outside — same table,
    same user — and cancelling one would mean telling a processor to stop
    billing something it never billed.
    """
    user_id = _session(paid_api, auth_headers)
    _post_webhook(paid_api, _purchase_event(event_id="evt_door", user_id=user_id))

    response = paid_api.post("/v1/billing/subscription/cancel", headers=auth_headers)
    assert response.status_code == 404
    assert cancels == []
    assert "natal" in _held(paid_api, auth_headers)["unlocked"]


# ══════════════════════════════════════════════════════════════════════════
#  A cancellation webhook has to find the grant it names
# ══════════════════════════════════════════════════════════════════════════

def test_a_cancellation_reaches_the_grant_that_holds_its_subscription_id(
    paid_api, auth_headers
):
    """The revocation used to match on `event.transaction_id`, and never fired.

    On a subscription event the transaction id resolves to the subscription's
    own id, while the entitlement a subscription writes carries no transaction
    id at all — `data.id` there is a plan and not a payment, so storing it as
    one would make the two columns mean the same thing. Nothing matched, and a
    cancellation silently revoked nothing: the plan was cancelled at the
    processor and kept granting here until its expiry.

    The row this closes is found only by its subscription id, and the assertion
    on `transaction_id` is what says so — a row with no transaction id cannot
    have been found by one.
    """

    from sqlalchemy import select

    from alma.db.models import Entitlement
    from alma.db.session import session_factory

    _subscribe(paid_api, auth_headers, subscription_id="sub_real")

    async def read():
        async with session_factory()() as session:
            return (await session.execute(select(Entitlement))).scalars().all()

    granted = read_async(read)
    assert [(e.subscription_id, e.transaction_id) for e in granted] == [("sub_real", None)]

    response = _post_webhook(
        paid_api,
        _subscription_event(
            "subscription.canceled", event_id="evt_off", subscription_id="sub_real"
        ),
    )
    # It reaches exactly one row and that row is the one holding the id. What it
    # does to it is note the cancellation, not revoke: the period has been paid
    # for. See `test_a_cancellation_stops_the_charge_and_leaves_the_period_alone`.
    assert response.json()["status"] == "noted 1"
    assert _held(paid_api, auth_headers)["unlocked"], "a paid period was repossessed"
    assert _held(paid_api, auth_headers)["entitlements"][0]["renews_at"] is None


def test_a_cancellation_reaches_the_plan_it_names_and_leaves_the_other_one(
    paid_api, auth_headers
):
    """Two plans on one account, and only the cancelled one stops renewing.

    A handler that walked every entitlement the user holds would pass a test
    with one subscription in it and stop a second plan in production. The match
    is on the subscription id the event carries, and this is the case that can
    tell the difference.
    """
    user_id = _subscribe(paid_api, auth_headers, subscription_id="sub_month")
    _post_webhook(
        paid_api,
        _subscription_event(
            "subscription.activated",
            event_id="evt_on_year",
            subscription_id="sub_year",
            user_id=user_id,
            product="sub.monthly",
        ),
    )
    assert len(_held(paid_api, auth_headers)["entitlements"]) == 2

    # No `custom_data` on this one, exactly as a cancellation arrives: the owner
    # has to be found from the entitlement holding that subscription id.
    response = _post_webhook(
        paid_api,
        _subscription_event(
            "subscription.canceled", event_id="evt_off_year", subscription_id="sub_year"
        ),
    )
    assert response.json()["status"] == "noted 1"

    rows = _held(paid_api, auth_headers)["entitlements"]
    assert len(rows) == 2
    # Раньше строки различались видом (`monthly` против `annual`). Подписка в v3
    # одна, поэтому две живые подписки — это два **разных** `subscription_id` с
    # одним видом, и это ровно тот случай, который тест и должен ловить: он
    # проверяет, что отмена нашла строку по идентификатору, а не прошлась по
    # всем правам подряд. Различаем их обещанием списать.
    cancelled = [row for row in rows if row["renews_at"] is None]
    running = [row for row in rows if row["renews_at"] is not None]
    assert len(cancelled) == 1 and len(running) == 1
    # The cancelled one stops renewing and keeps running; the other is untouched.
    assert cancelled[0]["active"] is True
    assert running[0]["active"] is True
    assert {row["kind"] for row in rows} == {"monthly"}


def test_a_cancellation_for_a_subscription_we_do_not_hold_revokes_nothing(
    paid_api, auth_headers
):
    """An event about somebody else's plan, or one from another environment.

    Without an owner there is nothing to revoke, and the money trail keeps the
    record either way — the alternative, guessing at an owner, is how one
    person's cancellation closes another person's reading.
    """
    _subscribe(paid_api, auth_headers, subscription_id="sub_ours")

    response = _post_webhook(
        paid_api,
        _subscription_event(
            "subscription.canceled", event_id="evt_stranger", subscription_id="sub_theirs"
        ),
    )
    assert "without an owner" in response.json()["status"]
    assert _held(paid_api, auth_headers)["entitlements"][0]["active"] is True
