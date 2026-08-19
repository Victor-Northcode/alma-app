"""Пять мест, где один читатель останавливал всех остальных.

Цель, ради которой это написано, — «десять тысяч человек заходят и сервис
отвечает». Мешало этому не количество запросов, а то, что **один** дорогой
запрос выключал воркер целиком: синхронный расчёт внутри `async def` держит
событийный цикл, а цикл у воркера один на все соединения сразу.

Каждый тест здесь падает на коде, который был до правки:

* годовой скан транзитов считался прямо в цикле — 1.26 с, в течение которых
  воркер не отвечал ни балансировщику, ни чужому запросу, ни уже идущему
  потоку беседы;
* поиск часового пояса — то же самое, 0.33 с на первом вызове, и платил их
  первый живой человек после каждой выкладки;
* фактор для пуша про пару считался в цикле внутри платёжной транзакции;
* LRU расчётов не имел замка, а после переезда в потоки его начали трогать
  одновременно;
* `TransitsRequest` разрешал `days=1095` вместе с Луной — одно тело запроса
  на 11.9 с тишины;
* «Сегодня» открывало два запроса, и годовой скан считался **дважды**, потому
  что две ручки спрашивали одно и то же разными словами.

Метрика везде одна и честная: **пропуск пульса**. Внутри работающего
приложения тикает корутина с периодом 10 мс; если цикл свободен, худший
промежуток между тиками — миллисекунды, а если его держат — он равен
длительности синхронной работы. Числа в порогах — не замеры (они разъедутся на
другой машине), а граница «на порядок меньше, чем сама работа».
"""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import date, datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from alma.api.cache import result_cache
from alma.calc.cache import MemoryCache, compute_cached_async, key_for
from alma.calc.contract import BirthData, build
from conftest import SOFIA, LUCAS


# ── как измеряется «цикл стоял» ────────────────────────────────────────────

class Pulse:
    """Корутина-пульс: тикает каждые `period` и запоминает худший пропуск."""

    def __init__(self, period: float = 0.01) -> None:
        self.period = period
        self.gaps: list[float] = []
        self._running = True

    async def run(self) -> None:
        last = time.perf_counter()
        while self._running:
            await asyncio.sleep(self.period)
            now = time.perf_counter()
            self.gaps.append(now - last)
            last = now

    async def stop(self, task: asyncio.Task) -> None:
        self._running = False
        await task

    @property
    def worst(self) -> float:
        return max(self.gaps) if self.gaps else 0.0


async def _under_pulse(work):
    """Выполнить `work()`, вернуть (сколько длилось, худший пропуск пульса)."""
    pulse = Pulse()
    task = asyncio.create_task(pulse.run())
    await asyncio.sleep(0.05)          # дать пульсу разогнаться

    started = time.perf_counter()
    result = await work()
    elapsed = time.perf_counter() - started

    await pulse.stop(task)
    return result, elapsed, pulse.worst


@pytest.fixture
async def live(tmp_path, monkeypatch):
    """Приложение под настоящим ASGI и своим циклом — не через TestClient.

    `TestClient` уводит приложение на отдельный поток с собственным циклом, и
    измерить из теста, стоял ли **тот** цикл, нельзя вовсе: тест живёт в другом
    потоке и его собственный цикл свободен по построению. Поэтому здесь
    `ASGITransport` — приложение крутится в том же цикле, что и пульс, ровно
    как под uvicorn.
    """
    from alma import config as config_module
    from alma.db import create_all, session as session_module
    from conftest import database_url

    await session_module.dispose()
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "load.db"))
    monkeypatch.setenv("ALMA_ENV", "test")
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()

    from alma.api.app import create_app, thread_pool_size
    from anyio import to_thread

    await create_all()
    result_cache().clear()
    # `ASGITransport` не проигрывает lifespan, а лимитер ставится там. Тесты
    # ниже меряют цикл, а не lifespan, — но пул им нужен настоящий.
    to_thread.current_default_thread_limiter().total_tokens = thread_pool_size()

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token = (await client.get("/v1/auth/session")).json()["token"]
        client.headers["Authorization"] = f"Bearer {token}"
        saved = await client.post("/v1/profiles", json=SOFIA)
        assert saved.status_code in (200, 201), saved.text
        yield client

    await session_module.dispose()
    config_module.settings.cache_clear()


# ── 1. расчёт не держит цикл ───────────────────────────────────────────────

