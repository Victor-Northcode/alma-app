import 'dart:convert';

import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/net/models.dart';
import 'package:alma/screens/systems/people_screen.dart';
import 'package:alma/screens/systems/systems_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Колода «Моих систем» отвечает на тап **каждой** картой.
///
/// `locked-chapter-spec.md` §1 и §7, кадр C5. Проверяется то, на чём продукт
/// терял самый дорогой импульс: карточка совместимости была подписана «add a
/// person» и на тап не отвечала — человек, потянувшийся к совместимости,
/// упирался в картинку. Заодно проверяются подписи: обещание карты — это
/// половина её кликабельности, «рассчитано» не говорит, что будет по нажатию.

/// Сервер в пробирке: хаб с восемью системами, из них три в состояниях, из-за
/// которых карта раньше умолкала.
AlmaClient deckClient({required List<String> people}) {
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
        'unlocked': <String>[],
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
          'name': 'Anna',
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
    } else if (path == '/v1/systems/hub') {
      body = {
        'has_birth_data': true,
        'birth_time_known': false,
        'people': people.length,
        'systems': [
          {'slug': 'natal', 'unlocked': false, 'status': 'open'},
          {'slug': 'birth-card', 'unlocked': false, 'status': 'calculated'},
          // Без времени рождения соляра нет — карта приглушена, но жива.
          {'slug': 'solar-return', 'unlocked': false, 'status': 'needs-time'},
          {'slug': 'astrocartography', 'unlocked': false, 'status': 'open'},
          {'slug': 'numerology', 'unlocked': false, 'status': 'open'},
          {'slug': 'transits', 'unlocked': false, 'status': 'open'},
          {
            'slug': 'compatibility',
            'unlocked': false,
            'status': people.isEmpty ? 'add-person' : 'open',
          },
          {'slug': 'synthesis', 'unlocked': false, 'status': 'not-yet'},
        ],
      };
    } else if (path == '/v1/billing/entitlements') {
      body = {'unlocked': <String>[], 'entitlements': []};
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

Widget deck(AlmaSession session, void Function(SystemSlug) onOpen) => SessionScope(
      session: session,
      child: MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: SystemsScreen(onOpenSystem: onOpen),
      ),
    );

/// Кадр телефона, а не пробирочные 800×600.
///
/// Колода считает высоту карты от окна и садится в четыре ряда ровно на экран;
/// на низком окне нижний ряд просто не строится ленивым списком, и «карта не
/// отвечает на тап» стало бы неотличимо от «карты нет на экране». Размеры — те
/// же 402×874, на которых нарисован кадр C5.
Future<void> show(WidgetTester tester, Widget app) async {
  tester.view.physicalSize = const Size(402, 874);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(app);
  // Приход экрана анимирован; кадры отсчитываются руками, как в соседних
  // тестах, — `pumpAndSettle` здесь упирается в вечные рисунки продукта.
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

  testWidgets('ни одна карта не молчит под пальцем', (tester) async {
    final session = AlmaSession(deckClient(people: []));
    await session.start();
    final tapped = <SystemSlug>[];
    await show(tester, deck(session, tapped.add));

    // Имя системы стоит на карте — по нему в карту и попадают.
    for (final title in const [
      'Natal chart',
      'Birth Card',
      'Solar return',
      'Astrocartography',
      'Numerology',
      'Transits',
      'Compatibility',
      'Cross-synthesis',
    ]) {
      await tester.tap(find.text(title));
    }
    await tester.pump();
    expect(tapped, hasLength(8),
        reason: 'молчащая карта — тупик, а не оформление');
    expect(tapped.toSet(), SystemSlug.values.toSet());
  });

  testWidgets('совместимость зовёт человека, а не сообщает о его отсутствии',
      (tester) async {
    final session = AlmaSession(deckClient(people: []));
    await session.start();
    await show(tester, deck(session, (_) {}));

    expect(find.text('tap to add someone →'), findsOneWidget);
    // Та самая подпись, которая называла состояние вместо действия.
    expect(find.text('add a person'), findsNothing);
    // Ни одной цены на этом экране — продажа живёт внутри главы.
    expect(find.textContaining(r'$'), findsNothing);
  });

  testWidgets('остальные карты обещают начало чтения', (tester) async {
    final session = AlmaSession(deckClient(people: ['mama']));
    await session.start();
    await show(tester, deck(session, (_) {}));

    // Оглавлений никто не привозил — числа открытых глав ещё нет, и карта
    // обещает начало, а не выдумывает счёт.
    expect(find.text('read the opening →'), findsWidgets);
    // С человеком в аккаунте совместимость перестаёт звать в ту же секунду.
    expect(find.text('tap to add someone →'), findsNothing);
    // Нехватка данных остаётся названной: обещать чтение там, где не хватает
    // времени рождения, значит соврать до входа.
    expect(find.text('needs birth time'), findsOneWidget);
  });

  testWidgets('экран людей возвращает того, с кем читать', (tester) async {
    final session = AlmaSession(deckClient(people: ['mama', 'partner']));
    await session.start();
    Profile? picked;
    await tester.pumpWidget(SessionScope(
      session: session,
      child: MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: Builder(
          builder: (context) => TextButton(
            child: const Text('go'),
            onPressed: () async {
              picked = await Navigator.of(context).push<Profile>(
                  MaterialPageRoute(
                      builder: (context) => const PeopleScreen(picking: true)));
            },
          ),
        ),
      ),
    ));
    await tester.tap(find.text('go'));
    // Небо экрана людей дышит вечно — `pumpAndSettle` его не дождётся.
    for (var i = 0; i < 12; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    // Второй сохранённый — тот самый случай, на котором глава ломалась: сервер
    // при двоих не угадывает, и человека обязан назвать экран.
    await tester.tap(find.text('partner'));
    for (var i = 0; i < 12; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }
    expect(picked?.id, 'partner');
  });
}
