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
 * The backend's catalogue keys are `door.natal`, `door.birth-card`,
 * `pair.check`, `sub.monthly`. The Play Console will not accept a hyphen in a
 * product id, so `backend/alma/billing/provider.py::store_product_id` states the
 * rule the console is filled in by: the catalogue key, with [PREFIX] in front of
 * it and every hyphen turned into an underscore.
 * `ai.pazl.alma.door.birth_card`. It is reversible only because no catalogue key
 * contains an underscore, which is a fact the backend pins with a test and this
 * file pins with another.
 *
 * This mattered before anything was sold. `POST /v1/billing/iap/verify` calls
 * `prices.product(product)` on the way in, so handing it the *Play* id answers
 * **404 "nothing on sale called 'ai.pazl.alma.door.natal'"** — a purchase Google
 * has taken money for and a server that grants nothing. The purchase token that
 * comes back from Play carries the Play id; the verify call needs the catalogue
 * key; [slugFor] is the one place that conversion happens.
 *
 * ## A catalogue key is not a system slug any more
 *
 * Until v3 they were the same string — `"natal"` was both the product and the
 * thing it opened — and the shelf has stopped being shaped that way: five doors,
 * a pair check, a bundle and a subscription. So `AlmaSystem.NATAL` and
 * `DOOR_NATAL` are two different constants and [systemFor] is the one place that
 * maps between them. Handing a system slug to [productId] now produces an id no
 * console has, which is a purchase sheet that never opens.
 *
 * ## The rule about what may be sold
 *
 * A Play product id exists in the console whether or not our server listed it,
 * so the *app* is the only thing standing between a price and somebody buying it
 * directly. Hence [sellable]: nothing is purchasable that this account's own
 * catalogue did not list. Never a hardcoded list of "things we sell" — the
 * server already decided what is on the shelf in this currency, for this person.
 *
 * The set of prices this refuses is empty today; it was not always, and will not
 * stay so. `archive-bump` at $29.99 granted exactly what the $38.99 archive
 * granted, so a bump bought alone was the archive at nine dollars off, and the
 * first A/B on the bundle price puts two prices behind one grant again.
 *
 * ## Where the prefix comes from
 *
 * `ALMA_STORE_PRODUCT_PREFIX`, whose default is `"ai.pazl.alma."`. It is a
 * constant here because a client cannot read the server's environment, and the
 * id is needed before any call is made. If a deployment ever changes it, this
 * line changes with it — which is exactly the sort of coupling worth writing
 * down rather than discovering through an empty product sheet.
 */
object StoreProducts {

    const val PREFIX: String = "ai.pazl.alma."

    /* ── the eight catalogue keys, which are the eight store products ── */

    const val DOOR_NATAL: String = "door.natal"
    const val DOOR_NUMEROLOGY: String = "door.numerology"
    const val DOOR_BIRTH_CARD: String = "door.birth-card"
    const val DOOR_ASTROCARTOGRAPHY: String = "door.astrocartography"
    const val DOOR_SYNTHESIS: String = "door.synthesis"

    /** One report about one person. Play type `INAPP`, **consumed** after use. */
    const val PAIR_CHECK: String = "pair.check"

    /** All five readings that never change, bought outright. */
    const val BUNDLE_STATIC: String = "bundle.static"

    /** Everything, for as long as it is paid for. */
    const val SUB_MONTHLY: String = "sub.monthly"

    /** Play sells this as `SUBS`; everything else is `INAPP`. */
    val SUBSCRIPTIONS: Set<String> = setOf(SUB_MONTHLY)

    /**
     * The one product Play must **consume** rather than only acknowledge.
     *
     * `consumeAsync` is what makes a one-time product buyable again, and that is
     * exactly right for a pair check and exactly wrong for everything else: a
     * consumed door would be a permanent unlock the person can be charged for
     * twice, and an unconsumed pair check makes the second partner unbuyable.
     */
    val CONSUMED_AFTER_GRANT: Set<String> = setOf(PAIR_CHECK)

    /**
     * The three systems that move. Mirrors `LIVING_SYSTEMS` in the catalogue.
     *
     * They have no door in v3 and that is the point: transits are recomputed
     * every day and the solar return is rewritten every birthday, so selling
     * either "permanently" is selling a subscription without charging for one.
     * The set survives because the daily note and the subscription paywall both
     * need to name what only the plan carries.
     */
    val LIVING: Set<String> = setOf(
        AlmaSystem.TRANSITS,
        AlmaSystem.SOLAR_RETURN,
        AlmaSystem.COMPATIBILITY,
    )

