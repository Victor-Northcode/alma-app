"""Alma in Italian.

The 41 chapter titles and questions and the nine pairs of synthesis poles,
in Italian. Nothing else belongs in this file: the structure they hang on —
which factors a chapter reads from, its word budget, whether it needs a birth
time — lives in `alma/ai/chapters.py`, and the axis *names* are identifiers
that stay English everywhere. `alma/i18n/__init__.py` explains why.

What these strings are, so they are written as what they are.

A **title** is a noun phrase of two or three words: the name of a room in
somebody's chart. Not a heading, not a sentence.

A **question** is the reader's own, in their own voice, and it is the reason
they tap. "How do I attach, and what breaks it?" is a question somebody asks
themselves at two in the morning. It stays a question in Italian, and it
stays theirs.

A **pole** is a short clause describing a way of being, and the pair has to
read as two ends of one line — the reader sees both at once, under the axis
they disagree about.

Alma's voice is plain, exact, a little cool. Never breathy, never flattering,
never mystical for its own sake; concrete over cosmic. `src/lib/i18n/it.ts`
is the reference for how she already sounds in Italian — most of it was
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
"""

from __future__ import annotations

from .words import AxisWords, ChapterWords

#: All 100 strings below are Italian. From here on `tests/test_locales.py`
#: fails on any one of them that is still character-for-character English and
#: not listed in `SHARED`.
WRITTEN = True

#: Empty, and it stays empty unless somebody can name the string. Italian
#: happens to have a word of its own for every one of these — even "Portrait",
#: which French and German keep, is *Ritratto* here — so nothing needs waving
#: through. A blanket exemption would make the check above a formality.
SHARED: frozenset[str] = frozenset()

# Two things this file does that the English does not, both deliberate.
#
# The masculine generic. Italian makes the reader pick a gender in places
# English never does — *fatto*, *visto*, *chiamato*. The product already chose:
# the landing page says "Ti dico di cosa sei fatto" and the journey asks
# "Quando sei nato?". Splitting the difference here with */a endings or
# neutral circumlocutions would sound like a form, not like Alma, and it would
# sound different from the sentence directly above it on the same screen.
#
# The reader's own voice. A question is asked at two in the morning, so it
# takes the shape spoken Italian actually uses — left dislocation ("I soldi, da
# dove mi arrivano davvero?"), *sotto sotto*, *aprire bocca*, *andare in
# pezzi*. Where the English leans on a construction Italian does not have, the
# construction changed rather than the language; the individual notes below say
# where and why.

