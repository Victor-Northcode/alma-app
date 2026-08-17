import 'package:flutter/material.dart';

import '../../billing/ladder.dart';
import '../../design/alma_presence.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import 'paywall_parts.dart';
import 'paywall_shell.dart';

/// V7 · квота вопросов: три бесплатных кончились, четвёртый уже задан.
///
/// Поверхность **P6**. Продаётся та же подписка, что на V6, и полка у них
/// общая — разный здесь **порядок обещаний**.
///
/// ## Заданный вопрос стоит над пейволлом, а не под ним
///
/// Сначала «твой вопрос никуда не делся», потом «вот сколько стоит ответ».
/// Переставить эти два блока — значит превратить экран в «заплати, чтобы
/// вернуть своё»; ровно поэтому пузырь с вопросом и метка удержания стоят
/// первыми, до света, заголовка и цены.
///
/// **Удержание — не картинка.** Вопрос действительно ждёт: беседа
/// (`alma_screen.dart`) держит его у себя и отправляет сама, как только этот
/// экран вернул `bought`. Метка обещает это словами, и обещание обязано быть
/// правдой — экран, сказавший «уйдёт, когда продолжишь», и потерявший вопрос,
/// стоит дороже любого пейволла.
///
/// ## Чего здесь нет
///
/// Цен разовых покупок. Ссылки «все планы» — человек пришёл с конкретным
/// вопросом, а не выбирать тариф. Формулировки «купи, чтобы отправить»: вопрос
/// уже принят, продаётся ответ.
class QuotaScreen extends StatelessWidget {
  const QuotaScreen({super.key, required this.question});

  /// Тот самый четвёртый вопрос, слово в слово.
  final String question;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return PaywallShell(
      intent: const PaywallIntent.questionQuota(),
      seed: 0x0D005607,
      builder: (context, deal) {
        final key = deal.first;
        final price = key == null ? null : deal.price(key);
        return Column(children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(
                  AlmaMetrics.pad, 12, AlmaMetrics.pad, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (question.trim().isNotEmpty) ...[
                    _Asked(question: question),
                    const SizedBox(height: 14),
                    _Held(l.paywallV3QuotaHeld),
                  ],
                  const SizedBox(height: AlmaMetrics.gapSection),
                  const Center(child: AlmaPresence(size: 56)),
                  const SizedBox(height: 16),
                  Text(
                    l.paywallV3QuotaTitle,
                    textAlign: TextAlign.center,
                    style: AlmaType.displayL.copyWith(fontSize: 27, height: 1.16),
                  ),
                  const SizedBox(height: 14),
                  Padding(
                    // Ещё 22 по бокам сверх поля страницы — на холсте абзац
                    // уже колонки, потому что он читается как тихий ответ, а
                    // не как заголовок.
                    padding: const EdgeInsets.symmetric(
                        horizontal: AlmaMetrics.pad),
                    child: Text(
                      l.paywallV3QuotaNote,
                      textAlign: TextAlign.center,
                      style: AlmaType.body.copyWith(
                        fontSize: 14,
                        height: 1.6,
                        color: AlmaPalette.body.withValues(alpha: 0.75),
                      ),
                    ),
                  ),
                  const SizedBox(height: 26),
                  _AlsoInside(
                    overline: l.paywallV3QuotaAlsoInside,
                    text: l.paywallV3QuotaAlsoInsideList,
                  ),
                ],
              ),
            ),
          ),
          PaywallBottom(children: [
            // Абзац продления **не тот же**, что на V6: третьим пунктом он
            // несёт обещание про отправку вопроса, и общего ключа у них нет.
            Text(
              l.paywallV3SubRenewalDisclosureQuota,
              style: AlmaType.meta.copyWith(fontSize: 12, height: 1.45),
            ),
            const SizedBox(height: 10),
            if (deal.loading)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 17),
                child: Text(l.stateLoadingShort, style: AlmaType.meta),
              )
            else
              PaywallCta(
                label: price == null || key == null
                    ? null
                    : l.paywallV3QuotaCta(price),
                store: deal.store,
                warm: true,
                onTap: () {
                  if (key != null) deal.buy(key);
                },
              ),
            PaywallNotice(store: deal.store),
            const SizedBox(height: 11),
            // TODO(canvas): ни `×`, ни `←` на кадре V7 нет (спека, дыра №6).
            // Пока экран закрывается «не сейчас» и краевым жестом маршрута —
            // оба с первого раза, как требует §5 правило 4.
            PaywallQuietLink(
              label: l.paywallNotNow,
              color: AlmaPalette.muted3,
              onTap: () => deal.close('not_now'),
            ),
          ]),
        ]);
      },
    );
  }
}

/// Пузырь заданного вопроса — прижат вправо, как в самой беседе.
class _Asked extends StatelessWidget {
  const _Asked({required this.question});

  final String question;

  @override
  Widget build(BuildContext context) => Align(
        alignment: Alignment.centerRight,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 280),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 11, horizontal: 16),
            decoration: BoxDecoration(
              color: AlmaPalette.veilStrong,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Text(
              question,
              style: AlmaType.body.copyWith(fontSize: 15, height: 1.5),
            ),
          ),
        ),
      );
}

/// Метка удержания: слово и золотая точка, сразу под вопросом.
class _Held extends StatelessWidget {
  const _Held(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Flexible(
            child: Text(
              text,
              textAlign: TextAlign.end,
              style: AlmaType.meta.copyWith(
                fontSize: 11.5,
                color: AlmaPalette.gold.withValues(alpha: 0.8),
              ),
            ),
          ),
          const SizedBox(width: 7),
          Container(
            width: 5,
            height: 5,
            decoration: const BoxDecoration(
              color: AlmaPalette.gold,
              shape: BoxShape.circle,
            ),
          ),
        ],
      );
}

/// Карточка «а ещё внутри»: то, что подписка открывает помимо вопросов.
///
/// Стоит **после** ответа на заданный вопрос, а не до: человек пришёл с
/// вопросом, и список всего остального до ответа читался бы витриной.
class _AlsoInside extends StatelessWidget {
  const _AlsoInside({required this.overline, required this.text});

  final String overline;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(vertical: 15, horizontal: 17),
        decoration: BoxDecoration(
          // `rgba(16,22,54,.4)` и кант `rgba(201,174,107,.28)` — числа V7.
          color: AlmaPalette.night700.withValues(alpha: 0.4),
          borderRadius: BorderRadius.circular(16),
          border:
              Border.all(color: AlmaPalette.gold.withValues(alpha: 0.28)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Text(overline.toUpperCase(),
                  style: AlmaType.readerHead.copyWith(
                    letterSpacing: 2,
                    color: AlmaPalette.gold,
                  )),
              const SizedBox(width: 12),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Container(
                    height: 1,
                    decoration:
                        BoxDecoration(gradient: AlmaGradient.fadedRule),
                  ),
                ),
              ),
            ]),
            const SizedBox(height: 9),
            Text(
              text,
              style: AlmaType.body.copyWith(
                fontSize: 13.5,
                height: 1.55,
                color: AlmaPalette.body.withValues(alpha: 0.8),
              ),
            ),
          ],
        ),
      );
}
