import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';

import '../../billing/alma_store.dart';
import '../../billing/ladder.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../billing/store_words.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/reading_tally.dart';
import '../../state/session.dart';
import '../paywall/paywall_router.dart' show openAllPlans;
import 'chapter_screen.dart';
import 'pair_add_screen.dart';

/// «Что дальше» — V3, поверхность P3: единственное место апсейла после
/// покупки.
///
/// Разметка `SCREENS-V3.md` §V3. Открывается по тапу на приглашение в конце
/// последней главы купленной системы — не автопереходом: человек только что
/// дочитал то, за что заплатил, и экран, вставший сам, читался бы перебивкой.
///
/// Три карточки убывают по силе, как на холсте: следующая непрочитанная
/// система (бесплатная глава, не цена!), совместимость с ценой `pair.check`,
/// набор с ценой `bundle.static`. Золотой кнопки на экране нет ни одной —
/// человек только что заплатил, и золото сразу после покупки читается как
/// «мало дал».
class WhatNextScreen extends StatefulWidget {
  const WhatNextScreen({super.key, required this.finished});

  /// Система, чей разбор только что дочитан, — её не предлагаем читать снова.
  final SystemSlug finished;

  @override
  State<WhatNextScreen> createState() => _WhatNextScreenState();
}

class _WhatNextScreenState extends State<WhatNextScreen> {
  final AlmaStore _store = AlmaStore.shared;

  bool _started = false;
  bool _announced = false;

  /// Следующая непрочитанная система — или `null`, пока считается либо если
  /// читано всё. Карточка без кандидата не рисуется вовсе: предлагать «начни
  /// вот это» тому, кто это уже открывал, значит доказать, что экран его не
  /// знает.
  SystemSlug? _nextUnread;

  /// Оглавление следующей системы уже спрашивается — второй тап не second
  /// запрос, а ожидание первого.
  bool _openingBusy = false;

