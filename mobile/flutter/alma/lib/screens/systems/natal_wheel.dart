import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../design/palette.dart';
import '../../design/self_drawing.dart';

/// Карта рождения как колесо, чертящее себя.
///
/// Порт `mobile/ios/Alma/Screens/Systems/NatalWheel.swift`. Это и есть картинка:
/// двенадцать знаков на внешнем кольце, куспиды домов спицами, планеты своими
/// глифами, главные аспекты хордами внутри.
///
/// **Глифы, а не подписи.** Колесо — это диаграмма, и глиф в ней и есть
/// нотация; имена планет живут строками ниже, где им место.
///
/// Собирается в том порядке, в каком колесо чертил бы астролог: кольца, знаки,
/// дома, планеты, аспекты. Та же церемония, которой открывается запуск.
class NatalWheel extends StatelessWidget {
  const NatalWheel({super.key, required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 1,
      child: SelfDrawing(
        builder: (context, progress) => CustomPaint(
          painter: _WheelPainter(data: data, progress: progress),
          size: Size.infinite,
        ),
      ),
    );
  }
}

class _Body {
  const _Body(this.name, this.glyph, this.longitude);
  final String name;
  final String glyph;
  final double longitude;
}

class _WheelPainter extends CustomPainter {
  _WheelPainter({required this.data, required this.progress});

  final Map<String, dynamic> data;
  final double progress;

  static const _signGlyphs = [
    '♈︎', '♉︎', '♊︎', '♋︎', '♌︎', '♍︎', '♎︎', '♏︎', '♐︎', '♑︎', '♒︎', '♓︎',
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final side = math.min(size.width, size.height);
    final centre = Offset(size.width / 2, size.height / 2);
    final outer = side * 0.48;
    final signBand = side * 0.40;
    final planetRing = side * 0.31;
    final aspectRing = side * 0.26;

    final angles = data['angles'];
    final ascendant = angles is Map ? (angles['ascendant'] as num?)?.toDouble() : null;

    /// Экранный угол для эклиптической долготы: Асцендент (или 0° Овна) слева,
    /// зодиак идёт против часовой стрелки.
    Offset point(double longitude, double radius) {
      final base = ascendant ?? 0;
      final degrees = 180 - (longitude - base);
      final radians = degrees * math.pi / 180;
      return centre + Offset(math.cos(radians) * radius, -math.sin(radians) * radius);
    }

    // ── кольца: каждое сметает себя по кругу ──
    final ringSweep = phase(progress, 0.0, 0.35);
    for (final radius in [outer, signBand, planetRing]) {
      _arc(canvas, centre, radius, ringSweep,
          AlmaPalette.gold.withValues(alpha: 0.28), 1);
    }
    _arc(canvas, centre, aspectRing, ringSweep,
        AlmaPalette.gold.withValues(alpha: 0.18), 1);

    // ── знаки: загораются по очереди ──
    for (var index = 0; index < 12; index++) {
      final lit = phase(progress, 0.20 + index * 0.02, 0.40 + index * 0.02);
      if (lit <= 0) continue;
      final start = index * 30.0;
      canvas.drawLine(
        point(start, signBand),
        point(start, outer),
        Paint()
          ..color = AlmaPalette.gold.withValues(alpha: 0.35 * lit)
          ..strokeWidth = 1,
      );
      _glyph(canvas, _signGlyphs[index], point(start + 15, (outer + signBand) / 2),
          side * 0.045, AlmaPalette.goldBright.withValues(alpha: 0.8 * lit));
    }

    // ── дома, когда есть горизонт: спицы растут наружу ──
    final houses = data['houses'];
    if (ascendant != null && houses is List) {
      final grown = phase(progress, 0.40, 0.65);
      if (grown > 0) {
        for (final raw in houses) {
          if (raw is! Map) continue;
          final cusp = (raw['cusp'] as num?)?.toDouble();
          final number = (raw['number'] as num?)?.toInt();
          if (cusp == null || number == null) continue;
          final cardinal = const [1, 4, 7, 10].contains(number);
          final from = point(cusp, aspectRing);
          final to = point(cusp, signBand);
          canvas.drawLine(
            from,
            Offset.lerp(from, to, grown)!,
            Paint()
              ..color = AlmaPalette.gold.withValues(alpha: (cardinal ? 0.5 : 0.22) * grown)
              ..strokeWidth = cardinal ? 1.4 : 1,
          );
          final next = houses.whereType<Map>().where(
              (h) => (h['number'] as num?)?.toInt() == number % 12 + 1);
          if (next.isNotEmpty) {
            final nextCusp = (next.first['cusp'] as num?)?.toDouble();
            if (nextCusp != null) {
              var span = nextCusp - cusp;
              if (span < 0) span += 360;
              _glyph(canvas, '$number', point(cusp + span / 2, aspectRing * 0.9),
                  side * 0.028, AlmaPalette.muted3.withValues(alpha: grown));
            }
          }
        }
      }
    }

    // ── планеты: садятся по одной, тесные расходятся внутрь ──
    final bodies = <_Body>[];
    final placements = data['placements'];
    if (placements is Map) {
      placements.forEach((name, placement) {
        if (placement is! Map) return;
        final longitude = (placement['longitude'] as num?)?.toDouble();
        final glyph = placement['glyph'] as String?;
        if (longitude == null || glyph == null) return;
        bodies.add(_Body(name as String, glyph, longitude));
      });
    }
    bodies.sort((a, b) => a.longitude.compareTo(b.longitude));

    final drawn = <(double, int)>[];
    for (var order = 0; order < bodies.length; order++) {
      final body = bodies[order];
      final close = drawn
          .where((d) =>
              (((d.$1 - body.longitude + 180) % 360) - 180).abs() < 6)
          .length;
      drawn.add((body.longitude, close));
      final step = bodies.length > 1 ? 0.25 / (bodies.length - 1) : 0.0;
      final seated =
          phase(progress, 0.55 + order * step, 0.70 + order * step);
      if (seated <= 0) continue;
      final radius = planetRing - close * side * 0.045;
      canvas.drawLine(
        point(body.longitude, signBand),
        point(body.longitude, signBand - side * 0.015),
        Paint()
          ..color = AlmaPalette.starFill.withValues(alpha: 0.8 * seated)
          ..strokeWidth = 1,
      );
      _glyph(canvas, body.glyph, point(body.longitude, radius),
          side * 0.042 * (0.6 + 0.4 * seated),
          AlmaPalette.starFill.withValues(alpha: seated));
    }

    // ── аспекты: сплетаются последними, только главные ──
    final aspects = data['aspects'];
    if (aspects is List) {
      final woven = phase(progress, 0.78, 1.0);
      if (woven > 0) {
        final positions = {for (final b in bodies) b.name: b.longitude};
        for (final raw in aspects) {
          if (raw is! Map) continue;
          if (raw['major'] != true) continue;
          final from = positions[raw['first']];
          final to = positions[raw['second']];
          if (from == null || to == null) continue;
          final tense = raw['harmony'] == 'tense';
          final a = point(from, aspectRing);
          final b = point(to, aspectRing);
          canvas.drawLine(
            a,
            Offset.lerp(a, b, woven)!,
            Paint()
              ..color = (tense ? AlmaPalette.disagree : AlmaPalette.agree)
                  .withValues(alpha: 0.30 * woven)
              ..strokeWidth = tense ? 0.9 : 0.7,
          );
        }
      }
    }
  }

