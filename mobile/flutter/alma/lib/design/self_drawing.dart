import 'package:flutter/material.dart';

/// Часы вступления, общие для всех рисунков продукта.
///
/// Порт `SelfDrawing` из `SystemArt.swift`. Рисунок **строит себя** за две
/// секунды, ступень за ступенью, и потом замирает — правильная экономия для
/// слабой машины. Кубическое замедление: диаграмма приезжает быстро и оседает
/// мягко.
///
/// Повторное появление сбрасывает часы, и пауза снимается вместе с ними: на
/// iOS остановленная лента с новым «рождением» рисовала один кадр нулевого
/// прогресса, и рисунок просто пропадал при каждом возврате. Здесь то же
/// правило записано в [initState].
class SelfDrawing extends StatefulWidget {
  const SelfDrawing({super.key, required this.builder, this.intro = const Duration(seconds: 2)});

  /// Получает прогресс 0…1 после замедления.
  final Widget Function(BuildContext context, double progress) builder;
  final Duration intro;

  @override
  State<SelfDrawing> createState() => _SelfDrawingState();
}

class _SelfDrawingState extends State<SelfDrawing> with SingleTickerProviderStateMixin {
  late final AnimationController _controller =
      AnimationController(vsync: this, duration: widget.intro);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      if (still) {
        _controller.value = 1;
      } else {
        _controller.forward(from: 0);
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final raw = _controller.value;
        // Ease-out cubic, ровно как в Swift: 1 - (1 - t)³.
        final eased = 1 - ((1 - raw) * (1 - raw) * (1 - raw));
        return widget.builder(context, eased);
      },
    );
  }
}

/// Какой отрезок вступления принадлежит элементу, как его собственный 0…1.
///
/// Ровно `phase` из `SystemArt.swift` и `NatalWheel.swift`: кольца сметаются
/// первыми, знаки загораются по очереди, дома растут наружу, планеты садятся,
/// аспекты сплетаются последними — тот порядок, в каком колесо чертил бы
/// астролог.
double phase(double progress, double from, double to) {
  final value = (progress - from) / (to - from);
  return value.clamp(0.0, 1.0);
}
