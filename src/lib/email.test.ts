/**
 * What counts as an address worth sending to the server.
 *
 * These cases used to live at the bottom of `checkout.test.ts`, under the
 * heading "the address a session is created against", beside a suite that
 * tested which payment overlay to open. That suite is gone with the checkout
 * it guarded — a test for deleted code is deleted with it — but this half is a
 * rule rather than a mechanism, and the rule did not change when the thing
 * asking for the address did: it is now the sign-in panel rather than the pay
 * button, and it must still be the loosest check that catches the typo people
 * actually make.
 *
 * The second case is the one that matters. Every address in it is real and
 * deliverable, and every one of them is refused by the regex somebody
 * eventually wants to put here — which on this screen costs a sign-in, for a
 * product where signing in is the only way to keep what you have.
 */

import { describe, expect, it } from "vitest";
import { looksLikeEmail } from "./email";

describe("the address a sign-in link is sent to", () => {
  it("catches the slip people actually make", () => {
    expect(looksLikeEmail("sofia@example.com")).toBe(true);
    expect(looksLikeEmail("  sofia@example.com  ")).toBe(true);
    expect(looksLikeEmail("sofia")).toBe(false);
    expect(looksLikeEmail("@example.com")).toBe(false);
    expect(looksLikeEmail("sofia@")).toBe(false);
    expect(looksLikeEmail("")).toBe(false);
  });

  it("does not reject addresses that are unusual but valid", () => {
    expect(looksLikeEmail("sofia+alma@example.co.uk")).toBe(true);
    expect(looksLikeEmail("o'brien@example.museum")).toBe(true);
    expect(looksLikeEmail("софия@пример.рф")).toBe(true);
    expect(looksLikeEmail("sofia@localhost")).toBe(true);
  });
});
