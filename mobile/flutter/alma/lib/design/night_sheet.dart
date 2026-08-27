import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import 'palette.dart';
import 'typography.dart';

/// Лист, выезжающий снизу. Один на продукт.
///
/// **Почему рама живёт здесь, а не в экране, который её открыл.**
///
/// Листов в приложении уже два, и оба были написаны заново:
/// `pair_add_screen.dart` открывал выбор даты и времени, `people_screen.dart`
/// — выбор числа, и каждый звал `showModalBottomSheet` с единственной
/// настройкой `backgroundColor: AlmaPalette.night700`. Ночь `#101636` плоской
/// заливкой поверх неба читается системным диалогом, а не Alma; владелец
/// назвал это дословно — «просто синий экран». Третий лист, написанный тем же
/// способом, был вопросом времени, поэтому числа рамы стоят в одном месте.
///
/// **Числа не выдуманы: холст рисует шит ровно один раз — дверь V2**
/// (`docs/monetization/SCREENS-V3.md` §V2), и оттуда взято всё:
///
/// * радиус лба **28 28 0 0**;
/// * кант сверху `1px rgba(201,174,107,.3)` — золото на **0.30**;
/// * заливка `linear-gradient(180deg, rgba(13,17,32,.88), rgba(7,10,22,.97) 60%)`;
/// * `backdrop-filter: blur(14px)` — небо под листом остаётся небом, только
///   не в фокусе; это и есть глубина, которой не бывает у плоской заливки;
/// * внутреннее поле **30**: «шит физически меньше экрана, и внутри него своя
///   мера» — страничные 22 (`AlmaMetrics.pad`) сюда не приходят.
///
/// Единственное расхождение с холстом — цвет заливки. `rgba(13,17,32,·)` в
/// палитре продукта нет, а заводить `#0D1120` девятым оттенком ночи ради
/// одного градиента значило бы начать ту самую болезнь, против которой написан
/// `palette.dart`. Взяты соседние токены — [AlmaPalette.night] `#0A0D1C` на
/// 0.88 и [AlmaPalette.night900] `#070A16` на 0.97: расхождение три единицы на
/// канал, глазом неразличимо, новых цветов ноль.
class AlmaSheet extends StatelessWidget {
  const AlmaSheet({super.key, required this.title, required this.children});

  /// Имя того, что открыли. Сюда приходит подпись самой пилюли — лист не
  /// заводит собственных слов, он называет то, по чему постучали.
  final String title;

  final List<Widget> children;

  /// Радиус лба — V2.
  static const radius = 28.0;

