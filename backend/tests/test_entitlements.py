"""The paywall's rules, tested as rules rather than as arithmetic.

Each test here names a decision that money depends on: how wide each grant
reaches, what a subscription does *not* include, and which of three tiers a
person is in. None of them re-runs the implementation and compares it to
itself — the numbers are derived from the catalogue and the definitions, so a
change that quietly reverses a rule fails here instead of in a bank statement.

**Что отсюда убрано и почему.** Первая треть файла проверяла кредитный добор:
самая дорогая покупка внутри тридцатидневного окна, потолок кредита, отказ
считать кредит через валюту. Монетизация v3 сняла с продажи и `archive`, и
`archive-upgrade`, и `archive-bump` — значит нет цены, в которую этот кредит
можно было бы превратить, — а вместе с ними ушли `annual_credit`,
`list_price_cents` и `CREDIT_*`. Тесты удалены целиком, а не закомментированы:
закомментированный тест — это обещание вернуться, которого никто не давал.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from conftest import database_url, run_async

from alma.auth import accounts, entitlements
from alma.calc.contract import SYSTEMS
from alma.db import session as session_module
from alma.db.models import Entitlement, EntitlementKind, utcnow


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A fresh database, driven synchronously through a small runner."""
    from alma import config as config_module

    # Disposed before the URL is chosen: on Postgres `database_url` empties
    # the schema, and a connection still pooled from the previous test would
    # turn that drop into a lock wait.
    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "ents.db"))
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()
    run_async(session_module.create_all)

    def run(coro_factory):
        async def wrapper():
            async with session_module.session_scope() as session:
                return await coro_factory(session)

        return run_async(wrapper)

    yield run
    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


# ── the three tiers ────────────────────────────────────────────────────────

def test_a_person_with_nothing_is_free(db):
    async def work(session):
        return await entitlements.tier_of(session, await accounts.create_guest(session))

    assert db(work) == "free"


def test_a_one_time_purchase_makes_an_owner(db):
    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t1"
        )
        return await entitlements.tier_of(session, user)

    assert db(work) == "owner"


def test_a_live_plan_makes_a_subscriber_and_an_expired_one_does_not(db):
    """The tier follows the money that is still arriving, not the money that did."""

    async def work(session):
        user = await accounts.create_guest(session)
        plan = await entitlements.grant(
            session, user, system="*", kind=EntitlementKind.monthly.value,
            subscription_id="sub_1", duration=timedelta(days=31),
        )
        while_live = await entitlements.tier_of(session, user)

        plan.expires_at = utcnow() - timedelta(days=1)
        await session.flush()
        return while_live, await entitlements.tier_of(session, user)

    assert db(work) == ("subscriber", "free")


def test_every_recurring_product_we_sell_makes_a_subscriber(db):
    """Whatever renews, in whatever plan, reads as a subscriber.

    This used to be a set of kind strings written next to the tier function,
    and it was one plan behind the moment the monthly was priced: a person
    paying us every month was billed as a subscriber, answered as a free user
    on the cheapest model, and rationed to three questions a day.
    """
    from alma.billing.catalogue import PRODUCTS

    kinds = sorted({item.kind for item in PRODUCTS.values() if item.interval})
    assert kinds, "the catalogue must sell something that renews"

    async def work(session):
        tiers = {}
        for kind in kinds:
            user = await accounts.create_guest(session)
            await entitlements.grant(
                session, user, system="*", kind=kind,
                subscription_id=f"sub_{kind}", duration=timedelta(days=31),
            )
            tiers[kind] = await entitlements.tier_of(session, user)
        return tiers

    for kind, tier in db(work).items():
        assert tier == "subscriber", f"a {kind} plan reads as {tier}"


