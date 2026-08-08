"""The natal chart, assembled.

This is where the measured sky (`ephemeris`), the geometry of the horizon
(`houses`) and the interpretive vocabulary (`zodiac`) become one object the
rest of the service can read. Nothing is computed twice and nothing is
invented here — the module's whole job is composition, plus the handful of
derived points that need two systems at once (Part of Fortune needs the
Ascendant *and* the luminaries; the sect needs the Sun relative to the
horizon).

Two honesty rules are enforced structurally rather than by convention:

* Without a birth time there are no houses, no angles, no Part of Fortune and
  no sect. Those fields are None, and `time_known` says why. A chart that
  quietly assumed noon would produce an Ascendant that is wrong by up to
  180°, which reads exactly as confidently as a right one.
* Chiron can be genuinely unavailable. It is absent from the body list rather
  than present with a placeholder, and `unavailable` records the reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ephemeris, houses, zodiac
from .ephemeris import Position
from .timeutil import BirthMoment

#: Everything the chart draws, in the order a wheel lists them.
CHART_BODIES: tuple[str, ...] = ephemeris.PLANETS

#: Points that are computed rather than observed.
DERIVED_POINTS: tuple[str, ...] = ("true_node", "mean_node", "lilith")

#: Which bodies count toward the element/modality balance, and how much.
#: The luminaries and the Ascendant carry the chart; the outer planets are
#: generational and would otherwise drown out the personal picture.
BALANCE_WEIGHTS: dict[str, float] = {
    "sun": 3.0, "moon": 3.0, "ascendant": 3.0,
    "mercury": 2.0, "venus": 2.0, "mars": 2.0, "midheaven": 2.0,
    "jupiter": 1.5, "saturn": 1.5,
    "uranus": 0.5, "neptune": 0.5, "pluto": 0.5,
}


@dataclass(frozen=True, slots=True)
class BodyPlacement:
    """One body as the chart reads it: where, in what, moving how."""

    body: str
    longitude: float
    latitude: float
    speed: float
    retrograde: bool
    sign: str
    degree_in_sign: float
    formatted: str
    house: int | None
    dignity: str | None
    dispositor: str | None
    distance_au: float

    def describe(self) -> str:
        parts = [f"{self.body} {self.formatted}"]
        if self.house:
            parts.append(f"house {self.house}")
        if self.retrograde:
            parts.append("retrograde")
        if self.dignity and self.dignity != "peregrine":
            parts.append(self.dignity)
        return " · ".join(parts)


@dataclass(frozen=True, slots=True)
class NatalChart:
    """A complete natal chart. Every field is either measured or None."""

    julian_day: float
    time_known: bool
    latitude: float
    longitude: float
    tz_name: str
    utc_offset_hours: float
    ephemeris_kernel: str

    placements: dict[str, BodyPlacement]
    aspects: tuple[zodiac.Aspect, ...]
    configurations: tuple[zodiac.Configuration, ...]
    balance: dict
    dominants: dict
    moon_phase: dict
    lunar_day: int

    angles: houses.Angles | None = None
    house_cusps: tuple[float, ...] | None = None
    house_system: str | None = None
    house_fallback: str | None = None
    part_of_fortune: float | None = None
    sect: str | None = None                 # "day" | "night"
    unavailable: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    # ── the citable surface the AI layer is allowed to reference ──────────

    def factors(self) -> list[str]:
        """Every fact this chart can support a sentence with.

        The AI layer may cite these strings and nothing else. If a paragraph
        references something that is not in this list, the validator rejects
        it and regenerates — which is why the list has to be exhaustive and
        literal rather than decorative.
        """
        items: list[str] = []
        for placement in self.placements.values():
            items.append(placement.describe())

        if self.angles:
            items.append(f"ascendant {zodiac.format_position(self.angles.ascendant)}")
            items.append(f"midheaven {zodiac.format_position(self.angles.midheaven)}")
            items.append(f"descendant {zodiac.format_position(self.angles.descendant)}")
            items.append(f"imum coeli {zodiac.format_position(self.angles.imum_coeli)}")
            items.append(f"vertex {zodiac.format_position(self.angles.vertex)}")
        if self.part_of_fortune is not None:
            items.append(f"part of fortune {zodiac.format_position(self.part_of_fortune)}")
        if self.sect:
            items.append(f"{self.sect} birth")

        items += [aspect.describe() for aspect in self.aspects]
        items += [f"{c.name}: {', '.join(c.members)} ({c.detail})" for c in self.configurations]

        items.append(f"dominant element {self.balance['dominant_element']}")
        items.append(f"dominant modality {self.balance['dominant_modality']}")
        for missing in self.balance["missing_elements"]:
            items.append(f"no {missing} in the chart")
        if self.dominants["dominant_planet"]:
            items.append(f"dominant planet {self.dominants['dominant_planet']}")
        if self.dominants["dominant_sign"]:
            items.append(f"dominant sign {self.dominants['dominant_sign']}")

        items.append(f"moon phase {self.moon_phase['phase']}")
        items.append(f"lunar day {self.lunar_day}")
        if self.house_system:
            items.append(f"houses computed in {self.house_system}")
        return items

    def sun_sign(self) -> str:
        return self.placements["sun"].sign

    def moon_sign(self) -> str:
        return self.placements["moon"].sign

    def rising_sign(self) -> str | None:
        return zodiac.sign_of(self.angles.ascendant) if self.angles else None


def _placement(
    position: Position,
    cusps: tuple[float, ...] | None,
) -> BodyPlacement:
    dignity = zodiac.dignity_of(position.body, position.longitude)
    # Only the seven traditional bodies have essential dignity; for the
    # rest the table would report "peregrine" for every sign, which says
    # nothing. Reporting None is the honest shape.
    has_dignity = position.body in {
        "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
        "uranus", "neptune", "pluto",
    }
    return BodyPlacement(
        body=position.body,
        longitude=position.longitude,
        latitude=position.latitude,
        speed=position.speed_longitude,
        retrograde=position.retrograde,
        sign=zodiac.sign_of(position.longitude),
        degree_in_sign=zodiac.degree_in_sign(position.longitude),
        formatted=zodiac.format_position(position.longitude),
        house=houses.house_of(position.longitude, cusps) if cusps else None,
        dignity=dignity.status if has_dignity else None,
        dispositor=dignity.dispositor,
        distance_au=position.distance_au,
    )


def _sect(sun_longitude: float, ascendant: float, descendant: float) -> str:
    """Day birth means the Sun is above the horizon.

    Above the horizon is the half of the ecliptic running from the Descendant
    forward to the Ascendant — houses 7 through 12. Using "is the Sun in
    houses 7-12" directly would be circular here, since we want the sect
    before the house table exists in every system.
    """
    span = (ascendant - descendant) % 360.0
    offset = (sun_longitude - descendant) % 360.0
    return "day" if offset < span else "night"


def compute(
    *,
    moment: BirthMoment,
    latitude: float,
    longitude: float,
    house_system: str = "placidus",
    include_minor_aspects: bool = True,
) -> NatalChart:
    """Everything the natal system knows about one birth."""
    jd = moment.julian_day_utc
    t = ephemeris._skyfield_time(jd)

    raw: dict[str, Position] = ephemeris.positions(jd, CHART_BODIES)
    raw["true_node"] = ephemeris.lunar_node(jd, true_node=True)
    raw["mean_node"] = ephemeris.lunar_node(jd, true_node=False)
    raw["lilith"] = ephemeris.lilith(jd)

    unavailable: list[str] = []
    chiron = ephemeris.chiron(jd)
    if chiron is not None:
        raw["chiron"] = chiron
    else:
        unavailable.append(
            "chiron: outside the tabulated range 1900–2100, or the table is not installed"
        )

    notes: list[str] = []
    if moment.tz_note:
        notes.append(moment.tz_note)

    # ── angles and houses, only when the time is real ─────────────────────
    angles = cusps = system_used = fallback = None
    if moment.time_known:
        angles = houses.angles(jd, t.tt, latitude, longitude)
        table = houses.compute(angles, latitude, house_system)
        cusps, system_used, fallback = table.cusps, table.system, table.fallback_reason
        if fallback:
            notes.append(fallback)
    else:
        unavailable.append(
            "houses, angles, part of fortune and sect: the birth time is unknown"
        )

    placements = {name: _placement(pos, cusps) for name, pos in raw.items()}

    # ── aspects ───────────────────────────────────────────────────────────
    aspect_longitudes = {name: p.longitude for name, p in placements.items()}
    aspect_speeds = {name: p.speed for name, p in placements.items()}
    if angles:
        aspect_longitudes["ascendant"] = angles.ascendant
        aspect_longitudes["midheaven"] = angles.midheaven
        # The angles do not move through the zodiac the way a body does;
        # leaving them out of the speed table keeps "applying" honest.

    aspects = zodiac.find_aspects(
        aspect_longitudes, aspect_speeds, include_minor=include_minor_aspects
    )
    # The two nodes are the same axis measured two ways: they are always
    # within ~1.6° of each other, and their "conjunction" is an artefact.
    aspects = [
        a for a in aspects
        if {a.first, a.second} != {"true_node", "mean_node"}
    ]
    configurations = zodiac.find_configurations(aspect_longitudes, aspects)

    # ── balance, dominants, derived points ────────────────────────────────
    balance_input = {
        name: p.longitude for name, p in placements.items() if name in BALANCE_WEIGHTS
    }
    if angles:
        balance_input["ascendant"] = angles.ascendant
        balance_input["midheaven"] = angles.midheaven
    balance = zodiac.balance(balance_input, BALANCE_WEIGHTS)

    house_map = {name: p.house for name, p in placements.items() if p.house}
    dominants = zodiac.dominants(aspect_longitudes, house_map, aspects)

    sun_lon = placements["sun"].longitude
    moon_lon = placements["moon"].longitude
    fortune = sect = None
    if angles:
        sect = _sect(sun_lon, angles.ascendant, angles.descendant)
        fortune = zodiac.part_of_fortune(
            angles.ascendant, sun_lon, moon_lon, day_birth=sect == "day"
        )

    return NatalChart(
        julian_day=jd,
        time_known=moment.time_known,
        latitude=latitude,
        longitude=longitude,
        tz_name=moment.tz_name,
        utc_offset_hours=moment.utc_offset_hours,
        ephemeris_kernel=ephemeris.kernel_name(),
        placements=placements,
        aspects=tuple(aspects),
        configurations=tuple(configurations),
        balance=balance,
        dominants=dominants,
        moon_phase=zodiac.moon_phase(sun_lon, moon_lon),
        lunar_day=zodiac.lunar_day(sun_lon, moon_lon),
        angles=angles,
        house_cusps=cusps,
        house_system=system_used,
        house_fallback=fallback,
        part_of_fortune=fortune,
        sect=sect,
        unavailable=tuple(unavailable),
        notes=tuple(notes),
    )
