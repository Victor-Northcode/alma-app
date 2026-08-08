/**
 * One promise, and the four states it has to be true in.
 *
 * The handoff is the last thing the website says, and what it says about
 * continuity decides whether somebody re-enters their birth time or loses it.
 * The failure this guards is not a crash — every branch returns a perfectly
 * good sentence — it is a branch returning the *reassuring* sentence to
 * somebody it is not true for, which no type checks and no reviewer notices
 * once the copy has been edited twice.
 *
 * So: every branch, in every language, mapped to the string the dictionary
 * holds for it, plus the two precedence rules that are easy to get backwards.
 */

import { describe, expect, it } from "vitest";

import { carrySentence } from "./carry";
import { dictionaries } from "./i18n";

const EMAIL = "sofia@example.com";
const OTHER = "someone.else@example.com";

describe.each(Object.entries(dictionaries))("%s", (_locale, dictionary) => {
  const app = dictionary.app;

  it("names the address when the chart is on an account", () => {
    const said = carrySentence(app, { state: "attached", email: EMAIL }, null);
    expect(said).toBe(app.carryNamed(EMAIL));
    expect(said).toContain(EMAIL);
  });

  it("still promises the account when the address is unknown", () => {
    // Reachable through a provider that hides the address. The promise holds —
    // it is the account that carries the chart — but the sentence cannot name
    // an address it does not have, and interpolating an empty one would print
    // "This sky is on ." to somebody.
    expect(carrySentence(app, { state: "attached", email: null }, null)).toBe(app.carryAccount);
  });

  it("tells a guest plainly that the chart stays in the browser", () => {
    expect(carrySentence(app, { state: "guest" }, null)).toBe(app.carryGuest);
  });

  it("points a guest at the link that would rescue the chart", () => {
    expect(carrySentence(app, { state: "guest" }, EMAIL)).toBe(app.carrySent(EMAIL));
  });

  it("stays conditional when the backend did not answer", () => {
    expect(carrySentence(app, { state: "unknown" }, null)).toBe(app.carryUnknown);
  });

  it("prefers a link in flight over the guest sentence when both are true", () => {
    // Both describe the same person a second apart; only one of them tells
    // them not to throw the letter away.
    expect(carrySentence(app, { state: "unknown" }, EMAIL)).toBe(app.carrySent(EMAIL));
  });

  it("prefers the account over a link, even a link to another address", () => {
    // An account is a fact and a link is an intention. Somebody signed in as
    // one address who then asked for a link to another must not be told their
    // chart is waiting on the second one.
    expect(carrySentence(app, { state: "attached", email: EMAIL }, OTHER)).toBe(
      app.carryNamed(EMAIL),
    );
  });
});
