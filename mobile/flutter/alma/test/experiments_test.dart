import 'package:flutter_test/flutter_test.dart';

import 'package:alma/state/experiments.dart';

void main() {
  test('один человек — всегда один вариант', () {
    final first = assignVariant(
        experiment: 'bundle_link_p1', subject: 'anon-1', arms: ['on', 'off']);
    for (var i = 0; i < 50; i++) {
      expect(
        assignVariant(
            experiment: 'bundle_link_p1', subject: 'anon-1', arms: ['on', 'off']),
        first,
        reason: 'вариант обязан быть детерминированным',
      );
    }
  });

  test('варианты распределяются, а не сваливаются в один', () {
    var on = 0;
    for (var i = 0; i < 1000; i++) {
      if (assignVariant(
              experiment: 'bundle_link_p1',
              subject: 'anon-$i',
              arms: ['on', 'off']) ==
          'on') {
        on++;
      }
    }
    // Не точность монетки, а отсутствие перекоса: и 400, и 600 годятся,
    // 0 или 1000 значили бы, что хеш не работает.
    expect(on, inInclusiveRange(400, 600));
  });

  test('разные эксперименты режут людей по-разному', () {
    var same = 0;
    for (var i = 0; i < 200; i++) {
      final a = assignVariant(
          experiment: 'exp-a', subject: 'anon-$i', arms: ['x', 'y']);
      final b = assignVariant(
          experiment: 'exp-b', subject: 'anon-$i', arms: ['x', 'y']);
      if (a == b) same++;
    }
    expect(same, inInclusiveRange(60, 140),
        reason: 'полное совпадение значило бы, что имя эксперимента не участвует');
  });
}
