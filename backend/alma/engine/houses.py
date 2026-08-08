"""Angles and house cusps, written from the standard formulae.

Placidus is a *time* division, not a space division: a degree of the ecliptic
belongs to the eleventh house when it has completed one third of its journey
from the horizon to the meridian. That definition is the test — `houses.py`
is verified by asserting the trisection property directly, not by matching
another implementation's numbers.

Above the polar circle a degree can fail to rise at all, and Placidus is
simply undefined there. We say so and fall back to Porphyry, recording the
substitution, rather than emitting a cusp that looks like an answer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import erfa

from .ephemeris import true_obliquity

_TAU = 2.0 * math.pi


class PlacidusUndefined(Exception):
    """The requested cusp never rises at this latitude."""


@dataclass(frozen=True, slots=True)
class Angles:
    ascendant: float
    midheaven: float
    descendant: float
    imum_coeli: float
    vertex: float
    ramc: float          # right ascension of the midheaven, degrees
    obliquity: float     # degrees


@dataclass(frozen=True, slots=True)
class Houses:
    cusps: tuple[float, ...]   # 12 cusps, index 0 == house 1
    system: str                # what was actually used
    requested_system: str
    fallback_reason: str | None


def sidereal_time(jd_utc: float, tt: float, longitude_east: float) -> float:
    """Local apparent sidereal time in degrees — the RAMC."""
    gst = erfa.gst06a(jd_utc, 0.0, tt, 0.0)  # radians, Greenwich apparent
    return (math.degrees(gst) + longitude_east) % 360.0


def angles(jd_utc: float, tt: float, latitude: float, longitude_east: float) -> Angles:
    """Ascendant, Midheaven and Vertex from sidereal time and latitude."""
    ramc = sidereal_time(jd_utc, tt, longitude_east)
    eps = true_obliquity(tt)
    ramc_rad = math.radians(ramc)
    lat_rad = math.radians(latitude)

    # MC is where the meridian cuts the ecliptic.
    mc = math.degrees(math.atan2(math.tan(ramc_rad), math.cos(eps))) % 360.0
    # Keep MC in the same half of the sky as the RAMC.
    if abs((mc - ramc + 180.0) % 360.0 - 180.0) > 90.0:
        mc = (mc + 180.0) % 360.0

    # Ascendant: the ecliptic degree rising on the eastern horizon.
    asc = math.degrees(
        math.atan2(
            math.cos(ramc_rad),
            -(math.sin(ramc_rad) * math.cos(eps) + math.tan(lat_rad) * math.sin(eps)),
        )
    ) % 360.0

    # Vertex is the Ascendant of the co-latitude, taken in the west.
    colat = math.radians(90.0 - abs(latitude))
    west = math.radians((ramc + 180.0) % 360.0)
    vertex = math.degrees(
        math.atan2(
            math.cos(west),
            -(math.sin(west) * math.cos(eps) + math.tan(colat) * math.sin(eps)),
        )
    ) % 360.0
    if latitude < 0:
        vertex = (vertex + 180.0) % 360.0

    return Angles(
        ascendant=asc,
        midheaven=mc,
        descendant=(asc + 180.0) % 360.0,
        imum_coeli=(mc + 180.0) % 360.0,
        vertex=vertex,
        ramc=ramc,
        obliquity=math.degrees(eps),
    )


def _ecliptic_longitude_at_ra(ra_deg: float, eps: float) -> float:
    """The ecliptic point sharing this right ascension."""
    ra = math.radians(ra_deg)
    lon = math.degrees(math.atan2(math.sin(ra), math.cos(ra) * math.cos(eps))) % 360.0
    # atan2 collapses two branches; keep the one in the same half as the RA.
    if abs((lon - ra_deg + 180.0) % 360.0 - 180.0) > 90.0:
        lon = (lon + 180.0) % 360.0
    return lon


def _declination_of_ecliptic_point(lon_deg: float, eps: float) -> float:
    return math.asin(math.sin(eps) * math.sin(math.radians(lon_deg)))


def ascensional_difference(declination: float, latitude: float) -> float:
    """How far a body's rising departs from due east, in degrees.

    Undefined when |tan δ · tan φ| > 1 — the circumpolar case, where the
    degree either never rises or never sets.
    """
    value = math.tan(declination) * math.tan(math.radians(latitude))
    if abs(value) > 1.0:
        raise PlacidusUndefined(
            f"declination {math.degrees(declination):.2f}° never rises at latitude {latitude:.2f}°"
        )
    return math.degrees(math.asin(value))


def _placidus_cusp(
    *, ramc: float, latitude: float, eps: float, fraction: float, nocturnal: bool
) -> float:
    """Solve one intermediate Placidus cusp by fixed-point iteration.

    The cusp is the ecliptic degree whose hour angle is `fraction` of its own
    semi-arc. Because the semi-arc depends on the declination, which depends
    on the degree we are solving for, it is solved iteratively — it converges
    in a handful of passes away from the poles.
    """
    # Seed with the equal-arc guess; sign follows the hemisphere we are in.
    offset = fraction * 90.0
    ra = ramc + (180.0 - offset if nocturnal else offset)

    for _ in range(100):
        lon = _ecliptic_longitude_at_ra(ra, eps)
        dec = _declination_of_ecliptic_point(lon, eps)
        ad = ascensional_difference(dec, latitude)
        semi_arc = (90.0 - ad) if nocturnal else (90.0 + ad)
        target = ramc + (180.0 - fraction * semi_arc if nocturnal else fraction * semi_arc)
        if abs((target - ra + 180.0) % 360.0 - 180.0) < 1e-9:
            ra = target
            break
        ra = target

    return _ecliptic_longitude_at_ra(ra % 360.0, eps)


def placidus(ang: Angles, latitude: float) -> tuple[float, ...]:
    """The twelve Placidus cusps. Raises `PlacidusUndefined` inside the polar circle."""
    eps = math.radians(ang.obliquity)
    c11 = _placidus_cusp(ramc=ang.ramc, latitude=latitude, eps=eps, fraction=1 / 3, nocturnal=False)
    c12 = _placidus_cusp(ramc=ang.ramc, latitude=latitude, eps=eps, fraction=2 / 3, nocturnal=False)
    c2 = _placidus_cusp(ramc=ang.ramc, latitude=latitude, eps=eps, fraction=2 / 3, nocturnal=True)
    c3 = _placidus_cusp(ramc=ang.ramc, latitude=latitude, eps=eps, fraction=1 / 3, nocturnal=True)

    cusps = [
        ang.ascendant, c2, c3,
        ang.imum_coeli, (c11 + 180.0) % 360.0, (c12 + 180.0) % 360.0,
        ang.descendant, (c2 + 180.0) % 360.0, (c3 + 180.0) % 360.0,
        ang.midheaven, c11, c12,
    ]
    return tuple(c % 360.0 for c in cusps)


def whole_sign(ang: Angles) -> tuple[float, ...]:
    """Each house is one whole sign, starting from the Ascendant's sign."""
    start = math.floor(ang.ascendant / 30.0) * 30.0
    return tuple((start + 30.0 * i) % 360.0 for i in range(12))


