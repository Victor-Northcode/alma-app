import type { SystemSummary } from "./types";

/**
 * What the landing knows without asking the backend.
 *
 * This file used to be the whole product's understudy: sixteen natal chapters
 * of finished prose, a day's transits, nine synthesis axes, a chat thread, and
 * a set of chapter lists per system — about five hundred lines of invented
 * reading, written for one imaginary person (Pisces, life path 7, The Star,
 * Milan) and served by the hooks whenever the API was unreachable. Every screen
 * that displayed it belonged to the cabinet, and the cabinet is gone; a fixture
 * with no screen behind it is prose nobody proofreads and everybody eventually
 * believes, so it went with them.
 *
 * What is left is what the landing genuinely computes or genuinely lists: the
 * eight system cards, the legal wall, the compliance badges, and the small
 * piece of arithmetic that answers in the two seconds before a birth has been
 * saved anywhere.
 *
 * **No price appears in here.** These carried one per system and one per
 * chapter — $14.99, $6.99, $19.99, $4.99 — against a catalogue that sells a
 * $5.99 door and no chapter at all. A price in a fixture is a price shown to
 * somebody and then not charged; every figure the interface renders comes from
 * `/v1/billing/catalogue`, and `prices.test.ts` walks this whole module to keep
 * it that way.
 */
export const systems: SystemSummary[] = [
  { slug: "natal", group: "who-am-i", motif: "wheel", door: true },
  { slug: "numerology", group: "who-am-i", motif: "number" },
  { slug: "birth-card", group: "who-am-i", motif: "arcana" },
  { slug: "transits", group: "right-now", motif: "orbits", door: true },
  { slug: "solar-return", group: "this-year", motif: "solar" },
  { slug: "compatibility", group: "how-we-match", motif: "two-circles", door: true },
  { slug: "astrocartography", group: "where-to-be", motif: "globe", door: true },
  { slug: "synthesis", group: "all-of-it", motif: "axes" },
];

/**
 * How much writing there is, and how much of it is free.
 *
 * The handoff is where the website says what continues in the app, and the
 * sentence it says it in is a number: *this many chapters, this many of them
 * free*. A number in copy is a claim, and this one is a claim about a Python
 * file six directories away — `backend/alma/ai/chapters.py`, which defines
 * every chapter of every system and marks exactly one per system `free=True`.
 * Written here rather than fetched because there is no endpoint that answers
 * "how many chapters exist" and inventing one to render a sentence is a round
 * trip for a constant; `data.test.ts` reads that file and fails if either
 * figure drifts, which is the same trade `birthCard` above already makes.
 *
 * Not a price and not a promise about what a person owns — see the pricing
 * section for what a system costs, which only the catalogue may say.
 */
export const CHAPTERS = 41;
export const FREE_CHAPTERS = 8;

/**
 * The footer's legal wall — every entry with somewhere to go.
 *
 * This list used to be eighteen strings on `href="#"`, including a Korean
 * privacy policy and a Japanese commercial-transactions notice. A link is a
 * claim that the document behind it exists; eighteen dead ones claimed twelve
 * documents that were never written, which is the same species of untruth as
 * an invented birth time. So the list is now what there is: five documents,
 * plus the addresses that reach a person.
 *
 * Cookies, withdrawal rights and the sale-of-data line are not separate pages
 * because they are not separate subjects — they are sections of the privacy
 * and refund policies, and they link straight to those sections.
 */
export const legalLinks: ReadonlyArray<{ label: string; href: string }> = [
  { label: "Terms of Service", href: "/terms" },
  { label: "Privacy Policy", href: "/privacy" },
  { label: "Cookie Policy", href: "/privacy#cookies" },
  { label: "Refund Policy", href: "/refunds" },
  { label: "Subscription Terms", href: "/subscription-terms" },
  { label: "Withdrawal Rights (EU/UK)", href: "/refunds#withdrawal" },
  { label: "Your Privacy Choices", href: "/privacy#choices" },
  { label: "Do Not Sell or Share My Personal Information", href: "/privacy#choices" },
  { label: "Imprint / Impressum", href: "/imprint" },
  /**
   * The two the wall was missing, and both are store requirements rather than
   * tidiness. Google asks that the account-deletion resource be *readily
   * discoverable*, which a URL pasted into Play Console and linked from nowhere
   * on the site is not; Apple asks for a support URL that reaches real contact
   * information, and the bottom of the page is where a person looks for one.
   * Support comes before Contact because the page tells you what to put in the
   * letter, and a letter with the order number in it is answered once.
   */
  { label: "Support", href: "/support" },
  { label: "Delete Your Account", href: "/delete-account" },
  { label: "Contact", href: "mailto:hello@pazl.ai" },
];

