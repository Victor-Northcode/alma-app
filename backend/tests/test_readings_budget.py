"""The money rules behind a reading and a chat turn.

Three separate things are asserted here, and they are separate on purpose.

*What a free chapter costs* is measured against the ceiling rather than
against another run of the same code: the prompt is built exactly as the
router builds it, priced from the table in `alma.ai.cost`, and compared to
`free_user_budget`. That is a statement about the product's economics, and it
fails the day a prompt grows past what the free tier can pay for.

*Which model and which allowance a tier gets* is asserted per tier, because
the bug it replaces was a boolean that could not tell an $8.99 purchase from
a $9.99-a-month subscription.

*What the two refusals say* matters as much as that they happen. Running out
of questions and running out of money are different sentences, and a client
that cannot tell them apart tells a subscriber with sixty turns left to come
back tomorrow.
"""

from __future__ import annotations

import json
from datetime import date, datetime

import pytest
from conftest import read_async

from alma.ai import chapters as chapter_defs
from alma.ai import conversation, cost, writer
from alma.ai.provider import ScriptedProvider, models
from alma.api.routers import readings as route
from alma.calc import BirthData, compute
from alma.config import settings
from alma.i18n import replies as i18n_replies
from tests.conftest import LUCAS, SOFIA


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


@pytest.fixture
def scripted(api):
    """Substitute a scripted provider for the real one, per test."""
    from alma.api.deps import get_provider

    provider = ScriptedProvider()
    api.app.dependency_overrides[get_provider] = lambda: (lambda: provider)
    yield provider
    api.app.dependency_overrides.clear()


def _reply(factors: list[str]) -> str:
    return json.dumps(
        {
            "title": "A title",
            "teaser": "A line.",
            "advice": "Say the thing sooner.",
            # Длина заготовки держится выше нижней границы главы: у платной
            # это триста слов, и абзац из шести отвергается валидатором,
            # после чего сценарий кончается ответами и тест падает 503-й на
            # ровном месте. Строка повторяется, потому что проверяется бюджет,
            # а не проза.
            "paragraphs": [
                {"text": "The first paragraph, read from the chart. " * 30,
                 "factors": factors[:1]},
                {"text": "The second, from the same place. " * 30,
                 "factors": factors[:1]},
                # Третий абзац: у платной главы минимум теперь три.
                {"text": "The third, still from the chart. " * 30,
                 "factors": factors[:1]},
            ],
        }
    )


def _chat_reply(factors: list[str]) -> str:
    return json.dumps(
        {
            "answer": [{"text": "Here is what the chart says.", "factors": factors[:1]}],
            "answered_from_chart": True,
            "remember": [],
        }
    )


def _natal_factors() -> list[str]:
    return list(compute("natal", _birth(SOFIA), house_system="placidus").factors)


def _numerology_factors() -> list[str]:
    return list(
        compute("numerology", _birth(SOFIA), reference=datetime.now().date()).factors
    )


# ── what a free chapter costs ──────────────────────────────────────────────

def _system_results() -> dict[str, object]:
    """One `CalcResult` per system, computed the way the router computes it."""
    birth, other = _birth(SOFIA), _birth(LUCAS)
    today = datetime.now().date()
    results = {}
    for system in chapter_defs.BY_SYSTEM:
        options = route._options_for(system, "placidus")
        if system == "compatibility":
            # Its prompt is the second largest we build, because it carries two
            # charts, so it has to be in every ceiling measurement here.
            options = {"other": other, "house_system": "placidus"}
        if system in ("numerology", "birth-card", "synthesis"):
            options = {"reference": today}
        results[system] = compute(system, birth, **options)
    return results


def _free_chapter_projections(model: str) -> dict[str, float]:
    """Every free chapter of every system, priced the way the router prices it."""
    results = _system_results()
    return {
        f"{system}/{chapter.slug}": route._chapter_projection(
            results[system], chapter, model=model, locale="en", memory=None
        )
        for system in chapter_defs.BY_SYSTEM
        for chapter in chapter_defs.for_system(system)
        if chapter.free
    }


def _opening_projections(model: str, *, locale: str = "en") -> dict[str, float]:
    """Открывающий абзац каждой закрытой главы, в ценах роутера.

    Сорок штук, а не сорок одна: у бесплатной главы открывающего абзаца не
    бывает — она открыта, и роутер до этой ветки не доходит.
    """
    results = _system_results()
    return {
        f"{system}/{chapter.slug}": route._chapter_projection(
            results[system], chapter_defs.opening_of(chapter),
            model=model, locale=locale, memory=None,
        )
        for system in chapter_defs.BY_SYSTEM
        for chapter in chapter_defs.for_system(system)
        if not chapter.free
    }


