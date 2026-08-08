"""The seam, tested as the thing a second processor will be held to.

Everything here is written against `provider.py` rather than against Paddle.
That is the point: each of these is a rule the Dodo adapter has to satisfy on
the day it lands, and a test that only ever ran Paddle through its own
functions would prove nothing about the seam at all.

`test_billing.py` stays the adversarial file — signatures, replays, forged
bodies, the money trail. This one is about translation: whether one processor's
shape actually arrives in our words, and whether the words mean what the
entitlement layer thinks they mean.
"""

from __future__ import annotations

import time

import pytest

from alma.billing import catalogue as prices
from alma.billing import paddle as adapter
from alma.billing.provider import (
    MAX_SIGNATURE_AGE,
    BillingProvider,
    BillingUnavailable,
    EventKind,
    Grant,
    InvalidSignature,
    NormalisedEvent,
    SessionHandle,
    check_freshness,
    entitlement_for,
    header_value,
    provider_for,
    sealed_owner,
    stamp,
)

SECRET = "pdl_ntfset_test_secret"


@pytest.fixture
def configured(monkeypatch):
    """Settings with both Paddle credentials present."""
    from alma import config as config_module

    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("PADDLE_API_KEY", "pdl_test_key")
    monkeypatch.setenv("PADDLE_CLIENT_TOKEN", "live_token")
    config_module.settings.cache_clear()
    yield
    config_module.settings.cache_clear()


def _paddle_event(event_type: str = "transaction.completed", **data) -> dict:
    body = {
        "id": "txn_1",
        "currency_code": "USD",
        "custom_data": stamp("user-1", "natal"),
        "details": {"totals": {"grand_total": "899"}},
        "billing_details": {"address": {"country_code": "IT"}},
    }
    body.update(data)
    return {"event_id": "evt_1", "event_type": event_type, "data": body}


# ── the adapter really is the protocol ─────────────────────────────────────

def test_the_paddle_adapter_satisfies_the_protocol():
    """A protocol nothing is checked against is a comment with syntax."""
    assert isinstance(adapter.PaddleProvider(), BillingProvider)


def test_the_configuration_picks_the_processor():
    """Which processor runs is a config value, which is the whole exercise."""
    assert provider_for("paddle").name == "paddle"
    with pytest.raises(BillingUnavailable, match="not a payment processor"):
        provider_for("stripe-but-imaginary")


def test_an_unconfigured_provider_name_falls_back_rather_than_failing_to_import():
    """`ALMA_BILLING_PROVIDER` does not exist yet, and this still has to work.

    A seam that only functions once someone has added a settings field is a
    seam that breaks the service on the commit before the one that fixes it.
    """
    assert provider_for().name == "paddle"


# ── a processor's shape arrives in our words ───────────────────────────────

def test_normalising_loses_nothing_the_entitlement_layer_needs():
    """Every field the grant path reads survives the translation."""
    event = adapter.parse(_paddle_event())
    normalised = event.normalise()

    assert normalised.provider == "paddle"
    assert normalised.owner_id == "user-1"
    assert normalised.product == "natal"
    assert normalised.transaction_id == "txn_1"
    assert normalised.amount_cents == 899
    assert normalised.currency == "USD"
    assert normalised.country == "IT"
    assert normalised.kind is EventKind.PAYMENT


def test_an_adapter_produces_exactly_a_grant_and_nothing_else():
    """The whole contract with the entitlement layer, stated once.

    The neutral function is handed an event built by hand — no Paddle anywhere
    — and answers the same `Grant` the adapter's own path answers. That is what
    a second processor has to be able to reach.
    """
    by_hand = NormalisedEvent(
        provider="not-a-real-processor",
        id="evt_1",
        type="whatever.that.processor.calls.it",
        kind=EventKind.PAYMENT,
        product="annual",
        subscription_id="sub_9",
        grants=True,
    )
    granted = entitlement_for(by_hand)

    assert isinstance(granted, Grant)
    assert granted.system == "*"
    assert granted.scope == "all"
    assert granted.duration.days == 365
    assert granted.subscription_id == "sub_9"


