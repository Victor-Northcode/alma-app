"""The App Store adapter, probed the way the Paddle and Dodo ones are.

Same adversary, a completely different scheme. There is no shared secret with
Apple, so the questions change shape: not "did somebody forge an HMAC" but
"will this accept a certificate chain that vouches for itself", "will it accept
a real Apple signature over *another app's* purchase", and "will it grant the
same transaction twice when StoreKit replays it, which StoreKit does on every
launch".

**The chain is real and the root is not Apple's.** A test cannot mint a
certificate under Apple Root CA - G3 — that is the entire point of pinning it —
so the pin is swapped for a root these tests generate, and every certificate,
signature and rejection below is genuine ECDSA over a genuine X.509 chain. One
test then checks the shipped pin separately, by its own fingerprint, so the
substitution cannot hide a mangled paste.

**The fixtures are documented shapes, not captured traffic.** No purchase has
ever completed through this code. Every payload is assembled from Apple's
published models — `JWSTransactionDecodedPayload` and
`responseBodyV2DecodedPayload` — and a field that is not in those is not here.
When a real transaction first lands, the thing to check is that it has no field
these do not.
"""

from __future__ import annotations

import base64
import json
import time
from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils as asym_utils
from cryptography.x509.oid import NameOID

from alma.billing import appstore
from alma.billing.appstore import (
    AppStoreProvider,
    InvalidSignature,
    decode_transaction,
    entitlement_for,
    parse,
)
from alma.billing.provider import (
    BillingUnavailable,
    EventKind,
    ProductMismatch,
    PurchaseIncomplete,
    SelfServiceOnly,
    store_product_id,
)

BUNDLE = "com.alma.app"


# ── a certificate authority we control, standing in for Apple's ────────────


def _authority(name: str, *, issuer=None, issuer_key=None, ca: bool = True):
    """One EC certificate, self-signed or signed by the pair handed in.

    Written out rather than mocked. The whole question this file exists to ask
    is whether `_check_chain` actually verifies signatures, and a mock chain
    would answer it by construction.
    """
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer.subject if issuer is not None else subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
    )
    certificate = builder.sign(issuer_key or key, hashes.SHA256())
    return key, certificate


@pytest.fixture
def apple(monkeypatch):
    """A three-link chain, with our root pinned in place of Apple's.

    Returns the pieces a test needs to sign something, plus a rogue root that
    verifies perfectly and chains nowhere — which is the forgery this adapter
    has to refuse and the one an `hmac`-shaped mind does not think of.
    """
    root_key, root = _authority("Test Root CA")
    intermediate_key, intermediate = _authority(
        "Test Intermediate", issuer=root, issuer_key=root_key
    )
    leaf_key, leaf = _authority(
        "Test Leaf", issuer=intermediate, issuer_key=intermediate_key, ca=False
    )

    rogue_root_key, rogue_root = _authority("Rogue Root CA")
    rogue_key, rogue_leaf = _authority(
        "Rogue Leaf", issuer=rogue_root, issuer_key=rogue_root_key, ca=False
    )

    monkeypatch.setattr(
        appstore,
        "APPLE_ROOT_CA_G3_PEM",
        root.public_bytes(serialization.Encoding.PEM),
    )
    return {
        "chain": [leaf, intermediate, root],
        "key": leaf_key,
        "rogue_chain": [rogue_leaf, rogue_root],
        "rogue_key": rogue_key,
    }


def _sign(payload: dict, key, chain, *, alg: str = "ES256") -> str:
    """Assemble a JWS the way RFC 7515 says to, from the spec rather than from us.

    `x5c` is standard base64 and the segments are base64url — a difference that
    costs nothing until a certificate contains a `+`, and then one delivery in
    a few fails with a message that reads like an attack.

    The signature is raw `r || s`, which is the JWS encoding of ECDSA, not the
    DER `cryptography` produces. A test that asked the module to sign would
    prove only that the module is self-consistent.
    """
    header = {
        "alg": alg,
        "x5c": [
            base64.b64encode(certificate.public_bytes(serialization.Encoding.DER)).decode()
            for certificate in chain
        ],
    }
    encoded_header = _segment(header)
    encoded_payload = _segment(payload)
    der = key.sign(f"{encoded_header}.{encoded_payload}".encode(), ec.ECDSA(hashes.SHA256()))
    r, s = asym_utils.decode_dss_signature(der)
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{encoded_header}.{encoded_payload}.{_raw(raw)}"


