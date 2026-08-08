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
const nextConfig: NextConfig = {
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  distDir: process.env.ALMA_DIST_DIR ?? ".next",
};

export default nextConfig;
