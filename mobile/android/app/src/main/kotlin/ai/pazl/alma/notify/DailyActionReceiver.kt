package ai.pazl.alma.notify

import ai.pazl.alma.AlmaApplication
import ai.pazl.alma.R
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.widget.Toast

/**
 * "Turn these off" and "Fewer of these", from inside the notification.
 *
 * A receiver rather than an activity, because the point of these two buttons is
 * that they cost one tap and no attention. Launching the app to confirm that
 * somebody wants fewer notifications is how a mildly irritated subscriber
 * becomes an uninstall — and an uninstall costs the entire remaining lifetime of
 * the subscription, where a person who taps *Fewer of these* is still paying.
 *
 * **Off deletes the token row, it does not set a flag.** `docs/PUSH.md §6.2(6)`:
 * a flag is a thing a future job can forget to read, and the row is the simplest
 * possible proof that off means off. It is also the withdrawal-of-consent
 * obligation Guideline 4.5.4 and Play's own policy put on us.
 *
 * The `goAsync` dance is not ceremony. `onReceive` runs on the main thread and
 * the process may be killed the moment it returns, so a network call started
 * without holding the broadcast open is a network call that may never leave the
 * device — which would leave somebody who tapped *Turn these off* still
 * receiving.
 */
class DailyActionReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val application = context.applicationContext as? AlmaApplication ?: return
        val daily = application.container.daily

        val message = when (intent.action) {
            ACTION_TURN_OFF -> R.string.daily_action_turned_off
            // One step down rather than off. The person said "fewer", and
            // hearing "fewer" as "none" is how a quieter subscriber becomes an
            // uninstall two months later.
            ACTION_QUIETER -> R.string.daily_action_quieter_done
            else -> return
        }

        DailyNotifications.clear(context)
        // Said out loud, because a button that appears to do nothing is a button
        // somebody presses again and then stops trusting. The wording is the
        // same reassurance the settings detail line carries — Today is still
        // there — so that turning it off does not read as losing something.
        Toast.makeText(context, message, Toast.LENGTH_LONG).show()

        val pending = goAsync()
        daily.applyNotificationAction(intent.action) { pending.finish() }
    }

    companion object {
        const val ACTION_TURN_OFF = "ai.pazl.alma.DAILY_TURN_OFF"
        const val ACTION_QUIETER = "ai.pazl.alma.DAILY_QUIETER"
    }
}
