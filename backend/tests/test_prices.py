"""The price list, asserted against what we decided to charge.

A price is the one number in this codebase that a refactor must never be able
to move quietly, so most of this file is a second, independent copy of the
shelf. That duplication is deliberate: a golden test that derived its
expectations from `REGIONAL_CENTS` would pass for any table at all.

The rest asserts the rules the table has to obey — that five doors cost more
than the bundle, that the bundle costs less than a quarter of a year of the
plan, and that a product we do not sell in a currency is refused rather than
priced in dollars with the local symbol in front of it.

**Что отсюда убрано.** Треть файла проверяла кредитную лестницу: что апгрейд
равен полке минус дверь в каждой валюте, что решать в чекауте никогда не
хуже, что кредит подставляет товар вместо цены. Монетизация v3 сняла с
продажи `archive`, `archive-bump` и `archive-upgrade` целиком (ТЗ §2), так что
проверять нечего — не «пока нечего», а нечего. Тесты удалены, а не
закомментированы.
"""

from __future__ import annotations

import pytest

from alma.billing import catalogue as prices
from alma.billing.catalogue import NotSold, Product
from alma.calc import SYSTEMS

#: Every published amount, written out by hand. If a change to the mechanism
#: moves any of these, that is the test failing on purpose.
GOLDEN: dict[str, dict[str, int]] = {
    "USD": {"door": 499, "pair": 499, "bundle": 1999, "monthly": 999},
    "EUR": {"door": 549, "pair": 549, "bundle": 2099, "monthly": 1049},
    "GBP": {"door": 499, "pair": 499, "bundle": 1999, "monthly": 999},
    "CHF": {"door": 590, "pair": 590, "bundle": 2390, "monthly": 1190},
    "AUD": {"door": 799, "pair": 799, "bundle": 3199, "monthly": 1599},
    "CAD": {"door": 749, "pair": 749, "bundle": 2799, "monthly": 1399},
    "NOK": {"door": 5900, "pair": 5900, "bundle": 21900, "monthly": 10900},
    "DKK": {"door": 3900, "pair": 3900, "bundle": 15900, "monthly": 7900},
    "BRL": {"door": 1290, "pair": 1290, "bundle": 5190, "monthly": 2590},
    "MXN": {"door": 5900, "pair": 5900, "bundle": 21900, "monthly": 10900},
    "PLN": {"door": 1099, "pair": 1099, "bundle": 4399, "monthly": 2199},
    "TRY": {"door": 6900, "pair": 6900, "bundle": 25900, "monthly": 12900},
    "INR": {"door": 10900, "pair": 10900, "bundle": 43900, "monthly": 21900},
    # Рублёвая полоса — витрина «/pay» (Т-Банк, 30.08.2026). Четыре числа
    # выведены из долларовых по покупательной способности, и владелец их ещё
    # НЕ подтверждал: строка здесь прибивает выведенное, чтобы оно не поплыло
    # молча, а не выдаёт его за решённое. Подтвердит или поменяет — править
    # вместе с REGIONAL_CENTS в catalogue.py.
    "RUB": {"door": 49900, "pair": 49900, "bundle": 199900, "monthly": 99900},
}

#: Пять систем, которые продаются дверьми. Написаны руками по той же причине,
#: что и цены: список, взятый из каталога, подтвердил бы любой каталог.
STATIC = ("natal", "numerology", "birth-card", "astrocartography", "synthesis")

#: И три, которых на полке нет. Транзиты и соляр пересчитываются, поэтому
#: продаются только подпиской; совместимость покупается на человека.
NOT_A_DOOR = ("transits", "solar-return", "compatibility")


def _cents(currency: str, band: str) -> int:
    """What we charge, through the mechanism the application uses."""
    item = next(p for p in prices.PRODUCTS.values() if p.band == band)
    return item.cents_in(currency)


# ── the shelf, pinned ──────────────────────────────────────────────────────

def test_the_shelf_is_the_eight_rows_v3_decided_on():
    assert list(prices.PRODUCTS) == [
        "door.natal",
        "door.numerology",
        "door.birth-card",
        "door.astrocartography",
        "door.synthesis",
        "pair.check",
        "bundle.static",
        "sub.monthly",
    ]


