"use client";

import type { CSSProperties } from "react";

/* ══════════════════════════════════════════════════════════════════
   Six motifs, all in code. No stock imagery, no gradient-mesh JPEGs.
   Each system owns one motif and keeps it everywhere.
   Never scales up: the chart wheel caps at 420.
   ══════════════════════════════════════════════════════════════════ */

const ZODIAC = ["♈︎", "♉︎", "♊︎", "♋︎", "♌︎", "♍︎", "♎︎", "♏︎", "♐︎", "♑︎"];
const ZODIAC_POS: Array<[number, number]> = [
  [165, 40],
  [248, 72],
  [294, 128],
  [294, 212],
  [248, 266],
  [165, 298],
  [82, 266],
  [36, 212],
  [36, 128],
  [82, 72],
];

/** Natal · rotation 140–260 s · rings 1px gold 20–55% · aspects in gold-bright */
export function ChartWheel({
  size,
  spin = 220,
  glyphs = true,
  extraRing = false,
  style,
}: {
  size?: number | string;
  spin?: number;
  glyphs?: boolean;
  extraRing?: boolean;
  style?: CSSProperties;
}) {
  return (
    <svg
      viewBox="0 0 330 330"
      fill="none"
      style={{ width: size ?? "100%", height: size ?? "100%", ...style }}
      aria-hidden
    >
      <g style={{ animation: `spin ${spin}s linear infinite`, transformOrigin: "165px 165px" }}>
        <circle cx="165" cy="165" r="152" stroke="#C9AE6B" strokeOpacity=".4" />
        <circle cx="165" cy="165" r="140" stroke="#C9AE6B" strokeOpacity=".18" />
        <circle cx="165" cy="165" r="98" stroke="#A8873C" strokeOpacity=".3" strokeDasharray="2 5" />
        {extraRing && <circle cx="165" cy="165" r="52" stroke="#C9AE6B" strokeOpacity=".2" />}
        <ellipse cx="165" cy="165" rx="152" ry="58" stroke="#C9AE6B" strokeOpacity=".22" />
        <g stroke="#C9AE6B" strokeOpacity=".22" strokeWidth=".7">
          <path d="M165 13v304M13 165h304M57 57l216 216M273 57L57 273" />
          <path d="M165 25 L286 95 M286 95 L286 235 M286 235 L165 305 M165 305 L44 235 M44 235 L44 95 M44 95 L165 25" />
        </g>
        <g stroke="#F6E7BC" strokeOpacity=".62">
          <path d="M76 92 L118 128 L96 186 L150 214 L212 176" />
          <path d="M118 128 L186 96 L246 124" />
          {extraRing && <path d="M212 176 L262 230" />}
        </g>
        <g fill="#FFF8E6">
          <circle cx="76" cy="92" r="2.6" style={{ animation: "twinkle 4s ease-in-out infinite" }} />
          <circle cx="118" cy="128" r="3.4" style={{ animation: "twinkle 5s ease-in-out .4s infinite" }} />
          <circle cx="96" cy="186" r="2.2" style={{ animation: "twinkle 4.4s ease-in-out .8s infinite" }} />
          <circle cx="150" cy="214" r="3" style={{ animation: "twinkle 5.4s ease-in-out .2s infinite" }} />
          <circle cx="212" cy="176" r="3.8" style={{ animation: "twinkle 4.8s ease-in-out 1s infinite" }} />
          <circle cx="186" cy="96" r="2.4" style={{ animation: "twinkle 4.2s ease-in-out .6s infinite" }} />
          <circle cx="246" cy="124" r="2.8" style={{ animation: "twinkle 5.2s ease-in-out 1.4s infinite" }} />
          {extraRing && <circle cx="262" cy="230" r="2.2" style={{ animation: "twinkle 4.6s ease-in-out .3s infinite" }} />}
        </g>
        {extraRing && (
          <g fill="#C9AE6B" opacity=".8">
            <circle cx="44" cy="140" r="1.3" />
            <circle cx="290" cy="180" r="1.3" />
            <circle cx="132" cy="60" r="1.3" />
            <circle cx="230" cy="286" r="1.3" />
            <circle cx="70" cy="248" r="1.3" />
            <circle cx="300" cy="120" r="1.3" />
          </g>
        )}
        {glyphs && (
          <g fontFamily="Playfair Display" fontSize="15" fill="#C9AE6B" fillOpacity=".85" textAnchor="middle">
            {ZODIAC.map((g, i) => (
              <text key={g} x={ZODIAC_POS[i][0]} y={ZODIAC_POS[i][1]}>
                {g}
              </text>
            ))}
          </g>
        )}
      </g>
    </svg>
  );
}

