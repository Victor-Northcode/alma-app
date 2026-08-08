"""Compatibility — two charts, read against each other three ways.

*Synastry* is the direct comparison: each person's planets aspecting the
other's, plus the house overlays that say which area of life each person
lands in for the other.

*Composite* is the midpoint chart — not a moment that ever existed, but the
conventional picture of the relationship as its own entity.

*Davison* is the chart for the midpoint in time and space: a real instant at
a real place, which means it can be computed with the ordinary natal machinery
and carries real houses.

Three views because they disagree, and where they disagree is the interesting
part. The synthesis layer downstream is built to surface that rather than
average it away.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import zodiac
from .natal import NatalChart, compute as compute_natal
from .timeutil import BirthMoment

#: Which cross-contacts carry weight in a relationship reading, and how much.
#: Sun/Moon/Venus/Mars/Ascendant are the relationship axis; the outer planets
#: matter when they touch a personal point and say little when they touch
#: each other, which for two people of the same generation they always do.
PAIR_WEIGHT: dict[str, float] = {
    "sun": 1.0, "moon": 1.0, "ascendant": 1.0, "venus": 0.9, "mars": 0.8,
    "midheaven": 0.7, "mercury": 0.6, "jupiter": 0.5, "saturn": 0.6,
    "chiron": 0.4, "true_node": 0.5,
    "uranus": 0.3, "neptune": 0.3, "pluto": 0.35, "lilith": 0.25,
}

#: Aspect quality. Squares and oppositions are not "bad" here — they are the
#: contacts that produce friction and attachment both, so they score as
#: strongly as trines while being flagged differently.
ASPECT_QUALITY: dict[str, tuple[float, str]] = {
    "conjunction": (1.0, "fusion"),
    "opposition": (0.9, "tension"),
    "trine": (0.85, "ease"),
    "square": (0.85, "friction"),
    "sextile": (0.6, "ease"),
    "quincunx": (0.35, "adjustment"),
}

GENERATIONAL = {"uranus", "neptune", "pluto"}


@dataclass(frozen=True, slots=True)
class Contact:
    """One cross-aspect between the two charts."""

    from_person: str      # "a" or "b" — whose body is first
    first: str
    second: str
    aspect: str
    orb: float
    quality: str
    weight: float

    def describe(self) -> str:
        glyph = zodiac.ASPECT_GLYPHS.get(self.aspect, self.aspect)
        other = "B" if self.from_person == "a" else "A"
        mine = "A" if self.from_person == "a" else "B"
        return f"{mine}'s {self.first} {glyph} {other}'s {self.second} · {self.orb:.2f}°"


@dataclass(frozen=True, slots=True)
class Overlay:
    """Where one person's body falls in the other's houses."""

    body: str
    house: int
    owner: str            # whose houses

    def describe(self) -> str:
        other = "B" if self.owner == "b" else "A"
        mine = "A" if self.owner == "b" else "B"
        return f"{mine}'s {self.body} falls in {other}'s house {self.house}"


@dataclass(frozen=True, slots=True)
class Compatibility:
    """The whole comparison, three views deep."""

    contacts: tuple[Contact, ...]
    overlays: tuple[Overlay, ...]
    composite: dict
    davison: NatalChart | None
    scores: dict
    highlights: tuple[str, ...]
    unavailable: tuple[str, ...] = ()

    def factors(self) -> list[str]:
        items = [contact.describe() for contact in self.contacts]
        items += [overlay.describe() for overlay in self.overlays]
        items.append(f"composite sun {zodiac.format_position(self.composite['sun'])}")
        items.append(f"composite moon {zodiac.format_position(self.composite['moon'])}")
        items.append(f"composite venus {zodiac.format_position(self.composite['venus'])}")
        if self.davison and self.davison.angles:
            items.append(
                f"davison ascendant {zodiac.format_position(self.davison.angles.ascendant)}"
            )
        for key, value in self.scores.items():
            items.append(f"{key} score {value}")
        items += list(self.highlights)
        return items


def midpoint(a: float, b: float) -> float:
    """The near midpoint of two longitudes.

    Averaging the raw numbers puts the midpoint of 350° and 10° at 180°, the
    opposite side of the zodiac from where it belongs. Going through the
    signed difference keeps it at 0°.

    Two points in exact opposition have two equally valid midpoints, ninety
    degrees either side. That is a real ambiguity in the definition rather
    than a bug, so it is resolved deterministically — the lower of the two —
    which also keeps the function symmetric in its arguments. A composite
    that changed depending on which partner was passed first would be a
    strange thing to sell.
    """
    difference = (b - a) % 360.0
    if difference > 180.0:
        difference -= 360.0

    mid = (a + difference / 2.0) % 360.0
    if abs(abs(difference) - 180.0) < 1e-12:
        mid = min(mid, (mid + 180.0) % 360.0)
    return mid


def _points(chart: NatalChart) -> dict[str, float]:
    points = {name: p.longitude for name, p in chart.placements.items() if name != "mean_node"}
    if chart.angles:
        points["ascendant"] = chart.angles.ascendant
        points["midheaven"] = chart.angles.midheaven
    return points


def contacts(chart_a: NatalChart, chart_b: NatalChart, *, orb_scale: float = 1.0) -> list[Contact]:
    """Every cross-aspect between the two charts, heaviest first."""
    a_points, b_points = _points(chart_a), _points(chart_b)
    found: list[Contact] = []

    for a_name, a_lon in a_points.items():
        for b_name, b_lon in b_points.items():
            # Two people of an age share their outer planets; an aspect
            # between them describes a generation, not a relationship.
            if a_name in GENERATIONAL and b_name in GENERATIONAL:
                continue

            gap = zodiac.separation(a_lon, b_lon)
            for aspect in zodiac.ASPECT_TYPES:
                if aspect.name not in ASPECT_QUALITY:
                    continue
                orb = abs(gap - aspect.angle)
                allowance = aspect.orb * orb_scale
                if a_name in zodiac.TIGHT_ORB_POINTS or b_name in zodiac.TIGHT_ORB_POINTS:
                    allowance *= 0.6
                if orb > allowance:
                    continue

                strength, quality = ASPECT_QUALITY[aspect.name]
                weight = (
                    PAIR_WEIGHT.get(a_name, 0.3)
                    * PAIR_WEIGHT.get(b_name, 0.3)
                    * strength
                    * max(0.25, 1.0 - orb / max(allowance, 1e-6))
                )
                found.append(
                    Contact(
                        from_person="a",
                        first=a_name,
                        second=b_name,
                        aspect=aspect.name,
                        orb=orb,
                        quality=quality,
                        weight=round(weight, 4),
                    )
                )
                break

    found.sort(key=lambda c: -c.weight)
    return found


def overlays(chart_a: NatalChart, chart_b: NatalChart) -> list[Overlay]:
    """Which of each person's houses the other person lands in."""
    from .houses import house_of

    result: list[Overlay] = []
    if chart_b.house_cusps:
        for name, placement in chart_a.placements.items():
            result.append(
                Overlay(name, house_of(placement.longitude, chart_b.house_cusps), owner="b")
            )
    if chart_a.house_cusps:
        for name, placement in chart_b.placements.items():
            result.append(
                Overlay(name, house_of(placement.longitude, chart_a.house_cusps), owner="a")
            )
    return result


