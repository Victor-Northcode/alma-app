import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:alma/design/plates.dart';
import 'package:alma/net/models.dart' show SystemSlug;

/// Карта вклеек сверяется с двумя источниками сразу: с каталогом глав движка и
/// с файлами на диске бэкенда.
///
/// Ошибиться здесь можно тихо в обе стороны. Забытая глава — арка с цифрой там,
/// где должна быть картина, и никто не заметит, пока не купит эту главу.
/// Опечатка в имени — 404 и та же арка, то есть та же тишина.
void main() {
  // Разделитель — любой: на Windows `Directory.current.path` отдаёт обратные
  // слэши, и регексп с прямыми не совпадал — «бэкенд» оказывался самим
  // каталогом приложения, существовал, и проверка искала картины не там
  // (два ложных красных в виндовой базе, ревью 27.08.2026).
  final backend = Directory.current.path.replaceFirst(
    RegExp(r'[/\\]mobile[/\\]flutter[/\\]alma$'),
    '/backend/static/plates',
  );

  /// Каталог глав движка. Дублируется здесь намеренно: тест обязан падать,
  /// когда главы в движке меняются, а карта — нет.
  const chapters = <SystemSlug, List<String>>{
    SystemSlug.natal: [
      'core', 'portrait', 'love', 'money', 'career', 'mind', 'shadow', 'roots',
      'karmic-axis', 'work-rhythms', 'transformation', 'freedom', 'dreams',
      'circle', 'worldview', 'milestones',
    ],
    SystemSlug.numerology: [
      'life-path', 'birthday-number', 'personal-year', 'pinnacles', 'name',
    ],
    SystemSlug.birthCard: ['personality', 'soul', 'year-card'],
    SystemSlug.transits: ['active', 'ahead', 'long'],
    SystemSlug.solarReturn: ['year-shape', 'emphasis', 'contacts'],
    SystemSlug.compatibility: ['attraction', 'friction', 'overlays', 'together'],
    SystemSlug.astrocartography: ['lines', 'here', 'crossings'],
    SystemSlug.synthesis: ['agreement', 'disagreement', 'single', 'whole'],
  };

  /// Дыр не осталось: последние шесть вклеек владелец прислал, и все главы
  /// каталога названы. Множество пустое намеренно — оно и есть сторож. Стоит
  /// добавить главу и забыть про картину, как арка молча покажет римскую цифру
  /// вместо картины, а этот тест — упадёт.
  const knownGaps = <String>{};

  test('карта знает ровно те главы, что есть в движке', () {
    for (final entry in chapters.entries) {
      final mapped = AlmaPlates.all[entry.key]?.keys.toSet() ?? {};
      expect(mapped, entry.value.toSet(),
          reason: 'у ${entry.key.slug} карта и движок разошлись');
    }
    expect(AlmaPlates.all.keys.toSet(), chapters.keys.toSet());
  });

  test('всего глав 41 — столько же, сколько в каталоге', () {
    final total = AlmaPlates.all.values.fold(0, (n, m) => n + m.length);
    expect(total, 41);
  });

  test('дыр не осталось: у каждой главы есть картина', () {
    final gaps = <String>{};
    AlmaPlates.all.forEach((system, map) {
      map.forEach((chapter, plate) {
        if (plate == null) gaps.add('${system.slug}/$chapter');
      });
    });
    expect(gaps, knownGaps, reason: 'появилась незаявленная дыра либо закрылась старая');
  });

  test('каждое названное имя лежит на диске бэкенда', () {
    if (!Directory(backend).existsSync()) {
      markTestSkipped('бэкенд не в этом чекауте');
      return;
    }
    final missing = <String>{};
    AlmaPlates.all.forEach((system, map) {
      map.forEach((chapter, plate) {
        if (plate == null) return;
        if (!File('$backend/$plate.webp').existsSync()) {
          missing.add('${system.slug}/$chapter → $plate');
        }
      });
    });
    expect(missing, isEmpty, reason: 'нет файлов: $missing');
  });

  test('вклейка ежедневника существует и не занята ни одной главой', () {
    final used = <String>{};
    for (final map in AlmaPlates.all.values) {
      used.addAll(map.values.whereType<String>());
    }
    expect(used, isNot(contains(AlmaPlates.today)),
        reason: 'plate-moon — арт «Сегодня», в главы его не класть');
    if (Directory(backend).existsSync()) {
      expect(File('$backend/${AlmaPlates.today}.webp').existsSync(), isTrue);
    }
  });

  test('синтез намеренно делит одну картину на четыре главы', () {
    final synthesis = AlmaPlates.all[SystemSlug.synthesis]!.values.toSet();
    expect(synthesis, {'plate-synthesis'});
  });

  test('вклейки с лицами спрятаны до новых картин; предметные — показываются',
      () {
    // Правило владельца от 29.08.2026: «убрать лица, кроме раздела
    // совместимости». Список `_faces` собран осмотром всех 41 файла глазами;
    // здесь закреплено поведение `name()`: лицо → null (цифра на пергаменте),
    // гравюра → своя картина, совместимость — целиком как была.
    expect(AlmaPlates.name(SystemSlug.natal, 'portrait'), isNull,
        reason: 'plate-face — буквально лицо');
    expect(AlmaPlates.name(SystemSlug.solarReturn, 'year-shape'), isNull,
        reason: 'plate-year — человек с книгой');
    expect(AlmaPlates.name(SystemSlug.transits, 'ahead'), 'plate-ahead',
        reason: 'фазы луны над дворцом — лиц нет, картина остаётся');
    expect(AlmaPlates.name(SystemSlug.astrocartography, 'lines'),
        'plate-lines', reason: 'глобус — предметная гравюра');
    expect(AlmaPlates.name(SystemSlug.compatibility, 'attraction'),
        'plate-pull', reason: 'пара остаётся со своими картинами целиком');
  });

  testWidgets('без store арка сразу показывает римскую цифру, а не пустоту',
      (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: PlateArch(store: null, plate: 'plate-love', numeral: 'III'),
      ),
    ));
    await tester.pump();
    expect(find.text('III'), findsOneWidget);
  });

  testWidgets('глава без арта показывает цифру, а не чужую картинку',
      (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: PlateArch(store: null, plate: null, numeral: 'II'),
      ),
    ));
    await tester.pump();
    expect(find.text('II'), findsOneWidget);
    expect(find.byType(Image), findsNothing);
  });
}
