/// Немецкий перевод пяти юридических документов. Целиком на «du», как весь
/// продукт; структура повторяет `legal_text.dart` раздел в раздел и блок в
/// блок — 37 разделов, те же списки с теми же пунктами, — чтобы сверка
/// структуры ловила расхождение переводов так же, как ловит расхождение
/// с нативом. GDPR по-немецки называется DSGVO; имена собственные
/// (Pazl LLC, Apple, Anthropic, Wyoming) не переводятся. В фактах переведён
/// ярлык, значение оставлено как есть; в незаполненных фактах slug остаётся
/// английским — его заполняет владелец.
library;

import 'legal_text.dart';

class LegalTextDe {
  const LegalTextDe._();

  /// Дата в шапке каждого документа — та же, что у английского оригинала:
  /// переводили и проверяли вместе.
  static const updated = '7. August 2026';

  static const operatorName = 'Pazl LLC';

  static const merchant = 'Apple';

  static const contact = 'hello@pazl.ai';

  static const preamble = 'Das hier ist eine Beschreibung in klarer Sprache, wie Alma tatsächlich funktioniert. Sie ist zum Lesen geschrieben, nicht zum Überfliegen, und nichts darin widerspricht dem, was die App tut. Sie ist keine Rechtsberatung.';

  static const footer = 'Wenn ein Satz auf dieser Seite unklar ist, ist das unsere Schuld, nicht deine. Schreib an hello@pazl.ai, und wir korrigieren den Satz.';

  static LegalDoc of(LegalDocument which) => switch (which) {
        LegalDocument.terms => terms,
        LegalDocument.privacy => privacy,
        LegalDocument.refunds => refunds,
        LegalDocument.subscriptionTerms => subscriptionTerms,
        LegalDocument.imprint => imprint,
      };

