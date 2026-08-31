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

/// **Лоадер главы стоит по центру экрана, а не по центру остатка под шапкой.**
///
/// Страница живёт в `Expanded` ПОД кнопкой возврата, и голый `Center` вешал
/// ожидание на полшапки ниже видимого центра — владелец снял это на
/// устройстве 31.08.2026: «лоадер слишком низко». Поправка —
/// `_screenCentered` в chapter_screen.dart; этот тест меряет её линейкой:
/// середина колонки ожидания обязана совпасть с серединой экрана.
///
/// Запрос главы здесь не отвечает никогда — так экран честно застревает в
/// «Пишу эту главу…», том самом состоянии, в котором висел владелец.
/// Ручка вечного запроса: тест завершает его сам, когда домерил, — иначе
/// биндинг падает на «Timer is still pending» (таймаут клиента), а дожигать
/// таймаут нельзя: он рождает ретрай с новым таймером.
final _pen = Completer<http.Response>();

AlmaClient hangingClient() {
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
        'system': 'natal',
        'total': 16,
        'chapters': [
          {
            'slug': 'core',
            'numeral': 'I',
            'index': 1,
            'title': 'Core',
            'question': '',
            'free': true,
            'open': true,
            'written': false,
            'needs_birth_time': false
          },
        ],
      };
    } else if (path == '/v1/readings') {
      // Письмо «идёт», пока тест меряет; ответ отдаст сам тест в конце.
      return _pen.future;
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('ожидание «Пишу эту главу…» стоит по центру экрана',
      (tester) async {
    final session = AlmaSession(hangingClient());
    await session.start();
    await tester.pumpWidget(SessionScope(
      session: session,
      child: const MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: ChapterScreen(system: SystemSlug.natal, chapter: 'core'),
      ),
    ));
    for (var i = 0; i < 12; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    final phrase = find.text('Written from your own positions');
    expect(phrase, findsOneWidget, reason: 'экран не дошёл до ожидания письма');
    final caption = find.text('Writing this chapter…');
    expect(caption, findsOneWidget);

    // Середина колонки ожидания — от верха фразы до низа подписи.
    final top = tester.getRect(phrase).top;
    final bottom = tester.getRect(caption).bottom;
    final middle = (top + bottom) / 2;
    final screen = tester.view.physicalSize.height / tester.view.devicePixelRatio;

    expect(
      middle,
      closeTo(screen / 2, 8),
      reason: 'центр ожидания уехал с центра экрана: без поправки на шапку '
          'он висел на полшапки (~27) ниже — то самое «лоадер слишком низко»',
    );

    // Отпустить вечный запрос: письмо «пришло», таймер таймаута снимается.
    _pen.complete(http.Response(
      jsonEncode({
        'reading': {
          'system': 'natal',
          'chapter': 'core',
          'title': 'Core',
          'teaser': '',
          'body': ['Один абзац.'],
          'cited_factors': [],
          'read_from': '',
          'model': 'test',
        },
        'cached': true,
      }),
      200,
      headers: {'content-type': 'application/json'},
    ));
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }
  });
}
