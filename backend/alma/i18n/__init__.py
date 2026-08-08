"""The reader's own language, for the strings the backend writes itself.

Almost everything a reader sees is either their own chart or prose the model
generated, and both of those already arrive in their language. Two things did
not: the 41 chapter titles and questions in `alma/ai/chapters.py`, and the
eighteen pole clauses in `alma/engine/synthesis.py`. A German reader with a
German interface, a German store listing and a chapter written in German
opened the table of contents and read *"Core — What am I actually like,
underneath?"*. That title is the largest type on the screen and that question
is the reason anybody taps. This package is where the other five languages
live.

**Which strings are here, and which deliberately are not.**

An axis's *name* — "Direction", "Character", "Weak point" — is an identifier,
not copy, and nothing in this package translates it. It is the key
`synthesis.compute` files each system's signal under; it is a substring in the
synthesis chapter's `reads` tuple, which is how that chapter finds its
factors at all; and it appears inside `Synthesis.factors()`, which is the list
the writer is given, the list the model must cite from verbatim, and the list
`ai/validator.py` checks those citations against character by character. A
German axis name means the model cites "Richtung", the validator looks for it
in an English factor list, does not find it, calls it invented, and refuses
the reading after three attempts — the reader pays for a chapter and is told
it could not be written. Both clients already know this and already translate
the nine names themselves, keyed on the English word: `CabinetCopy.axis(_:)`
on iOS, `t.synthesis.axes` on the web.

`Axis.label` ("2 disagree", "seen by one") and `Synthesis.summary()` are
inside `factors()` for the same reason and are data for the same reason. The
clients translate those too.

What *is* copy is the pair of poles. No prompt contains them, no factor list
mentions them, they exist only in the payload served to a client — and they
are shown to a reader verbatim: "without them, '2 disagree' is a number with
no subject", as the iOS model puts it. So they are translated, under the
English axis name as their key. A translator never touches an identifier.

That makes the translatable surface **100 strings, not 109**. The nine axis
names are the nine that have to stay English.

**Why the words live apart from the definitions.**

`chapters.py` describes structure: which factors a chapter may read from, what
its word budget is, whether it needs a birth time, whether it is the free
sample. Changing a `reads` tuple changes which facts a chapter is allowed to
cite, and a chapter with no matching factors is not written at all. That is
not a file to hand five translators working in parallel. Each language gets
one file containing nothing but words, which also turns "is anything missing"
into a set comparison — `tests/test_locales.py` does exactly that, for all
100 strings in all six languages.

English is the one language with no file here. It stays where it has always
been, in the `Chapter` dataclasses and in `synthesis.AXES`, and the catalogue
reads it off them. A second copy of the English would be a second thing to
keep in step and it would be the copy that drifts; and the question a chapter
asks and the factors it reads from are two statements of the same editorial
decision, which belong next to each other. So the English cannot go missing,
and every other language is checked against it.
"""

from __future__ import annotations

from functools import lru_cache

from . import de as _de
from . import es as _es
from . import fr as _fr
from . import it as _it
from . import pt_BR as _pt_br
from . import ru as _ru
from .words import AxisWords, Catalogue, ChapterWords

__all__ = [
    "AxisWords",
    "Catalogue",
    "ChapterWords",
    "DEFAULT_LOCALE",
    "LOCALES",
    "MAX_TAG",
    "axis_words",
    "catalogue",
    "chapter_words",
    "localise_synthesis",
    "resolve",
]

#: The seven languages this product ships in, in the order `src/lib/i18n`
#: lists them. Anything else is a reader we have no words for.
LOCALES: tuple[str, ...] = ("en", "es", "de", "it", "fr", "pt-BR", "ru")

DEFAULT_LOCALE = "en"

