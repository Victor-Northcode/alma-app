"""Привязка покупки пары к человеку: `/billing/pair/intent`, `/verify`, `/bind`.

Расходуемый товар покупается многократно, значит одна и та же строка каталога в
двух покупках означает двух разных людей — и сервер обязан знать, каких. Здесь
проверяется ровно та граница, на которой это решается: **`profile_id` приходит
из нашей записи, сделанной до оплаты, и сверяется с токеном, который подписал
магазин.** Из тела `/verify` он не приходит никогда, и первый же тест ниже
пытается это сделать.

Фикстуры подписи взяты из `test_billing_appstore` намеренно: вторая копия
помощника, собирающего JWS, — это вторая вещь, которую придётся держать в
согласии с RFC 7515.
"""

from __future__ import annotations

import pytest
from conftest import LUCAS, SOFIA, read_async

from test_billing_appstore import (  # noqa: F401 - `apple` is a fixture
    BUNDLE,
    _notification,
    _sign,
    _transaction,
    apple,
)


@pytest.fixture
def store_api(api, monkeypatch):
    """The app with Apple configured as a processor it can talk to."""
    from alma import config as config_module

    monkeypatch.setenv("APPLE_BUNDLE_ID", BUNDLE)
    config_module.settings.cache_clear()
    yield api
    config_module.settings.cache_clear()


def _account(api) -> dict:
    return {"Authorization": f"Bearer {api.get('/v1/auth/session').json()['token']}"}


