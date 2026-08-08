/**
 * Shapes the interface reads from.
 *
 * Most of what was here described the cabinet — a chapter with its body and
 * the positions it was read from, a synthesis axis with its verdict, a transit
 * with two lengths of caption, a `Profile` of somebody's name, email and birth
 * card. None of those screens exist on the web any longer; the app carries its
 * own models, and a type with no value of it is a shape nobody can be wrong
 * about, which is why it is not kept "just in case".
 *
 * What survives is the one thing the landing still needs: the eight cards, as
 * little of them as the landing actually renders.
 */

export type SystemSlug =
  | "natal"
  | "transits"
  | "numerology"
  | "compatibility"
  | "birth-card"
  | "solar-return"
  | "astrocartography"
  | "synthesis";

/** Cards are grouped by the user's question, not by the name of the system. */
export type QuestionGroup =
  | "who-am-i"
  | "right-now"
  | "this-year"
  | "how-we-match"
  | "where-to-be"
  | "all-of-it";

export interface SystemSummary {
  slug: SystemSlug;
  group: QuestionGroup;
  motif: "wheel" | "orbits" | "number" | "arcana" | "two-circles" | "globe" | "solar" | "axes";
  /**
   * The four "doors" — one per user question — shown on the landing from
   * tablet up. The remaining four are named in a line underneath.
   */
  door?: boolean;
}
