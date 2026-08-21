"use client";

import { useCallback, useEffect, useId, useRef, useState, type CSSProperties, type ReactNode } from "react";

/**
 * The primitives the storefront shares.
 *
 * Five went with the cabinet: a section label, a ruled label, a status tag, a
 * generic row and a settings row. All five were shapes for screens that read a
 * chart, and the landing has always drawn its own headings — a component with
 * one caller is a component, a component with none is a shape somebody will
 * reuse wrongly because it is there.
 */

/* ══ Buttons ══════════════════════════════════════════════════════ */

type BtnProps = {
  children: ReactNode;
  /**
   * Two, where there were five. `veil`, `danger` and `ink` dressed the
   * settings screen's destructive actions and the parchment reader; their
   * rules are out of `globals.css`, so leaving the names here would offer a
   * variant that renders as an unstyled button.
   */
  variant?: "gold" | "outline";
  block?: boolean;
  onClick?: () => void;
  style?: CSSProperties;
  type?: "button" | "submit";
  disabled?: boolean;
  "aria-label"?: string;
};

export function Button({ children, variant = "gold", block, onClick, style, type = "button", disabled, ...rest }: BtnProps) {
  const cls = ["btn", `btn-${variant}`, block ? "btn-block" : ""].filter(Boolean).join(" ");
  return (
    <button className={cls} onClick={onClick} style={style} type={type} disabled={disabled} {...rest}>
      {children}
    </button>
  );
}

/* ══ Custom select — never native (locale format drift) ═══════════ */