def test_the_one_free_chapter_fits_the_free_ceiling_on_the_mid_model():
    """Бесплатная глава обязана быть по карману, иначе её нельзя прочитать.

    Тест мерил по одной главе-образцу на каждую из восьми систем; с 17.08.2026
    бесплатна ровно одна во всём продукте, и правило про неё то же самое:
    `writer.write` сверяет её с `free_user_budget`, и глава, которую потолок
    отвергает, — это 503, а не пейволл. Астрокартография когда-то выходила за
    потолок на шесть десятых цента, и особенного в ней было только одно —
    длинный список факторов.
    """
    ceiling = settings().free_user_budget
    _cheap, mid, _strong = models()

    projected = _free_chapter_projections(mid)
    assert list(projected) == ["natal/core"]

    over = {name: cost for name, cost in projected.items() if cost > ceiling}
    assert not over, (
        f"free chapters over the ${ceiling:.2f} ceiling on {mid}: "
        + ", ".join(f"{name} ${cost:.4f}" for name, cost in over.items())
    )


def test_every_opening_fits_the_free_ceiling_on_the_mid_model():
    """Сорок открывающих абзацев — то, что раздаётся даром теперь.

    Тот же вопрос, что и про бесплатную главу, и он стал важнее: абзац
    пишется для **каждой** закрытой главы, то есть у всех сорока промт обязан
    влезать в бесплатный потолок. Не влезет один — на одной конкретной главе
    вместо цены появится пустая стена, и найдётся это на самой длинной
    системе, как в прошлый раз.

    Кириллица меряется отдельно, потому что она и стоит отдельно: `writer`
    удваивает и потолок, и число токенов на слово, а промт остаётся тем же.
    """
    ceiling = settings().free_user_budget
    _cheap, mid, _strong = models()

    total = 41 - 1  # сорок одна глава минус одна бесплатная
    for locale, scale in (("en", 1.0), ("ru", 2.0)):
        projected = _opening_projections(mid, locale=locale)
        assert len(projected) == total, "у каждой закрытой главы есть открывающий абзац"
        over = {n: c for n, c in projected.items() if c > ceiling * scale}
        assert not over, (
            f"[{locale}] openings over the ${ceiling * scale:.2f} ceiling on {mid}: "
            + ", ".join(f"{name} ${cost:.4f}" for name, cost in over.items())
        )


def test_walking_every_locked_chapter_costs_about_what_the_owner_was_told():
    """Цена обхода всех глав тем, кто ничего не купил, — **один раз за жизнь**.

    Число здесь не круглое, и это намеренно: оно должно ловить не «стало
    чуть-чуть дороже», а «кто-то удлинил открывающий абзац или подключил его к
    сильной модели», то есть удвоение. Верхняя граница — проекция потолка, где
    вся разрешённая длина считается израсходованной; настоящий счёт примерно
    вдвое ниже, потому что сорок слов столько токенов не занимают.

    И это плата за жизнь аккаунта, а не за месяц: `_opening_key` намеренно не
    включает движущиеся факторы, поэтому повторные заходы бесплатны, а
    транзиты не переписывают свой абзац каждый раз, когда контакт входит в орб.
    """
    _cheap, mid, _strong = models()
    sweep = sum(_opening_projections(mid).values())
    assert 0.40 < sweep < 1.00, f"обход всех закрытых глав стоит ${sweep:.4f}"


def test_the_strong_model_is_what_the_free_ceiling_refuses():
    """Why the router must not send free writing to the strong model.

    This is the reproduction of the bug kept as an assertion. Every chapter
    used to go to the strong model while the free ones were guarded against
    the free ceiling, and the astrocartography sample — eleven thousand
    characters of line descriptions — projected past it. Every request for
    that chapter answered 503. If the prices or the prompt ever change enough
    that this stops being true, the routing is still correct and this test
    should be read again rather than deleted.

    Мерится по `astrocartography/lines`, хотя она перестала быть бесплатной:
    воспроизводится **баг**, а не сегодняшняя полка, и промт у неё тот же
    самый — самый длинный в продукте.
    """
    ceiling = settings().free_user_budget
    _cheap, mid, strong = models()
    results = _system_results()
    lines = chapter_defs.find("astrocartography", "lines")

    on_strong = route._chapter_projection(
        results["astrocartography"], lines, model=strong, locale="en", memory=None
    )
    on_mid = route._chapter_projection(
        results["astrocartography"], lines, model=mid, locale="en", memory=None
    )
    assert on_strong > ceiling
    assert _free_chapter_projections(strong)["natal/core"] < ceiling, (
        "the bug was never visible on natal"
    )
    # Средняя модель на том же промте — то, чем баг чинился, и чинится до сих
    # пор для всего, что раздаётся даром.
    assert on_mid < ceiling


