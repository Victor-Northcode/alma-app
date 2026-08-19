"""The database, as small as it can be and no smaller.

Two shapes are worth explaining because they are not the obvious ones.

*A user starts as a guest.* There is no anonymous session that later becomes
an account — the guest **is** an account, with a row and an id, from the first
tap. Signing in attaches an identity to a row that already exists, so nothing
has to be migrated and there is no window where a person's chart lives only
in a cookie. `merge_into` records the one case where two rows have to become
one: someone who used the app as a guest on a phone and then signed in with
an account they had already made on a laptop.

*Deletion is real.* `deleted_at` exists so a request can be honoured
immediately at the API while the rows are erased, not as a way to keep data
that someone asked us to destroy. `accounts.erase` is what removes them, and
the list of tables it walks is the list of tables a person's data lives in —
a new table that holds a `user_id` and is not in it is a promise this project
has broken without noticing.
"""

from __future__ import annotations

import enum
import logging
import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates

log = logging.getLogger("alma.db.models")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clamped(value: str | None, limit: int, where: str) -> str | None:
    """Cut a provider's string to the width of the column it is going into.

    Only ever used on the columns that hold a **processor's** word rather than
    ours — `Entitlement.status`, `Purchase.status`. Their contents arrive in a
    webhook body, so their length is a promise somebody else makes and can
    break in a release note we do not read.

    Truncating is the right trade here and it would be wrong almost anywhere
    else. These two columns are documented as recorded-and-never-consulted:
    nothing decides access, money or eligibility from them, so a shortened
    value costs a support engineer some context. The alternative costs a sale —
    Postgres rejects the INSERT, the webhook handler records the delivery as
    failed, and the renewal or the refund that event carried never lands. The
    log line is loud on purpose: it is the signal to widen the column, and a
    silent clamp would leave nobody any reason to.
    """
    if value is not None and len(value) > limit:
        log.warning("%s truncated to %d characters: %r", where, limit, value)
        return value[:limit]
    return value


def as_utc(value: datetime | None) -> datetime | None:
    """Force a stored timestamp to be timezone-aware.

    SQLite has no datetime type and hands back naive values even from a
    `DateTime(timezone=True)` column, so comparing one to an aware `utcnow()`
    raises. Everything written here is UTC, so attaching the zone on read is
    correct rather than merely convenient — and doing it in one place means
    the next comparison someone writes cannot reintroduce the bug.
    """
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def new_id() -> str:
    """A URL-safe opaque id. Not sequential: ids end up in shared links."""
    return secrets.token_urlsafe(16)


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSON, list: JSON}


class AuthProvider(str, enum.Enum):
    guest = "guest"
    google = "google"
    apple = "apple"
    email = "email"


