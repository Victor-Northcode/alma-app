"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Star, AlmaAvatar } from "@/components/brand/Star";
import { Comet, Mote, Starfield } from "@/components/sky/Sky";
import { SignInPanel } from "@/components/auth/SignInPanel";
import { GetTheApp } from "@/components/handoff/GetTheApp";
import { LanguagePicker } from "@/components/landing/LanguagePicker";
import { Button, Select, Toggle } from "@/components/ui";
import { CHAPTERS } from "@/lib/data";
import type { Dictionary } from "@/lib/i18n";
import { useT } from "@/lib/i18n/provider";
import { useJourney } from "@/lib/journey-store";
import { hasTime, saveBirth } from "@/lib/save-birth";
import { trackOnce, useStage } from "@/lib/track";
import { usePlaceSearch, useSystem } from "@/lib/use-alma";

const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"];

/**
 * The journey rises over the landing — no page load. The landing stays
 * underneath, scaled to .98 and dimmed to 40%. ✕ returns with state kept.
 * Every scene: living celestial art in the middle, controls at the bottom,
 * no boxes.
 *
 * There is no gate anywhere in it now. The offer that used to sit between the
 * portrait and the account is gone with the rest of the web checkout — the
 * ladder is sold through Apple and Google — so every step from here to the end
 * either gives something away or gets out of the way. What the website sells
 * is the download.
 */
