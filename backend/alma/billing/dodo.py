"""Dodo Payments: the second implementation of the seam, and the reason it exists.

Paddle's acceptable-use policy names our category as **prohibited** rather than
restricted — "digital services associated with pseudo-science, including but
not limited to clairvoyance, horoscopes, fortune-telling" — and FastSpring and
2Checkout carry the same clause almost word for word. Dodo puts "Spiritual &
Astrology services" on a *requires-review* list instead, which is a
conversation rather than a refusal. Nobody has been approved anywhere yet, so
the point of this file is not that Dodo is the answer. It is that a second
adapter proves the first one was an adapter.

Three things here are load-bearing and the rest is translation.

**The signature.** Dodo follows the [Standard Webhooks](https://standardwebhooks.com)
specification, not Paddle's scheme: three headers, and a signed message of
`f"{webhook-id}.{webhook-timestamp}.{raw_body}"`, HMAC-SHA256, base64. Every
detail of the encoding is taken from the reference implementation Dodo's own
SDK delegates to (`standardwebhooks.Webhook.verify`) rather than from prose,
because a signature scheme that is *nearly* right fails identically to a wrong
secret and there is no way to tell the two apart from a log line.

**The replay window is ours, not theirs.** Dodo's documentation gives no
guidance on one, which is a reason to keep `check_freshness` rather than to
widen it to infinity: an unbounded window means a signature captured from a
proxy log is good forever.

**Idempotency needs almost nothing new.** `webhook-id` is a stable
per-delivery id and drops straight onto `webhook_event.id`. The one wrinkle is
that it is a *header*, and it is the only identifier Dodo sends — there is no
`event_id` in the body — so `parse` has to be given the headers to see it, and
`BillingProvider.parse` takes them for exactly that reason. There is
deliberately no fallback that derives an id from the body: see `parse` for the
two ways round that an invented id was wrong.

Everything else in this file is one job: turn Dodo's shapes into a
`NormalisedEvent`, so that nothing above the adapter ever learns that
`custom_data` is called `metadata` here, that a refund's fullness is a boolean
rather than a word, or that a country lives one level shallower.

No credentials appear here. `DODO_PAYMENTS_API_KEY` and
`DODO_PAYMENTS_WEBHOOK_KEY` come from the environment.
"""

from __future__ import annotations

import base64
import binascii
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

#: Re-exported so `dodo.MAX_SIGNATURE_AGE` and `dodo.Grant` mean exactly what
#: `paddle.MAX_SIGNATURE_AGE` and `paddle.Grant` mean — the same objects, from
#: `provider.py`, not lookalikes. Two `InvalidSignature` classes with the same
#: name would both look right and only one of them would be caught by the
#: router's `except`, which is the shape of a webhook endpoint that accepts
#: everything.
__all__ = [
    "GRANTING",
    "MAX_SIGNATURE_AGE",
    "MONEY_EVENTS",
    "PERIOD",
    "REVOKING",
    "DodoClient",
    "DodoProvider",
    "Event",
    "Grant",
    "InvalidSignature",
    "entitlement_for",
    "parse",
    "verify",
]

#: Dodo's two hosts, named the way their own SDK names them. A constant that
#: renames a vendor's term is a constant somebody has to translate every time
#: they read it against the documentation.
TEST_API = "https://test.dodopayments.com"
LIVE_API = "https://live.dodopayments.com"

#: The three Standard Webhooks headers. Paddle carries the whole signature in
#: one; neither number is inherent to signing a webhook, which is why the
#: protocol hands an adapter the entire mapping.
ID_HEADER = "webhook-id"
TIMESTAMP_HEADER = "webhook-timestamp"
SIGNATURE_HEADER = "webhook-signature"

#: The prefix a Standard Webhooks secret carries, and the version tag on each
#: signature inside the header.
_SECRET_PREFIX = "whsec_"
_SIGNATURE_VERSION = "v1"

#: The values of `DODO_PAYMENTS_ENVIRONMENT` that mean real cards. Anything
#: else — including a typo, an empty string and Dodo's own "test_mode" — is the
#: test environment, because a typo must not be the thing that decides money is
#: real, while the opposite mistake costs one failed test purchase.
#:
#: One predicate, read by both the host and the word handed to the client, so
#: the API we call and the SDK the browser initialises cannot end up disagreeing
#: about which world they are in.
_LIVE_WORDS: frozenset[str] = frozenset({"live", "live_mode", "production"})


def is_live(environment: str | None) -> bool:
    return (environment or "").strip().lower() in _LIVE_WORDS


