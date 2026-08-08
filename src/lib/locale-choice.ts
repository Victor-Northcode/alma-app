/**
 * Choosing a language, from the browser.
 *
 * The reading half of this — cookie first, then `Accept-Language` — is
 * `lib/i18n/index.ts` and `lib/locale-server.ts`. This is the writing half,
 * which had no implementation at all: the locale was negotiated from the
 * header and there was no control anywhere in the interface to disagree with
 * it. A Briton in Spain was handed a Spanish page with no way out of it.
 *
 * ── why a cookie, again ───────────────────────────────────────────────────
 * Because the server has to know. `app/layout.tsx` picks `<html lang>` and the
 * page title before anything is painted, and `/support` renders its sentences
 * server-side for an App Review employee opening it cold. A preference in
 * localStorage is invisible to all of that: the page would arrive in one
 * language and hydrate into another, which React resolves by throwing the tree
 * away. So writing the choice means writing a cookie and then asking the
 * server to render again — see `setLocale` in `lib/i18n/provider.tsx`.
 *
 * ── why this file is not in `src/lib/i18n/` ───────────────────────────────
 * The same reason `locale-server.ts` is not: `scripts/check-locales.mjs`
 * enumerates every `.ts` file in that directory and audits it as a language.
 * A helper dropped in beside the dictionaries would be counted as a seventh
 * locale with no keys, and the script's closing line would quietly start
 * reporting a number that is not true.
 */

import { LOCALES, LOCALE_STORAGE_KEY, dictionaries, type Locale } from "./i18n";

/** One language, as the picker has to show it. */
export interface LanguageOption {
  locale: Locale;
  /**
   * The language's name **in itself** — Deutsch, not German.
   *
   * This is the whole point of the control and the one detail it cannot get
   * wrong. Somebody who cannot read the page they are looking at cannot read
   * that page's word for their own language either, so an exonym list is a
   * picker only for people who did not need one. It is read out of each
   * dictionary's own `meta.name`, which means the name travels with the
   * translation and cannot drift from it.
   *
   * Not a flag. A flag is a country: Spanish is not Spain to most of the
   * people who speak it, Portuguese here is Brazil's and not Portugal's, and
   * French belongs to no single square of colour. The word is unambiguous and
   * the icon is not.
   */
  name: string;
  /**
   * The BCP-47 tag, put on the option's `lang` attribute so a screen reader
   * pronounces "Français" in French instead of sounding it out in the voice
   * of the page it is sitting on.
   */
  htmlLang: string;
}

/**
 * The six, in the order they are offered.
 *
 * Deliberately not sorted by anything the current language decides —
 * alphabetising "Deutsch, English, Español…" by the reader's collation would
 * reorder the list under somebody who switched languages and then went looking
 * for the one they had just left. `LOCALES` order is fixed and shared with the
 * server.
 */
export function languageOptions(): readonly LanguageOption[] {
  return LOCALES.map((locale) => ({
    locale,
    name: dictionaries[locale].meta.name,
    htmlLang: dictionaries[locale].meta.htmlLang,
  }));
}

/**
 * What this language calls itself.
 *
 * For the one control that has to name a language without room to show six:
 * the nav's toggle, which reads "Deutsch" to a German reader and opens the row
 * that holds the other five. Read from the same `meta.name` the picker reads,
 * so the bar and the row cannot disagree about what a language is called.
 */
export function languageName(locale: Locale): string {
  return dictionaries[locale].meta.name;
}

/**
 * A year.
 *
 * Long enough that the choice outlives the visit it was made in, which is the
 * only thing that makes it a preference rather than a setting. A session
 * cookie would forget a Briton in Spain every time they closed the tab, and
 * they would meet the Spanish page again on the next visit having already told
 * us once.
 */
export const LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

/**
 * The `document.cookie` string that remembers a choice.
 *
 * Built here, as a pure string, rather than written inline in the click
 * handler — every attribute on it is a decision that can be silently wrong,
 * and a wrong one fails in a way nobody sees in development:
 *
 * - **`Path=/`** — without it the cookie is scoped to the page it was set on,
 *   so a choice made on the landing would be invisible to `/support` and the
 *   legal routes, which are exactly the server-rendered pages that read it.
 * - **`SameSite=Lax`** — `Strict` would drop the cookie on arrival from any
 *   other site. The two ways people reach this website are a shared link and
 *   the link in a sign-in letter, and under `Strict` both would land in the
 *   negotiated language with the person's own choice sitting unusable in the
 *   jar.
 * - **no `HttpOnly`** — it cannot have it. `storedLocale()` reads this back
 *   from `document.cookie` in the browser, and the whole mechanism is a client
 *   preference the server is allowed to overhear.
 * - **`Secure` only where there is TLS** — a `Secure` cookie is discarded
 *   outright on `http://localhost`, which would make the picker appear to do
 *   nothing for everybody developing against it.
 *
 * There is nothing private in the value: it is one of six public strings, and
 * it says which language somebody reads.
 */
export function localeCookie(locale: Locale, options: { secure?: boolean } = {}): string {
  const parts = [
    `${LOCALE_STORAGE_KEY}=${encodeURIComponent(locale)}`,
    "Path=/",
    `Max-Age=${LOCALE_COOKIE_MAX_AGE}`,
    "SameSite=Lax",
  ];
  if (options.secure) parts.push("Secure");
  return parts.join("; ");
}
