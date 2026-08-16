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

/// Закрытая глава не тревожит писателя.
///
/// Правило владельца: «мы не должны сразу писать всю главу, пока у человека
/// нет подписки или купленного». До него платная глава писалась целиком и
/// показывалась размытой — за генерацию платили мы, до всякой покупки. Тест
/// держит обе половины отмены: `POST /v1/readings` не уходит вовсе, и кнопка
/// стоит на экране сразу, а не после ответа сервера.

/// Куда стучался клиент — по одной строке на запрос.
late List<String> calls;

AlmaClient lockedClient() {
  calls = [];
  final transport = MockClient((request) async {
    final path = request.url.path;
    calls.add('${request.method} $path');
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
      // Натальная карта у гостя: первая глава бесплатна и открыта, вторая
      // закрыта — ровно то, что сервер печатает неоплатившему.
      body = {
        'system': 'natal',
        'total': 2,
        'chapters': [
          {'slug': 'core', 'numeral': 'I', 'index': 1, 'title': 'Ядро',
           'question': '', 'free': true, 'open': true, 'written': true,
           'needs_birth_time': false},
          {'slug': 'career', 'numeral': 'II', 'index': 2, 'title': 'Дело',
           'question': '', 'free': false, 'open': false, 'written': false,
           'needs_birth_time': false},
        ],
      };
    } else if (path == '/v1/readings') {
      body = {
        'reading': {
          'system': 'natal', 'chapter': 'core', 'title': 'Ядро',
          'teaser': '', 'body': ['Первый абзац бесплатной главы.'],
          'cited_factors': <String>[], 'read_from': '', 'model': 'test',
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

Widget host(AlmaSession session, String chapter) => SessionScope(
      session: session,
      child: MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: ChapterScreen(system: SystemSlug.natal, chapter: chapter),
      ),
    );

/// Рисунок стены крутится вечно, и `pumpAndSettle` на нём не возвращается —
/// поэтому кадры отсчитываются руками, как в `chapter_pull_test`.
Future<void> settle(WidgetTester tester) async {
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('вход в закрытую главу не шлёт POST /v1/readings', (tester) async {
    final session = AlmaSession(lockedClient());
    await session.start();
    await tester.pumpWidget(host(session, 'career'));
    await settle(tester);

    expect(calls.where((c) => c == 'POST /v1/readings'), isEmpty,
        reason: 'без права главу не пишут — значит, и не просят');
    expect(find.text('Unlock'), findsOneWidget);
    expect(find.text('Unlock to read'), findsOneWidget);
  });

  testWidgets('стена стоит на первом кадре, когда оглавление уже привозили',
      (tester) async {
    final session = AlmaSession(lockedClient());
    await session.start();
    // Так и бывает в жизни: в главу заходят с экрана системы, который только
    // что показал это оглавление.
    await session.client.chapters(SystemSlug.natal, locale: session.locale);

    await tester.pumpWidget(host(session, 'career'));
    await tester.pump();

    expect(find.text('Unlock'), findsOneWidget,
        reason: 'кнопка обязана быть сразу, без экрана ожидания');
    // «Пишу эту главу…» — экран того, кому текст положен.
    expect(find.text('Writing this chapter…'), findsNothing);
  });

  testWidgets('открытая глава по-прежнему идёт за текстом', (tester) async {
    final session = AlmaSession(lockedClient());
    await session.start();
    await tester.pumpWidget(host(session, 'core'));
    await settle(tester);

    expect(calls.where((c) => c == 'POST /v1/readings'), hasLength(1),
        reason: 'бесплатная глава пишется как писалась');
  });
}
