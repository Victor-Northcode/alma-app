"""The six languages, checked the way the web checks its six.

The web cannot ship a missing string: the dictionaries are typed against
`typeof en`, so an absent key is a build error, and `scripts/check-locales.mjs`
catches the other failure — a key that was copied across and never translated,
which is the one that actually reaches customers, because the page looks
finished and one sentence in six is in the wrong language.

Python has neither of those. This file is both of them.

What it guards is 100 strings: 41 chapter titles, 41 chapter questions, and
nine pairs of synthesis poles. Not 109 — the nine axis *names* are identifiers
the model cites and the validator checks character by character, and
`alma/i18n/__init__.py` explains at length why translating them refuses the
reading rather than localising it. The tests at the bottom hold that line, so
that a future translator who reasonably assumes "Direction" is a word finds
out here rather than from a reader whose paid chapter would not write.
"""

from __future__ import annotations

import pytest

from alma import i18n
from alma.i18n import replies
from alma.ai import chapters as chapter_defs
from alma.ai import voice
from alma.engine import synthesis

#: Every (system, slug) pair there is, taken from the definitions rather than
#: written out — a chapter added tomorrow is covered by these tests today.
CHAPTER_KEYS = [
    (system, chapter.slug)
    for system, defined in chapter_defs.BY_SYSTEM.items()
    for chapter in defined
]

AXIS_NAMES = [name for name, _negative, _positive in synthesis.AXES]

#: Not a magic number so much as a headline: this is the size of the surface
#: five people were asked to translate, and it is asserted so that a chapter
#: quietly disappearing shows up as a failing count rather than as a shorter
#: list nobody counted.
TRANSLATABLE_STRINGS = len(CHAPTER_KEYS) * 2 + len(AXIS_NAMES) * 2


def test_the_surface_is_the_size_we_think_it_is():
    assert len(CHAPTER_KEYS) == 41
    assert len(AXIS_NAMES) == 9
    assert TRANSLATABLE_STRINGS == 100


# ── every string exists in every language ──────────────────────────────────

@pytest.mark.parametrize("locale", i18n.LOCALES)
def test_every_locale_carries_every_chapter(locale):
    """The build error the type system would have given us on the web.

    Both directions. A missing key is a German reader shown an English title;
    an *extra* key is a translation of a chapter that no longer exists, which
    is worse than harmless — it is a slug someone renamed and a file nobody
    updated, and the renamed chapter is the one now reading in English.
    """
    theirs = i18n.catalogue(locale).chapters
    present = {(system, slug) for system, rows in theirs.items() for slug in rows}
    assert present == set(CHAPTER_KEYS), locale


@pytest.mark.parametrize("locale", i18n.LOCALES)
def test_every_locale_carries_every_axis(locale):
    assert set(i18n.catalogue(locale).axes) == set(AXIS_NAMES), locale


def _chapters(locale: str) -> list[tuple[str, str, i18n.ChapterWords]]:
    """This locale's chapters, by key, skipping any it does not have.

    Every test below this line asks a question *about a string* — is it blank,
    is it still a question, is it still English — and none of them is the test
    that owns "does this file have all 41 chapters". That one is
    `test_every_locale_carries_every_chapter`, and it fails with a readable
    set difference naming exactly the key that went.

    Indexing here instead meant one deleted key produced five failures: the
    one that says which key, and four bare `KeyError` tracebacks that name the
    symptom. A translator who dropped a line should be told once, by the test
    whose sentence is about that, and not have to work out which of five
    failures is the cause of the other four.
    """
    theirs = i18n.catalogue(locale).chapters
    found = []
    for system, slug in CHAPTER_KEYS:
        words = theirs.get(system, {}).get(slug)
        if words is not None:
            found.append((system, slug, words))
    return found


def _axes(locale: str) -> list[tuple[str, i18n.AxisWords]]:
    """As `_chapters`, for the nine pairs of poles."""
    theirs = i18n.catalogue(locale).axes
    return [(name, theirs[name]) for name in AXIS_NAMES if name in theirs]


@pytest.mark.parametrize("locale", i18n.LOCALES)
def test_nothing_is_blank(locale):
    """An empty string is a missing translation that survived the key check."""
    for system, slug, words in _chapters(locale):
        assert words.title.strip(), f"{locale} {system}/{slug} has no title"
        assert words.question.strip(), f"{locale} {system}/{slug} has no question"
    for name, poles in _axes(locale):
        assert poles.negative.strip(), f"{locale} {name} has no negative pole"
        assert poles.positive.strip(), f"{locale} {name} has no positive pole"


