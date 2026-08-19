"""Paddle, behind the seam: one processor's shape, translated into ours.

Two things here are load-bearing and everything else is glue.

**The signature.** A webhook endpoint that grants paid access is an endpoint
that grants paid access to whoever can POST to it, unless the signature is
verified first. Paddle signs the raw body with an HMAC keyed on a shared
secret, and the comparison is constant-time — a timing-comparable check on a
signature is a signature check that can be brute-forced a byte at a time.

**Idempotency.** Providers retry, deliberately and correctly. Every event id
is recorded before it is processed, and a second delivery of the same id does
nothing at all. Without that, a retried `transaction.completed` grants the
same purchase twice, and the person who notices is the one asking for a
refund.

What is *not* here any more is the vocabulary. `Grant`, `PERIOD`,
`entitlement_for` and the replay window moved to `provider.py`, because none of
them is about Paddle: they are about what we sell and how long a period lasts.
What is left in this file is the part that would be thrown away if we were
refused by Paddle tomorrow — a header format, a signed-message layout, the
names of fields inside a payload, and a list of event strings. `PaddleProvider`
is the adapter; nothing above it should import anything else from here.

No credentials appear in this file. `PADDLE_API_KEY` and
`PADDLE_WEBHOOK_SECRET` come from the environment; the account holder puts
them there.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

import httpx

from ..config import settings
from . import http
from .provider import (
    MAX_SIGNATURE_AGE,
    PERIOD,
    BillingUnavailable,
    EventKind,
    Grant,
    InvalidSignature,
    NormalisedEvent,
    SessionHandle,
    check_freshness,
    header_value,
    moment,
    sealed_owner,
    stamp,
)
from .provider import entitlement_for as _entitlement_for

log = logging.getLogger("alma.billing")

#: Re-exported so that everything already importing them from here keeps
#: working, and so that `paddle.MAX_SIGNATURE_AGE` still means what it did.
#: The definitions live in `provider.py`; these are the same objects.
__all__ = [
    "GRANTING",
    "MAX_SIGNATURE_AGE",
    "MONEY_EVENTS",
    "PERIOD",
    "REVOKING",
    "SIGNATURE_HEADER",
    "Event",
    "Grant",
    "InvalidSignature",
    "PaddleClient",
    "PaddleProvider",
    "entitlement_for",
    "parse",
    "verify",
]

SANDBOX_API = "https://sandbox-api.paddle.com"
LIVE_API = "https://api.paddle.com"

#: Paddle carries the whole signature in one header, as `ts=…;h1=…`. Dodo
#: needs three (Standard Webhooks). Neither number is inherent to signing a
#: webhook, which is why the protocol hands an adapter the whole mapping.
SIGNATURE_HEADER = "Paddle-Signature"


@dataclass(frozen=True, slots=True)
class Event:
    """A Paddle webhook, read lazily off the payload it arrived in.

    A view rather than a copy, because the fields worth reading differ per
    event family and half of them are absent on any given delivery. The
    provider-neutral summary is `normalise()`; everything above the adapter
    reads that instead.
    """

    id: str
    type: str
    payload: dict

    @property
    def data(self) -> dict:
        return self.payload.get("data", {})

    @property
    def transaction_id(self) -> str | None:
        """The transaction this event is *about*.

        The order of the fallback is load-bearing and used to be reversed. On a
        transaction event the id lives in `data.id`; on an **adjustment** — a
        refund, a credit, a chargeback — `data.id` is the adjustment's own id
        (`adj_…`) and the transaction it reduces is in `data.transaction_id`.
        Preferring `data.id` therefore attached every refund to a transaction
        that does not exist, so the purchase it reduces was never found, never
        marked, and the refund was inserted as a second, positive purchase row.
        Asking for `transaction_id` first is right for both shapes, because a
        transaction event does not carry that field at all.
        """
        return self.data.get("transaction_id") or self.data.get("id")

    @property
    def adjustment_id(self) -> str | None:
        """The adjustment's own id, on the events that have one."""
        return self.data.get("id") if self.data.get("transaction_id") else None

    @property
    def adjustment(self) -> tuple[str, str] | None:
        """(action, type) for an adjustment — e.g. ("refund", "partial").

        Read rather than assumed, because the three things Paddle sends here
        mean different things to us: a full refund closes what it paid for, a
        partial refund reduces a charge and closes nothing, and a chargeback is
        a full refund we did not choose. Treating them alike either takes
        access away from somebody who was refunded five dollars of forty, or
        leaves it with somebody who was refunded everything.
        """
        action = self.data.get("action")
        return (str(action), str(self.data.get("type") or "partial")) if action else None

    @property
    def subscription_id(self) -> str | None:
        """The subscription this event belongs to, on every shape that has one.

        A renewal is a new transaction with a new id every month, so the
        transaction id cannot identify the plan. Without this, a cancellation
        matches only the row belonging to the charge it names and every earlier
        row keeps its future expiry — the subscription is cancelled and the
        access it granted never stops.
        """
        data = self.data
        return (
            data.get("subscription_id")
            or (data.get("id") if self.type.startswith("subscription.") else None)
            or self.custom.get("subscription_id")
        )

    @property
    def status(self) -> str | None:
        """The provider's own word for the subscription's state.

        Recorded and never consulted by `Entitlement.covers` — access is
        decided by the expiry and the revocation, which we set ourselves. The
        day they rename one of these strings must not be the day everybody who
        has paid is locked out.
        """
        value = self.data.get("status")
        return str(value) if value else None

    @property
    def renews_at(self) -> datetime | None:
        """When Paddle says it will charge this plan again."""
        return moment(self.data.get("next_billed_at"))

    @property
    def custom(self) -> dict:
        return self.data.get("custom_data") or {}

    @property
    def user_id(self) -> str | None:
        """Who Paddle says this payment belongs to. **Not yet trustworthy.**

        The raw field, kept raw so that support reading a delivery sees what
        arrived. `normalise()` reads the sealed pair instead — Paddle's client
        token is public by design, so anybody can open an overlay against our
        account with any `customData` they like, and the signature on the
        webhook only proves Paddle echoed it. See `provider.stamp`.
        """
        return self.custom.get("user_id")

    @property
    def product_slug(self) -> str | None:
        """What Paddle says was bought. **Not yet trustworthy** — see `user_id`."""
        return self.custom.get("product")

    @property
    def country(self) -> str | None:
        address = self.data.get("billing_details") or {}
        return (address.get("address") or {}).get("country_code") or self.data.get("country_code")

    @property
    def buyer_email(self) -> str | None:
        """The address Paddle collected, **if this delivery happens to carry it**.

        Usually it does not, and that is the whole reason `buyer_address` on the
        provider is a coroutine. A transaction payload names a `customer_id` and
        stops there; only an account configured to expand the customer, or one
        of the shapes that carries `billing_details`, puts an address in the
        body. Read here anyway because a value already in hand is worth more
        than the same value fetched over the network a second later.
        """
        customer = self.data.get("customer") or {}
        billing = self.data.get("billing_details") or {}
        value = customer.get("email") or billing.get("email")
        return str(value) if value else None

    def amount_cents(self) -> int:
        totals = (self.data.get("details") or {}).get("totals") or {}
        raw = totals.get("grand_total") or self.data.get("total") or "0"
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    def currency(self) -> str:
        return self.data.get("currency_code") or "USD"

    def normalise(self) -> NormalisedEvent:
        """This event in provider-neutral words.

        The three booleans are answered here, using Paddle's own event strings,
        so that nothing upstream ever has to hold another company's vocabulary.
        `moves_money` repeats the transaction-id condition on purpose: a
        `subscription.*` event carries a subscription id in `data.id` and no
        payment at all, so recording one as a purchase wrote a zero-amount row
        whose "transaction id" had never identified money.

        The owner and the product come from `sealed_owner`, not from
        `self.user_id` and `self.product_slug`. Those two read `custom_data`
        straight, and `custom_data` on this processor is a field the payer can
        write: paddle.js takes `customData` as an argument and the client token
        that opens an overlay is published to every browser. Preferring the
        sealed pair over the price-id lookup is the right order round —
        `_key_from_price_id` answers only for a checkout somebody opened outside
        our own flow, and it cannot answer at all while every processor
        identifier in the catalogue is the empty string.
        """
        owner, product = sealed_owner(self.custom)
        return NormalisedEvent(
            provider=PaddleProvider.name,
            id=self.id,
            type=self.type,
            kind=_kind_of(self.type),
            owner_id=owner,
            product=product or _key_from_price_id(self),
            subscription_id=self.subscription_id,
            transaction_id=self.transaction_id,
            amount_cents=self.amount_cents(),
            currency=self.currency(),
            country=self.country,
            buyer_email=self.buyer_email,
            status=self.status,
            renews_at=self.renews_at,
            adjustment=self.adjustment,
            grants=self.type in GRANTING,
            revokes=self.type in REVOKING,
            moves_money=bool(self.transaction_id) and self.type.startswith(MONEY_EVENTS),
            payload=self.payload,
        )


