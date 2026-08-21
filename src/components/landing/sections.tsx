"use client";

import { useState, type ReactNode } from "react";
import {
  ArcanaCard,
  ArtCircle,
  ChartWheel,
  ChartWheelSmall,
  Globe,
  NineAxisStar,
  NumberGlyph,
  Orbits,
  SolarWheel,
  TwoCircles,
} from "@/components/art";
import { Star } from "@/components/brand/Star";
import { Aura, Comet, Mote, Starfield } from "@/components/sky/Sky";
import { Accordion, RailDots, useRail } from "@/components/ui";
import { insightFor, systems } from "@/lib/data";
import { useT } from "@/lib/i18n/provider";
import { useJourney } from "@/lib/journey-store";
import {
  APP_STORE_BADGE,
  APP_STORE_URL,
  PLAY_STORE_BADGE,
  PLAY_STORE_URL,
} from "@/lib/stores";
import { offers, priceOf, useCatalogue } from "@/lib/use-catalogue";

/** Roman numerals differ by breakpoint — mobile carries two extra sections. */
function Numeral({ m, d }: { m: string; d: string }) {
  return (
    <span className="numeral">
      <span className="only-mobile">{m}</span>
      <span className="from-tablet">{d}</span>
    </span>
  );
}

function Label({ m, d, children, tone }: { m: string; d: string; children: ReactNode; tone?: "ink" }) {
  return (
    <div className="sec-head">
      <Numeral m={m} d={d} />
      <span className="overline-wide" style={tone === "ink" ? { color: "#7A6129" } : undefined}>
        {children}
      </span>
    </div>
  );
}

/* ══ HERO ═════════════════════════════════════════════════════════ */

export function Hero() {
  const { state } = useJourney();
  const t = useT();
  // Null until a date is entered. The wheel keeps turning either way — what
  // it must not do is put a stranger's sign in the middle and call it yours.
  const insight = insightFor(state.date);
  const stamp = state.date
    ? `${String(state.date.day).padStart(2, "0")}.${String(state.date.month).padStart(2, "0")}`
    : t.insight.awaitingMeta;
  return (
    <section id="top" className="hero">
      <Aura tone="indigo" size="min(900px,64vw)" top="-24%" right="-8%" drift="a" />
      <Aura tone="deep" size="min(760px,54vw)" bottom="-30%" left="-12%" drift="b" />
      <Starfield />
      <Comet top="80px" left="14%" />
      <Mote top="60%" left="8%" />
      <Mote top="70%" left="52%" duration={17} delay={4} color="#E4D3A2" size={1.6} />

      <div className="hero-inner">
        <div>
          <div className="overline-wide" style={{ marginBottom: 20 }}>
            {t.hero.overline}
          </div>
          {/* The line break is authored on mobile and desktop; tablet lets it
              flow — and the space after it is what makes "lets it flow" true.
              `.hero-break` is `display:none` between 700 and 1023, so without a
              space the two halves ran together: "Ocho formas de leerte a ti
              mismo" rendered as "leertea ti mismo", "dich zu lesen" as
              "dichzu lesen", and the same in all six languages. On the first
              line of the page, at every tablet width and every desktop window
              under 1024. The `<br>` is authored *after* the space for the same
              reason the "eight" title below does it that way: a space before a
              break collapses, a space after it survives when the break is
              hidden. */}
          <h1 className="hero-title">
            {t.hero.titleA}{" "}
            <br className="hero-break" />
            {t.hero.titleB} <span style={{ color: "var(--gold-bright)" }}>{t.hero.titleAccent}</span>
          </h1>
          <p className="hero-sub">
            <span className="only-mobile">{t.hero.subShort}</span>
            <span className="from-tablet">{t.hero.subLong}</span>
          </p>
          <div className="hero-capture">
            {/* The one door out of the landing: the app. The web used to open a
                free in-browser reading here; the product is sold and read in the
                app now, so every call to action hands the visitor over to the
                store instead of starting a session the site can no longer keep. */}
            <a className="btn btn-gold hero-cta" href="#get-app">
              {t.cta.getApp}
            </a>
            <p className="hero-cta-note">{t.app.appleSoon} · {t.app.googleSoon}</p>
          </div>
        </div>

        <div className="hero-art">
          <div className="star-map">
            <div
              style={{
                position: "absolute",
                inset: "6%",
                borderRadius: "50%",
                background: "radial-gradient(circle,rgba(58,52,132,.5),transparent 66%)",
                filter: "blur(26px)",
              }}
              aria-hidden
            />
            <ChartWheel style={{ position: "absolute" }} extraRing />
            <div
              style={{
                position: "absolute",
                width: "38%",
                aspectRatio: "1",
                borderRadius: "50%",
                background: "radial-gradient(circle,rgba(10,13,28,.92) 40%,rgba(10,13,28,0) 72%)",
              }}
              aria-hidden
            />
            <div className="ripple-ring" aria-hidden />
            <div className="ripple-ring" style={{ animationDelay: "3.5s", borderColor: "rgba(228,211,162,.3)" }} aria-hidden />
            <div style={{ position: "relative", textAlign: "center" }}>
              <div className="hero-glyph glyph">{insight ? insight.sign.glyph : "✦"}</div>
              <div className="hero-glyph-meta">{t.hero.yourSky} · {stamp}</div>
            </div>
          </div>
          <p className="hero-quote">
            “{t.hero.quote}”
            <span className="hero-quote-attr from-tablet">Alma</span>
          </p>
          <div className="overline only-mobile" style={{ marginTop: 10 }}>
            Alma
          </div>
        </div>
      </div>
    </section>
  );
}

