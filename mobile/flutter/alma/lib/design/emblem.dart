import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'metrics.dart';
import 'palette.dart';
import 'typography.dart';

/// Знак Alma: ромб золотого литья с восьмиконечной звездой и двумя встречными
/// кольцами лучей.
///
/// **Рисуется кодом, а не картинкой, и это решение.** Знак стоит в четырёх
/// размерах — 24 в рейле планшета, 64 в церемониальном диалоге, 110 на «Сегодня»
/// — и растровый остался бы резким только в одном из них. Нарисованный
/// перекрашивается токенами и вращается; единственная растровая версия знака в
/// продукте — иконка приложения, и там он статичен по определению.
///
/// Числа из дизайн-проекта: градиент под 135°, ромб повёрнут на 45°, звезда
/// **восьмиконечная** и цвета `#141019` — не чистого чёрного, иначе она читается
/// дырой, а не тенью. Кольца идут навстречу друг другу за 70 и 90 секунд:
/// одинаковая скорость слепила бы их в одно неподвижное пятно.
class AlmaEmblem extends StatefulWidget {
  const AlmaEmblem({super.key, this.size = 64, this.rings = true});

  final double size;

  /// Кольца лучей вокруг ромба. В рейле их нет: на 24 точках они превращаются
  /// в грязь вокруг знака.
  final bool rings;

  @override
  State<AlmaEmblem> createState() => _AlmaEmblemState();
}

class _AlmaEmblemState extends State<AlmaEmblem> with TickerProviderStateMixin {
  late final AnimationController _outer = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 70),
  );
  late final AnimationController _inner = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 90),
  );

  @override
  void initState() {
    super.initState();
    _outer.repeat();
    _inner.repeat();
  }

  @override
  void dispose() {
    _outer.dispose();
    _inner.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // «Меньше движения» останавливает кольца, но не убирает их: они часть
    // знака, а не украшение поверх него.
    final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    final side = widget.size;
    final full = widget.rings ? side * 2.1 : side;

    return SizedBox(
      width: full,
      height: full,
      child: Stack(
        alignment: Alignment.center,
        children: [
          if (widget.rings) ...[
            _Ring(turn: still ? null : _outer, size: full, step: 8.6, lit: 2.4),
            _Ring(
              turn: still ? null : _inner,
              size: full * 0.82,
              step: 8.6,
              lit: 2.4,
              reverse: true,
            ),
          ],
          _Diamond(side: side),
        ],
      ),
    );
  }
}

/// Ромб с литым золотом и звездой внутри.
class _Diamond extends StatelessWidget {
  const _Diamond({required this.side});

  final double side;

  @override
  Widget build(BuildContext context) {
    return Transform.rotate(
      angle: math.pi / 4,
      child: Container(
        width: side * 0.72,
        height: side * 0.72,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(side * 0.06),
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFFFBEDC4),
              Color(0xFFE0C077),
              Color(0xFFB3913F),
              Color(0xFF8A6F2E),
            ],
            stops: [0, 0.34, 0.70, 1],
          ),
        ),
        // Звезда рисуется невращённой: ромб повёрнут, а знак внутри — нет.
        child: Transform.rotate(
          angle: -math.pi / 4,
          child: CustomPaint(painter: _StarPainter(), size: Size.square(side * 0.72)),
        ),
      ),
    );
  }
}

/// Восьмиконечная звезда: четыре длинных луча по осям и четыре коротких между.
///
/// Восемь, а не четыре: четырёхлучевая внутри ромба повторяет его форму и
/// пропадает, восьмилучевая читается как знак.
class _StarPainter extends CustomPainter {
  static const _ink = Color(0xFF141019);

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final long = size.width * 0.30;
    final short = long * 0.38;

    final path = Path();
    for (var i = 0; i < 16; i++) {
      final r = i.isEven ? long : short;
      final a = -math.pi / 2 + i * math.pi / 8;
      final p = Offset(c.dx + r * math.cos(a), c.dy + r * math.sin(a));
      i == 0 ? path.moveTo(p.dx, p.dy) : path.lineTo(p.dx, p.dy);
    }
    path.close();
    canvas.drawPath(path, Paint()..color = _ink);
  }

  @override
  bool shouldRepaint(_StarPainter oldDelegate) => false;
}

/// Кольцо лучей: тонкие золотые спицы, вырезанные в кольцо.
class _Ring extends StatelessWidget {
  const _Ring({
    required this.turn,
    required this.size,
    required this.step,
    required this.lit,
    this.reverse = false,
  });

  /// `null` — система просит меньше движения: кольцо стоит.
  final AnimationController? turn;
  final double size;

