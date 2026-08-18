import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';

import '../../billing/ladder.dart';
import '../../design/buttons.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../billing/store_words.dart';
import '../legal/legal_screen.dart';
import '../legal/legal_text.dart';
import 'paywall_parts.dart';
import 'paywall_shell.dart';

/// V8 · все планы: единственный экран каталога, где видно несколько цен.
///
/// Поверхность **P7**. Открывается **только** по тихим ссылкам «Все планы» с
/// двери и с подписки и из настроек — никогда сам. Автоматический показ этого
/// экрана есть возврат к той самой лестнице, ради отмены которой затевался v3.
///
/// ## Две подписанные группы, а не ступени
///
/// Группы названы обещаниями — «навсегда» и «подписка», — а не механикой
/// («разовое / автопродление»). Разовое стоит **выше**: школа продукта —
/// маленький честный первый платёж, и порядок групп её повторяет.
///
/// ## Что здесь покупается, а что просто названо ценой
///
/// Холст не нарисовал ни одного нажатого состояния — спека называет это самой
/// дорогой дырой (№2). Решение принято такое: **строка, за которой стоит ровно
/// один товар, — кнопка; строка, за которой стоит выбор, — цена словами.**
///
/// * «Все пять разборов» и «Вся Alma» — по одному SKU, тап открывает лист
///   магазина сразу. Это честнее второй схемы («выбрать строку, потом кнопка
///   внизу»): та воспроизводит лестницу, которую v3 как раз убил;
/// * «Один разбор» — это пять дверей по одной цене, и тапнуть «одну из пяти»
///   нельзя: какую именно, решают в «Моих системах», а не здесь. Строка
///   называет цену и молчит;
/// * «Разбор пары» — consumable на конкретного человека. Покупка без адресата
///   существует, но как **сбой** (W6, `unbound`), и заводить её нажатием
///   означало бы делать сбой штатным путём. Покупается пара во флоу пары, где
///   человек уже назван.
class PlansScreen extends StatelessWidget {
  const PlansScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return PaywallShell(
      intent: const PaywallIntent.plans(),
      seed: 0x0D005608,
      builder: (context, deal) {
        final doors = [
          for (final key in deal.rungs)
            if (key.system != null) key,
        ];
        final bundle = deal.rungs.contains(LadderKey.bundleStatic);
        final pair = deal.rungs.contains(LadderKey.pairCheck);
        final plan = deal.rungs.contains(LadderKey.subMonthly);
        // Цена «одного разбора» — самая дешёвая из **оставшихся** дверей, а не
        // первая попавшаяся: у купившей четыре двери на полке остаётся одна, и
        // строка обязана называть её цену.
        final doorPrice = deal.store.cheapestOf(doors);
        final forever = <Widget>[
          if (doors.isNotEmpty)
            _PlanRow(
              title: l.paywallV3PlansOneReading,
              note: l.paywallV3BundleIncludes,
              price: doorPrice,
            ),
          if (bundle)
            _PlanRow(
              title: l.paywallV3BundleTitle,
              note: l.paywallV3PlansAllFiveNote,
              price: deal.price(LadderKey.bundleStatic),
              onTap: deal.busy
                  ? null
                  : () => deal.buy(LadderKey.bundleStatic),
            ),
          if (pair)
            _PlanRow(
              title: l.paywallV3PlansPair,
              note: l.paywallV3PlansPairNote,
              price: deal.price(LadderKey.pairCheck),
            ),
        ];

        return Column(children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(
                  AlmaMetrics.pad, 12, AlmaMetrics.pad, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  PaywallHeader(
                    overline: l.paywallV3PlansOverline,
                    onClose: () => deal.close('close'),
                  ),
                  const SizedBox(height: 6),
                  Text(l.paywallV3PlansTitle, style: AlmaType.displayL),
                  if (deal.loading)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 40),
                      child: Center(
                          child: Text(l.stateLoadingShort,
                              style: AlmaType.meta)),
                    )
                  // **Пустая полка — это два разных состояния, и путать их
                  // нельзя.**
                  //
                  // Здесь стояло одно условие на оба, и человеку без единой
                  // покупки экран говорил «всё открыто, сорок одна глава твоя»
                  // над дырой в пол-экрана. Найдено глазами на симуляторе:
                  // товаров в консоли ещё нет, магазин молчит, полка пуста — и
                  // фраза о правах читалась как обещание, которого никто не
                  // давал.
                  //
                  // Молчащий магазин — факт о сети, и о правах он не говорит
                  // ничего. Дверь (`V2`) сообщает о нём прямо; витрина обязана
                  // тем же тоном, а не пустотой под заголовком «все планы».
                  else if (deal.store.silent) ...[
                    const SizedBox(height: 20),
                    Text(l.storeUnavailable, style: AlmaType.body),
                    const SizedBox(height: 14),
                    AlmaButton(
                      kind: AlmaButtonKind.veil,
                      fills: false,
                      label: l.stateRetry,
                      onTap: deal.busy ? null : () => deal.store.load(),
                    ),
                  ]
                  // А это уже правда о владельце: магазин ответил, и на полке
                  // для неё ничего не осталось.
                  else if (forever.isEmpty && !plan) ...[
                    const SizedBox(height: 20),
                    Text(l.paywallOwnedAll, style: AlmaType.voice),
                    const SizedBox(height: 14),
                    Text(l.storeManageNote, style: AlmaType.meta),
                  ],
                  if (forever.isNotEmpty) ...[
                    const SizedBox(height: 20),
                    _GroupLabel(l.paywallV3PlansGroupForever),
                    const SizedBox(height: 4),
                    for (final (i, row) in forever.indexed)
                      Container(
                        decoration: i == 0
                            ? null
                            : BoxDecoration(
                                border: Border(
                                  top: BorderSide(
                                      color: AlmaPalette.veilStrong),
                                ),
                              ),
                        child: row,
                      ),
                  ],
                  if (plan) ...[
                    const SizedBox(height: 14),
                    _GroupLabel(l.paywallV3PlansGroupSubscription),
                    const SizedBox(height: 8),
                    _PlanCard(
                      title: l.paywallV3SubTitleShort,
                      price: deal.price(LadderKey.subMonthly),
                      includes: l.paywallV3SubIncludesLine,
                      onTap: deal.busy
                          ? null
                          : () => deal.buy(LadderKey.subMonthly),
                    ),
                  ],
                  const SizedBox(height: 12),
                  // Строка-разделитель ожиданий. Стоит **под обеими** группами
                  // и говорит ровно то, из-за чего пишут «думала, всё входит в
                  // подписку»: купленное навсегда отменой не гасится.
                  PaywallSpark(
                      text: l.paywallV3PlansDividerNote, size: 12.5),
                  PaywallNotice(store: deal.store, centred: false),
                ],
              ),
            ),
          ),
          PaywallBottom(children: [
            // Юридический абзац закрывает обе группы одной фразой — и
            // продление подписки, и «разовые не продлеваются никогда».
            // Сокращать при переводе нельзя: требование ревью магазинов.
            // TODO(stores): Apple ID вшит и здесь — варианта для Play на
            // холсте нет (спека, дыра №7).
            Text(
              l.paywallV3PlansLegal,
              style: AlmaType.meta.copyWith(
                fontSize: 11.5,
                height: 1.45,
                color: AlmaPalette.muted3,
              ),
            ),
            const SizedBox(height: 8),
            PaywallFooter(store: deal.store, children: const [
              _LegalLink(LegalDocument.terms),
              _LegalLink(LegalDocument.privacy),
            ]),
          ]),
        ]);
      },
    );
  }
}

