import { cookies, headers } from "next/headers";
import { countryFromHeaders } from "./country";
import { LOCALE_STORAGE_KEY, resolveLocale, type Locale } from "./i18n";

/**
 * What this request should be rendered in, decided on the server.
 *
 * This rule lived inside `app/layout.tsx` as a private function, which was fine
 * while the root layout was the only thing that needed it. `/support` needs it
 * too, and needs it in a *page* rather than in a provider: that page is opened
 * cold by an App Review employee, in a browser, and the translated sentences
 * have to be in the HTML that arrives rather than painted in afterwards by
 * React. Resolving the locale in a client component would have been right for a
 * person and wrong for the one reader the page exists to satisfy.
 *
 * Two callers, one rule, one file — the alternative is two copies that agree
 * today. The precedence itself is `resolveLocale`, in `lib/i18n`, because the
 * client half of the application has to reach the same answer for the same
 * request or hydration discards the tree.
 *
 * ── the third source, and why it is third ─────────────────────────────────
 * The country the request came from, read off whichever edge is in front of
 * this process. It ranks below `Accept-Language` on purpose and the owner's own
 * example is why: a browser asking for `en-GB` from a Spanish address is a
 * Briton in Spain, and they want English. What the country is for is the
 * request that asked for nothing we ship — a phone set to Arabic, in Madrid,
 * which used to be handed English because "no header" and "no language of yours
 * that we have" were the same answer.
 *
 * Nothing about this changes what the *client* does, and that is deliberate.
 * The browser never sees the country and never re-derives the language; it
 * takes the server's answer through `LocaleProvider`'s `initial` and only ever
 * overrides it from the cookie, which the server read too. So there is no path
 * where SSR and hydration can disagree about a country neither of them can
 * measure twice.
 *
 * ── why this is not in `src/lib/i18n/` ────────────────────────────────────
 * `scripts/check-locales.mjs` enumerates every `.ts` file in that directory and
 * treats each one as a language. A helper dropped in beside the dictionaries
 * would be audited as a seventh locale, find no keys, and quietly change the
 * script's closing line from "5 translated" to "6" — a number in a build log
 * that is not true. The import below is the whole cost of keeping that honest.
 */
export async function currentLocale(): Promise<Locale> {
  const jar = await cookies();
  const head = await headers();
  return resolveLocale({
    explicit: jar.get(LOCALE_STORAGE_KEY)?.value,
    browser: head.get("accept-language"),
    country: countryFromHeaders(head),
  });
}
