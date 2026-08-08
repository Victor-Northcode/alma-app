package ai.pazl.alma.notify

import ai.pazl.alma.MainActivity
import ai.pazl.alma.R
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

/**
 * The channels, the payload, and what a tap does.
 *
 * ## Two channels, never one
 *
 * A channel id is **permanent for an install**: it cannot be renamed, merged or
 * re-scoped once a notification has been posted to it, and the only way out is
 * a new id, which reads to the person as a new kind of notification appearing
 * out of nowhere. So this is a one-line decision at build time that is very
 * expensive afterwards, and it is worth spending the paragraph.
 *
 * The daily and the renewal notice must not share one. The renewal notice is a
 * promise the subscription-terms page makes in six languages — it says plainly
 * that it is not marketing and cannot be unsubscribed from — and a shared
 * channel would let somebody silence a legal commitment by silencing a
 * horoscope. `docs/PUSH.md §6.2(5)`.
 *
 * The renewal channel is created here even though nothing posts to it yet
 * (`alma/billing/renewals.py` sends email and has never been scheduled). Creating
 * both at the same moment is what stops a future change from taking the
 * expedient path and reusing the one that already exists.
 *
 * ## The payload is a key, never a sentence
 *
 * FCM sends `body_loc_key` plus `body_loc_args` and Android resolves the key
 * against this app's own string resources, in the *device's* language. Three
 * things follow, and they are the whole argument of `docs/PUSH.md §1.6`: the six
 * translations live in the app bundle and pass the same locale gate as every
 * other string in the product; the payload carries a key and three words rather
 * than a statement about somebody's birth chart; and the server never has to
 * decide what language a phone is in.
 *
 * The functions below therefore never compose a sentence either. [post] takes
 * an already-resolved title and body — because when FCM delivers a
 * `notification` message the *system* builds the notification and this code is
 * not involved at all — and exists for the data-message path and for the
 * developer build's "post one of these" affordance.
 */
object DailyNotifications {

    /** The daily. About once a week, and silenceable on its own. */
    const val CHANNEL_DAILY = "alma.daily"

    /** Money. Separate, and never merged with the above. */
    const val CHANNEL_RENEWAL = "alma.subscription"

    /** Extras on the intent a tap delivers to [MainActivity]. */
    const val EXTRA_KIND = "alma.notification.kind"
    const val EXTRA_DATE = "alma.notification.date"
    const val KIND_DAILY = "daily"

    /**
     * One notification at a time, replaced rather than stacked.
     *
     * A fixed id is the local half of `apns-collapse-id` / `collapse_key`: a
     * retry, or a job that ran twice, replaces Thursday's notification instead
     * of leaving two of them. `PUSH.md §6.2(4)`.
     */
    private const val NOTIFICATION_ID = 1_001

    /**
     * Create both channels. Idempotent — Android ignores a channel that exists,
     * except for the name and description, which it updates.
     *
     * Called at process start rather than at first send, because a channel that
     * exists is a row in the system's own settings screen: it lets somebody
     * turn the daily off from Android's UI before we have ever sent one, which
     * is a route out that costs us nothing to provide.
     */
    fun createChannels(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java) ?: return

        val daily = NotificationChannel(
            CHANNEL_DAILY,
            context.getString(R.string.daily_channel_name),
            // **DEFAULT and not HIGH.** Importance decides whether Android
            // interrupts, and claiming urgency for something that is not urgent
            // is a small dishonesty the operating system eventually charges for
            // in its own delivery heuristics. It is also the honest level: the
            // daily is about a day, and a day is not an interruption.
            NotificationManager.IMPORTANCE_DEFAULT,
        ).apply {
            description = context.getString(R.string.daily_channel_description)
            // No badge. A dot on the launcher icon for something that is not a
            // message waiting is the kind of pressure this feature exists not
            // to apply.
            setShowBadge(false)
        }

        val renewal = NotificationChannel(
            CHANNEL_RENEWAL,
            context.getString(R.string.renewal_channel_name),
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = context.getString(R.string.renewal_channel_description)
        }

