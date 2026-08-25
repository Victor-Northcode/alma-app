"""Час доставки, когда часы под ногами человека двигаются.

`test_notify_rules.py` проверяет правила без базы, `test_notify_daily.py` —
джоб на одном инстанте в Варшаве. Здесь — то, что между ними: **двадцать
четыре часа подряд** для одного человека в поясе, где обещание «утро в его
время» ломается легче всего.

Ломается оно четырьмя способами, и каждый из них здесь свой раздел:

* **Дробное смещение.** Джоб ходит по целым часам UTC, а Индия сдвинута на
  полчаса, Непал — на сорок пять минут, Чатем — на сорок пять минут и почти
  сутки вперёд. Если бы окно `WINDOW_HOURS` было равенством, эти люди не
  получили бы заметку никогда.
* **Перевод стрелок.** В день перехода местное десять утра приходится на
  другой час UTC, чем вчера. Реализация, кэширующая смещение, промахивается
  ровно на час — а окно в три часа этот промах прячет, поэтому здесь
  проверяется не «пришло», а **ровно в какие часы UTC человек становится
  должен**.
* **Переезд.** Часовой пояс приезжает со строкой устройства и меняется на
  первом же запуске приложения в новой стране. Полёт **на запад через линию
  дат** делает местную дату *меньше*, чем вчера, — и это единственный способ
  получить две заметки за два часа.
* **Наивный datetime.** Час без пояса читается как UTC в одном месте и роняет
  вычитание в другом. Самая частая причина «пуш ночью» и единственная, которую
  видно только в тесте, который её специально подставляет.

Плюс то, что рядом и проверяется той же машинерией: две реплики в один час,
телефон, переехавший на другой аккаунт, удалённый аккаунт, и одна плохая
доставка, которая не имеет права уронить остальных.

Вендора нет ни одного: транспорт — четыре строки, ровно как в соседних файлах.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from conftest import database_url, run_async

from alma.db.models import DeviceToken, Entitlement, UsageCounter, User, new_id, utcnow
from alma.notify import daily, rules, tokens
from alma.notify.transport import Push, Receipt, Verdict

# Те же четыре строки стенда, что в `test_notify_daily.py`. Импортом, а не
# копией: расходящиеся заглушки — это два разных представления о контракте
# `alma.daily.candidates`, и второе из них никто не поддерживает.
from test_notify_daily import Piece, Vendor, nothing, one_contact, wrote


@pytest.fixture
def db(tmp_path, monkeypatch):
    from alma import config as config_module
    from alma.db import session as session_module

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "clock.db"))
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()
    run_async(session_module.create_all)
    yield session_module
    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


async def subscriber(
    session,
    *,
    zone: str,
    at: datetime,
    hour: int | None = None,
    locale: str | None = None,
    platform: str = "ios",
    token: str | None = None,
    with_token: bool = True,
) -> User:
    """Подписчик с одним телефоном, живой на момент `at`.

    Свой, а не импортированный из `test_notify_daily`: тот считает всё от
    единственного августовского инстанта, а половина проверок здесь идёт в
    марте и в ноябре. Подписка живёт год от `at`, «видели» — это сам `at`:
    иначе тест про переход на зимнее время падал бы по дормантности, то есть
    по причине, к переходу отношения не имеющей.
    """
    user = User(
        id=new_id(),
        provider="guest",
        locale="en",
        last_seen_at=at,
        daily_hour=hour,
    )
    session.add(user)
    await session.flush()
    session.add(
        Entitlement(
            user_id=user.id,
            system="*",
            kind="monthly",
            scope="live",
            expires_at=at + timedelta(days=365),
        )
    )
    if with_token:
        await tokens.register(
            session,
            user_id=user.id,
            platform=platform,
            token=token or (new_id() * 4)[:96].replace("-", "a"),
            timezone=zone,
            locale=locale,
        )
    await session.flush()
    return user


async def due_hours(session, *, start: datetime, span: int = 30) -> set[int]:
    """В какие часы UTC подряд идущих суток человек считается «в своём утре».

    `candidates=nothing` — намеренно: без кандидата ничего не занимается и не
    отправляется, значит каждый час независим от предыдущего и множество можно
    читать целиком. Это и есть то, что нужно от теста про часовые пояса:
    отправку проверяют другие файлы, здесь проверяется **выбор часа**.
    """
    hit: set[int] = set()
    for step in range(span):
        moment = start + timedelta(hours=step)
        report = await daily.run(
            session,
            now=moment,
            transports={"ios": Vendor()},
            candidates=nothing,
            compose_piece=wrote,
        )
        if report["due"]:
            hit.add(moment.hour)
    return hit


def utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


# ── дробные смещения ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "zone,start,expected",
    [
        # Индия +05:30. Местные 10:00–12:59 — это 04:30–07:29 UTC, а джоб ходит
        # по целым часам: 05:00 (10:30), 06:00 (11:30), 07:00 (12:30).
        ("Asia/Kolkata", utc(2026, 8, 7), {5, 6, 7}),
        # Непал +05:45 — единственный пояс с четвертью часа в живых. 04:15–07:14
        # UTC, целые часы те же три.
        ("Asia/Kathmandu", utc(2026, 8, 7), {5, 6, 7}),
        # Чатем +12:45 зимой южного полушария: местное утро 8 августа — это
        # 21:15–00:14 UTC 7-го, целые часы 22, 23 и 00 (уже 8-го).
        ("Pacific/Chatham", utc(2026, 8, 7), {22, 23, 0}),
        # Лорд-Хау +10:30 вне своего получасового лета: 23:30–02:29 UTC.
        ("Australia/Lord_Howe", utc(2026, 8, 7), {0, 1, 2}),
    ],
)
def test_a_half_hour_zone_still_has_a_morning(db, zone, start, expected):
    """Окно — диапазон, а не равенство, и вот кому это спасает заметку.

    Джоб просыпается в :00 UTC. В поясе, сдвинутом на полчаса, местные ровно
    10:00 не наступают ни в один из этих моментов вовсе — `local_hour == 10`
    было бы вечной тишиной для полутора миллиардов человек.
    """
    async def work():
        async with db.session_scope() as session:
            await subscriber(session, zone=zone, at=start)
            return await due_hours(session, start=start)

    assert run_async(work) == expected


# ── перевод стрелок ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "zone,start,expected,what",
    [
        # Варшава, суббота перед переходом: CET (+1), местные 10–12 = 09–11 UTC.
        ("Europe/Warsaw", utc(2026, 3, 28), {9, 10, 11}, "накануне, зимнее время"),
        # Воскресенье 29 марта 2026, стрелки 02:00 → 03:00. CEST (+2): те же
        # местные часы — это уже 08–10 UTC. Смещение на час — весь смысл теста.
        ("Europe/Warsaw", utc(2026, 3, 29), {8, 9, 10}, "весной, час вперёд"),
        # 25 октября 2026, стрелки назад: сутки длиной 25 часов, возвращаемся
        # к 09–11 UTC.
        ("Europe/Warsaw", utc(2026, 10, 25), {9, 10, 11}, "осенью, час назад"),
        # Нью-Йорк, 8 марта 2026 — сутки длиной 23 часа. EDT (−4): 14–16 UTC.
        ("America/New_York", utc(2026, 3, 8), {14, 15, 16}, "США, весной"),
        # 1 ноября 2026 — сутки длиной 25 часов, EST (−5): 15–17 UTC.
        ("America/New_York", utc(2026, 11, 1), {15, 16, 17}, "США, осенью"),
    ],
)
def test_the_morning_follows_the_clock_change(db, zone, start, expected, what):
    """Проверяется не «пришло», а в какие именно часы UTC человек стал должен.

    Окно шириной в три часа прячет ошибку ровно в час: реализация, взявшая
    смещение вчерашнего дня, всё равно попала бы внутрь окна и тест на «пришло
    один раз» остался бы зелёным. Поэтому здесь сверяется множество часов
    целиком — оно сдвигается вместе со стрелками или не сдвигается вовсе.
    """
    async def work():
        async with db.session_scope() as session:
            await subscriber(session, zone=zone, at=start)
            return await due_hours(session, start=start)

    assert run_async(work) == expected, what


def test_a_day_with_a_clock_change_still_holds_exactly_one_daily(db):
    """Сутки в 25 часов — это не повод для двух заметок.

    Ключ идемпотентности — местная дата, и в день перевода стрелок назад она
    одна и та же на протяжении двадцати пяти часов. Строка `UsageCounter`
    держит это без единого знания о переходе.
    """
    vendor = Vendor()
    start = utc(2026, 11, 1)

    async def work():
        async with db.session_scope() as session:
            await subscriber(session, zone="America/New_York", at=start)
            fired = []
            for step in range(30):
                moment = start + timedelta(hours=step)
                report = await daily.run(
                    session, now=moment, transports={"ios": vendor},
                    candidates=one_contact, compose_piece=wrote,
                )
                if report.get("sent"):
                    fired.append(moment)
            return fired

    fired = run_async(work)
    assert len(fired) == 1, f"одна заметка на местные сутки, а не {len(fired)}"
    local = rules.local_now(ZoneInfo("America/New_York"), fired[0])
    assert local.hour == rules.DEFAULT_HOUR
    assert local.date() == date(2026, 11, 1)
    assert len(vendor.sent) == 1


def test_the_chosen_hour_is_the_delivered_hour_anywhere_in_a_day(db):
    """Час, выбранный человеком, — час доставки, по всем суткам и поясам.

    Прежняя жёсткая гарантия «никогда ночью» отменена владельцем 25.08.2026
    («хочу выбрать любое время»); её место заняла новая, не менее жёсткая:
    23 означает 23 — во всех тридцати часах подряд, в четырёх поясах, включая
    два по разные стороны линии дат. Тихая замена выбранного часа на другой
    и была той жалобой, с которой владелец пришёл.

    Момент снимается с `compose_piece`, потому что это единственная функция,
    которая видит получателя **после** того, как все правила сказали «да», и
    прямо перед тем, как пуш уедет вендору. Всё, что здесь записалось,
    доставлено.
    """
    composed: list[datetime] = []

    async def recording(session, recipient, chosen, day, tier):
        composed.append(recipient.local)
        return Piece()

    async def work():
        async with db.session_scope() as session:
            for zone in (
                "Pacific/Kiritimati", "Pacific/Midway", "Asia/Kathmandu", "Europe/Warsaw"
            ):
                await subscriber(session, zone=zone, at=utc(2026, 8, 7), hour=23)
            for step in range(30):
                await daily.run(
                    session,
                    now=utc(2026, 8, 7) + timedelta(hours=step),
                    transports={"ios": Vendor()},
                    candidates=one_contact,
                    compose_piece=recording,
                )

    run_async(work)
    assert composed, "стенд обязан хоть кому-то что-то отправить, иначе он ничего не проверил"
    off_hour = [moment for moment in composed if moment.hour != 23]
    assert off_hour == [], f"доставлено не в выбранный час: {off_hour}"


# ── переезд ────────────────────────────────────────────────────────────────


def test_flying_west_across_the_date_line_does_not_buy_a_second_daily(db):
    """Окленд → Гонолулу: местная дата уезжает **назад**, ключ счётчика другой.

    Утро 8 августа в Окленде (UTC+12) — это 22:00 UTC 7-го. Тот же инстант в
    Гонолулу (UTC−10) — 12:00 **7-го**, то есть человек всё ещё внутри своего
    окна, а `counter_key` смотрит на другую дату и ничего не помнит. Приложение
    перерегистрирует устройство на первом запуске после посадки, так что новый
    пояс появляется в строке в тот же час.

    Час посещается больше одного раза by design — две реплики, перезапуск
    супервизора, задокументированный повтор `--at`, — и раньше второй визит
    внутри этого часа отправлял вторую заметку через два часа после первой.
    Ровно тот отказ, ради которого написана вся схема «занять день до
    отправки», пришедший со стороны календаря, а не со стороны джоба.
    """
    vendor = Vendor()
    landed = utc(2026, 8, 7, 22)

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session, zone="Pacific/Auckland", at=landed)
            first = await daily.run(
                session, now=landed, transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )
            # Самолёт сел, приложение поздоровалось — строка устройства теперь
            # говорит другой пояс.
            for row in await tokens.for_user(session, user.id):
                row.timezone = "Pacific/Honolulu"
            await session.commit()
            second = await daily.run(
                session, now=landed + timedelta(minutes=30), transports={"ios": vendor},
                candidates=one_contact, compose_piece=wrote,
            )
            return first, second

    first, second = run_async(work)
    assert first["sent"] == 1
    assert second.get("sent", 0) == 0, "вторая заметка через полчаса после первой"
    assert second["refused:a daily went out inside the last 3 days"] == 1
    assert len(vendor.sent) == 1


def test_a_send_day_in_the_future_still_closes_the_gap():
    """Тот же закон, сказанный без базы: расстояние абсолютное.

    `too_soon` фильтровал историю по `day <= today` — что читается очевидно
    верным и неверно ровно для тех, кто пересёк линию дат на запад.
    """
    today = date(2026, 8, 7)
    assert rules.too_soon(today, [today + timedelta(days=1)])
    assert rules.too_soon(today, [today + timedelta(days=3)])
    assert not rules.too_soon(today, [today + timedelta(days=4)])


def test_moving_east_moves_the_morning_with_the_person(db):
    """Варшава → Токио: следующее утро считается по новому поясу, а не по старому.

    Проверяется через `due`, а не через отправку: пояс решает, в какой час UTC
    человек попадает в отбор, и это единственное, что переезд меняет.
    """
    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session, zone="Europe/Warsaw", at=utc(2026, 8, 7))
            before = await due_hours(session, start=utc(2026, 8, 7))
            for row in await tokens.for_user(session, user.id):
                row.timezone = "Asia/Tokyo"
            await session.commit()
            after = await due_hours(session, start=utc(2026, 8, 7))
            return before, after

    before, after = run_async(work)
    # Варшава летом +2: местные 10–12 = 08–10 UTC. Токио +9 круглый год: 01–03.
    assert before == {8, 9, 10}
    assert after == {1, 2, 3}


def test_the_phone_in_the_pocket_outranks_the_tablet_in_the_drawer(db):
    """Пояс берёт последнее живое устройство, а не первое попавшееся.

    Планшет, оставшийся в стране, из которой человек уехал, не имеет права
    решать, когда зазвонит телефон у него в кармане.
    """
    async def work():
        async with db.session_scope() as session:
            user = await subscriber(
                session, zone="America/Toronto", at=utc(2026, 8, 7), token="t" * 64
            )
            old = (await tokens.for_user(session, user.id))[0]
            old.last_seen_at = utc(2026, 7, 1)
            await tokens.register(
                session, user_id=user.id, platform="ios", token="p" * 64,
                timezone="Asia/Tokyo", locale="it",
            )
            await session.commit()
            selected = await daily.due(session, now=utc(2026, 8, 7, 1))
            return [(r.zone.key, r.locale) for r in selected]

    assert run_async(work) == [("Asia/Tokyo", "it")]


# ── наивный datetime ───────────────────────────────────────────────────────


def test_a_naive_instant_is_read_as_utc_rather_than_as_local_or_a_crash(db):
    """Час без пояса — самая частая причина заметки посреди ночи.

    Он читается как UTC в `local_now` и роняет вычитание в `is_dormant`: одно
    и то же отсутствие `tzinfo` даёт тихий неверный ответ на одной строке и
    `TypeError` тремя строками ниже. `daily.moment_of` — то место, где это
    решается один раз.
    """
    aware = utc(2026, 8, 7, rules.DEFAULT_HOUR - 2)
    naive = aware.replace(tzinfo=None)

    async def work():
        async with db.session_scope() as session:
            await subscriber(session, zone="Europe/Warsaw", at=aware)
            return await daily.run(
                session, now=naive, transports={"ios": Vendor()},
                candidates=one_contact, compose_piece=wrote,
            )

    report = run_async(work)
    assert report["due"] == 1
    assert report["sent"] == 1
    assert "errored" not in report, "наивный час не должен ронять получателя"


def test_a_naive_last_seen_from_sqlite_does_not_look_like_a_dormant_person():
    """SQLite отдаёт наивное время из колонки, объявленной с поясом.

    Наивное «вчера» рядом с aware «сейчас» — это `TypeError`, а не «дормант»,
    и в джобе он выглядит как один получатель в `errored` со стектрейсом, в
    котором про часовые пояса нет ни слова.
    """
    now = utc(2026, 8, 7)
    assert not rules.is_dormant(now.replace(tzinfo=None) - timedelta(days=1), now)
    assert rules.is_dormant(now.replace(tzinfo=None) - timedelta(days=61), now)
    # И симметрично: наивным может приехать `now`, а не только `last_seen`.
    assert rules.is_dormant(now - timedelta(days=61), now.replace(tzinfo=None))


# ── две реплики ────────────────────────────────────────────────────────────


def test_two_connections_cannot_claim_the_same_morning(db):
    """Первичный ключ решает, а не порядок, в котором повезло.

    Две реплики читают одну и ту же пустую историю и обе решают отправлять —
    это нормальный, ожидаемый исход, и единственное, что стоит между ним и
    двумя уведомлениями, — строка, которую база разрешит вставить один раз.
    Две **разные сессии**, потому что внутри одной это проверяет карту
    объектов SQLAlchemy, а не базу.

    Проигравшая реплика слышит `orphaned`, пока победившая держит вендора, и
    `already` после того, как та подтвердила. Это задокументированная
    неразличимость — «занято и ещё не отправлено» выглядит одинаково у живой
    заявки на другом хосте и у процесса, убитого посреди прохода, — и в обоих
    случаях ответ один: не отбирать. Дороже неё была бы обратная ошибка.
    """
    day = date(2026, 8, 7)

    async def work():
        async with db.session_scope() as setup:
            user = await subscriber(session=setup, zone="Europe/Warsaw", at=utc(2026, 8, 7))
            user_id = user.id
        factory = db.session_factory()
        async with factory() as one:
            row, first = await daily.claim(one, user_id=user_id, day=day)
            async with factory() as two:
                _, in_flight = await daily.claim(two, user_id=user_id, day=day)
                # Проигравшая реплика обязана отпустить соединение: её
                # неудавшаяся вставка оставила открытую транзакцию, а на SQLite
                # читатель блокирует писателя — то есть подтверждение
                # победившей встало бы в «database is locked». В джобе это
                # делает `run`, здесь приходится руками.
                await two.rollback()
            await daily.confirm(one, row)
        async with factory() as three:
            _, after = await daily.claim(three, user_id=user_id, day=day)
            return first, in_flight, after

    assert run_async(work) == ("claimed", "orphaned", "already")


def test_two_replicas_in_the_same_hour_send_once(db):
    """Обе реплики идут целиком, вторая — пока первая держит вендора.

    Гейт устроен так, что вторая реплика проходит весь свой проход в тот
    момент, когда первая уже заняла день и ещё не получила ответа вендора: это
    и есть та щель, в которую попадает второе уведомление, если строка
    занимается после отправки, а не до.
    """
    reached = asyncio.Event()
    released = asyncio.Event()

    class Held:
        platform = "ios"

        def __init__(self) -> None:
            self.sent: list[Push] = []

        async def send(self, token, push: Push) -> Receipt:
            self.sent.append(push)
            reached.set()
            await asyncio.wait_for(released.wait(), 10)
            return Receipt(Verdict.sent)

    first, second = Held(), Vendor()

    async def work():
        async with db.session_scope() as setup:
            await subscriber(setup, zone="Europe/Warsaw", at=utc(2026, 8, 7))
        moment = utc(2026, 8, 7, rules.DEFAULT_HOUR - 2)
        factory = db.session_factory()

        async def replica(transport, wait: bool):
            if wait:
                await asyncio.wait_for(reached.wait(), 10)
            async with factory() as session:
                report = await daily.run(
                    session, now=moment, transports={"ios": transport},
                    candidates=one_contact, compose_piece=wrote,
                )
            if wait:
                released.set()
            return report

        return await asyncio.gather(replica(first, False), replica(second, True))

    one, two = run_async(work)
    assert one["sent"] == 1
    assert two.get("sent", 0) == 0
    # `orphaned`, а не `already`: первая реплика ещё висит в вендоре и строку не
    # подтвердила. Отчёт при этом честен — «день занят и не отправлен» правда, —
    # а второго уведомления не случилось, что и есть проверяемое свойство.
    assert two["orphaned"] == 1
    assert len(first.sent) == 1 and second.sent == []


# ── чужой аккаунт ──────────────────────────────────────────────────────────


def test_a_phone_that_changed_hands_hears_only_its_new_owner(db):
    """Переустановка и вход другим человеком: строка переезжает, а не двоится.

    Пара `(platform, token)` уникальна намеренно — иначе телефон получил бы две
    заметки о двух разных картах, и вторая была бы про чужую жизнь.
    """
    vendor = Vendor()
    same = "d" * 64

    async def work():
        async with db.session_scope() as session:
            first = await subscriber(
                session, zone="Europe/Warsaw", at=utc(2026, 8, 7), token=same
            )
            # Второй аккаунт своего телефона не имеет: он появится ровно тогда,
            # когда на этот же телефон войдут им.
            second = await subscriber(
                session, zone="Europe/Warsaw", at=utc(2026, 8, 7), with_token=False
            )
            # Тот же телефон, другой аккаунт: приложение переустановили и вошли
            # другим человеком, токен APNs при этом остался прежним.
            await tokens.register(
                session, user_id=second.id, platform="ios", token=same,
                timezone="Europe/Warsaw",
            )
            await session.commit()
            report = await daily.run(
                session, now=utc(2026, 8, 7, rules.DEFAULT_HOUR - 2),
                transports={"ios": vendor}, candidates=one_contact, compose_piece=wrote,
            )
            return report, len(await tokens.for_user(session, first.id))

    report, orphaned = run_async(work)
    assert orphaned == 0, "прежний владелец больше не указывает на этот телефон"
    assert report["due"] == 1
    assert len(vendor.sent) == 1


def test_an_erased_account_is_not_reachable_at_all(db):
    """Удаление стирает токены; `is_active` — второй замок на той же двери.

    Оба нужны: `erase` удаляет строки, а `due` отбрасывает нежившие аккаунты,
    у которых токен пережил удаление по любой причине — слитый аккаунт,
    незавершённая эрайза, строка, восстановленная из бэкапа.
    """
    async def work():
        async with db.session_scope() as session:
            from alma.auth.accounts import erase

            erased = await subscriber(session, zone="Europe/Warsaw", at=utc(2026, 8, 7))
            survivor = await subscriber(session, zone="Europe/Warsaw", at=utc(2026, 8, 7))
            await erase(session, erased)
            await session.commit()
            gone = len(await tokens.for_user(session, erased.id))

            # И отдельно — токен, переживший удаление: строка есть, аккаунта нет.
            zombie = await subscriber(session, zone="Europe/Warsaw", at=utc(2026, 8, 7))
            zombie.deleted_at = utcnow()
            await session.commit()
            selected = await daily.due(
                session, now=utc(2026, 8, 7, rules.DEFAULT_HOUR - 2)
            )
            return gone, [r.user.id for r in selected], survivor.id

    gone, selected, survivor = run_async(work)
    assert gone == 0, "erase обязан снимать устройства вместе с аккаунтом"
    assert selected == [survivor]


def test_turning_notifications_off_leaves_nothing_to_send_to(db):
    """«Выключено» в этом продукте — удаление строк, а не флаг.

    Проверяется с той стороны, с которой это важно: после отказа джоб не
    отбирает человека вовсе, а не отбирает и вежливо молчит.
    """
    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session, zone="Europe/Warsaw", at=utc(2026, 8, 7))
            await tokens.forget(session, user.id)
            await session.commit()
            return await daily.due(session, now=utc(2026, 8, 7, rules.DEFAULT_HOUR - 2))

    assert run_async(work) == []


# ── одна плохая доставка ───────────────────────────────────────────────────


def test_one_unreachable_device_costs_neither_the_person_nor_the_run(db):
    """Оборванный сокет — ответ про устройство, а не про человека.

    Раньше исключение из `transport.send` вылетало из цикла по устройствам:
    второй телефон того же человека не опрашивался, день оставался занятым, и
    следующий прогон рапортовал `orphaned` — строку, которая значит «процесс
    убили посреди прохода», — про обычную сетевую икоту. И это при живом
    втором вендоре.
    """
    class Broken:
        platform = "ios"

        async def send(self, token, push):
            raise ConnectionResetError("TLS reset by peer")

    android = Vendor(platform="android")

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session, zone="Europe/Warsaw", at=utc(2026, 8, 7))
            await tokens.register(
                session, user_id=user.id, platform="android", token="g" * 140,
                timezone="Europe/Warsaw",
            )
            await session.commit()
            report = await daily.run(
                session, now=utc(2026, 8, 7, rules.DEFAULT_HOUR - 2),
                transports={"ios": Broken(), "android": android},
                candidates=one_contact, compose_piece=wrote,
            )
            live = await tokens.for_user(session, user.id)
            return report, len(live)

    report, live = run_async(work)
    assert report["sent"] == 1, "второй телефон обязан быть опрошен"
    assert "errored" not in report
    assert len(android.sent) == 1
    assert live == 2, "про токен ничего не узнали — строку не трогаем"


def test_a_dead_device_does_not_take_the_rest_of_the_run_with_it(db):
    """Один 410 в середине списка — это одна удалённая строка, а не тишина.

    Порядок `due` устойчив, поэтому «упало на втором» без защиты означало бы
    «третий и четвёртый не получают никогда».
    """
    class Mixed:
        """Мёртвый токен второму по счёту, всем остальным — принято."""

        platform = "ios"

        def __init__(self) -> None:
            self.sent: list[Push] = []

        async def send(self, token, push):
            self.sent.append(push)
            if len(self.sent) == 2:
                # Момент смерти — **после** регистрации, иначе правило про
                # переустановку правильно оставит строку, и тест будет про
                # другое (см. `test_a_reinstall_survives_a_stale_410`).
                return Receipt(
                    Verdict.dead, "Unregistered", dead_since=utcnow() + timedelta(seconds=1)
                )
            return Receipt(Verdict.sent)

    vendor = Mixed()

    async def work():
        async with db.session_scope() as session:
            for _ in range(4):
                await subscriber(session, zone="Europe/Warsaw", at=utc(2026, 8, 7))
            await session.commit()
            report = await daily.run(
                session, now=utc(2026, 8, 7, rules.DEFAULT_HOUR - 2),
                transports={"ios": vendor}, candidates=one_contact, compose_piece=wrote,
            )
            left = (await session.execute(__import__("sqlalchemy").select(DeviceToken))).scalars().all()
            return report, len(left)

    report, left = run_async(work)
    assert report["due"] == 4
    assert report["sent"] == 3
    assert report["failed"] == 1, "мёртвому токену слать было некуда — день возвращён"
    assert left == 3, "мёртвая строка удалена, живые целы"
    assert len(vendor.sent) == 4


def test_a_day_lost_to_a_dead_token_is_not_a_day_claimed(db):
    """Никто не принял — день обязан вернуться, иначе завтра он «уже был»."""
    gone = Vendor(receipt=Receipt(Verdict.dead, "UNREGISTERED"))

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(session, zone="Europe/Warsaw", at=utc(2026, 8, 7))
            await daily.run(
                session, now=utc(2026, 8, 7, rules.DEFAULT_HOUR - 2),
                transports={"ios": gone}, candidates=one_contact, compose_piece=wrote,
            )
            return await session.get(
                UsageCounter, daily.counter_key(user.id, date(2026, 8, 7))
            )

    assert run_async(work) is None


# ── локаль ─────────────────────────────────────────────────────────────────


def test_the_account_language_answers_when_the_phone_did_not(db):
    """Лестница из двух ступеней, и вторая существует не для красоты.

    Клиент отправляет локаль устройства при регистрации, но поле необязательно
    (`DeviceIn.locale: str | None`), а `tokens.register` не перетирает известное
    пустым. Аккаунт — то, что остаётся.
    """
    vendor = Vendor()

    async def work():
        async with db.session_scope() as session:
            user = await subscriber(
                session, zone="Europe/Rome", at=utc(2026, 8, 7), locale=None
            )
            user.locale = "fr"
            await session.commit()
            await daily.run(
                session, now=utc(2026, 8, 7, rules.DEFAULT_HOUR - 2),
                transports={"ios": vendor}, candidates=one_contact, compose_piece=wrote,
            )
            return vendor.sent[0]

    push = run_async(work)
    assert push.args[:2] == ("Saturne", "Soleil")
    assert push.args[2] == "16:20", "французский пишет время в двадцати четырёх часах"
