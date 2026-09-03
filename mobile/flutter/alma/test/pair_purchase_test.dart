import 'package:flutter_test/flutter_test.dart';

import 'package:alma/billing/ladder.dart';
import 'package:alma/net/models.dart';

void main() {
  test('расходуемых ступеней ровно пять — пара, три пачки и соляр', () {
    // От ответа зависит магазинный вызов: consumable, купленный как
    // non-consumable, Play продаёт один раз за жизнь аккаунта — а пачку
    // вопросов и соляр покупают повторно. Двери и подписка — наоборот:
    // расходуемая дверь позволила бы продать натал дважды одному человеку.
    // Набор закреплён волной пакетов 02.09.2026 (был «ровно одна — пара»).
    const consumable = {
      LadderKey.pairCheck,
      LadderKey.questions5,
      LadderKey.questions10,
      LadderKey.questions25,
      LadderKey.reportYear,
    };
    for (final key in LadderKey.values) {
      expect(key.consumable, consumable.contains(key),
          reason: consumable.contains(key)
              ? '${key.slug} покупается повторно — обязан быть расходуемым'
              : '${key.slug} не расходуемый и не должен им становиться');
    }
  });

  test('билет intent читает ответ сервера как есть', () {
    final ticket = PairIntentTicket.fromJson(const {
      'intent_id': 'abc',
      'app_account_token': '9f2f7b1e-9a1f-4d5e-8c3a-0b1d2e3f4a5b',
      'profile_id': 'p1',
      'product': 'pair.check',
    });
    expect(ticket.intentId, 'abc');
    expect(ticket.appAccountToken, '9f2f7b1e-9a1f-4d5e-8c3a-0b1d2e3f4a5b');
    expect(ticket.profileId, 'p1');
  });
}
