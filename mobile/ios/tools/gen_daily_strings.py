#!/usr/bin/env python3
"""Write Alma/Resources/Daily.xcstrings, and merge the push keys into Localizable.

Two catalogs, and the split is not organisational tidiness — it is a mechanical
constraint that will bite anybody who ignores it.

**`Daily.xcstrings`** holds everything the *app* draws: the Today block, the
three settings positions, the invitation, the honest status lines. A table per
owner is this project's rule (see `gen_screens_strings.py`), and
`LocalizedStringResource` takes a table name, so the cost is one argument.

**`Localizable.xcstrings`** gets the `push.daily.*` keys, and it has to.
`loc-key` and `title-loc-key` in an APNs payload are resolved by the operating
system, and iOS looks them up in **`Localizable.strings` only** — there is no
table parameter in a push payload. A `push.daily.square` sitting in `Daily`
would resolve to nothing and the notification would arrive showing the raw key.
So this script *merges* into that file rather than overwriting it: it reads what
is there, replaces only keys beginning `push.`, and writes the union back.

## Why one key per aspect rather than one key with the aspect as an argument

`loc-args` are substituted verbatim, with no nested lookup. An aspect is a verb
in English ("squares"), a prepositional phrase in German ("im Quadrat zu") and a
noun phrase in Italian ("in quadratura al") — its grammar is different in each
of the six languages and it changes the word order of the sentence around it.
That is precisely the half `docs/PUSH.md §1.6` says belongs in the template a
translator opens, not in the arguments the server substitutes.

So the server picks the key from the aspect and passes **two placement names and
a time**: closed sets of single words, which is the other half of the same
division of labour. There are five aspects in `ASPECT_TARGETS`, and a sixth
would be a sixth key here rather than a change of shape.

    $ python3 tools/gen_daily_strings.py
"""

import json
import os

L = ["en", "es", "de", "it", "fr", "pt-BR"]
HERE = os.path.dirname(__file__)
DAILY_OUT = os.path.normpath(os.path.join(HERE, "..", "Alma", "Resources", "Daily.xcstrings"))
LOCALIZABLE = os.path.normpath(
    os.path.join(HERE, "..", "Alma", "Resources", "Localizable.xcstrings")
)

DAILY = {}
PUSH = {}


def lit(en, es, de, it, fr, pt_BR):
    return {"en": en, "es": es, "de": de, "it": it, "fr": fr, "pt-BR": pt_BR}


def add(key, comment, values):
    assert key not in DAILY, key
    DAILY[key] = (comment, values)


def push(key, comment, values):
    assert key not in PUSH, key
    assert key.startswith("push."), key
    PUSH[key] = (comment, values)


# ── the setting: one control, three positions ─────────────────────────────
#
# The wording of the three positions and their three detail lines is
# `docs/THE-DAILY.md §5.4` verbatim in English. It is not paraphrased here,
# because those three lines carry the honesty the whole feature rests on — "Today
# is still here whenever you open it" is what makes Off a safe choice rather than
# a loss — and they are the ones most likely to be flattened in translation.

add("daily.setting.title", "Section label for the notification control.", lit(
    en="The daily",
    es="Lo diario",
    de="Das Tägliche",
    it="Il quotidiano",
    fr="Le quotidien",
    pt_BR="O diário"))

add("daily.setting.off", "Position 1 of 3.", lit(
    en="Off", es="Desactivado", de="Aus", it="Disattivato",
    fr="Désactivé", pt_BR="Desligado"))

add("daily.setting.occasionally", "Position 2 of 3. The default for a subscriber.", lit(
    en="Occasionally", es="De vez en cuando", de="Gelegentlich",
    it="Ogni tanto", fr="De temps en temps", pt_BR="De vez em quando"))

add("daily.setting.onlyWhatMatters", "Position 3 of 3.", lit(
    en="Only what matters", es="Solo lo que importa", de="Nur was zählt",
    it="Solo ciò che conta", fr="Seulement l'essentiel", pt_BR="Só o que importa"))

