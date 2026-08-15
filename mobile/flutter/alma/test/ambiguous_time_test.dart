import 'dart:convert';

import 'package:alma/net/alma_client.dart';
import 'package:alma/net/models.dart' show SystemSlug;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// Развилка перевода часов доезжает до экрана целой.
///
/// Ночь, в которую часы перевели назад, даёт два настоящих момента с разным
/// небом, и сервер отвечает 409, отказываясь бросать монетку. Экран развилки
/// может задать вопрос только при одном условии: до него доехали оба варианта
/// с именами часов и датой перевода. Стоит развилке превратиться в общий отказ
/// — и человек, родившийся в ту ночь, упирается в «что-то пошло не так» на
/// последнем шаге анкеты, без единого способа пройти дальше.
void main() {
  // Клиент по дороге читает токен из связки и идентификатор из настроек —
  // обе платформенные, обе в тестах подменяются заглушками.
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  /// Настоящее тело ответа: снято с `ambiguity_detail` в бэкенде.
  const body = {
    'detail': {
      'error': 'ambiguous_birth_time',
      'message': '1992-09-27T02:30:00 is ambiguous in Europe/Berlin',
      'timezone': 'Europe/Berlin',
      'transition_local_date': '1992-09-27',
      'options': [
        {
          'choice': 'earlier',
          'utc': '1992-09-27T00:30:00+00:00',
          'abbreviation': 'CEST',
          'offset_hours': 2.0,
        },
        {
          'choice': 'later',
          'utc': '1992-09-27T01:30:00+00:00',
          'abbreviation': 'CET',
          'offset_hours': 1.0,
        },
      ],
    },
  };

  AlmaClient clientAnswering(Object payload, {int status = 409}) => AlmaClient(
        baseUrl: Uri.parse('http://test.local'),
        http: MockClient((_) async => http.Response(jsonEncode(payload), status,
            headers: {'content-type': 'application/json'})),
      );

  test('409 приходит своим типом, а не общим отказом', () async {
    try {
      await clientAnswering(body).compute(SystemSlug.natal);
      fail('развилка обязана броситься');
    } on AmbiguousBirthTime catch (fork) {
      expect(fork.timezone, 'Europe/Berlin');
      expect(fork.transitionLocalDate, '1992-09-27');
      expect(fork.earlier?.abbreviation, 'CEST');
      expect(fork.later?.abbreviation, 'CET');
      // «Часом позже» на экране — это разница смещений, а не слово в вёрстке.
      expect(fork.gapHours, 1.0);
      expect(fork.earlier?.utc?.toIso8601String(), '1992-09-27T00:30:00.000Z');
    }
  });

  test('бросок переживает разбор, обёрнутый в глухой catch', () async {
    // **Ловушка, в которую этот код однажды попал.** Разбор тела 4xx обёрнут в
    // `catch (_) {}`, чтобы кривой JSON не ронял приложение. Бросок развилки
    // изнутри этого блока тот же `catch` и проглотил бы — человек получил бы
    // общий отказ, а не вопрос. Поэтому развилка собирается внутри, а бросается
    // за ним, и проверяется это здесь, а не читается глазами.
    try {
      await clientAnswering(body).compute(SystemSlug.natal);
      fail('проглочено');
    } on AmbiguousBirthTime catch (_) {
      // так и должно быть
    } on ServerRefused catch (e) {
      fail('развилка выродилась в общий отказ: ${e.code}');
    }
  });

  test('отказ без вариантов остаётся обычным отказом', () async {
    // Без списка вариантов вопроса не задать, и притворяться, что можно,
    // хуже честного отказа.
    const bare = {
      'detail': {'error': 'ambiguous_birth_time', 'message': 'нет вариантов'}
    };
    try {
      await clientAnswering(bare).compute(SystemSlug.natal);
      fail('должен был отказать');
    } on ServerRefused catch (e) {
      expect(e.code, 'ambiguous_birth_time');
      expect(e.status, 409);
    }
  });
}
