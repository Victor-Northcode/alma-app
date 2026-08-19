import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// У пары нет бесплатного текста — и ни одна строка семи каталогов не обещает
/// обратного.
///
/// **Почему это тест, а не вычитка.** Владелец, 19.08.2026: «по паре немного
/// не понял мы не даем бесплатно пару никакую все за деньги можно писать
/// только имя». Бесплатны расчёт синастрии и место под человека — имя и дата
/// рождения; любой **написанный** текст пары платный, и сервер с того же дня
/// не пишет закрытой главе пары даже открывающего абзаца
/// (`readings.py::_locked_chapter`).
///
/// Обещание живёт в двадцати одной строке на семи языках, и держать его
/// вычиткой нельзя: перевод правит человек, который читает одну строку, а не
/// решение владельца. Строка «начало читается бесплатно», вернувшаяся в
/// португальский, — это экран, зовущий читать то, чего сервер не напишет, и
/// узнаётся она не на ревью, а в сторе.
///
/// **Правило, которое проверяется.** В строке про пару **предложение**, где
/// говорят о чтении или о главе, не смеет одновременно говорить «бесплатно»
/// или «до оплаты». Предложение, а не строка целиком: «Расчёт бесплатен.
/// Платишь за главы» — ровно то, что мы обещаем, и запрещать соседство слов в
/// разных фразах значило бы запрещать саму мысль.
///
/// **Второй тест — про сам сыщик.** Правило из слов семи языков молча
/// перестаёт ловить от одной опечатки в основе, и тогда первый тест зелен
/// потому, что не видит ничего. Поэтому ниже лежат **снятые** строки — те, что
/// стояли в каталогах до решения владельца, — и все двадцать одна обязаны быть
/// пойманы.
void main() {
  final l10n = Directory('${Directory.current.path}/lib/l10n');

  const catalogues = {
    'en': 'app_en.arb', 'ru': 'app_ru.arb', 'de': 'app_de.arb',
    'fr': 'app_fr.arb', 'es': 'app_es.arb', 'it': 'app_it.arb',
    'pt-BR': 'app_pt.arb',
  };

  /// Основы слова, а не слова целиком: языки склоняют. Совпадение считается с
  /// **начала** слова — иначе русское «считается» содержит «читается», и
  /// строка про бесплатный расчёт сама себя обвиняет.
  RegExp stems(List<String> parts) => RegExp(
        '(?<!\\p{L})(?:${parts.join('|')})',
        caseSensitive: false,
        unicode: true,
      );

  /// Чтение и главы — то, что у пары стоит денег.
  final written = stems([
    'read', 'chapter', 'capítulo', 'capitolo', 'kapitel', 'chapitre', 'глав',
    'lee', 'lect', 'legg', 'lies', 'liest', 'lis', 'lit', 'lire', 'lê', 'ler',
    'чита', 'прочит',
    // Название главы I на семи языках: «как начинается притяжение» — это
    // обещание текста, даже когда слово «глава» не сказано.
    'attraction', 'atracción', 'attrazione', 'anziehung', 'attirance',
    'atração', 'притяжен',
  ]);

  /// «Бесплатно» на семи языках.
  final free = stems([
    'free', 'frei', 'kostenlos', 'umsonst', 'gratis', 'grátis', 'gratuit',
    'gratuita', 'gratuito', 'offert', 'de graça', 'бесплат',
  ]);

  /// «До того, как заплатишь» — то же обещание без слова «бесплатно». Это
  /// форма, в которой оно и стояло в четырнадцати строках из двадцати одной.
  final before = RegExp(
    '(?<!\\p{L})(?:before|bevor|avant|antes|prima|до)(?!\\p{L})',
    caseSensitive: false,
    unicode: true,
  );

  /// Фразы, а не строка целиком. Точка с запятой считается концом фразы: во
  /// французском перед ней стоит узкий неразрывный пробел, и он остаётся в
  /// левой части — на поиск основ это не влияет.
  List<String> sentences(String value) =>
      value.split(RegExp(r'[.!?;…]')).where((s) => s.trim().isNotEmpty).toList();

  String? offence(String value) {
    for (final sentence in sentences(value)) {
      if (!written.hasMatch(sentence)) continue;
      if (free.hasMatch(sentence) || before.hasMatch(sentence)) return sentence;
    }
    return null;
  }

  Map<String, String> strings(String name) {
    final data =
        jsonDecode(File('${l10n.path}/$name').readAsStringSync()) as Map<String, dynamic>;
    return {
      for (final entry in data.entries)
        if (!entry.key.startsWith('@') && entry.value is String)
          entry.key: entry.value as String,
    };
  }

  /// Всё, что человек читает про пару: ключи пары и ключи совместимости — она
  /// же и есть пара, просто названная системой.
  bool aboutPairs(String key) {
    final lower = key.toLowerCase();
    return lower.contains('pair') || lower.contains('compat');
  }

  test('ни одна строка пары не обещает бесплатного текста', () {
    final offenders = <String>[];
    for (final locale in catalogues.entries) {
      for (final entry in strings(locale.value).entries) {
        if (!aboutPairs(entry.key)) continue;
        final caught = offence(entry.value);
        if (caught != null) {
          offenders.add('${locale.key}/${entry.key}: ${caught.trim()}');
        }
      }
    }
    expect(offenders, isEmpty,
        reason: 'у пары бесплатен расчёт, а не написанное:\n  '
            '${offenders.join('\n  ')}');
  });

  test('правило ловит те строки, ради которых написано', () {
    // Дословно то, что стояло в каталогах до 19.08.2026. Список полный: три
    // ключа на семь языков.
    const removed = <String>[
      'Their chart is calculated for free, like yours. How the first chapter — attraction — begins, you read before deciding anything.',
      'how Attraction begins is free to read',
      'A date of birth is enough — you read how Attraction begins before paying anything.',
      'Эта карта считается бесплатно, как и твоя. Как начинается первая глава — притяжение, — ты читаешь до любых решений.',
      'начало главы «притяжение» читается бесплатно',
      'Достаточно даты рождения — начало главы «притяжение» ты читаешь бесплатно, до всякой оплаты.',
      'Diese Karte wird kostenlos berechnet, wie deine. Wie das erste Kapitel — die Anziehung — beginnt, liest du, bevor du etwas entscheidest.',
      'wie die Anziehung beginnt, liest du kostenlos',
      'Das Geburtsdatum genügt — wie die Anziehung beginnt, liest du, bevor du irgendetwas bezahlst.',
      "Sa carte est calculée gratuitement, comme la tienne. Comment commence le premier chapitre — l'attirance —, tu le lis avant de décider quoi que ce soit.",
      "le début de l'attirance se lit gratuitement",
      "La date de naissance suffit — tu lis le début de l'attirance avant de payer quoi que ce soit.",
      'Su carta se calcula gratis, como la tuya. Cómo empieza el primer capítulo — la atracción — lo lees antes de decidir nada.',
      'cómo empieza la atracción se lee gratis',
      'Basta la fecha de nacimiento — lees cómo empieza la atracción antes de pagar nada.',
      "La sua carta si calcola gratis, come la tua. Come comincia il primo capitolo — l'attrazione — lo leggi prima di decidere.",
      "come comincia l'attrazione si legge gratis",
      "Basta la data di nascita — leggi come comincia l'attrazione prima di pagare qualsiasi cosa.",
      'O mapa se calcula de graça, como o seu. Como começa o primeiro capítulo — a atração — você lê antes de decidir qualquer coisa.',
      'como a atração começa lê-se de graça',
      'Basta a data de nascimento — você lê como a atração começa antes de pagar qualquer coisa.',
    ];
    expect(removed.length, 21);
    final missed = [for (final value in removed) if (offence(value) == null) value];
    expect(missed, isEmpty,
        reason: 'сыщик ослеп на этих строках — правило перестало работать:\n  '
            '${missed.join('\n  ')}');
  });

  test('каталог и сгенерированный класс говорят одно и то же', () {
    // Правка `.arb` без `flutter gen-l10n` оставляет на экране прежний текст, и
    // тест выше при этом зелен: он смотрит в исправленный файл, а приложение
    // читает соседний сгенерированный.
    const generated = {
      'en': 'alma_l10n_en.dart', 'ru': 'alma_l10n_ru.dart',
      'de': 'alma_l10n_de.dart', 'fr': 'alma_l10n_fr.dart',
      'es': 'alma_l10n_es.dart', 'it': 'alma_l10n_it.dart',
      'pt-BR': 'alma_l10n_pt.dart',
    };
    const keys = ['pairInputFreeNote', 'pairRowNotOpened', 'pairHookNote'];
    final stale = <String>[];
    for (final locale in catalogues.entries) {
      final catalogue = strings(locale.value);
      // Кавычка внутри строки уезжает в дарт как `\'` — сравнивать надо текст,
      // а не экранирование.
      final code = File('${l10n.path}/${generated[locale.key]}')
          .readAsStringSync()
          .replaceAll(r'\', '');
      for (final key in keys) {
        expect(catalogue[key], isNotNull, reason: '$key потерялся в ${locale.key}');
        if (!code.contains(catalogue[key]!)) stale.add('${locale.key}/$key');
      }
    }
    expect(stale, isEmpty,
        reason: 'каталог и класс разошлись — запустите `flutter gen-l10n`:\n  '
            '${stale.join('\n  ')}');
  });
}
