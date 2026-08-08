package ai.pazl.alma.ui.screens

import ai.pazl.alma.R
import ai.pazl.alma.core.AppContainer
import ai.pazl.alma.core.ScreenState
import ai.pazl.alma.core.SessionHolder
import ai.pazl.alma.data.AlmaClient
import ai.pazl.alma.data.AlmaSystem
import ai.pazl.alma.data.ApiFailure
import ai.pazl.alma.data.ApiResult
import ai.pazl.alma.data.dto.CalcRequest
import ai.pazl.alma.data.dto.CalcResultDto
import ai.pazl.alma.data.dto.ReadingDto
import ai.pazl.alma.data.dto.ReadingRequest
import ai.pazl.alma.notify.DailyContact
import androidx.compose.ui.platform.LocalContext
import ai.pazl.alma.notify.DailyRule
import ai.pazl.alma.notify.DailyState
import ai.pazl.alma.ui.components.MoonMedallion
import ai.pazl.alma.ui.components.Overline
import ai.pazl.alma.ui.components.QuietButton
import ai.pazl.alma.ui.components.StateHost
import ai.pazl.alma.ui.components.riseIn
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import ai.pazl.alma.ui.sky.NightSky
import ai.pazl.alma.ui.sky.SkyConfig
import ai.pazl.alma.ui.theme.AlmaPalette
import ai.pazl.alma.ui.theme.AlmaTheme
import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.annotation.StringRes
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.LocalTime
import kotlinx.serialization.json.JsonObject

/**
 * Today: what is actually crossing this chart right now.
 *
 * Three requests, and they are deliberately unequal.
 *
 * **The transits** are the screen itself. A locked answer still carries the
 * window and the active count — those are preview fields the server keeps — so
 * the rule above the list keeps its honest number while the contacts behind it
 * stay trimmed away. Inventing three plausible aspects to fill that gap would
 * sell the door by lying about what is behind it, so the strip is simply empty
 * and the row underneath it is where the transits open.
 *
 * **The natal chart** supplies the moon line and the positions strip. Locked, it
 * answers with preview fields only, so each row falls back to the sign it still
 * names and disappears entirely when even that is gone.
 *
 * **The free transits chapter** supplies the one paragraph in Alma's voice. It
 * has no fallback: where Alma has not written about this person's day, the
 * screen shows a state rather than prose from somewhere else.
 *
 * What is *not* here is a fourth request. The web app asks the hub whether
 * there is birth data, because its calculation endpoints answer a missing
 * profile with a bare 400 that arrives indistinguishable from a real fault.
 * This app already knows: `SessionHolder` has loaded the profile list before
 * `ready` goes true, and `hasBirthData` is that same fact without a round trip.
 */
@Composable
fun TodayScreen(
    container: AppContainer,
    onOpenSystem: (String) -> Unit,
    onAddBirthData: () -> Unit,
    onOpenChapter: (String, String) -> Unit = { _, _ -> },
    onAskAlma: () -> Unit = {},
    onOffer: (String) -> Unit = {},
    onSignIn: () -> Unit = {},
) {
    val vm: TodayViewModel = viewModel { TodayViewModel(container.client, container.session) }
    val state by vm.state.collectAsStateWithLifecycle()
    val daily by container.daily.state.collectAsStateWithLifecycle()

    // The platform's permission dialog, and the *only* place it is launched
    // from. It is reached from `DailyInvitation`'s yes and from nowhere else,
    // which is the ordering `docs/PUSH.md §5.5` insists on: Android has no
    // provisional mode, so after a denial the system does not ask again until
    // the app is reinstalled — our own question is repeatable and the
    // platform's is not, so ours goes first, every time.
    //
    // The result is handed straight back to the controller, which reflects a
    // denial in the switch rather than leaving a control that claims to be on
    // and delivers nothing.
    val permission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted -> container.daily.onPermissionResult(granted) }

    // The daily is a subscriber feature, and the subscription can start while
    // this screen is on the back stack — the paywall is a navigation from here.
    // Keyed on the flag rather than run once, so buying the plan makes the
    // invitation appear on the screen the person is standing on instead of on
    // their next cold launch.
    LaunchedEffect(daily.isSubscriber) { container.daily.refresh() }

    // Not `SkyConfig.Reader`, even though there is a paragraph here: Today is
    // the screen a person opens first and most often, and stripping the comet
    // off it would make the app's front door the quietest sky in the product.
    // One mote instead of three keeps the moving budget under the paragraph.
    NightSky(config = SkyConfig(seed = 1, motes = 1)) {
        StateHost(state, onRetry = vm::reload) { today ->
            TodayBody(
                today = today,
                daily = daily,
                onOpenSystem = onOpenSystem,
                onAddBirthData = onAddBirthData,
                onOpenChapter = onOpenChapter,
                onAskAlma = onAskAlma,
                onOffer = onOffer,
                onAcceptDaily = {
                    container.daily.accept()
                    // Below API 33 the permission does not exist and
                    // notifications are on by default, so there is nothing to
                    // ask for and the controller's own refresh picks it up.
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        permission.launch(Manifest.permission.POST_NOTIFICATIONS)
                    } else {
                        container.daily.onPermissionResult(true)
                    }
                },
                onDeclineDaily = container.daily::decline,
                isGuest = container.session.state.collectAsStateWithLifecycle().value.isGuest,
                onSignIn = onSignIn,
            )
        }
    }
}

