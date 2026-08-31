/**
 * Locale resolution.
 *
 * Four sources, in falling order of how much they mean: what the person
 * explicitly chose, what their account says, what their browser asked for, and
 * — last — where they are. An explicit choice outranks everything and is never
 * quietly overridden: someone who picked English on a German laptop picked
 * English.
 *
 * ── why the country comes last, and why it is here at all ─────────────────
 * The owner's example is the whole argument: *"вдруг британец из Испании
 * зашёл"* — suppose a Briton in Spain turns up. A browser sending `en-GB` from
 * a Spanish address is asking for English and must get English; a country that
 * outranked the header would hand them a Spanish page and call it
 * localisation.
 *
 * So the country only speaks where the browser said nothing we can use, which
 * is a narrower case than it sounds and a real one: a request with no
 * `Accept-Language` at all, and — much more often — a request asking for a
 * language we do not ship. Somebody in Madrid whose phone is set to Arabic used
 * to get English, because English is the default and `negotiate` could not tell
 * "asked for something we do not have" apart from "asked for nothing". Spanish
 * is the better guess for that person, and it is a guess about *where they are*
 * rather than about who they are, which is why it ranks below anything they
 * said themselves.
 *
 * `preferred` exists so that distinction can be made at all. It returns `null`
 * where `negotiate` returns English, and `negotiate` keeps its old signature
 * because callers that have no country to offer should not have to invent one.
 */

import { de } from "./de";
import { en, type Dictionary } from "./en";
import { es } from "./es";
import { fr } from "./fr";
import { it } from "./it";
import { ptBR } from "./pt-BR";
import { ru } from "./ru";

export type { Dictionary } from "./en";

// Русский — седьмой, добавлен вместе с рублёвой витриной «/pay»
// (владелец, 31.08.2026): покупатель, которого страница оплаты встречает
// по-русски, не должен попадать с неё на английский лендинг.
export const LOCALES = ["en", "es", "de", "it", "fr", "pt-BR", "ru"] as const;
export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "en";

export const dictionaries: Record<Locale, Dictionary> = {
  en,
  es,
  de,
  it,
  fr,
  "pt-BR": ptBR,
  ru,
};

/**
 * The key the choice is remembered under.
 *
 * A cookie rather than localStorage, for one reason: the server has to know.
 * The page title, the `<html lang>` and the first paint are all rendered on
 * the server, and a preference it cannot see produces a German page under an
 * English title — or, worse, a hydration mismatch that throws the tree away.
 * A cookie is the only client preference SSR can read.
 */
export const LOCALE_STORAGE_KEY = "alma.locale";

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

export function dictionary(locale: Locale): Dictionary {
  return dictionaries[locale] ?? en;
}

/**
 * Best match for an `Accept-Language` header or `navigator.languages`, or
 * `null` when the browser asked only for languages we do not ship.
 *
 * The `null` is the point of this function existing beside `negotiate`, which
 * answers English to both "asked for nothing" and "asked for Arabic". Those are
 * different facts and only one of them leaves room for another source to speak:
 * a request with no header is a request we know nothing about, and a request
 * asking for a language we do not have is a person we cannot serve in their own
 * words — where the country they are standing in is a better guess than the
 * default, and `resolveLocale` is where that is decided.
 *
 * Region-aware in the one direction that matters: `pt-BR` is a locale we ship
 * and `pt-PT` is not, so a Portuguese browser gets Brazilian Portuguese rather
 * than English. Any other `pt` does too — it is far closer than the fallback.
 */
export function preferred(
  accepted: string | readonly string[] | null | undefined,
): Locale | null {
  if (!accepted) return null;

  const candidates =
    typeof accepted === "string"
      ? accepted
          .split(",")
          .map((part) => {
            const [tag, q] = part.trim().split(";q=");
            return { tag: tag.trim(), q: q ? Number(q) : 1 };
          })
          .sort((a, b) => b.q - a.q)
          .map((entry) => entry.tag)
      : [...accepted];

  for (const raw of candidates) {
    const tag = raw.toLowerCase();
    if (tag === "pt-br" || tag.startsWith("pt")) return "pt-BR";

    const exact = LOCALES.find((locale) => locale.toLowerCase() === tag);
    if (exact) return exact;

    const base = tag.split("-")[0];
    const loose = LOCALES.find((locale) => locale.toLowerCase().split("-")[0] === base);
    if (loose) return loose;
  }
  return null;
}

/**
 * Best match for a browser's languages, falling back to English.
 *
 * Kept as its own export rather than folded into `preferred`, because most
 * callers have nothing else to offer and a function that can return `null`
 * makes each of them decide what to do about it — six copies of `?? "en"`, five
 * of which stay right.
 */
export function negotiate(accepted: string | readonly string[] | null | undefined): Locale {
  return preferred(accepted) ?? DEFAULT_LOCALE;
}