async def test_a_year_of_transits_does_not_stop_the_worker(live):
    """Самый дорогой вызов сервиса — и самый частый: его открывает «Сегодня».

    До правки пульс пропускал ровно столько, сколько длился скан (замерено
    1.257 с при скане 1.269 с — то есть цикл стоял **всё** время расчёта).
    """
    result_cache().clear()

    response, elapsed, worst = await _under_pulse(
        lambda: live.post("/v1/systems/transits", json={})
    )

    assert response.status_code == 200
    assert elapsed > 0.1, "скан обязан быть настоящим, иначе тест ничего не значит"
    assert worst < elapsed / 4, (
        f"цикл стоял {worst:.3f} с из {elapsed:.3f} с расчёта — "
        "значит расчёт по-прежнему в цикле"
    )


async def test_a_cheap_request_is_answered_while_a_scan_is_running(live):
    """То же самое, но глазами балансировщика и чужого читателя.

    Пока идёт скан, `/health` обязан отвечать — и отвечать много раз. До
    правки за 1.35 с скана проходило 11 ответов (то есть цикл отдавали только
    на переключениях вокруг ввода-вывода), после — 170.
    """
    result_cache().clear()

    answered: list[float] = []
    scanning = True

    async def knock():
        while scanning:
            moment = time.perf_counter()
            assert (await live.get("/health")).status_code == 200
            answered.append(time.perf_counter() - moment)
            await asyncio.sleep(0.005)

    knocker = asyncio.create_task(knock())
    started = time.perf_counter()
    response = await live.post("/v1/systems/transits", json={})
    elapsed = time.perf_counter() - started
    scanning = False
    await knocker

    assert response.status_code == 200
    assert elapsed > 0.1
    # При периоде 5 мс за секунду скана проходит больше сотни; порог взят с
    # большим запасом, чтобы медленная машина не сделала тест капризным.
    assert len(answered) > 20 * elapsed, (
        f"за {elapsed:.2f} с расчёта живость спросили всего {len(answered)} раз"
    )


async def test_a_timezone_lookup_does_not_stop_the_worker(live):
    """Первый вызов `timezonefinder` — 0.33 с разворачивания полигонов.

    Прогрев на старте (`app._warm`) снимает эту цену с первого человека, но не
    с воркера, который перезапустился под нагрузкой, — поэтому поток нужен
    отдельно от прогрева.
    """
    from alma import geo

    geo._finder.cache_clear()

    response, elapsed, worst = await _under_pulse(
        lambda: live.get("/v1/places/timezone?latitude=45.4642&longitude=9.19")
    )

    assert response.status_code == 200
    assert response.json()["timezone"] == "Europe/Rome"
    assert worst < max(0.05, elapsed / 4), (
        f"цикл стоял {worst:.3f} с из {elapsed:.3f} с поиска зоны"
    )


async def test_the_place_search_leaves_the_event_loop(live, monkeypatch):
    """Подсказка мест летит на каждое нажатие клавиши — и читает файл.

    Замер длительности здесь ничего не докажет (на горячем кэше страниц
    SQLite это единицы миллисекунд), а доказать надо именно место исполнения:
    страница, которой нет в кэше ОС, — блокирующее чтение с диска, и его
    длительность нам не принадлежит.
    """
    from alma import geo

    seen: dict = {}
    real = geo.search

    def watched(query, *, limit=8):
        seen["thread"] = threading.current_thread()
        return real(query, limit=limit)

    monkeypatch.setattr(geo, "search", watched)

    response = await live.get("/v1/places/search?q=milano")

    assert response.status_code == 200
    assert seen["thread"] is not threading.main_thread()


async def test_the_pair_push_factor_leaves_the_event_loop(monkeypatch):
    """Фактор для пуша считается внутри платёжной транзакции.

    «Расчёт обычно уже в кэше» — правда для клиента, который только что
    смотрел на пару, и неправда для нотификации магазина, прилетающей минутами
    позже в другой воркер. Там это честный промах и синастрия в цикле.
    """
    from alma.notify import pair

    seen: dict = {}
    result_cache().clear()

    def watched(system, birth, **options):
        seen["thread"] = threading.current_thread()
        return build(system=system, birth=birth, data={"overlays": []}, factors=())

    monkeypatch.setattr("alma.calc.service.compute", watched)

    class Row:
        birth_date = date(1998, 3, 14)
        birth_time = "04:20"
        latitude, longitude = 45.4642, 9.19
        timezone = "Europe/Rome"
        place_label = "Milan, Italy"
        name = "Sofia"

    class Other(Row):
        birth_date = date(1995, 7, 2)
        name = "Lucas"

    assert await pair._factor_for(Row(), Other()) is None
    assert seen["thread"] is not threading.main_thread()


# ── 2. кэш расчётов под замком ─────────────────────────────────────────────

