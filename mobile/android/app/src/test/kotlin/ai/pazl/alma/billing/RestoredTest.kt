package ai.pazl.alma.billing

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * What a restore is allowed to conclude.
 *
 * The counter this replaced was incremented once per purchase Play returned,
 * *before* `redeem` had decided anything — so a pending cash payment or a
 * product id from an older price list both counted as "found", the paywall's
 * `NothingFound` branch never fired, and the person who tapped restore got a
 * reload that changed nothing and no sentence at all.
 *
 * These are the three distinctions that were being collapsed, tested on the
 * type rather than through `BillingClient`, which cannot be instantiated off a
 * device.
 */
class RestoredTest {

    @Test
    fun `nothing at all is the only case that means Google has no record`() {
        assertFalse(PlayBilling.Restored().any)
    }

    @Test
    fun `a pending purchase is not nothing`() {
        // "Google has no purchase on this account" would be a flat falsehood
        // here: Google has one and is waiting for cash.
        assertTrue(PlayBilling.Restored(pending = 1).any)
    }

    @Test
    fun `a purchase we could not confirm is not nothing either`() {
        // The unhappy middle, and the one that must not read as "no purchase":
        // it is deliberately left unacknowledged so Google refunds in three
        // days, and the person is entitled to know that is what is happening.
        assertTrue(PlayBilling.Restored(unconfirmed = 1).any)
    }

    @Test
    fun `a product this build does not sell still counts as something Play returned`() {
        // Not restorable *here*, which from the reader's side is the same
        // sentence as nothing — but the count is kept separate so the log can
        // tell an old price list apart from an empty account.
        assertTrue(PlayBilling.Restored(unknown = 1).any)
    }

    @Test
    fun `a grant is counted on its own`() {
        val restored = PlayBilling.Restored(granted = 2, unconfirmed = 1)
        assertTrue(restored.any)
        assertTrue(restored.granted == 2)
    }
}
