import '../net/models.dart' show SystemSlug;

/// Единственное место, где имена картинок написаны буквами.
///
/// Строковый путь, набранный по месту, ошибается молча: Flutter не находит
/// ассет, рисует пустоту и пишет в консоль, которую на устройстве никто не
/// читает. Здесь путь собирается из перечисления, а тест проверяет, что каждому
/// имени отсюда соответствует файл на диске и запись в `pubspec.yaml`.
/// **Перегонять только из `assets/`, никогда из `assets/opt/`.**
///
/// В дизайн-пакете папка `opt` названа рабочей, и это сбивает: она собрана как
/// веб-превью для холста эталонов, а не как спека бандла. Небо там 720 точек в
/// ширину — под @3x нужно 1320, и на телефоне вышло бы мыло на каждом экране.
/// Всё, что лежит в `assets/img`, перегнано из полноразмерных оригиналов:
/// небо 1320×2358, карты 840×1260, WebP q80, три масштаба.
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

  /// Филигрань-разделитель.
  ///
  /// **Альфы у файла нет.** Здесь стояло «кладётся маской, а не картинкой
  /// поверх фона» — и это было неправдой про этот файл: 358×120 WebP без
  /// альфа-канала, снимок броши на синем бархате. Положенный как есть, он даёт
  /// на небе прямоугольник с видимыми краями. Кто его ставит, тот и обязан
  /// кадрировать полосой и гасить края градиентной маской — как это делает
  /// `_Filigree` в `offer_screen.dart`.
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
