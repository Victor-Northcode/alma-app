"""Соединение с базой не удерживается, пока работает модель.

**Что здесь доказывается и почему это самый дорогой из известных дефектов.**

Пул по умолчанию у SQLAlchemy 2.0 — `pool_size=5` плюс `max_overflow=10`, то
есть 15 соединений на процесс, и `pool_timeout=30`. Транзакция запроса
открывается первым же SELECT в `api/deps.visitor` — то есть на КАЖДОМ запросе
с токеном, — а FastAPI держит yield-зависимость до конца ответа. У
генерирующих роутов между этим SELECT и коммитом лежал вызов модели: 10–40
секунд, до трёх попыток. Замер на исходном коде (`pytest` тут ни при чём, это
был отдельный прогон пятнадцати параллельных `POST /v1/readings`):

    pool: size=5 overflow=10 timeout=30.0 → потолок 15
    одновременных генераций: 15 | занято соединений: 15
    дешёвый /billing/catalogue упал за 30.0s:
        TimeoutError: QueuePool limit of size 5 overflow 10 reached

То есть шестнадцатый запрос — любой, включая самый дешёвый в продукте —
получал 500 через полминуты, и умирал он не из-за собственной цены, а из-за
того, что пул общий.

Тесты ниже проверяют три разных утверждения, и все три падают на коде до
правки:

* `test_generation_holds_no_pool_connection` — во время вызова модели занято
  ноль соединений. Мерится изнутри провайдера, то есть ровно в тот момент,
  который и был дорогим;
* `test_a_cheap_request_lives_through_a_full_house_of_generations` — с пулом,
  сжатым до двух соединений, три одновременные генерации не мешают дешёвому
  запросу пройти. На старом коде две генерации выбирали пул целиком;
* `test_the_pool_is_sized_explicitly_and_only_postgres_gets_server_timeouts` —
  числа заданы явно и серверные таймауты не уезжают на SQLite.

Клиент здесь `httpx.AsyncClient` поверх ASGI, а не `TestClient`: `TestClient`
ведёт запросы через портальный поток и параллельных запросов из тела теста не
даёт, а весь вопрос — именно про одновременность.
"""

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest import SOFIA, database_url


SLOW_MODEL_TIMEOUT = 20


class GatedProvider:
    """Модель, которая «пишет» ровно столько, сколько её держит тест.

    Не `ScriptedProvider` с задержкой: важна не задержка, а возможность
    остановить генерацию в её середине и посмотреть на пул именно там. Заодно
    записывает `pool.checkedout()` в момент вызова — это и есть измеряемая
    величина.
    """

    def __init__(self, payload: str, *, gate: asyncio.Event | None = None):
        self.payload = payload
        self.gate = gate
        self.arrived = asyncio.Event()
        self.calls = 0
        #: Сколько соединений пула было занято на момент каждого вызова модели.
        self.checked_out: list[int] = []

    async def complete(self, *, system, prompt, model, max_tokens=4096,
                       schema=None, cache_system=False, effort=None):
        from alma.ai.provider import Completion
        from alma.db.session import engine

        self.calls += 1
        self.checked_out.append(engine().pool.checkedout())
        self.arrived.set()
        if self.gate is not None:
            await asyncio.wait_for(self.gate.wait(), timeout=SLOW_MODEL_TIMEOUT)
        return Completion(
            text=self.payload, model=model, input_tokens=1200, output_tokens=400
        )


def _chapter_reply(factors: list[str]) -> str:
    """Три абзаца — минимум платной главы; см. довод в `test_readings_api`."""
    return json.dumps(
        {
            "title": "Life path",
            "teaser": "A line.",
            "advice": "Say the thing sooner.",
            "paragraphs": [
                {"text": "The first paragraph, read from the chart.", "factors": factors[:1]},
                {"text": "The second, from the same place.", "factors": factors[:1]},
                {"text": "The third, still from the chart.", "factors": factors[:1]},
            ],
        }
    )


def _factors() -> list[str]:
    from datetime import date, datetime, timezone

    from alma.calc import BirthData, compute

    birth = BirthData(
        date=date.fromisoformat(SOFIA["birth_date"]),
        time=SOFIA["birth_time"],
        latitude=SOFIA["latitude"],
        longitude=SOFIA["longitude"],
        timezone=SOFIA["timezone"],
        place_label=SOFIA["place_label"],
        name=SOFIA["name"],
    )
    return list(
        compute("numerology", birth, reference=datetime.now(timezone.utc).date()).factors
    )


@pytest.fixture
def opened(monkeypatch):
    """Всё куплено: тест не про пейволл, а про соединения."""
    from alma.auth import entitlements

    async def yes(session, user, system, *, chapter=None, partner_id=None, at=None):
        return entitlements.Access(True, "bought in the test", kind="one_time")

    monkeypatch.setattr(entitlements, "check", yes)


