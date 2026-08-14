import 'dart:convert';

import 'package:alma/main.dart';
import 'package:alma/net/alma_client.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Сколько раз спросили письмо дня. Проверяется отдельно: неподписчику его
/// не показывают, и **просить его у сервера тоже незачем** — это деньги за
/// генерацию, потраченные в пустоту, и месячный потолок, сгорающий на тексте,
/// которого никто не прочтёт.
int readingCalls = 0;

/// «Сегодня» с настоящими формами ответов: профиль есть, транзиты несут
/// области и фазу луны, письмо дня написано. Формы сняты с живого сервера,
/// а не выдуманы — сломается договор, сломается и тест.
///
/// [subscriber] решает, что отвечает `/v1/billing/entitlements`: гороскоп —
/// функция подписки по решению владельца, и оба состояния экрана обязаны быть
/// закреплены, иначе однажды он снова начнёт раздаваться даром.
AlmaClient richClient({bool subscriber = true}) {
  readingCalls = 0;
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
      // Голый список — форма настоящего сервера. Обёртку {'profiles': […]} в
      // прошлый раз выдумал сам тест, и клиент, читавший её, прошёл проверку,
      // а на живом сервере молча терял профиль.
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
    } else if (path == '/v1/systems/transits') {
      body = {
        'system': 'transits',
        'engine_version': 'test',
        'computed_at': '2026-08-10T00:00:00Z',
        'subject': <String, dynamic>{},
        'data': {
          'sky_now': {
            'moon_phase': {'phase': 'waning crescent', 'illumination': 0.07, 'waxing': false},
          },
          'active': <Map<String, dynamic>>[],
          'upcoming': [
            {
              'area': 'work',
              'transiting': 'sun',
              'natal': 'midheaven',
              'aspect': 'trine',
              'exact': '2026-08-11T09:00:00Z',
              'urgency': 3.0,
            },
          ],
        },
        'factors': <String>[],
        'unavailable': <String>[],
        'notes': <String>[],
        'provenance': <String, dynamic>{},
        'access': {'allowed': true, 'reason': ''},
      };
    } else if (path == '/v1/billing/entitlements') {
      body = {
        'unlocked': subscriber
            ? ['natal', 'numerology', 'birth-card', 'transits', 'solar-return',
               'compatibility', 'astrocartography', 'synthesis']
            : <String>[],
        'entitlements': subscriber
            ? [
                {'active': true, 'kind': 'monthly', 'scope': 'all', 'system': '*'}
              ]
            : <Map<String, dynamic>>[],
        'currency': 'USD',
      };
    } else if (path == '/v1/readings') {
      readingCalls += 1;
      body = {
        'reading': {
          'system': 'transits',
          'chapter': 'active',
          'title': 'День',
          'teaser': 'Первая строка дня.',
          'body': ['Сейчас проходящий Нептун встал точно на твой Марс.'],
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
    // **Связка в пробирке.** `flutter_secure_storage` разговаривает с
    // платформой каналом, которого в тестах нет: без этой строки первый же
    // `read()` не отвечает никогда, и тест умирает по десятиминутному
    // таймауту, не сказав почему.
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('«Сегодня» показывает имя, области и письмо дня', (tester) async {
    await tester.pumpWidget(AlmaApp(client: richClient()));
    // Сессия и обе загрузки — несколько кругов по сети в пробирке.
    // Заставка держит экран 3,4 секунды и уходит, только когда сессия
    // ответила. Пробирка проматывает её целиком — иначе каждый тест кабинета
    // проверял бы небо.
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 60));
    }
    await tester.pump(const Duration(seconds: 4));
    // И ещё несколько кадров: каскад прихода ставит по таймеру на блок, и
    // тест, кончившийся раньше них, падает на «pending timers».
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    // Имя владельца вместо «Today» — как на iOS. Профиль есть, значит
    // вкладки на месте, а путешествие не показано.
    expect(find.text('Анатолий'), findsOneWidget);
    expect(find.text('What should I call you?'), findsNothing);

    // Письмо дня.
    expect(find.textContaining('Нептун'), findsOneWidget);

    // Область с контактом собрана фразой каталога: «Sun now and your natal
    // Midheaven» в en; тест гоняет en, потому и проверяет английские слова.
    expect(find.textContaining('Midheaven'), findsOneWidget);

    // Пустые области говорят это словами, а не молчат: три из четырёх пустые,
    // и каждая несёт строку каталога — «Nothing exact here today.»
    expect(find.text('Nothing exact here today.'), findsNWidgets(3));
  });

  testWidgets('без плана гороскоп закрыт, и письмо дня даже не запрашивается',
      (tester) async {
    await tester.pumpWidget(AlmaApp(client: richClient(subscriber: false)));
    // Заставка держит экран 3,4 секунды и уходит, только когда сессия
    // ответила. Пробирка проматывает её целиком — иначе каждый тест кабинета
    // проверял бы небо.
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 60));
    }
    await tester.pump(const Duration(seconds: 4));
    // И ещё несколько кадров: каскад прихода ставит по таймеру на блок, и
    // тест, кончившийся раньше них, падает на «pending timers».
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    // Ни абзаца дня, ни блюра, ни пустой карточки: одна фраза о том, что это
    // такое и где живёт, и дверь.
    expect(find.textContaining('Нептун'), findsNothing);
    expect(
      find.text(
          'The horoscope is written from your own chart every morning, and it comes with the plan.'),
      findsOneWidget,
    );
    expect(find.text('Open the horoscope'), findsOneWidget);

    // И приглашение к плану — на экране, которым подписчик пользовался бы
    // каждый день, а не одним тапом в настройках, куда никто не заходит,
    // чтобы ему что-нибудь продали.
    expect(find.text('Everything open, every day'), findsOneWidget);
    expect(find.text('See the plans'), findsOneWidget);

    // Главное: за письмо дня никто не заплатил.
    expect(readingCalls, 0);
  });
}
