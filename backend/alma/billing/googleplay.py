"""Google Play, behind the seam: purchase tokens and Real-time Developer Notifications.

The fourth implementation of `provider.py`, and the mirror image of the third.
Apple hands us a document that proves itself and needs no call; Google hands us
an **opaque purchase token** that proves nothing at all and has to be exchanged
for the truth over the Play Developer API. Google's own documentation says so
outright — always call the API after a notification — and that single difference
is what put `enrich` on the protocol.

Three things here are load-bearing and the rest is translation.

**Verification is an API call, authenticated as us.** There is no signature on a
purchase token; a token is a database key in Google's database. So
`purchases.subscriptionsv2.get` and `purchases.products.get` are the check, and
the credential is a service account whose private key signs a JWT that is
exchanged for an access token. A token for another app cannot be verified at all
— the package name is in the URL — which is the same protection Apple's
`bundleId` comparison gives, arriving by a completely different route.

**The notification is authenticated separately, and by Google rather than by
us.** A Real-time Developer Notification arrives through Cloud Pub/Sub push,
which signs an OIDC JWT with Google's own keys and puts it in
`Authorization: Bearer`. That token's `aud` is whatever we configured on the
push subscription, and it is the closest thing here to a shared secret: without
it, the endpoint is a URL anybody who learns it can POST a renewal to. It is
verified against Google's published certificates, never against anything the
token itself points at.

**The notification body says almost nothing.** A `SubscriptionNotification` is a
version, an integer and a purchase token — no product, no order id, no expiry,
no state. Everything in a `NormalisedEvent` beyond "something happened to this
token" comes from `enrich`, which is called after the idempotency check so a
redelivered message costs no quota. Pub/Sub delivery is at-least-once by design
and Google says to deduplicate on `messageId`, which is exactly the id this
adapter reports.

Sources, read rather than recalled:
* Play Developer API — purchases.subscriptionsv2.get, purchases.products.get
  (https://developers.google.com/android-publisher/api-ref/rest/v3/purchases.subscriptionsv2/get)
* Real-time developer notifications reference
  (https://developer.android.com/google/play/billing/rtdn-reference)
* Authenticating Pub/Sub push subscriptions
  (https://cloud.google.com/pubsub/docs/authenticate-push-subscriptions)

No credentials appear in this file. `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`,
`GOOGLE_PLAY_PACKAGE_NAME` and `GOOGLE_PLAY_PUBSUB_AUDIENCE` come from the
environment.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime

import httpx
import jwt

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
    header_value,
    moment,
    store_product_id,
    store_slug,
)
from .provider import entitlement_for as _entitlement_for

log = logging.getLogger("alma.billing")

#: Re-exported so `googleplay.Grant` is the same object as `paddle.Grant`. See
#: the same list in `dodo.py` for why two same-named exception classes is the
#: shape of a webhook endpoint that accepts everything.
__all__ = [
    "GRANTING",
    "PERIOD",
    "REVOKING",
    "Event",
    "GooglePlayClient",
    "GooglePlayProvider",
    "Grant",
    "InvalidSignature",
    "entitlement_for",
    "parse",
    "verify",
]

ANDROID_PUBLISHER = "https://androidpublisher.googleapis.com/androidpublisher/v3"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
PUBLISHER_SCOPE = "https://www.googleapis.com/auth/androidpublisher"

#: Where Google publishes the keys that sign a Pub/Sub push token. Fetched
#: rather than pinned — unlike Apple's root, these rotate on Google's schedule
#: and a pinned copy would fail closed on a rotation morning, taking every
#: renewal with it. `PyJWKClient` caches them.
GOOGLE_CERTS = "https://www.googleapis.com/oauth2/v3/certs"

#: The two spellings Google uses for the issuer of an OIDC token. Both are
#: documented as valid and only one of them is a URL, which is exactly the sort
#: of detail a hand-written comparison gets wrong once.
GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})

#: Where a customer manages and cancels their own subscription. `sku` and
#: `package` are query parameters Play reads to open the right row.
MANAGE_URL = "https://play.google.com/store/account/subscriptions"

#: The states in which a Play subscription is worth granting for. `CANCELED`
#: belongs here and it is the one that looks wrong: on Play a cancelled
#: subscription has auto-renew turned off and **remains active until its expiry
#: time**, which is precisely the rule the whole seam is built around. Refusing
#: it would take a reading away from somebody who has paid for the rest of the
#: month, on the day they cancelled.
LIVE_STATES = frozenset({
    "SUBSCRIPTION_STATE_ACTIVE",
    "SUBSCRIPTION_STATE_CANCELED",
    "SUBSCRIPTION_STATE_IN_GRACE_PERIOD",
})

#: `purchaseState` on a one-time product: 0 purchased, 1 cancelled, 2 pending.
#: An integer enum with no names in the payload, so the names are here.
PURCHASED, CANCELLED, PENDING = 0, 1, 2


# ── talking to Google as ourselves ─────────────────────────────────────────


class GooglePlayClient:
    """The small part of the Play Developer API we actually call.

    Three endpoints: one subscription lookup, one product lookup, and nothing
    that changes anything. That last part is deliberate — see
    `GooglePlayProvider.cancel_subscription` for why the cancel endpoint that
    exists is not called.
    """

    #: One access token, cached across requests for the process. Google's tokens
    #: last an hour and minting one costs a round trip plus an RSA signature; a
    #: fresh one per webhook would put that on the critical path of every
    #: renewal. Class-level rather than per-instance because the provider is
    #: constructed per request — `billing_adapter()` is deliberately not cached —
    #: so a per-instance cache would never be read twice.
    _token: str = ""
    _token_expires: float = 0.0

    #: Refresh this many seconds before Google says it expires. A token that is
    #: valid when we check it and expired when Google checks it is a 401 on a
    #: webhook, and a 401 on a webhook is a retry, and a retry is how one
    #: payment becomes two grants.
    LEEWAY = 120

    def __init__(self, credentials: dict | None = None, package: str | None = None) -> None:
        config = settings()
        self.package = package if package is not None else config.google_play_package
        if credentials is not None:
            self._credentials: dict | None = credentials
        else:
            self._credentials = _service_account(config.google_play_service_account)

    @property
    def configured(self) -> bool:
        return bool(self._credentials and self.package)

    def _assertion(self) -> str:
        """A JWT saying we are the service account, signed with its own key.

        The OAuth 2.0 JWT bearer flow: the assertion is exchanged for an access
        token rather than used as one. `aud` is the token endpoint and not the
        API — an assertion that named the API could be replayed against it by
        whoever it passed through.
        """
        assert self._credentials is not None
        now = int(time.time())
        return jwt.encode(
            {
                "iss": self._credentials.get("client_email"),
                "scope": PUBLISHER_SCOPE,
                "aud": TOKEN_ENDPOINT,
                "iat": now,
                # An hour is Google's maximum. Shorter would be pointless: the
                # assertion is used once, immediately, and thrown away.
                "exp": now + 3600,
            },
            self._credentials.get("private_key") or "",
            algorithm="RS256",
            headers={"kid": self._credentials.get("private_key_id")},
        )

    async def _access_token(self) -> str:
        if self._token and time.time() < GooglePlayClient._token_expires - self.LEEWAY:
            return self._token
        if not self.configured:
            raise BillingUnavailable(
                "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON / GOOGLE_PLAY_PACKAGE_NAME are "
                "not set — cannot talk to Google Play"
            )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    TOKEN_ENDPOINT,
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": self._assertion(),
                    },
                )
        except httpx.HTTPError as exc:
            raise BillingUnavailable(f"google unreachable: {exc}") from exc
        if response.status_code >= 400:
            raise BillingUnavailable(
                f"google refused the service account: {response.status_code} "
                f"{response.text[:200]}"
            )
        body = response.json()
        GooglePlayClient._token = str(body.get("access_token") or "")
        GooglePlayClient._token_expires = time.time() + float(body.get("expires_in") or 0)
        if not GooglePlayClient._token:
            raise BillingUnavailable("google returned no access token")
        return GooglePlayClient._token

    async def _get(self, path: str) -> dict:
        """One read, raising `BillingUnavailable` on anything but success.

        Raising rather than returning `None`, for the same reason `DodoClient`
        does: every call here decides whether somebody who has paid gets what
        they paid for, and a failure that returns quietly turns into a refusal
        the person cannot argue with.

        A 404 raises too, and that is the interesting case: Google answers 404
        for a purchase token it does not recognise, which is what a forged one
        looks like. It is not turned into a distinct exception because we cannot
        tell it apart from a token for the wrong package, or from a real token
        during a Play outage — and the two wrong answers are "you are a forger"
        and "try again", which is not a call a status code should make. The
        router's 503 says try again; a log line carries the 404.
        """
        token = await self._access_token()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{ANDROID_PUBLISHER}{path}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as exc:
            raise BillingUnavailable(f"google unreachable: {exc}") from exc
        if response.status_code >= 400:
            raise BillingUnavailable(
                f"google refused GET {path}: {response.status_code} {response.text[:300]}"
            )
        return response.json() if response.content else {}

    async def subscription(self, purchase_token: str) -> dict:
        """`purchases.subscriptionsv2.get` — the whole state of one subscription.

        v2 and not v1, and the difference matters rather than being a version
        bump: v1 answers about a single SKU and v2 answers about the
        subscription, with `lineItems`, a named `subscriptionState`, and a
        `latestOrderId` that identifies the individual charge. Without that last
        one there is nothing short enough to put in `Purchase.transaction_id` —
        a purchase token can run to a thousand characters, and the column is 64.
        """
        return await self._get(
            f"/applications/{self.package}/purchases/subscriptionsv2/tokens/{purchase_token}"
        )

    async def product(self, product_id: str, purchase_token: str) -> dict:
        """`purchases.products.get` — one non-consumable purchase.

        The product id is in the URL, which is why the one-time path needs it
        and the subscription path does not. On the notification route Google
        supplies it as `sku`; on the verify route the app does not have to,
        because the catalogue key being claimed names it — see
        `GooglePlayProvider.verify_purchase`.
        """
        return await self._get(
            f"/applications/{self.package}/purchases/products/{product_id}"
            f"/tokens/{purchase_token}"
        )


def _service_account(raw: str) -> dict | None:
    """The service-account credentials, from JSON or from a path to it.

    Both are accepted because both are how people actually deploy: a platform
    secret store hands over a string, and a mounted volume hands over a file.
    Guessing between them on the first character is unambiguous — JSON starts
    with `{` and a path does not — and it saves a second environment variable
    whose only job would be to say which of the two the first one is.

    A value that is neither answers `None` rather than raising, and the refusal
    happens where it can say something useful: `configured` is false, and the
    first call explains which variable to fix.
    """
    value = (raw or "").strip()
    if not value:
        return None
    if not value.startswith("{"):
        try:
            value = open(value, encoding="utf-8").read()
        except OSError as exc:
            log.error("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON is not a readable file: %s", exc)
            return None
    try:
        parsed = json.loads(value)
    except ValueError:
        log.error("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON is neither JSON nor a path to it")
        return None
    return parsed if isinstance(parsed, dict) else None


# ── the Pub/Sub push token, which is the only signature there is ───────────

_jwk_client: jwt.PyJWKClient | None = None


def _keys() -> jwt.PyJWKClient:
    """Google's signing keys, fetched once and cached.

    A module-level cache rather than a fresh client per delivery: `PyJWKClient`
    caches inside itself, and constructing one per request throws that away and
    fetches Google's certificate set on every webhook.
    """
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = jwt.PyJWKClient(GOOGLE_CERTS, cache_keys=True)
    return _jwk_client


def verify(
    raw_body: bytes, headers: Mapping[str, str], *, secret: str | None = None
) -> None:
    """Verify the Pub/Sub push token on one delivery, or raise.

    This is the whole of "did Google send this". The body is not signed at all —
    a Pub/Sub message is a base64 blob inside a JSON envelope, and anybody can
    write one — so what is checked is the OIDC token Pub/Sub puts in
    `Authorization`, against Google's published keys.

    `aud` is the load-bearing claim. Google will happily mint a valid,
    Google-signed OIDC token for *any* service account and *any* audience, so a
    signature alone proves only that some Google customer sent this. The
    audience is configured on our own push subscription and nowhere else, which
    makes it the nearest thing to the shared secret the other three adapters
    have. `GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT` narrows it further and is
    strongly worth setting: it pins *which* identity may push, so that an
    audience string leaking from a log is not on its own enough.

    `secret` is accepted and ignored, for the same reason it is on the Apple
    adapter: the protocol has one, and there is nothing here it could be.
    """
    config = settings()
    audience = config.google_play_pubsub_audience
    if not audience:
        raise InvalidSignature(
            "GOOGLE_PLAY_PUBSUB_AUDIENCE is not set — refusing to accept an "
            "unverified notification that grants paid access"
        )

    bearer = header_value(headers, "Authorization")
    scheme, _, token = bearer.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise InvalidSignature("no Pub/Sub bearer token on the request")

    try:
        key = _keys().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            audience=audience,
            # Google documents that a push token may be up to an hour old when
            # it arrives, so the freshness question is answered by `exp` — which
            # PyJWT checks — rather than by `provider.check_freshness`. That
            # helper's five minutes is right for a scheme where we choose the
            # window; here the sender does.
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidSignature(f"Pub/Sub token did not verify: {exc}") from exc
    except (httpx.HTTPError, OSError, ValueError) as exc:
        # Fetching Google's keys failed. Refusing is the safe direction: Pub/Sub
        # retries a push it could not deliver, so a minute of outage costs a
        # delay rather than a lost renewal.
        raise InvalidSignature(f"could not fetch Google's signing keys: {exc}") from exc

    if str(claims.get("iss") or "") not in GOOGLE_ISSUERS:
        raise InvalidSignature(f"Pub/Sub token issuer is {claims.get('iss')!r}")

    expected = config.google_play_pubsub_service_account
    if expected:
        if str(claims.get("email") or "") != expected or not claims.get("email_verified"):
            raise InvalidSignature(
                f"Pub/Sub token is from {claims.get('email')!r}, not {expected!r}"
            )
    else:
        log.warning(
            "GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT is unset: the audience is the only "
            "thing distinguishing Google Play from any other Google customer"
        )


# ── one Play event, in our words ───────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Event:
    """A Real-time Developer Notification, before and after the API call.

    `state` is empty until `enrich` has filled it, and that is not a
    half-constructed object — it is the honest shape of what arrived. A Play
    notification genuinely contains a package name, an integer and a token, and
    a dataclass pretending otherwise would be pretending Google told us the
    product.

    Property names mirror the other three adapters even where Google keeps the
    value somewhere else, so the four files read side by side.
    """

    #: Pub/Sub's `messageId`. Stable across redeliveries, which is what makes
    #: insert-before-process work — Google's own documentation asks for exactly
    #: this deduplication, and adds that it saves API quota.
    id: str
    #: Google's own words for what happened: `subscription.2`,
    #: `one_time_product.1`, `voided_purchase`. The integer is kept rather than
    #: renamed because it is what the reference table is keyed by, and support
    #: reading a row should be able to look it up without a translation step.
    type: str
    purchase_token: str
    #: The decoded `DeveloperNotification`, which is what goes into
    #: `webhook_event.payload` — a base64 blob in that column would be a row
    #: nobody can read at two in the morning.
    notification: dict
    #: What the Play Developer API said, once it has been asked. Empty on the
    #: notification as it arrives, and on a voided purchase, which is the one
    #: shape that carries its own facts.
    state: dict

    @property
    def kind_word(self) -> str:
        """Which of the four mutually exclusive notification bodies this is."""
        return self.type.split(".")[0]

    @property
    def notification_code(self) -> int:
        tail = self.type.split(".")[-1]
        return int(tail) if tail.isdigit() else 0

    @property
    def line_item(self) -> dict:
        """The one line of a subscription we sell.

        Play supports several products under one subscription; the ladder sells
        exactly one, so the first line is the line. If a bundle is ever sold,
        this has to become a search rather than an index — and the failure it
        would produce until then is granting the first item of a bundle, which
        is why it is written down here rather than left as a `[0]`.
        """
        items = self.state.get("lineItems")
        return items[0] if isinstance(items, list) and items else {}

    @property
    def product_id(self) -> str | None:
        for value in (
            self.line_item.get("productId"),
            self.state.get("productId"),
            (self.notification.get("oneTimeProductNotification") or {}).get("sku"),
        ):
            if value:
                return str(value)
        return None

    @property
    def product(self) -> str | None:
        return store_slug(self.product_id or "", processor=GooglePlayProvider.name)

    @property
    def transaction_id(self) -> str | None:
        """The individual charge, short enough to be a key.

        `latestOrderId` on a subscription, `orderId` on a one-time purchase and
        on a voided one. Never the purchase token: a token can run past a
        thousand characters and `Purchase.transaction_id` is 64, so storing one
        would truncate — and a truncated unique key is a collision waiting for
        the second customer.
        """
        for value in (
            self.state.get("latestOrderId"),
            self.state.get("orderId"),
            (self.notification.get("voidedPurchaseNotification") or {}).get("orderId"),
        ):
            if value:
                return str(value)
        return None

    @property
    def subscription_id(self) -> str | None:
        """The plan across every renewal it will ever have.

        Google gives each renewal an order id of the form `GPA.1234-…-5678..3`,
        where the suffix counts the charge. The base is therefore stable for the
        life of the plan and short, which is what `Entitlement.subscription_id`
        needs; the purchase token is stable too and is 20 times too long.

        A voided purchase is included when Google says the thing voided was a
        subscription (`productType` 1), and it has to be: a renewal refunded in
        month twelve names *that* charge's order id, while the entitlement still
        carries the order id of the first one — `entitlements.grant` extends a
        subscription row in place and never rewrites its `transaction_id`. So
        matching the refund on the transaction alone would find no row, and the
        money would go back while the plan kept working.

        **Unverified:** whether a resubscription after expiry keeps the same
        base order id is not stated in Google's reference. If it does not, a
        resubscribe writes a second entitlement row rather than extending the
        first — visible, harmless, and something `linkedPurchaseToken` would
        let us join up if it ever matters.
        """
        voided = self.notification.get("voidedPurchaseNotification") or {}
        subscription_shaped = (
            self.kind_word == "subscription"
            or bool(self.state.get("lineItems"))
            or voided.get("productType") == 1
        )
        if not subscription_shaped:
            return None
        latest = self.transaction_id
        return latest.split("..")[0] if latest else None

    @property
    def status(self) -> str | None:
        """Google's own word for the state — recorded, never consulted.

        `subscriptionState` is a documented enum and it is exactly the sort of
        string that gets renamed. Access is decided by the expiry and the
        revocation, which we set ourselves.
        """
        value = self.state.get("subscriptionState")
        return str(value) if value else None

    @property
    def renews_at(self) -> datetime | None:
        """When Play bills again, as an RFC 3339 instant.

        `expiryTime` on the line item. For an auto-renewing plan the moment it
        expires and the moment it renews are the same instant; once auto-renew
        is off they still are, because Play lets the paid period run out rather
        than ending it.
        """
        return moment(self.line_item.get("expiryTime"))

    @property
    def adjustment(self) -> tuple[str, str] | None:
        """(action, type) for money coming back, in the seam's vocabulary.

        Only a `voidedPurchaseNotification` returns money. `refundType` is 1 for
        a full void and 2 for a quantity-based partial one, and Google notes
        that voiding the last of a multi-quantity purchase reports a *full*
        refund rather than a second partial — which is the arithmetic trap
        `dodo.Event.adjustment` avoids by reading a flag, and Google avoids for
        us by the same means.

        We sell nothing with a quantity above one, so the partial branch cannot
        fire today. It is written anyway because the cost of being wrong is
        asymmetric: a partial mapped as full closes a grant somebody still owns.
        """
        voided = self.notification.get("voidedPurchaseNotification")
        if not isinstance(voided, dict):
            return None
        return ("refund", "partial" if voided.get("refundType") == 2 else "full")

    def amount_cents(self) -> int:
        """What Play charged, in the storefront currency's minor units.

        Zero for a one-time purchase, and that is Google rather than us:
        `ProductPurchase` states no price at all — not in v3, not anywhere — so
        a row in the money trail for a door records the fact of the payment and
        not its size, and the size is reconciled against the Play payout report.
        A subscription is better off: `autoRenewingPlan.recurringPrice` is a
        `Money` of units plus nanos, and both halves are read, because 5 units
        and 990000000 nanos is $5.99 and reading only the units is $5.00.
        """
        price = (self.line_item.get("autoRenewingPlan") or {}).get("recurringPrice")
        if not isinstance(price, dict):
            return 0
        try:
            units = int(price.get("units") or 0)
            nanos = int(price.get("nanos") or 0)
        except (TypeError, ValueError):
            return 0
        return units * 100 + nanos // 10_000_000

    def currency(self) -> str:
        price = (self.line_item.get("autoRenewingPlan") or {}).get("recurringPrice")
        code = price.get("currencyCode") if isinstance(price, dict) else None
        return str(code) if code else "USD"

    @property
    def country(self) -> str | None:
        """`regionCode`, which Google states as ISO 3166-1 alpha-2 — ours exactly."""
        value = self.state.get("regionCode")
        return str(value) if value else None

    @property
    def account_token(self) -> str | None:
        """`obfuscatedExternalProfileId` — наш токен, вернувшийся от Google.

        **Профильный, а не аккаунтный, и разница здесь — вся суть.**
        `obfuscatedExternalAccountId` отвечает на вопрос «чей это Google-аккаунт»
        и для расходуемой покупки бесполезен: у всех проверок пары одного
        человека он одинаков. `obfuscatedExternalProfileId` Google описывает как
        «профиль внутри аккаунта» — то самое место, куда кладут «про кого эта
        покупка», и именно его приложение заполняет из `/billing/pair/intent`.

        Значение приходит из ответа Play Developer API, то есть от Google, а не
        из тела запроса клиента. Оговорка из `normalise()` — «грант никогда не
        читается из поля, которое пишет плательщик» — здесь соблюдена не тем,
        что поле стало доверенным, а тем, что оно бесполезно для подмены: токен
        привязан к нашей строке `PairIntent`, и чужой intent принадлежит чужому
        аккаунту, где `billing.pairs.partner_for` его и отвергнет.
        """
        value = self.state.get("obfuscatedExternalProfileId")
        return str(value).strip().lower() or None if value else None

    def normalise(self) -> NormalisedEvent:
        """This event in provider-neutral words.

        `owner_id` is always `None` for the same reason it is on Apple: Google
        echoes nothing of ours. `obfuscatedExternalAccountId` *could* carry our
        user id, and deliberately does not — it is set by the app when the
        purchase flow starts, which makes it a field the client chooses, and the
        seam's rule is that a grant is never read out of a field the payer can
        write. The owner comes from the authenticated caller on the verify path
        and from our own rows on the notification path.
        """
        return NormalisedEvent(
            provider=GooglePlayProvider.name,
            id=self.id,
            type=self.type,
            kind=_kind_of(self.type),
            owner_id=None,
            product=self.product,
            subscription_id=self.subscription_id,
            transaction_id=self.transaction_id,
            amount_cents=self.amount_cents(),
            currency=self.currency(),
            country=self.country,
            buyer_email=None,
            status=self.status,
            renews_at=self.renews_at,
            adjustment=self.adjustment,
            account_token=self.account_token,
            grants=self._grants,
            revokes=self.type in REVOKING,
            moves_money=bool(self.transaction_id) and self.type in MONEY_EVENTS,
            priced_by_us=False,
            payload={"notification": self.notification, "purchase": self.state},
        )

    @property
    def _grants(self) -> bool:
        """Whether this event should open or extend access.

        Two conditions, and the second is Google's alone. The type has to be one
        that grants — and the subscription has to be in a state that is actually
        live. A `SUBSCRIPTION_RECOVERED` for a plan Google has since expired, or
        a renewal notification redelivered days later against a subscription now
        `ON_HOLD`, would otherwise extend a grant by a whole period on the
        strength of an integer. The state is the fresher fact: it came from the
        API call `enrich` made a moment ago, and the notification is a claim
        about the past.
        """
        if self.type not in GRANTING:
            return False
        if self.kind_word == "one_time_product":
            return True
        return self.status in LIVE_STATES

    def normalise_as_purchase(self) -> NormalisedEvent:
        """The verify path's event: a payment, whatever the product turns out to be.

        `type` is already `"purchase"`, which `_kind_of` maps to `PAYMENT`. What
        this adds is the two flags a bare `normalise()` would have to work out
        from a notification code that is not there. A purchase verified from the
        app always grants and always moved money — the sheet closed and Google
        confirmed it — and saying so here keeps `_grants` free of a special case
        that would read as a general rule.
        """
        return replace(
            self.normalise(), grants=True, moves_money=bool(self.transaction_id)
        )

    def with_state(self, state: dict) -> Event:
        return Event(
            id=self.id,
            type=self.type,
            purchase_token=self.purchase_token,
            notification=self.notification,
            state=state,
        )


# ── which notifications change what a person can read ──────────────────────
#
# Everything not named below is recorded and ignored. Google's table has
# twenty-odd entries and most of them are about billing mechanics we have no
# opinion on.

#: Access begins, or is extended by another period.
#:
#: `subscription.1` (RECOVERED) and `subscription.7` (RESTARTED) are here beside
#: the obvious two because both mean the plan is live again and has been paid
#: for — recovery from account hold, and a user restoring a cancelled plan from
#: the Play subscriptions screen. Both are gated on the live-state check in
#: `_grants`, which is what stops a stale redelivery extending anything.
GRANTING = frozenset({
    "subscription.1",   # SUBSCRIPTION_RECOVERED
    "subscription.2",   # SUBSCRIPTION_RENEWED
    "subscription.4",   # SUBSCRIPTION_PURCHASED
    "subscription.7",   # SUBSCRIPTION_RESTARTED
    "one_time_product.1",  # ONE_TIME_PRODUCT_PURCHASED
})

#: ...and which end access.
#:
#: Read this against `IGNORED_REASONS`, where five types that look exactly like
#: revocations are listed with the reason each one is not — and against Apple's
#: `REVOKING`, which reaches the same three answers through different words. The
#: two stores must not disagree about what happens to somebody who cancels.
REVOKING = frozenset({
    "subscription.12",  # SUBSCRIPTION_REVOKED — ended before expiry, money back
    "subscription.13",  # SUBSCRIPTION_EXPIRED — the paid period is over
    "voided_purchase",  # a refund or chargeback on any product
})

#: The notifications on which money moved.
MONEY_EVENTS = frozenset({
    "subscription.1",
    "subscription.2",
    "subscription.4",
    "subscription.7",
    "one_time_product.1",
    "voided_purchase",
})

#: Why each notification we deliberately do nothing with is doing nothing.
#:
#: Not read by any code path. The first five look like revocations and are not,
#: and the next person to add a line to `REVOKING` should have to read past the
#: reason it was left out.
IGNORED_REASONS: dict[str, str] = {
    "subscription.3": (
        "SUBSCRIPTION_CANCELED. Cancelling is not refunding: Play's own "
        "documentation says the subscription remains valid until its expiry "
        "time, and somebody who cancels on the 3rd has paid through the end of "
        "the period. Taking the reading away at the moment they press the button "
        "is charging for a month and delivering three days, and it is the click "
        "most likely to be followed by a chargeback. `subscription.13` closes it."
    ),
    "subscription.5": (
        "SUBSCRIPTION_ON_HOLD. Dunning — Google is still retrying the card. The "
        "grant already carries an expiry, so letting it lapse is the honest "
        "outcome if the retries fail; revoking here takes the product from "
        "somebody whose payment is about to succeed."
    ),
    "subscription.6": (
        "SUBSCRIPTION_IN_GRACE_PERIOD. Dunning again, and this one is Google "
        "explicitly asking us to keep serving while it retries."
    ),
    "subscription.10": (
        "SUBSCRIPTION_PAUSED. A pause stops billing; it does not send money "
        "back. The expiry already covers the period that was paid for."
    ),
    "subscription.20": (
        "SUBSCRIPTION_PENDING_PURCHASE_CANCELED. A purchase that never "
        "completed — a slow payment method the buyer abandoned. Nothing was "
        "granted, so there is nothing to revoke, and putting it in REVOKING "
        "would run a revocation against an id that matches no row until the day "
        "it matches one."
    ),
    "subscription.9": (
        "SUBSCRIPTION_DEFERRED. We moved the next charge later, usually as an "
        "apology. It changes what Google will bill and not what has been paid; "
        "the grant's own expiry catches up at the next renewal."
    ),
    "subscription.11": (
        "SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED. A plan for a future pause."
    ),
    "subscription.17": (
        "SUBSCRIPTION_ITEMS_CHANGED. A bundle changing shape. The ladder sells "
        "one product per subscription, so this cannot arrive; when it can, it "
        "has to re-scope the grant, and `entitlements.grant` cannot re-scope "
        "without also extending by a whole period."
    ),
    "subscription.18": (
        "SUBSCRIPTION_CANCELLATION_SCHEDULED. An installment plan ending at the "
        "commitment date. We sell no installment plans."
    ),
    "subscription.19": (
        "SUBSCRIPTION_PRICE_CHANGE_UPDATED, and 22 (price step-up consent) with "
        "it. Both are about what the *next* charge will be."
    ),
    "one_time_product.2": (
        "ONE_TIME_PRODUCT_CANCELED. A pending purchase the buyer abandoned. "
        "Nothing was granted."
    ),
    "test": (
        "The delivery Google sends when somebody presses the button in the Play "
        "Console. It carries no purchase token, so it records itself as a "
        "webhook event and grants nothing — which is what the button is for."
    ),
}


_KINDS: dict[str, EventKind] = {
    "subscription.1": EventKind.SUBSCRIPTION_RENEWED,
    "subscription.2": EventKind.SUBSCRIPTION_RENEWED,
    "subscription.3": EventKind.SUBSCRIPTION_CANCELLED,
    "subscription.4": EventKind.SUBSCRIPTION_STARTED,
    "subscription.5": EventKind.SUBSCRIPTION_DUNNING,
    "subscription.6": EventKind.SUBSCRIPTION_DUNNING,
    "subscription.7": EventKind.SUBSCRIPTION_RENEWED,
    "subscription.9": EventKind.SUBSCRIPTION_UPDATED,
    "subscription.10": EventKind.SUBSCRIPTION_PAUSED,
    "subscription.11": EventKind.SUBSCRIPTION_UPDATED,
    "subscription.12": EventKind.SUBSCRIPTION_ENDED,
    "subscription.13": EventKind.SUBSCRIPTION_ENDED,
    "subscription.17": EventKind.SUBSCRIPTION_UPDATED,
    "subscription.18": EventKind.SUBSCRIPTION_UPDATED,
    "subscription.19": EventKind.SUBSCRIPTION_UPDATED,
    "subscription.20": EventKind.PAYMENT_FAILED,
    "one_time_product.1": EventKind.PAYMENT,
    "one_time_product.2": EventKind.PAYMENT_FAILED,
    "voided_purchase": EventKind.ADJUSTMENT,
    # The verify path, where the app tells us a purchase completed and the API
    # call is what makes that checkable.
    "purchase": EventKind.PAYMENT,
}


def _kind_of(event_type: str) -> EventKind:
    return _KINDS.get(event_type, EventKind.UNKNOWN)


def parse(payload: dict, headers: Mapping[str, str] | None = None) -> Event:
    """Read one Pub/Sub push into an `Event`, without asking Google anything yet.

    The envelope is `{"message": {"data": <base64>, "messageId": …}, "subscription": …}`
    and the interesting part is the base64, which decodes to a
    `DeveloperNotification` carrying exactly one of four mutually exclusive
    bodies.

    The package name is checked here rather than later. A notification for
    another app cannot happen through a push subscription we own, but the check
    costs nothing and it is the one that would catch a Pub/Sub topic
    misconfigured to point at somebody else's Play account — which is a mistake
    that produces perfectly valid deliveries granting readings to strangers.

    `headers` is accepted and unused: `messageId` is in the body. The parameter
    exists because Standard Webhooks puts the per-delivery id in a header.
    """
    message = payload.get("message")
    message = message if isinstance(message, dict) else {}
    encoded = message.get("data")
    if not isinstance(encoded, str) or not encoded:
        raise InvalidSignature("Pub/Sub message carries no data")
    try:
        notification = json.loads(base64.b64decode(encoded))
    except (binascii.Error, ValueError) as exc:
        raise InvalidSignature("Pub/Sub message data is not base64 JSON") from exc
    if not isinstance(notification, dict):
        raise InvalidSignature("the developer notification is not an object")

    expected = settings().google_play_package
    if expected and str(notification.get("packageName") or "") != expected:
        raise InvalidSignature(
            f"notification is for package {notification.get('packageName')!r}, "
            f"not {expected!r}"
        )

    kind, code, token = _which_body(notification)
    return Event(
        id=str(message.get("messageId") or ""),
        type=f"{kind}.{code}" if code else kind,
        purchase_token=token,
        notification=notification,
        state={},
    )


def _which_body(notification: dict) -> tuple[str, int | None, str]:
    """Which of the four mutually exclusive bodies arrived, and its token.

    Ordered rather than searched, because Google states they are mutually
    exclusive and an order makes the tie impossible to get wrong if they ever
    stop being. `test` last, because a test notification is the only one that
    carries no token at all and it must not be mistaken for a malformed one.
    """
    for key, name in (
        ("subscriptionNotification", "subscription"),
        ("oneTimeProductNotification", "one_time_product"),
    ):
        body = notification.get(key)
        if isinstance(body, dict):
            code = body.get("notificationType")
            return name, int(code) if isinstance(code, int) else 0, str(
                body.get("purchaseToken") or ""
            )
    voided = notification.get("voidedPurchaseNotification")
    if isinstance(voided, dict):
        return "voided_purchase", None, str(voided.get("purchaseToken") or "")
    return "test", None, ""


def entitlement_for(event: Event) -> Grant | None:
    """What this Play event should grant, if anything. See `paddle.entitlement_for`."""
    return _entitlement_for(event.normalise())


class GooglePlayProvider:
    """Google Play as a `StoreProvider`."""

    name = "googleplay"
    granting = GRANTING
    revoking = REVOKING
    manage_url = MANAGE_URL

    #: The legal seller. Google is the merchant of record for Play billing,
    #: which is what removes the EU OSS registration, the Brazilian CNPJ and
    #: every US state registration from this business.
    #:
    #: **Unverified against a contract**, and imprecise in the same way Apple's
    #: is: the entity on a buyer's statement depends on their country — Google
    #: Commerce Ltd. in much of the world, Google Payment Corp. and others
    #: elsewhere. This string is published on the refunds page, which is what a
    #: card issuer reads during a dispute, so it has to be confirmed before
    #: launch or become a per-region lookup.
    merchant = "Google"

    requires_email = False

    #: Google emails the receipt, as the seller. See the field on the protocol.
    issues_the_receipt = True

    def __init__(self, client: GooglePlayClient | None = None) -> None:
        # Built lazily: a provider being asked only to parse a notification
        # should not have to care whether a service account exists.
        self._client = client

    @property
    def client(self) -> GooglePlayClient:
        if self._client is None:
            self._client = GooglePlayClient()
        return self._client

    def verify(
        self, raw_body: bytes, headers: Mapping[str, str], *, secret: str | None = None
    ) -> None:
        verify(raw_body, headers, secret=secret)

    def parse(
        self, payload: dict, headers: Mapping[str, str] | None = None
    ) -> NormalisedEvent:
        """The notification as it arrived, before Google has been asked anything.

        Deliberately incomplete: no product, no order id, no expiry. The router
        calls `enrich` next, and it does so **after** the idempotency check, so a
        redelivered message never costs an API call. Google's documentation asks
        for that in as many words.
        """
        return parse(payload, headers).normalise()

    async def enrich(self, event: NormalisedEvent) -> NormalisedEvent:
        """Go and ask Google what this notification was about.

        The one adapter where this does anything, and the reason the method is
        on the protocol at all. Without it a renewal has no product to grant, no
        order id to record the money against, and no state to check the grant is
        still warranted.

        A voided purchase is returned untouched: it carries its own order id and
        its own refund type, the token behind it is by definition no longer
        valid, and asking about it would spend quota to be told nothing.

        A failure raises. The router records the error and re-raises, Pub/Sub
        retries, and the retry finds the same `messageId` already recorded —
        which is exactly the shape that makes at-least-once delivery safe.
        """
        found = parse_of(event)
        if found is None or not found.purchase_token or found.kind_word in {
            "voided_purchase",
            "test",
        }:
            return event

        if found.kind_word == "one_time_product":
            product_id = str(
                (found.notification.get("oneTimeProductNotification") or {}).get("sku") or ""
            )
            if not product_id:
                log.error("one-time notification %s names no sku", found.id)
                return event
            state = await self.client.product(product_id, found.purchase_token)
            # `products.get` answers without the product id it was asked about,
            # so it is put back: everything downstream reads the product off the
            # state, and a state with no product grants nothing.
            state = {**state, "productId": product_id}
        else:
            state = await self.client.subscription(found.purchase_token)

        return found.with_state(state).normalise()

    async def verify_purchase(self, *, transaction: str, product: str) -> NormalisedEvent:
        """Check one purchase token against Google and say what it grants.

        `transaction` is `Purchase.purchaseToken` from the Play Billing Library.
        Unlike Apple's it proves nothing on its own — it is a key into Google's
        database — so this always makes a network call, and the client should
        expect it to take the time an API call takes.

        Which endpoint to ask is decided by **our catalogue**, not by the client:
        a product with an interval is a subscription and anything else is a
        one-time purchase. That is deliberate. Letting the request say which
        would let it ask the subscription endpoint about a door and the product
        endpoint about a plan, and the answers differ in exactly the field the
        grant is keyed on.

        Three refusals: a token Google does not recognise (a `BillingUnavailable`
        carrying Google's 404 — see `GooglePlayClient._get` for why it is not a
        distinct exception), a purchase that has not settled or has been voided,
        and a product that is not the one being claimed.
        """
        from . import catalogue as prices

        try:
            item = prices.product(product)
        except ValueError as exc:
            raise ProductMismatch(str(exc)) from exc

        product_id = _store_id(product)
        if item.interval:
            state = await self.client.subscription(transaction)
            _check_subscription_is_live(state)
        else:
            state = await self.client.product(product_id, transaction)
            _check_product_is_bought(state)
            # Google's own `productId` wins, and only where Google omitted it
            # do we fall back to the one we asked about.
            #
            # This used to stamp `product_id` unconditionally — the product the
            # *client claimed* — and then read it straight back out for the
            # `found != product` comparison forty lines below, which made that
            # comparison unable to fail on this path. The exploit it looks like
            # (present a $5.99 door token as `archive`) does not actually work,
            # because Google answers 404 to
            # `purchases/products/alma.archive/tokens/<door-token>` and `_get`
            # turns that into `BillingUnavailable`. But that is one HTTP status
            # in somebody else's API holding the whole gate, and it misfiles the
            # failure: a deliberate forgery surfaced as 503 "we could not ask,
            # try again", which is the one answer that invites an infinite retry
            # and the one log line nobody alerts on.
            #
            # With Google's own value kept, the check below has something real
            # to compare and a mismatch reads as a mismatch.
            state = {**state, "productId": state.get("productId") or product_id}

        event = Event(
            id="",
            type="purchase",
            purchase_token=transaction,
            notification={},
            state=state,
        )
        found = event.product
        if found is None:
            raise ProductMismatch(
                f"{event.product_id!r} is not a product this price list sells"
            )
        if found != product:
            # Reachable on both paths now. On the subscription path Google is
            # asked about a token rather than about a product, so a token for
            # the monthly plan presented as a claim on the annual answers
            # `monthly` here. On the one-time path it is reachable whenever
            # Google returns a `productId` at all — see the comment above about
            # why this comparison used to be dead code there.
            raise ProductMismatch(
                f"Google says this token bought {found!r}; {product!r} was claimed"
            )
        if not event.transaction_id:
            raise BillingUnavailable(
                "Google returned a purchase with no order id — there is nothing "
                "to record the money against or to make the grant idempotent on"
            )

        # The id is the order id and not the purchase token, and it is set here
        # rather than at construction because only Google knows it: the token is
        # what the app holds, and it is both too long for the column and stable
        # across renewals, so filing a purchase under it would collide the
        # twelfth month with the first.
        return replace(
            event.normalise_as_purchase(), id=f"{self.name}:{event.transaction_id}"
        )

    async def open_session(
        self,
        *,
        product: str,
        user_id: str,
        currency: str,
        country: str | None = None,
        email: str | None = None,
    ) -> SessionHandle:
        """There is no server-created checkout on Google Play. See the Apple twin."""
        raise BillingUnavailable(
            "purchases on Google Play are opened by the app through the Play "
            "Billing Library; there is no checkout for a server to create"
        )

    async def cancel_subscription(self, subscription_id: str) -> None:
        """Play *does* expose a cancel, and we deliberately do not call it.

        `purchases.subscriptionsv2.cancel` exists and works. Three reasons not
        to use it, and the first two are the ones that matter.

        It needs the **purchase token**, which we do not keep: a token runs to
        around a thousand characters and every identifier column in the schema
        is 64, so calling it would mean a new column holding a credential-shaped
        blob for every subscriber, for the sake of a button Play already has.

        It would be a second cancellation path for one subscription. The
        customer can always cancel in Play, so ours would be the copy that has
        to stay in agreement with theirs, and the failure of that is somebody
        who cancelled in Play being told by us that their plan renews — which is
        the sentence most likely to be followed by a chargeback.

        And Play's own subscription centre is where Google expects people to go.
        So the honest answer is the link, raised as `SelfServiceOnly` so the
        router can hand it to the client rather than apologise.
        """
        raise SelfServiceOnly(
            "a Google Play subscription is cancelled by its owner, in the Play "
            "subscriptions screen",
            manage_url=f"{MANAGE_URL}?package={settings().google_play_package}",
        )

    async def buyer_address(self, event: NormalisedEvent) -> str | None:
        """Google tells us nothing about the buyer, and does not need to.

        `subscribeWithGoogleInfo.emailAddress` exists and is populated only for
        the small set of purchases made through Subscribe with Google, which is
        not how a Play Billing purchase arrives. Reading it would produce an
        address for one buyer in a thousand and `None` for the rest, which is a
        worse shape than `None` for everyone: a receipt path that fires
        occasionally is one nobody notices is broken.

        It does not matter, because Google is the merchant of record and sends
        the receipt itself. See `issues_the_receipt`.
        """
        return None


def _store_id(slug: str) -> str:
    return store_product_id(slug, processor=GooglePlayProvider.name)


def _check_subscription_is_live(state: dict) -> None:
    """Refuse a subscription Google says is not in force."""
    status = str(state.get("subscriptionState") or "")
    if status not in LIVE_STATES:
        raise PurchaseIncomplete(f"Google says this subscription is {status or 'unknown'}")


def _check_product_is_bought(state: dict) -> None:
    """Refuse a one-time purchase that has not settled, or has been undone.

    `purchaseState` is 0 purchased, 1 cancelled, 2 pending. Pending is a real
    and ordinary state on Play — cash at a convenience store, a slow bank
    transfer — and it is not a forgery: the honest answer is "not yet", which is
    why it is `PurchaseIncomplete` and not `InvalidSignature`. Google will send
    a `one_time_product.1` notification when it settles, and that grants.
    """
    state_code = state.get("purchaseState")
    if state_code == PURCHASED:
        return
    if state_code == PENDING:
        raise PurchaseIncomplete("Google says this purchase is still pending")
    raise PurchaseIncomplete(
        f"Google says this purchase is not in force (purchaseState {state_code!r})"
    )


def parse_of(event: NormalisedEvent) -> Event | None:
    """Rebuild the adapter's own `Event` from a normalised one.

    `enrich` is handed a `NormalisedEvent` because that is the vocabulary the
    router holds, and it needs the purchase token, which is not on it — the
    token is a credential for Google's API and has no business in the seam's
    shared shape. So it travels where the verbatim payload travels, and is read
    back here.

    Returns `None` for an event from another adapter, which cannot happen
    through the router and is exactly the sort of thing that becomes possible
    the day somebody adds a reconciliation job.
    """
    if event.provider != GooglePlayProvider.name:
        return None
    notification = (event.payload or {}).get("notification")
    if not isinstance(notification, dict):
        return None
    _kind, _code, token = _which_body(notification)
    return Event(
        id=event.id,
        type=event.type,
        purchase_token=token,
        notification=notification,
        state=(event.payload or {}).get("purchase") or {},
    )
