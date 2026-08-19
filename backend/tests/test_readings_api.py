"""Readings and chat over HTTP, with a scripted model behind them.

Everything the user actually pays for passes through these two routes, so the
tests here are about the guarantees rather than the plumbing: a reading is
written once and never changes, a locked chapter never reaches the model, an
invented factor never reaches the reader, and the question counter is a real
limit rather than a suggestion.
"""

from __future__ import annotations

import json

import pytest

from alma.ai.provider import ScriptedProvider
from alma.config import settings
from tests.conftest import SOFIA


@pytest.fixture
def scripted(api):
    """Substitute a scripted provider for the real one, per test."""
    from alma.api.app import create_app  # noqa: F401  (app already built by `api`)
    from alma.api.deps import get_provider

    provider = ScriptedProvider()
    # The dependency yields a *factory*, so that resolving it does no work and
    # the paywall gets to answer before a missing API key can.
    api.app.dependency_overrides[get_provider] = lambda: (lambda: provider)
    yield provider
    api.app.dependency_overrides.clear()


@pytest.fixture
def owns(monkeypatch):
    """Открыть всё, не проходя через магазин.

    Появилась вместе с правилом «бесплатна ровно одна глава во всём продукте».
    До него половина тестов этого файла брала `numerology/life-path` как
    «какую-нибудь бесплатную главу» и проверяла на ней механику чтения:
    написано один раз, выдуманный фактор не доходит до читателя, партнёр
    обязан быть назван. Механика у оплаченной главы та же самая, а вот
    отсутствие права теперь возвращает стену — и такой тест молча
    превращается в тест про пейволл.

    Кто и почему получает доступ — предмет `test_entitlements.py`; здесь это
    условие, а не проверяемое. Поэтому monkeypatch, а не грант через биллинг:
    тест не должен зависеть от того, каким SKU сегодня открывается система.
    """
    from alma.auth import entitlements

    async def yes(session, user, system, *, chapter=None, partner_id=None, at=None):
        return entitlements.Access(True, "bought in the test", kind="one_time")

    monkeypatch.setattr(entitlements, "check", yes)


def _chapter_reply(factors, *, title="Life path", teaser="A line.") -> str:
    # Три абзаца, а не два. Платная глава требует трёх (`Chapter.paragraphs`
    # по умолчанию — (3, 5)), и с тех пор как бесплатная глава в продукте
    # ровно одна, почти всё здесь пишется как платное. Двухабзацная заготовка
    # отвергалась бы валидатором, писатель уходил бы на вторую попытку, и тест
    # падал бы 503-й на кончившемся сценарии — то есть по причине, не имеющей
    # отношения к тому, что он проверяет. Бесплатной главе три абзаца тоже
    # годятся: у неё (2, 4).
    return json.dumps(
        {
            "title": title,
            "teaser": teaser,
            "advice": "Say the thing sooner.",
            "paragraphs": [
                {"text": "The first paragraph, read from the chart.", "factors": factors[:1]},
                {"text": "The second, from the same place.", "factors": factors[:1]},
                {"text": "The third, still from the chart.", "factors": factors[:1]},
            ],
        }
    )


def _opening_reply(factors, *, title="Life path", teaser="A line.") -> str:
    """Заготовка открывающего абзаца: один абзац, как просит `opening_of`."""
    return json.dumps(
        {
            "title": title,
            "teaser": teaser,
            "paragraphs": [
                {"text": "Forty words about you, read from the chart.",
                 "factors": factors[:1]},
            ],
        }
    )


def _factors_for(api, headers, system="numerology") -> list[str]:
    """The real factors for this birth, taken from the engine.

    Not from the systems endpoint: that strips the factor list for a locked
    system, which is the correct behaviour there and useless here — a test
    that scripts a reply citing an empty list is only testing the validator.
    """
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
    options = (
        {"reference": datetime.now(timezone.utc).date()}
        if system in ("numerology", "birth-card", "synthesis")
        else {}
    )
    return list(compute(system, birth, **options).factors)


# ── the table of contents ──────────────────────────────────────────────────

def test_the_chapter_list_of_a_paid_system_opens_nothing(api, auth_headers):
    """Семь систем из восьми не открывают ни одной главы, и это правило.

    Здесь стояло обратное: у нумерологии открывалась глава I. Владелец,
    17.08.2026: бесплатна ровно одна глава во всём продукте — натал I. Восемь
    первых глав даром — это восемь разных обещаний на восьми экранах, и на
    экране они читались не как щедрость, а как случайность: одна система
    открылась, другая показала стену.

    Закрытая глава при этом не пустая — она отдаёт открывающий абзац; но
    оглавление обязано говорить правду про доступ, иначе клиент нарисует
    бейдж «free» над платным текстом.
    """
    body = api.get("/v1/readings/numerology/chapters", headers=auth_headers).json()
    assert body["total"] == 5
    assert [c["slug"] for c in body["chapters"] if c["open"]] == []
    assert not any(c["free"] for c in body["chapters"])


def test_the_one_free_chapter_in_the_product_is_natal_i(api, auth_headers):
    body = api.get("/v1/readings/natal/chapters", headers=auth_headers).json()
    open_ones = [c for c in body["chapters"] if c["open"]]
    assert [c["slug"] for c in open_ones] == ["core"]
    assert open_ones[0]["free"] is True


