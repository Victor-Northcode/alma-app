"""The Google Play adapter, probed the way the other three are.

The mirror image of the Apple file. There, the danger is a document that
verifies itself; here there is no document at all — a purchase token is a key
into Google's database and proves nothing — so the questions move: will this
accept a Pub/Sub push from any Google customer who finds the URL, will it grant
a token whose product is not the one being claimed, and will a renewal find the
plan it belongs to when the only stable short identifier is buried in an order
id suffix.

**The Play API is stubbed and the Pub/Sub signature is real.** The API is a
network call whose shapes are documented; a stub of it tests our reading of
those shapes, which is the part we can get wrong. The push token is a genuine
RS256 JWT against a genuine key, because "does the audience check actually
run" is not a question a stub can answer.

**The fixtures are documented shapes, not captured traffic.** Nothing has ever
been sold through this code. Every payload is assembled from Google's published
`SubscriptionPurchaseV2`, `ProductPurchase` and `DeveloperNotification`
references, and a field not in those is not here.
"""

from __future__ import annotations

import base64
import json
import time
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from alma.billing import googleplay
from alma.billing.googleplay import (
    GooglePlayProvider,
    InvalidSignature,
    entitlement_for,
    parse,
    verify,
)
from alma.billing.provider import (
    BillingUnavailable,
    EventKind,
    ProductMismatch,
    PurchaseIncomplete,
    SelfServiceOnly,
    store_product_id,
)

PACKAGE = "com.alma.app"
AUDIENCE = "https://alma.example/v1/billing/webhook"
PUSHER = "play-rtdn@alma.iam.gserviceaccount.com"

#: A real order id, with the suffix Google appends per charge. The base is what
#: identifies the plan across every renewal it will ever have; the whole string
#: identifies one charge.
ORDER = "GPA.3372-3387-1969-56003"


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("GOOGLE_PLAY_PACKAGE_NAME", PACKAGE)
    monkeypatch.setenv("GOOGLE_PLAY_PUBSUB_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT", PUSHER)
    config_module.settings.cache_clear()
    yield
    config_module.settings.cache_clear()


# ── a signing key standing in for Google's ─────────────────────────────────


@pytest.fixture
def google(monkeypatch):
    """Google's OIDC signing key, replaced by one we hold.

    The keys behind `oauth2/v3/certs` rotate on Google's schedule, so unlike
    Apple's root they are fetched rather than pinned — which means the thing to
    test is what happens *after* a signature verifies, and for that the key has
    to be ours.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class _Key:
        def __init__(self, material):
            self.key = material

    class _Client:
        def get_signing_key_from_jwt(self, token):
            return _Key(key.public_key())

    monkeypatch.setattr(googleplay, "_keys", lambda: _Client())
    return key


def _push_token(
    google_key,
    *,
    audience: str = AUDIENCE,
    email: str = PUSHER,
    issuer: str = "https://accounts.google.com",
    expires_in: int = 3600,
) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "iss": issuer,
            "aud": audience,
            "azp": "112233445566778899000",
            "email": email,
            "email_verified": True,
            "sub": "112233445566778899000",
            "iat": now,
            "exp": now + expires_in,
        },
        google_key,
        algorithm="RS256",
    )


def _headers(google_key, **overrides) -> dict:
    return {"Authorization": f"Bearer {_push_token(google_key, **overrides)}"}


# ── the documented payload shapes ──────────────────────────────────────────


def _push(notification: dict, *, message_id: str = "9876543210") -> dict:
    """The Pub/Sub envelope: a base64 blob, a message id, and nothing signed."""
    return {
        "message": {
            "data": base64.b64encode(json.dumps(notification).encode()).decode(),
            "messageId": message_id,
            "publishTime": "2026-08-06T12:00:00.000Z",
        },
        "subscription": "projects/alma/subscriptions/play-rtdn",
    }


def _subscription_notification(code: int, *, token: str = "tok_abc", package=PACKAGE) -> dict:
    return {
        "version": "1.0",
        "packageName": package,
        "eventTimeMillis": str(int(time.time() * 1000)),
        "subscriptionNotification": {
            "version": "1.0",
            "notificationType": code,
            "purchaseToken": token,
        },
    }


def _one_time_notification(code: int, *, sku: str, token: str = "tok_one") -> dict:
    return {
        "version": "1.0",
        "packageName": PACKAGE,
        "eventTimeMillis": str(int(time.time() * 1000)),
        "oneTimeProductNotification": {
            "version": "1.0",
            "notificationType": code,
            "purchaseToken": token,
            "sku": sku,
        },
    }


def _voided_notification(*, order: str = ORDER, refund_type: int = 1) -> dict:
    return {
        "version": "1.0",
        "packageName": PACKAGE,
        "eventTimeMillis": str(int(time.time() * 1000)),
        "voidedPurchaseNotification": {
            "purchaseToken": "tok_abc",
            "orderId": order,
            "productType": 1,
            "refundType": refund_type,
        },
    }


def _subscription_state(
    *,
    product: str = "monthly",
    state: str = "SUBSCRIPTION_STATE_ACTIVE",
    order: str = f"{ORDER}..3",
    units: int = 9,
    nanos: int = 990_000_000,
    days: int = 31,
) -> dict:
    """A `SubscriptionPurchaseV2`, in Google's own field names."""
    expiry = (datetime.now(UTC) + timedelta(days=days)).isoformat().replace("+00:00", "Z")
    return {
        "kind": "androidpublisher#subscriptionPurchaseV2",
        "regionCode": "US",
        "startTime": "2026-05-06T12:00:00Z",
        "subscriptionState": state,
        "latestOrderId": order,
        "acknowledgementState": "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED",
        "lineItems": [
            {
                "productId": store_product_id(product, processor="googleplay"),
                "expiryTime": expiry,
                "autoRenewingPlan": {
                    "autoRenewEnabled": state == "SUBSCRIPTION_STATE_ACTIVE",
                    "recurringPrice": {
                        "currencyCode": "USD",
                        "units": str(units),
                        "nanos": nanos,
                    },
                },
                "offerDetails": {"basePlanId": "monthly"},
            }
        ],
    }


