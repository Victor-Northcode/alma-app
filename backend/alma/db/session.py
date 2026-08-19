"""Engine, session factory, and the small amount of schema management we need.

SQLite in development, Postgres in production, one URL apart. The only place
the difference shows is the pragma below: SQLite does not enforce foreign
keys unless asked, which means `ondelete="CASCADE"` silently does nothing and
a deletion test passes locally while leaving orphans in production.

**Здесь же живёт правило «соединение не держат, пока думает модель».**
`get_session` отдаёт сессию на весь запрос, поэтому первый же SELECT в
`api/deps.visitor` занимает соединение до самого ответа, — а между ними у
генерирующих роутов лежит вызов модели на десятки секунд. Разрывают это два
куска ниже: явные числа пула и `SessionReleased`, зависимость, которая отдаёт
соединение запроса пулу прежде, чем тело роута начнёт работу.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..config import settings
from .models import Base

_engine: AsyncEngine | None = None
_factory: async_sessionmaker[AsyncSession] | None = None


#: Сколько соединений один воркер держит постоянно.
#:
#: **Умолчание было потолком, и потолок был 15.** SQLAlchemy 2.0 даёт
#: `pool_size=5` плюс `max_overflow=10` и `pool_timeout=30`. Замерено на этом
#: коде (пятнадцать одновременных `POST /v1/readings` с задержанной моделью):
#: занято ровно 15 соединений, а шестнадцатый запрос — `GET
#: /v1/billing/catalogue`, самый дешёвый в продукте, — ждал 30.0 секунды и
#: кончился `TimeoutError: QueuePool limit of size 5 overflow 10 reached`, то
#: есть 500 без объяснения. Пул общий, поэтому дорогие пути убивали дешёвые.
#:
#: Двадцать, а не пятнадцать и не сто. Считать надо от числа воркеров, а не от
#: числа пользователей: соединение теперь занято долями секунды на запрос, а не
#: на всю генерацию, так что двадцати хватает на сотни одновременных запросов
#: одного воркера. Верхняя граница — `max_connections` у Postgres, по умолчанию
#: 100 с тремя зарезервированными за суперпользователем: три воркера по
#: 20 + 10 = 90 помещаются, четыре по 30 — уже нет. Больше четырёх воркеров на
#: одну базу означает pgbouncer, а не бо́льшие числа здесь.
POOL_SIZE = 20

#: Запас на всплеск сверх постоянного пула. Держится не дольше, чем нужен:
#: overflow-соединения закрываются, как только очередь рассосалась.
MAX_OVERFLOW = 10

#: Сколько ждать свободного соединения. Десять секунд, а не тридцать: после
#: разрыва сессии на границе генерации соединение занято десятками
#: миллисекунд, и очередь длиной в десять секунд означает не нагрузку, а
#: поломку. Быстрый честный отказ лучше, чем полминуты тишины у клиента,
#: который к тому моменту уже успел переспросить.
POOL_TIMEOUT = 10

#: Возраст, после которого соединение переоткрывается. Полчаса — короче любого
#: типового простоя, который рвут между нами и базой: pgbouncer
#: `server_idle_timeout` и NAT у облачных провайдеров обычно час.
POOL_RECYCLE = 1800

#: Серверные таймауты Postgres, в миллисекундах. **Только для asyncpg** — на
#: SQLite таких параметров нет, и `connect_args` с ними роняет подключение.
#:
#: Это вторая линия за тем же самым: пул больше не кончается от долгой
#: транзакции, а эти три следят, чтобы долгой транзакции вовсе не заводилось.
#: `statement_timeout` — 15 с: ни один запрос продукта не длится и секунды,
#: пятнадцать это «что-то пошло не так», а не «сегодня медленно».
#: `lock_timeout` — 3 с: ждать блокировку дольше трёх секунд означает драку за
#: одну строку, и лучше ответить 500 одному, чем собрать очередь.
#: `idle_in_transaction_session_timeout` — 30 с: транзакция, простоявшая
#: открытой полминуты, после разрыва сессии на границе генерации означает
#: утечку, а не работу. Это ровно тот случай, который аудит и нашёл: старый код
#: держал такую транзакцию 10–40 секунд на каждой генерации.
ASYNCPG_SERVER_SETTINGS = {
    "statement_timeout": "15000",
    "lock_timeout": "3000",
    "idle_in_transaction_session_timeout": "30000",
}


def engine_options(url: str) -> dict:
    """Что передаётся в `create_async_engine` для этого URL.

    Отдельной функцией, потому что решение здесь ветвится по драйверу и это
    ровно та ветка, которую надо уметь проверить тестом, не поднимая Postgres:
    серверные таймауты обязаны появиться на asyncpg и обязаны **не** появиться
    на SQLite, где они роняют подключение при первом же connect.
    """
    options: dict = {
        "pool_size": POOL_SIZE,
        "max_overflow": MAX_OVERFLOW,
        "pool_timeout": POOL_TIMEOUT,
        "pool_recycle": POOL_RECYCLE,
        # **Цена разреза, названная вслух.** `pool_pre_ping` шлёт `SELECT 1` на
        # каждом взятии соединения из пула, а взятий стало больше: генерация
        # раньше брала соединение один раз на запрос, теперь — три-четыре раза
        # по одной короткой транзакции. Это три-четыре лишних round-trip'а на
        # запрос, доли миллисекунды каждый, против генерации в 10–40 секунд.
        # Обмен очевидный, и он уже был выбран до этой правки — строка стояла
        # здесь и раньше.
        "pool_pre_ping": True,
    }
    if "asyncpg" in url:
        # `server_settings`, а не голые kwargs: asyncpg принимает так любой
        # GUC, а `statement_timeout=` как параметр `connect()` не понимает
        # вовсе. Ветка по драйверу обязательна — aiosqlite на этих ключах
        # падает при первом же подключении.
        options["connect_args"] = {"server_settings": dict(ASYNCPG_SERVER_SETTINGS)}
    elif url.startswith("sqlite") and ":memory:" in url:
        # `:memory:` берёт `StaticPool`, которому размеры пула не нужны и
        # запрещены. В продукте такой URL не встречается, но `dispose()` и
        # тесты могут привести сюда.
        return {}
    return options


def engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = settings().database_url
        if url.startswith("sqlite"):
            path = url.split("///")[-1]
            if path and path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)

        _engine = create_async_engine(
            url, echo=False, future=True, **engine_options(url)
        )

        if url.startswith("sqlite"):
            @event.listens_for(_engine.sync_engine, "connect")
            def _sqlite_pragmas(connection, _record):  # pragma: no cover - driver hook
                cursor = connection.cursor()
                # Without this, ondelete="CASCADE" is decoration and deleting
                # a user leaves their profiles behind.
                cursor.execute("PRAGMA foreign_keys=ON")
                # **Write-ahead logging, and a client is what made it necessary.**
                #
                # In SQLite's default rollback-journal mode a writer takes an
                # exclusive lock on the whole database and every reader waits;
                # with `timeout=0` the waiters do not wait, they fail. The iOS
                # app opens Today with four requests at once — transits, natal,
                # synthesis and the free transits chapter — and each of them
                # touches `UPDATE user SET last_seen_at`, so two of the four came
                # back "database is locked" on a cold launch. That is not a
                # hypothetical about a busy server: it is what the first screen
                # of the product did, every time, on the machine it was built on.
                #
                # WAL lets readers run against a snapshot while one writer
                # appends, which is exactly this shape of traffic. The five-second
                # busy timeout covers the remaining case — two writers — by
                # waiting rather than failing, which is what a person on a phone
                # would prefer over a retry button.
                #
                # This is a development convenience and does not decide the
                # production question. SQLite has one writer whatever the journal
                # mode; a deployment serving real traffic wants Postgres, and
                # `ALMA_DATABASE_URL` is what points at one.
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()

    return _engine


def session_factory() -> async_sessionmaker[AsyncSession]:
    global _factory
    if _factory is None:
        _factory = async_sessionmaker(engine(), expire_on_commit=False, class_=AsyncSession)
    return _factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """A transaction that commits on success and rolls back on anything else."""
    async with session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency form of `session_scope`."""
    async with session_scope() as session:
        yield session


