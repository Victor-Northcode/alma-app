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
#  A price the server does not offer, bought by naming it
# ══════════════════════════════════════════════════════════════════════════


def test_a_price_that_is_not_on_the_shelf_grants_nothing(
    store_api, auth_headers, apple, monkeypatch
):
    """Магазин продаст любой идентификатор, заведённый в консоли.

    Здесь стояли два теста — `archive-upgrade` за $33.00 и `archive-bump` за
    $29.99, — и оба ловили одно: цена, которая выдаёт то же, что полочная, но
    стоит дешевле, купленная по имени тем, кто её не заслужил. Условных цен в v3
    нет, так что строка снимается с полки прямо здесь, ровно как её снимет
    первый A/B по цене бандла (ТЗ §7).

    Что проверяется — со стороны нападающего: клиентские фильтры
    (`Storefront.offers`, `StoreProducts.sellable`) решают только, что
    **нарисовано**, и ни один из них не переживает пересобранный APK. Единственное,
    что стоит между чужим идентификатором и грантом, — сервер.
    """
    import dataclasses

    from alma.billing import catalogue as prices

    monkeypatch.setitem(
        prices.PRODUCTS,
        "bundle.static",
        dataclasses.replace(prices.PRODUCTS["bundle.static"], offered="in-checkout"),
    )
    token = _sign(
        _transaction(
            product="bundle.static", transaction_id="2000000500009001", price=19990
        ),
        apple["key"],
        apple["chain"],
    )
    response = _verify(store_api, auth_headers, transaction=token, product="bundle.static")

    unlocked = store_api.get("/v1/billing/entitlements", headers=auth_headers).json()["unlocked"]
    assert unlocked == [], (
        "a price the server does not offer was bought by name and granted "
        f"{unlocked} (verify answered {response.status_code} {response.json()})"
    )


def test_a_withdrawn_product_id_grants_nothing(store_api, auth_headers, apple):
    """Идентификатор снятой полки, подписанный магазином, — реальный случай.

    Аккаунт в App Store может нести покупку товара из прежнего прайс-листа, а
    старая сборка приложения — попросить его по имени. Такой платёж надо
    записать и не выдать по нему ничего: `store_slug` отвечает `None` для
    ключа, которого нет в каталоге, и это единственное, что стоит между
    снятым SKU и грантом, который он когда-то выдавал.
    """
    token = _sign(
        _transaction(product="archive", transaction_id="2000000500009002", price=38990),
        apple["key"],
        apple["chain"],
    )
    _verify(store_api, auth_headers, transaction=token, product="archive")

    unlocked = store_api.get("/v1/billing/entitlements", headers=auth_headers).json()["unlocked"]
    assert unlocked == [], f"a withdrawn SKU still granted {unlocked}"


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
        store_api, auth_headers, transaction="not-a-jws", product="door.natal"
    )
    detail = response.json()["detail"]
    assert isinstance(detail, dict), detail
    assert detail["error"] in {
        "invalid_transaction",
        "product_mismatch",
        "purchase_incomplete",
        "billing_unavailable",
    }, detail
