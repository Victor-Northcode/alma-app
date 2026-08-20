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
    #: How many paragraphs arrived and how many this piece needs. Carried for
    #: the same reason as `uncited_allowed`: so `complaint` can say what to do
    #: rather than only that something is wrong. Both default to zero, which
    #: is what every caller that never sets `minimum` above one will see.
    written: int = 0
    needed: int = 0

    def complaint(self) -> str:
        """What to tell the model on the retry, in its own terms.

        **Every fault that can set `ok=False` has to produce words here.**
        `too_short` did not, and the consequence was a retry that changed
        nothing: `writer.build_prompt` only appends the rejection block `if
        complaint`, so an empty string meant the second prompt was byte-for-byte
        the first one. A model handed the identical brief writes the identical
        answer, so a chapter that came back one paragraph short spent all three
        attempts on the same reply and was then refused — three real
        generations, no chapter, and nothing in the prompt that could have
        told the model what to change.
        """
        parts: list[str] = []
        if self.empty:
            parts.append("The reading was empty. Write the chapter.")
        if self.too_short:
            parts.append(
                f"You wrote {self.written} paragraph(s); this needs {self.needed}. "
                "Add the missing one(s), each naming a factor it was read from."
                if self.needed
                else "This is shorter than the chapter needs. Add a paragraph, "
                "naming a factor it was read from."
            )
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
    most_words: int | None = None,
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
    # **Потолок длины, а не только пол.**
    #
    # Проверка всех сорока одной главы нашла открывающий абзац на 108 слов при
    # заказанных 34–46. Длина просилась в промте и не сторожилась нигде, и в
    # этом месте это не косметика: абзац закрытой главы существует, чтобы
    # продать её, а на треть экрана он перестаёт быть началом и становится
    # содержанием, за которое человек уже не заплатит.
    #
    # Порог щедрый намеренно — полтора заказанных потолка. Ловить надо грубый
    # перебор, а не пять лишних слов: каждая жалоба стоит попытки, а их три.
    if most_words is not None:
        words_written = sum(len(p.text.split()) for p in paragraphs)
        if words_written > most_words:
            reasons.append(
                f"{words_written} words where at most {most_words} were asked for; "
                "cut it back to the length in the brief"
            )
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
        written=len(paragraphs),
        needed=minimum,
    )