/* ── what the screen holds ─────────────────────────────────────────────── */

@Immutable
data class TodayView(
    val hasBirthData: Boolean,
    /** The transits. Null only when there is no birth data to compute them from. */
    val sky: CalcResultDto?,
    /**
     * The natal chart, or null because its request failed.
     *
     * Null is not an error state here on purpose: the moon line and the
     * positions strip are both things this screen can do without, and a failure
     * panel over them would say "something went wrong" about the part of the
     * screen that is not the point of it. The transits failing is what takes
     * the whole screen down, because that *is* the point of it.
     */
    val chart: CalcResultDto?,
    /** Alma's paragraph about today, when she has written one. */
    val line: ReadingDto?,
    /** Why there is no paragraph, when the reason is worth saying out loud. */
    val lineFailure: ApiFailure?,
    val greeting: String?,
    /**
     * Whether a birth time was given.
     *
     * Read off the profile rather than sniffed out of the chart payload,
     * because that is where the fact actually lives — `birthTime == null` is
     * the same test five of the eight systems already make. The daily needs it
     * for one sentence: a chart without a time has no Ascendant and no
     * Midheaven to be crossed, which is a different reason for an empty day
     * than a quiet sky, and the two must not read the same.
     */
    val birthTimeKnown: Boolean = true,
)

class TodayViewModel(
    private val client: AlmaClient,
    private val session: SessionHolder,
) : ViewModel() {

    private val _state = MutableStateFlow<ScreenState<TodayView>>(ScreenState.Loading)
    val state: StateFlow<ScreenState<TodayView>> = _state.asStateFlow()

    private var running: Job? = null

    init {
        reload()
    }

    /**
     * Load the screen, once.
     *
     * The old job is cancelled first so that a person tapping retry twice does
     * not have two chapter writes in flight — `POST /v1/readings` costs real
     * money on the first call for a chapter, and two of them in parallel is two
     * of them charged.
     */
    fun reload() {
        running?.cancel()
        running = viewModelScope.launch {
            _state.value = ScreenState.Loading

            // Nothing that branches on `hasBirthData` may run before the session
            // is ready, and this screen is entirely that branch.
            val account = session.state.first { it.ready }
            if (!account.hasBirthData) {
                _state.value = ScreenState.Loaded(
                    TodayView(
                        hasBirthData = false,
                        sky = null,
                        chart = null,
                        line = null,
                        lineFailure = null,
                        greeting = account.profile?.name?.trim()?.takeIf { it.isNotEmpty() }
                            ?: account.account?.displayName,
                    )
                )
                return@launch
            }

            val locale = account.locale
            // Three independent requests, so three at once. The reading is the
            // slow one — seconds, because a language model may be writing — and
            // chaining it behind the two calculations would make the whole
            // screen wait for it.
            val (sky, chart, reading) = coroutineScope {
                val skyCall = async {
                    client.system(AlmaSystem.TRANSITS, CalcRequest(days = 30, locale = locale))
                }
                val chartCall = async { client.system(AlmaSystem.NATAL, CalcRequest(locale = locale)) }
                val readingCall = async {
                    client.reading(
                        ReadingRequest(
                            system = AlmaSystem.TRANSITS,
                            chapter = TransitsFreeChapter,
                            locale = locale,
                        )
                    )
                }
                Triple(skyCall.await(), chartCall.await(), readingCall.await())
            }

            // One automatic second try for the day's text, only for failures
            // a retry can change — the writing layer hiccuping, not a lock.
            var line = reading
            if (line is ApiResult.Err &&
                (line.failure is ApiFailure.Unavailable || line.failure is ApiFailure.Offline)
            ) {
                kotlinx.coroutines.delay(2_000)
                line = client.reading(
                    ReadingRequest(
                        system = AlmaSystem.TRANSITS,
                        chapter = TransitsFreeChapter,
                        locale = locale,
                    )
                )
            }

            _state.value = when (sky) {
                is ApiResult.Err -> ScreenState.Failed(sky.failure)
                is ApiResult.Ok -> ScreenState.Loaded(
                    TodayView(
                        hasBirthData = true,
                        sky = sky.data,
                        chart = chart.dataOrNull(),
                        line = (line as? ApiResult.Ok)?.data?.reading,
                        lineFailure = (line as? ApiResult.Err)?.failure,
                        // Profile first: the journey writes the name there, and
                        // a person who typed it is not greeted as nobody.
                        greeting = account.profile?.name?.trim()?.takeIf { it.isNotEmpty() }
                            ?: account.account?.displayName,
                        birthTimeKnown = account.birthTimeKnown,
                    )
                )
            }
        }
    }

    private fun <T> ApiResult<T>.dataOrNull(): T? = (this as? ApiResult.Ok)?.data

    companion object {
        /**
         * The one transits chapter that is free, from `alma/ai/chapters.py`.
         *
         * Hardcoded rather than read from `/chapters`, because this screen wants
         * one paragraph and not a list, and a request for the list to find out
         * which chapter to request would double the round trips to learn a fact
         * that has never changed.
         */
        const val TransitsFreeChapter: String = "active"
    }
}

