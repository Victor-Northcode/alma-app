/**
 * The language picker, and the two ways it can be silently useless.
 *
 * **It can name languages in the wrong language.** A picker that offers
 * "German, Spanish, French" is a picker for people who already read English,
 * which is precisely the set of people who did not need it. Nothing in the
 * type system distinguishes an endonym from an exonym — both are strings — so
 * the six names are spelled out here, by hand, as the expectation. Reading
 * them back out of the dictionaries would be reading the answer off the paper
 * being marked.
 *
 * **It can set a cookie the server never sees.** The choice is a cookie
 * because SSR has to read it (`lib/locale-server.ts`), and every attribute on
 * that cookie is a decision that fails invisibly when it is wrong: the wrong
 * path and `/support` renders in the negotiated language; `SameSite=Strict`
 * and the choice is dropped for anybody arriving from a link; `Secure` on
 * localhost and the picker appears to do nothing for everybody developing
 * against it. None of that throws.
 */

import { describe, expect, it } from "vitest";

import { LOCALES, LOCALE_STORAGE_KEY, isLocale, type Locale } from "./i18n";
import { LOCALE_COOKIE_MAX_AGE, languageOptions, localeCookie } from "./locale-choice";

/** Each language, written as its own speakers write it. */
const ENDONYM: Record<Locale, string> = {
  en: "English",
  es: "Español",
  de: "Deutsch",
  it: "Italiano",
  fr: "Français",
  "pt-BR": "Português (Brasil)",
};

/** The BCP-47 tag a screen reader needs to pronounce that name. */
const TAG: Record<Locale, string> = {
  en: "en",
  es: "es",
  de: "de",
  it: "it",
  fr: "fr",
  "pt-BR": "pt-BR",
};

describe("what the picker offers", () => {
  it("offers every language the product ships in, and only those", () => {
    expect(languageOptions().map((option) => option.locale)).toEqual([...LOCALES]);
  });

  it("names each language in itself, not in the language being read", () => {
    for (const option of languageOptions()) {
      expect(option.name).toBe(ENDONYM[option.locale]);
    }
  });

  it("gives every option the tag that makes its name pronounceable", () => {
    for (const option of languageOptions()) {
      expect(option.htmlLang).toBe(TAG[option.locale]);
    }
  });

  it("gives no two languages the same name", () => {
    // Two identical rows in a list of six is a person choosing at random. It is
    // the failure a shortened "Português" would cause the day a European
    // Portuguese locale is added beside the Brazilian one.
    const names = languageOptions().map((option) => option.name);
    expect(new Set(names).size).toBe(names.length);
  });

  it("is not sorted by the names it happens to be showing", () => {
    // Collating alphabetically would put Deutsch first and reorder the row
    // beneath somebody who has just switched and is looking back for the
    // language they left. The order is `LOCALES`, which the server shares.
    const names = languageOptions().map((option) => option.name);
    expect(names).not.toEqual([...names].sort((a, b) => a.localeCompare(b)));
  });
});

describe("the cookie the choice is remembered in", () => {
  const attributes = (cookie: string) =>
    Object.fromEntries(
      cookie.split("; ").map((part) => {
        const [name, value = ""] = part.split("=");
        return [name.toLowerCase(), value];
      }),
    ) as Record<string, string>;

  it("is the key the server reads", () => {
    // `locale-server.ts` looks this exact name up in the request's cookies. A
    // rename on one side and not the other produces a picker that changes
    // nothing after a refresh, with no error anywhere.
    for (const locale of LOCALES) {
      expect(localeCookie(locale)).toContain(`${LOCALE_STORAGE_KEY}=`);
    }
  });

  it("carries a value the reader will accept back", () => {
    for (const locale of LOCALES) {
      const written = attributes(localeCookie(locale))[LOCALE_STORAGE_KEY.toLowerCase()];
      expect(isLocale(decodeURIComponent(written))).toBe(true);
      expect(decodeURIComponent(written)).toBe(locale);
    }
  });

  it("is scoped to the whole site, not to the page it was chosen on", () => {
    // The picker is on the landing; the pages that most need the answer —
    // `/support`, the legal routes — are elsewhere and are rendered on the
    // server.
    expect(attributes(localeCookie("de")).path).toBe("/");
  });

  it("survives arriving from somewhere else", () => {
    // `Strict` would withhold the cookie on the first request from any other
    // origin, which is how both of this product's real entrances work: a
    // shared link, and the link inside a sign-in letter.
    expect(attributes(localeCookie("de")).samesite).toBe("Lax");
  });

  it("outlives the visit it was made in", () => {
    // A preference, not a setting for this tab. Anything shorter than a season
    // means the Briton in Spain re-chooses on every visit.
    expect(LOCALE_COOKIE_MAX_AGE).toBeGreaterThanOrEqual(60 * 60 * 24 * 90);
    expect(Number(attributes(localeCookie("de"))["max-age"])).toBe(LOCALE_COOKIE_MAX_AGE);
  });

  it("stays readable by the browser that wrote it", () => {
    // `storedLocale()` reads it back out of `document.cookie`; `HttpOnly`
    // would leave the provider's cross-tab safety net blind to it.
    expect(localeCookie("de").toLowerCase()).not.toContain("httponly");
  });

  it("asks for TLS only where there is TLS", () => {
    // A `Secure` cookie is discarded outright on `http://localhost`, so
    // hard-coding it would break the picker for everyone developing against it
    // and for nobody in production.
    expect(localeCookie("de", { secure: true })).toContain("Secure");
    expect(localeCookie("de", { secure: false })).not.toContain("Secure");
    expect(localeCookie("de")).not.toContain("Secure");
  });
});
