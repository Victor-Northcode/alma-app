import type { CSSProperties } from "react";

/**
 * Ambient sky: two starfield layers, ≤3 dust motes, one comet per screen,
 * at most two aura blobs — never behind body copy.
 * All of it pauses under prefers-reduced-motion (see globals.css).
 */

export function Grain() {
  return <div className="grain" aria-hidden />;
}

export function Starfield({ second = false, style }: { second?: boolean; style?: CSSProperties }) {
  return (
    <>
      <div className="starfield" style={style} aria-hidden />
      {second && <div className="starfield-2" style={style} aria-hidden />}
    </>
  );
}

export function Comet({
  top = "80px",
  left = "14%",
  width = 180,
  duration = 18,
}: {
  top?: string;
  left?: string;
  width?: number;
  duration?: number;
}) {
  return <div className="comet" style={{ top, left, width, animationDuration: `${duration}s` }} aria-hidden />;
}

export function Mote({
  top = "60%",
  left = "8%",
  duration = 14,
  delay = 0,
  color = "#F6E7BC",
  size = 2,
}: {
  top?: string;
  left?: string;
  duration?: number;
  delay?: number;
  color?: string;
  size?: number;
}) {
  return (
    <div
      className="mote"
      style={{
        top,
        left,
        width: size,
        height: size,
        background: color,
        animationDuration: `${duration}s`,
        animationDelay: `${delay}s`,
      }}
      aria-hidden
    />
  );
}

export function Aura({
  tone = "indigo",
  size = "min(900px,64vw)",
  top,
  right,
  bottom,
  left,
  drift,
  style,
}: {
  tone?: "indigo" | "deep" | "gold" | "violet";
  size?: string;
  top?: string;
  right?: string;
  bottom?: string;
  left?: string;
  drift?: "a" | "b";
  style?: CSSProperties;
}) {
  const fill =
    tone === "deep"
      ? "radial-gradient(circle,rgba(30,58,150,.38),transparent 70%)"
      : tone === "gold"
        ? "radial-gradient(circle,rgba(201,174,107,.2),transparent 66%)"
        : tone === "violet"
          ? "radial-gradient(circle,rgba(74,58,158,.34),transparent 68%)"
          : "radial-gradient(circle,rgba(96,78,196,.42) 0%,rgba(58,52,132,.22) 44%,transparent 70%)";

  return (
    <div
      className="aura"
      style={{
        width: size,
        aspectRatio: "1",
        top,
        right,
        bottom,
        left,
        background: fill,
        animation: drift ? `aura${drift.toUpperCase()} ${drift === "a" ? 30 : 36}s ease-in-out infinite` : undefined,
        ...style,
      }}
      aria-hidden
    />
  );
}

/**
 * The parchment band: elliptical edges where it meets night, one light
 * sweep every 11–15 s. The only light surface outside the reader.
 */
export function ParchmentBand({
  children,
  padding = "clamp(28px,3vw,52px) var(--pad)",
}: {
  children: React.ReactNode;
  padding?: string;
}) {
  return (
    <section style={{ position: "relative", margin: "0 0 clamp(64px,7vw,120px)" }}>
      <div
        style={{
          position: "absolute",
          top: "-56px",
          left: "-4%",
          width: "108%",
          height: 120,
          background: "var(--parchment)",
          borderRadius: "50%",
        }}
        aria-hidden
      />
      <div
        style={{
          position: "absolute",
          bottom: "-56px",
          left: "-4%",
          width: "108%",
          height: 120,
          background: "var(--parchment)",
          borderRadius: "50%",
        }}
        aria-hidden
      />
      <div style={{ position: "relative", background: "var(--parchment)", color: "var(--ink)", padding, overflow: "hidden" }}>
        <div className="parchment-sweep" aria-hidden />
        <div style={{ position: "relative", maxWidth: "var(--shell)", margin: "0 auto" }}>{children}</div>
      </div>
    </section>
  );
}
