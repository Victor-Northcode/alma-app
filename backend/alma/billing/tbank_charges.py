"""Продление подписок Т-Банка: `Init` + `Charge` по сохранённому `RebillId`.

У Т-Банка нет сущности «подписка» — есть рекуррентный платёж: первый `Init`
с `Recurrent=Y` возвращает `RebillId`, а каждое продление — наш собственный
вызов. Значит «подписка продлевается автоматически» — обещание, которое
держит этот джоб, и никто больше. Запускается раз в день из cron тем же
способом, что `renewals`: `python -m alma.billing.tbank_charges`.

Что он делает и чего не делает:

- **Списывает только то, что само попросило.** Берутся действующие гранты
  `source='tbank'` подписочного вида с наступившим `renews_at`. Отменённая
  подписка — это `renews_at IS NULL` (роутер снял его при отмене), и джоб её
  не видит: списывать после отмены — это то самое «скрытое списание», за
  которое банки блокируют терминал.
- **Не выдаёт доступ.** Успешный `Charge` кончается нотификацией CONFIRMED
  на общий вебхук — грант продлевает она, тем же путём и с той же
  идемпотентностью, что любой платёж. Джоб лишь двигает `renews_at` вперёд,
  чтобы не списать дважды за один день.
- **Отказ банка — не событие.** Карта умерла — `Charge` вернул ошибку;
  `renews_at` сдвигается на сутки, и завтра попытка повторится. Доступ
  закроет собственный `expires_at` гранта — честно и сам, без нашего
  участия; окно между `renews_at` и `expires_at` (один день из `PERIOD`)
  и есть весь дозволенный ретрай.
- **Пишет числа.** Джоб работает без свидетелей, и «сколько нашёл, сколько
  списал, сколько отказано» — единственный способ узнать, что он месяц
  ничего не делал.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Entitlement, as_utc, utcnow

log = logging.getLogger("alma.billing.tbank")

#: На сколько отодвигается попытка после отказа банка. Сутки: чаще — это
#: долбить умершую карту, реже — потерять окно до `expires_at`.
RETRY = timedelta(days=1)


async def due(session: AsyncSession) -> list[Entitlement]:
    from ..auth import entitlements as ent

    now = utcnow()
    rows = (
        await session.execute(
            select(Entitlement).where(
                Entitlement.source == "tbank",
                Entitlement.revoked_at.is_(None),
                Entitlement.renews_at.is_not(None),
                Entitlement.subscription_id.is_not(None),
            )
        )
    ).scalars().all()
    kinds = ent.subscription_kinds()
    return [
        row for row in rows
        if row.kind in kinds and (as_utc(row.renews_at) or now) <= now
    ]


async def charge_due(session: AsyncSession) -> dict:
    """Списать всё, что подошло. Возвращает счёт для лога."""
    from . import catalogue as prices
    from .tbank import TBankClient, remember_order

    outcome = {"due": 0, "charged": 0, "declined": 0, "skipped": 0}
    client = TBankClient()
    for plan in await due(session):
        outcome["due"] += 1
        # Товар восстанавливается по виду гранта: подписка в продукте одна.
        product = "sub.monthly"
        try:
            item = prices.product(product)
            cents = item.cents_in("RUB")
        except Exception:
            outcome["skipped"] += 1
            log.error("no RUB price for %s — cannot renew %s", product, plan.id)
            continue
        try:
            order_id = await remember_order(plan.user_id, product)
            created = await client.init_payment({
                "Amount": cents,
                "OrderId": order_id,
                "Description": item.name[:140],
                "CustomerKey": plan.user_id,
            })
            await client.charge(
                payment_id=str(created.get("PaymentId")),
                rebill_id=plan.subscription_id,
            )
        except Exception as exc:  # noqa: BLE001 — отказ банка не роняет обход
            outcome["declined"] += 1
            plan.renews_at = utcnow() + RETRY
            log.warning("tbank charge declined for %s: %s", plan.id, exc)
            continue
        # Сдвиг сразу и на месяц: нотификация CONFIRMED поставит своё точное
        # `renews_at` через грант, а этот сдвиг — только страховка от второго
        # списания, если джоб запустят дважды до прихода нотификации.
        plan.renews_at = utcnow() + timedelta(days=30)
        outcome["charged"] += 1
    await session.flush()
    if outcome["declined"] or outcome["skipped"]:
        log.error("tbank renewals: %s", outcome)
    else:
        log.info("tbank renewals: %s", outcome)
    return outcome


async def _run() -> dict:
    from ..db.session import session_scope

    async with session_scope() as session:
        return await charge_due(session)


if __name__ == "__main__":  # pragma: no cover — вход для cron
    logging.basicConfig(level=logging.INFO)
    print(asyncio.run(_run()))
