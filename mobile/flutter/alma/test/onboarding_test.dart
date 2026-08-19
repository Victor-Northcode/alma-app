import 'dart:convert';

import 'package:alma/main.dart';
import 'package:alma/net/alma_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Маленькая обучалка: приходит один раз, закрывается с первого раза, второй
/// запуск её не показывает.
///
/// **Проверяется то, чем такая вещь портит продукт.** Обучалка, которую нельзя
/// закрыть первым тапом, и обучалка, приходящая каждый запуск, — это два
/// способа сделать плохо всем, включая тех, кому она когда-то помогла. Третья
/// проверка — что её не видит человек, у которого карта уже построена: он
/// анкеты не проходил, кабинет знает, и накладка поверх знакомого экрана
/// читается поломкой.
///
/// Тексты английские, как в соседних тестах кабинета: локаль в пробирке —
/// системная, а не та, что лежит в аккаунте.

/// Сервер в пробирке: профиль есть, хаб отвечает восемью системами, письмо дня
/// написано. Формы — те же, что у настоящего бэкенда.
AlmaClient cabinetClient() {
  final http.Client transport = MockClient((request) async {
    final path = request.url.path;
    Object body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't1', 'user_id': 'u1', 'is_guest': true, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {
        'id': 'u1',
        'locale': 'en',
        'is_guest': true,
        'created_at': '2026-08-10T00:00:00Z',
        'unlocked': <String>[],
        'display_name': 'Anna',
      };
    } else if (path == '/v1/profiles') {
      body = [
        {
          'id': 'p1',
          'is_self': true,
          'birth_date': '1992-05-11',
          'birth_time': '11:26',
          'latitude': 55.75,
          'longitude': 37.62,
          'timezone': 'Europe/Moscow',
          'name': 'Anna',
        }
      ];
    } else if (path == '/v1/systems/hub') {
      body = {
        'has_birth_data': true,
        'birth_time_known': true,
        'people': 0,
        'systems': [
          for (final slug in const [
            'natal',
            'birth-card',
            'solar-return',
            'astrocartography',
            'numerology',
            'transits',
            'compatibility',
            'synthesis',
          ])
            {'slug': slug, 'unlocked': false, 'status': 'open'},
        ],
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
      body = {'unlocked': <String>[], 'entitlements': <Map<String, dynamic>>[]};
    } else if (path == '/v1/readings') {
      body = {
        'reading': null,
        'locked': true,
        'product': 'sub.monthly',
        'opening': {
          'system': 'transits',
          'chapter': 'active',
          'title': 'Day',
          'teaser': '',
          'body': ['The Moon is waning in your sixth house.'],
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

/// Довести кабинет до того кадра, на котором обучалка успела бы прийти.
///
/// Заставка держит экран 3,4 секунды, каскад прихода ставит таймеры, оболочка
/// даёт кабинету осесть ещё 900 мс, а сама проводка ждёт 380 мс, пока доедет
/// страница вкладки. `pumpAndSettle` здесь упирается в вечное небо продукта,
/// поэтому кадры отсчитываются руками, как в соседних тестах.
Future<void> openCabinet(WidgetTester tester, AlmaClient client) async {
  await tester.pumpWidget(AlmaApp(client: client));
  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 60));
  }
  await tester.pump(const Duration(seconds: 4));
  for (var i = 0; i < 30; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

/// Промотать несколько кадров — столько, чтобы успели и переход между шагами, и
/// уход накладки.
Future<void> beats(WidgetTester tester, [int count = 16]) async {
  for (var i = 0; i < count; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('обучалка приходит один раз и уходит с первого тапа',
      (tester) async {
    // Кадр телефона, а не пробирочные 800×600: вырез считается от настоящих
    // мест настоящих карт, и на чужом кадре колода в четыре ряда не сядет.
    tester.view.physicalSize = const Size(402, 874);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    // Анкета пройдена — оболочка взвела бы этот признак сама на `onDone`
    // путешествия; здесь он положен на диск заранее, чтобы не гонять церемонию.
    SharedPreferences.setMockInitialValues(
        {'alma.onboarding.armed': true});

    await openCabinet(tester, cabinetClient());

    // Первый шаг — про «Мои системы», и оболочка сама привезла туда вкладку.
    expect(find.text('Your eight systems'), findsOneWidget);
    expect(find.text('Next'), findsOneWidget);

    // Тап по затемнению — и всё. Точка выбрана внизу экрана: там наверняка
    // затемнение, а не карточка проводки.
    await tester.tapAt(const Offset(201, 840));
    await beats(tester);
    expect(find.text('Your eight systems'), findsNothing);

    // Кабинет под ней остался живым, а не снялся вместе с накладкой: заголовок
    // «Моих систем» и подпись вкладки — обе на месте.
    expect(find.text('My systems'), findsWidgets);

    // Второй запуск — той же установки, с той же памятью на диске.
    await openCabinet(tester, cabinetClient());
    expect(find.text('Your eight systems'), findsNothing);
    expect(find.text('A page for every day'), findsNothing);
  });

  testWidgets('два шага: сперва системы, потом «Сегодня», потом тишина',
      (tester) async {
    tester.view.physicalSize = const Size(402, 874);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    SharedPreferences.setMockInitialValues(
        {'alma.onboarding.armed': true});

    await openCabinet(tester, cabinetClient());
    expect(find.text('Your eight systems'), findsOneWidget);

    await tester.tap(find.text('Next'));
    await beats(tester);

    // Второй шаг стоит на «Сегодня» — и вкладку туда привезла та же оболочка.
    expect(find.text('Your eight systems'), findsNothing);
    expect(find.text('A page for every day'), findsOneWidget);
    // Последний шаг не обещает третьего.
    expect(find.text('Next'), findsNothing);
    expect(find.text('Got it'), findsOneWidget);

    await tester.tap(find.text('Got it'));
    await beats(tester);
    expect(find.text('A page for every day'), findsNothing);
    // Ушли — и остались на «Сегодня», а не на полпути между вкладками.
    expect(find.text('Anna'), findsOneWidget);
  });

  testWidgets('без пройденной анкеты обучалки нет вовсе', (tester) async {
    tester.view.physicalSize = const Size(402, 874);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    // Пустая память — это человек, у которого карта построена давно: он анкеты
    // в этой сборке не проходил, и накладку поверх знакомого кабинета получить
    // не должен. Этой же веткой живут все остальные тесты кабинета.
    SharedPreferences.setMockInitialValues({});

    await openCabinet(tester, cabinetClient());
    expect(find.text('Your eight systems'), findsNothing);
    expect(find.text('Anna'), findsOneWidget);
  });
}
