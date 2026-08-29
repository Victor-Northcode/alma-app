"""Правки по живым скринам владельца от 29.08.2026.

Каждый тест здесь — один скрин: глава личного года объяснила читателю, что
«месяцев четырнадцать»; глава имени назвала числа без выкладки; глава пары
объявила «накал страстей 3.4» с сырой внутренней суммы; глава «Где ты сейчас»
читалась от места рождения. Правила, которыми это чинится, закреплены ниже —
и обязаны падать на старом коде тем самым сообщением.
"""

from __future__ import annotations

from datetime import date

import pytest

from alma.ai import chapters, writer
from alma.calc import BirthData, compute
from tests.conftest import SOFIA


def _birth() -> BirthData:
    return BirthData(
        date=date.fromisoformat(SOFIA["birth_date"]),
        time=SOFIA["birth_time"],
        latitude=SOFIA["latitude"],
        longitude=SOFIA["longitude"],
        timezone=SOFIA["timezone"],
        place_label=SOFIA["place_label"],
        name="Анатолий Михайлов",
    )


# ── «14 месяцев существует» ────────────────────────────────────────────────

def test_the_personal_cycle_length_rides_in_the_prompt():
    """Движок отдаёт цикл строго 1–9; модель склеила «14» из соседних чисел
    («day 14», «karmic debt 14») — теперь длина цикла названа прямо в брифе
    главы, единственном месте, где модель могла её не знать."""
    result = compute("numerology", _birth(), reference=date(2026, 8, 29))
    chapter = chapters.find("numerology", "personal-year")
    prompt = writer.build_prompt(
        result, chapter,
        offered=chapters.relevant_factors(chapter, list(result.factors)),
    )
    assert "THIS CHAPTER:" in prompt
    assert "1 through 9" in prompt
    assert "not a calendar month" in prompt


def test_a_chapter_without_special_rules_gets_no_guidance_line():
    result = compute("numerology", _birth(), reference=date(2026, 8, 29))
    chapter = chapters.find("numerology", "life-path")
    prompt = writer.build_prompt(
        result, chapter,
        offered=chapters.relevant_factors(chapter, list(result.factors)),
    )
    assert "THIS CHAPTER:" not in prompt


# ── «непонятно как посчиталось» ────────────────────────────────────────────

def test_the_name_workings_spell_out_every_letter():
    """Числа выражения и желания приходят с чеком: буква за буквой, сумма,
    свёртка — глава цитирует таблицу, а не объявляет итог."""
    result = compute("numerology", _birth(), reference=date(2026, 8, 29))
    workings = [f for f in result.factors if "working:" in f]
    expression = next(f for f in workings if f.startswith("expression working"))
    soul = next(f for f in workings if f.startswith("soul urge working"))
    # Разложение по буквам: «A1 N5 …» — значение стоит при каждой букве.
    assert " A1 " in f" {expression} ", expression
    assert "adds to" in expression and "→" in expression
    assert "A1" in soul or "O6" in soul, soul
    # И глава имени просит выкладку словами.
    chapter = chapters.find("numerology", "name")
    assert "Show the arithmetic" in chapter.guidance


def test_the_name_chapter_is_offered_its_workings():
    result = compute("numerology", _birth(), reference=date(2026, 8, 29))
    chapter = chapters.find("numerology", "name")
    offered = chapters.relevant_factors(chapter, list(result.factors))
    assert any(f.startswith("expression working") for f in offered)
    assert any(f.startswith("soul urge working") for f in offered)


# ── «накал страстей 3.4» ───────────────────────────────────────────────────

def test_raw_pair_scores_never_reach_the_factor_list():
    """Сырые суммы (`attraction score 3.417`) — кухня расчёта, не текст:
    модель печатала их читателю как шкалу, которой продукт не обещал."""
    other = BirthData(
        date=date(1993, 7, 21), time="08:15", latitude=48.85, longitude=2.35,
        timezone="Europe/Paris", place_label="Paris", name="Партнёр",
    )
    result = compute("compatibility", _birth(), other=other)
    scored = [f for f in result.factors if " score " in f]
    assert scored == [], f"скоры уехали в факторы: {scored}"
    # Но сами скоры живы в данных — они кухня, а не тайна.
    assert "scores" in result.data and result.data["scores"]


