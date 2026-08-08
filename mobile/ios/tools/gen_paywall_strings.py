#!/usr/bin/env python3
"""Write Paywall.xcstrings.

Hand-writing a String Catalog is six lines of JSON per key, and the paywall has
fifty of them; this script exists so the six languages sit next to each other in
one readable table while the file Xcode reads is generated from it. Rerunning it
is the way to add a key — never editing the JSON by hand, which is where a
missing language hides.
"""

import json
import pathlib

LANGS = ["en", "es", "de", "it", "fr", "pt-BR"]

# key: (comment, {lang: value})
S: dict[str, tuple[str, dict[str, str]]] = {}


def add(key: str, comment: str, en, es, de, it, fr, ptbr):
    S[key] = (comment, dict(zip(LANGS, [en, es, de, it, fr, ptbr])))


# ── the frame ────────────────────────────────────────────────────────────────

add("paywall.label", "Eyebrow above the ladder. From pricing.label in src/lib/i18n.",
    "what it costs", "cuánto cuesta", "was es kostet", "quanto costa",
    "ce que ça coûte", "quanto custa")

add("paywall.doorSub", "Under the title when one system is being sold. journey.offerSub.",
    "The numbers above are yours and stay free. This opens the whole system — every chapter of the reading, written from your positions, not a template.",
    "Los números de arriba son tuyos y siguen siendo gratis. Esto abre el sistema entero — cada capítulo de la lectura, escrito desde tus posiciones, no una plantilla.",
    "Die Zahlen oben gehören dir und bleiben kostenlos. Das hier öffnet das ganze System — jedes Kapitel der Deutung, aus deinen Positionen geschrieben, keine Vorlage.",
    "I numeri qui sopra sono tuoi e restano gratis. Questo apre l'intero sistema — ogni capitolo della lettura, scritto dalle tue posizioni, non un modello.",
    "Les nombres ci-dessus sont à toi et restent gratuits. Ceci ouvre le système entier — chaque chapitre de la lecture, écrit à partir de tes positions, pas un modèle.",
    "Os números acima são seus e continuam de graça. Isto abre o sistema inteiro — cada capítulo da leitura, escrito a partir das suas posições, não um modelo.")

add("paywall.everythingTitle", "Title of the cabinet paywall. cabinet.openWritten.",
    "Open the rest of what your chart says",
    "Abrir el resto de lo que dice tu carta",
    "Den Rest öffnen, den dein Horoskop sagt",
    "Apri il resto di quello che dice il tuo tema",
    "Ouvrir le reste de ce que dit ton thème",
    "Abrir o resto do que o seu mapa diz")

add("paywall.everythingSub", "Under that title. states.lockedNote.",
    "Written from your own positions the first time you open it — your chart, never a template.",
    "Escrito a partir de tus propias posiciones la primera vez que lo abres — tu carta, nunca una plantilla.",
    "Beim ersten Öffnen aus deinen eigenen Positionen geschrieben — dein Horoskop, nie eine Vorlage.",
    "Scritto dalle tue posizioni la prima volta che lo apri — il tuo tema, mai un modello.",
    "Rédigé à partir de tes propres positions la première fois que tu l'ouvres — ton thème, jamais un modèle.",
    "Escrito a partir das suas próprias posições na primeira vez que você abre — o seu mapa, nunca um modelo.")

add("paywall.freeNote", "The standing promise, repeated where the money is asked for.",
    "Every calculation stays free, always. What has a price is the writing.",
    "Todos los cálculos siguen siendo gratis, siempre. Lo que tiene precio es lo escrito.",
    "Alle Berechnungen bleiben kostenlos, immer. Einen Preis hat das Geschriebene.",
    "Tutti i calcoli restano gratis, sempre. Ad avere un prezzo è ciò che è scritto.",
    "Tous les calculs restent gratuits, toujours. Ce qui a un prix, c'est le texte.",
    "Todos os cálculos continuam de graça, sempre. O que tem preço é o texto.")

# ── the eight, as row titles (eight.names in src/lib/i18n) ───────────────────

add("paywall.system.natal", "Row title for the natal door.",
    "Natal chart", "Carta natal", "Geburtshoroskop", "Tema natale", "Thème natal", "Mapa natal")
