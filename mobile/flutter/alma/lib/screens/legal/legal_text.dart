/// Пять юридических документов — в самом приложении, а не по ссылке.
///
/// Порт `mobile/ios/Alma/Screens/Settings/LegalText.swift`, слово в слово:
/// 37 разделов, 72 абзаца, 6 списков на 25 пунктов, 5 фактов,
/// 5 незаполненных фактов, 3 пропуска.
///
/// **Пункты списков считаются отдельно, и не зря.** Прежняя сверка считала
/// только блоки — а список остаётся одним блоком, из скольких бы пунктов он ни
/// состоял. Так и разошлись: из терминов выпал пункт про атаку на сервис, из
/// возвратов — четыре случая, при которых Alma поддерживает запрос без спора
/// («не сгенерировалось», «списали дважды», «списали после отмены», «сбой стоил
/// оплаченного месяца»), а заголовок раздела о четырнадцати днях пропал, и его
/// пять абзацев ушли в предыдущий раздел. Числа сходились, текста не было.
/// Тест `test/legal_text_test.dart` ловит теперь именно это.
///
/// **Почему они здесь, а не за ссылкой.** Guideline 3.1.2 требует рабочую
/// ссылку на условия и политику с того экрана, где продаётся подписка, а 5.1.1
/// — чтобы политика была достижима вообще. Рецензент открывает каждую. Ссылка
/// наружу — это ссылка, которая может лежать в тот день, когда идёт ревью, и
/// в порте она вела на `alma.pazl.ai`, который **не резолвится**: пять строк в
/// настройках открывали браузер с ошибкой. Текст в бинарнике не нуждается в
/// сети совсем.
///
/// **Этот файл — английский эталон; переводы живут рядом.** До 25.08.2026
/// документы были только по-английски — юридический довод проверяется по
/// праву той страны, где его читают (Codice del consumo ст. 9, CDC ст. 46,
/// языковые правила Франции). Владелец решил переводить: шесть зеркал
/// `legal_text_{ru,es,de,it,fr,pt}.dart` выбираются `LegalCatalog` по языку
/// приложения, их структуру блок в блок сторожит
/// `test/legal_catalog_test.dart`. Проверку переводов юристом по юрисдикциям
/// это не заменяет — она остаётся в открытых и сказана владельцу вслух.
///
/// **Пропуски были видны, а не выдуманы, — и потому заполнились.** Пока
/// фактов не было, они печатались помеченными дырами; 25.08.2026 владелец дал
/// адрес регистрации, номер файлинга и управляющего, и дыры стали фактами.
/// Незаполненным остался один VAT ID — налог считает Apple, своя регистрация
/// идёт, и документ так и говорит.
library;

/// Что стоит в документе: абзац, список, факт, ненайденный факт, пропуск.
sealed class LegalBlock {
  const LegalBlock();

  const factory LegalBlock.para(String text) = LegalPara;
  const factory LegalBlock.points(List<String> items) = LegalPoints;
  const factory LegalBlock.fact(String label, String value) = LegalFact;
  const factory LegalBlock.factBlank(String label, String value) = LegalFactBlank;
  const factory LegalBlock.blank(String what) = LegalBlank;
}

class LegalPara extends LegalBlock {
  const LegalPara(this.text);
  final String text;
}

class LegalPoints extends LegalBlock {
  const LegalPoints(this.items);
  final List<String> items;
}

class LegalFact extends LegalBlock {
  const LegalFact(this.label, this.value);
  final String label;
  final String value;
}

/// Факт, которого никто ещё не дал. Помечен, а не придуман.
class LegalFactBlank extends LegalBlock {
  const LegalFactBlank(this.label, this.value);
  final String label;
  final String value;
}

class LegalBlank extends LegalBlock {
  const LegalBlank(this.what);
  final String what;
}

class LegalSection {
  const LegalSection(this.title, this.blocks);
  final String title;
  final List<LegalBlock> blocks;
}

