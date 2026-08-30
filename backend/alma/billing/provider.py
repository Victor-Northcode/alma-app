"""The seam where a payment processor plugs in, and the words both sides speak.

We have not been approved by anybody yet. Paddle's acceptable-use policy names
our category — horoscopes, fortune-telling — as *prohibited* rather than
restricted, and FastSpring and 2Checkout carry the same clause almost word for
word because they share an upstream template. Dodo puts us on a
requires-review list; Stripe has had no global ban since 2021. So the processor
is not a decision that has been made, it is a decision that will be made *for*
us, possibly twice, and the only sane response is to make being refused by one
of them an afternoon rather than a rewrite.

That is what this file is for. It holds the vocabulary the entitlement layer
understands, and an adapter translates one processor's shape into it. Nothing
above the adapter may know which processor is in use.

**What is inherent to card billing** — every processor does these, so they
belong here:

* A **signed webhook is the only trustworthy statement that money moved.** The
  browser noticing a checkout closed is a claim by the client, and anything the
  browser can decide, the browser can be made to decide.
* That signature needs a **replay window** and a **constant-time comparison**.
  A valid signature from last week is still a replay; a comparison that returns
  early leaks the digest a byte at a time.
* Delivery is **at least once**, with a stable per-delivery id, so idempotency
  is our problem and it has to be a database constraint. Where that id lives
  differs — Paddle puts it in the body, Dodo in a header — so `parse` is handed
  the headers as well.
* A signature proves the processor **relayed** a field faithfully; it does not
  prove the field is ours. Every processor lets us attach a blob to a checkout
  and echoes it back, and on at least one of them that blob goes out through
  the browser. So the blob carries a seal of our own (`stamp`), and what was
  charged is checked against what the catalogue asks (`entitlement_for`).
* Some events arrive **with nothing we set on them** — a refund issued from a
  dashboard, a chargeback opened by a bank, a dunning retry. So finding our own
  user from our own rows is not a nicety, it is a required path.
* Money comes back in **three different meanings**: all of it, some of it, and
  a credit against a future invoice. They are not interchangeable, and each
  processor spells them differently while meaning the same three things.
* A **subscription has a life of its own**, separate from any one payment:
  started, renewed, retried after a failure, cancelled but paid until a date,
  finally ended. Cancelling is not refunding.
* An amount is **minor units plus a currency**, and a **billing country**
  decides the tax, so both travel with the event.

**What is an accident of Paddle** — none of this may leak past an adapter:

* The single `Paddle-Signature: ts=…;h1=…` header, and a signed message of
  `timestamp:body`. Dodo signs `id.timestamp.body` across three Standard
  Webhooks headers. Same idea, no shared byte.
* The name `custom_data` for the blob we echo through a checkout, and the fact
  that it is a blob at all.
* `data.id` meaning a different object per event family — a transaction, an
  adjustment, or a subscription — which is a shape that has already cost us one
  real bug (see `Event.transaction_id`).
* Spelling an adjustment as `action` × `type`, and the specific words "refund",
  "chargeback", "credit", "full", "partial".
* `details.totals.grand_total`, and its being a **string**.
* The browser being handed a **price id** and opening an overlay with a client
  token. Dodo's server creates a checkout session and hands back a URL or a
  client secret, and the browser never learns a price identifier — which is
  strictly the better shape, so `SessionHandle` carries both and the client
  uses whichever the adapter filled in.
* Event type strings, their `transaction.` / `adjustment.` / `subscription.`
  families, and sandbox and live being two hostnames.

The one thing deliberately *not* abstracted is the catalogue. What we sell, at
what price, in which currency, is our decision and not a processor's — a
processor only ever holds an identifier pointing back at a row of it.

**What the stores changed, and what they did not.** Apple and Google are the
third and fourth implementation of this seam, and most of the paragraphs above
survived them unedited: a signed statement is still the only trustworthy claim
that money moved, delivery is still at least once, a subscription still has a
life of its own, and a cancellation still runs to the end of the paid period.
Four things did not fit, and each one is a field or a method here rather than a
branch upstairs:

* **The purchase is not a webhook.** The app is handed a signed transaction the
  moment the sheet closes and the person is standing there waiting; the store's
  notification may be minutes behind. `StoreProvider.verify_purchase` is that
  path, and it is the only method a card processor does not have.
* **We do not set the price.** Apple charges a Japanese buyer ¥900 for the door
  and no row of `REGIONAL_CENTS` says so. `priced_by_us` turns off a comparison
  that would refuse every honest purchase, and the signed `productId` is what
  stands in its place.
* **The store is the seller.** It sends the receipt, so `issues_the_receipt`
  stops us logging an incomplete-waiver alarm about a waiver that is not ours.
* **The delivery may say almost nothing.** A Play notification is a package
  name, an integer and a token, and Google's own documentation says to go and
  ask. `enrich` is that call, and it happens after the idempotency check so a
  replay costs no quota.
"""

from __future__ import annotations

import enum
import hashlib
import hmac
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable

log = logging.getLogger("alma.billing")

#: Reject a signature older than this even if it verifies. A valid signature
#: replayed a week later is still a replay.
#:
#: Provider-neutral on purpose. Paddle documents a five-minute window; Dodo's
#: documentation gives no replay guidance at all, which is a reason to keep our
#: own number rather than to drop the check — an unbounded window means a
#: signature captured from a log is good forever.
MAX_SIGNATURE_AGE = 300  # seconds


