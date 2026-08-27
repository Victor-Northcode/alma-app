import 'dart:async';
import 'dart:convert';

import 'package:alma/billing/alma_store.dart';
import 'package:alma/billing/ladder.dart';
import 'package:alma/design/buttons.dart';
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

/// Закрытая глава — это сама глава, дописанная наполовину.
///
/// Здесь сходятся три правила, и каждое стоило денег, пока не было записано.
///
/// **Первое: целую главу до покупки не пишут.** «Мы не должны сразу писать всю
/// главу, пока у человека нет подписки или купленного» — до этого решения
/// платная глава писалась сильной моделью целиком и показывалась размытой, то
/// есть за генерацию платили мы, на каждом, включая тех, кто не купит никогда.
///
/// **Второе: показать всё равно надо.** На месте отменённой пробы встала чёрная
/// стена «Unlock to read» — «ничего не показано, ничего не доказано, цены нет»,
/// — и `locked-chapter-spec.md` §5 удаляет её вместе с экраном «Alma сегодня
/// много для тебя написала · Посмотреть планы». Вместо них один паттерн: один
/// **написанный** абзац (`opening`, ≈40 слов средней моделью), размытый
/// клиентский филлер под ним и одна кнопка с ценой, стоящая **на** размытии.
///
/// **Третье: кнопка не ждёт сети.** Право известно из оглавления, поэтому титул
/// и цена стоят на первом кадре, а абзац дописывается сверху, когда приедет.
///
/// Тесты ниже держат все три и ту деталь, ради которой всё это рисовалось:
/// чистого разрыва между текстом и ценой нет.

/// Куда стучался клиент — по одной строке на запрос.
late List<String> calls;

/// Открывающий абзац — тот самый, который пишет движок закрытой главе.
const _opening = 'Leo on the first house means you are read before you speak, '
    'and the tell is Mercury at 9°14′ in the twelfth.';

/// Так выглядит текст целой главы. На закрытой его быть не должно ни строкой.
const _wholeChapter = 'Весь купленный текст главы, которого до оплаты нет.';

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

/// Ответ сервера на закрытую главу: 200, `reading` пуст, абзац отдельно.
Map<String, Object?> _locked(String system, String chapter, String product) => {
      'system': system,
      'chapter': chapter,
      'locked': true,
      'reading': null,
      'opening': {
        'system': system,
        'chapter': chapter,
        'title': 'Дело',
        'teaser': '',
        'body': [_opening],
        'cited_factors': ['ascendant 18°38′ leo'],
        'read_from': '',
        'model': 'test',
      },
      'product': product,
      'needs_partner': false,
      'cached': true,
    };

