import 'dart:convert';

import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/net/models.dart';
import 'package:alma/screens/systems/system_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Момент возвращения Солнца печатается по часам того места, для которого
/// построен соляр.
///
/// Случай взят настоящий и худший: рождение в Сан-Паулу, возвращение 2026 года
/// в 01:21 UTC 11 мая. По местным часам это 22:21 **десятого** — то есть UTC
/// врёт здесь не только часом, но и днём, а день до этой строки был всем, что
/// экран показывал. Такая ошибка не выглядит ошибкой: дата правдоподобна,
/// просто чужая.
///
/// Формы ответов сняты с живого сервера. Расчёт урезан до полей, которые
/// читает экран, но ни одно из них не выдумано — `return_tz` и
/// `return_offset_minutes` приезжают из `alma/calc/service.py`.
AlmaClient solarClient({bool withZone = true}) {
  final transport = MockClient((request) async {
    final path = request.url.path;
    Object body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't', 'user_id': 'u', 'is_guest': true, 'locale': 'ru'};
    } else if (path == '/v1/account') {
      body = {
        'id': 'u', 'locale': 'ru', 'is_guest': true,
        'created_at': '2026-08-10T00:00:00Z', 'unlocked': <String>[],
      };
    } else if (path == '/v1/profiles') {
      body = [
        {
          'id': 'p1', 'is_self': true, 'birth_date': '1995-05-11',
          'birth_time': '10:05', 'latitude': -23.5505, 'longitude': -46.6333,
          'timezone': 'America/Sao_Paulo', 'name': 'Лукас',
        }
      ];
    } else if (path.endsWith('/chapters')) {
      body = {
        'system': 'solar-return',
        'total': 1,
        'chapters': [
          {
            'slug': 'the-year', 'numeral': 'I', 'index': 1,
            'title': 'Год', 'question': '', 'free': true, 'open': true,
            'written': true, 'needs_birth_time': true,
          },
        ],
      };
    } else if (path == '/v1/systems/solar-return') {
      body = {
        'system': 'solar-return',
        'engine_version': 'test',
        'computed_at': '2026-08-16T00:00:00Z',
        'subject': <String, dynamic>{},
        'data': {
          'year': 2026,
          'return_at': '2026-05-11T01:21+00:00',
          // Старый сервер этих двух полей не присылает — и клиент обязан
          // работать и так, оставаясь на дневной форме.
          if (withZone) 'return_tz': 'America/Sao_Paulo',
          if (withZone) 'return_offset_minutes': -180,
          'relocated': false,
          'latitude': -23.5505,
          'longitude': -46.6333,
          'year_ruler': 'venus',
          'angular_bodies': <String>[],
          'natal_contacts': <String>[],
          'chart': {
            'placements': {
              'sun': {'longitude': 50.1, 'glyph': '☉', 'sign': 'taurus'},
              'moon': {'longitude': 210.4, 'glyph': '☽', 'sign': 'scorpio'},
            },
            'angles': {
              'ascendant': 12.0, 'midheaven': 280.0,
              'descendant': 192.0, 'imum_coeli': 100.0,
            },
            'houses': [
              for (var i = 0; i < 12; i++)
                {'number': i + 1, 'cusp': i * 30.0, 'sign': 'aries'},
            ],
            'aspects': <Map<String, dynamic>>[],
          },
        },
        'factors': <String>[],
        'access': {'allowed': true},
      };
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

Widget host(AlmaSession session) => SessionScope(
      session: session,
      child: MaterialApp(
        locale: const Locale('ru'),
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        // Scaffold, потому что в приложении экран лежит внутри оболочки:
        // строки оглавления — InkWell, а ему нужен Material над головой.
        home: Scaffold(
          body: SystemScreen(
            system: SystemSlug.solarReturn,
            // Третьим параметром экран называет пару — у соляра её нет, но
            // подпись обязана совпадать с той, что ждёт экран.
            onOpenChapter: (_, _, {partner}) {},
          ),
        ),
      ),
    );

Future<void> _open(WidgetTester tester, AlmaSession session) async {
  // Экран длиннее пробирочных 800×600: рисунок соляра занимает почти весь
  // первый экран, а строки фактов идут под ним и в ленивом списке просто не
  // строятся. Высокое окно — не декорация теста, а единственный способ
  // добраться до строки, ради которой он написан.
  tester.view.physicalSize = const Size(900, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(host(session));
  for (var i = 0; i < 12; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('соляр печатает возвращение по часам своего места', (tester) async {
    final session = AlmaSession(solarClient());
    await session.start();
    await _open(tester, session);

    // 01:21 UTC одиннадцатого — это 22:21 десятого в Сан-Паулу.
    expect(find.textContaining('10 мая 2026'), findsOneWidget);
    expect(find.textContaining('22:21'), findsOneWidget);
    // И ни следа UTC-дня: он здесь ровно на сутки мимо.
    expect(find.textContaining('11 мая'), findsNothing);
  });

  testWidgets('без зоны остаётся день — как на нативе, а не пустая строка',
      (tester) async {
    final session = AlmaSession(solarClient(withZone: false));
    await session.start();
    await _open(tester, session);

    // Час не печатается вовсе: без зоны его неоткуда взять честно.
    expect(find.textContaining(RegExp(r'\d{1,2}:\d{2}')), findsNothing);
    // Но строка «возвращение» на месте — с днём, как её печатал натив.
    expect(find.textContaining('2026'), findsWidgets);
  });
}
