"""The four sentences the server writes to a reader itself, in all seven.

Almost everything a reader sees is prose a model generated in their language,
or a chart, or a string from an app bundle. These four are neither: they are
what the chat route says when there is no reply to give — the validator refused
what came back, the model provider is down, the day's questions are spent, the
month's money is. Every one of them replaces something that was `str(exc)`.

**What `str(exc)` actually put on a person's screen.** A Russian speaker asked
three times about her Moon and got, three times:

    could not produce an answer that only cites real factors — refusing rather
    than replying with something invented

That is a sentence about our validator, in a language she was not writing, and
it blames nothing, offers nothing and does not acknowledge that a question was
lost. The provider path was worse — it forwarded another company's error object
verbatim, including their request id, to somebody who had just typed *"honestly
i am not okay tonight"* (`docs/CONVERSATION.md` §16, §17).

**Why here and not in the app bundles.** The push strings are keys the
operating system resolves in the device's language, because a notification is
delivered to a phone rather than answered to a request. An HTTP error body is
the reply to a request that carried `locale`, so the server already knows the
language and there is no reason to make three clients each carry the same four
sentences — and no reason for a fourth consumer (a browser, a script, a
support tool) to get engineering prose because it is not one of the three.

The clients still classify on the machine code and may prefer their own copy;
both of them do today, which is correct. What this table guarantees is that the
`message` field is never worse than the client's own sentence, and is never
about our internals.

**The register is hers.** First person, no apology theatre, and each one says
what can still be done — because the measured complaint about the 429 was not
that it arrived but that it named only what the reader could not have. The
eight systems are computed free for everybody, for ever, and that is the true
sentence to end on when the questions run out.
"""

from __future__ import annotations

from . import resolve

#: Refused: the validator could not accept anything the model produced.
REFUSED: dict[str, str] = {
    "en": "I could not answer that without saying something I cannot show you "
          "in your chart, so I would rather not answer it at all. Ask me again "
          "in different words and I will try from another angle.",
    "es": "No pude responder a eso sin decir algo que no puedo mostrarte en tu "
          "carta, así que prefiero no responder. Pregúntamelo con otras "
          "palabras y lo intentaré desde otro ángulo.",
    "de": "Ich konnte das nicht beantworten, ohne etwas zu sagen, das ich dir "
          "in deinem Chart nicht zeigen kann — dann sage ich lieber nichts. "
          "Frag mich noch einmal mit anderen Worten, ich versuche es anders.",
    "it": "Non sono riuscita a rispondere senza dire qualcosa che non posso "
          "mostrarti nel tuo tema, e allora preferisco non rispondere. "
          "Chiedimelo con altre parole e ci proverò da un'altra angolazione.",
    "fr": "Je n'ai pas pu répondre sans dire quelque chose que je ne peux pas "
          "te montrer dans ton thème, alors je préfère ne rien dire. "
          "Redemande-le-moi autrement et j'essaierai sous un autre angle.",
    "pt-BR": "Não consegui responder sem dizer algo que não posso te mostrar no "
             "seu mapa, então prefiro não responder. Me pergunte de outro jeito "
             "e eu tento por outro caminho.",
    # «Не смогла» — Alma's voice is feminine in Russian, as in Italian
    # («riuscita») and French; the gender rule protects the *reader*, never
    # the speaker.
    "ru": "Я не смогла ответить на это, не сказав того, чего не могу показать "
          "в твоей карте, — тогда лучше промолчать. Спроси меня другими "
          "словами, и я зайду с другой стороны.",
}

#: The model provider did not answer. Never their words, never their request id.
UNAVAILABLE: dict[str, str] = {
    "en": "I could not reach the part of me that writes, just now. Your question "
          "was not lost — ask it again in a moment.",
    "es": "Ahora mismo no pude llegar a la parte de mí que escribe. Tu pregunta "
          "no se perdió: vuelve a hacérmela en un momento.",
    "de": "Ich komme gerade nicht an den Teil von mir heran, der schreibt. "
          "Deine Frage ist nicht verloren — stell sie gleich noch einmal.",
    "it": "In questo momento non riesco a raggiungere la parte di me che scrive. "
          "La tua domanda non è andata persa: rifammela tra un momento.",
    "fr": "Je n'arrive pas à joindre, à l'instant, la partie de moi qui écrit. "
          "Ta question n'est pas perdue — repose-la dans un moment.",
    "pt-BR": "Agora não consegui alcançar a parte de mim que escreve. Sua "
             "pergunta não se perdeu — me pergunte de novo daqui a pouco.",
    "ru": "Прямо сейчас я не дотянулась до той части себя, которая пишет. "
          "Твой вопрос не потерялся — задай его ещё раз через минуту.",
}