/* ── the screen ────────────────────────────────────────────────────────── */

/**
 * Which greeting the reader's own clock earns.
 *
 * Four rather than three, because "good night" and "good evening" are different
 * sentences in five of the six languages and collapsing them would make the
 * translations worse than the English. The boundaries are the ordinary ones and
 * are deliberately not clever: nothing here knows about sunrise, and pretending
 * to would be inventing a fact on the screen that exists to only state real ones.
 */
@StringRes
private fun greetingFor(hour: Int): Int = when (hour) {
    in 5..11 -> R.string.cabinet_good_morning
    in 12..17 -> R.string.cabinet_good_afternoon
    in 18..21 -> R.string.cabinet_good_evening
    else -> R.string.cabinet_good_night
}

@Composable
private fun TodayBody(
    today: TodayView,
    daily: DailyState,
    onOpenSystem: (String) -> Unit,
    onAddBirthData: () -> Unit,
    onOpenChapter: (String, String) -> Unit,
    onAskAlma: () -> Unit,
    onOffer: (String) -> Unit,
    onAcceptDaily: () -> Unit,
    onDeclineDaily: () -> Unit,
    isGuest: Boolean = false,
    onSignIn: () -> Unit = {},
) {
    val transits: JsonObject? = today.sky?.data
    val chart: JsonObject? = today.chart?.data

    // `skyDetails` was the fold behind «Небо за словами» and is gone with it.
    // The facts it hid are no longer behind anything: the areas under the
    // horoscope name their own contacts and dates.

    CabinetPage {
        // **The device's calendar day, not the transit window's start.**
        //
        // This read `window.from`, which the server computes in its own frame,
        // and on a phone in Madrid at 01:52 on 7 August the screen called Today
        // said "6 AUGUST". The window is an astronomical range and the header is
        // a calendar day; they are not the same question, and a browser sitting
        // in the server's timezone is the only reason the web mostly gets away
        // with asking one and printing the other. "Honest before beautiful" is
        // the strictest rule in the brief, and a wrong date is the cheapest way
        // to lose a reader's trust in everything calculated below it.
        val day = dayAndMonth(LocalDate.now().toString())

        // Tonight's moon, from the transit payload's `sky_now` — the sky at
        // the moment the day was computed, never the natal chart. The natal
        // moon phase used to stand here, under today's date: the moon this
        // person was born under, presented as tonight's.
        val skyMoon = transits?.obj("sky_now")?.obj("moon_phase")

        Row(verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f)) {
                if (day != null) Overline(day, wide = true, modifier = Modifier.riseIn(0))

                // A guest has no name yet, and the greeting has to read without
                // one. The comma goes with the name: every one of the six
                // greetings ends in one, and "Good morning," alone reads as a
                // line that failed to finish.
                //
                // Four greetings off the local hour rather than one hardcoded
                // string. "Good morning" at two in the morning was the same
                // class of untruth as the date above it, and from the same
                // cause: a fact about the reader's day taken from somewhere
                // that is not their day.
                val name = today.greeting?.takeIf { it.isNotBlank() }
                val greeting = stringResource(greetingFor(LocalTime.now().hour))
                Text(
                    text = if (name != null) "$greeting $name" else greeting.trimEnd(',', ' '),
                    style = AlmaTheme.type.displayXl,
                    modifier = Modifier.padding(top = 8.dp).riseIn(0),
                )

                val phaseKey = skyMoon?.text("phase")
                if (phaseKey != null) {
                    val lit = skyMoon.number("illumination")
                        ?.let { " · ${(it * 100).toInt()}%" }.orEmpty()
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.padding(top = 8.dp).riseIn(0),
                    ) {
                        Text(text = "☽", style = AlmaTheme.type.headingM, color = AlmaPalette.GoldBright)
                        Text(text = phaseName(phaseKey) + lit, style = AlmaTheme.type.meta)
                    }
                }
            }

            // The seal of the day: tonight's actual moon, with a spark per
            // contact perfecting today. New data every morning — the reason to
            // open this screen is drawn in its corner.
            val litNow = skyMoon?.number("illumination")
            if (litNow != null) {
                val zone = remember { java.time.ZoneId.systemDefault() }
                val todayDate = remember { LocalDate.now(zone) }
                val sparks = DailyContact.all(transits)
                    .filter { it.exact?.atZone(zone)?.toLocalDate() == todayDate }
                    .map { it.aspect == "square" || it.aspect == "opposition" }
                MoonMedallion(
                    illumination = litNow,
                    waxing = skyMoon.bool("waxing") ?: true,
                    sparks = sparks,
                    modifier = Modifier
                        .padding(top = 24.dp, start = 12.dp)
                        .size(68.dp)
                        .riseIn(0),
                )
            }
        }

        if (!today.hasBirthData) {
            NeedBirthData {
                QuietButton(
                    text = stringResource(R.string.state_add_birth_data),
                    onClick = onAddBirthData,
                )
            }
            return@CabinetPage
        }

        Spacer(Modifier.height(26.dp))

        // **One telling of the day, under one name.**
        //
        // This screen used to say the same sky three times — a daily block
        // naming the exact contact, a written line describing it, and ACTIVE
        // NOW listing it again — under headers no ordinary reader could parse.
        // Two rounds of cutting later it was still three: «Твой день», a fold
        // called «Небо за словами», and «Точно сегодня». The owner asked what
        // the middle one was for and the honest answer was "the order we built
        // them in".
        //
        // Now one block called what people call it. A horoscope by sun sign is
        // written for a twelfth of humanity and cites nothing; this is read
        // from this person's own transits with the day each one perfects. The
        // word is theirs, the content stays ours. See the longer note on iOS's
        // `daySection`, and `engine/areas.py` for the mapping.
        RuledLabel(
            stringResource(R.string.cabinet_horoscope_today),
            modifier = Modifier.riseIn(1),
        )
        Spacer(Modifier.height(14.dp))
        if (daily.isSubscriber) {
            Box(Modifier.riseIn(1)) {
                DayVoice(
                    today = today,
                    isSubscriber = true,
                    onReadWholeDay = {
                        onOpenChapter(AlmaSystem.TRANSITS, TodayViewModel.TransitsFreeChapter)
                    },
                )
            }
            Spacer(Modifier.height(14.dp))
            HoroscopeAreas(transits)
        } else {
            // No opening paragraph, no blur, no empty card: the owner's call is
            // that the horoscope belongs to the plan whole, and a one-time
            // purchase does not open it either.
            Text(
                text = stringResource(R.string.cabinet_horoscope_locked),
                style = AlmaTheme.type.dayVoice,
                modifier = Modifier.padding(vertical = 6.dp),
            )
            QuietButton(
                text = stringResource(R.string.cabinet_horoscope_open),
                onClick = { onOffer("") },
            )
        }

        // The one contextual nudge the product allows itself: a rare sky —
        // a slow planet exact today — shown to somebody who is not paying for
        // the notification that would have told them. At most once a week,
        // silent for thirty days after a dismissal, gone for subscribers.
        if (!daily.isSubscriber) {
            Box(Modifier.riseIn(2)) {
                SkyEventCard(
                    contacts = DailyContact.all(transits),
                    onOpen = { onOffer("") },
                )
            }
        }

        // The second entrance to the setting, on the surface the content is on.
        //
        // `docs/PUSH.md §5.2` names a settings switch nobody finds as one of the
        // moments that look right and are not — the switch itself is correct,
        // what fails is a switch reachable *only* from a settings list. This is
        // the other entrance, and it sits **below** the day rather than above
        // it: a person who has just read what today actually holds is deciding
        // whether to be told about the next one, where a person who has read
        // nothing yet is being interrupted.
        if (daily.shouldInvite(hasBirthData = true, previouslyDenied = !daily.permitted && daily.answeredTheAsk)) {
            Box(Modifier.riseIn(3)) {
                DailyInvitation(onYes = onAcceptDaily, onNo = onDeclineDaily)
            }
        }

        // Once, quietly: a guest with a chart worth keeping is invited to
        // attach an identity to it — the owner's call. Second launch onward,
        // dismissible for good.
        val context = LocalContext.current
        var nudgeDismissed by remember { mutableStateOf(!SaveAccountNudge.shouldShow(context, isGuest)) }
        if (!nudgeDismissed) {
            Column(Modifier.riseIn(3).padding(top = 20.dp)) {
                Text(text = stringResource(R.string.save_account_title), style = AlmaTheme.type.headingM)
                Text(
                    text = stringResource(R.string.save_account_body),
                    style = AlmaTheme.type.meta,
                    modifier = Modifier.padding(top = 6.dp),
                )
                Row(
                    horizontalArrangement = Arrangement.spacedBy(18.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(top = 10.dp),
                ) {
                    QuietButton(text = stringResource(R.string.save_account_cta), onClick = onSignIn)
                    Text(
                        text = stringResource(R.string.save_account_later),
                        style = AlmaTheme.type.meta,
                        modifier = Modifier.clickable {
                            SaveAccountNudge.dismiss(context)
                            nudgeDismissed = true
                        },
                    )
                }
            }
        }

        Spacer(Modifier.height(24.dp))
        Text(
            text = stringResource(R.string.cabinet_not_prediction),
            style = AlmaTheme.type.meta,
            modifier = Modifier.riseIn(4),
        )

        Spacer(Modifier.height(6.dp))
        CabinetRow(modifier = Modifier.riseIn(5), onClick = onAskAlma, rule = false) {
            Text(
                text = stringResource(R.string.cabinet_ask_alma),
                style = AlmaTheme.type.headingM,
                modifier = Modifier.weight(1f),
            )
            Text(text = "→", style = AlmaTheme.type.positions)
        }

        // **The plan, said in words, to somebody who does not have one.**
        //
        // Here because this is the screen a subscriber would use every day and
        // therefore the screen where the reason for one is legible: the
        // transits above it move, and a chapter bought once does not. Hidden
        // the moment somebody subscribes, so it never sells what is owned.
        if (!daily.isSubscriber) {
            Spacer(Modifier.height(24.dp))
            Box(Modifier.riseIn(6)) {
                PlanInvitation(onOpen = { onOffer(AlmaSystem.NATAL) })
            }
        }

        // The door, and only when there is one. A person who has already
        // unlocked the transits is not offered them again.
        if (today.sky?.locked == true) {
            Spacer(Modifier.height(20.dp))
            CabinetRow(onClick = { onOpenSystem(AlmaSystem.TRANSITS) }, rule = false) {
                Column(Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.cabinet_today_in_full),
                        style = AlmaTheme.type.headingM,
                    )
                    Text(
                        // What is true next to a door, and nothing more. The web
                        // app's version of this row promised a reading "against
                        // your fourth house" to everybody; this screen knows no
                        // house and could not have named one.
                        text = stringResource(R.string.state_locked_note),
                        style = AlmaTheme.type.meta,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }
                Text(text = "→", style = AlmaTheme.type.positions)
            }
        }

        Spacer(Modifier.height(24.dp))
    }
}