export function Select({
  value,
  placeholder,
  options,
  onChange,
  flex = 1,
  ariaLabel,
  missing,
}: {
  value: string | null;
  placeholder: string;
  options: string[];
  onChange: (v: string) => void;
  flex?: number;
  ariaLabel: string;
  /** the field the CTA is waiting on — a gold ring, never a red error */
  missing?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const listId = useId();

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  return (
    // `min-width: 0` lives in the stylesheet rather than here so a caller
    // can raise it — an inline style cannot be overridden by CSS, and the
    // hero row needs its fields to stop shrinking before the word "Month"
    // becomes "M…".
    <div ref={ref} className="select-wrap" style={{ flex, position: "relative" }}>
      <button
        type="button"
        className="field"
        style={{ width: "100%" }}
        data-open={open}
        data-empty={value === null}
        data-missing={missing || undefined}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={ariaLabel}
        onClick={() => setOpen((o) => !o)}
      >
        <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{value ?? placeholder}</span>
        <span className="field-caret">{open ? "▴" : "▾"}</span>
      </button>
      {open && (
        <ul
          id={listId}
          role="listbox"
          aria-label={ariaLabel}
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            left: 0,
            right: 0,
            zIndex: 50,
            maxHeight: 244,
            overflowY: "auto",
            listStyle: "none",
            margin: 0,
            padding: 6,
            borderRadius: 22,
            background: "var(--night-700)",
            border: "1px solid rgba(201,174,107,.3)",
            boxShadow: "var(--elev-2)",
          }}
        >
          {options.map((o) => (
            <li key={o}>
              <button
                type="button"
                role="option"
                aria-selected={o === value}
                onClick={() => {
                  onChange(o);
                  setOpen(false);
                }}
                style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "11px 16px",
                  borderRadius: 999,
                  border: 0,
                  background: o === value ? "rgba(201,174,107,.14)" : "transparent",
                  color: o === value ? "var(--gold-bright)" : "var(--body)",
                  fontSize: 15.5,
                  cursor: "pointer",
                }}
              >
                {o}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ══ Toggle ═══════════════════════════════════════════════════════ */

export function Toggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      className="toggle"
      data-on={on}
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={() => onChange(!on)}
    />
  );
}

/* ══ FAQ — accordions, each answering one objection ═══════════════ */

export function Accordion({
  q,
  a,
  open,
  onToggle,
  size = "m",
}: {
  q: string;
  a: string;
  /** Controlled by the FAQ section so only one answer is open at a time. */
  open: boolean;
  onToggle: () => void;
  size?: "m" | "l";
}) {
  const id = useId();
  return (
    <div className="faq-item" data-open={open} data-size={size}>
      <button
        type="button"
        className="faq-q tap44"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={id}
      >
        <span className="faq-q-text">{q}</span>
        {/* One glyph, rotated. A plus that turns 45° into a cross reads as
            open/close without swapping the character, so the icon animates on
            the same curve as the panel rather than popping. */}
        <span className="faq-q-icon" aria-hidden>
          +
        </span>
      </button>
      {/* The grid `0fr → 1fr` height transition: the answer stays in the DOM so
          it can animate, the inner box clips it, and `aria-hidden` keeps a
          closed answer out of the screen-reader flow. */}
      <div className="faq-a-wrap" aria-hidden={!open}>
        <div className="faq-a-clip">
          <p className="faq-a" id={id}>
            {a}
          </p>
        </div>
      </div>
    </div>
  );
}

/* ══ Rails ════════════════════════════════════════════════════════ */

/**
 * Tracks the card nearest the start of a horizontal rail by measuring the
 * real children, so the dots stay honest whatever the card width is, and
 * lets the dots page the rail.
 */
export function useRail() {
  const ref = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(0);
  const [count, setCount] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const read = () => {
      const kids = Array.from(el.children) as HTMLElement[];
      setCount(kids.length);
      // when the rail is laid out as a grid there is nothing to page
      if (getComputedStyle(el).overflowX !== "auto") return;
      const left = el.scrollLeft;
      let nearest = 0;
      let best = Infinity;
      kids.forEach((kid, i) => {
        const d = Math.abs(kid.offsetLeft - el.offsetLeft - left);
        if (d < best) {
          best = d;
          nearest = i;
        }
      });
      // at the very end, the last card is the one on screen
      if (left >= el.scrollWidth - el.clientWidth - 2) nearest = kids.length - 1;
      setIndex(nearest);
    };

    read();
    el.addEventListener("scroll", read, { passive: true });
    const ro = new ResizeObserver(read);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", read);
      ro.disconnect();
    };
  }, []);

  const goto = useCallback((i: number) => {
    const el = ref.current;
    if (!el) return;
    const kid = el.children[i] as HTMLElement | undefined;
    if (!kid) return;
    el.scrollTo({ left: kid.offsetLeft - el.offsetLeft, behavior: "smooth" });
  }, []);

  return { ref, index, count, goto };
}

/**
 * `label` is passed in rather than read from the dictionary here.
 *
 * The name of each dot used to be built in this file — `` `Go to ${i + 1} of
 * ${count}` `` — which meant the eight controls a phone user steps through to
 * reach the eight systems announced themselves in English on the Spanish,
 * German, Italian, French and Brazilian landings. An `aria-label` is a
 * user-facing string and this one was outside every check that exists for
 * them, because `check-locales.mjs` reads `src/lib/i18n` and this is not that.
 *
 * The component still does not read the dictionary. It is a generic control
 * used by whoever has a rail, and it already takes `note` from its caller for
 * the same reason: the thing that knows what is in the rail is the thing that
 * can name it.
 */
export function RailDots({
  count,
  active,
  note,
  label,
  onSelect,
}: {
  count: number;
  active: number;
  note: string;
  label: (position: number, total: number) => string;
  onSelect?: (i: number) => void;
}) {
  return (
    <div className="dots" style={{ padding: "14px var(--pad) 0" }}>
      {Array.from({ length: count }).map((_, i) => (
        <button
          key={i}
          type="button"
          className="dot tap44"
          data-active={i === active}
          aria-label={label(i + 1, count)}
          aria-current={i === active}
          onClick={() => onSelect?.(i)}
        />
      ))}
      <span style={{ marginLeft: 8, fontSize: 12, color: "var(--muted-3)" }}>{note}</span>
    </div>
  );
}
