import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * The landing's roman numerals count, at both widths, without repeating or
 * skipping.
 *
 * They are the only spine the page has — nine sections of night with no chrome
 * between them — and a reader following them is being told how far through the
 * argument they are. Two numbers have to be right at once, because two of the
 * sections only exist on a phone and one only exists above 700 px, so `Label`
 * carries a mobile numeral and a desktop numeral and the two sequences are
 * different lengths.
 *
 * Both have been wrong, separately, and neither was noticed by anybody reading
 * the file:
 *
 * * On a phone the sequence ran **I, II, IV, IV, V, VII, VII, VIII** — two
 *   numerals used twice and two never used at all — because a hardcoded `IV`
 *   sat under a comment that said III.
 * * On a desktop it ran **I, —, III, IV, V, VI, VII**. The insight section is
 *   deliberately not numbered there and shows a dash, and every section after
 *   it went on counting as though the dash had used up a number, so **II
 *   appeared at no width at all**. Measured live at 1024 and 1440 by reading
 *   the visible child of each `.numeral`; the phone was clean by then, so the
 *   fix for the first defect had left the second one standing.
 *
 * Reading the source rather than rendering, for the reason `eight-layout` and
 * `legal-truth` both give: there is no browser here, the fact worth holding is
 * one a browser would only show at one particular width, and the numerals are
 * literals in one file with one shape.
 *
 * The dash is allowed and is checked for separately. What is not allowed is a
 * gap in the numbers that remain.
 */

const SECTIONS = readFileSync(
  join(process.cwd(), "src/components/landing/sections.tsx"),
  "utf8",
);

const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];

/** The numeral that is not a number: the insight section, on wide screens. */
const UNNUMBERED = "—";

interface Head {
  /** The `className` of the nearest `<section>` above this label. */
  section: string;
  mobile: string;
  desktop: string;
}

/**
 * Every `<Label>` in the file, in source order, tagged with the section it is
 * in — because whether a numeral is *shown* depends on whether its section is
 * one of the breakpoint-only variants.
 */
function heads(): Head[] {
  const found: Head[] = [];
  let section = "";
  const token = /<section[^>]*className="([^"]+)"|<Label m="([^"]+)" d="([^"]+)"/g;
  for (const match of SECTIONS.matchAll(token)) {
    if (match[1] !== undefined) {
      section = match[1];
      continue;
    }
    found.push({ section, mobile: match[2], desktop: match[3] });
  }
  return found;
}

const HEADS = heads();

/** What a reader actually sees, at one of the two widths. */
function visible(width: "mobile" | "desktop"): string[] {
  return HEADS.filter((head) =>
    width === "mobile"
      ? !head.section.includes("from-tablet-block")
      : !head.section.includes("only-mobile-block"),
  ).map((head) => (width === "mobile" ? head.mobile : head.desktop));
}

describe("the section numerals are a spine", () => {
  it("finds the labels at all", () => {
    // Guards every assertion below: a rename of `Label` would otherwise make
    // this whole file pass by testing an empty list.
    expect(HEADS.length).toBeGreaterThanOrEqual(8);
    expect(HEADS.every((head) => head.section !== "")).toBe(true);
  });

  for (const width of ["mobile", "desktop"] as const) {
    it(`counts from I with no gap and no repeat on ${width}`, () => {
      const numbered = visible(width).filter((numeral) => numeral !== UNNUMBERED);
      expect(numbered, `the ${width} spine reads ${visible(width).join(", ")}`).toEqual(
        ROMAN.slice(0, numbered.length),
      );
    });
  }

  it("shows the dash on one section, and only above 700", () => {
    // The insight section is outside the count on a wide screen because it is
    // the product doing the thing rather than a step in the argument. On a
    // phone the page is one column read strictly in order, an unnumbered
    // section between II and III reads as a numeral that failed to render, and
    // the spine is the only progress indicator there is — so it takes a number
    // there. One section, one width: more than one dash is not a decision, it
    // is a habit.
    expect(visible("desktop").filter((numeral) => numeral === UNNUMBERED)).toHaveLength(1);
    expect(visible("mobile").filter((numeral) => numeral === UNNUMBERED)).toHaveLength(0);
  });

  it("gives the phone two more sections than the desktop", () => {
    // Not a rule so much as the reason the two sequences differ at all: "how to
    // read yourself" and the voice-on-the-night are phone-only, and the
    // parchment band replaces the second of them above 700. If this ever
    // becomes equal, `Label` is carrying two identical values everywhere and
    // one of the two arguments has quietly gone away.
    expect(visible("mobile").length - visible("desktop").length).toBe(1);
  });

  it("keeps every numeral a roman numeral or the dash", () => {
    const strange = HEADS.flatMap(({ mobile, desktop }) => [mobile, desktop]).filter(
      (numeral) => numeral !== UNNUMBERED && !ROMAN.includes(numeral),
    );
    expect(strange, `not a numeral: ${strange.join(", ")}`).toEqual([]);
  });
});
