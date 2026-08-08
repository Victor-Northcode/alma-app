"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import type { JourneyDoor } from "./cta";

/**
 * The date entered on the landing page is carried into the journey and
 * never asked again. Pressing any start button opens the overlay — it
 * never reloads the page, and closing it returns to the landing with the
 * state kept.
 */

export interface BirthDate {
  day: number;
  month: number; // 1-12
  year: number;
}

/**
 * A place as the gazetteer knows it.
 *
 * The journey used to keep only the typed string. That is enough to print
 * "Milan, Italy" on a screen and not nearly enough to cast a chart — a
 * chart needs a coordinate and, far more delicately, the timezone that
 * place was on at that date. So the selected place is carried whole.
 */
export interface ChosenPlace {
  id: number;
  label: string;
  latitude: number;
  longitude: number;
  timezone: string;
}

export interface JourneyState {
  date: BirthDate | null;
  intent: string | null;
  name: string;
  /**
   * Null until the person sets it. These used to default to 04:20 AM — the
   * reference chart's birth time — which meant anyone who tapped through the
   * step got a precise Ascendant computed from a stranger's minute. An unset
   * time is treated exactly like a declared unknown one.
   */
  hour: string | null;
  minute: string | null;
  /**
   * Defaulted to "AM", not null — the picker displays "AM" as its placeholder
   * whether or not anything is chosen, so a null here looked exactly like a
   * choice. Somebody who set 04 and 00 and never opened this list saw
   * `04 · 00 · AM` and had their birth time silently dropped by `hasTime`,
   * because it required this field to be truthy. Found on Android, where the
   * same code produced a profile row with `birth_time: null` and a portrait
   * saying NEEDS BIRTH TIME with no way to tell why. Fixed in both.
   */
  meridiem: string;
  timeUnknown: boolean;
  place: string | null;
  placeDetail: ChosenPlace | null;
  /** Set once the birth has been saved, so we do not save it twice. */
  savedProfileId: string | null;
}

const EMPTY: JourneyState = {
  date: null,
  intent: null,
  name: "",
  hour: null,
  minute: null,
  meridiem: "AM",
  timeUnknown: false,
  place: null,
  placeDetail: null,
  savedProfileId: null,
};

const KEY = "alma.journey";

interface Ctx {
  state: JourneyState;
  set: (patch: Partial<JourneyState>) => void;
  open: boolean;
  step: number;
  /**
   * Opens the overlay; `from` records which CTA fired it (analytics).
   *
   * A closed union rather than a free string, for the reason `track.ts` gives
   * about stage names: a typo does not fail, it invents a sixth source with a
   * plausible spelling and a count of one, and the funnel then shows one of the
   * five buttons having lost all of its traffic.
   */
  start: (from: JourneyDoor) => void;
  close: () => void;
  goto: (step: number) => void;
  next: () => void;
  revealed: boolean;
  reveal: () => void;
}

const JourneyContext = createContext<Ctx | null>(null);

export function JourneyProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<JourneyState>(EMPTY);
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(1);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(KEY);
      if (raw) setState({ ...EMPTY, ...JSON.parse(raw) });
    } catch {
      /* storage unavailable — the journey still works, it just won't survive a reload */
    }
  }, []);

  const set = useCallback((patch: Partial<JourneyState>) => {
    setState((prev) => {
      const nextState = { ...prev, ...patch };
      try {
        sessionStorage.setItem(KEY, JSON.stringify(nextState));
      } catch {
        /* ignore */
      }
      return nextState;
    });
  }, []);

  /**
   * The control that opened the journey, so closing it can put the reader back.
   *
   * This lives in the store rather than in the overlay because the overlay
   * unmounts the moment `open` goes false (`if (!open) return null`), so a
   * cleanup function inside it runs after the dialog — and the focus — are
   * already gone. The store outlives both.
   *
   * A ref rather than state: nothing renders differently for it, and putting a
   * DOM node in state would re-render every consumer of this context twice per
   * journey for no visible change.
   *
   * It is read at `start` time rather than being told which button it was.
   * Five controls open this overlay — the nav pill, the sheet, the insight CTA,
   * the pricing CTA, the final CTA, and the sticky bar makes six — and a list
   * of them here would be a sixth place to remember when a seventh is added.
   * Whatever had focus when the door was pressed is the thing to return to.
   */
  const opener = useRef<HTMLElement | null>(null);

  const start = useCallback((from: JourneyDoor) => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("alma:cta_click", { detail: { from } }));
      const active = document.activeElement;
      opener.current = active instanceof HTMLElement && active !== document.body ? active : null;
    }
    setOpen(true);
  }, []);

  const close = useCallback(() => setOpen(false), []);
  const goto = useCallback((s: number) => setStep(s), []);
  const next = useCallback(() => setStep((s) => Math.min(8, s + 1)), []);
  const reveal = useCallback(() => setRevealed(true), []);

  // The overlay owns the scroll while it is up.
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  /**
   * Closing returns focus to whatever opened the overlay.
   *
   * Measured before this existed: focusing the hero CTA, clicking it and
   * sampling `document.activeElement` at 60, 120, 350, 700 and 1200 ms gave
   * `BODY` every time, and pressing Escape left it on `BODY` too. A keyboard
   * user was dropped at the top of a 5,000 px document twice — once on the way
   * in and once on the way out — and had to tab back through thirty controls to
   * reach the button they had just pressed.
   *
   * An effect and not the body of `close()`, which is where this was first
   * written and where it cannot work. React batches a click handler's state
   * updates and flushes them after the handler returns, so a `focus()` call
   * beside `setOpen(false)` runs while the overlay is still mounted and the
   * landing behind it is still `inert` — and Chrome refuses focus inside an
   * inert subtree, silently, leaving the reader on `body` exactly as before.
   * An effect keyed on `open` is guaranteed to run after the DOM has caught up,
   * with `inert` gone and the opener focusable again.
   *
   * On first mount `open` is already false and there is no opener, so this is a
   * no-op until a journey has actually been opened and closed.
   *
   * `isConnected` is checked because the opener may be gone: the nav sheet's
   * CTA closes the sheet as it starts the journey. Focusing a detached node
   * silently drops focus to the body, which is the bug being fixed, so leaving
   * focus where the browser put it is better than pretending.
   *
   * `preventScroll` because the landing is exactly where the reader left it —
   * `body` kept `overflow: hidden` and the scroll position survived. Restoring
   * focus should not also jump the page.
   */
  useEffect(() => {
    if (open) return;
    const target = opener.current;
    opener.current = null;
    if (target && target.isConnected) target.focus({ preventScroll: true });
  }, [open]);

  const value = useMemo(
    () => ({ state, set, open, step, start, close, goto, next, revealed, reveal }),
    [state, set, open, step, start, close, goto, next, revealed, reveal],
  );

  return <JourneyContext.Provider value={value}>{children}</JourneyContext.Provider>;
}

export function useJourney() {
  const ctx = useContext(JourneyContext);
  if (!ctx) throw new Error("useJourney must be used inside <JourneyProvider>");
  return ctx;
}
