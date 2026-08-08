import type { ReactNode } from "react";
import { CONTACT, LEGAL_UPDATED, OPERATOR } from "@/lib/legal";

/**
 * The pieces a legal document is made of.
 *
 * These are server components with no state — a document does not move. They
 * exist so the five pages read as documents in the source too, which is the
 * only way anyone will notice that a sentence has gone wrong. Everything here
 * is ink on parchment; the night canvas stops at the door of these pages.
 */

/**
 * The head of every document: what it is, when it was written, and the
 * admission that it has not been through a lawyer.
 *
 * That admission is not decoration. Publishing plain-language policy that
 * reads like settled law, before it has been reviewed per jurisdiction, is
 * exactly the kind of confident wrongness this product is supposed to avoid.
 */
export function DocHead({ title, lead }: { title: string; lead: string }) {
  return (
    <>
      <div className="legal-eyebrow">Alma · {OPERATOR}</div>
      <h1 className="legal-title">{title}</h1>
      <div className="legal-updated">Last updated {LEGAL_UPDATED}</div>
      <p className="legal-note">
        This is a plain-language summary of how Alma actually works, prepared for review. It is not
        final legal advice, and it has not yet been checked against the law of every country Alma is
        sold in. Where a fact is not settled it is left visibly blank rather than filled in.
      </p>
      <div className="legal-rule" />
      <p className="legal-lead">{lead}</p>
    </>
  );
}

/** A titled section. `id` is set where a footer link points at it. */
export function Sec({ title, id, children }: { title: string; id?: string; children: ReactNode }) {
  return (
    <section className="legal-sec" id={id}>
      <h2 className="legal-h">{title}</h2>
      {children}
    </section>
  );
}

/** A paragraph. */
export function Para({ children }: { children: ReactNode }) {
  return <p className="legal-para">{children}</p>;
}

/** A list, for the places where prose would be pretending. */
export function Points({ children }: { children: ReactNode }) {
  return <ul className="legal-points">{children}</ul>;
}

/** One labelled fact, hairline-separated — the imprint is mostly these. */
export function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="legal-fact">
      <span className="legal-fact-label">{label}</span>
      <span className="legal-fact-value">{children}</span>
    </div>
  );
}

/**
 * A fact nobody has supplied yet.
 *
 * Marked, not invented. A registration number that looks plausible is worse
 * than an obvious gap: the gap gets filled before launch, the plausible number
 * never does.
 */
export function Blank({ children }: { children: ReactNode }) {
  return <span className="legal-blank">[{children}]</span>;
}

/** The foot of every document. */
export function DocFoot() {
  return (
    <div className="legal-foot">
      If a sentence on this page is unclear, that is our fault, not yours. Write to{" "}
      <a href={`mailto:${CONTACT}`}>{CONTACT}</a> and we will fix the sentence.
      <br />
      {OPERATOR} · Wyoming, United States
    </div>
  );
}
