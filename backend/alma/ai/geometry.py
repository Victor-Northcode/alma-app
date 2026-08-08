"""Checking what the prose says *about* a factor, not merely that it cited one.

`validator.check` compares factor strings character for character, and that
catches the invented placement — a Mars in a sign the chart does not have. It
cannot catch the sentence that cites a real factor and then describes it
wrongly, because it never reads the sentence. Measured, on a reading this
product actually produced and shipped (Portland, 1999-09-14 04:35):

    "Mercury is also caught in the tension of the grand cross — it squares
     Mars and Pluto in Sagittarius."

Three claims. *Mars and Pluto in Sagittarius* is true — 7°29′ and 7°56′ ♐. The
other two are false, and the chart says so in the factor list that same reply
cited:

    ☿ Q ♂ · 0°52′                                   ← quintile, 72°, not square
    ☿ Q ♇ · 0°25′                                   ← quintile, 72°, not square
    grand cross: moon, saturn, venus, uranus         ← Mercury is not in it

The second error is worse than the first. A quintile is a soft aspect; the
sentence called it *tension*. The meaning was not merely imprecise, it was
inverted. And every gate passed, because `grand cross: moon, saturn, venus,
uranus (fixed)` **is** a real factor and **was** cited honestly. The validator
matched the string and never asked what the sentence claimed about it.

So this module reads the claims instead. Two shapes, because those are the two
the engine can adjudicate:

* **an aspect between two bodies** — "Mercury squares Mars". The engine either
  emitted an aspect between that pair or it did not, and if it did, it named
  which one.
* **membership in a configuration** — "Mercury is caught in the grand cross".
  A configuration factor carries its members by name.

Anything else a sentence might assert — a house meaning, a dignity, a mood — is
either checked elsewhere (`validator.dignity_drift`) or is interpretation,
which is what the reader is paying for and not a thing to police.

**Two verdicts, and the split is deliberate.** A *contradiction* — the chart
says quintile, the prose says square — is decidable and gets rejected outright.
An *unsupported* claim — an aspect between a pair the engine emitted nothing
for — is rejected too, but it is the weaker of the two: an aspect can be real
and fall outside the orb the engine uses, in which case we do not know it and
must not print it either. Both are wrong to ship. They are reported separately
so a failure that keeps recurring can be read for which kind it is.

**On false positives, which are the real risk here.** A guard that refuses
correct writing is worse than no guard, because it is spent on retries and
eventually on a reader who gets an error instead of an answer. Three defences,
all of them measured against the 46 readings and chat turns this product had
already stored:

1. Only a clause where **two known bodies flank a known aspect word** is a
   claim. "Venus and Mars sit together in your first house" asserts no aspect
   and is not read as one.
2. A **hypothetical clause is skipped** — "someone whose Mars squares your
   Venus" is about a person who does not exist yet, and the reader's chart
   cannot confirm or deny it.
3. A **definition is skipped** — "a full moon means the moon stands opposite
   the sun" is a statement about astronomy, not about this reader.

The first version of this check, without 2 and 3, flagged four paragraphs and
three of them were correct writing. That number is in the tests.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ..engine.zodiac import ASPECT_GLYPHS, PLANET_GLYPHS

# ── the vocabulary ──────────────────────────────────────────────────────────
#
# Bodies come from `i18n.placements`, which already carries all six languages
# and is asserted against both client apps by `tests/test_notify_strings.py`.
# Aspect words do not exist there, and the comment in that file says why: they
# are verbs, they conjugate, and the notification layer keeps them inside the
# localisation key instead. Prose uses them as nouns and as verbs both, so the
# table below carries every form a writer would reach for rather than a lemma.

from ..i18n.placements import PLACEMENTS

#: Every spelling of every aspect, in the six languages, mapped to the engine's
#: own name for it. Verb forms included ("squares", "opposes") because prose
#: uses them far more often than the noun; inflections included where a reader
#: would meet them. A word missing here means a claim goes unchecked, which is
#: the safe direction to fail — the same principle `DIGNITY_WORDS` is written
#: under.
ASPECT_WORDS: dict[str, tuple[str, ...]] = {
    "conjunction": (
        "conjunct", "conjunction", "conjoined",
        "conjuncion", "conjunto", "conjunta",
        "konjunktion", "konjunkt",
        "congiunzione", "congiunto", "congiunta",
        "conjonction", "conjoint",
        "conjuncao",
    ),
    "opposition": (
        "opposite", "opposition", "opposes", "opposed",
        "oposicion", "opuesto", "opuesta", "se opone",
        "gegenuber", "gegenueber",
        "opposizione", "opposto", "opposta",
        "oppose", "opposee",
        "oposicao", "oposto", "oposta",
    ),
    "trine": (
        "trine", "trines", "trined",
        "trigono", "trigona",
        "trigon",
        "trine a", "trigone",
    ),
    "square": (
        "square", "squares", "squared", "squaring",
        "cuadratura", "cuadrado", "cuadrada", "en cuadratura",
        "quadrat", "im quadrat",
        "quadrato", "quadrata",
        "carre", "carree",
        "quadratura",
    ),
    "sextile": ("sextile", "sextiles", "sextil", "sestile", "sextiliza"),
    "quincunx": ("quincunx", "inconjunct", "quincuncio", "quinconce", "quincunce"),
    "semisextile": ("semisextile", "semisextil", "halbsextil", "semisestile",
                    "semi sextile", "semissextil"),
    "semisquare": ("semisquare", "semi square", "semicuadratura", "halbquadrat",
                   "semiquadrato", "semi carre", "semiquadratura"),
    "sesquiquadrate": ("sesquiquadrate", "sesquisquare", "sesquicuadratura",
                       "anderthalbquadrat", "sesquiquadrato", "sesqui carre",
                       "sesquiquadratura"),
    "quintile": ("quintile", "quintil", "quintiles"),
    "biquintile": ("biquintile", "biquintil", "bicuintil"),
}

#: The configurations `zodiac.configurations` can emit, and what prose calls
#: them. The engine's key is the left-hand side and is exactly the prefix a
#: configuration factor is printed with.
CONFIGURATION_WORDS: dict[str, tuple[str, ...]] = {
    "grand cross": ("grand cross", "gran cruz", "grosses kreuz", "großes kreuz",
                    "gran croce", "croce grande", "grande croix", "grande cruz"),
    "grand trine": ("grand trine", "gran trigono", "grosses trigon", "großes trigon",
                    "grande trigono", "grand trigone"),
    "t-square": ("t square", "t-square", "cuadratura en t", "t quadrat",
                 "quadrato a t", "carre en t", "quadratura em t"),
    "stellium": ("stellium", "stellum", "amas"),
    "yod": ("yod", "finger of god", "dedo de dios", "finger gottes",
            "dito di dio", "doigt de dieu", "dedo de deus"),
    "kite": ("kite", "cometa", "drachen", "aquilone", "cerf volant", "pipa"),
}

#: Clauses that put a claim in somebody else's chart, or in no chart at all.
#: A hypothetical is not a statement about this reader and cannot be checked
#: against this reader's factors — "someone whose Mars squares your Venus" is
#: advice about who to look for, and it is good writing.
_HYPOTHETICAL = re.compile(
    r"\b(someone|somebody|anyone|a person|a partner|whoever|if your|if their|"
    r"if you had|would be|were born|alguien|si tu|si su|jemand|wessen|wenn dein|"
    r"qualcuno|se il tuo|se la tua|quelqu un|quelqu'un|dont le|si ton|si ta|"
    r"alguem|se o seu|se a sua)\b"
)

#: Clauses that define a term rather than report a placement. "A full moon
#: means the moon stands opposite the sun" is astronomy; it is true of every
#: full moon and is not a claim about whose chart this is.
_DEFINITION = re.compile(
    r"\b(means|meaning|is what|is when|by definition|significa|quiere decir|"
    r"bedeutet|heisst|heißt|vuol dire|significato|signifie|veut dire|quer dizer)\b"
)

#: Aspect words that are a substring of a *configuration* name, and must not be
#: read as the aspect when they appear inside it.
#:
#: `\bsquare\b` matches inside "t-square", because the hyphen is a word
#: boundary. Measured, that turned every correct sentence naming a t-square —
#: *"Pluto, apex of a t-square with your moon and Jupiter"* — into two invented
#: aspect claims. A t-square is a configuration and is checked as one.
_NOT_AN_ASPECT = re.compile(r"(?:\bt|\bsemi|\bsesqui)[\s-]*$")


#: Where one claim stops and the next begins.
#:
#: A full stop, and nothing softer. The first version broke on the em dash too
#: and that is what let the measured sentence through: *"Mercury is caught in
#: the grand cross — it squares Mars and Pluto"* became two fragments, the
#: first holding a configuration and no verb, the second holding a verb whose
#: subject was the pronoun *it*. Both halves passed. An em dash joins a clause
#: to its subject far more often than it ends a thought, so it is punctuation
#: here and not a boundary.
_SENTENCE_BREAK = re.compile(r"[.!?;\n]+")


def _fold(value: str) -> str:
    """Strip accents and case so `Plutón`, `Pluton` and `pluton` are one word."""
    folded = unicodedata.normalize("NFKD", value)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return folded.lower()


#: Every name every body answers to, folded, mapped to the engine's key.
_BODY_NAMES: dict[str, str] = {}
for _key, _row in PLACEMENTS.items():
    for _name in _row.values():
        _BODY_NAMES[_fold(_name)] = _key
    _BODY_NAMES[_fold(_key.replace("_", " "))] = _key
# The engine emits `true_node` and `mean_node`; both are the north node and a
# reader is never told which computation produced it. Prose says "north node",
# and a claim about it must match a factor carrying either key.
_BODY_NAMES["north node"] = "true_node"
_BODY_NAMES["nodo norte"] = "true_node"
_BODY_NAMES["nordknoten"] = "true_node"
_BODY_NAMES["nodo nord"] = "true_node"
_BODY_NAMES["noeud nord"] = "true_node"

#: Glyph → key, for parsing the factor strings, which are always glyphs.
_GLYPH_TO_BODY = {glyph: key for key, glyph in PLANET_GLYPHS.items()}
_GLYPH_TO_ASPECT = {glyph: name for name, glyph in ASPECT_GLYPHS.items()}

#: Nodes are one point with two computations and one glyph. `PLANET_GLYPHS`
#: maps both to ☊, so the dict above keeps only whichever came last; pin it.
_GLYPH_TO_BODY["☊"] = "true_node"

_NODE_KEYS = {"true_node", "mean_node"}


def _same_body(a: str, b: str) -> bool:
    """Whether two engine keys name the same point."""
    if a == b:
        return True
    return a in _NODE_KEYS and b in _NODE_KEYS


@dataclass(frozen=True, slots=True)
class Claim:
    """One assertion the prose makes that the engine can adjudicate."""

    kind: str          # "aspect" | "membership"
    first: str         # engine key, or the configuration name for a membership
    second: str        # engine key
    relation: str      # aspect name, or "" for a membership
    clause: str        # the sentence it was read from, for the complaint


@dataclass(frozen=True, slots=True)
class Drift:
    contradicted: tuple[str, ...] = ()
    unsupported: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.contradicted or self.unsupported)

    def complaint(self) -> str:
        """What to tell the model, naming the factor it should have read."""
        parts: list[str] = []
        if self.contradicted:
            parts.append(
                "These sentences describe the chart wrongly — the placement is "
                "in the factor list and says something else: "
                + "; ".join(self.contradicted[:4])
                + ". Say what the factor says, or drop the sentence."
            )
        if self.unsupported:
            parts.append(
                "These sentences assert a geometry that is not in the data you "
                "were given: "
                + "; ".join(self.unsupported[:4])
                + ". Only name an aspect that appears in the factor list."
            )
        return " ".join(parts)


def relations(factors: list[str] | tuple[str, ...]) -> tuple[dict, dict]:
    """What the engine actually asserts: aspects between pairs, and memberships.

    Returns `(aspects, configurations)` where `aspects` maps an unordered pair
    of engine keys to the set of aspect names asserted between them, and
    `configurations` maps a configuration name to the set of its members.
    """
    aspects: dict[frozenset[str], set[str]] = {}
    configurations: dict[str, set[str]] = {}

    for raw in factors:
        text = str(raw)

        # `stellium: mean_node, moon, true_node (3 bodies in Virgo)`
        head, sep, tail = text.partition(":")
        name = _fold(head).strip()
        if sep and name in CONFIGURATION_WORDS:
            members = tail.split("(")[0]
            found = {
                _BODY_NAMES[_fold(part).strip()]
                for part in members.split(",")
                if _fold(part).strip() in _BODY_NAMES
            }
            if found:
                configurations.setdefault(name, set()).update(found)
            continue

        # `♀ △ ♄ · 6°50′` and `transiting uranus □ natal neptune · orb 0.17°`.
        # The aspect is a glyph in both shapes — the words around it name the
        # bodies, and whether they are glyphs or spelled out varies by system.
        for glyph, aspect in _GLYPH_TO_ASPECT.items():
            if glyph not in text:
                continue
            left, _, right = text.partition(glyph)
            first, second = _body_in(left), _body_in(right)
            if first and second:
                aspects.setdefault(frozenset((first, second)), set()).add(aspect)
            break
        else:
            # Quintile and biquintile are letters rather than glyphs — `☿ Q ♇`
            # — so they cannot be found by scanning for a symbol.
            match = re.search(r"\s(bQ|Q)\s", text)
            if match:
                aspect = "biquintile" if match.group(1) == "bQ" else "quintile"
                first = _body_in(text[: match.start()])
                second = _body_in(text[match.end():])
                if first and second:
                    aspects.setdefault(frozenset((first, second)), set()).add(aspect)

    return aspects, configurations


def _body_in(fragment: str) -> str | None:
    """The one body named in a fragment of a factor string, if exactly one is."""
    for glyph, key in _GLYPH_TO_BODY.items():
        if glyph in fragment:
            return key
    folded = _fold(fragment)
    for name, key in _BODY_NAMES.items():
        if re.search(rf"\b{re.escape(name)}\b", folded):
            return key
    return None


def claims(text: str) -> list[Claim]:
    """Every checkable assertion in a piece of prose.

    Scanned over the whole passage rather than sentence by sentence, because
    the subject of a claim is very often a pronoun whose antecedent is in the
    sentence before — *"Mercury is caught in the grand cross. It squares Mars"*
    — and a guard that reads one sentence at a time sees a verb with nobody
    doing it and passes. The **object** must still share a sentence with its
    verb: that is what stops a body three sentences later being paired with an
    aspect it was never near.
    """
    folded = _fold(text)

    # The sentence each character belongs to, so an object can be required to
    # share one with its verb while a subject may be looked up further back.
    bounds: list[tuple[int, int]] = []
    start = 0
    for match in _SENTENCE_BREAK.finditer(folded):
        bounds.append((start, match.start()))
        start = match.end()
    bounds.append((start, len(folded)))

    def sentence_at(pos: int) -> tuple[int, int]:
        for lo, hi in bounds:
            if lo <= pos <= hi:
                return lo, hi
        return 0, len(folded)

    # `(start, end, key)` — the end matters: advancing a cursor past an object
    # by one character lands inside the word, and the next gap reads as "ars
    # and " rather than " and ", which ends the list one item early. That cost
    # the Pluto half of the measured sentence.
    bodies = sorted(
        (m.start(), m.end(), key)
        for name, key in _BODY_NAMES.items()
        for m in re.finditer(rf"\b{re.escape(name)}\b", folded)
    )
    if not bodies:
        return []

    found: list[Claim] = []

    # A conjunction is the one aspect prose usually declines to name. It says a
    # planet *sits on* another point, and means the same thing. Recorded in
    # `docs/CONVERSATION.md` §4.4 from a live reading: *"your sun … sits almost
    # exactly on your Midheaven — 0°05′ apart"*, where the factor is `☉ ⚹ MC ·
    # 0°05′` — a **sextile**, sixty degrees, whose orb of five arcminutes the
    # sentence reprinted as the distance between them. Nothing in the aspect
    # vocabulary could see it, because the sentence never uses an aspect word.
    #
    # The gap between the verb and "on" is bounded rather than fixed, so
    # "sits on", "sits right on" and "sits almost exactly on" are one pattern.
    # A claim still needs two recognised points either side, which is what
    # keeps "sits on the cusp of the second house" out of it: a house is not a
    # body and forms no pair.
    for hit in re.finditer(
        r"\b(?:sits?|sitting|falls?|lands?|rests?|steht|liegt|esta|se trova|"
        r"se trouve|fica)\b[^.;!?]{0,26}?\b(?:on|auf|sobre|su|sur|em cima de)\b",
        folded,
    ):
        lo, hi = sentence_at(hit.start())
        if _HYPOTHETICAL.search(folded[lo:hi]) or _DEFINITION.search(folded[lo:hi]):
            continue
        before = [k for pos, _end, k in bodies if pos < hit.start()]
        after = [k for pos, _end, k in bodies if hit.end() < pos <= hi]
        if before and after and not _same_body(before[-1], after[0]):
            found.append(
                Claim("aspect", before[-1], after[0], "conjunction", text[lo:hi])
            )

    for aspect, words in ASPECT_WORDS.items():
        for word in words:
            for hit in re.finditer(rf"\b{re.escape(word)}\b", folded):
                # "t-square", "semisquare" and "sesquiquadrate" all contain a
                # shorter aspect word behind a boundary the regex honours.
                if _NOT_AN_ASPECT.search(folded[max(0, hit.start() - 8):hit.start()]):
                    continue
                lo, hi = sentence_at(hit.start())
                clause = text[lo:hi]
                if _HYPOTHETICAL.search(folded[lo:hi]) or _DEFINITION.search(
                    folded[lo:hi]
                ):
                    continue
                # The subject may be a pronoun standing for a body named
                # earlier; the object may not.
                before = [k for pos, _end, k in bodies if pos < hit.start()]
                after = [(pos, end, k) for pos, end, k in bodies if hit.end() < pos <= hi]
                if not before or not after:
                    continue
                subject = before[-1]
                # "it squares Mars and Pluto" is two claims, not one. Taking
                # only the first object would have checked Mars and let Pluto
                # through — which is half of the measured failure.
                #
                # But the run has to stop where the list does. Sweeping every
                # body left in the sentence read *"Mercury quintiles Mars and
                # Pluto, and the grand cross is carried by your moon, saturn,
                # venus and uranus"* as four more claims about Mercury — four
                # false positives on a sentence that is entirely correct. So
                # an object is only an object while nothing but separators
                # stands between it and the one before it.
                cursor = hit.end()
                for pos, end, obj in after:
                    if not _thin(folded[cursor:pos]):
                        break
                    cursor = end
                    if not _same_body(subject, obj):
                        found.append(Claim("aspect", subject, obj, aspect, clause))

    for configuration, words in CONFIGURATION_WORDS.items():
        for word in words:
            for hit in re.finditer(rf"\b{re.escape(word)}\b", folded):
                lo, hi = sentence_at(hit.start())
                if _HYPOTHETICAL.search(folded[lo:hi]) or _DEFINITION.search(
                    folded[lo:hi]
                ):
                    continue
                clause = text[lo:hi]
                # Which body the sentence actually puts *inside* the figure.
                #
                # Naively taking the nearest body before the name reads
                # *"Mercury quintiles Mars and Pluto, and the grand cross is
                # carried by your moon…"* as a claim that **Pluto** is in the
                # cross — measured, a false positive on correct writing. What
                # separates the two is grammar: in the failing sentence the
                # body and the figure sit in one uninterrupted phrase
                # ("Mercury is caught in the tension of the grand cross"),
                # and in the correct one a comma and a conjunction stand
                # between them, which is where the subject changed.
                claimed: list[str] = []
                before = [(pos, end, k) for pos, end, k in bodies if lo <= pos < hit.start()]
                if before:
                    pos, _end, key = before[-1]
                    joining = folded[pos:hit.start()]
                    if "," not in joining and not re.search(r"\band\b|\by\b|\bund\b|\be\b|\bet\b", joining):
                        claimed.append(key)
                # A figure may also name its own members — "the grand cross of
                # moon, saturn, venus and mercury". Only `of` and `between`
                # introduce a member list; "is carried by" introduces the same
                # bodies in a sentence that is describing rather than placing,
                # and both forms are correct writing when the names are right.
                after = [(pos, end, k) for pos, end, k in bodies if hit.end() < pos <= hi]
                if after:
                    lead = folded[hit.end():after[0][0]]
                    if re.search(r"\b(of|between|de|entre|von|zwischen|di|tra|fra|d)\b", lead) \
                            and "," not in lead:
                        claimed.extend(k for _pos, _end, k in after)
                for member in dict.fromkeys(claimed):
                    found.append(Claim("membership", configuration, member, "", clause))

    return found


def drift(text: str, factors: list[str] | tuple[str, ...]) -> Drift:
    """Claims in `text` that `factors` contradict, or do not support.

    `factors` is the whole reading's factor list rather than one paragraph's
    citations, and that scope is deliberate. A paragraph may legitimately refer
    back to what an earlier one established — *"a milder contact than the
    Uranus–Neptune square"* was flagged by the paragraph-scoped version and is
    correct writing, because that square is in the same reading. What is never
    legitimate is naming geometry the chart does not have at all.
    """
    # No chart, no adjudication. A turn that cited nothing — a greeting, an
    # aside — has no factor list behind it, and calling every aspect in it
    # unsupported would refuse the one shape this product deliberately allows
    # to claim nothing at all.
    if not factors:
        return Drift()

    aspects, configurations = relations(factors)
    contradicted: list[str] = []
    unsupported: list[str] = []

    for claim in claims(text):
        if claim.kind == "membership":
            members = configurations.get(claim.first)
            if members is None:
                # No such configuration in this chart. Prose may be explaining
                # what a t-square is rather than saying this reader has one,
                # and the definition guard cannot catch every phrasing, so
                # this is left alone.
                continue
            if not any(_same_body(claim.second, m) for m in members):
                named = ", ".join(sorted(members))
                contradicted.append(
                    f"\"{_trim(claim.clause)}\" — the {claim.first} is "
                    f"{named}, and {claim.second} is not in it"
                )
            continue

        held = _lookup(aspects, claim.first, claim.second)
        if held is None:
            unsupported.append(
                f"\"{_trim(claim.clause)}\" — no aspect between "
                f"{claim.first} and {claim.second} is in the factor list"
            )
        elif claim.relation not in held:
            actual = ", ".join(sorted(held))
            contradicted.append(
                f"\"{_trim(claim.clause)}\" — the chart has {claim.first} "
                f"{actual} {claim.second}, not {claim.relation}"
            )

    return Drift(
        contradicted=tuple(dict.fromkeys(contradicted)),
        unsupported=tuple(dict.fromkeys(unsupported)),
    )


def _lookup(aspects: dict, first: str, second: str) -> set[str] | None:
    """Aspects held between two points, tolerating the node's two keys."""
    direct = aspects.get(frozenset((first, second)))
    if direct is not None:
        return direct
    if first in _NODE_KEYS or second in _NODE_KEYS:
        for pair, held in aspects.items():
            a, b = tuple(pair) if len(pair) == 2 else (next(iter(pair)),) * 2
            if (_same_body(a, first) and _same_body(b, second)) or (
                _same_body(a, second) and _same_body(b, first)
            ):
                return held
    return None