#: How long a language tag a request may carry, before `resolve` gets to see
#: it. Every route that takes one used to cap it at 8 characters, which is
#: about the length of the six tags we ship and *not* the length of a tag a
#: client can honestly send: `zh-Hans-CN` is ten, `de-DE-1996` is ten,
#: `en_US_POSIX` is eleven. Each of those was a 422 with no body — a blank
#: table of contents — for a reader `resolve` would have answered in English
#: perfectly happily, which is the exact inverse of what its docstring
#: promises. 35 is the practical BCP-47 ceiling (language-script-region plus a
#: variant); anything longer is not a tag and is refused on its way in.
#:
#: This is only safe alongside resolving before storing: `Reading.locale` is a
#: `String(8)` column, so what goes into the database has to be one of the six
#: rather than whatever arrived.
MAX_TAG = 35


def resolve(locale: str | None) -> str:
    """Which of the six a reader actually gets.

    English is the fallback and it is chosen *here*, once, rather than falling
    out of a `dict.get(locale, english)` at each call site. That matters
    because the interesting cases are not "a language we do not ship": they
    are `"de-AT"`, `"pt_BR"` written with an underscore, and `"PT-br"` from a
    client that lower-cased its tag. Every one of those is a reader we *do*
    have words for, and every one of them lands on English under a plain
    dictionary lookup — silently, because English is what the screen looked
    like before anybody thought about it, so nothing looks broken.

    Portuguese is region-aware in the one direction that matters, which is the
    rule `src/lib/i18n/index.ts` already follows: we ship Brazilian Portuguese
    and nothing else, so a `pt-PT` reader gets Brazilian rather than English.
    It is far closer than the fallback.
    """
    if not locale:
        return DEFAULT_LOCALE

    tag = locale.strip().replace("_", "-")
    if not tag:
        return DEFAULT_LOCALE

    lowered = tag.lower()
    for shipped in LOCALES:
        if shipped.lower() == lowered:
            return shipped

    base = lowered.split("-")[0]
    if base == "pt":
        return "pt-BR"
    for shipped in LOCALES:
        if shipped.lower().split("-")[0] == base:
            return shipped

    # A language nobody has written yet. English, deliberately and knowingly:
    # a table of contents is not optional furniture, and a reader who gets it
    # in the wrong language can still use the product, where a reader who gets
    # an exception cannot.
    return DEFAULT_LOCALE


# ── the catalogue ──────────────────────────────────────────────────────────

#: The six files. English is absent on purpose — see the module docstring.
_TRANSLATIONS = {
    "es": _es, "de": _de, "it": _it, "fr": _fr, "pt-BR": _pt_br, "ru": _ru,
}


@lru_cache(maxsize=1)
def _english() -> Catalogue:
    """The English, read off the definitions instead of copied beside them.

    Imported inside the function rather than at module scope, and not for
    speed. `alma.ai.__init__` imports `voice` and `writer`, both of which ask
    this package for a locale; a module-scope import here would make that a
    cycle — `alma.i18n` half-built, importing `alma.ai`, which imports
    `alma.i18n` and finds `resolve` not yet defined. Deferring it means the
    two packages depend on each other only at call time, when both are whole.
    """
    from ..ai import chapters as chapter_defs
    from ..engine import synthesis

    return Catalogue(
        locale=DEFAULT_LOCALE,
        chapters={
            system: {
                chapter.slug: ChapterWords(chapter.title, chapter.question)
                for chapter in defined
            }
            for system, defined in chapter_defs.BY_SYSTEM.items()
        },
        axes={
            name: AxisWords(negative=negative, positive=positive)
            for name, negative, positive in synthesis.AXES
        },
        # The reference. It is written by definition.
        written=True,
        shared=frozenset(),
    )


def catalogue(locale: str) -> Catalogue:
    """Every string this backend hands a reader, in one language.

    Takes a locale as a client sent it, not a resolved one — `resolve` is the
    only place that decision is made and this is one of its callers.
    """
    resolved = resolve(locale)
    if resolved == DEFAULT_LOCALE:
        return _english()
    module = _TRANSLATIONS[resolved]
    return Catalogue(
        locale=resolved,
        chapters=module.CHAPTERS,
        axes=module.AXES,
        written=module.WRITTEN,
        shared=module.SHARED,
    )


