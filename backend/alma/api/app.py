"""The FastAPI application.

Assembly only: routers, middleware, and the two error handlers that turn our
domain exceptions into answers a client can act on. Everything with an
opinion lives in the module it belongs to.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
from contextlib import asynccontextmanager, suppress

from anyio import to_thread
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..calc.service import AmbiguousBirthTime, TimeRequired, ambiguity_detail
from ..config import settings
from ..db import dispose
from ..db.session import verify_schema
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


#: Самое большое тело запроса, которое сервис соглашается прочитать, в байтах.
#:
#: **До этого потолка не было вовсе.** Ни один маршрут его не просит — рождение
#: это несколько чисел, сообщение чата ограничено 2000 символами схемой, а
#: `events.meta`/`properties` были `dict` без границы, — но «никто не просит»
#: и «никто не может» это разные вещи: тело буферизуется до того, как pydantic
#: скажет «слишком большое», так что 12-мегабайтный JSON занимал память воркера
#: целиком по пути к 422. 256 КБ — с запасом на порядок больше самого крупного
#: честного тела и всё ещё несоизмеримо меньше того, чем можно занять память.
MAX_REQUEST_BODY_BYTES = 256 * 1024


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


#: Сколько ждать фоновые ходы беседы при остановке процесса, в секундах.
#:
#: **Число выбрано от `graceful_timeout`, а не от длины генерации.**
#: `gunicorn.conf.py` даёт воркеру 120 секунд на то, чтобы уйти по-хорошему, и
#: после них присылает SIGKILL. Всё, что здесь ждётся дольше, ждётся зря: нас
#: убьют посреди ожидания, и оплаченный ход всё равно не допишется. Сто секунд
#: оставляют двадцать на всё остальное закрытие — пул базы, HTTP-клиенты,
#: последние ответы, — и на то, чтобы отказ успел попасть в лог.
#:
#: Кого ждём: `readings._STREAM_TURNS` — задачи, которые дописывают ход беседы
#: после того, как клиент ушёл (там же довод, почему их не отменяют). При
#: выкладке процесс уходил, не дождавшись их: генерация состоялась, за неё
#: выставлен счёт, а `session_scope` внутри задачи получил `CancelledError` и
#: откатил и расход, и списанный вопрос, и сам ответ. То есть заплатили мы, а
#: человек не получил ничего — и месячный потолок этого не увидел.
STREAM_TURN_GRACE_SECONDS = 100.0


def _pending_turns() -> set:
    """Фоновые ходы беседы, которых стоит дождаться. Пустое — тоже ответ.

    Источник один — `deps.STREAM_TURNS`. Здесь недолго стояло два: реестр и
    приватное множество `readings._STREAM_TURNS`, прочитанное через `getattr`,
    пока роутер на реестр не переехал. Второй источник снят вместе с причиной, и
    снят намеренно, а не оставлен «на всякий случай»: `getattr` с запасным
    пустым значением молча превращает ошибку в «ждать нечего», а «ждать нечего»
    здесь означает «оплаченные ответы потеряны». Ошибку импорта лучше увидеть
    один раз при запуске, чем не увидеть ни разу при остановке.
    """
    from . import deps

    return deps.STREAM_TURNS.pending()


async def _drain_stream_turns(seconds: float = STREAM_TURN_GRACE_SECONDS) -> None:
    """Дать недописанным ходам беседы кончиться. Не дольше, чем нам самим дано."""
    pending = _pending_turns()
    if not pending:
        return

    log.warning("waiting for %d paid conversation turn(s) to finish", len(pending))
    done, still_running = await asyncio.wait(pending, timeout=seconds)
    if still_running:
        # Не отменяем: отмена — это ровно тот откат, от которого мы уходим.
        # Пусть их снимет SIGKILL, а в логе останется, за что именно человеку
        # придётся извиняться.
        log.error(
            "%d conversation turn(s) were still writing after %.0fs and the "
            "process is going anyway — those answers are paid for and lost",
            len(still_running), seconds,
        )
    else:
        log.warning("all %d conversation turn(s) finished", len(done))


async def close_http_clients() -> None:
    """Отпустить соединения, которые процесс держал открытыми между запросами.

    Их два, и оба появились в один день по одной причине: клиент, создаваемый
    на каждый вызов, — это TLS-рукопожатие на каждый вызов. Общий клиент живёт
    сколько процесс, а значит его надо закрыть, когда процесс уходит: `httpx`
    без `aclose` оставляет открытые сокеты, и воркер, снятый по SIGTERM,
    оставил бы их вендору как полуоткрытые соединения.

    Ошибки проглатываются каждым из двух по отдельности: остановка, упавшая на
    закрытии клиента, — это `dispose()` пула базы, который не случился.
    """
    from ..ai.provider import close_provider
    from ..billing import http as billing_http

    for name, close in (("billing", billing_http.aclose), ("model", close_provider)):
        try:
            await close()
        except Exception as exc:  # noqa: BLE001 — см. докстринг
            log.info("closing the %s http client: %s", name, exc)


class MaxBodySize:
    """ASGI-обёртка: отказать телу больше потолка, не забуферив его целиком.

    Два края одной дыры, и закрыть надо оба. Клиент с честным `Content-Length`
    отсекается **до** первого прочитанного байта — 413, приложение не
    запускается. Клиент без длины (chunked) считается по мере чтения: как только
    накоплено больше потолка, поток обрывается пустым `more_body=False`, тело
    приходит усечённым, и разбор упирается в 422 — память при этом ограничена
    потолком, а не размером того, что прислали. Определён здесь, а не в
    отдельном модуле: это часть сборки приложения, как и CORS ниже.
    """

    def __init__(self, app, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        for name, value in scope.get("headers", ()):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = None
                if declared is not None and declared > self.max_bytes:
                    return await self._too_large(send)
                break

        received = 0
        over = False

        async def limited_receive():
            nonlocal received, over
            message = await receive()
            if message["type"] == "http.request" and not over:
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # Обрываем тело здесь: приложение получит усечённый JSON и
                    # ответит 422, а память не вырастет за потолок.
                    over = True
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        return await self.app(scope, limited_receive, send)

    @staticmethod
    async def _too_large(send) -> None:
        await send({
            # 413 by number: Starlette renamed the constant (…_REQUEST_ENTITY_…
            # → …_CONTENT_…) and deprecated the old name, the same reason the
            # routers spell 422 as a number rather than pin a version over it.
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({
            "type": "http.response.body",
            "body": b'{"error":"request_too_large"}',
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = settings()
    # Refuses to boot a production process whose session tokens would be
    # forgeable. Better a failed deploy than a quiet one.
    config.check_production_ready()
    # **Схему здесь только проверяют.** Создавал её раньше каждый воркер, и на
    # восьми процессах это восемь одновременных `CREATE INDEX` по одной базе в
    # секунду выкладки. Теперь её приводит в порядок один шаг деплоя
    # (`python -m tools.migrate`, `docs/DEPLOY.md §4`), а процесс, поднявшийся
    # раньше него, обязан не подняться вовсе: тихо стартовать на базе без
    # колонки значит отдать первый же платный запрос пятисоткой.
    await verify_schema()

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
    # Порядок здесь важен и стоил разбора: сперва дописать оплаченные ходы,
    # потом закрывать то, чем они пишут. Закрытый пул базы или закрытый
    # HTTP-клиент посреди хода — это тот же потерянный ответ, только с более
    # запутанной трассировкой.
    await _drain_stream_turns()
    await close_http_clients()
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

    # Потолок размера тела стоит **снаружи** CORS. Starlette исполняет
    # добавленное последним первым, поэтому он идёт после CORS: огромное тело
    # надо отсечь до всякой другой работы, а отказ 413 не нуждается в
    # CORS-заголовках — его читает не браузерный fetch, а тот, кто пытается
    # занять память воркера.
    app.add_middleware(MaxBodySize, max_bytes=MAX_REQUEST_BODY_BYTES)

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

    @app.exception_handler(RequestValidationError)
    async def _unprocessable(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Тот же ответ, что и по умолчанию у FastAPI (`{"detail": [...]}`, 422),
        # но с одной защитой. FastAPI кладёт отвергнутое значение обратно в тело
        # ошибки полем `input`; для широты `NaN` или долготы `Infinity` — а это
        # валидный вход питоновского json-парсера, но не JSON по спецификации —
        # рендер ответа идёт через `json.dumps(allow_nan=False)` и падает, и
        # чистый 422 оборачивался 500 на сериализации собственного отказа.
        # Найдено аудитом 20.08.2026: `POST /v1/profiles` с `latitude: NaN`.
        # Диапазон значение и так отвергает — лечим только его отголосок.
        return JSONResponse(
            status_code=422,
            content={"detail": _fold_nonfinite(jsonable_encoder(exc.errors()))},
        )

    return app


def _fold_nonfinite(value):
    """Свернуть не-конечные float к их тексту («nan»/«inf»/«-inf»).

    Рекурсивно, потому что отвергнутое значение живёт в `input` внутри списка
    словарей `exc.errors()`, а не на поверхности.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, dict):
        return {key: _fold_nonfinite(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_fold_nonfinite(item) for item in value]
    return value


app = create_app()
