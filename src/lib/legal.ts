/**
 * The facts the five legal documents share, in one place.
 *
 * A privacy policy that says one thing and a refund policy that says another
 * is the ordinary way this goes wrong, and it goes wrong because each page was
 * written on its own. Everything a second document would have to repeat lives
 * here instead: the operator, the merchant of record, the contact address, the
 * minimum age, and the date.
 */

/**
 * The date printed at the top of every document.
 *
 * One constant for all of them, deliberately. They were written together and
 * reviewed together; separate dates would suggest separate reviews, and the
 * moment one of them is stale the others cannot be trusted either. Change it
 * whenever any of them changes.
 *
 * Moved to the 7th when the seller changed: every document that named a card
 * processor as the merchant of record was rewritten for Apple and Google, which
 * is the largest factual change these pages have had. A reader who kept the
 * older version is entitled to see from the date that this is not it.
 */
export const LEGAL_UPDATED = "7 August 2026";

/** Who operates Alma. Not the seller — see `MERCHANT`. */
export const OPERATOR = "Pazl LLC";

/**
 * Every company that can be the merchant of record for an Alma purchase.
 *
 * The merchant of record takes the payment, issues the invoice, handles the tax
 * and holds the money, which is the whole reason the refund policy reads the
 * way it does. Two of the four below actually do that today — see
 * `STORE_MERCHANTS`. The other two are the card processors behind the billing
 * seam, and **nothing sells through them**: the web checkout is gone, both apps
 * bill through their store, and every `open_session` on a card adapter refuses.
 *
 * They stay in the table anyway, for two reasons that are not sentiment. The
 * seam is real — `ALMA_BILLING_PROVIDER` still selects an adapter, and our
 * category is prohibited by one processor's acceptable-use policy and merely
 * reviewable by another's, so which one we would fall back to is an open
 * question rather than a closed one. And `legal-truth.test.ts` reads the
 * backend's `billing/` directory and asserts this table names a seller for
 * every adapter that ships: a processor added there and forgotten here renders
 * the fallback name, which is a different company's name on a dispute.
 *
 * `/v1/billing/catalogue` publishes the same string under `merchant`, and the
 * two have to agree. This constant exists because the legal pages are static
 * and must render without a network call.
 */
const MERCHANTS: Record<string, string> = {
  paddle: "Paddle.com Market Ltd",
  dodo: "Dodo Payments",
  appstore: "Apple",
  googleplay: "Google",
};

export const BILLING_PROVIDER = process.env.NEXT_PUBLIC_BILLING_PROVIDER ?? "paddle";

/**
 * The card processor the seam is configured with — **not the seller**.
 *
 * It was the seller, on every page, while the web had a checkout. It has one
 * reader left: the paragraph on `/refunds` that tells somebody holding a
 * receipt from a company other than Apple or Google where to go. That paragraph
 * exists because a policy that mentions only the two stores would leave a
 * person with a card-processor receipt reading a page that does not describe
 * their purchase — and because deleting the fallback from the documents while
 * the adapters are still shipped is deleting a promise while keeping the
 * behaviour.
 */
export const MERCHANT = MERCHANTS[BILLING_PROVIDER] ?? MERCHANTS.paddle;

/**
 * Who actually sells Alma: the two stores, and nobody else.
 *
 * Every payment happens inside an app, through Play Billing or StoreKit. Google
 * or Apple is the merchant of record, they issue the receipt, they hold the
 * money, cancellation happens on their account screen, and our backend sends
 * them a purchase token to verify each one. Nothing is sold on the website —
 * there is no checkout on it to sell anything with.
 *
 * The privacy policy asserts a *complete* list of recipients, and both apps
 * link to it — `SettingsScreen.kt` opens `https://alma.pazl.ai/privacy`. Naming
 * only the card processor made that list wrong in both directions at once: it
 * named a company that receives nothing from a buyer, and omitted the one that
 * takes their money. Play's reviewers read the linked policy against the Data
 * safety form, and a mismatch there is a finding rather than a nuance.
 *
 * These are constants rather than another environment lookup because they are
 * not configuration: an app on the Play Store cannot bill through anyone but
 * Google, whatever any variable says.
 */
export const STORE_MERCHANTS = [
  { store: "Google Play", merchant: MERCHANTS.googleplay, platform: "Android" },
  { store: "the App Store", merchant: MERCHANTS.appstore, platform: "iPhone and iPad" },
] as const;

/**
 * Where a buyer's receipt comes from, in the words each processor uses.
 *
 * The refunds page routes people through their receipt email, and "the receipt
 * Paddle emailed you" is a sentence that stops being true the day the
 * configuration changes.
 */
export const RECEIPT_FROM = MERCHANT;

/**
 * How long deleted data can still exist in a backup, in days.
 *
 * The one number on the deletion page that is a promise about infrastructure
 * rather than about code, and the one place deleted data survives an
 * "immediately" that is otherwise literal. It is here because two pages state
 * it — `/delete-account`, which is the resource Play validates and reads as the
 * deletion promise, and `/privacy`, where it was a `<Blank>` while the other
 * page was already promising thirty days. Two pages disagreeing about how long
 * we keep data somebody asked us to destroy is the worst shape this fact can
 * take, so it is one constant with two readers.
 *
 * **This is a commitment, not an observation.** Nothing in this repository can
 * verify it: it is a property of whatever the database is hosted on, and the
 * hosting region is itself still a blank on the privacy page. Whoever fills in
 * that blank must confirm the backup schedule against this number and change
 * one of the two.
 */
export const BACKUP_WINDOW_DAYS = 30;

/**
 * How long a step label and the browser id beside it are kept, in days.
 *
 * Unlike the number above it, this one **is** verifiable from this repository,
 * and it has to be: it is a retention promise about an identifier that lives in
 * somebody's browser, made on the privacy page, and the only thing that makes
 * it true is `funnel.purge` in the backend being run. So the number is stated
 * here for the page to print, `PURGE_AFTER_DAYS` in `backend/alma/funnel.py` is
 * what the deletion actually uses, and `legal-truth.test.ts` fails if the two
 * ever disagree — because a policy that says a hundred and eighty days over a
 * job that keeps for ever is worse than having no policy, since it is the
 * version a reader believes.
 *
 * What has to happen outside this repository is the cron line, which is in
 * `backend/README.md` beside the renewal notice for the same reason: a job that
 * nothing schedules sends nothing, deletes nothing, and looks exactly like
 * success.
 */
export const FUNNEL_RETENTION_DAYS = 180;

/** One address, read by people who built the product. */
export const CONTACT = "hello@pazl.ai";

/** Alma is not sold to anyone younger than this. */
export const MIN_AGE = 16;

/** The five documents, in the order they are worth reading. */
export const LEGAL_DOCS = [
  { href: "/privacy", label: "Privacy" },
  { href: "/terms", label: "Terms" },
  { href: "/refunds", label: "Refunds" },
  { href: "/subscription-terms", label: "Subscription terms" },
  { href: "/imprint", label: "Imprint" },
] as const;
