import 'package:flutter_test/flutter_test.dart';

import 'package:alma/state/pull_latch.dart';

void main() {
  test('рука взводит на 56 и подтверждает на 130', () {
    final latch = PullLatch();
    expect(latch.onScroll(30, byHand: true), PullEvent.none);
    expect(latch.onScroll(56, byHand: true), PullEvent.armed);
    expect(latch.onScroll(100, byHand: true), PullEvent.none);
    expect(latch.onScroll(130, byHand: true), PullEvent.committed);
    // Палец ушёл после упора — переворот.
    expect(latch.onScroll(80, byHand: false), PullEvent.advance);
    expect(latch.committed, isFalse, reason: 'упор одноразовый');
  });

  test('инерция не взводит и не переворачивает никогда', () {
    final latch = PullLatch();
    // Резкий смах: резинка глубже обоих порогов, но руки на стекле нет.
    expect(latch.onScroll(200, byHand: false), PullEvent.none);
    expect(latch.armed, isFalse);
    expect(latch.committed, isFalse);
    // И на возврате резинки тоже ничего.
    expect(latch.onScroll(40, byHand: false), PullEvent.none);
  });

  test('возврат выше гистерезиса снимает и взвод, и упор', () {
    final latch = PullLatch();
    latch.onScroll(140, byHand: true); // armed
    expect(latch.onScroll(140, byHand: true), PullEvent.committed);
    // Рука передумала: вернулась выше 0.7 × 56 = 39.2.
    expect(latch.onScroll(30, byHand: true), PullEvent.disarmed);
    expect(latch.committed, isFalse);
    // Отпускание после отката — не переворот.
    expect(latch.onScroll(10, byHand: false), PullEvent.none);
  });

  test('между порогами отпускание гасит подсветку без переворота', () {
    final latch = PullLatch();
    latch.onScroll(70, byHand: true); // armed, не committed
    expect(latch.onScroll(20, byHand: false), PullEvent.disarmed);
  });

  test('новая страница начинает с чистой решётки', () {
    final latch = PullLatch();
    latch.onScroll(140, byHand: true);
    latch.onScroll(140, byHand: true);
    latch.reset();
    expect(latch.armed, isFalse);
    expect(latch.committed, isFalse);
    expect(latch.onScroll(80, byHand: false), PullEvent.none);
  });
}