# ── every string is still the kind of thing it was ─────────────────────────

@pytest.mark.parametrize("locale", i18n.LOCALES)
def test_a_question_is_still_a_question(locale):
    """The question is what makes somebody tap, and it is theirs, not ours.

    Every one of the six languages ends a question with `?` — Spanish opens
    one with `¿` as well, French puts a space before it — so this is a real
    rule and not an English habit. It also catches the mistake this shape is
    most exposed to: a title and a question written into each other's field.
    """
    for system, slug, words in _chapters(locale):
        assert words.question.rstrip().endswith("?"), (
            f"{locale} {system}/{slug}: {words.question!r} is not a question"
        )
        assert not words.title.rstrip().endswith("?"), (
            f"{locale} {system}/{slug}: the title {words.title!r} is a question — "
            "the two fields look swapped"
        )


@pytest.mark.parametrize("locale", i18n.LOCALES)
def test_a_title_is_a_name_and_not_a_sentence(locale):
    """A chapter title is the name of a room, so it does not end in a stop."""
    for system, slug, words in _chapters(locale):
        assert not words.title.rstrip().endswith((".", "!")), (
            f"{locale} {system}/{slug}: {words.title!r} is written as a sentence"
        )


# ── and it is actually in that language ────────────────────────────────────

def _still_english(locale: str, *, allow_shared: bool) -> tuple[list[str], int]:
    """This locale's strings that are character-for-character English.

    Returns them and how many strings were compared, which is 100 for a
    complete file and fewer for one missing a key. The second number is what
    the `WRITTEN = False` branch measures against, so that a dropped chapter
    is reported by the completeness test alone rather than also arriving here
    as a bogus "this file has been part-translated".
    """
    english, theirs = i18n.catalogue(i18n.DEFAULT_LOCALE), i18n.catalogue(locale)
    shared = theirs.shared if allow_shared else frozenset()
    found: list[str] = []
    compared = 0

    for system, slug, yours in _chapters(locale):
        mine = english.chapters[system][slug]
        for field in ("title", "question"):
            compared += 1
            value = getattr(yours, field)
            if value == getattr(mine, field) and value not in shared:
                found.append(f"{system}/{slug}.{field}: {value!r}")

    for name, yours in _axes(locale):
        mine = english.axes[name]
        for field in ("negative", "positive"):
            compared += 1
            value = getattr(yours, field)
            if value == getattr(mine, field) and value not in shared:
                found.append(f"axis {name}.{field}: {value!r}")

    return found, compared


@pytest.mark.parametrize("locale", sorted(set(i18n.LOCALES) - {i18n.DEFAULT_LOCALE}))
def test_the_written_flag_tells_the_truth(locale):
    """`check-locales.mjs`, for the backend — and it is load-bearing both ways.

    A locale file says in one line whether it has been translated, and this
    test refuses to let that line be wrong in either direction.

    **`WRITTEN = True` and English left in it** is the failure the web's
    checker exists for, and the one that actually reaches customers: the
    screen looks finished and one title in six is in the wrong language. Words
    that genuinely are the same in both languages — "Portrait" is French and
    German for "Portrait" — go in that file's own `SHARED` set, one at a time,
    exactly as the web's checker requires. A blanket exemption would make this
    a formality.

    **`WRITTEN = False` and not English any more** is the failure that would
    have made the flag a convention nobody enforces: 39 chapters translated,
    two forgotten, the flag never flipped, and the check above skipped
    forever. So a file that has not been written must still be *entirely* the
    English it was generated as. There is no half state to hide in.
    """
    if i18n.catalogue(locale).written:
        left, _compared = _still_english(locale, allow_shared=True)
        assert not left, (
            f"{locale} says it is written, but {len(left)} string(s) are still "
            "English:\n  " + "\n  ".join(left)
        )
        return

    left, compared = _still_english(locale, allow_shared=False)
    assert len(left) == compared, (
        f"{locale} has been part-translated — {compared - len(left)} of "
        f"{TRANSLATABLE_STRINGS} strings are no longer English — but its file still "
        "says WRITTEN = False, which is what turns off the check that the rest of "
        "them are done. Finish it and flip the flag."
    )


# ── which language a reader gets ───────────────────────────────────────────

@pytest.mark.parametrize("locale", i18n.LOCALES)
def test_a_shipped_locale_resolves_to_itself(locale):
    assert i18n.resolve(locale) == locale


