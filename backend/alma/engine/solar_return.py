"""The solar return — the chart for the moment the Sun comes back.

Once a year the Sun reaches the exact ecliptic longitude it held at birth,
and the chart cast for that instant is read as the shape of the year that
follows. The instant is a root, not a date: the Sun's return misses midnight
by hours, and those hours decide the return Ascendant, which is most of what
the reading is about.

That sensitivity is also why the return is refused without a birth time. An
unknown time leaves the natal Sun uncertain by about a quarter of a degree,
which moves the return by six hours, which moves the return Ascendant by
ninety degrees. A return chart built on an assumed noon is not a weaker
answer — it is a different person's year.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np

from . import ephemeris, zodiac
from .natal import NatalChart, compute as compute_natal
from .timeutil import BirthMoment

#: The Sun moves about a degree a day, so the return is always within a day
#: or two of the birthday; a five-day bracket is generous and cheap.
SEARCH_RADIUS_DAYS = 5.0


class BirthTimeRequired(Exception):
    """The solar return is meaningless without a real birth time."""


@dataclass(frozen=True, slots=True)
class SolarReturn:
    """One year, as the returning Sun draws it."""

    year: int
    return_jd: float
    return_utc: datetime
    natal_sun: float
    chart: NatalChart
    latitude: float
    longitude: float
    relocated: bool
    year_ruler: str | None
    angular_bodies: tuple[str, ...]
    natal_contacts: tuple[str, ...]

    def factors(self) -> list[str]:
        items = [
            f"solar return {self.year} at {self.return_utc:%Y-%m-%d %H:%M} UTC",
            f"return ascendant {zodiac.format_position(self.chart.angles.ascendant)}",
            f"return midheaven {zodiac.format_position(self.chart.angles.midheaven)}",
        ]
        if self.year_ruler:
            items.append(f"ruler of the year {self.year_ruler}")
        for body in self.angular_bodies:
            items.append(f"{body} is angular in the solar return")
        items += list(self.natal_contacts)
        items += [
            f"return {placement.describe()}"
            for placement in self.chart.placements.values()
        ]
        if self.relocated:
            items.append("the return is cast for where you are, not where you were born")
        return items


def _sun_offset(jd_array, natal_sun: float):
    return (ephemeris.longitudes("sun", jd_array) - natal_sun + 180.0) % 360.0 - 180.0


def return_moment(natal_sun: float, birthday: datetime, year: int) -> float:
    """The Julian day the Sun regains `natal_sun` in the given year.

    Bracketed around the anniversary rather than searched blindly: the Sun
    passes a given degree exactly once a year, so a bracket around the
    birthday contains the one crossing and no other.
    """
    anniversary = birthday.replace(year=year, tzinfo=timezone.utc)
    from .timeutil import _julian_day

    centre = _julian_day(anniversary)
    low, high = centre - SEARCH_RADIUS_DAYS, centre + SEARCH_RADIUS_DAYS

    grid = np.linspace(low, high, 41)
    offsets = _sun_offset(grid, natal_sun)
    # Ignore the wrap: the Sun's offset jumps 360° once per orbit, not here.
    stepped = np.abs(np.diff(offsets)) > 180.0
    crossings = np.flatnonzero(((offsets[:-1] * offsets[1:]) <= 0) & ~stepped)
    if crossings.size == 0:
        raise ValueError(
            f"the Sun does not reach {natal_sun:.4f}° within five days of the "
            f"{year} anniversary — check the natal longitude"
        )

    index = int(crossings[0])
    low, high = float(grid[index]), float(grid[index + 1])
    f_low = float(_sun_offset([low], natal_sun)[0])
    for _ in range(60):
        mid = (low + high) / 2.0
        f_mid = float(_sun_offset([mid], natal_sun)[0])
        if high - low < 1e-7:
            break
        if f_low * f_mid <= 0:
            high = mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2.0


def _angular(chart: NatalChart, orb: float = 8.0) -> tuple[str, ...]:
    """Bodies sitting on an angle — the loudest thing in a return chart."""
    if not chart.angles:
        return ()
    angles = (
        chart.angles.ascendant, chart.angles.midheaven,
        chart.angles.descendant, chart.angles.imum_coeli,
    )
    found = []
    for name, placement in chart.placements.items():
        if any(zodiac.separation(placement.longitude, a) <= orb for a in angles):
            found.append(name)
    return tuple(found)


def _natal_contacts(natal_chart: NatalChart, return_chart: NatalChart) -> tuple[str, ...]:
    """Where the return chart lands on the natal one.

    A return read in isolation floats free of the person; the contacts are
    what tie the year to the life it belongs to.
    """
    contacts: list[str] = []
    natal_points = {n: p.longitude for n, p in natal_chart.placements.items()}
    if natal_chart.angles:
        natal_points["ascendant"] = natal_chart.angles.ascendant
        natal_points["midheaven"] = natal_chart.angles.midheaven

    return_angles = {
        "return ascendant": return_chart.angles.ascendant,
        "return midheaven": return_chart.angles.midheaven,
    }
    for label, angle in return_angles.items():
        for name, longitude in natal_points.items():
            gap = zodiac.separation(angle, longitude)
            if gap <= 3.0:
                contacts.append(f"{label} sits on natal {name} ({gap:.1f}°)")
            elif abs(gap - 180.0) <= 3.0:
                contacts.append(f"{label} opposes natal {name} ({abs(gap - 180.0):.1f}°)")
    return tuple(contacts)


def compute(
    *,
    natal_chart: NatalChart,
    birth_moment: BirthMoment,
    year: int,
    latitude: float | None = None,
    longitude: float | None = None,
    house_system: str = "placidus",
) -> SolarReturn:
    """The solar return for one year, cast where the person will be.

    Passing a latitude and longitude relocates the return, which is the
    orthodox way to read a year spent somewhere other than the birthplace —
    the Sun returns at the same instant everywhere, but the horizon under it
    is different.
    """
    if not natal_chart.time_known:
        raise BirthTimeRequired(
            "a solar return needs a real birth time: an assumed noon moves the "
            "return by six hours and the return ascendant by a whole quadrant"
        )

    natal_sun = natal_chart.placements["sun"].longitude
    jd = return_moment(natal_sun, birth_moment.utc, year)

    place_lat = natal_chart.latitude if latitude is None else latitude
    place_lon = natal_chart.longitude if longitude is None else longitude
    relocated = (place_lat, place_lon) != (natal_chart.latitude, natal_chart.longitude)

    utc = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=jd - 2451545.0)
    moment = BirthMoment(
        utc=utc,
        tz_name=birth_moment.tz_name,
        utc_offset_hours=birth_moment.utc_offset_hours,
        time_known=True,
        dst_active=False,
        tz_note=None,
    )
    chart = compute_natal(
        moment=moment,
        latitude=place_lat,
        longitude=place_lon,
        house_system=house_system,
    )

    ruler = None
    if chart.angles:
        rising = zodiac.sign_of(chart.angles.ascendant)
        traditional, modern = zodiac.SIGN_RULERS[rising]
        ruler = modern or traditional

    return SolarReturn(
        year=year,
        return_jd=jd,
        return_utc=utc,
        natal_sun=natal_sun,
        chart=chart,
        latitude=place_lat,
        longitude=place_lon,
        relocated=relocated,
        year_ruler=ruler,
        angular_bodies=_angular(chart),
        natal_contacts=_natal_contacts(natal_chart, chart),
    )
