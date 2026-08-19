import 'package:flutter/material.dart';

import '../../design/buttons.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import 'coach_anchors.dart';

/// Куда обучалка ведёт человека на каждом шаге. Оболочка знает, что такое
/// вкладка; обучалка — только то, о чём она сейчас рассказывает.
enum CoachStop { systems, today }

/// Маленькая проводка по кабинету: два шага и ни одного лишнего.
///
/// **Это накладка над живым продуктом, а не слайд-шоу о нём.** Затемнение с
/// вырезом лежит поверх настоящих «Моих систем» и настоящего «Сегодня»: человек
/// смотрит на свои восемь карт и на свою страницу дня, а не на картинку, где
/// они нарисованы. Отсюда и всё устройство — маршрут поверх кабинета, а не
/// экран вместо него: вкладки под ним продолжают жить, их вёрстка не тронута ни
/// строкой, и выключить проводку значит просто снять маршрут.
///
/// **Два шага, и это потолок.** Владелец просил «маленькую» и оставил за собой
/// право выключить; третий шаг превратил бы её в то, что выключают не глядя.
///
/// **Закрывается с первого раза.** Тап по затемнению, крестик, «понятно» — три
/// двери, ни одного переспрашивания. Обучалка, которая уточняет «точно
/// уверены?», стоит дороже той пользы, ради которой её показали.
Future<void> showCoachMarks(
  BuildContext context, {
  required void Function(CoachStop) goTo,
}) {
  return Navigator.of(context, rootNavigator: true).push(
    PageRouteBuilder<void>(
      // Кабинет под накладкой обязан **остаться нарисованным**: в этом вся
      // затея. Непрозрачный маршрут снял бы его с экрана, и подсвечивать стало
      // бы нечего.
      opaque: false,
      // Затемнение рисуем сами: у него вырез, а барьер маршрута — сплошной
      // прямоугольник и ничего больше.
      barrierColor: null,
      barrierDismissible: false,
      // Появление и уход держит сама накладка — ей одной известно, уважает ли
      // человек «Сокращённое движение».
      transitionDuration: Duration.zero,
      reverseTransitionDuration: Duration.zero,
      pageBuilder: (context, _, _) => CoachMarks(goTo: goTo),
    ),
  );
}

class CoachMarks extends StatefulWidget {
  const CoachMarks({super.key, required this.goTo});

  /// Довезти кабинет до вкладки, о которой пойдёт речь. Ответ на «как» —
  /// у оболочки: она одна знает про `PageView` и его контроллер.
  final void Function(CoachStop) goTo;

  @override
  State<CoachMarks> createState() => _CoachMarksState();
}

class _CoachMarksState extends State<CoachMarks> {
  static const _stops = <CoachStop>[CoachStop.systems, CoachStop.today];

  /// Сколько ждать, пока страница вкладки доедет. Оболочка везёт её за 320 мс
  /// (`_CabinetShellState._goTo`), и мерить положение карты посреди этого
  /// движения значило бы вырезать дыру там, где элемента уже нет.
  ///
  /// Полтораста миллисекунд запаса сверх переезда — не осторожность на глаз:
  /// движение начинается на **следующем** кадре после `goTo`, и мерка,
  /// назначенная впритык, застаёт страницу в десятке точек от места. Поймано в
  /// пробирке: вырез на «Сегодня» выходил сдвинутым на 9,6 точки влево.
  static const _settle = Duration(milliseconds: 520);

  /// Второй заход, если с первого мерить было нечего. Панель дня строится по
  /// ответу сервера, а колода — по хабу: у человека, у которого сеть медленнее
  /// анкеты, к первому кадру кабинета может не быть ни того, ни другого.
  static const _retry = Duration(milliseconds: 420);

  /// Воздух вокруг подсвеченного места и между вырезом и карточкой.
  static const _halo = 8.0;
  static const _gap = 18.0;