def porphyry(ang: Angles) -> tuple[float, ...]:
    """Trisect each ecliptic quadrant — defined at every latitude."""
    asc, mc = ang.ascendant, ang.midheaven
    ic, dsc = ang.imum_coeli, ang.descendant
    q1 = (asc - ic) % 360.0     # houses 1..3 span IC→ASC? no: ASC→IC is 1-3
    q_asc_ic = (ic - asc) % 360.0
    q_ic_dsc = (dsc - ic) % 360.0
    q_dsc_mc = (mc - dsc) % 360.0
    q_mc_asc = (asc - mc) % 360.0
    del q1
    cusps = [
        asc,
        (asc + q_asc_ic / 3.0) % 360.0,
        (asc + 2.0 * q_asc_ic / 3.0) % 360.0,
        ic,
        (ic + q_ic_dsc / 3.0) % 360.0,
        (ic + 2.0 * q_ic_dsc / 3.0) % 360.0,
        dsc,
        (dsc + q_dsc_mc / 3.0) % 360.0,
        (dsc + 2.0 * q_dsc_mc / 3.0) % 360.0,
        mc,
        (mc + q_mc_asc / 3.0) % 360.0,
        (mc + 2.0 * q_mc_asc / 3.0) % 360.0,
    ]
    return tuple(cusps)


def compute(
    ang: Angles, latitude: float, system: str = "placidus"
) -> Houses:
    """Cusps in the requested system, with an honest fallback near the poles."""
    if system == "whole_sign":
        return Houses(whole_sign(ang), "whole_sign", system, None)
    if system == "porphyry":
        return Houses(porphyry(ang), "porphyry", system, None)

    try:
        return Houses(placidus(ang, latitude), "placidus", system, None)
    except PlacidusUndefined as exc:
        return Houses(
            porphyry(ang),
            "porphyry",
            system,
            f"Placidus is undefined at latitude {latitude:.2f}° ({exc}); "
            "Porphyry used instead",
        )


def house_of(longitude: float, cusps: tuple[float, ...]) -> int:
    """Which house a degree falls in, 1..12."""
    for i in range(12):
        start = cusps[i]
        end = cusps[(i + 1) % 12]
        span = (end - start) % 360.0
        offset = (longitude - start) % 360.0
        if offset < span:
            return i + 1
    return 12