export function JourneyOverlay() {
  const { open, close, state } = useJourney();
  const t = useT();
  const [index, setIndex] = useState(0);

  /**
   * The address a sign-in link was sent to during this walk, if one was.
   *
   * Held here rather than in the journey store, which persists to
   * sessionStorage: this is somebody's email address, it is needed for the
   * length of one screen, and writing it to storage to save passing a prop two
   * levels is a copy of a person's address left behind in their browser for no
   * benefit. It is also deliberately not read back from anywhere on reopen — a
   * link sent in a previous session is a fact we no longer know.
   */
  const [linkSentTo, setLinkSentTo] = useState<string | null>(null);

  /**
   * The top of the funnel, recorded from the one component that is mounted for
   * exactly as long as the landing is on screen.
   *
   * This reads oddly in a file called JourneyOverlay, and it is deliberate:
   * `LandingShell` mounts this component and nothing else does, so its mount is
   * one landing view and never two. The tidier home is the shell itself, which
   * belongs to somebody else this phase — see the note left with the results.
   */
  useStage("landing_view");

  // Opening the overlay is the quiz starting. Once per page load: closing and
  // reopening is the same person on the same visit, and counting it twice
  // makes the first drop-off rate look better than it is.
  useEffect(() => {
    if (open) trackOnce("quiz_start");
  }, [open]);

  /**
   * The date entered on the landing is carried over and never asked again.
   *
   * Two things about this, and both were wrong when it was one line.
   *
   * **Both arrays end at `handoff`.** The branch for a visitor who arrived
   * without a date stopped at `auth`, so the one screen that says where the
   * product actually lives was shown only to people who had typed their
   * birthday into the hero. That was survivable while the last step was a link
   * into a cabinet on the same origin. It is not survivable now that the last
   * step *is* the conversion — the whole of what this website is for.
   *
   * **The answer is frozen when the overlay opens.** It was read from live
   * state, so the moment somebody filled in the date step the array they were
   * walking swapped underneath them for the shorter one — and index 3, which
   * had just become "time", was now "place". Anyone who entered their date
   * inside the journey rather than on the landing was never asked what time
   * they were born, and there is no second chance to ask: the houses, the
   * Ascendant, the solar return and the whole map stay closed for a person who
   * would have answered. The counter lied about it too, jumping from "/ IX" to
   * "/ VIII" mid-walk.
   */
  const [needsDate, setNeedsDate] = useState(() => state.date === null);
  useEffect(() => {
    // On open, and only on open: the index is 0 here, so re-deciding the shape
    // of the walk cannot move anybody. `state.date` is deliberately not a
    // dependency — that is exactly the swap this exists to prevent.
    if (open) setNeedsDate(state.date === null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const steps = useMemo(
    () =>
      needsDate
        ? (["intent", "name", "date", "time", "place", "ceremony", "portrait", "auth", "handoff"] as const)
        : (["intent", "name", "time", "place", "ceremony", "portrait", "auth", "handoff"] as const),
    [needsDate],
  );

  useEffect(() => {
    if (!open) setIndex(0);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [open, close]);

  /**
   * Focus enters the dialog when the dialog opens.
   *
   * `role="dialog"`, `aria-modal="true"` and a label were all declared below
   * and none of them was ever announced, because focus never arrived: measured
   * from a click on the insight CTA, `document.activeElement` was `<body>` at
   * 60, 120, 350, 700 and 1200 ms. A screen-reader user who pressed the biggest
   * gold button on the page heard nothing at all — not the dialog's name, not
   * the step counter, not the first question — while the page behind them went
   * `inert` and silent. Containment was the half that had been done; this is
   * the other half, and neither is worth much alone.
   *
   * The container takes focus rather than the first control, which is why it
   * carries `tabIndex={-1}`. Focusing the ✕ would announce "back, button" and
   * bury the fact that a modal opened at all; focusing the container announces
   * the dialog and its name first, and the next Tab lands on the ✕ anyway
   * because it is the first thing in the DOM.
   *
   * Keyed on `open` alone, so moving between the nine steps does not haul focus
   * back to the top of a dialog somebody is already working inside.
   */
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (open) dialog.current?.focus({ preventScroll: true });
  }, [open]);

  if (!open) return null;

  const step = steps[index];
  const next = () => setIndex((i) => Math.min(steps.length - 1, i + 1));

  return (
    <div
      className="journey"
      role="dialog"
      aria-modal="true"
      aria-label={t.journey.dialogLabel}
      ref={dialog}
      tabIndex={-1}
    >
      <div className="journey-scene">
        <Starfield second />
        <Mote top="26%" left="8%" duration={13} />
        <Mote top="44%" left="74%" duration={16} delay={4} color="#E4D3A2" size={1.6} />
        <Mote top="66%" left="36%" duration={15} delay={8} color="#FFF8E6" />
        <Comet top="14%" left="22%" width={150} duration={17} />

        <header className="journey-head">
          <span className="journey-count">
            {/* Derived, not written: the journey gained a step and a hard-coded
                "/ VIII" would have quietly started lying about how far along
                somebody was. */}
            {ROMAN[index]} <span style={{ color: "var(--muted-3)" }}>/ {ROMAN[steps.length - 1]}</span>
          </span>
          {step === "handoff" ? (
            <span style={{ fontSize: 12.5, color: "var(--muted-3)" }}>{t.journey.done}</span>
          ) : (
            <button type="button" className="journey-close" onClick={close} aria-label={t.journey.back}>
              ✕
            </button>
          )}
          {/* The picker belongs here more than anywhere else on the site, and
              this was the one screen it was missing from.

              The overlay is `position: fixed; inset: 0` at z-index 70 with
              `overflow: hidden` on the body behind it, so while it is open it
              *is* the viewport: six real wheel-scroll bursts move `scrollY`
              from 0 to 0. All five gold controls on the landing open it. So a
              Briton in Spain who does the natural thing — press the big gold
              button — was nine steps deep in Spanish, being asked for a name, a
              birth date, a birth time and a birthplace, with the only way out
              of the wrong language four thousand pixels down a page they could
              no longer reach. The picker was built for exactly that person and
              was absent from exactly their screen.

              It costs nothing to put here: switching mid-journey is already
              proven safe — the cookie is written, React state moves in the same
              frame, and `router.refresh()` re-renders the server tree without
              discarding the name, date, time and place already typed. A
              `location.reload()` would have thrown all four away, which is why
              `setLocale` does not use one.

              Its own row, after the close button in both DOM and tab order:
              the dialog's own controls come first, and the six names need the
              full width at 360 px. */}
          <div className="journey-lang">
            <LanguagePicker />
          </div>
        </header>

        {step === "intent" && <StepIntent onNext={next} />}
        {step === "name" && <StepName onNext={next} />}
        {step === "date" && <StepDate onNext={next} />}
        {step === "time" && <StepTime onNext={next} />}
        {step === "place" && <StepPlace onNext={next} />}
        {step === "ceremony" && <StepCeremony onNext={next} />}
        {step === "portrait" && <StepPortrait onNext={next} />}
        {step === "auth" && <StepAuth onNext={next} onLinkSent={setLinkSentTo} />}
        {step === "handoff" && <StepHandoff linkSentTo={linkSentTo} />}
      </div>
    </div>
  );
}

/* ══ scene chrome ═════════════════════════════════════════════════ */

function Scene({
  art,
  title,
  sub,
  controls,
  artHeight = 308,
}: {
  art: ReactNode;
  title?: string;
  sub?: string;
  controls: ReactNode;
  artHeight?: number;
}) {
  return (
    <>
      <div className="journey-art" style={{ height: artHeight }}>
        {art}
      </div>
      {title && (
        <div className="journey-copy">
          <h2 className="journey-title">{title}</h2>
          {sub && <p className="journey-sub">{sub}</p>}
        </div>
      )}
      <div className="journey-controls">{controls}</div>
    </>
  );
}

/* ══ I · what's loudest ═══════════════════════════════════════════ */

/**
 * The four intents, each pointing at the system that answers it.
 *
 * This used to decide what was *sold* at the end: someone who said "us, will
 * this work" met a compatibility door rather than a natal one. Nothing is sold
 * on the web any more, and the honest options at that point were to delete the
 * mapping or to give it the only job left worth doing — so the handoff names
 * the matched system as the thing waiting in the app.
 *
 * The alternative was to keep asking the question and read the answer nowhere,
 * which is worse than either: a question asked for nothing is a step somebody
 * abandons at, and this one is ten seconds into the funnel.
 */
const INTENTS: Array<{ key: keyof Dictionary["journey"]["intents"]; system: string }> = [
  { key: "self", system: "natal" },
  { key: "shifting", system: "transits" },
  { key: "us", system: "compatibility" },
  { key: "where", system: "astrocartography" },
];

function StepIntent({ onNext }: { onNext: () => void }) {
  const { state, set } = useJourney();
  const t = useT();
  return (
    <Scene
      artHeight={336}
      art={
        <svg width="360" height="326" viewBox="0 0 320 290" fill="none" style={{ overflow: "visible", maxWidth: "100%" }} aria-hidden>
          <path
            d="M54 214 L112 128 L182 160 L232 66 L286 112"
            stroke="#C9AE6B"
            strokeOpacity=".5"
            strokeDasharray="460"
            strokeDashoffset="460"
            style={{ animation: "dash 3.4s ease-out forwards" }}
          />
          <path
            d="M112 128 L142 236 L232 66"
            stroke="#C9AE6B"
            strokeOpacity=".26"
            strokeDasharray="460"
            strokeDashoffset="460"
            style={{ animation: "dash 4.2s ease-out .5s forwards" }}
          />
          <g fill="#F6E7BC">
            <circle cx="54" cy="214" r="3.6" style={{ animation: "twinkle 3.6s ease-in-out infinite" }} />
            <circle cx="112" cy="128" r="4.8" style={{ animation: "twinkle 4.4s ease-in-out .6s infinite" }} />
            <circle cx="182" cy="160" r="3.2" style={{ animation: "twinkle 4s ease-in-out .3s infinite" }} />
            <circle cx="232" cy="66" r="5.4" style={{ animation: "twinkle 5.2s ease-in-out .9s infinite" }} />
            <circle cx="286" cy="112" r="3.4" style={{ animation: "twinkle 4.8s ease-in-out 1.2s infinite" }} />
            <circle cx="142" cy="236" r="4" style={{ animation: "twinkle 4.2s ease-in-out .2s infinite" }} />
          </g>
          <circle cx="232" cy="66" r="17" stroke="#E4D3A2" strokeOpacity=".26" />
        </svg>
      }
      title={t.journey.intentTitle}
      controls={
        <>
          {INTENTS.map((intent) => (
            <button
              key={intent.key}
              type="button"
              className="choice"
              data-selected={state.intent === intent.key}
              onClick={() => {
                // The key, not the sentence. The sentence is different in six
                // languages; what the handoff at the end needs is the choice.
                set({ intent: intent.key });
                onNext();
              }}
            >
              {t.journey.intents[intent.key]}
            </button>
          ))}
          <button type="button" className="journey-skip" onClick={onNext}>
            {t.journey.intentSkip}
          </button>
        </>
      }
    />
  );
}

/* ══ II · name (a name isn't an account) ══════════════════════════ */

function StepName({ onNext }: { onNext: () => void }) {
  const { state, set } = useJourney();
  const t = useT();
  return (
    <Scene
      artHeight={302}
      art={
        <>
          <div className="orbit-halo" aria-hidden />
          <div className="orbit-ring" aria-hidden>
            <div className="orbit-body" />
          </div>
          <div className="orbit-ring-dashed" aria-hidden />
          <AlmaAvatar size={62} ring={false} />
        </>
      }
      title={t.journey.nameTitle}
      sub={t.journey.nameSub}
      controls={
        <>
          <input
            className="text-input"
            value={state.name}
            onChange={(e) => set({ name: e.target.value })}
            placeholder={t.journey.namePlaceholder}
            aria-label={t.journey.nameAria}
            autoFocus
          />
          <Button block onClick={onNext}>
            {t.journey.continueCta}
          </Button>
          <div className="journey-or">
            <span />
            <span>{t.journey.orFaster}</span>
            <span />
          </div>
          <button type="button" className="provider" onClick={onNext}>
            <span className="provider-mark">G</span>
            {t.journey.withGoogle}
          </button>
        </>
      }
    />
  );
}

/* ══ date — only when it wasn't captured on the landing ═══════════ */

const YEARS = Array.from({ length: 92 }, (_, i) => String(new Date().getFullYear() - 10 - i));

function StepDate({ onNext }: { onNext: () => void }) {
  const { set } = useJourney();
  const t = useT();
  const [day, setDay] = useState<string | null>(null);
  // The index, not the word: "März" has to become 3 for the backend, and the
  // word it came from is different in every locale.
  const [monthIndex, setMonthIndex] = useState(-1);
  const [year, setYear] = useState<string | null>(null);
  const months = t.months as readonly string[];
  const complete = day !== null && monthIndex >= 0 && year !== null;

  return (
    <Scene
      artHeight={300}
      art={
        <svg width="262" height="262" viewBox="0 0 230 230" fill="none" aria-hidden>
          <circle cx="115" cy="115" r="106" stroke="#C9AE6B" strokeOpacity=".45" />
          <circle cx="115" cy="115" r="86" stroke="#A8873C" strokeOpacity=".3" strokeDasharray="2 5" />
          <g style={{ animation: "spin 180s linear infinite", transformOrigin: "115px 115px" }}>
            <circle cx="115" cy="20" r="4" fill="#F6E7BC" />
          </g>
          <circle cx="115" cy="115" r="4.6" fill="#F6E7BC" />
        </svg>
      }
      title={t.journey.dateTitle}
      sub={t.journey.dateSub}
      controls={
        <>
          <div style={{ display: "flex", gap: 9 }}>
            <Select
              ariaLabel={t.capture.day}
              value={day}
              placeholder={t.capture.dayShort}
              options={Array.from({ length: 31 }, (_, i) => String(i + 1))}
              onChange={setDay}
            />
            <Select
              ariaLabel={t.capture.month}
              value={monthIndex >= 0 ? months[monthIndex] : null}
              placeholder={t.capture.monthShort}
              options={months as string[]}
              onChange={(v) => setMonthIndex(months.indexOf(v))}
              flex={1.6}
            />
            <Select
              ariaLabel={t.capture.year}
              value={year}
              placeholder={t.capture.yearShort}
              options={YEARS}
              onChange={setYear}
              flex={1.3}
            />
          </div>
          <Button
            block
            disabled={!complete}
            onClick={() => {
              if (!complete) return;
              set({ date: { day: Number(day), month: monthIndex + 1, year: Number(year) } });
              onNext();
            }}
          >
            {t.journey.continueCta}
          </Button>
        </>
      }
    />
  );
}

/* ══ III · birth time, honestly ═══════════════════════════════════ */

const HOURS = Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, "0"));
const MINUTES = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, "0"));

