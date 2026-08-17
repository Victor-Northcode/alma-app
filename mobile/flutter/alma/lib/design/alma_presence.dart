import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'palette.dart';

/// Чем сейчас занят свет.
enum PresenceMood {
  /// Ждёт. Дыхание 5 секунд, лучей нет.
  calm,

  /// Думает: вокруг света кольцо лучей, дыхание учащается до 2.6 секунды.
  thinking,
}

/// Свет-присутствие Alma — **не аватар и не спиннер**.
///
/// Спека чата: «Alma — не печатающий бот, она свет, который дышит, и её
/// думание называет настоящий расчёт». Отсюда три вещи, каждая из которых
/// решение, а не оформление:
///
/// * **Дыхание идёт на своих часах** — 1 → 1.07 за пять секунд, ease-in-out.
///   Не на часах списка и не на часах ответа: свет живёт, пока человек читает,
///   и это единственное, чему закон движения («ничего не движется, пока читают
///   текст») разрешает шевелиться.
/// * **Думание — работа, а не ожидание.** Кольцо лучей вращается за девять
///   секунд: не фоновые семьдесят-двести, которыми в этом продукте крутятся
///   декорации, и не полсекунды спиннера. Девять — это темп человека, который
///   листает карту, и дыхание в это время учащается до 2.6 с.
/// * **Наклон на отправку.** В момент, когда вопрос ушёл, свет прибавляет
///   пятнадцать процентов яркости за 240 мс — тот же жест, что поворот головы
///   на голос. Это единственная реакция на действие; всё остальное свет делает
///   сам.
///
/// Размеры из спеки: 64 в приветствии, 26 в шапке ответа, 70 в думании (внутри
/// кольца 110).
class AlmaPresence extends StatefulWidget {
  const AlmaPresence({
    super.key,
    this.size = greeting,
    this.mood = PresenceMood.calm,
    this.tilt = 0,
  });

  /// Приветствие A1.
  static const greeting = 64.0;

  /// Шапка ответа A3 — тот же свет, уменьшенный до подписи.
  static const inHeader = 26.0;

  /// Думание A2.
  static const thinking = 70.0;

  /// Коробка кольца лучей вокруг думающего света.
  static const thinkingRing = 110.0;

  final double size;
  final PresenceMood mood;

  /// 0…1 — наклон на отправку вопроса: +15 % яркости.
  ///
  /// **Часы наклона снаружи, и это не мелочь.** Свет не знает, что вопрос
  /// ушёл, — знает экран; а главное, наклон обязан пережить смену состояния
  /// чата, в которую он и попадает (приветствие сменяется лентой ровно в тот
  /// кадр, в который вопрос уходит). Контроллер, заведённый здесь, умирал бы
  /// вместе с виджетом состояния — см. `_AlmaScreenState._presence`.
  final double tilt;

  @override
  State<AlmaPresence> createState() => _AlmaPresenceState();
}

class _AlmaPresenceState extends State<AlmaPresence>
    with TickerProviderStateMixin {
  /// Дыхание. Половина цикла: 5 с в покое, 2.6 с в думании.
  late final AnimationController _breath = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2500),
  );

  /// Оборот кольца лучей — девять секунд, линейно и без разворота.
  late final AnimationController _rays = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 9),
  );

  bool _still = false;

  @override
  void initState() {
    super.initState();
    // «Меньше движения» читается из окружения, а оно доступно только после
    // первого кадра. При включённом свет просто стоит: по спеке в reduced
    // motion дыхания нет вовсе, а состояния сменяются гашением.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      if (_still) return;
      _sync();
    });
  }

  @override
  void didUpdateWidget(AlmaPresence old) {
    super.didUpdateWidget(old);
    if (!_still && widget.mood != old.mood) _sync();
  }

  /// Часы под настроение. Дыхание не перезапускается с нуля — иначе смена
  /// состояния дёргала бы свет рывком в самый заметный момент.
  void _sync() {
    _breath.duration = Duration(
      milliseconds: widget.mood == PresenceMood.thinking ? 1300 : 2500,
    );
    if (!_breath.isAnimating) _breath.repeat(reverse: true);
    if (widget.mood == PresenceMood.thinking) {
      if (!_rays.isAnimating) _rays.repeat();
    } else {
      _rays.stop();
    }
  }

  @override
  void dispose() {
    _breath.dispose();
    _rays.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final thinking = widget.mood == PresenceMood.thinking;
    final box = thinking ? AlmaPresence.thinkingRing : widget.size;
    return SizedBox.square(
      dimension: box,
      child: Stack(
        alignment: Alignment.center,
        clipBehavior: Clip.none,
        children: [
          if (thinking && !_still)
            Positioned.fill(
              child: IgnorePointer(
                child: CustomPaint(painter: _Rays(_rays)),
              ),
            ),
          AnimatedBuilder(
            animation: _breath,
            builder: (context, child) {
              final t = _still
                  ? 0.0
                  : Curves.easeInOut.transform(_breath.value);
              return Transform.scale(
                // Спека: scale 1 → 1.07.
                scale: 1 + t * 0.07,
                child: Opacity(
                  // Наклон кладётся поверх дыхания и обрезается единицей:
                  // яркость выше сплошного света — это уже белое пятно.
                  opacity: math.min(1, (0.92 + t * 0.08) * (1 + widget.tilt * 0.15)),
                  child: child,
                ),
              );
            },
            // Свет несёт **свой** размер, а не берёт его у места в разметке:
            // `Stack` даёт нестеснённому ребёнку свободные границы, и голая
            // раскраска без ребёнка садится в них нулём — круг пропадал вовсе.
            child: SizedBox.square(
              dimension: widget.size,
              child: const DecoratedBox(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  // Радиальный глоу спеки, знак в знак:
                  // rgba(246,231,188,.9) 0 % → rgba(201,174,107,.4) 45 % →
                  // прозрачное 75 %.
                  gradient: RadialGradient(
                    radius: 0.5,
                    colors: [
                      Color(0xE6F6E7BC),
                      Color(0x66C9AE6B),
                      Color(0x00C9AE6B),
                    ],
                    stops: [0.0, 0.45, 0.75],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Кольцо лучей вокруг думающего света.
///
/// Порт `repeating-conic-gradient` эталона: луч 2.2°, шаг 8°, то есть сорок
/// пять лучей по кругу, и всё это в кольце между 46 % и 66 % радиуса коробки —
/// в самой кромке свечения, где оно уже почти прозрачно. Рисовальщиком, а не
/// градиентом: `SweepGradient` во Flutter не умеет повторяться, и сорок пять
/// пар стопов пришлось бы выписывать руками.
class _Rays extends CustomPainter {
  _Rays(this.clock) : super(repaint: clock);

  final Animation<double> clock;

  static const _step = 8 * math.pi / 180;
  static const _width = 2.2 * math.pi / 180;

  @override
  void paint(Canvas canvas, Size size) {
    final centre = size.center(Offset.zero);
    final r = size.shortestSide / 2;
    final inner = r * 0.46;
    final outer = r * 0.66;
    final turn = clock.value * 2 * math.pi;
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = outer - inner
      ..color = AlmaPalette.goldBright.withValues(alpha: 0.55);
    final rect = Rect.fromCircle(center: centre, radius: (inner + outer) / 2);
    for (var i = 0; i * _step < 2 * math.pi; i++) {
      canvas.drawArc(rect, turn + i * _step, _width, false, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _Rays old) => false;
}
