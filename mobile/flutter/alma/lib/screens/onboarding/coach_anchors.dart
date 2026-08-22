import 'package:flutter/widgets.dart';

/// Куда обучалка показывает пальцем.
///
/// **Ключи, а не координаты.** Вырез в затемнении обязан лежать ровно на
/// настоящем элементе настоящего экрана — иначе это уже не подсветка продукта,
/// а картинка о нём. Числа сюда вписать нельзя: высота карты колоды считается
/// от окна (`SystemsScreen._cardHeight`), панель дня стоит после шапки, чья
/// высота зависит от длины имени человека, а на планшете и на маленьком
/// телефоне не совпадает ни то, ни другое. Поэтому экраны вешают ключ на свой
/// элемент, а обучалка спрашивает у него прямоугольник в тот момент, когда
/// собирается его подсветить.
///
/// **Экранам это ничего не стоит.** Ключ на уже существующем виджете не
/// добавляет ни узла в дерево, ни точки в разметку: вёрстка вкладок остаётся
/// той же, какой была, и её тесты — тоже.
class CoachAnchors {
  const CoachAnchors._();

  /// «8/8 рассчитано» в шапке «Моих систем» — доказательство того, что говорит
  /// первый шаг.
  static final systemsTally = GlobalKey(debugLabel: 'coach.systems.tally');

  /// Первый ряд колоды: натальная карта и карта рождения.
  static final systemsFirstRow = GlobalKey(debugLabel: 'coach.systems.row');

  /// Стеклянная панель дня на «Сегодня» — заметка и живой слой под ней.
  static final todayPanel = GlobalKey(debugLabel: 'coach.today.panel');

  /// Композер беседы с Alma — поле вопроса и кнопка отправки.
  static final almaComposer = GlobalKey(debugLabel: 'coach.alma.composer');

  /// Тумблер «каждое утро» в настройках — три положения рассылки.
  static final settingsMorning = GlobalKey(debugLabel: 'coach.settings.morning');

  /// Где сейчас стоит помеченный виджет, в координатах экрана.
  ///
  /// `null` — законный ответ, и он значит «этого на экране сейчас нет»: хаб ещё
  /// не приехал и колода пуста, панель дня не построена, страница вкладки не
  /// доехала. Обучалка на такой ответ показывает карточку без выреза, а не
  /// вырез в пустом месте.
  static Rect? rect(GlobalKey key) {
    final context = key.currentContext;
    if (context == null) return null;
    final box = context.findRenderObject();
    if (box is! RenderBox || !box.attached || !box.hasSize) return null;
    return box.localToGlobal(Offset.zero) & box.size;
  }

  /// Общая рамка нескольких помеченных мест; пропавшие не в счёт.
  static Rect? union(List<GlobalKey> keys) {
    Rect? all;
    for (final key in keys) {
      final one = rect(key);
      if (one == null) continue;
      all = all == null ? one : all.expandToInclude(one);
    }
    return all;
  }
}