class LegalDoc {
  const LegalDoc({required this.lead, required this.sections});
  final String lead;
  final List<LegalSection> sections;
}

/// Какие документы есть. Порядок — тот же, что в настройках и в подвале
/// витрины.
enum LegalDocument { terms, privacy, refunds, subscriptionTerms, imprint }

class LegalText {
  const LegalText._();

  /// Дата в шапке каждого документа. Одна на все пять намеренно: их писали и
  /// проверяли вместе, и пять разных дат означали бы пять разных проверок.
  static const updated = '7 August 2026';

  /// Кто управляет Alma. Не кто её продаёт — см. [merchant].
  static const operatorName = 'Pazl LLC';

  /// Кто продаёт её **в этом приложении**. Магазин — продавец по документам
  /// для каждой встроенной покупки: он берёт деньги, выдаёт чек, считает и
  /// платит налог и держит деньги у себя.
  static const merchant = 'Apple';

  static const contact = 'hello@pazl.ai';

  /// Признание в начале каждого документа. Не украшение: публиковать
  /// человеческим языком то, что читается как устоявшееся право, до проверки
  /// по юрисдикциям — ровно та уверенная неправота, ради невозможности которой
  /// продукт существует.
  static const preamble = 'This is a plain-language account of how Alma actually works. It is written to be read, not skimmed past, and nothing in it contradicts what the app does. It is not legal advice.';

  static const footer = 'If a sentence on this page is unclear, that is our fault, not yours. Write to hello@pazl.ai and we will fix the sentence.';

  static LegalDoc of(LegalDocument which) => switch (which) {
        LegalDocument.terms => terms,
        LegalDocument.privacy => privacy,
        LegalDocument.refunds => refunds,
        LegalDocument.subscriptionTerms => subscriptionTerms,
        LegalDocument.imprint => imprint,
      };


