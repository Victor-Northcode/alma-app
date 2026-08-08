/**
 * Where the visitor is, and the two different things that follow from it.
 *
 * The bug underneath all of this was silent in the way that matters:
 * `useCatalogue(country?)` took a country, nothing passed one, and
 * `currency_for(None)` answers USD — which is exactly what a developer in the
 * United States sees when everything is working. Every visitor on earth was
 * quoted dollars and no screen looked broken. The language half was the same
 * shape: `negotiate` answered English both to a request with no header and to a
 * request asking for a language we do not ship, so a phone set to Arabic in
 * Madrid got English and there was no way to tell that from a correct answer.
 *
 * So these tests are about *precedence* and about the difference between an
 * answer and a fallback. The currency half is proved on the server, in
 * `backend/tests/test_region.py`, because that is where it is decided; what is
 * proved here is the language, the header reading that feeds it, and the one
 * property a server-rendered page cannot be wrong about — that the browser
 * reaches the same answer the server did.
 */

import { afterEach, describe, expect, it } from "vitest";

import { cleanCountry, countryFromHeaders, EDGE_COUNTRY_HEADERS } from "./country";
import {
  COUNTRY_LANGUAGE,
  DEFAULT_LOCALE,
  LOCALES,
  LOCALE_STORAGE_KEY,
  localeForCountry,
  negotiate,
  preferred,
  resolveLocale,
  storedLocale,
  type Locale,
} from "./i18n";
import { localeCookie } from "./locale-choice";
import { offers, priceOf, type Catalogue } from "./use-catalogue";

/** A `Headers`-shaped object over a plain record. */
function head(values: Record<string, string>): { get(name: string): string | null } {
  return { get: (name) => values[name.toLowerCase()] ?? null };
}

describe("reading the country off the edge", () => {
  it.each(EDGE_COUNTRY_HEADERS)("reads %s", (header) => {
    // Each name in the list is wired rather than merely documented. A tuple of
    // header names is the kind of thing that grows a typo and stays plausible
    // for a year, because the deployment that needed the fifth entry is not the
    // one anybody develops against.
    expect(countryFromHeaders(head({ [header]: "de" }))).toBe("DE");
  });

  it("believes the first edge to answer", () => {
    expect(
      countryFromHeaders(head({ "cf-ipcountry": "ES", "x-vercel-ip-country": "US" })),
    ).toBe("ES");
  });

  it("does not try to read a country out of an IP address", () => {
    // `X-Forwarded-For` is on every proxied request and answers a different
    // question. Getting a country out of it needs a database we do not ship or
    // a service we will not call — and that service would receive the address
    // of every visitor, which is the argument the bundled gazetteer exists to
    // make.
    expect(EDGE_COUNTRY_HEADERS).not.toContain("x-forwarded-for");
    expect(countryFromHeaders(head({ "x-forwarded-for": "203.0.113.7" }))).toBeNull();
  });

  it.each(["XX", "T1", "ZZ", "EU", "AP"])(
    "treats %s as the edge saying it does not know",
    (code) => {
      // Not the same as a country we have no words for: that one falls through
      // to English by rule, and this one has to fall through because there is
      // nothing to fall through *from*. Keeping them distinguishable is the
      // difference between a default and a wrong fact.
      expect(countryFromHeaders(head({ "cf-ipcountry": code }))).toBeNull();
    },
  );

  it.each(["", "  ", "D", "DEU", "d3", "??"])("refuses %p", (value) => {
    expect(cleanCountry(value)).toBeNull();
  });

  it("is not case- or whitespace-sensitive", () => {
    expect(cleanCountry(" es ")).toBe("ES");
  });

  it("answers nothing when nothing in front of us knows", () => {
    // The ordinary development case, and the honest answer for a deployment
    // with no CDN. Nothing downstream may turn it into a guess.
    expect(countryFromHeaders(head({}))).toBeNull();
  });
});

/**
 * The other half of what a country decides, and the one that had no test at all
 * because it had never happened: until the country reached the server, every
 * price list was the US one, and the US one contains everything.
 *
 * The five purchasing-power markets carry the archive and the year and nothing
 * else — a PPP-fair door is small enough that local VAT plus the flat
 * per-transaction fee eats a third of it. Measured against a Brazilian edge, the
 * catalogue answers `BRL` with two items in it, and the landing has to draw two
 * rows rather than three with a blank in one of them.
 */
