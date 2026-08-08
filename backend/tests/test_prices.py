"""The price list, asserted against what we decided to charge.

A price is the one number in this codebase that a refactor must never be able
to move quietly, so most of this file is a second, independent copy of the
ladder. That duplication is deliberate: a golden test that derived its
expectations from `REGIONAL_CENTS` would pass for any table at all.

The rest asserts the rules the table has to obey — that the upgrade costs
exactly the shelf less the door, that deciding at the checkout is never the
worse deal, that a year of months costs more than the year, and that a
product we do not sell in a currency is refused rather than priced in dollars
with the local symbol in front of it.
"""

from __future__ import annotations

import pytest

from alma.billing import catalogue as prices
from alma.billing.catalogue import NotSold, Product
from alma.calc import SYSTEMS

#: Every published amount, written out by hand. If a change to the mechanism
#: moves any of these, that is the test failing on purpose.
GOLDEN: dict[str, dict[str, int]] = {
    "USD": {"weekly": 499, "door": 599, "archive": 3899, "archive-bump": 2999,
            "archive-upgrade": 3300, "monthly": 999, "annual": 7899},
    "EUR": {"weekly": 549, "door": 649, "archive": 4099, "archive-bump": 3149, "archive-upgrade": 3450, "monthly": 1049, "annual": 8299},
    "GBP": {"weekly": 499, "door": 599, "archive": 3999, "archive-bump": 3099, "archive-upgrade": 3400, "monthly": 999, "annual": 7999},
    "CHF": {"weekly": 590, "door": 690, "archive": 4590, "archive-bump": 3490, "archive-upgrade": 3900, "monthly": 1190, "annual": 9290},
    "AUD": {"weekly": 799, "door": 999, "archive": 5999, "archive-bump": 4499, "archive-upgrade": 5000, "monthly": 1599, "annual": 12499},
    "CAD": {"weekly": 749, "door": 899, "archive": 5499, "archive-bump": 4199, "archive-upgrade": 4600, "monthly": 1399, "annual": 10999},
    "NOK": {"weekly": 5900, "door": 7900, "archive": 44900, "archive-bump": 33900, "archive-upgrade": 37000, "monthly": 10900, "annual": 89900},
    "DKK": {"weekly": 3900, "door": 4900, "archive": 29900, "archive-bump": 22300, "archive-upgrade": 25000, "monthly": 7900, "annual": 61900},
    "BRL": {"archive": 9990, "annual": 21900},
    "MXN": {"archive": 42900, "annual": 86900},
    "PLN": {"archive": 8499, "annual": 17499},
    "TRY": {"archive": 50900, "annual": 102900},
    "INR": {"archive": 84900, "annual": 174900},
}

#: The markets that get the archive and the year and nothing else.
PPP = ("BRL", "MXN", "PLN", "TRY", "INR")


def _cents(currency: str, band: str) -> int:
    """What we charge, through the mechanism the application uses."""
    item = next(p for p in prices.PRODUCTS.values() if p.band == band)
    return item.cents_in(currency)


# ── the ladder, pinned ─────────────────────────────────────────────────────

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
    doors = {slug: prices.PRODUCTS[slug] for slug in SYSTEMS}
    assert {item.cents for item in doors.values()} == {599}
    assert {item.scope for item in doors.values()} == {"system"}


def test_every_system_can_be_bought_and_nothing_else_claims_to_be_one():
    for system in SYSTEMS:
        assert prices.product(system).slug == system
    for slug, item in prices.PRODUCTS.items():
        if item.scope == "system":
            assert slug in SYSTEMS, f"{slug} is priced as a system but is not one"
        else:
            assert item.slug == "*", f"{slug} unlocks {item.slug!r} rather than everything"


# ── the rules the table has to obey ────────────────────────────────────────

def test_the_upgrade_is_the_shelf_less_the_door_in_every_market():
    """The whole promise of the upgrade: deciding late costs the same total.

    If this drifts by so much as a cent, a person who bought a door and came
    back pays a different price for the archive than the person who bought it
    outright, and the difference is the reason they write in.
    """
    for currency, table in GOLDEN.items():
        if "door" not in table:
            continue
        assert table["archive-upgrade"] == table["archive"] - table["door"], currency


def test_deciding_at_the_checkout_is_never_the_worse_deal():
    """The bump has to beat the shelf, and beat coming back later.

    Otherwise the in-checkout offer is a trap: it reads as a saving and is a
    surcharge, and the buyer finds out on the second invoice.
    """
    for currency, table in GOLDEN.items():
        if "door" not in table:
            continue
        assert table["door"] + table["archive-bump"] <= table["archive"], currency
        assert table["archive-bump"] < table["archive-upgrade"], currency


