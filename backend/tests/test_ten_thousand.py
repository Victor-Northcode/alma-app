"""Шесть мест, где сервис работал ровно до второго рабочего процесса.

Общее у них — арифметика деплоя, а не тема. `gunicorn.conf.py` поднимает
воркеров по числу ядер: на четырёх ядрах это восемь процессов, и каждый из них
до этой волны держал в своей памяти то, что обязано было быть одно на сервис.
Каждый тест здесь падает на коде, который был до правки, и в комментарии
сказано — как именно.

1. **Потолки на входе** (гости, письма входа, события анонима) считались в
   памяти процесса: восемь процессов — восьмикратный потолок, а выкладка
   обнуляла счёт целиком.
2. **Квоты и деньги** читались, сравнивались и записывались тремя разными
   обращениями к базе, между которыми лежала генерация.
3. **HTTP-клиент** создавался на каждый вызов — то есть TLS-рукопожатие на
   каждую проверку покупки и на каждую главу.
4. **Схему** создавал каждый воркер на старте: восемь одновременных
   `CREATE INDEX` в секунду выкладки.
5. **Фоновые ходы беседы** никто не ждал при остановке: оплаченный ответ
   уходил вместе с процессом.
6. **Растущие таблицы** никто не уменьшал.
"""

from __future__ import annotations

import asyncio
import logging
from importlib import import_module
from datetime import date, datetime, timedelta, timezone

import pytest
from conftest import database_url, run_async

from alma.api import deps
from alma.db import counters
from alma.db import session as session_module


def _new_user(session, user_id: str = "u-limits-1"):
    from alma.db.models import User

    session.add(User(id=user_id, provider="guest"))
    return user_id


def _user_model():
    """Модель пользователя — импортом внутри, как и всё в этом файле.

    Счётчикам `readings.py` нужен объект, привязанный к **той самой** сессии, в
    которой он их зовёт: два воркера в тестах ниже — это две сессии, и общий
    объект между ними стёр бы ровно ту границу, которую они проверяют.
    """
    from alma.db.models import User

    return User


# ── 1. потолки на входе общие для всех воркеров ────────────────────────────


def test_two_workers_do_not_get_two_ceilings(schema):
    """**Главное свойство волны, и до неё его не было.**

    Два `SharedWindow` — это два рабочих процесса: у каждого своя память,
    общего у них только база. На старом коде (`FixedWindow`, словарь в памяти)
    второй объект начинал считать с нуля и пропускал ещё столько же, сколько
    первый, — то есть «тридцать гостей в час с адреса» на восьмиядерной машине
    означало двести сорок.
    """
    async def go():
        first = deps.SharedWindow(name="probe_two", limit=2, seconds=3600)
        second = deps.SharedWindow(name="probe_two", limit=2, seconds=3600)

        async with session_module.session_scope() as session:
            assert await first.hit(session, "203.0.113.7") is True
            assert await second.hit(session, "203.0.113.7") is True
            # Третье обращение — уже сверх потолка, каким бы из процессов оно
            # ни пришло.
            assert await first.hit(session, "203.0.113.7") is False
            assert await second.hit(session, "203.0.113.7") is False

    run_async(go)


def test_a_restart_does_not_hand_the_ceiling_back(schema):
    """Выкладка — это новый процесс с пустой памятью, а не новое окно.

    До правки `docker compose up -d --build` возвращал каждому источнику
    полный потолок: счётчики жили в процессе, процесс уходил. То есть потолок
    снимался ровно тогда, когда мы сами этого хотели меньше всего.
    """
    async def go():
        before = deps.SharedWindow(name="probe_restart", limit=1, seconds=3600)
        async with session_module.session_scope() as session:
            assert await before.hit(session, "198.51.100.4") is True

        # Процесс ушёл: объект новый, память пустая, база та же.
        after = deps.SharedWindow(name="probe_restart", limit=1, seconds=3600)
        async with session_module.session_scope() as session:
            assert await after.hit(session, "198.51.100.4") is False

    run_async(go)


def test_a_spent_ceiling_stops_costing_us_a_query(schema):
    """Дешёвая половина схемы: отказ выдаётся из памяти, без обращения к базе.

    Ради этого свойства всё и затевалось так, а не «строка в базу на каждый
    запрос»: по этому пути ходит скрипт, который крутит тысячи запросов, и он
    обязан быть для нас бесплатным. Память при этом умеет только отказывать —
    пропустить может лишь база, иначе мы вернули бы попроцессные потолки.
    """
    async def go():
        window = deps.SharedWindow(name="probe_cheap", limit=1, seconds=3600)
        async with session_module.session_scope() as session:
            assert await window.hit(session, "203.0.113.8") is True
            assert await window.hit(session, "203.0.113.8") is False

        # Сессии нет вовсе: если объект пойдёт в базу, он упадёт на `None`, и
        # это единственный способ проверить «не ходил», который нельзя пройти
        # случайно.
        for _ in range(50):
            assert await window.hit(None, "203.0.113.8") is False

    run_async(go)


