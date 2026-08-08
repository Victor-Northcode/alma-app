"""Signs, aspects, dignities, configurations — the interpretive scaffolding.

None of this is astronomy: it is the agreed vocabulary layered on top of the
longitudes, and every rule here comes from published tradition rather than
from a library we cannot use. Keeping it in one module means the AI layer has
exactly one place to draw citable factors from.
"""

from __future__ import annotations

from dataclasses import dataclass

SIGNS: tuple[str, ...] = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)
SIGN_GLYPHS: tuple[str, ...] = (
    "♈︎", "♉︎", "♊︎", "♋︎", "♌︎", "♍︎", "♎︎", "♏︎", "♐︎", "♑︎", "♒︎", "♓︎",
)
ELEMENTS: tuple[str, ...] = ("fire", "earth", "air", "water")
MODALITIES: tuple[str, ...] = ("cardinal", "fixed", "mutable")

PLANET_GLYPHS = {
    "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀", "mars": "♂",
    "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆", "pluto": "♇",
    "true_node": "☊", "mean_node": "☊", "chiron": "⚷", "lilith": "⚸",
    "fortune": "⊗", "ascendant": "ASC", "midheaven": "MC",
}

#: Traditional day/night rulers, then the modern outer-planet assignments.
SIGN_RULERS: dict[str, tuple[str, str | None]] = {
    "Aries": ("mars", None),
    "Taurus": ("venus", None),
    "Gemini": ("mercury", None),
    "Cancer": ("moon", None),
    "Leo": ("sun", None),
    "Virgo": ("mercury", None),
    "Libra": ("venus", None),
    "Scorpio": ("mars", "pluto"),
    "Sagittarius": ("jupiter", None),
    "Capricorn": ("saturn", None),
    "Aquarius": ("saturn", "uranus"),
    "Pisces": ("jupiter", "neptune"),
}

EXALTATIONS = {
    "sun": "Aries", "moon": "Taurus", "mercury": "Virgo", "venus": "Pisces",
    "mars": "Capricorn", "jupiter": "Cancer", "saturn": "Libra",
}
FALLS = {planet: SIGNS[(SIGNS.index(sign) + 6) % 12] for planet, sign in EXALTATIONS.items()}


@dataclass(frozen=True, slots=True)
class AspectType:
    name: str
    angle: float
    orb: float
    harmony: str      # "harmonious" | "tense" | "neutral"
    major: bool


ASPECT_TYPES: tuple[AspectType, ...] = (
    AspectType("conjunction", 0.0, 8.0, "neutral", True),
    AspectType("opposition", 180.0, 8.0, "tense", True),
    AspectType("trine", 120.0, 7.0, "harmonious", True),
    AspectType("square", 90.0, 7.0, "tense", True),
    AspectType("sextile", 60.0, 5.0, "harmonious", True),
    AspectType("quincunx", 150.0, 3.0, "tense", False),
    AspectType("semisextile", 30.0, 2.0, "neutral", False),
    AspectType("semisquare", 45.0, 2.0, "tense", False),
    AspectType("sesquiquadrate", 135.0, 2.0, "tense", False),
    AspectType("quintile", 72.0, 2.0, "harmonious", False),
    AspectType("biquintile", 144.0, 2.0, "harmonious", False),
)

#: The astrological glyphs, and the sextile is worth a note because it was
#: wrong. It used to be "✶" — U+2736 SIX POINTED BLACK STAR, a decorative
#: asterisk from the dingbats block that merely looks like the aspect. The
#: real one is U+26B9 SEXTILE, which lives in the Miscellaneous Symbols block
#: next to the other five and is what a font ships an astrological glyph for.
#:
#: This is not typography. These glyphs are the *only* thing naming the aspect
#: in a factor string — `transits.Hit.describe()` renders "transiting pluto ⚹
#: natal ascendant" and nothing in it says the word "sextile" — so the glyph is
#: what a model has to read the geometry from. A decorative star is not a
#: symbol it can be expected to know, and a reading that guessed wrong from it
#: is the failure `alma/daily/writing.py::brief` now defends against by naming
#: the aspect in words as well. Fixing the character does not make the glyph
#: sufficient; it stops it being actively misleading.
ASPECT_GLYPHS = {
    "conjunction": "☌", "opposition": "☍", "trine": "△", "square": "□",
    "sextile": "⚹", "quincunx": "⚻", "semisextile": "⚺", "semisquare": "∠",
    "sesquiquadrate": "⚼", "quintile": "Q", "biquintile": "bQ",
}

