"""Смена языка переводит написанное, а не пишет заново.

Правило владельца от 28.08.2026: при смене языка приложения уже написанные
тексты — главы, текст дня, сферы, беседа — переводятся дешёвой моделью, а не
перегенерируются. Экономика правила: перегенерация платной главы — 11.19¢ по
замеру (opus), перевод — доли цента (haiku), и слова, за которые человек
заплатил, остаются теми же словами на любом языке.

Каждый тест здесь стережёт одно из обещаний:
- перевод зовёт дешёвую модель с выключенным обдуманием, а не сильную;
- переведённая строка ложится в тот же кеш и второй раз не стоит ничего;
- сорвавшийся перевод падает в обычную генерацию, а не в 503;
- беседа отдаётся целиком на языке запроса, включая вопросы человека,
  и исходные реплики при этом не перезаписываются.
"""

from __future__ import annotations

import json

import pytest

from alma.ai import translator
from alma.ai.provider import ScriptedProvider, THINKING_OFF
from alma.config import settings
from tests.conftest import SOFIA, read_async


@pytest.fixture
def scripted(api):
    """Подменённый провайдер — как в `test_readings_api`, по тесту на раз."""
    from alma.api.deps import get_provider

    provider = ScriptedProvider()
    api.app.dependency_overrides[get_provider] = lambda: (lambda: provider)
    yield provider
    api.app.dependency_overrides.clear()


@pytest.fixture
def owns(monkeypatch):
    from alma.auth import entitlements

    async def yes(session, user, system, *, chapter=None, partner_id=None, at=None):
        return entitlements.Access(True, "bought in the test", kind="one_time")

    monkeypatch.setattr(entitlements, "check", yes)


def _factors_for(api, headers, system="numerology") -> list[str]:
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


def _chapter_reply(factors, *, title="Life path") -> str:
    return json.dumps(
        {
            "title": title,
            "teaser": "A line.",
            "advice": "Say the thing sooner.",
            "paragraphs": [
                {"text": "The first paragraph, read from the chart.", "factors": factors[:1]},
                {"text": "The second, from the same place.", "factors": factors[:1]},
                {"text": "The third, still from the chart.", "factors": factors[:1]},
            ],
        }
    )


def _opening_reply(factors) -> str:
    return json.dumps(
        {
            "title": "Career",
            "teaser": "A line.",
            "paragraphs": [
                {"text": "Forty words about you, read from the chart.",
                 "factors": factors[:1]},
            ],
        }
    )


#: Перевод главы: шесть непустых сегментов — заголовок, тизер, три абзаца,
#: совет. Кириллица целиком: у русской цели переводчик гоняет тот же
#: `russian_latin_leak`, что и писатель, и латинское слово вернуло бы вторую
#: попытку, которой сценарий теста не обещал.
_RU_CHAPTER = json.dumps(
    {
        "segments": [
            "Путь жизни",
            "Одна строка.",
            "Первый абзац, прочитанный из карты.",
            "Второй, из того же места.",
            "Третий, всё ещё из карты.",
            "Скажи это раньше.",
        ]
    },
    ensure_ascii=False,
)


# ── глава ──────────────────────────────────────────────────────────────────