add("daily.setting.off.detail", "Under position 1. Makes Off a safe choice rather than a loss.", lit(
    en="No notifications. Today is still here whenever you open it.",
    es="Sin notificaciones. Hoy sigue aquí siempre que lo abras.",
    de="Keine Mitteilungen. Heute ist trotzdem da, wann immer du es öffnest.",
    it="Nessuna notifica. Oggi resta qui ogni volta che lo apri.",
    fr="Aucune notification. Aujourd'hui reste là chaque fois que tu l'ouvres.",
    pt_BR="Sem notificações. Hoje continua aqui sempre que você abrir."))

add("daily.setting.occasionally.detail", "Under position 2. The measured cadence, stated plainly.", lit(
    en="About once a week, when something in your chart is actually exact.",
    es="Aproximadamente una vez por semana, cuando algo en tu carta es exacto de verdad.",
    de="Etwa einmal pro Woche, wenn in deinem Horoskop wirklich etwas exakt wird.",
    it="Circa una volta a settimana, quando qualcosa nel tuo tema diventa davvero esatto.",
    fr="Environ une fois par semaine, quand quelque chose dans ton thème devient vraiment exact.",
    pt_BR="Cerca de uma vez por semana, quando algo no seu mapa fica realmente exato."))

add("daily.setting.onlyMatters.detail", "Under position 3.", lit(
    en="A few times a year. The slow ones only — the transits that last months.",
    es="Unas pocas veces al año. Solo los lentos: los tránsitos que duran meses.",
    de="Ein paar Mal im Jahr. Nur die langsamen — die Transite, die Monate dauern.",
    it="Poche volte all'anno. Solo i lenti: i transiti che durano mesi.",
    fr="Quelques fois par an. Seulement les lents — les transits qui durent des mois.",
    pt_BR="Poucas vezes por ano. Só os lentos — os trânsitos que duram meses."))

add("daily.setting.hour", "Label on the delivery-hour row.", lit(
    en="Arrives at", es="Llega a las", de="Kommt um",
    it="Arriva alle", fr="Arrive à", pt_BR="Chega às"))

add("daily.setting.quiet", "Quiet hours. Shown, not editable — see THE-DAILY §5.2.", lit(
    en="Never between 22:00 and 08:00, in your time.",
    es="Nunca entre las 22:00 y las 08:00, en tu hora.",
    de="Nie zwischen 22:00 und 08:00, in deiner Zeit.",
    it="Mai tra le 22:00 e le 08:00, nella tua ora.",
    fr="Jamais entre 22h00 et 08h00, à ton heure.",
    pt_BR="Nunca entre 22:00 e 08:00, no seu horário."))

add("daily.setting.timezone", "Label on the timezone row.", lit(
    en="Your time", es="Tu hora", de="Deine Zeit",
    it="La tua ora", fr="Ton heure", pt_BR="Seu horário"))

add("daily.setting.timezone.device", "Where the zone came from. Shown so the override is discoverable.", lit(
    en="from your device", es="desde tu dispositivo", de="von deinem Gerät",
    it="dal tuo dispositivo", fr="depuis ton appareil", pt_BR="do seu aparelho"))

add("daily.setting.timezone.birth", "Where the zone came from.", lit(
    en="from your birth data", es="desde tus datos de nacimiento",
    de="aus deinen Geburtsdaten", it="dai tuoi dati di nascita",
    fr="depuis tes données de naissance", pt_BR="dos seus dados de nascimento"))

add("daily.setting.timezone.chosen", "Where the zone came from.", lit(
    en="you chose this", es="lo elegiste tú", de="von dir gewählt",
    it="l'hai scelta tu", fr="tu l'as choisie", pt_BR="você escolheu"))

# ── the two actions on the notification itself ────────────────────────────