def test_a_subscriber_who_also_bought_something_is_still_a_subscriber(db):
    """Two states at once resolve to the one that keeps paying us."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t1"
        )
        await entitlements.grant(
            session, user, system="*", kind=EntitlementKind.monthly.value,
            subscription_id="sub_1", duration=timedelta(days=31),
        )
        return await entitlements.tier_of(session, user)

    assert db(work) == "subscriber"


def test_a_kind_we_never_sold_is_not_an_owner(db):
    """A grant made by hand must not be handed the paying account's budget.

    The tier is matched against the kinds we know we were paid for, rather
    than being "anything that is not nothing" — the day support grants a
    week of something to apologise for an outage, that account should not
    acquire an owner's spending ceiling along with it.
    """

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system="natal", kind="comp",
            transaction_id="t1", duration=timedelta(days=7),
        )
        return await entitlements.tier_of(session, user)

    assert db(work) == "free"


def test_a_revoked_purchase_drops_the_tier(db):
    async def work(session):
        user = await accounts.create_guest(session)
        held = await entitlements.grant(
            session, user, system="natal", kind="one_time", transaction_id="t1"
        )
        await entitlements.revoke(session, held)
        return await entitlements.tier_of(session, user)

    assert db(work) == "free"


# ── the live subscription is not the archive ───────────────────────────────

def test_a_live_subscription_does_not_unlock_the_archive(db):
    """The subscription sells what changes. The archive is bought once.

    A scope the hub does not recognise used to be no scope at all, and the
    only branch that answered "everything" was the one that meant everything.
    A subscriber who found the natal report already open would never buy it.
    """
    living = entitlements.living_systems() & set(SYSTEMS)
    archive = set(SYSTEMS) - living
    assert living and archive, "a live plan must cover some systems and not others"

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE,
            kind=EntitlementKind.monthly.value, subscription_id="sub_1",
            duration=timedelta(days=31),
        )
        unlocked = await entitlements.unlocked_systems(session, user)
        # `transits`, а не первая по алфавиту живая система: первая —
        # `compatibility`, а её `check` без партнёра справедливо считает
        # ошибкой вызова. Спрашивать здесь надо про систему, у которой вопрос
        # «открыта ли» вообще имеет ответ без второго человека.
        opens = await entitlements.check(session, user, "transits")
        stays_shut = await entitlements.check(session, user, sorted(archive)[0])
        return unlocked, opens.allowed, stays_shut.allowed

    unlocked, opens, stays_shut = db(work)
    assert unlocked == living
    assert opens is True
    assert stays_shut is False


def test_a_live_plan_spelled_the_way_the_catalogue_spells_it(db):
    """The shape a real subscription actually has: `system="*"`, `scope="live"`.

    That is what `PRODUCTS["monthly"]` produces, and `unlocked_systems` tested
    the legacy `system == "*"` sentinel *before* the scope — so it matched
    first and handed the subscriber all eight systems, while `covers()`, which
    reads scope first, refused seven of them. The hub drew the natal report as
    owned and opening it was refused. The existing test above passed only
    because it grants with `system="live"`, a spelling the catalogue never
    produces.
    """
    living = entitlements.living_systems() & set(SYSTEMS)

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.EVERYTHING,
            kind=EntitlementKind.monthly.value, scope=entitlements.SCOPE_LIVE,
            subscription_id="sub_live", duration=timedelta(days=31),
        )
        return (
            await entitlements.unlocked_systems(session, user),
            (await entitlements.check(session, user, "natal")).allowed,
            (await entitlements.check(session, user, "transits")).reason,
        )

    unlocked, natal, reason = db(work)
    assert unlocked == living
    assert natal is False
    assert "subscription" in reason, "a monthly plan is not the annual plan"


# ── which prices may be put in front of whom ───────────────────────────────

def test_every_shelf_price_is_offered_to_anybody(db):
    """Условных цен в v3 нет, значит вся полка предлагается всем."""
    from alma.billing.catalogue import PRODUCTS

    async def work(session):
        user = await accounts.create_guest(session)
        return {
            key: await entitlements.may_be_offered(session, user, key)
            for key in PRODUCTS
        }

    answers = db(work)
    assert len(answers) == 8
    assert all(answers.values()), answers


def test_a_product_we_do_not_sell_is_refused_by_name(db):
    """Чекаут и `/iap/verify` принимают имя товара от клиента, а клиент — не та
    сторона, которой мы верим.

    Тест переписан из проверки условных цен (`archive-upgrade`,
    `archive-bump`), которых больше нет. Проверяемое правило то же и оно
    единственное, что осталось от того механизма: имя, которого нет на полке,
    отвергается по имени, а не тем, что мы его не нарисовали.
    """

    async def work(session):
        user = await accounts.create_guest(session)
        return [
            await entitlements.may_be_offered(session, user, key)
            # Ключи прежней полки, слаг системы вместо ключа каталога и просто
            # выдумка: все три — то, что приходит от пересобранного клиента.
            for key in ("archive", "archive-upgrade", "natal", "door.transits", "")
        ]

    assert db(work) == [False, False, False, False, False]


# ── бандл: пять статичных систем, и ни одной живой ─────────────────────────

def test_the_bundle_opens_the_five_static_systems_and_nothing_else(db):
    """Транзиты и соляр пересчитываются, и продать их «навсегда» за $19.99
    значит отдать подписку одним платежом."""
    living = entitlements.living_systems() & set(SYSTEMS)

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.EVERYTHING,
            kind=EntitlementKind.one_time.value, scope=entitlements.SCOPE_STATIC,
            transaction_id="t1",
        )
        return (
            await entitlements.unlocked_systems(session, user),
            (await entitlements.check(session, user, "natal")).allowed,
            (await entitlements.check(session, user, "transits")).allowed,
        )

    unlocked, natal, transits = db(work)
    assert unlocked == entitlements.STATIC_SYSTEMS
    assert natal is True
    assert transits is False
    assert not (entitlements.STATIC_SYSTEMS & living), (
        "статичная система, которая ещё и живая, — это дверь, продающая подписку"
    )


def test_the_bundle_owner_is_an_owner_and_not_a_subscriber(db):
    """Иначе $19.99 однократно покупают подписочные квоты чата навсегда."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.EVERYTHING,
            kind=EntitlementKind.one_time.value, scope=entitlements.SCOPE_STATIC,
            transaction_id="t1",
        )
        return await entitlements.tier_of(session, user)

    assert db(work) == "owner"


