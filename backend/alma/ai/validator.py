"""Checking that a reading only says what the engine actually knows.

This is the part that makes the product defensible. A language model asked
about a birth chart will produce beautiful, fluent, specific astrology whether
or not it was given a chart — and the invented version is indistinguishable
from the real one to everybody except the person who built the engine. So
every generated paragraph carries the factor strings it was read from, and
this module checks them against the CalcResult, character for character.

Three failure modes, each with its own verdict:

* **Invented** — a cited factor that does not exist. The reading is rejected
  and regenerated. This is the one that matters: a plausible-sounding
  hallucinated placement is exactly what a competitor's product is made of.
* **Uncited** — a paragraph that names no factor at all. Also rejected: an
  unsourced paragraph is unsourced whether or not it happens to be true.
* **Off-topic** — a cited factor that is real but was not offered to this
  chapter. A warning rather than a rejection, because a genuine cross-reference
  ("your Saturn again, from the career chapter") is good writing.

**One paragraph in a conversation may carry no factor, and that is not a hole
in the rule.** A chapter is nothing but claims, so `allow_uncited` stays 0
there. A chat turn is a person being answered, and the rules she is written
under ask for shapes a strict floor cannot express: a refusal has two halves
and only the second one reads from the chart; "that lands hard" comes before
any placement; a reply in the reader's own language opens with a sentence that
asserts nothing. Measured, that collision refused 3 of 17 real turns
(`docs/CONVERSATION.md` §12) — the questions about death, pregnancy and whether
it gets better — and what those readers got instead of an answer was an English
error string. The rule is *a claim about a person names its placement*; a
sentence that claims nothing was never covered by it. So one uncited paragraph
is tolerated, provided at least one other paragraph does cite. Not two: the
tolerance is for the sentence that opens or closes a reading, and a reply that
is mostly unsourced prose is the thing this module exists to refuse.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Paragraph:
    text: str
    factors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Verdict:
    ok: bool
    invented: tuple[str, ...] = ()
    uncited: tuple[int, ...] = ()          # paragraph indices
    too_short: bool = False               # fewer paragraphs than a chapter needs
    off_topic: tuple[str, ...] = ()
    empty: bool = False
    reasons: tuple[str, ...] = ()
    #: How many uncited paragraphs this check was willing to tolerate. Carried
    #: on the verdict so the complaint can offer the tolerance rather than
    #: demand the impossible: told flatly that *every* paragraph must cite, a
    #: model asked to open with an acknowledgement will invent a factor for the
    #: acknowledgement, which is the failure this whole module exists to stop.
    uncited_allowed: int = 0

    def complaint(self) -> str:
        """What to tell the model on the retry, in its own terms."""
        parts: list[str] = []
        if self.empty:
            parts.append("The reading was empty. Write the chapter.")
        if self.invented:
            listed = "; ".join(self.invented[:6])
            parts.append(
                "These factors do not exist in the data you were given and must "
                f"not appear anywhere in the reading: {listed}. Use only the "
                "factors from the list, copied exactly."
            )
        if self.uncited:
            which = ", ".join(str(i + 1) for i in self.uncited)
            if self.uncited_allowed:
                parts.append(
                    f"Paragraph(s) {which} cite no factor. At most "
                    f"{self.uncited_allowed} paragraph may carry none — keep the "
                    "one that says nothing about them, and either name a factor "
                    "for the rest or fold them into a paragraph that has one."
                )
            else:
                parts.append(
                    f"Paragraph(s) {which} cite no factor. Every paragraph must "
                    "name at least one factor it was read from, or be deleted."
                )
        return " ".join(parts)


def _normalise(value: str) -> str:
    """Fold a factor string to something two spellings can agree on.

    Models reproduce a factor with a different dash, a collapsed space or a
    stray capital far more often than they invent one outright, and rejecting
    a correct citation over a typographic difference would make the validator
    the thing that breaks the product.
    """
    folded = unicodedata.normalize("NFKD", value)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = folded.replace("′", "'").replace("’", "'").replace("″", '"')
    # Every separator becomes a space. A model that writes "Mars 5°00′ — house 1"
    # where we wrote "· house 1" has cited correctly, and rejecting it over a
    # dash would make the validator the thing that breaks the product.
    folded = re.sub(r"[·•|,;–—−-]+", " ", folded)
    folded = re.sub(r"\s+", " ", folded)
    return folded.strip().lower()


def normalise(value: str) -> str:
    """The folding above, under a name other modules may use.

    Two factor strings are the same factor when they fold to the same thing,
    and more than this module now needs to ask that question — the chat's
    "you have cited nothing new" fence compares this turn's citations against
    earlier ones and must agree with the validator about what counts as the
    same placement.
    """
    return _normalise(value)


def check(
    paragraphs: list[Paragraph] | tuple[Paragraph, ...],
    *,
    allowed: list[str] | tuple[str, ...],
    offered: list[str] | tuple[str, ...] | None = None,
    minimum: int = 1,
    allow_uncited: int = 0,
) -> Verdict:
    """Validate a generated reading against the factors that produced it.

    `allow_uncited` is how many paragraphs may name no factor at all, and it
    is only ever non-zero for a conversation — the reasoning is in this
    module's docstring. It buys nothing unless something else cites: a reply
    where *no* paragraph names a placement is refused however small the
    tolerance, because that is a reading with no chart behind it.
    """
    if not paragraphs:
        return Verdict(ok=False, empty=True, reasons=("nothing was generated",))

    # `minimum` rather than a constant, because this function checks two
    # different things. A chapter is not a chapter at one paragraph — the
    # writer passes 2. A chat answer legitimately is one, so it passes 1.
    # The floor used to sit in the JSON schema as `"minItems": 2`, which the
    # API rejects outright: arrays there accept only 0 or 1. It belongs on
    # this side anyway — a schema says what the model may emit, a validator
    # says what we are willing to ship, and only the second one can refuse.
    too_short = len(paragraphs) < minimum

    known = {_normalise(f): f for f in allowed}
    on_topic = {_normalise(f) for f in (offered if offered is not None else allowed)}

    invented: list[str] = []
    blank: list[int] = []
    unsourced: list[int] = []
    cited_count = 0
    off_topic: list[str] = []

    for index, paragraph in enumerate(paragraphs):
        # A paragraph with no text is not a paragraph. It is never tolerated,
        # whatever `allow_uncited` says, because the tolerance is for a
        # *sentence that claims nothing* — not for an empty slot in the array.
        if not paragraph.text.strip():
            blank.append(index)
            continue
        if not paragraph.factors:
            unsourced.append(index)
            continue

        cited_count += 1
        for cited in paragraph.factors:
            key = _normalise(cited)
            if key not in known:
                invented.append(cited)
            elif key not in on_topic:
                off_topic.append(cited)

    # The tolerance is spent on the *first* uncited paragraph, because that is
    # where the shapes the rules ask for put it — the acknowledgement, the half
    # of a refusal that says no, the line in the reader's own language. A
    # trailing uncited paragraph is far more often a conclusion drawn about the
    # person, which is exactly the thing that has to name where it came from.
    tolerated = allow_uncited if cited_count else 0
    uncited = sorted(blank + unsourced[tolerated:])

    reasons: list[str] = []
    # Length is collected rather than returned early, so one complaint carries
    # every problem. Telling the model only "too short" spends an attempt on
    # length and lets it invent the same placement again on the next one —
    # and there are only three attempts before the chapter is refused.
    if too_short:
        reasons.append(f"only {len(paragraphs)} paragraph(s); this needs {minimum}")
    if invented:
        reasons.append(f"{len(invented)} invented factor(s)")
    if uncited:
        reasons.append(f"{len(uncited)} uncited paragraph(s)")

    return Verdict(
        ok=not invented and not uncited and not too_short,
        invented=tuple(dict.fromkeys(invented)),
        uncited=tuple(uncited),
        off_topic=tuple(dict.fromkeys(off_topic)),
        too_short=too_short,
        reasons=tuple(reasons),
        uncited_allowed=tolerated,
    )


#: Phrases that promise a specific event rather than describing a disposition.
#: Not a content filter — a product rule. Alma describes patterns; an app that
#: tells someone when they will die, or that their test results will be fine,
#: is a different and much worse product.
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\byou will (die|be diagnosed|get (cancer|sick))\b", "predicts death or diagnosis"),
    (r"\byou (will|are going to) be pregnant\b", "predicts pregnancy"),
    (r"\byou will (win|lose) (the )?(case|lawsuit|trial)\b", "predicts a legal outcome"),
    (r"\b(guaranteed|certain) (profit|return|gain)\b", "promises a financial outcome"),
    (r"\bdo not (see|consult) a (doctor|lawyer)\b", "discourages professional advice"),
    (r"\byour (partner|husband|wife|ex) (is|has been) (cheating|lying)\b",
     "asserts a third party's private conduct"),
)


#: Words that turn a forbidden sentence into the sentence we want.
#:
#: `\byou will die\b` matched *"I cannot tell you when you will die"* — the
#: only correct answer to the question, and the one this guard fired on. Logged
#: live: `chat attempt 1 broke a rule: predicts death or diagnosis`, burning one
#: of two attempts on the reply that obeyed the rule, and pushing the turn
#: towards the 422 the reader actually saw (`docs/CONVERSATION.md` §12). The two
#: blast radii overlap exactly: the questions where the pattern is most likely
#: to misfire are the questions where a refusal is the only shippable answer.
#:
#: Rejected alternative: dropping the patterns and trusting the prompt. The
#: bare assertion — "you will be diagnosed in March" — is the product risk this
#: guard exists for, and it stays caught. What changes is that a negation in the
#: same clause exempts it, which is a thing regex can check and meaning is not.
_NEGATION = re.compile(
    r"\b(cannot|can ?not|can't|could not|couldn't|do not|don't|does not|doesn't|"
    r"will not|won't|would not|wouldn't|never|no one|nobody|nothing|not|unable|"
    r"refuse|decline)\b"
)

#: How far back a negation may sit and still be about this clause.
_NEGATION_WINDOW = 80


def safety(text: str) -> list[str]:
    """Product-rule violations in generated prose, if any.

    A match is only a violation when nothing in the same clause negates it. The
    clause, not the paragraph: "I do not read the future. You will die at 61."
    is two sentences and the second one is the violation, so the search window
    stops at the last sentence break rather than sweeping up a disclaimer from
    somewhere earlier.
    """
    lowered = text.lower()
    reasons: list[str] = []
    for pattern, reason in FORBIDDEN_PATTERNS:
        for match in re.finditer(pattern, lowered):
            before = lowered[: match.start()]
            cut = max(before.rfind("."), before.rfind("!"), before.rfind("?"),
                      before.rfind("\n"), before.rfind(";"))
            clause = before[cut + 1:][-_NEGATION_WINDOW:]
            if _NEGATION.search(clause):
                continue
            reasons.append(reason)
            break
    return reasons


#: The four dignities the engine puts in a factor string, and the words prose
#: uses for each in the six languages this product ships in.
#:
#: A cited factor covers the claim it carries and no more. Measured: *"Júpiter
#: … está exaltado"* is true of this chart, and the factor cited beside it was
#: `natal: ruler of the eighth (jupiter) in house 2`, which says nothing about
#: dignity (`docs/CONVERSATION.md` §11). It happened to be right. The next one
#: is a coin toss, and a reader who checks one citation and finds it does not
#: support the sentence loses the meaning of every other citation in the app.
#:
#: This checks *strings*, so it is deliberately a nudge and not a gate: see
#: `conversation._dignity_drift`, which spends an attempt on it and never a
#: 422. A dignity word in a language we do not ship simply is not in this table
#: and the check quietly does nothing, which is the right way for it to fail.
DIGNITY_WORDS: dict[str, tuple[str, ...]] = {
    "exaltation": ("exaltation", "exalted", "exaltación", "exaltado", "exaltada",
                   "erhöhung", "erhöht", "esaltazione", "esaltato", "exaltation",
                   "exalté", "exaltada", "exaltação"),
    "fall": ("in fall", "im fall", "en caída", "in caduta", "en chute", "em queda"),
    "detriment": ("detriment", "detrimento", "exil", "esilio", "exilio"),
    "rulership": ("rulership", "domicile", "domicilio", "domizil", "domicile"),
}


def dignity_drift(paragraphs: list[Paragraph] | tuple[Paragraph, ...]) -> list[str]:
    """Dignity words in prose that the paragraph's own citations do not carry."""
    drifted: list[str] = []
    for paragraph in paragraphs:
        if not paragraph.factors:
            continue
        prose = _normalise(paragraph.text)
        sources = _normalise(" ".join(paragraph.factors))
        for dignity, words in DIGNITY_WORDS.items():
            if dignity in sources:
                continue
            # Normalised on both sides, so "exaltación" and "exaltacion" are
            # one word and a stray accent is not the thing that decides.
            if any(_normalise(word) in prose for word in words):
                drifted.append(dignity)
    return list(dict.fromkeys(drifted))


