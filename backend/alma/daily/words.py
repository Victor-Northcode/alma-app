"""Every word the daily says for itself, in all six languages.

Two very different kinds of string live here and it is worth being clear about
why they are in one file.

**The notification line is assembled, not generated.** `notification.py` argues
that at length; the consequence is this table. A line like *"Transit-Saturn im
Quadrat zu deiner Sonne — exakt um 14:20"* has four moving parts — the
transiting body, the aspect, the natal point, the instant — and three of them
are astrological vocabulary that has a settled word in each language and no
word at all on the server today. `JourneyL10n.swift` and the Android
`strings.xml` files hold exactly one of them (`ascendant`), each in their own
client, which is the shape of a table that is about to be written twice and
disagree. It is written once, here, on the server that composes the line.

**Grammar is stored, not computed.** `POINTS` holds *"deiner Sonne"* rather
than *"Sonne"*, because every aspect phrase in German takes the dative and the
possessive inflects for the noun's gender: `deiner` Sonne, `deinem` Mond,
`deinem` Aszendenten. The same is true of French (`ton` Soleil, `ta` Lune) and
Italian (`il tuo` Sole, `la tua` Luna). A server that stored bare nouns would
have to know the gender of fifteen words in five languages and the case each
preposition governs — which is a grammar engine, and a grammar engine is how
you ship *"in Quadrat zu dein Sonne"* to a paying subscriber. Storing the
inflected phrase moves that knowledge to the person writing the translation,
which is where it already is.

For the same reason the aspect phrases were chosen to end in a preposition that
does **not** contract with what follows: Italian and Portuguese use *con* /
*com* for opposition rather than the more usual *a*, because *"in opposizione a
il tuo Sole"* is wrong and *"al tuo Sole"* would need the server to contract it.
Spanish keeps *a* because *tu* is a possessive, not an article, and does not
contract.

**What is not here.** No sentence about what a transit *means*. Every such
sentence is generated, cited and validated (`alma/ai/validator.py`); a table of
canned interpretations is the horoscope this product exists not to be, and
`docs/THE-DAILY.md §2.5` already refused the cheaper version of that idea on
the same grounds. What is in this file is either a proper noun, a grammatical
connective, or a piece of interface furniture.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import i18n

#: The natal points the daily can name. Exactly the keys of
#: `transits.NATAL_WEIGHT` plus the two angles `transits.natal_points` adds,
#: because those are the only things a `Hit.natal` can be. A test asserts the
#: two lists are the same, so a new natal point cannot be transited into
#: existence without acquiring six words first — the failure otherwise is an
#: English "Ascendant" sitting inside an Italian sentence, which is the exact
#: defect `docs/PUSH.md §3` found in the naive `loc-args` design.
POINT_KEYS: tuple[str, ...] = (
    "sun", "moon", "ascendant", "midheaven", "mercury", "venus", "mars",
    "saturn", "jupiter", "chiron", "true_node", "uranus", "neptune", "pluto",
    "lilith",
)

#: The moving bodies. `moon` is here even though `docs/THE-DAILY.md §1.5`
#: excludes it from the daily permanently: this table is vocabulary, and the
#: exclusion belongs in `selection.py` where it can be tested. A missing word
#: would turn a policy decision into a KeyError somewhere unrelated.
BODY_KEYS: tuple[str, ...] = (
    "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus",
    "neptune", "pluto", "chiron",
)

ASPECT_KEYS: tuple[str, ...] = (
    "conjunction", "sextile", "square", "trine", "opposition",
)

#: The settings surface, keyed exactly as `docs/THE-DAILY.md §5.4` names it so
#: that the three clients and this file can be compared key by key rather than
#: by reading two documents side by side.
SETTING_KEYS: tuple[str, ...] = (
    "daily.setting.title",
    "daily.setting.off",
    "daily.setting.occasionally",
    "daily.setting.only_what_matters",
    "daily.setting.off.detail",
    "daily.setting.occasionally.detail",
    "daily.setting.only_matters.detail",
    "daily.setting.hour",
    "daily.setting.quiet",
    "daily.setting.timezone",
    "daily.setting.timezone.device",
    "daily.setting.timezone.birth",
    "daily.setting.timezone.chosen",
    "daily.action.turn_off",
    "daily.action.quieter",
    "daily.empty.title",
    "daily.empty.body",
)


@dataclass(frozen=True, slots=True)
class DailyWords:
    """One language's whole vocabulary for the daily."""

    locale: str

    #: What the prompt calls this piece and what it asks. The daily's `Chapter`
    #: is built per-locale from these rather than looked up through
    #: `i18n.chapter_words`, because it deliberately is not in
    #: `chapters.BY_SYSTEM` — putting it there would add a 41st chapter to the
    #: table of contents, to the paywall, and to `tests/test_locales.py`'s
    #: comparison of all six catalogue files, none of which is what the daily
    #: is. `writer.build_prompt` asks the chapter for its own words, so a
    #: locally-built `Chapter` is the whole mechanism needed.
    title: str
    question: str

    #: name → the moving body, in whatever form `transiting` below needs.
    #:
    #: **Not uniformly a bare noun and not uniformly an article-carrying one.**
    #: The two fields are one unit: English and German mark the transit with a
    #: *prefix* ("Transiting {body}", "Transit-{body}") and so want the bare
    #: nominative, while the four Romance languages mark it with a *suffix*
    #: ("{body} en tránsito") and so want the article in front of the noun
    #: where it belongs. Filling this table without reading `transiting` is how
    #: German shipped **"Transit-die Sonne im Quadrat zu deiner Sonne"** — the
    #: transiting Sun is 23% of all pushes, so roughly a quarter of German
    #: lock-screen titles carried a grammar error. `tests/test_daily.py`
    #: asserts no composed line in any locale contains a doubled article.
    bodies: dict[str, str]
    #: name → "your Sun", already inflected for whatever `aspects` governs.
    points: dict[str, str]
    #: aspect → the connective phrase, e.g. "im Quadrat zu".
    aspects: dict[str, str]

    #: "{body}" → how a transiting body is marked as transiting. Its own
    #: template because the word order differs: English prefixes it and the
    #: five Romance/Germanic others either suffix it or hyphenate it.
    transiting: str

    line_exact: str

    #: The same line for a moment that has **already happened** when the
    #: notification lands.
    #:
    #: Delivery is fixed at 08:00 local (`selection.DELIVERY_HOUR`), and a
    #: simulation over six charts and a full year found **39% of exact-hit
    #: pushes perfect before 08:00** — Seoul at 00:04, Auckland at 01:16,
    #: Buenos Aires at 00:02. `line_exact` carries no tense, so all of those
    #: read as something still to come: a person waits for 00:04 and nothing
    #: arrives, and after one of those they stop reading the time as
    #: information at all. That is 27% of every notification this feature
    #: sends, on the one line the whole product is differentiated by.
    #:
    #: **The past marker attaches to the hour, not to the planet.** Spanish,
    #: Italian and Portuguese say "a las / alle / às", which is an elided
    #: feminine plural — "ya pasadas", "ormai passate", "já passadas" agree
    #: with *that* and are therefore invariant with respect to the transiting
    #: body. French uses the impersonal "c'est déjà passé" for the same reason.
    #: A past participle agreeing with the subject would break on Italian
    #: Venere and French Vénus, which are feminine where every other body in
    #: those tables is masculine — and relying on Venus being too light to
    #: clear the push floor would be a grammar decision resting on a weight
    #: constant in another module.
    line_exact_past: str

    line_entering: str
    line_quiet: str

    settings: dict[str, str] = field(default_factory=dict)

    def contact(self, *, body: str, aspect: str, point: str) -> str:
        """"Transit-Saturn im Quadrat zu deiner Sonne" — the naming half."""
        return " ".join(
            (
                self.transiting.format(body=self.bodies[body]),
                self.aspects[aspect],
                self.points[point],
            )
        )


