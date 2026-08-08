#!/usr/bin/env python3
"""Append the daily's strings to the six Android string tables.

Appends rather than rewrites: `res/values*/strings.xml` are hand-maintained
files with 280 keys in them that this feature has no business touching. Every
key it owns starts `daily_` or `push_daily_`, it removes those before writing,
and it leaves everything else exactly where it was. Running it twice is a no-op.

**Two families of key, and the difference matters at runtime.**

`daily_*` are drawn by the app through `stringResource`. `push_daily_*` are
never referenced from Kotlin at all — they are named in the *payload*, as FCM's
`body_loc_key` and `title_loc_key`, and Android resolves them by looking up a
string resource with that exact name in the app's own resources. A rename here
without a matching rename on the server produces a notification that shows
nothing, so they are grouped and commented in the XML for whoever meets them.

One key per aspect, for the reason `docs/PUSH.md §1.6` gives: `loc-args` are
substituted verbatim, and an aspect is a verb in English, a prepositional phrase
in German and a noun phrase in Italian. Its grammar belongs in the template a
translator opens, not in an argument a server substitutes.

    $ python3 tools/gen_daily_strings.py
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.normpath(os.path.join(HERE, "..", "app", "src", "main", "res"))

# Android's own directory names, which are not the locale tags the rest of the
# product uses: `pt-BR` is `values-pt-rBR` on this platform and nowhere else.
DIRS = {
    "en": "values",
    "es": "values-es",
    "de": "values-de",
    "it": "values-it",
    "fr": "values-fr",
    "pt-BR": "values-pt-rBR",
}

T = {}


def lit(en, es, de, it, fr, pt_BR):
    return {"en": en, "es": es, "de": de, "it": it, "fr": fr, "pt-BR": pt_BR}


def add(key, comment, values):
    assert key not in T, key
    T[key] = (comment, values)


# ── the setting ───────────────────────────────────────────────────────────

add("daily_title", "Section label for the notification control.", lit(
    en="The daily", es="Lo diario", de="Das Tägliche",
    it="Il quotidiano", fr="Le quotidien", pt_BR="O diário"))

add("daily_off", "Position 1 of 3.", lit(
    en="Off", es="Desactivado", de="Aus", it="Disattivato",
    fr="Désactivé", pt_BR="Desligado"))

add("daily_occasionally", "Position 2 of 3. The default for a subscriber.", lit(
    en="Occasionally", es="De vez en cuando", de="Gelegentlich",
    it="Ogni tanto", fr="De temps en temps", pt_BR="De vez em quando"))

add("daily_only_matters", "Position 3 of 3.", lit(
    en="Only what matters", es="Solo lo que importa", de="Nur was zählt",
    it="Solo ciò che conta", fr="Seulement l'essentiel", pt_BR="Só o que importa"))

add("daily_off_detail", "Under position 1. Makes Off a safe choice rather than a loss.", lit(
    en="No notifications. Today is still here whenever you open it.",
    es="Sin notificaciones. Hoy sigue aquí siempre que lo abras.",
    de="Keine Mitteilungen. Heute ist trotzdem da, wann immer du es öffnest.",
    it="Nessuna notifica. Oggi resta qui ogni volta che lo apri.",
    fr="Aucune notification. Aujourd'hui reste là chaque fois que tu l'ouvres.",
    pt_BR="Sem notificações. Hoje continua aqui sempre que você abrir."))

add("daily_occasionally_detail", "Under position 2. The measured cadence, stated plainly.", lit(
    en="About once a week, when something in your chart is actually exact.",
    es="Aproximadamente una vez por semana, cuando algo en tu carta es exacto de verdad.",
    de="Etwa einmal pro Woche, wenn in deinem Horoskop wirklich etwas exakt wird.",
    it="Circa una volta a settimana, quando qualcosa nel tuo tema diventa davvero esatto.",
    fr="Environ une fois par semaine, quand quelque chose dans ton thème devient vraiment exact.",
    pt_BR="Cerca de uma vez por semana, quando algo no seu mapa fica realmente exato."))

add("daily_only_matters_detail", "Under position 3.", lit(
    en="A few times a year. The slow ones only — the transits that last months.",
    es="Unas pocas veces al año. Solo los lentos: los tránsitos que duran meses.",
    de="Ein paar Mal im Jahr. Nur die langsamen — die Transite, die Monate dauern.",
    it="Poche volte all'anno. Solo i lenti: i transiti che durano mesi.",
    fr="Quelques fois par an. Seulement les lents — les transits qui durent des mois.",
    pt_BR="Poucas vezes por ano. Só os lentos — os trânsitos que duram meses."))

add("daily_hour", "Label on the delivery-hour row.", lit(
    en="Arrives at", es="Llega a las", de="Kommt um",
    it="Arriva alle", fr="Arrive à", pt_BR="Chega às"))

add("daily_quiet", "Quiet hours. Shown, not editable — THE-DAILY §5.2.", lit(
    en="Never between 22:00 and 08:00, in your time.",
    es="Nunca entre las 22:00 y las 08:00, en tu hora.",
    de="Nie zwischen 22:00 und 08:00, in deiner Zeit.",
    it="Mai tra le 22:00 e le 08:00, nella tua ora.",
    fr="Jamais entre 22h00 et 08h00, à ton heure.",
    pt_BR="Nunca entre 22:00 e 08:00, no seu horário."))

add("daily_timezone", "Label on the timezone row.", lit(
    en="Your time", es="Tu hora", de="Deine Zeit",
    it="La tua ora", fr="Ton heure", pt_BR="Seu horário"))

add("daily_timezone_device", "Where the zone came from.", lit(
    en="from your device", es="desde tu dispositivo", de="von deinem Gerät",
    it="dal tuo dispositivo", fr="depuis ton appareil", pt_BR="do seu aparelho"))

add("daily_timezone_birth", "Where the zone came from.", lit(
    en="from your birth data", es="desde tus datos de nacimiento",
    de="aus deinen Geburtsdaten", it="dai tuoi dati di nascita",
    fr="depuis tes données de naissance", pt_BR="dos seus dados de nascimento"))

add("daily_timezone_chosen", "Where the zone came from.", lit(
    en="you chose this", es="lo elegiste tú", de="von dir gewählt",
    it="l'hai scelta tu", fr="tu l'as choisie", pt_BR="você escolheu"))

# ── the actions on the notification ───────────────────────────────────────

add("daily_action_turn_off", "Action on every notification. One tap to Off.", lit(
    en="Turn these off", es="Desactivar esto", de="Diese abschalten",
    it="Disattiva queste", fr="Désactiver", pt_BR="Desligar isto"))

add("daily_action_quieter", "Action on every notification. Steps down a position.", lit(
    en="Fewer of these", es="Menos de estas", de="Weniger davon",
    it="Meno di queste", fr="Moins souvent", pt_BR="Menos disto"))

add("daily_action_turned_off", "Toast after the action ran, from a broadcast receiver.", lit(
    en="Turned off. Today is still here whenever you open it.",
    es="Desactivado. Hoy sigue aquí siempre que lo abras.",
    de="Abgeschaltet. Heute ist trotzdem da, wann immer du es öffnest.",
    it="Disattivato. Oggi resta qui ogni volta che lo apri.",
    fr="Désactivé. Aujourd'hui reste là chaque fois que tu l'ouvres.",
    pt_BR="Desligado. Hoje continua aqui sempre que você abrir."))

add("daily_action_quieter_done", "Toast after stepping down a position.", lit(
    en="Fewer. Only the slow ones now — a few times a year.",
    es="Menos. Ahora solo los lentos: unas pocas veces al año.",
    de="Weniger. Jetzt nur noch die langsamen — ein paar Mal im Jahr.",
    it="Meno. Ora solo i lenti: poche volte all'anno.",
    fr="Moins. Seulement les lents désormais — quelques fois par an.",
    pt_BR="Menos. Agora só os lentos — poucas vezes por ano."))

# ── the block on Today ────────────────────────────────────────────────────

add("daily_today_label", "Section label above the day's exact contact.", lit(
    en="Exact today", es="Exacto hoy", de="Heute exakt",
    it="Esatto oggi", fr="Exact aujourd'hui", pt_BR="Exato hoje"))

add("daily_today_at", "The instant it perfects. %1$s is a time of day.", lit(
    en="Exact at %1$s", es="Exacto a las %1$s", de="Exakt um %1$s",
    it="Esatto alle %1$s", fr="Exact à %1$s", pt_BR="Exato às %1$s"))

add("daily_today_since", "How long it has been live. %1$s is a date.", lit(
    en="In orb since %1$s", es="En orbe desde el %1$s", de="Im Orbis seit %1$s",
    it="In orbe dal %1$s", fr="Dans l'orbe depuis le %1$s", pt_BR="Em orbe desde %1$s"))

add("daily_today_until", "When it stops. %1$s is a date.", lit(
    en="in orb until %1$s", es="en orbe hasta el %1$s", de="im Orbis bis %1$s",
    it="in orbe fino al %1$s", fr="dans l'orbe jusqu'au %1$s", pt_BR="em orbe até %1$s"))

add("daily_empty_title", "The honest empty state. A day with nothing exact is a real answer.", lit(
    en="Nothing is exact today", es="Hoy nada es exacto", de="Heute ist nichts exakt",
    it="Oggi niente è esatto", fr="Rien n'est exact aujourd'hui", pt_BR="Nada está exato hoje"))

add("daily_empty_body", "Under the empty state, pointing at what is still live.", lit(
    en="What is still in orb is below. Nothing perfects today.",
    es="Lo que sigue en orbe está abajo. Hoy nada se hace exacto.",
    de="Was noch im Orbis steht, findest du unten. Heute wird nichts exakt.",
    it="Ciò che è ancora in orbe è qui sotto. Oggi niente diventa esatto.",
    fr="Ce qui est encore dans l'orbe est ci-dessous. Rien ne devient exact aujourd'hui.",
    pt_BR="O que ainda está em orbe está abaixo. Hoje nada se torna exato."))

# ── the ask, which is our own and comes before the system's ───────────────

add("daily_ask_title", "The invitation on Today. On Android it is the pre-prompt.", lit(
    en="Tell me the morning it happens",
    es="Avísame la mañana en que ocurra",
    de="Sag mir Bescheid an dem Morgen, an dem es passiert",
    it="Dimmelo la mattina in cui accade",
    fr="Préviens-moi le matin où cela arrive",
    pt_BR="Me avise na manhã em que acontecer"))

add("daily_ask_body", "What will arrive and how often, before POST_NOTIFICATIONS is requested.", lit(
    en="One notification, at 08:00, on the days something in your chart is exact. About once a week. Never at night, and you can turn it off from inside the notification itself.",
    es="Una notificación, a las 08:00, los días en que algo en tu carta sea exacto. Aproximadamente una vez por semana. Nunca de noche, y puedes desactivarla desde la propia notificación.",
    de="Eine Mitteilung, um 08:00, an den Tagen, an denen in deinem Horoskop etwas exakt wird. Etwa einmal pro Woche. Nie nachts, und du kannst sie direkt aus der Mitteilung heraus abschalten.",
    it="Una notifica, alle 08:00, nei giorni in cui qualcosa nel tuo tema è esatto. Circa una volta a settimana. Mai di notte, e puoi disattivarla dalla notifica stessa.",
    fr="Une notification, à 08h00, les jours où quelque chose dans ton thème est exact. Environ une fois par semaine. Jamais la nuit, et tu peux la désactiver depuis la notification elle-même.",
    pt_BR="Uma notificação, às 08:00, nos dias em que algo no seu mapa estiver exato. Cerca de uma vez por semana. Nunca à noite, e você pode desligar pela própria notificação."))

add("daily_ask_yes", "Accepts. The platform prompt comes after this and only after.", lit(
    en="Yes, tell me", es="Sí, avísame", de="Ja, sag mir Bescheid",
    it="Sì, dimmelo", fr="Oui, préviens-moi", pt_BR="Sim, me avise"))

add("daily_ask_no", "Declines, repeatably. Our question costs nothing to ask twice.", lit(
    en="Not now", es="Ahora no", de="Jetzt nicht",
    it="Non ora", fr="Pas maintenant", pt_BR="Agora não"))

# ── the honest status lines ───────────────────────────────────────────────

add("daily_status_denied", "Shown once, never nagged. PUSH.md §5.5(3).", lit(
    en="Notifications are off for Alma. You can turn them on in your phone's settings.",
    es="Las notificaciones de Alma están desactivadas. Puedes activarlas en los ajustes del teléfono.",
    de="Mitteilungen für Alma sind aus. Du kannst sie in den Einstellungen deines Telefons einschalten.",
    it="Le notifiche di Alma sono disattivate. Puoi attivarle nelle impostazioni del telefono.",
    fr="Les notifications d'Alma sont désactivées. Tu peux les activer dans les réglages de ton téléphone.",
    pt_BR="As notificações da Alma estão desligadas. Você pode ligá-las nos ajustes do seu telefone."))

add("daily_status_open_settings", "Button beside the denied line.", lit(
    en="Open settings", es="Abrir ajustes", de="Einstellungen öffnen",
    it="Apri impostazioni", fr="Ouvrir les réglages", pt_BR="Abrir ajustes"))

add("daily_status_not_delivering", "Truthful when this device has no accepted push registration.", lit(
    en="Nothing is being sent yet. This phone is not registered for notifications, so the daily lives here, on Today.",
    es="Todavía no se envía nada. Este teléfono no está registrado para notificaciones, así que lo diario vive aquí, en Hoy.",
    de="Es wird noch nichts gesendet. Dieses Telefon ist nicht für Mitteilungen registriert, also lebt das Tägliche hier, unter Heute.",
    it="Non viene ancora inviato nulla. Questo telefono non è registrato per le notifiche, quindi il quotidiano vive qui, in Oggi.",
    fr="Rien n'est encore envoyé. Ce téléphone n'est pas enregistré pour les notifications, le quotidien vit donc ici, dans Aujourd'hui.",
    pt_BR="Nada está sendo enviado ainda. Este telefone não está registrado para notificações, então o diário vive aqui, em Hoje."))

add("daily_status_registered", "Truthful when the server has accepted this device's token.", lit(
    en="This phone is registered for the daily.",
    es="Este teléfono está registrado para lo diario.",
    de="Dieses Telefon ist für das Tägliche registriert.",
    it="Questo telefono è registrato per il quotidiano.",
    fr="Ce téléphone est enregistré pour le quotidien.",
    pt_BR="Este telefone está registrado para o diário."))

add("daily_subscriber_only", "A free reader turning the switch on. Not a broken switch — a door.", lit(
    en="The daily is part of the monthly plan. Today is free, and always will be.",
    es="Lo diario forma parte del plan mensual. Hoy es gratis, y siempre lo será.",
    de="Das Tägliche gehört zum Monatsplan. Heute ist kostenlos und bleibt es.",
    it="Il quotidiano fa parte del piano mensile. Oggi è gratuito, e lo resterà.",
    fr="Le quotidien fait partie de l'abonnement mensuel. Aujourd'hui est gratuit, et le restera.",
    pt_BR="O diário faz parte do plano mensal. Hoje é gratuito, e sempre será."))

# ── the claim, checked against this person's own chart ────────────────────

add("daily_verified_label", "Label on the counted row under the setting.", lit(
    en="Exact days in the next 30",
    es="Días exactos en los próximos 30",
    de="Exakte Tage in den nächsten 30",
    it="Giorni esatti nei prossimi 30",
    fr="Jours exacts dans les 30 prochains",
    pt_BR="Dias exatos nos próximos 30"))

add("daily_verified_note", "Says where the number came from, so the cadence claim is checkable.", lit(
    en="Counted from your own chart, on this device, with the same rule the notification uses.",
    es="Contados desde tu propia carta, en este dispositivo, con la misma regla que usa la notificación.",
    de="Aus deinem eigenen Horoskop gezählt, auf diesem Gerät, mit derselben Regel wie die Mitteilung.",
    it="Contati dal tuo tema, su questo dispositivo, con la stessa regola che usa la notifica.",
    fr="Comptés depuis ton propre thème, sur cet appareil, avec la règle qu'utilise la notification.",
    pt_BR="Contados a partir do seu mapa, neste aparelho, com a mesma regra que a notificação usa."))

# ── the two channels ──────────────────────────────────────────────────────
#
# Two, never one. A channel id is permanent for an install and cannot be
# renamed or merged afterwards, so this is a one-line decision at build time
# that is very expensive to change later — and sharing a channel would let
# somebody silence the renewal notice, which the subscription-terms page
# promises in six languages and says plainly cannot be unsubscribed from, by
# silencing a horoscope. `docs/PUSH.md §6.2(5)`.

add("daily_channel_name", "Android notification channel, shown in system settings.", lit(
    en="The daily", es="Lo diario", de="Das Tägliche",
    it="Il quotidiano", fr="Le quotidien", pt_BR="O diário"))

add("daily_channel_description", "Under the channel name in system settings.", lit(
    en="The days something in your chart is exact. About once a week.",
    es="Los días en que algo en tu carta es exacto. Aproximadamente una vez por semana.",
    de="Die Tage, an denen in deinem Horoskop etwas exakt wird. Etwa einmal pro Woche.",
    it="I giorni in cui qualcosa nel tuo tema è esatto. Circa una volta a settimana.",
    fr="Les jours où quelque chose dans ton thème est exact. Environ une fois par semaine.",
    pt_BR="Os dias em que algo no seu mapa está exato. Cerca de uma vez por semana."))

add("renewal_channel_name", "The second channel. Never merged with the first.", lit(
    en="Your subscription", es="Tu suscripción", de="Dein Abonnement",
    it="Il tuo abbonamento", fr="Ton abonnement", pt_BR="Sua assinatura"))

add("renewal_channel_description", "Under the channel name. Says plainly that it is not marketing.", lit(
    en="Before a charge, and when a plan changes. Not marketing, and it cannot be unsubscribed from.",
    es="Antes de un cobro y cuando cambia un plan. No es marketing y no se puede cancelar la suscripción.",
    de="Vor einer Abbuchung und bei Änderungen am Plan. Keine Werbung, und nicht abbestellbar.",
    it="Prima di un addebito e quando un piano cambia. Non è marketing e non è disattivabile.",
    fr="Avant un prélèvement et quand un abonnement change. Ce n'est pas du marketing et on ne peut pas s'en désabonner.",
    pt_BR="Antes de uma cobrança e quando um plano muda. Não é marketing e não dá para cancelar o recebimento."))

# ── the payload keys ──────────────────────────────────────────────────────
#
# Never referenced from Kotlin. FCM's `body_loc_key` / `title_loc_key` name
# them and Android resolves them against these resources, so the server and
# this file have to agree by name.

add("push_daily_title", "FCM title_loc_key for every daily.", lit(
    en="Exact today", es="Exacto hoy", de="Heute exakt",
    it="Esatto oggi", fr="Exact aujourd'hui", pt_BR="Exato hoje"))

add("push_daily_conjunction", "Body. %1$s transiting body, %2$s natal point, %3$s time.", lit(
    en="%1$s meets your %2$s at %3$s.",
    es="%1$s se une a tu %2$s a las %3$s.",
    de="%1$s trifft dein %2$s um %3$s.",
    it="%1$s si congiunge al tuo %2$s alle %3$s.",
    fr="%1$s rejoint ton %2$s à %3$s.",
    pt_BR="%1$s se une ao seu %2$s às %3$s."))

add("push_daily_opposition", "Body. %1$s transiting body, %2$s natal point, %3$s time.", lit(
    en="%1$s opposes your %2$s at %3$s.",
    es="%1$s se opone a tu %2$s a las %3$s.",
    de="%1$s steht deinem %2$s um %3$s gegenüber.",
    it="%1$s si oppone al tuo %2$s alle %3$s.",
    fr="%1$s s'oppose à ton %2$s à %3$s.",
    pt_BR="%1$s se opõe ao seu %2$s às %3$s."))

add("push_daily_square", "Body. %1$s transiting body, %2$s natal point, %3$s time.", lit(
    en="%1$s squares your %2$s at %3$s.",
    es="%1$s forma cuadratura con tu %2$s a las %3$s.",
    de="%1$s steht um %3$s im Quadrat zu deinem %2$s.",
    it="%1$s è in quadratura al tuo %2$s alle %3$s.",
    fr="%1$s est au carré de ton %2$s à %3$s.",
    pt_BR="%1$s faz quadratura com seu %2$s às %3$s."))

add("push_daily_trine", "Body. %1$s transiting body, %2$s natal point, %3$s time.", lit(
    en="%1$s trines your %2$s at %3$s.",
    es="%1$s forma trígono con tu %2$s a las %3$s.",
    de="%1$s steht um %3$s im Trigon zu deinem %2$s.",
    it="%1$s è in trigono al tuo %2$s alle %3$s.",
    fr="%1$s est au trigone de ton %2$s à %3$s.",
    pt_BR="%1$s faz trígono com seu %2$s às %3$s."))

add("push_daily_sextile", "Body. %1$s transiting body, %2$s natal point, %3$s time.", lit(
    en="%1$s sextiles your %2$s at %3$s.",
    es="%1$s forma sextil con tu %2$s a las %3$s.",
    de="%1$s steht um %3$s im Sextil zu deinem %2$s.",
    it="%1$s è in sestile al tuo %2$s alle %3$s.",
    fr="%1$s est au sextile de ton %2$s à %3$s.",
    pt_BR="%1$s faz sextil com seu %2$s às %3$s."))

add("push_daily_entering_conjunction", "Orb entry, slow bodies. Two arguments: no instant to name.", lit(
    en="%1$s is coming to your %2$s. In orb from today.",
    es="%1$s se acerca a tu %2$s. En orbe desde hoy.",
    de="%1$s nähert sich deinem %2$s. Ab heute im Orbis.",
    it="%1$s si avvicina al tuo %2$s. In orbe da oggi.",
    fr="%1$s s'approche de ton %2$s. Dans l'orbe à partir d'aujourd'hui.",
    pt_BR="%1$s está se aproximando do seu %2$s. Em orbe a partir de hoje."))

add("push_daily_entering_opposition", "Orb entry, slow bodies.", lit(
    en="%1$s is coming to oppose your %2$s. In orb from today.",
    es="%1$s se acerca a la oposición de tu %2$s. En orbe desde hoy.",
    de="%1$s nähert sich der Opposition zu deinem %2$s. Ab heute im Orbis.",
    it="%1$s si avvicina all'opposizione al tuo %2$s. In orbe da oggi.",
    fr="%1$s s'approche de l'opposition à ton %2$s. Dans l'orbe à partir d'aujourd'hui.",
    pt_BR="%1$s está se aproximando da oposição ao seu %2$s. Em orbe a partir de hoje."))

add("push_daily_entering_square", "Orb entry, slow bodies.", lit(
    en="%1$s is coming to square your %2$s. In orb from today.",
    es="%1$s se acerca a la cuadratura de tu %2$s. En orbe desde hoy.",
    de="%1$s nähert sich dem Quadrat zu deinem %2$s. Ab heute im Orbis.",
    it="%1$s si avvicina alla quadratura al tuo %2$s. In orbe da oggi.",
    fr="%1$s s'approche du carré à ton %2$s. Dans l'orbe à partir d'aujourd'hui.",
    pt_BR="%1$s está se aproximando da quadratura ao seu %2$s. Em orbe a partir de hoje."))

add("push_daily_entering_trine", "Orb entry, slow bodies.", lit(
    en="%1$s is coming to trine your %2$s. In orb from today.",
    es="%1$s se acerca al trígono de tu %2$s. En orbe desde hoy.",
    de="%1$s nähert sich dem Trigon zu deinem %2$s. Ab heute im Orbis.",
    it="%1$s si avvicina al trigono al tuo %2$s. In orbe da oggi.",
    fr="%1$s s'approche du trigone à ton %2$s. Dans l'orbe à partir d'aujourd'hui.",
    pt_BR="%1$s está se aproximando do trígono ao seu %2$s. Em orbe a partir de hoje."))

add("push_daily_entering_sextile", "Orb entry, slow bodies.", lit(
    en="%1$s is coming to sextile your %2$s. In orb from today.",
    es="%1$s se acerca al sextil de tu %2$s. En orbe desde hoy.",
    de="%1$s nähert sich dem Sextil zu deinem %2$s. Ab heute im Orbis.",
    it="%1$s si avvicina al sestile al tuo %2$s. In orbe da oggi.",
    fr="%1$s s'approche du sextile à ton %2$s. Dans l'orbe à partir d'aujourd'hui.",
    pt_BR="%1$s está se aproximando do sextil ao seu %2$s. Em orbe a partir de hoje."))


# ── write them out ────────────────────────────────────────────────────────

def escape(value: str) -> str:
    """Android's own escaping, which catches people out in exactly two places.

    An unescaped apostrophe is a build error (`aapt2` refuses it), and `&`
    breaks the XML. Both appear in this copy — "Aujourd'hui", "l'orbe" — and the
    error message for the first names a line number in a generated file.
    """
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("'", "\\'")
        .replace('"', "\\\"")
    )


#: Every prefix this script owns.
#:
#: `renewal_channel_` is in the list and is easy to leave out — it does not
#: start `daily_`, it is about the *other* notification channel, and the first
#: version of this file missed it. A second run then produced two
#: `renewal_channel_description` entries and `aapt2` failed the whole build with
#: "Found item String/renewal_channel_description more than one time", naming a
#: generated file and no cause. Anything added below has to appear here too.
OWNED_PREFIXES = ("daily_", "push_daily_", "renewal_channel_")

_names = "|".join(OWNED_PREFIXES)
OWNED = re.compile(
    rf'\n?    <!--[^\n]*-->\n    <string name="(?:{_names})[^"]*">.*?</string>'
    rf'|\n?    <string name="(?:{_names})[^"]*">.*?</string>',
    re.S,
)

for locale, directory in DIRS.items():
    path = os.path.join(RES, directory, "strings.xml")
    with open(path, encoding="utf-8") as fh:
        source = fh.read()

    # Idempotent: everything this script owns is removed before it is written,
    # so a second run replaces rather than duplicates. A duplicated resource
    # name is a build failure, which is a merciful way to find out, but a
    # generator that only works once is not a generator.
    source = OWNED.sub("", source)

    block = ["\n", "    <!-- ── the daily ─────────────────────────────────────────────────\n",
             "         Generated by tools/gen_daily_strings.py. The push_daily_* keys are\n",
             "         never referenced from Kotlin: FCM names them in the payload and\n",
             "         Android resolves them here, so a rename needs a server change too.\n",
             "    -->\n"]
    for key in sorted(T):
        comment, values = T[key]
        missing = [loc for loc in DIRS if not values.get(loc)]
        assert not missing, (key, missing)
        if locale == "en":
            block.append(f"    <!-- {comment} -->\n")
        block.append(f'    <string name="{key}">{escape(values[locale])}</string>\n')

    out = source.replace("</resources>", "".join(block) + "</resources>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(len(T), "keys ->", path)
