#!/usr/bin/env python3
"""Write Alma/Resources/Cabinet.xcstrings.

Every string the cabinet shows, in six languages, generated rather than typed.
Most of them already exist in `src/lib/i18n/` and in the settings component's
own COPY table, so they are *extracted* from there instead of being retyped:
the two clients then say the same sentence to the same person, and a wording
that was argued over once stays argued over once. What is new to the app --
the App Store cancellation lines, the refusal to predict -- is written in the
table below, in all six languages, next to each other.

Rerunning this is the way to add a key. Editing the JSON by hand is where a
missing language hides.

    $ python3 tools/gen_cabinet_strings.py
"""

import json
import os
import re

L = ["en", "es", "de", "it", "fr", "pt-BR"]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
I18N = os.path.join(ROOT, "src", "lib", "i18n")
SETTINGS = os.path.join(ROOT, "src", "components", "cabinet", "SettingsBody.tsx")
OUT = os.path.join(os.path.dirname(__file__), "..", "Alma", "Resources", "Cabinet.xcstrings")

# -- reading TypeScript object literals --------------------------------------
# Not a parser: a scanner that pulls flat `key: "value"` pairs out of one named
# block. Function-valued entries ((n) => ...) are skipped, and their six
# versions are written out by hand below -- a handful of strings.

def strip_comments(s):
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'^\s*//.*$', '', s, flags=re.M)
    return s

def block(s, path):
    """Return the text of the object literal at a dotted path."""
    cur = s
    for part in path.split('.'):
        m = re.search(r'(?m)^\s*(?:"%s"|%s):\s*\{' % (re.escape(part), re.escape(part)), cur)
        if not m: return None
        i = m.end()-1
        depth=0
        for j in range(i, len(cur)):
            if cur[j]=='{': depth+=1
            elif cur[j]=='}':
                depth-=1
                if depth==0:
                    cur = cur[i:j+1]
                    break
        else:
            return None
    return cur

def flat(text):
    """key -> string for simple string-valued entries at depth 1."""
    out = {}
    if text is None: return out
    body = text[1:-1]
    # walk top level only
    depth=0; i=0; start=0; parts=[]
    instr=None
    while i < len(body):
        c = body[i]
        if instr:
            if c=='\\': i+=2; continue
            if c==instr: instr=None
        elif c in '"\'`': instr=c
        elif c in '{[(': depth+=1
        elif c in '}])': depth-=1
        elif c==',' and depth==0:
            parts.append(body[start:i]); start=i+1
        i+=1
    parts.append(body[start:])
    for p in parts:
        m = re.match(r'\s*(?:"([^"]+)"|([A-Za-z_][\w-]*)):\s*(.*)\s*$', p, re.S)
        if not m: continue
        key = m.group(1) or m.group(2)
        val = m.group(3).strip()
        sm = re.match(r'^"((?:[^"\\]|\\.)*)"$', val, re.S)
        if not sm:
            sm = re.match(r"^'((?:[^'\\]|\\.)*)'$", val, re.S)
        if not sm: continue
        raw = sm.group(1)
        raw = raw.replace('\\"','"').replace("\\'","'").replace('\\n','\n').replace('\\\\','\\')
        raw = re.sub(r'\s*\n\s*', ' ', raw)
        out[key] = raw
    return out


def load(locale):
    return strip_comments(open(os.path.join(I18N, locale + ".ts")).read())


DICT = {loc: load(loc) for loc in L}

_settings = strip_comments(open(SETTINGS).read())
_m = re.search(r"const COPY: Record<Locale, SettingsCopy> = \{", _settings)
_i = _m.end() - 1
_depth = 0
COPY_BLOCK = None
for _j in range(_i, len(_settings)):
    if _settings[_j] == "{":
        _depth += 1
    elif _settings[_j] == "}":
        _depth -= 1
        if _depth == 0:
            COPY_BLOCK = _settings[_i:_j + 1]
            break


