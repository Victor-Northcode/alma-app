"""Checkout, cancellation, the webhook, store purchases, the receipt, one downsell.

Nothing in this file knows which payment processor is running. It asks
`config.billing_adapter()` for one and speaks the vocabulary in
`billing/provider.py` — a `NormalisedEvent` with three flags on it, a
`SessionHandle`, a `Grant`. That is not architecture for its own sake: Paddle's
acceptable-use policy names our category as prohibited and nobody has approved
us yet, so which processor takes the money is a decision that will be made
*for* us, possibly twice. It has now been made twice, and neither time was a
card processor: Apple and Google both permit our category outright, and both are
the merchant of record.

That move added exactly one endpoint here, `/billing/iap/verify`, and it exists
for a reason that is about latency rather than about stores. A store's
notification is not fast enough to be the thing a person waits for — StoreKit
hands the app a signed transaction the instant the sheet closes and Apple's
notification is minutes behind — so the app tells us, and we check it against
the store. Everything after that check is the same path a webhook takes: the
same `_ingest`, the same insert-before-process, the same `_apply`. There is no
second set of idempotency rules, because a second set is how one payment becomes
two grants.

Three rules survive whoever the processor turns out to be.

**Entitlements are granted by the signed webhook, server-side.** Never by the
browser reporting that a checkout closed — anything the browser can decide, the
browser can be made to decide. The checkout endpoint hands out no access and
never has.

**Cancelling is not refunding.** `/subscription/cancel` stops the next charge
and leaves the entitlement exactly where it is, because the period has been
paid for. Revoking there would repossess something somebody bought. On a store
we cannot stop the charge at all — the subscription belongs to an Apple ID or a
Google account — so the endpoint answers 409 with the URL where its owner can,
and writes nothing: a local flag saying "cancelled" does not stop a card being
charged, and the person finds out on a statement.

**The downsell happens once.** A product decision enforced in code because it
is the kind of thing that erodes: when someone declines a purchase they are
offered a cheaper option once, and then never asked again. A second nudge is
what turns a person who was thinking about it into a person who has decided.

And one rule that is not about processors at all. **The receipt is part of the
sale, not part of the follow-up.** A buyer of digital content loses the 14-day
withdrawal right only if we also confirm the contract on a durable medium, so
the letter that goes out from the webhook is what makes the two checkboxes at
the checkout mean anything. It is sent from here, once per payment, for the
same reason the grant is: this is the one place that knows the money moved and
cannot be made to think so twice. On a store it is not sent at all, and that is
not a gap: Apple and Google are the seller, they charged the card, and the
confirmation is theirs. `issues_the_receipt` is what tells the two apart, so a
real alarm about an incomplete waiver does not fire on every store sale.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Request, status
from sqlalchemy import select

from ... import funnel, mail, region
from ...auth import entitlements
from ...billing import catalogue as prices
from ...billing.provider import (
    BillingUnavailable,
    EventKind,
    Grant,
    InvalidSignature,
    NormalisedEvent,
    ProductMismatch,
    PurchaseIncomplete,
    SelfServiceOnly,
    StoreProvider,
    entitlement_for,
)
from ...config import billing_adapter, settings
from ...db.models import (
    Consent,
    Entitlement,
    Purchase,
    User,
    WebhookEvent,
    as_utc,
    utcnow,
)
from ..deps import CurrentUser, EdgeCountry, SessionDep, Visitor

log = logging.getLogger("alma.api.billing")
router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/catalogue")
async def price_list(
    user: Visitor,
    session: SessionDep,
    edge: EdgeCountry,
    country: str | None = None,
) -> dict:
    """What things cost for this person. Every number here is one we take.

    **The country comes from the request, and it did not used to come from
    anywhere.** `useCatalogue(country?)` on the web took one and no caller ever
    passed one, so `currency_for(None)` answered USD and every visitor on earth
    was quoted dollars — a German reading a euro landing page and being shown
    `$5.99` for a door that costs `€6.49`. The client cannot fix that on its own:
    a browser knows its languages and its timezone, and neither of those is a
    country. The edge in front of this process does know, so `region.resolve`
    reads it off the header Cloudflare (or Vercel, or CloudFront) already wrote,
    and `?country=` stays as the fallback for a client that knows better and for
    the tests that pin the ladder market by market.

    **`Visitor`, not `CurrentUser`, and that one word is the whole point of the
    route.** Reading a price is looking at a shelf; it is not an act, and the
    owner's rule is that an account appears when somebody registers or has been
    through the journey rather than on a page view. This endpoint was the last
    place on the web where that rule was broken, and it was broken on the
    loudest page: the landing renders `<Pricing />` unconditionally,
    `useCatalogue` fetches on mount, and so a browser that loaded the site and
    touched nothing still ended up with a `user` row and a bearer token for it
    — the exact behaviour `POST /v1/events` had just stopped having. The 143
    accounts against 46 profiles would simply have been reproduced through this
    door instead.

    Worse than the row: the catalogue fetch goes out *before* the beacon does,
    so the minting request carried no `X-Alma-Anon` at all and there was nothing
    for `current_user` to claim. The browser came away holding an account that
    the funnel could never join to the visit that created it, and the first
    conversion rate read zero on a perfectly healthy first visit.

    Nothing in the response depends on there being an account: the price list
    is the same shelf for everybody, and the only per-person value left is the
    `unlocked` set further down, which is empty for an account minted a
    microsecond ago. (Кредитная подстановка, ради которой сюда раньше
    приходилось звать пользователя ещё раз, снята вместе с самими доборами —
    монетизация v3, ТЗ §2.)
    """
    where = region.resolve(stated=country, edge=edge)
    currency = prices.currency_for(where)
    listing = prices.catalogue(country=where)
    adapter = billing_adapter()
    # Which processor is running, and whether it can create a session without
    # an email address. Both are read by the offer screen *before* anybody
    # presses a button: a processor that has to create a customer cannot open a
    # checkout for an address it has never seen, so that address has to be
    # collected while the person is still deciding rather than discovered as a
    # 400 after they decided.
    #
    # Paddle's client token used to be published here as well. It is gone
    # because it is one processor's word: the token belongs to the session the
    # checkout endpoint creates, and a catalogue that names it is a catalogue
    # that has to be edited the day the processor changes.
    listing["provider"] = adapter.name
    listing["requires_email"] = adapter.requires_email
    # Who legally sells to this person. It is the processor, not us — both
    # adapters are merchants of record — and it is published rather than typed
    # into the interface because `src/lib/legal.ts` held it as a build-time
    # constant naming one of them. Switch processors and every legal page still
    # named the old seller, including the refunds page that tells people where
    # their money comes back from, which is the page a card issuer reads.
    listing["merchant"] = adapter.merchant
    # Where a subscriber goes to stop paying, when that is not us. Only the
    # stores fill it in — on Paddle and Dodo `/subscription/cancel` does the job
    # itself — and the settings screen reads it before it draws a cancel button,
    # because on iOS and Android the button has to be a link to the platform's
    # own subscription screen and an app that only *says* so fails review.
    manage_url = getattr(adapter, "manage_url", "")
    if manage_url:
        listing["manage_url"] = manage_url
    listing["unlocked"] = (
        [] if user is None else sorted(await entitlements.unlocked_systems(session, user))
    )
    return listing


@router.post("/checkout")
async def checkout(
    user: CurrentUser,
    session: SessionDep,
    edge: EdgeCountry,
    product: str = Body(embed=True),
    country: str | None = Body(default=None, embed=True),
    email: str | None = Body(default=None, embed=True),
    consent: dict | None = Body(default=None, embed=True),
) -> dict:
    """Start one checkout, and answer with whatever this processor needs to open.

    **A guest may buy.** This used to demand a signed-in account, which put a
    registration form between someone who had just decided to pay and the act
    of paying. That is the most expensive wall in any funnel, and it is
    unnecessary here: a guest already *is* an account row with an id, so the
    payment has something real to attach to. Signing in comes afterwards, and
    what it buys the person is durability rather than permission — see the
    warning the interface shows once the purchase lands.

    **`email` is a requirement for one processor and a courtesy for the
    other**, which is exactly why it is optional here rather than mandatory.
    Dodo's checkout session cannot be created without an address, because
    creating one creates a customer; so on Dodo an account with no email has to
    be asked for one *before* the button, and this endpoint says so with
    `email_required` rather than letting the processor refuse after the person
    has decided to pay. Paddle collects the address inside its own overlay, so
    demanding one here would reinstate the registration wall the paragraph
    above removed. A signed-in account's own address is used without asking.

    **`consent` is the evidence of a waiver, and it is written before the
    money.** Two boxes ticked in a browser are the first two legs of
    CRD Art. 16(m); the receipt is the third. They used to be sent here and
    dropped on the floor — accepted by FastAPI, ignored by everything, and then
    *asserted* by a receipt printed from a per-locale template, which is worse
    evidentially than saying nothing because it manufactures a record of a
    consent that may never have been given. So the sentences the buyer actually
    read are stored, at the moment they were read, and the webhook joins them to
    the payment. It is optional on the wire because a checkout without one is a
    legitimate different state — a surface that shows no boxes, and a buyer who
    therefore keeps their 14 days — and not because it is decoration.

    A `consent` that arrives malformed is logged and **discarded rather than
    refused**. Refusing would cost a sale over a bug in our own client; storing
    a half-read one would be the same fabrication in a smaller font. Discarding
    fails in the buyer's favour: no record, no waiver, the withdrawal right
    stands, and the receipt says so.

    The response shape belongs to `SessionHandle` and is provider-neutral: the
    `provider` field is the discriminant and the rest is what that one needs.
    Nothing about a person's access is decided here — the signed webhook does
    that, and this endpoint could be replayed all day without granting anybody
    anything.
    """
    try:
        prices.product(product)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    # Товар не с полки отказывается по имени, а не просто не попадает в список.
    # Условных цен в v3 нет, так что сегодня проверка пропускает все восемь
    # строк, — и она всё равно стоит здесь, потому что закрывала уже случавшуюся
    # дыру: `archive-bump` за $29.99 выдавал тот же грант, что архив за $38.99, а
    # этот эндпоинт принимал любой ключ по имени, то есть архив покупался на
    # девять долларов дешевле одним запросом. Первый же A/B по цене бандла
    # (ТЗ §7) заводит вторую цену на один и тот же грант.
    if not await entitlements.may_be_offered(session, user, product):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_offered",
                "message": f"{product!r} is not on offer to this account",
                "product": product,
            },
        )

    config = settings()
    if not config.billing_enabled:
        # Named variables rather than "billing is off", and named for whichever
        # processor is selected: an operator reading this needs to know which
        # line of the deploy configuration is empty, and being told to fill in
        # Paddle's keys while running Dodo is worse than being told nothing.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "billing_unavailable",
                "message": f"{', '.join(config.missing_billing_credentials())} are not set",
            },
        )

    adapter = billing_adapter()
    buyer = (email or user.email or "").strip()
    if adapter.requires_email and not _usable_address(buyer):
        # One error code for "we have none" and for "the one we have is not an
        # address", because the interface's answer to both is the same: ask for
        # one and try again. Splitting them would produce a second failure kind
        # that every caller has to handle identically.
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "email_required",
                "message": (
                    f"{adapter.name} cannot open a checkout without an email address"
                ),
                "product": product,
            },
        )

    # The same rule the catalogue used, and deliberately the same call: the
    # price somebody was shown and the price they are about to be charged have
    # to be decided by the same country, or the two come apart for anyone whose
    # client says one thing and whose connection says another.
    where = region.resolve(stated=country, edge=edge)
    currency = prices.currency_for(where)
    try:
        handle = await adapter.open_session(
            product=product,
            user_id=user.id,
            currency=currency,
            country=where,
            email=buyer or None,
        )
    except prices.NotSold as exc:
        # The five purchasing-power markets carry the archive and the year and
        # nothing else, so this is the ordinary path there rather than an edge
        # case. It used to fall out of the handler as a 500 — a crash in the
        # error tracker and nothing the client could render — because the
        # pricing lines sat outside the try above.
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_sold_here",
                "message": str(exc),
                "product": product,
                "currency": currency,
            },
        ) from exc
    except BillingUnavailable as exc:
        # The adapter's own refusal — no key, or the processor would not create
        # the session. A 503 rather than a 500: nothing is broken here, and the
        # client already knows how to say "you cannot buy this right now".
        log.warning("%s refused to open a session: %s", adapter.name, exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "billing_unavailable", "message": str(exc)},
        ) from exc

    # Only once the processor has actually opened something. A consent recorded
    # against a checkout that could not be created would be evidence of a
    # contract nobody could have entered into.
    _record_consent(session, user=user, product=product, given=consent)

    # And the same for the stage. `checkout_opened` used to exist only on the
    # browser's word, which meant a buyer with Do Not Track or GPC set produced
    # a purchase with no checkout above it — so the one conversion rate that
    # decides advertising spend was computed on a denominator that
    # systematically excluded privacy-conscious buyers. Duplicate rows are
    # harmless: the funnel counts distinct accounts, not events.
    try:
        await funnel.record(
            session,
            user_id=user.id,
            stage="checkout_opened",
            properties={"product": product, "currency": currency},
        )
    except Exception:  # noqa: BLE001 - measurement never costs a sale
        log.exception("could not record checkout_opened for %s", user.id)

    return handle.to_client()


#: How many statements one consent may carry, and how long each may be. Both
#: are ceilings rather than shapes: the offer screen sends two sentences and
#: the plan-shaped pair is also two, but a limit written as "exactly two" is one
#: that has to be edited the day a third box appears, and a column with no limit
#: at all is a place to put a megabyte.
MAX_STATEMENTS = 8
MAX_STATEMENT_CHARS = 400


def _record_consent(session, *, user: User, product: str, given: dict | None) -> None:
    """Write down what this buyer ticked, in the words they were shown.

    Returns nothing and raises nothing. Everything it refuses, it refuses by
    writing no row — which leaves the buyer with the withdrawal right they would
    have had if the boxes had never been on screen, and leaves the receipt with
    nothing to quote. That is the safe direction: the harm of a missing record
    falls on us, and the harm of an invented one falls on the person we invented
    it about.

    What is kept is `key` and `text` and nothing else. Not because a processor
    might send something else — this comes from our own client — but because
    this is a JSON column on a row keyed to a person, and the rule that stops a
    free-text field from one day holding a birth date is that the shape is
    fixed here rather than trusted upstream.
    """
    if given is None:
        return
    if not isinstance(given, dict):
        log.error("checkout for %s sent a consent that is not an object", user.id)
        return

    raw = given.get("statements")
    if not isinstance(raw, list) or not raw:
        log.error("checkout for %s sent a consent with no statements", user.id)
        return

    statements: list[dict] = []
    for item in raw[:MAX_STATEMENTS]:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()[:64]
        text = str(item.get("text") or "").strip()[:MAX_STATEMENT_CHARS]
        if key and text:
            statements.append({"key": key, "text": text})

    if len(statements) != len(raw[:MAX_STATEMENTS]):
        # Half a consent is not a consent. If any statement could not be read,
        # none of them is stored: quoting one of two ticked lines back at
        # somebody is a document that misrepresents what they agreed to.
        log.error(
            "checkout for %s sent %d statements and only %d were usable — "
            "recording none of them",
            user.id, len(raw), len(statements),
        )
        return

    session.add(
        Consent(
            user_id=user.id,
            product=product,
            locale=str(given.get("locale") or user.locale or "en")[:8],
            # The client's own clock, and it is allowed to be wrong. What this
            # column is for is the buyer's account of when they decided;
            # `created_at` beside it is ours, and the gap between them is
            # something a dispute can be argued over rather than something to
            # quietly overwrite.
            agreed_at=_moment(given.get("agreed_at")),
            statements=statements,
        )
    )


def _moment(value: object) -> datetime | None:
    """An ISO-8601 instant from a client, or `None`. Never an exception."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _usable_address(email: str) -> bool:
    """The loosest check that catches the slip people actually make.

    A missing or dangling `@`, and nothing else. Anything stricter starts
    refusing addresses that are perfectly valid — plus tags, apostrophes, new
    top-level domains, the whole internationalised world — and the cost of a
    false refusal here is a sale. The processor validates properly; this exists
    so that the common typo does not become an unexplained failure at the pay
    button.
    """
    return "@" in email and not email.startswith("@") and not email.endswith("@")


