#!/usr/bin/env python3
"""Write Alma/Resources/Screens.xcstrings.

The strings for the six screens that were placeholders until now — the Alma
tab, one saved conversation, sign-in, the legal reader, the people list and
add-a-person — in six languages, generated rather than typed.

A fifth table rather than more keys in `Cabinet.xcstrings`: a String Catalog is
one JSON document with one `strings` object, so two people adding keys are
editing the same lines of the same file, and `LocalizedStringResource` takes a
table name, so a second file costs one parameter and removes the conflict
entirely. The linker merges them.

Wording that already exists in `src/lib/i18n/` is reused verbatim rather than
re-translated. Everything else is new to the app — the web has no chat composer,
no restore, and no in-app legal reader — and is written here in all six
languages next to each other, which is the only way to notice that one of them
says something different.

    $ python3 tools/gen_screens_strings.py
"""

import json
import os

L = ["en", "es", "de", "it", "fr", "pt-BR"]
OUT = os.path.join(
    os.path.dirname(__file__), "..", "Alma", "Resources", "Screens.xcstrings"
)

T = {}


def add(key, comment, values):
    assert key not in T, key
    T[key] = (comment, values)


def lit(en, es, de, it, fr, pt_BR):
    return {"en": en, "es": es, "de": de, "it": it, "fr": fr, "pt-BR": pt_BR}


# ── the Alma tab ──────────────────────────────────────────────────────────

add("scr.chat.opening", "Alma's first line on an empty conversation.", lit(
    en="Ask me anything about your chart. I answer from what is in it, and I say so when the answer is not.",
    es="Pregúntame lo que quieras sobre tu carta. Respondo desde lo que hay en ella, y lo digo cuando la respuesta no está ahí.",
    de="Frag mich alles über dein Horoskop. Ich antworte aus dem, was darin steht — und sage es, wenn die Antwort nicht darin steht.",
    it="Chiedimi qualsiasi cosa sul tuo tema. Rispondo da ciò che vi è scritto, e lo dico quando la risposta non c'è.",
    fr="Demande-moi ce que tu veux sur ton thème. Je réponds à partir de ce qui s'y trouve, et je le dis quand la réponse n'y est pas.",
    pt_BR="Pergunte o que quiser sobre seu mapa. Respondo a partir do que está nele, e digo quando a resposta não está."))

add("scr.chat.noChart", "The same, before any birth data exists.", lit(
    en="I can talk without your chart, but I would only be guessing. Give me your birth data and I can read you instead.",
    es="Puedo hablar sin tu carta, pero solo estaría adivinando. Dame tus datos de nacimiento y podré leerte de verdad.",
    de="Ich kann ohne dein Horoskop reden, aber ich würde nur raten. Gib mir deine Geburtsdaten, dann kann ich dich lesen.",
    it="Posso parlare senza il tuo tema, ma starei solo indovinando. Dammi i tuoi dati di nascita e potrò leggerti davvero.",
    fr="Je peux parler sans ton thème, mais je ne ferais que deviner. Donne-moi tes données de naissance et je pourrai te lire.",
    pt_BR="Posso conversar sem seu mapa, mas estaria só adivinhando. Me dê seus dados de nascimento e poderei ler você."))

add("scr.chat.rule", "The method claim under the opening line. The 4.3(b) argument, in the chat.", lit(
    en="Every answer names the placements it was read from. Nothing here is a prediction.",
    es="Cada respuesta nombra las posiciones de las que se leyó. Nada de esto es una predicción.",
    de="Jede Antwort nennt die Positionen, aus denen sie gelesen wurde. Nichts davon ist eine Vorhersage.",
    it="Ogni risposta nomina le posizioni da cui è stata letta. Niente qui è una previsione.",
    fr="Chaque réponse nomme les positions dont elle est tirée. Rien ici n'est une prédiction.",
    pt_BR="Cada resposta nomeia as posições de onde foi lida. Nada aqui é uma previsão."))

add("scr.chat.prompt1", "A suggested opening question.", lit(
    en="What am I like when nobody is watching?",
    es="¿Cómo soy cuando nadie me mira?",
    de="Wie bin ich, wenn niemand hinsieht?",
    it="Come sono quando nessuno guarda?",
    fr="Comment suis-je quand personne ne regarde ?",
    pt_BR="Como eu sou quando ninguém está olhando?"))

