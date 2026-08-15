import 'dart:math' as math;

import 'package:flutter/widgets.dart';

/// Текстурное золото — заливка главной кнопки продукта.
///
/// **Плоского золота с тёмным текстом здесь быть не может.** Так кнопка
/// выглядела до дизайн-проекта: градиент `#DCC48A → #A8873C` и чернильная
/// подпись. Читалось это пластиковой наклейкой, а не ключом от двери, и
/// дизайн-система запрещает такую заливку словом «никогда».
///
/// Настоящая — тёмная: почти чёрная основа, тёплое свечение сверху и веер
/// тонких лучей снизу, будто на металл падает свет. Подпись — слоновая кость,
/// не чернила. Три слоя снизу вверх, как в рецепте `SKILL.md §2`:
///
/// 1. `linear-gradient(180deg, #1a1626, #0c0a14)` — основа;
/// 2. `repeating-conic-gradient(from -8deg at 50% 130%, …)` — лучи, шаг 7°,
///    из которых 1.8° золотые;
/// 3. `radial-gradient(140% 220% at 50% -80%, …)` — свечение над кнопкой.
///
/// Во Flutter нет ни повторяющегося конического градиента, ни процентов от
/// размера в позиции центра, поэтому лучи рисуются `SweepGradient` с
/// посчитанными остановками, а центры вынесены за пределы кнопки через
/// `Alignment` — 130% по высоте это `y = 1.6` в системе Flutter, где −1 верх,
/// а 1 низ.
class GoldTexture {
  const GoldTexture._();

  static const base = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFF1A1626), Color(0xFF0C0A14)],
  );

  /// Кант: тот же тёплый тон, что и свечение, чуть плотнее.
  static const edge = Color(0x8CE4C48A); // rgba(228,196,138,.55)

  /// Свечение над кнопкой. Центр на 80% выше верхнего края — в системе
  /// Flutter это `y = -2.6`, а радиус берётся от большей стороны, поэтому
  /// 140%/220% сведены к одному коэффициенту 2.2 по вертикали.
  static const glow = RadialGradient(
    center: Alignment(0, -2.6),
    radius: 2.2,
    colors: [Color(0x8CE4C48A), Color(0x0D141019)],
    stops: [0, 0.55],
  );

  /// Лучи рисуются painter'ом, а не градиентом.
  ///
  /// `SweepGradient` пробовался первым — он ближе всего к
  /// `repeating-conic-gradient` по замыслу, и рисовал он, если честно, почти то
  /// же самое. Но повторения он не умеет: пятьдесят один луч приходится
  /// задавать двумя сотнями остановок, посчитанных вручную, и любая правка
  /// шага требует пересчёта всего массива. Painter говорит то же самое тремя
  /// числами — клин в 1.8° каждые 7°, начиная с −8°, из точки на 130% высоты,
  /// то есть чуть ниже кнопки, — и читается как рецепт, а не как результат его
  /// применения.
  ///
  /// Сверено с эталоном в одном масштабе: веер, число и толщина лучей
  /// совпадают. Первое впечатление «лучи втрое шире» оказалось артефактом
  /// сравнения — эталон снимался в 1×, устройство в 2,23×.
}

/// Веер тонких лучей из точки под кнопкой.
class _RaysPainter extends CustomPainter {
  const _RaysPainter();

  /// Шаг и освещённая доля, градусы. Из `SKILL.md §2`.
  static const _period = 7.0;
  static const _lit = 1.8;
  static const _from = -8.0;

  @override
  void paint(Canvas canvas, Size size) {
    // Центр на 130% высоты от верха — ниже нижнего края на 30% высоты.
    final c = Offset(size.width / 2, size.height * 1.3);
    // Луч должен доставать до дальнего угла, иначе веер обрывается на середине.
    final reach = math.sqrt(size.width * size.width + c.dy * c.dy) * 1.1;
    final paint = Paint()..color = const Color(0x66C9AE6B);

    for (double a = _from; a < 360 + _from; a += _period) {
      final from = a * math.pi / 180;
      final to = (a + _lit) * math.pi / 180;
      canvas.drawPath(
        Path()
          ..moveTo(c.dx, c.dy)
          ..lineTo(c.dx + reach * math.cos(from), c.dy + reach * math.sin(from))
          ..lineTo(c.dx + reach * math.cos(to), c.dy + reach * math.sin(to))
          ..close(),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(_RaysPainter oldDelegate) => false;
}

/// Кнопка, залитая текстурным золотом.
///
/// Отдельным виджетом, а не одним `BoxDecoration`: три слоя нельзя сложить в
/// одну заливку — `BoxDecoration` знает про один градиент.
class GoldSurface extends StatelessWidget {
  const GoldSurface({
    super.key,
    required this.child,
    required this.radius,
    this.dimmed = false,
  });

  final Widget child;
  final BorderRadius radius;

  /// Нажатие: свет глохнет, кнопка темнеет. Масштаб не трогаем — золотая
  /// кнопка, которая уменьшается, читается как пластик.
  final bool dimmed;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: radius,
      child: Stack(
        children: [
          // **Слои растягиваются `Positioned.fill`, а не сами по себе.**
          //
          // `DecoratedBox` без ребёнка имеет нулевой размер: сложенные в `Stack`
          // просто как дети, все три градиента отрисовались в ничто, и кнопка
          // вышла прозрачной — сквозь неё было видно небо. Размер стопке задаёт
          // последний слой, у которого есть содержимое; остальные растягиваются
          // по нему.
          const Positioned.fill(
            child: DecoratedBox(decoration: BoxDecoration(gradient: GoldTexture.base)),
          ),
          Positioned.fill(
            child: Opacity(
              opacity: dimmed ? 0.5 : 1,
              child: const CustomPaint(painter: _RaysPainter()),
            ),
          ),
          Positioned.fill(
            child: Opacity(
              opacity: dimmed ? 0.55 : 1,
              child: const DecoratedBox(
                  decoration: BoxDecoration(gradient: GoldTexture.glow)),
            ),
          ),
          DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: radius,
              border: Border.all(color: GoldTexture.edge),
            ),
            child: child,
          ),
        ],
      ),
    );
  }
}