@pytest.mark.parametrize(
    "asked, given",
    [
        ("de-AT", "de"),          # an Austrian phone
        ("de_DE", "de"),          # an underscore, from a client using POSIX tags
        ("PT-BR", "pt-BR"),       # a tag that arrived upper-cased
        ("pt", "pt-BR"),          # the language with no region
        ("pt-PT", "pt-BR"),       # Portugal: Brazilian is far closer than English
        ("es-419", "es"),         # Latin American Spanish
        ("fr-CA", "fr"),
        ("  it  ", "it"),
    ],
)
def test_a_region_lands_on_the_language_we_have(asked, given):
    """The near misses, which are the ones that used to land on English.

    None of these is an exotic tag. Every one of them is a reader whose words
    we have written and who was handed the fallback anyway, silently, because
    a dictionary lookup on the exact string missed by two characters.
    """
    assert i18n.resolve(asked) == given


@pytest.mark.parametrize("asked", ["nl", "ja", "en-GB", "", "   ", None, "not a tag"])
def test_a_language_we_have_not_written_gets_english(asked):
    """Deliberately English, and English all the way down.

    Not an exception and not an empty list: a table of contents somebody
    cannot read is still a table of contents, and a 500 is not.
    """
    assert i18n.resolve(asked) in {"en", "en"}
    words = i18n.chapter_words("natal", "core", locale=asked)
    assert words.title == chapter_defs.find("natal", "core").title


def test_the_voice_can_name_every_language_we_ship():
    """`voice.system_prompt` looks its language up by the resolved tag.

    It indexes rather than `.get`s, on purpose — a locale in `LOCALES` with no
    entry here would be a reader told to write in nothing. This is the test
    that makes indexing safe.
    """
    assert set(voice.LOCALE_NAMES) == set(i18n.LOCALES)


def test_the_reading_is_written_in_the_language_of_a_regional_tag():
    """"de-AT" is German prose, not English prose.

    This is the bug that lookup used to have: `LOCALE_NAMES.get("de-AT")`
    missed, fell through to the default, and instructed the model to write in
    English for a reader whose whole interface was German.
    """
    assert "German" in voice.system_prompt(locale="de-AT")
    assert "Brazilian Portuguese" in voice.system_prompt(locale="pt_BR")


# ── the nine names are not copy ────────────────────────────────────────────

def test_the_axis_names_are_the_same_in_every_language():
    """The line this whole design rests on.

    An axis name is a dictionary key in `compute`, a substring in the
    synthesis chapter's `reads` tuple, and a string inside
    `Synthesis.factors()` — which is the list the model must cite from
    verbatim and the list `ai/validator.py` checks those citations against
    character by character. Translate it and a German reading cites
    "Richtung", the validator finds no such factor, calls it invented, and
    refuses the chapter after three attempts. The clients translate the nine
    names themselves, keyed on the English word.
    """
    for locale in i18n.LOCALES:
        assert set(i18n.catalogue(locale).axes) == set(AXIS_NAMES), locale


def test_the_synthesis_chapter_can_still_find_its_factors():
    """The `reads` tuple of the last synthesis chapter *is* the nine names.

    So if a name ever moved, "All of it together" would match nothing, and a
    chapter with no factors is not written at all — the most expensive chapter
    of the most expensive system, silently absent.
    """
    whole = chapter_defs.find("synthesis", "whole")
    assert set(whole.reads) == set(AXIS_NAMES)


def test_the_poles_are_translated_and_nothing_else_is(monkeypatch):
    """What `localise_synthesis` is allowed to touch.

    The poles and the direction move. The name, the verdict, the label and
    every cited factor stay exactly as the engine wrote them, because all four
    are read back by something that compares strings.
    """
    monkeypatch.setitem(
        i18n._TRANSLATIONS["de"].AXES,
        "Direction",
        i18n.AxisWords(negative="arbeitet allein", positive="arbeitet öffentlich"),
    )
    data = {
        "summary": "3 systems across nine axes: 4 agree, 2 disagree, 3 seen by one",
        "axes": [
            {
                "name": "Direction",
                "verdict": "agree",
                "label": "2 agree",
                "count": 2,
                "direction": "works in public, in front of people",
                "positive_pole": "works in public, in front of people",
                "negative_pole": "works alone, out of sight",
                "signals": [{"system": "natal", "factor": "midheaven in Leo"}],
            }
        ],
    }

    localised = i18n.localise_synthesis(data, locale="de")
    axis = localised["axes"][0]

    assert axis["positive_pole"] == "arbeitet öffentlich"
    assert axis["negative_pole"] == "arbeitet allein"
    assert axis["direction"] == "arbeitet öffentlich"

    assert axis["name"] == "Direction"
    assert axis["label"] == "2 agree"
    assert axis["verdict"] == "agree"
    assert axis["signals"] == [{"system": "natal", "factor": "midheaven in Leo"}]
    assert localised["summary"] == data["summary"]


