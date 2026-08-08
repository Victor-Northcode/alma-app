"""Alma in German.

The 41 chapter titles and questions and the nine pairs of synthesis poles,
in German. Nothing else belongs in this file: the structure they hang on —
which factors a chapter reads from, its word budget, whether it needs a birth
time — lives in `alma/ai/chapters.py`, and the axis *names* are identifiers
that stay English everywhere. `alma/i18n/__init__.py` explains why.

What these strings are, so they are written as what they are.

A **title** is a noun phrase of two or three words: the name of a room in
somebody's chart. Not a heading, not a sentence.

A **question** is the reader's own, in their own voice, and it is the reason
they tap. "How do I attach, and what breaks it?" is a question somebody asks
themselves at two in the morning. It stays a question in German, and it
stays theirs.

A **pole** is a short clause describing a way of being, and the pair has to
read as two ends of one line — the reader sees both at once, under the axis
they disagree about.

Alma's voice is plain, exact, a little cool. Never breathy, never flattering,
never mystical for its own sake; concrete over cosmic. `src/lib/i18n/de.ts`
is the reference for how she already sounds in German — most of it was
written rather than translated, and this file should sound like it came from
the same person. A literal rendering of the English will read like a
translated app, which is the one thing this product is built not to be.

What `tests/test_locales.py` will not let through: a key added, removed or
renamed; a title or a question left blank; a question that does not end in a
question mark, or a title that does; a file left half-done with `WRITTEN`
still False; and, once `WRITTEN` is True, any string still identical to the
English and not listed in `SHARED`. Translate the values. Leave every key —
and the nine axis names, which are identifiers the model cites and the
validator checks — exactly as they are.

**German in particular.** *Du* throughout, for the reason `src/lib/i18n/de.ts`
gives: Alma knows the reader's birth minute, and *Sie* would put a desk
between them. Compounds where a German would use one — *Geburtstagszahl*,
*Persönlichkeitskarte*, *Weltbild*, *Lebensabschnitt* — and not where the
compound merely fits: *Meilensteine* is business jargon for what this chapter
actually holds, so `milestones` is *Wendepunkte*. Several lines are built
differently from the English rather than translated across it, because the
German that says the same thing is a different sentence; each of those is
noted where it stands.

Titles were kept short on purpose. German runs 20–30% longer than English and
these are the largest type on the chapter screen, next to a numeral, on a
phone — a three-word title here is already at the width a two-word English
one occupies.
"""

from __future__ import annotations

from .words import AxisWords, ChapterWords

#: True: every one of the 100 strings below is German.
#: `tests/test_locales.py` reads this, and from here on any string identical
#: to the English fails the suite unless it is listed in `SHARED`.
WRITTEN = True

#: Words that are correctly the same in German as in English. Listed one
#: at a time rather than waved through, exactly as `scripts/check-locales.mjs`
#: does for the web dictionaries, and only consulted once `WRITTEN` is True.
#:
#: Empty, and that is a finding rather than an omission: German spells the one
#: word that would have qualified with an umlaut and a hard t — *Porträt* —
#: so not one of the hundred survives the crossing unchanged.
SHARED: frozenset[str] = frozenset()

