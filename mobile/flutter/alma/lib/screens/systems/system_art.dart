import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../design/palette.dart';
import '../../design/self_drawing.dart';

/// Диаграммы остальных систем — по одной на систему, и каждая читает **свой**
/// payload. Порт `SystemArt.swift`: те же формы, те же фазы вступления, тот же
/// закон — нет данных, нет штриха.

/* ── нумерология: жизнь кольцом ─────────────────────────────────────────── */

/// Вершины и циклы двумя полосами вокруг числа жизненного пути, засечка —
/// сегодняшний возраст.
class NumerologyRing extends StatelessWidget {
  const NumerologyRing({super.key, required this.data, this.age});

  final Map<String, dynamic> data;
  final int? age;

  @override
  Widget build(BuildContext context) => AspectRatio(
        aspectRatio: 1,
        child: SelfDrawing(
          builder: (context, p) =>
              CustomPaint(painter: _NumerologyPainter(data, age, p), size: Size.infinite),
        ),
      );
}

class _Seg {
  const _Seg(this.number, this.from, this.to);
  final int number;
  final double from;
  final double to;
}

List<_Seg> _segments(Object? rows, double span) {
  if (rows is! List) return const [];
  final out = <_Seg>[];
  for (final row in rows) {
    if (row is! Map) continue;
    final number = (row['number'] as num?)?.toInt();
    final from = (row['starts_age'] as num?)?.toDouble();
    if (number == null || from == null) continue;
    // `ends_age` пуст у последнего отрезка и означает «до конца жизни».
    final to = (row['ends_age'] as num?)?.toDouble() ?? span;
    out.add(_Seg(number, from, to));
  }
  return out;
}

class _NumerologyPainter extends CustomPainter {
  _NumerologyPainter(this.data, this.age, this.progress);

  final Map<String, dynamic> data;
  final int? age;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final side = math.min(size.width, size.height);
    final centre = Offset(size.width / 2, size.height / 2);

    final pinnacleRows = data['pinnacles'];
    final lastStart = pinnacleRows is List && pinnacleRows.isNotEmpty
        ? ((pinnacleRows.last as Map)['starts_age'] as num?)?.toDouble() ?? 72
        : 72;
    final span = math.max(math.max(lastStart + 9, 81), (age ?? 0) + 9).toDouble();

    double angle(double years) => (years / span) * 360 - 90;
    Offset at(double years, double radius) {
      final a = angle(years) * math.pi / 180;
      return centre + Offset(math.cos(a) * radius, math.sin(a) * radius);
    }

    void band(List<_Seg> segments, double radius, Color colour, double opening, double upTo) {
      for (var i = 0; i < segments.length; i++) {
        final grown = phase(progress, opening + i * 0.06, upTo + i * 0.06);
        if (grown <= 0) continue;
        final seg = segments[i];
        // Волос зазора между отрезками: это главы жизни, а не одна линия.
        final from = seg.from + span * 0.006;
        final to = seg.from + (seg.to - seg.from - span * 0.006) * grown;
        canvas.drawArc(
          Rect.fromCircle(center: centre, radius: radius),
          angle(from) * math.pi / 180,
          (angle(to) - angle(from)) * math.pi / 180,
          false,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.6
            ..color = colour.withValues(alpha: 0.55),
        );
        _text(canvas, '${seg.number}', at((seg.from + seg.to) / 2, radius + side * 0.045),
            side * 0.045, colour.withValues(alpha: grown));
      }
    }

    band(_segments(data['pinnacles'], span), side * 0.40, AlmaPalette.gold, 0.1, 0.4);
    band(_segments(data['cycles'], span), side * 0.28, AlmaPalette.starFill, 0.3, 0.6);

    // Сегодняшний возраст — только когда он действительно известен.
    if (age != null) {
      final lit = phase(progress, 0.75, 0.9);
      if (lit > 0) {
        canvas.drawLine(
          at(age!.toDouble(), side * 0.245),
          at(age!.toDouble(), side * 0.44),
          Paint()
            ..strokeWidth = 1
            ..color = AlmaPalette.goldBright.withValues(alpha: 0.8 * lit),
        );
      }
    }

