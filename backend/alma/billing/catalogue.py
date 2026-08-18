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
* **Каталог не считает цену из другой цены.** Ни скидок, ни доборов, ни
  `payable_cents`: каждая строка называет сумму, которую действительно
  спишут. До v3 здесь жила кредитная лестница — `archive-upgrade` по цене
  полки минус дверь, `archive-bump` внутри чужого чекаута, — и она стоила
  двух отдельных багов: витрина печатала число, которое процессор не взял бы,
  а по имени продукта можно было купить архив на девять долларов дешевле.
  В v3 её нет вовсе (ТЗ §2, решение владельца от 17.08.2026: старую
  монетизацию не консервируем, а вычищаем), и вместе с ней ушли `WITHDRAWN_CENTS`,
  `annual_credit` и подстановка товара в `catalogue()`.

**Ключ словаря — это идентификатор товара в сторах, а не слаг системы.**
Решение v3 и единственное место, где о нём написано. До v3 ключ `PRODUCTS`
совпадал со слагом системы (`"natal"`), и это работало ровно пока полка была
«восемь дверей плюс архив». В v3 полка разнородная: пять дверей, бандл, пара и
подписка — «натал» перестал быть именем товара и стал именем того, что товар
открывает. Поэтому:

* **ключ** — `door.natal`, `pair.check`, `bundle.static`, `sub.monthly`. Он же,
  с приставкой из `settings().store_product_prefix` и дефисами, заменёнными на
  подчёркивания, — идентификатор в App Store Connect и Play Console:
  `ai.pazl.alma.door.natal`, `ai.pazl.alma.door.birth_card`. Правило и обратное
  преобразование живут в `provider.store_product_id` / `store_slug` и не
  изменились: они всегда работали с ключом, а не со слагом;
* **`Product.slug`** остался тем, чем был, — системой, которую товар открывает
  (`"*"` для бандла и подписки). Разводить их пришлось потому, что иначе
  идентификатор в консоли зависел бы от того, как называется наша система, а
  переименовать его после публикации не даст ни один магазин.

Цена ошибки, если кто-то снова их сольёт: `store_slug` вернёт ключ, которого
нет в `PRODUCTS`, покупка отработает и не выдаст ничего — деньги взяты, глава
закрыта, и ни один лог об этом не скажет.
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
    #: "one_time" | "consumable" | "monthly". Пишется в `Entitlement.kind`,
    #: поэтому список обязан совпадать с `EntitlementKind` — это пинается
    #: тестом. `consumable` завели под `pair.check`: он покупается многократно,
    #: и магазин обязан позволить купить его снова, а разовая дверь — нет.
    kind: str
    cents: int           # USD minor units — what a US buyer is charged
    band: str            # which row of REGIONAL_CENTS prices it
    interval: str = ""   # "" | "month" | "year" — empty means it does not renew
    #: Ширина гранта, теми же словами, что и колонка `Entitlement.scope`:
    #: "system" (одна система) | "static" (пять статичных) | "pair" (одна пара)
    #: | "all" (всё, пока подписка жива) | "live" (легаси, новых не выписываем).
    scope: str = "system"
    #: Сколько проверок совместимости включено в один расчётный период. Поле
    #: товара, а не конфига: «что входит в подписку» — решение о том, что мы
    #: продаём, и оно обязано стоять рядом с ценой, иначе цена и обещание
    #: правятся в двух местах и однажды разойдутся. Ноль у всего, что не
    #: подписка. Начисление кредита — Ф0.4, здесь только объявление.
    pair_credits_monthly: int = 0
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

        **В v3 все восемь строк отвечают True, и механизм всё равно остаётся.**
        Он существует не ради текущей полки, а ради того класса ошибок, который
        уже случался: условная цена (`archive-bump` за $29.99 против архива за
        $38.99) выдавала ровно то же, что и полочная, а чекаут принимал любой
        ключ по имени — то есть архив покупался на девять долларов дешевле одним
        HTTP-запросом. Поле `offered` тогда лишь документировало намерение и не
        останавливало ничего; свойство — останавливает.

        Возвращать его придётся в первый же A/B с ценой бандла (ТЗ §7), и
        дешевле держать ворота закрытыми, чем строить их заново под давлением.
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