describe("a market is not shown a product it is not sold", () => {
  const brazil: Catalogue = {
    currency: "BRL",
    items: [
      {
        slug: "archive", system: "*", name: "The whole archive", kind: "one_time",
        interval: "", scope: "all", cents: 9990, display: "R$ 99,90",
      },
    ],
    provider: "appstore",
    requiresEmail: false,
    merchant: "Apple",
    unlocked: [],
  };

  it("draws no row for a door that does not exist in this market", () => {
    expect(offers(brazil, "natal")).toBe(false);
    expect(priceOf(brazil, "natal")).toBe("");
  });

  it("draws the rows this market does have", () => {
    expect(offers(brazil, "archive")).toBe(true);
  });

  it("draws every row while the answer is still in flight", () => {
    // Honest rather than convenient: before the catalogue lands we do not know
    // which market this is, and almost every market sells the door. The row
    // appears with the empty figure every price on that page has while loading.
    // Hiding all of them until the request returns would blank the pricing
    // section for the whole world to spare five markets one row.
    expect(offers(null, "natal")).toBe(true);
    expect(priceOf(null, "natal")).toBe("");
  });
});

describe("what a country is worth as a guess about language", () => {
  it("maps a country to the language it actually speaks", () => {
    expect(localeForCountry("ES")).toBe("es");
    expect(localeForCountry("AT")).toBe("de");
    expect(localeForCountry("br")).toBe("pt-BR");
  });

  it("gives Portugal the only Portuguese we have", () => {
    // The same rule `preferred` applies to a `pt-PT` browser. A Portuguese
    // reader handed Brazilian Portuguese is reading their own language written
    // slightly elsewhere; handed English, they are reading somebody else's.
    expect(localeForCountry("PT")).toBe("pt-BR");
  });

  it("declines to guess in a country with two of our languages", () => {
    // Switzerland, Belgium, Luxembourg, Canada. A coin flip between German and
    // French is not a better answer than the default — it is the same guess
    // wearing a confident face, and it is wrong for half the country.
    for (const country of ["CH", "BE", "LU", "CA"]) {
      expect(localeForCountry(country)).toBeNull();
    }
  });

  it("has nothing to say about a country we have no words for", () => {
    expect(localeForCountry("KE")).toBeNull();
    expect(localeForCountry("JP")).toBeNull();
  });

  it("never names a language we do not ship", () => {
    for (const locale of Object.values(COUNTRY_LANGUAGE)) {
      expect(LOCALES).toContain(locale);
    }
  });

  it("does not restate the default", () => {
    // An entry for the English-speaking countries would be a second place to be
    // wrong the day `DEFAULT_LOCALE` moves, and it would say nothing the
    // fallback does not already say.
    for (const country of ["US", "GB", "AU", "NZ", "IE"]) {
      expect(COUNTRY_LANGUAGE[country]).toBeUndefined();
    }
  });
});

describe("preferred, and the difference between silence and a miss", () => {
  it("answers nothing when the browser asked for nothing", () => {
    expect(preferred(null)).toBeNull();
    expect(preferred("")).toBeNull();
  });

  it("answers nothing when the browser asked for a language we do not ship", () => {
    // This is the case that used to be indistinguishable from a correct
    // English answer, and it is the only case where the country gets to speak.
    expect(preferred("ar,ja;q=0.8")).toBeNull();
  });

  it("still honours quality values and region tags", () => {
    expect(preferred("de-AT,de;q=0.9,en;q=0.5")).toBe("de");
    expect(preferred("en-GB")).toBe("en");
    expect(preferred("pt-PT")).toBe("pt-BR");
  });

  it("leaves negotiate answering English, for callers with nothing else", () => {
    expect(negotiate("ar")).toBe(DEFAULT_LOCALE);
    expect(negotiate(null)).toBe(DEFAULT_LOCALE);
  });
});

