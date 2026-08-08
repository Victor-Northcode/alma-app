"""The receipt — the leg of the withdrawal waiver that had no code.

CRD Art. 16(m) takes the 14-day right of withdrawal away from a buyer of
digital content only when three things have happened: prior express consent,
an acknowledgement that the right is lost, and confirmation of the contract on
a **durable medium**. A checkout can produce the first two. Only an email
produces the third, and without it the waiver is void in four of our six
locales and in the UK — which means somebody can read the whole archive, ask
for their money back on day thirteen, and be right.

So these tests are not about wording, and they are deliberately not about
whether an email is pretty. They ask the four questions the law and the money
ask: does every locale get every element a confirmation must contain, is a
retried delivery still one letter, does a mail provider having a bad afternoon
ever cost somebody the thing they paid for, and what exactly does a guest with
no address end up with.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import time
from datetime import datetime, timezone

import pytest
from conftest import read_async

from alma import mail
from alma.billing.catalogue import PRODUCTS
from alma.billing.provider import stamp

SECRET = "pdl_ntfset_test_secret"

#: The six the product ships. Taken from the sign-in link's own table rather
#: than written out again: a message that reaches five of the six languages the
#: other messages reach is a message somebody forgot to finish.
LOCALES = set(mail.SUBJECTS)


# ══════════════════════════════════════════════════════════════════════════
#  The letter itself
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def outbox(monkeypatch) -> list[dict]:
    """A configured mail provider that posts nothing anywhere."""
    from alma import config as config_module

    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    config_module.settings.cache_clear()

    sent: list[dict] = []

    async def capture(payload: dict) -> bool:
        sent.append(payload)
        return True

    monkeypatch.setattr(mail, "_post", capture)
    yield sent
    config_module.settings.cache_clear()


#: A consent as it comes back off the `consent` table: the sentences the buyer
#: was actually shown, in the order they were shown them. Deliberately *not*
#: any sentence `mail.py` itself holds — the whole rule being tested is that the
#: letter quotes what was recorded rather than what any dictionary happens to say
#: today, and a fixture borrowed from the copy table could not tell the two apart.
TICKED = (
    ("immediate_access", "Write it now — I'm not waiting out my 14 days."),
    ("withdrawal_waived", "I understand that once it's written, that right is gone."),
)


def _receipt(**changed) -> mail.Receipt:
    fields = {
        "email": "sofia@example.com",
        "locale": "en",
        "product": "natal",
        "amount_cents": 899,
        "currency": "USD",
        "paid_at": datetime(2026, 8, 6, 11, 30, tzinfo=timezone.utc),
        "merchant": "Paddle.com Market Ltd",
        "reference": "txn_01hz",
        "recurring": False,
        "consent": TICKED,
    }
    fields.update(changed)
    return mail.Receipt(**fields)


def _letter(outbox: list[dict], receipt: mail.Receipt) -> dict:
    assert asyncio.run(mail.send_receipt(receipt)) is True
    return outbox[-1]


@pytest.mark.parametrize("locale", sorted(LOCALES))
def test_every_locale_gets_every_element_a_confirmation_must_contain(outbox, locale):
    """The six things Art. 16(m) plus Art. 8(7) require, in the buyer's language.

    What was bought, what was paid, when, who sold it, the consent that was
    given, and where the money comes back from. A receipt missing any one of
    them is not a confirmation of a contract, and a waiver resting on it is a
    waiver a buyer can set aside.
    """
    letter = _letter(outbox, _receipt(locale=locale, product="archive", amount_cents=3899))
    body = letter["html"]
    name = mail.RECEIPT_PRODUCTS[locale]["archive"]
    copy = mail.RECEIPT_COPY[locale]

    assert letter["to"] == ["sofia@example.com"]
    assert name in letter["subject"], "the subject does not say what was bought"
    assert name in body                                  # what
    assert "$38.99" in body                              # what was paid...
    assert copy.tax_note in body                         # ...including tax
    assert mail.written_date(                            # when, in their language
        datetime(2026, 8, 6, tzinfo=timezone.utc), locale
    ) in body
    assert "Paddle.com Market Ltd" in body               # who sold it
    assert "txn_01hz" in body                            # which payment
    assert copy.consent in body                          # the consent given
    assert "/refunds" in body                            # and how to undo it


@pytest.mark.parametrize("locale", sorted(LOCALES))
def test_the_date_is_written_and_not_printed(outbox, locale):
    """`2026-08-06` in the middle of a sentence is a letter nobody wrote.

    The date sits inside running prose in all six languages — "Du hast am … für
    … bezahlt" — so an ISO string there is the one place these letters read as
    machine output, in the document we ask people to keep.
    """
    body = _letter(outbox, _receipt(locale=locale))["html"]
    assert "2026-08-06" not in body
    assert "2026" in body and "6" in body


@pytest.mark.parametrize("locale", sorted(LOCALES))
def test_a_year_is_not_told_the_same_story_as_a_reading(outbox, locale):
    """Art. 16(a) does not extinguish withdrawal on a twelve-month plan.

    A chapter is fully performed the second it is written; a year is not
    performed until the year is over, so the waiver that closes the first
    cannot close the second. A buyer who withdraws from the annual on day ten
    is owed a pro-rata refund under Art. 14(3), and this is the letter that has
    to tell them so — in the same language, without them having to ask.
    """
    plan = _letter(outbox, _receipt(locale=locale, product="annual",
                                    amount_cents=7899, recurring=True))["html"]
    once = _letter(outbox, _receipt(locale=locale))["html"]
    copy = mail.RECEIPT_COPY[locale]

    assert copy.consent_plan in plan
    assert copy.consent not in plan, "a plan was sold the one-time waiver"
    assert copy.consent in once
    assert copy.consent_plan not in once

    # ...and the plan is the only one that says how to stop the next charge.
    # California AB 2863 and the EU's withdrawal-function requirement both want
    # that in the medium the contract was made in, which is why the letter
    # points at the app rather than at a reply-to address.
    assert copy.cancel in plan
    assert copy.cancel not in once, "a permanent purchase was told how to cancel"
    # The button that says "manage your plan" has to land on the screen with the
    # cancel button on it. It used to point at `/?plan=1`, which nothing reads —
    # so a subscriber trying to stop a charge arrived on the marketing landing.
    assert mail.RECEIPT_PLAN_PATH in plan


@pytest.mark.parametrize("locale", sorted(LOCALES))
def test_the_letter_repeats_the_lines_that_were_actually_ticked(outbox, locale):
    """Art. 16(m) asks for the *consent* to be confirmed, not summarised.

    And the checkout says so in its own fine print — "the receipt in your inbox
    repeats both lines back" — which makes this a promise printed on the screen
    where the money is taken, next to two boxes nobody may tick for the buyer
    (Art. 22).

    What is quoted is what was **recorded**, not what this module's copy table
    says today. The two are the same sentence when nothing has drifted, which is
    exactly why the fixture deliberately differs from the table: a letter that
    printed its own copy would pass this test while quoting a checkbox the buyer
    never read.
    """
    body = _letter(outbox, _receipt(locale=locale))["html"]
    copy = mail.RECEIPT_COPY[locale]

    for _key, text in TICKED:
        assert text in body
    assert copy.consent_title in body

@pytest.mark.parametrize("locale", sorted(LOCALES))
def test_a_receipt_with_no_consent_claims_none_and_says_the_right_stands(outbox, locale):
    """The worst thing this letter could do is invent a consent.

    Every payment used to get the heading "What you ticked at the checkout" over
    two sentences from a per-locale template — including payments opened from
    surfaces with no checkbox on them at all. A buyer who was never shown a box
    then held a document from us asserting they ticked one, which is not a
    weaker confirmation but a manufactured one, on the medium whose entire
    purpose is to be evidence.

    So with nothing recorded: no heading, no quotes, no waiver paragraph — and
    the good news said out loud, because a right nobody was asked to give up is
    a right the buyer still has.
    """
    body = _letter(outbox, _receipt(locale=locale, consent=None))["html"]
    copy = mail.RECEIPT_COPY[locale]

    assert copy.consent_title not in body
    assert copy.consent not in body
    assert copy.consent_plan not in body
    assert copy.withdrawal_stands in body
    # And it is still a receipt: what was bought, what was paid, who sold it.
    assert "$8.99" in body
    assert "Paddle.com Market Ltd" in body


def test_the_six_locales_are_six_translations_and_not_one_repeated():
    """The failure this catches is a paste, and it is invisible by inspection.

    A locale whose consent paragraph is English is a buyer who was handed a
    legal statement they cannot read, which is exactly as good as not sending
    one. Identity between any two of the six is the only cheap way to see it.
    """
    assert set(mail.RECEIPT_COPY) == LOCALES
    for field in ("subject", "lede", "consent", "consent_plan", "withdrawal_stands",
                  "cancel", "refund"):
        written = {getattr(copy, field) for copy in mail.RECEIPT_COPY.values()}
        assert len(written) == len(LOCALES), f"{field} is not six different sentences"


def test_every_product_on_the_ladder_has_a_name_in_every_language():
    """A receipt has to say what was bought, so a price with no name is a gap.

    Pinned against the catalogue rather than against a list here: the ladder is
    the thing that changes, and the day somebody adds a rung this fails instead
    of shipping a confirmation that names the purchase `archive-bump`.
    """
    for locale in LOCALES:
        assert set(mail.RECEIPT_PRODUCTS[locale]) == set(PRODUCTS), locale


def test_a_language_we_do_not_speak_is_written_to_in_english(outbox):
    """Falling back is right; falling back silently is not — see the log line.

    A confirmation nobody receives is worse than one in the wrong language, so
    an unknown locale must not raise. It must also not produce an empty letter,
    which is what reading the copy table with `[]` would have done.
    """
    body = _letter(outbox, _receipt(locale="nl"))["html"]
    assert mail.RECEIPT_COPY["en"].consent in body


def test_the_amount_is_what_the_statement_will_say(outbox):
    """The processor's total, tax included — never the catalogue's shelf price.

    A merchant of record adds US sales tax on top in some states, so the money
    that moved is the shelf price *or more*, and a receipt quoting the shelf
    price disagrees with the card statement beside it. That disagreement is the
    beginning of a dispute, and the buyer is the one who is right.
    """
    body = _letter(outbox, _receipt(amount_cents=971))["html"]
    assert "$9.71" in body
    assert "$8.99" not in body


def test_a_brazilian_is_shown_a_brazilian_price(outbox):
    """R$219,00 and not "R$219.00" — the same rule the renewal notice keeps."""
    body = _letter(
        outbox, _receipt(locale="pt-BR", product="annual", amount_cents=21900,
                         currency="BRL", recurring=True)
    )["html"]
    assert "R$ 219" in body


def test_the_letter_offers_no_unsubscribe(outbox):
    """It is not marketing. A confirmation of what somebody paid is owed to
    them, and an unsubscribe on it would be an offer to stop owing it."""
    body = _letter(outbox, _receipt())["html"].lower()
    assert "unsubscribe" not in body or "nothing to unsubscribe" in body


def test_an_unconfigured_mail_provider_is_a_refusal_and_not_a_pretence(monkeypatch):
    """`False` here is a legal fact rather than a failed send.

    It means a purchase exists whose waiver was never completed. The caller has
    to be able to tell that apart from success, so it is a return value and not
    a shrug.
    """
    from alma import config as config_module

    monkeypatch.setenv("RESEND_API_KEY", "")
    config_module.settings.cache_clear()
    try:
        assert asyncio.run(mail.send_receipt(_receipt())) is False
    finally:
        config_module.settings.cache_clear()


# ══════════════════════════════════════════════════════════════════════════
#  The wiring: one payment, one letter, and never at the cost of the grant
# ══════════════════════════════════════════════════════════════════════════

def _sign(body: bytes) -> str:
    at = int(time.time())
    digest = hmac.new(SECRET.encode(), f"{at}:".encode() + body, hashlib.sha256).hexdigest()
    return f"ts={at};h1={digest}"


@pytest.fixture
def paid_api(api, monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("PADDLE_API_KEY", "pdl_test_key")
    config_module.settings.cache_clear()
    yield api
    config_module.settings.cache_clear()


@pytest.fixture
def receipts(monkeypatch) -> list:
    """Every receipt the router handed to the post, without a provider."""
    posted: list = []

    async def capture(receipt) -> bool:
        posted.append(receipt)
        return True

    monkeypatch.setattr(mail, "send_receipt", capture)
    return posted


def _post_webhook(api, payload: dict):
    body = json.dumps(payload).encode()
    return api.post(
        "/v1/billing/webhook", content=body, headers={"Paddle-Signature": _sign(body)}
    )


def _purchase_event(
    *, event_id: str, user_id: str, product: str = "natal",
    total: str = "899", subscription_id: str | None = None,
    buyer_email: str | None = None,
) -> dict:
    data: dict = {
        "id": f"txn_{event_id}",
        "currency_code": "USD",
        "custom_data": stamp(user_id, product),
        "details": {"totals": {"grand_total": total}},
    }
    if subscription_id:
        data["subscription_id"] = subscription_id
    if buyer_email:
        # The address the processor collected inside its own checkout. Paddle
        # usually sends a `customer_id` instead and has to be asked over the
        # network; the expanded shape is the one that costs no round trip, and
        # it is the shape this test uses because what is under test is what the
        # router does with an address rather than how the adapter found one.
        data["customer"] = {"email": buyer_email}
    return {"event_id": event_id, "event_type": "transaction.completed", "data": data}


def _signed_in(api, headers, *, email: str = "sofia@example.com", locale: str = "it") -> str:
    """A user with an address, which is the only user we can write to.

    Written straight onto the row rather than through the magic-link flow: what
    is being tested is what the webhook does with an address, not how one gets
    there, and the sign-in path would drag a mail provider into a test about
    receipts.
    """
    from alma.db.models import User
    from alma.db.session import session_factory

    user_id = api.get("/v1/auth/session", headers=headers).json()["user_id"]

    async def attach():
        async with session_factory()() as session:
            user = await session.get(User, user_id)
            user.email = email
            user.locale = locale
            user.provider = "email"
            await session.commit()

    read_async(attach)
    return user_id


def _held(api, headers) -> dict:
    return api.get("/v1/billing/entitlements", headers=headers).json()


def test_a_purchase_is_confirmed_in_writing(paid_api, auth_headers, receipts):
    """The whole point: money moved, access was given, and a durable copy of
    what was agreed went to the buyer, in the language they bought in."""
    user_id = _signed_in(paid_api, auth_headers)
    response = _post_webhook(paid_api, _purchase_event(event_id="evt_1", user_id=user_id))

    assert response.json()["status"] == "granted natal"
    assert len(receipts) == 1
    written = receipts[0]
    assert written.email == "sofia@example.com"
    assert written.locale == "it"
    assert written.product == "natal"
    assert written.amount_cents == 899
    assert written.merchant == "Paddle.com Market Ltd"
    assert written.reference == "txn_evt_1"
    assert written.recurring is False


def test_a_redelivered_webhook_does_not_write_twice(paid_api, auth_headers, receipts):
    """Providers retry, and they are right to. Two receipts for one payment
    reads as a system that has charged twice — which is the letter's own
    subject, so it is the worst possible thing to duplicate."""
    user_id = _signed_in(paid_api, auth_headers)
    event = _purchase_event(event_id="evt_same", user_id=user_id)

    first = _post_webhook(paid_api, event)
    again = _post_webhook(paid_api, event)

    assert first.json()["status"] == "granted natal"
    assert again.json()["status"] == "already processed"
    assert len(receipts) == 1


def test_a_mail_provider_having_a_bad_afternoon_never_costs_a_grant(
    paid_api, auth_headers, monkeypatch
):
    """The entitlement is the customer's the moment the money moved.

    A webhook that fails is a webhook the processor retries, and a retried
    delivery is how one payment becomes two grants — so an unsent email must
    never turn into a refused delivery. It is logged and the day goes on.
    """
    async def explode(receipt):
        raise RuntimeError("resend is down")

    monkeypatch.setattr(mail, "send_receipt", explode)

    user_id = _signed_in(paid_api, auth_headers)
    response = _post_webhook(paid_api, _purchase_event(event_id="evt_boom", user_id=user_id))

    assert response.status_code == 200
    assert response.json()["status"] == "granted natal"
    assert "natal" in _held(paid_api, auth_headers)["unlocked"]


def test_a_guest_is_written_to_at_the_address_the_processor_collected(
    paid_api, auth_headers, receipts
):
    """The guest funnel is most of this product's buyers, and it had no receipt.

    A guest may buy — that is deliberate — and a guest has no address of ours.
    Every one of those purchases therefore went unconfirmed, which means no
    durable medium, which means the third leg of Art. 16(m) was missing for the
    whole pre-account funnel: those buyers keep the 14-day right whatever they
    ticked. The address exists, though. Both processors collect one inside their
    own checkout, and the fix is to ask them for it.
    """
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    response = _post_webhook(
        paid_api,
        _purchase_event(event_id="evt_guest", user_id=user_id, buyer_email="paid@example.com"),
    )

    assert response.json()["status"] == "granted natal"
    assert "natal" in _held(paid_api, auth_headers)["unlocked"]
    assert [r.email for r in receipts] == ["paid@example.com"]


def test_the_account_address_wins_over_the_one_on_the_card(
    paid_api, auth_headers, receipts
):
    """The contract is with the account, so that is the inbox we write to.

    Somebody signed in whose card is registered to a different address gets the
    confirmation where they will look for it, rather than wherever their bank
    happens to hold. The processor's copy is the answer for a guest and not a
    replacement for ours.
    """
    user_id = _signed_in(paid_api, auth_headers)
    _post_webhook(
        paid_api,
        _purchase_event(event_id="evt_both", user_id=user_id,
                        buyer_email="the.card@example.com"),
    )
    assert [r.email for r in receipts] == ["sofia@example.com"]


def test_a_buyer_nobody_can_write_to_still_gets_what_they_paid_for(
    paid_api, auth_headers, receipts
):
    """No address on the account, none from the processor, and a grant anyway.

    What must never happen is the purchase failing because a letter could not be
    addressed. What *does* happen is logged at error, because the consequence is
    not "no email" — it is a waiver that was never completed.
    """
    user_id = paid_api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    response = _post_webhook(paid_api, _purchase_event(event_id="evt_nobody", user_id=user_id))

    assert response.json()["status"] == "granted natal"
    assert "natal" in _held(paid_api, auth_headers)["unlocked"]
    assert receipts == []


def test_opening_a_checkout_confirms_nothing(paid_api, auth_headers, receipts):
    """A receipt for a purchase that has not happened is a receipt for nothing.

    The checkout endpoint hands out no access and it may not hand out a
    confirmation either — the browser reporting an intention to pay is not a
    payment, and everything a browser can decide, a browser can be made to
    decide.
    """
    _signed_in(paid_api, auth_headers)
    paid_api.post("/v1/billing/checkout", json={"product": "natal"}, headers=auth_headers)
    assert receipts == []


def test_a_subscription_receipt_says_the_year_can_still_be_withdrawn_from(
    paid_api, auth_headers, receipts
):
    """The recurring flag is read off the catalogue, not off a list of kinds.

    It decides which of two legally different paragraphs the buyer is sent, so
    getting it from `interval` — the same field `entitlement_for` reads — is
    what stops the annual from being confirmed as though it were a chapter.
    """
    user_id = _signed_in(paid_api, auth_headers)
    _post_webhook(
        paid_api,
        _purchase_event(event_id="evt_year", user_id=user_id, product="annual",
                        total="7899", subscription_id="sub_1"),
    )
    assert [(r.product, r.recurring) for r in receipts] == [("annual", True)]


def test_a_refund_is_not_a_purchase_to_confirm(paid_api, auth_headers, receipts):
    """Money going the other way is not a sale, and a receipt for it would tell
    somebody they had bought the thing we have just taken back."""
    user_id = _signed_in(paid_api, auth_headers)
    _post_webhook(paid_api, _purchase_event(event_id="evt_sale", user_id=user_id))
    receipts.clear()

    refunded = _post_webhook(paid_api, {
        "event_id": "evt_back",
        "event_type": "adjustment.created",
        "data": {
            "id": "adj_1",
            "transaction_id": "txn_evt_sale",
            "action": "refund",
            "type": "full",
            "currency_code": "USD",
            "details": {"totals": {"grand_total": "899"}},
        },
    })
    assert refunded.json()["status"] == "revoked 1"
    assert receipts == []


# ══════════════════════════════════════════════════════════════════════════
#  The consent: written at the checkout, quoted by the receipt
# ══════════════════════════════════════════════════════════════════════════

#: What the offer screen posts. The shape is the contract: a locale, the moment
#: of the tap by the buyer's own clock, and the exact sentences that were on the
#: screen when they tapped.
CONSENT_BODY = {
    "locale": "de",
    "agreed_at": "2026-08-06T15:40:55.510Z",
    "statements": [
        {"key": "immediate_access",
         "text": "Schreib es sofort — ich warte meine 14 Tage Bedenkzeit nicht ab."},
        {"key": "withdrawal_waived",
         "text": "Mir ist klar: Sobald es geschrieben ist, ist dieses Recht weg."},
    ],
}


@pytest.fixture
def sellable(paid_api, monkeypatch):
    """A checkout that opens, so the consent beside it can be recorded.

    `open_session` is stubbed rather than the whole adapter: what is under test
    is that the endpoint stores what the buyer agreed to, and dragging a
    processor's HTTP API into that would be testing Paddle.
    """
    from alma.api.routers import billing as router
    from alma.billing.paddle import PaddleProvider
    from alma.billing.provider import SessionHandle, stamp as seal

    class Opens(PaddleProvider):
        async def open_session(self, *, product, user_id, currency, country=None, email=None):
            return SessionHandle(
                provider="paddle", product=product, currency=currency,
                cents=899, display="$8.99", custom_data=seal(user_id, product),
                price_id="pri_test",
            )

    monkeypatch.setattr(router, "billing_adapter", lambda *_, **__: Opens())
    return paid_api


def test_what_the_buyer_ticked_is_what_the_letter_quotes(sellable, auth_headers, receipts):
    """End to end, and this is the finding the whole phase turned on.

    The consent record used to be accepted by the checkout and dropped on the
    floor, while the receipt asserted a consent from a per-locale template. So
    the two legs of Art. 16(m) the checkout can produce existed nowhere, and the
    document that was supposed to confirm them was generating them instead.
    """
    user_id = _signed_in(sellable, auth_headers)
    opened = sellable.post(
        "/v1/billing/checkout",
        json={"product": "natal", "consent": CONSENT_BODY},
        headers=auth_headers,
    )
    assert opened.status_code == 200

    _post_webhook(sellable, _purchase_event(event_id="evt_agreed", user_id=user_id))

    assert len(receipts) == 1
    assert receipts[0].consent == (
        ("immediate_access", CONSENT_BODY["statements"][0]["text"]),
        ("withdrawal_waived", CONSENT_BODY["statements"][1]["text"]),
    )


def test_a_checkout_that_asked_for_nothing_confirms_nothing(
    sellable, auth_headers, receipts
):
    """The Paywall sells the archive and the year with no boxes on screen.

    That surface must keep working — hard-requiring the field would 400 every
    cabinet purchase — and the buyer must not be told they ticked something.
    `None` here is what makes the letter print the paragraph saying the
    withdrawal right still stands.
    """
    user_id = _signed_in(sellable, auth_headers)
    sellable.post("/v1/billing/checkout", json={"product": "natal"}, headers=auth_headers)
    _post_webhook(sellable, _purchase_event(event_id="evt_silent", user_id=user_id))

    assert [r.consent for r in receipts] == [None]


def test_half_a_consent_is_not_a_consent(sellable, auth_headers, receipts):
    """One unreadable statement and none of them is stored.

    Quoting one of two ticked lines back at somebody is a document that
    misrepresents what they agreed to, and a malformed record is refused in the
    buyer's favour rather than in ours: no record, no waiver, and the letter
    says the right stands.
    """
    user_id = _signed_in(sellable, auth_headers)
    sellable.post(
        "/v1/billing/checkout",
        json={"product": "natal", "consent": {
            "locale": "de",
            "statements": [CONSENT_BODY["statements"][0], {"key": "withdrawal_waived"}],
        }},
        headers=auth_headers,
    )
    _post_webhook(sellable, _purchase_event(event_id="evt_half", user_id=user_id))

    assert [r.consent for r in receipts] == [None]


def test_a_renewal_does_not_reuse_last_year_s_ticked_boxes(
    sellable, auth_headers, receipts
):
    """A second year's charge is not a second contract.

    The consent was given once, when the plan was bought. A renewal receipt that
    quoted those boxes as though they had been ticked this morning would be
    dating a record wrongly — and the plan does not rest on a waiver anyway,
    because Art. 16(a) does not extinguish the right until the service is fully
    performed.
    """
    user_id = _signed_in(sellable, auth_headers)
    sellable.post(
        "/v1/billing/checkout",
        json={"product": "annual", "consent": CONSENT_BODY},
        headers=auth_headers,
    )
    _post_webhook(sellable, _purchase_event(
        event_id="evt_y1", user_id=user_id, product="annual",
        total="7899", subscription_id="sub_year"))
    _post_webhook(sellable, _purchase_event(
        event_id="evt_y2", user_id=user_id, product="annual",
        total="7899", subscription_id="sub_year"))

    assert len(receipts) == 2
    assert receipts[0].consent is not None
    assert receipts[1].consent is None, "a renewal quoted a consent given a year ago"


def test_the_seller_named_is_the_processor_that_is_actually_running(
    paid_api, auth_headers, receipts, monkeypatch
):
    """The merchant of record is a configuration decision, and this letter is
    what a card issuer reads during a dispute. A build switched to the other
    processor and still naming the first one is telling them the wrong seller.
    """
    from alma.api.routers import billing as router
    from alma.billing.paddle import PaddleProvider

    class SoldBySomebodyElse(PaddleProvider):
        """The same processor, sold under a different legal entity.

        Subclassed rather than stubbed so that the signature check and the
        parser are the real ones: what is being substituted is the single fact
        the receipt reads, and nothing else about the delivery.
        """

        merchant = "Not Paddle Ltd"

    monkeypatch.setattr(router, "billing_adapter", lambda *_, **__: SoldBySomebodyElse())
    user_id = _signed_in(paid_api, auth_headers)
    _post_webhook(paid_api, _purchase_event(event_id="evt_who", user_id=user_id))

    assert receipts[0].merchant == "Not Paddle Ltd"