def test_an_unknown_system_has_no_chapters(api, auth_headers):
    assert api.get("/v1/readings/palmistry/chapters", headers=auth_headers).status_code == 404


# ── generating ─────────────────────────────────────────────────────────────

def test_a_reading_is_generated_and_cited(api, auth_headers, scripted, owns):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.append(_chapter_reply(factors))

    response = api.post(
        "/v1/readings",
        json={"system": "numerology", "chapter": "life-path"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cached"] is False
    assert body["reading"]["body"]
    assert body["reading"]["cited_factors"]
    assert body["reading"]["read_from"].startswith("Read from:")


def test_a_reading_is_written_once_and_never_changes(api, auth_headers, scripted, owns):
    """A paragraph that landed must still be there tomorrow."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.append(_chapter_reply(factors, title="First writing"))

    first = api.post(
        "/v1/readings", json={"system": "numerology", "chapter": "life-path"},
        headers=auth_headers,
    ).json()
    second = api.post(
        "/v1/readings", json={"system": "numerology", "chapter": "life-path"},
        headers=auth_headers,
    ).json()

    assert first["cached"] is False and second["cached"] is True
    assert second["reading"]["body"] == first["reading"]["body"]
    assert len(scripted.calls) == 1, "the model was called again for a stored reading"


def test_a_locked_chapter_answers_with_its_opening_paragraph(api, auth_headers, scripted):
    """Закрытая глава — это та же глава, дописанная на один абзац.

    Прежде тест держал 402 `locked` и «модель не вызвана вовсе». Первая
    половина ушла, вторая осталась в другом виде — и это ровно то, что
    поменял владелец, увидев чёрную стену: «просят заплатить за заголовок»
    (`locked-chapter-spec.md` §5).

    Что теперь обязано быть правдой: ответ 200 — потому что запрос удался,
    сохранил строку и потратил деньги, а код ошибки на таком запросе врёт;
    `locked` сказано полем; сама глава не отдана (`reading is None`); и над
    размытием стоит **написанный** абзац с позициями (§7). Плюс SKU, которым
    эта система открывается, — чтобы клиент не собирал таблицу цен во второй
    раз.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_opening_reply(_factors_for(api, auth_headers, "natal")))

    response = api.post(
        "/v1/readings", json={"system": "natal", "chapter": "career"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["locked"] is True
    assert body["reading"] is None, "закрытая глава не отдаёт саму главу"
    assert body["product"] == "door.natal"
    assert body["access"]["allowed"] is False
    assert body["opening"]["body"], "стена без написанного абзаца — та же стена"
    assert body["opening"]["cited_factors"], "абзац обязан быть с позициями"
    assert len(scripted.calls) == 1, "сорок слов, а не глава"


def test_the_opening_of_a_locked_chapter_is_written_once_and_for_ever(
    api, auth_headers, scripted
):
    """Второй заход в ту же закрытую главу не стоит ни цента.

    Решение владельца: абзац пишется при первом открытии и кэшируется
    навсегда. Обход всех глав стоит около тридцати центов **один раз за жизнь
    аккаунта**, а не каждый раз, когда человек листает разбор, раздумывая.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_opening_reply(_factors_for(api, auth_headers, "natal")))
    request = {"system": "natal", "chapter": "career"}

    first = api.post("/v1/readings", json=request, headers=auth_headers).json()
    second = api.post("/v1/readings", json=request, headers=auth_headers).json()

    assert first["cached"] is False and second["cached"] is True
    assert second["opening"]["body"] == first["opening"]["body"]
    assert len(scripted.calls) == 1, "второй заход снова заплатил за те же слова"


def test_the_opening_is_asked_for_as_prose_and_not_as_a_description(api, auth_headers, scripted):
    """Приёмка спеки §7, переведённая в проверяемое.

    «На каждой залоченной главе виден **написанный** абзац: не заголовок, не
    „описание системы“, а живой текст с позициями.» Судить прозу тестом
    нельзя — модели здесь всё равно нет, — но можно судить **бриф**, а
    описание системы вместо наблюдения берётся именно из брифа.

    Два отличия от бесплатной главы, и оба обязаны быть в системном промте:
    свой регистр вместо «это бесплатное чтение» (`FREE_TIER` велит быть
    *законченным*, а это — начало главы) и прямой запрет пересказывать, о чём
    глава будет, и продавать словами. Второе не мелочь копирайта: цену на
    экране говорит одна кнопка, и абзац, который делает это ещё раз, — второй
    оффер там, где их должно быть ноль (ТЗ §1, принцип 2).
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_opening_reply(_factors_for(api, auth_headers, "natal")))
    api.post(
        "/v1/readings", json={"system": "natal", "chapter": "career"}, headers=auth_headers
    )

    system_prompt = scripted.calls[0]["system"]
    assert "This is the free reading." not in system_prompt
    assert "opening paragraph of a chapter the reader has not paid for" in system_prompt
    assert "Do not describe what the chapter will cover" in system_prompt
    assert "Do not sell." in system_prompt


def test_a_locked_chapter_never_writes_the_chapter_itself(api, auth_headers, scripted):
    """Стена по-прежнему стоит до полной генерации, и это не смягчилось.

    Между 402 и сегодняшним ответом был режим (`ALMA_PREVIEW_CHAPTERS`), в
    котором первые несколько закрытых глав писались **целиком** и размывались
    на клиенте; владелец отменил его по деньгам — глава сильной моделью за
    $0.02–0.10 для человека, который ещё ничего не решил. Открывающий абзац
    его не возвращает: длина у него своя (`opening_of`), и проверяется это
    здесь тем, что модель просят про один абзац, а не про три.
    """
    from alma.ai import chapters as chapter_defs

    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_opening_reply(_factors_for(api, auth_headers, "natal")))
    api.post(
        "/v1/readings", json={"system": "natal", "chapter": "career"}, headers=auth_headers
    )

    prompt = scripted.calls[0]["prompt"]
    career = chapter_defs.find("natal", "career")
    assert f"{chapter_defs.OPENING_WORDS[0]}–{chapter_defs.OPENING_WORDS[1]} words" in prompt
    assert "in one paragraph" in prompt
    assert f"{career.words[0]}–{career.words[1]} words" not in prompt


def test_a_known_gender_reaches_the_writer_and_stands_down_the_gate(api, auth_headers, scripted):
    """With a volunteered gender the Russian prompt asks for agreement.

    The genderless register was a workaround for not knowing; once the person
    says «женщина», «ты родилась» is correct Russian and the gate that used
    to burn attempts on it stands down. The prompt is the observable: it must
    name the agreement instead of the prohibition.
    """
    api.post("/v1/profiles", json={**SOFIA, "gender": "female"}, headers=auth_headers)
    factors = _factors_for(api, auth_headers, "natal")
    # A Russian body, because the Latin-leak gate reads the prose: an English
    # scripted reply on a ru request is rejected and retried until the script
    # runs dry, which is that gate doing its job on the wrong patient.
    scripted.responses.append(json.dumps({
        "title": "Заголовок",
        "teaser": "Строка.",
        "advice": "Скажи это раньше.",
        "paragraphs": [
            {"text": "Ты родилась с этим небом.", "factors": factors[:1]},
            {"text": "И оно читается отсюда.", "factors": factors[:1]},
        ],
    }))

    response = api.post(
        "/v1/readings",
        json={"system": "natal", "chapter": "core", "locale": "ru"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    prompt = scripted.calls[0]["prompt"]
    assert "женщина" in prompt
    assert "не выдавай пол" not in prompt


def test_the_free_sample_chapter_of_a_paid_system_generates(api, auth_headers, scripted):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers, "natal")
    scripted.responses.append(_chapter_reply(factors))

    response = api.post(
        "/v1/readings", json={"system": "natal", "chapter": "core"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text


def test_an_invented_factor_never_reaches_the_reader(api, auth_headers, scripted, owns):
    """The model tries twice to invent, then gets it right."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.extend(
        [
            _chapter_reply(["a placement this chart does not have"]),
            _chapter_reply(factors),
        ]
    )

    body = api.post(
        "/v1/readings", json={"system": "numerology", "chapter": "life-path"},
        headers=auth_headers,
    ).json()
    assert len(scripted.calls) == 2
    for cited in body["reading"]["cited_factors"]:
        assert cited in factors


def test_a_model_that_only_invents_produces_no_reading(api, auth_headers, scripted, owns):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.extend([_chapter_reply(["not real"]) for _ in range(3)])

    response = api.post(
        "/v1/readings", json={"system": "numerology", "chapter": "life-path"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "reading_refused"


def test_the_wall_still_stands_when_the_model_cannot_be_reached(api, auth_headers):
    """Без ключа абзаца нет, а цена есть.

    Тест назывался «locked outranks an unconfigured api key» и держал 402
    против 503: провайдер строится лениво, чтобы пейволл отвечал раньше, чем
    отсутствие ключа. Правило то же, а форма другая — теперь закрытая глава
    честно ходит к модели за сорока словами, и вопрос становится острее:
    **что увидит человек, когда модель недоступна?**

    Ответ — стену с ценой и без абзаца. 503 на экране, где показывают цену, —
    это не «мы честно сказали о сбое», это ненайденная кнопка «купить» у
    человека, который уже потянулся за кошельком. Абзац — лучшее усилие,
    стена — обязательство.

    Никакого `scripted` здесь нет намеренно: настоящая зависимость, ключа нет.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    response = api.post(
        "/v1/readings", json={"system": "natal", "chapter": "career"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["locked"] is True
    assert body["opening"] is None
    assert body["product"] == "door.natal"


def test_a_missing_api_key_says_so_rather_than_failing_obscurely(api, auth_headers, owns):
    """No provider override here — the real one, with no key configured.

    Про **открытую** главу, и `owns` появился здесь именно поэтому: у закрытой
    недоступная модель гасится в стену (тест выше), а у купленной молчать
    нельзя — человек заплатил и обязан узнать, что сломались мы.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    response = api.post(
        "/v1/readings", json={"system": "numerology", "chapter": "life-path"},
        headers=auth_headers,
    )
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "ai_unavailable"
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]["message"]


def test_a_reading_needs_saved_birth_data(api, auth_headers, scripted, owns):
    response = api.post(
        "/v1/readings", json={"system": "numerology", "chapter": "life-path"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_a_locked_chapter_without_birth_data_still_shows_its_price(api, auth_headers, scripted):
    """Анкеты нет — абзаца нет, стена есть.

    Обратная сторона теста выше. «Сначала сохрани дату рождения» — законный
    400 для главы, которую человек открыл и обязан доделать ввод; на закрытой
    он превращает пейволл в форму, и человек не узнаёт, что глава продаётся.
    """
    response = api.post(
        "/v1/readings", json={"system": "natal", "chapter": "career"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["locked"] is True
    assert response.json()["opening"] is None
    assert scripted.calls == [], "нечего писать — не звали"


def test_an_unknown_chapter_is_a_404(api, auth_headers, scripted):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    response = api.post(
        "/v1/readings", json={"system": "numerology", "chapter": "nonsense"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# ── «в транзитах нет бесплатного» ──────────────────────────────────────────

def _transit_factors() -> list[str]:
    """Факторы того же скана, что просит роут.

    Не `_factors_for(..., "transits")`: тот считает без опций, а роут просит
    год с полуночи (`_options_for`). Разные сканы — разные строки факторов, и
    заготовка, ссылающаяся на чужие, отвергается валидатором как выдумка.
    """
    from alma.ai import chapters as chapter_defs
    from alma.api.routers import readings as route
    from alma.calc import compute

    from tests.test_readings_budget import _birth

    result = compute(
        "transits", _birth(SOFIA), **route._options_for("transits", "placidus")
    )
    return chapter_defs.relevant_factors(
        chapter_defs.find("transits", "active"), result.factors
    )


def test_the_day_text_of_the_today_screen_is_closed_without_a_subscription(
    api, auth_headers, scripted
):
    """Экран «Сегодня» у неподписчика показывает цену, а не текст дня.

    Владелец, 17.08.2026, буквально: «в транзитах нет бесплатного». Дневной
    текст на этом экране — глава `transits/active`, и она же была бесплатной
    утренней заметкой. Отдельной сущности «бесплатная заметка» больше нет:
    транзиты — движок ежедневного гороскопа, то есть ровно то, что продаётся
    подпиской, и глава, переписываемая каждый день и раздаваемая даром, —
    это подписка, за которую забыли взять деньги.

    Цена здесь обязана быть подписочной. `door.transits` не существует и не
    должен: продать «навсегда» то, что переписывается само, значит продать
    подписку и не взять за неё денег.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_opening_reply(_transit_factors()))

    response = api.post(
        "/v1/readings", json={"system": "transits", "chapter": "active"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["locked"] is True
    assert body["reading"] is None, "текст дня — не бесплатный"
    assert body["product"] == "sub.monthly"
    assert body["opening"]["body"], "и всё-таки не молчание"


def test_the_day_text_opens_for_a_subscriber(api, auth_headers, scripted, owns):
    """Обратная сторона: подписчику та же глава приходит целиком.

    Проверяется вместе с закрытой, потому что порознь эти два теста
    доказывают половину: «закрыто у всех» — тоже поломка, и куда более тихая.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_chapter_reply(_transit_factors()))

    response = api.post(
        "/v1/readings", json={"system": "transits", "chapter": "active"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json().get("locked") is not True
    assert response.json()["reading"]["body"]


# ── the conversation ───────────────────────────────────────────────────────

def _chat_reply(factors, *, from_chart=True, remember=None) -> str:
    return json.dumps(
        {
            "answer": [{"text": "Here is what the chart says.", "factors": list(factors)}],
            "answered_from_chart": from_chart,
            "remember": remember or [],
        }
    )


def test_a_chat_turn_answers_and_cites(api, auth_headers, scripted):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.append(_chat_reply(factors[:1]))

    body = api.post(
        "/v1/chat", json={"message": "What should I do about work?"}, headers=auth_headers
    ).json()
    assert body["thread_id"]
    assert body["message"]["role"] == "alma"
    assert body["message"]["cited_factors"] == factors[:1]
    assert body["questions_left"] >= 0


def test_a_conversation_keeps_its_history(api, auth_headers, scripted, monkeypatch):
    # Two question turns on one account; the welcome bundle ships as one, and
    # this test is about history mechanics rather than tiering.
    monkeypatch.setattr(settings(), "free_welcome_bundle", 2)
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.extend([_chat_reply(factors[:1]), _chat_reply(factors[:1])])

    first = api.post("/v1/chat", json={"message": "Tell me about work"}, headers=auth_headers).json()
    api.post(
        "/v1/chat",
        json={"message": "And money?", "thread_id": first["thread_id"]},
        headers=auth_headers,
    )

    thread = api.get(f"/v1/chat/threads/{first['thread_id']}", headers=auth_headers).json()
    assert [m["role"] for m in thread["messages"]] == ["user", "alma", "user", "alma"]
    # The second call must have been given the first exchange.
    assert "Tell me about work" in scripted.calls[1]["prompt"]


def test_alma_may_say_the_chart_is_silent(api, auth_headers, scripted):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_chat_reply([], from_chart=False))

    body = api.post(
        "/v1/chat", json={"message": "What is the capital of Peru?"}, headers=auth_headers
    ).json()
    assert body["message"]["answered_from_chart"] is False
    assert body["message"]["cited_factors"] == []


def test_the_free_question_limit_is_real(api, auth_headers, scripted, monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("ALMA_FREE_QUESTIONS", "2")
    # The welcome bundle answers before the daily counter can refuse, so a test
    # about the counter has to silence it. Through the environment rather than
    # the settings object, because `cache_clear()` below rebuilds that object
    # and would throw away anything patched on it.
    monkeypatch.setenv("ALMA_WELCOME_BUNDLE", "0")
    config_module.settings.cache_clear()
    try:
        api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
        factors = _factors_for(api, auth_headers)
        scripted.responses.extend([_chat_reply(factors[:1]) for _ in range(3)])

        for index in range(2):
            response = api.post(
                "/v1/chat", json={"message": f"question {index}"}, headers=auth_headers
            )
            assert response.status_code == 200

        blocked = api.post("/v1/chat", json={"message": "one more"}, headers=auth_headers)
        assert blocked.status_code == 429
        assert blocked.json()["detail"]["error"] == "question_limit"
        assert blocked.json()["detail"]["allowance"] == 2
    finally:
        config_module.settings.cache_clear()


def test_a_greeting_does_not_spend_the_one_welcome_question(api, auth_headers, scripted):
    """Saying hello is not a question, and it used to cost one anyway.

    Asserted against the *whole* allowance rather than against the other
    greeting. `hello == thanks` passes for any two equal numbers, including two
    turns that both charged — which is exactly what a stale worker was observed
    doing while this test was green (`docs/CONVERSATION.md` §5).
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    # The welcome bundle is the whole free allowance now — one question, on
    # the model that sells, and a greeting must not be the thing that spends it.
    allowance = settings().free_welcome_bundle
    scripted.responses.extend([
        json.dumps({"answer": [{"text": "Hello. What would you like to look at?",
                                "factors": []}],
                    "kind": "aside"}),
        json.dumps({"answer": [{"text": "You're welcome.", "factors": []}], "kind": "aside"}),
        _chat_reply(factors[:1]),
    ])

    hello = api.post("/v1/chat", json={"message": "hi"}, headers=auth_headers).json()
    thanks = api.post("/v1/chat", json={"message": "thanks"}, headers=auth_headers).json()
    assert hello["questions_left"] == allowance, "the first turn was charged"
    assert thanks["questions_left"] == allowance
    assert hello["message"]["kind"] == "aside"

    # And a real question still costs one.
    asked = api.post(
        "/v1/chat", json={"message": "what does my chart say about work?"},
        headers=auth_headers,
    ).json()
    assert asked["questions_left"] == allowance - 1
    assert asked["message"]["kind"] == "reading"


#: The four values the two shipped clients decode, copied from them rather than
#: from us: `ChatTurnKind` in `mobile/flutter/alma/lib/screens/alma/chat_turn.dart`.
#: Раньше здесь стояли два натива; они сняты 17 августа 2026 — продукт
#: собирается только из порта.
#: `care` is in their vocabulary and not in ours on purpose — branch D4 has a
#: rule in the prompt and no copy in any of the six languages, so nothing may
#: emit it until somebody writes that copy.
CLIENT_TURN_KINDS = {"reading", "chart_silent", "conversation", "care"}


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"answer": [{"text": "Hello.", "factors": []}], "kind": "aside"}, "conversation"),
        ({"answer": [{"text": "Not in your chart, but here is what I know.",
                      "factors": []}], "kind": "silent"}, "chart_silent"),
    ],
)
def test_the_wire_field_is_the_one_the_clients_decode(
    api, auth_headers, scripted, payload, expected
):
    """The seam two workflows shipped opposite halves of on the same day.

    The server emitted `kind` with `reading | silent | aside`; both clients
    decode `turn_kind` with `reading | chart_silent | conversation | care` and
    are unit-tested against those strings. So `ChatTurnKind.of()` received null
    on every turn, took the legacy branch, and the honest note under a silent
    turn was unreachable for everybody. Every backend test asserted on the
    `Answer` object and every client test on a hand-written JSON fixture, and
    nothing compared the two — so this asserts the JSON keys and values.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    _factors_for(api, auth_headers)
    scripted.responses.append(json.dumps(payload))

    message = api.post(
        "/v1/chat", json={"message": "hi"}, headers=auth_headers
    ).json()["message"]

    assert "turn_kind" in message, "the clients look for this key and no other"
    assert message["turn_kind"] == expected
    assert message["turn_kind"] in CLIENT_TURN_KINDS


def test_a_reopened_thread_renders_the_way_it_rendered_live(api, auth_headers, scripted):
    """`GET /threads/{id}` returned no kind, so a relaunch lost every label."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.extend([
        json.dumps({"answer": [{"text": "Hello.", "factors": []}], "kind": "aside"}),
        _chat_reply(factors[:1]),
    ])

    live = api.post("/v1/chat", json={"message": "hi"}, headers=auth_headers).json()
    api.post(
        "/v1/chat",
        json={"message": "and my work?", "thread_id": live["thread_id"]},
        headers=auth_headers,
    )

    thread = api.get(f"/v1/chat/threads/{live['thread_id']}", headers=auth_headers).json()
    kinds = [m.get("turn_kind") for m in thread["messages"] if m["role"] == "alma"]
    assert kinds == ["conversation", "reading"]
    assert all(kind in CLIENT_TURN_KINDS for kind in kinds)


def test_the_wall_speaks_the_reader_s_language_and_names_what_is_still_free(
    api, auth_headers, scripted, monkeypatch
):
    """The 429 landed, measured, on "wait what does fixed mean".

    Its body was an untranslated English fragment that named only what was
    being withheld — which reframes the subscription as the price of being
    understood. Every calculation in this product is free; that is the sentence
    the wall should end on.
    """
    monkeypatch.setenv("ALMA_WELCOME_BUNDLE", "0")
    from alma import config as config_module
    from alma.i18n import replies as i18n_replies

    monkeypatch.setenv("ALMA_FREE_QUESTIONS", "1")
    config_module.settings.cache_clear()
    try:
        api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
        factors = _factors_for(api, auth_headers)
        scripted.responses.append(_chat_reply(factors[:1]))
        api.post(
            "/v1/chat", json={"message": "what am i like", "locale": "it"},
            headers=auth_headers,
        )

        blocked = api.post(
            "/v1/chat", json={"message": "che vuol dire fisso?", "locale": "it"},
            headers=auth_headers,
        )
        detail = blocked.json()["detail"]
        assert blocked.status_code == 429 and detail["error"] == "question_limit"
        assert detail["message"] == i18n_replies.LIMIT_DAY["it"].format(limit=1)
        assert "otto i sistemi" in detail["message"]
    finally:
        config_module.settings.cache_clear()


def test_a_message_in_crisis_is_answered_without_the_model_and_kept_in_the_thread(
    api, auth_headers, scripted
):
    """Кризис на проводе: без астрологии, без цитат, без обращения к модели.

    Сценарий провайдера намеренно пуст. Если ход всё-таки пойдёт к модели, он
    упрётся в кончившийся сценарий и тест упадёт — то есть «модель не звали» тут
    проверено тем же способом, что и на уровне модуля.
    """
    from alma.i18n import replies as i18n_replies

    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    body = api.post(
        "/v1/chat",
        json={"message": "я не хочу жить", "locale": "ru"},
        headers=auth_headers,
    )
    assert body.status_code == 200, body.text
    answer = body.json()["message"]
    assert answer["body"] == i18n_replies.CRISIS["ru"]
    assert answer["cited_factors"] == []
    assert answer["turn_kind"] == "conversation", "никакой пометки о карте"
    assert answer["answered_from_chart"] is False
    assert scripted.calls == [], "человека в беде отдали модели"

    # И он остаётся в беседе: перечитанный тред показывает ту же реплику, а не
    # дыру на месте самого важного сообщения в нём.
    thread = api.get(
        f"/v1/chat/threads/{body.json()['thread_id']}", headers=auth_headers
    ).json()
    assert [m["body"] for m in thread["messages"]] == [
        "я не хочу жить", i18n_replies.CRISIS["ru"],
    ]


def test_the_question_wall_never_stands_in_front_of_a_crisis(
    api, auth_headers, scripted, monkeypatch
):
    """Стена ограничивает генерацию, а кризисный ход её не совершает.

    Ответ на такое сообщение — строка из каталога: ноль токенов, ноль центов.
    Показать вместо неё «вопросы на сегодня кончились» значит показать счётчик
    тому, кто написал самое важное, что он тут напишет, — и показать его за
    фразу, которая ничего не стоит.
    """
    monkeypatch.setenv("ALMA_WELCOME_BUNDLE", "0")
    monkeypatch.setenv("ALMA_FREE_QUESTIONS", "1")
    from alma import config as config_module
    from alma.i18n import replies as i18n_replies

    config_module.settings.cache_clear()
    try:
        api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
        factors = _factors_for(api, auth_headers)
        scripted.responses.append(_chat_reply(factors[:1]))
        api.post("/v1/chat", json={"message": "what am i like"}, headers=auth_headers)

        blocked = api.post(
            "/v1/chat", json={"message": "what about work"}, headers=auth_headers
        )
        assert blocked.status_code == 429, "стена на месте для обычного вопроса"

        care = api.post(
            "/v1/chat", json={"message": "i don't want to live anymore"},
            headers=auth_headers,
        )
        assert care.status_code == 200, care.text
        assert care.json()["message"]["body"] == i18n_replies.CRISIS["en"]
    finally:
        config_module.settings.cache_clear()


def test_someone_elses_conversation_is_not_readable(api, auth_headers, scripted):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.append(_chat_reply(factors[:1]))
    mine = api.post("/v1/chat", json={"message": "hello"}, headers=auth_headers).json()

    stranger = {"Authorization": f"Bearer {api.get('/v1/auth/session').json()['token']}"}
    assert api.get(f"/v1/chat/threads/{mine['thread_id']}", headers=stranger).status_code == 404


# ── memory ─────────────────────────────────────────────────────────────────

def test_alma_remembers_what_she_was_told(api, auth_headers, scripted):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.append(
        _chat_reply(factors[:1], remember=["they are deciding whether to leave their job"])
    )

    api.post("/v1/chat", json={"message": "Should I quit?"}, headers=auth_headers)
    memory = api.get("/v1/memory", headers=auth_headers).json()["memory"]
    assert len(memory) == 1
    assert "leave their job" in memory[0]["body"]


def test_memory_is_not_duplicated(api, auth_headers, scripted):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    remembered = ["they are deciding whether to leave their job"]
    scripted.responses.extend(
        [_chat_reply(factors[:1], remember=remembered) for _ in range(2)]
    )

    api.post("/v1/chat", json={"message": "one"}, headers=auth_headers)
    api.post("/v1/chat", json={"message": "two"}, headers=auth_headers)
    assert len(api.get("/v1/memory", headers=auth_headers).json()["memory"]) == 1


def test_memory_reaches_the_next_prompt(api, auth_headers, scripted, monkeypatch):
    monkeypatch.setattr(settings(), "free_welcome_bundle", 2)
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.extend(
        [
            _chat_reply(factors[:1], remember=["they run a small studio"]),
            _chat_reply(factors[:1]),
        ]
    )
    api.post("/v1/chat", json={"message": "one"}, headers=auth_headers)
    api.post("/v1/chat", json={"message": "two"}, headers=auth_headers)
    assert "they run a small studio" in scripted.calls[1]["system"]


def test_memory_can_be_deleted(api, auth_headers, scripted):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses.append(_chat_reply(factors[:1], remember=["something private"]))
    api.post("/v1/chat", json={"message": "one"}, headers=auth_headers)

    entry = api.get("/v1/memory", headers=auth_headers).json()["memory"][0]
    assert api.delete(f"/v1/memory/{entry['id']}", headers=auth_headers).status_code == 204
    assert api.get("/v1/memory", headers=auth_headers).json()["memory"] == []


# ── the second person ──────────────────────────────────────────────────────

def test_a_compatibility_reading_says_who_is_missing_rather_than_failing(
    api, auth_headers, scripted, owns
):
    """It used to be a 500, and always had been.

    `_options_for` fell through to `{"house_system": …}` while
    `compatibility_result` requires `other`, so every request raised
    TypeError — including the sample chapter that exists to sell the report.
    The budget test priced that chapter, which read as coverage of a path that
    never executed.

    Ответ с тех пор поменялся дважды, и второй раз — сегодня. Был 422
    `partner_required`; он приходил, потому что глава I пары была бесплатной и
    доходила до `_partner`. Теперь она закрыта, а безымянная пара упирается в
    `PAIR_WITHOUT_PROFILE` раньше — и это правильнее: 422 на месте пейволла
    означало бы, что человек так и не узнал, что глава продаётся.

    Чего не потерялось: **чего именно не хватает, сказано полем**, а не тоном
    сообщения. `needs_partner` — единственное «закрыто», которое не чинится
    деньгами, и клиент рисует по нему «tap to add someone →» вместо цены.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    response = api.post(
        "/v1/readings",
        json={"system": "compatibility", "chapter": "attraction"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["locked"] is True
    assert body["needs_partner"] is True
    assert body["opening"] is None, "синастрию не из чего построить"
    assert scripted.calls == []


def test_a_pair_chapter_is_locked_like_any_other_and_priced_like_a_pair(
    api, auth_headers, scripted
):
    """Глава I пары («Притяжение») больше не бесплатный тизер.

    Владелец, 17.08.2026: «тизер и глава I пары — одно и то же». Вместе с
    `free=True` снят и весь второй механизм — кап `pair.teaser_cap`, счётчик
    `pair_teaser`, — потому что от чего он защищал, от того теперь защищает
    сама стена. Остаётся обычная закрытая глава: открывающий абзац и цена
    `pair.check`, а не `door.compatibility`, которого не существует.
    """
    from tests.conftest import LUCAS

    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    api.post("/v1/profiles", json={**LUCAS, "relation": "partner"}, headers=auth_headers)
    scripted.responses.append(_opening_reply(_pair_factors("attraction")))

    response = api.post(
        "/v1/readings",
        json={"system": "compatibility", "chapter": "attraction"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["locked"] is True
    assert body["needs_partner"] is False
    assert body["product"] == "pair.check"
    assert body["opening"]["cited_factors"]


def _pair_factors(chapter: str) -> list[str]:
    """Настоящие факторы синастрии Софии и Лукаса для этой главы."""
    from datetime import date

    from alma.ai import chapters as chapter_defs
    from alma.calc import BirthData, compute
    from tests.conftest import LUCAS

    def birth(payload: dict) -> BirthData:
        return BirthData(
            date=date.fromisoformat(payload["birth_date"]),
            time=payload["birth_time"],
            latitude=payload["latitude"],
            longitude=payload["longitude"],
            timezone=payload["timezone"],
            place_label=payload["place_label"],
            name=payload["name"],
        )

    result = compute(
        "compatibility", birth(SOFIA), other=birth(LUCAS), house_system="placidus"
    )
    return chapter_defs.relevant_factors(
        chapter_defs.find("compatibility", chapter), result.factors
    )


def test_a_compatibility_reading_is_written_about_two_people(api, auth_headers, scripted, owns):
    from datetime import date

    from alma.calc import BirthData, compute
    from tests.conftest import LUCAS

    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    partner = api.post(
        "/v1/profiles", json={**LUCAS, "relation": "partner"}, headers=auth_headers
    ).json()

    def _birth(payload: dict) -> BirthData:
        return BirthData(
            date=date.fromisoformat(payload["birth_date"]),
            time=payload["birth_time"],
            latitude=payload["latitude"],
            longitude=payload["longitude"],
            timezone=payload["timezone"],
            place_label=payload["place_label"],
            name=payload["name"],
        )

    from alma.ai import chapters as chapter_defs

    result = compute(
        "compatibility", _birth(SOFIA), other=_birth(LUCAS), house_system="placidus"
    )
    offered = chapter_defs.relevant_factors(
        chapter_defs.find("compatibility", "attraction"), result.factors
    )
    scripted.responses.append(_chapter_reply(offered, title="What pulls"))

    response = api.post(
        "/v1/readings",
        json={
            "system": "compatibility",
            "chapter": "attraction",
            "partner_profile_id": partner["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["reading"]["body"]


def test_a_compatibility_reading_cannot_name_somebody_elses_partner(api, auth_headers, owns):
    from tests.conftest import LUCAS

    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    stranger = api.get("/v1/auth/session").json()
    theirs = api.post(
        "/v1/profiles",
        json=LUCAS,
        headers={"Authorization": f"Bearer {stranger['token']}"},
    ).json()

    response = api.post(
        "/v1/readings",
        json={
            "system": "compatibility",
            "chapter": "attraction",
            "partner_profile_id": theirs["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def _spheres_json(factors):
    import json as _json
    spheres = []
    for key in ("core", "love", "money", "career", "mind"):
        spheres.append({
            "sphere": key,
            "text": f"A plain sentence about {key}. Another one.",
            "factors": [factors[0]],
        })
    return _json.dumps({"spheres": spheres})


def test_the_free_spheres_are_written_once_and_cached(api, auth_headers, scripted):
    """The natal preview: five cited blocks, free, written once per chart.

    The shop window for the sixteen chapters — shaped after the reference the
    owner chose: wheel, placements, then short free interpretations per sphere
    with the full reading behind the price. Cached because the same person
    opening the same chart twice must read the same words and pay us nothing
    twice over.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    # Natal factors, because the route validates citations against the natal
    # chart — a numerology factor would be "invented" here and rightly refused.
    factors = _factors_for(api, auth_headers, system="natal")
    scripted.responses.append(_spheres_json(factors))

    first = api.get("/v1/natal/spheres", headers=auth_headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert [s["sphere"] for s in body["spheres"]] == [
        "core", "love", "money", "career", "mind"
    ]
    # Every block carries its chapter door and a localised title.
    for sphere in body["spheres"]:
        assert sphere["chapter"]
        assert sphere["title"]
        assert sphere["factors"]
    assert body["cached"] is False

    # Second ask: no new generation — the scripted provider has no responses
    # left, so a cache miss would 503 rather than silently pass.
    second = api.get("/v1/natal/spheres", headers=auth_headers)
    assert second.status_code == 200, second.text
    assert second.json()["cached"] is True


def test_two_simultaneous_requests_write_one_chapter_and_charge_once(
    api, auth_headers, scripted
):
    """The race the owner hit on his own first run.

    Today and a fast tap both ask for the same unwritten chapter; both used to
    generate, both were charged, and the second insert died on the UNIQUE
    constraint — a 500 reading "Alma is not answering" over a chapter that had
    just been written. The per-key lock makes the loser wait and wake to a
    cache hit; one generation, one charge, two 200s.
    """
    import anyio

    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers, system="natal")
    # Exactly ONE scripted response: a second generation would die asking for
    # a response the script does not have, which is the assertion.
    scripted.responses.append(_chapter_reply(factors[:1]))

    results = []

    async def ask() -> None:
        async def one(bucket):
            answer = await anyio.to_thread.run_sync(
                lambda: api.post(
                    "/v1/readings",
                    json={"system": "natal", "chapter": "core", "locale": "en"},
                    headers=auth_headers,
                )
            )
            bucket.append(answer)

        async with anyio.create_task_group() as group:
            group.start_soon(one, results)
            group.start_soon(one, results)

    anyio.run(ask)

    codes = sorted(r.status_code for r in results)
    assert codes == [200, 200], [r.text for r in results]
    cached = sorted(r.json()["cached"] for r in results)
    assert cached == [False, True], "one write, one cache hit — never two writes"


def test_glyph_notation_is_refused_in_sphere_prose(api, auth_headers, scripted):
    """The preview is plain words; the notation stays in the factors array.

    Seen live, in Russian: the model pasted «☉ □ ☽» into sentences that the
    brief says are for somebody who has never opened an astrology book. The
    prompt forbids it and the gate enforces it — first reply leaks a glyph and
    is refused, the retry in words is accepted.
    """
    import json as _json

    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers, system="natal")

    leaky = []
    for key in ("core", "love", "money", "career", "mind"):
        leaky.append({
            "sphere": key,
            "text": f"Your ☉ □ ☽ shapes {key}. Another sentence.",
            "factors": [factors[0]],
        })
    scripted.responses.append(_json.dumps({"spheres": leaky}))
    scripted.responses.append(_spheres_json(factors))

    answer = api.get("/v1/natal/spheres", headers=auth_headers)
    assert answer.status_code == 200, answer.text
    for sphere in answer.json()["spheres"]:
        assert "☉" not in sphere["text"] and "□" not in sphere["text"]


def test_sphere_chapters_exist(api, auth_headers):
    """A sphere pointing at a chapter that does not exist is a dead button."""
    from alma.ai import chapters, spheres

    slugs = {c.slug for c in chapters.BY_SYSTEM["natal"]}
    for _key, chapter in spheres.SPHERES:
        assert chapter in slugs
