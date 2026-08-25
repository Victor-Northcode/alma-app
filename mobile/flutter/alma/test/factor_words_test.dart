import 'dart:ui' show Locale;

import 'package:flutter_test/flutter_test.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/screens/cabinet_words.dart';

/// Балансовые факты в мета-строке «прочитано из» говорят на языке читателя.
///
/// Владелец, 25.08.2026: русская глава носила подпись «Прочитано из dominant
/// element» — движок цитирует не только позиции, и всё, что не тело и не
/// аспект, проходило словарь нетронутым.
void main() {
  late L ru;
  late L en;

  setUpAll(() async {
    ru = await L.delegate.load(const Locale('ru'));
    en = await L.delegate.load(const Locale('en'));
  });

  test('доминантная стихия — фразой каталога', () {
    expect(CabinetWordsMore.factor(ru, 'dominant element fire'),
        'стихия-доминанта — огонь');
    expect(CabinetWordsMore.factor(en, 'dominant element fire'),
        'dominant element — fire');
  });

  test('доминантная планета — с переведённым телом', () {
    expect(CabinetWordsMore.factor(ru, 'dominant planet saturn'),
        'планета-доминанта — Сатурн');
  });

  test('фаза Луны, лунный день и секта — тоже', () {
    expect(CabinetWordsMore.factor(ru, 'moon phase waxing gibbous'),
        contains('фаза Луны'));
    expect(CabinetWordsMore.factor(ru, 'lunar day 11'), 'лунный день 11');
    expect(CabinetWordsMore.factor(ru, 'day birth'), 'дневное рождение');
  });

  test('отсутствующая стихия', () {
    expect(CabinetWordsMore.factor(ru, 'no water in the chart'),
        'вода в карте отсутствует');
  });

  test('позиции как раньше: тело, градус, глиф, дом', () {
    expect(CabinetWordsMore.factor(ru, 'sun 24°17′ ♌︎ · house 10'),
        'Солнце 24°17′ ♌ · 10-й дом');
  });
}