/**
 * Which of the six a country is a reason to guess, where it is a reason at all.
 *
 * Only countries whose majority language is one we ship *and* which have one
 * such language. The omissions are the interesting part:
 *
 * - **Switzerland, Belgium, Luxembourg, Canada.** Each has two or more of our
 *   six as an official language. A coin flip between German and French is not a
 *   better guess than the default; it is the same guess with a confident face
 *   on. They fall through to English, which every one of those countries reads
 *   as the neutral choice anyway.
 * - **The English-speaking countries.** `DEFAULT_LOCALE` already answers for
 *   them, and an entry that restates the default is a second place to be wrong
 *   the day the default moves.
 * - **Countries where a language we ship is official but not what people speak
 *   at home.** Administrative French is not a reason to hand somebody a page in
 *   it; the browser's own header is a far better signal there and it is the one
 *   that already outranks this table.
 *
 * Portuguese-speaking countries all map to `pt-BR` because that is the only
 * Portuguese we have — the same rule `preferred` already applies to a `pt-PT`
 * browser, stated once more here so the two cannot disagree.
 */
export const COUNTRY_LANGUAGE: Readonly<Record<string, Locale>> = {
  // Spanish
  ES: "es", MX: "es", AR: "es", CO: "es", CL: "es", PE: "es", VE: "es",
  EC: "es", GT: "es", CU: "es", BO: "es", DO: "es", HN: "es", PY: "es",
  SV: "es", NI: "es", CR: "es", PA: "es", UY: "es", GQ: "es",
  // German
  DE: "de", AT: "de", LI: "de",
  // Italian
  IT: "it", SM: "it", VA: "it",
  // French
  FR: "fr", MC: "fr",
  // Portuguese — Brazil's, everywhere, because it is the one we have
  BR: "pt-BR", PT: "pt-BR", AO: "pt-BR", MZ: "pt-BR", CV: "pt-BR",
  GW: "pt-BR", ST: "pt-BR",
  // Russian — Russia and Belarus, where it is the majority home language.
  // Deliberately NOT the rest of the CIS: Kazakhstan, Ukraine and the
  // Baltics each have their own first language, and a Russian page there
  // is a guess about politics as much as about words; the browser header
  // outranks this table for anyone who actually asked for Russian.
  RU: "ru", BY: "ru",
};

/** What being in this country is worth as a guess, or `null`. */
export function localeForCountry(country: string | null | undefined): Locale | null {
  if (!country) return null;
  return COUNTRY_LANGUAGE[country.trim().toUpperCase()] ?? null;
}

/**
 * Read the remembered choice from the cookie, if there is one.
 *
 * For a while this had a reader and no writer: the cabinet's settings screen
 * was the only thing that ever set the cookie, and it was deleted. The reader
 * stayed because the precedence rule was right and because `app/layout.tsx`
 * needs it server-side to pick the title and `<html lang>` before the first
 * paint. `LanguagePicker` is the writer now, through `setLocale` in
 * `i18n/provider.tsx`, and `lib/locale-choice.ts` owns what that cookie says.
 *
 * **This is the browser's only source of the locale, and it has to stay the
 * only one.** The server resolves the language from three things — this
 * cookie, `Accept-Language`, and the country the request came from — and hands
 * the result down as `initial`. Two of the three are invisible to the browser.
 * Anything here that tried to negotiate a locale of its own would disagree with
 * the server for every visitor whose language came from a header, and a
 * disagreement during hydration is not one wrong word on a page: React throws
 * the tree away and rebuilds it.
 */
export function storedLocale(): Locale | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${LOCALE_STORAGE_KEY}=([^;]*)`),
  );
  const value = match ? decodeURIComponent(match[1]) : null;
  return isLocale(value) ? value : null;
}

/**
 * What the app should open in, given everything it knows.
 *
 * The precedence is the whole of the rule and it is stated once, here, so that
 * the server-rendered pages and anything client-side cannot answer differently
 * for the same request — which on a hydrating page is not a disagreement, it is
 * React throwing the tree away.
 *
 *  1. **What the person chose.** The cookie. Never overridden by anything
 *     below it, in either direction: a Briton who taps "Español" in Madrid
 *     keeps Spanish, and a Briton who taps nothing keeps English.
 *  2. **What their account says**, for a signed-in reader on a second device.
 *  3. **What their browser asked for.** A stated preference, made once, in the
 *     operating system, by somebody who meant it.
 *  4. **Where they are.** Only when the three above said nothing usable. See
 *     `COUNTRY_LANGUAGE` for which countries are a reason to guess at all.
 *  5. English.
 */
export function resolveLocale(options: {
  explicit?: string | null;
  account?: string | null;
  browser?: string | readonly string[] | null;
  /** Two-letter country code from the edge — see `lib/country.ts`. */
  country?: string | null;
}): Locale {
  if (isLocale(options.explicit)) return options.explicit;
  if (isLocale(options.account)) return options.account;
  return preferred(options.browser) ?? localeForCountry(options.country) ?? DEFAULT_LOCALE;
}
