import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;

import 'palette.dart';
import 'typography.dart';

/// Барабан, которым в этом продукте называют число.
///
/// **Почему это общий компонент.** Барабанов в приложении два вида и они были
/// нарисованы по-разному: анкета (`journey_screen.dart`) — с полосой выбора,
/// лестницей яркости и засечными цифрами; лист совместимости — плоским
/// списком, где выбранная строка отличалась от соседней только прозрачностью
/// 0.45 против 1. Один и тот же человек называет дату рождения дважды — свою в
/// анкете и чужую в совместимости, — и второй раз она выглядела чужим
/// интерфейсом. Числа держатся вместе, иначе разъедутся снова.
///
/// Числа сняты с анкеты, то есть с эталона дизайн-проекта:
///
/// * окно **148** и **пять** строк в нём — `itemExtent 148/5 = 29.6`;
/// * полоса выбора **34**, кант сверху и снизу `rgba(201,174,107,.16)` —
///   вчетверо бледнее золотой волосяной линии: сначала читается цифра, потом
///   рамка;
/// * лестница яркости от центра **1 → .55 → .4** — именно она делает столбик
///   похожим на барабан, а не перспектива;
/// * цифра — **Playfair 19** (`AlmaType.displayL`): «позиция в этом дизайне
///   типографика, а не значок», и цифры продукта засечные везде;
/// * барабан почти плоский (`diameterRatio 2.4`, `perspective 0.002`): на
///   узкой колонке завал крайних строк читается сбоем вёрстки, а не объёмом.
///
/// **Правило анкеты «пока не тронули, ничего не выбрано» действует и здесь.**
///
/// Раньше в этом файле стояло обратное: ответ на листе даёт кнопка «Готово», а
/// не поворот, и заводить выключенную кнопку там, где человек уже постучал по
/// полю, незачем. Довод держался на том, что в полосе стоит осмысленное
/// умолчание, — а его там не было. Барабаны листа открывались на первой
/// строке, то есть на «1 января 1990», и «Готово», нажатое без прокрутки,
/// отправляло на сервер дату, которую никто не называл: ровно та ошибка, из-за
/// которой натив отказался от колеса вовсе: «`DatePicker` всегда имеет
/// значение, поэтому открывается на сегодня, и человек, пролиставший мимо,
/// молча сообщил, что родился сегодня утром» (`JourneyControls.swift:145`).
/// Заодно первая строка — это половина барабана, стоящая пустой: колонка из
/// пяти строк показывала три. Владелец снял оговорку 19.08.2026.
///
/// С тех пор своего колеса у анкеты нет — она зовёт это, тем же вызовом, что и
/// листы: правило переехало сюда целиком, а не было переписано во второй раз.
///
/// Отсюда два следствия, оба видны глазом:
///
/// * барабан без значения открывается **серединой списка** ([opensAt]), а не
///   первой строкой, — эталон нарисован полным, и полным он обязан быть с
///   первого кадра, до всякой прокрутки;
/// * невыбранный барабан весь на ступень тусклее (**.55 → .4 → .3**), полоса
///   выбора у него почти погашена, и [onChanged] он не зовёт вовсе. Значение
///   отдаёт палец: `dragDetails != null` отличает жест от программной
///   прокрутки, которой барабан доезжает сам — при появлении, при возврате на
///   шаг, при подстройке размеров.
///
/// Кнопку листа гасит тот, кто её ставит: барабан не знает, сколько колонок
/// должны быть названы, чтобы «Готово» загорелось.
class AlmaWheel extends StatefulWidget {
  const AlmaWheel({
    super.key,
    required this.label,
    required this.min,
    required this.max,
    required this.value,
    required this.onChanged,
    this.fallback,
    this.caption,
    this.showLabel = true,
  });

  /// Подпись колонки: «День», «Час». Прописные и разрядку ставит барабан.
  final String label;

  /// Рисуется ли подпись над барабаном. Голосу она остаётся всегда — гаснет
  /// только на экране, и только там, где то же слово уже стоит выше: над
  /// колёсами анкеты стоит вопрос шага, а над барабаном листа — его заголовок,
  /// то есть подпись пилюли, по которой постучали.
  final bool showLabel;

  final int min;
  final int max;

  /// Выбранное число или `null` — «не отвечал». Пустое состояние здесь
  /// законное: пилюля, которую открыл этот лист, тоже стоит плейсхолдером,
  /// пока значения нет.
  final int? value;

  /// На чём открыться, пока ничего не выбрано, если середина списка не годится.
  /// Году она не годится: середина 1900–2026 — это 1963, а середина взрослой
  /// жизни тридцать лет назад.
  final int? fallback;

  final ValueChanged<int> onChanged;

  /// Как печатается число. По умолчанию как есть; часам и минутам нужен ноль
  /// впереди — иначе колонка «0, 1, 2» стоит рядом с «10, 11, 12» и столбик
  /// выглядит рваным.
  final String Function(int)? caption;

