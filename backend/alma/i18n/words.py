"""The two shapes a piece of Alma's copy comes in.

Their own module so that a translation file can import them without importing
the catalogue that collects the translation files — no partially-initialised
package, no import order to remember.

Both are dataclasses rather than tuples or dicts on purpose. A translator
opening `de.py` sees `title=` and `question=` written out beside the words,
which is the difference between a file somebody can edit confidently and a
file where the second element of a pair might be either. A misspelled field
name is a TypeError at import; a misspelled dict key would be a chapter that
silently reads in English.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChapterWords:
    """What one chapter is called, and what it asks.

    The title is a noun phrase — the name of a room in somebody's chart. The
    question is the reader's own, in their own voice, and it is the thing that
    makes them tap. Neither is a heading.
    """

    title: str
    question: str


@dataclass(frozen=True, slots=True)
class AxisWords:
    """The two ends of one synthesis axis.

    Not the axis's *name* — that is an identifier and stays English
    everywhere; see the note at the top of `alma/i18n/__init__.py`. These are
    the two short clauses a reader is shown when three systems disagree about
    them, and they only work as a pair: they have to read as two ends of one
    line, in whatever language they are written.
    """

    negative: str
    positive: str


@dataclass(frozen=True, slots=True)
class Catalogue:
    """Every string this backend hands a reader, in one language."""

    locale: str
    #: system slug → chapter slug → the words.
    chapters: dict[str, dict[str, ChapterWords]]
    #: axis name (English, an identifier) → its two poles.
    axes: dict[str, AxisWords]
    #: False while the file is still the English text waiting to be replaced.
    #: `tests/test_locales.py` reads this: once it is True, any string still
    #: identical to the English fails the suite.
    written: bool
    #: Strings that are correctly the same word in this language as in
    #: English. Listed one at a time rather than guessed at, exactly as
    #: `scripts/check-locales.mjs` does for the web dictionaries.
    shared: frozenset[str]