class EntitlementKind(str, enum.Enum):
    """Every kind of grant the catalogue can sell, and no kind it cannot.

    The enum has to enumerate what is actually on sale. It listed only
    `one_time` and `annual` while the catalogue had already priced a monthly
    plan, and because kinds are stored as free strings nothing broke loudly —
    `tier_of` simply read a paying subscriber as a free user, on the cheapest
    model, with three questions a day. A test pins this list against the
    catalogue's own kinds so the two cannot separate again.
    """

    one_time = "one_time"      # одна система или бандл из пяти, куплено навсегда
    #: Один отчёт по одной паре. Расходуемый в магазине — покупается столько
    #: раз, сколько партнёров человек проверит, — но выданный **грант**
    #: бессрочен: отчёт, за который заплачено, остаётся читаемым навсегда.
    #: Расходуется покупка, а не доступ.
    consumable = "consumable"
    monthly = "monthly"        # всё, пока подписка жива
    # `weekly` и `annual` сняты вместе с самими подписками (ТЗ §2, монетизация
    # v3). Удалены, а не оставлены «на всякий случай»: тест держит этот список
    # равным видам из каталога, и лишний член означал бы вид гранта, который
    # ничто не выписывает, ничто не продлевает и ничто не истекает — то есть
    # состояние, в которое можно попасть только руками и из которого нет
    # выхода. На момент удаления таких грантов в базе не было ни одного.
    # There is deliberately no `trial`. Nothing in the product issues one, and
    # a kind that exists only in this enum reads to the next person as a
    # feature that already works: they grant it, and the paywall acquires a
    # state that no webhook renews, no job expires and no test covers. Add it
    # back on the day something actually issues one, together with the code
    # that takes it away again.


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(16), default=AuthProvider.guest.value)
    provider_subject: Mapped[str | None] = mapped_column(String(255), index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    locale: Mapped[str] = mapped_column(String(8), default="en")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: What the daily notification is allowed to do — one of
    #: `notify.rules.Preference`, or NULL for "has not been asked yet".
    #:
    #: **On the user and not the profile**, because a person has one phone and
    #: several charts: the preference belongs to whoever holds the phone, not
    #: to any one birth in the account.
    #:
    #: **NULL is a third state and it carries the default.** `THE-DAILY.md §5.1`
    #: wants Occasionally for a subscriber and Off for everybody else, which a
    #: column default cannot express because it does not know the tier. Worse,
    #: a default of "off" written into the column would be indistinguishable
    #: from somebody who chose off — and then subscribing would silently switch
    #: their notifications back on. `rules.preference_of` resolves the NULL.
    daily_push: Mapped[str | None] = mapped_column(String(24))
    #: The hour, in the person's own clock, the daily may arrive at. Editable
    #: because "I get up at 05:30" is a real fact about somebody and the only
    #: one they can tell us that we cannot measure — but clamped outside quiet
    #: hours by `rules.delivery_hour`, so setting 03:00 and then complaining
    #: about a 03:00 notification is not a state this system can be put into.
    daily_hour: Mapped[int | None] = mapped_column(Integer)
    #: An override for the delivery clock, for somebody whose device does not
    #: report one or reports the wrong one. Second rung of the ladder in
    #: `rules.zone_for`; the device's own zone still wins when it exists,
    #: because a person who moves changes zones more often than they change
    #: settings.
    daily_timezone: Mapped[str | None] = mapped_column(String(64))

    #: Set when this row was folded into another account. Kept rather than
    #: deleted so an old token still resolves to the surviving user instead of
    #: silently logging someone out mid-purchase.
    merged_into_id: Mapped[str | None] = mapped_column(ForeignKey("user.id"))

    #: **Ленивые, а не `selectin`, и это правка производительности, а не вкуса.**
    #:
    #: `lazy="selectin"` означает: каждый раз, когда откуда угодно загружается
    #: строка `user`, следом уходят ещё два запроса — за профилями и за правами.
    #: Строка `user` загружается на **каждом** запросе к API (`deps.visitor` →
    #: `accounts.resolve`), то есть это были два лишних обращения к базе на
    #: любой вызов, включая те, которым ни профили, ни права не нужны вовсе.
    #:
    #: Платили за них ни за что: ни одна строка в `alma/` не читает
    #: `user.profiles` и `user.entitlements`. Всё, что работает с профилями и
    #: правами, ходит своими запросами — `select(Profile).where(...)` в
    #: `deps.load_profile` и `resolve_birth`, `auth/entitlements.py` за
    #: грантами, `accounts.erase` бьёт `delete(table).where(table.user_id ==
    #: ...)` напрямую. Каскад `delete-orphan` тоже никого не грузил: `User`
    #: никогда не удаляется через `session.delete` — удаление аккаунта это
    #: `erase`, оставляющая надгробие.
    #:
    #: Связи оставлены объявленными: они держат `back_populates` для
    #: `Profile.user` и `Entitlement.user` и описывают форму схемы. Тот, кому
    #: коллекция понадобится, попросит её явно — `selectinload(User.profiles)`
    #: в своём запросе, — и заплатит за неё там, где она нужна.
    profiles: Mapped[list["Profile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    entitlements: Mapped[list["Entitlement"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_guest(self) -> bool:
        return self.provider == AuthProvider.guest.value

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None and self.merged_into_id is None


class Profile(Base):
    """One birth. A user has their own, plus anyone they compare against."""

    __tablename__ = "profile"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)

    name: Mapped[str | None] = mapped_column(String(120))
    relation: Mapped[str | None] = mapped_column(String(40))   # "partner", "friend"
    is_self: Mapped[bool] = mapped_column(Boolean, default=False)
    #: "female" | "male" | NULL. Not an astrological input — the chart does
    #: not care — but Russian grammar does: with a known gender Alma writes
    #: «ты родилась» instead of tiptoeing around the past tense, and the
    #: genderless gate stands down. NULL keeps the old behaviour exactly.
    gender: Mapped[str | None] = mapped_column(String(10))
    #: «Что сейчас важнее всего?» — ответ квиза V0: "love" | "money" | "self" |
    #: "future" | NULL. Не астрология, а сигнал NBO (ТЗ v3 §4): от него зависит
    #: порядок карточек главного экрана и какая глава стоит тизером. NULL —
    #: человек прошёл анкету до появления вопроса или пропустил его; NBO тогда
    #: живёт на одних поведенческих сигналах. Только у is_self-профиля: чужой
    #: интерес не спрашивается.
    interest: Mapped[str | None] = mapped_column(String(10))

    birth_date: Mapped[datetime] = mapped_column(Date)
    #: "HH:MM" or NULL. NULL is a real state, not a missing value: every
    #: system that needs the horizon checks it and refuses rather than
    #: assuming noon.
    birth_time: Mapped[str | None] = mapped_column(String(5))
    #: Какое из двух одинаковых времён имелось в виду, когда часы в ту ночь
    #: переводили назад: "earlier" | "later" | NULL.
    #:
    #: **Без этого поля ответ было некуда положить.** Движок умеет разводить
    #: двойное 02:30 и умеет принять решение — но `birth_from_profile` не
    #: передавал его, и любой расчёт по сохранённому профилю снова упирался в
    #: 409. То есть человек, родившийся в час перевода часов, отвечал на вопрос
    #: и получал его снова, и так каждый раз, до конца.
    #:
    #: NULL значит «не спрашивали», и это верно для подавляющего большинства
    #: рождений: развилка возникает один час в году в каждом поясе.
    on_ambiguous: Mapped[str | None] = mapped_column(String(8))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str] = mapped_column(String(64))
    place_label: Mapped[str | None] = mapped_column(String(200))
    place_id: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(back_populates="profiles")

    __table_args__ = (Index("profile_user_self", "user_id", "is_self"),)


class Entitlement(Base):
    """What a user has paid for. The only thing that unlocks content."""

    __tablename__ = "entitlement"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)

    system: Mapped[str] = mapped_column(String(32))       # "*" for everything
    kind: Mapped[str] = mapped_column(String(16))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: Which processor's money this was. It defaulted to "paddle", so a row
    #: written without one claimed a processor rather than admitting it had
    #: none — and the month a business runs two of them, this column is the only
    #: thing telling their revenue apart. "unknown" is a state somebody can
    #: search for; a wrong name is not.
    source: Mapped[str] = mapped_column(String(32), default="unknown")
    transaction_id: Mapped[str | None] = mapped_column(String(64), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    #: The provider's subscription, when this grant came from one. Indexed
    #: because the only question ever asked of it arrives from a webhook —
    #: "which grant does this renewal, cancellation or dunning notice belong
    #: to" — and that lookup happens while the provider is waiting for a 200.
    subscription_id: Mapped[str | None] = mapped_column(String(64), index=True)

    #: The provider's own word for the subscription's state: "active",
    #: "past_due", "canceled". Recorded for support and never consulted by
    #: `covers` — access is decided by `revoked_at` and `expires_at`, which we
    #: set ourselves. Gating on a free-text string the provider owns means the
    #: day they rename one, everybody who has paid is locked out at once.
    #:
    #: **Sixty-four rather than twenty-four, and the difference is a lost sale.**
    #: This column holds a string *they* choose, and Google Play's
    #: `subscriptionState` enum is spelt in full: the shortest value it can send
    #: is `SUBSCRIPTION_STATE_ACTIVE` at 25 characters and the longest is
    #: `SUBSCRIPTION_STATE_PENDING_PURCHASE_CANCELED` at 44. Every one of them
    #: overflowed the old width. SQLite does not enforce a VARCHAR length, so
    #: the whole test suite passed and would have gone on passing; Postgres
    #: raises `StringDataRightTruncationError`, the webhook handler catches it
    #: and records the delivery as failed, and the subscription is never
    #: written. `_clamp` below is the belt to this braces — the value is a
    #: provider's, so its length is not ours to guarantee.
    status: Mapped[str | None] = mapped_column(String(64))

    @validates("status")
    def _clamp_status(self, _key: str, value: str | None) -> str | None:
        return _clamped(value, 64, "entitlement.status")

    #: When the subscription bills again. Distinct from `expires_at` on
    #: purpose: this is a promise to charge, that is the moment access stops,
    #: and between a cancellation and the end of a paid period they disagree.
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: How wide the grant is: "system" (whatever `system` names), "all"
    #: (everything), or "live" (only what is worth renting). The default is a
    #: *server* default as well as a Python one, so that the same word fills
    #: the column whether the row was written by this process or backfilled by
    #: `migrate.reconcile` onto a table that predates the column — a row that
    #: came back NULL would read as "no scope", and every branch below would
    #: then fall through to the legacy shape by accident rather than by rule.
    scope: Mapped[str] = mapped_column(String(16), default="system", server_default="system")

    user: Mapped[User] = relationship(back_populates="entitlements")

    #: `for_user()` спрашивается на каждом входе в главу, на каждом рендере хаба
    #: и на каждом webhook, и почти всегда следующим вопросом идёт «а какой у
    #: строки scope» — «мои пары», «куплен ли бандл», «есть ли живая подписка».
    #: Одна колонка `user_id` в индексе оставляла базе выбирать строки все, а
    #: фильтровать по scope в памяти; на аккаунте с одной покупкой это незаметно,
    #: на аккаунте, купившем двадцать пар, — двадцать строк на каждый чих.
    __table_args__ = (Index("entitlement_user_scope", "user_id", "scope"),)

    def covers(
        self,
        system: str,
        *,
        chapter: str | None = None,
        partner_id: str | None = None,
        at: datetime | None = None,
    ) -> bool:
        """Whether this entitlement opens a system, or one chapter of one.

        `system` on the row is either "*" (everything), a system slug, the
        "slug:chapter" form a single-chapter purchase writes, or the
        "pair:{profile_id}" form a compatibility purchase writes. A
        system-level grant covers every chapter in it; a chapter-level grant
        covers exactly one and must not leak into the rest.

        `scope` overrides that shape where a plan needs a different one. "all"
        is an everything-grant said outright instead of inferred from a "*".
        "static" is the bundle: the five readings that are fixed at birth, and
        deliberately not the two that recompute — a transit reading sold once
        and kept is a subscription we forgot to charge for. "pair" is one
        report about one person. "live" is the legacy recurring plan and covers
        only the systems that change with the date.

        **Порядок веток здесь — то же правило, что в `entitlements.covers` и
        `unlocked_systems`, и по той же причине.** Все три спрашивают scope до
        легаси-сентинела `system == "*"`: подписка выписывается с `system="*"`,
        и если сентинел проверить раньше, хаб и вход в главу ответят по-разному
        про одну и ту же строку. Новый scope добавляется во все три места сразу
        или ни в одно.
        """
        moment = as_utc(at) or utcnow()
        if self.revoked_at is not None:
            return False
        expires = as_utc(self.expires_at)
        if expires is not None and expires <= moment:
            return False

        if self.scope == "pair":
            # Оплачен отчёт про конкретного человека, а не система. Сравнение
            # идёт по обеим половинам: без проверки `system == "compatibility"`
            # грант пары открыл бы натал, без проверки имени партнёра — все
            # пары разом за одну покупку.
            return system == "compatibility" and self.system == f"pair:{partner_id}"
        if self.scope == "live":
            # Imported inside the method rather than at module scope: what is
            # on sale is the catalogue's business, and the schema has to stay
            # importable without dragging the billing package in behind it.
            from ..billing.catalogue import LIVING_SYSTEMS

            return system in LIVING_SYSTEMS
        if self.scope == "static":
            # Импорт внутри метода и из `auth`, а не из каталога: «какие
            # системы статичны» — свойство самих систем, а не полки, и держать
            # ответ в двух местах значит однажды продать бандл, который
            # открывает четыре разбора из пяти.
            from ..auth.entitlements import STATIC_SYSTEMS

            return system in STATIC_SYSTEMS
        if self.scope == "all":
            return True

        if self.system == "*" or self.system == system:
            return True
        return chapter is not None and self.system == f"{system}:{chapter}"


class Purchase(Base):
    """The money trail, kept separately from what it unlocked.

    An entitlement can be granted for reasons other than a payment — support
    putting something right — and a payment can arrive that we have not yet
    turned into an entitlement. Keeping them apart means neither one has to
    lie about the other.
    """

    __tablename__ = "purchase"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))

    #: See `Entitlement.source` for why this does not default to a processor.
    provider: Mapped[str] = mapped_column(String(16), default="unknown")
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    checkout_id: Mapped[str | None] = mapped_column(String(64))
    price_id: Mapped[str | None] = mapped_column(String(64))
    product: Mapped[str | None] = mapped_column(String(64))
    #: Set on every payment that belongs to a subscription, including the
    #: renewals. Without it the second month's charge is an anonymous payment
    #: and the refund conversation starts with us not knowing what it was for.
    subscription_id: Mapped[str | None] = mapped_column(String(64), index=True)

    #: The address the **processor** collected from the buyer, when it tells us.
    #:
    #: Deliberately not `User.email`, and the distinction is a security one
    #: rather than a tidiness one: that column is the sign-in identity, and
    #: `accounts.by_email` merges a guest into whoever holds it — so an
    #: unverified address typed at a checkout, written there, would be an
    #: account-takeover primitive. Here it is what it is: a fact about one
    #: payment. It is what lets a guest who bought without signing in get a
    #: receipt and a warning before the next charge, which the whole guest
    #: funnel previously got neither of.
    buyer_email: Mapped[str | None] = mapped_column(String(320))

    #: What happened to this payment, in the processor's vocabulary — either
    #: its event type outright, or `type:action` when the event was an
    #: adjustment. Sixty-four for the same reason as `Entitlement.status`: the
    #: strings are long and they are not ours. `adjustment.updated:chargeback`
    #: is 29 characters and Dodo's `subscription.update_payment_method` is 34,
    #: so a refund written on Postgres against the old 24-character column
    #: raised, the webhook was recorded as failed, and the money came back to
    #: the buyer while the entitlement stayed open. Four tests in
    #: `test_billing.py` reproduce exactly that once the suite is pointed at a
    #: real Postgres, and pass on SQLite either way.
    status: Mapped[str] = mapped_column(String(64), default="pending")

    @validates("status")
    def _clamp_status(self, _key: str, value: str | None) -> str | None:
        return _clamped(value, 64, "purchase.status")

    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    #: How much of `amount_cents` has been given back, in the same currency.
    #: A separate column rather than a second Purchase row, because a refund
    #: written as its own row is a positive amount in the money trail: every
    #: revenue sum over this table then counts the refund as revenue and the
    #: purchase it reduces still reads as collected in full. It is also the
    #: only way to tell a partial refund from a full one, which is the
    #: difference between reducing a charge and closing an entitlement.
    refunded_cents: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    country: Mapped[str | None] = mapped_column(String(2))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Set only when the whole charge has come back. A partial refund moves
    #: `refunded_cents` and leaves this NULL, because the purchase is still a
    #: purchase and what it bought is still owed to the buyer.
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class PairIntent(Base):
    """Про кого была открыта покупка пары — записанное до того, как её оплатили.

    **Зачем вообще нужна таблица.** `pair.check` расходуемый: он покупается
    столько раз, сколько партнёров человек проверит, и каждая покупка — это
    отчёт про *конкретного* человека. Магазин про наших людей ничего не знает:
    Apple подписывает `productId` и `transactionId`, Google отдаёт токен
    покупки, и ни в одном из двух пейлоадов нет поля «Маша». Значит, связь
    «этот платёж — про этого партнёра» может быть либо словом клиента, либо
    нашей записью, сделанной *до* оплаты. Слово клиента здесь непригодно: тело
    `/billing/iap/verify` пишет приложение, а подписанный магазином факт — нет,
    и разница между ними ровно та, из-за которой чужой профиль можно было бы
    открыть за $4.99 подменой одного поля.

    Поэтому механика такая: клиент просит intent, сервер запоминает пару
    (аккаунт, профиль) и выдаёт `app_account_token`; клиент кладёт этот токен в
    магазинную покупку (`appAccountToken` у Apple, `obfuscatedProfileId` у
    Play); магазин возвращает его нам **внутри подписанного пейлоада**. Токен —
    это то единственное, что проходит через магазин и остаётся нашим.

    `profile_id` — обычная строка, а не внешний ключ, и это осознанно: профиль
    партнёра можно удалить, а грант, за который заплачено, обязан пережить
    удаление (А7, случай 12). Внешний ключ с CASCADE стёр бы историю покупки
    вместе с профилем, а с RESTRICT — запретил бы удалять профиль, то есть
    превратил бы одну покупку в вечную запись в чужом аккаунте.
    """

    __tablename__ = "pair_intent"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    #: Чей отчёт покупается. Проверен на принадлежность аккаунту и на `is_self`
    #: в момент создания intent — то есть до того, как деньги ушли.
    profile_id: Mapped[str] = mapped_column(String(32), index=True)

    #: То, что уедет в магазин и вернётся оттуда подписанным. UUID-строка,
    #: потому что Apple принимает в `appAccountToken` только UUID; выводится
    #: детерминированно из `id` (см. `billing.pairs.token_for`) и всё равно
    #: **хранится**, потому что обратный вопрос — «чей это токен» — задаётся на
    #: каждой верификации, и один индексированный поиск дешевле, чем перебор
    #: всех intent'ов аккаунта с пересчётом.
    app_account_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    #: Когда intent закрыт покупкой. Не удаляется, а помечается: незакрытые
    #: intent'ы — это брошенные покупки, и их количество рядом с количеством
    #: закрытых есть та самая воронка «открыл магазин и передумал».
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Какой транзакцией закрыт. Нужен ровно для разбора инцидента: «за что
    #: человек заплатил и что мы ему за это открыли» должно читаться с одной
    #: строки, без соединения трёх таблиц по времени.
    transaction_id: Mapped[str | None] = mapped_column(String(64), index=True)