def test_the_opening_of_a_locked_chapter_is_written_by_the_mid_model(
    api, auth_headers, scripted
):
    """И довод здесь **не** тот, что у бесплатной главы.

    Бесплатную главу сильная модель писать не может физически: её промт в
    бесплатный потолок на сильной модели не влезает (тест выше). Открывающий
    абзац влезает — он просит вчетверо меньше выхода, и на сильной модели
    самая длинная система проектируется в $0.036 против потолка $0.05.

    Причина, по которой он всё равно пишется средней, — не потолок одного
    вызова, а масштаб: абзац тратится **до** всякого решения о покупке, то
    есть на каждого, включая тех, кто не купит никогда, и таких большинство.
    Сорок абзацев на аккаунт — это то место, где разница между моделями
    умножается на всю базу свободных аккаунтов.

    Записано тестом, а не комментарием, потому что комментарий не падает.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_opening(_natal_factors()))

    response = api.post(
        "/v1/readings", json={"system": "natal", "chapter": "career"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    _cheap, mid, strong = models()
    assert scripted.calls[0]["model"] == mid
    assert strong not in {call["model"] for call in scripted.calls}


def test_a_free_chapter_is_written_by_the_mid_model(api, auth_headers, scripted):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_reply(_natal_factors()))

    response = api.post(
        "/v1/readings", json={"system": "natal", "chapter": "core"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    _cheap, mid, _strong = models()
    assert scripted.calls[0]["model"] == mid


def test_a_paid_chapter_is_written_by_the_strong_model(api, auth_headers, scripted, monkeypatch):
    from alma.auth import entitlements

    async def owns_it(session, user, system, *, chapter=None, partner_id=None, at=None):
        return entitlements.Access(True, "bought in the test", kind="one_time")

    monkeypatch.setattr(entitlements, "check", owns_it)
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_reply(_natal_factors()))

    response = api.post(
        "/v1/readings", json={"system": "natal", "chapter": "career"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    _cheap, _mid, strong = models()
    assert scripted.calls[0]["model"] == strong


def _opening(factors: list[str]) -> str:
    """Заготовка открывающего абзаца: один абзац, как просит `opening_of`."""
    return json.dumps(
        {
            "title": "A title",
            "teaser": "A line.",
            "paragraphs": [
                {"text": "Forty words about you, read from the chart.",
                 "factors": factors[:1]},
            ],
        }
    )


def test_a_locked_chapter_pays_for_forty_words_and_never_for_the_chapter(
    api, auth_headers, scripted
):
    """Сколько стоит стена — и сколько она стоит на второй заход.

    Здесь стояло «закрытая глава не доходит ни до писателя, ни до счётчика
    денег», и до 17.08.2026 это было правдой. До того был обратный режим:
    первые несколько закрытых глав писались **целиком** (`ALMA_PREVIEW_CHAPTERS`)
    и размывались на клиенте. Владелец отменил его по деньгам, а потом отменил
    и получившуюся чёрную стену — «просят заплатить за заголовок».

    Середина проверяется здесь с трёх сторон, и все три про деньги:
    писателя зовут по разу на главу, а не по разу на просмотр; каждый вызов
    записан в месячный счёт, потому что вызов без записи — дыра в потолке, а
    не экономия; и второй обход тех же глав не стоит уже ничего.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _natal_factors()
    scripted.responses.extend(_opening(factors) for _ in range(3))
    user_id = api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]

    locked = ("career", "love", "shadow")
    for chapter in locked:
        wall = api.post(
            "/v1/readings", json={"system": "natal", "chapter": chapter}, headers=auth_headers
        )
        assert wall.status_code == 200, wall.text
        body = wall.json()
        assert body["locked"] is True and body["reading"] is None
        assert body["opening"]["body"]

    assert len(scripted.calls) == 3, "по одному абзацу на главу, и ни одной главы"
    walked = _spent(user_id)
    assert walked > 0.0, "написанный абзац обязан быть записан в счёт"

    for chapter in locked:
        again = api.post(
            "/v1/readings", json={"system": "natal", "chapter": chapter}, headers=auth_headers
        )
        assert again.status_code == 200 and again.json()["cached"] is True

    assert len(scripted.calls) == 3, "второй заход снова заплатил за те же слова"
    assert _spent(user_id) == pytest.approx(walked), "перечитывание стены бесплатно"