@router.post("/webhook", include_in_schema=False)
async def webhook(
    request: Request, session: SessionDep, background: BackgroundTasks
) -> dict:
    """The configured processor calls this. Nobody else may.

    Verified before it is parsed, recorded before it is processed, and a
    second delivery of the same event id does nothing — providers retry, and
    a duplicate grant is our bug rather than theirs.

    One route, one URL, whichever processor is running. The signature scheme is
    not: Paddle signs `timestamp:body` into one header and Dodo signs
    `id.timestamp.body` across three, so the whole header mapping is handed to
    the adapter and *it* knows which of them to read. This used to declare
    `Paddle-Signature` as a parameter, which put one processor's header in the
    function signature of the endpoint every processor has to call.

    The per-delivery id is the primary key of `webhook_event` and needs no
    translation: Paddle's `event_id` and Dodo's `webhook-id` are both stable
    per delivery, so insert-before-process idempotency is unchanged. But
    **where** it lives is not the same, which is why `parse` is handed the
    headers too. Paddle's is in the body; Dodo's is a header and nothing else,
    and this call omitted them — so every Dodo delivery was filed under an id
    derived from the body's identity instead. Dodo states that a retry carries
    "the latest payload at the time of delivery", so a refreshed timestamp made
    a retry look like a new event and granted a second period; two distinct
    refunds of one payment in the same second collided the other way and the
    second silently never happened.

    That same early return is what makes the receipt idempotent, and it is why
    the receipt is sent from here rather than from a job of its own: a processor
    retrying a delivery never reaches `_apply` a second time, so it cannot
    produce a second letter. `BackgroundTasks` is how the letter leaves *after*
    this transaction has committed and this response has been sent — a mail
    provider having a slow ten seconds must not hold a webhook open until the
    processor gives up and retries, because that retry is how one payment
    becomes two grants.
    """
    adapter = billing_adapter()
    raw = await request.body()
    try:
        adapter.verify(raw, request.headers)
    except InvalidSignature as exc:
        log.warning("rejected webhook: %s", exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    # The same bytes that were verified, parsed once. Re-reading the request
    # would be re-reading a cached body, but going through `raw` says outright
    # that nothing unverified reaches the parser.
    payload = await request.json()
    event = adapter.parse(payload, request.headers)
    if not event.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="event has no id")

    outcome, fresh = await _ingest(session, adapter, event, payload, background)
    if not fresh:
        return {"status": "already processed", "event_id": event.id}
    return {"status": outcome, "event_id": event.id}


