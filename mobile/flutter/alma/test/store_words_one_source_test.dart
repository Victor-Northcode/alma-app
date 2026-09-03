import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// **Строка, называющая магазин, зовётся только через StoreWords.**
///
/// Восемь ключей с «Apple» внутри ходили с экранов напрямую, и живой
/// Android печатал «Apple принял платёж» и «настройки Apple ID» — владелец,
/// 02.09.2026: «на андроиде написано что оплату принимает эпл — зачем».
/// Пары *Play существуют для каждой, выбор платформы стоит в одном месте
/// (`billing/store_words.dart`), и этот тест — то, что не даст девятому
/// ключу повторить дорогу восьми: прямой вызов `l.<яблочный ключ>` с экрана
/// падает здесь по имени файла и ключа.
void main() {
  test('яблочные строки не зовутся с экранов напрямую', () {
    // Ключи, у которых есть Play-близнец. Голый ключ со «своим» магазином —
    // всегда ошибка вне store_words.dart.
    const storeBound = [
      'paywallNotVerified',
      'paywallVerifyLater',
      'paywallWithdrawn',
      'paywallV3PlansLegal',
      'paywallV3CancelNote',
      'paywallV3CancelNoteNoDate',
      'paywallV3StateProcessingNote',
      'cabPlanRenewsAtStore',
      'cabManageInStore',
      'cabManagedByApple',
      'paywallManageNote',
      'paywallRestoredNone',
      'paywallRestoring',
      'paywallStoreUnavailable',
      'paywallV3SubRenewalDisclosure',
      'pillSheetFootnote',
    ];

    final offenders = <String>[];
    final dart = Directory('lib')
        .listSync(recursive: true)
        .whereType<File>()
        .where((f) => f.path.endsWith('.dart'))
        .where((f) => !f.path.replaceAll('\\', '/').contains('/l10n/'))
        .where((f) =>
            !f.path.replaceAll('\\', '/').endsWith('billing/store_words.dart'));
    for (final file in dart) {
      final source = file.readAsStringSync();
      for (final key in storeBound) {
        // `l.paywallNotVerified,` — прямой вызов; `l.storeNotVerified` — нет.
        final direct = RegExp('\\bl\\.$key\\b');
        if (direct.hasMatch(source)) {
          offenders.add('${file.path}: l.$key');
        }
      }
    }
    expect(offenders, isEmpty,
        reason: 'строка магазина в обход StoreWords — это «Apple» на живом '
            'Android; зовите store*-двойника: $offenders');
  });
}