def test_localising_a_synthesis_does_not_rewrite_the_cached_one(monkeypatch):
    """The dictionary handed in belongs to `api/cache.py`, not to us.

    One `CalcResult` is computed per birth and handed to every request for
    that birth, in whatever language each of them asked for. Translating in
    place would mean the second reader's language decided the first reader's
    chart — and, because the cache is keyed on the birth, it would stay wrong
    until the entry expired.
    """
    monkeypatch.setitem(
        i18n._TRANSLATIONS["fr"].AXES,
        "Character",
        i18n.AxisWords(negative="tient sa position", positive="change de forme"),
    )
    data = {
        "axes": [
            {
                "name": "Character",
                "direction": None,
                "positive_pole": "changes shape",
                "negative_pole": "holds a position",
            }
        ]
    }
    before = {"axes": [dict(data["axes"][0])]}

    i18n.localise_synthesis(data, locale="fr")

    assert data == before, "the cached result was translated in place"


def test_an_axis_we_have_no_words_for_keeps_the_engines_own():
    """Never blank. The same rule both clients follow for an unknown name."""
    data = {"axes": [{"name": "Weather", "positive_pole": "sunny", "negative_pole": "grey"}]}
    localised = i18n.localise_synthesis(data, locale="de")
    assert localised["axes"][0]["positive_pole"] == "sunny"


# ── over HTTP ──────────────────────────────────────────────────────────────

def test_the_chapter_list_is_served_in_the_readers_language(api, auth_headers, monkeypatch):
    """The whole point, end to end.

    `GET /v1/readings/{system}/chapters` takes `locale` the same way
    `POST /v1/readings` does — same name, same default — and answers with the
    title and the question in that language, plus the language it settled on
    so a client can tell what it got.
    """
    monkeypatch.setitem(
        i18n._TRANSLATIONS["de"].CHAPTERS["natal"],
        "core",
        i18n.ChapterWords(title="Kern", question="Wie bin ich wirklich, darunter?"),
    )

    body = api.get("/v1/readings/natal/chapters?locale=de", headers=auth_headers).json()
    core = next(c for c in body["chapters"] if c["slug"] == "core")

    assert body["locale"] == "de"
    assert core["title"] == "Kern"
    assert core["question"] == "Wie bin ich wirklich, darunter?"
    # Structure is untouched: a client keys on the slug and the numeral.
    assert core["numeral"] == "I"
    assert core["free"] is True


def test_a_regional_tag_is_answered_and_reported(api, auth_headers, monkeypatch):
    monkeypatch.setitem(
        i18n._TRANSLATIONS["de"].CHAPTERS["natal"],
        "core",
        i18n.ChapterWords(title="Kern", question="Wie bin ich wirklich, darunter?"),
    )
    body = api.get("/v1/readings/natal/chapters?locale=de-AT", headers=auth_headers).json()
    assert body["locale"] == "de"
    assert next(c for c in body["chapters"] if c["slug"] == "core")["title"] == "Kern"


def test_the_chapter_list_without_a_locale_is_english(api, auth_headers):
    """The default is what every existing client already gets."""
    body = api.get("/v1/readings/natal/chapters", headers=auth_headers).json()
    core = next(c for c in body["chapters"] if c["slug"] == "core")
    assert body["locale"] == "en"
    assert core["title"] == "Core"
    assert core["question"] == "What am I really like underneath?"