class InvalidSignature(Exception):
    """The webhook did not come from the processor, or has been tampered with.

    Raised rather than returned as a `False`, and that is a decision worth
    defending: "no webhook secret is configured" and "this signature does not
    match" are the same boolean and completely different incidents. The first
    is an operator error that should page somebody the moment a deploy takes
    traffic; the second is a rotated key or an attacker. The endpoint answers
    401 with the reason in the body, and the reason is only there if the
    failure carried it.
    """


class BillingUnavailable(Exception):
    """No processor is configured, or the processor refused.

    Notably raised by `cancel_subscription` when there is no API key. A cancel
    that quietly does nothing is worse than one that fails loudly: the person
    who asked believes they have stopped paying, and finds out otherwise on
    their card statement.
    """


class SelfServiceOnly(BillingUnavailable):
    """This processor will not let *us* cancel; the customer has to.

    A subclass rather than a sibling so that any caller which only knows how to
    handle `BillingUnavailable` still handles this one — as a refusal, which it
    is — while a caller that knows better can offer the person the door instead
    of an apology.

    It exists because of the stores. On Apple there is no server API to cancel
    an auto-renewable subscription at all: the subscription belongs to the Apple
    ID, not to our account, and Apple's own Settings screen is the only place it
    can be stopped. Google *does* expose `purchases.subscriptionsv2.cancel`, and
    we deliberately do not call it — calling it would mean two cancellation
    paths for one subscription, ours and Play's, with our copy of the state
    guessing at the other's, and the person who cancels in Play (which they can
    always do) would still be told by us that their plan renews.

    So the honest answer on a store is a link. `manage_url` is that link, and it
    is a field rather than prose because the client has to be able to *open* it —
    a message saying "cancel in Settings" is what an app gets rejected for under
    the same guideline that requires a subscription-management link.
    """

    def __init__(self, message: str, *, manage_url: str) -> None:
        super().__init__(message)
        self.manage_url = manage_url


class ProductMismatch(Exception):
    """The store signed a purchase of something other than what is being claimed.

    The store equivalent of `_the_money_covers_it`, and needed for the same
    reason: the client names the thing it wants unlocked, and the client is not
    a party we trust. On a card processor the lie available to a client is a
    *price*; on a store the price is Apple's or Google's and cannot be touched,
    so the only lie left is the product — buy the $5.99 door, claim the $38.99
    archive. The store's own signature over `productId` is what refuses it.
    """


class PurchaseIncomplete(Exception):
    """The store knows this purchase and says it has not (or no longer) happened.

    Distinct from a forged transaction, because the two are different incidents
    with different answers. A forgery is an attack and the response is a 401 and
    a log line somebody reads. This is a purchase in `Pending` — a Play
    slow-payment method, a Family-Ask approval — or one already refunded or
    revoked, and the response is "not yet" or "not any more", which the client
    renders rather than reports.
    """


class EventKind(str, enum.Enum):
    """What a processor just told us happened, in words we chose.

    This is the taxonomy, not the policy. It answers "what is this event", and
    deliberately not "what should we do about it" — the second question is
    answered by the `grants` / `revokes` / `moves_money` flags an adapter
    stamps onto the event, because the two providers we have read do not agree
    about which of these should end somebody's access and we would rather that
    disagreement be visible than averaged away.

    The values that matter most are the ones that look like a revocation and
    are not. `SUBSCRIPTION_DUNNING` is a failed renewal the processor is still
    retrying, and `SUBSCRIPTION_CANCELLED` is a plan that keeps working until
    the period already paid for runs out. Treating either as "access stops now"
    takes a reading away from somebody who has paid for it.
    """

    PAYMENT = "payment"
    PAYMENT_FAILED = "payment_failed"
    #: Money coming back, or a credit that only looks like it. The `adjustment`
    #: pair on the event says which.
    ADJUSTMENT = "adjustment"
    #: A card issuer arguing about a charge, before anybody has won. Distinct
    #: from `ADJUSTMENT` because no money has moved yet and it may never: a
    #: dispute that is merely opened must not touch the refund column, and it
    #: must not close a grant that may still be won back. Only its terminal
    #: outcomes are adjustments.
    DISPUTE = "dispute"
    SUBSCRIPTION_STARTED = "subscription_started"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_DUNNING = "subscription_dunning"
    SUBSCRIPTION_PAUSED = "subscription_paused"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    SUBSCRIPTION_ENDED = "subscription_ended"
    #: A processor shipping a feature we have not adopted. Recorded, ignored,
    #: and not an error — treating an unknown type as a failure means every
    #: product launch by our processor becomes a 500 and a retry storm.
    UNKNOWN = "unknown"


#: The adjustment actions on which money actually comes back to the payer.
#:
#: A `credit` reduces what is owed on a future invoice and returns nothing on a
#: paid transaction, so counting it as a refund would both overstate the refund
#: column and — if it were also allowed to close a grant — take a reading away
#: from somebody who still paid for it. Closing is a stricter question again: a
#: *returning* action that is `full`. A partial refund reduces a charge; it
#: does not undo what the charge bought.
RETURNING_ACTIONS: frozenset[str] = frozenset({"refund", "chargeback"})