def test_a_recurring_plan_is_recognised_by_its_interval_not_by_its_name():
    """Stated over the catalogue, in the neutral function, with no adapter.

    The list-of-kind-strings this replaces is what let a $9.99 monthly write a
    permanent everything-grant: the list said "annual" and the monthly was not
    it, so it fell through to a one-time grant with no expiry.
    """
    for key, item in prices.PRODUCTS.items():
        granted = entitlement_for(
            NormalisedEvent(
                provider="x", id="e", type="t", kind=EventKind.PAYMENT,
                product=key, grants=True,
            )
        )
        assert granted is not None, key
        assert (granted.duration is not None) == bool(item.interval), key


def test_an_event_that_does_not_grant_grants_nothing():
    """The flag is the policy, and the adapter is the only thing that sets it."""
    refund = adapter.parse(_paddle_event("transaction.refunded")).normalise()
    assert refund.grants is False
    assert entitlement_for(refund) is None


def test_every_event_the_policy_names_is_one_the_taxonomy_knows():
    """An adapter must not call an event significant and then fail to classify it.

    A `granting` string that normalises to UNKNOWN means the policy sets and
    the taxonomy have drifted apart, and the symptom is a payment that grants
    correctly while every report about it says "unknown".
    """
    provider = adapter.PaddleProvider()
    for event_type in provider.granting | provider.revoking:
        kind = adapter.parse({"event_type": event_type, "data": {}}).normalise().kind
        assert kind is not EventKind.UNKNOWN, event_type


def test_an_unknown_event_type_is_recorded_rather_than_refused():
    """A processor shipping a feature we have not adopted is not an incident."""
    event = adapter.parse(_paddle_event("subscription.trialing")).normalise()
    assert event.kind is EventKind.UNKNOWN
    assert (event.grants, event.revokes) == (False, False)


# ── the things that look like a revocation and are not ─────────────────────

def test_a_partial_refund_does_not_close_the_grant():
    """Five dollars back on a reading they have read is not a repossession."""
    event = NormalisedEvent(
        provider="x", id="e", type="t", kind=EventKind.ADJUSTMENT,
        adjustment=("refund", "partial"),
    )
    assert event.returns_money is True
    assert event.closes_the_grant is False


def test_a_credit_neither_returns_money_nor_closes_anything():
    """A credit reduces a future invoice. Nothing comes back on this charge."""
    event = NormalisedEvent(
        provider="x", id="e", type="t", kind=EventKind.ADJUSTMENT,
        adjustment=("credit", "full"),
    )
    assert event.returns_money is False
    assert event.closes_the_grant is False


def test_a_full_chargeback_closes_the_grant():
    """A chargeback is a full refund we did not choose, and it still closes."""
    event = NormalisedEvent(
        provider="x", id="e", type="t", kind=EventKind.ADJUSTMENT,
        adjustment=("chargeback", "full"),
    )
    assert event.closes_the_grant is True


def test_dunning_and_cancellation_stay_distinguishable_from_an_ending():
    """Three different futures, and only one of them should stop access today.

    A dunning retry is a card that will probably work on the second attempt; a
    cancellation is a period already paid for; only an expiry is access that
    has run out. The taxonomy keeps them apart so the question "which of these
    ends a grant" has somewhere to be answered *once*.

    It is not answered once today: Paddle's `revoking` set ends access on both
    of the first two, which is the policy this code shipped with and which the
    Dodo rules contradict. That divergence is deliberately not asserted here —
    pinning it would make it permanent — but it is why these kinds are separate
    values rather than one `SUBSCRIPTION_TROUBLE`.
    """
    dunning = adapter.parse(_paddle_event("subscription.past_due")).normalise()
    cancelled = adapter.parse(_paddle_event("subscription.canceled")).normalise()

    assert dunning.kind is EventKind.SUBSCRIPTION_DUNNING
    assert cancelled.kind is EventKind.SUBSCRIPTION_CANCELLED
    assert dunning.kind is not cancelled.kind
    assert EventKind.SUBSCRIPTION_ENDED not in (dunning.kind, cancelled.kind)


