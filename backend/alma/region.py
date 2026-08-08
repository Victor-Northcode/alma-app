"""Which country a *request* comes from, and what may honestly follow from it.

This is not `geo.py`. That module answers where somebody was *born* — a place
they typed, resolved against a bundled gazetteer so that a birthplace never
leaves the building. This one answers where the person is *standing right now*,
which is a property of the HTTP request rather than of any data we hold, and it
exists for exactly one reason: `currency_for(None)` returns USD, nobody was
passing a country, and so every visitor on earth was quoted dollars.

── where the truth lives, and why it is not a lookup ──────────────────────────

The server sees the country before the client does, because a real deployment
already put something in front of us that knows it. Cloudflare writes
`CF-IPCountry`; Vercel writes `X-Vercel-IP-Country`; CloudFront, Fastly and App
Engine each write their own. All of them are the answer to "which country did
this TCP connection come from", computed at the edge, for free, on a request
that was going to be proxied anyway.

The alternative was a geo-IP service, and it is refused on principle rather
than on cost. This product ships its own gazetteer specifically so that nobody
has to be told their birthplace was sent to a third party to be looked up. An
IP-to-country call for the sake of a *price* would hand that same third party
every visitor's address, and it would undo the argument entirely — a promise
that holds for the sensitive data and not for the trivial data is not a promise
anybody has to believe.

That is also why `X-Forwarded-For` is read for nothing here. It carries an IP,
and an IP is not a country without either a database we do not ship or a
service we will not call. It is named in this docstring only because it is the
header somebody reaches for next, and finding out here that it cannot answer is
cheaper than finding out after the dependency is in the lockfile.

── whose word wins ───────────────────────────────────────────────────────────

Two sources can name a country: the edge, and the client, which may pass
`?country=`. **The edge wins where it speaks, and the client's word fills the
silence.** See `resolve`.

The rejected alternative was the reverse, and it had a real argument behind it:
a mobile client knows its *store region*, which is the thing that will actually
be charged, and no network can know that. It lost for two reasons. The apps do
not render our figures at all — StoreKit and Play Billing publish the prices the
buyer is charged, and our catalogue is consulted for which rows exist, not for
what they cost — so the one caller that could know better has nothing to gain.
And a rule that differs between "the price we show" and "the price we charge" is
precisely how a shown price and a charged price come apart, which is the failure
this codebase has already had five times.

── what a country may and may not decide ─────────────────────────────────────

It picks a currency, and through the currency it picks which products appear at
all — the purchasing-power markets carry the archive and the year and nothing
else. That is a real, honest consequence: listing a door price to somebody in
Brazil is listing something no store will sell them.

It decides nothing about what anybody is charged. On the web the processor's
own billing country does that, taken from the address the buyer types into the
checkout; in the apps the store's region does, and the store also sets the
number. So a country resolved here is always an *estimate for display*, and any
surface that renders a figure from it has to say so.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

log = logging.getLogger("alma.region")

#: The headers a CDN or platform sets to say which country a connection came
#: from, in the order we believe them. Each is written by the edge and, on the
#: way through, **overwritten** if the client tried to send one — which is the
#: whole basis for trusting them at all.
#:
#: Lower-case because that is how HTTP/2 sends them and how Starlette's
#: case-insensitive mapping compares them; a plain `dict` passed in from a test
#: must use these exact keys.
EDGE_COUNTRY_HEADERS: tuple[str, ...] = (
    "cf-ipcountry",              # Cloudflare
    "x-vercel-ip-country",       # Vercel
    "cloudfront-viewer-country", # AWS CloudFront
    "fastly-client-country",     # Fastly
    "x-appengine-country",       # Google App Engine
)

#: Two-letter codes that are shaped like a country and are not one.
#:
#: Cloudflare answers `XX` when it cannot place an address and `T1` for traffic
#: arriving over Tor; `ZZ` is the ISO user-assigned code various proxies use for
#: the same thing; `EU` and `AP` are MaxMind's continent-level fallbacks.
#:
#: Each of these would fall through `COUNTRY_CURRENCY` to USD anyway, so this
#: set buys nothing in the pricing path. It matters for *language*: "we do not
#: know where this is" and "this is the country XX" are different statements,
#: and only the first one is true.
UNRESOLVED: frozenset[str] = frozenset({"XX", "T1", "ZZ", "EU", "AP", "A1", "A2", "O1"})


def clean_country(value: str | None) -> str | None:
    """A two-letter country code, or nothing.

    Deliberately strict about shape rather than about membership: this does not
    check the code against a list of the world's countries, because that list
    changes and because a country we have never priced is not an error — it is
    a visitor who pays in dollars, which is `currency_for`'s documented
    fallback. What is refused is anything that is not a country code at all,
    including the placeholders an edge sends when it could not tell.
    """
    if not value:
        return None
    code = value.strip().upper()
    if len(code) != 2 or not code.isascii() or not code.isalpha():
        return None
    return None if code in UNRESOLVED else code


def from_headers(headers: Mapping[str, str]) -> str | None:
    """What the network says, or nothing.

    First header that answers wins, rather than a merge: two edges in the same
    request path is a deployment we do not have, and if we ever do, the one
    closest to the client is the one that measured the connection.
    """
    for name in EDGE_COUNTRY_HEADERS:
        found = clean_country(headers.get(name))
        if found is not None:
            return found
    return None


def resolve(*, stated: str | None, edge: str | None) -> str | None:
    """The country to price this request in — the network first, then the client.

    `None` is a real answer and callers must keep it one: it means we do not
    know, and `currency_for(None)` answers USD, which is a stated fallback
    rather than a guess dressed up as a fact.

    The order is the security half of the docstring at the top of this file.
    `stated` is free text on a query string, written by whoever is on the other
    end of the socket; the edge header is written by our own infrastructure and
    overwritten if a client tries to forge it. Since a country selects a
    currency, and currencies differ by a factor of four across the
    purchasing-power markets, believing the client first would make the price
    list something a reader could choose from. Behind a real edge this order
    closes that; in front of no edge it is exactly as good as what came before.
    """
    return clean_country(edge) or clean_country(stated)


#: How many requests have asked this module for a country, and how many times
#: the network answered. Two plain ints and no lock: they are only ever touched
#: from inside the event loop with no `await` between the read and the write, so
#: an increment cannot interleave with another. They are a diagnostic, not a
#: ledger — an undercount by one would change nothing anybody does about it.
_ASKED = 0
_ANSWERED = 0
_WARNED = False


def observe(country: str | None) -> None:
    """Record whether the edge spoke, and say so once if it never does.

    **A fallback that cannot be told apart from a bug should announce itself.**
    With no CDN in front — or with one whose country header is switched off —
    `from_headers` returns `None`, `currency_for(None)` returns USD, and every
    visitor on earth is quoted dollars. That is the honest fallback, and it is
    also exactly the symptom of the defect this module was written to fix: a
    correct-looking response, confidently wrong, in front of somebody about to
    spend money. Verified by hand: a bare `GET /v1/billing/catalogue`, and one
    carrying only `X-Forwarded-For`, both answer `currency: USD` with the full
    eleven-row ladder, and nothing anywhere says why.

    The only way anybody would otherwise find out is by noticing that nobody
    outside the United States is being quoted their own currency, which is a
    thing you notice in a revenue report months later.

    So: one warning the first time a request arrives with no edge country,
    naming the headers that would have answered — and a running count on
    `/ready`, so that "is this deployment actually behind an edge" has an answer
    that does not require reading the logs from boot. One warning rather than
    one per request, because a line on every request is a line nobody reads and
    a log bill somebody pays.
    """
    global _ASKED, _ANSWERED, _WARNED
    _ASKED += 1
    if country is not None:
        _ANSWERED += 1
        return
    if not _WARNED:
        _WARNED = True
        log.warning(
            "no edge country header on this request — every visitor will be "
            "quoted USD until one is set. Expected one of: %s",
            ", ".join(EDGE_COUNTRY_HEADERS),
        )


def observations() -> dict[str, int | bool]:
    """What `/ready` reports about the edge.

    `seen` is the field that matters, and in practice it is three-valued:
    `asked == 0` means nothing has been priced yet and the question is still
    open; `asked > 0` with `seen` false means this deployment has no edge in
    front of it and is quoting USD to everybody; `seen` true means the header is
    arriving and the prices are the visitor's own.
    """
    return {"asked": _ASKED, "answered": _ANSWERED, "seen": _ANSWERED > 0}


def forget_observations() -> None:
    """Reset the counters. For tests, which must not see each other's requests."""
    global _ASKED, _ANSWERED, _WARNED
    _ASKED = 0
    _ANSWERED = 0
    _WARNED = False