def frm(section, key):
    return {loc: flat(block(DICT[loc], section))[key] for loc in L}


def syn(section, key):
    return frm(section, key)


def copy(key):
    return {loc: flat(block(COPY_BLOCK, loc))[key] for loc in L}


def lit(**kw):
    return {loc: kw[loc.replace("-", "_")] for loc in L}


T = {}   # key -> (comment, {loc: value})

def add(key, comment, values):
    T[key] = (comment, values)


P = {}   # key -> {loc: {plural category: value}}

def plural(key, forms):
    """Give a counted key its plural variations.

    Six strings in the cabinet carry a `%lld` and none of them had variations,
    so every one was ungrammatical at n=1 in all six languages: English
    rendered "1 AGREE", German "1 STIMMEN ÜBEREIN" where it has to be "stimmt",
    and "3 SIEHT NUR EINES" — a singular verb with three. They sit directly
    under the cross-system heading on Today, which is the block the App Store
    argument depends on and the first thing anybody reads, and a chart with a
    single agreement is common rather than an edge case. Six strings times six
    languages is thirty-six sentences that were wrong whenever the number was
    one.

    The `other` form is the string already written above, unchanged, so this
    only ever *adds* a case. The categories are the ones each language really
    uses: en/de/it need one|other, while es, fr and pt-BR also need `many`,
    which CLDR gives those three for large magnitudes.
    """
    assert key in T, key
    P[key] = forms


def plurals(en, es, de, it, fr, pt_BR):
    """Six singulars, matched against the plurals already in `T`."""
    return {"en": en, "es": es, "de": de, "it": it, "fr": fr, "pt-BR": pt_BR}


def correct_plural(key, **kw):
    """Replace the `other` form as well as adding a `one`.

    Needed where the string inherited from the web is itself singular — it was
    written for a chip that usually showed one and reused for every count.
    """
    T[key] = (T[key][0], {loc: kw[loc.replace("-", "_")] for loc in L})

# ── the eight, their groups and their states ────────────────────────────────
for slug in ["natal", "numerology", "birth-card", "transits", "solar-return",
             "compatibility", "astrocartography", "synthesis"]:
    add("cab.system." + slug, "Name of one of the eight systems.",
        frm("eight.names", slug))

GROUPS = {"whoAmI": "who-am-i", "rightNow": "right-now", "thisYear": "this-year",
          "howWeMatch": "how-we-match", "whereToBe": "where-to-be", "allOfIt": "all-of-it"}
for name, key in GROUPS.items():
    add("cab.group." + name, "The question a group of systems answers.",
        frm("eight.groups", key))

for name, key in [("calculated", "calculated"), ("open", "open"), ("needsTime", "needsTime"),
                  ("addPerson", "addPerson"), ("notYet", "notYet")]:
    add("cab.status." + name, "One of the five states the hub reports for a system.",
        frm("cabinet", key))

# ── shared cabinet words ────────────────────────────────────────────────────
add("cab.chapters", "Section label above a table of contents.", frm("sky", "chapters"))
add("cab.locked", "Tag on a chapter that has not been paid for.", frm("cabinet", "locked"))
add("cab.openTag", "Tag on a chapter that can be read now.", frm("cabinet", "open"))
add("cab.calculatedWord", "Word after the tally: '5/8 calculated'.", frm("cabinet", "calculated"))
add("cab.oneTimeNote", "Under a door price.", frm("cabinet", "oneTimeNote"))
add("cab.archiveNote", "The archive, in one line.", frm("cabinet", "archiveNote"))
add("cab.rebuilds", "Under the cross-synthesis row.", frm("cabinet", "rebuilds"))
add("cab.readingChart", "Wait while a system is computed.", frm("cabinet", "reading"))
add("cab.activeNow", "Section label above the transits in orb today.",
    frm("sky", "activeNow"))
add("cab.strongestAspects", "Section label above the tightest natal aspects.",
    frm("sky", "strongestAspects"))