def _signing_key(secret: str) -> bytes:
    """The raw HMAC key behind a `whsec_…` secret.

    A Standard Webhooks secret is **base64 of the key**, not the key. The
    reference implementation strips the `whsec_` prefix, appends `==` so an
    unpadded value still decodes, and base64-decodes the rest; Dodo's SDK calls
    that implementation, so the sender is signing with those bytes and anything
    else here produces a digest that never matches. That failure is
    indistinguishable from a wrong secret in the logs, which is why it is
    spelled out rather than left to be inferred from "HMAC SHA256".

    A secret that is not base64 at all keeps its own bytes rather than being
    rejected. It is not this function's business to decide that a dashboard has
    changed format, and refusing here would take down a webhook endpoint that
    might verify perfectly well.

    `validate=True` is what makes that last paragraph true, and it was missing.
    `b64decode` defaults to `validate=False`, which **silently discards** every
    character outside the base64 alphabet instead of raising — so the fallback
    was unreachable and a secret containing such a character was reduced to its
    base64-alphabet subset. `whsec_hello world!!` and `whsec_helloworld` both
    produced the same seven-byte key. It failed safe, in that a mangled key
    yields a mismatch and never a wrong grant, but the incident it produced read
    as "signature does not match" — an attacker or a rotation — rather than as a
    secret pasted in the wrong format.

    The padding is rebuilt rather than appended, which the reference
    implementation gets away with only because it does not validate: a secret
    that already carries its `=` padding, plus a blind `"=="`, is four padding
    characters and not valid base64 at all. Under validation that is the *common*
    secret failing, not the malformed one — so the tail is stripped and the right
    number of characters put back.
    """
    body = secret[len(_SECRET_PREFIX):] if secret.startswith(_SECRET_PREFIX) else secret
    body = body.rstrip("=")
    try:
        return base64.b64decode(body + "=" * (-len(body) % 4), validate=True)
    except (binascii.Error, ValueError):
        return secret.encode()


def verify(
    raw_body: bytes, headers: Mapping[str, str], *, secret: str | None = None
) -> None:
    """Verify a Standard Webhooks signature, or raise.

    The signed message is `f"{webhook-id}.{webhook-timestamp}.{raw_body}"`, and
    the body goes in exactly as received — re-serialising the JSON changes
    bytes and therefore changes the digest, usually by one space after a colon.

    Signing the **id** as well as the body is what stops a captured delivery
    being replayed under a fresh id: `webhook-id` is the idempotency key, so if
    it were not covered, one valid body could be granted over and over by
    changing the header the insert-before-process check reads.
    """
    key = secret if secret is not None else settings().dodo_webhook_secret
    if not key:
        raise InvalidSignature(
            "DODO_PAYMENTS_WEBHOOK_KEY is not set — refusing to accept an "
            "unverified webhook that grants paid access"
        )

    event_id = header_value(headers, ID_HEADER)
    stamp = header_value(headers, TIMESTAMP_HEADER)
    provided = header_value(headers, SIGNATURE_HEADER)
    if not (event_id and stamp and provided):
        raise InvalidSignature("missing one of the three Standard Webhooks headers")

    check_freshness(stamp)

    # The timestamp goes into the message exactly as it arrived. The reference
    # implementation round-trips it through a datetime and floors it, which is
    # the same string for the integer seconds Dodo documents — but only the
    # sender knows what it actually signed, and what it sent is what it signed.
    message = f"{event_id}.{stamp}.".encode() + raw_body
    expected = hmac.new(_signing_key(key), message, hashlib.sha256).digest()

    # The header may carry several space-separated `v1,<base64>` signatures.
    # That is not decoration: it is how a secret is rotated, with both the old
    # and the new signature on every delivery for the length of the window.
    # Reading only the first would break every webhook for that whole period,
    # and the failure would arrive as "signature does not match" — which reads
    # as an attack rather than as a rotation somebody started this morning.
    for versioned in provided.split(" "):
        version, _, encoded = versioned.partition(",")
        if version != _SIGNATURE_VERSION or not encoded:
            continue
        try:
            candidate = base64.b64decode(encoded)
        except (binascii.Error, ValueError):
            continue
        # Constant time. Called here rather than through a shared helper on
        # purpose — `hmac.compare_digest` has to be visible at the call site,
        # and a test reads this function's source to make sure it still is,
        # because a `==` here passes every functional test ever written for it
        # and only ever shows up as an attacker who measured the difference.
        if hmac.compare_digest(expected, candidate):
            return

    raise InvalidSignature("signature does not match")


