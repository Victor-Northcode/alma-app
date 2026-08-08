package ai.pazl.alma.billing

import ai.pazl.alma.data.AlmaSystem
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * What the paywall offers, and in what order.
 *
 * The Play half of the shelf cannot be tested without a store — `ProductDetails`
 * has no public constructor and is parsed from a store response — so the rule
 * that decides *what may be listed* is separated from the lookup that prices it,
 * and this is that rule.
 */
class ShelfLadderTest {

    /** Everything the server lists for an account with no history. */
    private val shelf = setOf(
        AlmaSystem.NATAL, AlmaSystem.NUMEROLOGY, AlmaSystem.BIRTH_CARD, AlmaSystem.TRANSITS,
        AlmaSystem.SOLAR_RETURN, AlmaSystem.COMPATIBILITY, AlmaSystem.ASTROCARTOGRAPHY,
        AlmaSystem.SYNTHESIS, StoreProducts.ARCHIVE, StoreProducts.MONTHLY, StoreProducts.ANNUAL,
    )

    @Test
    fun `the door the person reached for comes first, plans after the archive`() {
        assertEquals(
            listOf(
                AlmaSystem.COMPATIBILITY, StoreProducts.ARCHIVE,
                StoreProducts.ANNUAL, StoreProducts.MONTHLY,
            ),
            ladder(AlmaSystem.COMPATIBILITY, shelf, emptyList()),
        )
    }

    @Test
    fun `reaching for nothing opens on the plans, annual above monthly`() {
        // The chat opens the paywall with no system, because what is being
        // asked for there is more questions — and only the plan grants those.
        // The annual leads: it takes 60–70% of plan sales when it does, and
        // annual subscribers retain better a year on.
        assertEquals(
            listOf(
                StoreProducts.ANNUAL, StoreProducts.MONTHLY,
                StoreProducts.ARCHIVE,
            ),
            ladder(null, shelf, emptyList()),
        )
    }

    @Test
    fun `the upgrade stands in for the archive when the server substituted it`() {
        val substituted = shelf - StoreProducts.ARCHIVE + StoreProducts.ARCHIVE_UPGRADE
        assertEquals(
            listOf(
                AlmaSystem.NATAL, StoreProducts.ARCHIVE_UPGRADE,
                StoreProducts.ANNUAL, StoreProducts.MONTHLY,
            ),
            ladder(AlmaSystem.NATAL, substituted, listOf(AlmaSystem.NUMEROLOGY)),
        )
    }

    @Test
    fun `nothing already owned is offered again`() {
        val rows = ladder(AlmaSystem.NATAL, shelf, listOf(AlmaSystem.NATAL))
        assertFalse(rows.contains(AlmaSystem.NATAL))
        assertEquals(
            listOf(StoreProducts.ARCHIVE, StoreProducts.ANNUAL, StoreProducts.MONTHLY),
            rows,
        )
    }

    @Test
    fun `a live plan removes both plan rows and nothing else`() {
        // Selling an annual to a monthly subscriber is a *change* inside one
        // Play subscription group, done on Play's own screen — never a second
        // purchase here.
        assertEquals(
            listOf(StoreProducts.ARCHIVE),
            ladder(null, shelf, AlmaSystem.ALL, hasPlan = true),
        )
    }

    @Test
    fun `an archive owner keeps the plans and loses the archive`() {
        // The archive is forty-one written chapters; the living layer is
        // transits that move. They are not the same purchase.
        assertEquals(
            listOf(StoreProducts.ANNUAL, StoreProducts.MONTHLY),
            ladder(null, shelf, AlmaSystem.ALL, ownsArchive = true),
        )
    }

    @Test
    fun `somebody holding a plan and the archive is offered nothing at all`() {
        assertTrue(
            ladder(
                AlmaSystem.NATAL, shelf, AlmaSystem.ALL,
                hasPlan = true, ownsArchive = true,
            ).isEmpty()
        )
    }

    @Test
    fun `a conditional price is never listed, even if the server sends one`() {
        val leaky = shelf + StoreProducts.ARCHIVE_BUMP
        assertFalse(ladder(null, leaky, emptyList()).contains(StoreProducts.ARCHIVE_BUMP))
    }

    @Test
    fun `a system the server does not price in this currency is not offered`() {
        // The PPP markets get the archive and the year and nothing else — a
        // door at a PPP-fair price loses money to VAT and the flat fee. Asking
        // for one is `NotSold` on the server; here it is simply absent.
        val brazil = setOf(StoreProducts.ARCHIVE, StoreProducts.ANNUAL)
        assertEquals(
            listOf(StoreProducts.ARCHIVE, StoreProducts.ANNUAL),
            ladder(AlmaSystem.NATAL, brazil, emptyList()),
        )
    }
}
