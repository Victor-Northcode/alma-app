import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// Французская типографика: узкий неразрывный пробел перед двойными знаками.
///
/// **Почему это тест, а не вкус.** Во французском перед `?`, `!`, `;`, `:` и
/// внутри кавычек-ёлочек стоит пробел — но не обычный. Обычный переносится:
/// строка рвётся, и вопросительный знак уезжает на следующую строку один.
/// Узкий неразрывный `U+202F` не рвётся и уже обычного, поэтому «est le tien ?»
/// выглядит французским текстом, а не английским с лишним пробелом.
///
/// Правило действует **на всю локаль разом**: половина файла по одному правилу,
/// половина по другому читается неряшливостью, а не решением.
///
/// **Близнец `backend/tests/test_french_spacing.py`, и это намеренно.** Тот
/// тест сторожит те же `.arb`, но живёт в наборе, который правящий французский
/// каталог никогда не запускает: правка `app_fr.arb` проверяется `flutter test`,
/// а красным становится `pytest` через десять минут в чужом окне. Проверка
/// должна падать там, где сделана правка. Пятая проверка здесь своя — её
/// серверному тесту неоткуда сделать.
void main() {
  final l10n = Directory('${Directory.current.path}/lib/l10n');

  /// Узкий неразрывный пробел. В исходнике он невидим, поэтому объявлен кодом:
  /// строка с настоящим знаком выглядит здесь как опечатка и однажды будет
  /// «исправлена» на обычный пробел.
  const nnbsp = ' ';

  /// Знаки, которым во французском положен пробел слева.
  const doubleMarks = '?!;:';

  Map<String, String> strings(String name) {
    final data =
        jsonDecode(File('${l10n.path}/$name').readAsStringSync()) as Map<String, dynamic>;
    return {
      for (final entry in data.entries)
        if (!entry.key.startsWith('@') && entry.value is String)
          entry.key: entry.value as String,
    };
  }

  test('во французском перед двойным знаком стоит узкий, а не обычный пробел', () {
    final offenders = [
      for (final entry in strings('app_fr.arb').entries)
        if (RegExp(' [${RegExp.escape(doubleMarks)}]').hasMatch(entry.value))
          '${entry.key}: ${entry.value}',
    ];
    expect(offenders, isEmpty,
        reason: 'обычный пробел переносится, и знак уедет на следующую строку '
            'один:\n  ${offenders.join('\n  ')}');
  });

  test('ёлочки прижаты к тексту тем же узким пробелом', () {
    final offenders = [
      for (final entry in strings('app_fr.arb').entries)
        if (entry.value.contains('« ') || entry.value.contains(' »'))
          '${entry.key}: ${entry.value}',
    ];
    expect(offenders, isEmpty,
        reason: 'внутри ёлочек нужен тот же узкий неразрывный:\n  '
            '${offenders.join('\n  ')}');
  });

  test('узкий пробел не протёк в остальные шесть языков', () {
    const others = {
      'en': 'app_en.arb', 'ru': 'app_ru.arb', 'de': 'app_de.arb',
      'es': 'app_es.arb', 'it': 'app_it.arb', 'pt-BR': 'app_pt.arb',
    };
    final dirty = [
      for (final locale in others.entries)
        for (final entry in strings(locale.value).entries)
          if (entry.value.contains(nnbsp)) '${locale.key}/${entry.key}',
    ];
    // Остальные шесть языков этого знака не знают, и попавший туда невидимый
    // пробел — мусор: он приедет в поиск, в буфер обмена и в чужой редактор.
    expect(dirty, isEmpty,
        reason: 'узкий неразрывный пробел — правило одного языка:\n  '
            '${dirty.join('\n  ')}');
  });

  test('правило где-то действительно применено', () {
    // Страховка от теста, который зелен, потому что проверять нечего: три
    // проверки выше пройдут и на файле без единого двойного знака. Эта падает,
    // если французский лишился их всех, — то есть если правило выполнили
    // удалением текста, а не расстановкой пробелов.
    final marked = strings('app_fr.arb')
        .values
        .fold(0, (n, value) => n + nnbsp.allMatches(value).length);
    expect(marked, greaterThanOrEqualTo(20),
        reason: 'узких пробелов всего $marked — правило где-то потерялось');
  });

  test('сгенерированный класс несёт те же узкие пробелы, что и каталог', () {
    // Показывается человеку не `.arb`, а `alma_l10n_fr.dart`, и он лежит в
    // репозитории рядом. Правка каталога без `flutter gen-l10n` оставляет
    // французский на экране прежним, и все четыре проверки выше при этом
    // зелены: они смотрят в исправленный файл, а приложение читает старый.
    final generated = File('${l10n.path}/alma_l10n_fr.dart').readAsStringSync();
    final catalogue = strings('app_fr.arb')
        .values
        .fold(0, (n, value) => n + nnbsp.allMatches(value).length);
    expect(nnbsp.allMatches(generated).length, catalogue,
        reason: 'каталог и сгенерированный класс разошлись — '
            'запустите `flutter gen-l10n`');
  });
}