@dataclass(frozen=True, slots=True)
class Event:
    """A Dodo webhook, read lazily off the payload it arrived in.

    The envelope is `{business_id, type, timestamp, data}` and everything
    interesting is in `data`, discriminated by `data.payload_type` — `Payment`,
    `Subscription`, `Refund`, `Dispute`, and a dozen families we do not act on.

    The property names are deliberately the same as the Paddle adapter's, even
    where Dodo nests the value somewhere else entirely, so that the two files
    can be read side by side and the differences are only ever in the bodies.
    """

    id: str
    type: str
    payload: dict

    @property
    def data(self) -> dict:
        return self.payload.get("data", {})

    @property
    def transaction_id(self) -> str | None:
        """The payment this event is *about*.

        Flat on every shape, because Dodo names its identifiers apart: a
        payment carries `payment_id`, and so does the refund or dispute that
        reduces it, while their own ids are `refund_id` and `dispute_id`.
        Paddle overloads `data.id` for both, and the fallback order there is
        load-bearing and was once reversed — which attached every refund to a
        transaction that did not exist. There is no equivalent trap here, and
        this property must never grow one.
        """
        value = self.data.get("payment_id")
        return str(value) if value else None

    @property
    def adjustment_id(self) -> str | None:
        """The refund's or dispute's own id, on the events that have one."""
        value = self.data.get("refund_id") or self.data.get("dispute_id")
        return str(value) if value else None

    @property
    def adjustment(self) -> tuple[str, str] | None:
        """(action, type) for something that reduces a charge — e.g. ("refund", "full").

        The vocabulary is the protocol's, not Dodo's: `refund` and `chargeback`
        are the two actions that return money, and `full` against `partial`
        decides whether what the charge bought stops being readable.

        Dodo hands the full/partial distinction over directly as
        `Refund.is_partial`, which is better than inferring it by comparing
        amounts — a whole refund issued in two halves is two partials, and
        arithmetic would call the second one full and close the grant.

        A dispute is a chargeback we did not choose, and only its two terminal
        outcomes are one: `dispute.lost` (defended and lost) and
        `dispute.accepted` (conceded). `dispute.opened` and `dispute.challenged`
        are money *held*, not money gone; mapping them here would close a grant
        that may yet be won back, and would add the disputed amount to the
        refund column a second time when the outcome finally lands.
        **Unverified:** Dodo's reference does not say whether an accepted
        dispute can also emit `lost`. If it can, the refund column is charged
        twice for one dispute.
        """
        if self.type == "refund.succeeded":
            return ("refund", "partial" if self.data.get("is_partial") else "full")
        if self.type in TERMINAL_DISPUTE_EVENTS:
            return ("chargeback", "full")
        return None

    @property
    def subscription_id(self) -> str | None:
        """The subscription this event belongs to, on every shape that has one.

        Flat again: a Dodo subscription event carries `subscription_id` in its
        own right, and a renewal payment carries the same field alongside its
        `payment_id`. Paddle needs a three-way fallback here because a
        `subscription.*` event hides the id in `data.id`; the metadata fallback
        below survives only for an event we ourselves tagged.
        """
        value = self.data.get("subscription_id") or self.custom.get("subscription_id")
        return str(value) if value else None

    @property
    def status(self) -> str | None:
        """The processor's own word for the state — recorded, never consulted.

        A provider swap is precisely the day every one of these strings changes
        at once: Paddle writes "canceled", Dodo writes "cancelled". If the
        paywall read them, that day would be the day everybody who has paid is
        locked out. Access is decided by the expiry and the revocation, which
        we set ourselves.
        """
        value = self.data.get("status") or self.data.get("dispute_status")
        return str(value) if value else None

    @property
    def renews_at(self) -> datetime | None:
        """When the plan bills again, as Dodo stated it.

        Not an expiry. Between a cancellation and the end of a paid period the
        two disagree, and that gap is the entire difference between cancelling
        and refunding.
        """
        return moment(self.data.get("next_billing_date"))

    @property
    def custom(self) -> dict:
        """Our own tag on the purchase.

        The one rename that matters: Paddle calls this `custom_data`, Dodo
        calls it `metadata`. It is set when the checkout session is created, so
        it comes back on the payment and — because Dodo copies it onto the
        subscription — on every renewal for the life of the plan.
        """
        return self.data.get("metadata") or {}

    @property
    def user_id(self) -> str | None:
        """Who Dodo says this payment belongs to. **Not yet trustworthy.**

        The raw field, kept raw so support reading a delivery sees what arrived;
        `normalise()` reads the sealed pair instead. Dodo seals its metadata
        into a server-created session, so on this processor the blob genuinely
        never passes through a browser — but the check is the seam's and not one
        processor's, and an adapter that skipped it because *its* shape is safe
        would be one refusal away from being the adapter that does not check.

        Coerced to `str` because Dodo types a metadata value as string, number
        *or* boolean: a value that leaves as `"7"` can come back as `7.0`, and
        `session.get(User, 7.0)` finds nobody and raises nothing.
        """
        value = self.custom.get("user_id")
        return str(value) if value not in (None, "") else None

    @property
    def product_slug(self) -> str | None:
        """What Dodo says was bought. **Not yet trustworthy** — see `user_id`."""
        value = self.custom.get("product")
        return str(value) if value not in (None, "") else None

    @property
    def country(self) -> str | None:
        """Where the buyer is, for the money trail and the tax.

        `data.billing.country` — one level shallower than Paddle's
        `billing_details.address.country_code`, and an ISO-3166 alpha-2 code
        either way, so `catalogue.currency_for` reads it unchanged.
        """
        value = (self.data.get("billing") or {}).get("country")
        return str(value) if value else None

    @property
    def buyer_email(self) -> str | None:
        """The address Dodo collected from the buyer, on every payment.

        Dodo puts the customer object in the body, which is the difference
        between this adapter and Paddle's — there, the same question costs an
        API call. What it is for is the receipt: a guest may buy, a guest has no
        address of ours, and the confirmation on a durable medium is the third
        leg of the withdrawal waiver rather than a courtesy.

        Read and handed upward, **never written to `User.email`**. That column
        is the sign-in identity and `accounts.by_email` merges a guest into
        whoever holds it, so an unverified address arriving from a checkout
        would be an account-takeover primitive.
        """
        value = (self.data.get("customer") or {}).get("email")
        return str(value) if value else None

    def amount_cents(self) -> int:
        """What actually moved, in the currency's minor units.

        `total_amount` on a payment — tax included, which is what every other
        amount in our money trail means — and `amount` on a refund or a dispute.

        Two fields are excluded on purpose. `settlement_amount` is what reaches
        our Dodo balance after conversion rather than what the buyer was
        charged, so recording it would silently restate every foreign sale by
        the spread. `recurring_pre_tax_amount` on a subscription event is
        pre-tax by name, and mixing it into a column that otherwise holds
        tax-inclusive totals would corrupt the credit calculation that reads
        those amounts against each other — it is not needed anyway, because the
        money for a subscription arrives on its own `payment.succeeded`. A
        subscription event therefore reports zero here, exactly as Paddle's
        `subscription.activated` does.
        """
        data = self.data
        raw = data.get("total_amount")
        if raw is None:
            raw = data.get("amount")
        if raw is None:
            return 0
        try:
            return int(raw)
        except (TypeError, ValueError):
            # A dispute types its amount as a *string* while every other amount
            # in the API is an integer of minor units. Parsing through float
            # covers a decimal-shaped one without letting a word through.
            try:
                return int(float(raw))
            except (TypeError, ValueError):
                return 0

    def currency(self) -> str:
        """The ISO-4217 code. Dodo calls the field `currency`; Paddle,
        `currency_code`."""
        value = self.data.get("currency")
        return str(value) if value else "USD"

    def normalise(self) -> NormalisedEvent:
        """This event in provider-neutral words.

        The three booleans are answered here, using Dodo's own event strings,
        so nothing upstream ever holds another company's vocabulary.

        `grants` carries the one rule that is Dodo's alone and costs money if
        it is missed — see `_grants`. `moves_money` is deliberately narrower
        than a family prefix: a dispute that has merely been *opened* is in the
        `dispute.` family and has moved nothing, and recording it as money
        would mark a purchase refunded while we are still arguing about it.

        The owner and product come from `sealed_owner` for the reason spelled
        out on `Event.user_id`: the rule that a grant is read only out of
        metadata we ourselves signed belongs to the seam, so both adapters obey
        it and neither has to be the one that remembers to.
        """
        owner, product = sealed_owner(self.custom)
        return NormalisedEvent(
            provider=DodoProvider.name,
            id=self.id,
            type=self.type,
            kind=_kind_of(self.type),
            owner_id=owner,
            product=product or _key_from_product_id(self),
            subscription_id=self.subscription_id,
            transaction_id=self.transaction_id,
            amount_cents=self.amount_cents(),
            currency=self.currency(),
            country=self.country,
            buyer_email=self.buyer_email,
            status=self.status,
            renews_at=self.renews_at,
            adjustment=self.adjustment,
            grants=self._grants,
            revokes=self.type in REVOKING,
            moves_money=self._moves_money,
            payload=self.payload,
        )

    @property
    def _grants(self) -> bool:
        if self.type not in GRANTING:
            return False
        if self.type == "payment.succeeded" and self.subscription_id:
            # The one place Dodo differs from Paddle in a way that costs money.
            # A renewal here emits **both** `payment.succeeded` and
            # `subscription.renewed`; Paddle emits only the transaction. Since
            # `entitlements.grant` keys on the subscription id and extends the
            # row by a whole period each time it is called, letting both
            # through would grant two months for one month's money — every
            # month, silently, with the expiry drifting further and further
            # ahead of the payments. So the subscription lifecycle events are
            # the single source of a recurring grant, and the payment event is
            # left to do the one thing only it can: record the money.
            return False
        return True

    @property
    def _moves_money(self) -> bool:
        if not self.transaction_id or not self.type.startswith(MONEY_EVENTS):
            return False
        # An open or challenged dispute names a payment but has not moved a
        # cent. `_record_money` would take it down the not-an-adjustment path
        # and, on an ADJUSTMENT kind, write the whole amount into
        # `refunded_cents` — marking a purchase refunded while the outcome is
        # still weeks away, and doing it a second time when the outcome lands.
        return not (
            self.type.startswith("dispute.") and self.type not in TERMINAL_DISPUTE_EVENTS
        )


