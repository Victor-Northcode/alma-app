package ai.pazl.alma.billing

import ai.pazl.alma.data.AlmaSystem
import com.android.billingclient.api.BillingClient

/**
 * The translation between what the catalogue calls a product and what the Play
 * Console calls it — and the two rules about *which* products may be sold at
 * all.
 *
 * ## Why a translation is needed
 *
 * The backend's catalogue keys are `natal`, `birth-card`, `solar-return`,
 * `archive-upgrade`. The Play Console will not accept a hyphen in a product id,
 * so `backend/alma/billing/provider.py::store_product_id` states the rule the
 * console is filled in by: the catalogue key, with [PREFIX] in front of it and
 * every hyphen turned into an underscore. `alma.birth_card`. It is reversible
 * only because no catalogue key contains an underscore, which is a fact the
 * backend pins with a test and this file pins with another.
 *
 * This mattered before anything was sold. `POST /v1/billing/iap/verify` calls
 * `prices.product(product)` on the way in, so handing it the *Play* id answers
 * **404 "nothing on sale called 'alma.natal'"** — a purchase Google has taken
 * money for and a server that grants nothing. The purchase token that comes
 * back from Play carries the Play id; the verify call needs the catalogue slug;
 * [slugFor] is the one place that conversion happens.
 *
 * ## The two rules about what may be sold
 *
 * **A conditional price is not a shelf item.** `archive-bump` at $29.99 and
 * `archive` at $38.99 grant exactly the same thing — everything — so a bump
 * bought on its own is the archive at nine dollars off. On the web that is
 * enforced by `Product.on_the_shelf`, which keeps it out of the catalogue
 * response entirely. A store is different and worse: a Play product id exists
 * in the console whether or not our server listed it, so the *app* is the only
 * thing standing between a conditional price and somebody buying it directly.
 * Hence [NEVER_ALONE], checked in [PlayBilling.purchase] rather than only in
 * the paywall — a screen is a place a mistake gets made once and copied.
 *
 * `archive-upgrade` is not in that set, and the difference is worth stating: it
 * is a real price for a real person, offered *instead of* the archive to
 * somebody who bought a door inside the credit window. The server decides that
 * — it substitutes the row into the catalogue response — so the rule here is
 * [sellable]: nothing is purchasable that this account's own catalogue did not
 * list. Never a hardcoded list of "things we sell".
 *
 * ## Where the prefix comes from
 *
 * `ALMA_STORE_PRODUCT_PREFIX`, whose default is `"alma."`. It is a constant
 * here because a client cannot read the server's environment, and the id is
 * needed before any call is made. If a deployment ever changes it, this line
 * changes with it — which is exactly the sort of coupling worth writing down
 * rather than discovering through an empty product sheet.
 */
object StoreProducts {

    const val PREFIX: String = "alma."

    /* ── the five catalogue keys that are not one of the eight systems ── */

    const val ARCHIVE: String = "archive"
    const val ARCHIVE_BUMP: String = "archive-bump"
    const val ARCHIVE_UPGRADE: String = "archive-upgrade"
    const val WEEKLY: String = "weekly"
    const val MONTHLY: String = "monthly"
    const val ANNUAL: String = "annual"

    /** Play sells these as `SUBS`; everything else is `INAPP`. */
    val SUBSCRIPTIONS: Set<String> = setOf(WEEKLY, MONTHLY, ANNUAL)

    /**
     * The three systems that move, and therefore the only ones a monthly plan
     * honestly rents. Mirrors `LIVING_SYSTEMS` in the catalogue: a natal chart
     * bought monthly would be rent on a number that has not changed since
     * birth.
     */
    val LIVING: Set<String> = setOf(
        AlmaSystem.TRANSITS,
        AlmaSystem.SOLAR_RETURN,
        AlmaSystem.COMPATIBILITY,
    )

    /**
     * Priced to exist only inside another checkout. Play has no equivalent of
     * an in-checkout upsell, so if this id is ever created in the console it is
     * a product anybody with a modified client could buy on its own — for nine
     * dollars less than the thing it grants.
     */
    val NEVER_ALONE: Set<String> = setOf(ARCHIVE_BUMP)

