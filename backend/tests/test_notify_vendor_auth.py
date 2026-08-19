"""Протухший bearer против негодного ключа — два состояния, которые FCM
отвечает одним кодом, и до этой правки мы читали оба как второе.

Токен доступа Google живёт час и кэшируется на пятьдесят минут (`fcm._LIFETIME`).
Десяти минут запаса не хватает ровно в двух обыденных случаях: часы хоста ушли
вперёд относительно Google, и прогон, начавшийся за минуту до границы, дошёл до
тысячного получателя уже за ней. В обоих Google отвечает `401`.

`FCM.read` переводит 401 в `Verdict.fatal` — «наши учётные данные неверны для
всех токенов», — а `daily.deliver` на `fatal` снимает вендора с прогона. То есть
**один просроченный кэш отменял утро всем подписчикам на Android**, и лечился он
сам собой через час, что делало его ещё и неуловимым.

Здесь проверяется ровно одно поведение: 401 → выбросить кэш, выпустить токен
заново, повторить **один раз**. Не в цикле: 401 на свежевыданном токене — это
уже действительно негодный сервис-аккаунт, и второй ответ будет тем же.

Сокета нет: `httpx.AsyncClient` подменён, `access_token` — тоже. Проверяется
собственная логика отправителя, а не то, что Google отвечает как в документации.
"""

from __future__ import annotations

import time

import pytest

from alma.notify import fcm
from alma.notify.transport import Push, Verdict


class Reply:
    """Ответ httpx в объёме, который читает `FCM.send`."""

    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


class Row:
    """Строка `DeviceToken` в объёме, который читает конверт."""

    token = "d" * 64
    platform = "android"
    environment = None
    locale = "en"


@pytest.fixture
def google(monkeypatch):
    """Настроенный FCM без единого настоящего креденшала."""
    from alma import config as config_module

    monkeypatch.setenv("ALMA_FCM_SERVICE_ACCOUNT_JSON", '{"client_email":"a@b","private_key":"x"}')
    monkeypatch.setenv("ALMA_FCM_PROJECT_ID", "alma-test")
    config_module.settings.cache_clear()
    fcm._forget_token()
    yield
    fcm._forget_token()
    config_module.settings.cache_clear()


def transport(monkeypatch, replies: list[Reply]):
    """Подменённый httpx, отдающий заранее написанные ответы по порядку.

    Возвращает список отправленных заголовков `Authorization` — по нему и
    видно, что второй запрос ушёл с *другим* токеном, а не с тем же.
    """
    bearers: list[str] = []
    handed = {"n": 0}

    async def mint(*, now=None) -> str:
        handed["n"] += 1
        return f"token-{handed['n']}"

    monkeypatch.setattr(fcm, "access_token", mint)

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None, headers=None):
            bearers.append((headers or {}).get("Authorization", ""))
            return replies.pop(0)

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    return bearers


def test_a_401_re_mints_the_token_and_retries_once(google, monkeypatch):
    """Протухший кэш стоит одной перевыдачи, а не утра всех подписчиков."""
    bearers = transport(monkeypatch, [Reply(401, '{"error":{"status":"UNAUTHENTICATED"}}'), Reply(200)])
    # Кэш заполнен и «свежий» с точки зрения нашего таймера: именно это
    # состояние Google и опровергает своим 401.
    fcm._token = ("stale-bearer", time.time())

    receipt = _send(monkeypatch)

    assert receipt.verdict is Verdict.sent
    assert len(bearers) == 2, "повтора не было — 401 остался фатальным"
    assert bearers[0] != bearers[1], "повтор ушёл с тем же протухшим токеном"
    assert fcm._token is None, "кэш не выброшен, следующая отправка снова получит 401"


def test_a_second_401_is_fatal_rather_than_a_loop(google, monkeypatch):
    """401 на свежевыданном токене — это уже не кэш, а негодный сервис-аккаунт.

    Повторять по нему бессмысленно: ответ будет тем же, а тысяча повторов —
    это тысяча запросов, доказывающих одно и то же.
    """
    bearers = transport(
        monkeypatch,
        [Reply(401, '{"error":{"status":"UNAUTHENTICATED"}}')] * 2,
    )

    receipt = _send(monkeypatch)

    assert receipt.verdict is Verdict.fatal
    assert len(bearers) == 2, "повтор ушёл больше одного раза"


def test_a_403_is_not_retried_because_a_new_token_cannot_help(google, monkeypatch):
    """«Аутентификация прошла, прав нет» — сервис-аккаунту не дали роль.

    Перевыдача токена этого не исправляет, и попытка — это лишний запрос на
    каждое уведомление в прогоне.
    """
    bearers = transport(monkeypatch, [Reply(403, '{"error":{"status":"PERMISSION_DENIED"}}')])

    receipt = _send(monkeypatch)

    assert receipt.verdict is Verdict.fatal
    assert len(bearers) == 1, "403 повторён, хотя новый токен ничего не меняет"


def _send(monkeypatch):
    import asyncio

    sender = fcm.FCM()
    push = Push(title_key="push.daily.title", body_key="push.daily.exact.square", args=("Saturn",))
    return asyncio.run(sender.send(Row(), push))
