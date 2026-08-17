import 'package:flutter/material.dart';

import '../../billing/alma_store.dart';
import '../../billing/ladder.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import 'paywall_router.dart';

/// Всё, что у пяти продающих экранов одинаково **под** разметкой.
///
/// Магазин, полка, лестница, воронка и уход с экрана — это пять раз одно и то
/// же, и разведённое по экранам оно разойдётся: один забудет `checkout_started`,
/// другой перечитает права, третий закроется до того, как сервер ответил.
/// Экран, взявший эту оболочку, получает [PaywallDeal] и рисует; решать, чем
/// кончился показ, ему не нужно.
///
/// **Экран закрывается сам, когда право выдано.** Не по ответу магазина —
/// `AlmaStore` открывает лист, но право пишет сервер, — а по извещению
/// `unlocked`/`restored`, то есть по перечитанным правам. Пейволл, оставшийся
/// на экране после успешной покупки, читается как «не прошло», и человек
/// нажимает второй раз.
class PaywallShell extends StatefulWidget {
  const PaywallShell({
    super.key,
    required this.intent,
    required this.seed,
    required this.builder,
    this.mood = SkyMood.cabinet,
  });

  /// Зачем открыли. Из него же считается поверхность для воронки.
  final PaywallIntent intent;

  /// Своё небо у каждого экрана: переход между двумя пейволлами обязан быть
  /// видимым переходом, а не теми же звёздами дважды.
  final int seed;

  final SkyMood mood;
  final Widget Function(BuildContext context, PaywallDeal deal) builder;

  @override
  State<PaywallShell> createState() => _PaywallShellState();
}

class _PaywallShellState extends State<PaywallShell> {
  final AlmaStore _store = AlmaStore.shared;

  List<Plan> _shelf = const [];
  bool _loading = true;
  bool _started = false;

  /// Извещение магазина, с которым экран открылся.
  ///
  /// **Сравнивается по личности объекта, а не по значению.** `AlmaStore` живёт
  /// один на процесс, и извещение о позавчерашней покупке всё ещё в нём: экран,
  /// смотрящий на `message == unlocked`, закрылся бы в первый же кадр, ничего
  /// не продав. Каждое новое извещение — новый объект, и «новое» здесь значит
  /// ровно это.
  StoreNotice? _seen;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    _seen = _store.notice;
    _store.addListener(_storeChanged);
    _store.attach(SessionScope.of(context));
    // Что угодно, кроме загруженной полки, стоит попробовать ещё раз: экран,
    // открытый заново после мёртвой сети, обязан работать.
    if (_store.state != StoreState.ready) _store.load();
    _load();
  }

  @override
  void dispose() {
    _store.removeListener(_storeChanged);
    super.dispose();
  }

  void _storeChanged() {
    if (!mounted) return;
    final notice = _store.notice;
    if (!identical(notice, _seen)) {
      _seen = notice;
      final unlocked = notice != null &&
          (notice.message == StoreMessage.unlocked ||
              notice.message == StoreMessage.restored);
      if (unlocked) {
        Navigator.of(context).pop(PaywallOutcome.bought);
        return;
      }
    }
    setState(() {});
  }

  Future<void> _load() async {
    final session = SessionScope.of(context);
    try {
      final shelf = await session.client.catalogue(locale: session.locale);
      if (mounted) {
        setState(() {
          _shelf = shelf.plans;
          _loading = false;
        });
      }
    } on AlmaError {
      // Полка не приехала — цены всё равно спрашивают у магазина, а что мы
      // продаём, известно и без неё. Экран рисуется, кнопка гаснет.
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Ступень воронки «пейволл показан». Один раз за показ и только после
  /// того, как известно, чем торгуем: `sku` без полки был бы пустым.
  bool _announced = false;

  void _announce(List<LadderKey> rungs) {
    if (_announced || _loading) return;
    _announced = true;
    final trigger = PaywallSurfaceScope.maybeOf(context)?.trigger ?? 'direct';
    SessionScope.of(context).client.track(FunnelStage.paywallShown, meta: {
      'surface': widget.intent.surfaceCode,
      if (rungs.isNotEmpty) 'sku': rungs.first.slug,
      'trigger': trigger,
    });
  }

  void _buy(LadderKey key) {
    SessionScope.of(context).client.track(FunnelStage.checkoutStarted,
        meta: {'surface': widget.intent.surfaceCode, 'sku': key.slug});
    _store.buy(key);
  }

  void _close(String method, PaywallOutcome outcome) {
    SessionScope.of(context).client.track(FunnelStage.paywallDismissed,
        meta: {'surface': widget.intent.surfaceCode, 'method': method});
    Navigator.of(context).pop(outcome);
  }

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    final rungs = ladderFor(
      intent: widget.intent,
      held: session.entitlements,
      shelf: _shelf,
    );
    _announce(rungs);
    return Scaffold(
      // **Свой `Scaffold`.** `NightSky` — это небо и колонка, а не
      // material-поверхность; на вкладках его держит `Scaffold` кабинета, а
      // открытый отдельным маршрутом экран этой опоры не имеет, и Flutter
      // рисует каждую строку жёлтой с подчёркиванием.
      backgroundColor: AlmaPalette.night,
      body: NightSky(
        mood: widget.mood,
        seed: widget.seed,
        child: SafeArea(
          child: widget.builder(
            context,
            PaywallDeal._(
              store: _store,
              rungs: rungs,
              loading: _loading,
              onBuy: _buy,
              onClose: _close,
            ),
          ),
        ),
      ),
    );
  }
}

/// То, что оболочка знает о сделке, — экрану, который её рисует.
class PaywallDeal {
  const PaywallDeal._({
    required this.store,
    required this.rungs,
    required this.loading,
    required this.onBuy,
    required this.onClose,
  });

  final AlmaStore store;

  /// Что сегодня на полке для этого намерения, в порядке [ladderFor].
  final List<LadderKey> rungs;

  /// Полка ещё едет. Цена может не приехать и потом — это уже не загрузка.
  final bool loading;

  /// Оболочка сама открывает лист и сама считает ступени воронки — экран
  /// зовёт [buy] и [close], а не эти поля.
  final void Function(LadderKey) onBuy;
  final void Function(String, PaywallOutcome) onClose;

  LadderKey? get first => rungs.isEmpty ? null : rungs.first;

  /// Цена **как её напечатал магазин**. `null` — магазин молчит, и число
  /// выдумывать нельзя ни при каких обстоятельствах.
  String? price(LadderKey key) => store.price(key);

  bool get busy => store.busy != null;

  /// Открыть лист покупки. Ступень воронки уходит отсюда, а не с кнопки.
  void buy(LadderKey key) => onBuy(key);

  /// Уйти. [method] — `close`, `not_now`, `just_cancel`; жест «назад» считает
  /// маршрутизатор.
  ///
  /// [outcome] отличает «отказалась» от «пошла отменять дальше» (V9): для
  /// отчёта это один и тот же `paywall_dismissed`, для вызывающего — два
  /// разных продолжения, и решать по одному значению их нельзя.
  void close(String method,
          {PaywallOutcome outcome = PaywallOutcome.dismissed}) =>
      onClose(method, outcome);
}
