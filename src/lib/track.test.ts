/**
 * Four rules, and they are the only four worth a test here.
 *
 * The transport is a fire-and-forget `fetch` with a `.catch` that does nothing;
 * asserting that a promise was created proves nothing about the property that
 * matters, which is that no caller can ever be made to wait for or notice it.
 * What *can* go wrong silently, and would keep going wrong for months, is the
 * set below: a person's opt-out being ignored, something they typed arriving in
 * an analytics table because a caller passed a form value straight through, a
 * page view coming back with an account attached to it, and the id that ties one
 * visit together changing between two beacons — which reads as a hundred
 * visitors who each did exactly one thing and converted at zero.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

import { ANON_HEADER, readAnonId } from "./api";
import { FUNNEL_RETENTION_DAYS } from "./legal";
import { optedOut, scrub, track } from "./track";

describe("a browser asking not to be measured", () => {
  it("is obeyed on any one signal, not on agreement between them", () => {
    // The point of an opt-out is that it costs one gesture. Requiring two
    // switches to be set would mean ignoring everybody whose browser only
    // offers one, which is most of them.
    expect(optedOut({ navigator: "1" })).toBe(true);
    expect(optedOut({ window: "1" })).toBe(true);
    expect(optedOut({ ms: "1" })).toBe(true);
    expect(optedOut({ gpc: true })).toBe(true);
  });

  it("understands the older spelling as well as the current one", () => {
    expect(optedOut({ navigator: "yes" })).toBe(true);
  });

  it("measures when nothing has been asked for", () => {
    expect(optedOut({})).toBe(false);
    expect(optedOut({ navigator: null, window: undefined, gpc: false })).toBe(false);
    // "0" and "unspecified" are a browser saying it has no preference, which
    // is not the same as a person saying no.
    expect(optedOut({ navigator: "0" })).toBe(false);
    expect(optedOut({ navigator: "unspecified" })).toBe(false);
  });
});

describe("what a stage is allowed to carry", () => {
  it("keeps the keys the funnel table actually has", () => {
    expect(scrub({ product: "natal", system: "natal", locale: "pt-BR", step: 4 })).toEqual({
      product: "natal",
      system: "natal",
      locale: "pt-BR",
      step: 4,
    });
  });

  it("drops a key the server would refuse, instead of losing the whole event", () => {
    // `/v1/events` answers 422 for an unrecognised key and records nothing at
    // all. Mirroring its allowlist here is what turns "somebody added a key"
    // from a stage that silently stops being counted into one lost dimension.
    expect(scrub({ product: "natal", country: "IT" })).toEqual({ product: "natal" });
    expect(scrub({ email: "sofia@example.com" })).toBeUndefined();
  });

  it("drops anything a person could have typed", () => {
    // The failure being prevented is not malice. It is somebody, in a year,
    // putting a form value in `variant` because it was in scope.
    expect(scrub({ variant: "Sofia Bianchi" })).toBeUndefined();
    expect(scrub({ variant: "sofia@example.com" })).toBeUndefined();
    expect(scrub({ chapter: "Why do I keep leaving good things?" })).toBeUndefined();
  });

  it("refuses a label longer than the column the server keeps", () => {
    expect(scrub({ variant: "x".repeat(64) })).toEqual({ variant: "x".repeat(64) });
    expect(scrub({ variant: "x".repeat(65) })).toBeUndefined();
  });

  it("says nothing rather than an empty object when nothing survived", () => {
    expect(scrub(undefined)).toBeUndefined();
    expect(scrub({})).toBeUndefined();
    expect(scrub({ step: Number.NaN })).toBeUndefined();
    expect(scrub({ step: 1.5 })).toBeUndefined();
  });
});

/* ── who a beacon says it is ───────────────────────────────────────────── */

interface Beacon {
  url: string;
  headers: Record<string, string>;
}

/**
 * A browser with storage, a `fetch` that records instead of sending, and a
 * do-not-track flag the caller chooses.
 *
 * Built by hand rather than through a DOM environment: what is under test is
 * three lines of decision-making, and the whole point of those lines is what
 * they write to storage and what they put on the wire, both of which are
 * plainer to assert against a `Map` than against jsdom.
 */
