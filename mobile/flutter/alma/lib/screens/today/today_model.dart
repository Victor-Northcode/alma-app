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

  /// Открывающий абзац закрытой главы дня — бесплатная утренняя заметка W4.
  ///
  /// Есть только у закрытого ответа: открытому письму опенинг не пишется, а у
  /// закрытого он бывает пуст — потолок месяца выбран, модель промолчала, —
  /// и это законное состояние, а не сбой (`ReadingResponse.opening`). Экран
  /// на `null` показывает прежний замок и **не переспрашивает**: ретрай в
  /// цикле жёг бы серверу тот самый месячный потолок, из-за которого опенинга
  /// и нет.
  Reading? get openingNote {
    final answer = line;
    if (answer is! LoadDone<ReadingResponse>) return null;
    if (!answer.value.locked) return null;
    return answer.value.opening;
  }

  /// Сколько аспектов станут точными отсюда до конца воскресенья — живое
  /// число подписи «Транзиты недели» (W4: оно приходит из расчёта, не из
  /// словаря).
  ///
  /// `null` — небо ещё не пришло; ноль — честно тихая неделя. Оба списка, по
  /// той же причине, что в [nearest]: `active` — что в орбе сейчас,
  /// `upcoming` — что на подходе, и точность контакта из `active` может
  /// стоять в будущем. Прошедшие точности не считаются: «между сейчас и
  /// воскресеньем» — обещание вперёд, и вчерашний аспект в нём был бы
  /// враньём — ровно тем, за которое с этого экрана уже снимали далёкие даты.
  int? get exactUntilSunday {
    final result = sky;
    if (result is! LoadDone<CalcResult>) return null;
    final data = result.value.data;
    final now = DateTime.now();
    // Конец воскресенья — начало ближайшего понедельника по часам устройства:
    // сравнение «строго до» не требует возиться с 23:59.
    final today = DateTime(now.year, now.month, now.day);
    final monday = today.add(Duration(days: 8 - now.weekday));
    var count = 0;
    for (final key in const ['active', 'upcoming']) {
      for (final hit in (data[key] as List? ?? const []).whereType<Map>()) {
        final exact = DateTime.tryParse(hit['exact'] as String? ?? '');
        if (exact == null) continue;
        final local = exact.toLocal();
        if (!local.isBefore(now) && local.isBefore(monday)) count += 1;
      }
    }
    return count;
  }

  /// Небо считается всем; главу дня теперь просят оба тарифа.
  ///
  /// **Расчёт бесплатен навсегда, платны слова — и у слов два размера.**
  /// Подписчику ручка отвечает письмом дня целиком. Бесплатному тот же запрос
  /// отвечает 200 с `locked: true` и `opening`: ≈40 слов средней моделью из
  /// настоящих позиций — единственные токены до оплаты (`readings.py`,
  /// `_locked_chapter`). Раньше бесплатный тариф главу не просил вовсе, и это
  /// было правильно, пока закрытый блок был стеной: полная генерация в
  /// пустоту — деньги, потраченные зря. Теперь опенинг — сам крючок возврата
  /// (W4, §3 P5), и стоит он дешевле пустой панели. Месячное окно опенингов
  /// сервер держит сам: выбрано — приедет `opening: null`, и экран честно
  /// показывает замок, без ретрая.
  ///
  /// [subscriber] больше не решает, лететь ли запросу, — но остаётся в
  /// подписи: экран им решает, что рисовать, и параметр держит обе половины
  /// решения в одном вызове.
  /// Номер живой загрузки. Причин перечитать экран стало три (профиль, права,
  /// язык — 28.08.2026), и две загрузки подряд перестали быть теорией: письмо
  /// дня едет секунды, и ответ прежнего языка, пришедший после нового, ставил
  /// бы текст на старом языке поверх уже начатого перечитывания. Побеждает
  /// последний заход, а не быстрейший.
  int _epoch = 0;

  Future<void> load({required String locale, required bool subscriber}) async {
    final epoch = ++_epoch;
    sky = const LoadRunning();
    line = const LoadRunning();
    notifyListeners();

    // Одновременно, как на iOS: гороскоп — это транзиты плюс письмо дня, и
    // ждать их по очереди значит удвоить время до первого слова на экране.
    await Future.wait([
      _loadSky(epoch),
      _loadLine(locale, epoch),
    ]);
  }

  Future<void> _loadSky(int epoch) async {
    try {
      final result = await client.compute(SystemSlug.transits);
      if (epoch != _epoch) return;
      sky = LoadDone(result);
    } on AlmaError catch (error) {
      if (epoch != _epoch) return;
      sky = LoadFailed(error);
    }
    notifyListeners();
  }

  Future<void> _loadLine(String locale, int epoch) async {
    try {
      final result = await client.reading(
        system: SystemSlug.transits,
        chapter: 'active',
        locale: locale,
      );
      if (epoch != _epoch) return;
      line = LoadDone(result);
    } on AlmaError catch (error) {
      if (epoch != _epoch) return;
      line = LoadFailed(error);
    }
    notifyListeners();
  }
}