@dataclass(frozen=True, slots=True)
class NormalisedEvent:
    """One webhook, in our words rather than the processor's.

    Everything above the adapter reads this and nothing else. The three
    booleans are the whole policy surface: an adapter has already asked its own
    provider's event-type strings whether this grants, revokes or moves money,
    so no caller has to hold a list of another company's vocabulary.

    `type` and `payload` are kept verbatim anyway, because the row in
    `webhook_event` is what support reads at two in the morning and a
    normalised summary is not enough to reconstruct what arrived.
    """

    provider: str
    id: str
    #: The processor's own event-type string, recorded rather than interpreted.
    type: str
    kind: EventKind
    #: Our user, when the processor is echoing back something we set. `None` on
    #: every event we did not originate — refunds, chargebacks, dunning — which
    #: is why finding an owner from our own rows is a required path and not a
    #: fallback.
    owner_id: str | None = None
    #: The catalogue key, already resolved. Which field of which object held it
    #: — our own metadata, or a price identifier we have to look up — is the
    #: adapter's problem and dies inside it.
    product: str | None = None
    subscription_id: str | None = None
    transaction_id: str | None = None
    amount_cents: int = 0
    currency: str = "USD"
    country: str | None = None
    #: The address the **processor** collected from the buyer, when the delivery
    #: carries it. This is not `User.email` and must never be written to it:
    #: that column is the sign-in identity, and an unverified address typed at
    #: somebody else's checkout written there is an account-takeover primitive
    #: through `accounts.by_email`. What it is for is the receipt — a guest may
    #: buy, a guest has no address of ours, and without one the confirmation
    #: that completes the withdrawal waiver has nowhere to go. `None` where the
    #: processor did not put it in the body; see `BillingProvider.buyer_address`,
    #: which is allowed to go and ask.
    buyer_email: str | None = None
    #: The processor's own word for the subscription's state. Written to the
    #: entitlement and never read back by the paywall: the day a processor
    #: renames one of these strings must not be the day everybody who has paid
    #: is locked out.
    status: str | None = None
    #: When the plan bills again, if the event says. Distinct from an expiry:
    #: this is a promise to charge, that is the moment access stops, and
    #: between a cancellation and the end of a paid period they disagree.
    renews_at: datetime | None = None
    #: (action, type) — e.g. ("refund", "partial"). `None` when this is not an
    #: adjustment at all.
    adjustment: tuple[str, str] | None = None
    #: Токен, который приложение положило в покупку и магазин вернул **внутри
    #: подписанного пейлоада**: `appAccountToken` у Apple,
    #: `obfuscatedExternalProfileId` у Google.
    #:
    #: Единственное поле здесь, которое сочинили мы, а магазин заверил. Тем оно
    #: и ценно: `owner_id` приходит из нашей сессии (кто платит), а это отвечает
    #: на второй вопрос — **за кого** платят. Для расходуемой проверки пары
    #: второго вопроса не избежать: `pair.check` покупается многократно, и один
    #: и тот же `productId` в разных покупках означает разных людей.
    #:
    #: Значение непрозрачно для этого модуля: он его переносит, а расшифровывает
    #: `billing.pairs`, где лежит и правило, по которому токен выводится. Так
    #: сделано потому, что «токен» — понятие магазинов, а «профиль партнёра» —
    #: наше, и адаптер не должен знать второго.
    account_token: str | None = None
    #: Партнёр, про которого этот платёж, — уже разобранный из токена.
    #:
    #: Заполняется **не адаптером**: магазин про наши профили не знает, а знает
    #: `billing.pairs.partner_for`, которому нужна база. Роутер ставит его перед
    #: `entitlement_for`, и это единственный источник, из которого грант пары
    #: узнаёт имя профиля. Из тела запроса он не берётся никогда — тело пишет
    #: клиент, и `profile_id` оттуда означал бы «открой мне отчёт про любого
    #: человека, чей id я угадал, за одну свою покупку».
    partner_id: str | None = None
    grants: bool = False
    revokes: bool = False
    moves_money: bool = False
    #: Whether `amount_cents` may be checked against our own catalogue.
    #:
    #: True on a card processor, where we set the price, publish it, and are
    #: therefore entitled to refuse a charge that does not cover it. **False on
    #: a store**, and that is not a weakening of the check: Apple and Google set
    #: the price themselves, per storefront, from a tier we chose in a console —
    #: a Japanese buyer is charged ¥900 for the door and nothing in
    #: `REGIONAL_CENTS` says so, because that file holds the prices *we* charge.
    #: Comparing them would refuse every legitimate purchase outside the
    #: currencies we happen to price in, and converting one into the other is
    #: exactly the request-time arithmetic `catalogue.py` exists to forbid.
    #:
    #: What replaces the check is stronger rather than weaker, which is the only
    #: reason it is allowed to be skipped. The price check guards against a
    #: client that chose its own price id; on a store the client never names a
    #: price *or* a product — it hands us the store's own signature over the
    #: `productId`, and `ProductMismatch` refuses anything that is not the thing
    #: being claimed.
    #:
    #: The rejected alternative was to set `moves_money=False` on store events
    #: and skip the whole money path. It costs too much: no `Purchase` row, so
    #: no money trail and no `transaction_id` on the entitlement, and therefore
    #: no way for a refund to find the one-time purchase it undoes.
    priced_by_us: bool = True
    payload: dict = field(default_factory=dict)

    @property
    def returns_money(self) -> bool:
        """Whether this adjustment actually sends money back to the payer."""
        return self.adjustment is not None and self.adjustment[0] in RETURNING_ACTIONS

    @property
    def closes_the_grant(self) -> bool:
        """Whether what this undoes should stop being readable.

        A full return, and only a full return. Somebody refunded five dollars
        of a thirty-nine dollar archive keeps the archive — the alternative is
        repossessing a reading they have already read, over money we chose to
        give back. An event that is not an adjustment at all answers `True`,
        because then the question is settled by `revokes` instead.
        """
        if self.adjustment is None:
            return True
        return self.returns_money and self.adjustment[1] == "full"


