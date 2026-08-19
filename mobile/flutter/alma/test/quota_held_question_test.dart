import 'dart:convert';

import 'package:alma/billing/alma_store.dart';
import 'package:alma/design/tab_bar.dart';
import 'package:alma/l10n/alma_l10n.dart';
import 'package:alma/net/alma_client.dart';
import 'package:alma/screens/alma/alma_screen.dart';
import 'package:alma/screens/paywall/paywall_router.dart';
import 'package:alma/screens/paywall/quota_screen.dart';
import 'package:alma/state/paywall_guard.dart';
import 'package:alma/state/session.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// **Купленная подписка обязана отправить тот самый вопрос.**
///
/// Экран квоты (V7) обещает это словами на самом кадре: вопрос удержан и
/// уйдёт, как только откроется доступ. Обещание держалось только на бумаге.
/// `_openQuota` звался из `catch` внутри `_send` — то есть до `finally`, где
/// снимается признак отправки. Вернувшийся с покупкой человек попадал в
/// повторный `_send`, тот первой же строкой видел «уже отправляю» и молча
/// выходил, а удержание и черновик к этой секунде были уже стёрты. Человек
/// платил ровно за этот ответ и оставался с пустым полем.
///
/// Покупка здесь — не StoreKit, а её единственное следствие, которое видит
/// беседа: маршрут пейволла закрывается с [PaywallOutcome.bought]. Ровно
/// этим значением его закрывает `PaywallShell`, когда сервер выдал право.

/// Сколько вопросов ушло на сервер. Ради него тест и написан: пропавшая
/// отправка отличается от состоявшейся **только** этим числом.
int asked = 0;

/// Первый вопрос упирается в дневную квоту, второй получает ответ.
///
/// Формы настоящие: отказ по квоте приходит в `detail.error`
/// (`question_limit.day`) с уже переведённой фразой, ответ — SSE с `done`, в
/// котором тот же JSON, что отдаёт `/v1/chat`.
AlmaClient quotaThenAnswer() {
  asked = 0;
  final http.Client transport = MockClient((request) async {
    final path = request.url.path;
    if (path == '/v1/chat/stream') {
      asked += 1;
      if (asked == 1) {
        return http.Response(
            jsonEncode({
              'detail': {
                'error': 'question_limit.day',
                'message': 'Questions come back tomorrow.',
              }
            }),
            429,
            headers: {'content-type': 'application/json'});
      }
      final done = jsonEncode({
        'thread_id': 'th1',
        'message': {
          'body': 'Saturn is crossing your fourth house.',
          'turn_kind': 'reading',
          'cited_factors': <String>[],
        },
        'questions_left': 29,
      });
      return http.Response(
          'event: done\n'
          'data: $done\n'
          '\n',
          200,
          headers: {'content-type': 'text/event-stream; charset=utf-8'});
    }
    Map<String, dynamic> body;
    if (path == '/v1/auth/refresh') {
      body = {'token': 't1', 'user_id': 'u1', 'is_guest': true, 'locale': 'en'};
    } else {
      body = {};
    }
    return http.Response(jsonEncode(body), 200,
        headers: {'content-type': 'application/json'});
  });
  return AlmaClient(baseUrl: Uri.parse('http://test.local'), http: transport);
}

/// Беседа под тем же небом, что в приложении.
///
/// **`SessionScope` — над `MaterialApp`, а не под ним.** Пейволл встаёт
/// маршрутом **корневого** навигатора, то есть вне поддерева вкладки; сессия,
/// положенная в `home`, до него не достаёт, и экран квоты не строится вовсе.
/// В приложении она и стоит над всем — см. `AlmaApp.build`.
Widget _cabinet(AlmaSession session) => SessionScope(
      session: session,
      child: MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        // Материал — то, на чём в оболочке стоит вкладка: без него `TextField`
        // композера не строится вовсе.
        home: Material(child: AlmaScreen(tabs: TabsPeek())),
      ),
    );

/// Кадры отсчитываются руками: свет Alma дышит вечно, и `pumpAndSettle` здесь
/// ждал бы всегда.
Future<void> _frames(WidgetTester tester, {int count = 14}) async {
  for (var i = 0; i < count; i++) {
    await tester.pump(const Duration(milliseconds: 80));
  }
}