def test_different_limiters_do_not_share_one_source(schema):
    """Один адрес в `guest_mint` и в `anon_events` — два разных счёта."""
    async def go():
        mints = deps.SharedWindow(name="guest_mint", limit=1, seconds=3600)
        events = deps.SharedWindow(name="anon_events", limit=1, seconds=3600)
        async with session_module.session_scope() as session:
            assert await mints.hit(session, "203.0.113.9") is True
            assert await events.hit(session, "203.0.113.9") is True
            assert await mints.hit(session, "203.0.113.9") is False

    run_async(go)


def test_the_source_is_never_stored_in_the_clear(schema):
    """Таблица потолков не должна становиться журналом IP-адресов и почты.

    Privacy-страница обещает, что аналитика не хранит адресов; таблица,
    набитая ими через заднюю дверь, сделала бы это обещание неправдой. В
    строку идёт отпечаток.
    """
    from sqlalchemy import select

    from alma.db.models import RateWindow

    async def go():
        window = deps.SharedWindow(name="probe_privacy", limit=5, seconds=3600)
        async with session_module.session_scope() as session:
            await window.hit(session, "203.0.113.77")
            await window.hit(session, "sofia@example.com")

        async with session_module.session_scope() as session:
            ids = (await session.execute(select(RateWindow.id))).scalars().all()

        joined = " ".join(ids)
        assert "203.0.113.77" not in joined
        assert "sofia@example.com" not in joined
        assert "example.com" not in joined
        assert len(ids) == 2, "два разных источника — две строки"

    run_async(go)


def test_the_guest_ceiling_holds_across_a_restart_of_the_app(api, monkeypatch, tmp_path):
    """То же самое, но целиком через HTTP и через второе приложение.

    Второй `create_app()` на той же базе — это второй воркер: у него свои
    `app.state.rate_windows` и общая с первым база. До правки он выдал бы
    гостю полный потолок заново.
    """
    from fastapi.testclient import TestClient

    from alma.api.app import create_app

    monkeypatch.setattr(deps, "GUEST_MINTS_PER_HOUR", 1)
    assert api.get("/v1/auth/session").status_code == 200
    assert api.get("/v1/auth/session").status_code == 429

    with TestClient(create_app()) as second_worker:
        refused = second_worker.get("/v1/auth/session")
    assert refused.status_code == 429, (
        "второй воркер выдал ещё один гостевой аккаунт — потолок снова "
        "умножается на число процессов"
    )


# ── 2. квоты и деньги: увеличить и проверить одним запросом ────────────────


def test_a_quota_is_spent_and_checked_without_a_gap(schema):
    """Примитив, ради которого написан `db/counters.py`.

    Порядок «прибавить → посмотреть» вместо «прочитать → сравнить → позже
    записать»: второй вызов видит своё же увеличение и упирается, тогда как
    старая пара `get`/`+=`/`flush` давала обоим один и тот же ноль.
    """
    async def go():
        async with session_module.session_scope() as session:
            user_id = _new_user(session, "u-quota-1")
            await session.flush()
            today = date.today()

            assert await counters.spend_and_check(
                session, user_id=user_id, day=today, metric="q", limit=2
            ) == 1
            assert await counters.spend_and_check(
                session, user_id=user_id, day=today, metric="q", limit=2
            ) == 2
            with pytest.raises(counters.QuotaExceeded) as refused:
                await counters.spend_and_check(
                    session, user_id=user_id, day=today, metric="q", limit=2
                )
            assert refused.value.spent == 3
            assert refused.value.limit == 2

    run_async(go)


def _statements_while(work) -> list[str]:
    """SQL, который база увидела за время этой корутины.

    Нужен, потому что проверяемое свойство — не «сколько получилось», а
    **сколько запросов на это ушло**. Прежний приём (`session.get` → `+= 1` →
    `flush`) даёт тот же ответ на одном воркере и разъезжается только под
    настоящей одновременностью, которую на SQLite не поставишь: два пишущих
    соединения он сериализует. Считать запросы — прямая проверка того самого
    условия, «увеличить и проверить одним запросом».
    """
    from sqlalchemy import event

    seen: list[str] = []
    engine = session_module.engine().sync_engine

    def record(_conn, _cursor, statement, *_rest):
        seen.append(" ".join(statement.split()))

    event.listen(engine, "before_cursor_execute", record)
    try:
        run_async(work)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    return seen