# ── which model and how many turns each tier gets ──────────────────────────

@pytest.fixture
def as_tier(monkeypatch):
    """Pin the commercial tier without going through a payment provider.

    Deriving the tier from entitlements is `entitlements.tier_of`'s rule and
    is tested where it lives. What this router owes is the mapping from a
    tier to a model and an allowance, and that is what these tests hold.
    """
    from alma.auth import entitlements

    def pin(tier: str) -> None:
        async def answer(session, user, *, at=None):
            return tier

        monkeypatch.setattr(entitlements, "tier_of", answer)

    return pin


def test_the_first_questions_ever_are_on_the_model_that_sells(
    api, auth_headers, scripted, as_tier
):
    """A new account's opening turns run on the mid model, then the cheap one.

    **The shop window used to be the cheapest model.** Free meant
    `claude-haiku-4-5` from the first word, and the owner\'s verdict on his own
    product was that Alma is stupid. On one chart and one question — *what are
    my talents* — the cheap model returned four flat sentences and the mid
    model returned *"you see the error in the invoice before anyone else
    does."* The second is the product; the first is what everybody who had not
    paid was shown, at the exact moment they decide whether to believe it.

    Three a day for ever on the mid model is $5.47 a month from somebody who
    pays nothing. One **ever** is six cents per install, spent exactly where
    the decision is made — and after it the conversation belongs to the plan.
    The cheap model is gone from the chat entirely: the owner's verdict on it
    was that it made Alma sound stupid, and a shop window that undersells the
    product is worse than a closed door.
    """
    as_tier("free")
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = _numerology_factors()
    scripted.responses.extend(_chat_reply(factors) for _ in range(3))

    cheap, mid, _strong = models()
    welcome = settings().free_welcome_bundle

    for _ in range(welcome):
        body = api.post("/v1/chat", json={"message": "and now?"}, headers=auth_headers)
        assert body.status_code == 200, body.text
    assert {call["model"] for call in scripted.calls} == {mid}, (
        "the first turn of a new account is the one that decides whether "
        "anybody believes the product, and it must not be the cheap model"
    )
    assert cheap not in {call["model"] for call in scripted.calls}

    # The welcome is spent, and the wall is immediate — there is no daily
    # refill and no cheap tier behind it. The sentence on the wall points at
    # the plan; the client shows the paywall.
    blocked = api.post("/v1/chat", json={"message": "again"}, headers=auth_headers)
    assert blocked.status_code == 429
    detail = blocked.json()["detail"]
    assert detail["error"] == "question_limit"
    assert detail["period"] == "day"


def test_a_purchase_includes_a_finite_bundle_on_the_better_model(
    api, auth_headers, scripted, as_tier
):
    """A door includes a pile of good conversation, and the pile runs out.

    A one-time purchase never expires, so an allowance that renewed with it
    would be a subscription given away for free — about seventy cents a month,
    for ever, against eight dollars that arrive once. A fixed bundle instead:
    the same model a subscriber gets, for a countable number of turns.
    """
    as_tier("owner")
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_chat_reply(_numerology_factors()))

    body = api.post("/v1/chat", json={"message": "hello"}, headers=auth_headers).json()
    _cheap, _mid, strong = models()
    assert scripted.calls[0]["model"] == strong, (
        "the purchase bundle is the deepest voice — it is the thanks for a "
        "purchase and the taste of what the plan carries"
    )
    assert body["questions_period"] == "once"
    assert body["questions_left"] == settings().owner_question_bundle - 1


def test_a_spent_bundle_meets_the_wall_that_sells_the_plan(
    api, auth_headers, scripted, as_tier
):
    """When the purchase bundle runs out the conversation belongs to the plan.

    There is no cheap tier to fall back to any more. The buyer who spent five
    questions on the deepest voice has discovered by using it what the
    subscription is for — and the wall's own sentence says so, in their
    language, ending on what stays free.
    """
    as_tier("owner")
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    bundle = settings().owner_question_bundle
    for _ in range(bundle):
        scripted.responses.append(_chat_reply(_numerology_factors()))

    for _ in range(bundle):
        answer = api.post("/v1/chat", json={"message": "again"}, headers=auth_headers)
        assert answer.status_code == 200, answer.text

    blocked = api.post("/v1/chat", json={"message": "one more"}, headers=auth_headers)
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["error"] == "question_limit"


