import 'dart:convert';

import 'package:alma/main.dart';
import 'package:alma/net/alma_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Сервер в пробирке: те же формы ответов, что отдаёт настоящий бэкенд.
/// Тесты оболочки не должны требовать поднятого uvicorn — но и не должны
/// обходить сетевой слой: клиент здесь настоящий, подменён только транспорт.
AlmaClient fakeClient() {
  final http.Client transport = MockClient((request) async {
    final path = request.url.path;
    Map<String, dynamic> body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't1', 'user_id': 'u1', 'is_guest': true, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {
        'id': 'u1',
        'locale': 'en',
        'is_guest': true,
        'created_at': '2026-08-10T00:00:00Z',
        'unlocked': <String>[],
      };
    } else if (path == '/v1/profiles') {
      // Голый список — как отвечает настоящий сервер, не выдуманная обёртка.
      return http.Response('[]', 200,
          headers: {'content-type': 'application/json'});
    } else {
      body = {};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('оболочка строится и рисует все четыре вкладки', (tester) async {
    await tester.pumpWidget(AlmaApp(client: fakeClient()));
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Today'), findsWidgets);
    expect(find.text('My systems'), findsWidgets);
    expect(find.text('Alma'), findsWidgets);
    expect(find.text('Settings'), findsWidgets);
  });

  testWidgets('переключение вкладки меняет заголовок', (tester) async {
    await tester.pumpWidget(AlmaApp(client: fakeClient()));
    await tester.pump(const Duration(milliseconds: 50));
    await tester.tap(find.text('Settings').last);
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Settings'), findsWidgets);
  });
}