function StepTime({ onNext }: { onNext: () => void }) {
  const { state, set } = useJourney();
  const t = useT();
  return (
    <Scene
      art={
        <svg width="262" height="262" viewBox="0 0 230 230" fill="none" aria-hidden>
          <circle cx="115" cy="115" r="106" stroke="#C9AE6B" strokeOpacity=".45" />
          <circle cx="115" cy="115" r="86" stroke="#A8873C" strokeOpacity=".3" strokeDasharray="2 5" />
          <g stroke="#C9AE6B" strokeOpacity=".55">
            <path d="M115 9v14M115 207v14M9 115h14M207 115h14" />
          </g>
          <g style={{ animation: "spin 60s linear infinite", transformOrigin: "115px 115px" }}>
            <path d="M115 115 L115 38" stroke="#F6E7BC" strokeOpacity=".9" strokeWidth="1.4" strokeLinecap="round" />
          </g>
          <g style={{ animation: "spin 720s linear infinite", transformOrigin: "115px 115px" }}>
            <path d="M115 115 L168 90" stroke="#C9AE6B" strokeOpacity=".8" strokeWidth="1.8" strokeLinecap="round" />
          </g>
          <circle cx="115" cy="115" r="4.6" fill="#F6E7BC" />
        </svg>
      }
      title={t.journey.timeTitle}
      sub={t.journey.timeSub}
      controls={
        <>
          <div style={{ display: "flex", gap: 9, opacity: state.timeUnknown ? 0.4 : 1 }}>
            <Select
              ariaLabel={t.journey.hourLabel}
              value={state.hour}
              placeholder={t.journey.hourLabel}
              options={HOURS}
              onChange={(v) => set({ hour: v })}
            />
            <Select
              ariaLabel={t.journey.minuteLabel}
              value={state.minute}
              placeholder={t.journey.minuteLabel}
              options={MINUTES}
              onChange={(v) => set({ minute: v })}
            />
            <Select
              ariaLabel={t.journey.meridiemLabel}
              value={state.meridiem}
              // "AM" is the same token in all six locales — it is what the
              // option list itself contains, not a translated word.
              placeholder="AM"
              options={["AM", "PM"]}
              onChange={(v) => set({ meridiem: v })}
            />
          </div>
          <div className="journey-toggle-row">
            <span>
              <span style={{ fontSize: 15, color: "rgba(237,231,218,.8)" }}>{t.capture.unknownTime}</span>
              {/* Shown for a declared unknown AND for a step tapped straight
                  through: both mean we have no time, and only one of them
                  used to say so. */}
              {!hasTime(state) && (
                <span style={{ display: "block", fontSize: 13, color: "var(--muted-2)", marginTop: 3 }}>
                  {t.journey.lockedWithoutTime}
                </span>
              )}
            </span>
            <Toggle
              on={state.timeUnknown}
              onChange={(v) => set({ timeUnknown: v })}
              label={t.capture.unknownTime}
            />
          </div>
          <Button block onClick={onNext}>
            {t.journey.continueCta}
          </Button>
        </>
      }
    />
  );
}

