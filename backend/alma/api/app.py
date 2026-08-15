"""The FastAPI application.

Assembly only: routers, middleware, and the two error handlers that turn our
domain exceptions into answers a client can act on. Everything with an
opinion lives in the module it belongs to.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..calc.service import AmbiguousBirthTime, TimeRequired
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
    places,
    profiles,
    readings,
    systems,
)

log = logging.getLogger("alma")


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

    yield
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
            content={
                "error": "ambiguous_birth_time",
                "message": str(exc),
                "options": [
                    {"choice": "earlier", "utc": exc.earlier.isoformat()},
                    {"choice": "later", "utc": exc.later.isoformat()},
                ],
            },
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