/**
 * The plan, offered where somebody can see why they would want it.
 *
 * Not a ladder and not a price: the price is Play Billing's and belongs on the
 * offer screen, one tap away. This is the sentence that was missing — what the
 * plan contains and why a chapter bought once is not the same thing.
 */
@Composable
private fun PlanInvitation(onOpen: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(text = stringResource(R.string.plans_title), style = AlmaTheme.type.headingM)
        Text(text = stringResource(R.string.plans_body), style = AlmaTheme.type.meta)
        QuietButton(text = stringResource(R.string.plans_cta), onClick = onOpen)
    }
}

/**
 * Alma's telling of the day, or the reason there isn't one.
 *
 * The whole day for a subscriber, the opening for everybody else — with the
 * rest one tap away, because the chapter it comes from is the free one and
 * pretending otherwise would be a lie with a paywall drawn on it.
 *
 * A locked answer is not said out loud: the door at the foot of the screen is
 * already the offer, and an error panel on top of it would say the same thing
 * twice and worse. Everything else is said, because a Today screen with no
 * paragraph and no explanation reads as a day with nothing in it.
 */
@Composable
private fun DayVoice(
    today: TodayView,
    isSubscriber: Boolean,
    onReadWholeDay: () -> Unit,
) {
    val line = today.line
    if (line != null && isSubscriber && line.body.isNotEmpty()) {
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            line.body.forEach { paragraph ->
                Text(text = paragraph, style = AlmaTheme.type.dayVoice)
            }
        }
        return
    }
    val lead = line?.teaser?.takeIf { it.isNotBlank() } ?: line?.body?.firstOrNull()
    if (lead != null) {
        Text(text = lead, style = AlmaTheme.type.dayVoice)
        Spacer(Modifier.height(6.dp))
        CabinetRow(onClick = onReadWholeDay, rule = false) {
            Text(
                text = stringResource(R.string.cabinet_read_whole_day),
                style = AlmaTheme.type.headingM,
                modifier = Modifier.weight(1f),
            )
            Text(text = "→", style = AlmaTheme.type.positions)
        }
        return
    }
    when (val failure = today.lineFailure) {
        // Not failed and nothing readable: the answer came back with an empty
        // body, which is rare and is not worth an apology.
        null -> Unit
        is ApiFailure.Locked -> Unit
        is ApiFailure.NeedsBirthTime -> Text(
            text = stringResource(R.string.error_needs_birth_time),
            style = AlmaTheme.type.meta,
        )
        // The string table, not `failure.message`, and the emulator proved why:
        // a 503 from the writing layer came back as "ANTHROPIC_API_KEY is not
        // set — put it in the environment", which is a sentence for whoever
        // deploys this and not for whoever reads it. The server's messages are
        // also English in all six locales. The translated line says the thing
        // that actually matters — the calculations are unaffected.
        is ApiFailure.Unavailable -> Text(
            text = stringResource(R.string.error_ai_unavailable),
            style = AlmaTheme.type.meta,
        )
        // Alma read the sky and it is quiet. Not an apology, and not a retry:
        // this used to fall through to "Something went wrong. Try again in a
        // moment." on a screen whose three calculations had all succeeded,
        // because the refusal is a 422 and the classifier had no case for it.
        // Alma's own voice, because it is Alma speaking.
        is ApiFailure.NothingToSay -> Text(
            text = stringResource(R.string.state_nothing_today),
            style = AlmaTheme.type.almaVoice,
        )
        else -> Text(
            text = stringResource(R.string.error_generic),
            style = AlmaTheme.type.meta,
        )
    }
}

