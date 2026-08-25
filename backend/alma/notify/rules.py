"""The rules that keep the daily welcome, written as code rather than as intent.

The owner said "not annoying" twice, which makes it a requirement with a
number behind it rather than a sentiment. `docs/THE-DAILY.md` found the
numbers by simulation over 24 real charts for a year; this module is those
numbers, and nothing here is a fresh opinion. Where a figure appears below it
is quoted from that file with the section it came from, because a constant
somebody re-tuned by feel is how a measured design becomes a guess.

**The finding that shapes everything.** Filtering transits honestly by the
weight the engine already computes produces a median of 0.88 notifications a
week and a worst chart at 1.13 — inside the safe band before any cap is
applied. So the cap is a guard against a chart nobody has seen, not the
mechanism the design leans on. *A cap that does the work is a cap lying about
the content*, and if these caps ever start binding, the weight floor is what
should move, not the cap.

**Silence is a supported state.** There is no floor. §1 of that file measured
20-to-36-day gaps between things worth saying at a defensible weight, and
manufacturing something to fill them is the horoscope failure this product
exists in opposition to. A month with nothing in it is a correct month, and it
is only tolerable because the Today page is always there — that is the trade,
and it is why nothing in this module has an "at least" in it.

**Six refusals, and each one is somebody telling us something.**

| refusal | what it is | what it reads |
|---|---|---|
| preference | they chose | Off, or a floor they raised |
| entitlement | they are not paying | the daily is what the subscription rents |
| dormancy | they stopped opening the app | two months of not looking is an answer |
| quiet hours | it is the middle of their night | 22:00–08:00, dropped not deferred |
| the gap and the caps | we have been talking a lot | ≥3 days apart, ≤2/week, ≤10/month |
| nothing qualifies | the sky is quiet | the commonest one, and the healthiest |

They are checked in that order deliberately: cheapest first, and the ones that
are about the person before the one that is about the sky. A run that logs
"refused: not a subscriber" has told an operator something; a run that logs
"refused: nothing qualified" for the same person has told them something
false.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Protocol, Sequence, runtime_checkable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

log = logging.getLogger("alma.notify.rules")

# ── the clock ──────────────────────────────────────────────────────────────

#: Nothing is sent between these hours in the person's own time. Hard, with no
#: user override: making it editable invites somebody to set 03:00 and then
#: file a complaint about a 03:00 notification. It is *shown* in the settings,
#: which is the point — it tells the person we thought about it.
QUIET_START = 22
QUIET_END = 8

#: When the daily arrives, in the person's own clock, for somebody who has not
#: chosen. Deliberately not optimised: the outside evidence puts the
#: click-through peak late in the evening, but that peak measures retail
#: impulse, and a piece about today arriving at 22:00 is a piece about a day the
#: person has already had.
#:
#: **Ten, not eight** — the owner's call, and the reason is what 08:00 collides
#: with. Eight in the morning is inside the commute, the school run and the
#: first hour at a desk: the notification arrives while the phone is already
#: being used for something urgent, and a piece about the shape of the day is
#: read in the two seconds before it is dismissed. Ten is after that wave and
#: before lunch. It is a default rather than a rule — the hour is editable in
#: settings on both platforms, because "I get up at 05:30" is a real fact about
#: a person that no default can know.
#:
#: This number is written in three places (here, `DailyStore.defaultHour` on
#: iOS, `DailyStore.DEFAULT_HOUR` on Android) and they must agree: the phone
#: schedules the local notification and the server picks whose morning has
#: arrived, so a disagreement means two dailies or none.
DEFAULT_HOUR = 10

#: How long after their hour somebody may still be caught, if a run was missed.
#: This is `renewals.py`'s discipline — "the window is a range and not an
#: equality" — and it is the whole argument for running hourly: a job that
#: asked for `local_hour == 8` would drop everybody in one band of longitudes
#: for a whole day the first time a deploy overlapped their morning. Three
#: hours keeps a late daily inside the morning it is about; past that it is
#: dropped rather than deferred, because a daily is about a day.
WINDOW_HOURS = 3

# ── the cadence ────────────────────────────────────────────────────────────

#: THE-DAILY.md §6.3. Two of these three never bind at the measured cadence.
MIN_GAP_DAYS = 3
PER_WEEK = 2
PER_MONTH = 10

#: THE-DAILY.md §4.3's valve: after this long in silence, one candidate is
#: admitted at a lower floor. It halves the worst measured silence from 60 days
#: to 33, moves the median by one notification a year, and fires 1.75 times per
#: chart-year — rare enough to stay a valve rather than becoming the rule. The
#: 14-day version fires 111 times and is the beginning of manufacturing
#: content.
VALVE_AFTER_DAYS = 21
VALVE_FLOOR = 0.20

#: After this long without opening the app, we stop. The person has already
#: told us something, and a notification is not an argument that will change
#: it — the modal response to over-notification is to silence the app, and the
#: second-most-modal is to delete it, so the marginal push to somebody who has
#: gone quiet has negative expected value.
#:
#: Sixty days rather than thirty, and it must stay shorter than
#: `tokens.SWEEP_AFTER`. Thirty would catch a subscriber six weeks into a busy
#: patch, who is precisely who this feature is for. Sixty is two unopened
#: renewals, which is a different fact about a person. **Go quiet first, forget
#: second** — that ordering is why the two constants are 60 and 90 rather than
#: the other way round.
DORMANT_AFTER = timedelta(days=60)


class Preference(str, enum.Enum):
    """One control, three positions.

    Three and not five. Every additional position is a decision the person has
    no basis for making, and a state that has to be tested in six languages.
    """

    off = "off"
    occasionally = "occasionally"
    only_what_matters = "only_what_matters"


@dataclass(frozen=True, slots=True)
class Bar:
    """How high the sky has to jump for one preference.

    `entering` is `None` where orb entries never qualify. That is not the same
    as a floor of 1.0, and the distinction is the difference between "a very
    heavy transit entering orb would count" and "we do not push orb entries" —
    which is what *Only what matters* actually means.
    """

    exact: float
    entering: float | None
    valve: float | None


#: THE-DAILY.md §5.1 and §6.3. `occasionally` is the measured rule: median
#: 46 notifications a year. `only_what_matters` is the 0.50 floor from §1.4 —
#: the Saturn returns and the Pluto squares and nothing else, 7–13 a year.
BARS: dict[Preference, Bar] = {
    Preference.off: Bar(exact=2.0, entering=None, valve=None),
    Preference.occasionally: Bar(exact=0.35, entering=0.30, valve=VALVE_FLOOR),
    Preference.only_what_matters: Bar(exact=0.50, entering=None, valve=None),
}

#: Which transiting bodies may fire on *entering orb* rather than on perfecting.
#: The slow ones only, and the reason is in the measurements: Neptune's median
#: contact is live for 86 days, so its perfection is not the news — its arrival
#: is. Mercury's median contact is live for thirty hours, and an entry
#: notification for one would be a notification about nothing.
SLOW_BODIES = frozenset(
    {"jupiter", "saturn", "uranus", "neptune", "pluto", "chiron"}
)


@runtime_checkable
class Candidate(Protocol):
    """What `alma.daily` hands this module: one contact, already computed.

    Structural rather than a class anybody has to import, so that the daily
    package can return its own type and neither package has to depend on the
    other's. The names are `Hit`'s names where `Hit` has them, because the
    engine is the source and renaming a field between two modules is how the
    two stop meaning the same thing.

    The contract, stated once so it can be built against:

        alma.daily.candidates(session, user, *, on: date) -> Sequence[Candidate]

    Everything the sky offers this person on this local date, unfiltered by
    weight. **The astronomy is the daily package's; the cadence is this
    module's** — and that split is the reason the caps can be tested without
    an ephemeris and the ephemeris can be tested without a calendar.
    """

    transiting: str
    natal: str
    aspect: str
    #: `BODY_WEIGHT × NATAL_WEIGHT × ASPECT_WEIGHT`, straight off
    #: `transits._weight`. No second scoring system: the one that exists
    #: already encodes exactly the slow-versus-fast distinction the
    #: measurements found.
    weight: float
    #: The aspect perfects on this local date.
    exact: bool
    #: The contact enters orb on this local date.
    entering: bool
    #: When it perfects, in UTC. Rendered into the recipient's clock for the
    #: notification's one numeric argument.
    exact_at: datetime


@dataclass(frozen=True, slots=True)
class Chosen:
    """The one contact that earned an interruption, and how it earned it."""

    candidate: Candidate
    #: "exact", "entering" or "valve" — which of the three doors it came
    #: through. The notification's wording differs, and a valve piece must read
    #: as the quiet week it is rather than as an announcement.
    door: str


@dataclass(frozen=True, slots=True)
class Decision:
    """Whether to send, and the sentence explaining why not.

    The reason is not decoration. This job runs unattended, and the only way
    anybody discovers it has been sending nothing for a month is a tally of
    these strings in a log line — "refused: dormant × 400" is a different
    incident from "refused: nothing qualified × 400".
    """

    send: bool
    reason: str
    chosen: Chosen | None = None


# ── the clock, resolved ────────────────────────────────────────────────────


@lru_cache(maxsize=512)
def _zone(name: str) -> ZoneInfo | None:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def zone_for(
    *, device: str | None = None, chosen: str | None = None, birth: str | None = None
) -> ZoneInfo | None:
    """The clock this person's morning happens in, or `None` if we do not know.

    1. **A zone they chose in settings**, which only exists if they overrode it.
    2. **The device's own zone**, last reported at registration. Correct by
       construction for anybody who did not override it, and updates when they
       travel.
    3. **The birth zone.** Right for the majority who never moved, and wrong in
       a specific and predictable way for everybody who did: `Profile.timezone`
       is derived from the *birthplace*, so somebody born in Lisbon and living
       in Toronto would be woken at three in the morning.

    A ladder, not a merge. Never average two zones, and never guess one from a
    country: the coarse country is right for Poland and useless for the United
    States, Russia, Brazil, Canada and Australia, four of which are inside our
    six-language footprint.

    **The chosen zone outranks the device's, and it did not used to.** The
    device rung came first, and the clients send `X-Alma-Timezone` on every
    launch, so the device rung always resolved and `User.daily_timezone` — the
    only control a person has over this — could never take effect. Meanwhile
    `GET /v1/notifications` reported `timezone_source: "chosen"` whenever the
    field was set. A control displayed as active and inert is worse than an
    absent one, and this is the field somebody reaches for precisely when
    notifications are landing at the wrong hour. An explicit human choice
    outranks an inferred one.

    **There is no UTC rung, and that is the fix for a rule that failed open.**
    It used to end in `ZoneInfo("UTC")`, logging that "somebody is being sent a
    daily at the wrong hour" and then sending it. At 08:30 UTC the fallback
    reports 08:30 local, not quiet, due now — the same instant is 22:30 in
    Honolulu and 00:30 in Anchorage, both of which are quiet hours. "Never
    between 22:00 and 08:00" is the promise the settings screen prints and the
    only hard guarantee in a feature whose stated requirement is *not
    annoying*; a rule that logs an error and then does the thing it warned
    about is not a guarantee. UTC is a legitimate zone for somebody actually in
    it and is not a legitimate guess. `daily.due()` skips a recipient with no
    zone and counts it under its own refusal, so the run report shows it rather
    than hiding it.
    """
    for name in (chosen, device, birth):
        if not name:
            continue
        found = _zone(name)
        if found is not None:
            return found
        log.warning("unusable timezone %r; falling through the ladder", name)
    log.error(
        "no usable timezone from settings, device or birth data — refusing to "
        "send rather than guessing UTC, which would put somebody's daily in "
        "the middle of their night"
    )
    return None


def local_now(zone: ZoneInfo, at: datetime | None = None) -> datetime:
    moment = at or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(zone)


def is_quiet(local: datetime) -> bool:
    """Whether this instant is inside the recipient's night.

    The comparison wraps midnight, which is the only interesting thing about
    it: `22 <= hour or hour < 8`, not `22 <= hour < 8`, which is never true.
    """
    return local.hour >= QUIET_START or local.hour < QUIET_END


def delivery_hour(raw: int | None) -> int:
    """The hour somebody asked for — any of the twenty-four, honoured exactly.

    До 25.08.2026 здесь стоял зажим в 08–21: «мы никогда не шлём ночью».
    Владелец отменил его словами «я хочу, чтобы можно было выбрать любое
    время»: ночь защищается от НАС, а не от самого человека. Тот, кто сам
    поставил 23:00, жалобу на 23:00 не подаст — а вот уведомление, тихо
    переехавшее с выбранных 23 на 21, читается как «настройка не работает»
    (эту жалобу владелец и принёс). Зажим остался только у значения, которого
    никто не выбирал: DEFAULT_HOUR лежит днём.
    """
    if raw is None:
        return DEFAULT_HOUR
    return max(0, min(23, int(raw)))


def due_now(local: datetime, hour: int) -> bool:
    """Whether this person's morning has arrived, within the catch-up window.

    The quiet-hours check is separate and comes after this in `may_send`,
    because they answer different questions and a single combined condition
    would make the refusal reason a lie.
    """
    return hour <= local.hour < hour + WINDOW_HOURS


# ── who is eligible at all ─────────────────────────────────────────────────


def preference_of(stored: str | None, tier: str) -> Preference:
    """What this person's control is set to, resolving "never asked".

    Default **Occasionally for a subscriber and Off for everybody else**. A
    stored value always wins, in both directions: somebody who turned it off
    before subscribing stays off, which is the half that a column default
    would have got wrong.
    """
    if stored:
        try:
            return Preference(stored)
        except ValueError:
            log.warning("unknown notification preference %r; treating as off", stored)
            return Preference.off
    return Preference.occasionally if tier == "subscriber" else Preference.off


def entitled(tier: str) -> bool:
    """Whether this tier gets a pushed daily at all.

    **Subscribers only, and the alternatives were considered.** The owner's
    words were «для подписчиков», and the commercial argument agrees with him:
    the monthly plan rents the three systems that move, everything else is
    bought once and kept, and a notification about a transit is precisely the
    living layer arriving unprompted. It is the only thing the subscription is
    actually renting between one month and the next.

    *A free taste* — one a month as an argument for the paid tier — is a real
    product idea and is not implemented, because the version of it that works
    is a good notification and the version of it that ships is an
    advertisement, and Apple's guideline 4.5.4 forbids the second outright.

    *A one-time owner* gets nothing pushed, and that is not a punishment: they
    bought a chart, which is true forever and does not develop overnight. There
    is nothing to tell them today that was not true yesterday.

    What neither of them gets is a **broken switch**. Both can register a
    device token, because the OS permission is per-install and spending it
    twice is not possible; both see the setting; and a free user who turns it
    on meets the paywall rather than silence. Silently accepting a preference
    we will never honour is the one option that is indefensible.
    """
    return tier == "subscriber"


def is_dormant(last_seen: datetime | None, now: datetime | None = None) -> bool:
    """Whether this person has stopped opening the app.

    `User.last_seen_at` is bumped by `accounts.touch` on every authenticated
    request, so it means "the app made a call", which is as close to "opened
    it" as this system can get without a second event.

    Both sides are forced UTC-aware before they are subtracted. `last_seen`
    comes back naive from SQLite whatever the column says, and `now` is
    whatever a caller passed — and mixing the two raises `TypeError`, which in
    this job means one recipient counted under `errored` with a stack trace
    that says nothing about a timezone.
    """
    if last_seen is None:
        return False
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    return moment - last_seen > DORMANT_AFTER


# ── the cadence, over a history of send days ───────────────────────────────


def too_soon(today: date, history: Sequence[date]) -> str:
    """Why this person may not be interrupted today, or an empty string.

    `history` is the local dates a daily was actually sent on, read off the
    `UsageCounter` rows the job writes. Reading the cadence off the same rows
    that make the job idempotent is what makes these limits survive a job that
    runs twice, a job that runs on two hosts, and a deploy mid-run — none of
    which an in-process counter would survive.

    **No exception to the three-day gap, and one was considered.** "Never two
    days running unless the event genuinely earns it" is the humane version of
    this rule, and it was rejected because nothing measured supports a number
    for "genuinely". What the 24-chart simulation did show is that the gap is
    not the thing doing the work — the weight floor is — so an exception to it
    would buy a rare second notification at the cost of the one property this
    feature has to have. A transit heavy enough to earn an interruption is in
    orb for weeks; it is on the Today page tomorrow, and the person can go and
    look.

    **A send day in the future is not nonsense, and dropping it was a bug.**
    History used to be filtered to `day <= today` before anything was counted,
    which reads as obviously right and is wrong for one population: somebody
    who flies *west across the date line*. Auckland's morning of the 8th
    happens at 22:00 UTC on the 7th; land in Honolulu and their local date is
    still the 7th, so `counter_key` is a different row and the gap saw an empty
    history. The result is two dailies inside two hours — the precise failure
    the claim-before-send design exists to prevent, arrived at from the
    calendar instead of from the job. So the comparison is now absolute: a
    daily three days away in *either* direction is a daily we have just sent.
    """
    recent = sorted(history)
    if not recent:
        return ""

    if any(0 < abs((today - day).days) <= MIN_GAP_DAYS for day in recent):
        return f"a daily went out inside the last {MIN_GAP_DAYS} days"

    week = today - timedelta(days=6)
    if sum(1 for day in recent if day >= week) >= PER_WEEK:
        return f"already {PER_WEEK} this week"

    if sum(1 for day in recent if (day.year, day.month) == (today.year, today.month)) >= PER_MONTH:
        return f"already {PER_MONTH} this month"

    return ""


def valve_is_open(today: date, history: Sequence[date]) -> bool:
    """Whether the starvation valve should lower the floor for one candidate.

    Open only when nothing has fired for `VALVE_AFTER_DAYS` — and, for
    somebody brand new with no history at all, closed. A first notification
    admitted at 0.20 because the account is three weeks old would make the
    quietest possible piece the first thing they ever receive from us, which
    is the worst possible first impression of a feature whose entire claim is
    that it only speaks when there is something to say.
    """
    past = [day for day in history if day <= today]
    if not past:
        return False
    return (today - max(past)).days >= VALVE_AFTER_DAYS


def pick(
    candidates: Sequence[Candidate], *, bar: Bar, valve: bool = False
) -> Chosen | None:
    """The one contact worth an interruption today, or nothing.

    **At most one a day, ever.** Two notifications in one morning is two
    notifications, whatever the sky is doing, and the tie-break is simply the
    heavier one. The other candidate is on the Today page, which is where
    everything that did not clear this bar lives.

    The valve is applied last and only to what the ordinary floors rejected,
    so a quiet-week piece can never displace a real one.
    """
    def door_for(item: Candidate) -> str | None:
        if item.exact and item.weight >= bar.exact:
            return "exact"
        if (
            item.entering
            and bar.entering is not None
            and item.weight >= bar.entering
            and item.transiting in SLOW_BODIES
        ):
            return "entering"
        return None

    ranked = sorted(candidates, key=lambda item: -item.weight)
    for item in ranked:
        door = door_for(item)
        if door:
            return Chosen(item, door)

    if not valve or bar.valve is None:
        return None
    for item in ranked:
        # The valve lowers the floor; it does not lower the standard of what
        # counts as news. Something still has to be *new* today, or the quiet
        # week would be announced with a transit that has been sitting in orb
        # for two months — which is the manufactured piece §4.3 said to drop
        # the valve rather than write.
        if (item.exact or item.entering) and item.weight >= bar.valve:
            return Chosen(item, "valve")
    return None


def may_send(
    *,
    tier: str,
    stored_preference: str | None,
    last_seen: datetime | None,
    local: datetime,
    hour: int,
    history: Sequence[date],
    candidates: Sequence[Candidate],
    now: datetime | None = None,
) -> Decision:
    """The whole rule, in the order the refusals are cheapest to answer.

    Pure: no session, no clock of its own, no vendor. Every limit this feature
    promises can therefore be asserted in a test with six arguments and no
    database, which is the only way a rule like "never between 22:00 and
    08:00, on either side of the date line" gets checked rather than believed.
    """
    # An explicit Off outranks everything, including the entitlement check, so
    # that the job's tally distinguishes somebody who chose silence from
    # somebody who is not paying for sound. They are different populations —
    # one is a product signal and the other is a commercial one — and because
    # the default for a non-subscriber *is* Off, asking `preference_of` first
    # would file every free user under "off" and make the distinction
    # unreadable in exactly the place it is needed.
    if stored_preference == Preference.off.value:
        return Decision(False, "off")
    if not entitled(tier):
        return Decision(False, "not a subscriber")
    preference = preference_of(stored_preference, tier)
    if preference is Preference.off:
        return Decision(False, "off")
    if is_dormant(last_seen, now):
        return Decision(False, "dormant")
    if not due_now(local, hour):
        return Decision(False, "not their hour")
    # Ночного гейта здесь больше нет (владелец, 25.08.2026: любой час из 24
    # выбирается и уважается). От дрейфа в чужое время суток защищает сам
    # `due_now`: письмо уходит только в выбранный час и его короткое окно
    # догона, а не «когда-нибудь потом».

    blocked = too_soon(local.date(), history)
    if blocked:
        return Decision(False, blocked)

    chosen = pick(
        candidates,
        bar=BARS[preference],
        valve=valve_is_open(local.date(), history),
    )
    if chosen is None:
        return Decision(False, "nothing qualified")
    return Decision(True, chosen.door, chosen)
