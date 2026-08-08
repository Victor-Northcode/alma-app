"use client";

import { useId } from "react";

type Variant = "gold" | "ink" | "flat";

/**
 * The mark: a four-pointed star drawn by hand — thick arms, short points,
 * slightly off-axis so it never reads as a generated sparkle.
 * Never in a circle, never rotated, never used as a bullet or a loader.
 */
export function Star({
  size = 26,
  variant = "gold",
  className,
  style,
}: {
  size?: number;
  variant?: Variant;
  className?: string;
  style?: React.CSSProperties;
}) {
  const id = useId().replace(/:/g, "");
  const body =
    "M32.4 6.4 Q35.6 22.8 41.2 26.6 Q47 30 57.8 31.9 Q47 34 41 37.4 Q35.4 41 32 57.6 Q28.6 41.2 23 37.6 Q17 34.2 6.2 32.1 Q17.2 29.8 23.2 26.4 Q28.8 22.6 32.4 6.4 Z";
  const inner =
    "M32.2 13 Q34.4 26.6 37.6 29.8 Q34.2 34.8 32 51 Q29.8 34.8 26.6 30 Q30 26.8 32.2 13 Z";

  if (variant === "flat") {
    return (
      <svg width={size} height={size} viewBox="0 0 64 64" fill="none" className={className} style={style} aria-hidden>
        <path d={body} fill="#e0c077" />
      </svg>
    );
  }

  const stops =
    variant === "ink"
      ? [
          ["0%", "#C2A868"],
          ["42%", "#94773A"],
          ["100%", "#5E4B20"],
        ]
      : [
          ["0%", "#FBEDC4"],
          ["34%", "#E0C077"],
          ["70%", "#B3913F"],
          ["100%", "#8A6F2E"],
        ];

  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" className={className} style={style} aria-hidden>
      <defs>
        <linearGradient id={id} x1="20%" y1="0%" x2="80%" y2="100%">
          {stops.map(([offset, color]) => (
            <stop key={offset} offset={offset} stopColor={color} />
          ))}
        </linearGradient>
      </defs>
      <path
        d={body}
        fill={`url(#${id})`}
        stroke={variant === "ink" ? "#4A3A16" : "#7A6129"}
        strokeWidth={variant === "ink" ? 0.9 : 0.8}
        strokeLinejoin="round"
      />
      <path d={inner} fill={variant === "ink" ? "#3A2D11" : "#8A6F2E"} fillOpacity={variant === "ink" ? 0.28 : 0.16} />
    </svg>
  );
}

/**
 * Lockup: mark height = cap height × 1.05, tracking .34em with a matching
 * padding-left so the word stays optically centred.
 */
export function Wordmark({
  size = 19,
  starSize,
  tracking = "0.34em",
  className,
}: {
  size?: number;
  starSize?: number;
  tracking?: string;
  className?: string;
}) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 11 }} className={className}>
      <Star size={starSize ?? Math.round(size * 1.35)} />
      <span
        style={{
          fontFamily: "var(--serif)",
          fontSize: size,
          letterSpacing: tracking,
          color: "var(--ink-light)",
          paddingLeft: tracking,
        }}
      >
        ALMA
      </span>
    </span>
  );
}

/** Alma's presence: 96 / 56 / 24 px. Rings drop below 56. */
export function AlmaAvatar({
  size = 56,
  ring = true,
  ringSize,
  className,
}: {
  size?: number;
  ring?: boolean;
  ringSize?: number;
  className?: string;
}) {
  const outer = ringSize ?? Math.round(size * 1.5);
  return (
    <span
      className={className}
      style={{
        position: "relative",
        width: ring ? outer : size,
        height: ring ? outer : size,
        display: "grid",
        placeItems: "center",
        flex: "0 0 auto",
      }}
      aria-hidden
    >
      {ring && size >= 56 && (
        <span
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            border: "1px solid rgba(228,211,162,.3)",
            animation: "ripple 8s ease-out infinite",
          }}
        />
      )}
      <span
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          background:
            "radial-gradient(circle at 42% 38%,#FFF6DF,#F1DFAE 34%,rgba(201,174,107,.45) 64%,transparent 80%)",
          boxShadow: `0 0 ${Math.round(size * 0.54)}px rgba(228,211,162,.34)`,
          animation: "breathe 6s ease-in-out infinite",
        }}
      />
    </span>
  );
}