add("paywall.system.numerology", "Row title for the numerology door.",
    "Numerology", "Numerología", "Numerologie", "Numerologia", "Numérologie", "Numerologia")
add("paywall.system.birthCard", "Row title for the birth-card door.",
    "Birth Card", "Carta de nacimiento", "Geburtskarte", "Carta di nascita",
    "Carte de naissance", "Carta de nascimento")
add("paywall.system.transits", "Row title for the transits door.",
    "Transits", "Tránsitos", "Transite", "Transiti", "Transits", "Trânsitos")
add("paywall.system.solarReturn", "Row title for the solar-return door.",
    "Solar return", "Revolución solar", "Solarhoroskop", "Rivoluzione solare",
    "Révolution solaire", "Revolução solar")
add("paywall.system.compatibility", "Row title for the compatibility door.",
    "Compatibility", "Compatibilidad", "Partnerschaft", "Affinità", "Compatibilité", "Compatibilidade")
add("paywall.system.astrocartography", "Row title for the astrocartography door.",
    "Astrocartography", "Astrocartografía", "Astrokartografie", "Astrocartografia",
    "Astrocartographie", "Astrocartografia")
add("paywall.system.synthesis", "Row title for the cross-synthesis door.",
    "Cross-synthesis", "Síntesis cruzada", "Quersynthese", "Sintesi incrociata",
    "Synthèse croisée", "Síntese cruzada")

# ── the rungs above a door ───────────────────────────────────────────────────

add("paywall.doorNote", "Under a door row. cabinet.oneTimeNote.",
    "One payment. Yours permanently.", "Un solo pago. Tuyo para siempre.",
    "Einmalzahlung. Bleibt dauerhaft deins.", "Un solo pagamento. Tuo per sempre.",
    "Paiement unique. À vous pour toujours.", "Pagamento único. Seu para sempre.")

add("paywall.archiveTitle", "The archive row. cabinet.wholeArchive.",
    "The whole archive", "El archivo completo", "Das ganze Archiv",
    "L'archivio intero", "L'archive entière", "O arquivo inteiro")

add("paywall.archiveNote", "Under the archive row. cabinet.archiveNote.",
    "All eight systems, bought once.", "Los ocho sistemas, comprados una vez.",
    "Alle acht Systeme, einmal gekauft.", "Tutti gli otto sistemi, acquistati una volta.",
    "Les huit systèmes, achetés une fois.", "Os oito sistemas, comprados uma vez.")

add("paywall.upgradeTitle", "The archive-upgrade row, shown only to somebody who already owns a door.",
    "The rest of the archive", "El resto del archivo", "Der Rest des Archivs",
    "Il resto dell'archivio", "Le reste de l'archive", "O resto do arquivo")

add("paywall.upgradeNote", "Why the upgrade costs less than the archive.",
    "The archive, less what you already paid for one system.",
    "El archivo, menos lo que ya pagaste por un sistema.",
    "Das Archiv, abzüglich dessen, was du für ein System schon bezahlt hast.",
    "L'archivio, meno quello che hai già pagato per un sistema.",
    "L'archive, moins ce que tu as déjà payé pour un système.",
    "O arquivo, menos o que você já pagou por um sistema.")

add("paywall.monthlyTitle", "The monthly plan. The backend calls it 'Everything live, monthly'.",
    "Everything live, monthly", "Todo lo que se mueve, cada mes", "Alles Lebendige, monatlich",
    "Tutto ciò che si muove, ogni mese", "Tout ce qui bouge, chaque mois",
    "Tudo que se move, todo mês")

add("paywall.monthlyNote", "What the monthly plan actually grants. Not everything — the living layer.",
    "Transits, the solar return and compatibility while they move, plus 40 questions a month. Renews until you cancel.",
    "Tránsitos, revolución solar y compatibilidad mientras se mueven, más 40 preguntas al mes. Se renueva hasta que lo canceles.",
    "Transite, Solarhoroskop und Partnerschaft, solange sie ziehen, dazu 40 Fragen im Monat. Verlängert sich, bis du kündigst.",
    "Transiti, rivoluzione solare e affinità mentre si muovono, più 40 domande al mese. Si rinnova finché non disdici.",
    "Transits, révolution solaire et compatibilité au fil de leur course, plus 40 questions par mois. Se renouvelle jusqu'à résiliation.",
    "Trânsitos, revolução solar e compatibilidade conforme se movem, mais 40 perguntas por mês. Renova até você cancelar.")

