/**
 * Where a person goes when the answer is not ours to give.
 *
 * Every payment in Alma is made inside an app, through Apple or Google, and
 * that one fact decides the whole of this file: the money is held by a company
 * we do not work for, the receipt comes from them, cancellation happens on
 * their account screen, and a refund is theirs to grant. We can ask. We cannot
 * pay.
 *
 * So `/support` and `/refunds` have to send people *off this site*, which is
 * the one thing a support page must never get wrong — a dead link on the page
 * somebody opens because they have been charged twice is worse than no page.
 * The four destinations below are therefore constants with one reader each,
 * checked rather than remembered:
 *
 *   $ curl -sIL -o /dev/null -w '%{http_code}' <url>
 *   200  reportaproblem.apple.com
 *   200  support.apple.com/en-us/118223   ("Request a refund for apps or
 *        content that you bought from Apple" — the old HT204084 redirects here,
 *        which is why the number and not the letters)
 *   200  play.google.com/store/account/orderhistory
 *   200  play.google.com/store/account/subscriptions
 *   200  support.google.com/googleplay/answer/2479637   (refund policies)
 *   200  support.google.com/googleplay/answer/7018481   (cancel a subscription)
 *   403  apps.apple.com/account/subscriptions
 *
 * That last one is real and is the canonical Apple subscriptions screen — it is
 * the URL the iOS app itself opens (`SettingsScreen.swift:31`). Apple answers a
 * command-line client with 403 and a browser with the page, so it is listed
 * here with its answer written down: a future check that treats a non-200 as a
 * broken link should skip it deliberately rather than "fix" it into something
 * that returns 200 and is not the subscriptions screen.
 *
 * Checked 7 August 2026. If one of these ever moves, the store's own help
 * search is the fallback a person can always reach, which is why the two help
 * articles are here beside the two tools: an article is a stable thing to name
 * in prose, a tool is the thing that actually does the work.
 */

/** The two hosts a store link is allowed to be on, for the test that guards it. */
export const SUPPORT_HOSTS = ["apple.com", "google.com"] as const;

export const APPLE = {
  /** The refund tool itself. Sign in with the Apple Account that bought it. */
  refund: "https://reportaproblem.apple.com",
  /** Apple's own explanation of what can be refunded and how long it takes. */
  refundHelp: "https://support.apple.com/en-us/118223",
  /** Manage or cancel a subscription. 403s to curl; opens in a browser. */
  subscriptions: "https://apps.apple.com/account/subscriptions",
} as const;

export const GOOGLE = {
  /** Order history — a refund is requested from the purchase itself. */
  refund: "https://play.google.com/store/account/orderhistory",
  /** Google's refund policy, including the 48-hour self-serve window. */
  refundHelp: "https://support.google.com/googleplay/answer/2479637",
  /** Manage or cancel a subscription. */
  subscriptions: "https://play.google.com/store/account/subscriptions",
  /** How to cancel, in Google's words, for a person who wants the steps. */
  cancelHelp: "https://support.google.com/googleplay/answer/7018481",
} as const;
