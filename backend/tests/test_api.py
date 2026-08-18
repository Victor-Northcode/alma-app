"""The HTTP surface, exercised the way a client actually uses it.

The tests that matter most here are not the happy paths — those fail loudly.
They are the ones where a mistake produces a *working* product that is subtly
wrong: a guest whose reading vanishes when they sign in, a paywall that leaks
the thing it is selling, a profile endpoint that lets one account read
another's birth data, a birth time silently invented for a chart that needs
one.
"""

from __future__ import annotations

from tests.conftest import LUCAS, SOFIA, run_async


# ── service ────────────────────────────────────────────────────────────────

def test_health_is_up(api):
    assert api.get("/health").json()["status"] == "ok"


def test_ready_reports_what_is_missing(api):
    body = api.get("/ready").json()
    assert body["checks"]["database"] is True
    assert body["checks"]["ephemeris"] is True
    assert isinstance(body["missing"], list)
    # No API keys in a test environment, so it must say so rather than claim
    # to be production-ready.
    assert body["production_ready"] is False


# ── the guest-first contract ───────────────────────────────────────────────

def test_a_first_request_creates_a_guest_and_hands_back_a_token(api):
    response = api.get("/v1/auth/session")
    assert response.status_code == 200
    body = response.json()
    assert body["is_guest"] is True
    assert body["token"]
    assert response.headers.get("X-Alma-Token")


def test_a_token_keeps_you_as_the_same_person(api, auth_headers):
    first = api.get("/v1/auth/session", headers=auth_headers).json()
    second = api.get("/v1/auth/session", headers=auth_headers).json()
    assert first["user_id"] == second["user_id"]


def test_no_token_means_a_different_person_each_time(api):
    first = api.get("/v1/auth/session").json()
    second = api.get("/v1/auth/session").json()
    assert first["user_id"] != second["user_id"]


def test_a_forged_token_is_treated_as_a_new_visitor_not_an_error(api):
    """A sign-in wall on a bad cookie is a sign-in wall on the front page."""
    response = api.get("/v1/auth/session", headers={"Authorization": "Bearer nonsense"})
    assert response.status_code == 200
    assert response.json()["is_guest"] is True


def test_a_token_signed_with_another_secret_is_refused(api, monkeypatch):
    import jwt

    forged = jwt.encode({"sub": "someone", "exp": 9999999999, "iss": "alma"}, "wrong", algorithm="HS256")
    body = api.get("/v1/auth/session", headers={"Authorization": f"Bearer {forged}"}).json()
    assert body["user_id"] != "someone"


# ── profiles ───────────────────────────────────────────────────────────────

def test_saving_and_reading_back_a_birth(api, auth_headers):
    created = api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    assert created.status_code == 201
    profile = created.json()
    assert profile["birth_time"] == "04:20"
    assert profile["is_self"] is True

    listed = api.get("/v1/profiles", headers=auth_headers).json()
    assert [p["id"] for p in listed] == [profile["id"]]


