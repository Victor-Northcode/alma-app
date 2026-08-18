/// Единственная дверь ко всем продающим экранам v3.
///
/// **Зачем одна точка.** До v3 пейволл открывался из пяти мест пятью
/// `Navigator.push(OfferScreen(...))`, и каждое место решало само, что показать
/// и стоит ли показывать вообще. Пока экран был один, это сходило с рук; в v3
/// экранов пять, правил показа — четыре (§5 ТЗ), а событий воронки — три на
/// каждый показ, и все три сервер отклоняет без поверхности. Пять копий этой
/// логики разойдутся не «когда-нибудь», а на первой же правке: тот, кто
/// добавит шестой вход, скопирует ближайший.
///
/// Поэтому здесь:
///
/// * **выбор экрана по намерению** — и ни один экран не знает про другой;
/// * **инварианты ненавязчивости** (`PaywallGuard`) — до всякой навигации;
/// * **воронка** — `paywall_shown` / `paywall_dismissed` / `checkout_started`
///   с поверхностью, посчитанной намерением, а не экраном.
///
/// Чего здесь **нет**: решения, что человеку продать. Это `ladderFor`, и она
/// живёт в `billing/`, потому что полка — вопрос каталога, а не навигации.
library;

import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';

import '../../billing/ladder.dart';
import '../../net/models.dart';
import '../../state/paywall_guard.dart';
import '../../state/session.dart';
import 'cancel_save_screen.dart';
import 'plans_screen.dart';
import 'quota_screen.dart';
import 'subscription_screen.dart';

/// Чем кончился показ.
enum PaywallOutcome {
  /// Куплено — сервер выдал право, экран закрылся сам.
  bought,

  /// Закрыт крестиком, «не сейчас» или жестом назад.
  dismissed,

  /// Не показан вовсе: сработал один из инвариантов §5.
  blocked,

  /// Только V9: «просто отменить». Не отказ от покупки, а продолжение того
  /// пути, ради которого экран и открылся.
  justCancel,
}

/// Экран пары строит другой агент, и до тех пор его сюда подставляют.
///
/// **Регистрацией, а не импортом.** P4 (ввод → тизер → пейволл → отчёт) —
/// отдельная работа Ф1, и маршрутизатор, импортирующий файл, которого ещё нет,
/// не собирается вовсе. Точка входа одна и тогда, когда половина экранов
/// написана: флоу пары поднимает [pair] у себя, и `PaywallIntent.pair()`
/// начинает работать, ничего здесь не меняя.
class PaywallScreens {
  const PaywallScreens._();

  /// Кто рисует P4. `null` — экран ещё не построен.
  static Widget Function(BuildContext context)? pair;
}

/// Показать продающий экран, если его вообще можно показать.
///
/// [trigger] — то, что человек только что сделал: `locked_chapter`,
/// `live_block`, `question`, `all_plans`, `cancel_flow`. Уходит в воронку
/// ярлыком, поэтому без пробелов (`alma/funnel.py`, `LABEL`).
///
/// [proactive] — оффер всплыл сам, а не по тапу. Таких §5 разрешает не больше
/// одного за сессию.
Future<PaywallOutcome> showPaywall(
  BuildContext context,
  PaywallIntent intent, {
  required String trigger,
  bool proactive = false,
  String? question,
  int? chapters,
  int? opens,
}) async {
  final refusal = PaywallGuard.check(proactive: proactive);
  if (refusal != PaywallRefusal.none) {
    // Молча для человека, вслух для того, кто отлаживает: отказ показать
    // пейволл — это работающее правило, а не сбой.
    debugPrint('пейволл ${intent.surfaceCode} не показан: ${refusal.name}');
    return PaywallOutcome.blocked;
  }
  final screen = _screenFor(intent,
      question: question, chapters: chapters, opens: opens);
  if (screen == null) return PaywallOutcome.blocked;
  final session = SessionScope.of(context);
  if (proactive) PaywallGuard.noteProactive();

  PaywallGuard.onScreen = true;
  try {
    final outcome = await Navigator.of(context, rootNavigator: true)
        .push<PaywallOutcome>(CupertinoPageRoute(
      builder: (_) => PaywallSurfaceScope(trigger: trigger, child: screen),
    ));
    // Жест «назад» возвращает `null`: для §5 это такой же законный отказ, как
    // крестик, и в отчёте он обязан отличаться от него методом.
    if (outcome == null) {
      session.client.track(FunnelStage.paywallDismissed,
          meta: {'surface': intent.surfaceCode, 'method': 'back'});
      return PaywallOutcome.dismissed;
    }
    return outcome;
  } finally {
    PaywallGuard.onScreen = false;
  }
}