def test_a_subscription_event_is_never_read_as_money_moving():
    """`data.id` on one of these is a plan, not a payment.

    Recording it as a purchase wrote a zero-amount row whose transaction id had
    never identified money. Asserted on the neutral flag, so the next adapter
    inherits the rule rather than the bug.
    """
    event = adapter.parse(
        {"event_id": "e", "event_type": "subscription.activated",
         "data": {"id": "sub_1", "status": "active"}}
    ).normalise()
    assert event.moves_money is False
    assert event.subscription_id == "sub_1"


def test_a_payment_is_read_as_money_moving():
    assert adapter.parse(_paddle_event()).normalise().moves_money is True


# ── the parts of a signature check that belong to nobody ───────────────────

def test_the_replay_window_is_the_seam_s_and_not_a_processor_s():
    """Dodo's documentation gives no guidance here, so ours has to survive.

    An unbounded window means a signature lifted from a log is good forever.
    """
    check_freshness(int(time.time()))
    with pytest.raises(InvalidSignature, match="replay"):
        check_freshness(int(time.time()) - MAX_SIGNATURE_AGE - 1)
    with pytest.raises(InvalidSignature, match="not a number"):
        check_freshness("the day before yesterday")


def test_a_signature_from_the_near_future_is_still_accepted():
    """Clocks drift, and a renewal must not fail because a server ran fast."""
    check_freshness(int(time.time()) + 10)


def test_headers_are_found_however_the_sender_capitalised_them():
    """Standard Webhooks sends lowercase; Paddle sends title case; HTTP says
    neither matters. An adapter that string-matches one spelling refuses every
    real delivery from the other."""
    assert header_value({"paddle-signature": "ts=1;h1=x"}, "Paddle-Signature") == "ts=1;h1=x"
    assert header_value({"Webhook-Id": "msg_1"}, "webhook-id") == "msg_1"
    assert header_value({}, "webhook-id") == ""


def test_the_protocol_refuses_an_unsigned_body_the_same_way_the_module_does():
    """Going through the seam must not soften the refusal.

    It raises rather than returning a bool on purpose: "no secret is
    configured" and "this signature does not match" are the same boolean and
    completely different incidents, and only one of them is an attacker.
    """
    provider = adapter.PaddleProvider()
    with pytest.raises(InvalidSignature, match="no signature"):
        provider.verify(b"{}", {}, secret=SECRET)
    with pytest.raises(InvalidSignature, match="PADDLE_WEBHOOK_SECRET"):
        provider.verify(b"{}", {"Paddle-Signature": "ts=1;h1=x"}, secret="")


# ── opening a checkout, whoever is running it ──────────────────────────────

async def test_a_session_quotes_the_price_the_catalogue_holds(configured):
    """What the paywall shows and what the card is charged are one number."""
    session = await adapter.PaddleProvider().open_session(
        product="natal", user_id="user-1", currency="EUR", country="DE"
    )
    assert isinstance(session, SessionHandle)
    assert session.cents == prices.PRODUCTS["natal"].cents_in("EUR")
    assert session.display == prices.PRODUCTS["natal"].display("EUR")


async def test_a_session_carries_the_owner_sealed_and_never_the_email(configured):
    """`custom_data` is how a payment finds its owner when it comes back.

    An email in there would attach a payment to whoever in a household shares
    an address with the payer, which is the failure this field exists to avoid
    — so an adapter that is *given* an email still must not echo one.

    And the owner is **sealed**. On this processor the blob travels through the
    browser, and the client token that opens the overlay is published, so a
    payer who could write this field would choose both which account is credited
    and what it buys. The two readable fields stay readable so a payment in the
    dashboard can be attributed by hand; the third is what makes them ours.
    """
    session = await adapter.PaddleProvider().open_session(
        product="natal", user_id="user-7", currency="USD", email="buyer@example.com"
    )
    assert session.custom_data["user_id"] == "user-7"
    assert session.custom_data["product"] == "natal"
    assert sealed_owner(session.custom_data) == ("user-7", "natal")
    assert "buyer@example.com" not in str(session.to_client())


