import 'package:flutter/material.dart';

/// Появление и жизнь осевшего экрана.
///
/// Порт `mobile/ios/Alma/DesignSystem/Components/Arrival.swift`, числа те же:
/// кривая (0.16, 1, 0.3, 1) на 550 мс, каскад по 70 мс на ступень, подъём на
/// 16 точек, ступени дальше восьмой не ждут дольше восьмой.
class AlmaArrive {
  const AlmaArrive._();

  static const curve = Cubic(0.16, 1, 0.3, 1);
  static const duration = Duration(milliseconds: 550);
  static const stagger = Duration(milliseconds: 70);
  static const rise = 16.0;
}

/// Затухание-и-подъём на первом появлении, [index] ступеней вниз по каскаду.
///
/// Одноразовое: обновление данных перерисовывает содержимое, но не
/// переигрывает вход. Безопасно в обычной колонке; в ленивом списке ушедшая
/// далеко строка уничтожается и войдёт заново при возврате — терпимо для
/// чата, неверно для оглавления. Экраны здесь используют обычные колонки.
class RiseIn extends StatefulWidget {
  const RiseIn({super.key, this.index = 0, required this.child});

  final int index;
  final Widget child;

  @override
  State<RiseIn> createState() => _RiseInState();
}

class _RiseInState extends State<RiseIn> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: AlmaArrive.duration,
  );
  late final CurvedAnimation _eased =
      CurvedAnimation(parent: _controller, curve: AlmaArrive.curve);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      if (still) {
        _controller.value = 1;
      } else {
        Future.delayed(AlmaArrive.stagger * widget.index.clamp(0, 8), () {
          if (mounted) _controller.forward();
        });
      }
    });
  }

  @override
  void dispose() {
    _eased.dispose();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _eased,
      builder: (context, child) => Opacity(
        opacity: _eased.value,
        child: Transform.translate(
          offset: Offset(0, AlmaArrive.rise * (1 - _eased.value)),
          child: child,
        ),
      ),
      child: widget.child,
    );
  }
}

/// Тихая жизнь осевшего рисунка: медленный вдох масштаба и света.
///
/// Ответ на находку владельца «анимация пропадает, она должна оставаться»,
/// который ничего не стоит: 3.4 секунды туда-обратно, масштаб 0.996…1.008,
/// свет 0.965…1. При «меньше движения» рисунок неподвижен.
class Breathing extends StatefulWidget {
  const Breathing({super.key, required this.child});

  final Widget child;

  @override
  State<Breathing> createState() => _BreathingState();
}

class _BreathingState extends State<Breathing>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 3400),
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      if (!still) _controller.repeat(reverse: true);
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
      builder: (context, child) {
        final t = Curves.easeInOut.transform(_controller.value);
        return Transform.scale(
          scale: 0.996 + t * 0.012,
          child: Opacity(opacity: 0.965 + t * 0.035, child: child),
        );
      },
      child: widget.child,
    );
  }
}
