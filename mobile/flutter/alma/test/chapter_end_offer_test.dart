import 'dart:convert';

import 'package:alma/billing/alma_store.dart';
import 'package:alma/billing/ladder.dart';
import 'package:alma/design/art.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/net/models.dart';
import 'package:alma/screens/systems/chapter_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// V1 — оффер в конце дочитанной бесплатной главы.
///
/// **Что здесь сторожится и почему именно это.** Владелец, увидев кадр, сказал
/// про прежний вид: «по нашему дизайну эта перепродажа выглядит совсем
/// по-другому, она с картинкой, красивая». Разница между «совсем по-другому» и
/// «как надо» на этом экране складывается из трёх вещей, и ни одну из них не
/// поймает `flutter analyze`:
///
/// * **обложка** — карточка без картины это другая карточка;
/// * **шесть чипов вместо четырёх** — пять имён глав и счёт неназванных: чипы
///   делают работу, которую не сделает цена, и обрезанные до четырёх молчали о
///   том, что список не кончился;
/// * **инварианты кадра** — ни слова о подписке, тихая ссылка ровно одна и
///   ведёт на набор. Это правило P0, а не вкус: первая сессия несёт минимум
///   сущностей.

/// Восемь глав натала: первая бесплатна и открыта, семь платных закрыты — то
/// есть пять имён на кадре и «+2 more» шестым чипом.
const _paidTitles = [
  'Money and resources',
  'Work and calling',
  'The shadow',
  'Home and roots',
  'Freedom',
  'Dreams',
  'The circle',
];

/// Текст главы. Восемь абзацев — не для красоты: оффер поднимается по доле
/// прокрутки, а на странице, которая помещается в экран целиком, прокрутки нет
/// вовсе и порог недостижим.
const _wholeChapter =
    'Первый абзац бесплатной главы, дочитанной до самого низа страницы.';
const _body = [
  _wholeChapter,
  'Второй абзац этой бесплатной главы.',
  'Третий абзац этой бесплатной главы.',
  'Четвёртый абзац этой бесплатной главы.',
  'Пятый абзац этой бесплатной главы.',
  'Шестой абзац этой бесплатной главы.',
  'Седьмой абзац этой бесплатной главы.',
  'Восьмой абзац этой бесплатной главы.',
];

Map<String, Object?> _chapter(
  String slug,
  String numeral,
  int index,
  String title, {
  required bool free,
  required bool open,
}) =>
    {
      'slug': slug,
      'numeral': numeral,
      'index': index,
      'title': title,
      'question': '',
      'free': free,
      'open': open,
      'written': false,
      'needs_birth_time': false,
    };

AlmaClient _client() {
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
      body = [
        {
          'id': 'p1',
          'is_self': true,
          'birth_date': '1992-05-11',
          'latitude': 55.75,
          'longitude': 37.62,
          'timezone': 'Europe/Moscow',
        }
      ];
    } else if (path.endsWith('/chapters')) {
      body = {
        'system': 'natal',
        'total': _paidTitles.length + 1,
        'chapters': [
          _chapter('core', 'I', 1, 'Ядро', free: true, open: true),
          for (var i = 0; i < _paidTitles.length; i++)
            _chapter('paid$i', 'II', i + 2, _paidTitles[i],
                free: false, open: false),
        ],
      };
    } else if (path == '/v1/readings') {
      body = {
        'reading': {
          'system': 'natal',
          'chapter': 'core',
          'title': 'Ядро',
          'teaser': '',
          'body': _body,
          'cited_factors': <String>[],
          'read_from': '',
          'model': 'test',
        },
        'cached': true,
      };
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

Widget _host(AlmaSession session) => SessionScope(
      session: session,
      child: MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: const ChapterScreen(system: SystemSlug.natal, chapter: 'core'),
      ),
    );

