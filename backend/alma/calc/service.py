"""One entry point per system, all of them producing a CalcResult.

Everything above this line — the API, the AI layer, the cache — talks to
`compute()` and never to the engine directly. That is what keeps the promise
that the AI can only cite facts the engine actually produced: there is one
place where facts become citable, and it is here.

The serialisers below are deliberately explicit rather than reflective. A
generic "dump every field" would quietly start exposing internals the moment
someone added one, and the shape of `data` is a public contract the frontend
reads.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, timezone

from ..engine import (
    arcana,
    astrocartography,
    ephemeris,
    natal,
    numerology,
    solar_return,
    synastry,
    synthesis,
    transits,
    zodiac,
)
from ..engine.timeutil import AmbiguousLocalTime, BirthMoment, resolve
from .contract import BirthData, CalcResult, build, json_safe

#: Re-exported so callers can catch it without importing the engine.
AmbiguousBirthTime = AmbiguousLocalTime


class TimeRequired(Exception):
    """This system cannot be computed without a real birth time."""


def moment_for(birth: BirthData) -> BirthMoment:
    hour, minute = birth.hour_minute
    return resolve(
        year=birth.date.year,
        month=birth.date.month,
        day=birth.date.day,
        hour=hour,
        minute=minute,
        tz_name=birth.timezone,
        on_ambiguous=birth.on_ambiguous,
    )


def chart_for(birth: BirthData, *, house_system: str = "placidus") -> natal.NatalChart:
    return natal.compute(
        moment=moment_for(birth),
        latitude=birth.latitude,
        longitude=birth.longitude,
        house_system=house_system,
    )


def _provenance(chart: natal.NatalChart | None = None, **extra) -> dict:
    """What produced these numbers — recorded on every result.

    A reading that cannot be reproduced cannot be defended, and "which
    ephemeris and which house system" is the whole of the difference between
    two implementations disagreeing and one of them being wrong.
    """
    data = {"ephemeris": ephemeris.kernel_name()}
    if chart is not None:
        data["house_system"] = chart.house_system
        data["julian_day"] = chart.julian_day
        data["timezone"] = chart.tz_name
        data["utc_offset_hours"] = chart.utc_offset_hours
        if chart.house_fallback:
            data["house_fallback"] = chart.house_fallback
    data.update(extra)
    return data


# ── natal ──────────────────────────────────────────────────────────────────

def _placement_dict(placement: natal.BodyPlacement) -> dict:
    return {
        "body": placement.body,
        "glyph": zodiac.PLANET_GLYPHS.get(placement.body, ""),
        "longitude": placement.longitude,
        "latitude": placement.latitude,
        "speed": placement.speed,
        "retrograde": placement.retrograde,
        "sign": placement.sign,
        "sign_glyph": zodiac.SIGN_GLYPHS[zodiac.sign_index(placement.longitude)],
        "degree": placement.degree_in_sign,
        "formatted": placement.formatted,
        "house": placement.house,
        "dignity": placement.dignity,
        "dispositor": placement.dispositor,
    }


def _aspect_dict(aspect: zodiac.Aspect) -> dict:
    return {
        "first": aspect.first,
        "second": aspect.second,
        "type": aspect.type,
        "glyph": zodiac.ASPECT_GLYPHS.get(aspect.type, ""),
        "angle": aspect.angle,
        "orb": round(aspect.orb, 4),
        "applying": aspect.applying,
        "harmony": aspect.harmony,
        "major": aspect.major,
        "text": aspect.describe(),
    }


def natal_result(birth: BirthData, *, house_system: str = "placidus") -> CalcResult:
    chart = chart_for(birth, house_system=house_system)

    data = {
        "placements": {name: _placement_dict(p) for name, p in chart.placements.items()},
        "aspects": [_aspect_dict(a) for a in chart.aspects],
        "configurations": [
            {"name": c.name, "members": list(c.members), "detail": c.detail}
            for c in chart.configurations
        ],
        "balance": chart.balance,
        "dominants": chart.dominants,
        "moon_phase": chart.moon_phase,
        "lunar_day": chart.lunar_day,
        "sun_sign": chart.sun_sign(),
        "moon_sign": chart.moon_sign(),
        "rising_sign": chart.rising_sign(),
        "time_known": chart.time_known,
    }
    if chart.angles:
        data["angles"] = {
            "ascendant": chart.angles.ascendant,
            "midheaven": chart.angles.midheaven,
            "descendant": chart.angles.descendant,
            "imum_coeli": chart.angles.imum_coeli,
            "vertex": chart.angles.vertex,
            "obliquity": chart.angles.obliquity,
            "formatted": {
                "ascendant": zodiac.format_position(chart.angles.ascendant),
                "midheaven": zodiac.format_position(chart.angles.midheaven),
            },
        }
        data["houses"] = [
            {
                "number": index + 1,
                "cusp": cusp,
                "sign": zodiac.sign_of(cusp),
                "formatted": zodiac.format_position(cusp),
            }
            for index, cusp in enumerate(chart.house_cusps)
        ]
        data["part_of_fortune"] = chart.part_of_fortune
        data["sect"] = chart.sect

    return build(
        system="natal",
        birth=birth,
        data=data,
        factors=chart.factors(),
        unavailable=chart.unavailable,
        notes=chart.notes,
        provenance=_provenance(chart),
    )


# ── numerology ─────────────────────────────────────────────────────────────

def numerology_result(birth: BirthData, *, reference: date_type | None = None) -> CalcResult:
    today = reference or datetime.now(timezone.utc).date()
    result = numerology.calculate(
        day=birth.date.day,
        month=birth.date.month,
        year=birth.date.year,
        full_name=birth.name,
    )
    personal_year = numerology.personal_year(birth.date.day, birth.date.month, today.year)
    personal_month = numerology.personal_month(personal_year, today.month)
    personal_day = numerology.personal_day(personal_month, today.day)

    data = {
        "life_path": result.life_path,
        "life_path_debt": result.life_path_debt,
        "birthday_number": result.birthday_number,
        "destiny_number": result.destiny_number,
        "master_numbers": list(result.master_numbers_present),
        "karmic_debts": list(result.karmic_debts_present),
        "pinnacles": [json_safe(p) for p in result.pinnacles],
        "challenges": [json_safe(c) for c in result.challenges],
        "cycles": [json_safe(c) for c in result.cycles],
        "personal": {
            "year": personal_year,
            "month": personal_month,
            "day": personal_day,
            "reference_date": today.isoformat(),
        },
    }
    unavailable: list[str] = []
    if result.name:
        data["name"] = {
            "expression": result.name.expression,
            "soul_urge": result.name.soul_urge,
            "personality": result.name.personality,
            "maturity": result.name.maturity,
            "karmic_lessons": list(result.name.karmic_lessons),
        }
    else:
        unavailable.append(
            "expression, soul urge, personality and maturity: these are read "
            "from the full birth name, which we do not have"
        )

    return build(
        system="numerology",
        birth=birth,
        data=data,
        factors=result.factors()
        + [
            f"personal year {personal_year}",
            f"personal month {personal_month}",
            f"personal day {personal_day}",
        ],
        unavailable=unavailable,
        provenance={"method": "pythagorean"},
    )


# ── birth card ─────────────────────────────────────────────────────────────

def _card_dict(card: arcana.Card) -> dict:
    return {
        "number": card.number,
        "name": card.name,
        "numeral": card.numeral,
        "element": card.element,
        "ruler": card.ruler,
    }


def birth_card_result(birth: BirthData, *, reference: date_type | None = None) -> CalcResult:
    today = reference or datetime.now(timezone.utc).date()
    life_path, _debt = numerology.life_path(birth.date.day, birth.date.month, birth.date.year)
    result = arcana.calculate(
        day=birth.date.day,
        month=birth.date.month,
        year=birth.date.year,
        life_path=life_path,
        today=(today.year, today.month, today.day),
    )

    data = {
        "personality": _card_dict(result.personality),
        "soul": _card_dict(result.soul),
        "is_same_card": result.is_same_card,
        "triad": [_card_dict(c) for c in result.triad],
        "life_path_link": result.life_path_link,
    }
    if result.year:
        data["year"] = {
            "card": _card_dict(result.year.card),
            "next_card": _card_dict(result.year.next_card),
            "period_start": result.year.period_start,
            "period_end": result.year.period_end,
            "position_in_cycle": result.year.position_in_cycle,
        }

    return build(
        system="birth-card",
        birth=birth,
        data=data,
        factors=result.factors(),
        provenance={"attributions": "golden dawn"},
    )


# ── transits ───────────────────────────────────────────────────────────────

def _julian(when: datetime) -> float:
    from ..engine.timeutil import _julian_day

    return _julian_day(when)


def _hit_dict(hit: transits.Hit) -> dict:
    return {
        "transiting": hit.transiting,
        "natal": hit.natal,
        "aspect": hit.aspect,
        "glyph": zodiac.ASPECT_GLYPHS.get(hit.aspect, ""),
        "exact": _iso(hit.exact_jd),
        "enters": _iso(hit.enters_jd),
        "leaves": _iso(hit.leaves_jd),
        "orb_now": hit.orb_now,
        "applying": hit.applying,
        "retrograde": hit.retrograde,
        "weight": hit.weight,
        "urgency": hit.urgency,
        "text": hit.describe(),
    }


def _iso(jd: float | None) -> str | None:
    if jd is None:
        return None
    from datetime import timedelta

    moment = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=jd - 2451545.0)
    return moment.isoformat(timespec="minutes")


def transits_result(
    birth: BirthData,
    *,
    start: datetime | None = None,
    days: int = 365,
    include_moon: bool = False,
    house_system: str = "placidus",
) -> CalcResult:
    chart = chart_for(birth, house_system=house_system)
    begin = start or datetime.now(timezone.utc)
    start_jd = _julian(begin)
    hits = transits.scan(
        chart,
        start_jd=start_jd,
        end_jd=start_jd + days,
        include_moon=include_moon,
        reference_jd=start_jd,
    )
    live = transits.active(hits, start_jd)

    # The sky at the moment this was asked for — not at the moment of birth.
    # `Today` prints a moon line under today's date, and it used to read the
    # *natal* chart's `moon_phase`: the moon this person was born under,
    # presented as tonight's. Same class of untruth as yesterday's date on a
    # screen called Today, and from the same cause — a fact about the reader's
    # day taken from somewhere that is not their day.
    now = ephemeris.positions(start_jd, ("sun", "moon"))
    sun_now = now["sun"].longitude
    moon_now = now["moon"].longitude

    data = {
        "window": {"from": begin.isoformat(timespec="minutes"), "days": days},
        "sky_now": {
            "moon_phase": zodiac.moon_phase(sun_now, moon_now),
            "lunar_day": zodiac.lunar_day(sun_now, moon_now),
        },
        "active": [_hit_dict(h) for h in live],
        "upcoming": [_hit_dict(h) for h in hits[:60]],
        "active_count": len(live),
        "total": len(hits),
    }
    unavailable = list(chart.unavailable)
    if not chart.time_known:
        unavailable.append(
            "transits to the ascendant and midheaven: the birth time is unknown"
        )

    return build(
        system="transits",
        birth=birth,
        data=data,
        factors=transits.factors(live),
        unavailable=unavailable,
        notes=chart.notes,
        provenance=_provenance(chart, window_days=days),
    )


# ── solar return ───────────────────────────────────────────────────────────

def solar_return_result(
    birth: BirthData,
    *,
    year: int | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    house_system: str = "placidus",
) -> CalcResult:
    chart = chart_for(birth, house_system=house_system)
    if not chart.time_known:
        raise TimeRequired(
            "a solar return needs a real birth time — an assumed noon moves "
            "the return by six hours and the return ascendant by a quadrant"
        )

    target = year or datetime.now(timezone.utc).year
    result = solar_return.compute(
        natal_chart=chart,
        birth_moment=moment_for(birth),
        year=target,
        latitude=latitude,
        longitude=longitude,
        house_system=house_system,
    )

    data = {
        "year": result.year,
        "return_at": result.return_utc.isoformat(timespec="minutes"),
        "relocated": result.relocated,
        "latitude": result.latitude,
        "longitude": result.longitude,
        "year_ruler": result.year_ruler,
        "angular_bodies": list(result.angular_bodies),
        "natal_contacts": list(result.natal_contacts),
        "chart": {
            "placements": {
                name: _placement_dict(p) for name, p in result.chart.placements.items()
            },
            "angles": {
                "ascendant": result.chart.angles.ascendant,
                "midheaven": result.chart.angles.midheaven,
                "descendant": result.chart.angles.descendant,
                "imum_coeli": result.chart.angles.imum_coeli,
            },
            "houses": [
                {"number": i + 1, "cusp": cusp, "sign": zodiac.sign_of(cusp)}
                for i, cusp in enumerate(result.chart.house_cusps)
            ],
            "aspects": [_aspect_dict(a) for a in result.chart.aspects],
        },
    }

    return build(
        system="solar-return",
        birth=birth,
        data=data,
        factors=result.factors(),
        unavailable=result.chart.unavailable,
        notes=result.chart.notes,
        provenance=_provenance(result.chart, return_julian_day=result.return_jd),
    )


# ── compatibility ──────────────────────────────────────────────────────────

def compatibility_result(
    birth: BirthData,
    other: BirthData,
    *,
    house_system: str = "placidus",
) -> CalcResult:
    chart_a = chart_for(birth, house_system=house_system)
    chart_b = chart_for(other, house_system=house_system)
    result = synastry.compute(
        chart_a=chart_a,
        chart_b=chart_b,
        moment_a=moment_for(birth),
        moment_b=moment_for(other),
        house_system=house_system,
    )

    data = {
        "other": other.as_dict(),
        "contacts": [
            {
                "first": c.first,
                "second": c.second,
                "aspect": c.aspect,
                "glyph": zodiac.ASPECT_GLYPHS.get(c.aspect, ""),
                "orb": round(c.orb, 4),
                "quality": c.quality,
                "weight": c.weight,
                "text": c.describe(),
            }
            for c in result.contacts[:80]
        ],
        "overlays": [
            {"body": o.body, "house": o.house, "owner": o.owner, "text": o.describe()}
            for o in result.overlays
        ],
        "composite": {
            key: value
            for key, value in result.composite.items()
            if key not in {"aspects", "balance", "moon_phase"}
        },
        "composite_aspects": result.composite.get("aspects", []),
        "composite_balance": result.composite.get("balance"),
        "scores": result.scores,
        "highlights": list(result.highlights),
    }
    if result.davison and result.davison.angles:
        data["davison"] = {
            "julian_day": result.davison.julian_day,
            "latitude": result.davison.latitude,
            "longitude": result.davison.longitude,
            "ascendant": result.davison.angles.ascendant,
            "midheaven": result.davison.angles.midheaven,
            "placements": {
                name: _placement_dict(p) for name, p in result.davison.placements.items()
            },
        }

    return build(
        system="compatibility",
        birth=birth,
        data=data,
        factors=result.factors(),
        unavailable=result.unavailable,
        provenance=_provenance(chart_a, partner_house_system=chart_b.house_system),
    )


# ── astrocartography ───────────────────────────────────────────────────────

def astrocartography_result(
    birth: BirthData,
    *,
    house_system: str = "placidus",
    include_parans: bool = True,
) -> CalcResult:
    chart = chart_for(birth, house_system=house_system)
    if not chart.time_known:
        raise TimeRequired(
            "astrocartography needs a real birth time — sidereal time moves a "
            "degree every four minutes, so a noon guess is a different continent"
        )

    result = astrocartography.compute(chart, include_parans=include_parans)
    data = {
        "lines": [
            {
                "body": line.body,
                "angle": line.angle,
                "glyph": zodiac.PLANET_GLYPHS.get(line.body, ""),
                "meridian": line.meridian,
                "points": [{"lat": lat, "lon": lon} for lat, lon in line.points],
            }
            for line in result.lines
        ],
        "parans": [
            {
                "first": p.first,
                "first_angle": p.first_angle,
                "second": p.second,
                "second_angle": p.second_angle,
                "latitude": p.latitude,
                "text": p.describe(),
            }
            for p in result.parans
        ],
        "birthplace": {
            "latitude": result.birthplace.latitude,
            "longitude": result.birthplace.longitude,
            "influences": [
                {"body": b, "angle": a, "degrees": d}
                for b, a, d in result.birthplace.influences
            ],
            "text": result.birthplace.describe(),
        },
    }

    return build(
        system="astrocartography",
        birth=birth,
        data=data,
        factors=result.factors(),
        unavailable=result.unavailable,
        notes=chart.notes,
        provenance=_provenance(chart, influence_orb=astrocartography.INFLUENCE_ORB),
    )


# ── cross-synthesis ────────────────────────────────────────────────────────

def synthesis_result(
    birth: BirthData,
    *,
    reference: date_type | None = None,
    house_system: str = "placidus",
) -> CalcResult:
    today = reference or datetime.now(timezone.utc).date()
    chart = chart_for(birth, house_system=house_system)
    numbers = numerology.calculate(
        day=birth.date.day, month=birth.date.month, year=birth.date.year,
        full_name=birth.name,
    )
    cards = arcana.calculate(
        day=birth.date.day, month=birth.date.month, year=birth.date.year,
        life_path=numbers.life_path, today=(today.year, today.month, today.day),
    )
    personal_year = numerology.personal_year(birth.date.day, birth.date.month, today.year)

    result = synthesis.compute(
        chart=chart, numerology=numbers, arcana=cards, personal_year=personal_year
    )

    data = {
        "summary": result.summary(),
        "agreements": result.agreements,
        "disagreements": result.disagreements,
        "single_voice": result.single_voice,
        "axes": [
            {
                "name": axis.name,
                "verdict": axis.verdict,
                "label": axis.label,
                "count": axis.count,
                "direction": axis.direction,
                "positive_pole": axis.positive_pole,
                "negative_pole": axis.negative_pole,
                "signals": [
                    {"system": s.system, "value": s.value, "factor": s.factor, "leans": s.leans}
                    for s in axis.signals
                ],
            }
            for axis in result.axes
        ],
    }

    return build(
        system="synthesis",
        birth=birth,
        data=data,
        factors=result.factors(),
        unavailable=chart.unavailable,
        notes=chart.notes,
        provenance=_provenance(chart, reference_period=_synthesis_period(birth, today)),
    )


def _synthesis_period(birth: BirthData, today: date_type) -> str:
    """The span of dates over which this synthesis is the same synthesis.

    The stamp used to be `reference_date`: the single day it was computed on.
    That is a fact about the request rather than about the answer, and once the
    cache key became the pair of years this result actually moves with — the
    calendar year for the personal year, the birthday year for the Year Card —
    it made a hit distinguishable from a miss, which is the second rule in
    `cache.py`'s own docstring. Worse, it is served to clients: a synthesis
    computed in March and read in September reported March. Naming the period
    is constant across every reference date that shares the key, so it is true
    for as long as the answer is.
    """
    had_birthday = (today.month, today.day) >= (birth.date.month, birth.date.day)
    card_year = today.year if had_birthday else today.year - 1
    return f"{card_year}-{birth.date.month:02d}-{birth.date.day:02d}/{today.year}"


# ── dispatcher ─────────────────────────────────────────────────────────────

_BUILDERS = {
    "natal": natal_result,
    "numerology": numerology_result,
    "birth-card": birth_card_result,
    "transits": transits_result,
    "solar-return": solar_return_result,
    "compatibility": compatibility_result,
    "astrocartography": astrocartography_result,
    "synthesis": synthesis_result,
}


def compute(system: str, birth: BirthData, **options) -> CalcResult:
    """Compute one system. The only door the rest of the service uses."""
    try:
        builder = _BUILDERS[system]
    except KeyError:
        raise ValueError(f"unknown system: {system}") from None
    return builder(birth, **options)
