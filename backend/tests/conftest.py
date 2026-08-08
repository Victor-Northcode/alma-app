"""Shared fixtures.

Each API test gets its own empty database in a temporary file. Not in-memory:
SQLite's `:memory:` gives every connection its own private database, so an
async pool silently hands different requests different worlds — which shows up
as a test that passes alone and fails in a suite.

The suite is also sealed off from `.env`. `Settings` reads `(".env", ".env.local")`,
so the moment a developer configures a real key the suite starts testing their
machine instead of the code: 59 tests failed the first time a working
`ANTHROPIC_API_KEY` was added, including the one asserting that a *missing* key
produces an honest 503 — it had been passing because the key was absent, not
because the code was right. A test that changes its answer when someone edits an
untracked file is not a test.
"""

from __future__ import annotations

import os

# Before any `alma` import: `Settings.model_config` is evaluated when the class
# is defined, so a fixture setting this later is already too late — the file
# has been read and the developer's key is in the settings object.
os.environ.setdefault("ALMA_SKIP_DOTENV", "1")

import asyncio  # noqa: E402
from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402


def postgres_url() -> str | None:
    """The Postgres the suite was asked to run against, or None for SQLite.

    SQLite stays the default deliberately: it needs no server, the whole suite
    finishes in about fifty seconds on it, and a contributor who has just
    cloned the repository can run it without installing anything. But SQLite is
    *not* what production runs, and it is forgiving in ways Postgres is not —
    it accepts a string where an integer was declared, has no real datetime
    type, and never once complained about a transaction left open after an
    error. Every one of those is a bug that only exists in production.

    So the same suite can be pointed at a real server:

        ALMA_TEST_DATABASE_URL=postgresql+asyncpg://alma@127.0.0.1:5432/alma_test \\
            python -m pytest

    Nothing else changes. The fixtures below ask this function for a URL
    instead of writing a SQLite path, so a test written tomorrow gets Postgres
    coverage for free rather than by remembering to.
    """
    url = os.getenv("ALMA_TEST_DATABASE_URL", "").strip()
    return url or None


def _reset_postgres(url: str) -> None:
    """Empty the target database between tests, the way a tmp file is empty.

    Dropping and recreating `public` rather than the database itself, because
    dropping a database needs a connection to a *different* one and refuses
    while anything is still attached — which, in a suite that disposes engines
    asynchronously, is a race that fails about one run in ten. The schema has
    no such problem: `CASCADE` takes the tables with it and the recreate is a
    single statement.
    """
    import asyncpg

    dsn = url.replace("+asyncpg", "")

    async def wipe() -> None:
        connection = await asyncpg.connect(dsn)
        try:
            await connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        finally:
            await connection.close()

    asyncio.run(wipe())


def run_async(work):
    """Run one coroutine in a private event loop and close the engine with it.

    The synchronous tests below drive async code by calling `asyncio.run` once
    per assertion, which means one process spins up dozens of event loops. That
    is fine on aiosqlite and fatal on asyncpg: `alma.db.session` holds a single
    module-level engine, its pool caches connections, and an asyncpg connection
    is bound to the loop that opened it — reusing one from a loop that has since
    closed raises "got Future attached to a different loop", or worse, hangs.

    Disposing inside the same loop is the fix, and it costs a connection setup
    per call rather than anything structural. No server has this problem: a
    uvicorn worker has exactly one loop for its whole life, which is why the
    pool stays a pool in `session.py` instead of being weakened to a NullPool
    to accommodate a shape only the tests have.
    """
    async def go():
        from alma.db import session as session_module

        try:
            return await work()
        finally:
            await session_module.dispose()

    return asyncio.run(go())