def _product_state(*, purchase_state: int = 0, order: str = ORDER) -> dict:
    """A `ProductPurchase`. Note what is *not* in it: a price, in any form."""
    return {
        "kind": "androidpublisher#productPurchase",
        "purchaseTimeMillis": str(int(time.time() * 1000)),
        "purchaseState": purchase_state,
        "consumptionState": 0,
        "orderId": order,
        "purchaseType": 0,
        "acknowledgementState": 1,
        "quantity": 1,
        "regionCode": "US",
    }


class FakePlay:
    """Google, as far as this adapter can tell.

    Records what it was asked, because two of the rules here are about *which*
    endpoint gets called: the catalogue decides subscription against one-time,
    not the client, and a redelivered notification must cost no call at all.
    """

    def __init__(self, *, subscription: dict | None = None, product: dict | None = None):
        self._subscription = subscription
        self._product = product
        self.calls: list[tuple[str, str]] = []

    async def subscription(self, purchase_token: str) -> dict:
        self.calls.append(("subscription", purchase_token))
        if self._subscription is None:
            raise BillingUnavailable("google refused GET /subscriptionsv2: 404 Not Found")
        return self._subscription

    async def product(self, product_id: str, purchase_token: str) -> dict:
        self.calls.append(("product", product_id))
        if self._product is None:
            raise BillingUnavailable("google refused GET /products: 404 Not Found")
        return self._product


def _adapter(**stubs) -> GooglePlayProvider:
    return GooglePlayProvider(client=FakePlay(**stubs))


# ══════════════════════════════════════════════════════════════════════════
#  The push token, which is the only signature there is
# ══════════════════════════════════════════════════════════════════════════

def test_an_unsigned_push_is_refused(google):
    body = json.dumps(_push(_subscription_notification(2))).encode()
    with pytest.raises(InvalidSignature, match="bearer"):
        verify(body, {})


def test_a_push_for_another_audience_is_refused(google):
    """The claim that makes a Google-signed token *ours*.

    Google will mint a perfectly valid OIDC token for any of its customers and
    any audience they choose, so the signature alone proves only that somebody
    with a Google account sent this. Without the audience check, the
    notification endpoint extends subscriptions for whoever finds the URL.
    """
    body = json.dumps(_push(_subscription_notification(2))).encode()
    headers = _headers(google, audience="https://someone-else.example/hook")
    with pytest.raises(InvalidSignature):
        verify(body, headers)