add("cab.lunarDay", "Row label.", frm("cabinet", "lunarDay"))
add("cab.askAlma", "Row that opens the conversation.", syn("chat", "ariaLabel"))
add("cab.signIn", "Sign in.", lit(en="Sign in", es="Entrar", de="Anmelden",
                                  it="Accedi", fr="Se connecter", pt_BR="Entrar"))

add("cab.noBirthData", "Shown where a chart is needed and none has been given.",
    frm("states", "noBirthData"))
add("cab.addBirthData", "Button into the journey.", frm("states", "addBirthData"))
add("cab.needsBirthTime", "A system that cannot run without the minute.",
    frm("states", "needsBirthTime"))
add("cab.addBirthTime", "Button.", frm("states", "addBirthTime"))
add("cab.lockedNote", "What a locked chapter honestly is.", frm("states", "lockedNote"))
add("cab.writingNote", "Under the wait while a chapter is written.",
    frm("states", "writingNote"))
add("cab.refused", "Alma declined to write this chapter from the chart.",
    frm("states", "refused"))

add("cab.chapterCount", "'%lld chapters' — the size of a system.", lit(
    en="%lld chapters", es="%lld capítulos", de="%lld Kapitel",
    it="%lld capitoli", fr="%lld chapitres", pt_BR="%lld capítulos"))
add("cab.openAllChapters", "Door button. No price: the price comes from StoreKit.", lit(
    en="Open all %lld chapters", es="Abrir los %lld capítulos",
    de="Alle %lld Kapitel öffnen", it="Apri tutti i %lld capitoli",
    fr="Ouvrir les %lld chapitres", pt_BR="Abrir os %lld capítulos"))
add("cab.openSystemNamed", "Door button for a named system, without a price.", lit(
    en="Open %@", es="Abrir %@", de="%@ öffnen",
    it="Apri %@", fr="Ouvrir %@", pt_BR="Abrir %@"))

# ── cross-synthesis ─────────────────────────────────────────────────────────
add("cab.synth.title", "Headline of the cross-synthesis.", syn("synthesis", "title"))
add("cab.synth.lead", "What agreement and disagreement each mean.",
    syn("synthesis", "leadLong"))
add("cab.synth.agree", "Chip: how many systems agree on an axis.", lit(
    en="%lld agree", es="%lld coinciden", de="%lld stimmen überein",
    it="%lld concordano", fr="%lld s'accordent", pt_BR="%lld concordam"))
add("cab.synth.disagree", "Chip: how many systems disagree on an axis.", lit(
    en="%lld disagree", es="%lld discrepan", de="%lld widersprechen sich",
    it="%lld si contraddicono", fr="%lld se contredisent", pt_BR="%lld discordam"))
add("cab.synth.single", "Chip: only one system speaks to this axis.",
    syn("synthesis", "single"))
add("cab.synth.singleCount", "Chip with a count.", lit(
    en="%lld seen by one", es="%lld los ve un solo sistema", de="%lld sieht nur eines",
    it="%lld li vede un solo sistema", fr="%lld vus par un seul",
    pt_BR="%lld só um sistema vê"))
for axis in ["Direction", "Character", "Mind", "Relationships", "Resources",
             "Work", "Weak point", "Growth", "Rhythms"]:
    add("cab.axis." + axis.replace(" ", "-"), "One of the nine axes.",
        frm("synthesis.axes", axis))

# ── the engine's English enums, translated where they are shown ─────────────
for element in ["fire", "earth", "air", "water"]:
    add("cab.element." + element, "Dominant element of a chart.",
        frm("sky.elements", element))
for phase in ["new moon", "waxing crescent", "first quarter", "waxing gibbous",
              "full moon", "waning gibbous", "last quarter", "waning crescent"]:
    add("cab.phase." + phase.replace(" ", "-"), "Moon phase.", frm("sky.phases", phase))

