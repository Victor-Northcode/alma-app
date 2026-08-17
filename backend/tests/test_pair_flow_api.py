"""Флоу P4 сверху: кредит подписчика и кап бесплатных тизеров, через HTTP.

`test_pair_credits.py` проверяет правила кредита как правила. Здесь — то, что
их **кто-то спрашивает**: что вторая проверка подписчика в одном цикле упирается
в 402 до генерации, что первая тратит включённую и превращается в обычный грант,
и что бесплатный тизер второму новому человеку в месяц заменяется пейволлом.

Все три — про деньги в разные стороны. Не спросить кредит значит раздавать
отчёты по 26¢ без счёта; спросить его слишком строго значит показать пейволл
тому, кто уже платит $9.99 в месяц, — а это отмена, а не покупка.
"""

from __future__ import annotations

import json

import pytest
from conftest import LUCAS, SOFIA

from test_billing_appstore import (  # noqa: F401 - `apple` is a fixture
    BUNDLE,
    _sign,
    _transaction,
    apple,
)
from alma.ai.provider import ScriptedProvider


@pytest.fixture
def store_api(api, monkeypatch):
    from alma import config as config_module

    monkeypatch.setenv("APPLE_BUNDLE_ID", BUNDLE)
    config_module.settings.cache_clear()
    yield api
    config_module.settings.cache_clear()


@pytest.fixture
def scripted(store_api):
    """Провайдер, который отвечает заготовкой вместо модели."""
    from alma.api.deps import get_provider

    provider = ScriptedProvider()
    store_api.app.dependency_overrides[get_provider] = lambda: (lambda: provider)
    yield provider
    store_api.app.dependency_overrides.clear()


def _headers(api) -> dict:
    return {"Authorization": f"Bearer {api.get('/v1/auth/session').json()['token']}"}


def _profiles(api, headers) -> tuple[str, str]:
    api.post("/v1/profiles", json={**SOFIA, "is_self": True}, headers=headers)
    partner = api.post(
        "/v1/profiles",
        json={**LUCAS, "relation": "partner", "name": "Katya"},
        headers=headers,
    )
    assert partner.status_code == 201, partner.text
    return partner.json()["id"], headers


def _subscribe(api, headers, apple, *, transaction_id: str = "2000000700000001") -> None:
    token = _sign(
        _transaction(
            product="sub.monthly",
            transaction_id=transaction_id,
            kind="Auto-Renewable Subscription",
            price=9990,
            expires_in_days=31,
        ),
        apple["key"], apple["chain"],
    )
    response = api.post(
        "/v1/billing/iap/verify",
        json={"platform": "appstore", "product": "sub.monthly", "transaction": token},
        headers=headers,
    )
    assert response.status_code == 200, response.text


def _birth(payload: dict):
    from datetime import date

    from alma.calc import BirthData

    return BirthData(
        date=date.fromisoformat(payload["birth_date"]),
        time=payload["birth_time"],
        latitude=payload["latitude"],
        longitude=payload["longitude"],
        timezone=payload["timezone"],
        place_label=payload["place_label"],
        name=payload["name"],
    )


def _reply(chapter: str = "attraction") -> str:
    """Ответ «модели» с **настоящими** факторами этой главы.

    Выдуманные не годятся: валидатор цитат отвергает абзац, который ссылается
    на то, чего в расчёте нет, писатель перегенерирует, и тест падает на
    закончившихся заготовках, а не на том, что проверяет.
    """
    from alma.ai import chapters as chapter_defs
    from alma.calc import compute

    result = compute(
        "compatibility", _birth(SOFIA), other=_birth(LUCAS), house_system="placidus"
    )
    offered = chapter_defs.relevant_factors(
        chapter_defs.find("compatibility", chapter), result.factors
    )
    # Три абзаца, а не два: платная глава короче трёх отвергается валидатором,
    # писатель уходит на перегенерацию, и тест падает на кончившихся
    # заготовках вместо того, что проверяет.
    return json.dumps(
        {
            "title": "What pulls",
            "teaser": "A line.",
            "advice": "Say the thing sooner.",
            "paragraphs": [
                {
                    "text": "The first paragraph, read from the chart.",
                    "factors": offered[:1],
                },
                {"text": "The second, from the same place.", "factors": offered[:1]},
                {"text": "And a third, which the length asks for.", "factors": offered[:1]},
            ],
        }
    )


