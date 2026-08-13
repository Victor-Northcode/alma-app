import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../design/palette.dart';
import '../../design/self_drawing.dart' show phase;

/// Что человек видит те сорок-девяносто секунд, пока глава пишется.
///
/// Порт `WritingArt.swift`. На нативе ожидание — не строка «подождите», а
/// рисунок, который собирает себя: две орбиты, засечки по кругу и точки,
/// зажигающиеся одна за другой, — и он идёт по кругу, пока текст не пришёл.
/// В порте на этом месте стояла одна строка мелким шрифтом, и минута ожидания
/// выглядела зависанием.
///
/// Рисунок ничего не утверждает о карте: это не диаграмма, а ожидание, и
/// поэтому у него нет данных на входе. Диаграммы систем — отдельная работа и
/// читают свои payload'ы.
class WritingArt extends StatelessWidget {
  const WritingArt({super.key, this.size = 260, this.seed = 0});

  final double size;

  /// Чей это рисунок. Каждая система ждёт по-своему: у одной орбит две, у
  /// другой пять, точки садятся в своём порядке и своей крупности. На нативе
  /// у каждой из восьми систем своя анимация письма, и порт держит то же
  /// правило — иначе восемь ожиданий выглядят одним.
  final int seed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: _Forever(size: size, seed: seed),
    );
  }
}

class _WritingPainter extends CustomPainter {
  _WritingPainter(this.progress, this.seed);

  final double progress;
  final int seed;

  @override
  void paint(Canvas canvas, Size size) {
    final centre = Offset(size.width / 2, size.height / 2);
    final outer = size.width * 0.42;
    final inner = size.width * 0.27;

    // Две орбиты замыкаются первыми, одна за другой.
    // Число орбит и их радиусы — от системы: две у одной, четыре у другой.
    final rings = 2 + seed % 3;
    for (var r = 0; r < rings; r++) {
      final radius = outer - (outer - inner) * r / (rings - 1).clamp(1, 9);
      final from = 0.05 * r;
      final to = 0.45 + 0.05 * r;
      final swept = phase(progress, from, to);
      if (swept <= 0) continue;
      canvas.drawArc(
        Rect.fromCircle(center: centre, radius: radius),
        -math.pi / 2,
        2 * math.pi * swept,
        false,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = AlmaPalette.gold.withValues(alpha: 0.45),
      );
    }

    // Засечки по внешнему краю — минуты на циферблате неба.
    final ticks = 24 + (seed % 4) * 12;
    for (var i = 0; i < ticks; i++) {
      final lit = phase(progress, 0.25 + i * 0.006, 0.5 + i * 0.006);
      if (lit <= 0) continue;
      final a = i * 2 * math.pi / ticks - math.pi / 2;
      final r1 = outer * 1.09;
      final r2 = r1 + (i % 4 == 0 ? 7 : 4);
      canvas.drawLine(
        centre + Offset(math.cos(a) * r1, math.sin(a) * r1),
        centre + Offset(math.cos(a) * r2, math.sin(a) * r2),
        Paint()
          ..strokeWidth = 1
          ..color = AlmaPalette.gold.withValues(alpha: 0.3 * lit),
      );
    }

    // Точки на орбитах и нити между соседними — созвездие, которое строится.
    // Свои места у точек: сдвиг по кругу зависит от системы.
    final shift = (seed % 7) / 7;
    final seats = [0.08, 0.2, 0.34, 0.52, 0.63, 0.78, 0.9]
        .map((f) => (f + shift) % 1.0)
        .toList();
    Offset seat(int i) {
      final a = seats[i] * 2 * math.pi - math.pi / 2;
      final r = i.isEven ? outer : inner;
      return centre + Offset(math.cos(a) * r, math.sin(a) * r);
    }

    for (var i = 0; i < seats.length; i++) {
      final lit = phase(progress, 0.45 + i * 0.05, 0.7 + i * 0.05);
      if (lit <= 0) continue;
      if (i > 0) {
        final drawn = phase(progress, 0.5 + i * 0.05, 0.75 + i * 0.05);
        if (drawn > 0) {
          final a = seat(i - 1);
          final b = seat(i);
          canvas.drawLine(
            a,
            Offset(a.dx + (b.dx - a.dx) * drawn, a.dy + (b.dy - a.dy) * drawn),
            Paint()
              ..strokeWidth = 1
              ..color = AlmaPalette.gold.withValues(alpha: 0.35),
          );
        }
      }
      canvas.drawCircle(
        seat(i),
        (i.isEven ? 4.5 : 3.0) * lit,
        Paint()..color = AlmaPalette.starFill.withValues(alpha: 0.9 * lit),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _WritingPainter old) =>
      old.progress != progress || old.seed != seed;
}


/// **Рисунок идёт, пока идёт письмо.**
///
/// `SelfDrawing` проигрывает вступление один раз и застывает — так устроены
/// диаграммы, и для них это правильно: осевшая картина стоит столько же,
/// сколько статичная. Здесь наоборот: минута неподвижности читается как
/// зависшее приложение, а человек должен видеть, что главу действительно
/// пишут. Цикл повторяется, и каждый круг начинается с чистого неба.
class _Forever extends StatefulWidget {
  const _Forever({required this.size, required this.seed});

  final double size;
  final int seed;

  @override
  State<_Forever> createState() => _ForeverState();
}

class _ForeverState extends State<_Forever> with SingleTickerProviderStateMixin {
  late final AnimationController _clock = AnimationController(
    vsync: this,
    // Длительность круга тоже своя: одинаковый ритм у восьми ожиданий читается
    // как одна и та же заставка.
    duration: Duration(milliseconds: 6200 + (widget.seed % 5) * 700),
  )..repeat();

  @override
  void dispose() {
    _clock.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _clock,
        builder: (context, _) => CustomPaint(
          painter: _WritingPainter(
              Curves.easeInOutCubic.transform(_clock.value), widget.seed),
          size: Size.square(widget.size),
        ),
      );
}
