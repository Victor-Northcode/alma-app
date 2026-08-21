"use client";

import { Grain } from "@/components/sky/Sky";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RevealController } from "./RevealController";
import {
  Faq,
  FinalCta,
  Hero,
  HowToRead,
  Marquee,
  Pricing,
  TheEight,
  Voice,
  WhatItIs,
} from "./sections";

/**
 * The landing, as a marketing page and nothing more.
 *
 * The in-browser reading — the journey overlay, the sticky call-to-action bar,
 * the birth-date capture in the hero — used to live here. The product is read
 * and sold in the app now, through Apple and Google, so the website's one job
 * is to explain what Alma is and hand the visitor to the store. Every gold
 * control on the page is an anchor to `#get-app` (the closing section), and the
 * interactive machinery that opened a session the site can no longer keep is
 * gone. The eight-systems art still draws its instruments without a date in
 * them — honest, and the same "we have not met you yet" state it always fell
 * back to.
 */
export function LandingShell() {
  return (
    <>
      <Grain />
      <RevealController />
      <div className="landing">
        <Nav />
        <Hero />
        <Marquee />
        <WhatItIs />
        <TheEight />
        <HowToRead />
        <Voice />
        <Pricing />
        <Faq />
        <FinalCta />
        <Footer />
      </div>
    </>
  );
}
