"""The FastAPI application.

Assembly only: routers, middleware, and the two error handlers that turn our
domain exceptions into answers a client can act on. Everything with an
opinion lives in the module it belongs to.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

from anyio import to_thread
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..calc.service import AmbiguousBirthTime, TimeRequired, ambiguity_detail
from ..config import settings
from ..db import create_all, dispose
from ..geo import PlaceIndexMissing
from . import plates
from .routers import (
    account,
    auth,
    billing,
    events,
    health,
    notify,
    pairs,
    places,
    profiles,
    readings,
    systems,
)

log = logging.getLogger("alma")


#: Сколько синхронной работы воркеру разрешено вести одновременно.
#:
#: Через этот пул уходит всё, что нельзя оставить в событийном цикле: расчёты
#: (`calc.cache.compute_cached_async`), геопоиск (`routers/places`), разбор
#: токенов входа (`auth/providers`) — и всё, что Starlette сам увозит из
#: синхронных зависимостей. Умолчание anyio — 40; выбрано меньше, и вот почему.
#:
#: Замерено на этой машине (10 ядер), годовой скан транзитов в потоках:
#:
#:      1 одновременно — 1.22 с всего
#:      2              — 2.20 с   (1.10 с на скан)
#:     10              — 10.94 с  (1.09 с на скан)
#:     20              — 22.28 с  (1.11 с на скан)
#:
#: То есть общее время растёт линейно: работа упирается в GIL и в ядра, и
#: параллельно она не идёт. Пул нужен ради **задержки цикла**, а не ради
#: пропускной способности, и лишние токены её только ухудшают: на 40 токенах
#: сорок пришедших разом читателей получают ответ через 44 секунды каждый —
#: все сорок дождутся таймаута клиента, и вся эта работа будет выброшена.
#: Меньший потолок означает, что часть ждёт в очереди, а те, кого впустили,
#: успевают ответить; лишние соединения при этом никуда не деваются — их
#: держит балансировщик, которому мы наконец отвечаем на проверку живости.
#:
#: Ровно `cpu_count()` было бы правильным числом, если бы вся работа была
#: счётной. Но половина того, что здесь бывает, — ожидание: SQLite читает
#: страницу с диска, `timezonefinder` разворачивает mmap, `PyJWKClient` идёт в
#: сеть за ключами Google. Такой поток держит токен, не занимая ядра, и ×2 —
#: место под них, не увеличивающее счётную нагрузку.
#:
#: `os.cpu_count()` читается на старте процесса, а не при импорте: цифра
#: принадлежит машине, а не коду, и на проде она другая.
def thread_pool_size() -> int:
    return (os.cpu_count() or 4) * 2


def _warm() -> None:
    """Синхронно прогреть то, за что иначе платит первый живой человек.

    Всё здесь — процессные кэши (`functools.lru_cache`), которые наполняются
    при первом обращении, и цена первого обращения замерена на этой машине:

    * `geo._finder()` — **0.334 с**. Полигоны `timezonefinder`, ~50 МБ. Это
      самая дорогая строка в файле и главная причина, по которой прогрев
      вообще есть: без него её оплачивает человек, который первым после
      выкладки открыл экран места рождения, — то есть самый первый шаг самого
      первого сценария продукта.
    * `geo._zone_names()` — 0.028 с. Обход каталога tzdata. Стоит на пути
      **каждого** запроса через `deps.device_timezone`, так что без прогрева
      её платит вообще первый запрос, какой бы он ни был.
    * индекс мест и эфемерида — единицы миллисекунд каждая, но это открытие
      файла и mmap, то есть блокирующее чтение с диска неизвестной длины на
      холодной машине.

    Ошибки проглатываются намеренно и логируются одной строкой: прогрев — это
    оптимизация, а не проверка готовности. Индекса мест может не быть вовсе
    (`PlaceIndexMissing` — законное состояние, `/places/search` отвечает на
    него 503), и уронить из-за этого весь процесс значило бы обменять
    работающий сервис на тёплый кэш.
    """
    from .. import geo

    steps = (
        ("timezone list", lambda: geo.is_known_timezone("UTC")),
        ("timezone polygons", lambda: geo.timezone_at(51.5074, -0.1278)),
        ("place index", lambda: geo.index_available() and geo.search("london", limit=1)),
        ("ephemeris", _warm_ephemeris),
    )
    for name, step in steps:
        try:
            step()
        except Exception as exc:      # noqa: BLE001 — см. докстринг
            log.info("warm-up skipped %s: %s", name, exc)


def _warm_ephemeris() -> None:
    from ..engine import ephemeris

    ephemeris.positions(2451545.0, ("sun", "moon"))


async def _warm_in_background() -> None:
    """Прогрев в рабочем потоке, запущенный и брошенный.

    **Готовность не ждёт прогрева, и это условие задачи, а не удобство.**
    Порядок в `lifespan` таков, что `yield` (то есть «процесс принимает
    соединения») случается сразу за созданием этой задачи: 0.36 с прогрева
    добавились бы к каждому старту воркера, а во время выкладки это 0.36 с,
    на которые балансировщик не видит ни старый воркер, ни новый.

    В потоке, а не прямо здесь, по той же причине, что и всё остальное: сам
    прогрев — синхронная работа, и оставить его в цикле значило бы получить
    ровно ту паузу, от которой он избавляет.
    """
    with suppress(Exception):
        await to_thread.run_sync(_warm, abandon_on_cancel=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = settings()
    # Refuses to boot a production process whose session tokens would be
    # forgeable. Better a failed deploy than a quiet one.
    config.check_production_ready()
    await create_all()

    missing = config.missing_for_production()
    if missing and config.is_production:
        log.warning("running in production without: %s", ", ".join(missing))

    # Ставится здесь, а не при импорте: лимитер anyio привязан к работающему
    # циклу, и вне его `current_default_thread_limiter()` просто поднимает.
    to_thread.current_default_thread_limiter().total_tokens = thread_pool_size()

    warming = asyncio.create_task(_warm_in_background())

    yield

    warming.cancel()
    with suppress(asyncio.CancelledError):
        await warming
    await dispose()


def create_app() -> FastAPI:
    config = settings()
    app = FastAPI(
        title="Alma",
        version="1.0.0",
        summary="Eight systems of self-knowledge, calculated rather than guessed.",
        lifespan=lifespan,
        docs_url="/docs" if not config.is_production else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Without this the browser cannot read the token minted by the request
        # that first needed an account — saving a birth, landing a sign-in — and
        # the next act would mint another one, so a person would collect an
        # account per thing they did. The id going the *other* way is a request
        # header the client generates and never needs to read back, which is why
        # only one of the two is named here; `allow_headers` already takes it.
        expose_headers=["X-Alma-Token"],
    )

    for router in (
        health.router,
        auth.router,
        account.router,
        profiles.router,
        pairs.router,
        places.router,
        systems.router,
        readings.router,
        billing.router,
        events.router,
        notify.router,
    ):
        app.include_router(router, prefix="" if router is health.router else "/v1")

    # Вклейки глав живут вне `/v1`: это файлы, а не ручка API, и версия им ни к
    # чему — содержимое под именем неизменно, новая картинка приезжает новым
    # `?v=` в ссылке.
    app.include_router(plates.router)

    @app.exception_handler(AmbiguousBirthTime)
    async def _ambiguous(_request: Request, exc: AmbiguousBirthTime) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ambiguity_detail(exc),
        )

    @app.exception_handler(TimeRequired)
    async def _needs_time(_request: Request, exc: TimeRequired) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": "birth_time_required", "message": str(exc)},
        )

    @app.exception_handler(PlaceIndexMissing)
    async def _no_places(_request: Request, exc: PlaceIndexMissing) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "place_index_missing", "message": str(exc)},
        )

    return app


app = create_app()
