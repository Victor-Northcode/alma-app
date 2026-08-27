import 'dart:convert';

import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/net/models.dart';
import 'package:alma/screens/systems/chapter_screen.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Мета-строка «прочитано из» никогда не режется многоточием.**
///
/// Правило `AlmaShrink.fitMetaLine`: тело, градус и знак неделимы, режется
/// только хвост дома. Оно выполнялось по замеру — и нарушалось на экране:
/// на веб-сборке владелец увидел «Луна 12°39′ ♍ · 2…» (27.08.2026). Замер
/// шёл голым стилем строки, а `Text` рисует её, слив со стилем по умолчанию
/// `Material` (`bodyMedium`), у которого есть разрядка — 0.25 точки на
/// знак в Material 3. Двадцать знаков — пять точек, и вариант, «влезавший»
/// по замеру, на экране не влезал: многоточие съедало ровно то, ради чего
/// строка существует.
///
/// Разрядка в тесте увеличена до 1.5, а ширина строки перебирается масштабом
/// шрифта: где-то в этом ряду голый замер и живой рендер обязательно
/// разойдутся — если мерить не тем стилем, каким рисуют.

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
        'total': 1,
        'chapters': [
          {
            'slug': 'core',
            'numeral': 'I',
            'index': 1,
            'title': 'Ядро',
            'question': '',
            'free': true,
            'open': true,
            'written': true,
            'needs_birth_time': false,
          },
        ],
      };
    } else if (path == '/v1/readings') {
      body = {
        'reading': {
          'system': 'natal',
          'chapter': 'core',
          'title': 'Ядро',
          'teaser': '',
          'body': ['Один абзац.'],
          'cited_factors': [
            'moon 12°39′ virgo · house 2',
            'sun 20°51′ taurus · house 10',
            'ascendant 12°41′ leo',
          ],
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

/// Видимая мета-строка: та, у которой есть голосовая форма.
Finder _metaText() => find.byWidgetPredicate((w) =>
    w is Text && w.semanticsLabel != null && (w.data ?? '').startsWith('moon'));

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  testWidgets('режется только хвост дома — на экране, а не только по замеру',
      (tester) async {
    tester.view.physicalSize = const Size(402, 874) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);

    final session = AlmaSession(_client());
    await session.start();
    await tester.pumpWidget(SessionScope(
      session: session,
      child: MaterialApp(
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        theme: ThemeData(
          useMaterial3: true,
          textTheme: const TextTheme(bodyMedium: TextStyle(letterSpacing: 1.5)),
        ),
        home: const ChapterScreen(system: SystemSlug.natal, chapter: 'core'),
      ),
    ));
    for (var i = 0; i < 12; i++) {
      await tester.pump(const Duration(milliseconds: 80));
    }
    expect(_metaText(), findsOneWidget, reason: 'мета-строка на странице');

    for (var scale = 0.40; scale <= 1.00; scale += 0.02) {
      tester.platformDispatcher.textScaleFactorTestValue = scale;
      await tester.pump();
      await tester.pump();
      final text = tester.widget<Text>(_metaText()).data!;
      final paragraph = tester.renderObject<RenderParagraph>(
          find.descendant(of: _metaText(), matching: find.byType(RichText)));
      // Голое тело со знаком многоточие получить вправе — ему дали слишком
      // мало места. Всё, что с хвостом дома, обязано влезать целиком.
      if (text.contains(' · ')) {
        expect(paragraph.didExceedMaxLines, isFalse,
            reason: 'масштаб ${scale.toStringAsFixed(2)}: «$text» влезает по '
                'замеру и режется многоточием на экране');
      }
    }
  });
}
