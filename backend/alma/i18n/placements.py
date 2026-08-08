"""The fifteen words a notification is allowed to contain.

A push payload carries a localisation key and a few arguments rather than a
sentence (`docs/PUSH.md §1.6`): the key names a string in the app's own
bundle, the operating system looks it up in the **device's** language, and the
arguments are substituted into it. That keeps the sentence about somebody's
chart off the wire, keeps the six translations where every other translated
string in this product lives, and means the server never has to decide what
language a phone is in.

There is one thing `loc-args` does not do, and it is easy to miss until an
Italian subscriber reads *"Marte attraversa il tuo Ascendant"*: the arguments
are substituted **verbatim**. There is no nested lookup. So the arguments have
to arrive already translated, and this is the table that translates them.

**The division of labour is the whole design.** The key carries word order,
grammar and the verb — "squares", "crosses", "entra in orbe" — and lives in a
file a translator opens. The arguments carry single words from a closed set of
fifteen, and the server substitutes them. Neither half is a generated
sentence, and neither half can drift into one.

**Why these fifteen and no more.** They are exactly the keys of
`transits.NATAL_WEIGHT` — every point the transit engine will ever name — plus
nothing. The transiting bodies are a subset of the same list. A sixteenth word
here would be a word no notification can contain.

**Why this file is separate from the rest of `alma/i18n/`.** The five language
modules beside it hold chapter titles and synthesis poles, checked as a set
against the English definitions by `tests/test_locales.py`. These are a
different kind of string: they are nouns from a closed vocabulary rather than
copy, they are needed by the notification transport rather than by the
reading layer, and the same fifteen words already exist in two client apps —
`cabinet_sun` and friends in `strings.xml`, `JourneyL10n.swift` on iOS. So
this table turns two copies and a gap into one source and two mirrors, and
`tests/test_notify_strings.py` asserts it agrees with the clients rather than
merely existing.

Aspect names are deliberately **not** here. "Squares" is a verb, its form
differs by language and by tense, and putting it in the arguments would be
asking the server to conjugate. The aspect is part of the key instead — see
`notify/strings.py`.
"""

from __future__ import annotations

#: The six, spelled as `alma/i18n/__init__.py` spells them.
LOCALES: tuple[str, ...] = ("en", "es", "de", "it", "fr", "pt-BR", "ru")

#: One row per point, one column per language. Written as a dict of dicts
#: rather than five modules because it is ninety short nouns, most of which
#: are Latin in five of the six languages, and splitting them across files
#: would make the one useful operation — reading a row across all six — the
#: awkward one.
PLACEMENTS: dict[str, dict[str, str]] = {
    "sun":        {"en": "Sun", "es": "Sol", "de": "Sonne", "it": "Sole", "fr": "Soleil", "pt-BR": "Sol", "ru": "Солнце"},
    "moon":       {"en": "Moon", "es": "Luna", "de": "Mond", "it": "Luna", "fr": "Lune", "pt-BR": "Lua", "ru": "Луна"},
    "mercury":    {"en": "Mercury", "es": "Mercurio", "de": "Merkur", "it": "Mercurio", "fr": "Mercure", "pt-BR": "Mercúrio", "ru": "Меркурий"},
    "venus":      {"en": "Venus", "es": "Venus", "de": "Venus", "it": "Venere", "fr": "Vénus", "pt-BR": "Vênus", "ru": "Венера"},
    "mars":       {"en": "Mars", "es": "Marte", "de": "Mars", "it": "Marte", "fr": "Mars", "pt-BR": "Marte", "ru": "Марс"},
    "jupiter":    {"en": "Jupiter", "es": "Júpiter", "de": "Jupiter", "it": "Giove", "fr": "Jupiter", "pt-BR": "Júpiter", "ru": "Юпитер"},
    "saturn":     {"en": "Saturn", "es": "Saturno", "de": "Saturn", "it": "Saturno", "fr": "Saturne", "pt-BR": "Saturno", "ru": "Сатурн"},
    "uranus":     {"en": "Uranus", "es": "Urano", "de": "Uranus", "it": "Urano", "fr": "Uranus", "pt-BR": "Urano", "ru": "Уран"},
    "neptune":    {"en": "Neptune", "es": "Neptuno", "de": "Neptun", "it": "Nettuno", "fr": "Neptune", "pt-BR": "Netuno", "ru": "Нептун"},
    "pluto":      {"en": "Pluto", "es": "Plutón", "de": "Pluto", "it": "Plutone", "fr": "Pluton", "pt-BR": "Plutão", "ru": "Плутон"},
    # Chiron is a proper name in three of the six and a transliteration in the
    # other three; the Spanish and Portuguese forms are the ones astrologers in
    # those languages actually print, not calques of the English.
    "chiron":     {"en": "Chiron", "es": "Quirón", "de": "Chiron", "it": "Chirone", "fr": "Chiron", "pt-BR": "Quíron", "ru": "Хирон"},
    # The engine's `true_node` is the north node; the south node is its exact
    # opposite and is never transited separately, so there is no row for it.
    "true_node":  {"en": "North Node", "es": "Nodo Norte", "de": "Nordknoten", "it": "Nodo Nord", "fr": "Nœud Nord", "pt-BR": "Nodo Norte", "ru": "Северный узел"},
    "lilith":     {"en": "Lilith", "es": "Lilith", "de": "Lilith", "it": "Lilith", "fr": "Lilith", "pt-BR": "Lilith", "ru": "Лилит"},
    "ascendant":  {"en": "Ascendant", "es": "Ascendente", "de": "Aszendent", "it": "Ascendente", "fr": "Ascendant", "pt-BR": "Ascendente", "ru": "Асцендент"},
    # The Latin survives in German and is what German-language astrology
    # prints; the other four translate it.
    "midheaven":  {"en": "Midheaven", "es": "Medio Cielo", "de": "Medium Coeli", "it": "Medio Cielo", "fr": "Milieu du Ciel", "pt-BR": "Meio do Céu", "ru": "Середина неба"},
}


def placement(name: str, locale: str) -> str:
    """One point's name in one language, falling back honestly.

    An unknown locale answers in English rather than raising: a notification
    that does not go out because somebody's phone reports `en-AU` is a worse
    outcome than one word in the wrong language, and the fallback is the same
    one the rest of the product uses.

    An unknown *point* is a bug rather than a locale problem — the engine has
    grown a body — so it answers with the raw key and logs nothing here,
    because the place that notices is a test over `NATAL_WEIGHT` and not a
    running system at 08:00.
    """
    row = PLACEMENTS.get(name)
    if row is None:
        return name.replace("_", " ")
    return row.get(_base(locale), row["en"])


def _base(locale: str | None) -> str:
    """Match `pt-BR` from `pt-BR`, `pt_BR` or `pt`, and `en` from anything else.

    Clients report a device language in whatever shape their platform uses —
    `pt_BR` on Android, `pt-BR` on iOS, sometimes a bare `pt`. Normalising here
    rather than at every call site means the notification layer never has to
    know that.
    """
    if not locale:
        return "en"
    tag = locale.replace("_", "-")
    if tag in PLACEMENTS["sun"]:
        return tag
    head = tag.split("-")[0].lower()
    if head == "pt":
        return "pt-BR"
    return head if head in PLACEMENTS["sun"] else "en"