/** Compact wheel used inside circular art slots and cabinet panels. */
export function ChartWheelSmall({ size = "82%", spin = 140 }: { size?: number | string; spin?: number }) {
  return (
    <svg width={size} viewBox="0 0 180 180" fill="none" aria-hidden>
      <g style={{ animation: `spinBack ${spin}s linear infinite`, transformOrigin: "90px 90px" }}>
        <circle cx="90" cy="90" r="82" stroke="#C9AE6B" strokeOpacity=".55" />
        <circle cx="90" cy="90" r="62" stroke="#A8873C" strokeOpacity=".4" strokeDasharray="2 4" />
        <g stroke="#C9AE6B" strokeOpacity=".3" strokeWidth=".7">
          <path d="M90 8v164M8 90h164M32 32l116 116M148 32L32 148" />
        </g>
        <g stroke="#F6E7BC" strokeOpacity=".8">
          <path d="M52 48 L128 112 M128 112 L70 132 M70 132 L52 48" />
        </g>
        <g fill="#FFF8E6">
          <circle cx="52" cy="48" r="3.4" />
          <circle cx="128" cy="112" r="3.4" />
          <circle cx="70" cy="132" r="3.4" />
        </g>
      </g>
    </svg>
  );
}

/** Transits · counter-rotation 26 / 40 s · max 3 ellipses per scene */
export function Orbits({ size = "82%" }: { size?: number | string }) {
  return (
    <svg width={size} viewBox="0 0 180 180" fill="none" aria-hidden>
      <ellipse cx="90" cy="90" rx="78" ry="30" stroke="#C9AE6B" strokeOpacity=".5" />
      <ellipse cx="90" cy="90" rx="58" ry="58" stroke="#A8873C" strokeOpacity=".32" strokeDasharray="2 5" />
      <ellipse cx="90" cy="90" rx="30" ry="72" stroke="#C9AE6B" strokeOpacity=".3" />
      <g style={{ animation: "spin 26s linear infinite", transformOrigin: "90px 90px" }}>
        <circle cx="168" cy="90" r="4.4" fill="#F6E7BC" />
      </g>
      <g style={{ animation: "spinBack 40s linear infinite", transformOrigin: "90px 90px" }}>
        <circle cx="90" cy="18" r="3" fill="#C9AE6B" />
      </g>
      <circle cx="90" cy="90" r="13" fill="#F1DFAE" />
    </svg>
  );
}

/** Compatibility · shared lens at 14% · never overlapping faces or hearts */
export function TwoCircles({ size = "82%" }: { size?: number | string }) {
  return (
    <svg width={size} viewBox="0 0 180 180" fill="none" aria-hidden>
      <circle cx="70" cy="90" r="46" stroke="#C9AE6B" strokeOpacity=".62" />
      <circle cx="110" cy="90" r="46" stroke="#E4D3A2" strokeOpacity=".62" />
      <path d="M90 47 a46 46 0 0 1 0 86 a46 46 0 0 1 0 -86" fill="#F6E7BC" fillOpacity=".14" />
      <circle cx="70" cy="90" r="3.4" fill="#F6E7BC" />
      <circle cx="110" cy="90" r="3.4" fill="#F6E7BC" />
    </svg>
  );
}

/** Astrocartography · graticule at 32% · planetary lines 1.2 px star-fill */
export function Globe({ size = "82%" }: { size?: number | string }) {
  return (
    <svg width={size} viewBox="0 0 180 180" fill="none" aria-hidden>
      <circle cx="90" cy="90" r="72" stroke="#C9AE6B" strokeOpacity=".55" />
      <g stroke="#C9AE6B" strokeOpacity=".32">
        <path d="M18 90h144M90 18c26 24 26 120 0 144M90 18c-26 24-26 120 0 144M32 48c34 16 82 16 116 0M32 132c34-16 82-16 116 0" />
      </g>
      <g stroke="#F6E7BC" strokeOpacity=".85" strokeWidth="1.2">
        <path d="M60 20c-8 44-8 96 0 140M124 24c6 42 6 90 0 132" />
      </g>
      <circle cx="60" cy="76" r="3.6" fill="#F6E7BC" />
    </svg>
  );
}

