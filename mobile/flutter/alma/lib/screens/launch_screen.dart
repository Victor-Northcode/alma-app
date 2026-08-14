import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../design/palette.dart';
import '../design/sky/night_sky.dart';
import '../design/typography.dart';
import '../l10n/alma_l10n.dart';

/// Первые секунды приложения: небо, соединяющее само себя.
///
/// Порт `mobile/ios/Alma/Screens/AlmaLaunch.swift`. До него порт открывался
/// подменой готового экрана за один кадр — против сервера на той же машине это
/// длилось десятки миллисекунд и читалось как мигание.
///
/// **Один источник времени и одна кривая.** Все семь движений выведены из
/// одних часов через `_eased(from, to)` — ease-out cubic, — и это то, что
/// делает пять разных вещей одним жестом. Линейное нарастание читалось бы как
/// полоса загрузки.
///
/// **Уход требует двух условий сразу**: сессия готова И прошло положенное
/// время. На нативе первая версия читала «готово» из замыкания, захватившего
/// значение на момент создания задачи, — заставка не уходила вовсе. Здесь
/// решение принимается снаружи, в [_settle], на каждое изменение обоих.
///
/// **Знак не вращается и никогда не служит индикатором загрузки** — это тот
/// самый штамп, ради ухода от которого он рисовался. Роль индикатора несут
/// дышащая точка и волосяная линия, заполняющаяся за время показа.
class LaunchScreen extends StatefulWidget {
  const LaunchScreen({super.key, required this.ready, required this.onDone});

  /// Знает ли уже приложение, кто перед ним.
  final bool ready;

  final VoidCallback onDone;

  @override
  State<LaunchScreen> createState() => _LaunchScreenState();
}

