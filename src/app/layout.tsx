import type { Metadata, Viewport } from "next";
import { Golos_Text, Playfair_Display } from "next/font/google";
import { LocaleProvider } from "@/lib/i18n/provider";
import { dictionary } from "@/lib/i18n";
import { currentLocale } from "@/lib/locale-server";
import { APPLE_APP_ID } from "@/lib/stores";
import "./globals.css";
import "./screens.css";

const playfair = Playfair_Display({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500"],
  style: ["normal", "italic"],
  variable: "--font-playfair",
  display: "swap",
});

const golos = Golos_Text({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-golos",
  display: "swap",
});

/**
 * The title and description follow the browser's language.
 *
 * Worth doing properly rather than shipping an English title everywhere:
 * this is the text that appears in a shared link and in a search result, and
 * it is the only part of the product a person sees before deciding whether
 * to open it at all.
 */
export async function generateMetadata(): Promise<Metadata> {
  const locale = await currentLocale();
  const { title, description } = dictionary(locale).meta;
  return {
    title,
    description,
    openGraph: { title, description, locale: dictionary(locale).meta.htmlLang },
    /**
     * Safari's native app banner, which is the best-converting thing that can
     * appear on an iPhone visiting this site and costs one meta tag:
     * `<meta name="apple-itunes-app" content="app-id=…">`.
     *
     * Written only when there is an id. An empty or invented `app-id` is not
     * ignored gracefully by every iOS version — some show a banner that opens
     * an App Store page for nothing — and there is no id to write today,
     * because Apple issues one with the app record and the app has not been
     * accepted. `lib/stores.ts` holds it, `stores.test.ts` insists it matches
     * the badge's own listing, and that is the whole of what launch day
     * changes here.
     *
     * The Android equivalent is not a meta tag at all — Chrome reads
     * `related_applications` out of the web manifest — so it lives in
     * `app/manifest.ts` and is gated on the same constants.
     */
    itunes: APPLE_APP_ID ? { appId: APPLE_APP_ID } : undefined,
  };
}

export const viewport: Viewport = {
  themeColor: "#0A0D1C",
  width: "device-width",
  initialScale: 1,
};

// The rule that used to live here — cookie first, then `Accept-Language` — is
// now `lib/locale-server.ts`, because `/support` needs the same answer in a
// page rather than in this layout, and two copies of a precedence rule agree
// only until one of them is edited. It has since grown a fourth source, the
// country the request came from, which ranks last and only speaks when the
// browser asked for a language we do not ship.
//
// Two consequences land here rather than there. `generateMetadata` and this
// component both call it, so the title, the description and `<html lang>` are
// decided by one reading of one request rather than by two that could differ.
//
// And the HTML now varies by a request *header* as well as by the cookie.
// Reading `cookies()` and `headers()` already makes every route through this
// layout dynamic, so Next renders them per request and marks them uncacheable,
// and nothing in the default deployment can serve one visitor's language to the
// next. That is the mechanism, not a promise: anything put in front of the web
// process that caches HTML anyway has to `Vary` on the country header
// alongside `Cookie`. The API side of the same rule is declared rather than
// inferred — see the `Vary` in `alma/api/deps.py`, where the response is a
// plain cacheable GET and the cost of a cache hit across countries is a price
// in the wrong currency.

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await currentLocale();

  return (
    <html lang={dictionary(locale).meta.htmlLang} className={`${playfair.variable} ${golos.variable}`}>
      <body
        style={
          {
            "--serif": `var(--font-playfair), Georgia, serif`,
            "--sans": `var(--font-golos), system-ui, sans-serif`,
          } as React.CSSProperties
        }
      >
        <LocaleProvider initial={locale}>{children}</LocaleProvider>
      </body>
    </html>
  );
}