  /// Кандидаты первой карточки: статичная пятёрка в порядке колоды «Моих
  /// систем». Живые системы и пара сюда не входят — их «открытие» не глава I,
  /// а подписка и чужая дата рождения.
  static const _order = <SystemSlug>[
    SystemSlug.natal,
    SystemSlug.birthCard,
    SystemSlug.astrocartography,
    SystemSlug.numerology,
    SystemSlug.synthesis,
  ];

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    _store.addListener(_storeChanged);
    _store.attach(SessionScope.of(context));
    if (_store.state != StoreState.ready) _store.load();
    _findNextUnread();
  }

  @override
  void dispose() {
    _store.removeListener(_storeChanged);
    super.dispose();
  }

  void _storeChanged() {
    if (mounted) setState(() {});
  }

  /// Первая по колоде система, которую не открывали ни разу.
  ///
  /// Счёт — [ReadingTally], тот же, каким выбирает систему спасение от отмены:
  /// клиентское приближение, пока чтение не считается на сервере.
  Future<void> _findNextUnread() async {
    for (final system in _order) {
      if (system == widget.finished) continue;
      if (await ReadingTally.opens(system) == 0) {
        if (mounted) setState(() => _nextUnread = system);
        return;
      }
    }
  }

  /// «Экран показан» — один раз за показ.
  ///
  /// Поверхность — `p3` словом §3 ТЗ напрямую: в [PaywallIntent] её нет,
  /// потому что V3 — не пейволл (он не просит денег кнопкой, цены на нём
  /// стоят текстом), а сервер это слово знает (`alma/funnel.py`, `SURFACES`).
  void _announce() {
    if (_announced) return;
    _announced = true;
    SessionScope.of(context).client.track(FunnelStage.paywallShown, meta: {
      'surface': 'p3',
      'trigger': 'what_next',
    });
  }

  /// Первая карточка ведёт в бесплатную главу — не к цене (ТЗ §3 P3).
  ///
  /// Слаг открывающей главы знает только оглавление, и оно спрашивается по
  /// тапу: держать восемь оглавлений заранее ради одной карточки — это сеть,
  /// потраченная до вопроса.
  Future<void> _readOpening(SystemSlug system) async {
    if (_openingBusy) return;
    setState(() => _openingBusy = true);
    try {
      final session = SessionScope.of(context);
      final list =
          session.client.knownChapters(system, locale: session.locale) ??
              await session.client.chapters(system, locale: session.locale);
      if (!mounted) return;
      ChapterEntry? opening;
      for (final entry in list.chapters) {
        if (entry.free) {
          opening = entry;
          break;
        }
      }
      if (opening == null) return;
      final slug = opening.slug;
      await Navigator.of(context, rootNavigator: true).push(
        CupertinoPageRoute(
          builder: (context) => ChapterScreen(system: system, chapter: slug),
        ),
      );
    } on AlmaError {
      // Сеть промолчала — карточка остаётся, и тап можно повторить. Пугать
      // отдельным экраном отказ одного GET не заслуживает.
    } finally {
      if (mounted) setState(() => _openingBusy = false);
    }
  }

  void _checkSomeone() {
    Navigator.of(context, rootNavigator: true).push(
      CupertinoPageRoute(builder: (context) => const PairAddScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    _announce();
    final session = SessionScope.of(context);
    final next = _nextUnread;
    final bundlePrice = _store.price(LadderKey.bundleStatic);
    return Scaffold(
      body: Container(
        decoration:
            const BoxDecoration(gradient: AlmaGradient.parchment),
        child: SafeArea(
          bottom: false,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(
                AlmaMetrics.pad, 10, AlmaMetrics.pad, 60),
            children: [
              Row(children: [
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: Icon(Icons.arrow_back, color: AlmaPalette.inkMuted),
                  padding: EdgeInsets.zero,
                ),
              ]),
              const SizedBox(height: 20),
              Text(
                l.paywallV3WhatNextOverline.toUpperCase(),
                style:
                    AlmaType.overline.copyWith(color: AlmaPalette.goldDeep),
              ),
              // Карточка 1 · следующая непрочитанная система: имя и её
              // бесплатное открытие. Единственная карточка с кнопкой, и
              // действие на ней бесплатное — «одна цена на экране» в честном
              // виде.
              if (next != null) ...[
                const SizedBox(height: 12),
                _Card(
                  bordered: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        LadderKey.systemTitle(l, next),
                        style: AlmaType.displayL.copyWith(
                            fontSize: 18,
                            height: 1.2,
                            color: AlmaPalette.ink),
                      ),
                      const SizedBox(height: 10),
                      _OutlineCta(
                        label: l.paywallV3WhatNextReadOpening,
                        onTap: _openingBusy
                            ? null
                            : () => _readOpening(next),
                      ),
                    ],
                  ),
                ),
              ],
              // Карточка 2 · совместимость: цена `pair.check` стоит на
              // контурной кнопке, тап ведёт к вводу человека — сначала кто,
              // потом деньги.
              const SizedBox(height: 14),
              _Card(
                bordered: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l.paywallV3WhatNextPairTitle,
                      style: AlmaType.displayL.copyWith(
                          fontSize: 18, height: 1.2, color: AlmaPalette.ink),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      l.paywallV3WhatNextPairNote,
                      style: AlmaType.meta.copyWith(
                          height: 1.5, color: AlmaPalette.inkMuted),
                    ),
                    const SizedBox(height: 10),
                    if (_store.price(LadderKey.pairCheck) case final price?)
                      _OutlineCta(
                        label: l.paywallV3WhatNextPairCta(price),
                        onTap: _checkSomeone,
                      )
                    else
                      // Цену выдумать нельзя; молчащий магазин говорит о себе
                      // теми же словами, что на всех витринах.
                      Text(
                        l.storeUnavailable,
                        style: AlmaType.meta
                            .copyWith(color: AlmaPalette.inkMuted),
                      ),
                  ],
                ),
              ),
              // Карточка 3 · набор — намеренно тише первых двух: без канта,
              // цена текстом, стрелка вместо кнопки. У владельца набора её
              // нет вовсе.
              if (!session.entitlements.ownsArchive) ...[
                const SizedBox(height: 14),
                GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => openAllPlans(context),
                  child: _Card(
                    bordered: false,
                    child: Row(children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              l.paywallV3BundleTitle,
                              style: AlmaType.displayL.copyWith(
                                  fontSize: 16.5,
                                  height: 1.2,
                                  color: AlmaPalette.ink),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              // Цена текстом, не кнопкой — карточка тихая; а
                              // без цены остаётся состав: что мы продаём,
                              // известно и без App Store.
                              bundlePrice == null
                                  ? l.paywallV3BundleIncludes
                                  : '${l.paywallV3BundleIncludes} · ${l.paywallV3BundlePrice(bundlePrice)}',
                              style: AlmaType.meta.copyWith(
                                  fontSize: 12.5,
                                  height: 1.45,
                                  color: AlmaPalette.inkMuted),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        '→',
                        style: AlmaType.numeral.copyWith(
                            fontSize: 15, color: AlmaPalette.goldDeep),
                      ),
                    ]),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Карточка на пергаменте: с кантом — продающая, без — тихая (числа V3).
class _Card extends StatelessWidget {
  const _Card({required this.bordered, required this.child});

  final bool bordered;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 17),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: bordered
              ? Border.all(
                  color: AlmaPalette.goldDeep.withValues(alpha: 0.5))
              : null,
          gradient: bordered
              ? const LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Color(0xCCFFFCF4), Color(0x99E9DDC1)],
                )
              : null,
          color:
              bordered ? null : AlmaPalette.ink.withValues(alpha: 0.05),
        ),
        child: child,
      );
}

/// Кнопка-контур V3: высота 44, радиус 22, кант золота на 0.6, по содержимому.
/// Не [AlmaButton]: у той обводка ночная и высота 54 — иерархией экрана здесь
/// правит холст, а не общая метрика.
class _OutlineCta extends StatelessWidget {
  const _OutlineCta({required this.label, required this.onTap});

  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Align(
        alignment: AlignmentDirectional.centerStart,
        child: GestureDetector(
          onTap: onTap,
          child: Opacity(
            opacity: onTap == null ? 0.45 : 1,
            child: Container(
              height: 44,
              padding: const EdgeInsets.symmetric(horizontal: 20),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(22),
                border: Border.all(
                    color: AlmaPalette.goldDeep.withValues(alpha: 0.6)),
              ),
              child: Text(
                label,
                style: AlmaType.button
                    .copyWith(fontSize: 14, color: AlmaPalette.ink),
              ),
            ),
          ),
        ),
      );
}
