"""The daily — the rules it lives or dies by.

Five of these are the ones the feature was commissioned with, and they are the
five that stop it degrading into a horoscope with a timestamp:

* a day with nothing produces nothing;
* a day with an event produces exactly **one** piece;
* the same day asked twice returns the same text;
* a piece citing a placement the chart does not contain is refused;
* the ceilings bite.

The rest assert the measured policy in `docs/THE-DAILY.md` — the cadence, the
Moon's permanent exclusion, quiet hours, the gap and the cap — and the six
languages. The cadence test is the one to look at first if somebody edits
`TRANSIT_ORBS`, `BODY_WEIGHT` or `NATAL_WEIGHT`: those tables are what
`selection.PUSH_FLOOR` is calibrated against, and a change to them moves this
feature's frequency without touching a line of its code.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from conftest import database_url, run_async

from dataclasses import replace

from alma.ai import chapters, cost, writer
from alma.ai.provider import ScriptedProvider
from alma.ai.writer import ReadingRefused
from alma.auth import accounts
from alma.calc.contract import BirthData
from alma.calc.service import chart_for
from alma.daily import clock, notification, selection, service, storage, words
from alma.db import session as session_module
from alma.db.models import Profile, UsageCounter
from alma.engine import zodiac

# ── the chart every test shares ────────────────────────────────────────────
#
# Chart B from `docs/THE-DAILY.md §1.1` — Kraków, 1978, a real birth time. It
# measured 485 contacts in the 2026-08-07 window there and measures 485 here,
# which is what makes the counts below comparable to the document rather than
# to a different year of sky. The window is hard-coded for the same reason.

BIRTH = BirthData(
    date=date(1978, 5, 18),
    time="03:05",
    latitude=50.06,
    longitude=19.94,
    timezone="Europe/Warsaw",
    place_label="Kraków, Poland",
    name="Ola",
)

#: No birth time — §7's "Chart E", which loses the Ascendant and the Midheaven
#: and is measurably thinner for it. The daily must still work and must say so.
TIMELESS = BirthData(
    date=date(2003, 9, 21),
    latitude=-36.85,
    longitude=174.76,
    timezone="Pacific/Auckland",
    place_label="Auckland, New Zealand",
)

WINDOW_FROM = datetime(2026, 8, 7, tzinfo=timezone.utc)
ZONE = ZoneInfo("Europe/Warsaw")
DAYS = 365


@pytest.fixture(scope="module")
def sky():
    """One year of contacts, scanned once for the whole module.

    `transits.scan` over a year is 1.35 s (§2.4). Paying that per test would
    make this file slower than the rest of the suite put together, and every
    test here wants the same year.
    """
    return service.hits_for(BIRTH, start=WINDOW_FROM, days=DAYS)


@pytest.fixture(scope="module")
def calendar(sky):
    """Which days of the year have an occasion at the push floor, and which do not."""
    days = [WINDOW_FROM.date() + timedelta(days=i) for i in range(DAYS)]
    found = {d: selection.occasion_for(sky, on=d, zone=ZONE) for d in days}
    return found


@pytest.fixture(scope="module")
def a_day_with(calendar):
    return next(d for d, o in sorted(calendar.items()) if o is not None)


@pytest.fixture(scope="module")
def a_day_without(calendar):
    return next(d for d, o in sorted(calendar.items()) if o is None)


# ── the database, driven synchronously ─────────────────────────────────────

@pytest.fixture
def db(tmp_path, monkeypatch):
    from alma import config as config_module

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "daily.db"))
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()
    run_async(session_module.create_all)

    def run(coro_factory):
        async def wrapper():
            async with session_module.session_scope() as session:
                return await coro_factory(session)

        return run_async(wrapper)

    yield run
    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


async def _person(session):
    """A guest with one profile, which is all `piece_for` needs."""
    user = await accounts.create_guest(session)
    profile = Profile(
        user_id=user.id,
        is_self=True,
        birth_date=BIRTH.date,
        birth_time=BIRTH.time,
        latitude=BIRTH.latitude,
        longitude=BIRTH.longitude,
        timezone=BIRTH.timezone,
        place_label=BIRTH.place_label,
    )
    session.add(profile)
    await session.flush()
    return user, profile


def reply(factor: str, *, teaser: str = "Mars reaches your Moon at 17:30.") -> str:
    """One well-formed generation, citing the factor it was given."""
    return json.dumps(
        {
            "title": "Today",
            "teaser": teaser,
            "paragraphs": [
                {
                    "text": (
                        "Transiting Mars comes to the exact degree of your natal "
                        "Moon this afternoon. It has been closing on it for days; "
                        "today is the day it arrives."
                    ),
                    "factors": [factor],
                }
            ],
            "advice": "",
        }
    )


async def _write(session, user, profile, *, on, hits, provider, locale="en",
                 tier="subscriber", model="claude-sonnet-5"):
    return await service.piece_for(
        session,
        user,
        birth=BIRTH,
        profile_id=profile.id,
        hits=hits,
        on=on,
        zone=ZONE,
        provider=provider,
        model=model,
        tier=tier,
        locale=locale,
    )


# ── 1 · a day with nothing produces nothing ────────────────────────────────

def test_a_day_with_nothing_produces_nothing(db, sky, a_day_without):
    """Silence is a supported state, not a bug to be filled.

    §4.1 sets the floor at *zero* notifications: there is no minimum and
    nothing is manufactured to fill a gap. What makes that survivable is the
    pull surface, which does not go through this path at all — so the assertion
    is not only that no piece comes back but that nothing was generated and
    nothing was charged. A daily that quietly spends money on days it decides
    to say nothing about would be the worst of both designs.
    """
    provider = ScriptedProvider(responses=[])   # any generation at all raises

    async def work(session):
        user, profile = await _person(session)
        piece = await _write(session, user, profile, on=a_day_without, hits=sky,
                             provider=provider)
        return piece, await cost.month_spend(session, user), await storage.written_count(session, user)

    piece, spent, rows = db(work)
    assert piece is None
    assert provider.calls == []
    assert spent == 0.0
    assert rows == 0


def test_the_empty_day_still_has_words_for_the_reader(a_day_without):
    """Nothing to say is not nothing to show.

    §5.1's whole argument for allowing silence is that opening the app always
    shows something. The six-language strings for that state exist here so a
    client cannot invent an English one.
    """
    for locale in words.WORDS:
        settings = words.words_for(locale).settings
        assert settings["daily.empty.title"].strip()
        assert settings["daily.empty.body"].strip()


# ── 2 · a day with an event produces exactly one piece ─────────────────────

def test_a_day_with_an_event_produces_exactly_one_piece(db, sky, calendar, a_day_with):
    occasion = calendar[a_day_with]
    provider = ScriptedProvider(responses=[reply(occasion.factor)])

    async def work(session):
        user, profile = await _person(session)
        piece = await _write(session, user, profile, on=a_day_with, hits=sky,
                             provider=provider)
        return piece, await storage.written_count(session, user)

    piece, rows = db(work)
    assert piece is not None
    assert piece.cached is False
    assert rows == 1
    assert len(provider.calls) == 1


def test_the_heaviest_candidate_wins_and_kind_does_not_break_the_tie(sky, calendar):
    """At most one a day, and it is the heaviest thing eligible — §6.3.

    §1.2 measured 6.4–10.7 contacts in orb on an average day and up to 15 on
    the fullest, so something has to choose. Weight chooses, and **not** the
    kind of event: twice in this chart-year a slow body entering orb at 0.42
    and 0.49 outranks a lighter contact perfecting the same day, and it should.
    A Saturn window opening is bigger news than a Mars square closing, and the
    only defensible ranking is the one `transits._weight` already encodes.

    The candidate pool is rebuilt here from the raw hits rather than asked of
    `occasion_for`, which would be the function agreeing with itself.
    """
    from alma.engine import transits

    for day, occasion in calendar.items():
        candidates = [
            h for h in sky
            if h.weight >= selection.PUSH_FLOOR
            and clock.local_date(h.exact_jd, ZONE) == day
        ] + [
            h for h in sky
            if h.transiting in transits.SLOW_BODIES
            and h.weight >= selection.SLOW_ENTRY_FLOOR
            and h.enters_jd is not None
            and clock.local_date(h.enters_jd, ZONE) == day
        ]
        if not candidates:
            assert occasion is None
            continue
        assert occasion is not None
        assert occasion.hit.weight == max(h.weight for h in candidates)


def test_the_piece_is_shorter_than_a_chapter():
    """A lock screen is not a page. Asserted so nobody quietly relaxes it."""
    from alma.ai import chapters

    daily = service.writing.chapter_for("en")
    assert daily.words[1] < min(c.words[0] for c in chapters.NATAL)
    assert daily.paragraphs == (1, 2)


# ── 3 · the same day asked twice returns the same text ─────────────────────

def test_the_same_day_asked_twice_returns_the_same_text(db, sky, calendar, a_day_with):
    """Written once, returned forever — a chapter's rule, for a chapter's reason.

    The provider is scripted with exactly one reply, so a second generation
    would raise rather than quietly cost money. Two separate session scopes,
    so what is being asserted is that the row persisted and was found again
    rather than that an object stayed in memory.
    """
    occasion = calendar[a_day_with]
    provider = ScriptedProvider(responses=[reply(occasion.factor)])

    async def first(session):
        user, profile = await _person(session)
        piece = await _write(session, user, profile, on=a_day_with, hits=sky,
                             provider=provider)
        return user.id, profile.id, piece.body

    user_id, profile_id, body = db(first)

    async def second(session):
        user = await accounts.resolve(session, user_id)
        profile = await session.get(Profile, profile_id)
        return await _write(session, user, profile, on=a_day_with, hits=sky,
                            provider=provider)

    again = db(second)
    assert again.cached is True
    assert again.body == body
    assert again.body["body"] == body["body"]
    assert len(provider.calls) == 1


def test_two_languages_are_two_pieces_and_neither_replaces_the_other(
    db, sky, calendar, a_day_with
):
    """The same rule chapters follow, for the same reason.

    A reader who switches their phone to French should get a French piece about
    the same event, not an English one they cannot read — and the English one
    they already read must still be there.
    """
    occasion = calendar[a_day_with]
    provider = ScriptedProvider(responses=[reply(occasion.factor), reply(occasion.factor)])

    async def work(session):
        user, profile = await _person(session)
        english = await _write(session, user, profile, on=a_day_with, hits=sky,
                               provider=provider, locale="en")
        french = await _write(session, user, profile, on=a_day_with, hits=sky,
                              provider=provider, locale="fr")
        return english, french, await storage.written_count(session, user)

    english, french, rows = db(work)
    assert english.locale == "en" and french.locale == "fr"
    assert english.cached is False and french.cached is False
    assert rows == 2


def test_a_regional_tag_does_not_buy_a_second_copy_of_the_same_day(
    db, sky, calendar, a_day_with
):
    """"de-AT" and "de" are one piece. `readings.py` learned this expensively."""
    occasion = calendar[a_day_with]
    provider = ScriptedProvider(responses=[reply(occasion.factor)])

    async def work(session):
        user, profile = await _person(session)
        await _write(session, user, profile, on=a_day_with, hits=sky,
                     provider=provider, locale="de")
        again = await _write(session, user, profile, on=a_day_with, hits=sky,
                             provider=provider, locale="de-AT")
        return again, await storage.written_count(session, user)

    again, rows = db(work)
    assert again.cached is True
    assert rows == 1


# ── 4 · a piece citing an absent placement is refused ──────────────────────

def test_a_piece_citing_a_placement_the_chart_does_not_have_is_refused(
    db, sky, calendar, a_day_with
):
    """The rule that makes this product defensible, applied to the daily.

    A model asked what today holds will produce fluent, specific, plausible
    astrology whether or not it was given a chart, and the invented version is
    indistinguishable from the real one to everybody except the person who
    built the engine. The daily arrives uninvited and is read by people who
    never open the piece behind it, so it needs this more than a chapter does.

    Three attempts, all inventing, then a refusal — and the money is charged
    anyway, because three generations really happened.
    """
    invented = "transiting pluto ☌ natal venus · orb 0.00°"
    assert invented not in [h.describe() for h in sky]
    provider = ScriptedProvider(responses=[reply(invented) for _ in range(3)])

    async def work(session):
        user, profile = await _person(session)
        try:
            await _write(session, user, profile, on=a_day_with, hits=sky, provider=provider)
        except ReadingRefused as exc:
            return user.id, str(exc)
        return user.id, None

    user_id, message = db(work)
    assert message is not None
    assert len(provider.calls) == 3

    async def check(session):
        user = await accounts.resolve(session, user_id)
        return await cost.month_spend(session, user), await storage.written_count(session, user)

    spent, rows = db(check)
    assert rows == 0, "a refused daily must not leave a row behind"
    assert spent > 0.0, "three paid attempts must reach the month ledger"


def test_an_uncited_paragraph_is_refused_too(db, sky, calendar, a_day_with):
    """An unsourced paragraph is unsourced whether or not it happens to be true."""
    unsourced = json.dumps(
        {
            "title": "Today",
            "teaser": "Something is happening today.",
            "paragraphs": [{"text": "Today favours bold moves.", "factors": []}],
            "advice": "",
        }
    )
    provider = ScriptedProvider(responses=[unsourced for _ in range(3)])

    async def work(session):
        user, profile = await _person(session)
        with pytest.raises(ReadingRefused):
            await _write(session, user, profile, on=a_day_with, hits=sky, provider=provider)
        return True

    assert db(work)


def test_the_brief_offers_the_contact_and_only_the_contact(sky, calendar, a_day_with):
    """One event, not the whole day (§2.1).

    The measured difference is 167 characters against 2,324, but the reason to
    assert it is editorial rather than financial: given everything in orb a
    model writes about the day, and a piece that mentions eight contacts is the
    horoscope this feature exists not to be.
    """
    from alma.daily import writing

    occasion = calendar[a_day_with]
    result = writing.brief(occasion, chart=chart_for(BIRTH), birth=BIRTH)
    transiting = [f for f in result.factors if f.startswith("transiting")]

    # Two "transiting" lines, not one: the contact, and the moving body's own
    # degree. The second was added after a live generation put Pluto on an
    # Ascendant 300° away — see `writing._geometry`. It is still one *event*,
    # which is what this test is about; the whole day would be eight.
    assert occasion.factor in transiting
    assert len(transiting) == 2
    assert len(result.factors) <= 3


def test_the_cited_orb_is_the_orb_on_the_day_and_not_the_orb_at_the_scan(
    sky, calendar, a_day_with
):
    """`Hit.orb_now` is measured against the scan's reference instant.

    For the year-ahead scan §6.2 recommends, that reference is up to a year
    from the day being written about — so quoting it would put one false number
    in a piece whose entire argument is that its numbers are true. An aspect
    that perfects has an orb of zero, by definition, and that is what is cited.
    """
    for day, occasion in calendar.items():
        if occasion is None or occasion.kind != selection.PERFECTS:
            continue
        assert "0.00" in occasion.factor
        assert occasion.orb == 0.0


# ── 5 · the ceilings bite ──────────────────────────────────────────────────

def test_the_per_call_ceiling_bites(db, sky, calendar, a_day_with, monkeypatch):
    """One generation that is somehow too big never happens.

    The daily is guarded at `paid=False`, i.e. against `free_user_budget` and
    not the half-dollar report ceiling, which §2.2 shows leaves an order of
    magnitude of headroom on a $0.0105 piece. That is the point: this is the
    one generation that can run every day for every subscriber, so a prompt
    that quietly grew should stop being affordable long before an invoice
    notices.
    """
    from alma import config as config_module

    monkeypatch.setenv("ALMA_FREE_USER_BUDGET", "0.000001")
    config_module.settings.cache_clear()

    occasion = calendar[a_day_with]
    provider = ScriptedProvider(responses=[reply(occasion.factor)])

    async def work(session):
        user, profile = await _person(session)
        with pytest.raises(cost.BudgetExceeded):
            await _write(session, user, profile, on=a_day_with, hits=sky, provider=provider)
        return await storage.written_count(session, user)

    assert db(work) == 0
    assert provider.calls == [], "refused before the model was ever called"


def test_the_month_ceiling_bites(db, sky, calendar, a_day_with, monkeypatch):
    """Thirty cheap dailies must meet the ceiling, not the invoice.

    This is the failure `guard` cannot see: every call it approved was
    genuinely, individually cheap. Without the cumulative check one account can
    spend without limit as long as it does so in small enough pieces, and a
    daily is the smallest piece this product has.
    """
    from alma import config as config_module

    monkeypatch.setenv("ALMA_FREE_MONTH_BUDGET", "0.10")
    monkeypatch.setenv("ALMA_OWNER_MONTH_BUDGET", "0.20")
    monkeypatch.setenv("ALMA_SUBSCRIBER_MONTH_BUDGET", "0.30")
    config_module.settings.cache_clear()

    occasion = calendar[a_day_with]
    provider = ScriptedProvider(responses=[reply(occasion.factor)])

    async def work(session):
        user, profile = await _person(session)
        today = datetime.now(timezone.utc).date()
        session.add(
            UsageCounter(
                id=f"{user.id}:{today.isoformat()}:{cost.SPEND_METRIC}",
                user_id=user.id, day=today, metric=cost.SPEND_METRIC,
                count=1, amount=29.9,          # 29.9 cents of a 30-cent month
            )
        )
        await session.flush()
        with pytest.raises(cost.BudgetExceeded):
            await _write(session, user, profile, on=a_day_with, hits=sky, provider=provider)
        return await storage.written_count(session, user)

    assert db(work) == 0
    assert provider.calls == []


def test_a_generation_is_charged_to_the_month_ledger(db, sky, calendar, a_day_with):
    """Every daily goes through the same ledger as everything else."""
    occasion = calendar[a_day_with]
    provider = ScriptedProvider(responses=[reply(occasion.factor)])

    async def work(session):
        user, profile = await _person(session)
        piece = await _write(session, user, profile, on=a_day_with, hits=sky,
                             provider=provider)
        return piece, await cost.month_spend(session, user)

    piece, spent = db(work)
    assert spent > 0.0
    assert piece.body["model"] == "claude-sonnet-5"


# ── the measured policy ────────────────────────────────────────────────────

def test_the_moon_is_never_the_reason_a_daily_fires(sky, calendar):
    """§1.5, measured and decided permanently.

    About 1,600 exact lunar contacts a year on 358–365 days. A system that
    always has an answer is a system whose answers carry no information, which
    is the whole argument for this feature having quiet days at all.
    """
    assert not any(h.transiting == "moon" for h in sky)
    assert not any(o and o.hit.transiting == "moon" for o in calendar.values())


def test_the_moon_is_refused_even_when_a_caller_scans_it_in():
    """The exclusion is a rule here, not a default inherited from `scan`."""
    lunar = service.transits.scan(
        chart_for(BIRTH),
        start_jd=clock.to_jd(WINDOW_FROM),
        end_jd=clock.to_jd(WINDOW_FROM) + 30,
        bodies=("moon",),
        reference_jd=clock.to_jd(WINDOW_FROM),
    )
    assert lunar, "the fixture is only meaningful if the Moon really does perfect"
    days = {clock.local_date(h.exact_jd, ZONE) for h in lunar}
    for day in days:
        assert selection.occasion_for(lunar, on=day, zone=ZONE, floor=0.0) is None


def test_the_cadence_lands_inside_the_measured_band(sky):
    """The number the owner asked twice about, simulated over a chart-year.

    §4.2 measured a median of 45.5 pushes a year across 24 charts, a maximum of
    59, and every chart under 1.5 a week without the monthly cap ever binding.
    This chart is one of the 24. If an edit to `TRANSIT_ORBS`, `BODY_WEIGHT` or
    `NATAL_WEIGHT` moves it out of that band, this feature's frequency changed
    without anybody touching its code — which is exactly the drift the scripts
    in `backend/tools/daily/` were kept for.
    """
    pushes: list[date] = []
    kernels: list[tuple[date, str]] = []

    for offset in range(DAYS):
        day = WINDOW_FROM.date() + timedelta(days=offset)
        recent = [
            kernel for when, kernel in kernels
            if 0 < (day - when).days <= selection.RECENT_KERNEL_DAYS
        ]
        decision = selection.decide(
            sky, on=day, zone=ZONE, history=pushes, recent_kernels=recent
        )
        if decision.push:
            pushes.append(day)
            kernels.append((day, decision.occasion.kernel))

    per_week = len(pushes) / (DAYS / 7)
    assert 20 <= len(pushes) <= 70, f"{len(pushes)} pushes a year is outside §4.2"
    assert per_week < 1.5, f"{per_week:.2f}/week breaks the §4.1 band"

    gaps = [(b - a).days for a, b in zip(pushes, pushes[1:])]
    assert min(gaps) >= selection.MIN_GAP_DAYS
    by_month: dict[tuple[int, int], int] = {}
    for day in pushes:
        by_month[(day.year, day.month)] = by_month.get((day.year, day.month), 0) + 1
    assert max(by_month.values()) <= selection.MONTHLY_CAP


def test_quiet_hours_drop_rather_than_defer(sky, a_day_with):
    """22:00–08:00, hard, no override (§3.5).

    A daily is about a day. One that arrives at 02:00 to describe yesterday is
    worse than one that never arrives, and silence is already supported — so
    the notification is dropped, and nothing is queued for the morning.
    """
    for hour in (22, 23, 0, 3, 7):
        decision = selection.decide(sky, on=a_day_with, zone=ZONE, hour=hour)
        assert decision.push is False
        assert "quiet" in decision.reason
        # The occasion survives: Off and quiet hours are delivery preferences,
        # not feature gates. The page still has something to show.
        assert decision.occasion is not None


def test_off_silences_the_push_and_withholds_nothing(sky, a_day_with):
    decision = selection.decide(sky, on=a_day_with, zone=ZONE, preference=selection.OFF)
    assert decision.push is False
    assert decision.occasion is not None, "Off is a delivery preference, not a gate"


def test_only_what_matters_is_rarer_and_exact_only(sky, calendar):
    """§5.1: the Saturn returns and the Pluto squares, and nothing else."""
    strict = [
        d for d in calendar
        if selection.occasion_for(
            sky, on=d, zone=ZONE,
            floor=selection.ONLY_WHAT_MATTERS_FLOOR, slow_entry_floor=None,
        )
    ]
    ordinary = [d for d, o in calendar.items() if o is not None]
    assert len(strict) < len(ordinary)
    for day in strict:
        chosen = selection.occasion_for(
            sky, on=day, zone=ZONE,
            floor=selection.ONLY_WHAT_MATTERS_FLOOR, slow_entry_floor=None,
        )
        assert chosen.kind == selection.PERFECTS
        assert chosen.hit.weight >= selection.ONLY_WHAT_MATTERS_FLOOR


def test_the_three_day_gap_and_the_monthly_cap_both_hold(sky, a_day_with):
    inside = selection.decide(
        sky, on=a_day_with, zone=ZONE, history=[a_day_with - timedelta(days=1)]
    )
    assert inside.push is False and "last 3 days" in inside.reason

    # Exactly three days is still too soon. `decide` used to compare with `<`
    # where `rules.too_soon` compares with `<=`, so day three was allowed here
    # and blocked there; both now come from the one function.
    boundary = selection.decide(
        sky, on=a_day_with, zone=ZONE,
        history=[a_day_with - timedelta(days=selection.MIN_GAP_DAYS)],
    )
    assert boundary.push is False and "last 3 days" in boundary.reason

    # The weekly cap, which `decide` did not have at all. Two pushes spaced
    # four days apart are inside one week and inside the gap.
    weekly = selection.decide(
        sky, on=a_day_with, zone=ZONE,
        history=[a_day_with - timedelta(days=4), a_day_with - timedelta(days=6)],
    )
    assert weekly.push is False and "this week" in weekly.reason


def test_the_valve_needs_a_history_before_it_fires(sky, a_day_with):
    """A brand-new subscriber's first push must be a real one.

    §4.3's valve exists to break a 60-day silence, and an empty history
    is not a silence — it is an account that has not been here long enough to
    have had one. Firing on it would greet somebody with a piece announcing a
    quiet week they have not yet lived through.
    """
    fresh = selection.decide(sky, on=a_day_with, zone=ZONE, history=[])
    assert fresh.occasion is None or fresh.occasion.valve is False


def test_the_valve_lowers_the_floor_after_three_silent_weeks(sky):
    """And only then, and only for one candidate."""
    starved = None
    for offset in range(DAYS):
        day = WINDOW_FROM.date() + timedelta(days=offset)
        decision = selection.decide(
            sky, on=day, zone=ZONE,
            history=[day - timedelta(days=selection.VALVE_AFTER_DAYS)],
        )
        if decision.push and decision.occasion.valve:
            starved = decision.occasion
            break
    if starved is not None:
        assert starved.hit.weight >= selection.VALVE_FLOOR
        assert starved.hit.weight < selection.PUSH_FLOOR


# ── what the judges found, asserted ────────────────────────────────────────

def test_the_brief_carries_both_ends_of_the_aspect_and_names_it_in_words(
    sky, calendar, a_day_with
):
    """A live generation put Pluto on an Ascendant 300° away and was published.

    Kraków 1978, 2026-08-31, `pluto:sextile:ascendant`. The piece read
    "transiting Pluto reaches your Ascendant at 3°31′ Aries exactly, orb
    0.00°"; Pluto was at 3°31′ Aquarius. `validator.check` passed it on the
    first attempt and was right to — it compares citations, never prose.

    The prompt caused it: the aspect arrived only as a glyph, and the brief
    carried no position for the moving body, so the one degree anywhere in it
    was the natal one. This asserts both halves of the fix, plus the sentence
    that forbids the exact claim that was made.
    """
    from alma.daily import writing

    occasion = calendar[a_day_with]
    chart = chart_for(BIRTH)
    result = writing.brief(occasion, chart=chart, birth=BIRTH)
    prompt = writer.build_prompt(
        result,
        writing.chapter_for("en"),
        offered=[f for f in result.factors if f.startswith("transiting")],
    )

    # The aspect as a word, not only as ⚹ / □ / △.
    assert occasion.hit.aspect in prompt.lower()

    # The moving body's own degree, formatted exactly as the natal one is.
    moving = writing.moving_longitude(occasion)
    assert moving is not None
    assert zodiac.format_position(moving) in prompt

    natal = writing.natal_longitude(chart, occasion.hit.natal)
    if occasion.hit.aspect != "conjunction":
        assert abs(moving - natal) > 1.0, "a non-conjunction is not the same degree"
        assert "DIFFERENT SIGNS" in prompt


def test_the_sextile_glyph_is_the_sextile_and_not_a_dingbat():
    """U+26B9 SEXTILE, not U+2736 SIX POINTED BLACK STAR.

    The glyph used to be a decorative asterisk from the dingbats block. It is
    the only thing in a factor string that names the aspect, so it is what a
    model reads the geometry from.
    """
    assert zodiac.ASPECT_GLYPHS["sextile"] == "⚹"
    assert "✶" not in zodiac.ASPECT_GLYPHS.values()


def test_a_moment_already_past_is_not_announced_as_still_to_come(calendar, sky):
    """39% of exact hits perfect before the 08:00 delivery hour.

    Measured over six charts and a year. The untensed line told every one of
    those readers to look forward to something that had already happened —
    Seoul "exact at 00:04" delivered at 08:00, eight hours late.
    """
    occasion = next(
        (o for o in calendar.values() if o and o.kind == selection.PERFECTS), None
    )
    assert occasion is not None

    early = replace(occasion, at=occasion.at.replace(hour=3, minute=42))
    late = replace(occasion, at=occasion.at.replace(hour=17, minute=30))

    for locale in words.WORDS:
        past = notification.line(early, locale=locale)
        future = notification.line(late, locale=locale)
        assert past != future, locale
        assert "03:42" in past and "17:30" in future

    assert notification.compose(early, teaser="x").key == notification.KEY_EXACT_PAST
    assert notification.compose(late, teaser="x").key == notification.KEY_EXACT

    # And the brief tells the model the same thing, so the prose agrees with
    # the title rather than following the tense it was handed.
    from alma.daily import writing

    assert "past tense" in writing._timing(early)
    assert "past tense" not in writing._timing(late)


def test_no_composed_line_in_any_language_doubles_an_article(calendar, a_day_with):
    """German shipped "Transit-die Sonne im Quadrat zu deiner Sonne".

    `transiting` is a prefix in English and German and a suffix in the four
    Romance languages, so `bodies` has to hold a bare noun in the first two and
    an article-carrying one in the rest. The transiting Sun is 23% of pushes.
    """
    doubled = {
        "de": ("Transit-die", "Transit-der", "Transit-das"),
        "en": ("Transiting the", "Transiting a"),
    }
    for locale in words.WORDS:
        vocabulary = words.words_for(locale)
        for body in vocabulary.bodies:
            for aspect in vocabulary.aspects:
                for point in vocabulary.points:
                    line = vocabulary.contact(body=body, aspect=aspect, point=point)
                    for bad in doubled.get(locale, ()):
                        assert bad not in line, f"{locale}: {line}"

    assert words.words_for("de").contact(
        body="sun", aspect="square", point="sun"
    ) == "Transit-Sonne im Quadrat zu deiner Sonne"


def test_the_same_contact_is_not_announced_twice_in_a_month(sky, a_day_with):
    """The enters→perfects pair was 18% of all pushes.

    `jupiter:conjunction:mars` enters orb on 4 September and perfects on 11
    September; both cleared their floor independently because nothing keyed on
    the contact's own identity. The entry is the one kept — suppressing the
    *later* half is the only causal choice, since on the day a window opens
    nothing knows whether the exact will survive the gap a week later.
    """
    first = selection.decide(sky, on=a_day_with, zone=ZONE, history=[])
    assert first.push is True

    again = selection.decide(
        sky,
        on=a_day_with,
        zone=ZONE,
        history=[],
        recent_kernels=[first.occasion.kernel],
    )
    assert again.push is False
    assert "already sent" in again.reason


def test_a_silence_the_sky_caused_is_not_blamed_on_the_gap(sky):
    """`Decision.reason` is the only diagnostic this feature has.

    The guards used to run gap-before-emptiness, so 8 days of a 30-day month
    reported "last push was 1 day(s) ago" about days on which nothing had been
    suppressed at all — the more alarming of the two answers, and the wrong one.
    """
    empty = [
        WINDOW_FROM.date() + timedelta(days=i)
        for i in range(120)
        if selection.occasion_for(sky, on=WINDOW_FROM.date() + timedelta(days=i), zone=ZONE)
        is None
    ]
    assert empty, "a chart with something every day would be a different bug"

    day = empty[0]
    decision = selection.decide(
        sky, on=day, zone=ZONE, history=[day - timedelta(days=1)]
    )
    assert decision.occasion is None
    assert "nothing in this chart" in decision.reason
    assert "day" not in decision.reason.replace("today", "")


def test_the_two_packages_agree_about_the_cadence(sky, a_day_with):
    """`selection.decide` and `notify.rules` are one rule, not two that match.

    They drifted once: `<` against `<=` on the gap, and no weekly cap here at
    all. The arithmetic is now `rules.too_soon`'s in both places, so the test
    is that the numbers are the same object rather than the same value.
    """
    from alma.notify import rules

    assert selection.MIN_GAP_DAYS is rules.MIN_GAP_DAYS
    assert selection.WEEKLY_CAP is rules.PER_WEEK
    assert selection.MONTHLY_CAP is rules.PER_MONTH
    assert selection.VALVE_AFTER_DAYS is rules.VALVE_AFTER_DAYS

    for gap in (1, 2, 3, 4, 5):
        history = [a_day_with - timedelta(days=gap)]
        mine = selection.decide(sky, on=a_day_with, zone=ZONE, history=history)
        theirs = rules.too_soon(a_day_with, history)
        if mine.occasion is None:
            continue
        assert bool(theirs) == (not mine.push), f"{gap} days apart"


def test_a_daily_carries_no_advice_even_when_the_model_writes_one(
    db, sky, calendar, a_day_with
):
    """`voice.DAILY_TIER` forbids the horoscope voice; the schema asked anyway.

    Seven of eight live generations filled `advice`, every one with the banned
    content — "wait an hour before answering it". It is the line most likely to
    be screenshotted and it collides with the product's own legal copy.
    """
    occasion = calendar[a_day_with]
    payload = json.loads(reply(occasion.factor))
    payload["advice"] = "Wait an hour before answering it."
    provider = ScriptedProvider(responses=[json.dumps(payload)])

    async def work(session):
        user, profile = await _person(session)
        return await _write(session, user, profile, on=a_day_with, hits=sky,
                            provider=provider)

    piece = db(work)
    assert piece.body["advice"] == ""

    # And the field is not even offered, so the tokens are not spent on it —
    # and no instruction leaks sideways into the paragraphs.
    from alma.daily import writing

    assert "advice" not in writer.schema_for(writing.chapter_for("en"))["properties"]
    assert "advice" in writer.schema_for(chapters.BY_SYSTEM["natal"][0])["properties"]


# ── the notification ───────────────────────────────────────────────────────

def test_the_notification_names_the_placement_and_the_minute(calendar, a_day_with):
    """"Mars reaches your Ascendant at 14:20", not "Something is happening today"."""
    occasion = calendar[a_day_with]
    if occasion.kind != selection.PERFECTS:
        pytest.skip("this chart's first occasion is an orb entry, which has no minute")

    line = notification.line(occasion, locale="en")
    assert clock.format_time(occasion.at) in line
    assert occasion.hit.transiting.capitalize() in line or occasion.hit.transiting in line.lower()
    assert occasion.hit.natal.replace("_", " ") in line.lower() or "node" in line.lower()


def test_the_notification_exists_in_all_six_languages(calendar, a_day_with):
    occasion = calendar[a_day_with]
    lines = {locale: notification.line(occasion, locale=locale) for locale in words.WORDS}
    assert len(set(lines.values())) == len(words.WORDS), "two locales produced the same line"
    for locale, line in lines.items():
        assert line.strip()
        if occasion.kind == selection.PERFECTS:
            assert clock.format_time(occasion.at) in line


def test_every_placement_a_transit_can_touch_has_six_words():
    """The defect `docs/PUSH.md §3` found: "Ascendant" inside an Italian sentence.

    `loc-args` are substituted verbatim, and until this table existed the
    localised placement names lived only in the two clients. A natal point that
    can be transited but has no word here would appear in English in the middle
    of five other languages.
    """
    from alma.engine import transits

    reachable = set(transits.NATAL_WEIGHT) | {"ascendant", "midheaven"}
    assert reachable == set(words.POINT_KEYS)
    for locale in words.WORDS:
        vocabulary = words.words_for(locale)
        assert set(vocabulary.points) == reachable
        assert set(vocabulary.aspects) == {a for a, _ in transits.ASPECT_TARGETS}
        assert set(vocabulary.bodies) >= set(transits.TRANSIT_ORBS)


def test_every_daily_string_exists_in_every_language():
    """The rule `alma/i18n/` already holds, extended to this package's copy."""
    for locale in words.WORDS:
        vocabulary = words.words_for(locale)
        assert vocabulary.locale == locale
        assert set(vocabulary.settings) == set(words.SETTING_KEYS)
        for key in words.SETTING_KEYS:
            assert vocabulary.settings[key].strip(), f"{locale}/{key} is empty"
        assert vocabulary.title.strip() and vocabulary.question.strip()
        for template in (vocabulary.line_exact, vocabulary.line_entering, vocabulary.line_quiet):
            assert "{contact}" in template
        assert "{time}" in vocabulary.line_exact
        assert "{body}" in vocabulary.transiting


