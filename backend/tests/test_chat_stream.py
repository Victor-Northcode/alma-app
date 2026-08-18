"""POST /v1/chat/stream — тот же ход беседы, рассказанный по дороге.

Четыре обещания нового маршрута, каждое своим тестом: стадии приходят до
`done` и названы из настоящих данных запроса; `done` по форме — ровно ответ
`/v1/chat`, потому что клиент разбирает оба одним кодом; квота списывается
один раз на вопрос, а не по разу на каждый вход; отказ квоты отвечает тем же
429 с тем же телом, что старый маршрут, — до первого байта потока, потому
что внутри уже начатого 200 честного 429 не бывает.

Здесь же — глава-источник (`source_chapter`): она называется, когда глава в
контексте ровно одна, и молчит, когда их несколько или ни одной. Поле общее
для обоих маршрутов, а живёт в этом файле потому, что появилось вместе с ним.
"""

from __future__ import annotations

import json

from alma import config as config_module
from alma import i18n
from alma.config import settings
from tests.conftest import SOFIA
from tests.test_readings_api import (  # noqa: F401 — фикстуры регистрируются импортом
    _chapter_reply,
    _chat_reply,
    _factors_for,
    owns,
    scripted,
)


def _events(text: str) -> list[tuple[str, dict]]:
    """SSE-текст → [(event, data)].

    Разбор свой и трёхстрочный намеренно: формат события — «event: имя»,
    «data: json», пустая строка, — и клиент на телефоне разбирает его так же,
    без библиотеки. Тест, который читает провод тем же способом, что и клиент,
    проверяет ровно тот договор, который клиенту нужен.
    """
    parsed: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        name = None
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
        if name is not None:
            parsed.append((name, json.loads("\n".join(data_lines))))
    return parsed


def _done(events: list[tuple[str, dict]]) -> dict:
    return next(data for name, data in events if name == "done")


def _stream(api, headers, message: str):
    return api.post("/v1/chat/stream", json={"message": message}, headers=headers)


def test_stages_arrive_before_done_and_name_real_data(api, auth_headers, scripted):
    """Экран думания получает настоящие шаги, а не театр.

    Дом обязан быть домом из натальной карты этого человека: спека беседы §6 —
    «никаких выдуманных домов», и тест сверяет имя стадии с факторами той же
    карты, которые движок считает без модели.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.append(_chat_reply(factors[:1]))

    response = _stream(api, auth_headers, "What should I do about work?")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _events(response.text)
    kinds = [name for name, _ in events]
    assert kinds[-1] == "done", "поток обязан кончиться ответом"
    assert kinds.count("done") == 1

    stages = [data for name, data in events if name == "stage"]
    assert stages, "ни одной стадии — экран думания остался слепым"
    for data in stages:
        assert data["stage"] in ("house", "body")
        assert data["name"], "стадия без имени — пустая строка на экране"

    houses = [data for data in stages if data["stage"] == "house"]
    assert houses, "у Софии есть время рождения — дома посчитаны и один назван"
    assert houses[0]["name"].isdigit()
    natal = _factors_for(api, auth_headers, "natal")
    assert any(f"house {houses[0]['name']}" in factor for factor in natal), (
        "названный дом не из карты этого человека"
    )


def test_done_is_the_same_answer_the_old_route_gives(api, auth_headers, scripted):
    """Форма `done` и форма `/v1/chat` — один договор, разобранный одним кодом."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.extend([_chat_reply(factors[:1]), _chat_reply(factors[:1])])

    old = api.post(
        "/v1/chat", json={"message": "And work?"}, headers=auth_headers
    ).json()
    done = _done(_events(_stream(api, auth_headers, "And love?").text))

    assert set(done) == set(old), "поля разъехались — клиент увидит дыру"
    assert set(done["message"]) == set(old["message"])
    assert done["message"]["role"] == "alma"
    assert done["message"]["cited_factors"] == factors[:1]
    assert done["questions_period"] == old["questions_period"]
    assert "source_chapter" in done and "source_chapter" in old