  /// Потолок высоты выреза — доля экрана.
  ///
  /// **Подсветка размером в экран это не подсветка, а рамка.** Панель дня на
  /// бесплатном «Сегодня» высокая — заметка, а под ней три блока живого слоя, —
  /// и честный вырез по её краям съедал 595 точек из 874: карточке не
  /// оставалось места ни сверху, ни снизу, и она уезжала за нижнюю кромку.
  /// Обрезаем снизу, а не сверху: разговор идёт про заметку дня, и она стоит в
  /// голове панели.
  ///
  /// Сорок сотых, а не сорок пять: на кадре 402×874 сорок пять оставляли под
  /// вырезом 239 точек при нужных 240, и карточка съезжала в запасное положение
  /// у нижней кромки, наползая на панель. Одной точки не должно решать ничего —
  /// поэтому запас, а не подгонка порога.
  static const _holeShare = 0.40;

  /// Сколько нужно карточке, чтобы встать целиком. Меньше — она прижимается к
  /// нижней кромке и слегка накрывает вырез; лучше так, чем половина карточки
  /// за краем экрана.
  static const _cardRoom = 240.0;

  int _step = 0;
  Rect? _hole;

  /// Страница доехала и место измерено — карточку можно показывать. До этого на
  /// экране одно затемнение: карточка, приехавшая раньше вкладки, о которой
  /// говорит, читается как подпись не к той картинке.
  bool _settled = false;

