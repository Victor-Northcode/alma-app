import 'package:alma/design/invitation_pill.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Правила пилюли «Вся Alma» — те, которые нельзя проверить глазом.
///
/// Шесть секунд, одиннадцать секунд и полторы минуты руками на симуляторе не
/// отличить от «кажется, работает»; три показа за сессию требуют пяти минут
/// сидения перед экраном, а «три отказа подряд выключают навсегда» — трёх
/// запусков подряд. Здесь это секунды поддельных часов.
void main() {
  late List<({String name, Map<String, Object?> meta})> events;
  late void Function(String, Map<String, Object?>) realSink;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    events = [];
    realSink = PillEvents.sink;
    PillEvents.sink = (name, meta) => events.add((name: name, meta: meta));
  });

  tearDown(() => PillEvents.sink = realSink);

  /// Кабинет в пробирке: пилюля живёт в своей записи `Overlay` поверх пустой
  /// страницы — ровно так, как в оболочке.
  Widget cabinet(PillDirector director) => MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: Scaffold(
          body: Stack(
            children: [
              const SizedBox.expand(),
              Positioned.fill(
                child: Overlay(
                  initialEntries: [
                    OverlayEntry(
                        builder: (context) => PillLayer(director: director)),
                  ],
                ),
              ),
            ],
          ),
        ),
      );

  final pill = find.text('All of Alma');

  testWidgets('приходит на осевший экран, а не вместе с ним', (tester) async {
    final director = PillDirector();
    addTearDown(director.dispose);
    await tester.pumpWidget(cabinet(director));
    await tester.pump();
    director.surface = PillSurface.today;
    await tester.pump();

    // Пять секунд — экран ещё читают.
    await tester.pump(const Duration(seconds: 5));
    expect(pill, findsNothing);

    // Шестая секунда тишины — приглашение приходит.
    await tester.pump(const Duration(seconds: 2));
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsOneWidget);
    expect(events.single.name, 'pill_shown');
    expect(events.single.meta['surface'], 'today');
    expect(events.single.meta['session_count'], 1);

    // Одиннадцать секунд жизни и уход.
    await tester.pump(const Duration(seconds: 11));
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsNothing);
    expect(events.map((e) => e.name), contains('pill_expired'));
  });

  testWidgets('касание отодвигает приход — экран под пальцем не осел',
      (tester) async {
    final director = PillDirector();
    addTearDown(director.dispose);
    await tester.pumpWidget(cabinet(director));
    await tester.pump();
    director.surface = PillSurface.today;
    await tester.pump();

    for (var i = 0; i < 4; i++) {
      await tester.pump(const Duration(seconds: 5));
      director.stirred();
      await tester.pump();
      expect(pill, findsNothing, reason: 'палец на экране — приглашения нет');
    }
    await tester.pump(const Duration(seconds: 7));
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsOneWidget);
  });

  testWidgets('три показа за сессию и полторы минуты тишины между',
      (tester) async {
    final director = PillDirector();
    addTearDown(director.dispose);
    await tester.pumpWidget(cabinet(director));
    await tester.pump();
    director.surface = PillSurface.today;
    await tester.pump();

    for (var round = 1; round <= 3; round++) {
      await tester.pump(const Duration(seconds: 7));
      await tester.pump(const Duration(milliseconds: 400));
      expect(pill, findsOneWidget, reason: 'показ $round');
      // Пока не прошло полторы минуты, второго приглашения не бывает.
      await tester.pump(const Duration(seconds: 12));
      await tester.pump(const Duration(milliseconds: 400));
      expect(pill, findsNothing);
      await tester.pump(const Duration(seconds: 60));
      expect(pill, findsNothing, reason: 'минуты тишины мало, нужно полторы');
      await tester.pump(const Duration(seconds: 25));
      await tester.pump(const Duration(milliseconds: 400));
    }

    // Четвёртого не бывает: напоминание, повторённое четыре раза за пять
    // минут, — уже не напоминание.
    await tester.pump(const Duration(minutes: 5));
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsNothing);
    expect(events.where((e) => e.name == 'pill_shown').length, 3);
  });

  testWidgets('поверхность, сказавшая «не сейчас», молчит неделю',
      (tester) async {
    SharedPreferences.setMockInitialValues({
      'pill.notNowUntil.today':
          DateTime.now().add(const Duration(days: 3)).millisecondsSinceEpoch,
    });
    final director = PillDirector();
    addTearDown(director.dispose);
    await tester.pumpWidget(cabinet(director));
    await tester.pump();
    director.surface = PillSurface.today;
    await tester.pump(const Duration(seconds: 12));
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsNothing);

    // Отказ на «Сегодня» ничего не говорит о «Моих системах».
    director.surface = PillSurface.systems;
    await tester.pump(const Duration(seconds: 7));
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsOneWidget);
  });

  testWidgets('выключенная навсегда не приходит никогда', (tester) async {
    SharedPreferences.setMockInitialValues({'pill.retired': true});
    final director = PillDirector();
    addTearDown(director.dispose);
    await tester.pumpWidget(cabinet(director));
    await tester.pump();
    director.surface = PillSurface.today;
    await tester.pump(const Duration(minutes: 4));
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsNothing);
    expect(events, isEmpty);
  });

  testWidgets('покупка выключает приглашение и запоминает это', (tester) async {
    final director = PillDirector();
    addTearDown(director.dispose);
    await tester.pumpWidget(cabinet(director));
    await tester.pump();
    director.surface = PillSurface.today;
    await tester.pump(const Duration(seconds: 7));
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsOneWidget);

    // Звать заплатившего купить — не продажа, а сообщение о том, что мы не
    // знаем, кто перед нами.
    director.bought = true;
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsNothing);
    expect(
      events.where((e) => e.name == 'pill_retired').single.meta['reason'],
      'purchase',
    );
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getBool('pill.retired'), isTrue);
  });

  testWidgets('смена поверхности не переносит показ на новый экран',
      (tester) async {
    final director = PillDirector();
    addTearDown(director.dispose);
    await tester.pumpWidget(cabinet(director));
    await tester.pump();
    director.surface = PillSurface.today;
    await tester.pump(const Duration(seconds: 5));
    // Ушли, не досчитав. Досчитывать чужие секунды на другом экране нельзя.
    director.surface = PillSurface.systems;
    await tester.pump(const Duration(seconds: 3));
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsNothing);
    await tester.pump(const Duration(seconds: 4));
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsOneWidget);
    expect(events.single.meta['surface'], 'systems');
  });

  testWidgets('на чужой поверхности не приходит вовсе', (tester) async {
    final director = PillDirector();
    addTearDown(director.dispose);
    await tester.pumpWidget(cabinet(director));
    await tester.pump();
    // Пергамент главы, витрина, настройки, беседа — оболочка говорит `null`.
    director.surface = null;
    await tester.pump(const Duration(minutes: 3));
    await tester.pump(const Duration(milliseconds: 400));
    expect(pill, findsNothing);
    expect(events, isEmpty);
  });
}
