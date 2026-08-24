import 'package:alma/design/close_button.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/screens/legal/legal_screen.dart';
import 'package:alma/screens/legal/legal_text.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Выход с правового экрана — единый крестик, и цель у него не меньше 44.
///
/// История в два слоя. Сначала здесь стерёгся размер цели у текстовой «←»:
/// вокруг знака 18 стояли отбивки 4 × 6, цель выходила 26 × 40, и палец
/// промахивался на экране, где человеку показывают его же права. 24 августа
/// владелец снял сам зоопарк выходов («то крестик, то стрелочка, то слева, то
/// справа — сделай идентичным»), и выходом стал общий [AlmaClose] — крестик
/// справа, как у всех страниц, открытых поверх. Прежний тест упал на этой
/// правке ровно как положено; теперь стережётся новое правило: выход есть,
/// он единый и в него попадает палец.
void main() {
  testWidgets('выход с правового экрана — единый крестик с целью не меньше 44',
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

    final close = find.byType(AlmaClose);
    expect(close, findsOneWidget,
        reason: 'выход обязан быть общим AlmaClose, а не своей стрелкой');

    final box = tester.getSize(close);
    expect(box.width, greaterThanOrEqualTo(44),
        reason: 'цель выхода уже сорока четырёх точек — палец промахивается');
    expect(box.height, greaterThanOrEqualTo(44),
        reason: 'цель выхода ниже сорока четырёх точек');

    // Крестик стоит у правого канта — правило «закрыть — справа».
    final centre = tester.getCenter(close);
    expect(centre.dx, greaterThan(402 / 2),
        reason: 'закрытие поверх-экрана обязано стоять справа');
  });
}
