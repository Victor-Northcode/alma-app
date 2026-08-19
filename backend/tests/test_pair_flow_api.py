"""Флоу P4 сверху: кредит подписчика и стена свободного аккаунта, через HTTP.

`test_pair_credits.py` проверяет правила кредита как правила. Здесь — то, что
их **кто-то спрашивает**: что вторая проверка подписчика в одном цикле упирается
в 402 до генерации, что первая тратит включённую и превращается в обычный грант,
и что свободный аккаунт не получает про пару ни единого написанного слова.

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
#  Глава I пары — обычная закрытая глава
# ══════════════════════════════════════════════════════════════════════════
#
# Здесь стояли четыре теста про кап бесплатных тизеров: «один новый человек в
# месяц», «уже написанный тизер не отбирают», «кап меняется через `Setting`
# без релиза», «подписчика не капают». Механики больше нет — владелец,
# 17.08.2026: «тизер „Притяжение“ и глава I пары — одно и то же», — и вместе с
# ней ушли `pair.teaser_cap`, `TEASER_CAP_DEFAULT` и счётчик `pair_teaser`.
#
# Молча удалять их было бы неправильно: они защищали настоящие деньги, и то,
# что защищало, обязано быть проверено по-новому.
#
# Кап держал число **бесплатных генераций** в месяц. Теперь их ноль — владелец,
# 19.08.2026: «мы не даем бесплатно пару никакую все за деньги можно писать
# только имя», — и капу нечего считать: заходов в стену сколько угодно, стоят
# они ноль. Тесты ниже проверяют именно это, а не «сколько раз можно»:
# провайдер не позвался ни разу, окно абзацев не тронуто, подписчик проходит
# без стены.


def test_a_free_account_gets_a_price_and_not_one_written_word(store_api, scripted):
    """У пары бесплатного текста нет вообще — ни отчёта, ни открывающего абзаца.

    Тест назывался «свободный аккаунт получает начало главы пары и цену» и
    проверял ровно то, чего больше нет. Владелец, 19.08.2026: «мы не даем
    бесплатно пару никакую все за деньги можно писать только имя». Бесплатны
    расчёт синастрии и место под человека; любой написанный текст пары платный.

    **Проверяется не только пустое поле, но и молчание провайдера.** `opening:
    null` можно получить и потому, что модель отказала, — а это стоит трёх
    оплаченных попыток. Обещание здесь сильнее: генерации не случилось вовсе,
    и `scripted.calls` — единственное, что это доказывает.
    """
    headers = _headers(store_api)
    partner, _ = _profiles(store_api, headers)

    response = _read(store_api, headers, partner=partner, chapter="attraction")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["locked"] is True
    assert body["reading"] is None, "полный отчёт даром не отдаётся"
    assert body["product"] == "pair.check"
    assert body["opening"] is None, "написанного начала у пары нет"
    assert body["needs_partner"] is False, "человек назван — закрыто деньгами"
    assert scripted.calls == [], "модель не должна была позваться ни разу"


@pytest.mark.parametrize("chapter", ["attraction", "friction", "overlays", "together"])
def test_no_pair_chapter_writes_anything_for_free(store_api, scripted, chapter):
    """Все четыре, а не только глава I.

    Глава I была тизером и стоит отдельного теста выше; остальные три никогда
    ничего не обещали и всё равно писали абзац — тем же путём. Параметризация
    здесь ровно затем, чтобы пятая глава пары, добавленная завтра, не завела
    себе бесплатное начало молча.
    """
    headers = _headers(store_api)
    partner, _ = _profiles(store_api, headers)

    body = _read(store_api, headers, partner=partner, chapter=chapter).json()

    assert body["locked"] is True
    assert body["opening"] is None
    assert scripted.calls == []


def test_the_pair_wall_does_not_spend_the_monthly_opening_window(store_api, scripted):
    """Окно открывающих абзацев бережёт витрину натальной карты, а не пары.

    `_opening_allowance` — шестьдесят абзацев в месяц на аккаунт, последняя
    линия против петли «сменил дату рождения — пиши заново». Пара до неё больше
    не доходит, и это важно проверить счётчиком, а не только пустым полем:
    заходы в закрытые главы пары ничем не ограничены (человека заводят
    бесплатно), и если бы они тратили окно, то выедали бы его целиком — а
    расплачивался бы за это натальный экран, где абзац и правда продаёт.
    """
    from sqlalchemy import select

    from alma.db import session as db_session
    from alma.db.models import UsageCounter
    from conftest import read_async

    headers = _headers(store_api)
    partner, _ = _profiles(store_api, headers)

    for _ in range(3):
        _read(store_api, headers, partner=partner, chapter="attraction")

    # `read_async`, а не `run_async`: соединения приложения принадлежат циклу
    # портального потока TestClient, и читать ими из тела теста — тот самый
    # «attached to a different loop» (см. довод в conftest).
    async def counters() -> list[str]:
        async with db_session.session_scope() as session:
            rows = await session.execute(
                select(UsageCounter).where(UsageCounter.metric == "opening")
            )
            return [row.id for row in rows.scalars()]

    assert read_async(counters) == [], "пара не тратит окно абзацев"
    assert scripted.calls == []


def test_a_subscriber_never_meets_the_wall_on_the_pair_chapter(store_api, apple, scripted):
    """Подписка покрывает совместимость целиком — стены на главе I нет.

    Тест назывался «подписчика не капают на тизерах» и проверял, что кап на
    бесплатные тизеры его не касается. Кап снят; обещание то же и проверяется
    прямее: подписчик получает не абзац с ценой, а главу.
    """
    headers = _headers(store_api)
    partner, _ = _profiles(store_api, headers)
    _subscribe(store_api, headers, apple)
    scripted.responses.append(_reply())

    response = _read(store_api, headers, partner=partner, chapter="attraction")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("locked") is not True
    assert body["reading"]["body"]


def test_paid_pair_report_locks_the_partner_birth(api, auth_headers):
    """Одна покупка — один человек: рождение под грантом не переписывается.

    До этой правки грант пары назывался профилем, а не рождением, и профиль
    можно было править. Значит одна проверка за $4.99 (или одна включённая в
    подписку) превращалась в сколько угодно отчётов: подменил дату и место —
    получил другого человека под тем же грантом, и каждый такой запрос стоил
    полной генерации, самой дорогой в продукте.
    """
    from sqlalchemy import select

    from alma.auth import entitlements
    from alma.db import session as db_session
    from alma.db.models import User
    from conftest import run_async

    partner = api.post("/v1/profiles", headers=auth_headers, json={
        "name": "Партнёр", "birth_date": "1990-01-01",
        "latitude": 55.75, "longitude": 37.62, "timezone": "Europe/Moscow",
        "is_self": False,
    }).json()

    async def grant() -> None:
        async with db_session.session_scope() as session:
            user = (await session.execute(select(User).limit(1))).scalars().first()
            await entitlements.grant(
                session, user,
                system=entitlements.pair_system(partner["id"]),
                kind="consumable",
                scope=entitlements.SCOPE_PAIR,
                transaction_id="txn-lock-test",
                amount_cents=499, currency="USD", source="appstore",
            )

    # run_async ждёт функцию, а не готовую корутину: она вызывает её внутри
    # собственного цикла и закрывает движок вместе с ним.
    run_async(grant)

    moved = api.patch(f"/v1/profiles/{partner['id']}", headers=auth_headers, json={
        "name": "Партнёр", "birth_date": "1985-07-07",
        "latitude": 48.85, "longitude": 2.35, "timezone": "Europe/Paris",
        "is_self": False,
    })
    assert moved.status_code == 409
    assert moved.json()["detail"]["error"] == "birth_locked_by_purchase"

    # Имя менять по-прежнему можно: расчёт его не видит.
    renamed = api.patch(f"/v1/profiles/{partner['id']}", headers=auth_headers, json={
        "name": "Новое имя", "birth_date": "1990-01-01",
        "latitude": 55.75, "longitude": 37.62, "timezone": "Europe/Moscow",
        "is_self": False,
    })
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Новое имя"
