"""Place search and timezone lookup — the first thing a new user touches."""

from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, HTTPException, Query, status

from ... import geo
from ..schemas import PlaceOut

router = APIRouter(prefix="/places", tags=["places"])


@router.get("/search", response_model=list[PlaceOut])
async def search(
    q: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=8, ge=1, le=25),
) -> list[PlaceOut]:
    if not geo.index_available():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="the place index is not installed on this server",
        )
    return [PlaceOut(**place.as_dict()) for place in geo.search(q, limit=limit)]


@router.get("/timezone")
async def timezone_for(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    on: date | None = None,
    at: str | None = Query(default=None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$"),
) -> dict:
    """Which zone covers a coordinate, and what it was doing on a given day.

    The date matters and is not optional in spirit: the same place has had
    different offsets in different decades, and the offset at the *birth*
    is the only one that produces the right chart.
    """
    zone = geo.timezone_at(latitude, longitude)
    if zone is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="no timezone covers that coordinate — is it in the sea?",
        )

    when = datetime.combine(on or date.today(), time.fromisoformat(at) if at else time(12, 0))
    offset = geo.offset_at(zone, when)
    return {
        "timezone": zone,
        "offset_hours": offset,
        "offset": geo.describe_offset(offset),
        "as_of": when.date().isoformat(),
        "nearest_place": (
            place.as_dict() if (place := geo.nearest(latitude, longitude)) else None
        ),
    }
