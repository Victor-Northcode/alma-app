"""What a person who wants free entitlements can actually get out of the store
route, and the one thing the Android client cannot get out of it at all.

These are deliberately separate from `test_billing_iap.py`, which pins the
contract as it is meant to work. Everything here fails today. Each test says
what it would cost if it stayed failing, because a red test with no consequence
attached gets deleted by the next person who is in a hurry.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from test_billing_appstore import (  # noqa: F401 - `apple` is a fixture
    BUNDLE,
    _sign,
    _transaction,
    apple,
)


@pytest.fixture
def store_api(api, monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("APPLE_BUNDLE_ID", BUNDLE)
    config_module.settings.cache_clear()
    yield api
    config_module.settings.cache_clear()


def _verify(api, headers, *, transaction: str, product: str, platform: str = "appstore"):
    return api.post(
        "/v1/billing/iap/verify",
        json={"platform": platform, "product": product, "transaction": transaction},
        headers=headers,
    )


# ══════════════════════════════════════════════════════════════════════════
#  The conditional price, bought by somebody who never earned it
# ══════════════════════════════════════════════════════════════════════════


def test_archive_upgrade_is_refused_to_an_account_holding_no_door(
    store_api, auth_headers, apple
):
    """$33.00 must not buy the $38.99 archive for a first-time buyer.

    `archive-upgrade` is the shelf price *less a door already paid for*. It
    writes the identical everything-grant the archive writes, so an account
    that never bought a door and buys the upgrade directly has bought the
    archive at $5.99 off.

    Both store clients refuse to open a sheet for it unless the server put it
    on their own catalogue — but that is a client-side lock on a product id
    that exists in the console regardless, which is exactly the class of rule
    `may_be_offered` was written to stop trusting the client about. Today the
    router calls `may_be_offered` and only *logs* when it answers False.

    The grant is the thing to refuse, not the money: the store has already
    taken it by the time this runs, so the honest server answer is to keep the
    payment, grant the credit the buyer is actually entitled to (nothing wider
    than a door), and reconcile — never to write the everything-grant.
    """
    token = _sign(
        _transaction(product="archive-upgrade", transaction_id="2000000500009001", price=33000),
        apple["key"],
        apple["chain"],
    )
    response = _verify(store_api, auth_headers, transaction=token, product="archive-upgrade")

    unlocked = store_api.get("/v1/billing/entitlements", headers=auth_headers).json()["unlocked"]
    assert len(unlocked) < 8, (
        "an account with no door bought archive-upgrade and now holds "
        f"everything: {unlocked} (verify answered {response.status_code} "
        f"{response.json()})"
    )


def test_archive_bump_is_refused_outright(store_api, auth_headers, apple):
    """$29.99 must never buy the archive, in any account state.

    `archive-bump` is priced to exist only as the second line of another
    checkout — 599 + 2999 is a cent under the shelf — and `may_be_offered`
    says it is *never* offerable on its own. A store has no equivalent of an
    in-checkout upsell, so if the id is ever created in the console this is
    the only thing between it and a direct purchase of the archive at nine
    dollars off. The Android client refuses it twice (`StoreProducts.NEVER_ALONE`,
    checked again inside `PlayBilling.purchase`) and neither of those refusals
    survives a repackaged APK.
    """
    token = _sign(
        _transaction(product="archive-bump", transaction_id="2000000500009002", price=29990),
        apple["key"],
        apple["chain"],
    )
    response = _verify(store_api, auth_headers, transaction=token, product="archive-bump")

    unlocked = store_api.get("/v1/billing/entitlements", headers=auth_headers).json()["unlocked"]
    assert len(unlocked) < 8, (
        "archive-bump bought on its own granted the whole archive: "
        f"{unlocked} (verify answered {response.status_code} {response.json()})"
    )


# ══════════════════════════════════════════════════════════════════════════
#  The platform name the Android client actually sends
# ══════════════════════════════════════════════════════════════════════════

_MOBILE = Path(__file__).resolve().parents[2] / "mobile"


def _platform_literal(source: Path) -> str:
    """The `platform` value a client hardcodes into its verify body."""
    text = source.read_text()
    match = re.search(r"platform\s*[:=]\s*\"([a-z]+)\"", text)
    assert match is not None, f"no platform literal found in {source}"
    return match.group(1)


@pytest.mark.parametrize(
    "source",
    [
        _MOBILE / "android/app/src/main/kotlin/ai/pazl/alma/data/AlmaClient.kt",
        _MOBILE / "ios/Alma/Billing/BillingAPI.swift",
    ],
    ids=["android", "ios"],
)
def test_the_platform_name_each_client_sends_resolves_to_an_adapter(source):
    """A store name this backend does not answer is money taken for nothing.

    `_store_adapter` resolves the adapter from the request rather than from
    `ALMA_BILLING_PROVIDER`, because one deployment answers both apps. The
    names it knows are the ones `provider_for` branches on — `appstore` and
    `googleplay`. Anything else is a 400 before Google is ever asked, on every
    retry, forever: the purchase is never acknowledged, so Google refunds it
    three days later and the person who paid spends those three days looking
    at a locked chapter.

    Checked against the client source rather than against a list written here,
    because the failure this catches is precisely a client and a server that
    each look correct on their own.
    """
    from alma.billing.provider import BillingUnavailable, provider_for

    platform = _platform_literal(source)
    try:
        provider_for(platform)
    except BillingUnavailable as exc:
        pytest.fail(
            f"{source.name} sends platform={platform!r} and /v1/billing/iap/verify "
            f"answers 400 unknown_platform to it: {exc}"
        )


def test_the_store_refusals_are_distinguishable_from_a_dead_session(store_api, auth_headers):
    """`invalid_transaction` is a 401 and must not read as "sign in again".

    The Android classifier checks the `error` key before the status and then
    falls through to the status code. `invalid_transaction`, `product_mismatch`
    and `purchase_incomplete` are not in its list, so the first of them —
    a 401 — becomes `ApiFailure.Unauthenticated`, which everywhere else in the
    app means "the token was rejected". A screen that handles that generically
    signs somebody out because a purchase signature failed.

    This pins the shape the client has to be able to tell apart: the body of a
    store refusal always names itself in `detail.error`.
    """
    response = _verify(
        store_api, auth_headers, transaction="not-a-jws", product="natal"
    )
    detail = response.json()["detail"]
    assert isinstance(detail, dict), detail
    assert detail["error"] in {
        "invalid_transaction",
        "product_mismatch",
        "purchase_incomplete",
        "billing_unavailable",
    }, detail