EN = DailyWords(
    locale="en",
    title="Today",
    question="What is actually happening in my chart today?",
    # Bare, because `transiting` prefixes: "Transiting Sun", which is also how
    # every astrologer writes it. "Transiting the Sun" is what the article
    # bought.
    bodies={
        "sun": "Sun", "moon": "Moon", "mercury": "Mercury",
        "venus": "Venus", "mars": "Mars", "jupiter": "Jupiter",
        "saturn": "Saturn", "uranus": "Uranus", "neptune": "Neptune",
        "pluto": "Pluto", "chiron": "Chiron",
    },
    points={
        "sun": "your Sun", "moon": "your Moon", "ascendant": "your Ascendant",
        "midheaven": "your Midheaven", "mercury": "your Mercury",
        "venus": "your Venus", "mars": "your Mars", "saturn": "your Saturn",
        "jupiter": "your Jupiter", "chiron": "your Chiron",
        "true_node": "your North Node", "uranus": "your Uranus",
        "neptune": "your Neptune", "pluto": "your Pluto",
        "lilith": "your Lilith",
    },
    aspects={
        "conjunction": "conjunct", "sextile": "sextile", "square": "square",
        "trine": "trine", "opposition": "opposite",
    },
    transiting="Transiting {body}",
    line_exact="{contact} — exact at {time}",
    line_exact_past="{contact} — exact at {time}, earlier today",
    line_entering="{contact} — in orb from today",
    line_quiet="A quiet week. {contact} is the one thing still moving.",
    settings={
        "daily.setting.title": "The daily",
        "daily.setting.off": "Off",
        "daily.setting.occasionally": "Occasionally",
        "daily.setting.only_what_matters": "Only what matters",
        "daily.setting.off.detail":
            "No notifications. Today is still here whenever you open it.",
        "daily.setting.occasionally.detail":
            "About once a week, when something in your chart is actually exact.",
        "daily.setting.only_matters.detail":
            "A few times a year. The slow ones only — the transits that last months.",
        "daily.setting.hour": "Arrives at",
        "daily.setting.quiet": "Never between 22:00 and 08:00, in your time.",
        "daily.setting.timezone": "Your time",
        "daily.setting.timezone.device": "from your device",
        "daily.setting.timezone.birth": "from your birth data",
        "daily.setting.timezone.chosen": "you chose this",
        "daily.action.turn_off": "Turn these off",
        "daily.action.quieter": "Fewer of these",
        "daily.empty.title": "Nothing is exact today",
        "daily.empty.body":
            "What is still in orb is below. Nothing perfects today.",
    },
)