@dataclass(frozen=True, slots=True)
class SessionHandle:
    """Everything a client needs to open one checkout, whoever is running it.

    Two shapes fit in here because the two processors disagree about who holds
    the price. Paddle hands the browser a `price_id` and a client token and the
    browser opens an overlay; Dodo's server creates a session and hands back a
    `url` or a `client_secret`, and the browser never learns a price identifier
    at all. The second is better — a price the client names is a price the
    client can change — so the fields for it are here and an adapter fills in
    whichever it can honour.

    `cents` and `display` are ours either way. What the paywall showed and what
    the card is charged have to be the same number, and the only way to keep
    that true is for both to come from the same row of the catalogue.
    """

    provider: str
    product: str
    currency: str
    cents: int
    display: str
    #: Echoed back to us on the webhook. This is how a payment finds its owner;
    #: matching on email would attach it to whoever shares an address with the
    #: payer, which for a family is common.
    #:
    #: `None` where the adapter sealed it into a server-created session and the
    #: browser has no reason to see it — which is the better shape, and the one
    #: Dodo has. It is not `{}`, because an empty dict in the JSON body reads as
    #: "there is metadata and it is empty" rather than "this processor does not
    #: put metadata through the browser at all".
    custom_data: dict | None = None
    price_id: str | None = None
    client_token: str | None = None
    environment: str | None = None
    #: A hosted payment page to send the buyer to.
    url: str | None = None
    #: For a checkout SDK that mounts in the page.
    client_secret: str | None = None
    #: The processor's own id for the payment it just created, if it made one
    #: before the money moved. Never a grant on its own — the webhook is.
    reference: str | None = None

    def to_client(self) -> dict:
        """The JSON the checkout endpoint returns.

        Fields the adapter could not fill are dropped rather than sent as
        `null`, so a client cannot reach for a price id that does not exist and
        pass `undefined` to an SDK — the failure that produces is a checkout
        that silently never opens.
        """
        body: dict = {
            "provider": self.provider,
            "product": self.product,
            "currency": self.currency,
            "cents": self.cents,
            "display": self.display,
        }
        optional = {
            "custom_data": dict(self.custom_data) if self.custom_data else None,
            "price_id": self.price_id,
            "client_token": self.client_token,
            "environment": self.environment,
            # `checkout_url`, not `url`. The field is `url` on the record
            # because that is what it is; it is renamed exactly once, here, on
            # the way out — a key called `url` in a body that also carries a
            # price and a product gets read as "the thing to link to" by
            # whoever arrives next. The router used to do this rename itself,
            # which meant three parties held two names for one value.
            "checkout_url": self.url,
            "client_secret": self.client_secret,
            "reference": self.reference,
        }
        body.update({key: value for key, value in optional.items() if value is not None})
        return body


