import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';

import '../billing/alma_store.dart';
import '../billing/ladder.dart';
import '../design/buttons.dart';
import '../design/metrics.dart';
import '../design/palette.dart';
import '../design/screen_scaffold.dart';
import '../design/typography.dart';
import '../l10n/alma_l10n.dart';
import '../net/alma_client.dart';
import '../net/models.dart';
import '../state/session.dart';
import 'legal/legal_screen.dart';
import 'legal/legal_text.dart';

/// Витрина: что можно открыть, почём, и одна кнопка.
///
/// Порт `mobile/ios/Alma/Billing/PaywallView.swift` — лестница, а не список
/// цен. Отличие не косметическое: список ничего не продаёт, потому что не
/// говорит, что внутри и что будет после нажатия. Здесь стоит всё, что на
/// нативе:
///
/// * три проверяемых факта о покупке — не прилагательные;
/// * ступени с подписью под каждой и точкой выбора, без карточек и рамок;
/// * раскрытие автопродления **прямо над кнопкой** — этого требует и App
///   Review, и здравый смысл: о повторном списании узнают до нажатия;
/// * три честные строки о том, кто продавец и где отменяют;
/// * восстановление покупок — без него магазин отклоняет приложение, и это
///   единственное, что помогает человеку с новым телефоном;
/// * «не сейчас», которое слышно.
///
/// **Каждая цена приходит из магазина.** Наш каталог решает, какие ступени
/// существуют и что каждая открывает; сколько это стоит — решает App Store.
/// Серверная цена в долларах, показанная тому, кто платит в иенах, была бы
/// числом, которого с него не возьмут.
///
/// **Ничего здесь ничего не открывает.** Золотая кнопка открывает лист Apple,
/// подписанная покупка уходит на сервер, сервер проверяет подпись и пишет
/// право, экран перечитывает права. Пути, который открыл бы главу решением
/// клиента, в этом файле нет.
class OfferScreen extends StatefulWidget {
  const OfferScreen({super.key, this.system});

  /// За какой дверью пришли. `null` — «Вся Alma», витрина целиком.
  final SystemSlug? system;

  @override
  State<OfferScreen> createState() => _OfferScreenState();
}

class _OfferScreenState extends State<OfferScreen> {
  final AlmaStore _store = AlmaStore.shared;

  List<Plan> _shelf = const [];
  bool _loading = true;
  bool _started = false;