def test_a_language_change_translates_the_chapter_instead_of_rewriting_it(
    api, auth_headers, scripted, owns
):
    """Та же глава на новом языке — дешёвый перевод, а не вторая генерация."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses += [_chapter_reply(factors), _RU_CHAPTER]
    request = {"system": "numerology", "chapter": "life-path"}

    english = api.post(
        "/v1/readings", json=request, headers=auth_headers
    ).json()
    russian = api.post(
        "/v1/readings", json={**request, "locale": "ru"}, headers=auth_headers
    ).json()

    assert english["reading"]["title"] == "Life path"
    assert russian["reading"]["title"] == "Путь жизни"
    assert russian["reading"]["body"][0] == "Первый абзац, прочитанный из карты."
    assert russian["reading"]["advice"] == "Скажи это раньше."
    # Непереводимые поля скопированы, а не потеряны и не переведены.
    assert russian["reading"]["paragraph_factors"] == english["reading"]["paragraph_factors"]
    assert russian["reading"]["cited_factors"] == english["reading"]["cited_factors"]
    assert russian["reading"]["translated_from"] == "en"

    assert len(scripted.calls) == 2
    translation = scripted.calls[1]
    assert translation["model"] == settings().model_cheap, (
        "перевод пошёл не на дешёвую модель — вся экономика правила в ней"
    )
    assert translation["effort"] == THINKING_OFF, "переводу нечего обдумывать"
    assert translation["schema"] == translator.SEGMENTS_SCHEMA


def test_a_translated_chapter_is_cached_like_any_other(
    api, auth_headers, scripted, owns
):
    """Второй заход на новом языке не зовёт модель вовсе."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses += [_chapter_reply(factors), _RU_CHAPTER]
    request = {"system": "numerology", "chapter": "life-path"}

    api.post("/v1/readings", json=request, headers=auth_headers)
    first = api.post(
        "/v1/readings", json={**request, "locale": "ru"}, headers=auth_headers
    ).json()
    second = api.post(
        "/v1/readings", json={**request, "locale": "ru"}, headers=auth_headers
    ).json()

    assert first["cached"] is False and second["cached"] is True
    assert second["reading"]["body"] == first["reading"]["body"]
    assert len(scripted.calls) == 2, "кеш перевода не сработал — модель звали снова"

    async def rows():
        from sqlalchemy import select

        from alma.db.models import Reading
        from alma.db.session import session_scope

        async with session_scope() as session:
            stored = (
                await session.execute(
                    select(Reading).where(Reading.chapter == "life-path")
                )
            ).scalars().all()
            return {(r.locale, r.model) for r in stored}

    stored = read_async(rows)
    assert {locale for locale, _ in stored} == {"en", "ru"}
    assert any(
        model == settings().model_cheap for locale, model in stored if locale == "ru"
    ), "русская строка обязана быть записана переводом, дешёвой моделью"


def test_a_failed_translation_falls_back_to_generation(
    api, auth_headers, scripted, owns
):
    """Сорвавшийся перевод — причина сгенерировать, а не причина отказать.

    Сценарий: обе попытки перевода возвращают не то число сегментов, после
    чего запрос уходит в обычную генерацию и глава всё равно приезжает.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    broken = json.dumps({"segments": ["одна строка вместо шести"]}, ensure_ascii=False)
    russian_written = json.dumps(
        {
            "title": "Путь жизни",
            "teaser": "Одна строка.",
            "advice": "Скажи это раньше.",
            "paragraphs": [
                {"text": "Первый абзац, прочитанный из карты.", "factors": factors[:1]},
                {"text": "Второй, из того же места.", "factors": factors[:1]},
                {"text": "Третий, всё ещё из карты.", "factors": factors[:1]},
            ],
        },
        ensure_ascii=False,
    )
    scripted.responses += [
        _chapter_reply(factors), broken, broken, russian_written,
    ]
    request = {"system": "numerology", "chapter": "life-path"}

    api.post("/v1/readings", json=request, headers=auth_headers)
    response = api.post(
        "/v1/readings", json={**request, "locale": "ru"}, headers=auth_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()["reading"]
    assert body["title"] == "Путь жизни"
    assert "translated_from" not in body, "это генерация, а не перевод"
    assert len(scripted.calls) == 4, (
        "ожидались: генерация en, две попытки перевода, генерация ru"
    )
    assert scripted.calls[3]["model"] != settings().model_cheap


# ── открывающий абзац закрытой главы ───────────────────────────────────────

def test_the_opening_of_a_locked_chapter_translates_too(api, auth_headers, scripted):
    """Витрина при смене языка тоже переводится, а не пишется заново."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses += [
        _opening_reply(_factors_for(api, auth_headers, "natal")),
        json.dumps(
            {
                "segments": [
                    "Карьера",
                    "Одна строка.",
                    "Сорок слов о тебе, прочитанных из карты.",
                ]
            },
            ensure_ascii=False,
        ),
    ]
    request = {"system": "natal", "chapter": "career"}

    english = api.post("/v1/readings", json=request, headers=auth_headers).json()
    russian = api.post(
        "/v1/readings", json={**request, "locale": "ru"}, headers=auth_headers
    ).json()
    again = api.post(
        "/v1/readings", json={**request, "locale": "ru"}, headers=auth_headers
    ).json()

    assert english["locked"] and russian["locked"]
    assert russian["opening"]["body"] == ["Сорок слов о тебе, прочитанных из карты."]
    assert russian["opening"]["translated_from"] == "en"
    assert again["cached"] is True
    assert len(scripted.calls) == 2, "перевод абзаца обязан лечь в кеш навсегда"
    assert scripted.calls[1]["model"] == settings().model_cheap