def test_no_language_was_left_in_english():
    """The check `scripts/check-locales.mjs` runs on the web dictionaries.

    Not applied to proper nouns — "Mars" is "Mars" in four of the six — but the
    sentences are copy and a sentence identical to the English is a sentence
    nobody translated.
    """
    english = words.words_for("en")
    for locale in words.WORDS:
        if locale == "en":
            continue
        theirs = words.words_for(locale)
        shared = [
            key for key in words.SETTING_KEYS
            if theirs.settings[key] == english.settings[key]
        ]
        assert not shared, f"{locale} still reads English at {shared}"
        assert theirs.question != english.question


def test_a_notification_without_a_written_piece_is_impossible(calendar, a_day_with):
    """No piece, no push.

    The notification's body is the piece's teaser, which was generated, cited
    and validated. There is deliberately no path that invents one, because a
    line on a lock screen must not claim more than the validated piece behind
    it.
    """
    occasion = calendar[a_day_with]
    with pytest.raises(ValueError):
        notification.compose(occasion, teaser="", locale="en")
    with pytest.raises(ValueError):
        notification.compose(occasion, teaser="   ", locale="en")


def test_the_notification_carries_the_instant_for_a_client_to_reformat(
    calendar, a_day_with
):
    """The server knows the language and never the region.

    "14:20" or "2:20 PM" is an en-GB/en-US question and every locale we hold is
    a language, so the composed line is 24-hour everywhere and the ISO instant
    travels beside it.
    """
    occasion = calendar[a_day_with]
    note = notification.compose(occasion, teaser="Mars reaches your Moon.", locale="en")
    payload = note.payload()
    assert payload["at"].startswith(occasion.on.isoformat())
    assert payload["loc_key"].startswith("daily.push.")
    assert payload["loc_args"], "a client composing locally needs the arguments"
    assert payload["body"] == "Mars reaches your Moon."