def test_a_year_of_months_costs_more_than_the_year():
    """A monthly cheaper than the annual over twelve months sells against itself."""
    for currency, table in GOLDEN.items():
        if "monthly" not in table:
            continue
        assert table["monthly"] * 12 > table["annual"], currency


def test_the_ladder_climbs_in_every_currency():
    for currency, table in GOLDEN.items():
        rungs = [table[band] for band in ("door", "archive", "annual") if band in table]
        assert rungs == sorted(rungs), currency


def test_a_ppp_market_is_offered_the_archive_and_the_year_and_nothing_else():
    """At a PPP-fair door, tax plus the flat processor fee takes a third of it."""
    for currency in PPP:
        assert set(prices.REGIONAL_CENTS[currency]) == {"archive", "annual"}
        offered = {
            slug for slug, item in prices.PRODUCTS.items() if item.sold_in(currency)
        }
        assert offered == {"archive", "annual"}, currency


# ── a product we do not sell is refused, never priced in dollars ───────────

def test_a_product_not_sold_here_refuses_instead_of_charging_the_us_price():
    """The defect this replaced: the door fell through to its USD amount.

    A Brazilian was shown R$8.99 for a door priced at nothing, and the only
    thing standing between that and a charge was the client not asking.
    """
    with pytest.raises(NotSold):
        prices.PRODUCTS["natal"].cents_in("BRL")
    with pytest.raises(NotSold):
        prices.PRODUCTS["monthly"].display("INR")
    assert prices.PRODUCTS["natal"].sold_in("BRL") is False


def test_an_unpriced_currency_refuses_rather_than_answering_in_dollars():
    """Sweden is not priced. Asking for a Swedish price must not return 599."""
    assert "SEK" not in prices.REGIONAL_CENTS
    with pytest.raises(NotSold):
        prices.PRODUCTS["archive"].cents_in("SEK")


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
    archive = prices.PRODUCTS["archive"]
    assert archive.display("USD") == "$38.99"
    assert archive.display("EUR") == "€40,99"
    assert archive.display("GBP") == "£39.99"
    assert archive.display("CHF") == "CHF 45.90"
    assert archive.display("AUD") == "A$59.99"
    assert archive.display("CAD") == "C$54.99"
    assert archive.display("NOK") == "kr 449"
    assert archive.display("DKK") == "kr 299"
    assert archive.display("BRL") == "R$ 99,90"
    assert archive.display("MXN") == "MX$429"
    assert archive.display("PLN") == "84,99 zł"
    assert archive.display("TRY") == "₺509"
    assert archive.display("INR") == "₹849"


def test_the_symbol_goes_where_the_market_puts_it():
    """A Pole shown "zł84,99" is being shown a currency on the wrong end."""
    assert prices.format_price(8499, "PLN").endswith("zł")
    assert prices.format_price(8499, "EUR").startswith("€")


def test_an_unknown_currency_still_says_which_currency_it_is():
    """A bare number is worse than a wrong symbol: nothing about it looks wrong."""
    assert prices.format_price(1499, "SEK") == "SEK 14.99"


def test_the_old_rounding_machine_could_not_have_produced_this_ladder():
    """Why the multiplier architecture had to go, stated as a fact.

    `_to_price_point` snaps anything between ten and two hundred units onto an
    x9.90 ending. The shelf price and the annual are neither, so no amount of
    tuning the multipliers could ever have reached them.
    """
    assert prices._to_price_point(3899) != 3899
    assert prices._to_price_point(7899) != 7899


# ── the credit ─────────────────────────────────────────────────────────────

def test_every_price_published_is_a_price_a_price_id_can_take():
    """Nothing in the list is computed out of another number.

    This is the rule the whole credit mechanism turns on. The list used to
    publish `payable_cents` — a price minus a credit — while the checkout
    opened the overlay against the full price id, so two shipped surfaces
    stated an amount that would never be charged. Every entry now names a
    catalogue key, and its `cents` is that key's own amount in that currency.
    """
    for currency, country in (("USD", "US"), ("EUR", "DE"), ("BRL", "BR")):
        listing = prices.catalogue(country=country, credit_cents=899, credit_currency=currency)
        for item in listing["items"]:
            assert item["cents"] == prices.PRODUCTS[item["slug"]].cents_in(currency)
            assert "payable_cents" not in item