@pytest.mark.parametrize(
    "tag, given",
    [
        ("zh-Hans-CN", "en"),      # a language nobody has written: English
        ("en_US_POSIX", "en"),
        ("de-DE-1996", "de"),      # and two we *have* written, refused on length
        ("es-419-u-va", "es"),
    ],
)
def test_a_tag_longer_than_our_own_still_gets_a_table_of_contents(api, auth_headers, tag, given):
    """A language we cannot write is answered, not refused.

    The ceiling on this parameter used to be 8 characters — roughly the length
    of the six tags *we* ship, which is not the length of a tag a client can
    honestly send. `zh-Hans-CN` is ten and was a 422 with no chapters in it:
    a blank table of contents for a reader `resolve` would have handed English
    without complaint. That is the exact inverse of what `resolve` is for, and
    it is one wrong `@Query` annotation away from being what an Android client
    reading `Locale.getDefault()` produces.
    """
    response = api.get(f"/v1/readings/natal/chapters?locale={tag}", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["locale"] == given
    assert len(body["chapters"]) == 16


def test_a_tag_that_is_not_a_tag_is_still_refused(api, auth_headers):
    """Widened, not opened. 35 characters is a language tag's practical bound."""
    response = api.get(
        "/v1/readings/natal/chapters?locale=" + "x" * 64, headers=auth_headers
    )
    assert response.status_code == 422


def test_the_model_is_asked_the_question_in_the_readers_language(monkeypatch):
    """The prompt carries the chapter's question, and it is theirs too.

    Asking in English and demanding an answer in German makes the model
    translate the brief before it starts, and lets it title the chapter
    something other than the words on the screen the reader tapped.
    """
    from datetime import date

    from alma.ai import writer
    from alma.calc import BirthData, compute

    monkeypatch.setitem(
        i18n._TRANSLATIONS["de"].CHAPTERS["natal"],
        "core",
        i18n.ChapterWords(title="Kern", question="Wie bin ich wirklich, darunter?"),
    )

    result = compute(
        "natal",
        BirthData(
            date=date(1998, 3, 14), time="04:20", latitude=45.4642, longitude=9.19,
            timezone="Europe/Rome",
        ),
    )
    chapter = chapter_defs.find("natal", "core")
    offered = chapter_defs.relevant_factors(chapter, result.factors)

    german = writer.build_prompt(result, chapter, offered=offered, locale="de")
    assert "Kern — Wie bin ich wirklich, darunter?" in german
    # The factors are identifiers and stay exactly as the engine wrote them,
    # in every language — that is what the validator compares against.
    for factor in offered:
        assert factor in german

    english = writer.build_prompt(result, chapter, offered=offered)
    assert "Core — What am I really like underneath?" in english


def test_a_regional_tag_does_not_buy_a_second_copy_of_the_same_reading(api, auth_headers):
    """"de" and "de-AT" are one German reading, and one generation.

    `reading_once` includes the locale and used to include it *raw*, which was
    right while `voice.system_prompt` did `LOCALE_NAMES.get(locale, en)`: a
    "de-AT" reader really was written to in English, so the two rows really
    were two different readings. Since that lookup resolves, the prompts are
    byte-identical, and the only thing the raw tag decided was how many times
    we paid for the same German — once for the phone that reports "de" and
    again for the one that reports "de-AT". A reader who switches form is
    charged twice for prose they already own.

    Написано на `natal/core`, а не на `numerology/life-path`: с 17.08.2026
    бесплатна ровно одна глава во всём продукте, и это она. Проверяемое от
    выбора главы не зависит — вопрос про ключ строки `reading`, а не про
    систему, — а платить за право доступа ради теста про локали незачем.
    """
    from alma.ai.provider import ScriptedProvider
    from alma.api.deps import get_provider
    from tests.conftest import SOFIA
    from tests.test_readings_api import _chapter_reply, _factors_for

    scripted = ScriptedProvider()
    api.app.dependency_overrides[get_provider] = lambda: (lambda: scripted)
    try:
        api.post("/v1/profiles", json=SOFIA, headers=auth_headers)
        # One scripted reply, deliberately: the second request must not need a
        # second one. If it does, the provider runs dry and the route answers
        # 503 — which is this test failing loudly rather than quietly.
        scripted.responses.append(
            _chapter_reply(_factors_for(api, auth_headers, "natal"), title="Kern")
        )

        response = api.post(
            "/v1/readings",
            json={"system": "natal", "chapter": "core", "locale": "de"},
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        first = response.json()
        second = api.post(
            "/v1/readings",
            json={"system": "natal", "chapter": "core", "locale": "de-AT"},
            headers=auth_headers,
        ).json()

        assert first["cached"] is False
        assert second["cached"] is True, "de-AT paid for a second copy of the German"
        assert second["reading"]["body"] == first["reading"]["body"]
        assert len(scripted.calls) == 1
    finally:
        api.app.dependency_overrides.clear()


# ── the four sentences the server writes itself ────────────────────────────
#
# These are a different kind of string from everything above: not a chapter
# title a translator was handed, but what the chat route says when there is no
# reply to give. They are here because they are subject to the same rule — a
# reader who paid in Italian does not meet English on the one screen where
# something has gone wrong — and because each of them replaces a `str(exc)`
# that put our validator's own vocabulary, or another company's error object,
# in front of somebody who had just asked a personal question.

@pytest.mark.parametrize("error", sorted(replies.BY_ERROR))
def test_every_server_written_sentence_exists_in_every_language(error):
    table = replies.BY_ERROR[error]
    assert set(table) == set(i18n.LOCALES), f"{error} is missing a language"
    assert all(value.strip() for value in table.values())


@pytest.mark.parametrize("error", sorted(replies.BY_ERROR))
def test_no_translation_is_the_english_left_behind(error):
    """The failure mode a set comparison cannot see: the key exists, in English."""
    table = replies.BY_ERROR[error]
    english = table["en"]
    assert all(
        table[locale] != english
        for locale in i18n.LOCALES
        if locale != i18n.DEFAULT_LOCALE
    ), f"{error} carries English under another language's key"


def test_a_placeholder_survives_every_translation():
    """A limit that vanished in translation would be a sentence with a hole."""
    # The day wall no longer quotes a number — there is no daily refill to
    # count, and «your 0 questions» was the sentence a placeholder would buy.
    for locale in i18n.LOCALES:
        assert "{limit}" in replies.BY_ERROR["question_limit.month"][locale]
        # The other two walls that count something: a week's allowance and the
        # finite bundle a purchase includes. Both name their number, and both
        # are reached through the same `question_limit.{period}` key.
        assert "{limit}" in replies.BY_ERROR["question_limit.week"][locale]
        assert "{limit}" in replies.BY_ERROR["question_limit.once"][locale]
        assert "{limit}" not in replies.BY_ERROR["question_limit.day"][locale]
        assert "40" in replies.reply("question_limit.month", locale, limit=40)


def test_a_regional_tag_still_gets_its_own_language():
    """`de-AT` is a real tag from a real phone, and its reader reads German."""
    assert replies.reply("answer_refused", "de-AT") == replies.REFUSED["de"]
    # Russian ships now; Japanese is the example of a language we do not.
    assert replies.reply("answer_refused", "ja") == replies.REFUSED["en"]


def test_no_server_written_sentence_is_about_our_internals():
    """What `str(exc)` used to say, and what a reader must never be shown."""
    forbidden = ("validator", "factor", "cite", "request_id", "invalid_request",
                 "HTTP", "error code", "traceback")
    for table in replies.BY_ERROR.values():
        for locale, sentence in table.items():
            lowered = sentence.lower()
            assert not any(word.lower() in lowered for word in forbidden), (
                f"{locale} names our machinery: {sentence}"
            )


def test_our_own_chapter_titles_pass_the_gate_we_hold_alma_to():
    """The catalogue is copy too, and it was breaking its own rule.

    `validator.plain_language` refuses a paragraph containing «ядро», «суть»,
    "essence", "true self" and the rest — the list the owner dictated from the
    paragraph that angered him. But the gate only ever reads what the *model*
    writes. Chapter titles and questions are ours, they are shipped in seven
    languages, and nothing checked them: the first free chapter of a Russian
    natal chart was called «Ядро» and asked «Что во мне настоящее, под всем
    остальным?» — the banned word and the banned phrase, printed at the top of
    the screen that sells the other fifteen. Found by opening it on a phone.

    Held here rather than in the writer's tests because it is not about a
    generation: it is about the words we ship with the binary.
    """
    import importlib

    from alma.ai.validator import _PURPLE

    modules = {
        "ru": "alma.i18n.ru", "es": "alma.i18n.es", "de": "alma.i18n.de",
        "fr": "alma.i18n.fr", "it": "alma.i18n.it", "pt-BR": "alma.i18n.pt_BR",
    }
    offences: list[str] = []
    for locale, name in modules.items():
        banned = _PURPLE[locale]
        for system, chapters_of in importlib.import_module(name).CHAPTERS.items():
            for slug, words in chapters_of.items():
                for field in ("title", "question"):
                    text = (getattr(words, field, "") or "").lower()
                    for word in banned:
                        if word in text:
                            offences.append(
                                f"{locale} {system}/{slug} {field}: "
                                f"«{getattr(words, field)}» contains «{word}»"
                            )
    assert not offences, "\n".join(offences)