@pytest.mark.parametrize("currency", sorted(GOLDEN))
def test_every_published_price_is_the_price_we_decided(currency: str):
    for band, expected in GOLDEN[currency].items():
        assert _cents(currency, band) == expected, f"{currency} {band} moved"


def test_no_currency_carries_a_price_we_did_not_decide():
    """The golden table is exhaustive, so a new price cannot appear unpinned."""
    published = {
        currency: dict(table) for currency, table in prices.REGIONAL_CENTS.items()
    }
    published["USD"] = {
        item.band: item.cents for item in prices.PRODUCTS.values()
    }
    assert published == GOLDEN


def test_the_door_is_one_price_for_every_system():
    """A price that varied by system would vary by quiz answer."""
    doors = {
        key: item for key, item in prices.PRODUCTS.items() if item.band == "door"
    }
    assert len(doors) == 5
    assert {item.cents for item in doors.values()} == {499}
    assert {item.scope for item in doors.values()} == {"system"}
    assert {item.slug for item in doors.values()} == set(STATIC)


def test_the_three_systems_that_move_have_no_door():
    """Разбор, который пересчитывается, проданный «навсегда», — это подписка,
    за которую забыли брать деньги. Совместимость продаётся `pair.check`, то
    есть на конкретного человека, а не системой."""
    doors = {item.slug for item in prices.PRODUCTS.values() if item.band == "door"}
    for system in NOT_A_DOOR:
        assert system not in doors, f"{system} is being sold as a permanent door"
    assert set(STATIC) | set(NOT_A_DOOR) == set(SYSTEMS)


def test_every_system_names_the_one_thing_that_opens_it():
    """Экран закрытой главы обязан назвать цену — любой главы любой системы.

    `catalogue.unlocks` — то самое место, откуда роут глав берёт SKU для стены
    (`locked-chapter-spec.md` §1). Система, для которой оно падает, — это 500
    вместо пейволла; система, для которой оно врёт, — это кнопка «$4.99
    навсегда» над транзитами, которые разово не продаются вовсе.

    Проверяется по видам товара, а не по именам ключей: имена — дело полки, а
    вид («навсегда», «подписка», «на человека») — обещание, которое стоит под
    кнопкой и которое нельзя перепутать.
    """
    for system in SYSTEMS:
        key = prices.unlocks(system)
        item = prices.PRODUCTS[key]
        if system in NOT_A_DOOR and system != "compatibility":
            assert item.interval, f"{system} moves and must be sold as a subscription"
        elif system == "compatibility":
            assert item.kind == "consumable", "пара покупается на человека"
        else:
            assert item.band == "door" and item.slug == system

    with pytest.raises(ValueError):
        prices.unlocks("palmistry")


def test_a_catalogue_key_is_never_mistaken_for_a_system_slug():
    """В v3 они разошлись, и это единственная причина, по которой
    `store_product_id` даёт `ai.pazl.alma.door.natal`, а не `…alma.natal`.
    Слаг, случайно оказавшийся ключом, — это покупка, которая верифицируется и
    не выдаёт ничего."""
    for system in SYSTEMS:
        assert system not in prices.PRODUCTS, (
            f"{system!r} is both a system and a catalogue key again"
        )
    for key in prices.PRODUCTS:
        assert "." in key, f"{key} does not name what kind of product it is"


# ── the rules the table has to obey ────────────────────────────────────────

def test_five_doors_cost_more_than_the_bundle_in_every_market():
    """Иначе бандл бессмыслен: платить за пять по одной было бы дешевле, а
    «скидка 20%» в копирайте — неправдой, за которую снимают с полки."""
    for currency, table in GOLDEN.items():
        assert table["door"] * 5 > table["bundle"], currency


def test_the_bundle_costs_less_than_three_months_of_the_plan():
    """Иначе он не якорь. Бандл существует, чтобы подписка читалась дёшево, а
    не чтобы быть второй подпиской, купленной одним платежом."""
    for currency, table in GOLDEN.items():
        assert table["bundle"] < table["monthly"] * 3, currency