def verify(raw_body: bytes, signature_header: str, *, secret: str | None = None) -> None:
    """Verify a Paddle webhook signature, or raise.

    Header form: `ts=1700000000;h1=<hex>`. The signed payload is the
    timestamp, a colon, then the raw body — raw, not re-serialised, because
    re-encoding JSON changes bytes and therefore changes the digest.
    """
    key = secret if secret is not None else settings().paddle_webhook_secret
    if not key:
        raise InvalidSignature(
            "PADDLE_WEBHOOK_SECRET is not set — refusing to accept an unverified "
            "webhook that grants paid access"
        )
    if not signature_header:
        raise InvalidSignature("no signature header")

    parts = dict(
        piece.split("=", 1) for piece in signature_header.split(";") if "=" in piece
    )
    timestamp, provided = parts.get("ts"), parts.get("h1")
    if not timestamp or not provided:
        raise InvalidSignature("malformed signature header")

    check_freshness(timestamp)

    expected = hmac.new(
        key.encode(), f"{timestamp}:".encode() + raw_body, hashlib.sha256
    ).hexdigest()

    # Constant time: a comparison that returns early leaks the signature one
    # byte at a time to anyone willing to measure. Called here rather than
    # through a shared helper deliberately — `hmac.compare_digest` has to be
    # visible at the call site, and a test reads this function's source to make
    # sure it still is, because a `==` here passes every functional test that
    # will ever be written for it.
    if not hmac.compare_digest(expected, provided):
        raise InvalidSignature("signature does not match")


