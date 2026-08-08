"use client";

/**
 * Six words, each in its own language.
 *
 * The locale was negotiated from `Accept-Language` and there was nothing on
 * the page that could disagree with it — a Briton in Spain met a Spanish site
 * with no way out. This is the way out.
 *
 * ── why it is a row of words and not a dropdown ───────────────────────────
 * Six options is small enough to show whole, and showing them whole removes
 * every hard part: no popup to position, no outside-click to catch, no focus
 * to trap and return, no `aria-expanded` to keep honest, and nothing that can
 * open behind the sticky bar on a phone. It also fits the house rule — night,
 * one gold, no boxes — which a floating panel does not. A `<select>` would
 * have been fewer lines still and was rejected for a specific reason: the
 * native control renders in the platform's chrome and the closed state shows
 * one name, so the five languages a person is looking for are the five they
 * cannot see until they open it.
 *
 * ── the accessibility, which is most of the point ─────────────────────────
 * Real `<button>`s, so they are in the tab order without being told to be, and
 * they inherit the focus ring `globals.css` puts on everything interactive.
 * The group carries the translated word for "Language" as its accessible name,
 * which is the one string here that has to be in the reader's language —
 * everything else is deliberately in somebody else's. `aria-current` marks the
 * language being read, so a screen reader announces it as the current one
 * rather than leaving six identical-sounding choices. Each option carries its
 * own `lang`, so "Français" is pronounced in French rather than sounded out by
 * an English voice, which is the difference between a name and a noise.
 *
 * `focusable` exists for the mobile nav sheet, which is collapsed to zero
 * height rather than unmounted: focusable controls inside an `aria-hidden`
 * container are a keyboard trap into invisible content, and the sheet's links
 * already solve it the same way.
 */

import { useLocale } from "@/lib/i18n/provider";
import { languageName, languageOptions } from "@/lib/locale-choice";

export function LanguagePicker({ focusable = true }: { focusable?: boolean }) {
  const { locale, setLocale, t } = useLocale();
  const current = languageOptions().find((option) => option.locale === locale);

  return (
    <div className="lang" role="group" aria-label={t.language.label}>
      {languageOptions().map((option) => (
        <button
          key={option.locale}
          type="button"
          className="lang-option"
          lang={option.htmlLang}
          aria-current={option.locale === locale ? "true" : undefined}
          tabIndex={focusable ? 0 : -1}
          onClick={() => setLocale(option.locale)}
        >
          {option.name}
        </button>
      ))}
      {/*
        Something says out loud that the language changed.

        Everything visible about this control was already correct — `<html
        lang>` moves, the group's name moves, `aria-current` moves, the page
        title moves, and focus stays on the button that was pressed — and none
        of it makes a sound. The one person this control exists for is somebody
        who could not read the page they were on, and silence after activating
        it leaves them with no way to know it worked except by re-reading the
        page to find out. `aria-current` having moved is discoverable on the
        *next* interaction, which is one interaction too late.

        Rendered from the new locale's own dictionary and carrying the new
        locale's `lang`, so the confirmation is spoken in the voice `<html lang>`
        has just switched to — "Sprache: Deutsch" in a German voice, not sounded
        out by an English one. That is the same rule each option in the row
        follows.

        No new dictionary key: this is the pair the nav's toggle already uses
        for its accessible name, and two different confirmations of one event
        are two things that come apart.

        `polite` rather than `assertive`: nothing here is urgent, and the
        announcement should queue behind whatever the reader was in the middle
        of rather than cut it off. The region is always in the DOM so the change
        is a change to live content rather than the arrival of a live region,
        which is the difference between being announced and being ignored.
      */}
      <span className="sr-only" role="status" aria-live="polite" lang={current?.htmlLang}>
        {t.language.label}: {languageName(locale)}
      </span>
    </div>
  );
}
