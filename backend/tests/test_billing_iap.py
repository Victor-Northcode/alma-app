"""`POST /v1/billing/iap/verify`, and the store notifications behind it.

The other two store files test the adapters. This one tests the *contract the
iOS and Android clients are written against*, and the two rules that only exist
once an adapter is wired into the router:

**A replay grants nothing twice.** This is not a hypothetical on a store the way
it is on a card processor. StoreKit re-delivers every unfinished transaction on
each app launch, and a "restore purchases" tap replays every transaction the
Apple ID has ever made — so the second call is the ordinary case, not the attack,
and it has to be cheap and silent.

**The owner is the caller, and the first caller wins.** Apple and Google echo
nothing of ours, so the account comes from the session token. Two accounts
racing for one transaction is therefore possible, and the safe direction is that
the second gets nothing.

The fixtures come from `test_billing_appstore`, deliberately: a second copy of
the JWS signing helper is a second thing to keep in agreement with RFC 7515.
"""

from __future__ import annotations

import pytest
from conftest import read_async

from test_billing_appstore import (  # noqa: F401 - `apple` is a fixture
    BUNDLE,
    _notification,
    _sign,
    _transaction,
    apple,
)


@pytest.fixture
def store_api(api, monkeypatch):
    """The app with Apple configured as a processor it can talk to."""
    from alma import config as config_module

    monkeypatch.setenv("APPLE_BUNDLE_ID", BUNDLE)
    config_module.settings.cache_clear()
    yield api
    config_module.settings.cache_clear()


@pytest.fixture
def notified_api(store_api, monkeypatch):
    """...and selected, so `/billing/webhook` is Apple's notification endpoint."""
    from alma import config as config_module

    monkeypatch.setenv("ALMA_BILLING_PROVIDER", "appstore")
    config_module.settings.cache_clear()
    yield store_api
    config_module.settings.cache_clear()


def _verify(api, headers, *, transaction: str, product: str, platform: str = "appstore"):
    return api.post(
        "/v1/billing/iap/verify",
        json={"platform": platform, "product": product, "transaction": transaction},
        headers=headers,
    )


def _held(api, headers) -> dict:
    return api.get("/v1/billing/entitlements", headers=headers).json()


def _second_account(api) -> dict:
    return {"Authorization": f"Bearer {api.get('/v1/auth/session').json()['token']}"}


# ══════════════════════════════════════════════════════════════════════════
#  The happy path, which is also the contract the client is written against
# ══════════════════════════════════════════════════════════════════════════

def test_a_verified_purchase_unlocks_the_system_it_bought(store_api, auth_headers, apple):
    token = _sign(_transaction(product="natal"), apple["key"], apple["chain"])
    response = _verify(store_api, auth_headers, transaction=token, product="natal")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "granted natal"
    assert body["platform"] == "appstore"
    assert body["transaction_id"] == "2000000500000001"
    # The list the paywall reads, returned from the same request. Without it the
    # app has to guess how long to wait before re-fetching `/entitlements`, and
    # the guess is made while somebody who has paid watches a locked chapter.
    assert body["unlocked"] == ["natal"]
    assert body["expires_at"] is None
    assert _held(store_api, auth_headers)["unlocked"] == ["natal"]


def test_a_subscription_reports_when_access_runs_out(store_api, auth_headers, apple):
    token = _sign(
        _transaction(
            product="monthly",
            transaction_id="2000000500000010",
            kind="Auto-Renewable Subscription",
            price=9990,
            expires_in_days=31,
        ),
        apple["key"],
        apple["chain"],
    )
    body = _verify(store_api, auth_headers, transaction=token, product="monthly").json()

    assert body["subscription_id"] == "2000000500000010"
    # The sentence the settings screen has to be able to say. A recurring grant
    # written without an expiry would be a month's payment that never has to be
    # made again, which `entitlements.grant` refuses outright.
    assert body["expires_at"] is not None


# ══════════════════════════════════════════════════════════════════════════
#  Replay
# ══════════════════════════════════════════════════════════════════════════

