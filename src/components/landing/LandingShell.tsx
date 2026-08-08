"use client";

import { useEffect, useRef, useState } from "react";
import { Grain } from "@/components/sky/Sky";
import { JourneyOverlay } from "@/components/journey/JourneyOverlay";
import { barVisible } from "@/lib/cta-bar";
import { useJourney } from "@/lib/journey-store";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import {
  CtaBar,
  Faq,
  FinalCta,
  FirstInsight,
  Hero,
  HowToRead,
  Marquee,
  Pricing,
  Synthesis,
  TheEight,
  Voice,
  WhatItIs,
} from "./sections";

export function LandingShell() {
  const { open } = useJourney();
  const [barShown, setBarShown] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const insightRef = useRef<HTMLDivElement>(null);

  /**
   * The bar appears after 560 px of scroll and hides again near the footer, so
   * it never covers the legal block — but each of those two edges is a band
   * rather than a line, and the bands and their reasoning now live in
   * `lib/cta-bar.ts`.
   *
   * They were four literals inside this listener, which is the one place they
   * cannot be checked: a scroll handler is only true while somebody is
   * scrolling, and the case that matters is a trackpad drifting two pixels
   * across a boundary. As a pure function the rule can be walked in both
   * directions by a test, which is what `cta-bar.test.ts` does.
   *
   * `setBarShown` takes the previous value rather than reading state through
   * the closure: this listener is registered once and would otherwise be
   * looking at the `barShown` of the first render forever. It is also what
   * makes the hysteresis possible at all — the answer depends on which way the
   * question is being asked.
   *
   * `scrollHeight` is read on every event on purpose. The FAQ's "show all"
   * adds three accordions and the page grows under a reader who is standing
   * still; a height cached at mount would put the footer edge in the wrong
   * place for the rest of the session.
   */
  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY;
      const bottom = document.documentElement.scrollHeight - window.innerHeight - y;
      setBarShown((shown) => barVisible(shown, y, bottom));
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    /* Also on resize: rotating a phone changes `innerHeight` and the document's
       height at once, and without this the footer edge is measured against the
       previous orientation until the next scroll event. */
    window.addEventListener("resize", onScroll);
    onScroll();
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  /* The hero button reveals the first insight in-page — no page load. */
  function reveal() {
    setRevealed(true);
    requestAnimationFrame(() => {
      insightRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  return (
    <>
      <Grain />
      {/*
        `inert` while the journey is open, which is the half of `role="dialog"`
        that was declared and not implemented.

        The overlay says `aria-modal="true"`, covers the viewport at z-index 70
        and stops the body scrolling — and left all 39 controls behind it in the
        tab order. Measured with the overlay open at step II: 45 tabbable
        elements on the page, 6 of them inside the dialog, and the dialog's own
        name field was tab stop 40. So a keyboard or screen-reader user tabbed
        straight out of the journey into the nav, the hero's date fields, five
        in-page CTAs and the footer — content that is invisible and cannot be
        scrolled to.

        One attribute rather than a focus trap: `inert` removes the subtree from
        the tab order *and* from the accessibility tree, which is exactly what
        `aria-modal` is promising, and it cannot fall out of step with the DOM
        the way a hand-written trap does when somebody adds a control. React 19
        takes it as a boolean.

        The sticky bar is outside this element and answers the same way for the
        same reason: `visible` is `barShown && !open`, and `CtaBar` puts
        `inert` on itself whenever it is not visible.
      */}
      <div className="landing" data-dim={open} inert={open}>
        <Nav />
        <Hero onReveal={reveal} />
        <Marquee />
        <WhatItIs />
        <div ref={insightRef}>
          <FirstInsight revealed={revealed} />
        </div>
        <HowToRead />
        <TheEight />
        <Synthesis />
        <Voice />
        <Pricing />
        <Faq />
        <FinalCta />
        <Footer />
      </div>
      {/*
        The bar leaves when the journey opens, and it leaves rather than
        vanishing.

        It sits outside the `inert` wrapper because it is chrome, not page — so
        unlike everything above it, it would still be focusable and still be
        announced with the dialog open. `visible` carries `!open`, and `CtaBar`
        turns that into `inert` on itself plus `pointer-events: none`, which is
        the same one-attribute answer the wrapper above uses.

        Left visible it would also be a second gold call to action underneath a
        modal that is already asking the same question, which is the confusion
        the five doors were unified to end.

        Its exit is 420 ms and the overlay's rise is 380 ms, both on the same
        curve; the overlay is opaque and forty layers above it, so what the exit
        actually buys is the *return*. Closing the journey without finishing it
        puts the reader back exactly where they were, and the bar sliding back
        up is the page saying the door is still open — where a bar snapping into
        existence would read as a new thing appearing.
      */}
      <CtaBar visible={barShown && !open} />
      <JourneyOverlay />
    </>
  );
}
