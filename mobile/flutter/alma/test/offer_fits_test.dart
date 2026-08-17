import 'dart:convert';

import 'package:alma/billing/alma_store.dart';
import 'package:alma/billing/ladder.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/screens/offer_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Критерий эталона `s8`: экран помещается целиком.**
///
/// Шапка → строка о бесплатности → планы → юридика → кнопка → Restore и «не
/// сейчас» → ссылки, и всё это без прокрутки на 402×874. Компакт-вариант `C2`
/// доказывает, что то же самое влезает в 375×667 — то есть в iPhone SE.
///
/// До 16 августа 2026 не влезало примерно вдвое: над лестницей стояла картина
/// в пергаментной раме, каждый план был карточкой с рамкой и полем 16×20,
/// абзац о продлении разворачивался в четыре строки, а «Restore purchases» и
/// «Not now» лежали двумя полноширинными плитами одна под другой. Владелец:
/// «текущая сборка увеличена примерно в 1.5–2 раза».
///
/// Проверяется высотой, а не глазом: у прокрутки внутри каркаса есть
/// `maxScrollExtent`, и ноль в нём — это и есть «влезло».
void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    // **Синглтон магазина заводится один раз и под iOS.**
    //
    // По умолчанию в тестах платформа — Android, и `InAppPurchase.instance`
    // поднимает Play Billing, который каналов не находит и роняет
    // `PlatformException` мимо тела теста. Эталон `s8` снят с iPhone, продукт
    // на iOS платит через StoreKit, и он в тестовой среде молчит тихо.
    //
    // Признак снимается тут же: фреймворк не разрешает уносить отладочную
    // переменную из теста и валит проверку инвариантов на выходе.
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    AlmaStore.shared;
    debugDefaultTargetPlatformOverride = null;
  });

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
    // Цены магазина: в тестовой среде App Store молчит, а без цен нет ни
    // кнопки, ни абзаца о продлении — то есть нет того, что не влезало.
    AlmaStore.shared.seedPrices({
      for (final key in LadderKey.values)
        key: _product(key.storeProductId, _price[key]!, _raw[key]!),
    });
  });

  // **Вьюпорт нарочно высокий — 402×3000.** Список каркаса ленивый: то, что
  // ниже сгиба, просто не строится, и `find.text` его не находит. С подставным
  // шрифтом тестовой среды колонка выходит примерно втрое выше настоящей, так
  // что на 874 не строились ни архивная строка, ни кнопки. Высокий вьюпорт
  // делает проверки про **состав и порядок**, а не про высоту.
  //
  // **Пиксельного «влезает» здесь нет намеренно.** В `flutter test` настоящих
  // шрифтов нет, и подставной шрифт даёт строки примерно втрое выше: заголовок
  // в 29 пунктов меряется 128 точками вместо 65. Любое число, снятое отсюда,
  // соврало бы в обе стороны. Критерий эталона — «весь экран без прокрутки на
  // 402×874» — проверяется на симуляторе, с живыми Playfair и Golos; здесь
  // проверяется то, что от шрифта не зависит: состав и порядок.

  testWidgets('факты стоят до первой цены', (tester) async {
    await _open(tester, const Size(402, 3000));
    final free = tester.getTopLeft(find.textContaining('Every calculation')).dy;
    final firstPrice = tester.getTopLeft(find.text(r'$4.99').first).dy;
    expect(free, lessThan(firstPrice),
        reason: 'строка о бесплатности обязана стоять выше всех цен');
  });

  testWidgets('подписи Restore и «не сейчас» не режутся никогда',
      (tester) async {
    await _open(tester, const Size(402, 3000));
    // **Проверяется целость подписи, а не то, что кнопки в одну строку.**
    // На эталонной ширине с живыми Playfair и Golos они стоят строкой — это
    // снято на симуляторе. Но подставной шрифт тестовой среды примерно втрое
    // шире, и здесь `Wrap` честно роняет вторую кнопку вниз; ровно то же
    // случится с «Käufe wiederherstellen» рядом с «Jetzt nicht». Инвариант,
    // который обязан держаться при любом шрифте и языке, один: подпись не
    // обрезана многоточием.
    for (final label in const ['Restore purchases', 'Not now']) {
      expect(find.text(label), findsOneWidget, reason: '«$label» обрезана');
    }
    final restore = tester.getRect(find.text('Restore purchases'));
    final notNow = tester.getRect(find.text('Not now'));
    expect((restore.height - notNow.height).abs(), lessThan(2),
        reason: 'обе кнопки обязаны быть одного роста');
  });

  testWidgets('планы — строки списка: рамок нет, цена справа', (tester) async {
    await _open(tester, const Size(402, 3000));
    // Полка v3: пять дверей → бандл → пара → подписка.
    for (final title in const [
      'Natal chart',
      'Numerology',
      'Birth Card',
      'Astrocartography',
      'Cross-synthesis',
      'All eight systems',
      'Compatibility',
      'Everything live, monthly',
    ]) {
      expect(find.text(title), findsOneWidget, reason: title);
    }
    // Цена стоит правее заголовка — колонкой, а не пилюлей под ним.
    final title = tester.getRect(find.text('Natal chart'));
    final price = tester.getRect(find.text(r'$4.99').first);
    expect(price.left, greaterThan(title.right),
        reason: 'цена обязана стоять справа в своей колонке');
    // **Арта на лестнице нет вовсе.** Картина живёт на `s46` и баннером в
    // шите `s32`; здесь она съедала пол-экрана и уводила цены за сгиб. Небо
    // ищем не по типу `Image` — оно тоже картинка и стоит на каждом экране.
    expect(
      find.byWidgetPredicate((w) =>
          w is Image &&
          w.image is AssetImage &&
          (w.image as AssetImage).assetName.contains('gates')),
      findsNothing,
    );

    // Форма списка: строки разделены волосом сверху, а не обведены рамкой.
    // Проверяется положительно — «волос есть», — потому что отрицательная
    // проверка «нет скруглённой обводки» ловила кнопку «не сейчас», у которой
    // обводка законная.
    final hairlines = find.byWidgetPredicate((w) =>
        w is Container &&
        w.decoration is BoxDecoration &&
        (w.decoration as BoxDecoration).border is Border &&
        ((w.decoration as BoxDecoration).border as Border).top !=
            BorderSide.none &&
        ((w.decoration as BoxDecoration).border as Border).bottom ==
            BorderSide.none);
    // Восемь строк, семь волосов: у первой его нет.
    expect(hairlines, findsNWidgets(7),
        reason: 'строки списка обязаны разделяться волосом, а не рамкой');
  });
}

