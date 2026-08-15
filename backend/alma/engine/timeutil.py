"""Civil time → astronomical time.

Birth data arrives as a wall-clock time in some place on some date. Turning
that into a instant on the astronomical timescale is where historical
timezones bite: the same wall clock means different UTC depending on which
DST rules and which standard offset were in force *at that date*, and those
rules changed. `zoneinfo` carries the IANA tz database, which encodes the
history, so we resolve the offset at the birth instant rather than today's.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class AmbiguousLocalTime(Exception):
    """The wall clock is ambiguous or does not exist (a DST transition).

    Carries both candidate instants so the caller can decide rather than
    having a guess silently baked into a chart.

    It also carries what the *question* needs, not only what the calculation
    needs. Asking "which 02:30 is yours?" is unanswerable without the two
    names the clock had that night — CEST and CET — and the date it changed;
    a fork offering two identical-looking times is a coin flip with extra
    steps. Those come from the zone at each instant, so this is the one place
    that can state them, and stating them here keeps `zoneinfo` out of the
    clients.
    """

    def __init__(
        self,
        message: str,
        *,
        earlier: datetime,
        later: datetime,
        tz_name: str = "",
        earlier_abbr: str = "",
        later_abbr: str = "",
        earlier_offset_hours: float = 0.0,
        later_offset_hours: float = 0.0,
        transition_local_date: str = "",
    ) -> None:
        super().__init__(message)
        self.earlier = earlier
        self.later = later
        self.tz_name = tz_name
        self.earlier_abbr = earlier_abbr
        self.later_abbr = later_abbr
        self.earlier_offset_hours = earlier_offset_hours
        self.later_offset_hours = later_offset_hours
        self.transition_local_date = transition_local_date


@dataclass(frozen=True, slots=True)
class BirthMoment:
    """A birth instant, resolved and self-describing.

    `time_known` is carried all the way through the engine: without it the
    houses, the angles, the solar return and the map are refused rather than
    computed from an assumed noon.
    """

    utc: datetime
    tz_name: str
    utc_offset_hours: float
    time_known: bool
    dst_active: bool
    # Set when the wall clock fell in a DST gap/overlap and we resolved it.
    tz_note: str | None = None

    @property
    def julian_day_utc(self) -> float:
        """Julian Day number for the UTC instant (the engine's own clock)."""
        return _julian_day(self.utc)


def resolve(
    *,
    year: int,
    month: int,
    day: int,
    hour: int | None,
    minute: int | None,
    tz_name: str,
    on_ambiguous: str = "raise",
) -> BirthMoment:
    """Resolve a wall-clock birth time in `tz_name` to a UTC instant.

    `hour`/`minute` of None means the time is unknown. We anchor those charts
    at 12:00 local — the choice that minimises the error on the Moon and on
    the day's sign boundaries — but flag `time_known=False` so every
    time-dependent block downstream refuses to render rather than pretending.

    `on_ambiguous` controls DST edges: "raise" surfaces the ambiguity to the
    caller (the honest default), "earlier"/"later" pick a fold deliberately.
    """
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:  # pragma: no cover - bad input
        raise ValueError(f"unknown timezone: {tz_name}") from exc

    time_known = hour is not None and minute is not None
    h = 12 if hour is None else hour
    m = 0 if minute is None else minute

    naive = datetime(year, month, day, h, m)
    earlier = naive.replace(tzinfo=tz, fold=0)
    later = naive.replace(tzinfo=tz, fold=1)
    note: str | None = None

    # A wall clock that maps to two different UTC instants sits in the
    # autumn overlap; one that maps to none sits in the spring gap.
    ambiguous = earlier.utcoffset() != later.utcoffset()
    if ambiguous and time_known:
        if on_ambiguous == "raise":
            raise AmbiguousLocalTime(
                f"{naive.isoformat()} is ambiguous in {tz_name} "
                "(daylight-saving transition) — ask which one",
                earlier=earlier.astimezone(timezone.utc),
                later=later.astimezone(timezone.utc),
                tz_name=tz_name,
                earlier_abbr=earlier.tzname() or "",
                later_abbr=later.tzname() or "",
                earlier_offset_hours=_hours(earlier.utcoffset()),
                later_offset_hours=_hours(later.utcoffset()),
                transition_local_date=_transition_date(earlier, later),
            )
        chosen = later if on_ambiguous == "later" else earlier
        note = f"daylight-saving transition; resolved to the {on_ambiguous} instant"
    else:
        chosen = earlier

    utc = chosen.astimezone(timezone.utc)
    offset = chosen.utcoffset()
    dst = chosen.dst()
    return BirthMoment(
        utc=utc,
        tz_name=tz_name,
        utc_offset_hours=(offset.total_seconds() / 3600.0) if offset else 0.0,
        time_known=time_known,
        dst_active=bool(dst and dst.total_seconds()),
        tz_note=note,
    )


def _hours(delta: timedelta | None) -> float:
    return delta.total_seconds() / 3600.0 if delta else 0.0


def _transition_date(earlier: datetime, later: datetime) -> str:
    """The date of the changed clock at the transition, `YYYY-MM-DD`.

    **Read by the *new* offset — the person's own night, not the decree's.**
    Where the clock goes back at two or three in the morning, as it does
    almost everywhere, both readings give the same day and the choice never
    shows. Brazil switched at midnight: on 2015-02-22 00:00 −02 the clock
    became 2015-02-21 23:00 −03, so the repeated hour belongs to the 21st
    while the official date of the change is the 22nd. Somebody born at 23:30
    that night lived through the 21st, and «clocks were set back on the 22nd»
    would send them looking for a different night than the one they are being
    asked about.

    The remaining crack is an overlap that itself crosses midnight — a
    transition at 00:30 repeats 23:30…00:30 — where a birth after midnight
    gets the day before it. It stays: the alternative pins the sentence to the
    birth date and loses Brazil, which is the case that actually occurs.

    `zoneinfo` publishes no list of transitions, so the instant is found by
    walking the gap between the two candidates. It is at most a couple of
    hours wide and transitions land on whole minutes, so a minute-wide step
    finds it exactly.
    """
    target = later.utcoffset()
    step = timedelta(minutes=1)
    at = earlier.astimezone(timezone.utc)
    end = later.astimezone(timezone.utc)
    zone = later.tzinfo
    while at <= end:
        if at.astimezone(zone).utcoffset() == target:
            return at.astimezone(zone).date().isoformat()
        at += step
    # Недостижимо: обе точки на то и разные, что смещение между ними меняется.
    # Но соврать датой хуже, чем промолчать, — поэтому пустая строка, и экран
    # покажет вопрос без неё.
    return ""


def _julian_day(dt: datetime) -> float:
    """Julian Day from a UTC datetime (Gregorian calendar, Meeus ch. 7)."""
    dt = dt.astimezone(timezone.utc)
    y, mo = dt.year, dt.month
    d = (
        dt.day
        + (dt.hour + dt.minute / 60.0 + (dt.second + dt.microsecond / 1e6) / 3600.0) / 24.0
    )
    if mo <= 2:
        y -= 1
        mo += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (mo + 1)) + d + b - 1524.5