def test_the_pair_costs_the_same_as_a_door():
    """Одна цена импульса: и дверь, и проверка пары продаются в момент
    «зацепило», и разная цена на двух таких экранах читается как ошибка."""
    for currency, table in GOLDEN.items():
        assert table["pair"] == table["door"], currency


def test_the_shelf_climbs_in_every_currency():
    for currency, table in GOLDEN.items():
        rungs = [table["door"], table["monthly"], table["bundle"]]
        assert rungs == sorted(rungs), currency


def test_every_market_is_offered_the_whole_shelf():
    """PPP-рынки впервые получают всё. Прежний отказ держался на фиксированной
    комиссии за транзакцию, которой у магазинов нет: доля, которая остаётся
    нам, одинакова и на R$12.90, и на R$99.90."""
    for currency in prices.REGIONAL_CENTS:
        offered = {
            key for key, item in prices.PRODUCTS.items() if item.sold_in(currency)
        }
        assert offered == set(prices.PRODUCTS), currency


# ── a product we do not sell is refused, never priced in dollars ───────────

def test_an_unpriced_currency_refuses_rather_than_answering_in_dollars():
    """Sweden is not priced. Asking for a Swedish price must not return 499."""
    assert "SEK" not in prices.REGIONAL_CENTS
    with pytest.raises(NotSold):
        prices.PRODUCTS["bundle.static"].cents_in("SEK")
    assert prices.PRODUCTS["bundle.static"].sold_in("SEK") is False


def test_a_band_nobody_priced_cannot_borrow_the_us_amount():
    """The structural half: absence is refusal wherever it occurs, not just
    where we happened to write a test."""
    unpriced = Product("*", "Something new", "one_time", 1234, band="tarot-deck")
    assert unpriced.cents_in("USD") == 1234
    for currency in prices.REGIONAL_CENTS:
        with pytest.raises(NotSold):
            unpriced.cents_in(currency)


def test_every_country_we_bill_has_a_price_list_and_a_way_to_write_it():
    """Switzerland was reachable and unpriced, so Swiss buyers paid raw USD."""
    for country, currency in prices.COUNTRY_CURRENCY.items():
        assert currency in prices.REGIONAL_CENTS, f"{country} bills in unpriced {currency}"
        assert currency in prices.CURRENCY_FORMAT, f"{currency} has no notation"
    assert prices.currency_for("CH") == "CHF"


# ── a price a human would recognise ────────────────────────────────────────

def test_every_currency_renders_a_price_its_readers_would_recognise():
    bundle = prices.PRODUCTS["bundle.static"]
    assert bundle.display("USD") == "$19.99"
    assert bundle.display("EUR") == "€20,99"
    assert bundle.display("GBP") == "£19.99"
    assert bundle.display("CHF") == "CHF 23.90"
    assert bundle.display("AUD") == "A$31.99"
    assert bundle.display("CAD") == "C$27.99"
    assert bundle.display("NOK") == "kr 219"
    assert bundle.display("DKK") == "kr 159"
    assert bundle.display("BRL") == "R$ 51,90"
    assert bundle.display("MXN") == "MX$219"
    assert bundle.display("PLN") == "43,99 zł"
    assert bundle.display("TRY") == "₺259"
    assert bundle.display("INR") == "₹439"


def test_the_symbol_goes_where_the_market_puts_it():
    """A Pole shown "zł43,99" is being shown a currency on the wrong end."""
    assert prices.format_price(4399, "PLN").endswith("zł")
    assert prices.format_price(4399, "EUR").startswith("€")


def test_an_unknown_currency_still_says_which_currency_it_is():
    """A bare number is worse than a wrong symbol: nothing about it looks wrong."""
    assert prices.format_price(1499, "SEK") == "SEK 14.99"


def test_the_old_rounding_machine_could_not_have_produced_this_shelf():
    """Why the multiplier architecture had to go, stated as a fact.

    `_to_price_point` snaps anything between ten and two hundred units onto an
    x9.90 ending, so the bundle at 1999 comes back as 1990 — a price nobody
    chose, three doors' worth of margin away from one that was.
    """
    assert prices._to_price_point(1999) != 1999
    assert prices._to_price_point(2099) != 2099