def parse(payload: dict, headers: Mapping[str, str] | None = None) -> Event:
    """Read one delivery into an `Event`.

    The headers are not optional in any real sense: **Dodo puts no identifier in
    the body at all**, so `webhook-id` is the only per-delivery id there is, and
    it is the idempotency key the whole insert-before-process check turns on.
    They are typed optional only because the protocol says so, for Paddle's sake.

    There used to be a fallback here that hashed the event's *identity* — type,
    emission timestamp, resource id — when the headers were missing, and it was
    deleted rather than kept as a safety net. Dodo documents that a retry
    carries "the latest payload at the time of delivery", so a timestamp
    refreshed between attempts made a retry look like a new event: the same
    renewal granted a second period, silently. The mirror failure was a
    collision — two distinct refunds of one payment inside the same second share
    all three fields, and the second was answered "already processed" and never
    happened, so the money went back and the grant stayed. An id we invented was
    not second best, it was wrong in both directions. Without it a caller that
    forgets the headers produces an event with no id, the router answers 400,
    and somebody finds out.
    """
    return Event(
        id=header_value(headers or {}, ID_HEADER),
        type=str(payload.get("type") or ""),
        payload=payload,
    )


# ── which events change what a person can read ─────────────────────────────
#
# Everything not named below is recorded and ignored. An unknown event type is
# not an error, it is Dodo shipping a feature we have not adopted — and there
# are forty-odd of them, across payouts, licence keys, credits and entitlement
# grants we do not use.

