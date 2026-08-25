/// Итальянский перевод пяти юридических документов.
///
/// Структура зеркалит `legal_text.dart` раздел в раздел и блок в блок:
/// те же 8/7/7/9/6 разделов, те же виды блоков в том же порядке, те же
/// количества пунктов в списках — иначе сверка, описанная в шапке
/// оригинала, не поймает расхождение. Обращение — «tu», как весь продукт.
/// Имена собственные и технические значения (Pazl LLC, Apple,
/// hello@pazl.ai, reportaproblem.apple.com, Wyoming, GDPR, CCPA,
/// Anthropic) не переводятся; в фактах переведена метка, значение
/// оставлено как есть; в незаполненных фактах слаг остаётся английским,
/// чтобы дыру заполняли по тому же имени, что и в оригинале.
library;

import 'legal_text.dart';

class LegalTextIt {
  const LegalTextIt._();

  /// Дата в шапке каждого документа — та же, что у английского оригинала:
  /// перевод не меняет дату проверки текста.
  static const updated = '7 agosto 2026';

  static const preamble =
      'Questo è un resoconto in linguaggio semplice di come Alma funziona davvero. È scritto per essere letto, non per essere scorso in fretta, e niente qui dentro contraddice ciò che l\'app fa. Non è una consulenza legale.';

  static const footer =
      'Se una frase di questa pagina non è chiara, la colpa è nostra, non tua. Scrivi a hello@pazl.ai e correggeremo la frase.';

  static LegalDoc of(LegalDocument which) => switch (which) {
        LegalDocument.terms => terms,
        LegalDocument.privacy => privacy,
        LegalDocument.refunds => refunds,
        LegalDocument.subscriptionTerms => subscriptionTerms,
        LegalDocument.imprint => imprint,
      };