def test_spending_a_quota_is_one_statement_with_no_read_before_it(schema):
    """«Увеличить и проверить одним запросом» — проверяется буквально.

    Прежний приём читал строку (`SELECT`), прибавлял в питоне и записывал
    (`INSERT`/`UPDATE`) — между чтением и записью у `readings.py` лежит целая
    генерация, и два хода проходили обе стены с одним и тем же нулём.
    Атомарный вариант не читает вовсе: он прибавляет и получает результат тем
    же запросом, поэтому «прочитанное» и «записанное» не могут разойтись по
    определению.
    """
    async def prepare():
        async with session_module.session_scope() as session:
            _new_user(session, "u-quota-2")

    run_async(prepare)

    async def spend():
        async with session_module.session_scope() as session:
            await counters.spend_and_check(
                session, user_id="u-quota-2", day=date.today(), metric="q", limit=3
            )

    statements = [
        line for line in _statements_while(spend)
        if "usage_counter" in line.lower()
    ]
    assert len(statements) == 1, (
        "списание квоты стоило больше одного запроса — значит, между чтением и "
        "записью снова есть щель: " + " | ".join(statements)
    )
    lowered = statements[0].lower()
    assert "on conflict" in lowered and "returning" in lowered
    assert not lowered.startswith("select"), "счётчик снова читается перед записью"


def test_charging_the_month_writes_before_it_sums(schema):
    """Порядок, который и закрывает гонку на деньгах.

    Расход записан **до** того, как месячная сумма прочитана, поэтому два
    одновременных вызова видят сумму, включающую их обоих. Прежний порядок —
    прочитать сумму, сравнить, записать много позже — давал обоим один и тот
    же ноль, и на двух воркерах это две генерации по цене одной.
    """
    async def prepare():
        async with session_module.session_scope() as session:
            _new_user(session, "u-money-3")

    run_async(prepare)

    async def charge():
        async with session_module.session_scope() as session:
            await counters.charge_and_check_month(
                session, user_id="u-money-3", cents=5.0, ceiling_dollars=10.0
            )

    statements = [
        line.lower() for line in _statements_while(charge)
        if "usage_counter" in line.lower()
    ]
    assert len(statements) == 2, " | ".join(statements)
    assert "on conflict" in statements[0], "сумма прочитана раньше, чем расход записан"
    assert statements[1].startswith("select sum")


def test_a_refund_puts_the_question_back(schema):
    """Ход, отменённый после списания, не должен стоить человеку вопроса."""
    async def go():
        async with session_module.session_scope() as session:
            user_id = _new_user(session, "u-quota-3")
            await session.flush()
            today = date.today()
            await counters.spend_and_check(
                session, user_id=user_id, day=today, metric="q", limit=1
            )
            await counters.refund(session, user_id=user_id, day=today, metric="q", count=1)
            assert await counters.spend_and_check(
                session, user_id=user_id, day=today, metric="q", limit=1
            ) == 1

    run_async(go)


def test_the_month_is_charged_before_it_is_read(schema):
    """Месячный потолок: расход записан до того, как сумма прочитана.

    Ровно этот порядок закрывает гонку, которую не закрывает число запросов:
    два одновременных вызова видят сумму, включающую их обоих. Проверяется и
    пересчёт центов в доллары — ошибка в сто раз здесь стоила бы денег.
    """
    async def go():
        async with session_module.session_scope() as session:
            user_id = _new_user(session, "u-money-1")
            await session.flush()

            # 40 центов при потолке в один доллар — проходит.
            assert await counters.charge_and_check_month(
                session, user_id=user_id, cents=40.0, ceiling_dollars=1.0
            ) == pytest.approx(0.4)

            with pytest.raises(counters.QuotaExceeded) as refused:
                await counters.charge_and_check_month(
                    session, user_id=user_id, cents=80.0, ceiling_dollars=1.0
                )
            assert refused.value.spent == pytest.approx(1.2)

    run_async(go)


def test_the_month_total_agrees_with_the_ledger_that_already_existed(schema):
    """Второго счётчика денег быть не должно — читается один и тот же.

    `ai/cost.month_spend` суммирует те же строки. Разойдись они, потолок,
    который отказывает, и цифра, которую видит поддержка, стали бы двумя
    разными числами.
    """
    from alma.ai import cost
    from alma.db.models import User

    async def go():
        async with session_module.session_scope() as session:
            user_id = _new_user(session, "u-money-2")
            await session.flush()
            await counters.charge_and_check_month(
                session, user_id=user_id, cents=17.5, ceiling_dollars=100.0
            )

        async with session_module.session_scope() as session:
            user = await session.get(User, "u-money-2")
            assert await cost.month_spend(session, user) == pytest.approx(0.175)

    run_async(go)


# ── 3. один HTTP-клиент на процесс ─────────────────────────────────────────


