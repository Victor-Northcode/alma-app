"""Body positions, from a permissive stack only.

Skyfield (MIT) reads NASA's DE kernels through jplephem (MIT); pyerfa
(BSD-3-Clause) supplies the IAU 2006/2000A precession-nutation and obliquity.
Nothing here is derived from Swiss Ephemeris or any AGPL source.

Astrology reads *apparent geocentric ecliptic longitude referred to the true
equinox of date*. Getting there is a two-step: ask Skyfield for the apparent
right ascension and declination of date (light-time, aberration, precession
and nutation applied), then rotate equator → ecliptic with the true obliquity.
Handing already-precessed coordinates to a routine that precesses again is the
classic way to be wrong by a smooth ~50 arcsec per year from J2000, which
looks plausible and is not.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import erfa
from skyfield.api import load, load_file

from .smallbody import chiron_body

# Ecliptic longitude only ever means "of date" in this engine.
_DEG = 180.0 / math.pi

#: Bodies the natal chart needs, mapped to their SPK targets.
BODY_TARGETS: dict[str, str] = {
    "sun": "sun",
    "moon": "moon",
    "mercury": "mercury",
    "venus": "venus",
    "mars": "mars barycenter",
    "jupiter": "jupiter barycenter",
    "saturn": "saturn barycenter",
    "uranus": "uranus barycenter",
    "neptune": "neptune barycenter",
    "pluto": "pluto barycenter",
}

PLANETS: tuple[str, ...] = tuple(BODY_TARGETS)

#: Chiron is a centaur, not a planet, so it is absent from DE440s. It comes
#: from a sampled JPL Horizons table instead — see `smallbody.py`.
CHIRON_JD_START = 2415020.5   # 1900-01-01
CHIRON_JD_END = 2488068.5     # 2099-12-29


@dataclass(frozen=True, slots=True)
class Position:
    """One body at one instant, in the frame astrology actually uses."""

    body: str
    longitude: float       # degrees, tropical, true equinox of date
    latitude: float        # degrees, ecliptic
    distance_au: float
    speed_longitude: float  # degrees/day; negative means retrograde
    retrograde: bool


def _kernel_path() -> Path:
    """DE440s if we have it, else the DE421 that ships offline.

    DE440 is what the spec names; DE421 is bundled with skyfield-data and
    keeps local development and CI working with no network. Both are NASA
    public data; the difference across 1900–2050 is far below our tolerance.
    """
    explicit = os.environ.get("ALMA_EPHEMERIS_KERNEL")
    if explicit:
        return Path(explicit)

    local = Path(__file__).resolve().parents[2] / "data" / "de440s.bsp"
    if local.exists():
        return local

    from skyfield_data import get_skyfield_data_path

    return Path(get_skyfield_data_path()) / "de421.bsp"


@lru_cache(maxsize=1)
def _loaded():
    kernel = _kernel_path()
    eph = load_file(str(kernel))
    ts = load.timescale(builtin=True)
    return eph, ts, kernel.name


def kernel_name() -> str:
    """Which ephemeris actually answered — recorded in every CalcResult."""
    return _loaded()[2]


def chiron_available(jd_utc: float) -> bool:
    """Whether Chiron can be answered for this date, table and range both."""
    body = chiron_body()
    # Leave a day of slack at each end so the speed's ±30-minute samples stay
    # inside the table.
    return body is not None and CHIRON_JD_START + 1 <= jd_utc <= CHIRON_JD_END - 1


def true_obliquity(tt: float) -> float:
    """True obliquity of the ecliptic, radians (IAU 2006 + 2000A nutation)."""
    mean = erfa.obl06(tt, 0.0)
    _dpsi, deps = erfa.nut06a(tt, 0.0)
    return mean + deps


def equatorial_to_ecliptic(ra: float, dec: float, obliquity: float) -> tuple[float, float]:
    """Rotate equatorial → ecliptic about the same equinox. Radians in and out."""
    sin_e, cos_e = math.sin(obliquity), math.cos(obliquity)
    lon = math.atan2(
        math.sin(ra) * cos_e + math.tan(dec) * sin_e,
        math.cos(ra),
    )
    lat = math.asin(math.sin(dec) * cos_e - math.cos(dec) * sin_e * math.sin(ra))
    return lon, lat


def _skyfield_time(jd_utc: float):
    _eph, ts, _ = _loaded()
    return ts.ut1_jd(jd_utc)


def _resolve(body: str):
    """The Skyfield vector function for a body name, Chiron included."""
    if body == "chiron":
        target = chiron_body()
        if target is None:
            raise LookupError("the Chiron table is not installed")
        return target
    eph, _ts, _ = _loaded()
    return eph[BODY_TARGETS[body]]


def position(body: str, jd_utc: float) -> Position:
    """Apparent geocentric position of one body."""
    eph, _ts, _ = _loaded()
    target = _resolve(body)
    t = _skyfield_time(jd_utc)
    earth = eph["earth"]

    ra, dec, dist = earth.at(t).observe(target).apparent().radec(epoch="date")
    eps = true_obliquity(t.tt)
    lon, lat = equatorial_to_ecliptic(ra.radians, dec.radians, eps)

    # Speed by symmetric difference: a body's daily motion is smooth over an
    # hour, and this keeps one code path for every body including the Moon.
    step = 1.0 / 48.0
    lon_before = _longitude_only(target, jd_utc - step)
    lon_after = _longitude_only(target, jd_utc + step)
    delta = (lon_after - lon_before + 540.0) % 360.0 - 180.0
    speed = delta / (2.0 * step)

    # Cast out of numpy: these values are serialised into CalcResult, and a
    # numpy scalar is not JSON-encodable.
    return Position(
        body=body,
        longitude=float(math.degrees(lon) % 360.0),
        latitude=float(math.degrees(lat)),
        distance_au=float(dist.au),
        speed_longitude=float(speed),
        retrograde=bool(speed < 0.0),
    )


def _longitude_only(target, jd_utc: float) -> float:
    eph, _ts, _ = _loaded()
    t = _skyfield_time(jd_utc)
    ra, dec, _ = eph["earth"].at(t).observe(target).apparent().radec(epoch="date")
    lon, _lat = equatorial_to_ecliptic(ra.radians, dec.radians, true_obliquity(t.tt))
    return math.degrees(lon) % 360.0


def chiron(jd_utc: float) -> Position | None:
    """Chiron, or None when the kernel is missing or the date is out of range."""
    if not chiron_available(jd_utc):
        return None
    return position("chiron", jd_utc)


def positions(jd_utc: float, bodies: tuple[str, ...] = PLANETS) -> dict[str, Position]:
    return {b: position(b, jd_utc) for b in bodies}


def longitudes(body: str, jd_array) -> "np.ndarray":
    """Ecliptic longitude of one body at many instants, in one pass.

    Transit hunting evaluates the same body at thousands of times, and
    Skyfield's per-call overhead — the light-time iteration especially —
    dominates when it is paid once per instant. Handing it the whole array
    turns an afternoon into a second, and the arithmetic is identical to
    `position()`: same apparent place, same true obliquity, same rotation.
    """
    import numpy as np

    eph, ts, _ = _loaded()
    jd = np.atleast_1d(np.asarray(jd_array, dtype=np.float64))
    t = ts.ut1_jd(jd)
    ra, dec, _dist = eph["earth"].at(t).observe(_resolve(body)).apparent().radec(epoch="date")

    mean = erfa.obl06(t.tt, 0.0)
    _dpsi, deps = erfa.nut06a(t.tt, 0.0)
    eps = mean + deps

    sin_e, cos_e = np.sin(eps), np.cos(eps)
    ra_rad, dec_rad = ra.radians, dec.radians
    lon = np.arctan2(
        np.sin(ra_rad) * cos_e + np.tan(dec_rad) * sin_e,
        np.cos(ra_rad),
    )
    return np.degrees(lon) % 360.0


def lunar_node(jd_utc: float, *, true_node: bool = True) -> Position:
    """The Moon's ascending node.

    The mean node is a polynomial in time (Meeus ch. 47). The true node
    oscillates about it by up to ~1.6°; we derive it from the Moon's own
    orbital plane rather than importing a table, which keeps the node
    consistent with the Moon we actually computed.
    """
    t = _skyfield_time(jd_utc)
    centuries = (t.tt - 2451545.0) / 36525.0
    mean = (
        125.0445479
        - 1934.1362891 * centuries
        + 0.0020754 * centuries**2
        + centuries**3 / 467441.0
        - centuries**4 / 60616000.0
    )
    if not true_node:
        speed = -1934.1362891 / 36525.0
        return Position("mean_node", float(mean % 360.0), 0.0, 0.0, speed, True)

    lon = _true_node_longitude(jd_utc, mean)
    step = 1.0 / 24.0
    before = _true_node_longitude(jd_utc - step, mean)
    after = _true_node_longitude(jd_utc + step, mean)
    delta = (after - before + 540.0) % 360.0 - 180.0
    return Position(
        "true_node", float(lon % 360.0), 0.0, 0.0, float(delta / (2 * step)), bool(delta < 0)
    )


def _true_node_longitude(jd_utc: float, mean_hint: float) -> float:
    """Where the Moon's instantaneous orbital plane crosses the ecliptic.

    The node is the line of intersection of the Moon's orbital plane with the
    ecliptic, so it is the cross product of the ecliptic pole and the Moon's
    orbital angular momentum — computed from the Moon's position and velocity.
    """
    eph, _ts, _ = _loaded()
    t = _skyfield_time(jd_utc)
    geocentric = eph["moon"].at(t) - eph["earth"].at(t)
    r = geocentric.position.au
    v = geocentric.velocity.au_per_d

    # Geometric position and velocity — no light-time or aberration. The
    # osculating plane is a dynamical property of the orbit, not of how we
    # happen to see it.
    hx = r[1] * v[2] - r[2] * v[1]
    hy = r[2] * v[0] - r[0] * v[2]
    hz = r[0] * v[1] - r[1] * v[0]

    # Skyfield hands back ICRS (J2000-aligned) vectors. Rotating those with
    # the obliquity *of date* silently mixes two frames and lands the node
    # about a precession-worth off — smooth, plausible, and wrong. Carry the
    # momentum vector to the true equator and equinox of date first.
    npb = erfa.pnm06a(t.tt, 0.0)
    hx, hy, hz = (
        npb[0][0] * hx + npb[0][1] * hy + npb[0][2] * hz,
        npb[1][0] * hx + npb[1][1] * hy + npb[1][2] * hz,
        npb[2][0] * hx + npb[2][1] * hy + npb[2][2] * hz,
    )

    eps = true_obliquity(t.tt)
    cos_e, sin_e = math.cos(eps), math.sin(eps)
    hy_ecl = hy * cos_e + hz * sin_e
    hz_ecl = -hy * sin_e + hz * cos_e

    # Ascending node is 90° behind the projection of the momentum vector.
    node = math.degrees(math.atan2(hx, -hy_ecl)) % 360.0
    # Keep the branch nearest the mean node; the two differ by at most ~1.6°.
    while node - mean_hint % 360.0 > 180.0:
        node -= 360.0
    while mean_hint % 360.0 - node > 180.0:
        node += 360.0
    return node % 360.0


def lilith(jd_utc: float) -> Position:
    """Mean lunar apogee — 'Black Moon Lilith' (Meeus ch. 47)."""
    t = _skyfield_time(jd_utc)
    centuries = (t.tt - 2451545.0) / 36525.0
    # Mean longitude of perigee; apogee is 180° away.
    perigee = (
        83.3532465
        + 4069.0137287 * centuries
        - 0.0103200 * centuries**2
        - centuries**3 / 80053.0
        + centuries**4 / 18999000.0
    )
    speed = 4069.0137287 / 36525.0
    return Position("lilith", float((perigee + 180.0) % 360.0), 0.0, 0.0, speed, False)