  static const terms = LegalDoc(
    lead:
        'Che cosa ricevi, che cosa Alma non farà, e le poche cose che ti chiediamo. Niente qui è un trucco, e non c\'è nessuna clausola più sotto che contraddica una frase più sopra.',
    sections: [
      LegalSection('Che cos\'è Alma', [
        LegalBlock.para(
            'Alma calcola un tema dalla tua data, ora e luogo di nascita, e da lì scrive le letture. Il calcolo è aritmetica ed è uguale per tutti. Le letture sono scritte da un modello linguistico che riceve il tuo tema e può citare soltanto ciò che vi si trova.'),
        LegalBlock.para(
            'Pazl LLC gestisce Alma. Dentro questa app la vende Apple — vedi i termini di abbonamento.'),
      ]),
      LegalSection('Che cosa Alma non è', [
        LegalBlock.para(
            'Alma non è una consulenza medica, legale o finanziaria, e non predice eventi. Non ti dirà se accettare il lavoro, lasciare la persona o sottoporti all\'operazione.'),
        LegalBlock.para(
            'Questa non è un\'avvertenza appiccicata in fondo a una pagina. È una regola applicata là dove le letture vengono generate: Alma ha l\'istruzione di non fare mai diagnosi, di non dare mai consigli su denaro o questioni legali, e di non affermare mai che qualcosa accadrà. Una lettura che fa una di queste cose è un difetto del nostro sistema, non una postilla che non hai letto. Segnalacelo a hello@pazl.ai e lo correggeremo.'),
        LegalBlock.para(
            'Se stai male, sei in pericolo, o stai prendendo una decisione in cui entrano denaro o questioni legali, parla con qualcuno di qualificato. Alma serve alla conoscenza di sé, e la conoscenza di sé non è un secondo parere.'),
      ]),
      LegalSection('Chi può usarla', [
        LegalBlock.para(
            'Chiunque abbia almeno 16 anni. Puoi leggere il tuo tema, e persino comprare, senza darci un indirizzo: un visitatore che non ha effettuato l\'accesso è già un account con un id, e ciò che l\'accesso aggiunge è la durata, non il permesso.'),
        LegalBlock.para(
            'Ma un account senza identità è un account in cui nessuno può rientrare. Su questo telefono il tuo account vive nel portachiavi, quindi sopravvive alla chiusura dell\'app — non sopravvive alla cancellazione dell\'app, né alla sostituzione del telefono. Accedi con Apple, o con un link a una casella di posta, e l\'account ti segue.'),
        LegalBlock.para(
            'Questo conta soprattutto per ciò che hai pagato. Un acquisto appartiene all\'account Alma che lo ha rivendicato per primo, quindi accedere prima di reinstallare è ciò che permette a «ripristina acquisti» di ritrovarli.'),
      ]),
      LegalSection('Che cosa ti chiediamo', [
        LegalBlock.points([
          'Inserisci i tuoi dati di nascita con onestà. Un\'ora di nascita indovinata produce un tema del tutto plausibile e completamente sbagliato, e Alma non può accorgersi della differenza.',
          'Se inserisci i dati di nascita di qualcun altro per una lettura di compatibilità, chiediglielo prima. Sono i suoi dati di nascita, non i tuoi.',
          'Non fare scraping di Alma, non rivendere le sue letture e non presentarle come un prodotto tuo. Ciò che Alma scrive per te è tuo: puoi conservarlo, stamparlo, citarlo e condividerlo.',
          'Non attaccare il servizio e non cercare di raggiungere i temi di altre persone.',
        ]),
      ]),
      LegalSection('Che cosa ti dobbiamo', [
        LegalBlock.para(
            'Le letture che hai comprato una tantum, tenute disponibili finché esiste il tuo account. Gli acquisti una tantum sono permanenti; non scadono quando scade un abbonamento.'),
        LegalBlock.para(
            'Un piano è l\'altro caso, e vale la pena essere precisi: le letture scritte per te mentre un piano è attivo restano nel tuo account quando il piano finisce, ma smettono di aprirsi, perché ciò che un piano vende è il periodo, non il testo. È questa la ragione per cui l\'archivio è venduto a parte.'),
        LegalBlock.para(
            'Alma non sarà attiva ogni secondo di ogni anno. Nessun servizio lo è. Se è giù quando la vuoi, tornerà — e se un\'interruzione nostra ti è costata un mese che avevi pagato, sosterremo la tua richiesta di rimborso presso Apple, perché sono loro a tenere i soldi.'),
        LegalBlock.para(
            'Se cambiamo questi termini, ricevi un\'email prima che il cambiamento entri in vigore, non una data aggiornata in silenzio in cima a una pagina. Quella lettera è scritta a mano e inviata all\'indirizzo del tuo account, perché Alma non ha una mailing list e niente di automatico che potrebbe inviarla.'),
        LegalBlock.para(
            'Il che significa: se non ci hai mai dato un indirizzo, non esiste un canale che ti raggiunga, e la data in cima a questa pagina è l\'unico avviso che c\'è. È una ragione per accedere, non una scappatoia di cui siamo contenti.'),
      ]),
      LegalSection('Se qualcosa va storto', [
        LegalBlock.para(
            'Se ti causiamo un danno, la nostra responsabilità è limitata a quanto hai pagato per la cosa che è andata storta. Alma è una lettura, non un servizio professionale, e non va trattata come tale — che è la stessa frase della sezione qui sopra, nel linguaggio della responsabilità.'),
        LegalBlock.para(
            'Niente qui ti toglie un diritto che il tuo paese ti riconosce. Dove i due sono in disaccordo, vince il tuo paese.'),
      ]),
      LegalSection('Come si chiude', [
        LegalBlock.para(
            'Se hai effettuato l\'accesso, puoi eliminare il tuo account nelle Impostazioni, in qualsiasi momento, senza chiedercelo e senza spiegazioni. Ha effetto immediato e porta con sé i tuoi dati — vedi la pagina sulla privacy.'),
        LegalBlock.para(
            'Se non l\'hai fatto — leggere senza account è permesso, e lo è anche comprare — il pulsante nelle Impostazioni non ha un account a cui collegare la richiesta, quindi ti chiede prima di accedere. Accedi con l\'identità con cui hai pagato e funziona. Se non puoi, scrivi a hello@pazl.ai e lo facciamo a mano. Questo significa una persona e un giorno lavorativo invece di un pulsante, e dirlo è meglio di una frase che promette il contrario su una schermata dove il pulsante è disattivato.'),
        LegalBlock.para(
            'Eliminare il tuo account Alma non annulla un abbonamento comprato tramite l\'App Store. Lo detiene Apple, e si annulla nella schermata abbonamenti di Apple — nelle Impostazioni c\'è un pulsante che la apre.'),
        LegalBlock.para(
            'Possiamo chiudere un account che attacca il servizio o lo usa contro altre persone. Se lo facciamo, ricevi l\'email e la ragione — o, se sull\'account non c\'è un indirizzo, la ragione su richiesta a hello@pazl.ai.'),
      ]),
      LegalSection('Legge applicabile', [
        LegalBlock.para(
            'Questi termini sono regolati dalla legge del Wyoming, United States — lo stato in cui Pazl LLC è costituita — e le controversie sono decise dai tribunali del Wyoming.'),
        LegalBlock.para(
            'Niente in quella frase ti toglie un diritto che il tuo paese ti riconosce: dove una legge a tutela del consumatore del tuo paese e questa clausola sono in disaccordo, vince il tuo paese, come dice già la sezione qui sopra.'),
      ]),
    ],
  );