def composite(chart_a: NatalChart, chart_b: NatalChart) -> dict:
    """The midpoint chart — the relationship read as its own entity.

    Every body is the near midpoint of the pair. The angles are the midpoints
    of the angles, which is the convention rather than a derivation: a
    composite has no moment and no place, so it has no horizon of its own.
    """
    a_points, b_points = _points(chart_a), _points(chart_b)
    shared = [name for name in a_points if name in b_points]
    points = {name: midpoint(a_points[name], b_points[name]) for name in shared}

    result: dict = dict(points)
    aspects = zodiac.find_aspects(points, include_minor=False)
    result["aspects"] = [a.describe() for a in aspects]
    result["balance"] = zodiac.balance(points)
    if "sun" in points and "moon" in points:
        result["moon_phase"] = zodiac.moon_phase(points["sun"], points["moon"])
    return result


def davison(
    chart_a: NatalChart,
    chart_b: NatalChart,
    moment_a: BirthMoment,
    moment_b: BirthMoment,
    *,
    house_system: str = "placidus",
) -> NatalChart | None:
    """The chart for the midpoint in time and space.

    Unlike the composite this is a real instant at a real place, so it has
    real houses and a real Moon. It needs both birth times to mean anything —
    a midpoint between a known time and an assumed noon is an assumed answer.
    """
    if not (chart_a.time_known and chart_b.time_known):
        return None

    middle = moment_a.utc + (moment_b.utc - moment_a.utc) / 2
    latitude = (chart_a.latitude + chart_b.latitude) / 2.0
    longitude = _midpoint_longitude(chart_a.longitude, chart_b.longitude)

    moment = BirthMoment(
        utc=middle.astimezone(timezone.utc),
        tz_name="UTC",
        utc_offset_hours=0.0,
        time_known=True,
        dst_active=False,
        tz_note=None,
    )
    return compute_natal(
        moment=moment, latitude=latitude, longitude=longitude, house_system=house_system
    )