    // Число жизненного пути в центре; мастер-число получает ореол.
    final path = (data['life_path'] as num?)?.toInt();
    if (path != null) {
      final seated = phase(progress, 0.45, 0.8);
      if (seated > 0) {
        if (const [11, 22, 33].contains(path)) {
          canvas.drawCircle(
            centre,
            side * 0.13,
            Paint()
              ..style = PaintingStyle.stroke
              ..strokeWidth = 0.8
              ..color = AlmaPalette.gold.withValues(alpha: 0.30 * seated),
          );
        }
        _text(canvas, '$path', centre, side * 0.17 * (0.7 + 0.3 * seated),
            AlmaPalette.inkLight.withValues(alpha: seated));
      }
    }

    // Личный год — число, которое меняется, под числом, которое не меняется.
    final year = (data['personal'] is Map) ? (data['personal']['year'] as num?)?.toInt() : null;
    if (year != null) {
      final lit = phase(progress, 0.85, 1);
      if (lit > 0) {
        _text(canvas, '· $year ·', centre + Offset(0, side * 0.15), side * 0.05,
            AlmaPalette.gold.withValues(alpha: 0.7 * lit));
      }
    }
  }

  @override
  bool shouldRepaint(covariant _NumerologyPainter old) => old.progress != progress;
}

/* ── астрокартография: линии на земле ───────────────────────────────────── */

/// Сетка и настоящие линии планет по их координатам. Береговой линии нет
/// намеренно: она была бы украшением, а линии — это расчёт.
class LinesMapArt extends StatelessWidget {
  const LinesMapArt({super.key, required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => AspectRatio(
        aspectRatio: 1.9,
        child: SelfDrawing(
          builder: (context, p) =>
              CustomPaint(painter: _LinesPainter(data, p), size: Size.infinite),
        ),
      );
}

class _LinesPainter extends CustomPainter {
  _LinesPainter(this.data, this.progress);

  final Map<String, dynamic> data;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    Offset project(double lat, double lon) =>
        Offset((lon + 180) / 360 * w, (66 - lat) / 132 * h);

    final grid = phase(progress, 0, 0.35);
    for (var i = 0; i <= 12; i++) {
      final x = i / 12 * w;
      canvas.drawLine(Offset(x, 0), Offset(x, h * grid),
          Paint()..strokeWidth = 0.5..color = AlmaPalette.gold.withValues(alpha: 0.10));
    }
    for (var i = 0; i <= 4; i++) {
      final y = i / 4 * h;
      canvas.drawLine(Offset(0, y), Offset(w * grid, y),
          Paint()
            ..strokeWidth = i == 2 ? 0.8 : 0.5
            ..color = AlmaPalette.gold.withValues(alpha: i == 2 ? 0.22 : 0.10));
    }

    final lines = (data['lines'] as List?) ?? const [];
    for (var index = 0; index < lines.length; index++) {
      final drawn = phase(progress, 0.2 + (index % 12) * 0.03, 0.65 + (index % 12) * 0.03);
      if (drawn <= 0) continue;
      final line = lines[index];
      if (line is! Map) continue;
      final points = (line['points'] as List?) ?? const [];
      if (points.length < 2) continue;
      final body = line['body'] as String? ?? '';
      final luminary = body == 'sun' || body == 'moon';
      final path = Path();
      final visible = math.max(2, (points.length * drawn).round());
      var started = false;
      for (final p in points.take(visible)) {
        if (p is! Map) continue;
        final lat = (p['lat'] as num?)?.toDouble();
        final lon = (p['lon'] as num?)?.toDouble();
        if (lat == null || lon == null) continue;
        final at = project(lat, lon);
        started ? path.lineTo(at.dx, at.dy) : path.moveTo(at.dx, at.dy);
        started = true;
      }
      canvas.drawPath(
        path,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = luminary ? 1.1 : 0.6
          ..color = luminary
              ? AlmaPalette.goldBright.withValues(alpha: 0.5)
              : AlmaPalette.starFill.withValues(alpha: 0.16),
      );
    }

    // Место рождения — единственная яркая звезда на карте.
    final place = data['birthplace'];
    if (place is Map) {
      final lat = (place['latitude'] as num?)?.toDouble();
      final lon = (place['longitude'] as num?)?.toDouble();
      final lit = phase(progress, 0.8, 1);
      if (lat != null && lon != null && lit > 0) {
        final at = project(lat, lon);
        final r = 3.5 * lit;
        for (final d in [Offset(r * 2.2, 0), Offset(-r * 2.2, 0), Offset(0, r * 2.2), Offset(0, -r * 2.2)]) {
          canvas.drawLine(at, at + d,
              Paint()..strokeWidth = 0.8..color = AlmaPalette.goldBright.withValues(alpha: 0.8 * lit));
        }
        canvas.drawCircle(at, r, Paint()..color = AlmaPalette.starFill.withValues(alpha: lit));
      }
    }
  }

  @override
  bool shouldRepaint(covariant _LinesPainter old) => old.progress != progress;
}

/* ── карта рождения: сама карта ─────────────────────────────────────────── */

/// Карта в рамке: римская цифра аркана и мотив его стихии.
class BirthCardArt extends StatelessWidget {
  const BirthCardArt({super.key, required this.data, this.name});

