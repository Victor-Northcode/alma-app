import 'dart:convert';

import 'package:alma/main.dart';
import 'package:alma/net/alma_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Возврат в приложение перечитывает права.**
///
/// Оплата бывает и вне магазина приложения: страница `/pay` (Т-Банк, СБП)
/// выдаёт право вебхуком, пока приложение свёрнуто за браузером. До хука в
/// `_AlmaAppState.didChangeAppLifecycleState` заплативший на сайте возвращался
/// к закрытым главам и должен был догадаться перезапустить приложение — ТЗ
/// владельца от 29.08.2026 требует автоматической проверки прав.
///
/// Тест считает настоящие запросы `/v1/billing/entitlements`, а состояние
/// жизненного цикла шлёт тем же путём, каким его шлёт телефон, — через
/// binding. На коде без хука первый же `expect` падает: возврат не добавляет
/// ни одного запроса (проверено откатом 30.08.2026).
void main() {
  var entitlementCalls = 0;

  AlmaClient countingClient() {
    final http.Client transport = MockClient((request) async {
      final path = request.url.path;
      Map<String, dynamic> body;
      if (path == '/v1/auth/refresh') {
        body = {
          'token': 't1',
          'user_id': 'u1',
          'is_guest': false,
          'locale': 'en',
        };
      } else if (path == '/v1/account') {
        body = {
          'id': 'u1',
          'locale': 'en',
          'is_guest': false,
          'created_at': '2026-08-10T00:00:00Z',
          'unlocked': <String>[],
        };
      } else if (path == '/v1/profiles') {
        return http.Response(jsonEncode(<Map<String, dynamic>>[]), 200,
            headers: {'content-type': 'application/json'});
      } else if (path == '/v1/billing/entitlements') {
        entitlementCalls += 1;
        body = {
          'unlocked': <String>[],
          'entitlements': <Map<String, dynamic>>[],
          'currency': 'USD',
        };
      } else {
        body = {};
      }
      return http.Response(jsonEncode(body), 200,
          headers: {'content-type': 'application/json'});
    });
    return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
  }

  setUp(() {
    entitlementCalls = 0;
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('возврат в приложение перечитывает права, второй подряд — нет',
      (tester) async {
    await tester.pumpWidget(AlmaApp(client: countingClient()));
    // Заставка (3,4 с) и каскад старта сессии.
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 60));
    }
    await tester.pump(const Duration(seconds: 4));
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }

    final atLaunch = entitlementCalls;
    expect(atLaunch, greaterThan(0),
        reason: 'старт сессии обязан был прочитать права хотя бы раз');

    // Ушли в браузер платить и вернулись — как это шлёт телефон. Переходы
    // идут по лестнице жизненного цикла: binding стережёт порядок assert-ом,
    // и «paused → resumed» одним прыжком роняет тест о фреймворк, не о наш код.
    _away(tester);
    _back(tester);
    await tester.pump(const Duration(milliseconds: 80));

    expect(entitlementCalls, atLaunch + 1,
        reason: 'возврат в приложение не перечитал права — заплативший '
            'на сайте остался бы у закрытых глав');

    // Второй возврат через секунду — переключение окон, а не оплата: права
    // меняются покупкой, и минутный зазор бережёт сервер от возвратов.
    _away(tester);
    _back(tester);
    await tester.pump(const Duration(milliseconds: 80));

    expect(entitlementCalls, atLaunch + 1,
        reason: 'каждый возврат в приложение долбит /entitlements — '
            'минутный зазор не работает');
  });
}

/// В фон: resumed → inactive → hidden → paused, как их шлёт телефон.
void _away(WidgetTester tester) {
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
}

/// Обратно: paused → hidden → inactive → resumed.
void _back(WidgetTester tester) {
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
}
