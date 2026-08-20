"""Прод, который не поднимется наполовину, и файлы, которыми его поднимают.

Две группы, и обе — про один и тот же класс отказов: конфигурацию, которая
выглядит рабочей и не работает.

**Первая — отказ стартовать.** До сих пор прод поднимался на SQLite и с пустым
`ANTHROPIC_API_KEY`, и оба отказа обнаруживал первый заплативший: файл-база
отвечала «database is locked» под вторым воркером, пустой ключ — 503 посреди
главы, за которую человек уже отдал деньги. Здесь проверяется, что такой запуск
падает **на старте** и называет всё недостающее разом.

**Вторая — цифры в файлах развёртывания.** Это тесты на текст, и это осознанно:
`graceful_timeout`, `proxy_buffering off` и заголовок `X-Real-IP` — не украшения,
у каждого есть отказ, который он предотвращает, и каждый исчезает от одной
неосторожной правки без единого красного теста. Приложение об этих файлах не
знает, поэтому больше проверить их нечем.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alma import config as config_module

BACKEND = Path(__file__).resolve().parents[1]


def settings_with(monkeypatch, **environment):
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    config_module.settings.cache_clear()
    return config_module.settings()


# ── 1. прод отказывается стартовать наполовину ─────────────────────────────


def test_production_on_sqlite_refuses_to_start(monkeypatch):
    """SQLite в проде — это не «медленнее», это один пишущий на весь сервис.

    Файл держит одну запись за раз, а прод — это несколько воркеров gunicorn
    плюс три регулярных процесса. Пятый претендент получает «database is
    locked», и происходит это посреди чужой оплаченной генерации.
    """
    config = settings_with(
        monkeypatch,
        ALMA_ENV="production",
        ALMA_JWT_SECRET="a-real-secret-value-not-the-default",
        ANTHROPIC_API_KEY="sk-ant-not-a-real-key",
        ALMA_DATABASE_URL="sqlite+aiosqlite:///./data/alma.db",
    )
    with pytest.raises(RuntimeError) as refused:
        config.check_production_ready()
    assert "ALMA_DATABASE_URL" in str(refused.value)
    assert "postgresql" in str(refused.value)


def test_production_without_a_model_key_refuses_to_start(monkeypatch):
    """Расчёты работают и без ключа. Всё, что продаётся, — нет.

    Главы, разговор, утренняя запись — это вызов модели, и без ключа он
    отвечает отказом уже после оплаты.
    """
    config = settings_with(
        monkeypatch,
        ALMA_ENV="production",
        ALMA_JWT_SECRET="a-real-secret-value-not-the-default",
        ALMA_DATABASE_URL="postgresql+asyncpg://alma:pw@db/alma",
        ANTHROPIC_API_KEY="",
    )
    with pytest.raises(RuntimeError) as refused:
        config.check_production_ready()
    assert "ANTHROPIC_API_KEY" in str(refused.value)


def test_production_with_the_development_secret_refuses_to_start(monkeypatch):
    config = settings_with(
        monkeypatch,
        ALMA_ENV="production",
        ALMA_DATABASE_URL="postgresql+asyncpg://alma:pw@db/alma",
        ANTHROPIC_API_KEY="sk-ant-not-a-real-key",
    )
    with pytest.raises(RuntimeError) as refused:
        config.check_production_ready()
    assert "ALMA_JWT_SECRET" in str(refused.value)


def test_an_empty_secret_is_refused_just_like_the_development_one(monkeypatch):
    """`ALMA_JWT_SECRET=` (пусто) обходило проверку и падало 500 у клиента.

    `.env.example` держит переменную пустой как «ещё не задано». Пустая строка
    перезаписывала непустой дефолт, `check_production_ready` пропускал её
    (пусто ≠ «dev-only-not-a-secret»), прод стартовал здоровым — и первый же
    запрос, минтящий токен, падал `HMAC key must not be empty`, 500, перед
    клиентом. Пустое теперь сведено к дефолту и отвергается той же дорогой, что
    и дефолт: громко и на старте. Найдено аудитом 20.08.2026.

    На старом коде прод с пустым секретом стартовал — тест был бы зелёным без
    падения, поэтому `pytest.raises` здесь и сторожит правку.
    """
    config = settings_with(
        monkeypatch,
        ALMA_ENV="production",
        ALMA_JWT_SECRET="",
        ALMA_DATABASE_URL="postgresql+asyncpg://alma:pw@db/alma",
        ANTHROPIC_API_KEY="sk-ant-not-a-real-key",
    )
    with pytest.raises(RuntimeError) as refused:
        config.check_production_ready()
    assert "ALMA_JWT_SECRET" in str(refused.value)


def test_the_refusal_names_everything_missing_at_once(monkeypatch):
    """Иначе настройка прода — это очередь из трёх деплоев.

    Поправил секрет — узнал про базу; поправил базу — узнал про ключ. Список
    собирается целиком и печатается целиком, и это половина ценности проверки:
    читать его будет не программист.
    """
    config = settings_with(monkeypatch, ALMA_ENV="production")
    with pytest.raises(RuntimeError) as refused:
        config.check_production_ready()

    message = str(refused.value)
    for name in ("ALMA_JWT_SECRET", "ALMA_DATABASE_URL", "ANTHROPIC_API_KEY"):
        assert name in message
    # И объясняет, что делать: имя переменной без объяснения — это сообщение,
    # по которому владелец ничего сделать не может.
    assert "secrets.token_urlsafe" in message


def test_a_fully_configured_production_starts(monkeypatch):
    config = settings_with(
        monkeypatch,
        ALMA_ENV="production",
        ALMA_JWT_SECRET="a-real-secret-value-not-the-default",
        ALMA_DATABASE_URL="postgresql+asyncpg://alma:pw@db:5432/alma",
        ANTHROPIC_API_KEY="sk-ant-not-a-real-key",
    )
    config.check_production_ready()  # не должно бросать


def test_billing_is_deliberately_not_a_reason_to_refuse_the_boot(monkeypatch):
    """Сервис считает все восемь систем без процессора, а касса отвечает 503.

    Это рабочее состояние, а не поломка, — и отказ стартовать из-за него
    означал бы, что развернуть продукт до одобрения процессором нельзя вовсе.
    `/ready` его всё равно покажет; см. ниже.
    """
    config = settings_with(
        monkeypatch,
        ALMA_ENV="production",
        ALMA_JWT_SECRET="a-real-secret-value-not-the-default",
        ALMA_DATABASE_URL="postgresql+asyncpg://alma:pw@db/alma",
        ANTHROPIC_API_KEY="sk-ant-not-a-real-key",
    )
    assert config.billing_enabled is False
    config.check_production_ready()


def test_development_stays_frictionless(monkeypatch):
    """Ничего из этого не касается машины разработчика — иначе `RUN-LOCAL.md` врёт."""
    config = settings_with(monkeypatch, ALMA_ENV="development")
    config.check_production_ready()


# ── 2. /ready перестал врать ───────────────────────────────────────────────


def test_ready_is_false_while_the_model_key_is_missing(api):
    """«Готов» означало «база отвечает и эфемериды на месте».

    То есть процесс с пустым `ANTHROPIC_API_KEY` и невыписанными ключами
    процессора отвечал `ready: true` — а наружу уходит только этот флаг. Иначе
    говоря, проверка готовности отвечала «готов» ровно в том состоянии, ради
    которого её и спрашивают: расчёты идут, а всё, что продаётся, отвечает 503.
    """
    body = api.get("/ready").json()
    assert body["checks"]["database"] is True
    assert body["checks"]["ai"] is False
    assert body["ready"] is False


def test_ready_is_true_once_everything_it_lists_is_configured(api, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-a-real-key")
    monkeypatch.setenv("ALMA_BILLING_PROVIDER", "appstore")
    monkeypatch.setenv("APPLE_BUNDLE_ID", "ai.pazl.alma")
    config_module.settings.cache_clear()

    body = api.get("/ready").json()
    assert body["checks"] == {
        "database": True,
        "ephemeris": True,
        "places": True,
        "ai": True,
        "billing": True,
    }
    assert body["ready"] is True


def test_liveness_does_not_depend_on_any_of_it(api):
    """`/health` — про то, жив ли процесс, и только.

    Разделение несущее: `HEALTHCHECK` в образе и в compose спрашивает именно
    его. Если бы живость зависела от ключа модели, развёртывание без кассы
    перезапускалось бы в петле, будучи совершенно исправным.
    """
    body = api.get("/health").json()
    assert body["status"] == "ok"


# ── 3. файлы развёртывания ─────────────────────────────────────────────────


def test_every_deployment_file_the_docs_promise_exists():
    """`docs/DEPLOY.md` ведёт владельца по этим путям. Битая ссылка = стоп."""
    for relative in (
        "Dockerfile",
        "docker-compose.yml",
        "gunicorn.conf.py",
        ".dockerignore",
        "deploy/Caddyfile",
        "deploy/nginx.conf",
        "deploy/systemd/alma-daily.service",
        "deploy/systemd/alma-daily.timer",
        "deploy/systemd/alma-renewals.timer",
        "deploy/systemd/alma-funnel-purge.timer",
    ):
        assert (BACKEND / relative).is_file(), f"{relative} обещан документацией и отсутствует"


def test_gunicorn_waits_long_enough_to_finish_a_paid_generation():
    """Умолчание gunicorn — 30 секунд, а глава пишется до трёх минут.

    При выкатке воркер получает SIGTERM и `graceful_timeout` на то, чтобы
    доработать, после чего SIGKILL. Тридцати секунд не хватает: `ai/provider.py`
    описывает живой случай, где читатель ждал ответа три минуты. Воркер, убитый
    на второй, — это глава, за которую заплатили и которой не получили, и счёт
    за вызов, который нам всё равно выставлен.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("alma_gunicorn_conf", BACKEND / "gunicorn.conf.py")
    conf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conf)

    assert conf.graceful_timeout >= 120
    assert conf.timeout >= 180
    # Наследник `UvicornWorker`, а не он сам, и это не косметика: оригинал не
    # задаёт `timeout_graceful_shutdown`, а без него uvicorn ждёт закрытия
    # открытых соединений без предела и не доходит до остановки приложения —
    # то есть `graceful_timeout` выше тратится на ожидание SSE, а ожидание
    # оплаченных ходов беседы не запускается вовсе. Довод целиком в
    # `alma/api/worker.py`; арифметику трёх чисел сторожит
    # `test_ten_thousand.test_the_process_lets_connections_go_before_it_waits_for_the_work`.
    from alma.api.worker import AlmaUvicornWorker

    assert conf.worker_class == "alma.api.worker.AlmaUvicornWorker"
    assert issubclass(AlmaUvicornWorker, importlib.import_module(
        "uvicorn.workers"
    ).UvicornWorker)
    # По ядрам, а не одна штука: прод жил одним процессом на одном ядре.
    assert conf.workers >= 2
    # Журнал доступа с настоящим адресом клиента, а не с адресом прокси.
    assert "x-real-ip" in conf.access_log_format


