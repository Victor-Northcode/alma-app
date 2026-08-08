"use client";

/**
 * The funnel, measured in a way that cannot cost a sale.
 *
 * One endpoint — `POST /v1/events`, body `{stage, properties?}` — and one rule
 * above every other consideration: **measurement never blocks and never
 * throws.** Nothing here is awaited by a caller, the request is fired and
 * forgotten, and every failure path ends in silence. A beacon that can reject
 * is a beacon that can reject inside a click handler on the pay button, and an
 * unmeasured purchase is worth infinitely more than a measured non-purchase.
 * That is why there is no retry, no queue and no `Promise` handed back: each of
 * those is a way for analytics to become a thing that has to work.
 *
 * **The stage names and the property keys are the server's, mirrored.** They
 * are not a convention this file invented — `alma/funnel.py` owns both lists,
 * validates against them, and answers 422 for anything outside them. A 422 is
 * refused *whole*: one unrecognised key and the stage is not recorded at all.
 * So the allowlist below exists to make a caller's mistake cost one dimension
 * rather than the entire event, and it has to be kept in step with the
 * frozenset in that module. Where the two disagree, the server is right.
 *
 * **Measuring somebody is not enrolling them.** This used to be the file that
 * created accounts: `POST /v1/events` minted one for any caller without a
 * token, and the first thing the landing does is fire `landing_view` on mount,
 * so a browser that loaded the page and touched nothing ended with a user row
 * and a bearer token. The account is now created by an act — saving a birth, or
 * signing in — and a stage from somebody who has done neither is recorded
 * against the anonymous id in `api.ts`: a random string, in this browser, that
 * grants nothing and buys nothing.
 *
 * **This is the only file that creates one.** `ensureAnonId` is called below,
 * *after* the opt-out check and nowhere else; `api.ts` reads the id but will
 * never mint it. So a person whose browser says do-not-track has no id written
 * to their storage at all, rather than one that is created and then politely
 * left unused — and the request that later mints their account carries the id
 * only if they never asked us not to measure them.
 *
 * **What is sent is one of those two identities, and nothing else.** The
 * request carries the same bearer token every other call carries, so the server
 * can attribute a stage to an account when there is one; it deliberately
 * carries no name, no address, no birth data and no free text. `properties` are
 * scrubbed down to short machine labels before they leave — see `scrub`, which
 * exists because the cheapest way for a person's email to end up in an
 * analytics table is for somebody to pass a form value straight through in six
 * months' time.
 *
 * **Opt-out is honoured before anything is built.** Do Not Track in its three
 * historical spellings, and Global Privacy Control, which is the one with legal
 * force behind it in California. Checked at every call rather than once at
 * import, because the header can be flipped by an extension mid-session.
 */

import { useEffect } from "react";

import { ANON_HEADER, API_BASE, ensureAnonId, readToken } from "./api";

/**
 * The four moments a browser is allowed to report.
 *
 * A closed union rather than a free string: the report is a comparison between
 * named stages, and a typo silently creates a fifth stage with a plausible name
 * and a count of one, which is the failure mode that makes analytics untrusted.
 * Here it is stricter still, because the server answers 422 for a name it does
 * not know and the event is simply lost.
 *
 * **These are the server's spellings, and this list is read by its tests.** The
 * last member used to be `declined` while `alma/funnel.py` spelled it
 * `offer_declined`, so every decline was answered 422 and thrown away by the
 * `.catch` below. A backend test now parses this union out of this file and
 * posts every name in it, so the two ends of the wire cannot drift apart again
 * in silence.
 *
 * **Four, where there were eight.** `offer_view`, `checkout_opened`,
 * `purchase_completed` and `offer_declined` all described the web checkout, and
 * the web no longer sells: the ladder is bought through Apple and Google, from
 * the apps. `alma/funnel.py` keeps all nine rungs, because the money still
 * happens and the server still reads `purchase` from the webhook — what changed
 * is only which of them a browser can honestly claim. A stage this file could
 * send but no screen could reach would read zero for ever and look like a
 * collapse in conversion rather than like a client that cannot get there.
 *
 * What is *not* here yet is the rung below `portrait_view`: somebody tapping
 * through to a store. It is unmeasurable rather than unmeasured — there are no
 * store URLs to tap (`lib/stores.ts`), and inventing a stage name for an event
 * that cannot fire is how a funnel acquires a rung nobody trusts.
 */
