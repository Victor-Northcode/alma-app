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

/// Глава совместимости называет, кого с кем читать.
///
/// **Сервер подставляет второго сам — но только пока он один.** `_partner` в
/// `readings.py` берёт единственного сохранённого человека и отвечает 422
/// `partner_required` при `len(others) != 1`. То есть у того, кто добавил
/// второго человека, глава ломалась ровно за то, что он сделал всё правильно, и
/// экран рисовал ему «добавь человека» поверх двух уже добавленных.
///
/// Транспорт здесь отвечает **как настоящий сервер**: обе формы сняты с живого
/// 8018 — 422 `{"detail":{"error":"partner_required","message":…}}` без поля и
/// 404 `"no such profile"` на выдуманный идентификатор.

/// Тела запросов к `/v1/readings` — по одному на запрос. Именно они и есть
/// предмет проверки: по нарисованному тексту нельзя отличить «сервер угадал» от
/// «клиент сказал».
late List<Map<String, dynamic>> readingBodies;

/// [people] — сохранённые люди, кроме самого человека, в том порядке, в котором
/// их отдаёт сервер (`is_self` первым, дальше по дате добавления).
AlmaClient compatibilityClient({required List<String> people}) {
  readingBodies = [];
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
        'unlocked': ['compatibility'],
      };
    } else if (path == '/v1/profiles') {
      body = [
        {
          'id': 'self',
          'is_self': true,
          'birth_date': '1992-05-11',
          'latitude': 55.75,
          'longitude': 37.62,
          'timezone': 'Europe/Moscow',
        },
        for (final id in people)
          {
            'id': id,
            'is_self': false,
            'name': id,
            'birth_date': '1990-03-01',
            'latitude': 55.75,
            'longitude': 37.62,
            'timezone': 'Europe/Moscow',
          },
      ];
    } else if (path == '/v1/billing/entitlements') {
      body = {'unlocked': <String>['compatibility'], 'entitlements': []};
    } else if (path.endsWith('/chapters')) {
      body = {
        'system': 'compatibility',
        'total': 1,
        'chapters': [
          {
            'slug': 'attraction',
            'numeral': 'I',
            'index': 1,
            'title': 'Притяжение',
            'question': '',
            'free': true,
            'open': true,
            'written': true,
            'needs_birth_time': false,
          },
        ],
      };
    } else if (path == '/v1/readings') {
      final sent = (jsonDecode(request.body) as Map).cast<String, dynamic>();
      readingBodies.add(sent);
      final partner = sent['partner_profile_id'] as String?;
      // **Слово в слово поведение сервера.** Не сказали, кого сравнивать, — он
      // ищет единственного; при двух и более отказывает 422 переведённой
      // фразой. Названного, но чужого, не бывает вовсе — 404.
      if (partner == null && people.length != 1) {
        return http.Response(
            jsonEncode({
              'detail': {
                'error': 'partner_required',
                'message':
                    'Compatibility is about two people. Add someone and I will read you together.',
              }
            }),
            422,
            headers: {'content-type': 'application/json'});
      }
      if (partner != null && !people.contains(partner)) {
        return http.Response(jsonEncode({'detail': 'no such profile'}), 404,
            headers: {'content-type': 'application/json'});
      }
      body = {
        'reading': {
          'system': 'compatibility',
          'chapter': 'attraction',
          'title': 'Притяжение',
          'teaser': '',
          'body': ['Вас двое, и это видно.'],
          'cited_factors': <String>[],
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

Widget host(AlmaSession session, {Profile? partner}) => SessionScope(
      session: session,
      child: MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: ChapterScreen(
          system: SystemSlug.compatibility,
          chapter: 'attraction',
          partner: partner,
        ),
      ),
    );

/// Рисунок ожидания крутится вечно — кадры отсчитываются руками, как в
/// `chapter_locked_test`.
Future<void> settle(WidgetTester tester) async {
  for (var i = 0; i < 12; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('с двумя сохранёнными людьми глава читается, а не отказывает',
      (tester) async {
    final session = AlmaSession(compatibilityClient(people: ['mama', 'partner']));
    await session.start();
    await tester.pumpWidget(host(session));
    await settle(tester);

    expect(readingBodies, hasLength(1));
    expect(readingBodies.first['partner_profile_id'], 'mama',
        reason: 'экран обязан назвать человека — сервер при двоих не угадывает');
    expect(find.text('Вас двое, и это видно.'), findsOneWidget);
    // Тот самый экран, который видел человек с двумя добавленными людьми.
    expect(find.text('Add a person'), findsNothing);
  });

  testWidgets('кого сравнивать, можно сказать снаружи', (tester) async {
    final client = compatibilityClient(people: ['mama', 'partner']);
    final session = AlmaSession(client);
    await session.start();
    final chosen = session.people.last;
    await tester.pumpWidget(host(session, partner: chosen));
    await settle(tester);

    expect(readingBodies.first['partner_profile_id'], 'partner',
        reason: 'названный человек побеждает выбор по умолчанию');
  });

  testWidgets('людей нет — 422 приходит по делу, и на экране дверь к человеку',
      (tester) async {
    final session = AlmaSession(compatibilityClient(people: []));
    await session.start();
    await tester.pumpWidget(host(session));
    await settle(tester);

    expect(readingBodies.first.containsKey('partner_profile_id'), isFalse,
        reason: 'выдумывать человека, которого нет, нечем');
    expect(find.text('Add a person'), findsOneWidget);
  });

  test('главе не про совместимость поле не отправляется вовсе', () async {
    final client = compatibilityClient(people: ['mama']);
    await client.reading(
      system: SystemSlug.natal,
      chapter: 'core',
      locale: 'en',
    );
    expect(readingBodies.first.containsKey('partner_profile_id'), isFalse,
        reason: 'запрос, несущий лишнее, врёт о том, что ему важно');
  });
}