# ── settings ────────────────────────────────────────────────────────────────
for name in ["title", "date", "time", "place", "fullName", "language", "plan",
             "everythingMonthly", "letters", "lettersNote", "exportData",
             "deleteAccount", "deleteConfirm", "privacy"]:
    add("cab.settings." + name, "Settings.", frm("settings", name))

for name in ["exporting", "exportSaved", "exportFailed", "needsAccount", "deleteWarning",
             "deleteForever", "deleteMismatch", "deleteFailed", "deleting", "keepAccount",
             "keepPlan", "guestNote", "freePlan", "freeNote", "ownedPlan", "oneTimeNote",
             "annualPlan", "cancelSubscription", "cancelWhat", "cancelling",
             "cancelledNoDate", "cancelFailed"]:
    add("cab.plan." + name, "Settings — plan, export, deletion.", copy(name))

add("cab.plan.renews", "When a subscription bills again.", lit(
    en="Renews %@ · we email you 3 days before",
    es="Se renueva el %@ · te avisamos 3 días antes",
    de="Verlängert sich am %@ · E-Mail 3 Tage vorher",
    it="Si rinnova il %@ · ti scriviamo 3 giorni prima",
    fr="Renouvellement le %@ · e-mail 3 jours avant",
    pt_BR="Renova em %@ · avisamos por e-mail 3 dias antes"))
add("cab.plan.renewsNoEmail", "The same, for an account with no address to warn.", lit(
    en="Renews %@ · add an email to be warned before it charges",
    es="Se renueva el %@ · añade un correo para que te avisemos antes del cobro",
    de="Verlängert sich am %@ · hinterlege eine E-Mail, um vorher gewarnt zu werden",
    it="Si rinnova il %@ · aggiungi un'email per essere avvisato prima dell'addebito",
    fr="Se renouvelle le %@ · ajoute un e-mail pour être prévenu avant le prélèvement",
    pt_BR="Renova em %@ · adicione um e-mail para ser avisado antes da cobrança"))
add("cab.plan.cancelled", "After a cancellation went through.", lit(
    en="Cancelled. Your plan stays open until %@.",
    es="Cancelado. Tu plan sigue abierto hasta el %@.",
    de="Gekündigt. Dein Plan bleibt bis zum %@ offen.",
    it="Disdetto. Il tuo piano resta aperto fino al %@.",
    fr="Résilié. Ton abonnement reste ouvert jusqu’au %@.",
    pt_BR="Cancelado. Seu plano continua aberto até %@."))
add("cab.plan.runsUntil", "Cancelled earlier, still paid for.", lit(
    en="Runs until %@. It will not renew.",
    es="Activo hasta el %@. No se renovará.",
    de="Läuft bis zum %@. Es verlängert sich nicht.",
    it="Attivo fino al %@. Non si rinnoverà.",
    fr="Actif jusqu’au %@. Il ne se renouvellera pas.",
    pt_BR="Ativo até %@. Não vai renovar."))
add("cab.plan.planEnded", "A plan that has run out.", lit(
    en="Your plan ended on %@.",
    es="Tu plan terminó el %@.",
    de="Dein Plan endete am %@.",
    it="Il tuo piano è finito il %@.",
    fr="Ton abonnement a pris fin le %@.",
    pt_BR="Seu plano terminou em %@."))
add("cab.merchantLine", "Fine print: who takes the money.", lit(
    en="Payments processed by %@ as merchant of record · VAT/GST included where applicable",
    es="Pagos procesados por %@ como vendedor legal · IVA incluido cuando corresponde",
    de="Zahlungen abgewickelt von %@ als rechtlichem Verkäufer · USt. enthalten, wo zutreffend",
    it="Pagamenti gestiti da %@ come venditore legale · IVA inclusa dove applicabile",
    fr="Paiements traités par %@ en tant que vendeur légal · TVA incluse le cas échéant",
    pt_BR="Pagamentos processados por %@ como vendedor legal · impostos incluídos quando aplicável"))
