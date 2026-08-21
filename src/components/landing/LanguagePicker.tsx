"use client";

/**
 * The way out of a language you cannot read — a compact dropdown at the top of
 * the page.
 *
 * It used to be a row of six words, which is honest but wide; the bar has room
 * for one. So the closed control shows the language being read and a caret, and
 * the open panel is the six endonyms, each in its own script. The hard parts a
 * `<select>` would hide are handled in the open: it closes on an outside click
 * or Escape, `aria-expanded` tracks the panel, `role="listbox"` names the
 * options, `aria-selected` marks the current one, and every option carries its
 * own `lang` so "Français" is pronounced in French rather than sounded out by
 * an English voice. The live region still speaks the change, because the one
 * person this exists for could not read the page they were on.
 *
 * `focusable` follows a collapsed container (the mobile sheet) so the options
 * are never a keyboard trap into invisible content.
 */

import { useEffect, useRef, useState } from "react";
import { useLocale } from "@/lib/i18n/provider";
import { languageName, languageOptions } from "@/lib/locale-choice";

export function LanguagePicker({ focusable = true }: { focusable?: boolean }) {
  const { locale, setLocale, t } = useLocale();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = languageOptions().find((option) => option.locale === locale);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  return (
    <div ref={ref} className="lang-dd">
      <button
        type="button"
        className="lang-dd-btn"
        lang={current?.htmlLang}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`${t.language.label}: ${languageName(locale)}`}
        tabIndex={focusable ? 0 : -1}
        onClick={() => setOpen((o) => !o)}
      >
        <svg className="lang-dd-globe" viewBox="0 0 24 24" width="15" height="15" aria-hidden>
          <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.3" />
          <ellipse cx="12" cy="12" rx="4" ry="9" fill="none" stroke="currentColor" strokeWidth="1.3" />
          <path d="M3.5 9h17M3.5 15h17" fill="none" stroke="currentColor" strokeWidth="1.3" />
        </svg>
        <span className="lang-dd-name">{languageName(locale)}</span>
        <span className="lang-dd-caret" aria-hidden>
          {open ? "▴" : "▾"}
        </span>
      </button>
      {open && (
        <ul className="lang-dd-menu" role="listbox" aria-label={t.language.label}>
          {languageOptions().map((option) => (
            <li key={option.locale}>
              <button
                type="button"
                role="option"
                className="lang-dd-opt"
                lang={option.htmlLang}
                data-current={option.locale === locale || undefined}
                aria-selected={option.locale === locale}
                onClick={() => {
                  setLocale(option.locale);
                  setOpen(false);
                }}
              >
                {option.name}
                {option.locale === locale && (
                  <span className="lang-dd-check" aria-hidden>
                    ✦
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      <span className="sr-only" role="status" aria-live="polite" lang={current?.htmlLang}>
        {t.language.label}: {languageName(locale)}
      </span>
    </div>
  );
}
