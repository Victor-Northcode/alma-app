package ai.pazl.alma.nav

import ai.pazl.alma.R
import androidx.annotation.StringRes

/**
 * Every route in the app, named once.
 *
 * Routes are strings rather than the type-safe `@Serializable` destinations that
 * Navigation 2.8 added, for a reason that is about this product rather than
 * about the API: several of them carry a **system slug**, and those slugs come
 * from the server. `AlmaSystem.ALL` is a list of strings the backend controls,
 * a ninth system will appear in it before this app is rebuilt, and a sealed
 * class of eight objects would have to be edited to open a screen the server
 * already serves.
 *
 * The paths mirror the web app's `(cabinet)` route group exactly — `/today`,
 * `/systems`, `/systems/{slug}`, `/systems/{slug}/{chapter}`, `/alma`,
 * `/settings` — so a deep link, an analytics event and a support conversation
 * all name the same place on both platforms.
 */
object Routes {

    /* ── the journey: everything before the cabinet ────────────────────── */

    /**
     * The whole funnel, as one destination.
     *
     * Landing, quiz, name, birth time, birth place, the ceremony, the portrait
     * and the offer are **steps inside one route**, not eight routes, and that
     * is deliberate. They share one piece of in-progress state — a half-entered
     * birth — that has no meaning outside the flow, and eight destinations would
     * mean either eight copies of it or a shared `ViewModel` hoisted above the
     * graph. It also makes back behave: `back` from step four goes to step
     * three inside the flow, and `back` from step one leaves.
     *
     * The step is an argument so that a process death resumes where the person
     * was, rather than at the beginning of a form they had half filled in.
     */
    const val JOURNEY = "journey?step={step}"

    fun journey(step: Int = 1): String = "journey?step=$step"

    const val ARG_STEP = "step"

    /** Sign-in. Reachable from settings and from a magic link; never blocks anything. */
    const val SIGN_IN = "sign-in"

    /* ── the cabinet: the four tabs ────────────────────────────────────── */

    const val TODAY = "today"
    const val SYSTEMS = "systems"
    const val ALMA = "alma"
    const val SETTINGS = "settings"

    /* ── inside a system ───────────────────────────────────────────────── */

    const val SYSTEM_DETAIL = "systems/{slug}"
    const val CHAPTER = "systems/{slug}/{chapter}"

    fun system(slug: String): String = "systems/$slug"
    fun chapter(slug: String, chapter: String): String = "systems/$slug/$chapter"

    const val ARG_SLUG = "slug"
    const val ARG_CHAPTER = "chapter"

    /**
     * Compatibility's second person.
     *
     * Its own destination rather than a step of the system screen, because it
     * is the one system whose input is another human being: it needs a picker,
     * a form and a saved profile of its own before it can calculate anything.
     */
    const val PEOPLE = "people"

    /** The paywall, over whatever is underneath it. `system` is what was being read. */
    const val OFFER = "offer?system={system}"

    fun offer(system: String? = null): String = "offer?system=${system.orEmpty()}"

    const val ARG_SYSTEM = "system"

    /**
     * One of the five legal documents, read in the app rather than in a browser.
     *
     * A route rather than five, for the same reason the system screens are one:
     * the document is an argument, and the slugs are the web app's own paths, so
     * `legal/subscription-terms` names the same page on every platform. It used
     * to be an `ACTION_VIEW` at `https://alma.pazl.ai/subscription-terms`, and
     * that host does not exist.
     */
    const val LEGAL = "legal/{document}"

    fun legal(document: String): String = "legal/$document"

    const val ARG_DOCUMENT = "document"
}

/**
 * The four destinations at the bottom of the screen.
 *
 * Four and no more. The web app's sidebar shows the same four, and `people` and
 * `synthesis` are reached from inside `systems` rather than getting a tab of
 * their own — a fifth tab would push the labels to two lines in German and make
 * the least-used destination as prominent as the most-used one.
 */
enum class CabinetTab(
    val route: String,
    // `@param:` explicitly, because Kotlin 2.2 warns that a bare annotation on
    // a constructor property will start applying to the backing field too in a
    // future release. Naming the target keeps today's behaviour and, more to
    // the point, keeps the warning out of every build log.
    @param:StringRes val label: Int,
) {
    Today(Routes.TODAY, R.string.nav_today),
    Systems(Routes.SYSTEMS, R.string.nav_systems),
    Alma(Routes.ALMA, R.string.nav_alma),
    Settings(Routes.SETTINGS, R.string.nav_settings),
    ;

    companion object {
        /**
         * Which tab a route belongs to.
         *
         * Prefix matching, because `systems/natal/i` has to keep the Systems tab
         * lit. Exact matching was the first version and it unlit the tab bar the
         * moment anybody opened a chapter.
         */
        fun forRoute(route: String?): CabinetTab? {
            if (route == null) return null
            return entries.firstOrNull { route == it.route || route.startsWith("${it.route}/") }
        }
    }
}