/* ══ MARQUEE ══════════════════════════════════════════════════════ */

export function Marquee() {
  const t = useT();
  // Built from the translated system names rather than from its own word
  // list. Two lists of the same eight things is one list that drifts, and
  // the marquee is the first thing a non-English reader would have seen
  // still in English.
  const words = systems.map((s) => ({ slug: s.slug, word: t.eight.names[s.slug].toLowerCase() }));
  const strip = (
    <div className="marquee-strip">
      {words.map(({ slug, word }) => (
        <span key={slug} style={{ display: "contents" }}>
          <span style={slug === "synthesis" ? { color: "var(--star-fill)" } : undefined}>{word}</span>
          <span style={{ color: "rgba(201,174,107,.5)" }} aria-hidden>
            ✦
          </span>
        </span>
      ))}
    </div>
  );
  return (
    <div className="marquee" aria-hidden>
      <div className="marquee-track">
        {strip}
        {strip}
      </div>
    </div>
  );
}

/* ══ I · WHAT IT IS ═══════════════════════════════════════════════ */

export function WhatItIs() {
  const t = useT();
  return (
    <section id="what" className="sec sec-what">
      <Aura tone="violet" size="min(700px,50vw)" top="10%" left="-10%" drift="b" style={{ filter: "blur(36px)" }} />
      <div className="sec-inner">
        <Label m="I" d="I">
          {t.what.label}
        </Label>
        <p className="what-lead">{t.what.lead}</p>
        <div className="what-grid">
          <div className="what-item">
            <div className="what-figure">{t.what.systemsFigure}</div>
            <div>
              <h3 className="what-title">{t.what.systemsTitle}</h3>
              <p className="what-body">
                <span className="only-mobile">{t.what.systemsShort}</span>
                <span className="from-tablet">{t.what.systemsLong}</span>
              </p>
            </div>
          </div>
          <div className="what-divider only-mobile" />
          <div className="what-item">
            <div className="what-figure what-figure-sm">{t.what.freeFigure}</div>
            <div>
              <h3 className="what-title">{t.what.freeTitle}</h3>
              <p className="what-body">
                <span className="only-mobile">{t.what.freeShort}</span>
                <span className="from-tablet">{t.what.freeLong}</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ══ II · FIRST INSIGHT (in-page, mobile section II) ═════════════ */

export function FirstInsight({ revealed }: { revealed: boolean }) {
  const { state } = useJourney();
  const t = useT();
  const insight = insightFor(state.date);

  return (
    <section id="insight" className="sec sec-insight" data-revealed={revealed}>
      <Aura
        tone="indigo"
        size="320px"
        top="26px"
        left="50%"
        style={{ transform: "translateX(-50%)", filter: "blur(26px)" }}
      />
      <div className="sec-inner">
        {/* The one section outside the count, and the only numeral on the page
            with a reason that was never written down.

            Everything else in the spine is a step in an argument — what it is,
            how to read it, the eight, where they agree, the voice, the price,
            the questions. This is not a step; it is the product doing the thing
            while the argument is still going on, and it changes under the
            reader the moment they type a date. The dash says it is not being
            counted.

            It only holds on a wide screen. On a phone the page is one column
            read strictly top to bottom, an unnumbered section between II and
            III reads as a numeral that failed to render, and the spine is the
            only thing telling a reader how far through they are — so the phone
            numbers it II and carries on.

            What was actually broken is that the desktop sections after this one
            kept counting as though the dash had used up a number: the spine
            read I, —, III, IV, V, VI, VII and II appeared at no width at all.
            They are renumbered below, so the dash now sits between I and II
            rather than in place of II. */}
        <Label m="II" d="—">
          {t.insight.label}
        </Label>
        {insight ? (
          <>
            <div className="insight-body">
              <div className="insight-glyph glyph">{insight.sign.glyph}</div>
              <div className="insight-sign">
                {t.insight.sun(t.signs[insight.sign.name as keyof typeof t.signs] ?? insight.sign.name)}
              </div>
              <div className="insight-pills">
                <span className="pill">{t.insight.lifePath(insight.path)}</span>
                <span className="pill">{insight.card.name}</span>
              </div>
            </div>
            {/* True of every chart, unlike the single interpretation that used
                to sit here and described exactly one of them. */}
            <p className="insight-line alma-voice">{t.insight.fromDateAlone}</p>
          </>
        ) : (
          <>
            <div className="insight-body">
              <div className="insight-glyph glyph" style={{ opacity: 0.5 }}>
                ✦
              </div>
            </div>
            <p className="insight-line alma-voice">{t.insight.awaiting}</p>
          </>
        )}
        <a className="btn btn-outline btn-block insight-cta" href="#get-app">
          {t.cta.getApp}
        </a>
      </div>
    </section>
  );
}

/* ══ III · HOW TO READ · parchment (mobile) ═══════════════════════ */

const RULE_NUMERALS = ["I", "II", "III", "IV"];

export function HowToRead() {
  const t = useT();
  return (
    <section className="parch-band only-mobile-block">
      <div className="parch-cap parch-cap-top" aria-hidden />
      <div className="parch-cap parch-cap-bottom" aria-hidden />
      <div className="parch-body">
        <div className="parchment-sweep" aria-hidden />
        <div style={{ position: "relative" }}>
          {/* Through `Label` like every other section head, and numbered III.
              It was a hardcoded `IV` sitting under a comment that said III, and
              since `TheEight` below is also IV the phone's spine read
              I, II, IV, IV, V, VII, VII, VIII — two numerals used twice and two
              never used at all. The numerals are the only spine this page has,
              so a duplicate is the page losing count of itself in front of a
              reader. `m` and `d` are the same value because this whole section
              is `only-mobile-block`; the desktop column takes the parchment at
              `Voice` instead. */}
          <Label m="III" d="III" tone="ink">
            {t.howToRead.label}
          </Label>
          <h3 className="parch-title">{t.howToRead.title}</h3>
          {t.howToRead.rules.map(([title, body], i) => (
            <div key={title}>
              {i > 0 && <div className="parch-rule" />}
              <div className="parch-rule-row">
                <span className="parch-numeral">{RULE_NUMERALS[i]}</span>
                <div>
                  <h4 className="parch-rule-title">{title}</h4>
                  <p className="parch-rule-body">{body}</p>
                </div>
              </div>
            </div>
          ))}
          <p className="parch-note">{t.howToRead.disclaimer}</p>
        </div>
      </div>
    </section>
  );
}

/* ══ IV/III · THE EIGHT ════════════════════════════════════════════ */

/**
 * The art in a system card's circle.
 *
 * Two of these used to be somebody else's chart. The Numerology card carried a
 * hardcoded `7` and the Tarot card a hardcoded `XVII` — the demo person's life
 * path and The Star — which meant a visitor who had typed a date was told *life
 * path 8* in the insight panel and shown a large **7** two sections below it,
 * on the card labelled Numerology, on the same scroll. The dictionary already
 * records that this exact number was cut out of that card's *note* for exactly
 * this reason; the glyph it was cut for survived.
 *
 * So the two that can be computed from a date are, and before there is a date
 * they show the motif with no numeral in it rather than a plausible wrong one.
 * That is the same rule the insight panel follows when it says *nothing above
 * is guessed, so nothing is here yet* — an empty slot is honest and a filled
 * one is a claim.
 *
 * Honest is not the same as absent, and for a while these two were absent. An
 * empty numeral in `NumberGlyph` drew literally nothing: measured on a first
 * visit, the Numerology card held no `<svg>` at all, a blank circle among seven
 * pieces of art, seen by every first-time visitor — which is everybody this
 * page exists for. Both components now draw their instrument when they have no
 * answer: the numerology dial with its nine ticks and the four-pointed star the
 * insight panel uses for *not yet*, and the birth card with an engraved rule
 * where the numeral is struck. Neither shows a number, and neither shows
 * nothing. When a date arrives the figure blooms into the same slot on
 * `art-arrives`, which is the section's whole argument happening in place.
 */
function Motif({ motif }: { motif: string }) {
  const { state } = useJourney();
  const insight = insightFor(state.date);
  switch (motif) {
    case "wheel":
      return <ChartWheelSmall />;
    case "orbits":
      return <Orbits />;
    case "number":
      return <NumberGlyph value={insight ? String(insight.path) : ""} />;
    case "arcana":
      return <ArcanaCard width={106} numeral={insight?.card.numeral ?? ""} />;
    case "two-circles":
      return <TwoCircles />;
    case "globe":
      return <Globe />;
    case "solar":
      return <SolarWheel />;
    default:
      return <NineAxisStar />;
  }
}

export function TheEight() {
  const { ref, index, count, goto } = useRail();
  const t = useT();
  return (
    <section id="eight" className="sec sec-eight">
      <div className="sec-inner">
        <Label m="IV" d="II">
          {t.eight.label}
        </Label>
        <h2 className="sec-title">
          {t.eight.titleA}
          <br className="only-mobile" /> {t.eight.titleB}
        </h2>
      </div>

      {/* Named, because Chrome makes it a tab stop whether or not we ask.
          A horizontally scrollable container with overflow is focusable
          automatically — no author `tabindex` — and it turned up as a real stop
          in the 360 traversal, between the insight CTA and the first dot, with
          `role` null and `aria-label` null. So a screen reader user arrived at
          an element that announced nothing and gave no hint that it scrolled,
          on the way to the dots, which do announce themselves. The name is the
          section's own title rather than a new string: it is already in six
          languages and it is already what this is. */}
      <div
        className="eight-rail rail"
        ref={ref}
        role="group"
        aria-label={`${t.eight.titleA} ${t.eight.titleB}`}
      >
        {systems.map((s) => (
          <article key={s.slug} className="eight-card" data-door={Boolean(s.door)}>
            <ArtCircle>
              <Motif motif={s.motif} />
            </ArtCircle>
            <div className="eight-copy">
              <div className="eight-group">{t.eight.groups[s.group]}</div>
              <h3 className="eight-name">{t.eight.names[s.slug]}</h3>
              <div className="eight-note">{t.eight.notes[s.slug]}</div>
            </div>
          </article>
        ))}
      </div>
      <div className="only-mobile">
        <RailDots
          count={count || systems.length}
          active={index}
          note={t.eight.swipe(systems.length)}
          label={t.eight.goTo}
          onSelect={goto}
        />
      </div>
      <div className="sec-inner from-tablet">
        <p className="eight-tail">{t.eight.tail}</p>
      </div>
    </section>
  );
}

/* ══ V/IV · CROSS-SYNTHESIS ══════════════════════════════════════ */

/**
 * The three axes the panel has room to name. The other six are counted, not
 * listed — see the `+n` row, which does the arithmetic rather than carrying a
 * typed number that stops being true the day a tenth axis is added.
 */
const SHOWN_AXES = ["Direction", "Relationships", "Resources"] as const;

/**
 * The empty instrument, which is what this panel always was underneath.
 *
 * It used to be a finished reading, printed for somebody who had entered
 * nothing: three of four lozenges lit on Direction under `aria-label="3 of 4
 * systems agree"`, a red "2 disagree" tag on Relationships, two of four on
 * Resources, and the sentence *"Your chart wants a witness; your Birth Card
 * wants an open door. Both are true."* — under a heading that says **about
 * you**. Every one of those was a literal in this file. A visitor reasonably
 * reads "2 disagree" as two systems disagreeing about *them*, because that is
 * what the panel is for and what the heading says it is.
 *
 * This is the same class of thing as the invented reviews, the fabricated
 * counts, the pre-filled birth data and the claim of eight agreeing systems
 * that have each already been cut out of this repository, and it survived
 * because it looks like a component rather than like a claim.
 *
 * Driving it from `insight` was the other option and it is not available:
 * `insightFor` has a date and nothing else, and an agreement count across four
 * systems needs a birth time and a place, a full chart, and the backend. The
 * landing genuinely cannot compute this. So the panel does what `NumberGlyph`
 * and `ArcanaCard` two sections above it do — it draws its instrument and not
 * its answer. Four unlit lozenges per axis say *four systems read this one, and
 * none of them has read you yet*; the nine-axis count is real arithmetic on the
 * dictionary; the prose beside it already explains what agreement and
 * disagreement mean. Nothing here is a number about a stranger.
 *
 * The heading keeps "about you". It is the section saying what the product
 * does, in the same voice as "Eight ways to read yourself" at the top of the
 * page — a promise about what a date buys, not a result being displayed. What
 * made the old panel dishonest was the figures under it, and those are gone.
 *
 * `aria-label` on each lozenge group is `insight.awaitingMeta` — "waiting for
 * your date", the phrase the hero already prints where a birthday would go.
 * One state, one sentence, already translated six times: a new string here
 * would be a second way of saying the same thing, which is how two ways of
 * saying it come to disagree. The old labels were hardcoded English as well as
 * false, so a Spanish screen reader heard "3 of 4 systems agree" in English
 * about a chart that did not exist.
 */
/**
 * `tabletOnly` is a boolean and not a `className` string, so that both spellings
 * of this row are written out in full, here, where `display-utilities.test.ts`
 * can read them. A component that takes an arbitrary class name composes it out
 * of sight of any check — the tablet-only row would be `row` in this file and
 * `from-tablet` in the caller, and the pair that breaks the layout would never
 * appear anywhere as a pair. That is precisely how the original defect survived.
 */
function AxisRow({ name, label, tabletOnly }: { name: string; label: string; tabletOnly?: boolean }) {
  return (
    <div className={tabletOnly ? "row from-tablet-flex" : "row"}>
      <span className="synth-axis">{name}</span>
      <span className="lozenges" aria-label={label}>
        <span className="lozenge" />
        <span className="lozenge" />
        <span className="lozenge" />
        <span className="lozenge" />
      </span>
    </div>
  );
}

export function Synthesis() {
  const t = useT();
  // Nine today. The row below says "+6" because six is what is left after the
  // three with room to be named, and it will say "+7" the day a tenth is added
  // without anybody having to remember this line exists.
  const rest = Object.keys(t.synthesis.axes).length - SHOWN_AXES.length;
  return (
    <section className="sec sec-synth">
      <Aura tone="indigo" size="min(760px,52vw)" top="0" right="-10%" drift="a" style={{ filter: "blur(36px)" }} />
      <div className="sec-inner synth-grid">
        <div>
          <Label m="V" d="III">
            {t.synthesis.label}
          </Label>
          <h2 className="sec-title">{t.synthesis.title}</h2>
          <p className="synth-lead">
            <span className="only-mobile">{t.synthesis.leadShort}</span>
            <span className="from-tablet">{t.synthesis.leadLong}</span>
          </p>
        </div>
        <div>
          {/* The third axis is a tablet-and-up row — the phone has room for two.
              It was `.row from-tablet`, and `.from-tablet` sets `display:
              initial`, which for `display` is `inline`: same specificity as
              `.row { display: flex }` and later in the cascade, so from 700 px
              up the row stopped being a row. Measured at 700, 768, 900, 1024 and
              1440: the label and its lozenges stacked, the lozenge group
              stretched the full 298 px column and sat on top of the row's own
              hairline, while "Direction" two rows above was correctly aligned.
              `.from-tablet-flex` exists for exactly this and is used correctly
              one section below, on `.price-row`. */}
          {SHOWN_AXES.map((axis, i) => (
            <AxisRow
              key={axis}
              name={t.synthesis.axes[axis]}
              label={t.insight.awaitingMeta}
              tabletOnly={i === SHOWN_AXES.length - 1}
            />
          ))}
          <div className="row" style={{ borderBottom: "none" }}>
            <span style={{ fontSize: 15, color: "var(--muted-2)" }}>
              <span className="only-mobile">{t.synthesis.moreShort}</span>
              <span className="from-tablet">{t.synthesis.moreLong}</span>
            </span>
            <span style={{ fontSize: 14, color: "var(--gold-bright)" }}>+{rest}</span>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ══ VI/V · ALMA'S VOICE ═════════════════════════════════════════ */

export function Voice() {
  const t = useT();
  const voice = `${t.voice.sample} ${t.voice.sampleTail}`;
  return (
    <>
      {/* mobile: on the night, no parchment (parchment is spent on "how to read") */}
      <section className="sec sec-voice only-mobile-block">
        <div className="sec-inner">
          {/* VI, not VII — `Pricing` below is VII on a phone, and this was the
              second half of the duplicate spine. Same value in both slots
              because this variant is `only-mobile-block`. */}
          <Label m="VI" d="VI">
            {t.voice.label}
          </Label>
          <h3 className="sec-title" style={{ marginBottom: 18 }}>
            {t.voice.title}
          </h3>
          <p className="alma-voice">{voice}</p>
          <div className="rule-fade" style={{ margin: "20px 0" }} />
          <p style={{ fontSize: 14.5, lineHeight: 1.65, color: "var(--muted-2)" }}>
            {t.voice.proofShort}
          </p>
        </div>
      </section>

      {/* tablet & desktop: the parchment band */}
      <section className="parch-band from-tablet-block">
        <div className="parch-cap parch-cap-top parch-cap-wide" aria-hidden />
        <div className="parch-cap parch-cap-bottom parch-cap-wide" aria-hidden />
        <div className="parch-body parch-body-wide">
          <div className="parchment-sweep" aria-hidden />
          <div className="parch-grid">
            <div>
              {/* The desktop half of the same section, numbered V there. This
                  one was already right; it goes through `Label` so that the two
                  variants cannot drift apart the next time either is edited. */}
              <Label m="IV" d="IV" tone="ink">
                {t.voice.label}
              </Label>
              <p className="parch-voice">{voice}</p>
            </div>
            <div>
              <h3 className="parch-side-title">{t.voice.title}</h3>
              <p className="parch-side-body">{t.voice.proofLong}</p>
              <p className="parch-note">{t.howToRead.disclaimer}</p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

/* ══ VII/VI · PRICING ════════════════════════════════════════════ */

export function Pricing() {
  const t = useT();
  const catalogue = useCatalogue();
  return (
    <section id="pricing" className="sec sec-pricing">
      <div className="sec-inner">
        <Label m="VII" d="V">
          {t.pricing.label}
        </Label>
        <h2 className="sec-title" style={{ marginBottom: "clamp(24px,3.4vw,52px)" }}>
          {t.pricing.titleA}
          <br className="to-tablet" /> {t.pricing.titleB}
        </h2>

        <div className="pricing-grid">
          <div>
            {/* Every figure on this page comes from the catalogue endpoint, and
                an unloaded catalogue shows no figure at all. Five prices were
                typed into the dictionaries and all five disagreed with what the
                processor would charge — a $14.99 chart against an $8.99 door, a
                $4.99 chapter that had been withdrawn, and a monthly plan with an
                introductory band that exists nowhere in the price list. A price
                in the interface is a quote. */}
            {/* And a market that is not sold the door is not shown one. The
                five purchasing-power markets carry the archive and the year and
                nothing else, so now that a country actually reaches the
                catalogue — it did not until this release, which is why every
                visitor on earth was quoted dollars — a Brazilian's price list
                has no `natal` row in it. Drawing the row anyway with an empty
                figure would advertise something no store will sell them.
                `offers` answers `true` while the catalogue is still loading, so
                what a slow connection sees is the ordinary blank figure rather
                than a section that assembles itself. */}
            {offers(catalogue, "natal") && (
              <>
                <div className="price-row">
                  <span className="price-name">{t.pricing.natal}</span>
                  <span className="price-figure">{priceOf(catalogue, "natal")}</span>
                </div>
                <p className="price-note">
                  <span className="only-mobile">{t.pricing.natalShort}</span>
                  <span className="from-tablet">{t.pricing.natalLong}</span>
                </p>
                <div className="price-rule" />
              </>
            )}
            {/* The rung above the door is the archive. It replaces the single
                chapter, which was withdrawn with the $4.99 tier. */}
            <div className="price-row from-tablet-flex">
              <span className="price-name">{t.pricing.wholeArchive}</span>
              <span className="price-figure">
                {priceOf(catalogue, "archive") || priceOf(catalogue, "archive-upgrade")}
              </span>
            </div>
            <p className="price-note from-tablet">{t.pricing.archiveNote}</p>
          </div>

          <div style={{ position: "relative" }}>
            <Aura tone="gold" size="116%" top="-20px" left="-8%" style={{ height: 240, filter: "blur(26px)" }} />
            <div style={{ position: "relative" }}>
              {/* There was a gold "most chosen" overline here. Nothing has ever
                  been sold through this code, so it was a popularity claim about
                  a product no one has bought — on the most expensive option, for
                  a brand whose whole argument is that it does not do this. */}
              <div className="price-row">
                <span className="price-name price-name-lg">{t.pricing.everythingYear}</span>
                <span className="price-figure price-figure-lg">
                  {priceOf(catalogue, "annual")}
                </span>
              </div>
              <p className="price-note price-note-lg">
                <span className="only-mobile">{t.pricing.everythingShort}</span>
                <span className="from-tablet">{t.pricing.everythingLong}</span>
              </p>
              {/* Auto-renewal, said next to the price rather than in the terms.
                  ROSCA and California AB 2863 both require the disclosure to be
                  clear and adjacent to the payment; more to the point, a person
                  who finds out a year later that this recurred is a person who
                  was not told. */}
              <p className="price-note">{t.pricing.renewsNote}</p>
              {/* Every price on this page is charged in the app, through Apple
                  and Google. The button hands the reader to the store rather
                  than opening a checkout the website cannot complete. */}
              <a className="btn btn-gold price-cta" href="#get-app">
                {t.cta.getApp}
              </a>
              {/* the honesty plate — full prices, no timers, nothing hidden */}
              <div className="honesty">
                {t.pricing.honesty.map((line) => (
                  <span key={line}>
                    <b>·</b> {line}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ══ VIII/VII · FAQ ═════════════════════════════════════════════════ */

export function Faq() {
  const t = useT();
  const [showAll, setShowAll] = useState(false);
  // Out of the dictionary rather than out of `data.ts`. These six questions
  // shipped in English on all six landings for as long as they were fixtures,
  // because `check-locales.mjs` only reads `src/lib/i18n/` — and one of them is
  // "Will you charge me automatically?", which is a subscription-terms question
  // being answered in a language the reader was not sold in.
  const items = showAll ? t.faq.items : t.faq.items.slice(0, 3);
  return (
    <section id="faq" className="sec sec-faq">
      <div className="faq-inner">
        <Label m="VIII" d="VI">
          {t.faq.label}
        </Label>
        <div className="only-mobile">
          {items.map((f, i) => (
            <Accordion key={f.q} q={f.q} a={f.a} defaultOpen={i === 0} size="m" />
          ))}
        </div>
        <div className="from-tablet">
          {items.map((f, i) => (
            <Accordion key={f.q} q={f.q} a={f.aLong} defaultOpen={i === 0} size="l" />
          ))}
        </div>
        <div style={{ borderTop: "1px solid rgba(237,231,218,.12)" }} />
        {!showAll && (
          <button
            type="button"
            onClick={() => setShowAll(true)}
            style={{
              marginTop: 18,
              background: "none",
              border: 0,
              padding: 0,
              color: "var(--gold-bright)",
              fontSize: 14.5,
              cursor: "pointer",
            }}
          >
            {t.faq.showAll}
          </button>
        )}
      </div>
    </section>
  );
}

/* ══ FINAL ════════════════════════════════════════════════════════ */

/**
 * One row per store. A filled listing URL becomes the store's own badge
 * artwork; an empty one — the truth today — becomes an honest "coming" plate
 * rather than a dead badge that looks tappable and is not. Same rule as the
 * app handoff (`lib/stores.ts`).
 */
function StoreBadge({
  url,
  artwork,
  live,
  soon,
}: {
  url: string;
  artwork: string;
  live: string;
  soon: string;
}) {
  if (!url) {
    return <span className="store-badge-soon">{soon}</span>;
  }
  return (
    <a className="store-badge" href={url} target="_blank" rel="noreferrer">
      <img src={artwork} alt={live} />
    </a>
  );
}

export function FinalCta() {
  const t = useT();
  const published = Boolean(APP_STORE_URL || PLAY_STORE_URL);
  return (
    <section id="get-app" className="sec-final">
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          background: "radial-gradient(60% 70% at 50% 40%, rgba(58,52,132,.5), transparent 68%)",
        }}
        aria-hidden
      />
      <Starfield />
      <Mote top="30%" left="16%" />
      <div className="final-inner">
        <Star size={52} style={{ marginBottom: 26 }} />
        <h2 className="final-title">{t.final.title}</h2>
        <p className="final-sub">{t.app.note}</p>
        <div className="final-stores">
          <StoreBadge
            url={APP_STORE_URL}
            artwork={APP_STORE_BADGE}
            live={t.app.appStore}
            soon={t.app.appleSoon}
          />
          <StoreBadge
            url={PLAY_STORE_URL}
            artwork={PLAY_STORE_BADGE}
            live={t.app.googlePlay}
            soon={t.app.googleSoon}
          />
        </div>
        {!published && <p className="final-store-note">{t.app.notYet}</p>}
        <a className="final-made" href="https://pazl.ai" target="_blank" rel="noreferrer">
          made by pazl.ai
        </a>
      </div>
    </section>
  );
}