def test_a_push_from_another_service_account_is_refused(google):
    body = json.dumps(_push(_subscription_notification(2))).encode()
    with pytest.raises(InvalidSignature, match="not"):
        verify(body, _headers(google, email="someone@else.iam.gserviceaccount.com"))


def test_a_push_from_a_non_google_issuer_is_refused(google):
    body = json.dumps(_push(_subscription_notification(2))).encode()
    with pytest.raises(InvalidSignature, match="issuer"):
        verify(body, _headers(google, issuer="https://accounts.evil.example"))


def test_an_expired_push_token_is_refused(google):
    body = json.dumps(_push(_subscription_notification(2))).encode()
    with pytest.raises(InvalidSignature):
        verify(body, _headers(google, expires_in=-60))


def test_a_valid_push_is_accepted(google):
    body = json.dumps(_push(_subscription_notification(2))).encode()
    verify(body, _headers(google))


def test_no_configured_audience_refuses_rather_than_accepting_everything(
    monkeypatch, google
):
    """A missing credential must not read as "accept anything".

    This is the store analogue of `PADDLE_WEBHOOK_SECRET` being unset, and it
    fails the same way: loudly, rather than by granting.
    """
    from alma import config as config_module

    monkeypatch.delenv("GOOGLE_PLAY_PUBSUB_AUDIENCE", raising=False)
    config_module.settings.cache_clear()
    body = json.dumps(_push(_subscription_notification(2))).encode()
    with pytest.raises(InvalidSignature, match="GOOGLE_PLAY_PUBSUB_AUDIENCE"):
        verify(body, _headers(google))


def test_a_notification_for_another_package_is_refused():
    """A Pub/Sub topic pointed at somebody else's Play account.

    It cannot happen through a subscription we own, and it produces perfectly
    valid deliveries granting readings to strangers when it does.
    """
    with pytest.raises(InvalidSignature, match="com.someone.else"):
        parse(_push(_subscription_notification(2, package="com.someone.else")))


# ══════════════════════════════════════════════════════════════════════════
#  Claiming the wrong thing
# ══════════════════════════════════════════════════════════════════════════

async def test_a_token_google_does_not_recognise_is_refused():
    """A forged purchase token, which on Play is a 404 rather than a bad signature.

    It is `BillingUnavailable` and not a distinct exception on purpose: from
    here, a forged token, a token for the wrong package and a real token during
    a Play outage are the same 404, and the two wrong answers — "you are a
    forger" and "try again" — are not a call a status code should make.
    """
    with pytest.raises(BillingUnavailable, match="404"):
        await _adapter().verify_purchase(transaction="tok_forged", product="natal")


async def test_a_product_mismatch_is_refused():
    """The store equivalent of the price check.

    The client cannot choose a price on Play — Google charges the tier we set —
    so the only lie left is the claim. Google's answer about the token is what
    refuses it.
    """
    adapter = _adapter(subscription=_subscription_state(product="monthly"))
    with pytest.raises(ProductMismatch, match="monthly"):
        await adapter.verify_purchase(transaction="tok_abc", product="annual")


async def test_a_pending_purchase_is_not_yet_rather_than_forged():
    """Cash at a convenience store, or a slow bank transfer. A real Play state.

    Refusing it as a forgery would tell somebody who is about to pay that they
    are cheating; the honest answer is "not yet", and the
    `one_time_product.1` notification that follows is what grants.
    """
    adapter = _adapter(product=_product_state(purchase_state=2))
    with pytest.raises(PurchaseIncomplete, match="pending"):
        await adapter.verify_purchase(transaction="tok_one", product="natal")


async def test_a_cancelled_one_time_purchase_is_refused():
    adapter = _adapter(product=_product_state(purchase_state=1))
    with pytest.raises(PurchaseIncomplete):
        await adapter.verify_purchase(transaction="tok_one", product="natal")


async def test_an_expired_subscription_token_is_refused():
    adapter = _adapter(subscription=_subscription_state(state="SUBSCRIPTION_STATE_EXPIRED"))
    with pytest.raises(PurchaseIncomplete, match="EXPIRED"):
        await adapter.verify_purchase(transaction="tok_abc", product="monthly")