/**
 * The badges under the footer links — and they are claims, not decoration.
 *
 * PIPA (KR) and APPI (JP) were here and are gone, for the same reason the
 * eighteen dead legal links above were cut: both regimes require a notice in
 * the local language naming a local representative, neither notice exists, the
 * product is not sold in won or yen, and the Korean privacy policy that used to
 * be linked was deleted precisely because it had never been written. A badge
 * claiming a regime we have not read is worse than no badge — it is the one
 * line on the page a regulator would check first.
 *
 * What is left is what the privacy policy actually answers: an age rule stated
 * in the terms, the European and UK regimes the export and deletion routes are
 * built for, and the Californian one whose sale-of-data question the policy
 * answers outright.
 */
export const complianceBadges = ["16+", "GDPR · UK GDPR", "CCPA / CPRA"];

/** Sun sign from a date — enough for the in-page first insight. */
export function sunSign(day: number, monthIndex: number): { name: string; glyph: string } {
  const cutoffs = [20, 19, 21, 20, 21, 21, 23, 23, 23, 23, 22, 22];
  const names = [
    "Capricorn",
    "Aquarius",
    "Pisces",
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
  ];
  const glyphs = ["♑︎", "♒︎", "♓︎", "♈︎", "♉︎", "♊︎", "♋︎", "♌︎", "♍︎", "♎︎", "♏︎", "♐︎"];
  const i = day < cutoffs[monthIndex] ? monthIndex : (monthIndex + 1) % 12;
  return { name: names[i], glyph: glyphs[i] };
}

/** Pythagorean life path — the digits of the date reduced, masters kept. */
export function lifePath(day: number, month: number, year: number): number {
  const reduce = (n: number): number => {
    while (n > 9 && n !== 11 && n !== 22 && n !== 33) {
      n = String(n)
        .split("")
        .reduce((a, d) => a + Number(d), 0);
    }
    return n;
  };
  return reduce(reduce(day) + reduce(month) + reduce(year));
}

const ARCANA = [
  "The Fool",
  "The Magician",
  "The High Priestess",
  "The Empress",
  "The Emperor",
  "The Hierophant",
  "The Lovers",
  "The Chariot",
  "Strength",
  "The Hermit",
  "Wheel of Fortune",
  "Justice",
  "The Hanged Man",
  "Death",
  "Temperance",
  "The Devil",
  "The Tower",
  "The Star",
  "The Moon",
  "The Sun",
  "Judgement",
  "The World",
];

const ROMAN = [
  "0",
  "I",
  "II",
  "III",
  "IV",
  "V",
  "VI",
  "VII",
  "VIII",
  "IX",
  "X",
  "XI",
  "XII",
  "XIII",
  "XIV",
  "XV",
  "XVI",
  "XVII",
  "XVIII",
  "XIX",
  "XX",
  "XXI",
];

const digitSum = (n: number): number =>
  String(Math.abs(n))
    .split("")
    .reduce((a, d) => a + Number(d), 0);

/**
 * The Personality card — and it must agree with the engine.
 *
 * This used to reduce each part of the date all the way to a single digit
 * before adding, which is a different method: for 7 July 1991 it produced
 * The Tower where `alma/engine/arcana.py` produces The Chariot. The landing
 * showed one card and the portrait, thirty seconds later, showed another —
 * on the same birthday, to the same person.
 *
 * The engine's method is the standard one: sum every digit of the date once,
 * then fold back into 0–21. Folding to a single digit first would collapse
 * every date onto the first ten arcana and throw away two thirds of the deck.
 * Mirrored here — with a test — because this copy exists only to answer in
 * the two seconds before the backend can.
 */
export function birthCard(day: number, month: number, year: number): { name: string; numeral: string } {
  let sum = digitSum(day) + digitSum(month) + digitSum(year);
  while (sum > 21) sum = digitSum(sum);
  return { name: ARCANA[sum], numeral: ROMAN[sum] };
}

/**
 * What the landing's instant insight shows — or `null` when there is nothing
 * to show yet.
 *
 * It used to return the demo profile for a missing date, which meant every
 * first-time visitor was shown Pisces, life path 7 and The Star as though the
 * page already knew them. It was somebody else's chart wearing the words
 * "your sky". The caller now gets `null` and says so honestly.
 *
 * The 14 March 1998 special case is gone with it: that date computes to the
 * same three values anyway, and a hard-coded shortcut around real arithmetic
 * is exactly the kind of thing that stops being true when the arithmetic
 * changes.
 */
export function insightFor(date: { day: number; month: number; year: number } | null) {
  if (!date) return null;
  return {
    sign: sunSign(date.day, date.month - 1),
    path: lifePath(date.day, date.month, date.year),
    card: birthCard(date.day, date.month, date.year),
  };
}
