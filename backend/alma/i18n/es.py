"""Alma in Spanish.

The 41 chapter titles and questions and the nine pairs of synthesis poles,
in Spanish. Nothing else belongs in this file: the structure they hang on —
which factors a chapter reads from, its word budget, whether it needs a birth
time — lives in `alma/ai/chapters.py`, and the axis *names* are identifiers
that stay English everywhere. `alma/i18n/__init__.py` explains why.

What these strings are, so they are written as what they are.

A **title** is a noun phrase of two or three words: the name of a room in
somebody's chart. Not a heading, not a sentence.

A **question** is the reader's own, in their own voice, and it is the reason
they tap. "How do I attach, and what breaks it?" is a question somebody asks
themselves at two in the morning. It stays a question in Spanish, and it
stays theirs.

A **pole** is a short clause describing a way of being, and the pair has to
read as two ends of one line — the reader sees both at once, under the axis
they disagree about.

Alma's voice is plain, exact, a little cool. Never breathy, never flattering,
never mystical for its own sake; concrete over cosmic. `src/lib/i18n/es.ts`
is the reference for how she already sounds in Spanish — most of it was
written rather than translated, and this file should sound like it came from
the same person. A literal rendering of the English will read like a
translated app, which is the one thing this product is built not to be.

**Three rules this file follows that the English did not have to think about.**

*Nothing here picks the reader's gender.* Spanish makes you choose:
"¿Con quién estoy hecho para estar?" tells half of Alma's readers she assumed
they were men. So every question is built out of verbs rather than participles
— "¿Con quién funciono de verdad?" — and the poles are third person and lean
on nouns, "teme quedar fuera de la vista", where a clitic would not have been
neutral either: "teme que lo vean" is masculine, and it took a reviewer to
notice that the line this docstring once held up as the genderless example was
the one exception in the file. The rule is the wider one — no participle, no
adjective and no pronoun in these 100 strings agrees with the person reading
them. It constrained the wording more than the translation did.

*A title that begins with "where" takes no accent; a question does.* "Donde
coinciden los sistemas" is a place, and it is the same construction
`src/lib/i18n/es.ts` already uses in its own section titles. "¿Dónde pasan dos
cosas a la vez?" is somebody asking. The accent is the difference between the
name of a room and a person talking, which is exactly the distinction between
these two fields, so it is worth being consistent about.

*"Temporada" is one thread, deliberately.* The Rhythms poles and the personal
year chapter are the same idea in two places — a stretch of time that opens
and closes — and a reader who meets "una temporada que se abre" under an axis
should recognise the word when the numerology chapter asks which one they are
in. English gets this free from "season"; Spanish has to choose it.

What `tests/test_locales.py` will not let through: a key added, removed or
renamed; a title or a question left blank; a question that does not end in a
question mark, or a title that does; a file left half-done with `WRITTEN`
still False; and, once `WRITTEN` is True, any string still identical to the
English and not listed in `SHARED`. Translate the values. Leave every key —
and the nine axis names, which are identifiers the model cites and the
validator checks — exactly as they are.
"""

from __future__ import annotations

from .words import AxisWords, ChapterWords

#: Every one of the 100 strings below is Spanish. From here on, any string
#: that matches the English character for character fails the suite unless it
#: is listed in `SHARED`.
WRITTEN = True

#: Words that are correctly the same in Spanish as in English. Listed one
#: at a time rather than waved through, exactly as `scripts/check-locales.mjs`
#: does for the web dictionaries, and only consulted once `WRITTEN` is True.
#:
#: Empty, and not for lack of looking. Spanish has its own word for every one
#: of these — even "Portrait", which German and French keep, is "Retrato"
#: here. A borrowing that survives in Spanish ("Karma", say) would go in this
#: set; nothing in this particular 100 qualifies.
SHARED: frozenset[str] = frozenset()