async def test_the_catalogue_decides_which_endpoint_is_asked():
    """Not the client, and the difference is the field the grant is keyed on.

    Letting a request say "this is a subscription" would let it ask the
    subscription endpoint about a door — and `SubscriptionPurchaseV2` carries a
    `latestOrderId` where `ProductPurchase` carries an `orderId`, so the two
    answers differ in exactly the place `subscription_id` comes from.
    """
    subscriptions = FakePlay(subscription=_subscription_state())
    await GooglePlayProvider(client=subscriptions).verify_purchase(
        transaction="tok_abc", product="monthly"
    )
    assert [name for name, _ in subscriptions.calls] == ["subscription"]

    products = FakePlay(product=_product_state())
    await GooglePlayProvider(client=products).verify_purchase(
        transaction="tok_one", product="natal"
    )
    assert products.calls == [("product", store_product_id("natal", processor="googleplay"))]


async def test_a_door_purchase_grants_its_system_and_records_no_price():
    """Google states no price for a one-time product, anywhere in v3.

    So the money row records the fact of the payment and not its size, and the
    size is reconciled against the Play payout report. Saying that here rather
    than in a comment alone means a future `ProductPurchase` that *does* carry
    a price will fail this test and be noticed.
    """
    adapter = _adapter(product=_product_state())
    event = await adapter.verify_purchase(transaction="tok_one", product="natal")

    assert event.provider == "googleplay"
    assert event.transaction_id == ORDER
    assert event.id == f"googleplay:{ORDER}"
    assert event.grants and event.moves_money and event.priced_by_us is False
    assert event.amount_cents == 0
    assert event.subscription_id is None

    from alma.billing.provider import entitlement_for as grant_for

    grant = grant_for(event)
    assert (grant.system, grant.kind, grant.scope, grant.duration) == (
        "natal", "one_time", "system", None
    )


async def test_a_subscription_price_is_read_as_units_and_nanos():
    """$9.99 is 9 units and 990 000 000 nanos. Reading only the units is $9.00."""
    adapter = _adapter(subscription=_subscription_state(units=9, nanos=990_000_000))
    event = await adapter.verify_purchase(transaction="tok_abc", product="monthly")
    assert (event.amount_cents, event.currency) == (999, "USD")


async def test_a_subscription_purchase_carries_the_id_every_renewal_will_share():
    """The base of the order id, not the purchase token.

    A Play purchase token can run past a thousand characters and
    `Entitlement.subscription_id` is 64. The base is stable for the life of the
    plan and short enough to store, which is the only pair of properties that
    works.
    """
    adapter = _adapter(subscription=_subscription_state(order=f"{ORDER}..0"))
    event = await adapter.verify_purchase(transaction="tok_abc", product="monthly")

    assert event.subscription_id == ORDER
    assert event.transaction_id == f"{ORDER}..0"
    assert event.renews_at is not None

    from alma.billing.provider import entitlement_for as grant_for

    grant = grant_for(event)
    assert grant.subscription_id == ORDER
    assert grant.scope == "live"
    assert grant.duration is not None and 28 <= grant.duration.days <= 31


# ══════════════════════════════════════════════════════════════════════════
#  Notifications
# ══════════════════════════════════════════════════════════════════════════

async def test_a_renewal_extends_the_same_subscription(google):
    """Two charges, one plan, one row.

    The renewal's order id ends `..4` where the purchase's ended `..0`, and both
    reduce to the same base — which is what stops a grant being written once a
    month and a cancellation catching only the last of them.
    """
    adapter = _adapter(subscription=_subscription_state(order=f"{ORDER}..4"))
    event = adapter.parse(_push(_subscription_notification(2)))
    event = await adapter.enrich(event)

    assert event.kind is EventKind.SUBSCRIPTION_RENEWED
    assert event.subscription_id == ORDER
    assert event.transaction_id == f"{ORDER}..4"
    assert event.grants is True

    from alma.billing.provider import entitlement_for as grant_for

    assert grant_for(event).subscription_id == ORDER


