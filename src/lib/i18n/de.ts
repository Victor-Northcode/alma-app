/**
 * German.
 *
 * "Du" throughout. Alma knows the reader's birth minute; "Sie" would put a
 * desk between them. German runs roughly 20–30% longer than English, which
 * is why the layout uses `min-width: 0` and ellipsis on every fixed-width
 * row — this is the locale that finds the overflow bugs.
 */

import type { Dictionary } from "./en";

export const de: Dictionary = {
  meta: {
    name: "Deutsch",
    htmlLang: "de",
    title: "Alma — Acht Arten, dich zu lesen. Eine Alma.",
    description:
      "Acht Traditionen lesen deine Geburtsdaten und sagen dir, wo sie übereinstimmen. Jede Berechnung ist kostenlos — du zahlst nur für die Worte.",
  },

  nav: {
    what: "Was es ist",
    eight: "Die acht",
    pricing: "Preise",
    faq: "Fragen",
    signIn: "Anmelden",
    openMenu: "Menü öffnen",
    closeMenu: "Menü schließen",
  },

  // The five controls that open the free journey share this one label; the
  // note in `en.ts` says why. What stood in the nav here was "Registrieren" —
  // literally *register*, offered by a website that mints no account at all.
  cta: {
    read: "Mich lesen — kostenlos",
    getApp: "App laden",
  },

  language: {
    label: "Sprache",
  },

  hero: {
    overline: "acht Systeme · eine Stimme",
    titleA: "Acht Arten, dich",
    titleB: "zu lesen.",
    titleAccent: "Eine Alma.",
    subShort: "Acht Traditionen lesen deine Geburtsdaten und zeigen, wo sie übereinstimmen.",
    subLong:
      "Acht Traditionen lesen deine Geburtsdaten und sagen dir, wo sie übereinstimmen. Jede Berechnung ist kostenlos — du zahlst nur für die Worte.",
    yourSky: "dein Himmel",
    quote: "Ich sage dir nicht, was passieren wird. Ich sage dir, woraus du gemacht bist.",
  },

  capture: {
    day: "Geburtstag",
    month: "Geburtsmonat",
    year: "Geburtsjahr",
    dayShort: "Tag",
    monthShort: "Monat",
    yearShort: "Jahr",
    submit: "Meine erste Einsicht zeigen — kostenlos",
    impossibleDate: "Dieses Datum gibt es nicht. Prüf den Tag.",
    pickYear: "Noch eins — wähl das Jahr.",
    unknownTime: "Ich kenne meine Geburtszeit nicht",
    searchPlace: "Wo bist du geboren?",
    noPlaces: "Kein Ort mit diesem Namen. Versuch die nächstgrößere Stadt.",
  },

  what: {
    label: "was es ist",
    lead: "Ein tiefer Blick nach innen — ohne Eile, ohne Lärm",
    systemsFigure: "8",
    systemsTitle: "verschiedene Systeme",
    systemsShort: "Jedes mit eigener Logik und eigenen blinden Flecken.",
    systemsLong:
      "Jedes mit eigener Logik und eigenen blinden Flecken. Fang an, wo du willst — keine Reihenfolge, keine Hausaufgaben.",
    freeFigure: "0 €",
    freeTitle: "für jede Berechnung",
    freeShort: "Echte Ephemeridendaten, vollständig gezeigt, für immer kostenlos.",
    freeLong: "Aus echten Ephemeridendaten berechnet, vollständig gezeigt, für immer kostenlos.",
  },

  insight: {
    label: "zwei Sekunden nach deinem Datum",
    sun: (sign: string) => `Sonne in ${sign}`,
    lifePath: (n: number | string) => `Lebenszahl ${n}`,
    fromDateAlone: "Drei Systeme, allein aus deinem Datum. Uhrzeit und Ort öffnen die anderen fünf.",
    awaiting: "Hier wird nichts geraten, also steht hier noch nichts. Gib mir ein Datum, dann füllt sich das mit deinem.",
    awaitingMeta: "wartet auf dein Datum",
    hook: "Drei Systeme kennen dich schon. Fünf weitere warten auf zwei Angaben.",
  },

  howToRead: {
    label: "wie du dich liest",
    title: "Vier kleine Regeln",
    rules: [
      ["Der Moment", "Ein Kapitel nach dem anderen, nicht sechzehn."],
      ["Der Widerspruch", "Wenn zwei Systeme streiten, kür keinen Sieger."],
      ["Die Frage", "Frag in deinen Worten; sie nennt die Position."],
      ["Die Rückkehr", "Komm in einem Monat wieder — der Text wird neu gebaut."],
    ],
    disclaimer: "*Nichts hiervon ersetzt Therapie oder ärztlichen Rat.",
  },

  eight: {
    label: "die acht",
    titleA: "Vier Fragen,",
    titleB: "acht Wege zur Antwort",
    swipe: (n: number) => `wischen · alle ${n}`,
    goTo: (i: number, n: number) => `Zu ${i} von ${n}`,
    tail:
      "Nach deiner Frage geordnet, nicht nach dem Namen der Tradition. Alle acht werden kostenlos berechnet.",
    groups: {
      "who-am-i": "wer bin ich",
      "right-now": "gerade jetzt",
      "this-year": "dieses Jahr",
      "how-we-match": "wie wir passen",
      "where-to-be": "wo sein",
      "all-of-it": "alles zusammen",
    },
    notes: {
      natal: "16 Kapitel",
      numerology: "allein aus deinem Datum",
      "birth-card": "22 Arkana",
      transits: "täglich",
      "solar-return": "braucht die Geburtszeit",
      compatibility: "eine Person hinzufügen",
      astrocartography: "braucht die Geburtszeit",
      synthesis: "9 Achsen",
    },
    names: {
      natal: "Geburtshoroskop",
      numerology: "Numerologie",
      "birth-card": "Geburtskarte",
      transits: "Transite",
      "solar-return": "Solarhoroskop",
      compatibility: "Partnerschaft",
      astrocartography: "Astrokartografie",
      synthesis: "Quersynthese",
    },
  },

  synthesis: {
    label: "nur hier",
    title: "Wo drei Systeme sich über dich einig sind",
    leadShort: "Wenn drei übereinstimmen, kommt das einem Beweis am nächsten.",
    leadLong:
      "Wenn drei übereinstimmen, kommt das einem Beweis am nächsten. Wenn zwei sich widersprechen, ist das noch nützlicher — das ist der Konflikt, den du immer wieder lebst.",
    axes: {
      Direction: "Richtung",
      Character: "Charakter",
      Mind: "Denken",
      Relationships: "Beziehungen",
      Resources: "Mittel",
      Work: "Arbeit",
      "Weak point": "Schwachstelle",
      Growth: "Wachstum",
      Rhythms: "Rhythmen",
    },
    moreShort: "Denken · Arbeit · Wachstum · Rhythmen",
    moreLong: "Denken · Arbeit · Schwachstelle · Wachstum · Rhythmen",
  },

  voice: {
    label: "Almas Stimme",
    title: "Jeder Absatz nennt eine echte Position",
    sample:
      "Saturn steht auf deinem Deszendenten bei 19° Fische. Du hast früh gelernt, dass Nähe einen Preis hat — also zahlst du ihn im Voraus, bevor jemand fragt.",
    sampleTail:
      "Deshalb beginnen deine Beziehungen so souverän und enden so erschöpft.",
    proofShort: "Verschieb deine Geburtszeit um zwei Stunden, und dieser Text ändert sich.",
    proofLong:
      "Verschieb deine Geburtszeit um zwei Stunden, und dieser Text ändert sich. Bei jedem Release automatisch geprüft.",
  },

  pricing: {
    label: "was es kostet",
    titleA: "Die Zahlen sind kostenlos.",
    titleB: "Die Worte haben einen Preis.",
    natal: "Ganzes Geburtshoroskop",
    natalShort: "Alle 16 Kapitel, eine Zahlung, für immer deins.",
    natalLong:
      "Alle 16 Kapitel auf einmal, eine Zahlung, für immer deins. Mit 15 Fragen an Alma.",
    everythingYear: "Alles, für ein Jahr",
    everythingShort: "Jedes System, jedes Kapitel und die Transite, während sie ziehen.",
    everythingLong:
      "Alle Systeme und Kapitel, tägliche Transite und Fragen an jedem Tag des Jahres.",
    renewsNote: "Verlängert sich jedes Jahr, bis du kündigst. Zwei Taps, in den Einstellungen.",
    honesty: [
      "einmal ist einmal",
      "E-Mail vor der Verlängerung",
      "Kündigen mit zwei Taps",
      "den Endpreis setzt dein Store",
    ],
    wholeArchive: "Das ganze Archiv",
    archiveNote: "Alle acht Systeme, einmal gekauft.",
  },

  faq: {
    label: "Fragen",
    showAll: "Alle Fragen →",
    items: [
      {
        q: "Ist das echte Astrologie?",
        a: "Ephemeriden der NASA JPL, gegen Referenzhoroskope auf ein Hundertstel Grad geprüft.",
        aLong:
          "Ephemeriden der NASA JPL, Placidus-Häuser, tropischer Tierkreis — gegen Referenzhoroskope auf ein Hundertstel Grad geprüft, inklusive Zeitumstellungen und polarer Breiten.",
      },
      {
        q: "Ich kenne meine Geburtszeit nicht",
        a: "Alles, was sie nicht braucht, funktioniert weiter. Was sie braucht, bleibt als nicht verfügbar markiert.",
        aLong:
          "Alles, was keine Uhrzeit braucht, funktioniert weiter: Sonne, Planeten nach Zeichen, Numerologie, deine Geburtskarte, die meisten Transite. Häuser, Solarhoroskop und Karte bleiben als nicht verfügbar markiert — wir erfinden sie nicht.",
      },
      {
        q: "Bucht ihr automatisch ab?",
        a: "Einmalig heißt einmalig. Ein Abo schreibt dir drei Tage vor jeder Verlängerung und wird mit zwei Taps gekündigt.",
        aLong:
          "Einmalkäufe sind einmalig — es gibt keine Testphase, die in eine Abbuchung übergeht. Ein Abo schreibt dir drei Tage vor jeder Verlängerung mit Datum und Betrag, an die Adresse deines Kontos oder, wenn du keine hast, an die, mit der du bezahlt hast. Der volle Preis steht vor dem Bezahlen auf dem Button, und Kündigen sind zwei Taps in den Einstellungen — danach läuft das Abo bis zum Ende des bezahlten Zeitraums.",
      },
      {
        q: "Ist das Wahrsagerei?",
        a: "Nein. Keine Ereignisvorhersagen, keine Schicksalssprache, keine Medizin- oder Geldratschläge.",
        aLong:
          "Nein. Alma beschreibt, woraus dein Horoskop besteht, nicht was passieren wird. Es gibt keine Ereignisvorhersagen, keine Schicksalssprache und nirgendwo medizinische, psychologische oder finanzielle Beratung.",
      },
      {
        q: "Warum acht Systeme?",
        a: "Weil eine Tradition sich nicht selbst prüfen kann. Acht schon.",
        aLong:
          "Weil eine Tradition sich nicht selbst prüfen kann. Wenn drei unabhängige Systeme dasselbe über dich sagen, ist das das Nächste an einem Beweis, was dieses Feld zu bieten hat — und wo zwei sich widersprechen, hast du einen echten inneren Konflikt gefunden statt einer schlechten Deutung.",
      },
      {
        q: "Was passiert mit meinen Daten?",
        a: "Deine zum Exportieren, deine zum Löschen, in den Einstellungen, jederzeit.",
        aLong:
          "Deine Geburtsdaten werden zum Rechnen und zum Schreiben verwendet, sonst nichts. Angemeldet kannst du jederzeit selbst alles exportieren oder dein Konto löschen, ohne den Support anzuschreiben. DSGVO, UK GDPR und CCPA gelten.",
      },
      {
        q: "Welche Systeme liest Alma?",
        a: "Acht: Astrologie, Numerologie, deine Geburtskarte, Astrokartografie, Transite, Solar, Kompatibilität und eine Quersynthese aus allen.",
        aLong:
          "Acht insgesamt — westliche Astrologie, Numerologie, deine Geburtskarte, Astrokartografie, Transite, das Solar und Kompatibilität — dazu eine Quersynthese, die sie gegeneinander liest und zeigt, wo sie übereinstimmen und wo nicht.",
      },
      {
        q: "Brauche ich ein Konto?",
        a: "Nein. Alles wird aus deinen Geburtsdaten berechnet. Ein Konto trägt dein Horoskop nur auf ein neues Telefon.",
        aLong:
          "Zum Lesen brauchst du kein Konto — jede Berechnung läuft aus deinen Geburtsdaten auf dem Gerät. Die Anmeldung sichert nur dein Horoskop und deine Käufe, damit sie auf ein neues Gerät mitkommen, und ist völlig optional.",
      },
    ] as ReadonlyArray<{ q: string; a: string; aLong: string }>,
  },

  final: {
    title: "Dein Himmel war die ganze Zeit da.",
    sub: "Gib ihm ein Datum. Acht Systeme antworten in unter einer Minute.",
  },

  ctaBar: {
    placeholder: "Dein Geburtsdatum",
    ready: "3 Systeme bereit · 5 warten",
    waiting: "8 Systeme · warten auf ein Datum",
  },

  footer: {
    privacy: "Datenschutz",
    terms: "AGB",
    refunds: "Rückerstattung",
    subscriptionTerms: "Abo-Bedingungen",
    imprint: "Impressum",
    cookies: "Cookies verwalten",
    withdrawal: "Widerrufsrecht (EU/UK)",
    support: "Hilfe",
    deleteAccount: "Konto löschen",
    choices: "Deine Datenschutz-Optionen",
    doNotSell: "Meine personenbezogenen Daten nicht verkaufen oder weitergeben",
    contact: "Kontakt",
    groupLegal: "Rechtliches",
    groupMoney: "Geld",
    groupCompany: "Unternehmen",
    payments:
      "Gekauft wird alles in der App, bei Apple oder Google als rechtlichem Verkäufer · Steuer enthalten, wo sie anfällt",
    disclaimer:
      "Nur zur Selbsterkenntnis. Keine medizinische, psychologische, rechtliche oder finanzielle Beratung und keine Vorhersage von Ereignissen.",
    performance:
      "Digitale Inhalte öffnen sich, sobald sie bezahlt sind. Worauf du damit verzichtest und worauf nicht, steht auf der",
    performanceLink: "Erstattungsseite",
    rights: "© 2026 Pazl LLC. Alle Rechte vorbehalten.",
  },

  months: [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
  ],

  signs: {
    Aries: "Widder", Taurus: "Stier", Gemini: "Zwillinge", Cancer: "Krebs",
    Leo: "Löwe", Virgo: "Jungfrau", Libra: "Waage", Scorpio: "Skorpion",
    Sagittarius: "Schütze", Capricorn: "Steinbock",
    Aquarius: "Wassermann", Pisces: "Fische",
  },

  app: {
    note: "Gelesen wird in der App. Alle Berechnungen bleiben dort kostenlos, genau wie hier.",
    waiting: (system: string) => `Dein ${system} wartet in der App.`,
    appleSoon: "Bald im App Store",
    googleSoon: "Bald bei Google Play",
    appStore: "Im App Store laden",
    googlePlay: "Jetzt bei Google Play",
    notYet: "Wir sind in keinem der beiden Stores. Hier stehen die Buttons, sobald es so weit ist.",
    continues: {
      chaptersLabel: "Die Kapitel",
      chapters: (all: number) =>
        `${all} Stück, geschrieben aus den Zahlen, die du gerade gesehen hast. Das erste Natal-Kapitel ist kostenlos — der Rest wird System für System gekauft oder alle acht auf einmal.`,
      secondLabel: "Die, denen ein Datum nicht reicht",
      second:
        "Kompatibilität öffnet sich, sobald du eine zweite Person hinzufügst. Astrokartografie zieht deine Linien über die Weltkarte, damit du nach einer Stadt fragen kannst, bevor du hinziehst.",
      almaLabel: "Alma selbst",
      alma:
        "Frag sie in deinen eigenen Worten nach diesem Horoskop. Jede Antwort nennt die Position, aus der sie kommt — damit du sie nachprüfen kannst.",
    },
    carryNamed: (email: string) =>
      `Dieser Himmel liegt auf ${email}. Melde dich in der App mit dieser Adresse an, dann ist er schon da — nichts doppelt einzugeben.`,
    carryAccount:
      "Dieser Himmel liegt auf deinem Konto. Melde dich in der App genauso an, dann ist er schon da — nichts doppelt einzugeben.",
    carrySent: (email: string) =>
      `Öffne den Link, den wir gerade an ${email} geschickt haben — er legt diesen Himmel auf ein Konto. Melde dich danach in der App mit derselben Adresse an, dort wartet er.`,
    carryGuest:
      "Hier ist niemand angemeldet, also bleibt dieser Himmel in diesem Browser. Die App fragt einmal erneut nach deinem Geburtsdatum — eine Minute — und jede Zahl von oben kommt genauso wieder.",
    carryUnknown:
      "Wenn du dich eben angemeldet hast, findet die App diesen Himmel über dieselbe Adresse. Wenn du es übersprungen hast, fragt sie einmal erneut nach deinem Geburtsdatum — eine Minute — und jede Zahl von oben kommt genauso wieder.",
  },

  support: {
    title: "Hilfe",
    lead: "Eine Adresse, gelesen von den Leuten, die Alma gebaut haben. Keine Ticketnummer, keine Warteschlange und niemand, der ein Skript vorliest.",

    writeTitle: "Schreib uns",
    write1:
      "Alles landet in einem Postfach. Schreib in deiner Sprache — Alma ist in sieben geschrieben und wird in allen sieben beantwortet.",
    write2:
      "Es antwortet ein Mensch, meistens am selben Tag und nie später als drei Werktage. Wenn es länger gedauert hat, ist bei uns etwas schiefgelaufen: schreib noch einmal und sag dazu, dass es das zweite Mal ist.",

    includeTitle: "Was in die Mail gehört",
    include1: "In welchem Store du gekauft hast — App Store oder Google Play.",
    include2: "Die Bestellnummer auf der Quittung des Stores, wenn es um Geld geht.",
    include3:
      "Die E-Mail-Adresse deines Alma-Kontos. Falls du dich nie angemeldet hast, stattdessen die Konto-ID aus den Einstellungen.",
    include4: "Was passiert ist, in deinen eigenen Worten. Ein Screenshot hilft und ist nie Pflicht.",
    includeNote:
      "Eines können wir nicht gebrauchen: eine Kartennummer. Deine Karte erreicht Alma nie, wir können damit keinen Kauf finden, und keine Mail von uns wird jemals danach fragen.",

    moneyTitle: "Das Geld liegt beim Store",
    money1:
      "Alma ist nicht die Verkäuferin. Auf iPhone und iPad verkauft Apple, auf Android verkauft Google. Sie ziehen das Geld ein, sie stellen die Rechnung, sie kümmern sich um die Steuer, und sie halten das Geld.",
    money2:
      "Das heißt: erstatten können wir dir nichts. Auf unserer Seite gibt es dafür keinen Knopf, und eine Hilfeseite, die etwas anderes andeutet, kostet dich einen Nachmittag. Frag den Store, der verkauft hat:",
    refundApple: "Apple — reportaproblem.apple.com, angemeldet mit dem Apple-Account, der gekauft hat.",
    refundGoogle:
      "Google Play — öffne deinen Bestellverlauf und fordere zu diesem Kauf eine Erstattung an.",
    money3:
      "Wenn der Fehler bei uns liegt — ein Text, der nie ankam, eine doppelte Abbuchung, ein durch unseren Fehler falsch gerechnetes Horoskop — schreib zuerst uns. Wir fragen für dich beim Store, du musst dafür nicht streiten, und wir sagen dir, was geantwortet wurde, auch wenn es ein Nein ist.",

    cancelTitle: "Ein Abo kündigen",
    cancel1:
      "Gehört ebenfalls dem Store, aus demselben Grund. Zwei Taps: öffne deine Abos in dem Store, in dem du gekauft hast, und kündige. Almas eigene Einstellungen haben eine Zeile, die genau diesen Bildschirm öffnet.",
    cancel2:
      "Kündigen stoppt die nächste Abbuchung. Es ist keine Erstattung des laufenden Zeitraums — der ist bezahlt und bleibt bis zu seinem letzten Tag offen.",

    dataTitle: "Dein Konto und deine Daten",
    data1:
      "Alles zu exportieren, was Alma über dich hat, und alles zu löschen, steht beides in den Einstellungen und geschieht beides sofort. Keines von beidem braucht uns, und vor keinem steht ein Angebot im Weg.",

    readingTitle: "In einem Text stimmt etwas nicht",
    reading1:
      "Sag es uns. Ein Horoskop, das nicht zu deinen eingegebenen Geburtsdaten passt, ist ein Fehler und keine Auslegungssache, und uns ist weit lieber, davon zu hören, als dass du beschließt, Alma sei eben so.",
    reading2:
      "Alma ist für Selbsterkenntnis da. Sie ist keine medizinische, juristische oder finanzielle Beratung und sagt nichts voraus. Wenn es dir schlecht geht, du in Gefahr bist oder eine Entscheidung mit Geld oder Recht triffst, sprich bitte mit einer qualifizierten Person — das können wir nicht sein, so gut der Text auch war.",

    whoTitle: "An wen du schreibst",
    who1:
      "Pazl LLC in Wyoming, USA: die Firma, die Alma betreibt. Zwischen dir und den Leuten, die sie gebaut haben, steht niemand.",

    moreTitle: "Der Rest, schriftlich",
    moreNote:
      "Diese Texte gibt es nur auf Englisch, und zwar mit Absicht: jeder einzelne muss gegen das Recht des Landes geprüft werden, in dem er gelesen wird, bevor man sich dort darauf verlassen kann — und sechs selbstsichere Übersetzungen eines ungeprüften Dokuments wären schlimmer als ein ehrliches Original.",
  },

  journey: {
    intentTitle: "Was ist gerade am lautesten in dir?",
    intentSkip: "Überspringen — ich weiß, was ich will",
    intents: {
      self: "Wer ich wirklich bin",
      shifting: "Etwas verschiebt sich und ich weiß nicht warum",
      us: "Wir — wird das gehen",
      where: "Wo ich leben sollte",
    },
    freeLabel: "deins, kostenlos, für immer",
    freeNote: "Diese Zahlen kosten nie etwas. Sie gehören dir, ob du weiterliest oder nicht.",
    calculated: "alle acht Systeme · berechnet",
    needsTimeRow: "Solarhoroskop · Karte",
    keepMySky: "Meinen Himmel behalten",
    staysFree: "Alles oben bleibt für immer kostenlos",
    dialogLabel: "Wir lernen dich kennen",
    back: "Zurück zur Startseite",
    done: "fertig",
    continueCta: "Weiter",
    orFaster: "oder schneller",
    withGoogle: "Weiter mit Google",
    nameTitle: "Wie soll ich dich nennen?",
    nameSub: "Ein Name ist kein Konto. Noch wird nichts gespeichert.",
    namePlaceholder: "Lena",
    nameAria: "Dein Name",
    dateTitle: "Wann bist du geboren?",
    dateSub: "Allein das Datum ergibt schon drei Systeme.",
    timeTitle: "Um wie viel Uhr bist du geboren?",
    timeSub:
      "Die Uhrzeit gibt Häuser, das Solar und deine Karte. Ohne sie bleiben die zu — erfinden werden wir sie nicht.",
    hourLabel: "Stunde",
    minuteLabel: "Min",
    meridiemLabel: "AM oder PM",
    lockedWithoutTime: "Häuser, Solar und Karte bleiben zu",
    placeTitle: "Wo bist du geboren?",
    placeSub: "Die Stadt genügt. Die historische Zeitzone lösen wir selbst auf.",
    placePlaceholder: "Berlin",
    buildMySky: "Meinen Himmel bauen",
    ceremony: [
      ["System 1 von 8 wird gelesen · Geburtshoroskop", "Zehn Planeten, zwölf Häuser — dein Horoskop entsteht aus echten Ephemeriden."],
      ["System 2 von 8 wird gelesen · Numerologie", "Dein Lebensweg wird zu einer Zahl, die Beweise lieber mag als Glauben."],
      ["System 3 von 8 wird gelesen · Geburtskarte", "Eines von zweiundzwanzig Arkana, allein aus dem Datum berechnet."],
      ["System 4 von 8 wird gelesen · Transite", "Wo der Himmel jetzt steht, gegen den Stand von damals."],
      ["System 5 von 8 wird gelesen · Partnerschaft", "Bleibt offen, bis du eine zweite Person hinzufügst — nichts erfunden."],
      ["System 6 von 8 wird gelesen · Solar", "Das kommende Jahr, gelesen ab der Minute, in der die Sonne zurückkehrt."],
      ["System 7 von 8 wird gelesen · Astrokartografie", "Planetenlinien über der Karte, aus deiner genauen Minute gezogen."],
      ["System 8 von 8 wird gelesen · Quersynthese", "Neun Achsen. Wo drei Traditionen übereinstimmen, geht das in deinen Kern."],
    ],
    ceremonySkip: "Zeremonie überspringen",
    authTitle: (name: string) => (name ? `Behalte das, ${name}` : "Behalte das"),
    authSub:
      "Ein Tippen, und deine acht Systeme, dein Porträt und deine Fragen bleiben deine. Nie ein Passwort.",
    legalBefore: "Mit dem Weitermachen akzeptierst du die",
    legalTerms: "AGB",
    legalAnd: "und die",
    legalPrivacy: "Datenschutzerklärung",
    legalAfter: ". Ab 16.",
    handoffTitle: "Jetzt lies dich langsam.",
    handoffSub: "Drei Regeln, die das hier tragen — mehr Einführung gibt es nie.",
    rules: [
      "Ein Kapitel nach dem anderen. Sechzehn auf einmal sind Lärm.",
      "Wenn zwei Systeme sich widersprechen, kür keinen Sieger. Genau da liegt das Material.",
      "Frag mich mit deinen eigenen Worten. Drei Fragen sind gratis.",
    ],
    ascendant: "Aszendent",
    moonPhase: "Mond",
    needsTimeTag: "Geburtszeit fehlt",
    authSkip: "Später — zeig mir einfach die App",
    placeOffline: "Das Ortsverzeichnis ist gerade nicht erreichbar. Versuch es gleich noch einmal.",
    phases: {
      "new moon": "Neumond",
      "waxing crescent": "zunehmende Sichel",
      "first quarter": "erstes Viertel",
      "waxing gibbous": "zunehmender Mond",
      "full moon": "Vollmond",
      "waning gibbous": "abnehmender Mond",
      "last quarter": "letztes Viertel",
      "waning crescent": "abnehmende Sichel",
    },
  },
};