#: Phrases that promise a specific event rather than describing a disposition.
#: Not a content filter — a product rule. Alma describes patterns; an app that
#: tells someone when they will die, or that their test results will be fine,
#: is a different and much worse product.
#:
#: **И это же — юридическая граница, которую держит ответ, а не дисклеймер.**
#: Продукт продаётся во всех сторах мира, и «медицинский совет» перестаёт быть
#: медицинским советом не оттого, что под ним написано «это развлечение».
#: Ниже — те же шесть правил, что были, плюс границы, которые до сих пор
#: просились только в промте: лечение, диагноз, деньги, право, самоповреждение,
#: возраст. Просьба — это предпочтение; проверка — это правило.
#:
#: **Ни один из них не про слово, все про утверждение.** «Инвестируй» ловится
#: только с объектом, которого в карте нет и быть не может (крипта, акции,
#: недвижимость); «you have depression» ловится, а «you have a heaviness about
#: mornings» — нет. Отрицание в том же предложении снимает совпадение (см.
#: `safety`), поэтому «я не скажу тебе, когда ты умрёшь» — единственный
#: правильный ответ на этот вопрос — проходит.
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\byou will (die|be diagnosed|get (cancer|sick))\b", "predicts death or diagnosis"),
    (r"\byou (will|are going to) be pregnant\b", "predicts pregnancy"),
    (r"\byou will (win|lose) (the )?(case|lawsuit|trial)\b", "predicts a legal outcome"),
    (r"\b(guaranteed|certain) (profit|return|gain)\b", "promises a financial outcome"),
    (r"\bdo not (see|consult) a (doctor|lawyer)\b", "discourages professional advice"),
    (r"\byour (partner|husband|wife|ex) (is|has been) (cheating|lying)\b",
     "asserts a third party's private conduct"),

    # ── медицина ───────────────────────────────────────────────────────────
    # Самая дорогая из границ: совет бросить назначенное — это вред, который
    # наступает в тот же день. Промт просил «скажи, что это разговор с тем, кто
    # назначил»; здесь это перестаёт быть просьбой.
    (r"\b(stop|come off|quit|skip|halve|double) (taking )?(your |the |his |her )?"
     r"(medication|medicine|meds|pills|tablets|antidepressants?|antipsychotics?|"
     r"insulin|chemo|chemotherapy|treatment)\b",
     "tells the reader what to do with a prescribed treatment"),
    # Доза — единственное число, которого в карте нет ни при каких условиях.
    (r"\b\d+\s?(mg|mcg|milligrams?)\b", "names a dose"),
    (r"\byou (have|suffer from|are suffering from) "
     r"(depression|bipolar|adhd|autism|schizophreni\w*|ocd|ptsd|anorexi\w*|bulimi\w*|"
     r"cancer|diabetes|an eating disorder|a personality disorder|an anxiety disorder)\b",
     "asserts a diagnosis"),
    (r"\byou are (bipolar|autistic|schizophrenic|clinically depressed|manic)\b",
     "asserts a diagnosis"),
    (r"\b(will|would|can) (cure|heal|fix) (your|the|his|her) "
     r"(illness|disease|cancer|depression|condition|symptoms)\b",
     "promises a cure"),

    # ── деньги ─────────────────────────────────────────────────────────────
    # Инвестиционная рекомендация — лицензируемая деятельность почти везде.
    # Привязано к объекту, а не к глаголу: «вложись в себя» — нормальная фраза
    # главы про второй дом, и она обязана остаться.
    (r"\b(invest|put your money) in (crypto\w*|bitcoin|ethereum|stocks?|shares|"
     r"the market|property|real estate|gold|that coin|this coin)\b",
     "recommends an investment"),
    (r"\b(you should|i (would )?(recommend|suggest|advise)|my advice is to) "
     r"(invest|sell your|buy shares|buy stock|take out a loan|borrow against)\b",
     "recommends a financial move"),
    (r"\b(sell|buy) (your (shares|stock|stocks|crypto|bitcoin|flat|house|home)|"
     r"before the (crash|drop))\b", "tells the reader to buy or sell"),

    # ── право ──────────────────────────────────────────────────────────────
    (r"\byou should (sue|file (a )?(lawsuit|suit|claim)|press charges|plead|"
     r"sign (the|that|this) (contract|agreement)|refuse to sign)\b",
     "gives legal advice"),
    (r"\byou (do not|don't) need (a|to see a) (lawyer|solicitor|attorney|doctor|"
     r"therapist|psychiatrist)\b", "tells the reader not to get professional help"),

    # ── самоповреждение ────────────────────────────────────────────────────
    # Ни одного контекста, в котором эта фраза от Alma допустима. Кризисный
    # разговор ведёт `conversation`, своим текстом, мимо модели вовсе.
    (r"\b(kill yourself|take your own life|end your life|hurt yourself|"
     r"harm yourself|cut yourself)\b", "speaks to self-harm"),

    # ── предсказание беды ──────────────────────────────────────────────────
    (r"\byou (only )?have \w+ (years|months|weeks) (left|to live)\b",
     "predicts a lifespan"),
    (r"\byour (mother|father|child|son|daughter|partner|husband|wife) will "
     r"(die|be diagnosed|get (cancer|sick))\b", "predicts a death or diagnosis"),
    (r"\b(there will be|expect) an? (accident|crash|earthquake|fire|disaster|attack)\b",
     "predicts a catastrophe"),

    # ── третьи лица ────────────────────────────────────────────────────────
    (r"\byour (partner|husband|wife|ex|boss|mother|father|friend) is "
     r"(abusive|a narcissist|manipulating you|using you|hiding)\b",
     "asserts a third party's private conduct"),

    # ── возраст и секс ─────────────────────────────────────────────────────
    # Узко и намеренно: восьмой дом, Венера и Марс говорят о близости, и это
    # астрология, а не эротика. Ловится только то, что в сторе называется
    # explicit — акт и анатомия, а не тема.
    (r"\b(blowjob|cunnilingus|masturbat\w+|your (genitals|penis|vagina|clitoris|"
     r"nipples|breasts))\b", "explicit sexual content"),
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


