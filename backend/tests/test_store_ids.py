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
catalogue **keys**, not over finished ids: the prefix has one home
(`settings().store_product_prefix`, mirrored by `LadderKey.prefix`,
`StoreProducts.PREFIX` and Flutter's `LadderKey.prefix`) and those are checked
against each other; everything else is checked key by key.

**Ключ каталога перестал быть слагом системы (монетизация v3).** До неё
`"natal"` был и товаром, и системой, и Android держал восемь системных
констант в `AlmaSystem` и пять «остальных» в `StoreProducts`. Теперь ключей
восемь и все восемь — товары: `door.natal`, `pair.check`, `bundle.static`,
`sub.monthly`. Отсюда две правки в разборе ниже: точка допущена в регулярках, а
`AlmaSystem.ALL` из сверки убран — систему больше нельзя купить по её имени.

Строк, которых *не должно* быть в магазинах, в v3 нет: условные цены
(`archive-bump`) сняты вместе с архивом. Проверка на их отсутствие удалена
вместе с ними — не потому, что правило смягчилось, а потому, что предмета нет;
правило «продаём только то, что на полке» живёт в `entitlements.may_be_offered`
и в его собственных тестах.
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
FLUTTER_LADDER = ROOT / "mobile/flutter/alma/lib/billing/ladder.dart"

#: Every file below lives in the mobile app rather than in this package, so a
#: checkout of the backend alone has nothing to read. Skipping is honest;
#: failing would train somebody to ignore a red suite.
requires_mobile = pytest.mark.skipif(
    not (LADDER_KEY.exists() and STORE_PRODUCTS.exists() and STOREKIT.exists()),
    reason="the mobile sources are not in this checkout",
)


def catalogue_keys() -> set[str]:
    return set(PRODUCTS)


def ladder_keys() -> set[str]:
    """The `case`s of `LadderKey`, whose raw value is the catalogue key.

    A case with no `= "…"` is its own name, which is why the fallback is the
    identifier — though in v3 every case carries a raw value, because no
    catalogue key is a legal Swift identifier any more.
    """
    source = LADDER_KEY.read_text()
    # Only the enum body: `var` and `func` below it mention no cases, but a
    # doc-comment further down might.
    body = source.split("enum LadderKey", 1)[1]
    found: set[str] = set()
    for name, raw in re.findall(r'^\s*case\s+(\w+)(?:\s*=\s*"([^"]+)")?', body, re.M):
        found.add(raw or name)
    return found


def flutter_keys() -> set[str]:
    """The values of Flutter's `LadderKey`, which is the third copy of the enum."""
    source = FLUTTER_LADDER.read_text()
    body = source.split("enum LadderKey {", 1)[1].split("\n}", 1)[0]
    return set(re.findall(r"^\s*\w+\('([a-z.\-]+)'", body, re.M))


def android_keys() -> set[str]:
    """Every catalogue key Android names.

    `AlmaSystem.ALL` is deliberately not folded in any more: a system slug is
    not a product, and `StoreProducts.productId("natal")` now produces an id no
    console has.
    """
    source = STORE_PRODUCTS.read_text()
    consts = set(re.findall(r'const val \w+: String = "([a-z.\-_]+)"', source))
    consts.discard(settings().store_product_prefix)  # PREFIX is not a key
    return consts


def android_all_set() -> set[str]:
    """What `StoreProducts.ALL` actually enumerates, by constant name."""
    source = STORE_PRODUCTS.read_text()
    block = re.search(r"val ALL: Set<String> =\s*(.+?)\n\n", source, re.S)
    assert block, "StoreProducts.ALL is no longer in the shape this test reads"
    names = set(re.findall(r"\b([A-Z][A-Z_]+)\b", block.group(1)))
    names.discard("ALL")
    literal = dict(re.findall(r'const val (\w+): String = "([a-z.\-_]+)"', source))
    return {literal[n] for n in names if n in literal}


def storekit_ids() -> set[str]:
    d = json.loads(STOREKIT.read_text())
    ids = {p["productID"] for p in d.get("products", [])}
    for group in d.get("subscriptionGroups", []):
        ids |= {s["productID"] for s in group.get("subscriptions", [])}
    ids |= {p["productID"] for p in d.get("nonRenewingSubscriptions", [])}
    return ids


def storekit_types() -> dict[str, str]:
    """Product id → StoreKit type, which is the half that cannot be changed
    after a product is saved in App Store Connect."""
    d = json.loads(STOREKIT.read_text())
    types = {p["productID"]: p["type"] for p in d.get("products", [])}
    for group in d.get("subscriptionGroups", []):
        for sub in group.get("subscriptions", []):
            types[sub["productID"]] = sub["type"]
    return types


def products_md_keys() -> set[str]:
    """The first column of the table in §1, which is the catalogue key."""
    rows = re.findall(r"^\|\s*`([a-z.\-]+)`\s*\|", PRODUCTS_MD.read_text(), re.M)
    return set(rows)


def id_for(key: str, prefix: str) -> str:
    """The rule, stated once here and three times in the apps: prefix, no hyphens."""
    return prefix + key.replace("-", "_")


@requires_mobile
def test_the_ios_ladder_knows_every_row_it_can_sell() -> None:
    assert ladder_keys() == catalogue_keys()


@requires_mobile
def test_the_flutter_ladder_knows_every_row_it_can_sell() -> None:
    assert flutter_keys() == catalogue_keys()


@requires_mobile
def test_the_android_constants_know_every_catalogue_row() -> None:
    assert android_keys() == catalogue_keys()


@requires_mobile
def test_androids_all_set_holds_what_it_says_it_holds() -> None:
    # It says: "Every key backend/alma/billing/catalogue.py knows."
    assert android_all_set() == catalogue_keys()


@requires_mobile
def test_the_storekit_file_carries_every_product_that_is_sold() -> None:
    prefix = settings().store_product_prefix
    expected = {id_for(key, prefix) for key in catalogue_keys()}
    assert storekit_ids() == expected


@requires_mobile
def test_the_pair_is_the_one_consumable_and_everything_else_is_not() -> None:
    """Тип необратим в момент сохранения товара, и обе ошибки стоят денег.

    Non-consumable на паре — это «одна пара на аккаунт навсегда», то есть
    отсутствие второй покупки вообще. Consumable на двери — это разбор, который
    исчезает из записей магазина после подтверждения: restore нечего вернуть, а
    человека можно взять деньги второй раз.
    """
    prefix = settings().store_product_prefix
    types = storekit_types()
    assert types[id_for("pair.check", prefix)] == "Consumable"
    for key, item in PRODUCTS.items():
        if key == "pair.check":
            continue
        expected = "RecurringSubscription" if item.interval else "NonConsumable"
        assert types[id_for(key, prefix)] == expected, key


@requires_mobile
def test_the_subscription_lives_in_the_group_it_has_to_live_in() -> None:
    """Одна группа `alma_access`: будущие weekly/annual (ТЗ §8, A/B после данных
    по удержанию) обязаны быть взаимозаменяемы с месячной, а товар, заведённый
    вне группы, переехать в группу потом не может."""
    d = json.loads(STOREKIT.read_text())
    groups = d.get("subscriptionGroups", [])
    assert len(groups) == 1
    assert groups[0]["name"] == "alma_access"
    assert [s["productID"] for s in groups[0]["subscriptions"]] == [
        id_for("sub.monthly", settings().store_product_prefix)
    ]


def test_the_sheet_somebody_types_from_lists_every_catalogue_row() -> None:
    # PRODUCTS.md is in the repository whether or not the apps are, so this one
    # is not skipped with the others.
    assert catalogue_keys() <= products_md_keys()


@requires_mobile
def test_the_prefix_has_one_value_in_three_places() -> None:
    prefix = settings().store_product_prefix
    assert f'static let prefix = "{prefix}"' in LADDER_KEY.read_text()
    assert f'const val PREFIX: String = "{prefix}"' in STORE_PRODUCTS.read_text()
    assert f"static const prefix = '{prefix}'" in FLUTTER_LADDER.read_text()
