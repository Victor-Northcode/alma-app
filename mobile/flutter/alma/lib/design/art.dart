import '../net/models.dart' show SystemSlug;

/// Единственное место, где имена картинок написаны буквами.
///
/// Строковый путь, набранный по месту, ошибается молча: Flutter не находит
/// ассет, рисует пустоту и пишет в консоль, которую на устройстве никто не
/// читает. Здесь путь собирается из перечисления, а тест проверяет, что каждому
/// имени отсюда соответствует файл на диске и запись в `pubspec.yaml`.
class AlmaArt {
  const AlmaArt._();

  static const _dir = 'assets/img';

  /// Туманность за всем продуктом. Стоит на всех сорока восьми эталонных
  /// экранах и всегда под скримом — см. `NightBackground`.
  static const sky = '$_dir/bg-sky.webp';

  /// Продающий слой. Каждая картина встречается один-два раза и только на
  /// пороге: витрина, дверь, приглашение.
  static const gates = '$_dir/art-gates.webp';
  static const fan = '$_dir/art-fan.webp';
  static const couple = '$_dir/art-couple.webp';
  static const globe = '$_dir/art-globe.webp';

  /// Филигрань-разделитель. Кладётся маской, а не картинкой поверх фона.
  static const divider = '$_dir/art-divider.webp';

  /// Карта системы для колоды «Мои системы» и для героя двери.
  ///
  /// Один файл на оба места: в колоде карта рисуется вчетверо мельче своего
  /// размера, и это дешевле, чем держать два набора.
  static String card(SystemSlug system) => '$_dir/card-${_cardName(system)}.webp';

  /// Имена файлов художника не совпадают со слагами движка в трёх местах из
  /// восьми, и это не повод переименовывать ни то, ни другое: слаг — контракт
  /// с сервером, имя файла — контракт с дизайн-пакетом. Карта между ними живёт
  /// здесь, одна на приложение.
  static String _cardName(SystemSlug system) => switch (system) {
        SystemSlug.natal => 'natal',
        SystemSlug.numerology => 'numerology',
        SystemSlug.birthCard => 'birthcard',
        SystemSlug.transits => 'transits',
        SystemSlug.solarReturn => 'solar',
        SystemSlug.compatibility => 'compat',
        SystemSlug.astrocartography => 'astro',
        SystemSlug.synthesis => 'synthesis',
      };

  /// Всё, что вшито в приложение, — для теста, который сверяет список с диском.
  static List<String> get bundled => [
        sky, gates, fan, couple, globe, divider,
        for (final s in SystemSlug.values) card(s),
      ];
}