CHAPTERS: dict[str, dict[str, ChapterWords]] = {
    "natal": {
        "core": ChapterWords(
            title="Kern",
            question="Wie bin ich wirklich, unter der Oberfläche?",
        ),
        "portrait": ChapterWords(
            title="Porträt",
            question="Wie wirke ich, bevor ich etwas sage?",
        ),
        "love": ChapterWords(
            title="Liebe und Nähe",
            # "attach" is the clinical word in English and it stays clinical
            # here: *sich binden* is what a German says about themselves, and
            # *zerbrechen* is what breaks in a German sentence about closeness.
            question="Wie binde ich mich und woran zerbricht das?",
        ),
        "money": ChapterWords(
            # *Mittel* alone only reads as money inside *finanzielle Mittel*;
            # on its own it is a remedy or a means. And the clients print
            # *Mittel* as the name of the Resources axis, so the same word
            # would name two different rooms. *Besitz* is the German for what
            # this house holds.
            title="Geld und Besitz",
            question="Wie kommt Geld eigentlich zu mir?",
        ),
        "career": ChapterWords(
            # *Beruf und Berufung* is a real German pair, not a rendering of
            # one — the same two words with the same one letter between them.
            title="Beruf und Berufung",
            # *aufreiben* rather than *auszehren* or *ausbrennen*: it is what
            # actually happens to somebody in the wrong job, and it is a word
            # they would use about themselves.
            question="Welche Arbeit reibt mich nicht auf?",
        ),
        "mind": ChapterWords(
            title="Denken und Sprechen",
            question="Wie denke ich und wie klinge ich dabei?",
        ),
        "shadow": ChapterWords(
            title="Schatten und Wunde",
            # *inszenieren* keeps the theatre in "re-staging" — the reader is
            # both the one who puts the scene on and the one it happens to.
            question="Was wiederhole ich immer wieder?",
        ),
        "roots": ChapterWords(
            # *Wurzeln* is available and is what a translation would reach
            # for; *Herkunft* is what a German means by it — where you come
            # from, family included, no metaphor needed.
            title="Herkunft und Familie",
            # A perfect main verb with a present infinitive after it — *habe
            # geerbt, ohne zuzustimmen* — puts the consent in a different time
            # from the inheritance and has to be read twice. German keeps both
            # in the past, and this is the construction it uses for it.
            question="Was habe ich geerbt, ohne dass mich jemand gefragt hätte?",
        ),
        "karmic-axis": ChapterWords(
            title="Karmische Achse",
            # The impersonal *es* carries exactly the English passive's
            # ambiguity about who is doing the moving, and does it in three
            # words instead of a construction nobody says out loud. The verb
            # has to be *treiben*: German *schieben* wants a hand and a cart,
            # and "es schiebt mich" is not a sentence anybody says, where "es
            # treibt mich" is — the same agentless force, already in the
            # language.
            question="Wohin treibt es mich?",
        ),
        "work-rhythms": ChapterWords(
            title="Arbeit und Rhythmus",
            question="Welches Tempo halte ich durch?",
        ),
        "transformation": ChapterWords(
            title="Krisen und Wandlung",
            question="Wie falle ich auseinander und wie baue ich mich wieder auf?",
        ),
        "freedom": ChapterWords(
            title="Freiheit und Eigenart",
            question="Wo weigere ich mich, wie alle anderen zu sein?",
        ),
        "dreams": ChapterWords(
            title="Träume und Grenzen",
            # German has the idiom the English is reaching for: *die Konturen
            # verlieren* is precisely losing your edges, and it is ordinary
            # speech rather than an image built for the occasion.
            question="Wo verliere ich meine Konturen?",
        ),
        "circle": ChapterWords(
            # *Kreis* on its own is a shape in German. *Umfeld* is the word
            # for the people around somebody.
            title="Umfeld und Verbündete",
            # "built to be around" has no German construction; asking which
            # people you are *right* among gets to the same place, and gets
            # there in the reader's own voice.
            question="Unter welchen Menschen bin ich eigentlich richtig?",
        ),
        "worldview": ChapterWords(
            title="Weltbild und Wachstum",
            question="Woran glaube ich, wenn niemand zuschaut?",
        ),
        "milestones": ChapterWords(
            # *Meilensteine* is what a project plan has. What this chapter
            # holds is the ages at which a life turns. Not *nach Alter*
            # either: that is a sort order, the phrase on a column header, and
            # a title is supposed to name a room rather than a view setting —
            # the question underneath already says the ages are the point.
            title="Wendepunkte im Leben",
            question="Wann ändert sich die Form meines Lebens?",
        ),
    },
    "numerology": {
        "life-path": ChapterWords(
            # *Lebensweg*, the word `de.ts` already uses in the ceremony line
            # ("Dein Lebensweg wird zu einer Zahl").
            title="Lebensweg",
            # The English packs purpose and duration into one verb ("built to
            # *spend my life* on") and German cannot follow it; *ein Leben
            # lang* tacked on after the comma is the English shape showing
            # through. The duration is already in the title, so the question
            # only has to carry the purpose — in the product's own German,
            # which is *woraus du gemacht bist* rather than anything about
            # fate.
            question="Wofür bin ich eigentlich gebaut?",
        ),
        "birthday-number": ChapterWords(
            title="Geburtstagszahl",
            # "discount" is a whole sentence in German. This is that sentence:
            # it comes easily, *and therefore* it does not count — which is
            # the reader's own faulty arithmetic, stated in their voice.
            question="Was fällt mir leicht und zählt deshalb nicht?",
        ),
        "personal-year": ChapterWords(
            title="Persönliches Jahr",
            # English "season" is a metaphor; German *Jahreszeit* is not — it
            # means spring, summer, autumn, winter and nothing else, so the
            # reader was being asked something they could answer by looking
            # out of the window. *Zeit* carries the stretch of time the
            # chapter is actually about, and it is the same word the Rhythms
            # poles use, which makes the two places one thread the way
            # "season" does in English.
            question="In was für einer Zeit bin ich gerade?",
        ),
        "pinnacles": ChapterWords(
            # *Gipfel* rather than *Höhepunkte*: a pinnacle is a summit, and
            # *Höhepunkt* carries a colloquial sexual reading that sits oddly
            # against *Prüfungen*.
            title="Gipfel und Prüfungen",
            question="Was wird gerade von mir verlangt?",
        ),
        "name": ChapterWords(
            title="Namenszahlen",
            # *auf einen Namen hören* is the German for answering to one, and
            # it keeps the small distance the English has between the person
            # and the name they were given.
            question="Was trägt der Name, auf den ich höre?",
        ),
    },
    "birth-card": {
        "personality": ChapterWords(
            title="Persönlichkeitskarte",
            question="Wie lesen mich andere?",
        ),
        "soul": ChapterWords(
            title="Seelenkarte",
            question="Was läuft darunter?",
        ),
        "year-card": ChapterWords(
            title="Jahreskarte",
            # *ausgerechnet* is how German says "this particular" without
            # saying it, and it carries the reader's slight resentment at
            # the year they happen to be in.
            question="Wofür ist ausgerechnet dieses Jahr da?",
        ),
    },
    "transits": {
        "active": ChapterWords(
            title="Was gerade läuft",
            question="Was passiert gerade wirklich mit mir?",
        ),
        "ahead": ChapterWords(
            title="Die nächsten Monate",
            question="Was kommt und wann?",
        ),
        "long": ChapterWords(
            title="Die langen Transite",
            question="Worum geht es in diesem ganzen Lebensabschnitt?",
        ),
    },
    "solar-return": {
        "year-shape": ChapterWords(
            title="Die Form des Jahres",
            question="Wofür ist dieses Jahr da?",
        ),
        "emphasis": ChapterWords(
            title="Wo das Jahr landet",
            question="Welchen Teil meines Lebens trifft es?",
        ),
        "contacts": ChapterWords(
            title="Wo es dein Horoskop berührt",
            # *was ich schon bin* rather than a relative pronoun: German would
            # force *der* or *die* here and pick a gender for every reader.
            question="Wie knüpft es an das an, was ich schon bin?",
        ),
    },
    "compatibility": {
        "attraction": ChapterWords(
            # German needs the prefix: *ziehen* is what a horse does to a
            # cart, *anziehen* is what one person does to another.
            title="Was anzieht",
            question="Warum diese Person und keine andere?",
        ),
        "friction": ChapterWords(
            # *wo es hakt* is the idiom itself, not a rendering of one.
            title="Wo es hakt",
            question="Worüber werden wir immer wieder streiten?",
        ),
        "overlays": ChapterWords(
            # Not *ineinander landen*: with two people German hears the bed
            # idiom (*wir sind im Bett gelandet*), so a chapter about one
            # person's planets falling into the other's houses announced
            # itself as a sex chapter — in the largest type on the screen,
            # over a question about territory. *Überlagerung* is the German
            # term for a chart overlay and is exactly as unglamorous as this
            # product wants to be.
            title="Wo wir uns überlagern",
            # *besetzen* is cool and slightly territorial, which is what the
            # chapter is about: a person occupying a room of your life.
            question="Welchen Teil meines Lebens besetzt diese Person?",
        ),
        "together": ChapterWords(
            title="Ihr beide als ein Ganzes",
            question="Wie ist die Beziehung selbst?",
        ),
    },
    "astrocartography": {
        "lines": ChapterWords(
            title="Deine Linien",
            question="Welche Orte verstärken welchen Teil von mir?",
        ),
        "here": ChapterWords(
            title="Wo du gerade bist",
            # *was macht X mit mir* is the ordinary German for it, and it is
            # already the shape of a question somebody asks themselves.
            question="Was macht der Ort, an dem ich lebe, mit mir?",
        ),
        "crossings": ChapterWords(
            title="Kreuzungen",
            question="Wo passieren zwei Dinge auf einmal?",
        ),
    },
    "synthesis": {
        "agreement": ChapterWords(
            # `de.ts` already says it this way on the landing page: "Wo drei
            # Systeme sich über dich einig sind".
            title="Wo die Systeme sich einig sind",
            # *stimmen* is the right verb — `de.ts` ends its own example with
            # "Beides stimmt" — but German does not hang a direction on it,
            # and *aus mehr als einer Richtung* floats with nothing to arrive
            # at. *sich bestätigen* takes it naturally and keeps the chapter's
            # actual claim, which is that something was confirmed rather than
            # merely said. *Seite* rather than *Richtung* because the clients
            # print *Richtung* as the name of the Direction axis.
            question="Was bestätigt sich von mehr als einer Seite?",
        ),
        "disagreement": ChapterWords(
            title="Wo sie sich widersprechen",
            question="In welchem Widerspruch lebe ich eigentlich?",
        ),
        "single": ChapterWords(
            title="Was nur ein System sieht",
            question="Was würde ich übersehen, wenn ich nur eins davon lese?",
        ),
        "whole": ChapterWords(
            title="Alles zusammen",
            # "add up to" is arithmetic in English and *hinauslaufen auf* is
            # the German for the same move — where does the sum end up. A
            # literal *was ergibt das zusammen* would only repeat the title.
            question="Worauf läuft das alles hinaus?",
        ),
    },
}