  /// Уходим. Три двери ведут в один `pop`, и второй тап по закрывающейся
  /// накладке не должен снимать заодно и кабинет.
  bool _leaving = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _enter(0));
  }

  Future<void> _enter(int step) async {
    setState(() {
      _step = step;
      _hole = null;
      _settled = false;
    });
    widget.goTo(_stops[step]);
    await Future<void>.delayed(_settle);
    if (!mounted) return;
    var hole = _measure(_stops[step]);
    if (hole == null) {
      await Future<void>.delayed(_retry);
      if (!mounted) return;
      hole = _measure(_stops[step]);
    }
    if (!mounted) return;
    setState(() {
      _hole = hole;
      _settled = true;
    });
  }

  Rect? _measure(CoachStop stop) {
    final found = switch (stop) {
      // Счётчик и первый ряд вместе: рамка вокруг них накрывает и заголовок
      // экрана, который стоит на той же строке, что счётчик. Получается один
      // вырез на всю верхушку «Моих систем» — там, где сказано «восемь» и
      // где эти восемь начинаются.
      CoachStop.systems => CoachAnchors.union(
          [CoachAnchors.systemsTally, CoachAnchors.systemsFirstRow]),
      CoachStop.today => CoachAnchors.rect(CoachAnchors.todayPanel),
    };
    if (found == null) return null;
    // Ореол вокруг элемента и обрезка по экрану: вырез, уехавший за кромку,
    // рисует затемнение с прорехой у края.
    final size = MediaQuery.sizeOf(context);
    final top = (found.top - _halo).clamp(0.0, size.height);
    return Rect.fromLTRB(
      (found.left - _halo).clamp(0.0, size.width),
      top,
      (found.right + _halo).clamp(0.0, size.width),
      (found.bottom + _halo)
          .clamp(0.0, size.height)
          .clamp(top, top + size.height * _holeShare),
    );
  }

  void _close() {
    if (_leaving) return;
    _leaving = true;
    Navigator.of(context).pop();
  }

  void _next() {
    if (_step + 1 < _stops.length) {
      _enter(_step + 1);
    } else {
      _close();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    // «Сокращённое движение» — тогда просто появление: ни проявления, ни
    // подъёма карточки. Тем же вызовом, что и весь остальной приход экранов
    // (`RiseIn`), чтобы правило было одно на продукт.
    final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    final last = _step == _stops.length - 1;

    return Material(
      // Накладка живёт в корневом `Overlay`, а не под `Scaffold`: без
      // собственного холста у текста не было бы ни направления, ни стиля по
      // умолчанию. Прозрачный — рисуем мы сами.
      type: MaterialType.transparency,
      child: Stack(
        children: [
          // Затемнение с вырезом. Тап по нему — первая из трёх дверей наружу;
          // тап внутрь выреза закрывает так же, и это решение: человек,
          // ткнувший в подсвеченную карту, хотел открыть её, а не читать про
          // неё дальше.
          Positioned.fill(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: _close,
              child: TweenAnimationBuilder<double>(
                tween: Tween<double>(begin: 0, end: 1),
                duration: still ? Duration.zero : AlmaMotion.sheet,
                curve: AlmaMotion.sheetCurve,
                builder: (context, shown, child) =>
                    Opacity(opacity: shown, child: child),
                child: CustomPaint(painter: _Scrim(hole: _hole)),
              ),
            ),
          ),
          if (_settled) _card(context, l, last, still),
        ],
      ),
    );
  }

  /// Карточка: где встать — решает вырез.
  ///
  /// Ниже подсвеченного места, если под ним есть куда встать, иначе выше.
  /// Выреза нет вовсе — по центру: так выглядит честный запасной случай, когда
  /// подсвечивать оказалось нечего.
  Widget _card(BuildContext context, L l, bool last, bool still) {
    final size = MediaQuery.sizeOf(context);
    final safe = MediaQuery.paddingOf(context);
    final hole = _hole;
    final card = _CoachCard(
      key: ValueKey(_step),
      step: _step,
      steps: _stops.length,
      title: _title(l),
      body: _body(l),
      cta: last ? l.onbDone : l.onbNext,
      closeLabel: l.onbClose,
      still: still,
      onNext: _next,
      onClose: _close,
    );

    if (hole == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
          child: card,
        ),
      );
    }

    final below = size.height - safe.bottom - hole.bottom - _gap;
    final above = hole.top - safe.top - _gap;
    if (below >= above && below >= _cardRoom) {
      return Positioned(
        left: AlmaMetrics.pad,
        right: AlmaMetrics.pad,
        top: hole.bottom + _gap,
        child: card,
      );
    }
    if (above > below && above >= _cardRoom) {
      return Positioned(
        left: AlmaMetrics.pad,
        right: AlmaMetrics.pad,
        bottom: size.height - hole.top + _gap,
        child: card,
      );
    }
    // Ни сверху, ни снизу не помещается — крупный кегль системы, маленький
    // экран. Прижимаемся к нижней кромке: карточка, наехавшая на вырез, читается
    // хуже, чем карточка, у которой видна половина, — но она хотя бы вся видна.
    return Positioned(
      left: AlmaMetrics.pad,
      right: AlmaMetrics.pad,
      bottom: safe.bottom + _gap,
      child: card,
    );
  }

  String _title(L l) => switch (_stops[_step]) {
        CoachStop.systems => l.onbSystemsTitle,
        CoachStop.today => l.onbTodayTitle,
      };

  String _body(L l) => switch (_stops[_step]) {
        CoachStop.systems => l.onbSystemsBody,
        CoachStop.today => l.onbTodayBody,
      };
}

/// Карточка проводки: точки шагов, крестик, заголовок, подпись, одна кнопка.
///
/// Ночь и золото продукта, ни одного нового цвета: тело — `night700`, кант —
/// волосяная золотая линия, заголовок засечным (Playfair `headingM`), подпись
/// текстовым (Golos `meta`). Кнопка — обводка из общего набора: золотая на этом
/// месте была бы вторым главным действием на экране, у которого главное
/// действие — сам продукт под затемнением.
class _CoachCard extends StatelessWidget {
  const _CoachCard({
    super.key,
    required this.step,
    required this.steps,
    required this.title,
    required this.body,
    required this.cta,
    required this.closeLabel,
    required this.still,
    required this.onNext,
    required this.onClose,
  });

