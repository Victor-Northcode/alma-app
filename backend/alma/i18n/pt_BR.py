"""Alma in Brazilian Portuguese.

The 41 chapter titles and questions and the nine pairs of synthesis poles,
in Brazilian Portuguese. Nothing else belongs in this file: the structure they hang on —
which factors a chapter reads from, its word budget, whether it needs a birth
time — lives in `alma/ai/chapters.py`, and the axis *names* are identifiers
that stay English everywhere. `alma/i18n/__init__.py` explains why.

What these strings are, so they are written as what they are.

A **title** is a noun phrase of two or three words: the name of a room in
somebody's chart. Not a heading, not a sentence.

A **question** is the reader's own, in their own voice, and it is the reason
they tap. "How do I attach, and what breaks it?" is a question somebody asks
themselves at two in the morning. It stays a question in Brazilian Portuguese, and it
stays theirs.

A **pole** is a short clause describing a way of being, and the pair has to
read as two ends of one line — the reader sees both at once, under the axis
they disagree about.

Alma's voice is plain, exact, a little cool. Never breathy, never flattering,
never mystical for its own sake; concrete over cosmic. `src/lib/i18n/pt-BR.ts`
is the reference for how she already sounds in Brazilian Portuguese — most of it was
written rather than translated, and this file should sound like it came from
the same person. A literal rendering of the English will read like a
translated app, which is the one thing this product is built not to be.

Two things Brazilian Portuguese decides differently from English, and both were
decided the same way each time.

**Gender.** A participle agrees with the person it describes, and this file
never knows who is reading. "teme não ser visto" tells half the readers the
sentence was not written for them. So wherever the English leans on a past
participle — *fears being unseen*, *asked to withdraw* — the Portuguese is
rebuilt on a verb or a noun instead, which costs nothing and reads to
everybody: "teme sumir de vista", "a tarefa é se recolher". `src/lib/i18n/pt-BR.ts`
already avoids gendered forms the same way, sentence by sentence, and that is
why.

**Idiom over gloss.** *How do I come across before I speak?* glosses to
"como eu apareço antes de falar", which nobody says. What a Brazilian actually
says is "antes de abrir a boca", so that is what is here. The same for *what
do I keep re-staging?* → "que cena eu vivo repetindo?", which keeps the
staging and drops the Latinate verb. Every departure of that kind is marked
with a comment beside it.

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

#: False while the strings below are still the English, waiting to be
#: replaced. Flip it to True when every one of them is Brazilian Portuguese —
#: `tests/test_locales.py` reads this, and from that moment on any string
#: still identical to the English fails the suite.
WRITTEN = True

#: Words that are correctly the same in Brazilian Portuguese as in English. Listed one
#: at a time rather than waved through, exactly as `scripts/check-locales.mjs`
#: does for the web dictionaries, and only consulted once `WRITTEN` is True.
SHARED: frozenset[str] = frozenset()

CHAPTERS: dict[str, dict[str, ChapterWords]] = {
    "natal": {
        # "Núcleo" is already the word the ceremony on the web uses for this —
        # "aquilo vai para o seu núcleo" — so the first chapter a reader ever
        # opens is called what the site promised them it would be called.
        "core": ChapterWords(
            title="Núcleo",
            question="Como eu sou de verdade, por baixo?",
        ),
        # *Come across before I speak* has no gloss anybody says out loud.
        # "Antes de abrir a boca" is the phrase, and it is the same register:
        # dry, physical, slightly impatient.
        "portrait": ChapterWords(
            title="Retrato",
            question="Como eu chego antes de abrir a boca?",
        ),
        "love": ChapterWords(
            title="Amor e proximidade",
            question="Como eu me apego e o que quebra isso?",
        ),
        "money": ChapterWords(
            title="Dinheiro e recursos",
            question="Por onde o dinheiro chega até mim?",
        ),
        "career": ChapterWords(
            title="Carreira e vocação",
            question="Que trabalho não me esgota?",
        ),
        # "Como eu soo" is not Portuguese. The question is about what leaves
        # the mouth, so it says that.
        "mind": ChapterWords(
            title="Mente e fala",
            question="Como eu penso e como isso sai quando eu falo?",
        ),
        # *Re-staging* is theatre in English and the theatre is the point: the
        # same scene, mounted again. "Que cena eu vivo repetindo" keeps the
        # stage and loses the Latinate verb nobody would say.
        "shadow": ChapterWords(
            title="Sombra e ferida",
            question="O que eu vivo repetindo?",
        ),
        "roots": ChapterWords(
            title="Raízes e família",
            question="O que eu herdei sem ter concordado?",
        ),
        # "Sendo levado" would gender the reader; "me levando" does not, and
        # is the more natural way to ask it anyway.
        "karmic-axis": ChapterWords(
            title="Eixo cármico",
            question="Para onde isso tudo está me levando?",
        ),
        "work-rhythms": ChapterWords(
            title="Trabalho e ritmos",
            question="Que ritmo eu aguento manter?",
        ),
        "transformation": ChapterWords(
            title="Crises e transformação",
            question="Como eu desmorono e como eu me reconstruo?",
        ),
        "freedom": ChapterWords(
            title="Liberdade e singularidade",
            question="Onde eu me recuso a ser igual aos outros?",
        ),
        "dreams": ChapterWords(
            title="Sonhos e limites",
            question="Onde eu perco meus contornos?",
        ),
        # *Built to be around* turns into a boast in Portuguese if translated
        # literally. "Com quem eu funciono" is the same claim, colder.
        "circle": ChapterWords(
            title="Círculo e aliados",
            question="Com quem eu funciono de verdade?",
        ),
        "worldview": ChapterWords(
            title="Visão de mundo e crescimento",
            question="No que eu acredito quando ninguém está olhando?",
        ),
        "milestones": ChapterWords(
            title="Marcos por idade",
            question="Quando o formato da minha vida muda?",
        ),
    },
    "numerology": {
        "life-path": ChapterWords(
            title="Caminho de vida",
            question="No que eu vim gastar a minha vida?",
        ),
        # Not "número do dia": that collides with the *dia pessoal* this
        # system also computes, one chapter down.
        "birthday-number": ChapterWords(
            title="Número do nascimento",
            question="O que me vem fácil e eu não dou valor?",
        ),
        # *Season* is a northern word for a stretch of the year. In Brazil the
        # seasons barely mark anything, so this asks about the phase, which is
        # what the chapter is actually about.
        "personal-year": ChapterWords(
            title="Ano pessoal",
            question="Em que fase eu estou, de verdade?",
        ),
        # "Cobrado" — what is being demanded of me — is what a Brazilian says
        # here. "Pedido" would soften a chapter about challenges.
        "pinnacles": ChapterWords(
            title="Pináculos e desafios",
            question="O que está sendo cobrado de mim agora?",
        ),
        # *The name I answer to* has no equivalent construction. "O nome que
        # me chamam" is how it is said.
        "name": ChapterWords(
            title="Números do nome",
            question="O que carrega o nome que me chamam?",
        ),
    },
    "birth-card": {
        "personality": ChapterWords(
            title="Carta da personalidade",
            question="Como as pessoas me leem?",
        ),
        "soul": ChapterWords(
            title="Carta da alma",
            question="O que corre por baixo disso?",
        ),
        "year-card": ChapterWords(
            title="Carta do ano",
            question="Para que serve esse ano em particular?",
        ),
    },
    "transits": {
        "active": ChapterWords(
            title="O que está ativo agora",
            question="O que está acontecendo comigo, de verdade?",
        ),
        "ahead": ChapterWords(
            title="Os próximos meses",
            question="O que vem e quando?",
        ),
        "long": ChapterWords(
            title="Os trânsitos longos",
            question="Do que se trata esse capítulo inteiro da minha vida?",
        ),
    },
    "solar-return": {
        "year-shape": ChapterWords(
            title="O formato do ano",
            question="Para que serve esse ano?",
        ),
        "emphasis": ChapterWords(
            title="Onde o ano cai",
            question="Que parte da minha vida ele toca?",
        ),
        "contacts": ChapterWords(
            title="Onde ele encontra seu mapa",
            question="Como isso se liga a quem eu já sou?",
        ),
    },
    "compatibility": {
        "attraction": ChapterWords(
            title="O que puxa",
            question="Por que essa pessoa e não outra?",
        ),
        # "Travar" is what a Brazilian says about a thing that keeps jamming
        # at the same point — which is what this chapter is.
        "friction": ChapterWords(
            title="Onde trava",
            question="Sobre o que a gente vai brigar sempre?",
        ),
        # House overlays: each chart falls into the other's rooms. "Cai" keeps
        # that, and keeps it physical.
        "overlays": ChapterWords(
            title="Onde um cai no outro",
            question="Que parte da minha vida essa pessoa ocupa?",
        ),
        "together": ChapterWords(
            title="Vocês dois como uma coisa só",
            question="Como é a relação em si?",
        ),
    },
    "astrocartography": {
        "lines": ChapterWords(
            title="Suas linhas",
            question="Que lugar amplifica que parte de mim?",
        ),
        "here": ChapterWords(
            title="Onde você está agora",
            question="O que o lugar onde eu moro está fazendo comigo?",
        ),
        "crossings": ChapterWords(
            title="Cruzamentos",
            question="Onde duas coisas acontecem ao mesmo tempo?",
        ),
    },
    "synthesis": {
        # *From more than one direction* would import "direção", which is an
        # axis name three lines down and an identifier. "Por mais de um lado"
        # says the same thing and borrows nothing.
        "agreement": ChapterWords(
            title="Onde os sistemas concordam",
            question="O que é verdade por mais de um lado?",
        ),
        "disagreement": ChapterWords(
            title="Onde eles discordam",
            question="Em que contradição eu vivo, de verdade?",
        ),
        "single": ChapterWords(
            title="O que só um sistema vê",
            question="O que eu perderia lendo só um deles?",
        ),
        # "Tudo junto" is the phrase the web already uses for this group of
        # systems, and "no fim das contas" is how the sum is asked for.
        "whole": ChapterWords(
            title="Tudo junto",
            question="No fim das contas, o que isso tudo dá?",
        ),
    },
}

AXES: dict[str, AxisWords] = {
    # "Sozinho" would gender the reader. "A portas fechadas" is the idiom for
    # working where nobody is watching, and it pairs cleanly against "em
    # público": both clauses are a manner and then a witness.
    "Direction": AxisWords(
        negative="trabalha a portas fechadas, longe dos olhos",
        positive="trabalha em público, na frente das pessoas",
    ),
    "Character": AxisWords(
        negative="mantém a posição",
        positive="muda de forma",
    ),
    "Mind": AxisWords(
        negative="quer prova antes",
        positive="confia na primeira impressão",
    ),
    # Word for word what the landing page already says when it shows this
    # axis disagreeing: "seu mapa quer uma testemunha; sua Carta de nascimento
    # quer uma porta aberta."
    "Relationships": AxisWords(
        negative="quer uma porta aberta",
        positive="quer uma testemunha",
    ),
    # The English pair turns on *own* versus *other people*. Portuguese can
    # carry it on one noun: whose hands.
    "Resources": AxisWords(
        negative="constrói com as próprias mãos",
        positive="chega pelas mãos dos outros",
    ),
    "Work": AxisWords(
        negative="um empurrão grande, de uma vez",
        positive="uma prática pequena, repetida",
    ),
    # *Fears being unseen / fears being seen* is a participle at both ends,
    # and a participle agrees with whoever is reading. Built on "vista"
    # instead: nothing to agree with, and the two ends stay one line.
    "Weak point": AxisWords(
        negative="teme sumir de vista",
        positive="teme ficar à vista",
    ),
    # Same problem, same fix: "chamado a" would gender it. A task has no
    # gender, and the two reflexive verbs mirror each other exactly.
    "Growth": AxisWords(
        negative="a tarefa é se recolher",
        positive="a tarefa é se expor",
    ),
    # "Estação" is weather in Brazil. A cycle is what opens and closes.
    "Rhythms": AxisWords(
        negative="um ciclo que se fecha",
        positive="um ciclo que se abre",
    ),
}