/// Метка группы: Golos 600 11 ls 2.2 золотом и гаснущая линия за ней.
class _GroupLabel extends StatelessWidget {
  const _GroupLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Row(children: [
        Text(text.toUpperCase(), style: AlmaType.readingPart),
        const SizedBox(width: 12),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Container(
              height: 1,
              decoration: BoxDecoration(gradient: AlmaGradient.fadedRule),
            ),
          ),
        ),
      ]);
}

/// Строка группы «навсегда»: имя, состав, цена справа.
///
/// **Цена — из каталога локали, и только оттуда.** `null` значит, что магазин
/// не ответил: колонка остаётся пустой, а строка остаётся на месте — что мы
/// продаём, известно и без App Store.
class _PlanRow extends StatelessWidget {
  const _PlanRow({
    required this.title,
    required this.note,
    required this.price,
    this.onTap,
  });

  final String title;
  final String note;
  final String? price;

  /// `null` — строка называет цену, но не покупает. См. шапку [PlansScreen].
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: price == null ? null : onTap,
        behavior: HitTestBehavior.opaque,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 13),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        style: AlmaType.headingM
                            .copyWith(fontSize: 17, height: 1.2)),
                    const SizedBox(height: 3),
                    Text(
                      note,
                      style: AlmaType.meta.copyWith(
                        fontSize: 12.5,
                        color: AlmaPalette.body.withValues(alpha: 0.7),
                      ),
                    ),
                  ],
                ),
              ),
              if (price != null) ...[
                const SizedBox(width: 12),
                Padding(
                  padding: const EdgeInsets.only(top: 1),
                  child: Text(price!, style: AlmaType.numeral),
                ),
              ],
            ],
          ),
        ),
      );
}

