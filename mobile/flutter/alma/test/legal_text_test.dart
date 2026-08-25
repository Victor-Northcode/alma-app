import 'package:alma/screens/legal/legal_text.dart';
import 'package:flutter_test/flutter_test.dart';

/// Юридический текст не должен худеть молча.
///
/// Он уже похудел один раз: `legal_text.dart` обещал «слово в слово» с
/// `mobile/ios/Alma/Screens/Settings/LegalText.swift` и сверялся по числу
/// блоков — а список остаётся одним блоком, из скольких бы пунктов он ни
/// состоял. Так исчезли пункт про атаку на сервис, четыре случая безусловной
/// поддержки возврата и заголовок раздела о четырнадцати днях (его пять
/// абзацев осели в предыдущем разделе). Все числа при этом сходились.
///
/// Поэтому тест считает разделы и пункты, а не одни блоки, и проверяет
/// присутствие тех самых фраз: пропажа права на отказ или случая «списали
/// дважды» — это не косметика, а обещание, которого приложение больше не даёт.
void main() {
  /// Плоский список всех строк документа — то, что реально увидит читатель.
  List<String> textOf(LegalDoc doc) => [
        doc.lead,
        for (final s in doc.sections) ...[
          s.title,
          for (final b in s.blocks)
            ...switch (b) {
              LegalPara(:final text) => [text],
              LegalPoints(:final items) => items,
              LegalFact(:final label, :final value) => [label, value],
              LegalFactBlank(:final label, :final value) => [label, value],
              LegalBlank(:final what) => [what],
            },
        ],
      ];

  int countOf<T extends LegalBlock>(LegalDoc doc) => doc.sections
      .expand((s) => s.blocks)
      .whereType<T>()
      .length;

  final all = LegalDocument.values.map(LegalText.of).toList();

  group('структура — та же, что на iOS', () {
    test('разделов 37, по документам 8/7/7/9/6', () {
      // Раздел о четырнадцати днях в возвратах — седьмой; когда его заголовок
      // потеряли, здесь стояло 6, и порт всё равно «сходился».
      expect(all.map((d) => d.sections.length).toList(), [8, 7, 7, 9, 6]);
      expect(all.fold<int>(0, (n, d) => n + d.sections.length), 37);
    });

    test('абзацев 71, списков 6 на 25 пунктов', () {
      // 25.08.2026: право и суд заполнены Вайомингом, представитель по ст. 27
      // назван честным состоянием — три «пропуска» стали двумя абзацами
      // текста, и счёт абзацев сместился с 72 на 71.
      expect(all.fold<int>(0, (n, d) => n + countOf<LegalPara>(d)), 71);
      expect(all.fold<int>(0, (n, d) => n + countOf<LegalPoints>(d)), 6);
      // Пункты, а не списки: ровно тут и утекал текст.
      final points = all
          .expand((d) => d.sections)
          .expand((s) => s.blocks)
          .whereType<LegalPoints>()
          .fold<int>(0, (n, p) => n + p.items.length);
      expect(points, 25);
    });

    test('фактов 5, незаполненных фактов 5, пропусков 0', () {
      expect(all.fold<int>(0, (n, d) => n + countOf<LegalFact>(d)), 5);
      expect(all.fold<int>(0, (n, d) => n + countOf<LegalFactBlank>(d)), 5);
      expect(all.fold<int>(0, (n, d) => n + countOf<LegalBlank>(d)), 0);
    });

    test('ни одной пустой строки — блок без текста читается как пропажа', () {
      for (final doc in all) {
        for (final line in textOf(doc)) {
          expect(line.trim(), isNotEmpty);
        }
      }
    });
  });

  group('обещания, которые нельзя потерять', () {
    test('условия просят не атаковать сервис и не лезть в чужие карты', () {
      expect(textOf(LegalText.terms),
          contains("Do not attack the service or try to reach other people's charts."));
    });

    test('возвраты перечисляют все шесть случаев без спора', () {
      final refunds = textOf(LegalText.refunds);
      for (final promise in const [
        'The reading never generated, or generated and would not open.',
        'You were charged twice for the same thing.',
        'You were charged after cancelling.',
        'An outage of ours cost you a subscription month you had paid for.',
      ]) {
        expect(refunds, contains(promise), reason: 'пропал случай: $promise');
      }
      expect(
        refunds.where((s) => s.startsWith('The chart was wrong')).length,
        1,
      );
      expect(
        refunds.where((s) => s.startsWith('You changed your mind')).length,
        1,
      );
    });

    test('право на отказ за четырнадцать дней — отдельный раздел', () {
      final section = LegalText.refunds.sections.singleWhere((s) =>
          s.title == 'The 14-day withdrawal right, which we do not treat as waived');
      // Пять абзацев: они однажды уже слились с разделом выше, и заголовок,
      // на который ссылается список случаев («see the withdrawal right
      // below»), исчез вместе с ними.
      expect(section.blocks.whereType<LegalPara>().length, 5);
      expect(
        section.blocks.whereType<LegalPara>().first.text,
        startsWith('In the EU and the UK you have fourteen days'),
      );
      expect(
        LegalText.refunds.sections
            .singleWhere((s) => s.title == 'Nothing is written until you open it')
            .blocks
            .length,
        2,
      );
    });
  });

  group('пропуски остаются пропусками', () {
    test('юридические факты, которых у нас нет, не выдуманы', () {
      final blanks = all
          .expand((d) => d.sections)
          .expand((s) => s.blocks)
          .whereType<LegalBlank>()
          .map((b) => b.what)
          .toList();
      // Текстовых пропусков не осталось (25.08.2026) — но сама проверка
      // живёт: новый LegalBlank обязан быть замечен, а не просочиться.
      expect(blanks, isEmpty);

      final factBlanks = all
          .expand((d) => d.sections)
          .expand((s) => s.blocks)
          .whereType<LegalFactBlank>()
          .map((b) => b.label)
          .toList();
      expect(factBlanks, [
        'Registered address',
        'Registration number',
        'Represented by',
        'VAT identification',
        'Under §18 (2) MStV',
      ]);
    });
  });
}