export type Stage =
  | "landing_view"
  | "quiz_start"
  | "quiz_complete"
  | "portrait_view";

/** Short machine labels. Never prose, and never anything a person typed. */
export type Properties = Record<string, string | number | boolean>;

/* ── opting out ────────────────────────────────────────────────────────── */

/**
 * The four signals a browser uses to say "do not measure me".
 *
 * Taken as a plain object rather than read from `navigator` inside the check so
 * that the rule is testable without a DOM — the tests here run in node.
 */
export interface OptOutSignals {
  /** `navigator.doNotTrack` — "1" everywhere modern, "yes" in older builds. */
  navigator?: string | null;
  /** `window.doNotTrack` — where IE and old Edge put the same flag. */
  window?: string | null;
  /** `navigator.msDoNotTrack` — the third spelling of the same thing. */
  ms?: string | null;
  /** `navigator.globalPrivacyControl` — GPC, and the one with a statute. */
  gpc?: boolean;
}

/**
 * Is this browser asking not to be measured?
 *
 * Any one signal is enough. Requiring agreement between them would mean
 * ignoring a person who set the only switch their browser offers, and the whole
 * value of an opt-out is that it takes one gesture rather than three.
 */
export function optedOut(signals: OptOutSignals): boolean {
  if (signals.gpc === true) return true;
  return [signals.navigator, signals.window, signals.ms].some(
    (value) => value === "1" || value === "yes",
  );
}

function browserSignals(): OptOutSignals {
  const nav = window.navigator as Navigator & {
    doNotTrack?: string | null;
    msDoNotTrack?: string | null;
    globalPrivacyControl?: boolean;
  };
  const win = window as Window & { doNotTrack?: string | null };
  return {
    navigator: nav.doNotTrack,
    window: win.doNotTrack,
    ms: nav.msDoNotTrack,
    gpc: nav.globalPrivacyControl,
  };
}

/* ── what may travel ───────────────────────────────────────────────────── */

/**
 * The only keys the table keeps, mirroring `funnel.PROPERTIES`.
 *
 * Every one of them describes the product rather than the person — which
 * system was on screen, which product was being bought, which language the page
 * was in. There is no free-text key on either side of the wire, which is what
 * makes it structurally impossible to end up with somebody's question or
 * somebody's name in a funnel row.
 */
const KEYS = new Set([
  "system",
  "chapter",
  "product",
  "locale",
  "step",
  "variant",
  "currency",
  "how",
]);

/**
 * A label, not a sentence.
 *
 * No whitespace and no `@`, which between them make it impossible to smuggle a
 * name, an address or anything a person typed into a funnel table by accident.
 * "natal", "dismissed", "pt-BR" pass; "Sofia Bianchi" and "sofia@example.com"
 * do not, and are dropped rather than truncated — a half of somebody's address
 * is still their address. Sixty-four characters is the server's own ceiling.
 *
 * **This used to be the only place the rule existed, which made it a rule about
 * one browser rather than about the table.** `funnel.clean_properties` checked
 * an allowed key and a length and nothing else, so both of the examples above
 * were short enough to be written straight into the column — refused here,
 * accepted there, and the difference invisible from either side. The server now
 * compiles the same pattern and a backend test reads this literal out of this
 * file and asks both ends about the same values, so the next edit to either one
 * has to be an edit to both.
 */
const LABEL = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;