#: The three systems that change with time. Imported by the paywall, by the
#: daily note, and by the entitlement check for the legacy `"live"` scope.
#:
#: **В v3 это уже не «что продаёт подписка».** Подписка продаёт всё
#: (`sub.monthly`, `scope="all"`), и живой слой — только та её часть, которую
#: нельзя купить навсегда: транзиты пересчитываются каждый день, соляр — к
#: каждому дню рождения. Список остаётся, потому что на нём держатся два
#: живых потребителя: `Entitlement.covers` для грантов со `scope="live"`
#: (новых не выписываем, старые обязаны продолжать работать) и утренняя
#: заметка, которая решает по нему, что показывать бесплатно.
LIVING_SYSTEMS: frozenset[str] = frozenset({"transits", "solar-return", "compatibility"})

#: The price bands. Every currency table is keyed by these, and a product
#: names the one it sits on rather than carrying its own foreign amounts —
#: five doors at the same price should be one row to edit, not five to keep
#: in agreement.
#:
#: `door` и `pair` стоят одинаково ($4.99) и всё-таки разведены на две полосы.
#: Довод: одинаковая цена у них — следствие позиционирования, а не одна цена
#: двух видов одного товара. Дверь покупается один раз и навсегда, проверка
#: пары — расходуемая и покупается многократно; ТЗ §7 планирует A/B по цене, и
#: общая полоса означала бы, что сдвиг одной цены молча тянет за собой пять
#: чужих. Тринадцать продублированных чисел — плата за то, что этого не
#: случится.
BANDS: tuple[str, ...] = ("door", "pair", "bundle", "monthly")

_DOOR_CENTS = 499
_PAIR_CENTS = 499

#: Полка v3 — восемь строк, и ровно эти восемь заводятся в консолях.
#:
#: Одна цена на все двери: квиз решает, какую систему человеку предложат
#: первой, так что цена, зависящая от системы, — это цена, зависящая от ответа
#: в квизе, и приглашение пройти квиз ещё раз ради разбора подешевле.
#:
#: Транзитов, соляра и совместимости среди дверей нет намеренно (ТЗ §2):
#: транзиты — движок ежедневного гороскопа, соляр переписывается к каждому дню
#: рождения, и продать их «навсегда» значит продать подписку без подписки.
#: Совместимость продаётся поштучно, `pair.check`, потому что покупается не
#: система, а отчёт про конкретного человека.
PRODUCTS: dict[str, Product] = {
    "door.natal": Product("natal", "Natal chart", "one_time", _DOOR_CENTS, band="door"),
    "door.numerology": Product(
        "numerology", "Numerology", "one_time", _DOOR_CENTS, band="door"
    ),
    "door.birth-card": Product(
        "birth-card", "Birth Card", "one_time", _DOOR_CENTS, band="door"
    ),
    "door.astrocartography": Product(
        "astrocartography", "Astrocartography", "one_time", _DOOR_CENTS, band="door"
    ),
    "door.synthesis": Product(
        "synthesis", "Cross-synthesis", "one_time", _DOOR_CENTS, band="door"
    ),
    # Расходуемый: один отчёт про одну пару, покупается столько раз, сколько
    # партнёров человек проверит. `slug` здесь — система, к которой отчёт
    # относится, и **не** то, что будет записано в грант: грант пары называется
    # `pair:{profile_id}`, а какой это профиль, знает только PairIntent (А4,
    # фаза Ф0.3). Поэтому `provider.entitlement_for` отказывается выписывать
    # что-либо по `scope="pair"` — см. комментарий там; ошибка стоила бы
    # открытой совместимости со всеми партнёрами сразу за $4.99.
    "pair.check": Product(
        "compatibility", "One compatibility report", "consumable", _PAIR_CENTS,
        band="pair", scope="pair",
    ),
    # Пять статичных разборов разом. Цена — решение владельца от 17.08.2026;
    # два инварианта, которые её держат, пинаются тестами в `test_prices.py`:
    # сумма пяти дверей должна быть больше бандла (иначе бандл бессмыслен) и
    # бандл — меньше трёх месяцев подписки (иначе он не якорь, а вторая
    # подписка).
    "bundle.static": Product(
        "*", "All five readings", "one_time", 1999, band="bundle", scope="static"
    ),
    # Единственная подписка. `scope="all"`, а не `"live"`: v3 продаёт «всё, пока
    # платишь» — живой слой плюс статичные разборы, — и это ровно то, что
    # обещает копирайт P5. Строка «купленное навсегда остаётся твоим» рядом с
    # кнопкой существует потому, что `all` истекает, а `system`/`static` — нет.
    "sub.monthly": Product(
        "*", "Everything, monthly", "monthly", 999,
        band="monthly", interval="month", scope="all", pair_credits_monthly=1,
    ),
}