  static const terms = LegalDoc(
    lead: 'What you get, what Alma will not do, and the few things we ask of you. Nothing here is a trick, and there is no clause below that contradicts a sentence above it.',
    sections: [
      LegalSection('What Alma is', [
        LegalBlock.para('Alma calculates a chart from your birth date, time and place, and writes readings from it. The calculation is arithmetic and is the same for everyone. The readings are written by a language model that is given your chart and is allowed to cite only what is in it.'),
        LegalBlock.para('Pazl LLC operates Alma. Inside this app, Apple sells it — see the subscription terms.'),
      ]),
      LegalSection('What Alma is not', [
        LegalBlock.para('Alma is not medical, legal or financial advice, and it does not predict events. It will not tell you whether to take the job, leave the person, or have the operation.'),
        LegalBlock.para('This is not a disclaimer bolted to the end of a page. It is a rule enforced where the readings are generated: Alma is instructed never to diagnose, never to advise on money or law, and never to state that something will happen. A reading that does any of those things is a fault in our system, not fine print you failed to read. Tell us at hello@pazl.ai and we will fix it.'),
        LegalBlock.para('If you are unwell, in danger, or making a decision with money or law in it, talk to someone qualified. Alma is for self-knowledge, and self-knowledge is not a second opinion.'),
      ]),
      LegalSection('Who may use it', [
        LegalBlock.para('Anyone aged 16 or over. You can read your chart, and even buy, without giving us an address: an unsigned-in visitor is already an account with an id, and what signing in adds is durability rather than permission.'),
        LegalBlock.para('But an account with no identity is an account nobody can get back into. On this phone your account lives in the keychain, so it survives the app closing — it does not survive the app being deleted, or the phone being replaced. Sign in with Apple, or with a link to an inbox, and the account follows you.'),
        LegalBlock.para('This matters most for something you have paid for. A purchase belongs to whichever Alma account claimed it first, so signing in before you reinstall is what makes "restore purchases" find them.'),
      ]),
      LegalSection('What we ask of you', [
        LegalBlock.points([
          'Enter your own birth data honestly. A guessed birth time produces a chart that is entirely plausible and completely wrong, and Alma cannot tell the difference.',
          'If you enter someone else\'s birth data for a compatibility reading, ask them first. It is their birth data, not yours.',
          'Do not scrape Alma, resell its readings, or present them as a product of your own. What Alma writes for you is yours to keep, print, quote and share.',
          'Do not attack the service or try to reach other people\'s charts.',
        ]),
      ]),
      LegalSection('What we owe you', [
        LegalBlock.para('The readings you bought outright, kept available while your account exists. One-time purchases are permanent; they do not expire when a subscription does.'),
        LegalBlock.para('A plan is the other case, and it is worth being exact about: readings written for you while a plan is running stay in your account when the plan ends, but they stop opening, because what a plan sells is the period rather than the text. That is the reason the archive is sold separately at all.'),
        LegalBlock.para('Alma will not be up every second of every year. Nobody\'s service is. If it is down when you want it, it will come back — and if an outage of ours cost you a month you paid for, we will support your refund request to Apple, because they are who holds the money.'),
        LegalBlock.para('If we change these terms, you get an email before the change takes effect, not a silently updated date at the top of a page. That letter is written by hand and sent to the address on your account, because Alma has no mailing list and nothing automatic that could send it.'),
        LegalBlock.para('Which means: if you have never given us an address, there is no channel that reaches you, and the date at the top of this page is the only notice there is. That is a reason to sign in, not a loophole we are pleased with.'),
      ]),
      LegalSection('If something goes wrong', [
        LegalBlock.para('If we cause you loss, our responsibility is limited to what you paid for the thing that went wrong. Alma is a reading, not a professional service, and it should not be relied on as one — which is the same sentence as the section above, in the language of liability.'),
        LegalBlock.para('Nothing here removes a right your own country gives you. Where the two disagree, your country wins.'),
      ]),
      LegalSection('Ending it', [
        LegalBlock.para('If you have signed in, you can delete your account in Settings, at any moment, without asking us and without explaining. It takes effect immediately and it takes your data with it — see the privacy page.'),
        LegalBlock.para('If you have not — reading without an account is allowed, and so is buying without one — the button in Settings has no account to attach the request to, so it asks you to sign in first. Sign in with the identity you paid with and it works. If you cannot, write to hello@pazl.ai and we do it by hand. That is a person and a working day rather than a button, and stating it is better than a sentence promising otherwise on a screen where the button is greyed out.'),
        LegalBlock.para('Deleting your Alma account does not cancel a subscription bought through the App Store. Apple holds that, and it is cancelled on Apple\'s own subscription screen — there is a button in Settings that opens it.'),
        LegalBlock.para('We may close an account that is attacking the service or using it against other people. If we do, you get the email and the reason — or, where there is no address on the account, the reason on request at hello@pazl.ai.'),
      ]),
      LegalSection('Law', [
        LegalBlock.para('These terms are governed by the law of Wyoming, United States — the state Pazl LLC is organised in — and disputes are heard in the courts of Wyoming.'),
        LegalBlock.para('Nothing in that sentence removes a right your own country gives you: where a consumer law of your country and this clause disagree, your country wins, as the section above already says.'),
      ]),
    ],
  );

