"""Счётчики, которые нельзя прочитать-сравнить-записать.

Один приём на весь сервис: **сначала прибавить, потом смотреть на результат**,
и прибавить одним запросом, который база выполняет целиком или не выполняет
вовсе. Всё, что здесь есть, — обёртки над

    INSERT … VALUES … ON CONFLICT (id) DO UPDATE SET count = count + :n
    RETURNING count

то есть над «увеличить и узнать, сколько стало» без окна между чтением и
записью. Поддерживается и Postgres, и SQLite (3.35+, у нас 3.50); синтаксис у
них разный ровно в имени конструктора, поэтому ветка по диалекту одна и она
здесь.

**Почему это отдельный модуль, а не метод рядом с каждым потолком.** До него в
сервисе было три с половиной копии одного и того же кода: `funnel.spend_allowance`,
`readings._count`/`_asked`, `readings._opening_allowance`, `daily.storage`. Все
они читают строку через `session.get`, прибавляют в питоне и полагаются на
`flush`. На одном воркере это почти правда — почти, потому что уже там два
одновременных запроса читают один и тот же ноль. На восьми воркерах это не
правда вовсе: 19 августа 2026 замерено, что двойное нажатие «отправить» на
телефоне проходит обе стены (`_chat_gate` и `_guard_month`) с одним и тем же
нулём в руках, и оплачена при этом одна генерация, а сделано две.

**Порядок «прибавить → проверить», а не «проверить → прибавить».** Он выглядит
странно (мы записываем то, что можем отказать), и он единственный правильный:
при обратном порядке два вызова читают одно значение и оба проходят. Здесь оба
прибавляют, и второй видит своё же увеличение — то есть отказ достаётся ровно
одному из них. Откат записи при отказе делает вызывающий: у HTTP-маршрутов это
происходит само (`session_scope` откатывает транзакцию на исключении), у всех
прочих есть `refund`.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import RateWindow, UsageCounter


class QuotaExceeded(Exception):
    """Потолок выбран. Несёт то, что нужно, чтобы объяснить это человеку."""

    def __init__(self, message: str, *, spent: float, limit: float) -> None:
        super().__init__(message)
        #: Сколько стало **после** этого обращения — то есть с учётом того,
        #: которое сейчас отказывают. Отчёт, а не остаток.
        self.spent = spent
        self.limit = limit


def _insert(session: AsyncSession):
    """Конструктор `INSERT` того диалекта, у которого есть `ON CONFLICT`.

    `sqlalchemy.insert` его не имеет: `on_conflict_do_update` живёт в
    диалектах, и их два. Ветка по имени диалекта, а не по строке URL, потому
    что URL у тестов и у прода разные, а диалект — то, что реально исполняет
    запрос.
    """
    name = session.get_bind().dialect.name
    if name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert


async def add(
    session: AsyncSession,
    *,
    user_id: str,
    day: date,
    metric: str,
    count: int = 0,
    cents: float = 0.0,
) -> tuple[int, float]:
    """Прибавить к счётчику аккаунта и вернуть, сколько стало. Один запрос.

    Возвращает пару `(count, amount)` — оба поля строки после увеличения, даже
    если двигали одно: вызывающему почти всегда нужно и то и другое, а второй
    запрос за соседней колонкой стоил бы ровно столько же, сколько первый.

    Ключ строки собирается здесь и нигде больше. Формула `user:day:metric`
    старше этого модуля (её знают `funnel`, `readings`, `daily/storage`), и
    именно поэтому она вынесена в `counter_id`: строка, собранная на месте с
    другим разделителем, — это второй счётчик под тем же именем.
    """
    insert = _insert(session)
    key = counter_id(user_id, day, metric)
    statement = (
        insert(UsageCounter)
        .values(
            id=key, user_id=user_id, day=day, metric=metric,
            count=count, amount=cents,
        )
        .on_conflict_do_update(
            index_elements=[UsageCounter.id],
            set_={
                "count": UsageCounter.count + count,
                "amount": UsageCounter.amount + cents,
            },
        )
        .returning(UsageCounter.count, UsageCounter.amount)
    )
    row = (await session.execute(statement)).one()
    return int(row[0] or 0), float(row[1] or 0.0)


def counter_id(user_id: str, day: date, metric: str) -> str:
    """Первичный ключ строки `usage_counter`. Одна формула на весь сервис."""
    return f"{user_id}:{day.isoformat()}:{metric}"


async def spend_and_check(
    session: AsyncSession,
    *,
    user_id: str,
    day: date,
    metric: str,
    limit: int,
    count: int = 1,
) -> int:
    """Списать одно обращение и отказать, если после него потолок перейдён.

    **Это тот примитив, ради которого написан модуль.** Одна строка кода на
    месте вызова вместо трёх (`get` → `+= 1` → `flush` → `if`), и без окна
    между ними. Возвращает новое значение счётчика, чтобы вызывающий мог
    показать его человеку («это третий вопрос из трёх»).

    Потолок сравнивается строго: `limit` — сколько **можно**, поэтому отказ
    начинается на `limit + 1`. Так же считали все три места, откуда это
    собрано, и менять смысл числа заодно с механизмом значило бы тихо сдвинуть
    квоту всем.
    """
    spent, _ = await add(
        session, user_id=user_id, day=day, metric=metric, count=count
    )
    if spent > limit:
        raise QuotaExceeded(
            f"{limit} is the allowance for {metric}; this account is at {spent}",
            spent=spent,
            limit=limit,
        )
    return spent


async def refund(
    session: AsyncSession,
    *,
    user_id: str,
    day: date,
    metric: str,
    count: int = 0,
    cents: float = 0.0,
) -> None:
    """Вернуть то, что списали и не потратили.

    Нужен там, где отказ **не** откатывает транзакцию сам: фоновая задача,
    собственный `session_scope`, ход беседы, отменённый после списания. У
    HTTP-маршрута этого не бывает — исключение уносит транзакцию целиком, — но
    полагаться на это в модуле, который зовут отовсюду, нельзя.

    Отдельным именем, а не `add(count=-1)`, ровно затем, чтобы возврат было
    видно в диффе: списание и возврат — разные события, и «минус один» посреди
    кода читается как опечатка.
    """
    await add(
        session, user_id=user_id, day=day, metric=metric,
        count=-count, cents=-cents,
    )


# ── деньги за месяц ────────────────────────────────────────────────────────


async def charge_and_check_month(
    session: AsyncSession,
    *,
    user_id: str,
    cents: float,
    ceiling_dollars: float,
    at: datetime | None = None,
    metric: str = "spend_cents",
) -> float:
    """Записать расход и вернуть месячный итог, отказав, если он перевалил.

    **Два запроса, а не один, и это ограничение базы, а не небрежность.**
    Месячный потолок — это сумма по строкам месяца, а не одна строка; сложить
    её в том же запросе, который пишет сегодняшнюю, умеет только Postgres
    (пишущий CTE), а SQLite не умеет ни пишущих CTE, ни подзапросов в
    `RETURNING`. Ветка «на Postgres один запрос, на SQLite два» означала бы,
    что гонку, которую мы чиним, тесты не видят вовсе: они ходят по SQLite.

    Гонка при этом закрыта, и закрывает её **порядок**, а не число запросов:
    расход записан до того, как сумма прочитана, поэтому два одновременных
    вызова видят сумму, включающую их обоих, и отказ достаётся хотя бы одному.
    Прежний порядок — прочитать сумму, сравнить, много позже записать — давал
    обоим один и тот же ноль.

    Потолок в долларах, а расход в центах: так уже устроен `ai/cost.py`, и
    пересчёт живёт в одном месте — здесь. Сравнивать центы с долларами значит
    ошибиться в сто раз в ту сторону, которая стоит денег.
    """
    from ..ai.cost import month_bounds

    when = (at or datetime.now(timezone.utc)).date()
    await add(session, user_id=user_id, day=when, metric=metric, cents=cents)

    first, following = month_bounds(at)
    total = await session.scalar(
        select(func.sum(UsageCounter.amount)).where(
            UsageCounter.user_id == user_id,
            UsageCounter.metric == metric,
            UsageCounter.day >= first,
            UsageCounter.day < following,
        )
    )
    dollars = (total or 0.0) / 100.0
    if dollars > ceiling_dollars:
        raise QuotaExceeded(
            f"this account has cost ${dollars:.4f} this month against a "
            f"${ceiling_dollars:.2f} ceiling",
            spent=dollars,
            limit=ceiling_dollars,
        )
    return dollars


# ── окна ограничителей на входе ────────────────────────────────────────────


async def hit_window(
    session: AsyncSession,
    *,
    row_id: str,
    expires_at: datetime,
    step: int = 1,
) -> int:
    """Прибавить к общему счёту окна и вернуть, сколько стало. Один запрос.

    Отдельно от `add` выше, потому что таблица другая и ключ другой: здесь нет
    аккаунта, есть отпечаток источника (см. `RateWindow`). Всё остальное — тот
    же приём и по той же причине.
    """
    insert = _insert(session)
    statement = (
        insert(RateWindow)
        .values(id=row_id, expires_at=expires_at, count=step)
        .on_conflict_do_update(
            index_elements=[RateWindow.id],
            set_={"count": RateWindow.count + step},
        )
        .returning(RateWindow.count)
    )
    return int((await session.execute(statement)).scalar_one() or 0)


async def sweep_windows(session: AsyncSession, *, now: datetime) -> int:
    """Удалить окна, которые уже ничего не ограничивают. Возвращает сколько.

    Строк здесь столько, сколько было различимых источников за окно, и они
    никогда не перезаписываются: новое окно — новый первичный ключ. Без этой
    чистки таблица растёт линейно по посетителям и не перестаёт никогда;
    ставит её в расписание `tools/prune.py`, а `docs/DEPLOY.md §5` — в cron.
    """
    result = await session.execute(
        delete(RateWindow).where(RateWindow.expires_at < now)
    )
    return int(result.rowcount or 0)


__all__ = [
    "QuotaExceeded",
    "add",
    "charge_and_check_month",
    "counter_id",
    "hit_window",
    "refund",
    "spend_and_check",
    "sweep_windows",
]
