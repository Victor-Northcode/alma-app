package ai.pazl.alma.billing

import ai.pazl.alma.core.SessionHolder
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.data.ApiResult
import android.app.Activity
import android.content.Context
import android.util.Log
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams
import com.android.billingclient.api.acknowledgePurchase
import com.android.billingclient.api.queryProductDetails
import com.android.billingclient.api.queryPurchasesAsync
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.coroutines.resume
import kotlin.coroutines.suspendCoroutine

/**
 * Google Play Billing, and the one rule that survives every platform.
 *
 * ## The rule
 *
 * **Entitlements are granted by the server after it verifies the purchase with
 * Google, never by the app noticing that billing returned OK.**
 *
 * Nothing in this file unlocks anything. When Play says a purchase succeeded,
 * this hands the purchase *token* to `POST /v1/billing/iap/verify` and waits;
 * the backend exchanges that token with the Play Developer API and grants from
 * what Google says. The unlocked list on the response is the only thing that
 * changes what the person can read.
 *
 * The reason is not paranoia about our own code, it is that anything the client
 * can decide, the client can be made to decide. A rooted device with a billing
 * shim returns `BillingResponseCode.OK` for free; it cannot make Google's API
 * agree that an order exists. The web client has carried the same comment since
 * its first version and an attack review later proved it right — metadata the
 * browser carried turned out to be rewritable and the fix was a server-side
 * seal. Android does not get a weaker rule.
 *
 * ## Acknowledgement is after verification, and that order matters
 *
 * Play *refunds a purchase automatically* if it is not acknowledged within
 * three days. Acknowledging before the server has granted would remove the one
 * safety net that exists for the case where verification fails: as long as the
 * purchase is unacknowledged, [restore] re-presents it on every launch and the
 * person eventually gets what they paid for, or Google gives them their money
 * back. Acknowledging first turns that into a silent loss.
 *
 * ## Restore is not a button, it is a launch step
 *
 * Play re-delivers every owned, unacknowledged purchase to
 * `queryPurchasesAsync`. [restore] is called at launch and on resume — and from
 * the paywall's own button, because a person who has just reinstalled looks for
 * one — and it is safe to call as often as it likes: a replayed verification
 * answers `already_claimed` and writes nothing, because the backend keys the
 * event on the store's own order id and that column is a primary key.
 *
 * ## The product ids are not the catalogue slugs
 *
 * The Play Console will not accept a hyphen, so what the console holds is
 * `alma.birth_card` where the catalogue says `birth-card`. Everything crossing
 * this boundary goes through [StoreProducts], and what goes to our server is
 * always the slug: `/v1/billing/iap/verify` looks the product up in the
 * catalogue and answers 404 for anything else, which would be a purchase Google
 * has taken money for and a server that grants nothing.
 */