  static const terms = LegalDoc(
    lead: 'Was du bekommst, was Alma nicht tun wird, und das Wenige, das wir von dir erbitten. Nichts hier ist ein Trick, und weiter unten steht keine Klausel, die einem Satz weiter oben widerspricht.',
    sections: [
      LegalSection('Was Alma ist', [
        LegalBlock.para('Alma berechnet aus deinem Geburtsdatum, deiner Geburtszeit und deinem Geburtsort ein Horoskop und schreibt daraus Deutungen. Die Berechnung ist Arithmetik und für alle gleich. Die Deutungen schreibt ein Sprachmodell, das dein Horoskop erhält und nur zitieren darf, was darin steht.'),
        LegalBlock.para('Pazl LLC betreibt Alma. In dieser App verkauft Apple sie — siehe die Abo-Bedingungen.'),
      ]),
      LegalSection('Was Alma nicht ist', [
        LegalBlock.para('Alma ist keine medizinische, rechtliche oder finanzielle Beratung, und sie sagt keine Ereignisse voraus. Sie wird dir nicht sagen, ob du den Job annehmen, den Menschen verlassen oder dich operieren lassen sollst.'),
        LegalBlock.para('Das ist kein Haftungsausschluss, der ans Ende einer Seite geschraubt wurde. Es ist eine Regel, die dort durchgesetzt wird, wo die Deutungen entstehen: Alma ist angewiesen, niemals zu diagnostizieren, niemals zu Geld oder Recht zu raten und niemals zu behaupten, dass etwas eintreten wird. Eine Deutung, die eines davon tut, ist ein Fehler in unserem System — kein Kleingedrucktes, das du übersehen hast. Sag uns unter hello@pazl.ai Bescheid, und wir beheben ihn.'),
        LegalBlock.para('Wenn es dir nicht gut geht, du in Gefahr bist oder eine Entscheidung ansteht, in der Geld oder Recht steckt, sprich mit jemandem, der dafür qualifiziert ist. Alma ist für Selbsterkenntnis da, und Selbsterkenntnis ist keine zweite fachliche Meinung.'),
      ]),
      LegalSection('Wer sie nutzen darf', [
        LegalBlock.para('Alle ab 16 Jahren. Du kannst dein Horoskop lesen und sogar kaufen, ohne uns eine Adresse zu geben: Auch ohne Anmeldung bist du bereits ein Konto mit einer ID, und was die Anmeldung hinzufügt, ist Beständigkeit, nicht Erlaubnis.'),
        LegalBlock.para('Aber ein Konto ohne Identität ist ein Konto, in das niemand zurückkommt. Auf diesem Telefon lebt dein Konto im Schlüsselbund und überlebt so das Schließen der App — nicht aber das Löschen der App oder den Wechsel des Telefons. Melde dich mit Apple an oder mit einem Link an ein Postfach, und das Konto folgt dir.'),
        LegalBlock.para('Am wichtigsten ist das für etwas, das du bezahlt hast. Ein Kauf gehört dem Alma-Konto, das ihn zuerst beansprucht hat — erst wenn du dich vor einer Neuinstallation anmeldest, kann „Käufe wiederherstellen“ ihn also finden.'),
      ]),
      LegalSection('Was wir von dir erbitten', [
        LegalBlock.points([
          'Gib deine eigenen Geburtsdaten ehrlich ein. Eine geratene Geburtszeit erzeugt ein Horoskop, das völlig plausibel und völlig falsch ist, und Alma kann den Unterschied nicht erkennen.',
          'Wenn du für eine Partnerschaftsdeutung die Geburtsdaten eines anderen Menschen eingibst, frag ihn vorher. Es sind seine Geburtsdaten, nicht deine.',
          'Lies Alma nicht automatisiert aus, verkaufe ihre Deutungen nicht weiter und gib sie nicht als dein eigenes Produkt aus. Was Alma für dich schreibt, darfst du behalten, drucken, zitieren und teilen.',
          'Greife den Dienst nicht an und versuche nicht, an die Horoskope anderer Leute zu gelangen.',
        ]),
      ]),
      LegalSection('Was wir dir schulden', [
        LegalBlock.para('Die Deutungen, die du fest gekauft hast, bleiben verfügbar, solange dein Konto existiert. Einmalkäufe sind dauerhaft; sie laufen nicht ab, wenn ein Abo es tut.'),
        LegalBlock.para('Ein Abo ist der andere Fall, und hier lohnt sich Genauigkeit: Deutungen, die für dich geschrieben wurden, während ein Abo lief, bleiben nach dessen Ende in deinem Konto, aber sie öffnen sich nicht mehr — denn was ein Abo verkauft, ist der Zeitraum, nicht der Text. Genau deshalb wird das Archiv überhaupt separat verkauft.'),
        LegalBlock.para('Alma wird nicht jede Sekunde jedes Jahres erreichbar sein. Kein Dienst ist das. Ist sie gerade nicht da, wenn du sie willst, kommt sie zurück — und wenn ein Ausfall von uns dich einen bezahlten Monat gekostet hat, unterstützen wir deinen Erstattungsantrag bei Apple, denn dort liegt das Geld.'),
        LegalBlock.para('Wenn wir diese Bedingungen ändern, bekommst du eine E-Mail, bevor die Änderung wirksam wird — kein stillschweigend aktualisiertes Datum oben auf einer Seite. Dieser Brief wird von Hand geschrieben und an die Adresse deines Kontos geschickt, denn Alma hat keinen Verteiler und nichts Automatisches, das ihn verschicken könnte.'),
        LegalBlock.para('Das heißt aber auch: Hast du uns nie eine Adresse gegeben, gibt es keinen Kanal, der dich erreicht, und das Datum oben auf dieser Seite ist die einzige Mitteilung, die es gibt. Das ist ein Grund, sich anzumelden — kein Schlupfloch, auf das wir stolz wären.'),
      ]),
      LegalSection('Wenn etwas schiefgeht', [
        LegalBlock.para('Verursachen wir dir einen Schaden, ist unsere Verantwortung auf das begrenzt, was du für die Sache bezahlt hast, die schiefging. Alma ist eine Deutung, keine professionelle Dienstleistung, und sollte auch nicht als solche verstanden werden — das ist derselbe Satz wie im Abschnitt oben, nur in der Sprache der Haftung.'),
        LegalBlock.para('Nichts hier nimmt dir ein Recht, das dir dein eigenes Land gibt. Wo beides sich widerspricht, gewinnt dein Land.'),
      ]),
      LegalSection('Wie es endet', [
        LegalBlock.para('Wenn du angemeldet bist, kannst du dein Konto in den Einstellungen löschen — jederzeit, ohne uns zu fragen und ohne Begründung. Es wirkt sofort und nimmt deine Daten mit — siehe die Datenschutzseite.'),
        LegalBlock.para('Wenn nicht — Lesen ohne Konto ist erlaubt, Kaufen auch —, hat der Knopf in den Einstellungen kein Konto, an das er die Anfrage hängen könnte, und bittet dich deshalb, dich zuerst anzumelden. Melde dich mit der Identität an, mit der du bezahlt hast, und es funktioniert. Wenn du das nicht kannst, schreib an hello@pazl.ai, und wir erledigen es von Hand. Das ist ein Mensch und ein Arbeitstag statt eines Knopfes — und das offen zu sagen ist besser als ein Satz, der auf einem Bildschirm mit ausgegrautem Knopf etwas anderes verspricht.'),
        LegalBlock.para('Das Löschen deines Alma-Kontos kündigt kein über den App Store gekauftes Abo. Das hält Apple, und gekündigt wird es auf Apples eigener Abo-Seite — in den Einstellungen gibt es einen Knopf, der sie öffnet.'),
        LegalBlock.para('Wir können ein Konto schließen, das den Dienst angreift oder ihn gegen andere Menschen einsetzt. Tun wir das, bekommst du die E-Mail und den Grund — oder, wenn am Konto keine Adresse hängt, den Grund auf Anfrage unter hello@pazl.ai.'),
      ]),
      LegalSection('Anwendbares Recht', [
        LegalBlock.para('Diese Bedingungen unterliegen dem Recht von Wyoming, United States — dem Bundesstaat, in dem Pazl LLC organisiert ist —, und Streitigkeiten werden vor den Gerichten von Wyoming verhandelt.'),
        LegalBlock.para('Nichts an diesem Satz nimmt dir ein Recht, das dir dein eigenes Land gibt: Wo ein Verbraucherrecht deines Landes und diese Klausel sich widersprechen, gewinnt dein Land — wie der Abschnitt oben schon sagt.'),
      ]),
    ],
  );

