import 'dart:convert';

import 'package:alma/design/tab_bar.dart';
import 'package:alma/main.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/net/models.dart';
import 'package:alma/notify/push_devices.dart';
import 'package:alma/screens/systems/chapter_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Тап по уведомлению обязан куда-то вести.**
///
/// `AlmaPush.onOpened` писал ступень воронки и на этом заканчивался: человек,
/// разбуженный обещанием «сегодня Марс встаёт на твой Асцендент» или «отчёт по
/// вашей паре готов», попадал на ту вкладку, с которой ушёл в прошлый раз.
/// Пейлоад при этом всё называл — закрытый список типов в `docs/PUSH.md §2.3`:
/// `daily` ведёт на «Сегодня», `pair_ready` — в отчёт **этой** пары.

/// Партнёр, про которого приходит `pair_ready`.
const partnerId = 'p2';

AlmaClient pushClient() {
  final http.Client transport = MockClient((request) async {
    final path = request.url.path;
    Map<String, dynamic> body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't1', 'user_id': 'u1', 'is_guest': false, 'locale': 'en'};
    } else if (path == '/v1/account') {
      body = {
        'id': 'u1',
        'locale': 'en',
        'is_guest': false,
        'created_at': '2026-08-10T00:00:00Z',
        'unlocked': <String>[],
      };
    } else if (path == '/v1/profiles') {
      // Голый список — форма настоящего сервера: своё рождение и один
      // сохранённый человек, тот самый, про которого придёт пуш пары.
      return http.Response(
          jsonEncode([
            {
              'id': 'p1',
              'is_self': true,
              'birth_date': '1992-05-11',
              'birth_time': '11:26',
              'latitude': 55.75,
              'longitude': 37.62,
              'timezone': 'Europe/Moscow',
              'name': 'Anatoly',
            },
            {
              'id': partnerId,
              'is_self': false,
              'birth_date': '1990-02-02',
              'birth_time': '08:00',
              'latitude': 48.85,
              'longitude': 2.35,
              'timezone': 'Europe/Paris',
              'name': 'Marie',
            },
          ]),
          200,
          headers: {'content-type': 'application/json'});
    } else if (path == '/v1/systems/hub') {
      body = {
        'has_birth_data': true,
        'birth_time_known': true,
        'people': 1,
        'systems': <Map<String, dynamic>>[],
      };
    } else if (path == '/v1/systems/transits') {
      // «Сегодня» строится первым и разбирает расчёт строго: пустое тело
      // роняет `CalcResult.fromJson` мимо `AlmaError`, то есть мимо всякой
      // обработки экрана. Форма настоящая.
      body = {
        'system': 'transits',
        'engine_version': 'test',
        'computed_at': '2026-08-10T00:00:00Z',
        'subject': <String, dynamic>{},
        'data': {
          'sky_now': {
            'moon_phase': {
              'phase': 'waning crescent',
              'illumination': 0.07,
              'waxing': false,
            },
          },
          'active': <Map<String, dynamic>>[],
          'upcoming': <Map<String, dynamic>>[],
        },
        'factors': <String>[],
        'unavailable': <String>[],
        'notes': <String>[],
        'provenance': <String, dynamic>{},
        'access': {'allowed': true, 'reason': ''},
      };
    } else if (path == '/v1/readings') {
      body = {
        'reading': null,
        'locked': true,
        'product': 'sub.monthly',
        'opening': null,
        'cached': true,
      };
    } else if (path == '/v1/billing/entitlements') {
      body = {
        'unlocked': <String>[],
        'entitlements': <Map<String, dynamic>>[],
        'currency': 'USD',
      };
    } else if (path == '/v1/readings/compatibility/chapters') {
      // Первую главу пары называет сервер — клиент её не выдумывает.
      body = {
        'system': 'compatibility',
        'total': 1,
        'chapters': [
          {
            'slug': 'attraction',
            'numeral': 'I',
            'index': 0,
            'title': 'What pulls you together',
            'question': 'Why this person?',
            'free': true,
            'open': true,
            'written': true,
            'needs_birth_time': false,
          }
        ],
      };
    } else {
      body = {};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

/// Проматывает заставку (3,4 с) и каскады прихода вкладок.
Future<void> _openCabinet(WidgetTester tester) async {
  await tester.pumpWidget(AlmaApp(client: pushClient()));
  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 60));
  }
  await tester.pump(const Duration(seconds: 4));
  for (var i = 0; i < 12; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

Future<void> _frames(WidgetTester tester, {int count = 16}) async {
  for (var i = 0; i < count; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

/// Тап по уведомлению — **тем же путём, каким он приходит с телефона**.
///
/// `AppDelegate` кладёт строковые поля `userInfo` на канал `ai.pazl.alma/push`
/// вызовом `pushOpened`; отсюда и до экрана идёт весь настоящий путь — разбор
/// в `AlmaPush._deliver`, ступень воронки в корне, признак [pushedOpen],
/// оболочка. Ставить признак руками значило бы проверять половину дороги и
/// не заметить, если оборвётся первая.
Future<void> _tapPush(
    WidgetTester tester, Map<String, String> payload) async {
  await tester.binding.defaultBinaryMessenger.handlePlatformMessage(
    'ai.pazl.alma/push',
    const StandardMethodCodec()
        .encodeMethodCall(MethodCall('pushOpened', payload)),
    (_) {},
  );
}

/// На какой вкладке стоит кабинет. Вкладки живут одновременно, поэтому «что
/// нашлось в дереве» о месте не говорит ничего, а страница `PageView` говорит.
double _page(WidgetTester tester) =>
    tester.widget<PageView>(find.byType(PageView)).controller?.page ?? -1;

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
    pushedOpen.value = null;
  });

  tearDown(() => pushedOpen.value = null);

  testWidgets('тап по дневной заметке приводит на «Сегодня»', (tester) async {
    tester.view.physicalSize = const Size(700, 1600) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await _openCabinet(tester);
    // Уводим с «Сегодня»: иначе тест не отличит «пуш привёл» от «мы и так
    // здесь стояли».
    // Тапом по бару, а не смахом: с 25.08.2026 у смаха вкладок порог втрое
    // выше обычного (случайные диагонали при вертикальной прокрутке), и над
    // горизонтальными виджетами «Сегодня» он намеренно уступает им жест.
    // Подготовке теста нужен переход, а не проверка смаха.
    await tester.tap(find.text('My systems'));
    await _frames(tester);
    expect(_page(tester), closeTo(CabinetTab.systems.index.toDouble(), 0.01),
        reason: 'подготовка не сработала — мы всё ещё на «Сегодня»');

    // Тап по уведомлению. Пейлоад — как его отдаёт сервер (`PUSH.md §2.3`):
    // `date` в нём есть, но экран дня другой даты не знает, и клиент её не
    // выдумывает.
    await _tapPush(tester, const {'type': 'daily', 'date': '2026-08-19'});
    await _frames(tester);

    expect(_page(tester), closeTo(CabinetTab.today.index.toDouble(), 0.01),
        reason: 'тап по дневной заметке никуда не привёл');
    // Признак погашен: один тап открывает одно место один раз.
    expect(pushedOpen.value, isNull);
  });

  testWidgets('тап по готовому отчёту открывает совместимость с этим человеком',
      (tester) async {
    tester.view.physicalSize = const Size(700, 1600) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await _openCabinet(tester);
    expect(find.byType(ChapterScreen), findsNothing);

    await _tapPush(
        tester, const {'type': 'pair_ready', 'profile_id': partnerId});
    await _frames(tester);

    // Первая глава отчёта — и она про **того** человека, чей `profile_id`
    // приехал в пуше.
    final chapter = tester.widget<ChapterScreen>(find.byType(ChapterScreen));
    expect(chapter.system, SystemSlug.compatibility);
    expect(chapter.partner?.id, partnerId,
        reason: 'отчёт открылся не про того человека');
    expect(_page(tester), closeTo(CabinetTab.systems.index.toDouble(), 0.01),
        reason: 'глава пары живёт в стеке «Моих систем»');
  });

  testWidgets('пуш про неизвестного человека никуда не уводит',
      (tester) async {
    tester.view.physicalSize = const Size(700, 1600) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await _openCabinet(tester);

    // Профиль удалён после покупки — осиротевший грант. Открыть совместимость
    // «с кем-нибудь» значило бы показать отчёт про другого человека, а он
    // называет обоих поимённо.
    await _tapPush(tester, const {'type': 'pair_ready', 'profile_id': 'gone'});
    await _frames(tester);

    expect(find.byType(ChapterScreen), findsNothing);
    expect(_page(tester), closeTo(CabinetTab.today.index.toDouble(), 0.01));
  });

  testWidgets('незнакомый тип пуша ничего не открывает', (tester) async {
    tester.view.physicalSize = const Size(700, 1600) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await _openCabinet(tester);
    // Тапом по бару, а не смахом: с 25.08.2026 у смаха вкладок порог втрое
    // выше обычного (случайные диагонали при вертикальной прокрутке), и над
    // горизонтальными виджетами «Сегодня» он намеренно уступает им жест.
    // Подготовке теста нужен переход, а не проверка смаха.
    await tester.tap(find.text('My systems'));
    await _frames(tester);

    // Сборка старше сервера — обычное дело. Догадка «наверное, это про день»
    // увела бы человека не туда, что хуже, чем не двинуться.
    await _tapPush(tester, const {'type': 'weekly'});
    await _frames(tester);

    expect(find.byType(ChapterScreen), findsNothing);
    expect(_page(tester), closeTo(CabinetTab.systems.index.toDouble(), 0.01),
        reason: 'незнакомый тип увёл с места');
  });
}
