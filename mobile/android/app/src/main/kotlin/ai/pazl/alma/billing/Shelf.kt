package ai.pazl.alma.billing

import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.data.dto.CatalogueItemDto
import ai.pazl.alma.data.map
import androidx.compose.runtime.Immutable
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.ProductDetails
import java.text.NumberFormat
import java.util.Currency
import kotlin.math.roundToInt

/**
 * What the paywall is allowed to sell, assembled from the two authorities that
 * have to agree.
 *
 * **Our server decides what is on the shelf.** Which products exist, which of
 * them this account may see, whether the archive row is the archive or the
 * cheaper upgrade this person has earned — all of that comes from
 * `GET /v1/billing/catalogue` and none of it is decided here.
 *
 * **Play decides what a price says.** On Android, Google takes the money and
 * Google does the currency, the local tax and the formatting. Our catalogue's
 * `display` is the right number on the web and the wrong one here: it is the
 * price *our processor* would charge, and printing it beside a Play sheet
 * showing something else is a store rejection at best and a lie at worst. So
 * every price on this screen is [ProductDetails]'s own formatted string.
 *
 * The consequence is the one thing that will look like a bug and is not: **a
 * product the Play Console does not have is not shown at all**. There is no
 * fallback to our own price, because a row nobody can buy, priced in a currency
 * Play is not charging in, is worse than an absent row. Until the in-app
 * products exist in the console with the ids [StoreProducts.productId]
 * produces, [Shelf.rows] comes back empty and [Shelf.unpriced] says which slugs
 * the server offered and Play had never heard of.
 */
@Immutable
data class ShelfRow(
    /** The catalogue key: "natal", "archive", "archive-upgrade", "annual". */
    val slug: String,
    /** The system a door opens. Null on the archive and on the plans. */
    val system: String?,
    /**
     * What Play will charge at the tap, formatted by Play.
     *
     * For a plan with an introductory phase this is the *first* phase — the
     * amount that actually leaves the account today — and [recurringPrice]
     * carries what it becomes. Showing the ongoing price on the button while
     * charging an introductory one is the same class of mistake as showing our
     * currency: a number on screen that is not the number on the statement.
     */
    val price: String,
    /** The ongoing price, when an introductory phase makes it differ from [price]. */
    val recurringPrice: String?,
    /** "month", "year", or null for a one-time purchase. */
    val interval: String?,
    /** Set on `archive-upgrade`: the shelf product this stands in for. */
    val replaces: String?,
    val details: ProductDetails,
    /**
     * Which offer inside the product is being bought.
     *
     * Required for subscriptions, and required in Billing 8 for a one-time
     * product that has purchase options. Null for a plain one-time product,
     * where passing one is a `DEVELOPER_ERROR` rather than a no-op.
     */
    val offerToken: String?,
    /**
     * The annual's arithmetic, set on the annual row only: the per-month
     * equivalent, formatted in Play's own currency, and the percentage saved
     * against twelve months of the monthly. Null when the monthly is not on
     * the shelf to compare against, or when the comparison does not favour
     * the year — an invented saving is a lie with a percent sign on it.
     */
    val perMonth: String? = null,
    val savingsPercent: Int? = null,
) {
    val recurring: Boolean get() = !interval.isNullOrBlank()
}

@Immutable
data class Shelf(
    /** In the order somebody climbs the ladder: the door, the archive, the year. */
    val rows: List<ShelfRow>,
    /** The currency our server prices in. Kept for the log, never printed. */
    val currency: String,
    /** Where a subscriber cancels, when the server knows. */
    val manageUrl: String?,
    /**
     * Slugs the server offered that Play could not price.
     *
     * Not an error state on its own — it is exactly what happens before the
     * console has been filled in — but it is the difference between "there is
     * nothing left to sell you" and "payments are not working", which are two
     * different sentences and only one of them is true at a time.
     */
    val unpriced: List<String>,
)

/**
 * Build the ladder for one paywall.
 *
 * @param wanted the system the person reached for, or null when they reached
 *   for nothing in particular — the chat opens the paywall with no system,
 *   because what is being asked for there is more questions rather than a
 *   chart. A `?: "natal"` in that position would offer a natal purchase to
 *   somebody who already owns natal, which is the web app's own note.
 * @param owned what this account can already read. A row whose grant has
 *   already landed is dropped rather than greyed out: an offer to buy
 *   something you own is not an offer.
 */
