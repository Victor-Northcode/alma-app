import 'package:alma/design/sky/night_sky.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Небо — файл общий, и правка ради одного экрана обязана оставаться правкой
/// ради одного экрана.
///
/// V9 (отмена подписки) просит приглушённый купол: `rgba(58,52,132,.4)` вместо
/// `.5` и вуаль плотнее — `.55/.70/.95` против `.50/.68/.94`. Это добавленное
/// значение [SkyMood.hushed], а не новые числа у прежних трёх: кабинет, чтение
/// и церемония стоят на сорока восьми эталонных экранах, и сдвинуть их «заодно»
/// значит переписать весь продукт мимо холста.
void main() {
  test('приглушённое небо гасит только купол и уплотняет только вуаль', () {
    // .4 / .5 — купол гасится долей, а не своим вторым цветом.
    expect(SkyMood.hushed.domeAlpha, closeTo(0.8, 0.0001));
    expect(SkyMood.hushed.veil, const [
      Color(0x8C0A0D1C), // .55
      Color(0xB3090C1A), // .70
      Color(0xF2070A16), // .95
    ]);
    // Поле звёзд у кадра V9 то же, что у кабинета: спека называет две величины,
    // и приглушать заодно звёзды значило бы дорисовать за холст.
    expect(SkyMood.hushed.starIntensity, SkyMood.cabinet.starIntensity);
    expect(SkyMood.hushed.density, SkyMood.cabinet.density);
    expect(SkyMood.hushed.hasComet, isFalse);
  });

  test('у прежних трёх настроений купол и вуаль не тронуты', () {
    for (final mood in [SkyMood.cabinet, SkyMood.reading, SkyMood.ceremony]) {
      expect(mood.domeAlpha, 1.0, reason: '${mood.name}: купол полный');
      expect(mood.veil, const [
        Color(0x800A0D1C), // .50
        Color(0xAD090C1A), // .68
        Color(0xF0070A16), // .94
      ], reason: '${mood.name}: вуаль ночи как она есть');
    }
  });
}
