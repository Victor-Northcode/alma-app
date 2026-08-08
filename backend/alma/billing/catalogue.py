"""Prices, and the one rule that keeps a shown price and a charged price equal.

Everything here is data rather than logic, deliberately: a price is a decision
somebody made in a market, not the output of a formula. That is the lesson of
what this file used to be. It held one multiplier per country and rounded the
result onto a familiar ending, which is a machine that *cannot* express the
price list we actually sell — asked for €38.99 it produced €39.90, and asked
for a euro price at all it produced the raw US number, so European buyers were
quietly charged their dollar price with a euro sign in front of it.

So the shape changed. `REGIONAL_CENTS` holds the exact minor units for each
currency and each price band, and **those integers must equal the amounts on
the processor's price ids**. Nothing is derived at request time, which is the
only way the number on the paywall and the number on the card cannot diverge.

Two other rules are worth stating because both were bugs:

* **A product that is not sold in a currency is a refusal, not a fallback.**
  The PPP markets get the archive and the year and nothing else, because at a
  PPP-fair price the local VAT plus the flat processor fee eats 25–33% of an
  $8.99 door. Asking for a price that does not exist raises `NotSold`; the old
  code answered with the US number, which is how a Brazilian nearly got billed
  R$8.99 for a door priced R$0.
* **A credit is a product, not a discount.** Someone who buys one reading,
  likes it, and upgrades inside the window should not pay for that reading
  twice — and the only way to keep that promise is a price id that already
  carries the reduced amount. `archive-upgrade` is exactly that: the shelf
  price less the door, in every currency where both are sold, so the person
  who decides late pays what the person who decided at the checkout paid.

  This used to be arithmetic instead. `catalogue()` published a
  `payable_cents` per product — the price minus a credit — while the checkout
  opened the processor's overlay against the full price id, with no discount
  and no custom amount. Two shipped surfaces stated a number that would never
  be charged, which is the shape of a chargeback and of a consumer-protection
  complaint. Nothing here computes a price out of another price any more: the
  qualifying buyer is offered the upgrade *instead of* the shelf item, and
  what they are shown is what the price id takes.

**The window is thirty days**, not the seven this file used to claim. The
upgrade is offered after a reading has been read and thought about, and a week
put the offer in front of people who had not finished the thing they bought.
`CREDIT_WINDOW` in `auth/entitlements.py` is the one place it is a number.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class NotSold(ValueError):
    """This product is not offered in this currency.

    A first-class state rather than a missing key. Every alternative — falling
    back to the US amount, to zero, to `None` — ends with somebody being shown
    or charged a number nobody chose, and the fallback is invisible until a
    customer notices it.
    """


@dataclass(frozen=True, slots=True)
class Product:
    """One thing that can be bought, and everything a client needs to show it."""

    slug: str            # the system it unlocks, or "*" for everything
    name: str
    kind: str            # "one_time" | "monthly" | "annual"
    cents: int           # USD minor units — what a US buyer is charged
    band: str            # which row of REGIONAL_CENTS prices it
    interval: str = ""   # "" | "month" | "year" — empty means it does not renew
    scope: str = "system"  # "system" | "all" | "live"
    #: Where in the funnel this price is allowed to appear. "shelf" is the
    #: public list; "in-checkout" exists only as an upsell inside another
    #: checkout; "after-door" is offered once, to someone who already bought a
    #: door. Rendering an "after-door" price to a person who owns nothing is
    #: offering them a discount off a purchase they have not made.
    offered: str = "shelf"

    #: The identifier each processor holds for this row, keyed by processor
    #: name — `{"paddle": "pri_…", "dodo": "pdt_…"}`.
    #:
    #: A mapping and not a column per processor, and the difference is the point
    #: of this whole change. It was `paddle_price_id: str`, which is one
    #: company's word in a file whose entire job is that what we sell is our
    #: decision and not a processor's. A second flat column would have made the
    #: second processor as expensive as the first — and a third impossible
    #: without editing every lookup. Here, a new processor is a new key.
    #:
    #: Every one of these is empty. Nothing has ever been sold through this
    #: code, and they are filled in from a processor's dashboard once an account
    #: exists — which is the one step no amount of code can do for us.
    processor_ids: dict[str, str] = field(default_factory=dict)

    def identifier(self, processor: str) -> str:
        """What `processor` calls this product, or "" if it has never been told.

        Empty is a refusal upstream, never a fallback: an adapter that opened a
        session against the wrong identifier would charge the right money for
        the wrong thing, and the webhook that came back would grant the wrong
        thing too.
        """
        return self.processor_ids.get(processor, "")

    @property
    def dollars(self) -> float:
        """The US price in whole units. Only ever the US one — see `cents_in`."""
        return self.cents / 100.0

    @property
    def on_the_shelf(self) -> bool:
        """Whether this price may be listed and sold on its own.

        The conditional prices are not merely "shown elsewhere": they are
        cheaper than the shelf item they stand in for, and each of them
        granted exactly what the shelf item grants. `archive-bump` at $29.99
        and `archive` at $38.99 both write an everything-grant, so while the
        list rendered all thirteen keys and the checkout accepted any of them
        by name, anyone who read one HTTP response could buy the archive for
        nine dollars less. This property is the gate that stops that; the
        `offered` field was only ever a note about intent.
        """
        return self.offered == "shelf"

    def sold_in(self, currency: str) -> bool:
        return currency == "USD" or self.band in REGIONAL_CENTS.get(currency, {})

    def cents_in(self, currency: str) -> int:
        """What this costs in `currency`, in that currency's minor units.

        Never a conversion. The number returned is the number on the price id,
        because a displayed price computed one way and a charged price fetched
        another way will disagree eventually, and the disagreement is found by
        the buyer.
        """
        if currency == "USD":
            return self.cents
        try:
            return REGIONAL_CENTS[currency][self.band]
        except KeyError:
            raise NotSold(f"{self.name!r} ({self.band}) is not sold in {currency}") from None

    def display(self, currency: str = "USD") -> str:
        return format_price(self.cents_in(currency), currency)


#: The three systems that change with time, and therefore the only ones a
#: recurring plan can honestly sell — a natal chart bought monthly would be
#: rent on a number that has not moved since birth. Imported by the paywall
#: and by the entitlement check for the `"live"` scope.
LIVING_SYSTEMS: frozenset[str] = frozenset({"transits", "solar-return", "compatibility"})

#: The price bands. Every currency table is keyed by these, and a product
#: names the one it sits on rather than carrying its own foreign amounts —
#: eight doors at the same price should be one row to edit, not eight to keep
#: in agreement.
BANDS: tuple[str, ...] = (
    "door",
    "archive",
    "archive-bump",
    "archive-upgrade",
    "monthly",
    "annual",
)

_DOOR_CENTS = 599

#: The catalogue. One price for every door: the quiz decides which system a
#: person is offered, so a price that varied by system would be a price that
#: varied by quiz answer, and the eight differentiated prices we used to
#: publish were an invitation to answer the quiz again for a cheaper reading.
PRODUCTS: dict[str, Product] = {
    "natal": Product("natal", "Natal chart", "one_time", _DOOR_CENTS, band="door"),
    "numerology": Product("numerology", "Numerology", "one_time", _DOOR_CENTS, band="door"),
    "birth-card": Product("birth-card", "Birth Card", "one_time", _DOOR_CENTS, band="door"),
    "transits": Product("transits", "Transits", "one_time", _DOOR_CENTS, band="door"),
    "solar-return": Product("solar-return", "Solar return", "one_time", _DOOR_CENTS, band="door"),
    "compatibility": Product("compatibility", "Compatibility", "one_time", _DOOR_CENTS, band="door"),
    "astrocartography": Product(
        "astrocartography", "Astrocartography", "one_time", _DOOR_CENTS, band="door"
    ),
    "synthesis": Product("synthesis", "Cross-synthesis", "one_time", _DOOR_CENTS, band="door"),
    # The shelf. Bought outright and kept, because what is sold is a written
    # interpretation of numbers that do not change.
    "archive": Product(
        "*", "The whole archive", "one_time", 3899, band="archive", scope="all"
    ),
    # The rest of the archive, added to a door *in the same checkout*. It is a
    # cent under the door plus the upgrade, so that deciding now is never the
    # worse deal and deciding later is never punished. It is not a standalone
    # archive at $29.99 and must never be sold as one — 899 + 2999 = 3898 is
    # the sum that is one cent under the shelf, and a bump bought alone is the
    # shelf item at nine dollars off. `on_the_shelf` is what enforces that.
    "archive-bump": Product(
        "*", "The rest of the archive", "one_time", 2999,
        band="archive-bump", scope="all", offered="in-checkout",
    ),
    # The shelf price less the door already paid. Offered once, to someone who
    # already bought a door — which is the whole of the credit promise, turned
    # into a price id instead of into arithmetic nobody charges.
    "archive-upgrade": Product(
        # 3899 archive − 599 door. Derived by hand and pinned by a test rather
        # than computed here, because the number on this line must equal the
        # number on the store's price id, and only a person can put it there.
        "*", "The rest of the archive", "one_time", 3300,
        band="archive-upgrade", scope="all", offered="after-door",
    ),
    # The only recurring things worth renting are the ones that move: transits,
    # the solar return, compatibility. Everything else stays a purchase.
    "monthly": Product(
        "*", "Everything live, monthly", "monthly", 999,
        band="monthly", interval="month", scope="live",
    ),
    "annual": Product(
        "*", "Everything, for a year", "annual", 7899,
        band="annual", interval="year", scope="all",
    ),
}


#: Exact minor units per currency, per band. Computed from FX on 6 Aug 2026
#: and each market's own tax, then set — not converted at request time.
#:
#: USD is absent on purpose: `Product.cents` is the US price and there must be
#: exactly one place holding it.
REGIONAL_CENTS: dict[str, dict[str, int]] = {
    # VAT-neutral: at these points the net after 19–25% EU VAT lands within 1%
    # of the US net, which is the definition of "the same price" rather than a
    # discount or a surcharge.
    "EUR": {
        "door": 649, "archive": 4099, "archive-bump": 3149,
        "archive-upgrade": 3450, "monthly": 1049, "annual": 8299,
    },
    # UK consumers pay roughly 8% above the US for digital subscriptions and
    # the market is used to it.
    "GBP": {
        "door": 599, "archive": 3999, "archive-bump": 3099,
        "archive-upgrade": 3400, "monthly": 999, "annual": 7999,
    },
    # Switzerland was not in COUNTRY_CURRENCY at all, so Swiss buyers were
    # billed raw USD — the single most under-priced market we had. Swiss VAT is
    # 8.1%, not 20%, and Swiss consumers pay 1.25–1.65x the US price for
    # digital subscriptions (Spotify CHF 15.95 against $11.99; Netflix
    # CHF 22.90 against $17.99). These points net about 135% of the US net.
    "CHF": {
        "door": 690, "archive": 4590, "archive-bump": 3490,
        "archive-upgrade": 3900, "monthly": 1190, "annual": 9290,
    },
    "AUD": {
        "door": 999, "archive": 5999, "archive-bump": 4499,
        "archive-upgrade": 5000, "monthly": 1599, "annual": 12499,
    },
    "CAD": {
        "door": 899, "archive": 5499, "archive-bump": 4199,
        "archive-upgrade": 4600, "monthly": 1399, "annual": 10999,
    },
    "NOK": {
        "door": 7900, "archive": 44900, "archive-bump": 33900,
        "archive-upgrade": 37000, "monthly": 10900, "annual": 89900,
    },
    "DKK": {
        "door": 4900, "archive": 29900, "archive-bump": 22300,
        "archive-upgrade": 25000, "monthly": 7900, "annual": 61900,
    },
    # Purchasing-power markets: the archive and the year, and nothing else.
    # A PPP-fair door is small enough that local VAT plus the flat per-
    # transaction fee takes a quarter to a third of it, so the door would be
    # sold at a loss on the second-cheapest thing we make. Offering fewer
    # products at an honest price beats offering all of them at a price that
    # is really the US one.
    "BRL": {"archive": 9990, "annual": 21900},
    "MXN": {"archive": 42900, "annual": 86900},
    "PLN": {"archive": 8499, "annual": 17499},
    "TRY": {"archive": 50900, "annual": 102900},
    "INR": {"archive": 84900, "annual": 174900},
}


@dataclass(frozen=True, slots=True)
class Notation:
    """How one currency writes a price.

    Every field here has burned somebody: a Brazilian shown "R$38.97" is being
    shown something that is not a price, and a Pole shown "zł84,99" is being
    shown a currency that goes on the other end.
    """

    symbol: str
    thousands: str
    decimal: str
    suffix: bool = False


#: All of these are two-decimal currencies. A zero-decimal one (JPY, KRW) would
#: need `format_price` to stop dividing by 100 before it could be listed.
CURRENCY_FORMAT: dict[str, Notation] = {
    "USD": Notation("$", ",", "."),
    "GBP": Notation("£", ",", "."),
    "EUR": Notation("€", ".", ","),
    "CHF": Notation("CHF ", "'", "."),
    "AUD": Notation("A$", ",", "."),
    "CAD": Notation("C$", ",", "."),
    "NOK": Notation("kr ", " ", ","),
    "DKK": Notation("kr ", " ", ","),
    "BRL": Notation("R$ ", ".", ","),
    "MXN": Notation("MX$", ",", "."),
    "PLN": Notation(" zł", " ", ",", suffix=True),
    "TRY": Notation("₺", ".", ","),
    "INR": Notation("₹", ",", "."),
}


def _to_price_point(cents: int) -> int:
    """Suggest a price point to a human. Never used to compute one.

    Converting $14.99 into reais gives 3 897, which is not a price anybody
    would set. This rounds such a number onto a familiar ending so that
    whoever is filling in a new column of `REGIONAL_CENTS` has somewhere to
    start — and then they decide, and the decision is written down as an
    integer that matches the processor's price id.

    It is deliberately not wired into `cents_in`. A multiplier plus rounding
    cannot express $38.99 at all: it snaps everything between 10.00 and 199.99
    onto an x9.90 ending, so 3899 comes back as 3990 and 7899 as 7990.
    """
    if cents < 1_000:                      # under ten units → x.90
        return max(90, (cents // 100) * 100 + 90)
    if cents < 20_000:                     # tens → x9.90
        return max(990, round(cents / 1_000) * 1_000 - 10)
    return round(cents / 1_000) * 1_000    # hundreds → a whole ten units


def format_price(cents: int, currency: str = "USD") -> str:
    """A price as the reader's own locale writes it.

    An unlisted currency renders its ISO code rather than a bare number: a
    figure with no currency attached is worse than a figure in the wrong one,
    because nothing about it looks wrong.
    """
    style = CURRENCY_FORMAT.get(currency) or Notation(f"{currency} ", ",", ".")
    whole, part = divmod(abs(cents), 100)
    grouped = f"{whole:,}".replace(",", style.thousands)
    body = grouped if part == 0 else f"{grouped}{style.decimal}{part:02d}"
    return f"{body}{style.symbol}" if style.suffix else f"{style.symbol}{body}"


#: Which currency a country is billed in. Everything not listed pays in USD,
#: which is a deliberate fallback for a country we have not priced — unlike a
#: *product* we have not priced in a listed currency, which is a refusal.
COUNTRY_CURRENCY: dict[str, str] = {
    "BR": "BRL",
    "MX": "MXN",
    # The euro area, all twenty. A missing member does not fail loudly; it
    # bills that country in dollars, which is why the list is complete rather
    # than "the big ones".
    "DE": "EUR", "FR": "EUR", "IT": "EUR", "ES": "EUR", "NL": "EUR",
    "PT": "EUR", "IE": "EUR", "AT": "EUR", "BE": "EUR", "FI": "EUR",
    "GR": "EUR", "SK": "EUR", "SI": "EUR", "LT": "EUR", "LV": "EUR",
    "EE": "EUR", "LU": "EUR", "CY": "EUR", "MT": "EUR", "HR": "EUR",
    "GB": "GBP",
    "CH": "CHF",
    "AU": "AUD",
    "CA": "CAD",
    "NO": "NOK",
    "DK": "DKK",
    "PL": "PLN",
    "TR": "TRY",
    "IN": "INR",
}


def currency_for(country: str | None) -> str:
    return COUNTRY_CURRENCY.get((country or "").upper(), "USD")


def product(slug: str) -> Product:
    try:
        return PRODUCTS[slug]
    except KeyError:
        raise ValueError(f"nothing on sale called {slug!r}") from None


def by_price_id(price_id: str, processor: str | None = None) -> str | None:
    """Which catalogue **key** carries this processor identifier.

    The key, not the `Product`, because five products share the slug `"*"` and
    a caller holding only the object has to guess its way back to a key. The
    guess that was there — `found.slug if found.kind == "one_time" else
    "annual"` — was wrong in both directions on the same line: an archive
    lookup produced `"*"`, which is not a key, so the payment was recorded and
    nothing granted; a monthly lookup produced `"annual"`, so a month's price
    bought a year.

    `processor` narrows the search to one processor's identifiers, which is what
    an adapter should pass: two processors could in principle issue the same
    string, and matching another one's would grant against a product this
    payment did not buy. Omitting it searches all of them, which is right for a
    support tool holding an identifier and not knowing where it came from.
    """
    if not price_id:
        return None
    for key, item in PRODUCTS.items():
        found = (
            [item.identifier(processor)] if processor else list(item.processor_ids.values())
        )
        if price_id in [value for value in found if value]:
            return key
    return None


#: What we no longer publish but may still owe a credit against.
#:
#: The single chapter was sold in task #21 at $4.99 and withdrawn when this
#: ladder replaced it. Its price is kept because a credit has to be a number we
#: actually advertised: falling back to `Entitlement.amount_cents` would credit
#: the processor's grand total, which carries sales tax we have already handed
#: to a tax authority, and refunding that out of margin on a reading the buyer
#: keeps is a worse answer than crediting nothing. USD only, because a chapter
#: price in any other currency was produced by the multiplier this file
#: deleted, and a number nobody chose is not a number we can hand back.
WITHDRAWN_CENTS: dict[str, dict[str, int]] = {
    "chapter": {"USD": 499},
}


def _entry(key: str, item: Product, currency: str) -> dict:
    return {
        "slug": key,
        "system": item.slug,
        "name": item.name,
        "kind": item.kind,
        "interval": item.interval,
        "scope": item.scope,
        "offered": item.offered,
        "cents": item.cents_in(currency),
        "display": item.display(currency),
    }


def catalogue(
    *,
    country: str | None = None,
    credit_cents: int = 0,
    credit_currency: str = "USD",
) -> dict:
    """The price list a client renders. Every number in it is a number we take.

    Only the shelf appears. The conditional prices used to be listed too, and
    since each of them grants exactly what the shelf item it stands in for
    grants, listing them published a cheaper way to buy the same thing to
    anyone who read the response.

    A qualifying credit does not discount a price here; it **substitutes a
    product**. Someone who bought a door inside the window is shown
    `archive-upgrade` where the archive would have been, because that is a real
    price id at exactly the shelf price less the door, so the amount on the
    paywall is the amount on the card. Arithmetic in this function could only
    ever have produced a number the processor would not honour.

    Each entry carries its own `kind`, `interval` and `scope`. This used to
    render one hardcoded annual block and filter the annual out of the list, so
    the moment a second recurring plan existed it would have been drawn as a
    one-time purchase — a subscription sold as a single payment is a chargeback
    with a delay on it.
    """
    currency = currency_for(country)
    # A credit is denominated in the currency it was paid in and we are told
    # which that was. If it does not match what we are about to price, it is
    # refused rather than compared: NOK 109 set against a $78.99 plan reads as
    # a $109 credit and would substitute an upgrade the buyer has not earned.
    spendable = credit_cents if credit_currency == currency else 0
    upgrade = PRODUCTS["archive-upgrade"]
    substitute = spendable > 0 and upgrade.sold_in(currency)

    items: list[dict] = []
    for key, item in PRODUCTS.items():
        if not item.on_the_shelf or not item.sold_in(currency):
            continue
        if key == "archive" and substitute:
            entry = _entry("archive-upgrade", upgrade, currency)
            # Named so the interface can say *why* this is cheaper rather than
            # inventing a struck-through price of its own.
            entry["replaces"] = "archive"
            entry["credit_cents"] = item.cents_in(currency) - entry["cents"]
            items.append(entry)
            continue
        items.append(_entry(key, item, currency))

    listing: dict = {"currency": currency, "items": items}
    # A transitional alias, not a second source of truth: it is the same dict
    # object that is already in `items`. The interface still reads
    # `catalogue.annual`; this key goes when it reads `items` instead.
    annual = next((entry for entry in items if entry["slug"] == "annual"), None)
    if annual is not None:
        listing["annual"] = annual
    return listing
