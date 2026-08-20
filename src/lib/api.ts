/**
 * The client for the Alma backend.
 *
 * Three things this file is responsible for, and nothing else lives here.
 *
 * **The guest token.** Every request carries it; the request that first *needs*
 * an account gets one back in `X-Alma-Token` and stores it. That is what makes
 * the product usable before anyone has signed in — and why the token is
 * captured from *every* response rather than only from the sign-in call, since
 * which request turns out to be that one depends on what the person does.
 *
 * What no longer mints an account is a page view. `POST /v1/events` answered
 * every tokenless beacon with a fresh account, and the landing fires one on
 * mount, so loading the site and touching nothing left a row behind. The
 * account is created by an act — a birth saved, a sign-in landed — and the
 * anonymous id below is what keeps the funnel joinable across that moment.
 *
 * **Typed failures.** The backend answers a locked chapter with 402, a
 * missing birth time with 422, and a daylight-saving ambiguity with 409 and
 * two candidate instants. Each of those is a thing the interface has to
 * *say*, not an error to swallow, so they come back as a discriminated union
 * rather than a thrown `Error` with a message in it.
 *
 * **Nothing else.** No caching, no retries, no astrology. A component that
 * needs a chart asks for one.
 */

import type { Locale } from "./i18n";
import { FUNNEL_RETENTION_DAYS } from "./legal";

export const API_BASE =
  process.env.NEXT_PUBLIC_ALMA_API?.replace(/\/$/, "") ?? "http://localhost:8000";

const TOKEN_KEY = "alma.token";
// Exported because the funnel beacon in `track.ts` reads the same header off
// its own response, and a second copy of this string is a second thing to get
// wrong the day it changes.
export const TOKEN_HEADER = "x-alma-token";

const ANON_KEY = "alma.anon";
/**
 * When the id in `alma.anon` was minted, as epoch milliseconds.
 *
 * Stored beside the id rather than encoded into it, so that the id stays the
 * opaque random string the backend's `ANON_ID` pattern expects and the two
 * facts can be read independently. A browser whose storage holds an id and no
 * timestamp — one written before this existed — is treated as expired on the
 * next call, which re-mints once and then behaves.
 */
const ANON_MINTED_KEY = "alma.anon.minted";
export const ANON_HEADER = "x-alma-anon";

/* ── the session token ─────────────────────────────────────────────────── */

/**
 * The bearer token lives in `localStorage`, and that is a **deliberate,
 * accepted trade-off** rather than an oversight — written here so the decision
 * is on the record where the code makes it (a QA note, 2026-08-20, flagged it
 * as an undocumented risk).
 *
 * The risk it accepts: `localStorage` is readable by any script on the origin,
 * so a future XSS would be able to steal the token. There are no XSS sinks
 * today — the app renders no user HTML — but the mitigation is not "trust that
 * forever", it is the CSP added in `next.config.ts` (BUG-004), which is the
 * layer that keeps injected script from running in the first place.
 *
 * Why not an httpOnly cookie, the usual answer: the same token authenticates
 * the iOS and Android clients, which have no cookie jar and read it from a
 * native store, and the web client has to be able to *hand it back* to the
 * request that minted it (`X-Alma-Token`) — a cookie the script cannot read
 * breaks that handoff. Moving the web flow alone to an httpOnly cookie is a
 * real project (a server-side session shim in front of a token API), and it is
 * the owner's to schedule, not something to change under a QA pass. If it is
 * ever done, this is the comment to delete.
 */
export function readToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function writeToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* private browsing: the session lasts the tab, which is survivable */
  }
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(TOKEN_KEY);
    // The id goes with the token, always. It is only ever cleared when the
    // account behind it is gone, and a browser that kept it would carry an
    // identifier belonging to somebody who asked to be deleted straight into
    // the next account it makes.
    window.localStorage.removeItem(ANON_KEY);
    window.localStorage.removeItem(ANON_MINTED_KEY);
  } catch {
    /* as above */
  }
}

/* ── the anonymous id ──────────────────────────────────────────────────── */

