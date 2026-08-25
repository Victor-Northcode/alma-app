import 'legal_text.dart';
import 'legal_text_de.dart';
import 'legal_text_es.dart';
import 'legal_text_fr.dart';
import 'legal_text_it.dart';
import 'legal_text_pt.dart';
import 'legal_text_ru.dart';

/// Пять документов на языке читателя.
///
/// До 25.08.2026 документы жили только по-английски — осознанно: переведённая
/// юридическая оговорка без проверки юристом может не связывать потребителя
/// (довод записан в шапке `legal_text.dart`). Владелец решил иначе: «сделай
/// их все на всех языках». Перевод смысловой и структурно зеркальный —
/// `test/legal_catalog_test.dart` сверяет каждый язык с английским блок в
/// блок, — но юрпроверку по юрисдикциям он не заменяет, и это честно сказано
/// владельцу, а не спрятано.
///
/// Незнакомая локаль честно получает английский — он остаётся эталоном.
class LegalCatalog {
  const LegalCatalog._();

  static String _lang(String localeName) =>
      localeName.split(RegExp('[_-]')).first.toLowerCase();

  static LegalDoc of(String localeName, LegalDocument which) =>
      switch (_lang(localeName)) {
        'ru' => LegalTextRu.of(which),
        'es' => LegalTextEs.of(which),
        'de' => LegalTextDe.of(which),
        'it' => LegalTextIt.of(which),
        'fr' => LegalTextFr.of(which),
        'pt' => LegalTextPt.of(which),
        _ => LegalText.of(which),
      };

  static String updated(String localeName) => switch (_lang(localeName)) {
        'ru' => LegalTextRu.updated,
        'es' => LegalTextEs.updated,
        'de' => LegalTextDe.updated,
        'it' => LegalTextIt.updated,
        'fr' => LegalTextFr.updated,
        'pt' => LegalTextPt.updated,
        _ => LegalText.updated,
      };

  static String preamble(String localeName) => switch (_lang(localeName)) {
        'ru' => LegalTextRu.preamble,
        'es' => LegalTextEs.preamble,
        'de' => LegalTextDe.preamble,
        'it' => LegalTextIt.preamble,
        'fr' => LegalTextFr.preamble,
        'pt' => LegalTextPt.preamble,
        _ => LegalText.preamble,
      };

  static String footer(String localeName) => switch (_lang(localeName)) {
        'ru' => LegalTextRu.footer,
        'es' => LegalTextEs.footer,
        'de' => LegalTextDe.footer,
        'it' => LegalTextIt.footer,
        'fr' => LegalTextFr.footer,
        'pt' => LegalTextPt.footer,
        _ => LegalText.footer,
      };
}
