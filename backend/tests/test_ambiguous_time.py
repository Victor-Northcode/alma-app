"""Развилка перевода часов: что именно узнаёт клиент.

Экран `s38` дизайн-проекта спрашивает «в ту ночь 02:30 было дважды — какие
ваши?». Вопрос осмыслен только вместе с тем, чем эти два раза отличаются:
именами, которые часы носили в ту ночь, и датой перевода. Ни того ни другого
телефон посчитать не может — базы часовых поясов у него нет.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alma.calc.service import AmbiguousBirthTime, ambiguity_detail
from alma.engine.timeutil import resolve


def raise_at(*, year, month, day, hour, minute, tz_name) -> AmbiguousBirthTime:
    with pytest.raises(AmbiguousBirthTime) as caught:
        resolve(
            year=year, month=month, day=day, hour=hour, minute=minute, tz_name=tz_name
        )
    return caught.value


def test_berlin_1992_is_the_night_the_design_draws():
    """Тот самый случай с макета: 27 сентября 1992, CEST против CET."""
    detail = ambiguity_detail(
        raise_at(year=1992, month=9, day=27, hour=2, minute=30, tz_name="Europe/Berlin")
    )
    assert detail["transition_local_date"] == "1992-09-27"
    options = {o["choice"]: o for o in detail["options"]}
    assert options["earlier"]["abbreviation"] == "CEST"
    assert options["later"]["abbreviation"] == "CET"
    # «Часом позже» на экране — это разница смещений, а не выдумка вёрстки.
    assert options["earlier"]["offset_hours"] - options["later"]["offset_hours"] == 1.0


def test_a_midnight_switch_names_the_night_that_was_lived():
    """Бразилия переводила часы в полночь, и это ломает «дату по декрету».

    22 февраля 2015 в 00:00 −02 часы стали 21 февраля 23:00 −03. Повторился
    час **21-го**, и человек, родившийся в 23:30, прожил 21-е. Назвать ему
    22-е — отправить искать не ту ночь.
    """
    detail = ambiguity_detail(
        raise_at(
            year=2015, month=2, day=21, hour=23, minute=30, tz_name="America/Sao_Paulo"
        )
    )
    assert detail["transition_local_date"] == "2015-02-21"


def test_the_hour_before_and_after_the_overlap_are_not_a_question():
    """Развилка узкая: спрашивать вне повторившегося часа не о чем."""
    for hour in (1, 4):
        moment = resolve(
            year=1992, month=9, day=27, hour=hour, minute=30, tz_name="Europe/Berlin"
        )
        assert moment.time_known


def test_nobody_builds_this_body_by_hand_any_more():
    """Три копии этого ответа уже разъезжались — больше их быть не должно.

    Тело собиралось руками в обработчике и в двух роутерах. Копии были
    одинаковыми ровно до первой правки: обработчик научился присылать имена
    зон, роутеры продолжили слать две голые метки времени, и какой из трёх
    ответов достанется человеку, решало только то, в какую ручку он попал.
    """
    api = Path(__file__).resolve().parents[1] / "alma" / "api"
    culprits = [
        path.relative_to(api.parent).as_posix()
        for path in api.rglob("*.py")
        if '"error": "ambiguous_birth_time"' in path.read_text()
    ]
    assert culprits == [], f"собирают ответ мимо ambiguity_detail: {culprits}"


AMBIGUOUS = {
    "birth_date": "1998-10-25",
    "birth_time": "02:30",
    "latitude": 45.4642,
    "longitude": 9.19,
    "timezone": "Europe/Rome",
    "place_label": "Milan, Italy",
    "name": "Sofia Rossi",
    "is_self": True,
}


def test_the_answer_survives_being_saved(api, auth_headers):
    """**Без этого вопрос задавался бы вечно.**

    Движок умел развести двойное 02:30 и умел принять решение, но профиль его
    не хранил: `birth_from_profile` не передавал `on_ambiguous`, и каждый
    следующий расчёт по сохранённому рождению снова упирался в 409. Человек,
    родившийся в час перевода часов, отвечал на вопрос и получал его снова —
    на каждой главе, каждый день.
    """
    created = api.post(
        "/v1/profiles",
        json={**AMBIGUOUS, "on_ambiguous": "later"},
        headers=auth_headers,
    ).json()
    assert created["on_ambiguous"] == "later"

    # И расчёт по этому профилю больше не спрашивает.
    answer = api.post(
        "/v1/systems/natal",
        json={"profile_id": created["id"]},
        headers=auth_headers,
    )
    assert answer.status_code == 200, answer.text


def test_an_unanswered_birth_still_asks(api, auth_headers):
    """NULL — это «не спрашивали», а не «выбрано раньшее»."""
    created = api.post(
        "/v1/profiles", json=AMBIGUOUS, headers=auth_headers
    ).json()
    assert created["on_ambiguous"] is None

    answer = api.post(
        "/v1/systems/natal",
        json={"profile_id": created["id"]},
        headers=auth_headers,
    )
    assert answer.status_code == 409
    assert answer.json()["detail"]["error"] == "ambiguous_birth_time"


def test_editing_the_name_does_not_erase_the_answer(api, auth_headers):
    """Клиент правит имя формой целиком и про развилку не помнит.

    `on_ambiguous` по умолчанию «raise», и слепая запись затёрла бы ответ,
    данный однажды, — вопрос вернулся бы после безобидной правки.
    """
    created = api.post(
        "/v1/profiles",
        json={**AMBIGUOUS, "on_ambiguous": "earlier"},
        headers=auth_headers,
    ).json()
    edited = api.patch(
        f"/v1/profiles/{created['id']}",
        json={**AMBIGUOUS, "name": "Sofia R."},
        headers=auth_headers,
    ).json()
    assert edited["on_ambiguous"] == "earlier", "ответ пережил правку имени"
