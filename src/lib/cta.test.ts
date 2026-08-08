/**
 * What the buttons on the landing page are allowed to promise.
 *
 * Every gold control on this website opens the same free journey overlay, and
 * the failure this guards is not a crash — every one of them rendered a
 * perfectly good sentence. It is a button describing a product that does not
 * exist. "Sign up" shipped for months on a website that mints no account; in
 * Spanish and Brazilian Portuguese it read *create an account* outright, which
 * is a specific thing to have promised somebody and then not done.
 *
 * The type system cannot see any of this: a label is a string and every string
 * type-checks. So the rules are asserted here, in all six languages, because
 * the one that was wrong was wrong in six and nobody reading English noticed.
 */

import { describe, expect, it } from "vitest";

import { JOURNEY_DOORS, journeyCta } from "./cta";
import { dictionaries, LOCALES, type Locale } from "./i18n";

/**
 * Words that offer an account, per language.
 *
 * Written out rather than machine-derived, because the point is to encode what
 * a *reader* would understand the button to be offering, and that is a fact
 * about the language rather than about our dictionary. These are the actual
 * strings that were found in the nav — "Crear cuenta", "Registrieren",
 * "Registrati", "S'inscrire", "Criar conta" — plus the noun each language uses
 * for the thing itself, so a rephrasing that still promises one is caught too.
 *
 * Nothing about signing *in* is here, and that is deliberate: `/sign-in`
 * exists, it is where a magic link lands, and "Anmelden" and "Se connecter"
 * are honest.
 */
const OFFERS_AN_ACCOUNT: Record<Locale, readonly RegExp[]> = {
  en: [/\bsign\s*up\b/i, /\bregister\b/i, /\baccount\b/i, /\bjoin\b/i],
  es: [/\bcrear?\s+(una\s+)?cuenta\b/i, /\bregistr/i, /\bcuenta\b/i],
  de: [/\bregistr/i, /\bkonto\b/i],
  it: [/\bregistr/i, /\baccount\b/i, /\bconto\b/i],
  fr: [/\bs['’]inscrire\b/i, /\binscription\b/i, /\bcompte\b/i],
  "pt-BR": [/\bcriar?\s+(uma\s+)?conta\b/i, /\bcadastr/i, /\bconta\b/i],
};

/**
 * The word each language uses for free-of-charge.
 *
 * The button's entire claim is that pressing it costs nothing, and that claim
 * is the first casualty when a sentence is shortened to fit a pill. A
 * translation that reads "Empezar" is grammatical, fits, and quietly withdraws
 * the only promise being made.
 */
const SAYS_FREE: Record<Locale, RegExp> = {
  en: /\bfree\b/i,
  es: /\bgratis\b/i,
  de: /\bkostenlos\b/i,
  it: /\bgratis\b/i,
  fr: /\bgratuit/i,
  "pt-BR": /\b(de\s+graça|grátis)\b/i,
};

describe("the door out of the landing page", () => {
  it("is opened from five places, each named once", () => {
    // Duplicated source names silently merge two rows of the funnel, and the
    // merge looks like one button doing twice the work of the others.
    expect(new Set(JOURNEY_DOORS).size).toBe(JOURNEY_DOORS.length);
  });

  // There is deliberately no test here that the five doors share a label.
  // `journeyCta` takes no door, so such a test would run the code and check it
  // equals itself — the coherence is structural, and the assertions below are
  // about the one thing a structure cannot guarantee: what the sentence says.
});

describe.each(LOCALES)("%s", (locale) => {
  const t = dictionaries[locale];
  const label = journeyCta(t);

  it("does not offer an account the website cannot create", () => {
    for (const forbidden of OFFERS_AN_ACCOUNT[locale]) {
      expect(label).not.toMatch(forbidden);
    }
  });

  it("still says the reading is free", () => {
    expect(label).toMatch(SAYS_FREE[locale]);
  });

  it("fits the narrowest button without a word hanging off it", () => {
    // Both halves of one measurement, and both of them re-taken.
    //
    // The tightest of the five doors is the sticky bar on a phone. Its button
    // is capped at 50% of the bar's 316 px inner at 360 — 158 px, of which 122
    // is usable once the pill has its padding. The six labels set at 136,
    // 113.8, 167.8, 127.6, 161.5 and 125.7 px in the pill's own font, so five
    // of the six are wider than one line of it.
    //
    // This test used to say the cap was "180 px on a 360 px screen" and that a
    // label past it "wraps inside a control with a fixed 50 px height" and
    // loses its second half. Neither is true any more and one never was: the
    // 50% is of the bar, not of the viewport, and the pill now grows to a
    // second line rather than clipping — `.cta-bar-btn` in `screens.css` has
    // why wrapping beat every alternative. So what has to hold changed shape.
    //
    // Two lines is the ceiling, at roughly 17 characters to a line; 24 is kept
    // as the working limit because it is where today's longest sits with room
    // to spare. And a box that wraps only helps if the words give it somewhere
    // to break: an unbreakable 15-character word is 115 px and squeezes into
    // 122, a 16-character one does not, and a German compound is exactly how
    // that arrives.
    expect(label.length).toBeLessThanOrEqual(24);
    for (const word of label.split(/\s+/)) {
      expect(word.length, `${locale}: "${word}" cannot break`).toBeLessThanOrEqual(15);
    }
  });

  it("leaves the bar's status line room to be read", () => {
    // The other half of the same 360 px bar, and the half that was losing.
    //
    // The button and the status column share one row: `.cta-bar-btn` is capped
    // at 50% and the copy takes what is left, which measured live is 144 px of
    // a 360 px screen. The status line was `nowrap` with an ellipsis, so at
    // that width German rendered as "…teme · war…" — every one of the six
    // overflowed, and the bar's entire informational job is to say that three
    // systems are ready and five are waiting.
    //
    // It wraps to two lines now. What has to stay true is that two lines are
    // *enough*: `-webkit-line-clamp: 2` means a third line is cut, so a string
    // long enough to need one goes back to being unreadable. At the bar's
    // 13.5 px face roughly 20 characters fit on a 144 px line, so 40 is the
    // ceiling. Today's longest is French at 33.
    //
    // Measured in characters rather than pixels for the reason the rule above
    // is: this file has no browser, and a character count that is calibrated
    // against a real measurement catches the regression that matters — a
    // translator writing a sentence where a label belongs.
    for (const status of [t.ctaBar.ready, t.ctaBar.waiting]) {
      expect(status.length, `${locale}: "${status}"`).toBeLessThanOrEqual(40);
    }
  });
});