#: Luminaries get a wider orb; the outer planets and points get a tighter one.
ORB_WEIGHTS = {"sun": 1.25, "moon": 1.25, "ascendant": 1.15, "midheaven": 1.15}
TIGHT_ORB_POINTS = {"chiron", "lilith", "true_node", "mean_node", "fortune", "vertex"}


def sign_index(longitude: float) -> int:
    return int(longitude % 360.0 // 30)


def sign_of(longitude: float) -> str:
    return SIGNS[sign_index(longitude)]


def degree_in_sign(longitude: float) -> float:
    return longitude % 30.0


def element_of(longitude: float) -> str:
    return ELEMENTS[sign_index(longitude) % 4]


def modality_of(longitude: float) -> str:
    return MODALITIES[sign_index(longitude) % 3]


def format_position(longitude: float) -> str:
    """'23°14′ ♓︎' — the way a chart actually prints a position."""
    idx = sign_index(longitude)
    deg = degree_in_sign(longitude)
    whole = int(deg)
    minutes = int(round((deg - whole) * 60))
    if minutes == 60:
        whole, minutes = whole + 1, 0
    return f"{whole}°{minutes:02d}′ {SIGN_GLYPHS[idx]}"


def separation(a: float, b: float) -> float:
    """Shortest angular distance between two longitudes, 0..180."""
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


@dataclass(frozen=True, slots=True)
class Aspect:
    first: str
    second: str
    type: str
    angle: float
    orb: float
    exact_orb: float
    applying: bool
    harmony: str
    major: bool

    def describe(self) -> str:
        glyph = ASPECT_GLYPHS.get(self.type, self.type)
        deg = int(self.orb)
        minutes = int(round((self.orb - deg) * 60))
        return (
            f"{PLANET_GLYPHS.get(self.first, self.first)} {glyph} "
            f"{PLANET_GLYPHS.get(self.second, self.second)} · {deg}°{minutes:02d}′"
        )


def _allowed_orb(aspect: AspectType, first: str, second: str) -> float:
    weight = max(ORB_WEIGHTS.get(first, 1.0), ORB_WEIGHTS.get(second, 1.0))
    if first in TIGHT_ORB_POINTS or second in TIGHT_ORB_POINTS:
        weight = min(weight, 0.6)
    return aspect.orb * weight


def find_aspects(
    positions: dict[str, float],
    speeds: dict[str, float] | None = None,
    *,
    include_minor: bool = True,
) -> list[Aspect]:
    """Every aspect between the supplied points, tightest orb first.

    `applying` needs the speeds: an aspect is applying when the faster body is
    still closing on exactness. Without speeds we say nothing rather than
    guessing, because "applying" is the half of the statement that carries the
    timing.
    """
    speeds = speeds or {}
    names = list(positions)
    found: list[Aspect] = []

    for i, first in enumerate(names):
        for second in names[i + 1 :]:
            gap = separation(positions[first], positions[second])
            for aspect in ASPECT_TYPES:
                if not include_minor and not aspect.major:
                    continue
                orb = abs(gap - aspect.angle)
                if orb > _allowed_orb(aspect, first, second):
                    continue

                applying = False
                if first in speeds and second in speeds:
                    step = 0.01
                    later = separation(
                        positions[first] + speeds[first] * step,
                        positions[second] + speeds[second] * step,
                    )
                    applying = abs(later - aspect.angle) < orb

                found.append(
                    Aspect(
                        first=first,
                        second=second,
                        type=aspect.name,
                        angle=aspect.angle,
                        orb=orb,
                        exact_orb=gap,
                        applying=applying,
                        harmony=aspect.harmony,
                        major=aspect.major,
                    )
                )
                break  # one aspect per pair — the closest match wins

    found.sort(key=lambda a: a.orb)
    return found


@dataclass(frozen=True, slots=True)
class Dignity:
    planet: str
    sign: str
    status: str          # rulership | exaltation | detriment | fall | peregrine
    dispositor: str | None


def dignity_of(planet: str, longitude: float) -> Dignity:
    sign = sign_of(longitude)
    traditional, modern = SIGN_RULERS[sign]
    rulers = {traditional} | ({modern} if modern else set())

    if planet in rulers:
        status = "rulership"
    elif EXALTATIONS.get(planet) == sign:
        status = "exaltation"
    elif planet in SIGN_RULERS[SIGNS[(SIGNS.index(sign) + 6) % 12]]:
        status = "detriment"
    elif FALLS.get(planet) == sign:
        status = "fall"
    else:
        status = "peregrine"

    dispositor = None if planet in rulers else (modern or traditional)
    return Dignity(planet, sign, status, dispositor)


def final_dispositor(dignities: dict[str, Dignity]) -> str | None:
    """The planet every chain of rulership eventually lands on, if any.

    Most charts have none — the chains close into a loop instead. Reporting
    "none" is the honest answer far more often than naming one.
    """
    for start in dignities:
        seen: list[str] = []
        current = start
        while current and current not in seen:
            seen.append(current)
            entry = dignities.get(current)
            if entry is None or entry.dispositor is None:
                break
            current = entry.dispositor
        else:
            continue
        if entry is not None and entry.dispositor is None and len(seen) > 1:
            return current
    return None


def balance(longitudes: dict[str, float], weights: dict[str, float] | None = None) -> dict:
    """Element and modality distribution, weighted toward the personal points."""
    weights = weights or {}
    elements = {e: 0.0 for e in ELEMENTS}
    modalities = {m: 0.0 for m in MODALITIES}
    for name, lon in longitudes.items():
        w = weights.get(name, 1.0)
        elements[element_of(lon)] += w
        modalities[modality_of(lon)] += w

    total = sum(elements.values()) or 1.0
    dominant_element = max(elements, key=lambda k: elements[k])
    dominant_modality = max(modalities, key=lambda k: modalities[k])
    missing = [e for e, v in elements.items() if v == 0]
    return {
        "elements": {k: round(v, 2) for k, v in elements.items()},
        "modalities": {k: round(v, 2) for k, v in modalities.items()},
        "element_percent": {k: round(100 * v / total, 1) for k, v in elements.items()},
        "dominant_element": dominant_element,
        "dominant_modality": dominant_modality,
        "missing_elements": missing,
    }


@dataclass(frozen=True, slots=True)
class Configuration:
    name: str
    members: tuple[str, ...]
    detail: str


def find_configurations(
    positions: dict[str, float], aspects: list[Aspect]
) -> list[Configuration]:
    """Stellium, t-square, grand trine, grand cross, yod and kite."""
    found: list[Configuration] = []
    by_pair = {frozenset((a.first, a.second)): a for a in aspects}

    def linked(x: str, y: str, kind: str) -> bool:
        aspect = by_pair.get(frozenset((x, y)))
        return aspect is not None and aspect.type == kind

    names = [n for n in positions if n not in {"ascendant", "midheaven"}]

    # Stellium: three or more bodies in one sign.
    by_sign: dict[str, list[str]] = {}
    for name in names:
        by_sign.setdefault(sign_of(positions[name]), []).append(name)
    for sign, members in by_sign.items():
        if len(members) >= 3:
            found.append(
                Configuration("stellium", tuple(sorted(members)), f"{len(members)} bodies in {sign}")
            )

    for i, a in enumerate(names):
        for j, b in enumerate(names[i + 1 :], i + 1):
            # Grand trine and kite
            if linked(a, b, "trine"):
                for c in names[j + 1 :]:
                    if linked(a, c, "trine") and linked(b, c, "trine"):
                        members = (a, b, c)
                        found.append(
                            Configuration("grand trine", members, f"in {element_of(positions[a])}")
                        )
                        for d in names:
                            if d in members:
                                continue
                            opposed = [m for m in members if linked(d, m, "opposition")]
                            sextiles = [m for m in members if linked(d, m, "sextile")]
                            if opposed and len(sextiles) >= 2:
                                found.append(
                                    Configuration(
                                        "kite", members + (d,), f"{d} opposes {opposed[0]}"
                                    )
                                )
            # T-square: two bodies in opposition, both square a third.
            if linked(a, b, "opposition"):
                for c in names:
                    if c in (a, b):
                        continue
                    if linked(a, c, "square") and linked(b, c, "square"):
                        found.append(
                            Configuration("t-square", (a, b, c), f"apex {c} in {sign_of(positions[c])}")
                        )
                        # Grand cross: a fourth body opposing the apex.
                        for d in names:
                            if d in (a, b, c):
                                continue
                            if linked(c, d, "opposition") and linked(a, d, "square"):
                                found.append(
                                    Configuration("grand cross", (a, b, c, d), modality_of(positions[a]))
                                )
            # Yod: two bodies in sextile, both quincunx a third.
            if linked(a, b, "sextile"):
                for c in names:
                    if c in (a, b):
                        continue
                    if linked(a, c, "quincunx") and linked(b, c, "quincunx"):
                        found.append(Configuration("yod", (a, b, c), f"apex {c}"))

    # Collapse duplicates that different orderings produced.
    unique: dict[tuple[str, tuple[str, ...]], Configuration] = {}
    for config in found:
        unique.setdefault((config.name, tuple(sorted(config.members))), config)
    return list(unique.values())


def dominants(
    longitudes: dict[str, float], houses_of: dict[str, int], aspects: list[Aspect]
) -> dict:
    """Which sign, planet and element the chart keeps insisting on.

    Scored rather than counted: an angular placement and a tight aspect say
    more than a body parked in the twelfth with no contacts.
    """
    scores: dict[str, float] = {}
    sign_scores: dict[str, float] = {s: 0.0 for s in SIGNS}

    for name, lon in longitudes.items():
        base = 3.0 if name in {"sun", "moon"} else 2.0
        house = houses_of.get(name)
        if house in (1, 10):
            base += 2.0
        elif house in (4, 7):
            base += 1.0
        scores[name] = scores.get(name, 0.0) + base
        sign_scores[sign_of(lon)] += base

    for aspect in aspects:
        weight = 1.5 if aspect.major else 0.5
        weight *= max(0.2, 1.0 - aspect.orb / 8.0)
        scores[aspect.first] = scores.get(aspect.first, 0.0) + weight
        scores[aspect.second] = scores.get(aspect.second, 0.0) + weight

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    ranked_signs = sorted(sign_scores.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "planets": [{"body": n, "score": round(v, 2)} for n, v in ranked[:5]],
        "signs": [{"sign": s, "score": round(v, 2)} for s, v in ranked_signs[:3] if v > 0],
        "dominant_planet": ranked[0][0] if ranked else None,
        "dominant_sign": ranked_signs[0][0] if ranked_signs else None,
    }


def part_of_fortune(ascendant: float, sun: float, moon: float, *, day_birth: bool) -> float:
    """ASC + Moon − Sun by day; the Sun and Moon swap by night."""
    if day_birth:
        return (ascendant + moon - sun) % 360.0
    return (ascendant + sun - moon) % 360.0


MOON_PHASES = (
    (0.0, "new moon"), (45.0, "waxing crescent"), (90.0, "first quarter"),
    (135.0, "waxing gibbous"), (180.0, "full moon"), (225.0, "waning gibbous"),
    (270.0, "last quarter"), (315.0, "waning crescent"),
)


def moon_phase(sun_longitude: float, moon_longitude: float) -> dict:
    """Phase from the Sun–Moon elongation, plus the illuminated fraction."""
    import math

    elongation = (moon_longitude - sun_longitude) % 360.0
    name = MOON_PHASES[0][1]
    for boundary, label in MOON_PHASES:
        if elongation >= boundary - 22.5:
            name = label
    if elongation >= 337.5:
        name = "new moon"

    illumination = (1 - math.cos(math.radians(elongation))) / 2
    return {
        "elongation": round(elongation, 4),
        "phase": name,
        "illumination": round(illumination, 4),
        "waxing": elongation < 180.0,
    }


def lunar_day(sun_longitude: float, moon_longitude: float) -> int:
    """Lunar day 1..30, counted from the new moon by elongation."""
    elongation = (moon_longitude - sun_longitude) % 360.0
    return min(30, int(elongation / 12.0) + 1)