/**
 * Who this browser is, before there is anybody to be.
 *
 * The account used to be minted by the first request that arrived without a
 * token, which meant the landing page's own `landing_view` beacon created one
 * on every page load — two thirds of the rows in the dev database were people
 * who had never typed anything. The account is now created by an act: saving a
 * birth, or signing in. Which leaves a real question the funnel cannot do
 * without — *of the people who saw the landing, how many finished* — and this
 * is the answer to it.
 *
 * It is a random string. Not derived from the browser, the screen, the fonts or
 * anything else that could be recomputed about this device; not a fingerprint,
 * not a session id, and not a thing anybody can sign in with. Its whole job is
 * to say that the landing view and the quiz an hour later were the same visit,
 * and to be claimable by the account when one is finally created — which is why
 * it goes on *every* request rather than only on the beacons. The request that
 * mints the account is the one moment the server can honestly record that this
 * browser became that account.
 *
 * **Nothing here mints it.** `read` returns what is stored and `ensure` is
 * called from exactly one place: `track.ts`, after it has checked Do Not Track
 * and Global Privacy Control. A person who has asked not to be measured
 * therefore gets no id at all — nothing written to their storage, nothing sent
 * — rather than an id that is created and then politely not used. That is the
 * difference between honouring an opt-out and describing one.
 *
 * **And it expires.** The privacy page promises that the step labels and the
 * browser id are deleted after `FUNNEL_RETENTION_DAYS`, and until this existed
 * only the first half of that was true: the server purged the rows and the
 * string in the browser stayed for ever, because nothing on the web signs out
 * and `clearToken` runs only on a 410. So the same visitor was re-identified
 * under the same id in year three, and a purged id could be claimed afresh by a
 * *different* account — an identifier with an unbounded life that is eventually
 * joined to a person, which is exactly the shape the page exists to promise we
 * do not keep. It now dies on the same schedule the rows do, on this side of
 * the wire as well as on the server's.
 */
export function readAnonId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(ANON_KEY);
  } catch {
    return null;
  }
}

/**
 * How long a browser keeps one id before minting another, in milliseconds.
 *
 * The same number the backend purges on and the same number the privacy page
 * prints, imported rather than repeated: `legal.ts` holds it, a test ties it to
 * `PURGE_AFTER_DAYS` in `alma/funnel.py`, and a fourth copy of "180" would be
 * the one that quietly disagrees.
 */
const ANON_LIFETIME_MS = FUNNEL_RETENTION_DAYS * 24 * 60 * 60 * 1000;

/** Whether the stored id has outlived the retention the product promises. */
function anonExpired(now: number): boolean {
  try {
    const minted = Number(window.localStorage.getItem(ANON_MINTED_KEY));
    // `NaN` — no timestamp, or an unreadable one — is expired. That is the
    // direction that fails safe: an id whose age cannot be established is one
    // whose age might be anything, and re-minting costs a browser one joined
    // visit while keeping it costs the promise on the privacy page.
    return !Number.isFinite(minted) || now - minted >= ANON_LIFETIME_MS;
  } catch {
    return true;
  }
}

/** The stored id, or a new one. Only `track.ts` calls this — see above. */
export function ensureAnonId(): string | null {
  if (typeof window === "undefined") return null;
  const now = Date.now();
  const existing = readAnonId();
  if (existing && !anonExpired(now)) return existing;

  const minted = randomId();
  try {
    window.localStorage.setItem(ANON_KEY, minted);
    window.localStorage.setItem(ANON_MINTED_KEY, String(now));
  } catch {
    /* private browsing: the id lasts this page, which undercounts returning
       visits and is survivable. Sending it anyway keeps *this* visit joined. */
  }
  return minted;
}

/**
 * A random id, from the strongest source this browser actually has.
 *
 * `crypto.randomUUID` needs a secure context, which a developer on a phone
 * pointed at a laptop over plain http does not have, and `getRandomValues` does
 * not. The last fallback is `Math.random`, which is not a security decision
 * because none of this is one: the id authorises nothing, and the cost of a
 * collision is two visits counted as one in a report.
 */