suspend fun buildShelf(
    client: AlmaClient,
    billing: PlayBilling,
    wanted: String?,
    owned: Collection<String>,
    hasPlan: Boolean = false,
    ownsArchive: Boolean = false,
): ApiResult<Shelf> = client.catalogue().map { catalogue ->
    val offered: Map<String, CatalogueItemDto> = catalogue.items.associateBy { it.slug }
    val ladder = ladder(wanted, offered.keys, owned, hasPlan = hasPlan, ownsArchive = ownsArchive)

    // Two queries because Play will not mix product types in one, and both are
    // skipped when there is nothing of that type to ask about — an empty
    // product list is a `DEVELOPER_ERROR`, not an empty answer.
    val (subscriptions, purchases) = ladder.partition(StoreProducts::isSubscription)
    val details: Map<String, ProductDetails> = buildMap {
        if (purchases.isNotEmpty()) {
            putAll(billing.productDetails(purchases.map(StoreProducts::productId)).associateBy { it.productId })
        }
        if (subscriptions.isNotEmpty()) {
            putAll(
                billing.productDetails(
                    subscriptions.map(StoreProducts::productId),
                    BillingClient.ProductType.SUBS,
                ).associateBy { it.productId }
            )
        }
    }

    val rows = ladder.mapNotNull { slug ->
        val item = offered.getValue(slug)
        val play = details[StoreProducts.productId(slug)] ?: return@mapNotNull null
        row(slug, item, play)
    }.let { built ->
        // The annual's arithmetic, computed once both plans are priced.
        val breakdown = annualBreakdown(details)
        if (breakdown == null) built
        else built.map { row ->
            if (row.slug == StoreProducts.ANNUAL) {
                row.copy(perMonth = breakdown.first, savingsPercent = breakdown.second)
            } else {
                row
            }
        }
    }

    Shelf(
        rows = rows,
        currency = catalogue.currency,
        manageUrl = catalogue.manageUrl,
        unpriced = ladder.filterNot { slug -> rows.any { it.slug == slug } },
    )
}

/**
 * Which rungs this person is shown, in the order they climb them.
 *
 * The door for the system they reached for, then the archive, then the year —
 * the same ladder as the web app's sheet, and pre-selected by the caller on the
 * first of them.
 *
 * `archive` and `archive-upgrade` are both named and at most one survives: they
 * are mutually exclusive in a single catalogue response, because the server
 * substitutes the upgrade for the archive when this account has earned it.
 * Naming both takes whichever arrived rather than deciding here which one
 * somebody deserves — a decision that involves a thirty-day window, a currency
 * match and a purchase history, none of which this app has.
 *
 * Pure, and separated from the Play lookup for that reason: what may be sold is
 * the rule worth a test, and the test should not need a store.
 */
internal fun ladder(
    wanted: String?,
    offered: Set<String>,
    owned: Collection<String>,
    /**
     * Whether a plan is live on this account, read off the entitlement rows'
     * `kind` rather than off `unlocked` — the flat list cannot tell an annual
     * subscriber from an archive owner, and only the first must lose the plan
     * rows. Selling an annual to a monthly subscriber is a *change* inside one
     * Play subscription group, done on Play's own screen, never here.
     */
    hasPlan: Boolean = false,
    /**
     * Whether the archive was bought outright. The plans stay on the shelf for
     * an archive owner: the archive is forty-one written chapters, and the
     * living layer is transits that move. They are not the same purchase.
     */
    ownsArchive: Boolean = false,
): List<String> = buildList {
    wanted?.takeIf { it in AlmaSystem.ALL }?.let(::add)
    // **Plans first when nobody reached for a door**, annual above monthly —
    // research is unambiguous that the plan sells best led by the annual
    // (60–70% of plan sales when it leads, and better day-380 retention). On a
    // door intent the door stays first and pre-selected: selling what somebody
    // reached for is this ladder's own oldest law.
    if (wanted == null && !hasPlan) {
        add(StoreProducts.ANNUAL)
        add(StoreProducts.MONTHLY)
    }
    add(StoreProducts.ARCHIVE)
    add(StoreProducts.ARCHIVE_UPGRADE)
    if (wanted != null && !hasPlan) {
        add(StoreProducts.ANNUAL)
        add(StoreProducts.MONTHLY)
    }
}.filter { slug ->
    StoreProducts.sellable(slug, offered) && when (slug) {
        // The plan rows are removed by a live plan and by nothing else.
        StoreProducts.ANNUAL, StoreProducts.MONTHLY -> !hasPlan
        // The archive rows by outright ownership — not by `grantLanded`, whose
        // `unlocked ⊇ ALL` test is also true of every annual subscriber.
        StoreProducts.ARCHIVE, StoreProducts.ARCHIVE_UPGRADE -> !ownsArchive
        else -> !StoreProducts.grantLanded(slug, owned)
    }
}