  static const privacy = LegalDoc(
    lead:
        'Che cosa Alma conserva su di te, perché ogni cosa è conservata, e che cosa servirebbe per liberarsi di tutto. Ogni voce qui sotto è una colonna che esiste in una tabella reale, non una categoria che ci sembrava rassicurante.',
    sections: [
      LegalSection('Che cosa viene raccolto', [
        LegalBlock.points([
          'La tua data, ora e luogo di nascita, e il nome che hai indicato. Questo è il tema. Senza non c\'è prodotto; con esso, tutto il resto che Alma fa è aritmetica su questi cinque numeri.',
          'Il tuo indirizzo email, se hai effettuato l\'accesso. Senza password — la casella di posta è l\'account. Accedendo con Apple potremmo ricevere un indirizzo di inoltro al posto del tuo, e va benissimo: non abbiamo mai bisogno di conoscere quello vero.',
          'Le letture scritte per te, perché un capitolo che hai pagato dica domani la stessa cosa, e perché non venga scritto due volte a nostre spese.',
          'Le tue domande ad Alma e le sue risposte, perché una conversazione abbia una memoria.',
          'Che cosa hai comprato, come elenco di diritti — quale sistema, quando, per quanto tempo. Non un numero di carta: non ne abbiamo mai avuto uno e non potremmo conservarlo nemmeno volendo.',
          'Una manciata di eventi di funnel — che un quiz è stato iniziato, che un ritratto è stato visto — senza alcun contenuto dentro. Vengono contati, mai letti.',
        ]),
      ]),
      LegalSection('Che cosa non viene raccolto', [
        LegalBlock.para(
            'Nessun dato di pagamento. In questa app il pagamento lo prende Apple, che custodisce la carta; l\'unica cosa che ci arriva è una dichiarazione firmata che un acquisto è avvenuto, che verifichiamo con il certificato di Apple stessa prima di agire di conseguenza.'),
        LegalBlock.para(
            'Nessun identificatore pubblicitario, nessuna analitica di terze parti, nessun tracciamento su altre app o siti, nessuna posizione oltre il luogo di nascita che hai digitato. Non c\'è niente da cui fare opt-out perché non c\'è niente in funzione.'),
        LegalBlock.para(
            'Non vendiamo né condividiamo informazioni personali, in nessuno dei sensi che queste parole hanno nel California Consumer Privacy Act o in qualsiasi altra legge. Non esiste alcun accordo con nessuno che ce lo permetterebbe.'),
      ]),
      LegalSection('Chi altro li vede', [
        LegalBlock.points([
          'Anthropic, che gestisce il modello che scrive le letture. La tua data di nascita, la tua ora di nascita, il nome del tuo luogo di nascita e il tuo nome, se lo hai dato, vengono inviati così come sono conservati — sono ciò da cui la lettura viene scritta. Lo stesso vale per il tema calcolato, la domanda che hai posto e i brevi fatti che Alma ricorda. Una domanda che poni porta con sé gli ultimi dodici messaggi di quella conversazione perché abbia senso nel contesto. Il tuo indirizzo email non viene inviato e non serve. Nemmeno le coordinate del tuo luogo di nascita vengono inviate: il tema è calcolato qui e viaggia solo il risultato.',
          'Apple o Google, a seconda dello store da cui hai preso Alma, per qualsiasi acquisto in questa app. Vedono l\'acquisto, non il tema.',
          'Il nostro fornitore di posta, per le due lettere che Alma invia: un link di accesso e — per un piano comprato fuori dagli app store — un avviso prima di un rinnovo.',
          'Il nostro fornitore di hosting, che gestisce la macchina su cui sta il database.',
        ]),
        LegalBlock.para(
            'Questa è la lista intera. Se mai dovesse allungarsi, questa pagina cambia prima che l\'accordo cominci, non dopo.'),
      ]),
      LegalSection('Dove vivono, e per quanto tempo', [
        LegalBlock.para(
            'Su server nell\'Unione Europea. Letture e temi sono conservati finché esiste il tuo account, perché è questo il loro senso. Gli eventi di funnel sono conservati come conteggi.'),
        LegalBlock.para(
            'Su questo telefono, il token del tuo account sta nel portachiavi — cifrato dal sistema, escluso dai backup, e mai scritto in un posto che un backup o un\'altra app possano leggere.'),
      ]),
      LegalSection('Che cosa puoi farci', [
        LegalBlock.points([
          'Esportare tutto, in un unico file, dalle Impostazioni. Sono le righe reali del database, non un riassunto.',
          'Eliminare tutto, dalle Impostazioni. È immediato ed è reale: le righe vengono eliminate, non contrassegnate. Le letture che hai pagato non possono essere riscritte parola per parola, ed è per questo che il pulsante ti chiede prima di digitare il tuo indirizzo.',
          'Chiederci qualsiasi cosa a hello@pazl.ai. Risponde una persona.',
        ]),
        LegalBlock.para(
            'In base al GDPR hai anche il diritto di rettificare ciò che conserviamo, di opporti al trattamento e di presentare reclamo alla tua autorità di controllo nazionale. I primi due sono i due pulsanti qui sopra; il terzo non ha bisogno di niente da parte nostra.'),
      ]),
      LegalSection('Minori', [
        LegalBlock.para(
            'Alma è per persone dai 16 anni in su ed è classificata di conseguenza sull\'App Store. Non conserviamo consapevolmente dati su nessuno di più giovane. Se credi che lo stiamo facendo, scrivi a hello@pazl.ai e saranno eliminati il giorno stesso in cui leggiamo il messaggio.'),
      ]),
      LegalSection('A chi scrivere', [
        LegalBlock.para(
            'Pazl LLC è il titolare del trattamento. hello@pazl.ai raggiunge una persona, non una coda di ticket.'),
        LegalBlock.para(
            'Pazl LLC non ha uno stabilimento nell\'UE e non ha ancora nominato un rappresentante ai sensi dell\'art. 27 del GDPR. Finché su questa pagina non ne verrà indicato uno, ogni diritto elencato in questa pagina si esercita allo stesso modo: scrivendo a hello@pazl.ai, dove risponde una persona.'),
      ]),
    ],
  );

