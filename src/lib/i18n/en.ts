/**
 * English — the source dictionary.
 *
 * Every other locale is typed against `typeof en`, so a missing key is a
 * build error rather than a paragraph that silently reverts to English in
 * front of a Brazilian customer. That is the whole reason the dictionary is
 * one nested object instead of a flat map of loose strings.
 *
 * What is *not* here: the readings themselves. Chapter text is generated per
 * locale by the writing layer, which is given the language in its system
 * prompt — translating generated prose after the fact would produce English
 * sentences wearing Italian words.
 */

export const en = {
  meta: {
    name: "English",
    // The tag goes on <html lang>, so it has to be a real BCP-47 tag.
    htmlLang: "en",
    title: "Alma — Eight ways to read yourself. One Alma.",
    description:
      "Eight traditions read your birth data and tell you where they agree. Every calculation is free — you pay only for the words.",
  },

  nav: {
    what: "What it is",
    eight: "The eight",
    pricing: "Pricing",
    faq: "Questions",
    signIn: "Sign in",
    openMenu: "Open menu",
    closeMenu: "Close menu",
  },

  /**
   * One door, one sentence.
   *
   * Five controls on this page open the free journey — the nav pill, the
   * button under the first insight, the one under the year price, the one in
   * the closing panel and the sticky bar — and until now each of them named a
   * different destination. "Sign up" offered an account the web cannot mint;
   * "Start — the chart is free" sat directly under an annual price, where
   * "start" reads as start the plan; "Continue free" and "Build my full sky"
   * described two different things that were in fact the same overlay. A
   * person who reads two of them concludes there are two products.
   *
   * So the label lives here, once, and every one of the five wears it. What it
   * claims is exactly what happens: the journey asks for a date, a time and a
   * place, computes the chart, hands over the sun, the moon, the life path,
   * the birth card and the moon phase, and charges nothing anywhere in it. It
   * deliberately does not promise where you end up — that is the app, on a
   * store that has not accepted us yet, and `handoff` is the screen allowed to
   * say so. A button that promised the app would be promising a download that
   * does not exist today.
   *
   * The five places stay distinguishable in the funnel through `JourneyDoor`
   * in `lib/cta.ts`, which is the right place for that difference: analytics
   * needs to tell them apart, a reader does not.
   */
  cta: {
    read: "Read myself — free",
    getApp: "Get the app",
  },

  language: {
    /**
     * The picker's accessible name, and the only string in it that is
     * translated. The six options are each written in their own language —
     * see `lib/locale-choice.ts` — because somebody who cannot read this page
     * cannot read this page's word for their own language either.
     */
    label: "Language",
  },

  hero: {
    overline: "eight systems · one voice",
    titleA: "Eight ways to read",
    titleB: "yourself.",
    titleAccent: "One Alma.",
    subShort: "Eight traditions read your birth data and show where they agree.",
    subLong:
      "Eight traditions read your birth data and tell you where they agree. Every calculation is free — you pay only for the words.",
    yourSky: "your sky",
    quote: "I don't tell you what will happen. I tell you what you're made of.",
  },

  capture: {
    day: "Day of birth",
    month: "Month of birth",
    year: "Year of birth",
    dayShort: "Day",
    monthShort: "Month",
    yearShort: "Year",
    submit: "Show my first insight — free",
    impossibleDate: "That date does not exist. Check the day.",
    pickYear: "One more — pick the year.",
    unknownTime: "I don't know my birth time",
    searchPlace: "Where were you born?",
    noPlaces: "No place by that name. Try the nearest larger town.",
  },

  what: {
    label: "what it is",
    lead: "A deep inner look — without rush or noise",
    systemsFigure: "8",
    systemsTitle: "different systems",
    systemsShort: "Each with its own logic and blind spots.",
    systemsLong:
      "Each with its own logic and blind spots. Start anywhere — no order, no homework.",
    freeFigure: "$0",
    freeTitle: "for every calculation",
    freeShort: "Real ephemeris data, shown in full, forever free.",
    freeLong: "Computed from real ephemeris data, shown in full, forever free.",
  },

  insight: {
    label: "two seconds after your date",
    sun: (sign: string) => `Sun in ${sign}`,
    lifePath: (n: number | string) => `Life path ${n}`,
    fromDateAlone: "Three systems, from your date alone. Your time and place open the other five.",
    awaiting: "Nothing above is guessed, so nothing is here yet. Give me a date and this fills with your own.",
    awaitingMeta: "waiting for your date",
    hook: "Three systems already know you. Five more are waiting for two details.",
  },

  howToRead: {
    label: "how to read yourself",
    title: "Four small rules",
    rules: [
      ["The moment", "One chapter at a time, not sixteen."],
      ["The disagreement", "When two systems argue, don't pick a winner."],
      ["The question", "Ask in your own words; she names the position."],
      ["The return", "Come back in a month — the text is rebuilt."],
    ] as readonly (readonly [string, string])[],
    disclaimer: "*Nothing here replaces therapy or a doctor.",
  },

  eight: {
    label: "the eight",
    titleA: "Four questions,",
    titleB: "eight ways to answer",
    swipe: (n: number) => `swipe · all ${n}`,
    /**
     * The rail's pagination dots, one accessible name each.
     *
     * It was a template literal inside `RailDots` — "Go to 3 of 8" — so the
     * eight controls a phone user steps through to reach the eight systems
     * announced themselves in English on all six landings. `RailDots` is a
     * generic control and does not read the dictionary; the caller passes this
     * in, the same way it already passes `swipe`.
     */
    goTo: (i: number, n: number) => `Go to ${i} of ${n}`,
    tail:
      "Grouped by your question, not by the name of the tradition. Every one of the eight is calculated free.",
    groups: {
      "who-am-i": "who am I",
      "right-now": "right now",
      "this-year": "this year",
      "how-we-match": "how we match",
      "where-to-be": "where to be",
      "all-of-it": "all of it",
    },
    /**
     * The line under each card's name, and it was English on six landings.
     *
     * These lived in `data.ts` as fixture fields, where `check-locales.mjs`
     * cannot see them — the same hole the six FAQ questions fell through. One
     * of them was worse than untranslated: Numerology read "life path 7",
     * which is the demo person's number, printed under the card for every
     * visitor whose life path is anything else.
     */
    notes: {
      natal: "16 chapters",
      numerology: "from your date alone",
      "birth-card": "22 arcana",
      transits: "daily",
      "solar-return": "needs birth time",
      compatibility: "add a person",
      astrocartography: "needs birth time",
      synthesis: "9 axes",
    },
    names: {
      natal: "Natal chart",
      numerology: "Numerology",
      "birth-card": "Birth Card",
      transits: "Transits",
      "solar-return": "Solar return",
      compatibility: "Compatibility",
      astrocartography: "Astrocartography",
      synthesis: "Cross-synthesis",
    },
  },

  synthesis: {
    label: "only here",
    title: "Where three systems agree about you",
    leadShort: "Three agreeing is the closest thing to proof.",
    leadLong:
      "Three agreeing is the closest thing to proof. Two disagreeing is more useful still — that's the conflict you keep living out.",
    axes: {
      Direction: "Direction",
      Character: "Character",
      Mind: "Mind",
      Relationships: "Relationships",
      Resources: "Resources",
      Work: "Work",
      "Weak point": "Weak point",
      Growth: "Growth",
      Rhythms: "Rhythms",
    },
    moreShort: "Mind · work · growth · rhythms",
    moreLong: "Mind · work · weak point · growth · rhythms",
  },

  voice: {
    label: "Alma's voice",
    title: "Every paragraph names a real position",
    sample:
      "Saturn sits on your Descendant at 19° Pisces. You learned early that closeness has a price — so you pay it in advance, before anyone asks.",
    sampleTail:
      "That is why your relationships start out so competent and end up so tired.",
    proofShort: "Move your birth time by two hours and this text changes.",
    proofLong:
      "Move your birth time by two hours and this text changes. Verified by an automated test on every release.",
  },

  pricing: {
    label: "what it costs",
    titleA: "The numbers are free.",
    titleB: "The words have a price.",
    natal: "Whole natal chart",
    natalShort: "All 16 chapters, one payment, yours permanently.",
    natalLong:
      "All 16 chapters at once, one payment, yours permanently. Includes 15 questions to Alma.",
    // The paywall charges the annual plan and used to label that row with
    // `everything` — "Everything, monthly" above a year's price. A row whose
    // title and amount describe different products is the shape a chargeback
    // takes, so the sheet names the thing it actually bills.
    everythingYear: "Everything, for a year",
    everythingShort: "Every system, every chapter, and the transits as they move.",
    everythingLong:
      "Every system and chapter, daily transits, and questions every day of the year.",
    renewsNote: "Renews every year until you cancel. Two taps, from Settings.",
    /**
     * The honesty plate. Full prices, no timers, nothing hidden — and, since
     * this release, one line about the prices above it.
     *
     * **The web sells nothing.** Every figure in this section comes from our
     * catalogue, priced in the currency of the country the request arrived
     * from, and the charge happens in the App Store or on Google Play, which
     * price from the *account's* store region. Those are usually the same
     * country and they are not the same fact: somebody in Spain with a British
     * Apple ID is shown euros here and charged pounds there, and a person who
     * moved last year may be shown their new country and billed in their old
     * one. Neither is fixable from a web page — no browser can read a store
     * account — so the page says so instead of quietly printing a number the
     * store will not honour.
     *
     * It is a permanent line rather than one that appears when we suspect a
     * mismatch, because we cannot suspect anything: the store region is
     * invisible to us here, always. A caveat that switched itself off would be
     * claiming a certainty this surface never has.
     */
    honesty: [
      "one-time is one-time",
      "email before renewal",
      "cancel in two taps",
      "your store sets the final price",
    ] as readonly string[],
    wholeArchive: "The whole archive",
    archiveNote: "All eight systems, bought once.",
  },

  faq: {
    label: "questions",
    showAll: "All questions →",
    /**
     * The six questions, and they were shipping in English on six landings.
     *
     * They lived in `src/lib/data.ts` as fixtures rather than here, so
     * `check-locales.mjs` could not see them and nobody noticed that a German
     * visitor was reading "Will you charge me automatically?" in English — a
     * subscription-terms question, answered in a language they were not sold in.
     * `q` is the question, `a` is the phone answer and `aLong` is the one the
     * wider screen has room for; the two are not the same sentence trimmed,
     * because a truncated legal answer is a different answer.
     */
    items: [
      {
        q: "Is this real astrology?",
        a: "NASA JPL ephemeris data, tested against reference charts to a hundredth of a degree.",
        aLong:
          "NASA JPL ephemeris data, Placidus houses, tropical zodiac — tested against reference charts to a hundredth of a degree, including daylight-saving edge cases and polar latitudes.",
      },
      {
        q: "I don't know my birth time",
        a: "Everything that does not need it still works. What needs it stays marked unavailable.",
        aLong:
          "Everything that does not need a time still works: sun, planets by sign, numerology, your Birth Card, most transits. Houses, the solar return and the map stay marked as unavailable — we will not invent them.",
      },
      {
        q: "Will you charge me automatically?",
        a: "One-time means one-time. A plan writes to you three days before every renewal and cancels in two taps.",
        aLong:
          "One-time purchases are one-time — there is no trial that turns into a charge. A plan writes to you three days before every renewal with the date and the amount, to the address on your account or, if you have none, to the one you paid with. The full price is printed on the button before you pay, and cancelling is two taps in Settings, after which the plan runs to the end of the period you have already paid for.",
      },
      {
        q: "Is this fortune-telling?",
        a: "No. No predictions of events, no fate language, no medical or money advice.",
        aLong:
          "No. Alma describes what your chart is made of, not what will happen. There are no event predictions, no fate language, and no medical, psychological or financial advice anywhere in the product.",
      },
      {
        q: "Why eight systems?",
        a: "Because one tradition cannot check itself. Eight can.",
        aLong:
          "Because one tradition cannot check itself. When three independent systems say the same thing about you, that is the closest thing to proof this field can offer — and where two disagree, you have found a real internal conflict rather than a bad reading.",
      },
      {
        q: "What happens to my data?",
        a: "Yours to export, yours to delete, from Settings, at any time.",
        aLong:
          "Your birth data is used to calculate and to write, nothing else. Sign in and you can export everything or delete your account yourself, at any moment, without writing to support. GDPR, UK GDPR and CCPA apply.",
      },
      {
        q: "Which systems does Alma read?",
        a: "Eight: astrology, numerology, your birth card, astrocartography, transits, the solar return, compatibility, and a cross-synthesis of them all.",
        aLong:
          "Eight in all — Western astrology, numerology, your birth card, astrocartography, transits, the solar return and compatibility — plus a cross-synthesis that reads them against each other and shows where they agree and where they don't.",
      },
      {
        q: "Do I need an account?",
        a: "No. Everything calculates from your birth details. An account only carries your chart to a new phone.",
        aLong:
          "No account is needed to read yourself — every calculation runs from your birth details on your phone. Signing in only saves your chart and purchases so they follow you to a new device, and it is entirely optional.",
      },
    ] as ReadonlyArray<{ q: string; a: string; aLong: string }>,
  },

  final: {
    title: "Your sky has been there the whole time.",
    sub: "Give it a date. Eight systems answer in under a minute.",
  },

  ctaBar: {
    placeholder: "Your date of birth",
    ready: "3 systems ready · 5 waiting",
    waiting: "8 systems · waiting on one date",
  },

  footer: {
    privacy: "Privacy",
    terms: "Terms",
    refunds: "Refunds",
    subscriptionTerms: "Subscription terms",
    imprint: "Imprint",
    cookies: "Manage cookies",
    /**
     * The rest of the footer, which was hardcoded English on six landings.
     *
     * A legal notice in a language the reader does not speak is not a notice —
     * France's language rules, Italy's Codice del consumo art. 9 and Brazil's
     * CDC art. 46 all say a term a consumer could not understand does not bind
     * them — and `check-locales.mjs` cannot see a string that lives in a
     * component.
     */
    withdrawal: "Withdrawal rights (EU/UK)",
    /**
     * Two links the footer was missing, and both of them are required reading
     * rather than housekeeping. Google asks that the deletion page be
     * *readily discoverable*, which a URL pasted into Play Console and linked
     * nowhere on the site is not; Apple asks for a support URL that reaches a
     * human, and the place a person looks for one is the bottom of the page.
     */
    support: "Support",
    deleteAccount: "Delete your account",
    choices: "Your privacy choices",
    doNotSell: "Do not sell or share my personal information",
    contact: "Contact",
    groupLegal: "Legal",
    groupMoney: "Money",
    groupCompany: "Company",
    /**
     * This took a merchant name and printed "payments processed by Paddle as
     * merchant of record" under a website that cannot take a payment at all.
     * Nothing is sold here any more: the ladder is bought inside the apps,
     * where Apple and Google are the sellers. A processor named on a page that
     * never charges anybody is not a harmless leftover — it is the line a card
     * issuer reads during a dispute, naming a company that never saw the money.
     *
     * A plain string rather than a function now, and deliberately: the two
     * seller names are fixed facts about the two stores rather than
     * configuration, and a string is a thing `check-locales.mjs` can see. It
     * could not see inside the template literal this used to be.
     */
    payments:
      "Nothing is sold on this website. Everything is bought inside the app, from Apple or Google as merchant of record · tax included where it applies",
    disclaimer:
      "For self-knowledge only. Not medical, psychological, legal or financial advice, and not a prediction of events.",
    /**
     * This used to read "by purchasing you agree to immediate performance and
     * waive the EU/UK 14-day withdrawal right", one click from a policy page
     * titled "…which we do not treat as waived". Both halves were wrong:
     * purchasing waives nothing on its own — two express consents plus a
     * receipt do — and nothing is written at the moment of payment anyway.
     */
    performance:
      "Digital content opens as soon as it is paid for. What that does and does not waive is on the",
    performanceLink: "refunds page",
    rights: "© 2026 Pazl LLC. All rights reserved.",
  },

  months: [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ] as readonly string[],

  signs: {
    Aries: "Aries", Taurus: "Taurus", Gemini: "Gemini", Cancer: "Cancer",
    Leo: "Leo", Virgo: "Virgo", Libra: "Libra", Scorpio: "Scorpio",
    Sagittarius: "Sagittarius", Capricorn: "Capricorn",
    Aquarius: "Aquarius", Pisces: "Pisces",
  },

  /**
   * The handoff, which is the only conversion this website has left.
   *
   * Its own group rather than a corner of `journey`, because two screens say
   * it — the last step of the journey and the page a magic link lands on —
   * and neither owns it. The store names are not translated: "App Store" and
   * "Google Play" are the words on the badge in every locale Apple and Google
   * publish, and a translated one is a badge nobody recognises.
   *
   * Both "coming" lines exist because neither app has been accepted yet, and
   * both live lines exist so that publishing is one constant in
   * `lib/stores.ts` and nothing else. See the note there.
   */
  app: {
    note: "The reading happens in the app. Every calculation stays free there, exactly as it is here.",
    waiting: (system: string) => `Your ${system} is waiting in the app.`,
    appleSoon: "Coming to the App Store",
    googleSoon: "Coming to Google Play",
    appStore: "Download on the App Store",
    googlePlay: "Get it on Google Play",
    /* Why there is a sentence where a control should be. Somebody who taps a
       plate and nothing happens concludes the site is broken; somebody who
       reads one line concludes we are not out yet, which is the truth and
       costs nothing. */
    notYet: "Neither store has us yet. This is where the buttons go the day they do.",
    /**
     * What continues in the app, one honest sentence each.
     *
     * Three, and no fourth: this screen is read by somebody who has just been
     * given something real and is deciding whether to bother. No countdown, no
     * struck-through price, no "limited" — that rule was written on the paywall
     * that used to stand here and it outlived its file.
     */
    continues: {
      chaptersLabel: "The chapters",
      // «One in every system» was the pre-17.08.2026 rule; since the owner's
      // decision exactly one chapter in the product is free (natal I, "Core"),
      // and a sentence advertising eight was a false claim in six languages.
      chapters: (all: number) =>
        `${all} of them, written from the numbers you have just been shown. The first natal chapter opens free, and the rest are bought a system at a time, or all eight at once.`,
      secondLabel: "The ones that need more than a date",
      second:
        "Compatibility opens when you add a second person. Astrocartography draws your lines across the map, so you can ask about a city before you move to it.",
      almaLabel: "Alma herself",
      alma:
        "Ask about this chart in your own words. Every answer names the position it came from, so you can check her.",
    },
    /**
     * Whether the chart just calculated survives the walk to a phone — and it
     * is four sentences because there are four true answers, not one hopeful
     * one. Nothing here may imply a continuity the code does not provide: a
     * guest chart lives on a token in this browser's local storage, and a fresh
     * install has neither the token nor any way to ask for it.
     */
    carryNamed: (email: string) =>
      `This sky is on ${email}. Sign in with that address in the app and it is already there — nothing to enter twice.`,
    carryAccount:
      "This sky is on your account. Sign in the same way in the app and it is already there — nothing to enter twice.",
    carrySent: (email: string) =>
      `Open the link we just sent to ${email} — that is what puts this sky on an account. Then sign in with the same address in the app and it is waiting.`,
    carryGuest:
      "Nothing here is signed in, so this sky stays in this browser. The app asks for your birth date once more — about a minute — and every number above comes back the same.",
    carryUnknown:
      "If you signed in a moment ago, the app finds this sky from the same address. If you skipped it, the app asks for your birth date once more — about a minute — and every number above comes back the same.",
  },

  /**
   * The support page — the one document on this site that is translated.
   *
   * The five legal documents are English-only for a stated reason: an argument
   * about consumer law has to be reviewed against the law of the country it is
   * read in, and six confident unreviewed versions are worse than one original.
   * This page is not an argument. It is an address, a list of what to put in a
   * letter, and directions to two other companies' screens — instructions,
   * which translate exactly, and which are read by somebody who is already
   * annoyed and should not also have to read English.
   *
   * **No sentence here contains a link.** Word order moves between these six
   * languages and an anchor buried mid-sentence moves with it, which is how a
   * translated page ends up linking the wrong two words or, worse, splitting a
   * URL. Every destination is rendered by the page as its own line, with the
   * address itself as the link text. That is why `refundApple` reads like a
   * label rather than like prose.
   *
   * **"three working days" is written out in each language rather than
   * interpolated.** A number passed into a template would escape
   * `check-locales.mjs`, which cannot see inside a function — and this is the
   * one promise on the page a person will hold us to. Changing it means editing
   * six strings, and that is the correct amount of friction for changing a
   * promise.
   */
  support: {
    title: "Support",
    lead: "One address, read by the people who built Alma. No ticket number, no queue, and nobody reading from a script.",

    writeTitle: "Write to us",
    write1:
      "Everything comes to one mailbox. Write in your own language — Alma is written in six and answered in all of them.",
    write2:
      "A person answers, usually the same day and never later than three working days. If it has been longer than that, something has gone wrong on our side: write again, and say that you are writing again.",

    includeTitle: "What to put in the letter",
    include1: "Which store you bought in — the App Store or Google Play.",
    include2: "The order number on the store's receipt, if the letter is about money.",
    include3:
      "The email address on your Alma account. If you never signed in, the account id shown in Settings instead.",
    include4: "What happened, in your own words. A screenshot helps and is never required.",
    includeNote:
      "One thing we cannot use: a card number. Your card never reaches Alma, we cannot look a purchase up by it, and no letter from us will ever ask you for one.",

    moneyTitle: "Anything about money is held by the store",
    money1:
      "Alma is not the seller. Apple sells it on iPhone and iPad, Google sells it on Android. They take the payment, they issue the receipt, they handle the tax, and they hold the money.",
    money2:
      "Which means we cannot refund you ourselves. There is no button on our side to press, and a support page that implied otherwise would cost you an afternoon. Ask the store that sold it:",
    refundApple: "Apple — reportaproblem.apple.com, signed in with the Apple Account that bought it.",
    refundGoogle: "Google Play — open your order history and request a refund on the purchase.",
    money3:
      "Where the fault is ours — a reading that never arrived, a charge that happened twice, a chart wrong through an error of ours — write to us first. We ask the store on your behalf, we do not make you argue for it, and we tell you what they said even when the answer is no.",

    cancelTitle: "Cancelling a subscription",
    cancel1:
      "Also the store's, for the same reason. Two taps: open your subscriptions on the store you bought from, then cancel. Alma's own Settings has a row that opens exactly that screen for you.",
    cancel2:
      "Cancelling stops the next charge. It is not a refund of the period you are in — that period was paid for and it stays open until its last day.",

    dataTitle: "Your account and your data",
    data1:
      "Exporting everything Alma holds about you, and deleting it, are both in Settings and both happen immediately. Neither one needs us, and neither one has an offer standing in front of it.",

    readingTitle: "Something in a reading is wrong",
    reading1:
      "Tell us. A chart that does not match the birth data you entered is a fault rather than a matter of interpretation, and we would much rather hear about it than have you decide Alma is simply like that.",
    reading2:
      "Alma is for self-knowledge. It is not medical, legal or financial advice and it does not predict events. If you are unwell, in danger, or making a decision with money or law in it, please talk to someone qualified — that is not something we can be, however good the reading was.",

    whoTitle: "Who you are writing to",
    who1:
      "Pazl LLC, in Wyoming, United States: the company that operates Alma. Nobody sits between you and the people who built it.",

    moreTitle: "The rest of it, in writing",
    moreNote:
      "These are in English only, and deliberately: each one has to be checked against the law of the country it is read in before it can be trusted there, and six confident translations of an unreviewed document would be worse than one honest original.",
  },

  journey: {
    intentTitle: "What's loudest in you right now?",
    intentSkip: "Skip — I know what I want",
    intents: {
      self: "Who am I, really",
      shifting: "Something's shifting and I don't know why",
      us: "Us — will this work",
      where: "Where I should live",
    },
    freeLabel: "yours, free, forever",
    freeNote: "These numbers cost nothing, ever. They are yours whether you read further or not.",
    calculated: "all eight systems · calculated",
    needsTimeRow: "Solar return · map",
    keepMySky: "Keep my sky",
    staysFree: "Everything above stays free, forever",
    dialogLabel: "Getting to know you",
    back: "Back to the landing",
    done: "done",
    continueCta: "Continue",
    orFaster: "or faster",
    withGoogle: "Continue with Google",
    nameTitle: "What should I call you?",
    nameSub: "A name isn't an account. Nothing is saved yet.",
    namePlaceholder: "Sofia",
    nameAria: "Your name",
    dateTitle: "When were you born?",
    dateSub: "The date alone already gives three systems.",
    timeTitle: "What time were you born?",
    timeSub:
      "Time gives houses, the solar return and your map. Without it those stay locked — we won't invent them.",
    hourLabel: "Hour",
    minuteLabel: "Min",
    meridiemLabel: "AM or PM",
    lockedWithoutTime: "Houses, solar return and map stay locked",
    placeTitle: "Where were you born?",
    placeSub: "City is enough. We resolve the historical time zone ourselves.",
    placePlaceholder: "Milan",
    buildMySky: "Build my sky",
    ceremony: [
      ["reading system 1 of 8 · natal chart", "Ten planets, twelve houses — your chart is drawn from real ephemeris data."],
      ["reading system 2 of 8 · numerology", "Your life path reduces to a number that prefers proof over belief."],
      ["reading system 3 of 8 · birth card", "One of twenty-two arcana, calculated from the date alone."],
      ["reading system 4 of 8 · transits", "Where the sky is now, against where it was when you started."],
      ["reading system 5 of 8 · compatibility", "Held open until you add a second person — nothing invented."],
      ["reading system 6 of 8 · solar return", "The year ahead, read from the minute the Sun comes back to its place."],
      ["reading system 7 of 8 · astrocartography", "Planetary lines across the map, drawn from your exact minute."],
      ["reading system 8 of 8 · cross-synthesis", "Nine axes. Where three traditions agree, that goes to your core."],
    ],
    ceremonySkip: "Skip the ceremony",
    authTitle: (name: string) => (name ? `Keep this, ${name}` : "Keep this"),
    authSub:
      "One tap and your eight systems, your portrait and your questions stay yours. No password, ever.",
    legalBefore: "By continuing you agree to the",
    legalTerms: "Terms",
    legalAnd: "and",
    legalPrivacy: "Privacy Policy",
    legalAfter: ". 16+.",
    handoffTitle: "Now read yourself slowly.",
    handoffSub: "Three rules that make this work — the only onboarding we'll ever give you.",
    rules: [
      "One chapter at a time. Sixteen at once is noise.",
      "When two systems disagree, don't pick a winner. That's the material.",
      "Ask me in your own words. Three questions are free.",
    ],
    /* The five below were `cabinet` and `sky` keys until the cabinet was
       removed. The portrait is what reads them — it names the Ascendant only
       when a birth time made one computable, tags the row that needs one, and
       prints the moon phase — so they moved to the group that reads them
       rather than keeping a group named after a screen nobody can open. */
    ascendant: "Ascendant",
    moonPhase: "Moon",
    needsTimeTag: "needs birth time",
    authSkip: "Not now — just show me the app",
    placeOffline: "I can't reach the place index right now. Try again in a moment.",
    phases: {
      "new moon": "new moon",
      "waxing crescent": "waxing crescent",
      "first quarter": "first quarter",
      "waxing gibbous": "waxing gibbous",
      "full moon": "full moon",
      "waning gibbous": "waning gibbous",
      "last quarter": "last quarter",
      "waning crescent": "waning crescent",
    },
  },

};

/**
 * The shape every locale must satisfy.
 *
 * Derived from `en` rather than hand-written on purpose: a key added to the
 * source without a translation becomes a compile error, which is the only
 * thing that keeps six locales in step once the copy starts moving.
 */
export type Dictionary = typeof en;
