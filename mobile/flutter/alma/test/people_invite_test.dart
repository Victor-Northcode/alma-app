import 'dart:convert';

import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/screens/systems/people_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Друзья на экране людей: кнопка «Позвать в Alma» и бейдж живой связи.
///
/// Фича роста (владелец, 31.08.2026). Что прибито:
/// * кнопка стоит над списком — самый ценный жест экрана не спрятан под форму;
/// * человек, пришедший по приглашению, помечен «в Alma» — золотом, событием;
/// * 422 `no_self_birth` отвечает словами о причине, а не сырой ошибкой.
AlmaClient peopleClient({required bool withSelf}) {
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
        if (withSelf)
          {
            'id': 'self1',
            'is_self': true,
            'birth_date': '1992-05-11',
            'latitude': 55.75,
            'longitude': 37.62,
            'timezone': 'Europe/Moscow',
            'name': 'Sofia',
          },
        {
          'id': 'friend1',
          'is_self': false,
          'relation': 'friend',
          'birth_date': '1990-07-02',
          'latitude': 41.9,
          'longitude': 12.5,
          'timezone': 'Europe/Rome',
          'name': 'Marco',
        },
        {
          'id': 'dead1',
          'is_self': false,
          'birth_date': '1991-01-01',
          'latitude': 48.85,
          'longitude': 2.35,
          'timezone': 'Europe/Paris',
          'name': 'Записанный',
        },
      ];
    } else if (path == '/v1/friends' && request.method == 'GET') {
      // Живая связь ровно одна: Марко пришёл по ссылке, «Записанный» — нет.
      body = {
        'friends': [
          {'profile_id': 'friend1', 'name': 'Marco', 'since': '2026-08-31T00:00:00Z'},
        ],
      };
    } else if (path == '/v1/friends/invites' && request.method == 'POST') {
      if (!withSelf) {
        return http.Response(
          jsonEncode({
            'detail': {
              'error': 'no_self_birth',
              'message': 'save your own birth before inviting someone',
            }
          }),
          422,
          headers: {'content-type': 'application/json'},
        );
      }
      body = {'token': 'tok', 'url': 'https://alma.pazl.ai/p/tok'};
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

Future<void> _open(WidgetTester tester, AlmaSession session) async {
  await tester.pumpWidget(SessionScope(
    session: session,
    child: const MaterialApp(
      localizationsDelegates: L.localizationsDelegates,
      supportedLocales: L.supportedLocales,
      home: PeopleScreen(),
    ),
  ));
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('кнопка «Позвать в Alma» стоит над списком, живой друг помечен',
      (tester) async {
    final session = AlmaSession(peopleClient(withSelf: true));
    await session.start();
    await _open(tester, session);

    final invite = find.text('Invite to Alma');
    expect(invite, findsOneWidget, reason: 'жеста роста на экране нет');

    // Кнопка выше первой строки списка: рост не спрятан под форму.
    expect(
      tester.getTopLeft(invite).dy,
      lessThan(tester.getTopLeft(find.text('Marco')).dy),
      reason: '«Позвать» уехала под список',
    );

    // Живая связь помечена — и ровно одна: запись с датой бейджа не носит.
    expect(find.text('IN ALMA'), findsOneWidget,
        reason: 'пришедший по приглашению неотличим от мёртвой записи');
  });

  testWidgets('без своей даты приглашение отвечает словами, а не ошибкой',
      (tester) async {
    final session = AlmaSession(peopleClient(withSelf: false));
    await session.start();
    await _open(tester, session);

    await tester.tap(find.text('Invite to Alma'));
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    expect(
      find.text(
        'First save your own birth — the invitation promises a comparison of two.',
      ),
      findsOneWidget,
      reason: '422 no_self_birth не превратился в человеческую фразу',
    );

    // Дожечь анимацию появления строки (RiseIn, 560 мс): без этого биндинг
    // падает на «Timer is still pending» уже после всех проверок.
    await tester.pump(const Duration(seconds: 1));
  });
}