def parse(payload: dict) -> tuple[str, list[Paragraph]]:
    """Pull a title and paragraphs out of a model response.

    Tolerant of the shapes a schema-constrained model actually returns —
    strings where a list was asked for, a missing title — because a structural
    quibble is not worth a regeneration when the content is fine.
    """
    title = str(payload.get("title") or "").strip()
    raw = payload.get("paragraphs") or []
    if isinstance(raw, dict):
        raw = [raw]

    paragraphs: list[Paragraph] = []
    for item in raw:
        if isinstance(item, str):
            paragraphs.append(Paragraph(item.strip(), ()))
            continue
        if not isinstance(item, dict):
            continue
        cited = item.get("factors") or []
        if isinstance(cited, str):
            cited = [cited]
        paragraphs.append(
            Paragraph(
                text=str(item.get("text") or "").strip(),
                factors=tuple(str(f).strip() for f in cited if str(f).strip()),
            )
        )
    return title, paragraphs


#: Russian bigrams that gender the reader — «ты рождён» tells half the readers
#: the text assumed they were men. Anchored on «ты»/fixed participles so that
#: «путь должен» and other innocent uses never trip it. Shared by the spheres
#: and the chapter writer, because the rule is the product's, not one route's.
RU_GENDERED: tuple[str, ...] = (
    "ты рождён", "ты рождена", "ты родился", "ты родилась", "ты был ",
    "ты была ", "ты должен", "ты должна", "ты сам ", "ты сама ",
    "ты готов ", "ты готова ", "ты одинок ", "ты одинока ", "ты хотел ",
    "ты хотела ", "ты решил ", "ты решила ", "быть понятым", "быть понятой",
)


def russian_gendered(text: str) -> list[str]:
    """The gendered forms present in a Russian text, for the retry complaint."""
    lowered = text.lower()
    return [b for b in RU_GENDERED if b in lowered]


def russian_latin_leak(text: str) -> list[str]:
    """Latin words stranded in Russian prose — «твой natal Уран», seen live.

    The factor identifiers are English and the model quotes them; most slips
    are a single untranslated word riding into the sentence. Only prose is
    checked — the `factors` arrays stay English by contract — and the one
    Latin word Russian prose is allowed is the product's own name.
    """
    import re
    allowed = {"alma"}
    roman = re.compile(r"^[IVXLCDM]+$")
    words = re.findall(r"[A-Za-z]{2,}", text)
    return sorted({
        w for w in words
        if w.lower() not in allowed and not roman.fullmatch(w)
    })
