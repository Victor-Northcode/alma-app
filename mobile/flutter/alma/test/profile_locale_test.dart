import 'dart:convert';

import 'package:alma/net/alma_client.dart';
import 'package:alma/net/models.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Отказ приходит на языке запроса — потому что запрос называет язык.
///
/// `POST /v1/profiles` отвечает читателю одной фразой: 402 `partner_limit`,
/// «одно сохранённое сравнение — бесплатно». Язык этой фразы сервер берёт из
/// поля `locale` тела (`api/schemas.py`, `ProfileInput.locale` — «язык
/// *отказа*»), а без поля откатывается на `user.locale`. У свежего гостя там
/// стоит язык чеканки: наш `PATCH /v1/account` уходит без ожидания. То есть
/// первому гостю — тому, кто добавляет второго человека в первые минуты, —
/// отказ приходил по-английски.
///
/// Формы сняты с живого сервера 8018: то же тело с `"locale":"ru"` и `"de"`
/// отвечает по-русски и по-немецки, и обе фразы лежат в `alma/i18n/replies.py`.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  const birth = BirthInput(
    birthDate: '1990-03-01',
    latitude: 55.75,
    longitude: 37.61,
    timezone: 'Europe/Moscow',
    name: 'Мама',
  );

  test('язык уезжает в теле запроса', () async {
    late Map<String, dynamic> sent;
    final client = AlmaClient(
      baseUrl: Uri.parse('http://test.local'),
      http: MockClient((request) async {
        sent = (jsonDecode(request.body) as Map).cast<String, dynamic>();
        return http.Response(
            jsonEncode({
              'id': 'p2',
              'is_self': false,
              'birth_date': '1990-03-01',
              'latitude': 55.75,
              'longitude': 37.61,
              'timezone': 'Europe/Moscow',
            }),
            201,
            headers: {'content-type': 'application/json'});
      }),
    );

    await client.saveProfile(birth, locale: 'ru', isSelf: false);

    expect(sent['locale'], 'ru');
    // И рождение осталось рождением: язык не притворяется его частью.
    expect(sent['birth_date'], '1990-03-01');
    expect(sent['is_self'], false);
  });

  test('402 доезжает как отказ с кодом и готовой фразой', () async {
    // Тело — с живого сервера, слово в слово, включая `limit`.
    final client = AlmaClient(
      baseUrl: Uri.parse('http://test.local'),
      http: MockClient((request) async => http.Response(
            jsonEncode({
              'detail': {
                'error': 'partner_limit',
                'message': 'Одно сохранённое сравнение — бесплатно. Дверь '
                    'совместимости вмещает двоих, а подписка — столько людей, '
                    'сколько их в твоей жизни.',
                'limit': 1,
              }
            }),
            402,
            headers: {'content-type': 'application/json'},
          )),
    );

    try {
      await client.saveProfile(birth, locale: 'ru', isSelf: false);
      fail('сервер отказал — клиент обязан бросить');
    } on ServerRefused catch (refusal) {
      expect(refusal.status, 402);
      expect(refusal.code, 'partner_limit');
      // Экран показывает эту фразу дословно — значит, она обязана доехать
      // целой, а не превратиться в общее «что-то не работает».
      expect(refusal.message, startsWith('Одно сохранённое сравнение'));
    }
  });
}
