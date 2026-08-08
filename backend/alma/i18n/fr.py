"""Alma in French.

The 41 chapter titles and questions and the nine pairs of synthesis poles,
in French. Nothing else belongs in this file: the structure they hang on —
which factors a chapter reads from, its word budget, whether it needs a birth
time — lives in `alma/ai/chapters.py`, and the axis *names* are identifiers
that stay English everywhere. `alma/i18n/__init__.py` explains why.

What these strings are, so they are written as what they are.

A **title** is a noun phrase of two or three words: the name of a room in
somebody's chart. Not a heading, not a sentence.

A **question** is the reader's own, in their own voice, and it is the reason
they tap. "How do I attach, and what breaks it?" is a question somebody asks
themselves at two in the morning. It stays a question in French, and it
stays theirs.

A **pole** is a short clause describing a way of being, and the pair has to
read as two ends of one line — the reader sees both at once, under the axis
they disagree about.

Alma's voice is plain, exact, a little cool. Never breathy, never flattering,
never mystical for its own sake; concrete over cosmic. `src/lib/i18n/fr.ts`
is the reference for how she already sounds in French — most of it was
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

Three decisions taken across the whole file, so they are not re-argued at
each line.

**Tu, not vous.** The shipped French product uses tu — `src/lib/i18n/fr.ts`
says why, and it is the right call for something that holds your birth minute.
It surfaces in four titles here ("Tes lignes", "Là où tu es maintenant", "Là
où elle rencontre ton thème", "Vous deux comme une seule chose", where *vous*
is the plural of two people and not the formal singular). The questions are
the reader talking to themselves, so they are first person throughout and the
address never comes up.

**A plain space before « ? ».** French typography wants a narrow no-break
space there and `src/lib/i18n/fr.ts` uses an ordinary one anyway, in all
thirteen of its questions. These strings are matched against that file by eye
and rendered by three clients that do nothing clever with whitespace, so they
follow it rather than introducing a second convention in the same product.

**The masculine as the unmarked form.** "travaille seul", "craint de ne pas
être vu". French has no neutral participle and the shipped copy already made
this choice — "Où es-tu né ?" is on the capture screen of every page. Doing
something else here would make the poles the only place in the product that
tries.
"""

from __future__ import annotations

from .words import AxisWords, ChapterWords

#: False while the strings below are still the English, waiting to be
#: replaced. Flip it to True when every one of them is French —
#: `tests/test_locales.py` reads this, and from that moment on any string
#: still identical to the English fails the suite.
WRITTEN = True

#: Words that are correctly the same in French as in English. Listed one
#: at a time rather than waved through, exactly as `scripts/check-locales.mjs`
#: does for the web dictionaries, and only consulted once `WRITTEN` is True.
#:
#: "Portrait" is the French word. It is also, in French, the *right* word for
#: this chapter in a way the English only borrows: a portrait is what somebody
#: looks like to a painter who has not spoken to them, which is exactly what
#: the ascendant chapter is about. Translating it away — "Apparence", "Image"
#: — would be inventing a difference to prove the file was worked on.
SHARED: frozenset[str] = frozenset({"Portrait"})

