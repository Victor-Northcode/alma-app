"""Apple, behind the seam: StoreKit 2 transactions and Server Notifications V2.

Apple is the third implementation of `provider.py`, and it is the one that made
the seam worth having. Paddle's acceptable-use policy names our category —
"clairvoyance, horoscopes, fortune-telling" — as prohibited outright, and
FastSpring and 2Checkout copy the clause. Apple's App Review Guidelines
*permit* astrology apps. So the processor hunt ends here, and the price of that
is a shape that differs from a card processor in four specific ways, all of
which are named in `provider.py` and none of which leaks past this file.

**There is no shared secret and no webhook signature to check.** That sentence
is the whole security model. A card processor and we agree on a key; Apple does
not agree on anything with us. What arrives is a **JWS** — a JSON Web Signature
— whose header carries `x5c`, a chain of X.509 certificates. The leaf signs the
payload with ES256; the leaf is signed by an Apple intermediate; the
intermediate is signed by **Apple Root CA - G3**, which is pinned in this file
by its own bytes. Nothing here trusts a certificate because it arrived in the
`x5c` header — a chain that vouches for itself is a chain an attacker writes.

**The bundle id is the credential.** A valid Apple signature proves Apple signed
it, not that it is *ours*: anyone with an App Store app gets Apple-signed
transactions, and one of them handed to this endpoint would otherwise unlock a
reading. So the decoded `bundleId` is compared against `APPLE_BUNDLE_ID` and
anything else is refused as hard as a forgery.

**The purchase is not a notification.** StoreKit hands the app a signed
transaction the instant the sheet closes; `ASSNv2` for the same purchase may be
seconds or minutes behind, and the person is standing there having paid. So
`verify_purchase` exists, the client calls it, and the notification that arrives
later is idempotent against it — see `Event.id`.

Sources, read rather than recalled:
* App Store Server API — JWSTransaction and JWSTransactionDecodedPayload
  (https://developer.apple.com/documentation/appstoreserverapi/jwstransaction)
* App Store Server Notifications V2 — responseBodyV2, notificationType, subtype
  (https://developer.apple.com/documentation/appstoreservernotifications/notificationtype)
* Apple Root CA - G3, from https://www.apple.com/certificateauthority/

No credentials appear in this file. `APPLE_BUNDLE_ID` comes from the
environment; there is no key to leak, because verification is against Apple's
own public root.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography import x509
from cryptography.exceptions import InvalidSignature as _CryptoInvalidSignature
from cryptography.hazmat.primitives.asymmetric import ec, utils as asym_utils
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import Encoding

from ..config import settings
from .provider import (
    PERIOD,
    BillingUnavailable,
    EventKind,
    Grant,
    InvalidSignature,
    NormalisedEvent,
    ProductMismatch,
    PurchaseIncomplete,
    SelfServiceOnly,
    SessionHandle,
    moment,
    store_slug,
)
from .provider import entitlement_for as _entitlement_for

log = logging.getLogger("alma.billing")

#: Re-exported so `appstore.Grant` is the same object as `paddle.Grant`. Two
#: `InvalidSignature` classes with one name would both look right and only one
#: would be caught by the router's `except`, which is the shape of a webhook
#: endpoint that accepts everything.
__all__ = [
    "APPLE_ROOT_CA_G3_PEM",
    "GRANTING",
    "PERIOD",
    "REVOKING",
    "AppStoreProvider",
    "Event",
    "Grant",
    "InvalidSignature",
    "decode_transaction",
    "entitlement_for",
    "parse",
    "verify",
]

#: **Apple Root CA - G3**, the trust anchor every StoreKit signature has to
#: reach. Pinned as bytes rather than fetched, and rather than taken from the
#: operating system's trust store: a JWS is only as trustworthy as the root it
#: chains to, and "whatever this container image happens to trust" is a set that
#: changes with a base-image bump and contains several hundred authorities we
#: have no relationship with. Any one of them could sign a certificate for a
#: leaf that then signs a transaction granting the archive.
#:
#: Downloaded from https://www.apple.com/certificateauthority/AppleRootCA-G3.cer
#: on 6 August 2026. Its own SHA-256 fingerprint is
#: 63343abfb89a6a03ebb57e9b3f5fa7be7c4f5c756f3017b3a8c488c3653e9179, which
#: `test_billing_appstore.py` recomputes from these bytes — so a paste that
#: silently lost a character fails a test rather than every purchase.
#: Subject and issuer are both "CN=Apple Root CA - G3, OU=Apple Certification
#: Authority, O=Apple Inc., C=US"; it expires 30 April 2039.
APPLE_ROOT_CA_G3_PEM = b"""-----BEGIN CERTIFICATE-----
MIICQzCCAcmgAwIBAgIILcX8iNLFS5UwCgYIKoZIzj0EAwMwZzEbMBkGA1UEAwwS
QXBwbGUgUm9vdCBDQSAtIEczMSYwJAYDVQQLDB1BcHBsZSBDZXJ0aWZpY2F0aW9u
IEF1dGhvcml0eTETMBEGA1UECgwKQXBwbGUgSW5jLjELMAkGA1UEBhMCVVMwHhcN
MTQwNDMwMTgxOTA2WhcNMzkwNDMwMTgxOTA2WjBnMRswGQYDVQQDDBJBcHBsZSBS
b290IENBIC0gRzMxJjAkBgNVBAsMHUFwcGxlIENlcnRpZmljYXRpb24gQXV0aG9y
aXR5MRMwEQYDVQQKDApBcHBsZSBJbmMuMQswCQYDVQQGEwJVUzB2MBAGByqGSM49
AgEGBSuBBAAiA2IABJjpLz1AcqTtkyJygRMc3RCV8cWjTnHcFBbZDuWmBSp3ZHtf
TjjTuxxEtX/1H7YyYl3J6YRbTzBPEVoA/VhYDKX1DyxNB0cTddqXl5dvMVztK517
IDvYuVTZXpmkOlEKMaNCMEAwHQYDVR0OBBYEFLuw3qFYM4iapIqZ3r6966/ayySr
MA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgEGMAoGCCqGSM49BAMDA2gA
MGUCMQCD6cHEFl4aXTQY2e3v9GwOAEZLuN+yRhHFD/3meoyhpmvOwgPUnPWTxnS4
at+qIxUCMG1mihDK1A3UT82NQz60imOlM27jbdoXt2QfyFMm+YhidDkLF1vLUagM
6BgD56KyKA==
-----END CERTIFICATE-----
"""

#: The only algorithm we accept in a JWS header. Named and compared rather than
#: read and used, because the classic JWS attack is an `alg` the verifier
#: obeys — `none`, or an RSA name against an EC key.
SIGNING_ALGORITHM = "ES256"

#: Where a customer manages the subscription. Apple exposes no cancel API at
#: all: an auto-renewable subscription belongs to the Apple ID rather than to
#: our account, and this URL is the only place it can be stopped.
MANAGE_URL = "https://apps.apple.com/account/subscriptions"

#: How many certificates a chain may carry. Apple sends three — leaf,
#: intermediate, root — and a bound exists because each link costs a signature
#: verification and the list arrives from the network.
MAX_CHAIN = 6

#: Apple's word for a real purchase, and for App Review's.
PRODUCTION = "Production"
SANDBOX = "Sandbox"

#: The product types that renew on their own. Read from the transaction rather
#: than inferred from our catalogue, so that a product miscreated in App Store
#: Connect as a one-off is caught here instead of granting a permanent
#: everything to somebody paying monthly.
AUTO_RENEWABLE = "Auto-Renewable Subscription"


# ── the JWS, and the chain behind it ───────────────────────────────────────


def _b64url(segment: str) -> bytes:
    """One JWS segment's bytes. Padding is rebuilt; JWS omits it."""
    try:
        return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except (binascii.Error, ValueError) as exc:
        raise InvalidSignature("a JWS segment is not base64url") from exc