def test_a_replayed_transaction_grants_once(store_api, auth_headers, apple):
    """The ordinary case on a store, not the attack.

    StoreKit re-delivers unfinished transactions on every launch and a restore
    replays the lot. Two grants for one purchase is the bug that turns into a
    refund conversation; here it would also be a second `Purchase` row, and the
    money trail would show revenue that never arrived.
    """

    from sqlalchemy import select

    from alma.db.models import Entitlement, Purchase
    from alma.db.session import session_factory

    token = _sign(_transaction(product="natal"), apple["key"], apple["chain"])
    first = _verify(store_api, auth_headers, transaction=token, product="natal")
    second = _verify(store_api, auth_headers, transaction=token, product="natal")

    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == "granted natal"
    assert second.json()["status"] == "already_claimed"
    # The second answer still tells the client what it holds, because the client
    # asking twice is usually a client that lost its state rather than one
    # cheating — and answering "no" to a restore is answering wrongly.
    assert second.json()["unlocked"] == ["natal"]

    async def _rows():
        async with session_factory()() as session:
            grants = (await session.execute(select(Entitlement))).scalars().all()
            money = (await session.execute(select(Purchase))).scalars().all()
            return len(grants), len(money)

    assert read_async(_rows) == (1, 1)


def test_a_transaction_already_claimed_by_another_account_grants_nothing(
    store_api, auth_headers, apple
):
    """Two Alma accounts on one Apple ID. The first one wins.

    The safe direction, and knowingly not the kind one: somebody who reinstalls
    and gets a fresh guest account restores a purchase that belongs to the old
    one and is told they hold nothing. The fix is account linking, not a second
    grant — see `open_problems`.
    """
    token = _sign(_transaction(product="natal"), apple["key"], apple["chain"])
    _verify(store_api, auth_headers, transaction=token, product="natal")

    other = _second_account(store_api)
    response = _verify(store_api, other, transaction=token, product="natal")

    assert response.status_code == 200
    assert response.json()["status"] == "already_claimed"
    assert response.json()["unlocked"] == []
    assert _held(store_api, other)["unlocked"] == []


# ══════════════════════════════════════════════════════════════════════════
#  Refusals
# ══════════════════════════════════════════════════════════════════════════

def test_a_forged_transaction_is_a_401(store_api, auth_headers, apple):
    forged = _sign(_transaction(), apple["rogue_key"], apple["rogue_chain"])
    response = _verify(store_api, auth_headers, transaction=forged, product="natal")

    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_transaction"
    assert _held(store_api, auth_headers)["unlocked"] == []


def test_another_apps_purchase_is_a_401(store_api, auth_headers, apple):
    """A real Apple signature over a real purchase of somebody else's product."""
    token = _sign(_transaction(bundle="com.someone.else"), apple["key"], apple["chain"])
    response = _verify(store_api, auth_headers, transaction=token, product="natal")

    assert response.status_code == 401
    assert _held(store_api, auth_headers)["unlocked"] == []


def test_claiming_the_archive_for_a_door_is_a_409(store_api, auth_headers, apple):
    """The store equivalent of the price check, at the endpoint.

    $5.99 paid, $38.99 claimed. Nothing is granted and nothing is recorded.
    """
    token = _sign(_transaction(product="natal"), apple["key"], apple["chain"])
    response = _verify(store_api, auth_headers, transaction=token, product="archive")

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "product_mismatch"
    assert _held(store_api, auth_headers)["unlocked"] == []


def test_a_revoked_transaction_is_a_409_rather_than_a_401(store_api, auth_headers, apple):
    """A refunded purchase re-presented. The signature is perfect; Apple says no.

    Separated from the forgery because the two are different incidents with
    different answers — one is an attack worth an alert, the other is a person
    whose refund went through.
    """
    token = _sign(_transaction(revoked=True), apple["key"], apple["chain"])
    response = _verify(store_api, auth_headers, transaction=token, product="natal")

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "purchase_incomplete"


def test_a_product_we_do_not_sell_is_a_404(store_api, auth_headers, apple):
    token = _sign(_transaction(), apple["key"], apple["chain"])
    response = _verify(store_api, auth_headers, transaction=token, product="tarot")
    assert response.status_code == 404