/**
 * The horoscope's four headings, each holding this person's own sky.
 *
 * **The form is borrowed and the content is not.** Work, love, money, the body
 * are the questions people arrive with, and every horoscope in the category
 * answers them in that order — so the order is taken and the sentences under it
 * are the reader's real transits, named, with the day each perfects. An area
 * with nothing in it says so, which is the line no sun-sign horoscope can write
 * and the clearest single proof that this one is computed.
 *
 * The mapping from a natal point to an area lives on the server
 * (`engine/areas.py`): it is a judgement about astrology rather than about
 * layout, and both apps have to agree on it.
 */
@Composable
private fun HoroscopeAreas(transits: JsonObject?) {
    val hits = transits?.array("active").orEmpty().filterIsInstance<JsonObject>()
    // The order the server reads them in, mirrored so the two cannot silently
    // disagree about which comes first.
    for (area in listOf("work", "love", "money", "body")) {
        val mine = hits
            .filter { it.text("area") == area }
            .sortedByDescending { it.number("urgency") ?: 0.0 }
        Column(Modifier.padding(bottom = 14.dp)) {
            Text(
                text = when (area) {
                    "work" -> stringResource(R.string.cabinet_area_work)
                    "love" -> stringResource(R.string.cabinet_area_love)
                    "money" -> stringResource(R.string.cabinet_area_money)
                    else -> stringResource(R.string.cabinet_area_body)
                },
                style = AlmaTheme.type.meta,
                color = AlmaPalette.GoldBright,
            )
            val first = mine.firstOrNull()
            val transiting = first?.text("transiting")
            val natal = first?.text("natal")
            Text(
                text = if (first != null && transiting != null && natal != null) {
                    val phrase = contactPhrase(
                        transiting,
                        first.text("aspect") ?: first.text("glyph").orEmpty(),
                        natal,
                        first.bool("retrograde") == true,
                    )
                    // A date only when the engine has one: a contact already
                    // past exactness carries none, and inventing "today" for it
                    // would be a small lie in the place least allowed one.
                    val day = dayAndMonth(first.text("exact"))
                    if (day != null) "$phrase, $day." else "$phrase."
                } else {
                    stringResource(R.string.cabinet_area_quiet)
                },
                style = AlmaTheme.type.meta,
                modifier = Modifier.padding(top = 3.dp),
            )
        }
    }
}

