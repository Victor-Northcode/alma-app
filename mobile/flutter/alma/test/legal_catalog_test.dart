import 'package:flutter_test/flutter_test.dart';
import 'package:alma/screens/legal/legal_catalog.dart';
import 'package:alma/screens/legal/legal_text.dart';

/// Шесть переводов юридических документов зеркалят английский эталон.
///
/// Владелец (25.08.2026): «документы на всех языках». Перевод, потерявший
/// раздел или пункт списка, — это обещание, данное на одном языке и снятое
/// на другом; ровно эту пропажу однажды поймал legal_text_test у порта.
void main() {
  const locales = ['ru', 'es', 'de', 'it', 'fr', 'pt'];

  String shape(LegalDoc doc) => doc.sections
      .map((s) => s.blocks.map((b) => switch (b) {
            LegalPara() => 'p',
            LegalPoints(:final items) => 'L${items.length}',
            LegalFact() => 'f',
            LegalFactBlank() => 'F',
            LegalBlank() => 'B',
          }).join())
      .join('|');

  for (final locale in locales) {
    test('$locale: структура блок в блок совпадает с английской', () {
      for (final which in LegalDocument.values) {
        expect(
          shape(LegalCatalog.of(locale, which)),
          shape(LegalText.of(which)),
          reason: 'документ $which на $locale разошёлся с эталоном по форме',
        );
      }
    });

    test('$locale: значения фактов не переведены — Pazl LLC остаётся собой',
        () {
      final imprint = LegalCatalog.of(locale, LegalDocument.imprint);
      final values = imprint.sections
          .expand((s) => s.blocks)
          .whereType<LegalFact>()
          .map((f) => f.value)
          .toList();
      expect(values, containsAll(['Pazl LLC', 'hello@pazl.ai', 'Apple']));
    });
  }

  test('ru: ни одного вежливого «вы» в пяти документах', () {
    final polite = RegExp(r'\b([Вв]ы|[Вв]ас|[Вв]ам|[Вв]ами|[Вв]аш\w*)\b');
    for (final which in LegalDocument.values) {
      final doc = LegalCatalog.of('ru', which);
      for (final section in doc.sections) {
        for (final block in section.blocks) {
          final texts = switch (block) {
            LegalPara(:final text) => [text],
            LegalPoints(:final items) => items,
            LegalFact(:final label) => [label],
            LegalFactBlank(:final label) => [label],
            LegalBlank() => const <String>[],
          };
          for (final text in texts) {
            expect(polite.hasMatch(text), isFalse,
                reason: 'вежливое «вы» в $which: «$text»');
          }
        }
      }
    }
  });

  test('fr: перед ? ! ; : стоит узкий неразрывный пробел', () {
    final bad = RegExp(r'[^ \s\d«][?!;:]');
    for (final which in LegalDocument.values) {
      final doc = LegalCatalog.of('fr', which);
      for (final section in doc.sections) {
        for (final block in section.blocks) {
          final texts = switch (block) {
            LegalPara(:final text) => [text],
            LegalPoints(:final items) => items,
            _ => const <String>[],
          };
          for (final text in texts) {
            final cleaned = text
                .replaceAll('reportaproblem.apple.com', '')
                .replaceAll('hello@pazl.ai', '');
            expect(bad.hasMatch(cleaned), isFalse,
                reason: 'обычный пробел перед знаком в $which: «$text»');
          }
        }
      }
    }
  });
}