  /// Какая ступень выбрана. `null` значит «первая» — и никогда не самая
  /// дорогая: витрина, открывающаяся преднажатой на годовом за $78.99 у того,
  /// кто ткнул в одну закрытую главу, учит людей закрывать витрины.
  LadderKey? _chosen;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    _store.addListener(_storeChanged);
    _store.attach(SessionScope.of(context));
    // Что угодно, кроме загруженной полки, стоит попробовать ещё раз: витрина,
    // открытая заново после мёртвой сети, обязана работать.
    if (_store.state != StoreState.ready) _store.load();
    _load();
    // Ступень воронки: витрину открыли. С системой в мете, когда пришли за
    // дверью, — иначе отчёт не отличит «показали лестницу» от «показали
    // конкретную дверь».
    SessionScope.of(context).client.track(
      FunnelStage.offerView,
      meta: widget.system == null ? null : {'product': widget.system!.slug},
    );
  }

  @override
  void dispose() {
    _store.removeListener(_storeChanged);
    super.dispose();
  }

  void _storeChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _load() async {
    final session = SessionScope.of(context);
    try {
      final shelf = await session.client.catalogue(locale: session.locale);
      if (mounted) {
        setState(() {
          _shelf = shelf;
          _loading = false;
        });
      }
    } on AlmaError {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Дверь, к которой потянулись, — если она ещё не открыта.
  ///
  /// Тому, у кого натальная карта уже куплена и кто пришёл сюда из натальной
  /// главы, натальную карту не продают второй раз: [ladderFor] эту ступень всё
  /// равно уберёт, и остался бы экран, озаглавленный системой, которую он не
  /// продаёт.
  PaywallIntent _intentFor(Entitlements held) {
    final system = widget.system;
    if (system == null || held.opened(system)) {
      return const PaywallIntent.everything();
    }
    return PaywallIntent.door(system);
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final session = SessionScope.of(context);
    final intent = _intentFor(session.entitlements);
    final rungs = ladderFor(
      intent: intent,
      held: session.entitlements,
      shelf: _shelf,
    );
    final door = intent.system;
    final chosen = rungs.contains(_chosen) ? _chosen! : rungs.firstOrNull;

    return Scaffold(
      backgroundColor: AlmaPalette.night,
      // **Свой `Scaffold`.**
      //
      // `ScreenScaffold` — это небо и колонка, а не material-поверхность: на
      // вкладках его держит `Scaffold` кабинета. Открытый отдельным маршрутом
      // экран этой опоры не имеет, и Flutter рисует каждую строку жёлтой с
      // подчёркиванием — ровно то, что было на кадре у владельца.
      body: ScreenScaffold(
        seed: 0x0FFE2026,
        eyebrow: l.paywallLabel,
        title: door == null
            ? l.paywallEverythingTitle
            : LadderKey.systemTitle(l, door),
        children: [
          Text(door == null ? l.paywallEverythingSub : l.paywallDoorSub,
              style: AlmaType.body),
          const SizedBox(height: 18),
          // Что покупают — до всякой цены и до всякой ошибки. Владелец однажды
          // ткнул в закрытую главу на симуляторе без магазина и попал на
          // страницу, всё содержимое которой было «App Store не отвечает».
          _Facts(door: door != null),
          const SizedBox(height: 10),
          if (_loading)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 40),
              child:
                  Center(child: Text(l.stateLoadingShort, style: AlmaType.meta)),
            )
          else if (rungs.isEmpty)
            // Продавать нечего. Сказано прямо, и с единственным управлением,
            // которое ещё полезно, — а не пустым экраном и уж точно не
            // строкой, предлагающей купить уже купленное.
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(l.paywallOwnedAll, style: AlmaType.voice),
                  const SizedBox(height: 14),
                  Text(l.paywallManageNote, style: AlmaType.meta),
                  const SizedBox(height: 18),
                  // Состояние «у тебя есть всё» было единственным, где нельзя
                  // было попросить это обратно, — и это же состояние песочницы
                  // рецензента, уже всё купившего.
                  _RestoreButton(store: _store),
                ],
              ),
            )
          else ...[
            for (final (i, key) in rungs.indexed)
              _Rung(
                rung: key,
                price: _store.price(key),
                selected: key == chosen,
                showsRule: i != rungs.length - 1,
                onTap: _store.busy != null
                    ? null
                    : () => setState(() => _chosen = key),
              ),
            if (chosen != null)
              _BuyArea(
                chosen: chosen,
                store: _store,
                intent: intent,
                onDecline: () {
                  session.client.track(
                    FunnelStage.offerDeclined,
                    meta: door == null ? null : {'product': door.slug},
                  );
                  Navigator.of(context).maybePop();
                },
              ),
          ],
        ],
      ),
    );
  }
}

/// Три факта о покупке, на языке покупателя. Факты, не прилагательные: каждая
/// строка проверяема по продукту.
class _Facts extends StatelessWidget {
  const _Facts({required this.door});

  final bool door;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final lines = door
        ? [l.paywallPitchDoor1, l.paywallPitchDoor2, l.paywallPitchDoor3]
        : [l.paywallPitchPlan1, l.paywallPitchPlan2, l.paywallPitchPlan3];
    return _Dotted(lines: lines, style: AlmaType.body);
  }
}

/// Строки, начинающиеся с точки. Тот же приём, что на нативе, и он один на
/// оба места — обещания и факты.
class _Dotted extends StatelessWidget {
  const _Dotted({required this.lines, required this.style});

