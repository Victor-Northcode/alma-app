"""Which clock the reader is actually looking at.

The engine speaks Julian Day and the reader does not. Every date this package
decides — is this event today, does the send instant fall inside quiet hours,
which day does a stored piece belong to — is a date *in the reader's own zone*,
and getting that wrong is not a rounding error. A transit that perfects at
23:40 UTC on the 6th perfects at 08:40 on the 7th in Tokyo and at 18:40 on the
6th in New York. Filing it under the UTC date would tell a Tokyo reader on the
7th that nothing is happening today, on the morning it happens.

**`Profile.timezone` is the birth timezone, not the reader's.** That is the
trap this module exists to make hard to fall into, and it is why `zone_for`
takes a ladder rather than a string. `docs/THE-DAILY.md §3.1` puts it plainly:
a person born in Auckland who now lives in Berlin has `Profile.timezone ==
"Pacific/Auckland"` and no part of the system knows they moved. Using it as the
delivery clock sends a good-morning piece at 20:00.

The device zone that fixes this does not arrive yet — it needs the
`X-Alma-Timezone` header contracted from `alma/api/deps.py`, which another
workflow owns. So the ladder is written now, with the top rung empty, rather
than written later once every caller has already reached for `profile.timezone`
directly.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

#: J2000.0 — the epoch `_julian_day` is anchored on, as a UTC instant.
J2000_JD = 2451545.0
J2000 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)

#: Where the ladder ends. Deliberately UTC and deliberately unreachable in
#: practice — `Profile.timezone` is NOT NULL, so rung three always resolves.
#: Reaching this is a bug worth logging rather than a case worth designing for
#: (`THE-DAILY.md §3.3`), which is why `zone_for` returns the rung it used.
LAST_RESORT = "UTC"


def from_jd(jd: float) -> datetime:
    """A Julian Day as an aware UTC instant.

    The inverse of `engine.timeutil._julian_day`, and written as an offset from
    J2000 rather than by re-deriving the calendar: the round trip through the
    Meeus formulae loses seconds to floating point, and this package compares
    instants against an 08:00 boundary.
    """
    return J2000 + timedelta(days=jd - J2000_JD)


def to_jd(moment: datetime) -> float:
    from ..engine.timeutil import _julian_day

    return _julian_day(moment)


def known(name: str | None) -> bool:
    """Whether this is a zone identifier the machine can actually resolve.

    Not `geo.is_known_timezone` — that module belongs to another workflow and
    answers a different question (is this a zone we will accept from a client).
    This one asks whether `ZoneInfo` will hand back a rule set, which is what
    every conversion below depends on, and it has to stay answerable without
    importing a file this package is not allowed to touch.
    """
    if not name:
        return False
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def zone_for(
    *,
    device: str | None = None,
    chosen: str | None = None,
    birth: str | None = None,
) -> tuple[ZoneInfo, str]:
    """The reader's clock, and which rung of the ladder produced it.

    `THE-DAILY.md §3.3`, in order: the timezone this installation last
    reported, the one the person picked in settings, the birth timezone, and
    then UTC. First one that *resolves* wins — a rung holding a zone this
    machine has never heard of is skipped rather than fatal, because a stale
    `tzdata` should degrade the send hour, not stop the job.

    The source is returned because the settings screen shows it. "Warsaw — from
    your device" versus "Auckland — from your birth data" is what makes the
    override discoverable to the one person who needs it: somebody who moved
    and whose notifications are landing at the wrong hour will look here first.

    It is a ladder and not a merge. Never average two zones, and never guess
    one from the country — `region.py`'s coarse country is right for Poland and
    useless for the United States, Brazil, Russia, Canada and Australia, four
    of which are inside our six-language footprint.
    """
    for name, source in ((device, "device"), (chosen, "chosen"), (birth, "birth")):
        if known(name):
            return ZoneInfo(name), source          # type: ignore[arg-type]
    return ZoneInfo(LAST_RESORT), "fallback"


def local(jd: float, zone: ZoneInfo) -> datetime:
    """One instant, in the reader's clock."""
    return from_jd(jd).astimezone(zone)


def local_date(jd: float, zone: ZoneInfo) -> date:
    return local(jd, zone).date()


def day_bounds(on: date, zone: ZoneInfo) -> tuple[float, float]:
    """The Julian Days that bracket one local calendar day.

    Built from midnight to midnight in the reader's zone rather than by adding
    1.0 to a Julian Day, because a local day is 23 or 25 hours long twice a
    year and the transit that perfects in the missing hour is not less real for
    it.
    """
    start = datetime.combine(on, datetime.min.time(), tzinfo=zone)
    end = datetime.combine(on + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    return to_jd(start), to_jd(end)


def format_time(moment: datetime) -> str:
    """The instant as the notification prints it: 24-hour, zero-padded.

    24-hour in all six languages, including English. The alternative is a
    12-hour clock for some readers, and choosing that needs a *region* — the
    difference is en-US against en-GB, and every locale we hold is a language.
    Guessing it from the timezone would be a second guess layered on the ladder
    above. So the composed line is 24-hour everywhere, and every payload also
    carries the ISO instant (`Notification.at`) so a client that knows the
    device's real locale can print 2:20 PM instead. The server should not be
    the thing deciding that.
    """
    return moment.strftime("%H:%M")