/** Solar return · the only system that keeps rays. */
export function SolarWheel({ size = "82%" }: { size?: number | string }) {
  return (
    <svg width={size} viewBox="0 0 180 180" fill="none" aria-hidden>
      <g stroke="#C9AE6B" strokeOpacity=".6" strokeLinecap="round">
        <path d="M90 12v22M90 146v22M12 90h22M146 90h22M35 35l16 16M129 129l16 16M145 35l-16 16M51 129l-16 16" />
      </g>
      <circle cx="90" cy="90" r="52" stroke="#A8873C" strokeOpacity=".35" strokeDasharray="2 5" />
      <circle cx="90" cy="90" r="30" fill="#F1DFAE" />
      <circle cx="82" cy="82" r="10" fill="#FFF8E6" opacity=".5" />
    </svg>
  );
}

/**
 * Birth card · 112×158, arch top, engraved water lines, roman numeral.
 * Own art only — never Rider–Waite.
 */
/**
 * A tarot card back, with a numeral on it when there is one to put there.
 *
 * The default was `"XVII"` — The Star, the demo person's birth card — which is
 * a fixture shown to a stranger under the words "your sky". It defaults to
 * nothing now, and the caller passes the numeral it has computed from a real
 * date; the card is still a card without it, which is the point.
 *
 * Without a numeral the plate at the foot of the card carries an engraved rule
 * instead — the blank line on a certificate, which says *a name belongs here
 * and has not been written yet*. An empty `<text>` said the same thing by
 * saying nothing, and nothing is indistinguishable from a card that forgot to
 * render. The rule is the honest half of the promise the section makes: give it
 * a date and this fills in.
 */
export function ArcanaCard({ width = 106, numeral = "" }: { width?: number; numeral?: string }) {
  const height = Math.round((width / 106) * 150);
  return (
    <div
      style={{
        width,
        height,
        borderRadius: `${Math.round(width * 0.5)}px ${Math.round(width * 0.5)}px 8px 8px`,
        overflow: "hidden",
        border: "1px solid rgba(201,174,107,.6)",
        background: "linear-gradient(170deg,#1A2148,#070B1A)",
        position: "relative",
      }}
      aria-hidden
    >
      <svg width={width} height={height} viewBox="0 0 106 150" fill="none" style={{ position: "absolute", inset: 0 }}>
        <g stroke="#C9AE6B" strokeOpacity=".45" strokeWidth=".7">
          <path d="M8 92c12-8 24-8 36 0s24 8 36 0 18-6 18-6M8 106c12-8 24-8 36 0s24 8 36 0 18-6 18-6M8 120c12-8 24-8 36 0s24 8 36 0 18-6 18-6" />
        </g>
        <path d="M53 26 L56.4 40.6 L71 44 L56.4 47.4 L53 62 L49.6 47.4 L35 44 L49.6 40.6 Z" fill="#F6E7BC" />
        {numeral ? (
          <text
            x="53"
            y="140"
            textAnchor="middle"
            fontFamily="Playfair Display"
            fontSize="11"
            letterSpacing="2"
            fill="#C9AE6B"
            className="art-arrives"
          >
            {numeral}
          </text>
        ) : (
          <line x1="41" y1="137" x2="65" y2="137" stroke="#C9AE6B" strokeOpacity=".38" strokeWidth=".9" />
        )}
      </svg>
    </div>
  );
}

/**
 * Cross-synthesis · nine spokes, nine identical nodes, one gold.
 *
 * This used to read "green agree · red conflict · gold single. Node radius
 * encodes system count", and it did exactly that: four nodes in `#8FBF9A` and
 * two in `#E0917F` — the product's `--agree` and `--disagree` tokens — at two
 * different radii. Two rules broken at once, in one small drawing.
 *
 * It was the only one of the eight cards that left the gold. Enumerating the
 * computed fills of all eight SVGs: seven use C9AE6B / A8873C / F6E7BC /
 * E4D3A2 / FFF8E6 and nothing else; the eighth added a green and a salmon. In
 * a row that is meant to read as eight facets of one material, the coloured
 * one pulls the eye immediately at 700 and 768 — it looks like the card that
 * was not finished, which is the opposite of what a synthesis card should say.
 *
 * And the encoding was a reading. Four axes agreeing and two in conflict is a
 * specific claim about a specific chart, drawn for a visitor who has entered no
 * birth data, in the section whose closing sentence is "every one of the eight
 * is calculated free". The card next to it — the numerology dial — settled this
 * question already: nine ticks, none of them ever lit, because lighting one
 * would be inventing an answer by another means. Nine identical nodes here for
 * the same reason. The instrument has nine axes; which of them agree is what a
 * date buys.
 *
 * The semantic colours are not kept behind a prop for a future in-app view.
 * Nothing in this codebase renders one — the cabinet went to the native apps,
 * which draw their own — so a `semantic` flag would be a branch with no caller,
 * carrying the exact pair of hues that had to be removed. When a screen exists
 * that has real agreement counts to show, it can ask for them then, against
 * whatever design that screen turns out to need.
 */
