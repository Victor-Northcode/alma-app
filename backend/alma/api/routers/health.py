"""Health and readiness.

`/health` is for a load balancer: is this process alive. `/ready` is for a
human before a launch: is everything this service needs actually configured.
The second one lists what is missing by name, because "not ready" without a
reason is a message that gets ignored.
"""

from __future__ import annotations

import time

from fastapi import APIRouter

from ... import geo, region
from ...calc.contract import ENGINE_VERSION
from ...config import settings
from ...db import healthy
from ...engine import ephemeris
from ..cache import result_cache

router = APIRouter(tags=["service"])
_STARTED = time.time()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "uptime_seconds": round(time.time() - _STARTED, 1)}


@router.get("/ready")
async def ready() -> dict:
    config = settings()
    database = await healthy()

    try:
        kernel = ephemeris.kernel_name()
        chiron = ephemeris.chiron_body() is not None
        ephemeris_ok = True
    except Exception as exc:  # pragma: no cover - only on a broken install
        kernel, chiron, ephemeris_ok = str(exc), False, False

    missing = config.missing_for_production()
    checks = {
        "database": database,
        "ephemeris": ephemeris_ok,
        "places": geo.index_available(),
        "ai": config.ai_enabled,
        "billing": config.billing_enabled,
    }
    return {
        "ready": database and ephemeris_ok and geo.index_available(),
        "production_ready": not missing,
        "missing": missing,
        "checks": checks,
        "engine_version": ENGINE_VERSION,
        "ephemeris_kernel": kernel,
        "chiron_available": chiron,
        "environment": config.environment,
        # Whether anything in front of this service is telling it where requests
        # come from. Not part of `ready`: a service with no edge is running and
        # serving, it is only quoting dollars to the whole world while doing it.
        # That is a deployment fault rather than an outage, and failing
        # readiness for it would block a deploy over a price label. It is here
        # because it is otherwise indistinguishable from correct behaviour —
        # see `region.observe`.
        "edge_country": region.observations(),
        "cache": {
            "size": result_cache().size,
            "hits": result_cache().hits,
            "misses": result_cache().misses,
        },
    }