async def test_a_stale_renewal_against_a_dead_plan_grants_nothing():
    """The state is the fresher fact, and the notification is a claim about the past.

    Pub/Sub is at-least-once and can redeliver days later. Granting on the
    strength of the integer alone would extend a plan Google has since expired
    by a whole period.
    """
    adapter = _adapter(subscription=_subscription_state(state="SUBSCRIPTION_STATE_ON_HOLD"))
    event = await adapter.enrich(adapter.parse(_push(_subscription_notification(2))))
    assert event.grants is False


async def test_a_cancellation_does_not_revoke():
    """Play's own words: the subscription remains valid until its expiry time.

    So `SUBSCRIPTION_CANCELED` clears the promise to charge and touches nothing
    else. Revoking here is charging for a month and delivering three days.
    """
    adapter = _adapter(subscription=_subscription_state(state="SUBSCRIPTION_STATE_CANCELED"))
    event = await adapter.enrich(adapter.parse(_push(_subscription_notification(3))))

    assert event.kind is EventKind.SUBSCRIPTION_CANCELLED
    assert event.revokes is False
    assert event.grants is False
    assert "subscription.3" not in googleplay.REVOKING
    # And the cancelled state is still a live one, because on Play it is: a
    # renewal notification arriving in the same period must still extend.
    assert event.status == "SUBSCRIPTION_STATE_CANCELED"


async def test_account_hold_and_grace_period_revoke_nothing():
    """Dunning twice over — and the grace period is Google asking us to keep serving."""
    for code, state in (
        (5, "SUBSCRIPTION_STATE_ON_HOLD"),
        (6, "SUBSCRIPTION_STATE_IN_GRACE_PERIOD"),
    ):
        adapter = _adapter(subscription=_subscription_state(state=state))
        event = await adapter.enrich(adapter.parse(_push(_subscription_notification(code))))
        assert event.kind is EventKind.SUBSCRIPTION_DUNNING
        assert event.revokes is False and event.grants is False


async def test_an_expiry_ends_the_plan():
    adapter = _adapter(subscription=_subscription_state(state="SUBSCRIPTION_STATE_EXPIRED"))
    event = await adapter.enrich(adapter.parse(_push(_subscription_notification(13))))
    assert event.kind is EventKind.SUBSCRIPTION_ENDED
    assert event.revokes is True


async def test_a_refund_closes_the_grant_and_costs_no_api_call():
    """A voided purchase carries its own facts, so there is nothing to ask.

    The token behind it is invalid by definition; asking about it would spend
    quota to be told nothing.
    """
    adapter = _adapter()
    event = await adapter.enrich(adapter.parse(_push(_voided_notification())))

    assert event.kind is EventKind.ADJUSTMENT
    assert event.revokes is True
    assert event.adjustment == ("refund", "full")
    assert event.returns_money and event.closes_the_grant
    assert event.transaction_id == ORDER
    assert adapter.client.calls == []


async def test_a_voided_renewal_names_the_plan_and_not_only_the_charge():
    """A refund in month twelve has to find the row written in month one.

    `entitlements.grant` extends a subscription row in place and never rewrites
    its `transaction_id`, so the entitlement still carries the *first* order id
    while the void names the twelfth. Matching on the transaction alone would
    find nothing — and the money would go back while the plan kept working.
    """
    adapter = _adapter()
    event = await adapter.enrich(
        adapter.parse(_push(_voided_notification(order=f"{ORDER}..11")))
    )
    assert event.transaction_id == f"{ORDER}..11"
    assert event.subscription_id == ORDER


async def test_a_partial_void_does_not_close_the_grant():
    """`refundType` 2 is a quantity-based partial void.

    We sell nothing with a quantity above one, so it cannot fire today. It is
    mapped anyway because the cost of being wrong is asymmetric: a partial read
    as full repossesses a reading somebody still owns.
    """
    adapter = _adapter()
    event = await adapter.enrich(adapter.parse(_push(_voided_notification(refund_type=2))))
    assert event.adjustment == ("refund", "partial")
    assert event.closes_the_grant is False


async def test_a_one_time_purchase_notification_grants():
    adapter = _adapter(product=_product_state())
    sku = store_product_id("natal", processor="googleplay")
    event = await adapter.enrich(adapter.parse(_push(_one_time_notification(1, sku=sku))))

    assert event.kind is EventKind.PAYMENT
    assert event.product == "natal"
    assert event.grants is True
    assert entitlement_for.__doc__  # the delegation is documented, not duplicated