  static const privacy = LegalDoc(
    lead: 'What Alma holds about you, why each thing is held, and what it would take to get rid of all of it. Every item below is a column that exists in a real table, not a category we thought sounded reassuring.',
    sections: [
      LegalSection('What is collected', [
        LegalBlock.points([
          'Your birth date, time and place, and the name you gave. This is the chart. Without it there is no product; with it, everything else Alma does is arithmetic on these five numbers.',
          'Your email address, if you signed in. Passwordless — the inbox is the account. Sign in with Apple may give us a relay address instead, and that is fine: we never need to know your real one.',
          'The readings written for you, so that a chapter you paid for says the same thing tomorrow, and so it is not written twice at our cost.',
          'Your questions to Alma and her answers, so a conversation has a memory.',
          'What you have bought, as a list of grants — which system, when, for how long. Not a card number: we have never had one and could not store one if we wanted to.',
          'A handful of funnel events — that a quiz was started, that a portrait was seen — with no content in them. They are counted, never read.',
        ]),
      ]),
      LegalSection('What is not collected', [
        LegalBlock.para('No payment details. Apple takes the payment in this app and holds the card; the only thing that reaches us is a signed statement that a purchase happened, which we check against Apple\'s own certificate before we act on it.'),
        LegalBlock.para('No advertising identifiers, no third-party analytics, no tracking across other apps or websites, no location beyond the birthplace you typed. There is nothing to opt out of because there is nothing running.'),
        LegalBlock.para('We do not sell or share personal information, in the sense either of those words has under the California Consumer Privacy Act or any other statute. There is no arrangement with anybody that would let us.'),
      ]),
      LegalSection('Who else sees it', [
        LegalBlock.points([
          'Anthropic, who run the model that writes the readings. Your birth date, your birth time, the name of your birthplace and your name if you gave one are sent, as they are stored — they are what the reading is written from. So are the calculated chart, the question you asked, and the short facts Alma remembers. A question you ask carries the last twelve messages of that conversation so it makes sense in context. Your email address is not sent and is not needed. Your birthplace coordinates are not sent either: the chart is computed here and only the result travels.',
          'Apple or Google, whichever store you got Alma from, for anything bought in this app. They see the purchase, not the chart.',
          'Our mail provider, for the two letters Alma sends: a sign-in link, and — for a plan bought outside the app stores — a notice before a renewal.',
          'Our hosting provider, who runs the machine the database is on.',
        ]),
        LegalBlock.para('That is the whole list. If it ever gets longer, this page changes before the arrangement starts, not after.'),
      ]),
      LegalSection('Where it lives, and for how long', [
        LegalBlock.para('On servers in the European Union. Readings and charts are kept while your account exists, because that is the point of them. Funnel events are kept as counts.'),
        LegalBlock.para('On this phone, your account token is in the keychain — encrypted by the system, excluded from backups, and never written anywhere a backup or another app can read it.'),
      ]),
      LegalSection('What you can do about it', [
        LegalBlock.points([
          'Export everything, as one file, from Settings. It is the actual database rows, not a summary.',
          'Delete everything, from Settings. It is immediate and it is real: the rows are deleted rather than flagged. Readings you paid for cannot be written again word for word, which is why the button asks you to type your address first.',
          'Ask us anything at hello@pazl.ai. A person answers.',
        ]),
        LegalBlock.para('Under the GDPR you also have the right to correct what we hold, to object to processing, and to complain to your national supervisory authority. The first two are the two buttons above; the third needs nothing from us.'),
      ]),
      LegalSection('Children', [
        LegalBlock.para('Alma is for people aged 16 and over and is rated accordingly on the App Store. We do not knowingly hold data about anybody younger. If you believe we do, write to hello@pazl.ai and it will be deleted the day we read it.'),
      ]),
      LegalSection('Who to write to', [
        LegalBlock.para('Pazl LLC is the controller. hello@pazl.ai reaches a person, not a ticket queue.'),
        LegalBlock.para('Pazl LLC has no establishment in the EU and has not yet appointed a representative under GDPR Art. 27. Until one is named on this page, every right this page lists is exercised the same way: by writing to hello@pazl.ai, where a person answers.'),
      ]),
    ],
  );

