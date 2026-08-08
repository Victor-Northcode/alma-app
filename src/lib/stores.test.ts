/**
 * One rule about the last link on the website: **it is a store or it is
 * nothing.**
 *
 * Neither app has been accepted anywhere yet, so both constants are empty and
 * the handoff renders "coming to the App Store" instead of a badge. The
 * dangerous moment is not now — it is the afternoon somebody wants the page to
 * look finished and pastes in a search URL, a TestFlight invite, a Play Console
 * internal-testing link or `pazl.ai` itself. Each of those reads as "download
 * the app" to a visitor and to a reviewer, and none of them is one; the first
 * two also expire.
 *
 * So this asserts the only thing that can be asserted about a constant that is
 * meant to be empty today: it is empty, or it is on the store's own host. It is
 * deliberately not a test that the URLs are set — the empty state is correct
 * and shipping, and a red test for a fact about the world that has not happened
 * yet is a test people learn to ignore.
 *
 * The rest of the file guards the *other* half of launch day, which is the half
 * that gets forgotten because nothing on screen looks wrong without it: a badge
 * with no artwork behind it, a Safari banner pointing at a different app than
 * the badge, a Play link for a package we do not ship. Each of those is a
 * one-line mistake made once, in a hurry, on the busiest day this product will
 * have.
 */

import { existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  APPLE_APP_ID,
  APP_STORE_BADGE,
  APP_STORE_URL,
  PLAY_PACKAGE,
  PLAY_STORE_BADGE,
  PLAY_STORE_URL,
  STORE_HOSTS,
} from "./stores";

const PUBLIC = join(__dirname, "..", "..", "public");

describe("the store links", () => {
  it("is either unset or on Apple's own host", () => {
    expect(APP_STORE_URL === "" || APP_STORE_URL.startsWith(STORE_HOSTS.apple)).toBe(true);
  });

  it("is either unset or on Google's own host", () => {
    expect(PLAY_STORE_URL === "" || PLAY_STORE_URL.startsWith(STORE_HOSTS.google)).toBe(true);
  });

  it("names hosts that are the stores themselves, not a redirect we control", () => {
    // `alma.pazl.ai` does not resolve and `pazl.ai` is a marketing apex.
    // Neither may become the destination of a badge that says "App Store".
    expect(STORE_HOSTS.apple).toBe("https://apps.apple.com/");
    expect(STORE_HOSTS.google).toBe("https://play.google.com/");
  });
});

describe("the smart banner and the badge point at the same app", () => {
  it("holds an app id that is a number, or nothing", () => {
    // It goes into `<meta name="apple-itunes-app" content="app-id=…">` verbatim.
    // Safari ignores a malformed one silently, so a typo here is a banner that
    // simply never appears and nobody can explain why.
    expect(APPLE_APP_ID === "" || /^\d{6,12}$/.test(APPLE_APP_ID)).toBe(true);
  });

  it("does not publish a listing without the id the banner needs", () => {
    // The badge and the banner are the same launch. Filling in one and not the
    // other ships a page that converts on desktop and stays silent in the one
    // browser where a native banner outperforms everything else on the screen.
    if (APP_STORE_URL) expect(APPLE_APP_ID).not.toBe("");
  });

  it("links the listing of the app the banner names", () => {
    // `apps.apple.com/app/id123…` and `app-id=123…` disagreeing sends the badge
    // to one product and the banner to another, and both look right.
    if (APP_STORE_URL && APPLE_APP_ID) expect(APP_STORE_URL).toContain(`id${APPLE_APP_ID}`);
  });

  it("links the Play listing of the package we actually ship", () => {
    // `PLAY_PACKAGE` mirrors `applicationId` in the Android build file. A Play
    // URL for anything else is a badge pointing at somebody else's app.
    if (PLAY_STORE_URL) expect(PLAY_STORE_URL).toContain(`id=${PLAY_PACKAGE}`);
  });
});

describe("a live badge has the store's own artwork behind it", () => {
  /**
   * Apple and Google both require their supplied badge artwork and both forbid
   * redrawing it, so the artwork cannot be committed ahead of the listing
   * without shipping a badge that looks tappable and is not. That leaves one
   * failure worth catching: the URL going in without the file, which renders a
   * broken image in the place a person is meant to tap.
   */
  it.each([
    ["App Store", APP_STORE_URL, APP_STORE_BADGE],
    ["Google Play", PLAY_STORE_URL, PLAY_STORE_BADGE],
  ])("%s", (_store, url, badge) => {
    if (!url) return;
    expect(
      existsSync(join(PUBLIC, badge.replace(/^\//, ""))),
      `${badge} is missing — download it from the store's brand guidelines`,
    ).toBe(true);
  });
});
