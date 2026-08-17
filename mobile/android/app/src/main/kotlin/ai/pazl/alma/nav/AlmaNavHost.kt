package ai.pazl.alma.nav

import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.ui.screens.AlmaScreen
import ai.pazl.alma.ui.screens.ChapterScreen
import ai.pazl.alma.ui.screens.JourneyScreen
import ai.pazl.alma.ui.screens.LegalDocument
import ai.pazl.alma.ui.screens.LegalScreen
import ai.pazl.alma.ui.screens.OfferScreen
import ai.pazl.alma.ui.screens.PeopleScreen
import ai.pazl.alma.ui.screens.SettingsScreen
import ai.pazl.alma.ui.screens.SignInScreen
import ai.pazl.alma.ui.screens.SystemDetailScreen
import ai.pazl.alma.ui.screens.SystemsScreen
import ai.pazl.alma.ui.screens.TodayScreen
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.ui.input.pointer.pointerInput
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.compose.runtime.LaunchedEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.semantics.Role
import ai.pazl.alma.ui.theme.PillShape
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.foundation.clickable
import androidx.compose.ui.res.stringResource
import ai.pazl.alma.ui.theme.AlmaTheme
import ai.pazl.alma.ui.theme.AlmaSpacing
import androidx.compose.ui.unit.dp
import androidx.compose.ui.Alignment
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import androidx.navigation.navArgument
import ai.pazl.alma.ui.theme.AlmaMotion
import ai.pazl.alma.ui.theme.AlmaPalette

/**
 * The graph.
 *
 * One `NavHost` for the whole app, with the tab bar drawn only where it belongs
 * — the journey, sign-in and the paywall are full-screen, and a tab bar under
 * the ceremony would make a nine-second moment feel like a settings page.
 *
 * ## Transitions
 *
 * A cross-fade, everywhere, at 240 ms. Not a slide. The rule is "the sky moves,
 * the UI doesn't": a screen that slides in drags the starfield across with it
 * and the illusion that the sky is behind the app rather than part of it breaks
 * immediately. A fade leaves the sky where it is and changes what is in front
 * of it, which is what actually happens.
 */