add("daily.action.turnOff", "Action button on every notification. One tap to Off.", lit(
    en="Turn these off", es="Desactivar esto", de="Diese abschalten",
    it="Disattiva queste", fr="Désactiver", pt_BR="Desligar isto"))

add("daily.action.quieter", "Action button on every notification. Steps down a position.", lit(
    en="Fewer of these", es="Menos de estas", de="Weniger davon",
    it="Meno di queste", fr="Moins souvent", pt_BR="Menos disto"))

add("daily.action.turnedOff", "Confirmation banner after the notification action ran.", lit(
    en="Turned off. Today is still here whenever you open it.",
    es="Desactivado. Hoy sigue aquí siempre que lo abras.",
    de="Abgeschaltet. Heute ist trotzdem da, wann immer du es öffnest.",
    it="Disattivato. Oggi resta qui ogni volta che lo apri.",
    fr="Désactivé. Aujourd'hui reste là chaque fois que tu l'ouvres.",
    pt_BR="Desligado. Hoje continua aqui sempre que você abrir."))

# ── the block on Today ────────────────────────────────────────────────────

add("daily.today.label", "Section label above the day's exact contact.", lit(
    en="Exact today", es="Exacto hoy", de="Heute exakt",
    it="Esatto oggi", fr="Exact aujourd'hui", pt_BR="Exato hoje"))

add("daily.today.at", "The instant it perfects. %@ is a time of day.", lit(
    en="Exact at %@", es="Exacto a las %@", de="Exakt um %@",
    it="Esatto alle %@", fr="Exact à %@", pt_BR="Exato às %@"))

add("daily.today.since", "How long it has been live. %@ is a date.", lit(
    en="In orb since %@", es="En orbe desde el %@", de="Im Orbis seit %@",
    it="In orbe dal %@", fr="Dans l'orbe depuis le %@", pt_BR="Em orbe desde %@"))

add("daily.today.until", "When it stops. %@ is a date.", lit(
    en="in orb until %@", es="en orbe hasta el %@", de="im Orbis bis %@",
    it="in orbe fino al %@", fr="dans l'orbe jusqu'au %@", pt_BR="em orbe até %@"))

add("daily.empty.title", "The honest empty state. A day with nothing exact is a real answer.", lit(
    en="Nothing is exact today", es="Hoy nada es exacto", de="Heute ist nichts exakt",
    it="Oggi niente è esatto", fr="Rien n'est exact aujourd'hui", pt_BR="Nada está exato hoje"))

add("daily.empty.body", "Under the empty state, pointing at what is still live.", lit(
    en="What is still in orb is below. Nothing perfects today.",
    es="Lo que sigue en orbe está abajo. Hoy nada se hace exacto.",
    de="Was noch im Orbis steht, findest du unten. Heute wird nichts exakt.",
    it="Ciò che è ancora in orbe è qui sotto. Oggi niente diventa esatto.",
    fr="Ce qui est encore dans l'orbe est ci-dessous. Rien ne devient exact aujourd'hui.",
    pt_BR="O que ainda está em orbe está abaixo. Hoje nada se torna exato."))

# ── the ask, which is our own and comes before the system's ───────────────

add("daily.ask.title", "The invitation on Today. THE-DAILY §5.2's second entrance.", lit(
    en="Tell me the morning it happens",
    es="Avísame la mañana en que ocurra",
    de="Sag mir Bescheid an dem Morgen, an dem es passiert",
    it="Dimmelo la mattina in cui accade",
    fr="Préviens-moi le matin où cela arrive",
    pt_BR="Me avise na manhã em que acontecer"))