CHAPTERS: dict[str, dict[str, ChapterWords]] = {
    "natal": {
        # *Nucleo* rather than a loan word: the journey already says "Dove tre
        # tradizioni concordano, quello va nel tuo nucleo", so this room has
        # had an Italian name since before the chapter list existed. And
        # *sotto sotto* is what an Italian actually says for "underneath" when
        # they mean a person and not a shelf.
        "core": ChapterWords(
            title="Nucleo",
            question="Sotto sotto, come sono fatto?",
        ),
        # "Come across" has no Italian verb. *Che effetto faccio* is the
        # phrase, and *prima di aprire bocca* is what replaces "before I
        # speak" — it carries the same faint impatience.
        "portrait": ChapterWords(
            title="Ritratto",
            question="Che effetto faccio prima di aprire bocca?",
        ),
        "love": ChapterWords(
            title="Amore e vicinanza",
            question="Come mi lego e cosa lo rompe?",
        ),
        # *Soldi*, not *denaro*. The support page already says "I soldi li
        # tiene lo store"; *denaro* is the word on a bank statement.
        "money": ChapterWords(
            title="Soldi e risorse",
            question="I soldi, da dove mi arrivano davvero?",
        ),
        "career": ChapterWords(
            title="Carriera e vocazione",
            question="Che lavoro non mi consuma?",
        ),
        # "How do I sound" is an English idiom — *come suono* in Italian is
        # what an instrument does. The two halves keep their symmetry instead:
        # penso / lo dico.
        "mind": ChapterWords(
            title="Mente e parola",
            question="Come penso e come lo dico?",
        ),
        "shadow": ChapterWords(
            title="Ombra e ferita",
            question="Cosa continuo a ripetere?",
        ),
        "roots": ChapterWords(
            title="Radici e famiglia",
            question="Cosa ho ereditato senza averlo scelto?",
        ),
        # The English is an agentless passive — "being moved" by nothing you
        # can name. Italian has no comfortable way to say that without
        # inventing a mover, so the sentence turns and *tutto questo* does the
        # work: it points at the chart, not at a destiny.
        "karmic-axis": ChapterWords(
            title="Asse karmico",
            question="Verso cosa mi sta portando tutto questo?",
        ),
        "work-rhythms": ChapterWords(
            title="Lavoro e ritmi",
            question="Che ritmo riesco a tenere?",
        ),
        "transformation": ChapterWords(
            title="Crisi e trasformazione",
            question="Come vado in pezzi e come mi rimetto insieme?",
        ),
        # *Come tutti* rather than a literal "come chiunque altro": it is
        # shorter, and it is the thing people say.
        "freedom": ChapterWords(
            title="Libertà e unicità",
            question="Dove mi rifiuto di essere come tutti?",
        ),
        # "Edges" is the English way of not repeating "boundaries".
        # *Contorni* does the same job in Italian and is just as physical.
        "dreams": ChapterWords(
            title="Sogni e confini",
            question="Dove perdo i contorni?",
        ),
        "circle": ChapterWords(
            title="Cerchia e alleati",
            question="Con chi sono fatto per stare?",
        ),
        # *Visione del mondo* is four words and reads like a syllabus.
        # *Convinzioni* is one word and is what the question is about.
        "worldview": ChapterWords(
            title="Convinzioni e crescita",
            question="In cosa credo quando non mi guarda nessuno?",
        ),
        "milestones": ChapterWords(
            title="Tappe per età",
            question="Quando cambia la forma della mia vita?",
        ),
    },
    "numerology": {
        # The web already calls it "Sentiero di vita" on the landing page, two
        # seconds after somebody types their date. Same room, same name.
        "life-path": ChapterWords(
            title="Sentiero di vita",
            question="A cosa sono fatto per dedicare la mia vita?",
        ),
        # "Discount" as a verb is English. *Dare per scontato* is the exact
        # Italian move — you have it, so you stop counting it.
        "birthday-number": ChapterWords(
            title="Numero di nascita",
            question="Cosa mi viene facile e do per scontato?",
        ),
        "personal-year": ChapterWords(
            title="Anno personale",
            question="In che stagione sono davvero?",
        ),
        # *Pinnacoli* exists in Italian numerology and sounds like a manual.
        # *Vette e prove* is two plain nouns that hold each other up.
        "pinnacles": ChapterWords(
            title="Vette e prove",
            question="Cosa mi viene chiesto, adesso?",
        ),
        # *Rispondere a un nome* is the Italian idiom behind "the name I
        # answer to", and *portarsi dietro* is what a name does with what it
        # carries.
        "name": ChapterWords(
            title="Numeri del nome",
            question="Cosa si porta dietro il nome a cui rispondo?",
        ),
    },
    "birth-card": {
        "personality": ChapterWords(
            title="Carta della personalità",
            question="Come mi leggono gli altri?",
        ),
        "soul": ChapterWords(
            title="Carta dell'anima",
            question="E sotto, cosa scorre?",
        ),
        "year-card": ChapterWords(
            title="Carta dell'anno",
            question="A cosa serve proprio quest'anno?",
        ),
    },
    "transits": {
        "active": ChapterWords(
            title="Cos'è attivo adesso",
            question="Cosa mi sta succedendo davvero?",
        ),
        "ahead": ChapterWords(
            title="I prossimi mesi",
            question="Cosa sta arrivando e quando?",
        ),
        # "This whole chapter of my life" cannot stay a *capitolo* here — the
        # thing the reader is holding is literally a chapter, and the word
        # would point at the screen instead of at their life. *Pezzo di vita*
        # is what somebody says out loud anyway.
        "long": ChapterWords(
            title="I transiti lunghi",
            question="Di cosa parla questo pezzo di vita?",
        ),
    },
    "solar-return": {
        "year-shape": ChapterWords(
            title="La forma dell'anno",
            question="A cosa serve quest'anno?",
        ),
        "emphasis": ChapterWords(
            title="Dove cade l'anno",
            question="Quale parte della mia vita tocca?",
        ),
        "contacts": ChapterWords(
            title="Dove incontra il tuo tema",
            question="Come si aggancia a chi sono già?",
        ),
    },
    "compatibility": {
        "attraction": ChapterWords(
            title="Cosa attira",
            question="Perché questa persona e non un'altra?",
        ),
        # *Incepparsi* is what a mechanism does when it catches — the same
        # concrete, unglamorous register as the English.
        "friction": ChapterWords(
            title="Dove si inceppa",
            question="Su cosa continueremo a litigare?",
        ),
        "overlays": ChapterWords(
            title="Dove cadiamo uno nell'altro",
            question="Che parte della mia vita occupa questa persona?",
        ),
        "together": ChapterWords(
            title="Voi due come una cosa sola",
            question="Com'è la relazione in sé?",
        ),
    },
    "astrocartography": {
        # "Amplify" would be *amplifica*, which belongs to a mixing desk.
        # *Accendere* is what a place does to a part of somebody.
        "lines": ChapterWords(
            title="Le tue linee",
            question="Quale posto accende quale parte di me?",
        ),
        "here": ChapterWords(
            title="Dove sei adesso",
            question="Cosa mi sta facendo il posto in cui vivo?",
        ),
        "crossings": ChapterWords(
            title="Incroci",
            question="Dove succedono due cose insieme?",
        ),
    },
    "synthesis": {
        # *Concordare* and *contraddirsi* are the two verbs the landing page
        # and the cabinet already use for these two states. A reader meets
        # them before they ever open a chapter.
        "agreement": ChapterWords(
            title="Dove i sistemi concordano",
            question="Cos'è vero da più di una parte?",
        ),
        "disagreement": ChapterWords(
            title="Dove si contraddicono",
            question="In quale contraddizione vivo davvero?",
        ),
        "single": ChapterWords(
            title="Quello che vede un solo sistema",
            question="Cosa mi perderei leggendone uno solo?",
        ),
        # "So what does this add up to?" opens on a shrug. *Allora* is that
        # shrug, and *venire fuori* is the sum without the arithmetic.
        "whole": ChapterWords(
            title="Tutto insieme",
            question="Allora, cosa ne viene fuori?",
        ),
    },
}

