"use client";

import { useMemo, useState } from "react";
import { Select } from "@/components/ui";
import { useT } from "@/lib/i18n/provider";
import { useJourney } from "@/lib/journey-store";

const YEARS = Array.from({ length: 92 }, (_, i) => String(new Date().getFullYear() - 10 - i));

/**
 * The capture widget lives in the first screen: three selects and one gold
 * button. Foot-in-the-door — a micro-action that costs nothing and already
 * returns a result. The date is carried onward and never asked again.
 */
export function DateCapture({
  layout = "stacked",
  label,
  onSubmit,
}: {
  /** "stacked" = button under the row (mobile/tablet); "inline" = button in the row (desktop) */
  layout?: "stacked" | "inline";
  label?: string;
  onSubmit: () => void;
}) {
  const { state, set } = useJourney();
  const t = useT();
  // Empty, not "14". The old defaults were the reference chart's birthday —
  // 14 March — so a visitor who scrolled past without touching anything was
  // shown somebody else's date sitting in their form, and the sticky bar at
  // the bottom then reported it back to them as theirs.
  // Derived from the store rather than seeded from it. `useState` reads its
  // argument once, on the first render — and the store hydrates from
  // `sessionStorage` inside an effect, which happens *after* that. So a
  // returning visitor used to find three empty selects under a hero already
  // showing their sign and their date, with the gold button asking for a date
  // they had given a minute earlier. The local state now holds only what has
  // been typed since this mount, and the store answers for everything else.
  const [typedDay, setTypedDay] = useState<string | null>(null);
  const day = typedDay ?? (state.date ? String(state.date.day) : null);
  const setDay = setTypedDay;
  // The month is held as an index, not as its name. Holding the name would
  // mean that switching language mid-form silently cleared the field, since
  // "March" is not in the Italian list — the kind of bug that only appears
  // once the product has more than one language.
  const [typedMonth, setTypedMonth] = useState<number | null>(null);
  const monthIndex = typedMonth ?? (state.date ? state.date.month - 1 : -1);
  const setMonthIndex = setTypedMonth;
  const [typedYear, setTypedYear] = useState<string | null>(null);
  const year = typedYear ?? (state.date ? String(state.date.year) : null);
  const setYear = setTypedYear;

  const [nudge, setNudge] = useState(false);
  const months = t.months as readonly string[];
  const month = monthIndex >= 0 ? months[monthIndex] : null;
  const daysInMonth = useMemo(() => {
    if (monthIndex < 0) return 31;
    const y = year ? Number(year) : 2000;
    return new Date(y, monthIndex + 1, 0).getDate();
  }, [monthIndex, year]);

  const days = useMemo(() => Array.from({ length: daysInMonth }, (_, i) => String(i + 1)), [daysInMonth]);
  const impossible = day !== null && Number(day) > daysInMonth;
  const complete = day !== null && monthIndex >= 0 && year !== null && !impossible;

  /* The button keeps its gold — an incomplete date points at the field
     that is missing rather than greying the promise out. */
  function submit() {
    if (!complete) {
      setNudge(true);
      return;
    }
    setNudge(false);
    set({ date: { day: Number(day), month: monthIndex + 1, year: Number(year) } });
    onSubmit();
  }

  const row = (
    <div className="date-row">
      <Select
        ariaLabel={t.capture.day}
        value={day}
        placeholder={t.capture.dayShort}
        options={days}
        onChange={setDay}
        flex={1}
      />
      <Select
        ariaLabel={t.capture.month}
        value={month}
        placeholder={t.capture.monthShort}
        options={months as string[]}
        onChange={(v) => setMonthIndex(v ? months.indexOf(v) : -1)}
        flex={1.6}
      />
      <Select
        ariaLabel={t.capture.year}
        value={year}
        placeholder={t.capture.yearShort}
        options={YEARS}
        onChange={(v) => {
          setYear(v);
          setNudge(false);
        }}
        flex={1.3}
        missing={nudge && year === null}
      />
      {layout === "inline" && (
        <button type="button" className="btn btn-gold date-inline-btn" onClick={submit}>
          {label ?? t.capture.submit}
        </button>
      )}
    </div>
  );

  return (
    <div>
      {row}
      {impossible && (
        <div style={{ fontSize: 13.5, color: "var(--disagree)", marginTop: 8 }} role="alert">
          {t.capture.impossibleDate}
        </div>
      )}
      {layout === "stacked" && (
        <button type="button" className="btn btn-gold btn-block" style={{ marginTop: 10 }} onClick={submit}>
          {label ?? t.capture.submit}
        </button>
      )}
      {nudge && !impossible && (
        <div className="date-nudge" role="status">
          {t.capture.pickYear}
        </div>
      )}
    </div>
  );
}