async def _ingest(
    session,
    adapter,
    event: NormalisedEvent,
    payload: dict,
    background: BackgroundTasks,
) -> tuple[str, bool]:
    """Record one event exactly once and apply it. Returns (outcome, was it new).

    Lifted out of `webhook` when the stores arrived, because a store purchase
    verified from the app has to travel this identical path — recorded before it
    is processed, keyed on an id that a replay repeats, and applied by the same
    `_apply`. Writing a second path for it would have been writing a second set
    of idempotency rules, and the one thing every processor gets wrong is
    delivering twice.

    Insert-before-process is the whole mechanism and it is a database
    constraint rather than a code path: `webhook_event.id` is the primary key,
    so two concurrent deliveries of one event cannot both get past it.

    The enrichment happens **here**, after the duplicate check and before
    `_apply`, and the order is deliberate. Google's notification carries a
    package name, an integer and a purchase token — no product, no order id, no
    expiry — so it has to be exchanged for the truth over the Play Developer
    API, and Google's own documentation asks that a redelivered message not cost
    that call. Doing it before the check would spend quota on every retry;
    doing it after `_apply` would be applying an event with no product in it.
    """
    seen = await session.get(WebhookEvent, event.id)
    if seen is not None:
        return "already processed", False

    record = WebhookEvent(
        id=event.id, event_type=event.type, payload=payload, provider=event.provider
    )
    session.add(record)
    await session.flush()

    try:
        event = await adapter.enrich(event)
        outcome = await _apply(session, adapter, event, background)
        record.processed_at = utcnow()
        return outcome, True
    except Exception as exc:  # recorded, then re-raised so the provider retries
        record.error = str(exc)[:500]
        log.exception("failed to process %s", event.id)
        raise


# ── a purchase the app made, checked against the store that signed it ──────


