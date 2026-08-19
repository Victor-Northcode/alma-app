import 'dart:async';
import 'dart:convert';

import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/net/models.dart';
import 'package:alma/screens/systems/chapter_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Жест перелистывания, прогнанный настоящей физикой.
///
/// В браузере мышь не тянет прокрутку, на устройстве нужен палец — а здесь
/// тестовый привод честно тащит BouncingScrollPhysics, так что оба порога
/// проверяются с той же задемпфированной дотяжкой, что у настоящего жеста.
AlmaClient chapterClient() {
  final transport = MockClient((request) async {
    final path = request.url.path;
    Object body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't', 'user_id': 'u', 'is_guest': true, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {'id': 'u', 'locale': 'en', 'is_guest': true, 'created_at': '', 'unlocked': []};
    } else if (path == '/v1/profiles') {
      body = [
        {'id': 'p1', 'is_self': true, 'birth_date': '1992-05-11',
         'latitude': 55.75, 'longitude': 37.62, 'timezone': 'Europe/Moscow'}
      ];
    } else if (path.endsWith('/chapters')) {
      body = {
        'system': 'numerology',
        'total': 2,
        'chapters': [
          {'slug': 'life-path', 'numeral': 'I', 'index': 1, 'title': 'Жизненный путь',
           'question': '', 'free': true, 'open': true, 'written': true, 'needs_birth_time': false},
          {'slug': 'birthday-number', 'numeral': 'II', 'index': 2, 'title': 'Число дня',
           'question': '', 'free': false, 'open': true, 'written': true, 'needs_birth_time': false},
        ],
      };
    } else if (path == '/v1/readings') {
      final payload = jsonDecode(request.body) as Map<String, dynamic>;
      final chapter = payload['chapter'] as String;
      body = {
        'reading': {
          'system': 'numerology', 'chapter': chapter,
          'title': chapter == 'life-path' ? 'Первая' : 'Вторая',
          'teaser': '',
          'body': List.generate(30, (i) => 'Абзац $i главы $chapter, достаточно длинный, чтобы страница прокручивалась и имела настоящее дно.'),
          'cited_factors': [], 'read_from': '', 'model': 'test',
        },
        'cached': true,
      };
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

/* ── стенд протяжки ────────────────────────────────────────────────────── */

/// Что сервер отдал и о чём его спросили — на этом держатся все проверки
/// перехода: главу называет **запрос**, а не только текст на экране.
class Wire {
  final List<String> asked = [];
  final List<Map<String, dynamic>> events = [];
  int chapterLists = 0;

  /// Слаги оглавления. Второй вызов может ответить другим списком — так
  /// проверяется перечитывание оглавления под ногами у жеста.
  List<List<String>> listings = const [];

  /// Оглавления по системам: у каждой своё, и путать их нельзя.
  Map<String, List<String>> bySystem = const {};

  /// О каких систем спрашивали главы.
  final List<String> systemsAsked = [];

  /// Главы, письмо которых сервер провалит.
  Set<String> broken = const {};

  /// Ворота ответа главы: пока Completer не выполнен, страница висит в
  /// «Пишу эту главу…», а уходящая страница остаётся на экране.
  Map<String, Completer<void>> gates = {};
}

/// Оглавление из четырёх глав: первая бесплатная, остальные куплены.
List<Map<String, dynamic>> _toc(List<String> slugs) => [
      for (var i = 0; i < slugs.length; i++)
        {
          'slug': slugs[i],
          'numeral': 'N${i + 1}',
          'index': i + 1,
          'title': 'Глава ${slugs[i]}',
          'question': '',
          'free': i == 0,
          'open': true,
          'written': true,
          'needs_birth_time': false,
        },
    ];

AlmaClient standClient(Wire wire) {
  final transport = MockClient((request) async {
    final path = request.url.path;
    Object body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't', 'user_id': 'u', 'is_guest': true, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {'id': 'u', 'locale': 'en', 'is_guest': true, 'created_at': '', 'unlocked': []};
    } else if (path == '/v1/profiles') {
      body = [
        {'id': 'p1', 'is_self': true, 'birth_date': '1992-05-11',
         'latitude': 55.75, 'longitude': 37.62, 'timezone': 'Europe/Moscow'}
      ];
    } else if (path == '/v1/events') {
      wire.events.add(jsonDecode(request.body) as Map<String, dynamic>);
      body = <String, dynamic>{};
    } else if (path.endsWith('/chapters')) {
      // `/v1/readings/<система>/chapters`
      final system = path.split('/')[3];
      wire.systemsAsked.add(system);
      final slugs = wire.bySystem[system] ??
          wire.listings[wire.chapterLists.clamp(0, wire.listings.length - 1)];
      wire.chapterLists++;
      body = {
        'system': system,
        'total': slugs.length,
        'chapters': _toc(slugs),
      };
    } else if (path == '/v1/readings') {
      final payload = jsonDecode(request.body) as Map<String, dynamic>;
      final chapter = payload['chapter'] as String;
      wire.asked.add(chapter);
      final gate = wire.gates[chapter];
      if (gate != null) await gate.future;
      if (wire.broken.contains(chapter)) {
        return http.Response(
            jsonEncode({'detail': {'code': 'oops', 'message': 'нет связи'}}), 500,
            headers: {'content-type': 'application/json'});
      }
      body = {
        'reading': {
          'system': 'numerology',
          'chapter': chapter,
          'title': 'Титул $chapter',
          'teaser': '',
          'body': List.generate(
              30,
              (i) =>
                  'Абзац $i главы $chapter, достаточно длинный, чтобы страница прокручивалась и имела настоящее дно.'),
          'cited_factors': [],
          'read_from': '',
          'model': 'test',
        },
        'cached': true,
      };
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

Widget host(AlmaSession session,
        {String chapter = 'life-path',
        SystemSlug system = SystemSlug.numerology}) =>
    SessionScope(
      session: session,
      child: MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        // Ключ — вместо нового маршрута: в продукте в каждую главу входят
        // отдельным `push`, и состояние экрана всегда свежее. Без ключа
        // подмена системы на месте переиспользовала бы старое состояние вместе
        // с чужим оглавлением — случай, которого в продукте не бывает.
        home: ChapterScreen(
          key: ValueKey('${system.slug}/$chapter'),
          system: system,
          chapter: chapter,
        ),
      ),
    );

/// Экран главы, открытый **поверх** другой страницы: только так проверяется
/// возврат назад и повторный вход.
Widget stack(AlmaSession session,
        {required String chapter, SystemSlug system = SystemSlug.numerology}) =>
    SessionScope(
      session: session,
      child: MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) =>
                        ChapterScreen(system: system, chapter: chapter))),
                child: const Text('открыть'),
              ),
            ),
          ),
        ),
      ),
    );