  final int step;
  final int steps;
  final String title;
  final String body;
  final String cta;
  final String closeLabel;
  final bool still;
  final VoidCallback onNext;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    final card = Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 18),
      decoration: BoxDecoration(
        // Градиент, а не заливка: плоский прямоугольник одного тона на этом
        // экране читается плашкой, положенной поверх продукта. Панели «Сегодня»
        // собраны тем же способом — тон сверху, глубже книзу, — и карточка
        // проводки должна принадлежать той же семье.
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [AlmaPalette.night700, AlmaPalette.night900],
        ),
        borderRadius: BorderRadius.circular(AlmaPalette.buttonRadius),
        border: Border.all(color: AlmaPalette.hairlineGold),
        boxShadow: [
          BoxShadow(
            color: AlmaPalette.voidDark.withValues(alpha: 0.55),
            blurRadius: 30,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(children: [
            // Счёт шагов точками, а не «1 из 2»: два слова о том, сколько
            // осталось терпеть, — это уже размер, которого у маленькой вещи не
            // должно быть. И переводить нечего.
            for (var i = 0; i < steps; i++)
              Container(
                width: 5,
                height: 5,
                margin: const EdgeInsets.only(right: 6),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: i == step
                      ? AlmaPalette.goldBright
                      : AlmaPalette.gold.withValues(alpha: 0.3),
                ),
              ),
            const Spacer(),
            Semantics(
              button: true,
              label: closeLabel,
              child: GestureDetector(
                onTap: onClose,
                behavior: HitTestBehavior.opaque,
                // Крестик мелкий, а место под пальцем — нет: 40 точек, как у
                // всякой кнопки, до которой дотягиваются, не целясь.
                child: SizedBox(
                  width: 40,
                  height: 30,
                  child: Align(
                    alignment: Alignment.centerRight,
                    child: Text(
                      '✕',
                      style: AlmaType.meta.copyWith(
                        fontSize: 15,
                        color: AlmaPalette.gold.withValues(alpha: 0.7),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ]),
          const SizedBox(height: 6),
          Text(title, style: AlmaType.headingM),
          const SizedBox(height: 8),
          Text(body, style: AlmaType.meta),
          const SizedBox(height: 16),
          AlmaButton(
            kind: AlmaButtonKind.outline,
            fills: false,
            label: cta,
            onTap: onNext,
          ),
        ],
      ),
    );

    if (still) return card;
    // Появление: проявление с подъёмом на те же 16 точек, которыми на этом
    // продукте приходит всё остальное (`AlmaArrive.rise`).
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0, end: 1),
      duration: AlmaMotion.ui,
      curve: AlmaMotion.uiCurve,
      builder: (context, shown, child) => Opacity(
        opacity: shown,
        child: Transform.translate(
          offset: Offset(0, 16 * (1 - shown)),
          child: child,
        ),
      ),
      child: card,
    );
  }
}

/// Ночь поверх кабинета с одним вырезом.
class _Scrim extends CustomPainter {
  const _Scrim({required this.hole});

  final Rect? hole;

  /// Скругление выреза. На точку больше карты колоды (13), чтобы ореол шёл
  /// вокруг её угла, а не срезал его.
  static const _radius = Radius.circular(14);

  @override
  void paint(Canvas canvas, Size size) {
    final full = Offset.zero & size;
    // Не чёрный: `voidDark` — самый глубокий тон продукта, и ночь под
    // затемнением обязана остаться той же ночью.
    final ink = Paint()..color = AlmaPalette.voidDark.withValues(alpha: 0.86);
    final rect = hole;
    if (rect == null) {
      canvas.drawRect(full, ink);
      return;
    }
    final rounded = RRect.fromRectAndRadius(rect, _radius);
    canvas.drawPath(
      Path.combine(
        PathOperation.difference,
        Path()..addRect(full),
        Path()..addRRect(rounded),
      ),
      ink,
    );
    // Золотое свечение снаружи выреза и волосяная линия по самому краю: без
    // них дыра в затемнении читается как непрокрасившийся кусок экрана.
    canvas.drawRRect(
      rounded,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = AlmaPalette.gold.withValues(alpha: 0.34)
        ..maskFilter = const MaskFilter.blur(BlurStyle.outer, 6),
    );
    canvas.drawRRect(
      rounded,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = AlmaPalette.gold.withValues(alpha: 0.28),
    );
  }

  @override
  bool shouldRepaint(covariant _Scrim old) => old.hole != hole;
}