#: Access begins, or is extended by another period.
#:
#: `subscription.renewed` belongs here rather than in some reconciliation pass
#: because `entitlements.grant` extends an existing subscription row in place,
#: from whichever is later — the current expiry or now. A renewal *is* a grant
#: as far as this layer is concerned.
GRANTING = frozenset({
    "payment.succeeded",
    "subscription.active",
    "subscription.renewed",
})

#: ...and which end access.
#:
#: Read this against the three that are deliberately **not** here — see
#: `IGNORED_REASONS`. It is also worth reading against Paddle's `REVOKING`,
#: which ends access on a cancellation and on a dunning retry: those are the
#: same two traps, sprung, and they are preserved there because changing them
#: changes what the product does to people who have paid.
REVOKING = frozenset({
    "subscription.expired",
    "refund.succeeded",
    "dispute.lost",
    "dispute.accepted",
})

#: The dispute outcomes in which the money is actually gone. Separate from
#: `REVOKING` because `Event.adjustment` and `Event._moves_money` both need the
#: same list, and a second literal set of strings is a second thing to forget.
TERMINAL_DISPUTE_EVENTS = frozenset({"dispute.lost", "dispute.accepted"})

#: The event families that can move money. Paddle spells them `transaction.`
#: and `adjustment.`; Dodo splits refunds and disputes into families of their
#: own. Neither spelling belongs anywhere but in an adapter.
MONEY_EVENTS: tuple[str, ...] = ("payment.", "refund.", "dispute.")

#: Why each event we deliberately do nothing with is doing nothing.
#:
#: Not read by any code path, and that is the point: three of these look
#: exactly like a revocation, and the next person to add a line to `REVOKING`
#: should have to read past the reason it was left out. A test asserts that
#: every event in Dodo's documented table appears in one of these three sets,
#: so an event cannot be merely unmentioned.
IGNORED_REASONS: dict[str, str] = {
    "subscription.on_hold": (
        "Dunning, not cancellation. Dodo's own words are 'put on hold due to "
        "failed renewal', and Dodo goes on retrying the card. Revoking here "
        "takes the product away from somebody whose payment is about to "
        "succeed — and the person whose card bounced is the person least able "
        "to argue about it. The grant already carries an expiry; if the "
        "retries fail, `subscription.expired` arrives and that is the honest "
        "moment."
    ),
    "subscription.cancelled": (
        "Cancelling is not refunding. Somebody who cancels on the 3rd has paid "
        "through the end of the period and is owed every day of it; taking the "
        "product away at the moment they press the button is charging for a "
        "month and delivering three days, and it is the click most likely to "
        "be followed by a chargeback. Letting `expires_at` run out is the "
        "whole mechanism, and `subscription.expired` closes it."
    ),
    "subscription.failed": (
        "Nothing was ever granted, so there is nothing to revoke. Dodo's words "
        "are 'creation failed during mandate creation' — the subscription did "
        "not start. Putting this in REVOKING would run the revocation against "
        "a subscription id that matches no row, which is harmless today and "
        "becomes a real revocation the day somebody retries a failed mandate "
        "on an id we have since granted against."
    ),
    "subscription.paused": (
        "A pause stops billing; it does not send money back. The grant already "
        "has an expiry, so letting it lapse neither punishes somebody who "
        "paused inside a period they had paid for nor keeps paying out after "
        "it. **Unverified:** this event is named in Dodo's webhook guide but "
        "absent from the event union in their own SDK, so it may not exist."
    ),
    "subscription.updated": (
        "A reconciliation, not a decision: it fires on any field change and "
        "carries `status`, `next_billing_date` and `metadata`. There is "
        "nowhere to put that yet — the webhook handler has no reconcile path — "
        "and inventing one here that nothing calls would read as a promise "
        "that these fields are kept fresh."
    ),
    "subscription.plan_changed": (
        "A plan change should re-scope the row and must not extend it, and "
        "`entitlements.grant` cannot do the first without the second: given a "
        "duration it always adds a whole period. Granting here would hand a "
        "free month to anybody who switched plans mid-period. Leaving it out "
        "costs the opposite and smaller thing — an upgrade keeps the old scope "
        "until the next renewal, at most one period, bounded by an expiry that "
        "already exists. **Unverified:** whether Dodo charges and resets the "
        "cycle on a plan change is not stated in the reference, and the answer "
        "decides which of those two is right."
    ),
    "subscription.update_payment_method": (
        "A new card against the same plan. Nothing about access changed."
    ),
    "payment.failed": (
        "No money arrived, so nothing is granted — and nothing is revoked "
        "either, because a failed charge against a live subscription is "
        "dunning. See `subscription.on_hold`."
    ),
}


