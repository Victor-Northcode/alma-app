import { readFileSync, existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { legalLinks } from "./data";

/**
 * Two rules the legal pages stand on, both of which fail silently.
 *
 * **The seller named on /refunds must be the seller that took the money.** The
 * page a card issuer reads during a dispute names the two stores by constant
 * and the card processor as `MERCHANT`, which is chosen by
 * `NEXT_PUBLIC_BILLING_PROVIDER` from a table in `lib/legal.ts` — while the
 * string that is actually true is the `merchant` attribute on the backend
 * adapter that `ALMA_BILLING_PROVIDER` selects. Two tables, two environment
 * variables, one fact. That fact matters less than it did now that nothing
 * sells through a card processor, and it is guarded exactly as hard: the seam
 * still ships, and the day it carries a payment is not the day to discover the
 * refunds page names a company that does not exist. So this reads the adapters and
 * asserts they agree; a processor renaming its legal entity, or a new adapter
 * added with a merchant nobody copied across, fails here rather than in a
 * chargeback where the seller we named does not exist.
 *
 * **A link is a claim that the document behind it exists.** `legalLinks` was
 * eighteen entries on `href="#"` once, claiming twelve documents that had never
 * been written. It is now five documents and their sections, and the sections
 * are the fragile part: `/refunds#withdrawal` is printed in the footer under
 * the pay button, and an anchor that has been renamed sends the one reader who
 * cares most to the top of a page instead of to the paragraph.
 */

const ROOT = join(__dirname, "..", "..");
const LEGAL = join(ROOT, "src", "app", "(legal)");

function read(path: string): string {
  return readFileSync(path, "utf8");
}

describe("the merchant of record named on the legal pages", () => {
  const table = read(join(ROOT, "src", "lib", "legal.ts"));

  /** The `paddle: "…"` / `dodo: "…"` pairs the pages render. */
  const named = new Map<string, string>(
    [...table.matchAll(/^\s{2}(\w+):\s*"([^"]+)",$/gm)].map((m) => [m[1], m[2]]),
  );

  /**
   * Every billing adapter the backend ships, discovered rather than listed.
   *
   * It used to be `["paddle", "dodo"]`, typed here — which made this test the
   * third table of processors in a file whose entire purpose is that there
   * should be one. Apple and Google were added to the backend, `legal.ts`
   * learned about them, and the *test* was what went stale: it failed for
   * naming too few rather than too many, which is the least useful direction a
   * guard can fail in. Reading the directory is what its own comment always
   * claimed it did.
   */
  const adapters = readdirSync(join(ROOT, "backend", "alma", "billing"))
    .filter((file) => file.endsWith(".py"))
    .map((file) => ({ name: file.replace(/\.py$/, ""), source: read(join(ROOT, "backend", "alma", "billing", file)) }))
    .filter(({ source }) => /^\s*merchant\s*=\s*"[^"]+"/m.test(source))
    .map(({ name }) => name);

  it("knows a seller for every processor this build can be configured with", () => {
    // The adapters are the authority on which processors exist at all: one
    // added to the backend and forgotten here renders the fallback seller,
    // which is a different company's name on a dispute.
    expect(adapters.length).toBeGreaterThan(0);
    expect([...named.keys()].sort()).toEqual([...adapters].sort());
  });

  it("matches the merchant every adapter reports", () => {
    for (const provider of adapters) {
      const source = read(join(ROOT, "backend", "alma", "billing", `${provider}.py`));
      const merchant = /^\s*merchant\s*=\s*"([^"]+)"/m.exec(source);
      expect(merchant, `${provider}.py declares no merchant`).not.toBeNull();
      expect(named.get(provider), `legal.ts names the wrong seller for ${provider}`).toBe(
        merchant![1],
      );
    }
  });
});