def parse(payload: dict) -> Event:
    return Event(
        id=str(payload.get("event_id") or payload.get("notification_id") or ""),
        type=str(payload.get("event_type") or ""),
        payload=payload,
    )


#: Which events change what a person can read. Anything else is recorded and
#: ignored — an unknown event type is not an error, it is Paddle shipping a
#: feature we have not adopted.
#:
#: **`transaction.paid` is deliberately not here, and used to be.** Paddle emits
#: both it and `transaction.completed` for a single charge; they carry the same
#: subscription id and arrive under different event ids, so insert-before-
#: process does not collapse them, and `entitlements.grant` extends a
#: subscription row by a whole `PERIOD` on each call. One month's money bought
#: two months, every month, with the expiry drifting further ahead of the
#: payments and nothing reporting it — a monthly subscriber who cancelled after
#: a year still held access for another year. `transaction.completed` is the
#: settled one and is the only one that may grant; `transaction.paid` still
#: records money through `MONEY_EVENTS`, which is the thing only it can do when
#: it arrives first.
#:
#: Dodo's rule for the same shape cannot be copied across, and it is worth
#: saying why: there, a payment carrying a subscription id never grants, because
#: `subscription.renewed` does. Paddle has no renewal event at all — a renewal
#: arrives as another `transaction.completed` with a subscription id on it — so
#: that condition here would stop every renewal from ever extending anything.
GRANTING = frozenset({"transaction.completed", "subscription.activated"})

#: ...and which end access. Money coming back, and nothing else.
#:
#: **`subscription.canceled` and `subscription.past_due` were here and are not
#: any more**, and that is a product decision rather than a refactor. Both took
#: a reading away from somebody who had paid for it.
#:
#: A cancellation is not a refund. Somebody who cancels a year in month two has
#: paid for ten more months and is owed every day of them; `/subscription/cancel`
#: says so, the subscription-terms page says so — "the plan then runs to the end
#: of the month you have already paid for, and stops" — and Paddle emits this
#: event *in response to our own cancel call*, so pressing the button promised a
#: date and then revoked before the page finished reloading. `past_due` is
#: worse: it is Paddle's dunning state, a card that will very likely succeed on
#: the retry, and the person whose card bounced is the person least able to
#: argue about it.
#:
#: What ends a plan is its expiry, which every recurring grant carries because
#: `grant()` refuses to write one without a duration. Both events are still read
#: — see `_note_the_plan` in the router — to clear `renews_at` and record the
#: status, so the account screen stops promising a charge that will not happen.
#: This is now the same rule the Dodo adapter follows, which matters: the two
#: processors must not disagree about what happens to a person who cancels.
REVOKING = frozenset({
    "transaction.refunded",
    "adjustment.created",
})

