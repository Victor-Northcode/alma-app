"""Engine, session factory, and the small amount of schema management we need.

SQLite in development, Postgres in production, one URL apart. The only place
the difference shows is the pragma below: SQLite does not enforce foreign
keys unless asked, which means `ondelete="CASCADE"` silently does nothing and
a deletion test passes locally while leaving orphans in production.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

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


def engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = settings().database_url
        if url.startswith("sqlite"):
            path = url.split("///")[-1]
            if path and path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_async_engine(url, echo=False, future=True, pool_pre_ping=True)

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