/* ══ IV · place ═══════════════════════════════════════════════════ */

function StepPlace({ onNext }: { onNext: () => void }) {
  const { state, set } = useJourney();
  const t = useT();
  const [query, setQuery] = useState(state.place ?? "");
  // The real gazetteer, debounced, with superseded requests aborted. This is
  // the one step whose answer the whole chart hangs on: the coordinate sets
  // the horizon and the timezone sets the instant.
  const { places, searching, failed } = usePlaceSearch(query);
  return (
    <Scene
      artHeight={292}
      art={
        <svg width="284" height="284" viewBox="0 0 250 250" fill="none" style={{ maxWidth: "100%" }} aria-hidden>
          <g style={{ animation: "spin 120s linear infinite", transformOrigin: "125px 125px" }}>
            <circle cx="125" cy="125" r="104" stroke="#C9AE6B" strokeOpacity=".5" />
            <g stroke="#C9AE6B" strokeOpacity=".28">
              <path d="M21 125h208M125 21c38 34 38 174 0 208M125 21c-38 34-38 174 0 208M46 68c48 24 110 24 158 0M46 182c48-24 110-24 158 0" />
            </g>
          </g>
          <circle cx="125" cy="125" r="104" stroke="#C9AE6B" strokeOpacity=".18" />
          <g>
            <circle cx="152" cy="86" r="5.6" fill="#F6E7BC" />
            <circle
              cx="152"
              cy="86"
              r="14"
              stroke="#F6E7BC"
              strokeOpacity=".4"
              style={{ animation: "ripple 4s ease-out infinite", transformOrigin: "152px 86px" }}
            />
          </g>
        </svg>
      }
      title={t.journey.placeTitle}
      sub={t.journey.placeSub}
      controls={
        <>
          <input
            className="text-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.journey.placePlaceholder}
            aria-label={t.capture.searchPlace}
          />
          <div className="suggestions">
            {places.map((place) => (
              <button
                key={place.id}
                type="button"
                className="suggestion"
                data-selected={state.placeDetail?.id === place.id}
                onClick={() => {
                  // The whole place, not just its name — the chart needs the
                  // coordinate and the zone, and asking again later would
                  // mean asking a question the person already answered.
                  set({
                    place: place.label,
                    placeDetail: {
                      id: place.id,
                      label: place.label,
                      latitude: place.latitude,
                      longitude: place.longitude,
                      timezone: place.timezone,
                    },
                  });
                  setQuery(place.label);
                }}
              >
                <span>{place.label}</span>
                <span className="suggestion-tz">{place.timezone.split("/").pop()?.replace(/_/g, " ")}</span>
              </button>
            ))}
            {!places.length && query.trim().length >= 2 && !searching && (
              <p className="suggestion-empty">{t.capture.noPlaces}</p>
            )}
            {failed && !places.length && <p className="suggestion-empty">{t.journey.placeOffline}</p>}
          </div>
          <Button
            block
            disabled={!state.placeDetail}
            onClick={onNext}
          >
            {t.journey.buildMySky}
          </Button>
        </>
      }
    />
  );
}