ES = DailyWords(
    locale="es",
    title="Hoy",
    question="¿Qué está pasando de verdad en mi carta hoy?",
    bodies={
        "sun": "el Sol", "moon": "la Luna", "mercury": "Mercurio",
        "venus": "Venus", "mars": "Marte", "jupiter": "Júpiter",
        "saturn": "Saturno", "uranus": "Urano", "neptune": "Neptuno",
        "pluto": "Plutón", "chiron": "Quirón",
    },
    points={
        "sun": "tu Sol", "moon": "tu Luna", "ascendant": "tu Ascendente",
        "midheaven": "tu Medio Cielo", "mercury": "tu Mercurio",
        "venus": "tu Venus", "mars": "tu Marte", "saturn": "tu Saturno",
        "jupiter": "tu Júpiter", "chiron": "tu Quirón",
        "true_node": "tu Nodo Norte", "uranus": "tu Urano",
        "neptune": "tu Neptuno", "pluto": "tu Plutón", "lilith": "tu Lilith",
    },
    # `tu` is a possessive, not an article, so Spanish is the one language here
    # where `a` does not contract and the natural preposition can be kept.
    aspects={
        "conjunction": "en conjunción con", "sextile": "en sextil con",
        "square": "en cuadratura con", "trine": "en trígono con",
        "opposition": "en oposición a",
    },
    transiting="{body} en tránsito",
    line_exact="{contact} — exacto a las {time}",
    line_exact_past="{contact} — exacto a las {time}, ya pasadas",
    line_entering="{contact} — entra en orbe hoy",
    line_quiet="Una semana tranquila. {contact} es lo único que sigue moviéndose.",
    settings={
        "daily.setting.title": "Cada día",
        "daily.setting.off": "Desactivado",
        "daily.setting.occasionally": "De vez en cuando",
        "daily.setting.only_what_matters": "Solo lo que importa",
        "daily.setting.off.detail":
            "Sin notificaciones. Lo de hoy sigue ahí cuando abras la app.",
        "daily.setting.occasionally.detail":
            "Más o menos una vez por semana, cuando algo en tu carta se hace "
            "exacto de verdad.",
        "daily.setting.only_matters.detail":
            "Unas pocas veces al año. Solo los lentos: los tránsitos que duran meses.",
        "daily.setting.hour": "Llega a las",
        "daily.setting.quiet": "Nunca entre las 22:00 y las 08:00, en tu hora.",
        "daily.setting.timezone": "Tu hora",
        "daily.setting.timezone.device": "de tu dispositivo",
        "daily.setting.timezone.birth": "de tus datos de nacimiento",
        "daily.setting.timezone.chosen": "lo elegiste tú",
        "daily.action.turn_off": "Desactivar esto",
        "daily.action.quieter": "Menos de esto",
        "daily.empty.title": "Hoy nada es exacto",
        "daily.empty.body":
            "Abajo está lo que sigue en orbe. Hoy no se hace exacto nada.",
    },
)

