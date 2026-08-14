import 'dart:convert';
import 'dart:io';

import 'package:alma/main.dart';
import 'package:alma/net/alma_client.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
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

/// Тот же клиент, но сеть лежит: каждый запрос падает, как в метро.
AlmaClient deadNetworkClient() {
  final http.Client transport = MockClient((request) async {
    throw const SocketException('сеть недоступна');
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

  testWidgets('гостя без рождения встречает путешествие, не пустой кабинет',
      (tester) async {
    await tester.pumpWidget(AlmaApp(client: fakeClient()));
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 60));
    }
    // Первый шаг путешествия — вопрос имени — и обещание, что ничего не
    // сохраняется. Кабинет без рождения не рисуется вовсе.
    expect(find.text('What should I call you?'), findsOneWidget);
    expect(find.text('Today'), findsNothing);
  });

  testWidgets('упавшая сеть показывает отказ с повтором, а не анкету заново',
      (tester) async {
    // Профиль не пришёл не потому, что его нет, а потому что спросить не
    // удалось. Прежде оболочка читала пустой профиль как нового человека и
    // встречала анкетой того, у кого карта построена и оплачена, — приложение
    // выглядело так, будто стёрло всё. Натив в этом месте показывает отказ с
    // кнопкой, и здесь теперь то же самое.
    await tester.pumpWidget(AlmaApp(client: deadNetworkClient()));
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 60));
    }
    expect(find.text('What should I call you?'), findsNothing);
    expect(find.text('Try again'), findsOneWidget);
  });
}
