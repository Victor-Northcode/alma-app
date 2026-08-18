import 'dart:convert';

import 'package:alma/billing/alma_store.dart';
import 'package:alma/billing/ladder.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/screens/paywall/plans_screen.dart';
import 'package:alma/screens/paywall/quota_screen.dart';
import 'package:alma/screens/paywall/subscription_screen.dart';
import 'package:alma/state/paywall_guard.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Три закона монетизации v3, проверенные на самих экранах.**
///
/// 1. Одна цена на экране: одна золотая кнопка и не более одной **продающей**
///    тихой ссылки. Лестница цен существует ровно на одном кадре — V8.
/// 2. Разовое и подписка не смешиваются: на разовом экране слова про продление
///    вне закона, на подписочном абзац продления обязателен и стоит **над**
///    кнопкой.
/// 3. Порядок донного блока V6 — ✦-строка о вечном, потом продление, потом
///    цена. Это защита от красной линии §7 ТЗ («думала, всё входит в
///    подписку»), и переставить его — значит снять защиту, ничего не сломав
///    на глаз.
///
/// Числа и высоты здесь не проверяются намеренно: в `flutter test` настоящих
/// шрифтов нет, подставной даёт строки примерно втрое выше, и любое снятое
/// отсюда число соврало бы. Проверяется то, что от шрифта не зависит: состав и
/// **порядок**.
void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    // Синглтон магазина заводится под iOS: по умолчанию в тестах платформа
    // Android, и `InAppPurchase.instance` поднимает Play Billing, который
    // каналов не находит и роняет `PlatformException` мимо тела теста.
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    AlmaStore.shared;
    debugDefaultTargetPlatformOverride = null;
  });

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
    PaywallGuard.reset();
    AlmaStore.shared.seedPrices({
      for (final key in LadderKey.values)
        key: _product(key.storeProductId, _price[key]!, _raw[key]!),
    });
  });

  testWidgets('V6 · подписка: «навсегда» и продление стоят над кнопкой',
      (tester) async {
    await _open(tester, const SubscriptionScreen());

    final forever = tester.getBottomLeft(
        find.text('Readings bought forever stay yours even without a subscription.'));
    final renewal = tester.getBottomLeft(find.textContaining('Renews monthly'));
    final button = tester.getTopLeft(find.textContaining(r'All of Alma'));

    expect(forever.dy, lessThan(renewal.dy),
        reason: 'строка о вечном читается первой из трёх');
    expect(renewal.dy, lessThan(button.dy),
        reason: 'абзац продления обязан стоять над ценой, а не под ней');

    // Правило 1: цен на экране одна — своя. Ни двери, ни бандла.
    expect(find.textContaining(r'$4.99'), findsNothing);
    expect(find.textContaining(r'$19.99'), findsNothing);
  });

  testWidgets('V7 · квота: вопрос стоит над ценой и назван удержанным',
      (tester) async {
    await _open(tester,
        const QuotaScreen(question: 'Will this year be easier than the last one?'));

    final asked =
        tester.getBottomLeft(find.text('Will this year be easier than the last one?'));
    final held = tester.getBottomLeft(find.textContaining('held —'));
    final title = tester.getTopLeft(find.textContaining('Three questions a month'));

    expect(asked.dy, lessThan(held.dy),
        reason: 'сначала вопрос, потом обещание, что он не потерян');
    expect(held.dy, lessThan(title.dy),
        reason: 'иначе экран читается как «заплати, чтобы вернуть своё»');
    expect(find.text(r'Ask on · $9.99 / month'), findsOneWidget);
    // Абзац продления здесь свой — он обещает отправку вопроса.
    expect(find.textContaining('your question sends the moment it opens'),
        findsOneWidget);
    // Ссылки на лестницу на этом кадре нет: пришли с вопросом, а не за тарифом.
    expect(find.text('All plans'), findsNothing);
  });

  testWidgets('V8 · все планы: две подписанные группы и строка-разделитель',
      (tester) async {
    await _open(tester, const PlansScreen());

    for (final label in const ['FOREVER', 'SUBSCRIPTION']) {
      expect(find.text(label), findsOneWidget, reason: label);
    }
    // Группа «навсегда» — три строки, и цена у каждой своя.
    expect(find.text('One reading'), findsOneWidget);
    expect(find.text('All five readings'), findsOneWidget);
    expect(find.text('A compatibility report'), findsOneWidget);
    expect(find.text(r'$4.99'), findsNWidgets(2));
    expect(find.text(r'$19.99'), findsOneWidget);
    // Подписка выделена не кнопкой, а карточкой и светлой ценой.
    expect(find.text('All of Alma'), findsOneWidget);
    expect(find.text(r'$9.99 / month'), findsOneWidget);

    final forever = tester.getBottomLeft(find.text('FOREVER'));
    final subscription = tester.getTopLeft(find.text('SUBSCRIPTION'));
    expect(forever.dy, lessThan(subscription.dy),
        reason: 'разовое стоит выше подписки — маленький честный первый платёж');

    // Строка, разделяющая ожидания, и юридический абзац за обе группы сразу.
    expect(
        find.text('What you bought forever does not disappear if you cancel.'),
        findsOneWidget);
    expect(find.textContaining('one-time purchases never renew'), findsOneWidget);
  });
}