def test_the_localised_arguments_are_in_the_readers_language(calendar, a_day_with):
    """The pre-localisation that removes `PUSH.md`'s verbatim-substitution trap."""
    occasion = calendar[a_day_with]
    italian = notification.compose(occasion, teaser="Oggi.", locale="it")
    assert "il tuo" in italian.args[0] or "la tua" in italian.args[0]
    assert "in transito" in italian.args[0]


def test_a_valve_piece_is_announced_differently(calendar, a_day_with):
    """§4.3 makes this a condition of the valve existing at all."""
    from dataclasses import replace

    occasion = calendar[a_day_with]
    quiet = replace(occasion, valve=True)
    for locale in words.WORDS:
        loud_line = notification.line(occasion, locale=locale)
        quiet_line = notification.line(quiet, locale=locale)
        assert quiet_line != loud_line
        assert notification.compose(quiet, teaser="x", locale=locale).key == (
            notification.KEY_QUIET
        )


# ── the clock, and the chart without a birth time ──────────────────────────

def test_the_delivery_clock_is_not_the_birth_clock():
    """§3.1's trap, asserted so nobody reaches for `Profile.timezone` directly.

    Somebody born in Auckland and living in Berlin has a birth timezone of
    Pacific/Auckland and no part of the system knows they moved. Using it as
    the delivery clock sends a good-morning piece at 20:00.
    """
    zone, source = clock.zone_for(device="Europe/Berlin", birth="Pacific/Auckland")
    assert str(zone) == "Europe/Berlin" and source == "device"

    zone, source = clock.zone_for(chosen="Europe/Lisbon", birth="Pacific/Auckland")
    assert str(zone) == "Europe/Lisbon" and source == "chosen"

    zone, source = clock.zone_for(birth="Pacific/Auckland")
    assert str(zone) == "Pacific/Auckland" and source == "birth"

    zone, source = clock.zone_for(device="Mars/Olympus_Mons", birth="Pacific/Auckland")
    assert str(zone) == "Pacific/Auckland", "an unresolvable rung is skipped, not fatal"
    assert source == "birth"

    assert clock.zone_for()[1] == "fallback"


