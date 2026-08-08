"""Where a request comes from, and the price list that follows.

The bug this file exists because of is not subtle and was invisible for the
same reason: `currency_for(None)` answers USD, no caller ever passed a country,
and USD is what a developer in the United States sees when everything is
working. Every visitor on earth was quoted dollars and nothing anywhere looked
broken.

So the tests are about precedence rather than about any single header. The
interesting cases are all disagreements — the client says one thing and the
connection says another — plus the two answers that have to stay *answers*
rather than fallbacks: a country we have never priced pays in dollars, and a
country nobody could determine is `None` rather than the string "XX".
"""

from __future__ import annotations

import pytest

from alma import region
from alma.billing import catalogue as prices


# ── reading the network's answer ───────────────────────────────────────────

@pytest.mark.parametrize("header", region.EDGE_COUNTRY_HEADERS)
def test_every_edge_we_name_is_actually_read(header: str):
    """Each header in the list is wired, not merely documented.

    A tuple of header names is the kind of thing that grows a typo and stays
    plausible for a year: the deployment that needed the fifth entry is not the
    deployment anyone is testing on.
    """
    assert region.from_headers({header: "de"}) == "DE"


def test_the_first_edge_to_answer_is_believed():
    """Two edges in one path is a deployment we do not have; if we ever do, the
    one closest to the client measured the connection."""
    assert region.from_headers({"cf-ipcountry": "ES", "x-vercel-ip-country": "US"}) == "ES"


def test_a_header_the_edge_did_not_set_is_silence_not_a_country():
    assert region.from_headers({}) is None
    assert region.from_headers({"x-forwarded-for": "203.0.113.7"}) is None


def test_an_ip_is_not_a_country():
    """`X-Forwarded-For` is present on every proxied request and answers a
    different question. Reading it would need a database we do not ship or a
    service we will not call — the same service that would receive every
    visitor's address, which is the argument the bundled gazetteer exists to
    make."""
    assert "x-forwarded-for" not in region.EDGE_COUNTRY_HEADERS


@pytest.mark.parametrize("code", sorted(region.UNRESOLVED))
def test_the_edge_saying_it_does_not_know_is_not_a_country(code: str):
    """Cloudflare answers `XX` for an address it cannot place and `T1` for Tor.

    Treating either as a country is not merely useless — `currency_for` would
    fall through to USD either way — it is a false statement, and the language
    rule on the web reads the same value. "We do not know where this is" and
    "this is the country XX" have to stay distinguishable.
    """
    assert region.from_headers({"cf-ipcountry": code}) is None


@pytest.mark.parametrize("value", ["", "  ", "D", "DEU", "d3", "??", "ES;US"])
def test_anything_that_is_not_a_country_code_is_refused(value: str):
    assert region.clean_country(value) is None


def test_case_and_whitespace_are_not_a_different_country():
    assert region.clean_country(" es ") == "ES"
    assert region.clean_country("es") == "ES"


def test_a_country_we_have_never_priced_is_still_a_country():
    """The shape is checked; membership of a list of the world is not.

    Kenya is not in `COUNTRY_CURRENCY` and never will be until somebody prices
    it. That is a visitor who pays in dollars — the documented fallback — and
    not an error, and not a reason for this module to hold a second copy of
    ISO 3166 that goes stale the next time a country changes its name.
    """
    assert region.clean_country("KE") == "KE"
    assert prices.currency_for("KE") == "USD"


# ── precedence, in every order ─────────────────────────────────────────────

def test_the_network_outranks_the_client():
    """`?country=` is free text written by whoever is on the other end of the
    socket; the edge header is written by our own infrastructure and overwritten
    if a client tries to forge one. Since a country picks a currency, and the
    purchasing-power markets are a quarter of the US price, believing the client
    first would make the price list something a reader could choose from."""
    assert region.resolve(stated="IN", edge="US") == "US"


def test_the_client_is_believed_when_the_network_is_silent():
    """No edge in front of the process is the ordinary development case, and it
    is also every test in this suite that pins a market by name."""
    assert region.resolve(stated="BR", edge=None) == "BR"


def test_neither_is_a_real_answer():
    """`None` has to survive to `currency_for`, which answers USD *deliberately*.
    Inventing "US" here would turn a stated fallback into a claim about where
    somebody is."""
    assert region.resolve(stated=None, edge=None) is None
    assert prices.currency_for(None) == "USD"


def test_an_unusable_edge_answer_lets_the_client_speak():
    """`XX` is the edge saying it does not know, which is not the same as the
    edge disagreeing. A client that knows its own market should not be silenced
    by a header that said nothing."""
    assert region.resolve(stated="DE", edge="XX") == "DE"


def test_an_unusable_client_answer_does_not_erase_the_network():
    assert region.resolve(stated="", edge="FR") == "FR"
    assert region.resolve(stated="not-a-country", edge="FR") == "FR"


# ── what actually reaches a reader ─────────────────────────────────────────

