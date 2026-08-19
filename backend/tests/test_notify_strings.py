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
import json
from pathlib import Path

import pytest

from alma.engine.transits import NATAL_WEIGHT, TRANSIT_ORBS
from alma.i18n.placements import LOCALES, PLACEMENTS, placement
from alma.notify import message

#: Каталог строк клиента. **Порт, а не натив.**
#:
#: Читалcя `mobile/android/.../res`, пока Android был отдельным приложением. С
#: 17 августа 2026 продукт один и написан на Flutter, нативы сняты, и зеркал у
#: сервера снова два: он сам и порт.
#:
#: Переписать было обязательно, а не «можно бы». Сверка молча пропускалась,
#: если каталога нет (`pytest.skip`), — то есть, удалив натив, мы бы не уронили
#: ни одного теста и **потеряли бы сторожа, ничего не заметив**. Именно этот
#: сторож поймал расхождение, ради которого файл и написан.
FLUTTER = Path(__file__).resolve().parents[2] / "mobile/flutter/alma/lib/l10n"

#: What the client calls the placements it shows, and what we call them.
#:
#: **The node is here because it was the one that drifted.** Sun, Moon and
#: Ascendant were checked from the first version and never moved; the node was
#: not checked, and Russian ended up calling it «Восходящий узел» on all three
#: clients while this table sent «Северный узел» in the notification about it.
#: Six languages and the English were fine. A word that appears both on the
#: chart and in a push about that chart is exactly the pair this file exists
#: to hold together, so the list is now every such word rather than three.
SHARED = {
    "cabBodySun": "sun",
    "cabBodyMoon": "moon",
    "cabBodyAscendant": "ascendant",
    "cabBodyTrueNode": "true_node",
}

#: The notification's own headline, held to the same rule for a harder reason.
#:
#: The placement names below are mirrored because a word on the chart and the
#: same word in a push about that chart have to agree. This one is mirrored
#: because the server **sends** it: iOS resolves `title-loc-key` against
#: `Localizable.strings` in the app's native bundle, the Flutter port has no
#: such file (`knownRegions` is `(en, Base)`), and an unresolved key renders as
#: the raw key on the lock screen. So `message.TITLES` composes the headline
#: from these seven strings, and this is what stops the two copies drifting —
#: which they already had: the server's English source said "In your chart
#: today" while every one of the seven catalogues said "Exact today".
TITLE = "pushDailyTitle"

#: Android's directory suffix per locale. `values` with no suffix is English.
#:
#: **Russian was missing here for as long as Russian has existed.** It is in
#: `i18n.LOCALES`, it is a column in `PLACEMENTS`, and the client has shipped
#: `values-ru` since the seventh locale landed — but this map never grew the
#: row, so the entire Russian half of "one source, two mirrors" was asserted
#: nowhere. That is how the node drifted without a red test.
#: Локаль → файл каталога. У порта имена проще нативных: `values-pt-rBR`
#: превратился в `app_pt.arb`, и седьмая строка больше не может потеряться при
#: добавлении языка — файл называется так же, как локаль.
FLUTTER_FILES = {
    "en": "app_en.arb", "es": "app_es.arb", "de": "app_de.arb",
    "it": "app_it.arb", "fr": "app_fr.arb", "pt-BR": "app_pt.arb",
    "ru": "app_ru.arb",
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


@pytest.mark.parametrize("locale", sorted(FLUTTER_FILES))
def test_the_server_agrees_with_the_words_the_app_already_shows(locale):
    """One source, two mirrors — asserted rather than hoped for.

    Sun, Moon and Ascendant appear on the Today screen in six languages
    already. If the notification for a transit to the Ascendant used a
    different word from the screen it opens, the person would reasonably
    conclude they were two different things.
    """
    path = FLUTTER / FLUTTER_FILES[locale]
    # Пропуска здесь больше нет намеренно. Порт — единственный клиент продукта;
    # его каталога не может не быть, и «нет файла» это поломка дерева, а не
    # обстоятельство, под которое сторожу следует прогибаться.
    catalogue = json.loads(path.read_text(encoding="utf-8"))
    for key, ours in SHARED.items():
        assert key in catalogue, f"{key} is gone from {path.name}"
        assert catalogue[key] == PLACEMENTS[ours][locale], (
            f"{ours} in {locale}: the app says {catalogue[key]!r} and the "
            f"server would send {PLACEMENTS[ours][locale]!r}"
        )


@pytest.mark.parametrize("locale", sorted(FLUTTER_FILES))
def test_the_headline_the_server_sends_is_the_headline_the_app_wrote(locale):
    """Не «переведено», а «совпадает» — потому что отправляет его сервер.

    Ключ `title-loc-key` разрешается в **нативном** бандле, которого у порта
    нет вовсе, и неразрешённый ключ iOS показывает сырой строкой. Поэтому
    заголовок собирается на сервере (`message.TITLES`), и единственное, что
    держит две копии одной фразы вместе, — эта сверка.
    """
    catalogue = json.loads((FLUTTER / FLUTTER_FILES[locale]).read_text(encoding="utf-8"))
    assert TITLE in catalogue, f"{TITLE} is gone from {FLUTTER_FILES[locale]}"
    assert message.TITLES[locale] == catalogue[TITLE], (
        f"{locale}: the app says {catalogue[TITLE]!r} and the notification "
        f"would arrive headed {message.TITLES[locale]!r}"
    )


def test_the_composed_headline_covers_every_locale_the_product_ships():
    from alma.i18n.placements import LOCALES

    assert set(message.TITLES) == set(LOCALES)
    assert all(value.strip() for value in message.TITLES.values())
