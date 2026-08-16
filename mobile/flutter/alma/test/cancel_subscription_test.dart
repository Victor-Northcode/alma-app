import 'dart:convert';

import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/screens/settings/settings_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Сколько раз ушла отмена. Это и есть предмет проверки: два шага, о которых
/// нельзя судить по нарисованному тексту, — судить о них можно только по тому,
/// сколько запросов ушло к моменту первого нажатия.
int cancelCalls = 0;

/// Конец оплаченного периода. Одно число для всего файла: экран показывает его
/// первым шагом (из `expires_at`) и повторяет после отмены (из `access_until`),
/// и это обязано быть одно и то же число.
const periodEnds = '2027-03-04T00:00:00Z';

/// Настройки подписчика. [source] — кто продал подписку, и это единственная
/// разница между двумя мирами: `appstore` отменяет Apple, `paddle` — мы.
AlmaClient settingsClient({required String source, bool cancelFails = false}) {
  cancelCalls = 0;
  final transport = MockClient((request) async {
    final path = request.url.path;
    Object body;
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
      // Голый список — форма настоящего сервера.
      body = <Map<String, dynamic>>[];
    } else if (path == '/v1/notifications') {
      body = {'daily': 'off', 'hour': 10};
    } else if (path == '/v1/billing/entitlements') {
      body = {
        'unlocked': ['natal'],
        'entitlements': [
          {
            'active': true,
            'kind': 'monthly',
            'scope': 'all',
            'system': '*',
            'source': source,
            'renews_at': periodEnds,
            'expires_at': periodEnds,
          }
        ],
        'currency': 'USD',
      };
    } else if (path == '/v1/billing/subscription/cancel') {
      cancelCalls++;
      if (cancelFails) {
        // 502 — платёжная система не ответила, и сервер **ничего не записал**.
        return http.Response(
            jsonEncode({
              'detail': {
                'error': 'cancel_failed',
                'message': 'we could not reach the payment processor',
              }
            }),
            502,
            headers: {'content-type': 'application/json'});
      }
      body = {
        'cancelled': true,
        'provider': 'paddle',
        'subscription_ids': ['sub_1'],
        'access_until': periodEnds,
        'renews_at': null,
      };
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

/// Английский прибит гвоздями: иначе поисковые строки зависели бы от языка
/// машины, на которой запускают тесты.
Widget host(AlmaSession session) => SessionScope(
      session: session,
      child: const MaterialApp(
        locale: Locale('en'),
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        // Material — то, что даёт настоящему экрану оболочка кабинета: без
        // него InkWell в списке настроек не строится вовсе.
        home: Scaffold(body: SettingsScreen()),
      ),
    );

Future<void> settle(WidgetTester tester) async {
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

/// Открыть настройки в окне высотой во весь экран.
///
/// **Окно здесь не украшение.** Настройки длиннее тестовых 800×600, а ленивый
/// список не строит того, что за краем: в обычном окне «Отменить подписку»
/// просто нет в дереве, и тест, который его «не нашёл», доказал бы не границу
/// магазина, а собственную прокрутку.
Future<AlmaSession> openSettings(WidgetTester tester, AlmaClient client) async {
  tester.view.physicalSize = const Size(900, 5000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  final session = AlmaSession(client);
  await session.start();
  await tester.pumpWidget(host(session));
  await settle(tester);
  return session;
}

/// Нажать по подписи, доведя её до видимой части экрана.
///
/// Настройки длиннее любого окна — и тестового в 800×600 тем более, — а
/// нажатие мимо видимой области тестовый привод просто не доставляет.
Future<void> tapText(WidgetTester tester, String label) async {
  final target = find.text(label);
  await tester.ensureVisible(target);
  await tester.pump();
  await tester.tap(target);
  await settle(tester);
}

/// То же число и по тем же правилам, что печатает экран.
String readable(String instant) =>
    DateFormat.yMMMMd('en').format(DateTime.parse(instant).toLocal());

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('подписке из App Store отмена внутри приложения не предлагается',
      (tester) async {
    await openSettings(tester, settingsClient(source: 'appstore'));

    // Отменяет её Apple, и говорит об этом экран — своей строкой и ссылкой в
    // магазин. Кнопки отмены нет вовсе: предложить её здесь — нарушение
    // правил магазина и обещание, которого сервер не сдержит (409).
    expect(find.text('Cancel subscription'), findsNothing);
    expect(find.text('Manage this subscription in the App Store'),
        findsOneWidget);
    expect(
        find.textContaining('bought in the App Store', findRichText: true),
        findsOneWidget);
    expect(cancelCalls, 0);
  });

  testWidgets('первое нажатие ничего не отправляет, второе отменяет',
      (tester) async {
    await openSettings(tester, settingsClient(source: 'paddle'));

    // Подписку продали мы — кнопка есть.
    expect(find.text('Cancel subscription'), findsOneWidget);

    // ШАГ ПЕРВЫЙ. Разворачивает объяснение — и не касается сети.
    await tapText(tester, 'Cancel subscription');
    expect(cancelCalls, 0,
        reason: 'первое нажатие обязано только объяснить, а не отменить');
    expect(find.textContaining('The next charge stops'), findsOneWidget);
    // Дата конца оплаченного периода — голым числом под объяснением.
    expect(find.text(readable(periodEnds)), findsOneWidget);
    expect(find.text('Keep my plan'), findsOneWidget);

    // ШАГ ВТОРОЙ. Та же красная кнопка — и вот теперь запрос.
    await tapText(tester, 'Cancel subscription');
    expect(cancelCalls, 1);
    // Дата в подтверждении — из ответа сервера, и это то же число.
    expect(find.textContaining('stays open until ${readable(periodEnds)}'),
        findsOneWidget);
    // И ни одного удержания по дороге: между шагами стоит только «оставить
    // план», без скидок и без третьего экрана.
    expect(find.textContaining('%'), findsNothing);
  });

  testWidgets('«оставить план» закрывает форму, так ничего и не отправив',
      (tester) async {
    await openSettings(tester, settingsClient(source: 'paddle'));

    await tapText(tester, 'Cancel subscription');
    await tapText(tester, 'Keep my plan');

    expect(cancelCalls, 0);
    expect(find.textContaining('The next charge stops'), findsNothing);
    // Кнопка вернулась: передумать в обе стороны можно сколько угодно раз.
    expect(find.text('Cancel subscription'), findsOneWidget);
  });

  testWidgets('отказ платёжной системы не уносит форму', (tester) async {
    await openSettings(
        tester, settingsClient(source: 'paddle', cancelFails: true));

    await tapText(tester, 'Cancel subscription');
    await tapText(tester, 'Cancel subscription');

    expect(cancelCalls, 1);
    // Ничего не изменилось — так и сказано, и есть чем повторить.
    expect(find.textContaining('nothing has changed'), findsOneWidget);
    expect(find.text('Cancel subscription'), findsOneWidget);
    expect(find.text('Keep my plan'), findsOneWidget);
  });
}