add("daily.ask.body", "What will arrive and how often, before any system dialog.", lit(
    en="One notification, at 08:00, on the days something in your chart is exact. About once a week. Never at night, and you can turn it off from inside the notification itself.",
    es="Una notificación, a las 08:00, los días en que algo en tu carta sea exacto. Aproximadamente una vez por semana. Nunca de noche, y puedes desactivarla desde la propia notificación.",
    de="Eine Mitteilung, um 08:00, an den Tagen, an denen in deinem Horoskop etwas exakt wird. Etwa einmal pro Woche. Nie nachts, und du kannst sie direkt aus der Mitteilung heraus abschalten.",
    it="Una notifica, alle 08:00, nei giorni in cui qualcosa nel tuo tema è esatto. Circa una volta a settimana. Mai di notte, e puoi disattivarla dalla notifica stessa.",
    fr="Une notification, à 08h00, les jours où quelque chose dans ton thème est exact. Environ une fois par semaine. Jamais la nuit, et tu peux la désactiver depuis la notification elle-même.",
    pt_BR="Uma notificação, às 08:00, nos dias em que algo no seu mapa estiver exato. Cerca de uma vez por semana. Nunca à noite, e você pode desligar pela própria notificação."))

add("daily.ask.yes", "Accepts the invitation. The platform prompt comes after this.", lit(
    en="Yes, tell me", es="Sí, avísame", de="Ja, sag mir Bescheid",
    it="Sì, dimmelo", fr="Oui, préviens-moi", pt_BR="Sim, me avise"))

add("daily.ask.no", "Declines, repeatably. Our question costs nothing to ask twice.", lit(
    en="Not now", es="Ahora no", de="Jetzt nicht",
    it="Non ora", fr="Pas maintenant", pt_BR="Agora não"))

# ── the honest status lines ───────────────────────────────────────────────

add("daily.status.denied", "Shown once, never nagged. §5.5(3).", lit(
    en="Notifications are off for Alma. You can turn them on in your phone's settings.",
    es="Las notificaciones de Alma están desactivadas. Puedes activarlas en los ajustes del teléfono.",
    de="Mitteilungen für Alma sind aus. Du kannst sie in den Einstellungen deines Telefons einschalten.",
    it="Le notifiche di Alma sono disattivate. Puoi attivarle nelle impostazioni del telefono.",
    fr="Les notifications d'Alma sont désactivées. Tu peux les activer dans les réglages de ton téléphone.",
    pt_BR="As notificações da Alma estão desligadas. Você pode ligá-las nos ajustes do seu telefone."))

add("daily.status.openSettings", "Button beside the denied line.", lit(
    en="Open settings", es="Abrir ajustes", de="Einstellungen öffnen",
    it="Apri impostazioni", fr="Ouvrir les réglages", pt_BR="Abrir ajustes"))

add("daily.status.provisional", "iOS provisional authorization, described as it actually behaves.", lit(
    en="Arriving quietly. Alma's notifications go straight to Notification Center — no banner, no sound — until you decide otherwise.",
    es="Llegan en silencio. Las notificaciones de Alma van directas al Centro de notificaciones —sin banner ni sonido— hasta que decidas otra cosa.",
    de="Sie kommen leise an. Almas Mitteilungen gehen direkt in die Mitteilungszentrale — ohne Banner, ohne Ton — bis du es anders entscheidest.",
    it="Arrivano in silenzio. Le notifiche di Alma vanno dritte al Centro Notifiche — senza banner né suono — finché non decidi diversamente.",
    fr="Elles arrivent discrètement. Les notifications d'Alma vont directement au Centre de notifications — sans bannière ni son — jusqu'à ce que tu en décides autrement.",
    pt_BR="Chegam em silêncio. As notificações da Alma vão direto para a Central de Notificações — sem banner nem som — até você decidir o contrário."))

add("daily.status.upgrade", "The provisional → explicit escalation, offered once.", lit(
    en="Let them arrive properly", es="Deja que lleguen de verdad",
    de="Lass sie richtig ankommen", it="Falle arrivare davvero",
    fr="Laisse-les arriver vraiment", pt_BR="Deixe que cheguem de verdade"))

