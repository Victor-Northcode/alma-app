package ai.pazl.alma.notify

import ai.pazl.alma.core.SessionHolder
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.data.dto.DailySettingsBody
import ai.pazl.alma.data.dto.DeviceRegistrationBody
import android.content.Context
import android.os.Build
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.Locale
import java.util.TimeZone

/**
 * The daily's state, and the one place that decides anything about it.
 *
 * It lives on the container rather than in a `ViewModel` because three separate
 * things reach for it and only one of them is a screen: Today draws the
 * invitation, Settings draws the control, and [DailyActionReceiver] acts on a
 * notification button in a process that may have no activity at all. A
 * `ViewModel` would be gone in the third case.
 *
 * The thing this type exists to prevent is a settings screen that says "about
 * once a week" while nothing is registered and nothing is sent — which is the
 * exact failure the web app shipped once (four toggles, no sender) and had to
 * remove, and which the note at the top of `SettingsScreen.kt` still explains.
 */
class DailyController(
    context: Context,
    private val client: AlmaClient,
    private val session: SessionHolder,
    private val tokens: PushTokens,
    private val scope: CoroutineScope,
) {

    private val app = context.applicationContext
    private val store = DailyStore(app)

    private val _state = MutableStateFlow(
        DailyState(
            chosen = store.preference,
            hour = store.hour,
            answeredTheAsk = store.answeredTheAsk,
            registered = store.isRegistered,
            permitted = DailyNotifications.enabled(app),
        )
    )
    val state: StateFlow<DailyState> = _state.asStateFlow()

    init {
        // Both channels at process start, so that a person can silence the
        // daily from Android's own settings before we have ever sent one. A
        // route out that costs nothing to provide.
        DailyNotifications.createChannels(app)
    }

    /**
     * Read the world and repair anything that drifted.
     *
     * Called on every foreground. Three things it fixes, all invisible until
     * somebody complains: a permission revoked in Android's settings while the
     * app was closed, a token FCM rotated, and a subscription that lapsed since
     * the last launch.
     */
    fun refresh() {
        scope.launch {
            val account = session.state.value
            val subscriber = account.entitlements?.isSubscriber() == true
            val permitted = DailyNotifications.enabled(app)

            _state.value = _state.value.copy(
                chosen = store.preference,
                hour = store.hour,
                answeredTheAsk = store.answeredTheAsk,
                registered = store.isRegistered,
                permitted = permitted,
                channelSilenced = DailyNotifications.channelSilenced(app),
                isSubscriber = subscriber,
            )

            val wanted = _state.value.preference.wantsDelivery && subscriber && permitted
            if (!wanted) {
                // A lapse stops the sends and **keeps the person's choice**.
                // Deleting the stored position on cancellation would mean asking
                // again on resubscription, which spends the one-shot permission
                // twice; `PUSH.md §4` makes the same call about the token row.
                if (store.isRegistered) stopDelivery()
                return@launch
            }
            registerIfPossible()
        }
    }

    /* ── the moment somebody says yes ──────────────────────────────────── */

    /**
     * The person accepted the invitation on Today.
     *
     * On Android this is the **pre-prompt and nothing else** — it records the
     * choice and returns. `POST_NOTIFICATIONS` is requested by the caller,
     * immediately afterwards, from an activity, because only an activity can
     * launch a permission request.
     *
     * The ordering is the whole design. Android has no provisional mode, so the
     * one-shot problem is undiluted: after a denial the system does not prompt
     * again until the app is reinstalled or its target SDK is raised. Our own
     * question is repeatable and the platform's is not, so ours goes first,
     * every time. `docs/PUSH.md §5.5`.
     */
    fun accept() {
        store.answeredTheAsk = true
        store.preference = DailyPreference.OCCASIONALLY
        _state.value = _state.value.copy(
            answeredTheAsk = true,
            chosen = DailyPreference.OCCASIONALLY,
        )
    }

    /** Declined. Nothing is asked of the OS, so nothing is spent. */
    fun decline() {
        store.answeredTheAsk = true
        store.preference = DailyPreference.OFF
        _state.value = _state.value.copy(answeredTheAsk = true, chosen = DailyPreference.OFF)
    }

    /**
     * Move to a position, and make the world agree with it.
     *
     * The local store first, so the interface is never showing something it has
     * not remembered; then the server. A network failure leaves a person whose
     * switch says what they set and whose phone sends nothing — the safe
     * direction, because the unsafe one is a person who turned it off and keeps
     * receiving.
     */
    fun choose(position: DailyPreference) {
        store.preference = position
        _state.value = _state.value.copy(chosen = position)
        scope.launch {
            if (position.wantsDelivery) registerIfPossible() else stopDelivery()
        }
    }

    fun setHour(hour: Int) {
        val clamped = DailyStore.clamp(hour)
        store.hour = clamped
        _state.value = _state.value.copy(hour = clamped)
        scope.launch { syncPreference() }
    }

    /**
     * The result of the `POST_NOTIFICATIONS` dialog, handed back by the screen.
     *
     * A denial is **final and is not nagged**. It is reflected in the state so
     * the switch stops claiming to be on, said once in the interface, and never
     * asked about again — `PUSH.md §5.5(3)`. Reflecting it matters as much as
     * not nagging: a control that says On and delivers nothing is the specific
     * lie this whole file is arranged to avoid.
     */
    fun onPermissionResult(granted: Boolean) {
        _state.value = _state.value.copy(permitted = granted)
        if (granted) {
            scope.launch { registerIfPossible() }
        }
    }

    /* ── the two buttons on the notification ───────────────────────────── */

    /**
     * Run a notification action to completion, then call [done].
     *
     * [done] is the receiver's `goAsync` finisher: the process can be killed the
     * moment `onReceive` returns, so the delete has to hold the broadcast open
     * or somebody who tapped *Turn these off* stays subscribed to it.
     */
    fun applyNotificationAction(action: String?, done: () -> Unit) {
        scope.launch {
            try {
                when (action) {
                    DailyActionReceiver.ACTION_TURN_OFF -> {
                        store.preference = DailyPreference.OFF
                        _state.value = _state.value.copy(chosen = DailyPreference.OFF)
                        stopDelivery()
                    }
                    DailyActionReceiver.ACTION_QUIETER -> {
                        val next = if (_state.value.preference == DailyPreference.OCCASIONALLY) {
                            DailyPreference.ONLY_WHAT_MATTERS
                        } else {
                            DailyPreference.OFF
                        }
                        store.preference = next
                        _state.value = _state.value.copy(chosen = next)
                        if (next.wantsDelivery) syncPreference() else stopDelivery()
                    }
                }
            } finally {
                done()
            }
        }
    }

    /* ── the token ─────────────────────────────────────────────────────── */

    /**
     * Hand the token over, if there is one and it is wanted.
     *
     * Not conditional on the token having *changed*: FCM rotates tokens without
     * telling anybody, the only reliable way to learn the new one is to ask, and
     * re-registering an unchanged token is one small request that also refreshes
     * `last_seen_at` — the column the server's stale-token sweep reads.
     *
     * Today [tokens] is [NoPushTransport] and this returns at the first line.
     * That is not a failure path being swallowed; it is the accurate state of a
     * phone with no push transport compiled into the app, and the settings
     * screen says exactly that.
     */
    private suspend fun registerIfPossible() {
        val state = _state.value
        if (!state.preference.wantsDelivery || !state.isSubscriber || !state.permitted) return
        val token = tokens.current() ?: return

        val body = DeviceRegistrationBody(
            platform = "android",
            token = token,
            environment = tokens.environment,
            timezone = TimeZone.getDefault().id,
            appVersion = runCatching {
                app.packageManager.getPackageInfo(app.packageName, 0).versionName
            }.getOrNull().orEmpty(),
            osVersion = Build.VERSION.RELEASE.orEmpty(),
            locale = Locale.getDefault().toLanguageTag(),
        )

        when (client.registerDevice(body)) {
            is ApiResult.Ok -> {
                store.lastToken = token
                store.registeredAtMillis = System.currentTimeMillis()
                _state.value = _state.value.copy(registered = true)
                // The position and the hour are the *user's*, not the install's,
                // and they go up their own route. After the token, so that a
                // 402 for a free reader cannot cost us the registration.
                syncPreference()
            }
            is ApiResult.Err -> {
                // Still not shown as an error, and the reason has changed. The
                // route exists now; what remains unknowable from here is
                // whether a vendor credential is configured on the server, so a
                // registration that is accepted still does not prove anything
                // will arrive. The settings screen describes the state rather
                // than apologising for it.
                store.clearRegistration()
                _state.value = _state.value.copy(registered = false)
            }
        }
    }

    /**
     * Tell the server to forget this device, and forget it here.
     *
     * `PUSH.md §6.2(6)`: **off deletes the row**. Not a flag consulted before
     * sending — the row. It is the simplest possible proof that off means off,
     * and a flag is a thing a future job can forget to read.
     */
    private suspend fun stopDelivery() {
        val token = store.lastToken
        store.clearRegistration()
        _state.value = _state.value.copy(registered = false)

        // **Both halves, and the second one is why this is not one call.**
        // Deleting this device stops this device. `PATCH {"daily":"off"}` is
        // what stops the *account* — it is the only writer of
        // `User.daily_push`, and it also forgets every other device on the
        // server side, which is the case a person with a phone and a tablet
        // would otherwise discover the hard way.
        syncPreference()

        if (token != null) {
            // A failed opt-out is the one network failure here worth noticing:
            // it is the withdrawal of consent Play and Guideline 4.5.4 both
            // require, and failing silently is how somebody keeps hearing from
            // us after saying stop. The account-level call above has already
            // run, so nobody is actually still reachable — but a delete that
            // did not happen is a row kept without a reason.
            val gone = client.forgetDevice(token)
            if (gone is ApiResult.Err) {
                Log.e("alma.daily", "device delete failed, the row may survive: $gone")
            }
        }
    }

    /**
     * `PATCH /v1/notifications`. It used to post to `/v1/account/daily`, which
     * does not exist, so no client had ever written `User.daily_push`.
     */
    private suspend fun syncPreference() {
        val state = _state.value
        client.setDailyPreference(
            DailySettingsBody(
                daily = state.preference.wire,
                hour = state.hour,
            )
        )
    }
}