        manager.createNotificationChannel(daily)
        manager.createNotificationChannel(renewal)
    }

    /**
     * Whether the operating system will actually show one.
     *
     * `areNotificationsEnabled()` and not a flag of ours: a person can turn Alma
     * off in Android's settings, or turn off just this channel, and will never
     * tell us they did. `PUSH.md §5.6`.
     */
    fun enabled(context: Context): Boolean =
        NotificationManagerCompat.from(context).areNotificationsEnabled()

    /**
     * Whether the daily's own channel has been silenced, which is a different
     * thing from the app being silenced and needs a different sentence.
     */
    fun channelSilenced(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return false
        val manager = context.getSystemService(NotificationManager::class.java) ?: return false
        val channel = manager.getNotificationChannel(CHANNEL_DAILY) ?: return false
        return channel.importance == NotificationManager.IMPORTANCE_NONE
    }

    /**
     * Post one.
     *
     * [title] and [body] arrive already resolved, because the localisation is
     * the *system's* job on the FCM `notification` path and this function must
     * not become a second place where a sentence is assembled.
     *
     * Two actions ride on every one of them. `THE-DAILY.md §5.2` requires a
     * permanent turn-off *inside* the notification — an action button, not a
     * deep link into a settings tree — and the reasoning is worth keeping next
     * to the code: the design goal is to make the disable path so easy that
     * nobody reaches for the uninstall path. An uninstall costs the whole
     * remaining subscription; a person who taps "Fewer of these" is still a
     * subscriber.
     */
    fun post(context: Context, title: String, body: String, day: String?) {
        if (!enabled(context)) return

        val notification = NotificationCompat.Builder(context, CHANNEL_DAILY)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(title)
            .setContentText(body)
            // The body is one sentence and will not wrap on a phone, but German
            // is reliably a third longer than English and the collapsed line
            // truncates. BigText is what lets the whole citation be read
            // without opening anything.
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(openDaily(context, day))
            .setAutoCancel(true)
            .setCategory(NotificationCompat.CATEGORY_RECOMMENDATION)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .addAction(
                0,
                context.getString(R.string.daily_action_quieter),
                action(context, DailyActionReceiver.ACTION_QUIETER),
            )
            .addAction(
                0,
                context.getString(R.string.daily_action_turn_off),
                action(context, DailyActionReceiver.ACTION_TURN_OFF),
            )
            .build()

        // `notify` is documented to throw on a missing POST_NOTIFICATIONS
        // permission, and the check above is racy by construction — the person
        // can revoke it between the two lines. Swallowed rather than crashed:
        // a notification nobody was allowed to see is not an error worth taking
        // the app down for.
        runCatching { NotificationManagerCompat.from(context).notify(NOTIFICATION_ID, notification) }
    }

    /**
     * A tap opens the daily, not the home screen.
     *
     * `MainActivity` is `singleTask`, so this arrives at `onNewIntent` when the
     * app is running and at `onCreate` when it is not — the two cases the
     * activity has to handle, and it does, in one function.
     *
     * `FLAG_UPDATE_CURRENT` matters more than it looks: without it a second
     * notification would reuse the first one's extras, so Friday's tap would
     * open Thursday. `FLAG_IMMUTABLE` is required from API 31 and is right
     * regardless — nothing outside this app should be able to rewrite where
     * our own notification leads.
     */
    private fun openDaily(context: Context, day: String?): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(EXTRA_KIND, KIND_DAILY)
            putExtra(EXTRA_DATE, day)
        }
        return PendingIntent.getActivity(
            context,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    /**
     * The two action buttons go to a receiver rather than to the activity.
     *
     * Making somebody watch a launch animation to turn a notification off is
     * the opposite of one tap, and it is also the moment they are least willing
     * to look at the app. The receiver does the work with nothing on screen.
     */
    private fun action(context: Context, action: String): PendingIntent {
        val intent = Intent(context, DailyActionReceiver::class.java).setAction(action)
        return PendingIntent.getBroadcast(
            context,
            action.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    /** Take the current one down — after it has been opened, or turned off. */
    fun clear(context: Context) {
        NotificationManagerCompat.from(context).cancel(NOTIFICATION_ID)
    }
}