  static const refunds = LegalDoc(
    lead: 'Alma is not the seller of anything bought in this app. Apple is. That single fact decides most of what follows, so it goes first rather than in a footnote.',
    sections: [
      LegalSection('Apple is the merchant of record', [
        LegalBlock.para('When you buy something inside this app, your contract of sale is with Apple. They take the payment, they issue the receipt, they calculate and remit the tax, and they hold the money. Your card details never reach us.'),
        LegalBlock.para('So a refund is not a button we can press. It leaves their account, not ours, which is why refund requests go to them. We can support your request, and we do, but the decision and the transfer are theirs.'),
      ]),
      LegalSection('How to ask', [
        LegalBlock.points([
          'reportaproblem.apple.com, signed in with the Apple Account you bought with. That is the fastest route and it goes straight to the people holding the money. The same form is reachable from the receipt Apple emailed you.',
          'Or write to hello@pazl.ai with the Apple Account you bought with. We cannot issue the refund, but we can confirm to Apple what happened on our side, and we will tell you what they said even when the answer is no.',
        ]),
      ]),
      LegalSection('Where we support the request without arguing', [
        LegalBlock.para('These are our faults, or your right, and neither is a judgement call:'),
        LegalBlock.points([
          'The reading never generated, or generated and would not open.',
          'The chart was wrong because of an error on our side rather than a birth time you were unsure of.',
          'You were charged twice for the same thing.',
          'You were charged after cancelling.',
          'An outage of ours cost you a subscription month you had paid for.',
          'You changed your mind within fourteen days — see the withdrawal right below, which we do not treat as waived.',
        ]),
        LegalBlock.para('You do not have to prove any of this to us. If the record shows it, we say so to Apple, and we tell you we have.'),
      ]),
      LegalSection('Nothing is written until you open it', [
        LegalBlock.para('A chapter is generated the first time you open it, not at the moment you pay. The archive is forty-one chapters across eight systems, eight of which are the free samples anybody can read; buying it opens the other thirty-three, and opening them is not the same as writing them. Each one is written when you go to it, from your chart as it stands then, and stored so that it says the same thing every time afterwards.'),
        LegalBlock.para('That is the reason this page can say what it says next. At the second your card is charged, nothing has been delivered — and a promise that you have given up a right over text nobody has written yet is not a promise anybody should be asked to keep.'),
      ]),
      LegalSection('The 14-day withdrawal right, which we do not treat as waived', [
        LegalBlock.para('In the EU and the UK you have fourteen days to change your mind about something bought online. Digital content can be an exception to that, but only when three things have happened: you expressly agreed that we start immediately, you acknowledged that starting immediately costs you the right, and you were sent confirmation of both on something durable.'),
        LegalBlock.para('Through the App Store, Apple runs the purchase sheet and Apple sends the receipt — we do not control any of the three, and we are not going to stand on a waiver we did not obtain. If you tell us within fourteen days of buying that you have changed your mind, we support a full refund with Apple and we do not ask you why.'),
        LegalBlock.para('When the whole price comes back, what it bought closes: the archive stops opening, or the system you bought stops opening. Money back with the reading kept is not a refund, it is a hundred percent discount, and we would rather refuse the second than pretend it is the first.'),
        LegalBlock.para('We do not deduct for the chapters already written for you, and we do not split the purchase into the part that was performed and the part that was not. We could — we know exactly which chapters exist — but any figure we set for how much of a book you have read would be a number we invented, and one invented number is worse for this document than a policy that occasionally costs us a sale.'),
        LegalBlock.para('After the fourteen days, the list above is the policy: our faults, without argument, and otherwise a request Apple decides.'),
      ]),
      LegalSection('A year is not delivered on the first day', [
        LegalBlock.para('The yearly plan is a different case in law and in fact. It is not a thing handed over at once — it is twelve months of access to everything, including systems that are rewritten as the sky moves, and on day ten of it nothing like the whole has been performed. No consent at a checkout ends your right to withdraw from a service that has barely started.'),
        LegalBlock.para('So: withdraw from a plan within fourteen days and what should come back is the part of the period you have not used, worked out on the days that have passed, and the plan ends there rather than running on. We ask Apple for exactly that and we close the access at our end whether or not they agree, because the second half is ours to do.'),
      ]),
      LegalSection('The model withdrawal form', [
        LegalBlock.para('You do not have to use a form — an email saying you have changed your mind is enough — but the law requires one to be offered, so here it is:'),
        LegalBlock.para('To Pazl LLC, hello@pazl.ai — I hereby give notice that I withdraw from my contract for the supply of the following digital content: [what you bought]. Ordered on [date]. Name of consumer: [your name]. Email address used: [your address]. Date: [today].'),
        LegalBlock.para('Addressed to us rather than to Apple on purpose: the contract for the content is with us, the money is held by them, and you should not have to work out which of the two to write to. We forward it.'),
      ]),
    ],
  );