def _certificates(header: dict) -> list[x509.Certificate]:
    """The `x5c` chain, as certificates, leaf first.

    `x5c` is standard base64 (RFC 7515 §4.1.6), *not* base64url like the
    segments around it — a difference that costs nothing until a certificate
    happens to contain a `+` or a `/`, at which point one in a few decodes
    fails and the incident reads as a bad signature.
    """
    chain = header.get("x5c")
    if not isinstance(chain, list) or not chain:
        raise InvalidSignature("JWS header carries no x5c certificate chain")
    if len(chain) > MAX_CHAIN:
        raise InvalidSignature(f"x5c carries {len(chain)} certificates; refusing")
    certificates: list[x509.Certificate] = []
    for encoded in chain:
        try:
            certificates.append(x509.load_der_x509_certificate(base64.b64decode(str(encoded))))
        except (binascii.Error, ValueError, TypeError) as exc:
            raise InvalidSignature("x5c holds something that is not a certificate") from exc
    return certificates


def _root() -> x509.Certificate:
    return x509.load_pem_x509_certificate(APPLE_ROOT_CA_G3_PEM)


def _check_chain(certificates: Sequence[x509.Certificate], now: datetime) -> None:
    """Walk the chain to our pinned Apple root, or raise.

    Three separate things, and skipping any one of them makes the other two
    decorative:

    * **Every link is verified.** `issuer` matching `subject` is a string
      comparison and proves nothing; the signature is what proves it.
    * **The last link is verified against our own copy of the root**, never
      against the root Apple put in `x5c`. A chain that ends in a certificate
      the sender supplied is a chain the sender can replace wholesale — a
      self-made root, a self-made intermediate, a self-made leaf, and a
      perfectly valid signature over a transaction granting the archive.
    * **Validity windows are checked.** An expired Apple intermediate is not an
      attack, but accepting one means accepting a certificate whose key Apple
      has stopped standing behind.

    **Not done: revocation.** Neither OCSP nor a CRL is consulted, and that is a
    stated gap rather than an oversight — Apple's own App Store Server Library
    makes online checks an opt-in flag, because a revocation responder that is
    slow or down would take every purchase in the app down with it. The exposure
    is a leaf Apple revoked and has not yet expired; the mitigation, if it ever
    matters, is Apple's library rather than a homemade OCSP client.
    """
    trusted_root = _root()
    # Apple sends the root as the last element. If it is there it must be ours,
    # byte for byte; if it is not, the chain simply ends one link earlier and
    # our copy is appended. Both orders end at the same certificate object.
    chain = list(certificates)
    if len(chain) > 1 and chain[-1].subject == chain[-1].issuer:
        if chain[-1].public_bytes(Encoding.DER) != trusted_root.public_bytes(Encoding.DER):
            raise InvalidSignature("x5c ends in a root that is not Apple Root CA - G3")
        chain = chain[:-1]
    chain.append(trusted_root)

    if len(chain) < 2:
        raise InvalidSignature("x5c carries only a root certificate")

    for certificate in chain:
        if not (certificate.not_valid_before_utc <= now <= certificate.not_valid_after_utc):
            raise InvalidSignature(
                f"certificate {certificate.subject.rfc4514_string()!r} is outside its "
                "validity window"
            )

    for signed, issuer in zip(chain, chain[1:], strict=False):
        if signed.issuer != issuer.subject:
            raise InvalidSignature("the x5c chain does not join up")
        try:
            issuer.public_key().verify(
                signed.signature,
                signed.tbs_certificate_bytes,
                ec.ECDSA(signed.signature_hash_algorithm),
            )
        except (_CryptoInvalidSignature, TypeError, ValueError) as exc:
            raise InvalidSignature(
                "a certificate in the x5c chain was not signed by the one above it"
            ) from exc


