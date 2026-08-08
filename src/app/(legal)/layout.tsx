import type { ReactNode } from "react";
import { LegalBar, LegalSide } from "@/components/legal/LegalNav";

/**
 * The five documents: privacy, terms, refunds, subscription terms, imprint.
 *
 * ── English only, for now, on purpose ─────────────────────────────────────
 * The rest of Alma is in six languages and this route group is in one. Legal
 * text is not interface copy: each of these pages has to be reviewed against
 * the law of the country it is read in before it can be trusted there, and
 * translating first would mean shipping six confident versions of an
 * unreviewed document. A refund policy that is wrong in German is worse than
 * one that is merely in English — the reader can tell that an English page is
 * the original, and cannot tell that a German one has drifted. So: review per
 * jurisdiction first, translate after. The links to these pages are already
 * translated, which is the part a person needs to find them.
 *
 * The surface is parchment, the same as the chapter reader. It is the only
 * other place in the product where ink on paper is the right answer: a
 * document should look like a document, and should print like one.
 */
export default function LegalLayout({ children }: { children: ReactNode }) {
  return (
    <div className="legal parchment" lang="en">
      <div className="parchment-sweep" aria-hidden />
      <LegalSide />
      <div className="legal-main">
        <LegalBar />
        <article className="legal-doc">{children}</article>
      </div>
    </div>
  );
}