class PairCredit(Base):
    """Проверка пары, включённая подписчику в один расчётный период.

    **Отдельная таблица, а не колонка в `Entitlement`, и это не вкусовщина.**
    Грант подписки — строка, которую `entitlements.grant` переписывает на месте
    при каждом продлении, при смене плана и при восстановлении после отмены;
    счётчик, живущий в ней, обнулялся бы вместе с любым из этих событий — то
    есть подписчик получал бы новую бесплатную пару за каждый апгрейд. Кредит
    обязан пережить смену гранта, поэтому он живёт своей строкой.

    **Период берётся из `renews_at` подписки, а не из календарного месяца.**
    Человек, подписавшийся 31 января, не должен получать вторую проверку
    первого февраля; человек, подписавшийся первого числа, не должен ждать
    лишних дней. Календарь тут вообще ни при чём: расчётный период — это то,
    что магазин назвал следующей датой списания.

    Неиспользованный кредит не переносится: `granted` и `used` живут внутри
    своего периода, следующая строка начинается с нуля. Это обещание копирайта
    («1 проверка в этом месяце»), и накопление сделало бы из подписки счёт,
    который однажды предъявят целиком.
    """

    __tablename__ = "pair_credit"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)

    #: Границы расчётного периода. `period_end` — это `renews_at` подписки на
    #: момент открытия строки (а если продлевать уже нечего — `expires_at`),
    #: и именно он отвечает на вопрос «тот же это период или следующий».
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    #: Сколько включено и сколько потрачено. `granted` хранится, а не читается
    #: из каталога на лету: если завтра подписка станет давать две проверки,
    #: прошлые периоды обязаны остаться такими, какими их продали.
    granted: Mapped[int] = mapped_column(Integer, default=1)
    used: Mapped[int] = mapped_column(Integer, default=0)

    #: Чей это был цикл. Нужен, когда у аккаунта в истории две подписки: без
    #: него нельзя отличить «новый период той же подписки» от «первый период
    #: новой».
    subscription_id: Mapped[str | None] = mapped_column(String(64), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    #: **Ограничение — это и есть защита от двойного начисления.** Два
    #: одновременных продления (нотификация магазина и наш собственный
    #: `/iap/verify` по одному и тому же платежу) считают одно и то же начало
    #: периода и оба пробуют вставить строку; выживает одна. Без него защита
    #: была бы «сначала посмотрели, потом записали», то есть гонкой, которая
    #: стоит $4.99 за каждый выигранный заезд.
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", name="pair_credit_period"),
    )


