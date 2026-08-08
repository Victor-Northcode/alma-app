"use client";

/**
 * The locale, as React sees it.
 *
 * Deliberately not URL-routed. `/de/` on every path would mean every shared
 * link carries a language the recipient may not read, and the storefront is
 * one page that people arrive at from everywhere. The choice comes from the
 * cookie, and from `Accept-Language` when there is no cookie.
 *
 * `initial` comes from the server, which has already read that cookie — so
 * the first paint is in the right language and the first effect below is only
 * a safety net for the case where the cookie was written by another tab.
 * Reading the preference during render instead would produce markup the
 * server never generated, and React would throw the whole tree away.
 *
 * ── `setLocale`, and why it is three statements rather than one ───────────
 * There was a `setLocale` here once. It wrote a preference for a screen that
 * had been deleted and PATCHed `/api/account`, a route this application has
 * never had — a switch with no lever attached to a request to a 404 — so it
 * went, and the website was left with no way to change language at all. This
 * is its replacement, and the shape of it is decided entirely by the fact that
 * the *server* resolves the locale:
 *
 *  1. **Write the cookie.** It is the only client preference SSR can read, and
 *     everything below depends on the server seeing it. `lib/locale-choice.ts`
 *     owns what that cookie has to say.
 *  2. **Move the React state immediately.** This is what stops the flash. The
 *     whole landing is client-rendered from this context, so the new language
 *     is on screen in the same frame as the tap — before any request goes out,
 *     and regardless of how long the server takes. Waiting for the refresh
 *     instead would show the old language for a round trip on every switch.
 *  3. **Ask the server to render again.** `router.refresh()` and not
 *     `location.reload()`, and the difference is the whole requirement: a
 *     reload throws away every client component's state, which here means the
 *     date, name, birth time and place somebody has already typed into the
 *     journey. A refresh re-runs the server components with the new cookie and
 *     reconciles them into the tree that is already mounted, so `<html lang>`,
 *     the document title and any server-rendered page — the legal routes,
 *     `/support` — catch up while the overlay stays exactly where it was.
 *
 * The state is not resynced from `initial` afterwards. A refreshed layout does
 * pass the new value down, but treating that prop as authoritative would mean
 * a slow or failed refresh could drag the interface back to the language the
 * person just left.
 */

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  DEFAULT_LOCALE,
  dictionary,
  storedLocale,
  type Dictionary,
  type Locale,
} from ".";
import { localeCookie } from "../locale-choice";

interface LocaleValue {
  locale: Locale;
  t: Dictionary;
  /** Remember a choice and render the whole page in it. */
  setLocale: (next: Locale) => void;
}

const LocaleContext = createContext<LocaleValue>({
  locale: DEFAULT_LOCALE,
  t: dictionary(DEFAULT_LOCALE),
  setLocale: () => {},
});

export function LocaleProvider({
  initial = DEFAULT_LOCALE,
  children,
}: {
  initial?: Locale;
  children: ReactNode;
}) {
  const [locale, setLocaleState] = useState<Locale>(initial);
  const router = useRouter();

  useEffect(() => {
    const remembered = storedLocale();
    if (remembered && remembered !== locale) setLocaleState(remembered);
    // Runs once: after this the choice only changes through `setLocale`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    document.documentElement.lang = dictionary(locale).meta.htmlLang;
  }, [locale]);

  const setLocale = useCallback(
    (next: Locale) => {
      // Choosing the language you are already reading is a no-op rather than a
      // refresh. It is the likeliest tap in the picker — the current option is
      // the one a person's eye lands on — and spending a server round trip and
      // a re-render on it would make the control feel broken.
      if (next === locale) return;
      // `location.protocol` rather than a build-time flag: the same bundle is
      // served over http on a developer's machine and https everywhere else,
      // and a `Secure` cookie is silently dropped by the first of those.
      document.cookie = localeCookie(next, {
        secure: window.location.protocol === "https:",
      });
      setLocaleState(next);
      router.refresh();
    },
    [locale, router],
  );

  const value = useMemo(
    () => ({ locale, t: dictionary(locale), setLocale }),
    [locale, setLocale],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

/** Everything a component needs to render in the current language. */
export function useLocale(): LocaleValue {
  return useContext(LocaleContext);
}

/** The dictionary alone — the common case. */
export function useT(): Dictionary {
  return useContext(LocaleContext).t;
}