add("scr.chat.prompt2", "A suggested opening question.", lit(
    en="What is crossing my chart this week?",
    es="¿Qué está cruzando mi carta esta semana?",
    de="Was kreuzt diese Woche mein Horoskop?",
    it="Che cosa attraversa il mio tema questa settimana?",
    fr="Qu'est-ce qui traverse mon thème cette semaine ?",
    pt_BR="O que está cruzando meu mapa esta semana?"))

add("scr.chat.prompt3", "A suggested opening question.", lit(
    en="Where do my systems disagree about me?",
    es="¿En qué no coinciden mis sistemas sobre mí?",
    de="Wo widersprechen sich meine Systeme über mich?",
    it="Dove i miei sistemi non concordano su di me?",
    fr="Où mes systèmes ne sont-ils pas d'accord sur moi ?",
    pt_BR="Onde meus sistemas discordam sobre mim?"))

add("scr.chat.placeholder", "The composer's placeholder.", lit(
    en="Ask Alma", es="Pregunta a Alma", de="Frag Alma",
    it="Chiedi ad Alma", fr="Demande à Alma", pt_BR="Pergunte a Alma"))

add("scr.chat.send", "Accessibility label on the send button.", lit(
    en="Send", es="Enviar", de="Senden", it="Invia", fr="Envoyer", pt_BR="Enviar"))

add("scr.chat.thinking", "While an answer is being written.", lit(
    en="Alma is reading your chart",
    es="Alma está leyendo tu carta",
    de="Alma liest dein Horoskop",
    it="Alma sta leggendo il tuo tema",
    fr="Alma lit ton thème",
    pt_BR="Alma está lendo seu mapa"))

add("scr.chat.thinkingStill", "Replaces the line above after ten seconds, so a long wait still reads as progress.", lit(
    en="Still reading — she does not skim.",
    es="Sigue leyendo: no lee por encima.",
    de="Sie liest noch — sie überfliegt nicht.",
    it="Sta ancora leggendo: non va di fretta.",
    fr="Elle lit encore — elle ne survole pas.",
    pt_BR="Ainda lendo — ela não passa os olhos por cima."))

# `scr.chat.notFromChart` was here, and it was the bug in the owner's
# screenshot: an uppercase NOT FROM YOUR CHART under a *refusal*, so a sentence
# declining to read a greeting was dressed as a statement about somebody's
# chart. What replaces it is one sentence, in her own voice, shown only when the
# server says the turn was a genuinely silent chart — never after a greeting,
# never after a message she could not read. See `ChatTurnKind`.
add("scr.chat.silent", "Footnote under an answer Alma gave without the chart, because the chart is silent on it.", lit(
    en="I answered that one from what I know, not from your chart.",
    es="Esa la respondí desde lo que sé, no desde tu carta.",
    de="Diese habe ich aus dem beantwortet, was ich weiß — nicht aus deinem Horoskop.",
    it="A questa ho risposto da ciò che so, non dal tuo tema.",
    fr="J'ai répondu à celle-ci à partir de ce que je sais, pas de ton thème.",
    pt_BR="Essa eu respondi a partir do que sei, não do seu mapa."))

add("scr.chat.couldAsk", "Overline above the three opening questions.", lit(
    en="you could ask",
    es="podrías preguntar",
    de="du könntest fragen",
    it="potresti chiedere",
    fr="tu peux demander",
    pt_BR="você pode perguntar"))

add("scr.chat.readFromAll", "Accessibility label on the collapsed citation line.", lit(
    en="Show every placement this was read from",
    es="Mostrar todas las posiciones de las que se leyó esto",
    de="Alle Positionen zeigen, aus denen das gelesen wurde",
    it="Mostra tutte le posizioni da cui è stato letto",
    fr="Afficher toutes les positions dont ceci est tiré",
    pt_BR="Mostrar todas as posições de onde isto foi lido"))

# The three openers on an empty conversation, each naming a sign this person
# actually has. The sign arrives from the engine in English — it is a key, not
# prose — and is translated by `JourneyL10n.sign` before it lands in `%@`.
add("scr.chat.promptMoon", "Opening question about this person's own moon sign. %@ is the sign.", lit(
    en="My Moon is in %@. What does it actually need?",
    es="Mi Luna está en %@. ¿Qué necesita de verdad?",
    de="Mein Mond steht in %@. Was braucht er wirklich?",
    it="La mia Luna è in %@. Di che cosa ha davvero bisogno?",
    fr="Ma Lune est en %@. De quoi a-t-elle vraiment besoin ?",
    pt_BR="Minha Lua está em %@. Do que ela realmente precisa?"))