def test_metadata_nobody_sealed_names_nobody():
    """The whole rule, in one line: a signature relays, it does not attest.

    A blob a payer wrote in a console has a user id and a product in it and
    looks exactly like ours. Reading an owner out of one is how a purchase lands
    on an account that never opened the checkout, and reading a product out of
    one is how $8.99 buys the $38.99 archive.
    """
    assert sealed_owner({"user_id": "user-1", "product": "archive"}) == (None, None)
    assert sealed_owner({}) == (None, None)
    assert sealed_owner(None) == (None, None)

    honest = stamp("user-1", "natal")
    assert sealed_owner(honest) == ("user-1", "natal")
    # ...and neither half can be edited afterwards while keeping the seal.
    assert sealed_owner({**honest, "product": "archive"}) == (None, None)
    assert sealed_owner({**honest, "user_id": "user-2"}) == (None, None)


async def test_a_product_not_sold_in_a_market_is_refused_rather_than_priced(configured):
    """The five purchasing-power markets carry the archive and the year only."""
    with pytest.raises(prices.NotSold):
        await adapter.PaddleProvider().open_session(
            product="natal", user_id="user-1", currency="BRL", country="BR"
        )


async def test_a_session_cannot_be_opened_without_credentials(monkeypatch):
    """No keys must mean a clear refusal, not a checkout that opens on nothing."""
    from alma import config as config_module

    monkeypatch.setenv("PADDLE_API_KEY", "")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "")
    config_module.settings.cache_clear()
    try:
        with pytest.raises(BillingUnavailable):
            await adapter.PaddleProvider().open_session(
                product="natal", user_id="user-1", currency="USD"
            )
    finally:
        config_module.settings.cache_clear()


def test_a_client_is_never_handed_a_null_identifier():
    """A field the adapter could not fill is absent, not `null`.

    A client that reaches for `price_id` and gets `undefined` passes it to an
    SDK, and the checkout silently never opens — which reads to the buyer as a
    dead button rather than as an error anybody gets told about.
    """
    dodo_shaped = SessionHandle(
        provider="some-processor", product="natal", currency="USD",
        cents=899, display="$8.99", custom_data={"user_id": "u"},
        url="https://checkout.example/pay/abc",
    )
    body = dodo_shaped.to_client()
    assert body["checkout_url"] == "https://checkout.example/pay/abc"
    assert "price_id" not in body and "client_secret" not in body


async def test_cancelling_without_an_api_key_fails_loudly(monkeypatch):
    """A cancel that quietly does nothing is worse than one that errors.

    The person believes they have stopped paying, and finds out otherwise on a
    card statement — which is the one billing failure that reliably becomes a
    chargeback rather than a support ticket.
    """
    from alma import config as config_module

    monkeypatch.setenv("PADDLE_API_KEY", "")
    config_module.settings.cache_clear()
    try:
        with pytest.raises(BillingUnavailable, match="PADDLE_API_KEY"):
            await adapter.PaddleProvider().cancel_subscription("sub_1")
    finally:
        config_module.settings.cache_clear()


# ── one processor's word must not reach the browser as another's ───────────

def test_the_environment_word_the_client_reads_is_the_seam_s_and_not_a_vendor_s():
    """Each processor has its own name for "this is real money".

    Dodo's configuration holds *their* words — `test_mode` and `live_mode`,
    because that is what their dashboard prints — while `src/lib/checkout.ts`
    computes `live = environment === "production"`. Handing the browser
    `live_mode` therefore initialised the **test** SDK against a live checkout
    session, and the failure lands on the first real customer of the new
    processor. Neither suite could see it, because each side is internally
    consistent on its own.

    Asserted over both adapters, because the rule is that the client reads one
    word whoever is running.
    """
    from alma.billing import dodo

    assert dodo.is_live("live_mode") and dodo.is_live("production")
    assert not dodo.is_live("test_mode")
    # A typo is the test environment. The opposite mistake costs one failed
    # test purchase; this one charges real cards through a sandbox SDK.
    assert not dodo.is_live("livemode") and not dodo.is_live("") and not dodo.is_live(None)