@pytest.mark.parametrize("proxy", ["deploy/Caddyfile", "deploy/nginx.conf"])
def test_the_proxy_does_not_break_the_stream_of_stages(proxy):
    """Две умолчательные настройки прокси ломают `/v1/chat/stream`, и обе тихо.

    Буферизация копит ответ и отдаёт целиком — читатель видит пустой экран всю
    генерацию, а потом всё сразу, то есть поток стадий перестаёт существовать.
    Таймаут чтения в минуту читает паузу «модель думает» как обрыв и закрывает
    соединение посреди оплаченной генерации.
    """
    text = (BACKEND / proxy).read_text()
    assert "/v1/chat/stream" in text

    if proxy.endswith("nginx.conf"):
        assert "proxy_buffering off" in text
        assert "proxy_read_timeout 300s" in text
    else:
        assert "flush_interval -1" in text
        assert "read_timeout 300s" in text


@pytest.mark.parametrize("proxy", ["deploy/Caddyfile", "deploy/nginx.conf"])
def test_the_proxy_passes_the_real_client_address(proxy):
    """`api/deps.request_source` читает `X-Real-IP` и намеренно не читает `X-Forwarded-For`.

    Прокси `X-Forwarded-For` *дописывают*, поэтому первый элемент цепочки
    сочиняет клиент, и потолок по источнику снимается одной строкой заголовка.
    Без `X-Real-IP` все запросы мира приходят с адреса прокси, складываются в
    один ключ, и потолок начинает бить по живым людям вместо скрипта.
    """
    text = (BACKEND / proxy).read_text()
    assert "X-Real-IP" in text


