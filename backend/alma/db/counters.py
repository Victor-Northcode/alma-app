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


async def bump_flag(
    session: AsyncSession,
    *,
    row_id: str,
    user_id: str,
    metric: str,
    day: date | None = None,
) -> int:
    """Прибавить единицу к строке-флагу с заданным `id` и вернуть новый счёт.

    Для счётчиков «раз и навсегда», чей ключ **не зависит от календарного дня**:
    единственный даунселл-оффер за всю жизнь аккаунта (`billing.declined`).
    `id` задаётся целиком вызывающим (там он `{user_id}:downsell`), а `day` в
    строке — только отметка времени, не часть ключа, поэтому «раз и навсегда» не
    превращается в «раз в день».

    Отдельно от `add`, который собирает `id` из `counter_id` (то есть *с* днём):
    смешать их значило бы читать одну строку, а писать в другую. Приём тот же —
    `INSERT … ON CONFLICT DO UPDATE SET count = count + 1 RETURNING count`, без
    окна между чтением и записью: два одновременных «закрыл чекаут» больше не
    видят оба нуль и не отдают оба оффер (BUG-006, аудит 29.08.2026).
    """
    insert = _insert(session)
    when = day or date.today()
    statement = (
        insert(UsageCounter)
        .values(id=row_id, user_id=user_id, day=when, metric=metric, count=1, amount=0.0)
        .on_conflict_do_update(
            index_elements=[UsageCounter.id],
            set_={"count": UsageCounter.count + 1},
        )
        .returning(UsageCounter.count)
    )
    return int((await session.execute(statement)).scalar_one() or 0)


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
#
# **Здесь стоял `charge_and_check_month`, и он снят как невостребованный.**
#
# Он писал расход, потом читал месячную сумму и отказывал, если она перевалила
# потолок, — и довод был верный: порядок «сначала записать, потом посмотреть»
# закрывает гонку, которую «прочитать, сравнить, много позже записать» не
# закрывает. Беда была в другом: **его не звал никто**. Живой месячный потолок —
# `ai/cost.guard_month`, и он остался тем, чем был. То есть в сервисе лежал
# примитив, объявлявший гонку закрытой, при живой гонке в двух шагах от него;
# это хуже, чем отсутствие примитива, потому что читается как сделанная работа.
#
# Почему потолок не переведён на него, а примитив снят. Месячный потолок — это
# **предохранитель на наш расход**, а не обещание человеку: «мы потратили
# столько, сколько этот тариф стоит». Проверять его до вызова можно только по
# оценке — сколько вызов будет стоить, известно после. Значит настоящих
# вариантов два: сравнивать оценку (как сейчас) или **резервировать** её строкой
# и потом уточнять до факта.
#
# Резерв закрывает гонку полностью и стоит вот чего: незакрытая бронь —
# процесс убит посреди генерации, ветка отказа без возврата — навсегда делает
# аккаунт дороже, чем он был, а предохранитель, ошибающийся в эту сторону,
# отрезает **платящего подписчика**. Цена нерешения меряется иначе: одновременные
# вызовы читают одну сумму и все проходят, то есть перелёт равен
# «одновременность × стоимость вызова» — центы против долларового потолка,
# один раз за месяц, и следующий запрос уже видит правду.
#
# Правду он видит с тех пор, как `readings._spend` пишет одним запросом: до
# этого книга **теряла** расход при одновременной записи, и вот это делало
# предохранитель неработающим по-настоящему — он считал нас дешевле, чем мы
# есть, ровно под той нагрузкой, ради которой поставлен. Эта половина починена.
# Резерв — решение владельца, а не недосмотр, и он записан в `docs/REMAINING.md`.


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
    "bump_flag",
    "counter_id",
    "hit_window",
    "refund",
    "spend_and_check",
    "sweep_windows",
]