  static const refunds = LegalDoc(
    lead:
        'Alma non è il venditore di niente di ciò che si compra in questa app. Lo è Apple. Questo singolo fatto decide gran parte di ciò che segue, quindi sta all\'inizio e non in una nota a piè di pagina.',
    sections: [
      LegalSection('Apple è il venditore ufficiale', [
        LegalBlock.para(
            'Quando compri qualcosa dentro questa app, il tuo contratto di vendita è con Apple. Sono loro a prendere il pagamento, a emettere la ricevuta, a calcolare e versare le imposte, e a tenere i soldi. I dati della tua carta non ci raggiungono mai.'),
        LegalBlock.para(
            'Quindi un rimborso non è un pulsante che possiamo premere. Esce dal loro conto, non dal nostro, ed è per questo che le richieste di rimborso vanno a loro. Possiamo sostenere la tua richiesta, e lo facciamo, ma la decisione e il trasferimento sono loro.'),
      ]),
      LegalSection('Come chiedere', [
        LegalBlock.points([
          'reportaproblem.apple.com, con l\'accesso fatto con l\'Apple Account con cui hai comprato. È la via più rapida e va dritta a chi tiene i soldi. Lo stesso modulo è raggiungibile dalla ricevuta che Apple ti ha inviato per email.',
          'Oppure scrivi a hello@pazl.ai indicando l\'Apple Account con cui hai comprato. Non possiamo emettere il rimborso, ma possiamo confermare ad Apple che cosa è successo dalla nostra parte, e ti diremo che cosa hanno risposto anche quando la risposta è no.',
        ]),
      ]),
      LegalSection('Quando sosteniamo la richiesta senza discutere', [
        LegalBlock.para(
            'Questi sono errori nostri, o un tuo diritto, e in nessuno dei due casi è questione di giudizio:'),
        LegalBlock.points([
          'La lettura non è mai stata generata, oppure è stata generata e non si apriva.',
          'Il tema era sbagliato per un errore dalla nostra parte, non per un\'ora di nascita di cui non eri sicuro.',
          'Ti hanno addebitato due volte la stessa cosa.',
          'Ti hanno addebitato dopo che avevi annullato.',
          'Un\'interruzione nostra ti è costata un mese di abbonamento che avevi pagato.',
          'Hai cambiato idea entro quattordici giorni — vedi più sotto il diritto di recesso, che non consideriamo rinunciato.',
        ]),
        LegalBlock.para(
            'Non devi dimostrarci niente di tutto questo. Se i registri lo mostrano, lo diciamo ad Apple, e ti diciamo di averlo fatto.'),
      ]),
      LegalSection('Niente viene scritto finché non lo apri', [
        LegalBlock.para(
            'Un capitolo viene generato la prima volta che lo apri, non nel momento in cui paghi. L\'archivio è fatto di quarantuno capitoli in otto sistemi, otto dei quali sono gli assaggi gratuiti che chiunque può leggere; comprarlo apre gli altri trentatré, e aprirli non è lo stesso che scriverli. Ciascuno viene scritto quando ci arrivi, dal tuo tema com\'è in quel momento, e conservato perché dica la stessa cosa ogni volta successiva.'),
        LegalBlock.para(
            'È questa la ragione per cui questa pagina può dire ciò che dice subito dopo. Nel secondo in cui la tua carta viene addebitata, niente è stato consegnato — e una promessa di aver rinunciato a un diritto su un testo che nessuno ha ancora scritto non è una promessa che si dovrebbe chiedere a qualcuno di mantenere.'),
      ]),
      LegalSection('Il diritto di recesso di 14 giorni, che non consideriamo rinunciato', [
        LegalBlock.para(
            'Nell\'UE e nel Regno Unito hai quattordici giorni per cambiare idea su qualcosa comprato online. I contenuti digitali possono essere un\'eccezione, ma solo quando sono accadute tre cose: hai espressamente acconsentito che iniziassimo subito, hai preso atto che iniziare subito ti costa il diritto, e ti è stata inviata conferma di entrambe le cose su un supporto durevole.'),
        LegalBlock.para(
            'Tramite l\'App Store, è Apple a gestire la schermata di acquisto ed è Apple a inviare la ricevuta — non controlliamo nessuna delle tre cose, e non abbiamo intenzione di appellarci a una rinuncia che non abbiamo ottenuto. Se ci dici entro quattordici giorni dall\'acquisto che hai cambiato idea, sosteniamo un rimborso completo presso Apple e non ti chiediamo perché.'),
        LegalBlock.para(
            'Quando torna indietro l\'intero prezzo, ciò che aveva comprato si chiude: l\'archivio smette di aprirsi, o smette di aprirsi il sistema che avevi comprato. Soldi indietro con la lettura che resta non è un rimborso, è uno sconto del cento per cento, e preferiamo rifiutare il secondo piuttosto che fingere che sia il primo.'),
        LegalBlock.para(
            'Non detraiamo niente per i capitoli già scritti per te, e non dividiamo l\'acquisto nella parte eseguita e in quella non eseguita. Potremmo — sappiamo esattamente quali capitoli esistono — ma qualsiasi cifra fissassimo per quanto di un libro hai letto sarebbe un numero inventato da noi, e un numero inventato è peggio, per questo documento, di una politica che ogni tanto ci costa una vendita.'),
        LegalBlock.para(
            'Passati i quattordici giorni, la politica è l\'elenco qui sopra: i nostri errori, senza discutere, e per il resto una richiesta che decide Apple.'),
      ]),
      LegalSection('Un anno non viene consegnato il primo giorno', [
        LegalBlock.para(
            'Il piano annuale è un caso diverso in diritto e nei fatti. Non è una cosa consegnata in una volta sola — sono dodici mesi di accesso a tutto, compresi i sistemi che vengono riscritti man mano che il cielo si muove, e al decimo giorno niente che assomigli all\'intero è stato eseguito. Nessun consenso dato a una cassa mette fine al tuo diritto di recedere da un servizio appena iniziato.'),
        LegalBlock.para(
            'Quindi: recedi da un piano entro quattordici giorni e ciò che deve tornare indietro è la parte del periodo che non hai usato, calcolata sui giorni trascorsi, e il piano finisce lì invece di proseguire. Chiediamo ad Apple esattamente questo e chiudiamo l\'accesso dalla nostra parte che siano d\'accordo o no, perché la seconda metà spetta a noi.'),
      ]),
      LegalSection('Il modulo tipo di recesso', [
        LegalBlock.para(
            'Non sei obbligato a usare un modulo — basta un\'email in cui dici che hai cambiato idea — ma la legge richiede che ne venga offerto uno, quindi eccolo:'),
        LegalBlock.para(
            'A Pazl LLC, hello@pazl.ai — Con la presente comunico il recesso dal mio contratto di fornitura del seguente contenuto digitale: [che cosa hai comprato]. Ordinato il [data]. Nome del consumatore: [il tuo nome]. Indirizzo email usato: [il tuo indirizzo]. Data: [oggi].'),
        LegalBlock.para(
            'Indirizzato a noi e non ad Apple di proposito: il contratto per il contenuto è con noi, i soldi li tiene Apple, e non dovresti essere tu a dover capire a quale dei due scrivere. Lo inoltriamo noi.'),
      ]),
    ],
  );

