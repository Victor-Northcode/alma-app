/**
 * Brazilian Portuguese.
 *
 * "Você" throughout — the natural register, and the one the whole country
 * actually uses. Prices here are shown in reais at the regional rate rather
 * than converted from dollars: charging US prices in São Paulo is charging
 * roughly four times as much, which is a decision about who gets to read
 * this rather than a decision about pricing.
 */

import type { Dictionary } from "./en";

export const ptBR: Dictionary = {
  meta: {
    name: "Português (Brasil)",
    htmlLang: "pt-BR",
    title: "Alma — Oito jeitos de ler você mesmo. Uma Alma.",
    description:
      "Oito tradições leem seus dados de nascimento e dizem onde concordam. Todo cálculo é gratuito — você paga só pelas palavras.",
  },

  nav: {
    what: "O que é",
    eight: "Os oito",
    pricing: "Preços",
    faq: "Perguntas",
    signIn: "Entrar",
    openMenu: "Abrir o menu",
    closeMenu: "Fechar o menu",
  },

  // The five controls that open the free journey share this one label; the
  // note in `en.ts` says why. What stood in the nav here was "Criar conta" —
  // literally *create an account*, offered by a website that mints no account at all.
  cta: {
    read: "Me ler — de graça",
    getApp: "Baixar o app",
  },

  language: {
    label: "Idioma",
  },

  hero: {
    overline: "oito sistemas · uma voz",
    titleA: "Oito jeitos de ler",
    titleB: "você mesmo.",
    titleAccent: "Uma Alma.",
    subShort: "Oito tradições leem seus dados de nascimento e mostram onde concordam.",
    subLong:
      "Oito tradições leem seus dados de nascimento e dizem onde concordam. Todo cálculo é gratuito — você paga só pelas palavras.",
    yourSky: "seu céu",
    quote: "Não digo o que vai acontecer. Digo do que você é feito.",
  },

  capture: {
    day: "Dia de nascimento",
    month: "Mês de nascimento",
    year: "Ano de nascimento",
    dayShort: "Dia",
    monthShort: "Mês",
    yearShort: "Ano",
    submit: "Ver minha primeira leitura — de graça",
    impossibleDate: "Essa data não existe. Confira o dia.",
    pickYear: "Mais um — escolha o ano.",
    unknownTime: "Não sei minha hora de nascimento",
    searchPlace: "Onde você nasceu?",
    noPlaces: "Nenhum lugar com esse nome. Tente a cidade maior mais próxima.",
  },

  what: {
    label: "o que é",
    lead: "Um olhar fundo para dentro — sem pressa e sem barulho",
    systemsFigure: "8",
    systemsTitle: "sistemas diferentes",
    systemsShort: "Cada um com sua lógica e seus pontos cegos.",
    systemsLong:
      "Cada um com sua lógica e seus pontos cegos. Comece por onde quiser — sem ordem, sem lição de casa.",
    freeFigure: "R$ 0",
    freeTitle: "por cada cálculo",
    freeShort: "Efemérides de verdade, mostradas por inteiro, de graça para sempre.",
    freeLong: "Calculado com efemérides de verdade, mostrado por inteiro, de graça para sempre.",
  },

  insight: {
    label: "dois segundos depois da sua data",
    sun: (sign: string) => `Sol em ${sign}`,
    lifePath: (n: number | string) => `Caminho de vida ${n}`,
    fromDateAlone: "Três sistemas, só com a sua data. Sua hora e seu lugar abrem os outros cinco.",
    awaiting: "Aqui nada é chutado, então ainda não tem nada. Me dê uma data e isto se enche do que é seu.",
    awaitingMeta: "esperando a sua data",
    hook: "Três sistemas já conhecem você. Outros cinco esperam dois detalhes.",
  },

  howToRead: {
    label: "como se ler",
    title: "Quatro regras pequenas",
    rules: [
      ["O momento", "Um capítulo por vez, não dezesseis."],
      ["A discordância", "Quando dois sistemas discordam, não escolha um vencedor."],
      ["A pergunta", "Pergunte com suas palavras; ela nomeia a posição."],
      ["O retorno", "Volte em um mês — o texto é reescrito."],
    ],
    disclaimer: "*Nada disso substitui terapia ou médico.",
  },

  eight: {
    label: "os oito",
    titleA: "Quatro perguntas,",
    titleB: "oito jeitos de responder",
    swipe: (n: number) => `arraste · todos os ${n}`,
    goTo: (i: number, n: number) => `Ir para ${i} de ${n}`,
    tail:
      "Agrupados pela sua pergunta, não pelo nome da tradição. Todos os oito são calculados de graça.",
    groups: {
      "who-am-i": "quem eu sou",
      "right-now": "agora",
      "this-year": "este ano",
      "how-we-match": "como a gente combina",
      "where-to-be": "onde estar",
      "all-of-it": "tudo junto",
    },
    notes: {
      natal: "16 capítulos",
      numerology: "só com a sua data",
      "birth-card": "22 arcanos",
      transits: "todo dia",
      "solar-return": "precisa da hora de nascimento",
      compatibility: "adicione uma pessoa",
      astrocartography: "precisa da hora de nascimento",
      synthesis: "9 eixos",
    },
    names: {
      natal: "Mapa natal",
      numerology: "Numerologia",
      "birth-card": "Carta de nascimento",
      transits: "Trânsitos",
      "solar-return": "Revolução solar",
      compatibility: "Compatibilidade",
      astrocartography: "Astrocartografia",
      synthesis: "Síntese cruzada",
    },
  },

  synthesis: {
    label: "só aqui",
    title: "Onde três sistemas concordam sobre você",
    leadShort: "Três concordando é o mais perto de uma prova que existe.",
    leadLong:
      "Três concordando é o mais perto de uma prova que existe. Dois discordando é ainda mais útil — é o conflito que você continua vivendo.",
    axes: {
      Direction: "Direção",
      Character: "Caráter",
      Mind: "Mente",
      Relationships: "Relações",
      Resources: "Recursos",
      Work: "Trabalho",
      "Weak point": "Ponto fraco",
      Growth: "Crescimento",
      Rhythms: "Ritmos",
    },
    moreShort: "Mente · trabalho · crescimento · ritmos",
    moreLong: "Mente · trabalho · ponto fraco · crescimento · ritmos",
  },

  voice: {
    label: "a voz da Alma",
    title: "Cada parágrafo nomeia uma posição real",
    sample:
      "Saturno está no seu Descendente a 19° de Peixes. Você aprendeu cedo que proximidade tem preço — então paga adiantado, antes de alguém pedir.",
    sampleTail:
      "É por isso que suas relações começam tão competentes e terminam tão cansadas.",
    proofShort: "Mova sua hora de nascimento em duas horas e este texto muda.",
    proofLong:
      "Mova sua hora de nascimento em duas horas e este texto muda. Verificado por um teste automático a cada versão.",
  },

  pricing: {
    label: "quanto custa",
    titleA: "Os números são de graça.",
    titleB: "As palavras têm preço.",
    natal: "Mapa natal inteiro",
    natalShort: "Os 16 capítulos, um pagamento só, seus para sempre.",
    natalLong:
      "Os 16 capítulos de uma vez, um pagamento só, seus para sempre. Inclui 15 perguntas para a Alma.",
    everythingYear: "Tudo, por um ano",
    everythingShort: "Todos os sistemas, todos os capítulos e os trânsitos conforme se movem.",
    everythingLong:
      "Todos os sistemas e capítulos, trânsitos diários e perguntas todo dia do ano.",
    renewsNote: "Renova todo ano até você cancelar. Dois toques, nos Ajustes.",
    honesty: [
      "pagamento único é pagamento único",
      "e-mail antes da renovação",
      "cancelar em dois toques",
      "o preço final é o da sua loja",
    ],
    wholeArchive: "O arquivo inteiro",
    archiveNote: "Os oito sistemas, comprados uma vez.",
  },

  faq: {
    label: "perguntas",
    showAll: "Todas as perguntas →",
    items: [
      {
        q: "Isso é astrologia de verdade?",
        a: "Efemérides da NASA JPL, conferidas com mapas de referência até o centésimo de grau.",
        aLong:
          "Efemérides da NASA JPL, casas Placidus, zodíaco tropical — conferidas com mapas de referência até o centésimo de grau, incluindo mudanças de horário e latitudes polares.",
      },
      {
        q: "Não sei minha hora de nascimento",
        a: "Tudo que não precisa dela continua funcionando. O que precisa fica marcado como indisponível.",
        aLong:
          "Tudo que não precisa de hora continua funcionando: sol, planetas por signo, numerologia, sua Carta de nascimento, quase todos os trânsitos. Casas, revolução solar e o mapa ficam marcados como indisponíveis — a gente não inventa.",
      },
      {
        q: "Vocês vão me cobrar automaticamente?",
        a: "Uma vez é uma vez. Um plano escreve para você três dias antes de cada renovação e cancela em dois toques.",
        aLong:
          "Compras únicas são únicas — não existe teste que vira cobrança. Um plano escreve para você três dias antes de cada renovação com a data e o valor, para o e-mail da sua conta ou, se você não tiver, para o que usou ao pagar. O preço cheio fica impresso no botão antes de pagar, e cancelar são dois toques nos Ajustes: depois o plano vai até o fim do período já pago.",
      },
      {
        q: "Isso é adivinhação?",
        a: "Não. Sem previsão de acontecimentos, sem linguagem de destino, sem conselho médico ou financeiro.",
        aLong:
          "Não. O Alma descreve do que o seu mapa é feito, não o que vai acontecer. Não há previsão de acontecimentos, nem linguagem de destino, nem conselho médico, psicológico ou financeiro em lugar nenhum.",
      },
      {
        q: "Por que oito sistemas?",
        a: "Porque uma tradição sozinha não consegue se conferir. Oito conseguem.",
        aLong:
          "Porque uma tradição sozinha não consegue se conferir. Quando três sistemas independentes dizem a mesma coisa sobre você, isso é o mais perto de uma prova que esse campo consegue oferecer — e onde dois discordam, você achou um conflito interno de verdade, não uma leitura ruim.",
      },
      {
        q: "O que acontece com meus dados?",
        a: "Seus para exportar, seus para apagar, pelos Ajustes, quando quiser.",
        aLong:
          "Seus dados de nascimento servem para calcular e para escrever, mais nada. Com conta, você exporta tudo ou apaga a conta sozinho, a qualquer momento, sem escrever para o suporte. Valem o GDPR, o UK GDPR e a CCPA.",
      },
      {
        q: "Quais sistemas o Alma lê?",
        a: "Oito: astrologia, numerologia, sua carta de nascimento, astrocartografia, trânsitos, revolução solar, compatibilidade e uma síntese cruzada de todos.",
        aLong:
          "Oito no total — astrologia ocidental, numerologia, sua carta de nascimento, astrocartografia, trânsitos, revolução solar e compatibilidade — mais uma síntese cruzada que os lê entre si e mostra onde concordam e onde não.",
      },
      {
        q: "Preciso de conta?",
        a: "Não. Tudo é calculado a partir dos seus dados de nascimento. A conta só leva seu mapa para outro telefone.",
        aLong:
          "Não é preciso conta para se ler: cada cálculo parte dos seus dados de nascimento no aparelho. Entrar só salva seu mapa e suas compras para acompanharem você em um novo dispositivo, e é totalmente opcional.",
      },
    ] as ReadonlyArray<{ q: string; a: string; aLong: string }>,
  },

  final: {
    title: "Seu céu esteve ali esse tempo todo.",
    sub: "Dê uma data a ele. Oito sistemas respondem em menos de um minuto.",
  },

  ctaBar: {
    placeholder: "Sua data de nascimento",
    ready: "3 sistemas prontos · 5 esperando",
    waiting: "8 sistemas · esperando uma data",
  },

  footer: {
    privacy: "Privacidade",
    terms: "Termos",
    refunds: "Reembolsos",
    subscriptionTerms: "Termos de assinatura",
    imprint: "Informações legais",
    cookies: "Gerenciar cookies",
    withdrawal: "Direito de arrependimento (UE/RU)",
    support: "Ajuda",
    deleteAccount: "Excluir sua conta",
    choices: "Suas escolhas de privacidade",
    doNotSell: "Não vender nem compartilhar meus dados pessoais",
    contact: "Contato",
    groupLegal: "Legal",
    groupMoney: "Dinheiro",
    groupCompany: "Empresa",
    payments:
      "Tudo é comprado dentro do app, da Apple ou do Google como vendedor legal · impostos incluídos quando se aplicam",
    disclaimer:
      "Só para autoconhecimento. Não é orientação médica, psicológica, jurídica ou financeira, e não prevê acontecimentos.",
    performance:
      "O conteúdo digital abre assim que é pago. Do que isso abre mão e do que não abre está na",
    performanceLink: "página de reembolsos",
    rights: "© 2026 Pazl LLC. Todos os direitos reservados.",
  },

  months: [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
  ],

  signs: {
    Aries: "Áries", Taurus: "Touro", Gemini: "Gêmeos", Cancer: "Câncer",
    Leo: "Leão", Virgo: "Virgem", Libra: "Libra", Scorpio: "Escorpião",
    Sagittarius: "Sagitário", Capricorn: "Capricórnio",
    Aquarius: "Aquário", Pisces: "Peixes",
  },

  app: {
    note: "A leitura acontece no app. Todos os cálculos continuam gratuitos lá, igual aqui.",
    waiting: (system: string) => `Seu ${system.toLowerCase()} espera por você no app.`,
    appleSoon: "Em breve na App Store",
    googleSoon: "Em breve no Google Play",
    appStore: "Baixar na App Store",
    googlePlay: "Disponível no Google Play",
    notYet: "Ainda não estamos em nenhuma das duas lojas. É aqui que os botões vão ficar no dia em que estivermos.",
    continues: {
      chaptersLabel: "Os capítulos",
      chapters: (all: number) =>
        `${all} no total, escritos a partir dos números que você acabou de ver. O primeiro capítulo natal é gratuito, e o resto se compra um sistema por vez, ou os oito de uma vez.`,
      secondLabel: "Os que precisam de mais do que uma data",
      second:
        "A compatibilidade abre quando você adiciona uma segunda pessoa. A astrocartografia desenha suas linhas no mapa, para você perguntar sobre uma cidade antes de se mudar para ela.",
      almaLabel: "A própria Alma",
      alma:
        "Pergunte sobre este mapa com as suas palavras. Cada resposta nomeia a posição de onde veio, para você poder conferir.",
    },
    carryNamed: (email: string) =>
      `Este céu está em ${email}. Entre com esse endereço no app e ele já estará lá — nada para digitar duas vezes.`,
    carryAccount:
      "Este céu está na sua conta. Entre do mesmo jeito no app e ele já estará lá — nada para digitar duas vezes.",
    carrySent: (email: string) =>
      `Abra o link que acabamos de enviar para ${email}: é ele que coloca este céu numa conta. Depois entre com o mesmo endereço no app e ele estará esperando.`,
    carryGuest:
      "Ninguém está conectado aqui, então este céu fica neste navegador. O app pede sua data de nascimento mais uma vez — um minuto — e todos os números acima voltam iguais.",
    carryUnknown:
      "Se você acabou de entrar, o app encontra este céu pelo mesmo endereço. Se pulou, ele pede sua data de nascimento mais uma vez — um minuto — e todos os números acima voltam iguais.",
  },

  support: {
    title: "Ajuda",
    lead: "Um endereço só, lido por quem construiu a Alma. Sem número de chamado, sem fila e sem ninguém lendo um roteiro.",

    writeTitle: "Escreva para a gente",
    write1:
      "Tudo chega na mesma caixa. Escreva no seu idioma: a Alma é escrita em sete e responde nos sete.",
    write2:
      "Quem responde é uma pessoa, normalmente no mesmo dia e nunca depois de três dias úteis. Se passou disso, alguma coisa falhou do nosso lado: escreva de novo e diga que é a segunda vez.",

    includeTitle: "O que colocar na mensagem",
    include1: "Em qual loja você comprou: App Store ou Google Play.",
    include2: "O número do pedido no recibo da loja, se a mensagem for sobre dinheiro.",
    include3:
      "O e-mail da sua conta na Alma. Se você nunca entrou, o id da conta que aparece nos Ajustes.",
    include4: "O que aconteceu, com as suas palavras. Uma captura de tela ajuda e nunca é obrigatória.",
    includeNote:
      "Uma coisa que não serve para nada aqui: o número do cartão. Seu cartão nunca chega até a Alma, não conseguimos achar uma compra por ele, e nenhuma mensagem nossa vai pedir isso.",

    moneyTitle: "O dinheiro está com a loja",
    money1:
      "A Alma não é a vendedora. No iPhone e no iPad quem vende é a Apple; no Android é o Google. São eles que cobram, que emitem o recibo, que cuidam do imposto e que ficam com o dinheiro.",
    money2:
      "O que significa que não temos como te reembolsar. Não existe botão nenhum do nosso lado, e uma página de ajuda que insinuasse o contrário custaria uma tarde sua. Peça para a loja que vendeu:",
    refundApple: "Apple — reportaproblem.apple.com, com a Apple Account que fez a compra.",
    refundGoogle: "Google Play — abra seu histórico de pedidos e peça o reembolso naquela compra.",
    money3:
      "Quando o erro é nosso — uma leitura que nunca chegou, uma cobrança em dobro, um mapa errado por falha nossa — escreva primeiro para nós. A gente pede à loja no seu lugar, sem te fazer discutir, e conta o que responderam mesmo quando a resposta é não.",

    cancelTitle: "Cancelar uma assinatura",
    cancel1:
      "Também é da loja, pelo mesmo motivo. Dois toques: abra suas assinaturas na loja onde comprou e cancele. Os próprios Ajustes da Alma têm uma linha que abre exatamente essa tela.",
    cancel2:
      "Cancelar interrompe a próxima cobrança. Não é reembolso do período atual: esse período foi pago e continua aberto até o último dia.",

    dataTitle: "Sua conta e seus dados",
    data1:
      "Exportar tudo o que a Alma guarda sobre você e apagar tudo estão os dois nos Ajustes, e os dois acontecem na hora. Nenhum dos dois precisa da gente, e nenhum tem uma oferta atravessada na frente.",

    readingTitle: "Tem algo errado numa leitura",
    reading1:
      "Conte para a gente. Um mapa que não bate com os dados de nascimento que você digitou é um defeito, não uma questão de interpretação, e preferimos muito mais ficar sabendo do que você concluir que a Alma é assim mesmo.",
    reading2:
      "A Alma é para se conhecer. Não é orientação médica, jurídica nem financeira, e não prevê acontecimentos. Se você não está bem, está em perigo, ou está decidindo algo que envolve dinheiro ou lei, fale com alguém qualificado — isso a gente não tem como ser, por melhor que a leitura tenha sido.",

    whoTitle: "Para quem você está escrevendo",
    who1:
      "Pazl LLC, no Wyoming, Estados Unidos: a empresa que opera a Alma. Não tem ninguém entre você e quem construiu isso.",

    moreTitle: "O resto, por escrito",
    moreNote:
      "Estão só em inglês, e de propósito: cada um precisa ser conferido contra a lei do país onde é lido antes de dar para confiar nele, e seis traduções confiantes de um documento não revisado seriam piores do que um único original honesto.",
  },

  journey: {
    intentTitle: "O que está mais alto em você agora?",
    intentSkip: "Pular — já sei o que quero",
    intents: {
      self: "Quem eu sou, de verdade",
      shifting: "Alguma coisa está mudando e não sei por quê",
      us: "A gente — isso vai dar certo",
      where: "Onde eu deveria morar",
    },
    freeLabel: "seu, de graça, para sempre",
    freeNote: "Esses números nunca custam nada. São seus, você lendo mais ou não.",
    calculated: "os oito sistemas · calculados",
    needsTimeRow: "Revolução solar · mapa",
    keepMySky: "Guardar meu céu",
    staysFree: "Tudo acima fica de graça, para sempre",
    dialogLabel: "Conhecendo você",
    back: "Voltar para a página inicial",
    done: "pronto",
    continueCta: "Continuar",
    orFaster: "ou mais rápido",
    withGoogle: "Continuar com o Google",
    nameTitle: "Como eu te chamo?",
    nameSub: "Um nome não é uma conta. Ainda não estamos salvando nada.",
    namePlaceholder: "Ana",
    nameAria: "Seu nome",
    dateTitle: "Quando você nasceu?",
    dateSub: "Só a data já dá três sistemas.",
    timeTitle: "Que horas você nasceu?",
    timeSub:
      "A hora dá as casas, a revolução solar e o seu mapa. Sem ela, ficam fechados — e a gente não inventa.",
    hourLabel: "Hora",
    minuteLabel: "Min",
    meridiemLabel: "AM ou PM",
    lockedWithoutTime: "Casas, revolução solar e mapa ficam fechados",
    placeTitle: "Onde você nasceu?",
    placeSub: "A cidade basta. O fuso horário histórico a gente resolve.",
    placePlaceholder: "São Paulo",
    buildMySky: "Construir meu céu",
    ceremony: [
      ["lendo o sistema 1 de 8 · mapa natal", "Dez planetas, doze casas — seu mapa é traçado com efemérides de verdade."],
      ["lendo o sistema 2 de 8 · numerologia", "Seu caminho de vida se reduz a um número que prefere prova a crença."],
      ["lendo o sistema 3 de 8 · carta de nascimento", "Um dos vinte e dois arcanos, calculado só pela data."],
      ["lendo o sistema 4 de 8 · trânsitos", "Onde o céu está agora, contra onde ele estava quando você começou."],
      ["lendo o sistema 5 de 8 · compatibilidade", "Fica aberto até você adicionar uma segunda pessoa — nada inventado."],
      ["lendo o sistema 6 de 8 · revolução solar", "O ano que vem, lido a partir do minuto em que o Sol volta ao lugar."],
      ["lendo o sistema 7 de 8 · astrocartografia", "Linhas planetárias no mapa, traçadas do seu minuto exato."],
      ["lendo o sistema 8 de 8 · síntese cruzada", "Nove eixos. Onde três tradições concordam, aquilo vai para o seu núcleo."],
    ],
    ceremonySkip: "Pular a cerimônia",
    authTitle: (name: string) => (name ? `Guarde isso, ${name}` : "Guarde isso"),
    authSub:
      "Um toque e seus oito sistemas, seu retrato e suas perguntas continuam seus. Sem senha, nunca.",
    legalBefore: "Ao continuar você aceita os",
    legalTerms: "Termos",
    legalAnd: "e a",
    legalPrivacy: "Política de Privacidade",
    legalAfter: ". 16+.",
    handoffTitle: "Agora se leia devagar.",
    handoffSub: "Três regras que fazem isso funcionar — a única introdução que a gente vai te dar.",
    rules: [
      "Um capítulo por vez. Dezesseis de uma vez é barulho.",
      "Quando dois sistemas discordam, não escolha um vencedor. O material está aí.",
      "Me pergunte com suas palavras. Três perguntas são de graça.",
    ],
    ascendant: "Ascendente",
    moonPhase: "Lua",
    needsTimeTag: "falta a hora de nascimento",
    authSkip: "Agora não — me mostra o app",
    placeOffline: "Não consigo acessar o índice de lugares agora. Tente de novo daqui a pouco.",
    phases: {
      "new moon": "lua nova",
      "waxing crescent": "lua crescente",
      "first quarter": "quarto crescente",
      "waxing gibbous": "gibosa crescente",
      "full moon": "lua cheia",
      "waning gibbous": "gibosa minguante",
      "last quarter": "quarto minguante",
      "waning crescent": "lua minguante",
    },
  },
};