def test_a_local_day_is_the_readers_day_and_not_utc(sky):
    """The whole reason `clock.py` exists.

    A contact that perfects at 23:40 UTC belongs to the next day in Tokyo and
    to the same day in New York. Filing it under UTC tells a Tokyo reader on
    the morning it happens that nothing is happening.
    """
    tokyo, new_york = ZoneInfo("Asia/Tokyo"), ZoneInfo("America/New_York")
    disagreements = sum(
        1 for h in sky
        if clock.local_date(h.exact_jd, tokyo) != clock.local_date(h.exact_jd, new_york)
    )
    assert disagreements > 0


def test_a_chart_without_a_birth_time_says_so_rather_than_serving_less():
    """§7: the daily is measurably thinner for these people and must admit it."""
    from alma.daily import writing

    hits = service.hits_for(TIMELESS, start=WINDOW_FROM, days=45)
    zone = ZoneInfo("Pacific/Auckland")
    occasion = next(
        (
            selection.occasion_for(hits, on=WINDOW_FROM.date() + timedelta(days=i), zone=zone)
            for i in range(45)
            if selection.occasion_for(hits, on=WINDOW_FROM.date() + timedelta(days=i), zone=zone)
        ),
        None,
    )
    assert occasion is not None, "45 days with nothing at all would be a different bug"
    assert occasion.hit.natal not in ("ascendant", "midheaven")

    result = writing.brief(occasion, chart=chart_for(TIMELESS), birth=TIMELESS)
    assert any("birth time is unknown" in note for note in result.unavailable)


