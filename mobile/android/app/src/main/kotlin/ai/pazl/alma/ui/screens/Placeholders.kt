package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.ui.components.AlmaWordmark
import ai.pazl.alma.ui.components.Overline
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

/**
 * ## For the three agents adding screens after this one
 *
 * Every destination in the graph has a stub here so that the skeleton builds
 * and runs end to end. **Delete a stub when you write the real screen** — do
 * not extend it. Each one is a `@Composable` with the exact signature
 * `nav/AlmaNavHost.kt` calls it with, and those signatures are the contract:
 * change one and you change the graph.
 *
 * ### Where a screen goes
 *
 * One file per screen, in `ui/screens/`, named after the destination:
 * `TodayScreen.kt`, `SystemsScreen.kt`, `AlmaScreen.kt`, `SettingsScreen.kt`,
 * `JourneyScreen.kt`, `SystemDetailScreen.kt`, `ChapterScreen.kt`,
 * `PeopleScreen.kt`, `OfferScreen.kt`, `SignInScreen.kt`. Its `ViewModel` goes
 * beside it in the same file if it is small and in `<Name>ViewModel.kt` if it
 * is not.
 *
 * ### The shape every screen has
 *
 * ```
 * @Composable
 * fun TodayScreen(container: AppContainer, …) {
 *     val vm: TodayViewModel = viewModel { TodayViewModel(container.client, container.session) }
 *     val state by vm.state.collectAsStateWithLifecycle()
 *     NightSky(config = SkyConfig(seed = 1)) {
 *         StateHost(state, onRetry = vm::reload) { data -> Today(data) }
 *     }
 * }
 * ```
 *
 * Four rules that are not negotiable, because the whole skeleton assumes them:
 *
 * 1. **No networking in a composable.** The `ViewModel` calls `AlmaClient`; the
 *    composable is a function of state. A `LaunchedEffect` that fetches is the
 *    same bug with a different shape — it re-fires on configuration change and
 *    writes a chapter twice, which costs real money.
 * 2. **`ScreenState`, not booleans.** Loading, Loaded, Failed. There is no
 *    fourth case and no `isLoading` beside the data.
 * 3. **`NightSky` wraps the content**, so the sky is behind it and the grain is
 *    above it. Use `SkyConfig.Reader` on anything with a paragraph on it.
 * 4. **Every visible string comes from `strings.xml`**, in all six languages,
 *    added in the same commit. There is no compile-time check for this.
 */

// AlmaScreen, JourneyScreen and SignInScreen have all been built — see
// AlmaScreen.kt, JourneyScreen.kt (with JourneySteps/Art/Fields/ViewModel) and
// SignInScreen.kt. Their stubs are gone rather than commented out, which is the
// point of the rule at the top of this file: two definitions of one destination
// is a compile error waiting for whoever writes the next one.

/**
 * The last stub, and the only screen in the graph that is still one.
 *
 * People is where a second birth is saved, and it is the one thing standing
 * between a visitor and the compatibility reading — so it deserves the real
 * treatment the other nine got rather than a smaller version of it. What it
 * needs is the journey's date, time and place fields (`JourneyFields.kt`) over
 * `POST /v1/profiles` with `is_self = false` and a relation, plus a list with a
 * delete on each row.
 *
 * Until then this says what it is. `SystemsScreen` sends a `add-person` row
 * here, and a screen that invented a person to fill the space would break the
 * rule the whole product is built on.
 */
// PeopleScreen's stub is gone — the screen is real and lives in
// PeopleScreen.kt, with its state in the same file. Its signature is unchanged,
// so the graph in nav/AlmaNavHost.kt calls it exactly as before. It was the
// last stub in the app.

// OfferScreen's stub is gone — the paywall is real and lives in OfferScreen.kt,
// with its state in OfferViewModel.kt. Its signature is unchanged, so the graph
// in nav/AlmaNavHost.kt calls it exactly as before.

/**
 * What a stub looks like: the mark, the destination's name, and nothing that
 * could be mistaken for content.
 *
 * Nothing invented. No sample chart, no placeholder chapter, no fake price —
 * "honest before beautiful" applies to scaffolding too, and every one of those
 * was found in the web app and removed once.
 */
@Composable
private fun Stub(
    name: String,
    seed: Int,
    config: SkyConfig = SkyConfig(seed = seed),
) {
    NightSky(config = config.copy(seed = seed)) {
        StubBody(name)
    }
}

@Composable
private fun BoxScope.StubBody(name: String) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .systemBarsPadding()
            .padding(horizontal = 22.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        AlmaWordmark()
        Overline(name, wide = true)
        // Translated, like everything else a person can read. It was English
        // for everybody, which is a small thing until it is the only sentence
        // on the screen.
        Text(
            text = stringResource(R.string.people_not_built),
            style = AlmaTheme.type.meta,
            textAlign = TextAlign.Center,
        )
    }
}