  /// Внутреннее поле шита — V2. Шире страничного на восемь точек.
  static const _pad = 30.0;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      // Кант рисуется **поверх** заливки и только по лбу, как на V2.
      // `Border(top:)` внутри `BoxDecoration` провёл бы прямую поперёк
      // скруглённого верха и оборвался бы на плечах; `RoundedRectangleBorder`
      // с `side` обвёл бы заодно бока и низ, которых холст не рисует.
      foregroundPainter: _SheetBrow(),
      child: ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(radius)),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                // Токены ночной продающей поверхности — общие с карточкой
                // оффера (`AlmaGradient.nightCard`): одна семья одними числами.
                colors: [
                  AlmaPalette.nightCardTop,
                  AlmaPalette.nightCardBottom,
                  AlmaPalette.nightCardBottom,
                ],
                stops: const [0, 0.6, 1],
              ),
            ),
            // Дно листа — дно экрана; отступ снизу считает система, а не
            // вёрстка. На вкладке это ещё и высота бара: `Scaffold` с
            // `extendBody` кладёт её в нижний паддинг тела, и `SafeArea`
            // забирает её вместе с кромкой жеста.
            child: SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(_pad, 10, _pad, 18),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Хват — обещание жеста. Его цвет тот же, что у канта:
                    // золото 0.30 холста V2, а не серая палочка платформы.
                    Container(
                      width: 36,
                      height: 4,
                      decoration: BoxDecoration(
                        color: AlmaPalette.nightCardEdge,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                    const SizedBox(height: 14),
                    // Заголовок — Playfair 17.5/1.25 (`AlmaType.headingM`),
                    // ступень «заголовок строки или карточки»: лист меньше
                    // экрана, и `displayL` 29 в нём был бы вторым главным
                    // заголовком поверх первого.
                    Text(title,
                        textAlign: TextAlign.center, style: AlmaType.headingM),
                    const SizedBox(height: 18),
                    ...children,
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Золотой кант по лбу листа: `1px rgba(201,174,107,.3)` шита V2 и ни одной
/// линии сверх того.
///
/// Дуга уведена внутрь на пол-точки: линия рисуется по центру пути, и без
/// сдвига её внешняя половина легла бы за край листа.
class _SheetBrow extends CustomPainter {
  static const _inset = 0.5;

  @override
  void paint(Canvas canvas, Size size) {
    const r = AlmaSheet.radius;
    final path = Path()
      ..moveTo(_inset, r)
      ..arcToPoint(const Offset(r, _inset),
          radius: const Radius.circular(r - _inset))
      ..lineTo(size.width - r, _inset)
      ..arcToPoint(Offset(size.width - _inset, r),
          radius: const Radius.circular(r - _inset));
    canvas.drawPath(
      path,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = AlmaPalette.nightCardEdge,
    );
  }

  @override
  bool shouldRepaint(_SheetBrow old) => false;
}

/// Открыть [AlmaSheet] с содержимым, которое умеет перестраиваться.
///
/// [builder] получает `refresh` того же вида, что `setState`: барабаны листа
/// меняют друг друга (февраль укорачивает список дней), и перестраивать ради
/// этого весь экран под листом незачем.
///
/// **Оба привычных способа закрыть лист названы явно.** `isDismissible` — тап
/// по затемнению, `enableDrag` — свайп вниз. У `showModalBottomSheet` оба и так
/// по умолчанию `true`, но лист без выхода — это ловушка, и полагаться в таком
/// на умолчание чужой библиотеки нельзя: строка кода дешевле.
///
/// **Сокращённое движение соблюдается само и именно поэтому.** Свой
/// `AnimationController` здесь не заводится ни одного: приезд листа ведёт
/// контроллер маршрута, а он сверяется с `SemanticsBinding.disableAnimations` и
/// при «уменьшении движения» проигрывает путь в двадцать раз быстрее, то есть
/// мгновенно. Любая своя анимация в этой раме обязана спросить
/// `MediaQuery.disableAnimationsOf(context)` руками — сейчас спрашивать нечему.
Future<T?> showAlmaSheet<T>({
  required BuildContext context,
  required String title,
  required List<Widget> Function(
          BuildContext context, void Function(VoidCallback) refresh)
      builder,
}) {
  return showModalBottomSheet<T>(
    context: context,
    // Рама рисует себя сама: размытие, градиент и кант в один `BoxDecoration`
    // не складываются, и `Material` под ними обязан быть прозрачным.
    backgroundColor: Colors.transparent,
    elevation: 0,
    // Затемнение — самый глубокий тон продукта той же долей, какой продукт
    // приглушает текст (`muted3` = 0.62). Чёрного `black54` в палитре нет.
    barrierColor: AlmaPalette.voidDark.withValues(alpha: 0.62),
    isDismissible: true,
    enableDrag: true,
    // Высота листа — его содержимое, а не 9/16 экрана: на крупном шрифте
    // барабаны с кнопкой в долю не помещаются.
    isScrollControlled: true,
    // Верх — под строкой состояния, низ остаётся дном экрана.
    useSafeArea: true,
    builder: (context) => StatefulBuilder(
      builder: (context, refresh) =>
          AlmaSheet(title: title, children: builder(context, refresh)),
    ),
  );
}