@runtime_checkable
class BillingProvider(Protocol):
    """What every payment processor has to be able to do for us.

    Shaped against Paddle and Dodo at once rather than against the one we
    happen to have written first, because a protocol shaped around a single
    provider is a protocol that gets rewritten the moment the second arrives.
    Where the two genuinely differ — who holds the price, how many headers
    carry a signature, whether an email address is required before a session
    can exist — the difference is a field or a flag here, not a branch upstream.
    """

    #: Goes in `webhook_event.provider` and `entitlement.source`. A row that
    #: cannot say which processor wrote it is a row nobody can reconcile after
    #: a migration.
    name: str

    #: The processor's own event-type strings that may create a grant, and
    #: those that may end one. Named per adapter because the strings are
    #: another company's vocabulary — and, less comfortably, because the two
    #: providers do not agree on the *policy* either: see the note on Paddle's
    #: `REVOKING`, which ends access on a cancellation and on a dunning retry
    #: where the Dodo rules say neither should.
    granting: frozenset[str]
    revoking: frozenset[str]

    #: The **merchant of record**: the company that legally sells to the buyer,
    #: appears on their card statement, and is named on our refunds page. Not
    #: cosmetic and not ours to hard-code — a build configured for a different
    #: processor and still naming the old one is telling a card issuer the wrong
    #: seller during a dispute, on the page the issuer reads. `/billing/catalogue`
    #: publishes it so the interface says whatever is actually true today.
    merchant: str

    #: Whether a session cannot be created without a buyer's email address.
    #: Dodo requires one to create a customer, which turns the email field on
    #: the offer screen from a nice-to-have into an API precondition — better
    #: discovered from this flag than from a 400 after the person clicked buy.
    requires_email: bool

    #: Whether **the processor** confirms the contract on a durable medium.
    #:
    #: False on a card processor, which is why `_confirm_the_purchase` exists at
    #: all: CRD Art. 16(m) only extinguishes the 14-day withdrawal right when
    #: prior consent, an acknowledgement, *and* a confirmation under Art. 8(7)
    #: have all happened, and on Paddle or Dodo the third of those is a letter we
    #: send. True on a store, where Apple and Google are the merchant of record
    #: and email the receipt themselves — we are not the seller and have no
    #: address to write to anyway.
    #:
    #: A flag rather than "no address, so skip it", because those two states have
    #: to produce different log lines. A card payment with no address is an
    #: incident: that buyer's waiver is incomplete and they keep their 14 days.
    #: A store payment with no address is Tuesday. Logging the first sentence
    #: about the second is how a real alarm gets tuned out.
    issues_the_receipt: bool

    def verify(
        self, raw_body: bytes, headers: Mapping[str, str], *, secret: str | None = None
    ) -> None:
        """Raise `InvalidSignature` unless this body really came from us.

        Takes the whole header mapping rather than one header's value: Paddle
        signs with one header, Dodo with three, and a signature scheme is
        exactly the kind of thing that grows a header.

        Takes the **raw body**, never a re-serialised dict. Re-encoding JSON
        changes bytes and therefore changes the digest, so a handler that
        verifies against `json.dumps(payload)` verifies nothing except its own
        round trip.
        """
        ...

    def parse(
        self, payload: dict, headers: Mapping[str, str] | None = None
    ) -> NormalisedEvent:
        """One delivery, in our words.

        The headers are here because **the per-delivery id is not always in the
        body.** Paddle puts `event_id` in the payload; Dodo follows Standard
        Webhooks and puts `webhook-id` in a header, and that header is the
        idempotency key — the one thing insert-before-process depends on. A
        protocol that took only the payload made every Dodo delivery fall back
        to an id derived from the body, and Dodo documents that a retry carries
        "the latest payload at the time of delivery": one field of that derived
        identity moving between attempts turns a retry into a new event, and a
        granting event granted twice is a billing period nobody paid for.

        Optional so that an adapter which does not need them can ignore the
        argument, never so that a caller may omit it.
        """
        ...

    async def enrich(self, event: NormalisedEvent) -> NormalisedEvent:
        """Fill in what the delivery did not carry, asking the processor if need be.

        A separate step, and asynchronous, because of Google. A Real-time
        Developer Notification contains a package name, an integer, and a
        purchase token — **not** the product, the order id, the expiry or the
        state. Google's own documentation says outright to call the Play
        Developer API after receiving one, so on that adapter a notification
        cannot be turned into a `NormalisedEvent` without a network call, and
        `parse` is synchronous.

        The rejected alternative was to make `parse` a coroutine. It is called
        from a signature-checking path on two other adapters that need nothing
        of the kind, and making the common case async to serve the uncommon one
        puts an `await` in front of a pure function forever.

        Called **after** the idempotency check rather than before, which is why
        it is worth being a separate step rather than folded into `parse`: a
        replayed delivery costs no API quota, and Google's documentation asks
        for exactly that.

        Every adapter that already knows everything returns the event it was
        given. It is not optional on the protocol, because an adapter that
        silently did not implement it would produce an event missing the fields
        that decide a grant.
        """
        ...

    async def open_session(
        self,
        *,
        product: str,
        user_id: str,
        currency: str,
        country: str | None = None,
        email: str | None = None,
    ) -> SessionHandle:
        """Start one checkout. Raises `NotSold` where the price does not exist."""
        ...

    async def cancel_subscription(self, subscription_id: str) -> None:
        """Stop the next charge, and let the paid period run out.

        Not a refund and not a revocation: the person has paid for a period and
        keeps it. Raises `BillingUnavailable` rather than returning quietly
        when there is no API key.
        """
        ...

    async def buyer_address(self, event: NormalisedEvent) -> str | None:
        """Where to send this buyer's receipt, as the processor knows it.

        A coroutine and not a field because the two processors differ in
        exactly the way that matters: Dodo puts `data.customer.email` in the
        body of every payment, and Paddle does not put an address in a
        transaction payload at all — it sends a customer id and expects the
        question to be asked. So one adapter answers from the payload it was
        handed and the other may have to make one HTTP call, and neither
        difference is allowed upstairs.

        Why it is worth a call: **a guest may buy**, that is deliberate and the
        funnel depends on it, and a guest has no address of ours. Without this
        the entire pre-account funnel gets no receipt, which means no
        confirmation on a durable medium, which means the withdrawal waiver
        those buyers gave is incomplete and they keep their 14 days whatever
        they ticked. One request per payment is a cheap price for the leg of a
        legal test.

        Returns `None` rather than raising when the processor will not say. The
        caller logs that and sends nothing; a receipt is not worth failing a
        webhook over, because a failed webhook is retried and a retried webhook
        is how one payment becomes two grants.
        """
        ...


@runtime_checkable
class StoreProvider(BillingProvider, Protocol):
    """A processor where the *app*, not our server, opens the purchase.

    The one thing a store does that a card processor cannot, and therefore the
    one method that could not go on `BillingProvider` without every adapter
    growing a `raise NotImplementedError`. Apple and Google hand the app a
    signed proof of purchase the moment the sheet closes; there is no webhook at
    that moment and there may never be one, because the App Store Server
    Notification for a first purchase can arrive seconds or minutes later — and
    the person is standing there, having paid, looking at a locked chapter.

    So the client asks us to verify, and we do it against the store's own keys.
    That is the whole of the difference; everything downstream of the returned
    `NormalisedEvent` is the same seam the card processors go through.
    """

    #: Where the customer manages and cancels their own subscription. Published
    #: to the client because a store subscription can only be cancelled there,
    #: and an app that says so without offering the link is an app that fails
    #: review for it.
    manage_url: str

    async def verify_purchase(self, *, transaction: str, product: str) -> NormalisedEvent:
        """Check one proof of purchase against the store, or refuse it.

        `transaction` is the store's own proof and its shape differs: Apple's is
        a **JWS**, signed by a certificate chain rooting in the Apple Root CA, and
        it carries the whole truth inside it. Google's is an opaque **purchase
        token** which carries nothing at all and has to be exchanged for the
        truth over the Play Developer API. One parameter for both, because the
        client's job is identical either way — hand over what the store gave you
        — and a field named for one platform's shape is a field the other
        platform's client has to be told to ignore.

        `product` is the catalogue key being claimed, and it is checked rather
        than believed: `ProductMismatch` if the store signed a different one.

        Raises `InvalidSignature` for a forgery or another app's bundle,
        `PurchaseIncomplete` for a purchase the store says has not settled, and
        `BillingUnavailable` when we cannot ask.
        """
        ...