def verify(jws: str, *, now: datetime | None = None) -> dict:
    """Verify one Apple JWS and return its decoded payload, or raise.

    The signature is raw `r || s` — the JWS form (RFC 7518 §3.4) — while
    `cryptography` verifies DER, so the two halves are re-encoded. Getting that
    wrong fails identically to a forgery, which is why it is spelled out.

    Nothing is read out of the payload before the signature is checked. The
    header is parsed first because it has to be — the key lives in it — and
    nothing but `alg` and `x5c` is taken from it.
    """
    parts = jws.split(".")
    if len(parts) != 3:
        raise InvalidSignature("not a JWS: expected three dot-separated segments")
    encoded_header, encoded_payload, encoded_signature = parts

    try:
        header = json.loads(_b64url(encoded_header))
    except ValueError as exc:
        raise InvalidSignature("JWS header is not JSON") from exc
    if not isinstance(header, dict):
        raise InvalidSignature("JWS header is not an object")
    if header.get("alg") != SIGNING_ALGORITHM:
        # The oldest JWS attack there is: the verifier obeys the token's own
        # claim about how it was signed. `alg: none` and a swap to an HMAC name
        # both turn a signature check into a formality.
        raise InvalidSignature(f"JWS alg is {header.get('alg')!r}, not {SIGNING_ALGORITHM}")

    certificates = _certificates(header)
    _check_chain(certificates, now or datetime.now(UTC))

    raw = _b64url(encoded_signature)
    if len(raw) != 64:
        raise InvalidSignature("ES256 signature is not 64 bytes")
    signature = asym_utils.encode_dss_signature(
        int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")
    )
    key = certificates[0].public_key()
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise InvalidSignature("the leaf certificate does not hold an EC key")
    try:
        key.verify(
            signature, f"{encoded_header}.{encoded_payload}".encode(), ec.ECDSA(SHA256())
        )
    except _CryptoInvalidSignature as exc:
        raise InvalidSignature("signature does not match") from exc

    try:
        payload = json.loads(_b64url(encoded_payload))
    except ValueError as exc:
        raise InvalidSignature("JWS payload is not JSON") from exc
    if not isinstance(payload, dict):
        raise InvalidSignature("JWS payload is not an object")
    return payload


def _check_it_is_ours(bundle_id: object, environment: object) -> None:
    """Refuse a transaction that is Apple's but not ours, or from the wrong world.

    **This is the credential check.** There is no shared secret with Apple, so a
    valid signature says only that Apple signed it — and Apple signs a
    transaction for every app on the store. Somebody's 99c flashlight purchase,
    handed to `/billing/iap/verify`, is a real Apple signature over a real
    transaction, and without this line it would unlock the archive.

    The sandbox is the other half. App Review runs against the **production**
    build with **Sandbox** transactions, so refusing sandbox outright fails
    review — which is why `ALMA_APPLE_ACCEPT_SANDBOX` defaults to true and why
    turning it off is a decision with a consequence attached. Left on, a person
    with a sandbox tester account for our bundle can mint purchases; left off,
    the app does not ship. The environment is recorded on every event so the two
    can at least be told apart afterwards, which is the honest middle and not a
    fix.
    """
    config = settings()
    expected = config.apple_bundle_id
    if not expected:
        raise BillingUnavailable(
            "APPLE_BUNDLE_ID is not set — refusing to accept an Apple transaction "
            "we cannot tell apart from another app's"
        )
    if str(bundle_id or "") != expected:
        raise InvalidSignature(
            f"transaction is signed for bundle {bundle_id!r}, not {expected!r}"
        )
    if str(environment or "") == SANDBOX and not config.apple_accept_sandbox:
        raise InvalidSignature(
            "this is a Sandbox transaction and ALMA_APPLE_ACCEPT_SANDBOX is off"
        )


def decode_transaction(jws: str, *, now: datetime | None = None) -> dict:
    """One `JWSTransaction`, verified, and proven to be for our app."""
    payload = verify(jws, now=now)
    _check_it_is_ours(payload.get("bundleId"), payload.get("environment"))
    return payload