# ── what a client is given ─────────────────────────────────────────────────

def test_every_price_published_is_a_price_a_price_id_can_take():
    """Nothing in the list is computed out of another number.

    The list used to publish `payable_cents` — a price minus a credit — while
    the checkout opened the overlay against the full price id, so two shipped
    surfaces stated an amount that would never be charged. Every entry now
    names a catalogue key, and its `cents` is that key's own amount in that
    currency.
    """
    for currency, country in (("USD", "US"), ("EUR", "DE"), ("BRL", "BR")):
        listing = prices.catalogue(country=country)
        for item in listing["items"]:
            assert item["cents"] == prices.PRODUCTS[item["slug"]].cents_in(currency)
            assert "payable_cents" not in item
            assert "credit_cents" not in item


def test_a_recurring_plan_is_never_rendered_as_a_single_payment():
    """The defect this replaced: the list filtered the annual out and carried
    no interval, so the first monthly plan added would have been drawn as a
    one-time purchase."""
    listing = prices.catalogue()
    plan = next(item for item in listing["items"] if item["slug"] == "sub.monthly")
    assert (plan["kind"], plan["interval"]) == ("monthly", "month")
    for item in listing["items"]:
        if item["kind"] != "monthly":
            assert item["interval"] == "", item["slug"]


def test_the_list_is_whatever_is_on_the_shelf_rather_than_a_hardcoded_shape():
    listing = prices.catalogue()
    assert [item["slug"] for item in listing["items"]] == [
        key for key, item in prices.PRODUCTS.items() if item.on_the_shelf
    ]


def test_the_catalogue_carries_the_scope_each_row_grants():
    """Клиент рисует по нему разные вещи: `pair` — это отчёт про человека, а не
    система, и строка, пришедшая без scope, была бы нарисована дверью."""
    scopes = {
        item["slug"]: item["scope"] for item in prices.catalogue()["items"]
    }
    assert scopes["door.natal"] == "system"
    assert scopes["pair.check"] == "pair"
    assert scopes["bundle.static"] == "static"
    assert scopes["sub.monthly"] == "all"


def test_a_brazilian_is_shown_the_whole_shelf_in_reais():
    listing = prices.catalogue(country="BR")
    assert listing["currency"] == "BRL"
    assert len(listing["items"]) == 8
    plan = next(item for item in listing["items"] if item["slug"] == "sub.monthly")
    assert plan["display"] == "R$ 25,90"


def test_the_catalogue_no_longer_publishes_an_annual_alias():
    """Ключ-алиас `annual` показывал ту же строку вторым именем и уходит вместе
    с годовой подпиской. Оставленный пустым он читался бы как «план не
    продаётся» на витрине, где план — единственная подписка."""
    assert "annual" not in prices.catalogue()


# ── the subscription ───────────────────────────────────────────────────────

def test_the_subscription_sells_everything_while_it_lasts():
    """`live` был про то, что подписка снимала только движущееся. В v3 она
    продаёт всё, и строка «купленное навсегда остаётся твоим» в P5 существует
    именно потому, что `all` истекает, а `system` и `static` — нет."""
    plan = prices.PRODUCTS["sub.monthly"]
    assert plan.scope == "all"
    assert plan.interval == "month"
    assert plan.pair_credits_monthly == 1


def test_only_the_subscription_carries_a_pair_credit():
    """«Одна проверка в месяц» — обещание подписки. Кредит на разовом товаре
    был бы обещанием, которое никто не сбрасывает."""
    for key, item in prices.PRODUCTS.items():
        if key == "sub.monthly":
            continue
        assert item.pair_credits_monthly == 0, key


def test_the_living_systems_are_still_named_for_the_daily_note():
    """Список остался, хотя подписка больше не «только живое»: на нём держатся
    гранты `scope="live"` и утренняя заметка."""
    assert prices.LIVING_SYSTEMS <= set(SYSTEMS)
    assert prices.LIVING_SYSTEMS == {"transits", "solar-return", "compatibility"}
