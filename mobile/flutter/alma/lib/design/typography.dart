import 'package:flutter/widgets.dart';

import 'palette.dart';

/// Шкала, названная по тому, **чем строка является**, а не по её размеру:
/// экран, просящий `displayXl`, не может случайно поставить 39 пунктов на
/// подпись.
///
/// Порт `mobile/ios/Alma/DesignSystem/Typography.swift`. Размеры — те же, что
/// у веб-приложения на телефоне; настольные ступени не переносились, потому что
/// телефон есть телефон.
///
/// **Про шрифты — и это оказалось не тем, чего мы боялись.**
///
/// Ни iOS, ни Android **не кладут файлы шрифтов в приложение**: проверено, ни
/// одного .ttf или .otf в обоих деревьях. iOS перебирает список — Playfair
/// Display, New York, Charter, Georgia — и берёт первый установленный; ни
/// Playfair, ни Golos Text на телефоне не установлены, так что засечным
/// работает системный New York, а текстом системный SF Pro. Android идёт тем же
/// путём через `FontFamily.Serif` и `FontFamily.SansSerif`.
///
/// То есть настоящая гарнитура продукта — **гарнитура платформы**, и это то
/// самое, что делает нативный экран таким, каким он выглядит. Значит просить
/// надо ровно её, тем же списком и с тем же порядком: `fontFamilyFallback`
/// делает во Flutter то же, что `firstInstalled` делает в Swift — берёт первое,
/// что есть на устройстве.
///
/// Риск от шрифта из-за этого гораздо меньше, чем казалось: мы не подменяем
/// гарнитуру своей, мы просим ту же. Остаётся различие в **раскладке**: Flutter
/// сам переносит строки и расставляет межбуквенные интервалы, а не отдаёт это
/// системе. Это проверяется только сравнением на устройстве.
class AlmaType {
  const AlmaType._();

  static const _display = 'Playfair Display';
  static const _ui = 'Golos Text';

  /// Тот же список, что в `AlmaFonts.displayFamilies` на iOS, и системный
  /// засечный последним — на Android и в браузере ни одного из первых нет.
  static const _displayFallback = ['New York', 'Charter', 'Georgia', 'serif'];

  /// Пусто по смыслу: не найдя Golos Text, платформа берёт свой текстовый
  /// шрифт — SF Pro на iOS, Roboto на Android. Именно это и происходит в
  /// нативных приложениях сегодня.
  static const _uiFallback = ['-apple-system', 'SF Pro Text', 'Roboto', 'sans-serif'];

  /// Надзаголовок раздела: 11.5 пунктов, разрядка .22em, прописные, золото.
  /// Регистр меняет вызывающая сторона — шрифт его не несёт.
  static const overline = TextStyle(
    fontFamily: _ui,
    fontFamilyFallback: _uiFallback,
    fontSize: 11.5,
    fontWeight: FontWeight.w600,
    letterSpacing: 11.5 * 0.22,
    color: AlmaPalette.gold,
    height: 1.3,
  );

  /// Главная строка экрана. Одна на экран, не больше.
  static const displayXl = TextStyle(
    fontFamily: _display,
    fontFamilyFallback: _displayFallback,
    fontSize: 39,
    height: 1.08,
    color: AlmaPalette.inkLight,
  );

  /// Заголовки экранов и разделов.
  static const displayL = TextStyle(
    fontFamily: _display,
    fontFamilyFallback: _displayFallback,
    fontSize: 29,
    height: 1.12,
    color: AlmaPalette.inkLight,
  );

  /// Заголовки строк и карточек.
  static const headingM = TextStyle(
    fontFamily: _display,
    fontFamilyFallback: _displayFallback,
    fontSize: 17.5,
    height: 1.25,
    color: AlmaPalette.inkLight,
  );

  /// Голос Alma. Курсив ставит вызывающая сторона.
  static const voice = TextStyle(
    fontFamily: _display,
    fontFamilyFallback: _displayFallback,
    fontSize: 21,
    height: 1.42,
    fontStyle: FontStyle.italic,
    color: AlmaPalette.inkLight,
  );

  /// Основной текст — само чтение.
  static final body = TextStyle(
    fontFamily: _ui,
    fontFamilyFallback: _uiFallback,
    fontSize: 15.5,
    height: 1.55,
    color: AlmaPalette.body,
  );

  /// Второстепенные строки под заголовком.
  static final meta = TextStyle(
    fontFamily: _ui,
    fontFamilyFallback: _uiFallback,
    fontSize: 13,
    height: 1.45,
    color: AlmaPalette.muted,
  );

  /// Числа глав и градусы — засечным, потому что позиция в этом дизайне
  /// типографика, а не значок.
  static const numeral = TextStyle(
    fontFamily: _display,
    fontFamilyFallback: _displayFallback,
    fontSize: 14,
    color: AlmaPalette.gold,
  );

  /// Подписи кнопок.
  static const button = TextStyle(
    fontFamily: _ui,
    fontFamilyFallback: _uiFallback,
    fontSize: 16.5,
    fontWeight: FontWeight.w600,
    color: AlmaPalette.inkOnGold,
  );

  /// Метки: 10.5 пунктов, разрядка .12em, прописные.
  static const tag = TextStyle(
    fontFamily: _ui,
    fontFamilyFallback: _uiFallback,
    fontSize: 10.5,
    letterSpacing: 10.5 * 0.12,
    color: AlmaPalette.gold,
  );

  /// Голос дня — тот же засечный, чуть мельче голоса Alma.
  /// Голос дня. Значение в значение с `almaDayVoice()`: 17.5 светлым
  /// начертанием, интерлиньяж 1.55, чернила приглушены до 0.95.
  ///
  /// Здесь стояли 19 обычным весом и 1.5 — на кадре рядом с нативом текст дня
  /// был заметно крупнее и жирнее, и на экран помещалось на треть меньше.
  /// «Твой день слишком длинным текстом описывается, нужно короче и тоньше
  /// шрифт» — правка, ради которой этот стиль и появился на нативе.
  static final dayVoice = TextStyle(
    fontFamily: _display,
    fontFamilyFallback: _displayFallback,
    fontSize: 17.5,
    fontWeight: FontWeight.w300,
    height: 1.55,
    color: AlmaPalette.inkLight.withValues(alpha: 0.95),
  );
}
