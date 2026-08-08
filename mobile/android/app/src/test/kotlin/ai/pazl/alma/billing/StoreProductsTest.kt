package ai.pazl.alma.billing

import ai.pazl.alma.data.AlmaSystem
import com.android.billingclient.api.BillingClient
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The rules that decide what is charged for and what is unlocked, tested
 * against the backend's own source rather than against this app's behaviour.
 *
 * Each case here corresponds to a line in `backend/alma/billing/provider.py` or
 * `catalogue.py`, and two of them are the shape of a bug that has already been
 * paid for once: an id sent to the store in the catalogue's spelling, and a
 * purchase acknowledged when nothing was granted.
 */
class StoreProductsTest {

    @Test
    fun `every catalogue key survives the trip to the console and back`() {
        StoreProducts.ALL.forEach { slug ->
            assertEquals(slug, StoreProducts.slugFor(StoreProducts.productId(slug)))
        }
    }

    @Test
    fun `no product id carries a hyphen, because neither console accepts one`() {
        StoreProducts.ALL.forEach { slug ->
            val id = StoreProducts.productId(slug)
            assertFalse("$id still has a hyphen in it", id.contains('-'))
            assertTrue(id.startsWith(StoreProducts.PREFIX))
        }
    }

    @Test
    fun `the four hyphenated keys are spelled the way the backend spells them`() {
        // Pinned by hand rather than derived, because the rule and its
        // implementation being the same expression proves nothing.
        assertEquals("alma.birth_card", StoreProducts.productId(AlmaSystem.BIRTH_CARD))
        assertEquals("alma.solar_return", StoreProducts.productId(AlmaSystem.SOLAR_RETURN))
        assertEquals("alma.archive_bump", StoreProducts.productId(StoreProducts.ARCHIVE_BUMP))
        assertEquals("alma.archive_upgrade", StoreProducts.productId(StoreProducts.ARCHIVE_UPGRADE))
    }

    @Test
    fun `an id from another app, or from a price list we withdrew, is not ours`() {
        assertNull(StoreProducts.slugFor("com.other.app.subscription"))
        assertNull(StoreProducts.slugFor("alma.chapter"))
        assertNull(StoreProducts.slugFor(""))
        // The old single-chapter SKU's shape, which is the one most likely to
        // still be sitting in somebody's Google account.
        assertNull(StoreProducts.slugFor("alma.natal_chapter"))
    }

    @Test
    fun `subscriptions are the only two that Play sells as SUBS`() {
        assertEquals(BillingClient.ProductType.SUBS, StoreProducts.productType(StoreProducts.MONTHLY))
        assertEquals(BillingClient.ProductType.SUBS, StoreProducts.productType(StoreProducts.ANNUAL))
        assertEquals(BillingClient.ProductType.INAPP, StoreProducts.productType(AlmaSystem.NATAL))
        assertEquals(BillingClient.ProductType.INAPP, StoreProducts.productType(StoreProducts.ARCHIVE))
    }

    @Test
    fun `the in-checkout bump is never sellable, whatever the server says`() {
        // Even in the impossible case where it appears in a catalogue response:
        // it grants everything the archive grants, nine dollars cheaper, and a
        // store product id exists whether or not our shelf listed it.
        val everything = StoreProducts.ALL
        assertFalse(StoreProducts.sellable(StoreProducts.ARCHIVE_BUMP, everything))
    }

    @Test
    fun `the upgrade price is sellable only when this account was offered it`() {
        assertFalse(
            StoreProducts.sellable(StoreProducts.ARCHIVE_UPGRADE, listOf("archive", "annual"))
        )
        assertTrue(
            StoreProducts.sellable(StoreProducts.ARCHIVE_UPGRADE, listOf("archive-upgrade", "annual"))
        )
    }

    @Test
    fun `a door has landed only when its own system is unlocked`() {
        assertTrue(StoreProducts.grantLanded(AlmaSystem.NATAL, listOf("natal")))
        assertFalse(StoreProducts.grantLanded(AlmaSystem.NATAL, listOf("numerology")))
        assertFalse(StoreProducts.grantLanded(AlmaSystem.NATAL, emptyList()))
    }

    @Test
    fun `an everything-grant has landed only when all eight are unlocked`() {
        val everything = AlmaSystem.ALL
        val allButOne = AlmaSystem.ALL - AlmaSystem.SYNTHESIS

        listOf(
            StoreProducts.ARCHIVE,
            StoreProducts.ARCHIVE_UPGRADE,
            StoreProducts.ANNUAL,
        ).forEach { slug ->
            assertTrue(slug, StoreProducts.grantLanded(slug, everything))
            assertFalse(slug, StoreProducts.grantLanded(slug, allButOne))
        }
    }

    @Test
    fun `a monthly plan has landed when the three living systems are unlocked`() {
        // And *only* the three. A monthly subscriber does not hold the archive,
        // which is the disagreement `unlocked_systems` was fixed for: the hub
        // drew the natal report as owned and the access check refused it.
        assertTrue(StoreProducts.grantLanded(StoreProducts.MONTHLY, StoreProducts.LIVING))
        assertFalse(
            StoreProducts.grantLanded(StoreProducts.MONTHLY, listOf(AlmaSystem.TRANSITS))
        )
        assertFalse(StoreProducts.grantLanded(StoreProducts.ARCHIVE, StoreProducts.LIVING))
    }

    @Test
    fun `a slug this build has never heard of never counts as landed`() {
        // The caller's other question — did the server say "granted" — is what
        // covers a product added after this release. Guessing here would
        // acknowledge a purchase that unlocked nothing, and acknowledging is
        // what switches off Google's three-day refund.
        assertFalse(StoreProducts.grantLanded("ninth-system", AlmaSystem.ALL))
    }

    @Test
    fun `the manage link points at the row, not at the list`() {
        val url = StoreProducts.manageSubscriptionUrl("ai.pazl.alma", "alma.annual")
        assertTrue(url.contains("sku=alma.annual"))
        assertTrue(url.contains("package=ai.pazl.alma"))
        // With no product it is still a working link rather than a broken one.
        assertEquals(
            "https://play.google.com/store/account/subscriptions",
            StoreProducts.manageSubscriptionUrl("ai.pazl.alma", null),
        )
    }
}