# The one line in this file that is about our own unfinished work rather than
# about the reader's phone — and it is here rather than omitted because the
# alternative is a switch that claims to deliver something no sender exists for.
# The web app shipped exactly that once and it was taken back out; see the note
# at the top of the Android SettingsScreen.
add("daily.status.notDelivering", "Truthful when this device has no accepted push registration.", lit(
    en="Nothing is being sent yet. This phone is not registered for notifications, so the daily lives here, on Today.",
    es="Todavía no se envía nada. Este teléfono no está registrado para notificaciones, así que lo diario vive aquí, en Hoy.",
    de="Es wird noch nichts gesendet. Dieses Telefon ist nicht für Mitteilungen registriert, also lebt das Tägliche hier, unter Heute.",
    it="Non viene ancora inviato nulla. Questo telefono non è registrato per le notifiche, quindi il quotidiano vive qui, in Oggi.",
    fr="Rien n'est encore envoyé. Ce téléphone n'est pas enregistré pour les notifications, le quotidien vit donc ici, dans Aujourd'hui.",
    pt_BR="Nada está sendo enviado ainda. Este telefone não está registrado para notificações, então o diário vive aqui, em Hoje."))

add("daily.status.registered", "Truthful when the server has accepted this device's token.", lit(
    en="This phone is registered for the daily.",
    es="Este teléfono está registrado para lo diario.",
    de="Dieses Telefon ist für das Tägliche registriert.",
    it="Questo telefono è registrato per il quotidiano.",
    fr="Ce téléphone est enregistré pour le quotidien.",
    pt_BR="Este telefone está registrado para o diário."))

add("daily.subscriberOnly", "A free reader turning the switch on. Not a broken switch — a door.", lit(
    en="The daily is part of the monthly plan. Today is free, and always will be.",
    es="Lo diario forma parte del plan mensual. Hoy es gratis, y siempre lo será.",
    de="Das Tägliche gehört zum Monatsplan. Heute ist kostenlos und bleibt es.",
    it="Il quotidiano fa parte del piano mensile. Oggi è gratuito, e lo resterà.",
    fr="Le quotidien fait partie de l'abonnement mensuel. Aujourd'hui est gratuit, et le restera.",
    pt_BR="O diário faz parte do plano mensal. Hoje é gratuito, e sempre será."))

# ── the claim, checked against this person's own chart ────────────────────

add("daily.verified.label", "Label on the counted row under the setting.", lit(
    en="Exact days in the next 30",
    es="Días exactos en los próximos 30",
    de="Exakte Tage in den nächsten 30",
    it="Giorni esatti nei prossimi 30",
    fr="Jours exacts dans les 30 prochains",
    pt_BR="Dias exatos nos próximos 30"))

add("daily.verified.note", "Says where the number came from, so the cadence claim is checkable.", lit(
    en="Counted from your own chart, on this device, with the same rule the notification uses.",
    es="Contados desde tu propia carta, en este dispositivo, con la misma regla que usa la notificación.",
    de="Aus deinem eigenen Horoskop gezählt, auf diesem Gerät, mit derselben Regel wie die Mitteilung.",
    it="Contati dal tuo tema, su questo dispositivo, con la stessa regola che usa la notifica.",
    fr="Comptés depuis ton propre thème, sur cet appareil, avec la règle qu'utilise la notification.",
    pt_BR="Contados a partir do seu mapa, neste aparelho, com a mesma regra que a notificação usa."))

# ── the payload keys ──────────────────────────────────────────────────────
#
# %1$@ and %2$@ are placement names — already translated by the server, from the
# table `docs/PUSH.md §1.6` asks `alma/i18n/` for — and %3$@ is a time of day.
# Nothing here is a sentence composed on a server, and nothing here can drift
# from what the app shows, because the app never composes these at all.

push("push.daily.title", "APNs title-loc-key / FCM title_loc_key for every daily.", lit(
    en="Exact today", es="Exacto hoy", de="Heute exakt",
    it="Esatto oggi", fr="Exact aujourd'hui", pt_BR="Exato hoje"))

