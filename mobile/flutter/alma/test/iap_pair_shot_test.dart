import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:alma/billing/alma_store.dart';
import 'package:alma/billing/ladder.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/net/models.dart';
import 'package:alma/screens/systems/chapter_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Кадр для App Store Connect: закрытая глава пары.**
///
/// Не тест-сторож, а съёмка: `--update-goldens` пишет
/// `goldens/iap-pair-check.png` — настоящий рендер `ChapterScreen`
/// совместимости тем же движком, теми же шрифтами и с ценой из витринного
/// списка, 1284 × 2778 физических пикселей. Снимается здесь, потому что
/// веб-прогон не смог дотапаться до главы пары (перехват жестов на экране
/// W3), а Apple ждёт кадр, где видны товар и цена.
AlmaClient _client() {
  final transport = MockClient((request) async {
    final path = request.url.path;
    Object body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't', 'user_id': 'u', 'is_guest': true, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {
        'id': 'u', 'locale': 'en', 'is_guest': true, 'created_at': '',
        'unlocked': <String>[],
      };
    } else if (path == '/v1/profiles') {
      body = [
        {
          'id': 'p1', 'is_self': true, 'birth_date': '1992-05-11',
          'birth_time': '11:26', 'latitude': 55.75, 'longitude': 37.62,
          'timezone': 'Europe/Moscow', 'name': 'Anatoly',
        },
        {
          'id': 'p2', 'is_self': false, 'birth_date': '1994-03-08',
          'birth_time': '09:45', 'latitude': 40.41, 'longitude': -3.7,
          'timezone': 'Europe/Madrid', 'name': 'Lina', 'relation': 'partner',
        },
      ];
    } else if (path.endsWith('/chapters')) {
      body = {
        'system': 'compatibility',
        'total': 4,
        'chapters': [
          {
            'slug': 'attraction', 'numeral': 'I', 'index': 1,
            'title': 'What pulls',
            'question': 'Why this person and not another?',
            'free': false, 'open': false, 'written': false,
            'needs_birth_time': false,
          },
          {
            'slug': 'friction', 'numeral': 'II', 'index': 2,
            'title': 'Where it catches',
            'question': 'What will we keep arguing about?',
            'free': false, 'open': false, 'written': false,
            'needs_birth_time': false,
          },
          {
            'slug': 'houses', 'numeral': 'III', 'index': 3,
            'title': 'Where we land in each other',
            'question': 'What part of my life does this person occupy?',
            'free': false, 'open': false, 'written': false,
            'needs_birth_time': false,
          },
          {
            'slug': 'whole', 'numeral': 'IV', 'index': 4,
            'title': 'The two of you as one thing',
            'question': 'What is the relationship itself like?',
            'free': false, 'open': false, 'written': false,
            'needs_birth_time': false,
          },
        ],
      };
    } else if (path == '/v1/readings') {
      body = {
        'system': 'compatibility', 'chapter': 'attraction',
        'locked': true, 'reading': null, 'opening': null,
        'product': 'pair.check', 'needs_partner': false, 'cached': false,
      };
    } else if (path.endsWith('/systems/natal')) {
      final payload = jsonDecode(request.body) as Map<String, dynamic>;
      final theirs = payload['profile_id'] == 'p2';
      body = {
        'system': 'natal',
        'data': {'sun_sign': theirs ? 'Pisces' : 'Taurus'},
      };
    } else {
      body = <String, dynamic>{};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    AlmaStore.shared;
    debugDefaultTargetPlatformOverride = null;
    // Настоящие гарнитуры вместо тестовой заглушки: кадр уходит в App Store.
    // Плюс шрифт иконок Material — иначе стрелка «назад» рисуется квадратом.
    {
      final loader = FontLoader('MaterialIcons');
      loader.addFont(File('C:/src/flutter/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf').readAsBytes().then((b) => b.buffer.asByteData()));
      await loader.load();
    }
    // Системный символьный шрифт: звезда ✦ и глифы зодиака в тестовой среде
    // без него рисуются квадратами (в приложении их даёт система).
    // И под именем Georgia — она стоит в цепочке дисплейных фолбэков, через
    // неё звезда ✦ доезжает до титульных стилей.
    for (final family in ['Segoe UI Symbol', 'Georgia']) {
      final loader = FontLoader(family);
      loader.addFont(File('C:/Windows/Fonts/seguisym.ttf')
          .readAsBytes().then((b) => b.buffer.asByteData()));
      await loader.load();
    }
    for (final (family, files) in [
      ('Playfair Display', ['PlayfairDisplay-Variable.ttf']),
      ('Golos Text', ['GolosText-Variable.ttf']),
      ('Lora', ['Lora-Variable.ttf']),
    ]) {
      final loader = FontLoader(family);
      for (final file in files) {
        loader.addFont(rootBundle.load('assets/fonts/$file'));
      }
      // Вторым файлом — символьный: ✦ и глифы зодиака берутся из него,
      // когда их нет в гарнитуре (в приложении это делает система).
      loader.addFont(File('C:/Windows/Fonts/seguisym.ttf')
          .readAsBytes().then((b) => b.buffer.asByteData()));
      await loader.load();
    }
  });

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
    // Плагина магазина в пробирке нет: экран зовёт load(), и SK2-каналы
    // взрываются PlatformException мимо теста. Задвижка держит load()
    // навсегда — цены уже посеяны.
    final gate = AlmaStore.loadGate = Completer<void>();
    addTearDown(() { if (!gate.isCompleted) gate.complete(); AlmaStore.loadGate = null; });
    AlmaStore.shared.seedPrices({
      for (final key in LadderKey.values)
        key: ProductDetails(
          id: key.storeProductId,
          title: key.slug,
          description: '',
          price: key == LadderKey.subMonthly
              ? r'$9.99'
              : key == LadderKey.bundleStatic
                  ? r'$19.99'
                  : r'$4.99',
          rawPrice: key == LadderKey.subMonthly
              ? 9.99
              : key == LadderKey.bundleStatic
                  ? 19.99
                  : 4.99,
          currencyCode: 'USD',
        ),
    });
  });

  testWidgets('кадр: закрытая глава пары с ценой за человека', tags: 'shots',
      (tester) async {
    // Кадр пишется в логических пикселях, поэтому холст — 1284 × 2778 @1x,
    // а телефонная вёрстка 428 × 926 масштабируется втрое при отрисовке:
    // векторы и глифы растеризуются в целевом размере, без мыла.
    tester.view.physicalSize = const Size(1284, 2778);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final session = AlmaSession(_client());
    await session.start();
    final partner = session.people.single;
    await tester.pumpWidget(SessionScope(
      session: session,
      child: MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        locale: const Locale('en'),
        theme: ThemeData(useMaterial3: true, brightness: Brightness.dark),
        home: Align(
          alignment: Alignment.topLeft,
          child: Transform.scale(
            scale: 3,
            alignment: Alignment.topLeft,
            child: SizedBox(
              width: 428,
              height: 926,
              child: MediaQuery(
              data: const MediaQueryData(
                size: Size(428, 926),
                devicePixelRatio: 3,
              ),
                child: ChapterScreen(
                  system: SystemSlug.compatibility,
                  chapter: 'attraction',
                  partner: partner,
                ),
              ),
            ),
          ),
        ),
      ),
    ));
    for (var i = 0; i < 30; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(find.textContaining('Per person'), findsOneWidget);
    expect(find.textContaining(r'$4.99'), findsWidgets);

    await expectLater(
      find.byType(ChapterScreen),
      matchesGoldenFile('goldens/iap-pair-check.png'),
    );
  });
}