  final Map<String, dynamic> data;
  final String? name;

  @override
  Widget build(BuildContext context) => AspectRatio(
        aspectRatio: 1.25,
        child: SelfDrawing(
          builder: (context, p) =>
              CustomPaint(painter: _CardPainter(data, name, p), size: Size.infinite),
        ),
      );
}

class _CardPainter extends CustomPainter {
  _CardPainter(this.data, this.name, this.progress);

  final Map<String, dynamic> data;
  final String? name;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final side = math.min(size.width, size.height);
    final centre = Offset(size.width / 2, size.height / 2);
    final cardW = side * 0.52;
    final cardH = cardW * 1.62;

    final drawn = phase(progress, 0, 0.4);
    if (drawn > 0) {
      final rect = RRect.fromRectAndRadius(
        Rect.fromCenter(center: centre, width: cardW, height: cardH * drawn),
        Radius.circular(cardW * 0.05),
      );
      canvas.drawRRect(
        rect,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = AlmaPalette.gold.withValues(alpha: 0.45),
      );
    }

    final personality = data['personality'];
    if (personality is! Map) return;

    final numeral = personality['numeral'] as String?;
    if (numeral != null) {
      final said = phase(progress, 0.4, 0.7);
      if (said > 0) {
        _text(canvas, numeral, centre - Offset(0, cardH * 0.22), side * 0.12,
            AlmaPalette.inkLight.withValues(alpha: said));
      }
    }

    // Мотив стихии: воздух — три дуги, вода — две волны, огонь — язык пламени,
    // земля — три линии горизонта. Ничего не утверждает сверх стихии карты.
    final element = personality['element'] as String?;
    final motif = phase(progress, 0.55, 0.85);
    if (element != null && motif > 0) {
      final colour = AlmaPalette.gold.withValues(alpha: 0.55 * motif);
      final w = cardW * 0.6;
      final at = centre + Offset(0, cardH * 0.08);
      final paint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.8
        ..color = colour;
      switch (element) {
        case 'air':
          for (var i = 0; i < 3; i++) {
            final y = at.dy + (i - 1) * w * 0.14;
            final p = Path()..moveTo(at.dx - w / 2, y);
            p.quadraticBezierTo(at.dx, y - w * 0.08, at.dx - w / 2 + w * motif, y);
            canvas.drawPath(p, paint);
          }
        case 'water':
          for (var i = 0; i < 2; i++) {
            final y = at.dy + i * w * 0.14;
            final p = Path()..moveTo(at.dx - w / 2, y);
            p.cubicTo(at.dx - w / 4, y - w * 0.1, at.dx + w / 4, y + w * 0.1,
                at.dx + w / 2 * (2 * motif - 1), y);
            canvas.drawPath(p, paint);
          }
        case 'fire':
          final p = Path()..moveTo(at.dx, at.dy + w * 0.2);
          p.quadraticBezierTo(at.dx - w * 0.3, at.dy, at.dx, at.dy - w * 0.28 * motif);
          p.quadraticBezierTo(at.dx + w * 0.3, at.dy, at.dx, at.dy + w * 0.2);
          canvas.drawPath(p, paint);
        default:
          for (var i = 0; i < 3; i++) {
            final y = at.dy + (i - 1) * w * 0.12;
            canvas.drawLine(Offset(at.dx - w / 2 * motif, y), Offset(at.dx + w / 2 * motif, y), paint);
          }
      }
    }