  /// На чём барабан встанет, пока ничего не выбрано.
  ///
  /// Считается снаружи там, где от положения барабана зависит соседний: пока
  /// месяц не назван, в окне стоит его середина, и список дней обязан
  /// кончаться там же, где кончается видимый месяц, а не на выдуманном числе.
  static int opensAt(int min, int max, {int? fallback}) =>
      fallback != null && fallback >= min && fallback <= max
          ? fallback
          : min + (max - min + 1) ~/ 2;

  @override
  State<AlmaWheel> createState() => _AlmaWheelState();
}

class _AlmaWheelState extends State<AlmaWheel> {
  /// **Контроллер живёт в состоянии, а не в build.** Лист перестраивается на
  /// каждый поворот любого барабана (месяц меняет число дней), и контроллер,
  /// созданный в build, возвращал бы все три колонки на исходную строку при
  /// каждом движении пальца.
  late final FixedExtentScrollController _controller =
      FixedExtentScrollController(initialItem: _initial);

  /// Строка, с которой барабан открывается.
  int get _initial =>
      (widget.value ??
          AlmaWheel.opensAt(widget.min, widget.max,
              fallback: widget.fallback)) -
      widget.min;

  /// Какая строка сейчас в полосе. Лестница яркости считается от расстояния до
  /// неё, а не от значения: она описывает барабан, а не выбор.
  late int _centre = _initial;

  /// Барабан хоть раз тронули пальцем. До этого он ничего не отдаёт.
  bool _touched = false;

  bool get _chosen => widget.value != null;

  /// Высота строки. Пять строк в окне 148 — как в эталоне.
  static const _extent = 148 / 5;

  /// Полоса выбора: золото на 0.16. Ровно то же число, что у полосы анкеты, —
  /// и та же почти погашенная 0.06, пока значения нет.
  Color get _band =>
      _chosen ? const Color(0x29C9AE6B) : const Color(0x0FC9AE6B);

  @override
  void didUpdateWidget(AlmaWheel old) {
    super.didUpdateWidget(old);
    // Февраль после января: выбранный 31-й день перестал существовать, и
    // барабан обязан доехать до последнего настоящего, а не стоять за краем
    // укоротившегося списка. Сверяется положение самого барабана — значение
    // родитель уже подрезал, и по нему обрыв не виден.
    if (widget.max < old.max) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!_controller.hasClients) return;
        final last = widget.max - widget.min;
        if (_controller.selectedItem > last) _controller.jumpToItem(last);
      });
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  String _caption(int value) => widget.caption?.call(value) ?? '$value';

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: widget.label,
      value: widget.value == null ? '' : _caption(widget.value!),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        // Подпись — интерфейсная, значит Golos: `AlmaType.tag` 10.5 с
        // разрядкой 0.12em. Цвет приглушён до `muted3` (0.62) вместо золота
        // самого токена: над полосой выбора стоит золотой кант, и второе
        // золото в четырёх точках от него спорило бы с ним за взгляд.
        if (widget.showLabel) ...[
          Text(widget.label.toUpperCase(),
              style: AlmaType.tag.copyWith(color: AlmaPalette.muted3)),
          const SizedBox(height: 10),
        ],
        SizedBox(
          height: 148,
          child: Stack(alignment: Alignment.center, children: [
            Container(
              height: 34,
              decoration: BoxDecoration(
                border: Border(
                  top: BorderSide(color: _band),
                  bottom: BorderSide(color: _band),
                ),
              ),
            ),
            NotificationListener<ScrollNotification>(
              // `dragDetails != null` отличает жест от всего остального: у
              // прокрутки, начатой пальцем, они есть, у программной — нет.
              onNotification: (notification) {
                if (notification is ScrollStartNotification &&
                    notification.dragDetails != null) {
                  _touched = true;
                }
                return false;
              },
              child: ListWheelScrollView.useDelegate(
                controller: _controller,
                itemExtent: _extent,
                diameterRatio: 2.4,
                perspective: 0.002,
                physics: const FixedExtentScrollPhysics(),
                onSelectedItemChanged: (index) {
                  // Лестница яркости следует за видимой строкой всегда — она
                  // описывает барабан, а не выбор.
                  setState(() => _centre = index);
                  if (!_touched) return;
                  HapticFeedback.selectionClick();
                  widget.onChanged(widget.min + index);
                },
                childDelegate: ListWheelChildBuilderDelegate(
                  childCount: widget.max - widget.min + 1,
                  builder: (context, index) {
                    final away = (index - _centre).abs();
                    return Center(
                      child: Text(
                        _caption(widget.min + index),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AlmaType.displayL.copyWith(
                          fontSize: 19,
                          color: _chosen && away == 0
                              ? AlmaPalette.inkLight
                              : AlmaPalette.body.withValues(
                                  alpha: switch ((_chosen, away)) {
                                    (true, 1) => 0.55,
                                    (true, _) => 0.4,
                                    // Невыбранный барабан весь на ступень
                                    // тусклее: его центральная строка светит
                                    // ровно как соседка выбранного, и слоновой
                                    // кости в ней нет.
                                    (false, 0) => 0.55,
                                    (false, 1) => 0.4,
                                    (false, _) => 0.3,
                                  },
                                ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          ]),
        ),
      ]),
    );
  }
}
