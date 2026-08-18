import 'dart:io' show Platform;

import '../l10n/alma_l10n.dart';

/// Слова о магазине — того магазина, в котором приложение живёт.
///
/// «Управлять в App Store», напечатанное на Android, — не мелочь: Play-версия
/// обязана называть свою подписку своими словами, и человек, которого послали
/// в чужой магазин, не найдёт там ни подписки, ни отмены. Восемь строк
/// каталога существуют парами (яблочная и Play-вариант с суффиксом Play);
/// выбор платформы стоит здесь один раз, а не восемью условиями по экранам.
extension StoreWords on L {
  bool get _apple => Platform.isIOS || Platform.isMacOS;

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