add("cab.disclaimer", "What Alma is not.", frm("footer", "disclaimer"))
for name in ["terms", "privacy", "refunds", "subscriptionTerms", "imprint"]:
    add("cab.legal." + name, "One of the five documents.", frm("footer", name))

# ── written new for the app ─────────────────────────────────────────────────
add("cab.readFrom", "Overline above the positions a chapter was read from.", lit(
    en="read from", es="leído en", de="gelesen aus",
    it="letto da", fr="lu dans", pt_BR="lido em"))
add("cab.notPrediction", "The refusal to predict, said on the first screen.", lit(
    en="Nothing here is a prediction. Every line names the placement it was read from.",
    es="Nada de esto es una predicción. Cada línea nombra la posición de la que se leyó.",
    de="Nichts davon ist eine Vorhersage. Jede Zeile nennt die Position, aus der sie gelesen wurde.",
    it="Niente qui è una previsione. Ogni riga nomina la posizione da cui è stata letta.",
    fr="Rien ici n'est une prédiction. Chaque ligne nomme la position dont elle est tirée.",
    pt_BR="Nada aqui é previsão. Cada linha nomeia a posição de onde foi lida."))
add("cab.freeTag", "Tag on the one chapter of a system that costs nothing.", lit(
    en="free", es="gratis", de="kostenlos", it="gratuito", fr="gratuit", pt_BR="grátis"))
add("cab.freeChapterNote", "Why one chapter opens without paying.", lit(
    en="One chapter of every system is free.",
    es="Un capítulo de cada sistema es gratis.",
    de="Ein Kapitel jedes Systems ist kostenlos.",
    it="Un capitolo di ogni sistema è gratuito.",
    fr="Un chapitre de chaque système est gratuit.",
    pt_BR="Um capítulo de cada sistema é grátis."))
add("cab.acrossSystems", "Section label над the cross-system block on Today.", lit(
    en="across your systems", es="entre tus sistemas", de="über deine Systeme hinweg",
    it="tra i tuoi sistemi", fr="à travers tes systèmes", pt_BR="entre seus sistemas"))
add("cab.manageInStore", "Opens the App Store's subscription page.", lit(
    en="Manage this subscription in the App Store",
    es="Gestiona esta suscripción en la App Store",
    de="Dieses Abo im App Store verwalten",
    it="Gestisci questo abbonamento nell'App Store",
    fr="Gérer cet abonnement dans l'App Store",
    pt_BR="Gerencie esta assinatura na App Store"))
add("cab.managedByApple", "Why cancelling happens at Apple and not here.", lit(
    en="This plan was bought in the App Store, so Apple holds the payment method and the cancellation happens there.",
    es="Este plan se compró en la App Store, así que Apple guarda el método de pago y la cancelación se hace allí.",
    de="Dieser Plan wurde im App Store gekauft — Apple verwaltet die Zahlungsmethode, und dort wird auch gekündigt.",
    it="Questo piano è stato comprato nell'App Store: Apple tiene il metodo di pagamento e la disdetta si fa lì.",
    fr="Cet abonnement a été acheté dans l'App Store : Apple détient le moyen de paiement, et la résiliation se fait là-bas.",
    pt_BR="Este plano foi comprado na App Store, então a Apple guarda a forma de pagamento e o cancelamento acontece lá."))
add("cab.exportReady", "The export finished.", lit(
    en="Your file is ready.", es="Tu archivo está listo.", de="Deine Datei ist fertig.",
    it="Il tuo file è pronto.", fr="Ton fichier est prêt.", pt_BR="Seu arquivo está pronto."))
add("cab.saveFile", "Share sheet button.", lit(
    en="Save the file", es="Guardar el archivo", de="Datei sichern",
    it="Salva il file", fr="Enregistrer le fichier", pt_BR="Salvar o arquivo"))