function browser(signals: { doNotTrack?: string } = {}) {
  const stored = new Map<string, string>();
  const sent: Beacon[] = [];

  vi.stubGlobal("window", {
    localStorage: {
      getItem: (key: string) => stored.get(key) ?? null,
      setItem: (key: string, value: string) => void stored.set(key, value),
      removeItem: (key: string) => void stored.delete(key),
    },
    navigator: { doNotTrack: signals.doNotTrack ?? null },
  });
  vi.stubGlobal("fetch", (url: string, init: RequestInit) => {
    sent.push({ url, headers: init.headers as Record<string, string> });
    return Promise.resolve({} as Response);
  });

  return { stored, sent };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("a page view", () => {
  it("does not come back with an account attached to it", () => {
    // The bug this replaces: `POST /v1/events` minted an account for any
    // caller without a token, and the landing fires one on mount — so loading
    // the site and touching nothing left a user row and a bearer token behind.
    // Two thirds of the rows in the dev database were that.
    const { stored, sent } = browser();
    track("landing_view");

    expect(sent).toHaveLength(1);
    expect(sent[0].headers.Authorization).toBeUndefined();
    expect(stored.has("alma.token")).toBe(false);
  });

  it("carries one id for the whole visit, not one per beacon", () => {
    // A beacon per identity is the same broken funnel as an account per
    // beacon: the landing view belongs to somebody who never appears again and
    // the quiz belongs to somebody who was never seen arriving, so the first
    // conversion rate reads zero on data that looks perfectly healthy.
    const { sent } = browser();
    track("landing_view");
    track("quiz_start");

    const ids = sent.map((beacon) => beacon.headers[ANON_HEADER]);
    expect(ids[0]).toBeTruthy();
    expect(ids[1]).toBe(ids[0]);
  });

  it("keeps that id where the next request can find it", () => {
    // The request that mints the account has to carry it, or the server has
    // nothing to claim and the two halves of the journey stay two people.
    const { sent } = browser();
    track("landing_view");
    expect(readAnonId()).toBe(sent[0].headers[ANON_HEADER]);
  });

  it("sends an id the server will accept rather than drop", () => {
    // `funnel.clean_anon_id` refuses anything that does not look like an id we
    // would have issued, and a dropped id on a caller with no token is a 422.
    // Asserting the shape here is what stops that being discovered in a report
    // that reads zero, since the beacon swallows the refusal.
    const { sent } = browser();
    track("landing_view");
    expect(sent[0].headers[ANON_HEADER]).toMatch(/^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$/);
  });
});

describe("the id's own lifetime", () => {
  it("ends when the retention the privacy page promises ends", () => {
    // The page says the step labels *and the browser id* are deleted after 180
    // days. Only the first half was ever true: the server purged its rows and
    // the string in the browser stayed for ever, because nothing on the web
    // signs out and `clearToken` runs only on a 410. So the same person was
    // re-identified under the same id in year three, and a purged id could be
    // claimed afresh by a different account — an identifier with no end that is
    // eventually joined to a person, which is the one thing that page is for.
    const { stored, sent } = browser();
    track("landing_view");
    const first = sent[0].headers[ANON_HEADER];

    const aDayLate = Date.now() - (FUNNEL_RETENTION_DAYS + 1) * 24 * 60 * 60 * 1000;
    stored.set("alma.anon.minted", String(aDayLate));
    track("quiz_start");

    expect(sent[1].headers[ANON_HEADER]).not.toBe(first);
    expect(readAnonId()).toBe(sent[1].headers[ANON_HEADER]);
  });

  it("survives an ordinary visit a month later", () => {
    // The other direction, and the one that matters for the numbers: an id
    // that rotated on every visit would make every returning visitor a new
    // person and every rate in the report a rate over strangers.
    const { stored, sent } = browser();
    track("landing_view");

    stored.set("alma.anon.minted", String(Date.now() - 30 * 24 * 60 * 60 * 1000));
    track("quiz_start");

    expect(sent[1].headers[ANON_HEADER]).toBe(sent[0].headers[ANON_HEADER]);
  });

  it("re-mints an id it cannot date", () => {
    // A browser holding an id written before the timestamp existed. Its age is
    // unknowable, which means it might be anything, so it is treated as spent:
    // re-minting costs one joined visit and keeping it costs the promise.
    const { stored, sent } = browser();
    stored.set("alma.anon", "3f9a4c1e-77b2-4d0a-9c31-0f8e6b2a5d44");
    track("landing_view");

    expect(sent[0].headers[ANON_HEADER]).not.toBe("3f9a4c1e-77b2-4d0a-9c31-0f8e6b2a5d44");
  });
});

describe("a browser that asked not to be measured", () => {
  it("is given no id at all, rather than one that is politely not used", () => {
    // The difference between honouring an opt-out and describing one. Nothing
    // is sent, and — the part that would have been easy to miss — nothing is
    // written to their storage either.
    const { stored, sent } = browser({ doNotTrack: "1" });
    track("landing_view");

    expect(sent).toHaveLength(0);
    expect(stored.size).toBe(0);
    expect(readAnonId()).toBeNull();
  });
});