@router.post("/iap/verify")
async def verify_store_purchase(
    user: CurrentUser,
    session: SessionDep,
    background: BackgroundTasks,
    platform: str = Body(embed=True),
    product: str = Body(embed=True),
    transaction: str = Body(embed=True),
) -> dict:
    """Verify one App Store or Play purchase and grant what it bought.

    **Why this exists at all**, when the seam already has a webhook: the store
    notification is not fast enough to be the thing a person waits for. StoreKit
    hands the app a signed transaction the instant the sheet closes; Apple's
    Server Notification for the same purchase arrives seconds or minutes later,
    and Google's is a Pub/Sub push with its own latency. In between, somebody
    who has paid is looking at a locked chapter. So the app tells us, and we
    check it against the store rather than believing it.

    **The adapter is chosen by the request, not by the configuration.** One
    backend answers an iOS app and an Android app at the same time, so
    `ALMA_BILLING_PROVIDER` — which decides who takes the money on the web, and
    which notification endpoint is live — cannot also decide this. A platform we
    do not ship, or one whose credentials are absent, is refused by name.

    **The owner is the caller.** Apple and Google echo nothing of ours: there is
    no `custom_data` to seal, and Google's `obfuscatedExternalAccountId` is set
    by the client, which makes it exactly the kind of field `provider.stamp`
    exists to distrust. What replaces the seal is stronger — the request carries
    our own session token, so the account is one we issued rather than one a
    processor relayed.

    **A replay grants nothing twice**, and it is the same mechanism the webhook
    uses: the event id is `"<platform>:<the store's own transaction id>"`, it
    goes through `_ingest`, and `webhook_event.id` is a primary key. A store
    *will* replay — StoreKit re-delivers unfinished transactions on every app
    launch, and a restore-purchases tap replays every transaction the Apple ID
    ever made. The second call answers `already_claimed` and writes nothing.

    That last sentence has a sharp edge worth stating: `already_claimed` also
    covers a transaction that belongs to *another* account. Two Alma accounts
    on one Apple ID — a guest on a reinstalled phone, say — race for the same
    purchase and the first one wins it. That is the safe direction (nothing is
    granted twice) and it is not the kind direction; the fix is account linking
    rather than a second grant, and it is in `open_problems`.
    """
    adapter = _store_adapter(platform)

    try:
        prices.product(product)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    try:
        event = await adapter.verify_purchase(transaction=transaction, product=product)
    except InvalidSignature as exc:
        # A forgery, or a real store signature over another app's purchase.
        # 401 rather than 400: this is a failed authentication of the document,
        # not a malformed request, and it is the line a log alert should watch.
        log.warning("rejected a %s purchase: %s", platform, exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={
            "error": "invalid_transaction", "message": str(exc), "platform": platform,
        }) from exc
    except ProductMismatch as exc:
        # The store equivalent of the price check. 409 rather than 400 because
        # the request is well formed and the *world* disagrees with it.
        log.warning("refused a %s purchase claiming %r: %s", platform, product, exc)
        raise HTTPException(status.HTTP_409_CONFLICT, detail={
            "error": "product_mismatch", "message": str(exc), "product": product,
        }) from exc
    except PurchaseIncomplete as exc:
        # Pending, refunded or revoked. Ordinary states with ordinary answers,
        # which is why they are not 401 — a Play cash payment is genuinely "not
        # yet", and the notification that settles it will grant.
        raise HTTPException(status.HTTP_409_CONFLICT, detail={
            "error": "purchase_incomplete", "message": str(exc), "product": product,
        }) from exc
    except BillingUnavailable as exc:
        # We could not ask. Never the buyer's fault and never a refusal: the
        # client should retry, and the store will send its notification anyway.
        log.error("could not verify a %s purchase: %s", platform, exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail={
            "error": "billing_unavailable", "message": str(exc),
        }) from exc

    # The one field the store cannot tell us. Everything else on this event came
    # out of a signature or an API call; this comes out of the session token.
    event = replace(event, owner_id=user.id)

    # Правило «продаём только то, что на полке», которое `/billing/checkout`
    # соблюдает и этот эндпоинт когда-то не соблюдал.
    #
    # Магазин продаст любой идентификатор, заведённый в консоли, любому, кто его
    # назовёт: клиентские фильтры (`Storefront.offers`, `StoreProducts.sellable`)
    # решают только, что **нарисовано**, и пересобранная сборка их не спрашивает.
    # Поэтому сервер спрашивает сам.
    #
    # **Проверяется слаг, который подписал магазин**, а не тот, что назвал
    # клиент: клиентский уже проверен в `verify_purchase`, и читать его тут
    # значит поверить запросу дважды.
    #
    # **Грант отзывается, деньги остаются** — два разных решения, и ранняя
    # версия этого блока смешивала их. Отказать в *платеже* нельзя: магазин уже
    # взял деньги, и 4xx здесь — это деньги ни за что и человек, спорящий с
    # Apple про наш дизайн идентификаторов. Поэтому событие всё равно
    # проглатывается, деньги записываются, transaction_id закрепляется за
    # аккаунтом, чтобы повтор не попробовал ещё раз.
    #
    # Снятие `grants` — самый узкий доступный рычаг: `entitlement_for` и так
    # отвечает `None` на негрантящее событие, так что второй копии правила о
    # scope здесь не появляется.
    #
    # Лекарство для того, кто честно заплатил, — магазинное и уже подключено:
    # в ответе `not_offered`, ни один клиент не видит ожидаемого гранта, значит
    # ни один не подтверждает (Android) и не финиширует (iOS) транзакцию, а
    # Google возвращает неподтверждённую покупку через три дня.
    honoured = await entitlements.may_be_offered(session, user, event.product)
    if not honoured:
        log.warning(
            "account %s claimed %r on %s, which is not a price on this shelf "
            "(transaction %s) — money recorded, grant refused",
            user.id, event.product, platform, event.transaction_id,
        )
        event = replace(event, grants=False)

    outcome, fresh = await _ingest(session, adapter, event, event.payload, background)
    if not fresh:
        log.info("%s transaction %s was claimed already", platform, event.transaction_id)

    held = await entitlements.for_user(session, user)
    granted = next(
        (row for row in held if row.transaction_id == event.transaction_id), None
    )
    return {
        # `not_offered` rather than the ingest outcome, so a client can tell
        # "we recorded your money and granted you nothing on purpose" apart from
        # "somebody else already claimed this transaction". Both leave the
        # purchase unacknowledged, which is what actually matters; they are
        # different sentences to put in front of a person.
        "status": ("not_offered" if not honoured else outcome) if fresh else "already_claimed",
        "platform": platform,
        "product": product,
        "transaction_id": event.transaction_id,
        "subscription_id": event.subscription_id,
        # What the client actually needs in order to unlock a screen: not the
        # outcome string, which is for logs, but the list the paywall reads.
        # Returned from the same request so the app never has to guess how long
        # to wait before re-fetching `/billing/entitlements`.
        "unlocked": sorted(await entitlements.unlocked_systems(session, user)),
        "expires_at": (
            as_utc(granted.expires_at).isoformat()
            if granted is not None and granted.expires_at
            else None
        ),
    }


def _store_adapter(platform: str) -> StoreProvider:
    """The adapter for a named store, or a refusal that says which one.

    Three separate refusals, because they send whoever is reading the log to
    three different places: a platform this build does not ship, a platform that
    is not a store at all (somebody POSTing `"paddle"` here), and a store whose
    credentials are missing from this deployment.
    """
    try:
        adapter = billing_adapter(platform)
    except BillingUnavailable as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"error": "unknown_platform", "message": str(exc), "platform": platform},
        ) from exc

    if not isinstance(adapter, StoreProvider):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "not_a_store",
                "message": f"{platform!r} is a payment processor, not an app store — "
                           "its purchases arrive as webhooks, not from a client",
                "platform": platform,
            },
        )

    missing = [
        name for name, value in settings().credentials_for(platform).items() if not value
    ]
    if missing:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "billing_unavailable",
                "message": f"{', '.join(missing)} are not set",
                "platform": platform,
            },
        )
    return adapter