DE = DailyWords(
    locale="de",
    title="Heute",
    question="Was passiert heute wirklich in meinem Chart?",
    # Bare nominatives, because `transiting` below is a *prefix*:
    # "Transit-Sonne", "Transit-Mond", exactly as "Transit-Saturn" already
    # was. They used to carry articles — "die Sonne", "der Mond" — which
    # composed to "Transit-die Sonne im Quadrat zu deiner Sonne". The
    # transiting Sun is 23% of all pushes and the Moon is excluded, so that
    # one word was roughly a quarter of every German notification title. Note
    # that this is the *opposite* rule from `points` above, which stores fully
    # inflected phrases: there the aspect governs a case, here nothing does.
    bodies={
        "sun": "Sonne", "moon": "Mond", "mercury": "Merkur",
        "venus": "Venus", "mars": "Mars", "jupiter": "Jupiter",
        "saturn": "Saturn", "uranus": "Uranus", "neptune": "Neptun",
        "pluto": "Pluto", "chiron": "Chiron",
    },
    # Dative throughout: every phrase in `aspects` below governs it. The
    # possessive is inflected for the noun's gender here rather than derived,
    # which is the whole reason this table holds phrases and not nouns.
    points={
        "sun": "deiner Sonne", "moon": "deinem Mond",
        "ascendant": "deinem Aszendenten", "midheaven": "deinem Medium Coeli",
        "mercury": "deinem Merkur", "venus": "deiner Venus",
        "mars": "deinem Mars", "saturn": "deinem Saturn",
        "jupiter": "deinem Jupiter", "chiron": "deinem Chiron",
        "true_node": "deinem Nordknoten", "uranus": "deinem Uranus",
        "neptune": "deinem Neptun", "pluto": "deinem Pluto",
        "lilith": "deiner Lilith",
    },
    aspects={
        "conjunction": "in Konjunktion mit", "sextile": "im Sextil zu",
        "square": "im Quadrat zu", "trine": "im Trigon zu",
        "opposition": "in Opposition zu",
    },
    # "Transit-Saturn", not "Saturn im Transit": the aspect phrases already
    # begin with "im", and "Saturn im Transit im Quadrat zu" stutters.
    transiting="Transit-{body}",
    line_exact="{contact} — exakt um {time}",
    line_exact_past="{contact} — exakt um {time}, bereits vorbei",
    line_entering="{contact} — ab heute im Orbis",
    line_quiet="Eine ruhige Woche. {contact} ist das Einzige, was sich noch bewegt.",
    settings={
        "daily.setting.title": "Das Tägliche",
        "daily.setting.off": "Aus",
        "daily.setting.occasionally": "Gelegentlich",
        "daily.setting.only_what_matters": "Nur was zählt",
        "daily.setting.off.detail":
            "Keine Mitteilungen. Heute ist trotzdem da, wann immer du die App öffnest.",
        "daily.setting.occasionally.detail":
            "Etwa einmal pro Woche, wenn in deinem Chart wirklich etwas exakt wird.",
        "daily.setting.only_matters.detail":
            "Ein paar Mal im Jahr. Nur die langsamen — die Transite, die Monate dauern.",
        "daily.setting.hour": "Kommt um",
        "daily.setting.quiet": "Nie zwischen 22:00 und 08:00, in deiner Zeit.",
        "daily.setting.timezone": "Deine Zeit",
        "daily.setting.timezone.device": "von deinem Gerät",
        "daily.setting.timezone.birth": "aus deinen Geburtsdaten",
        "daily.setting.timezone.chosen": "von dir gewählt",
        "daily.action.turn_off": "Diese abschalten",
        "daily.action.quieter": "Weniger davon",
        "daily.empty.title": "Heute wird nichts exakt",
        "daily.empty.body":
            "Unten steht, was noch im Orbis ist. Heute wird nichts exakt.",
    },
)

