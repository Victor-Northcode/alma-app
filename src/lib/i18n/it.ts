/**
 * Italian.
 *
 * "Tu" throughout. The reference chart in the design belongs to someone born
 * in Milan, so this is the locale where the fixtures and the language line
 * up — which makes it the useful one to read when checking that the copy
 * still sounds like a person.
 */

import type { Dictionary } from "./en";

export const it: Dictionary = {
  meta: {
    name: "Italiano",
    htmlLang: "it",
    title: "Alma — Otto modi di leggerti dentro. Una sola Alma.",
    description:
      "Otto tradizioni leggono i tuoi dati di nascita e ti dicono dove concordano. Ogni calcolo è gratuito — paghi solo le parole.",
  },

  nav: {
    what: "Che cos'è",
    eight: "Gli otto",
    pricing: "Prezzi",
    faq: "Domande",
    signIn: "Accedi",
    openMenu: "Apri il menu",
    closeMenu: "Chiudi il menu",
  },

  // The five controls that open the free journey share this one label; the
  // note in `en.ts` says why. What stood in the nav here was "Registrati" —
  // literally *register*, offered by a website that mints no account at all.
  cta: {
    read: "Leggermi — gratis",
    getApp: "Scarica l'app",
  },

  language: {
    label: "Lingua",
  },

  hero: {
    overline: "otto sistemi · una voce",
    titleA: "Otto modi di leggerti",
    titleB: "dentro.",
    titleAccent: "Una sola Alma.",
    subShort: "Otto tradizioni leggono i tuoi dati di nascita e mostrano dove concordano.",
    subLong:
      "Otto tradizioni leggono i tuoi dati di nascita e ti dicono dove concordano. Ogni calcolo è gratuito — paghi solo le parole.",
    yourSky: "il tuo cielo",
    quote: "Non ti dico cosa succederà. Ti dico di cosa sei fatto.",
  },

  capture: {
    day: "Giorno di nascita",
    month: "Mese di nascita",
    year: "Anno di nascita",
    dayShort: "Giorno",
    monthShort: "Mese",
    yearShort: "Anno",
    submit: "Mostrami la prima lettura — gratis",
    impossibleDate: "Questa data non esiste. Controlla il giorno.",
    pickYear: "Ancora uno — scegli l'anno.",
    unknownTime: "Non so l'ora di nascita",
    searchPlace: "Dove sei nato?",
    noPlaces: "Nessun luogo con quel nome. Prova con la città più vicina.",
  },

  what: {
    label: "che cos'è",
    lead: "Uno sguardo profondo dentro — senza fretta e senza rumore",
    systemsFigure: "8",
    systemsTitle: "sistemi diversi",
    systemsShort: "Ognuno con la sua logica e i suoi punti ciechi.",
    systemsLong:
      "Ognuno con la sua logica e i suoi punti ciechi. Comincia da dove vuoi — nessun ordine, nessun compito.",
    freeFigure: "0 €",
    freeTitle: "per ogni calcolo",
    freeShort: "Dati effemeridi reali, mostrati per intero, gratis per sempre.",
    freeLong: "Calcolato da effemeridi reali, mostrato per intero, gratis per sempre.",
  },

  insight: {
    label: "due secondi dopo la tua data",
    sun: (sign: string) => `Sole in ${sign}`,
    lifePath: (n: number | string) => `Sentiero di vita ${n}`,
    fromDateAlone: "Tre sistemi, solo dalla tua data. Ora e luogo aprono gli altri cinque.",
    awaiting: "Qui non si indovina niente, quindi ancora non c'è niente. Dammi una data e questo si riempie del tuo.",
    awaitingMeta: "in attesa della tua data",
    hook: "Tre sistemi ti conoscono già. Altri cinque aspettano due dettagli.",
  },

  howToRead: {
    label: "come leggerti",
    title: "Quattro piccole regole",
    rules: [
      ["Il momento", "Un capitolo alla volta, non sedici."],
      ["Il disaccordo", "Quando due sistemi litigano, non scegliere un vincitore."],
      ["La domanda", "Chiedi con parole tue; lei nomina la posizione."],
      ["Il ritorno", "Torna fra un mese — il testo viene riscritto."],
    ],
    disclaimer: "*Niente di tutto questo sostituisce la terapia o un medico.",
  },

  eight: {
    label: "gli otto",
    titleA: "Quattro domande,",
    titleB: "otto modi di rispondere",
    swipe: (n: number) => `scorri · tutti e ${n}`,
    goTo: (i: number, n: number) => `Vai a ${i} di ${n}`,
    tail:
      "Raggruppati per la tua domanda, non per il nome della tradizione. Tutti e otto sono calcolati gratis.",
    groups: {
      "who-am-i": "chi sono",
      "right-now": "adesso",
      "this-year": "quest'anno",
      "how-we-match": "come stiamo insieme",
      "where-to-be": "dove stare",
      "all-of-it": "tutto insieme",
    },
    notes: {
      natal: "16 capitoli",
      numerology: "solo dalla tua data",
      "birth-card": "22 arcani",
      transits: "ogni giorno",
      "solar-return": "serve l'ora di nascita",
      compatibility: "aggiungi una persona",
      astrocartography: "serve l'ora di nascita",
      synthesis: "9 assi",
    },
    names: {
      natal: "Tema natale",
      numerology: "Numerologia",
      "birth-card": "Carta di nascita",
      transits: "Transiti",
      "solar-return": "Rivoluzione solare",
      compatibility: "Affinità",
      astrocartography: "Astrocartografia",
      synthesis: "Sintesi incrociata",
    },
  },

  synthesis: {
    label: "solo qui",
    title: "Dove tre sistemi concordano su di te",
    leadShort: "Tre che concordano sono la cosa più vicina a una prova.",
    leadLong:
      "Tre che concordano sono la cosa più vicina a una prova. Due che si contraddicono servono ancora di più — è il conflitto che continui a vivere.",
    axes: {
      Direction: "Direzione",
      Character: "Carattere",
      Mind: "Mente",
      Relationships: "Relazioni",
      Resources: "Risorse",
      Work: "Lavoro",
      "Weak point": "Punto debole",
      Growth: "Crescita",
      Rhythms: "Ritmi",
    },
    moreShort: "Mente · lavoro · crescita · ritmi",
    moreLong: "Mente · lavoro · punto debole · crescita · ritmi",
  },

  voice: {
    label: "la voce di Alma",
    title: "Ogni paragrafo nomina una posizione reale",
    sample:
      "Saturno sta sul tuo Discendente a 19° dei Pesci. Hai imparato presto che la vicinanza ha un prezzo — così lo paghi in anticipo, prima che qualcuno lo chieda.",
    sampleTail:
      "Per questo le tue relazioni iniziano così competenti e finiscono così stanche.",
    proofShort: "Sposta l'ora di nascita di due ore e questo testo cambia.",
    proofLong:
      "Sposta l'ora di nascita di due ore e questo testo cambia. Verificato da un test automatico a ogni rilascio.",
  },

  pricing: {
    label: "quanto costa",
    titleA: "I numeri sono gratis.",
    titleB: "Le parole hanno un prezzo.",
    natal: "Tema natale completo",
    natalShort: "Tutti i 16 capitoli, un solo pagamento, tuoi per sempre.",
    natalLong:
      "Tutti i 16 capitoli insieme, un solo pagamento, tuoi per sempre. Con 15 domande ad Alma.",
    everythingYear: "Tutto, per un anno",
    everythingShort: "Ogni sistema, ogni capitolo e i transiti mentre si muovono.",
    everythingLong:
      "Tutti i sistemi e i capitoli, transiti quotidiani e domande ogni giorno dell'anno.",
    renewsNote: "Si rinnova ogni anno finché non disdici. Due tocchi, dalle Impostazioni.",
    honesty: [
      "una tantum è una tantum",
      "email prima del rinnovo",
      "disdetta in due tocchi",
      "il prezzo finale lo fissa il tuo store",
    ],
    wholeArchive: "L'archivio intero",
    archiveNote: "Tutti gli otto sistemi, acquistati una volta.",
  },

  faq: {
    label: "domande",
    showAll: "Tutte le domande →",
    items: [
      {
        q: "È astrologia vera?",
        a: "Effemeridi NASA JPL, verificate su temi di riferimento fino al centesimo di grado.",
        aLong:
          "Effemeridi NASA JPL, case Placidus, zodiaco tropicale — verificate su temi di riferimento fino al centesimo di grado, compresi i cambi d'ora e le latitudini polari.",
      },
      {
        q: "Non so la mia ora di nascita",
        a: "Tutto ciò che non ne ha bisogno funziona lo stesso. Ciò che ne ha bisogno resta segnato come non disponibile.",
        aLong:
          "Tutto ciò che non richiede un'ora funziona lo stesso: sole, pianeti per segno, numerologia, la tua Carta di nascita, quasi tutti i transiti. Case, rivoluzione solare e mappa restano segnate come non disponibili — non ce le inventiamo.",
      },
      {
        q: "Mi addebiterete automaticamente?",
        a: "Una tantum vuol dire una tantum. Un abbonamento ti scrive tre giorni prima di ogni rinnovo e si disdice in due tocchi.",
        aLong:
          "Gli acquisti singoli sono singoli — non c'è nessuna prova che diventa un addebito. Un abbonamento ti scrive tre giorni prima di ogni rinnovo con la data e l'importo, all'indirizzo del tuo account o, se non ne hai uno, a quello con cui hai pagato. Il prezzo pieno è stampato sul pulsante prima di pagare, e disdire sono due tocchi nelle Impostazioni: dopo, il piano resta attivo fino alla fine del periodo già pagato.",
      },
      {
        q: "È cartomanzia?",
        a: "No. Nessuna previsione di eventi, nessun linguaggio del destino, nessun consiglio medico o finanziario.",
        aLong:
          "No. Alma descrive di che cosa è fatto il tuo tema, non che cosa succederà. Non ci sono previsioni di eventi, né linguaggio del destino, né consigli medici, psicologici o finanziari da nessuna parte.",
      },
      {
        q: "Perché otto sistemi?",
        a: "Perché una tradizione sola non può verificare sé stessa. Otto sì.",
        aLong:
          "Perché una tradizione sola non può verificare sé stessa. Quando tre sistemi indipendenti dicono la stessa cosa di te, è la cosa più vicina a una prova che questo campo possa offrire — e dove due non sono d'accordo, hai trovato un conflitto interno vero e non una lettura sbagliata.",
      },
      {
        q: "Che fine fanno i miei dati?",
        a: "Tuoi da esportare, tuoi da cancellare, dalle Impostazioni, quando vuoi.",
        aLong:
          "I tuoi dati di nascita servono a calcolare e a scrivere, nient'altro. Con un account puoi esportare tutto o cancellare l'account da solo, in qualsiasi momento, senza scrivere all'assistenza. Valgono GDPR, UK GDPR e CCPA.",
      },
      {
        q: "Quali sistemi legge Alma?",
        a: "Otto: astrologia, numerologia, la tua carta di nascita, astrocartografia, transiti, rivoluzione solare, compatibilità e una sintesi incrociata di tutti.",
        aLong:
          "Otto in tutto — astrologia occidentale, numerologia, la tua carta di nascita, astrocartografia, transiti, rivoluzione solare e compatibilità — più una sintesi incrociata che li legge l'uno con l'altro e mostra dove concordano e dove no.",
      },
      {
        q: "Serve un account?",
        a: "No. Tutto si calcola dai tuoi dati di nascita. L'account porta solo il tuo tema su un altro telefono.",
        aLong:
          "Non serve un account per leggerti: ogni calcolo parte dai tuoi dati di nascita sul telefono. L'accesso salva solo il tuo tema e i tuoi acquisti perché ti seguano su un nuovo dispositivo, ed è del tutto facoltativo.",
      },
    ] as ReadonlyArray<{ q: string; a: string; aLong: string }>,
  },

  final: {
    title: "Il tuo cielo è sempre stato lì.",
    sub: "Dagli una data. Otto sistemi rispondono in meno di un minuto.",
  },

  ctaBar: {
    placeholder: "La tua data di nascita",
    ready: "3 sistemi pronti · 5 in attesa",
    waiting: "8 sistemi · aspettano una data",
  },

  footer: {
    privacy: "Privacy",
    terms: "Termini",
    refunds: "Rimborsi",
    subscriptionTerms: "Condizioni di abbonamento",
    imprint: "Note legali",
    cookies: "Gestisci i cookie",
    withdrawal: "Diritto di recesso (UE/UK)",
    support: "Assistenza",
    deleteAccount: "Elimina il tuo account",
    choices: "Le tue scelte sulla privacy",
    doNotSell: "Non vendere né condividere i miei dati personali",
    contact: "Contatti",
    groupLegal: "Legale",
    groupMoney: "Denaro",
    groupCompany: "Azienda",
    payments:
      "Si compra tutto dentro l'app, da Apple o da Google come venditore legale · imposte incluse dove si applicano",
    disclaimer:
      "Solo per conoscere sé stessi. Non è un consiglio medico, psicologico, legale o finanziario, e non prevede eventi.",
    performance:
      "I contenuti digitali si aprono appena vengono pagati. A cosa rinunci e a cosa no è scritto nella",
    performanceLink: "pagina dei rimborsi",
    rights: "© 2026 Pazl LLC. Tutti i diritti riservati.",
  },

  months: [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
  ],

  signs: {
    Aries: "Ariete", Taurus: "Toro", Gemini: "Gemelli", Cancer: "Cancro",
    Leo: "Leone", Virgo: "Vergine", Libra: "Bilancia", Scorpio: "Scorpione",
    Sagittarius: "Sagittario", Capricorn: "Capricorno",
    Aquarius: "Acquario", Pisces: "Pesci",
  },

  app: {
    note: "La lettura avviene nell'app. Tutti i calcoli restano gratuiti lì, esattamente come qui.",
    waiting: (system: string) => `Il tuo ${system.toLowerCase()} ti aspetta nell'app.`,
    appleSoon: "Presto su App Store",
    googleSoon: "Presto su Google Play",
    appStore: "Scarica su App Store",
    googlePlay: "Disponibile su Google Play",
    notYet: "Non siamo ancora in nessuno dei due store. Qui ci saranno i pulsanti il giorno in cui ci saremo.",
    continues: {
      chaptersLabel: "I capitoli",
      chapters: (all: number) =>
        `${all} in tutto, scritti dai numeri che hai appena visto. Il primo capitolo natale è gratuito, e gli altri si comprano un sistema alla volta, o tutti e otto insieme.`,
      secondLabel: "Quelli a cui una data non basta",
      second:
        "La compatibilità si apre quando aggiungi una seconda persona. L'astrocartografia traccia le tue linee sulla mappa, così puoi chiedere di una città prima di andarci a vivere.",
      almaLabel: "Alma stessa",
      alma:
        "Chiedile di questo tema con parole tue. Ogni risposta nomina la posizione da cui viene, così puoi verificarla.",
    },
    carryNamed: (email: string) =>
      `Questo cielo è su ${email}. Accedi con quell'indirizzo nell'app e lo trovi già lì: niente da inserire due volte.`,
    carryAccount:
      "Questo cielo è sul tuo account. Accedi allo stesso modo nell'app e lo trovi già lì: niente da inserire due volte.",
    carrySent: (email: string) =>
      `Apri il link che abbiamo appena mandato a ${email}: è quello che mette questo cielo su un account. Poi accedi con lo stesso indirizzo nell'app e ti aspetta lì.`,
    carryGuest:
      "Qui non è connesso nessuno, quindi questo cielo resta in questo browser. L'app ti chiederà la data di nascita un'altra volta — un minuto — e ogni numero qui sopra torna identico.",
    carryUnknown:
      "Se ti sei appena connesso, l'app trova questo cielo dallo stesso indirizzo. Se l'hai saltato, ti chiederà la data di nascita un'altra volta — un minuto — e ogni numero qui sopra torna identico.",
  },

  support: {
    title: "Assistenza",
    lead: "Un solo indirizzo, letto da chi ha costruito Alma. Nessun numero di ticket, nessuna coda e nessuno che legge un copione.",

    writeTitle: "Scrivici",
    write1:
      "Arriva tutto nella stessa casella. Scrivi nella tua lingua: Alma è scritta in sette lingue e risponde in tutte e sette.",
    write2:
      "Risponde una persona, di solito in giornata e mai oltre tre giorni lavorativi. Se è passato più tempo, qualcosa è andato storto da noi: riscrivici e dicci che è la seconda volta.",

    includeTitle: "Cosa mettere nel messaggio",
    include1: "In quale store hai comprato: App Store o Google Play.",
    include2: "Il numero d'ordine sulla ricevuta dello store, se il messaggio riguarda soldi.",
    include3:
      "L'indirizzo email del tuo account Alma. Se non hai mai fatto l'accesso, l'id account che trovi nelle Impostazioni.",
    include4: "Cos'è successo, con parole tue. Uno screenshot aiuta e non è mai obbligatorio.",
    includeNote:
      "Una cosa che non possiamo usare: il numero della carta. La tua carta non arriva mai ad Alma, non possiamo cercare un acquisto a partire da quella, e nessun messaggio nostro te lo chiederà mai.",

    moneyTitle: "I soldi li tiene lo store",
    money1:
      "Alma non è il venditore. Su iPhone e iPad vende Apple, su Android vende Google. Sono loro a incassare, a emettere la ricevuta, a occuparsi delle imposte e a tenere i soldi.",
    money2:
      "Quindi non possiamo rimborsarti noi. Da questa parte non c'è nessun pulsante da premere, e una pagina di assistenza che lasciasse intendere il contrario ti costerebbe un pomeriggio. Chiedilo allo store che te l'ha venduto:",
    refundApple: "Apple — reportaproblem.apple.com, con l'Apple Account che ha fatto l'acquisto.",
    refundGoogle: "Google Play — apri la cronologia ordini e chiedi il rimborso su quell'acquisto.",
    money3:
      "Quando la colpa è nostra — una lettura mai arrivata, un addebito doppio, un tema sbagliato per un errore nostro — scrivi prima a noi. Lo chiediamo allo store per tuo conto, senza farti discutere, e ti diciamo cosa hanno risposto anche quando la risposta è no.",

    cancelTitle: "Disdire un abbonamento",
    cancel1:
      "Anche questo è dello store, per lo stesso motivo. Due tocchi: apri i tuoi abbonamenti nello store dove hai comprato e disdici. Le Impostazioni di Alma hanno una riga che apre esattamente quella schermata.",
    cancel2:
      "Disdire ferma l'addebito successivo. Non è un rimborso del periodo in corso: quel periodo è pagato e resta aperto fino all'ultimo giorno.",

    dataTitle: "Il tuo account e i tuoi dati",
    data1:
      "Esportare tutto quello che Alma tiene su di te ed eliminarlo sono entrambi nelle Impostazioni e avvengono entrambi subito. Nessuno dei due passa da noi, e davanti a nessuno dei due c'è un'offerta.",

    readingTitle: "C'è qualcosa di sbagliato in una lettura",
    reading1:
      "Diccelo. Un tema che non corrisponde ai dati di nascita che hai inserito è un errore, non una questione di interpretazione, e preferiamo di gran lunga saperlo che lasciarti pensare che Alma sia così.",
    reading2:
      "Alma serve a conoscersi. Non è un parere medico, legale o finanziario e non prevede eventi. Se stai male, sei in pericolo o stai prendendo una decisione che riguarda soldi o leggi, parla con qualcuno di qualificato: quello non possiamo esserlo noi, per quanto buona fosse la lettura.",

    whoTitle: "A chi stai scrivendo",
    who1:
      "Pazl LLC, in Wyoming, Stati Uniti: la società che gestisce Alma. Tra te e chi l'ha costruita non c'è nessuno.",

    moreTitle: "Il resto, per iscritto",
    moreNote:
      "Sono solo in inglese, e di proposito: ognuno va verificato contro la legge del paese in cui viene letto prima di potercisi fidare, e sei traduzioni sicure di sé di un documento non verificato sarebbero peggio di un unico originale onesto.",
  },

  journey: {
    intentTitle: "Cosa ti risuona più forte adesso?",
    intentSkip: "Salta — so già cosa voglio",
    intents: {
      self: "Chi sono davvero",
      shifting: "Qualcosa si sta spostando e non so perché",
      us: "Noi — funzionerà",
      where: "Dove dovrei vivere",
    },
    freeLabel: "tuo, gratis, per sempre",
    freeNote: "Questi numeri non costano mai nulla. Sono tuoi, che tu legga oltre o no.",
    calculated: "tutti e otto i sistemi · calcolati",
    needsTimeRow: "Rivoluzione solare · mappa",
    keepMySky: "Tieni il mio cielo",
    staysFree: "Tutto quello sopra resta gratis, per sempre",
    dialogLabel: "Facciamo conoscenza",
    back: "Torna alla pagina iniziale",
    done: "fatto",
    continueCta: "Continua",
    orFaster: "oppure più veloce",
    withGoogle: "Continua con Google",
    nameTitle: "Come ti chiamo?",
    nameSub: "Un nome non è un account. Non stiamo ancora salvando niente.",
    namePlaceholder: "Giulia",
    nameAria: "Il tuo nome",
    dateTitle: "Quando sei nato?",
    dateSub: "Solo la data ti dà già tre sistemi.",
    timeTitle: "A che ora sei nato?",
    timeSub:
      "L'ora dà le case, la rivoluzione solare e la tua mappa. Senza restano chiuse — non le inventiamo.",
    hourLabel: "Ora",
    minuteLabel: "Min",
    meridiemLabel: "AM o PM",
    lockedWithoutTime: "Case, rivoluzione solare e mappa restano chiuse",
    placeTitle: "Dove sei nato?",
    placeSub: "Basta la città. Il fuso orario storico lo risolviamo noi.",
    placePlaceholder: "Milano",
    buildMySky: "Costruisci il mio cielo",
    ceremony: [
      ["leggo il sistema 1 di 8 · tema natale", "Dieci pianeti, dodici case — il tuo tema nasce da effemeridi vere."],
      ["leggo il sistema 2 di 8 · numerologia", "Il tuo sentiero di vita si riduce a un numero che preferisce le prove alla fede."],
      ["leggo il sistema 3 di 8 · carta di nascita", "Uno dei ventidue arcani, calcolato solo dalla data."],
      ["leggo il sistema 4 di 8 · transiti", "Dov'è il cielo adesso, contro dov'era quando hai iniziato."],
      ["leggo il sistema 5 di 8 · affinità", "Resta aperto finché non aggiungi una seconda persona — niente di inventato."],
      ["leggo il sistema 6 di 8 · rivoluzione solare", "L'anno che viene, letto dal minuto in cui il Sole torna al suo posto."],
      ["leggo il sistema 7 di 8 · astrocartografia", "Linee planetarie sulla mappa, tracciate dal tuo minuto esatto."],
      ["leggo il sistema 8 di 8 · sintesi incrociata", "Nove assi. Dove tre tradizioni concordano, quello va nel tuo nucleo."],
    ],
    ceremonySkip: "Salta la cerimonia",
    authTitle: (name: string) => (name ? `Tieni questo, ${name}` : "Tieni questo"),
    authSub:
      "Un tocco e i tuoi otto sistemi, il tuo ritratto e le tue domande restano tuoi. Nessuna password, mai.",
    legalBefore: "Continuando accetti i",
    legalTerms: "Termini",
    legalAnd: "e l'",
    legalPrivacy: "Informativa privacy",
    legalAfter: ". 16+.",
    handoffTitle: "Adesso leggiti con calma.",
    handoffSub: "Tre regole che fanno funzionare tutto — l'unica introduzione che ti daremo.",
    rules: [
      "Un capitolo alla volta. Sedici insieme sono rumore.",
      "Quando due sistemi litigano, non scegliere un vincitore. È lì il materiale.",
      "Chiedimi con parole tue. Tre domande sono gratis.",
    ],
    ascendant: "Ascendente",
    moonPhase: "Luna",
    needsTimeTag: "manca l'ora di nascita",
    authSkip: "Non ora — portami all'app",
    placeOffline: "Non riesco a raggiungere l'indice dei luoghi. Riprova fra un momento.",
    phases: {
      "new moon": "luna nuova",
      "waxing crescent": "luna crescente",
      "first quarter": "primo quarto",
      "waxing gibbous": "gibbosa crescente",
      "full moon": "luna piena",
      "waning gibbous": "gibbosa calante",
      "last quarter": "ultimo quarto",
      "waning crescent": "luna calante",
    },
  },
};