/**
 * Keep the labels, drop everything else, and never complain.
 *
 * Both ends of the wire do this, for the same reason and in the same direction:
 * `funnel.clean_properties` also drops an unknown key and keeps the event,
 * because a 422 here would be swallowed by the beacon and the day somebody adds
 * one label to a screen the whole rung would vanish from the funnel for a
 * release. A missing dimension is a bad afternoon; a missing rung is a decision
 * made on a wrong number. (An unknown *stage* is refused outright at the other
 * end — that one has nowhere to be counted, so refusing it costs nothing.)
 *
 * The one asymmetry worth naming is what happens next. The server logs the key
 * it dropped, so somebody eventually reads the line and adds it to `PROPERTIES`;
 * this does not, because the caller is a click handler on the way to a purchase
 * and nothing measurement does may surface anywhere near one.
 */
export function scrub(properties: Properties | undefined): Properties | undefined {
  if (!properties) return undefined;
  const kept: Properties = {};
  let count = 0;
  for (const [key, value] of Object.entries(properties)) {
    if (!KEYS.has(key)) continue;
    if (typeof value === "boolean") {
      kept[key] = value;
    } else if (typeof value === "number") {
      if (!Number.isInteger(value)) continue;
      kept[key] = value;
    } else if (typeof value === "string") {
      if (!LABEL.test(value)) continue;
      kept[key] = value;
    } else {
      continue;
    }
    count += 1;
  }
  return count ? kept : undefined;
}

/* ── sending ───────────────────────────────────────────────────────────── */

/**
 * Record one stage. Returns nothing, waits for nothing, fails at nothing.
 *
 * `keepalive` rather than a bare fetch: the last stages of a funnel are fired
 * next to a navigation — a tap that leaves for a store listing — and a plain
 * request is cancelled when the document goes. It is
 * not `navigator.sendBeacon`, which cannot set an Authorization header and
 * would therefore send every event unattributed.
 *
 * **Both identities go, when both exist.** The token if there is one, and the
 * anonymous id always — the id is what ties this stage to the ones sent before
 * the account existed, and dropping it the moment a token appears would cut the
 * funnel in half at exactly the point conversion is measured.
 *
 * Nothing is read back off the response any more. This used to adopt the token
 * the route minted for a tokenless caller, which was the client half of the
 * behaviour being removed: a beacon is not an act, and a screen that records a
 * page view must not come away holding an account.
 */
export function track(stage: Stage, properties?: Properties): void {
  try {
    if (typeof window === "undefined") return;
    if (optedOut(browserSignals())) return;

    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const token = readToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    // Past the opt-out check, and the only call to it in the codebase. A person
    // who has asked not to be measured never reaches this line, so nothing is
    // written to their browser at all.
    const anon = ensureAnonId();
    if (anon) headers[ANON_HEADER] = anon;

    void fetch(`${API_BASE}/v1/events`, {
      method: "POST",
      headers,
      body: JSON.stringify({ stage, properties: scrub(properties) }),
      keepalive: true,
    }).catch(() => {
      /* a dead beacon is not a thing to tell anybody about */
    });
  } catch {
    /* as above: nothing measurement does may surface anywhere */
  }
}

/**
 * Stages that have already been recorded in this document.
 *
 * Module-level rather than per-component, because the thing being counted is
 * "a person reached this screen" and React will happily mount the same screen
 * twice — StrictMode does it on purpose in development, and a remount on a
 * state change would otherwise double every view in the report.
 */
const recorded = new Set<Stage>();

/** Record a stage the first time it happens, and never again this page load. */
export function trackOnce(stage: Stage, properties?: Properties): void {
  if (recorded.has(stage)) return;
  recorded.add(stage);
  track(stage, properties);
}

/**
 * Record a stage when a screen appears — the view half of the funnel.
 *
 * `properties` are read when the stage fires and are deliberately not a
 * dependency: they describe the screen rather than identify it, and re-firing a
 * view because an object literal was rebuilt on a re-render is exactly the
 * double-count `trackOnce` exists to prevent.
 */
export function useStage(stage: Stage, properties?: Properties): void {
  useEffect(() => {
    trackOnce(stage, properties);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);
}
