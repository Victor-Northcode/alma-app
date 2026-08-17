"""What a person is allowed to read, decided in one place.

Every paywall in the product asks this module and nothing else. That is the
only way the answer stays consistent between the hub, a chapter, the chat and
the API — three of those being generous where the fourth is strict is how a
paywall becomes both annoying and leaky at the same time.

The rules, and **the order they are asked in is itself a rule**:

* Is the grant still alive at all — not revoked, not expired? Nothing else is
  worth asking first, because a cancelled subscription that answers the second
  question works forever.
* Then, how wide is it? `scope` decides, before any older sentinel does. A
  live plan is written the way the catalogue produces it — `system="*"`,
  `scope="live"` — so reading the `"*"` first matches a subscription and
  answers "everything". That is not a hypothetical: the hub did exactly that
  while `covers()` did not, so a subscriber saw the natal report drawn as
  owned and was refused when they opened it. Every function here that walks
  entitlements asks scope before the sentinel, and they are the same order on
  purpose.
* A one-time purchase covers exactly the system it was bought for, forever,
  or exactly the one chapter when a chapter is what was bought.
* Бандл (`static`) покрывает пять статичных систем и ничего больше: транзиты
  и соляр пересчитываются, и продать их «навсегда» — значит продать подписку,
  не взяв за неё денег.
* Совместимость покупается **не системой, а человеком**: грант `pair` называет
  один профиль (`pair:{profile_id}`) и открывает отчёт только про него. Это
  единственный scope, который не отвечает на вопрос «открыта ли система», и
  поэтому единственный, которого нет в `unlocked_systems` — см. `unlocked_pairs`.
* A live subscription covers the systems that keep moving. Легаси: ни один
  товар v3 такого гранта не выписывает, но старые строки обязаны работать.
* One chapter of every system is free, named by the chapter definitions
  rather than by a second list here.

What this module is *not* about is worth saying, because the boundary is the
product: every **calculation** is free and always will be. The chart, the
numbers, the cards, the lines on the map cost us nothing to produce — the
ephemeris and the gazetteer are static files on our own disk. What is sold,
and therefore the only thing any answer here is about, is the written
interpretation.

So a caller that takes a `False` from here and hides the numbers as well has
misread it. There is no answer in this module that means "do not show them
their chart" — and one caller was reading it that way. `systems.PREVIEW_FIELDS`
now has an entry for all eight systems, with a test, because the two that had
none went blank the day the last free system did.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Entitlement, EntitlementKind, User, as_utc, utcnow

#: Whole systems given away, of which there are now none.
#:
#: This used to open numerology and birth-card in their entirety. Against the
#: per-system free chapters in `ai/chapters.py` that was fourteen written
#: chapters handed to every quiz-completer on the most expensive model — about
#: $0.29 a head, against a cohort that converts at one or two percent. A free
#: tier is an argument for the paid one; it is not an argument if it loses
#: money on people who were never going to buy.
#:
#: The boundary, so nobody re-opens this by halves: **calculations stay free
#: forever** — they are computed from static local files and cost nothing —
#: and **one written chapter per system stays free**, via `free_chapters()`.
#: What ended is whole free *systems*, which is the only thing this constant
#: ever meant. The mechanism is kept rather than deleted because re-opening a
#: system for a campaign should be a one-line, one-place decision.
FREE_SYSTEMS: frozenset[str] = frozenset()

#: How wide a grant is, spelled the way the `scope` column spells it. Named
#: here because a paywall that compares against a bare string is a paywall one
#: typo away from opening.
SCOPE_SYSTEM = "system"   # одна система, навсегда — дверь
SCOPE_STATIC = "static"   # пять статичных разборов, навсегда — бандл
SCOPE_PAIR = "pair"       # один отчёт по одной паре, навсегда
SCOPE_ALL = "all"         # всё, пока подписка жива
#: Легаси и навсегда: `live` покрывал только движущиеся системы. Новых таких
#: грантов не выписывается ни одним товаром v3, но слово остаётся в коде — тот
#: день, когда его удалят, станет днём, когда старый подписчик получит отказ на
#: главе, за которую заплатил.
SCOPE_LIVE = "live"

#: Пять систем, которые не меняются после рождения, — ровно то, что открывает
#: `bundle.static`, и ровно то, что продаётся дверьми по одной.
#:
#: Список здесь, а не в каталоге (в отличие от `LIVING_SYSTEMS`), и это
#: осознанная асимметрия: «что входит в подписку» — вопрос о том, что мы
#: продаём, а «что такое статичная система» — свойство самих систем: натал,
#: нумерология и карта рождения не станут живыми от смены полки. Тест держит
#: его равным множеству дверей, так что разойтись с каталогом он не может.
STATIC_SYSTEMS: frozenset[str] = frozenset(
    {"natal", "numerology", "birth-card", "astrocartography", "synthesis"}
)

#: The older spelling of an everything-grant, written in the `system` column
#: before `scope` existed. Still accepted on the way in and still understood
#: on the way out, because rows written under it are in the database.
EVERYTHING = "*"

#: Приставка, которой грант пары называет своего партнёра: `pair:{profile_id}`.
#: Одно место, потому что строка собирается на записи гранта и разбирается на
#: проверке доступа, и опечатка в одной из двух половин — это оплаченный отчёт,
#: который не открывается.
PAIR_PREFIX = "pair:"


def pair_system(partner_id: str) -> str:
    """Что пишется в `Entitlement.system` для купленной пары."""
    return f"{PAIR_PREFIX}{partner_id}"


#: Within a paid system, one chapter stays open as the sample. Which one is
#: declared alongside the chapter itself rather than duplicated here — a
#: second copy of this list is a list that drifts, and a drifted exemption
#: locks the very chapter that is supposed to sell the rest.
def free_chapters(system: str) -> frozenset[str]:
    from ..ai.chapters import BY_SYSTEM, free_chapters as declared

    return declared(system) if system in BY_SYSTEM else frozenset()


@dataclass(frozen=True, slots=True)
class Access:
    """Whether a person may read something, and why."""

    allowed: bool
    reason: str
    kind: str | None = None            # "free" | "one_time" | "consumable" | "monthly"
    expires_at: datetime | None = None

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "kind": self.kind,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


#: Ответ про пару, которую невозможно назвать: партнёр передан «сырой» датой
#: рождения и профиля у него нет, либо профилей несколько и ни один не назван.
#:
#: Это **не** ошибка вызова, поэтому и не `PartnerRequired`: у человека без
#: сохранённого профиля не может быть гранта `pair:{id}` — не к чему его
#: привязать, — так что «закрыто» здесь правда, а не отговорка. Ответ живёт
#: константой, а не собирается на месте, чтобы формулировка про пары была в
#: одном файле с правилом про пары: два разных «закрыто» на двух экранах — это
#: два разных объяснения одного и того же отказа.
PAIR_WITHOUT_PROFILE = Access(False, "compatibility opens one saved partner at a time")


def living_systems() -> frozenset[str]:
    """Which systems a live subscription includes.

    The list belongs to the catalogue, because "what does the subscription
    contain" is a decision about what we sell rather than about who may read
    what. Read through a function so that this module holds a name and not a
    copy: a second list of systems is a list that drifts, and this one drifts
    in the expensive direction — the archive given away for a month's rent.

    Imported inside the call for the same reason `Entitlement.covers` does
    it: identity should not have to drag the billing package in behind it.
    """
    from ..billing.catalogue import LIVING_SYSTEMS

    return frozenset(LIVING_SYSTEMS)


def subscription_kinds() -> frozenset[str]:
    """Which entitlement kinds mean "this renews".

    Read off the catalogue rather than listed here, because the question is
    only ever "does the thing we sold under this kind bill again", and the
    catalogue is where an interval is declared. The alternative — a set of
    strings in this file — was already one plan behind the day the monthly
    was priced, and a subscriber read as free gets the free tier's model and
    the free tier's three questions while paying us every month.

    Deliberately not "anything with an expiry": a grant made by hand to put
    something right also expires, and it is not a subscription.
    """
    from ..billing.catalogue import PRODUCTS

    return frozenset(item.kind for item in PRODUCTS.values() if item.interval)


def is_in_force(entitlement: Entitlement, at: datetime | None = None) -> bool:
    """Whether this grant still counts at all, before asking what it covers.

    Two questions live inside `Entitlement.covers`: is this row still alive,
    and does it reach this system. They have to be separable, because the
    second one for a live subscription is answered by the catalogue — "what is
    in the plan" is a decision about what we sell — and the tier, the hub, the
    renewal and the account screen all need the first question on its own.

    Public because the account screen needs exactly this and was asking for it
    the wrong way: `entitlement.covers(entitlement.system)` probes coverage
    using the row's own `system` column as a slug, and for a live subscription
    that column holds "live" or "*" — neither of which is a living system. A
    paying subscriber was shown "active: false" on the one screen a person
    opens when they are already wondering whether to cancel.
    """
    if entitlement.revoked_at is not None:
        return False
    moment = at or utcnow()
    expires = as_utc(entitlement.expires_at)
    return expires is None or expires > moment


async def for_user(session: AsyncSession, user: User) -> list[Entitlement]:
    result = await session.execute(
        select(Entitlement).where(
            Entitlement.user_id == user.id, Entitlement.revoked_at.is_(None)
        )
    )
    return list(result.scalars().all())


class PartnerRequired(ValueError):
    """`compatibility` спросили без партнёра, о котором идёт речь.

    Не «нет доступа», а неправильный вызов, и разница видна на HTTP: 400, не
    402. Совместимость в v3 покупается поштучно (`pair.check` → грант
    `pair:{profile_id}`), поэтому «можно ли читать совместимость» — вопрос без
    ответа, пока не сказано, с кем. Ответить на него `False` значило бы
    показать пейволл человеку, который уже заплатил за этот самый отчёт, и
    отличить такой отказ от честного было бы нечем.
    """


async def check(
    session: AsyncSession,
    user: User,
    system: str,
    *,
    chapter: str | None = None,
    partner_id: str | None = None,
    at: datetime | None = None,
) -> Access:
    """The single authority on whether this person may read this thing.

    `partner_id` обязателен для `compatibility` и бессмыслен для всего
    остального: отчёт по паре покупается на одного конкретного партнёра, и
    грант называет именно его.
    """
    moment = at or utcnow()

    if system in FREE_SYSTEMS:
        return Access(True, "this system is free", kind="free")
    if chapter and chapter in free_chapters(system):
        return Access(True, "this chapter is free", kind="free")

    # Требование партнёра стоит **после** бесплатных веток намеренно. Первая
    # глава совместимости бесплатна для всех, и «про кого она» её открытость не
    # меняет — то есть на этот вопрос ответ есть и без имени. Не отвечает без
    # имени только платная глава, и вот там молчание — уже ошибка вызова.
    if system == "compatibility" and partner_id is None:
        raise PartnerRequired(
            "compatibility is bought one partner at a time: check() needs the "
            "partner_id whose report is being opened"
        )

    for entitlement in await for_user(session, user):
        if not entitlement.covers(
            system, chapter=chapter, partner_id=partner_id, at=moment
        ):
            continue
        # Scope first, in the order `covers` and `unlocked_systems` ask it: a
        # live plan is granted with `system="*"`, so testing the everything
        # sentinel first would tell a monthly subscriber they hold the annual
        # plan — on the screen where they are deciding whether it is worth it.
        # `pair` и `static` встали перед сентинелом по той же причине и с той
        # же ценой ошибки: оба пишутся с `system`, который сентинелу не
        # соответствует, но порядок здесь — правило, а не совпадение.
        return Access(
            True,
            "covered by your subscription"
            if entitlement.scope == SCOPE_LIVE
            else "this pair is yours"
            if entitlement.scope == SCOPE_PAIR
            else "covered by the five readings you bought"
            if entitlement.scope == SCOPE_STATIC
            else "covered by your plan"
            if entitlement.scope == SCOPE_ALL or entitlement.system == EVERYTHING
            else "you own this chapter"
            if ":" in entitlement.system
            else f"you own {system}",
            kind=entitlement.kind,
            expires_at=entitlement.expires_at,
        )

    return Access(False, f"{system} has not been unlocked yet")


async def unlocked_systems(session: AsyncSession, user: User) -> set[str]:
    """Everything this person can read right now — for the hub."""
    from ..calc.contract import SYSTEMS

    # One clock for the whole answer: asking the time again per row lets two
    # grants that expire in the same second disagree about whether they did.
    moment = utcnow()
    unlocked = set(FREE_SYSTEMS)
    everything = set(SYSTEMS)
    for entitlement in await for_user(session, user):
        if not is_in_force(entitlement, moment):
            continue
        # Scope is asked *first*, in the same order `Entitlement.covers` asks
        # it, and that order is the whole rule. A monthly plan is granted the
        # way the catalogue describes it — `system="*"`, `scope="live"` — so
        # testing the legacy `system == "*"` sentinel first matched the
        # subscription and returned the entire archive. The two functions then
        # disagreed about one row: the hub drew the natal report as owned and
        # `check()` refused it on the way in. A subscriber who finds the natal
        # report already open never buys it, and finding out it was a lie is
        # worse than never having been offered it.
        if entitlement.scope == SCOPE_LIVE:
            unlocked |= living_systems() & everything
            continue
        if entitlement.scope == SCOPE_PAIR:
            # **Пара намеренно не добавляет `compatibility` в общий сет.**
            # Доступ поштучный: куплен отчёт про одного человека, а не система.
            # Открыть её здесь значило бы нарисовать в хабе «совместимость
            # открыта», и следующий же партнёр упёрся бы в пейволл — то самое
            # расхождение хаба и `check()`, ради которого весь этот порядок
            # проверок и написан. Список пар отдаётся отдельно, `unlocked_pairs`.
            continue
        if entitlement.scope == SCOPE_STATIC:
            unlocked |= STATIC_SYSTEMS & everything
            continue
        if entitlement.scope == SCOPE_ALL or entitlement.system == EVERYTHING:
            return everything
        # A single chapter does not unlock its system on the hub — it is one
        # chapter, and showing the whole system as owned would be a promise
        # the reader finds out about at the second chapter.
        if ":" not in entitlement.system:
            unlocked.add(entitlement.system)
    return unlocked


async def unlocked_pairs(session: AsyncSession, user: User) -> list[str]:
    """Профили партнёров, чьи отчёты уже оплачены — для экрана «Мои пары».

    Отдельный ответ, а не строка в `unlocked_systems`, ровно потому, что это
    другой вопрос: там — «какие системы открыты», здесь — «про кого написано».
    Слить их нельзя: одно `compatibility` в общем сете означало бы «открыта
    совместимость», то есть про всех, а куплены — конкретные люди.

    Источник правды — гранты, а не история покупок магазина: расходуемые товары
    Apple через restore не возвращает, так что список, построенный по StoreKit,
    после переустановки был бы пуст, хотя человек заплатил.
    """
    moment = utcnow()
    found: list[str] = []
    for entitlement in await for_user(session, user):
        if not is_in_force(entitlement, moment):
            continue
        if entitlement.scope != SCOPE_PAIR:
            continue
        if not entitlement.system.startswith(PAIR_PREFIX):
            # Грант пары, который не называет партнёра, ничего не открывает —
            # он не совпадёт ни с одним `pair:{id}` в `covers`. Пропускаем
            # молча: строка есть, читать по ней нечего, и падать на ней значит
            # уронить весь хаб из-за одной кривой записи.
            continue
        found.append(entitlement.system[len(PAIR_PREFIX):])
    return found


async def tier_of(session: AsyncSession, user: User, *, at: datetime | None = None) -> str:
    """Which commercial tier this person is in: free, owner, or subscriber.

    The chat allowances and the spend ledger both key off this, and they have
    to agree — a person the ledger thinks is free and the chat thinks is paid
    gets a conversation that stops mid-answer. So the definition lives here
    once: a live subscription outranks a purchase, because someone who has
    both is paying us monthly and should be treated as the more valuable of
    the two states.

    Anything else — a grant made by hand to put something right, a kind we
    have stopped selling — reads as free. This number decides how much of our
    money a person may spend on generation, and only a kind we know we were
    paid for may raise it.

    **Владелец бандла — `owner`, а не `subscriber`, и это тоже решается здесь.**
    Бандл продаётся как `kind="one_time"`, поэтому попадает в ветку ниже сам
    собой; писать его отдельной строкой не надо, а вот проверить — надо, и тест
    это делает. Цена ошибки: `subscriber` — это подписочные квоты чата
    (`subscriber_questions_per_month`) каждый месяц до конца жизни аккаунта, за
    один платёж в $19.99.

    `consumable` (`pair.check`) намеренно не поднимает тир ни до чего. Куплен
    один отчёт, а не доступ; отчёт стоит нам один раз, а квота чата — каждый
    месяц.
    """
    moment = at or utcnow()
    recurring = subscription_kinds()

    tier = "free"
    for entitlement in await for_user(session, user):
        if not is_in_force(entitlement, moment):
            continue
        if entitlement.kind in recurring:
            return "subscriber"
        if entitlement.kind == EntitlementKind.one_time.value:
            tier = "owner"
    return tier


async def has_kind(session: AsyncSession, user: User, kind: str) -> bool:
    """Есть ли у человека живое право именно этого рода.

    Нужно ровно для одного: недельная подписка получает порцию вопросов по
    своему сроку, а `tier_of` намеренно не различает сроки — она отвечает на
    вопрос «платит ли», а не «как часто».
    """
    moment = utcnow()
    for entitlement in await for_user(session, user):
        if is_in_force(entitlement, moment) and entitlement.kind == kind:
            return True
    return False


async def may_be_offered(
    session: AsyncSession, user: User, key: str, *, at: datetime | None = None
) -> bool:
    """Whether this person may be sold the catalogue product named `key`.

    **Два отказа, и оба нужны.** Первый — ключ, которого мы не продаём: чекаут
    и `/iap/verify` принимают имя товара от клиента, а клиент — не сторона,
    которой мы верим. Второй — цена не с полки.

    Условных цен в v3 нет, так что сегодня функция отвечает True на все восемь
    строк. Она остаётся потому, что закрывает уже случавшуюся дыру: `archive-bump`
    за $29.99 выдавал ровно то же, что архив за $38.99, и пока чекаут принимал
    любой ключ по имени, архив покупался одним HTTP-запросом на девять долларов
    дешевле. `Product.offered` тогда лишь описывал намерение; проверка —
    останавливает. Первый же A/B по цене бандла (ТЗ §7) заведёт вторую цену на
    один и тот же грант, и ворота понадобятся снова.

    `at` больше не используется — держать его в сигнатуре дешевле, чем править
    всех вызывающих ради параметра, который вернётся вместе с условной ценой.
    """
    from ..billing.catalogue import PRODUCTS

    item = PRODUCTS.get(key)
    return item is not None and item.on_the_shelf


async def grant(
    session: AsyncSession,
    user: User,
    *,
    system: str,
    kind: str,
    transaction_id: str | None = None,
    subscription_id: str | None = None,
    scope: str | None = None,
    status: str | None = None,
    renews_at: datetime | None = None,
    amount_cents: int = 0,
    currency: str = "USD",
    # Not a processor name. Every caller that knows one passes it; a grant
    # made by hand to put something right genuinely has no processor, and
    # saying "paddle" for it is a row that lies about where money came from.
    source: str = "unknown",
    duration: timedelta | None = None,
) -> Entitlement:
    """Give access. Idempotent per transaction, and per subscription.

    The transaction check is what makes a retried webhook safe. Payment
    providers retry, and a second grant for the same money is a real bug —
    the kind that turns a refund into a support conversation.

    The subscription check is what makes a *renewal* safe, and it cannot be
    the transaction check: every renewal is a new charge with a new
    transaction id, so keying on that wrote one row a month. Two things went
    wrong with that. The rows accumulated, so every paywall check walked a
    longer list each month; and a cancellation only ever caught the row
    belonging to the charge it named, leaving the earlier ones with future
    expiry dates, still granting what had just been cancelled. One
    subscription is one row, extended in place.

    This is also the only writer of `scope`, which is why it is derived here
    when the caller does not say: both spellings of an everything-grant — the
    old `system="*"` and the explicit scope — have to end up as the same row,
    or the hub and the paywall disagree about the same purchase.
    """
    moment = utcnow()
    # Никаких сроков по умолчанию от вида гранта. Здесь стоял «год для
    # `annual`» — единственный вид, которому длительность угадывалась, — и он
    # ушёл вместе с годовой подпиской. Длительность теперь либо назвал
    # вызывающий, либо её нет; проверка ниже ловит второй случай там, где он
    # опасен.
    span = duration
    if span is None and kind in subscription_kinds():
        # No expiry means forever, and forever is what a subscription is sold
        # *instead of*. A monthly plan granted with no duration would be a
        # month's payment that never has to be made again, and nothing would
        # ever report it as wrong — the row simply keeps working.
        raise ValueError(
            f"a {kind!r} grant needs a duration: a recurring plan written "
            "without an expiry never has to be renewed"
        )
    width = scope or (
        SCOPE_ALL if system == EVERYTHING
        else SCOPE_LIVE if system == SCOPE_LIVE
        # Пара выводится из формы `system`, как и всё остальное здесь: грант,
        # названный `pair:{id}` и записанный со `scope="system"`, не совпал бы
        # ни с одним запросом — `covers` сравнивает `pair`-гранты только внутри
        # своей ветки, — и отчёт, за который заплачено, не открылся бы.
        else SCOPE_PAIR if system.startswith(PAIR_PREFIX)
        else SCOPE_SYSTEM
    )

    if subscription_id:
        # Revoked rows included on purpose: a subscription that is cancelled
        # and started again is the same subscription to the provider, and a
        # second row for it would be a second thing to cancel later.
        found = (
            await session.execute(
                select(Entitlement).where(
                    Entitlement.user_id == user.id,
                    Entitlement.subscription_id == subscription_id,
                )
            )
        ).scalars().first()
        if found is not None:
            # **One period per transaction, and that condition is the fix.**
            #
            # A store subscription arrives twice for one payment and under two
            # different idempotency keys, so insert-before-process cannot
            # collapse them: the app hands us the signed transaction the instant
            # the sheet closes and `/billing/iap/verify` files it as
            # `appstore:<transactionId>`, then Apple's own SUBSCRIBED
            # notification for the same purchase arrives filed under
            # `notificationUUID`. Both reached here, and this branch used to
            # extend by a whole period every time it was called — so every
            # subscriber silently got two months for one month's money, or two
            # years for one year's, with a correct-looking money trail (the
            # `Purchase` row *does* dedupe on transaction id) and nothing wrong
            # anywhere but an expiry date nobody reads until somebody reconciles
            # against Apple's payout report.
            #
            # A genuine renewal carries a *fresh* transaction id — DID_RENEW
            # always does — so it still extends. A replay of the transaction
            # that last extended this row does not.
            already_extended = (
                transaction_id is not None and found.transaction_id == transaction_id
            )
            if span is not None and not already_extended:
                # Extend from whichever is later: a renewal charged a day
                # early must not cost the payer that day, and a subscription
                # resumed after a lapse must not be handed the weeks it was
                # not paying for.
                found.expires_at = max(as_utc(found.expires_at) or moment, moment) + span
            if transaction_id:
                # Recorded on every extension, because it is the only thing that
                # can answer "has this charge already been honoured?" next time.
                found.transaction_id = transaction_id
            # A plan change is the same subscription, so it is the same row.
            # Writing a second one would leave the old scope open for as long
            # as its expiry lasted, which is how a downgrade keeps paying out.
            found.system = system
            found.kind = kind
            found.scope = width
            found.revoked_at = None
            if amount_cents:
                # **Only when the event actually carried a figure**, and that
                # condition is the whole fix. This row is where the pre-renewal
                # notice reads the amount it is about to warn somebody about,
                # and on one of the two processors a subscription grant is
                # written from `subscription.active`/`renewed`, whose amount is
                # deliberately zero — the money arrives on its own payment
                # event. So the column stayed at nought for the life of every
                # Dodo plan, and the letter whose entire job is to say what is
                # about to be taken would have said "$0.00 will be charged"
                # three days before taking $78.99. Writing the zero back over a
                # good figure would be the same bug facing the other way, which
                # is why this is a condition and not an assignment.
                found.amount_cents = amount_cents
                found.currency = currency
            if status is not None:
                found.status = status
            if renews_at is not None:
                found.renews_at = renews_at
            await session.flush()
            return found
    elif transaction_id:
        existing = await session.execute(
            select(Entitlement).where(
                Entitlement.transaction_id == transaction_id,
                Entitlement.user_id == user.id,
                Entitlement.system == system,
            )
        )
        found = existing.scalar_one_or_none()
        if found is not None:
            return found

    entitlement = Entitlement(
        user_id=user.id,
        system=system,
        kind=kind,
        scope=width,
        expires_at=moment + span if span is not None else None,
        transaction_id=transaction_id,
        subscription_id=subscription_id,
        status=status,
        renews_at=renews_at,
        amount_cents=amount_cents,
        currency=currency,
        source=source,
    )
    session.add(entitlement)
    await session.flush()
    return entitlement


async def revoke(session: AsyncSession, entitlement: Entitlement) -> None:
    """Used on refund and chargeback. The row stays; access stops."""
    entitlement.revoked_at = utcnow()
    await session.flush()