@pytest.mark.parametrize(
    "country,currency",
    [("DE", "EUR"), ("GB", "GBP"), ("BR", "BRL"), ("CH", "CHF"), ("KE", "USD")],
)
def test_the_resolved_country_reaches_the_price_list(country: str, currency: str):
    listing = prices.catalogue(country=region.resolve(stated=None, edge=country))
    assert listing["currency"] == currency


def test_a_market_that_does_not_sell_a_door_does_not_list_one():
    """The five purchasing-power markets carry the archive and the year and
    nothing else, because a PPP-fair door is eaten by local VAT plus the flat
    per-transaction fee. Now that a country actually arrives, this stops being
    theoretical: a landing page that lists a door price to somebody in Brazil is
    listing something no store will sell them."""
    brazil = prices.catalogue(country="BR")
    slugs = {item["slug"] for item in brazil["items"]}
    assert slugs == {"archive", "annual"}

    home = prices.catalogue(country="US")
    assert "natal" in {item["slug"] for item in home["items"]}


# ── over HTTP, which is where it has to be true ────────────────────────────

def test_the_catalogue_prices_the_country_the_edge_reports(api):
    response = api.get("/v1/billing/catalogue", headers={"CF-IPCountry": "DE"})
    assert response.status_code == 200
    assert response.json()["currency"] == "EUR"


def test_a_visitor_with_no_edge_in_front_is_quoted_dollars(api):
    """Not a bug and the reason the bug survived: this is what a developer sees
    on localhost, and it is the honest answer when nothing knows where somebody
    is."""
    assert api.get("/v1/billing/catalogue").json()["currency"] == "USD"


def test_the_query_string_cannot_undercut_the_network(api):
    """The one that is worth an HTTP test rather than a unit test: the
    precedence has to survive FastAPI's parameter binding, because a route that
    reads `country` instead of the resolved value looks identical in review."""
    response = api.get(
        "/v1/billing/catalogue?country=IN", headers={"CF-IPCountry": "GB"}
    )
    assert response.json()["currency"] == "GBP"


def test_the_price_list_tells_a_cache_it_depends_on_the_country(api):
    """The failure this prevents is a CDN serving Germany's prices to Brazil.

    `GET /v1/billing/catalogue` is a plain cacheable GET whose body now varies by
    a request header. Nothing caches it today; the declaration exists so that
    the day something does, it is already correct rather than discovered by a
    buyer being shown a number in the wrong currency.
    """
    vary = api.get("/v1/billing/catalogue").headers.get("vary", "").lower()
    for header in region.EDGE_COUNTRY_HEADERS:
        assert header in vary


def test_reading_a_price_still_creates_nobody(api):
    """The catalogue is the request a page view makes first, and it takes
    `Visitor` for that reason. Adding a dependency to the signature is exactly
    the kind of edit that quietly puts `CurrentUser` back."""
    response = api.get("/v1/billing/catalogue", headers={"CF-IPCountry": "ES"})
    assert response.status_code == 200
    assert "X-Alma-Token" not in response.headers


# ── saying so when nothing is in front of us ───────────────────────────────

def test_a_deployment_with_no_edge_can_be_told_apart_from_one_in_america(api):
    """The fallback and the bug produce byte-identical responses.

    With no CDN in front — or with one whose country header is switched off —
    `from_headers` answers `None`, `currency_for(None)` answers USD, and the
    whole world is quoted dollars. That is the documented, honest fallback. It
    is also, exactly, the symptom of the defect this module was written to
    remove, and the only way anybody would otherwise notice is by wondering
    months later why nobody outside the United States is being quoted their own
    currency.

    So the service says which of the two it is. This asserts the distinction
    rather than the wording: after a request that carried no edge header,
    `/ready` reports that it was asked and not answered; after one that did,
    `seen` is true. A `/ready` that always said the same thing would be no
    better than the silence it replaces.
    """
    region.forget_observations()

    api.get("/v1/billing/catalogue")
    blind = api.get("/ready").json()["edge_country"]
    assert blind["asked"] >= 1
    assert blind["answered"] == 0
    assert blind["seen"] is False

    api.get("/v1/billing/catalogue", headers={"CF-IPCountry": "DE"})
    sighted = api.get("/ready").json()["edge_country"]
    assert sighted["answered"] == 1
    assert sighted["seen"] is True


def test_the_first_blind_request_says_so_in_the_log(api, caplog):
    """Once, not per request: a line on every request is a line nobody reads.

    The names of the headers are in the message because the person reading it
    is deciding what to configure, and "no edge country" without them is a
    sentence that sends somebody to the source.
    """
    region.forget_observations()
    with caplog.at_level("WARNING", logger="alma.region"):
        api.get("/v1/billing/catalogue")
        api.get("/v1/billing/catalogue")
        api.get("/v1/billing/catalogue")

    warnings = [r for r in caplog.records if r.name == "alma.region"]
    assert len(warnings) == 1
    assert "CF-IPCountry".lower() in warnings[0].getMessage().lower()


def test_an_edge_that_speaks_is_never_warned_about(api, caplog):
    region.forget_observations()
    with caplog.at_level("WARNING", logger="alma.region"):
        api.get("/v1/billing/catalogue", headers={"CF-IPCountry": "BR"})
    assert [r for r in caplog.records if r.name == "alma.region"] == []