    /** Every key `backend/alma/billing/catalogue.py` knows. */
    val ALL: Set<String> =
        AlmaSystem.ALL.toSet() + setOf(ARCHIVE, ARCHIVE_BUMP, ARCHIVE_UPGRADE, MONTHLY, ANNUAL)

    /* ── the id rule, both ways ────────────────────────────────────────── */

    /** What the Play Console calls the catalogue row [slug]. */
    fun productId(slug: String): String = PREFIX + slug.replace('-', '_')

    /**
     * The catalogue key behind a Play product id, or null if it is not ours.
     *
     * Null has to be reachable and has to be handled: a Google account can
     * carry a purchase of a product from an older price list, and that is a
     * payment to leave alone rather than a chapter to unlock. Guessing — say,
     * stripping the prefix and hoping — would send an unknown string to the
     * verify endpoint, which answers 404 and leaves the purchase unacknowledged
     * for Google to refund three days later.
     */
    fun slugFor(productId: String): String? {
        if (!productId.startsWith(PREFIX)) return null
        val slug = productId.removePrefix(PREFIX).replace('_', '-')
        return slug.takeIf { it in ALL }
    }

    fun isSubscription(slug: String): Boolean = slug in SUBSCRIPTIONS

    fun productType(slug: String): String =
        if (isSubscription(slug)) BillingClient.ProductType.SUBS else BillingClient.ProductType.INAPP

    /**
     * Whether this app may open a Play sheet for [slug].
     *
     * Two conditions, and they are different in kind. [NEVER_ALONE] is a
     * product decision that no server response can override — a conditional
     * price is cheaper than the shelf item it stands in for, and selling it
     * alone is selling the shelf item at a discount nobody authorised.
     * [offered] is this account's own catalogue: the server already decided
     * what is on the shelf in this currency, for this person, including whether
     * they qualify for the upgrade price, and an app that sells anything else
     * is an app that has an opinion about prices.
     */
    fun sellable(slug: String, offered: Collection<String>): Boolean =
        slug !in NEVER_ALONE && slug in offered

    /**
     * Whether the grant a purchase of [slug] should produce is present in
     * [unlocked].
     *
     * This is the question that decides whether a purchase is **acknowledged**,
     * and getting it wrong costs somebody their money. `/iap/verify` answers
     * `already_claimed` for two very different situations: our own replay —
     * Play re-delivers every unacknowledged purchase on every launch — and a
     * transaction that belongs to *another* Alma account, which is the common
     * case for a guest on a reinstalled phone. Both come back 200, and the
     * `unlocked` list is the only thing that tells them apart, because it is
     * always *this* account's list.
     *
     * Acknowledging the second case would be the worst outcome available: the
     * person paid, holds nothing, and the three-day auto-refund that would have
     * given them their money back has just been switched off by us.
     */
    fun grantLanded(slug: String, unlocked: Collection<String>): Boolean = when (slug) {
        in AlmaSystem.ALL -> slug in unlocked
        // Everything-grants. `archive-bump` is here for completeness rather
        // than because it can be bought — it cannot; see [NEVER_ALONE].
        ARCHIVE, ARCHIVE_BUMP, ARCHIVE_UPGRADE, ANNUAL -> unlocked.containsAll(AlmaSystem.ALL)
        MONTHLY -> unlocked.containsAll(LIVING)
        // A slug this build has never heard of. Not "landed", but not a
        // refusal either — see the `status` check at the call site, which is
        // what lets a product added to the server after this release still be
        // acknowledged on the server's own word.
        else -> false
    }

    /**
     * Where a person cancels a Play subscription — which is the only place they
     * can.
     *
     * An app that offers its own cancel button for a Play subscription cannot
     * honour it: the contract is between the buyer and Google, and a local flag
     * saying "cancelled" does not stop a card being charged. An app that merely
     * *says* "cancel in Google Play" without linking there fails review. So the
     * link is built here, with the two query parameters Play reads to open the
     * right row rather than the subscriptions list.
     */
    fun manageSubscriptionUrl(packageName: String, productId: String? = null): String =
        if (productId.isNullOrBlank()) {
            "https://play.google.com/store/account/subscriptions"
        } else {
            "https://play.google.com/store/account/subscriptions" +
                "?sku=$productId&package=$packageName"
        }
}
