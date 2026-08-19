import 'dart:convert';

import 'package:alma/design/gilt_page.dart';
import 'package:alma/design/metrics.dart';
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

/// Где стоит «←» на странице главы.
///
/// **Владелец снял её положение с кадра:** «кнопка назад в главах — нужно
/// сдвинуть левее, сейчас выглядит немного странно». Кружок отмерялся от поля
/// колонки текста (52), а поле это принадлежит **ширине строки чтения**, а не
/// шапке: стрелка вставала на двадцать пять точек правее, чем «←» на анкете
/// пары, на экране системы, в правовом документе и в шапках витрин, — и
/// читалась утопленной вглубь листа.
AlmaClient backClient({required bool open}) {
  final transport = MockClient((request) async {
    final path = request.url.path;
    Object body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't', 'user_id': 'u', 'is_guest': true, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {
        'id': 'u',
        'locale': 'en',
        'is_guest': true,
        'created_at': '',
        'unlocked': []
      };
    } else if (path == '/v1/profiles') {
      body = [
        {
          'id': 'p1',
          'is_self': true,
          'birth_date': '1992-05-11',
          'latitude': 55.75,
          'longitude': 37.62,
          'timezone': 'Europe/Moscow'
        }
      ];
    } else if (path.endsWith('/chapters')) {
      body = {
        'system': 'numerology',
        'total': 16,
        'chapters': [
          {
            'slug': 'ch1',
            'numeral': 'I',
            'index': 1,
            'title': 'Первая',
            'question': '',
            'free': open,
            'open': open,
            'written': true,
            'needs_birth_time': false
          },
          {
            'slug': 'ch2',
            'numeral': 'II',
            'index': 2,
            'title': 'Вторая',
            'question': '',
            'free': false,
            'open': open,
            'written': true,
            'needs_birth_time': false
          },
        ],
      };
    } else if (path == '/v1/readings') {
      if (!open) {
        body = {'locked': true, 'product': 'natal_forever'};
      } else {
        body = {
          'reading': {
            'system': 'numerology',
            'chapter': 'ch1',
            'title': 'Первая',
            'teaser': '',
            'body': ['Один абзац главы, достаточный, чтобы страница жила.'],
            'cited_factors': [],
            'read_from': '',
            'model': 'test',
          },
          'cached': true,
        };
      }
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

Future<void> open(WidgetTester tester, AlmaSession session) async {
  await tester.pumpWidget(SessionScope(
    session: session,
    child: const MaterialApp(
      localizationsDelegates: L.localizationsDelegates,
      supportedLocales: L.supportedLocales,
      home: ChapterScreen(system: SystemSlug.numerology, chapter: 'ch1'),
    ),
  ));
  for (var i = 0; i < 12; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('«←» стоит по общему полю продукта, а не по полю колонки текста',
      (tester) async {
    final session = AlmaSession(backClient(open: true));
    await session.start();
    await open(tester, session);

    final box = tester.getRect(find.byType(GiltBack));
    expect(box.left, AlmaMetrics.pad,
        reason: 'цель нажатия начинается там же, где «←» на всех остальных '
            'кадрах; было 47 — поле колонки 52 минус поле кружка 5');
    expect(box.width, greaterThanOrEqualTo(44));
    expect(box.height, greaterThanOrEqualTo(44));
    // Центр знака — 44 от края экрана, как у «←» анкеты пары и экрана системы.
    expect(box.center.dx, AlmaMetrics.pad + GiltPage.hit / 2);
  });

  testWidgets('на закрытой главе «←» не наезжает на счётчик', (tester) async {
    // У закрытой страницы счётчик «1 / 16» напечатан рядом со стрелкой (нити
    // прогресса там нет). Сдвиг стрелки влево двигает счётчик вместе с ней и
    // не имеет права на неё налезть.
    final session = AlmaSession(backClient(open: false));
    await session.start();
    await open(tester, session);

    final box = tester.getRect(find.byType(GiltBack));
    expect(box.left, AlmaMetrics.pad);
    final counter = tester.getRect(find.text('1 / 16'));
    expect(counter.left, greaterThanOrEqualTo(box.right),
        reason: 'счётчик начинается за целью нажатия, а не поверх неё');
  });
}
