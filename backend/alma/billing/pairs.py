"""Кто именно был куплен, когда куплена проверка пары.

Расходуемый товар отличается от двери одним свойством, и оно ломает всё
остальное: `pair.check` покупается многократно, и две покупки с одним и тем же
`productId` — это два разных человека. Магазин про наших людей не знает ничего.
Apple подписывает `productId`, `transactionId` и дату; Google отдаёт токен, по
которому можно спросить о покупке. Ни в одном из двух ответов нет поля «Маша».

Значит, связь «этот платёж — про этого партнёра» может быть только одной из
двух вещей: словом клиента или нашей записью, сделанной **до** оплаты. Первое
негодно, и негодно не гипотетически. Тело `POST /billing/iap/verify` пишет
приложение; приложение пересобирается; `profile_id` в теле — это поле, которое
любой владелец телефона может назвать сам, и оно открывало бы отчёт про
человека, чей id он угадал или подсмотрел в чужой ссылке, за собственные $4.99.
Подписанный магазином пейлоад — не может: его содержимое зафиксировано в момент
оплаты, и подделать его — значит подделать подпись Apple.

Поэтому механика — pending-intent:

    1. `POST /billing/pair/intent {profile_id}` — сервер проверяет, что профиль
       принадлежит этому человеку и не `is_self`, и запоминает пару
       (аккаунт, профиль) строкой `PairIntent`. Отвечает токеном.
    2. Клиент открывает магазинный лист, положив токен в покупку:
       `appAccountToken` у Apple, `obfuscatedProfileId` у Play.
    3. Магазин возвращает токен нам **внутри подписанного пейлоада**.
    4. `partner_for()` ниже превращает токен обратно в `profile_id`.

**Стор — источник правды, а intent — наша память.** Если они разошлись (человек
начал покупку для Маши, свернул приложение, начал для Кати — и оплатилась
первая), грант выписывается по токену из пейлоада, а расхождение пишется в лог
как `pair_intent_mismatch`. Обратный порядок — верить нашему последнему intent —
означал бы открыть отчёт про того, за кого не платили, и узнать об этом было бы
неоткуда: обе покупки настоящие.

**Токена нет вовсе** — грант не выписывается, покупка остаётся `unbound`,
человеку отдаётся 202 и путь `POST /billing/pair/bind`. Деньги не теряются
никогда: они записаны, они его, и привязать их можно вторым шагом. Единственная
альтернатива — выдать хоть что-нибудь наугад — открывает отчёт про не того
человека, а это не чинится: текст написан и прочитан.
"""

from __future__ import annotations

import hashlib
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import PairIntent, Profile, User, new_id, utcnow

log = logging.getLogger("alma.billing.pairs")

#: Пространство имён, из которого выводится токен. Константа, а не случайное
#: значение и не `settings()`: токен обязан быть воспроизводимым от `intent.id`
#: **через годы** — на нём сходятся наша строка и подписанный магазином факт, и
#: день, когда пространство сменится, станет днём, когда все незакрытые покупки
#: перестанут узнаваться. К секретам это отношения не имеет: токен не
#: удостоверяет ничего сам по себе, он только называет строку, у которой уже
#: есть владелец.
_NAMESPACE = uuid.UUID("6f2f7b1e-9a1f-4d5e-8c3a-0b1d2e3f4a5b")