/// Дочитать главу. Оффер поднимается по факту прокрутки (ТЗ §3 P1: «скролл
/// ≥85 %»), поэтому иначе его на кадре нет вовсе — и это правильно.
///
/// Прыжком позиции, а не жестом: флинг на всю страницу — это «рука», утащенная
/// за край, то есть заодно протяжка к следующей главе (урок `chapter_pull_test`).
Future<void> _readToEnd(WidgetTester tester) async {
  final position =
      tester.state<ScrollableState>(find.byType(Scrollable).first).position;
  var settled = position.maxScrollExtent;
  for (var i = 0; i < 40; i++) {
    await tester.pump(const Duration(milliseconds: 80));
    if (position.maxScrollExtent == settled && settled > 0) break;
    settled = position.maxScrollExtent;
  }
  position.jumpTo(position.maxScrollExtent);
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

Future<AlmaSession> _open(WidgetTester tester) async {
  // Кадр эталона, 402 × 874. Больше брать нельзя: страница обязана быть
  // длиннее экрана, иначе прокрутки нет вовсе и порог дочитанности недостижим.
  tester.view.physicalSize = const Size(402, 874) * 3;
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final session = AlmaSession(_client());
  await session.start();
  await tester.pumpWidget(_host(session));
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
  return session;
}

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    // Синглтон магазина заводится под iOS: по умолчанию в тестах платформа —
    // Android, и `InAppPurchase.instance` поднимает Play Billing, который
    // каналов не находит и роняет `PlatformException` мимо тела теста.
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    AlmaStore.shared;
    debugDefaultTargetPlatformOverride = null;
  });

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
    // Настоящего магазина в пробирке нет, а без цен нет ни кнопки, ни тихой
    // ссылки: число на них обязано прийти с полки, а не из головы.
    AlmaStore.shared.seedPrices({
      for (final key in LadderKey.values)
        key: ProductDetails(
          id: key.storeProductId,
          title: key.slug,
          description: '',
          price: key == LadderKey.bundleStatic ? r'$19.99' : r'$4.99',
          rawPrice: key == LadderKey.bundleStatic ? 19.99 : 4.99,
          currencyCode: 'USD',
        ),
    });
  });

  testWidgets('карточка оффера несёт обложку системы 66 × 88',
      (tester) async {
    await _open(tester);
    await _readToEnd(tester);

    final cover = find.byWidgetPredicate((widget) =>
        widget is Image &&
        widget.image is AssetImage &&
        (widget.image as AssetImage).assetName ==
            AlmaArt.card(SystemSlug.natal));
    expect(cover, findsOneWidget,
        reason: 'холст ставит в карточку card-natal — карту системы из '
            'бандла, а не вклейку главы по сети');
    expect(
        tester.getSize(
            find.ancestor(of: cover, matching: find.byType(Container)).first),
        const Size(66, 88));

    // Строки карточки: оверлайн, заголовок с числом глав и подпись под ним.
    expect(find.text('YOUR NATAL CHART READING'), findsOneWidget);
    expect(find.text('7 more chapters'), findsOneWidget);
    expect(
        find.text(
            'Every chapter written from your own positions, not from a template.'),
        findsOneWidget);
    expect(find.text('Yours forever · no subscription'), findsOneWidget);
  });

  testWidgets('пять имён глав и шестой чип со счётом неназванных',
      (tester) async {
    await _open(tester);
    await _readToEnd(tester);

    expect(find.text('WHAT THE REST HOLDS'), findsOneWidget);
    // Первое имя встречается дважды: тем же именем хвост страницы зовёт
    // следующую главу, и это не дубль чипа, а другая строка кадра.
    expect(find.text(_paidTitles.first), findsNWidgets(2));
    for (final title in _paidTitles.getRange(1, 5)) {
      expect(find.text(title), findsOneWidget, reason: 'имя главы чипом');
    }
    // Шестое и седьмое имена не показаны — вместо них счёт.
    expect(find.text(_paidTitles[5]), findsNothing);
    expect(find.text('+2 more'), findsOneWidget,
        reason: 'шестой чип говорит, что список не кончился');
  });

  testWidgets('ни слова о подписке, тихая ссылка одна и ведёт на набор',
      (tester) async {
    await _open(tester);
    await _readToEnd(tester);

    expect(find.text(r'All five readings — $19.99'), findsOneWidget);
    expect(find.text('All plans'), findsNothing,
        reason: 'витрины на первой сессии нет: тихая ссылка ровно одна');
    expect(find.textContaining('/ month'), findsNothing);
    expect(find.textContaining('renew'), findsNothing);
    // Цена двери стоит на кнопке — короткой подписью или полной, но стоит.
    expect(find.textContaining(r'$4.99'), findsWidgets);
  });
}