#: The free or purchased questions are spent. There is no daily refill any
#: more — the sentence points at the plan and ends on what stays free.
LIMIT_DAY: dict[str, str] = {
    "en": 'That was the last of your questions for now — the plan is what carries our conversation on. Everything your chart is made of stays open either way: all eight systems, calculated in full.',
    "es": 'Esa era la última pregunta por ahora — el plan es lo que continúa nuestra conversación. Todo aquello de lo que está hecha tu carta sigue abierto igualmente: los ocho sistemas, calculados por completo.',
    "de": 'Das war vorerst die letzte Frage — der Plan ist es, der unser Gespräch weiterträgt. Alles, woraus dein Chart besteht, bleibt so oder so offen: alle acht Systeme, vollständig berechnet.',
    "it": "Quella era l'ultima domanda per ora — è il piano a portare avanti la nostra conversazione. Tutto ciò di cui è fatto il tuo tema resta comunque aperto: tutti e otto i sistemi, calcolati per intero.",
    "fr": "C'était la dernière question pour l'instant — c'est l'abonnement qui porte notre conversation. Tout ce dont ton thème est fait reste ouvert quoi qu'il arrive : les huit systèmes, calculés en entier.",
    "pt-BR": 'Essa foi a última pergunta por enquanto — é o plano que leva nossa conversa adiante. Tudo de que seu mapa é feito continua aberto de qualquer jeito: os oito sistemas, calculados por inteiro.',
    "ru": 'Это был последний вопрос. Дальше наш разговор — часть плана. Всё, из чего состоит твоя карта, в любом случае остаётся открытым: все восемь систем, рассчитанных полностью.',
}

#: The month's questions are spent. Same sentence, a different clock.
LIMIT_MONTH: dict[str, str] = {
    "en": "That is your {limit} questions this month. They come back on the "
          "first. Everything your chart is made of stays open in the meantime — "
          "all eight systems, calculated in full.",
    "es": "Esas son tus {limit} preguntas de este mes. Vuelven el día uno. "
          "Mientras tanto, todo aquello de lo que está hecha tu carta sigue "
          "abierto: los ocho sistemas, calculados por completo.",
    "de": "Das waren deine {limit} Fragen in diesem Monat. Am Ersten sind sie "
          "wieder da. Alles, woraus dein Chart besteht, bleibt derweil offen — "
          "alle acht Systeme, vollständig berechnet.",
    "it": "Queste erano le tue {limit} domande di questo mese. Tornano il primo. "
          "Nel frattempo resta aperto tutto ciò di cui è fatto il tuo tema: "
          "tutti e otto i sistemi, calcolati per intero.",
    "fr": "Ce sont tes {limit} questions de ce mois-ci. Elles reviennent le "
          "premier. Entre-temps, tout ce dont ton thème est fait reste ouvert — "
          "les huit systèmes, calculés en entier.",
    "pt-BR": "Essas foram suas {limit} perguntas deste mês. Elas voltam no dia "
             "primeiro. Enquanto isso, tudo de que seu mapa é feito continua "
             "aberto — os oito sistemas, calculados por inteiro.",
    "ru": "Это твои {limit} вопросов в этом месяце. Первого числа они "
          "вернутся. Всё, из чего состоит твоя карта, тем временем остаётся "
          "открытым — все восемь систем, рассчитанных полностью.",
}

#: A partner past the ladder's rung. Ends on what opens more, like the rest.
PARTNER_LIMIT: dict[str, str] = {
    "en": "One saved comparison comes free. The compatibility door holds two, and the plan holds as many people as your life does.",
    "es": "Una comparación guardada es gratis. La puerta de compatibilidad guarda dos, y el plan, tantas personas como tu vida.",
    "de": "Ein gespeicherter Vergleich ist frei. Die Partnerschafts-Tür hält zwei, der Plan so viele Menschen wie dein Leben.",
    "it": "Un confronto salvato è gratis. La porta dell'affinità ne tiene due, il piano tante persone quante ne ha la tua vita.",
    "fr": "Une comparaison enregistrée est offerte. La porte de compatibilité en garde deux, l'abonnement autant de personnes que ta vie.",
    "pt-BR": "Uma comparação salva é grátis. A porta da compatibilidade guarda duas, e o plano, quantas pessoas a sua vida tiver.",
    "ru": "Одно сохранённое сравнение — бесплатно. Дверь совместимости вмещает двоих, а подписка — столько людей, сколько их в твоей жизни.",
}

#: Every table in this module, by the machine code the clients classify on.
#: Named so the test that checks all six languages are present can iterate
#: rather than list — a table added without its translations is the failure.
BY_ERROR: dict[str, dict[str, str]] = {
    "answer_refused": REFUSED,
    "ai_unavailable": UNAVAILABLE,
    "question_limit.day": LIMIT_DAY,
    "question_limit.month": LIMIT_MONTH,
    "partner_limit": PARTNER_LIMIT,
}


def reply(error: str, locale: str | None = None, **arguments: object) -> str:
    """The sentence for this failure, in this reader's language.

    `resolve` rather than a plain lookup, for the same reason every other
    locale in this package goes through it: `de-AT` is a real tag from a real
    phone, and a reader whose whole interface is German should not meet English
    on the one screen where something has gone wrong.
    """
    table = BY_ERROR[error]
    text = table[resolve(locale)]
    return text.format(**arguments) if arguments else text
