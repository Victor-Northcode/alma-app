import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  APPEAR_AFTER,
  FOOTER_CLEAR,
  FOOTER_NEAR,
  KEEP_UNTIL,
  barVisible,
} from "./cta-bar";

/**
 * The sticky bar arrives once and leaves once, however somebody scrolls.
 *
 * The defect this guards against is not a wrong number, it is a *single*
 * number. With one threshold and a 420 ms transition, a reader whose scroll
 * overshoots by two pixels — which is every trackpad, every momentum scroll and
 * every thumb — flips the state twice, and a bar that is 200 ms into arriving
 * when it is told to leave restarts backwards. The result is a bar that pumps,
 * at the exact moment a reader has stopped to look at something.
 *
 * So the rule is asymmetric on purpose, and asymmetry is the kind of thing that
 * gets "tidied" into symmetry by somebody who reads the code and not the
 * reason. The walks below are the argument in test form: crossing a boundary
 * one way must not be undone by drifting back a few pixels.
 */

describe("the sticky bar does not pump at its boundaries", () => {
  it("waits for 560 px before it appears at all", () => {
    expect(barVisible(false, 559, 9999)).toBe(false);
    expect(barVisible(false, 561, 9999)).toBe(true);
  });

  it("does not leave again until the page is 100 px back", () => {
    // The whole point. At 500 the answer depends on which way you came, and a
    // rule that answered the same either way is the flicker.
    expect(barVisible(false, 500, 9999)).toBe(false);
    expect(barVisible(true, 500, 9999)).toBe(true);
    expect(barVisible(true, 459, 9999)).toBe(false);
  });

  it("survives a scroll that overshoots the top edge and settles back", () => {
    // A momentum scroll to 570 that rubber-bands back to 545: one arrival, and
    // it stays arrived.
    let shown = false;
    const seen: boolean[] = [];
    for (const y of [400, 520, 570, 558, 545, 552, 549]) {
      shown = barVisible(shown, y, 9999);
      seen.push(shown);
    }
    expect(seen).toEqual([false, false, true, true, true, true, true]);
    // Once, not three times.
    expect(seen.filter((v, i) => v !== seen[i - 1]).length - 1).toBe(1);
  });

  it("leaves before the footer and does not come back on a jitter", () => {
    // Approaching the legal block, then a small bounce back off the bottom.
    let shown = true;
    const seen: boolean[] = [];
    for (const bottom of [600, 500, 430, 419, 440, 480, 519, 521]) {
      shown = barVisible(shown, 3000, bottom);
      seen.push(shown);
    }
    expect(seen).toEqual([true, true, true, false, false, false, false, true]);
  });

  it("never covers the footer, whichever direction the reader came from", () => {
    // The bar sits over the bottom of the page, and the bottom of the page is
    // the legal block. There is no scroll position at all where it is shown and
    // the document has less than FOOTER_NEAR left.
    for (const shown of [true, false]) {
      for (let bottom = 0; bottom <= FOOTER_NEAR; bottom += 20) {
        expect(barVisible(shown, 3000, bottom), `shown=${shown} bottom=${bottom}`).toBe(false);
      }
    }
  });

  it("keeps the two bands wide enough to be bands", () => {
    // 100 px each. Wider than any overshoot a scroll produces, narrower than a
    // deliberate scroll back. If either of these ever reaches zero the rule has
    // been flattened into the single threshold it replaced, and nothing else in
    // this file would fail.
    expect(APPEAR_AFTER - KEEP_UNTIL).toBeGreaterThanOrEqual(60);
    expect(FOOTER_CLEAR - FOOTER_NEAR).toBeGreaterThanOrEqual(60);
  });
});

describe("the bar arrives as one movement", () => {
  /**
   * Travel and fade share a duration and a curve, so the opacity is a function
   * of the position at every frame.
   *
   * They did not: the transform ran for `--d-bar` (420 ms) on ease-out-expo
   * while the opacity ran 300 ms on `ease`. Neither number is wrong alone,
   * which is why the bar was hard to fault and easy to feel — it finished
   * becoming opaque a fifth of a second before it finished moving, so the last
   * 120 ms were a solid bar still visibly sliding. Two events where the eye
   * expects one.
   *
   * Read out of the stylesheet, because there is no browser here and because
   * the thing worth holding is the *equality* rather than either value.
   */
  const css = readFileSync(join(process.cwd(), "src/app/screens.css"), "utf8").replace(
    /\/\*[\s\S]*?\*\//g,
    "",
  );
  const rule = css.match(/\.cta-bar\s*\{([^}]*)\}/)?.[1] ?? "";
  const transition = rule.match(/transition:\s*([^;]*);/)?.[1].replace(/\s+/g, " ").trim() ?? "";

  it("moves and fades over the same duration on the same curve", () => {
    const parts = transition.split(",").map((p) => p.trim());
    expect(parts, `\`transition\` on .cta-bar is: ${transition}`).toHaveLength(2);
    const [travel, fade] = parts;
    expect(travel.startsWith("transform ")).toBe(true);
    expect(fade.startsWith("opacity ")).toBe(true);
    // Same duration, same easing — compared as written, since both are tokens
    // rather than numbers here.
    expect(travel.replace("transform ", "")).toBe(fade.replace("opacity ", ""));
  });

  it("uses the shared bar duration rather than a number typed here", () => {
    expect(transition).toContain("var(--d-bar)");
  });
});
