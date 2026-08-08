/**
 * Where the app can be got, once there is somewhere to get it.
 *
 * Every constant below that names a *listing* is empty, and that is the honest
 * state of the world today: neither build has been accepted by a store, so
 * neither has a listing, neither has a URL and Apple has not issued an app id.
 * A badge pointing at a search page, at a placeholder id, or at `pazl.ai` would
 * be a link that looks like a download and is not one — which is the exact
 * species of small lie this product is built against.
 *
 * So the handoff renders a plate that says "coming to the App Store" while
 * these are empty, and the store's own badge the moment one is filled in. That
 * is the whole of the switch: paste the listing URL here, deploy, done. No
 * feature flag, no environment variable, no second place to remember — an
 * environment variable was the alternative and it was rejected because the
 * value is a public, permanent fact about the product rather than a per-
 * deployment secret, and because a missing variable in production would fail
 * silently into the same empty state we are already handling here.
 *
 * `alma.pazl.ai` and `api.pazl.ai` are NXDOMAIN as of today and are compiled
 * into both shipped mobile builds; only the apex answers. That is not this
 * file's problem to solve, but it is the reason nothing here tries to be clever
 * about deep links: a universal link into an app that is not installed, on a
 * host that does not resolve, is two failures wearing one URL.
 *
 * ── LAUNCH DAY ────────────────────────────────────────────────────────────
 * Per store, two things, and `stores.test.ts` fails the build if you do one
 * without the other:
 *
 *   1. the listing URL below (and, for Apple, `APPLE_APP_ID` with it — the
 *      badge and the Safari banner are the same launch);
 *   2. the store's **own** badge artwork, downloaded from the guidelines and
 *      committed at the path named below. Both Apple and Google require their
 *      supplied artwork and forbid redrawing it, so it is not in this
 *      repository yet: shipping a hand-made lookalike would be a trademark
 *      problem on top of a design one, and shipping the real artwork next to a
 *      badge that cannot be tapped is the dead badge this file exists to avoid.
 *      Apple: the **black** badge, because a second platform's badge is beside
 *      it. Google: the SVG, unmodified, uncoloured.
 */

/** Apple's listing, e.g. `https://apps.apple.com/app/id0000000000`. */
// Annotated `string` rather than inferred: without it TypeScript narrows an
// empty constant to the literal type `""`, and every `if (!url)` in the
// handoff becomes a branch it can prove is always taken — which is a compile
// error in the test and, worse, an invitation to delete the empty case.
export const APP_STORE_URL: string = "";

/** Google's listing, e.g. `https://play.google.com/store/apps/details?id=ai.pazl.alma`. */
export const PLAY_STORE_URL: string = "";

/**
 * The numeric App Store id, which is what Safari's native app banner runs on.
 *
 * Separate from the URL above because it is consumed somewhere else entirely —
 * a `<meta name="apple-itunes-app">` in the document head, written by
 * `app/layout.tsx` — and because the two go stale in different ways. Apple
 * issues it when the app record is created, which can be well before the app is
 * approved; the banner is still not allowed to appear until the listing is
 * live, which is why the meta tag reads this and the test insists the two agree.
 */
export const APPLE_APP_ID: string = "";

/**
 * The Android application id, which is known today and always has been.
 *
 * `mobile/android/app/build.gradle.kts` declares it, and it is deliberately
 * *not* used to synthesise a Play URL: `play.google.com/store/apps/details?id=…`
 * answers 404 for an unpublished package, so deriving the link from the package
 * would produce a badge that is live-looking and broken from the first deploy.
 * It is used for the web manifest's `related_applications`, which is Chrome's
 * equivalent of Safari's banner and is inert until a listing exists.
 */
export const PLAY_PACKAGE = "ai.pazl.alma";

/**
 * Where each store's own badge artwork is expected to live.
 *
 * Paths rather than imported assets so that the day the artwork lands is a
 * `git add` in `public/` and nothing else. Neither file is committed yet — see
 * the launch-day note above — and `stores.test.ts` refuses a listing URL whose
 * artwork is missing, so the first deploy after publishing cannot ship a broken
 * image where the badge should be.
 */
export const APP_STORE_BADGE = "/badges/app-store.svg";
export const PLAY_STORE_BADGE = "/badges/google-play.svg";

/**
 * The hosts a store link is allowed to be on.
 *
 * Exported for the test rather than used at runtime: the failure being guarded
 * against is somebody pasting a marketing page, a shortener or a TestFlight
 * invite into the constants above, all three of which read as "the app" in a
 * review and none of which is the store.
 */
export const STORE_HOSTS = {
  apple: "https://apps.apple.com/",
  google: "https://play.google.com/",
} as const;
