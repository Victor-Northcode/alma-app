import 'package:flutter/material.dart';

import '../../billing/ladder.dart';
import '../../design/art.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import 'paywall_parts.dart';
import 'paywall_router.dart';
import 'paywall_shell.dart';

/// V6 · подписка: «Вся Alma — $9.99 / месяц».
///
/// Поверхность **P5**. Сюда ведут тап по закрытому блоку живого слоя на
/// «Сегодня» и тап по закрытой главе транзитов или соляра — двери у них нет и
/// не будет: они пересчитываются, и продать их «навсегда» значит продать
/// подписку, не взяв за неё денег.
///
/// ## Порядок донного блока переставлять нельзя
///
/// ✦-строка о вечном → абзац продления → кнопка. Довод в §7 ТЗ: жалобы «думала,
/// всё входит в подписку» названы красной линией проекта, и строка, разделяющая
/// ожидания, обязана стоять **над** ценой, а не под ней и не мелким кеглем.
/// Абзац продления над кнопкой требуют вдобавок правила магазинов: о повторном
/// списании человек узнаёт до нажатия, а не из выписки.
///
/// ## Чего здесь нет
///
/// Ни одной цены разовой покупки — ни $4.99, ни бандла. Слово «навсегда»
/// появляется ровно один раз и говорит о **другом** товаре («разборы, купленные
/// навсегда»). Слов «бесплатно» и «попробуй» нет вовсе: триала не существует,
/// и §5 запрещает «бесплатно» рядом с подпиской даже в виде намёка.
class SubscriptionScreen extends StatelessWidget {
  const SubscriptionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return PaywallShell(
      intent: const PaywallIntent.subscription(),
      seed: 0x0D005606,
      builder: (context, deal) {
        final key = deal.first;
        final price = key == null ? null : deal.price(key);
        return Column(children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(
                  AlmaMetrics.pad, 12, AlmaMetrics.pad, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  PaywallHeader(
                    overline: l.paywallV3SubOverline,
                    onClose: () => deal.close('close'),
                  ),
                  const SizedBox(height: 6),
                  Text(l.paywallV3SubTitle, style: AlmaType.displayL),
                  const SizedBox(height: 16),
                  PaywallPlate(
                    // Живой слой — это небо, и картина у него та же, что стоит
                    // за всем продуктом. Своей картинки у него нет и быть не
                    // должно: транзиты и соляр не предмет, а движение.
                    image: const AssetImage(AlmaArt.sky),
                    height: 150,
                    // `rgba(201,174,107,.42)` — кант вклейки V6.
                    edgeColor: AlmaPalette.gold.withValues(alpha: 0.42),
                    caption: Text(
                      l.paywallV3SubPlateCaption,
                      style: AlmaType.headingM.copyWith(fontSize: 18),
                    ),
                  ),
                  const SizedBox(height: 16),
                  for (final line in [
                    l.paywallV3SubIncludesTransits,
                    l.paywallV3SubIncludesSolar,
                    l.paywallV3SubIncludesPair,
                    l.paywallV3SubIncludesQuestions,
                  ])
                    _Included(line),
                ],
              ),
            ),
          ),
          PaywallBottom(children: [
            // 1. Строка, разделяющая ожидания. Читается первой из трёх — она
            //    полужирная и светлее соседей.
            PaywallSpark(text: l.paywallV3SubForeverStays),
            const SizedBox(height: 10),
            // 2. Абзац продления. TODO(stores): фраза называет Apple ID, а
            //    продукт кроссплатформенный; варианта для Play на холсте нет
            //    (спека, дыра №7) — решение владельца.
            Text(
              l.paywallV3SubRenewalDisclosure,
              style: AlmaType.meta.copyWith(fontSize: 12, height: 1.45),
            ),
            const SizedBox(height: 10),
            // 3. И только теперь цена.
            if (deal.loading)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 17),
                child: Text(l.stateLoadingShort, style: AlmaType.meta),
              )
            else
              PaywallCta(
                label: price == null || key == null
                    ? null
                    : l.paywallV3SubCta(price),
                store: deal.store,
                warm: true,
                onTap: () {
                  if (key != null) deal.buy(key);
                },
              ),
            PaywallNotice(store: deal.store),
            const SizedBox(height: 11),
            // 4. Подвал. `Restore` требуют оба магазина — он не продаёт, а
            //    возвращает; «Все планы» — единственная продающая ссылка.
            PaywallFooter(store: deal.store, children: [
              PaywallQuietLink(
                label: l.paywallV3PlansLink,
                onTap: () => openAllPlans(context),
              ),
            ]),
          ]),
        ]);
      },
    );
  }
}

/// Пункт состава: точка 4 × 4 и строка Golos 14/1.5.
///
/// Точка стоит на первой строке, а не по центру блока: у двухстрочного пункта
/// центр уезжает вниз, и точка оказывается напротив пустоты.
class _Included extends StatelessWidget {
  const _Included(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 9),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              margin: const EdgeInsets.only(top: 7),
              width: 4,
              height: 4,
              decoration: const BoxDecoration(
                color: AlmaPalette.gold,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Text(
                text,
                style: AlmaType.body.copyWith(fontSize: 14, height: 1.5),
              ),
            ),
          ],
        ),
      );
}