/// Тихая ссылка «Все планы» — и единственное место, где пейволл встаёт поверх
/// пейволла законно.
///
/// **Почему это не нарушение §5.** Правило 3 запрещает пейволлу *появляться*
/// поверх другого: два зова подряд, ни об одном из которых не просили. Здесь
/// человек сам спросил «а что тут вообще есть» — с V2 или с V6, — и лестница
/// отвечает ровно на этот вопрос. Поэтому [PaywallGuard] здесь не спрашивают.
///
/// **Новым маршрутом, а не подменой содержимого.** Тот, кто посмотрел планы и
/// передумал, обязан вернуться к той самой двери, с которой ушёл, а не
/// оказаться на ней заново.
Future<PaywallOutcome> openAllPlans(BuildContext context) async {
  final outcome = await Navigator.of(context, rootNavigator: true)
      .push<PaywallOutcome>(CupertinoPageRoute(
    builder: (_) => const PaywallSurfaceScope(
      trigger: 'all_plans_link',
      child: PlansScreen(),
    ),
  ));
  return outcome ?? PaywallOutcome.dismissed;
}

/// Повод, по которому экран открыт, — вниз по дереву.
///
/// **Повод знает зовущий, а поверхность — намерение.** Поверхность экран
/// считает сам из своего [PaywallIntent] и ошибиться не может; а вот «по чему
/// именно человек тапнул» знает только место вызова, и передать это иначе, чем
/// сверху вниз, значило бы завести у каждого экрана по параметру, который
/// нужен одному лишь отчёту.
///
/// `null` — экран открыт мимо маршрутизатора (тест, прямой push). Тогда повод
/// `direct`, и это честнее выдуманного.
class PaywallSurfaceScope extends InheritedWidget {
  const PaywallSurfaceScope({
    super.key,
    required this.trigger,
    required super.child,
  });

  final String trigger;

  static PaywallSurfaceScope? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<PaywallSurfaceScope>();

  @override
  bool updateShouldNotify(PaywallSurfaceScope old) => old.trigger != trigger;
}

/// Какой экран отвечает этому намерению.
///
/// **Живая система двери не имеет** (ТЗ §3 P2): транзиты пересчитываются
/// каждый день, соляр переписывается к каждому дню рождения, и продать их
/// «навсегда» значит продать подписку, не взяв за неё денег. Тап по их
/// закрытой главе ведёт на V6 — и решается это здесь, а не в главе: правило
/// про живые системы уже стоит в `ladderFor`, и второе место, где оно
/// записано, однажды разойдётся с первым.
Widget? _screenFor(
  PaywallIntent intent, {
  String? question,
  int? chapters,
  int? opens,
}) {
  switch (intent.surface) {
    case PaywallSurface.door:
      // **Отдельного экрана двери больше нет** — спека запертой главы (§5)
      // удалила маршрут «пейволл главы»: закрытая глава продаёт сама, внутри
      // себя, написанным началом и кнопкой на размытии. Интент двери остался
      // жить кодом поверхности воронки; показывать по нему больше нечего.
      // Живые системы (без двери в каталоге) по-прежнему уводят к подписке.
      final system = intent.system;
      if (system == null) return null;
      if (LadderKey.doorFor(system) == null) return const SubscriptionScreen();
      return null;

    case PaywallSurface.subscription:
      return intent.questions
          ? QuotaScreen(question: question ?? '')
          : const SubscriptionScreen();

    case PaywallSurface.plans:
      return const PlansScreen();

    case PaywallSurface.cancelSave:
      final system = intent.system;
      if (system == null) return null;
      return CancelSaveScreen(system: system, chapters: chapters, opens: opens);

    case PaywallSurface.pair:
      // TODO(pair): P4 строит отдельный агент Ф1. Пока он не поднял
      // `PaywallScreens.pair`, тизер и его пейволл сюда не приходят — и это
      // лучше, чем показать вместо них чужой экран.
      final build = PaywallScreens.pair;
      return build == null ? null : Builder(builder: build);
  }
}