# ── what a store calls the things in our catalogue ─────────────────────────
#
# A store product id is not like a Paddle price id, and the difference decides
# where it lives. A price id is *issued* by a processor: it appears in a
# dashboard after somebody creates a price, and no amount of code here can
# predict it — which is why `Product.processor_ids` is empty and has to be
# filled in by hand. A store product id is the opposite: **we choose it** and
# type it into App Store Connect or the Play Console. There is nothing to fetch,
# so a table of them would be a second place to keep the same decision, and the
# failure mode of a table that disagrees with a console is a purchase that
# verifies and grants nothing.
#
# So it is a rule instead, and the rule is the contract with whoever fills in
# the console. Both stores restrict the character set: App Store Connect allows
# alphanumerics and periods, the Play Console lowercase alphanumerics,
# underscores and periods. Neither allows the hyphen four of our keys carry —
# `birth-card`, `solar-return`, `archive-bump`, `archive-upgrade` — so the
# hyphen becomes an underscore and comes back on the way in. That is reversible
# only because no catalogue key contains an underscore, which is a fact a test
# pins rather than a hope.
#
# An identifier pinned in `Product.processor_ids` still wins. It costs one
# lookup and it is the escape hatch for the day a product has to be re-created
# in a console under a name the rule cannot produce — a store will not let a
# product id be reused after deletion.


def _store_prefix(prefix: str | None) -> str:
    if prefix is not None:
        return prefix
    from ..config import settings

    return settings().store_product_prefix


def store_product_id(slug: str, *, processor: str, prefix: str | None = None) -> str:
    """What `processor` calls the catalogue row `slug`."""
    from .catalogue import PRODUCTS

    item = PRODUCTS.get(slug)
    pinned = item.identifier(processor) if item is not None else ""
    if pinned:
        return pinned
    return f"{_store_prefix(prefix)}{slug.replace('-', '_')}"


def store_slug(product_id: str, *, processor: str, prefix: str | None = None) -> str | None:
    """The catalogue key behind a store product id, or `None` if it is not ours.

    `None` is the answer that refuses a grant, and it has to be reachable: a
    store account can carry products from an older price list, and a purchase of
    one of those is a payment to record rather than a chapter to unlock.
    """
    from .catalogue import PRODUCTS, by_price_id

    found = by_price_id(product_id, processor)
    if found is not None:
        return found
    head = _store_prefix(prefix)
    if not product_id.startswith(head):
        return None
    slug = product_id[len(head):].replace("_", "-")
    return slug if slug in PRODUCTS else None


# ── the metadata we put on a checkout, and why it is signed ────────────────

#: The field inside a processor's metadata blob that proves *we* wrote the two
#: fields beside it. The name is ours and appears in no processor's schema.
SEAL_FIELD = "alma_seal"

#: Domain separation for the key. The seal and a session token are two
#: different statements made with the same secret, and a key used for two
#: purposes is a key where a value from one can be replayed into the other.
_SEAL_LABEL = b"alma.checkout.owner.v1"

#: `\x1f` (unit separator) cannot occur in a user id or a catalogue key, so
#: `("ab", "c")` and `("a", "bc")` cannot seal to the same digest. Joining on a
#: character that *can* occur is how two different statements share a signature.
_SEAL_JOIN = "\x1f"


def _seal(user_id: str, product: str) -> str:
    from ..config import settings

    key = hmac.new(settings().jwt_secret.encode(), _SEAL_LABEL, hashlib.sha256).digest()
    message = f"{user_id}{_SEAL_JOIN}{product}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def stamp(user_id: str, product: str) -> dict:
    """The metadata a checkout is opened with: who it is for and what it buys.

    **The signature on a webhook proves the processor relayed a field
    faithfully. It proves nothing about who wrote it.** Every processor echoes
    this blob back to us inside a signed envelope, and on Paddle the blob passes
    through the browser on its way out — paddle.js takes `customData` as an
    argument, and the client token that opens an overlay is public by design, so
    anyone can open a checkout against our own account with any metadata they
    like. Reading a grant out of that field meant the payer chose both **which
    account** was credited and **what it bought**: an $8.99 door, relabelled
    `archive` in a console before the overlay opened, wrote the whole $38.99
    archive permanently, and relabelled `annual` wrote a year of everything.
    Neither the amount sitting on the same event nor `may_be_offered` was ever
    consulted, so the guard on the checkout guarded the one door that was
    already locked.

    So the two readable fields carry a third beside them, keyed on our own
    secret. They stay readable because a payment in a processor's dashboard that
    says only `alma_seal: 4f2b…` is a payment support cannot attribute; nothing
    reads them back without the seal agreeing.

    This is *not* a replacement for the price check in `entitlement_for`. The
    seal says which product we opened a checkout for; it cannot say which price
    was actually charged, and on Paddle the browser holds the price id too.

    One consequence to know about: the key is derived from `ALMA_JWT_SECRET`, so
    rotating that invalidates every seal in flight — including the copies
    riding on live subscriptions, which processors echo on every renewal for the
    life of the plan. A renewal therefore never depends on it: it is matched by
    subscription id against a row we already hold. See `_extend_the_plan_we_hold`
    in the router.
    """
    return {"user_id": user_id, "product": product, SEAL_FIELD: _seal(user_id, product)}