def _midpoint_longitude(a: float, b: float) -> float:
    """Geographic midpoint, taken the short way round the globe."""
    difference = (b - a + 180.0) % 360.0 - 180.0
    return ((a + difference / 2.0 + 180.0) % 360.0) - 180.0


def _scores(found: list[Contact]) -> dict:
    """Four named scores, each the sum of the contacts that produce it.

    Not a single "compatibility percentage": one number invites the reader to
    treat a relationship as pass or fail, and it hides the thing they came for
    — which part is easy and which part is work.
    """
    buckets = {"attraction": 0.0, "warmth": 0.0, "friction": 0.0, "endurance": 0.0}
    for contact in found:
        pair = {contact.first, contact.second}
        if pair & {"venus", "mars"} and contact.weight > 0:
            buckets["attraction"] += contact.weight
        if contact.quality in ("ease", "fusion"):
            buckets["warmth"] += contact.weight
        if contact.quality in ("friction", "tension"):
            buckets["friction"] += contact.weight
        if pair & {"saturn"} or pair & {"midheaven"}:
            buckets["endurance"] += contact.weight

    return {key: round(value, 3) for key, value in buckets.items()}


def _highlights(found: list[Contact], overlay_list: list[Overlay]) -> tuple[str, ...]:
    """The handful of statements a reader would actually repeat out loud."""
    lines: list[str] = []
    for contact in found[:5]:
        lines.append(f"{contact.describe()} — {contact.quality}")

    seventh = [o for o in overlay_list if o.house == 7]
    for overlay in seventh[:2]:
        lines.append(f"{overlay.describe()} — the partnership house")
    eighth = [o for o in overlay_list if o.house == 8]
    for overlay in eighth[:1]:
        lines.append(f"{overlay.describe()} — the house of what is shared and hidden")
    return tuple(lines)


def compute(
    *,
    chart_a: NatalChart,
    chart_b: NatalChart,
    moment_a: BirthMoment | None = None,
    moment_b: BirthMoment | None = None,
    house_system: str = "placidus",
) -> Compatibility:
    """The whole comparison."""
    found = contacts(chart_a, chart_b)
    overlay_list = overlays(chart_a, chart_b)

    unavailable: list[str] = []
    if not (chart_a.time_known and chart_b.time_known):
        unavailable.append(
            "house overlays and the davison chart: both birth times are needed"
        )

    davison_chart = None
    if moment_a and moment_b:
        davison_chart = davison(chart_a, chart_b, moment_a, moment_b, house_system=house_system)

    return Compatibility(
        contacts=tuple(found),
        overlays=tuple(overlay_list),
        composite=composite(chart_a, chart_b),
        davison=davison_chart,
        scores=_scores(found),
        highlights=_highlights(found, overlay_list),
        unavailable=tuple(unavailable),
    )