# ── one Apple event, in our words ──────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Event:
    """A verified Apple transaction, with the notification around it if there was one.

    Two arrival routes end in the same object, which is the point. A purchase
    verified from the app has `notification = {}` and a transaction; a Server
    Notification has both. Everything below reads `transaction` and consults
    `notification` only for the type, so the two routes cannot drift into
    granting different things for the same purchase.

    Property names deliberately mirror `paddle.Event` and `dodo.Event` even
    where Apple keeps the value somewhere else entirely, so the three files read
    side by side and the differences are only in the bodies.
    """

    #: Our per-delivery id. `notificationUUID` for a notification — stable
    #: across Apple's retries — and `appstore:<transactionId>` for a purchase
    #: verified from the app, which is what makes a replayed StoreKit
    #: transaction land on the row that already exists.
    id: str
    #: What happened, in Apple's words: `SUBSCRIBED.INITIAL_BUY`, `DID_RENEW`,
    #: `REFUND`. `purchase` on the verify path, where Apple said nothing and the
    #: app did.
    type: str
    transaction: dict
    notification: dict

    @property
    def transaction_id(self) -> str | None:
        value = self.transaction.get("transactionId")
        return str(value) if value else None

    @property
    def subscription_id(self) -> str | None:
        """The plan this event belongs to, across every renewal it will ever have.

        `originalTransactionId`, and only for an auto-renewable product. Every
        renewal is a fresh `transactionId`, so the transaction cannot identify a
        plan — the same reason Paddle needs `subscription_id` and Dodo needs
        `subscription_id`. Restricted to auto-renewables because Apple sets
        `originalTransactionId` on a non-consumable too (it equals
        `transactionId`), and letting that through would file a permanent door
        purchase as a subscription: `entitlements.grant` would then extend it in
        place on the next unrelated purchase, and `/subscription/cancel` would
        offer to cancel a chapter somebody owns outright.
        """
        if self.transaction.get("type") != AUTO_RENEWABLE:
            return None
        value = self.transaction.get("originalTransactionId")
        return str(value) if value else None

    @property
    def product_id(self) -> str | None:
        value = self.transaction.get("productId")
        return str(value) if value else None

    @property
    def product(self) -> str | None:
        """The catalogue key Apple's product id points at, or `None`.

        `None` is a payment recorded and nothing granted, which is the right
        answer for a product on the App Store account that this price list no
        longer contains.
        """
        return store_slug(self.product_id or "", processor=AppStoreProvider.name)

    @property
    def renews_at(self) -> datetime | None:
        """When Apple will charge this plan again.

        `expiresDate`, in **milliseconds** since the epoch — every date in an
        Apple payload is, and reading one as seconds puts the renewal in 1970.
        For an auto-renewable subscription the moment it expires and the moment
        it renews are the same instant, which is why one field answers both
        questions; between a cancellation and that instant they stay the same,
        because Apple stops the charge rather than the period.
        """
        return _apple_moment(self.transaction.get("expiresDate"))

    @property
    def status(self) -> str | None:
        """What we record about this event's state, for support and never for access.

        Apple has no status string on a transaction, so this carries the thing
        that actually matters when somebody is looking at a row and wondering
        why it exists: which world it came from. A grant written from a Sandbox
        transaction is a grant App Review made, or a tester, and it is the first
        question anybody reconciling a month of revenue will ask.
        """
        environment = self.transaction.get("environment")
        return str(environment) if environment else None

    @property
    def adjustment(self) -> tuple[str, str] | None:
        """(action, type) for money coming back, in the seam's vocabulary.

        Apple refunds a whole transaction or none of it — `revocationDate` and
        `revocationReason` are per transaction, and there is no partial-refund
        shape in `JWSTransactionDecodedPayload` — so every return here is
        `("refund", "full")` and closes what it paid for. A subscription refunded
        for one period arrives as a refund of that period's transaction; because
        the event also names the subscription, `_revoke_for` closes the plan,
        which is what Apple's own guidance asks for.

        `REVOKE` is Family Sharing being turned off rather than money moving.
        It is a revocation and not an adjustment: nothing came back, so writing
        it into the refund column would overstate refunds by the price of every
        shared purchase.
        """
        if self.notification_type == "REFUND":
            return ("refund", "full")
        return None

    @property
    def account_token(self) -> str | None:
        """`appAccountToken` — единственное наше поле внутри подписи Apple.

        Apple принимает в него только UUID и возвращает его в
        `JWSTransactionDecodedPayload` дословно, поэтому это ровно то, что нужно
        расходуемой проверке пары: `productId` у всех покупок пары один и тот же,
        а вот про кого именно эта — говорит только он.

        Приводится к нижнему регистру, потому что UUID регистронезависим по
        RFC 4122, а сравнение строк — нет: `appAccountToken`, вернувшийся от
        Apple в верхнем регистре, не совпал бы с нашей записью, и оплаченный
        отчёт ушёл бы в «непривязанные» вместо того, чтобы открыться.
        """
        value = self.transaction.get("appAccountToken")
        return str(value).strip().lower() or None if value else None

    @property
    def notification_type(self) -> str:
        value = self.notification.get("notificationType")
        return str(value) if value else ""

    @property
    def subtype(self) -> str:
        value = self.notification.get("subtype")
        return str(value) if value else ""

    def amount_cents(self) -> int:
        """What Apple charged, in the storefront currency's minor units.

        `price` is in **milliunits** — $5.99 arrives as 5990 — so it is divided
        by ten rather than used. Absent on transactions signed before Apple
        added the field, and on those this is zero: a purchase with no stated
        price is still a purchase, and refusing it would be refusing a real
        grant over a field Apple did not send.

        This is never compared with the catalogue. See
        `NormalisedEvent.priced_by_us`.
        """
        raw = self.transaction.get("price")
        if raw is None:
            return 0
        try:
            return int(raw) // 10
        except (TypeError, ValueError):
            return 0

    def currency(self) -> str:
        value = self.transaction.get("currency")
        return str(value) if value else "USD"

    def normalise(self) -> NormalisedEvent:
        """This event in provider-neutral words.

        `owner_id` is always `None`, and that is not an omission: Apple echoes
        nothing of ours. On the verify path the owner is the **authenticated
        caller**, which the router sets — a stronger statement than any sealed
        blob, since it is our own session token rather than a field a processor
        relayed. On the notification path the owner is recovered from our own
        rows, which the seam already treats as a required path rather than a
        fallback, because a refund issued from a dashboard has never carried an
        owner either.
        """
        return NormalisedEvent(
            provider=AppStoreProvider.name,
            id=self.id,
            type=self.type,
            kind=_kind_of(self.notification_type, self.subtype),
            owner_id=None,
            product=self.product,
            subscription_id=self.subscription_id,
            transaction_id=self.transaction_id,
            amount_cents=self.amount_cents(),
            currency=self.currency(),
            # Apple states a `storefront` as ISO 3166-1 **alpha-3** ("USA"),
            # while `catalogue.currency_for` and every other country in this
            # system are alpha-2. Left unset rather than half-translated: a
            # three-letter code in a column of two-letter ones is a value that
            # silently matches nothing, and the country here would only ever
            # feed a tax decision that is Apple's to make, not ours.
            country=None,
            buyer_email=None,
            status=self.status,
            renews_at=self.renews_at,
            adjustment=self.adjustment,
            account_token=self.account_token,
            grants=self._grants,
            revokes=self.notification_type in REVOKING,
            moves_money=bool(self.transaction_id) and self._moves_money,
            priced_by_us=False,
            payload={"notification": self.notification, "transaction": self.transaction},
        )

    @property
    def _grants(self) -> bool:
        """Whether this event should open or extend access.

        The verify path always grants — the app would not be calling unless the
        sheet had closed on a completed purchase, and the signature is what
        makes that claim checkable.

        On the notification path, `DID_CHANGE_RENEWAL_STATUS` is deliberately
        absent even with `AUTO_RENEW_ENABLED`: turning renewal back on inside a
        paid period charges nothing, and granting there would add a whole
        `PERIOD` to a plan for a switch being flipped. It is free access, once
        per flip, for as many flips as somebody cares to make.
        """
        if not self.notification_type:
            return True
        return self.notification_type in GRANTING

    @property
    def _moves_money(self) -> bool:
        """Whether money actually changed hands on this event.

        Narrower than "has a transaction", because every Apple notification
        carries a signed transaction — including the ones that describe a
        setting being changed. Recording those would write a purchase row per
        renewal-toggle, each carrying the price of the original charge.
        """
        if not self.notification_type:
            return True
        return self.notification_type in MONEY_EVENTS