def sealed_owner(custom: Mapping[str, object] | None) -> tuple[str | None, str | None]:
    """The owner and product *we* put on this checkout, or `(None, None)`.

    `(None, None)` is not an error and not rare: a refund issued from a
    dashboard, a chargeback opened by a bank, a dunning retry and a support
    checkout all arrive carrying nothing we set. The owner for those is
    recovered from our own rows, which is a required path rather than a
    fallback — so an unsealed blob is simply an event we did not originate, and
    it grants nothing.
    """
    if not custom:
        return (None, None)
    user_id = str(custom.get("user_id") or "")
    product = str(custom.get("product") or "")
    provided = str(custom.get(SEAL_FIELD) or "")
    if not (user_id and product and provided):
        return (None, None)
    # Constant time, for the same reason the webhook signature is: a comparison
    # that returns early leaks the digest a byte at a time to anyone willing to
    # open checkouts and measure, and forging one seal forges every purchase.
    if not hmac.compare_digest(_seal(user_id, product), provided):
        log.warning("checkout metadata carried a seal we did not write; ignoring it")
        return (None, None)
    return (user_id, product)


# ── the parts of a signature check that are not any one provider's ─────────


def header_value(headers: Mapping[str, str], name: str) -> str:
    """One header, found without caring how the sender capitalised it.

    Starlette hands us a case-insensitive mapping and a test hands us a plain
    dict, and HTTP header names are case-insensitive in both.
    """
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return value or ""
    return ""


def check_freshness(timestamp: str | int, *, now: float | None = None) -> None:
    """Reject a signature old enough to be a replay, or raise.

    Shared by every adapter, because the window is a decision about our own
    risk and not about a processor's scheme. Dodo's documentation offers no
    guidance here at all; that is a reason to keep ours rather than to widen it
    to infinity.
    """
    try:
        age = abs((now if now is not None else time.time()) - int(timestamp))
    except (TypeError, ValueError) as exc:
        raise InvalidSignature("signature timestamp is not a number") from exc
    if age > MAX_SIGNATURE_AGE:
        raise InvalidSignature(f"signature is {age:.0f}s old — refusing a possible replay")


# The constant-time comparison itself is deliberately *not* wrapped in a helper
# here. `hmac.compare_digest` has to appear literally in each adapter's
# `verify`, and there is a test that reads the source to make sure it does —
# because the failure it prevents is invisible: a `==` on a digest still passes
# every functional test ever written for it, and only ever shows up as an
# attacker who measured the difference.