def test_the_billing_client_is_one_per_process():
    """Клиент на вызов — это TLS-рукопожатие на вызов.

    До правки каждый адаптер кассы открывал свой `httpx.AsyncClient` через
    `async with` и закрывал на выходе, поэтому keep-alive не срабатывал ни
    разу: соединение выбрасывалось вместе с клиентом.
    """
    from alma.billing import http as billing_http

    async def go():
        first = billing_http.client()
        second = billing_http.client()
        assert first is second, "второй вызов открыл второй пул соединений"
        assert first.timeout.connect == billing_http.CONNECT_TIMEOUT
        assert first.timeout.read == billing_http.READ_TIMEOUT
        await billing_http.aclose()
        assert first.is_closed
        # После закрытия следующий вызов честно строит новый.
        assert billing_http.client() is not first
        await billing_http.aclose()

    asyncio.run(go())


def test_the_adapters_no_longer_open_a_client_of_their_own():
    """Строку `async with httpx.AsyncClient(` легко вернуть, не заметив.

    Поэтому она стережётся текстом: пул, созданный на один вызов, к моменту
    второго уже собран сборщиком мусора, и никакой замер этого не покажет —
    покажет только счёт за задержку.
    """
    import pathlib

    billing = pathlib.Path(__file__).resolve().parents[1] / "alma" / "billing"
    offenders = [
        f"{path.name}:{number}"
        for path in sorted(billing.glob("*.py"))
        if path.name != "http.py"
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if "httpx.AsyncClient(" in line
    ]
    assert offenders == [], (
        "адаптер снова создаёт свой HTTP-клиент: " + ", ".join(offenders)
    )


def test_the_model_provider_is_built_once(monkeypatch):
    """`default_provider()` звался зависимостью на каждом запросе.

    То есть на каждую главу поднимался новый `AsyncAnthropic` со своим пулом —
    и каждая глава начинала с рукопожатия до `api.anthropic.com`.
    """
    from alma.ai import provider as provider_module

    built = []

    class _Fake:
        def __init__(self) -> None:
            built.append(self)

        async def aclose(self) -> None:
            built.remove(self)

    provider_module.reset_provider()
    monkeypatch.setattr(provider_module, "AnthropicProvider", _Fake)

    first = provider_module.default_provider()
    second = provider_module.default_provider()
    assert first is second
    assert len(built) == 1, "провайдер строится на каждом вызове"

    asyncio.run(provider_module.close_provider())
    assert built == [], "lifespan не отпустил соединения провайдера"


# ── 4. схему создаёт выкладка, а не восемь воркеров ────────────────────────


def test_a_worker_refuses_to_start_on_a_database_with_no_schema(tmp_path, monkeypatch):
    """Тихий старт на пустой базе — это 500 на первом же платном запросе.

    До правки каждый воркер создавал схему сам, и на восьми процессах это
    восемь одновременных `CREATE INDEX` в ту же секунду. Теперь её приводит
    один шаг выкладки, а воркер обязан **не подняться**, если шага не было.
    """
    from fastapi.testclient import TestClient

    from alma import config as config_module
    from alma.api.app import create_app

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "bare.db"))
    monkeypatch.setenv("ALMA_ENV", "test")
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()

    with pytest.raises(session_module.SchemaNotReady) as refused:
        with TestClient(create_app()):
            pass

    # Отказ обязан называть команду: тот, кто это увидит, будет чинить прод.
    assert session_module.MIGRATE_COMMAND in str(refused.value)

    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


def test_the_deploy_command_builds_the_schema_the_workers_check(tmp_path, monkeypatch):
    """`tools/migrate.py` и `verify_schema` обязаны сходиться.

    Иначе «миграция прошла» и «воркер поднимется» — два разных утверждения, и
    расходятся они на выкладке.
    """
    from alma import config as config_module

    import tools.migrate as migrate_tool

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "migrated.db"))
    monkeypatch.setenv("ALMA_ENV", "test")
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()

    assert migrate_tool.main(["--check"]) == 1, "на пустой базе проверка обязана отказать"
    assert migrate_tool.main([]) == 0
    assert migrate_tool.main(["--check"]) == 0

    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


def test_the_missing_column_is_named_rather_than_merely_refused(tmp_path, monkeypatch):
    """Отказ, не называющий, чего не хватает, чинят вслепую."""
    from alma import config as config_module

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "column.db"))
    monkeypatch.setenv("ALMA_ENV", "test")
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()
    run_async(session_module.create_all)

    async def drop_a_column():
        from sqlalchemy import text

        async with session_module.engine().begin() as connection:
            await connection.execute(text("ALTER TABLE rate_window DROP COLUMN count"))

    run_async(drop_a_column)

    with pytest.raises(session_module.SchemaNotReady) as refused:
        run_async(session_module.verify_schema)
    assert "rate_window.count" in str(refused.value)

    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


# ── 5. оплаченный ход беседы переживает остановку ──────────────────────────