/// Цены полки v3, ровно как в `backend/alma/billing/catalogue.py`.
const _price = <LadderKey, String>{
  LadderKey.natal: r'$4.99',
  LadderKey.numerology: r'$4.99',
  LadderKey.birthCard: r'$4.99',
  LadderKey.astrocartography: r'$4.99',
  LadderKey.synthesis: r'$4.99',
  LadderKey.pairCheck: r'$4.99',
  LadderKey.bundleStatic: r'$19.99',
  LadderKey.subMonthly: r'$9.99',
};

const _raw = <LadderKey, double>{
  LadderKey.natal: 4.99,
  LadderKey.numerology: 4.99,
  LadderKey.birthCard: 4.99,
  LadderKey.astrocartography: 4.99,
  LadderKey.synthesis: 4.99,
  LadderKey.pairCheck: 4.99,
  LadderKey.bundleStatic: 19.99,
  LadderKey.subMonthly: 9.99,
};

Map<String, dynamic> _plan(String slug, String kind, String display) => {
      'slug': slug,
      'name': slug,
      'kind': kind,
      'display': display,
      'interval': kind == 'monthly' ? 'month' : '',
      'scope': 'all',
      'offered': 'shelf',
    };

ProductDetails _product(String id, String price, double raw) => ProductDetails(
      id: id,
      title: id,
      description: id,
      price: price,
      rawPrice: raw,
      currencyCode: 'USD',
    );

/// Вьюпорт нарочно высокий: список экрана ленивый, и то, что ниже сгиба, просто
/// не строится. Проверки здесь про состав и порядок, а не про высоту.
Future<void> _open(WidgetTester tester, Widget screen) async {
  tester.view.physicalSize = const Size(402, 3000) * 3;
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  final session = AlmaSession(_client());
  await session.start();
  await tester.pumpWidget(SessionScope(
    session: session,
    child: MaterialApp(
      locale: const Locale('en'),
      localizationsDelegates: L.localizationsDelegates,
      supportedLocales: L.supportedLocales,
      home: screen,
    ),
  ));
  for (var i = 0; i < 12; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
  // **Чужие помехи, а не наши ошибки.** `in_app_purchase` в тестовой среде не
  // находит своих каналов и роняет `PlatformException` асинхронно; картинки
  // бандла в `flutter test` не читаются вовсе. Ни то ни другое не говорит о
  // вёрстке, а всё остальное обязано долететь до теста.
  final noise = tester.takeException();
  if (noise != null &&
      !noise.toString().contains('channel-error') &&
      !noise.toString().contains('Unable to load asset')) {
    throw noise;
  }
}

AlmaClient _client() {
  final transport = MockClient((request) async {
    final path = request.url.path;
    Object body = <String, dynamic>{};
    if (path == '/v1/auth/refresh') {
      body = {'token': 't1', 'user_id': 'u1', 'is_guest': true, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {
        'id': 'u1',
        'locale': 'en',
        'is_guest': true,
        'created_at': '2026-08-17T00:00:00Z',
        'unlocked': <String>[],
      };
    } else if (path == '/v1/profiles') {
      body = <Map<String, dynamic>>[];
    } else if (path == '/v1/billing/catalogue') {
      body = {
        'items': [
          for (final key in LadderKey.values)
            _plan(key.slug, key.isSubscription ? 'monthly' : 'one_time',
                _price[key]!),
        ],
      };
    } else if (path == '/v1/billing/entitlements') {
      body = {
        'unlocked': <String>[],
        'entitlements': <Map<String, dynamic>>[],
        'currency': 'USD',
      };
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}
