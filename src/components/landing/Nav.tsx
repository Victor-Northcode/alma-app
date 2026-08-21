"use client";

import { useEffect, useState } from "react";
import { Star, Wordmark } from "@/components/brand/Star";
import { useLocale } from "@/lib/i18n/provider";
import { LanguagePicker } from "./LanguagePicker";

/** Landing nav is opaque #090C1A — never translucent over content. */
export function Nav() {
  const { t } = useLocale();
  const [menu, setMenu] = useState(false);

  const sheet: Array<[string, string]> = [
    ["#what", t.nav.what],
    ["#eight", t.nav.eight],
    ["#faq", t.nav.faq],
  ];

  useEffect(() => {
    if (!menu) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setMenu(false);
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [menu]);

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 40,
        background: "var(--night-850)",
        borderBottom: "1px solid var(--hairline-gold)",
      }}
    >
      <div className="nav-inner">
        <a href="#top" aria-label="Alma — home">
          <span className="nav-mark-small">
            <Wordmark size={15.5} starSize={21} tracking="0.32em" />
          </span>
          <span className="nav-mark-full">
            <Wordmark size={19} starSize={26} />
          </span>
        </a>

        <div className="nav-anchors">
          <a href="#what">{t.nav.what}</a>
          <a href="#eight">{t.nav.eight}</a>
          <a href="#faq">{t.nav.faq}</a>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* The language dropdown lives in the bar at every width now — one
              compact control, no sheet-under-the-header, no second copy to keep
              in step. */}
          <LanguagePicker />
          {/* The website's one action is the app. It scrolls to the store
              hand-off at the foot of the page. Below 900px it is not rendered
              and the sheet carries it instead. */}
          <a className="nav-cta" href="#get-app">
            {t.cta.getApp}
          </a>
          <button
            type="button"
            className="nav-burger"
            aria-label={menu ? t.nav.closeMenu : t.nav.openMenu}
            aria-expanded={menu}
            aria-controls="nav-sheet"
            onClick={() => setMenu((m) => !m)}
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </div>

      {/* the sheet unrolls on a grid row so the height animates without a fixed value */}
      <div id="nav-sheet" className="nav-sheet" data-open={menu} aria-hidden={!menu}>
        <div className="nav-sheet-inner">
          <a
            className="btn btn-gold nav-sheet-cta"
            href="#get-app"
            tabIndex={menu ? 0 : -1}
            onClick={() => setMenu(false)}
          >
            {t.cta.getApp}
          </a>
          {sheet.map(([href, label]) => (
            <a key={href} href={href} onClick={() => setMenu(false)} tabIndex={menu ? 0 : -1}>
              {label}
              <span className="nav-sheet-arrow" aria-hidden>
                →
              </span>
            </a>
          ))}
        </div>
      </div>
    </nav>
  );
}

export function FooterMark() {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 11 }}>
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
    </span>
  );
}
