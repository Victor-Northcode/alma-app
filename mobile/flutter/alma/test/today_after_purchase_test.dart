import 'dart:convert';

import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/screens/today/today_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Заплативший обязан увидеть оплаченное, не убивая приложение.**
///
/// «Сегодня» перечитывало себя только по смене профиля. Права при этом решают
/// не вёрстку, а **запрос**: та же ручка `/v1/readings` отвечает подписчику
/// письмом дня, а бесплатному — 200 с `locked: true` и открывающим абзацем
/// (`readings.py`, `_locked_chapter`). Поэтому купивший подписку получал
/// мгновенно перерисованный каркас страницы — сессия `InheritedNotifier`, он
/// приходит сам — и внутри него ту же бесплатную заметку, которую сервер отдал
/// **до** покупки. Письма дня не было до перезапуска.

/// Сколько раз спросили главу дня. Второй запрос и есть предмет теста: без
/// него экран не перечитан, и разница видна только числом.
int readings = 0;

/// Права переключаются на живом клиенте — как в жизни: тот же аккаунт,
/// тот же профиль, изменилась подписка.
bool subscribed = false;

/// «Сегодня» с настоящими формами ответов; подписка читается из [subscribed]
/// **в момент запроса**, а не при сборке клиента.
AlmaClient switchingClient() {
  readings = 0;
  subscribed = false;
  final http.Client transport = MockClient((request) async {
    final path = request.url.path;
    Map<String, dynamic> body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't1', 'user_id': 'u1', 'is_guest': false, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {
        'id': 'u1',
        'locale': 'en',
        'is_guest': false,
        'created_at': '2026-08-10T00:00:00Z',
        'unlocked': <String>[],
        'display_name': 'Anatoly',
      };
    } else if (path == '/v1/profiles') {
      return http.Response(
          jsonEncode([
            {
              'id': 'p1',
              'is_self': true,
              'birth_date': '1992-05-11',
              'birth_time': '11:26',
              'latitude': 55.75,
              'longitude': 37.62,
              'timezone': 'Europe/Moscow',
              'name': 'Anatoly',
            }
          ]),
          200,
          headers: {'content-type': 'application/json'});
    } else if (path == '/v1/systems/transits') {
      body = {
        'system': 'transits',
        'engine_version': 'test',
        'computed_at': '2026-08-10T00:00:00Z',
        'subject': <String, dynamic>{},
        'data': {
          'sky_now': {
            'moon_phase': {
              'phase': 'waning crescent',
              'illumination': 0.07,
              'waxing': false,
            },
          },
          'active': <Map<String, dynamic>>[],
          'upcoming': <Map<String, dynamic>>[],
        },
        'factors': <String>[],
        'unavailable': <String>[],
        'notes': <String>[],
        'provenance': <String, dynamic>{},
        'access': {'allowed': true, 'reason': ''},
      };
    } else if (path == '/v1/billing/entitlements') {
      body = {
        'unlocked': subscribed
            ? ['natal', 'transits', 'solar-return', 'compatibility']
            : <String>[],
        'entitlements': subscribed
            ? [
                {'active': true, 'kind': 'monthly', 'scope': 'all', 'system': '*'}
              ]
            : <Map<String, dynamic>>[],
        'currency': 'USD',
      };
    } else if (path == '/v1/readings') {
      readings += 1;
      body = subscribed
          ? {
              'reading': {
                'system': 'transits',
                'chapter': 'active',
                'title': 'Day',
                'teaser': 'The first line of the day.',
                'body': ['Transiting Neptune sits exactly on your Mars.'],
                'cited_factors': <String>[],
                'read_from': '',
                'model': 'test',
              },
              'cached': true,
            }
          : {
              'reading': null,
              'locked': true,
              'product': 'sub.monthly',
              'opening': {
                'system': 'transits',
                'chapter': 'active',
                'title': 'Day',
                'teaser': '',
                'body': ['The Moon is waning through your sixth house.'],
                'cited_factors': <String>[],
                'read_from': '',
                'model': 'test',
              },
              'cached': true,
            };
    } else {
      body = {};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

Future<void> _frames(WidgetTester tester, {int count = 14}) async {
  for (var i = 0; i < count; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('покупка перечитывает «Сегодня», а не ждёт перезапуска',
      (tester) async {
    // Ширина щедрая намеренно: настоящих шрифтов в `flutter test` нет,
    // подставной шире, и кнопка «прочитать всё небо» на телефонной ширине
    // переполняет свою строку — артефакт шрифта, а не вёрстки. Предмет теста
    // здесь — запрос, а не сантиметры.
    tester.view.physicalSize = const Size(700, 3000) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    final session = AlmaSession(switchingClient());
    await session.start();

    await tester.pumpWidget(SessionScope(
      session: session,
      child: MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: const TodayScreen(),
      ),
    ));
    await _frames(tester);

    // До покупки: бесплатная заметка из `opening`, письма дня нет.
    expect(readings, 1);
    expect(find.textContaining('sixth house'), findsOneWidget);
    expect(find.textContaining('Neptune'), findsNothing);

    // Деньги прошли, сервер выдал право, `AlmaStore` перечитал права сессии —
    // ровно то, что делает `refreshRights` после успешной покупки.
    subscribed = true;
    await session.refreshRights();
    await _frames(tester);

    // **Вот проверка.** Страница спросила главу заново — уже как подписчик.
    expect(readings, 2,
        reason: 'права изменились, а экран не перечитал себя: '
            'заплативший остался на бесплатном ответе до перезапуска');
    expect(find.textContaining('Neptune'), findsOneWidget,
        reason: 'письмо дня не пришло на экран после покупки');
    expect(find.textContaining('sixth house'), findsNothing,
        reason: 'бесплатная заметка осталась поверх оплаченного письма');
  });

  testWidgets('перестройка без смены прав в сеть не ходит', (tester) async {
    // Ширина щедрая намеренно: настоящих шрифтов в `flutter test` нет,
    // подставной шире, и кнопка «прочитать всё небо» на телефонной ширине
    // переполняет свою строку — артефакт шрифта, а не вёрстки. Предмет теста
    // здесь — запрос, а не сантиметры.
    tester.view.physicalSize = const Size(700, 3000) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    final session = AlmaSession(switchingClient());
    await session.start();

    await tester.pumpWidget(SessionScope(
      session: session,
      child: MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: const TodayScreen(),
      ),
    ));
    await _frames(tester);
    expect(readings, 1);

    // Сессия шевельнулась, права те же. `build` зовётся десятки раз за минуту,
    // и признак «с какими правами читали» существует ровно затем, чтобы это не
    // превращалось в поток запросов: у главы дня на сервере месячное окно.
    await session.refreshRights();
    await session.refreshRights();
    await _frames(tester);
    expect(readings, 1, reason: 'экран перечитывает себя без причины');
  });
}