# ── беседа ─────────────────────────────────────────────────────────────────

def _seed_thread(api, auth_headers) -> str:
    """Беседа в базе, минуя квоты чата: тест про перевод, а не про порции."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)

    async def work():
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import select

        from alma.db.models import ChatMessage, ChatThread, User
        from alma.db.session import session_scope

        # Времена явные: порядок реплик в отдаче — `order_by(created_at)`, и
        # две строки, вставленные в одну микросекунду, перепутали бы вопрос с
        # ответом ровно в той паре, на которой тест сверяет перевод.
        wrote = datetime.now(timezone.utc)
        async with session_scope() as session:
            user = (await session.execute(select(User))).scalars().one()
            thread = ChatThread(user_id=user.id, title="Что меня ждёт весной")
            session.add(thread)
            await session.flush()
            session.add(
                ChatMessage(
                    thread_id=thread.id, role="user",
                    body="Что меня ждёт весной?", locale="ru",
                    created_at=wrote,
                )
            )
            session.add(
                ChatMessage(
                    thread_id=thread.id, role="alma",
                    body="Весна принесёт ясность.", locale="ru",
                    created_at=wrote + timedelta(seconds=1),
                )
            )
            return thread.id

    return read_async(work)


def test_a_thread_is_served_in_the_language_of_the_app(api, auth_headers, scripted):
    """Беседа целиком на языке запроса — включая собственные вопросы человека.

    И с вечным кешем: второй заход на том же языке не зовёт модель. Исходные
    реплики не перезаписываются — без `locale` в запросе тред отдаётся как
    был записан.
    """
    thread_id = _seed_thread(api, auth_headers)
    scripted.responses += [
        # Свежие реплики переводятся первыми (бюджет времени может не дать
        # перевести всё), поэтому в пачке ответ Alma стоит раньше вопроса.
        json.dumps(
            {"segments": ["Spring brings clarity.", "What awaits me in spring?"]}
        ),
        json.dumps({"segments": ["What awaits me in spring"]}),
    ]

    english = api.get(
        f"/v1/chat/threads/{thread_id}?locale=en", headers=auth_headers
    ).json()
    assert [m["body"] for m in english["messages"]] == [
        "What awaits me in spring?",
        "Spring brings clarity.",
    ]
    assert english["title"] == "What awaits me in spring"
    assert len(scripted.calls) == 2, "реплики одним вызовом, заголовок вторым"

    again = api.get(
        f"/v1/chat/threads/{thread_id}?locale=en", headers=auth_headers
    ).json()
    assert [m["body"] for m in again["messages"]] == [
        "What awaits me in spring?",
        "Spring brings clarity.",
    ]
    assert len(scripted.calls) == 2, "перевод беседы обязан лечь в кеш навсегда"

    plain = api.get(f"/v1/chat/threads/{thread_id}", headers=auth_headers).json()
    assert [m["body"] for m in plain["messages"]] == [
        "Что меня ждёт весной?",
        "Весна принесёт ясность.",
    ], "исходные реплики — запись разговора, перевод их не трогает"


def test_the_thread_list_translates_titles_once(api, auth_headers, scripted):
    """Список бесед читается на языке приложения, и тоже по кешу."""
    _seed_thread(api, auth_headers)
    scripted.responses.append(
        json.dumps({"segments": ["What awaits me in spring"]})
    )

    first = api.get("/v1/chat/threads?locale=en", headers=auth_headers).json()
    second = api.get("/v1/chat/threads?locale=en", headers=auth_headers).json()

    assert first["threads"][0]["title"] == "What awaits me in spring"
    assert second["threads"][0]["title"] == "What awaits me in spring"
    assert len(scripted.calls) == 1, "заголовок переводится один раз на язык"


def test_messages_without_a_locale_still_translate(api, auth_headers, scripted):
    """Null-локаль старых реплик — не причина оставить их на старом языке.

    Колонка `ChatMessage.locale` появилась 28.08.2026; у всего, что написано
    раньше, языка нет, и восстановить его нельзя. Такая реплика переводится
    наравне с чужой: модель, которой велено вернуть уже-целевой текст без
    изменений, делает ровно это, и ответ ложится в кеш навсегда.
    """
    thread_id = _seed_thread(api, auth_headers)

    async def strip():
        from sqlalchemy import update

        from alma.db.models import ChatMessage
        from alma.db.session import session_scope

        async with session_scope() as session:
            await session.execute(
                update(ChatMessage)
                .where(ChatMessage.thread_id == thread_id)
                .values(locale=None)
            )

    read_async(strip)
    scripted.responses += [
        json.dumps(
            {"segments": ["Spring brings clarity.", "What awaits me in spring?"]}
        ),
        json.dumps({"segments": ["What awaits me in spring"]}),
    ]

    english = api.get(
        f"/v1/chat/threads/{thread_id}?locale=en", headers=auth_headers
    ).json()
    assert [m["body"] for m in english["messages"]] == [
        "What awaits me in spring?",
        "Spring brings clarity.",
    ]


def test_the_source_is_the_original_not_an_earlier_translation(
    api, auth_headers, scripted, owns
):
    """Перевод с перевода запрещён, пока жив оригинал.

    Свежая строка той же главы может сама быть haiku-переводом; брать её
    исходником значило бы копить дрейф, пока оплаченный сильной моделью
    оригинал лежит строкой ниже.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers)
    scripted.responses += [
        _chapter_reply(factors),
        _RU_CHAPTER,
        json.dumps({"segments": ["T", "Z", "E", "Zw", "D", "S"]}),
    ]
    request = {"system": "numerology", "chapter": "life-path"}

    api.post("/v1/readings", json=request, headers=auth_headers)
    api.post(
        "/v1/readings", json={**request, "locale": "ru"}, headers=auth_headers
    )
    api.post(
        "/v1/readings", json={**request, "locale": "de"}, headers=auth_headers
    )

    assert len(scripted.calls) == 3
    german = scripted.calls[2]["prompt"]
    assert "The first paragraph, read from the chart." in german, (
        "немецкий обязан переводиться с английского оригинала"
    )
    assert "Первый абзац" not in german, (
        "русская строка — сама перевод, исходником быть не может"
    )