#: Восемь потоков — столько же порядка, сколько токенов в пуле
#: (`app.thread_pool_size()` на этой машине — 20). Ёмкость 8 при 256 ключах
#: означает, что вытеснение идёт почти на каждой записи: это и есть узкое
#: место, а не размер кэша. В проде ёмкость 2048 — гонка там та же, просто
#: реже, то есть «раз в день у кого-то», а не «пять раз из пяти».
THREADS = 8
ROUNDS = 400
CAPACITY = 8
KEYS = 256


def test_the_result_cache_survives_being_used_from_many_threads():
    """LRU без замка ломается ровно тогда, когда расчёты уехали в потоки.

    И `get`, и `put` — два шага над одним словарём: найти (или записать) и
    переставить в конец. Между ними стоит вызов, а вызов — точка, в которой
    интерпретатор отдаёт GIL. Другой поток за это время вытесняет ключ, только
    что записанный первым и ещё не переставленный, и `move_to_end` падает
    `KeyError` посреди чужого запроса — то есть 500 на ровном месте, у
    случайного человека, не воспроизводимая.

    `setswitchinterval` опущен на микросекунду **нарочно**: гонка существует и
    на умолчании (5 мс), но там она стреляет раз в тысячи прогонов — то есть в
    проде на десяти тысячах читателей ежедневно, а в CI никогда. Сжатие
    интервала не создаёт новую беду, а делает существующую воспроизводимой;
    ровно так же поступают тесты потолков в `test_hardening.py`, подменяя
    большие числа маленькими. Замерено: на этой конфигурации без замка падает
    5 прогонов из 5, на умолчании — 0 из 5.
    """
    import sys

    cache = MemoryCache(capacity=CAPACITY)
    birth = BirthData(
        date=date(1998, 3, 14), latitude=45.4642, longitude=9.19,
        timezone="Europe/Rome", time="04:20",
    )
    results = [
        build(system="natal", birth=birth, data={"n": n}, factors=(f"factor {n}",))
        for n in range(KEYS)
    ]
    failures: list[BaseException] = []
    barrier = threading.Barrier(THREADS)

    def hammer(offset: int) -> None:
        barrier.wait()
        try:
            for round_ in range(ROUNDS):
                index = (offset * 37 + round_) % KEYS
                cache.put(f"key-{index}", results[index])
                found = cache.get(f"key-{index}")
                if found is not None:
                    # Промах законен — запись могли вытеснить. Чужой ответ под
                    # своим ключом — нет: это и есть порча, которую ловим.
                    assert found.data["n"] == index, (index, found.data)
        except BaseException as exc:      # noqa: BLE001 — тест ради этого и есть
            failures.append(exc)

    was = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        threads = [threading.Thread(target=hammer, args=(i,)) for i in range(THREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        sys.setswitchinterval(was)

    assert failures == [], failures
    assert cache.size <= cache.capacity, (
        f"{cache.size} записей при ёмкости {cache.capacity} — вытеснение сломано"
    )
    # Не детектор, а утверждение: счётчики читает `/ready`, и они обязаны
    # сойтись с числом вызовов. Сегодняшний CPython их `+= 1` не рвёт (точек
    # проверки между чтением атрибута и записью в цикле интерпретатора нет) —
    # но обещания такого нигде нет, и на сборке без GIL его точно не будет.
    assert cache.hits + cache.misses == THREADS * ROUNDS, (
        f"{cache.hits} + {cache.misses} вместо {THREADS * ROUNDS}"
    )


async def test_two_workers_computing_the_same_thing_agree(monkeypatch):
    """Одновременный промах по одному ключу отдаёт один и тот же ответ.

    Расчёт нарочно медленный, чтобы оба потока гарантированно оказались внутри
    него разом — та самая гонка, которой до потоков не могло быть.
    """
    cache = MemoryCache(capacity=8)
    birth = BirthData(
        date=date(1998, 3, 14), latitude=45.4642, longitude=9.19,
        timezone="Europe/Rome", time="04:20",
    )
    computed = 0

    def slow(system, birth_, **options):
        nonlocal computed
        computed += 1
        time.sleep(0.05)
        return build(system=system, birth=birth_, data={"ok": True}, factors=("f",))

    monkeypatch.setattr("alma.calc.service.compute", slow)

    both = await asyncio.gather(*(
        compute_cached_async("natal", birth, cache=cache, house_system="placidus")
        for _ in range(2)
    ))

    assert both[0].data == both[1].data == {"ok": True}
    assert cache.size == 1, "два одинаковых вопроса — одна запись"


# ── 3. прогрев на старте ───────────────────────────────────────────────────

def test_startup_does_not_wait_for_the_warm_up(tmp_path, monkeypatch):
    """Готовность процесса не платит за прогрев — иначе он вреден.

    Прогрев стоит 0.36 с (полигоны часовых поясов — 0.33 с из них). Если бы
    lifespan его дожидался, эти 0.36 с добавились бы к каждому старту воркера,
    а во время выкладки это окно, в котором балансировщик не видит ни старый
    процесс, ни новый. Порог 2 с — не про скорость прогрева, а про то, что его
    вообще **не ждут**: `create_all` на пустой SQLite и так укладывается
    в сотые.
    """
    from fastapi.testclient import TestClient

    from alma import config as config_module
    from alma import geo
    from alma.api.app import create_app
    from alma.db import session as session_module
    from conftest import database_url

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "warm.db"))
    monkeypatch.setenv("ALMA_ENV", "test")
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()

    # Холодный процесс: прогревать должно быть что.
    geo._finder.cache_clear()
    geo._zone_names.cache_clear()

    started = time.perf_counter()
    with TestClient(create_app()) as client:
        boot = time.perf_counter() - started
        assert client.get("/health").status_code == 200

        deadline = time.time() + 10.0
        while geo._finder.cache_info().currsize == 0 and time.time() < deadline:
            time.sleep(0.02)

        assert geo._finder.cache_info().currsize == 1, (
            "полигоны часовых поясов так и не загрузились — прогрев не сработал"
        )
        assert geo._zone_names.cache_info().currsize == 1

    assert boot < 2.0, f"старт занял {boot:.3f} с — готовность ждёт прогрева"

    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


