"""Вход по коду из письма — приложенческая половина magic-link.

Появился 24.08.2026 по слову владельца: у приложения нет deep-link, ссылка из
письма открывает веб, и входить с телефона было нечем. Код живёт в той же
таблице и по тем же правилам, что ссылка, — эти тесты стерегут ровно паритет:
всё, что обещано ссылке, обязано выполняться и для кода.
"""

from tests.test_api import SOFIA  # тот же тестовый человек, что во всех API-тестах


def _request_code(api, headers, email="sofia@example.com"):
    response = api.post("/v1/auth/magic-link", json={"email": email}, headers=headers)
    assert response.status_code == 202
    body = response.json()
    # Почтовика в тестах нет — код приезжает в ответе, как и debug_token.
    assert body["sent"] is True
    return body["debug_code"]


def test_the_code_signs_you_in_and_keeps_your_work(api, auth_headers):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    guest_id = api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]

    code = _request_code(api, auth_headers)
    assert len(code) == 6 and code.isdigit()

    signed_in = api.post(
        "/v1/auth/email-code/consume",
        json={"email": "sofia@example.com", "code": code},
        headers=auth_headers,
    ).json()

    assert signed_in["is_guest"] is False
    assert signed_in["email"] == "sofia@example.com"
    assert signed_in["user_id"] == guest_id, "вход не должен заводить нового человека"


def test_the_code_works_only_once(api, auth_headers):
    code = _request_code(api, auth_headers)
    body = {"email": "sofia@example.com", "code": code}
    first = api.post("/v1/auth/email-code/consume", json=body, headers=auth_headers)
    second = api.post("/v1/auth/email-code/consume", json=body, headers=auth_headers)
    assert first.status_code == 200
    assert second.status_code == 400
    assert "already been used" in second.text


def test_a_wrong_code_is_refused(api, auth_headers):
    code = _request_code(api, auth_headers)
    wrong = "000000" if code != "000000" else "000001"
    refused = api.post(
        "/v1/auth/email-code/consume",
        json={"email": "sofia@example.com", "code": wrong},
        headers=auth_headers,
    )
    assert refused.status_code == 400
    assert "not valid" in refused.text


def test_the_code_is_bound_to_its_email(api, auth_headers):
    """Шесть цифр ищутся только против СВОЕГО письма.

    Адрес вшит в хэш кода: тот же код с чужим адресом обязан быть отказом —
    иначе перебор шёл бы против всех ожидающих строк сразу.
    """
    code = _request_code(api, auth_headers)
    refused = api.post(
        "/v1/auth/email-code/consume",
        json={"email": "other@example.com", "code": code},
        headers=auth_headers,
    )
    assert refused.status_code == 400
    assert "not valid" in refused.text


def test_code_guessing_hits_a_ceiling(api, auth_headers):
    """Десять попыток в час с источника — дальше 429, а не тихий перебор."""
    _request_code(api, auth_headers)
    last = None
    for attempt in range(11):
        last = api.post(
            "/v1/auth/email-code/consume",
            json={"email": "sofia@example.com", "code": f"{attempt:06d}"},
            headers=auth_headers,
        )
        if last.status_code == 429:
            break
    assert last is not None and last.status_code == 429