def _apple_moment(value: object) -> datetime | None:
    """One Apple timestamp — milliseconds since the epoch — as an instant.

    Tolerant like `provider.moment`, and for the same reason: these only ever
    feed `renews_at`, which is shown to a person and never gates access, so a
    field Apple renames must not turn a paid renewal into a 500 and a retry
    loop. `moment` itself is reused for the ISO-8601 case, because Apple's
    *notification* dates are milliseconds while nothing stops a future field
    being a string.
    """
    if isinstance(value, str):
        return moment(value)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        return datetime.fromtimestamp(value / 1000, UTC)
    except (OverflowError, OSError, ValueError):
        return None


# ── which notifications change what a person can read ──────────────────────
#
# Everything not named below is recorded and ignored. An unrecognised type is
# not an error, it is Apple shipping something we have not adopted — and there
# are a dozen of those, across price increases, consumption requests, renewal
# extensions and external purchase tokens.

#: Access begins, or is extended by another period.
#:
#: `DID_RENEW` belongs here for the same reason Dodo's `subscription.renewed`
#: does: `entitlements.grant` extends an existing subscription row in place,
#: from whichever is later — the current expiry or now — so a renewal *is* a
#: grant at this layer.
#:
#: `ONE_TIME_CHARGE` is Apple's notification for a non-consumable or
#: non-renewing purchase. In practice the app has already called
#: `/billing/iap/verify` and this arrives second; it is still listed, because
#: the person may have closed the app between paying and the call, and
#: `Event.id` makes the two idempotent against each other only when the second
#: one is allowed to grant.
GRANTING = frozenset({"SUBSCRIBED", "DID_RENEW", "ONE_TIME_CHARGE", "OFFER_REDEEMED"})

#: ...and which end access. Money coming back, a purchase taken away, and a
#: period that has genuinely run out.
#:
#: Read this against `IGNORED_REASONS`, where four types that look exactly like
#: revocations are listed with the reason each one is not. The rule is the same
#: one Paddle and Dodo follow and it is a product decision rather than a
#: mapping: a cancellation runs to the end of the period already paid for, a
#: billing retry is dunning, and only money actually returning closes a grant.
REVOKING = frozenset({"REFUND", "REVOKE", "EXPIRED", "GRACE_PERIOD_EXPIRED"})