class Consent(Base):
    """What a buyer ticked at a checkout, in the words they were shown.

    **The trader carries the burden of proving this.** A buyer of digital
    content loses the 14-day right of withdrawal only on three conditions
    (CRD Art. 16(m)): prior express consent, an acknowledgement that the right
    goes with it, and confirmation on a durable medium. The receipt is the
    third. This table is the first two, and without it they existed only as two
    booleans in a browser that no longer exists — every waiver unprovable, and a
    receipt quoting sentences from a template rather than from anything the
    buyer did.

    Written when the checkout is opened rather than when the money lands,
    because that is when the consent happened and because the two are separated
    by a processor, a browser and a retry. `transaction_id` is filled in later,
    by the webhook, and is what turns a statement of intent into part of a
    contract: a row that never gets one is somebody who ticked two boxes and
    then closed the tab, which is evidence of nothing and is deleted on erasure
    rather than kept.

    `statements` is a list of `{key, text}` — the **exact sentences**, not a
    summary. Art. 16(m) asks for the consent to be confirmed, and a paraphrase
    reconstructed six months later from a template proves only what the
    template said today.
    """

    __tablename__ = "consent"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    #: Nullable for the same reason `Purchase.user_id` is: an erased account
    #: detaches from the record of a contract it entered into, and the record
    #: stays because a contract is not ours alone to delete.
    user_id: Mapped[str | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"), index=True)
    #: The catalogue key the checkout was opened for. Half of the lookup that
    #: joins this to a payment — a person may open two checkouts for different
    #: things and only pay for one, and the consent that belongs to the money is
    #: the one for the product the money bought.
    product: Mapped[str] = mapped_column(String(64), index=True)
    #: The language the sentences were read in, as the browser reported it.
    locale: Mapped[str] = mapped_column(String(8), default="en")
    #: When the buyer ticked, by their own clock. Recorded beside `created_at`
    #: rather than instead of it: one is what the client says happened and the
    #: other is when we heard about it, and a dispute is argued over the gap.
    agreed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    statements: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    #: Set by the webhook when a payment claims this consent. Indexed because
    #: that is the only question ever asked of it after the fact — "what did the
    #: person who paid for this transaction agree to".
    transaction_id: Mapped[str | None] = mapped_column(String(64), index=True)


class WebhookEvent(Base):
    """Every webhook we have seen, so that none is processed twice.

    Payment providers retry, and they are right to. Idempotency has to live
    on our side, and it has to be a database constraint rather than a code
    path — a duplicate grant is a real product bug and a race is exactly how
    it happens.

    `payload` is the delivery **verbatim**, which is what support reads at two
    in the morning and is also the reason `user_id` exists: a processor's body
    carries the buyer's name, email address and billing country, so these rows
    hold personal data whether or not we ever look at it. Without a column
    saying whose it is, an erasure request could not find them — the table has
    no other link to a person — and "we delete everything" would have been a
    sentence with an undisclosed exception behind it. See `accounts.erase`.
    """

    __tablename__ = "webhook_event"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(16), default="unknown")
    event_type: Mapped[str] = mapped_column(String(64))
    #: Whoever this delivery turned out to be about, once the router has worked
    #: it out — from our own sealed metadata, or from the purchase or the
    #: subscription it undoes. A plain string and not a foreign key for the
    #: reason spelled out on `Event.user_id`: `erase` leaves the `user` row as a
    #: tombstone, so a CASCADE would never fire and would be a rule that is true
    #: in every test and false in production.
    user_id: Mapped[str | None] = mapped_column(String(32), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class Reading(Base):
    """Generated prose, stored so it never changes under the reader.

    A reading a person paid for and came back to must say the same thing the
    second time. Regenerating on every view would be cheaper to build and
    would quietly destroy the product: the whole promise is that this is
    *your* reading, not a fresh guess each visit.
    """

    __tablename__ = "reading"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id", ondelete="CASCADE"))

    system: Mapped[str] = mapped_column(String(32))
    chapter: Mapped[str | None] = mapped_column(String(64))
    locale: Mapped[str] = mapped_column(String(8), default="en")

    calc_key: Mapped[str] = mapped_column(String(64), index=True)
    engine_version: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(64))

    body: Mapped[dict] = mapped_column(JSON, default=dict)
    cited_factors: Mapped[list] = mapped_column(JSON, default=list)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_cents: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "system", "chapter", "calc_key", "locale", name="reading_once"),
    )


