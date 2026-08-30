"""Т-Банк (Tinkoff): оплата российской картой и через СБП, третий адаптер шва.

Paddle и Dodo не работают с российскими картами вовсе; для покупателя из
России единственный путь — российский эквайринг, и Т-Банк выбран владельцем
(29.08.2026, ТЗ «оплата как у Twinby»): страница «Как оплатить» на сайте,
вход той же почтой, что в приложении, оплата СБП или картой, и доступ
привязывается к аккаунту вебхуком.

Три вещи здесь несущие, остальное — перевод словаря.

**Подпись — не HMAC-заголовок, а поле `Token` в теле.** Т-Банк подписывает
так: берутся все корневые поля запроса со скалярными значениями (вложенные
`DATA` и `Receipt` не участвуют), к ним добавляется пара `Password` со
значением пароля терминала, пары сортируются по имени ключа, значения
конкатенируются в одну строку и хэшируются SHA-256; hex-дайджест и есть
`Token`. Булевы значения при этом пишутся строчными (`true`/`false`) — так
их сериализует их собственная сторона. Проверка обязана пересобрать токен и
сравнить `hmac.compare_digest`-ом: `==` проходит каждый функциональный тест
и проявляется только атакой по времени.

**Владелец платежа не едет в нотификации.** У Paddle и Dodo `metadata`
возвращается в вебхуке, и печать `stamp()` читается прямо из него. Т-Банк в
нотификацию `DATA` не кладёт — приходит только `OrderId`. Поэтому заказ
пишется в свою таблицу (`WebOrder`) при открытии сессии, а `enrich`
дочитывает владельца и товар по `OrderId` из неё. Это не обход печати, а её
эквивалент: строку заказа создал наш сервер в нашей базе, браузер её не
видел и подменить не мог.

**Подписка — рекуррент, а не подписка процессора.** У Т-Банка нет сущности
«подписка»: первый платёж с `Recurrent=Y` возвращает в нотификации
`RebillId`, а каждое продление — это наш собственный вызов `Init` + `Charge`
по этому `RebillId` (джоб `alma.billing.tbank_charges`, раз в день из cron —
тем же способом, что `renewals`). `RebillId` играет роль `subscription_id`
во всём шве: `entitlement_for` требует его для monthly-гранта, продление
идемпотентно продлевает ту же строку, а «отмена подписки» — это снятие
`renews_at` нашей же рукой: списывать больше некому, кроме нашего джоба, и
джоб отменённую строку не видит. Поэтому `cancel_subscription` здесь —
успешный no-op: запись делает роутер, как и для остальных.

Никаких кредов в этом файле нет: `TBANK_TERMINAL_KEY` и `TBANK_PASSWORD`
приходят из окружения, вводит их владелец сам.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta

import httpx

from ..config import settings
from ..db.models import utcnow
from .provider import (
    MAX_SIGNATURE_AGE,
    PERIOD,
    BillingUnavailable,
    EventKind,
    Grant,
    InvalidSignature,
    NormalisedEvent,
    SessionHandle,
)
from .provider import entitlement_for as _entitlement_for

log = logging.getLogger("alma.billing")

__all__ = [
    "GRANTING",
    "MAX_SIGNATURE_AGE",
    "PERIOD",
    "REVOKING",
    "Grant",
    "InvalidSignature",
    "TBankClient",
    "TBankProvider",
    "entitlement_for",
    "sign",
    "verify",
]

entitlement_for = _entitlement_for

#: Боевой хост эквайринга — один; песочница у Т-Банка живёт на том же адресе
#: с тестовым терминалом, так что окружение выбирается ключами, а не хостом.
API = "https://securepay.tinkoff.ru/v2"

#: Статусы платежа, которые выдают доступ. Только CONFIRMED: деньги списаны.
#: AUTHORIZED — холд двухстадийного терминала, деньги ещё не наши; терминал
#: продукта одностадийный, но нотификация о холде всё равно не повод открыть
#: главы — см. IGNORED_REASONS.
GRANTING = frozenset({"CONFIRMED"})

#: ...и которые его закрывают.
REVOKING = frozenset({"REFUNDED", "PARTIAL_REFUNDED"})

#: Почему остальные статусы нарочно ничего не делают. Не читается кодом —
#: читается тем, кто соберётся добавить строку в REVOKING.
IGNORED_REASONS: dict[str, str] = {
    "AUTHORIZED": (
        "Холд, не списание. Одностадийный терминал шлёт CONFIRMED сам; "
        "грант по холду — доступ за деньги, которые ещё можно не взять."
    ),
    "REJECTED": (
        "Платёж не прошёл. Ничего не выдано — и отзывать нечего; для "
        "продления это значит «джоб попробует завтра», а доступ закроет "
        "своя дата истечения, не отказ банка."
    ),
    "DEADLINE_EXPIRED": "Человек не завершил оплату. См. REJECTED.",
    "CANCELED": (
        "Отмена неоплаченного платежа (или полный возврат холда). Деньги "
        "не списывались — закрывать нечего."
    ),
    "REVERSED": (
        "Отмена холда двухстадийки до списания. Денег не было — гранта не "
        "было."
    ),
    "3DS_CHECKING": "Промежуточный шаг 3-D Secure.",
    "FORM_SHOWED": "Человек открыл платёжную форму. Это не деньги.",
    "NEW": "Платёж создан. Это тоже не деньги.",
    "CHECKED": "Карта проверена нулевым платежом.",
    "COMPLETED": "Финал СБП-возврата у некоторых терминалов; см. REFUNDED.",
}


def sign(fields: Mapping[str, object], password: str) -> str:
    """`Token` по правилам Т-Банка — SHA-256 отсортированной конкатенации.

    Участвуют только корневые скалярные поля (без `Token`, без вложенных
    `DATA`/`Receipt`), плюс пара `Password`. Булевы значения — строчными:
    их сторона сериализует `Success: true` как `true`, и токен, собранный
    из питоньего `True`, не совпадёт никогда — а в логе это неотличимо от
    неверного пароля.
    """
    flat: dict[str, str] = {}
    for name, value in fields.items():
        if name == "Token" or isinstance(value, (dict, list)):
            continue
        if isinstance(value, bool):
            flat[name] = "true" if value else "false"
        elif value is None:
            continue
        else:
            flat[name] = str(value)
    flat["Password"] = password
    line = "".join(value for _, value in sorted(flat.items()))
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def verify(
    raw_body: bytes,
    headers: Mapping[str, str],
    *,
    secret: str | None = None,
    payload: dict | None = None,
) -> None:
    """Проверить `Token` нотификации, или отказать.

    Заголовков у Т-Банка нет — вся правда в теле, поэтому тело разбирается
    здесь (роутер отдаёт сырые байты всем адаптерам одинаково). Свежесть не
    проверяется: временной метки в нотификации нет вовсе, и охрана от
    повтора — идемпотентность `webhook_event.id`, а не окно.
    """
    password = secret if secret is not None else settings().tbank_password
    if not password:
        raise InvalidSignature(
            "TBANK_PASSWORD is not set — refusing to accept an unverified "
            "webhook that grants paid access"
        )
    if payload is None:
        import json

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise InvalidSignature("the notification body is not JSON") from exc
    if not isinstance(payload, dict):
        raise InvalidSignature("the notification body is not an object")

    provided = str(payload.get("Token") or "")
    if not provided:
        raise InvalidSignature("the notification carries no Token")
    expected = sign(payload, password)
    # Constant time, и вызов стоит буквально здесь — тест читает исходник
    # каждого `verify` и требует `hmac.compare_digest` на месте: `==`
    # проходит любой функциональный тест и виден только атакой по времени.
    if not hmac.compare_digest(expected.encode(), provided.lower().encode()):
        raise InvalidSignature("the notification Token does not match")


@dataclass(frozen=True, slots=True)
class Event:
    """Одна нотификация Т-Банка, прочитанная лениво.

    Тело плоское: `{TerminalKey, OrderId, Success, Status, PaymentId,
    Amount, RebillId?, Token, ...}`. Имена свойств — те же, что у соседних
    адаптеров, чтобы три файла читались рядом.
    """

    payload: dict

    @property
    def status(self) -> str:
        return str(self.payload.get("Status") or "")

    @property
    def id(self) -> str:
        """Ключ идемпотентности: платёж + его состояние.

        Своего идентификатора доставки у Т-Банка нет; ретрай нотификации —
        то же `(PaymentId, Status)` и обязан быть дублем, а возврат по тому
        же платежу — другое состояние и обязан пройти.
        """
        payment = self.payload.get("PaymentId")
        return f"tbank:{payment}:{self.status}" if payment else ""

    @property
    def order_id(self) -> str | None:
        value = self.payload.get("OrderId")
        return str(value) if value else None

    @property
    def transaction_id(self) -> str | None:
        value = self.payload.get("PaymentId")
        return str(value) if value else None

    @property
    def subscription_id(self) -> str | None:
        """`RebillId` — вся «подписка», какая у Т-Банка есть.

        Приходит в нотификации первого рекуррентного платежа и каждого
        `Charge` по нему; шов ключует продления ровно этим полем.
        """
        value = self.payload.get("RebillId")
        return str(value) if value else None

    @property
    def amount_cents(self) -> int:
        """`Amount` уже в копейках — минорной единице рубля."""
        try:
            return int(self.payload.get("Amount") or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def adjustment(self) -> tuple[str, str] | None:
        if self.status == "REFUNDED":
            return ("refund", "full")
        if self.status == "PARTIAL_REFUNDED":
            return ("refund", "partial")
        return None

    @property
    def kind(self) -> EventKind:
        if self.adjustment is not None:
            return EventKind.ADJUSTMENT
        if self.status in GRANTING:
            return EventKind.PAYMENT
        if self.status in ("REJECTED", "DEADLINE_EXPIRED"):
            return EventKind.PAYMENT_FAILED
        return EventKind.UNKNOWN

    def normalise(self) -> NormalisedEvent:
        grants = self.status in GRANTING and bool(self.payload.get("Success", True))
        return NormalisedEvent(
            provider="tbank",
            id=self.id,
            type=self.status,
            kind=self.kind,
            # Владелец и товар дочитываются в `enrich` из `WebOrder` по
            # `OrderId`: нотификация Т-Банка `DATA` не возвращает, и здесь
            # их честно нет, а не «нет пока».
            owner_id=None,
            product=None,
            subscription_id=self.subscription_id,
            transaction_id=self.transaction_id,
            amount_cents=self.amount_cents,
            currency="RUB",
            country="RU",
            buyer_email=None,
            status=self.status,
            renews_at=None,
            adjustment=self.adjustment,
            grants=grants,
            revokes=self.status in REVOKING,
            moves_money=grants or self.status in REVOKING,
            # Суммы называем мы сами при `Init`, поэтому чек «деньги
            # покрывают цену» обязан работать: RUB-полоса каталога и есть
            # то, что было выставлено.
            priced_by_us=True,
            payload=self.payload,
        )


def parse(payload: dict, headers: Mapping[str, str] | None = None) -> Event:
    return Event(payload=payload)


class TBankClient:
    """Тонкий клиент трёх вызовов: `Init`, `Charge`, `GetState`."""

    def __init__(self, *, base: str | None = None) -> None:
        self._base = (base or API).rstrip("/")

    async def _call(self, method: str, fields: dict) -> dict:
        config = settings()
        if not (config.tbank_terminal_key and config.tbank_password):
            raise BillingUnavailable(
                "TBANK_TERMINAL_KEY / TBANK_PASSWORD are not set"
            )
        body = {"TerminalKey": config.tbank_terminal_key, **fields}
        body["Token"] = sign(body, config.tbank_password)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                answer = await client.post(f"{self._base}/{method}", json=body)
        except httpx.HTTPError as exc:
            raise BillingUnavailable(f"tbank {method} failed: {exc}") from exc
        if answer.status_code != 200:
            raise BillingUnavailable(
                f"tbank {method} answered {answer.status_code}: {answer.text[:200]}"
            )
        data = answer.json()
        if not data.get("Success"):
            raise BillingUnavailable(
                f"tbank {method} refused: {data.get('ErrorCode')} "
                f"{data.get('Message') or ''} {data.get('Details') or ''}".strip()
            )
        return data

    async def init_payment(self, fields: dict) -> dict:
        return await self._call("Init", fields)

    async def charge(self, *, payment_id: str, rebill_id: str) -> dict:
        return await self._call(
            "Charge", {"PaymentId": payment_id, "RebillId": rebill_id}
        )

    async def get_state(self, *, payment_id: str) -> dict:
        return await self._call("GetState", {"PaymentId": payment_id})


async def remember_order(user_id: str, product: str) -> str:
    """Записать заказ и вернуть его `OrderId`.

    Строка — единственный мост от нотификации к владельцу: `DATA` в
    нотификации не возвращается, `OrderId` возвращается всегда. Создаёт её
    только наш сервер, поэтому она и играет роль печати `stamp()`.
    """
    from ..db.models import WebOrder
    from ..db.session import session_scope

    order_id = uuid.uuid4().hex
    async with session_scope() as session:
        session.add(WebOrder(order_id=order_id, user_id=user_id, product=product))
    return order_id


async def order_owner(order_id: str) -> tuple[str, str] | None:
    from ..db.models import WebOrder
    from ..db.session import session_scope

    async with session_scope() as session:
        row = await session.get(WebOrder, order_id)
        return (row.user_id, row.product) if row is not None else None


class TBankProvider:
    """Т-Банк как `BillingProvider`."""

    name = "tbank"
    granting = GRANTING
    revoking = REVOKING

    #: Продавец — ИП, чьи реквизиты вводит владелец (`TBANK_MERCHANT_NAME`).
    #: Здесь нет захардкоженного имени нарочно: назвать не того продавца на
    #: странице возвратов — это то, что читает банк при споре, и выдуманное
    #: имя хуже пустого.
    @property
    def merchant(self) -> str:
        return settings().tbank_merchant_name

    #: Чек 54-ФЗ без адреса не пробить, а письмо со ссылкой «уже оплачено» —
    #: часть сценария владельца; страница и так логинит почтой.
    requires_email = True

    #: Чек шлёт касса Т-Банка — наш собственный чек-вейвер тут не при чём.
    issues_the_receipt = False

    def __init__(self, client: TBankClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> TBankClient:
        if self._client is None:
            self._client = TBankClient()
        return self._client

    def verify(
        self, raw_body: bytes, headers: Mapping[str, str], *, secret: str | None = None
    ) -> None:
        verify(raw_body, headers, secret=secret)

    def parse(
        self, payload: dict, headers: Mapping[str, str] | None = None
    ) -> NormalisedEvent:
        return parse(payload, headers).normalise()

    async def enrich(self, event: NormalisedEvent) -> NormalisedEvent:
        """Дочитать владельца и товар по `OrderId` — см. довод в шапке файла.

        Заказ не найден — событие остаётся без владельца, и роутер честно
        запишет это в `webhook_event.error`: чужая нотификация на наш адрес
        не выдаёт ничего.
        """
        from dataclasses import replace

        order_id = (event.payload or {}).get("OrderId")
        found = await order_owner(str(order_id)) if order_id else None
        if found is None:
            return event
        owner_id, product = found
        renews = None
        if event.grants:
            from . import catalogue as prices

            try:
                item = prices.product(product)
            except ValueError:
                item = None
            if item is not None and item.interval:
                # Дата следующего списания — наша: у Т-Банка нет подписки,
                # списывает наш джоб. За день до конца оплаченного месяца
                # (`PERIOD` даёт 31 день доступа) — окно на ретрай отказа.
                renews = utcnow() + PERIOD[item.interval] - timedelta(days=1)
        return replace(event, owner_id=owner_id, product=product, renews_at=renews)

    async def open_session(
        self,
        *,
        product: str,
        user_id: str,
        currency: str,
        country: str | None = None,
        email: str | None = None,
    ) -> SessionHandle:
        """`Init` → адрес платёжной формы Т-Банка (карта и СБП на ней).

        Цена спрашивается у каталога первой: `NotSold` без RUB-полосы — отказ
        до всякой сети. Сумму называем мы (`Amount`, копейки), и тот же
        каталог потом сверяет её в вебхуке — `priced_by_us`.
        """
        from . import catalogue as prices

        config = settings()
        item = prices.product(product)
        cents, display = item.cents_in(currency), item.display(currency)

        order_id = await remember_order(user_id, product)
        fields: dict = {
            "Amount": cents,
            "OrderId": order_id,
            "Description": item.name[:140],
            # Ключ рекуррента: без CustomerKey Т-Банк не вернёт RebillId.
            "CustomerKey": user_id,
            "SuccessURL": f"{config.web_url}/pay/done",
            "FailURL": f"{config.web_url}/pay/fail",
        }
        if item.interval:
            fields["Recurrent"] = "Y"
        if email:
            fields["DATA"] = {"Email": email}
            if config.tbank_taxation:
                # Чек 54-ФЗ. Ставка и система налогообложения — от владельца
                # (ИП, обычно УСН без НДС → Tax "none"); без TBANK_TAXATION
                # чек не собирается вовсе — терминал без кассы его и не ждёт.
                fields["Receipt"] = {
                    "Email": email,
                    "Taxation": config.tbank_taxation,
                    "Items": [
                        {
                            "Name": item.name[:128],
                            "Price": cents,
                            "Quantity": 1,
                            "Amount": cents,
                            "Tax": config.tbank_vat,
                            "PaymentObject": "service",
                        }
                    ],
                }
        if config.tbank_notification_url:
            fields["NotificationURL"] = config.tbank_notification_url

        created = await self.client.init_payment(fields)
        return SessionHandle(
            provider=self.name,
            product=product,
            currency=currency,
            cents=cents,
            display=display,
            url=created.get("PaymentURL"),
            reference=str(created.get("PaymentId") or ""),
        )

    async def cancel_subscription(self, subscription_id: str) -> None:
        """Успех без сети — и это решение, а не заглушка.

        Списывает не Т-Банк, а наш джоб по `renews_at`; роутер после этого
        вызова снимает `renews_at` сам, и списывать становится некому.
        Дёргать API нечем и незачем: сущности «подписка» у Т-Банка нет.
        """
        return None

    async def buyer_address(self, event: NormalisedEvent) -> str | None:
        return event.buyer_email