def test_a_subscriber_gets_the_mid_model_counted_by_the_month(
    api, auth_headers, scripted, as_tier
):
    as_tier("subscriber")
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_chat_reply(_numerology_factors()))

    body = api.post("/v1/chat", json={"message": "hello"}, headers=auth_headers).json()
    _cheap, mid, _strong = models()
    assert scripted.calls[0]["model"] == mid
    assert body["questions_period"] == "month"
    assert body["questions_left"] == settings().subscriber_questions_per_month - 1


def test_every_period_an_allowance_can_carry_has_a_sentence_for_its_wall():
    """`_chat_gate` собирает ключ фразы из периода порции — и промах это 500.

    Периодов четыре: день (свободный слой), месяц (подписка и приветственный
    бандл), неделя (недельный A/B, ТЗ §8) и `once` (бандл покупки). Фраз в
    `i18n/replies.py` было две, и `replies.reply()` индексирует, а не `.get`,
    потому что молча отдать читателю английский — тоже брак. Значит недостающая
    фраза — это `KeyError` посреди 429: вместо переведённого отказа, который
    продаёт план, читатель получает экран ошибки.

    Периоды перечислены вызовом самих конструкторов порции, а не списком строк:
    пятый период, добавленный завтра, попадёт сюда сам, а не через год.
    """
    periods = {
        route._allowance("free", mid="m").period,
        route._allowance("subscriber", mid="m").period,
        route._allowance("subscriber", mid="m", weekly=True).period,
        route._bundle(strong="s").period,
        route._welcome(mid="m").period,
    }
    assert periods == {"day", "month", "week", "once"}

    silent = sorted(p for p in periods if f"question_limit.{p}" not in i18n_replies.BY_ERROR)
    assert not silent, (
        "у периода нет фразы для стены — `replies.reply()` бросит KeyError, и "
        f"читатель увидит 500 вместо 429: {silent}"
    )


def test_a_weekly_allowance_at_its_wall_answers_429_rather_than_raising(
    api, auth_headers, scripted, as_tier, monkeypatch
):
    """День, когда недельный A/B включат обратно, не должен быть пятисотым.

    Порция по недельному сроку оставлена в коде намеренно (см. довод в
    `_chat_gate`), и до этой правки она доходила до стены с ключом
    `question_limit.week`, которого в таблице не было. Первый же подписчик
    эксперимента, упёршийся в свою десятку, получал бы `KeyError` — и получал
    бы его ровно на том экране, который эксперимент и продаёт.

    `has_kind` подменена, а не выписана грантом: кинда `weekly` больше нет ни в
    каталоге, ни в `EntitlementKind` — это утверждает
    `test_there_are_no_weekly_or_annual_kinds_any_more`, — и выписать её честно
    сегодня нечем. Подменяется ровно та функция, которая в тот день ответит
    `True` сама.
    """
    from alma import config as config_module
    from alma.auth import entitlements

    async def weekly(session, user, kind):
        return kind == "weekly"

    monkeypatch.setattr(entitlements, "has_kind", weekly)
    monkeypatch.setenv("ALMA_WEEKLY_QUESTIONS", "1")
    config_module.settings.cache_clear()
    try:
        as_tier("subscriber")
        api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
        scripted.responses.append(_chat_reply(_numerology_factors()))

        first = api.post(
            "/v1/chat",
            json={"message": "come sono fatta", "locale": "it"},
            headers=auth_headers,
        )
        assert first.status_code == 200, first.text
        assert first.json()["questions_period"] == "week"

        blocked = api.post(
            "/v1/chat",
            json={"message": "e adesso", "locale": "it"},
            headers=auth_headers,
        )
        assert blocked.status_code == 429, blocked.text
        detail = blocked.json()["detail"]
        assert detail["error"] == "question_limit"
        assert detail["period"] == "week"
        # Её фраза, на языке читателя, и кончается тем, что у него всё равно
        # есть, — как у остальных трёх стен.
        assert detail["message"] == i18n_replies.LIMIT_WEEK["it"].format(limit=1)
        assert "otto i sistemi" in detail["message"]
    finally:
        config_module.settings.cache_clear()


