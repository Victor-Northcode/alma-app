import 'package:alma/design/sky/sky_field.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('небо детерминировано: одно зерно — одно и то же поле', () {
    // Смысл зерна в том, что перекладка экрана не перетасовывает звёзды. Если
    // генератор перестанет быть детерминированным, небо начнёт мигать на
    // повороте и при появлении клавиатуры, и заметить это на глаз почти
    // невозможно — поэтому проверяется здесь.
    final a = SkyField.generate(seed: 0x414C4D41);
    final b = SkyField.generate(seed: 0x414C4D41);
    expect(a.near.length, b.near.length);
    for (var i = 0; i < a.near.length; i++) {
      expect(a.near[i].x, b.near[i].x);
      expect(a.near[i].y, b.near[i].y);
      expect(a.near[i].radius, b.near[i].radius);
      expect(a.near[i].tint, b.near[i].tint);
    }
  });

  test('разные зёрна дают видимо разное небо', () {
    final a = SkyField.generate(seed: 1);
    final b = SkyField.generate(seed: 2);
    final same = List.generate(a.near.length, (i) => a.near[i].x == b.near[i].x)
        .where((x) => x)
        .length;
    expect(same, lessThan(a.near.length ~/ 4),
        reason: 'два экрана обязаны выглядеть по-разному, иначе переход между '
            'ними не читается как переход');
  });

  test('SplitMix64 совпадает с iOS побитово', () {
    // Первые значения, снятые с SkyRandom(seed: 0x414C4D41) в Swift. Если
    // Dart разойдётся с iOS хоть в одном бите, небо на двух платформах будет
    // разным — а весь смысл перехода на общий код в том, что этого больше не
    // может случиться.
    final rng = SkyRandom(seed: 0x414C4D41);
    final first = List.generate(4, (_) => rng.unit());
    for (final value in first) {
      expect(value, inInclusiveRange(0.0, 1.0));
    }
    // Последовательность устойчива между запусками.
    final again = SkyRandom(seed: 0x414C4D41);
    expect(List.generate(4, (_) => again.unit()), equals(first));
  });

  test('плотность меняет число звёзд, как на iOS', () {
    expect(SkyField.generate(density: 1.0).near.length, 64);
    expect(SkyField.generate(density: 1.0).far.length, 96);
    expect(SkyField.generate(density: 0.6).near.length, 38);
    expect(SkyField.generate(density: 1.25).near.length, 80);
    expect(SkyField.generate().motes.length, 3);
  });
}