IT = DailyWords(
    locale="it",
    title="Oggi",
    question="Che cosa sta succedendo davvero nel mio tema oggi?",
    bodies={
        "sun": "il Sole", "moon": "la Luna", "mercury": "Mercurio",
        "venus": "Venere", "mars": "Marte", "jupiter": "Giove",
        "saturn": "Saturno", "uranus": "Urano", "neptune": "Nettuno",
        "pluto": "Plutone", "chiron": "Chirone",
    },
    points={
        "sun": "il tuo Sole", "moon": "la tua Luna",
        "ascendant": "il tuo Ascendente", "midheaven": "il tuo Medio Cielo",
        "mercury": "il tuo Mercurio", "venus": "la tua Venere",
        "mars": "il tuo Marte", "saturn": "il tuo Saturno",
        "jupiter": "il tuo Giove", "chiron": "il tuo Chirone",
        "true_node": "il tuo Nodo Nord", "uranus": "il tuo Urano",
        "neptune": "il tuo Nettuno", "pluto": "il tuo Plutone",
        "lilith": "la tua Lilith",
    },
    # All five end in "con", including opposition, where "a" would be the more
    # usual preposition — "in opposizione a il tuo Sole" is ungrammatical and
    # "al tuo Sole" would need the server to contract the article.
    aspects={
        "conjunction": "in congiunzione con", "sextile": "in sestile con",
        "square": "in quadratura con", "trine": "in trigono con",
        "opposition": "in opposizione con",
    },
    transiting="{body} in transito",
    line_exact="{contact} — esatto alle {time}",
    line_exact_past="{contact} — esatto alle {time}, ormai passate",
    line_entering="{contact} — entra in orbe oggi",
    line_quiet="Una settimana tranquilla. {contact} è l'unica cosa che si muove ancora.",
    settings={
        "daily.setting.title": "Il quotidiano",
        "daily.setting.off": "Disattivato",
        "daily.setting.occasionally": "Ogni tanto",
        "daily.setting.only_what_matters": "Solo ciò che conta",
        "daily.setting.off.detail":
            "Nessuna notifica. Oggi resta comunque lì, ogni volta che apri l'app.",
        "daily.setting.occasionally.detail":
            "Circa una volta a settimana, quando qualcosa nel tuo tema diventa "
            "davvero esatto.",
        "daily.setting.only_matters.detail":
            "Poche volte all'anno. Solo i lenti — i transiti che durano mesi.",
        "daily.setting.hour": "Arriva alle",
        "daily.setting.quiet": "Mai tra le 22:00 e le 08:00, nella tua ora.",
        "daily.setting.timezone": "La tua ora",
        "daily.setting.timezone.device": "dal tuo dispositivo",
        "daily.setting.timezone.birth": "dai tuoi dati di nascita",
        "daily.setting.timezone.chosen": "l'hai scelto tu",
        "daily.action.turn_off": "Disattiva queste",
        "daily.action.quieter": "Meno di queste",
        "daily.empty.title": "Oggi niente è esatto",
        "daily.empty.body":
            "Sotto c'è ciò che è ancora in orbe. Oggi non si perfeziona nulla.",
    },
)