#: The notifications on which money moved. `REFUND_REVERSED` is here because a
#: reversal restores a charge we had recorded as returned — the money trail has
#: to see it — but it is not in `GRANTING`, because Apple's own documentation
#: says the customer's access should be restored and that is a support decision
#: with a person's name on it rather than an automatic re-grant.
MONEY_EVENTS = frozenset({"SUBSCRIBED", "DID_RENEW", "ONE_TIME_CHARGE", "REFUND"})

#: Why each notification we deliberately do nothing with is doing nothing.
#:
#: Not read by any code path, and that is the point: the first four look exactly
#: like revocations, and the next person to add a line to `REVOKING` should have
#: to read past the reason it was left out.
IGNORED_REASONS: dict[str, str] = {
    "DID_CHANGE_RENEWAL_STATUS": (
        "Auto-renewal turned off is a cancellation, and cancelling is not "
        "refunding. Somebody who turns it off on the 3rd has paid through the "
        "end of the period and is owed every day of it; taking the reading away "
        "when they flip the switch is charging for a month and delivering three "
        "days. `EXPIRED` is the honest moment, and until then `_note_the_plan` "
        "clears `renews_at` so the account screen stops promising a charge."
    ),
    "DID_FAIL_TO_RENEW": (
        "Dunning. Apple is still trying the card — the subtypes are literally "
        "BILLING_RETRY and GRACE_PERIOD — and the person whose card bounced is "
        "the one least able to argue about it. If the retries fail, "
        "GRACE_PERIOD_EXPIRED or EXPIRED arrives and closes it."
    ),
    "DID_CHANGE_RENEWAL_PREF": (
        "An upgrade or downgrade taking effect at the next period. It should "
        "re-scope the grant and must not extend it, and `entitlements.grant` "
        "cannot do the first without the second: given a duration it always "
        "adds a whole period. Granting here would hand a free month to anybody "
        "who switched plans. Leaving it out costs the opposite and smaller "
        "thing — the old scope survives until the next renewal, bounded by an "
        "expiry that already exists. Today the ladder sells one subscription, "
        "so nothing can reach this at all."
    ),
    "REFUND_DECLINED": (
        "Apple refused a refund the customer asked for. Nothing changed: the "
        "money never left and the grant was never closed."
    ),
    "REFUND_REVERSED": (
        "Money that came back and then went out again. It is in MONEY_EVENTS so "
        "the trail is right, and deliberately not in GRANTING: Apple asks that "
        "access be restored, but a re-grant written from a reversal would run "
        "against a revoked row with no fresh transaction to key on, and the "
        "population is small enough that a person should look at it."
    ),
    "CONSUMPTION_REQUEST": (
        "Apple asking what a consumable was worth, for a refund decision — and "
        "since v3 we do sell one, `pair.check`. Deliberately unanswered all the "
        "same: the reply is a `consumptionRequest` call describing how much of "
        "the thing the customer used, and the honest answer for a written "
        "report is 'all of it, the moment it was generated', which is an "
        "argument against the refund somebody has already asked for. Silence "
        "lets Apple decide on its own, which for a $4.99 report is the cheaper "
        "of two ways to be wrong. The refund itself still lands: `REFUND` "
        "revokes exactly the grant its transaction paid for."
    ),
    "PRICE_INCREASE": (
        "A price change we made in App Store Connect, working its way through "
        "consent. It changes what the next charge is, not what this grant is."
    ),
    "RENEWAL_EXTENDED": (
        "A period we extended by hand, usually as an apology for an outage. It "
        "moves the expiry Apple holds and not the money; the grant's own expiry "
        "catches up on the next renewal. **Unverified:** whether Apple emits a "
        "DID_RENEW at the new date is not stated in the notification reference, "
        "and if it does not, an extension we grant in Connect is not reflected "
        "here until the following period."
    ),
    "RENEWAL_EXTENSION": (
        "The summary of a bulk extension request, not an event about one "
        "customer. There is nobody to find from it."
    ),
    "EXTERNAL_PURCHASE_TOKEN": (
        "An alternative payment provider under the EU DMA entitlement. We do "
        "not use one — the whole point of moving to the stores was that Apple "
        "and Google will take our category's money at all — so this cannot "
        "arrive, and a handler for it would be a promise that it can."
    ),
    "TEST": (
        "A delivery Apple sends when somebody presses the button in App Store "
        "Connect. It carries no transaction, so it records itself as a webhook "
        "event and grants nothing — which is exactly the check the button is "
        "for."
    ),
}