add("cab.exportNote", "What the export contains.", lit(
    en="Everything we hold about you, as one file.",
    es="Todo lo que guardamos sobre ti, en un solo archivo.",
    de="Alles, was wir über dich haben, in einer Datei.",
    it="Tutto quello che abbiamo su di te, in un unico file.",
    fr="Tout ce que nous détenons sur toi, en un seul fichier.",
    pt_BR="Tudo o que guardamos sobre você, em um arquivo só."))
add("cab.birthDataLabel", "Section label.", lit(
    en="birth data", es="datos de nacimiento", de="Geburtsdaten",
    it="dati di nascita", fr="données de naissance", pt_BR="dados de nascimento"))
add("cab.dataAndLegal", "Section label.", lit(
    en="data & legal", es="datos y legal", de="Daten & Recht",
    it="dati e note legali", fr="données et mentions légales", pt_BR="dados e jurídico"))
add("cab.accountLabel", "Section label.", lit(
    en="account", es="cuenta", de="Konto", it="account", fr="compte", pt_BR="conta"))
add("cab.guest", "What an account with no identity attached is called.", lit(
    en="Guest", es="Invitado", de="Gast", it="Ospite", fr="Invité", pt_BR="Convidado"))
add("cab.compatNeedsPerson", "Compatibility with nobody to compare against.", lit(
    en="Compatibility needs a second birth. Add somebody and the whole comparison is calculated free.",
    es="La compatibilidad necesita un segundo nacimiento. Añade a alguien y toda la comparación se calcula gratis.",
    de="Für die Partnerschaft braucht es eine zweite Geburt. Füge jemanden hinzu — der ganze Vergleich wird kostenlos berechnet.",
    it="L'affinità ha bisogno di una seconda nascita. Aggiungi qualcuno e tutto il confronto viene calcolato gratis.",
    fr="La compatibilité a besoin d'une deuxième naissance. Ajoute quelqu'un et toute la comparaison est calculée gratuitement.",
    pt_BR="A compatibilidade precisa de um segundo nascimento. Adicione alguém e toda a comparação é calculada de graça."))
add("cab.addAPerson", "Button that opens the people list.", lit(
    en="Add a person", es="Añadir a alguien", de="Jemanden hinzufügen",
    it="Aggiungi una persona", fr="Ajouter quelqu'un", pt_BR="Adicionar alguém"))
add("cab.notCalculated", "Label above what this chart could not answer.", lit(
    en="not calculated", es="sin calcular", de="nicht berechnet",
    it="non calcolato", fr="non calculé", pt_BR="não calculado"))
add("cab.upcoming", "Section label above transits that have not arrived yet.", lit(
    en="coming up", es="lo que viene", de="was kommt",
    it="in arrivo", fr="à venir", pt_BR="o que vem"))
add("cab.noneActive", "Nothing is in orb today, said as an answer.", lit(
    en="Nothing is in orb today. That is an answer, not an empty screen.",
    es="Hoy no hay nada en orbe. Eso es una respuesta, no una pantalla vacía.",
    de="Heute steht nichts im Orbis. Das ist eine Antwort, kein leerer Bildschirm.",
    it="Oggi non c'è niente in orbe. È una risposta, non uno schermo vuoto.",
    fr="Rien n'est dans l'orbe aujourd'hui. C'est une réponse, pas un écran vide.",
    pt_BR="Nada está em orbe hoje. Isso é uma resposta, não uma tela vazia."))
add("cab.transitWindow", "The window a transit scan covers.", lit(
    en="next %lld days", es="próximos %lld días", de="nächste %lld Tage",
    it="prossimi %lld giorni", fr="%lld prochains jours", pt_BR="próximos %lld dias"))
add("cab.advice", "Heading above the one line of advice a chapter ends with.", lit(
    en="what to do with it", es="qué hacer con esto", de="was du damit machst",
    it="cosa farne", fr="quoi en faire", pt_BR="o que fazer com isso"))
