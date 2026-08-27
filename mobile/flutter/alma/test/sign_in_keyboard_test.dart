import 'dart:convert';

import 'package:alma/design/buttons.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/screens/settings/sign_in_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Клавиатура уходит в ту же секунду, что принята шестая цифра.**
///
/// Владелец, 26.08.2026, с живого iPhone: «после входа зависает клавиатура».
/// Поле кода отключалось (`enabled: false`) с открытой связью посреди
/// автоподстановки кода из письма, а оба экрана входа уходили с фокусом
/// внутри — и системная клавиатура оставалась висеть над «Сегодня» без
/// хозяина. Единая кнопка закрытия снимает фокус до ухода (24 авг,
/// `AlmaClose`) — единственный приём, который на устройстве клавиатуру
/// убирал; автозакрытие после входа шло мимо него.
///
/// Саму зависшую системную клавиатуру тестовой обвязкой не поймать: здесь
/// уничтоженное поле закрывает связь честно, и «в конце спрятана» — правда и
/// на сломанном коде. Стережётся механизм: фокус снят и контекст
/// автозаполнения закрыт **до** того, как код ушёл на сервер, а не когда-
/// нибудь после; и ни одно поле не держит фокус ни на одном кадре до тишины.

AlmaClient _client({required VoidCallback onConsume}) {
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
      body = <Object>[];
    } else if (path == '/v1/auth/providers') {
      body = {'email': true};
    } else if (path == '/v1/auth/magic-link') {
      body = {'expires_in_minutes': 15};
    } else if (path == '/v1/auth/email-code/consume') {
      onConsume();
      body = {'token': 't2', 'user_id': 'u2', 'is_guest': false, 'locale': 'en'};
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

/// Экран, с которого открывают вход, — как «Сегодня» и настройки в приложении:
/// вход всегда лежит поверх, и после него сюда возвращаются.
class _Home extends StatelessWidget {
  const _Home();

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(
          child: TextButton(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => const SignInScreen()),
            ),
            child: const Text('open'),
          ),
        ),
      );
}

/// Небо анимируется без конца — `pumpAndSettle` здесь не оседает никогда.
Future<void> _settle(WidgetTester tester) async {
  for (var i = 0; i < 12; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

Finder _focusedField() => find.byWidgetPredicate(
      (w) => w is EditableText && w.focusNode.hasFocus,
      skipOffstage: false,
    );

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('фокус снят и автозаполнение закрыто до отправки кода',
      (tester) async {
    bool? focusedWhenSent;
    final session = AlmaSession(_client(
      onConsume: () => focusedWhenSent = _focusedField().evaluate().isNotEmpty,
    ));
    await session.start();
    await tester.pumpWidget(SessionScope(
      session: session,
      child: const MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: _Home(),
      ),
    ));

    await tester.tap(find.text('open'));
    await _settle(tester);
    expect(find.byType(SignInScreen), findsOneWidget);

    // Почта набирается с клавиатуры: поле в фокусе, как у живого человека.
    await tester.tap(find.byType(TextField));
    await tester.enterText(find.byType(TextField), 'a@b.co');
    await tester.pump();
    expect(_focusedField(), findsOneWidget, reason: 'поле почты в фокусе');

    await tester.tap(find.byType(AlmaButton).first);
    await _settle(tester);
    expect(find.byType(TextField), findsOneWidget,
        reason: 'экран шести ячеек открыт, поле почты под ним');
    expect(_focusedField(), findsOneWidget,
        reason: 'поле кода само взяло фокус — клавиатура поднята');

    tester.testTextInput.log.clear();
    await tester.enterText(find.byType(TextField), '123456');
    // Шестая цифра отправила код сама — и к этому моменту фокуса уже нет.
    expect(focusedWhenSent, isFalse,
        reason: 'поле держало фокус, когда код ушёл на сервер: клавиатура '
            'снимается отключением поля когда-нибудь потом, а не сразу');
    expect(
      tester.testTextInput.log.map((call) => call.method),
      contains('TextInput.finishAutofillContext'),
      reason: 'контекст автозаполнения кода из письма не закрыт вслух',
    );

    // Дальше — кадр за кадром до тишины: экран кода закрывается, экран почты
    // под ним закрывает себя сам, и ни одно поле не получает фокус обратно.
    for (var frame = 0; frame < 40; frame++) {
      await tester.pump(const Duration(milliseconds: 50));
      expect(_focusedField(), findsNothing,
          reason: 'кадр $frame: поле держит фокус после принятого кода');
    }
    expect(find.byType(SignInScreen), findsNothing,
        reason: 'оба экрана входа закрылись сами');
    expect(find.text('open'), findsOneWidget);
  });
}
