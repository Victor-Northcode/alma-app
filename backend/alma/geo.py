"""Places and their timezones — offline, and historically correct.

Two separate problems live here and they are easy to confuse.

*Where* is a search problem: someone types "milano" or "Милан" and expects
Milan. That runs against a bundled GeoNames index, so there is no geocoding
bill, no rate limit and no network dependency in the birth-data flow — the
one flow that must never fail.

*When* is the harder one. A birth time is a wall clock, and turning it into
an instant needs the offset that was in force *on that date*, not today's.
Italy was on CET in 1998 and on CEST in July; Russia abolished daylight
saving in 2011 and reinstated permanent standard time in 2014; Brazil dropped
it entirely in 2019. `zoneinfo` carries the IANA history, so the whole job is
to find the right zone name and let it answer — never to store an offset.

The one thing this module refuses to do is guess an offset from a coordinate
alone when the zone is unknown. A wrong zone is an hour of birth time, which
is thirty degrees of Ascendant, which is a different reading.
"""

from __future__ import annotations

import math
import os
import sqlite3
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, available_timezones


@dataclass(frozen=True, slots=True)
class Place:
    """One place, with everything a chart needs and nothing it does not."""

    id: int
    name: str
    region: str | None
    country: str
    country_code: str
    latitude: float
    longitude: float
    timezone: str
    population: int

    @property
    def label(self) -> str:
        parts = [self.name]
        if self.region and self.region != self.name:
            parts.append(self.region)
        parts.append(self.country)
        return ", ".join(parts)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "region": self.region,
            "country": self.country,
            "country_code": self.country_code,
            "label": self.label,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
        }


class PlaceIndexMissing(Exception):
    """The bundled gazetteer is not installed."""


def _index_path() -> Path:
    explicit = os.environ.get("ALMA_PLACES_DB")
    if explicit:
        return Path(explicit)
    return Path(__file__).resolve().parents[1] / "data" / "places.sqlite"