def _read(api, headers, *, partner: str, chapter: str):
    return api.post(
        "/v1/readings",
        json={
            "system": "compatibility",
            "chapter": chapter,
            "partner_profile_id": partner,
        },
        headers=headers,
    )


# ══════════════════════════════════════════════════════════════════════════
#  Кредит подписчика
# ══════════════════════════════════════════════════════════════════════════

def test_credits_are_zero_without_a_subscription(store_api):
    headers = _headers(store_api)
    body = store_api.get("/v1/billing/credits", headers=headers).json()
    assert body["pair"] == {
        "granted": 0, "used": 0, "remaining": 0, "period_end": None,
    }


def test_a_subscriber_is_told_what_is_included(store_api, apple):
    headers = _headers(store_api)
    _subscribe(store_api, headers, apple)

    body = store_api.get("/v1/billing/credits", headers=headers).json()["pair"]
    assert body["granted"] == 1
    assert body["remaining"] == 1
    # Дата конца периода — то, чем экран P4 подписывает бейдж «входит в
    # подписку»; без неё «в этом месяце» пришлось бы считать на клиенте.
    assert body["period_end"] is not None


def test_the_first_pair_of_the_month_spends_the_credit(store_api, apple, scripted):
    """И превращается в обычный грант: отчёт остаётся навсегда."""
    headers = _headers(store_api)
    partner, _ = _profiles(store_api, headers)
    _subscribe(store_api, headers, apple)
    scripted.responses.append(_reply("friction"))

    response = _read(store_api, headers, partner=partner, chapter="friction")
    assert response.status_code == 200, response.text

    credits = store_api.get("/v1/billing/credits", headers=headers).json()["pair"]
    assert credits["used"] == 1
    assert credits["remaining"] == 0

    listed = store_api.get("/v1/pairs", headers=headers).json()
    assert [row["profile_id"] for row in listed] == [partner]
    assert listed[0]["source"] == "credit"
    assert listed[0]["name"] == "Katya"


def test_the_second_pair_of_the_month_is_offered_at_a_price(store_api, apple, scripted):
    """**А7, случай 4, на HTTP.** 402 приходит до генерации, а не после."""
    headers = _headers(store_api)
    first, _ = _profiles(store_api, headers)
    _subscribe(store_api, headers, apple)
    scripted.responses.append(_reply("friction"))
    assert _read(store_api, headers, partner=first, chapter="friction").status_code == 200

    second = store_api.post(
        "/v1/profiles",
        json={**SOFIA, "relation": "partner", "name": "Masha"},
        headers=headers,
    ).json()["id"]

    refused = _read(store_api, headers, partner=second, chapter="friction")

    assert refused.status_code == 402
    detail = refused.json()["detail"]
    # Отдельный код, а не общий `locked`: экран «купи подписку», показанный
    # подписчику, читается как поломка биллинга и кончается отменой.
    assert detail["error"] == "beyond_monthly_pair"
    assert detail["product"] == "pair.check"
    # Генерация не запускалась — заготовка осталась нетронутой.
    assert len(scripted.responses) == 0
    assert len(scripted.calls) == 1


def test_a_paid_pair_reads_every_chapter_without_touching_the_credit(
    store_api, apple, scripted
):
    """Четыре главы одного отчёта — одна проверка, а не четыре."""
    headers = _headers(store_api)
    partner, _ = _profiles(store_api, headers)
    _subscribe(store_api, headers, apple)

    scripted.responses.extend([_reply("friction"), _reply("together")])
    assert _read(store_api, headers, partner=partner, chapter="friction").status_code == 200
    assert _read(store_api, headers, partner=partner, chapter="together").status_code == 200

    credits = store_api.get("/v1/billing/credits", headers=headers).json()["pair"]
    assert credits["used"] == 1