#: Та же зависимость, что `api.deps.SessionDep`, и намеренно тот же объект
#: `get_session`: FastAPI кэширует зависимость по функции, поэтому оба имени
#: приводят к одной сессии внутри одного запроса. Копия живёт здесь, чтобы
#: `release_request_session` ниже не тянуло `api.deps`, который сам импортирует
#: этот модуль.
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def release_request_session(session: SessionDep) -> None:
    """Отдать соединение запроса пулу до того, как роут пойдёт звать модель.

    **Убрать `SessionDep` из подписи роута — необходимо и недостаточно, и это
    стоило замера.** Соединение занимает не роут, а зависимость: `visitor`
    (`api/deps.py`) делает SELECT по токену на КАЖДОМ запросе, а FastAPI держит
    yield-зависимость открытой до конца ответа. Роут, зависящий только от
    `CurrentUser`, всё равно показывает `pool.checkedout() == 1` внутри своего
    тела — измерено; так что генерация на сорок секунд держала бы соединение и
    без единого упоминания сессии в подписи.

    `commit()` — это то, чем `AsyncSession` возвращает соединение в пул.
    Транзакция зависимости к этому моменту содержит ровно то, что она и должна
    была сохранить: `accounts.touch` (не чаще раза в час) и, для нового гостя,
    саму строку аккаунта. Раньше их коммитил `session_scope` в конце запроса,
    теперь — эта строка; сохраняется то же самое, просто раньше.

    Ставится **последней** в подписи роута: зависимости решаются в порядке
    параметров, и отпускать соединение надо после `CurrentUser`, а не до.
    Порядок стережёт тест
    `test_generation_holds_no_pool_connection` — он падает, если эта
    зависимость уедет вверх.

    Дальше роут работает короткими `session_scope`, и между ними соединения у
    него нет.
    """
    await session.commit()