add("cab.nextChapter", "Link to the next chapter.", lit(
    en="next", es="siguiente", de="weiter", it="avanti", fr="suivant", pt_BR="próximo"))
add("cab.guestNoteApp", "A guest account, on a phone rather than in a browser.", lit(
    en="You are not signed in. Your chart lives on this phone only.",
    es="No has iniciado sesión. Tu carta solo vive en este teléfono.",
    de="Du bist nicht angemeldet. Dein Horoskop lebt nur auf diesem Telefon.",
    it="Non hai effettuato l'accesso. Il tuo tema vive solo su questo telefono.",
    fr="Tu n'es pas connecté. Ton thème ne vit que sur ce téléphone.",
    pt_BR="Você não entrou. Seu mapa vive só neste telefone."))
add("cab.unknownTime", "The birth time was never given. A first-class state.", lit(
    en="birth time unknown", es="hora de nacimiento desconocida",
    de="Geburtszeit unbekannt", it="ora di nascita sconosciuta",
    fr="heure de naissance inconnue", pt_BR="hora de nascimento desconhecida"))
add("cab.languageNote", "Which of the two languages this picker sets.", lit(
    en="This is the language Alma writes in. The app itself follows your phone.",
    es="Este es el idioma en el que escribe Alma. La app sigue el de tu teléfono.",
    de="In dieser Sprache schreibt Alma. Die App selbst folgt deinem Telefon.",
    it="È la lingua in cui scrive Alma. L'app segue quella del telefono.",
    fr="C'est la langue dans laquelle Alma écrit. L'app suit celle de ton téléphone.",
    pt_BR="É o idioma em que Alma escreve. O app segue o do seu telefone."))
add("cab.chapterProgress", "Position in a system: '3 of 16'.", lit(
    en="%1$lld of %2$lld", es="%1$lld de %2$lld", de="%1$lld von %2$lld",
    it="%1$lld di %2$lld", fr="%1$lld sur %2$lld", pt_BR="%1$lld de %2$lld"))

# ── the two sentences a store changes ───────────────────────────────────────
# The web's `settings.lettersNote` promises three letters, two of which Apple
# sends inside this app; and `plan.renews` promises a warning three days before
# a charge we neither make nor can see coming. Both are replaced rather than
# translated, because the truthful version is a different sentence and not a
# different wording.
add("cab.settings.lettersNoteStore",
    "Which letters Alma sends, on a build where Apple is the merchant.", lit(
    en="Alma sends one: your sign-in link. Apple sends the receipt for anything you buy in the app and the warning before a plan renews, because Apple takes the payment. There is no newsletter and nothing to unsubscribe from.",
    es="Alma envía uno: tu enlace de acceso. Apple envía el recibo de todo lo que compres en la app y el aviso antes de que se renueve un plan, porque Apple cobra el pago. No hay boletín ni nada de lo que darse de baja.",
    de="Alma sendet einen: deinen Anmeldelink. Apple sendet die Rechnung für alles, was du in der App kaufst, und die Warnung vor einer Verlängerung — denn Apple zieht die Zahlung ein. Es gibt keinen Newsletter und nichts abzubestellen.",
    it="Alma invia una cosa: il tuo link di accesso. Apple invia la ricevuta di tutto ciò che compri nell'app e l'avviso prima del rinnovo di un piano, perché è Apple a incassare. Non c'è newsletter e non c'è nulla da disdire.",
    fr="Alma envoie une chose : ton lien de connexion. Apple envoie le reçu de tout ce que tu achètes dans l'app et l'avertissement avant le renouvellement d'un abonnement, car c'est Apple qui encaisse. Il n'y a pas de newsletter et rien à résilier.",
    pt_BR="Alma envia uma coisa: seu link de acesso. A Apple envia o recibo de tudo o que você compra no app e o aviso antes de um plano renovar, porque é a Apple que cobra. Não há newsletter e nada para cancelar."))

