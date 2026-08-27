import 'dart:convert';

import 'package:alma/net/alma_client.dart';
import 'package:alma/state/locale_override.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Язык у приложения один.** Интерфейс и то, что пишет Alma, говорят на
/// одном языке всегда — и он берётся из телефона, пока человек не выбрал
/// другой в настройках.
///
/// Владелец, 26.08.2026, с живого iPhone: «язык телефона английский, но
/// интерфейс на русском», «гороскоп при этом на английском — часть контента
/// на русском, часть на английском». Два языка жили порознь: интерфейс —
/// в `LocaleOverride` на диске, текст — в `account.locale` на сервере, и
/// связь между ними была односторонней: выбранный язык **выключал**
/// синхронизацию с устройством (`session.dart:133`) и больше ничего не делал.
/// Вход в аккаунт подменял аккаунт серверным, у которого стоял язык по
/// умолчанию `en`, — и главы уезжали на английский при русском интерфейсе.
///
/// Здесь закреплено: язык сервера всегда равен языку интерфейса, на каждом
/// старте и после каждой смены аккаунта; язык телефона — тот из списка
/// предпочтений, который продукт умеет; выбор языка телефона в настройках
/// снимает переопределение, и интерфейс снова следует за телефоном.

/// Сервер, который помнит язык аккаунта и записывает всё, что ему прислали.
class _Wire {
  _Wire({required this.server});

  String server;
  final patched = <String>[];
  var accountReads = 0;

  late final AlmaClient client = AlmaClient(
    baseUrl: Uri.parse('http://test.local'),
    http: MockClient(_answer),
  );

  Future<http.Response> _answer(http.Request request) async {
    final path = request.url.path;
    Object body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't', 'user_id': 'u', 'is_guest': true, 'locale': server};
    } else if (path == '/v1/account' && request.method == 'PATCH') {
      final sent = (jsonDecode(request.body) as Map)['locale'] as String;
      patched.add(sent);
      server = sent;
      body = <String, dynamic>{};
    } else if (path == '/v1/account') {
      accountReads += 1;
      body = {
        'id': 'u',
        'locale': server,
        'is_guest': true,
        'created_at': '',
        'unlocked': <String>[],
      };
    } else if (path == '/v1/profiles') {
      body = <Object>[];
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  }
}

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    LocaleOverride.reset();
  });

  testWidgets('выбранный язык доезжает до сервера на каждом старте — и после входа',
      (tester) async {
    tester.platformDispatcher.localesTestValue = const [Locale('en', 'US')];
    // Выбор лежит на диске; `restore()` намеренно не зовётся — сессия обязана
    // дождаться диска сама, иначе старт, обогнавший чтение, запишет на сервер
    // язык телефона поверх выбранного.
    SharedPreferences.setMockInitialValues({'alma.locale.override': 'ru'});
    final wire = _Wire(server: 'en');
    final session = AlmaSession(wire.client);

    await session.start();
    expect(session.locale, 'ru', reason: 'Alma пишет на языке интерфейса');
    expect(wire.patched, ['ru'], reason: 'сервер узнал язык при старте');

    // Вход: аккаунт сменился на серверный с языком по умолчанию. Ровно так
    // главы и уехали на английский у владельца.
    wire.server = 'en';
    await session.start(force: true);
    expect(session.locale, 'ru');
    expect(wire.patched.last, 'ru',
        reason: 'новому аккаунту язык интерфейса сообщается заново');

    tester.platformDispatcher.clearLocalesTestValue();
  });

  testWidgets('язык телефона — тот из списка предпочтений, который продукт умеет',
      (tester) async {
    // Телефон на украинском, второй язык — русский. Интерфейс Flutter решает
    // по всему списку и берёт русский; текст обязан взять тот же, а не
    // свалиться в английский оттого, что первый язык списка незнаком.
    tester.platformDispatcher.localesTestValue = const [
      Locale('uk', 'UA'),
      Locale('ru', 'RU'),
    ];
    SharedPreferences.setMockInitialValues({});
    final wire = _Wire(server: 'en');
    final session = AlmaSession(wire.client);

    await session.start();
    expect(session.locale, 'ru');
    expect(wire.patched, ['ru']);

    tester.platformDispatcher.clearLocalesTestValue();
  });

  testWidgets('pt любого региона: pt для интерфейса, pt-BR для сервера',
      (tester) async {
    tester.platformDispatcher.localesTestValue = const [Locale('en', 'US')];
    SharedPreferences.setMockInitialValues({});
    final wire = _Wire(server: 'en');
    final session = AlmaSession(wire.client);
    await session.start();

    await session.chooseLanguage('pt-BR');
    expect(LocaleOverride.value.value, const Locale('pt'),
        reason: 'у ARB нет региона');
    expect(session.locale, 'pt-BR', reason: 'у каталога сервера есть');
    expect(wire.patched.last, 'pt-BR');

    tester.platformDispatcher.clearLocalesTestValue();
  });

  testWidgets('выбор языка телефона снимает переопределение', (tester) async {
    tester.platformDispatcher.localesTestValue = const [Locale('en', 'US')];
    SharedPreferences.setMockInitialValues({'alma.locale.override': 'ru'});
    final wire = _Wire(server: 'ru');
    final session = AlmaSession(wire.client);
    await session.start();
    expect(session.locale, 'ru');

    // Выбран язык телефона: отдельной строки «как в телефоне» в списке нет,
    // и не нужно — совпадение с телефоном и есть «как в телефоне». Иначе
    // человек, однажды тронувший список, не вернул бы интерфейс за телефоном
    // никогда.
    await session.chooseLanguage('en');
    expect(LocaleOverride.value.value, isNull);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('alma.locale.override'), isNull);
    expect(session.locale, 'en');
    expect(wire.patched.last, 'en');

    await session.chooseLanguage('de');
    expect(LocaleOverride.value.value, const Locale('de'));
    expect(session.locale, 'de');
    expect(wire.patched.last, 'de');

    tester.platformDispatcher.clearLocalesTestValue();
  });
}
