import 'dart:async';
import 'dart:convert';

import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/net/models.dart';
import 'package:alma/screens/systems/chapter_screen.dart';
import 'package:alma/screens/systems/system_screen.dart';
import 'package:alma/screens/systems/writing_art.dart';
import 'package:alma/screens/today/today_screen.dart';
import 'package:alma/state/locale_override.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Смена языка перечитывает содержимое, а не только подписи.
///
/// Владелец, 28.08.2026: после смены языка на экране не остаётся ни строки на
/// старом — ни в главе, ни на «Сегодня», ни в беседе. Сервер уже написанное
/// переводит дешёвой моделью (`ai/translator.py`), поэтому перечитать экран —
/// это доли цента, а не вторая генерация.
///
/// До этих тестов смену языка глотали три защёлки: `_started` у главы,
/// `_threadLoaded` у беседы и условие перезагрузки «Сегодня» без локали —
/// интерфейс переключался мгновенно (`InheritedNotifier`), а тексты стояли на
/// прежнем языке до перезапуска приложения.

const _english = 'The chapter text, written in English.';
const _russian = 'Текст главы, написанный по-русски.';

/// Все запросы клиента — метод, путь и query, по строке на запрос.
late List<String> paths;

/// Тела `POST /v1/readings` в порядке отправки — язык смотрится здесь.
late List<Map<String, dynamic>> readingPosts;