#: The event families that move money. A `subscription.*` event carries a
#: subscription id in `data.id` and no payment at all, so recording one as a
#: purchase wrote a zero-amount row whose "transaction id" was a subscription —
#: a row in the money trail that never corresponded to money.
MONEY_EVENTS = ("transaction.", "adjustment.")


#: Paddle's event strings, in our taxonomy. A family prefix is not enough on
#: its own — `transaction.completed` and `transaction.payment_failed` are the
#: same family and opposite outcomes — so the exact strings are listed and
#: everything unrecognised falls through to a prefix and then to UNKNOWN.
#:
#: Two of our kinds have no Paddle string at all, and that is Paddle rather
#: than us. A **renewal** arrives here as another `transaction.completed`
#: carrying a subscription id, not as an event of its own — Dodo sends
#: `subscription.renewed` — and Paddle has no separate "expired" event either,
#: because it folds the end of a plan into `subscription.canceled`. Both kinds
#: exist because the second processor distinguishes them, which is the whole
#: reason the taxonomy is ours and not a rename of somebody's event list.
_KINDS: dict[str, EventKind] = {
    "transaction.completed": EventKind.PAYMENT,
    "transaction.paid": EventKind.PAYMENT,
    "transaction.payment_failed": EventKind.PAYMENT_FAILED,
    "transaction.refunded": EventKind.ADJUSTMENT,
    "subscription.activated": EventKind.SUBSCRIPTION_STARTED,
    "subscription.created": EventKind.SUBSCRIPTION_STARTED,
    "subscription.resumed": EventKind.SUBSCRIPTION_UPDATED,
    "subscription.updated": EventKind.SUBSCRIPTION_UPDATED,
    "subscription.past_due": EventKind.SUBSCRIPTION_DUNNING,
    "subscription.paused": EventKind.SUBSCRIPTION_PAUSED,
    "subscription.canceled": EventKind.SUBSCRIPTION_CANCELLED,
}


def _kind_of(event_type: str) -> EventKind:
    known = _KINDS.get(event_type)
    if known is not None:
        return known
    if event_type.startswith("adjustment."):
        return EventKind.ADJUSTMENT
    return EventKind.UNKNOWN


def entitlement_for(event: Event) -> Grant | None:
    """What this Paddle event should grant, if anything.

    A translation and a delegation: the rule itself — that a recurring plan is
    recognised by the catalogue having given the product an interval — is ours
    and lives in `provider.py`, where the Dodo adapter reaches the same answer
    through the same function rather than through a second copy of it.
    """
    return _entitlement_for(event.normalise())


def _key_from_price_id(event: Event) -> str | None:
    """The catalogue key behind a checkout opened outside our own flow.

    A support tool, say, which has a price id and no `custom_data`.
    `by_price_id` answers with the key, so nothing here has to infer one from
    a kind — inferring is what turned a monthly price id into a year.

    Narrowed to this processor's identifiers. Two processors could issue the
    same string, and matching the other one's would grant against a product this
    payment did not buy.
    """
    from .catalogue import by_price_id

    for line in (event.data.get("items") or []):
        price_id = (line.get("price") or {}).get("id") or line.get("price_id")
        found = by_price_id(price_id or "", PaddleProvider.name)
        if found is not None:
            return found
    return None


