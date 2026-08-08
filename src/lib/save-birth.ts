"use client";

/**
 * Turning what the journey collected into a saved birth.
 *
 * This is the seam where a person stops being a visitor and starts having a
 * chart, so it is worth being exact about two things.
 *
 * **The clock.** The journey collects the hour in twelve-hour form with a
 * meridiem, because that is how people say it. The engine needs twenty-four
 * hour local time. 12 AM is midnight and 12 PM is noon, which is the one
 * pair every naive conversion gets backwards — and getting it backwards
 * moves the Ascendant by half a circle while producing a chart that looks
 * entirely reasonable.
 *
 * **Not knowing.** `timeUnknown` produces `null`, never "12:00". The backend
 * treats null as a first-class state and refuses the systems that need a
 * horizon; a fabricated noon would instead produce confident, wrong houses.
 */

import { api, isOk, type BirthInput, type Failure, type Profile } from "./api";
import type { JourneyState } from "./journey-store";

export function toTwentyFourHour(hour: string, minute: string, meridiem: string): string {
  const h = Number(hour);
  const m = Number(minute);
  if (!Number.isFinite(h) || !Number.isFinite(m)) return "12:00";

  const upper = meridiem.toUpperCase();
  let hours = h % 12; // 12 AM → 0, 12 PM → 12 once the branch below runs
  if (upper === "PM") hours += 12;
  return `${String(hours).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/**
 * Whether a real birth time was entered.
 *
 * Declared unknown and never filled in are the same fact, and both must
 * produce a null rather than a guess — an empty hour coerces to zero, which
 * would silently send midnight and hand back an Ascendant nobody asked for.
 */
export function hasTime(state: JourneyState): boolean {
  // The meridiem is not checked here any more and cannot be: it defaults to
  // "AM" in the store, because the picker has always *displayed* "AM" whether
  // or not anything was chosen. Requiring it meant an unset meridiem — which
  // looked identical to a chosen one — threw away an hour and a minute the
  // person had genuinely entered. An hour and a minute are still both
  // required, so tapping straight through still produces no time.
  return !state.timeUnknown && Boolean(state.hour) && Boolean(state.minute);
}

export function birthFromJourney(state: JourneyState): BirthInput | null {
  const { date, placeDetail } = state;
  if (!date || !placeDetail) return null;

  return {
    birth_date: `${date.year}-${String(date.month).padStart(2, "0")}-${String(date.day).padStart(2, "0")}`,
    // Unknown stays unknown — declared or simply never set. Both are the same
    // fact, and the backend is built to answer honestly about what it cannot
    // compute without it. The dangerous version of this line would coerce a
    // blank hour to 0 and quietly send midnight.
    birth_time: hasTime(state)
      ? toTwentyFourHour(state.hour!, state.minute!, state.meridiem)
      : null,
    latitude: placeDetail.latitude,
    longitude: placeDetail.longitude,
    timezone: placeDetail.timezone,
    place_label: placeDetail.label,
    place_id: placeDetail.id,
    name: state.name.trim() || null,
  };
}

export type SaveOutcome =
  | { ok: true; profile: Profile }
  | { ok: false; reason: "incomplete" }
  | { ok: false; reason: "failed"; error: Failure };

/**
 * The save that is currently in flight, if there is one.
 *
 * Module-level rather than a `useRef`, because the thing being deduplicated is
 * a request rather than a component: whoever calls `saveBirth` while one is
 * already going gets that one back instead of starting a second.
 *
 * **This became load-bearing when the account stopped being minted on page
 * load.** `StepCeremony` saves from a `useEffect(…, [])`, and `reactStrictMode`
 * runs effects twice on mount in development — so two `POST /v1/profiles` went
 * out microseconds apart. That used to be harmless: the landing had already
 * minted an account, both requests carried its token, and the second one simply
 * wrote a second profile onto the same row. Now neither request carries a
 * token, so **each of them mints an account of its own**, and one journey ends
 * as two users, two identical profiles, and a person holding whichever token
 * arrived last. Reproduced against a fresh database: two accounts created
 * 116 microseconds apart, both named Sofia Bianchi, born on the same day, in
 * Milan.
 *
 * The claim table survives it correctly — first claim wins, so the browser id
 * belongs to exactly one of the two, and the funnel reports one person rather
 * than a plausible wrong number. What it cannot fix is the orphan: an account
 * with a chart in it that nothing will ever open again.
 *
 * StrictMode's double-invoke is development-only, so this was never reaching a
 * real visitor. It is guarded anyway, because "two concurrent requests with no
 * token mint two accounts" is a property of the whole design rather than of one
 * effect — `funnel.claim`'s own docstring names that race — and the next caller
 * to save from somewhere else should not have to know.
 */
let inFlight: Promise<SaveOutcome> | null = null;

/**
 * Save the birth the journey collected.
 *
 * Called at the end of the journey rather than at each step: a person who
 * abandons halfway has not asked us to keep anything, and storing a partial
 * birth would leave the cabinet reading a chart its owner never finished
 * entering.
 *
 * Two concurrent calls are one request. See `inFlight` for why that matters
 * more than it used to.
 */
export function saveBirth(state: JourneyState): Promise<SaveOutcome> {
  if (inFlight) return inFlight;

  const birth = birthFromJourney(state);
  if (!birth) return Promise.resolve({ ok: false, reason: "incomplete" });

  inFlight = api
    .saveProfile({ ...birth, is_self: true })
    .then((result): SaveOutcome =>
      isOk(result)
        ? { ok: true, profile: result.data }
        : { ok: false, reason: "failed", error: result },
    )
    .finally(() => {
      // Cleared when it settles rather than kept for the session: a failed
      // save has to be retryable — the ceremony swallows the failure and the
      // portrait is where it becomes visible — and a person who corrects a
      // birthplace and walks the journey again is making a second real request.
      inFlight = null;
    });

  return inFlight;
}