describe("every legal link points at something that exists", () => {
  const pages = new Map<string, string>();
  for (const link of legalLinks) {
    if (link.href.startsWith("mailto:")) continue;
    const [path] = link.href.split("#");
    const file = join(LEGAL, path.replace(/^\//, ""), "page.tsx");
    if (existsSync(file)) pages.set(path, read(file));
  }

  it.each(legalLinks.map((l) => [l.label, l.href] as const))(
    "%s → %s",
    (_label, href) => {
      if (href.startsWith("mailto:")) {
        expect(href).toMatch(/^mailto:.+@.+\..+$/);
        return;
      }
      const [path, anchor] = href.split("#");
      expect(pages.has(path), `no page renders ${path}`).toBe(true);
      if (anchor) {
        // `Sec` takes the anchor as `id`, so the section that the footer sends
        // people to is findable in the source of the page it lives on.
        expect(pages.get(path)).toContain(`id="${anchor}"`);
      }
    },
  );
});

/**
 * The same rule, turned on the documents themselves.
 *
 * The footer's wall is checked above because it was once eighteen links to
 * nothing. The pages link to each other far more than the footer links to them
 * — a refund policy that sends you to a cancellation section, a deletion page
 * that sends you to the privacy policy — and those links were checked by
 * nobody. They are the ones that break silently, because the page they point at
 * still exists and only the anchor has been renamed: the reader lands at the
 * top of a long document instead of at the paragraph that answers them, and
 * nothing anywhere errors.
 */
describe("every internal link inside a legal document resolves", () => {
  const docs = readdirSync(LEGAL, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => ({ route: `/${entry.name}`, source: read(join(LEGAL, entry.name, "page.tsx")) }));

  const bodies = new Map(docs.map((doc) => [doc.route, doc.source]));

  it("finds the documents at all", () => {
    // A guard on the guard: a rename of the route group would leave every
    // assertion below iterating an empty list and passing.
    expect(docs.length).toBeGreaterThanOrEqual(6);
  });

  it.each(docs.map((doc) => [doc.route, doc.source] as const))("%s", (route, source) => {
    // `href="/…"` covers both `<Link>` and `<a>`; anything interpolated is an
    // external address from `lib/support.ts` and is checked separately.
    for (const [, href] of source.matchAll(/href="(\/[^"]*)"/g)) {
      const [path, anchor] = href.split("#");
      expect(bodies.has(path), `${route} links to ${path}, which no page renders`).toBe(true);
      if (anchor) {
        expect(
          bodies.get(path),
          `${route} links to ${href}, and no section on ${path} has that id`,
        ).toContain(`id="${anchor}"`);
      }
    }
  });
});

/**
 * Where a legal page sends somebody off this site.
 *
 * These cannot be checked for a 200 from a test — the suite runs without a
 * network, and a store's help centre answering a command-line client is its own
 * decision (`apps.apple.com` returns 403 to curl and the page to a browser). So
 * what is asserted is the part a test *can* know: the destination is one of the
 * two companies that hold our customers' money, over TLS. A typo'd or
 * substituted host on the page somebody reads after being charged twice is the
 * failure this exists for; the addresses themselves are checked by hand, and
 * `lib/support.ts` records when and with what result.
 */
describe("every external link on a legal page is a store address", () => {
  const ALLOWED = ["apple.com", "google.com"];
  const sources = [
    ...readdirSync(LEGAL, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => [`/${entry.name}`, read(join(LEGAL, entry.name, "page.tsx"))] as const),
    ["lib/support.ts", read(join(ROOT, "src", "lib", "support.ts"))] as const,
  ];

  it.each(sources)("%s", (_where, source) => {
    for (const [, url] of source.matchAll(/"(https?:\/\/[^"]+)"/g)) {
      const { protocol, hostname } = new URL(url);
      expect(protocol, `${url} is not over TLS`).toBe("https:");
      // Two exceptions that are neither stores nor mistakes: the imprint's
      // attribution links, which a licence requires by name.
      if (hostname.endsWith("geonames.org") || hostname.endsWith("creativecommons.org")) continue;
      expect(
        ALLOWED.some((host) => hostname === host || hostname.endsWith(`.${host}`)),
        `${url} is not on ${ALLOWED.join(" or ")}`,
      ).toBe(true);
    }
  });
});

/**
 * The two links inside the receipt email, which land on this site.
 *
 * `mail.py` builds them as `{web_url}{PATH}` and the paths are Python strings
 * six directories away from the pages that have to answer them. One of them has
 * already been wrong twice: it was `/?plan=1`, which nothing read, and then
 * `/settings`, which was a real cancel button until the cabinet was deleted. A
 * receipt is the one letter people keep, and its "Manage your plan" button is
 * pressed by somebody trying to stop a charge — the worst possible moment to
 * arrive at a 404 or at the page that sells the product.
 */