def read_async(work):
    """Read the database from a test body without borrowing the app's engine.

    The `api` fixture's TestClient runs the application on a portal thread with
    an event loop of its own, and every connection the app pooled belongs to
    that loop. A test that then wants to look at the rows — "did the webhook
    write a purchase?" — calls `asyncio.run` on a third loop, and on asyncpg
    that reuse is the same "attached to a different loop" crash as above.

    So this hands the helper a private engine for the duration: same URL, same
    models, its own connection, disposed before the loop closes. It is swapped
    into `alma.db.session` rather than passed in, because the helpers were
    written against `session_factory()` and rewriting twenty of them to take a
    session would be a bigger change than the problem deserves.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from alma.config import settings
    from alma.db import session as session_module

    async def go():
        private = create_async_engine(settings().database_url, future=True)
        saved_engine = session_module._engine
        saved_factory = session_module._factory
        session_module._engine = private
        session_module._factory = async_sessionmaker(
            private, expire_on_commit=False, class_=AsyncSession
        )
        try:
            return await work()
        finally:
            session_module._engine = saved_engine
            session_module._factory = saved_factory
            await private.dispose()

    return asyncio.run(go())


def database_url(tmp_path, name: str) -> str:
    """A URL for an empty database, Postgres if one was configured or SQLite.

    `name` is only used for the SQLite file. On Postgres there is one database
    and it is wiped here, which is why this must be called *after* the previous
    test's engine has been disposed and *before* the next `create_all`.
    """
    url = postgres_url()
    if url:
        _reset_postgres(url)
        return url
    return f"sqlite+aiosqlite:///{tmp_path / name}"


@pytest.fixture(autouse=True)
def _sealed_environment(monkeypatch) -> Iterator[None]:
    """No test sees the developer's `.env`, and none sees their real keys.

    Autouse and unconditional: opting in per test would mean the next test
    written is the one that forgets. Anything a test genuinely needs set, it
    sets itself with `monkeypatch.setenv` after this has run.
    """
    from alma import config as config_module

    for leaked in (
        "ANTHROPIC_API_KEY",
        "RESEND_API_KEY",
        "PADDLE_API_KEY",
        "PADDLE_CLIENT_TOKEN",
        "PADDLE_WEBHOOK_SECRET",
        "DODO_PAYMENTS_API_KEY",
        "DODO_PAYMENTS_WEBHOOK_KEY",
        "ALMA_BILLING_PROVIDER",
        "ALMA_JWT_SECRET",
        "GOOGLE_CLIENT_ID",
        "APPLE_CLIENT_ID",
    ):
        monkeypatch.delenv(leaked, raising=False)
    config_module.settings.cache_clear()
    yield
    config_module.settings.cache_clear()


@pytest.fixture
def api(tmp_path, monkeypatch) -> Iterator:
    """A TestClient against a fresh database and a clean settings cache."""
    from fastapi.testclient import TestClient

    from alma import config as config_module

    from alma.db import session as session_module

    # Dispose before the wipe, not after: on Postgres `database_url` drops the
    # schema, and a pooled connection still holding a table open turns that
    # into a lock wait rather than an empty database.
    asyncio.run(session_module.dispose())

    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "test.db"))
    monkeypatch.setenv("ALMA_ENV", "test")
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()

    from alma.api.app import create_app
    from alma.api.cache import result_cache

    result_cache().clear()

    with TestClient(create_app()) as client:
        yield client

    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


@pytest.fixture
def token(api) -> str:
    """A guest session token — every request needs one, or mints one."""
    response = api.get("/v1/auth/session")
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def auth_headers(token) -> dict:
    return {"Authorization": f"Bearer {token}"}


SOFIA = {
    "birth_date": "1998-03-14",
    "birth_time": "04:20",
    "latitude": 45.4642,
    "longitude": 9.19,
    "timezone": "Europe/Rome",
    "place_label": "Milan, Italy",
    "name": "Sofia Rossi",
}

LUCAS = {
    "birth_date": "1995-07-02",
    "birth_time": "18:05",
    "latitude": -23.5505,
    "longitude": -46.6333,
    "timezone": "America/Sao_Paulo",
    "place_label": "São Paulo, Brazil",
    "name": "Lucas Souza",
}
