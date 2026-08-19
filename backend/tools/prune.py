"""Растущие таблицы: что удаляется, когда и по чьему обещанию.

    cd /srv/alma/backend
    python -m tools.prune              # удалить
    python -m tools.prune --dry-run    # только посчитать, ничего не трогая

**Пять таблиц, которые растут и которые никто не уменьшает.** Ни одна из них
не имеет потолка по построению: события воронки пишутся на каждый шаг каждого
посетителя, `webhook_event` — на каждую доставку от каждой кассы, `rate_window`
— на каждый различимый источник за каждое окно, `magic_link` — на каждый
запрос письма входа, `calc_cache` — на каждый уникальный расчёт. На десяти
тысячах пользователей это не «когда-нибудь», а первые же месяцы: одних только
окон ограничителей получается по строке на посетителя в час.

**Сроки взяты из обещаний продукта, а не выбраны здесь.** Это правило, а не
оговорка: число, живущее в коде и на privacy-странице по отдельности, — это
обещание, которое никто не может проверить. Поэтому:

* **События воронки — 180 дней.** `funnel.PURGE_AFTER_DAYS`, оно же
  `FUNNEL_RETENTION_DAYS` в `src/lib/legal.ts`, оно же напечатано на
  privacy-странице («deleted after 180 days whether or not there is an
  account»). Здесь оно не переписано, а вызвано: `funnel.purge` — та же
  функция, которую зовёт `python -m alma.funnel --purge`, и второй реализации у
  этого обещания быть не должно.
* **Доставки вебхуков — те же 180 дней.** Своего срока у них нигде не
  напечатано, поэтому взято число воронки — не потому, что оно «единственное,
  что продукт сказал вслух» (так здесь было написано, и это неправда:
  privacy-страница называет и 90, и 60 на пуш-токен, и 30 на окно резервных
  копий), а чтобы в системе не заводился четвёртый срок хранения без нужды.
  Персональные данные в теле доставки действительно бывают, но не у всех касс:
  Apple и Google Play присылают покупку без адреса покупателя
  (`googleplay.py`, `appstore.py` ставят `buyer_email=None`), а dodo и paddle —
  с адресом и страной. То есть срок нужен ради веб-касс, и это ровно тот
  случай, когда короче выдумывать не стоит, а длиннее — незачем.
  Идемпотентность не страдает: повторы кассы измеряются днями (Apple —
  несколько суток, Play RTDN — семь, Paddle — трое), а не полугодиями.

* **Ссылки входа — до конца своего срока жизни.** `magic_link` хранит почтовый
  адрес **открытым текстом** и не выметалась ничем: единственный `delete` по
  ней жил в удалении аккаунта, то есть адрес человека, который запросил письмо
  и аккаунт так и не завёл, оставался у нас навсегда. Строка после истечения не
  читается ничем — `consume_magic_link` отказывает и просроченной, и
  использованной, — поэтому удалять её безопасно и нечего терять. Это самая
  тихая из четырёх находок: таблица не «растёт», она копит адреса.
* **Окна ограничителей — до конца своего окна.** Строка живёт час или сутки по
  построению (`RateWindow.expires_at`) и после этого не читается ничем. Это
  единственная здешняя чистка, которая не про приватность, а про то, что мусор
  нельзя копить вечно.
* **Кэш расчётов — 180 дней с записи.** Персональных данных в нём нет (ключ —
  содержимое расчёта), поэтому срок здесь — вопрос места, а не обещания; взято
  то же число, чтобы в системе не было третьего срока хранения. **Сегодня эта
  таблица пуста и растёт со скоростью ноль**: `CalcCacheEntry` объявлена, и
  никто в неё не пишет — кэш расчётов живёт в памяти процесса
  (`api/cache.result_cache`). Чистка здесь стоит не потому, что таблица растёт,
  а потому, что в тот день, когда кто-нибудь начнёт в неё писать, единственное,
  чего никто не сделает, — не заведёт чистку.

**Чего эта команда не делает — и это решение владельца, а не упущение.**
Беседы (`chat_thread`, `chat_message`) и главы (`reading`) здесь не трогаются
вовсе, хотя они и есть самое объёмное из растущего. Privacy-страница обещает
про них ровно одно: «While your account exists» — они живут, пока живёт
аккаунт, и удаляются целиком при его удалении (`accounts.erase`). Любой срок,
введённый здесь, был бы **сокращением напечатанного обещания молча**, а
человек, который вернулся через год перечитать главу, за которую заплатил, —
это тот случай, ради которого главы вообще хранятся, а не генерируются заново.
Если владелец решит иначе, менять надо сперва privacy-страницу и
`src/lib/legal.ts`, и только потом этот файл.

Ставится в расписание — `docs/DEPLOY.md §5`. Раз в сутки; ничего срочного здесь
нет, но пропущенная неделя — это неделя лишних строк, а пропущенный год — это
обещание, которое перестало быть правдой.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

log = logging.getLogger("alma.tools.prune")

#: Сколько хранится доставка вебхука. См. довод в докстринге модуля — число не
#: своё, а то же, что у воронки, и меняться должно вместе с ним.
WEBHOOK_RETENTION_DAYS = 180

#: Сколько хранится запись кэша расчётов. Тоже не своё число, по той же причине.
CALC_CACHE_RETENTION_DAYS = 180


async def _prune(*, dry_run: bool) -> dict[str, int]:
    from sqlalchemy import delete, func, select

    from alma import funnel
    from alma.db import counters
    from alma.db.models import (
        CalcCacheEntry,
        MagicLink,
        RateWindow,
        WebhookEvent,
        utcnow,
    )
    from alma.db.session import session_scope

    now = utcnow()
    counted: dict[str, int] = {}

    async with session_scope() as session:
        # Воронка — через `funnel.purge`, а не своим `delete`: у этого обещания
        # одна реализация, и она там. Она же убирает осиротевшие claim-строки.
        if dry_run:
            counted["funnel events"] = await _count(
                session, select(func.count()).select_from(funnel.Event).where(
                    funnel.Event.created_at < now - timedelta(days=funnel.PURGE_AFTER_DAYS)
                )
            )
        else:
            counted["funnel events"] = await funnel.purge(session)

        webhook_cutoff = now - timedelta(days=WEBHOOK_RETENTION_DAYS)
        if dry_run:
            counted["webhook deliveries"] = await _count(
                session,
                select(func.count()).select_from(WebhookEvent).where(
                    WebhookEvent.received_at < webhook_cutoff
                ),
            )
        else:
            gone = await session.execute(
                delete(WebhookEvent).where(WebhookEvent.received_at < webhook_cutoff)
            )
            counted["webhook deliveries"] = int(gone.rowcount or 0)

        # Ссылки входа: удаляются по истечении, а не по возрасту. Срок жизни
        # ссылки задан при её выдаче, и после него строка не читается ничем
        # (`consume_magic_link` отказывает и просроченной, и использованной) —
        # значит второго срока здесь заводить не надо, надо взять её собственный.
        if dry_run:
            counted["sign-in links"] = await _count(
                session,
                select(func.count()).select_from(MagicLink).where(
                    MagicLink.expires_at < now
                ),
            )
        else:
            gone = await session.execute(
                delete(MagicLink).where(MagicLink.expires_at < now)
            )
            counted["sign-in links"] = int(gone.rowcount or 0)

        if dry_run:
            counted["rate windows"] = await _count(
                session,
                select(func.count()).select_from(RateWindow).where(
                    RateWindow.expires_at < now
                ),
            )
        else:
            counted["rate windows"] = await counters.sweep_windows(session, now=now)

        calc_cutoff = now - timedelta(days=CALC_CACHE_RETENTION_DAYS)
        if dry_run:
            counted["calc cache"] = await _count(
                session,
                select(func.count()).select_from(CalcCacheEntry).where(
                    CalcCacheEntry.created_at < calc_cutoff
                ),
            )
        else:
            gone = await session.execute(
                delete(CalcCacheEntry).where(CalcCacheEntry.created_at < calc_cutoff)
            )
            counted["calc cache"] = int(gone.rowcount or 0)

        if dry_run:
            # Ничего не сохраняем: `session_scope` коммитит на выходе, а
            # считать мы приходили, а не удалять.
            await session.rollback()

    return counted


async def _count(session, statement) -> int:
    return int((await session.execute(statement)).scalar_one() or 0)


def render(counted: dict[str, int], *, dry_run: bool) -> str:
    verb = "would delete" if dry_run else "deleted"
    lines = [f"{verb} {number} {name}" for name, number in counted.items()]
    return "\n".join(lines) or "nothing to do"


async def _run(dry_run: bool) -> int:
    from alma.db.session import dispose

    try:
        counted = await _prune(dry_run=dry_run)
    finally:
        await dispose()
    print(render(counted, dry_run=dry_run))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="посчитать, что удалилось бы, и ничего не удалять",
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return asyncio.run(_run(arguments.dry_run))


if __name__ == "__main__":  # pragma: no cover - точка входа расписания
    raise SystemExit(main())
