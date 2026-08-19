import 'package:flutter/material.dart';

import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/screen_scaffold.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import 'legal_text.dart';

/// Один из пяти юридических документов.
///
/// Открывается из настроек и из трёх ссылок в подвале витрины. В порте обе
/// дороги вели наружу, на `alma.pazl.ai`, которого не существует: пять строк
/// открывали браузер с ошибкой. Присутствующая и мёртвая ссылка хуже
/// отсутствующей — она читается как попытка закрыть чек-лист.
///
/// Текст лежит в бинарнике (см. [LegalText]), поэтому у экрана нет ни
/// состояния, ни загрузки, ни отказа. Это единственный экран приложения,
/// который не может не открыться, и так задумано.
class LegalScreen extends StatelessWidget {
  const LegalScreen({super.key, required this.document});

  final LegalDocument document;

  static String title(L l, LegalDocument document) => switch (document) {
        LegalDocument.terms => l.cabLegalTerms,
        LegalDocument.privacy => l.cabLegalPrivacy,
        LegalDocument.refunds => l.cabLegalRefunds,
        LegalDocument.subscriptionTerms => l.cabLegalSubscriptionTerms,
        LegalDocument.imprint => l.cabLegalImprint,
      };

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final doc = LegalText.of(document);
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      body: ScreenScaffold(
        mood: SkyMood.reading,
        seed: 0x4C454741,
        children: [
          // **Шапка рисуется здесь, а не слотами каркаса.**
          //
          // В макете над заголовком стоит «← DATA & LEGAL»: стрелка и название
          // раздела, из которого пришли, одной строкой. У каркаса надзаголовок
          // — строка, в неё кнопку не положить, а выше заголовка у него места
          // нет. Заодно чинится то, что этот экран **вообще не имел видимого
          // возврата**: он открывается `CupertinoPageRoute` без панели, и
          // назад вёл только краевой смах.
          //
          // Надзаголовком стояло «ALMA · PAZL LLC» — имя оператора, которое
          // ниже и так напечатано дважды, вместо того единственного, что тут
          // нужно: откуда сюда пришли и как выйти.
          Row(children: [
            // Знак маленький, цель большая: 18 × 18 не нажимается. Здесь стояли
            // отбивки 4 × 6 вокруг знака, то есть цель 26 × 40 — единственная в
            // продукте ниже сорока четырёх, которые остальные шапки держат
            // прямым числом (`system_screen`, `chapter_screen`, шапки витрин).
            // Промах здесь стоит дороже обычного: это экран, где человеку
            // показывают его же права, и единственный выход с него — эта
            // стрелка (открыт `CupertinoPageRoute` без панели).
            //
            // Знак прижат к левому канту цели, а не поставлен в её середину:
            // цель растёт вправо и вниз, а сам знак остаётся ровно на поле
            // страницы, где и стоял, — иначе он уехал бы вправо от поля, то
            // есть ровно тем дефектом, который в главах только что чинили.
            GestureDetector(
              onTap: () => Navigator.of(context).maybePop(),
              behavior: HitTestBehavior.opaque,
              child: SizedBox(
                width: 44,
                height: 44,
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text('←',
                      style: AlmaType.body
                          .copyWith(fontSize: 18, color: AlmaPalette.gold)),
                ),
              ),
            ),
            Text(l.cabDataAndLegal.toUpperCase(), style: AlmaType.overline),
          ]),
          Padding(
            padding: const EdgeInsets.only(top: 10, bottom: 4),
            child: Text(title(l, document), style: AlmaType.displayL),
          ),
          Text('Last updated ${LegalText.updated}', style: AlmaType.meta),
          // Признание — перед документом, а не под ним.
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Text(LegalText.preamble, style: AlmaType.meta),
          ),
          const _Rule(),
          Text(doc.lead, style: AlmaType.voice),
          for (final (i, section) in doc.sections.indexed) ...[
            const SizedBox(height: AlmaMetrics.gapLarge),
            // «1 · WHAT ALMA IS» — номер и разделитель, как в макете. Номер не
            // строка перевода: это порядковый номер раздела, и по нему на
            // документ ссылаются в переписке.
            //
            // **Без линейки и во всю ширину.** `SectionLabel` отдаёт подписи
            // 30.5% строки — доля, снятая с кабинета, где подписи в одно
            // слово. Заголовок документа так не живёт: «IF SOMETHING GOES
            // WRONG» вставало в четыре строки у левого края. В макете у
            // юридического экрана линейки нет вовсе.
            Text('${i + 1} · ${section.title}'.toUpperCase(),
                style: AlmaType.overline),
            const SizedBox(height: 6),
            for (final block in section.blocks) _Block(block: block),
          ],
          const SizedBox(height: AlmaMetrics.gapLarge),
          const _Rule(),
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(LegalText.footer, style: AlmaType.meta),
          ),
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text('${LegalText.operatorName} · Wyoming, United States',
                style: AlmaType.meta),
          ),
        ],
      ),
    );
  }
}

/// Абзац, список, факт или пропуск.
class _Block extends StatelessWidget {
  const _Block({required this.block});

  final LegalBlock block;

  @override
  Widget build(BuildContext context) {
    switch (block) {
      case LegalPara(:final text):
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Text(text, style: AlmaType.body),
        );

      case LegalPoints(:final items):
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final item in items)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Та же золотая точка, что на честной плашке витрины.
                      // Не системный маркер: залитый кружок — это список в
                      // приложении настроек.
                      Text('·', style: AlmaType.numeral),
                      const SizedBox(width: 10),
                      Expanded(child: Text(item, style: AlmaType.body)),
                    ],
                  ),
                ),
            ],
          ),
        );

      case LegalFact(:final label, :final value):
        return _FactRow(label: label, value: value);

      case LegalFactBlank(:final label, :final value):
        return _FactRow(label: label, value: '[$value]', missing: true);

      case LegalBlank(:final what):
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 2),
          child: Text('[$what]',
              style: AlmaType.body
                  .copyWith(color: AlmaPalette.disagree.withValues(alpha: 0.8))),
        );
    }
  }
}

class _FactRow extends StatelessWidget {
  const _FactRow({required this.label, required this.value, this.missing = false});

  final String label;
  final String value;
  final bool missing;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Вес 4/6, как во всех парах «подпись — значение» продукта: у
            // `Expanded` по умолчанию один flex, и значение запиралось в своей
            // половине.
            Expanded(flex: 4, child: Text(label, style: AlmaType.meta)),
            const SizedBox(width: 12),
            Expanded(
              flex: 6,
              child: Text(
                value,
                textAlign: TextAlign.right,
                style: AlmaType.body.copyWith(
                  color: missing
                      ? AlmaPalette.disagree.withValues(alpha: 0.8)
                      : AlmaPalette.body,
                ),
              ),
            ),
          ],
        ),
      );
}

/// Линейка, гаснущая к краям, — та же, что делит разделы кабинета.
class _Rule extends StatelessWidget {
  const _Rule();

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 14),
        child: Container(
          height: 1,
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [
              AlmaPalette.hairlineGold,
              AlmaPalette.hairlineGold.withValues(alpha: 0),
            ]),
          ),
        ),
      );
}