class _LaunchScreenState extends State<LaunchScreen>
    with SingleTickerProviderStateMixin {
  /// 3,4 секунды — число с натива, и оно выросло с 2,8 не ради скорости: там
  /// чинили плотность, а не длительность.
  static const _runtime = 3.4;

  late final AnimationController _clock = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: (_runtime * 1000) ~/ 1),
  )..forward();

  bool _dwelt = false;
  bool _handedOver = false;

  @override
  void initState() {
    super.initState();
    _clock.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        _dwelt = true;
        _settle();
      }
    });
  }

  @override
  void didUpdateWidget(LaunchScreen old) {
    super.didUpdateWidget(old);
    if (widget.ready != old.ready) _settle();
  }

  @override
  void dispose() {
    _clock.dispose();
    super.dispose();
  }

  void _settle() {
    if (_handedOver || !_dwelt || !widget.ready) return;
    _handedOver = true;
    widget.onDone();
  }

  /// 0 → 1 между двумя моментами, по ease-out cubic.
  double _eased(double from, double to, double t) {
    final raw = ((t - from) / (to - from)).clamp(0.0, 1.0);
    return 1 - math.pow(1 - raw, 3).toDouble();
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    // Сокращённое движение — не «пропустить заставку»: убрать её целиком
    // значило бы вернуть ту самую вспышку, ради которой она написана.
    // Рисуется тот же кадр, взятый в конце.
    final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    // **Своя material-поверхность.** Без неё Flutter рисует «ALMA» жёлтой с
    // двойным подчёркиванием — тот же артефакт, что был на витрине: экран
    // возвращается из `home` напрямую и `Scaffold` над собой не имеет.
    return Semantics(
      label: l.stateLoadingShort,
      child: Material(
        color: AlmaPalette.night,
        child: AnimatedBuilder(
          animation: _clock,
          builder: (context, _) {
            final t = still ? _runtime : _clock.value * _runtime;
            final fold = _eased(1.90, 2.65, t);
            final bloom = _eased(2.05, 2.85, t);
            final word = _eased(2.35, 3.05, t);
            return Stack(
              alignment: Alignment.center,
              children: [
                // Небо — **сиблингом, а не фоном**: здесь приходящее небо и
                // есть содержимое, а фон невозможно увидеть проявляющимся.
                Opacity(
                  opacity: still ? 1 : _eased(0, 0.9, t),
                  // Режим церемонии, и не ради яркости: у кабинетного неба
                  // своя комета, а две одновременно читаются как погода.
                  child: const NightSky(
                    mood: SkyMood.ceremony,
                    seed: 0x414C4D41,
                    child: SizedBox.expand(),
                  ),
                ),
                Opacity(
                  opacity: (1 - fold * 0.97).clamp(0.0, 1.0),
                  child: Transform.scale(
                    // Карта не просто гаснет, а стягивается: её втягивают в
                    // знак, а форма, которая только тускнеет, выглядит
                    // брошенной, а не разрешившейся.
                    scale: 1.04 - _eased(0, 0.9, t) * 0.04 - fold * 0.10,
                    child: SizedBox(
                      width: 300,
                      height: 300,
                      child: CustomPaint(
                        painter: _StarChart(
                          lines: _eased(0.35, 1.95, t),
                          nodes: _eased(0.25, 1.80, t),
                          comet: _eased(1.20, 2.20, t),
                          cometTwo: _eased(1.65, 2.60, t),
                          time: t,
                        ),
                      ),
                    ),
                  ),
                ),
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Opacity(
                      opacity: bloom,
                      child: Transform.scale(
                        scale: 0.72 + bloom * 0.28,
                        child: SizedBox(
                          width: 46,
                          height: 46,
                          child: CustomPaint(painter: _Mark(bloom: bloom)),
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    Opacity(
                      opacity: word,
                      child: Transform.translate(
                        offset: Offset(0, (1 - word) * 7),
                        child: Text(
                          'ALMA',
                          style: AlmaType.meta.copyWith(
                            fontSize: 15,
                            color: AlmaPalette.parchment.withValues(alpha: 0.9),
                            // Буквы оседают: разрядка закрывается с
                            // рассыпанной до набранной — шрифт приходит, а не
                            // появляется.
                            letterSpacing: 7 + (1 - word) * 9,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 30),
                    // Самая тихая полоса прогресса, какая бывает: одна золотая
                    // волосяная линия, без рамки и без процентов.
                    Opacity(
                      opacity: _eased(0.55, 1.20, t),
                      child: SizedBox(
                        width: 84,
                        height: 1,
                        child: Stack(alignment: Alignment.centerLeft, children: [
                          ColoredBox(
                            color: AlmaPalette.gold.withValues(alpha: 0.16),
                            child: const SizedBox(width: 84, height: 1),
                          ),
                          ColoredBox(
                            color:
                                AlmaPalette.goldBright.withValues(alpha: 0.75),
                            child: SizedBox(
                                width: 84 * (t / _runtime).clamp(0.0, 1.0),
                                height: 1),
                          ),
                        ]),
                      ),
                    ),
                  ],
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

/// Небо, соединяющее себя: девять узлов, три ветви линий и две кометы.
///
/// Ни циферблата, ни кольца вокруг — решение владельца: приход это небо,
/// которое связывает само себя, и ничего нарисованного вокруг.
class _StarChart extends CustomPainter {
  _StarChart({
    required this.lines,
    required this.nodes,
    required this.comet,
    required this.cometTwo,
    required this.time,
  });

  final double lines;
  final double nodes;
  final double comet;
  final double cometTwo;
  final double time;

  static const _points = [
    (48.0, 196.0, 3.2), (104.0, 118.0, 4.6), (168.0, 152.0, 3.0),
    (214.0, 58.0, 5.2), (268.0, 104.0, 3.4), (132.0, 224.0, 3.8),
    (76.0, 64.0, 2.6), (232.0, 186.0, 3.0), (176.0, 250.0, 2.4),
  ];

  static const _spine = [
    Offset(48, 196), Offset(104, 118), Offset(168, 152),
    Offset(214, 58), Offset(268, 104),
  ];
  static const _branch = [Offset(104, 118), Offset(132, 224), Offset(214, 58)];
  static const _branchTwo = [
    [Offset(76, 64), Offset(104, 118)],
    [Offset(232, 186), Offset(268, 104)],
    [Offset(132, 224), Offset(176, 250)],
  ];

  /// Ломаная, прочерченная на долю [progress] от своей длины.
  void _drawTrimmed(Canvas canvas, List<Offset> path, double progress, Paint paint) {
    if (progress <= 0) return;
    final lengths = [
      for (var i = 1; i < path.length; i++) (path[i] - path[i - 1]).distance,
    ];
    final total = lengths.fold<double>(0, (a, b) => a + b);
    var left = total * progress.clamp(0.0, 1.0);
    for (var i = 1; i < path.length; i++) {
      final segment = lengths[i - 1];
      if (left <= 0) return;
      final part = (left / segment).clamp(0.0, 1.0);
      canvas.drawLine(
        path[i - 1],
        Offset.lerp(path[i - 1], path[i], part)!,
        paint,
      );
      left -= segment;
    }
  }

  @override
  void paint(Canvas canvas, Size size) {
    final stroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..strokeCap = StrokeCap.round;

    _drawTrimmed(canvas, _spine, lines,
        stroke..color = AlmaPalette.gold.withValues(alpha: 0.5));
    _drawTrimmed(canvas, _branch, (lines * 1.3 - 0.3).clamp(0.0, 1.0),
        stroke..color = AlmaPalette.gold.withValues(alpha: 0.24));
    for (final pair in _branchTwo) {
      _drawTrimmed(canvas, pair, (lines * 1.5 - 0.5).clamp(0.0, 1.0),
          stroke..color = AlmaPalette.gold.withValues(alpha: 0.18));
    }

    for (var i = 0; i < _points.length; i++) {
      final share = i / _points.length;
      final lit = ((nodes - share * 0.55) / 0.45).clamp(0.0, 1.0);
      if (lit <= 0) continue;
      // Мерцание: каждая звезда дышит на своём такте, и собранная карта
      // выглядит живой, а не напечатанной.
      final breathe =
          0.75 + 0.25 * math.sin(time * (1.1 + (i % 4) * 0.4) + i * 2);
      final (x, y, r) = _points[i];
      final centre = Offset(x, y);
      canvas.drawCircle(
        centre,
        r * (0.4 + lit * 0.6) * breathe,
        Paint()
          ..color = AlmaPalette.starFill.withValues(alpha: lit)
          ..maskFilter = MaskFilter.blur(BlurStyle.solid, 6 * breathe * 0.35),
      );
    }

    // Кольцо вокруг самого яркого узла — оттуда и распускается знак.
    if (nodes > 0) {
      canvas.drawCircle(
        const Offset(214, 58),
        (30 + (1 - nodes) * 14) / 2,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = AlmaPalette.goldBright.withValues(alpha: 0.22 * nodes),
      );
    }

    _comet(canvas, comet, 90, 28, const Offset(-40, 250), const Offset(340, 40));
    _comet(canvas, cometTwo, 64, -16, const Offset(330, 210), const Offset(-30, 120));
  }

  void _comet(Canvas canvas, double phase, double width, double angle,
      Offset from, Offset to) {
    if (phase <= 0 || phase >= 1) return;
    final centre = Offset.lerp(from, to, phase)!;
    canvas.save();
    canvas.translate(centre.dx, centre.dy);
    canvas.rotate(angle * math.pi / 180);
    final rect = Rect.fromCenter(center: Offset.zero, width: width, height: 1.2);
    canvas.drawRect(
      rect,
      Paint()
        ..shader = LinearGradient(colors: [
          const Color(0x00000000),
          AlmaPalette.starFill.withValues(alpha: 0.75 * math.sin(phase * math.pi)),
          const Color(0x00000000),
        ]).createShader(rect),
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _StarChart old) =>
      old.lines != lines || old.nodes != nodes || old.time != time;
}

/// Знак Alma — четырёхлучевая звезда, распускающаяся из ярчайшего узла, и
/// шесть искр, поднятых ею.
class _Mark extends CustomPainter {
  _Mark({required this.bloom});

  final double bloom;

  static const _motes = [-26.0, 18.0, -12.0, 30.0, -34.0, 8.0];

  @override
  void paint(Canvas canvas, Size size) {
    for (var i = 0; i < _motes.length; i++) {
      final phase = (bloom * 1.4 - i * 0.12).clamp(0.0, 1.0);
      if (phase <= 0 || phase >= 1) continue;
      canvas.drawCircle(
        Offset(size.width / 2 + _motes[i], size.height / 2 + 34 - phase * 74),
        1.25,
        Paint()
          ..color = AlmaPalette.goldBright
              .withValues(alpha: 0.7 * phase * (1 - phase) * 4 * 0.35),
      );
    }

    // Сама звезда: четыре луча, сходящиеся в точку, залитые золотым листом.
    final c = Offset(size.width / 2, size.height / 2);
    final r = size.width * 0.5;
    final path = Path();
    for (var i = 0; i < 4; i++) {
      final angle = i * math.pi / 2;
      final tip = c + Offset(math.cos(angle) * r, math.sin(angle) * r);
      final left = c +
          Offset(math.cos(angle + math.pi / 4), math.sin(angle + math.pi / 4)) *
              (r * 0.19);
      if (i == 0) {
        path.moveTo(tip.dx, tip.dy);
      } else {
        path.lineTo(tip.dx, tip.dy);
      }
      path.lineTo(left.dx, left.dy);
    }
    path.close();
    canvas.drawPath(
      path,
      Paint()
        ..shader = AlmaGradient.goldLeaf.createShader(
            Rect.fromCircle(center: c, radius: r)),
    );
  }

  @override
  bool shouldRepaint(covariant _Mark old) => old.bloom != bloom;
}
