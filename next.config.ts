import type { NextConfig } from "next";

/**
 * `distDir` is a variable so that a verification build cannot fight the dev
 * server.
 *
 * Both `next dev` and `next build` own `.next`, and running one while the
 * other is live leaves a half-written manifest behind — the failure surfaces
 * minutes later as `ENOENT routes-manifest.json`, or as a page that suddenly
 * "cannot find module", and it looks like a code fault rather than two
 * processes sharing a directory. `npm run verify` therefore builds into
 * `.next-verify` and leaves the running dev server alone.
 */

/**
 * The origin the browser is allowed to talk to for the API.
 *
 * `connect-src` in the CSP below has to name it, or every call to the backend
 * is blocked — and the backend is a *different* origin in production
 * (`NEXT_PUBLIC_ALMA_API`), so `'self'` is not enough. Read here at build time,
 * the same value the client reads in `src/lib/api.ts`. When it is unset we fall
 * back to allowing http/https connections rather than blocking them, because a
 * page that cannot reach its API is worse than a slightly wider connect-src on
 * a build nobody configured.
 */
const apiOrigin = (() => {
  const raw = process.env.NEXT_PUBLIC_ALMA_API?.replace(/\/$/, "");
  if (!raw) return "http: https:";
  try {
    return new URL(raw).origin;
  } catch {
    return "http: https:";
  }
})();

/**
 * A conservative Content-Security-Policy.
 *
 * The load-bearing directive is `frame-ancestors 'none'` — with no framing
 * headers at all the site could be dropped into an attacker's iframe and
 * clickjacked. `object-src 'none'` and `base-uri 'self'` close the other two
 * classic holes. `script-src`/`style-src` keep `'unsafe-inline'` because Next's
 * runtime injects inline bootstrap script and styled markup; tightening those
 * to nonces is a larger change than this audit fix and would need every inline
 * site rewritten. Google Sign-In (`SignInPanel`) loads a script and an iframe
 * from `accounts.google.com`, so those are allowed explicitly.
 */
const contentSecurityPolicy = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://apis.google.com",
  "style-src 'self' 'unsafe-inline'",
  // The API origin by name, not only `https:`: the pay page (`/pay`) draws
  // the systems' plates straight off the backend (`/static/plates/…`), and a
  // deployment whose API speaks plain http — every local stand — rendered
  // eight blank rectangles with no error anywhere but the CSP report.
  `img-src 'self' data: blob: https: ${apiOrigin}`,
  "font-src 'self' data:",
  `connect-src 'self' ${apiOrigin}`,
  "frame-src https://accounts.google.com",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

/**
 * The baseline security headers, absent until now (`curl -sD -` returned none).
 *
 * Every one of these was missing, which is why they are added as a set rather
 * than one at a time: clickjacking (no frame protection), MIME-sniffing (no
 * nosniff), referrer leakage of the magic-link token in `/sign-in?token=…`
 * (default referrer policy), and no HSTS on the https origin. `Referrer-Policy:
 * strict-origin-when-cross-origin` is the one BUG-010 leans on so a sign-in URL
 * cannot carry its token to a third party.
 */
const securityHeaders = [
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  distDir: process.env.ALMA_DIST_DIR ?? ".next",
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
