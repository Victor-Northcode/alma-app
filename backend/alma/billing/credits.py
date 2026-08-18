"""Одна проверка пары в месяц, включённая в подписку.

Подписка v3 обещает «всё» и одну новую совместимость в расчётный период. Это
единственная строка полки, где «всё» имеет границу, и граница честная: отчёт
про пару — самая дорогая генерация в продукте (~26¢ сильной моделью), и
подписка за $9.99 с потолком расходов $4.50 не может оплачивать их
неограниченно. Вторая проверка в том же периоде продаётся за $4.99, как и всем
остальным.

**Что здесь считается, а что нет.** Кредит — про *создание нового* отчёта, а не
про чтение уже написанного. Уже открытая пара остаётся открытой навсегда, в том
числе после отмены подписки: за неё заплачено — деньгами или кредитом, — и
забирать прочитанное нельзя. Поэтому потраченный кредит материализуется в
обычный грант `pair:{profile_id}`, неотличимый от купленного, и «Мои пары»
строятся из грантов, ничего не зная про кредиты.

**Период — из `renews_at`, а не из календаря.** Подписавшийся 31 января не
должен получать вторую проверку 1 февраля, а подписавшийся 1-го не должен ждать
дольше других. Календарный месяц вообще не участвует: расчётный период — это
то, что магазин назвал следующей датой списания.

**Новый период открывается только движением даты вперёд.** Это правило —
единственная защита от бесплатных отчётов, розданных событием, за которое никто
не платил: отмена (`renews_at` → `None`, остаётся `expires_at`), grace period
(дата не двигается, потому что списание не прошло), сверка состояния подписки —
все они приводят сюда, и ни одно не должно начислить. Начисляет только дата,
которая стала больше, а стать больше она может лишь после оплаты.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    Entitlement,
    PairCredit,
    User,
    as_utc,
    new_id,
    utcnow,
)

log = logging.getLogger("alma.billing.credits")


async def _live_plan(
    session: AsyncSession, user: User, *, at: datetime | None = None
) -> Entitlement | None:
    """Действующая подписка этого человека, или `None`.

    «Действующая» — по `entitlements.is_in_force`, то есть не отозванная и не
    истёкшая; отменённая, но ещё не истёкшая, подписка сюда **входит**, и это
    случай 5 матрицы А7: период оплачен, кредит в нём — тоже.
    """
    from ..auth import entitlements

    moment = at or utcnow()
    recurring = entitlements.subscription_kinds()
    plans = [
        held
        for held in await entitlements.for_user(session, user)
        if held.kind in recurring and entitlements.is_in_force(held, moment)
    ]
    if not plans:
        return None
    # Если планов почему-то два, берётся тот, чей период кончается позже: это
    # тот, за который заплачено дальше всех.
    return max(plans, key=lambda row: as_utc(row.expires_at) or moment)


def _period_end(plan: Entitlement) -> datetime | None:
    """Конец расчётного периода этой подписки.

    `renews_at` — обещание списать снова, и пока оно есть, период кончается им.
    После отмены обещания нет, и границей становится `expires_at`: доступ (и
    кредит вместе с ним) доживает до конца оплаченного, что и требует А7 §5.
    """
    return as_utc(plan.renews_at) or as_utc(plan.expires_at)


def _included(plan: Entitlement) -> int:
    """Сколько проверок включает этот план — из каталога, а не из числа здесь.

    «Что входит в подписку» — решение о том, что мы продаём, и оно стоит рядом
    с ценой (`Product.pair_credits_monthly`). Число, написанное здесь, было бы
    вторым таким решением, и однажды они разошлись бы: обещание на экране одно,
    начисление другое.
    """
    from .catalogue import PRODUCTS

    for item in PRODUCTS.values():
        if item.interval and item.kind == plan.kind:
            return item.pair_credits_monthly
    return 0


async def _latest(session: AsyncSession, user: User) -> PairCredit | None:
    return (
        await session.execute(
            select(PairCredit)
            .where(PairCredit.user_id == user.id)
            .order_by(PairCredit.period_end.desc())
            .limit(1)
        )
    ).scalars().first()


async def ensure_period(
    session: AsyncSession, user: User, *, at: datetime | None = None
) -> PairCredit | None:
    """Строка кредита текущего периода — открыв её, если период новый.

    Идемпотентна и вызывается отовсюду: из обработчика продления (там она —
    «закрыть текущий, открыть новый» из А5), из `GET /billing/credits` и из
    самой траты. Одна функция, потому что вопрос один: «в каком периоде мы
    сейчас и открыт ли он».

    `None` означает «кредитов у этого человека нет вовсе» — нет живой подписки
    или план ничего не включает. Это не ошибка: у большинства аккаунтов так.
    """
    plan = await _live_plan(session, user, at=at)
    if plan is None:
        return None

    granted = _included(plan)
    if granted <= 0:
        return None

    end = _period_end(plan)
    if end is None:
        # Подписка без даты — состояние, которое `entitlements.grant` отказывается
        # писать (повторяющийся план без срока никогда не пришлось бы продлевать).
        # Если оно всё же встретилось, начислять нечего: у периода нет конца, то
        # есть он один и бесконечный.
        log.error(
            "subscription %s has neither renews_at nor expires_at — no credit "
            "period can be opened from it", plan.subscription_id or plan.id,
        )
        return None

    latest = await _latest(session, user)

    if latest is not None and plan.renews_at is None:
        # **Подписка отменена — новых периодов больше не будет.**
        #
        # Здесь стояла проверка «конец периода уехал вперёд», и её было
        # недостаточно ровно на этом случае. Пока подписка жива, границу задаёт
        # `renews_at`; после отмены он стёрт, и границей становится
        # `expires_at`, который **намеренно дальше**: `PERIOD["month"]` — 31
        # день, чтобы продление успевало прийти до того, как доступ пропадёт.
        # То есть у отменённой подписки «конец периода» прыгает вперёд на
        # несколько дней сам собой, без единого списания, — и правило «уехало
        # вперёд, значит новый период» выдавало бы бесплатный отчёт за 26¢
        # каждому, кто нажал «отменить». Первым это нашёл тест
        # `test_a_cancelled_period_keeps_its_credit_until_it_expires`.
        #
        # Что остаётся верным: текущая строка живёт и тратится до `expires_at`
        # (А7, случай 5). Отмена — не возврат; период оплачен.
        return latest

    if latest is not None and as_utc(latest.period_end) >= end:
        # Тот же период: сообщение о нём пришло повторно, или дата не двигалась.
        # Строка уже есть — вместе со всем, что из неё потрачено.
        return latest

    start = as_utc(latest.period_end) if latest is not None else as_utc(plan.granted_at)
    start = start or utcnow()

    row = PairCredit(
        id=new_id(),
        user_id=user.id,
        period_start=start,
        period_end=end,
        granted=granted,
        used=0,
        subscription_id=plan.subscription_id,
    )
    session.add(row)
    # Без `try`, и это осознанно. Гонка (продление пришло дважды одновременно:
    # нотификация магазина и наш собственный `/iap/verify` по тому же платежу)
    # упирается в ограничение `pair_credit_period`, вторая вставка падает,
    # запрос отвечает ошибкой — и повтор, который есть у **обоих** этих путей,
    # находит строку уже открытой. Ловить исключение здесь пришлось бы с
    # `rollback()`, а он в этой сессии откатывает всю транзакцию запроса: цена
    # аккуратности была бы потерянная запись покупки, то есть ровно то, чего
    # нельзя. Проигранный заезд стоит одного 500 и одной повторной доставки.
    await session.flush()
    return row


async def state(
    session: AsyncSession, user: User, *, at: datetime | None = None
) -> dict:
    """Что показать на экране пары: сколько включено, сколько потрачено, до когда.

    Открывает период, если он назрел, — потому что это же и есть ответ на
    вопрос «сколько у меня осталось», и ответить на него старой строкой значило
    бы сказать «ноль» человеку, у которого вчера прошло списание.
    """
    row = await ensure_period(session, user, at=at)
    if row is None:
        return {"granted": 0, "used": 0, "remaining": 0, "period_end": None}
    remaining = max(0, (row.granted or 0) - (row.used or 0))
    return {
        "granted": row.granted or 0,
        "used": row.used or 0,
        "remaining": remaining,
        "period_end": as_utc(row.period_end).isoformat() if row.period_end else None,
    }


async def spend(
    session: AsyncSession, user: User, profile_id: str, *, at: datetime | None = None
) -> Entitlement | None:
    """Потратить кредит на нового партнёра и выписать грант, или `None`.

    Грант пишется **обычный**, `scope="pair"`, бессрочный, с `source="credit"` —
    неотличимый от купленного везде, где спрашивают доступ, и отличимый ровно в
    одном месте: список «Мои пары» умеет сказать, что этот отчёт пришёл с
    подпиской. Так и должно быть: отмена подписки его не забирает, потому что
    период, в котором он выдан, был оплачен.

    `None` — «кредита нет»: либо подписки нет, либо он уже потрачен в этом
    периоде. Вызывающий показывает пейволл $4.99 с копирайтом «сверх месячной».
    """
    from ..auth import entitlements

    row = await ensure_period(session, user, at=at)
    if row is None or (row.used or 0) >= (row.granted or 0):
        return None

    row.used = (row.used or 0) + 1
    grant = await entitlements.grant(
        session,
        user,
        system=entitlements.pair_system(profile_id),
        kind="consumable",
        scope=entitlements.SCOPE_PAIR,
        # Денег не было — и колонка обязана сказать это прямо. Написать сюда
        # имя магазина значило бы, что в отчёте за месяц этот отчёт числится
        # проданным: сверка с выплатами Apple не сойдётся ровно на $4.99.
        source="credit",
        amount_cents=0,
    )
    await session.flush()
    log.info(
        "account %s spent a monthly pair credit on %s (%s of %s in the period "
        "ending %s)", user.id, profile_id, row.used, row.granted, row.period_end,
    )
    # Пуш «отчёт пары готов» (кадр W7) — кредитный грант ничем не тише
    # купленного: период, в котором он выдан, оплачен. Хук здесь, а не у
    # вызывающего: единственный вызывающий — `readings.py`, чужой файл, а
    # выдача гранта — вот она. `report_ready` идемпотентен и не поднимает
    # исключений, так что трата кредита не может сорваться из-за уведомления.
    from ..notify import pair as pair_push

    await pair_push.report_ready(session, user, partner_id=profile_id, source="credit")
    return grant


# ── бесплатного тизера пары здесь больше нет ───────────────────────────────
#
# Тут стояла вторая механика: `TEASER_SETTING` (`pair.teaser_cap`),
# `TEASER_CAP_DEFAULT`, метрика `pair_teaser` в `UsageCounter` и `teaser_allowed`,
# считавшая, скольких **разных людей** свободный аккаунт проверил даром за
# календарный месяц. Всё это снято 17.08.2026 решением владельца: «тизер
# „Притяжение“ и глава I пары — одно и то же».
#
# Механика была не лишней, а **второй**. Она защищала ровно от того же, от чего
# теперь защищает сама стена: свободный аккаунт, добавляющий партнёра за
# партнёром, платными генерациями по 26¢ из `free_month_budget`. Как только
# глава I совместимости перестала быть бесплатной, до генерации полного отчёта
# такой аккаунт не доходит вовсе — он видит открывающий абзац (десятые доли
# цента, один раз на пару) и цену. Кап поверх этого был бы третьим числом,
# решающим тот же вопрос, и первым же, которое разошлось бы с остальными.
#
# Что осталось нетронутым и трогать нельзя: расчёт совместимости бесплатен и
# будет бесплатным всегда — он считается из статических файлов и не стоит нам
# ничего. Платный здесь только текст.
