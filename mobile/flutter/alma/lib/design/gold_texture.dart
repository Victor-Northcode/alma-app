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

  /// Лучи. Шаг 7°: 1.8° золота и 5.2° пустоты, из-под низа кнопки.
  ///
  /// `SweepGradient` красит по кругу от 0 и не умеет повторяться — поэтому
  /// остановки считаются заранее, парой на каждый луч. Пятьдесят один луч на
  /// круг: ровно 360/7.
  static SweepGradient rays() {
    const period = 7 * math.pi / 180;
    const lit = 1.8 * math.pi / 180;
    const gold = Color(0x66C9AE6B); // rgba(201,174,107,.4)
    const none = Color(0x00C9AE6B);

    final colors = <Color>[];
    final stops = <double>[];
    const full = 2 * math.pi;
    for (double a = 0; a < full; a += period) {
      final start = a / full;
      final end = math.min(a + lit, full) / full;
      // Пара «включили — выключили» на каждый луч: резкая грань, а не размытие.
      colors.addAll([gold, gold, none, none]);
      stops.addAll([start, end, end, math.min(a + period, full) / full]);
    }
    return SweepGradient(
      center: const Alignment(0, 1.6),
      startAngle: -8 * math.pi / 180,
      endAngle: -8 * math.pi / 180 + full,
      colors: colors,
      stops: stops,
      tileMode: TileMode.repeated,
    );
  }
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
        fit: StackFit.passthrough,
        children: [
          const DecoratedBox(decoration: BoxDecoration(gradient: GoldTexture.base)),
          Opacity(
            opacity: dimmed ? 0.5 : 1,
            child: DecoratedBox(decoration: BoxDecoration(gradient: GoldTexture.rays())),
          ),
          Opacity(
            opacity: dimmed ? 0.55 : 1,
            child: const DecoratedBox(decoration: BoxDecoration(gradient: GoldTexture.glow)),
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