describe("the paths the receipt email links to", () => {
  const mail = read(join(ROOT, "backend", "alma", "mail.py"));
  const paths = [...mail.matchAll(/^RECEIPT_\w*PATH\s*=\s*"([^"]+)"/gm)].map((m) => m[1]);

  it("finds them", () => {
    expect(paths.length).toBeGreaterThan(0);
  });

  it.each(paths)("%s", (href) => {
    const [path, anchor] = href.split("#");
    const file = join(LEGAL, path.replace(/^\//, ""), "page.tsx");
    expect(existsSync(file), `the receipt links to ${path}, which no page renders`).toBe(true);
    if (anchor) {
      expect(
        read(file),
        `the receipt links to ${href}, and no section on ${path} has that id`,
      ).toContain(`id="${anchor}"`);
    }
  });
});

/**
 * The retention the privacy page promises, against the code that does it.
 *
 * This one is different in kind from the backup window beside it in
 * `lib/legal.ts`, and that is why it gets a test rather than a paragraph of
 * caveats. The backup window is a property of somebody's hosting and nothing
 * here can check it. This one is a `DELETE` in `backend/alma/funnel.py`, so the
 * only way the page can be wrong is if the two numbers drift — which is exactly
 * what happens when a retention is shortened in a policy review and nobody
 * changes the job, or lengthened in the job and nobody changes the policy.
 *
 * It matters more than an ordinary constant mismatch because of what is being
 * kept: an identifier that sits in somebody's browser tying their visits
 * together. A page that says a hundred and eighty days over a job that keeps for
 * ever is worse than no policy at all, because it is the version a reader
 * believes.
 */
describe("how long the funnel keeps a browser id", () => {
  it("is the number the code deletes on", () => {
    const declared = read(join(ROOT, "src", "lib", "legal.ts")).match(
      /FUNNEL_RETENTION_DAYS = (\d+)/,
    );
    const enforced = read(join(ROOT, "backend", "alma", "funnel.py")).match(
      /^PURGE_AFTER_DAYS = (\d+)/m,
    );
    expect(declared, "lib/legal.ts no longer declares FUNNEL_RETENTION_DAYS").toBeTruthy();
    expect(enforced, "alma/funnel.py no longer declares PURGE_AFTER_DAYS").toBeTruthy();
    expect(Number(declared![1])).toBe(Number(enforced![1]));
  });

  it("is printed on the page rather than typed into it", () => {
    // A number typed into the prose is a number that survives the constant
    // changing, and the privacy page is the last place to discover that.
    const page = read(join(LEGAL, "privacy", "page.tsx"));
    expect(page).toContain("FUNNEL_RETENTION_DAYS");
  });

  it("is the number the app expires its own id on", () => {
    // The server purging its rows is only half of the promise. The other half
    // is the identifier itself: a string that sits in somebody's storage tying
    // their visits together, and that is eventually joined to an account.
    // While only the rows expired, the same person was re-identified under the
    // same id in year three and a purged id could be claimed afresh by a
    // *different* account — an identifier with no end, which is the one thing
    // the privacy page exists to promise we do not keep.
    //
    // So every client re-mints past the retention, and each holds its own copy
    // of the number because none of them can import the others'. Three copies
    // of one fact is two chances to disagree, and the one that drifts silently
    // is a mobile constant nobody re-reads. Hence this.
    //
    // Читалось из двух нативов (`InstallationId.swift`, `Measurement.kt`) —
    // они сняты вместе с самими нативами («продукт собирается только из
    // порта»), и этот тест месяц падал на ENOENT. Падал он по делу: порт
    // constant-у не унаследовал, id жил вечно, и обещание страницы
    // приватности держал только сервер. Срок вернулся во Flutter-клиент
    // 30.08.2026, и читается теперь оттуда.
    const enforced = Number(
      read(join(ROOT, "backend", "alma", "funnel.py")).match(/^PURGE_AFTER_DAYS = (\d+)/m)![1],
    );

    const flutter = read(
      join(ROOT, "mobile", "flutter", "alma", "lib", "net", "alma_client.dart"),
    ).match(/static const anonRetentionDays = (\d+)/);

    expect(flutter, "alma_client.dart no longer declares anonRetentionDays").toBeTruthy();
    expect(Number(flutter![1]), "the app disagrees with PURGE_AFTER_DAYS").toBe(enforced);
  });
});
