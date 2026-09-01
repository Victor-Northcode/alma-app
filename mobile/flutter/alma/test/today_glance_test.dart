import 'dart:convert';

import 'package:alma/main.dart';
import 'package:alma/design/palette.dart';
import 'package:alma/net/alma_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **День одним взглядом** (31.08.2026, по образцу Co-Star): у каждой живой
/// области дня справа стоит глиф её аспекта, тоном дня — поток (трин,
/// секстиль) золотом, трение (квадрат, оппозиция) приглушённым красным
/// несогласия. Что прибито:
///
/// * глиф — ТОГО ЖЕ контакта, что назван строкой области: второго мнения о
///   дне у взгляда нет (закон «числа из факторов», за нарушение которого
///   владелец уже снимал выдуманный «накал страстей»);
/// * тихая область не носит ничего — пустое место не обещает события.
AlmaClient glanceClient() {
  final http.Client transport = MockClient((request) async {
    final path = request.url.path;
    Map<String, dynamic> body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't1', 'user_id': 'u1', 'is_guest': true, 'locale': 'ru'};
    } else if (path == '/v1/account') {
      body = {
        'id': 'u1',
        'locale': 'ru',
        'is_guest': true,
        'created_at': '2026-08-10T00:00:00Z',
        'unlocked': <String>[],
        'display_name': 'Анатолий',
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
              'name': 'Анатолий',
            }
          ]),
          200,
          headers: {'content-type': 'application/json'});
    } else if (path == '/v1/systems/hub') {
      body = {
        'has_birth_data': true,
        'birth_time_known': true,
        'people': 1,
        'systems': <Map<String, dynamic>>[],
      };
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
          'active': [
            {
              'area': 'work',
              'transiting': 'saturn',
              'natal': 'midheaven',
              'aspect': 'square',
              'glyph': '□',
              'exact': '2026-08-10T09:00:00Z',
              'urgency': 5.0,
            },
            {
              'area': 'love',
              'transiting': 'venus',
              'natal': 'moon',
              'aspect': 'trine',
              'glyph': '△',
              'exact': '2026-08-10T12:00:00Z',
              'urgency': 4.0,
            },
          ],
          'upcoming': <Map<String, dynamic>>[],
        },
        'factors': <String>[],
        'unavailable': <String>[],
        'notes': <String>[],
        'provenance': <String, dynamic>{},
        'access': {'allowed': true, 'reason': ''},
      };
    } else if (path == '/v1/billing/entitlements') {
      // Подписчик: панель областей — часть открытого дня, и взгляд живёт
      // там же, где живут её строки.
      body = {
        'unlocked': [
          'natal', 'numerology', 'birth-card', 'transits', 'solar-return',
          'compatibility', 'astrocartography', 'synthesis',
        ],
        'entitlements': [
          {'active': true, 'kind': 'monthly', 'scope': 'all', 'system': '*'}
        ],
        'currency': 'USD',
      };
    } else if (path == '/v1/readings') {
      body = {
        'reading': {
          'system': 'transits',
          'chapter': 'active',
          'title': 'День',
          'teaser': 'Первая строка дня.',
          'body': ['Сатурн сегодня стоит квадратом к твоей Середине неба.'],
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

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('глиф области несёт тон дня: трение красным, поток золотом',
      (tester) async {
    tester.view.physicalSize = const Size(700, 1800) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(AlmaApp(client: glanceClient()));
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 60));
    }
    await tester.pump(const Duration(seconds: 4));
    for (var i = 0; i < 12; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    final friction = find.text('□');
    final flow = find.text('△');
    expect(friction, findsOneWidget,
        reason: 'квадрат работы не дошёл до взгляда');
    expect(flow, findsOneWidget, reason: 'трин любви не дошёл до взгляда');

    final frictionColor = tester.widget<Text>(friction).style!.color!;
    final flowColor = tester.widget<Text>(flow).style!.color!;
    expect(frictionColor.r, AlmaPalette.disagree.r,
        reason: 'трение обязано быть красным несогласия');
    expect(flowColor, AlmaPalette.goldBright,
        reason: 'поток обязан быть золотым');

    // Тихие области («деньги», «тело» — в дне пусто) глифа не носят: два
    // глифа на четыре области, не четыре.
    expect(find.text('☌'), findsNothing);
  });
}