  void _arc(Canvas canvas, Offset centre, double radius, double sweep,
      Color colour, double width) {
    if (sweep <= 0) return;
    canvas.drawArc(
      Rect.fromCircle(center: centre, radius: radius),
      -math.pi / 2,
      2 * math.pi * sweep,
      false,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = width
        ..color = colour,
    );
  }

  /// **Знак зодиака — это типографика, а не эмодзи.**
  ///
  /// Строки несут селектор текстового начертания U+FE0E, как и на iOS, но
  /// Flutter его не слушает: без явного шрифта движок берёт Apple Color Emoji,
  /// и на колесе вырастают фиолетовые плашки вместо золотых глифов. Найдено на
  /// первом же кадре колеса рядом с нативным. Шрифт назван прямо; на Android и
  /// в браузере его нет, и там срабатывают запасные, у которых те же знаки
  /// есть в текстовом виде.
  static const _glyphFallback = [
    'Apple Symbols',
    'Segoe UI Symbol',
    'Noto Sans Symbols 2',
    'serif',
  ];

  void _glyph(Canvas canvas, String text, Offset at, double size, Color colour) {
    final painter = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          fontSize: size,
          color: colour,
          fontFamily: 'Apple Symbols',
          fontFamilyFallback: _glyphFallback,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    painter.paint(canvas, at - Offset(painter.width / 2, painter.height / 2));
  }

  @override
  bool shouldRepaint(covariant _WheelPainter old) =>
      old.progress != progress || old.data != data;
}
