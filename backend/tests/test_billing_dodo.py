"""The Dodo adapter, probed the way the Paddle one is.

Same adversary, different scheme: an unsigned request, a wrong secret, a
replayed timestamp, a body truncated after signing — and then every event in
Dodo's table mapped onto the grant it should produce, including the three that
look exactly like revocations and are not.

**The fixtures are documented shapes, not captured traffic.** Nobody has a
Dodo account yet — no purchase has ever completed through any of this code —
so every payload here is assembled from Dodo's published schemas (the
`Payment`, `Subscription`, `Refund` and `Dispute` response objects, and the
`{business_id, type, timestamp, data}` webhook envelope). A field that is not
in those schemas is not in these fixtures. When a real webhook first lands,
the thing to check is that it has no field these do not.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest

from alma.billing import catalogue as prices
from alma.billing import dodo
from alma.billing import provider as provider_module
from alma.billing.provider import stamp
from alma.billing.dodo import Event, InvalidSignature, entitlement_for, parse, verify

#: Base64 of `b"test-dodo-webhook-secret"`, carrying the `whsec_` prefix a
#: Standard Webhooks secret has. The prefix and the base64 both matter: the
#: key that signs is the *decoded* bytes, not the string.
SECRET = "whsec_dGVzdC1kb2RvLXdlYmhvb2stc2VjcmV0"


def _sign(
    body: bytes,
    *,
    event_id: str = "evt_dodo_1",
    secret: str = SECRET,
    timestamp: int | None = None,
) -> dict[str, str]:
    """Sign a body the way the Standard Webhooks specification says to.

    Written out from the spec rather than called out to the module under test:
    `id.timestamp.body`, HMAC-SHA256 under the base64-decoded secret, base64,
    tagged `v1,`. A test that asks `verify` to check `verify`'s own output
    proves only that the function is deterministic.
    """
    stamp = timestamp if timestamp is not None else int(time.time())
    key = base64.b64decode(secret.removeprefix("whsec_") + "==")
    digest = hmac.new(key, f"{event_id}.{stamp}.".encode() + body, hashlib.sha256).digest()
    return {
        "webhook-id": event_id,
        "webhook-timestamp": str(stamp),
        "webhook-signature": f"v1,{base64.b64encode(digest).decode()}",
    }


# ── the documented payload shapes ──────────────────────────────────────────

def _payment(
    event_type: str = "payment.succeeded",
    *,
    user_id: str | None = "user-1",
    product: str | None = "door.natal",
    total: int = 899,
    subscription_id: str | None = None,
) -> dict:
    # Sealed the way `open_session` seals it. Bare `{"user_id": …, "product":
    # …}` is metadata nothing reads any more: a grant is only ever taken from a
    # blob carrying our own signature, so a fixture writing a plain one would be
    # rehearsing the attack rather than the purchase.
    metadata: dict = (
        stamp(user_id, product)
        if user_id is not None and product is not None
        else {key: value for key, value in
              (("user_id", user_id), ("product", product)) if value is not None}
    )
    return {
        "business_id": "bus_alma",
        "type": event_type,
        "timestamp": "2026-08-06T12:00:00Z",
        "data": {
            "payload_type": "Payment",
            "payment_id": "pay_1",
            "business_id": "bus_alma",
            "brand_id": "brd_1",
            "created_at": "2026-08-06T12:00:00Z",
            "currency": "USD",
            "total_amount": total,
            "tax": 0,
            # Deliberately different from `total_amount`: this is what reaches
            # our Dodo balance after conversion, and it must never be the
            # number the money trail records.
            "settlement_amount": 812,
            "settlement_currency": "USD",
            "customer": {
                "customer_id": "cus_1",
                "name": "A Buyer",
                "email": "buyer@example.com",
            },
            "billing": {
                "country": "IT",
                "state": None,
                "city": None,
                "street": None,
                "zipcode": None,
            },
            "metadata": metadata,
            "product_cart": [{"product_id": "pdt_door", "quantity": 1}],
            "subscription_id": subscription_id,
            "digital_products_delivered": True,
            "payment_provider": "dodo",
            "disputes": [],
            "refunds": [],
            "retry_attempt": 0,
            "is_update_payment_method": False,
            "status": "succeeded",
        },
    }


def _subscription(
    event_type: str,
    *,
    user_id: str | None = "user-1",
    product: str = "sub.monthly",
    status: str = "active",
    subscription_id: str = "sub_1",
) -> dict:
    metadata: dict = stamp(user_id, product) if user_id is not None else {"product": product}
    return {
        "business_id": "bus_alma",
        "type": event_type,
        "timestamp": "2026-08-06T12:00:00Z",
        "data": {
            "payload_type": "Subscription",
            "subscription_id": subscription_id,
            "status": status,
            "product_id": "pdt_monthly",
            "quantity": 1,
            "recurring_pre_tax_amount": 999,
            "tax_inclusive": False,
            "currency": "USD",
            "brand_id": "brd_1",
            "created_at": "2026-08-06T12:00:00Z",
            "next_billing_date": "2026-09-06T12:00:00Z",
            "previous_billing_date": "2026-08-06T12:00:00Z",
            "payment_frequency_interval": "Month",
            "payment_frequency_count": 1,
            "subscription_period_interval": "Month",
            "subscription_period_count": 1,
            "trial_period_days": 0,
            "on_demand": False,
            "cancel_at_next_billing_date": False,
            "cancelled_at": None,
            "customer": {
                "customer_id": "cus_1",
                "name": "A Buyer",
                "email": "buyer@example.com",
            },
            "billing": {"country": "DE", "state": None, "city": None,
                        "street": None, "zipcode": None},
            "metadata": metadata,
            "addons": [],
            "meters": [],
        },
    }


def _refund(*, is_partial: bool, amount: int = 3899) -> dict:
    return {
        "business_id": "bus_alma",
        "type": "refund.succeeded",
        "timestamp": "2026-08-06T12:00:00Z",
        "data": {
            "payload_type": "Refund",
            "refund_id": "ref_1",
            "payment_id": "pay_1",
            "business_id": "bus_alma",
            "brand_id": "brd_1",
            "created_at": "2026-08-06T12:00:00Z",
            "is_partial": is_partial,
            "amount": amount,
            "currency": "USD",
            "status": "succeeded",
            "reason": None,
            "customer": {
                "customer_id": "cus_1",
                "name": "A Buyer",
                "email": "buyer@example.com",
            },
            "metadata": {},
        },
    }


def _dispute(event_type: str) -> dict:
    return {
        "business_id": "bus_alma",
        "type": event_type,
        "timestamp": "2026-08-06T12:00:00Z",
        "data": {
            "payload_type": "Dispute",
            "dispute_id": "dis_1",
            "payment_id": "pay_1",
            "business_id": "bus_alma",
            # A string, while every other amount in the API is an integer of
            # minor units. This is Dodo's schema, not a mistake in the fixture.
            "amount": "3899",
            "currency": "USD",
            "created_at": "2026-08-06T12:00:00Z",
            "dispute_stage": "dispute",
            "dispute_status": "dispute_lost",
        },
    }


# ── signature verification ─────────────────────────────────────────────────

def test_the_signed_message_is_the_one_the_specification_names(monkeypatch):
    """A known-answer vector, so the wire format cannot drift quietly.

    Every part of the construction is pinned by this one assertion: the
    message is `id.timestamp.body`, the key is the *base64-decoded* secret
    rather than the string, the digest is HMAC-SHA256, and it goes on the wire
    base64-encoded behind a `v1,` tag. Get any of those wrong and a real
    webhook fails in a way that reads exactly like a mistyped secret.

    The expected value was produced by the Standard Webhooks reference
    implementation — the same code Dodo's own SDK delegates to.
    """
    body = b'{"type":"payment.succeeded"}'
    headers = {
        "webhook-id": "evt_dodo_0001",
        "webhook-timestamp": "1754500000",
        "webhook-signature": "v1,WUSbO/31hkG0XaFQxXsKdjJHxFmk1nyH5PN3NWzPWCs=",
    }
    # Frozen so the replay window does not reject a vector that is, by design,
    # from a fixed moment.
    from alma.billing import provider

    monkeypatch.setattr(provider.time, "time", lambda: 1754500000.0)
    verify(body, headers, secret=SECRET)


def test_a_correctly_signed_body_verifies():
    body = json.dumps(_payment()).encode()
    verify(body, _sign(body), secret=SECRET)


def test_an_unsigned_request_is_refused():
    body = json.dumps(_payment()).encode()
    with pytest.raises(InvalidSignature, match="missing"):
        verify(body, {}, secret=SECRET)


def test_each_of_the_three_headers_is_required():
    """Two of three is not a signature; it is a signature over an unknown message."""
    body = json.dumps(_payment()).encode()
    complete = _sign(body)
    for dropped in complete:
        partial = {name: value for name, value in complete.items() if name != dropped}
        with pytest.raises(InvalidSignature, match="missing"):
            verify(body, partial, secret=SECRET)


def test_the_headers_are_matched_case_insensitively():
    """HTTP header names are case-insensitive and proxies do rewrite them."""
    body = json.dumps(_payment()).encode()
    shouted = {name.upper(): value for name, value in _sign(body).items()}
    verify(body, shouted, secret=SECRET)


def test_the_wrong_secret_is_refused():
    body = json.dumps(_payment()).encode()
    other = "whsec_" + base64.b64encode(b"someone-elses-secret").decode()
    with pytest.raises(InvalidSignature, match="does not match"):
        verify(body, _sign(body, secret=other), secret=SECRET)


def test_a_body_altered_after_signing_is_refused():
    """The whole point: the amount cannot be edited in flight."""
    body = json.dumps(_payment()).encode()
    headers = _sign(body)
    tampered = json.dumps(_payment(total=999999)).encode()
    with pytest.raises(InvalidSignature, match="does not match"):
        verify(tampered, headers, secret=SECRET)


def test_a_truncated_body_is_refused():
    """Half a payload is not a shorter payload; it is a different message.

    Worth its own case because a truncated body is what a dropped connection
    or a proxy with a size limit produces, and the JSON it leaves behind can
    still parse — `{"total_amount": 8990` cut before the tax line does not,
    but plenty of truncations do.
    """
    body = json.dumps(_payment()).encode()
    headers = _sign(body)
    with pytest.raises(InvalidSignature, match="does not match"):
        verify(body[: len(body) // 2], headers, secret=SECRET)


def test_a_replayed_signature_expires():
    """A valid signature from last week is still a replay."""
    body = json.dumps(_payment()).encode()
    old = _sign(body, timestamp=int(time.time()) - 3600)
    with pytest.raises(InvalidSignature, match="replay"):
        verify(body, old, secret=SECRET)


def test_a_signature_from_the_future_is_refused_too():
    """A clock far ahead of ours is a replay window held open by an attacker."""
    body = json.dumps(_payment()).encode()
    ahead = _sign(body, timestamp=int(time.time()) + 3600)
    with pytest.raises(InvalidSignature, match="replay"):
        verify(body, ahead, secret=SECRET)


def test_the_id_is_part_of_the_signed_message():
    """Otherwise one signed body could be replayed under a fresh event id.

    The idempotency key is `webhook-id`. If it were not signed, an attacker
    holding one valid delivery could change the id and have the same purchase
    granted again — the insert-before-process check would see a new id and let
    it through.
    """
    body = json.dumps(_payment()).encode()
    headers = _sign(body)
    headers["webhook-id"] = "evt_dodo_replayed"
    with pytest.raises(InvalidSignature, match="does not match"):
        verify(body, headers, secret=SECRET)


def test_a_rotation_header_carrying_several_signatures_is_accepted():
    """A secret is rotated by sending both signatures on every delivery.

    Reading only the first would break every webhook for the length of the
    rotation window, and the failure would arrive as "signature does not
    match" — which reads as an attack rather than as a rotation.
    """
    body = json.dumps(_payment()).encode()
    stamp = int(time.time())
    old = _sign(body, secret="whsec_" + base64.b64encode(b"the-old-one").decode(),
                timestamp=stamp)
    new = _sign(body, timestamp=stamp)
    headers = dict(new)
    headers["webhook-signature"] = (
        f"{old['webhook-signature']} {new['webhook-signature']}"
    )
    verify(body, headers, secret=SECRET)


def test_an_unknown_signature_version_is_not_accepted():
    """A `v2,` we do not understand must not be treated as a pass."""
    body = json.dumps(_payment()).encode()
    headers = _sign(body)
    headers["webhook-signature"] = headers["webhook-signature"].replace("v1,", "v2,", 1)
    with pytest.raises(InvalidSignature, match="does not match"):
        verify(body, headers, secret=SECRET)


def test_a_missing_secret_refuses_rather_than_accepting():
    """No configuration must never mean 'accept everything'."""
    body = json.dumps(_payment()).encode()
    with pytest.raises(InvalidSignature, match="DODO_PAYMENTS_WEBHOOK_KEY"):
        verify(body, _sign(body), secret="")


def test_a_timestamp_that_is_not_a_number_is_refused():
    body = json.dumps(_payment()).encode()
    headers = _sign(body)
    headers["webhook-timestamp"] = "yesterday"
    with pytest.raises(InvalidSignature, match="not a number"):
        verify(body, headers, secret=SECRET)


def test_the_comparison_is_constant_time():
    """Byte-at-a-time comparison leaks the signature to a patient attacker."""
    import inspect

    assert "compare_digest" in inspect.getsource(dodo.verify)


def test_the_replay_window_is_the_one_we_already_had():
    """Dodo documents no window, so ours is the only one there is.

    Pinned because it is the sort of constant that gets loosened during a
    debugging session and left loose.
    """
    from alma.billing import paddle

    assert dodo.MAX_SIGNATURE_AGE is paddle.MAX_SIGNATURE_AGE
    assert dodo.MAX_SIGNATURE_AGE <= 300


# ── the event id comes from the header ─────────────────────────────────────

def test_the_delivery_id_is_read_from_the_header():
    """`webhook-id` is the idempotency key; there is no id in the body."""
    payload = _payment()
    event = parse(payload, {"webhook-id": "evt_dodo_77"})
    assert event.id == "evt_dodo_77"
    assert event.type == "payment.succeeded"


def test_without_the_header_there_is_no_id_rather_than_an_invented_one():
    """There used to be a fallback here that hashed the event's identity.

    It was wrong in both directions and the errors were silent. Dodo states
    that a retry carries "the latest payload at the time of delivery", so a
    timestamp refreshed between attempts made a retry look like a new event and
    granted a second period; and two distinct refunds of one payment inside the
    same second shared every hashed field, so the second was answered "already
    processed" and never happened — the money went back and the grant stayed.

    An id we do not have is now an id we do not have. The router answers 400,
    which is visible, rather than filing the delivery under a guess.
    """
    assert parse(_payment()).id == ""
    assert parse(_payment(), {}).id == ""
    assert parse(_payment(), {"webhook-id": "evt_real"}).id == "evt_real"


# ── what the adapter absorbs ───────────────────────────────────────────────

def test_the_owner_and_product_are_read_from_dodo_s_metadata():
    """Paddle calls it `custom_data`; Dodo calls it `metadata`.

    The names on the far side of the seam are identical, which is the only
    reason `entitlement_for` and the webhook handler can be written once.
    """
    event = parse(_payment(user_id="user-42", product="bundle.static"))
    assert event.user_id == "user-42"
    assert event.product_slug == "bundle.static"


def test_a_metadata_value_that_returns_as_a_number_still_finds_its_user():
    """Dodo types a metadata value as string, number *or* boolean.

    A user id that leaves as `"7"` can come back as `7.0`, and
    `session.get(User, 7.0)` finds nobody and raises nothing.
    """
    payload = _payment()
    payload["data"]["metadata"]["user_id"] = 7
    assert parse(payload).user_id == "7"


def test_the_amount_country_and_currency_are_read_from_dodo_s_nesting():
    event = parse(_payment(total=5900))
    assert event.amount_cents() == 5900
    assert event.currency() == "USD"
    # One level shallower than Paddle's `billing_details.address.country_code`,
    # and still the ISO code `currency_for` expects.
    assert event.country == "IT"
    assert prices.currency_for(event.country) == "EUR"


def test_the_settlement_amount_is_never_what_the_money_trail_records():
    """It is what reaches our balance after conversion, not what was charged.

    Recording it would restate every foreign sale by the spread, silently.
    """
    event = parse(_payment(total=899))
    assert event.data["settlement_amount"] != 899
    assert event.amount_cents() == 899


def test_a_subscription_event_reports_no_money():
    """`recurring_pre_tax_amount` is pre-tax and must not enter that column.

    Every other amount in the money trail is tax-inclusive, and the credit
    calculation reads them against each other. The money for a subscription
    arrives on its own `payment.succeeded`, so zero here is the truth.
    """
    event = parse(_subscription("subscription.active"))
    assert event.data["recurring_pre_tax_amount"] == 999
    assert event.amount_cents() == 0


def test_a_missing_total_does_not_raise():
    assert Event(id="e", type="payment.succeeded", payload={"data": {}}).amount_cents() == 0


def test_the_payment_and_the_thing_that_reduces_it_are_told_apart():
    """Dodo names them separately, so the fallback Paddle needs is absent.

    On Paddle, `data.id` is the transaction on one event and the adjustment on
    another, and preferring the wrong one attached every refund to a
    transaction that does not exist. Here the payment is always `payment_id`
    and the refund's own id is always `refund_id`.
    """
    refund = parse(_refund(is_partial=False))
    assert refund.transaction_id == "pay_1"
    assert refund.adjustment_id == "ref_1"

    payment = parse(_payment())
    assert payment.transaction_id == "pay_1"
    assert payment.adjustment_id is None


def test_a_subscription_id_is_flat_on_every_shape_that_has_one():
    assert parse(_subscription("subscription.renewed")).subscription_id == "sub_1"
    assert parse(_payment(subscription_id="sub_1")).subscription_id == "sub_1"
    assert parse(_payment()).subscription_id is None


def test_both_adapters_answer_to_the_same_names():
    """The seam, asserted directly.

    `entitlement_for` and the webhook handler read these names and nothing
    else. If one adapter grows a name the other lacks, the handler starts
    caring which processor it is talking to, and there is no seam left.
    """
    from alma.billing import paddle

    contract = (
        "id", "type", "payload", "data", "transaction_id", "adjustment_id",
        "adjustment", "subscription_id", "status", "renews_at", "custom",
        "user_id", "product_slug", "country", "amount_cents", "currency",
        "normalise",
    )
    for name in contract:
        assert hasattr(paddle.Event, name), f"paddle.Event lost {name}"
        assert hasattr(dodo.Event, name), f"dodo.Event lost {name}"

    for name in ("Grant", "PERIOD", "GRANTING", "REVOKING", "MONEY_EVENTS",
                 "entitlement_for", "parse", "verify", "InvalidSignature"):
        assert hasattr(paddle, name), f"paddle lost {name}"
        assert hasattr(dodo, name), f"dodo lost {name}"


def test_a_dodo_grant_is_a_paddle_grant():
    """Not a lookalike. The entitlement layer must take one contract, not two.

    Two `InvalidSignature` classes with the same name would both look right,
    and only one of them would be caught by the router's `except` — which is
    the shape of a webhook endpoint that accepts everything.
    """
    from alma.billing import paddle, provider

    assert dodo.Grant is paddle.Grant is provider.Grant
    assert dodo.InvalidSignature is paddle.InvalidSignature is provider.InvalidSignature
    assert dodo.PERIOD is provider.PERIOD


def test_the_adapter_is_a_billing_provider():
    from alma.billing.provider import BillingProvider

    assert isinstance(dodo.DodoProvider(), BillingProvider)
    assert dodo.DodoProvider.name == "dodo"


def test_the_factory_hands_back_this_adapter_when_the_configuration_asks():
    """The one answer that must never come out of the factory is Paddle."""
    from alma.billing.provider import provider_for

    assert isinstance(provider_for("dodo"), dodo.DodoProvider)


# ── every event in the table ───────────────────────────────────────────────

def test_a_succeeded_payment_grants_the_product():
    grant = entitlement_for(parse(_payment(product="door.natal")))
    assert (grant.system, grant.kind, grant.duration) == ("natal", "one_time", None)
    assert grant.scope == "system"


def test_a_plan_purchase_grants_everything_for_the_period_it_paid_for():
    grant = entitlement_for(parse(_payment(product="sub.monthly", total=999)))
    assert grant.system == "*" and grant.kind == "monthly"
    assert grant.scope == "all"
    assert grant.duration is not None and 28 <= grant.duration.days <= 31


def test_an_activated_subscription_grants_its_plan_and_carries_its_id():
    grant = entitlement_for(parse(_subscription("subscription.active")))
    assert grant.kind == "monthly"
    # `all`, а не `live`: подписка v3 продаёт всё, пока за неё платят.
    assert grant.scope == "all"
    assert grant.subscription_id == "sub_1"
    assert grant.duration is not None and 28 <= grant.duration.days <= 31


def test_a_renewal_extends_the_same_subscription():
    """A renewal has to name the subscription, not the charge.

    Every renewal is a new payment with a new id, so a grant keyed on the
    payment writes one row a month and a cancellation only ever catches the
    last of them.
    """
    grant = entitlement_for(parse(_subscription("subscription.renewed")))
    assert grant.subscription_id == "sub_1"
    assert grant.duration is not None


def test_a_renewal_payment_does_not_grant_a_second_period():
    """The one place Dodo costs money where Paddle does not.

    Dodo emits **both** `payment.succeeded` and `subscription.renewed` for the
    same renewal; Paddle emits only the transaction. `entitlements.grant`
    extends the subscription row by a period each time it is called, so
    granting on both would hand out two months for one month's money — every
    month, silently, with the row drifting further ahead of the payments.
    """
    both = parse(_payment(product="sub.monthly", total=999, subscription_id="sub_1"))
    assert entitlement_for(both) is None

    alone = parse(_payment(product="door.natal"))
    assert entitlement_for(alone) is not None


def test_every_recurring_product_is_granted_with_an_expiry():
    """Stated over the catalogue rather than over the two plans we have today.

    A recurring plan granted without a duration is a payment that never has to
    be made again, and `grant()` raises for exactly that — but only if the
    kind reaching it is the recurring one.
    """
    for key, item in prices.PRODUCTS.items():
        # Priced at what the catalogue asks: a money event carrying less than
        # the product costs grants nothing.
        grant = entitlement_for(parse(_payment(product=key, total=item.cents)))
        if item.scope == "pair":
            # Единственная строка, которая намеренно не грантит отсюда:
            # партнёра называет PairIntent (А4, Ф0.3), не прайс-лист.
            assert grant is None, key
            continue
        assert grant is not None, key
        if item.interval:
            assert grant.duration is not None, key
            assert grant.kind == item.kind, key
        else:
            assert grant.duration is None, key


def test_a_subscription_on_hold_does_not_revoke():
    """Dunning. Dodo's own words: 'put on hold due to failed renewal'.

    Dodo goes on retrying the card. Revoking here takes the product from
    somebody whose payment is about to succeed, and the person whose card
    bounced is the person least able to argue about it. If the retries fail,
    `subscription.expired` arrives and that is the honest moment.
    """
    event = parse(_subscription("subscription.on_hold", status="on_hold"))
    assert entitlement_for(event) is None
    assert "subscription.on_hold" not in dodo.REVOKING


def test_a_cancelled_subscription_runs_to_its_expiry_rather_than_being_revoked():
    """Cancelling is not a refund.

    Somebody who cancels on the 3rd has paid through the end of the period and
    is owed every day of it. Taking the product away at the moment they click
    cancel is charging for a month and delivering three days — and it is the
    click most likely to be followed by a chargeback.
    """
    event = parse(_subscription("subscription.cancelled", status="cancelled"))
    assert entitlement_for(event) is None
    assert "subscription.cancelled" not in dodo.REVOKING


def test_a_failed_subscription_revokes_nothing_because_nothing_was_granted():
    """'Creation failed during mandate creation' — the subscription never started."""
    event = parse(_subscription("subscription.failed", status="failed"))
    assert entitlement_for(event) is None
    assert "subscription.failed" not in dodo.REVOKING


def test_an_expired_subscription_is_the_one_that_closes_the_grant():
    event = parse(_subscription("subscription.expired", status="expired"))
    assert entitlement_for(event) is None
    assert "subscription.expired" in dodo.REVOKING


@pytest.mark.parametrize(
    "event_type",
    [
        "subscription.paused",
        "subscription.updated",
        "subscription.plan_changed",
        "subscription.update_payment_method",
    ],
)
def test_the_remaining_subscription_events_neither_grant_nor_revoke(event_type):
    """Each one has a written reason, and the reason is next to the decision."""
    assert entitlement_for(parse(_subscription(event_type))) is None
    assert event_type not in dodo.REVOKING
    assert event_type in dodo.IGNORED_REASONS


def test_a_failed_payment_grants_nothing_and_revokes_nothing():
    event = parse(_payment("payment.failed"))
    assert entitlement_for(event) is None
    assert "payment.failed" not in dodo.REVOKING


def test_every_event_in_the_table_is_accounted_for():
    """No event Dodo documents may be merely unmentioned.

    An event that is neither granting, nor revoking, nor written down as
    deliberately ignored is an event nobody has thought about — and the way
    that shows up is a subscription that keeps granting after it should have
    stopped.
    """
    table = {
        "payment.succeeded", "payment.failed",
        "subscription.active", "subscription.renewed", "subscription.updated",
        "subscription.on_hold", "subscription.paused", "subscription.cancelled",
        "subscription.expired", "subscription.failed",
        "subscription.plan_changed", "subscription.update_payment_method",
    }
    decided = dodo.GRANTING | dodo.REVOKING | set(dodo.IGNORED_REASONS)
    assert table <= decided, table - decided


# ── refunds and disputes ───────────────────────────────────────────────────

def test_a_full_refund_closes_the_grant_and_a_partial_one_does_not():
    """Somebody refunded five dollars of a thirty-nine dollar archive keeps it.

    The distinction comes from Dodo's own `is_partial` rather than from
    comparing amounts: a whole refund issued in two halves is two partials,
    and arithmetic would call the second one full.
    """
    assert parse(_refund(is_partial=False)).adjustment == ("refund", "full")
    assert parse(_refund(is_partial=True, amount=500)).adjustment == ("refund", "partial")
    assert "refund.succeeded" in dodo.REVOKING


def test_a_refund_grants_nothing():
    assert entitlement_for(parse(_refund(is_partial=False))) is None


def test_a_lost_dispute_is_a_chargeback_and_an_open_one_is_not():
    """A dispute in progress is money held, not money gone.

    Closing the grant when the dispute opens takes the product from somebody
    who may yet be found to have paid for it — and it would add the disputed
    amount to the refund column a second time when the outcome lands.
    """
    assert parse(_dispute("dispute.lost")).adjustment == ("chargeback", "full")
    assert parse(_dispute("dispute.accepted")).adjustment == ("chargeback", "full")
    assert parse(_dispute("dispute.opened")).adjustment is None
    assert parse(_dispute("dispute.challenged")).adjustment is None
    assert "dispute.opened" not in dodo.REVOKING


def test_a_dispute_amount_arriving_as_a_string_is_still_a_number():
    """Dodo types this one as a string while every other amount is an integer."""
    assert parse(_dispute("dispute.lost")).amount_cents() == 3899


def test_a_payment_is_money_and_a_subscription_event_is_not():
    """What belongs in the `Purchase` table, asked as the handler asks it.

    Dodo splits refunds and disputes into families of their own, where Paddle
    folds both into `adjustment.`. A `subscription.*` event carries no payment
    at all, so recording one would write a zero-amount row whose transaction id
    is a subscription — a line in the money trail that never was money.
    """
    assert parse(_payment()).normalise().moves_money is True
    assert parse(_refund(is_partial=True)).normalise().moves_money is True
    assert parse(_dispute("dispute.lost")).normalise().moves_money is True
    assert parse(_subscription("subscription.active")).normalise().moves_money is False


def test_a_dispute_that_is_only_open_has_not_moved_any_money():
    """It names a payment and is in the `dispute.` family, and neither is enough.

    `_record_money` would take an open dispute down the not-an-adjustment path
    and write the whole amount into `refunded_cents` — marking a purchase
    refunded while the outcome is still weeks away, and doing it again when the
    outcome lands.
    """
    for event_type in ("dispute.opened", "dispute.challenged", "dispute.won"):
        assert parse(_dispute(event_type)).normalise().moves_money is False, event_type


# ── the normalised event ───────────────────────────────────────────────────

def test_the_flags_carry_the_whole_policy():
    """Nothing above the adapter holds a Dodo event string, so these are it."""
    granting = parse(_payment(), {"webhook-id": "evt_1"}).normalise()
    assert (granting.grants, granting.revokes) == (True, False)
    assert granting.provider == "dodo"
    assert granting.id == "evt_1"
    assert granting.kind is dodo.EventKind.PAYMENT

    ending = parse(_subscription("subscription.expired", status="expired")).normalise()
    assert (ending.grants, ending.revokes) == (False, True)
    assert ending.kind is dodo.EventKind.SUBSCRIPTION_ENDED

    dunning = parse(_subscription("subscription.on_hold", status="on_hold")).normalise()
    assert (dunning.grants, dunning.revokes) == (False, False)
    assert dunning.kind is dodo.EventKind.SUBSCRIPTION_DUNNING


def test_the_normalised_event_speaks_our_words_and_not_dodo_s():
    """Every field the handler reads, filled from a shape it never sees."""
    event = parse(_subscription("subscription.active")).normalise()
    assert event.owner_id == "user-1"
    assert event.product == "sub.monthly"
    assert event.subscription_id == "sub_1"
    assert event.country == "DE"
    assert event.status == "active"
    assert event.renews_at is not None and event.renews_at.month == 9


def test_a_partial_refund_does_not_close_the_grant_and_a_full_one_does():
    """`closes_the_grant` is the question the revocation actually asks."""
    assert parse(_refund(is_partial=True, amount=500)).normalise().closes_the_grant is False
    assert parse(_refund(is_partial=False)).normalise().closes_the_grant is True
    assert parse(_refund(is_partial=True, amount=500)).normalise().returns_money is True


# ── the client ─────────────────────────────────────────────────────────────

class _Recorder:
    """Подставной общий клиент процесса, записывающий один вызов.

    Подменяется не `httpx.AsyncClient`, а `billing.http.client()` — с 19 августа
    2026 адаптеры кассы не создают клиента на вызов, а берут один на процесс
    (довод — в `billing/http.py`). Контекстный менеджер здесь остался нарочно и
    больше не используется: если кто-нибудь вернёт `async with`, тест продолжит
    проходить и промолчит о том, что рукопожатие вернулось.
    """

    calls: list[tuple[str, str, dict | None]] = []
    status = 200
    body: dict = {}

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def request(self, method, url, *, headers=None, json=None):
        type(self).calls.append((method, url, json))

        class _Response:
            status_code = type(self).status
            content = b"{}"
            text = ""

            def json(inner) -> dict:
                return type(self).body

        return _Response()


@pytest.fixture
def recorder(monkeypatch):
    _Recorder.calls = []
    _Recorder.status = 200
    _Recorder.body = {}
    from alma.billing import http as billing_http

    monkeypatch.setattr(billing_http, "client", lambda: _Recorder())
    return _Recorder


async def test_cancelling_stops_the_next_charge_and_not_the_paid_period(recorder):
    """`cancel_at_next_billing_date`, never `status: "cancelled"`.

    The second ends the subscription there and then and sets `cancelled_at`,
    which takes away access already paid for — a refund we never agreed to
    give, arriving as a punishment for leaving.
    """
    await dodo.DodoClient(api_key="k").cancel_subscription("sub_1")

    method, url, body = recorder.calls[0]
    assert method == "PATCH"
    assert url.endswith("/subscriptions/sub_1")
    assert body == {"cancel_at_next_billing_date": True}
    assert "status" not in body


async def test_a_cancel_that_fails_is_loud(recorder):
    """A cancel that quietly does nothing is found on a card statement."""
    recorder.status = 500
    with pytest.raises(dodo.BillingUnavailable):
        await dodo.DodoClient(api_key="k").cancel_subscription("sub_1")


async def test_an_unconfigured_cancel_refuses_rather_than_returning_quietly():
    with pytest.raises(dodo.BillingUnavailable, match="DODO_PAYMENTS_API_KEY"):
        await dodo.DodoClient(api_key="").cancel_subscription("sub_1")


@pytest.fixture
def listed_on_dodo(monkeypatch):
    """A catalogue row that carries a Dodo product id, because none does yet.

    Faked here rather than written into the catalogue: which identifier a
    processor hands back for a product is a value out of a dashboard nobody has
    opened, and an invented one in the price list is an identifier that looks
    real. The column it goes in is `processor_ids`, keyed by processor name —
    not a flat `dodo_product_id`, which would have made a third processor a
    third column and a third lookup.
    """
    import dataclasses

    natal = prices.PRODUCTS["door.natal"]
    monkeypatch.setitem(
        prices.PRODUCTS,
        "door.natal",
        dataclasses.replace(natal, processor_ids={"dodo": "pdt_natal"}),
    )


async def test_a_session_carries_no_price_the_client_could_change(recorder, listed_on_dodo):
    """The browser gets a URL, never a price identifier.

    This is the half of the swap that is strictly an improvement: Paddle hands
    the browser a price id and a client token, and a price a client names is a
    price a client can substitute.
    """
    recorder.body = {"session_id": "cks_1", "checkout_url": "https://checkout.dodo/x"}
    provider = dodo.DodoProvider(dodo.DodoClient(api_key="k"))

    handle = await provider.open_session(
        product="door.natal", user_id="user-1", currency="USD", country="IT",
    )
    body = handle.to_client()
    assert body["checkout_url"] == "https://checkout.dodo/x"
    assert "price_id" not in body
    assert body["cents"] == prices.PRODUCTS["door.natal"].cents

    # Nor does the browser get the metadata at all: it is sealed into a
    # session the server created, and `to_client` drops the field rather than
    # sending a copy nothing reads back.
    assert "custom_data" not in body

    _method, _url, sent = recorder.calls[0]
    assert sent["metadata"]["user_id"] == "user-1"
    assert sent["metadata"]["product"] == "door.natal"
    # ...and it carries our own signature over that pair, so a copy that came
    # back altered would be read as metadata we did not write.
    assert sent["metadata"][provider_module.SEAL_FIELD]
    # The address is not in the metadata. Metadata is how a payment finds its
    # owner, and an owner found by email is whoever in a household shares one.
    assert "email" not in sent["metadata"]


async def test_a_product_with_no_dodo_identifier_refuses_rather_than_guessing(recorder):
    """Every identifier in the catalogue is empty until a dashboard is opened.

    Opening a session against the wrong product id charges the right money for
    the wrong thing, and the webhook that comes back grants the wrong thing too.
    So it refuses, before the network, naming the exact line to fill in.
    """
    provider = dodo.DodoProvider(dodo.DodoClient(api_key="k"))
    with pytest.raises(dodo.BillingUnavailable, match="processor_ids"):
        await provider.open_session(product="door.natal", user_id="user-1", currency="USD")
    assert recorder.calls == []


def test_one_processor_s_identifier_is_never_read_as_another_s():
    """Two processors can issue the same string, and neither owns the namespace.

    Matching the other one's would resolve a payment onto a product it did not
    buy — so the lookup is narrowed to the processor the event came from.
    """
    import dataclasses

    from alma.billing.catalogue import by_price_id

    clash = dataclasses.replace(
        prices.PRODUCTS["door.natal"], processor_ids={"paddle": "id_the_same"}
    )
    saved = prices.PRODUCTS["door.natal"]
    prices.PRODUCTS["door.natal"] = clash
    try:
        assert by_price_id("id_the_same", "paddle") == "door.natal"
        assert by_price_id("id_the_same", "dodo") is None
        # A support tool holding an identifier and not knowing where it came
        # from still gets an answer.
        assert by_price_id("id_the_same") == "door.natal"
        assert by_price_id("") is None
    finally:
        prices.PRODUCTS["door.natal"] = saved


async def test_a_price_that_does_not_exist_is_refused_before_the_network(
    recorder, monkeypatch, listed_on_dodo
):
    """Цены нет — отказ, и он не стоит похода к процессору.

    Раньше примером служила Бразилия: PPP-рынки не получали дверь. В v3 полка
    продаётся во всех тринадцати валютах, поэтому полосу убирают здесь руками —
    ровно как это сделает первая же правка `REGIONAL_CENTS`. Проверяемое правило
    не изменилось и оно структурное: отсутствие цены — это отказ, а не число,
    которого никто не выбирал, и узнаётся оно до сети.
    """
    monkeypatch.setitem(
        prices.REGIONAL_CENTS, "BRL",
        {k: v for k, v in prices.REGIONAL_CENTS["BRL"].items() if k != "door"},
    )
    provider = dodo.DodoProvider(dodo.DodoClient(api_key="k"))
    with pytest.raises(prices.NotSold):
        await provider.open_session(product="door.natal", user_id="user-1", currency="BRL")
    assert recorder.calls == []


def test_an_email_is_not_a_precondition_for_a_dodo_checkout():
    """Contradicting the brief, on the strength of Dodo's own schema.

    `customer` is optional on a checkout session, and email is required only
    *inside* it, to create a new customer inline. Omit `customer` and Dodo's
    hosted page collects the address itself, while our metadata still carries
    the user id — so the webhook still finds its owner. Claiming otherwise
    would put a form field between somebody who has decided to pay and the act
    of paying, in a product that deliberately lets a guest buy.
    """
    assert dodo.DodoProvider.requires_email is False


# ── the rest ───────────────────────────────────────────────────────────────

def test_an_unknown_event_type_grants_nothing():
    assert entitlement_for(parse(_payment("payout.succeeded"))) is None


def test_an_unknown_product_grants_nothing():
    assert entitlement_for(parse(_payment(product="a-thing-we-do-not-sell"))) is None


def test_a_payment_with_no_metadata_grants_nothing_rather_than_guessing():
    """Every Dodo product id in the catalogue is unset, so nothing resolves.

    The purchase is still recorded — the money is not lost — and support can
    attach it by hand. Guessing a product from a cart we cannot identify is
    how a door becomes an archive.
    """
    event = parse(_payment(user_id=None, product=None))
    assert event.product_slug is None
    assert entitlement_for(event) is None


def test_a_status_string_we_have_never_seen_changes_nothing():
    """`Entitlement.status` is written and never read, and that must survive.

    A provider swap is precisely the day every one of these strings changes at
    once — Paddle says "canceled", Dodo says "cancelled" — so the day a
    provider renames one must not be the day everybody who has paid is locked
    out. Access is decided by the expiry and the revocation, which we set.
    """
    from alma.auth import entitlements
    from alma.db.models import Entitlement

    payload = _subscription("subscription.active")
    payload["data"]["status"] = "a_word_dodo_invented_last_tuesday"
    event = parse(payload)

    ordinary = parse(_subscription("subscription.active"))
    assert event.status == "a_word_dodo_invented_last_tuesday"
    assert entitlement_for(event) == entitlement_for(ordinary)
    assert entitlements.is_in_force(
        Entitlement(status=event.status, revoked_at=None, expires_at=None)
    )


def test_the_client_defaults_to_the_test_host():
    """A typo in an environment variable must not be what charges real cards."""
    assert dodo.DodoClient(api_key="k", environment="").base == dodo.TEST_API
    assert dodo.DodoClient(api_key="k", environment="sandbox").base == dodo.TEST_API
    assert dodo.DodoClient(api_key="k", environment="live_mode").base == dodo.LIVE_API


def test_an_unconfigured_client_does_nothing_rather_than_failing_open():
    assert dodo.DodoClient(api_key="").configured is False