export function NineAxisStar({
  size = "82%",
  spin,
  pulse = false,
}: {
  size?: number | string;
  spin?: number;
  pulse?: boolean;
}) {
  return (
    <svg width={size} viewBox="0 0 220 220" fill="none" aria-hidden>
      {spin && (
        <g style={{ animation: `spin ${spin}s linear infinite`, transformOrigin: "110px 110px" }}>
          <circle cx="110" cy="110" r="100" stroke="#C9AE6B" strokeOpacity=".32" />
          <circle cx="110" cy="110" r="74" stroke="#C9AE6B" strokeOpacity=".2" strokeDasharray="2 5" />
          <circle cx="110" cy="110" r="46" stroke="#C9AE6B" strokeOpacity=".16" />
        </g>
      )}
      <g stroke="#C9AE6B" strokeOpacity=".3">
        <path d="M110 110 L110 10 M110 110 L174 33 M110 110 L208 78 M110 110 L188 168 M110 110 L143 205 M110 110 L77 205 M110 110 L32 168 M110 110 L12 78 M110 110 L46 33" />
      </g>
      {/* Nine, all the same size, at the end of the nine spokes. Equal radii
          are the point: a larger node was "more systems read this axis", which
          is a measurement, and there is nothing here to measure yet. */}
      <g fill="#E4D3A2">
        <circle cx="110" cy="16" r="4.6" />
        <circle cx="170" cy="38" r="4.6" />
        <circle cx="204" cy="80" r="4.6" />
        <circle cx="184" cy="164" r="4.6" />
        <circle cx="140" cy="198" r="4.6" />
        <circle cx="80" cy="198" r="4.6" />
        <circle cx="36" cy="164" r="4.6" />
        <circle cx="18" cy="80" r="4.6" />
        <circle cx="50" cy="38" r="4.6" />
      </g>
      <circle cx="110" cy="110" r="7" fill="#F6E7BC" />
      {pulse && (
        <circle
          cx="110"
          cy="110"
          r="18"
          stroke="#F6E7BC"
          strokeOpacity=".4"
          style={{ animation: "ripple 6s ease-out infinite", transformOrigin: "110px 110px" }}
        />
      )}
    </svg>
  );
}