  static const subscriptionTerms = LegalDoc(
    lead: 'What renews, what it costs, and how to stop it — which, for a plan bought in this app, happens on Apple\'s own subscription screen rather than on ours. Where something is less tidy than that, it is written down rather than left out.',
    sections: [
      LegalSection('What renews', [
        LegalBlock.para('The price list carries two recurring plans. The yearly one opens everything Alma has written for you — every system, every chapter — for a year. The monthly one opens only the three systems that move with the date: transits, the solar return, and compatibility. Renting a natal chart would be rent on numbers that have not changed since you were born, so the archive is not part of it.'),
        LegalBlock.para('Either plan renews automatically on its own cycle until you stop it. Payment is charged to your Apple Account at confirmation of purchase. It renews unless auto-renewal is turned off at least 24 hours before the end of the current period, and your account is charged for the renewal within 24 hours of the end of that period.'),
        LegalBlock.para('A payment opens slightly more than the period it is for — thirty-one days for a month, three hundred and sixty-five for a year, counted from whichever is later, the day you pay or the day your current access ends. The extra days do not stack up; they exist so that a renewal charged a few hours late can never lock you out of a period you have already paid for.'),
        LegalBlock.para('The price is the one shown on the purchase sheet. It is not printed on this page on purpose: Apple sets and charges the price for your storefront in your own currency with your own tax, and their number is the one that is true.'),
      ]),
      LegalSection('A plan is rented, not bought', [
        LegalBlock.para('The yearly plan opens everything for a year. It is not a purchase of the archive. When the year ends and you have not renewed, the readings that were written for you during it stay in your account — nothing is deleted — but they stop opening, the same as any chapter you have not paid for.'),
        LegalBlock.para('If what you want is text that is yours whatever happens next, that is the archive, bought once. Anything bought outright is permanent and is untouched by a plan starting, ending or being cancelled.'),
      ]),
      LegalSection('Who tells you before you are charged', [
        LegalBlock.para('For a plan bought in this app, Apple does. Apple sends the receipt and Apple sends the renewal notice, because Apple is the seller and holds the payment method. We do not send either, and a page of ours promising otherwise would be a promise we cannot keep.'),
        LegalBlock.para('For a plan bought on our website with a card, we do: three days before a renewal, an email goes out saying what is about to be taken, in the currency it will be taken in, and on what date. It is not a marketing email and there is no unsubscribe on it, because a subscription you have forgotten about is the oldest trick in this industry and we would rather not be in that business.'),
      ]),
      LegalSection('The price you agreed to is the price that renews', [
        LegalBlock.para('Nothing in Alma can change what an existing plan costs. A new price on the price list applies to new purchases; your plan goes on billing what it was opened at. Apple additionally asks you to confirm any price increase before it takes effect, and will cancel the subscription rather than charge you the new price if you do not.'),
      ]),
      LegalSection('Cancelling', [
        LegalBlock.para('A subscription bought in this app is cancelled on Apple\'s subscription screen: Settings → Plan → Manage this subscription in the App Store, which opens it directly. Or, outside Alma: the Settings app → your name → Subscriptions.'),
        LegalBlock.para('We cannot cancel it for you, and we will not pretend to. Apple holds the payment method; a flag on our side saying "cancelled" does not stop a card being charged, and somebody who believed it would find out on a statement. If you ask us to cancel, the app says exactly this and sends you to the right screen rather than writing anything.'),
        LegalBlock.para('A plan bought on our website with a card is different, and there the two taps are real: Settings → Plan → Cancel subscription → Confirm. No email to write, no reason to give, no call, and no offer standing between you and the second tap.'),
        LegalBlock.para('Cancelling is not a refund of the period you are in, and nothing is taken away at the moment you cancel. What is and is not refundable — including the fourteen days in which you can withdraw from a plan outright — is on the refunds page.'),
      ]),
      LegalSection('What you keep afterwards', [
        LegalBlock.para('Everything you bought outright. A system, or the whole archive, bought as a one-time purchase is permanent and is not affected by a subscription ending.'),
        LegalBlock.para('Your account, your chart and your conversations stay as they are. Ending a subscription is not deleting an account — that is a separate, deliberate act in Settings.'),
      ]),
      LegalSection('One reading first, the rest later', [
        LegalBlock.para('If you buy a single system and then decide within thirty days that you want the rest, the rest of the archive is offered at its price less what you already paid for that reading. Nothing to claim, nothing to refund first — the reduced price is simply what you are charged.'),
        LegalBlock.para('It is offered while you hold one system and nothing wider. After thirty days the offer is gone and the reading you bought remains yours. The reduction applies to the archive; a plan is priced on its own.'),
      ]),
      LegalSection('If a payment fails', [
        LegalBlock.para('Nothing is taken away. A card that bounces is usually a card that works on the retry, and Apple retries for a while — the person whose payment failed is the last person who should be locked out while it is being sorted out.'),
        LegalBlock.para('If the retries never succeed, the plan is simply not extended: your access runs to the end of the period you already paid for and stops there. Anything you bought outright is untouched by any of this. Subscribing again starts a new period from the day it is paid.'),
      ]),
      LegalSection('Invoices and tax', [
        LegalBlock.para('Apple is the seller of record for anything bought in this app. They issue the receipt, they handle VAT, GST and sales tax where it applies, and their receipt is the document your accountant wants. It is at reportaproblem.apple.com and in the email Apple sent you.'),
      ]),
    ],
  );