def test_a_missing_place_index_does_not_stop_the_process(tmp_path, monkeypatch):
    """Прогрев — оптимизация, а не проверка готовности.

    Индекса мест может не быть (`/places/search` честно отвечает на это 503),
    и обменивать работающий сервис на тёплый кэш нельзя.
    """
    from alma.api.app import _warm

    def explode() -> bool:
        raise RuntimeError("no place index on this machine")

    monkeypatch.setattr("alma.geo.index_available", explode)
    _warm()          # не поднимает — этого и добиваемся


def test_the_thread_pool_is_sized_by_the_machine(tmp_path, monkeypatch):
    """Потолок одновременной синхронной работы — решение, а не умолчание anyio.

    Умолчание — 40. Замерено: годовой скан в потоках не ускоряется вовсе
    (20 штук разом заняли 22.3 с против 20 × 1.1 с по одному), так что лишние
    токены только растягивают ответ всем сразу. Проверяется, что число
    поставлено и что оно взято от машины, а не зашито.
    """
    import os

    from fastapi.testclient import TestClient
    from anyio import to_thread

    from alma import config as config_module
    from alma.api.app import create_app, thread_pool_size
    from alma.db import session as session_module
    from conftest import database_url

    assert thread_pool_size() == (os.cpu_count() or 4) * 2

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "pool.db"))
    monkeypatch.setenv("ALMA_ENV", "test")
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()

    seen: dict = {}

    with TestClient(create_app()) as client:
        @client.app.get("/_pool_for_the_test")
        async def _pool() -> dict:
            seen["tokens"] = to_thread.current_default_thread_limiter().total_tokens
            return {}

        client.get("/_pool_for_the_test")

    assert seen["tokens"] == thread_pool_size()

    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


# ── 4. потолок окна транзитов ──────────────────────────────────────────────

@pytest.mark.parametrize(
    "body, expect",
    [
        ({}, 200),                                        # то, что шлёт клиент
        ({"days": 365}, 200),                             # то, что шлёт readings
        ({"days": 90}, 200),
        ({"days": 366}, 422),
        ({"days": 1095}, 422),                            # прежний потолок
        ({"days": 31, "include_moon": True}, 200),
        ({"days": 32, "include_moon": True}, 422),
        ({"days": 1095, "include_moon": True}, 422),      # 11.9 с одним телом
    ],
)
def test_the_transit_window_has_an_honest_ceiling(api, auth_headers, body, expect):
    """Потолок взят из того, что продукт действительно просит.

    Клиент шлёт пустое тело, `readings._options_for` — ровно 365,
    `daily.SCAN_DAYS` — те же 365. Больше года не просит никто; прежний
    потолок 1095 вместе с Луной стоил 11.9 с замеренного времени на запрос.
    """
    assert api.post("/v1/profiles", json=SOFIA, headers=auth_headers).status_code in (200, 201)

    response = api.post("/v1/systems/transits", json=body, headers=auth_headers)

    assert response.status_code == expect, response.text


