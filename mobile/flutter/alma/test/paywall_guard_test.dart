import 'package:alma/billing/ladder.dart';
import 'package:alma/design/palette.dart' show readingNow;
import 'package:alma/net/models.dart' show SystemSlug;
import 'package:alma/state/paywall_guard.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Инварианты §5 ТЗ — те, что нельзя проверить глазами.**
///
/// Их четыре, каждый однажды нарушится молча, и ни один не виден на кадре:
/// пейволл поверх пейволла заметен только тому, у кого он случился; десять
/// минут после покупки — вообще никому, кроме человека, которому продали
/// дважды. Поэтому они лежат отдельной вещью без единого виджета вокруг, и
/// проверяются здесь.
void main() {
  setUp(() {
    PaywallGuard.reset();
    readingNow.value = false;
  });

  tearDown(() {
    PaywallGuard.reset();
    readingNow.value = false;
  });

  test('по умолчанию показывать можно', () {
    expect(PaywallGuard.check(proactive: false), PaywallRefusal.none);
    expect(PaywallGuard.check(proactive: true), PaywallRefusal.none);
  });

  test('пейволл никогда не встаёт поверх другого пейволла', () {
    PaywallGuard.onScreen = true;
    expect(PaywallGuard.check(proactive: false), PaywallRefusal.overPaywall);
  });

  test('во время чтения главы цена не появляется', () {
    readingNow.value = true;
    expect(PaywallGuard.check(proactive: false), PaywallRefusal.whileReading);
  });

  test('десять минут после покупки продукт молчит', () {
    final bought = DateTime(2026, 8, 17, 12);
    PaywallGuard.notePurchase(bought);
    expect(
      PaywallGuard.check(
          proactive: false, now: bought.add(const Duration(minutes: 9, seconds: 59))),
      PaywallRefusal.afterPurchase,
      reason: 'девять минут — это ещё «сразу после покупки»',
    );
    expect(
      PaywallGuard.check(
          proactive: false, now: bought.add(const Duration(minutes: 10))),
      PaywallRefusal.none,
      reason: 'ровно десять минут — граница, и она открытая',
    );
  });

  test('проактивный оффер за сессию один, тапнутых — сколько угодно', () {
    PaywallGuard.noteProactive();
    expect(PaywallGuard.check(proactive: true), PaywallRefusal.proactiveSpent);
    expect(PaywallGuard.check(proactive: false), PaywallRefusal.none,
        reason: 'она сама пришла — это не проактивный оффер');
  });

  /// Поверхность у события — половина его имени: без неё сервер не пишет
  /// событие вовсе (`alma/funnel.py`, `SurfaceMissing`). Считается она
  /// намерением, и вот таблица.
  test('каждое намерение знает свою поверхность §3', () {
    expect(const PaywallIntent.door(SystemSlug.natal).surfaceCode, 'p2');
    expect(const PaywallIntent.subscription().surfaceCode, 'p5');
    expect(const PaywallIntent.questionQuota().surfaceCode, 'p6');
    expect(const PaywallIntent.pair().surfaceCode, 'p4');
    expect(const PaywallIntent.plans().surfaceCode, 'p7');
    expect(const PaywallIntent.cancelSave(SystemSlug.natal).surfaceCode, 'p8');
  });

  test('квота вопросов и живой слой продают одну и ту же полку', () {
    // Экрана два, товар один: разведи их полками — и «месячный план» получит
    // второе описание, которое однажды разойдётся с первым.
    expect(const PaywallIntent.questionQuota().surface,
        const PaywallIntent.subscription().surface);
    expect(const PaywallIntent.questionQuota().ladder, isFalse,
        reason: 'лестница живёт ровно на одном экране — V8');
  });

  test('правило 2: отклонённый проактивный SKU молчит 48 часов', () {
    // noteDeclined пишет и на диск; в пробирке диск — мок.
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    PaywallGuard.reset();
    final noon = DateTime(2026, 8, 18, 12);
    PaywallGuard.noteDeclined('pair.check', noon);
    // Проактивный показ того же товара — тишина, и почти до конца окна.
    expect(
      PaywallGuard.check(
          proactive: true, sku: 'pair.check', now: noon.add(const Duration(hours: 47))),
      PaywallRefusal.declinedRecently,
    );
    // Контекстный пейволл по тапу — без кулдауна: «она сама пришла».
    expect(
      PaywallGuard.check(
          proactive: false, sku: 'pair.check', now: noon.add(const Duration(hours: 1))),
      PaywallRefusal.none,
    );
    // Другой товар не задет: отказ адресный.
    expect(
      PaywallGuard.check(
          proactive: true, sku: 'bundle.static', now: noon.add(const Duration(hours: 1))),
      PaywallRefusal.none,
    );
    // Через 48 часов — снова можно.
    expect(
      PaywallGuard.check(
          proactive: true,
          sku: 'pair.check',
          now: noon.add(const Duration(hours: 48, minutes: 1))),
      PaywallRefusal.none,
    );
    PaywallGuard.reset();
  });
}