#: Dodo's event strings, in the protocol's taxonomy. Listed exactly rather than
#: matched by family, because `payment.succeeded` and `payment.failed` are the
#: same family and opposite outcomes.
#:
#: One mapping is an approximation and is marked as such. `subscription.failed`
#: is a mandate that never authorised — nothing was collected and no plan
#: exists — and the taxonomy has no "never started", so `PAYMENT_FAILED` is the
#: nearest true statement about it.
#:
#: The non-terminal disputes used to be an approximation too, mapped to
#: `UNKNOWN` because the taxonomy had no word for an argument in progress. It
#: has one now: `DISPUTE` says outright that money is *held* rather than gone,
#: which is the distinction that keeps a purchase from reading as refunded while
#: we are still arguing about it. Only the two terminal outcomes are adjustments.
_KINDS: dict[str, EventKind] = {
    "payment.succeeded": EventKind.PAYMENT,
    "payment.failed": EventKind.PAYMENT_FAILED,
    "refund.succeeded": EventKind.ADJUSTMENT,
    "dispute.opened": EventKind.DISPUTE,
    "dispute.challenged": EventKind.DISPUTE,
    "dispute.expired": EventKind.DISPUTE,
    "dispute.won": EventKind.DISPUTE,
    "dispute.lost": EventKind.ADJUSTMENT,
    "dispute.accepted": EventKind.ADJUSTMENT,
    "subscription.active": EventKind.SUBSCRIPTION_STARTED,
    "subscription.renewed": EventKind.SUBSCRIPTION_RENEWED,
    "subscription.updated": EventKind.SUBSCRIPTION_UPDATED,
    "subscription.plan_changed": EventKind.SUBSCRIPTION_UPDATED,
    "subscription.update_payment_method": EventKind.SUBSCRIPTION_UPDATED,
    "subscription.on_hold": EventKind.SUBSCRIPTION_DUNNING,
    "subscription.paused": EventKind.SUBSCRIPTION_PAUSED,
    "subscription.cancelled": EventKind.SUBSCRIPTION_CANCELLED,
    "subscription.expired": EventKind.SUBSCRIPTION_ENDED,
    "subscription.failed": EventKind.PAYMENT_FAILED,
}


def _kind_of(event_type: str) -> EventKind:
    return _KINDS.get(event_type, EventKind.UNKNOWN)


def entitlement_for(event: Event) -> Grant | None:
    """What this Dodo event should grant, if anything.

    A translation and a delegation: the rule itself — that a recurring plan is
    recognised by the catalogue having given the product an interval — is ours
    and lives in `provider.py`, where the Paddle adapter reaches the same
    answer through the same function rather than through a second copy of it.
    A second copy is how two adapters start disagreeing about what a monthly is.
    """
    return _entitlement_for(event.normalise())


def _key_from_product_id(event: Event) -> str | None:
    """The catalogue key behind a checkout we did not open.

    A payment names its products in `data.product_cart[]`; a subscription names
    its one product in `data.product_id`. Either way the catalogue is asked
    which key carries that identifier, so nothing here infers a key from a kind
    — inferring is what once turned a monthly price id into a year.

    Narrowed to this processor's identifiers, because two processors could
    issue the same string and matching the other one's would grant against a
    product this payment did not buy.

    Every identifier in the catalogue is still the empty string — nothing has
    been sold through this code and no processor account exists — so this
    answers `None` today. That is not silent: a purchase opened through our own
    checkout carries the sealed product in its metadata and never reaches this
    function, and one that does reach it is recorded with no grant, which
    support can see and fix by hand.
    """
    from .catalogue import by_price_id

    data = event.data
    identifiers = [line.get("product_id") for line in (data.get("product_cart") or [])]
    identifiers.append(data.get("product_id"))
    for identifier in identifiers:
        found = by_price_id(str(identifier or ""), DodoProvider.name)
        if found is not None:
            return found
    return None