@pytest.fixture
async def app(tmp_path, monkeypatch):
    """Приложение на своей пустой базе, поднятое в этом же цикле событий."""
    from alma import config as config_module
    from alma.db import session as session_module

    await session_module.dispose()
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "pool.db"))
    monkeypatch.setenv("ALMA_ENV", "test")
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()

    from alma.api.app import create_app
    from alma.api.cache import result_cache

    result_cache().clear()
    built = create_app()
    await session_module.create_all()
    try:
        yield built
    finally:
        await session_module.dispose()
        config_module.settings.cache_clear()


async def _account(client) -> dict:
    """Гость с сохранённым рождением — всё, что нужно для генерации."""
    token = (await client.get("/v1/auth/session")).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/v1/profiles", json=SOFIA, headers=headers)
    return headers


async def test_generation_holds_no_pool_connection(app, opened) -> None:
    """Пока модель пишет главу, занятых соединений ноль.

    Мерится изнутри `complete`, потому что мерить снаружи нечестно: между
    двумя короткими транзакциями соединение и правда свободно, а вопрос стоит
    про те самые десятки секунд, что лежат посередине.

    На коде до правки здесь была единица — соединение, взятое SELECT'ом в
    `deps.visitor` и не отпущенное до конца ответа. Единица на запрос при пуле
    в пятнадцать и есть весь дефект.
    """
    from alma.api.deps import get_provider

    provider = GatedProvider(_chapter_reply(_factors()))
    app.dependency_overrides[get_provider] = lambda: (lambda: provider)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers = await _account(client)
        answer = await client.post(
            "/v1/readings",
            json={"system": "numerology", "chapter": "life-path", "locale": "en"},
            headers=headers,
        )

    assert answer.status_code == 200, answer.text
    assert provider.calls == 1, "глава должна была писаться ровно один раз"
    assert provider.checked_out == [0], (
        "во время генерации соединение пула не должно удерживаться; занято: "
        f"{provider.checked_out}"
    )


async def test_the_opening_paragraph_holds_no_connection_either(app) -> None:
    """Та же проверка на массовом бесплатном пути — закрытой главе.

    Отдельным тестом, а не параметром к предыдущему: это другой код
    (`_locked_chapter` → `_write_opening`), и приходит сюда почти весь трафик
    продукта — сорок закрытых глав против одной открытой.
    """
    from alma.api.deps import get_provider

    opening = json.dumps(
        {
            "title": "Life path",
            "teaser": "A line.",
            "paragraphs": [
                {"text": "Forty words about you, read from the chart.",
                 "factors": _factors()[:1]},
            ],
        }
    )
    provider = GatedProvider(opening)
    app.dependency_overrides[get_provider] = lambda: (lambda: provider)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers = await _account(client)
        answer = await client.post(
            "/v1/readings",
            json={"system": "numerology", "chapter": "life-path", "locale": "en"},
            headers=headers,
        )

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["locked"] is True, "глава платная, значит это стена с абзацем"
    assert body["opening"] is not None, "абзац должен был написаться"
    assert provider.checked_out == [0], (
        "открывающий абзац пишется без открытого соединения; занято: "
        f"{provider.checked_out}"
    )


async def test_a_chat_turn_holds_no_connection(app) -> None:
    """И беседа тоже: `/v1/chat` — второй по объёму путь генерации."""
    from alma.api.deps import get_provider

    reply = json.dumps(
        {
            "answer": [
                {"text": "Here is what the chart says.", "factors": _factors()[:1]}
            ],
            "answered_from_chart": True,
            "remember": [],
        }
    )
    provider = GatedProvider(reply)
    app.dependency_overrides[get_provider] = lambda: (lambda: provider)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers = await _account(client)
        answer = await client.post(
            "/v1/chat", json={"message": "What should I do about work?"},
            headers=headers,
        )

    assert answer.status_code == 200, answer.text
    assert provider.checked_out and set(provider.checked_out) == {0}, (
        "ход беседы не должен держать соединение через генерацию; занято: "
        f"{provider.checked_out}"
    )