add("paywall.annualTitle", "The annual plan. pricing.everythingYear.",
    "Everything, for a year", "Todo, durante un año", "Alles, für ein Jahr",
    "Tutto, per un anno", "Tout, pendant un an", "Tudo, por um ano")

add("paywall.annualNote",
    "Under the annual row. pricing.renewsNote, corrected: on iOS cancelling is not two taps in our Settings.",
    "Renews every year until you cancel. Cancel any time in your Apple ID settings.",
    "Se renueva cada año hasta que lo canceles. Cancela cuando quieras en los ajustes de tu Apple ID.",
    "Verlängert sich jedes Jahr, bis du kündigst. Kündigen kannst du jederzeit in deinen Apple-ID-Einstellungen.",
    "Si rinnova ogni anno finché non disdici. Puoi disdire quando vuoi nelle impostazioni del tuo ID Apple.",
    "Se renouvelle chaque année jusqu'à résiliation. Résiliable à tout moment dans les réglages de ton identifiant Apple.",
    "Renova todo ano até você cancelar. Cancele quando quiser nos ajustes do seu Apple ID.")

# ── controls ─────────────────────────────────────────────────────────────────

add("paywall.notNow", "The way out. cabinet.notNow.",
    "Not now", "Ahora no", "Jetzt nicht", "Non ora", "Pas maintenant", "Agora não")

add("paywall.skip", "The way out of the offer after the portrait. journey.offerSkip.",
    "Not now — take me in", "Ahora no — llévame dentro", "Jetzt nicht — bring mich rein",
    "Non ora — portami dentro", "Pas maintenant — fais-moi entrer",
    "Agora não — me leva para dentro")

add("paywall.oneTimeFine", "Fine print under a one-time purchase. journey.offerFine.",
    "One payment. Yours permanently. No account needed to buy.",
    "Un solo pago. Tuyo para siempre. No hace falta cuenta para comprar.",
    "Eine Zahlung. Dauerhaft deins. Zum Kaufen brauchst du kein Konto.",
    "Un pagamento solo. Tuo per sempre. Per comprare non serve un account.",
    "Un seul paiement. À toi définitivement. Aucun compte requis pour acheter.",
    "Um pagamento só. Seu para sempre. Não precisa de conta para comprar.")

add("paywall.restore", "The restore button Apple requires every app that sells non-consumables to have.",
    "Restore purchases", "Restaurar compras", "Käufe wiederherstellen",
    "Ripristina acquisti", "Restaurer les achats", "Restaurar compras")

add("paywall.restoring", "While the restore is running.",
    "Asking the App Store…", "Preguntando a la App Store…", "Frage den App Store…",
    "Sto chiedendo all'App Store…", "Je demande à l'App Store…", "Perguntando à App Store…")

add("paywall.restoredNone", "A restore that found nothing. Not an error.",
    "The App Store has nothing to restore for this Apple ID.",
    "La App Store no tiene nada que restaurar para este Apple ID.",
    "Der App Store hat für diese Apple-ID nichts wiederherzustellen.",
    "L'App Store non ha nulla da ripristinare per questo ID Apple.",
    "L'App Store n'a rien à restaurer pour cet identifiant Apple.",
    "A App Store não tem nada para restaurar neste Apple ID.")

add("paywall.restoredOther",
    "A restore that found purchases already claimed by a different Alma account. The fix is signing in, not a second grant.",
    "These purchases already belong to another Alma account. Sign in with that one and they come with you.",
    "Estas compras ya pertenecen a otra cuenta de Alma. Inicia sesión con esa y vienen contigo.",
    "Diese Käufe gehören bereits einem anderen Alma-Konto. Melde dich mit diesem an, dann kommen sie mit.",
    "Questi acquisti appartengono già a un altro account Alma. Accedi con quello e ti seguono.",
    "Ces achats appartiennent déjà à un autre compte Alma. Connecte-toi avec celui-là et ils te suivent.",
    "Estas compras já pertencem a outra conta Alma. Entre com ela e elas vêm junto.")