def _self_profile(api, headers, birth: dict = SOFIA) -> str:
    response = api.post("/v1/profiles", json={**birth, "is_self": True}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _partner(api, headers, birth: dict = LUCAS, name: str | None = None) -> str:
    payload = {**birth, "is_self": False, "relation": "partner"}
    if name:
        payload["name"] = name
    response = api.post("/v1/profiles", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _intent(api, headers, profile_id: str) -> dict:
    response = api.post(
        "/v1/billing/pair/intent", json={"profile_id": profile_id}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def _pair_transaction(apple, *, token: str | None, transaction_id: str) -> str:
    """Одна подписанная Apple покупка проверки пары.

    `type` — `Consumable`: именно он отличает расходуемую покупку от двери, и
    именно на нём держится то, что `subscription_id` у неё не появляется.
    """
    payload = _transaction(
        product="pair.check",
        transaction_id=transaction_id,
        kind="Consumable",
        price=4990,
    )
    if token is not None:
        payload["appAccountToken"] = token
    return _sign(payload, apple["key"], apple["chain"])


def _verify(api, headers, *, transaction: str, body: dict | None = None):
    return api.post(
        "/v1/billing/iap/verify",
        json={
            "platform": "appstore",
            "product": "pair.check",
            "transaction": transaction,
            **(body or {}),
        },
        headers=headers,
    )


def _pairs(api, headers) -> list[dict]:
    response = api.get("/v1/pairs", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


# ══════════════════════════════════════════════════════════════════════════
#  Подмена профиля — то, ради чего вся конструкция
# ══════════════════════════════════════════════════════════════════════════

def test_the_body_cannot_choose_whose_report_is_opened(store_api, apple):
    """**Главный тест файла.** `profile_id` в теле `/verify` не значит ничего.

    Тело запроса пишет приложение, приложение пересобирается, и `profile_id`
    оттуда открывал бы отчёт про любого человека, чей id удалось назвать —
    например, подсмотренный в чужой ссылке. Здесь покупка открыта для своей
    Кати, а тело называет профиль **чужого аккаунта**; грант обязан достаться
    Кате, а чужой профиль — остаться закрытым у обоих.
    """
    stranger = _account(store_api)
    _self_profile(store_api, stranger, LUCAS)
    theirs = _partner(store_api, stranger, SOFIA, name="Somebody else")

    headers = _account(store_api)
    _self_profile(store_api, headers)
    katya = _partner(store_api, headers, name="Katya")

    opened = _intent(store_api, headers, katya)
    token = _pair_transaction(
        apple, token=opened["app_account_token"], transaction_id="2000000600000001"
    )

    response = _verify(
        store_api, headers,
        transaction=token,
        # Клиент врёт двумя полями сразу: и профилем, и intent'ом.
        body={"profile_id": theirs, "intent_id": "made-up"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["profile_id"] == katya
    assert [row["profile_id"] for row in _pairs(store_api, headers)] == [katya]
    assert _pairs(store_api, stranger) == []


def test_a_second_partner_needs_a_second_purchase(store_api, apple):
    """Одна покупка — один человек. Иначе $4.99 открывают всех подряд."""
    headers = _account(store_api)
    _self_profile(store_api, headers)
    katya = _partner(store_api, headers, name="Katya")

    opened = _intent(store_api, headers, katya)
    _verify(
        store_api, headers,
        transaction=_pair_transaction(
            apple, token=opened["app_account_token"], transaction_id="2000000600000002"
        ),
    )

    # Второй партнёр появляется только после первой покупки — таков нынешний
    # бесплатный слой, — и это ровно тот случай, ради которого тест: человек с
    # двумя сохранёнными людьми и одной оплаченной парой.
    masha = _partner(store_api, headers, LUCAS, name="Masha")

    held = store_api.get("/v1/billing/entitlements", headers=headers).json()
    assert held["unlocked_pairs"] == [katya]
    assert masha not in held["unlocked_pairs"]
    # И система целиком не открывается: «совместимость» в общем списке означала
    # бы «про всех», а куплен один человек.
    assert "compatibility" not in held["unlocked"]


def test_another_account_cannot_claim_a_token_it_did_not_open(store_api, apple):
    """Токен не полномочие: он называет строку, у которой уже есть владелец."""
    first = _account(store_api)
    _self_profile(store_api, first)
    partner = _partner(store_api, first, name="Katya")
    opened = _intent(store_api, first, partner)

    second = _account(store_api)
    response = _verify(
        store_api, second,
        transaction=_pair_transaction(
            apple, token=opened["app_account_token"], transaction_id="2000000600000003"
        ),
    )

    # Деньги записаны на того, кто их заплатил, а грант не выписан никому:
    # ни чужому аккаунту (это была бы кража), ни владельцу intent'а (он не
    # платил). 202 — «мы приняли платёж и ждём, к кому его применить».
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "unbound"
    assert _pairs(store_api, second) == []
    assert _pairs(store_api, first) == []


def test_an_intent_refuses_a_profile_that_is_not_yours(store_api):
    """И отвечает так же, как на несуществующий, — иначе это перебор чужих id."""
    first = _account(store_api)
    _self_profile(store_api, first)
    partner = _partner(store_api, first)

    second = _account(store_api)
    stolen = store_api.post(
        "/v1/billing/pair/intent", json={"profile_id": partner}, headers=second
    )
    invented = store_api.post(
        "/v1/billing/pair/intent", json={"profile_id": "no-such-profile"}, headers=second
    )

    assert stolen.status_code == invented.status_code == 404
    assert stolen.json()["detail"] == invented.json()["detail"]


def test_an_intent_refuses_the_buyer_themselves(store_api):
    """Совместимость с самим собой — не товар, а описка в клиенте."""
    headers = _account(store_api)
    mine = _self_profile(store_api, headers)

    response = store_api.post(
        "/v1/billing/pair/intent", json={"profile_id": mine}, headers=headers
    )
    assert response.status_code == 404


# ══════════════════════════════════════════════════════════════════════════
#  Повтор
# ══════════════════════════════════════════════════════════════════════════

def test_a_replayed_pair_purchase_grants_once(store_api, apple):
    """StoreKit пере-доставляет незакрытые транзакции на каждом запуске.

    Для расходуемого товара это особенно важно: второй грант выглядел бы как
    вторая покупка, а вторая строка в `Purchase` — как выручка, которой не было.
    """
    from sqlalchemy import select

    from alma.db.models import Entitlement, Purchase
    from alma.db.session import session_factory

    headers = _account(store_api)
    _self_profile(store_api, headers)
    partner = _partner(store_api, headers)
    opened = _intent(store_api, headers, partner)
    token = _pair_transaction(
        apple, token=opened["app_account_token"], transaction_id="2000000600000004"
    )

    first = _verify(store_api, headers, transaction=token)
    second = _verify(store_api, headers, transaction=token)

    assert first.status_code == second.status_code == 200
    assert first.json()["status"].startswith("granted")
    assert second.json()["status"] == "already_claimed"

    async def counted() -> tuple[int, int]:
        async with session_factory()() as session:
            grants = (await session.execute(select(Entitlement))).scalars().all()
            money = (await session.execute(select(Purchase))).scalars().all()
            return len(grants), len(money)

    assert read_async(counted) == (1, 1)


def test_two_accounts_on_one_apple_id_and_the_first_one_wins(store_api, apple):
    """А7, случай 8. Безопасное направление — не выдать дважды."""
    first = _account(store_api)
    _self_profile(store_api, first)
    partner = _partner(store_api, first)
    opened = _intent(store_api, first, partner)
    token = _pair_transaction(
        apple, token=opened["app_account_token"], transaction_id="2000000600000005"
    )

    assert _verify(store_api, first, transaction=token).status_code == 200

    second = _account(store_api)
    answer = _verify(store_api, second, transaction=token)

    assert answer.status_code == 200
    assert answer.json()["status"] == "already_claimed"
    assert _pairs(store_api, second) == []
    assert len(_pairs(store_api, first)) == 1


# ══════════════════════════════════════════════════════════════════════════
#  Токена нет — деньги всё равно не теряются
# ══════════════════════════════════════════════════════════════════════════

def test_a_purchase_without_a_token_is_recorded_and_left_unbound(store_api, apple):
    """Старый клиент, сбой между intent'ом и листом — деньги записаны.

    202, а не ошибка: 4xx заставил бы честный клиент не финишировать
    транзакцию, а деньги уже списаны. Ответ означает «принято, к кому
    применить — решим следующим вызовом».
    """
    from sqlalchemy import select

    from alma.db.models import Purchase
    from alma.db.session import session_factory

    headers = _account(store_api)
    _self_profile(store_api, headers)
    _partner(store_api, headers)

    response = _verify(
        store_api, headers,
        transaction=_pair_transaction(
            apple, token=None, transaction_id="2000000600000006"
        ),
    )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "unbound"
    assert body["profile_id"] is None
    assert _pairs(store_api, headers) == []

    async def money() -> tuple[str, int]:
        async with session_factory()() as session:
            row = (
                await session.execute(
                    select(Purchase).where(
                        Purchase.transaction_id == "2000000600000006"
                    )
                )
            ).scalar_one()
            return row.status, row.amount_cents

    status, cents = read_async(money)
    # Деньги на месте и помечены так, что их можно найти запросом: платёж без
    # гранта и без статуса выглядел бы как обычная успешная продажа.
    assert status == "unbound"
    assert cents == 499

    # Повтор той же транзакции обязан отвечать так же. `already_claimed` с
    # кодом 200 сказал бы клиенту «отчёт открыт», а он не открыт — и человек
    # остался бы с оплаченной покупкой и без экрана, который её завершает.
    retry = _verify(
        store_api, headers,
        transaction=_pair_transaction(
            apple, token=None, transaction_id="2000000600000006"
        ),
    )
    assert retry.status_code == 202
    assert retry.json()["status"] == "unbound"


def test_bind_finishes_an_unbound_purchase(store_api, apple):
    headers = _account(store_api)
    _self_profile(store_api, headers)
    partner = _partner(store_api, headers, name="Katya")
    _verify(
        store_api, headers,
        transaction=_pair_transaction(
            apple, token=None, transaction_id="2000000600000007"
        ),
    )

    bound = store_api.post(
        "/v1/billing/pair/bind",
        json={"transaction": "2000000600000007", "profile_id": partner},
        headers=headers,
    )

    assert bound.status_code == 200, bound.text
    assert bound.json() == {
        "granted": True, "profile_id": partner, "status": "bound",
    }
    assert [row["profile_id"] for row in _pairs(store_api, headers)] == [partner]
    assert [row["source"] for row in _pairs(store_api, headers)] == ["purchase"]


def test_bind_is_idempotent_and_refuses_a_second_partner(store_api, apple):
    """Одна покупка — один отчёт. Второй партнёр по той же транзакции — 409."""
    headers = _account(store_api)
    _self_profile(store_api, headers)
    katya = _partner(store_api, headers, name="Katya")
    _verify(
        store_api, headers,
        transaction=_pair_transaction(
            apple, token=None, transaction_id="2000000600000008"
        ),
    )

    def bind(profile_id: str):
        return store_api.post(
            "/v1/billing/pair/bind",
            json={"transaction": "2000000600000008", "profile_id": profile_id},
            headers=headers,
        )

    assert bind(katya).status_code == 200
    # Повтор того же — не ошибка: клиент, ретраящий после таймаута, не должен
    # получать отказ за то, что первая попытка удалась.
    again = bind(katya)
    assert again.status_code == 200
    assert again.json()["status"] == "already_bound"

    masha = _partner(store_api, headers, LUCAS, name="Masha")
    stolen = bind(masha)
    assert stolen.status_code == 409
    assert stolen.json()["detail"]["error"] == "already_bound"
    assert len(_pairs(store_api, headers)) == 1


def test_bind_refuses_a_purchase_whose_money_came_back(store_api, apple):
    """Иначе непривязанная покупка — это бесплатный отчёт в один запрос:
    получить возврат в магазине, потом назвать партнёра."""
    from conftest import read_async

    headers = _account(store_api)
    _self_profile(store_api, headers)
    partner = _partner(store_api, headers)
    _verify(
        store_api, headers,
        transaction=_pair_transaction(
            apple, token=None, transaction_id="2000000600000012"
        ),
    )

    async def refund() -> None:
        from sqlalchemy import select

        from alma.db.models import Purchase, utcnow
        from alma.db.session import session_factory

        async with session_factory()() as session:
            row = (
                await session.execute(
                    select(Purchase).where(
                        Purchase.transaction_id == "2000000600000012"
                    )
                )
            ).scalar_one()
            row.refunded_cents = row.amount_cents
            row.refunded_at = utcnow()
            await session.commit()

    read_async(refund)

    response = store_api.post(
        "/v1/billing/pair/bind",
        json={"transaction": "2000000600000012", "profile_id": partner},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "refunded"
    assert _pairs(store_api, headers) == []


def test_bind_refuses_a_transaction_from_another_account(store_api, apple):
    first = _account(store_api)
    _self_profile(store_api, first)
    _partner(store_api, first)
    _verify(
        store_api, first,
        transaction=_pair_transaction(
            apple, token=None, transaction_id="2000000600000009"
        ),
    )

    second = _account(store_api)
    _self_profile(store_api, second, LUCAS)
    theirs = _partner(store_api, second, SOFIA)
    response = store_api.post(
        "/v1/billing/pair/bind",
        json={"transaction": "2000000600000009", "profile_id": theirs},
        headers=second,
    )

    assert response.status_code == 404
    assert _pairs(store_api, second) == []


# ══════════════════════════════════════════════════════════════════════════
#  Расхождение intent и токена: магазин прав
# ══════════════════════════════════════════════════════════════════════════

def test_the_store_wins_when_the_client_names_a_different_intent(store_api, apple):
    """Начал покупку для Маши, свернул приложение, начал для Кати.

    Оплатилась та, чей токен уехал в магазин. Наша «последняя открытая» —
    догадка, подписанный пейлоад — факт.
    """
    headers = _account(store_api)
    _self_profile(store_api, headers)
    katya = _partner(store_api, headers, name="Katya")
    first = _intent(store_api, headers, katya)
    _verify(
        store_api, headers,
        transaction=_pair_transaction(
            apple, token=first["app_account_token"], transaction_id="2000000600000010"
        ),
    )
    masha = _partner(store_api, headers, LUCAS, name="Masha")

    # Два живых intent'а: последним открыт Катин, а уехал в магазин — Машин.
    for_masha = _intent(store_api, headers, masha)
    for_katya = _intent(store_api, headers, katya)

    response = _verify(
        store_api, headers,
        transaction=_pair_transaction(
            apple, token=for_masha["app_account_token"],
            transaction_id="2000000600000011",
        ),
        body={"intent_id": for_katya["intent_id"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["profile_id"] == masha
    assert sorted(row["profile_id"] for row in _pairs(store_api, headers)) == sorted(
        [katya, masha]
    )


def test_a_token_we_never_issued_grants_nothing(store_api, apple):
    """Подпись Apple настоящая, токен — выдуманный. Грант не выписывается."""
    headers = _account(store_api)
    _self_profile(store_api, headers)
    _partner(store_api, headers)

    response = _verify(
        store_api, headers,
        transaction=_pair_transaction(
            apple,
            token="11111111-2222-4333-8444-555555555555",
            transaction_id="2000000600000011",
        ),
    )

    assert response.status_code == 202
    assert response.json()["status"] == "unbound"
    assert _pairs(store_api, headers) == []


# ══════════════════════════════════════════════════════════════════════════
#  Токен как таковой
# ══════════════════════════════════════════════════════════════════════════

def test_an_intent_opened_as_a_guest_survives_signing_in(store_api, apple):
    """А7, случай 11, с той стороны, о которой легко забыть.

    Приложение просит зарегистрироваться **перед** покупкой, чтобы покупка не
    потерялась, — значит «открыл intent гостем, вошёл, оплатил» это не редкость,
    а обычный порядок. Если `merge` не перенесёт intent, токен найдёт строку с
    чужим `user_id`, и оплаченный отчёт уйдёт в «непривязанные».
    """
    from conftest import read_async

    guest = _account(store_api)
    _self_profile(store_api, guest)
    partner = _partner(store_api, guest, name="Katya")
    opened = _intent(store_api, guest, partner)

    async def sign_in() -> None:
        from sqlalchemy import select

        from alma.auth import accounts
        from alma.db.models import User
        from alma.db.session import session_factory

        async with session_factory()() as session:
            source = (await session.execute(select(User))).scalars().first()
            target = await accounts.create_guest(session)
            target.email = "her@example.com"
            await accounts.merge(session, source=source, target=target)
            await session.commit()

    read_async(sign_in)

    # Тот же токен, что уехал в магазин до входа в аккаунт, — и он обязан
    # по-прежнему называть того же партнёра.
    signed_in = _account(store_api)
    response = _verify(
        store_api, signed_in,
        transaction=_pair_transaction(
            apple, token=opened["app_account_token"], transaction_id="2000000600000013"
        ),
    )
    # Аккаунт из фикстуры — третий, не тот, в который влили; проверяем главное:
    # intent переехал и остался связанным со своим владельцем, а не потерялся.
    assert response.status_code in (200, 202)

    async def owner_of_the_intent() -> tuple[str, str]:
        from sqlalchemy import select

        from alma.db.models import PairIntent, User
        from alma.db.session import session_factory

        async with session_factory()() as session:
            intent = (await session.execute(select(PairIntent))).scalars().one()
            merged = (
                await session.execute(select(User).where(User.email == "her@example.com"))
            ).scalars().one()
            return intent.user_id, merged.id

    holder, merged_id = read_async(owner_of_the_intent)
    assert holder == merged_id, "intent остался на гостевой строке"


def test_the_token_is_a_uuid_apple_will_accept():
    """Apple принимает в `appAccountToken` только UUID; иначе StoreKit
    откажет в момент оплаты, а не при сборке."""
    import uuid

    from alma.billing.pairs import token_for

    value = token_for("intent-id")
    parsed = uuid.UUID(value)
    assert str(parsed) == value
    assert parsed.version == 4


def test_the_token_is_the_same_every_time_for_one_intent():
    """Иначе восстановить связь можно было бы только из строки, и её потеря
    означала бы потерянную покупку."""
    from alma.billing.pairs import token_for

    assert token_for("a") == token_for("a")
    assert token_for("a") != token_for("b")