  static const imprint = LegalDoc(
    lead: 'Who is behind Alma, in the form Germany\'s Telemediengesetz §5 and Italy\'s and France\'s equivalents ask for. Everything not yet supplied is marked as missing rather than filled in with something plausible.',
    sections: [
      LegalSection('Operator', [
        LegalBlock.fact('Company', 'Pazl LLC'),
        LegalBlock.fact('Form', 'Limited liability company'),
        LegalBlock.fact('Jurisdiction', 'Wyoming, United States'),
        LegalBlock.fact('Registered address', '30 N Gould St Ste R, Sheridan, Wyoming 82801'),
        LegalBlock.fact('Registration number', '2026-002034771'),
        LegalBlock.fact('Represented by', 'Anatolii Mikhailov'),
      ]),
      LegalSection('Contact', [
        LegalBlock.fact('Email', 'hello@pazl.ai'),
        LegalBlock.para('A person reads it. There is no telephone number, and rather than print one that reaches an answering machine, this says so.'),
      ]),
      LegalSection('Selling in this app', [
        LegalBlock.fact('Merchant of record', 'Apple'),
        LegalBlock.para('Anything bought inside this app is sold by Apple, who take the payment, issue the receipt and remit the tax. The entity on your statement depends on your storefront — Apple Inc., Apple Distribution International Ltd. or iTunes K.K. — and the receipt Apple sends you names the one that charged you.'),
      ]),
      LegalSection('Value added tax', [
        LegalBlock.factBlank('VAT identification', 'VAT ID'),
        LegalBlock.para('Alma is sold through Apple, who account for VAT and GST where it applies. A VAT number of our own is being registered.'),
      ]),
      LegalSection('Online dispute resolution', [
        LegalBlock.para('The European Commission\'s ODR platform closed in July 2025 and is not linked here, because a link to a platform that no longer exists is worse than no link. We are not obliged to use, and do not commit to, an alternative dispute-resolution body. Write to hello@pazl.ai and a person will answer.'),
      ]),
      LegalSection('Responsible for content', [
        LegalBlock.fact('Under §18 (2) MStV', 'Anatolii Mikhailov · 30 N Gould St Ste R, Sheridan, Wyoming 82801'),
      ]),
    ],
  );
}
