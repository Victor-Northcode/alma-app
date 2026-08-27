import 'package:flutter/foundation.dart'
    show TargetPlatform, defaultTargetPlatform;

import '../l10n/alma_l10n.dart';

/// Задвижка платформы магазина — для тестов и веб-просмотра.
///
/// Тесты про App Store закрепляют платформу здесь, а не через
/// `debugDefaultTargetPlatformOverride`: тот сторожится проверкой инвариантов
/// flutter_test между тестами и не переживает `setUpAll`. Веб-просмотр вне
/// релиза ставит её по `?store=apple` (`main.dart`): экраны с этой машины
/// смотрят веб-сборкой, и без ручки кадры витрин для App Store Connect
/// выходили со словами про Google Play (27.08.2026).
TargetPlatform? storeWordsPlatformOverride;

/// Слова о магазине — того магазина, в котором приложение живёт.
///
/// «Управлять в App Store», напечатанное на Android, — не мелочь: Play-версия
/// обязана называть свою подписку своими словами, и человек, которого послали
/// в чужой магазин, не найдёт там ни подписки, ни отмены. Восемь строк
/// каталога существуют парами (яблочная и Play-вариант с суффиксом Play);
/// выбор платформы стоит здесь один раз, а не восемью условиями по экранам.
extension StoreWords on L {
  // `defaultTargetPlatform`, а не `dart:io Platform`: тот отвечает про ОС
  // машины, на которой идёт код, — на устройствах это одно и то же, а в
  // тестах `Platform` непереопределяем и отвечал про хост. Прогон на Windows
  // печатал Play-строки в тех же тестах, что на Маке видели App Store, — два
  // «виндовых» красных, которые были не виндовыми (ревью 27.08.2026).
  bool get _apple =>
      switch (storeWordsPlatformOverride ?? defaultTargetPlatform) {
        TargetPlatform.iOS || TargetPlatform.macOS => true,
        _ => false,
      };

  String get storeManageInStore =>
      _apple ? cabManageInStore : cabManageInStorePlay;
  String get storeManagedBy =>
      _apple ? cabManagedByApple : cabManagedByGooglePlay;
  String get storeRestoredNone =>
      _apple ? paywallRestoredNone : paywallRestoredNonePlay;
  String get storeRestoring =>
      _apple ? paywallRestoring : paywallRestoringPlay;
  String get storeUnavailable =>
      _apple ? paywallStoreUnavailable : paywallStoreUnavailablePlay;
  String get storeManageNote =>
      _apple ? paywallManageNote : paywallManageNotePlay;
  String get storeSheetFootnote =>
      _apple ? pillSheetFootnote : pillSheetFootnotePlay;
  String get storeRenewalDisclosure => _apple
      ? paywallV3SubRenewalDisclosure
      : paywallV3SubRenewalDisclosurePlay;
}