FR = DailyWords(
    locale="fr",
    title="Aujourd'hui",
    question="Qu'est-ce qui se passe vraiment dans mon thème aujourd'hui ?",
    bodies={
        "sun": "le Soleil", "moon": "la Lune", "mercury": "Mercure",
        "venus": "Vénus", "mars": "Mars", "jupiter": "Jupiter",
        "saturn": "Saturne", "uranus": "Uranus", "neptune": "Neptune",
        "pluto": "Pluton", "chiron": "Chiron",
    },
    points={
        "sun": "ton Soleil", "moon": "ta Lune", "ascendant": "ton Ascendant",
        "midheaven": "ton Milieu du Ciel", "mercury": "ton Mercure",
        "venus": "ta Vénus", "mars": "ton Mars", "saturn": "ton Saturne",
        "jupiter": "ton Jupiter", "chiron": "ton Chiron",
        "true_node": "ton Nœud Nord", "uranus": "ton Uranus",
        "neptune": "ton Neptune", "pluto": "ton Pluton", "lilith": "ta Lilith",
    },
    aspects={
        "conjunction": "en conjonction avec", "sextile": "en sextile à",
        "square": "en carré à", "trine": "en trigone à",
        "opposition": "en opposition à",
    },
    transiting="{body} en transit",
    line_exact="{contact} — exact à {time}",
    line_exact_past="{contact} — exact à {time}, c'est déjà passé",
    line_entering="{contact} — entre en orbe aujourd'hui",
    line_quiet="Une semaine calme. {contact} est la seule chose qui bouge encore.",
    settings={
        "daily.setting.title": "Le quotidien",
        "daily.setting.off": "Désactivé",
        "daily.setting.occasionally": "De temps en temps",
        "daily.setting.only_what_matters": "Seulement l'essentiel",
        "daily.setting.off.detail":
            "Aucune notification. Aujourd'hui reste là, chaque fois que tu ouvres l'app.",
        "daily.setting.occasionally.detail":
            "Environ une fois par semaine, quand quelque chose devient vraiment "
            "exact dans ton thème.",
        "daily.setting.only_matters.detail":
            "Quelques fois par an. Seulement les lents — les transits qui durent "
            "des mois.",
        "daily.setting.hour": "Arrive à",
        "daily.setting.quiet": "Jamais entre 22h00 et 08h00, à ton heure.",
        "daily.setting.timezone": "Ton heure",
        "daily.setting.timezone.device": "depuis ton appareil",
        "daily.setting.timezone.birth": "depuis tes données de naissance",
        "daily.setting.timezone.chosen": "tu l'as choisi",
        "daily.action.turn_off": "Désactiver",
        "daily.action.quieter": "Moins de ça",
        "daily.empty.title": "Rien n'est exact aujourd'hui",
        "daily.empty.body":
            "Ci-dessous, ce qui est encore en orbe. Rien ne devient exact aujourd'hui.",
    },
)