CHAPTERS: dict[str, dict[str, ChapterWords]] = {
    "natal": {
        "core": ChapterWords(
            title="Núcleo",
            question="¿Cómo soy de verdad, por debajo de todo?",
        ),
        "portrait": ChapterWords(
            title="Retrato",
            # "How do I come across" is a stock English phrase with no stock
            # Spanish equivalent; the literal "¿Cómo me presento?" is a job
            # interview. What a person actually asks is what other people see,
            # and "antes de que abra la boca" is how they say "before I speak".
            question="¿Cómo me ven antes de que abra la boca?",
        ),
        "love": ChapterWords(
            title="Amor y cercanía",
            question="¿Cómo me apego y qué lo rompe?",
        ),
        "money": ChapterWords(
            title="Dinero y recursos",
            question="¿Cómo me llega el dinero de verdad?",
        ),
        "career": ChapterWords(
            title="Carrera y vocación",
            question="¿Qué trabajo no me va a desgastar?",
        ),
        "mind": ChapterWords(
            title="Mente y palabra",
            # "How do I sound?" has no Spanish verb that survives on its own —
            # "cómo sueno" is what an instrument does, and "cuando hablo" only
            # made the borrowed half longer. What the English pair actually
            # is, is two beats of the same length: thinking, then saying. That
            # is what this keeps, and "lo digo" is the title's own *palabra*.
            question="¿Cómo pienso y cómo lo digo?",
        ),
        "shadow": ChapterWords(
            title="Sombra y herida",
            # "Re-staging" is theatre, and the theatre survives in "escena".
            # Not "montar una escena", which in Spanish is a tantrum.
            question="¿Qué escena repito una y otra vez?",
        ),
        "roots": ChapterWords(
            title="Raíces y familia",
            question="¿Qué heredé sin que nadie me preguntara?",
        ),
        "karmic-axis": ChapterWords(
            title="Eje kármico",
            # The third person plural carries the English agentless passive,
            # but the verb has to be "llevar": in Spanish you *mueves* a piece
            # of furniture, or you move somebody emotionally. Being carried in
            # a direction you did not pick is "llevar", which is also the verb
            # the Brazilian file reached for unprompted.
            question="¿Hacia dónde me están llevando?",
        ),
        "work-rhythms": ChapterWords(
            title="Trabajo y ritmos",
            question="¿Qué ritmo puedo sostener?",
        ),
        "transformation": ChapterWords(
            title="Crisis y transformación",
            question="¿Cómo me rompo y cómo me reconstruyo?",
        ),
        "freedom": ChapterWords(
            title="Libertad y diferencia",
            question="¿Dónde me niego a parecerme a nadie?",
        ),
        "dreams": ChapterWords(
            title="Sueños y límites",
            question="¿Dónde se me borran los contornos?",
        ),
        "circle": ChapterWords(
            title="Círculo y aliados",
            question="¿Con quién funciono de verdad?",
        ),
        "worldview": ChapterWords(
            title="Creencias y crecimiento",
            question="¿Qué creo de verdad cuando nadie mira?",
        ),
        "milestones": ChapterWords(
            # "Hitos" is a project plan. The chapter is about the ages at which
            # a life changes shape, and that is what a person calls them.
            title="Las edades clave",
            question="¿Cuándo cambia la forma de mi vida?",
        ),
    },
    "numerology": {
        "life-path": ChapterWords(
            # "Camino de vida", the term `src/lib/i18n/es.ts` already prints
            # under the reader's date on the landing page.
            title="Camino de vida",
            # "What was I built to spend my life on" cannot be said in Spanish
            # without a gendered participle ("hecho"), so the question is
            # rebuilt on a verb. Not on "se me va la vida en…", which is a real
            # phrase about the wrong thing: it means something is consuming me
            # ("se me va la vida en el trabajo"), so the chapter that should
            # name what a life is worth spending read as what is draining it.
            # "Debería" keeps it a question somebody asks themselves rather
            # than a destiny anybody is assigning them.
            question="¿A qué debería dedicar la vida?",
        ),
        "birthday-number": ChapterWords(
            # "Número del día" is read against "Año personal" two rows down as
            # today's number rather than the day somebody was born on.
            title="Número de nacimiento",
            question="¿Qué se me da fácil y no valoro?",
        ),
        "personal-year": ChapterWords(
            title="Año personal",
            question="¿En qué temporada estoy en realidad?",
        ),
        "pinnacles": ChapterWords(
            title="Pináculos y desafíos",
            question="¿Qué se me está pidiendo ahora mismo?",
        ),
        "name": ChapterWords(
            title="Números del nombre",
            question="¿Qué lleva dentro el nombre al que respondo?",
        ),
    },
    "birth-card": {
        "personality": ChapterWords(
            title="Carta de personalidad",
            question="¿Cómo me leen los demás?",
        ),
        "soul": ChapterWords(
            title="Carta del alma",
            question="¿Qué corre por debajo de eso?",
        ),
        "year-card": ChapterWords(
            title="Carta del año",
            # "En concreto" is Peninsular, in a file that is neutral Latin
            # American throughout. "Justamente este año" says the same slight
            # resentment at the year you happen to be in, in both hemispheres.
            question="¿Para qué sirve justamente este año?",
        ),
    },
    "transits": {
        "active": ChapterWords(
            title="Lo que está activo ahora",
            question="¿Qué me está pasando, en realidad?",
        ),
        "ahead": ChapterWords(
            title="Los meses que vienen",
            question="¿Qué viene y cuándo?",
        ),
        "long": ChapterWords(
            title="Los tránsitos largos",
            # Two things the English gets away with and Spanish does not.
            # "Capítulo" is the product's own word — es.ts prints "Los 16
            # capítulos" — so a reader holding a chapter was being asked about
            # a chapter, and the word pointed at the screen instead of at
            # their life; "etapa" is the ordinary Spanish for a stretch of
            # one. And "¿de qué va…?" is Peninsular, which "de qué se trata"
            # is not.
            question="¿De qué se trata toda esta etapa de mi vida?",
        ),
    },
    "solar-return": {
        "year-shape": ChapterWords(
            title="La forma del año",
            question="¿Para qué es este año?",
        ),
        "emphasis": ChapterWords(
            title="Donde cae el año",
            question="¿Qué parte de mi vida toca?",
        ),
        "contacts": ChapterWords(
            title="Donde se cruza con tu carta",
            question="¿Cómo conecta con quien ya soy?",
        ),
    },
    "compatibility": {
        "attraction": ChapterWords(
            title="Lo que atrae",
            question="¿Por qué esta persona y no otra?",
        ),
        "friction": ChapterWords(
            # "Where it catches" is cloth on a nail. "Donde roza" is the same
            # gesture in Spanish and the same two words.
            title="Donde roza",
            question="¿De qué vamos a discutir una y otra vez?",
        ),
        "overlays": ChapterWords(
            title="Donde cae cada uno en el otro",
            question="¿Qué parte de mi vida ocupa esta persona?",
        ),
        "together": ChapterWords(
            # "Los dos" rather than anything with "vosotros" or "ustedes":
            # neutral in both hemispheres, and it is what the pair would call
            # themselves.
            title="Los dos como una sola cosa",
            question="¿Cómo es la relación en sí?",
        ),
    },
    "astrocartography": {
        "lines": ChapterWords(
            title="Tus líneas",
            # "Amplificar" belongs to a mixing desk. A place lights a part of
            # somebody up, and "encenderse" is that in Spanish — which also
            # loses the doubled "qué… qué", heavier here than in English.
            question="¿Qué parte de mí se enciende en cada lugar?",
        ),
        "here": ChapterWords(
            title="Donde estás ahora",
            question="¿Qué me está haciendo el lugar donde vivo?",
        ),
        "crossings": ChapterWords(
            title="Cruces",
            question="¿Dónde pasan dos cosas a la vez?",
        ),
    },
    "synthesis": {
        "agreement": ChapterWords(
            # "Coincidir" is the verb the landing page already uses for this
            # ("Donde tres sistemas coinciden sobre ti"), and "discrepar" for
            # its opposite. Both are kept here so the app and the site are
            # describing the same thing in the same words.
            title="Donde coinciden los sistemas",
            question="¿Qué es verdad desde más de un lado?",
        ),
        "disagreement": ChapterWords(
            title="Donde discrepan",
            question="¿En qué contradicción vivo de verdad?",
        ),
        "single": ChapterWords(
            title="Lo que solo ve un sistema",
            question="¿Qué se me escaparía si leyera solo uno?",
        ),
        "whole": ChapterWords(
            title="Todo junto",
            question="Entonces, ¿qué sale de todo esto?",
        ),
    },
}