/**
 * What the two screens draw from.
 *
 * [chosen] and [preference] are deliberately both here: the first is what the
 * person actually said and the second is what that means given everything else,
 * and conflating them is how a lapsed subscriber's choice gets thrown away.
 */
data class DailyState(
    /** The stored answer, or null because they have not answered. */
    val chosen: DailyPreference? = null,
    val hour: Int = DailyStore.DEFAULT_HOUR,
    val answeredTheAsk: Boolean = false,
    /** Whether the server has accepted a token for this device. */
    val registered: Boolean = false,
    /** Whether Android will show a notification at all. */
    val permitted: Boolean = false,
    /** Whether the daily's own channel has been silenced from system settings. */
    val channelSilenced: Boolean = false,
    val isSubscriber: Boolean = false,
) {
    /**
     * `THE-DAILY.md §5.1`'s rule: **Occasionally for a subscriber, Off for
     * everybody else**, unless the person has said otherwise.
     */
    val preference: DailyPreference
        get() = chosen ?: if (isSubscriber) DailyPreference.OCCASIONALLY else DailyPreference.OFF

    /**
     * Whether anything can actually arrive — a different question from what the
     * person chose, and one that must never be conflated with it.
     */
    val deliverable: Boolean
        get() = isSubscriber && preference.wantsDelivery && registered && permitted && !channelSilenced

    /**
     * Whether the invitation belongs on Today right now.
     *
     * Four conditions, and each one is somebody's bad experience: a chart must
     * exist (there is nothing to promise otherwise), the person must be a
     * subscriber (offering it to a free reader is a paywall wearing a permission
     * dialog), they must not have answered already (asked once, not every
     * launch), and the OS must not already have said no (a denied person shown
     * an invitation is being nagged about something they cannot act on here).
     */
    fun shouldInvite(hasBirthData: Boolean, previouslyDenied: Boolean): Boolean =
        hasBirthData && isSubscriber && !answeredTheAsk && !previouslyDenied
}

/**
 * Whether this account is renting the living layer.
 *
 * Asked of `kind` rather than of `system`, for the reason the iOS `AccountModel`
 * already documents: both recurring products are stored against `system: "*"`,
 * so matching on that told a monthly subscriber they held the annual plan.
 * `active` is computed server-side because a client comparing dates gets
 * subscriptions wrong.
 */
fun ai.pazl.alma.data.dto.EntitlementsDto.isSubscriber(): Boolean =
    entitlements.any { it.active && it.kind != "one_time" }
