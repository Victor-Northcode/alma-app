"""Transits — where the moving sky touches the fixed chart.

A transit is only interesting if we can say *when*. "Saturn is squaring your
Sun" is a horoscope; "Saturn squares your Sun exactly on 14 June, in orb from
2 May to 28 July, and back over it in October" is a calendar entry. So this
module is built around root-finding rather than sampling: the exact hit is
solved for, the window is solved for, and the orb you see today is a
consequence rather than the headline.

Two decisions carry the module.

*Signed targets, not aspect names.* Working with `|separation − angle|` puts a
kink at exactness that bisection cannot cross. A trine is therefore two
targets, +120° and −120°, each with a smooth signed offset that changes sign
exactly where the aspect perfects.

*Everything vectorised.* A year of transits is tens of thousands of position
evaluations, and Skyfield's per-call overhead — the light-time iteration
above all — dominates completely when paid one instant at a time. Every
search here evaluates whole arrays: the sampling grid in one call, and each
round of bisection across all open brackets at once.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import ephemeris, zodiac
from .natal import NatalChart

#: Which moving bodies are reported, and how tight their orb is.
#: The Moon touches everything every month, so it is opt-in: including it by
#: default would bury the slow transits that actually describe a year.
TRANSIT_ORBS: dict[str, float] = {
    "sun": 1.0, "mercury": 1.0, "venus": 1.0, "mars": 1.5,
    "jupiter": 1.5, "saturn": 1.5, "uranus": 1.0, "neptune": 1.0,
    "pluto": 1.0, "chiron": 1.0, "moon": 0.5,
}

SLOW_BODIES: tuple[str, ...] = ("jupiter", "saturn", "uranus", "neptune", "pluto", "chiron")

#: Signed offsets, not aspect names: a trine is two distinct crossings.
ASPECT_TARGETS: tuple[tuple[str, float], ...] = (
    ("conjunction", 0.0),
    ("sextile", 60.0), ("sextile", -60.0),
    ("square", 90.0), ("square", -90.0),
    ("trine", 120.0), ("trine", -120.0),
    ("opposition", 180.0),
)

#: How heavy a hit is before its orb is taken into account. A Pluto square to
#: the Sun is a chapter of a life; a Venus sextile to Neptune is a Tuesday.
ASPECT_WEIGHT = {
    "conjunction": 1.0, "opposition": 0.95, "square": 0.9,
    "trine": 0.7, "sextile": 0.5,
}
BODY_WEIGHT = {
    "pluto": 1.0, "saturn": 1.0, "uranus": 0.95, "neptune": 0.9,
    "jupiter": 0.75, "chiron": 0.7, "mars": 0.5, "sun": 0.45,
    "venus": 0.3, "mercury": 0.3, "moon": 0.15,
}
NATAL_WEIGHT = {
    "sun": 1.0, "moon": 1.0, "ascendant": 1.0, "midheaven": 1.0,
    "mercury": 0.7, "venus": 0.7, "mars": 0.7,
    "saturn": 0.6, "jupiter": 0.5, "chiron": 0.5, "true_node": 0.5,
    "uranus": 0.4, "neptune": 0.4, "pluto": 0.4, "lilith": 0.3,
}

#: Sampling step per body, in days — fine enough that no crossing and no orb
#: window can slip between two samples. Mercury can cover 2° in a day and the
#: Moon 13°, so the fast bodies are sampled far more often than the slow ones.
STEPS: dict[str, float] = {
    "moon": 0.05,
    "mercury": 0.5, "venus": 0.5, "sun": 0.5,
    "mars": 1.0,
    "jupiter": 4.0, "saturn": 4.0, "uranus": 4.0,
    "neptune": 4.0, "pluto": 4.0, "chiron": 4.0,
}

#: Bisection stops here: 10⁻⁴ day is 8.6 seconds, far finer than any birth
#: time we are given and far finer than the ephemeris disagreement.
TIME_TOLERANCE = 1e-4


def _wrap180(degrees):
    return (degrees + 180.0) % 360.0 - 180.0


@dataclass(frozen=True, slots=True)
class Hit:
    """One transit contact, with the dates that make it actionable."""

    transiting: str
    natal: str
    aspect: str
    target_offset: float
    exact_jd: float
    enters_jd: float | None      # None when it was already in orb at the edge
    leaves_jd: float | None
    orb_now: float
    applying: bool
    retrograde: bool          # direction at the moment the aspect perfects
    weight: float             # how heavy the contact is, regardless of date

    @property
    def urgency(self) -> float:
        """Weight discounted by how far out of orb the contact is today."""
        return round(self.weight * max(0.2, 1.0 - min(1.0, self.orb_now / 3.0)), 4)

    def describe(self) -> str:
        glyph = zodiac.ASPECT_GLYPHS.get(self.aspect, self.aspect)
        motion = " retrograde" if self.retrograde else ""
        return (
            f"transiting {self.transiting}{motion} {glyph} natal {self.natal}"
            f" · orb {self.orb_now:.2f}°"
        )


def natal_points(chart: NatalChart) -> dict[str, float]:
    """The natal degrees worth transiting, angles included when we have them."""
    points = {
        name: placement.longitude
        for name, placement in chart.placements.items()
        if NATAL_WEIGHT.get(name, 0.0) > 0
    }
    if chart.angles:
        points["ascendant"] = chart.angles.ascendant
        points["midheaven"] = chart.angles.midheaven
    return points


def _grid(start: float, end: float, step: float) -> np.ndarray:
    count = max(2, int(np.ceil((end - start) / step)) + 1)
    return np.linspace(start, end, count)


def _residual(longitude, natal, target, orb_edge):
    """The function whose zeros we are chasing.

    Two root problems share one shape. Exactness is where the signed offset
    from the target reaches zero; the orb boundary is where its magnitude
    reaches the orb. `orb_edge` is NaN for the first kind and the orb for the
    second, which lets a single vectorised bisection solve both at once — and
    that matters, because the cost here is the number of ephemeris calls, not
    the number of brackets inside them.
    """
    signed = _wrap180(_wrap180(longitude - natal) - target)
    return np.where(np.isnan(orb_edge), signed, np.abs(signed) - orb_edge)


def _bisect(body: str, low, high, natal, target, orb_edge) -> np.ndarray:
    """Bisect every bracket for one body simultaneously.

    Each round is a single vectorised ephemeris call no matter how many
    brackets are open. That is the whole reason a year of transits finishes
    in a second rather than an hour: the work is ~20 calls per body, not ~20
    calls per contact.
    """
    low = np.asarray(low, dtype=np.float64).copy()
    high = np.asarray(high, dtype=np.float64).copy()
    if low.size == 0:
        return low

    f_low = _residual(ephemeris.longitudes(body, low), natal, target, orb_edge)
    rounds = int(np.ceil(np.log2(max(1e-12, float(np.max(high - low))) / TIME_TOLERANCE))) + 2
    for _ in range(max(1, rounds)):
        mid = (low + high) / 2.0
        f_mid = _residual(ephemeris.longitudes(body, mid), natal, target, orb_edge)
        left = f_low * f_mid <= 0
        high = np.where(left, mid, high)
        low = np.where(left, low, mid)
        f_low = np.where(left, f_low, f_mid)
    return (low + high) / 2.0


def scan(
    chart: NatalChart,
    *,
    start_jd: float,
    end_jd: float,
    bodies: tuple[str, ...] | None = None,
    include_moon: bool = False,
    reference_jd: float | None = None,
) -> list[Hit]:
    """Every transit contact between two instants, heaviest first."""
    if end_jd <= start_jd:
        raise ValueError("the transit window must run forwards")

    if bodies is None:
        bodies = tuple(b for b in TRANSIT_ORBS if b != "moon" or include_moon)

    targets = natal_points(chart)
    reference = start_jd if reference_jd is None else reference_jd
    hits: list[Hit] = []

    for body in bodies:
        if body == "chiron" and not (
            ephemeris.chiron_available(start_jd) and ephemeris.chiron_available(end_jd)
        ):
            continue

        orb = TRANSIT_ORBS[body]
        grid = _grid(start_jd, end_jd, STEPS.get(body, 4.0))
        sky = ephemeris.longitudes(body, grid)
        reference_longitude = float(ephemeris.longitudes(body, [reference])[0])
        drift = float(
            ephemeris.longitudes(body, [reference + 0.5])[0]
        )
        moving_back = _wrap180(drift - reference_longitude) < 0

        # Collect every bracket for this body first — exact hits and orb
        # boundaries together — then solve them all in one vectorised pass.
        keys: list[tuple[str, str, float]] = []
        lo: list[float] = []
        hi: list[float] = []
        natal_of: list[float] = []
        target_of: list[float] = []
        edge_of: list[float] = []
        kinds: list[bool] = []      # True for an orb boundary

        for natal_name, natal_longitude in targets.items():
            offsets = _wrap180(sky - natal_longitude)
            for aspect, target in ASPECT_TARGETS:
                signed = _wrap180(offsets - target)
                # A jump of nearly 360° between samples is the wrap, not a
                # crossing; a real crossing moves far less than half a turn.
                stepped = np.abs(np.diff(signed)) > 180.0
                exact_idx = np.flatnonzero(((signed[:-1] * signed[1:]) <= 0) & ~stepped)
                if exact_idx.size == 0:
                    continue

                edge = np.abs(signed) - orb
                edge_idx = np.flatnonzero(((edge[:-1] * edge[1:]) <= 0) & ~stepped)

                for index in exact_idx:
                    keys.append((natal_name, aspect, target))
                    lo.append(grid[index]); hi.append(grid[index + 1])
                    natal_of.append(natal_longitude); target_of.append(target)
                    edge_of.append(np.nan); kinds.append(False)
                for index in edge_idx:
                    keys.append((natal_name, aspect, target))
                    lo.append(grid[index]); hi.append(grid[index + 1])
                    natal_of.append(natal_longitude); target_of.append(target)
                    edge_of.append(orb); kinds.append(True)

        if not keys:
            continue

        roots = _bisect(
            body,
            np.array(lo), np.array(hi),
            np.array(natal_of), np.array(target_of), np.array(edge_of),
        )

        # Regroup: each exact hit takes the nearest orb boundary on each side
        # of it within its own (point, aspect, target) series.
        boundaries: dict[tuple[str, str, float], list[float]] = {}
        for key, root, is_edge in zip(keys, roots, kinds):
            if is_edge:
                boundaries.setdefault(key, []).append(float(root))
        for series in boundaries.values():
            series.sort()

        # Direction has to be read at the moment each aspect perfects, not at
        # whatever "today" happens to be: a station between the two would make
        # every later hit's direction a fiction.
        exact_jds = np.array(
            [float(r) for r, is_edge in zip(roots, kinds) if not is_edge]
        )
        if exact_jds.size:
            here = ephemeris.longitudes(body, exact_jds)
            soon = ephemeris.longitudes(body, exact_jds + 0.25)
            backwards = _wrap180(soon - here) < 0
        else:
            backwards = np.array([], dtype=bool)
        direction = iter(backwards)

        for key, root, is_edge in zip(keys, roots, kinds):
            if is_edge:
                continue
            natal_name, aspect, target = key
            exact_jd = float(root)
            moving_back = bool(next(direction))
            series = boundaries.get(key, [])
            before = [b for b in series if b < exact_jd]
            after = [b for b in series if b > exact_jd]

            natal_longitude = targets[natal_name]
            orb_now = abs(
                float(_wrap180(_wrap180(reference_longitude - natal_longitude) - target))
            )
            later = abs(float(_wrap180(_wrap180(drift - natal_longitude) - target)))

            hits.append(
                Hit(
                    transiting=body,
                    natal=natal_name,
                    aspect=aspect,
                    target_offset=target,
                    exact_jd=exact_jd,
                    enters_jd=before[-1] if before else None,
                    leaves_jd=after[0] if after else None,
                    orb_now=round(orb_now, 4),
                    applying=later < orb_now,
                    retrograde=moving_back,
                    weight=_weight(body, natal_name, aspect),
                )
            )

    hits.sort(key=lambda h: (-h.weight, h.exact_jd))
    return hits


def _weight(body: str, natal_name: str, aspect: str) -> float:
    """How much this contact matters, independent of when it lands.

    Deliberately not discounted by the orb of the moment: a Pluto square that
    perfects in November is a heavy transit in January too, and ranking a
    year's forecast by today's orb would bury it under a passing Venus.
    """
    return round(
        BODY_WEIGHT.get(body, 0.3)
        * NATAL_WEIGHT.get(natal_name, 0.3)
        * ASPECT_WEIGHT.get(aspect, 0.4),
        4,
    )


def active(hits: list[Hit], jd: float, *, limit: int | None = None) -> list[Hit]:
    """The hits actually in orb at one instant, most pressing first."""
    live = [
        h for h in hits
        if (h.enters_jd is None or h.enters_jd <= jd)
        and (h.leaves_jd is None or jd <= h.leaves_jd)
    ]
    live.sort(key=lambda h: -h.urgency)
    return live[:limit] if limit else live


def factors(hits: list[Hit]) -> list[str]:
    """Citable strings for the AI layer — one per contact."""
    return [hit.describe() for hit in hits]
