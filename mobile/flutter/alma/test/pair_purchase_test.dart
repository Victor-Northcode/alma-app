import 'package:flutter_test/flutter_test.dart';

import 'package:alma/billing/ladder.dart';
import 'package:alma/net/models.dart';

void main() {
  test('расходуемая ступень ровно одна — проверка пары', () {
    // От ответа зависит магазинный вызов: consumable, купленный как
    // non-consumable, Play продаёт один раз за жизнь аккаунта.
    expect(LadderKey.pairCheck.consumable, isTrue);
    for (final key in LadderKey.values) {
      if (key == LadderKey.pairCheck) continue;
      expect(key.consumable, isFalse,
          reason: '${key.slug} не расходуемый и не должен им становиться');
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