/// Помехи чужих плагинов — не предмет этого теста. `in_app_purchase` в
/// тестовой среде каналов не находит и роняет `PlatformException` асинхронно,
/// картинки бандла не читаются вовсе; всё остальное обязано долететь.
void _dropStoreNoise(WidgetTester tester) {
  final noise = tester.takeException();
  if (noise != null &&
      !noise.toString().contains('channel-error') &&
      !noise.toString().contains('Unable to load asset')) {
    throw noise;
  }
}

/// Закрыть пейволл так, как его закрывает сам продукт.
void _closePaywall(WidgetTester tester, [PaywallOutcome? outcome]) =>
    Navigator.of(tester.element(find.byType(QuotaScreen)), rootNavigator: true)
        .pop(outcome);

const _question = 'Why does home feel like work?';

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    // Синглтон магазина заводится под iOS: по умолчанию в тестах платформа
    // Android, и `InAppPurchase.instance` поднимает Play Billing, который
    // каналов не находит и роняет `PlatformException` мимо тела теста.
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    AlmaStore.shared;
    debugDefaultTargetPlatformOverride = null;
  });

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
    // Десять минут тишины после покупки — общая память процесса, и покупка
    // соседнего теста запретила бы этому показать пейволл вовсе.
    PaywallGuard.reset();
  });

  testWidgets('квота → покупка → тот же вопрос уходит сам', (tester) async {
    tester.view.physicalSize = const Size(402, 874) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_cabinet(AlmaSession(quotaThenAnswer())));
    await tester.pump();

    await tester.enterText(find.byType(TextField), _question);
    await tester.testTextInput.receiveAction(TextInputAction.send);
    await _frames(tester);

    // Вопрос упёрся в квоту, и экран квоты пришёл **сам** — по отправке, а не
    // по интересу к цене (ТЗ P6).
    expect(asked, 1, reason: 'вопрос до сервера не дошёл');
    expect(find.byType(QuotaScreen), findsOneWidget,
        reason: 'экран квоты не открылся на исчерпанной квоте');
    // И держит в руках то, ради чего человек его открыл.
    expect(find.text(_question), findsWidgets,
        reason: 'удержанный вопрос не показан над ценой');
    _dropStoreNoise(tester);

    _closePaywall(tester, PaywallOutcome.bought);
    await _frames(tester);

    // **Вот проверка.** Вопрос ушёл во второй раз — сам, без повторного набора.
    expect(asked, 2,
        reason: 'удержанный вопрос после покупки не отправился: '
            'человек заплатил ровно за этот ответ');
    expect(find.textContaining('fourth house'), findsOneWidget,
        reason: 'ответ на оплаченный вопрос не пришёл на экран');

    // И поле осталось чистым: вопрос принят, а не возвращён на второй набор.
    expect(tester.widget<TextField>(find.byType(TextField)).controller?.text,
        isEmpty);
    _dropStoreNoise(tester);
  });

  testWidgets('закрытый без покупки экран квоты удержания не снимает',
      (tester) async {
    tester.view.physicalSize = const Size(402, 874) * 3;
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_cabinet(AlmaSession(quotaThenAnswer())));
    await tester.pump();

    await tester.enterText(find.byType(TextField), _question);
    await tester.testTextInput.receiveAction(TextInputAction.send);
    await _frames(tester);
    expect(find.byType(QuotaScreen), findsOneWidget);
    _dropStoreNoise(tester);

    // Ушёл, ничего не купив: `null` — это жест «назад», такой же законный
    // отказ, как крестик.
    _closePaywall(tester);
    await _frames(tester);
    expect(asked, 1, reason: 'отказ от покупки не должен ничего отправлять');

    // Метка обещала «уйдёт, когда ты продолжишь», и продолжить можно завтра:
    // стена возвращает на тот же экран с тем же вопросом, а не на пустой.
    await tester.tap(find.text('See the plans'));
    await _frames(tester);
    expect(find.byType(QuotaScreen), findsOneWidget);
    expect(find.text(_question), findsWidgets,
        reason: 'удержание снялось отказом — вопрос набирали бы заново');
    _dropStoreNoise(tester);
  });
}