class CalcCacheEntry(Base):
    """Content-addressed calculation results, shared across every user.

    The key already folds in the engine version, so this table never needs
    invalidating — a version bump makes old rows unreachable and they age out.
    """

    __tablename__ = "calc_cache"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    system: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    hits: Mapped[int] = mapped_column(Integer, default=0)


class ChatThread(Base):
    __tablename__ = "chat_thread"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("profile.id", ondelete="SET NULL"))
    title: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    thread_id: Mapped[str] = mapped_column(
        ForeignKey("chat_thread.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(12))         # "user" | "alma"
    body: Mapped[str] = mapped_column(Text)
    cited_factors: Mapped[list] = mapped_column(JSON, default=list)
    #: What kind of turn this was, in the vocabulary the clients decode:
    #: "reading" | "chart_silent" | "conversation". Nullable, and null is the
    #: honest value for every row written before the column existed — a
    #: conversation read back cannot be re-classified after the fact, and a
    #: client that is told nothing draws nothing. Without it a reopened thread
    #: rendered every turn as an ordinary reply while the live one rendered the
    #: same turn with its note, which is a disagreement between two screens
    #: showing the same message.
    turn_kind: Mapped[str | None] = mapped_column(String(16))
    #: Глава, на которую опирался этот ответ: `{"system", "slug", "title"}`.
    #:
    #: **Та же болезнь, что лечил `turn_kind`, в другом поле.** Карточка «из
    #: главы» существовала только в теле живого ответа: человек возвращался в
    #: беседу назавтра, и дверь в главу, из которой ответ вырос, исчезала — при
    #: том что сам ответ на неё ссылался словами. Живой экран и поднятый с
    #: сервера показывали одно сообщение по-разному, а это ровно то состояние,
    #: ради которого вью на нативе и сделали общей.
    #:
    #: Хранится готовая тройка, а не пара «система/слаг». Заголовок переведён на
    #: язык **того запроса**, в котором ответ родился, и это правильный
    #: заголовок для этой реплики: беседа — запись разговора, а не витрина,
    #: которая перерисовывается под текущую локаль. Пересчёт на чтении стоил бы
    #: похода в каталог на каждое сообщение ради строки, которая уже написана.
    #:
    #: Nullable, и null — честное значение и для всякой строки до этой колонки,
    #: и для всякого хода, где главу назвать было нельзя: сервер называет её
    #: только когда в контексте была ровно одна написанная глава.
    source_chapter: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model: Mapped[str | None] = mapped_column(String(64))
    cost_cents: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    thread: Mapped[ChatThread] = relationship(back_populates="messages")


class Memory(Base):
    """What Alma remembers about a person between conversations.

    Deliberately a small, explicit table rather than a growing transcript.
    A reading that references something the reader said three months ago is
    the difference between a product and a toy — but only if what is stored
    is inspectable and deletable, which a compressed history is not.
    """

    __tablename__ = "memory"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))        # "fact" | "concern" | "preference"
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsageCounter(Base):
    """Per-user, per-day counters — questions asked, money spent."""

    __tablename__ = "usage_counter"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)   # user_id:day:metric
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    day: Mapped[datetime] = mapped_column(Date, index=True)
    metric: Mapped[str] = mapped_column(String(32))
    count: Mapped[int] = mapped_column(Integer, default=0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)