def test_a_grandfathered_plan_is_not_counted_against_the_monthly_credit(store_api, scripted):
    """А6: старую подписку не переписывают задним числом.

    Легаси-`live` покрывал совместимость целиком и был продан до того, как «одна
    проверка в месяц» появилась на свете. Предъявить его владельцу пейволл —
    значит нарушить обещание в тот самый месяц, когда он решает, продлевать ли.
    """
    from datetime import timedelta

    from conftest import read_async

    headers = _headers(store_api)
    partner, _ = _profiles(store_api, headers)

    async def grandfather() -> None:
        from sqlalchemy import select

        from alma.auth import entitlements
        from alma.db.models import User
        from alma.db.session import session_factory

        async with session_factory()() as session:
            user = (await session.execute(select(User))).scalars().first()
            await entitlements.grant(
                session, user, system=entitlements.SCOPE_LIVE,
                kind="annual", subscription_id="legacy_1",
                duration=timedelta(days=365), source="paddle",
            )
            await session.commit()

    read_async(grandfather)
    scripted.responses.append(_reply("friction"))

    response = _read(store_api, headers, partner=partner, chapter="friction")

    assert response.status_code == 200, response.text
    credits = store_api.get("/v1/billing/credits", headers=headers).json()["pair"]
    assert credits == {"granted": 0, "used": 0, "remaining": 0, "period_end": None}


# ══════════════════════════════════════════════════════════════════════════
#  Кап бесплатных тизеров
# ══════════════════════════════════════════════════════════════════════════

def test_the_free_teaser_covers_one_new_person_a_month(store_api, scripted):
    """Решение владельца: **один** человек, не три.

    Второй новый человек в том же месяце получает не тизер, а предложение
    купить полный разбор — по А9 это замена, а не ошибка.
    """
    headers = _headers(store_api)
    first, _ = _profiles(store_api, headers)
    scripted.responses.append(_reply())
    assert _read(store_api, headers, partner=first, chapter="attraction").status_code == 200

    # Второго партнёра бесплатный слой сохранить не даёт, пока не куплена хотя
    # бы одна пара, — поэтому он появляется у аккаунта, который уже платил.
    from alma.billing import credits as pair_credits  # noqa: F401  (документирует связь)

    second = store_api.post(
        "/v1/profiles",
        json={**SOFIA, "relation": "partner", "name": "Masha"},
        headers=headers,
    )
    assert second.status_code == 402, "лестница партнёров не изменилась"


def test_a_teaser_already_written_is_never_taken_away(store_api, scripted):
    """Перечитывание не считается: текст на экране, за него ничего не просили."""
    headers = _headers(store_api)
    partner, _ = _profiles(store_api, headers)
    scripted.responses.append(_reply())

    assert _read(store_api, headers, partner=partner, chapter="attraction").status_code == 200
    again = _read(store_api, headers, partner=partner, chapter="attraction")
    assert again.status_code == 200
    # Второй раз модель не звали: глава уже написана.
    assert len(scripted.calls) == 1


def test_the_cap_moves_without_a_release(store_api, scripted):
    """Кап живёт в `Setting`, а не в коде: правка цифры не должна быть деплоем.

    Ноль — самая честная проверка механизма: он не «читается», а решает.
    """
    from conftest import read_async

    async def close_the_free_layer() -> None:
        from alma.db.models import Setting
        from alma.db.session import session_factory

        async with session_factory()() as session:
            session.add(Setting(key="pair.teaser_cap", value={"per_month": 0}))
            await session.commit()

    headers = _headers(store_api)
    partner, _ = _profiles(store_api, headers)
    read_async(close_the_free_layer)

    refused = _read(store_api, headers, partner=partner, chapter="attraction")

    assert refused.status_code == 402
    assert refused.json()["detail"]["error"] == "teaser_cap"
    assert refused.json()["detail"]["product"] == "pair.check"
    assert len(scripted.calls) == 0, "пейволл обязан стоять до генерации"


def test_a_subscriber_is_never_capped_on_teasers(store_api, apple, scripted):
    """Три цента против $9.99 в месяц — не тот риск, ради которого ставят стену."""
    from conftest import read_async

    async def close_the_free_layer() -> None:
        from alma.db.models import Setting
        from alma.db.session import session_factory

        async with session_factory()() as session:
            session.add(Setting(key="pair.teaser_cap", value={"per_month": 0}))
            await session.commit()

    headers = _headers(store_api)
    partner, _ = _profiles(store_api, headers)
    _subscribe(store_api, headers, apple)
    read_async(close_the_free_layer)
    scripted.responses.append(_reply())

    assert _read(store_api, headers, partner=partner, chapter="attraction").status_code == 200
