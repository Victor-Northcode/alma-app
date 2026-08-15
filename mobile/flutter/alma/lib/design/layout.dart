import 'package:flutter/widgets.dart';

/// Четыре ширины, на которых продукт живёт, и всё, что от ширины зависит.
///
/// Свод из дизайн-проекта, раздел «Adaptive & Locales». В самом архиве этого
/// раздела нет — числа продиктованы владельцем 15 августа 2026 и записаны здесь
/// дословно, потому что второго источника у них нет.
///
/// **Зачем отдельный слой, а не `MediaQuery` по месту.** Ширина влияет на
/// девять величин сразу — поле, герой, титул, медальон, вклейку, бар, рейл,
/// колонку, число столбцов колоды. Спрошенная по месту, каждая из них уезжает
/// на своём экране по-своему, и через месяц планшет выглядит как четыре разных
/// приложения. Здесь они считаются один раз и берутся готовыми.
///
/// **Ничего не прячется.** Ни на одной ширине не исчезает ни один элемент:
/// узкий экран просто раньше начинает скроллиться. Это правило владельца и оно
/// же — причина, по которой compact сводится к числам, а не к «сократить».
enum AlmaBand {
  /// ≤380: маленькие телефоны. SE, mini, и любой, у кого крупный системный шрифт.
  compact,

  /// 381–743: эталон дизайна — 402×874, все экраны S1…S47 нарисованы здесь.
  ///
  /// Верхняя граница 743, а не 500: между 501 и 743 живут большие телефоны в
  /// альбоме и семидюймовые планшеты, а рейл начинается только с 744. Свод
  /// называет полосу «381–500» и следующую «≥744», не говоря про промежуток;
  /// раскладка телефона держится до самого рейла, потому что вертикальная
  /// колонка на 600 точках съела бы шестую часть ширины ради четырёх подписей.
  phone,

  /// ≥744, книжная: таб-бар уходит влево вертикальным рейлом, низ пуст.
  tabletPortrait,

  /// ≥1024, альбомная: глава — разворот в две страницы, рисунки данных
  /// двухпанельно.
  tabletLandscape,
}

/// Все размеры, зависящие от ширины, посчитанные один раз.
@immutable
class AlmaLayout {
  const AlmaLayout._({
    required this.band,
    required this.pad,
    required this.hero,
    required this.title,
    required this.medallion,
    required this.plateScale,
    required this.tabBar,
    required this.railWidth,
    required this.column,
    required this.deckColumns,
    required this.dialogMax,
  });

  final AlmaBand band;

  /// Боковое поле экрана.
  final double pad;

  /// Кегль главной строки — имя на «Сегодня».
  final double hero;

  /// Кегль титула экрана.
  final double title;

  /// Сторона медальона луны.
  final double medallion;

  /// Множитель высоты арки-вклейки: на узком экране вклейка ниже на 18%.
  final double plateScale;

  /// Полная высота таб-бара вместе с зоной домашнего индикатора.
  final double tabBar;

  /// Ширина вертикального рейла. Ноль на телефоне — рейла там нет.
  final double railWidth;

  /// Предел ширины колонки контента. Шире текст не растягивается никогда:
  /// строка длиннее теряется глазом, и планшет начинает читаться хуже телефона.
  final double column;

  /// Сколько карт в ряду на «Мои системы».
  final int deckColumns;

  /// Предел ширины модалки. На телефоне шит во всю ширину — предела нет.
  final double? dialogMax;

  /// Рейл вместо нижнего бара.
  bool get hasRail => railWidth > 0;

  /// Разворот в две страницы и двухпанельные рисунки данных.
  bool get isSpread => band == AlmaBand.tabletLandscape;

  /// Пропорция разворота главы: левая страница шире правой.
  static const spreadSplit = 0.55;

  static AlmaLayout of(BuildContext context) =>
      resolve(MediaQuery.sizeOf(context).width);

  /// Отдельно от [of], чтобы тест мог спросить полосу, не поднимая дерева.
  static AlmaLayout resolve(double width) {
    if (width >= 1024) {
      return const AlmaLayout._(
        band: AlmaBand.tabletLandscape,
        pad: 22, hero: 44, title: 33, medallion: 86, plateScale: 1,
        tabBar: 0, railWidth: 92, column: 560, deckColumns: 3, dialogMax: 420,
      );
    }
    if (width >= 744) {
      return const AlmaLayout._(
        band: AlmaBand.tabletPortrait,
        pad: 22, hero: 44, title: 33, medallion: 86, plateScale: 1,
        tabBar: 0, railWidth: 92, column: 560, deckColumns: 3, dialogMax: 420,
      );
    }
    if (width <= 380) {
      return const AlmaLayout._(
        band: AlmaBand.compact,
        pad: 18, hero: 33, title: 26, medallion: 68, plateScale: 0.82,
        tabBar: 72, railWidth: 0, column: double.infinity, deckColumns: 2,
        dialogMax: null,
      );
    }
    return const AlmaLayout._(
      band: AlmaBand.phone,
      pad: 22, hero: 39, title: 29, medallion: 86, plateScale: 1,
      tabBar: 84, railWidth: 0, column: double.infinity, deckColumns: 2,
      dialogMax: null,
    );
  }
}

