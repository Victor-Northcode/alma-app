"""Health and readiness.

`/health` is for a load balancer: is this process alive. `/ready` is for a
human before a launch: is everything this service needs actually configured.
The second one lists what is missing by name, because "not ready" without a
reason is a message that gets ignored.

**Кому этот список виден — отдельный вопрос, и раньше ответ был «всем».**
`/ready` открыт без токена (иначе он не годится ни балансировщику, ни проверке
деплоя) и при этом отдавал имя окружения, версию эфемерид, статистику кэша и
**поимённый перечень ненастроенных секретов**. Последнее — готовая карта для
атакующего: `missing` называет, какой замок ещё не повешен, а `checks` говорит,
какие двери вообще есть. Разведка такого качества обычно стоит недели.

Поэтому здесь два ответа на один маршрут. Наружу — булево «готов»: балансировщик
и `deploy --wait` спрашивают ровно его, а узнать, отвечает ли сервис, всё равно
можно любым запросом, так что это не новость. Подробности — только в локальной
песочнице (`deps.local_sandbox`, тот же замок, что на отладочном токене входа), а
в проде их место в логе процесса: `app.lifespan` пишет `running in production
without: …` на старте, и читает это тот, у кого есть доступ к машине, — то есть
ровно тот, кому список и предназначался.
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
from ..deps import local_sandbox

router = APIRouter(tags=["service"])
_STARTED = time.time()


@router.get("/health")
async def health() -> dict:
    """Живость. Публично и намеренно бессодержательно.

    Ни имени окружения, ни версий: единственное, что здесь сообщается сверх
    самого факта ответа, — сколько процесс живёт, и это то, ради чего маршрут
    существует (перезапускающийся под нагрузкой воркер виден только так).
    """
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
    # **Готовность — это все пять проверок, а не три из них.**
    #
    # Здесь стояло `database and ephemeris_ok and index_available()`, то есть
    # ровно те три, которые про инфраструктуру, — а `ai` и `billing` считались
    # ниже и в булев ответ не входили. Получалось, что процесс с пустым
    # `ANTHROPIC_API_KEY` и с невыписанными ключами процессора отвечал
    # `ready: true`, и это единственный ответ, который наружу вообще уходит.
    # То есть проверка готовности отвечала «готов» ровно в том состоянии, ради
    # которого её и спрашивают: расчёты идут, а всё, что продаётся, отвечает
    # 503 — главы, разговор, утренняя запись, касса.
    #
    # Цена честности названа прямо: развёртывание без процессора и без ключа
    # модели теперь говорит `ready: false`. Это правильно и это не отключает
    # сервис — **живость спрашивают у `/health`**, и именно его проверяет
    # `HEALTHCHECK` в `Dockerfile` и `docker-compose.yml`. `/ready` — ворота
    # выкатки: `docs/DEPLOY.md` велит смотреть его после каждого деплоя, и
    # смысл этого ритуала есть только пока «готов» означает «готов».
    answer = {"ready": all(checks.values())}
    if not local_sandbox():
        # Всё, что ниже, — про устройство сервиса, а не про то, отвечает ли он.
        # Наружу уходит один флаг: балансировщик спрашивает только его.
        return answer

    return {
        **answer,
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