CHAPTERS: dict[str, dict[str, ChapterWords]] = {
    "natal": {
        "core": ChapterWords(
            title="Noyau",
            # `src/lib/i18n/fr.ts` already sends the reader's core somewhere:
            # "Là où trois traditions s'accordent, ça part dans ton noyau."
            # The chapter it lands in should be called the same thing.
            question="Je suis comment, vraiment, sous tout ça ?",
        ),
        "portrait": ChapterWords(
            title="Portrait",
            # "Avant d'ouvrir la bouche" would be the funnier line and the
            # wrong one — this chapter is the ascendant, which is working on
            # people who will never hear you speak at all.
            question="De quoi j'ai l'air avant même de parler ?",
        ),
        "love": ChapterWords(
            title="Amour et proximité",
            question="Comment je m'attache et qu'est-ce qui casse ça ?",
        ),
        "money": ChapterWords(
            title="Argent et ressources",
            # "Par où" rather than "comment": the English "reach me" is about
            # the route money takes, not the technique for getting it, and the
            # chapter reads the second and eighth houses — where it comes from.
            question="Par où l'argent m'arrive vraiment ?",
        ),
        "career": ChapterWords(
            title="Métier et vocation",
            # "User" and not "épuiser". Being worn out is a Tuesday; being
            # worn *down*, slowly, by work that fits badly, is the thing
            # somebody opens this chapter about.
            question="Quel travail ne va pas m'user ?",
        ),
        "mind": ChapterWords(
            title="Esprit et parole",
            # "How do I sound" has no French verb. "Comment ça s'entend" keeps
            # what the English means — the way the thinking comes out audible
            # to somebody else — without the anglicism of "comment je sonne".
            question="Comment je pense et comment ça s'entend ?",
        ),
        "shadow": ChapterWords(
            title="Ombre et blessure",
            # "Rejouer" is the theatre word in French too, which is the whole
            # point of "re-staging": the same scene, the same parts, a new cast.
            question="Qu'est-ce que je rejoue sans arrêt ?",
        ),
        "roots": ChapterWords(
            title="Racines et famille",
            question="De quoi j'ai hérité sans jamais avoir dit oui ?",
        ),
        "karmic-axis": ChapterWords(
            title="Axe karmique",
            # The English is a passive with no agent — deliberately, because
            # naming the agent would be the mystical claim Alma does not make.
            # French keeps that with an impersonal "ça"; "je suis poussé vers"
            # would have been the translation and the wrong register.
            question="Vers quoi ça me pousse ?",
        ),
        "work-rhythms": ChapterWords(
            title="Travail et rythmes",
            question="Quel rythme je peux tenir ?",
        ),
        "transformation": ChapterWords(
            title="Crises et transformation",
            question="Comment je m'effondre et comment je me reconstruis ?",
        ),
        "freedom": ChapterWords(
            title="Liberté et singularité",
            question="Où je refuse de ressembler à quiconque ?",
        ),
        "dreams": ChapterWords(
            title="Rêves et limites",
            # "Contours" is what French loses rather than "edges" — the outline
            # that says where you stop and somebody else starts. Neptune, the
            # twelfth house, and the person who cannot tell whose mood this is.
            question="Où je perds mes contours ?",
        ),
        "circle": ChapterWords(
            title="Cercle et alliés",
            question="Je suis fait pour être entouré de qui, vraiment ?",
        ),
        "worldview": ChapterWords(
            title="Croyances et croissance",
            # "Vision du monde et croissance" is the faithful title and five
            # words long, which is a headline and not the name of a room.
            # "Croyances" is what the chapter's own question asks about.
            question="Qu'est-ce que je crois quand personne ne regarde ?",
        ),
        "milestones": ChapterWords(
            title="Étapes par âge",
            question="Quand est-ce que ma vie change de forme ?",
        ),
    },
    "numerology": {
        "life-path": ChapterWords(
            # The term the shipped French already uses, on the landing page:
            # `insight.lifePath` reads "Chemin de vie 7". A reader who saw it
            # there meets the same words at the top of the chapter.
            title="Chemin de vie",
            question="À quoi je suis fait pour passer ma vie ?",
        ),
        "birthday-number": ChapterWords(
            title="Nombre du jour",
            # "Discount" is an accounting word doing emotional work, and French
            # has no single verb for it. "Compter pour rien" is what a person
            # actually says about the thing they are good at and dismiss.
            question="Qu'est-ce qui me vient tout seul et que je compte pour rien ?",
        ),
        "personal-year": ChapterWords(
            title="Année personnelle",
            question="Je suis dans quelle saison, vraiment ?",
        ),
        "pinnacles": ChapterWords(
            title="Sommets et défis",
            question="Qu'est-ce qu'on me demande en ce moment ?",
        ),
        "name": ChapterWords(
            title="Nombres du nom",
            question="Qu'est-ce que porte le nom auquel je réponds ?",
        ),
    },
    "birth-card": {
        "personality": ChapterWords(
            title="Carte de personnalité",
            question="Comment les autres me lisent ?",
        ),
        "soul": ChapterWords(
            title="Carte de l'âme",
            # The English opens on "that" — it is the second chapter and it is
            # leaning on the first. French keeps the lean with the "et", which
            # is what makes this a question and not a section heading.
            question="Et qu'est-ce qui court en dessous ?",
        ),
        "year-card": ChapterWords(
            title="Carte de l'année",
            # "Précise" carries the English "particular", which is there to
            # separate this from the solar return's "À quoi sert cette année ?"
            # — two systems answering the same question, on purpose.
            question="Elle sert à quoi, cette année précise ?",
        ),
    },
    "transits": {
        "active": ChapterWords(
            title="Ce qui est actif maintenant",
            question="Qu'est-ce qui est en train de m'arriver, vraiment ?",
        ),
        "ahead": ChapterWords(
            title="Les mois qui viennent",
            question="Qu'est-ce qui arrive et quand ?",
        ),
        "long": ChapterWords(
            title="Les longs transits",
            question="De quoi parle tout ce chapitre de ma vie ?",
        ),
    },
    "solar-return": {
        "year-shape": ChapterWords(
            title="La forme de l'année",
            question="À quoi sert cette année ?",
        ),
        "emphasis": ChapterWords(
            # "Là où", not "Où". French wants the demonstrative to turn a
            # clause into a name, and the shipped copy already does it:
            # "Là où trois systèmes s'accordent sur toi".
            title="Là où l'année atterrit",
            question="Elle touche quelle partie de ma vie ?",
        ),
        "contacts": ChapterWords(
            title="Là où elle rencontre ton thème",
            question="Comment ça rejoint qui je suis déjà ?",
        ),
    },
    "compatibility": {
        "attraction": ChapterWords(
            title="Ce qui attire",
            question="Pourquoi cette personne-là et pas une autre ?",
        ),
        "friction": ChapterWords(
            # Not "Là où ça accroche", which is the literal translation and
            # means the opposite in spoken French — "ça accroche entre eux" is
            # what you say when two people click. "Ça coince" is the snag.
            title="Là où ça coince",
            question="Sur quoi on va se disputer, encore et encore ?",
        ),
        "overlays": ChapterWords(
            # "Chez" is the house preposition, and this chapter is houses: one
            # person's planets falling into the other's. French gets the pun
            # the English title only gestures at.
            title="Là où on tombe l'un chez l'autre",
            question="Cette personne occupe quelle partie de ma vie ?",
        ),
        "together": ChapterWords(
            # "Vous" here is the two of them, not the polite singular. The
            # composite chart is a third thing with its own sky, which is why
            # the title counts them and then makes them one.
            title="Vous deux comme une seule chose",
            question="Elle est comment, la relation elle-même ?",
        ),
    },
    "astrocartography": {
        "lines": ChapterWords(
            title="Tes lignes",
            question="Quels lieux amplifient quelle partie de moi ?",
        ),
        "here": ChapterWords(
            title="Là où tu es maintenant",
            # Dislocated, because that is how the question actually arrives at
            # two in the morning: the place first, then what it is doing to you.
            question="Il me fait quoi, l'endroit où je vis ?",
        ),
        "crossings": ChapterWords(
            title="Croisements",
            question="Où deux choses arrivent en même temps ?",
        ),
    },
    "synthesis": {
        "agreement": ChapterWords(
            # "S'accorder" is the verb the whole French product uses for this —
            # the hero, the FAQ, the synthesis section all say it. It is also
            # the better word: systems that agree are in tune, not in a vote.
            title="Là où les systèmes s'accordent",
            question="Qu'est-ce qui est vrai depuis plus d'une direction ?",
        ),
        "disagreement": ChapterWords(
            title="Là où ils se contredisent",
            question="Dans quelle contradiction je vis vraiment ?",
        ),
        "single": ChapterWords(
            title="Ce qu'un seul système voit",
            question="Qu'est-ce que je raterais en n'en lisant qu'un seul ?",
        ),
        "whole": ChapterWords(
            title="Tout ça ensemble",
            # "Ça donne quoi" is exactly "what does this add up to" in French,
            # and it is what somebody says out loud at the end of a long list.
            # "Quelle est la somme de tout cela ?" is the translation and
            # nobody has ever said it.
            question="Alors, ça donne quoi, tout ça ?",
        ),
    },
}