def test_the_host_and_the_word_handed_to_the_client_cannot_disagree():
    """One predicate decides both, so a live API call cannot open a test overlay."""
    from alma.billing import dodo

    for environment, host, word in (
        ("live_mode", dodo.LIVE_API, "production"),
        ("test_mode", dodo.TEST_API, "sandbox"),
        ("nonsense", dodo.TEST_API, "sandbox"),
    ):
        assert dodo.DodoClient(api_key="k", environment=environment).base == host
        assert ("production" if dodo.is_live(environment) else "sandbox") == word


def test_every_adapter_names_the_company_that_legally_sells():
    """Both processors are merchants of record, and it is not the same company.

    `src/lib/legal.ts` held this as a build-time constant naming one of them, so
    a build reconfigured to the other still told buyers — and, on the refunds
    page, their card issuer — the wrong seller.
    """
    from alma.billing import dodo

    assert adapter.PaddleProvider().merchant
    assert dodo.DodoProvider().merchant
    assert adapter.PaddleProvider().merchant != dodo.DodoProvider().merchant


def test_the_package_does_not_import_a_processor_to_be_imported():
    """Deleting one adapter must not break every importer of the package.

    The header used to do `from . import catalogue, paddle, provider`, which
    meant the coupling had moved from the router to the package rather than
    disappearing — and the whole claim of this seam is that being refused by a
    processor is an afternoon. Read off the source rather than by importing,
    because by the time a suite has run anything the adapters are in
    `sys.modules` and a successful import proves nothing.
    """
    import pathlib as _pathlib

    import alma.billing as package

    eager = [
        line
        for line in _pathlib.Path(package.__file__).read_text().splitlines()
        if line.startswith(("from . import", "import "))
    ]
    assert eager == ["from . import catalogue, provider"], eager


def test_the_package_exports_exactly_what_it_says_it_does():
    """`__all__` named `entitlement_for` while the comment above it explained
    why that name is deliberately absent, so `from alma.billing import *` raised
    `AttributeError`. The comment and the list were disagreeing, and the list is
    the one being executed.
    """
    import alma.billing as package

    assert "entitlement_for" not in package.__all__
    for name in package.__all__:
        assert hasattr(package, name), name


# ── what a store calls the things in our catalogue ─────────────────────────


def test_every_catalogue_key_round_trips_through_a_store_product_id():
    """The rule has to be reversible, and it is reversible only by accident.

    A store product id is *chosen* rather than issued — we type it into App
    Store Connect or the Play Console — so it is computed from the catalogue key
    instead of being a second table to keep in agreement. Neither console
    accepts a hyphen, so four of our keys grow an underscore on the way out and
    lose it on the way back. That inverse is unambiguous only because no key
    contains an underscore already, which is a fact rather than a hope: the
    assertion below is what keeps it one.
    """
    from alma.billing.provider import store_product_id, store_slug

    for key in prices.PRODUCTS:
        assert "_" not in key, (
            f"{key!r} contains an underscore, so the hyphen substitution in "
            "store_product_id is no longer reversible"
        )
        for processor in ("appstore", "googleplay"):
            product_id = store_product_id(key, processor=processor)
            assert "-" not in product_id, product_id
            assert store_slug(product_id, processor=processor) == key


def test_a_store_product_id_we_do_not_sell_answers_nothing():
    """`None` is the answer that refuses a grant, and it has to be reachable.

    A store account carries products from older price lists, and a purchase of
    one of those is a payment to record rather than a chapter to unlock.
    """
    from alma.billing.provider import store_slug

    assert store_slug("alma.something_withdrawn", processor="appstore") is None
    assert store_slug("com.someone.else.pro", processor="appstore") is None
    assert store_slug("", processor="appstore") is None