def test_the_static_systems_are_exactly_the_doors_on_the_shelf(db):
    """Бандл обещает «все пять разборов». Пять — это те пять, что продаются
    дверьми, и разойтись эти два списка не могут: бандл, открывающий четыре
    двери из пяти, — это возврат денег и объяснение в поддержке."""
    from alma.billing.catalogue import PRODUCTS

    doors = {
        item.slug
        for item in PRODUCTS.values()
        if item.scope == entitlements.SCOPE_SYSTEM
    }
    assert doors == entitlements.STATIC_SYSTEMS
    assert entitlements.STATIC_SYSTEMS <= set(SYSTEMS)


# ── пара: покупается человек, а не система ─────────────────────────────────

def test_a_pair_grant_opens_that_partner_and_no_other(db):
    """Грант называет один профиль. Открыть им систему значило бы продать все
    пары разом за $4.99."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.pair_system("p1"),
            kind="consumable", transaction_id="t1",
        )
        return (
            (await entitlements.check(
                session, user, "compatibility", partner_id="p1")).allowed,
            (await entitlements.check(
                session, user, "compatibility", partner_id="p2")).allowed,
            (await entitlements.check(session, user, "natal")).allowed,
        )

    assert db(work) == (True, False, False)


def test_a_pair_grant_derives_its_scope_from_the_system_it_names(db):
    """`grant` — единственный писатель `scope`. Строка `pair:{id}`, записанная
    со `scope="system"`, не совпала бы ни с одним запросом: `covers` сравнивает
    пары только внутри своей ветки."""

    async def work(session):
        user = await accounts.create_guest(session)
        row = await entitlements.grant(
            session, user, system=entitlements.pair_system("p1"),
            kind="consumable", transaction_id="t1",
        )
        return row.scope

    assert db(work) == entitlements.SCOPE_PAIR


def test_a_pair_never_appears_in_the_unlocked_systems(db):
    """Хаб и `check()` обязаны сойтись. Одно `compatibility` в общем списке
    означало бы «открыта совместимость», то есть про всех, — и второй партнёр
    упёрся бы в пейволл на системе, нарисованной открытой."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.pair_system("p1"),
            kind="consumable", transaction_id="t1",
        )
        return (
            await entitlements.unlocked_systems(session, user),
            await entitlements.unlocked_pairs(session, user),
        )

    unlocked, pairs = db(work)
    assert unlocked == set()
    assert pairs == ["p1"]