push("push.daily.conjunction", "Body. %1$@ transiting body, %2$@ natal point, %3$@ time.", lit(
    en="%1$@ meets your %2$@ at %3$@.",
    es="%1$@ se une a tu %2$@ a las %3$@.",
    de="%1$@ trifft dein %2$@ um %3$@.",
    it="%1$@ si congiunge al tuo %2$@ alle %3$@.",
    fr="%1$@ rejoint ton %2$@ à %3$@.",
    pt_BR="%1$@ se une ao seu %2$@ às %3$@."))

push("push.daily.opposition", "Body. %1$@ transiting body, %2$@ natal point, %3$@ time.", lit(
    en="%1$@ opposes your %2$@ at %3$@.",
    es="%1$@ se opone a tu %2$@ a las %3$@.",
    de="%1$@ steht deinem %2$@ um %3$@ gegenüber.",
    it="%1$@ si oppone al tuo %2$@ alle %3$@.",
    fr="%1$@ s'oppose à ton %2$@ à %3$@.",
    pt_BR="%1$@ se opõe ao seu %2$@ às %3$@."))

push("push.daily.square", "Body. %1$@ transiting body, %2$@ natal point, %3$@ time.", lit(
    en="%1$@ squares your %2$@ at %3$@.",
    es="%1$@ forma cuadratura con tu %2$@ a las %3$@.",
    de="%1$@ steht um %3$@ im Quadrat zu deinem %2$@.",
    it="%1$@ è in quadratura al tuo %2$@ alle %3$@.",
    fr="%1$@ est au carré de ton %2$@ à %3$@.",
    pt_BR="%1$@ faz quadratura com seu %2$@ às %3$@."))

push("push.daily.trine", "Body. %1$@ transiting body, %2$@ natal point, %3$@ time.", lit(
    en="%1$@ trines your %2$@ at %3$@.",
    es="%1$@ forma trígono con tu %2$@ a las %3$@.",
    de="%1$@ steht um %3$@ im Trigon zu deinem %2$@.",
    it="%1$@ è in trigono al tuo %2$@ alle %3$@.",
    fr="%1$@ est au trigone de ton %2$@ à %3$@.",
    pt_BR="%1$@ faz trígono com seu %2$@ às %3$@."))

push("push.daily.sextile", "Body. %1$@ transiting body, %2$@ natal point, %3$@ time.", lit(
    en="%1$@ sextiles your %2$@ at %3$@.",
    es="%1$@ forma sextil con tu %2$@ a las %3$@.",
    de="%1$@ steht um %3$@ im Sextil zu deinem %2$@.",
    it="%1$@ è in sestile al tuo %2$@ alle %3$@.",
    fr="%1$@ est au sextile de ton %2$@ à %3$@.",
    pt_BR="%1$@ faz sextil com seu %2$@ às %3$@."))

# Orb entry, slow bodies only — nothing perfects, so there is no instant to
# name and the templates take two arguments instead of three.
push("push.daily.entering.conjunction", "Orb entry. %1$@ transiting body, %2$@ natal point.", lit(
    en="%1$@ is coming to your %2$@. In orb from today.",
    es="%1$@ se acerca a tu %2$@. En orbe desde hoy.",
    de="%1$@ nähert sich deinem %2$@. Ab heute im Orbis.",
    it="%1$@ si avvicina al tuo %2$@. In orbe da oggi.",
    fr="%1$@ s'approche de ton %2$@. Dans l'orbe à partir d'aujourd'hui.",
    pt_BR="%1$@ está se aproximando do seu %2$@. Em orbe a partir de hoje."))

push("push.daily.entering.opposition", "Orb entry. %1$@ transiting body, %2$@ natal point.", lit(
    en="%1$@ is coming to oppose your %2$@. In orb from today.",
    es="%1$@ se acerca a la oposición de tu %2$@. En orbe desde hoy.",
    de="%1$@ nähert sich der Opposition zu deinem %2$@. Ab heute im Orbis.",
    it="%1$@ si avvicina all'opposizione al tuo %2$@. In orbe da oggi.",
    fr="%1$@ s'approche de l'opposition à ton %2$@. Dans l'orbe à partir d'aujourd'hui.",
    pt_BR="%1$@ está se aproximando da oposição ao seu %2$@. Em orbe a partir de hoje."))

