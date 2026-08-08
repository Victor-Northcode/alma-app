/**
 * French.
 *
 * "Tu" rather than "vous". The formal register would be the safer choice for
 * a shop; it is the wrong one for something that has your birth minute and
 * is about to tell you what you keep re-staging.
 *
 * Note the narrow no-break spaces before « ? » and « : » — French typography
 * requires them, and an ordinary space there lets the punctuation wrap onto
 * its own line.
 */

import type { Dictionary } from "./en";

export const fr: Dictionary = {
  meta: {
    name: "Français",
    htmlLang: "fr",
    title: "Alma — Huit façons de te lire toi-même. Une seule Alma.",
    description:
      "Huit traditions lisent tes données de naissance et te disent où elles s'accordent. Tous les calculs sont gratuits — tu ne paies que les mots.",
  },

  nav: {
    what: "Ce que c'est",
    eight: "Les huit",
    pricing: "Tarifs",
    faq: "Questions",
    signIn: "Se connecter",
    openMenu: "Ouvrir le menu",
    closeMenu: "Fermer le menu",
  },

  // The five controls that open the free journey share this one label; the
  // note in `en.ts` says why. What stood in the nav here was "S'inscrire" —
  // literally *sign yourself up*, offered by a website that mints no account at all.
  cta: {
    read: "Me lire — gratuitement",
  },

  language: {
    label: "Langue",
  },

  hero: {
    overline: "huit systèmes · une voix",
    titleA: "Huit façons de te",
    titleB: "lire toi-même.",
    titleAccent: "Une seule Alma.",
    subShort: "Huit traditions lisent tes données de naissance et montrent où elles s'accordent.",
    subLong:
      "Huit traditions lisent tes données de naissance et te disent où elles s'accordent. Tous les calculs sont gratuits — tu ne paies que les mots.",
    yourSky: "ton ciel",
    quote: "Je ne te dis pas ce qui va arriver. Je te dis de quoi tu es fait.",
  },

  capture: {
    day: "Jour de naissance",
    month: "Mois de naissance",
    year: "Année de naissance",
    dayShort: "Jour",
    monthShort: "Mois",
    yearShort: "Année",
    submit: "Voir ma première lecture — gratuitement",
    impossibleDate: "Cette date n'existe pas. Vérifie le jour.",
    pickYear: "Encore un — choisis l'année.",
    unknownTime: "Je ne connais pas mon heure de naissance",
    searchPlace: "Où es-tu né ?",
    noPlaces: "Aucun lieu de ce nom. Essaie la ville la plus proche.",
  },

  what: {
    label: "ce que c'est",
    lead: "Un regard profond vers l'intérieur — sans hâte ni bruit",
    systemsFigure: "8",
    systemsTitle: "systèmes différents",
    systemsShort: "Chacun avec sa logique et ses angles morts.",
    systemsLong:
      "Chacun avec sa logique et ses angles morts. Commence où tu veux — pas d'ordre, pas de devoirs.",
    freeFigure: "0 €",
    freeTitle: "pour chaque calcul",
    freeShort: "De vraies éphémérides, montrées en entier, gratuites pour toujours.",
    freeLong: "Calculé à partir de vraies éphémérides, montré en entier, gratuit pour toujours.",
  },

  insight: {
    label: "deux secondes après ta date",
    sun: (sign: string) => `Soleil en ${sign}`,
    lifePath: (n: number | string) => `Chemin de vie ${n}`,
    fromDateAlone: "Trois systèmes, à partir de ta date seule. Ton heure et ton lieu ouvrent les cinq autres.",
    awaiting: "Ici on ne devine rien, donc il n'y a encore rien. Donne-moi une date et ça se remplit du tien.",
    awaitingMeta: "en attente de ta date",
    hook: "Trois systèmes te connaissent déjà. Cinq autres attendent deux détails.",
  },

  howToRead: {
    label: "comment te lire",
    title: "Quatre petites règles",
    rules: [
      ["Le moment", "Un chapitre à la fois, pas seize."],
      ["Le désaccord", "Quand deux systèmes se disputent, ne choisis pas de gagnant."],
      ["La question", "Demande avec tes mots ; elle nomme la position."],
      ["Le retour", "Reviens dans un mois — le texte est réécrit."],
    ],
    disclaimer: "*Rien de tout cela ne remplace une thérapie ou un médecin.",
  },

  eight: {
    label: "les huit",
    titleA: "Quatre questions,",
    titleB: "huit façons de répondre",
    swipe: (n: number) => `fais glisser · les ${n}`,
    goTo: (i: number, n: number) => `Aller à ${i} sur ${n}`,
    tail:
      "Regroupés par ta question, pas par le nom de la tradition. Les huit sont calculés gratuitement.",
    groups: {
      "who-am-i": "qui je suis",
      "right-now": "en ce moment",
      "this-year": "cette année",
      "how-we-match": "comment on s'accorde",
      "where-to-be": "où être",
      "all-of-it": "tout ensemble",
    },
    notes: {
      natal: "16 chapitres",
      numerology: "à partir de ta date seule",
      "birth-card": "22 arcanes",
      transits: "chaque jour",
      "solar-return": "il faut l'heure de naissance",
      compatibility: "ajoute une personne",
      astrocartography: "il faut l'heure de naissance",
      synthesis: "9 axes",
    },
    names: {
      natal: "Thème natal",
      numerology: "Numérologie",
      "birth-card": "Carte de naissance",
      transits: "Transits",
      "solar-return": "Révolution solaire",
      compatibility: "Compatibilité",
      astrocartography: "Astrocartographie",
      synthesis: "Synthèse croisée",
    },
  },

  synthesis: {
    label: "seulement ici",
    title: "Là où trois systèmes s'accordent sur toi",
    leadShort: "Trois qui s'accordent, c'est ce qui ressemble le plus à une preuve.",
    leadLong:
      "Trois qui s'accordent, c'est ce qui ressemble le plus à une preuve. Deux qui se contredisent, c'est encore plus utile — c'est le conflit que tu continues de vivre.",
    axes: {
      Direction: "Direction",
      Character: "Caractère",
      Mind: "Esprit",
      Relationships: "Relations",
      Resources: "Ressources",
      Work: "Travail",
      "Weak point": "Point faible",
      Growth: "Croissance",
      Rhythms: "Rythmes",
    },
    moreShort: "Esprit · travail · croissance · rythmes",
    moreLong: "Esprit · travail · point faible · croissance · rythmes",
  },

  voice: {
    label: "la voix d'Alma",
    title: "Chaque paragraphe nomme une position réelle",
    sample:
      "Saturne est sur ton Descendant à 19° des Poissons. Tu as appris tôt que la proximité a un prix — alors tu le paies d'avance, avant que quiconque le demande.",
    sampleTail:
      "C'est pour cela que tes relations commencent si compétentes et finissent si fatiguées.",
    proofShort: "Décale ton heure de naissance de deux heures et ce texte change.",
    proofLong:
      "Décale ton heure de naissance de deux heures et ce texte change. Vérifié par un test automatique à chaque version.",
  },

  pricing: {
    label: "ce que ça coûte",
    titleA: "Les nombres sont gratuits.",
    titleB: "Les mots ont un prix.",
    natal: "Thème natal complet",
    natalShort: "Les 16 chapitres, un seul paiement, à toi pour toujours.",
    natalLong:
      "Les 16 chapitres d'un coup, un seul paiement, à toi pour toujours. Avec 15 questions à Alma.",
    everythingYear: "Tout, pendant un an",
    everythingShort: "Chaque système, chaque chapitre, et les transits au fil de leur course.",
    everythingLong:
      "Tous les systèmes et chapitres, les transits chaque jour, et des questions tous les jours de l'année.",
    renewsNote: "Se renouvelle chaque année jusqu'à résiliation. Deux taps, depuis les Réglages.",
    honesty: [
      "un paiement unique reste unique",
      "e-mail avant le renouvellement",
      "résiliation en deux taps",
      "le prix final est fixé par la boutique",
    ],
    wholeArchive: "L'archive entière",
    archiveNote: "Les huit systèmes, achetés une fois.",
  },

  faq: {
    label: "questions",
    showAll: "Les six questions →",
    items: [
      {
        q: "C'est de la vraie astrologie ?",
        a: "Éphémérides NASA JPL, vérifiées sur des thèmes de référence au centième de degré.",
        aLong:
          "Éphémérides NASA JPL, maisons Placidus, zodiaque tropical — vérifiées sur des thèmes de référence au centième de degré, changements d'heure et latitudes polaires compris.",
      },
      {
        q: "Je ne connais pas mon heure de naissance",
        a: "Tout ce qui n'en a pas besoin marche quand même. Ce qui en a besoin reste marqué indisponible.",
        aLong:
          "Tout ce qui n'a pas besoin d'une heure marche quand même : soleil, planètes par signe, numérologie, ta Carte de naissance, la plupart des transits. Les maisons, la révolution solaire et la carte restent marquées indisponibles — on ne les invente pas.",
      },
      {
        q: "Vous allez me prélever automatiquement ?",
        a: "Un paiement unique reste unique. Un abonnement t'écrit trois jours avant chaque renouvellement et se résilie en deux taps.",
        aLong:
          "Les achats uniques sont uniques — il n'y a pas d'essai qui se transforme en prélèvement. Un abonnement t'écrit trois jours avant chaque renouvellement avec la date et le montant, à l'adresse de ton compte ou, si tu n'en as pas, à celle avec laquelle tu as payé. Le prix complet est imprimé sur le bouton avant de payer, et résilier, c'est deux taps dans les Réglages : ensuite l'abonnement court jusqu'à la fin de la période déjà payée.",
      },
      {
        q: "C'est de la voyance ?",
        a: "Non. Aucune prédiction d'événements, aucun langage du destin, aucun conseil médical ou financier.",
        aLong:
          "Non. Alma décrit de quoi ton thème est fait, pas ce qui va arriver. Il n'y a aucune prédiction d'événements, aucun langage du destin, et aucun conseil médical, psychologique ou financier nulle part.",
      },
      {
        q: "Pourquoi huit systèmes ?",
        a: "Parce qu'une seule tradition ne peut pas se vérifier elle-même. Huit, si.",
        aLong:
          "Parce qu'une seule tradition ne peut pas se vérifier elle-même. Quand trois systèmes indépendants disent la même chose de toi, c'est ce qui ressemble le plus à une preuve dans ce domaine — et là où deux se contredisent, tu as trouvé un vrai conflit intérieur plutôt qu'une mauvaise lecture.",
      },
      {
        q: "Que deviennent mes données ?",
        a: "À toi de les exporter, à toi de les supprimer, depuis les Réglages, quand tu veux.",
        aLong:
          "Tes données de naissance servent à calculer et à écrire, rien d'autre. Connecté, tu peux tout exporter ou supprimer ton compte toi-même, à tout moment, sans écrire au support. Le RGPD, le RGPD britannique et la CCPA s'appliquent.",
      },
    ] as ReadonlyArray<{ q: string; a: string; aLong: string }>,
  },

  final: {
    title: "Ton ciel a toujours été là.",
    sub: "Donne-lui une date. Huit systèmes répondent en moins d'une minute.",
  },

  ctaBar: {
    placeholder: "Ta date de naissance",
    ready: "3 systèmes prêts · 5 en attente",
    waiting: "8 systèmes · en attente d'une date",
  },

  footer: {
    privacy: "Confidentialité",
    terms: "Conditions",
    refunds: "Remboursements",
    subscriptionTerms: "Conditions d'abonnement",
    imprint: "Mentions légales",
    cookies: "Gérer les cookies",
    withdrawal: "Droit de rétractation (UE/RU)",
    support: "Aide",
    deleteAccount: "Supprimer ton compte",
    choices: "Tes choix de confidentialité",
    doNotSell: "Ne pas vendre ni partager mes données personnelles",
    contact: "Contact",
    groupLegal: "Légal",
    groupMoney: "Argent",
    groupCompany: "Société",
    payments:
      "Rien n'est vendu sur ce site. Tout s'achète dans l'application, auprès d'Apple ou de Google en tant que vendeur légal · taxe incluse le cas échéant",
    disclaimer:
      "Pour se connaître, rien de plus. Ce n'est pas un avis médical, psychologique, juridique ou financier, et ce n'est pas une prédiction.",
    performance:
      "Le contenu numérique s'ouvre dès qu'il est payé. Ce à quoi cela fait renoncer, et ce à quoi cela ne fait pas renoncer, est sur la",
    performanceLink: "page des remboursements",
    rights: "© 2026 Pazl LLC. Tous droits réservés.",
  },

  months: [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
  ],

  signs: {
    Aries: "Bélier", Taurus: "Taureau", Gemini: "Gémeaux", Cancer: "Cancer",
    Leo: "Lion", Virgo: "Vierge", Libra: "Balance", Scorpio: "Scorpion",
    Sagittarius: "Sagittaire", Capricorn: "Capricorne",
    Aquarius: "Verseau", Pisces: "Poissons",
  },

  app: {
    note: "La lecture se passe dans l'application. Tous les calculs y restent gratuits, exactement comme ici.",
    waiting: (system: string) => `Ton ${system.toLowerCase()} t'attend dans l'application.`,
    appleSoon: "Bientôt sur l'App Store",
    googleSoon: "Bientôt sur Google Play",
    appStore: "Télécharger dans l'App Store",
    googlePlay: "Disponible sur Google Play",
    notYet: "Nous ne sommes encore sur aucun des deux stores. Les boutons seront ici le jour où nous y serons.",
    continues: {
      chaptersLabel: "Les chapitres",
      chapters: (all: number, free: number) =>
        `${all} en tout, écrits à partir des nombres que tu viens de voir. ${free} sont gratuits — un dans chaque système — et les autres s'achètent système par système, ou les huit d'un coup.`,
      secondLabel: "Ceux à qui une date ne suffit pas",
      second:
        "La compatibilité s'ouvre dès que tu ajoutes une deuxième personne. L'astrocartographie trace tes lignes sur la carte, pour que tu puisses interroger une ville avant d'y partir.",
      almaLabel: "Alma elle-même",
      alma:
        "Pose-lui tes questions sur ce thème avec tes mots. Chaque réponse nomme la position d'où elle vient, pour que tu puisses la vérifier.",
    },
    carryNamed: (email: string) =>
      `Ce ciel est sur ${email}. Connecte-toi avec cette adresse dans l'application et il y est déjà : rien à saisir deux fois.`,
    carryAccount:
      "Ce ciel est sur ton compte. Connecte-toi de la même façon dans l'application et il y est déjà : rien à saisir deux fois.",
    carrySent: (email: string) =>
      `Ouvre le lien que nous venons d'envoyer à ${email} : c'est lui qui pose ce ciel sur un compte. Connecte-toi ensuite avec la même adresse dans l'application, il t'y attend.`,
    carryGuest:
      "Personne n'est connecté ici, donc ce ciel reste dans ce navigateur. L'application redemandera ta date de naissance une fois — une minute — et tous les nombres ci-dessus reviennent identiques.",
    carryUnknown:
      "Si tu viens de te connecter, l'application retrouve ce ciel avec la même adresse. Si tu as passé l'étape, elle redemandera ta date de naissance une fois — une minute — et tous les nombres ci-dessus reviennent identiques.",
  },

  support: {
    title: "Aide",
    lead: "Une seule adresse, lue par les personnes qui ont fabriqué Alma. Pas de numéro de ticket, pas de file d'attente, personne qui récite un script.",

    writeTitle: "Écris-nous",
    write1:
      "Tout arrive dans la même boîte. Écris dans ta langue : Alma est écrite en six langues et répond dans les six.",
    write2:
      "C'est une personne qui répond, en général le jour même et jamais au-delà de trois jours ouvrés. Si c'est plus long, quelque chose a échoué de notre côté : réécris-nous, et dis que c'est la deuxième fois.",

    includeTitle: "Ce qu'il faut mettre dans le message",
    include1: "Dans quel store tu as acheté — l'App Store ou Google Play.",
    include2: "Le numéro de commande figurant sur le reçu du store, si le message parle d'argent.",
    include3:
      "L'adresse e-mail de ton compte Alma. Si tu ne t'es jamais connecté, l'identifiant de compte affiché dans les Réglages.",
    include4: "Ce qui s'est passé, avec tes mots. Une capture d'écran aide et n'est jamais obligatoire.",
    includeNote:
      "Une chose dont nous ne pouvons rien faire : un numéro de carte. Ta carte n'arrive jamais jusqu'à Alma, nous ne pouvons retrouver aucun achat avec, et aucun message de notre part ne t'en demandera jamais.",

    moneyTitle: "L'argent est chez le store",
    money1:
      "Alma n'est pas le vendeur. Sur iPhone et iPad, c'est Apple qui vend ; sur Android, c'est Google. Ce sont eux qui encaissent, qui émettent le reçu, qui s'occupent de la taxe et qui détiennent l'argent.",
    money2:
      "Ce qui veut dire que nous ne pouvons pas te rembourser nous-mêmes. Il n'y a aucun bouton de notre côté, et une page d'aide qui laisserait croire le contraire te coûterait un après-midi. Demande-le au store qui a vendu :",
    refundApple: "Apple — reportaproblem.apple.com, connecté avec l'Apple Account qui a acheté.",
    refundGoogle: "Google Play — ouvre ton historique de commandes et demande le remboursement sur cet achat.",
    money3:
      "Quand la faute est la nôtre — une lecture qui n'est jamais arrivée, un prélèvement en double, un thème faux à cause d'une erreur de chez nous — écris-nous d'abord. Nous le demandons au store à ta place, sans te faire plaider, et nous te disons ce qu'ils ont répondu même quand c'est non.",

    cancelTitle: "Résilier un abonnement",
    cancel1:
      "Cela appartient aussi au store, pour la même raison. Deux taps : ouvre tes abonnements sur le store où tu as acheté, puis résilie. Les Réglages d'Alma ont une ligne qui ouvre exactement cet écran.",
    cancel2:
      "Résilier arrête le prochain prélèvement. Ce n'est pas un remboursement de la période en cours : elle est payée et reste ouverte jusqu'à son dernier jour.",

    dataTitle: "Ton compte et tes données",
    data1:
      "Exporter tout ce qu'Alma détient sur toi et le supprimer sont tous les deux dans les Réglages, et tous les deux immédiats. Aucun des deux n'a besoin de nous, et aucun n'a une offre plantée devant lui.",

    readingTitle: "Quelque chose cloche dans une lecture",
    reading1:
      "Dis-le-nous. Un thème qui ne correspond pas aux données de naissance que tu as saisies est une erreur et non une affaire d'interprétation, et nous préférons de loin l'apprendre plutôt que de te laisser conclure qu'Alma est comme ça.",
    reading2:
      "Alma sert à se connaître. Ce n'est ni un avis médical, ni juridique, ni financier, et elle ne prédit rien. Si tu vas mal, si tu es en danger, ou si tu prends une décision où il y a de l'argent ou du droit, parle à quelqu'un de qualifié — nous ne pouvons pas l'être, aussi bonne que soit la lecture.",

    whoTitle: "À qui tu écris",
    who1:
      "Pazl LLC, dans le Wyoming, aux États-Unis : la société qui exploite Alma. Personne ne se tient entre toi et les gens qui l'ont faite.",

    moreTitle: "Le reste, par écrit",
    moreNote:
      "Ces documents sont en anglais seulement, et c'est délibéré : chacun doit être vérifié contre le droit du pays où il est lu avant qu'on puisse s'y fier, et six traductions sûres d'elles d'un document non vérifié seraient pires qu'un seul original honnête.",
  },

  journey: {
    intentTitle: "Qu'est-ce qui résonne le plus fort en toi maintenant ?",
    intentSkip: "Passer — je sais ce que je veux",
    intents: {
      self: "Qui je suis, vraiment",
      shifting: "Quelque chose bouge et je ne sais pas pourquoi",
      us: "Nous — est-ce que ça va marcher",
      where: "Où je devrais vivre",
    },
    freeLabel: "à toi, gratuit, pour toujours",
    freeNote: "Ces nombres ne coûtent jamais rien. Ils sont à toi, que tu lises la suite ou non.",
    calculated: "les huit systèmes · calculés",
    needsTimeRow: "Révolution solaire · carte",
    keepMySky: "Garder mon ciel",
    staysFree: "Tout ce qui précède reste gratuit, pour toujours",
    dialogLabel: "On fait connaissance",
    back: "Retour à la page d'accueil",
    done: "terminé",
    continueCta: "Continuer",
    orFaster: "ou plus vite",
    withGoogle: "Continuer avec Google",
    nameTitle: "Comment je t'appelle ?",
    nameSub: "Un prénom n'est pas un compte. Rien n'est encore enregistré.",
    namePlaceholder: "Camille",
    nameAria: "Ton prénom",
    dateTitle: "Quand es-tu né ?",
    dateSub: "La date seule donne déjà trois systèmes.",
    timeTitle: "À quelle heure es-tu né ?",
    timeSub:
      "L'heure donne les maisons, la révolution solaire et ta carte. Sans elle, elles restent fermées — on ne les inventera pas.",
    hourLabel: "Heure",
    minuteLabel: "Min",
    meridiemLabel: "AM ou PM",
    lockedWithoutTime: "Maisons, révolution solaire et carte restent fermées",
    placeTitle: "Où es-tu né ?",
    placeSub: "La ville suffit. Le fuseau horaire historique, on le résout nous-mêmes.",
    placePlaceholder: "Paris",
    buildMySky: "Construire mon ciel",
    ceremony: [
      ["lecture du système 1 sur 8 · thème natal", "Dix planètes, douze maisons — ton thème est tracé à partir d'éphémérides réelles."],
      ["lecture du système 2 sur 8 · numérologie", "Ton chemin de vie se réduit à un nombre qui préfère les preuves aux croyances."],
      ["lecture du système 3 sur 8 · carte de naissance", "L'un des vingt-deux arcanes, calculé à partir de la date seule."],
      ["lecture du système 4 sur 8 · transits", "Où le ciel est maintenant, face à où il était à ton départ."],
      ["lecture du système 5 sur 8 · compatibilité", "Laissé ouvert jusqu'à ce que tu ajoutes une deuxième personne — rien d'inventé."],
      ["lecture du système 6 sur 8 · révolution solaire", "L'année qui vient, lue à la minute où le Soleil revient à sa place."],
      ["lecture du système 7 sur 8 · astrocartographie", "Des lignes planétaires sur la carte, tracées depuis ta minute exacte."],
      ["lecture du système 8 sur 8 · synthèse croisée", "Neuf axes. Là où trois traditions s'accordent, ça part dans ton noyau."],
    ],
    ceremonySkip: "Passer la cérémonie",
    authTitle: (name: string) => (name ? `Garde ça, ${name}` : "Garde ça"),
    authSub:
      "Un geste et tes huit systèmes, ton portrait et tes questions restent à toi. Jamais de mot de passe.",
    legalBefore: "En continuant tu acceptes les",
    legalTerms: "Conditions",
    legalAnd: "et la",
    legalPrivacy: "Politique de confidentialité",
    legalAfter: ". 16 ans et plus.",
    handoffTitle: "Maintenant lis-toi lentement.",
    handoffSub: "Trois règles qui font tenir tout ça — la seule prise en main qu'on te donnera.",
    rules: [
      "Un chapitre à la fois. Seize d'un coup, c'est du bruit.",
      "Quand deux systèmes se contredisent, ne choisis pas de gagnant. C'est là qu'est la matière.",
      "Demande-moi avec tes mots. Trois questions sont gratuites.",
    ],
    ascendant: "Ascendant",
    moonPhase: "Lune",
    needsTimeTag: "heure de naissance manquante",
    authSkip: "Plus tard — montre-moi l'application",
    placeOffline: "Je n'arrive pas à joindre l'index des lieux. Réessaie dans un instant.",
    phases: {
      "new moon": "nouvelle lune",
      "waxing crescent": "premier croissant",
      "first quarter": "premier quartier",
      "waxing gibbous": "gibbeuse croissante",
      "full moon": "pleine lune",
      "waning gibbous": "gibbeuse décroissante",
      "last quarter": "dernier quartier",
      "waning crescent": "dernier croissant",
    },
  },
};
