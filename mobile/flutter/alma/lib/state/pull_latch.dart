/// Решётка протяжки за дно главы: когда рука «взвела», когда «подтвердила»
/// и когда отпускание переворачивает страницу.
///
/// **Чистая механика без единого виджета** — и ровно поэтому отдельным
/// классом. Пороги 56 и 130 и правило «переворот только на отпускании»
/// проверяются здесь юнит-тестами напрямую: синтетический жест пробирки
/// не умеет честно тянуть резинку iOS (события пачками между кадрами гасятся
/// демпфером не так, как живой палец), и тест жеста годами проверял бы не
/// продукт, а причуды синтеза. Живая рука проверяется на симуляторе; решётка
/// — здесь.
class PullLatch {
  PullLatch({this.nearMark = 56.0, this.commitMark = 130.0});

  /// Первый порог: рука близко, хвост подсвечивается, тик хаптики.
  final double nearMark;

  /// Второй порог: упор взят; на отпускании страница перевернётся.
  final double commitMark;

  bool _armed = false;
  bool _committed = false;

  bool get armed => _armed;
  bool get committed => _committed;

  /// Что случилось на этом событии прокрутки.
  ///
  /// [byHand] — палец на стекле (у уведомления есть dragDetails). Инерция
  /// (byHand=false) не взводит и не подтверждает **никогда**: резкий смах,
  /// добивший резинку глубже порога, — это не решение человека, и глава
  /// держится, пока держат её.
  PullEvent onScroll(double distance, {required bool byHand}) {
    if (!byHand) {
      // Палец ушёл. Подтверждённый упор — переворот; всё прочее — отпускание.
      if (_committed) {
        _committed = false;
        _armed = false;
        return PullEvent.advance;
      }
      if (_armed && distance < nearMark * 0.7) {
        _armed = false;
        return PullEvent.disarmed;
      }
      return PullEvent.none;
    }
    if (distance >= nearMark && !_armed) {
      _armed = true;
      return PullEvent.armed;
    }
    if (distance < nearMark * 0.7 && _armed) {
      _armed = false;
      _committed = false;
      return PullEvent.disarmed;
    }
    if (distance >= commitMark && !_committed) {
      _committed = true;
      return PullEvent.committed;
    }
    return PullEvent.none;
  }

  /// Новая страница — новая решётка.
  void reset() {
    _armed = false;
    _committed = false;
  }
}

/// Ответ решётки на одно событие прокрутки.
enum PullEvent {
  none,

  /// Первый порог взят — лёгкий тик, полоса подсвечена.
  armed,

  /// Второй порог взят — тяжёлый тик, ждём отпускания.
  committed,

  /// Рука вернулась выше гистерезиса — подсветка гаснет.
  disarmed,

  /// Палец отпущен после подтверждения — переворачиваем страницу.
  advance,
}
