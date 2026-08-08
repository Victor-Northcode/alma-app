"""When a written chapter is the same chapter, and when it is a new one.

`Reading.calc_key` is how a stored chapter is found again. It used to be the
whole *system's* cache key, and the two answer different questions. A cache
key covers the system's entire answer, so for a system whose answer moves
daily it moves daily — correctly, because a transit scan really is different
tomorrow. But a chapter is not the system. Keying one on the other rewrote,
and charged for, every chapter of numerology and every chapter of transits
every midnight, on an archive sold as "written once, yours forever". The
stored-reading shortcut that exists to make that impossible never fired,
because the row was never found.

So the rule asserted here is: **a chapter is the same reading exactly when the
facts it is written from are the same.** Everything below is that rule from
one side or the other — never "the key equals itself".
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from alma.ai import chapters as chapter_defs
from alma.api.routers import readings as route
from alma.calc import BirthData, compute
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


def _key(system: str, birth: BirthData, chapter_slug: str, **options) -> str:
    chapter = chapter_defs.find(system, chapter_slug)
    result = compute(system, birth, **options)
    return route._reading_key(system, birth, options, result, chapter)


# ── the rule, stated over the systems that used to drift ───────────────────

@pytest.mark.parametrize(
    "system, chapter, moving",
    [
        ("numerology", "life-path", False),
        ("numerology", "personal-year", True),
        ("birth-card", "personality", False),
        ("birth-card", "year-card", False),
    ],
)
def test_a_chapter_keeps_its_key_exactly_while_its_own_facts_hold(system, chapter, moving):
    """Two references a month apart, and the key moves iff the facts moved.

    Stated as an equivalence rather than as "numerology is yearly now",
    because the equivalence is the thing that cannot be wrong. `personal-year`
    reads the personal month and day and genuinely changes; the other three
    read numbers fixed at birth or at a birthday and do not.
    """
    birth = _birth(SOFIA)
    early, late = date(2026, 8, 6), date(2026, 9, 6)

    definition = chapter_defs.find(system, chapter)
    facts = {
        moment: tuple(
            chapter_defs.relevant_factors(
                definition, compute(system, birth, reference=moment).factors
            )
        )
        for moment in (early, late)
    }
    changed = facts[early] != facts[late]
    assert changed is moving, f"{system}/{chapter} facts: {facts}"

    same_key = _key(system, birth, chapter, reference=early) == _key(
        system, birth, chapter, reference=late
    )
    assert same_key is not changed


def test_the_life_path_chapter_is_written_once_and_never_again():
    """Five numerology chapters rewritten nightly was $0.20 a day per owner.

    An owner's whole month is worth less than a week of that, so on about the
    fourth day they opened a chapter they had paid for and were told they had
    run out of money.
    """
    birth = _birth(SOFIA)
    keys = {
        _key("numerology", birth, "life-path", reference=date(2026, 8, 6) + timedelta(days=n))
        for n in range(0, 400, 17)
    }
    assert len(keys) == 1


def test_a_transit_chapter_moves_when_the_transits_move():
    """Transits genuinely change, so the chapter genuinely is written again.

    The point of the rule is that it says so for the right reason: a year
    later the active aspects are different, and that is why — not because a
    date went into a hash.
    """
    birth = _birth(SOFIA)
    start = datetime(2026, 8, 6, tzinfo=timezone.utc)
    later = start + timedelta(days=365)

    def key(when: datetime) -> str:
        return _key("transits", birth, "active", start=when, days=365, house_system="placidus")

    definition = chapter_defs.find("transits", "active")
    facts = {
        when: tuple(
            chapter_defs.relevant_factors(
                definition,
                compute("transits", birth, start=when, days=365, house_system="placidus").factors,
            )
        )
        for when in (start, later)
    }
    assert facts[start] != facts[later]
    assert key(start) != key(later)


def test_the_route_asks_for_a_transit_scan_no_finer_than_its_own_key():
    """A transit orb is quoted to a hundredth of a degree and moves all day.

    So a scan started at `now()` produced a finer answer than the day-wide key
    that stores it: whichever worker computed a day's transits first decided
    what everyone saw, and every other worker's scan differed in the second
    decimal — a hit distinguishable from a miss, and one extra copy of every
    written chapter per worker. The route asks for midnight so that the answer
    is a function of its key.
    """
    options = route._options_for("transits", "placidus")
    start = options["start"]
    assert (start.hour, start.minute, start.second, start.microsecond) == (0, 0, 0, 0)
    assert start.tzinfo is not None


def test_two_people_never_share_a_reading():
    """The birth is still in the key, because it still has to be."""
    assert _key("numerology", _birth(SOFIA), "life-path", reference=date(2026, 8, 6)) != _key(
        "numerology", _birth(LUCAS), "life-path", reference=date(2026, 8, 6)
    )


def test_two_chapters_of_one_system_are_two_readings():
    birth = _birth(SOFIA)
    assert _key("numerology", birth, "life-path", reference=date(2026, 8, 6)) != _key(
        "numerology", birth, "personal-year", reference=date(2026, 8, 6)
    )


def test_a_different_house_system_is_a_different_reading():
    """Not a moment, so it stays in the key untouched."""
    birth = _birth(SOFIA)
    assert _key("natal", birth, "core", house_system="placidus") != _key(
        "natal", birth, "core", house_system="whole_sign"
    )


# ── and the same thing over HTTP, which is where it cost money ─────────────

def _reply(factors: list[str]) -> str:
    return json.dumps(
        {
            "title": "A title",
            "teaser": "A line.",
            "advice": "Say the thing sooner.",
            "paragraphs": [
                {"text": "The first paragraph, read from the chart.", "factors": factors[:1]},
                {"text": "The second, from the same place.", "factors": factors[:1]},
            ],
        }
    )


@pytest.fixture
def scripted(api):
    from alma.ai.provider import ScriptedProvider
    from alma.api.deps import get_provider

    provider = ScriptedProvider()
    api.app.dependency_overrides[get_provider] = lambda: (lambda: provider)
    yield provider
    api.app.dependency_overrides.clear()


def test_the_free_numerology_sample_is_not_rewritten_the_next_day(
    api, auth_headers, scripted, monkeypatch
):
    """The reproduction, end to end: one provider call, then none.

    The clock is moved by moving `_options_for`, which is the only thing in
    the route that reads it — the same lever a real midnight pulls.
    """
    api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
    factors = list(compute("numerology", _birth(SOFIA), reference=date(2026, 8, 6)).factors)
    scripted.responses.extend(_reply(factors) for _ in range(3))

    real = route._options_for

    def at(day: date):
        def options(system: str, house_system: str) -> dict:
            base = real(system, house_system)
            if "reference" in base:
                base["reference"] = day
            return base

        monkeypatch.setattr(route, "_options_for", options)

    ask = lambda: api.post(
        "/v1/readings",
        json={"system": "numerology", "chapter": "life-path"},
        headers=auth_headers,
    ).json()

    at(date(2026, 8, 6))
    assert ask()["cached"] is False
    assert ask()["cached"] is True

    at(date(2026, 8, 7))
    assert ask()["cached"] is True, "a midnight is not a new reading"
    at(date(2027, 2, 14))
    assert ask()["cached"] is True, "nor is half a year"

    assert len(scripted.calls) == 1