def test_the_stream_spends_the_quota_once_per_question(api, auth_headers, scripted):
    """Одно списание на вопрос — не ноль (дыра мимо квоты) и не два."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.extend([_chat_reply(factors[:1]), _chat_reply(factors[:1])])
    allowance = settings().free_welcome_bundle

    first = _done(_events(_stream(api, auth_headers, "What about work?").text))
    assert first["questions_left"] == allowance - 1, "один вопрос — одно списание"
    second = _done(_events(_stream(api, auth_headers, "And money?").text))
    assert second["questions_left"] == allowance - 2


def test_the_quota_refusal_is_the_same_429_as_the_old_route(
    api, auth_headers, scripted, monkeypatch
):
    """Отказ квоты приходит честно: тем же статусом и телом, что у `/v1/chat`.

    До первого байта потока: SSE начинается с 200, и отказ внутри успешного
    ответа был бы вторым языком поломок, который клиенту пришлось бы учить.
    """
    # Через окружение, а не setattr на объекте настроек: cache_clear ниже
    # пересобирает объект, и заплатка на старом экземпляре пропала бы.
    monkeypatch.setenv("ALMA_FREE_QUESTIONS", "0")
    monkeypatch.setenv("ALMA_WELCOME_BUNDLE", "0")
    config_module.settings.cache_clear()
    try:
        streamed = api.post(
            "/v1/chat/stream", json={"message": "hi"}, headers=auth_headers
        )
        plain = api.post("/v1/chat", json={"message": "hi"}, headers=auth_headers)

        assert streamed.status_code == 429, "стрим обязан отказать, а не молчать"
        assert plain.status_code == 429
        assert streamed.headers["content-type"].startswith("application/json"), (
            "отказ — обычный ответ, не поток"
        )
        assert streamed.json()["detail"] == plain.json()["detail"]
        assert streamed.json()["detail"]["error"] == "question_limit"
    finally:
        config_module.settings.cache_clear()


# ── глава-источник ─────────────────────────────────────────────────────────


def test_the_answer_names_the_one_chapter_in_its_context(
    api, auth_headers, scripted, owns
):
    """Одна написанная глава в контексте — ответ называет её, с заголовком
    на языке запроса, и обе ручки говорят одно и то же."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.append(_chapter_reply(factors))
    written = api.post(
        "/v1/readings",
        json={"system": "numerology", "chapter": "life-path"},
        headers=auth_headers,
    )
    assert written.status_code == 200, written.text

    scripted.responses.extend([_chat_reply(factors[:1]), _chat_reply(factors[:1])])
    body = api.post(
        "/v1/chat", json={"message": "What am I built for?"}, headers=auth_headers
    ).json()
    expected = {
        "system": "numerology",
        "slug": "life-path",
        "title": i18n.chapter_words("numerology", "life-path", locale="en").title,
    }
    assert body["source_chapter"] == expected

    done = _done(_events(_stream(api, auth_headers, "And in a year?").text))
    assert done["source_chapter"] == expected


def test_no_chapter_is_invented_for_none_or_several(api, auth_headers, scripted, owns):
    """Глав в контексте ноль или несколько — поле молчит, а не гадает."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)

    scripted.responses.append(_chat_reply(factors[:1]))
    none = api.post(
        "/v1/chat", json={"message": "hi there"}, headers=auth_headers
    ).json()
    assert none["source_chapter"] is None, "глав нет — и источника нет"

    # Две главы, каждая со своими факторами: писатель цитирует только то, что
    # глава имеет право читать (`relevant_factors`), и заготовка с чужим
    # фактором ушла бы в отказ по причине, не относящейся к этому тесту.
    life_path = [f for f in factors if "life path" in f.lower()] or factors
    birthday = [f for f in factors if "birthday number" in f.lower()] or factors
    scripted.responses.extend([_chapter_reply(life_path), _chapter_reply(birthday)])
    for chapter in ("life-path", "birthday-number"):
        wrote = api.post(
            "/v1/readings",
            json={"system": "numerology", "chapter": chapter},
            headers=auth_headers,
        )
        assert wrote.status_code == 200, wrote.text

    scripted.responses.append(_chat_reply(factors[:1]))
    both = api.post(
        "/v1/chat", json={"message": "and now?"}, headers=auth_headers
    ).json()
    assert both["source_chapter"] is None, "из двух глав нельзя честно назвать одну"