  /// Шаг спиц и ширина освещённой части, в градусах.
  final double step;
  final double lit;

  final bool reverse;

  @override
  Widget build(BuildContext context) {
    final ring = CustomPaint(
      size: Size.square(size),
      painter: _RayPainter(step: step, lit: lit),
    );
    final controller = turn;
    if (controller == null) return SizedBox.square(dimension: size, child: ring);
    return SizedBox.square(
      dimension: size,
      child: RotationTransition(
        turns: reverse
            ? Tween<double>(begin: 1, end: 0).animate(controller)
            : controller,
        child: ring,
      ),
    );
  }
}

class _RayPainter extends CustomPainter {
  _RayPainter({required this.step, required this.lit});

  final double step;
  final double lit;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final outer = size.width / 2;
    // Кольцо, а не диск: лучи начинаются за ромбом и не лезут ему под низ.
    final inner = outer * 0.62;
    final paint = Paint()..color = const Color(0x59C9AE6B);

    for (double a = 0; a < 360; a += step) {
      final from = a * math.pi / 180;
      final to = (a + lit) * math.pi / 180;
      final path = Path()
        ..moveTo(c.dx + inner * math.cos(from), c.dy + inner * math.sin(from))
        ..lineTo(c.dx + outer * math.cos(from), c.dy + outer * math.sin(from))
        ..lineTo(c.dx + outer * math.cos(to), c.dy + outer * math.sin(to))
        ..lineTo(c.dx + inner * math.cos(to), c.dy + inner * math.sin(to))
        ..close();
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(_RayPainter oldDelegate) =>
      oldDelegate.step != step || oldDelegate.lit != lit;
}

/// Поле ввода церемонии: пилюля высотой 54, золотой кант при фокусе.
///
/// Отдельно от `TextField` по умолчанию, потому что материаловский подчёркнутый
/// вариант — чужая форма: у продукта поля пилюлями, как кнопки, и разница
/// между ними в заливке, а не в очертании.
class CeremonialField extends StatefulWidget {
  const CeremonialField({
    super.key,
    required this.controller,
    this.hint,
    this.onSubmitted,
    this.autofocus = false,
    this.keyboardType,
    this.textAlign = TextAlign.start,
  });

  final TextEditingController controller;
  final String? hint;
  final ValueChanged<String>? onSubmitted;
  final bool autofocus;
  final TextInputType? keyboardType;
  final TextAlign textAlign;

  @override
  State<CeremonialField> createState() => _CeremonialFieldState();
}

class _CeremonialFieldState extends State<CeremonialField> {
  late final FocusNode _focus = FocusNode()..addListener(_onFocus);

  void _onFocus() => setState(() {});

  @override
  void dispose() {
    _focus.removeListener(_onFocus);
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final lit = _focus.hasFocus;
    return AnimatedContainer(
      duration: AlmaMotion.ui,
      curve: AlmaMotion.uiCurve,
      height: AlmaMetrics.fieldHeight,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      decoration: BoxDecoration(
        color: const Color(0xD90D101C),
        borderRadius: BorderRadius.circular(AlmaMetrics.fieldHeight / 2),
        border: Border.all(
          // Кант при фокусе золотой и плотный: поле, в которое пишут, должно
          // отличаться от поля, которое ждёт, чем-то кроме мигающей палочки.
          color: lit
              ? const Color(0xCCC9AE6B)
              : const Color(0x1FEDE7DA),
          width: lit ? 1.4 : 1,
        ),
      ),
      // **Material внутри, а не снаружи.** `TextField` без него падает красной
      // плашкой «No Material widget found», и это ошибка не экрана, а виджета:
      // базовое поле не вправе требовать от каждого экрана знания о том, что у
      // него внутри. Прозрачный — рисует всё равно рамка выше.
      child: Material(
        type: MaterialType.transparency,
        child: Center(
        child: TextField(
          controller: widget.controller,
          focusNode: _focus,
          autofocus: widget.autofocus,
          keyboardType: widget.keyboardType,
          textAlign: widget.textAlign,
          onSubmitted: widget.onSubmitted,
          cursorColor: const Color(0xFFC9AE6B),
          style: AlmaType.body.copyWith(fontSize: 16, color: AlmaPalette.inkLight),
          decoration: InputDecoration(
            isDense: true,
            border: InputBorder.none,
            hintText: widget.hint,
            hintStyle: AlmaType.body
                .copyWith(fontSize: 16, color: AlmaPalette.body.withValues(alpha: 0.45)),
          ),
        ),
        ),
      ),
    );
  }
}