class DodoClient:
    """The small part of the Dodo API we actually call."""

    def __init__(self, api_key: str | None = None, environment: str | None = None) -> None:
        config = settings()
        self.api_key = api_key if api_key is not None else config.dodo_api_key
        chosen = environment if environment is not None else config.dodo_environment
        self.base = LIVE_API if is_live(chosen) else TEST_API

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        """One API call, raising `BillingUnavailable` on anything but success.

        Raising rather than returning `None`. Every call in this class either
        creates a checkout or stops a recurring charge, and both are things a
        person is waiting on the answer to — a failure that returns quietly
        leaves them believing a session opened, or that they have stopped
        paying, and they find out otherwise on a card statement.
        """
        if not self.configured:
            raise BillingUnavailable(
                "DODO_PAYMENTS_API_KEY is not set — cannot talk to Dodo"
            )
        try:
            # Общий клиент процесса, а не свой на вызов: см. `billing/http.py`.
            # Здесь это заметнее всего — отмена подписки и открытие кассы идут
            # к одному хосту, и второй запрос больше не платит за рукопожатие.
            response = await http.client().request(
                method,
                f"{self.base}{path}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
            )
        except httpx.HTTPError as exc:
            raise BillingUnavailable(f"dodo unreachable: {exc}") from exc
        if response.status_code >= 400:
            raise BillingUnavailable(
                f"dodo refused {method} {path}: "
                f"{response.status_code} {response.text[:300]}"
            )
        return response.json() if response.content else {}

    async def create_checkout_session(
        self,
        *,
        product_id: str,
        metadata: dict,
        email: str | None = None,
        customer_id: str | None = None,
        country: str | None = None,
        currency: str | None = None,
        return_url: str | None = None,
    ) -> dict:
        """`POST /checkouts` — the current endpoint, not the deprecated one.

        Dodo's own reference marks `POST /payments` deprecated in favour of
        checkout sessions, and the difference is not cosmetic: **the server
        creates the session and the browser is handed a URL**, never a price
        identifier. A price the client names is a price the client can
        substitute.

        `confirm` is deliberately not passed. It finalises every detail
        server-side and errors on anything missing, which turns a buyer's
        missing postcode into a 500 on our side rather than a field on theirs.
        The consequence is that `client_secret`, `payment_id` and
        `publishable_key` come back empty and `checkout_url` is the one that is
        filled — which is the shape we want anyway.
        """
        body: dict = {
            "product_cart": [{"product_id": product_id, "quantity": 1}],
            "metadata": metadata,
        }
        if customer_id:
            body["customer"] = {"customer_id": customer_id}
        elif email:
            body["customer"] = {"email": email}
        if country:
            body["billing_address"] = {"country": country}
        if currency:
            # Ignored by Dodo unless adaptive pricing is on, and sent anyway:
            # the catalogue has already decided which currency this person is
            # priced in, and letting the processor pick a different one is
            # exactly how a shown price and a charged price come apart.
            body["billing_currency"] = currency
        if return_url:
            body["return_url"] = return_url
        return await self._call("POST", "/checkouts", body)

    async def payment(self, payment_id: str) -> dict | None:
        """Fetch a payment, for reconciling a webhook we are unsure about.

        The one read, and the one call allowed to shrug: nobody is waiting on
        it and a reconciliation that fails can be run again.
        """
        try:
            return await self._call("GET", f"/payments/{payment_id}")
        except BillingUnavailable as exc:
            log.error("could not reconcile %s: %s", payment_id, exc)
            return None

    async def cancel_subscription(self, subscription_id: str) -> None:
        """Stop the next charge and let the paid period run out.

        `PATCH /subscriptions/{id}` with `cancel_at_next_billing_date`, not
        with `status: "cancelled"`. That is the whole decision: the second ends
        the subscription there and then and sets `cancelled_at`, which takes
        away access the person has already paid for — a refund we never agreed
        to give, arriving as a punishment for leaving.
        """
        await self._call(
            "PATCH",
            f"/subscriptions/{subscription_id}",
            {"cancel_at_next_billing_date": True},
        )