  static const privacy = LegalDoc(
    lead: 'Was Alma über dich hält, warum jedes Einzelne davon gehalten wird, und was nötig wäre, um alles davon loszuwerden. Jeder Punkt unten ist eine Spalte, die in einer echten Tabelle existiert — keine Kategorie, die uns beruhigend klang.',
    sections: [
      LegalSection('Was erhoben wird', [
        LegalBlock.points([
          'Dein Geburtsdatum, deine Geburtszeit, dein Geburtsort und der Name, den du angegeben hast. Das ist das Horoskop. Ohne sie gibt es kein Produkt; mit ihnen ist alles Weitere, was Alma tut, Arithmetik über diesen fünf Zahlen.',
          'Deine E-Mail-Adresse, falls du dich angemeldet hast. Ohne Passwort — das Postfach ist das Konto. „Mit Apple anmelden“ gibt uns unter Umständen stattdessen eine Relay-Adresse, und das ist in Ordnung: Deine echte müssen wir nie kennen.',
          'Die für dich geschriebenen Deutungen, damit ein Kapitel, das du bezahlt hast, morgen dasselbe sagt — und damit es nicht auf unsere Kosten zweimal geschrieben wird.',
          'Deine Fragen an Alma und ihre Antworten, damit ein Gespräch ein Gedächtnis hat.',
          'Was du gekauft hast, als Liste von Freischaltungen — welches System, wann, für wie lange. Keine Kartennummer: Wir hatten nie eine und könnten keine speichern, selbst wenn wir wollten.',
          'Eine Handvoll Funnel-Ereignisse — dass ein Quiz gestartet, dass ein Porträt gesehen wurde — ohne jeden Inhalt. Sie werden gezählt, nie gelesen.',
        ]),
      ]),
      LegalSection('Was nicht erhoben wird', [
        LegalBlock.para('Keine Zahlungsdaten. Apple nimmt in dieser App die Zahlung entgegen und hält die Karte; das Einzige, was uns erreicht, ist eine signierte Bestätigung, dass ein Kauf stattgefunden hat — und die prüfen wir gegen Apples eigenes Zertifikat, bevor wir danach handeln.'),
        LegalBlock.para('Keine Werbe-IDs, keine Analytik von Drittanbietern, kein Tracking über andere Apps oder Websites, kein Standort außer dem Geburtsort, den du eingetippt hast. Es gibt nichts, dem du widersprechen müsstest, weil nichts läuft.'),
        LegalBlock.para('Wir verkaufen und teilen keine personenbezogenen Daten — in keiner der Bedeutungen, die diese Wörter unter dem California Consumer Privacy Act oder irgendeinem anderen Gesetz haben. Es gibt mit niemandem eine Vereinbarung, die uns das erlauben würde.'),
      ]),
      LegalSection('Wer es sonst noch sieht', [
        LegalBlock.points([
          'Anthropic, die das Modell betreiben, das die Deutungen schreibt. Dein Geburtsdatum, deine Geburtszeit, der Name deines Geburtsorts und dein Name, falls du einen angegeben hast, werden gesendet, so wie sie gespeichert sind — aus ihnen wird die Deutung geschrieben. Ebenso das berechnete Horoskop, die Frage, die du gestellt hast, und die kurzen Fakten, die Alma sich merkt. Eine Frage von dir trägt die letzten zwölf Nachrichten des jeweiligen Gesprächs mit, damit sie im Zusammenhang Sinn ergibt. Deine E-Mail-Adresse wird nicht gesendet und wird nicht gebraucht. Die Koordinaten deines Geburtsorts auch nicht: Das Horoskop wird hier berechnet, und nur das Ergebnis reist.',
          'Apple oder Google — je nachdem, aus welchem Store du Alma hast — für alles, was in dieser App gekauft wird. Sie sehen den Kauf, nicht das Horoskop.',
          'Unser Mail-Anbieter, für die zwei Briefe, die Alma verschickt: einen Anmeldelink und — bei einem außerhalb der App-Stores gekauften Abo — eine Mitteilung vor einer Verlängerung.',
          'Unser Hosting-Anbieter, der die Maschine betreibt, auf der die Datenbank liegt.',
        ]),
        LegalBlock.para('Das ist die ganze Liste. Sollte sie je länger werden, ändert sich diese Seite, bevor die Vereinbarung beginnt — nicht danach.'),
      ]),
      LegalSection('Wo es liegt und wie lange', [
        LegalBlock.para('Auf Servern in der Europäischen Union. Deutungen und Horoskope werden aufbewahrt, solange dein Konto existiert, denn genau dafür sind sie da. Funnel-Ereignisse werden als Zählwerte aufbewahrt.'),
        LegalBlock.para('Auf diesem Telefon liegt dein Konto-Token im Schlüsselbund — vom System verschlüsselt, von Backups ausgenommen und nie irgendwohin geschrieben, wo ein Backup oder eine andere App es lesen könnte.'),
      ]),
      LegalSection('Was du tun kannst', [
        LegalBlock.points([
          'Alles exportieren, als eine Datei, aus den Einstellungen. Es sind die tatsächlichen Datenbankzeilen, keine Zusammenfassung.',
          'Alles löschen, aus den Einstellungen. Es geschieht sofort und es ist echt: Die Zeilen werden gelöscht, nicht bloß markiert. Deutungen, die du bezahlt hast, lassen sich nicht Wort für Wort noch einmal schreiben — deshalb bittet dich der Knopf, zuerst deine Adresse einzutippen.',
          'Uns alles fragen, unter hello@pazl.ai. Ein Mensch antwortet.',
        ]),
        LegalBlock.para('Nach der DSGVO hast du außerdem das Recht, das, was wir halten, berichtigen zu lassen, der Verarbeitung zu widersprechen und dich bei deiner nationalen Aufsichtsbehörde zu beschweren. Die ersten beiden sind die zwei Knöpfe oben; das Dritte braucht nichts von uns.'),
      ]),
      LegalSection('Kinder', [
        LegalBlock.para('Alma ist für Menschen ab 16 Jahren und im App Store entsprechend eingestuft. Wissentlich halten wir keine Daten über jemanden, der jünger ist. Wenn du glaubst, dass doch, schreib an hello@pazl.ai, und sie werden an dem Tag gelöscht, an dem wir es lesen.'),
      ]),
      LegalSection('An wen du schreibst', [
        LegalBlock.para('Pazl LLC ist der Verantwortliche. hello@pazl.ai erreicht einen Menschen, keine Ticket-Warteschlange.'),
        LegalBlock.para('Pazl LLC hat keine Niederlassung in der EU und hat noch keinen Vertreter nach Art. 27 DSGVO benannt. Bis auf dieser Seite einer genannt ist, übst du jedes Recht, das diese Seite aufzählt, auf demselben Weg aus: mit einer Mail an hello@pazl.ai, wo ein Mensch antwortet.'),
      ]),
    ],
  );

