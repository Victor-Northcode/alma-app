import 'dart:convert';

import 'package:alma/design/buttons.dart';
import 'package:alma/design/night_sheet.dart';
import 'package:alma/design/palette.dart';
import 'package:alma/design/wheel.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/screens/systems/pair_add_screen.dart';
import 'package:alma/screens/systems/people_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Лист выбора даты и времени: то в нём, что глазом на симуляторе видно, но
/// проверить нельзя.
///
/// Экран был «просто синим» — `showModalBottomSheet` с `night700` и голым
/// списком цифр. Здесь заперты те его свойства, которые ломаются молча:
/// **обе двери наружу** (тап по затемнению и свайп вниз — лист без выхода это
/// ловушка), **числа барабана** (полоса выбора и лестница яркости — то, чем
/// колесо анкеты отличается от списка) и **то, что экран совместимости зовёт
/// общую раму**, а не пишет себе третью.
///
/// С 19.08.2026 сюда же заперто **пустое состояние барабана**: лист открывается
/// серединой списка, а не первой строкой, и «Готово» не горит, пока значение не
/// названо. Обе половины правила проверяются только глазом — сломать их можно
/// одной строкой, и никакой другой тест этого не заметит.
void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  /// Пустая страница с одной кнопкой, открывающей лист.
  Widget host({int? value = 5, int min = 1, int max = 31}) => MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => Center(
              child: GestureDetector(
                onTap: () => showAlmaSheet<bool>(
                  context: context,
                  title: 'Date of birth',
                  builder: (context, refresh) => [
                    AlmaWheel(
                      label: 'Day',
                      min: min,
                      max: max,
                      value: value,
                      onChanged: (_) {},
                    ),
                  ],
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      );

  Future<void> open(WidgetTester tester) async {
    await tester.pumpWidget(host());
    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
  }

  /// Цвет канта полосы выбора.
  Color band(WidgetTester tester) => ((tester
          .widgetList<Container>(find.descendant(
              of: find.byType(AlmaWheel), matching: find.byType(Container)))
          .map((c) => c.decoration)
          .whereType<BoxDecoration>()
          .firstWhere((d) => d.border != null)
          .border!) as Border)
      .top
      .color;

  /// Стиль строки барабана по её тексту.
  TextStyle row(WidgetTester tester, String text) => tester
      .widget<Text>(find.descendant(
          of: find.byType(AlmaWheel), matching: find.text(text)))
      .style!;

  testWidgets('заголовок листа — засечный, как все заголовки продукта',
      (tester) async {
    await open(tester);
    final title = tester
        .widget<Text>(find.descendant(
            of: find.byType(AlmaSheet), matching: find.text('Date of birth')))
        .style!;
    expect(title.fontFamily, 'Playfair Display');
    expect(title.fontSize, 17.5, reason: 'ступень `headingM`, а не своя');
  });

  testWidgets('лист закрывается тапом по затемнению', (tester) async {
    await open(tester);
    expect(find.byType(AlmaSheet), findsOneWidget);
    // Верх экрана — там только затемнение: лист стоит внизу.
    await tester.tapAt(const Offset(400, 40));
    await tester.pumpAndSettle();
    expect(find.byType(AlmaSheet), findsNothing);
  });

  testWidgets('лист закрывается свайпом вниз', (tester) async {
    await open(tester);
    // Свайп берётся за шапку, а не за барабан: палец, начавший движение на
    // колесе, крутит колесо — и это правильно. Ради этого над барабанами и
    // стоят хват с заголовком.
    await tester.fling(
        find.descendant(
            of: find.byType(AlmaSheet), matching: find.text('Date of birth')),
        const Offset(0, 400),
        1200);
    await tester.pumpAndSettle();
    expect(find.byType(AlmaSheet), findsNothing);
  });

  testWidgets('при сокращённом движении лист уже на месте, а не едет',
      (tester) async {
    tester.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);

    await tester.pumpWidget(host());
    await tester.tap(find.text('open'));
    // Один кадр в двадцать миллисекунд: приезд листа длится 380 (`AlmaMotion
    // .sheet` тех же часов), и без «уменьшения движения» за это время он
    // проходит меньше десятой доли пути.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 20));

    final sheet = tester.getTopLeft(find.byType(AlmaSheet));
    final screen = tester.getSize(find.byType(MaterialApp)).height;
    expect(sheet.dy, lessThan(screen),
        reason: 'лист, который всё ещё едет снизу, стоит за краем экрана');
    expect(tester.getBottomLeft(find.byType(AlmaSheet)).dy, screen,
        reason: 'дно листа — дно экрана с первого же кадра');
  });

  group('барабан', () {
    testWidgets('выбранная строка светит слоновой костью, соседние — тусклее',
        (tester) async {
      await open(tester);
      // Лестница эталона: 1 → .55 → .4. Именно она делает столбик барабаном.
      expect(row(tester, '5').color, AlmaPalette.inkLight);
      expect(row(tester, '6').color,
          AlmaPalette.body.withValues(alpha: 0.55));
      expect(row(tester, '7').color, AlmaPalette.body.withValues(alpha: 0.4));
    });

    testWidgets('цифры засечные и того же кегля, что в анкете', (tester) async {
      await open(tester);
      expect(row(tester, '5').fontFamily, 'Playfair Display');
      expect(row(tester, '5').fontSize, 19);
    });

    testWidgets('полоса выбора — золото на 0.16, как у колеса анкеты',
        (tester) async {
      await open(tester);
      expect(band(tester), const Color(0x29C9AE6B));
    });

    testWidgets('без значения барабан открывается серединой списка',
        (tester) async {
      await tester.pumpWidget(host(value: null));
      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();
      // Середина 1..31 — шестнадцать, и над ней стоят две своих строки. Лист
      // открывался на «1», то есть половиной барабана, стоящей пустой: колонка
      // из пяти строк показывала три.
      for (final line in ['14', '15', '16', '17', '18']) {
        expect(find.descendant(of: find.byType(AlmaWheel), matching: find.text(line)),
            findsOneWidget);
      }
      expect(find.descendant(of: find.byType(AlmaWheel), matching: find.text('1')),
          findsNothing,
          reason: 'первая строка списка — не то, на чём барабан открывается');
    });

    testWidgets('невыбранный барабан весь на ступень тусклее, полоса погашена',
        (tester) async {
      await tester.pumpWidget(host(value: null));
      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();
      // Слоновой кости в невыбранном барабане нет вовсе: центральная строка
      // светит ровно как соседка выбранного.
      expect(row(tester, '16').color, AlmaPalette.body.withValues(alpha: 0.55));
      expect(row(tester, '17').color, AlmaPalette.body.withValues(alpha: 0.4));
      expect(row(tester, '18').color, AlmaPalette.body.withValues(alpha: 0.3));
      expect(band(tester), const Color(0x0FC9AE6B),
          reason: 'полоса зажигается вместе со значением, как в анкете');
    });
  });

  group('экран совместимости', () {
    Widget pairScreen() {
      final transport = MockClient((request) async => http.Response(
          jsonEncode(const <String, dynamic>{}), 200,
          headers: {'content-type': 'application/json'}));
      return SessionScope(
        session: AlmaSession(AlmaClient(
          baseUrl: Uri.parse('http://test.local'),
          http: transport,
        )),
        child: MaterialApp(
          locale: const Locale('en'),
          localizationsDelegates: L.localizationsDelegates,
          supportedLocales: L.supportedLocales,
          home: const PairAddScreen(),
        ),
      );
    }

    /// `pumpAndSettle` здесь невозможен: небо за анкетой движется бесконечно.
    Future<void> settle(WidgetTester tester) async {
      for (var i = 0; i < 12; i++) {
        await tester.pump(const Duration(milliseconds: 60));
      }
    }

    testWidgets('пилюля даты открывает общий лист с тремя барабанами',
        (tester) async {
      await tester.pumpWidget(pairScreen());
      await settle(tester);
      await tester.tap(find.text('Date of birth'));
      await settle(tester);

      expect(find.byType(AlmaSheet), findsOneWidget,
          reason: 'лист собирается общей рамой, а не заново на экране');
      expect(find.byType(AlmaWheel), findsNWidgets(3));
      // Заголовок листа — подпись пилюли, по которой постучали: пилюля и
      // заголовок дают два вхождения одной строки.
      expect(find.text('Date of birth'), findsNWidgets(2));

      final done = tester.widget<AlmaButton>(find.descendant(
          of: find.byType(AlmaSheet), matching: find.byType(AlmaButton)));
      expect(done.kind, AlmaButtonKind.gold,
          reason: 'единственное действие листа — золотое, как везде в продукте');
    });

    testWidgets('«Готово» не горит, пока дату не назвали', (tester) async {
      await tester.pumpWidget(pairScreen());
      await settle(tester);
      await tester.tap(find.text('Date of birth'));
      await settle(tester);

      final done = tester.widget<AlmaButton>(find.descendant(
          of: find.byType(AlmaSheet), matching: find.byType(AlmaButton)));
      expect(done.onTap, isNull,
          reason: 'нажатое без прокрутки «Готово» отправляло на сервер дату, '
              'которую никто не называл');
    });

    testWidgets('день кончается там же, где кончается видимый месяц',
        (tester) async {
      await tester.pumpWidget(pairScreen());
      await settle(tester);
      await tester.tap(find.text('Date of birth'));
      await settle(tester);

      final wheels = tester.widgetList<AlmaWheel>(find.byType(AlmaWheel));
      // Месяц не назван и стоит серединой — на июле; значит день считается по
      // июлю, а не по выдуманному числу.
      expect(wheels.map((w) => (w.min, w.max, w.value)),
          [(1, 31, null), (1, 12, null), (1900, DateTime.now().year, null)]);
      // Год открывается на «тридцати годах назад», как в анкете, а не на
      // середине ста двадцати шести лет.
      expect(wheels.last.fallback, DateTime.now().year - 30);
    });

    testWidgets('повёрнутый барабан отдаёт значение и зажигает свою полосу',
        (tester) async {
      await tester.pumpWidget(pairScreen());
      await settle(tester);
      await tester.tap(find.text('Date of birth'));
      await settle(tester);

      await tester.drag(find.byType(AlmaWheel).first, const Offset(0, -60));
      await settle(tester);

      final day = tester.widget<AlmaWheel>(find.byType(AlmaWheel).first);
      expect(day.value, isNotNull, reason: 'значение отдаёт палец');
      final done = tester.widget<AlmaButton>(find.descendant(
          of: find.byType(AlmaSheet), matching: find.byType(AlmaButton)));
      expect(done.onTap, isNull,
          reason: 'один барабан из трёх — это ещё не дата');
    });

    testWidgets('пилюля времени даёт часы с ведущим нулём и дорогу назад',
        (tester) async {
      await tester.pumpWidget(pairScreen());
      await settle(tester);
      await tester.tap(find.text('Time of birth'));
      await settle(tester);

      expect(find.byType(AlmaWheel), findsNWidgets(2));
      // Ноль впереди — свойство самой колонки, а не того, что видно в окне:
      // час открывается на 12, минуты на 30, и однозначных чисел в кадре нет.
      final hours = tester.widget<AlmaWheel>(find.byType(AlmaWheel).first);
      expect(hours.caption!(9), '09');
      expect(
          find.descendant(
              of: find.byType(AlmaWheel).last, matching: find.text('30')),
          findsOneWidget,
          reason: 'минуты открываются серединой списка, а не первой строкой');

      final buttons = tester
          .widgetList<AlmaButton>(find.descendant(
              of: find.byType(AlmaSheet), matching: find.byType(AlmaButton)))
          .toList();
      expect(buttons.map((b) => b.kind),
          [AlmaButtonKind.gold, AlmaButtonKind.veil],
          reason: 'ниже золотого «Готово» — тихий отказ от времени');
      expect(buttons.first.onTap, isNull,
          reason: 'время, названное наполовину, — опечатка, а не ответ');
      expect(buttons.last.onTap, isNotNull,
          reason: 'выключить обе кнопки значило бы запереть лист');
    });
  });

  /// Второй потребитель той же рамы — страница людей.
  ///
  /// Именно здесь дольше всего стоял `showModalBottomSheet` с
  /// `backgroundColor: night700` и `ListView` из `ListTile`: та самая плоская
  /// синяя плашка. Заперто то, что ломается молча: **лист вместо списка** и
  /// **когда число считается названным** — поворот барабана правит копию, а
  /// поле экрана меняет только «Готово».
  group('экран людей', () {
    Widget peopleScreen() {
      final transport = MockClient((request) async => http.Response(
          jsonEncode(const <String, dynamic>{}), 200,
          headers: {'content-type': 'application/json'}));
      return SessionScope(
        session: AlmaSession(AlmaClient(
          baseUrl: Uri.parse('http://test.local'),
          http: transport,
        )),
        child: MaterialApp(
          locale: const Locale('en'),
          localizationsDelegates: L.localizationsDelegates,
          supportedLocales: L.supportedLocales,
          home: const PeopleScreen(),
        ),
      );
    }

    /// Небо страницы дышит вечно — `pumpAndSettle` его не дождётся.
    Future<void> settle(WidgetTester tester) async {
      for (var i = 0; i < 12; i++) {
        await tester.pump(const Duration(milliseconds: 60));
      }
    }

    /// Открыть лист года. Год — единственная пилюля формы, чьё значение не
    /// спутать ни с чьим: день и месяц открываются на единице оба.
    Future<void> openYear(WidgetTester tester) async {
      await tester.pumpWidget(peopleScreen());
      await settle(tester);
      await tester.ensureVisible(find.text('1990'));
      await settle(tester);
      await tester.tap(find.text('1990'));
      await settle(tester);
    }

    /// Барабан листа и число, на котором он стоит.
    final wheel = find.byType(ListWheelScrollView);
    int atYear(WidgetTester tester) =>
        1900 +
        (tester.widget<ListWheelScrollView>(wheel).controller
                as FixedExtentScrollController)
            .selectedItem;

    testWidgets('число называют общей рамой, а не списком платформы',
        (tester) async {
      await openYear(tester);
      expect(find.byType(AlmaSheet), findsOneWidget,
          reason: 'лист собирается общей рамой, а не заново на экране');
      expect(find.byType(AlmaWheel), findsOneWidget);
      expect(find.byType(ListTile), findsNothing,
          reason: 'плоского списка цифр здесь больше нет');
      // Заголовок листа — подпись самой пилюли, и второй раз то же слово над
      // барабаном не печатается.
      expect(find.text('Year'), findsOneWidget);
      expect(find.text('YEAR'), findsNothing);
      expect(
          tester
              .widget<AlmaButton>(find.descendant(
                  of: find.byType(AlmaSheet),
                  matching: find.byType(AlmaButton)))
              .kind,
          AlmaButtonKind.gold,
          reason: 'единственное действие листа — золотое, как на W2');
    });

    testWidgets('«Готово» отдаёт то число, что стоит в полосе', (tester) async {
      await openYear(tester);
      await tester.drag(wheel, const Offset(0, -60));
      await settle(tester);
      final turned = atYear(tester);
      expect(turned, isNot(1990), reason: 'барабан провернули');

      await tester.tap(find.text('Done'));
      await settle(tester);
      expect(find.byType(AlmaSheet), findsNothing);
      expect(find.text('$turned'), findsOneWidget);
    });

    testWidgets('лист, закрытый мимо «Готово», поля не трогает',
        (tester) async {
      await openYear(tester);
      await tester.drag(wheel, const Offset(0, -60));
      await settle(tester);
      expect(atYear(tester), isNot(1990));

      // Верх экрана — затемнение: та же дверь наружу, что свайп вниз.
      await tester.tapAt(const Offset(400, 40));
      await settle(tester);
      expect(find.byType(AlmaSheet), findsNothing);
      expect(find.text('1990'), findsOneWidget,
          reason: 'поворот барабана — ещё не ответ, ответ даёт «Готово»');
    });
  });
}