def token_for(intent_id: str) -> str:
    """Токен, который уедет в магазин, — UUID, выведенный из `intent_id`.

    **Форма продиктована Apple:** `appAccountToken` принимает только UUID, и
    что-нибудь другое StoreKit просто не примет. Google в
    `obfuscatedProfileId` берёт до 64 символов любого вида, так что одна форма
    подходит обоим, и второй не заводится — два формата означали бы две ветки
    разбора, а разбор здесь один.

    **Детерминированный, а не случайный.** Случайный пришлось бы хранить,
    чтобы уметь ответить «чей это токен», и хранить *только* его — то есть
    потеря строки означала бы потерю связи. Выведенный из `id` восстанавливается
    из самой строки, а колонка рядом остаётся индексом для обратного вопроса,
    который задаётся на каждой верификации.

    Версия и вариант проставляются битами вручную: `uuid5` даёт UUIDv5, а Apple
    документирует поле как UUID без оговорок про версию — но клиенты StoreKit и
    тестовые утилиты чаще всего валидируют именно v4, и получить отказ в момент
    оплаты дороже, чем два присваивания здесь.
    """
    digest = hashlib.sha256(_NAMESPACE.bytes + intent_id.encode("utf-8")).digest()
    raw = bytearray(digest[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40   # версия 4
    raw[8] = (raw[8] & 0x3F) | 0x80   # вариант RFC 4122
    return str(uuid.UUID(bytes=bytes(raw)))


class NotYours(ValueError):
    """Профиль существует, но принадлежит не этому аккаунту, или это он сам.

    Одно исключение на два случая, потому что ответ у них один: покупку
    открывать нельзя. Разводить их наружу нельзя тем более — разные ответы на
    «нет такого профиля» и «профиль чужой» превращают эндпоинт в способ
    перебирать чужие id.
    """


async def open_intent(session: AsyncSession, user: User, profile_id: str) -> PairIntent:
    """Запомнить, про кого будет покупка, и выдать токен для магазина.

    Проверки стоят **здесь**, до денег, и это единственный момент, когда они
    что-то стоят: после оплаты отказать нельзя — магазин уже списал, — и всякая
    проверка на той стороне превращается в «деньги взяты, отчёт не открыт».

    `is_self` отвергается потому, что совместимость с самим собой — не товар, а
    описка в клиенте; продать её значит взять $4.99 за текст, который не о чем
    писать.
    """
    profile = await session.get(Profile, profile_id)
    if profile is None or profile.user_id != user.id:
        raise NotYours("no such profile")
    if profile.is_self:
        raise NotYours("a compatibility report is about two people")

    intent = PairIntent(
        id=new_id(),
        user_id=user.id,
        profile_id=profile_id,
    )
    intent.app_account_token = token_for(intent.id)
    session.add(intent)
    await session.flush()
    return intent


async def by_token(session: AsyncSession, token: str) -> PairIntent | None:
    """Строка, которой принадлежит этот токен, или `None`."""
    if not token:
        return None
    return (
        await session.execute(
            select(PairIntent).where(
                PairIntent.app_account_token == token.strip().lower()
            )
        )
    ).scalars().first()


async def partner_for(
    session: AsyncSession,
    user: User,
    *,
    token: str | None,
    intent_id: str | None = None,
    transaction_id: str | None = None,
) -> str | None:
    """Про кого этот платёж — по токену из подписанного пейлоада.

    Возвращает `profile_id` или `None`, и `None` означает ровно одно: грант не
    выписывается, покупка остаётся непривязанной, человеку показывается экран
    «к кому применить». Никаких догадок: единственный аккуратный ответ на
    «неизвестно, про кого» — спросить.

    `intent_id` из тела запроса участвует **только в сверке**. Совпал — тишина;
    разошёлся — строка `pair_intent_mismatch` в логе и грант по токену. Это и
    есть правило «стор — источник правды», записанное так, чтобы им нельзя было
    воспользоваться наоборот: подставить чужой `intent_id` можно, но выдаётся
    всё равно то, что подписал магазин.

    Чужой intent отвергается по `user_id`. Токен сам по себе не полномочие — он
    называет строку, — и строка с чужим владельцем означает либо ошибку
    клиента, либо попытку применить чужую покупку к своему аккаунту. Оба случая
    заканчиваются одинаково: `None` и громкая строка в логе.
    """
    if not token:
        log.warning(
            "a pair purchase arrived with no account token (transaction %s, "
            "account %s): the money is recorded and the grant waits for "
            "/billing/pair/bind",
            transaction_id, user.id,
        )
        return None

    intent = await by_token(session, token)
    if intent is None:
        log.warning(
            "pair token %s on transaction %s matches no intent we ever issued — "
            "money recorded, grant deferred",
            token, transaction_id,
        )
        return None

    if intent.user_id != user.id:
        # Не «редкий сбой», а именно то, от чего вся эта конструкция: один
        # аккаунт предъявляет покупку, открытую под другим. Ответ — отказать в
        # *привязке*, но не в деньгах: платёж остаётся записанным на того, кто
        # его сделал, и разбирается вручную.
        log.error(
            "pair token %s belongs to account %s and was presented by %s — "
            "refusing to bind (transaction %s)",
            token, intent.user_id, user.id, transaction_id,
        )
        return None

    if intent_id and intent_id != intent.id:
        # `pair_intent_mismatch`, приложение А4. Человек открыл покупку для
        # одного партнёра, свернул приложение, открыл для другого — и оплатился
        # первый. Магазин прав, наш «последний intent» — нет.
        log.warning(
            "pair_intent_mismatch: the client named intent %s and the store "
            "signed the token of intent %s (partner %s, transaction %s) — "
            "granting what the store signed",
            intent_id, intent.id, intent.profile_id, transaction_id,
        )

    if intent.consumed_at is None:
        intent.consumed_at = utcnow()
        intent.transaction_id = transaction_id
        await session.flush()
    elif intent.transaction_id and intent.transaction_id != transaction_id:
        # Один intent, две оплаченные транзакции. Реально бывает при повторной
        # покупке из того же экрана без нового intent'а; грант всё равно один и
        # тот же (`pair:{profile_id}`), так что вреда нет, но знать об этом
        # надо: вторые $4.99 за уже открытый отчёт — повод вернуть деньги.
        log.warning(
            "intent %s was already closed by transaction %s and is now claimed "
            "by %s — the partner is the same, the second charge may not be",
            intent.id, intent.transaction_id, transaction_id,
        )

    return intent.profile_id