/* ══ V · the ceremony — ~9 s, always skippable ════════════════════ */


function StepCeremony({ onNext }: { onNext: () => void }) {
  const [i, setI] = useState(0);
  const { state, set } = useJourney();
  const t = useT();
  const ceremony = t.journey.ceremony;

  // Every question has been answered by the time this runs — the ceremony is
  // what plays while the birth is saved — so this is where the quiz completes.
  // Not the portrait: that screen is the reward, and conflating "answered
  // everything" with "saw the result" hides the people the save fails for.
  useStage("quiz_complete");

  /**
   * The birth is saved here, under the ceremony.
   *
   * Not earlier: someone who abandons at the time step has not asked us to
   * keep anything. Not later either — the ceremony runs about nine seconds,
   * which is exactly the cover a network round trip needs, so the portrait on
   * the next screen has something to draw by the time it renders.
   *
   * A failure is deliberately not surfaced here. The person is watching an
   * animation, not a form; the portrait is where a missing chart becomes
   * visible, and it shows an absent line rather than an invented one.
   */
  useEffect(() => {
    if (state.savedProfileId) return;
    let live = true;
    saveBirth(state).then((outcome) => {
      if (live && outcome.ok) set({ savedProfileId: outcome.profile.id });
    });
    return () => {
      live = false;
    };
    // Fires once per journey; `state` changing mid-ceremony would re-save.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (i >= ceremony.length - 1) {
      const done = setTimeout(onNext, 1400);
      return () => clearTimeout(done);
    }
    const tick = setTimeout(() => setI((v) => v + 1), 1150);
    return () => clearTimeout(tick);
  }, [i, onNext, ceremony.length]);

  return (
    <>
      <div className="journey-art ceremony-art">
        <div className="ceremony-ring-outer" aria-hidden />
        <div className="ceremony-ring" aria-hidden>
          <div className="ceremony-body-a" />
          <div className="ceremony-body-b" />
        </div>
        <svg width="272" height="272" viewBox="0 0 240 240" fill="none" style={{ position: "absolute", maxWidth: "100%" }} aria-hidden>
          <circle cx="120" cy="120" r="112" stroke="#C9AE6B" strokeOpacity=".55" />
          <circle cx="120" cy="120" r="86" stroke="#A8873C" strokeOpacity=".5" strokeDasharray="2 4" />
          <circle cx="120" cy="120" r="44" stroke="#C9AE6B" strokeOpacity=".35" />
          <g stroke="#C9AE6B" strokeOpacity=".4" strokeWidth=".7">
            <path d="M120 8v224M8 120h224M40 40l160 160M200 40L40 200" />
            <path d="M120 34 L206 84 M120 34 L34 84 M206 156 L120 206 M34 156 L120 206 M206 84 L206 156 M34 84 L34 156" />
          </g>
          <g
            stroke="#E4D3A2"
            strokeOpacity=".85"
            strokeDasharray="300"
            strokeDashoffset="300"
            style={{ animation: "dash 3s ease-out forwards" }}
          >
            <path d="M74 66 L172 158 M172 158 L96 178 M96 178 L74 66" />
          </g>
          <g fill="#F6E7BC">
            <circle cx="74" cy="66" r="4" />
            <circle cx="172" cy="158" r="4" />
            <circle cx="96" cy="178" r="4" />
          </g>
        </svg>
        <AlmaAvatar size={58} ring={false} />
      </div>

      <div className="journey-copy" aria-live="polite">
        <div className="overline-wide" style={{ marginBottom: 14 }}>
          {ceremony[i][0]}
        </div>
        <p className="ceremony-line">{ceremony[i][1]}</p>
      </div>

      <div className="journey-controls">
        <div className="ceremony-bar">
          {ceremony.map((_, n) => (
            <span key={n} data-on={n <= i} />
          ))}
        </div>
        <button type="button" className="journey-skip" onClick={onNext}>
          {t.journey.ceremonySkip}
        </button>
      </div>
    </>
  );
}