@lru_cache(maxsize=1)
def _connection() -> sqlite3.Connection:
    path = _index_path()
    if not path.exists():
        raise PlaceIndexMissing(
            f"no place index at {path} — run tools/build_places.py to build one"
        )
    # Read-only and shared across threads: the index never changes at runtime.
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def index_available() -> bool:
    return _index_path().exists()


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _row_to_place(row: sqlite3.Row) -> Place:
    return Place(
        id=row["id"],
        name=row["name"],
        region=row["region"],
        country=row["country_name"],
        country_code=row["country"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        timezone=row["timezone"],
        population=row["population"],
    )


def search(query: str, *, limit: int = 8) -> list[Place]:
    """Places matching a typed query, most likely first.

    Ranking is two-tier: whether the query matches what the place is actually
    *called*, and then how many people live there. Population alone is not
    enough — Jakarta carries the alternate name "New York Van Java" and has
    almost as many inhabitants as New York, so a pure population sort answers
    "new york" with Jakarta in second place. Text relevance alone is not
    enough either: it cannot tell the Milan of a million people from the
    village in Michigan.
    """
    cleaned = _fold(query).strip()
    if len(cleaned) < 2:
        return []

    # Prefix-match the last token so results appear while still typing.
    # Hyphens and apostrophes split into tokens rather than reaching FTS5,
    # where a bare "-" is the NOT operator: «Санкт-Петербург» used to be a
    # syntax error swallowed into an empty result — a Russian typing their own
    # city's name found nothing.
    tokens = [
        t for t in cleaned.replace(",", " ").replace("-", " ").replace("'", " ").split() if t
    ]
    if not tokens:
        return []
    expression = " ".join(tokens[:-1] + [f"{tokens[-1]}*"])
    typed = " ".join(tokens)

    try:
        rows = _connection().execute(
            """
            SELECT place.* FROM place_fts
            JOIN place ON place.id = place_fts.rowid
            WHERE place_fts MATCH :expression
            ORDER BY place.population DESC
            LIMIT :pool
            """,
            {"expression": expression, "pool": CANDIDATE_POOL},
        ).fetchall()
    except sqlite3.OperationalError:
        # A query of pure punctuation can be a syntax error in FTS5; an empty
        # result is the right answer, not a 500.
        return []

    ranked = sorted(rows, key=lambda row: -_score(row, typed))
    places = []
    for row in ranked[:limit]:
        place = _row_to_place(row)
        # **The city keeps the script it was typed in.** GeoNames files every
        # place under its English name, so somebody typing «Омск» was shown —
        # and saved — "Omsk". The alternate-name column already carries the
        # Cyrillic spelling; when the query is Cyrillic and one of the
        # alternates matches it, that spelling is the display name. Only the
        # matched script, never a guess: a Latin query never renames a city
        # into an alphabet the person did not use.
        localized = _localized_name(row, query)
        if localized:
            place = replace(place, name=localized)
        places.append(place)
    return places


def _cyrillic(text: str) -> bool:
    return any("\u0400" <= ch <= "\u04FF" for ch in text)


def _localized_name(row: sqlite3.Row, typed_raw: str) -> str | None:
    """The reader's own spelling, echoed — never a reconstruction.

    The folded alternates cannot be turned back into display names: folding
    strips combining marks, and Cyrillic «й» *is* «и» plus a combining breve,
    so a name rebuilt from the fold reads «Нижнии» — a typo on the one field
    the person will stare at. What can be shown honestly is the string they
    typed themselves, exactly as they typed it, once the fold of it matches
    one of the place's own spellings in full. A half-typed query keeps the
    canonical name until the word is finished.
    """
    if not _cyrillic(typed_raw):
        return None
    typed = _fold(typed_raw).strip()
    alternates = {a for a in row["fold_alts"].split("|") if a and _cyrillic(a)}
    folded_variants = {typed, typed.replace("-", " "), typed.replace(" ", "-")}
    if alternates & folded_variants:
        cleaned = " ".join(typed_raw.split())
        # Title-case around both spaces and hyphens, so «санкт-петербург»
        # typed lazily still reads «Санкт-Петербург».
        return "-".join(
            " ".join(w[:1].upper() + w[1:].lower() for w in part.split())
            for part in cleaned.split("-")
        )
    return None


#: How many of the most populous matches to re-rank. Large enough that a
#: well-named small place is never cut before scoring, small enough to stay
#: sub-millisecond.
CANDIDATE_POOL = 200

#: Blend weights. Population enters logarithmically so that a city ten times
#: larger counts for more but not for everything, and a name match is worth
#: roughly the gap between a village and a capital.
_EXACT_NAME = 8.0
_EXACT_ALTERNATE = 6.5
_PREFIX_NAME = 4.0
_CONTAINS_NAME = 1.0


def _score(row: sqlite3.Row, typed: str) -> float:
    """How likely this is the place the user meant.

    Three signals, each of which is wrong on its own.

    Population alone answers "new york" with Jakarta, which genuinely carries
    the alternate name "New York Van Java" and has almost as many inhabitants.

    Primary-name matching alone answers "münchen" with Münchenstein, a Swiss
    suburb of twelve thousand, because GeoNames files Munich under its English
    name. Same for "roma", which lands on a town in Lesotho rather than Rome.

    So an exact match against *any* of a place's spellings counts for nearly
    as much as its primary name, and population enters logarithmically —
    enough to separate a capital from a village, not enough to let the biggest
    city win an argument about what it is called.
    """
    name = row["fold_name"]
    if name == typed:
        bonus = _EXACT_NAME
    elif f"|{typed}|" in row["fold_alts"]:
        bonus = _EXACT_ALTERNATE
    elif name.startswith(typed):
        bonus = _PREFIX_NAME
    elif typed in name:
        bonus = _CONTAINS_NAME
    else:
        bonus = 0.0
    return bonus + math.log1p(row["population"])


def by_id(place_id: int) -> Place | None:
    row = _connection().execute("SELECT * FROM place WHERE id = ?", (place_id,)).fetchone()
    return _row_to_place(row) if row else None


def nearest(latitude: float, longitude: float, *, within_degrees: float = 1.5) -> Place | None:
    """The most populous known place near a coordinate.

    Used when someone drops a pin rather than typing a name. The bounding box
    is crude on purpose — this is for naming a place, not for measuring one,
    and the coordinate the user gave is what the chart actually uses.
    """
    row = _connection().execute(
        """
        SELECT * FROM place
        WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?
        ORDER BY population DESC LIMIT 1
        """,
        (
            latitude - within_degrees, latitude + within_degrees,
            longitude - within_degrees, longitude + within_degrees,
        ),
    ).fetchone()
    return _row_to_place(row) if row else None


# ── timezones ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _finder():
    """timezonefinder, loaded lazily — it costs ~50 MB of resident memory."""
    from timezonefinder import TimezoneFinder

    return TimezoneFinder()


def timezone_at(latitude: float, longitude: float) -> str | None:
    """The IANA zone covering a coordinate, or None over open water.

    None is a real answer and must stay one. Returning "UTC" for a point in
    the middle of the Atlantic would silently produce a chart, and a chart
    from a wrong zone is wrong by up to twelve hours of Ascendant.
    """
    zone = _finder().timezone_at(lat=latitude, lng=longitude)
    if zone is None:
        # certain_timezone_at is stricter; timezone_at already falls back to
        # the closest zone for coastal points, so a None here means ocean.
        return None
    return zone


def is_known_timezone(name: str) -> bool:
    return name in available_timezones()


def offset_at(timezone_name: str, when: datetime) -> float:
    """The UTC offset in hours that zone had at that instant.

    Deliberately takes a datetime: an offset stored against a place is a bug
    waiting for a daylight-saving boundary.
    """
    zone = ZoneInfo(timezone_name)
    offset = when.replace(tzinfo=zone).utcoffset()
    return offset.total_seconds() / 3600.0 if offset else 0.0


def describe_offset(hours: float) -> str:
    """'+01:00' — how a birth record shows its offset."""
    sign = "+" if hours >= 0 else "−"
    total = int(round(abs(hours) * 60))
    return f"{sign}{total // 60:02d}:{total % 60:02d}"