#: Exact minor units per currency, per band. Computed from FX on 6 Aug 2026
#: and each market's own tax, then set — not converted at request time.
#:
#: USD is absent on purpose: `Product.cents` is the US price and there must be
#: exactly one place holding it.
#:
#: **Откуда взялись числа v3, по полосам — чтобы это можно было проверить, а не
#: принять на веру.**
#:
#: * `monthly` не тронут: $9.99 в v3 те же $9.99, что и раньше, значит вся
#:   строка остаётся ровно такой, какой её выбрал человек под каждый рынок;
#: * `door` и `pair` — это **уже принятые** точки $4.99: столько стоила
#:   недельная подписка, и её локальные цены выбирались под ту же сумму. Мы
#:   переиспользуем решение, а не изобретаем новое;
#: * `bundle` — единственная **выведенная** полоса: два месяца подписки,
#:   округлённые до окончания, принятого на рынке (€20.99, CHF 23.90, kr 219).
#:   $19.99 = 2 × $9.99 в США, и та же пропорция удерживает якорь везде;
#: * PPP-рынки (BRL, MXN, PLN, TRY, INR) впервые получают дверь и подписку.
#:   Прежний отказ держался на фиксированной комиссии за транзакцию, которой у
#:   магазинов нет: Apple и Google берут процент и только процент, так что доля,
#:   которая остаётся нам, одинакова и на R$12.90, и на R$99.90. Разбор — в
#:   `mobile/store/PRODUCTS.md` §5; числа $9.99 взяты оттуда же, дверь — 5/6 от
#:   выведенной там двери $5.99.
#:
#: **Выведенное — не значит утверждённое.** Полосу `bundle` и пять строк PPP
#: обязан подтвердить владелец, и подтверждать их надо **до** того, как товар
#: будет сохранён в консоли: у Apple цена берётся из сетки готовых точек, и если
#: точки нет, берут ближайшую — и тем же коммитом вписывают её сюда, иначе
#: витрина назовёт сумму, которой магазин не возьмёт.
REGIONAL_CENTS: dict[str, dict[str, int]] = {
    # VAT-neutral: at these points the net after 19–25% EU VAT lands within 1%
    # of the US net, which is the definition of "the same price" rather than a
    # discount or a surcharge.
    "EUR": {"door": 549, "pair": 549, "bundle": 2099, "monthly": 1049},
    # UK consumers pay roughly 8% above the US for digital subscriptions and
    # the market is used to it.
    "GBP": {"door": 499, "pair": 499, "bundle": 1999, "monthly": 999},
    # Switzerland was not in COUNTRY_CURRENCY at all, so Swiss buyers were
    # billed raw USD — the single most under-priced market we had. Swiss VAT is
    # 8.1%, not 20%, and Swiss consumers pay 1.25–1.65x the US price for
    # digital subscriptions (Spotify CHF 15.95 against $11.99; Netflix
    # CHF 22.90 against $17.99). These points net about 135% of the US net.
    "CHF": {"door": 590, "pair": 590, "bundle": 2390, "monthly": 1190},
    "AUD": {"door": 799, "pair": 799, "bundle": 3199, "monthly": 1599},
    "CAD": {"door": 749, "pair": 749, "bundle": 2799, "monthly": 1399},
    "NOK": {"door": 5900, "pair": 5900, "bundle": 21900, "monthly": 10900},
    "DKK": {"door": 3900, "pair": 3900, "bundle": 15900, "monthly": 7900},
    # Purchasing-power markets. Полная полка, а не две строки: см. вывод выше —
    # у магазина нет фиксированной комиссии, из-за которой дешёвый товар был
    # структурно хуже дорогого.
    "BRL": {"door": 1290, "pair": 1290, "bundle": 5190, "monthly": 2590},
    "MXN": {"door": 5900, "pair": 5900, "bundle": 21900, "monthly": 10900},
    "PLN": {"door": 1099, "pair": 1099, "bundle": 4399, "monthly": 2199},
    "TRY": {"door": 6900, "pair": 6900, "bundle": 25900, "monthly": 12900},
    "INR": {"door": 10900, "pair": 10900, "bundle": 43900, "monthly": 21900},
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


def product(key: str) -> Product:
    """Одна строка полки по её **ключу** (`door.natal`), не по слагу системы.

    Названо `key`, а не `slug`, с тех пор как эти два перестали совпадать: в v3
    `PRODUCTS["door.natal"].slug == "natal"`, и вызов `product("natal")` теперь
    честно падает вместо того, чтобы случайно попасть в товар.
    """
    try:
        return PRODUCTS[key]
    except KeyError:
        raise ValueError(f"nothing on sale called {key!r}") from None


def unlocks(system: str) -> str:
    """Какой ключ полки открывает написанные главы этой системы.

    Одно место, потому что таблица «система → цена» уже существует дважды: в
    `locked-chapter-spec.md` §1 и на экране закрытой главы. Третьей копией
    стал бы `if` на клиенте — и разошлась бы она молча, показав кнопку «Unlock
    and read · $4.99» над транзитами, которые разово не продаются вовсе.

    Три случая, и они не про астрологию, а про то, чем товар является:

    * **живая система** — транзиты и соляр переписываются сами, так что
      продать их «навсегда» значит продать подписку и не взять за неё денег.
      Их открывает `sub.monthly`, и только он;
    * **пара** — покупается не система, а отчёт про одного человека, поэтому
      `pair.check`, расходуемый;
    * **всё остальное** — дверь своей системы, `door.{slug}`, навсегда.

    Бандл (`bundle.static`) сюда намеренно не попадает: он открывает те же
    пять систем, но экран закрытой главы обязан назвать **одну** цену (ТЗ §1,
    принцип 2), а бандл живёт тихой ссылкой на «все планы».

    Падает, а не возвращает `None`, на системе, которой нечем открыться:
    беззвучный `None` дошёл бы до экрана кнопкой без цены.
    """
    if system in LIVING_SYSTEMS - {"compatibility"}:
        return "sub.monthly"
    if system == "compatibility":
        return "pair.check"
    key = f"door.{system}"
    if key not in PRODUCTS:
        raise ValueError(f"nothing on the shelf opens {system!r}")
    return key


def by_price_id(price_id: str, processor: str | None = None) -> str | None:
    """Which catalogue **key** carries this processor identifier.

    The key, not the `Product`, because more than one product shares the slug
    `"*"` and a caller holding only the object has to guess its way back to a
    key. The guess that was there — `found.slug if found.kind == "one_time"
    else "annual"` — was wrong in both directions on the same line: an archive
    lookup produced `"*"`, which is not a key, so the payment was recorded and
    nothing granted; a monthly lookup produced `"annual"`, so a month's price
    bought a year. В v3 ключ и слаг разошлись у **всех** строк, не только у
    `"*"`, — тем более нечего угадывать.

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


def catalogue(*, country: str | None = None) -> dict:
    """The price list a client renders. Every number in it is a number we take.

    Only the shelf appears — `on_the_shelf` is the gate, and in v3 it lets all
    eight rows through. Оно всё равно спрашивается: витрина, которая печатает
    `PRODUCTS` целиком, — это витрина, которая опубликует первую же условную
    цену в тот день, когда её заведут.

    Each entry carries its own `kind`, `interval` and `scope`. This used to
    render one hardcoded annual block and filter the annual out of the list, so
    the moment a second recurring plan existed it would have been drawn as a
    one-time purchase — a subscription sold as a single payment is a chargeback
    with a delay on it.

    **Кредита здесь больше нет ни в каком виде.** Подстановка `archive-upgrade`
    вместо `archive` ушла вместе с самими товарами (ТЗ §2), а с ней — параметры
    `credit_cents`/`credit_currency` и ключ-алиас `annual`. Возвращать сюда
    арифметику нельзя: цена, посчитанная в этой функции, — это цена, которой нет
    ни на одном идентификаторе товара, то есть число, которое магазин не возьмёт.
    """
    currency = currency_for(country)
    return {
        "currency": currency,
        "items": [
            _entry(key, item, currency)
            for key, item in PRODUCTS.items()
            if item.on_the_shelf and item.sold_in(currency)
        ],
    }
