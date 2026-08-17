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

**What "refused loudly" does and does not cover.** A column it cannot add
raises. A **rename or a drop** cannot raise, because from here the two are
indistinguishable from a fresh column plus an old one nobody mentioned: the
database keeps the old column with every row's data in it, the new one arrives
empty, and both are legal. So those are *named* instead — one warning at boot
listing every column the database holds and the models do not declare. That is
the honest limit of this module. It will not tell you which of a rename, a drop
or an older deploy you are looking at, and it will not move a single value
between them; it only makes sure the half-finished shape is written down
somewhere on the morning it happens rather than found by whoever is on the
incident an hour later.

**A real tool is still owed**, and it is a separate piece of work rather than a
larger version of this file: it needs versioned revisions, an `alembic_version`
row stamped onto every database that already ran, a test suite that builds its
databases by migrating rather than by `create_all`, and — because this product
deploys on SQLite — batch table rebuilds for anything that changes a column in
place. Every one of those is a decision about live customer rows.

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


def _reconcile(connection: Connection) -> tuple[list[str], list[str]]:
    """Add every declared-but-absent column and index.

    Returns what it did, and what it found and deliberately did not touch.
    """
    inspector = inspect(connection)
    live_tables = set(inspector.get_table_names())
    applied: list[str] = []
    undeclared: list[str] = []

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

        # Read before anything else, and never acted on. This is the shape a
        # rename leaves: the new column is added above, the old one keeps every
        # row's data, and both are perfectly legal to the database. Naming it is
        # all this module is allowed to do — moving the values is the decision
        # it exists to refuse. Harmless in itself (SQLAlchemy names its columns
        # in every statement), which is exactly why it can sit there unnoticed
        # until somebody counts the rows in the empty one.
        undeclared.extend(
            f"{table.name}.{name}"
            for name in sorted(present - {column.name for column in table.columns})
        )

        # Indexes come after the columns they cover. An index over a column
        # added in this same pass is fine; an index over a column that was
        # refused above never runs, because the refusal raised.
        known = {index["name"] for index in inspector.get_indexes(table.name)}
        for index in table.indexes:
            if index.name in known:
                continue
            connection.execute(CreateIndex(index, if_not_exists=True))
            applied.append(f"CREATE INDEX {index.name} ON {table.name}")

    return applied, undeclared


async def reconcile() -> list[str]:
    """Bring the live schema up to the models. Safe to run on every boot.

    Returns the statements it ran so the caller can log them: a schema change
    that happens silently is a schema change nobody can correlate with the
    incident it caused an hour later.

    The undeclared columns are logged rather than returned, and not raised.
    Raising would take a healthy deployment down over a column that harms
    nothing — a rolling deploy has this shape for as long as one host is still
    on the old build — and the caller is `create_all`, on the boot path.
    """
    from .session import engine

    async with engine().begin() as connection:
        applied, undeclared = await connection.run_sync(_reconcile)
    for statement in applied:
        log.warning("schema: %s", statement)
    if undeclared:
        log.warning(
            "schema: %d column(s) exist in the database and in no model, left "
            "untouched with whatever is in them: %s. If a model was renamed, "
            "the new column is empty and this one holds the data — moving it is "
            "a decision this module is not allowed to make.",
            len(undeclared),
            ", ".join(undeclared),
        )
    return applied
