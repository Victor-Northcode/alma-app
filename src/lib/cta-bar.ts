/**
 * When the sticky call-to-action bar is on screen.
 *
 * Pulled out of `LandingShell` so that the rule has somewhere to be written
 * down and somewhere to be tested. It was four numbers inside a scroll
 * listener, which is the one place they can never be checked: a scroll handler
 * is only true at the moment a person scrolls, and the moment that matters is
 * a trackpad drifting two pixels across a boundary.
 *
 * ── why each edge is a band and not a line ────────────────────────────────
 *
 * A single threshold plus a 420 ms transition is a flicker waiting to happen.
 * Both boundaries sit in the middle of a page a reader scrolls in both
 * directions, and momentum overshoots: one pixel either side of 560 flips the
 * state, and a bar 200 ms into arriving that is told to leave restarts
 * backwards. Two fingers of drift and it pumps.
 *
 * So each edge has an on-value and a different off-value, and the state changes
 * only when the page has actually travelled past one of them. Appear at 560,
 * do not disappear again until 460. Hide when the footer is within 420, do not
 * come back until it is 520 away. The 100 px of hysteresis is larger than any
 * overshoot a scroll produces and smaller than a deliberate scroll back, so
 * nothing a person means to do is ignored and nothing their hardware does by
 * accident is obeyed.
 *
 * The footer edge exists so the bar never covers the legal block — the one part
 * of the page a reader may need to read carefully and the one part a regulator
 * looks at.
 */

/** Below this the bar is not shown at all. */
export const APPEAR_AFTER = 560;
/** Once shown, it stays until the page is back above this. */
export const KEEP_UNTIL = 460;
/** Hide when the end of the document is this close. */
export const FOOTER_NEAR = 420;
/** Once hidden by the footer, do not return until it is this far away. */
export const FOOTER_CLEAR = 520;

/**
 * @param shown  whether the bar is on screen right now — the hysteresis needs
 *               to know which way it is being asked.
 * @param y      `window.scrollY`.
 * @param bottom how much document is left below the viewport.
 */
export function barVisible(shown: boolean, y: number, bottom: number): boolean {
  if (shown) return y > KEEP_UNTIL && bottom > FOOTER_NEAR;
  return y > APPEAR_AFTER && bottom > FOOTER_CLEAR;
}