/// Карточка подписки: единственный акцент экрана.
///
/// Цена набрана `starFill` — светлее всех прочих цен, — и это весь способ, каким
/// подписка здесь выделена. Ни золотой кнопки, ни «выгоднее», ни зачёркнутых
/// чисел: арифметики на этом экране нет вовсе.
class _PlanCard extends StatelessWidget {
  const _PlanCard({
    required this.title,
    required this.price,
    required this.includes,
    this.onTap,
  });

  final String title;
  final String? price;
  final String includes;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return GestureDetector(
      onTap: price == null ? null : onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 15, horizontal: 17),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          // Кант `rgba(228,196,138,.5)` и заливка золотом от 0.14 к 0.03 —
          // числа карточки подписки на холсте.
          border: Border.all(
              color: AlmaPalette.goldBright.withValues(alpha: 0.5)),
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              AlmaPalette.gold.withValues(alpha: 0.14),
              AlmaPalette.gold.withValues(alpha: 0.03),
            ],
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(title,
                      style: AlmaType.headingM
                          .copyWith(fontSize: 18, height: 1.2)),
                ),
                if (price != null)
                  Text(
                    l.paywallV3SubPrice(price!),
                    style: AlmaType.numeral.copyWith(
                        fontSize: 15, color: AlmaPalette.starFill),
                  ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              includes,
              style: AlmaType.meta.copyWith(
                fontSize: 12.5,
                height: 1.5,
                color: AlmaPalette.body.withValues(alpha: 0.78),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Ссылка на документ: золотая, подчёркнутая, открывает экран.
///
/// Guideline 3.1.2 просит рабочие ссылки на «Условия» и «Политику» с того
/// экрана, где продаётся подписка, и рецензент открывает каждую. Документы —
/// экраны, а не веб-ссылки: ссылка наружу может лежать в тот самый день, когда
/// идёт ревью.
class _LegalLink extends StatelessWidget {
  const _LegalLink(this.document);

  final LegalDocument document;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return PaywallQuietLink(
      label: switch (document) {
        LegalDocument.terms => l.paywallTerms,
        LegalDocument.privacy => l.paywallPrivacy,
        LegalDocument.subscriptionTerms => l.paywallSubscriptionTerms,
        LegalDocument.refunds => l.cabLegalRefunds,
        LegalDocument.imprint => l.cabLegalImprint,
      },
      onTap: () => Navigator.of(context, rootNavigator: true).push(
        CupertinoPageRoute(builder: (_) => LegalScreen(document: document)),
      ),
    );
  }
}