add("scr.chat.promptSun", "Opening question about this person's own sun sign. %@ is the sign.", lit(
    en="My Sun is in %@ — what does that ask of me?",
    es="Mi Sol está en %@: ¿qué me pide eso?",
    de="Meine Sonne steht in %@ — was verlangt das von mir?",
    it="Il mio Sole è in %@: che cosa mi chiede?",
    fr="Mon Soleil est en %@ — qu'est-ce que cela me demande ?",
    pt_BR="Meu Sol está em %@ — o que isso me pede?"))

add("scr.chat.promptRising", "Opening question about this person's own rising sign. %@ is the sign.", lit(
    en="%@ rising. Is that what people meet first?",
    es="Ascendente en %@. ¿Es lo primero que ven los demás?",
    de="Aszendent %@. Ist das, was andere zuerst von mir sehen?",
    it="Ascendente %@. È questo che gli altri incontrano per primo?",
    fr="Ascendant %@. Est-ce ce que les autres rencontrent en premier ?",
    pt_BR="Ascendente em %@. É isso que as pessoas encontram primeiro?"))

# The four sentences that replace a status code on this screen. `answer_refused`
# is the one that mattered: its message is `str(exc)` from `conversation.py` —
# English engineering prose — and it was being printed verbatim to whoever asked.
add("scr.chat.refused", "Shown when Alma could not answer without inventing a placement.", lit(
    en="I could not answer that one without inventing a placement, so I did not. Ask it another way and I will try again.",
    es="No podía responder a esa sin inventar una posición, así que no lo hice. Pregúntamelo de otra forma y lo intento de nuevo.",
    de="Ich konnte das nicht beantworten, ohne eine Position zu erfinden — also habe ich es gelassen. Frag es anders, und ich versuche es noch einmal.",
    it="Non potevo rispondere senza inventare una posizione, e non l'ho fatto. Chiedimelo in un altro modo e ci riprovo.",
    fr="Je ne pouvais pas répondre sans inventer une position, alors je ne l'ai pas fait. Reformule et je réessaie.",
    pt_BR="Eu não conseguia responder sem inventar uma posição, então não respondi. Pergunte de outro jeito e eu tento de novo."))

add("scr.chat.offline", "No network, in Alma's voice rather than as a status.", lit(
    en="I cannot reach your chart just now. Your question is still in the box — try again in a moment.",
    es="Ahora mismo no puedo alcanzar tu carta. Tu pregunta sigue escrita: inténtalo en un momento.",
    de="Ich komme gerade nicht an dein Horoskop. Deine Frage steht noch da — versuch es gleich noch einmal.",
    it="In questo momento non riesco a raggiungere il tuo tema. La tua domanda è ancora lì: riprova tra un istante.",
    fr="Je n'arrive pas à atteindre ton thème pour l'instant. Ta question est toujours là — réessaie dans un moment.",
    pt_BR="Não consigo alcançar seu mapa agora. Sua pergunta continua aí — tente de novo em um instante."))

add("scr.chat.unavailable", "Our fault, said as ours.", lit(
    en="Something on my side is not working. Your chart is untouched, and your question is still in the box.",
    es="Algo de mi lado no funciona. Tu carta está intacta y tu pregunta sigue escrita.",
    de="Auf meiner Seite funktioniert etwas nicht. Dein Horoskop ist unberührt, und deine Frage steht noch da.",
    it="Qualcosa dalla mia parte non funziona. Il tuo tema è intatto e la tua domanda è ancora lì.",
    fr="Quelque chose ne fonctionne pas de mon côté. Ton thème est intact, et ta question est toujours là.",
    pt_BR="Algo do meu lado não está funcionando. Seu mapa está intacto e sua pergunta continua aí."))

add("scr.chat.wentWrong", "Anything else that stopped an answer.", lit(
    en="That did not go through. Nothing was lost — your question is still in the box.",
    es="Eso no llegó. No se perdió nada: tu pregunta sigue escrita.",
    de="Das ist nicht durchgekommen. Nichts ist verloren — deine Frage steht noch da.",
    it="Non è passata. Non si è perso nulla: la tua domanda è ancora lì.",
    fr="Cela n'est pas passé. Rien n'est perdu — ta question est toujours là.",
    pt_BR="Isso não passou. Nada se perdeu — sua pergunta continua aí."))