#: Что человек написал, когда ему нужен не гороскоп, а живой человек.
#:
#: **Единственная проверка в этом модуле, которая смотрит на вопрос, а не на
#: ответ, и единственная, написанная на семи языках.** Обе особенности из
#: одного довода. Все правила выше ловят то, что сказала Alma, — если она
#: ошиблась, попытку можно потратить и переписать. Здесь ошибиться нельзя ни
#: разу: ответ модели на «я не хочу жить» приходит один раз, и если он приходит
#: с трактовкой Луны, продукт уже сделал то, чего делать не имел права. Поэтому
#: путь кризисного сообщения не проходит через модель вовсе (см.
#: `conversation.answer`), а раз он детерминированный, он обязан работать в том
#: языке, на котором человек пишет, — английский список закрыл бы шесть седьмых
#: читателей.
#:
#: **Ловится намерение о себе, а не тема смерти.** «Когда я умру» — вопрос о
#: предсказании, на него отвечает `FORBIDDEN_PATTERNS` и обычный отказ; «я хочу
#: умереть» — это другое, и разница здесь везде проведена по первому лицу и
#: воле: `want to die`, `хочу умереть`, `ich will sterben`, а не по слову
#: «умереть». Идиомы («dying to know», «умираю с голоду») не первого лица и не
#: волевые, и мимо проходят.
#:
#: Сравнение идёт по `_normalise`, поэтому шаблоны пишутся без диакритики и без
#: дефисов: `suicidio` покрывает `suicídio`, `self harm` — `self-harm`.
CRISIS_PATTERNS: tuple[str, ...] = (
    # английский
    r"\bkill(ing)? myself\b", r"\bend (my life|it all)\b", r"\btake my own life\b",
    r"\b(commit|committing) suicide\b", r"\bsuicidal\b", r"\bsuicide\b",
    r"\b(want|wanted|wanna) to die\b", r"\b(don't|do not|dont) want to (live|be here)\b",
    r"\b(hurt|hurting|harm|harming|cut|cutting) myself\b", r"\bself harm\b",
    r"\bno reason to live\b", r"\bbetter off dead\b", r"\bno point in living\b",
    # испанский
    r"\bmatarme\b", r"\bsuicid", r"\bquitarme la vida\b", r"\bacabar con mi vida\b",
    # «no me quiero vivir» — сломанный испанский, но пишут именно так, и
    # проверка на кризис не место, где спрашивают с человека грамматику.
    r"\bno (me |ya )?quiero (seguir )?vivi", r"\bquiero morir(me)?\b", r"\bhacerme dano\b",
    # немецкий
    r"\bmich umbringen\b", r"\bselbstmord\b", r"\bsuizid", r"\bnicht mehr leben\b",
    r"\bmir das leben nehmen\b", r"\bmich verletzen\b", r"\bich will sterben\b",
    # итальянский
    r"\buccidermi\b", r"\bsuicid", r"\bfarla finita\b", r"\btogliermi la vita\b",
    r"\bnon voglio (piu )?vivere\b", r"\bvoglio morire\b", r"\bfarmi del male\b",
    # французский
    r"\bme tuer\b", r"\bsuicid", r"\ben finir avec la vie\b",
    r"\bmettre fin a mes jours\b", r"\bje ne veux plus vivre\b",
    r"\bje veux mourir\b", r"\bme faire du mal\b",
    # португальский
    r"\bme matar\b", r"\bacabar com a minha vida\b", r"\btirar a minha vida\b",
    r"\bnao quero (mais )?viver\b", r"\bquero morrer\b", r"\bme machucar\b",
    # русский
    r"\bубить себя\b", r"\bпокончить с собой\b", r"\bсуицид", r"\bсамоубийств",
    r"\bне хочу жить\b", r"\bне хочется жить\b", r"\bхочу умереть\b",
    r"\bсвести счеты с жизнью\b", r"\bпричинить себе вред\b", r"\b(режу|резал|резать) себя\b",
    r"\bнет смысла жить\b", r"\bлучше бы я умер",
)

_CRISIS = re.compile("|".join(CRISIS_PATTERNS), re.UNICODE)


def crisis(text: str) -> bool:
    """Whether this message is somebody in danger rather than a question.

    Deliberately **not** negation-aware, unlike `safety`. There the negation
    saves a correct refusal from its own subject matter; here the sentence
    belongs to the reader, and "I don't want to live" is the thing itself
    rather than a denial of it. Reading a negation as an all-clear is the one
    mistake this function is not allowed to make.
    """
    return bool(_CRISIS.search(_normalise(text)))


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