/// [holdLaterReadings] — сервер отвечает на первый запрос главы сразу, а все
/// следующие держит, пока тест не отпустит: окно, в котором видно, что экран
/// показывает во время перечитывания. [holdChapters] — оглавление молчит:
/// состояние «право неизвестно», в котором глава раньше рисовала пустоту.
/// [holdEnglishReading] — держится только английский запрос главы: сценарий
/// «письмо шло, язык сменили», где старый ответ обязан умереть молча.
AlmaClient testClient({
  Completer<void>? holdLaterReadings,
  Completer<void>? holdChapters,
  Completer<void>? holdEnglishReading,
}) {
  paths = [];
  readingPosts = [];
  final transport = MockClient((request) async {
    final url = request.url;
    paths.add(
        '${request.method} ${url.path}${url.hasQuery ? '?${url.query}' : ''}');
    final path = url.path;
    Object body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't', 'user_id': 'u', 'is_guest': true, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {
        'id': 'u', 'locale': 'en', 'is_guest': true,
        'created_at': '', 'unlocked': <String>[],
      };
    } else if (path == '/v1/profiles') {
      body = [
        {
          'id': 'p1', 'is_self': true, 'birth_date': '1992-05-11',
          'birth_time': '11:26', 'latitude': 55.75, 'longitude': 37.62,
          'timezone': 'Europe/Moscow', 'name': 'Анатолий',
        }
      ];
    } else if (path == '/v1/systems/transits') {
      body = {
        'system': 'transits',
        'engine_version': 'test',
        'computed_at': '2026-08-10T00:00:00Z',
        'subject': <String, dynamic>{},
        'data': {
          'sky_now': {
            'moon_phase': {
              'phase': 'waning crescent', 'illumination': 0.07, 'waxing': false,
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
    } else if (path.endsWith('/chapters')) {
      if (holdChapters != null) await holdChapters.future;
      final ru = (url.queryParameters['locale'] ?? 'en').startsWith('ru');
      body = {
        'system': 'natal',
        'total': 1,
        'chapters': [
          {
            'slug': 'core', 'numeral': 'I', 'index': 1,
            'title': ru ? 'Ядро' : 'Core', 'question': '',
            'free': true, 'open': true, 'written': true,
            'needs_birth_time': false,
          },
        ],
      };
    } else if (path == '/v1/readings') {
      final payload = jsonDecode(request.body) as Map<String, dynamic>;
      readingPosts.add(payload);
      if (holdLaterReadings != null && readingPosts.length > 1) {
        await holdLaterReadings.future;
      }
      final ru = (payload['locale'] as String? ?? 'en').startsWith('ru');
      if (holdEnglishReading != null && !ru) await holdEnglishReading.future;
      body = {
        'reading': {
          'system': payload['system'],
          'chapter': payload['chapter'],
          'title': ru ? 'Ядро' : 'Core',
          'teaser': '',
          'body': [ru ? _russian : _english],
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

Widget _host(AlmaSession session, Widget screen) => SessionScope(
      session: session,
      child: MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: screen,
      ),
    );

/// Рисунки ожидания крутятся вечно — кадры отсчитываются руками, как в
/// `chapter_locked_test`.
Future<void> _settle(WidgetTester tester) async {
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
    LocaleOverride.reset();
  });

  testWidgets('глава перечитывает себя на новом языке, старый текст уходит',
      (tester) async {
    final hold = Completer<void>();
    final session = AlmaSession(testClient(holdLaterReadings: hold));
    await session.start();
    await tester.pumpWidget(
        _host(session, const ChapterScreen(system: SystemSlug.natal, chapter: 'core')));
    await _settle(tester);
    expect(find.text(_english), findsOneWidget);

    await session.chooseLanguage('ru');
    await _settle(tester);

    // Окно перечитывания: сервер ещё переводит, и на экране не должно быть
    // ни английского абзаца, ни пустоты — только ожидание.
    expect(find.text(_english), findsNothing,
        reason: 'абзац на прежнем языке под новым интерфейсом запрещён');
    expect(find.text(_russian), findsNothing);
    expect(
      find.byType(WritingArt).evaluate().isNotEmpty ||
          find.byType(WaitingDot).evaluate().isNotEmpty,
      isTrue,
      reason: 'пока перевод в пути — лоадер, а не пустота',
    );

    hold.complete();
    await _settle(tester);
    expect(find.text(_russian), findsOneWidget);
    expect(find.text(_english), findsNothing);
    expect(readingPosts.last['locale'], 'ru',
        reason: 'перечитывание обязано просить новый язык');
  });

  testWidgets('пока право на главу неизвестно — лоадер по центру, а не пустота',
      (tester) async {
    // Вход мимо прогретого оглавления: пуш, глубокая ссылка. Раньше здесь
    // возвращался `SizedBox.shrink()` — голое небо без единого знака жизни.
    final gate = Completer<void>();
    final session = AlmaSession(testClient(holdChapters: gate));
    await session.start();
    await tester.pumpWidget(
        _host(session, const ChapterScreen(system: SystemSlug.natal, chapter: 'core')));
    await _settle(tester);

    expect(find.text(_english), findsNothing);
    final dot = find.byType(WaitingDot);
    expect(dot, findsOneWidget, reason: 'знак ожидания вместо пустого экрана');
    final page = tester.getSize(find.byType(ChapterScreen));
    final middle = tester.getCenter(dot);
    expect(middle.dy, greaterThan(page.height * 0.3),
        reason: 'лоадер посреди экрана, а не строкой у края');
    expect(middle.dy, lessThan(page.height * 0.8));
    expect((middle.dx - page.width / 2).abs(), lessThan(4),
        reason: 'лоадер по центру, а не у поля');

    gate.complete();
    await _settle(tester);
    expect(find.text(_english), findsOneWidget,
        reason: 'оглавление ответило — глава дочитывается как обычно');
  });

  testWidgets('«Сегодня» перечитывает текст дня на новом языке', (tester) async {
    final session = AlmaSession(testClient());
    await session.start();
    await tester.pumpWidget(_host(session, const TodayScreen()));
    await _settle(tester);
    expect(readingPosts, hasLength(1));
    expect(readingPosts.single['locale'], 'en');

    await session.chooseLanguage('ru');
    await _settle(tester);

    // Как текст раскладывается по панелям — предмет `today_test`; здесь
    // закреплён сам контракт: смена языка — третья причина перечитать экран,
    // наравне со сменой профиля и прав, и просит она новый язык.
    expect(readingPosts, hasLength(2));
    expect(readingPosts.last['locale'], 'ru');
  });

  testWidgets('ответ, писавшийся на старом языке, не перекрывает новый',
      (tester) async {
    // Письмо главы идёт до трёх минут, и смена языка посреди него — обычное
    // дело. Старый ответ, доехавший после начала перечитывания, ставил бы
    // главу на прежнем языке под интерфейс на новом; побеждать обязан
    // последний заход, а не быстрейший (см. `_loadEpoch`).
    final hold = Completer<void>();
    final session = AlmaSession(testClient(holdEnglishReading: hold));
    await session.start();
    await tester.pumpWidget(
        _host(session, const ChapterScreen(system: SystemSlug.natal, chapter: 'core')));
    await _settle(tester);
    expect(find.text(_english), findsNothing, reason: 'английский ещё пишется');

    await session.chooseLanguage('ru');
    await _settle(tester);
    expect(find.text(_russian), findsOneWidget,
        reason: 'русский заход обогнал застрявший английский');

    hold.complete();
    await _settle(tester);
    expect(find.text(_russian), findsOneWidget);
    expect(find.text(_english), findsNothing,
        reason: 'устаревший ответ обязан умереть молча, а не сесть на экран');
  });

  testWidgets('оглавление системы перечитывает заголовки на новом языке',
      (tester) async {
    final session = AlmaSession(testClient());
    await session.start();
    await tester.pumpWidget(_host(
      session,
      Scaffold(
        body: SystemScreen(
          system: SystemSlug.natal,
          onOpenChapter: (_, _, {partner}) {},
        ),
      ),
    ));
    await _settle(tester);
    expect(find.text('Core'), findsOneWidget);

    await session.chooseLanguage('ru');
    await _settle(tester);

    expect(
      paths.where((p) => p == 'GET /v1/readings/natal/chapters?locale=ru'),
      isNotEmpty,
      reason: 'заголовки оглавления ключуются локалью и обязаны перечитаться',
    );
    expect(find.text('Ядро'), findsOneWidget);
    expect(find.text('Core'), findsNothing,
        reason: 'заголовок на прежнем языке под новым интерфейсом запрещён');
  });

  test('архив беседы и список бесед просят язык приложения', () async {
    // Серверный кеш переводов ключуется языком запроса; клиент, забывший его
    // приложить, получил бы реплики как записаны — на любом из семи языков.
    final client = testClient();
    await client.thread('t1', locale: 'ru');
    await client.threads(locale: 'pt-BR');
    expect(paths, contains('GET /v1/chat/threads/t1?locale=ru'));
    expect(paths, contains('GET /v1/chat/threads?locale=pt-BR'));
  });
}
