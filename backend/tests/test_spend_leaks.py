"""Четыре пути, по которым состоявшаяся генерация уходила мимо счёта.

Общее у них одно: модель позвали, токены произвели, счёт нам выставили — а в
`usage_counter` не появилось ничего. Такой расход невидим для месячного
потолка, то есть потолка на нём нет вовсе: он ограничивает не деньги, а пользу
от них. Каждый тест здесь описывает *деньги*, а не код, и каждый падал на том
коде, что был до правки:

* обрыв по `max_tokens` поднимался раньше, чем считались токены вызова, а на
  третьей попытке уносил с собой весь прогон — 503 без единой записи;
* `/v1/chat/stream` отменял свою задачу, когда читатель уходил, и откат уносил
  оплаченную генерацию вместе с вопросом из квоты;
* `GET /v1/natal/spheres` — единственная генерация продукта, которая никогда не
  спрашивала месячный потолок;
* два одновременных сообщения читали один и тот же ноль в счётчике вопросов и
  в леджере, и оба проходили обе стены.

Замеры цен здесь в токенах и центах намеренно: «расход записан» проверяется
числом, а не тем, что где-то появилась строка.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date

import pytest
from conftest import SOFIA, database_url, read_async, run_async
from sqlalchemy import select

from alma.ai import chapters, conversation, cost, writer
from alma.ai.provider import AnswerTruncated, Completion, ScriptedProvider
from alma.api.routers import readings as route
from alma.api.schemas import ChatRequest
from alma.auth import accounts
from alma.calc import BirthData, compute
from alma.config import settings
from alma.db import session as session_module
from alma.db.models import ChatMessage, Profile, UsageCounter, User
from tests.test_readings_api import (  # noqa: F401 — фикстуры регистрируются импортом
    _chapter_reply,
    _chat_reply,
    _factors_for,
    scripted,
)

BIRTH = BirthData(
    date=date.fromisoformat(SOFIA["birth_date"]),
    time=SOFIA["birth_time"],
    latitude=SOFIA["latitude"],
    longitude=SOFIA["longitude"],
    timezone=SOFIA["timezone"],
    place_label=SOFIA["place_label"],
    name=SOFIA["name"],
)


@pytest.fixture(scope="module")
def natal():
    return compute("natal", BIRTH)


def _reply(paragraphs) -> str:
    return json.dumps(
        {
            "title": "Core",
            "teaser": "A teaser.",
            "advice": "",
            "paragraphs": [
                {"text": text, "factors": list(factors)} for text, factors in paragraphs
            ],
        }
    )


def _cut_off(*, wrote_nothing: bool = False) -> AnswerTruncated:
    """Обрыв по `max_tokens` — такой, каким его отдаёт настоящий провайдер.

    Со счётчиками внутри: вызов, упёршийся в потолок, оплачен ровно так же, как
    удачный, и вся эта папка про то, что эти два числа обязаны дожить до
    леджера. Заготовка, потому что четыре теста ниже описывают один и тот же
    вызов и не должны расходиться в его цене.
    """
    return AnswerTruncated(
        "claude-sonnet-5 reached max_tokens=1560 and the answer was cut off",
        wrote_nothing=wrote_nothing,
        completion=Completion(
            text="" if wrote_nothing else "Half a sentence, and then the wall",
            model="claude-sonnet-5",
            input_tokens=1200,
            output_tokens=400,
            stop_reason="max_tokens",
        ),
    )


def _spheres_reply(factors) -> str:
    """Одна годная генерация превью: пять блоков, каждый со своей цитатой."""
    return json.dumps(
        {
            "spheres": [
                {
                    "sphere": key,
                    "text": f"A plain sentence about {key}. Another one.",
                    "factors": [factors[0]],
                }
                for key in ("core", "love", "money", "career", "mind")
            ]
        }
    )


def _month_spend(user_id: str) -> float:
    """Сколько этот аккаунт стоил нам в этом месяце — из того же места, что и потолок."""
    from alma.db import get_session

    async def read_back() -> float:
        async for session in get_session():
            return await cost.month_spend(session, await session.get(User, user_id))
        return 0.0

    return read_async(read_back)


# ── 1 · обрезанная генерация ───────────────────────────────────────────────


async def test_a_truncated_attempt_is_paid_for_like_any_other(natal):
    """Попытка, упёршаяся в потолок, стоит столько же, сколько удачная.

    `tally.record` стоял *после* `except AnswerTruncated`, и это была
    единственная ветка, по которой настоящий вызов модели проходил мимо счёта.
    Обрыв — не «вызова не было»: модель подумала, произвела токены, счёт
    выставлен. Здесь глава дописывается со второй попытки, и её цена обязана
    быть ценой двух вызовов, а не одного.
    """
    chapter = chapters.find("natal", "core")
    offered = chapters.relevant_factors(chapter, natal.factors)
    provider = ScriptedProvider(
        responses=[
            _cut_off(),
            _reply([("Fine.", offered[:1]), ("Also.", offered[:1])]),
        ]
    )

    written = await writer.write(
        result=natal, chapter=chapter, provider=provider, model="claude-opus-5"
    )

    assert written.attempts == 2
    assert written.spend.output_tokens == 400 + provider.output_tokens, (
        "оборванная попытка выпала из счёта — глава стоила два вызова, "
        f"а записан один: {written.spend.as_dict()}"
    )
    assert written.spend.input_tokens == 1200 + provider.input_tokens
    assert written.spend.dollars == pytest.approx(
        cost.cost("claude-opus-5", 2400, 800).dollars
    )


async def test_a_chapter_truncated_every_time_carries_what_it_cost(natal):
    """Три обрыва — три оплаченные генерации, и они уезжают вместе с отказом.

    Самый дорогой исход был единственным, который стоил аккаунту ноль: цикл
    поднимал `AnswerTruncated` голым, роутер видел в нём обычный
    `ModelUnavailable`, отвечал 503 мимо `_charge_anyway`, и откат сессии
    довершал дело. Русская глава на сильной модели — около $0.6 в никуда, и
    месячный потолок не сдвигался ни на цент, так что «повторить» можно было
    жать бесконечно.
    """
    chapter = chapters.find("natal", "core")
    provider = ScriptedProvider(
        responses=[_cut_off() for _ in range(writer.MAX_ATTEMPTS)]
    )

    with pytest.raises(AnswerTruncated) as caught:
        await writer.write(
            result=natal, chapter=chapter, provider=provider, model="claude-opus-5"
        )

    assert len(provider.calls) == writer.MAX_ATTEMPTS
    spend = getattr(caught.value, "spend", None)
    assert spend is not None, "отказ ушёл наружу без цены прогона"
    assert spend.output_tokens == 400 * writer.MAX_ATTEMPTS
    assert spend.cents > 0


async def test_a_chat_turn_truncated_every_time_carries_what_it_cost(natal):
    """То же самое на пути беседы: три попытки, и все три оплачены."""
    provider = ScriptedProvider(
        responses=[_cut_off() for _ in range(conversation.MAX_ATTEMPTS)]
    )

    with pytest.raises(AnswerTruncated) as caught:
        await conversation.answer(
            question="Tell me everything.",
            results=[natal],
            provider=provider,
            model="claude-haiku-4-5",
        )

    spend = getattr(caught.value, "spend", None)
    assert spend is not None, "отказ ушёл наружу без цены прогона"
    assert spend.output_tokens == 400 * conversation.MAX_ATTEMPTS
    assert spend.cents > 0


def test_a_chapter_truncated_every_time_still_moves_the_month_ledger(
    api, auth_headers, scripted
):
    """503 читателю — и запись в леджере, потому что деньги потрачены.

    Проверяется деньгами, а не кодом ответа: экран для человека остаётся тем
    же, меняется то, видит ли месячный потолок самый дорогой исход запроса.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    user_id = api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    scripted.responses.extend(_cut_off() for _ in range(writer.MAX_ATTEMPTS))

    response = api.post(
        "/v1/readings", json={"system": "natal", "chapter": "core"}, headers=auth_headers
    )

    assert response.status_code == 503, response.text
    assert response.json()["detail"]["error"] == "ai_unavailable"
    assert len(scripted.calls) == writer.MAX_ATTEMPTS
    assert _month_spend(user_id) > 0.0, (
        "три настоящие генерации, и в счёте аккаунта ноль — потолок месяца "
        "такого расхода не видит вовсе"
    )