def test_a_pinned_identifier_beats_the_convention(monkeypatch):
    """The escape hatch for a product re-created under a name the rule cannot make.

    Neither store lets a product id be reused after deletion, so the day one has
    to be re-created it gets a new name — and the catalogue is where that is
    written down.
    """
    from dataclasses import replace

    from alma.billing.provider import store_product_id, store_slug

    pinned = replace(
        prices.PRODUCTS["natal"], processor_ids={"appstore": "alma.natal_v2"}
    )
    monkeypatch.setitem(prices.PRODUCTS, "natal", pinned)

    assert store_product_id("natal", processor="appstore") == "alma.natal_v2"
    assert store_slug("alma.natal_v2", processor="appstore") == "natal"
    # ...and the convention still answers for every other row, so pinning one
    # product does not require pinning all of them.
    assert store_product_id("archive", processor="appstore") == "alma.archive"


def test_the_prefix_is_configuration_rather_than_a_literal(monkeypatch):
    from alma import config as config_module
    from alma.billing.provider import store_product_id, store_slug

    monkeypatch.setenv("ALMA_STORE_PRODUCT_PREFIX", "co.example.alma.")
    config_module.settings.cache_clear()
    try:
        assert store_product_id("natal", processor="appstore") == "co.example.alma.natal"
        assert store_slug("alma.natal", processor="appstore") is None
    finally:
        config_module.settings.cache_clear()


# ── choosing a store, and refusing one that is not configured ──────────────


def test_the_factory_knows_both_stores():
    from alma.billing.appstore import AppStoreProvider
    from alma.billing.googleplay import GooglePlayProvider

    assert isinstance(provider_for("appstore"), AppStoreProvider)
    assert isinstance(provider_for("googleplay"), GooglePlayProvider)


def test_a_store_selected_without_its_credentials_refuses_to_boot(monkeypatch):
    """The boot-time refusal, extended to the stores.

    Nothing set is a legitimate state — the service runs all eight calculations
    without a processor and the checkout answers 503 naming the variables. What
    is fatal is being *half* configured, because that is somebody who believed
    they had finished: a Play package name with no service account verifies
    nothing, so the money arrives through Google and the reading does not.
    """
    from alma.config import Settings

    monkeypatch.setenv("ALMA_BILLING_PROVIDER", "googleplay")
    monkeypatch.setenv("GOOGLE_PLAY_PACKAGE_NAME", "com.alma.app")
    monkeypatch.delenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_PLAY_PUBSUB_AUDIENCE", raising=False)
    with pytest.raises(ValueError, match="half configured"):
        Settings()


def test_a_store_selected_with_nothing_set_is_a_legitimate_state(monkeypatch):
    from alma.config import Settings

    monkeypatch.setenv("ALMA_BILLING_PROVIDER", "appstore")
    monkeypatch.delenv("APPLE_BUNDLE_ID", raising=False)
    settings = Settings()
    assert settings.billing_enabled is False
    assert settings.missing_billing_credentials() == ["APPLE_BUNDLE_ID"]


def test_the_missing_credentials_named_are_the_selected_processors(monkeypatch):
    """Telling somebody to fill in Paddle's keys while running the App Store is
    worse than telling them nothing."""
    from alma.config import Settings

    monkeypatch.setenv("ALMA_BILLING_PROVIDER", "appstore")
    monkeypatch.setenv("PADDLE_API_KEY", "pdl_key")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "pdl_secret")
    monkeypatch.delenv("APPLE_BUNDLE_ID", raising=False)
    assert Settings().missing_billing_credentials() == ["APPLE_BUNDLE_ID"]


def test_credentials_can_be_asked_for_by_name_not_only_for_the_selected_one(monkeypatch):
    """One backend serves an iOS app and an Android app at once.

    `ALMA_BILLING_PROVIDER` decides who takes the money on the web and which
    notification endpoint is live; it cannot also decide which store a
    `/billing/iap/verify` request is allowed to name.
    """
    from alma.config import Settings

    monkeypatch.setenv("ALMA_BILLING_PROVIDER", "appstore")
    monkeypatch.setenv("APPLE_BUNDLE_ID", "com.alma.app")
    settings = Settings()
    assert settings.credentials_for("googleplay") == {
        "GOOGLE_PLAY_PACKAGE_NAME": "",
        "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON": "",
        "GOOGLE_PLAY_PUBSUB_AUDIENCE": "",
    }
