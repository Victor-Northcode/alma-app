import 'package:flutter/material.dart';

import '../design/metrics.dart';
import '../design/palette.dart';
import '../design/screen_scaffold.dart';
import '../design/section_label.dart';
import '../design/typography.dart';
import '../l10n/alma_l10n.dart';
import '../net/alma_client.dart';
import '../net/models.dart';
import '../state/session.dart';

/// Предложение: что можно открыть и почём.
///
/// Полка приходит с сервера целиком — названия, сроки и **цены строкой**.
/// Своего форматирования здесь нет намеренно: витрина и чек обязаны показывать
/// одно число, а валюту знает тот, кто её считает.
///
/// Кнопки пока не покупают: магазина в порте ещё нет. Экран честно показывает,
/// что есть и сколько стоит, и на этом останавливается — рисовать рабочую
/// покупку там, где её нет, значит обмануть дважды: человека и себя.
class OfferScreen extends StatefulWidget {
  const OfferScreen({super.key});

  @override
  State<OfferScreen> createState() => _OfferScreenState();
}

class _OfferScreenState extends State<OfferScreen> {
  List<Plan> _plans = const [];
  bool _loading = true;
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    _load();
  }

  Future<void> _load() async {
    final session = SessionScope.of(context);
    try {
      final plans = await session.client.catalogue(locale: session.locale);
      if (mounted) {
        setState(() {
          // Условную цену — апгрейд архива — на полке не показывают: она
          // существует только внутри другой покупки.
          _plans = plans.where((p) => p.offered == 'shelf').toList();
          _loading = false;
        });
      }
    } on AlmaError {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final subscriptions = _plans.where((p) => p.isSubscription).toList();
    final doors = _plans.where((p) => !p.isSubscription).toList();

    return ScreenScaffold(
      seed: 0x4F464645,
      title: l.paywallEverythingTitle,
      children: [
        Text(l.paywallEverythingSub, style: AlmaType.meta),
        const SizedBox(height: AlmaMetrics.gapLarge),
        if (_loading)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 40),
            child: Center(child: Text(l.stateLoadingShort, style: AlmaType.meta)),
          )
        else ...[
          if (subscriptions.isNotEmpty) ...[
            SectionLabel(l.cabPlansCta),
            const SizedBox(height: 8),
            for (final plan in subscriptions)
              _PlanRow(title: _title(l, plan), price: plan.display, accent: true),
          ],
          if (doors.isNotEmpty) ...[
            const SizedBox(height: AlmaMetrics.gapLarge),
            SectionLabel(l.cabChapters),
            const SizedBox(height: 8),
            for (final plan in doors)
              _PlanRow(title: plan.name, price: plan.display, accent: false),
          ],
        ],
      ],
    );
  }

  /// Подписки названы в каталоге строк — по-русски и на остальных шести;
  /// имя из ответа сервера английское и годится только как запас.
  String _title(L l, Plan plan) => switch (plan.kind) {
        'weekly' => l.paywallWeeklyTitle,
        'monthly' => l.paywallMonthlyTitle,
        'annual' => l.paywallAnnualTitle,
        _ => plan.name,
      };
}

class _PlanRow extends StatelessWidget {
  const _PlanRow({required this.title, required this.price, required this.accent});

  final String title;
  final String price;
  final bool accent;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Row(children: [
          Expanded(
            child: Text(title,
                style: accent
                    ? AlmaType.body.copyWith(fontSize: 17)
                    : AlmaType.body),
          ),
          const SizedBox(width: 12),
          Text(price,
              style: AlmaType.numeral.copyWith(
                color: accent ? AlmaPalette.goldBright : AlmaPalette.gold,
                fontSize: accent ? 17 : 15,
              )),
        ]),
      );
}