# ── the job's idempotency ──────────────────────────────────────────────────

def test_a_job_that_runs_twice_sends_once(db, a_day_with):
    """§6.9. The hourly job will sometimes run twice over the same person.

    That is the price of a job whose missed run costs an hour rather than a
    day, and `user:day:daily_push` in `UsageCounter` is what makes the second
    run a no-op — the same mechanism `renewals.py` uses under its own metric.
    """
    async def work(session):
        user, _ = await _person(session)
        first = await service.claim_push(session, user, on=a_day_with)
        second = await service.claim_push(session, user, on=a_day_with)
        return first, second, await storage.push_history(session, user, on=a_day_with)

    first, second, history = db(work)
    assert first is True and second is False
    assert history == [a_day_with]


def test_the_push_history_feeds_the_gap_and_the_cap(db, a_day_with):
    async def work(session):
        user, _ = await _person(session)
        for offset in (0, 4, 8):
            await service.claim_push(session, user, on=a_day_with + timedelta(days=offset))
        # A row dated after the day being asked about is not a push that has
        # happened, and counting it would silence somebody over an event they
        # never received.
        await service.claim_push(session, user, on=a_day_with + timedelta(days=40))
        return await storage.push_history(session, user, on=a_day_with + timedelta(days=8))

    history = db(work)
    assert history == [
        a_day_with, a_day_with + timedelta(days=4), a_day_with + timedelta(days=8)
    ]