def test_chat_translation_pays_the_showcase_ledger_not_the_reading_one(
    api, auth_headers, scripted
):
    """Чтение собственного архива не съедает бюджет настоящих вопросов.

    Тот же довод, которым открывающий абзац переехал в `SHOWCASE_METRIC`:
    витрина в $1.28 съедала месяц бесплатного тира в $1.10 целиком.
    """
    thread_id = _seed_thread(api, auth_headers)
    scripted.responses += [
        json.dumps(
            {"segments": ["Spring brings clarity.", "What awaits me in spring?"]}
        ),
        json.dumps({"segments": ["What awaits me in spring"]}),
    ]

    api.get(f"/v1/chat/threads/{thread_id}?locale=en", headers=auth_headers)

    async def ledgers():
        from sqlalchemy import select

        from alma.ai import cost
        from alma.db.models import User
        from alma.db.session import session_scope

        async with session_scope() as session:
            user = (await session.execute(select(User))).scalars().one()
            return (
                await cost.month_spend(session, user),
                await cost.month_showcase_spend(session, user),
            )

    reading_spend, showcase_spend = read_async(ledgers)
    assert showcase_spend > 0, "перевод беседы обязан быть записан в показ"
    assert reading_spend == 0, (
        "статья чтения — для глав и вопросов, архив её не трогает"
    )


