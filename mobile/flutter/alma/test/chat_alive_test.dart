import 'dart:convert';

import 'package:alma/design/alma_presence.dart';
import 'package:alma/design/arrival.dart';
import 'package:alma/design/tab_bar.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/screens/alma/alma_screen.dart';
import 'package:alma/screens/alma/chat_turn.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Беседа обязана быть живой, и живость проверяется по кадрам.**
///
/// Три вещи, каждая из которых один раз уже была написана и не подключена:
/// свет не откликался на отправленный вопрос, своя реплика возникала рывком,
/// а первая строка ответа вставала в одном кадре с шапкой — то есть обещание
/// «сперва источник, потом речь» держалось со второй строки.
///
/// Числа здесь не выдуманы: они из `docs/design/handoff_all_screens/chat-spec.md`
/// (§1 наклон +15 % за 240 мс, §2 A3 «источник первым», §4 словарь движения) и
/// из перенесённого `Arrival.swift` — подъём 16 точек за 0.55 с.
///
/// `pumpAndSettle` нигде: свет Alma дышит вечно, и ждать конца анимаций значит
/// ждать всегда. Кадры отсчитываются руками.

/// Сервер в пробирке: ответ на вопрос приходит **не сразу**. Пауза здесь и
/// есть предмет проверки — всё время, пока вопрос в пути, свет держит наклон.
AlmaClient chatClient({Duration answersAfter = const Duration(seconds: 2)}) {
  final http.Client transport = MockClient((request) async {
    if (request.url.path == '/v1/chat') {
      await Future<void>.delayed(answersAfter);
      return http.Response(
          jsonEncode({
            'thread_id': 'th1',
            'message': {
              'body': 'Your sun lives in the fourth house.',
              'turn_kind': 'reading',
              'cited_factors': ['sun 17°46′ ♓︎ · house 4'],
            },
            'questions_left': 2,
          }),
          200,
          headers: {'content-type': 'application/json'});
    }
    Map<String, dynamic> body;
    if (request.url.path == '/v1/auth/refresh') {
      body = {'token': 't1', 'user_id': 'u1', 'is_guest': true, 'locale': 'en'};
    } else {
      body = {};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

/// Ответ длиной в несколько строк вёрстки — иначе каскаду нечего разносить.
const _answer =
    'Your Sun lives in the fourth house — the self is built at home, not in '
    'public. What reads as secrecy from outside is the placement keeping its '
    'workshop closed while the work is unfinished.';

Widget _frame(Widget child) => MaterialApp(
      locale: const Locale('en'),
      localizationsDelegates: L.localizationsDelegates,
      supportedLocales: L.supportedLocales,
      home: Scaffold(
        body: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 22),
          child: SingleChildScrollView(child: child),
        ),
      ),
    );

/// Прозрачность ближайшего [Opacity] над найденным — то, чем в этом файле
/// меряется вход: и шапка, и строки каскада, и пузырь своей реплики держатся
/// ровно на нём.
double _fade(WidgetTester tester, Finder of) => tester
    .widget<Opacity>(find.ancestor(of: of, matching: find.byType(Opacity)).first)
    .opacity;

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    // Связка в пробирке: без неё первый же `read()` не отвечает никогда.
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('свет наклоняется на отправленный вопрос и переживает отправку',
      (tester) async {
    tester.view.physicalSize = const Size(402, 874) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(MaterialApp(
      locale: const Locale('en'),
      localizationsDelegates: L.localizationsDelegates,
      supportedLocales: L.supportedLocales,
      // Материал — то, на чём в оболочке стоит вкладка: без него `TextField`
      // композера не строится вовсе.
      home: Material(
        child: SessionScope(
          session: AlmaSession(chatClient()),
          child: AlmaScreen(tabs: TabsPeek()),
        ),
      ),
    ));
    await tester.pump();

    // A1: свет один на экране, спокоен и не наклонён.
    expect(find.byType(AlmaPresence), findsOneWidget,
        reason: 'в приветствии свет ровно один');
    expect(tester.widget<AlmaPresence>(find.byType(AlmaPresence)).tilt, 0);
    // Тот самый экземпляр: если он умрёт на отправке, наклонять будет нечего.
    final light = tester.state<State>(find.byType(AlmaPresence));

    await tester.enterText(
        find.byType(TextField), 'Why do I guard my private life so hard?');
    await tester.testTextInput.receiveAction(TextInputAction.send);
    // Кадр отправки: приветствие сменилось лентой — ровно тот кадр, в котором
    // прежний свет снимался с дерева посреди анимации.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.byType(AlmaPresence), findsOneWidget,
        reason: 'в думании свет по-прежнему один — думание своего не заводит');
    expect(identical(tester.state<State>(find.byType(AlmaPresence)), light),
        isTrue,
        reason: 'свет обязан быть тем же: он живёт выше обоих состояний');

    final tilting = tester.widget<AlmaPresence>(find.byType(AlmaPresence));
    expect(tilting.tilt, greaterThan(0), reason: 'наклон не подключён');
    expect(tilting.tilt, lessThan(1), reason: '240 мс, а не один кадр');
    expect(tilting.mood, PresenceMood.thinking);

    // §1 и §4: наклон целиком укладывается в 240 мс.
    await tester.pump(const Duration(milliseconds: 200));
    expect(tester.widget<AlmaPresence>(find.byType(AlmaPresence)).tilt, 1);

    // Ответ приезжает, наклон отпускается; кадры досчитываются, чтобы тест не
    // кончился раньше собственных часов.
    await tester.pump(const Duration(seconds: 2));
    for (var i = 0; i < 40; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }
    expect(find.text('READ FROM'), findsOneWidget, reason: 'ответ не приехал');
    // Она ответила — наклон отпущен. Свет каркаса узнаётся по росту: в осевшей
    // ленте рядом стоит ещё один, шапочный, и он принадлежит ответу.
    final released = tester
        .widgetList<AlmaPresence>(find.byType(AlmaPresence))
        .firstWhere((light) => light.size == AlmaPresence.greeting);
    expect(released.tilt, 0, reason: 'наклон не отпущен после ответа');
  });

  testWidgets('своя реплика входит проявлением и подъёмом, а не рывком',
      (tester) async {
    tester.view.physicalSize = const Size(402, 874) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    const question = 'Why do I guard my private life so hard?';
    await tester.pumpWidget(
        _frame(const ChatTurnView(mine: true, body: question)));
    // Вход ставится нулевым таймером (каскад `RiseIn` считает ступени), а
    // `pump()` без длительности таймеры не двигает вовсе — миллисекунда нужна,
    // чтобы часы вообще пошли.
    await tester.pump(const Duration(milliseconds: 1));

    expect(_fade(tester, find.text(question)), lessThan(1),
        reason: 'пузырь появился готовым — входа нет');
    final risen = tester.getTopLeft(find.text(question)).dy;

    await tester.pump(AlmaArrive.duration + const Duration(milliseconds: 40));
    expect(_fade(tester, find.text(question)), 1);
    final seated = tester.getTopLeft(find.text(question)).dy;
    // Подъём 16 точек — число `Arrival.swift`, а не своё.
    expect(risen - seated, closeTo(AlmaArrive.rise, 0.5));
  });

  testWidgets('шапка ответа встаёт раньше первой строки речи', (tester) async {
    tester.view.physicalSize = const Size(402, 874) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_frame(const ChatTurnView(
      mine: false,
      arriving: true,
      citedFactors: ['sun 17°46′ ♓︎ · house 4'],
      body: _answer,
    )));
    await tester.pump();

    // Первая строка речи — первый кусок, вымеренный каскадом: его текст и есть
    // начало ответа.
    String? opening;
    for (final text in tester.widgetList<Text>(find.byType(Text))) {
      final data = text.data;
      if (data != null && data.length > 8 && _answer.startsWith(data)) {
        opening = data;
        break;
      }
    }
    expect(opening, isNotNull, reason: 'тело ответа не нарисовалось');

    final header = find.text('ALMA');
    // Кадр рождения: не встало ещё ничего, а первая строка тлеет — A3.
    expect(_fade(tester, header), 0);
    expect(_fade(tester, find.text(opening!)), lessThan(0.3));

    // §4: шапка с цитатой проявляется 240 мс…
    await tester.pump(const Duration(milliseconds: 240));
    expect(_fade(tester, header), 1, reason: 'шапка не доехала за свои 240 мс');
    expect(find.text('READ FROM'), findsOneWidget);
    // …и речь всё ещё не встала: это и есть «сперва источник, потом речь».
    expect(_fade(tester, find.text(opening)), lessThan(1),
        reason: 'первая строка встала вместе с шапкой');

    // Каскад доигрывает — и тогда речь на месте.
    for (var i = 0; i < 30; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }
    expect(_fade(tester, find.text(opening)), 1);
  });
}