def test_saving_a_second_self_replaces_the_first(api, auth_headers):
    """Two selves means every later reading has to guess which person."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    api.post(
        "/v1/profiles",
        json={**SOFIA, "birth_time": "09:00", "is_self": True},
        headers=auth_headers,
    )

    selves = [p for p in api.get("/v1/profiles", headers=auth_headers).json() if p["is_self"]]
    assert len(selves) == 1
    assert selves[0]["birth_time"] == "09:00"


def test_a_second_birth_saved_without_saying_whose_it_is_is_not_yours(api, auth_headers):
    """`is_self` defaulted to True, and a second self *deletes* the first.

    So a client that added a partner and forgot the flag destroyed the account
    owner's own chart, and every reading keyed to it, without an error. The
    first birth an account saves is obviously theirs; after that, claiming to
    be them has to be said out loud.
    """
    mine = api.post("/v1/profiles", json=SOFIA, headers=auth_headers).json()
    assert mine["is_self"] is True

    partner = api.post(
        "/v1/profiles", json={**LUCAS, "relation": "partner"}, headers=auth_headers
    ).json()
    assert partner["is_self"] is False

    saved = api.get("/v1/profiles", headers=auth_headers).json()
    assert [p["id"] for p in saved if p["is_self"]] == [mine["id"]]
    assert len(saved) == 2


def test_another_account_cannot_read_your_profile(api, auth_headers):
    mine = api.post("/v1/profiles", json=SOFIA, headers=auth_headers).json()

    stranger = api.get("/v1/auth/session").json()["token"]
    response = api.get(
        f"/v1/profiles/{mine['id']}", headers={"Authorization": f"Bearer {stranger}"}
    )
    assert response.status_code == 404


def test_a_missing_profile_and_someone_elses_look_identical(api, auth_headers):
    """Different answers would turn this route into an id enumerator."""
    mine = api.post("/v1/profiles", json=SOFIA, headers=auth_headers).json()
    stranger = {"Authorization": f"Bearer {api.get('/v1/auth/session').json()['token']}"}

    theirs = api.get(f"/v1/profiles/{mine['id']}", headers=stranger)
    nowhere = api.get("/v1/profiles/does-not-exist", headers=stranger)
    assert theirs.status_code == nowhere.status_code == 404
    assert theirs.json() == nowhere.json()


def test_your_own_birth_data_cannot_be_deleted_by_accident(api, auth_headers):
    mine = api.post("/v1/profiles", json=SOFIA, headers=auth_headers).json()
    response = api.delete(f"/v1/profiles/{mine['id']}", headers=auth_headers)
    assert response.status_code == 409


def test_a_second_person_can_be_added_and_removed(api, auth_headers):
    partner = api.post(
        "/v1/profiles",
        json={**LUCAS, "is_self": False, "relation": "partner"},
        headers=auth_headers,
    ).json()
    assert api.delete(f"/v1/profiles/{partner['id']}", headers=auth_headers).status_code == 204


def test_a_guest_is_minted_speaking_the_phones_language(api):
    """`Accept-Language` on the minting request decides `user.locale`.

    Before this, every guest started life in English and stayed there until
    the client's fire-and-forget locale PATCH landed — so the receipt, the
    daily fallback and every refusal built on `user.locale` spoke English
    during exactly the session in which a new reader meets them.
    """
    minted = api.get(
        "/v1/auth/session", headers={"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8"}
    ).json()
    assert minted["locale"] == "ru"

    bare = api.get("/v1/auth/session").json()
    assert bare["locale"] == "en"


def test_the_partner_ladder_refuses_in_the_language_of_the_request(api, auth_headers):
    """The refusal speaks the request's language, not the account's.

    A fresh guest's `user.locale` is the minting default until the client's
    fire-and-forget locale PATCH lands, and the partner-limit 402 was the one
    error built on `user.locale` alone — so a Russian reader adding their
    second person could meet an English sentence at the exact moment they are
    being sold to.
    """
    from alma.i18n import replies as i18n_replies

    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    first = api.post(
        "/v1/profiles",
        json={**LUCAS, "is_self": False, "relation": "partner", "locale": "ru"},
        headers=auth_headers,
    )
    assert first.status_code == 201, "the first saved comparison is free"

    second = api.post(
        "/v1/profiles",
        json={**LUCAS, "name": "Second", "is_self": False, "locale": "ru"},
        headers=auth_headers,
    )
    assert second.status_code == 402
    detail = second.json()["detail"]
    assert detail["error"] == "partner_limit"
    assert detail["limit"] == 1
    assert detail["message"] == i18n_replies.reply("partner_limit", "ru")


# ── input validation ───────────────────────────────────────────────────────

def test_an_unknown_timezone_is_refused(api, auth_headers):
    """A wrong zone silently produces a chart in UTC that looks correct."""
    response = api.post(
        "/v1/profiles", json={**SOFIA, "timezone": "Middle/Earth"}, headers=auth_headers
    )
    assert response.status_code == 422
    assert "timezone" in response.text


def test_an_empty_birth_time_means_unknown_not_midnight(api, auth_headers):
    profile = api.post(
        "/v1/profiles", json={**SOFIA, "birth_time": ""}, headers=auth_headers
    ).json()
    assert profile["birth_time"] is None


def test_a_malformed_birth_time_is_refused(api, auth_headers):
    for bad in ("25:00", "4:20", "04:60", "morning"):
        response = api.post(
            "/v1/profiles", json={**SOFIA, "birth_time": bad}, headers=auth_headers
        )
        assert response.status_code == 422, f"{bad!r} was accepted"


def test_a_date_outside_the_ephemeris_is_refused(api, auth_headers):
    response = api.post(
        "/v1/profiles", json={**SOFIA, "birth_date": "1804-01-01"}, headers=auth_headers
    )
    assert response.status_code == 422


# ── the systems ────────────────────────────────────────────────────────────

def test_a_natal_chart_can_be_computed_from_the_body_alone(api, auth_headers):
    response = api.post("/v1/systems/natal", json={"birth": SOFIA}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["sun_sign"] == "Pisces"
    assert body["data"]["rising_sign"]
    assert body["provenance"]["ephemeris"]


def test_a_saved_profile_is_used_when_no_birth_is_sent(api, auth_headers):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    body = api.post("/v1/systems/natal", json={}, headers=auth_headers).json()
    assert body["data"]["sun_sign"] == "Pisces"


def test_asking_without_any_birth_data_says_so(api, auth_headers):
    response = api.post("/v1/systems/natal", json={}, headers=auth_headers)
    assert response.status_code == 400
    assert "birth" in response.text


def test_no_system_comes_back_whole_without_paying_for_it(api, auth_headers):
    """Numerology and the birth card used to be free in their entirety.

    They are not any more: whole free systems were fourteen written chapters
    given away on the most expensive model. What is still free is every
    *calculation* and one sample chapter per system.
    """
    for system in ("numerology", "birth-card"):
        body = api.post(f"/v1/systems/{system}", json={"birth": SOFIA}, headers=auth_headers).json()
        assert body["access"]["allowed"] is False, f"{system} is being given away"
        # The *chapters* are what is withheld; the numbers underneath them are
        # free, which is what the next test asserts.
        assert body["locked"] is True


def test_a_locked_system_still_shows_its_numbers(api, auth_headers):
    """The two that regressed the day the free systems went away.

    Neither had a `PREVIEW_FIELDS` entry, because neither needed one while it
    was free — so `_respond` trimmed their `data` against an empty tuple and a
    free reader got `{}`. That is the first thing a visitor sees after the
    quiz: their life path number and their card. It costs us nothing to
    compute and it is the whole argument for the paid reading.
    """
    numerology = api.post(
        "/v1/systems/numerology", json={"birth": SOFIA}, headers=auth_headers
    ).json()
    assert numerology["locked"] is True
    assert isinstance(numerology["data"]["life_path"], int)
    # The pinnacles and the personal year are calculated too, so they arrive
    # as well. What is not here is a written word about any of them.
    assert "pinnacles" in numerology["data"]

    card = api.post(
        "/v1/systems/birth-card", json={"birth": SOFIA}, headers=auth_headers
    ).json()
    assert card["locked"] is True
    assert card["data"]["personality"]["name"]
    assert "soul" in card["data"], "the Soul Card is arithmetic; its chapter is the product"


def test_a_locked_system_gives_away_its_whole_calculation(api, auth_headers):
    """The promise, asserted as a promise: every calculation is free.

    This replaces a test over a whitelist. The whitelist was the defect — it
    trimmed a locked natal chart to three sign names and a moon phase while the
    landing page, the pricing block and the hero all said the calculation was
    free, in six languages. A reader who is shown a sun sign has not been shown
    a calculation.

    Stated over `SYSTEMS` so the ninth system cannot ship trimmed, and asserting
    the two halves that matter: the arithmetic arrives, and the writing does not.
    """
    from alma.calc.contract import SYSTEMS

    for system in SYSTEMS:
        if system == "compatibility":
            continue  # needs a second person; covered by its own test
        body = api.post(
            f"/v1/systems/{system}", json={"birth": SOFIA}, headers=auth_headers
        ).json()
        assert body["locked"] is True, f"{system} should be locked for this account"
        assert body["data"], f"{system} answered a free reader with nothing"
        assert body["factors"], (
            f"{system} withheld its factors — those are the arithmetic the "
            "writer reads from, not the writing"
        )


def test_a_locked_natal_chart_is_a_whole_chart(api, auth_headers):
    """The chart is the argument for the reading, so it cannot be the paywall.

    This asserted the opposite until today: no factors, no aspects, no houses,
    no placements — a sun sign and a moon phase. That is the shape App Review's
    Guideline 4.3(b) rejects, because a sign name with nothing under it is
    indistinguishable from the horoscope apps the guideline exists to refuse.
    The houses and the aspects, with their orbs, are the proof that something
    was computed rather than looked up.
    """
    body = api.post("/v1/systems/natal", json={"birth": SOFIA}, headers=auth_headers).json()
    assert body["access"]["allowed"] is False
    assert body["locked"] is True

    assert body["data"]["sun_sign"] == "Pisces"
    for computed in ("aspects", "houses", "placements"):
        assert computed in body["data"], f"{computed} is arithmetic and is not for sale"
    assert body["factors"], "the factor list is what the writer reads from, not the writing"


def test_locked_means_the_writing_is_withheld_and_nothing_else(api, auth_headers):
    """What the lock actually buys, stated once.

    A locked system answers with everything it computed. The 41 written
    chapters live behind `POST /v1/readings`, which checks the same
    entitlement — so this asserts the two ends of the same rule.

    **Оба конца теперь отвечают одинаково — 200 с флагом `locked`.** Раньше
    здесь стояло `refused.status_code in (402, 403)`, и расхождение было
    видно прямо в этом тесте: расчёт закрытой системы приходил как удача с
    флагом, а закрытая глава — как ошибка. Роутер глав перестал быть
    исключением из правила, которое `systems.py` держит с самого начала:
    «paywall's job is to sell the rest, and a blank page sells nothing».
    Ключа модели в тестах нет, поэтому открывающий абзац здесь пустой — стена
    от этого не перестаёт быть стеной.
    """
    for system in ("natal", "synthesis"):
        body = api.post(
            f"/v1/systems/{system}", json={"birth": SOFIA}, headers=auth_headers
        ).json()
        assert body["locked"] is True
        assert body["factors"], f"{system} withheld arithmetic it does not sell"

    # Профиль заводится намеренно — иначе тест доказывал бы отказ, который мог
    # бы прийти и от отсутствия анкеты.
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    refused = api.post(
        "/v1/readings", json={"system": "natal", "chapter": "love"}, headers=auth_headers
    ).json()
    assert refused["locked"] is True
    assert refused["reading"] is None, "the writing is what the lock is for"


def test_a_chart_without_a_birth_time_degrades_and_explains(api, auth_headers):
    body = api.post(
        "/v1/systems/natal", json={"birth": {**SOFIA, "birth_time": None}}, headers=auth_headers
    ).json()
    assert body["data"]["time_known"] is False
    assert body["data"]["rising_sign"] is None
    assert any("birth time" in reason for reason in body["unavailable"])


def test_systems_that_need_a_time_refuse_with_a_reason(api, auth_headers):
    for system in ("solar-return", "astrocartography"):
        response = api.post(
            f"/v1/systems/{system}",
            json={"birth": {**SOFIA, "birth_time": None}},
            headers=auth_headers,
        )
        assert response.status_code == 422
        assert response.json()["detail"]["error"] == "birth_time_required"


def test_compatibility_needs_a_second_person(api, auth_headers):
    response = api.post("/v1/systems/compatibility", json={"birth": SOFIA}, headers=auth_headers)
    assert response.status_code == 400


def test_compatibility_works_with_two_people(api, auth_headers):
    body = api.post(
        "/v1/systems/compatibility",
        json={"birth": SOFIA, "other": LUCAS},
        headers=auth_headers,
    ).json()
    assert set(body["data"]["scores"]) == {"attraction", "warmth", "friction", "endurance"}


def test_transits_answer_with_dates(api, auth_headers):
    body = api.post(
        "/v1/systems/transits", json={"birth": SOFIA, "days": 90}, headers=auth_headers
    ).json()
    assert body["data"]["window"]["days"] == 90
    assert isinstance(body["data"]["active_count"], int)


def test_an_ambiguous_birth_time_asks_rather_than_guesses(api, auth_headers):
    """A DST overlap is two real instants an hour apart.

    Italy put the clocks back at 03:00 on 25 October 1998, so 02:30 that
    morning happened twice. Choosing one silently would bury a coin flip in a
    paid reading.
    """
    response = api.post(
        "/v1/systems/natal",
        json={
            "birth": {
                **SOFIA,
                "birth_date": "1998-10-25",
                "birth_time": "02:30",
            }
        },
        headers=auth_headers,
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "ambiguous_birth_time"
    assert {option["choice"] for option in detail["options"]} == {"earlier", "later"}


def test_the_ambiguity_carries_what_the_question_needs_to_be_answerable(
    api, auth_headers
):
    """Two identical times are not a choice — the names of the clock are.

    The fork screen asks «which of the two 02:30 is yours?», and a person can
    only answer it if the two are told apart: CEST an hour before CET, on the
    night the clocks went back. None of that can be assembled on the phone —
    the clients carry no timezone database — so the 409 has to state it.
    """
    detail = api.post(
        "/v1/systems/natal",
        json={
            "birth": {**SOFIA, "birth_date": "1998-10-25", "birth_time": "02:30"}
        },
        headers=auth_headers,
    ).json()["detail"]

    assert detail["timezone"] == SOFIA["timezone"]
    assert detail["transition_local_date"] == "1998-10-25"
    options = {option["choice"]: option for option in detail["options"]}
    assert options["earlier"]["abbreviation"] == "CEST"
    assert options["later"]["abbreviation"] == "CET"
    assert options["earlier"]["offset_hours"] == 2.0
    assert options["later"]["offset_hours"] == 1.0


def test_the_ambiguity_can_then_be_resolved(api, auth_headers):
    payload = {
        **SOFIA, "birth_date": "1998-10-25", "birth_time": "02:30", "on_ambiguous": "earlier"
    }
    response = api.post("/v1/systems/natal", json={"birth": payload}, headers=auth_headers)
    assert response.status_code == 200


def test_the_two_ambiguous_choices_are_an_hour_and_a_chart_apart(api, auth_headers):
    """The reason the question is worth asking, stated as an assertion."""

    def chart(choice):
        return api.post(
            "/v1/systems/natal",
            json={
                "birth": {
                    **SOFIA, "birth_date": "1998-10-25",
                    "birth_time": "02:30", "on_ambiguous": choice,
                }
            },
            headers=auth_headers,
        ).json()

    earlier, later = chart("earlier"), chart("later")
    gap_hours = (
        later["provenance"]["julian_day"] - earlier["provenance"]["julian_day"]
    ) * 24
    # Floating-point Julian days: an hour is 1/24, which does not land exactly.
    assert abs(gap_hours - 1.0) < 1e-6, f"the two readings are {gap_hours:.4f} hours apart"

    # An hour of birth time is roughly fifteen degrees of Ascendant, which is
    # frequently a different rising sign — never a rounding difference.
    assert earlier["data"]["rising_sign"] or later["data"]["rising_sign"]
    assert earlier["provenance"]["julian_day"] != later["provenance"]["julian_day"]


# ── the hub ────────────────────────────────────────────────────────────────

def test_the_hub_describes_every_system(api, auth_headers):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    body = api.get("/v1/systems/hub", headers=auth_headers).json()
    assert len(body["systems"]) == 8
    assert body["has_birth_data"] is True
    assert body["birth_time_known"] is True


def test_the_hub_asks_for_a_birth_time_when_there_is_none(api, auth_headers):
    api.post("/v1/profiles", json={**SOFIA, "birth_time": None}, headers=auth_headers)
    body = api.get("/v1/systems/hub", headers=auth_headers).json()
    states = {s["slug"]: s["status"] for s in body["systems"]}
    assert states["solar-return"] == "needs-time"
    assert states["astrocartography"] == "needs-time"


def test_the_hub_asks_for_a_second_person_for_compatibility(api, auth_headers):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    states = {
        s["slug"]: s["status"] for s in api.get("/v1/systems/hub", headers=auth_headers).json()["systems"]
    }
    assert states["compatibility"] == "add-person"


# ── places ─────────────────────────────────────────────────────────────────

def test_place_search_over_http(api):
    results = api.get("/v1/places/search", params={"q": "milan"}).json()
    assert results and results[0]["name"] == "Milan"
    assert results[0]["timezone"] == "Europe/Rome"


def test_place_search_needs_something_to_search_for(api):
    assert api.get("/v1/places/search", params={"q": ""}).status_code == 422


def test_timezone_lookup_answers_for_a_date(api):
    body = api.get(
        "/v1/places/timezone",
        params={"latitude": 45.4642, "longitude": 9.19, "on": "1998-03-14"},
    ).json()
    assert body["timezone"] == "Europe/Rome"
    assert body["offset"] == "+01:00"


def test_timezone_lookup_uses_the_rules_of_that_year(api):
    summer = api.get(
        "/v1/places/timezone",
        params={"latitude": -23.55, "longitude": -46.63, "on": "2018-01-15"},
    ).json()
    later = api.get(
        "/v1/places/timezone",
        params={"latitude": -23.55, "longitude": -46.63, "on": "2020-01-15"},
    ).json()
    assert summer["offset"] != later["offset"], "Brazil dropped daylight saving in 2019"


# ── account ────────────────────────────────────────────────────────────────

def test_the_export_survives_a_conversation(api, auth_headers, monkeypatch):
    """Экспорт ломался у каждого, у кого есть хоть одна беседа.

    `accounts.export` читал `thread.messages` — ленивую связь — в сборке
    словаря, а ленивая загрузка в asyncio это `MissingGreenlet`, то есть 500.
    Маршрут выгрузки данных обязателен для обоих магазинов и это статья 15
    GDPR; он падал ровно у тех, у кого есть что выгружать.

    **Почему это не поймали два теста рядом.** Оба экспортируют аккаунт без
    единой беседы, и ветка со связью просто не выполнялась: тест проходил не
    потому, что код верен, а потому, что до кода не доходило. Здесь беседа
    заводится до выгрузки — и падение возвращается, если `selectinload` уйдёт.
    """
    from alma.db import session as db
    from alma.db.models import ChatMessage, ChatThread, User
    from sqlalchemy import select

    account = api.get("/v1/account", headers=auth_headers).json()

    async def _write() -> None:
        async with db.session_scope() as session:
            user = (
                await session.execute(select(User).where(User.id == account["id"]))
            ).scalar_one()
            thread = ChatThread(user_id=user.id, title="о Луне")
            session.add(thread)
            await session.flush()
            session.add(ChatMessage(thread_id=thread.id, role="user", body="что с Луной?"))
            session.add(ChatMessage(thread_id=thread.id, role="alma", body="она в Рыбах."))

    run_async(_write)

    export = api.get("/v1/account/export", headers=auth_headers)
    assert export.status_code == 200, export.text
    conversations = export.json()["conversations"]
    assert len(conversations) == 1
    assert [m["body"] for m in conversations[0]["messages"]] == [
        "что с Луной?",
        "она в Рыбах.",
    ]


def test_a_guest_can_export_and_delete(api, auth_headers):
    """This test used to assert the exact opposite, and the reversal is the point.

    Its old name was `test_a_guest_cannot_export_or_delete` and it pinned two
    401s. That looked like a sensible gate — export and delete are the two
    routes that need to be sure who is asking — and it was, until you notice
    what a guest account holds. Alma mints one on the first request and the
    journey writes a birth date and full-precision birth coordinates into it
    before a sign-in screen has ever been shown. So the account being refused
    was the one holding the most sensitive data in the product, and the price
    of removing that data was handing over an email address we did not have.

    Google Play requires an in-app route to account deletion from any app that
    creates an account, and "create another kind of account first" is not one.
    The confirmation is kept and made answerable: a guest types their own
    account id, which they have and a stranger does not.
    """
    account = api.get("/v1/account", headers=auth_headers).json()
    assert account["is_guest"] is True

    assert api.get("/v1/account/export", headers=auth_headers).status_code == 200

    wrong = api.post(
        "/v1/account/delete", json={"confirm": "x"}, headers=auth_headers
    )
    assert wrong.status_code == 400, "the confirmation still has to match"

    deleted = api.post(
        "/v1/account/delete", json={"confirm": account["id"]}, headers=auth_headers
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json() == {"deleted": True}

    # And the token that was minted for it is now a token for nothing.
    assert api.get("/v1/account", headers=auth_headers).status_code == 410


def test_the_account_route_describes_the_current_person(api, auth_headers):
    body = api.get("/v1/account", headers=auth_headers).json()
    assert body["is_guest"] is True
    # Nothing is unlocked until something is bought — "unlocked" means
    # written interpretation, which is the only thing that is ever sold.
    assert body["unlocked"] == []


def test_the_locale_can_be_changed(api, auth_headers):
    assert api.patch("/v1/account", json={"locale": "it"}, headers=auth_headers).json()["locale"] == "it"
    assert api.get("/v1/account", headers=auth_headers).json()["locale"] == "it"


# ── the magic-link flow, end to end ────────────────────────────────────────

def _request_link(api, headers, email="sofia@example.com"):
    response = api.post("/v1/auth/magic-link", json={"email": email}, headers=headers)
    assert response.status_code == 202
    body = response.json()
    # No mail provider in tests, so the link comes back in the response.
    # Production never reaches that branch — see the router.
    assert body["sent"] is True
    return body["debug_token"]


def test_a_magic_link_signs_you_in_and_keeps_your_work(api, auth_headers):
    """The whole point of the guest-first design, exercised over HTTP."""
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    guest_id = api.get("/v1/auth/session", headers=auth_headers).json()["user_id"]

    token = _request_link(api, auth_headers)
    signed_in = api.post(
        "/v1/auth/magic-link/consume", json={"token": token}, headers=auth_headers
    ).json()

    assert signed_in["is_guest"] is False
    assert signed_in["email"] == "sofia@example.com"
    assert signed_in["user_id"] == guest_id, "signing in should not have created a new person"

    after = {"Authorization": f"Bearer {signed_in['token']}"}
    profiles = api.get("/v1/profiles", headers=after).json()
    assert len(profiles) == 1 and profiles[0]["birth_time"] == "04:20"


def test_a_magic_link_works_only_once(api, auth_headers):
    token = _request_link(api, auth_headers)
    first = api.post("/v1/auth/magic-link/consume", json={"token": token}, headers=auth_headers)
    second = api.post("/v1/auth/magic-link/consume", json={"token": token}, headers=auth_headers)
    assert first.status_code == 200
    assert second.status_code == 400
    assert "already been used" in second.text


def test_an_invented_magic_link_is_refused(api, auth_headers):
    response = api.post(
        "/v1/auth/magic-link/consume", json={"token": "x" * 40}, headers=auth_headers
    )
    assert response.status_code == 400


def test_the_magic_link_endpoint_does_not_reveal_who_has_an_account(api, auth_headers):
    """Different answers here would let anyone enumerate our users."""
    known = api.post("/v1/auth/magic-link", json={"email": "sofia@example.com"}, headers=auth_headers)
    api.post("/v1/auth/magic-link/consume", json={"token": known.json()["debug_token"]}, headers=auth_headers)

    fresh = {"Authorization": f"Bearer {api.get('/v1/auth/session').json()['token']}"}
    again = api.post("/v1/auth/magic-link", json={"email": "sofia@example.com"}, headers=fresh)
    unknown = api.post("/v1/auth/magic-link", json={"email": "nobody@example.com"}, headers=fresh)

    assert again.status_code == unknown.status_code
    assert again.json()["sent"] == unknown.json()["sent"] is True


def test_signing_in_on_a_second_device_merges_rather_than_duplicates(api):
    """Guest on a phone, account on a laptop, one person."""
    laptop = {"Authorization": f"Bearer {api.get('/v1/auth/session').json()['token']}"}
    laptop_session = api.post(
        "/v1/auth/magic-link/consume",
        json={"token": _request_link(api, laptop)},
        headers=laptop,
    ).json()
    laptop = {"Authorization": f"Bearer {laptop_session['token']}"}
    api.post("/v1/profiles", json=SOFIA, headers=laptop)

    phone = {"Authorization": f"Bearer {api.get('/v1/auth/session').json()['token']}"}
    api.post("/v1/profiles", json={**LUCAS, "is_self": False}, headers=phone)
    phone_session = api.post(
        "/v1/auth/magic-link/consume",
        json={"token": _request_link(api, phone)},
        headers=phone,
    ).json()

    assert phone_session["user_id"] == laptop_session["user_id"]
    merged = {"Authorization": f"Bearer {phone_session['token']}"}
    profiles = api.get("/v1/profiles", headers=merged).json()
    assert len(profiles) == 2
    assert sum(1 for p in profiles if p["is_self"]) == 1


def test_a_bad_email_is_refused(api, auth_headers):
    response = api.post("/v1/auth/magic-link", json={"email": "not-an-address"}, headers=auth_headers)
    assert response.status_code == 422


def test_a_signed_in_user_can_export_and_delete(api, auth_headers):
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    session = api.post(
        "/v1/auth/magic-link/consume",
        json={"token": _request_link(api, auth_headers)},
        headers=auth_headers,
    ).json()
    signed_in = {"Authorization": f"Bearer {session['token']}"}

    export = api.get("/v1/account/export", headers=signed_in)
    assert export.status_code == 200
    assert "attachment" in export.headers["content-disposition"]
    assert len(export.json()["profiles"]) == 1

    wrong = api.post("/v1/account/delete", json={"confirm": "nope"}, headers=signed_in)
    assert wrong.status_code == 400

    gone = api.post(
        "/v1/account/delete", json={"confirm": "sofia@example.com"}, headers=signed_in
    )
    assert gone.status_code == 200

    after = api.get("/v1/auth/session", headers=signed_in)
    assert after.status_code == 410, "a deleted account must say so, not become a new guest"