    /** The five systems a door or the bundle opens. Mirrors `STATIC_SYSTEMS`. */
    val STATIC: Set<String> = setOf(
        AlmaSystem.NATAL,
        AlmaSystem.NUMEROLOGY,
        AlmaSystem.BIRTH_CARD,
        AlmaSystem.ASTROCARTOGRAPHY,
        AlmaSystem.SYNTHESIS,
    )

    /**
     * Every key `backend/alma/billing/catalogue.py` knows.
     *
     * `WEEKLY` was once added to the catalogue and missed here, which is not
     * cosmetic: [slugFor] answers null for anything outside this set, so a
     * bought subscription would have been read as somebody else's product, left
     * unacknowledged, and refunded by Google three days later.
     * `backend/tests/test_store_ids.py` fails when this set and the catalogue
     * disagree.
     */
    val ALL: Set<String> = setOf(
        DOOR_NATAL,
        DOOR_NUMEROLOGY,
        DOOR_BIRTH_CARD,
        DOOR_ASTROCARTOGRAPHY,
        DOOR_SYNTHESIS,
        PAIR_CHECK,
        BUNDLE_STATIC,
        SUB_MONTHLY,
    )

    /** Which door opens which system, and back. */
    private val DOOR_FOR_SYSTEM: Map<String, String> = mapOf(
        AlmaSystem.NATAL to DOOR_NATAL,
        AlmaSystem.NUMEROLOGY to DOOR_NUMEROLOGY,
        AlmaSystem.BIRTH_CARD to DOOR_BIRTH_CARD,
        AlmaSystem.ASTROCARTOGRAPHY to DOOR_ASTROCARTOGRAPHY,
        AlmaSystem.SYNTHESIS to DOOR_SYNTHESIS,
    )

    /** The catalogue key of the door for [system], or null when it has none. */
    fun doorFor(system: String): String? = DOOR_FOR_SYSTEM[system]

    /**
     * The system a catalogue key opens, or null when it opens more than one.
     *
     * Null for [PAIR_CHECK] deliberately, and not `AlmaSystem.COMPATIBILITY`: a
     * pair check opens one report about one person, not the system. Answering
     * with the system is how a hub ends up drawing "compatibility unlocked"
     * after one purchase and then refusing the second partner.
     */
    fun systemFor(slug: String): String? = when (slug) {
        DOOR_NATAL -> AlmaSystem.NATAL
        DOOR_NUMEROLOGY -> AlmaSystem.NUMEROLOGY
        DOOR_BIRTH_CARD -> AlmaSystem.BIRTH_CARD
        DOOR_ASTROCARTOGRAPHY -> AlmaSystem.ASTROCARTOGRAPHY
        DOOR_SYNTHESIS -> AlmaSystem.SYNTHESIS
        else -> null
    }

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
     * [offered] is this account's own catalogue: the server already decided what
     * is on the shelf in this currency, for this person, and an app that sells
     * anything else is an app that has an opinion about prices. Never a
     * hardcoded list of "things we sell" — that list is a second copy of the
     * shelf, and a second copy is the one that goes stale.
     */
    fun sellable(slug: String, offered: Collection<String>): Boolean = slug in offered

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
        BUNDLE_STATIC -> unlocked.containsAll(STATIC)
        SUB_MONTHLY -> unlocked.containsAll(AlmaSystem.ALL)
        // Пара сюда не попадает намеренно: её грант называет партнёра
        // (`pair:{profile_id}`) и в `unlocked` не появляется вовсе, потому что
        // открыта не система, а один отчёт. Проверять её по этому списку значит
        // никогда не подтвердить покупку — то есть отдать деньги обратно через
        // трёхдневный авто-рефанд Google у человека, который всё получил.
        // Подтверждение пары читает `unlocked_pairs`; это фаза Ф0.3.
        PAIR_CHECK -> false
        // A slug this build has never heard of, and the five doors, which name
        // their own system. Not "landed" on its own — see the `status` check at
        // the call site, which is what lets a product added to the server after
        // this release still be acknowledged on the server's own word.
        else -> systemFor(slug)?.let { it in unlocked } ?: false
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