# The keys are identifiers and stay English — the model cites them and
# `ai/validator.py` compares them character by character. The clients already
# show the reader "Direzione", "Punto debole" and the other seven, keyed on
# these words: `t.synthesis.axes` on the web, `cab.axis.*` in
# `Cabinet.xcstrings`. Only the values below are copy.
#
# Each pair is read at once, one under the other, so the two ends are held to
# the same grammatical shape in Italian even where the English lets itself
# drift.
AXES: dict[str, AxisWords] = {
    "Direction": AxisWords(
        negative="lavora da solo, lontano dagli occhi",
        positive="lavora in pubblico, davanti alla gente",
    ),
    "Character": AxisWords(
        negative="tiene la posizione",
        positive="cambia forma",
    ),
    "Mind": AxisWords(
        negative="prima vuole le prove",
        positive="si fida della prima impressione",
    ),
    # Word for word what the landing page already puts in this reader's mouth:
    # "Il tuo tema vuole un testimone; la tua Carta di nascita vuole una porta
    # aperta." Anything else here would be a second Italian for one idea.
    "Relationships": AxisWords(
        negative="vuole una porta aperta",
        positive="vuole un testimone",
    ),
    # The English changes subject halfway across the axis: the person builds,
    # then the money arrives. Read as a pair in Italian that lands as two
    # unrelated clauses, so the person stays the subject at both ends and the
    # clitic *le* carries the resources over from the axis name above them.
    "Resources": AxisWords(
        negative="se le costruisce da solo",
        positive="le riceve dagli altri",
    ),
    "Work": AxisWords(
        negative="un unico grande sforzo",
        positive="una piccola pratica ripetuta",
    ),
    "Weak point": AxisWords(
        negative="teme di non essere visto",
        positive="teme di essere visto",
    ),
    # "Asked to" with nobody doing the asking again. *Chiamato a* is the
    # Italian that carries a demand without naming who makes it, and it keeps
    # both ends to three words the way the English does.
    "Growth": AxisWords(
        negative="chiamato a ritirarsi",
        positive="chiamato a farsi vedere",
    ),
    "Rhythms": AxisWords(
        negative="una stagione che si chiude",
        positive="una stagione che si apre",
    ),
}