push("push.daily.entering.square", "Orb entry. %1$@ transiting body, %2$@ natal point.", lit(
    en="%1$@ is coming to square your %2$@. In orb from today.",
    es="%1$@ se acerca a la cuadratura de tu %2$@. En orbe desde hoy.",
    de="%1$@ nähert sich dem Quadrat zu deinem %2$@. Ab heute im Orbis.",
    it="%1$@ si avvicina alla quadratura al tuo %2$@. In orbe da oggi.",
    fr="%1$@ s'approche du carré à ton %2$@. Dans l'orbe à partir d'aujourd'hui.",
    pt_BR="%1$@ está se aproximando da quadratura ao seu %2$@. Em orbe a partir de hoje."))

push("push.daily.entering.trine", "Orb entry. %1$@ transiting body, %2$@ natal point.", lit(
    en="%1$@ is coming to trine your %2$@. In orb from today.",
    es="%1$@ se acerca al trígono de tu %2$@. En orbe desde hoy.",
    de="%1$@ nähert sich dem Trigon zu deinem %2$@. Ab heute im Orbis.",
    it="%1$@ si avvicina al trigono al tuo %2$@. In orbe da oggi.",
    fr="%1$@ s'approche du trigone à ton %2$@. Dans l'orbe à partir d'aujourd'hui.",
    pt_BR="%1$@ está se aproximando do trígono ao seu %2$@. Em orbe a partir de hoje."))

push("push.daily.entering.sextile", "Orb entry. %1$@ transiting body, %2$@ natal point.", lit(
    en="%1$@ is coming to sextile your %2$@. In orb from today.",
    es="%1$@ se acerca al sextil de tu %2$@. En orbe desde hoy.",
    de="%1$@ nähert sich dem Sextil zu deinem %2$@. Ab heute im Orbis.",
    it="%1$@ si avvicina al sestile al tuo %2$@. In orbe da oggi.",
    fr="%1$@ s'approche du sextile à ton %2$@. Dans l'orbe à partir d'aujourd'hui.",
    pt_BR="%1$@ está se aproximando do sextil ao seu %2$@. Em orbe a partir de hoje."))


# ── write them out ────────────────────────────────────────────────────────

def entries(table):
    out = {}
    for key in sorted(table):
        comment, values = table[key]
        missing = [loc for loc in L if not values.get(loc)]
        assert not missing, (key, missing)
        out[key] = {
            "comment": comment,
            "extractionState": "manual",
            "localizations": {
                loc: {"stringUnit": {"state": "translated", "value": values[loc]}}
                for loc in sorted(values)
            },
        }
    return out


def write(path, strings):
    with open(path, "w") as fh:
        json.dump(
            {"sourceLanguage": "en", "version": "1.0", "strings": strings},
            fh,
            ensure_ascii=False,
            indent=2,
        )
        fh.write("\n")


write(DAILY_OUT, entries(DAILY))
print(len(DAILY), "keys ->", DAILY_OUT)

# Merge rather than overwrite. `Localizable.xcstrings` belongs to the shell and
# is maintained by hand; this script owns only the `push.` prefix inside it, and
# rewriting the file wholesale would delete sixteen keys the app draws at launch.
with open(LOCALIZABLE) as fh:
    shell = json.load(fh)

kept = {k: v for k, v in shell["strings"].items() if not k.startswith("push.")}
kept.update(entries(PUSH))
shell["strings"] = {k: kept[k] for k in sorted(kept)}
write(LOCALIZABLE, shell["strings"])
print(len(PUSH), "push keys merged into", LOCALIZABLE, f"({len(kept)} total)")