def test_the_process_waits_for_a_paid_turn_before_it_goes(schema):
    """Выкладка посреди хода беседы уносила ответ, за который уже заплачено.

    Задача, дописывающая ход, не отменяется — отмена откатывает `session_scope`
    внутри неё, то есть и расход, и списанный вопрос, и сам текст. Поэтому
    остановка её **ждёт**; до правки `lifespan` не ждал вовсе.

    Проверяется через настоящий `lifespan`, а не через вызов помощника: ждать
    умел бы и помощник, которого никто не зовёт, — а именно это и было.
    """
    from alma.api.app import create_app

    finished: list[str] = []

    async def go():
        application = create_app()
        async with application.router.lifespan_context(application):
            async def slow_turn() -> None:
                await asyncio.sleep(0.05)
                finished.append("written")

            task = asyncio.create_task(slow_turn())
            assert deps.STREAM_TURNS.admit(task) is True

        assert finished == ["written"], (
            "остановка не дождалась хода беседы — ответ оплачен и потерян"
        )

    asyncio.run(go())


def test_waiting_for_a_turn_has_an_end(caplog):
    """Ждать дольше, чем нам самим дано, бессмысленно: придёт SIGKILL.

    `gunicorn` даёт воркеру 120 секунд (`graceful_timeout`), поэтому предел
    здесь меньше. Задача, не успевшая в него, не отменяется — отмена и есть
    тот откат, от которого уходим, — но в лог уходит строка, по которой видно,
    за что придётся извиняться.
    """
    import logging

    # Через `import_module`, а не `from alma.api import app`: второе даёт
    # объект FastAPI — `alma/api/__init__.py` кладёт его под тем же именем.
    app_module = import_module("alma.api.app")

    assert app_module.STREAM_TURN_GRACE_SECONDS < 120, (
        "ожидание длиннее graceful_timeout — процесс убьют посреди него"
    )

    async def go():
        forever = asyncio.create_task(asyncio.sleep(30))
        deps.STREAM_TURNS.admit(forever)
        with caplog.at_level(logging.ERROR):
            await app_module._drain_stream_turns(seconds=0.05)
        assert not forever.cancelled(), "ожидание отменило оплаченный ход"
        forever.cancel()
        assert any("still writing" in record.message for record in caplog.records)

    asyncio.run(go())


def test_background_turns_over_the_ceiling_are_still_held_and_complained_about(caplog):
    """Сверх потолка реестр кричит — но ссылку берёт всё равно.

    Тонкое место, и оно стоило одной правки. Сначала `admit` сверх потолка
    задачу **не добавлял**, и это выглядело как ограничитель, а работало как
    потеря: `asyncio` держит на задачи только слабые ссылки, поэтому задача, на
    которую никто не смотрит, может быть собрана сборщиком мусора посреди
    генерации. То есть «не берём тридцать третий оплаченный ответ под присмотр»
    означало «теряем его наверняка», вместо «теряем, если процесс остановят».

    Отказаться от хода в этой точке нельзя ничем: модель уже позвана и оплачена.
    Значит потолок может быть только громким. Тест держит обе половины: число в
    логе — есть, потеря ссылки — нет.
    """
    registry = deps.TurnRegistry(limit=2)

    async def go():
        tasks = [asyncio.create_task(asyncio.sleep(0.2)) for _ in range(3)]
        assert registry.admit(tasks[0]) is True
        assert registry.admit(tasks[1]) is True
        with caplog.at_level(logging.ERROR):
            assert registry.admit(tasks[2]) is False, "перелив потолка молчит"
        assert len(registry) == 3, (
            "задача сверх потолка не взята под присмотр — сборщик мусора съест "
            "её посреди оплаченной генерации"
        )
        assert tasks[2] in registry.pending(), "остановка не дождётся оплаченного хода"
        assert any(
            "running at once" in record.message for record in caplog.records
        ), "перелив потолка обязан быть виден в логе"
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(go())


def test_a_finished_turn_leaves_the_registry():
    """Реестр не растёт вечно: дописанный ход снимается сам.

    Обратная сторона правки выше. Раз ссылка теперь берётся всегда, единственное,
    что держит реестр конечным, — `add_done_callback`. Если он отвалится, утечка
    будет тихой: не падение, а воркер, который к концу дня помнит все беседы дня.
    """
    registry = deps.TurnRegistry(limit=2)

    async def go():
        task = asyncio.create_task(asyncio.sleep(0))
        registry.admit(task)
        assert len(registry) == 1
        await task
        # Колбэк ставится в очередь цикла, а не зовётся из `await`.
        await asyncio.sleep(0)
        assert len(registry) == 0, "дописанный ход остался в реестре — это утечка"

    asyncio.run(go())