add("scr.chat.outOfQuestions", "Only when the server did not send its own sentence, which already says when they return.", lit(
    en="That is all the questions for today. They come back tomorrow.",
    es="Eso es todo por hoy. Las preguntas vuelven mañana.",
    de="Das waren die Fragen für heute. Morgen gibt es wieder welche.",
    it="Per oggi le domande sono finite. Tornano domani.",
    fr="C'est tout pour aujourd'hui. Les questions reviennent demain.",
    pt_BR="As perguntas de hoje acabaram. Voltam amanhã."))

add("scr.chat.moreQuestions", "Button under the question-limit refusal.", lit(
    en="More questions",
    es="Más preguntas",
    de="Mehr Fragen",
    it="Più domande",
    fr="Plus de questions",
    pt_BR="Mais perguntas"))

add("scr.chat.past", "Menu label listing earlier conversations.", lit(
    en="earlier", es="anteriores", de="früher", it="precedenti", fr="avant", pt_BR="anteriores"))

add("scr.chat.untitled", "A conversation the backend has not titled yet.", lit(
    en="Untitled conversation",
    es="Conversación sin título",
    de="Gespräch ohne Titel",
    it="Conversazione senza titolo",
    fr="Conversation sans titre",
    pt_BR="Conversa sem título"))

# ── sign in ───────────────────────────────────────────────────────────────

add("scr.signIn.eyebrow", "Eyebrow above the sign-in title.", lit(
    en="your account", es="tu cuenta", de="dein Konto",
    it="il tuo account", fr="ton compte", pt_BR="sua conta"))

add("scr.signIn.title", "Sign-in screen title.", lit(
    en="Sign in", es="Iniciar sesión", de="Anmelden",
    it="Accedi", fr="Se connecter", pt_BR="Entrar"))

add("scr.signIn.lead", "What signing in actually does. It attaches; it does not replace.", lit(
    en="Signing in attaches a name to the account you already have. Nothing you have read or bought is lost — it is the same account, made durable.",
    es="Iniciar sesión añade un nombre a la cuenta que ya tienes. No se pierde nada de lo que has leído o comprado: es la misma cuenta, hecha duradera.",
    de="Die Anmeldung hängt einen Namen an das Konto, das du bereits hast. Nichts, was du gelesen oder gekauft hast, geht verloren — es ist dasselbe Konto, nur dauerhaft.",
    it="Accedere aggiunge un nome all'account che hai già. Nulla di ciò che hai letto o comprato va perso: è lo stesso account, reso duraturo.",
    fr="Se connecter attache un nom au compte que tu as déjà. Rien de ce que tu as lu ou acheté n'est perdu — c'est le même compte, rendu durable.",
    pt_BR="Entrar anexa um nome à conta que você já tem. Nada do que você leu ou comprou se perde — é a mesma conta, tornada durável."))

add("scr.signIn.reason1", "Why to sign in.", lit(
    en="Your chart survives a new phone.",
    es="Tu carta sobrevive a un teléfono nuevo.",
    de="Dein Horoskop überlebt ein neues Telefon.",
    it="Il tuo tema sopravvive a un telefono nuovo.",
    fr="Ton thème survit à un nouveau téléphone.",
    pt_BR="Seu mapa sobrevive a um telefone novo."))

add("scr.signIn.reason2", "Why to sign in — the restore case, which is the one that costs money.", lit(
    en="Anything you bought can be restored. A purchase belongs to the account that claimed it first, so sign in before you reinstall.",
    es="Todo lo que compraste se puede restaurar. Una compra pertenece a la cuenta que la reclamó primero, así que inicia sesión antes de reinstalar.",
    de="Alles Gekaufte lässt sich wiederherstellen. Ein Kauf gehört dem Konto, das ihn zuerst beansprucht hat — melde dich also vor einer Neuinstallation an.",
    it="Tutto ciò che hai comprato può essere ripristinato. Un acquisto appartiene all'account che lo ha reclamato per primo, quindi accedi prima di reinstallare.",
    fr="Tout ce que tu as acheté peut être restauré. Un achat appartient au compte qui l'a réclamé en premier, alors connecte-toi avant de réinstaller.",
    pt_BR="Tudo o que você comprou pode ser restaurado. Uma compra pertence à conta que a reivindicou primeiro, então entre antes de reinstalar."))

add("scr.signIn.reason3", "Why to sign in.", lit(
    en="There is no password. There never will be.",
    es="No hay contraseña. Nunca la habrá.",
    de="Es gibt kein Passwort. Und wird nie eines geben.",
    it="Non c'è password. Non ci sarà mai.",
    fr="Il n'y a pas de mot de passe. Il n'y en aura jamais.",
    pt_BR="Não há senha. Nunca haverá."))

