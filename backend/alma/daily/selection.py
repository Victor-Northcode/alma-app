"""Whether today is worth saying anything about, and if so which one thing.

Every number in this module was measured rather than chosen, and
`docs/THE-DAILY.md` is where the measuring is written down. Nothing here should
be re-derived from taste; if one of these constants looks wrong, the six
scripts in `backend/tools/daily/` re-run the measurement that produced it.

**The finding that shapes the module.** An ordinary chart has an exact aspect
on 259–276 days a year and something in orb on 87–94% of them (§1.2). The
problem was never that there is too little to say — it is that Mercury and
Venus are 55% of the volume and 4% of the meaning (§1.3), and a daily built on
all of it would be a horoscope that happens to be arithmetically true. So this
module's whole job is subtraction: it takes ~470 contacts a year and returns at
most one a day, on about 46 days.

**No second scoring system.** `transits._weight` is
`BODY_WEIGHT × NATAL_WEIGHT × ASPECT_WEIGHT`, and §1.3 measured that it already
encodes exactly the slow-versus-fast distinction the daily needs — at floor
0.30 a chart keeps 76 contacts of 479 and loses essentially all of Mercury and
Venus. Inventing a "daily score" here would be a second opinion about the same
question, and the two would diverge on the day somebody edits one of them.

**Silence is a state, not a failure.** `occasion_for` returning `None` is the
common case and the correct one. §4.1 sets the floor at *zero* pushes: there
is no minimum, no filler, and no "we had better say something". That is only
survivable because the pull surface — what is in orb, always there — does not
depend on this module at all.

---

**Who owns what, because two packages arrived at this from different sides.**
`alma/notify/rules.py` was written in parallel with this file, against the same
measured document, and it states the intended boundary in its own words: *the
astronomy is the daily package's and the cadence is that module's*. That split
is right and this package serves it — `service.candidates` is the contract
`alma/notify/daily.py` asks for by name, and a test in `tests/test_daily.py`
asserts the two packages choose the same contact for the same day.

The consequence for `decide` below: **`rules.may_send` is the authority on
whether a notification is sent**, because it is what the job actually calls and
because it knows things this file does not — dormancy, the entitlement, the
stored preference, whether this is even the person's hour. `decide` is the same
policy expressed for callers that have no notification in the picture at all:
the Today page, the simulations in `backend/tools/daily/`, and this package's
own tests, which need to assert the gap and the cap without standing up a
device-token table.

That used to be enforced by a test and it was not enough. The two drifted:
`decide` compared the gap with `<` where `rules.too_soon` compares with `<=`,
so a push exactly three days after the last one was allowed here and blocked
there, and `decide` had no weekly cap at all while `rules.PER_WEEK` was 2. The
measured 45.5-a-year figure was therefore being re-derived by the simulations
from a rule looser than the one that ships. **So the cadence arithmetic is no
longer duplicated: `decide` calls `rules.too_soon` and `rules.valve_is_open`,
and the constants below are imported rather than restated.** Two modules cannot
disagree about a number neither of them owns twice.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Sequence
from zoneinfo import ZoneInfo

from ..engine import transits
from ..engine.transits import Hit
from ..notify import rules
from . import clock

# ── the measured constants (docs/THE-DAILY.md §6.3) ────────────────────────

#: What earns an interruption when something perfects today. §4.2 simulated
#: this over 24 charts: median 45.5 pushes a year, worst chart 59, every chart
#: under 1.5 a week without the monthly cap ever binding.
PUSH_FLOOR = 0.35

#: A slow body *entering orb* is news at a lower bar than a fast body
#: perfecting, because a Neptune window is 86 days at the median (§1.3) and the
#: day it opens is the only day it is new.
SLOW_ENTRY_FLOOR = 0.30

#: The starvation valve (§4.3). Measured: halves the worst silence from 60 days
#: to 33, moves the median by one notification a year, does not move the
#: maximum at all, and fires 1.75 times per chart-year. The 14-day variant
#: fires 111 times over the same 24 chart-years and is where manufacturing
#: content begins.
#:
#: Imported from `rules.py` rather than restated, along with the three cadence
#: numbers below. They were written out twice and drifted; see the module
#: docstring. Kept under this module's own names so that callers and tests
#: reading `selection.MIN_GAP_DAYS` still work — an alias cannot disagree with
#: what it aliases.
VALVE_FLOOR = rules.VALVE_FLOOR
VALVE_AFTER_DAYS = rules.VALVE_AFTER_DAYS

#: "Only what matters" (§5.1): the Saturn returns and the Pluto squares, 7–13 a
#: year. Exact hits only — an orb entry at this weight would double the count
#: of a setting whose entire promise is that it is rare.
ONLY_WHAT_MATTERS_FLOOR = 0.50

#: §4.1. Above two a week the Braze/Klaviyo uninstall risk turns over, and an
#: uninstall costs the whole subscription rather than the notification. §4.2
#: showed the caps never bind on any of 24 charts — they guard a chart we have
#: not seen. A cap that does the work would be a cap lying about the content.
MIN_GAP_DAYS = rules.MIN_GAP_DAYS
WEEKLY_CAP = rules.PER_WEEK
MONTHLY_CAP = rules.PER_MONTH

#: How long a contact stays "already said". The enters→perfects pair is the
#: whole problem: `jupiter:conjunction:mars` enters orb on 4 September and
#: perfects on 11 September, and both cleared their floor independently because
#: nothing anywhere keyed on the contact's own identity. Measured over six
#: chart-years, **52 of 293 pushes repeated a contact seen inside 30 days** and
#: almost all of them were that pair, 7–10 days apart.
#:
#: A repeat is the most expensive notification this feature can send. Its whole
#: defence of a low volume is that every interruption is worth taking, and the
#: second "Jupiter conjunct your Mars" reads as the app having forgotten it
#: already said this — which teaches the reader that the next one is probably
#: also nothing new.
#:
#: Thirty days rather than a year. Beyond a month the exactness genuinely is
#: news again: a Pluto contact whose window opened in June and perfects in
#: September is two different facts to somebody living through it, and
#: suppressing the second would be the rule overshooting into silence.
RECENT_KERNEL_DAYS = 30

#: §3.4/§3.5, in the reader's own clock. Fixed, not optimised: this product's
#: content is "here is what today contains", and a piece about today arriving
#: at 22:00 is a piece about a day already had.
DELIVERY_HOUR = 8
QUIET_FROM = 22
QUIET_UNTIL = 8

OFF = "off"
OCCASIONALLY = "occasionally"
ONLY_WHAT_MATTERS = "only_what_matters"
PREFERENCES: frozenset[str] = frozenset({OFF, OCCASIONALLY, ONLY_WHAT_MATTERS})

PERFECTS = "perfects"
ENTERS = "enters"


@dataclass(frozen=True, slots=True)
class Occasion:
    """One event, with everything needed to write about it and to cite it.

    Deliberately carries no interpretation and no prose. It is the fact, in the
    reader's clock, plus the one string `alma/ai/validator.py` will check a
    generated paragraph against.
    """

    hit: Hit
    kind: str                       # PERFECTS | ENTERS
    on: date                        # the reader's local date this belongs to
    at: object                      # datetime in the reader's zone
    zone: str

    #: The orb at `at`, exactly. Zero when the aspect perfects — that is what
    #: perfecting means — and the body's orb limit when it enters, because that
    #: is what the edge of the window is. `Hit.orb_now` is deliberately not
    #: used: it is measured against the *scan's* reference instant, which for
    #: the year-ahead scan §6.2 recommends is up to a year ago, and quoting it
    #: as "the orb today" would be the one false number in a piece whose whole
    #: argument is that its numbers are true.
    orb: float

    enters_at: object | None        # datetime | None
    leaves_at: object | None        # datetime | None

    #: How many whole days this contact has already been in orb by `on`. The
    #: difference between "Saturn squares your Sun today" and "…and it has been
    #: building since March", which is the sentence the subscription is for.
    settled_days: int | None

    #: True when only the starvation valve admitted this. The piece must read
    #: as the quiet week it is (`voice.DAILY_TIER` says so in the prompt), and
    #: `notification.py` uses a different line for it.
    valve: bool = False

    @property
    def factor(self) -> str:
        """The citable string, spelled by `Hit.describe` and nothing else.

        Spelled by the same method the rest of the product uses, because
        `alma/ai/validator.py` compares character by character and a second
        spelling of the same fact is a refused reading.

        The one thing that is corrected is the orb. `Hit.orb_now` is measured
        against the *scan's* reference instant, which for the year-ahead scan
        §6.2 recommends is up to a year away from the day being written about —
        so `describe()` on the raw hit would print a real number that is true
        about a different day. `self.orb` is the orb at `self.at` and it is
        known exactly rather than computed: zero when an aspect perfects,
        because that is what perfecting means, and the body's orb limit when it
        enters, because that is what the edge of a window is. No ephemeris call
        and no chance of drift.
        """
        return replace(self.hit, orb_now=round(self.orb, 4)).describe()

    @property
    def kernel(self) -> str:
        """(transiting, aspect, natal) — the identity of the contact itself.

        Not an identity for the *event*: §2.5 measured that keying on this and
        sharing the generated prose buys 19.3× reuse and destroys the degree,
        the sign, the house, the instant and the window, i.e. everything the
        validator exists to enforce. It is used here only for logging and for
        the stored piece's provenance.
        """
        return f"{self.hit.transiting}:{self.hit.aspect}:{self.hit.natal}"


@dataclass(frozen=True, slots=True)
class Decision:
    """What to do today: what there is, and whether to interrupt for it."""

    occasion: Occasion | None
    push: bool
    #: Why not, when not. Not for the reader — for the log line that answers
    #: "why did I get nothing on Tuesday", which is a support question this
    #: feature will certainly generate.
    reason: str


def floor_for(preference: str) -> float:
    if preference == ONLY_WHAT_MATTERS:
        return ONLY_WHAT_MATTERS_FLOOR
    return PUSH_FLOOR


def is_quiet(hour: int) -> bool:
    """22:00–08:00, hard, in the reader's own clock.

    No override, not even a user override (§5.2). Making it editable invites
    somebody to set 03:00 and then file a complaint about a 03:00 notification,
    and a hard floor means the ePrivacy question never has to be argued in
    front of a regulator or a store reviewer.
    """
    return hour >= QUIET_FROM or hour < QUIET_UNTIL


def candidates_for(
    hits: list[Hit],
    *,
    on: date,
    zone: ZoneInfo,
    floor: float = PUSH_FLOOR,
    slow_entry_floor: float | None = SLOW_ENTRY_FLOOR,
) -> list[Occasion]:
    """Everything on this day that clears its floor, heaviest first.

    `occasion_for` is this and then `[0]`. It is split out because `decide`
    needs to be able to reach past the top one: when the heaviest thing today
    is a contact we announced a week ago, the day's actual news is the next one
    down, and picking it requires seeing the list rather than the winner.
    """
    day_start, _ = clock.day_bounds(on, zone)
    found: list[Occasion] = []

    for hit in hits:
        # The Moon is excluded here as well as at the scan, and permanently.
        # §1.5 measured ~1,600 lunar contacts a year on 358–365 days: a system
        # that always has an answer is a system whose answers carry no
        # information. `scan` defaults to excluding it, but the default is a
        # default and this is the rule.
        if hit.transiting == "moon":
            continue

        if hit.weight >= floor and clock.local_date(hit.exact_jd, zone) == on:
            found.append(
                _occasion(hit, kind=PERFECTS, on=on, jd=hit.exact_jd, zone=zone,
                          day_start=day_start)
            )
            continue

        if slow_entry_floor is None or hit.enters_jd is None:
            continue
        if hit.transiting not in transits.SLOW_BODIES:
            continue
        if hit.weight >= slow_entry_floor and clock.local_date(hit.enters_jd, zone) == on:
            found.append(
                _occasion(hit, kind=ENTERS, on=on, jd=hit.enters_jd, zone=zone,
                          day_start=day_start)
            )

    found.sort(key=lambda o: (-o.hit.weight, o.at))
    return found


def occasion_for(
    hits: list[Hit],
    *,
    on: date,
    zone: ZoneInfo,
    floor: float = PUSH_FLOOR,
    slow_entry_floor: float | None = SLOW_ENTRY_FLOOR,
) -> Occasion | None:
    """The one thing worth saying on this local day, or nothing.

    `hits` is whatever `transits.scan(chart, …, include_moon=False)` returned —
    this function never scans. §6.2: scan a year ahead once and store it; the
    same answer costs 30× more computed nightly, and a second scanner in this
    package would be a second set of numbers to keep in step with the first.

    Two ways to be a candidate, and both conditions in §4.1 matter:

    * the aspect **perfects** today at `weight ≥ floor`;
    * or a **slow** body's contact **enters orb** today at
      `weight ≥ slow_entry_floor`.

    Weight alone would fire on one heavy slow transit every day for three
    months. Novelty alone would fire on Mercury forever. Together they produce
    the measured 46 days a year.

    Ties go to the heavier contact and then to the earlier instant. At most one
    a day, always — two pieces about the same morning is two notifications
    dressed as one feature.
    """
    found = candidates_for(
        hits, on=on, zone=zone, floor=floor, slow_entry_floor=slow_entry_floor
    )
    return found[0] if found else None


def _occasion(
    hit: Hit, *, kind: str, on: date, jd: float, zone: ZoneInfo, day_start: float
) -> Occasion:
    settled = None
    if hit.enters_jd is not None:
        settled = max(0, int(day_start - hit.enters_jd))
    return Occasion(
        hit=hit,
        kind=kind,
        on=on,
        at=clock.local(jd, zone),
        zone=str(zone),
        orb=0.0 if kind == PERFECTS else transits.TRANSIT_ORBS.get(hit.transiting, 1.0),
        enters_at=clock.local(hit.enters_jd, zone) if hit.enters_jd is not None else None,
        leaves_at=clock.local(hit.leaves_jd, zone) if hit.leaves_jd is not None else None,
        settled_days=settled,
    )


def decide(
    hits: list[Hit],
    *,
    on: date,
    zone: ZoneInfo,
    preference: str = OCCASIONALLY,
    hour: int = DELIVERY_HOUR,
    history: Sequence[date] = (),
    recent_kernels: Sequence[str] = (),
) -> Decision:
    """Today's occasion, and whether it earns an interruption.

    The occasion is computed **whatever the preference is**, including Off.
    That is not an oversight: §5.1 is explicit that Off is a delivery
    preference and not a feature gate — "the Today page still works, nothing is
    withheld". A person who turned notifications off and opens the app must see
    the same day everybody else got told about.

    `history` is the local dates a daily actually went out on, and it replaced
    a `last_push_on` / `pushes_this_month` pair. The pair could express the gap
    and the monthly cap and could not express the weekly one, which is exactly
    why this function used to be missing it. It is the same argument the
    `history` list already makes in `rules.py`, and it is handed straight to
    `rules.too_soon` so the two cannot answer differently.

    `recent_kernels` is the contacts this person has already been told about
    inside `RECENT_KERNEL_DAYS`, and it is what stops the enters→perfects pair
    arriving as two notifications a week apart about the same planet, the same
    natal point and the same aspect.

    **The guard order is not the order of cost, and that was a bug.** It used
    to be preference → quiet → gap → cap → nothing-to-say, so on a day when
    `occasion_for` had returned nothing at all the reason still read "last push
    was 1 day(s) ago" — over one 30-day month that was 8 days out of 30
    reporting a cadence rule as the cause of a silence the sky was responsible
    for. `Decision.reason` exists to answer "why did I get nothing on Tuesday",
    and answering it with the more alarming of two possible causes sends
    whoever is debugging to investigate a rule that did nothing. Emptiness is
    now checked first: the gap and the caps only matter when there is something
    to suppress, which also makes them cheaper.
    """
    if preference not in PREFERENCES:
        raise ValueError(f"unknown notification preference {preference!r}")

    past = sorted(d for d in history if d <= on)
    ordinary = floor_for(preference)
    starved = preference == OCCASIONALLY and rules.valve_is_open(on, past)

    ranked = candidates_for(
        hits,
        on=on,
        zone=zone,
        floor=VALVE_FLOOR if starved else ordinary,
        # "Only what matters" takes exact hits only. An orb entry is a
        # legitimate piece of news at 0.30 and noise at a setting whose whole
        # promise is a handful a year.
        slow_entry_floor=None if preference == ONLY_WHAT_MATTERS else SLOW_ENTRY_FLOOR,
    )

    # Reach past a contact this person was already told about. Suppressing the
    # *later* half of a pair rather than the earlier one is the only causal
    # choice available: on the day a window opens nothing knows whether a
    # heavier event will land before it perfects, so holding the entry back in
    # the hope of a better exact could end in the gap or the cap eating that
    # one too and the reader hearing nothing at all. Dropping a repeat is a
    # pure function of what has already happened.
    already = frozenset(recent_kernels)
    fresh = [item for item in ranked if item.kernel not in already]
    repeated = len(ranked) - len(fresh)
    occasion = fresh[0] if fresh else None

    # The valve *opened* is not the same as the valve being *used*. Three quiet
    # weeks lower the floor to 0.20, but the heaviest thing that day is usually
    # still something that would have cleared 0.35 on its own — and marking
    # that as a valve piece would be a lie in two places at once: the brief
    # would tell the model the week is quiet, and the notification would go out
    # under `line_quiet` reading "a quiet week, this is the one thing still
    # moving" about an ordinary Mars square. So the flag is set from the
    # candidate that actually won, not from the condition that let it in.
    if occasion is not None and starved:
        occasion = replace(occasion, valve=occasion.hit.weight < ordinary)

    if preference == OFF:
        return Decision(occasion, False, "notifications are off")

    # Emptiness first. See the docstring: a silence caused by an empty sky was
    # being reported as a silence caused by the gap.
    if occasion is None:
        if repeated:
            return Decision(
                None,
                False,
                f"the only thing today was already sent inside "
                f"{RECENT_KERNEL_DAYS} days",
            )
        return Decision(None, False, "nothing in this chart clears the floor today")

    if is_quiet(hour):
        # Dropped, not deferred (§3.5). A daily is about a day; one that
        # arrives at 02:00 to describe yesterday is worse than one that never
        # arrives, and silence is already a supported state of this feature.
        return Decision(occasion, False, f"{hour:02d}:00 is inside quiet hours")

    # The gap and both caps, from `rules.py` rather than from a second copy
    # here. This is also what absorbs the travel double-send for free: somebody
    # who flies east across enough zones can meet 08:00 twice in 30 hours, and
    # the gap catches it without a special case (§3.5).
    blocked = rules.too_soon(on, past)
    if blocked:
        return Decision(occasion, False, blocked)

    return Decision(occasion, True, "valve" if occasion.valve else "clears the floor")