  static const subscriptionTerms = LegalDoc(
    lead:
        'Che cosa si rinnova, quanto costa e come fermarlo — cosa che, per un piano comprato in questa app, avviene nella schermata abbonamenti di Apple e non nella nostra. Dove qualcosa è meno ordinato di così, è scritto qui invece di essere lasciato fuori.',
    sections: [
      LegalSection('Che cosa si rinnova', [
        LegalBlock.para(
            'Il listino comprende due piani ricorrenti. Quello annuale apre tutto ciò che Alma ha scritto per te — ogni sistema, ogni capitolo — per un anno. Quello mensile apre solo i tre sistemi che si muovono con la data: i transiti, la rivoluzione solare e la compatibilità. Affittare un tema natale sarebbe un affitto su numeri che non cambiano da quando sei nato, quindi l\'archivio non ne fa parte.'),
        LegalBlock.para(
            'Entrambi i piani si rinnovano automaticamente secondo il proprio ciclo finché non li fermi. Il pagamento è addebitato sul tuo Apple Account alla conferma dell\'acquisto. Il piano si rinnova a meno che il rinnovo automatico non venga disattivato almeno 24 ore prima della fine del periodo in corso, e l\'addebito del rinnovo avviene sul tuo account entro 24 ore dalla fine di quel periodo.'),
        LegalBlock.para(
            'Un pagamento apre un po\' più del periodo a cui si riferisce — trentun giorni per un mese, trecentosessantacinque per un anno, contati dal più tardo tra il giorno in cui paghi e il giorno in cui finisce il tuo accesso attuale. I giorni in più non si accumulano; esistono perché un rinnovo addebitato con qualche ora di ritardo non possa mai chiuderti fuori da un periodo che hai già pagato.'),
        LegalBlock.para(
            'Il prezzo è quello mostrato nella schermata di acquisto. Non è stampato in questa pagina di proposito: Apple stabilisce e addebita il prezzo per il tuo storefront nella tua valuta con le tue imposte, e il numero vero è il loro.'),
      ]),
      LegalSection('Un piano si affitta, non si compra', [
        LegalBlock.para(
            'Il piano annuale apre tutto per un anno. Non è un acquisto dell\'archivio. Quando l\'anno finisce e non hai rinnovato, le letture scritte per te durante quell\'anno restano nel tuo account — niente viene eliminato — ma smettono di aprirsi, come qualsiasi capitolo che non hai pagato.'),
        LegalBlock.para(
            'Se ciò che vuoi è un testo che resti tuo qualunque cosa accada dopo, quello è l\'archivio, comprato una volta sola. Tutto ciò che è comprato una tantum è permanente e non è toccato da un piano che inizia, finisce o viene annullato.'),
      ]),
      LegalSection('Chi ti avvisa prima dell\'addebito', [
        LegalBlock.para(
            'Per un piano comprato in questa app, lo fa Apple. Apple invia la ricevuta e Apple invia l\'avviso di rinnovo, perché Apple è il venditore e detiene il metodo di pagamento. Noi non inviamo né l\'una né l\'altro, e una nostra pagina che promettesse il contrario sarebbe una promessa che non possiamo mantenere.'),
        LegalBlock.para(
            'Per un piano comprato sul nostro sito con una carta, lo facciamo noi: tre giorni prima di un rinnovo parte un\'email che dice che cosa sta per essere prelevato, nella valuta in cui sarà prelevato, e in quale data. Non è un\'email di marketing e non ha un link di disiscrizione, perché un abbonamento di cui ti sei dimenticato è il trucco più vecchio di questo settore e preferiamo non essere in quel mestiere.'),
      ]),
      LegalSection('Il prezzo che hai accettato è il prezzo che si rinnova', [
        LegalBlock.para(
            'Niente in Alma può cambiare quanto costa un piano esistente. Un nuovo prezzo a listino vale per i nuovi acquisti; il tuo piano continua a essere addebitato al prezzo a cui è stato aperto. Apple inoltre ti chiede di confermare qualsiasi aumento di prezzo prima che entri in vigore, e se non lo confermi annulla l\'abbonamento invece di addebitarti il nuovo prezzo.'),
      ]),
      LegalSection('Annullare', [
        LegalBlock.para(
            'Un abbonamento comprato in questa app si annulla nella schermata abbonamenti di Apple: Impostazioni → Piano → Gestisci questo abbonamento nell\'App Store, che la apre direttamente. Oppure, fuori da Alma: l\'app Impostazioni → il tuo nome → Abbonamenti.'),
        LegalBlock.para(
            'Non possiamo annullarlo per te, e non faremo finta di poterlo fare. Apple detiene il metodo di pagamento; una spunta dalla nostra parte che dice «annullato» non impedisce a una carta di essere addebitata, e chi ci avesse creduto lo scoprirebbe sull\'estratto conto. Se ci chiedi di annullare, l\'app dice esattamente questo e ti manda alla schermata giusta invece di scrivere alcunché.'),
        LegalBlock.para(
            'Un piano comprato sul nostro sito con una carta è diverso, e lì i due tocchi sono reali: Impostazioni → Piano → Annulla abbonamento → Conferma. Nessuna email da scrivere, nessuna ragione da dare, nessuna telefonata, e nessuna offerta in mezzo tra te e il secondo tocco.'),
        LegalBlock.para(
            'Annullare non è un rimborso del periodo in corso, e niente ti viene tolto nel momento in cui annulli. Che cosa è rimborsabile e che cosa no — compresi i quattordici giorni in cui puoi recedere del tutto da un piano — è nella pagina dei rimborsi.'),
      ]),
      LegalSection('Che cosa ti resta dopo', [
        LegalBlock.para(
            'Tutto ciò che hai comprato una tantum. Un sistema, o l\'archivio intero, comprato come acquisto una tantum è permanente e non è toccato dalla fine di un abbonamento.'),
        LegalBlock.para(
            'Il tuo account, il tuo tema e le tue conversazioni restano come sono. Terminare un abbonamento non è eliminare un account — quella è un\'azione separata e deliberata nelle Impostazioni.'),
      ]),
      LegalSection('Prima una lettura, il resto dopo', [
        LegalBlock.para(
            'Se compri un singolo sistema e poi, entro trenta giorni, decidi che vuoi il resto, il resto dell\'archivio ti è offerto al suo prezzo meno quanto hai già pagato per quella lettura. Niente da reclamare, niente da farsi rimborsare prima — il prezzo ridotto è semplicemente quello che ti viene addebitato.'),
        LegalBlock.para(
            'È offerto finché possiedi un solo sistema e niente di più ampio. Dopo trenta giorni l\'offerta sparisce e la lettura che hai comprato resta tua. La riduzione vale per l\'archivio; un piano ha un prezzo a sé.'),
      ]),
      LegalSection('Se un pagamento fallisce', [
        LegalBlock.para(
            'Niente ti viene tolto. Una carta rifiutata di solito è una carta che funziona al tentativo successivo, e Apple riprova per un po\' — la persona il cui pagamento è fallito è l\'ultima che dovrebbe restare chiusa fuori mentre la cosa si sistema.'),
        LegalBlock.para(
            'Se i tentativi non riescono mai, il piano semplicemente non viene prolungato: il tuo accesso arriva alla fine del periodo che hai già pagato e si ferma lì. Tutto ciò che hai comprato una tantum non è toccato da niente di tutto questo. Riabbonarsi fa partire un nuovo periodo dal giorno in cui viene pagato.'),
      ]),
      LegalSection('Fatture e imposte', [
        LegalBlock.para(
            'Apple è il venditore ufficiale per qualsiasi acquisto in questa app. Emette la ricevuta, gestisce IVA, GST e imposte sulle vendite dove si applicano, e la sua ricevuta è il documento che vuole il tuo commercialista. La trovi su reportaproblem.apple.com e nell\'email che Apple ti ha inviato.'),
      ]),
    ],
  );

