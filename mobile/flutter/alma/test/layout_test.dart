import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:alma/design/layout.dart';

/// Свод адаптивных правил проверяется числами, а не на глаз.
///
/// Эти величины продиктованы владельцем и в архиве дизайна их нет — значит
/// единственное место, где они записаны, это `layout.dart`, и единственное,
/// что не даст им тихо разъехаться, — этот файл.
void main() {
  group('полосы ширины', () {
    test('≤380 — compact, и всё сжимается по своду', () {
      final l = AlmaLayout.resolve(375);
      expect(l.band, AlmaBand.compact);
      expect(l.pad, 18);
      expect(l.hero, 33);
      expect(l.title, 26);
      expect(l.medallion, 68);
      expect(l.tabBar, 72);
      expect(l.plateScale, closeTo(0.82, 0.001), reason: 'вклейка ниже на 18%');
      expect(l.hasRail, isFalse);
    });

    test('402 — эталон дизайна, все S-экраны нарисованы здесь', () {
      final l = AlmaLayout.resolve(402);
      expect(l.band, AlmaBand.phone);
      expect(l.pad, 22);
      expect(l.hero, 39);
      expect(l.title, 29);
      expect(l.medallion, 86);
      expect(l.tabBar, 84);
      expect(l.hasRail, isFalse);
    });

    test('380 и 381 — граница compact ровно там, где сказано', () {
      expect(AlmaLayout.resolve(380).band, AlmaBand.compact);
      expect(AlmaLayout.resolve(381).band, AlmaBand.phone);
    });

    test('≥744 книжная — рейл слева, низ пуст, колонка 560', () {
      final l = AlmaLayout.resolve(768);
      expect(l.band, AlmaBand.tabletPortrait);
      expect(l.railWidth, 92);
      expect(l.tabBar, 0, reason: 'нижнего бара на планшете нет');
      expect(l.hasRail, isTrue);
      expect(l.column, 560);
      expect(l.deckColumns, 3);
      expect(l.dialogMax, 420);
      expect(l.title, 33, reason: 'титулы на шаг вверх');
      expect(l.hero, 44);
    });

    test('≥1024 альбомная — разворот и двухпанельные рисунки', () {
      final l = AlmaLayout.resolve(1180);
      expect(l.band, AlmaBand.tabletLandscape);
      expect(l.isSpread, isTrue);
      expect(l.railWidth, 92);
      expect(l.column, 560);
    });

    test('743 ещё телефон, 744 уже планшет', () {
      expect(AlmaLayout.resolve(743).hasRail, isFalse);
      expect(AlmaLayout.resolve(744).hasRail, isTrue);
    });

    test('колонка не растягивается шире 560 ни на какой ширине планшета', () {
      for (final w in [744.0, 834.0, 1024.0, 1366.0, 2048.0]) {
        expect(AlmaLayout.resolve(w).column, 560, reason: 'ширина $w');
      }
    });
  });

  group('полы ужатия', () {
    test('у кнопки свой пол 14, а не общий 11', () {
      expect(AlmaShrink.buttonFloor, 14);
      expect(AlmaShrink.buttonSteps.first, 16.5);
      expect(AlmaShrink.buttonSteps.last, AlmaShrink.buttonFloor);
    });

    test('подписи вкладок 10 → 9', () {
      expect(AlmaShrink.tabLabel, 10);
      expect(AlmaShrink.tabLabelFloor, 9);
    });

    test('юридические строки 12.5 → 11', () {
      expect(AlmaShrink.legal, 12.5);
      expect(AlmaShrink.legalFloor, 11);
    });

    test('тело не ужимается никогда', () {
      expect(AlmaShrink.bodyFixed, 15.5);
    });
  });

  group('правила языка', () {
    test('кириллический капс получает разрядку 1.8, латинский 2.5', () {
      expect(AlmaLocaleRules.capsTracking('МОИ СИСТЕМЫ'), 1.8);
      expect(AlmaLocaleRules.capsTracking('MY SYSTEMS'), 2.5);
    });

    test('решает строка, а не локаль: Alma в русском интерфейсе латиницей', () {
      expect(AlmaLocaleRules.capsTracking('ALMA'), 2.5);
      expect(AlmaLocaleRules.capsTracking('ГОРОСКОП НА СЕГОДНЯ'), 1.8);
    });

    test('смешанная строка считается кириллической', () {
      expect(AlmaLocaleRules.capsTracking('ВСЯ ALMA'), 1.8);
    });
  });

  testWidgets('of() читает ширину из дерева', (tester) async {
    late AlmaLayout seen;
    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(size: Size(768, 1024)),
        child: Builder(builder: (context) {
          seen = AlmaLayout.of(context);
          return const SizedBox();
        }),
      ),
    );
    expect(seen.band, AlmaBand.tabletPortrait);
  });
}