def moment(value: object) -> datetime | None:
    """An ISO-8601 instant from a processor, or `None` if it is not one.

    Tolerant on purpose. These timestamps only ever feed `renews_at`, which is
    shown to a person and never gates access, so a field a processor renames or
    stops sending must not turn a paid renewal into a 500 and a retry loop.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# ── what an event is worth, once it has been normalised ────────────────────

#: How long one billing period of each interval grants, before it has to be
#: paid for again. Thirty-one days rather than a calendar month so that a
#: renewal is always charged before access lapses; the grant is extended from
#: whichever is later — the current expiry or now — so the extra days do not
#: accumulate. A month that granted twenty-eight would take access away from
#: somebody who has paid, in the two days before the provider retries.
PERIOD: dict[str, timedelta] = {
    # Eight days for a week, one for a month: the buffer is the renewal
    # webhook's arrival window, so a slow store notice never locks out
    # somebody who has paid.
    "week": timedelta(days=8),
    "month": timedelta(days=31),
    "year": timedelta(days=365),
}


@dataclass(frozen=True, slots=True)
class Grant:
    """What one event says a person should be given.

    The entire contract between a processor and the entitlement layer. An
    adapter's job ends here: it produces one of these and nothing else, and
    anything it could not express as one of these is something the entitlement
    layer must not be asked to understand.

    A record rather than a tuple because it grew a scope and a subscription id
    and the tuple did not: `entitlement_for` returned `(system, kind,
    duration)` while the catalogue had already priced a recurring plan, so a
    monthly payment fell through to `("*", "one_time", None)` — no expiry, no
    subscription to cancel against, and `Entitlement.covers` answering True for
    the whole archive. Nothing reported it, because the row simply kept
    working: one $9.99 payment, the entire $38.99 archive, permanently. The
    `ValueError` `grant()` raises for a recurring kind with no duration never
    fired either, because the kind that reached it was "one_time".
    """

    system: str
    kind: str
    duration: timedelta | None
    scope: str
    subscription_id: str | None = None


def entitlement_for(event: NormalisedEvent) -> Grant | None:
    """What this event should grant, if anything.

    Provider-neutral because every question it asks has already been answered
    by the adapter: whether the event grants at all, and which row of the
    catalogue it names. What remains is our own product rule, and there are two.

    **A recurring plan is recognised by the catalogue having given the product
    an interval**, never by matching a list of kind strings written out here. A
    hand-written list is precisely what let a $9.99 monthly write a permanent
    everything-grant, because the list said "annual" and the monthly was not it.

    **What is granted has to be what the money paid for.** The amount is on the
    same event as the product, and nothing compared them: on the Paddle path the
    browser holds the price id as well as the metadata, so a checkout opened for
    the archive and paid at the door's price id charged $8.99 and granted
    $38.99 worth. `stamp` closes the half of that where the *product* is chosen
    in a console; this closes the half where the *price* is. Both are needed,
    and neither is sufficient alone.
    """
    from .catalogue import PRODUCTS

    if not event.grants or not event.product:
        return None

    product = PRODUCTS.get(event.product)
    if product is None:
        return None

    if not _the_money_covers_it(event, product):
        return None

    if product.scope == "pair":
        # **Грант пары называет партнёра, а не систему.** Каталог партнёра не
        # знает и знать не может: его назвал `PairIntent`, созданный до открытия
        # магазинного листа, и сюда он приезжает уже разобранным из токена
        # подписанного пейлоада (`partner_id`, приложение А4). Выписать грант с
        # `system="compatibility"` значило бы открыть отчёты про **всех**
        # партнёров за одну покупку в $4.99 — поэтому системы здесь нет вовсе, а
        # есть `pair:{profile_id}`.
        if not event.partner_id:
            # **Деньги записаны, доступ не выдан — и это не потеря денег, а
            # отложенная привязка.** Покупка без токена (старый клиент, редкий
            # сбой на стороне приложения) уходит в `status="unbound"`, человек
            # получает 202 и экран «к кому применить», а `POST /billing/pair/bind`
            # выписывает грант вторым шагом. Единственная альтернатива — выдать
            # хоть что-нибудь наугад — открывает отчёт не про того человека, и
            # исправить это уже нечем: отчёт написан и прочитан.
            log.warning(
                "%s bought a pair check with no partner on the event: no token "
                "in the signed payload, so the grant waits for /billing/pair/bind "
                "(event %s)",
                event.product, event.id,
            )
            return None
        from ..auth.entitlements import pair_system

        return Grant(
            system=pair_system(event.partner_id),
            kind=product.kind,
            # Бессрочно, и это не описка рядом со словом «расходуемый».
            # Расходуется **покупка** (магазин обязан позволить купить её
            # снова), а выданный доступ — нет: отчёт, за который заплачено,
            # читается всегда. Срок здесь означал бы, что купленный текст
            # однажды закроется, а его уже прочитали.
            duration=None,
            scope=product.scope,
        )

    if product.interval:
        return Grant(
            system=product.slug,
            kind=product.kind,
            duration=PERIOD[product.interval],
            scope=product.scope,
            subscription_id=event.subscription_id,
        )
    return Grant(
        system=product.slug, kind=product.kind, duration=None, scope=product.scope
    )


def _the_money_covers_it(event: NormalisedEvent, product) -> bool:
    """Whether what was charged is at least what this product costs.

    Only asked of an event that **moved money**. A subscription-lifecycle event
    carries a plan id and no payment at all — Paddle's `subscription.activated`
    and Dodo's `subscription.active` both report zero — so demanding an amount
    there would refuse every legitimate activation. The money for those arrives
    on its own payment event, which is checked.

    `>=` and not `==`, in both directions on purpose. A merchant of record adds
    US sales tax *on top* of the price in some states, so the collected total is
    the published price or more; the European amounts in `REGIONAL_CENTS` are
    already tax-inclusive and land exactly on it. What is refused is the
    opposite shape — a total *below* the shelf price — which is not something an
    honest checkout can produce, because we issue no coupons and no partial
    payments. The day we do, this is the line that has to learn about them.

    A currency we do not price this product in is refused rather than converted:
    `cents_in` raises `NotSold` there, and a product that does not exist in a
    market cannot have been legitimately bought in it.
    """
    from .catalogue import NotSold

    if not event.moves_money:
        return True
    if not event.priced_by_us:
        # A store's own price, in a storefront's own currency. See
        # `NormalisedEvent.priced_by_us` for why comparing it to our catalogue
        # refuses honest purchases, and for what stands in its place.
        return True
    try:
        price = product.cents_in(event.currency)
    except NotSold:
        log.warning(
            "refusing a grant: %s is not sold in %s, so %s cannot have bought it",
            event.product, event.currency, event.amount_cents,
        )
        return False
    if event.amount_cents >= price:
        return True
    log.warning(
        "refusing a grant: %s %s does not cover %r at %s %s (event %s)",
        event.amount_cents, event.currency, event.product, price, event.currency, event.id,
    )
    return False


def provider_for(name: str | None = None) -> BillingProvider:
    """The adapter the configuration asks for.

    Imported inside the function rather than at module scope, because every
    adapter imports the vocabulary from this file and a top-level import back
    would be a cycle. That is also what keeps this module cheap: importing the
    types does not drag an HTTP client in behind them. It is also what lets the
    package delete one adapter without breaking the other — nothing imports an
    adapter until somebody asks for it by name.
    """
    from ..config import settings

    chosen = (name or settings().billing_provider or "paddle").lower()

    if chosen == "paddle":
        from .paddle import PaddleProvider

        return PaddleProvider()
    if chosen == "dodo":
        from .dodo import DodoProvider

        return DodoProvider()
    if chosen == "appstore":
        from .appstore import AppStoreProvider

        return AppStoreProvider()
    if chosen == "googleplay":
        from .googleplay import GooglePlayProvider

        return GooglePlayProvider()
    if chosen == "tbank":
        from .tbank import TBankProvider

        return TBankProvider()

    raise BillingUnavailable(
        f"{chosen!r} is not a payment processor this build knows how to talk to"
    )