#: The nine keys are English on purpose and are not words. `__init__.py` says
#: why at length: the name is what `synthesis.compute` files a signal under,
#: what the synthesis chapter's `reads` tuple matches on, and what the model
#: cites and `ai/validator.py` compares character for character. The values
#: are the only copy in this half of the file.
#:
#: A pair is shown at once, one under the other, beneath an axis the systems
#: disagree about. So each pair is written to the same grammatical shape —
#: two verb phrases, or two noun phrases, never one of each. Where the English
#: breaks its own rule, the note on that axis says what French does instead.
AXES: dict[str, AxisWords] = {
    "Direction": AxisWords(
        negative="travaille seul, hors de vue",
        positive="travaille en public, devant les gens",
    ),
    "Character": AxisWords(
        negative="tient sa position",
        positive="change de forme",
    ),
    "Mind": AxisWords(
        negative="veut d'abord une preuve",
        positive="se fie à la première impression",
    ),
    # Straight out of `src/lib/i18n/fr.ts`, which already prints this exact
    # pair as its example of two systems contradicting each other: "Ton thème
    # veut un témoin ; ta Carte de naissance veut une porte ouverte." A reader
    # who saw the landing page should meet the same two clauses in the app.
    "Relationships": AxisWords(
        negative="veut une porte ouverte",
        positive="veut un témoin",
    ),
    # CONSTRUCTION CHANGED. The English swaps subject mid-pair: "builds their
    # own" is about the person, "arrives through other people" is about the
    # money. In English the ellipsis hides it; in French the verb agreement
    # would not, and the pair would read as two unrelated statements rather
    # than two ends of one line. Both halves keep the person as the subject
    # and the resources as the object.
    "Resources": AxisWords(
        negative="construit les siennes",
        positive="les reçoit des autres",
    ),
    # "Répétable" exists in French and belongs in a manual. "Répété" is the
    # same fact about the practice — that it comes back — in a word somebody
    # would use.
    "Work": AxisWords(
        negative="un seul grand effort",
        positive="un petit geste répété",
    ),
    "Weak point": AxisWords(
        negative="craint de ne pas être vu",
        positive="craint d'être vu",
    ),
    # CONSTRUCTION CHANGED, slightly. The English pole is "asked to be seen",
    # reusing "seen" from the axis above it; French would need "appelé à être
    # vu", which is heavy and would make the two axes look like the same
    # sentence twice. "Se montrer" is the active side of the same demand and
    # keeps the parallel with "se retirer" inside the pair, which is the
    # parallel the reader is actually looking at.
    "Growth": AxisWords(
        negative="appelé à se retirer",
        positive="appelé à se montrer",
    ),
    "Rhythms": AxisWords(
        negative="une saison qui se referme",
        positive="une saison qui s'ouvre",
    ),
}
