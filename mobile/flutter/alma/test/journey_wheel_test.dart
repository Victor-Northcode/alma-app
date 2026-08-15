import 'dart:convert';

import 'package:alma/design/buttons.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/screens/journey/journey_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// Колесо даты не вправе отдавать значение, которого не выбирали.
///
/// **Тест про данные, а не про красоту.** На шаге даты барабан стоит на
/// каком-то числе с первого кадра — иначе верхняя половина колонки пустая.
/// Если это число считать выбранным, каждый, кто прокрутил шаг мимо, уезжает
/// с чужой датой рождения, а от неё зависят все восемь систем — от солнечного
/// знака до числа жизненного пути. Натив ради этого отказался от колеса вовсе
/// (`JourneyControls.swift:145`); порт колесо вернул по дизайн-проекту и обязан
/// держать то же правило другим способом.
void main() {
  Widget host() {
    final transport = MockClient((request) async => http.Response(
        jsonEncode(const <String, dynamic>{}), 200,
        headers: {'content-type': 'application/json'}));
    return SessionScope(
      session: AlmaSession(AlmaClient(
        baseUrl: Uri.parse('http://test.local'),
        http: transport,
      )),
      child: MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: JourneyScreen(onDone: () {}),
      ),
    );
  }

  /// **`pumpAndSettle` здесь не работает и работать не может**: небо за
  /// анкетой движется бесконечно, а `pumpAndSettle` ждёт кадра, после которого
  /// анимаций не осталось. Поэтому кадры отсчитываются вручную — их хватает,
  /// чтобы барабан доехал до упора и отдал значение.
  Future<void> settle(WidgetTester tester) async {
    for (var i = 0; i < 12; i++) {
      await tester.pump(const Duration(milliseconds: 60));
    }
  }

  /// Нижняя кнопка шага. Её `onTap` — единственный внешний признак того,
  /// засчитана дата или нет.
  bool forwardEnabled(WidgetTester tester) =>
      tester.widget<AlmaButton>(find.byType(AlmaButton).last).onTap != null;

  /// Довести анкету до шага даты: имя и «о себе» кнопку не запирают.
  Future<void> toDateStep(WidgetTester tester) async {
    await tester.pumpWidget(host());
    await settle(tester);
    for (var i = 0; i < 2; i++) {
      await tester.tap(find.byType(AlmaButton).last);
      await settle(tester);
    }
    expect(find.byType(ListWheelScrollView), findsNWidgets(3),
        reason: 'шаг даты: день, месяц, год');
  }

  testWidgets('нетронутые колёса не пускают дальше', (tester) async {
    await toDateStep(tester);
    expect(forwardEnabled(tester), isFalse,
        reason: 'дата, которую никто не выбирал, не должна засчитываться');
  });

  testWidgets('одного повёрнутого колеса мало — нужны все три', (tester) async {
    await toDateStep(tester);
    await tester.drag(
        find.byType(ListWheelScrollView).first, const Offset(0, -60));
    await settle(tester);
    expect(forwardEnabled(tester), isFalse,
        reason: 'выбран только день; месяц и год по-прежнему не тронуты');
  });

  testWidgets('три поворота открывают дорогу', (tester) async {
    await toDateStep(tester);
    for (final wheel in find.byType(ListWheelScrollView).evaluate().toList()) {
      await tester.drag(find.byWidget(wheel.widget), const Offset(0, -60));
      await settle(tester);
    }
    expect(forwardEnabled(tester), isTrue);
  });

  testWidgets('поворот туда и обратно выбирает ту же строку, что видна',
      (tester) async {
    // Человеку, которому подошло стоящее в полосе число, деваться некуда:
    // нетронутое колесо ничего не отдаёт. Значит возврат на своё же значение
    // обязан его засчитать — иначе такую дату не выбрать вовсе.
    await toDateStep(tester);
    final day = find.byType(ListWheelScrollView).first;
    await tester.drag(day, const Offset(0, -60));
    await settle(tester);
    await tester.drag(day, const Offset(0, 60));
    await settle(tester);

    final wheel = tester.widget<ListWheelScrollView>(day);
    expect(wheel.controller, isA<FixedExtentScrollController>());
    expect((wheel.controller as FixedExtentScrollController).selectedItem, 15,
        reason: 'вернулись на середину списка — шестнадцатое число');
  });

  testWidgets('уход с шага и возврат не подменяют дату', (tester) async {
    // **Регрессия, найденная руками на симуляторе.** Колёса не имели ключей, и
    // Flutter переиспользовал состояние: барабан часов, возвращаясь, оказывался
    // барабаном дня — со своим смещением. На шаге даты после «назад» стояло
    // «6 января 1925» с горящей кнопкой «дальше»: дата, которую никто не
    // называл, готовая уехать на сервер и лечь в основание восьми систем.
    await toDateStep(tester);
    for (final wheel in find.byType(ListWheelScrollView).evaluate().toList()) {
      await tester.drag(find.byWidget(wheel.widget), const Offset(0, -60));
      await settle(tester);
    }
    expect(forwardEnabled(tester), isTrue);
    final chosen = _centres(tester);

    await tester.tap(find.byType(AlmaButton).last); // на шаг времени
    await settle(tester);
    expect(find.byType(ListWheelScrollView), findsNWidgets(2),
        reason: 'время: часы и минуты');

    await tester.tap(find.byIcon(Icons.arrow_back)); // и обратно на дату
    await settle(tester);
    expect(find.byType(ListWheelScrollView), findsNWidgets(3));
    expect(_centres(tester), chosen,
        reason: 'вернулись к своей дате, а не к чужому смещению');
    expect(forwardEnabled(tester), isTrue);
  });

  testWidgets('нетронутые колёса остаются нетронутыми и после возврата',
      (tester) async {
    await toDateStep(tester);
    expect(forwardEnabled(tester), isFalse);
    // Уйти можно только назад: вперёд без даты не пускают — в этом и смысл.
    await tester.tap(find.byIcon(Icons.arrow_back));
    await settle(tester);
    await tester.tap(find.byType(AlmaButton).last);
    await settle(tester);
    expect(find.byType(ListWheelScrollView), findsNWidgets(3));
    expect(forwardEnabled(tester), isFalse,
        reason: 'барабан, доехавший сам, — это не выбор человека');
  });
}

/// Какие строки стоят в полосе выбора у всех колёс шага.
List<int> _centres(WidgetTester tester) => tester
    .widgetList<ListWheelScrollView>(find.byType(ListWheelScrollView))
    .map((w) => (w.controller as FixedExtentScrollController).selectedItem)
    .toList();
