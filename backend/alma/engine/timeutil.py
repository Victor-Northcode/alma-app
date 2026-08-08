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
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class AmbiguousLocalTime(Exception):
    """The wall clock is ambiguous or does not exist (a DST transition).

    Carries both candidate instants so the caller can decide rather than
    having a guess silently baked into a chart.
    """

    def __init__(self, message: str, *, earlier: datetime, later: datetime) -> None:
        super().__init__(message)
        self.earlier = earlier
        self.later = later


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
