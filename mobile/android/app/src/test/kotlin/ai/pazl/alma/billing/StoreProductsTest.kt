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
    fun `the shelf is the eight rows the backend catalogue lists`() {
        assertEquals(
            setOf(
                "door.natal", "door.numerology", "door.birth-card",
                "door.astrocartography", "door.synthesis",
                "pair.check", "bundle.static", "sub.monthly",
            ),
            StoreProducts.ALL,
        )
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
    fun `the one hyphenated key is spelled the way the backend spells it`() {
        // Pinned by hand rather than derived, because the rule and its
        // implementation being the same expression proves nothing.
        assertEquals("ai.pazl.alma.door.birth_card", StoreProducts.productId(StoreProducts.DOOR_BIRTH_CARD))
        assertEquals("ai.pazl.alma.door.natal", StoreProducts.productId(StoreProducts.DOOR_NATAL))
        assertEquals("ai.pazl.alma.pair.check", StoreProducts.productId(StoreProducts.PAIR_CHECK))
        assertEquals("ai.pazl.alma.bundle.static", StoreProducts.productId(StoreProducts.BUNDLE_STATIC))
        assertEquals("ai.pazl.alma.sub.monthly", StoreProducts.productId(StoreProducts.SUB_MONTHLY))
    }

    @Test
    fun `an id from another app, or from a price list we withdrew, is not ours`() {
        assertNull(StoreProducts.slugFor("com.other.app.subscription"))
        assertNull(StoreProducts.slugFor("ai.pazl.alma.chapter"))
        assertNull(StoreProducts.slugFor(""))
        // The v2 shelf, which is the one most likely to still be sitting in
        // somebody's Google account. A purchase of it is a payment to leave
        // alone, not a chapter to unlock.
        assertNull(StoreProducts.slugFor("ai.pazl.alma.archive"))
        assertNull(StoreProducts.slugFor("ai.pazl.alma.annual"))
        assertNull(StoreProducts.slugFor("ai.pazl.alma.archive_upgrade"))
        // And the older prefix, from before `ai.pazl.alma.` was settled.
        assertNull(StoreProducts.slugFor("alma.natal"))
    }

    @Test
    fun `a system slug is not a product key`() {
        // The v3 split. `product("natal")` fails honestly on the server for the
        // same reason: the key is `door.natal`, and asking Play for
        // `ai.pazl.alma.natal` opens a sheet with nothing in it.
        AlmaSystem.ALL.forEach { system ->
            assertFalse("$system is being sold as a product", system in StoreProducts.ALL)
        }
    }

    @Test
    fun `the subscription is the only thing Play sells as SUBS`() {
        assertEquals(
            BillingClient.ProductType.SUBS,
            StoreProducts.productType(StoreProducts.SUB_MONTHLY),
        )
        listOf(
            StoreProducts.DOOR_NATAL,
            StoreProducts.BUNDLE_STATIC,
            StoreProducts.PAIR_CHECK,
        ).forEach { slug ->
            assertEquals(slug, BillingClient.ProductType.INAPP, StoreProducts.productType(slug))
        }
    }

    @Test
    fun `the pair check is the only product Play must consume`() {
        // A consumed door would be a permanent unlock somebody can be charged
        // for twice; an unconsumed pair check makes the second partner
        // unbuyable.
        assertEquals(setOf(StoreProducts.PAIR_CHECK), StoreProducts.CONSUMED_AFTER_GRANT)
    }

    @Test
    fun `only the five static systems have a door`() {
        StoreProducts.STATIC.forEach { system ->
            assertEquals(
                system,
                "door.$system",
                StoreProducts.doorFor(system),
            )
        }
        // Transits and the solar return recompute, and compatibility is bought
        // per partner. None of the three may be sold as a permanent door.
        StoreProducts.LIVING.forEach { system ->
            assertNull("$system must not have a door", StoreProducts.doorFor(system))
        }
    }

    @Test
    fun `a door names its own system and the wide products name none`() {
        assertEquals(AlmaSystem.NATAL, StoreProducts.systemFor(StoreProducts.DOOR_NATAL))
        assertEquals(AlmaSystem.BIRTH_CARD, StoreProducts.systemFor(StoreProducts.DOOR_BIRTH_CARD))
        assertNull(StoreProducts.systemFor(StoreProducts.BUNDLE_STATIC))
        assertNull(StoreProducts.systemFor(StoreProducts.SUB_MONTHLY))
        // Deliberately null and not `compatibility`: a pair check opens one
        // report about one person, not the system.
        assertNull(StoreProducts.systemFor(StoreProducts.PAIR_CHECK))
    }

    @Test
    fun `a door has landed only when its own system is unlocked`() {
        assertTrue(StoreProducts.grantLanded(StoreProducts.DOOR_NATAL, listOf("natal")))
        assertFalse(StoreProducts.grantLanded(StoreProducts.DOOR_NATAL, listOf("numerology")))
        assertFalse(StoreProducts.grantLanded(StoreProducts.DOOR_NATAL, emptyList()))
    }

    @Test
    fun `the bundle has landed only when all five static readings are unlocked`() {
        assertTrue(StoreProducts.grantLanded(StoreProducts.BUNDLE_STATIC, StoreProducts.STATIC))
        assertFalse(
            StoreProducts.grantLanded(
                StoreProducts.BUNDLE_STATIC,
                StoreProducts.STATIC - AlmaSystem.SYNTHESIS,
            )
        )
        // The living layer is not part of it, and its absence must not hold the
        // grant back.
        assertTrue(StoreProducts.grantLanded(StoreProducts.BUNDLE_STATIC, AlmaSystem.ALL))
    }

    @Test
    fun `the subscription has landed only when all eight systems are unlocked`() {
        assertTrue(StoreProducts.grantLanded(StoreProducts.SUB_MONTHLY, AlmaSystem.ALL))
        assertFalse(
            StoreProducts.grantLanded(StoreProducts.SUB_MONTHLY, AlmaSystem.ALL - AlmaSystem.SYNTHESIS)
        )
        // A bundle owner is not a subscriber: five static readings are not the
        // three that move.
        assertFalse(StoreProducts.grantLanded(StoreProducts.SUB_MONTHLY, StoreProducts.STATIC))
    }

    @Test
    fun `a pair check never counts as landed, whatever is unlocked`() {
        // Its grant names the partner (`pair:{profile_id}`) and never appears
        // in `unlocked` at all. Checking it against that list would mean never
        // acknowledging the purchase — Google's three-day auto-refund taking
        // the money back from somebody who got everything they paid for.
        assertFalse(StoreProducts.grantLanded(StoreProducts.PAIR_CHECK, AlmaSystem.ALL))
        assertFalse(StoreProducts.grantLanded(StoreProducts.PAIR_CHECK, emptyList()))
    }

    @Test
    fun `a slug this build has never heard of never counts as landed`() {
        // The caller's other question — did the server say "granted" — is what
        // covers a product added after this release. Guessing here would
        // acknowledge a purchase that unlocked nothing, and acknowledging is
        // what switches off Google's three-day refund.
        assertFalse(StoreProducts.grantLanded("ninth-system", AlmaSystem.ALL))
        assertFalse(StoreProducts.grantLanded("archive", AlmaSystem.ALL))
    }

    @Test
    fun `nothing is sellable that this account's own catalogue did not list`() {
        assertTrue(StoreProducts.sellable(StoreProducts.DOOR_NATAL, StoreProducts.ALL))
        assertFalse(StoreProducts.sellable(StoreProducts.DOOR_NATAL, listOf(StoreProducts.SUB_MONTHLY)))
        // A withdrawn price the server could not have listed, asked for by name.
        assertFalse(StoreProducts.sellable("archive-upgrade", StoreProducts.ALL))
    }

    @Test
    fun `the manage link points at the row, not at the list`() {
        val url = StoreProducts.manageSubscriptionUrl(
            "ai.pazl.alma",
            StoreProducts.productId(StoreProducts.SUB_MONTHLY),
        )
        assertTrue(url.contains("sku=ai.pazl.alma.sub.monthly"))
        assertTrue(url.contains("package=ai.pazl.alma"))
        // With no product it is still a working link rather than a broken one.
        assertEquals(
            "https://play.google.com/store/account/subscriptions",
            StoreProducts.manageSubscriptionUrl("ai.pazl.alma", null),
        )
    }
}
