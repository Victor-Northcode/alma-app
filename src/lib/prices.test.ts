/**
 * One rule, tested over everything that could break it: **the interface never
 * holds a price.**
 *
 * Five did, and all five disagreed with what the processor would charge. The
 * landing advertised a $14.99 natal chart against an $8.99 door, a $4.99 single
 * chapter that had been withdrawn, and a plan at "$9.99 · first month $4.99 ·
 * $49.99 a year" against a catalogue that sells $9.99 a month and $78.99 a year
 * with no introductory band anywhere in it. The primary call to action on the
 * page read "Start for $4.99" for an offer nothing in the system could sell.
 * The fixtures carried eight more, one per system.
 *
 * A price typed into the interface is a quote, and the person who finds the
 * disagreement is the buyer. So this walks the dictionaries and the fixtures
 * looking for anything shaped like money, and `priceOf` is asserted to answer
 * with nothing rather than with a remembered figure.
 */

import { describe, expect, it } from "vitest";

import { dictionaries } from "./i18n";
import * as fixtures from "./data";
import { priceOf, type Catalogue } from "./use-catalogue";

/**
 * Anything that reads as an amount of money in the six languages we ship.
 *
 * Deliberately loose — it matches "$4.99", "4,99 €", "R$ 12,90" and "zł 84,99"
 * alike — because the failure being prevented is a number reaching a screen,
 * not a number in one particular notation.
 */
const MONEY = /(?:[$£€₺₹]|R\$|CHF|A\$|C\$|MX\$|zł|kr)\s?\d|\d[\d.,]*\s?(?:€|zł|kr)/;

/**
 * Zero is the one figure the interface may hold.
 *
 * "$0", "0 €", "R$ 0" is not a price we charge — it is the claim that every
 * calculation is free, which is a product decision rather than a catalogue row,
 * and it is zero in every currency the catalogue prices. Nothing can be shown
 * this and then charged something else.
 */
const FREE = /^(?:[$£€₺₹]|R\$|CHF|A\$|C\$|MX\$)\s?0$|^0\s?(?:€|zł|kr)$/;

function strings(value: unknown, path: string, found: string[][]): void {
  if (typeof value === "string") {
    if (MONEY.test(value) && !FREE.test(value.trim())) found.push([path, value]);
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => strings(item, `${path}[${index}]`, found));
    return;
  }
  if (value && typeof value === "object") {
    for (const [key, inner] of Object.entries(value as Record<string, unknown>)) {
      strings(inner, path ? `${path}.${key}` : key, found);
    }
  }
}

describe("no price is written into the interface", () => {
  it("holds no amount of money in any of the six dictionaries", () => {
    const found: string[][] = [];
    for (const [locale, dictionary] of Object.entries(dictionaries)) {
      strings(dictionary, locale, found);
    }
    expect(found).toEqual([]);
  });

  /**
   * Every export of `data.ts`, and not three of them by name.
   *
   * The named list had a hole in it, and a wrong price was sitting in the hole:
   * a fabricated testimonial quoting "€14 once" against a catalogue whose EUR
   * door is €9,49 and whose EUR archive is €40,99. The reviews are gone, but
   * the hole is what let them through, and anything added to this module next
   * would land in the same place. Walking the whole namespace makes the rule
   * enforced rather than remembered.
   *
   * Functions are skipped because they are not strings and cannot be walked;
   * their *output* is a screen's business and is covered where it is rendered.
   */
  it("holds no amount of money anywhere in the reference fixtures", () => {
    const found: string[][] = [];
    for (const [name, value] of Object.entries(fixtures)) {
      if (typeof value === "function") continue;
      strings(value, name, found);
    }
    expect(found).toEqual([]);
  });
});

describe("priceOf", () => {
  const catalogue: Catalogue = {
    currency: "EUR",
    items: [
      {
        slug: "natal", system: "natal", name: "Natal chart", kind: "one_time",
        interval: "", scope: "system", cents: 949, display: "€9,49",
      },
    ],
    provider: "dodo",
    requiresEmail: false,
    merchant: "Dodo Payments",
    unlocked: [],
  };

  it("quotes the catalogue, in the currency the catalogue chose", () => {
    expect(priceOf(catalogue, "natal")).toBe("€9,49");
  });

  it("answers with nothing rather than a fallback figure", () => {
    // A screen that has not loaded the catalogue shows a gap. A gap is a moment
    // of nothing; a remembered price is a number somebody decides to pay
    // against, and then is charged a different one.
    expect(priceOf(catalogue, "archive")).toBe("");
    expect(priceOf(null, "natal")).toBe("");
  });
});