def test_a_revoked_pair_disappears_from_my_pairs(db):
    """Рефанд отчёта закрывает отчёт — А7, случай 6."""

    async def work(session):
        user = await accounts.create_guest(session)
        row = await entitlements.grant(
            session, user, system=entitlements.pair_system("p1"),
            kind="consumable", transaction_id="t1",
        )
        await entitlements.revoke(session, row)
        return await entitlements.unlocked_pairs(session, user)

    assert db(work) == []


def test_compatibility_without_a_partner_is_a_caller_error_not_a_refusal(db):
    """400, а не 402: «нет прав» и «не сказано, про кого» — разные состояния, и
    показать пейволл человеку, который уже купил этот отчёт, хуже, чем упасть."""

    async def work(session):
        user = await accounts.create_guest(session)
        try:
            await entitlements.check(session, user, "compatibility")
        except entitlements.PartnerRequired as exc:
            return str(exc)
        return None

    message = db(work)
    assert message is not None and "partner_id" in message


def test_a_pair_chapter_without_a_partner_is_closed_rather_than_a_call_error(db):
    """У совместимости бесплатных глав больше нет — и порядок веток тот же.

    Тест назывался «бесплатная глава пары не требует партнёра» и держал
    `allowed is True` на главе I: она была бесплатным тизером «Притяжение».
    Владелец снял тизер как отдельную сущность 17.08.2026 («тизер и глава I
    пары — одно и то же»), так что теперь верно обратное: без имени партнёра
    платная глава закрыта.

    Чем это **не** является — ошибкой вызова. `PartnerRequired` (400) значит
    «спросили бессмысленное»; здесь вопрос осмысленный, и ответ на него —
    «закрыто»: гранту `pair:{id}` не к чему привязаться. Разница видна на
    HTTP и стоит она пейволла, показанного тому, кто уже заплатил.
    """

    async def work(session):
        user = await accounts.create_guest(session)
        return await entitlements.check(
            session, user, "compatibility", chapter="attraction", partner_id="nobody"
        )

    assert db(work).allowed is False


def test_a_free_chapter_still_answers_without_a_partner_being_named(db):
    """Порядок веток в `check` — правило, а не сегодняшний состав каталога.

    Бесплатных глав у совместимости сейчас нет, поэтому проверяется сам
    порядок: на главе, помеченной `free`, ответ есть **до** вопроса «про
    кого». Спросив имя первым, мы уронили бы `PartnerRequired` на оглавлении
    у всякого, кто ещё никого не добавил, — то есть у всех, — в тот день,
    когда кампания снова откроет главу I пары на неделю.
    """
    from dataclasses import replace

    from alma.ai import chapters as chapter_defs

    async def work(session, monkeypatched: tuple):
        user = await accounts.create_guest(session)
        return await entitlements.check(
            session, user, "compatibility", chapter="attraction"
        )

    original = chapter_defs.BY_SYSTEM["compatibility"]
    freed = (replace(original[0], free=True), *original[1:])
    chapter_defs.BY_SYSTEM["compatibility"] = freed
    try:
        assert db(lambda session: work(session, freed)).allowed is True
    finally:
        chapter_defs.BY_SYSTEM["compatibility"] = original