class PlayBilling(
    context: Context,
    private val client: AlmaClient,
    private val session: SessionHolder,
    private val scope: CoroutineScope,
) {

    /** Where a purchase is, from the app's point of view. */
    sealed interface Status {
        data object Idle : Status

        /** Play's sheet is open, or the token is being verified. */
        data class Working(val product: String) : Status

        /** The server granted. [unlocked] is what may now be read. */
        data class Granted(val product: String, val unlocked: List<String>) : Status

        /**
         * A real state and not an error: a Play cash payment can be pending for
         * days. Nothing is owed and nothing is unlocked until Google settles it,
         * and the store notification that settles it will grant on its own.
         */
        data class Pending(val product: String) : Status

        /** The person closed the sheet. Not a failure; do not apologise for it. */
        data object Cancelled : Status

        /**
         * Play refused, or the server did.
         *
         * [paid] is the difference between two apologies that must not be the
         * same sentence. Before the sheet closes, a failure means no money
         * moved and "nothing has been charged" is true. After it — a
         * verification that answered 503, a network that died between Play and
         * us — Google *has* taken the payment, and telling that person nothing
         * was charged is the one lie this screen could tell that they can check
         * against their bank.
         */
        data class Failed(
            val product: String?,
            val failure: ApiFailure,
            val paid: Boolean = false,
        ) : Status
    }

    private val _status = MutableStateFlow<Status>(Status.Idle)
    val status: StateFlow<Status> = _status.asStateFlow()

    /**
     * Forget the last outcome.
     *
     * This state outlives the screen that caused it — it is held by the
     * container for the life of the process — so without this a paywall
     * dismissed after a refusal would open again days later still showing it.
     * Called when a screen has finished saying what a [Status.Cancelled] or
     * [Status.Failed] meant, never to hide one that has not been shown.
     */
    fun clear() {
        _status.value = Status.Idle
    }

    /**
     * Emitted once per grant, for the screens that must react rather than
     * render — a paywall closing, a chapter re-fetching itself.
     *
     * A [SharedFlow] rather than the state above because a grant is an event: a
     * screen that subscribes afterwards should not be told about a purchase it
     * missed and open a celebration for it.
     */
    private val _grants = MutableSharedFlow<Status.Granted>(
        replay = 0,
        extraBufferCapacity = 1,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
    )
    val grants: SharedFlow<Status.Granted> = _grants.asSharedFlow()

    private val purchasesUpdated = PurchasesUpdatedListener { result, purchases ->
        when (result.responseCode) {
            BillingClient.BillingResponseCode.OK ->
                purchases.orEmpty().forEach { purchase -> scope.launch { redeem(purchase) } }

            BillingClient.BillingResponseCode.USER_CANCELED ->
                _status.value = Status.Cancelled

            // Play's own answer for "they already own this". Not an error: it
            // means the grant is somewhere we have not looked, so look.
            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED ->
                scope.launch { restore() }

            else -> _status.value = Status.Failed(null, result.asFailure())
        }
    }

    private val billing: BillingClient = BillingClient.newBuilder(context.applicationContext)
        .setListener(purchasesUpdated)
        // Required from Billing 7 onward, and it is what makes the `Pending`
        // state above reachable rather than theoretical: without it, Play
        // refuses to start a flow that could end in a pending cash payment.
        .enablePendingPurchases(
            PendingPurchasesParams.newBuilder()
                .enableOneTimeProducts()
                .enablePrepaidPlans()
                .build()
        )
        .build()

    /**
     * Connect, and keep connected.
     *
     * Play drops the service connection whenever it feels like it — an app
     * update to Play itself is enough — so reconnection is not an error path,
     * it is the normal lifecycle. Anything that needs the client waits on
     * [ensureConnected] rather than assuming.
     */
    private suspend fun ensureConnected(): Boolean {
        if (billing.isReady) return true
        return suspendCoroutine { continuation ->
            billing.startConnection(object : BillingClientStateListener {
                override fun onBillingSetupFinished(result: BillingResult) {
                    continuation.resume(result.responseCode == BillingClient.BillingResponseCode.OK)
                }

                override fun onBillingServiceDisconnected() {
                    // Nothing here. Resuming with `false` would be wrong — this
                    // fires on *later* disconnections too, and a coroutine can
                    // only be resumed once. The next call reconnects.
                }
            })
        }
    }

    /**
     * Look up what Play will charge for these products.
     *
     * The catalogue from our own backend is the source of truth for *what is on
     * the shelf*; Play is the source of truth for *what a price says* on this
     * device, because Play does the currency and the local tax. A paywall that
     * printed our catalogue's `display` next to a Play sheet showing a different
     * number would be a store rejection and, more to the point, a lie.
     *
     * @param productIds Play product ids — **not** catalogue slugs. Build them
     *   with [StoreProducts.productId]; the console cannot hold a hyphen, so
     *   `birth-card` is `alma.birth_card` there.
     */
    suspend fun productDetails(
        productIds: List<String>,
        type: String = BillingClient.ProductType.INAPP,
    ): List<ProductDetails> {
        if (!ensureConnected()) return emptyList()
        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(
                productIds.map { id ->
                    QueryProductDetailsParams.Product.newBuilder()
                        .setProductId(id)
                        .setProductType(type)
                        .build()
                }
            )
            .build()
        val result = billing.queryProductDetails(params)
        return result.productDetailsList.orEmpty()
    }

    /**
     * Open Play's sheet.
     *
     * Returns as soon as the sheet is on screen; the outcome arrives through
     * [status] and [grants], because Play delivers it to the listener and not
     * to this call.
     */
    suspend fun purchase(
        activity: Activity,
        details: ProductDetails,
        offerToken: String? = null,
    ) {
        // The last gate in front of a product id this build does not sell, and
        // it is here rather than only in the paywall on purpose: a Play product
        // id exists whether or not our catalogue listed it, so the app is the
        // only thing standing between it and a direct purchase. A screen is a
        // place a rule gets copied wrong; this is the place it cannot be.
        //
        // Отдельного списка «никогда в одиночку» больше нет: условные цены
        // (`archive-bump`) сняты вместе с архивом — монетизация v3. Осталась
        // проверка, которая и была главной: идентификатор, которого нет в
        // каталоге этой сборки, не продаётся. Право отказать по составу полки
        // остаётся у сервера (`entitlements.may_be_offered`) и у
        // `StoreProducts.sellable`, который читает полку **этого** аккаунта.
        val slug = StoreProducts.slugFor(details.productId)
        if (slug == null) {
            Log.w(TAG, "refused to sell ${details.productId} — not a product this app offers")
            _status.value = Status.Failed(
                slug,
                ApiFailure.Invalid("${details.productId} is not sold on its own"),
            )
            return
        }

        if (!ensureConnected()) {
            _status.value = Status.Failed(slug, ApiFailure.Unavailable("Play is not available"))
            return
        }
        _status.value = Status.Working(slug)

        val product = BillingFlowParams.ProductDetailsParams.newBuilder()
            .setProductDetails(details)
            .apply {
                // Subscriptions carry an offer token; one-time products do not,
                // and passing an empty one to a one-time product is a
                // DEVELOPER_ERROR rather than a no-op.
                val token = offerToken
                    ?: details.subscriptionOfferDetails?.firstOrNull()?.offerToken
                if (token != null) setOfferToken(token)
            }
            .build()

        val params = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(listOf(product))
            .build()

        val result = billing.launchBillingFlow(activity, params)
        if (result.responseCode != BillingClient.BillingResponseCode.OK) {
            _status.value = Status.Failed(slug, result.asFailure())
        }
    }

    /**
     * What one pass of [restore] actually did.
     *
     * Four numbers rather than one, because the single `found` counter this
     * replaced conflated states that need different sentences and different
     * next steps. It counted every purchase Play returned, before `redeem` had
     * decided anything — including `PENDING` ones and including product ids
     * this build cannot map — so somebody holding only one of those was told
     * nothing at all: no "Google has no record", no explanation, and a reload
     * that changed nothing.
     */
    @Suppress("unused") // `unknown` is read by the paywall's log, not its copy.
    data class Restored(
        /** Purchases that reached a grant on this account. */
        val granted: Int = 0,
        /** Play cash payments still settling. Nothing is owed yet. */
        val pending: Int = 0,
        /** Presented, and we could not confirm them. The unhappy middle. */
        val unconfirmed: Int = 0,
        /** Product ids this build does not sell — an older price list, another app. */
        val unknown: Int = 0,
    ) {
        /** Whether Play returned anything at all. Zero means Google has no record. */
        val any: Boolean get() = granted + pending + unconfirmed + unknown > 0
    }

    /**
     * Re-present everything Play thinks this person owns.
     *
     * Called at launch and on resume, both product types. Cheap, idempotent,
     * and the reason a purchase interrupted by a dead battery still lands.
     *
     * [_status] is set **once, at the end, from the aggregate** rather than
     * inside the loop. Driving it per purchase meant restoring two, where the
     * first granted and the second failed, left the screen showing the failure.
     */
    suspend fun restore(): Restored {
        if (!ensureConnected()) return Restored()

        var granted = 0
        var pending = 0
        var unconfirmed = 0
        var unknown = 0
        var lastGrant: Status.Granted? = null
        var lastFailure: Status.Failed? = null

        listOf(BillingClient.ProductType.INAPP, BillingClient.ProductType.SUBS).forEach { type ->
            val params = QueryPurchasesParams.newBuilder().setProductType(type).build()
            val result = billing.queryPurchasesAsync(params)
            result.purchasesList.forEach { purchase ->
                when (val outcome = redeem(purchase, publish = false)) {
                    is Status.Granted -> { granted++; lastGrant = outcome }
                    is Status.Pending -> pending++
                    is Status.Failed -> { unconfirmed++; lastFailure = outcome }
                    else -> unknown++
                }
            }
        }

        // A grant outranks a failure: somebody who restored two purchases and
        // got one of them should see the good news, and the other is in the log.
        val outcome = lastGrant ?: lastFailure
        if (outcome != null) _status.value = outcome

        return Restored(granted, pending, unconfirmed, unknown)
    }

    /**
     * One purchase, from Play's word to the server's grant.
     *
     * The order of the six steps is the whole of this method's design:
     *
     * 1. The Play product id is turned into a catalogue slug. `/iap/verify`
     *    looks the product up in the catalogue by key, so sending it
     *    `alma.natal` answers 404 — money taken, nothing granted.
     * 2. A `PENDING` purchase is reported and left alone. Nothing is owed yet.
     * 3. **An account is waited for.** See [SessionHolder.awaitAccount]: a
     *    verification sent before the session request has answered goes out
     *    with no `Authorization` header, and the server mints a throwaway
     *    account to file Google's transaction against — permanently, because
     *    the transaction id is a primary key.
     * 4. The token goes to our server, which asks Google.
     * 5. Only once the grant is known to have landed **on this account** is the
     *    purchase acknowledged — see below, and see the class comment on why
     *    acknowledging first loses somebody's money silently.
     * 6. The session is told, so every screen sees the new entitlement at once.
     *
     * @param publish whether to write the outcome to [status]. False from
     *   [restore], which sets it once from the aggregate instead — a loop that
     *   published every purchase left two restored purchases showing whichever
     *   happened to be last rather than whichever mattered.
     * @return what happened, so [restore] can count outcomes rather than
     *   purchases. Null for a product this build does not sell.
     */
    private suspend fun redeem(purchase: Purchase, publish: Boolean = true): Status? {
        val productId = purchase.products.firstOrNull() ?: return null

        // A product id from an older price list, or from another app sharing
        // this Google account. Not ours to grant and not ours to acknowledge:
        // acknowledging a purchase we cannot verify would suppress the refund
        // that is the correct outcome for it.
        val slug = StoreProducts.slugFor(productId)
        if (slug == null) {
            Log.w(TAG, "ignoring a purchase of $productId — not a product this build sells")
            return null
        }

        if (purchase.purchaseState == Purchase.PurchaseState.PENDING) {
            return Status.Pending(slug).also { if (publish) _status.value = it }
        }
        if (purchase.purchaseState != Purchase.PurchaseState.PURCHASED) return null

        if (publish) _status.value = Status.Working(slug)

        // Before the request, not after. An unauthenticated verify is not a
        // retryable failure — it is a transaction filed against the wrong
        // account for good.
        if (!session.awaitAccount()) {
            Log.w(TAG, "not verifying $slug yet — this device has no account to grant to")
            return Status.Failed(
                slug,
                ApiFailure.Offline("no connection to Alma"),
                paid = true,
            ).also { if (publish) _status.value = it }
        }

        return when (val verified = client.verifyPurchase(slug, purchase.purchaseToken)) {
            is ApiResult.Ok -> {
                val answer = verified.data
                // **A 200 is not a grant.** `/iap/verify` answers
                // `already_claimed` both for our own replay — Play re-delivers
                // every unacknowledged purchase on every launch — and for a
                // transaction that belongs to a *different* Alma account, which
                // is the ordinary case for a guest on a reinstalled phone. Both
                // are 200s, and the only thing that tells them apart is
                // `unlocked`, which is always this account's own list.
                //
                // So two questions are asked, and either is enough. Did the
                // server say it granted just now, and does this account
                // actually hold what the purchase buys. The first covers a
                // product added to the catalogue after this release shipped;
                // the second covers every replay of something already owned.
                val landed = answer.status.startsWith("granted") ||
                    StoreProducts.grantLanded(slug, answer.unlocked)

                if (!landed) {
                    // Deliberately unacknowledged. Google refunds an
                    // unacknowledged purchase after three days, and that refund
                    // is the *correct* outcome here: somebody paid and this
                    // account holds nothing. Acknowledging would take away the
                    // one remedy they have left. The fix is account linking —
                    // it is in the backend's own open problems — and until it
                    // exists this is the honest failure.
                    Log.w(TAG, "$slug verified as '${answer.status}' but granted this account nothing")
                    return Status.Failed(
                        slug,
                        // Still locked, which is the truest thing that can be
                        // said about it. The interface has its own sentence for
                        // this case; this message is for a log.
                        ApiFailure.Locked(slug, null, "verified as '${answer.status}' and granted nothing"),
                        paid = true,
                    ).also { if (publish) _status.value = it }
                }

                if (!purchase.isAcknowledged) acknowledge(purchase)
                session.onPurchaseVerified(answer.unlocked)
                val granted = Status.Granted(slug, answer.unlocked)
                if (publish) _status.value = granted
                // Emitted whether or not the status was published: a grant is
                // an event, and a screen waiting to close on one should close
                // whether it arrived through a purchase or through a restore.
                _grants.tryEmit(granted)
                granted
            }

            is ApiResult.Err -> {
                // Left unacknowledged on purpose. Play will re-deliver it on the
                // next launch and `restore` will try again; if it never
                // succeeds, Google refunds after three days. Both outcomes are
                // better than a person who paid and got nothing.
                Log.w(TAG, "could not verify $slug: ${verified.failure.message}")
                // `paid` — Play has already told us this purchase is
                // PURCHASED, so the money moved whether or not our server
                // could be reached to confirm it.
                Status.Failed(slug, verified.failure, paid = true)
                    .also { if (publish) _status.value = it }
            }
        }
    }

    // TODO(Ф0.3): `pair.check` — расходуемый, и его надо **consume**, а не
    // только acknowledge. `consumeAsync` — то, что делает разовый товар
    // покупаемым заново; без него человек не сможет проверить второго
    // партнёра, а Play будет считать первую покупку вечной. Список — в
    // `StoreProducts.CONSUMED_AFTER_GRANT`, ветка пишется вместе с привязкой
    // покупки к партнёру (приложение А4): пока грант по паре не выписывается
    // вовсе, потреблять нечего.
    private suspend fun acknowledge(purchase: Purchase) {
        val params = AcknowledgePurchaseParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()
        val result = billing.acknowledgePurchase(params)
        if (result.responseCode != BillingClient.BillingResponseCode.OK) {
            // Worth a log and nothing more. The grant already happened
            // server-side; an unacknowledged purchase that Play later refunds
            // is reversed by the store notification, which is the seam's job.
            Log.w(TAG, "acknowledge failed: ${result.debugMessage}")
        }
    }

    /** Play's response codes, in the vocabulary the rest of the app speaks. */
    private fun BillingResult.asFailure(): ApiFailure = when (responseCode) {
        BillingClient.BillingResponseCode.NETWORK_ERROR,
        BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE,
        -> ApiFailure.Offline(debugMessage.ifBlank { "no connection to Play" })

        BillingClient.BillingResponseCode.BILLING_UNAVAILABLE,
        BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED,
        -> ApiFailure.Unavailable(debugMessage.ifBlank { "Play billing is unavailable" })

        else -> ApiFailure.Unexpected(responseCode, debugMessage.ifBlank { "Play refused the purchase" })
    }

    private companion object {
        const val TAG = "PlayBilling"
    }
}
