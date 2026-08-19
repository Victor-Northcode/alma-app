import 'dart:convert';

import 'package:alma/net/alma_client.dart';
import 'package:alma/notify/push_devices.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Зону, которой не знаем, не называем.**
///
/// Клиент отвечал `'UTC'` на всех трёх ветках неудачи — на вебе, без `TZ` и без
/// `/etc/localtime`, то есть **на всяком Android**, где такого файла нет вовсе.
/// Сервер эту строку принимает всерьёз: `is_known_timezone('UTC')` — правда,
/// зона садится в строку устройства, а `notify/rules.zone_for` ставит зону
/// устройства **выше** зоны рождения. Подписчик в Окленде получал утренний пуш
/// в восемь вечера. Тот же сервер ступень UTC у себя снёс намеренно — «законная
/// зона для того, кто в ней живёт, и незаконная догадка», — а клиент обходил
/// защиту снаружи. Незнание теперь называется незнанием: поля нет,
/// `tokens.register` оставляет прежнее известное значение.

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  group('разбор того, что отдала платформа', () {
    test('`TZ` именем IANA принимается как есть', () {
      expect(AlmaClient.ianaTimezone(envTz: 'Pacific/Auckland'),
          'Pacific/Auckland');
    });

    test('ссылка /etc/localtime читается до имени зоны', () {
      expect(
        AlmaClient.ianaTimezone(
            localtimeTarget: '/var/db/timezone/zoneinfo/Europe/Moscow'),
        'Europe/Moscow',
      );
    });

    test('короткое имя зоной не считается: сервер их не знает', () {
      // `geo.is_known_timezone` молча выбрасывает «MSK» и «+03», и отправленные
      // они значили бы ровно то же, что ничего, — но выглядели бы как знание.
      for (final short in const ['MSK', '+03', 'CET', 'EST5EDT']) {
        expect(AlmaClient.ianaTimezone(envTz: short), isNull,
            reason: '«$short» — не имя IANA');
      }
    });

    test('**голое «UTC» не проходит ни одной дорогой**', () {
      // Ровно та строка, которой чинилось незнание. Косая черта — весь
      // критерий, и она же не даёт ей вернуться.
      expect(AlmaClient.ianaTimezone(envTz: 'UTC'), isNull);
      expect(AlmaClient.ianaTimezone(localtimeTarget: '/usr/share/zoneinfo/UTC'),
          isNull);
      // А «Etc/UTC» — законное имя того, кто в ней живёт, и оно проходит.
      expect(AlmaClient.ianaTimezone(envTz: 'Etc/UTC'), 'Etc/UTC');
    });

    test('нет ни `TZ`, ни ссылки — нет и ответа (это Android)', () {
      // На Android `/etc/localtime` не существует вовсе. Здесь и стояло
      // `return 'UTC'`.
      expect(AlmaClient.ianaTimezone(), isNull);
      expect(AlmaClient.ianaTimezone(envTz: '', localtimeTarget: ''), isNull);
    });
  });

  test('неизвестная зона не едет в теле регистрации устройства', () {
    // `DeviceIn.timezone` объявлен необязательным, а `tokens.register` пишет
    // поле только когда оно пришло непустым: отсутствие поля оставляет серверу
    // ту зону, которую он уже знает, — прошлую настоящую вместо свежей выдумки.
    final unknown = PushDevice(
      platform: 'ios',
      token: 'a' * 64,
      environment: 'sandbox',
      timezone: null,
      locale: 'en',
    );
    expect(unknown.toJson().containsKey('timezone'), isFalse);

    final known = PushDevice(
      platform: 'ios',
      token: 'a' * 64,
      environment: 'sandbox',
      timezone: 'Pacific/Auckland',
      locale: 'en',
    );
    expect(known.toJson()['timezone'], 'Pacific/Auckland');
  });

  test('заголовок запроса либо несёт имя IANA, либо его нет', () async {
    // Что именно отдаст машина, на которой идут тесты, знать неоткуда — и это
    // не предмет проверки. Предмет — что догадка не уезжает: заголовка либо
    // нет, либо в нём настоящее имя.
    String? sent;
    var seen = false;
    final client = AlmaClient(
      baseUrl: Uri.parse('http://test.local'),
      http: MockClient((request) async {
        seen = true;
        sent = request.headers[AlmaClient.timezoneHeader] ??
            request.headers[AlmaClient.timezoneHeader.toLowerCase()];
        return http.Response(
            jsonEncode({
              'token': 't1',
              'user_id': 'u1',
              'is_guest': true,
              'locale': 'en',
            }),
            200,
            headers: {'content-type': 'application/json'});
      }),
    );

    await client.refresh();
    expect(seen, isTrue, reason: 'запрос не ушёл — проверять нечего');
    if (sent != null) {
      expect(sent, contains('/'),
          reason: 'в заголовок уехало короткое имя или догадка');
      expect(sent, isNot('UTC'));
    }
  });
}