async def _apply(
    session, adapter, event: NormalisedEvent, background: BackgroundTasks
) -> str:
    """Turn one verified event into a money record and, maybe, an entitlement.

    The adapter is handed down rather than looked up again, and that is not
    tidiness. `billing_adapter()` answers with whichever processor the *build*
    is configured for, and this function now runs for events that did not come
    from it: one backend serves an iOS app and an Android app while
    `ALMA_BILLING_PROVIDER` names one of them at most. Asking the configured
    adapter whether Apple sends its own receipts would have got Paddle's answer.

    Provider-neutral otherwise, and it has to be: every question this used to ask of
    Paddle's event-type strings — does this grant, does it revoke, did money
    move — has been answered by the adapter and arrives as a flag on the event.
    The `from ...billing.paddle import REVOKING` that used to sit here was the
    single line that made this function Paddle's.

    Two things here were wrong in ways that cost money in opposite directions,
    and both are about *finding the right row*.

    An adjustment — a refund, a credit, a chargeback — carries its own id and
    the transaction it reduces separately, and it carries none of our metadata
    at all. So the owner cannot be read off the event and has to be found from
    our own rows; and the adjustment must reduce the purchase it names rather
    than being inserted as a purchase of its own, which is a refund stored as a
    positive amount in the money trail.

    A subscription event names a subscription rather than a transaction, so a
    cancellation is matched on `subscription_id`. Matching on the transaction
    id caught only the row belonging to the charge it named, and every earlier
    renewal kept its future expiry — cancelled, and still granting.
    """
    purchase = await _record_money(session, event)
    paid = purchase is not None

    user = await session.get(User, event.owner_id) if event.owner_id else None
    if user is None:
        # An adjustment and a cancellation both arrive without `custom_data` —
        # we only set that when *we* open a checkout, and neither of those is
        # something we opened. So the owner is whoever holds the thing being
        # undone: the purchase being reduced, or the entitlement the
        # subscription granted. Without this the handler answered "recorded
        # without an owner" and never reached the revocation below, so the
        # money went back and the goods stayed.
        user = await _owner_of(session, event, purchase)

    if user is None:
        # A payment we cannot attach to anyone is kept, not dropped: support
        # can attach it by hand, and losing the record would lose the money.
        return "recorded without an owner"

    # Whose delivery this was, written onto the stored copy. The payload is kept
    # verbatim because that is what support reads at two in the morning, and on
    # both processors it carries the buyer's name, address and country — so
    # without this column an erasure request has no way to find these rows, and
    # "when you delete it, it goes" would have an undisclosed exception behind
    # it. Written here rather than at insert because *here* is where the owner
    # is known, including for the refunds and chargebacks that arrive carrying
    # nothing we set.
    stored = await session.get(WebhookEvent, event.id)
    if stored is not None:
        stored.user_id = user.id

    # A payment, and only a payment. It sits above the grant rather than inside
    # it because on one of the two processors the money and the entitlement
    # arrive as separate events on purpose — see `_confirm_the_purchase`.
    if paid and event.kind is EventKind.PAYMENT:
        await _confirm_the_purchase(session, adapter, event, user, purchase, background)

    granted = entitlement_for(event) or await _the_plan_we_already_hold(session, event, user)
    if granted is not None:
        await entitlements.grant(
            session,
            user,
            system=granted.system,
            kind=granted.kind,
            scope=granted.scope,
            # Only when there was a transaction. On a `subscription.*` event
            # `data.id` is the plan, not a payment, and storing that as a
            # transaction id makes the two columns mean the same thing on the
            # rows where telling them apart matters most.
            transaction_id=event.transaction_id if paid else None,
            subscription_id=granted.subscription_id,
            status=event.status,
            # When the plan bills again, as the processor stated it. Written so
            # the account screen can say "renews on the 4th" from the same row
            # the paywall reads, rather than from an expiry that means
            # something else — between a cancellation and the end of a paid
            # period those two dates disagree, and that gap is the whole
            # difference between cancelling and refunding.
            renews_at=event.renews_at,
            amount_cents=event.amount_cents,
            currency=event.currency,
            duration=granted.duration,
            # Which processor's money this was. It defaulted to "paddle" on the
            # column, so every Dodo grant would have claimed to be a Paddle one
            # — and the day somebody reconciles a month of revenue against two
            # processors, that column is the only thing telling them apart.
            source=event.provider,
        )
        return f"granted {granted.system}"

    if event.revokes:
        return f"revoked {await _revoke_for(session, event, user)}"

    if event.subscription_id and event.kind in PLAN_NEWS:
        return f"noted {await _note_the_plan(session, event, user)}"

    return "ignored"


#: The subscription-lifecycle events that change nothing about access and
#: everything about what we should be *saying*. None of them revokes: a
#: cancellation runs to the end of the period already paid for, dunning is a
#: retry, and a pause stops billing rather than sending money back. But all
#: three make "renews on the 4th" a false sentence on the account screen, and a
#: person who has just cancelled and is told their plan renews reads that as the
#: cancellation having failed — the next thing they do is a chargeback.
PLAN_NEWS = frozenset({
    EventKind.SUBSCRIPTION_CANCELLED,
    EventKind.SUBSCRIPTION_PAUSED,
    EventKind.SUBSCRIPTION_UPDATED,
    EventKind.SUBSCRIPTION_DUNNING,
})


async def _note_the_plan(session, event: NormalisedEvent, user) -> int:
    """Record what a plan event says, without touching what it grants.

    `expires_at` is never moved here, and that is the whole rule: the period has
    been paid for and it runs out on its own. What is written is the processor's
    status word — recorded for support and never read by the paywall — and
    `renews_at`, which is a promise to charge and is exactly what a cancellation
    withdraws.

    `renews_at` is cleared rather than merely left alone on a cancellation
    because the alternative is the account screen going on promising a charge
    that will not happen. It is *set* on an update only when the event carries a
    date, so a reconciliation that says nothing about billing cannot erase one.
    """
    noted = 0
    for held in await entitlements.for_user(session, user):
        if held.subscription_id != event.subscription_id:
            continue
        if event.status:
            held.status = event.status
        if event.kind is EventKind.SUBSCRIPTION_CANCELLED:
            held.renews_at = None
        elif event.renews_at is not None:
            held.renews_at = event.renews_at
        noted += 1
    if noted:
        await session.flush()
    return noted


async def _the_plan_we_already_hold(session, event: NormalisedEvent, user) -> Grant | None:
    """A renewal for a subscription we hold, when the event does not name a product.

    **A renewal must not depend on metadata.** The processor echoes our sealed
    blob onto every event for the life of a plan, which is convenient and is not
    something to build a recurring charge on: the seal is keyed on
    `ALMA_JWT_SECRET`, so rotating that secret — a thing an operator does after
    an incident, without thinking about billing — would leave every live
    subscription renewing into nothing. Silently. The plan would go on being
    charged and stop being extended, and the first person to notice would be a
    subscriber who had paid.

    So the plan a subscription renews into is the plan it already holds. The row
    is found by the subscription id the processor sent — an identifier we did
    not write and the browser cannot choose — and its `kind` names the catalogue
    row, which is then put through the same `entitlement_for` as everything
    else, price check included. There is no second copy of the rule here; there
    is only a second way of answering "which product is this".
    """
    if not event.grants or not event.subscription_id or event.product:
        return None

    for held in await entitlements.for_user(session, user):
        if held.subscription_id != event.subscription_id:
            continue
        key = _recurring_key(held.kind)
        return entitlement_for(replace(event, product=key)) if key else None
    return None


def _recurring_key(kind: str) -> str | None:
    """The catalogue key of the one recurring product sold under this kind.

    A lookup rather than a stored column, because `Entitlement` records what a
    grant *is* — system, kind, scope — and not which price list row produced it.
    Exactly one product carries each recurring kind, which is what makes this
    answerable at all; the day two do, this has to become a column.
    """
    for key, item in prices.PRODUCTS.items():
        if item.interval and item.kind == kind:
            return key
    return None


# ── the receipt, which is the third leg of a lawful waiver ─────────────────