/// Полы ужатия подписей — у каждого рода строки свой.
///
/// «Минимум 11» из `SKILL.md` относится к мете и подписям, а не к кнопкам: у
/// кнопки свой пол 14, и ниже него подпись не ужимают, а **заменяют** коротким
/// словарным вариантом — «Alle Live-Funktionen, wöchentlich · 4,99 €» становится
/// «Wöchentlich · 4,99 €». Ужатая до неразличимости кнопка выглядит сломанной,
/// а короткая строка — написанной.
class AlmaShrink {
  const AlmaShrink._();

  /// Кнопки: 16.5 → 15 → 14. Ниже — короткий вариант строки, а не мельче.
  static const buttonSteps = <double>[16.5, 15, 14];
  static const buttonFloor = 14.0;

  /// Подписи вкладок и рейла: 10 → 9, всегда одной строкой.
  static const tabLabel = 10.0;
  static const tabLabelFloor = 9.0;

  /// Юридические строки: 12.5 → 11.
  static const legal = 12.5;
  static const legalFloor = 11.0;

  /// Тело текста **не ужимается никогда** — 15.5 остаётся на всех ширинах и во
  /// всех языках. Немецкий и русский длиннее английского на 10–30%, и ответ на
  /// это — перенос, а не мельче: текст, который стал нечитаемым, не помещается
  /// вообще, он просто выглядит помещённым.
  static const bodyFixed = 15.5;

  /// Подобрать подпись кнопки под ширину: сначала кегль, потом словарь.
  ///
  /// Порядок из правил владельца и он не переставляется: спуститься по
  /// ступеням до 14, и **только если и там не влезло** — взять короткий
  /// вариант строки, снова с самого верха. Кнопка с подписью мельче 14 читается
  /// сломанной вёрсткой; кнопка с более коротким словом читается кнопкой.
  ///
  /// Короткий вариант есть далеко не в каждом языке: «Anmeldelink per E-Mail
  /// senden» ужимается до «Link senden», а «Прислать ссылку для входа» короче
  /// не становится — и тогда `short` совпадает с `label`, ступень 14 остаётся
  /// последним словом, и это честнее выдуманного сокращения.
  static ({String text, double size}) fitLabel({
    required String label,
    required TextStyle style,
    required double maxWidth,
    String? short,
    List<double> steps = buttonSteps,
    TextScaler scaler = TextScaler.noScaling,
  }) {
    // Ширины нет — мерить нечего; отдаём как есть, а не гадаем.
    if (!maxWidth.isFinite || maxWidth <= 0) {
      return (text: label, size: steps.first);
    }
    double width(String text, double size) {
      final painter = TextPainter(
        text: TextSpan(text: text, style: style.copyWith(fontSize: size)),
        maxLines: 1,
        textDirection: TextDirection.ltr,
        textScaler: scaler,
      )..layout();
      return painter.width;
    }

    for (final candidate in [label, if (short != null && short != label) short]) {
      for (final size in steps) {
        if (width(candidate, size) <= maxWidth) {
          return (text: candidate, size: size);
        }
      }
    }
    // Не влезло ничего: короткий вариант на нижней ступени — дальше многоточие,
    // и решает его уже сам `Text`.
    return (
      text: short ?? label,
      size: steps.last,
    );
  }
}

/// Правила, которые зависят от языка, а не от ширины.
class AlmaLocaleRules {
  const AlmaLocaleRules._();

  /// Разрядка прописных: 2.5 для латиницы, 1.8 для кириллицы.
  ///
  /// Кириллическая прописная шире латинской, и та же разрядка растаскивает
  /// надзаголовок в решётку. Проверяется по самой строке, а не по локали:
  /// в русском интерфейсе попадаются латинские надписи (Alma), и им нужна
  /// своя разрядка.
  static double capsTracking(String text) =>
      _hasCyrillic(text) ? 1.8 : 2.5;

  static bool _hasCyrillic(String s) {
    for (final c in s.runes) {
      if (c >= 0x0400 && c <= 0x04FF) return true;
    }
    return false;
  }

  /// Что не переводится ни на одном языке: имя продукта, римские цифры,
  /// градусы и знаки. Список нужен вычитке, а не коду, — но живёт рядом с
  /// правилами, чтобы его нашли.
  static const untranslated = <String>['Alma', 'I…XVI', '°', '′', '☉ ☽ ♀ …'];
}
