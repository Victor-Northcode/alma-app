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

  /// Гарнитура чтения — всё, что длиннее абзаца.
  ///
  /// **Третья роль появилась потому, что двух не хватило.** Дисплейной антиквой
  /// печатали и заголовок, и две тысячи знаков гороскопа; `today-reading-spec`
  /// называет это прямо: у Playfair высокий контраст, на 17 точках тонкие
  /// штрихи на тёмном пропадают, курсив добавляет наклон и связки, и такой
  /// текст больно читать. Playfair остаётся — но только в дисплее: имя дня,
  /// титулы, цифры, мета-строка.
  static const _reading = 'Lora';

  /// Засечные запасные — те же, что у дисплея: если Lora не доехала, текст
  /// должен остаться засечным, а не съехать в системный гротеск.
  static const _readingFallback = ['Charter', 'Georgia', 'Times New Roman', 'serif'];

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

  /* ── чтение ─────────────────────────────────────────────────────────────
     Три ступени `today-reading-spec §1`. Всё, что длиннее абзаца, печатается
     ими и только ими: гороскоп, читалка, голос Alma.                        */

  /// Лид — одна фраза, которой открывается чтение. Полужирный, 20/1.42.
  static final readingLead = TextStyle(
    fontFamily: _reading,
    fontFamilyFallback: _readingFallback,
    fontSize: 20,
    fontWeight: FontWeight.w500,
    fontVariations: const [FontVariation('wght', 500)],
    height: 1.42,
    color: AlmaPalette.inkLight,
  );

  /// Тело чтения. 17/1.65 — ступень «обычно» из трёх, которые даёт «Aa».
  ///
  /// Размер приходит снаружи ([readingSteps]), потому что выбор человека
  /// хранится за ним и переживает перезапуск. Интерлиньяж множителем, а не
  /// числом: на 19 точках 1.65 даёт 31 — на 16 те же 1.65 дают 26, и обе
  /// строки остаются одинаково просторными.
  static TextStyle readingBody([double size = 17]) => TextStyle(
        fontFamily: _reading,
        fontFamilyFallback: _readingFallback,
        fontSize: size,
        fontWeight: FontWeight.w400,
        fontVariations: const [FontVariation('wght', 400)],
        height: 1.65,
        color: AlmaPalette.inkLight.withValues(alpha: 0.95),
      );

  /// Три ступени кнопки «Aa»: мельче, обычно, крупнее.
  static const readingSteps = [16.0, 17.0, 19.0];

  /// Ответ Alma в беседе. Роль чтения, не дисплея.
  ///
  /// **Было: [voice] — Playfair Display, курсив, 18.5/1.5. Стало: Lora, прямое,
  /// 17/1.65.** Тот же довод, что уже записан у [_reading] и не был применён
  /// здесь: у Playfair высокий контраст, на семнадцати точках тонкие штрихи на
  /// тёмном пропадают, а курсив добавляет к этому наклон и связки. Одна фраза
  /// так читается — она и осталась так набрана: вступление и «нужно больше
  /// данных» на этом же экране печатаются [voice], потому что там курсив несёт
  /// голос, а не текст. Ответ на вопрос идёт тремя абзацами, и на трёх абзацах
  /// это перестаёт быть характером и становится трудом.
  ///
  /// Кегль и интерлиньяж — образцом взята глава, дословно: беседа и читалка
  /// печатают прозу одинаково, потому что это одна и та же проза одного и того
  /// же голоса, и разъезжаться им незачем. 17 меньше прежних 18.5, а строка при
  /// этом просторнее: 1.65 против 1.5 даёт 28 точек интерлиньяжа против 27.75.
  ///
  /// Ступени «Aa» сюда не приходят намеренно: у беседы нет этой кнопки, и
  /// заводить в ней вторую настройку размера ради одного экрана значило бы
  /// спрашивать человека о том, о чём он уже ответил в читалке.
  static final chatVoice = readingBody();

  /// Сноска — объяснение термина внутри карточки. 15/1.6.
  static final readingNote = TextStyle(
    fontFamily: _reading,
    fontFamilyFallback: _readingFallback,
    fontSize: 15,
    fontWeight: FontWeight.w400,
    fontVariations: const [FontVariation('wght', 400)],
    height: 1.6,
    color: AlmaPalette.body.withValues(alpha: 0.92),
  );

  /// Тихий подзаголовок смысловой части внутри чтения: Golos 600, 11, ls 2.2.
  ///
  /// Части размечает движок — клиент текст сам не режет. Строка стоит рядом с
  /// гаснущей линией и по весу обязана быть тише всего вокруг: это не заголовок
  /// раздела, а вздох между абзацами.
  static const readingPart = TextStyle(
    fontFamily: _ui,
    fontFamilyFallback: _uiFallback,
    fontSize: 11,
    fontWeight: FontWeight.w600,
    fontVariations: [FontVariation('wght', 600)],
    letterSpacing: 2.2,
    color: AlmaPalette.gold,
  );

  /// Шапка читалки: «16 АВГУСТА · ТВОЁ НЕБО». Golos 600, 10.5, ls 2.2.
  // `final`, а не `const`: `muted2` — вычисленная прозрачность, а не литерал.
  static final readerHead = TextStyle(
    fontFamily: _ui,
    fontFamilyFallback: _uiFallback,
    fontSize: 10.5,
    fontWeight: FontWeight.w600,
    fontVariations: const [FontVariation('wght', 600)],
    letterSpacing: 2.2,
    color: AlmaPalette.muted2,
  );
}
