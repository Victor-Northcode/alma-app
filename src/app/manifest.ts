import type { MetadataRoute } from "next";

import { PLAY_PACKAGE, PLAY_STORE_URL } from "@/lib/stores";

/**
 * Android's answer to Safari's smart banner.
 *
 * There is no `<meta name="google-play-app">` — that tag was Chrome's for one
 * version in 2013 and has been dead for a decade, and writing it is a common
 * way to believe you have shipped an install prompt that nothing reads. What
 * Chrome actually reads is `related_applications` in the web manifest, together
 * with `prefer_related_applications: true`, which tells it to promote the
 * native app rather than the site. So that is what this route is for, and it is
 * the only reason this file exists.
 *
 * **It is inert until there is a listing.** Both fields are written only when
 * `PLAY_STORE_URL` is filled in. A `related_applications` entry naming a
 * package that is not on Play resolves to nothing, and `prefer_related_
 * applications` with no related application is a preference for a thing that
 * does not exist — see `lib/stores.ts` for why the package id alone is not
 * treated as proof of publication.
 *
 * **No icons, and no `display: standalone`.** Both were considered and both are
 * wrong here. Together with a service worker they are what makes a site
 * installable, and the last thing this handoff should do is offer to add a
 * bookmark to somebody's home screen while telling them the reading happens in
 * the app: two icons, one of which is a website wearing the other's name. There
 * is no service worker either, so the site cannot become installable by
 * accident. The manifest is here to point at the app, not to imitate it.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    // Only the name, which is the same word in all six languages. A manifest is
    // generated once for every visitor rather than per request, so any sentence
    // put here would be one locale's sentence shown to the other five — and it
    // would be a sentence `check-locales.mjs` cannot see, which is precisely how
    // six landings ended up with English FAQ answers.
    name: "Alma",
    short_name: "Alma",
    start_url: "/",
    display: "browser",
    background_color: "#0A0D1C",
    theme_color: "#0A0D1C",
    ...(PLAY_STORE_URL
      ? {
          related_applications: [
            { platform: "play", id: PLAY_PACKAGE, url: PLAY_STORE_URL },
          ],
          prefer_related_applications: true,
        }
      : {}),
  };
}