class RateWindow(Base):
    """Потолок «столько-то раз за окно», общий для всех рабочих процессов.

    **Зачем отдельная таблица, а не `UsageCounter` рядом.** Счётчики выше
    считаются на `user.id`, и колонка — внешний ключ в `user` с
    `ON DELETE CASCADE`. Всё, что ограничивают ограничители на входе, случается
    **до** аккаунта и часто вместо него: гость ещё не заведён (это его и
    ограничивают), у маяка воронки аккаунта нет по замыслу, а письмо со ссылкой
    входа считается по адресу получателя, который нам может быть вообще
    незнаком. Писать такой ключ в `usage_counter.user_id` нельзя — это либо
    выдуманная строка `user` (ровно то, от чего уходили), либо висячий ключ в
    ограниченной колонке. Тот же довод уже записан в
    `funnel.spend_anonymous_allowance`.

    **Ключ здесь — отпечаток, а не то, что его породило.** `key_digest` —
    blake2b от «источника» (сетевой адрес или почтовый ящик), и обратно оно не
    разворачивается. Это не гигиена ради гигиены: privacy-страница обещает, что
    аналитика не хранит IP-адресов (`event` — пять колонок и ни одной такой), а
    таблица потолков, набитая живыми адресами посетителей, сделала бы это
    обещание неправдой через заднюю дверь. Отпечатка хватает на всё, что
    ограничителю нужно, — сравнить «этот же или другой».

    **Строка одна на (ограничитель, окно, источник).** Окно фиксированное и
    входит в первичный ключ номером, поэтому новое окно — это новая строка, а
    старая просто перестаёт кем-либо читаться. Отсюда `expires_at` и чистка:
    `tools/prune.py` удаляет истёкшие, и без неё таблица растёт по числу
    посетителей. Индекса по `expires_at` хватает — чистка ходит по нему одним
    диапазоном.
    """

    __tablename__ = "rate_window"

    #: `{имя ограничителя}:{номер окна}:{отпечаток ключа}`. Ширина с запасом:
    #: имя до 24 символов, номер окна — секунды эпохи, делённые на длину окна
    #: (10 цифр), отпечаток — 32 шестнадцатеричных символа.
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    #: Когда эта строка перестаёт что-либо значить. Читает только чистка.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class MagicLink(Base):
    """A single-use sign-in token. Stored hashed — the mail is the secret."""

    __tablename__ = "magic_link"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    guest_user_id: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Event(Base):
    """Product analytics. No third-party script, no personal data in the name.

    Six columns, and the discipline is entirely in what is *not* here. There
    is no IP address, no user agent, no referrer, no full URL, no device
    identifier, and no free-text field — each of those is a thing the privacy
    page would then have to admit to, and that page's whole value is that its
    list is short and complete. `alma/funnel.py` owns which names may be
    written and which keys may go in `properties`; both are closed sets,
    because an analytics table that accepts anything is one that eventually
    contains a birth date.

    **Either identifier may be absent, and that is the shape of the product.**
    A row written before anybody has given us anything has `anon_id` and no
    `user_id`; a row written by a signed-in person on a device that never sent
    one has `user_id` and no `anon_id`; most rows have both. What may never
    happen is a row with neither, because a row nothing can be counted against
    is a row that inflates a total and joins to nothing — `funnel.record`
    refuses it.

    `anon_id` is deliberately *not* the session identifier the paragraph above
    says is absent. It does not change per visit, it is not derived from the
    device or the browser, and it carries no information: it is a random string
    the client generates and keeps, which exists so that "of the people who saw
    the landing, how many finished" can be answered without minting an account
    for somebody who only looked. `AnonymousVisitor` is how it stops being
    anonymous, on the day its owner does something worth keeping. The privacy
    page names it, and `funnel.PURGE_AFTER_DAYS` bounds how long it lives.

    `user_id` is a plain string rather than a foreign key, which is a
    compromise rather than a preference. The constraint belongs here — these
    rows are a person's, and they should die with the account — but SQLite
    cannot add one to a table that already exists and `migrate.reconcile` is
    deliberately incapable of rewriting a table, so declaring it would make the
    rule true on every database built from scratch, including every test, and
    silently false on the one that is live. Erasure is therefore an explicit
    delete in `accounts.erase`; `funnel.forget` is the sentence for it.
    """

    __tablename__ = "event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: Indexed for one query only: erasing everything one account ever sent.
    user_id: Mapped[str | None] = mapped_column(String(32), index=True)
    #: The browser or app installation this came from, when there was no
    #: account yet. Indexed for two: the day's write allowance for a caller who
    #: has no account to count against, and erasing the rows of one that later
    #: had one.
    anon_id: Mapped[str | None] = mapped_column(String(64), index=True)
    #: One of `funnel.STAGE_NAMES`. Not indexed on its own — the composite
    #: below leads with it, so a second index over the same column would be
    #: paid for on every insert and read by nothing.
    name: Mapped[str] = mapped_column(String(64))
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    #: The funnel query, exactly: for each stage in a date range, the distinct
    #: accounts that reached it. This is the one table in the schema that grows
    #: with traffic rather than with customers, and the query over it runs
    #: across every row of a month.
    #:
    #: `anon_id` is deliberately **not** appended to it, although the query now
    #: reads that column too and a four-column index would cover the whole read.
    #: Adding it would change the definition of an index that already exists on
    #: the live database under this name, and `migrate.reconcile` creates
    #: missing indexes rather than rebuilding present ones — so the declaration
    #: here would be true of every database built from scratch, including every
    #: test, and quietly false of the only one that matters. The lookup falls
    #: back to the table for one column, which is a cost; a schema the code
    #: describes wrongly is a bug.
    __table_args__ = (Index("event_stage_window", "name", "created_at", "user_id"),)