@pytest.mark.parametrize("proxy", ["deploy/Caddyfile", "deploy/nginx.conf"])
def test_the_proxy_serves_the_plates_itself(proxy):
    """Картинка, прошедшая через приложение, занимает воркера на секунды.

    Ровно этого воркера не хватает тому, кто в этот момент ждёт главу.
    """
    text = (BACKEND / proxy).read_text()
    assert "/static/plates" in text
    assert "immutable" in text


def test_the_image_does_not_run_as_root():
    """Запись в собственный код — это разница между испорченным томом и бэкдором."""
    dockerfile = (BACKEND / "Dockerfile").read_text()
    assert "USER alma" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    # Две стадии: инструментов сборки в работающем образе быть не должно.
    assert dockerfile.count("FROM ") >= 2
    # Живость проверяется `/health`, не `/ready` — см. `test_liveness_...` выше.
    # Сама команда проверки, а не файл целиком: про `/ready` там написан абзац,
    # объясняющий, почему проверяется не он.
    probe = next(line for line in dockerfile.splitlines() if line.startswith("  CMD"))
    assert "/health" in probe and "/ready" not in probe


def test_no_secret_can_leak_into_the_image_or_the_repository():
    """`.env` в слое образа уезжает в реестр и достаётся всякому, у кого образ."""
    ignored = (BACKEND / ".dockerignore").read_text()
    assert ".env" in ignored
    assert "!.env.example" in ignored
    assert not (BACKEND / ".env").exists() or ".env" in (
        (BACKEND.parent / ".gitignore").read_text()
    )


def test_compose_brings_up_postgres_with_a_volume_that_survives_a_redeploy():
    """Единственный том, потеря которого невосполнима: люди, карты и покупки."""
    compose = (BACKEND / "docker-compose.yml").read_text()
    assert "postgres:16" in compose
    assert "alma-db:/var/lib/postgresql/data" in compose
    # Порт приложения наружу не публикуется: единственный путь снаружи — TLS.
    assert '"443:443"' in compose
    assert '"8000:8000"' not in compose
    # База поднимается раньше приложения, и именно «отвечает», а не «запущена»:
    # `create_all` идёт к ней на первой секунде lifespan.
    assert "service_healthy" in compose