/**
 * "$6.58" and 34, from Play's own micros — the ongoing phase of each plan, so
 * an introductory month does not flatter the saving. Null when either plan is
 * unpriced or the year does not actually cost less.
 */
private fun annualBreakdown(details: Map<String, ProductDetails>): Pair<String, Int>? {
    fun ongoing(slug: String) = details[StoreProducts.productId(slug)]
        ?.subscriptionOfferDetails
        ?.minByOrNull { it.pricingPhases.pricingPhaseList.sumOf { p -> p.priceAmountMicros } }
        ?.pricingPhases?.pricingPhaseList?.lastOrNull()

    val annual = ongoing(StoreProducts.ANNUAL) ?: return null
    val monthly = ongoing(StoreProducts.MONTHLY) ?: return null
    val yearAtMonthly = monthly.priceAmountMicros * 12
    if (yearAtMonthly <= annual.priceAmountMicros) return null

    val saving = ((yearAtMonthly - annual.priceAmountMicros) * 100.0 / yearAtMonthly)
        .roundToInt()
    val format = NumberFormat.getCurrencyInstance().apply {
        currency = Currency.getInstance(annual.priceCurrencyCode)
    }
    return format.format(annual.priceAmountMicros / 12 / 1_000_000.0) to saving
}

private fun row(slug: String, item: CatalogueItemDto, play: ProductDetails): ShelfRow? {
    val system = item.system?.takeIf { it != "*" }
    return if (StoreProducts.isSubscription(slug)) {
        // Play returns only the offers this account is *eligible* for, so the
        // cheapest of them is the one they would get if they went looking. An
        // app that picked the first offer in the list would sometimes charge
        // full price to somebody Google had already decided qualifies for an
        // introductory one, which is a complaint we would deserve.
        val offer = play.subscriptionOfferDetails
            ?.minByOrNull { it.pricingPhases.pricingPhaseList.sumOf { phase -> phase.priceAmountMicros } }
            ?: return null
        val phases = offer.pricingPhases.pricingPhaseList.ifEmpty { return null }
        val first = phases.first()
        val ongoing = phases.last()
        ShelfRow(
            slug = slug,
            system = system,
            price = first.formattedPrice,
            recurringPrice = ongoing.formattedPrice.takeIf { it != first.formattedPrice },
            interval = item.interval?.takeIf { it.isNotBlank() },
            replaces = item.replaces,
            details = play,
            offerToken = offer.offerToken,
        )
    } else {
        // `oneTimePurchaseOfferDetails` is the plain product; the list beside
        // it is Billing 8's purchase options, and a product that has them has
        // no plain offer at all. Both are read because which one is populated
        // is decided in the console, months from now, by somebody who will not
        // remember this file exists.
        val plain = play.oneTimePurchaseOfferDetails
        val option = play.oneTimePurchaseOfferDetailsList?.firstOrNull()
        val price = plain?.formattedPrice ?: option?.formattedPrice ?: return null
        ShelfRow(
            slug = slug,
            system = system,
            price = price,
            recurringPrice = null,
            interval = null,
            replaces = item.replaces,
            details = play,
            offerToken = if (plain == null) option?.offerToken else null,
        )
    }
}
