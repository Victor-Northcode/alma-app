/**
 * The conversion between what a person says and what the engine needs.
 *
 * Worth its own test file for one reason: the twelve-hour clock has a trap in
 * it. 12 AM is midnight and 12 PM is noon, and the obvious implementation —
 * add twelve when it says PM — gets both of them wrong by exactly twelve
 * hours. Twelve hours moves the Ascendant halfway round the zodiac and
 * produces a chart that is entirely plausible and completely wrong, which is
 * the only kind of bug this product genuinely cannot survive.
 */

import { describe, expect, it } from "vitest";
import { api } from "./api";
import { birthFromJourney, saveBirth, toTwentyFourHour } from "./save-birth";
import type { JourneyState } from "./journey-store";

const JOURNEY: JourneyState = {
  date: { day: 14, month: 3, year: 1998 },
  intent: null,
  name: "Sofia Rossi",
  hour: "04",
  minute: "20",
  meridiem: "AM",
  timeUnknown: false,
  place: "Milan, Lombardy, Italy",
  placeDetail: {
    id: 3173435,
    label: "Milan, Lombardy, Italy",
    latitude: 45.4642,
    longitude: 9.19,
    timezone: "Europe/Rome",
  },
  savedProfileId: null,
};

describe("the twelve-hour clock", () => {
  it("keeps ordinary morning and afternoon times where they belong", () => {
    expect(toTwentyFourHour("04", "20", "AM")).toBe("04:20");
    expect(toTwentyFourHour("04", "20", "PM")).toBe("16:20");
    expect(toTwentyFourHour("11", "59", "AM")).toBe("11:59");
    expect(toTwentyFourHour("01", "05", "PM")).toBe("13:05");
  });

  it("puts midnight at 00 and noon at 12", () => {
    // The whole reason this file exists. Both of these are off by twelve
    // hours in the naive version, and both produce a believable chart.
    expect(toTwentyFourHour("12", "00", "AM")).toBe("00:00");
    expect(toTwentyFourHour("12", "30", "AM")).toBe("00:30");
    expect(toTwentyFourHour("12", "00", "PM")).toBe("12:00");
    expect(toTwentyFourHour("12", "45", "PM")).toBe("12:45");
  });

  it("does not care how the meridiem was capitalised", () => {
    expect(toTwentyFourHour("07", "00", "pm")).toBe("19:00");
    expect(toTwentyFourHour("07", "00", "Pm")).toBe("19:00");
  });

  it("pads both halves so the backend's HH:MM pattern matches", () => {
    expect(toTwentyFourHour("9", "5", "AM")).toBe("09:05");
  });

  it("never leaves the day", () => {
    for (const meridiem of ["AM", "PM"]) {
      for (let hour = 1; hour <= 12; hour++) {
        const [h, m] = toTwentyFourHour(String(hour), "00", meridiem).split(":").map(Number);
        expect(h).toBeGreaterThanOrEqual(0);
        expect(h).toBeLessThanOrEqual(23);
        expect(m).toBe(0);
      }
    }
  });
});

describe("turning the journey into a birth", () => {
  it("carries the date, the place and the zone", () => {
    const birth = birthFromJourney(JOURNEY);
    expect(birth).not.toBeNull();
    expect(birth!.birth_date).toBe("1998-03-14");
    expect(birth!.birth_time).toBe("04:20");
    expect(birth!.timezone).toBe("Europe/Rome");
    expect(birth!.latitude).toBeCloseTo(45.4642);
    expect(birth!.place_id).toBe(3173435);
  });

  it("pads a single-digit month and day into the ISO form", () => {
    const birth = birthFromJourney({ ...JOURNEY, date: { day: 2, month: 7, year: 1995 } });
    expect(birth!.birth_date).toBe("1995-07-02");
  });

  it("sends null for an unknown time rather than inventing noon", () => {
    // An assumed noon does not produce a weaker chart. It produces a
    // different person's chart, with identical confidence.
    const birth = birthFromJourney({ ...JOURNEY, timeUnknown: true });
    expect(birth!.birth_time).toBeNull();
  });

  it("refuses to build a birth without a resolved place", () => {
    // The typed name is not enough: a chart needs the coordinate and the
    // zone, and guessing either is how a reading ends up being about
    // somebody else.
    expect(birthFromJourney({ ...JOURNEY, placeDetail: null })).toBeNull();
  });

  it("refuses to build a birth without a date", () => {
    expect(birthFromJourney({ ...JOURNEY, date: null })).toBeNull();
  });

  it("treats a blank name as no name at all", () => {
    expect(birthFromJourney({ ...JOURNEY, name: "   " })!.name).toBeNull();
  });
});