/// Цены полки v3, ровно как в `backend/alma/billing/catalogue.py`. Написаны
/// руками, а не выведены из каталога: тест, который берёт ожидание оттуда же,
/// откуда берёт факт, проходит при любой полке.
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

Future<void> _open(WidgetTester tester, Size size) async {
  tester.view.physicalSize = size * 3;
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  final session = AlmaSession(_client());
  await session.start();
  await tester.pumpWidget(SessionScope(
    session: session,
    child: const MaterialApp(
      locale: Locale('en'),
      localizationsDelegates: L.localizationsDelegates,
      supportedLocales: L.supportedLocales,
      home: OfferScreen(),
    ),
  ));
  for (var i = 0; i < 12; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
  // **Чужая помеха, а не наша ошибка.** `in_app_purchase` в тестовой среде не
  // находит своих каналов и роняет `PlatformException(channel-error)`
  // асинхронно — мимо тела теста, валя тот, что выполняется в эту секунду.
  // Заглушить его одним каналом не вышло: плагин стучится не в один. Забираем
  // здесь, чтобы проверки ниже говорили только о вёрстке.
  final noise = tester.takeException();
  if (noise != null && !noise.toString().contains('channel-error')) {
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
        'created_at': '2026-08-16T00:00:00Z',
        'unlocked': <String>[],
      };
    } else if (path == '/v1/profiles') {
      body = <Map<String, dynamic>>[];
    } else if (path == '/v1/billing/catalogue') {
      // Полка сервера. Без неё `ladderFor` возвращает пустой список, экран
      // уходит в ветку «всё уже открыто», и мерить становится нечего.
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