#: «Соединение запроса возвращено пулу». Значение всегда `None` — важен побочный
#: эффект, а не оно.
SessionReleased = Annotated[None, Depends(release_request_session)]


async def create_all() -> None:
    """Create any missing tables, then any missing columns and indexes.

    The second half is not decoration. `Base.metadata.create_all` creates
    tables and has no opinion about one that already exists, so on its own it
    leaves any database that predates a new column unqueryable — and says
    nothing about it. `migrate.reconcile` closes exactly that gap and refuses
    loudly at anything wider than adding a column or an index. Both halves are
    no-ops on a database that is already current, so this is safe on every
    boot; see `migrate.py` for why it is a placeholder rather than a tool.
    """
    from .migrate import reconcile

    async with engine().begin() as connection:
        # **Схема живёт вне `statement_timeout`, и это не поблажка.** Пятнадцать
        # секунд — потолок для запроса из продукта; `CREATE INDEX` по таблице с
        # миллионом строк укладывается в них не всегда, а таймаут на этом месте
        # означает воркер, который не поднимается. Снимается только на эту
        # транзакцию (`SET LOCAL`) и только на Postgres.
        #
        # `reconcile()` ниже открывает своё соединение и под этими потолками
        # остаётся: он добавляет колонки (в Postgres 11+ это мгновенно) и
        # индексы с `if_not_exists`. Индекс по большой таблице упрётся — и
        # упереться там правильнее, чем молча держать таблицу под блокировкой
        # весь деплой; `lock_timeout` в три секунды сказал бы то же самое.
        if connection.dialect.name == "postgresql":
            await connection.execute(text("SET LOCAL statement_timeout = 0"))
            await connection.execute(text("SET LOCAL lock_timeout = 0"))
        await connection.run_sync(Base.metadata.create_all)
    await reconcile()


async def drop_all() -> None:
    async with engine().begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


async def healthy() -> bool:
    try:
        async with session_factory()() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def dispose() -> None:
    global _engine, _factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _factory = None