    if (name != null && name!.isNotEmpty) {
      final said = phase(progress, 0.75, 1);
      if (said > 0) {
        _text(canvas, name!, centre + Offset(0, cardH * 0.72 / 2), side * 0.062,
            AlmaPalette.gold.withValues(alpha: 0.85 * said));
      }
    }
  }

  @override
  bool shouldRepaint(covariant _CardPainter old) => old.progress != progress;
}

/* ── синтез: девять осей звездой ────────────────────────────────────────── */

/// Ось, о которой системы согласны, расцветает золотом; спорная расходится на
/// две точки — согласие и несогласие продукта; одинокий голос остаётся точкой.
class SynthesisStar extends StatelessWidget {
  const SynthesisStar({super.key, required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => AspectRatio(
        aspectRatio: 1,
        child: SelfDrawing(
          builder: (context, p) =>
              CustomPaint(painter: _StarPainter(data, p), size: Size.infinite),
        ),
      );
}

class _StarPainter extends CustomPainter {
  _StarPainter(this.data, this.progress);

  final Map<String, dynamic> data;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final side = math.min(size.width, size.height);
    final centre = Offset(size.width / 2, size.height / 2);
    final axes = (data['axes'] as List?) ?? const [];
    if (axes.isEmpty) return;

    for (var index = 0; index < axes.length; index++) {
      final grown = phase(progress, 0.1 + index * 0.05, 0.5 + index * 0.05);
      if (grown <= 0) continue;
      final axis = axes[index];
      final verdict = axis is Map ? axis['verdict'] as String? ?? '' : '';
      final agree = verdict == 'agree';
      final a = (index / axes.length * 360 - 90) * math.pi / 180;
      final tip = centre + Offset(math.cos(a), math.sin(a)) * side * 0.42 * grown;

      canvas.drawLine(
        centre,
        tip,
        Paint()
          ..strokeWidth = agree ? 1.1 : 0.7
          ..color = AlmaPalette.gold.withValues(alpha: agree ? 0.45 : 0.2),
      );

      final seated = phase(progress, 0.5 + index * 0.04, 0.85 + index * 0.04);
      if (seated <= 0) continue;
      switch (verdict) {
        case 'agree':
          canvas.drawCircle(tip, side * 0.016 * seated,
              Paint()..color = AlmaPalette.agree.withValues(alpha: 0.9 * seated));
        case 'disagree':
          for (final (colour, sign) in [(AlmaPalette.agree, 1.0), (AlmaPalette.disagree, -1.0)]) {
            final off = Offset(-math.sin(a), math.cos(a)) * side * 0.022 * sign * seated;
            canvas.drawCircle(tip + off, side * 0.013 * seated,
                Paint()..color = colour.withValues(alpha: 0.85 * seated));
          }
        default:
          canvas.drawCircle(tip, side * 0.011 * seated,
              Paint()..color = AlmaPalette.starFill.withValues(alpha: 0.6 * seated));
      }
    }
  }

  @override
  bool shouldRepaint(covariant _StarPainter old) => old.progress != progress;
}

/* ── общее ──────────────────────────────────────────────────────────────── */

void _text(Canvas canvas, String text, Offset at, double size, Color colour) {
  final painter = TextPainter(
    text: TextSpan(
      text: text,
      style: TextStyle(
        fontSize: size,
        color: colour,
        fontFamily: 'Playfair Display',
        fontFamilyFallback: const ['New York', 'Charter', 'Georgia', 'serif'],
      ),
    ),
    textDirection: TextDirection.ltr,
  )..layout();
  painter.paint(canvas, at - Offset(painter.width / 2, painter.height / 2));
}