def test_a_credit_substitutes_the_upgrade_for_the_shelf_price():
    """Someone who bought a door is shown the upgrade where the archive was.

    The upgrade is a real price id at the shelf price less the door, so what
    the paywall says is what the card is charged. `replaces` is there so the
    interface can explain the lower number instead of inventing a struck-out
    price of its own.
    """
    listing = prices.catalogue(credit_cents=899, credit_currency="USD")
    slugs = [item["slug"] for item in listing["items"]]
    assert "archive-upgrade" in slugs and "archive" not in slugs

    upgrade = next(item for item in listing["items"] if item["slug"] == "archive-upgrade")
    assert upgrade["cents"] == prices.PRODUCTS["archive-upgrade"].cents
    assert upgrade["replaces"] == "archive"
    assert upgrade["credit_cents"] == prices.PRODUCTS["archive"].cents - upgrade["cents"]


def test_the_substitution_is_the_door_taken_off_in_every_market():
    """The upgrade is worth exactly one door wherever both are sold."""
    for currency, country in (("USD", "US"), ("EUR", "DE"), ("GBP", "GB"), ("NOK", "NO")):
        listing = prices.catalogue(country=country, credit_cents=1, credit_currency=currency)
        upgrade = next(item for item in listing["items"] if item["slug"] == "archive-upgrade")
        door = prices.PRODUCTS["natal"].cents_in(currency)
        archive = prices.PRODUCTS["archive"].cents_in(currency)
        assert archive - upgrade["cents"] == door, currency
        assert upgrade["credit_cents"] == door


def test_a_credit_earned_in_one_currency_is_not_spent_against_another():
    """kr 109 is about ten dollars, and would otherwise read as a $109 credit.

    Refusing it is the safe direction: the buyer can be given the credit by
    hand, whereas an upgrade handed out for nothing is gone.
    """
    listing = prices.catalogue(credit_cents=10900, credit_currency="NOK")
    slugs = [item["slug"] for item in listing["items"]]
    assert "archive" in slugs and "archive-upgrade" not in slugs


def test_a_market_with_no_upgrade_band_keeps_its_shelf_price():
    """Brazil is sold the archive and the year and nothing else.

    A substitution there would have to invent a price, which is what this
    module refuses to do anywhere else either.
    """
    listing = prices.catalogue(country="BR", credit_cents=9990, credit_currency="BRL")
    assert [item["slug"] for item in listing["items"]] == ["archive", "annual"]


# ── what a client is given ─────────────────────────────────────────────────

def test_a_recurring_plan_is_never_rendered_as_a_single_payment():
    """The defect this replaced: the list filtered the annual out and carried
    no interval, so the first monthly plan added would have been drawn as a
    one-time purchase."""
    listing = prices.catalogue()
    monthly = next(item for item in listing["items"] if item["slug"] == "monthly")
    annual = next(item for item in listing["items"] if item["slug"] == "annual")
    assert (monthly["kind"], monthly["interval"]) == ("monthly", "month")
    assert (annual["kind"], annual["interval"]) == ("annual", "year")
    for item in listing["items"]:
        if item["kind"] == "one_time":
            assert item["interval"] == "", item["slug"]


def test_the_list_is_whatever_is_on_the_shelf_rather_than_a_hardcoded_shape():
    listing = prices.catalogue()
    assert [item["slug"] for item in listing["items"]] == [
        key for key, item in prices.PRODUCTS.items() if item.on_the_shelf
    ]


def test_a_conditional_price_is_never_listed():
    """`archive-bump` and `archive-upgrade` grant what `archive` grants.

    They cost nine dollars less, so listing them published a cheaper way to
    buy the same thing to anyone who read the response — no purchase, no
    qualification, one HTTP call. `offered` used to say so and stop nothing.
    """
    for country in (None, "DE", "GB", "BR"):
        slugs = {item["slug"] for item in prices.catalogue(country=country)["items"]}
        assert "archive-bump" not in slugs
        assert "archive-upgrade" not in slugs

    conditional = [key for key, item in prices.PRODUCTS.items() if not item.on_the_shelf]
    assert conditional == ["archive-bump", "archive-upgrade"]


def test_a_brazilian_is_shown_only_what_is_sold_in_brazil():
    listing = prices.catalogue(country="BR")
    assert listing["currency"] == "BRL"
    assert [item["slug"] for item in listing["items"]] == ["archive", "annual"]
    assert listing["annual"]["display"] == "R$ 219"


# ── the monthly's scope ────────────────────────────────────────────────────

def test_the_monthly_rents_only_the_systems_that_move():
    """A natal chart bought monthly is rent on a number fixed at birth."""
    assert prices.LIVING_SYSTEMS <= set(SYSTEMS)
    assert prices.PRODUCTS["monthly"].scope == "live"
    assert prices.LIVING_SYSTEMS == {"transits", "solar-return", "compatibility"}