describe("precedence, in every order", () => {
  it("gives the Briton in Spain English", () => {
    // The owner's own example, and the reason the country ranks below the
    // browser rather than above it. `en-GB` from a Spanish address is a person
    // asking for English; a country that outranked the header would hand them a
    // Spanish page and call it localisation.
    expect(resolveLocale({ browser: "en-GB,en;q=0.9", country: "ES" })).toBe("en");
  });

  it("lets the country speak when the browser asked for nothing we have", () => {
    expect(resolveLocale({ browser: "ar,fa;q=0.9", country: "ES" })).toBe("es");
    expect(resolveLocale({ browser: null, country: "DE" })).toBe("de");
  });

  it("lets an explicit choice beat the browser and the country together", () => {
    // Somebody who taps a language has said something about themselves that no
    // header and no address can contradict.
    expect(
      resolveLocale({ explicit: "en", browser: "de-DE", country: "DE" }),
    ).toBe("en");
    expect(
      resolveLocale({ explicit: "it", browser: "en-GB", country: "ES" }),
    ).toBe("it");
  });

  it("lets an account beat the browser and the country", () => {
    expect(resolveLocale({ account: "fr", browser: "de-DE", country: "DE" })).toBe("fr");
  });

  it("lets an explicit choice beat the account", () => {
    expect(resolveLocale({ explicit: "de", account: "fr" })).toBe("de");
  });

  it("ignores a stored value that is not one of the six", () => {
    // A cookie is user-writable and survives a deploy that removed a language.
    expect(resolveLocale({ explicit: "ru", browser: "de-DE" })).toBe("de");
    expect(resolveLocale({ explicit: "ru", country: "ES" })).toBe("es");
  });

  it("falls to English when nothing knows anything", () => {
    expect(resolveLocale({})).toBe(DEFAULT_LOCALE);
    expect(resolveLocale({ browser: "ar", country: "KE" })).toBe(DEFAULT_LOCALE);
  });

  it("is not confused by an edge that could not place the address", () => {
    // `cleanCountry` has already turned "XX" into null by the time this runs;
    // the assertion is that nothing downstream reinvents it as a country.
    expect(
      resolveLocale({ browser: "ar", country: countryFromHeaders(head({ "cf-ipcountry": "XX" })) }),
    ).toBe(DEFAULT_LOCALE);
  });
});

/**
 * The property that cannot be tested by looking at either half alone.
 *
 * The server resolves the locale from three things it can see — the cookie, the
 * `Accept-Language` header and the country header — and hands the answer to
 * `LocaleProvider` as `initial`. The browser can see exactly one of those three.
 * If it tried to resolve the locale itself it would disagree with the server for
 * every visitor whose language came from the header or the country, and a
 * disagreement during hydration is not a wrong word on the page: React discards
 * the tree and rebuilds it.
 *
 * So the client's only source is the cookie, and these assert that this stays
 * true in both directions.
 */
describe("SSR and the browser reach the same answer", () => {
  const realDocument = (globalThis as { document?: unknown }).document;

  afterEach(() => {
    if (realDocument === undefined) delete (globalThis as { document?: unknown }).document;
    else (globalThis as { document?: unknown }).document = realDocument;
  });

  function browserCookie(jar: string): void {
    (globalThis as { document?: unknown }).document = { cookie: jar };
  }

  it("leaves a country-decided language alone, because there is no cookie to read", () => {
    // A visitor in Madrid with an Arabic phone is served Spanish by the server.
    // Nothing in the browser can re-derive that, and nothing tries: `storedLocale`
    // finds no cookie, the provider keeps `initial`, and the markup matches.
    const server = resolveLocale({ browser: "ar", country: "ES" });
    expect(server).toBe("es");

    browserCookie("");
    expect(storedLocale()).toBeNull();
  });

  it.each(LOCALES)("agrees with the server about a chosen %s", (locale: Locale) => {
    // The picker writes this exact cookie string; the server reads the same key
    // out of the request. Round-tripping through `localeCookie` rather than
    // hand-writing the pair is the point — a rename of the key would otherwise
    // pass this test and break the page.
    browserCookie(localeCookie(locale).split(";")[0]);
    expect(storedLocale()).toBe(locale);
    expect(
      resolveLocale({ explicit: locale, browser: "en-GB", country: "ES" }),
    ).toBe(locale);
  });

  it("agrees that a corrupted cookie is not a choice", () => {
    browserCookie(`${LOCALE_STORAGE_KEY}=klingon`);
    expect(storedLocale()).toBeNull();
    expect(resolveLocale({ explicit: "klingon", browser: "de-DE" })).toBe("de");
  });
});