def test_a_stored_daily_is_reachable_as_a_reading(db, sky, calendar, a_day_with):
    """Which is what makes `erase` and the account export already correct.

    `accounts.erase` deletes by walking an explicit list of tables and
    `GET /v1/account/export` reads `Reading`; both live in a file this workflow
    may not edit. A `DailyPiece` table would have been missing from both, and
    nothing fails when a table is missing from that list — which is exactly the
    promise `models.py`'s docstring warns about breaking without noticing.
    """
    occasion = calendar[a_day_with]
    provider = ScriptedProvider(responses=[reply(occasion.factor)])

    async def work(session):
        user, profile = await _person(session)
        await _write(session, user, profile, on=a_day_with, hits=sky, provider=provider)
        exported = await accounts.export(session, user)
        return exported

    exported = db(work)
    readings = exported.get("readings") or []
    assert any(
        storage.date_of(r.get("chapter") or "") == a_day_with for r in readings
    ), "a written daily must appear in the account export"


# ── the contract `alma/notify/` consumes ───────────────────────────────────

def test_the_notify_job_gets_the_candidates_it_declares_it_needs(db, a_day_with):
    """`alma/notify/daily.py::_selector` names this signature and raises without it.

    That package draws the boundary explicitly — *the astronomy is this
    package's and the cadence is that one's* — and its job refuses loudly
    rather than running to completion and sending nothing, which is the failure
    that looks exactly like success. So the shape is asserted here rather than
    discovered in production.
    """
    from alma.notify import rules

    async def work(session):
        user, _ = await _person(session)
        return await service.candidates(session, user, on=a_day_with)

    found = db(work)
    assert found, "the day the fixtures picked has at least one contact on it"
    for candidate in found:
        assert isinstance(candidate, rules.Candidate), "must satisfy their protocol"
        assert candidate.exact or candidate.entering
        assert candidate.exact_at.tzinfo is not None
        assert candidate.weight > 0