/// [hold] — сервер пишет абзац закрытой главы, пока тест не отпустит;
/// [silentOpening] — движок промолчал: `opening: null` при честном 200.
AlmaClient lockedClient({Completer<void>? hold, bool silentOpening = false}) {
  calls = [];
  final transport = MockClient((request) async {
    final path = request.url.path;
    calls.add('${request.method} $path');
    if (path == '/v1/readings' && hold != null) await hold.future;
    Object body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't', 'user_id': 'u', 'is_guest': true, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {'id': 'u', 'locale': 'en', 'is_guest': true, 'created_at': '', 'unlocked': []};
    } else if (path == '/v1/profiles') {
      body = [
        {'id': 'p1', 'is_self': true, 'birth_date': '1992-05-11',
         'latitude': 55.75, 'longitude': 37.62, 'timezone': 'Europe/Moscow'}
      ];
    } else if (path.contains('/transits/')) {
      // Живая система: бесплатных глав в ней нет вовсе — её продаёт подписка.
      body = {
        'system': 'transits',
        'total': 2,
        'chapters': [
          _chapter('active', 'I', 1, 'The sky now', free: false, open: false),
          _chapter('year', 'II', 2, 'The year', free: false, open: false),
        ],
      };
    } else if (path.endsWith('/chapters')) {
      // Натальная карта у гостя: первая глава бесплатна и открыта, вторая
      // закрыта — ровно то, что сервер печатает неоплатившему.
      body = {
        'system': 'natal',
        'total': 2,
        'chapters': [
          _chapter('core', 'I', 1, 'Ядро', free: true, open: true),
          _chapter('career', 'II', 2, 'Дело', free: false, open: false),
        ],
      };
    } else if (path == '/v1/readings') {
      final payload = jsonDecode(request.body) as Map<String, dynamic>;
      final system = payload['system'] as String;
      final chapter = payload['chapter'] as String;
      body = switch (chapter) {
        'career' => silentOpening
            ? (_locked(system, chapter, 'door.natal')..['opening'] = null)
            : _locked(system, chapter, 'door.natal'),
        'active' => _locked(system, chapter, 'sub.monthly'),
        _ => {
            'reading': {
              'system': system, 'chapter': chapter, 'title': 'Ядро',
              'teaser': '', 'body': [_wholeChapter],
              'cited_factors': <String>[], 'read_from': '', 'model': 'test',
            },
            'cached': true,
          },
      };
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

Widget host(AlmaSession session, SystemSlug system, String chapter) =>
    SessionScope(
      session: session,
      child: MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        home: ChapterScreen(system: system, chapter: chapter),
      ),
    );

/// Рисунок ожидания крутится вечно, и `pumpAndSettle` на нём не возвращается —
/// поэтому кадры отсчитываются руками, как в `chapter_pull_test`.
Future<void> settle(WidgetTester tester) async {
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

void _seedPrices() => AlmaStore.shared.seedPrices({
      for (final key in LadderKey.values)
        key: _product(
            key.storeProductId,
            key == LadderKey.subMonthly ? r'$9.99' : r'$4.99',
            key == LadderKey.subMonthly ? 9.99 : 4.99),
    });

ProductDetails _product(String id, String price, double raw) => ProductDetails(
      id: id,
      title: id,
      description: id,
      price: price,
      rawPrice: raw,
      currencyCode: 'USD',
    );

/// Высокий вьюпорт — не про красоту, а про то, что подставной шрифт тестовой
/// среды рисует строку примерно втрое выше настоящей. На 874 закрытая страница
/// упирается головой в низ ещё до размытого хвоста, и проверять на ней взаимное
/// положение блюра и кнопки бессмысленно.
Future<void> open(
  WidgetTester tester,
  AlmaSession session,
  SystemSlug system,
  String chapter,
) async {
  tester.view.physicalSize = const Size(402, 1400) * 3;
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(host(session, system, chapter));
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
    // Без цен нет кнопки: число на ней обязано совпасть со списанным, и
    // молчащий App Store рисует вместо неё честное «купить сейчас нельзя».
    _seedPrices();
  });

  testWidgets('закрытая глава просит абзац, а не главу', (tester) async {
    final session = AlmaSession(lockedClient());
    await session.start();
    await open(tester, session, SystemSlug.natal, 'career');
    await settle(tester);

    expect(calls.where((c) => c == 'POST /v1/readings'), hasLength(1),
        reason: 'ровно один запрос — за открывающим абзацем');
    expect(find.text(_wholeChapter), findsNothing,
        reason: 'целая глава до покупки не пишется и не показывается');
    expect(find.text(_opening), findsOneWidget,
        reason: 'ради этого абзаца стена и удалена: живой текст с позициями');
    expect(find.text(r'Unlock and read · $4.99'), findsOneWidget);
  });

  testWidgets('цена стоит на первом кадре, до всякой сети', (tester) async {
    final session = AlmaSession(lockedClient());
    await session.start();
    // Так и бывает в жизни: в главу заходят с экрана системы, который только
    // что показал это оглавление.
    await session.client.chapters(SystemSlug.natal, locale: session.locale);

    await open(tester, session, SystemSlug.natal, 'career');
    await tester.pump();

    expect(find.text(r'Unlock and read · $4.99'), findsOneWidget,
        reason: 'кнопка обязана быть сразу, без экрана ожидания');
    expect(find.text('Дело'), findsOneWidget, reason: 'титул из оглавления');
    // «Пишу эту главу…» — экран того, кому текст положен.
    expect(find.text('Writing this chapter…'), findsNothing);
  });

  testWidgets('пока абзац пишется — ожидание, а не ошибка', (tester) async {
    // Владелец (27.08.2026): «проверь, чтоб на страницах глав не было ошибки
    // на нашей стороне, пока не будет реальной ошибки — лоадер, пока ждём,
    // что ИИ ответит». Абзац закрытой главы — вызов модели на секунды и
    // десятки секунд, и всё это время на месте абзаца стояла ветка отказа с
    // «попробовать ещё раз»: у экрана не было состояния «в пути».
    final hold = Completer<void>();
    final session = AlmaSession(lockedClient(hold: hold));
    await session.start();
    await open(tester, session, SystemSlug.natal, 'career');
    await settle(tester);

    expect(calls.where((c) => c == 'POST /v1/readings'), hasLength(1));
    expect(find.textContaining('Something on our side'), findsNothing,
        reason: 'сервер ещё не ответил — ошибки нет');
    expect(find.text('Try again'), findsNothing);
    expect(find.text(r'Unlock and read · $4.99'), findsOneWidget,
        reason: 'кнопка с ценой ждать не обязана');
    // Размытый хвост приходит вместе с настоящим абзацем, а не раньше:
    // размытие под лоадером читалось «текст уже есть, его прячут»
    // (владелец, 27.08.2026). Лоадер — посреди свободного места страницы.
    expect(find.byType(ImageFiltered), findsNothing,
        reason: 'размытия нет, пока нет текста');
    final spinner = find.byType(CircularProgressIndicator);
    expect(spinner, findsOneWidget, reason: 'на месте абзаца — ожидание');
    final page = tester.getSize(find.byType(ChapterScreen));
    final middle = tester.getCenter(spinner);
    expect(middle.dy, greaterThan(page.height * 0.3),
        reason: 'лоадер посреди экрана, а не строкой у линейки');
    expect(middle.dy, lessThan(page.height * 0.8));
    // Правое поле страницы на 4 точки шире левого (GiltPage.sideRight),
    // поэтому центр колонки стоит на 2 точки левее центра экрана.
    expect((middle.dx - page.width / 2).abs(), lessThan(4),
        reason: 'лоадер по центру, а не у левого поля');

    hold.complete();
    await settle(tester);
    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.text(_opening), findsOneWidget);
    expect(find.byType(ImageFiltered), findsOneWidget,
        reason: 'размытие пришло вместе с текстом');
  });

  testWidgets('«Секунду» — та же кнопка, что и цена: меняется только надпись',
      (tester) async {
    // Владелец (27.08.2026): «кнопка с надписью „Секунду“ — это кнопка
    // всегда, и меняется в ней только надпись». Пока полка не ответила, на
    // месте цены стоит тот же золотой `AlmaButton` тех же размеров с
    // «Секунду»; цена дописывается в него, а не заменяет его другим виджетом.
    AlmaStore.shared.seedPrices({});
    final gate = AlmaStore.loadGate = Completer<void>();
    addTearDown(() {
      if (!gate.isCompleted) gate.complete();
      AlmaStore.loadGate = null;
    });
    final session = AlmaSession(lockedClient());
    await session.start();
    await open(tester, session, SystemSlug.natal, 'career');
    await settle(tester);

    final waiting = find.widgetWithText(AlmaButton, 'One moment');
    expect(waiting, findsOneWidget, reason: 'ожидание цены — кнопка');
    expect(tester.widget<AlmaButton>(waiting).kind, AlmaButtonKind.gold);
    final before = tester.getRect(waiting);

    // Полка ответила. Настоящего магазина в пробирке нет, и его ответ —
    // те же цены, что сеет `setUp`.
    gate.complete();
    _seedPrices();
    await settle(tester);
    final priced = find.widgetWithText(AlmaButton, r'Unlock and read · $4.99');
    expect(priced, findsOneWidget);
    expect(find.widgetWithText(AlmaButton, 'One moment'), findsNothing);
    expect(tester.widget<AlmaButton>(priced).kind, AlmaButtonKind.gold);
    expect(tester.getRect(priced), before,
        reason: 'кнопка не меняет ни места, ни размера — только надпись');
  });

  testWidgets('движок промолчал — вот тогда предложение повторить',
      (tester) async {
    final session = AlmaSession(lockedClient(silentOpening: true));
    await session.start();
    await open(tester, session, SystemSlug.natal, 'career');
    await settle(tester);

    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.textContaining('Something on our side'), findsOneWidget,
        reason: 'сервер ответил без абзаца — это настоящая правда');
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('под ценой сказана природа покупки, удалённых экранов нет',
      (tester) async {
    final session = AlmaSession(lockedClient());
    await session.start();
    await open(tester, session, SystemSlug.natal, 'career');
    await settle(tester);

    expect(find.text('Yours forever · no subscription'), findsOneWidget);
    // Позиции, из которых прочитан абзац, — на экране, а не только в тексте.
    expect(find.text('READ FROM'), findsOneWidget);
    // Экраны, которые удалили: ни заголовка стены, ни кнопки «см. планы».
    expect(find.text('Unlock to read'), findsNothing);
    expect(find.text('See the plans'), findsNothing);
  });

  testWidgets('размытие проходит под кнопкой, чистой полосы нет',
      (tester) async {
    final session = AlmaSession(lockedClient());
    await session.start();
    await open(tester, session, SystemSlug.natal, 'career');
    await settle(tester);

    final blur = tester.getRect(find.byType(ImageFiltered));
    final cta = tester.getRect(find.byType(AlmaButton));

    expect(blur.top, lessThan(cta.top),
        reason: 'размытая колонка начинается выше кнопки');
    expect(blur.bottom, greaterThanOrEqualTo(cta.bottom),
        reason: 'между текстом и ценой не должно быть чистой полосы — '
            'покупка обязана читаться как «открыть продолжение»');
    expect(blur.left, lessThanOrEqualTo(cta.left));
    expect(blur.right, greaterThanOrEqualTo(cta.right));
  });

  testWidgets('филлер не читается скринридером и кнопка на экране одна',
      (tester) async {
    final session = AlmaSession(lockedClient());
    await session.start();
    final handle = tester.ensureSemantics();
    await open(tester, session, SystemSlug.natal, 'career');
    await settle(tester);

    // Филлер нарисован…
    expect(find.textContaining('The second layer of this belongs'),
        findsOneWidget);
    // …и при этом голосу его не отдают: он ничего не значит, и читать вслух
    // три абзаца нейтральной прозы тому, кто не видит размытия, — обман.
    expect(find.bySemanticsLabel(RegExp('The second layer')), findsNothing);
    expect(find.bySemanticsLabel('Unlock to read'), findsOneWidget,
        reason: 'вместо филлера голос говорит, чем этот блок является');

    expect(find.byType(AlmaButton), findsOneWidget,
        reason: 'ровно одна кнопка на экране');
    handle.dispose();
  });

  testWidgets('живая система продаёт подписку и обещает не «навсегда»',
      (tester) async {
    final session = AlmaSession(lockedClient());
    await session.start();
    await open(tester, session, SystemSlug.transits, 'active');
    await settle(tester);

    expect(find.text(r'All of Alma · $9.99 / month'), findsOneWidget);
    expect(find.text('UPDATES DAILY'), findsOneWidget,
        reason: 'бейдж живой системы — часть шапки, а не украшение');
    expect(find.text('Yours forever · no subscription'), findsNothing,
        reason: 'у транзитов «навсегда» не бывает: они пересчитываются');
    expect(find.text(r'Unlock and read · $4.99'), findsNothing);
  });

  testWidgets('открытая глава по-прежнему приходит целиком', (tester) async {
    final session = AlmaSession(lockedClient());
    await session.start();
    await open(tester, session, SystemSlug.natal, 'core');
    await settle(tester);

    expect(find.text(_wholeChapter), findsOneWidget,
        reason: 'бесплатная глава пишется как писалась');
    expect(find.text('FREE'), findsOneWidget,
        reason: 'единственная бесплатная глава продукта помечена');
    expect(find.byType(AlmaButton), findsNothing,
        reason: 'на открытой главе продавать нечего');
  });
}
