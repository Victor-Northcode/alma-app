/**
 * Is this worth sending to the server as an address?
 *
 * Deliberately the loosest check that catches the typo people actually make —
 * a missing or dangling `@`. Anything stricter starts rejecting addresses that
 * are perfectly valid: apostrophes, plus tags, new top-level domains, and the
 * whole of the internationalised world. The backend validates properly; this
 * exists only so the common slip does not cost a round trip and an unexplained
 * failure at the button.
 *
 * It used to live in `lib/checkout.ts`, which sold things and no longer exists.
 * The sign-in panel was the other caller and is now the only one, so the rule
 * came here rather than being inlined there — inlining it would have made the
 * one place that decides what an address looks like a private detail of one
 * component, and the next caller would write a second, stricter copy.
 */

export function looksLikeEmail(address: string): boolean {
  const trimmed = address.trim();
  return (
    trimmed.includes("@") && !trimmed.startsWith("@") && !trimmed.endsWith("@")
  );
}