#: Words that may stand between a verb and its object, or between two objects,
#: without the list having ended: separators, the six languages' "and"/"or",
#: articles and possessives. Anything else is a new clause.
_THIN = re.compile(
    r"^[\s,]*(?:(?:and|or|y|o|e|ed|und|oder|et|ou|the|your|his|her|their|its|"
    r"a|an|to|with|tu|su|sua|seu|dein|deine|ton|ta|tuo|tua|il|la|le|los|las|"
    r"el|der|die|das|natal|transiting|"
    # The preposition that carries an aspect to its object. English
    # says "square *to*"; the other five say "zu", "con", "avec",
    # "com", "a". Without these the object sat on the far side of a
    # word the joiner did not recognise and every non-English claim
    # went unchecked — which is a check that only works in the language
    # it was written in, and this product ships in six.
    r"zu|mit|con|contra|avec|com|au|aux|al|ao|alla|allo|ai|agli|dem|den)[\s,]*)*$"
)

#: A comma before a conjunction ends the clause rather than continuing a list.
#: *"Saturn squares your Midheaven, and your Mercury rules that same
#: Midheaven"* is two statements; without this the second subject was read as
#: a third object of the first verb, and Saturn was accused of an aspect to
#: Mercury that nobody had claimed. An Oxford comma in a genuine list of three
#: is lost to this, which is the safe direction: a missed check ships correct
#: prose, a false one refuses it.
_CLAUSE_JOIN = re.compile(r",\s*(?:and|but|which|while|so|though|y|pero|und|aber|e|ma|et|mais|mas)\b")


#: A gloss set off from the sentence: brackets, or a pair of dashes.
#:
#: `CHAT_RULES` asks her to explain a term the first time she uses it, and she
#: does — *"Mercury makes a quincunx (a 150° angle — two things that don't talk
#: the same language) to Pluto"*. That parenthetical sits between the aspect
#: and its object, so the joiner stopped being thin and the claim was never
#: read. Measured on a live turn, and the claim it hid was false: the chart has
#: `☿ Q ♇`, a **quintile**. A product that asks for glosses cannot have a guard
#: that a gloss switches off.
_ASIDE = re.compile(r"\([^)]*\)|\[[^\]]*\]|[—–][^—–]*[—–]")


def _thin(joiner: str) -> bool:
    """Whether a list is still running across this gap."""
    joiner = _ASIDE.sub(" ", joiner)
    if _CLAUSE_JOIN.search(joiner):
        return False
    return bool(_THIN.match(joiner))


def _trim(clause: str, limit: int = 120) -> str:
    clause = re.sub(r"\s+", " ", clause).strip()
    return clause if len(clause) <= limit else clause[: limit - 1] + "…"
