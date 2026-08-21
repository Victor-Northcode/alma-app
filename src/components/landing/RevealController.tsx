"use client";

import { useEffect } from "react";

/**
 * Scroll-reveal, added from the client so it can never hide content.
 *
 * Nothing is hidden in the markup — the page is fully visible without
 * JavaScript and to a crawler. On mount this finds the sections that are still
 * *below the fold*, marks only those to animate, and reveals each as it scrolls
 * into view. Anything already on screen at load is left untouched, so there is
 * no flash of hide-then-show for the first screen; the effect only ever adds
 * motion to things a reader has not seen yet. A reader who has asked for
 * stillness gets none of it — the reduced-motion check returns early.
 */
export function RevealController() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const targets = Array.from(
      document.querySelectorAll<HTMLElement>(
        ".landing .sec, .landing .sec-final, .landing .parch-band, .landing .marquee, .landing .footer",
      ),
    );
    if (!targets.length) return;

    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add("reveal-in");
            io.unobserve(e.target);
          }
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.08 },
    );

    const foldish = window.innerHeight * 0.9;
    for (const el of targets) {
      if (el.getBoundingClientRect().top > foldish) {
        el.classList.add("reveal");
        io.observe(el);
      }
    }

    return () => io.disconnect();
  }, []);

  return null;
}
