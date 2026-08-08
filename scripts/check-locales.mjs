/**
 * A locale audit that runs in CI.
 *
 * TypeScript already guarantees every locale has every *key* — the
 * dictionaries are typed against `typeof en`, so a missing one is a build
 * error. What the type system cannot see is a key that was copied across and
 * never translated, which is the failure that actually reaches customers: the
 * page looks finished, and one sentence in six is in the wrong language.
 *
 * So this checks for untranslated leftovers. A handful of strings are
 * legitimately identical across languages — "Alma", "8", numerals, and words
 * like "Direction" that really are spelled the same — so those are listed
 * rather than guessed at.
 *
 *     node scripts/check-locales.mjs
 */

import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const DIR = "src/lib/i18n";
const SOURCE = "en.ts";

/** Strings that are correctly identical in more than one language. */
const SHARED = new Set([
  "Alma",
  "8",
  "4,8",
  "4.8",
  "$0",
  "0 €",
  "R$ 0",
  "Direction",
  "Questions",
  "Transits",
  "Privacy",
  "Libra",
  "Leo",
  "Cancer",
  "Virgo",
  "Sections",
  "Date",
  "Plan",
  // Genuine cognates, confirmed one at a time rather than waved through:
  "Aries", // Spanish spells it exactly as English does
  "Ascendant", // French, identically
  "Notifications", // French, identically
  "Legal", // Spanish and Brazilian Portuguese both spell it this way
  "Contact", // French, identically
  "questions", // French, identically — the FAQ section label
  "9 axes", // French, identically — "axe" takes the same plural
]);

function stringsIn(file) {
  const text = readFileSync(join(DIR, file), "utf8");
  const found = new Map();
  // Match `key: "value"` — good enough for a dictionary of literals, and it
  // deliberately ignores the template strings inside the helper functions.
  const pattern = /^\s*"?([A-Za-z][\w-]*)"?:\s*"((?:[^"\\]|\\.)*)"/gm;
  let match;
  while ((match = pattern.exec(text)) !== null) {
    const [, key, value] = match;
    if (!found.has(key)) found.set(key, []);
    found.get(key).push(value);
  }
  return found;
}

const source = stringsIn(SOURCE);
const locales = readdirSync(DIR).filter(
  (name) => name.endsWith(".ts") && name !== SOURCE && name !== "index.ts",
);

let problems = 0;

for (const file of locales) {
  const theirs = stringsIn(file);
  const untranslated = [];

  for (const [key, values] of source) {
    const mine = theirs.get(key);
    if (!mine) continue;
    for (const value of values) {
      if (!value.trim() || SHARED.has(value)) continue;
      // Ignore anything that is mostly punctuation, digits or a price.
      if (!/[A-Za-z]{4}/.test(value)) continue;
      if (mine.includes(value)) untranslated.push(`${key}: "${value}"`);
    }
  }

  if (untranslated.length) {
    problems += untranslated.length;
    console.error(`\n${file} — ${untranslated.length} string(s) still in English:`);
    for (const line of untranslated.slice(0, 12)) console.error(`  ${line}`);
    if (untranslated.length > 12) console.error(`  … and ${untranslated.length - 12} more`);
  }
}

if (problems) {
  console.error(
    `\n${problems} untranslated string(s). Either translate them or add them to ` +
      "SHARED in this script if they are genuinely the same word.",
  );
  process.exit(1);
}

console.log(`locales: ${locales.length} translated, no English left behind`);
