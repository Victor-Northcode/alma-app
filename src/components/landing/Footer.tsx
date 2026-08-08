"use client";

import Link from "next/link";
import { Star } from "@/components/brand/Star";
import { complianceBadges, legalLinks } from "@/lib/data";
import type { Dictionary } from "@/lib/i18n";
import { useT } from "@/lib/i18n/provider";
import { LanguagePicker } from "./LanguagePicker";

/**
 * The legal footer, in the language the visitor is reading.
 *
 * It was a server component with every sentence hardcoded in English, so a
 * German, French, Italian, Spanish or Brazilian visitor met the pre-contractual
 * notices in a language they had not been sold in. That is not a style problem:
 * France's language rules, Italy's Codice del consumo art. 9, Brazil's CDC
 * art. 46 and Mexico's Spanish requirement all treat a term the consumer could
 * not understand as one that does not bind them. It also put the strings
 * somewhere `check-locales.mjs` cannot see, which is why nobody noticed.
 *
 * `legalLinks` stays the authority on **where** each link goes — `legal-truth`
 * asserts every href resolves to a page or an anchor that exists — and the
 * dictionary supplies **what it is called**. Keeping the two apart means a
 * translation can never quietly repoint a link.
 */
function labelFor(href: string, t: Dictionary, fallback: string): string {
  const named: Record<string, string> = {
    "/terms": t.footer.terms,
    "/privacy": t.footer.privacy,
    "/privacy#cookies": t.footer.cookies,
    "/refunds": t.footer.refunds,
    "/subscription-terms": t.footer.subscriptionTerms,
    "/refunds#withdrawal": t.footer.withdrawal,
    "/privacy#choices": t.footer.choices,
    "/imprint": t.footer.imprint,
    "/support": t.footer.support,
    "/delete-account": t.footer.deleteAccount,
    "mailto:hello@pazl.ai": t.footer.contact,
  };
  // The two links that share `/privacy#choices` need different words, and the
  // second is a phrase California asks for verbatim rather than a page name.
  if (fallback.startsWith("Do Not Sell")) return t.footer.doNotSell;
  return named[href] ?? fallback;
}

export function Footer() {
  const t = useT();

  /**
   * The three rows the mobile footer shows instead of the full legal wall.
   *
   * Same principle as the wall above it: every word in the right-hand column is
   * a link to a document that exists. The rows used to read "Terms · Privacy ·
   * Refunds" and "EU · UK · KR · JP" as plain text, which looked like a legal
   * footer without being one.
   */
  const mobileRows: Array<[string, Array<{ label: string; href: string }>]> = [
    [
      t.footer.groupLegal,
      [
        { label: t.footer.terms, href: "/terms" },
        { label: t.footer.privacy, href: "/privacy" },
        // Play asks for the deletion page to be readily discoverable, and the
        // phone is where the person who wants it is standing.
        { label: t.footer.deleteAccount, href: "/delete-account" },
      ],
    ],
    [
      t.footer.groupMoney,
      [
        { label: t.footer.refunds, href: "/refunds" },
        { label: t.footer.subscriptionTerms, href: "/subscription-terms" },
      ],
    ],
    [
      t.footer.groupCompany,
      [
        { label: t.footer.imprint, href: "/imprint" },
        { label: t.footer.support, href: "/support" },
      ],
    ],
  ];

  return (
    <footer className="footer">
      <div className="footer-inner">
        {/* mobile: four rows, hairline-separated */}
        <div className="only-mobile-block">
          <div style={{ display: "flex", alignItems: "center", gap: 11, marginBottom: 22 }}>
            <Star size={19} />
            <span
              style={{
                fontFamily: "var(--serif)",
                fontSize: 14,
                letterSpacing: "0.32em",
                color: "var(--ink-light)",
                paddingLeft: "0.32em",
              }}
            >
              ALMA
            </span>
            <span style={{ flex: 1, height: 1, background: "rgba(201,174,107,.24)" }} />
            <span style={{ fontSize: 12, color: "var(--muted-3)" }}>16+</span>
          </div>
          {mobileRows.map(([group, links]) => (
            <div key={group} className="footer-row">
              <span style={{ fontSize: 14.5, color: "rgba(237,231,218,.82)" }}>{group}</span>
              <span style={{ fontSize: 13, display: "flex", gap: 10 }}>
                {links.map((l) => (
                  <Link key={l.href} href={l.href} style={{ color: "var(--muted-3)" }}>
                    {l.label}
                  </Link>
                ))}
              </span>
            </div>
          ))}
          <div className="footer-row" style={{ borderBottom: "1px solid var(--hairline)" }}>
            <span style={{ fontSize: 14.5, color: "rgba(237,231,218,.82)" }}>
              {t.footer.contact}
            </span>
            <a href="mailto:hello@pazl.ai" style={{ fontSize: 13 }}>
              hello@pazl.ai
            </a>
          </div>
        </div>

        {/* tablet & desktop: the full legal wall */}
        <div className="from-tablet-block">
          <div style={{ display: "flex", alignItems: "center", gap: 11, marginBottom: 26 }}>
            <Star size={22} />
            <span
              style={{
                fontFamily: "var(--serif)",
                fontSize: 16,
                letterSpacing: "0.34em",
                color: "var(--ink-light)",
                paddingLeft: "0.34em",
              }}
            >
              ALMA
            </span>
          </div>
          <div className="footer-links">
            {legalLinks.map((l) =>
              l.href.startsWith("mailto:") ? (
                <a key={l.label} href={l.href}>
                  {labelFor(l.href, t, l.label)}
                </a>
              ) : (
                <Link key={l.label} href={l.href}>
                  {labelFor(l.href, t, l.label)}
                </Link>
              ),
            )}
          </div>
          <div className="footer-badges">
            {complianceBadges.map((b) => (
              <span key={b} className="footer-badge">
                {b}
              </span>
            ))}
          </div>
        </div>

        {/* The conventional home for a language picker, and conventional is
            the whole argument: it is where a person who has decided to look
            for one looks first, at either width, without being taught. One
            copy for both layouts rather than one inside each block — two
            pickers would be two tab stops and two things to keep in step. */}
        <div className="footer-lang">
          <LanguagePicker />
        </div>

        <div className="footer-fine">
          Pazl LLC · Wyoming, USA · <a href="mailto:hello@pazl.ai">hello@pazl.ai</a>
          <br />
          <span className="from-tablet">
            <Link href="/subscription-terms">{t.footer.payments}</Link>
            <br />
          </span>
          {t.footer.disclaimer}
          <br />
          <span className="from-tablet">
            {t.footer.performance}{" "}
            <Link href="/refunds#withdrawal">{t.footer.performanceLink}</Link>.
            <br />
          </span>
          {t.footer.rights}
        </div>
      </div>
    </footer>
  );
}
