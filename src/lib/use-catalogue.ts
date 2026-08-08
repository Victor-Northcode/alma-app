"use client";

/**
 * The price list, read from the one place that knows it.
 *
 * Every price the interface shows has to be a price the processor will take,
 * and the only way to keep that true is for both to come from the same row of
 * the catalogue. Typing a number into the interface makes it a quote — and five
 * of them had already come apart: the landing advertised a $14.99 chart against
 * a $8.99 door, a $4.99 chapter that no longer exists, and a "$9.99 · first
 * month $4.99 · $49.99 a year" plan against a catalogue that sells $9.99 a
 * month and $78.99 a year with no introductory band at all. The primary call to
 * action read "Start for $4.99" for an offer nothing could sell.
 *
 * So there are no prices in the dictionaries any more. A screen that has not
 * loaded the catalogue shows no figure rather than a remembered one: an absent
 * price is a moment of nothing, and a wrong price is a number somebody decides
 * to pay against.
 *
 * The response also carries who is taking the money — `provider`, `merchant`,
 * and whether that processor can open a checkout without an email address —
 * because all three are server configuration and none of them is a build-time
 * constant. `requires_email` in particular is the difference between asking for
 * an address because the API needs one and asking for it because a form was
 * built that way.
 */

import { useEffect, useState } from "react";

import { api, isOk } from "./api";

export interface CatalogueItem {
  slug: string;
  /** The system it unlocks, or "*" for everything. */
  system: string;
  name: string;
  kind: string;
  /** "" | "month" | "year" — anything non-empty means this recurs. */
  interval: string;
  scope: string;
  cents: number;
  display: string;
  /** Set on a substituted entry: which shelf price this stands in for. */
  replaces?: string;
  credit_cents?: number;
}

export interface Catalogue {
  currency: string;
  items: CatalogueItem[];
  /** Which processor is live. The client opens the SDK this names, or refuses. */
  provider: string;
  /** Whether that processor cannot create a session without a buyer's address. */
  requiresEmail: boolean;
  /** The company that legally sells — the merchant of record on the statement. */
  merchant: string;
  unlocked: string[];
}

function read(payload: Record<string, unknown>): Catalogue {
  const rows = Array.isArray(payload.items) ? payload.items : [];
  return {
    currency: String(payload.currency ?? "USD"),
    items: rows.map((row) => {
      const it = (row ?? {}) as Record<string, unknown>;
      return {
        slug: String(it.slug ?? ""),
        system: String(it.system ?? ""),
        name: String(it.name ?? ""),
        kind: String(it.kind ?? ""),
        interval: String(it.interval ?? ""),
        scope: String(it.scope ?? ""),
        cents: typeof it.cents === "number" ? it.cents : 0,
        display: String(it.display ?? ""),
        replaces: typeof it.replaces === "string" ? it.replaces : undefined,
        credit_cents: typeof it.credit_cents === "number" ? it.credit_cents : undefined,
      };
    }),
    provider: String(payload.provider ?? ""),
    // Defaulting to `false` rather than `true`: a processor that does not need
    // an address must not be given a mandatory field, because that field is the
    // most expensive wall in the funnel and this product deliberately lets a
    // guest buy. If the guess is wrong the server says `email_required` and the
    // interface reveals the field then.
    requiresEmail: payload.requires_email === true,
    merchant: String(payload.merchant ?? ""),
    unlocked: Array.isArray(payload.unlocked) ? payload.unlocked.map(String) : [],
  };
}

/**
 * Fetch the price list once per mounted screen.
 *
 * Deliberately not cached across screens: a stale price is worse than a second
 * request, and the two places this is used — the landing and the paywall — are
 * both moments where somebody is about to decide to spend money.
 *
 * ── `country` is optional and the web deliberately never passes one ────────
 * It used to be optional and *nobody* passed one, which is a different thing:
 * `currency_for(None)` answers USD, so every visitor on earth was quoted
 * dollars and a German read `$5.99` for a door that costs `€6.49`. The fix is
 * not for this hook to start guessing. A browser cannot determine what country
 * it is in — `navigator.language` is a language, and a timezone is shared by
 * fourteen countries — and anything it did guess would arrive on the wire as a
 * value a reader could edit, which for a price list means choosing your own
 * market.
 *
 * The server sees the country first and for free, off the edge in front of it
 * (`backend/alma/region.py`). So the answer to "which currency" comes back with
 * the price list rather than being sent up with the request, and this argument
 * survives for the one caller that legitimately knows better than the network:
 * a store client that has been told its own storefront region.
 */
export function useCatalogue(country?: string): Catalogue | null {
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null);
  useEffect(() => {
    let live = true;
    void api.catalogue(country).then((result) => {
      if (live && isOk(result)) setCatalogue(read(result.data));
    });
    return () => {
      live = false;
    };
  }, [country]);
  return catalogue;
}

/** One price, or an empty string. Never a fallback figure. */
export function priceOf(catalogue: Catalogue | null, slug: string): string {
  return catalogue?.items.find((item) => item.slug === slug)?.display ?? "";
}

/**
 * Whether this market is sold this product at all.
 *
 * Distinct from `priceOf` returning `""`, and the distinction only became
 * visible once a country actually reached the catalogue. The five
 * purchasing-power markets carry the archive and the year and nothing else — a
 * PPP-fair door is small enough that local VAT plus the flat per-transaction
 * fee eats a third of it — so a Brazilian's price list has no `natal` row in
 * it. A screen that draws the row anyway with a blank figure is advertising
 * something no store will sell them, which is worse than not mentioning it.
 *
 * **An unloaded catalogue answers `true`**, and that is the honest default
 * rather than a convenient one: before the request comes back we do not know
 * which market this is, and the overwhelming majority of them do sell the door.
 * The row is drawn with no figure in it — which is what every price on this
 * page does while it is loading — and disappears only if the answer says it
 * does not exist here. The alternative, hiding every row until the catalogue
 * lands, would blank the pricing section on a slow connection for everybody in
 * the world to spare five markets a moment of a row they will not be offered.
 */
export function offers(catalogue: Catalogue | null, slug: string): boolean {
  if (catalogue === null) return true;
  return catalogue.items.some((item) => item.slug === slug);
}