def _segment(value: dict) -> str:
    return _raw(json.dumps(value, separators=(",", ":")).encode())


def _raw(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


# ── the documented payload shapes ──────────────────────────────────────────


def _transaction(
    *,
    product: str = "door.natal",
    transaction_id: str = "2000000500000001",
    original: str | None = None,
    kind: str = "Non-Consumable",
    bundle: str = BUNDLE,
    environment: str = "Production",
    price: int | None = 5990,
    expires_in_days: int | None = None,
    revoked: bool = False,
) -> dict:
    """A `JWSTransactionDecodedPayload`, in Apple's own field names."""
    now = int(time.time() * 1000)
    payload: dict = {
        "transactionId": transaction_id,
        "originalTransactionId": original or transaction_id,
        "bundleId": bundle,
        "productId": store_product_id(product, processor="appstore"),
        "purchaseDate": now,
        "originalPurchaseDate": now,
        "quantity": 1,
        "type": kind,
        "inAppOwnershipType": "PURCHASED",
        "signedDate": now,
        "environment": environment,
        "storefront": "USA",
        "storefrontId": "143441",
        "transactionReason": "PURCHASE",
    }
    if price is not None:
        # Milliunits, which is Apple's unit and not anybody else's: $5.99 is
        # 5990 and reading it as cents is a fifty-nine dollar purchase.
        payload["price"] = price
        payload["currency"] = "USD"
    if expires_in_days is not None:
        payload["expiresDate"] = now + expires_in_days * 86_400_000
    if revoked:
        payload["revocationDate"] = now
        payload["revocationReason"] = 0
    return payload


def _notification(
    apple, *, kind: str, subtype: str = "", transaction: dict | None = None,
    uuid: str = "8ad5a2f0-0000-4000-8000-000000000001",
) -> dict:
    """The body Apple POSTs: `{"signedPayload": "<JWS>"}` and nothing else."""
    data: dict = {
        "appAppleId": 1234567890,
        "bundleId": BUNDLE,
        "bundleVersion": "1",
        "environment": "Production",
    }
    if transaction is not None:
        data["signedTransactionInfo"] = _sign(transaction, apple["key"], apple["chain"])
    body: dict = {
        "notificationType": kind,
        "notificationUUID": uuid,
        "version": "2.0",
        "signedDate": int(time.time() * 1000),
        "data": data,
    }
    if subtype:
        body["subtype"] = subtype
    return {"signedPayload": _sign(body, apple["key"], apple["chain"])}


@pytest.fixture(autouse=True)
def _bundle(monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("APPLE_BUNDLE_ID", BUNDLE)
    config_module.settings.cache_clear()
    yield
    config_module.settings.cache_clear()


# ══════════════════════════════════════════════════════════════════════════
#  The pin itself
# ══════════════════════════════════════════════════════════════════════════

def test_the_shipped_pin_really_is_apple_root_ca_g3():
    """The one test the fake-root fixture cannot cover.

    Every other case here swaps the pin for a root we made, so a `PEM` constant
    that had lost a line to a wrapping editor would still pass all of them and
    fail on the first real purchase — as "signature does not match", which reads
    as an attack rather than as a paste. This checks the bytes we ship.
    """
    certificate = x509.load_pem_x509_certificate(appstore.APPLE_ROOT_CA_G3_PEM)
    assert certificate.fingerprint(hashes.SHA256()).hex() == (
        "63343abfb89a6a03ebb57e9b3f5fa7be7c4f5c756f3017b3a8c488c3653e9179"
    )
    assert "Apple Root CA - G3" in certificate.subject.rfc4514_string()
    # Self-signed, which is what a root is. An "Apple root" that named another
    # issuer would be an intermediate, and pinning one of those means every
    # rotation Apple makes is an outage.
    assert certificate.subject == certificate.issuer


# ══════════════════════════════════════════════════════════════════════════
#  Forgery
# ══════════════════════════════════════════════════════════════════════════

def test_a_chain_that_vouches_for_itself_is_refused(apple):
    """The forgery an HMAC-shaped mind does not think of.

    Everything about this token is internally valid: a real EC key, a real
    self-signed CA, a real certificate under it, a real ES256 signature over a
    real payload. It is refused for the one reason that matters — the chain
    ends somewhere we never agreed to trust. Reading the root out of `x5c`
    instead of out of this file would accept it.
    """
    forged = _sign(_transaction(), apple["rogue_key"], apple["rogue_chain"])
    with pytest.raises(InvalidSignature):
        decode_transaction(forged)


def test_a_leaf_borrowed_from_apples_chain_does_not_help(apple):
    """Presenting Apple's real chain while signing with another key.

    The chain verifies to our pinned root perfectly; the payload signature does
    not, because the signer does not hold the leaf's key. This is what a
    captured transaction re-signed with different contents looks like.
    """
    forged = _sign(_transaction(), apple["rogue_key"], apple["chain"])
    with pytest.raises(InvalidSignature, match="signature does not match"):
        decode_transaction(forged)


def test_a_tampered_payload_is_refused(apple):
    """One character changed in the product id, after signing."""
    token = _sign(_transaction(product="door.natal"), apple["key"], apple["chain"])
    header, payload, signature = token.split(".")
    swapped = _segment({**_transaction(), "productId": store_product_id(
        "bundle.static", processor="appstore"
    )})
    with pytest.raises(InvalidSignature, match="signature does not match"):
        decode_transaction(f"{header}.{swapped}.{signature}")
    # ...and the untouched one still verifies, so the assertion above is about
    # the tampering rather than about the fixture being broken.
    assert decode_transaction(token)["productId"].endswith("door.natal")


def test_alg_none_is_refused(apple):
    """The oldest JWS attack there is: the token naming its own algorithm.

    A verifier that obeys `alg` accepts `none`, and every signature in the
    system becomes decoration. The header is read before the signature — it has
    to be, the key is in it — which is exactly why this comparison exists.
    """
    token = _sign(_transaction(), apple["key"], apple["chain"], alg="none")
    with pytest.raises(InvalidSignature, match="alg"):
        decode_transaction(token)


def test_something_that_is_not_a_jws_at_all_is_refused(apple):
    for rubbish in ("", "not-a-token", "a.b", "a.b.c.d", "...."):
        with pytest.raises(InvalidSignature):
            decode_transaction(rubbish)


def test_an_expired_certificate_is_refused(monkeypatch, apple):
    """A chain that verified yesterday and does not today."""
    token = _sign(_transaction(), apple["key"], apple["chain"])
    with pytest.raises(InvalidSignature, match="validity window"):
        decode_transaction(token, now=datetime.now(UTC) + timedelta(days=400))


# ══════════════════════════════════════════════════════════════════════════
#  Another app's purchase
# ══════════════════════════════════════════════════════════════════════════

def test_a_transaction_for_another_apps_bundle_is_refused(apple):
    """A genuine Apple signature over a genuine purchase of something else.

    This is not hypothetical and it is not hard: every App Store app hands its
    own users signed transactions, and one of them POSTed here would otherwise
    unlock a reading for the price of a flashlight. There is no shared secret
    with Apple, so the bundle id is the entire credential.
    """
    token = _sign(_transaction(bundle="com.someone.else"), apple["key"], apple["chain"])
    with pytest.raises(InvalidSignature, match="com.someone.else"):
        decode_transaction(token)


def test_no_bundle_id_configured_refuses_rather_than_accepting_everything(
    monkeypatch, apple
):
    """A missing credential must not read as "accept any bundle".

    The failure this prevents is silent: with no configured bundle, a comparison
    written as `expected and bundle != expected` accepts every app on the store,
    and nothing in a log says so.
    """
    from alma import config as config_module

    monkeypatch.delenv("APPLE_BUNDLE_ID", raising=False)
    config_module.settings.cache_clear()
    token = _sign(_transaction(), apple["key"], apple["chain"])
    with pytest.raises(BillingUnavailable, match="APPLE_BUNDLE_ID"):
        decode_transaction(token)


def test_a_sandbox_transaction_is_accepted_by_default(apple):
    """Because App Review runs the production build against sandbox StoreKit.

    Refusing here is a rejected app. It is a real exposure and the comment on
    `ALMA_APPLE_ACCEPT_SANDBOX` says so; what makes it survivable is that the
    environment is recorded, which the next assertion checks.
    """
    token = _sign(_transaction(environment="Sandbox"), apple["key"], apple["chain"])
    assert decode_transaction(token)["environment"] == "Sandbox"

    event = parse(_notification(apple, kind="ONE_TIME_CHARGE", transaction=_transaction(
        environment="Sandbox"
    ))).normalise()
    assert event.status == "Sandbox"


def test_a_sandbox_transaction_is_refused_when_the_flag_is_off(monkeypatch, apple):
    from alma import config as config_module

    monkeypatch.setenv("ALMA_APPLE_ACCEPT_SANDBOX", "false")
    config_module.settings.cache_clear()
    token = _sign(_transaction(environment="Sandbox"), apple["key"], apple["chain"])
    with pytest.raises(InvalidSignature, match="Sandbox"):
        decode_transaction(token)


# ══════════════════════════════════════════════════════════════════════════
#  Claiming the wrong thing
# ══════════════════════════════════════════════════════════════════════════

async def test_a_product_mismatch_is_refused(apple):
    """The store equivalent of the price check, and the reason it is needed.

    On a card processor the lie available to a client is a price id; here the
    price is Apple's and cannot be touched, so the only lie left is the claim.
    Buy the $5.99 door, ask for the $38.99 archive. Apple's signature over
    `productId` is what refuses it.
    """
    token = _sign(_transaction(product="door.natal"), apple["key"], apple["chain"])
    with pytest.raises(ProductMismatch, match="door.natal"):
        await AppStoreProvider().verify_purchase(transaction=token, product="bundle.static")


async def test_a_product_the_price_list_does_not_sell_is_refused(apple):
    """An id from an older price list, or one created in Connect by hand."""
    payload = {**_transaction(), "productId": "alma.something_we_withdrew"}
    token = _sign(payload, apple["key"], apple["chain"])
    with pytest.raises(ProductMismatch):
        await AppStoreProvider().verify_purchase(transaction=token, product="door.natal")


async def test_a_revoked_transaction_is_refused(apple):
    """A refunded purchase presented as a fresh one.

    Not `InvalidSignature`: the signature is perfect and Apple is the one saying
    the purchase is gone. The two are different incidents and the second is not
    an attack, which is why the exception and the status code differ.
    """
    token = _sign(_transaction(revoked=True), apple["key"], apple["chain"])
    with pytest.raises(PurchaseIncomplete, match="revoked"):
        await AppStoreProvider().verify_purchase(transaction=token, product="door.natal")


async def test_a_door_purchase_grants_its_system_and_only_that(apple):
    token = _sign(_transaction(product="door.natal"), apple["key"], apple["chain"])
    event = await AppStoreProvider().verify_purchase(transaction=token, product="door.natal")

    assert event.provider == "appstore"
    assert event.transaction_id == "2000000500000001"
    assert event.id == "appstore:2000000500000001"
    assert event.grants and event.moves_money
    # Apple's price in milliunits, read as minor units. $5.99, not $59.90.
    assert event.amount_cents == 599

    from alma.billing.provider import entitlement_for as grant_for

    grant = grant_for(event)
    assert (grant.system, grant.kind, grant.scope, grant.duration) == (
        "natal", "one_time", "system", None
    )
    # A non-consumable is not a plan. Filing one as a subscription would let
    # `entitlements.grant` extend a permanent purchase in place, and would offer
    # a cancel button for a chapter somebody owns outright.
    assert grant.subscription_id is None


async def test_a_subscription_purchase_carries_the_id_every_renewal_will_share(apple):
    token = _sign(
        _transaction(
            product="sub.monthly",
            transaction_id="2000000500000002",
            original="2000000500000002",
            kind="Auto-Renewable Subscription",
            price=9990,
            expires_in_days=31,
        ),
        apple["key"],
        apple["chain"],
    )
    event = await AppStoreProvider().verify_purchase(transaction=token, product="sub.monthly")

    from alma.billing.provider import entitlement_for as grant_for

    grant = grant_for(event)
    assert grant.subscription_id == "2000000500000002"
    # `all`, а не `live`: подписка v3 продаёт всё, пока активна.
    assert grant.scope == "all"
    assert grant.duration is not None and 28 <= grant.duration.days <= 31
    assert event.renews_at is not None


async def test_the_store_price_is_never_checked_against_our_catalogue(apple):
    """A ¥900 door has to grant, and comparing it to `REGIONAL_CENTS` refuses it.

    Apple sets the price per storefront from a tier we chose; the yen amount
    appears in no row of our own price list, and converting one into the other
    is the request-time arithmetic `catalogue.py` exists to forbid. What guards
    the grant instead is the signed product id, which the mismatch tests cover.
    """
    yen = {**_transaction(product="door.natal", price=900_000), "currency": "JPY"}
    token = _sign(yen, apple["key"], apple["chain"])
    event = await AppStoreProvider().verify_purchase(transaction=token, product="door.natal")

    from alma.billing.provider import entitlement_for as grant_for

    assert (event.currency, event.amount_cents) == ("JPY", 90_000)
    assert event.priced_by_us is False
    # The catalogue does not price anything in yen at all, so a comparison would
    # raise `NotSold` and refuse the grant. It grants.
    assert grant_for(event) is not None


# ══════════════════════════════════════════════════════════════════════════
#  Notifications: the three that look like revocations and the one that is
# ══════════════════════════════════════════════════════════════════════════

def test_a_renewal_extends_the_same_subscription(apple):
    """A renewal has to name the plan, not the charge.

    Every renewal is a fresh `transactionId`, so a grant keyed on that writes
    one row a month — and a cancellation then catches only the last of them,
    leaving every earlier row with a future expiry and still granting.
    """
    event = parse(
        _notification(
            apple,
            kind="DID_RENEW",
            transaction=_transaction(
                product="sub.monthly",
                transaction_id="2000000500000099",
                original="2000000500000002",
                kind="Auto-Renewable Subscription",
                price=9990,
                expires_in_days=31,
            ),
            uuid="8ad5a2f0-0000-4000-8000-00000000dddd",
        )
    )
    grant = entitlement_for(event)

    assert event.normalise().kind is EventKind.SUBSCRIPTION_RENEWED
    assert grant.subscription_id == "2000000500000002"
    assert grant.duration is not None
    assert event.normalise().transaction_id == "2000000500000099"


def test_a_cancellation_does_not_revoke(apple):
    """Auto-renewal off is a cancellation, and cancelling is not refunding.

    Somebody who turns it off on the 3rd has paid through the end of the period
    and is owed every day of it. Revoking here is charging for a month and
    delivering three days — and it is the click most likely to be followed by a
    chargeback. What the event does change is `renews_at`, so the account screen
    stops promising a charge that will not happen.
    """
    event = parse(
        _notification(
            apple,
            kind="DID_CHANGE_RENEWAL_STATUS",
            subtype="AUTO_RENEW_DISABLED",
            transaction=_transaction(
                product="sub.monthly",
                kind="Auto-Renewable Subscription",
                expires_in_days=20,
            ),
        )
    ).normalise()

    assert event.kind is EventKind.SUBSCRIPTION_CANCELLED
    assert event.revokes is False
    assert event.grants is False
    assert "DID_CHANGE_RENEWAL_STATUS" not in appstore.REVOKING


def test_turning_renewal_back_on_is_not_a_cancellation_and_grants_nothing(apple):
    """The same notification type, the opposite meaning.

    Mapping it by type alone would have `_note_the_plan` clear `renews_at` on
    the event that restores it. Mapping it as a grant would hand a free period
    to anybody willing to flip the switch twice.
    """
    event = parse(
        _notification(
            apple,
            kind="DID_CHANGE_RENEWAL_STATUS",
            subtype="AUTO_RENEW_ENABLED",
            transaction=_transaction(
                product="sub.monthly", kind="Auto-Renewable Subscription", expires_in_days=20
            ),
        )
    ).normalise()

    assert event.kind is EventKind.SUBSCRIPTION_UPDATED
    assert event.revokes is False and event.grants is False


def test_a_billing_retry_revokes_nothing(apple):
    """Dunning. Apple is still trying the card, and the subtypes say so."""
    for subtype in ("BILLING_RETRY", "GRACE_PERIOD"):
        event = parse(
            _notification(
                apple,
                kind="DID_FAIL_TO_RENEW",
                subtype=subtype,
                transaction=_transaction(
                    product="sub.monthly", kind="Auto-Renewable Subscription"
                ),
            )
        ).normalise()
        assert event.kind is EventKind.SUBSCRIPTION_DUNNING
        assert event.revokes is False and event.grants is False


def test_a_refund_closes_the_grant(apple):
    """The one that does revoke, and the only one that should.

    Apple refunds a whole transaction or none of it — there is no partial shape
    in `JWSTransactionDecodedPayload` — so every return here is full and closes
    what it paid for.
    """
    event = parse(
        _notification(
            apple,
            kind="REFUND",
            transaction=_transaction(product="door.natal"),
        )
    ).normalise()

    assert event.kind is EventKind.ADJUSTMENT
    assert event.revokes is True
    assert event.adjustment == ("refund", "full")
    assert event.returns_money and event.closes_the_grant
    assert event.moves_money is True


def test_family_sharing_being_revoked_takes_access_without_taking_money(apple):
    event = parse(
        _notification(apple, kind="REVOKE", transaction=_transaction(product="door.natal"))
    ).normalise()

    assert event.revokes is True
    # Nothing came back, so nothing may be written into the refund column —
    # doing so would overstate refunds by the price of every shared purchase.
    assert event.adjustment is None
    assert event.moves_money is False


def test_an_expiry_ends_the_plan(apple):
    event = parse(
        _notification(
            apple,
            kind="EXPIRED",
            subtype="VOLUNTARY",
            transaction=_transaction(
                product="sub.monthly", kind="Auto-Renewable Subscription", expires_in_days=0
            ),
        )
    ).normalise()
    assert event.kind is EventKind.SUBSCRIPTION_ENDED
    assert event.revokes is True


def test_a_test_notification_records_itself_and_grants_nothing(apple):
    """The button in App Store Connect, which is what it is for."""
    event = parse(_notification(apple, kind="TEST")).normalise()
    assert event.grants is False and event.revokes is False
    assert event.kind is EventKind.UNKNOWN
    assert event.transaction_id is None


def test_a_notification_for_another_app_is_refused(apple):
    """The envelope carries a bundle id of its own, and it is checked too.

    Verifying only the inner transaction would leave a real Apple notification
    about somebody else's app being recorded against our webhook table.
    """
    body = {
        "notificationType": "REFUND",
        "notificationUUID": "8ad5a2f0-0000-4000-8000-00000000eeee",
        "version": "2.0",
        "signedDate": int(time.time() * 1000),
        "data": {"bundleId": "com.someone.else", "environment": "Production"},
    }
    with pytest.raises(InvalidSignature, match="com.someone.else"):
        parse({"signedPayload": _sign(body, apple["key"], apple["chain"])})


def test_every_notification_type_is_either_acted_on_or_explained():
    """No type may be merely unmentioned.

    Four of the ignored ones look exactly like revocations. Requiring a written
    reason for each is what makes adding a line to `REVOKING` a decision rather
    than a reflex.
    """
    documented = {
        "SUBSCRIBED", "DID_RENEW", "DID_CHANGE_RENEWAL_STATUS", "DID_CHANGE_RENEWAL_PREF",
        "DID_FAIL_TO_RENEW", "EXPIRED", "GRACE_PERIOD_EXPIRED", "REFUND", "REFUND_DECLINED",
        "REFUND_REVERSED", "REVOKE", "CONSUMPTION_REQUEST", "PRICE_INCREASE",
        "RENEWAL_EXTENDED", "RENEWAL_EXTENSION", "OFFER_REDEEMED", "ONE_TIME_CHARGE",
        "EXTERNAL_PURCHASE_TOKEN", "TEST",
    }
    named = appstore.GRANTING | appstore.REVOKING | set(appstore.IGNORED_REASONS)
    assert not documented - named, f"unmentioned: {sorted(documented - named)}"


# ══════════════════════════════════════════════════════════════════════════
#  The shape of the adapter
# ══════════════════════════════════════════════════════════════════════════

def test_the_adapter_is_a_store_provider():
    from alma.billing.provider import BillingProvider, StoreProvider

    adapter = AppStoreProvider()
    assert isinstance(adapter, BillingProvider)
    assert isinstance(adapter, StoreProvider)
    assert AppStoreProvider.name == "appstore"


def test_the_factory_hands_back_this_adapter_when_the_configuration_asks():
    from alma.billing.provider import provider_for

    assert isinstance(provider_for("appstore"), AppStoreProvider)


def test_the_vocabulary_is_shared_and_not_merely_similar():
    """One `InvalidSignature`, one `Grant`, across all four adapters.

    Two same-named exception classes would both look right and only one would be
    caught by the router's `except`, which is the shape of a webhook endpoint
    that accepts everything.
    """
    from alma.billing import dodo, paddle, provider

    assert appstore.Grant is paddle.Grant is dodo.Grant is provider.Grant
    assert appstore.InvalidSignature is provider.InvalidSignature
    assert appstore.PERIOD is provider.PERIOD


async def test_there_is_no_server_created_checkout():
    """Refused loudly rather than faked into a URL nothing can open."""
    with pytest.raises(BillingUnavailable, match="StoreKit"):
        await AppStoreProvider().open_session(
            product="door.natal", user_id="u1", currency="USD"
        )


async def test_cancelling_hands_back_the_place_the_customer_can_do_it():
    """Apple exposes no cancel API, so the honest answer is a link.

    Not a `BillingUnavailable` the router turns into "we could not reach the
    payment processor" — nothing failed. And nothing is written, which is the
    important half: recording a cancellation Apple never heard of would tell the
    account screen the plan had stopped renewing while it went on renewing.
    """
    with pytest.raises(SelfServiceOnly) as raised:
        await AppStoreProvider().cancel_subscription("2000000500000002")
    assert raised.value.manage_url.startswith("https://apps.apple.com/")
    assert isinstance(raised.value, BillingUnavailable)


async def test_apple_is_asked_for_no_address_and_sends_the_receipt_itself():
    """No address, and no incident either.

    A card payment with no address is a real alarm: that buyer's withdrawal
    waiver is incomplete and they keep their 14 days. A store payment with no
    address is Tuesday, because Apple is the seller and the confirmation is
    Apple's. `issues_the_receipt` is what keeps the first sentence from being
    logged about the second.
    """
    from alma.billing.provider import NormalisedEvent

    adapter = AppStoreProvider()
    assert adapter.issues_the_receipt is True
    assert await adapter.buyer_address(
        NormalisedEvent(
            provider="appstore", id="x", type="purchase", kind=EventKind.PAYMENT
        )
    ) is None
