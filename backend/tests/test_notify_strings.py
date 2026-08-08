"""The fifteen words a notification may contain, in all six languages.

A push payload carries a localisation key and arguments; the operating system
resolves the key in the device's language and substitutes the arguments
**verbatim**. There is no nested lookup, so an untranslated argument is an
English word sitting inside an otherwise-Italian sentence — which is the exact
failure `alma/i18n/placements.py` exists to stop and which no amount of
testing the *keys* would ever catch.

The last test in this file is the one worth having: it checks the server's
table against the words the clients already show a person for the same three
placements. Those words previously existed in two apps and nowhere on the
server, and the value of moving them here is entirely in the two staying in
step with the one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from alma.engine.transits import NATAL_WEIGHT, TRANSIT_ORBS
from alma.i18n.placements import LOCALES, PLACEMENTS, placement
from alma.notify import message

ANDROID = Path(__file__).resolve().parents[2] / "mobile/android/app/src/main/res"

#: What the client calls the three placements it shows, and what we call them.
SHARED = {"cabinet_sun": "sun", "cabinet_moon": "moon", "cabinet_ascendant": "ascendant"}

#: Android's directory suffix per locale. `values` with no suffix is English.
ANDROID_DIRS = {
    "en": "values", "es": "values-es", "de": "values-de",
    "it": "values-it", "fr": "values-fr", "pt-BR": "values-pt-rBR",
}


def test_every_point_the_engine_can_name_has_a_word():
    """A transit naming a placement with no translation is a notification we cannot send."""
    assert set(PLACEMENTS) == set(NATAL_WEIGHT), (
        "the table and `transits.NATAL_WEIGHT` have separated — a point the "
        "engine can transit and this cannot name would be sent in English"
    )


def test_every_transiting_body_is_nameable_too():
    assert set(TRANSIT_ORBS) <= set(PLACEMENTS)


@pytest.mark.parametrize("name", sorted(PLACEMENTS))
def test_all_six_languages_are_present_and_none_is_the_english_left_behind(name):
    row = PLACEMENTS[name]
    assert set(row) == set(LOCALES), f"{name} is missing a language"
    assert all(value.strip() for value in row.values())


def test_the_six_are_the_six_the_rest_of_the_product_ships():
    from alma import i18n

    assert set(LOCALES) == set(i18n.LOCALES)


@pytest.mark.parametrize(
    "reported,expected",
    [
        ("it", "Saturno"), ("it-IT", "Saturno"), ("pt", "Saturno"), ("pt_BR", "Saturno"),
        ("de-AT", "Saturn"), ("en-GB", "Saturn"), ("", "Saturn"), ("klingon", "Saturn"),
    ],
)
def test_a_device_language_is_normalised_rather_than_refused(reported, expected):
    """A phone reporting `pt_BR`, `pt-BR` or a bare `pt` gets Portuguese.

    Clients report whatever shape their platform uses. Falling back to English
    for an unknown tag is deliberate: one word in the wrong language is a much
    smaller failure than a notification that does not go out.
    """
    assert placement("saturn", reported) == expected


def test_every_key_the_composer_can_produce_has_an_english_source():
    """Eleven bodies plus a title, and no twelfth invented later.

    `STRINGS` is what a translator is handed. A key the composer can emit and
    the table does not list is a notification that arrives on a lock screen as
    a raw key — which is what an untranslated `loc-key` renders as.
    """
    from alma.engine.transits import ASPECT_TARGETS

    aspects = {name for name, _offset in ASPECT_TARGETS}
    for aspect in aspects:
        assert f"push.daily.exact.{aspect}" in message.STRINGS
        assert f"push.daily.entering.{aspect}" in message.STRINGS
    assert message.TITLE_KEY in message.STRINGS
    assert "push.daily.quiet" in message.STRINGS
    assert len(message.STRINGS) == len(aspects) * 2 + 2


def test_the_exact_lines_take_three_arguments_and_the_others_two():
    """The order is fixed by the table and is the one thing a translator may not change."""
    for key, text in message.STRINGS.items():
        wanted = 3 if key.startswith("push.daily.exact.") else (0 if key == message.TITLE_KEY else 2)
        assert len(re.findall(r"%\d\$@", text)) == wanted, key


def test_the_valve_line_reads_as_a_quiet_week_rather_than_an_announcement():
    """`THE-DAILY.md §7` made the valve conditional on exactly this.

    It recommended the 21-day starvation valve *on condition* that the piece
    reads as the quiet week it is, and recorded that nobody had drafted one. If
    this line stops naming the quiet before it names the transit, the honest
    move is to drop the valve and accept the 60-day silence — not to reword the
    test.
    """
    line = message.STRINGS["push.daily.quiet"]
    assert line.lower().startswith("a quiet")
    assert "still" in line.lower()
    assert "%3$@" not in line, "a quiet week is not about a moment, so it carries no time"


@pytest.mark.parametrize("locale", sorted(ANDROID_DIRS))
def test_the_server_agrees_with_the_words_the_app_already_shows(locale):
    """One source, two mirrors — asserted rather than hoped for.

    Sun, Moon and Ascendant appear on the Today screen in six languages
    already. If the notification for a transit to the Ascendant used a
    different word from the screen it opens, the person would reasonably
    conclude they were two different things.
    """
    path = ANDROID / ANDROID_DIRS[locale] / "strings.xml"
    if not path.is_file():
        pytest.skip("the Android client is not in this checkout")
    body = path.read_text()
    for android_key, ours in SHARED.items():
        found = re.search(rf'<string name="{android_key}">(.*?)</string>', body)
        assert found, f"{android_key} is gone from {path.name}"
        assert found.group(1) == PLACEMENTS[ours][locale], (
            f"{ours} in {locale}: the app says {found.group(1)!r} and the "
            f"server would send {PLACEMENTS[ours][locale]!r}"
        )