def test_a_spent_time_budget_serves_the_rest_as_written(
    api, auth_headers, scripted, monkeypatch
):
    """Клиент ждёт ответа 30 секунд — бюджет обязан вернуть его раньше.

    С нулевым бюджетом не переводится ничего, но беседа читается: реплики
    уезжают как записаны, заголовок (вне бюджета, он короткий) — переводом.
    """
    from alma.api.routers import readings as route

    thread_id = _seed_thread(api, auth_headers)
    monkeypatch.setattr(route, "CHAT_TRANSLATION_BUDGET_SECONDS", -1.0)
    scripted.responses.append(json.dumps({"segments": ["What awaits me in spring"]}))

    english = api.get(
        f"/v1/chat/threads/{thread_id}?locale=en", headers=auth_headers
    ).json()

    assert [m["body"] for m in english["messages"]] == [
        "Что меня ждёт весной?",
        "Весна принесёт ясность.",
    ], "бюджет истрачен — реплики уезжают как записаны, а не 503"
    assert len(scripted.calls) == 1, "в бюджет не влезла ни одна пачка реплик"


def test_the_newest_messages_translate_first(
    api, auth_headers, scripted, monkeypatch
):
    """Когда на всё не хватает, переводится то, к чему экран прокручен.

    Пачки по одной реплике (потолок в один знак), провайдер отвечает один раз
    и замолкает: перевод достаётся свежему ответу Alma, старый вопрос ждёт
    следующего открытия.
    """
    from alma.ai import translator
    from alma.ai.provider import ModelUnavailable

    thread_id = _seed_thread(api, auth_headers)
    monkeypatch.setattr(
        "alma.api.routers.readings.CHAT_BATCH_CHARS", 1
    )
    scripted.responses += [
        json.dumps({"segments": ["Spring brings clarity."]}),
        ModelUnavailable("the stand went quiet"),
        json.dumps({"segments": ["What awaits me in spring"]}),
    ]

    english = api.get(
        f"/v1/chat/threads/{thread_id}?locale=en", headers=auth_headers
    ).json()

    assert [m["body"] for m in english["messages"]] == [
        "Что меня ждёт весной?",
        "Spring brings clarity.",
    ], "свежая реплика переведена, старая честно ждёт"


def test_a_deterministic_refusal_is_paid_for_exactly_once(
    api, auth_headers, scripted
):
    """Отказ перевода кешируется исходником, а не оплачивается на каждом
    открытии: та же пачка даёт тот же отказ, и без записи каждый показ треда
    жёг бы две настоящие попытки вечно."""
    thread_id = _seed_thread(api, auth_headers)
    broken = json.dumps({"segments": ["одна строка вместо двух"]}, ensure_ascii=False)
    scripted.responses += [
        broken, broken,
        json.dumps({"segments": ["What awaits me in spring"]}),
    ]

    first = api.get(
        f"/v1/chat/threads/{thread_id}?locale=en", headers=auth_headers
    ).json()
    assert [m["body"] for m in first["messages"]] == [
        "Что меня ждёт весной?",
        "Весна принесёт ясность.",
    ], "отказ — реплики как записаны"
    spent = len(scripted.calls)

    second = api.get(
        f"/v1/chat/threads/{thread_id}?locale=en", headers=auth_headers
    ).json()
    assert len(scripted.calls) == spent, (
        "второе открытие не платит за тот же отказ"
    )
    assert [m["body"] for m in second["messages"]] == [
        "Что меня ждёт весной?",
        "Весна принесёт ясность.",
    ]


# ── сам переводчик ─────────────────────────────────────────────────────────