def test_a_chat_turn_truncated_every_time_still_moves_the_month_ledger(
    api, auth_headers, scripted
):
    """Тот же довод на беседе, где обрыв встречается чаще всего."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    user_id = api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    scripted.responses.extend(_cut_off() for _ in range(conversation.MAX_ATTEMPTS))

    response = api.post(
        "/v1/chat", json={"message": "What should I do about work?"}, headers=auth_headers
    )

    assert response.status_code == 503, response.text
    assert _month_spend(user_id) > 0.0, (
        "оборванный ход стоил трёх генераций и не стоил аккаунту ничего"
    )


# ── 2 · читатель, ушедший посреди стрима ───────────────────────────────────


class _Held(ScriptedProvider):
    """Провайдер, замерший внутри генерации, пока тест не отпустит.

    Без него «клиент ушёл посреди хода» — это надежда на то, что планировщик
    сложил корутины в нужном порядке. С ним момент разрыва задан точно: ход
    стоит в модели, то есть деньги уже тратятся, а читателя уже нет.
    """

    async def complete(self, **kwargs):
        self.reached.set()
        await self.released.wait()
        return await super().complete(**kwargs)


@pytest.fixture
def stream_db(tmp_path, monkeypatch):
    """Пустая база и свой цикл: стрим проверяется без TestClient.

    `TestClient` крутит приложение на своём портале, а этому тесту нужно
    закрыть генератор ответа руками — ровно так, как это делает Starlette,
    когда соединение оборвалось, — и потом дождаться фоновой задачи в том же
    цикле, где она живёт.
    """
    from alma import config as config_module

    asyncio.run(session_module.dispose())
    monkeypatch.setenv("ALMA_DATABASE_URL", database_url(tmp_path, "stream.db"))
    monkeypatch.setenv("ALMA_JWT_SECRET", "test-secret-not-the-default")
    config_module.settings.cache_clear()
    run_async(session_module.create_all)
    yield
    asyncio.run(session_module.dispose())
    config_module.settings.cache_clear()


def test_a_reader_who_leaves_mid_turn_does_not_erase_what_the_turn_cost(stream_db):
    """Обрыв связи не отменяет уже потраченные деньги.

    Сорванная связь — норма мобильной сети: лифт, метро, блокировка экрана.
    Поток отменял свою задачу, отмена приходила в `_chat_turn` и уносила всю
    транзакцию — `session_scope` на `CancelledError` делает rollback, — так что
    оплаченная генерация не оставляла ни расхода, ни списанного вопроса, ни
    ответа в треде. Платили мы, а месячный потолок этого не видел.

    Тест держит ход в модели, закрывает поток (это и есть ушедший читатель),
    отпускает модель и ждёт записи.
    """
    natal_factors = compute("natal", BIRTH).factors

    async def work():
        async with session_module.session_scope() as setup:
            user = await accounts.create_guest(setup)
            user_id = user.id
            setup.add(
                Profile(
                    user_id=user_id,
                    is_self=True,
                    birth_date=BIRTH.date,
                    birth_time=BIRTH.time,
                    latitude=BIRTH.latitude,
                    longitude=BIRTH.longitude,
                    timezone=BIRTH.timezone,
                    place_label=BIRTH.place_label,
                )
            )
            await setup.flush()

        held = _Held(responses=[_chat_reply(natal_factors[:1])])
        held.reached = asyncio.Event()
        held.released = asyncio.Event()

        async with session_module.session_scope() as session:
            who = await session.get(User, user_id)
            response = await route.chat_stream(
                ChatRequest(message="What should I do about work?"),
                who,
                session,
                lambda: held,
            )

        events = response.body_iterator
        first = await events.__anext__()
        assert first.startswith("event: stage"), first

        # Ход уже в модели: дальше каждая секунда — наши деньги.
        await asyncio.wait_for(held.reached.wait(), 30)
        # Читатель ушёл. Starlette закрывает генератор ответа ровно так.
        await events.aclose()
        held.released.set()

        # Ждём того, что обязано случиться и без читателя. На старом коде
        # задача отменена ещё в `aclose`, и ждать здесь нечего.
        for _ in range(300):
            async with session_module.session_scope() as check:
                spent = await cost.month_spend(check, await check.get(User, user_id))
                asked = await check.get(
                    UsageCounter,
                    route._counter_id(
                        user_id,
                        route._period_start("month"),
                        route.WELCOME_QUESTIONS_METRIC,
                    ),
                )
                said = (
                    await check.execute(
                        select(ChatMessage).where(ChatMessage.role == "alma")
                    )
                ).scalars().all()
            if spent > 0 and asked is not None and said:
                break
            await asyncio.sleep(0.05)
        return spent, (asked.count if asked is not None else 0), len(said)

    spent, asked, said = run_async(work)

    assert spent > 0.0, (
        "генерация состоялась и была оплачена, а в леджере ноль — уход "
        "читателя стёр деньги, которых он не возвращает"
    )
    assert asked == 1, "вопрос из квоты не списан, хотя ответ написан"
    assert said == 1, "за ответ заплачено, а в треде его нет"


# ── 3 · превью сфер мимо месячного потолка ─────────────────────────────────


def test_the_free_spheres_ask_the_month_ceiling_before_generating(
    api, auth_headers, scripted, monkeypatch
):
    """Единственная генерация продукта, которая никогда не спрашивала потолок.

    Расход она при этом записывала, так что превью тратило общий месячный
    потолок и само в него не упиралось — оно только приближало стену, за
    которой откажут другим экранам. Дыра открывается правкой даты рождения:
    ключ превью включает весь список факторов, поэтому каждая новая дата — это
    новая генерация, сколько угодно раз подряд.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    # Ответ в сценарии есть намеренно: без него отказ был бы неотличим от
    # «модели нечего было сказать», а проверяемое здесь — что до модели дело
    # не дошло вовсе.
    scripted.responses.append(
        _spheres_reply(_factors_for(api, auth_headers, system="natal"))
    )
    projections: list[float] = []

    async def refuse(session, user, *, tier, projected):
        projections.append(projected)
        raise cost.BudgetExceeded("the month is spent")

    monkeypatch.setattr(cost, "guard_month", refuse)

    response = api.get("/v1/natal/spheres", headers=auth_headers)

    assert response.status_code == 429, response.text
    assert response.json()["detail"]["error"] == "month_budget"
    assert scripted.calls == [], "модель позвали после отказа потолка"
    assert projections and projections[0] > 0, (
        "потолок спросили о нулевой цене — такая проверка не отказывает никогда"
    )