def test_the_refusal_says_why_in_words_a_person_can_read(api, auth_headers):
    """422 обязан объяснять, а не печатать границу диапазона."""
    assert api.post("/v1/profiles", json=SOFIA, headers=auth_headers).status_code in (200, 201)

    year = api.post(
        "/v1/systems/transits", json={"days": 800}, headers=auth_headers
    ).json()
    moon = api.post(
        "/v1/systems/transits",
        json={"days": 200, "include_moon": True},
        headers=auth_headers,
    ).json()

    said = str(year["detail"])
    assert "365 days" in said and "product asks for" in said, said

    said = str(moon["detail"])
    assert "27 days" in said and "31 days" in said, said


# ── 5. «Сегодня» считает год один раз ──────────────────────────────────────

def test_opening_today_scans_the_year_once(api, auth_headers, monkeypatch):
    """Экран открывает два запроса, а годовой скан обязан быть один.

    `today_model.load` пускает `_loadSky` (`POST /systems/transits`) и
    `_loadLine` (`POST /v1/readings` для главы `transits/active`) одновременно.
    Обе ручки просят у движка один и тот же год для одного и того же рождения,
    но ключи расходились: эта клала в опции `include_moon=False`, а
    `readings._options_for` его не шлёт вовсе, и `contract.cache_key` собирает
    ключ из **переданных** опций. Один и тот же скан по 1.26 с считался дважды
    за каждое открытие главного экрана продукта.

    Считаются вызовы самого движка, а не ключи: ключ — это то, чем починили,
    а сломано было именно «посчиталось дважды».
    """
    from alma.api.deps import birth_from_input
    from alma.api.routers import readings as readings_route
    from alma.api.schemas import BirthInput
    from conftest import run_async

    assert api.post("/v1/profiles", json=SOFIA, headers=auth_headers).status_code in (200, 201)
    result_cache().clear()

    scans: list[dict] = []
    import alma.calc.service as service_module

    real = service_module.compute

    def counting(system, birth, **options):
        if system == "transits":
            scans.append(options)
        return real(system, birth, **options)

    monkeypatch.setattr(service_module, "compute", counting)

    # 1. экран неба
    assert api.post("/v1/systems/transits", json={}, headers=auth_headers).status_code == 200

    # 2. письмо дня — тем же вызовом, каким его берёт роутер чтений; сам роутер
    #    сюда не зовётся только потому, что за ним стоит модель и деньги.
    birth = birth_from_input(BirthInput(**SOFIA))
    options = readings_route._options_for("transits", "placidus")
    run_async(lambda: readings_route._calc("transits", birth, **options))

    assert len(scans) == 1, (
        f"год посчитан {len(scans)} раза за одно открытие «Сегодня»: {scans}"
    )


def test_both_halves_of_today_ask_the_same_question(api, auth_headers, monkeypatch):
    """То же самое, но по ключу — так видно не только «дважды», но и почему.

    Ключ подсматривается там, где его строят, а не собирается в тесте заново:
    собранный заново он проверял бы, что `key_for` детерминирована, а не что
    две ручки задают один вопрос.
    """
    import alma.calc.cache as cache_module

    from alma.api.deps import birth_from_input
    from alma.api.routers import readings as readings_route
    from alma.api.schemas import BirthInput
    from conftest import run_async

    assert api.post("/v1/profiles", json=SOFIA, headers=auth_headers).status_code in (200, 201)
    result_cache().clear()

    keys: list[str] = []
    real = cache_module.key_for

    def watching(system, birth, options):
        key = real(system, birth, options)
        if system == "transits":
            keys.append(key)
        return key

    monkeypatch.setattr(cache_module, "key_for", watching)

    assert api.post("/v1/systems/transits", json={}, headers=auth_headers).status_code == 200

    birth = birth_from_input(BirthInput(**SOFIA))
    options = readings_route._options_for("transits", "placidus")
    run_async(lambda: readings_route._calc("transits", birth, **options))

    assert len(keys) == 2, keys
    assert keys[0] == keys[1], "две половины «Сегодня» спрашивают разными ключами"


def test_asking_for_the_moon_is_still_a_different_question(api, auth_headers):
    """Убрали повтор, а не различие: с Луной ответ другой и запись другая."""
    from alma.api.deps import birth_from_input
    from alma.api.schemas import BirthInput

    birth = birth_from_input(BirthInput(**LUCAS))
    base = {"start": datetime(2026, 6, 1, tzinfo=timezone.utc), "days": 31,
            "house_system": "placidus"}

    assert key_for("transits", birth, base) != key_for(
        "transits", birth, base | {"include_moon": True}
    )