  static const refunds = LegalDoc(
    lead: 'Alma ist nicht der Verkäufer von irgendetwas, das in dieser App gekauft wird. Apple ist es. Diese eine Tatsache entscheidet das meiste von dem, was folgt — deshalb steht sie zuerst und nicht in einer Fußnote.',
    sections: [
      LegalSection('Apple ist der Händler (Merchant of Record)', [
        LegalBlock.para('Wenn du in dieser App etwas kaufst, schließt du den Kaufvertrag mit Apple. Apple nimmt die Zahlung, stellt den Beleg aus, berechnet die Steuer und führt sie ab und hält das Geld. Deine Kartendaten erreichen uns nie.'),
        LegalBlock.para('Eine Erstattung ist deshalb kein Knopf, den wir drücken können. Das Geld verlässt Apples Konto, nicht unseres — darum gehen Erstattungsanträge an Apple. Wir können deinen Antrag unterstützen, und das tun wir, aber die Entscheidung und die Überweisung liegen bei Apple.'),
      ]),
      LegalSection('Wie du den Antrag stellst', [
        LegalBlock.points([
          'reportaproblem.apple.com, angemeldet mit dem Apple Account, mit dem du gekauft hast. Das ist der schnellste Weg und führt direkt zu denen, die das Geld halten. Dasselbe Formular ist auch aus dem Beleg erreichbar, den Apple dir gemailt hat.',
          'Oder schreib an hello@pazl.ai mit dem Apple Account, mit dem du gekauft hast. Erstatten können wir nicht, aber wir können Apple bestätigen, was auf unserer Seite passiert ist — und wir sagen dir, was Apple geantwortet hat, auch wenn die Antwort Nein ist.',
        ]),
      ]),
      LegalSection('Wo wir den Antrag ohne Diskussion unterstützen', [
        LegalBlock.para('Das sind unsere Fehler, oder dein Recht, und beides ist keine Ermessensfrage:'),
        LegalBlock.points([
          'Die Deutung wurde nie generiert, oder sie wurde generiert und ließ sich nicht öffnen.',
          'Das Horoskop war falsch wegen eines Fehlers auf unserer Seite — nicht wegen einer Geburtszeit, bei der du dir unsicher warst.',
          'Dir wurde dieselbe Sache zweimal berechnet.',
          'Dir wurde nach der Kündigung noch etwas berechnet.',
          'Ein Ausfall von uns hat dich einen bezahlten Abo-Monat gekostet.',
          'Du hast es dir innerhalb von vierzehn Tagen anders überlegt — siehe das Widerrufsrecht unten, das wir nicht als verwirkt behandeln.',
        ]),
        LegalBlock.para('Nichts davon musst du uns beweisen. Wenn die Aufzeichnungen es zeigen, sagen wir das Apple — und dir sagen wir, dass wir es getan haben.'),
      ]),
      LegalSection('Nichts wird geschrieben, bevor du es öffnest', [
        LegalBlock.para('Ein Kapitel wird generiert, wenn du es zum ersten Mal öffnest — nicht im Moment der Zahlung. Das Archiv sind einundvierzig Kapitel über acht Systeme, acht davon die freien Proben, die alle lesen können; der Kauf öffnet die übrigen dreiunddreißig, und sie zu öffnen ist nicht dasselbe, wie sie zu schreiben. Jedes wird geschrieben, wenn du zu ihm gehst — aus deinem Horoskop, wie es dann steht — und gespeichert, damit es danach jedes Mal dasselbe sagt.'),
        LegalBlock.para('Das ist der Grund, warum diese Seite sagen kann, was als Nächstes kommt. In der Sekunde, in der deine Karte belastet wird, ist noch nichts geliefert — und ein Versprechen, du hättest ein Recht über Text aufgegeben, den noch niemand geschrieben hat, ist kein Versprechen, das man von jemandem verlangen sollte.'),
      ]),
      LegalSection('Das 14-tägige Widerrufsrecht, das wir nicht als verwirkt behandeln', [
        LegalBlock.para('In der EU und im Vereinigten Königreich hast du vierzehn Tage, um es dir bei etwas online Gekauftem anders zu überlegen. Digitale Inhalte können davon eine Ausnahme sein — aber nur, wenn drei Dinge passiert sind: Du hast ausdrücklich zugestimmt, dass wir sofort beginnen; du hast zur Kenntnis genommen, dass der sofortige Beginn dich das Recht kostet; und dir wurde eine Bestätigung von beidem auf einem dauerhaften Datenträger geschickt.'),
        LegalBlock.para('Im App Store führt Apple den Kaufdialog, und Apple verschickt den Beleg — keines der drei liegt in unserer Hand, und wir werden uns nicht auf einen Verzicht berufen, den wir nicht eingeholt haben. Wenn du uns innerhalb von vierzehn Tagen nach dem Kauf sagst, dass du es dir anders überlegt hast, unterstützen wir eine volle Erstattung bei Apple und fragen dich nicht nach dem Warum.'),
        LegalBlock.para('Kommt der ganze Preis zurück, schließt sich, was er gekauft hat: Das Archiv öffnet sich nicht mehr, oder das gekaufte System öffnet sich nicht mehr. Geld zurück und die Deutung behalten ist keine Erstattung, sondern ein Rabatt von hundert Prozent — und wir verweigern lieber das Zweite, als das Erste vorzutäuschen.'),
        LegalBlock.para('Wir ziehen nichts für die Kapitel ab, die schon für dich geschrieben wurden, und wir teilen den Kauf nicht in den erbrachten und den nicht erbrachten Teil. Wir könnten es — wir wissen genau, welche Kapitel existieren —, aber jede Zahl, die wir dafür ansetzen würden, wie viel eines Buches du gelesen hast, wäre eine von uns erfundene Zahl, und eine erfundene Zahl ist für dieses Dokument schlimmer als eine Regel, die uns gelegentlich einen Verkauf kostet.'),
        LegalBlock.para('Nach den vierzehn Tagen ist die Liste oben die Regel: unsere Fehler, ohne Diskussion — und ansonsten ein Antrag, über den Apple entscheidet.'),
      ]),
      LegalSection('Ein Jahr ist am ersten Tag nicht geliefert', [
        LegalBlock.para('Das Jahresabo ist rechtlich und tatsächlich ein anderer Fall. Es ist nichts, was auf einmal übergeben wird — es sind zwölf Monate Zugang zu allem, einschließlich der Systeme, die neu geschrieben werden, während der Himmel sich bewegt, und an Tag zehn ist bei Weitem nicht das Ganze erbracht. Keine Zustimmung an einer Kasse beendet dein Recht, von einer Dienstleistung zurückzutreten, die kaum begonnen hat.'),
        LegalBlock.para('Also: Widerrufst du ein Abo innerhalb von vierzehn Tagen, soll der Teil des Zeitraums zurückkommen, den du nicht genutzt hast, berechnet nach den vergangenen Tagen — und das Abo endet dort, statt weiterzulaufen. Genau das beantragen wir bei Apple, und den Zugang schließen wir auf unserer Seite, ob Apple zustimmt oder nicht, denn die zweite Hälfte liegt bei uns.'),
      ]),
      LegalSection('Das Muster-Widerrufsformular', [
        LegalBlock.para('Du musst kein Formular verwenden — eine E-Mail, dass du es dir anders überlegt hast, genügt —, aber das Gesetz verlangt, dass eines angeboten wird. Hier ist es:'),
        LegalBlock.para('An Pazl LLC, hello@pazl.ai — Hiermit widerrufe ich den von mir geschlossenen Vertrag über die Bereitstellung der folgenden digitalen Inhalte: [was du gekauft hast]. Bestellt am [Datum]. Name des Verbrauchers: [dein Name]. Verwendete E-Mail-Adresse: [deine Adresse]. Datum: [heute].'),
        LegalBlock.para('Absichtlich an uns adressiert und nicht an Apple: Der Vertrag über die Inhalte besteht mit uns, das Geld hält Apple, und du sollst nicht herausfinden müssen, wem von beiden du schreibst. Wir leiten es weiter.'),
      ]),
    ],
  );