async def test_a_test_notification_records_itself_and_costs_no_api_call():
    """The button in the Play Console, which is what it is for."""
    adapter = _adapter()
    notification = {
        "version": "1.0",
        "packageName": PACKAGE,
        "eventTimeMillis": str(int(time.time() * 1000)),
        "testNotification": {"version": "1.0"},
    }
    event = await adapter.enrich(adapter.parse(_push(notification)))
    assert event.grants is False and event.revokes is False
    assert event.transaction_id is None
    assert adapter.client.calls == []


def test_the_delivery_id_is_the_message_id():
    """Google asks for deduplication on it, and says it saves API quota too.

    That second half is why `enrich` runs after the idempotency check rather
    than inside `parse`.
    """
    event = parse(_push(_subscription_notification(2), message_id="4242424242"))
    assert event.id == "4242424242"


def test_every_notification_type_is_either_acted_on_or_explained():
    """No type may be merely unmentioned. Five of the ignored ones look like
    revocations, and requiring a written reason is what makes adding a line to
    `REVOKING` a decision rather than a reflex."""
    documented = {f"subscription.{code}" for code in
                  (1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 17, 18, 19, 20)}
    documented |= {"one_time_product.1", "one_time_product.2", "voided_purchase", "test"}
    named = googleplay.GRANTING | googleplay.REVOKING | set(googleplay.IGNORED_REASONS)
    assert not documented - named, f"unmentioned: {sorted(documented - named)}"


# ══════════════════════════════════════════════════════════════════════════
#  The shape of the adapter
# ══════════════════════════════════════════════════════════════════════════

def test_the_adapter_is_a_store_provider():
    from alma.billing.provider import BillingProvider, StoreProvider

    adapter = GooglePlayProvider()
    assert isinstance(adapter, BillingProvider)
    assert isinstance(adapter, StoreProvider)
    assert GooglePlayProvider.name == "googleplay"


def test_the_factory_hands_back_this_adapter_when_the_configuration_asks():
    from alma.billing.provider import provider_for

    assert isinstance(provider_for("googleplay"), GooglePlayProvider)


def test_the_vocabulary_is_shared_and_not_merely_similar():
    from alma.billing import paddle, provider

    assert googleplay.Grant is paddle.Grant is provider.Grant
    assert googleplay.InvalidSignature is provider.InvalidSignature


async def test_there_is_no_server_created_checkout():
    with pytest.raises(BillingUnavailable, match="Play Billing"):
        await GooglePlayProvider().open_session(
            product="natal", user_id="u1", currency="USD"
        )


async def test_cancelling_hands_back_the_place_the_customer_can_do_it():
    """Play *does* expose a cancel and we deliberately do not call it.

    It needs the purchase token, which is 20 times too long for any identifier
    column we keep; and it would be a second cancellation path for one
    subscription, whose failure mode is somebody who cancelled in Play being
    told by us that their plan renews.
    """
    with pytest.raises(SelfServiceOnly) as raised:
        await GooglePlayProvider().cancel_subscription(ORDER)
    assert raised.value.manage_url.startswith("https://play.google.com/")
    assert PACKAGE in raised.value.manage_url
    assert isinstance(raised.value, BillingUnavailable)


def test_the_service_account_may_be_json_or_a_path(tmp_path):
    """Both, because both are how people deploy: a secret store hands over a
    string and a mounted volume hands over a path. A second variable saying
    which would be one more thing to get wrong."""
    credentials = {"client_email": "a@b.iam.gserviceaccount.com", "private_key": "-----x"}
    path = tmp_path / "sa.json"
    path.write_text(json.dumps(credentials))

    assert googleplay._service_account(json.dumps(credentials)) == credentials
    assert googleplay._service_account(str(path)) == credentials
    assert googleplay._service_account("") is None
    assert googleplay._service_account("/nowhere/at/all.json") is None


async def test_google_is_asked_for_no_address_and_sends_the_receipt_itself():
    from alma.billing.provider import NormalisedEvent

    adapter = GooglePlayProvider()
    assert adapter.issues_the_receipt is True
    assert await adapter.buyer_address(
        NormalisedEvent(
            provider="googleplay", id="x", type="purchase", kind=EventKind.PAYMENT
        )
    ) is None
