"use client";

import Link from "next/link";
import { Star } from "@/components/brand/Star";
import { complianceBadges } from "@/lib/data";
import { useLocale, useT } from "@/lib/i18n/provider";
import { LanguagePicker } from "./LanguagePicker";

/**
 * The footer, rebuilt as a proper masthead rather than a wall of legal text.
 *
 * Left: the mark, the one-line thesis, and the pazl.ai byline. Right: three
 * columns of links grouped by what they are about, so a person looking for the
 * deletion page or the refund policy finds it by category rather than scanning
 * a run-on line. Every label is a link to a page that exists — the compliance
 * links are required and stay — and each column names itself for a screen
 * reader. The same language dropdown from the header sits in the bottom bar,
 * where a person who has decided to look for one looks first.
 */
export function Footer() {
  const t = useT();
  const { locale } = useLocale();

  const columns: Array<[string, Array<{ label: string; href: string }>]> = [
    [
      t.footer.groupLegal,
      [
        { label: t.footer.terms, href: "/terms" },
        { label: t.footer.privacy, href: "/privacy" },
        { label: t.footer.cookies, href: "/privacy#cookies" },
        { label: t.footer.deleteAccount, href: "/delete-account" },
      ],
    ],
    [
      t.footer.groupMoney,
      [
        // Строка одной локали, поэтому литерал с условием, а не ключ
        // словаря: ключ пришлось бы завести на всех семи языках, и шесть
        // из них рекламировали бы путь, которого для их читателя нет
        // (владелец, 31.08.2026: «оплата тбанк была ток у русской версии
        // сайта, у англ и других был эпл»). Рублёвый путь — «/pay»,
        // остальные платят в приложении магазину.
        ...(locale === "ru"
          ? [{ label: "Оплатить картой или СБП", href: "/pay" }]
          : []),
        { label: t.footer.refunds, href: "/refunds" },
        { label: t.footer.subscriptionTerms, href: "/subscription-terms" },
        { label: t.footer.withdrawal, href: "/refunds#withdrawal" },
      ],
    ],
    [
      t.footer.groupCompany,
      [
        { label: t.footer.imprint, href: "/imprint" },
        { label: t.footer.support, href: "/support" },
        { label: t.footer.contact, href: "mailto:hello@pazl.ai" },
      ],
    ],
  ];

  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-top">
          <div className="footer-brand">
            <div className="footer-brand-mark">
              <Star size={24} />
              <span className="footer-brand-name">ALMA</span>
            </div>
            <p className="footer-brand-tag">{t.hero.overline}</p>
            <a
              className="footer-made"
              href="https://pazl.ai"
              target="_blank"
              rel="noreferrer"
            >
              made by pazl.ai
            </a>
          </div>

          <div className="footer-cols">
            {columns.map(([group, links]) => (
              <nav key={group} className="footer-col" aria-label={group}>
                <h4 className="footer-col-title">{group}</h4>
                <ul className="footer-col-links">
                  {links.map((l) => (
                    <li key={l.href}>
                      {l.href.startsWith("mailto:") ? (
                        <a href={l.href}>{l.label}</a>
                      ) : (
                        <Link href={l.href}>{l.label}</Link>
                      )}
                    </li>
                  ))}
                </ul>
              </nav>
            ))}
          </div>
        </div>

        <div className="footer-bar">
          <div className="footer-badges">
            <span className="footer-badge">16+</span>
            {complianceBadges.map((b) => (
              <span key={b} className="footer-badge">
                {b}
              </span>
            ))}
          </div>
          <LanguagePicker />
        </div>

        <p className="footer-fine">
          Pazl LLC · Wyoming, USA · <a href="mailto:hello@pazl.ai">hello@pazl.ai</a>
          <br />
          {t.footer.disclaimer} {t.footer.rights}
        </p>
      </div>
    </footer>
  );
}
