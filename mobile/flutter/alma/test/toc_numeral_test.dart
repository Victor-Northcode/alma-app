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

/// Колонка римской цифры в оглавлении — сорок точек, как на холсте W3/W5.
///
/// **Почему это тест, а не вкус.** Число стояло в двух местах файла записанным
/// вручную — в живой строке и в её заготовке, — и обе копии держались друг
/// друга, но не холста. Такое расхождение не видно глазами: колонка на четыре
/// точки шире просто отнимает их у текста, и заметно это становится на длинном
/// заголовке в узкой полосе, то есть на самом дешёвом телефоне и в самом
/// длинном языке.
///
/// Меряется не сама коробка, а расстояние между началом цифры и началом
/// заголовка: коробок в дереве много, а это ровно та величина, которую холст
/// и называет шириной колонки. От шрифта она не зависит — потому и проверяема
/// в `flutter test`, где настоящих шрифтов нет.
AlmaClient tocClient() {
  final transport = MockClient((request) async {
    final path = request.url.path;
    Object body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't', 'user_id': 'u', 'is_guest': true, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {
        'id': 'u', 'locale': 'en', 'is_guest': true,
        'created_at': '2026-08-10T00:00:00Z', 'unlocked': <String>[],
      };
    } else if (path == '/v1/profiles') {
      body = [
        {
          'id': 'p1', 'is_self': true, 'birth_date': '1995-05-11',
          'birth_time': '10:05', 'latitude': -23.5505, 'longitude': -46.6333,
          'timezone': 'America/Sao_Paulo', 'name': 'Lucas',
        }
      ];
    } else if (path.endsWith('/chapters')) {
      body = {
        'system': 'numerology',
        'total': 2,
        'chapters': [
          {
            'slug': 'life-path', 'numeral': 'I', 'index': 1,
            'title': 'Numeral column', 'question': '', 'free': true,
            'open': true, 'written': true, 'needs_birth_time': false,
          },
          {
            'slug': 'birthday-number', 'numeral': 'II', 'index': 2,
            'title': 'Second row', 'question': '', 'free': false,
            'open': false, 'written': false, 'needs_birth_time': false,
          },
        ],
      };
    } else if (path == '/v1/systems/numerology') {
      body = {
        'system': 'numerology',
        'engine_version': 'test',
        'computed_at': '2026-08-16T00:00:00Z',
        'subject': <String, dynamic>{},
        'data': <String, dynamic>{},
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
        locale: const Locale('en'),
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        // Строки оглавления — InkWell, а ему нужен Material над головой.
        home: Scaffold(
          body: SystemScreen(
            system: SystemSlug.numerology,
            onOpenChapter: (_, _, {partner}) {},
          ),
        ),
      ),
    );

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('заголовок главы начинается в сорока точках от цифры',
      (tester) async {
    tester.view.physicalSize = const Size(900, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final session = AlmaSession(tocClient());
    await session.start();
    await tester.pumpWidget(host(session));
    for (var i = 0; i < 12; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    for (final (numeral, title) in const [
      ('I', 'Numeral column'),
      ('II', 'Second row'),
    ]) {
      final left = tester.getTopLeft(find.text(numeral));
      final head = tester.getTopLeft(find.text(title));
      expect(head.dx - left.dx, 40.0,
          reason: 'колонка цифры на холсте W3/W5 — сорок точек ($numeral)');
    }
  });
}