add("scr.signIn.orEmail", "Divider above the email field.", lit(
    en="or by email", es="o por correo", de="oder per E-Mail",
    it="o via email", fr="ou par e-mail", pt_BR="ou por e-mail"))

add("scr.signIn.emailPlaceholder", "Email field placeholder.", lit(
    en="Your email address", es="Tu correo electrónico", de="Deine E-Mail-Adresse",
    it="Il tuo indirizzo email", fr="Ton adresse e-mail", pt_BR="Seu e-mail"))

add("scr.signIn.sendLink", "Button that sends the passwordless link.", lit(
    en="Send me a link", es="Envíame un enlace", de="Schick mir einen Link",
    it="Mandami un link", fr="Envoie-moi un lien", pt_BR="Me envie um link"))

add("scr.signIn.sending", "While it is being sent.", lit(
    en="Sending…", es="Enviando…", de="Wird gesendet…",
    it="Invio…", fr="Envoi…", pt_BR="Enviando…"))

add("scr.signIn.linkSent", "After it has been sent.", lit(
    en="Check your inbox. The link signs you in and expires shortly.",
    es="Revisa tu bandeja de entrada. El enlace te identifica y caduca pronto.",
    de="Sieh in deinem Posteingang nach. Der Link meldet dich an und läuft bald ab.",
    it="Controlla la posta. Il link ti fa accedere e scade a breve.",
    fr="Regarde ta boîte de réception. Le lien te connecte et expire bientôt.",
    pt_BR="Verifique sua caixa de entrada. O link faz você entrar e expira em breve."))

add("scr.signIn.failed", "A sign-in that did not work, with no server sentence behind it.", lit(
    en="That did not sign you in. Nothing has changed on your account.",
    es="Eso no te ha identificado. Nada ha cambiado en tu cuenta.",
    de="Damit wurdest du nicht angemeldet. An deinem Konto hat sich nichts geändert.",
    it="Non ha effettuato l'accesso. Nulla è cambiato nel tuo account.",
    fr="Cela ne t'a pas connecté. Rien n'a changé sur ton compte.",
    pt_BR="Isso não fez você entrar. Nada mudou na sua conta."))

add("scr.signIn.done", "After a successful sign-in.", lit(
    en="You are signed in.", es="Has iniciado sesión.", de="Du bist angemeldet.",
    it="Hai effettuato l'accesso.", fr="Tu es connecté.", pt_BR="Você entrou."))

add("scr.signIn.already", "Shown when the screen is opened by somebody already signed in.", lit(
    en="You are already signed in. This account follows you to any phone.",
    es="Ya has iniciado sesión. Esta cuenta te sigue a cualquier teléfono.",
    de="Du bist bereits angemeldet. Dieses Konto folgt dir auf jedes Telefon.",
    it="Hai già effettuato l'accesso. Questo account ti segue su qualsiasi telefono.",
    fr="Tu es déjà connecté. Ce compte te suit sur n'importe quel téléphone.",
    pt_BR="Você já está conectado. Esta conta acompanha você em qualquer telefone."))

add("scr.done", "A button that closes a screen.", lit(
    en="Done", es="Listo", de="Fertig", it="Fatto", fr="Terminé", pt_BR="Pronto"))

add("scr.signIn.privacy", "What we do with the address.", lit(
    en="We use your address for the sign-in link and nothing else. There is no newsletter.",
    es="Usamos tu dirección para el enlace de acceso y nada más. No hay boletín.",
    de="Wir nutzen deine Adresse für den Anmeldelink und für nichts anderes. Es gibt keinen Newsletter.",
    it="Usiamo il tuo indirizzo per il link di accesso e nient'altro. Non c'è newsletter.",
    fr="Nous utilisons ton adresse pour le lien de connexion et rien d'autre. Il n'y a pas de newsletter.",
    pt_BR="Usamos seu endereço para o link de acesso e nada mais. Não há newsletter."))

# ── people ────────────────────────────────────────────────────────────────

add("scr.people.eyebrow", "Eyebrow above the people list.", lit(
    en="compatibility", es="compatibilidad", de="Partnerschaft",
    it="compatibilità", fr="compatibilité", pt_BR="compatibilidade"))

add("scr.people.title", "People list title.", lit(
    en="People", es="Personas", de="Personen", it="Persone", fr="Personnes", pt_BR="Pessoas"))