async def test_a_cheap_request_lives_through_a_full_house_of_generations(
    tmp_path, monkeypatch, opened
) -> None:
    """Дешёвый запрос проходит, пока идут генерации числом больше пула.

    Пул сжат до двух соединений без overflow — те же пятнадцать, только
    быстрее: смысл в том, что генераций **больше**, чем пул может выдать, и
    именно этим старый код и убивал остальной трафик. Три генерации держатся
    внутри модели одновременно, и в этот момент запрашивается
    `GET /v1/billing/catalogue` — самый дешёвый маршрут в продукте.

    На коде до правки этот тест падает дважды: третья генерация не может взять
    соединение (две первые его держат) и каталог тоже, — обе ждут
    `pool_timeout` и получают 500.
    """
    from alma import config as config_module
    from alma.api.app import create_app
    from alma.api.cache import result_cache
    from alma.api.deps import get_provider
    from alma.db import session as session_module

    await session_module.dispose()
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "tight.db"))
    monkeypatch.setenv("ALMA_ENV", "test")
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()

    # Сжатый пул: два соединения, ни одного сверх, и короткое ожидание — чтобы
    # падение было падением, а не тридцатисекундной паузой в наборе тестов.
    monkeypatch.setattr(session_module, "POOL_SIZE", 2)
    monkeypatch.setattr(session_module, "MAX_OVERFLOW", 0)
    monkeypatch.setattr(session_module, "POOL_TIMEOUT", 2)

    result_cache().clear()
    app = create_app()
    await session_module.create_all()

    gate = asyncio.Event()
    provider = GatedProvider(_chapter_reply(_factors()), gate=gate)
    app.dependency_overrides[get_provider] = lambda: (lambda: provider)

    generations = 3
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://t", timeout=60
        ) as client:
            people = [await _account(client) for _ in range(generations)]

            assert session_module.engine().pool.size() == 2, "пул должен быть сжат"

            running = [
                asyncio.create_task(
                    client.post(
                        "/v1/readings",
                        json={"system": "numerology", "chapter": "life-path",
                              "locale": "en"},
                        headers=headers,
                    )
                )
                for headers in people
            ]

            # Ждём, пока все три действительно окажутся внутри модели.
            for _ in range(200):
                if provider.calls >= generations:
                    break
                await asyncio.sleep(0.05)
            assert provider.calls == generations, (
                f"внутри модели оказалось {provider.calls} из {generations} — "
                "остальные не дошли, потому что пул кончился"
            )
            assert session_module.engine().pool.checkedout() == 0, (
                "три идущие генерации не должны занимать ни одного соединения"
            )

            cheap = await client.get("/v1/billing/catalogue", headers=people[0])
            assert cheap.status_code == 200, (
                "дешёвый запрос обязан проходить, пока идут генерации: "
                f"{cheap.status_code} {cheap.text[:200]}"
            )

            gate.set()
            done = [await task for task in running]
            assert [r.status_code for r in done] == [200] * generations, (
                [r.text[:200] for r in done if r.status_code != 200]
            )
    finally:
        gate.set()
        await session_module.dispose()
        config_module.settings.cache_clear()


def test_the_pool_is_sized_explicitly_and_only_postgres_gets_server_timeouts() -> None:
    """Числа пула заданы, а серверные таймауты — только на asyncpg.

    Вторая половина не педантизм: `statement_timeout` и соседи — это GUC
    Postgres, и aiosqlite на них падает при первом же `connect()`, то есть
    ошибка ветвления здесь means «сервер не поднимается на машине
    разработчика».
    """
    from alma.db.session import (
        ASYNCPG_SERVER_SETTINGS,
        MAX_OVERFLOW,
        POOL_RECYCLE,
        POOL_SIZE,
        POOL_TIMEOUT,
        engine_options,
    )

    postgres = engine_options("postgresql+asyncpg://alma@127.0.0.1/alma")
    assert postgres["pool_size"] == POOL_SIZE == 20
    assert postgres["max_overflow"] == MAX_OVERFLOW == 10
    assert postgres["pool_timeout"] == POOL_TIMEOUT == 10
    assert postgres["pool_recycle"] == POOL_RECYCLE == 1800
    assert postgres["pool_pre_ping"] is True
    assert postgres["connect_args"]["server_settings"] == {
        "statement_timeout": "15000",
        "lock_timeout": "3000",
        "idle_in_transaction_session_timeout": "30000",
    }
    assert postgres["connect_args"]["server_settings"] == ASYNCPG_SERVER_SETTINGS

    sqlite = engine_options("sqlite+aiosqlite:///./alma.db")
    assert sqlite["pool_size"] == POOL_SIZE
    assert "connect_args" not in sqlite, (
        "серверные таймауты Postgres на SQLite роняют подключение"
    )

    # Три воркера по 20+10 — это 90 соединений, и это то число, ради которого
    # 20 выбрано именно так: `max_connections` у Postgres по умолчанию 100, из
    # них три зарезервированы за суперпользователем.
    assert (POOL_SIZE + MAX_OVERFLOW) * 3 <= 97


async def test_the_configured_pool_actually_connects(app) -> None:
    """Смоук: с этими опциями SQLite действительно открывается.

    Утверждение выше проверяет, что `connect_args` не уехал на SQLite, а это —
    что остальные пять опций драйвер принял. Одно без другого проверяет
    половину.
    """
    from alma.db.session import engine, healthy

    assert await healthy() is True
    assert engine().pool.size() == 20