PT_BR = DailyWords(
    locale="pt-BR",
    title="Hoje",
    question="O que está realmente acontecendo no meu mapa hoje?",
    bodies={
        "sun": "o Sol", "moon": "a Lua", "mercury": "Mercúrio",
        "venus": "Vênus", "mars": "Marte", "jupiter": "Júpiter",
        "saturn": "Saturno", "uranus": "Urano", "neptune": "Netuno",
        "pluto": "Plutão", "chiron": "Quíron",
    },
    points={
        "sun": "o seu Sol", "moon": "a sua Lua",
        "ascendant": "o seu Ascendente", "midheaven": "o seu Meio do Céu",
        "mercury": "o seu Mercúrio", "venus": "a sua Vênus",
        "mars": "o seu Marte", "saturn": "o seu Saturno",
        "jupiter": "o seu Júpiter", "chiron": "o seu Quíron",
        "true_node": "o seu Nodo Norte", "uranus": "o seu Urano",
        "neptune": "o seu Netuno", "pluto": "o seu Plutão",
        "lilith": "a sua Lilith",
    },
    # "com" for all five, opposition included, for the Italian reason: "a" plus
    # the article contracts to "ao"/"à" and the server must not be the thing
    # deciding which.
    aspects={
        "conjunction": "em conjunção com", "sextile": "em sextil com",
        "square": "em quadratura com", "trine": "em trígono com",
        "opposition": "em oposição com",
    },
    transiting="{body} em trânsito",
    line_exact="{contact} — exato às {time}",
    line_exact_past="{contact} — exato às {time}, já passadas",
    line_entering="{contact} — entra em orbe hoje",
    line_quiet="Uma semana tranquila. {contact} é a única coisa que ainda se move.",
    settings={
        "daily.setting.title": "O diário",
        "daily.setting.off": "Desativado",
        "daily.setting.occasionally": "De vez em quando",
        "daily.setting.only_what_matters": "Só o que importa",
        "daily.setting.off.detail":
            "Sem notificações. Hoje continua aqui sempre que você abrir o app.",
        "daily.setting.occasionally.detail":
            "Mais ou menos uma vez por semana, quando algo no seu mapa fica "
            "realmente exato.",
        "daily.setting.only_matters.detail":
            "Poucas vezes por ano. Só os lentos — os trânsitos que duram meses.",
        "daily.setting.hour": "Chega às",
        "daily.setting.quiet": "Nunca entre 22:00 e 08:00, no seu horário.",
        "daily.setting.timezone": "Seu horário",
        "daily.setting.timezone.device": "do seu aparelho",
        "daily.setting.timezone.birth": "dos seus dados de nascimento",
        "daily.setting.timezone.chosen": "você escolheu",
        "daily.action.turn_off": "Desativar isto",
        "daily.action.quieter": "Menos disto",
        "daily.empty.title": "Hoje nada está exato",
        "daily.empty.body":
            "Abaixo está o que ainda está em orbe. Hoje nada se torna exato.",
    },
)