def test_the_segments_schema_forbids_extra_properties():
    """Контракт API структурного вывода, поймано на проде 28.08.2026.

    Без `additionalProperties: false` каждый вызов перевода отвечал 400
    «'additionalProperties' must be explicitly set to false» и весь модуль
    тихо падал в дорогую генерацию — деградация скрывала поломку. Скриптовый
    провайдер схему не читает, поэтому число закреплено буквально, как у
    прочих схем проекта (`writer.CHAPTER_SCHEMA`, `spheres`, `conversation`).
    """
    assert translator.SEGMENTS_SCHEMA["additionalProperties"] is False


def test_the_bill_is_priced_by_the_requested_model_not_the_api_echo():
    """Счёт — по запрошенному имени модели, не по эху API.

    API отвечает версионным «claude-haiku-4-5-20251001», которого нет в
    `PRICES`, и цена уезжала на запасную — вдесятеро дороже. Первый живой
    перевод на проде (28.08.2026) записался 4.8¢ вместо ~0.5¢: переводы
    съедали бы месячные потолки за чтение, которого не было.
    """
    import asyncio

    from alma.ai.provider import Completion

    class Echoing:
        async def complete(self, **kwargs):
            return Completion(
                text=json.dumps({"segments": ["Один."]}, ensure_ascii=False),
                model="claude-haiku-4-5-20251001",
                input_tokens=1000,
                output_tokens=1000,
            )

    done = asyncio.run(
        translator.translate(
            ["One."],
            provider=Echoing(),
            model="claude-haiku-4-5",
            source_locale="en",
            target_locale="ru",
            paid=False,
            prose=True,
        )
    )
    assert done.model == "claude-haiku-4-5", (
        "строка reading несёт алиас, по нему же ищут запросы замера"
    )
    # Тысяча токенов входа и выхода по прайсу haiku: (1.00 + 5.00)/1000 = $0.006.
    assert abs(done.spend.dollars - 0.006) < 1e-9, (
        f"счёт ушёл не по haiku-прайсу: ${done.spend.dollars:.4f}"
    )


def test_reading_pieces_rebuilds_everything_but_the_prose():
    """Разборка-сборка не трогает поля, которые по контракту не переводятся."""
    body = {
        "title": "Life path",
        "teaser": "A line.",
        "body": ["One.", "Two."],
        "paragraph_factors": [["life_path_7"], ["life_path_7"]],
        "advice": "Do it.",
        "areas": [{"area": "work", "line": "Quiet day."}],
        "cited_factors": ["life_path_7"],
        "read_from": "Read from: life_path_7",
        "model": "claude-opus-5",
        "attempts": 1,
        "warnings": [],
    }
    segments, rebuild = translator.reading_pieces(body)
    assert segments == [
        "Life path", "A line.", "One.", "Two.", "Do it.", "Quiet day.",
    ]
    out = rebuild(["Т", "С", "Один.", "Два.", "Сделай.", "Тихий день."])
    assert out["body"] == ["Один.", "Два."]
    assert out["areas"] == [{"area": "work", "line": "Тихий день."}]
    assert out["paragraph_factors"] == body["paragraph_factors"]
    assert out["cited_factors"] == body["cited_factors"]
    assert out["read_from"] == body["read_from"]


def test_a_wrong_segment_count_earns_exactly_one_more_attempt():
    """Перевод, не совпавший с исходником, получает одну жалобу — не цикл."""
    import asyncio

    provider = ScriptedProvider()
    provider.responses += [
        json.dumps({"segments": ["only one"]}),
        json.dumps({"segments": ["One.", "Two."]}),
    ]

    done = asyncio.run(
        translator.translate(
            ["Один.", "Два."],
            provider=provider,
            model="claude-haiku-4-5",
            source_locale="ru",
            target_locale="en",
            paid=False,
        )
    )
    assert done.segments == ("One.", "Two.")
    assert len(provider.calls) == 2
    assert "rejected" in provider.calls[1]["prompt"]


