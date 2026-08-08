/**
 * Whether the chart made on this website will be there when the app opens.
 *
 * The last screen of the storefront has to answer that, and it is the one
 * sentence on the site with a real chance of being a lie — because the flattering
 * version ("everything is saved, see you in the app") is true for some people and
 * false for others, and nothing on screen distinguishes them. So the rule lives
 * here, in a pure function with a test, rather than inside the component that
 * renders it.
 *
 * **The mechanism, which the copy has to match exactly.** A birth saved from the
 * web belongs to whatever account the token in this browser's local storage
 * identifies, and that is a *guest* account until an address is attached to it. A
 * fresh install of the app has no such token and no way to ask for one: there is
 * no pairing code, no QR handoff and no deep link, and the host both mobile
 * builds are compiled against does not currently resolve. An identity is the only
 * bridge that exists. Everything below follows from that, and the day a real
 * transfer is built this file is where the new promise goes.
 */

import type { Dictionary } from "./i18n";

/**
 * What we know about this browser. `unknown` is a real answer rather than a
 * loading state to be styled away — see `useIdentity`, which leaves it that way
 * when the backend cannot be reached.
 */
export type Identity =
  | { state: "unknown" }
  | { state: "guest" }
  | { state: "attached"; email: string | null };

/**
 * The sentence for this person, in this state.
 *
 * The order of the branches is the argument, and it is not the order they were
 * written in:
 *
 * **attached** first, and it beats a link in flight. The account is a fact; a
 * link is an intention, and it may even be for a different address than the one
 * the person is already signed in as. This is the only case where "it is already
 * there" may be said at all.
 *
 * **a link sent in this session** second, ahead of plain guest. It is not merely
 * a sign-in that has not happened yet: `POST /v1/auth/magic-link` stores the
 * guest's id *on the link*, so consuming it — from any device, days later —
 * folds this exact chart into the account. The link is what rescues the chart,
 * and lumping this person in with somebody who skipped the step would tell them
 * to re-enter a birth time they are about to keep.
 *
 * **guest** third: nothing is attached and nothing will be. Saying so costs one
 * sentence. Not saying it costs somebody the birth minute they will not remember.
 *
 * **unknown** last, stated conditionally, because with no answer from the server
 * both halves are all that is honestly left — and both halves are still useful.
 */
export function carrySentence(
  app: Dictionary["app"],
  identity: Identity,
  linkSentTo: string | null,
): string {
  if (identity.state === "attached") {
    return identity.email ? app.carryNamed(identity.email) : app.carryAccount;
  }
  if (linkSentTo) return app.carrySent(linkSentTo);
  if (identity.state === "guest") return app.carryGuest;
  return app.carryUnknown;
}
