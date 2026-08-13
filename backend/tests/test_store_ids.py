"""The product ids, asserted across all five places that name them.

**Why this file exists.** The weekly subscription was added to the catalogue,
to `LadderKey`, to `StoreProducts` and to the paywall on both platforms — and
was missing from `Alma.storekit` and from `mobile/store/PRODUCTS.md` for a day
without anything failing. `PRODUCTS.md` is the sheet somebody types from into
App Store Connect and the Play Console, so a row absent there is a product
nobody creates; `Alma.storekit` is what a local StoreKit test buys from, so a
product absent there cannot be bought before TestFlight either.

Neither absence announces itself. `Product.products(for:)` returns the ids the
store knows and silently omits the rest, so the paywall renders one row short
with no error in any log — and the same silence is what Apple answers with as
Guideline 2.1, *"we were unable to locate the in-app purchases"*, days later.

**What is compared, and what deliberately is not.** The comparison is over
catalogue *slugs*, not over finished ids. The prefix is still undecided —
`alma.` is what every binary asks for today and `PRODUCTS.md` §2 recommends
`ai.pazl.alma.` — and a test that pinned the finished string would fail the
moment that decision lands, which is exactly when nobody wants a red suite. The
prefix has one home (`settings().store_product_prefix`, mirrored by
`LadderKey.prefix` and `StoreProducts.PREFIX`) and those three are checked
against each other; everything else is checked slug by slug.

The one row that is *supposed* to be missing from the stores is
`archive-bump`: an in-checkout upsell that must never exist as a product
anybody can buy on its own. `PRODUCTS.md` says "do not create" and the storekit
file has no such id, and this file asserts that absence rather than tolerating
it, because the day it appears in a console is a day somebody can buy the
nine-dollar discount without the thirty-nine-dollar thing it discounts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from alma.billing.catalogue import PRODUCTS
from alma.config import settings

#: The repository root, from `backend/tests/` upward.
ROOT = Path(__file__).resolve().parents[2]

LADDER_KEY = ROOT / "mobile/ios/Alma/Billing/LadderKey.swift"
STORE_PRODUCTS = ROOT / "mobile/android/app/src/main/kotlin/ai/pazl/alma/billing/StoreProducts.kt"
STOREKIT = ROOT / "mobile/ios/Alma.storekit"
PRODUCTS_MD = ROOT / "mobile/store/PRODUCTS.md"

#: Sold through the two consoles, so it must exist in both store-facing files.
#: `archive-bump` is the one catalogue row with no product behind it: an upsell
#: inside another checkout, and there is no such thing when the store owns the
#: confirmation sheet. `LadderKey` says so in its own words and does not model
#: it; Android keeps a constant for it only to refuse it by name.
NEVER_A_STORE_PRODUCT = {"archive-bump"}

#: Where Android keeps the eight system slugs — not in `StoreProducts`, which
#: holds only the rows that are *not* a system.
ALMA_SYSTEM = ROOT / "mobile/android/app/src/main/kotlin/ai/pazl/alma/data/AlmaClient.kt"

#: Every file below lives in the mobile app rather than in this package, so a
#: checkout of the backend alone has nothing to read. Skipping is honest;
#: failing would train somebody to ignore a red suite.
requires_mobile = pytest.mark.skipif(
    not (LADDER_KEY.exists() and STORE_PRODUCTS.exists() and STOREKIT.exists()),
    reason="the mobile sources are not in this checkout",
)


def catalogue_slugs() -> set[str]:
    return set(PRODUCTS)


def ladder_slugs() -> set[str]:
    """The `case`s of `LadderKey`, whose raw value is the catalogue slug.

    A case with no `= "…"` is its own name, which is why the fallback is the
    identifier: `case natal` is the slug `natal`, `case birthCard = "birth-card"`
    is `birth-card`.
    """
    source = LADDER_KEY.read_text()
    # Only the enum body: `var` and `func` below it mention no cases, but a
    # doc-comment further down might.
    body = source.split("enum LadderKey", 1)[1]
    found: set[str] = set()
    for name, raw in re.findall(r'^\s*case\s+(\w+)(?:\s*=\s*"([^"]+)")?', body, re.M):
        found.add(raw or name)
    return found


def android_system_slugs() -> set[str]:
    """The eight systems, which live in `AlmaSystem` beside the client."""
    source = ALMA_SYSTEM.read_text()
    block = source.split("object AlmaSystem", 1)[-1]
    return set(re.findall(r'const val \w+ = "([a-z\-]+)"', block))


def android_slugs() -> set[str]:
    """Every slug Android names: the non-system rows plus the eight systems."""
    source = STORE_PRODUCTS.read_text()
    consts = set(re.findall(r'const val \w+: String = "([a-z\-_]+)"', source))
    consts.discard("alma.")  # PREFIX is not a slug
    return consts | android_system_slugs()


def android_all_set() -> set[str]:
    """What `StoreProducts.ALL` actually enumerates, by constant name."""
    source = STORE_PRODUCTS.read_text()
    block = re.search(r"val ALL: Set<String> =\s*(.+?)\n\n", source, re.S)
    assert block, "StoreProducts.ALL is no longer in the shape this test reads"
    names = set(re.findall(r"\b([A-Z][A-Z_]+)\b", block.group(1)))
    names.discard("ALL")
    literal = dict(re.findall(r'const val (\w+): String = "([a-z\-_]+)"', source))
    slugs = {literal[n] for n in names if n in literal}
    # `AlmaSystem.ALL` carries the eight systems; they are named there, not here.
    if "AlmaSystem" in block.group(1):
        slugs |= android_system_slugs()
    return slugs


def storekit_ids() -> set[str]:
    d = json.loads(STOREKIT.read_text())
    ids = {p["productID"] for p in d.get("products", [])}
    for group in d.get("subscriptionGroups", []):
        ids |= {s["productID"] for s in group.get("subscriptions", [])}
    ids |= {p["productID"] for p in d.get("nonRenewingSubscriptions", [])}
    return ids


def products_md_slugs() -> set[str]:
    """The first column of the table in §1, which is the catalogue slug."""
    rows = re.findall(r"^\|\s*`([a-z\-]+)`\s*\|", PRODUCTS_MD.read_text(), re.M)
    return set(rows)


def id_for(slug: str, prefix: str) -> str:
    """The rule, stated once here and twice in the apps: prefix, no hyphens."""
    return prefix + slug.replace("-", "_")


@requires_mobile
def test_the_ios_ladder_knows_every_row_it_can_sell() -> None:
    # Everything except the upsell, which the enum documents as deliberately
    # absent: a build that asked StoreKit for it would be asking for a product
    # that must never exist in App Store Connect.
    assert ladder_slugs() == catalogue_slugs() - NEVER_A_STORE_PRODUCT


@requires_mobile
def test_the_android_constants_know_every_catalogue_row() -> None:
    assert android_slugs() == catalogue_slugs()


@requires_mobile
def test_androids_all_set_holds_what_it_says_it_holds() -> None:
    # It says: "Every key backend/alma/billing/catalogue.py knows."
    assert android_all_set() == catalogue_slugs()


@requires_mobile
def test_the_storekit_file_carries_every_product_that_is_sold() -> None:
    prefix = settings().store_product_prefix
    expected = {id_for(s, prefix) for s in catalogue_slugs() - NEVER_A_STORE_PRODUCT}
    assert storekit_ids() == expected


@requires_mobile
def test_the_upsell_is_not_a_product_anybody_can_buy() -> None:
    prefix = settings().store_product_prefix
    for slug in NEVER_A_STORE_PRODUCT:
        assert id_for(slug, prefix) not in storekit_ids()


def test_the_sheet_somebody_types_from_lists_every_catalogue_row() -> None:
    # PRODUCTS.md is in the repository whether or not the apps are, so this one
    # is not skipped with the others.
    assert catalogue_slugs() <= products_md_slugs()


@requires_mobile
def test_the_prefix_has_one_value_in_three_places() -> None:
    prefix = settings().store_product_prefix
    assert f'static let prefix = "{prefix}"' in LADDER_KEY.read_text()
    assert f'const val PREFIX: String = "{prefix}"' in STORE_PRODUCTS.read_text()
