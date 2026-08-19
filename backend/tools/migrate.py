"""Привести базу к тому, что ожидает код. Шаг выкладки, а не шаг старта.

    cd /srv/alma/backend
    python -m tools.migrate            # создать недостающее и уйти
    python -m tools.migrate --check    # только сказать, чего не хватает

**Зачем отдельная команда.** До 19 августа 2026 это делал каждый рабочий
процесс в своём `lifespan`. На одной машине с одним процессом разницы не было;
на четырёх ядрах `gunicorn.conf.py` поднимает восемь воркеров, и на выкладке
восемь процессов в одну секунду выполняли по базе `CREATE TABLE`,
`CREATE INDEX` и `ALTER TABLE ADD COLUMN`. Postgres берёт под это блокировку
каталога, а `lock_timeout` у нас три секунды (`db/session.ASYNCPG_SERVER_SETTINGS`) —
то есть семь воркеров из восьми имели полное право не встать, и увидели бы мы
это как «выкладка прошла, сервис лежит».

Один процесс делает работу, восемь только проверяют её результат
(`db.session.verify_schema`) и отказываются подниматься, если её не сделали.

**Что она умеет — ровно то же, что умел старт**: создать недостающие таблицы,
дописать недостающие колонки и индексы. Она ничего не переименовывает, ничего
не удаляет и ничего не переносит; всё, что шире, `db/migrate.py` отказывает
вслух и печатает DDL, который надо выполнить руками. Настоящий инструмент с
версиями ревизий всё ещё не написан — довод в докстринге того же файла.

Код возврата: 0 — схема на месте, 1 — не на месте (после `--check`) или
миграцию выполнить не удалось. Ровно поэтому `--check` годится для проверки
после выкладки одной строкой в скрипте.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

log = logging.getLogger("alma.tools.migrate")


async def _migrate() -> int:
    from alma.db import session as db

    try:
        # `create_all` — это create + reconcile: первая половина заводит
        # таблицы, вторая дописывает колонки и индексы. Здесь они по-прежнему
        # вместе, потому что порядок между ними важен, а разделять их некому:
        # обе половины теперь исполняет один процесс.
        await db.create_all()
        # Проверка сразу после, тем же кодом, что читают воркеры. Иначе
        # «миграция прошла» и «воркер поднимется» — два разных утверждения, и
        # узнают об этом на выкладке.
        await db.verify_schema()
    except Exception as exc:  # noqa: BLE001 — код возврата важнее трассировки
        log.error("migration failed: %s", exc)
        return 1
    finally:
        await db.dispose()
    print("schema is up to date")
    return 0


async def _check() -> int:
    from alma.db import session as db

    try:
        await db.verify_schema()
    except db.SchemaNotReady as exc:
        print(str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001 — база недоступна, это тоже «нет»
        print(f"could not read the schema: {exc}")
        return 1
    finally:
        await db.dispose()
    print("schema is up to date")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="ничего не менять, только сказать, чего не хватает (код 1, если не хватает)",
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return asyncio.run(_check() if arguments.check else _migrate())


if __name__ == "__main__":  # pragma: no cover - точка входа выкладки
    raise SystemExit(main())