def test_the_router_and_the_drain_watch_the_same_registry():
    """Ход, записанный роутером, обязан быть виден остановке. Один реестр на оба.

    Раньше их было два: `readings._STREAM_TURNS` (голое множество) и
    `deps.STREAM_TURNS`, а `app._pending_turns` читал первое через `getattr` с
    запасным пустым значением. Оба источника снялись, когда роутер переехал на
    реестр, и снялись намеренно: `getattr` молча превращает «структуру
    переименовали» в «ждать нечего», а «ждать нечего» на этой площадке означает
    «оплаченные ответы потеряны» — то есть самый тихий способ вернуть ровно ту
    беду, ради которой всё писалось.

    Тест проверяет не имена, а связь: задача, поданная через имя роутера,
    попадает в то, чего дождётся `lifespan`.
    """
    # Через `import_module`, а не `from alma.api import app`: второе даёт
    # объект FastAPI — `alma/api/__init__.py` кладёт его под тем же именем.
    app_module = import_module("alma.api.app")
    from alma.api.routers import readings

    async def go():
        task = asyncio.create_task(asyncio.sleep(0.2))
        readings._STREAM_TURNS.admit(task)
        try:
            assert task in app_module._pending_turns(), (
                "остановка не увидит хода, записанного роутером"
            )
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(go())


# ── 6. растущие таблицы ────────────────────────────────────────────────────


def test_the_prune_deletes_what_the_privacy_page_promised(schema):
    """Сроки — из обещаний продукта, и здесь их не сокращают молча."""
    from sqlalchemy import func, select

    from alma import funnel
    from alma.db.models import CalcCacheEntry, Event, RateWindow, WebhookEvent

    import tools.prune as prune_tool

    old = datetime.now(timezone.utc) - timedelta(days=funnel.PURGE_AFTER_DAYS + 1)
    fresh = datetime.now(timezone.utc) - timedelta(days=1)

    async def fill():
        async with session_module.session_scope() as session:
            session.add_all([
                Event(anon_id="a" * 12, name="landing_view", properties={}, created_at=old),
                Event(anon_id="b" * 12, name="landing_view", properties={}, created_at=fresh),
                WebhookEvent(id="w-old", event_type="x", received_at=old, payload={}),
                WebhookEvent(id="w-new", event_type="x", received_at=fresh, payload={}),
                RateWindow(
                    id="gone:1:aa",
                    expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                    count=9,
                ),
                RateWindow(
                    id="live:1:bb",
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    count=1,
                ),
                CalcCacheEntry(key="k-old", system="natal", payload={}, created_at=old),
                CalcCacheEntry(key="k-new", system="natal", payload={}, created_at=fresh),
            ])

    run_async(fill)

    counted = run_async(lambda: prune_tool._prune(dry_run=True))
    assert counted == {
        "funnel events": 1,
        "webhook deliveries": 1,
        "rate windows": 1,
        "calc cache": 1,
    }

    async def still_there() -> dict[str, int]:
        async with session_module.session_scope() as session:
            return {
                "events": (await session.execute(
                    select(func.count()).select_from(Event))).scalar_one(),
                "webhooks": (await session.execute(
                    select(func.count()).select_from(WebhookEvent))).scalar_one(),
            }

    assert (run_async(still_there))["events"] == 2, "--dry-run удалил строки"

    run_async(lambda: prune_tool._prune(dry_run=False))
    left = run_async(still_there)
    assert left == {"events": 1, "webhooks": 1}, "старое не удалено или свежее удалено"


def test_the_prune_keeps_the_retention_the_privacy_page_prints():
    """Число живёт в двух местах и обязано быть одним.

    `funnel.PURGE_AFTER_DAYS` печатается на privacy-странице как
    `FUNNEL_RETENTION_DAYS`; чистка вебхуков берёт то же число нарочно — тело
    доставки несёт имя и адрес покупателя, и другого срока про персональные
    данные продукт нигде не называл.
    """
    from alma import funnel

    import tools.prune as prune_tool

    assert funnel.PURGE_AFTER_DAYS == 180
    assert prune_tool.WEBHOOK_RETENTION_DAYS == funnel.PURGE_AFTER_DAYS
    assert prune_tool.CALC_CACHE_RETENTION_DAYS == funnel.PURGE_AFTER_DAYS


def test_the_prune_does_not_touch_conversations_or_readings():
    """Обещание про них напечатано: «While your account exists».

    Любой срок здесь был бы молчаливым сокращением этого обещания, а человек,
    вернувшийся через год перечитать оплаченную главу, — это то, ради чего
    главы вообще хранятся.
    """
    import pathlib

    source = (pathlib.Path(__file__).resolve().parents[1] / "tools" / "prune.py").read_text()
    for table in ("ChatThread", "ChatMessage", "Reading"):
        assert f"delete({table}" not in source, (
            f"{table} попала в чистку — сперва privacy-страница и legal.ts"
        )