  static const imprint = LegalDoc(
    lead:
        'Chi c\'è dietro Alma, nella forma richiesta dal §5 del Telemediengesetz tedesco e dagli equivalenti italiani e francesi. Tutto ciò che non è ancora stato fornito è segnato come mancante invece di essere riempito con qualcosa di plausibile.',
    sections: [
      LegalSection('Gestore', [
        LegalBlock.fact('Società', 'Pazl LLC'),
        LegalBlock.fact('Forma', 'Limited liability company'),
        LegalBlock.fact('Giurisdizione', 'Wyoming, United States'),
        LegalBlock.fact('Sede legale', '30 N Gould St Ste R, Sheridan, Wyoming 82801'),
        LegalBlock.fact('Numero di registrazione', '2026-002034771'),
        LegalBlock.fact('Rappresentata da', 'Anatolii Mikhailov'),
      ]),
      LegalSection('Contatti', [
        LegalBlock.fact('Email', 'hello@pazl.ai'),
        LegalBlock.para(
            'Lo legge una persona. Non c\'è un numero di telefono, e invece di stamparne uno che raggiunge una segreteria telefonica, qui lo diciamo.'),
      ]),
      LegalSection('Chi vende in questa app', [
        LegalBlock.fact('Venditore ufficiale', 'Apple'),
        LegalBlock.para(
            'Tutto ciò che si compra dentro questa app è venduto da Apple, che prende il pagamento, emette la ricevuta e versa le imposte. L\'entità sul tuo estratto conto dipende dal tuo storefront — Apple Inc., Apple Distribution International Ltd. o iTunes K.K. — e la ricevuta che Apple ti invia nomina quella che ti ha addebitato.'),
      ]),
      LegalSection('Imposta sul valore aggiunto', [
        LegalBlock.factBlank('Partita IVA', 'VAT ID'),
        LegalBlock.para(
            'Alma è venduta tramite Apple, che rende conto di IVA e GST dove si applicano. Una nostra partita IVA è in corso di registrazione.'),
      ]),
      LegalSection('Risoluzione delle controversie online', [
        LegalBlock.para(
            'La piattaforma ODR della Commissione europea ha chiuso a luglio 2025 e non è collegata qui, perché un link a una piattaforma che non esiste più è peggio di nessun link. Non siamo obbligati a ricorrere, e non ci impegniamo a ricorrere, a un organismo alternativo di risoluzione delle controversie. Scrivi a hello@pazl.ai e risponderà una persona.'),
      ]),
      LegalSection('Responsabile dei contenuti', [
        LegalBlock.fact('Ai sensi del §18 (2) MStV', 'Anatolii Mikhailov · 30 N Gould St Ste R, Sheridan, Wyoming 82801'),
      ]),
    ],
  );
}