def test_the_zone_the_sender_resolved_is_the_one_the_day_is_bracketed_on(
    db, a_day_with, monkeypatch
):
    """The device's clock has to survive the hand-off, or the daily is birth-timed.

    `Profile.timezone` is where somebody was *born*, and for everybody who has
    moved it is wrong by however many hours they flew. The sender holds the
    device rows, resolves the ladder once and passes the answer; deciding again
    in here would put the day's boundaries back on the birth clock while the
    morning was chosen on another, and the piece would be filed under a day it
    was not sent on.

    Both halves are asserted. Dropping the argument silently is the way this
    regresses, and it regresses green: the fallback keeps every other test
    passing.
    """
    seen: list[ZoneInfo] = []
    real = clock.day_bounds

    def spy(on, zone):
        seen.append(zone)
        return real(on, zone)

    monkeypatch.setattr(clock, "day_bounds", spy)

    async def given(session):
        user, _ = await _person(session)
        return await service.candidates(
            session, user, on=a_day_with, zone=ZoneInfo("Pacific/Auckland")
        )

    db(given)
    assert seen and set(seen) == {ZoneInfo("Pacific/Auckland")}, (
        "the zone the caller resolved was ignored somewhere below"
    )

    seen.clear()

    async def omitted(session):
        user, _ = await _person(session)
        return await service.candidates(session, user, on=a_day_with)

    db(omitted)
    assert seen and set(seen) == {ZoneInfo(BIRTH.timezone)}, (
        "without a zone the ladder here still has to resolve — a direct caller "
        "and a test have no device table to ask"
    )