def test_a_subscribers_turns_do_not_come_back_at_midnight(api, auth_headers, scripted, as_tier):
    """The counter a subscriber is measured by is filed under the month.

    Stated as a property of the key rather than by moving a clock: every day
    of a month resolves to one counter, and consecutive days do not. A daily
    counter for a monthly allowance would hand back seventy turns every
    midnight — twenty-one hundred turns a month against a ledger that buys
    seventy-four.
    """
    first = datetime(2026, 8, 1, 0, 30)
    last = datetime(2026, 8, 31, 23, 30)
    next_month = datetime(2026, 9, 1, 0, 30)

    assert route._period_start("month", first) == route._period_start("month", last)
    assert route._period_start("month", last) != route._period_start("month", next_month)
    assert route._period_start("day", first) != route._period_start("day", last)


def test_the_monthly_counter_cannot_collide_with_the_daily_one():
    """On the first of the month the two periods share a date, not a row.

    They are distinguished by the metric name rather than by the day, because
    the day is the one thing they genuinely have in common once a month. A
    shared row would charge the first turn of every month to both allowances.
    """
    first_of_month = route._period_start("month", datetime(2026, 8, 1, 9, 0))
    assert first_of_month == route._period_start("day", datetime(2026, 8, 1, 9, 0))
    assert route._counter_id("u1", first_of_month, route.DAILY_QUESTIONS_METRIC) != route._counter_id(
        "u1", first_of_month, route.MONTHLY_QUESTIONS_METRIC
    )


# ── the cumulative ledger ──────────────────────────────────────────────────

@pytest.fixture
def spent_month(monkeypatch):
    """A free-tier monthly ceiling too small for any call to fit under."""
    from alma import config as config_module

    monkeypatch.setenv("ALMA_FREE_MONTH_BUDGET", "0.0001")
    config_module.settings.cache_clear()
    yield
    config_module.settings.cache_clear()


def test_the_month_ledger_refuses_a_chat_turn_it_cannot_afford(
    api, auth_headers, scripted, as_tier, spent_month
):
    as_tier("free")
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_chat_reply(_numerology_factors()))

    response = api.post("/v1/chat", json={"message": "hello"}, headers=auth_headers)
    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "month_budget"
    assert scripted.calls == [], "the ledger has to answer before the model does"


def test_running_out_of_money_does_not_read_like_running_out_of_questions(
    api, auth_headers, scripted, as_tier, monkeypatch, spent_month
):
    """Two 429s that must never be confused for one another.

    Both refuse the same request and both reset, but one comes back tomorrow
    and the other comes back when the month does — and only one of them is
    fixed by paying us. They are told apart by the `error` field, so it is
    the field this asserts on rather than the prose.
    """
    as_tier("free")
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)

    money = api.post("/v1/chat", json={"message": "hello"}, headers=auth_headers).json()

    # Same tier, same route, allowance exhausted instead of the ledger.
    monkeypatch.setattr(route, "_guard_month", _no_month_guard)
    monkeypatch.setattr(settings(), "free_questions_per_day", 0)
    # The welcome bundle is a second allowance and would answer this request
    # before the counter ever refused it. Zeroed too, so the test still asks
    # the question it was written to ask.
    monkeypatch.setattr(settings(), "free_welcome_bundle", 0)
    count = api.post("/v1/chat", json={"message": "hello"}, headers=auth_headers).json()

    assert money["detail"]["error"] == "month_budget"
    assert count["detail"]["error"] == "question_limit"
    assert money["detail"]["message"] != count["detail"]["message"]


async def _no_month_guard(session, user, *, tier, projected):
    return None


def test_the_month_ledger_refuses_a_chapter_it_cannot_afford(
    api, auth_headers, scripted, spent_month
):
    """A chapter is generation too, and the ceiling is per account.

    The per-call guard inside `writer.write` would have let this through: one
    free chapter on the mid model is three cents and individually affordable.
    What the account has already spent is invisible from there.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_reply(_natal_factors()))

    response = api.post(
        "/v1/readings", json={"system": "natal", "chapter": "core"}, headers=auth_headers
    )
    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "month_budget"
    assert scripted.calls == []


def test_a_stored_reading_is_never_charged_to_the_ledger_again(
    api, auth_headers, scripted, monkeypatch
):
    """Re-reading what you already own must not be able to hit a ceiling.

    The stored-reading lookup runs before the ledger for exactly this reason:
    a chapter someone paid for has to still open on the last day of a month
    they have otherwise spent.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_reply(_natal_factors()))
    request = {"system": "natal", "chapter": "core"}

    assert api.post("/v1/readings", json=request, headers=auth_headers).status_code == 200

    calls: list[str] = []

    async def refuse(session, user, *, tier, projected):
        calls.append(tier)
        raise route.cost.BudgetExceeded("the month is spent")

    monkeypatch.setattr(route.cost, "guard_month", refuse)
    again = api.post("/v1/readings", json=request, headers=auth_headers)
    assert again.status_code == 200 and again.json()["cached"] is True
    assert calls == []


