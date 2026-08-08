import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { systems } from "./data";

/**
 * The eight-systems section, and the two things about it that are not style.
 *
 * The section's heading counts to eight, its rail dots count to eight and its
 * closing sentence says *every one of the eight is calculated free*. Under all
 * of that, `screens.css` carried one line inside its `min-width: 700px` block:
 *
 *     .eight-card[data-door="false"] { display: none; }
 *
 * Four of the eight are not doors — numerology, birth card, solar return and
 * cross-synthesis — so from 700 px up, exactly those four were removed. A
 * visitor on a tablet or a laptop was shown four cards and told, on the same
 * screen, that there were eight. Worse than a miscount: the four that survived
 * are the four with something to sell behind them, so a section whose entire
 * argument is *this is what we compute for nothing* had quietly become a list
 * of the paid ones.
 *
 * That is the kind of thing a stylesheet can do again in one line and nobody
 * notices for a month, so it is asserted here rather than remembered. The
 * second assertion is the arithmetic the replacement layout rests on: three
 * columns at tablet and four at desktop are not arbitrary, they are the two
 * factorings of eight that the six groups fall into, and the CSS centres the
 * last row on the promise that the last row holds two.
 *
 * Read out of the files rather than rendered, for the reason `legal-truth`
 * gives about the footer: there is no browser here, and the fact worth holding
 * is the one a browser would only reveal at one particular width.
 */

const SCREENS_CSS = readFileSync(join(process.cwd(), "src/app/screens.css"), "utf8");

/** Comments carry the history of this rule; only live declarations count. */
const declarations = SCREENS_CSS.replace(/\/\*[\s\S]*?\*\//g, "");

describe("the eight systems are eight at every width", () => {
  it("has eight of them", () => {
    expect(systems).toHaveLength(8);
  });

  it("hides none of them for not being a door", () => {
    // The exact defect: any selector that narrows `.eight-card` by `data-door`
    // is a selector that treats "we sell this" as a reason to draw it. Whether
    // it hides, dims or reorders, that distinction does not belong in the
    // section that promises the eight are calculated free.
    const byDoor = declarations.match(/\.eight-card\s*\[\s*data-door[^\]]*\]/g) ?? [];
    expect(byDoor, `screens.css narrows .eight-card by data-door: ${byDoor.join(", ")}`).toEqual([]);
  });

  it("hides none of them at all", () => {
    // Broader than the rule above and cheaper than trusting it: no rule whose
    // selector mentions `.eight-card` may declare `display: none`. The rail
    // itself may still be hidden; a card may not.
    const rules = declarations.match(/[^{}]*\.eight-card[^{}]*\{[^}]*\}/g) ?? [];
    const hiding = rules.filter((rule) => /display\s*:\s*none/.test(rule));
    expect(hiding, `a card is hidden by: ${hiding.join(" ")}`).toEqual([]);
  });
});

describe("the grid the eight are laid out on", () => {
  it("groups them contiguously, because the rows are the groups", () => {
    // Three columns at tablet makes the first row *who am I* entire — natal,
    // numerology, birth card — and that is only true while the array is
    // ordered by group. Interleave two groups and the rows stop meaning
    // anything, silently, with the layout still looking tidy.
    const seen = new Set<string>();
    let previous = "";
    for (const system of systems) {
      if (system.group !== previous) {
        expect(seen.has(system.group), `${system.group} is split across the list`).toBe(false);
        seen.add(system.group);
        previous = system.group;
      }
    }
  });

  it("leaves a last row of two at tablet, which is what the CSS centres", () => {
    // `.eight-card:nth-last-child(2)` and `:last-child` are pushed to columns
    // 2 and 4 of six so the final pair sits centred under the three above. If
    // the count ever stops leaving a remainder of two, those two rules move
    // cards that are not on the last row and the grid tears.
    expect(systems.length % 3).toBe(2);
  });

  it("divides evenly at desktop, which is why nothing is centred there", () => {
    // Four columns and eight cards is two whole rows, which is why the ≥1024
    // block resets `grid-column` to `auto` instead of repeating the centring.
    expect(systems.length % 4).toBe(0);
  });
});
