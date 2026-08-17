package ai.pazl.alma.billing

import ai.pazl.alma.data.AlmaSystem
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * What the paywall offers, and in what order — the v3 shelf.
 *
 * The Play half of the shelf cannot be tested without a store — `ProductDetails`
 * has no public constructor and is parsed from a store response — so the rule
 * that decides *what may be listed* is separated from the lookup that prices it,
 * and this is that rule.
 *
 * **Every expectation here is a catalogue key, never a system slug.** That is
 * the v3 change these tests exist to pin: until v3 the two were the same string
 * and the ladder could add `"natal"` to a list of things to buy. Now `"natal"`
 * is the name of what a product opens and `door.natal` is the product, so a
 * ladder that emits the system slug asks Play for a product no console has —
 * a purchase sheet that never opens.
 */
class ShelfLadderTest {

    /** The eight rows `catalogue.py` lists for an account with no history. */
    private val shelf = StoreProducts.ALL

    @Test
    fun `the door the person reached for comes first, then the bundle, then the plan`() {
        assertEquals(
            listOf(
                StoreProducts.DOOR_NATAL,
                StoreProducts.BUNDLE_STATIC,
                StoreProducts.SUB_MONTHLY,
            ),
            ladder(AlmaSystem.NATAL, shelf, emptyList()),
        )
    }

    @Test
    fun `reaching for nothing opens on the plan`() {
        // The chat opens the paywall with no system, because what is being
        // asked for there is more questions — and only the plan grants those.
        assertEquals(
            listOf(StoreProducts.SUB_MONTHLY, StoreProducts.BUNDLE_STATIC),
            ladder(null, shelf, emptyList()),
        )
    }

    @Test
    fun `a living system has no door, so the tap sells the subscription`() {
        // ТЗ §2 and P2: transits are recomputed every day and the solar return
        // is rewritten every birthday. Selling either "for ever" is selling a
        // subscription without charging for one, so neither has a door — and a
        // tap on their locked chapter must not answer with an empty screen.
        listOf(AlmaSystem.TRANSITS, AlmaSystem.SOLAR_RETURN).forEach { living ->
            assertEquals(
                living,
                listOf(StoreProducts.SUB_MONTHLY, StoreProducts.BUNDLE_STATIC),
                ladder(living, shelf, emptyList()),
            )
        }
    }

    @Test
    fun `compatibility is bought one partner at a time, not as a system`() {
        // `pair.check` opens one report about one person. A door here would be
        // "compatibility unlocked" after one purchase and a refusal on the
        // second partner.
        assertEquals(
            listOf(
                StoreProducts.PAIR_CHECK,
                StoreProducts.BUNDLE_STATIC,
                StoreProducts.SUB_MONTHLY,
            ),
            ladder(AlmaSystem.COMPATIBILITY, shelf, emptyList()),
        )
    }

    @Test
    fun `nothing already owned is offered again`() {
        val rows = ladder(AlmaSystem.NATAL, shelf, listOf(AlmaSystem.NATAL))
        assertFalse(rows.contains(StoreProducts.DOOR_NATAL))
        assertEquals(
            listOf(StoreProducts.BUNDLE_STATIC, StoreProducts.SUB_MONTHLY),
            rows,
        )
    }

    @Test
    fun `a live plan removes the plan row and nothing else`() {
        // Changing plan is done on Play's own screen, inside one subscription
        // group — never as a second purchase here.
        assertEquals(
            listOf(StoreProducts.DOOR_NATAL, StoreProducts.BUNDLE_STATIC),
            ladder(AlmaSystem.NATAL, shelf, emptyList(), hasPlan = true),
        )
    }

    @Test
    fun `a bundle owner keeps the plan and loses the bundle`() {
        // The bundle is five written readings; the plan also carries the layer
        // that moves. They are not the same purchase, so owning one does not
        // remove the other.
        assertEquals(
            listOf(StoreProducts.SUB_MONTHLY),
            ladder(null, shelf, AlmaSystem.ALL, ownsBundle = true),
        )
    }

    @Test
    fun `somebody holding the plan and the bundle is offered nothing at all`() {
        assertTrue(
            ladder(
                AlmaSystem.NATAL, shelf, AlmaSystem.ALL,
                hasPlan = true, ownsBundle = true,
            ).isEmpty()
        )
    }

    @Test
    fun `the pair check is offered again however many partners have been checked`() {
        // Consumable: it is bought once per partner, and the store must let it
        // be bought again. Filtering it by what is unlocked would mean the
        // second partner could never be checked.
        val rows = ladder(AlmaSystem.COMPATIBILITY, shelf, listOf(AlmaSystem.COMPATIBILITY))
        assertTrue(rows.contains(StoreProducts.PAIR_CHECK))
        assertEquals(StoreProducts.PAIR_CHECK, rows.first())
    }

    @Test
    fun `a product the server does not price in this currency is not offered`() {
        // Asking for a price that does not exist is `NotSold` on the server;
        // here it is simply an absent row, never our own number in its place.
        val thin = setOf(StoreProducts.BUNDLE_STATIC, StoreProducts.SUB_MONTHLY)
        assertEquals(
            listOf(StoreProducts.BUNDLE_STATIC, StoreProducts.SUB_MONTHLY),
            ladder(AlmaSystem.NATAL, thin, emptyList()),
        )
    }

    @Test
    fun `a withdrawn price is never listed, even if the server sends one`() {
        // The v3 shelf has no conditional prices left, and the gate stays shut
        // anyway: a store product id exists whether or not our shelf listed it,
        // and the first A/B on the bundle price puts two prices behind one
        // grant again.
        val leaky = shelf + "archive-upgrade" + "annual"
        val rows = ladder(null, leaky, emptyList())
        assertFalse(rows.contains("archive-upgrade"))
        assertFalse(rows.contains("annual"))
    }

    @Test
    fun `no rung is ever a system slug`() {
        // The whole v3 catalogue change in one assertion. `door.natal` is the
        // product; `natal` is what it opens. A rung spelled the second way is
        // an id no console has.
        AlmaSystem.ALL.forEach { system ->
            ladder(system, shelf, emptyList()).forEach { rung ->
                assertFalse(
                    "$rung is a system slug, not a catalogue key",
                    rung in AlmaSystem.ALL,
                )
                assertTrue("$rung is not in the catalogue", rung in StoreProducts.ALL)
            }
        }
    }
}
