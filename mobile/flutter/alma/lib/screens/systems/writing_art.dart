import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../design/palette.dart';
import '../../design/self_drawing.dart';

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
  const WritingArt({super.key, this.size = 260});

  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: SelfDrawing(
        // Дольше вступления диаграмм: это ожидание, а не приход экрана.
        intro: const Duration(seconds: 6),
        builder: (context, progress) => CustomPaint(
          painter: _WritingPainter(progress),
          size: Size.square(size),
        ),
      ),
    );
  }
}

class _WritingPainter extends CustomPainter {
  _WritingPainter(this.progress);

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final centre = Offset(size.width / 2, size.height / 2);
    final outer = size.width * 0.42;
    final inner = size.width * 0.27;

    // Две орбиты замыкаются первыми, одна за другой.
    for (final (radius, from, to) in [(outer, 0.0, 0.45), (inner, 0.15, 0.6)]) {
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
    for (var i = 0; i < 48; i++) {
      final lit = phase(progress, 0.25 + i * 0.006, 0.5 + i * 0.006);
      if (lit <= 0) continue;
      final a = i * math.pi / 24 - math.pi / 2;
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
    const seats = [0.08, 0.2, 0.34, 0.52, 0.63, 0.78, 0.9];
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
  bool shouldRepaint(covariant _WritingPainter old) => old.progress != progress;
}