#: Words that sound like meaning and carry none, per language.
#:
#: **Why this is a gate and not only an instruction.** The voice already asked
#: for plain writing and the writing came back ornate anyway: measured over the
#: 124 Russian paragraphs this product had actually written, there were 2.72
#: dashes per paragraph, and the sentence the owner quoted back was «это ядро
#: гораздо менее эффектное, чем маска Водолея». An instruction that is followed
#: on Tuesday and not on Thursday is not a rule; `russian_gendered` and
#: `russian_latin_leak` are here for the same reason and this joins them.
#:
#: Russian and English are the lists that have been read word by word — Russian
#: because it is the owner's language and the one he judged, English because it
#: is the source. The other five are the obvious cognates and are deliberately
#: short: a banned-word list in a language nobody here has audited is a source
#: of refusals rather than of quality, and it costs a real generation each time
#: it is wrong. Widen them when somebody who reads that language has looked.
#: Оба апострофа — один и тот же апостроф, когда мы ищем слово в тексте модели.
#:
#: **Дефект был тихий и жил до правки типографики.** Список запрещённых слов
#: сверяется с текстом простым вхождением подстроки, а модель пишет апостроф
#: тем знаком, каким захочет: `l'univers` и `l’univers` — для `in` это разные
#: строки. То есть половина французских и итальянских записей списка не ловилась
#: никогда, и заметить это было нельзя — проверка не падает, она молчит.
#:
#: Свелось наружу тем, что типографику французского привели к «’»: список,
#: приведённый вместе с текстом, перестал бы ловить прямой апостроф вместо
#: кудрявого — то же самое, только в другую сторону. Значит чинить надо не
#: список, а сравнение.
def _fold_apostrophes(value: str) -> str:
    return value.replace("\u2019", "'").replace("\u02bc", "'")


_PURPLE: dict[str, tuple[str, ...]] = {
    "ru": (
        "ядро", "суть", "истинное я", "истинного я", "настоящий ты", "маска",
        "энергия", "энергии", "путь души", "предназначение", "вселенная",
        "сакральн", "вибрация", "вибрации",
    ),
    "en": (
        "essence", "true self", "the real you", "life force", "energy",
        "path of the soul", "the universe", "sacred", "vibration", "alignment",
    ),
    "es": ("esencia", "verdadero yo", "energía", "el universo", "sagrado", "vibración"),
    "de": ("essenz", "wesenskern", "wahres selbst", "energie", "das universum", "schwingung"),
    "fr": ("essence", "vrai soi", "énergie", "l’univers", "sacré", "vibration"),
    "it": ("essenza", "vero sé", "energia", "l'universo", "sacro", "vibrazione"),
    "pt-BR": ("essência", "verdadeiro eu", "energia", "o universo", "sagrado", "vibração"),
}

#: Dashes allowed in one paragraph, per language. One is punctuation; the next
#: one is a tic — except where the language needs it.
#:
#: **Russian gets two, and that is linguistics rather than leniency.** Russian
#: has no present-tense copula: «Сатурн — планета границ» is how the language
#: says "Saturn is the planet of limits", and there is no way to write it
#: without the dash. A budget of one was set here first and the model could not
#: hold it — three live attempts in a row came back with two, three and four,
#: which is what fighting a grammar looks like from the outside. Two still cuts
#: the measured 2.78 a paragraph, and what the owner objected to was never the
#: copula: it was «ядро», «маска» and «гораздо более настоящее», which the word
#: list above refuses directly.
_DASH_BUDGET: dict[str, int] = {"ru": 2}
DASH_BUDGET = 1


def dash_budget(locale: str) -> int:
    return _DASH_BUDGET.get(locale, _DASH_BUDGET.get(locale.split("-")[0], DASH_BUDGET))

#: Mean words per sentence above which a paragraph is sent back.
#:
#: Eighteen, not the fourteen the voice asks for. The prompt sets the target and
#: this catches the failure — a gate at the target would reject writing that is
#: merely a little long, and every rejection is a real generation spent. The
#: measured mean before this landed was 16.2, so 18 is not a formality either.
SENTENCE_CEILING = 18.0

#: A single sentence longer than this is a paragraph pretending to be a
#: sentence, whatever the mean says.
LONGEST_SENTENCE = 45


def purple_words(text: str, locale: str) -> list[str]:
    """Which of the banned words this text contains, in the reader's language.

    Split out of `plain_language` so a **title** can be held to the word list
    without also being held to the dash budget and the sentence-length ceiling,
    neither of which means anything for a fragment of six words.

    That gap was not theoretical. `plain_language` is handed the paragraphs and
    nothing else, so the one line set largest on the page was never checked: the
    first free chapter of a Russian natal chart was published under «Ядро — что
    во мне настоящее, под всем остальным?» — the first word on the list, and
    the exact phrase the owner quoted as what he did not want. Read off a phone
    on 9 August 2026, four waves after the rule was written.
    """
    base = locale if locale in _PURPLE else locale.split("-")[0]
    lowered = _fold_apostrophes(text.lower())
    return [
        word for word in _PURPLE.get(base, ())
        if _fold_apostrophes(word) in lowered
    ]


