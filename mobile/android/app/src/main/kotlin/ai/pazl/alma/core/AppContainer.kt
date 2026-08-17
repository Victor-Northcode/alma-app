package ai.pazl.alma.core

import ai.pazl.alma.billing.PlayBilling
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.Measurement
import ai.pazl.alma.data.TokenStore
import ai.pazl.alma.notify.DailyController
import ai.pazl.alma.notify.NoPushTransport
import ai.pazl.alma.ui.components.PlateStore
import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.Dispatchers

/**
 * Everything that lives for the whole process, constructed once.
 *
 * This is the dependency graph, and it is thirty lines of Kotlin rather than a
 * DI framework because it is thirty lines of Kotlin. Hilt earns its weight when
 * a graph has scopes, qualifiers and a hundred bindings; this one has four
 * objects and one scope, and adding an annotation processor to wire them would
 * add a build step, a set of generated classes to read stack traces through,
 * and a rule about where new objects go — for no assembly we are not already
 * doing here in plain sight.
 *
 * When that stops being true — and the honest marker is "a screen needs
 * something the container cannot hand it without a cast" — the right move is
 * Hilt, not a bigger container. Not before.
 *
 * A screen gets its dependencies through its `ViewModel`'s constructor, and the
 * `ViewModel` gets them from a factory that closes over the container. There is
 * an example in `ui/screens/CabinetViewModels.kt`.
 */
class AppContainer(context: Context) {

    /**
     * Outlives every screen and belongs to none of them.
     *
     * `SupervisorJob` so that one failed refresh does not cancel the session
     * holder along with it, and the default dispatcher rather than `Main`
     * because nothing started here touches the view.
     */
    private val appScope: CoroutineScope =
        CoroutineScope(SupervisorJob() + Dispatchers.Default)

    val tokens: TokenStore = TokenStore(context)

    /** Whether the funnel beacon is sent. Settings owns the switch; the client obeys it. */
    val measurement: Measurement = Measurement(context)

    val client: AlmaClient = AlmaClient.create(tokens, measurement = measurement)

    val session: SessionHolder = SessionHolder(client, appScope)

    /**
     * The chapter plates, cached on disk for the life of the install.
     *
     * On the container rather than in a `ViewModel` because the cache is the
     * point: a store per chapter screen is a store with an empty cache every
     * time a chapter opens, which is the download this class exists to avoid.
     */
    val plates: PlateStore = PlateStore(context)

    val billing: PlayBilling = PlayBilling(context, client, session, appScope)

    /**
     * The daily's state — the preference, whether anything can be delivered, and
     * what the two buttons on a notification do.
     *
     * On the container rather than in a `ViewModel` because three things reach
     * for it and only one of them is a screen: Today draws the invitation,
     * Settings draws the control, and `DailyActionReceiver` acts on a
     * notification button in a process that may have no activity at all. A
     * `ViewModel` would be gone in the third case, which is the one where
     * somebody is trying to turn us off.
     *
     * [NoPushTransport] is the honest state of this build: `PushTokens` explains
     * at length why Firebase is not wired yet and who has to decide before it
     * can be. Everything downstream of a token works; the token is null, and the
     * settings screen says so in six languages rather than pretending.
     */
    val daily: DailyController = DailyController(
        context = context,
        client = client,
        session = session,
        tokens = NoPushTransport(),
        scope = appScope,
    )

    /**
     * Called from `Application.onTerminate` for symmetry, and it will almost
     * never run — Android does not reliably deliver that callback. Which is
     * fine: the process dying takes the scope with it. This exists so that a
     * test can tear the container down.
     */
    fun close() {
        appScope.cancel()
    }
}