async def _confirm_the_purchase(
    session, adapter, event: NormalisedEvent, user, purchase, background: BackgroundTasks
) -> None:
    """Queue the written confirmation of one payment, or say why there is none.

    **This is not a courtesy email.** CRD Art. 16(m) takes the 14-day
    withdrawal right away from a buyer of digital content only when three
    things have happened: prior express consent, an acknowledgement that the
    right is lost, and confirmation of the contract on a durable medium
    (Art. 8(7)). The checkout can produce the first two; only this produces the
    third. Without it the waiver is void in four of our six locales and in the
    UK, and somebody can read the whole archive and still withdraw.

    **It follows the money, not the grant**, and that is a decision about the
    seam rather than about the law. On Paddle a purchase and its grant are one
    `transaction.completed`; on Dodo they are two events on purpose — the
    payment records the money and the `subscription.*` event writes the grant,
    because letting both grant would extend a plan twice for one month's money.
    Hanging the receipt on the granting event would therefore have sent nothing
    at all for a Dodo subscription, and hanging it on both would send two. The
    payment is the one event that happens exactly once per charge on both
    processors, and it is also the only one that carries an amount: a receipt
    written off a subscription event would state a total of zero.

    Nothing here raises. A grant is the customer's the moment the processor
    says the money moved, and an unsent email is a far smaller harm than a
    refused delivery — which the processor retries, and a retried delivery is
    how one payment becomes two grants.
    """
    if adapter.issues_the_receipt:
        # A store sale. Apple and Google are the merchant of record — they
        # charged the card, they appear on the statement, and they email the
        # confirmation — so the durable-medium leg of the waiver is theirs and
        # not a thing we are failing to do. Returning before the address lookup
        # matters more than it looks: without this, every store purchase would
        # log "the withdrawal waiver behind it is not complete" at `error`, and
        # a real alarm that fires on every sale is an alarm nobody reads.
        log.debug(
            "no receipt from us for %s: %s is the merchant of record",
            event.transaction_id, event.provider,
        )
        return

    product = await _what_was_bought(session, event, user)
    address = await _where_to_write(adapter, event, user)

    if not address:
        # Nobody to write to, from either side. The account has no address and
        # the processor would not give us the one it collected — a key that is
        # not set, a customer it will not talk about, a network that is down.
        # Logged at `error` rather than swallowed, because the consequence is
        # not "no email": it is that this buyer's withdrawal waiver was never
        # completed and they keep the 14-day right whatever they ticked.
        log.error(
            "no address for %s — %s bought %r for %s %s with no receipt sent, so "
            "the withdrawal waiver behind it is not complete",
            user.id, event.provider, product, event.amount_cents, event.currency,
        )
        return

    if not product:
        # A receipt that cannot say what was bought is not a confirmation of a
        # contract, and sending a half one would look like the requirement had
        # been met. This is a payment we could not match to a catalogue row —
        # a support checkout, or a plan whose payment event reached us before
        # the subscription event that names it.
        log.error(
            "payment %s for %s names no product we sell — no receipt sent",
            event.transaction_id, user.id,
        )
        return

    item = prices.PRODUCTS[product]
    ticked = await _claim_consent(session, user=user, product=product, event=event)
    background.add_task(
        _deliver_receipt,
        mail.Receipt(
            email=address,
            locale=user.locale or "en",
            product=product,
            # The processor's own total, tax included, which is the number that
            # will appear on the buyer's statement. Never the catalogue's price:
            # a US buyer is charged sales tax on top of it, and a receipt that
            # disagrees with a statement is a receipt somebody disputes.
            amount_cents=event.amount_cents,
            currency=event.currency,
            paid_at=as_utc(purchase.completed_at) or utcnow(),
            # Who legally sold this, asked of the adapter that just verified the
            # delivery rather than written down anywhere: the merchant of record
            # changes with `ALMA_BILLING_PROVIDER`, and a receipt naming the
            # wrong seller is what a card issuer reads during a dispute.
            merchant=adapter.merchant,
            reference=event.transaction_id or "",
            # Whether this renews decides which withdrawal paragraph is true.
            # Art. 16(a) does not extinguish the right on a twelve-month plan
            # until the service is fully performed, so the annual cannot hide
            # behind the same waiver as a chapter delivered in one second. The
            # catalogue's `interval` is what answers that, for the same reason
            # `entitlement_for` reads it: a hand-written list of recurring kinds
            # is what once let a monthly write a permanent everything-grant.
            recurring=bool(item.interval),
            # What the buyer actually ticked, or nothing. The receipt prints the
            # "what you ticked at the checkout" block only when this is filled,
            # and quotes these sentences rather than a template — because a
            # letter asserting two boxes that were never on somebody's screen is
            # a fabricated record of consent, sent by us, on the durable medium
            # whose whole purpose is to be evidence.
            consent=ticked,
        ),
    )


async def _where_to_write(adapter, event: NormalisedEvent, user) -> str:
    """The address this receipt goes to: ours first, then the processor's.

    **The account's own address wins**, because the contract is with the
    account and that is the inbox a person will look in. The processor's copy
    is the answer for the guest funnel, which is most of this product's buyers
    by design: a guest is a real row with a real entitlement and no address of
    ours at all, so without this every guest purchase went unconfirmed and every
    guest waiver stayed incomplete.

    The processor is asked rather than trusted to have volunteered: Dodo puts
    the customer in the body, Paddle sends a customer id and has to be called.
    That difference lives in the adapter. Any failure of it answers `None` and
    ends as a log line, never as an exception — a receipt is not worth failing
    a webhook over, because a failed webhook is retried and a retried webhook is
    how one payment becomes two grants.
    """
    mine = (user.email or "").strip()
    if mine:
        return mine
    try:
        theirs = await adapter.buyer_address(event)
    except Exception:  # noqa: BLE001 - a processor may fail in any way it likes
        log.exception("could not ask %s for a buyer's address", event.provider)
        return ""
    return (theirs or "").strip()