#: The nine keys are identifiers and stay English — the clients hold the
#: German names (*Richtung*, *Charakter*, *Schwachstelle*, …) and the model
#: cites the English ones. Only the two clauses under each are copy.
#:
#: The reader sees both poles at once, one above the other, under a line that
#: says how many systems disagree. So each pair is written as a pair: the two
#: clauses take the same grammatical shape, and where German could not carry
#: the English shape the shape was changed on both ends rather than on one.
AXES: dict[str, AxisWords] = {
    # *im Verborgenen* and not *ungesehen*: the positive end is completely
    # ordinary German and a rare, faintly literary word at the negative end
    # makes the two stop reading as one line. It also keeps *sehen* out of an
    # axis that is not about being seen — the Weak point pair below is.
    "Direction": AxisWords(
        negative="arbeitet allein, im Verborgenen",
        positive="arbeitet öffentlich, vor Leuten",
    ),
    # hält/wechselt against die Position/die Form: one verb apart, which is
    # what makes the two read as one line rather than two statements.
    "Character": AxisWords(
        negative="hält die Position",
        positive="wechselt die Form",
    ),
    "Mind": AxisWords(
        negative="will erst Beweise",
        positive="traut dem ersten Eindruck",
    ),
    # Already written, on the landing page: "Dein Horoskop will einen Zeugen;
    # deine Geburtskarte will eine offene Tür." Same axis, same two clauses.
    "Relationships": AxisWords(
        negative="will eine offene Tür",
        positive="will einen Zeugen",
    ),
    # English can say "builds their own" with no object; German cannot, so
    # both ends take a pronoun for the resources the axis is named for — and
    # it has to be *sie*. The name the clients print above these two lines is
    # *Mittel* (`src/lib/i18n/de.ts`), which is plural, so *es* had no
    # antecedent anywhere on the screen and the one ungrammatical line in the
    # synthesis view was this one.
    "Resources": AxisWords(
        negative="baut sie selbst auf",
        positive="bekommt sie über andere",
    ),
    # *Kraftakt* is the German for one large push, in one word.
    "Work": AxisWords(
        negative="ein großer Kraftakt",
        positive="eine kleine, wiederholbare Übung",
    ),
    "Weak point": AxisWords(
        negative="fürchtet, übersehen zu werden",
        positive="fürchtet, gesehen zu werden",
    ),
    # "asked to" has no short German passive that stays this plain. *soll*
    # says the same thing — something is being required — and lets the pair
    # turn on one reflexive verb each: sich zurückziehen, sich zeigen.
    "Growth": AxisWords(
        negative="soll sich zurückziehen",
        positive="soll sich zeigen",
    ),
    # German has no participle pair for closing/opening a season, so the
    # relative clause carries it on both ends.
    "Rhythms": AxisWords(
        negative="eine Zeit, die sich schließt",
        positive="eine Zeit, die sich öffnet",
    ),
}