def test_the_friction_chapter_reads_the_hard_aspects_by_their_glyphs():
    """Аспекты печатаются знаками «□»/«☍», не словами: без глифов в списке
    глава напряжения видела из своего — только сатурн и снятый скор."""
    reads = chapters.find("compatibility", "friction").reads
    assert "□" in reads and "☍" in reads


def test_the_numbers_rule_rides_in_every_prompt():
    result = compute("numerology", _birth(), reference=date(2026, 8, 29))
    chapter = chapters.find("numerology", "life-path")
    prompt = writer.build_prompt(
        result, chapter,
        offered=chapters.relevant_factors(chapter, list(result.factors)),
    )
    assert "never invent or convert numbers" in prompt


def test_the_day_text_brief_forbids_weekdays_and_unit_conversion():
    """Живое чтение 29.08.2026: «0°94′», «во вторник» (в пятницу) и виньетка,
    в которой читатель себя не узнаёт. Бриф дневной главы запрещает все три —
    и обязан доезжать до промпта."""
    active = chapters.find("transits", "active")
    assert "Never name a weekday" in active.guidance
    assert "never convert degrees into minutes" in active.guidance
    result = compute("transits", _birth())
    prompt = writer.build_prompt(
        result, active,
        offered=chapters.relevant_factors(active, list(result.factors)),
    )
    assert "THIS CHAPTER:" in prompt
    assert "Never name a weekday" in prompt


def test_the_brief_is_part_of_the_chapter_identity():
    """Починка брифа обязана долетать до уже написанных глав.

    Промпт в ключ не входит, кеш вечен: без брифа в ключе глава, объяснившая
    читателю «четырнадцать месяцев», пережила бы правку у каждого, кто её
    открыл. Глава с новым guidance — честно новая глава.
    """
    from dataclasses import replace

    from alma.api.routers.readings import _opening_key, _reading_key

    result = compute("numerology", _birth(), reference=date(2026, 8, 29))
    chapter = chapters.find("numerology", "personal-year")
    bare = replace(chapter, guidance="")
    options = {"reference": date(2026, 8, 29)}

    assert _reading_key("numerology", _birth(), options, result, chapter) != \
        _reading_key("numerology", _birth(), options, result, bare), (
        "guidance обязан менять ключ главы"
    )
    assert _opening_key("numerology", _birth(), options, chapter) != \
        _opening_key("numerology", _birth(), options, bare), (
        "и ключ открывающего абзаца тоже"
    )


# ── «Где ты сейчас» — от места рождения ────────────────────────────────────

def test_a_named_current_place_becomes_a_citable_factor():
    """Названный город даёт фактор «at your current place: …» и другой ключ
    кэша; неназванный оставляет расчёт и главы прежними."""
    at_home = compute("astrocartography", _birth())
    moved = compute(
        "astrocartography", _birth(),
        current_latitude=52.52, current_longitude=13.405,
    )
    assert not any("current place" in f for f in at_home.factors)
    current = [f for f in moved.factors if f.startswith("at your current place:")]
    assert current, "фактор настоящего города обязан появиться"
    assert "current_place" in moved.data
    # И глава читает его: срез главы `here` пропускает новый фактор.
    chapter = chapters.find("astrocartography", "here")
    offered = chapters.relevant_factors(chapter, list(moved.factors))
    assert any(f.startswith("at your current place:") for f in offered)
    # Честность без города — тоже правило главы.
    assert "read from the birthplace" in chapter.guidance


def test_the_profile_carries_a_current_place(api, auth_headers):
    """Профиль хранит текущий город; PATCH без него города не стирает."""
    created = api.post(
        "/v1/profiles",
        json={
            **SOFIA,
            "current_latitude": 52.52,
            "current_longitude": 13.405,
            "current_place_label": "Berlin, Germany",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["current_place_label"] == "Berlin, Germany"

    # Правка имени старым клиентом — без полей города — город переживает.
    patched = api.patch(
        f"/v1/profiles/{body['id']}",
        json={**SOFIA, "name": "Sofia renamed"},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["current_latitude"] == pytest.approx(52.52)
    assert patched.json()["current_place_label"] == "Berlin, Germany"
