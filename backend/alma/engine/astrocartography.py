"""Astrocartography — the same birth moment, read at every place on Earth.

The birth instant fixes each body's right ascension and declination. What
changes with place is only the local sidereal time, so "where was Venus
rising when I was born?" has an exact answer: the set of longitudes where the
local hour angle puts Venus on the horizon.

Four lines per body:

* **MC** — the meridian passes through the body: hour angle zero.
* **IC** — the opposite meridian: hour angle 180°.
* **ASC / DESC** — the body sits on the horizon: cos H = −tan φ · tan δ.

The MC and IC lines are meridians, so they are straight and defined at every
latitude. The ASC and DESC lines are curves, and they simply stop where the
body becomes circumpolar — above that latitude it never rises or never sets,
and there is no line to draw. Drawing one anyway is the standard way these
maps go wrong.

*Parans* are the other half: latitudes where two bodies are angular at the
same moment. They are points on the map rather than lines, and they are where
a chart's contradictions become geographic.

One thing worth stating plainly, because it looks like a bug and is not: a
body standing on its own MC line does **not** put its ecliptic longitude on
the chart's Midheaven. The Midheaven is where the meridian cuts the *ecliptic*;
the MC line is where the meridian cuts the *body*. Those coincide only for a
body with no ecliptic latitude — the Sun, essentially. For the Moon they can
differ by several degrees. Astrocartography asks where a planet was actually
overhead or actually rising, so these lines are built from right ascension and
declination and never from longitude.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import erfa

from . import ephemeris, zodiac
from .natal import NatalChart

ANGLES: tuple[str, ...] = ("MC", "IC", "ASC", "DESC")

#: Latitude range worth drawing. Beyond ±66° the ASC/DESC lines are mostly
#: undefined and the inhabited land is negligible.
LATITUDE_LIMIT = 66.0
LATITUDE_STEP = 2.0

#: Which bodies get lines. The nodes and Lilith have no declination in the
#: physical sense we need here — they are points on the ecliptic, not objects
#: — so they are left out rather than faked.
LINE_BODIES: tuple[str, ...] = (
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto", "chiron",
)

#: Distance in degrees of longitude within which a line is "over" a place.
#: 5° is roughly 550 km at the equator — the orb the tradition uses.
INFLUENCE_ORB = 5.0


@dataclass(frozen=True, slots=True)
class Line:
    """One planetary line: a body on one angle, drawn as (lat, lon) points."""

    body: str
    angle: str
    points: tuple[tuple[float, float], ...]   # (latitude, longitude east)
    meridian: float | None                    # set for MC/IC, which are straight

    def describe(self) -> str:
        return f"{self.body} {self.angle} line"


@dataclass(frozen=True, slots=True)
class Paran:
    """A latitude where two bodies are angular at the same moment."""

    first: str
    first_angle: str
    second: str
    second_angle: str
    latitude: float

    def describe(self) -> str:
        return (
            f"{self.first} {self.first_angle} crosses {self.second} "
            f"{self.second_angle} at latitude {self.latitude:.1f}°"
        )


@dataclass(frozen=True, slots=True)
class PlaceReading:
    """What the map says about one specific place."""

    latitude: float
    longitude: float
    influences: tuple[tuple[str, str, float], ...]   # body, angle, degrees away

    def describe(self) -> str:
        if not self.influences:
            return "no planetary line runs within orb of this place"
        return "; ".join(
            f"{body} {angle} line {distance:.1f}° away" for body, angle, distance in self.influences
        )


@dataclass(frozen=True, slots=True)
class AstroMap:
    lines: tuple[Line, ...]
    parans: tuple[Paran, ...]
    birthplace: PlaceReading
    unavailable: tuple[str, ...] = ()

    def factors(self) -> list[str]:
        items = [line.describe() for line in self.lines]
        items += [paran.describe() for paran in self.parans]
        items.append(f"at the birthplace: {self.birthplace.describe()}")
        return items

    def read_place(self, latitude: float, longitude: float) -> PlaceReading:
        return _read_place(self.lines, latitude, longitude)


def _equatorial(body: str, jd_utc: float) -> tuple[float, float]:
    """Apparent right ascension and declination of date, in degrees.

    The lines are a question about the *sky*, not about the ecliptic, so this
    goes back to the equatorial coordinates rather than converting a longitude
    — a body's ecliptic latitude is exactly what would be lost.
    """
    eph, _ts, _ = ephemeris._loaded()
    t = ephemeris._skyfield_time(jd_utc)
    ra, dec, _ = eph["earth"].at(t).observe(ephemeris._resolve(body)).apparent().radec(
        epoch="date"
    )
    return float(ra._degrees), float(dec.degrees)


def greenwich_sidereal(jd_utc: float) -> float:
    """Greenwich apparent sidereal time in degrees at the birth instant."""
    t = ephemeris._skyfield_time(jd_utc)
    return math.degrees(erfa.gst06a(jd_utc, 0.0, t.tt, 0.0)) % 360.0


def _normalise_longitude(degrees: float) -> float:
    return ((degrees + 180.0) % 360.0) - 180.0


def _hour_angle_at_horizon(declination: float, latitude: float) -> float | None:
    """The hour angle at which a body of this declination touches the horizon.

    None when the body is circumpolar at this latitude: it either never sets
    or never rises, and there is no rising line to draw. This is where naive
    implementations quietly clamp the arccosine and produce a line along the
    polar circle that means nothing.
    """
    value = -math.tan(math.radians(latitude)) * math.tan(math.radians(declination))
    if abs(value) > 1.0:
        return None
    return math.degrees(math.acos(value))


def lines_for(body: str, jd_utc: float) -> list[Line]:
    """The four lines for one body."""
    ra, dec = _equatorial(body, jd_utc)
    gst = greenwich_sidereal(jd_utc)

    # Local hour angle H = LST − RA and LST = GST + λ, so λ = H + RA − GST.
    mc = _normalise_longitude(ra - gst)
    ic = _normalise_longitude(ra + 180.0 - gst)

    latitudes = [
        -LATITUDE_LIMIT + i * LATITUDE_STEP
        for i in range(int(2 * LATITUDE_LIMIT / LATITUDE_STEP) + 1)
    ]
    result = [
        Line(body, "MC", tuple((lat, mc) for lat in latitudes), mc),
        Line(body, "IC", tuple((lat, ic) for lat in latitudes), ic),
    ]

    rising: list[tuple[float, float]] = []
    setting: list[tuple[float, float]] = []
    for latitude in latitudes:
        hour_angle = _hour_angle_at_horizon(dec, latitude)
        if hour_angle is None:
            continue
        rising.append((latitude, _normalise_longitude(ra - hour_angle - gst)))
        setting.append((latitude, _normalise_longitude(ra + hour_angle - gst)))

    result.append(Line(body, "ASC", tuple(rising), None))
    result.append(Line(body, "DESC", tuple(setting), None))
    return result


def _longitude_at(line: Line, latitude: float) -> float | None:
    """Where a line crosses a given latitude, interpolating between points."""
    if line.meridian is not None:
        return line.meridian
    points = line.points
    if not points:
        return None
    for (lat_a, lon_a), (lat_b, lon_b) in zip(points, points[1:]):
        if min(lat_a, lat_b) <= latitude <= max(lat_a, lat_b):
            if lat_b == lat_a:
                return lon_a
            fraction = (latitude - lat_a) / (lat_b - lat_a)
            step = _normalise_longitude(lon_b - lon_a)
            return _normalise_longitude(lon_a + fraction * step)
    return None


def _read_place(lines: tuple[Line, ...], latitude: float, longitude: float) -> PlaceReading:
    influences: list[tuple[str, str, float]] = []
    for line in lines:
        crossing = _longitude_at(line, latitude)
        if crossing is None:
            continue
        distance = abs(_normalise_longitude(crossing - longitude))
        if distance <= INFLUENCE_ORB:
            influences.append((line.body, line.angle, round(distance, 2)))
    influences.sort(key=lambda item: item[2])
    return PlaceReading(latitude, longitude, tuple(influences))


def parans(lines: tuple[Line, ...], *, orb_minutes: float = 30.0) -> list[Paran]:
    """Latitudes where two bodies are angular within the same few minutes.

    Two lines crossing on the map is not a paran — that would only mean they
    share a place, not a moment. A paran is a coincidence in *time*: both
    bodies angular within the same short window, which happens along a whole
    latitude regardless of longitude.
    """
    tolerance = orb_minutes / 60.0 * 15.0  # minutes of time → degrees
    found: list[Paran] = []

    latitudes = [-LATITUDE_LIMIT + i * 1.0 for i in range(int(2 * LATITUDE_LIMIT) + 1)]
    for i, first in enumerate(lines):
        for second in lines[i + 1 :]:
            if first.body == second.body:
                continue
            for latitude in latitudes:
                a = _longitude_at(first, latitude)
                b = _longitude_at(second, latitude)
                if a is None or b is None:
                    continue
                if abs(_normalise_longitude(a - b)) <= tolerance:
                    found.append(
                        Paran(first.body, first.angle, second.body, second.angle, latitude)
                    )
                    break
    return found


def compute(
    chart: NatalChart,
    *,
    bodies: tuple[str, ...] | None = None,
    include_parans: bool = True,
) -> AstroMap:
    """The whole map for one birth.

    Refused without a birth time, and for the same reason the solar return is:
    the lines are meridians of local sidereal time, which advances a full
    degree every four minutes. An assumed noon puts every line up to 180° from
    where it belongs — a different continent, confidently drawn.
    """
    if not chart.time_known:
        raise ValueError(
            "astrocartography needs a real birth time: sidereal time moves a "
            "degree every four minutes, so an assumed noon misplaces every "
            "line by up to half the globe"
        )

    jd = chart.julian_day
    wanted = bodies or LINE_BODIES
    unavailable: list[str] = []

    drawn: list[Line] = []
    for body in wanted:
        if body == "chiron" and not ephemeris.chiron_available(jd):
            unavailable.append("chiron lines: outside the tabulated range")
            continue
        drawn.extend(lines_for(body, jd))

    all_lines = tuple(drawn)
    return AstroMap(
        lines=all_lines,
        parans=tuple(parans(all_lines)) if include_parans else (),
        birthplace=_read_place(all_lines, chart.latitude, chart.longitude),
        unavailable=tuple(unavailable),
    )


def relocated_angles(chart: NatalChart, latitude: float, longitude: float) -> dict:
    """The Ascendant and Midheaven the birth moment would have had elsewhere.

    This is what a relocation reading rests on. Note that it answers a
    different question from the lines above: these are ecliptic points, and a
    body sitting on its own MC line will only match this Midheaven if it has
    no ecliptic latitude.
    """
    from .houses import angles as compute_angles

    t = ephemeris._skyfield_time(chart.julian_day)
    ang = compute_angles(chart.julian_day, t.tt, latitude, longitude)
    return {
        "ascendant": ang.ascendant,
        "midheaven": ang.midheaven,
        "descendant": ang.descendant,
        "imum_coeli": ang.imum_coeli,
        "ascendant_sign": zodiac.sign_of(ang.ascendant),
        "midheaven_sign": zodiac.sign_of(ang.midheaven),
    }