  static const subscriptionTerms = LegalDoc(
    lead: 'Was sich verlängert, was es kostet und wie du es stoppst — was bei einem in dieser App gekauften Abo auf Apples eigener Abo-Seite geschieht, nicht auf unserer. Wo etwas weniger aufgeräumt ist als das, steht es hier, statt wegzubleiben.',
    sections: [
      LegalSection('Was sich verlängert', [
        LegalBlock.para('Die Preisliste führt zwei laufende Abos. Das Jahresabo öffnet alles, was Alma für dich geschrieben hat — jedes System, jedes Kapitel — für ein Jahr. Das Monatsabo öffnet nur die drei Systeme, die sich mit dem Datum bewegen: die Transite, das Solarhoroskop und die Partnerschaft. Ein Geburtshoroskop zu vermieten wäre Miete auf Zahlen, die sich seit deiner Geburt nicht geändert haben — deshalb gehört das Archiv nicht dazu.'),
        LegalBlock.para('Jedes der beiden Abos verlängert sich automatisch in seinem eigenen Zyklus, bis du es stoppst. Die Zahlung wird deinem Apple Account bei Bestätigung des Kaufs belastet. Das Abo verlängert sich, sofern die automatische Verlängerung nicht mindestens 24 Stunden vor Ende des laufenden Zeitraums abgeschaltet wird, und dein Account wird innerhalb von 24 Stunden vor Ende dieses Zeitraums für die Verlängerung belastet.'),
        LegalBlock.para('Eine Zahlung öffnet etwas mehr als den Zeitraum, für den sie ist — einunddreißig Tage für einen Monat, dreihundertfünfundsechzig für ein Jahr, gezählt ab dem späteren von beiden: dem Tag, an dem du zahlst, oder dem Tag, an dem dein laufender Zugang endet. Die Extratage stapeln sich nicht; es gibt sie, damit eine ein paar Stunden zu spät belastete Verlängerung dich nie aus einem Zeitraum aussperren kann, den du schon bezahlt hast.'),
        LegalBlock.para('Der Preis ist der, der auf dem Kaufdialog steht. Er ist absichtlich nicht auf diese Seite gedruckt: Apple setzt und berechnet den Preis für deinen Storefront, in deiner Währung, mit deiner Steuer — und Apples Zahl ist die, die stimmt.'),
      ]),
      LegalSection('Ein Abo ist gemietet, nicht gekauft', [
        LegalBlock.para('Das Jahresabo öffnet alles für ein Jahr. Es ist kein Kauf des Archivs. Wenn das Jahr endet und du nicht verlängert hast, bleiben die Deutungen, die währenddessen für dich geschrieben wurden, in deinem Konto — nichts wird gelöscht —, aber sie öffnen sich nicht mehr, wie jedes Kapitel, das du nicht bezahlt hast.'),
        LegalBlock.para('Wenn du Text willst, der deiner bleibt, egal was als Nächstes passiert, dann ist das das Archiv, einmal gekauft. Alles fest Gekaufte ist dauerhaft und bleibt unberührt davon, dass ein Abo beginnt, endet oder gekündigt wird.'),
      ]),
      LegalSection('Wer dich vor der Abbuchung informiert', [
        LegalBlock.para('Bei einem in dieser App gekauften Abo: Apple. Apple schickt den Beleg und Apple schickt die Verlängerungsmitteilung, denn Apple ist der Verkäufer und hält das Zahlungsmittel. Wir schicken keines von beidem, und eine Seite von uns, die etwas anderes verspräche, wäre ein Versprechen, das wir nicht halten können.'),
        LegalBlock.para('Bei einem auf unserer Website mit Karte gekauften Abo: wir. Drei Tage vor einer Verlängerung geht eine E-Mail hinaus, die sagt, was gleich abgebucht wird, in welcher Währung und an welchem Datum. Sie ist keine Marketing-Mail und hat keinen Abmelden-Link, denn ein Abo, das du vergessen hast, ist der älteste Trick dieser Branche, und in dem Geschäft wollen wir nicht sein.'),
      ]),
      LegalSection('Der Preis, dem du zugestimmt hast, ist der Preis, der sich verlängert', [
        LegalBlock.para('Nichts in Alma kann ändern, was ein bestehendes Abo kostet. Ein neuer Preis auf der Preisliste gilt für neue Käufe; dein Abo rechnet weiter zu dem Preis ab, zu dem es eröffnet wurde. Apple bittet dich zusätzlich, jede Preiserhöhung zu bestätigen, bevor sie wirksam wird — und kündigt das Abo lieber, als dir den neuen Preis zu berechnen, wenn du das nicht tust.'),
      ]),
      LegalSection('Kündigen', [
        LegalBlock.para('Ein in dieser App gekauftes Abo wird auf Apples Abo-Seite gekündigt: Einstellungen → Abo → „Dieses Abo im App Store verwalten“ — das öffnet sie direkt. Oder außerhalb von Alma: die Einstellungen-App → dein Name → Abonnements.'),
        LegalBlock.para('Wir können es nicht für dich kündigen, und wir tun nicht so, als könnten wir. Apple hält das Zahlungsmittel; ein Vermerk „gekündigt“ auf unserer Seite hält keine Kartenabbuchung auf, und wer ihm geglaubt hätte, erführe es auf dem Kontoauszug. Bittest du uns zu kündigen, sagt die App genau das und schickt dich auf die richtige Seite, statt irgendetwas zu schreiben.'),
        LegalBlock.para('Ein auf unserer Website mit Karte gekauftes Abo ist anders — dort sind die zwei Fingertipps echt: Einstellungen → Abo → Abo kündigen → Bestätigen. Keine E-Mail zu schreiben, kein Grund zu nennen, kein Anruf, und kein Angebot, das zwischen dir und dem zweiten Fingertipp steht.'),
        LegalBlock.para('Kündigen ist keine Erstattung des Zeitraums, in dem du bist, und im Moment der Kündigung wird dir nichts weggenommen. Was erstattet wird und was nicht — einschließlich der vierzehn Tage, in denen du ein Abo ganz widerrufen kannst — steht auf der Erstattungsseite.'),
      ]),
      LegalSection('Was dir danach bleibt', [
        LegalBlock.para('Alles, was du fest gekauft hast. Ein System oder das ganze Archiv als Einmalkauf ist dauerhaft und bleibt vom Ende eines Abos unberührt.'),
        LegalBlock.para('Dein Konto, dein Horoskop und deine Gespräche bleiben, wie sie sind. Ein Abo zu beenden ist nicht dasselbe wie ein Konto zu löschen — das ist ein eigener, bewusster Schritt in den Einstellungen.'),
      ]),
      LegalSection('Erst eine Deutung, der Rest später', [
        LegalBlock.para('Kaufst du ein einzelnes System und entscheidest dich innerhalb von dreißig Tagen für den Rest, wird dir das übrige Archiv zu seinem Preis abzüglich dessen angeboten, was du für diese Deutung schon bezahlt hast. Nichts zu beantragen, nichts vorher zu erstatten — der reduzierte Preis ist einfach das, was dir berechnet wird.'),
        LegalBlock.para('Das Angebot gilt, solange du genau ein System hältst und nichts Größeres. Nach dreißig Tagen ist es weg, und die gekaufte Deutung bleibt deine. Die Reduzierung gilt für das Archiv; ein Abo hat seinen eigenen Preis.'),
      ]),
      LegalSection('Wenn eine Zahlung fehlschlägt', [
        LegalBlock.para('Nichts wird weggenommen. Eine Karte, die abgelehnt wird, funktioniert meist beim nächsten Versuch, und Apple versucht es eine Weile weiter — wer gerade ein Zahlungsproblem hat, ist der Letzte, der ausgesperrt gehört, während es sich klärt.'),
        LegalBlock.para('Gelingen die Versuche nie, wird das Abo einfach nicht verlängert: Dein Zugang läuft bis zum Ende des bereits bezahlten Zeitraums und endet dort. Alles fest Gekaufte bleibt von alldem unberührt. Ein neues Abo beginnt einen neuen Zeitraum ab dem Tag, an dem es bezahlt wird.'),
      ]),
      LegalSection('Belege und Steuern', [
        LegalBlock.para('Apple ist der Verkäufer für alles, was in dieser App gekauft wird. Apple stellt den Beleg aus, kümmert sich um Mehrwertsteuer, GST und Sales Tax, wo sie anfallen, und Apples Beleg ist das Dokument, das deine Steuerberatung haben will. Er liegt unter reportaproblem.apple.com und in der E-Mail, die Apple dir geschickt hat.'),
      ]),
    ],
  );

