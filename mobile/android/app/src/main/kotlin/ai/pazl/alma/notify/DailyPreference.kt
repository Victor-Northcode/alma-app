package ai.pazl.alma.notify

import ai.pazl.alma.R
import android.content.Context
import androidx.annotation.StringRes

/**
 * One control, three positions. Not a switch, and not five.
 *
 * `docs/THE-DAILY.md §5.1` settles both halves. Three, because every additional
 * position is a decision the person has no basis for making and a state that has
 * to be tested in six languages. Not a switch, because the distance between
 * "about once a week" and "a few times a year" is the whole difference between
 * somebody who keeps notifications on and somebody who reaches for the uninstall
 * — and a binary control makes the second person's only option the one that
 * costs us the subscription.
 *
 * [wire] is what goes over the network and into preferences, written out rather
 * than derived from `name` or `ordinal`: an enum whose storage is its case order
 * silently repoints everybody's setting the day a case is inserted.
 */
enum class DailyPreference(
    val wire: String,
    @param:StringRes val title: Int,
    @param:StringRes val detail: Int,
) {
    /**
     * No push, ever. **Today still works** — nothing is withheld, this is a
     * delivery preference and not a feature gate, and the detail line says so
     * in all six languages because that sentence is what makes Off a safe
     * choice rather than a loss.
     */
    OFF("off", R.string.daily_off, R.string.daily_off_detail),

    /**
     * The measured rule: weight ≥ 0.35 perfecting today, or a slow body
     * entering orb at ≥ 0.30. Median 45.5 a year over a 24-chart cohort.
     */
    OCCASIONALLY("occasionally", R.string.daily_occasionally, R.string.daily_occasionally_detail),

    /**
     * Weight ≥ 0.50, exact hits only. The Saturn returns and the Pluto squares
     * and nothing else — 7 to 13 a year.
     */
    ONLY_WHAT_MATTERS(
        "only_what_matters",
        R.string.daily_only_matters,
        R.string.daily_only_matters_detail,
    ),
    ;

    /** Whether this position wants a device token. Only OFF does not. */
    val wantsDelivery: Boolean get() = this != OFF

    companion object {
        fun fromWire(value: String?): DailyPreference? = entries.firstOrNull { it.wire == value }
    }
}

/**
 * Where the clock came from, so the reader can tell.
 *
 * `THE-DAILY.md §5.2` asks for the *source* to be shown beside the zone, and the
 * reason is specific rather than decorative: somebody whose notifications arrive
 * at the wrong hour is somebody who moved, and "Lisbon — from your birth data"
 * is the one line that makes them look for the override instead of deciding the
 * app is broken.
 */
enum class DailyClockSource(@param:StringRes val label: Int) {
    DEVICE(R.string.daily_timezone_device),
    BIRTH(R.string.daily_timezone_birth),
    CHOSEN(R.string.daily_timezone_chosen),
}

/**
 * What the phone remembers between launches.
 *
 * Ordinary `SharedPreferences` and deliberately not [ai.pazl.alma.data.TokenStore]'s
 * keystore-backed file: this is a preference, not a credential. It is also
 * deliberately **not** the source of truth about whether anything is delivered —
 * that is `NotificationManagerCompat.areNotificationsEnabled()`, read live,
 * because a person who revokes permission in Android's own settings must not be
 * left looking at a switch of ours that still says On.
 */
class DailyStore(context: Context) {

    private val prefs = context.applicationContext
        .getSharedPreferences("alma.daily", Context.MODE_PRIVATE)

    /**
     * What the person chose, or `null` because they have not.
     *
     * **Nullable on purpose, and the nullability is load-bearing.**
     * `THE-DAILY.md §5.1` sets the default to *Occasionally for a subscriber and
     * Off for everybody else*, which is not a value — it is a rule that depends
     * on something this class cannot see. Collapsing "never chose" and "chose
     * Off" into one stored `off` would either enrol every free reader or leave
     * every subscriber out, and neither is recoverable afterwards because the
     * two states are gone. [DailyController] applies the rule; this remembers
     * the answer.
     */
    var preference: DailyPreference?
        get() = DailyPreference.fromWire(prefs.getString(KEY_PREFERENCE, null))
        set(value) = prefs.edit().apply {
            if (value == null) remove(KEY_PREFERENCE) else putString(KEY_PREFERENCE, value.wire)
        }.apply()

    /**
     * 08:00, and editable, because "I get up at 05:30" is a real fact about a
     * person and the only one they can tell us that we cannot measure.
     */
    var hour: Int
        get() = prefs.getInt(KEY_HOUR, DEFAULT_HOUR)
        set(value) = prefs.edit().putInt(KEY_HOUR, clamp(value)).apply()

    /**
     * Whether the invitation on Today has been answered — either way.
     *
     * Our own question, unlike the platform's, may be asked again; asking it on
     * every launch is the nagging the owner named twice. Once per install until
     * they act on it, and then never as a question again.
     */
    var answeredTheAsk: Boolean
        get() = prefs.getBoolean(KEY_ASKED, false)
        set(value) = prefs.edit().putBoolean(KEY_ASKED, value).apply()

    /**
     * The last token handed to the server, and when it was accepted.
     *
     * Both, because the pair answers the only question the settings screen has
     * to answer honestly: *is anything actually going to arrive?* A token with
     * no acceptance is a token that was minted and never stored anywhere,
     * which is the state this whole build is in until the backend route exists.
     */
    var lastToken: String?
        get() = prefs.getString(KEY_TOKEN, null)
        set(value) = prefs.edit().apply {
            if (value == null) remove(KEY_TOKEN) else putString(KEY_TOKEN, value)
        }.apply()

    var registeredAtMillis: Long
        get() = prefs.getLong(KEY_REGISTERED_AT, 0L)
        set(value) = prefs.edit().putLong(KEY_REGISTERED_AT, value).apply()

    val isRegistered: Boolean get() = lastToken != null && registeredAtMillis > 0L

    /** Forget delivery, keeping the preference. */
    fun clearRegistration() {
        prefs.edit().remove(KEY_TOKEN).remove(KEY_REGISTERED_AT).apply()
    }

    companion object {
        const val DEFAULT_HOUR = 8
        const val QUIET_FROM = 22
        const val QUIET_UNTIL = 8

        private const val KEY_PREFERENCE = "preference"
        private const val KEY_HOUR = "hour"
        private const val KEY_ASKED = "asked"
        private const val KEY_TOKEN = "token"
        private const val KEY_REGISTERED_AT = "registered_at"

        /**
         * Clamped outside quiet hours rather than validated with an error.
         *
         * `THE-DAILY.md §5.2`: quiet hours are shown and not editable, because
         * making them editable invites somebody to set 03:00 and then file a
         * complaint about a 03:00 notification. The delivery hour *is*
         * editable, so it is the thing that has to be kept inside them.
         */
        fun clamp(hour: Int): Int {
            val wrapped = ((hour % 24) + 24) % 24
            return if (wrapped in QUIET_UNTIL until QUIET_FROM) wrapped else DEFAULT_HOUR
        }
    }
}