Future<void> beats(WidgetTester tester, [int n = 12]) async {
  for (var i = 0; i < n; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

Future<ScrollPosition> settledBottom(WidgetTester tester) async {
  final position =
      tester.state<ScrollableState>(find.byType(Scrollable).first).position;
  var settled = position.maxScrollExtent;
  for (var i = 0; i < 40; i++) {
    await tester.pump(const Duration(milliseconds: 80));
    if (position.maxScrollExtent == settled && settled > 0) break;
    settled = position.maxScrollExtent;
  }
  position.jumpTo(position.maxScrollExtent);
  await tester.pump();
  return position;
}

/// Живая протяжка за дно — шагами по четыре точки с честными отметками
/// времени.
///
/// **Отметки времени обязательны.** Без них тестовый привод шлёт движения с
/// нулевым штампом, распознаватель жеста считает их одним мгновением, и
/// дотяжка не растёт вовсе — годами это и выдавали за «синтетическим пальцем
/// порог недостижим». Достижим: 140 шагов дают 180–196 точек дотяжки, то есть
/// с запасом за оба порога.
///
/// [clock] — двигать ли часы кадра. `false` держит анимацию смены главы
/// замороженной, и уходящая страница остаётся на экране столько, сколько нужно
/// проверке.
///
/// Возвращает самую глубокую дотяжку жеста — то самое число, которое до
/// починки оставалось нулём.
Future<double> pull(
  WidgetTester tester, {
  int steps = 140,
  bool release = true,
  bool clock = true,
  Finder? on,
}) async {
  final target = on ?? find.byType(SingleChildScrollView).first;
  final position = tester
      .state<ScrollableState>(
          find.descendant(of: target, matching: find.byType(Scrollable)))
      .position;
  final g = await tester.startGesture(tester.getCenter(target));
  await tester.pump();
  var deepest = 0.0;
  for (var i = 0; i < steps; i++) {
    await g.moveBy(const Offset(0, -4),
        timeStamp: Duration(milliseconds: 16 * (i + 1)));
    if (clock) {
      await tester.pump(const Duration(milliseconds: 16));
    } else {
      await tester.pump();
    }
    final past = position.pixels - position.maxScrollExtent;
    if (past > deepest) deepest = past;
  }
  if (release) {
    await g.up();
    await tester.pump();
  }
  return deepest;
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    // **Связка в пробирке.** `flutter_secure_storage` разговаривает с
    // платформой каналом, которого в тестах нет: без этой строки первый же
    // `read()` не отвечает никогда, и тест умирает по десятиминутному
    // таймауту, не сказав почему.
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('резкий смах на дне не переворачивает страницу', (tester) async {
    final session = AlmaSession(chapterClient());
    await session.start();
    await tester.pumpWidget(host(session));
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }
    expect(find.text('Первая'), findsOneWidget);

    // На дно — прыжком позиции, не жестом: флинг на восемь тысяч точек это
    // «рука», утащенная за край, и тест сам совершал глубокую протяжку.
    final position = await settledBottom(tester);

    // Резкий короткий смах: инерция бьёт в резинку глубже порога, но рука
    // за край не заходила — страница обязана остаться.
    await tester.fling(find.byType(SingleChildScrollView), const Offset(0, -80), 5000);
    // Кадры руками, не pumpAndSettle: страница теперь цельная, и вклейка
    // с её бесконечной анимацией ожидания смонтирована даже на дне — ждать
    // «когда всё замрёт» значит ждать вечно.
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 60));
    }
    expect(position.maxScrollExtent, greaterThan(0));

    // Заголовок вверху ленивого списка размонтирован — проверяем по
    // абзацам: они несут слаг своей главы.
    expect(find.textContaining('life-path'), findsWidgets,
        reason: 'инерция не должна листать главы — только рука');
    expect(find.textContaining('birthday-number'), findsNothing);
  });

  testWidgets('дно достижимо и хвост зовёт следующую главу', (tester) async {
    // Здесь стоял жест «глубокой протяжки» синтетическим пальцем — и он
    // годами проверял не продукт, а синтез событий: пробирка шлёт движения
    // пачками между кадрами, резинка iOS гасит пачку не так, как живой
    // палец, и порог подтверждения в ней недостижим, хотя рука на симуляторе
    // переворачивает страницы свободно (проверено глазами). Пороги и правило
    // «переворот только на отпускании» теперь юнит-тестирует решётка
    // (`pull_latch_test.dart`); этому тесту остаётся смоук: дно есть, хвост
    // стоит и зовёт ровно следующую главу.
    final session = AlmaSession(chapterClient());
    await session.start();
    await tester.pumpWidget(host(session));
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }
    await settledBottom(tester);

    expect(find.text('↓'), findsOneWidget,
        reason: 'хвост протяжки обязан стоять на дне');
    // Хвост печатает заголовок из оглавления, а не из текста главы.
    expect(find.textContaining('Число дня'), findsWidgets,
        reason: 'хвост зовёт ровно следующую главу по оглавлению');
  });

  /* ── переход между главами ───────────────────────────────────────────── */

  testWidgets('протяжка за дно доходит до порога и листает главу',
      (tester) async {
    // **Тот самый жест, на который жаловался владелец.** Полоса налива в
    // хвосте раньше меняла *ширину виджета* на каждом кадре протяжки, то есть
    // перевёрстывала колонку главы внутри живой прокрутки, — и дотяжка
    // переставала расти за пальцем. Порог 130 не брался вовсе: тот же жест
    // давал 0 точек дотяжки вместо 180.
    final wire = Wire()..listings = [const ['ch1', 'ch2', 'ch3', 'ch4']];
    final session = AlmaSession(standClient(wire));
    await session.start();
    await tester.pumpWidget(host(session, chapter: 'ch1'));
    await beats(tester);
    final position = await settledBottom(tester);

    final deepest = await pull(tester);
    expect(deepest, greaterThan(130),
        reason: 'дотяжка обязана расти за пальцем до порога подтверждения; '
            'перевёрстка полосы налива внутри прокрутки держала её на нуле');
    expect(position.maxScrollExtent, greaterThan(0));
    await beats(tester, 20);

    expect(wire.asked, ['ch1', 'ch2'],
        reason: 'протяжка обязана заказать ровно следующую главу');
    expect(find.textContaining('главы ch2'), findsWidgets);
    expect(find.textContaining('главы ch1'), findsNothing);
  });

  testWidgets('две протяжки подряд листают ровно по одной главе',
      (tester) async {
    // Через одну — это и была бы жалоба «переходит не туда»: человек тянет к
    // напечатанному имени, а попадает дальше.
    final wire = Wire()..listings = [const ['ch1', 'ch2', 'ch3', 'ch4']];
    final session = AlmaSession(standClient(wire));
    await session.start();
    await tester.pumpWidget(host(session, chapter: 'ch1'));
    await beats(tester);
    await settledBottom(tester);

    await pull(tester);
    await beats(tester, 20);
    await settledBottom(tester);
    await pull(tester);
    await beats(tester, 20);

    expect(wire.asked, ['ch1', 'ch2', 'ch3']);
    expect(find.textContaining('главы ch3'), findsWidgets);
  });

  testWidgets('на последней главе тянуть некуда', (tester) async {
    final wire = Wire()..listings = [const ['ch1', 'ch2']];
    final session = AlmaSession(standClient(wire));
    await session.start();
    await tester.pumpWidget(host(session, chapter: 'ch2'));
    await beats(tester);
    await settledBottom(tester);

    expect(find.text('↓'), findsNothing,
        reason: 'за последней главой хвоста нет');
    await pull(tester);
    await beats(tester, 20);

    expect(wire.asked, ['ch2'], reason: 'листать некуда — и не листаем');
    expect(find.textContaining('главы ch2'), findsWidgets);
  });

  testWidgets('уходящая глава уезжает 420 мс, а не исчезает', (tester) async {
    // **Анимация перелистывания не играла вовсе.** Смена главы меняет первый
    // слой стопки (бумага → ночь), а разбор безключевого списка детей на
    // первом же несовпадении гасит **все** остальные, — и содержимое экрана
    // пересобиралось целиком. `AnimatedSwitcher` получал новый элемент, старая
    // страница пропадала в тот же кадр, вместо того чтобы осесть вниз. Здесь
    // это видно прямо: сразу после протяжки текст ch1 обязан быть ещё на
    // экране, пока ch2 пишется.
    final wire = Wire()
      ..listings = [const ['ch1', 'ch2', 'ch3', 'ch4']]
      ..gates = {'ch2': Completer<void>()};
    final session = AlmaSession(standClient(wire));
    await session.start();
    await tester.pumpWidget(host(session, chapter: 'ch1'));
    await beats(tester);
    await settledBottom(tester);

    // Протяжка: ch2 заказана, но сервер её держит — на экране «Пишу эту
    // главу…», а страница ch1 ещё уезжает.
    await pull(tester);
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 1));
    }
    expect(wire.asked, ['ch1', 'ch2']);
    expect(find.textContaining('главы ch1'), findsWidgets,
        reason: 'уходящая страница живёт свои 420 мс — ради этой анимации '
            '[AnimatedSwitcher] тут и стоит');

    // Её отскок и её уход не заказывают ничего сверх названного хвостом.
    await beats(tester, 12);
    expect(wire.asked, ['ch1', 'ch2']);
    expect(find.textContaining('главы ch1'), findsNothing,
        reason: 'через 420 мс уходящая страница снята');

    wire.gates['ch2']!.complete();
    await beats(tester, 20);
    expect(find.textContaining('главы ch2'), findsWidgets);
    expect(wire.asked, ['ch1', 'ch2']);
  });

  testWidgets('отскок уходящей страницы не засчитывается новой главе',
      (tester) async {
    // Дочитанность — свойство показанной страницы. Уходящая страница
    // досматривает отскок резинки уже после того, как встала следующая, и её
    // «прокручено до дна» доставалось той, которую ещё не читали: нить у
    // правого поля вставала полной, воронка засчитывала чтение, а в середине
    // первого экрана вырастало приглашение «что дальше» — концовка главы
    // поверх её начала.
    final wire = Wire()..listings = [const ['ch1', 'ch2', 'ch3']];
    final session = AlmaSession(standClient(wire));
    await session.start();
    // ch3 — последняя и платная: ровно на ней дочитывание поднимает V3.
    await tester.pumpWidget(host(session, chapter: 'ch2'));
    await beats(tester);
    await settledBottom(tester);

    await pull(tester);
    // Кадры отскока: уходящая страница ещё шлёт уведомления со своего дна.
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 16));
    }
    await beats(tester, 20);

    expect(find.textContaining('главы ch3'), findsWidgets);
    expect(find.text('WHAT NEXT'), findsNothing,
        reason: 'только что открытая глава не может быть дочитанной');
    expect(
        wire.events.where((e) => e['stage'] == 'free_chapter_completed').length,
        0,
        reason: 'ни одной бесплатной главы здесь не дочитывали');
  });

  testWidgets('без оглавления хвоста нет и протяжка ничего не листает',
      (tester) async {
    // Оглавление задержано: пока его нет, «следующей главы» не существует, и
    // жест обязан быть пустым, а не гадать.
    final wire = Wire()..listings = [const []];
    final session = AlmaSession(standClient(wire));
    await session.start();
    await tester.pumpWidget(host(session, chapter: 'ch1'));
    await beats(tester);

    expect(find.text('↓'), findsNothing);
    expect(wire.asked, ['ch1']);
  });

  testWidgets('отказ письма после протяжки не заказывает лишних глав',
      (tester) async {
    // Протяжка увела на ch2, а письмо не доехало. Экран обязан остановиться на
    // отказе: ни третьей главы, ни повторного запроса второй. Признак перехода
    // при этом гасится в `finally` — конец загрузки есть конец перехода, чем бы
    // она ни кончилась; иначе он оставался бы поднятым и глушил любую
    // следующую протяжку молча.
    final wire = Wire()
      ..listings = [const ['ch1', 'ch2', 'ch3']]
      ..broken = {'ch2'};
    final session = AlmaSession(standClient(wire));
    await session.start();
    await tester.pumpWidget(host(session, chapter: 'ch1'));
    await beats(tester);
    await settledBottom(tester);

    await pull(tester);
    await beats(tester, 20);

    expect(wire.asked, ['ch1', 'ch2']);
    expect(find.textContaining('главы ch1'), findsNothing);
    expect(find.textContaining('главы ch3'), findsNothing);
    expect(find.byType(SingleChildScrollView), findsNothing,
        reason: 'текста нет — и хвоста, за который тянуть, тоже');
  });

  testWidgets('возврат назад и повторная протяжка листают ту же главу',
      (tester) async {
    // Экран главы уходит вместе с маршрутом, и второй вход обязан начинаться с
    // чистой решётки: иначе первая же протяжка после возврата уносила бы туда,
    // где кончился прошлый заход.
    final wire = Wire()..listings = [const ['ch1', 'ch2', 'ch3', 'ch4']];
    final session = AlmaSession(standClient(wire));
    await session.start();
    await tester.pumpWidget(stack(session, chapter: 'ch1'));
    await tester.tap(find.text('открыть'));
    await beats(tester);
    await settledBottom(tester);

    await pull(tester);
    await beats(tester, 20);
    expect(wire.asked, ['ch1', 'ch2']);

    // Назад к списку и снова в первую главу.
    final screen = tester.state<NavigatorState>(find.byType(Navigator).last);
    screen.pop();
    await beats(tester, 12);
    await tester.tap(find.text('открыть'));
    await beats(tester);
    await settledBottom(tester);

    await pull(tester);
    await beats(tester, 20);
    expect(wire.asked, ['ch1', 'ch2', 'ch1', 'ch2'],
        reason: 'второй заход начинает с той же первой главы и листает на '
            'вторую, а не туда, где кончился первый');
    expect(find.textContaining('главы ch2'), findsWidgets);
  });

  testWidgets('другая система листает по своему оглавлению', (tester) async {
    // Оглавления кэшируются в клиенте по системе; протяжка обязана брать
    // список **своей** системы, а не тот, что привезли последним.
    final wire = Wire()
      ..bySystem = const {
        'numerology': ['num1', 'num2', 'num3'],
        'natal': ['nat1', 'nat2', 'nat3'],
      };
    final session = AlmaSession(standClient(wire));
    await session.start();

    await tester.pumpWidget(host(session, chapter: 'num1'));
    await beats(tester);
    await settledBottom(tester);
    await pull(tester);
    await beats(tester, 20);
    expect(wire.asked, ['num1', 'num2']);

    // Тот же клиент, другая система: её оглавление своё, и хвост зовёт её главу.
    await tester.pumpWidget(
        host(session, chapter: 'nat1', system: SystemSlug.natal));
    await beats(tester);
    await settledBottom(tester);
    expect(find.textContaining('Глава nat2'), findsWidgets,
        reason: 'хвост натальной системы зовёт натальную главу');
    await pull(tester);
    await beats(tester, 20);

    expect(wire.asked, ['num1', 'num2', 'nat1', 'nat2']);
  });
}
