package ai.pazl.alma

import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.nav.AlmaNavHost
import ai.pazl.alma.nav.Routes
import ai.pazl.alma.notify.DailyNotifications
import ai.pazl.alma.ui.components.AlmaLaunch
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toArgb
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/**
 * The only activity.
 *
 * A single activity because navigation is a Compose concern here and a second
 * one would mean a second place the back stack lives. The window is edge to
 * edge from the first frame, which is not decoration: the sky has to run under
 * the status bar and behind the gesture bar or the "night is the canvas" rule
 * is broken by two grey strips.
 */
class MainActivity : ComponentActivity() {

    private val container: AppContainer
        get() = (application as AlmaApplication).container

    /**
     * The daily somebody tapped, if they did — carrying the day the payload was
     * about rather than "now".
     *
     * A flow held by the activity, and read by the graph, rather than a
     * `navController.navigate` at the point the intent arrives. The reason is
     * the cold-launch case: an intent from a killed app is delivered inside
     * `onCreate`, **before `setContent` has run**, so there is no
     * `NavHostController` to call — and a tap that silently does nothing from a
     * killed app while working perfectly from a backgrounded one is the version
     * of this bug that survives testing.
     */
    private val openDaily = MutableStateFlow<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        // Both bars transparent and both forced to the dark treatment. The
        // `SystemBarStyle.dark` overloads take the scrim colour Android draws on
        // API levels that insist on one; `Color.TRANSPARENT` asks for none, and
        // what shows through is the starfield.
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
        )
        super.onCreate(savedInstanceState)

        // The account is minted before the first frame asks for anything. It is
        // one request, it is idempotent, and everything downstream — the funnel
        // beacon, a saved birth date, a purchase — needs the row it creates.
        container.session.start()

        // The emailed sign-in link, if that is what opened us.
        signInFrom(intent)

        // Play re-delivers every owned, unacknowledged purchase, so this is how
        // a purchase interrupted by a dead battery or a failed verification
        // still lands. Tied to STARTED rather than to `onCreate` so it also runs
        // when somebody returns from Play's own subscription screen.
        //
        // It does **not** race the session any more, and it used to: nothing
        // ordered these two, `SessionInterceptor` attaches `Authorization` only
        // when a token already exists, and the server mints a fresh guest for
        // any request that arrives without one — so a cold start where Play's
        // `queryPurchasesAsync` beat `GET /v1/auth/session` filed Google's
        // transaction against a throwaway account, permanently. The wait is
        // inside `PlayBilling.redeem` rather than here, so it covers the
        // purchase listener too and not only this call site.
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                container.billing.restore()
                container.session.refreshEntitlements()
                // On every foreground, not only at launch. It repairs three
                // things that are invisible until somebody complains: a
                // permission revoked in Android's own settings while the app was
                // closed, a token FCM rotated, and a subscription that lapsed
                // since the last time this ran. `docs/PUSH.md §5.6` — the OS is
                // the truth and our flag is not.
                container.daily.refresh()
            }
        }

        // A tapped notification, if that is what opened us. Read before
        // `setContent` so a cold launch has it in hand by the first composition
        // rather than a frame later, which would show Today and then move.
        openDailyFrom(intent)

        setContent {
            AlmaTheme {
                val session by container.session.state.collectAsStateWithLifecycle()

                // Where a person lands is a question about *them* rather than
                // about the app: somebody with birth data on file has a cabinet
                // and should be dropped into it, and somebody without one has a
                // journey to walk. Deciding it here rather than inside
                // `TodayScreen` keeps "Today with nothing in it" from ever
                // being a state that has to be designed.
                //
                // It waits for `ready`, and it has to: a `NavHost` cannot change
                // its `startDestination` afterwards without rebuilding the graph
                // under whoever is standing in it, so guessing while the profile
                // request is in flight would put every returning person into the
                // journey for a third of a second and then yank them out.
                // The arrival: a star chart drawing itself and folding into
                // the mark, held until both the animation has run its 2.8s and
                // the session is ready. It replaces a plain "loading" line —
                // the first two seconds of every session were the flattest
                // moment in the product.
                var arrived by remember { mutableStateOf(false) }
                if (!arrived) {
                    AlmaLaunch(ready = session.ready) { arrived = true }
                } else {
                    // Decided **once**, when the first load finishes, and never
                    // recomputed afterwards.
                    //
                    // The comment above was right about the danger and stopped
                    // one step short of it. `hasBirthData` does not only go true
                    // when the profile request answers — it also goes true the
                    // moment the journey *saves* a birth, which happens under
                    // the ceremony, three steps before the journey ends. Reading
                    // it live handed `NavHost` a new `startDestination`, which
                    // rebuilds the graph and drops whoever was standing in it
                    // onto the new start: in practice, the ceremony vanished
                    // mid-animation and the person landed in Today having never
                    // seen their portrait — the one screen that hands over the
                    // free value the offer depends on.
                    //
                    // Keyed on `session.ready` so it is computed on the
                    // false → true edge and is stable from then on. The journey
                    // leaves by its own `onFinished`, which navigates explicitly.
                    val start = remember(session.ready) {
                        if (session.hasBirthData) Routes.TODAY else Routes.journey()
                    }
                    AlmaNavHost(
                        container = container,
                        modifier = Modifier.fillMaxSize().background(AlmaPalette.Night800),
                        startDestination = start,
                        openDaily = openDaily,
                    )
                }
            }
        }
    }

    /**
     * `launchMode="singleTask"`, so a link tapped while the app is already
     * running arrives here rather than in a second `onCreate`.
     */
    override fun onNewIntent(intent: android.content.Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        signInFrom(intent)
        openDailyFrom(intent)
    }

    /**
     * A tap on the daily opens the daily, not the home screen.
     *
     * `launchMode="singleTask"` means this arrives at `onNewIntent` when the app
     * is running and at `onCreate` when it is not; both call here, which is the
     * whole of "handle closed, backgrounded, and already open". The third state
     * — already standing on Today — falls out for free: the graph navigates to a
     * destination it is already on, `launchSingleTop` makes that a no-op, and
     * the notification is taken down either way.
     *
     * Silent when the intent carries no daily. This activity is also the
     * launcher and the sign-in link's target, so every ordinary start comes
     * through here too.
     */
    private fun openDailyFrom(intent: android.content.Intent?) {
        if (intent?.getStringExtra(DailyNotifications.EXTRA_KIND) != DailyNotifications.KIND_DAILY) {
            return
        }
        // Down as soon as it has been acted on. A notification still sitting in
        // the shade after its content has been read is the small untidiness
        // that makes somebody clear all of them, including the next one.
        DailyNotifications.clear(this)
        openDaily.value = intent.getStringExtra(DailyNotifications.EXTRA_DATE) ?: ""
    }

    /**
     * Redeem a sign-in token if this intent carries one.
     *
     * The link is `https://alma.pazl.ai/sign-in?token=…`, built by
     * `alma/mail.py`. Consuming it attaches an identity to the account this
     * device already has rather than swapping it for another, which is why
     * nothing is cleared first and why a guest's purchases survive signing in.
     *
     * Silent when there is no token: this activity is also the launcher, and
     * every ordinary start comes through here.
     */
    private fun signInFrom(intent: android.content.Intent?) {
        val token = intent?.data?.getQueryParameter("token")?.takeIf { it.isNotBlank() } ?: return
        container.session.signInWithLink(token)
    }
}
