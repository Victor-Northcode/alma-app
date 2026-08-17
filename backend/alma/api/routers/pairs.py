"""«Мои пары» — про кого уже написано, и откуда это взялось.

**Список строится из грантов, а не из истории магазина**, и это решение, а не
удобство. Расходуемые покупки Apple через restore не возвращает — правило
магазина, не наш выбор, — поэтому «Мои пары», собранные по StoreKit, после
переустановки телефона были бы пусты у человека, который заплатил за пять
отчётов. Грант же лежит у нас и переживает и переустановку, и смену устройства,
и вход в аккаунт после гостевого периода.

Тот же список поэтому отвечает и за кредитные проверки: подписчик, потративший
включённый месячный кредит, получает такой же грант `pair:{profile_id}`, и
единственное, чем он отличается, — колонка `source`. Отличие показывается
(«входит в подписку» против «куплено»), но доступ от него не зависит: оба
отчёта остаются открытыми навсегда.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from ...auth import entitlements
from ...db.models import Profile, as_utc
from ..deps import CurrentUser, SessionDep

router = APIRouter(prefix="/pairs", tags=["pairs"])

# TODO(Ф1): `GET /pairs/{profile_id}/teaser` из контракта А8 намеренно не
# заведён здесь, и это решение, а не нехватка времени — его надо либо
# подтвердить, либо снять вместе с экранами P4.
#
# Тизер «Притяжение» уже существует: это первая глава совместимости,
# бесплатная по `free_chapters`, и она приходит обычным `POST /v1/readings`
# с `chapter="attraction"`. Там же стоит серверный кап (`_teaser_or_paywall`),
# там же кэш готового текста, бюджетные потолки и валидатор цитат. Второй
# эндпоинт к той же генерации означал бы вторую копию всех четырёх — а
# разойтись им достаточно один раз, чтобы кап обходился запросом по другому
# адресу.
#
# Чего у клиента действительно нет, так это способа получить тизер **без
# сохранённого профиля** (ТЗ P4: «ввод даты → тизер»). Когда он понадобится,
# правильная форма — не второй генератор, а профиль, создаваемый до тизера:
# грант пары всё равно называет `profile_id`, и человек без профиля не может
# ничего купить.


@router.get("")
async def my_pairs(user: CurrentUser, session: SessionDep) -> list[dict]:
    """Оплаченные отчёты по парам, свежие сверху.

    Имя партнёра берётся из профиля, если он ещё существует. Если профиль
    удалён, строка **остаётся** — грант осиротел, но отчёт написан и оплачен, и
    убрать его из списка значило бы спрятать от человека то, за что он заплатил
    (А7, случай 12). Имя тогда `None`, и клиент рисует «без имени».
    """
    rows = [
        held
        for held in await entitlements.for_user(session, user)
        if held.scope == entitlements.SCOPE_PAIR
        and held.system.startswith(entitlements.PAIR_PREFIX)
        and entitlements.is_in_force(held)
    ]
    ids = [held.system.removeprefix(entitlements.PAIR_PREFIX) for held in rows]
    named = {
        profile.id: profile.name
        for profile in (
            await session.execute(select(Profile).where(Profile.id.in_(ids)))
        ).scalars().all()
        # Чужой профиль с угаданным id не должен подставить сюда своё имя:
        # грант называет только идентификатор, а имя читается из нашей же базы.
        if profile.user_id == user.id
    }
    listing = [
        {
            "profile_id": profile_id,
            "name": named.get(profile_id),
            "purchased_at": as_utc(held.granted_at).isoformat(),
            # «Куплено» против «входит в подписку». Читается из `source`,
            # который кредит заполняет словом `credit`, а магазин — своим
            # именем; третьего значения тут быть не может, поэтому и сравнение
            # одно.
            "source": "credit" if held.source == "credit" else "purchase",
        }
        for held, profile_id in zip(rows, ids)
    ]
    listing.sort(key=lambda item: item["purchased_at"], reverse=True)
    return listing