def test_two_wrong_answers_refuse_with_the_spend_attached():
    import asyncio

    provider = ScriptedProvider()
    provider.responses += [
        json.dumps({"segments": ["only one"]}),
        json.dumps({"segments": ["still one"]}),
    ]

    with pytest.raises(translator.TranslationRefused) as caught:
        asyncio.run(
            translator.translate(
                ["Один.", "Два."],
                provider=provider,
                model="claude-haiku-4-5",
                source_locale="ru",
                target_locale="en",
                paid=False,
            )
        )
    assert caught.value.spend.input_tokens > 0, (
        "обе попытки — настоящие вызовы, и их счёт обязан ехать наверх"
    )


def test_russian_output_with_latin_words_is_sent_back():
    """«Твой natal Уран» — та же протечка, что у писателя, и та же сетка."""
    import asyncio

    provider = ScriptedProvider()
    provider.responses += [
        json.dumps({"segments": ["Твой natal Уран говорит о многом."]}, ensure_ascii=False),
        json.dumps({"segments": ["Твой натальный Уран говорит о многом."]}, ensure_ascii=False),
    ]

    done = asyncio.run(
        translator.translate(
            ["Your natal Uranus says a lot."],
            provider=provider,
            model="claude-haiku-4-5",
            source_locale="en",
            target_locale="ru",
            paid=False,
            prose=True,
        )
    )
    assert done.segments == ("Твой натальный Уран говорит о многом.",)
    assert len(provider.calls) == 2


def test_the_romanised_name_from_the_factors_is_lawful_latin():
    """Глава имени цитирует «ANATOLIY MIKHAYLOV» — и обязана продолжать.

    Тот же список разрешённых, что у писателя (`russian_latin_leak` + факторы):
    без него верный перевод главы имени отвергался бы детерминированно, и
    либо имя транслитерировалось (читателю нечем проверить сумму), либо
    перевод падал в дорогую перегенерацию — на каждом, у кого эта глава есть.
    """
    import asyncio

    provider = ScriptedProvider()
    provider.responses.append(
        json.dumps(
            {"segments": ["Твоё имя посчитано как ANATOLIY MIKHAYLOV."]},
            ensure_ascii=False,
        )
    )

    done = asyncio.run(
        translator.translate(
            ["Your name counted as ANATOLIY MIKHAYLOV."],
            provider=provider,
            model="claude-haiku-4-5",
            source_locale="en",
            target_locale="ru",
            paid=False,
            factors=("name counted as ANATOLIY MIKHAYLOV",),
            prose=True,
        )
    )
    assert done.segments == ("Твоё имя посчитано как ANATOLIY MIKHAYLOV.",)
    assert len(provider.calls) == 1, "цитата из фактора — не протечка"


def test_gendered_russian_for_an_unknown_reader_is_sent_back():
    """Английский исходник безродовой — перевод обязан таким и остаться.

    «Ты родился» женщине — первая строка самого личного текста продукта,
    сообщающая, что Alma решила за неё; у писателя это ловит
    `russian_gendered`, и переводчик держит ту же сетку.
    """
    import asyncio

    provider = ScriptedProvider()
    provider.responses += [
        json.dumps({"segments": ["Ты родился под ясным небом."]}, ensure_ascii=False),
        json.dumps({"segments": ["Ты приходишь в мир под ясным небом."]}, ensure_ascii=False),
    ]

    done = asyncio.run(
        translator.translate(
            ["You were born under a clear sky."],
            provider=provider,
            model="claude-haiku-4-5",
            source_locale="en",
            target_locale="ru",
            paid=False,
            prose=True,
        )
    )
    assert done.segments == ("Ты приходишь в мир под ясным небом.",)
    assert len(provider.calls) == 2
    assert "gender" in provider.calls[1]["prompt"], (
        "жалоба обязана назвать род, а не пересказать общее недовольство"
    )