add("scr.people.lead", "What the list is for.", lit(
    en="Compatibility compares your chart against somebody else's. The comparison itself is calculated free, as every calculation is.",
    es="La compatibilidad compara tu carta con la de otra persona. La comparación se calcula gratis, como todos los cálculos.",
    de="Die Partnerschaftsanalyse vergleicht dein Horoskop mit dem einer anderen Person. Der Vergleich wird kostenlos berechnet, wie jede Berechnung.",
    it="La compatibilità confronta il tuo tema con quello di un'altra persona. Il confronto è calcolato gratis, come ogni calcolo.",
    fr="La compatibilité compare ton thème à celui de quelqu'un d'autre. Le calcul est gratuit, comme tous les calculs.",
    pt_BR="A compatibilidade compara seu mapa com o de outra pessoa. A comparação é calculada de graça, como todo cálculo."))

add("scr.people.saved", "Section label above the saved people.", lit(
    en="saved", es="guardadas", de="gespeichert",
    it="salvate", fr="enregistrées", pt_BR="salvas"))

add("scr.people.consent", "Whose birth data this is. The terms ask; this says it at the point of entry.", lit(
    en="It is their birth data, not yours. Ask them first.",
    es="Son sus datos de nacimiento, no los tuyos. Pídeselo antes.",
    de="Es sind ihre Geburtsdaten, nicht deine. Frag sie vorher.",
    it="Sono i loro dati di nascita, non i tuoi. Chiedi prima.",
    fr="Ce sont leurs données de naissance, pas les tiennes. Demande-leur d'abord.",
    pt_BR="Os dados de nascimento são deles, não seus. Pergunte antes."))

add("scr.people.unnamed", "A saved person with no name.", lit(
    en="Unnamed", es="Sin nombre", de="Ohne Namen",
    it="Senza nome", fr="Sans nom", pt_BR="Sem nome"))

add("scr.people.remove", "The remove control on a row.", lit(
    en="Remove", es="Quitar", de="Entfernen", it="Rimuovi", fr="Retirer", pt_BR="Remover"))

add("scr.people.removeTitle", "Confirmation dialog title.", lit(
    en="Remove this person?", es="¿Quitar a esta persona?", de="Diese Person entfernen?",
    it="Rimuovere questa persona?", fr="Retirer cette personne ?", pt_BR="Remover esta pessoa?"))

add("scr.people.removeWhat", "What removing actually costs.", lit(
    en="Their birth goes, and so does every compatibility reading written from it. Readings you paid for cannot be written again word for word.",
    es="Su nacimiento se borra, y con él toda lectura de compatibilidad escrita a partir de él. Las lecturas que pagaste no pueden volver a escribirse palabra por palabra.",
    de="Ihre Geburt wird gelöscht, und mit ihr jede daraus geschriebene Partnerschaftsdeutung. Bezahlte Deutungen lassen sich nicht Wort für Wort neu schreiben.",
    it="La loro nascita sparisce, e con essa ogni lettura di compatibilità scritta da lì. Le letture pagate non possono essere riscritte parola per parola.",
    fr="Sa naissance disparaît, et avec elle chaque lecture de compatibilité qui en est issue. Les lectures payées ne peuvent pas être réécrites mot pour mot.",
    pt_BR="O nascimento dela some, e com ele toda leitura de compatibilidade escrita a partir dele. Leituras pagas não podem ser reescritas palavra por palavra."))

add("scr.keep", "The cancel side of a destructive confirmation.", lit(
    en="Keep", es="Conservar", de="Behalten", it="Mantieni", fr="Garder", pt_BR="Manter"))

add("scr.addPerson.eyebrow", "Eyebrow above the add-a-person form.", lit(
    en="a second birth", es="un segundo nacimiento", de="eine zweite Geburt",
    it="una seconda nascita", fr="une seconde naissance", pt_BR="um segundo nascimento"))

add("scr.addPerson.title", "Add-a-person title.", lit(
    en="Add a person", es="Añadir una persona", de="Person hinzufügen",
    it="Aggiungi una persona", fr="Ajouter une personne", pt_BR="Adicionar uma pessoa"))

add("scr.addPerson.lead", "What is being asked for and why.", lit(
    en="The same five things your own chart needed. Without the minute of birth the comparison still runs, on fewer factors.",
    es="Las mismas cinco cosas que necesitó tu carta. Sin el minuto de nacimiento la comparación se hace igual, con menos factores.",
    de="Dieselben fünf Angaben, die dein eigenes Horoskop brauchte. Ohne die Geburtsminute läuft der Vergleich trotzdem, mit weniger Faktoren.",
    it="Le stesse cinque cose che serviva al tuo tema. Senza il minuto di nascita il confronto funziona lo stesso, su meno fattori.",
    fr="Les mêmes cinq choses qu'il fallait pour ton thème. Sans la minute de naissance la comparaison fonctionne quand même, sur moins de facteurs.",
    pt_BR="As mesmas cinco coisas que seu mapa precisou. Sem o minuto de nascimento a comparação ainda funciona, com menos fatores."))

