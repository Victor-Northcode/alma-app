/**
 * Spanish — neutral, readable in both Spain and Latin America.
 *
 * "Tú" throughout rather than "usted": Alma speaks to one person and knows
 * their birth time, which is not a relationship that survives the formal
 * register. Vocabulary chosen to avoid regionalisms in either direction.
 */

import type { Dictionary } from "./en";

export const es: Dictionary = {
  meta: {
    name: "Español",
    htmlLang: "es",
    title: "Alma — Ocho formas de leerte. Una Alma.",
    description:
      "Ocho tradiciones leen tus datos de nacimiento y te dicen dónde coinciden. Todos los cálculos son gratis — solo pagas por las palabras.",
  },

  nav: {
    what: "Qué es",
    eight: "Los ocho",
    pricing: "Precios",
    faq: "Preguntas",
    signIn: "Entrar",
    openMenu: "Abrir menú",
    closeMenu: "Cerrar menú",
  },

  // The five controls that open the free journey share this one label; the
  // note in `en.ts` says why. What stood in the nav here was "Crear cuenta" —
  // literally *create an account*, offered by a website that mints no account at all.
  cta: {
    read: "Leerme — gratis",
    getApp: "Descargar la app",
  },

  language: {
    label: "Idioma",
  },

  hero: {
    overline: "ocho sistemas · una voz",
    titleA: "Ocho formas de leerte",
    titleB: "a ti mismo.",
    titleAccent: "Una Alma.",
    subShort: "Ocho tradiciones leen tus datos de nacimiento y muestran dónde coinciden.",
    subLong:
      "Ocho tradiciones leen tus datos de nacimiento y te dicen dónde coinciden. Todos los cálculos son gratis — solo pagas por las palabras.",
    yourSky: "tu cielo",
    quote: "No te digo lo que va a pasar. Te digo de qué estás hecho.",
  },

  capture: {
    day: "Día de nacimiento",
    month: "Mes de nacimiento",
    year: "Año de nacimiento",
    dayShort: "Día",
    monthShort: "Mes",
    yearShort: "Año",
    submit: "Ver mi primera lectura — gratis",
    impossibleDate: "Esa fecha no existe. Revisa el día.",
    pickYear: "Uno más — elige el año.",
    unknownTime: "No sé mi hora de nacimiento",
    searchPlace: "¿Dónde naciste?",
    noPlaces: "No hay ningún lugar con ese nombre. Prueba con la ciudad más cercana.",
  },

  what: {
    label: "qué es",
    lead: "Una mirada honda hacia dentro — sin prisa ni ruido",
    systemsFigure: "8",
    systemsTitle: "sistemas distintos",
    systemsShort: "Cada uno con su lógica y sus puntos ciegos.",
    systemsLong:
      "Cada uno con su lógica y sus puntos ciegos. Empieza por donde quieras — sin orden ni deberes.",
    freeFigure: "0 €",
    freeTitle: "por cada cálculo",
    freeShort: "Datos de efemérides reales, completos, gratis para siempre.",
    freeLong: "Calculado con efemérides reales, mostrado entero, gratis para siempre.",
  },

  insight: {
    label: "dos segundos después de tu fecha",
    sun: (sign: string) => `Sol en ${sign}`,
    lifePath: (n: number | string) => `Camino de vida ${n}`,
    fromDateAlone: "Tres sistemas, solo con tu fecha. Tu hora y tu lugar abren los otros cinco.",
    awaiting: "Aquí no se adivina nada, así que todavía no hay nada. Dame una fecha y esto se llena con lo tuyo.",
    awaitingMeta: "esperando tu fecha",
    hook: "Tres sistemas ya te conocen. Otros cinco esperan dos datos más.",
  },

  howToRead: {
    label: "cómo leerte",
    title: "Cuatro reglas pequeñas",
    rules: [
      ["El momento", "Un capítulo cada vez, no dieciséis."],
      ["El desacuerdo", "Cuando dos sistemas discuten, no elijas ganador."],
      ["La pregunta", "Pregunta con tus palabras; ella nombra la posición."],
      ["El regreso", "Vuelve en un mes — el texto se reescribe."],
    ],
    disclaimer: "*Nada de esto sustituye a la terapia ni al médico.",
  },

  eight: {
    label: "los ocho",
    titleA: "Cuatro preguntas,",
    titleB: "ocho maneras de responder",
    swipe: (n: number) => `desliza · los ${n}`,
    goTo: (i: number, n: number) => `Ir a ${i} de ${n}`,
    tail:
      "Agrupados por tu pregunta, no por el nombre de la tradición. Los ocho se calculan gratis.",
    groups: {
      "who-am-i": "quién soy",
      "right-now": "ahora mismo",
      "this-year": "este año",
      "how-we-match": "cómo encajamos",
      "where-to-be": "dónde estar",
      "all-of-it": "todo junto",
    },
    notes: {
      natal: "16 capítulos",
      numerology: "solo con tu fecha",
      "birth-card": "22 arcanos",
      transits: "a diario",
      "solar-return": "necesita hora de nacimiento",
      compatibility: "añade a alguien",
      astrocartography: "necesita hora de nacimiento",
      synthesis: "9 ejes",
    },
    names: {
      natal: "Carta natal",
      numerology: "Numerología",
      "birth-card": "Carta de nacimiento",
      transits: "Tránsitos",
      "solar-return": "Revolución solar",
      compatibility: "Compatibilidad",
      astrocartography: "Astrocartografía",
      synthesis: "Síntesis cruzada",
    },
  },

  synthesis: {
    label: "solo aquí",
    title: "Donde tres sistemas coinciden sobre ti",
    leadShort: "Que tres coincidan es lo más parecido a una prueba.",
    leadLong:
      "Que tres coincidan es lo más parecido a una prueba. Que dos discrepen es aún más útil — ese es el conflicto que sigues viviendo.",
    axes: {
      Direction: "Dirección",
      Character: "Carácter",
      Mind: "Mente",
      Relationships: "Relaciones",
      Resources: "Recursos",
      Work: "Trabajo",
      "Weak point": "Punto débil",
      Growth: "Crecimiento",
      Rhythms: "Ritmos",
    },
    moreShort: "Mente · trabajo · crecimiento · ritmos",
    moreLong: "Mente · trabajo · punto débil · crecimiento · ritmos",
  },

  voice: {
    label: "la voz de Alma",
    title: "Cada párrafo nombra una posición real",
    sample:
      "Saturno está sobre tu Descendente a 19° de Piscis. Aprendiste pronto que la cercanía tiene un precio — así que lo pagas por adelantado, antes de que nadie lo pida.",
    sampleTail:
      "Por eso tus relaciones empiezan tan competentes y terminan tan cansadas.",
    proofShort: "Mueve tu hora de nacimiento dos horas y este texto cambia.",
    proofLong:
      "Mueve tu hora de nacimiento dos horas y este texto cambia. Verificado por una prueba automática en cada versión.",
  },

  pricing: {
    label: "cuánto cuesta",
    titleA: "Los números son gratis.",
    titleB: "Las palabras tienen precio.",
    natal: "Carta natal completa",
    natalShort: "Los 16 capítulos, un solo pago, tuyos para siempre.",
    natalLong:
      "Los 16 capítulos de una vez, un solo pago, tuyos para siempre. Incluye 15 preguntas a Alma.",
    everythingYear: "Todo, durante un año",
    everythingShort: "Todos los sistemas, todos los capítulos y los tránsitos según se mueven.",
    everythingLong:
      "Todos los sistemas y capítulos, tránsitos diarios y preguntas todos los días del año.",
    renewsNote: "Se renueva cada año hasta que lo canceles. Dos toques, desde Ajustes.",
    honesty: [
      "un pago único es un pago único",
      "aviso por correo antes de renovar",
      "cancelas en dos toques",
      "tu tienda fija el precio final",
    ],
    wholeArchive: "El archivo completo",
    archiveNote: "Los ocho sistemas, comprados una vez.",
  },

  faq: {
    label: "preguntas",
    showAll: "Todas las preguntas →",
    items: [
      {
        q: "¿Esto es astrología de verdad?",
        a: "Efemérides de la NASA JPL, contrastadas con cartas de referencia hasta la centésima de grado.",
        aLong:
          "Efemérides de la NASA JPL, casas Placidus, zodiaco tropical — contrastadas con cartas de referencia hasta la centésima de grado, incluidos los cambios de hora y las latitudes polares.",
      },
      {
        q: "No sé mi hora de nacimiento",
        a: "Todo lo que no la necesita sigue funcionando. Lo que sí la necesita queda marcado como no disponible.",
        aLong:
          "Todo lo que no necesita hora sigue funcionando: sol, planetas por signo, numerología, tu Carta de nacimiento, casi todos los tránsitos. Las casas, la revolución solar y el mapa quedan marcados como no disponibles — no nos los vamos a inventar.",
      },
      {
        q: "¿Me vais a cobrar automáticamente?",
        a: "Un pago único es un pago único. Un plan te escribe tres días antes de cada renovación y se cancela en dos toques.",
        aLong:
          "Las compras únicas son únicas — no hay prueba que se convierta en cobro. Un plan te escribe tres días antes de cada renovación con la fecha y el importe, al correo de tu cuenta o, si no tienes, al que usaste para pagar. El precio completo está impreso en el botón antes de pagar, y cancelar son dos toques en Ajustes: después el plan dura hasta el final del periodo que ya has pagado.",
      },
      {
        q: "¿Esto es adivinación?",
        a: "No. Sin predicciones de sucesos, sin lenguaje de destino, sin consejos médicos ni de dinero.",
        aLong:
          "No. Alma describe de qué está hecha tu carta, no lo que va a pasar. No hay predicciones de sucesos, ni lenguaje de destino, ni consejo médico, psicológico o financiero en ninguna parte.",
      },
      {
        q: "¿Por qué ocho sistemas?",
        a: "Porque una sola tradición no puede comprobarse a sí misma. Ocho sí.",
        aLong:
          "Porque una sola tradición no puede comprobarse a sí misma. Cuando tres sistemas independientes dicen lo mismo de ti, es lo más parecido a una prueba que este campo puede ofrecer — y donde dos discrepan, has encontrado un conflicto interno real y no una mala lectura.",
      },
      {
        q: "¿Qué pasa con mis datos?",
        a: "Tuyos para exportar, tuyos para borrar, desde Ajustes, cuando quieras.",
        aLong:
          "Tus datos de nacimiento se usan para calcular y para escribir, nada más. Si inicias sesión, puedes exportarlo todo o borrar tu cuenta tú mismo, en cualquier momento, sin escribir a soporte. Se aplican el RGPD, el RGPD del Reino Unido y la CCPA.",
      },
      {
        q: "¿Qué sistemas lee Alma?",
        a: "Ocho: astrología, numerología, tu carta del nacimiento, astrocartografía, tránsitos, revolución solar, compatibilidad y una síntesis cruzada de todos.",
        aLong:
          "Ocho en total —astrología occidental, numerología, tu carta del nacimiento, astrocartografía, tránsitos, revolución solar y compatibilidad— más una síntesis cruzada que los lee entre sí y muestra dónde coinciden y dónde no.",
      },
      {
        q: "¿Necesito una cuenta?",
        a: "No. Todo se calcula con tus datos de nacimiento. La cuenta solo lleva tu carta a otro teléfono.",
        aLong:
          "No hace falta una cuenta para leerte: cada cálculo parte de tus datos de nacimiento en el teléfono. Iniciar sesión solo guarda tu carta y tus compras para que te acompañen en un dispositivo nuevo, y es totalmente opcional.",
      },
    ] as ReadonlyArray<{ q: string; a: string; aLong: string }>,
  },

  final: {
    title: "Tu cielo ha estado ahí todo este tiempo.",
    sub: "Dale una fecha. Ocho sistemas responden en menos de un minuto.",
  },

  ctaBar: {
    placeholder: "Tu fecha de nacimiento",
    ready: "3 sistemas listos · 5 esperando",
    waiting: "8 sistemas · esperando una fecha",
  },

  footer: {
    privacy: "Privacidad",
    terms: "Términos",
    refunds: "Reembolsos",
    subscriptionTerms: "Condiciones de suscripción",
    imprint: "Aviso legal",
    cookies: "Gestionar cookies",
    withdrawal: "Derecho de desistimiento (UE/RU)",
    support: "Ayuda",
    deleteAccount: "Eliminar tu cuenta",
    choices: "Tus opciones de privacidad",
    doNotSell: "No vender ni compartir mi información personal",
    contact: "Contacto",
    groupLegal: "Legal",
    groupMoney: "Dinero",
    groupCompany: "Empresa",
    payments:
      "Todo se compra dentro de la app, a Apple o a Google como vendedor legal · impuestos incluidos cuando corresponde. Quien compra desde Rusia paga en esta web a través de T-Bank",
    disclaimer:
      "Solo para autoconocimiento. No es consejo médico, psicológico, legal ni financiero, y no predice acontecimientos.",
    performance:
      "El contenido digital se abre en cuanto se paga. Qué renuncia eso y qué no está en la",
    performanceLink: "página de reembolsos",
    rights: "© 2026 Pazl LLC. Todos los derechos reservados.",
  },

  months: [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
  ],

  signs: {
    Aries: "Aries", Taurus: "Tauro", Gemini: "Géminis", Cancer: "Cáncer",
    Leo: "Leo", Virgo: "Virgo", Libra: "Libra", Scorpio: "Escorpio",
    Sagittarius: "Sagitario", Capricorn: "Capricornio",
    Aquarius: "Acuario", Pisces: "Piscis",
  },

  app: {
    note: "La lectura ocurre en la app. Todos los cálculos siguen siendo gratis allí, igual que aquí.",
    waiting: (system: string) => `Tu ${system.toLowerCase()} te espera en la app.`,
    appleSoon: "Pronto en la App Store",
    googleSoon: "Pronto en Google Play",
    appStore: "Descargar en la App Store",
    googlePlay: "Disponible en Google Play",
    notYet: "Todavía no estamos en ninguna de las dos tiendas. Aquí estarán los botones el día que lo estemos.",
    continues: {
      chaptersLabel: "Los capítulos",
      chapters: (all: number) =>
        `${all} en total, escritos a partir de los números que acabas de ver. El primer capítulo natal se abre gratis, y el resto se compran de sistema en sistema, o los ocho de una vez.`,
      secondLabel: "Los que necesitan algo más que una fecha",
      second:
        "La compatibilidad se abre cuando añades a una segunda persona. La astrocartografía traza tus líneas sobre el mapa, para que puedas preguntar por una ciudad antes de mudarte a ella.",
      almaLabel: "La propia Alma",
      alma:
        "Pregúntale por esta carta con tus palabras. Cada respuesta nombra la posición de la que sale, para que puedas comprobarla.",
    },
    carryNamed: (email: string) =>
      `Este cielo está en ${email}. Entra con esa dirección en la app y ya estará ahí: nada que escribir dos veces.`,
    carryAccount:
      "Este cielo está en tu cuenta. Entra igual en la app y ya estará ahí: nada que escribir dos veces.",
    carrySent: (email: string) =>
      `Abre el enlace que acabamos de enviar a ${email}: eso es lo que pone este cielo en una cuenta. Después entra con la misma dirección en la app y te estará esperando.`,
    carryGuest:
      "Aquí no hay ninguna sesión iniciada, así que este cielo se queda en este navegador. La app te pedirá tu fecha de nacimiento una vez más —un minuto— y todos los números de arriba vuelven igual.",
    carryUnknown:
      "Si acabas de entrar, la app encuentra este cielo con la misma dirección. Si te lo saltaste, te pedirá tu fecha de nacimiento una vez más —un minuto— y todos los números de arriba vuelven igual.",
  },

  support: {
    title: "Ayuda",
    lead: "Una sola dirección, leída por quienes hicimos Alma. Sin número de ticket, sin cola y sin nadie leyendo un guion.",

    writeTitle: "Escríbenos",
    write1:
      "Todo llega al mismo buzón. Escribe en tu idioma: Alma está escrita en siete y se responde en los siete.",
    write2:
      "Contesta una persona, normalmente el mismo día y nunca más tarde de tres días laborables. Si ha pasado más tiempo, algo ha fallado de nuestro lado: vuelve a escribir y dinos que es la segunda vez.",

    includeTitle: "Qué poner en el correo",
    include1: "En qué tienda compraste: App Store o Google Play.",
    include2: "El número de pedido del recibo de la tienda, si el correo va de dinero.",
    include3:
      "El correo electrónico de tu cuenta de Alma. Si nunca iniciaste sesión, el id de cuenta que aparece en Ajustes.",
    include4: "Qué pasó, con tus palabras. Una captura ayuda y nunca es obligatoria.",
    includeNote:
      "Una cosa que no nos sirve: el número de tu tarjeta. Tu tarjeta nunca llega a Alma, no podemos buscar una compra con ella y ningún correo nuestro te lo pedirá jamás.",

    moneyTitle: "El dinero lo tiene la tienda",
    money1:
      "Alma no es la vendedora. En iPhone y iPad vende Apple; en Android vende Google. Ellos cobran, ellos emiten el recibo, ellos se ocupan de los impuestos y ellos guardan el dinero.",
    money2:
      "Lo que significa que no podemos devolverte el dinero nosotros. No hay ningún botón que pulsar de este lado, y una página de ayuda que insinuara lo contrario te costaría una tarde. Pídeselo a la tienda que te lo vendió:",
    refundApple: "Apple — reportaproblem.apple.com, con la Apple Account con la que compraste.",
    refundGoogle: "Google Play — abre tu historial de pedidos y pide el reembolso en esa compra.",
    money3:
      "Cuando la culpa es nuestra —una lectura que no llegó, un cobro repetido, una carta astral mal calculada por un error nuestro— escríbenos primero. Se lo pedimos a la tienda por ti, sin obligarte a discutirlo, y te contamos qué han dicho aunque la respuesta sea que no.",

    cancelTitle: "Cancelar una suscripción",
    cancel1:
      "También es de la tienda, por la misma razón. Dos toques: abre tus suscripciones en la tienda donde compraste y cancela. Los propios Ajustes de Alma tienen una fila que te abre esa pantalla.",
    cancel2:
      "Cancelar detiene el siguiente cobro. No es un reembolso del periodo en curso: ese periodo está pagado y sigue abierto hasta su último día.",

    dataTitle: "Tu cuenta y tus datos",
    data1:
      "Exportar todo lo que Alma guarda sobre ti y borrarlo están en Ajustes, y los dos son inmediatos. Ninguno nos necesita, y ninguno tiene una oferta puesta delante.",

    readingTitle: "Algo está mal en una lectura",
    reading1:
      "Dínoslo. Una carta que no coincide con los datos de nacimiento que escribiste es un fallo, no una cuestión de interpretación, y preferimos mil veces enterarnos a que decidas que Alma es así.",
    reading2:
      "Alma es para conocerte. No es consejo médico, legal ni financiero, y no predice acontecimientos. Si estás mal, en peligro, o tomando una decisión con dinero o con leyes de por medio, habla con alguien cualificado: eso no podemos serlo nosotros, por buena que fuera la lectura.",

    whoTitle: "A quién escribes",
    who1:
      "Pazl LLC, en Wyoming, Estados Unidos: la empresa que opera Alma. No hay nadie entre tú y las personas que la hicieron.",

    moreTitle: "El resto, por escrito",
    moreNote:
      "Están solo en inglés, y a propósito: cada uno tiene que revisarse contra la ley del país donde se lee antes de poder confiar en él, y seis traducciones seguras de un documento sin revisar serían peores que un único original honesto.",
  },

  journey: {
    intentTitle: "¿Qué suena más fuerte en ti ahora mismo?",
    intentSkip: "Saltar — ya sé lo que quiero",
    intents: {
      self: "Quién soy, de verdad",
      shifting: "Algo está cambiando y no sé por qué",
      us: "Nosotros — ¿esto va a funcionar?",
      where: "Dónde debería vivir",
    },
    freeLabel: "tuyo, gratis, para siempre",
    freeNote: "Estos números no cuestan nada, nunca. Son tuyos, sigas leyendo o no.",
    calculated: "los ocho sistemas · calculados",
    needsTimeRow: "Revolución solar · mapa",
    keepMySky: "Guardar mi cielo",
    staysFree: "Todo lo de arriba es gratis, para siempre",
    dialogLabel: "Conociéndote",
    back: "Volver a la portada",
    done: "listo",
    continueCta: "Continuar",
    orFaster: "o más rápido",
    withGoogle: "Continuar con Google",
    nameTitle: "¿Cómo te llamo?",
    nameSub: "Un nombre no es una cuenta. Todavía no se guarda nada.",
    namePlaceholder: "Sofía",
    nameAria: "Tu nombre",
    dateTitle: "¿Cuándo naciste?",
    dateSub: "Solo con la fecha ya tienes tres sistemas.",
    timeTitle: "¿A qué hora naciste?",
    timeSub:
      "La hora da las casas, la revolución solar y tu mapa. Sin ella quedan cerrados — no los vamos a inventar.",
    hourLabel: "Hora",
    minuteLabel: "Min",
    meridiemLabel: "AM o PM",
    lockedWithoutTime: "Casas, revolución solar y mapa quedan cerrados",
    placeTitle: "¿Dónde naciste?",
    placeSub: "Con la ciudad basta. El huso horario histórico lo resolvemos nosotros.",
    placePlaceholder: "Madrid",
    buildMySky: "Construir mi cielo",
    ceremony: [
      ["leyendo el sistema 1 de 8 · carta natal", "Diez planetas, doce casas — tu carta se traza con efemérides reales."],
      ["leyendo el sistema 2 de 8 · numerología", "Tu sendero de vida se reduce a un número que prefiere pruebas a creencias."],
      ["leyendo el sistema 3 de 8 · carta de nacimiento", "Uno de veintidós arcanos, calculado solo con la fecha."],
      ["leyendo el sistema 4 de 8 · tránsitos", "Dónde está el cielo ahora, frente a dónde estaba cuando empezaste."],
      ["leyendo el sistema 5 de 8 · compatibilidad", "Queda abierto hasta que añadas a otra persona — nada inventado."],
      ["leyendo el sistema 6 de 8 · revolución solar", "El año que viene, leído desde el minuto en que el Sol vuelve a su sitio."],
      ["leyendo el sistema 7 de 8 · astrocartografía", "Líneas planetarias sobre el mapa, trazadas con tu minuto exacto."],
      ["leyendo el sistema 8 de 8 · síntesis cruzada", "Nueve ejes. Donde tres tradiciones coinciden, eso va a tu núcleo."],
    ],
    ceremonySkip: "Saltar la ceremonia",
    authTitle: (name: string) => (name ? `Guarda esto, ${name}` : "Guarda esto"),
    authSub:
      "Un toque y tus ocho sistemas, tu retrato y tus preguntas siguen siendo tuyos. Sin contraseña, nunca.",
    legalBefore: "Al continuar aceptas los",
    legalTerms: "Términos",
    legalAnd: "y la",
    legalPrivacy: "Política de privacidad",
    legalAfter: ". 16+.",
    handoffTitle: "Ahora léete despacio.",
    handoffSub: "Tres reglas que hacen que esto funcione — la única guía que te vamos a dar.",
    rules: [
      "Un capítulo cada vez. Dieciséis de golpe es ruido.",
      "Cuando dos sistemas no coinciden, no elijas ganador. Ahí está el material.",
      "Pregúntame con tus palabras. Tres preguntas son gratis.",
    ],
    ascendant: "Ascendente",
    moonPhase: "Luna",
    needsTimeTag: "falta la hora de nacimiento",
    authSkip: "Ahora no — llévame a la app",
    placeOffline: "Ahora mismo no puedo consultar el índice de lugares. Inténtalo en un momento.",
    phases: {
      "new moon": "luna nueva",
      "waxing crescent": "luna creciente",
      "first quarter": "cuarto creciente",
      "waxing gibbous": "gibosa creciente",
      "full moon": "luna llena",
      "waning gibbous": "gibosa menguante",
      "last quarter": "cuarto menguante",
      "waning crescent": "luna menguante",
    },
  },
};