def test_a_stored_spheres_preview_opens_in_a_month_that_is_spent(
    api, auth_headers, scripted, monkeypatch
):
    """Гейт стоит после кэша, и это половина правки.

    Уже написанное превью — не генерация: перечитывать его в конце месяца
    должно быть можно, иначе натальный экран у бесплатного человека темнеет
    ровно тогда, когда он ничего не тратит.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(
        _spheres_reply(_factors_for(api, auth_headers, system="natal"))
    )
    assert api.get("/v1/natal/spheres", headers=auth_headers).status_code == 200

    async def refuse(session, user, *, tier, projected):
        raise cost.BudgetExceeded("the month is spent")

    monkeypatch.setattr(cost, "guard_month", refuse)

    again = api.get("/v1/natal/spheres", headers=auth_headers)
    assert again.status_code == 200, again.text
    assert again.json()["cached"] is True




# ── 4 · два сообщения, отправленные разом ──────────────────────────────────


class _Slow(ScriptedProvider):
    """Генерация, которая длится — как всякая настоящая.

    Задержка здесь не для того, чтобы тест позеленел, а для того, чтобы гонка
    была настоящей: два хода обязаны оказаться внутри ворот одновременно, и
    именно так это выглядит на телефоне, где палец нажимает «отправить» дважды
    за полсекунды. Второй ход считает карту по прогретому кэшу за десятки
    миллисекунд, так что треть секунды — щель с запасом.
    """

    async def complete(self, **kwargs):
        await asyncio.sleep(0.3)
        return await super().complete(**kwargs)


@pytest.fixture
def slow(api):
    from alma.api.deps import get_provider

    provider = _Slow()
    api.app.dependency_overrides[get_provider] = lambda: (lambda: provider)
    yield provider
    api.app.dependency_overrides.clear()


def test_two_questions_at_once_cannot_both_spend_the_only_one_left(
    api, auth_headers, slow, monkeypatch
):
    """Порция в один вопрос отвечает один раз, сколько бы их ни пришло разом.

    `_chat_gate` читал счётчик, а увеличивался он много позже — после целой
    генерации и, что важнее, после ответа: зависимость сессии коммитит уже
    отданный ответ. Поэтому второе сообщение читало ноль даже тогда, когда
    первое успело ответить, и бесплатный человек получал вдвое больше
    обещанного, а платили за это мы. Двойное нажатие «отправить» даёт ровно
    это.

    Ответов в сценарии два намеренно: будь он один, второй ход упал бы в 503
    «сценарий кончился», и тест зеленел бы не по той причине.

    **Про месячный потолок здесь теста нет, и это измеренный факт, а не
    забывчивость.** Дыра у него та же — читается до записи, — и закрыта тем же
    замком; но на SQLite её не показать. Ход пишет `chat_thread` и первое
    сообщение *раньше*, чем спрашивает потолок (`readings.py`: flush до
    `_guard_month`), а SQLite пускает одного писателя за раз, — так что второй
    ход упирается в блокировку базы и доходит до потолка уже после чужого
    коммита. Замерено: второй ход ждал ровно столько, сколько длилась
    генерация первого. На Postgres, где строки не запирают таблицу, эта
    очередь исчезает и щель настоящая — то есть тест на неё живёт в прогоне
    `ALMA_TEST_DATABASE_URL`, а не здесь, и написать его до появления такого
    прогона значило бы завести зелёный тест, который ничего не стережёт.
    """
    monkeypatch.setattr(settings(), "free_welcome_bundle", 1)
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _factors_for(api, auth_headers, system="natal")
    slow.responses.extend(_chat_reply(factors[:1]) for _ in range(2))

    import anyio

    answers: list = []

    async def ask() -> None:
        async def one(text: str) -> None:
            answers.append(
                await anyio.to_thread.run_sync(
                    lambda: api.post(
                        "/v1/chat", json={"message": text}, headers=auth_headers
                    )
                )
            )

        async with anyio.create_task_group() as group:
            group.start_soon(one, "What should I do about work?")
            group.start_soon(one, "And what about money?")

    anyio.run(ask)

    codes = sorted(answer.status_code for answer in answers)
    assert codes == [200, 429], [answer.text for answer in answers]
    refused = next(a for a in answers if a.status_code == 429)
    assert refused.json()["detail"]["error"] == "question_limit"
    assert len(slow.calls) == 1, "порция на один вопрос оплатила две генерации"
