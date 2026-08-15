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
/// **Шрифты теперь вшиты, и до 15 августа 2026 это было не так.**
///
/// Файл звал «Playfair Display» и «Golos Text» по имени с первого дня, а самих
/// файлов в приложении не было — ни одного .ttf ни в одном из трёх деревьев.
/// iOS молча брал первое установленное из списка ниже: засечным работал
/// системный New York, текстом — SF Pro. Экран выходил «почти правильным», и
/// именно поэтому расхождение с эталоном не бросалось в глаза: подмена была
/// красивой. Дизайн-проект пришёл с этими двумя семействами как с обязательными,
/// и теперь оба лежат в `assets/fonts` и объявлены в `pubspec.yaml`.
///
/// Файлы **вариативные**, по одному на начертание: одна ось `wght`, весь
/// диапазон 400–900, умолчание 400. Это легче набора отдельных весов и
/// позволяет брать промежуточные. Сабсеттинга не делалось: кириллица,
/// latin-ext, «ё» и кавычки-ёлочки внутри — иначе развалились бы шесть локалей
/// из семи.
///
/// **Вес такому файлу задаётся осью, а не `fontWeight`.** `fontWeight` выбирает
/// ближайший *объявленный* инстанс, а объявлен ровно один — поэтому один только
/// `fontWeight` рисует всё одинаково тонким, и полужирные надзаголовки молча
/// теряют вес. Ось двигает `fontVariations: [FontVariation('wght', N)]`, и она
/// проставлена там, где вес не 400. `fontWeight` рядом оставлен намеренно: он
/// нужен запасным шрифтам из `fontFamilyFallback` — у них осей нет.
///
/// У Playfair Display нижняя граница оси именно 400: просьба о 300 законно
/// рисуется как 400, так и в эталонах.
///
/// `fontFamilyFallback` остаётся как страховка на случай, если ассет не
/// доехал: тогда экран выглядит как раньше, а не пустыми квадратами.
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
    fontVariations: [FontVariation('wght', 600)],
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
  /// Голос Alma. 21 читался как заголовок: ответ на пол-экрана выходил
  /// плакатом, а это проза — «не очень красиво выглядит, текст очень крупный».
  /// 18.5 с чуть большим интерлиньяжем оставляют курсив узнаваемым и дают
  /// строке нормальную длину.
  static const voice = TextStyle(
    fontFamily: _display,
    fontFamilyFallback: _displayFallback,
    fontSize: 18.5,
    height: 1.5,
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

  /// Шрифты, в которых знак зодиака — типографика, а не картинка.
  ///
  /// Селектор U+FE0E Flutter не слушает и берёт Apple Color Emoji: «♌» в
  /// строке цитаты выходил фиолетовой плашкой с котёнком вместо знака. Колесо
  /// давно называет символьный шрифт прямо, а строки — нет; список тот же,
  /// чтобы вид знака не зависел от того, где он напечатан.
  static const glyphFallback = [
    'Apple Symbols',
    'Segoe UI Symbol',
    'Noto Sans Symbols 2',
    'serif',
  ];

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
    fontVariations: [FontVariation('wght', 600)],
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
    // Playfair начинается с 400: просьба о 300 законно рисуется как 400.
    fontWeight: FontWeight.w300,
    fontVariations: [FontVariation('wght', 400)],
    height: 1.55,
    color: AlmaPalette.inkLight.withValues(alpha: 0.95),
  );
}