async def _claim_consent(session, *, user, product: str, event: NormalisedEvent):
    """The consent this payment is the other half of, marked as claimed.

    Matched on (account, product) and not on a transaction id, because at the
    moment of consent there is no transaction — the processor invents that a few
    seconds later, on the other side of a browser. The newest unclaimed row
    wins: somebody who opened a checkout, closed it, and opened another one
    agreed twice, and the agreement that belongs to the money is the one they
    were reading when they paid.

    A renewal finds nothing, and that is correct rather than a gap. The consent
    was given once, when the plan was bought; the second year's charge is not a
    second contract, and a receipt that quoted last year's ticked boxes as
    though they were ticked this morning would be dating a record wrongly. What
    a renewal receipt says about withdrawal comes from the plan paragraph, which
    does not depend on a waiver at all — Art. 16(a) does not extinguish the
    right on a twelve-month service until it is fully performed.
    """
    row = (
        await session.execute(
            select(Consent)
            .where(
                Consent.user_id == user.id,
                Consent.product == product,
                Consent.transaction_id.is_(None),
            )
            .order_by(Consent.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if row is None:
        return None

    row.transaction_id = event.transaction_id or None
    await session.flush()
    return tuple(
        (str(item.get("key") or ""), str(item.get("text") or ""))
        for item in (row.statements or [])
        if item.get("text")
    ) or None


async def _what_was_bought(session, event: NormalisedEvent, user) -> str | None:
    """The catalogue key this payment paid for, from the event or from our rows.

    A renewal does not always name a product — the metadata a processor echoes
    is not something a recurring charge may depend on, since the seal is keyed
    on `ALMA_JWT_SECRET` and an operator may rotate that — so the plan a
    renewal pays for is the plan the subscription already holds. Exactly the
    reasoning in `_the_plan_we_already_hold`, asked here of a payment event
    that does not itself grant.
    """
    if event.product in prices.PRODUCTS:
        return event.product
    if not event.subscription_id:
        return None
    for held in await entitlements.for_user(session, user):
        if held.subscription_id == event.subscription_id:
            return _recurring_key(held.kind)
    return None


async def _deliver_receipt(receipt: mail.Receipt) -> None:
    """Put the letter in the post, after the webhook has been answered.

    Every failure ends here. The entitlement has already been written and
    committed; nothing this does can take it back, and nothing it raises may
    escape into the server's error handling and be mistaken for a failed
    delivery. What a failure costs is a receipt, and what it is worth saying
    about is exactly one log line loud enough to find — because a run of these
    means the ladder is selling without the third leg of its waiver.
    """
    try:
        if not await mail.send_receipt(receipt):
            log.error(
                "receipt not delivered for %s (%s) — the withdrawal waiver behind "
                "it is not complete",
                receipt.reference, receipt.product,
            )
    except Exception:  # noqa: BLE001 - a mail provider may fail in any way it likes
        log.exception("receipt for %s could not be sent", receipt.reference)


async def _owner_of(session, event: NormalisedEvent, purchase) -> User | None:
    """Who an event carrying none of our metadata belongs to, from our own rows.

    Every processor has events like this: a refund issued from a dashboard, a
    chargeback opened by a bank, a dunning retry. We only ever attach an owner
    to a checkout *we* opened, so for these the owner has to be recovered from
    what they undo — the purchase being reduced, or the entitlement the
    subscription granted.
    """
    if purchase is not None and purchase.user_id:
        return await session.get(User, purchase.user_id)
    if event.subscription_id:
        held = (
            await session.execute(
                select(Entitlement).where(
                    Entitlement.subscription_id == event.subscription_id
                )
            )
        ).scalars().first()
        if held is not None:
            return await session.get(User, held.user_id)
    return None


async def _record_money(session, event: NormalisedEvent) -> Purchase | None:
    """Write what actually moved. One row per transaction, ever.

    `moves_money` is the adapter's answer, not a prefix match on an event type
    the way this used to be: a subscription-lifecycle event carries a plan id
    and no payment at all, and recording one as a purchase wrote a zero-amount
    row whose "transaction id" had never identified money. Which of one
    processor's event families mean that is the adapter's problem — Paddle
    spells them `transaction.` and `adjustment.`, Dodo spells them `payment.`,
    and neither spelling belongs in this file.

    The transaction id is required alongside it because `Purchase.transaction_id`
    is the unique key of the money trail; a money event without one has nothing
    to write a row against and nothing to find it by later.
    """
    if not event.moves_money or not event.transaction_id:
        return None

    purchase = (
        await session.execute(
            select(Purchase).where(Purchase.transaction_id == event.transaction_id)
        )
    ).scalar_one_or_none()

    adjustment = event.adjustment
    if purchase is None:
        if adjustment is not None:
            # An adjustment against a transaction we never recorded. Kept as a
            # row so the money is not lost, but it is not a sale: recording it
            # as one is how a refund ends up counted as revenue.
            purchase = Purchase(
                provider=event.provider,
                transaction_id=event.transaction_id,
                product=None,
                amount_cents=0,
                currency=event.currency,
                country=event.country,
                payload=event.payload,
            )
        else:
            purchase = Purchase(
                provider=event.provider,
                transaction_id=event.transaction_id,
                user_id=event.owner_id,
                product=event.product,
                amount_cents=event.amount_cents,
                currency=event.currency,
                country=event.country,
                payload=event.payload,
            )
        session.add(purchase)

    if adjustment is not None:
        action, _kind = adjustment
        if event.returns_money:
            purchase.refunded_cents = (purchase.refunded_cents or 0) + event.amount_cents
            # `refunded_at` means "all of it came back", so a partial refund
            # leaves it unset: the purchase is still a purchase and what it
            # bought is still owed. `closes_the_grant` asks the same question
            # the revocation below asks — a full return — so the money trail and
            # the entitlement cannot end up disagreeing about one refund.
            if event.closes_the_grant or purchase.refunded_cents >= (purchase.amount_cents or 0) > 0:
                purchase.refunded_at = utcnow()
        # The status names the adjustment either way, so support can see which
        # of the shapes arrived rather than inferring it from an amount.
        purchase.status = f"{event.type}:{action}"
        return purchase

    purchase.status = event.type
    if event.kind is EventKind.PAYMENT:
        purchase.completed_at = utcnow()
        if event.subscription_id:
            purchase.subscription_id = event.subscription_id
        # Kept on the money row so that the next thing we owe this buyer — the
        # warning three days before the renewal — has somewhere to go. A guest
        # has no address of ours, and `renewals.due` used to skip them silently:
        # the promise printed loudest beside the pay button was least true for
        # the person reading it there. Never written to `User.email`; see the
        # column's own note.
        if event.buyer_email:
            purchase.buyer_email = event.buyer_email
    elif event.kind is EventKind.ADJUSTMENT:
        # A return that arrived as its own event rather than as an adjustment
        # record — Paddle's `transaction.refunded`. There is no action/type pair
        # to read, and the event exists only because the whole charge came back.
        purchase.refunded_cents = purchase.amount_cents
        purchase.refunded_at = utcnow()
    return purchase


async def _revoke_for(session, event: NormalisedEvent, user) -> int:
    """Close what this event undoes, and only that.

    Somebody refunded five dollars of a thirty-nine dollar archive keeps the
    archive — the alternative is taking away a reading they have read, over
    money we chose to give back. The code ignored the shape of the adjustment
    altogether, so it could tell none of these apart; `closes_the_grant` is that
    distinction, and it lives on the event because each processor spells the
    three meanings of returned money differently while meaning the same three.
    """
    if not event.closes_the_grant:
        return 0

    revoked = 0
    for held in await entitlements.for_user(session, user):
        matches_subscription = bool(
            event.subscription_id and held.subscription_id == event.subscription_id
        )
        matches_transaction = bool(
            event.transaction_id and held.transaction_id == event.transaction_id
        )
        if matches_subscription or matches_transaction:
            await entitlements.revoke(session, held)
            revoked += 1
    return revoked


# ── cancelling, which is not refunding ─────────────────────────────────────


@router.post("/subscription/cancel")
async def cancel_subscription(user: CurrentUser, session: SessionDep) -> dict:
    """Stop the next charge, and leave everything already paid for alone.

    Three shipped surfaces promised this endpoint before it existed — the
    settings screen, the subscription-terms page ("cancelling takes two taps")
    and the FAQ — and two laws now require it. California AB 2863 requires
    cancellation in the same medium the subscription was entered into for
    contracts formed on or after 1 July 2025, and the EU's withdrawal-function
    requirement took effect on 19 June 2026. "The link is in your receipt
    email" is not the same medium.

    **The entitlement is not revoked, and that is the whole rule.** A person
    who cancels a year in month two has paid for ten more months and keeps
    them; taking access away at the moment of cancelling is a refund we never
    agreed to give, arriving as a punishment for leaving. So `expires_at` is
    untouched and only `renews_at` — the promise to charge — is cleared. What
    comes back is the date access actually ends, which is the sentence the
    interface has to be able to say: *your year runs to the 4th of March.*

    The processor is called first and our own row is written only after it
    answers. The other order reads better and is a lie: a local flag saying
    "cancelled" does not stop a card being charged, and the person finds out on
    a statement.
    """
    recurring = entitlements.subscription_kinds()
    plans = [
        held
        for held in await entitlements.for_user(session, user)
        if held.subscription_id
        and held.kind in recurring
        and entitlements.is_in_force(held)
    ]
    if not plans:
        # Not an error worth logging and not a 500. Somebody who has never
        # subscribed, or whose plan has already run out, pressing a button the
        # interface should not have shown them.
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "error": "no_subscription",
                "message": "this account has no subscription to cancel",
            },
        )

    config = settings()
    if not config.billing_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "billing_unavailable",
                "message": f"{', '.join(config.missing_billing_credentials())} are not set",
            },
        )

    adapter = billing_adapter()
    cancelled: list[str] = []
    ends: list[datetime] = []
    for plan in plans:
        if plan.subscription_id in cancelled:
            # Two grants against one subscription should not exist — `grant()`
            # extends one row — but if they ever do, the processor is told once.
            continue
        try:
            await adapter.cancel_subscription(plan.subscription_id)
        except SelfServiceOnly as exc:
            # A store. Neither Apple nor Google will let a server cancel a
            # subscription that belongs to an Apple ID or a Google account, so
            # the honest answer is the door rather than an apology — and this
            # runs before the `BillingUnavailable` clause on purpose, because
            # `SelfServiceOnly` is a subclass of it and the wider one would
            # otherwise turn "here is where to cancel" into "we could not reach
            # the payment processor".
            #
            # 409 rather than 502: nothing failed. Nothing is written either,
            # which is the important half — writing `renews_at = None` here
            # would tell the account screen the plan had stopped renewing while
            # it went on renewing, and the person would find out on a statement.
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={
                    "error": "cancel_at_store",
                    "message": str(exc),
                    "provider": adapter.name,
                    # The one field the client cannot compute. An app that says
                    # "cancel in Settings" without opening Settings is an app
                    # that fails review under the guideline requiring a
                    # subscription-management link.
                    "manage_url": exc.manage_url,
                },
            ) from exc
        except BillingUnavailable as exc:
            # Loudly, and without writing anything: a cancellation the customer
            # believes happened and the processor never heard of is the failure
            # that ends in a chargeback and a complaint to a regulator.
            #
            # Raising rolls the whole request back, including any plan already
            # cancelled in this loop — that one is stopped at the processor
            # while our copy still says it renews, until the processor's own
            # webhook arrives. It takes two live plans on one account to reach
            # that, which the catalogue does not sell today; the day it does,
            # this has to report an outcome per plan instead of raising.
            log.error("%s refused to cancel %s: %s", adapter.name, plan.subscription_id, exc)
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": "cancel_failed",
                    "message": (
                        "we could not reach the payment processor to cancel this "
                        "subscription — nothing has been changed, please try again"
                    ),
                },
            ) from exc

        # Written only now, and only these two fields. `status` is recorded for
        # support and never read by the paywall — the day a processor renames
        # one of its status strings must not be the day everybody who has paid
        # is locked out — so our own word in it is safe. `renews_at` is cleared
        # because the promise to charge is what was just withdrawn.
        plan.renews_at = None
        plan.status = "cancelled"
        cancelled.append(plan.subscription_id)
        if plan.expires_at is not None:
            ends.append(as_utc(plan.expires_at))
    await session.flush()

    access_until = max(ends) if ends else None
    return {
        "cancelled": True,
        "provider": adapter.name,
        "subscription_ids": cancelled,
        # The date the reading stops opening — the sentence the interface has
        # to be able to say. `None` would mean a plan with no expiry, which
        # `grant()` refuses to write for a recurring kind, so in practice this
        # is always a date.
        "access_until": access_until.isoformat() if access_until else None,
        "renews_at": None,
    }


