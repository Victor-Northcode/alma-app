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

  /// Луна из расчёта транзитов: освещённость, растёт ли, строка вида
  /// «убывающий серп · 13%».
  Map<String, dynamic>? get moonNow {
    final result = sky;
    if (result is! LoadDone<CalcResult>) return null;
    final moon = result.value.data['moon'];
    return moon is Map ? moon.cast<String, dynamic>() : null;
  }

  Future<void> load({required String locale}) async {
    sky = const LoadRunning();
    line = const LoadRunning();
    notifyListeners();

    // Одновременно, как на iOS: гороскоп — это транзиты плюс письмо дня, и
    // ждать их по очереди значит удвоить время до первого слова на экране.
    await Future.wait([
      _loadSky(),
      _loadLine(locale),
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