def test_a_subscription_opens_every_pair_while_it_lasts(db):
    """`scope="all"` шире пары по построению, и это правильно: подписка в v3
    продаёт всё. Кредит («одна проверка в месяц») — про генерацию нового
    отчёта, а не про чтение уже написанного, и живёт в Ф0.4."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.EVERYTHING,
            kind=EntitlementKind.monthly.value, subscription_id="sub_1",
            duration=timedelta(days=31),
        )
        return (await entitlements.check(
            session, user, "compatibility", partner_id="anyone")).allowed

    assert db(work) is True


def test_a_cancelled_subscription_closes_what_it_opened(db):
    async def work(session):
        user = await accounts.create_guest(session)
        plan = await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE,
            kind=EntitlementKind.monthly.value, subscription_id="sub_1",
            duration=timedelta(days=31),
        )
        await entitlements.revoke(session, plan)
        return await entitlements.unlocked_systems(session, user)

    assert db(work) == set()


# ── renewals ───────────────────────────────────────────────────────────────

def test_a_recurring_grant_without_a_duration_is_refused(db):
    """A subscription with no expiry is one payment for permanent access."""

    async def work(session):
        user = await accounts.create_guest(session)
        try:
            await entitlements.grant(
                session, user, system="*", kind="monthly", subscription_id="sub_1"
            )
        except ValueError as exc:
            return str(exc)
        return None

    message = db(work)
    assert message is not None and "duration" in message

def test_a_renewal_extends_one_row_rather_than_writing_another(db):
    """Every renewal is a new charge, so the charge id cannot be the identity.

    Keying on it wrote a row a month, and cancelling then caught only the row
    belonging to the cancelled charge — the other eleven kept their future
    expiry dates and kept granting access.
    """
    from sqlalchemy import select

    month = timedelta(days=30)

    async def work(session):
        user = await accounts.create_guest(session)
        first = await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE, kind="monthly",
            subscription_id="sub_1", transaction_id="txn_1", duration=month,
        )
        first_expiry = first.expires_at
        second = await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE, kind="monthly",
            subscription_id="sub_1", transaction_id="txn_2", duration=month,
        )
        rows = (
            await session.execute(
                select(Entitlement).where(Entitlement.user_id == user.id)
            )
        ).scalars().all()
        return first.id, second.id, len(rows), first_expiry, second.expires_at

    first_id, second_id, count, before, after = db(work)
    assert first_id == second_id and count == 1
    assert after - before >= month - timedelta(seconds=1)


def test_a_lapsed_subscription_does_not_get_backdated_time(db):
    """Renewing after a gap buys the period from now, not from when it lapsed."""
    month = timedelta(days=30)

    async def work(session):
        user = await accounts.create_guest(session)
        plan = await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE, kind="monthly",
            subscription_id="sub_1", duration=month,
        )
        plan.expires_at = utcnow() - timedelta(days=90)
        await session.flush()
        resumed = await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE, kind="monthly",
            subscription_id="sub_1", duration=month,
        )
        return resumed.expires_at - utcnow()

    assert abs(db(work) - month) < timedelta(minutes=1)


def test_a_plan_change_moves_the_scope_instead_of_keeping_both(db):
    """Upgrading a subscription must not leave the old scope open behind it."""

    async def work(session):
        user = await accounts.create_guest(session)
        await entitlements.grant(
            session, user, system=entitlements.SCOPE_LIVE, kind="monthly",
            subscription_id="sub_1", duration=timedelta(days=30),
        )
        await entitlements.grant(
            session, user, system=entitlements.EVERYTHING, kind="monthly",
            subscription_id="sub_1", duration=timedelta(days=30),
        )
        rows = await entitlements.for_user(session, user)
        return len(rows), await entitlements.unlocked_systems(session, user)

    count, unlocked = db(work)
    assert count == 1
    assert unlocked == set(SYSTEMS)


# ── what is free ───────────────────────────────────────────────────────────

def test_no_system_is_free_and_the_free_layer_is_one_chapter(db):
    """Бесплатный слой — одна глава, а не образец каждой системы.

    Тест держал обратное: у каждой из восьми систем обязана была открываться
    глава-образец. Владелец, 17.08.2026: свободна ровно одна глава во всём
    продукте, натал I «Core». Восемь образцов читались на экране не как
    щедрость, а как случайность — и они же были той причиной, по которой у
    владельца одни главы открывались, а другие показывали чёрную стену.

    Заодно проверяется, что бесплатная глава не открывает свою систему
    целиком: `whole` спрашивается без имени главы, и ответ обязан быть «нет»
    даже у натала.
    """
    from alma.ai.chapters import BY_SYSTEM

    async def work(session):
        user = await accounts.create_guest(session)
        whole = {}
        opened = []
        for system, defined in BY_SYSTEM.items():
            # Совместимости нужен партнёр. Здесь передаётся заведомо
            # несуществующий профиль, чтобы «закрыто» осталось ответом про
            # права, а не про то, назвали ли партнёра.
            partner = "nobody" if system == "compatibility" else None
            whole[system] = (
                await entitlements.check(session, user, system, partner_id=partner)
            ).allowed
            for chapter in defined:
                access = await entitlements.check(
                    session, user, system, chapter=chapter.slug, partner_id=partner
                )
                if access.allowed:
                    opened.append(f"{system}/{chapter.slug}")
        return whole, opened

    whole, opened = db(work)
    for system, allowed in whole.items():
        assert allowed is False, f"{system} is being given away entirely"
    assert opened == ["natal/core"]
