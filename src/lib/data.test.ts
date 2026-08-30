import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { CHAPTERS, FREE_CHAPTERS, birthCard, insightFor, lifePath } from "./data";

/**
 * The landing computes a birth card and a life path locally so it can answer
 * in the two seconds before the backend has a profile to read. That makes it
 * a second implementation of arithmetic the engine already owns — and a
 * second implementation is only useful while it agrees.
 *
 * It did not. `birthCard` reduced each part of the date to a single digit
 * before adding, so 7 July 1991 came out as The Tower on the landing and The
 * Chariot in the portrait thirty seconds later. The rows below are the
 * engine's own output, produced by `alma/engine/arcana.py` and
 * `alma/engine/numerology.py`, and pasted here rather than recomputed by the
 * same code they are meant to check.
 */
const ENGINE: Array<[number, number, number, string, string, number]> = [
  [14, 3, 1998, "VIII", "Strength", 8],
  [7, 7, 1991, "VII", "The Chariot", 7],
  [1, 1, 2000, "IV", "The Emperor", 4],
  [29, 12, 1984, "IX", "The Hermit", 9],
  [31, 10, 1967, "X", "Wheel of Fortune", 1],
  [29, 11, 1975, "VIII", "Strength", 8],
  [5, 5, 2005, "XVII", "The Star", 8],
  [22, 9, 1959, "X", "Wheel of Fortune", 1],
];

describe("the landing's local arithmetic", () => {
  it.each(ENGINE)(
    "%i/%i/%i is %s %s, life path %i — same as the engine",
    (day, month, year, numeral, name, path) => {
      expect(birthCard(day, month, year)).toEqual({ numeral, name });
      expect(lifePath(day, month, year)).toBe(path);
    },
  );

  it("keeps master numbers, which is why 29-11-1975 is not 8 by the other method", () => {
    // reduce(29)=11, reduce(11)=11, reduce(1975)=4 → 26 → 8.
    expect(lifePath(29, 11, 1975)).toBe(8);
  });
});

/**
 * The handoff tells a person how much writing is waiting in the app, in
 * figures. Both come from `backend/alma/ai/chapters.py`, and both are the kind
 * of number that stays in the copy long after the thing it counted changed — a
 * chapter added to the natal set, or a second free one opened in a system,
 * would leave the last screen of the website quietly advertising the wrong
 * product in six languages.
 *
 * The source is read rather than imported: it is Python, and the counting is
 * deliberately as dumb as possible — every `_c(` is one chapter and every
 * `free=True` is one free chapter — so that this fails on a real change rather
 * than on a refactor of how the file is laid out.
 */
describe("what the handoff claims is in the app", () => {
  const source = readFileSync(
    join(__dirname, "..", "..", "backend", "alma", "ai", "chapters.py"),
    "utf8",
  );
  // Только строки кода: история решения «свободна одна глава» (17.08.2026)
  // живёт в комментариях chapters.py и поминает `free=True` четырежды —
  // счёт по сырому файлу выдал 5 «бесплатных глав» при одной настоящей.
  const code = source
    .split("\n")
    .filter((line) => !line.trimStart().startsWith("#"))
    .join("\n");
  // The definition of the helper is itself a `_c(` occurrence, and it is not a
  // chapter.
  const declared = code.split("_c(").length - 1 - 1;
  const free = code.split("free=True").length - 1;

  it("counts every chapter the writing layer defines", () => {
    expect(CHAPTERS).toBe(declared);
  });

  it("counts the free ones — exactly one in the product, which is the sentence", () => {
    // Восемь стало одной 17.08.2026 (решение владельца: свободен натал I
    // «Core», всё остальное закрыто) — а хэндофф ещё две недели обещал
    // «one in every system» на шести языках. Этот тест и был написан,
    // чтобы то предложение не пережило то решение.
    expect(FREE_CHAPTERS).toBe(free);
    expect(FREE_CHAPTERS).toBe(1);
  });
});

describe("insightFor", () => {
  it("returns nothing when there is no date, rather than somebody else's chart", () => {
    expect(insightFor(null)).toBeNull();
  });

  it("computes from the date it is given", () => {
    const insight = insightFor({ day: 7, month: 7, year: 1991 });
    expect(insight).not.toBeNull();
    expect(insight!.sign.name).toBe("Cancer");
    expect(insight!.path).toBe(7);
    expect(insight!.card.name).toBe("The Chariot");
  });

  it("no longer short-circuits the reference birthday to a hard-coded answer", () => {
    // 14 March 1998 used to bypass the arithmetic entirely and return The
    // Star. The engine says Strength; the shortcut was the only thing that
    // disagreed.
    expect(insightFor({ day: 14, month: 3, year: 1998 })!.card.name).toBe("Strength");
  });
});