#: Apple's notification types in the seam's taxonomy.
#:
#: Two of them are decided by their **subtype** rather than by their type, which
#: is why this is a function and not only a dict. `DID_CHANGE_RENEWAL_STATUS`
#: means opposite things under `AUTO_RENEW_DISABLED` and `AUTO_RENEW_ENABLED` —
#: a cancellation and its undo — and mapping both to one kind would have
#: `_note_the_plan` clear `renews_at` on the event that restores it.
_KINDS: dict[str, EventKind] = {
    "SUBSCRIBED": EventKind.SUBSCRIPTION_STARTED,
    "DID_RENEW": EventKind.SUBSCRIPTION_RENEWED,
    "DID_CHANGE_RENEWAL_PREF": EventKind.SUBSCRIPTION_UPDATED,
    "DID_FAIL_TO_RENEW": EventKind.SUBSCRIPTION_DUNNING,
    "GRACE_PERIOD_EXPIRED": EventKind.SUBSCRIPTION_ENDED,
    "EXPIRED": EventKind.SUBSCRIPTION_ENDED,
    "REFUND": EventKind.ADJUSTMENT,
    "REFUND_REVERSED": EventKind.PAYMENT,
    "REFUND_DECLINED": EventKind.UNKNOWN,
    "REVOKE": EventKind.SUBSCRIPTION_ENDED,
    "ONE_TIME_CHARGE": EventKind.PAYMENT,
    "OFFER_REDEEMED": EventKind.SUBSCRIPTION_STARTED,
    "PRICE_INCREASE": EventKind.SUBSCRIPTION_UPDATED,
    "RENEWAL_EXTENDED": EventKind.SUBSCRIPTION_UPDATED,
}


def _kind_of(notification_type: str, subtype: str = "") -> EventKind:
    if not notification_type:
        # The verify path: the app tells us a purchase completed and Apple's
        # signature is what makes that checkable. It is a payment, whatever the
        # product turns out to be — the subscription-started kind would put a
        # permanent door purchase through the plan-news path.
        return EventKind.PAYMENT
    if notification_type == "DID_CHANGE_RENEWAL_STATUS":
        return (
            EventKind.SUBSCRIPTION_CANCELLED
            if subtype == "AUTO_RENEW_DISABLED"
            else EventKind.SUBSCRIPTION_UPDATED
        )
    return _KINDS.get(notification_type, EventKind.UNKNOWN)


def parse(payload: dict, headers: Mapping[str, str] | None = None) -> Event:
    """Read one App Store Server Notification V2 into an `Event`.

    The body Apple POSTs is `{"signedPayload": "<JWS>"}` and nothing else. The
    JWS decodes to `responseBodyV2DecodedPayload` — `notificationType`,
    `subtype`, `notificationUUID`, and a `data` object holding `bundleId`,
    `environment` and a **second** JWS in `signedTransactionInfo`.

    Both are verified. The inner one is not trusted because the outer one was:
    they are separate signatures over separate payloads, and the outer envelope
    does not cover the inner transaction's contents in any way we could rely on.

    `headers` is accepted and unused — Apple puts `notificationUUID` in the
    body. The parameter exists because the protocol needs it for Standard
    Webhooks, where the per-delivery id is a header and nothing else.
    """
    signed = payload.get("signedPayload")
    if not isinstance(signed, str) or not signed:
        raise InvalidSignature("body carries no signedPayload")

    notification = verify(signed)
    data = notification.get("data")
    data = data if isinstance(data, dict) else {}
    _check_it_is_ours(data.get("bundleId"), data.get("environment"))

    transaction: dict = {}
    inner = data.get("signedTransactionInfo")
    if isinstance(inner, str) and inner:
        transaction = decode_transaction(inner)

    subtype = str(notification.get("subtype") or "")
    kind = str(notification.get("notificationType") or "")
    return Event(
        # `notificationUUID` and not a hash of the body. Apple retries a failed
        # delivery, and the retry carries the same UUID — which is what makes
        # insert-before-process work. Deriving an id from the payload instead
        # would file each retry as a new event, and a granting event granted
        # twice is a billing period nobody paid for.
        id=str(notification.get("notificationUUID") or ""),
        type=f"{kind}.{subtype}" if subtype else kind,
        transaction=transaction,
        notification=notification,
    )


def entitlement_for(event: Event) -> Grant | None:
    """What this Apple event should grant, if anything.

    A translation and a delegation. The rule — that a recurring plan is
    recognised by the catalogue having given the product an interval — is ours
    and lives in `provider.py`, where the other three adapters reach the same
    answer through the same function rather than through a fourth copy of it.
    """
    return _entitlement_for(event.normalise())


