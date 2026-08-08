import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * A class that decides *whether* something is shown must not also decide *how*.
 *
 * `.from-tablet`, `.only-mobile` and `.to-tablet` are visibility utilities:
 * they flip between `display: none` and `display: initial`. And `initial` for
 * `display` is **`inline`** — not "whatever the element was going to be". So
 * putting one of them on an element that needs a layout display silently
 * replaces that display, at exactly the widths where the element is visible.
 *
 * The cross-synthesis panel is what this cost. Its third row was
 * `className="row from-tablet"`, and `.row` is `display: flex`. Both selectors
 * compute to (0,1,0); the utility is restated last in `screens.css` so it wins;
 * from 700 px up the row stopped being a row. Measured at 700, 768, 900, 1024
 * and 1440: the axis label and its four lozenges stacked instead of sitting on
 * one line, the lozenge group stretched to the full 298 px column, and the
 * lozenges landed on top of the row's own hairline — while the identical row
 * two above it, which carries no utility, was correct. The one panel whose job
 * is to look like a real reading was visibly broken at every width it appears
 * at, in every language.
 *
 * `.from-tablet-block` and `.from-tablet-flex` exist precisely so that a
 * visibility utility can restore the right display, and `.price-row
 * from-tablet-flex` one section further down was already using the flex one
 * correctly. The file was inconsistent with itself, which is the strongest
 * argument there is for a test: the correct spelling and the broken spelling
 * look equally deliberate to a reader.
 *
 * So this reads both stylesheets, works out which classes set which `display`,
 * and refuses any `className` that combines a visibility utility with a class
 * that needs to lay its children out. It is deliberately derived from the CSS
 * rather than from a hardcoded list of utility names — a seventh utility added
 * next year is covered without anybody remembering this file exists.
 */

const STYLESHEETS = ["src/app/globals.css", "src/app/screens.css"] as const;

/** Every class name, mapped to every `display` value any rule gives it. */
function displaysByClass(): Map<string, Set<string>> {
  const found = new Map<string, Set<string>>();
  for (const file of STYLESHEETS) {
    const css = readFileSync(join(process.cwd(), file), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
    for (const rule of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const [, selector, body] = rule;
      for (const declaration of body.matchAll(/(?<![\w-])display\s*:\s*([a-z-]+)/g)) {
        for (const name of selector.matchAll(/\.([A-Za-z][\w-]*)/g)) {
          const values = found.get(name[1]) ?? new Set<string>();
          values.add(declaration[1]);
          found.set(name[1], values);
        }
      }
    }
  }
  return found;
}

const DISPLAYS = displaysByClass();

/**
 * Classes that make an element `inline` at some width. `initial` is the one
 * that catches people out — it looks like "leave it alone" and means `inline`.
 */
const INLINING = new Set(
  [...DISPLAYS].filter(([, values]) => values.has("initial") || values.has("inline")).map(([n]) => n),
);

/** Classes that lay their children out, and so cannot survive being inlined. */
const LAYOUT = new Set(
  [...DISPLAYS]
    .filter(([name, values]) => {
      if (INLINING.has(name)) return false;
      return ["flex", "grid", "block", "inline-flex", "inline-grid"].some((v) => values.has(v));
    })
    .map(([name]) => name),
);

function tsxFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) return tsxFiles(path);
    return path.endsWith(".tsx") ? [path] : [];
  });
}

/**
 * Every set of classes that could land on one element together.
 *
 * Not just `className="a b"`. A `className={cond ? "row from-tablet" : "row"}`
 * puts two classes on one element just as surely, and reading only the static
 * attribute form is how a check like this quietly stops covering the code it
 * was written for — the first draft of this test passed against the original
 * defect for exactly that reason, because the refactor that fixed it had moved
 * the classes into a ternary.
 *
 * So each string literal *inside* a `className={…}` expression is treated as
 * its own candidate set: they are alternatives, and each alternative is a set
 * of classes that really does end up on the element when that branch is taken.
 * Interpolations (`` `row ${extra}` ``) are the case this cannot see, which is
 * why `AxisRow` is written to spell both of its class strings out.
 */
function classSets(source: string): string[] {
  const sets: string[] = [];
  for (const attribute of source.matchAll(/className=(?:"([^"]*)"|\{([\s\S]*?)\}(?=\s|\/?>))/g)) {
    if (attribute[1] !== undefined) {
      sets.push(attribute[1]);
      continue;
    }
    for (const literal of attribute[2].matchAll(/["'`]([^"'`]*)["'`]/g)) sets.push(literal[1]);
  }
  return sets;
}

describe("a visibility utility never eats a layout display", () => {
  it("knows which utilities inline their element", () => {
    // If this ever finds nothing, the scan below is passing vacuously and the
    // whole file is decoration. The three page-wide ones must be in it.
    for (const utility of ["from-tablet", "only-mobile", "to-tablet"]) {
      expect(INLINING.has(utility), `${utility} no longer sets an inline display`).toBe(true);
    }
  });

  it("knows which classes lay out their children", () => {
    expect(LAYOUT.has("row"), ".row no longer declares a layout display").toBe(true);
  });

  it("finds no element carrying both", () => {
    const collisions: string[] = [];
    for (const file of tsxFiles(join(process.cwd(), "src"))) {
      const source = readFileSync(file, "utf8");
      for (const set of classSets(source)) {
        const classes = set.trim().split(/\s+/);
        const inlined = classes.filter((name) => INLINING.has(name));
        const laidOut = classes.filter((name) => LAYOUT.has(name));
        if (inlined.length > 0 && laidOut.length > 0) {
          collisions.push(
            `${file.replace(process.cwd() + "/", "")}: "${set}" — ` +
              `${inlined.join(", ")} inlines ${laidOut.join(", ")}`,
          );
        }
      }
    }
    expect(
      collisions,
      `use the -flex or -block variant instead:\n${collisions.join("\n")}`,
    ).toEqual([]);
  });

  it("offers a variant that restores each layout display", () => {
    // The fix has to be available, or the rule above is an instruction to
    // delete the utility. Both variants exist and both are used.
    expect(DISPLAYS.get("from-tablet-flex")?.has("flex")).toBe(true);
    expect(DISPLAYS.get("from-tablet-block")?.has("block")).toBe(true);
  });
});
