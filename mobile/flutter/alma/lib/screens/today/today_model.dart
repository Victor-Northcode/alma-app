import 'package:flutter/foundation.dart';

import '../../net/alma_client.dart';
import '../../net/models.dart';

/// Состояние одной загрузки: пусто → идёт → пришло/отказ.
sealed class Load<T> {
  const Load();
}

class LoadIdle<T> extends Load<T> {
  const LoadIdle();
}

class LoadRunning<T> extends Load<T> {
  const LoadRunning();
}

class LoadDone<T> extends Load<T> {
  const LoadDone(this.value);
  final T value;
}

class LoadFailed<T> extends Load<T> {
  const LoadFailed(this.error);
  final AlmaError error;
}

/// Запросы «Сегодня» и горсть фактов, из них извлечённых.
///
/// Порт `TodayModel` из `TodayScreen.swift`. Модель, а не состояние в виджете,
/// по той же причине, что и там: экран — функция состояния и сам в сеть не
/// ходит. Запросы летят одновременно; последовательно это были бы четыре
/// круга по сети.
class TodayModel extends ChangeNotifier {
  TodayModel(this.client);

  final AlmaClient client;

  Load<CalcResult> sky = const LoadIdle();
  Load<ReadingResponse> line = const LoadIdle();

  /// Луна из расчёта транзитов: фаза, освещённость, растёт ли.
  ///
  /// **Путь именно такой, и он не сокращается.** Здесь лежал геттер, читавший
  /// `data['moon']`, — движок кладёт луну в `data['sky_now']['moon_phase']`, и
  /// геттер молча возвращал `null` всегда. Экран этим не пользовался и брал
  /// фазу сам, поэтому ошибка ничего не ломала и жила незамеченной: мёртвый
  /// код, отвечающий неправдой, — это ловушка, расставленная следующему.
  Map<String, dynamic>? get moonPhase {
    final result = sky;
    if (result is! LoadDone<CalcResult>) return null;
    final now = result.value.data['sky_now'];
    if (now is! Map) return null;
    final moon = now['moon_phase'];
    return moon is Map ? moon.cast<String, dynamic>() : null;
  }

  /// Ближайший контакт области или `null` — «здесь сегодня тихо».
  ///
  /// **Оба списка, и пропуск одного — то, что опустошало экран.** `active` —
  /// что в орбе прямо сейчас, `upcoming` — что на подходе; читая только первый,
  /// владелец открыл гороскоп, где все четыре области сказали «тихо». Они
  /// говорили правду про `active` — а в `upcoming` стояло сорок контактов.
  /// Написанная строка области — или `null`, если её никто не писал.
  ///
  /// Живёт рядом с [nearest] намеренно: обе половины одной строки экрана —
  /// **какой контакт** и **что он значит** — приходят из разных мест, из
  /// расчёта и из письма, и держать их в одном месте единственный способ не
  /// забыть, что они обязаны быть про одно и то же.
  String? areaLine(String area) {
    final answer = line;
    if (answer is! LoadDone<ReadingResponse>) return null;
    // Пусто и когда главы в ответе нет вовсе: у закрытой главы `reading` пуст,
    // а области дня — часть купленного текста, а не открывающего абзаца.
    return answer.value.reading?.areas[area];
  }

  Map<String, dynamic>? nearest(String area) {
    final result = sky;
    if (result is! LoadDone<CalcResult>) return null;
    final data = result.value.data;
    final hits = <Map<String, dynamic>>[
      for (final key in const ['active', 'upcoming'])
        ...(data[key] as List? ?? const [])
            .whereType<Map>()
            .map((e) => e.cast<String, dynamic>())
            .where((e) => e['area'] == area),
    ];
    if (hits.isEmpty) return null;
    // Самый срочный первым — тот же порядок, что у движка.
    hits.sort((a, b) => ((b['urgency'] as num?) ?? 0)
        .compareTo((a['urgency'] as num?) ?? 0));
    return hits.first;
  }

  /// Небо считается всем, письмо дня — только тому, кому его покажут.
  ///
  /// **Расчёт бесплатен навсегда, платны слова.** Небо нужно и без подписки:
  /// из него медальон луны и фаза в шапке. А вот главу дня незачем даже
  /// просить у сервера, если экран её не покажет: это деньги за генерацию,
  /// потраченные в пустоту, и — на бесплатном тарифе — месячный потолок,
  /// сгорающий на тексте, которого никто не прочтёт.
  Future<void> load({required String locale, required bool subscriber}) async {
    sky = const LoadRunning();
    line = subscriber ? const LoadRunning() : const LoadIdle();
    notifyListeners();

    // Одновременно, как на iOS: гороскоп — это транзиты плюс письмо дня, и
    // ждать их по очереди значит удвоить время до первого слова на экране.
    await Future.wait([
      _loadSky(),
      if (subscriber) _loadLine(locale),
    ]);
  }

  Future<void> _loadSky() async {
    try {
      final result = await client.compute(SystemSlug.transits);
      sky = LoadDone(result);
    } on AlmaError catch (error) {
      sky = LoadFailed(error);
    }
    notifyListeners();
  }

  Future<void> _loadLine(String locale) async {
    try {
      final result = await client.reading(
        system: SystemSlug.transits,
        chapter: 'active',
        locale: locale,
      );
      line = LoadDone(result);
    } on AlmaError catch (error) {
      line = LoadFailed(error);
    }
    notifyListeners();
  }
}
