import 'package:shared_preferences/shared_preferences.dart';

import '../net/models.dart';

/// Сколько раз открывали главы каждой системы.
///
/// **Заведено ради одного экрана — V9, спасения от отмены.** Его строка — самая
/// сложная в каталоге: «Ты открывала эти шестнадцать глав одиннадцать раз. За
/// $4.99 они останутся читаемыми и после конца подписки». Оба числа — факт о
/// человеке, и без них экран превращается в обычный оффер: «купи натал»,
/// сказанное тому, кто уходит, — это не спасение, а последняя попытка продать.
/// Он же выбирает, **какую** систему предлагать: самую читаемую.
///
/// **Считает клиент, и это временно.** Правильное место для такой статистики —
/// сервер: он видит все устройства одного аккаунта, а этот счётчик умирает
/// вместе с установкой и не переезжает на новый телефон. Пока события чтения
/// не считаются на бэкенде, счёт здесь — минимальное честное приближение, и
/// экран умеет обходиться без него совсем (`paywallV3CancelSaveFactPlain`).
/// TODO(server): перенести на `/v1/events` или в собственную ручку профиля.
///
/// **Ничего личного здесь не лежит.** Слаг системы и целое число — ни текста,
/// ни времени, ни того, какую именно главу читали.
class ReadingTally {
  const ReadingTally._();

  static String _key(SystemSlug system) => 'reading.opens.${system.slug}';

  /// Глава этой системы открылась и была прочитана.
  ///
  /// Зовётся тогда, когда текст **приехал**, а не когда экран открылся: стена
  /// закрытой главы и ожидание письма — это не чтение, и считать их значило бы
  /// назвать самой читаемой ту систему, в которую чаще всего упирались.
  static Future<void> noteOpen(SystemSlug system) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_key(system), (prefs.getInt(_key(system)) ?? 0) + 1);
  }

  static Future<int> opens(SystemSlug system) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_key(system)) ?? 0;
  }

  /* ── пометки «прочитано» в оглавлении пары (W3) ─────────────────────────
     Отдельно от счёта открытий: там целое число на систему, здесь — признак
     на главу конкретной пары. Пара названа партнёром, потому что оглавление
     у каждого второго человека своё: «прочитано» у Маркуса ничего не говорит
     про Инес.                                                               */

  static String _chapterKey(SystemSlug system, String partnerId, String chapter) =>
      'reading.read.${system.slug}.$partnerId.$chapter';

  /// Глава этой пары открыта читаемой — с текстом, а не стеной.
  ///
  /// **Зовёт оглавление при переходе, а не сама глава.** Экран главы трогать
  /// нельзя (готовый паттерн C6), поэтому пометка ставится в момент тапа — и
  /// только по главе, которую сервер назвал открытой (`entry.open`): тап в
  /// закрытую главу — это встреча с дверью, а не чтение, и считать его
  /// значило бы пометить «прочитано» то, что человек ни разу не видел.
  /// TODO(server): как и счёт открытий, правильное место — сервер: пометка
  /// умирает с установкой и не переезжает на второе устройство.
  static Future<void> noteChapterRead(
      SystemSlug system, String partnerId, String chapter) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_chapterKey(system, partnerId, chapter), true);
  }

  /// Слаги прочитанных глав этой пары — для меток «read» в оглавлении.
  static Future<Set<String>> readChapters(
      SystemSlug system, String partnerId) async {
    final prefs = await SharedPreferences.getInstance();
    final prefix = 'reading.read.${system.slug}.$partnerId.';
    return prefs
        .getKeys()
        .where((key) => key.startsWith(prefix))
        .map((key) => key.substring(prefix.length))
        .toSet();
  }

  /// Самая читаемая из [among] — и `null`, если не читали ни одной.
  ///
  /// Пустой ответ здесь честнее первой попавшейся: экран спасения, назвавший
  /// «твоей самой читаемой» систему, которую человек не открывал ни разу,
  /// доказывает ровно обратное тому, ради чего он показан.
  static Future<SystemSlug?> mostRead(Iterable<SystemSlug> among) async {
    final prefs = await SharedPreferences.getInstance();
    SystemSlug? best;
    var bestCount = 0;
    for (final system in among) {
      final count = prefs.getInt(_key(system)) ?? 0;
      if (count > bestCount) {
        best = system;
        bestCount = count;
      }
    }
    return best;
  }
}
