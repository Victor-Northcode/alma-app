"""The rules that keep the daily welcome, asserted rather than intended.

`docs/THE-DAILY.md` measured every number in `alma/notify/rules.py` over 24
real charts. What a measurement cannot do is stop somebody re-tuning a
constant by feel eighteen months from now, so each limit gets a test that
fails with a sentence explaining what it was for.

Every test here runs without a database, without an ephemeris and without a
network, which is deliberate: a rule about the middle of somebody's night on
the other side of the date line has to be cheap to check, or it gets checked
by a person in production.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from alma.notify import rules


@dataclass(frozen=True)
class Contact:
    """A stand-in for whatever `alma.daily` returns. Structural, not inherited."""

    transiting: str = "saturn"
    natal: str = "sun"
    aspect: str = "square"
    weight: float = 0.9
    exact: bool = True
    entering: bool = False
    exact_at: datetime = datetime(2026, 8, 7, 14, 20, tzinfo=timezone.utc)


def at(zone: str, *, hour: int, day: int = 7, month: int = 8) -> datetime:
    return datetime(2026, month, day, hour, 0, tzinfo=ZoneInfo(zone))


# ── quiet hours ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("hour", [22, 23, 0, 3, 7])
def test_the_night_is_never_sendable(hour):
    assert rules.is_quiet(at("Europe/Warsaw", hour=hour)), (
        f"{hour}:00 is inside 22:00–08:00 and nothing may be sent into it"
    )


@pytest.mark.parametrize("hour", [8, 12, 21])
def test_the_day_is(hour):
    assert not rules.is_quiet(at("Europe/Warsaw", hour=hour))


def test_quiet_hours_hold_on_both_sides_of_the_date_line():
    """One UTC instant, two people, opposite answers — which is the point.

    A single global "is it night" would be right for one of these and wrong for
    the other, and the wrong one is a notification at three in the morning. The
    date is different too, not only the hour: Kiritimati is a day ahead of
    Midway for most of every day, so keying anything on the UTC date would send
    one of them twice inside one of their mornings.
    """
    moment = datetime(2026, 8, 7, 18, 0, tzinfo=timezone.utc)

    kiritimati = rules.local_now(ZoneInfo("Pacific/Kiritimati"), moment)  # UTC+14
    midway = rules.local_now(ZoneInfo("Pacific/Midway"), moment)          # UTC-11

    assert kiritimati.hour == 8 and kiritimati.date() == date(2026, 8, 8)
    assert midway.hour == 7 and midway.date() == date(2026, 8, 7)

    assert not rules.is_quiet(kiritimati)
    assert rules.is_quiet(midway), "07:00 is still inside quiet hours"

    # **The hour under test is Kiritimati's own, not `DEFAULT_HOUR`.** This
    # line used to read `hour=rules.DEFAULT_HOUR` and passed only because the
    # default happened to be 08:00, which is the hour this instant produces
    # there — so moving the default to 10:00 failed a test about the date line
    # for a reason that has nothing to do with the date line. What is being
    # asserted is that two clocks resolve independently from one instant; whose
    # preferred hour it is belongs to the caller.
    common = dict(
        tier="subscriber",
        stored_preference="occasionally",
        last_seen=moment,
        hour=kiritimati.hour,
        history=[],
        candidates=[Contact()],
        now=moment,
    )
    assert rules.may_send(local=kiritimati, **common).send
    sent = rules.may_send(local=midway, **common)
    assert not sent.send and sent.reason == "not their hour"


def test_a_zone_change_into_the_night_drops_rather_than_defers():
    """Somebody flew east and their 08:00 is now 23:00.

    `delivery_hour` clamps what a person may *choose*, so the only way to
    arrive here is a timezone that moved under a stored hour — and the answer
    is silence, not a queued notification. A daily that arrives at 23:00 to
    tell you about today is about a day you have already had.
    """
    local = at("Pacific/Auckland", hour=23)
    decision = rules.may_send(
        tier="subscriber",
        stored_preference="occasionally",
        last_seen=datetime.now(timezone.utc),
        local=local,
        hour=23,
        history=[],
        candidates=[Contact()],
    )
    assert not decision.send
    assert decision.reason == "quiet hours"


@pytest.mark.parametrize("asked,expected", [(3, 8), (0, 8), (23, 21), (22, 21), (6, 8), (9, 9)])
def test_the_delivery_hour_is_clamped_outside_the_night(asked, expected):
    assert rules.delivery_hour(asked) == expected


def test_the_catch_up_window_is_a_range_not_an_equality():
    """A missed run costs an hour, not a day.

    This is `renewals.py`'s discipline and it is the whole argument for running
    hourly. An equality would drop one band of longitudes for a full day the
    first time a deploy overlapped their morning.
    """
    assert rules.due_now(at("Europe/Warsaw", hour=8), 8)
    assert rules.due_now(at("Europe/Warsaw", hour=10), 8)
    assert not rules.due_now(at("Europe/Warsaw", hour=11), 8)
    assert not rules.due_now(at("Europe/Warsaw", hour=7), 8)


# ── the caps ───────────────────────────────────────────────────────────────


def test_never_two_days_running():
    today = date(2026, 8, 7)
    assert rules.too_soon(today, [today - timedelta(days=1)])
    assert rules.too_soon(today, [today - timedelta(days=3)])
    assert not rules.too_soon(today, [today - timedelta(days=4)])


def test_two_a_week_is_the_ceiling():
    today = date(2026, 8, 7)
    four_apart = [today - timedelta(days=4), today - timedelta(days=8)]
    # The one four days back clears the gap; the pair of them inside seven days
    # does not clear the weekly cap.
    assert rules.too_soon(today, [today - timedelta(days=4), today - timedelta(days=6)])
    assert not rules.too_soon(today, four_apart)


def test_ten_a_month_is_the_ceiling():
    """The branch itself, driven by a history no calendar can actually produce.

    Ten days inside August, one of them six days ago so the weekly cap does not
    answer first and the gap does not either. It is guard code, and guard code
    that has never been executed is guard code nobody knows the shape of.
    """
    today = date(2026, 8, 31)
    history = [date(2026, 8, 25)] + [date(2026, 8, day) for day in range(1, 10)]
    assert len(history) == 10
    assert rules.too_soon(today, history) == "already 10 this month"
    assert not rules.too_soon(today, history[:9])


def test_the_monthly_cap_is_a_backstop_behind_the_gap_and_cannot_bind_on_its_own():
    """Worth stating, because it looks like a live limit and is not.

    With a three-day gap the most notifications a 31-day month can hold is
    eight, so the ten is unreachable while the gap stands. That is the correct
    relationship — `THE-DAILY.md §4.2` found that the caps never bind at the
    measured cadence and that *a cap that does the work is a cap lying about
    the content* — and it is also the thing that changes silently if somebody
    relaxes the gap. This assertion is what turns that into a failing test
    rather than a surprise in somebody's notification tray.
    """
    most_in_a_month = 1 + 30 // (rules.MIN_GAP_DAYS + 1)
    assert most_in_a_month <= rules.PER_MONTH
    assert rules.PER_WEEK * 4 <= rules.PER_MONTH


def test_last_month_does_not_count_against_this_one():
    today = date(2026, 9, 1)
    history = [date(2026, 8, day) for day in range(1, 26, 3)]
    assert len(history) >= 8
    assert not rules.too_soon(today, history)


# ── who is eligible ────────────────────────────────────────────────────────


def test_the_daily_is_what_the_subscription_rents():
    assert rules.entitled("subscriber")
    assert not rules.entitled("owner")
    assert not rules.entitled("free")


def test_the_default_depends_on_the_tier_and_a_choice_always_wins():
    assert rules.preference_of(None, "subscriber") is rules.Preference.occasionally
    assert rules.preference_of(None, "free") is rules.Preference.off
    # The half a column default would have got wrong: somebody who turned it
    # off before subscribing must not be switched back on by subscribing.
    assert rules.preference_of("off", "subscriber") is rules.Preference.off
    assert rules.preference_of("only_what_matters", "free") is rules.Preference.only_what_matters


def test_an_unknown_stored_preference_is_silence_rather_than_noise():
    assert rules.preference_of("loud", "subscriber") is rules.Preference.off


def test_somebody_who_stopped_opening_the_app_is_left_alone():
    now = datetime(2026, 8, 7, tzinfo=timezone.utc)
    assert rules.is_dormant(now - timedelta(days=61), now)
    assert not rules.is_dormant(now - timedelta(days=59), now)


def test_going_quiet_happens_before_forgetting():
    """The two retention numbers have to be in this order and not the other.

    If tokens were swept before dormancy silenced somebody, the person who
    stopped opening the app would lose their registration — and therefore their
    ability to be reached at all when they came back — before we had even
    stopped talking to them.
    """
    from alma.notify import tokens

    assert rules.DORMANT_AFTER < tokens.SWEEP_AFTER


# ── what earns an interruption ─────────────────────────────────────────────


def test_weight_alone_does_not_qualify_and_neither_does_novelty():
    bar = rules.BARS[rules.Preference.occasionally]
    # Heavy, but nothing new today: it has been in orb for six weeks.
    assert rules.pick([Contact(weight=0.95, exact=False, entering=False)], bar=bar) is None
    # New today, but it is Mercury.
    assert rules.pick([Contact(transiting="mercury", weight=0.21)], bar=bar) is None


def test_only_the_slow_bodies_may_fire_on_entering_orb():
    bar = rules.BARS[rules.Preference.occasionally]
    fast = Contact(transiting="mars", weight=0.5, exact=False, entering=True)
    slow = Contact(transiting="neptune", weight=0.36, exact=False, entering=True)
    assert rules.pick([fast], bar=bar) is None
    chosen = rules.pick([slow], bar=bar)
    assert chosen is not None and chosen.door == "entering"


def test_only_what_matters_takes_the_heaviest_and_no_entries():
    bar = rules.BARS[rules.Preference.only_what_matters]
    assert rules.pick([Contact(weight=0.4)], bar=bar) is None
    assert rules.pick([Contact(weight=0.6)], bar=bar) is not None
    assert rules.pick(
        [Contact(transiting="pluto", weight=0.9, exact=False, entering=True)], bar=bar
    ) is None, "an orb entry is not what 'only what matters' means"


def test_at_most_one_a_day_and_it_is_the_heavier_one():
    bar = rules.BARS[rules.Preference.occasionally]
    chosen = rules.pick(
        [Contact(transiting="mars", weight=0.4), Contact(transiting="pluto", weight=0.9)],
        bar=bar,
    )
    assert chosen is not None
    assert chosen.candidate.transiting == "pluto"


def test_the_valve_opens_after_three_weeks_and_not_for_a_new_account():
    today = date(2026, 8, 7)
    assert not rules.valve_is_open(today, [])
    assert not rules.valve_is_open(today, [today - timedelta(days=20)])
    assert rules.valve_is_open(today, [today - timedelta(days=21)])


def test_the_valve_lowers_the_floor_but_not_the_standard_of_news():
    bar = rules.BARS[rules.Preference.occasionally]
    quiet = Contact(transiting="jupiter", weight=0.25)
    assert rules.pick([quiet], bar=bar) is None

    opened = rules.pick([quiet], bar=bar, valve=True)
    assert opened is not None and opened.door == "valve"

    stale = Contact(transiting="jupiter", weight=0.25, exact=False, entering=False)
    assert rules.pick([stale], bar=bar, valve=True) is None, (
        "the valve admits a quieter transit, not an older one"
    )


def test_a_real_candidate_is_never_displaced_by_a_valve_one():
    bar = rules.BARS[rules.Preference.occasionally]
    chosen = rules.pick(
        [Contact(transiting="jupiter", weight=0.25), Contact(transiting="saturn", weight=0.9)],
        bar=bar,
        valve=True,
    )
    assert chosen is not None and chosen.door == "exact"


# ── the ladder ─────────────────────────────────────────────────────────────


def test_the_clock_ladder_prefers_the_choice_then_the_device_then_the_birth():
    """The explicit human choice outranks the inferred one.

    It did not used to. The device rung came first and the clients send
    `X-Alma-Timezone` on every launch, so it always resolved and
    `User.daily_timezone` could never take effect — while the settings screen
    reported `timezone_source: "chosen"` and told the person it had. That field
    is what somebody reaches for when notifications are landing at the wrong
    hour, and it was inert.
    """
    assert rules.zone_for(
        device="Europe/Warsaw", chosen="Asia/Tokyo", birth="Pacific/Auckland"
    ).key == "Asia/Tokyo"
    assert rules.zone_for(device="Europe/Warsaw", birth="Pacific/Auckland").key == "Europe/Warsaw"
    assert rules.zone_for(birth="Pacific/Auckland").key == "Pacific/Auckland"


def test_an_unusable_zone_falls_through_and_an_empty_ladder_fails_closed():
    """No UTC rung. A guessed zone is a notification in somebody's night.

    The ladder used to end in UTC, log that "somebody is being sent a daily at
    the wrong hour", and send it. At 08:30 UTC that reads as 08:30 local and
    passes every check; the same instant is 22:30 in Honolulu and 00:30 in
    Anchorage. "Never between 22:00 and 08:00" is the only hard guarantee this
    feature makes.
    """
    assert rules.zone_for(device="Mars/Olympus", birth="Europe/Rome").key == "Europe/Rome"
    assert rules.zone_for() is None
    assert rules.zone_for(device="Mars/Olympus") is None


# ── the whole rule, in order ───────────────────────────────────────────────


def test_off_is_answered_before_anything_else_is_asked():
    """Somebody who chose silence is not reported as an unpaid user.

    The order of the refusals is itself a rule: the tally in the job's log is
    the only place anybody sees why nothing went out, and "off" and "not a
    subscriber" are different populations with different meanings.
    """
    decision = rules.may_send(
        tier="free",
        stored_preference="off",
        last_seen=datetime.now(timezone.utc),
        local=at("Europe/Warsaw", hour=8),
        hour=8,
        history=[],
        candidates=[Contact()],
    )
    assert decision.reason == "off"


def test_a_quiet_sky_is_the_commonest_answer_and_is_not_an_error():
    decision = rules.may_send(
        tier="subscriber",
        stored_preference="occasionally",
        last_seen=datetime.now(timezone.utc),
        local=at("Europe/Warsaw", hour=8),
        hour=8,
        history=[],
        candidates=[],
    )
    assert not decision.send
    assert decision.reason == "nothing qualified"