class AppStoreProvider:
    """Apple as a `StoreProvider`.

    Thin, like the other three: everything it does is already in this module. It
    exists so the router can hold *a* processor rather than *this* processor.
    """

    name = "appstore"
    granting = GRANTING
    revoking = REVOKING
    manage_url = MANAGE_URL

    #: The legal seller. Apple is the merchant of record for every in-app
    #: purchase, which is the second reason this move was worth making: no EU
    #: OSS registration, no Mexican fiscal representative, no Brazilian CNPJ.
    #:
    #: **Unverified against a contract, and knowingly imprecise.** The entity on
    #: a buyer's statement is not one company: Apple's Developer Program
    #: agreement names Apple Inc. for the Americas, Apple Distribution
    #: International Ltd. for Europe, iTunes K.K. for Japan and others besides,
    #: and which one applies depends on the storefront. This string is published
    #: on the refunds page, which is the page a card issuer reads during a
    #: dispute, so before launch it has to either be confirmed or become a
    #: per-storefront lookup.
    merchant = "Apple"

    #: Apple collects nothing for us and asks for nothing from us. There is no
    #: session to create at all, so there is certainly no address needed first.
    requires_email = False

    #: Apple emails the receipt, as the seller. See the field on the protocol
    #: for why this is a flag rather than "we have no address".
    issues_the_receipt = True

    def verify(
        self, raw_body: bytes, headers: Mapping[str, str], *, secret: str | None = None
    ) -> None:
        """Verify an App Store Server Notification, or raise.

        The protocol's signature fits with one substitution: there is no shared
        secret, so `secret` is accepted and ignored rather than removed —
        removing it would make this adapter unassignable to `BillingProvider`,
        and the router would have to ask which processor is running before it
        could verify.

        The *body* carries the signature here, not a header, which is why
        `headers` goes unread. That is the honest inversion: a card processor
        signs the bytes it sends with a key we share, and Apple sends a document
        that signs itself with a key only Apple has.
        """
        try:
            payload = json.loads(raw_body)
        except ValueError as exc:
            raise InvalidSignature("notification body is not JSON") from exc
        if not isinstance(payload, dict):
            raise InvalidSignature("notification body is not an object")
        parse(payload, headers)

    def parse(
        self, payload: dict, headers: Mapping[str, str] | None = None
    ) -> NormalisedEvent:
        """The protocol's `parse`. Verifies again rather than trusting the caller.

        Two ECDSA verifications repeated is a few hundred microseconds. What it
        buys is that this function is safe to call on its own — nothing in it
        reads a field out of an unverified document — and the alternative is a
        method whose safety depends on a call order that is not visible from
        here.
        """
        return parse(payload, headers).normalise()

    async def enrich(self, event: NormalisedEvent) -> NormalisedEvent:
        """Nothing to add: Apple's notification carries the signed transaction.

        The whole of `JWSTransactionDecodedPayload` is inside the delivery, so
        unlike Google there is no call to make. See `provider.BillingProvider.enrich`.
        """
        return event

    async def verify_purchase(self, *, transaction: str, product: str) -> NormalisedEvent:
        """Check one StoreKit 2 transaction and say what it grants.

        `transaction` is `Transaction.jwsRepresentation` from StoreKit 2, handed
        over verbatim by the app. Everything needed is inside it, so this makes
        no network call at all — which matters more than it sounds: it is called
        while somebody watches a spinner between paying and reading.

        Four refusals, in the order they are checked, because the order is what
        makes the logs readable:

        1. A signature that does not chain to Apple Root CA - G3.
        2. A `bundleId` that is not ours — a real Apple signature over somebody
           else's app's purchase.
        3. A `productId` we do not sell, or one whose catalogue key is not the
           key being claimed. This is the price check's replacement and it is
           the reason the client cannot buy the door and claim the archive.
        4. A transaction Apple has already revoked, which is a refunded purchase
           being presented as a fresh one.
        """
        decoded = decode_transaction(transaction)
        event = Event(
            id=f"{self.name}:{decoded.get('transactionId') or ''}",
            type="purchase",
            transaction=decoded,
            notification={},
        )

        if decoded.get("revocationDate") is not None:
            raise PurchaseIncomplete(
                f"Apple revoked transaction {event.transaction_id} "
                f"(reason {decoded.get('revocationReason')!r})"
            )

        found = event.product
        if found is None:
            raise ProductMismatch(
                f"{event.product_id!r} is not a product this price list sells"
            )
        if found != product:
            raise ProductMismatch(
                f"Apple signed a purchase of {found!r}; {product!r} was claimed"
            )
        if not event.transaction_id:
            # Without one there is no idempotency key and no money row to hang a
            # refund on. Apple always sends it; refusing loudly beats inventing
            # an id, which is the mistake the Dodo adapter's `parse` documents.
            raise InvalidSignature("the transaction carries no transactionId")

        return event.normalise()

    async def open_session(
        self,
        *,
        product: str,
        user_id: str,
        currency: str,
        country: str | None = None,
        email: str | None = None,
    ) -> SessionHandle:
        """There is no server-created checkout on the App Store.

        Raised rather than faked. Apple requires in-app purchases to go through
        StoreKit, the app opens the sheet itself, and a `SessionHandle` invented
        here would be a URL nothing can open. The router turns this into a 503
        carrying the message, which is a sentence a client can render — and the
        native client never asks, because `/billing/catalogue` publishes
        `provider: "appstore"` and that is the discriminant it switches on.
        """
        raise BillingUnavailable(
            "purchases on the App Store are opened by the app through StoreKit; "
            "there is no checkout for a server to create"
        )

    async def cancel_subscription(self, subscription_id: str) -> None:
        """Apple does not let us cancel. The customer does, and here is where.

        There is no App Store Server API endpoint for cancelling an
        auto-renewable subscription: it belongs to the Apple ID, not to our
        account, and Settings is the only place it can be stopped. Raising with
        the link is the honest answer and also the compliant one — the same
        guideline that expects an app to sell through StoreKit expects it to
        link people to where they can stop paying.
        """
        raise SelfServiceOnly(
            "an App Store subscription can only be cancelled by its owner, in "
            "Settings or the App Store app",
            manage_url=MANAGE_URL,
        )

    async def buyer_address(self, event: NormalisedEvent) -> str | None:
        """Apple never tells us who bought, and does not need to.

        A transaction carries an `appAccountToken` if the app set one and
        nothing else about a person — no name, no address, no country beyond a
        storefront. That is the privacy design of StoreKit and it is not an
        obstacle here: Apple is the merchant of record and sends the receipt
        itself, so the confirmation on a durable medium that the withdrawal
        waiver turns on is Apple's rather than ours. See `issues_the_receipt`.
        """
        return None