  final List<String> lines;
  final TextStyle style;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final line in lines)
            Padding(
              padding: const EdgeInsets.only(bottom: 7),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('·', style: AlmaType.numeral),
                  const SizedBox(width: 8),
                  Expanded(child: Text(line, style: style)),
                ],
              ),
            ),
        ],
      );
}

/// Ступень: что это слева, сколько магазин возьмёт справа.
///
/// Ни карточки, ни рамки, ни панели. Содержимое стоит на ночи, ступени
/// разделены волосяной линией, выбор — залитая золотая точка: залитая панель
/// была бы вторым акцентом, которого у этого продукта нет.
class _Rung extends StatelessWidget {
  const _Rung({
    required this.rung,
    required this.price,
    required this.selected,
    required this.showsRule,
    required this.onTap,
  });

  final LadderKey rung;

  /// `null` — магазин не ответил. Колонка остаётся пустой: единственное, что
  /// нельзя выдумывать, это число.
  final String? price;
  final bool selected;
  final bool showsRule;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Opacity(
        opacity: onTap == null ? 0.75 : 1,
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 15),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: AnimatedContainer(
                    duration: AlmaMotion.ui,
                    curve: AlmaMotion.uiCurve,
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: selected ? AlmaPalette.gold : Colors.transparent,
                      border: Border.all(
                        color: AlmaPalette.gold
                            .withValues(alpha: selected ? 0 : 0.45),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(rung.title(l), style: AlmaType.headingM),
                      const SizedBox(height: 4),
                      Text(rung.note(l), style: AlmaType.meta),
                    ],
                  ),
                ),
                if (price != null) ...[
                  const SizedBox(width: 12),
                  Opacity(
                    opacity: selected ? 1 : 0.7,
                    child: Text(price!, style: AlmaType.numeral),
                  ),
                ],
              ],
            ),
          ),
          if (showsRule) const AlmaHairline(),
        ]),
      ),
    );
  }
}

/// Раскрытие, кнопка, честность и путь назад.
class _BuyArea extends StatelessWidget {
  const _BuyArea({
    required this.chosen,
    required this.store,
    required this.intent,
    required this.onDecline,
  });

  final LadderKey chosen;
  final AlmaStore store;
  final PaywallIntent intent;