def test_a_platform_this_build_does_not_ship_is_a_400(store_api, auth_headers):
    response = _verify(
        store_api, auth_headers, transaction="x", product="natal", platform="amazon"
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unknown_platform"


def test_a_card_processor_is_refused_by_name(store_api, auth_headers):
    """`paddle` is a processor this build ships and is not a store.

    A separate refusal from "we do not ship that", because the two send whoever
    is reading the log to different places: one is a typo in a client, the other
    is a client that thinks a webhook-based processor takes purchases from a
    device.
    """
    response = _verify(
        store_api, auth_headers, transaction="x", product="natal", platform="paddle"
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "not_a_store"


def test_a_store_with_no_credentials_is_a_503(api, auth_headers, apple):
    """Not a refusal of the buyer. A 503 says try again; a 401 says you cheated.

    `api` rather than `store_api`: no `APPLE_BUNDLE_ID` at all, which is the
    state a half-finished deploy is in.
    """
    token = _sign(_transaction(), apple["key"], apple["chain"])
    response = _verify(api, auth_headers, transaction=token, product="natal")

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "billing_unavailable"
    assert "APPLE_BUNDLE_ID" in response.json()["detail"]["message"]


# ══════════════════════════════════════════════════════════════════════════
#  The notification behind the purchase
# ══════════════════════════════════════════════════════════════════════════

def _notify(api, body: dict):
    import json

    return api.post("/v1/billing/webhook", content=json.dumps(body).encode())


def test_a_notification_for_a_purchase_already_verified_grants_nothing_more(
    notified_api, auth_headers, apple
):
    """Both routes end at one grant, which is why they share `_ingest`.

    The app verifies the moment the sheet closes and Apple's notification lands
    afterwards. Two ids — `appstore:<transactionId>` and the `notificationUUID` —
    so insert-before-process does not collapse them, and it is
    `entitlements.grant`'s own per-transaction idempotency that has to.
    """

    from sqlalchemy import select

    from alma.db.models import Entitlement
    from alma.db.session import session_factory

    transaction = _transaction(product="natal")
    _verify(
        notified_api,
        auth_headers,
        transaction=_sign(transaction, apple["key"], apple["chain"]),
        product="natal",
    )
    response = _notify(
        notified_api, _notification(apple, kind="ONE_TIME_CHARGE", transaction=transaction)
    )

    assert response.status_code == 200

    async def _count():
        async with session_factory()() as session:
            return len((await session.execute(select(Entitlement))).scalars().all())

    assert read_async(_count) == 1
    assert _held(notified_api, auth_headers)["unlocked"] == ["natal"]


def test_a_renewal_extends_the_plan_it_belongs_to(notified_api, auth_headers, apple):
    """One row, extended in place, found by the id every renewal shares.

    Keyed on the transaction it would be one row a month — and a cancellation
    would then catch only the last of them, leaving the earlier rows with future
    expiry dates and still granting what had just been cancelled.
    """

    from sqlalchemy import select

    from alma.db.models import Entitlement
    from alma.db.session import session_factory

    plan = dict(
        product="monthly",
        kind="Auto-Renewable Subscription",
        original="2000000500000020",
        price=9990,
        expires_in_days=31,
    )
    _verify(
        notified_api,
        auth_headers,
        transaction=_sign(
            _transaction(transaction_id="2000000500000020", **plan),
            apple["key"],
            apple["chain"],
        ),
        product="monthly",
    )

    async def _plan():
        async with session_factory()() as session:
            rows = (await session.execute(select(Entitlement))).scalars().all()
            return [(row.subscription_id, row.expires_at) for row in rows]

    before = read_async(_plan)
    assert len(before) == 1 and before[0][0] == "2000000500000020"

    response = _notify(
        notified_api,
        _notification(
            apple,
            kind="DID_RENEW",
            transaction=_transaction(transaction_id="2000000500000021", **plan),
            uuid="8ad5a2f0-0000-4000-8000-00000000aaaa",
        ),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "granted *"

    after = read_async(_plan)
    assert len(after) == 1, "a renewal must extend the row, not write a second one"
    assert after[0][1] > before[0][1]


def test_a_cancellation_leaves_the_paid_period_alone(notified_api, auth_headers, apple):
    """The most expensive rule in the file, checked end to end.

    Somebody who turns auto-renewal off has paid through the end of the period.
    `expires_at` must not move; only `renews_at` — the promise to charge — is
    withdrawn, so the account screen stops saying a charge is coming.
    """

    from sqlalchemy import select

    from alma.db.models import Entitlement
    from alma.db.session import session_factory

    plan = dict(
        product="monthly",
        kind="Auto-Renewable Subscription",
        original="2000000500000030",
        price=9990,
        expires_in_days=31,
    )
    _verify(
        notified_api,
        auth_headers,
        transaction=_sign(
            _transaction(transaction_id="2000000500000030", **plan),
            apple["key"],
            apple["chain"],
        ),
        product="monthly",
    )

    async def _plan():
        async with session_factory()() as session:
            row = (await session.execute(select(Entitlement))).scalars().first()
            return row.expires_at, row.renews_at, row.revoked_at

    expiry_before, renews_before, _ = read_async(_plan)
    assert renews_before is not None

    _notify(
        notified_api,
        _notification(
            apple,
            kind="DID_CHANGE_RENEWAL_STATUS",
            subtype="AUTO_RENEW_DISABLED",
            transaction=_transaction(transaction_id="2000000500000031", **plan),
            uuid="8ad5a2f0-0000-4000-8000-00000000bbbb",
        ),
    )

    expiry_after, renews_after, revoked = read_async(_plan)
    assert expiry_after == expiry_before, "cancelling is not refunding"
    assert revoked is None
    assert renews_after is None
    assert _held(notified_api, auth_headers)["unlocked"] == sorted(
        ["transits", "solar-return", "compatibility"]
    )


def test_a_refund_closes_what_it_paid_for(notified_api, auth_headers, apple):
    """The one notification that does take access away.

    And it has to find the purchase it undoes from our own rows, because a
    refund carries none of our metadata — nothing does on a store.
    """
    transaction = _transaction(product="natal")
    _verify(
        notified_api,
        auth_headers,
        transaction=_sign(transaction, apple["key"], apple["chain"]),
        product="natal",
    )
    assert _held(notified_api, auth_headers)["unlocked"] == ["natal"]

    response = _notify(
        notified_api,
        _notification(
            apple,
            kind="REFUND",
            transaction=transaction,
            uuid="8ad5a2f0-0000-4000-8000-00000000cccc",
        ),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "revoked 1"
    assert _held(notified_api, auth_headers)["unlocked"] == []


def test_an_unsigned_notification_is_refused(notified_api):
    """No shared secret, and still nothing unverified gets in.

    The signature is inside the body here rather than in a header, which is the
    honest inversion: a card processor signs the bytes it sends with a key we
    share, and Apple sends a document that signs itself with a key only Apple
    has.
    """
    import json

    body = {"notificationType": "REFUND", "notificationUUID": "u", "data": {}}
    response = notified_api.post(
        "/v1/billing/webhook", content=json.dumps({"signedPayload": "not.a.jws"}).encode()
    )
    assert response.status_code == 401
    assert notified_api.post(
        "/v1/billing/webhook", content=json.dumps(body).encode()
    ).status_code == 401


# ══════════════════════════════════════════════════════════════════════════
#  Cancelling, which the store does and we do not
# ══════════════════════════════════════════════════════════════════════════

def test_cancelling_a_store_subscription_hands_back_a_link(
    notified_api, auth_headers, apple
):
    """409 and a URL, not 502 and an apology. Nothing failed and nothing changed.

    Writing `renews_at = None` here would tell the account screen the plan had
    stopped renewing while Apple went on charging for it, and the person would
    find out on a statement.
    """

    from sqlalchemy import select

    from alma.db.models import Entitlement
    from alma.db.session import session_factory

    _verify(
        notified_api,
        auth_headers,
        transaction=_sign(
            _transaction(
                product="monthly",
                transaction_id="2000000500000040",
                kind="Auto-Renewable Subscription",
                price=9990,
                expires_in_days=31,
            ),
            apple["key"],
            apple["chain"],
        ),
        product="monthly",
    )

    response = notified_api.post("/v1/billing/subscription/cancel", headers=auth_headers)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "cancel_at_store"
    assert detail["manage_url"].startswith("https://apps.apple.com/")

    async def _plan():
        async with session_factory()() as session:
            row = (await session.execute(select(Entitlement))).scalars().first()
            return row.renews_at, row.status

    renews_at, status = read_async(_plan)
    assert renews_at is not None, "nothing may be written when nothing was cancelled"
    assert status != "cancelled"


def test_the_catalogue_publishes_where_to_cancel(notified_api, auth_headers):
    """The settings screen reads it before it draws a button.

    An app that only *says* "cancel in Settings" fails review under the same
    guideline that requires selling through StoreKit.
    """
    listing = notified_api.get("/v1/billing/catalogue", headers=auth_headers).json()
    assert listing["provider"] == "appstore"
    assert listing["merchant"] == "Apple"
    assert listing["manage_url"] == "https://apps.apple.com/account/subscriptions"


# ══════════════════════════════════════════════════════════════════════════
#  A subscription's first period, which arrives twice for one payment
# ══════════════════════════════════════════════════════════════════════════

def test_the_first_period_of_a_plan_is_granted_once_not_twice(
    notified_api, auth_headers, apple
):
    """The one-time door was covered; the subscription was not, and it was wrong.

    A subscription bought in the app is reported to us twice under two different
    idempotency keys — `appstore:<transactionId>` from `/iap/verify` the moment
    the sheet closes, and `notificationUUID` from Apple's own SUBSCRIBED
    notification a few seconds later. `webhook_event.id` cannot collapse them, so
    both reach `entitlements.grant`, and the subscription branch used to extend
    `expires_at` by a whole period on every call with no per-transaction guard.
    Every subscriber got two months for one month's money, silently: the
    `Purchase` row deduped correctly, so the money trail looked right and only
    the expiry date was a month too far out.
    """

    from sqlalchemy import select

    from alma.db.models import Entitlement
    from alma.db.session import session_factory

    plan = dict(
        product="monthly",
        transaction_id="2000000500000060",
        kind="Auto-Renewable Subscription",
        original="2000000500000060",
        price=9990,
        expires_in_days=31,
    )
    transaction = _transaction(**plan)

    _verify(
        notified_api,
        auth_headers,
        transaction=_sign(transaction, apple["key"], apple["chain"]),
        product="monthly",
    )

    async def _expiry():
        async with session_factory()() as session:
            rows = (await session.execute(select(Entitlement))).scalars().all()
            return [row.expires_at for row in rows]

    after_verify = read_async(_expiry)
    assert len(after_verify) == 1

    # The *same* transaction, arriving the way Apple sends it.
    response = _notify(
        notified_api,
        _notification(
            apple,
            kind="SUBSCRIBED",
            subtype="INITIAL_BUY",
            transaction=transaction,
            uuid="8ad5a2f0-0000-4000-8000-00000000bbbb",
        ),
    )
    assert response.status_code == 200

    after_notification = read_async(_expiry)
    assert len(after_notification) == 1, "still one plan"
    assert after_notification[0] == after_verify[0], (
        "one payment buys one month: the notification replaying the transaction "
        "that was already verified must not extend the plan a second time"
    )


# ══════════════════════════════════════════════════════════════════════════
#  A conditional price claimed by somebody who has not earned it
# ══════════════════════════════════════════════════════════════════════════

def test_a_conditional_price_claimed_without_qualifying_grants_nothing(
    store_api, auth_headers, apple, caplog
):
    """`archive-upgrade` is the shelf price less a door already paid for.

    This test used to assert the opposite of what it asserts now, and the
    change is worth explaining rather than hiding in a diff. Its old name was
    `..._is_not_silent`, and its old body accepted the everything-grant so long
    as a warning was logged beside it — on the argument that Apple has already
    taken the money by the time this runs, so refusing is payment collected for
    nothing.

    Half of that argument is right and it is kept: the money is not refused.
    The event is ingested, the payment is recorded, the transaction id is filed
    so a replay cannot try again, and the response is a 200.

    The other half conflated two separable decisions. Taking the payment does
    not oblige us to write the grant, and writing it meant $33.00 bought the
    $38.99 archive on a first purchase — the exact exploit `may_be_offered`
    exists to close, closed on the web checkout and left open on the two
    platforms where the store will sell any product id that exists.

    So the grant is refused and the buyer is made whole by the store rather than
    by us: neither client can see what it expected in `unlocked`, so neither
    acknowledges the purchase, and Google refunds an unacknowledged purchase
    after three days. See `tests/test_billing_iap_attack.py`, which pins the
    same rule from the attacker's side.
    """
    import logging

    token = _sign(_transaction(product="archive-upgrade"), apple["key"], apple["chain"])

    with caplog.at_level(logging.WARNING, logger="alma.api.routers.billing"):
        response = _verify(
            store_api, auth_headers, transaction=token, product="archive-upgrade"
        )

    assert response.status_code == 200, "the money moved; it is not refused"
    body = response.json()
    assert body["status"] == "not_offered", body
    assert body["unlocked"] == [], (
        "an account holding no door bought archive-upgrade and was granted "
        f"{body['unlocked']}"
    )
    assert any(
        "without qualifying" in record.getMessage() for record in caplog.records
    ), "a discount nobody earned must not be silent"

    held = store_api.get("/v1/billing/entitlements", headers=auth_headers).json()
    assert held["unlocked"] == [], held
