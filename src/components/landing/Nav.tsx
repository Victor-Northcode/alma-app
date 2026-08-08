"use client";

import { useEffect, useState } from "react";
import { Star, Wordmark } from "@/components/brand/Star";
import { journeyCta } from "@/lib/cta";
import { useLocale } from "@/lib/i18n/provider";
import { useJourney } from "@/lib/journey-store";
import { languageName, languageOptions } from "@/lib/locale-choice";
import { LanguagePicker } from "./LanguagePicker";

/** Landing nav is opaque #090C1A — never translucent over content. */
export function Nav() {
  const { start } = useJourney();
  const { locale, t } = useLocale();
  const [menu, setMenu] = useState(false);
  // The tag for the toggle's own word, so a screen reader says "Deutsch" in
  // German rather than sounding it out in the voice of the surrounding page —
  // the same rule each option in the picker follows.
  const languageHtmlLang =
    languageOptions().find((option) => option.locale === locale)?.htmlLang ?? "en";

  // Built from the dictionary rather than a module constant: a constant is
  // evaluated once at import, which would freeze the menu in whatever
  // language the first render happened to use.
  const sheet: Array<[string, string]> = [
    ["#what", t.nav.what],
    ["#eight", t.nav.eight],
    ["#pricing", t.nav.pricing],
    ["#faq", t.nav.faq],
    ["/sign-in", t.nav.signIn],
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
        {/* The wordmark swaps size at the same width the bar changes shape.

            It used to swap at 700 on the shared `only-mobile` / `from-tablet`
            utilities while the bar itself changed at 900, so between 700 and
            899 the burger layout carried the larger wordmark. It fitted — but
            two numbers describing one bar are two numbers that drift apart the
            next time either is touched, and the whole reason 900 exists is that
            somebody measured this bar. `.nav-mark-*` are local to it. */}
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
          <a href="#pricing">{t.nav.pricing}</a>
          <a href="#faq">{t.nav.faq}</a>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <a href="/sign-in" className="nav-signin">
            {t.nav.signIn}
          </a>
          {/* It said "Sign up" — "Crear cuenta", "Criar conta", literally
              *create an account*, in two of the six — and no account is
              created anywhere on this website: the cabinet is gone and the
              journey's account step is optional and skippable. What the button
              does is open the free reading, so that is what it says now, in the
              same words as the other four controls that open the same thing.

              Below 900px this one is not rendered and the sheet's copy is; the
              note on `.nav-cta` in `screens.css` has the measurements. */}
          <button type="button" className="nav-cta" onClick={() => start("nav")}>
            {journeyCta(t)}
          </button>
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
          {/* The desktop half of the burger, and the reason it exists.

              At 900 and up the sheet was `display: none`, so the *only*
              language picker on the page was the footer's. Measured at 1280:
              it sits at page Y 5056 of a 5335 px document — 5.6 viewport
              heights down, the 31st of 39 tab stops — and the bar carried no
              language affordance at all. The argument written into this file
              for putting a second picker in the mobile sheet ("the footer is
              4,000 px below somebody who realised on the first screen that they
              cannot read the page") is exactly as true on a laptop, where there
              was no second picker. A Briton in Spain on a desktop had to scroll
              the whole Spanish page, or tab past thirty controls, to find the
              way out; that is not findable, it is only discoverable by somebody
              who already believes the control is there.

              The full row does not fit in the bar, and that was measured rather
              than assumed: at 1280 in German the bar has 320 px of slack and
              the six endonyms need 518. So the bar gets the one word it has
              room for — the language being read, in its own language — and it
              opens the same sheet the burger opens, which already holds the
              picker. One interaction model at every width, no popup to
              position, no plate, no chevron, and no second component.

              A separate element from the burger rather than one button with two
              skins: the accessible name has to differ (a burger says "menu", a
              language toggle says "language"), and a `display: none` element is
              not focusable, so only one of the two is ever in the tab order. */}
          {/* The name contains the visible word, and says which language it is.

              `aria-label={t.language.label}` alone *replaced* the button's text
              instead of describing it: measured at 1280 in German the button
              reads "Deutsch" and the accessibility tree said `button
              "Sprache"`. WCAG 2.5.3 Label in Name, straightforwardly failed — a
              speech-control user saying "click Deutsch" gets nothing at all,
              because the only name the machine has is a word that is not on the
              button.

              It also cost this control the one thing it is best placed to say.
              At ≥940 this is the only language affordance above the fold, and it
              was the single control in the set that never announced which
              language was currently active: the rows inside the sheet mark the
              current one with `aria-current`, but a screen-reader user out here
              heard "Language, collapsed" and had to open the sheet to find out
              where they were. "Sprache: Deutsch" answers both at once and still
              shows the one word the bar has room for. */}
          <button
            type="button"
            className="nav-lang-toggle"
            lang={languageHtmlLang}
            aria-label={`${t.language.label}: ${languageName(locale)}`}
            aria-expanded={menu}
            aria-controls="nav-sheet"
            onClick={() => setMenu((m) => !m)}
          >
            {languageName(locale)}
          </button>
        </div>
      </div>

      {/* the sheet unrolls on a grid row so the height animates without a fixed value */}
      <div id="nav-sheet" className="nav-sheet" data-open={menu} aria-hidden={!menu}>
        <div className="nav-sheet-inner">
          {/* The same door as the pill in the bar, at every width the bar is
              too narrow to hold a sentence in. First row rather than last: it
              is the primary action, and it is where a thumb already is after
              tapping the burger. The sheet closes behind it so the overlay
              does not rise over a menu left hanging open. */}
          <button
            type="button"
            className="btn btn-gold nav-sheet-cta"
            tabIndex={menu ? 0 : -1}
            onClick={() => {
              setMenu(false);
              start("nav");
            }}
          >
            {journeyCta(t)}
          </button>
          {sheet.map(([href, label]) => (
            <a key={href} href={href} onClick={() => setMenu(false)} tabIndex={menu ? 0 : -1}>
              {label}
              <span className="nav-sheet-arrow" aria-hidden>
                →
              </span>
            </a>
          ))}
          {/* The second home of the picker, and the one that matters on a
              phone. The footer is the conventional place for it and it is
              there — but the footer is the *bottom* of a page this long, and
              the person who needs this control has realised on the first
              screen that they cannot read the page. Asking them to scroll
              through nine sections of a language they do not speak to reach
              the fix is asking them to leave. Two taps from the top instead.

              `focusable` follows the sheet: collapsed, it is `aria-hidden`,
              and six tabbable buttons inside that are a keyboard trap. */}
          <div className="nav-sheet-lang">
            <LanguagePicker focusable={menu} />
          </div>
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