def test_the_deploy_document_schedules_both_new_commands():
    """Команда, которую никто не поставил в расписание, ничего не удаляет.

    Ровно так два из трёх существующих заданий не запускались ни разу (§5 того
    же документа), и это единственное, что делало обещание про 180 дней
    неправдой.
    """
    import pathlib

    deploy = (
        pathlib.Path(__file__).resolve().parents[2] / "docs" / "DEPLOY.md"
    ).read_text()
    assert "tools.migrate" in deploy, "шаг миграции не описан в выкладке"
    assert "tools.prune" in deploy, "чистка не поставлена в расписание"


# ── 7. те же счётчики, но уже на месте применения ──────────────────────────
#
# Пункты выше проверяют примитив. Эти — что им действительно пользуются там,
# где стояла беда: в `readings.py`, где между чтением счётчика и его записью
# лежит целая генерация. Примитив, написанный и не подключённый, — это ноль
# закрытых гонок и полная уверенность, что они закрыты.


def test_a_chat_question_is_counted_in_one_statement(schema):
    """Порция «три вопроса в день» пишется одним запросом, а не тремя.

    На старом коде `_count` был `session.get` → `+= 1` → `flush`. Два
    одновременных хода читали один ноль, оба писали единицу, и в счётчике
    оставалась одна на две оплаченные генерации — то есть порция переставала
    быть порцией, причём повторяемо: двойное нажатие «отправить» давало
    бесплатный вопрос столько раз, сколько его нажмут.

    Замок `_chat_slot` эту щель сужал до одного процесса, и в комментарии к нему
    так и написано: «настоящее лекарство — уникальность в базе, и его стоит
    завести в тот день, когда воркеров станет больше одного». Воркеров у нас
    `min(8, cpu*2)`.
    """
    from alma.api.routers import readings

    async def prepare():
        async with session_module.session_scope() as session:
            _new_user(session, "u-asked-1")

    run_async(prepare)

    async def count_one():
        async with session_module.session_scope() as session:
            user = await session.get(_user_model(), "u-asked-1")
            await readings._count(session, user, "questions")

    statements = [
        line.lower() for line in _statements_while(count_one)
        if "usage_counter" in line.lower()
    ]
    assert len(statements) == 1, (
        "вопрос считается больше чем одним запросом — щель между чтением и "
        "записью вернулась: " + " | ".join(statements)
    )
    assert "on conflict" in statements[0] and "returning" in statements[0]
    assert not statements[0].startswith("select"), "счётчик снова читают перед записью"


#: Как здесь моделируется одновременность двух воркеров, и почему именно так.
#:
#: Настоящую её на SQLite не поставишь: два пишущих соединения он сериализует,
#: поэтому «второй» всегда успевает увидеть коммит «первого», и потеря
#: обновления не воспроизводится — тесты проходили бы и на сломанном коде,
#: что хуже, чем не иметь их вовсе.
#:
#: Воспроизводится вот что. Под `READ COMMITTED` (умолчание Postgres) воркер,
#: прочитавший строку, держит **прочитанное** значение, пока чужой коммит меняет
#: настоящее. Приём «прочитать → прибавить в питоне → записать» пишет от
#: устаревшего, и чужая прибавка исчезает. Ровно это состояние здесь и
#: устраивается явно: сессия читает строку (после чего она лежит в её карте
#: объектов), другая сессия прибавляет и коммитит, и только потом первая пишет.
#: Один запрос `… count = count + :n RETURNING count` устаревшего значения не
#: имеет вовсе — он прибавляет там же, где хранит.
#:
#: **Возвращённую строку обязан держать вызывающий, и это не формальность.**
#: Карта объектов SQLAlchemy держит слабые ссылки: строка, которую никто не
#: держит, исчезает в сборщике мусора, `session.get` идёт в базу заново и
#: приносит уже чужое, свежее значение. Тест от этого проходил и на сломанном
#: коде — то есть молча переставал быть тестом. Живая ссылка здесь и есть та
#: половина модели, которая изображает «между нашим SELECT и нашим UPDATE
#: закоммитил кто-то другой».
def _stale_read(session, user_id: str, day, metric: str):
    from alma.db.models import UsageCounter

    return session.get(UsageCounter, counters.counter_id(user_id, day, metric))