add("cab.plan.renewsAtStore",
    "Renewal line for a plan bought through the App Store.", lit(
    en="Renews %@ · Apple charges it and warns you before it does",
    es="Se renueva el %@ · Apple lo cobra y te avisa antes",
    de="Verlängert sich am %@ · Apple bucht ab und warnt dich vorher",
    it="Si rinnova il %@ · Apple lo addebita e ti avvisa prima",
    fr="Renouvellement le %@ · Apple le prélève et te prévient avant",
    pt_BR="Renova em %@ · a Apple cobra e avisa você antes"))

# fix the one comment that slipped a Russian word in
T["cab.acrossSystems"] = ("Section label above the cross-system block on Today.",
                          T["cab.acrossSystems"][1])

# ── the six counted strings, given their singulars ──────────────────────────
plural("cab.synth.agree", plurals(
    en="%lld agrees", es="%lld coincide", de="%lld stimmt überein",
    it="%lld concorda", fr="%lld s'accorde", pt_BR="%lld concorda"))
plural("cab.synth.disagree", plurals(
    en="%lld disagrees", es="%lld discrepa", de="%lld widerspricht sich",
    it="%lld si contraddice", fr="%lld se contredit", pt_BR="%lld discorda"))
plural("cab.synth.singleCount", plurals(
    en="%lld seen by one", es="%lld lo ve un solo sistema", de="%lld sieht nur eines",
    it="%lld lo vede un solo sistema", fr="%lld vu par un seul",
    pt_BR="%lld só um sistema vê"))
# Two of the six inherited *plurals* are ungrammatical as well, which no amount
# of adding a singular fixes. Read on a German screen: "2 SIEHT NUR EINES" — a
# singular verb with two — because the web string was written for one and reused
# for all. The plural is corrected here rather than in `src/lib/i18n/`, which is
# the web app's to change.
correct_plural("cab.synth.singleCount", de="%lld sehen nur eines",
               it="%lld li vede un solo sistema", es="%lld los ve un solo sistema",
               fr="%lld vus par un seul", pt_BR="%lld só um sistema vê",
               en="%lld seen by one")
plural("cab.chapterCount", plurals(
    en="%lld chapter", es="%lld capítulo", de="%lld Kapitel",
    it="%lld capitolo", fr="%lld chapitre", pt_BR="%lld capítulo"))
plural("cab.openAllChapters", plurals(
    en="Open the %lld chapter", es="Abrir el %lld capítulo",
    de="Das %lld. Kapitel öffnen", it="Apri il %lld capitolo",
    fr="Ouvrir le %lld chapitre", pt_BR="Abrir o %lld capítulo"))
plural("cab.transitWindow", plurals(
    en="next %lld day", es="próximo %lld día", de="nächster %lld Tag",
    it="prossimo %lld giorno", fr="%lld prochain jour", pt_BR="próximo %lld dia"))

# `many` is a real CLDR category in three of the six and Xcode warns about a
# variation set that omits one the language uses. It takes the plural form,
# which is what those languages do at large magnitudes.
MANY = {"es", "fr", "pt-BR"}

catalog = {"sourceLanguage": "en", "version": "1.0", "strings": {}}
for key in sorted(T):
    comment, values = T[key]
    missing = [loc for loc in L if not values.get(loc)]
    assert not missing, (key, missing)

    if key in P:
        singular = P[key]
        catalog["strings"][key] = {
            "comment": comment,
            "extractionState": "manual",
            "localizations": {
                loc: {
                    "variations": {
                        "plural": {
                            category: {
                                "stringUnit": {"state": "translated", "value": text}
                            }
                            for category, text in sorted(
                                ({"one": singular[loc], "other": values[loc]}
                                 | ({"many": values[loc]} if loc in MANY else {})).items()
                            )
                        }
                    }
                }
                for loc in sorted(values)
            },
        }
        continue

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
