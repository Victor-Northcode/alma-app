"use client";

/**
 * React hooks over the API client.
 *
 * There were nine of these and there are two, which is the whole story of this
 * phase: seven of them fed cabinet screens that no longer exist. What survives
 * is what the journey asks for — the place index while somebody types, and a
 * calculated system for the portrait.
 *
 * The fixture fallback went with them, and that is worth being explicit about.
 * `useRequest` used to answer an unreachable backend with the reference data in
 * `data.ts` and flag it through `source: "fixture"`, so that the cabinet could
 * be reviewed with nothing running behind it. Neither surviving caller ever
 * used it: a place list invented in the browser would put a coordinate under a
 * town that is not there, and the portrait is the screen whose entire argument
 * is that every line on it was calculated. So an unreachable backend now
 * produces an absent line, which is what both callers already did with one.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { Identity } from "./carry";
import { useLocale } from "./i18n/provider";
import {
  api,
  isOk,
  readToken,
  type CalcResult,
  type Failure,
  type Place,
  type Result,
} from "./api";

export type Source = "live" | "fixture";

interface State<T> {
  data: T | null;
  error: Failure | null;
  loading: boolean;
}

const idle = <T,>(): State<T> => ({ data: null, error: null, loading: true });

/**
 * Run a request once on mount.
 *
 * `enabled: false` parks the hook: no request, no spinner, no error. That is
 * a third state and it needs to exist — a screen that should not ask yet
 * (no birth data saved) would otherwise have to choose between a request that
 * can only fail and a spinner that never resolves.
 */
function useRequest<T>(
  run: () => Promise<Result<T>>,
  deps: unknown[] = [],
  enabled = true,
): State<T> & { reload: () => void } {
  const [state, setState] = useState<State<T>>(idle<T>);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setState({ data: null, error: null, loading: false });
      return;
    }
    let live = true;
    setState((previous) => ({ ...previous, loading: true }));

    run().then((result) => {
      if (!live) return;
      setState(
        isOk(result)
          ? { data: result.data, error: null, loading: false }
          : { data: null, error: result, loading: false },
      );
    });

    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce, enabled]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { ...state, reload };
}

/* ── a calculated system ───────────────────────────────────────────────── */

/**
 * One calculated system.
 *
 * `enabled` exists so a screen can decline to ask: a request that can only
 * fail is both noise in the logs and a spinner somebody watches for nothing.
 * Disabled keeps the hook in the same position in the render (hooks may not be
 * called conditionally) while making no request.
 */
export function useSystem(
  slug: string,
  body: Record<string, unknown> = {},
  enabled = true,
) {
  // The reader's language, from the same context every visible string on the
  // page is rendered from. It goes on the request because the backend has one
  // route whose result contains prose — the synthesis poles, which are the
  // only strings in a `CalcResult` that are neither a number nor an
  // identifier — and it translates them off this field or answers English.
  // Threading it here rather than at each call site means a screen cannot ask
  // for a system in a language other than the one it is being read in.
  const { locale } = useLocale();
  const serialised = JSON.stringify(body);
  return useRequest<CalcResult>(
    () => api.system(slug, JSON.parse(serialised), locale),
    [slug, serialised, locale],
    enabled,
  );
}

/* ── who this browser is ───────────────────────────────────────────────── */

/**
 * Whether anything in this browser is attached to an address.
 *
 * `unknown` is a real answer and not a loading state to be styled away. The
 * handoff makes a promise about whether a chart survives the walk from this
 * browser to a phone, and `lib/carry.ts` — which owns that promise — has a
 * sentence for the case where we could not find out. Guessing "guest" instead
 * would tell somebody who signed in thirty seconds ago to type their birth date
 * again, and guessing "attached" would be the lie.
 */
export function useIdentity(): Identity {
  const [identity, setIdentity] = useState<Identity>({ state: "unknown" });

  useEffect(() => {
    // No token means nobody has done anything here yet — no birth saved, no
    // sign-in — and asking would mint a guest row for a page view. That is a
    // decision `track.ts` makes on purpose for the top of the funnel; it is not
    // one a screen should make on its way out of the product.
    if (!readToken()) {
      setIdentity({ state: "guest" });
      return;
    }

    let live = true;
    api.session().then((result) => {
      if (!live) return;
      if (!isOk(result)) return; // stays `unknown`, which is the honest sentence
      setIdentity(
        result.data.is_guest
          ? { state: "guest" }
          : { state: "attached", email: result.data.email },
      );
    });

    return () => {
      live = false;
    };
  }, []);

  return identity;
}

/* ── place search ──────────────────────────────────────────────────────── */

/**
 * Typeahead over the place index.
 *
 * Debounced, and every superseded request is aborted. Without the abort a
 * slow response for "mil" can land after the fast one for "milan" and
 * replace the right answer with a stale one — which reads as the search
 * being broken rather than slow.
 */
export function usePlaceSearch(query: string, { delay = 180 } = {}) {
  const [places, setPlaces] = useState<Place[]>([]);
  const [searching, setSearching] = useState(false);
  const [failed, setFailed] = useState(false);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    const trimmed = query.trim();
    controller.current?.abort();

    if (trimmed.length < 2) {
      setPlaces([]);
      setSearching(false);
      return;
    }

    setSearching(true);
    const next = new AbortController();
    controller.current = next;

    const timer = setTimeout(() => {
      api.searchPlaces(trimmed, next.signal).then((result) => {
        if (next.signal.aborted) return;
        setSearching(false);
        if (isOk(result)) {
          setPlaces(result.data);
          setFailed(false);
        } else {
          setPlaces([]);
          // Offline and "no such place" look the same to the person typing,
          // and the interface says the same thing about both.
          setFailed(true);
        }
      });
    }, delay);

    return () => {
      clearTimeout(timer);
      next.abort();
    };
  }, [query, delay]);

  return { places, searching, failed };
}