describe("a time that was never entered", () => {
  const untouched = { ...JOURNEY, hour: null, minute: null };

  it("is treated as unknown, not as midnight", () => {
    // The dangerous version coerces "" to 0 and sends 00:00 — a precise
    // Ascendant computed from a field nobody filled in.
    expect(birthFromJourney(untouched)!.birth_time).toBeNull();
  });

  it("is unknown even if only part of the clock was set", () => {
    expect(birthFromJourney({ ...JOURNEY, hour: null })!.birth_time).toBeNull();
    expect(birthFromJourney({ ...JOURNEY, minute: null })!.birth_time).toBeNull();
  });

  /**
   * The meridiem is the one field that must NOT make a time unknown, and it
   * used to. The picker shows "AM" as a placeholder whether or not anything is
   * chosen, so an unset meridiem is indistinguishable on screen from a chosen
   * one — and requiring it threw away an hour and a minute the person had
   * actually entered. It now defaults to "AM" in the store, which is what the
   * field claimed all along.
   */
  it("keeps a time whose meridiem was never touched, because the field said AM", () => {
    const untouchedMeridiem = { ...JOURNEY, hour: "4", minute: "20" };
    expect(birthFromJourney(untouchedMeridiem)!.birth_time).toBe("04:20");
  });

  it("still saves everything else about the birth", () => {
    const birth = birthFromJourney(untouched)!;
    expect(birth.birth_date).toBe("1998-03-14");
    expect(birth.timezone).toBe("Europe/Rome");
  });
});

/**
 * One journey is one account.
 *
 * This became a rule worth testing on the day the account stopped being minted
 * by a page view. Before that, two saves racing each other both carried the
 * token the landing had already been given, so the second one wrote a second
 * profile onto the same row and nothing was lost. Now neither carries a token,
 * so each mints an account of its own — and `StepCeremony` saves from a
 * `useEffect(…, [])` while `reactStrictMode` runs effects twice on mount.
 *
 * Reproduced against a fresh database before the guard: two accounts 116
 * microseconds apart, two identical profiles, and a person holding whichever
 * token happened to land last. The other account keeps a chart nothing will
 * ever open again.
 */
describe("two saves racing each other", () => {
  it("is one request, so it is one account", async () => {
    let calls = 0;
    let release: (value: unknown) => void = () => {};
    const held = new Promise((resolve) => {
      release = resolve;
    });

    const original = api.saveProfile;
    api.saveProfile = (async () => {
      calls += 1;
      await held;
      return { ok: true, data: { id: "p1" } } as never;
    }) as typeof api.saveProfile;

    try {
      // Both start before either can finish — which is exactly the shape of
      // the double-invoked effect, and of any two callers on one screen.
      const first = saveBirth(JOURNEY);
      const second = saveBirth(JOURNEY);
      release(null);
      const [a, b] = await Promise.all([first, second]);

      expect(calls, "a second POST /v1/profiles mints a second account").toBe(1);
      expect(a).toBe(b);
    } finally {
      api.saveProfile = original;
    }
  });

  it("lets the next journey through once the first has settled", async () => {
    // A save that failed has to be retryable — the ceremony swallows the
    // failure and the portrait is where it shows — and somebody who corrects a
    // birthplace and walks the journey again is making a real second request.
    let calls = 0;
    const original = api.saveProfile;
    api.saveProfile = (async () => {
      calls += 1;
      return { ok: false, kind: "offline", message: "no connection to Alma" } as never;
    }) as typeof api.saveProfile;

    try {
      await saveBirth(JOURNEY);
      await saveBirth(JOURNEY);
      expect(calls).toBe(2);
    } finally {
      api.saveProfile = original;
    }
  });
});