/**
 * The rare-sky card: one sentence, one door, one way to say no that is heard.
 *
 * The frequency law is the design: shown at most once in seven days, and a
 * dismissal buys thirty days of silence — an offer that appears on a schedule
 * is an ad; one that appears when the sky actually does something is
 * information with a door on it.
 */
@Composable
private fun SkyEventCard(contacts: List<DailyContact>, onOpen: () -> Unit) {
    val context = LocalContext.current
    val zone = remember { java.time.ZoneId.systemDefault() }
    val today = remember { java.time.LocalDate.now(zone) }
    var dismissed by remember { mutableStateOf(false) }

    val prefs = remember { context.getSharedPreferences("alma.skyevent", 0) }
    val now = System.currentTimeMillis()
    val silenced = now - prefs.getLong("declinedAt", 0) < 30L * 24 * 3600 * 1000 ||
        now - prefs.getLong("shownAt", 0) < 7L * 24 * 3600 * 1000

    val event = remember(contacts) {
        contacts.firstOrNull { it.exactOn(today, zone) && it.transiting in DailyRule.SLOW_BODIES }
    }
    if (dismissed || silenced || event == null) return

    LaunchedEffect(event) { prefs.edit().putLong("shownAt", now).apply() }

    Spacer(Modifier.height(24.dp))
    Column {
        Text(
            text = contactPhrase(event.transiting, event.aspect, event.natal, event.retrograde),
            style = AlmaTheme.type.headingM,
        )
        Text(
            text = stringResource(R.string.cabinet_sky_event_body),
            style = AlmaTheme.type.meta,
            modifier = Modifier.padding(top = 6.dp),
        )
        Row(
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.padding(top = 10.dp),
        ) {
            QuietButton(
                text = stringResource(R.string.plans_cta),
                onClick = onOpen,
                contentColor = AlmaPalette.GoldBright,
            )
            Text(
                text = stringResource(R.string.paywall_not_now),
                style = AlmaTheme.type.meta,
                color = AlmaPalette.Muted3,
                modifier = Modifier.clickable {
                    prefs.edit().putLong("declinedAt", System.currentTimeMillis()).apply()
                    dismissed = true
                },
            )
        }
    }
}


/**
 * The one invitation to attach an identity to the guest account. Counted per
 * cold start; put away for good with one tap — a card that keeps coming back
 * is nagging, and nagging sells nothing.
 */
internal object SaveAccountNudge {
    private const val PREFS = "save_account"
    private var counted = false

    fun shouldShow(context: android.content.Context, isGuest: Boolean): Boolean {
        val prefs = context.getSharedPreferences(PREFS, android.content.Context.MODE_PRIVATE)
        if (!counted) {
            counted = true
            prefs.edit().putInt("launches", prefs.getInt("launches", 0) + 1).apply()
        }
        return isGuest && !prefs.getBoolean("dismissed", false) && prefs.getInt("launches", 0) >= 2
    }

    fun dismiss(context: android.content.Context) {
        context.getSharedPreferences(PREFS, android.content.Context.MODE_PRIVATE)
            .edit().putBoolean("dismissed", true).apply()
    }
}