RU = DailyWords(
    locale="ru",
    title="Сегодня",
    question="Что на самом деле происходит в моей карте сегодня?",
    # The transiting adjective lives *inside* the noun, because Russian
    # declines it by the body's own gender — Транзитное Солнце, Транзитная
    # Луна, Транзитный Марс. A fixed prefix template is exactly how German
    # shipped "Transit-die Sonne"; here `transiting` is the identity template
    # and the agreement is written once, correctly, per body.
    bodies={
        "sun": "Транзитное Солнце", "moon": "Транзитная Луна",
        "mercury": "Транзитный Меркурий", "venus": "Транзитная Венера",
        "mars": "Транзитный Марс", "jupiter": "Транзитный Юпитер",
        "saturn": "Транзитный Сатурн", "uranus": "Транзитный Уран",
        "neptune": "Транзитный Нептун", "pluto": "Транзитный Плутон",
        "chiron": "Транзитный Хирон",
    },
    # Instrumental case throughout, because every connective below ends in
    # «с». Russian astrologers say both «в квадратуре с Луной» and «в
    # квадрате к Луне»; the table keeps to one government so that fifteen
    # points need one declension each rather than two.
    points={
        "sun": "твоим Солнцем", "moon": "твоей Луной",
        "ascendant": "твоим Асцендентом", "midheaven": "твоей Серединой неба",
        "mercury": "твоим Меркурием", "venus": "твоей Венерой",
        "mars": "твоим Марсом", "saturn": "твоим Сатурном",
        "jupiter": "твоим Юпитером", "chiron": "твоим Хироном",
        "true_node": "твоим Северным узлом", "uranus": "твоим Ураном",
        "neptune": "твоим Нептуном", "pluto": "твоим Плутоном",
        "lilith": "твоей Лилит",
    },
    aspects={
        "conjunction": "в соединении с", "sextile": "в секстиле с",
        "square": "в квадратуре с", "trine": "в трине с",
        "opposition": "в оппозиции с",
    },
    transiting="{body}",
    line_exact="{contact} — точно в {time}",
    # The past marker hangs on the moment, not on the planet, for the same
    # reason the Romance files use an elided plural: «уже позади» declines
    # with nothing and is true of Венера and Марс alike.
    line_exact_past="{contact} — точно в {time}, уже позади",
    line_entering="{contact} — в орбисе с сегодняшнего дня",
    line_quiet="Тихая неделя. {contact} — единственное, что ещё движется.",
    settings={
        "daily.setting.title": "Каждое утро",
        "daily.setting.off": "Выключено",
        "daily.setting.occasionally": "Иногда",
        "daily.setting.only_what_matters": "Только важное",
        "daily.setting.off.detail":
            "Без уведомлений. «Сегодня» всегда на месте, когда ты открываешь "
            "приложение.",
        "daily.setting.occasionally.detail":
            "Примерно раз в неделю, когда что-то в твоей карте действительно "
            "становится точным.",
        "daily.setting.only_matters.detail":
            "Несколько раз в год. Только медленные — транзиты, которые длятся "
            "месяцами.",
        "daily.setting.hour": "Приходит в",
        "daily.setting.quiet": "Никогда между 22:00 и 08:00 по твоему времени.",
        "daily.setting.timezone": "Твоё время",
        "daily.setting.timezone.device": "с твоего устройства",
        "daily.setting.timezone.birth": "из твоих данных рождения",
        # «ты выбираешь сам» is masculine; the noun phrase is nobody's gender.
        "daily.setting.timezone.chosen": "твой выбор",
        "daily.action.turn_off": "Выключить их",
        "daily.action.quieter": "Пореже",
        "daily.empty.title": "Тихий день в твоём небе",
        "daily.empty.body":
            "Что ещё в орбисе — ниже. Сегодня ничто не достигает точной "
            "отметки.",
    },
)

WORDS: dict[str, DailyWords] = {
    "en": EN, "es": ES, "de": DE, "it": IT, "fr": FR, "pt-BR": PT_BR, "ru": RU,
}


def words_for(locale: str | None) -> DailyWords:
    """This reader's vocabulary.

    Through `i18n.resolve` rather than a dictionary lookup, for the reason that
    module's docstring gives at length: the interesting inputs are "de-AT",
    "pt_BR" with an underscore and "PT-br", every one of which is a reader we
    have words for and every one of which lands on English under a plain
    `dict.get`. A notification is the one string in this product that arrives
    without being asked for, and arriving in the wrong language is worse there
    than anywhere else.
    """
    return WORDS[i18n.resolve(locale)]