# ── the single downsell ────────────────────────────────────────────────────

DOWNSELL_KEY = "downsell_offered"


@router.post("/declined")
async def declined(
    user: CurrentUser,
    session: SessionDep,
    edge: EdgeCountry,
    system: str | None = Body(default=None, embed=True),
    country: str | None = Body(default=None, embed=True),
) -> dict:
    """Called when someone closes the checkout without buying.

    Offers a cheaper option exactly once, ever. The second nudge is what turns
    someone who was still thinking about it into someone who has decided, so
    the counter is stored rather than kept in the client where a refresh would
    reset it.

    What is offered is the door for the system they were looking at, priced in
    their own currency. Both halves were wrong. It used to be
    `min(PRODUCTS, key=cents)` over everything but the annual, and since the
    eight doors are now one price that resolved to whichever came first in the
    dict literal — so a person who declined a compatibility reading was offered
    a natal chart, at the same price they had just refused, by an accident of
    insertion order. And it read `item.cents` and `display()`, which are the US
    figures, so a German was quoted $8.99 for a €9.49 door and a Brazilian was
    offered a product that does not exist in reais at all.
    """
    from ...db.models import UsageCounter

    key = f"{user.id}:downsell"
    row = await session.get(UsageCounter, key)
    if row is not None and (row.count or 0) > 0:
        return {"offer": None, "reason": "already offered once"}

    currency = prices.currency_for(region.resolve(stated=country, edge=edge))
    offer = _downsell(system, currency)
    if offer is None:
        # Nothing smaller is sold here. Saying so costs nothing and, crucially,
        # does not burn the one offer this person will ever get.
        return {"offer": None, "reason": "nothing smaller is sold in this market"}

    if row is None:
        row = UsageCounter(
            id=key, user_id=user.id, day=utcnow().date(),
            metric=DOWNSELL_KEY, count=0, amount=0.0,
        )
        session.add(row)
    row.count = (row.count or 0) + 1
    await session.flush()

    return {"offer": offer, "reason": "one smaller thing, once"}


def _downsell(system: str | None, currency: str) -> dict | None:
    """The cheapest thing we can honestly offer this person here.

    The door for what they declined, if we sell it in their currency;
    otherwise the cheapest one-time price that is sold there. `None` when
    nothing qualifies.

    **Сравнивается `item.slug`, а не ключ каталога.** До v3 они совпадали, и
    строка читалась как «дверь той системы, от которой отказались»; с ключами
    вида `door.natal` то же сравнение молча перестало совпадать хоть с чем-то, и
    человеку, отказавшемуся от нумерологии, предлагали бы первую строку словаря.

    `pair.check` исключён намеренно: чтобы предложить проверку пары, нужен
    партнёр, а здесь неизвестно, есть ли он вообще. Предложить $4.99 «проверить
    вас двоих» тому, кто только что закрыл разбор про себя, — это оффер, который
    он не может принять.
    """
    candidates = [
        (key, item)
        for key, item in prices.PRODUCTS.items()
        if item.on_the_shelf
        and item.sold_in(currency)
        and not item.interval
        and item.scope != entitlements.SCOPE_PAIR
    ]
    if not candidates:
        return None

    key, item = min(
        candidates,
        key=lambda pair: (pair[1].slug != system, pair[1].cents_in(currency)),
    )
    return {
        "slug": key,
        "system": item.slug,
        "name": item.name,
        "currency": currency,
        "cents": item.cents_in(currency),
        "display": item.display(currency),
    }


@router.get("/entitlements")
async def held(
    user: CurrentUser, session: SessionDep, edge: EdgeCountry, country: str | None = None
) -> dict:
    currency = prices.currency_for(region.resolve(stated=country, edge=edge))
    rows = await entitlements.for_user(session, user)
    return {
        "unlocked": sorted(await entitlements.unlocked_systems(session, user)),
        # Пары отдельным списком, а не строкой в `unlocked`: там — «какие
        # системы открыты», здесь — «про кого уже написано». Слить их значит
        # сказать хабу «совместимость открыта», то есть про всех, тогда как
        # оплачены конкретные люди.
        "unlocked_pairs": sorted(await entitlements.unlocked_pairs(session, user)),
        "entitlements": [
            {
                "system": e.system,
                "kind": e.kind,
                "scope": e.scope,
                # Through `as_utc`, because SQLite hands back naive values even
                # from a timezone-aware column and a naive ISO string is read by
                # every browser as *local* time. These three are printed on the
                # account screen — "your plan runs to the 4th" — so a reader far
                # enough east or west was shown the wrong day, and the one that
                # matters most is the date somebody checks before cancelling.
                "granted_at": as_utc(e.granted_at).isoformat(),
                "expires_at": as_utc(e.expires_at).isoformat() if e.expires_at else None,
                "renews_at": as_utc(e.renews_at).isoformat() if e.renews_at else None,
                # The question this field asks is "is this grant still in
                # force", and that is what it now calls. It used to be
                # `e.covers(e.system)`, which probes *coverage* using the row's
                # own system column as a slug — and a live subscription's column
                # holds "*", which is not a living system. A paying subscriber
                # was told their subscription was inactive, on the screen a
                # person opens when they are already wondering whether to keep
                # paying for it.
                "active": entitlements.is_in_force(e),
                # Who sold it. Published because the account screen has to say
                # two different true things about a renewal depending on the
                # answer: a plan bought through the App Store is one Apple
                # charges, Apple receipts and Apple warns about, and a plan
                # bought on the web with a card is one *we* do all three for.
                # The iOS client was choosing between those two sentences on
                # whether the account happened to have an email address, which
                # is not the same question — so a store subscriber with an
                # address was told "we email you 3 days before", which we
                # neither do nor can.
                "source": e.source,
            }
            for e in rows
        ],
        "currency": currency,
        # `annual_credit_cents` ушло вместе с кредитными доборами (v3, ТЗ §2).
        # Клиенты читают его как необязательное поле с нулём по умолчанию, так
        # что отсутствие ключа для них — то же самое, что ноль, который они
        # получали последние недели.
    }