def test_a_known_reader_gender_rides_in_the_prompt_and_is_allowed():
    """Род известен — грамматика идёт за ним, сетка безродовости молчит."""
    import asyncio

    provider = ScriptedProvider()
    provider.responses.append(
        json.dumps({"segments": ["Ты родилась под ясным небом."]}, ensure_ascii=False)
    )

    done = asyncio.run(
        translator.translate(
            ["You were born under a clear sky."],
            provider=provider,
            model="claude-haiku-4-5",
            source_locale="en",
            target_locale="ru",
            paid=False,
            reader_gender="female",
            prose=True,
        )
    )
    assert done.segments == ("Ты родилась под ясным небом.",)
    assert len(provider.calls) == 1
    assert "woman" in provider.calls[0]["system"], (
        "род читателя обязан уехать подсказкой в промпт"
    )


def test_every_target_language_names_its_register_in_the_prompt():
    """Продукт целиком на «ты», и перевод — тоже продукт.

    Без явного регистра модель выбирает вежливую форму: первый живой
    французский перевод на проде пришёл на «vous» при 102 строках «tu» в
    интерфейсе. Русский и испанский едут из `voice.LOCALE_NAMES`; четыре
    остальных закреплены здесь.
    """
    import asyncio

    expectations = {
        "fr": "never « vous »",
        "de": "never «Sie»",
        "it": "never «Lei»",
        "pt-BR": "«você»",
        "ru": "never Вы",
        "es": "never vos",
    }
    for target, marker in expectations.items():
        provider = ScriptedProvider()
        provider.responses.append(json.dumps({"segments": ["x"]}))
        asyncio.run(
            translator.translate(
                ["One."],
                provider=provider,
                model="claude-haiku-4-5",
                source_locale="en",
                target_locale=target,
                paid=False,
            )
        )
        assert marker in provider.calls[0]["system"], (
            f"{target}: регистр обязан быть назван в промпте"
        )


def test_a_banned_word_introduced_by_translation_is_sent_back():
    """«Core» первым живым французским переводом стал «Essence» — словом из
    запретного списка, которое писателю не сошло бы с рук. Перевод держит тот
    же словарь, что и генерация."""
    import asyncio

    provider = ScriptedProvider()
    provider.responses += [
        json.dumps({"segments": ["Твоё ядро сияет ровно."]}, ensure_ascii=False),
        json.dumps({"segments": ["Твоя основа держит ровно."]}, ensure_ascii=False),
    ]

    done = asyncio.run(
        translator.translate(
            ["Your core holds steady."],
            provider=provider,
            model="claude-haiku-4-5",
            source_locale="en",
            target_locale="ru",
            paid=False,
            prose=True,
        )
    )
    assert done.segments == ("Твоя основа держит ровно.",)
    assert len(provider.calls) == 2
    assert "banned" in provider.calls[1]["prompt"]


def test_conversation_is_not_judged_by_the_rules_of_prose():
    """Беседа — собственные слова человека: «я родилась», «мой iPhone».

    Сетки прозы (латиница, род) к ней не применяются — иначе верный перевод
    отвергался бы за то, что человек написал о себе в своём роде и назвал
    телефон телефоном.
    """
    import asyncio

    provider = ScriptedProvider()
    provider.responses.append(
        json.dumps(
            {"segments": ["Я родилась в мае, и мой iPhone это знает."]},
            ensure_ascii=False,
        )
    )

    done = asyncio.run(
        translator.translate(
            ["I was born in May and my iPhone knows it."],
            provider=provider,
            model="claude-haiku-4-5",
            source_locale=None,
            target_locale="ru",
            paid=False,
        )
    )
    assert done.segments == ("Я родилась в мае, и мой iPhone это знает.",)
    assert len(provider.calls) == 1


def test_empty_segments_do_not_travel_to_the_model():
    """Пустой совет остаётся пустым — модели не из чего его переводить."""
    import asyncio

    provider = ScriptedProvider()
    provider.responses.append(json.dumps({"segments": ["Один."]}))

    done = asyncio.run(
        translator.translate(
            ["One.", "", "   "],
            provider=provider,
            model="claude-haiku-4-5",
            source_locale="en",
            target_locale="ru",
            paid=False,
        )
    )
    assert done.segments == ("Один.", "", "   ")
    prompt = provider.calls[0]["prompt"]
    assert "One." in prompt and json.loads(prompt)["segments"] == ["One."]