def test_candidates_are_unfiltered_and_the_cadence_module_does_the_filtering(
    db, a_day_with, calendar
):
    """Two modules each dropping "the obviously irrelevant" is a floor applied twice.

    `rules.pick` owns the weight bar. This function hands over everything the
    sky offers, Mercury included — §1.3's 55% of the volume and 4% of the
    meaning — and the two agree about the answer only because exactly one of
    them is deciding.
    """
    from alma.notify import rules

    async def work(session):
        user, _ = await _person(session)
        return await service.candidates(session, user, on=a_day_with)

    found = db(work)
    assert any(c.weight < selection.PUSH_FLOOR for c in found), (
        "candidates must include what the floor will reject, or the floor is "
        "being applied in two places"
    )
    chosen = rules.pick(found, bar=rules.BARS[rules.Preference.occasionally])
    mine = calendar[a_day_with]
    assert chosen is not None
    assert (chosen.candidate.transiting, chosen.candidate.natal, chosen.candidate.aspect) == (
        mine.hit.transiting, mine.hit.natal, mine.hit.aspect
    ), "the two packages must choose the same contact for the same day"


def test_a_person_with_no_saved_birth_yields_no_candidates(db, a_day_with):
    """One profile-less account must not stop a run over every subscriber."""
    async def work(session):
        user = await accounts.create_guest(session)
        return await service.candidates(session, user, on=a_day_with)

    assert db(work) == []


def test_erase_takes_the_daily_with_it(db, sky, calendar, a_day_with):
    occasion = calendar[a_day_with]
    provider = ScriptedProvider(responses=[reply(occasion.factor)])

    async def work(session):
        user, profile = await _person(session)
        await _write(session, user, profile, on=a_day_with, hits=sky, provider=provider)
        assert await storage.written_count(session, user) == 1
        await accounts.erase(session, user)
        return await storage.written_count(session, user)

    assert db(work) == 0