def plain_language(text: str, locale: str) -> list[str]:
    """What is ornate, machine-made or unreadable in a piece of prose.

    Returns complaints in English — they go into the model's retry, not to a
    reader. Empty means the prose passed.

    Checked per paragraph rather than over the whole reading: the dash budget is
    a rule about a paragraph, and averaging it over a page would let one
    dash-riddled paragraph hide behind four clean ones.
    """
    complaints: list[str] = []
    base = locale if locale in _PURPLE else locale.split("-")[0]

    found = purple_words(text, locale)
    if found:
        complaints.append(
            "These words sound like meaning and carry none; rewrite without "
            "them: " + ", ".join(found[:6])
        )

    budget = dash_budget(base)
    for index, paragraph in enumerate(p for p in text.split("\n\n") if p.strip()):
        # The paragraph's own opening, quoted back. **A complaint that names an
        # index is a complaint the model cannot act on**: it rewrites the whole
        # chapter, puts the dashes somewhere else, and the second attempt fails
        # for the same reason as the first — watched live, twice, on the densest
        # natal chapter. Quoting it points at the sentence.
        opening = " ".join(paragraph.split()[:9])

        dashes = paragraph.count("—") + paragraph.count("–")
        if dashes > budget:
            allowed = "one" if budget == 1 else "two"
            complaints.append(
                f'The paragraph beginning "{opening}…" has {dashes} dashes. '
                f"{allowed.capitalize()} at most: where you reached for the next "
                "one, a full stop or a comma is what you meant. Change that "
                "paragraph and leave the others as they are."
            )

        sentences = [s for s in re.split(r"[.!?…]+", paragraph) if s.strip()]
        if not sentences:
            continue
        lengths = [len(s.split()) for s in sentences]
        mean = sum(lengths) / len(lengths)
        if mean > SENTENCE_CEILING:
            complaints.append(
                f'The paragraph beginning "{opening}…" averages {mean:.0f} words '
                "a sentence. Aim for about fourteen: a long sentence explains, a "
                "short one lands."
            )
        if max(lengths) > LONGEST_SENTENCE:
            complaints.append(
                f'The paragraph beginning "{opening}…" contains a sentence of '
                f"{max(lengths)} words. Break it."
            )

    return complaints


def russian_latin_leak(text: str, factors: tuple[str, ...] | list[str] = ()) -> list[str]:
    """Latin words stranded in Russian prose — «твой natal Уран», seen live.

    The factor identifiers are English and the model quotes them; most slips
    are a single untranslated word riding into the sentence. Only prose is
    checked — the `factors` arrays stay English by contract — and the one
    Latin word Russian prose is always allowed is the product's own name.

    **`factors` is the second allowance, and it is not a loophole.** A Cyrillic
    name is counted from a romanised spelling — «Анатолий Михайлов» as
    ANATOLIYMIKHAYLOV — and the chapter is *required* to name that spelling, or
    the reader cannot check the sum it produced. The engine puts it in the
    factor list; quoting a factor verbatim is the one thing this whole module
    exists to encourage. Caught the day the two rules met: the numerology name
    chapter was refused for citing the letters it was told to cite.

    **The allowance is the romanised name and nothing else.** It used to be
    every Latin word appearing anywhere in the factor list, and that emptied the
    gate on exactly the chapters it was written for: an astrological factor
    reads `transiting saturn ☌ natal midheaven · orb 5.49°`, so *transiting*,
    *saturn*, *natal*, *midheaven* and *orb* were all licensed, and a Russian
    chapter opening «транзитный Сатурн стоит на твоём Midheaven» passed
    without a complaint — seen on this machine on 13 August 2026, in the day
    text, which is the one paragraph every reader sees.

    The romanised name is distinguishable without a dictionary: `romanise`
    upper-cases it, so it arrives as ANATOLIY MIKHAYLOV while every engine term
    is lower-case. Matching only the upper-case runs keeps the numerology
    chapter able to cite the spelling its arithmetic used — the case that
    created this allowance — and lets go of the licence it accidentally granted
    to the whole English astronomical vocabulary.
    """
    import re
    allowed = {"alma"}
    for factor in factors:
        allowed.update(w.lower() for w in re.findall(r"\b[A-Z]{2,}\b", factor))
    roman = re.compile(r"^[IVXLCDM]+$")
    words = re.findall(r"[A-Za-z]{2,}", text)
    return sorted({
        w for w in words
        if w.lower() not in allowed and not roman.fullmatch(w)
    })