  static const imprint = LegalDoc(
    lead: 'Wer hinter Alma steht — in der Form, die §5 des deutschen Telemediengesetzes und die Entsprechungen in Italien und Frankreich verlangen. Alles, was noch nicht vorliegt, ist als fehlend markiert statt mit etwas Plausiblem gefüllt.',
    sections: [
      LegalSection('Anbieter', [
        LegalBlock.fact('Unternehmen', 'Pazl LLC'),
        LegalBlock.fact('Rechtsform', 'Limited liability company'),
        LegalBlock.fact('Registerstaat', 'Wyoming, United States'),
        LegalBlock.fact('Sitzanschrift', '30 N Gould St Ste R, Sheridan, Wyoming 82801'),
        LegalBlock.fact('Registernummer', '2026-002034771'),
        LegalBlock.fact('Vertreten durch', 'Anatolii Mikhailov'),
      ]),
      LegalSection('Kontakt', [
        LegalBlock.fact('E-Mail', 'hello@pazl.ai'),
        LegalBlock.para('Ein Mensch liest sie. Eine Telefonnummer gibt es nicht, und statt eine zu drucken, die einen Anrufbeantworter erreicht, steht das hier.'),
      ]),
      LegalSection('Verkauf in dieser App', [
        LegalBlock.fact('Händler (Merchant of Record)', 'Apple'),
        LegalBlock.para('Alles, was in dieser App gekauft wird, verkauft Apple: Apple nimmt die Zahlung, stellt den Beleg aus und führt die Steuer ab. Welche Gesellschaft auf deinem Kontoauszug steht, hängt von deinem Storefront ab — Apple Inc., Apple Distribution International Ltd. oder iTunes K.K. —, und der Beleg, den Apple dir schickt, nennt die, die dich belastet hat.'),
      ]),
      LegalSection('Umsatzsteuer', [
        LegalBlock.factBlank('Umsatzsteuer-Identifikationsnummer', 'VAT ID'),
        LegalBlock.para('Alma wird über Apple verkauft; Apple führt Mehrwertsteuer und GST ab, wo sie anfallen. Eine eigene Umsatzsteuer-Identifikationsnummer wird gerade beantragt.'),
      ]),
      LegalSection('Online-Streitbeilegung', [
        LegalBlock.para('Die ODR-Plattform der Europäischen Kommission wurde im Juli 2025 geschlossen und ist hier nicht verlinkt, denn ein Link auf eine Plattform, die nicht mehr existiert, ist schlimmer als kein Link. Zur Teilnahme an einem Verfahren vor einer Verbraucherschlichtungsstelle sind wir nicht verpflichtet und verpflichten uns auch nicht. Schreib an hello@pazl.ai, und ein Mensch antwortet.'),
      ]),
      LegalSection('Verantwortlich für den Inhalt', [
        LegalBlock.fact('Nach §18 Abs. 2 MStV', 'Anatolii Mikhailov · 30 N Gould St Ste R, Sheridan, Wyoming 82801'),
      ]),
    ],
  );
}
