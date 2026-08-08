/**
 * The one door out of the landing page, and the five places it stands in.
 *
 * Every gold button on this website does the same thing: it opens the free
 * journey overlay. It used to be five buttons with five different promises —
 * "Sign up", "Build my full sky — free →", "Start — the chart is free",
 * "Read myself — free", "Continue free" — and the first of them was a lie
 * outright, because nothing on the web creates an account. The other four were
 * merely four descriptions of one overlay, which is how a visitor comes to
 * believe there is a free thing, a chart thing and a paid thing.
 *
 * The label now lives once, in the dictionary, under `cta.read`. What is still
 * allowed to differ is where the tap came from — and that difference belongs
 * here rather than in the copy, because it is for the funnel and not for the
 * reader.
 */

import type { Dictionary } from "./i18n";

/**
 * The five controls that open the journey, named for the funnel.
 *
 * A closed union rather than a free string, for the reason `track.ts` gives
 * about `Stage`: `start("pricng")` silently invents a sixth source with a
 * plausible name and a count of one, and the report then shows the pricing
 * button losing all its traffic. These names are already in the events table,
 * so they are the existing spellings and not tidier new ones.
 *
 * They are deliberately *not* the analytics stage names — `alma:cta_click`
 * carries this as a property, and `funnel.py` owns the stages themselves.
 */
export const JOURNEY_DOORS = ["nav", "insight", "pricing", "final", "cta_bar"] as const;

export type JourneyDoor = (typeof JOURNEY_DOORS)[number];

/**
 * What every one of those controls says.
 *
 * A function rather than a bare key so that the rule — one door, one sentence —
 * has somewhere to be written down and somewhere to be tested. If a sixth CTA
 * ever needs different words, it will have to come through here and argue for
 * itself instead of being typed straight into a component.
 */
export function journeyCta(t: Dictionary): string {
  return t.cta.read;
}