def test_two_workers_asking_at_once_do_not_lose_a_question(schema):
    """Потерянное обновление на порции вопросов — и что оно стоит.

    Прежний приём читал пятёрку в обе сессии и записывал шестёрку дважды:
    счётчик показывал шесть там, где вопросов задано семь. Это не «на единицу
    меньше» — это порция, обходимая повторным нажатием сколько угодно раз.
    """
    from alma.api.routers import readings

    today = date.today()

    async def go():
        async with session_module.session_scope() as session:
            _new_user(session, "u-asked-2")
            await counters.add(
                session, user_id="u-asked-2", day=today, metric="questions", count=5
            )

        async with session_module.session_scope() as first:
            user_a = await first.get(_user_model(), "u-asked-2")
            # Первый воркер прочитал счётчик — как читает его `_chat_gate`.
            # Имя обязательно: см. довод у `_stale_read`.
            held = await _stale_read(first, "u-asked-2", today, "questions")
            assert held.count == 5

            # Второй воркер за это время задал свой вопрос и закоммитил.
            async with session_module.session_scope() as second:
                user_b = await second.get(_user_model(), "u-asked-2")
                await readings._count(second, user_b, "questions")

            # И только теперь пишет первый.
            await readings._count(first, user_a, "questions")

        async with session_module.session_scope() as session:
            spent, _cents = await counters.add(
                session, user_id="u-asked-2", day=today, metric="questions", count=0
            )
        assert spent == 7, (
            f"счётчик показывает {spent} после семи вопросов — обновление "
            "потеряно, и порция обходится повторным нажатием"
        )

    run_async(go)


def test_money_two_workers_spent_at_once_is_not_lost(schema):
    """То же для центов, и потеря здесь обиднее.

    Недосчитанные вопросы — это порция, отданная сверх обещанного. Недосчитанные
    центы — это месячный предохранитель, который считает нас дешевле, чем мы
    есть, то есть не срабатывает ровно под той нагрузкой, ради которой поставлен.
    """
    from alma.ai import cost
    from alma.api.routers import readings

    today = date.today()

    async def go():
        async with session_module.session_scope() as session:
            _new_user(session, "u-money-7")
            await counters.add(
                session,
                user_id="u-money-7",
                day=today,
                metric=cost.SPEND_METRIC,
                cents=1.0,
            )

        async with session_module.session_scope() as first:
            user_a = await first.get(_user_model(), "u-money-7")
            held = await _stale_read(first, "u-money-7", today, cost.SPEND_METRIC)
            assert held.amount == pytest.approx(1.0)

            async with session_module.session_scope() as second:
                user_b = await second.get(_user_model(), "u-money-7")
                await readings._spend(second, user_b, 3.0)

            await readings._spend(first, user_a, 4.0)

        async with session_module.session_scope() as session:
            _count, cents = await counters.add(
                session,
                user_id="u-money-7",
                day=today,
                metric=cost.SPEND_METRIC,
                cents=0.0,
            )
        assert cents == pytest.approx(8.0), (
            f"в книге {cents}¢ вместо восьми — расход потерян, и месячный "
            "потолок видит нас дешевле, чем мы есть"
        )

    run_async(go)


def test_the_opening_allowance_is_spent_in_one_statement(schema):
    """Витрина: шестидесятый абзац месяца обязан быть шестидесятым на всех воркерах.

    Ограничитель считает не деньги, а абзацы, и держит петлю «крутить дату
    рождения туда-обратно ради новых бесплатных начал». На старом коде он читал
    строку и прибавлял в питоне, то есть восемь воркеров, каждый со своим нулём,
    проходили шестидесятый восемь раз.
    """
    from alma.api.routers import readings

    async def prepare():
        async with session_module.session_scope() as session:
            _new_user(session, "u-open-1")

    run_async(prepare)

    async def spend_one():
        async with session_module.session_scope() as session:
            user = await session.get(_user_model(), "u-open-1")
            await readings._opening_allowance(session, user)

    statements = [
        line.lower() for line in _statements_while(spend_one)
        if "usage_counter" in line.lower()
    ]
    assert len(statements) == 1, (
        "абзац витрины стоит больше одного запроса: " + " | ".join(statements)
    )
    assert "on conflict" in statements[0] and "returning" in statements[0]


def test_the_opening_allowance_still_refuses_at_sixty_one(schema):
    """Механизм сменился, число — нет. Шестьдесят можно, шестьдесят первый нельзя."""
    from fastapi import HTTPException

    from alma.api.routers import readings

    month = date.today().replace(day=1)

    async def go():
        async with session_module.session_scope() as session:
            _new_user(session, "u-open-2")
            await counters.add(
                session,
                user_id="u-open-2",
                day=month,
                metric=readings.OPENING_METRIC,
                count=readings.OPENING_ALLOWANCE - 1,
            )

        async with session_module.session_scope() as session:
            user = await session.get(_user_model(), "u-open-2")
            # Шестидесятый проходит.
            await readings._opening_allowance(session, user)

        async with session_module.session_scope() as session:
            user = await session.get(_user_model(), "u-open-2")
            with pytest.raises(HTTPException) as caught:
                await readings._opening_allowance(session, user)
        assert caught.value.status_code == 429
        assert caught.value.detail == {"error": "opening_allowance"}

    run_async(go)