add("scr.addPerson.name", "Section label.", lit(
    en="their name", es="su nombre", de="ihr Name",
    it="il loro nome", fr="son nom", pt_BR="o nome"))

add("scr.addPerson.namePlaceholder", "Name field placeholder.", lit(
    en="Name", es="Nombre", de="Name", it="Nome", fr="Nom", pt_BR="Nome"))

add("scr.addPerson.relationPlaceholder", "Relation field placeholder.", lit(
    en="Partner, mother, friend… (optional)",
    es="Pareja, madre, amistad… (opcional)",
    de="Partner, Mutter, Freund… (optional)",
    it="Partner, madre, amico… (facoltativo)",
    fr="Partenaire, mère, ami… (facultatif)",
    pt_BR="Parceiro, mãe, amigo… (opcional)"))

add("scr.addPerson.birthday", "Section label.", lit(
    en="their birthday", es="su fecha de nacimiento", de="ihr Geburtstag",
    it="la loro data di nascita", fr="sa date de naissance", pt_BR="a data de nascimento"))

add("scr.addPerson.birthTime", "Section label.", lit(
    en="their birth time", es="su hora de nacimiento", de="ihre Geburtszeit",
    it="la loro ora di nascita", fr="son heure de naissance", pt_BR="a hora de nascimento"))

add("scr.addPerson.birthplace", "Section label.", lit(
    en="their birthplace", es="su lugar de nacimiento", de="ihr Geburtsort",
    it="il loro luogo di nascita", fr="son lieu de naissance", pt_BR="o local de nascimento"))

add("scr.addPerson.save", "The save button.", lit(
    en="Save this person", es="Guardar esta persona", de="Person speichern",
    it="Salva questa persona", fr="Enregistrer cette personne", pt_BR="Salvar esta pessoa"))

add("scr.addPerson.saving", "While saving.", lit(
    en="Saving…", es="Guardando…", de="Wird gespeichert…",
    it="Salvataggio…", fr="Enregistrement…", pt_BR="Salvando…"))

# ── the compatibility partner, named ──────────────────────────────────────

add("scr.compat.readAgainst", "Who a compatibility reading was computed against.", lit(
    en="Compared with %@",
    es="Comparado con %@",
    de="Verglichen mit %@",
    it="Confrontato con %@",
    fr="Comparé avec %@",
    pt_BR="Comparado com %@"))

add("scr.compat.choose", "Button that opens the people list to change the partner.", lit(
    en="Compare with somebody else",
    es="Comparar con otra persona",
    de="Mit jemand anderem vergleichen",
    it="Confronta con qualcun altro",
    fr="Comparer avec quelqu'un d'autre",
    pt_BR="Comparar com outra pessoa"))

# ── what the app shows before it has any data (the 4.3(b) empty state) ────

add("scr.empty.title", "Heading above the eight systems on an empty Today.", lit(
    en="Eight systems, one chart",
    es="Ocho sistemas, una carta",
    de="Acht Systeme, ein Horoskop",
    it="Otto sistemi, un tema",
    fr="Huit systèmes, un thème",
    pt_BR="Oito sistemas, um mapa"))

add("scr.empty.lead", "What Alma does, before it has anything to do it with.", lit(
    en="Alma computes eight independent systems from a real JPL ephemeris — forty-one chapters in all — and shows you where they agree about you and where they do not.",
    es="Alma calcula ocho sistemas independientes desde una efeméride real del JPL — cuarenta y un capítulos en total — y te muestra dónde coinciden sobre ti y dónde no.",
    de="Alma berechnet acht unabhängige Systeme aus einer echten JPL-Ephemeride — insgesamt einundvierzig Kapitel — und zeigt dir, wo sie über dich übereinstimmen und wo nicht.",
    it="Alma calcola otto sistemi indipendenti da un'effemeride JPL reale — quarantuno capitoli in tutto — e ti mostra dove concordano su di te e dove no.",
    fr="Alma calcule huit systèmes indépendants à partir d'une éphéméride JPL réelle — quarante et un chapitres en tout — et te montre où ils s'accordent sur toi et où ils divergent.",
    pt_BR="Alma calcula oito sistemas independentes a partir de uma efeméride real do JPL — quarenta e um capítulos ao todo — e mostra onde eles concordam sobre você e onde não."))