@Composable
fun AlmaNavHost(
    container: AppContainer,
    modifier: Modifier = Modifier,
    navController: NavHostController = rememberNavController(),
    startDestination: String,
    /**
     * The daily somebody tapped, carrying the payload's own day.
     *
     * Collected here rather than navigated to from `MainActivity`, because on a
     * cold launch the intent is delivered before `setContent` runs and there is
     * no controller to call yet. A flow crosses that gap: whatever was put in it
     * before the graph existed is the first value the collector sees.
     */
    openDaily: StateFlow<String?> = MutableStateFlow(null),
) {
    // Today, at the top, whatever was showing. `switchTab` rather than a bare
    // navigate, so somebody who was three chapters deep in Systems when the
    // notification arrived lands on the thing they tapped and finds their
    // chapter still there when they go back — which is what one saved stack per
    // tab already gives them, and what a `navigate` with `popUpTo(0)` would
    // throw away.
    val pendingDaily by openDaily.collectAsStateWithLifecycle()
    LaunchedEffect(pendingDaily) {
        if (pendingDaily != null) navController.switchTab(CabinetTab.Today)
    }

    val backStack by navController.currentBackStackEntryAsState()
    val route = backStack?.destination?.route
    val tab = CabinetTab.forRoute(route)

    Scaffold(
        modifier = modifier.fillMaxSize(),
        // The sky is drawn by each screen, behind its own content, so the
        // scaffold must not paint over it.
        containerColor = Color.Transparent,
        // **Zero, so the sky reaches the top of the display.**
        //
        // The default gives the content a top inset the size of the status bar,
        // which pushed every screen — the starfield included — below it and left
        // a flat strip of the window's own colour across the top. Consistent
        // everywhere, and it read as deliberate, but "night is the canvas" means
        // the canvas goes all the way up: the one screen that already looked
        // right was `MainActivity`'s `NightSky { Waiting() }`, which is the only
        // place the sky was composed full-bleed.
        //
        // The bottom is unaffected: `insets` below still carries the tab bar's
        // height, because a `Scaffold` measures that from the bar rather than
        // from this, and `CabinetBar` handles the gesture inset itself.
        contentWindowInsets = WindowInsets(0),
        contentColor = AlmaPalette.Body,
        bottomBar = {
            // Only where a tab is lit. `forRoute` returns null inside the
            // journey, sign-in and the offer — the three screens that should be
            // full-bleed.
            //
            // A chapter is **not** one of them, and this comment used to claim
            // it was. `forRoute` matches on prefix and the chapter route is
            // `systems/{slug}/chapter/{chapter}`, so Systems stays lit while
            // somebody reads — which is the intended behaviour (a sixteen-page
            // read should not need a back tap to leave) and is what the device
            // actually does. The two comments disagreed and this one was wrong.
            if (tab != null) {
                CabinetBar(
                    current = tab,
                    onSelect = { selected -> navController.switchTab(selected) },
                )
            }
        },
    ) { insets ->
        val session by container.session.state.collectAsStateWithLifecycle()
        val isSubscriber = session.entitlements?.entitlements.orEmpty().any {
            it.active && (it.kind == "weekly" || it.kind == "monthly" || it.kind == "annual")
        }
        androidx.compose.foundation.layout.Box(
            Modifier
                .fillMaxSize()
                // **Swiping between tabs, and the one rule that keeps it from
                // fighting everything else.** The owner asked for it: sitting
                // in Systems, swipe right and land on Today, swipe left and
                // land on Alma.
                //
                // Only where a tab is lit and only at the root of it — `tab`
                // is null inside the journey, sign-in and the offer, and
                // `previousBackStackEntry` tells us whether there is a screen
                // behind this one. Inside a stack the same gesture is the
                // platform's back, and a screen where sliding right sometimes
                // goes back and sometimes changes tab is worse than one where
                // it only ever does one of them.
                //
                // No wrapping: Settings does not lead round to Today. Four
                // items are visible at once and there is nothing to discover
                // by looping.
                .pointerInput(tab) {
                    if (tab == null) return@pointerInput
                    detectHorizontalDragGestures(
                        onDragEnd = {},
                    ) { change, dragAmount ->
                        if (kotlin.math.abs(dragAmount) < 24f) return@detectHorizontalDragGestures
                        if (navController.previousBackStackEntry != null) {
                            return@detectHorizontalDragGestures
                        }
                        val order = CabinetTab.entries
                        val here = order.indexOf(tab)
                        val next = here + if (dragAmount < 0) 1 else -1
                        if (next !in order.indices) return@detectHorizontalDragGestures
                        change.consume()
                        navController.switchTab(order[next])
                    }
                }
        ) {
        NavHost(
            navController = navController,
            startDestination = startDestination,
            // **`consumeWindowInsets` is what stops the chat composer floating
            // a tab bar's height above the keyboard.**
            //
            // `padding(insets)` inserts the space but does not tell anything
            // below that it did, so `Modifier.imePadding()` inside `AlmaScreen`
            // measured the keyboard from the *window* bottom and added all of
            // it — on top of the 62 dp the bar had already pushed the content
            // up. The composer stayed visible, which is why it was never
            // reported, but it sat with an empty band the height of the tab bar
            // between it and the keyboard, and the last answer was pushed that
            // much further off screen. Consuming the same padding makes
            // `imePadding` compute the remainder, which is the whole contract
            // of the two modifiers together.
            //
            // Every other route that takes typing — sign-in, the journey — is
            // one `forRoute` returns null for, so there is no bar, `insets` is
            // zero at the bottom and this consumes nothing.
            modifier = Modifier.fillMaxSize().padding(insets).consumeWindowInsets(insets),
            enterTransition = { fadeIn(tween(AlmaMotion.Ui, easing = AlmaMotion.UiEasing)) },
            exitTransition = { fadeOut(tween(AlmaMotion.Ui, easing = AlmaMotion.UiEasing)) },
            popEnterTransition = { fadeIn(tween(AlmaMotion.Ui, easing = AlmaMotion.UiEasing)) },
            popExitTransition = { fadeOut(tween(AlmaMotion.Ui, easing = AlmaMotion.UiEasing)) },
        ) {

            /* ── the journey ───────────────────────────────────────────── */

            composable(
                route = Routes.JOURNEY,
                arguments = listOf(
                    navArgument(Routes.ARG_STEP) {
                        type = NavType.IntType
                        defaultValue = 1
                    }
                ),
            ) { entry ->
                JourneyScreen(
                    container = container,
                    startStep = entry.arguments?.getInt(Routes.ARG_STEP) ?: 1,
                    onFinished = {
                        // The journey is left behind entirely, and it lands in
                        // My Systems — the owner's design: data in, the loading
                        // ceremony computes everything, the tab of systems is
                        // the arrival.
                        navController.navigate(Routes.SYSTEMS) {
                            popUpTo(0) { inclusive = true }
                        }
                    },
                    onOffer = { system -> navController.navigate(Routes.offer(system)) },
                )
            }

            composable(Routes.SIGN_IN) {
                SignInScreen(container = container, onDone = { navController.popBackStack() })
            }

            /* ── the cabinet ───────────────────────────────────────────── */

            composable(Routes.TODAY) {
                TodayScreen(
                    container = container,
                    onOpenSystem = { slug -> navController.navigate(Routes.system(slug)) },
                    onAddBirthData = { navController.navigate(Routes.journey(step = 2)) },
                    onOpenChapter = { slug, chapter ->
                        navController.navigate(Routes.chapter(slug, chapter))
                    },
                    // A tab switch, not a push: the chat is a tab, and arriving
                    // there by navigation would light Today's tab under Alma's
                    // screen.
                    onAskAlma = { navController.switchTab(CabinetTab.Alma) },
                    onOffer = { system -> navController.navigate(Routes.offer(system)) },
                    onSignIn = { navController.navigate(Routes.SIGN_IN) },
                )
            }

            composable(Routes.SYSTEMS) {
                SystemsScreen(
                    container = container,
                    onOpenSystem = { slug -> navController.navigate(Routes.system(slug)) },
                    onAddPerson = { navController.navigate(Routes.PEOPLE) },
                    onAddBirthData = { navController.navigate(Routes.journey(step = 2)) },
                )
            }

            composable(Routes.ALMA) {
                AlmaScreen(
                    container = container,
                    onOffer = { navController.navigate(Routes.offer()) },
                )
            }

            composable(Routes.SETTINGS) {
                SettingsScreen(
                    container = container,
                    onSignIn = { navController.navigate(Routes.SIGN_IN) },
                    // The plans-first ladder, for both doors out of Settings: a
                    // free reader turning the daily on is buying the plan the
                    // daily belongs to — a transits door grants chapters, not
                    // the daily — and "See the plans" means the plans.
                    onOffer = { navController.navigate(Routes.offer()) },
                    onLegal = { document -> navController.navigate(Routes.legal(document.slug)) },
                )
            }

            // The five documents. A push inside the graph rather than a browser
            // intent: the text ships with the binary, so this is the one screen
            // that opens with no network and cannot fail.
            composable(
                route = Routes.LEGAL,
                arguments = listOf(navArgument(Routes.ARG_DOCUMENT) { type = NavType.StringType }),
            ) { entry ->
                LegalScreen(
                    document = LegalDocument.of(entry.arguments?.getString(Routes.ARG_DOCUMENT)),
                    onBack = { navController.popBackStack() },
                )
            }

            /* ── inside a system ───────────────────────────────────────── */

            composable(
                route = Routes.SYSTEM_DETAIL,
                arguments = listOf(navArgument(Routes.ARG_SLUG) { type = NavType.StringType }),
            ) { entry ->
                val slug = entry.arguments?.getString(Routes.ARG_SLUG).orEmpty()
                SystemDetailScreen(
                    container = container,
                    system = slug,
                    onOpenChapter = { chapter -> navController.navigate(Routes.chapter(slug, chapter)) },
                    onOffer = { navController.navigate(Routes.offer(slug)) },
                    onBack = { navController.popBackStack() },
                )
            }

            composable(
                route = Routes.CHAPTER,
                arguments = listOf(
                    navArgument(Routes.ARG_SLUG) { type = NavType.StringType },
                    navArgument(Routes.ARG_CHAPTER) { type = NavType.StringType },
                ),
                // **A chapter arrives from below and leaves upwards**, which is
                // the direction the pull was going: the motion continues the
                // gesture instead of answering it. Everywhere else in the graph
                // keeps the cross-fade, because everywhere else is reached by a
                // tap and a tap has no direction.
                //
                // iOS gets the same movement a different way — there the screen
                // owns which chapter is showing, because a `NavigationStack`
                // ignores a `.transition` on its destination. This graph does
                // animate its own routes, so the smaller change is the right
                // one here.
                enterTransition = {
                    slideInVertically(tween(AlmaMotion.Page, easing = AlmaMotion.UiEasing)) { it / 3 } +
                        fadeIn(tween(AlmaMotion.Page, easing = AlmaMotion.UiEasing))
                },
                exitTransition = {
                    slideOutVertically(tween(AlmaMotion.Page, easing = AlmaMotion.UiEasing)) { -it / 3 } +
                        fadeOut(tween(AlmaMotion.Page, easing = AlmaMotion.UiEasing))
                },
            ) { entry ->
                val slug = entry.arguments?.getString(Routes.ARG_SLUG).orEmpty()
                ChapterScreen(
                    container = container,
                    system = slug,
                    chapter = entry.arguments?.getString(Routes.ARG_CHAPTER).orEmpty(),
                    onOffer = { navController.navigate(Routes.offer(slug)) },
                    onPlans = { navController.navigate(Routes.offer()) },
                    // Replaces rather than stacks: reading nine chapters in a
                    // row should not put nine screens behind the back button,
                    // and "back" from any of them means the chapter list.
                    onOpenChapter = { next ->
                        navController.navigate(Routes.chapter(slug, next)) {
                            popUpTo(Routes.CHAPTER) { inclusive = true }
                        }
                    },
                    // Pushed, not replaced: coming back from the people screen
                    // has to land on the chapter that asked for the person, and
                    // that chapter reloads itself when it is resumed.
                    onAddPerson = { navController.navigate(Routes.PEOPLE) },
                    onBack = { navController.popBackStack() },
                )
            }

            composable(Routes.PEOPLE) {
                PeopleScreen(container = container, onBack = { navController.popBackStack() })
            }

            composable(
                route = Routes.OFFER,
                arguments = listOf(
                    navArgument(Routes.ARG_SYSTEM) {
                        type = NavType.StringType
                        defaultValue = ""
                    }
                ),
            ) { entry ->
                OfferScreen(
                    container = container,
                    system = entry.arguments?.getString(Routes.ARG_SYSTEM).orEmpty().ifBlank { null },
                    onClose = { navController.popBackStack() },
                )
            }
        }

        // The one standing invitation — a small gold seal above the bar on
        // the two content tabs, gone the moment a plan exists.
        if (!isSubscriber && session.hasBirthData &&
            (tab == CabinetTab.Today || tab == CabinetTab.Systems)
        ) {
            Surface(
                color = AlmaPalette.Gold,
                shape = PillShape,
                shadowElevation = 6.dp,
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(end = AlmaSpacing.Pad, bottom = insets.calculateBottomPadding() + 18.dp)
                    .clickable(role = Role.Button) {
                        navController.navigate(Routes.offer(""))
                    },
            ) {
                Text(
                    text = "✦ " + stringResource(ai.pazl.alma.R.string.all_alma_pill),
                    style = AlmaTheme.type.meta.copy(color = AlmaPalette.InkOnGold),
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 9.dp),
                )
            }
        }
        }
    }
}

/**
 * Switch tabs the way tabs are supposed to behave.
 *
 * `saveState`/`restoreState` keep each tab's scroll position and its own back
 * stack, and `popUpTo(startDestination)` stops the back stack growing by one
 * every time somebody taps between Today and Systems — without it, twelve taps
 * means twelve presses of the back button to leave.
 *
 * `launchSingleTop` is what makes tapping the tab you are already on a no-op
 * rather than a second copy of the screen.
 */
private fun NavHostController.switchTab(tab: CabinetTab) {
    navigate(tab.route) {
        popUpTo(graph.findStartDestination().id) { saveState = true }
        launchSingleTop = true
        restoreState = true
    }
}