class PaddleClient:
    """The small part of the Paddle API we actually call."""

    def __init__(self, api_key: str | None = None, environment: str | None = None) -> None:
        config = settings()
        self.api_key = api_key or config.paddle_api_key
        self.base = (
            SANDBOX_API
            if (environment or config.paddle_environment) != "production"
            else LIVE_API
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def transaction(self, transaction_id: str) -> dict | None:
        """Fetch a transaction, for reconciling a webhook we are unsure about."""
        if not self.configured:
            return None
        try:
            # Общий клиент процесса — см. `billing/http.py`.
            response = await http.client().get(
                f"{self.base}/transactions/{transaction_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            if response.status_code >= 400:
                log.error("paddle refused: %s %s", response.status_code, response.text[:300])
                return None
            return response.json().get("data")
        except httpx.HTTPError as exc:
            log.error("paddle unreachable: %s", exc)
            return None

    async def customer_email(self, customer_id: str) -> str | None:
        """The address Paddle collected from one buyer, or `None`.

        A read that shrugs, on purpose. Everything this feeds is a receipt, and
        the alternative to a missing receipt is a webhook that fails and is
        retried — which is how one payment becomes two grants. So a key that is
        not set, a customer Paddle will not talk about and a network that is
        down all answer the same quiet `None`, and the caller logs it.
        """
        if not self.configured or not customer_id:
            return None
        try:
            response = await http.client().get(
                f"{self.base}/customers/{customer_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except httpx.HTTPError as exc:
            log.error("paddle unreachable while looking up a buyer's address: %s", exc)
            return None
        if response.status_code >= 400:
            log.error(
                "paddle refused a customer lookup: %s %s",
                response.status_code, response.text[:200],
            )
            return None
        try:
            address = (response.json().get("data") or {}).get("email")
        except ValueError:
            return None
        return str(address) if address else None

    async def cancel_subscription(self, subscription_id: str) -> None:
        """Stop the next charge and let the paid period run out.

        `effective_from` is the whole decision. Cancelling immediately would
        end access the person has already paid for, which is a refund we did
        not agree to give, arriving as a surprise the moment they click the
        button. `next_billing_period` charges nothing more and keeps what is
        owed.

        Failures raise. A read can shrug and return `None` — this cannot: a
        cancel that quietly does nothing leaves somebody believing they have
        stopped paying, and they find out on a card statement.
        """
        if not self.configured:
            raise BillingUnavailable(
                "PADDLE_API_KEY is not set — cannot cancel a subscription"
            )
        try:
            response = await http.client().post(
                f"{self.base}/subscriptions/{subscription_id}/cancel",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"effective_from": "next_billing_period"},
            )
        except httpx.HTTPError as exc:
            raise BillingUnavailable(f"paddle unreachable: {exc}") from exc
        if response.status_code >= 400:
            raise BillingUnavailable(
                f"paddle refused to cancel {subscription_id}: "
                f"{response.status_code} {response.text[:300]}"
            )


class PaddleProvider:
    """Paddle as a `BillingProvider`.

    Thin on purpose. Everything it does is already in this module — it exists
    so that the router can hold *a* processor rather than *this* processor, and
    so that the day we are refused, the diff is a configuration value and a
    second file rather than an edit to every call site.
    """

    name = "paddle"
    granting = GRANTING
    revoking = REVOKING

    #: The legal seller. Paddle is a merchant of record rather than a gateway,
    #: so this — not us — is the company on the buyer's statement and in the
    #: refunds policy. **Unverified against a contract**, because no account
    #: exists yet; it is the entity Paddle's own terms name for EU/UK sales and
    #: it has to be confirmed against the signed agreement before launch.
    merchant = "Paddle.com Market Ltd"

    #: Paddle creates the customer inside its own overlay, so we never need an
    #: address before a checkout can exist. Dodo does, which is why this is a
    #: flag the offer screen can read rather than an assumption baked upstream.
    requires_email = False

    #: Paddle emails its own receipt, and it is **not** the confirmation the
    #: withdrawal waiver needs: it names the transaction, not the two sentences
    #: the buyer ticked, and it is configurable off in the dashboard. Ours is
    #: the one that carries the consent, so `_confirm_the_purchase` sends it.
    #: The stores are the other answer — there, Apple and Google are the seller
    #: and the confirmation is theirs.
    issues_the_receipt = False

    def __init__(self, client: PaddleClient | None = None) -> None:
        # Built lazily: constructing one reads settings and nothing else, but a
        # provider that is only being asked to parse an event should not have
        # to care whether an API key exists.
        self._client = client

    @property
    def client(self) -> PaddleClient:
        if self._client is None:
            self._client = PaddleClient()
        return self._client

    def verify(
        self, raw_body: bytes, headers: Mapping[str, str], *, secret: str | None = None
    ) -> None:
        verify(raw_body, header_value(headers, SIGNATURE_HEADER), secret=secret)

    def parse(
        self, payload: dict, headers: Mapping[str, str] | None = None
    ) -> NormalisedEvent:
        """The headers are accepted and unused: Paddle's `event_id` is in the body.

        The parameter exists because the *protocol* needs it — Standard Webhooks
        puts the per-delivery id in a header, and that id is the idempotency key.
        Taking an argument it ignores costs this adapter nothing and is what lets
        the router pass the headers unconditionally, rather than asking which
        processor is running before it can call `parse`.
        """
        return parse(payload).normalise()

    async def enrich(self, event: NormalisedEvent) -> NormalisedEvent:
        """Nothing to add: a Paddle delivery carries the whole event.

        A coroutine that never awaits, for the same reason `buyer_address` on
        the Dodo adapter is one — the protocol is shaped for the harder case,
        and Google's notification genuinely says almost nothing. An adapter that
        already knows everything answers immediately rather than making the
        router ask which processor is running before it can call this.
        """
        return event

    async def open_session(
        self,
        *,
        product: str,
        user_id: str,
        currency: str,
        country: str | None = None,
        email: str | None = None,
    ) -> SessionHandle:
        """Everything Paddle's overlay needs to open.

        No network call: Paddle's checkout is opened by the browser against a
        price id and a client token, which is why this returns a `price_id` and
        neither a URL nor a client secret. That is the weaker of the two shapes
        `SessionHandle` supports — a price the client names is a price the
        client can substitute — and it is the reason the webhook, not the
        overlay closing, is what grants anything.

        Substituting it is caught rather than prevented: `entitlement_for`
        refuses a grant whose amount does not cover the catalogue price, so a
        checkout sealed for the archive and charged at the door's price id
        records the money and grants nothing. Preventing it needs the shape Dodo
        already has, where the server creates the session and the browser never
        learns an identifier — and on Paddle that is not enough on its own
        either, because the client token is published and anyone can open an
        overlay against any of our price ids. See `open_problems`.

        `email` is accepted and deliberately not used. Paddle prefills it in
        the overlay client-side, and it must not travel in `custom_data`:
        `custom_data` is what comes back on the webhook, and a payment that
        finds its owner by email address finds whoever in a household shares
        one.

        `country` is accepted and unused here for the same reason: Paddle
        collects the billing address itself and computes its own tax from it,
        while Dodo has to be *told* a country when the session is created. The
        parameter is on the protocol because one adapter cannot open a session
        without it.

        `NotSold` propagates. In the five purchasing-power markets the doors
        genuinely do not exist, so that is an ordinary answer there and the
        caller has to render it rather than crash on it.
        """
        from . import catalogue as prices

        item = prices.product(product)
        config = settings()
        if not config.billing_enabled:
            # Named from the configuration rather than typed out here, so the
            # message stays right if a credential is ever added or renamed.
            raise BillingUnavailable(
                f"{', '.join(config.missing_billing_credentials())} are not set"
            )

        return SessionHandle(
            provider=self.name,
            product=product,
            currency=currency,
            cents=item.cents_in(currency),
            display=item.display(currency),
            # Sealed, because this is the one adapter where the blob travels
            # through the browser on its way to the processor — and the client
            # token that opens the overlay is public, so the browser can open a
            # checkout of its own with metadata we never wrote. `stamp` is what
            # makes the copy that comes back on the webhook readable as ours.
            custom_data=stamp(user_id, product),
            price_id=item.identifier(self.name),
            client_token=config.paddle_client_token,
            environment=config.paddle_environment,
        )

    async def cancel_subscription(self, subscription_id: str) -> None:
        await self.client.cancel_subscription(subscription_id)

    async def buyer_address(self, event: NormalisedEvent) -> str | None:
        """Where to send this buyer's receipt.

        Paddle is the adapter that has to ask. A `transaction.completed` payload
        carries `customer_id` and no address — the customer object is not
        included in notification bodies — so for the whole guest funnel the
        alternative to one API call is no confirmation on a durable medium at
        all, and therefore no completed waiver for any buyer who never signed in.

        The payload is still preferred where it happens to carry one: an account
        configured to include the customer, and the `billing_details` some event
        shapes carry, both mean the answer is already in hand and a round trip
        would be a request made for nothing.
        """
        if event.buyer_email:
            return event.buyer_email
        customer_id = (event.payload.get("data") or {}).get("customer_id")
        return await self.client.customer_email(str(customer_id or ""))