function randomId(): string {
  const source = typeof crypto === "undefined" ? undefined : crypto;
  if (source?.randomUUID) return source.randomUUID();
  if (source?.getRandomValues) {
    const bytes = source.getRandomValues(new Uint8Array(16));
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`;
}

/* ── results ───────────────────────────────────────────────────────────── */

export type Ok<T> = { ok: true; data: T };

export type Failure =
  | { ok: false; kind: "locked"; system: string; chapter?: string; message: string }
  | { ok: false; kind: "needs-birth-time"; message: string }
  | { ok: false; kind: "ambiguous-time"; message: string; options: AmbiguityOption[] }
  | { ok: false; kind: "unauthenticated"; message: string }
  | { ok: false; kind: "account-deleted"; message: string }
  | { ok: false; kind: "unavailable"; message: string }
  | { ok: false; kind: "offline"; message: string }
  | { ok: false; kind: "invalid"; message: string }
  // `code` carries the backend's typed `error` string when there is one, so a
  // caller can branch on it instead of reading the English message. Added for
  // the magic-link screen, which used to classify used/expired/invalid by
  // substring and mislabelled an offline failure as an invalid link.
  | { ok: false; kind: "error"; status: number; message: string; code?: string };

export type Result<T> = Ok<T> | Failure;

export interface AmbiguityOption {
  choice: "earlier" | "later";
  utc: string;
}

/** Narrow a result without repeating the discriminant everywhere. */
export function isOk<T>(result: Result<T>): result is Ok<T> {
  return result.ok;
}

/* ── the request ───────────────────────────────────────────────────────── */

interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
  signal?: AbortSignal;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<Result<T>> {
  const url = new URL(`${API_BASE}${path}`);
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined) url.searchParams.set(key, String(value));
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = readToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  // Read, never minted. On the request that mints an account — saving a birth,
  // landing a sign-in link — this is what the server claims, so that the stages
  // recorded before the account and the stages recorded after it stay one
  // person in the funnel. `ensureAnonId` is called only by `track.ts`, behind
  // the opt-out check, which is why this line cannot create one.
  const anon = readAnonId();
  if (anon) headers[ANON_HEADER] = anon;

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch {
    // A dead network and a dead backend look the same from here, and the
    // interface says the same thing about both.
    return { ok: false, kind: "offline", message: "no connection to Alma" };
  }

  // Any response may mint a guest token — the very first one usually does.
  const issued = response.headers.get(TOKEN_HEADER);
  if (issued) writeToken(issued);

  if (response.status === 204) return { ok: true, data: undefined as T };

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (response.ok) return { ok: true, data: payload as T };
  return classify(response.status, payload);
}

function classify(status: number, payload: unknown): Failure {
  const detail = (payload as { detail?: unknown })?.detail;
  const asObject = (detail && typeof detail === "object" ? detail : payload) as
    | Record<string, unknown>
    | null;
  const message =
    (typeof detail === "string" ? detail : (asObject?.message as string)) ??
    "something went wrong";

  switch (asObject?.error) {
    case "locked":
      return {
        ok: false,
        kind: "locked",
        system: String(asObject.system ?? ""),
        chapter: asObject.chapter as string | undefined,
        message,
      };
    case "birth_time_required":
      return { ok: false, kind: "needs-birth-time", message };
    case "ambiguous_birth_time":
      return {
        ok: false,
        kind: "ambiguous-time",
        message,
        options: (asObject.options as AmbiguityOption[]) ?? [],
      };
    // Two, where there were four. `ai_unavailable` and `budget_exceeded` are
    // answers to `/v1/readings` and `/v1/chat`, and nothing on the web asks
    // either any more — a branch for a reply that cannot arrive is a claim
    // about the wire that stopped being true.
    case "billing_unavailable":
    case "place_index_missing":
      return { ok: false, kind: "unavailable", message };
    default:
      break;
  }

  if (status === 401) return { ok: false, kind: "unauthenticated", message };
  if (status === 402) return { ok: false, kind: "locked", system: "", message };
  if (status === 410) {
    // The account behind this token is gone. Holding on to it would make
    // every later request fail the same way.
    clearToken();
    return { ok: false, kind: "account-deleted", message };
  }
  if (status === 422) return { ok: false, kind: "invalid", message };
  if (status === 503) return { ok: false, kind: "unavailable", message };
  return {
    ok: false,
    kind: "error",
    status,
    message,
    code: typeof asObject?.error === "string" ? asObject.error : undefined,
  };
}

/* ── shapes the interface reads ────────────────────────────────────────── */

export interface Place {
  id: number;
  name: string;
  region: string | null;
  country: string;
  country_code: string;
  label: string;
  latitude: number;
  longitude: number;
  timezone: string;
}

export interface BirthInput {
  birth_date: string;
  birth_time?: string | null;
  latitude: number;
  longitude: number;
  timezone: string;
  place_label?: string | null;
  place_id?: number | null;
  name?: string | null;
  on_ambiguous?: "raise" | "earlier" | "later";
}

export interface Profile extends Omit<BirthInput, "on_ambiguous"> {
  id: string;
  relation: string | null;
  is_self: boolean;
}

export interface Session {
  token: string;
  user_id: string;
  is_guest: boolean;
  email: string | null;
  display_name: string | null;
  locale: string;
}

export interface Access {
  allowed: boolean;
  reason: string;
  kind: string | null;
  expires_at: string | null;
}

export interface CalcResult {
  system: string;
  engine_version: string;
  computed_at: string;
  subject: Record<string, unknown>;
  data: Record<string, unknown>;
  factors: string[];
  unavailable: string[];
  notes: string[];
  provenance: Record<string, unknown>;
  access: Access;
  locked?: boolean;
}

/* ── the endpoints ─────────────────────────────────────────────────────── */

/**
 * The endpoints the storefront still calls, and no others.
 *
 * Eighteen went in one afternoon — the hub, the chapter list, a reading, the
 * chat and its threads, the memory, the profile list, the entitlements, the
 * checkout, the downsell, the cancellation. All of them belonged to screens
 * that are no longer served from a browser, and every one of them is still on
 * the backend, still tested, still called by the two apps. What is gone is
 * this end of the wire: a client method with no caller is a promise that the
 * shape it declares is the shape the server sends, and nothing checks it.
 *
 * Eight are left, and each of them is one thing the website does: ask who this
 * token belongs to, ask for a sign-in link, land one, sign in with Google,
 * search the place index while somebody types, save the birth the journey
 * collected, calculate a system for the portrait, and read the price list the
 * landing quotes.
 */
export const api = {
  /**
   * Who this token belongs to — guest, or somebody with an address.
   *
   * Came back with the handoff, which is the one screen that has to tell the
   * truth about whether the chart just calculated will still be there when the
   * app opens. That answer is server state and nothing else: a person can sign
   * in in another tab, or arrive already signed in from a visit last week, and
   * a flag this client set during *this* journey would be wrong in both cases.
   *
   * It mints a guest account for a caller who has no token at all, which is why
   * the hook that wraps it declines to call it in that case — the handoff must
   * not create a row just by being looked at.
   */
  session: () => request<Session>("/v1/auth/session"),

  requestMagicLink: (email: string, locale: Locale) =>
    request<{ sent: boolean; debug_token?: string }>("/v1/auth/magic-link", {
      method: "POST",
      body: { email, locale },
    }),

  consumeMagicLink: (token: string) =>
    request<Session>("/v1/auth/magic-link/consume", { method: "POST", body: { token } }),

  /**
   * The provider's ID token, handed straight to the backend.
   *
   * Never decoded here. A token verified in the browser is a token verified
   * by whoever controls the browser — the signature check against Google's
   * published keys, and the audience check that it was minted for *us*,
   * both happen server-side in alma/auth/providers.py.
   */
  googleSignIn: (credential: string) =>
    request<Session>("/v1/auth/google", { method: "POST", body: { credential } }),

  searchPlaces: (q: string, signal?: AbortSignal) =>
    request<Place[]>("/v1/places/search", { query: { q, limit: 8 }, signal }),

  saveProfile: (birth: BirthInput & { is_self?: boolean; relation?: string }) =>
    request<Profile>("/v1/profiles", { method: "POST", body: birth }),

  /**
   * Calculate one system.
   *
   * `locale` is not decoration on a route that returns numbers. Most of a
   * `CalcResult` is arithmetic and identifiers, but the synthesis payload
   * carries the eighteen pole clauses — "works alone, out of sight" ↔ "works
   * in public, in front of people" — and those are prose somebody reads. The
   * backend translates them at the boundary, off this field, and answers
   * English when nobody sends one, which is what every caller here used to
   * get by not knowing the field existed.
   *
   * It is a parameter rather than a default because the browser cannot know
   * it: the language comes from the cookie the provider owns, so the hook
   * with the context in it is the only place that can supply it honestly.
   */
  system: (slug: string, body: Record<string, unknown> = {}, locale?: Locale) =>
    request<CalcResult>(`/v1/systems/${slug}`, {
      method: "POST",
      body: locale ? { ...body, locale } : body,
    }),

  /**
   * The price list, which the landing quotes and nothing here charges.
   *
   * Kept although the web cannot sell: the pricing section names what the
   * ladder costs before anybody downloads anything, and the one rule that has
   * to hold is that the figure it prints is the figure the store will take.
   * That rule survives the checkout being deleted — it is why this endpoint is
   * the only billing call left.
   */
  catalogue: (country?: string) =>
    request<Record<string, unknown>>("/v1/billing/catalogue", { query: { country } }),
};
