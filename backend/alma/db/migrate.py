"""Bringing an existing database up to the schema the code expects.

`create_all` creates missing *tables* and nothing else. It has no opinion
about a table that already exists, so the day a model grows a column, every
database that already ran becomes one the code cannot query — and it fails at
the first `SELECT`, which for this product is the paywall, the hub,
`/v1/account` and the billing webhook, all at once. Nothing warns: `create_all`
returns happily, the process starts, and the first customer sees a 500. The
test suite cannot catch it either, because `conftest` builds every database
from nothing.

That has now happened twice — `Entitlement` grew five columns and `Purchase`
grew two — which is the signal that a real migration tool is overdue. This
module is not that tool and does not pretend to be one. It does exactly one
thing, which is the one thing this project has needed both times:

    **add columns and indexes that the models declare and the database lacks.**

It is deliberately incapable of anything else. It never drops, never renames,
never changes a type and never rewrites data, because those are the operations
that need a person to decide what happens to the rows in between — and a tool
that can do them is a tool somebody will run without reading it. Anything it
cannot express is *refused loudly*, with the DDL to run by hand in the message,
rather than skipped: a migration that silently declines half its work leaves
exactly the state this module exists to prevent.

The wanted schema is read out of `Base.metadata` rather than written down as a
list of ALTER statements. A hand-written list is a list somebody forgets to add
to, and forgetting fails in a way that is indistinguishable from the failure
this module fixes.
"""

from __future__ import annotations

import logging

from sqlalchemy import Table, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.schema import CreateIndex

from .models import Base

log = logging.getLogger("alma.db.migrate")


class SchemaTooOld(RuntimeError):
    """The database needs a change this module is not allowed to make."""


def _add_column_sql(connection: Connection, table: Table, column) -> str:
    """The `ALTER TABLE … ADD COLUMN` for one column, or raise saying why not.

    A NOT NULL column can only be added to a table that already has rows if it
    carries a *server* default: SQLite refuses outright, and Postgres has to be
    told what to put in the rows that already exist. `default=` on the mapping
    is not enough — SQLAlchemy applies that at INSERT and the database has
    never heard of it. So a non-nullable column with no `server_default` is a
    change that needs a person, and this says so instead of guessing.
    """
    type_sql = column.type.compile(connection.dialect)
    statement = f"ALTER TABLE {table.name} ADD COLUMN {column.name} {type_sql}"

    if column.server_default is not None:
        literal = str(column.server_default.arg)
        rendered = literal if literal.lstrip("-").isdigit() else f"'{literal}'"
        return f"{statement} DEFAULT {rendered}"
    if column.nullable:
        return statement
    raise SchemaTooOld(
        f"{table.name}.{column.name} is NOT NULL with no server default, so "
        "there is nothing to put in the rows that already exist. Either give "
        "the model a server_default=, or run the change by hand: "
        f"{statement} DEFAULT <value>;"
    )


def _reconcile(connection: Connection) -> list[str]:
    """Add every declared-but-absent column and index. Returns what it did."""
    inspector = inspect(connection)
    live_tables = set(inspector.get_table_names())
    applied: list[str] = []

    for table in Base.metadata.sorted_tables:
        if table.name not in live_tables:
            # `create_all` runs first and owns this case. A table still missing
            # here is one create_all refused, and inventing it would hide that.
            continue

        present = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue
            statement = _add_column_sql(connection, table, column)
            connection.execute(text(statement))
            applied.append(statement)

        # Indexes come after the columns they cover. An index over a column
        # added in this same pass is fine; an index over a column that was
        # refused above never runs, because the refusal raised.
        known = {index["name"] for index in inspector.get_indexes(table.name)}
        for index in table.indexes:
            if index.name in known:
                continue
            connection.execute(CreateIndex(index, if_not_exists=True))
            applied.append(f"CREATE INDEX {index.name} ON {table.name}")

    return applied


async def reconcile() -> list[str]:
    """Bring the live schema up to the models. Safe to run on every boot.

    Returns the statements it ran so the caller can log them: a schema change
    that happens silently is a schema change nobody can correlate with the
    incident it caused an hour later.
    """
    from .session import engine

    async with engine().begin() as connection:
        applied = await connection.run_sync(_reconcile)
    for statement in applied:
        log.warning("schema: %s", statement)
    return applied
