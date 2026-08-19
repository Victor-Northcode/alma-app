import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/screens/legal/legal_screen.dart';
import 'package:alma/screens/legal/legal_text.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Цель нажатия у «←» правового экрана.
///
/// **Единственная в продукте, которая была ниже сорока четырёх точек.**
/// Остальные шапки держат 44 прямым числом (`system_screen`, `chapter_screen`,
/// шапки витрин); здесь вокруг знака 18 стояли отбивки 4 × 6, то есть цель
/// 26 × 40. Разница не косметическая: сорок четыре — это минимум, ниже которого
/// палец промахивается, и промахивается он на экране, где человеку показывают
/// его же права и единственный выход с которого — эта стрелка (экран открыт
/// `CupertinoPageRoute` без панели).
void main() {
  testWidgets('цель «назад» на правовом экране не меньше сорока четырёх точек',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(402, 874));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const MaterialApp(
      localizationsDelegates: L.localizationsDelegates,
      supportedLocales: L.supportedLocales,
      home: LegalScreen(document: LegalDocument.privacy),
    ));
    // Не `pumpAndSettle`: небо каркаса анимировано непрерывно, и ждать его
    // покоя значит ждать вечно. Но и двух кадров мало: каскад появления
    // (`design/arrival.dart`) ставит по таймеру на блок, а тест, кончившийся
    // раньше них, падает на «pending timers» — не по существу проверки.
    for (var i = 0; i < 12; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    final arrow = find.text('←');
    expect(arrow, findsOneWidget);

    final target = find.ancestor(
      of: arrow,
      matching: find.byType(GestureDetector),
    ).first;
    final box = tester.getSize(target);
    expect(box.width, greaterThanOrEqualTo(44),
        reason: 'цель «назад» уже сорока четырёх точек — палец промахивается');
    expect(box.height, greaterThanOrEqualTo(44),
        reason: 'цель «назад» ниже сорока четырёх точек');

    // И знак при этом остался на поле страницы, а не уехал в середину цели:
    // цель растёт наружу, рисунок стоит на месте.
    expect(tester.getTopLeft(arrow).dx, lessThan(tester.getTopLeft(target).dx + 8),
        reason: 'знак съехал вправо от поля страницы вместе с ростом цели');

    // Кегль знака — тот же 18, что у «←» остальных шапок: цель выросла, знак нет.
    expect(tester.widget<Text>(arrow).style?.fontSize, 18);
  });
}