/**
 * Numerology · an engraved dial with the visitor's life path in the middle of
 * it, and the dial alone until there is one.
 *
 * The default was `"7"`, which is the demo person's life path and was being
 * shown beside the words "your sky" to people whose life path is not 7. That
 * number is gone and must not come back in any form — not as a default, not as
 * a faint "example", not as a greyed-out digit behind the real one. A plausible
 * number is a claim whether or not it is dimmed.
 *
 * But what replaced it was an empty string in a `<div>`, and a `<div>` holding
 * an empty string draws nothing at all. Measured on a first visit: the
 * Numerology card contained no `<svg>` and no ink of any kind — a blank circle
 * in a row of seven pieces of art, on the section that exists to show a
 * stranger what the eight systems look like. Every first visitor saw it,
 * because before a date there is no visitor who does not.
 *
 * So the card draws its instrument rather than its answer. Nine ticks, because
 * numerology reduces to nine numbers; two engraved rings, in the same hairline
 * gold the chart wheel and the solar wheel are drawn in, so the numerology card
 * reads as one of a set rather than as a typographic accident among six pieces
 * of line art. The ticks are the same nine at every reading and mark nothing —
 * they are the face of the dial, not a needle pointing at an answer, which is
 * why none of them is ever lit. Lighting one would be inventing a number by
 * another means, and master numbers (11, 22, 33) do not sit on a nine-tick face
 * anyway.
 *
 * The middle is the only part that changes, and the change is the argument.
 * With a date it holds the number, in Playfair, in the gold everything computed
 * is set in, arriving on `art-arrives` so the moment reads as the dial
 * resolving rather than as a repaint. Same dial, same place, one thing swapped:
 * which is exactly what happened.
 *
 * With no date it holds an empty bezel — two hairline circles with nothing
 * between them, the setting a numeral is struck into, drawn in the engraving
 * language the rest of the dial is already in.
 *
 * It held the four-pointed star first, on the argument that the page should
 * have one visual word for not-knowing. The argument was right and the place
 * was wrong: Birth Card carries that same star permanently, and the two sit
 * side by side in both the three-column and the four-column layouts, so the
 * empty state — the state every first-time visitor is in — showed the identical
 * figure as the focal point of two adjacent cards. Eight distinct traditions
 * read as two unfinished tiles. The star is also the hero's centre glyph and
 * the insight panel's waiting mark, which is three appearances before anybody
 * has typed anything. One word for not-knowing is worth keeping; using it in
 * two touching cards is what it costs.
 *
 * Two circles rather than one, because one reads as a zero — which is a digit,
 * on a card whose whole subject is a digit. Two concentric hairlines read as a
 * frame around an absence, which is what this is.
 *
 * The rings and ticks are also drawn at the weight `ChartWheelSmall` uses next
 * door (.5 / .3 / .48, against its .55 / .4 / .3). They were .26 / .16 / .3 and
 * measurably the quietest art of the eight: a dial that faint beside the natal
 * chart at 768 and 1024 does not read as restraint, it reads as unfinished.
 */
export function NumberGlyph({ value = "", size = "76%" }: { value?: string; size?: number | string }) {
  // Nine ticks, 40° apart, the first at twelve o'clock. Rounded so the server
  // and the browser write byte-identical path data.
  const ticks = Array.from({ length: 9 }, (_, i) => {
    const a = ((i * 40 - 90) * Math.PI) / 180;
    const r = (k: number) => [100 + k * Math.cos(a), 100 + k * Math.sin(a)].map((n) => n.toFixed(2));
    const [x1, y1] = r(83);
    const [x2, y2] = r(92);
    return { x1, y1, x2, y2 };
  });
  return (
    <svg width={size} viewBox="0 0 200 200" fill="none" aria-hidden>
      <circle cx="100" cy="100" r="83" stroke="#C9AE6B" strokeOpacity=".5" />
      <circle cx="100" cy="100" r="62" stroke="#C9AE6B" strokeOpacity=".3" strokeDasharray="2 6" />
      <g stroke="#C9AE6B" strokeOpacity=".48" strokeWidth="1.2">
        {ticks.map((t) => (
          <line key={t.x1 + t.y1} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2} />
        ))}
      </g>
      {value ? (
        <text
          x="100"
          y="100"
          textAnchor="middle"
          dominantBaseline="central"
          fontFamily="var(--serif)"
          fontSize="86"
          fill="#E4D3A2"
          className="art-arrives"
          style={{ filter: "drop-shadow(0 0 18px rgba(228,211,162,.45))" }}
        >
          {value}
        </text>
      ) : (
        <g stroke="#C9AE6B" fill="none">
          <circle cx="100" cy="100" r="34" strokeOpacity=".42" />
          <circle cx="100" cy="100" r="30" strokeOpacity=".24" />
        </g>
      )}
    </svg>
  );
}

/** The circular art slot every system card sits in. Art is circular — always. */
export function ArtCircle({
  children,
  size,
  style,
}: {
  children: React.ReactNode;
  size?: number | string;
  style?: CSSProperties;
}) {
  return (
    <div
      style={{
        position: "relative",
        width: size ?? "100%",
        height: typeof size === "number" ? size : undefined,
        aspectRatio: typeof size === "number" ? undefined : "1",
        borderRadius: "50%",
        overflow: "hidden",
        background: "radial-gradient(circle at 50% 40%,rgba(96,78,196,.42),#080C1E 74%)",
        display: "grid",
        placeItems: "center",
        boxShadow: "0 18px 40px rgba(0,0,0,.45)",
        flex: "0 0 auto",
        ...style,
      }}
    >
      {children}
    </div>
  );
}
