"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LEGAL_DOCS } from "@/lib/legal";

/**
 * Getting between the five documents.
 *
 * The chapter reader's shape, because it is the same shape of problem: a
 * standing rail of everything there is to read, and the one you are reading
 * marked. Desktop gets the 260 px column; below that the five sit in a rail
 * across the top, which is the one place in this design a horizontal scroll is
 * the honest answer to a list that will not fit.
 *
 * The only reason this is a client component is `usePathname` — the pages
 * themselves are static server-rendered documents, which is what they should
 * be.
 */

/** Desktop: the column, inverted onto parchment. */
export function LegalSide() {
  const path = usePathname();

  return (
    <aside className="legal-side only-desktop">
      <div className="legal-side-title">Legal</div>
      <div className="legal-side-list">
        {LEGAL_DOCS.map((doc) => (
          <Link
            key={doc.href}
            href={doc.href}
            className="legal-side-item"
            data-active={path === doc.href}
          >
            {doc.label}
          </Link>
        ))}
      </div>
      <div className="legal-side-foot">
        <Link href="/">← Back to Alma</Link>
      </div>
    </aside>
  );
}

/** Mobile and tablet: the sticky bar. */
export function LegalBar() {
  const path = usePathname();

  return (
    <header className="legal-bar">
      <Link href="/" className="legal-home" aria-label="Back to Alma">
        ←
      </Link>
      <nav className="rail legal-rail" aria-label="Legal documents">
        {LEGAL_DOCS.map((doc) => (
          <Link key={doc.href} href={doc.href} data-active={path === doc.href}>
            {doc.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