# ── looking a string up ────────────────────────────────────────────────────

def chapter_words(
    system: str,
    slug: str,
    *,
    locale: str = DEFAULT_LOCALE,
    default: ChapterWords | None = None,
) -> ChapterWords:
    """One chapter's title and question, in the reader's language.

    Two fallbacks below the one in `resolve`, both field by field. A locale
    whose file is missing this chapter — or has it and left one of the two
    strings blank — falls back to the English for *that string only*, so a
    half-finished translation shows a mixed list rather than raising in front
    of a reader. `tests/test_locales.py` is what keeps that path from ever
    running in production; this is what it does if it ever gets there.

    A `(system, slug)` pair that is not in the catalogue at all is a different
    thing and raises `KeyError` — a caller bug, not a translation gap, and the
    route answers 404 for it long before reaching here. `default` is for the
    one caller that legitimately holds a `Chapter` which never came from
    `BY_SYSTEM`: `writer.build_prompt` is handed a chapter object, and a test
    fixture is entitled to invent one. It passes the chapter's own English so
    that inventing a chapter does not become inventing an exception.
    """
    try:
        english = _english().chapters[system][slug]
    except KeyError:
        if default is None:
            raise
        return default
    theirs = catalogue(locale).chapters.get(system, {}).get(slug)
    if theirs is None:
        return english
    return ChapterWords(
        title=theirs.title.strip() or english.title,
        question=theirs.question.strip() or english.question,
    )


def axis_words(name: str, *, locale: str = DEFAULT_LOCALE) -> AxisWords | None:
    """The two poles of one axis, in the reader's language.

    `None` for an axis this catalogue has never heard of, so the caller leaves
    the engine's own words in place rather than blanking them — the same rule
    the clients follow for an axis name they do not recognise.
    """
    english = _english().axes.get(name)
    if english is None:
        return None
    theirs = catalogue(locale).axes.get(name)
    if theirs is None:
        return english
    return AxisWords(
        negative=theirs.negative.strip() or english.negative,
        positive=theirs.positive.strip() or english.positive,
    )


def localise_synthesis(data: dict, *, locale: str) -> dict:
    """A synthesis payload with its poles in the reader's language.

    A **copy**, never a mutation. The `CalcResult` this dictionary belongs to
    is held in `api/cache.py` and handed to every request for the same birth,
    so rewriting it in place would translate one reader's chart into the
    language of whoever asked for it last. The cache is keyed on the birth and
    not on the locale, which is right: the arithmetic is identical in all six
    languages, and recomputing nine axes per language would be six times the
    work for the same nine numbers.

    Exactly three fields move — the two poles, and `direction`, which is
    whichever pole an agreeing axis landed on. The name, the verdict, the
    label, the signals and the factors they cite are data and stay English;
    the module docstring says why that is a decision rather than an oversight.
    """
    axes = data.get("axes")
    if not isinstance(axes, list):
        return data

    resolved = resolve(locale)
    if resolved == DEFAULT_LOCALE:
        return data

    translated: list = []
    for row in axes:
        words = axis_words(row.get("name", ""), locale=resolved) if isinstance(row, dict) else None
        if words is None:
            translated.append(row)
            continue

        # `direction` is one of the two pole strings by construction, so it is
        # matched against this row's own English poles rather than recomputed.
        # An axis that does not agree has no direction and keeps its None.
        direction = row.get("direction")
        if direction == row.get("positive_pole"):
            direction = words.positive
        elif direction == row.get("negative_pole"):
            direction = words.negative

        translated.append(
            row
            | {
                "positive_pole": words.positive,
                "negative_pole": words.negative,
                "direction": direction,
            }
        )

    return data | {"axes": translated}
