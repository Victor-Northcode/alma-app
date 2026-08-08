"""Place search and historical timezones.

Two things are tested here and they fail in different ways.

Search fails *visibly* — the user sees the wrong city and picks another — so
what matters is that the obvious query gives the obvious answer, including
when someone types their city's name in their own language. Each case below
is one that a single-signal ranking gets wrong: population alone answers
"new york" with Jakarta, name matching alone answers "roma" with a town in
Lesotho.

Timezones fail *invisibly*. Nothing about a chart says which offset produced
it, so an hour of error just produces a different, equally confident reading.
The dates below are real rule changes: Russia's 2011 and 2014 reforms, Brazil
abolishing daylight saving in 2019, Italy's summer time in 1998.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from alma import geo

pytestmark = pytest.mark.skipif(
    not geo.index_available(), reason="the place index is not built in this checkout"
)


# ── the query a person actually types ──────────────────────────────────────

@pytest.mark.parametrize(
    "query,expected",
    [
        ("milan", "Milan"),
        ("milano", "Milan"),          # Italian
        ("new york", "New York City"),
        ("york", "York"),             # must not be swallowed by New York
        ("münchen", "Munich"),        # German, filed under the English name
        ("munich", "Munich"),
        ("roma", "Rome"),             # Italian, and there is a Roma in Lesotho
        ("wien", "Vienna"),
        ("firenze", "Florence"),
        ("lisboa", "Lisbon"),
        ("praha", "Prague"),
        ("antwerpen", "Antwerp"),
        ("são paulo", "São Paulo"),
        ("sao paulo", "São Paulo"),   # without the accent
        ("tokyo", "Tokyo"),
        ("東京", "Tokyo"),
        # A Cyrillic query keeps the reader's own script on screen; the row
        # is still Moscow's — identity is the id, not the spelling.
        ("москва", "Москва"),
        ("köln", "Köln"),
        ("zurich", "Zürich"),
    ],
)
def test_the_obvious_query_gives_the_obvious_city(query, expected):
    results = geo.search(query, limit=3)
    assert results, f"{query!r} found nothing"
    assert results[0].name == expected, (
        f"{query!r} gave {results[0].label} instead of {expected}"
    )


def test_a_big_city_does_not_win_an_argument_about_its_name():
    """Jakarta is nicknamed "New York Van Java" and is nearly as large."""
    top = geo.search("new york", limit=1)[0]
    assert top.country_code == "US"


def test_search_needs_at_least_two_characters():
    assert geo.search("m") == []
    assert geo.search("") == []


def test_a_nonsense_query_returns_nothing_rather_than_guessing():
    assert geo.search("qwertyuiopasdfgh") == []


def test_punctuation_does_not_raise():
    """FTS5 has its own query syntax; a user typing it must not 500."""
    for query in ['"', "()", "* *", "a AND", "^^^", "NEAR("]:
        assert isinstance(geo.search(query), list)


def test_results_are_capped_at_the_requested_limit():
    assert len(geo.search("san", limit=5)) <= 5


def test_every_result_carries_what_a_chart_needs():
    for place in geo.search("paris", limit=5):
        assert -90 <= place.latitude <= 90
        assert -180 <= place.longitude <= 180
        assert geo.is_known_timezone(place.timezone), f"{place.label} has an unknown zone"
        assert place.label.count(",") >= 1


def test_lookup_by_id_round_trips():
    milan = geo.search("milan", limit=1)[0]
    again = geo.by_id(milan.id)
    assert again is not None
    assert again.name == milan.name
    assert again.latitude == milan.latitude


def test_an_unknown_id_returns_none():
    assert geo.by_id(-1) is None


def test_nearest_names_a_coordinate():
    place = geo.nearest(45.5, 9.2)
    assert place is not None and place.name == "Milan"


def test_nearest_gives_up_over_open_ocean():
    assert geo.nearest(0.0, -140.0, within_degrees=1.0) is None


# ── the offset that was in force *then* ────────────────────────────────────

def test_italy_was_on_summer_time_in_july_and_not_in_march():
    assert geo.offset_at("Europe/Rome", datetime(1998, 3, 14, 4, 20)) == 1.0
    assert geo.offset_at("Europe/Rome", datetime(1998, 7, 14, 4, 20)) == 2.0


def test_russia_changed_its_mind_twice():
    """Permanent summer time from 2011, then permanent standard time in 2014."""
    assert geo.offset_at("Europe/Moscow", datetime(2010, 7, 1)) == 4.0
    assert geo.offset_at("Europe/Moscow", datetime(2010, 1, 1)) == 3.0
    assert geo.offset_at("Europe/Moscow", datetime(2013, 1, 1)) == 4.0
    assert geo.offset_at("Europe/Moscow", datetime(2015, 7, 1)) == 3.0


def test_brazil_abolished_daylight_saving_in_2019():
    assert geo.offset_at("America/Sao_Paulo", datetime(2018, 1, 15)) == -2.0
    assert geo.offset_at("America/Sao_Paulo", datetime(2020, 1, 15)) == -3.0


def test_the_offset_is_never_read_from_today():
    """The whole point: two dates in one zone must be able to differ."""
    summer = geo.offset_at("Europe/Berlin", datetime(1985, 7, 1))
    winter = geo.offset_at("Europe/Berlin", datetime(1985, 1, 1))
    assert summer != winter


def test_a_coordinate_resolves_to_a_zone():
    assert geo.timezone_at(45.4642, 9.19) == "Europe/Rome"
    assert geo.timezone_at(-23.5505, -46.6333) == "America/Sao_Paulo"
    assert geo.timezone_at(35.6762, 139.6503) == "Asia/Tokyo"


def test_the_zone_a_place_carries_matches_its_coordinate():
    """A cross-check between two independent sources — GeoNames and the
    timezone shapefile — on the cities most people are born in."""
    for query in ("milan", "tokyo", "são paulo", "moscow", "new york", "sydney"):
        place = geo.search(query, limit=1)[0]
        found = geo.timezone_at(place.latitude, place.longitude)
        assert found == place.timezone, f"{place.label}: {found} vs {place.timezone}"


def test_offsets_format_the_way_a_birth_record_shows_them():
    assert geo.describe_offset(1.0) == "+01:00"
    assert geo.describe_offset(-3.5) == "−03:30"
    assert geo.describe_offset(5.75) == "+05:45"
    assert geo.describe_offset(0.0) == "+00:00"


def test_unknown_timezone_names_are_rejected():
    assert geo.is_known_timezone("Europe/Rome")
    assert not geo.is_known_timezone("Middle/Earth")