  /// «Не сейчас». Отдельная ступень воронки, а не просто выход: человек,
  /// закрывший витрину, и человек, ушедший с неё назад, — разные события.
  final VoidCallback onDecline;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final price = store.price(chosen);
    final busy = store.busy != null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Раскрытие стоит вплотную над кнопкой и меняется вместе с выбором.
        // Соседство — требование, а не вкус: App Review просит фразу об
        // автопродлении рядом с действием оплаты, а человек, открывший это
        // нажатием на одну закрытую главу, не должен узнать о годовом
        // списании из выписки.
        if (chosen.isSubscription)
          Padding(
            padding: const EdgeInsets.only(top: 18),
            child: Text(l.paywallAutoRenewTerms, style: AlmaType.meta),
          ),
        if (price == null) ...[
          // Магазин молчит. Полка выше осталась на месте — что на ней лежит,
          // известно и без App Store, — а купить нельзя, и это сказано.
          const SizedBox(height: 18),
          Text(l.paywallStoreUnavailable, style: AlmaType.body),
          const SizedBox(height: 16),
          Center(
            child: AlmaButton(
              kind: AlmaButtonKind.outline,
              fills: false,
              label: l.stateRetry,
              onTap: store.load,
            ),
          ),
        ] else
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: AlmaButton(
              // Одна строка, ужимающаяся, если надо: иерархия кнопок держится
              // высотой, и «Всё живое — на неделю · $4.99» в две строки стало
              // бы другим управлением.
              label: busy
                  ? l.stateLoadingShort
                  : '${chosen.title(l)} · $price',
              onTap: busy || store.restoring ? null : () => store.buy(chosen),
            ),
          ),
        if (store.notice != null)
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(
              _noticeText(l, store.notice!.message),
              style: AlmaType.meta.copyWith(
                color: switch (store.notice!.tone) {
                  StoreTone.good => AlmaPalette.agree,
                  StoreTone.waiting => AlmaPalette.gold,
                  StoreTone.bad => AlmaPalette.disagree,
                },
              ),
            ),
          ),
        Padding(
          padding: const EdgeInsets.only(top: 22),
          // Три обещания, поправленные на магазин: у веб-приложения продавец
          // мы, здесь — Apple. Она берёт деньги, она присылает чек, у неё же
          // отменяют.
          child: _Dotted(
            lines: [
              l.paywallHonestyOnce,
              l.paywallHonestySeller,
              l.paywallHonestyCancel,
            ],
            style: AlmaType.meta,
          ),
        ),
        const SizedBox(height: 6),
        Text(l.paywallFreeNote, style: AlmaType.meta),
        const SizedBox(height: 14),
        // **Условия, политика и условия подписки — с самой витрины.**
        //
        // Guideline 3.1.2 просит рабочие ссылки на первые две с того экрана,
        // где продаётся подписка, и рецензент открывает каждую. Документы —
        // экраны, а не веб-ссылки: ссылка наружу может лежать в тот день,
        // когда идёт ревью, и в порте она вела на несуществующий домен.
        Center(
          child: Wrap(
            alignment: WrapAlignment.center,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              _LegalLink(l.paywallTerms, LegalDocument.terms),
              Text('  ·  ', style: AlmaType.meta),
              _LegalLink(l.paywallPrivacy, LegalDocument.privacy),
              Text('  ·  ', style: AlmaType.meta),
              _LegalLink(
                  l.paywallSubscriptionTerms, LegalDocument.subscriptionTerms),
            ],
          ),
        ),
        const SizedBox(height: 18),
        // Apple отклоняет приложение, которое продаёт разовые покупки и не
        // умеет их вернуть. И это же единственное, что помогает человеку с
        // новым телефоном, — случай, который действительно случается.
        Center(child: _RestoreButton(store: store)),
        const SizedBox(height: 14),
        Center(
          child: AlmaButton(
            kind: AlmaButtonKind.outline,
            fills: false,
            label: intent.isDoor ? l.paywallSkip : l.paywallNotNow,
            onTap: onDecline,
          ),
        ),
        const SizedBox(height: 8),
      ],
    );
  }

  static String _noticeText(L l, StoreMessage message) => switch (message) {
        StoreMessage.storeSilent => l.paywallStoreUnavailable,
        StoreMessage.pending => l.paywallPending,
        StoreMessage.offline => l.paywallOffline,
        StoreMessage.notVerified => l.paywallNotVerified,
        StoreMessage.verifyLater => l.paywallVerifyLater,
        StoreMessage.withdrawn => l.paywallWithdrawn,
        StoreMessage.unlocked => l.paywallRestored,
        StoreMessage.restoring => l.paywallRestoring,
        StoreMessage.restored => l.paywallRestored,
        StoreMessage.restoredNone => l.paywallRestoredNone,
      };
}

/// Ссылка на документ: золотая, подчёркнутая, открывает экран.
class _LegalLink extends StatelessWidget {
  const _LegalLink(this.label, this.document);

  final String label;
  final LegalDocument document;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: () => Navigator.of(context, rootNavigator: true).push(
          CupertinoPageRoute(
              builder: (context) => LegalScreen(document: document)),
        ),
        child: Text(
          label,
          style: AlmaType.meta.copyWith(
            color: AlmaPalette.gold,
            decoration: TextDecoration.underline,
            decorationColor: AlmaPalette.gold.withValues(alpha: 0.6),
          ),
        ),
      );
}

class _RestoreButton extends StatelessWidget {
  const _RestoreButton({required this.store});

  final AlmaStore store;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return AlmaButton(
      kind: AlmaButtonKind.veil,
      fills: false,
      label: store.restoring ? l.paywallRestoring : l.paywallRestore,
      onTap: store.restoring || store.busy != null ? null : store.restore,
    );
  }
}

extension _FirstOrNull<T> on List<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