add("paywall.restored", "A restore that worked.",
    "Restored. Everything you bought is open again.",
    "Restaurado. Todo lo que compraste vuelve a estar abierto.",
    "Wiederhergestellt. Alles, was du gekauft hast, ist wieder offen.",
    "Ripristinato. Tutto quello che hai comprato è di nuovo aperto.",
    "Restauré. Tout ce que tu as acheté est de nouveau ouvert.",
    "Restaurado. Tudo o que você comprou está aberto de novo.")

add("paywall.pending", "Ask to Buy: a parent has to approve. Nothing is charged yet.",
    "Waiting for approval. Nothing has been charged, and this opens by itself the moment it is approved.",
    "Esperando aprobación. No se ha cobrado nada, y esto se abrirá solo en cuanto se apruebe.",
    "Warte auf Freigabe. Es wurde nichts abgebucht, und sobald sie erteilt ist, öffnet sich das hier von selbst.",
    "In attesa di approvazione. Non è stato addebitato nulla, e questo si aprirà da solo appena arriva.",
    "En attente d'autorisation. Rien n'a été débité, et ceci s'ouvrira tout seul dès l'accord.",
    "Esperando aprovação. Nada foi cobrado, e isto abre sozinho assim que for aprovado.")

# ── the ways it fails ────────────────────────────────────────────────────────

add("paywall.storeUnavailable", "StoreKit gave us no products. Without a price from Apple there is nothing honest to show.",
    "The App Store is not answering. Nothing here can be bought until it does — and nothing you already own has changed.",
    "La App Store no responde. Aquí no se puede comprar nada hasta que responda — y nada de lo que ya tienes ha cambiado.",
    "Der App Store antwortet nicht. Bis dahin lässt sich hier nichts kaufen — und an dem, was dir schon gehört, ändert das nichts.",
    "L'App Store non risponde. Qui non si può comprare nulla finché non risponde — e quello che possiedi già non cambia.",
    "L'App Store ne répond pas. Rien ne peut être acheté ici tant qu'il ne répond pas — et rien de ce que tu possèdes déjà ne change.",
    "A App Store não está respondendo. Nada pode ser comprado aqui até que responda — e nada do que você já tem mudou.")

add("paywall.verifyLater", "503 from our own server after Apple took the money. The store's notification grants independently.",
    "Apple has taken the payment. We could not confirm it this second — it will open by itself shortly, and nothing is lost.",
    "Apple ya cobró el pago. No hemos podido confirmarlo en este momento — se abrirá solo en un momento y no se pierde nada.",
    "Apple hat die Zahlung eingezogen. Wir konnten sie gerade nicht bestätigen — sie öffnet sich gleich von selbst, und nichts geht verloren.",
    "Apple ha incassato il pagamento. Non siamo riusciti a confermarlo in questo momento — si aprirà da solo tra poco, e non si perde nulla.",
    "Apple a prélevé le paiement. Nous n'avons pas pu le confirmer à l'instant — cela s'ouvrira tout seul sous peu, et rien n'est perdu.",
    "A Apple já cobrou o pagamento. Não conseguimos confirmar agora — vai abrir sozinho em instantes, e nada se perde.")

add("paywall.refused", "409 product_mismatch, or a purchase the store says is not complete.",
    "That purchase is not the one that was asked for. Nothing extra has been charged.",
    "Esa compra no es la que se pidió. No se ha cobrado nada de más.",
    "Dieser Kauf ist nicht der, der angefragt wurde. Es wurde nichts zusätzlich abgebucht.",
    "Quell'acquisto non è quello richiesto. Non è stato addebitato nulla in più.",
    "Cet achat n'est pas celui qui a été demandé. Rien de plus n'a été débité.",
    "Essa compra não é a que foi pedida. Nada a mais foi cobrado.")

add("paywall.withdrawn", "409 purchase_incomplete on Apple: the transaction was refunded or revoked.",
    "Apple has taken that purchase back — refunded or revoked — so nothing is open under it.",
    "Apple ha retirado esa compra — reembolsada o revocada — así que no hay nada abierto con ella.",
    "Apple hat diesen Kauf zurückgenommen — erstattet oder widerrufen —, deshalb ist damit nichts offen.",
    "Apple ha ritirato quell'acquisto — rimborsato o revocato — quindi non c'è nulla di aperto con esso.",
    "Apple a repris cet achat — remboursé ou révoqué — donc rien n'est ouvert avec lui.",
    "A Apple retirou essa compra — reembolsada ou revogada — então nada está aberto com ela.")