# The nine pairs. Each pole is a clause about a person, in the third person and
# in lower case, because the client prints them as "negativo ↔ positivo" under
# the axis name: they are two ends of one line and neither is a sentence.
AXES: dict[str, AxisWords] = {
    # Manner, then place, at both ends. The subordinate clause this used to
    # have ("sin que se le vea") was three words doing the work of two and put
    # a different grammar on each end of a pair the reader sees one above the
    # other.
    "Direction": AxisWords(
        negative="trabaja a solas, puertas adentro",
        positive="trabaja en público, delante de la gente",
    ),
    "Character": AxisWords(
        negative="mantiene su posición",
        positive="cambia de forma",
    ),
    "Mind": AxisWords(
        negative="quiere pruebas primero",
        positive="confía en la primera impresión",
    ),
    "Relationships": AxisWords(
        # Word for word the pair `src/lib/i18n/es.ts` already uses to explain
        # what a disagreement looks like: "tu carta quiere un testigo; tu Carta
        # de nacimiento quiere una puerta abierta".
        negative="quiere una puerta abierta",
        positive="quiere un testigo",
    ),
    "Resources": AxisWords(
        # The English pair changes subject halfway — the person builds, the
        # resources arrive — and Spanish keeps that rather than flattening it,
        # because the asymmetry is the point: one pole is something you do and
        # the other is something that happens to you.
        negative="los construye por su cuenta",
        positive="le llegan a través de otros",
    ),
    "Work": AxisWords(
        negative="un solo empujón grande",
        positive="una rutina pequeña que se repite",
    ),
    "Weak point": AxisWords(
        # The minimal pair survives — one preposition apart rather than one
        # negation — and it is built on "la vista" rather than on a clitic.
        # "Teme que lo vean" was the one place this file broke its own rule:
        # "lo" is the masculine object pronoun, so the pair that the docstring
        # offers as the example of a genderless construction was telling half
        # the readers it had assumed they were men. A noun agrees with nobody.
        negative="teme quedar fuera de la vista",
        positive="teme quedar a la vista",
    ),
    "Growth": AxisWords(
        negative="se le pide retirarse",
        positive="se le pide dejarse ver",
    ),
    "Rhythms": AxisWords(
        negative="una temporada que se cierra",
        positive="una temporada que se abre",
    ),
}