/* ══ VI · the portrait — value delivered ══════════════════════════ */

/**
 * The moment the product first says "here is you".
 *
 * It used to say it about somebody else. The pills were literal constants —
 * `☽ 8° ♏︎`, `ASC 11° ♌︎` — shown to every visitor whatever their birth; the
 * paragraph underneath was one fixed interpretation ("water sign, fixed
 * Moon…") regardless of chart; and the three rows claimed "16 chapters ready ·
 * 9 axes ready · 3 active today" without anything having been counted. On the
 * one screen whose whole job is to prove the calculation is real, all of it
 * was decoration.
 *
 * Now every line is fetched. The birth was saved during the ceremony a moment
 * earlier, so by the time this renders the request usually has an answer; if
 * it does not, the line is simply absent. Nothing here waits on a spinner and
 * nothing here guesses — an empty row is honest, a filled one is true.
 */
function StepPortrait({ onNext }: { onNext: () => void }) {
  const { state } = useJourney();
  const t = useT();
  const who = state.name.trim();

  useStage("portrait_view");

  const natal = useSystem("natal");
  const numerology = useSystem("numerology");
  const birthCard = useSystem("birth-card");

  // Locked is the normal case here — nobody has bought anything, and nobody
  // can from a browser — and a locked system still answers with its whole
  // calculation, which is more than the three signs this screen prints.
  const chart = (natal.data?.data ?? {}) as {
    sun_sign?: string;
    moon_sign?: string;
    rising_sign?: string | null;
    moon_phase?: { phase?: string };
    placements?: Record<string, { sign_glyph?: string } | undefined>;
  };
  const numbers = (numerology.data?.data ?? {}) as { life_path?: number };

  const signName = (english?: string | null) =>
    english ? (t.signs[english as keyof typeof t.signs] ?? english) : "";

  const pills = [
    chart.moon_sign ? `☽ ${signName(chart.moon_sign)}` : null,
    // The Ascendant exists only when the birth time does — the backend refuses
    // to compute a horizon without one, and this is the screen where that
    // refusal is most worth showing rather than hiding.
    chart.rising_sign ? `${t.journey.ascendant} ${signName(chart.rising_sign)}` : null,
    typeof numbers.life_path === "number" ? t.insight.lifePath(numbers.life_path) : null,
  ].filter((pill): pill is string => pill !== null);

  const sunGlyph = chart.placements?.sun?.sign_glyph ?? "";
  const sunLine = chart.sun_sign
    ? `${who ? `${who} · ` : ""}${t.insight.sun(signName(chart.sun_sign))}`
    : who;

  /**
   * The numbers that cost nothing, handed over here rather than promised.
   *
   * These used to be described as two free *systems*, and the backend used to
   * agree: `FREE_SYSTEMS` held numerology and the birth card. It is an empty
   * frozenset now (`alma/auth/entitlements.py`) — whole free systems ended, and
   * what stayed free is every calculation plus one written chapter per system.
   * So the promise kept here is about the values, not about a system: they are
   * computed, and computed is always free. That is also why the count is never
   * stated. This list is three rows for a birth with a known time and fewer
   * without one, and the sentence under it has to stay true either way — the
   * old one said "these two systems" above three rows. Both apps caught this
   * before the web did and each left a note pointing back here
   * (`ScreenL10n.swift`, `values/strings.xml`). The wording below is Android's
   * verbatim, in all six languages, because only its first half needed to
   * change and copying a reviewed translation beats writing a sixth one. iOS
   * says the same thing in its own words rather than this one — three surfaces
   * agreeing on the fact, two of them sharing the sentence.
   *
   * Handing the numbers over here is what makes the download an invitation
   * rather than a toll: the person already has something true about themselves
   * and can walk away with it, which is the only position from which "there is
   * more in the app" is a sentence rather than a wall.
   *
   * Every row is dropped if its request has not answered. A missing line is
   * better than a placeholder in the one place we are proving we do not use
   * placeholders.
   */
  const card = (birthCard.data?.data ?? {}) as {
    personality?: { name?: string; numeral?: string };
  };
  const free = [
    typeof numbers.life_path === "number"
      ? { label: t.eight.names.numerology, value: t.insight.lifePath(numbers.life_path) }
      : null,
    card.personality?.name
      ? {
          label: t.eight.names["birth-card"],
          value: `${card.personality.numeral ?? ""} ${card.personality.name}`.trim(),
        }
      : null,
    chart.moon_phase?.phase
      ? {
          label: t.journey.moonPhase,
          value:
            t.journey.phases[chart.moon_phase.phase as keyof typeof t.journey.phases] ??
            chart.moon_phase.phase,
        }
      : null,
  ].filter((row): row is { label: string; value: string } => row !== null);

  return (
    <div className="journey-scroll">
      <div className="portrait-head">
        <div className="overline-wide">{t.journey.calculated}</div>
        <div className="portrait-glyph glyph">{sunGlyph}</div>
        <div className="portrait-name">{sunLine}</div>
        {pills.length > 0 && (
          <div className="portrait-pills">
            {pills.map((pill) => (
              <span key={pill} className="pill">
                {pill}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="portrait-body">
        {/* The interpretation that used to sit here was one paragraph for
            everyone. Alma writes those from the chart, inside a reading — she
            does not have one ready at this instant, and will not be given a
            stand-in.

            What goes here instead is the part that is genuinely free and
            genuinely theirs. Two of the eight systems cost nothing, ever, and
            this is where that promise gets kept rather than described: the
            numbers are handed over before anything is asked for. */}
        <div className="rule-fade" style={{ margin: "22px 0" }} />

        {free.length > 0 && (
          <>
            <div className="overline" style={{ letterSpacing: "0.2em", marginBottom: 12 }}>
              {t.journey.freeLabel}
            </div>
            {free.map((row) => (
              <div key={row.label} className="portrait-row">
                <span style={{ fontSize: 15.5, color: "rgba(237,231,218,.8)" }}>{row.label}</span>
                <span style={{ fontSize: 15, color: "var(--gold-bright)" }}>{row.value}</span>
              </div>
            ))}
            <p className="journey-fine" style={{ marginTop: 14, textAlign: "left" }}>
              {t.journey.freeNote}
            </p>
          </>
        )}

        {!hasTime(state) && (
          <div className="portrait-row">
            <span style={{ fontSize: 15.5, color: "rgba(246,241,228,.7)" }}>
              {t.journey.needsTimeRow}
            </span>
            <span className="tag tag-gold">{t.journey.needsTimeTag}</span>
          </div>
        )}
      </div>

      <div className="journey-controls journey-controls-static">
        <Button block onClick={onNext}>
          {t.journey.keepMySky}
        </Button>
        <p className="journey-fine">{t.journey.staysFree}</p>
      </div>
    </div>
  );
}

/* ══ VII · keeping it — an account, so the app can find this ══════ */

/**
 * Signing in, and what it is now for.
 *
 * It used to be the gate in front of the cabinet: read anything on this
 * website and you first had to be somebody. There is no cabinet, so the gate
 * would now be a wall in front of a door nobody is going through — which is
 * why the step is skippable and says so.
 *
 * What it still does is the reason it survives at all. The birth saved under
 * the ceremony belongs to a guest row in the backend; signing in attaches an
 * identity to that same row. Sign in here with the address you will use on the
 * phone, and the chart the website just calculated is already there when the
 * app opens. Skip it and nothing is lost that was ever promised — the portrait
 * was free and stays free — but the sky is stranded in this browser.
 */
function StepAuth({
  onNext,
  onLinkSent,
}: {
  onNext: () => void;
  onLinkSent: (email: string) => void;
}) {
  const { state } = useJourney();
  const t = useT();
  const who = state.name.trim();
  return (
    <Scene
      art={
        <>
          <div className="auth-halo" aria-hidden />
          <div className="ripple-ring ripple-ring-sm" aria-hidden />
          <div className="ripple-ring ripple-ring-sm" style={{ animationDelay: "3.5s" }} aria-hidden />
          <Star size={82} />
        </>
      }
      title={t.journey.authTitle(who)}
      sub={t.journey.authSub}
      controls={
        <>
          {/* The three buttons here used to call onNext() — the journey moved
              on and nobody was signed in. This is the moment a person decides
              to trust us with their birth data, so it is the last place in the
              product where the gesture and the effect are allowed to differ. */}
          {/* A sent link does not advance the journey — the person has not
              signed in yet, and moving them on would be the same lie the three
              buttons used to tell. It is remembered so that the last screen can
              say what that link is actually for. */}
          <SignInPanel onSignedIn={onNext} onLinkSent={onLinkSent} />
          <button type="button" className="journey-skip" onClick={onNext}>
            {t.journey.authSkip}
          </button>
          <p className="journey-legal">
            {t.journey.legalBefore}{" "}
            <a href="/terms" target="_blank" rel="noreferrer">
              {t.journey.legalTerms}
            </a>{" "}
            {t.journey.legalAnd}{" "}
            <a href="/privacy" target="_blank" rel="noreferrer">
              {t.journey.legalPrivacy}
            </a>
            {t.journey.legalAfter}
          </p>
        </>
      }
    />
  );
}

/* ══ VIII · handoff — the end of the website ══════════════════════ */

/**
 * Where the web stops — and the only conversion this website has left.
 *
 * This screen used to push `/today` and the person carried on reading in the
 * same tab. Everything they were carrying on into is in the app now, sold
 * through Apple and Google, so this is the last thing the product says from a
 * browser and it has to earn a download without becoming an advertisement.
 *
 * Four things, in the order a person needs them, and the order is the argument.
 *
 * **The system they asked for**, named from the very first question of the
 * quiz. Not a generic "get the app": they told us ten seconds in what was
 * loudest in them, and this is where that answer is finally spent.
 *
 * **What continues**, three points, one sentence each. Deliberately not four,
 * and deliberately without a single number that is not checkable — the chapter
 * counts come from `data.ts`, which `data.test.ts` holds against the writing
 * layer's own definitions. There is no timer, no struck-through price and no
 * "limited": that rule was written on `Paywall.tsx`, which no longer exists,
 * and it is inherited here rather than lost with the file. Nothing on this
 * screen is urgent, because nothing about it is: the portrait above was free
 * and stays free whether or not they ever install anything.
 *
 * **Where to get it, and what travels with them.** `GetTheApp` owns both,
 * including the awkward sentence about a guest chart not following anybody
 * anywhere. Neither store link exists yet: see `lib/stores.ts` for why the row
 * says "coming" instead of pretending, and for the one line that changes when a
 * listing goes live.
 *
 * **The three rules**, last, because they are for after the download rather
 * than before it. They were written as the only onboarding this product would
 * ever give, and they are as true on a phone as they were in a browser — more
 * so, since the person is about to read a chapter somewhere we cannot see them
 * and there is no second chance to say "one at a time".
 */
function StepHandoff({ linkSentTo }: { linkSentTo: string | null }) {
  const { state } = useJourney();
  const t = useT();
  const wanted = INTENTS.find((intent) => intent.key === state.intent) ?? INTENTS[0];
  const system = t.eight.names[wanted.system as keyof typeof t.eight.names];

  const continues = [
    [t.app.continues.chaptersLabel, t.app.continues.chapters(CHAPTERS)],
    [t.app.continues.secondLabel, t.app.continues.second],
    [t.app.continues.almaLabel, t.app.continues.alma],
  ] as const;

  return (
    <div className="journey-scroll">
      <div className="handoff">
        <AlmaAvatar size={64} ring={false} />
        <h2 className="journey-title" style={{ marginTop: 24 }}>
          {t.journey.handoffTitle}
        </h2>
        <p className="journey-sub">{t.app.waiting(system)}</p>

        <div className="continues">
          {continues.map(([label, line]) => (
            <div key={label} className="continues-row">
              <div className="overline">{label}</div>
              <p>{line}</p>
            </div>
          ))}
        </div>

        <GetTheApp linkSentTo={linkSentTo} />

        <p className="journey-sub" style={{ marginTop: 34 }}>
          {t.journey.handoffSub}
        </p>
        <div className="handoff-rules">
          {t.journey.rules.map((text, i) => (
            <div key={ROMAN[i]}>
              {i > 0 && <div className="handoff-rule" />}
              <div className="handoff-row">
                <span className="handoff-numeral">{ROMAN[i]}</span>
                <p>{text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