add("paywall.notVerified", "401 invalid_transaction. Rare, and worth an alert on our side.",
    "That purchase could not be verified, so nothing has been opened. If Apple charged you, write to us and we will sort it out.",
    "No se ha podido verificar esa compra, así que no se ha abierto nada. Si Apple te cobró, escríbenos y lo resolvemos.",
    "Dieser Kauf konnte nicht bestätigt werden, deshalb wurde nichts geöffnet. Falls Apple abgebucht hat, schreib uns und wir klären das.",
    "Non è stato possibile verificare quell'acquisto, quindi non è stato aperto nulla. Se Apple ha addebitato, scrivici e sistemiamo.",
    "Cet achat n'a pas pu être vérifié, donc rien n'a été ouvert. Si Apple t'a débité, écris-nous et on règle ça.",
    "Não foi possível verificar essa compra, então nada foi aberto. Se a Apple cobrou, escreva para a gente e resolvemos.")

add("paywall.offline", "No network between the tap and our server.",
    "Alma is not answering right now, so the purchase could not be confirmed. It will open by itself once she does.",
    "Alma no responde ahora mismo, así que no se ha podido confirmar la compra. Se abrirá sola cuando responda.",
    "Alma antwortet gerade nicht, deshalb konnte der Kauf nicht bestätigt werden. Er öffnet sich von selbst, sobald sie es tut.",
    "Alma non risponde in questo momento, quindi l'acquisto non è stato confermato. Si aprirà da solo appena risponde.",
    "Alma ne répond pas pour l'instant, l'achat n'a donc pas pu être confirmé. Il s'ouvrira tout seul dès qu'elle répondra.",
    "A Alma não está respondendo agora, então a compra não pôde ser confirmada. Vai abrir sozinha assim que ela responder.")

# ── owning things ────────────────────────────────────────────────────────────

add("paywall.owned", "Marker on a row this account already holds.",
    "yours", "tuyo", "gehört dir", "tuo", "à toi", "seu")

add("paywall.ownedAll", "Shown instead of the ladder when there is nothing left to sell.",
    "Everything is open. All forty-one chapters are yours.",
    "Todo está abierto. Los cuarenta y un capítulos son tuyos.",
    "Alles ist offen. Alle einundvierzig Kapitel gehören dir.",
    "È tutto aperto. Tutti e quarantuno i capitoli sono tuoi.",
    "Tout est ouvert. Les quarante et un chapitres sont à toi.",
    "Está tudo aberto. Os quarenta e um capítulos são seus.")

# ── the store's own terms ────────────────────────────────────────────────────

add("paywall.manage", "Opens Apple's own subscription screen.",
    "Manage your subscription", "Gestionar tu suscripción", "Abo verwalten",
    "Gestisci l'abbonamento", "Gérer ton abonnement", "Gerenciar sua assinatura")

add("paywall.manageNote", "Why the cancel button is a link to Apple rather than a button of ours.",
    "Plans bought in the app are cancelled in your Apple ID settings, not here.",
    "Los planes comprados en la app se cancelan en los ajustes de tu Apple ID, no aquí.",
    "In der App gekaufte Abos kündigst du in den Apple-ID-Einstellungen, nicht hier.",
    "Gli abbonamenti acquistati nell'app si disdicono nelle impostazioni del tuo ID Apple, non qui.",
    "Les abonnements achetés dans l'app se résilient dans les réglages de ton identifiant Apple, pas ici.",
    "Planos comprados no app são cancelados nos ajustes do seu Apple ID, não aqui.")