add("scr.empty.example", "Label above the worked example of a cited factor.", lit(
    en="what a line looks like",
    es="cómo se ve una línea",
    de="wie eine Zeile aussieht",
    it="com'è fatta una riga",
    fr="à quoi ressemble une ligne",
    pt_BR="como é uma linha"))

add("scr.empty.exampleNote", "The sentence under the worked example.", lit(
    en="Every sentence Alma writes names the placement it was read from, like the one above. Nothing is a prediction, and nothing is shown that was not calculated.",
    es="Cada frase que escribe Alma nombra la posición de la que se leyó, como la de arriba. Nada es una predicción, y no se muestra nada que no se haya calculado.",
    de="Jeder Satz, den Alma schreibt, nennt die Position, aus der er gelesen wurde — wie oben. Nichts ist eine Vorhersage, und nichts wird gezeigt, was nicht berechnet wurde.",
    it="Ogni frase che Alma scrive nomina la posizione da cui è stata letta, come quella sopra. Niente è una previsione, e non si mostra nulla che non sia calcolato.",
    fr="Chaque phrase qu'Alma écrit nomme la position dont elle est tirée, comme celle ci-dessus. Rien n'est une prédiction, et rien n'est montré qui n'ait été calculé.",
    pt_BR="Cada frase que Alma escreve nomeia a posição de onde foi lida, como a de cima. Nada é previsão, e nada é mostrado sem ter sido calculado."))

add("scr.empty.chapters", "Chapter count beside a system in the empty state.", lit(
    en="%lld chapters", es="%lld capítulos", de="%lld Kapitel",
    it="%lld capitoli", fr="%lld chapitres", pt_BR="%lld capítulos"))

add("scr.empty.exampleTag", "Marks the sample citation as a sample, not this person's chart.", lit(
    en="example — not your chart",
    es="ejemplo — no es tu carta",
    de="Beispiel — nicht dein Horoskop",
    it="esempio — non è il tuo tema",
    fr="exemple — pas ton thème",
    pt_BR="exemplo — não é o seu mapa"))

# ── the portrait's free-value note, reworded ──────────────────────────────
#
# The web's `journey.freeNote` says "These two systems never cost anything" and
# sits under a block of *three* rows: numerology, the birth card, and the moon
# phase, which is free because it falls out of the natal preview. It reads as an
# off-by-one on the one screen whose entire purpose is to prove the numbers are
# real and carefully computed. Reworded rather than counted differently, because
# the number of free rows depends on what could be computed for this person and
# any fixed count will eventually be wrong again.
add("scr.journey.freeNote", "Under the free values on the portrait. Counts nothing.", lit(
    en="Every number above is calculated, and calculated is always free. They are yours whether you read further or not.",
    es="Cada número de arriba está calculado, y lo calculado siempre es gratis. Son tuyos leas más o no.",
    de="Jede Zahl oben ist berechnet, und Berechnetes ist immer kostenlos. Sie gehören dir, ob du weiterliest oder nicht.",
    it="Ogni numero qui sopra è calcolato, e il calcolo è sempre gratuito. Sono tuoi che tu legga oltre o no.",
    fr="Chaque nombre ci-dessus est calculé, et le calcul est toujours gratuit. Ils sont à toi que tu lises la suite ou non.",
    pt_BR="Cada número acima é calculado, e o cálculo é sempre gratuito. Eles são seus, leia adiante ou não."))

# ── write it out ──────────────────────────────────────────────────────────
#
# The six counted strings that needed plural variations live in
# `Cabinet.xcstrings`, not here — a key is looked up in the table its constant
# names, so moving one to a second table would silently stop resolving. They are
# in `gen_cabinet_strings.py` alongside their siblings.

catalog = {"sourceLanguage": "en", "version": "1.0", "strings": {}}

for key in sorted(T):
    comment, values = T[key]
    missing = [loc for loc in L if not values.get(loc)]
    assert not missing, (key, missing)
    catalog["strings"][key] = {
        "comment": comment,
        "extractionState": "manual",
        "localizations": {
            loc: {"stringUnit": {"state": "translated", "value": values[loc]}}
            for loc in sorted(values)
        },
    }

out = os.path.normpath(OUT)
with open(out, "w") as fh:
    json.dump(catalog, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(len(catalog["strings"]), "keys ->", out)
