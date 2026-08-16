import 'dart:math' as math;
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../l10n/alma_l10n.dart';
import 'metrics.dart';
import 'palette.dart';

/// Четыре вкладки кабинета.
enum CabinetTab {
  today,
  systems,
  alma,
  settings;

  String title(L l) => switch (this) {
        CabinetTab.today => l.tabToday,
        CabinetTab.systems => l.tabSystems,
        CabinetTab.alma => l.tabAlma,
        CabinetTab.settings => l.tabSettings,
      };
}

/// Нижний бар: плита ночи на 94% поверх размытия, одна золотая волосяная линия
/// сверху, погашенные глифы на 50%.
///
/// Порт `mobile/ios/Alma/Navigation/CabinetTabBar.swift`.
class CabinetTabBar extends StatelessWidget {
  const CabinetTabBar({
    super.key,
    required this.current,
    required this.onSelect,
  });

  final CabinetTab current;
  final ValueChanged<CabinetTab> onSelect;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final bottomInset = MediaQuery.paddingOf(context).bottom;

    return ValueListenableBuilder<bool>(
      valueListenable: readingNow,
      builder: (context, reading, _) => _bar(context, l, bottomInset, reading),
    );
  }

  Widget _bar(BuildContext context, L l, double bottomInset, bool reading) {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: DecoratedBox(
          // **Бар не блок, а край страницы.**
          //
          // Плотная заливка с золотой чертой поверху делала из него отдельную
          // панель, приклеенную к низу каждого экрана — «как будто отделён, а
          // нужно лаконичнее». Заливка стала прозрачной к верху и уходит в
          // страницу, черты нет вовсе: размытие держит подписи читаемыми над
          // любым текстом, а край растворяется.
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: reading
                  ? [
                      AlmaPalette.parchmentB.withValues(alpha: 0),
                      AlmaPalette.parchmentB.withValues(alpha: 0.90),
                      AlmaPalette.parchmentB.withValues(alpha: 0.96),
                    ]
                  : [
                      AlmaPalette.night850.withValues(alpha: 0),
                      AlmaPalette.night850.withValues(alpha: 0.90),
                      AlmaPalette.night850.withValues(alpha: 0.96),
                    ],
              stops: const [0, 0.30, 1],
            ),
          ),
          // **Завеса выше самого бара, и это лечит «срезанную строку».**
          //
          // Градиент начинался прозрачным ровно по верхней кромке подписей и
          // за 55% высоты доходил до плотного: строка списка, попавшая в эти
          // полсотни точек, оказывалась разрезанной пополам — сверху видна,
          // снизу нет. Читалось поломкой, а не глубиной.
          //
          // Растворение осталось, но плотность набирается втрое быстрее: за
          // первые 30% высоты вместо 55%. Верхние двадцать точек — по-прежнему
          // мягкий переход, дальше подписи стоят на своей земле, и строка под
          // ними уходит в ночь целиком, а не пополам.
          child: Padding(
            padding: EdgeInsets.only(bottom: bottomInset),
            child: SizedBox(
              height: AlmaMetrics.tabBarHeight,
              child: Row(
                children: [
                  for (final tab in CabinetTab.values)
                    Expanded(
                      child: _TabButton(
                        tab: tab,
                        active: tab == current,
                        label: tab.title(l),
                        onTap: () => onSelect(tab),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _TabButton extends StatelessWidget {
  const _TabButton({
    required this.tab,
    required this.active,
    required this.label,
    required this.onTap,
  });

  final CabinetTab tab;
  final bool active;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    // На пергаменте золото читается, а бледно-серые подписи тонут: неактивные
    // становятся чернилами страницы.
    final reading = readingNow.value;
    final colour = active
        ? (reading ? AlmaPalette.goldDeep : AlmaPalette.gold)
        : (reading ? AlmaPalette.inkMuted : AlmaPalette.muted3);
    return Semantics(
      selected: active,
      button: true,
      label: label,
      child: InkResponse(
        onTap: onTap,
        highlightColor: Colors.transparent,
        splashColor: Colors.transparent,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            SizedBox(
              width: 22,
              height: 22,
              child: CustomPaint(painter: _TabGlyph(tab: tab, active: active)),
            ),
            const SizedBox(height: 3),
            // Подпись тише, чем казалось по коду: на нативном баре она 10
            // пунктов обычного веса, и активная не жирнеет — её выделяет
            // золото. Сверено бок о бок; крупная жирная подпись делала бар
            // тяжелее всего экрана.
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 10, letterSpacing: 0.2, color: colour),
            ),
          ],
        ),
      ),
    );
  }
}

/// Четыре глифа, нарисованные путями.
///
/// **Не системные иконки.** Солнце, шестерёнка и сетка кругов — это иконки
/// любого приложения на телефоне, а солнце вдобавок сказало бы «погода». Это
/// глифы веб-приложения: маленькое солнце с четырьмя лучами для Сегодня, два
/// концентрических круга для восьми систем, собственная тёплая точка света для
/// Alma и знак настроек без шестерёнки — точка с шестью короткими штрихами.
class _TabGlyph extends CustomPainter {
  _TabGlyph({required this.tab, required this.active});

  final CabinetTab tab;
  final bool active;

  @override
  void paint(Canvas canvas, Size size) {
    final reading = readingNow.value;
    final colour = active
        ? (reading ? AlmaPalette.goldDeep : AlmaPalette.gold)
        : (reading ? AlmaPalette.inkMuted : AlmaPalette.body.withValues(alpha: 0.5));
    final stroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.25
      ..strokeCap = StrokeCap.round
      ..color = colour;
    final c = Offset(size.width / 2, size.height / 2);

    switch (tab) {
      case CabinetTab.alma:
        // Alma никогда не линия. Она — тёплая точка света, на том единственном
        // размере, где кольцо снимается.
        final glow = Paint()
          ..shader = RadialGradient(
            colors: [
              AlmaPalette.starFill.withValues(alpha: active ? 1.0 : 0.65),
              AlmaPalette.gold.withValues(alpha: active ? 0.5 : 0.3),
              const Color(0x00000000),
            ],
            stops: const [0.0, 0.45, 1.0],
          ).createShader(Rect.fromCircle(center: c, radius: size.width * 0.42));
        canvas.drawCircle(c, size.width * 0.42, glow);

      case CabinetTab.today:
        final r = size.width * 0.1667;
        canvas.drawCircle(c, r, stroke);
        for (var angle = 0.0; angle < 360; angle += 90) {
          final rad = angle * math.pi / 180;
          final inner = size.width * 0.34;
          final outer = size.width * 0.46;
          canvas.drawLine(
            c + Offset(math.cos(rad) * inner, math.sin(rad) * inner),
            c + Offset(math.cos(rad) * outer, math.sin(rad) * outer),
            stroke,
          );
        }

      case CabinetTab.systems:
        for (final r in [size.width * 0.375, size.width * 0.1333]) {
          canvas.drawCircle(c, r, stroke);
        }

      case CabinetTab.settings:
        canvas.drawCircle(c, size.width * 0.125, stroke);
        for (var angle = 30.0; angle < 360; angle += 60) {
          final rad = angle * math.pi / 180;
          final inner = size.width * 0.29;
          final outer = size.width * 0.42;
          canvas.drawLine(
            c + Offset(math.cos(rad) * inner, math.sin(rad) * inner),
            c + Offset(math.cos(rad) * outer, math.sin(rad) * outer),
            stroke,
          );
        }
    }
  }

  @override
  bool shouldRepaint(covariant _TabGlyph old) => old.active != active || old.tab != tab;
}