add("paywall.autoRenewTerms",
    "The auto-renewal disclosure App Review asks for, next to the payment action rather than in the terms.",
    "Payment is charged to your Apple ID when you confirm. The plan renews automatically unless you cancel at least 24 hours before the period ends, and the renewal is charged within the 24 hours before it. Manage or cancel it in your Apple ID settings.",
    "El pago se carga a tu Apple ID al confirmar. El plan se renueva automáticamente salvo que lo canceles al menos 24 horas antes de que acabe el periodo, y el cobro de la renovación se hace en las 24 horas previas. Gestiónalo o cancélalo en los ajustes de tu Apple ID.",
    "Die Zahlung wird bei der Bestätigung über deine Apple-ID abgebucht. Das Abo verlängert sich automatisch, sofern du nicht mindestens 24 Stunden vor Ende des Zeitraums kündigst; die Verlängerung wird in den 24 Stunden davor abgebucht. Verwalten und kündigen kannst du es in deinen Apple-ID-Einstellungen.",
    "Il pagamento viene addebitato sul tuo ID Apple alla conferma. L'abbonamento si rinnova automaticamente se non disdici almeno 24 ore prima della fine del periodo, e il rinnovo viene addebitato nelle 24 ore precedenti. Puoi gestirlo o disdirlo nelle impostazioni del tuo ID Apple.",
    "Le paiement est débité de ton identifiant Apple à la confirmation. L'abonnement se renouvelle automatiquement sauf résiliation au moins 24 heures avant la fin de la période, et le renouvellement est débité dans les 24 heures qui la précèdent. Gère-le ou résilie-le dans les réglages de ton identifiant Apple.",
    "O pagamento é cobrado no seu Apple ID ao confirmar. O plano renova automaticamente a menos que você cancele pelo menos 24 horas antes do fim do período, e a renovação é cobrada nas 24 horas anteriores. Gerencie ou cancele nos ajustes do seu Apple ID.")

add("paywall.terms", "Link to the terms. journey.legalTerms.",
    "Terms", "Términos", "AGB", "Termini", "Conditions", "Termos")

add("paywall.privacy", "Link to the privacy policy. journey.legalPrivacy.",
    "Privacy Policy", "Política de privacidad", "Datenschutzerklärung",
    "Informativa privacy", "Politique de confidentialité", "Política de Privacidade")

add("paywall.subscriptionTerms", "Link to the subscription terms document.",
    "Subscription terms", "Condiciones de suscripción", "Abo-Bedingungen",
    "Condizioni di abbonamento", "Conditions d'abonnement", "Termos da assinatura")

# ── the honesty plate, corrected for a store ─────────────────────────────────

add("paywall.honestyOnce", "First line of the honesty plate. pricing.honesty[0].",
    "one-time is one-time", "un pago único es un pago único", "einmal ist einmal",
    "una tantum è una tantum", "un paiement unique reste unique",
    "pagamento único é pagamento único")

add("paywall.honestySeller",
    "Second line. The web app promises an email before renewal, which is our webhook's job and not ours on a store.",
    "Apple takes the payment and sends the receipt",
    "Apple cobra y envía el recibo",
    "Apple zieht ein und schickt den Beleg",
    "Apple incassa e manda la ricevuta",
    "Apple encaisse et envoie le reçu",
    "a Apple cobra e envia o recibo")

add("paywall.honestyCancel",
    "Third line. The web app says 'cancel in two taps' from our Settings, which is false on iOS.",
    "cancel in your Apple ID settings", "cancelas en los ajustes de tu Apple ID",
    "Kündigen in den Apple-ID-Einstellungen", "disdici nelle impostazioni dell'ID Apple",
    "résiliation dans les réglages Apple", "cancele nos ajustes do Apple ID")


def build() -> dict:
    strings = {}
    for key, (comment, values) in sorted(S.items()):
        missing = [lang for lang in LANGS if not values.get(lang)]
        if missing:
            raise SystemExit(f"{key} is missing {missing}")
        strings[key] = {
            "comment": comment,
            "extractionState": "manual",
            "localizations": {
                lang: {"stringUnit": {"state": "translated", "value": values[lang]}}
                for lang in sorted(LANGS)
            },
        }
    return {"sourceLanguage": "en", "strings": strings, "version": "1.0"}


out = pathlib.Path(
    "/Users/anatoliymikhaylow/alma_project1/mobile/ios/Alma/Resources/Paywall.xcstrings"
)
out.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n")
print(f"wrote {out} — {len(S)} keys × {len(LANGS)} languages")