class DodoProvider:
    """Dodo as a `BillingProvider`.

    Thin, like the Paddle one: everything it does is already in this module. It
    exists so the router can hold *a* processor rather than *this* processor.
    """

    name = "dodo"
    granting = GRANTING
    revoking = REVOKING

    #: The legal seller, for the statement and for the refunds page. Dodo is a
    #: merchant of record like Paddle. **Unverified against a contract** — this
    #: is their trading name and not necessarily the registered entity that will
    #: appear on a card statement, which is a line to confirm during onboarding
    #: rather than to guess at. Naming the wrong seller on a refunds page is not
    #: cosmetic: that page is what a card issuer reads during a dispute.
    merchant = "Dodo Payments"

    #: **False, and the brief and `provider.py` both say otherwise.** Dodo's
    #: checkout-session schema makes `customer` optional, and email is required
    #: only *inside* it, to create a new customer inline — "Email is required
    #: for creating a new customer". Omit `customer` and Dodo's hosted page
    #: collects the address itself, and our `metadata` still carries the user
    #: id, so the webhook still finds its owner. Claiming otherwise would put a
    #: form field between somebody who has decided to pay and the act of
    #: paying, which is the most expensive wall in any funnel and the reason
    #: this product already lets a guest buy. An email we are given is still
    #: used — see `open_session`.
    requires_email = False

    #: Dodo sends its own receipt and it is not the one the waiver needs — see
    #: the same field on `PaddleProvider`. Ours quotes the sentences the buyer
    #: actually ticked; a processor's cannot, because it never saw them.
    issues_the_receipt = False

    def __init__(self, client: DodoClient | None = None) -> None:
        # Built lazily: a provider that is only being asked to parse an event
        # should not have to care whether an API key exists.
        self._client = client

    @property
    def client(self) -> DodoClient:
        if self._client is None:
            self._client = DodoClient()
        return self._client

    def verify(
        self, raw_body: bytes, headers: Mapping[str, str], *, secret: str | None = None
    ) -> None:
        verify(raw_body, headers, secret=secret)

    def parse(
        self, payload: dict, headers: Mapping[str, str] | None = None
    ) -> NormalisedEvent:
        """The protocol's `parse`, and the headers are not decoration here.

        `webhook-id` is the only per-delivery id Dodo sends and it is the
        idempotency key. Called without the headers this produces an event with
        no id and the router answers 400 — loudly, rather than filing the
        delivery under something invented. See `parse`.
        """
        return parse(payload, headers).normalise()

    async def enrich(self, event: NormalisedEvent) -> NormalisedEvent:
        """Nothing to add: a Dodo delivery carries the whole event.

        See `PaddleProvider.enrich`. The processor that needs this is Google,
        whose notification is a package name, an integer and a token.
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
        """Create one checkout session and hand back a URL.

        The order is the point. The catalogue is asked for the price *first*,
        so `NotSold` is raised before any network call — in the five
        purchasing-power markets the doors genuinely do not exist, and that is
        an ordinary answer there rather than a failure worth a round trip.

        What the client receives has no price in it that it could change: a
        URL, and the amount only so the interface can show what it already
        showed. Whether the money moved is still decided by the signed webhook
        and nothing else.
        """
        from . import catalogue as prices

        item = prices.product(product)
        cents, display = item.cents_in(currency), item.display(currency)

        # Refused loudly rather than guessed at: a session opened against the
        # wrong product id charges the right money for the wrong thing, and the
        # webhook that comes back grants the wrong thing too. Every identifier
        # in the catalogue is empty until somebody fills them in from a Dodo
        # dashboard, which is the one step no code here can do.
        product_id = item.identifier(self.name)
        if not product_id:
            raise BillingUnavailable(
                f"the catalogue has no Dodo product id for {product!r} — "
                f"`PRODUCTS[{product!r}].processor_ids['dodo']` is unset, "
                "so there is nothing to sell"
            )

        created = await self.client.create_checkout_session(
            product_id=product_id,
            # Echoed back on every webhook this purchase ever produces. Note
            # what is *not* here: the email address. `metadata` is how a
            # payment finds its owner, and an owner found by email is whoever
            # in a household shares one.
            #
            # Sealed by the seam rather than written out here. On this processor
            # the blob is sent server-to-server and never touches a browser, so
            # the seal proves nothing Dodo's own transport does not — but the
            # rule that a grant is only read out of metadata we signed belongs
            # to the seam, and an adapter that opted out because its shape is
            # safe is the adapter that stops being safe quietly.
            metadata=stamp(user_id, product),
            email=email,
            country=country,
            currency=currency,
            # The site root, and deliberately not a path invented here. Dodo
            # sends the buyer to this URL on success *and* on failure, and the
            # interface has no route for either yet — a 404 in the second after
            # somebody's card was charged is the worst page in the product.
            # Sending them back to the reading they bought is the right answer
            # and needs a page that exists; see `open_problems`.
            return_url=settings().web_url,
        )

        return SessionHandle(
            provider=self.name,
            product=product,
            currency=currency,
            cents=cents,
            display=display,
            # No `custom_data`, and that is the point of this shape rather than
            # an omission: the metadata is sealed into a session the server
            # created, so the browser has no reason to hold a copy and does not
            # get one. `SessionHandle.to_client` drops the field entirely, which
            # is what makes the comments in `src/lib/checkout.ts` true — they
            # said the browser never sees it while a copy was being sent.
            #
            # `environment` is translated here, where the rest of Dodo's
            # vocabulary dies. The configuration holds Dodo's own words —
            # "test_mode" / "live_mode" — because those are what their dashboard
            # prints; the client contract is "production" or anything else, and
            # `src/lib/checkout.ts` computes `live = environment === "production"`.
            # Handing the browser "live_mode" therefore initialised the *test*
            # SDK against a live checkout session, and the failure would have
            # landed on the first real customer of the new processor. Read
            # through the same predicate `DodoClient` uses to pick the host, so
            # the API we called and the SDK the browser starts cannot disagree.
            environment="production" if is_live(settings().dodo_environment) else "sandbox",
            url=created.get("checkout_url"),
            client_secret=created.get("client_secret"),
            reference=created.get("session_id"),
        )

    async def cancel_subscription(self, subscription_id: str) -> None:
        await self.client.cancel_subscription(subscription_id)

    async def buyer_address(self, event: NormalisedEvent) -> str | None:
        """Where to send this buyer's receipt.

        A coroutine that never awaits anything, because Dodo already told us:
        the customer object is in the body of every payment. The protocol is
        shaped for the harder case — Paddle has to be asked over the network —
        and an adapter that already knows the answer simply gives it.
        """
        return event.buyer_email