def test_a_chat_turn_is_recorded_where_the_ledger_reads_it(api, auth_headers, scripted, as_tier):
    """What the request path writes has to be what `month_spend` sums.

    The two halves live in different modules and are joined only by a metric
    name; a typo in it would not fail anything, it would silently make every
    account look free.
    """

    from alma.ai import cost
    from alma.db import get_session
    from alma.db.models import User

    as_tier("free")
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    scripted.responses.append(_chat_reply(_numerology_factors()))
    user_id = api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    api.post("/v1/chat", json={"message": "hello"}, headers=auth_headers)

    async def read_back() -> float:
        async for session in get_session():
            user = await session.get(User, user_id)
            return await cost.month_spend(session, user)
        return 0.0

    assert read_async(read_back) > 0.0


# ── the path that spends the most and used to record the least ─────────────

def _spent(user_id: str) -> float:

    from alma.ai import cost
    from alma.db import get_session
    from alma.db.models import User

    async def read_back() -> float:
        async for session in get_session():
            return await cost.month_spend(session, await session.get(User, user_id))
        return 0.0

    return read_async(read_back)


def test_a_refused_chapter_is_still_charged_to_the_month(api, auth_headers, scripted):
    """Three generations happen and all three are paid for.

    The refusal path is the *expensive* one — `MAX_ATTEMPTS` attempts rather
    than one — and it was the only path that recorded nothing at all: the
    router raised the 422 before `_spend`. So nothing bounded how many such
    requests an account could make, because the thing counting them was
    skipped exactly when they failed.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    user_id = api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    invented = _reply(["transiting Saturn conjunct natal Vulcan"])
    scripted.responses.extend(invented for _ in range(writer.MAX_ATTEMPTS))

    response = api.post(
        "/v1/readings", json={"system": "natal", "chapter": "core"}, headers=auth_headers
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "reading_refused"
    assert len(scripted.calls) == writer.MAX_ATTEMPTS

    charged = _spent(user_id)
    one_attempt = cost.cost(
        scripted.calls[0]["model"], scripted.input_tokens, scripted.output_tokens
    )
    assert charged == pytest.approx(one_attempt.dollars * writer.MAX_ATTEMPTS, rel=1e-6)


def test_a_refused_chat_turn_is_charged_but_does_not_cost_a_question(
    api, auth_headers, scripted, as_tier
):
    """The money is ours to account for; the question was never answered.

    This test used to assert the opposite, and the comment defending it — "a
    question that keeps tripping the validator is still a question" — was
    written before an aside became free. The two rules then contradicted each
    other in the reader's favour and against it at the same time: asking about
    death and getting an answer was free, asking about death and getting an
    error cost one of three. Measured on a real free account, two of the day's
    three questions went to error screens (`docs/CONVERSATION.md` §13).

    The worry that justified counting — an unlimited re-ask making the cheapest
    tier the most expensive — is answered by the two lines below it: the spend
    ledger records every attempt, and `guard_month` reads that ledger before
    the next request is allowed to generate anything at all.
    """
    as_tier("free")
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    user_id = api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]
    invented = _chat_reply(["life path 11 in the ninth house of Neptune"])
    scripted.responses.extend(invented for _ in range(conversation.MAX_ATTEMPTS))

    response = api.post("/v1/chat", json={"message": "well?"}, headers=auth_headers)
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "answer_refused"
    assert _spent(user_id) > 0.0, "every attempt is charged to the month"

    scripted.responses.append(_chat_reply(_numerology_factors()))
    left = api.post("/v1/chat", json={"message": "again"}, headers=auth_headers).json()
    # The whole free allowance is the one welcome question now, and the
    # refused attempt must not have been the thing that spent it.
    assert left["questions_left"] == settings().free_welcome_bundle - 1, (
        "the refused turn was counted against a person who was never answered"
    )


def test_the_refusal_a_reader_sees_is_in_their_language_and_not_about_us(
    api, auth_headers, scripted, as_tier
):
    """`str(exc)` was a sentence about our validator, in English, to anybody.

    A Russian speaker received "could not produce an answer that only cites
    real factors — refusing rather than replying with something invented" three
    times for one question about her Moon.
    """
    as_tier("free")
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    invented = _chat_reply(["life path 11 in the ninth house of Neptune"])
    scripted.responses.extend(invented for _ in range(conversation.MAX_ATTEMPTS))

    detail = api.post(
        "/v1/chat", json={"message": "erzähl mir von meinem Mond", "locale": "de"},
        headers=auth_headers,
    ).json()["detail"]

    assert detail["error"] == "answer_refused"
    assert detail["message"] == i18n_replies.REFUSED["de"]
    assert "cites real factors" not in detail["message"]


# ── an allowance nobody can actually use is a lie ──────────────────────────

def test_no_tier_is_promised_more_than_its_ceiling_can_fund():
    """The two numbers are set in different files and nothing joined them.

    `paid_questions_per_day` was 50 against a $0.70 owner ceiling — roughly
    thirteen times what it could fund — so an owner ran out of money on about
    the fourth day and was told 429 `month_budget` while the same response
    still said forty-five questions left. Two limits that disagree by an order
    of magnitude means the documented one is a lie and the ledger is quietly
    doing the product's job.

    Priced through the router's own projection helpers, because that is what
    `guard_month` adds, and against the heaviest month each tier can honestly
    have: every chat turn used, plus the most written content that tier can
    reach in one month.
    """
    config = settings()
    _cheap, mid, strong = models()
    birth, other = _birth(SOFIA), _birth(LUCAS)
    turn = _chat_turn_projection(birth)

    samples = sum(_free_chapter_projections(mid).values())
    # **Обход всех закрытых глав входит в худший месяц каждого тира, кто может
    # его совершить.** Свободный аккаунт — очевидно; но и покупатель тоже, и
    # это ровно тот случай, который заставил поднять `owner_month_budget` с
    # 3.25 до 3.60: человек может обойти сорок стен, раздумывая, купить бандл и
    # дочитать весь архив в том же месяце. Подписчику абзацы не пишутся вовсе —
    # ему всё открыто, — поэтому в его строке их нет.
    openings = sum(_opening_projections(mid).values())
    everything = _whole_archive_projection(birth, other, mid=mid)

    heaviest = {
        # The free chat is one welcome question ever, on the mid model; the
        # daily allowance is zero and the cheap tier is gone.
        "free": config.free_welcome_bundle * turn(mid) + samples + openings,
        # An owner may have bought the archive, so the whole of it is written
        # in the month they bought it — plus the five-question bundle on the
        # strong model, all conceivably in the same month.
        "owner": config.owner_question_bundle * turn(strong) + everything + openings,
        "subscriber": config.subscriber_questions_per_month * turn(mid) + everything,
    }
    for tier, needed in heaviest.items():
        ceiling = cost.month_ceiling(tier)
        assert needed <= ceiling, (
            f"the {tier} tier is promised ${needed:.4f} of generation against a "
            f"${ceiling:.2f} ceiling"
        )


def _chat_turn_projection(birth):
    """One turn, at the longest history the conversation will carry."""
    results = [
        compute("natal", birth, house_system="placidus"),
        compute("numerology", birth, reference=datetime.now().date()),
    ]
    history = [
        ("user", "What does my chart say about the work I should be doing?"),
        ("alma", "Your Midheaven in Capricorn describes a long climb. " * 4),
    ] * (conversation.MAX_HISTORY // 2)

    def at(model: str) -> float:
        return route._chat_projection(
            question="Should I take the job in Berlin or stay where I am?",
            results=results,
            history=history,
            model=model,
            locale="en",
            paid=False,
            memory=["they are a nurse", "they moved last year"],
        )

    return at


def _whole_archive_projection(birth, other, *, mid: str) -> float:
    """Every chapter of every system, each on the model that would write it."""
    _cheap, _mid, strong = models()
    today = datetime.now().date()
    total = 0.0
    for system in chapter_defs.BY_SYSTEM:
        options = route._options_for(system, "placidus")
        if system == "compatibility":
            options = {"other": other, "house_system": "placidus"}
        if system in ("numerology", "birth-card", "synthesis"):
            options = {"reference": today}
        result = compute(system, birth, **options)
        for chapter in chapter_defs.for_system(system):
            total += route._chapter_projection(
                result, chapter, model=mid if chapter.free else strong,
                locale="en", memory=None,
            )
    return total
