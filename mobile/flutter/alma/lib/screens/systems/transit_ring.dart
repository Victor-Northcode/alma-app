import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../design/palette.dart';
import '../../design/self_drawing.dart';

/// Год транзитов кольцом: где ты в нём стоишь и что на подходе.
///
/// Порт `TransitYearRing` из `SystemArt.swift`, под тем же законом, что и
/// колесо: **всё нарисованное прочитано из payload системы.** Дуга — это
/// настоящий контакт с датами входа, точности и выхода; красная — напряжённый
/// аспект; стрелка наверху — сегодня. Нет данных — нет штриха.
class TransitYearRing extends StatelessWidget {
  const TransitYearRing({super.key, required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final arcs = _arcs(data);
    return AspectRatio(
      aspectRatio: 1,
      child: SelfDrawing(
        builder: (context, progress) => CustomPaint(
          painter: _RingPainter(arcs, progress),
          size: Size.infinite,
        ),
      ),
    );
  }
}

/// Одна дуга: доля года от входа до выхода, глиф над ней и вес.
class _Arc {
  const _Arc(this.glyph, this.start, this.end, this.tense, this.weight);

  final String glyph;
  final double start;
  final double end;
  final bool tense;
  final double weight;
}

DateTime? _day(Object? iso) {
  if (iso is! String || iso.length < 10) return null;
  return DateTime.tryParse(iso.substring(0, 10));
}

/// Активные контакты сначала, затем самые тяжёлые из будущих — не больше
/// девяти полос: кольцо из тридцати дуг это клякса, а не картина.
List<_Arc> _arcs(Map<String, dynamic> data) {
  final window = data['window'];
  if (window is! Map) return const [];
  final from = _day(window['from']);
  if (from == null) return const [];
  final days = (window['days'] as num?)?.toDouble() ?? 365;

  double? fraction(Object? iso) {
    final day = _day(iso);
    if (day == null) return null;
    return (day.difference(from).inDays / days).clamp(0.0, 1.0);
  }

  _Arc? arc(Object? row) {
    if (row is! Map) return null;
    final exact = fraction(row['exact']);
    if (exact == null) return null;
    final start = fraction(row['enters']) ?? exact;
    final end = fraction(row['leaves']) ?? math.min(exact + 0.02, 1.0);
    final aspect = row['aspect'] as String? ?? '';
    return _Arc(
      row['glyph'] as String? ?? '·',
      start,
      math.max(end, start),
      aspect == 'square' || aspect == 'opposition',
      (row['weight'] as num?)?.toDouble() ?? 0.3,
    );
  }

  final active = ((data['active'] as List?) ?? const [])
      .map(arc)
      .whereType<_Arc>()
      .toList();
  final upcoming = ((data['upcoming'] as List?) ?? const [])
      .map(arc)
      .whereType<_Arc>()
      .toList()
    ..sort((a, b) => b.weight.compareTo(a.weight));
  return [...active, ...upcoming].take(9).toList();
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.arcs, this.progress);

  final List<_Arc> arcs;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final side = math.min(size.width, size.height);
    final centre = Offset(size.width / 2, size.height / 2);
    final ring = side * 0.44;

    Offset at(double fraction, double radius) {
      final a = (fraction * 360 - 90) * math.pi / 180;
      return centre + Offset(math.cos(a) * radius, math.sin(a) * radius);
    }

    // Сам год замыкается первым.
    final sweep = phase(progress, 0, 0.3);
    if (sweep > 0) {
      canvas.drawArc(
        Rect.fromCircle(center: centre, radius: ring),
        -math.pi / 2,
        2 * math.pi * sweep,
        false,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = AlmaPalette.gold.withValues(alpha: 0.4),
      );
    }

    // Двенадцать месячных засечек.
    for (var month = 0; month < 12; month++) {
      final lit = phase(progress, 0.1 + month * 0.02, 0.3 + month * 0.02);
      if (lit <= 0) continue;
      final f = month / 12;
      canvas.drawLine(
        at(f, ring - side * 0.012),
        at(f, ring + side * 0.012),
        Paint()
          ..strokeWidth = 1
          ..color = AlmaPalette.gold.withValues(alpha: 0.35 * lit),
      );
    }

    // Контакты: каждый на своей полосе, внутрь от кольца.
    final step = side * 0.032;
    for (var i = 0; i < arcs.length; i++) {
      final grown = phase(progress, 0.3 + i * 0.05, 0.55 + i * 0.05);
      if (grown <= 0) continue;
      final arc = arcs[i];
      final radius = ring - side * 0.05 - i * step;
      final span = math.max(arc.end - arc.start, 0.004);
      canvas.drawArc(
        Rect.fromCircle(center: centre, radius: radius),
        (arc.start * 360 - 90) * math.pi / 180,
        span * grown * 2 * math.pi,
        false,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2
          ..color = (arc.tense ? AlmaPalette.disagree : AlmaPalette.gold)
              .withValues(alpha: 0.30 + 0.5 * arc.weight),
      );
      _glyph(canvas, arc.glyph, at(arc.start + span / 2, radius), side * 0.035,
          AlmaPalette.starFill.withValues(alpha: grown));
    }

    // Стрелка «сейчас» — наверху, рисуется последней.
    final armed = phase(progress, 0.85, 1);
    if (armed > 0) {
      canvas.drawLine(
        at(0, ring - side * 0.30),
        at(0, ring + side * 0.02),
        Paint()
          ..strokeWidth = 1.2
          ..color = AlmaPalette.goldBright.withValues(alpha: 0.9 * armed),
      );
      _glyph(canvas, '☉', at(0, ring + side * 0.045), side * 0.04,
          AlmaPalette.goldBright.withValues(alpha: armed));
    }
  }

  /// Глифы — символьным шрифтом, иначе знак приезжает цветным эмодзи.
  void _glyph(Canvas canvas, String text, Offset at, double size, Color colour) {
    final painter = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          fontSize: size,
          color: colour,
          fontFamily: 'Apple Symbols',
          fontFamilyFallback: const [
            'Apple Symbols',
            'Segoe UI Symbol',
            'Noto Sans Symbols 2',
            'serif',
          ],
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    painter.paint(canvas, at - Offset(painter.width / 2, painter.height / 2));
  }

  @override
  bool shouldRepaint(covariant _RingPainter old) => old.progress != progress;
}
