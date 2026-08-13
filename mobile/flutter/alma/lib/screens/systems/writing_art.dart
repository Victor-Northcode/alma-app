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
    final r = size.width * 0.40;
    // **Форма у каждой системы своя, а не одна с другим сдвигом.** Владелец
    // прошёл все восемь и сказал прямо: «практически одна и та же». Здесь
    // восемь разных ожиданий; общий у них только материал — золото, тонкая
    // линия и звёздная точка.
    switch (seed % 8) {
      case 0:
        _orbits(canvas, centre, r, 3);
      case 1:
        _spiral(canvas, centre, r);
      case 2:
        _pulse(canvas, centre, r);
      case 3:
        _rays(canvas, centre, r, 12);
      case 4:
        _wave(canvas, centre, size);
      case 5:
        _lattice(canvas, centre, r);
      case 6:
        _comet(canvas, centre, r);
      default:
        _constellation(canvas, centre, r);
    }
  }

  Paint get _line => Paint()
    ..style = PaintingStyle.stroke
    ..strokeWidth = 1
    ..color = AlmaPalette.gold.withValues(alpha: 0.45);

  Paint get _star => Paint()..color = AlmaPalette.starFill.withValues(alpha: 0.9);

  /// Кольца, замыкающиеся одно за другим и снова расходящиеся.
  void _orbits(Canvas canvas, Offset c, double r, int rings) {
    for (var i = 0; i < rings; i++) {
      final t = phase(progress, i * 0.1, 0.6 + i * 0.1);
      if (t <= 0) continue;
      canvas.drawArc(Rect.fromCircle(center: c, radius: r - i * r * 0.22),
          -math.pi / 2, 2 * math.pi * t, false, _line);
    }
    canvas.drawCircle(c + Offset(0, -r), 3.5, _star);
  }

  /// Спираль, наматывающаяся к центру.
  void _spiral(Canvas canvas, Offset c, double r) {
    final path = Path();
    final turns = 3.5;
    final steps = (200 * progress).round();
    for (var i = 0; i <= steps; i++) {
      final t = i / 200;
      final a = t * turns * 2 * math.pi - math.pi / 2;
      final rad = r * (1 - t * 0.75);
      final p = c + Offset(math.cos(a) * rad, math.sin(a) * rad);
      i == 0 ? path.moveTo(p.dx, p.dy) : path.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(path, _line);
  }

  /// Круги, расходящиеся от центра, как круги на воде.
  void _pulse(Canvas canvas, Offset c, double r) {
    for (var i = 0; i < 4; i++) {
      final t = (progress + i / 4) % 1.0;
      canvas.drawCircle(
        c,
        r * t,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = AlmaPalette.gold.withValues(alpha: 0.5 * (1 - t)),
      );
    }
    canvas.drawCircle(c, 3, _star);
  }

  /// Лучи, зажигающиеся по кругу и гаснущие следом.
  void _rays(Canvas canvas, Offset c, double r, int count) {
    for (var i = 0; i < count; i++) {
      final own = (progress * count - i) % count / count;
      final lit = own < 0.35 ? 1 - own / 0.35 : 0.0;
      if (lit <= 0) continue;
      final a = i * 2 * math.pi / count - math.pi / 2;
      canvas.drawLine(
        c + Offset(math.cos(a), math.sin(a)) * r * 0.35,
        c + Offset(math.cos(a), math.sin(a)) * r,
        Paint()
          ..strokeWidth = 1.2
          ..color = AlmaPalette.gold.withValues(alpha: 0.55 * lit),
      );
    }
  }

  /// Волна, бегущая слева направо, — для карты линий.
  void _wave(Canvas canvas, Offset c, Size size) {
    for (var row = 0; row < 3; row++) {
      final path = Path();
      final y = c.dy + (row - 1) * size.height * 0.14;
      for (var x = 0.0; x <= size.width; x += 4) {
        final t = x / size.width;
        final dy = math.sin((t * 3 + progress * 2 + row * 0.4) * math.pi * 2) *
            size.height *
            0.05;
        x == 0 ? path.moveTo(x, y + dy) : path.lineTo(x, y + dy);
      }
      canvas.drawPath(path, _line);
    }
  }

  /// Решётка, проявляющаяся клетками.
  void _lattice(Canvas canvas, Offset c, double r) {
    const n = 4;
    for (var i = 0; i <= n; i++) {
      final t = phase(progress, i * 0.08, 0.5 + i * 0.08);
      if (t <= 0) continue;
      final o = (i / n - 0.5) * 2 * r;
      canvas.drawLine(c + Offset(o, -r), c + Offset(o, -r + 2 * r * t), _line);
      canvas.drawLine(c + Offset(-r, o), c + Offset(-r + 2 * r * t, o), _line);
    }
  }

  /// Комета, обходящая круг.
  void _comet(Canvas canvas, Offset c, double r) {
    canvas.drawCircle(
      c,
      r,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = AlmaPalette.gold.withValues(alpha: 0.18),
    );
    for (var i = 0; i < 14; i++) {
      final t = (progress - i * 0.012) % 1.0;
      final a = t * 2 * math.pi - math.pi / 2;
      canvas.drawCircle(
        c + Offset(math.cos(a), math.sin(a)) * r,
        3.2 * (1 - i / 14),
        Paint()..color = AlmaPalette.starFill.withValues(alpha: 0.9 * (1 - i / 14)),
      );
    }
  }

  /// Созвездие: точки садятся и связываются нитями.
  void _constellation(Canvas canvas, Offset c, double r) {
    const seats = [0.05, 0.19, 0.33, 0.5, 0.62, 0.79, 0.91];
    Offset at(int i) {
      final a = seats[i] * 2 * math.pi - math.pi / 2;
      return c + Offset(math.cos(a), math.sin(a)) * (i.isEven ? r : r * 0.62);
    }

    for (var i = 0; i < seats.length; i++) {
      final lit = phase(progress, i * 0.09, 0.4 + i * 0.09);
      if (lit <= 0) continue;
      if (i > 0) {
        final grown = phase(progress, 0.05 + i * 0.09, 0.45 + i * 0.09);
        final a = at(i - 1);
        final b = at(i);
        canvas.drawLine(a, Offset(a.dx + (b.dx - a.dx) * grown, a.dy + (b.dy - a.dy) * grown), _line);
      }
      canvas.drawCircle(at(i), 4 * lit, _star);
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
          // Линейный ход, а не кривая с остановками на краях: иначе рисунок
          // «шёл, пропадал и начинался сначала» — ровно то, что видно глазом.
          painter: _WritingPainter(_clock.value, widget.seed),
          size: Size.square(widget.size),
        ),
      );
}
