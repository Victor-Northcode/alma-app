"""Place search and timezone lookup — the first thing a new user touches.

Обе ручки — синхронная работа: FTS5-запрос в bundled SQLite и полигональный
поиск `timezonefinder` поверх ~50 МБ данных. Ни то ни другое не становится
асинхронным от слова `async def` перед функцией, поэтому обе уезжают в
рабочий поток (`anyio.to_thread`, тот же приём, что в `auth/providers` и
`calc/cache`).

Замер на этой машине, изнутри работающего приложения, пульс каждые 10 мс —
худший пропуск пульса есть время, которое воркер не отвечал никому:

* `GET /places/timezone`, **первый** вызов — 0.334 с. Столько стоит загрузка
  полигонов `timezonefinder`; платил её первый живой человек за день, и он же
  платил её после каждого перезапуска воркера. Прогрев на старте
  (`api/app._warm`) убирает эту секунду с человека, а поток убирает её из
  цикла — нужны оба: прогрев не помогает воркеру, который перезапустился под
  нагрузкой, а поток не помогает тому, кто пришёл первым.
* `GET /places/search` — здесь замер времени как раз **не** подтвердил
  тревогу: сам `geo.search` на прогретом кэше страниц SQLite укладывается в
  0.1–10 мс, и цикл на нём заметно не стоял. В поток он уехал по двум другим
  причинам. Первая — подсказка мест летит на **каждое нажатие клавиши**, и
  десять тысяч человек, набирающих город рождения, складывают миллисекунды в
  занятый цикл. Вторая и главная — 10 мс это ровно до тех пор, пока страница
  лежит в кэше ОС; чтение той, которой там нет, — блокирующий поход на диск, и
  его длительность нам не принадлежит вовсе. Оставлять в цикле работу, потолка
  которой мы не знаем, — это и есть та ставка, которой посвящён весь файл.

Один поток на запрос, а не три: зона, смещение и ближайший город считаются
одной синхронной функцией. Три `run_sync` подряд — это три постановки в
очередь пула ради работы, которая целиком занимает миллисекунды.
"""

from __future__ import annotations

from datetime import date, datetime, time
from functools import partial

from anyio import to_thread
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
    found = await to_thread.run_sync(partial(geo.search, q, limit=limit))
    return [PlaceOut(**place.as_dict()) for place in found]


def _timezone_payload(latitude: float, longitude: float, when: datetime) -> dict | None:
    """Зона, её смещение на дату и ближайший город — одним заходом в поток.

    Синхронная и приватная: всё, что она трогает, — это `geo`, то есть
    полигоны и SQLite. `None` означает «над водой» и остаётся ответом, а не
    ошибкой, — см. `geo.timezone_at`.
    """
    zone = geo.timezone_at(latitude, longitude)
    if zone is None:
        return None
    offset = geo.offset_at(zone, when)
    place = geo.nearest(latitude, longitude)
    return {
        "timezone": zone,
        "offset_hours": offset,
        "offset": geo.describe_offset(offset),
        "as_of": when.date().isoformat(),
        "nearest_place": place.as_dict() if place else None,
    }


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
    when = datetime.combine(on or date.today(), time.fromisoformat(at) if at else time(12, 0))
    payload = await to_thread.run_sync(
        partial(_timezone_payload, latitude, longitude, when)
    )
    if payload is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="no timezone covers that coordinate — is it in the sea?",
        )
    return payload
