import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Every control that can be focused shows where the focus is.
 *
 * The rule the stylesheets are held to here is not "there is a `:focus-visible`
 * block somewhere". It is stricter and it is the thing that actually broke:
 *
 *   **the focus indicator lives on a property that nothing decorative uses.**
 *
 * The indicator used to be a `box-shadow`, declared once at zero selector
 * weight so that a component could override it — `:where(a, button, …)` plus
 * `:focus-visible` computes to (0,1,0). `.btn-gold` is also (0,1,0), declares
 * its own `box-shadow` for the ambient drop shadow, and sits 350 lines later in
 * the same file. Later rule, same weight, same property: the shadow replaced
 * the ring, and `outline: none` in the indicator block meant there was nothing
 * underneath. The result was that **every gold call to action on the site had
 * no focus indicator at all** — the hero's two variants, the nav sheet, the
 * pricing CTA, the final CTA and the sticky bar. That is the entire conversion
 * path, invisible to anybody navigating by keyboard. WCAG 2.4.7. The three
 * text fields lost theirs the same way, to a bare `outline: none` in
 * `.text-input`.
 *
 * Nobody did anything wrong to cause it. A component added a shadow, which
 * components are supposed to be able to do. So the fix was not to win that one
 * specificity race — a fix that has to be re-won every time somebody adds a
 * shadow is a fix with an expiry date — but to move the indicator onto
 * `outline`, which cannot be used decoratively: it takes no part in layout, it
 * cannot be given a per-side value, and no design in this repository wants one.
 *
 * These tests hold that property boundary rather than the colours or the
 * widths, which are design and may change.
 */

const STYLESHEETS = ["src/app/globals.css", "src/app/screens.css"] as const;

interface Rule {
  file: string;
  selector: string;
  body: string;
}

/** Live declarations only — the comments here carry a lot of history. */
function rulesIn(file: string): Rule[] {
  const css = readFileSync(join(process.cwd(), file), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  const found: Rule[] = [];
  for (const match of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    found.push({ file, selector: match[1].trim().replace(/\s+/g, " "), body: match[2] });
  }
  return found;
}

const RULES = STYLESHEETS.flatMap(rulesIn);

const declares = (body: string, property: string) =>
  new RegExp(`(?<![\\w-])${property}\\s*:`).test(body);

describe("the focus ring cannot be overwritten by a decoration", () => {
  it("declares the indicator on outline, not on box-shadow", () => {
    const indicator = RULES.filter(
      (rule) => rule.selector.includes(":focus-visible") && rule.selector.includes(":where("),
    );
    expect(indicator, "no global :focus-visible rule found").toHaveLength(1);
    expect(declares(indicator[0].body, "outline")).toBe(true);
    // The specific regression: a ring drawn as a shadow is a ring any component
    // can delete by wanting a shadow of its own.
    expect(
      declares(indicator[0].body, "box-shadow"),
      "the global focus ring is drawn with box-shadow again — `.btn-gold` will win",
    ).toBe(false);
  });

  it("lets no rule outside a focus state touch outline", () => {
    // This is the invariant that makes the property safe. `outline` is the
    // indicator's own channel; the moment something else writes to it, the
    // collision that took out six buttons is available again — and `outline:
    // none` with nothing after it is exactly how the text inputs lost theirs.
    const trespassers = RULES.filter(
      (rule) => declares(rule.body, "outline") && !rule.selector.includes(":focus"),
    ).map((rule) => `${rule.file}: ${rule.selector}`);
    expect(trespassers, `outline is set outside a focus state by: ${trespassers.join(", ")}`).toEqual(
      [],
    );
  });

  it("covers text inputs as well as buttons and links", () => {
    // `.text-input` is the journey's name field, its email field and the
    // sign-in field. They are `<input>`s, they were not in the old selector
    // list at all, and `.text-input { outline: none }` removed what they would
    // otherwise have inherited from the browser — so all three had no focus
    // indicator from any source.
    const indicator = RULES.find(
      (rule) => rule.selector.includes(":focus-visible") && rule.selector.includes(":where("),
    );
    for (const element of ["a", "button", "input", "select", "textarea"]) {
      expect(
        new RegExp(`(?<![\\w-])${element}(?![\\w-])`).test(indicator?.selector ?? ""),
        `<${element}> is not covered by the global focus ring`,
      ).toBe(true);
    }
  });

  it("keeps the ring clear of the control it is pointing at", () => {
    // A filled gold button with a gold ring drawn on its own edge is a slightly
    // thicker gold button. The offset is what makes the indicator read against
    // the night behind it rather than against the fill.
    const indicator = RULES.find(
      (rule) => rule.selector.includes(":focus-visible") && rule.selector.includes(":where("),
    );
    expect(declares(indicator?.body ?? "", "outline-offset")).toBe(true);
  });

  it("does not reshape the control it lands on", () => {
    // The shadow version carried `border-radius: 999px`, which applied to the
    // *element* for as long as it had focus: square controls visibly became
    // pills when tabbed to. An outline follows the corners the control already
    // has, so there is nothing to declare and declaring it would be the old bug.
    const indicator = RULES.find(
      (rule) => rule.selector.includes(":focus-visible") && rule.selector.includes(":where("),
    );
    expect(declares(indicator?.body ?? "", "border-radius")).toBe(false);
  });
});
