/**
 * Which country a request came from, read off the edge that already knew.
 *
 * The web needs this for one thing only — the language a page is first painted
 * in, before anybody has chosen one. The *currency* is decided by the API,
 * which sees its own request through its own edge and answers with a price
 * list; nothing in the browser passes a country, and that is deliberate, since
 * the one thing a browser genuinely cannot determine about itself is where it
 * is. A `navigator.language` is a language, and `Intl.DateTimeFormat().
 * resolvedOptions().timeZone` is a zone shared by fourteen countries.
 *
 * ── why this duplicates `backend/alma/region.py` ──────────────────────────
 * Because the alternative is a network round trip inside the first paint.
 * `app/layout.tsx` has to know the language before it emits `<html lang>`, and
 * asking the API for it would put an HTTP call in front of the first byte of
 * every server-rendered page — for a question a header on the request we are
 * already handling has answered for free.
 *
 * The duplicated part is a list of header names and the rule that "XX" is not
 * a country. Both are pinned in `country.test.ts` and in
 * `backend/tests/test_region.py`, on both sides, deliberately: a shared
 * constant would need a build step to cross the language boundary, and the
 * cost of the two lists disagreeing is that one surface guesses a language
 * while the other prices in dollars — visible, and not silent.
 *
 * ── what this means for caching ───────────────────────────────────────────
 * The HTML now varies by a request header. Next renders these routes
 * dynamically already, because `cookies()` and `headers()` are read in the root
 * layout, so there is nothing to opt out of; but any CDN put in front of the
 * *web* process has to `Vary` on the country header as well as on `Cookie`, or
 * one visitor's language is served to the next.
 */

/**
 * The headers a CDN or platform sets to say where a connection came from, in
 * the order we believe them.
 *
 * Each is written by the edge and overwritten if the client tried to send one,
 * which is the entire basis for trusting them. Lower-case because HTTP/2 sends
 * them that way; `Headers.get` is case-insensitive regardless.
 *
 * `x-forwarded-for` is deliberately absent. It carries an IP, and an IP is not
 * a country without a database we do not ship or a lookup service we will not
 * call — the same service that would then receive the address of every visitor,
 * which is the argument the bundled gazetteer exists to make.
 */
export const EDGE_COUNTRY_HEADERS = [
  "cf-ipcountry", // Cloudflare
  "x-vercel-ip-country", // Vercel
  "cloudfront-viewer-country", // AWS CloudFront
  "fastly-client-country", // Fastly
  "x-appengine-country", // Google App Engine
] as const;

/**
 * Two-letter codes that are shaped like a country and are not one.
 *
 * Cloudflare answers `XX` for an address it could not place and `T1` for
 * traffic arriving over Tor; `ZZ` is the ISO user-assigned code other proxies
 * use for the same thing, and `EU`/`AP` are continent-level fallbacks.
 *
 * They matter because the country is used to *guess a language*. "We do not
 * know where this is" and "this is the country XX" are different statements and
 * only one of them is true; a `null` falls through to English, which is the
 * documented default, while an unrecognised code would too — by accident, and
 * indistinguishably from a country we simply have no words for.
 */
const UNRESOLVED = new Set(["XX", "T1", "ZZ", "EU", "AP", "A1", "A2", "O1"]);

/** A two-letter country code, or `null`. Shape is checked; membership is not. */
export function cleanCountry(value: string | null | undefined): string | null {
  if (!value) return null;
  const code = value.trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(code)) return null;
  return UNRESOLVED.has(code) ? null : code;
}

/**
 * What the network says, or `null`.
 *
 * Takes anything with a `get` so it can be handed Next's `ReadonlyHeaders`, a
 * real `Headers`, or a plain object in a test — none of which share a type and
 * all of which answer the same question.
 */
export function countryFromHeaders(
  headers: { get(name: string): string | null | undefined },
): string | null {
  for (const name of EDGE_COUNTRY_HEADERS) {
    const found = cleanCountry(headers.get(name));
    if (found !== null) return found;
  }
  return null;
}
