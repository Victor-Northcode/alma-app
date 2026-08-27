"""The sentences the server writes to a reader itself, in all seven.

Almost everything a reader sees is prose a model generated in their language,
or a chart, or a string from an app bundle. These are neither: they are what
the chat route says when there is no reply to give — the validator refused what
came back, the model provider is down, the day's questions are spent, the
month's money is. Most of them replace something that was `str(exc)`.

**Two of them are not failures at all**, and they arrived with the legal
review. `WITHHELD` is what stands in a thread where the answer crossed a line
the product does not cross; `CRISIS` is what stands where a reader said
something that must never be answered with astrology. Both are delivered as
ordinary turns of hers rather than as HTTP errors, for the reason spelled out
at each: a person who wrote either of those messages should get a sentence in
the conversation, not an error screen where the conversation was.

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
          "in deinem Horoskop nicht zeigen kann — dann sage ich lieber nichts. "
          "Frag mich noch einmal mit anderen Worten, ich versuche es anders.",
    "it": "Non sono riuscita a rispondere senza dire qualcosa che non posso "
          "mostrarti nel tuo tema, e allora preferisco non rispondere. "
          "Chiedimelo con altre parole e ci proverò da un'altra angolazione.",
    "fr": "Je n’ai pas pu répondre sans dire quelque chose que je ne peux pas "
          "te montrer dans ton thème, alors je préfère ne rien dire. "
          "Redemande-le-moi autrement et j’essaierai sous un autre angle.",
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
    "es": "Ahora mismo no consigo llegar a la parte de mí que escribe. Tu "
          "pregunta no se perdió: vuelve a hacérmela en un momento.",
    "de": "Ich komme gerade nicht an den Teil von mir heran, der schreibt. "
          "Deine Frage ist nicht verloren — stell sie gleich noch einmal.",
    "it": "In questo momento non riesco a raggiungere la parte di me che scrive. "
          "La tua domanda non è andata persa: rifammela tra un momento.",
    "fr": "En ce moment, je n’arrive pas à joindre la partie de moi qui écrit. "
          "Ta question n’est pas perdue — repose-la dans un instant.",
    "pt-BR": "Não consegui chegar agora na parte de mim que escreve. Sua "
             "pergunta não se perdeu — me pergunte de novo daqui a pouco.",
    "ru": "Прямо сейчас я не дотянулась до той части себя, которая пишет. "
          "Твой вопрос не потерялся — задай его ещё раз через минуту.",
}

#: The free or purchased questions are spent. There is no daily refill any
#: more — the sentence points at the plan and ends on what stays free.
LIMIT_DAY: dict[str, str] = {
    "en": 'That was the last of your questions for now — the plan is what carries our conversation on. Everything your chart is made of stays open either way: all eight systems, calculated in full.',
    "es": 'Esa era la última pregunta por ahora — el plan es lo que continúa nuestra conversación. Todo aquello de lo que está hecha tu carta sigue abierto igualmente: los ocho sistemas, calculados por completo.',
    "de": 'Das war vorerst deine letzte Frage — weiter geht unser Gespräch im Abo. Alles, woraus dein Horoskop besteht, bleibt so oder so offen: alle acht Systeme, vollständig berechnet.',
    "it": "Quella era l'ultima domanda per ora — è il piano a portare avanti la nostra conversazione. Tutto ciò di cui è fatto il tuo tema resta comunque aperto: tutti e otto i sistemi, calcolati per intero.",
    "fr": "C’était la dernière question pour l’instant — c’est l’abonnement qui porte notre conversation. Tout ce dont ton thème est fait reste ouvert quoi qu’il arrive : les huit systèmes, calculés en entier.",
    "pt-BR": 'Essa foi a última pergunta por enquanto — é o plano que leva nossa conversa adiante. Tudo o que forma o seu mapa continua aberto de qualquer jeito: os oito sistemas, calculados por inteiro.',
    "ru": 'Это был последний вопрос. Дальше наш разговор — часть плана. Всё, из чего состоит твоя карта, в любом случае остаётся открытым: все восемь систем, рассчитанные полностью.',
}

#: The month's questions are spent. Same sentence, a different clock.
LIMIT_MONTH: dict[str, str] = {
    "en": "Those were your {limit} questions this month. They come back on the "
          "first. Everything your chart is made of stays open in the meantime — "
          "all eight systems, calculated in full.",
    "es": "Esas son tus {limit} preguntas de este mes. Vuelven el día uno. "
          "Mientras tanto, todo aquello de lo que está hecha tu carta sigue "
          "abierto: los ocho sistemas, calculados por completo.",
    "de": "Das waren deine {limit} Fragen in diesem Monat. Am Ersten sind sie "
          "wieder da. Alles, woraus dein Horoskop besteht, bleibt derweil offen — "
          "alle acht Systeme, vollständig berechnet.",
    "it": "Queste erano le tue {limit} domande di questo mese. Tornano il primo. "
          "Nel frattempo resta aperto tutto ciò di cui è fatto il tuo tema: "
          "tutti e otto i sistemi, calcolati per intero.",
    "fr": "Ce sont tes {limit} questions de ce mois-ci. Elles reviennent le "
          "premier. Entre-temps, tout ce dont ton thème est fait reste ouvert — "
          "les huit systèmes, calculés en entier.",
    "pt-BR": "Essas foram suas {limit} perguntas deste mês. Elas voltam no dia "
             "primeiro. Enquanto isso, tudo o que forma o seu mapa continua "
             "aberto — os oito sistemas, calculados por inteiro.",
    "ru": "Это были все твои {limit} вопросов в этом месяце. Первого числа "
          "они вернутся. Всё, из чего состоит твоя карта, тем временем "
          "остаётся открытым — все восемь систем, рассчитанные полностью.",
}

#: The week's questions are spent. Same sentence again, a third clock.
#:
#: **Сегодня до неё не доходит ни один читатель, и написана она поэтому.**
#: Недельная подписка снята с продажи, `entitlements.has_kind(..., "weekly")`
#: всегда False, и порция по недельному сроку живёт в `_chat_gate` только
#: потому, что ТЗ §8 оставляет неделю как возможный A/B. Ключ фразы там
#: собирается из периода порции — `question_limit.{period}`, — а `reply()`
#: индексирует таблицу, а не `.get`-ает её. То есть в первый же день
#: эксперимента первый подписчик, упёршийся в свою десятку, получил бы
#: `KeyError` и 500 вместо переведённого 429 — на том самом экране, который
#: этот эксперимент и продаёт. Фраза дешевле, чем разбор такого дня.
LIMIT_WEEK: dict[str, str] = {
    "en": "Those were your {limit} questions this week. They come back when the "
          "week does. Everything your chart is made of stays open in the "
          "meantime — all eight systems, calculated in full.",
    "es": "Esas son tus {limit} preguntas de esta semana. Vuelven cuando vuelve "
          "la semana. Mientras tanto, todo aquello de lo que está hecha tu "
          "carta sigue abierto: los ocho sistemas, calculados por completo.",
    "de": "Das waren deine {limit} Fragen in dieser Woche. Sie kommen mit der "
          "neuen Woche zurück. Alles, woraus dein Horoskop besteht, bleibt "
          "derweil offen — alle acht Systeme, vollständig berechnet.",
    "it": "Queste erano le tue {limit} domande di questa settimana. Tornano "
          "quando torna la settimana. Nel frattempo resta aperto tutto ciò di "
          "cui è fatto il tuo tema: tutti e otto i sistemi, calcolati per "
          "intero.",
    "fr": "Ce sont tes {limit} questions de cette semaine. Elles reviennent "
          "quand la semaine revient. Entre-temps, tout ce dont ton thème est "
          "fait reste ouvert — les huit systèmes, calculés en entier.",
    "pt-BR": "Essas foram suas {limit} perguntas desta semana. Elas voltam "
             "quando a semana volta. Enquanto isso, tudo o que forma o seu "
             "mapa continua aberto — os oito sistemas, calculados por inteiro.",
    "ru": "Это были все твои {limit} вопросов на этой неделе. Они вернутся "
          "вместе с новой неделей. Всё, из чего состоит твоя карта, тем "
          "временем остаётся открытым — все восемь систем, рассчитанные "
          "полностью.",
}

#: Бандл покупки кончился. Единственная из четырёх стен, за которой не «когда-
#: нибудь», а «никогда»: дверь покупается один раз, и порция вопросов при ней
#: конечна — иначе это подписка, отданная за один платёж (см. `_bundle`).
#: Поэтому здесь нет ни завтра, ни первого числа; здесь есть план.
#:
#: **Тоже почти недостижима, и «почти» тут значащее.** Порция бандла
#: выбирается в `_chat_gate` только пока `asked < limit`, так что обычный
#: запрос до этой фразы не доходит. Но `asked` читается там дважды — до выбора
#: порции и после, — и между двумя чтениями соседний запрос того же человека
#: успевает списать последний вопрос. Вероятность мала, цена промаха ключа
#: прежняя: 500 вместо 429, и именно у того, кто нам заплатил.
LIMIT_ONCE: dict[str, str] = {
    "en": "Those were the {limit} questions your purchase included. They do not "
          "come back — the plan is what carries a conversation on. Everything "
          "your chart is made of stays open either way: all eight systems, "
          "calculated in full.",
    "es": "Esas son las {limit} preguntas que incluía tu compra. No vuelven: el "
          "plan es lo que continúa la conversación. Todo aquello de lo que está "
          "hecha tu carta sigue abierto igualmente: los ocho sistemas, "
          "calculados por completo.",
    "de": "Das waren die {limit} Fragen, die dein Kauf enthielt. Sie kommen "
          "nicht wieder — weiter geht ein Gespräch nur im Abo. Alles, woraus "
          "dein Horoskop besteht, bleibt so oder so offen: alle acht "
          "Systeme, vollständig berechnet.",
    "it": "Queste erano le {limit} domande incluse nel tuo acquisto. Non "
          "tornano: è il piano a portare avanti una conversazione. Tutto ciò di "
          "cui è fatto il tuo tema resta comunque aperto: tutti e otto i "
          "sistemi, calcolati per intero.",
    "fr": "Ce sont les {limit} questions que ton achat comprenait. Elles ne "
          "reviennent pas — c’est l’abonnement qui porte une conversation. Tout "
          "ce dont ton thème est fait reste ouvert de toute façon — les huit "
          "systèmes, calculés en entier.",
    "pt-BR": "Essas foram as {limit} perguntas que sua compra incluía. Elas não "
             "voltam — é o plano que leva uma conversa adiante. Tudo o que forma "
             "o seu mapa continua aberto de qualquer jeito: os oito sistemas, "
             "calculados por inteiro.",
    "ru": "Это те {limit} вопросов, что включала покупка. Они не вернутся: "
          "дальше наш разговор — часть плана. Всё, из чего состоит твоя карта, "
          "в любом случае остаётся открытым: все восемь систем, рассчитанные "
          "полностью.",
}

#: A partner past the ladder's rung. Ends on what opens more, like the rest.
#:
#: **Говорит про сохранённого человека, а не про «бесплатное сравнение».**
#: Стояло «One saved comparison comes free», и после решения владельца
#: 19.08.2026 («мы не даем бесплатно пару никакую все за деньги можно писать
#: только имя») это читалось обещанием бесплатного отчёта о паре, которого нет.
#: Бесплатно ровно то, что здесь и считается, — место под человека, с которым
#: сравнивают; написанные главы платны на любой ступени лестницы.
PARTNER_LIMIT: dict[str, str] = {
    "en": "A free account saves one person to compare with. A one-time compatibility purchase saves two, and the plan saves as many as your life has.",
    "es": "Una cuenta gratuita guarda una persona para comparar. La compra única de compatibilidad guarda dos, y el plan, tantas personas como haya en tu vida.",
    "de": "Ein kostenloses Konto speichert eine Person zum Vergleichen. Ein einmaliger Partnerschaftskauf speichert zwei, das Abo so viele, wie in deinem Leben vorkommen.",
    "it": "Un account gratuito conserva una persona con cui confrontarti. Un acquisto una tantum dell'affinità ne tiene due, il piano tutte quelle che ci sono nella tua vita.",
    "fr": "Un compte gratuit enregistre une personne à comparer. Un achat unique de compatibilité en garde deux, et l’abonnement autant de personnes qu’il y en a dans ta vie.",
    "pt-BR": "Uma conta grátis salva uma pessoa para comparar. A compra avulsa de compatibilidade guarda duas, e o plano guarda quantas pessoas a sua vida tiver.",
    "ru": "Бесплатный аккаунт хранит одного человека для сравнения. Разовая покупка совместимости — двоих, а подписка — столько людей, сколько их в твоей жизни.",
}

#: Совместимость просят без второго человека.
#:
#: **Это единственное сообщение, которое читатель видел дословно из кода.**
#: На экране главы стояло «a compatibility reading is about two people — send
#: `partner_profile_id`» — имя поля API, по-английски, посреди русской
#: страницы, снято владельцем на кадре. Оно писалось для того, кто зовёт
#: эндпоинт руками, и туда же вернулось: подробность остаётся кодом ошибки
#: `partner_required`, а человеку говорится, чего не хватает и что сделать.
PARTNER_REQUIRED: dict[str, str] = {
    "en": "A compatibility reading is about two people. Add someone, and I will read you together.",
    "es": "La compatibilidad trata de dos personas. Añade a alguien y leeré a los dos juntos.",
    "de": "Eine Partnerschaftsdeutung braucht zwei. Füge jemanden hinzu, und ich lese euch zusammen.",
    "it": "L'affinità riguarda due persone. Aggiungi qualcuno e vi leggerò insieme.",
    "fr": "La compatibilité parle de deux personnes. Ajoute quelqu’un, et je vous lirai ensemble.",
    "pt-BR": "A compatibilidade é sobre duas pessoas. Adicione alguém e vou ler vocês juntos.",
    "ru": "Совместимость — это про двоих. Добавь человека, и я прочту вас вместе.",
}

#: Every table in this module, by the machine code the clients classify on.
#: Named so the test that checks all six languages are present can iterate
#: rather than list — a table added without its translations is the failure.
#: Расходы этого аккаунта упёрлись в потолок.
#:
#: **Наружу не уходит ни одна цифра.** Раньше клиент показывал текст самого
#: исключения — «this account has cost $1.3612 so far this month and this call
#: would add about $0.0217, against a $1.10 ceiling for the free tier», —
#: по-английски и с нашей себестоимостью. Читателю это не объясняет ничего, а
#: конкуренту объясняет слишком много. Подробности остаются в логе, где им и
#: место.
BUDGET: dict[str, str] = {
    "en": "Alma has written a lot for you today. The next piece opens tomorrow "
          "— or right away with a plan.",
    "es": "Alma escribió mucho para ti hoy. Lo siguiente se abre mañana, o "
          "ahora mismo con un plan.",
    "de": "Alma hat heute viel für dich geschrieben. Das Nächste öffnet sich "
          "morgen — oder sofort mit einem Abo.",
    "it": "Alma ha scritto molto per te oggi. Il resto si apre domani, o "
          "subito con un piano.",
    "fr": "Alma a beaucoup écrit pour toi aujourd’hui. La suite s’ouvre "
          "demain — ou tout de suite avec un abonnement.",
    "pt-BR": "A Alma escreveu muito para você hoje. A próxima parte abre "
             "amanhã — ou agora mesmo com um plano.",
    "ru": "Alma сегодня много для тебя написала. Следующее откроется завтра — "
          "или прямо сейчас, с подпиской.",
}

#: Человек написал, что может себе навредить.
#:
#: **Единственная строка в этой таблице, которая не заменяет ошибку.** Всё
#: остальное здесь — то, что говорится вместо ответа, которого не получилось;
#: эта говорится вместо ответа, которого не должно быть. Кризисное сообщение не
#: доходит до модели вовсе (`validator.crisis` → `conversation.answer`), и
#: причина ровно та: ответ на «я не хочу жить» приходит один раз. Модель, у
#: которой в системном промте лежит правило про заботу, выполняет его
#: по-разному от прогона к прогону, а разброс здесь недопустим — это не стиль.
#:
#: **Ни одного номера телефона.** Продукт продаётся во всех сторах мира, и
#: 988 — это Америка, 112 — Европа, а неверный номер под этой фразой хуже, чем
#: отсутствие номера. Названо то, что есть везде: экстренная служба своей
#: страны, кризисная линия, один живой человек рядом.
#:
#: Русская строка обходит прошедшее время в обращении к читателю («написал/
#: написала») по тому же правилу, по которому его обходят главы: род читателя
#: неизвестен, и угадывать его в этом сообщении — последнее, что стоит делать.
CRISIS: dict[str, str] = {
    "en": "I am going to stop here, because this matters more than anything I "
          "could read in a chart. Please talk to someone who can be with you "
          "right now — the emergency number where you are, a crisis line, or "
          "one person you trust. I will still be here afterwards.",
    "es": "Me detengo aquí, porque esto importa más que cualquier cosa que yo "
          "pueda leer en una carta. Por favor, habla con alguien que pueda "
          "acompañarte ahora mismo: el número de emergencias de tu país, una "
          "línea de crisis, o una persona en quien confíes. Yo seguiré aquí "
          "después.",
    "de": "Ich höre hier auf, denn das wiegt schwerer als alles, was ich in "
          "einem Horoskop lesen könnte. Bitte sprich mit jemandem, der jetzt bei "
          "dir sein kann — dem Notruf in deinem Land, einer Krisenhotline oder "
          "einem Menschen, dem du vertraust. Ich bin danach noch da.",
    "it": "Mi fermo qui, perché questo conta più di qualsiasi cosa io possa "
          "leggere in un tema. Per favore parla con qualcuno che possa starti "
          "vicino adesso: il numero di emergenza del tuo paese, una linea di "
          "ascolto, o una persona di cui ti fidi. Io resto qui per dopo.",
    "fr": "Je m’arrête ici, parce que cela compte plus que tout ce que je "
          "pourrais lire dans un thème. S’il te plaît, parle à quelqu’un qui "
          "peut être auprès de toi maintenant : le numéro d’urgence de ton "
          "pays, une ligne d’écoute, ou une personne en qui tu as confiance. "
          "Je serai encore là ensuite.",
    "pt-BR": "Eu paro por aqui, porque isso pesa mais do que qualquer coisa "
             "que eu possa ler num mapa. Por favor, fale com alguém que possa "
             "estar com você agora: o número de emergência do seu país, uma "
             "linha de apoio, ou uma pessoa em quem você confia. Eu continuo "
             "aqui depois.",
    "ru": "Я остановлюсь здесь: это важнее всего, что я могу прочитать в "
          "карте. Пожалуйста, поговори с тем, кто может быть рядом прямо "
          "сейчас, — со службой экстренной помощи в твоей стране, с кризисной "
          "линией или с одним человеком, которому ты доверяешь. Я никуда не "
          "денусь и буду здесь потом.",
}

#: Ответ пересёк юридическую границу и потому не отдан.
#:
#: **Не отказ и не ошибка — подмена.** Раньше ответ, трижды нарушивший правило,
#: уходил в 422: читатель видел экран ошибки, а в ленте не оставалось ничего.
#: Теперь на его месте стоит эта фраза, обычной репликой Alma: она сохраняется
#: в беседе, перечитывается вместе с ней и не стоит читателю вопроса. Сам
#: нарушивший текст не уходит никуда и никогда — граница держится ответом.
#:
#: Названа причина, а не механика: решение принадлежит человеку и тому, кто в
#: нём разбирается. И названо, что можно спросить вместо — потому что отказ без
#: второй половины в этом продукте считается браком с тех пор, как это
#: посчитали.
WITHHELD: dict[str, str] = {
    "en": "I started that answer and stopped it. It was going somewhere a "
          "chart has no business going — towards a decision that belongs to "
          "you and to someone qualified, not to me. Ask me what the pattern "
          "looks like, and that part I will read you.",
    "es": "Empecé esa respuesta y la detuve. Iba hacia donde una carta no "
          "tiene nada que hacer: hacia una decisión que es tuya y de alguien "
          "calificado, no mía. Pregúntame cómo es el patrón y esa parte sí "
          "te la leo.",
    "de": "Ich habe diese Antwort begonnen und wieder abgebrochen. Sie ging "
          "dorthin, wo ein Horoskop nichts zu suchen hat — zu einer Entscheidung, "
          "die dir und einer Fachperson gehört, nicht mir. Frag mich, wie das "
          "Muster aussieht — diesen Teil lese ich für dich.",
    "it": "Ho cominciato questa risposta e l'ho fermata. Andava dove un tema "
          "non deve andare: verso una decisione che è tua e di chi se ne "
          "intende, non mia. Chiedimi che schema c'è, e quella parte te la "
          "leggo.",
    "fr": "J’ai commencé cette réponse et je l’ai arrêtée. Elle allait là où "
          "un thème n’a rien à faire : vers une décision qui t’appartient, à "
          "toi et à quelqu’un de qualifié, pas à moi. Demande-moi à quoi "
          "ressemble le motif, cette partie-là je te la lis.",
    "pt-BR": "Comecei essa resposta e a interrompi. Ela ia para onde um mapa "
             "não tem o que fazer: para uma decisão que é sua e de alguém "
             "qualificado, não minha. Me pergunte qual é o padrão, e essa "
             "parte eu leio para você.",
    "ru": "Я начала этот ответ и остановила его. Он уходил туда, куда карте "
          "ходить незачем, — к решению, которое принадлежит тебе и тому, кто в "
          "нём разбирается, а не мне. Спроси меня, как это выглядит в карте, — "
          "эту часть я прочитаю.",
}

#: Рождение, за которое уже заплатили, не переписывается.
#:
#: Грант проверки пары назван человеком, а не его рождением, поэтому правка
#: даты превращала бы одну покупку в бесконечные отчёты — и каждый стоил бы
#: полной генерации. Отказ говорит именно то, что произошло, и предлагает
#: единственный честный выход: другой человек — другая проверка.
BIRTH_LOCKED: dict[str, str] = {
    "en": "This person's birth data is part of a report you have already paid "
          "for, so it stays as it is. For someone else, add them as a new "
          "person — their own check, their own report.",
    "ru": "Данные рождения этого человека — часть разбора, за который уже "
          "заплачено, и остаются как есть. Если речь о другом человеке, "
          "добавь его отдельно: своя проверка, свой разбор.",
    "de": "Die Geburtsdaten dieser Person gehören zu einer Deutung, die du "
          "bereits bezahlt hast, und bleiben, wie sie sind. Für jemand anderen "
          "lege eine neue Person an — eigener Vergleich, eigene Deutung.",
    "fr": "Les données de naissance de cette personne font partie d’une lecture "
          "que tu as déjà payée : elles restent telles quelles. Pour quelqu’un "
          "d’autre, ajoute une nouvelle personne — sa propre analyse, sa propre "
          "lecture.",
    "es": "Los datos de nacimiento de esta persona forman parte de una lectura "
          "que ya pagaste, así que quedan como están. Para otra persona, añade "
          "a alguien nuevo: su propia comparación, su propia lectura.",
    "it": "I dati di nascita di questa persona fanno parte di una lettura che "
          "hai già pagato e restano come sono. Per qualcun altro, aggiungi una "
          "persona nuova: la sua analisi, la sua lettura.",
    "pt-BR": "Os dados de nascimento desta pessoa fazem parte de uma leitura "
             "que você já pagou e ficam como estão. Para outra pessoa, adicione "
             "uma pessoa nova: a análise dela, a leitura dela.",
}

BY_ERROR: dict[str, dict[str, str]] = {
    "answer_refused": REFUSED,
    "answer_withheld": WITHHELD,
    "crisis": CRISIS,
    "ai_unavailable": UNAVAILABLE,
    "question_limit.day": LIMIT_DAY,
    "question_limit.month": LIMIT_MONTH,
    "question_limit.week": LIMIT_WEEK,
    "question_limit.once": LIMIT_ONCE,
    "partner_limit": PARTNER_LIMIT,
    "birth_locked_by_purchase": BIRTH_LOCKED,
    "partner_required": PARTNER_REQUIRED,
    "budget_exceeded": BUDGET,
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
