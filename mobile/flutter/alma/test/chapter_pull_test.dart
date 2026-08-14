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

Widget host(AlmaSession session) => SessionScope(
      session: session,
      child: const MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: ChapterScreen(system: SystemSlug.numerology, chapter: 'life-path'),
      ),
    );

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
    final position = tester.state<ScrollableState>(find.byType(Scrollable).first).position;
    position.jumpTo(position.maxScrollExtent);
    await tester.pump();

    // Резкий короткий смах: инерция бьёт в резинку глубже порога, но рука
    // за край не заходила — страница обязана остаться.
    await tester.fling(find.byType(ListView), const Offset(0, -80), 5000);
    await tester.pumpAndSettle();

    // Заголовок вверху ленивого списка размонтирован — проверяем по
    // абзацам: они несут слаг своей главы.
    expect(find.textContaining('life-path'), findsWidgets,
        reason: 'инерция не должна листать главы — только рука');
    expect(find.textContaining('birthday-number'), findsNothing);
  });

  testWidgets('глубокая протяжка на дне открывает ровно следующую', (tester) async {
    final session = AlmaSession(chapterClient());
    await session.start();
    await tester.pumpWidget(host(session));
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    final position = tester.state<ScrollableState>(find.byType(Scrollable).first).position;
    position.jumpTo(position.maxScrollExtent);
    await tester.pump();

    // Медленная глубокая протяжка — рука, не инерция.
    // Демпф резинки съедает большую часть пути: чтобы рука дошла до 130
    // задемпфированных точек, самого пути нужно заметно больше — как и на
    // настоящем стекле, где это осознанное движение через пол-экрана.
    await tester.timedDrag(
      find.byType(ListView),
      const Offset(0, -1400),
      const Duration(milliseconds: 900),
    );
    await tester.pumpAndSettle();
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    expect(find.textContaining('birthday-number'), findsWidgets,
        reason: 'глубокая протяжка обязана перевернуть страницу');
  });
}
