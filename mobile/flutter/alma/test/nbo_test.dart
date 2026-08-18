import 'package:flutter_test/flutter_test.dart';

import 'package:alma/state/nbo.dart';

void main() {
  test('матрица §4: каждая строка интереса даёт свой порядок', () {
    expect(
      nboOrder(const NboSignals(interest: 'love')).take(3),
      [NboCard.compatibility, NboCard.natal, NboCard.horoscope],
    );
    expect(
      nboOrder(const NboSignals(interest: 'money')).take(3),
      [NboCard.natal, NboCard.astrocartography, NboCard.horoscope],
    );
    expect(
      nboOrder(const NboSignals(interest: 'self')).take(3),
      [NboCard.natal, NboCard.synthesis, NboCard.horoscope],
    );
    expect(
      nboOrder(const NboSignals(interest: 'future')).take(3),
      [NboCard.horoscope, NboCard.solar, NboCard.natal],
    );
  });

  test('прочитанная глава любви поднимает совместимость всем', () {
    final order = nboOrder(const NboSignals(
        interest: 'money', loveChapterReadRecently: true));
    expect(order.first, NboCard.compatibility);
    // interest=money при этом не теряется — натал остаётся сразу за ней.
    expect(order[1], NboCard.natal);
  });

  test('пол — тай-брейкер и никогда не сильнее интереса', () {
    // interest=money держит свой порядок; совместимости в тройке нет,
    // и пол ничего не двигает.
    final money = nboOrder(const NboSignals(interest: 'money', femaleReader: true));
    expect(money.take(3), [NboCard.natal, NboCard.astrocartography, NboCard.horoscope]);
    // Без интереса совместимость из третьей позиции поднимается на вторую.
    final blank = nboOrder(const NboSignals(femaleReader: true));
    expect(blank.take(3), [NboCard.natal, NboCard.compatibility, NboCard.horoscope]);
  });

  test('три распробованные системы без набора добавляют карточку набора', () {
    final order = nboOrder(const NboSignals(
        interest: 'self', freeChaptersReadSystems: 3));
    expect(order.last, NboCard.bundle);
    final owned = nboOrder(const NboSignals(
        interest: 'self', freeChaptersReadSystems: 3, ownsBundle: true));
    expect(owned.contains(NboCard.bundle), isFalse);
  });

  test('всё открыто — коммерции нет вовсе', () {
    final order = nboOrder(const NboSignals(ownsEverything: true));
    expect(order.contains(NboCard.bundle), isFalse);
    expect(order.first, NboCard.horoscope);
  });
}