class AnonymousVisitor(Base):
    """The one row that turns a browser id into an account id, and when.

    Without it the funnel has traded one broken measurement for another. Stages
    recorded before anybody gives us anything are attributed to a random string
    in a browser; the account is minted later, at the birth save or the sign-in,
    and every stage after that is attributed to its id. Two identities, one
    person, and "of the people who saw the landing, how many finished" reads as
    zero on data that looks perfectly healthy — which is the failure the whole
    table was built to stop.

    **The claim is written once and never moved.** The alternative — re-point
    the id at whichever account most recently appeared with it — was rejected
    because it silently rewrites history: a shared browser where a second person
    signs in would move the first person's landing view onto the second person's
    account, and nothing in the funnel would look wrong. First claim wins means
    the worst case is a second account whose early stages are missing, which is
    visible as a gap between `reached` and `total` rather than invisible.

    **But first-claim-wins is only half a rule, and on its own it fails in the
    mirror image of the case it was written against.** The paragraph above used
    to be the whole argument, and it was wrong about which way round the damage
    runs. Re-pointing would move the *first* person's rows onto the *second*
    person's account; never re-pointing moved the *second* person's rows onto
    the *first* person's account, which is worse in every direction that
    matters. The second person's steps improved a conversion rate they were not
    part of; their own erasure could not reach rows filed under somebody else's
    claim; and the first person's erasure quietly deleted a stranger's. None of
    that showed up as a gap between `reached` and `total`, because it did not
    look like a gap — it looked like one person having a very good day.

    So the claim is bounded in time as well as in ownership. `funnel.audience`
    resolves a bare id to this account for the rows recorded up to the claim and
    counts anything arriving long afterwards as an identity of its own, because
    after the claim the browser that owns the account sends a token and a row
    without one is not that session. `funnel.CLAIM_GRACE` is the width of the
    boundary and says why it is not zero.

    `anon_id` is the primary key, so the rule is the database's rather than a
    convention this module hopes callers keep. A racing second claim collides
    and is discarded — see `funnel.claim`, which expects that and treats it as
    the answer rather than as an error.

    It is separate from `user` on purpose. An account row should not accumulate
    the identifiers a person was measured under before they had an account: this
    is the funnel's own join table, it is listed on the privacy page as such,
    and deleting it is one statement in `funnel.forget`.
    """

    __tablename__ = "anonymous_visitor"

    anon_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    #: A plain string for the same reason `Event.user_id` is one.
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DeviceToken(Base):
    """One installation of the app on one phone, and how to reach it.

    A push token is a persistent identifier for a specific install on a
    specific device, stored against a `user_id` and useful only joined to one.
    It is personal data in the GDPR sense, a **Device ID** on Apple's privacy
    form and **Device or other IDs** on Play's, which is why the retention
    rules in `alma/notify/tokens.py` are rules rather than habits.

    **The row is the consent.** Turning the daily off deletes it rather than
    setting a flag something remembers to check before sending. Apple's
    guideline 4.5.4 requires an in-app way to stop receiving push, and the
    simplest proof that off means off is that there is nothing left to send to.
    Preference values that still want *some* push — "occasionally", "only what
    matters" — keep the row; only Off removes it.

    **Three columns exist because a wrong one of them is a silent failure.**

    `environment` is the whole of `docs/PUSH.md §1.8`: an Apple device token is
    only meaningful in the environment that issued it, TestFlight builds carry
    `aps-environment: production` however much they feel like testing, and a
    backend that picks the host from a deployment-wide setting will send every
    beta tester's notification into the void. Stored per token, the sender
    picks the host per token, and a production backend can serve a developer's
    simulator without a config change.

    `timezone` is the device's own IANA zone, persisted rather than read from a
    request header per response. The notification job runs on a schedule and
    has no request to read a header from; `Profile.timezone` is the *birth*
    zone, so using it would push somebody born in Lisbon and living in Toronto
    at three in the morning.

    `locale` is the language the phone is set to, which is not always the
    language the account chose. The payload carries a localisation key and
    arguments rather than a sentence (`docs/PUSH.md §1.6`), and the arguments
    are substituted verbatim — so the server has to translate the two or three
    words it sends, and this column is how it knows into what.

    Unique on `(platform, token)` and not on `(user_id, token)`: a token
    identifies an install, and if the same install turns up under a second
    account the row moves rather than doubling. Two rows for one device is two
    notifications for one morning, which is the failure this whole feature is
    built to avoid.
    """

    __tablename__ = "device_token"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    #: A plain string rather than a ForeignKey, for the reason `Event.user_id`
    #: gives: `accounts.erase` keeps the `user` row as a tombstone, so a CASCADE
    #: would never fire and would be a rule true in every test and false in
    #: production. `notify.tokens.forget` is the sentence that deletes these.
    user_id: Mapped[str] = mapped_column(String(32), index=True)

    platform: Mapped[str] = mapped_column(String(8))          # "ios" | "android"
    token: Mapped[str] = mapped_column(String(512))
    #: "production" | "sandbox". Meaningless on Android and set to "production"
    #: there rather than left null, so the column never has to be read as a
    #: three-state.
    environment: Mapped[str] = mapped_column(String(16), default="production")

    timezone: Mapped[str | None] = mapped_column(String(64))
    locale: Mapped[str | None] = mapped_column(String(8))
    app_version: Mapped[str | None] = mapped_column(String(32))
    os_version: Mapped[str | None] = mapped_column(String(32))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    #: Bumped every time the client re-registers, which it does on every launch.
    #: The retention sweep reads this rather than `created_at`, per Google's own
    #: guidance to stamp a timestamp on every upload and sweep on the timestamp.
    #: It is also what makes a stale 410 safe to ignore: if the app has told us
    #: it is alive more recently than APNs told us otherwise, the app wins.
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fail_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    #: Set when we have stopped trying and the token is nonetheless not dead —
    #: an environment mismatch, a wrong topic, a credential that does not match
    #: the build. Those must not be deleted, because the client would register
    #: the identical token again on the next launch and the loop would start
    #: over; and they must not be retried forever either. A dead token — 410,
    #: `Unregistered`, `UNREGISTERED` — is deleted outright and never reaches
    #: these two columns.
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_reason: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        UniqueConstraint("platform", "token", name="device_token_once"),
        Index("device_token_user_platform", "user_id", "platform"),
    )


class Setting(Base):
    """Anything an operator must be able to change without a deploy.

    Prices, prompts, limits. A code deploy to change a price is a code deploy
    that happens at the worst possible time.
    """

    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    updated_by: Mapped[str | None] = mapped_column(String(120))
