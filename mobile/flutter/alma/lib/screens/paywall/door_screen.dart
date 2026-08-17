import 'dart:io' show File;
import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../../billing/ladder.dart';
import '../../design/art.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import 'paywall_parts.dart';
import 'paywall_router.dart';
import 'paywall_shell.dart';

/// V2 · дверь: тап по закрытой главе статичного разбора.
///
/// Поверхность **P2**. Одна кнопка $4.99, строка «навсегда · без подписки»,
/// тихая ссылка «все планы» — и больше ничего. Соблазн «раз человек всё равно
/// смотрит на цену, покажем рядом и план» разобран один раз и в одном месте,
/// в шапке [PaywallIntent]; здесь только то, что из него следует: `ladderFor`
/// для двери возвращает **ровно одну** ступень, и второй цены на экране нет.
///
/// **Живых систем сюда не приходит.** Дверей у транзитов и соляра в v3 нет
/// вовсе, и маршрут для них ведёт на V6 — решает это маршрутизатор, а не глава
/// и не этот экран.
///
/// **`Restore` на двери нет, и это выбор холста, а не забывчивость.** Прежняя
/// дверь несла его строкой с доводом «Apple требует восстановление на каждой
/// поверхности, где продают разовые покупки». Требование Guideline 3.1.1 — про
/// приложение, а не про экран: восстановление живёт на V8 (куда ведёт тихая
/// ссылка отсюда), на V6 и в настройках. Если ревью однажды упрётся именно в
/// этот кадр, дешевле добавить строку сюда, чем спорить, — но добавлять её
/// заранее значит поставить на дверь второй тихий зов, которого холст не
/// рисовал.
///
/// ## Разметка
///
/// Числа холста (кадр 402 × 874): знак-веха 30 × 44 на 52 сверху, вклейка
/// закрытой главы 206 × 290 на 104, шит от 432 до низа. Отсчитываются они здесь
/// **от безопасной зоны**, а не от кромки стекла: холст статусной строки не
/// рисует, а устройство её имеет, и знак на 52 оказался бы под островом.
///
/// Зазор между низом вклейки и верхом шита — 38, и он же страховка на коротком
/// экране: вклейка ужимается, чтобы не заехать под стекло.
class DoorScreen extends StatelessWidget {
  const DoorScreen({
    super.key,
    required this.system,
    this.chapters,
    this.chapter,
  });

  final SystemSlug system;

  /// Сколько платных глав за дверью. `null` — оглавление не доехало; тогда
  /// заголовок обходится без числа, а не печатает выдуманное.
  final int? chapters;

  /// Глава, по которой тапнули: её номер, имя и вклейка.
  final DoorChapter? chapter;

  /// Кадр эталона. Все доли ниже считаются от него.
  static const _frameW = 402.0;
  static const _frameH = 874.0;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return PaywallShell(
      intent: PaywallIntent.door(system),
      // Небо двери — читательское: приглушённое поле без кометы. Свет,
      // ходящий поперёк, спорил бы и с картой, и с ценой.
      mood: SkyMood.reading,
      seed: 0x0D005632,
      builder: (context, deal) => LayoutBuilder(builder: (context, box) {
        final w = box.maxWidth;
        final h = box.maxHeight;
        final sheetTop = h * (432 / _frameH);
        final plateTop = h * (104 / _frameH);
        // Ширина вклейки — 206 из 402, но не настолько, чтобы она заехала под
        // шит: на коротком экране доли высоты и ширины расходятся, и побеждает
        // та, что оставляет вклейку целой.
        final byWidth = w * (206 / _frameW);
        final byHeight = (sheetTop - plateTop - 38) * (206 / 290);
        final plateW = byWidth < byHeight ? byWidth : byHeight;

        return Stack(children: [
          Positioned(
            left: 0,
            right: 0,
            top: h * (52 / _frameH),
            child: Center(child: PaywallWand(width: w * (30 / _frameW))),
          ),
          Positioned(
            left: 0,
            right: 0,
            top: plateTop,
            child: Center(
              child: _ChapterPlate(
                system: system,
                chapter: chapter,
                width: plateW > 0 ? plateW : 0,
              ),
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            top: sheetTop,
            bottom: 0,
            child: _DoorSheet(system: system, chapters: chapters, deal: deal),
          ),
          // **Крестик, которого на холсте нет.** §5 ТЗ, правило 4: пейволл
          // закрывается с первого раза. У V2 на холсте нет ни `×`, ни `←` —
          // спека называет это дырой №6 и рекомендует крестик, как на V6 и V8.
          // Он же оставляет жест «назад» краевым смахом маршрута.
          Positioned(
            right: AlmaMetrics.pad - 12,
            top: 0,
            child: Semantics(
              button: true,
              label: l.journeyClose,
              child: GestureDetector(
                onTap: () => deal.close('close'),
                behavior: HitTestBehavior.opaque,
                child: SizedBox(
                  width: 44,
                  height: 44,
                  child: Center(
                    child: Text('×',
                        style: AlmaType.button.copyWith(
                          fontSize: 18,
                          color: AlmaPalette.body.withValues(alpha: 0.6),
                        )),
                  ),
                ),
              ),
            ),
          ),
        ]);
      }),
    );
  }
}

/// Номер, имя и картина той главы, по которой тапнули.
///
/// Все три поля необязательны: дверь открывается и из главы, и с экрана
/// системы, и из «Сегодня», а знает о себе ровно то, что ей передали.
class DoorChapter {
  const DoorChapter({required this.numeral, required this.title, this.plate});

  /// «IV» — римская, из оглавления. Прописные ставит стиль.
  final String numeral;

  final String title;

  /// Имя вклейки (`AlmaPlates.name`) или `null`, если арта под эту главу ещё
  /// нет. Тогда на вклейке стоит карта системы — своя, а не чужая.
  final String? plate;
}

/// Вклейка закрытой главы: 206 × 290, радиус 14, кант 1.5 и тень в полэкрана.
///
/// **Картина грузится, а карта системы лежит в бандле** — поэтому запасной вид
/// не пустота и не шиммер: пока вклейка едет (и если она не приедет вовсе),
/// стоит карта системы. Дверь обязана показывать, что за ней, с первого кадра:
/// пустая рама на экране с ценой читается как сломанная покупка.
class _ChapterPlate extends StatefulWidget {
  const _ChapterPlate({
    required this.system,
    required this.chapter,
    required this.width,
  });

  final SystemSlug system;
  final DoorChapter? chapter;
  final double width;

  @override
  State<_ChapterPlate> createState() => _ChapterPlateState();
}

class _ChapterPlateState extends State<_ChapterPlate> {
  File? _file;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final plate = widget.chapter?.plate;
    if (plate == null || !mounted) return;
    final file = await SessionScope.of(context).plates.file(plate);
    if (mounted && file != null) setState(() => _file = file);
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final chapter = widget.chapter;
    final file = _file;
    return PaywallPlate(
      image: file != null
          ? FileImage(file) as ImageProvider
          : AssetImage(AlmaArt.card(widget.system)),
      width: widget.width,
      height: widget.width * 290 / 206,
      radius: 14,
      edge: 1.5,
      // Кант карты-героя — не золото палитры, а его светлая ступень на 0.6:
      // `rgba(228,196,138,.6)` холста.
      edgeColor: AlmaPalette.goldBright.withValues(alpha: 0.6),
      innerAlpha: 0.3,
      scrimStart: 0.4,
      alignment: Alignment.center,
      shadow: [
        BoxShadow(
          color: Colors.black.withValues(alpha: 0.7),
          blurRadius: 70,
          offset: const Offset(0, 26),
        ),
      ],
      captionInset: 14,
      captionBottom: 13,
      caption: chapter == null
          ? null
          : Column(
              children: [
                Text(
                  l.paywallV3DoorPlateChapter(chapter.numeral).toUpperCase(),
                  textAlign: TextAlign.center,
                  style: AlmaType.readerHead.copyWith(
                    fontSize: 10,
                    letterSpacing: 1.8,
                    color: AlmaPalette.gold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  chapter.title,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: AlmaType.headingM.copyWith(fontSize: 18, height: 1.2),
                ),
              ],
            ),
    );
  }
}

/// Шит двери: заголовок, довод и одна кнопка.
///
/// Числа холста: заливка от `rgba(13,17,32,.88)` к `rgba(7,10,22,.97)` на 60 %,
/// кант сверху золотом на 0.3, скругление 28 у верхних углов, размытие
/// подложки 14, поле 30. Блок действий уже шита на 4 с каждой стороны — на
/// холсте это `left/right 34` против поля 30.
class _DoorSheet extends StatelessWidget {
  const _DoorSheet({
    required this.system,
    required this.chapters,
    required this.deal,
  });

  final SystemSlug system;
  final int? chapters;
  final PaywallDeal deal;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final name = LadderKey.systemTitle(l, system);
    final key = deal.first;
    final price = key == null ? null : deal.price(key);
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Color(0xE00D1120), Color(0xF7070A16), Color(0xF7070A16)],
              stops: [0, 0.6, 1],
            ),
            border: Border(
              // `rgba(201,174,107,.3)` — кант шита на холсте V2.
              top: BorderSide(color: AlmaPalette.gold.withValues(alpha: 0.3)),
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(30, 26, 30, 0),
            // **Шит прокручивается целиком, но по умолчанию не двигается.**
            // Двумя частями — прижатым к верху текстом и прибитыми к низу
            // действиями — он остаётся ровно до тех пор, пока магазин отвечает
            // ценой. Стоило ему замолчать, как на месте кнопки вырастает
            // объяснение в три строки, и довод наверху обрезался бы на
            // полуслове; обрезанная фраза читается сломанным экраном, а не
            // экраном, который можно прокрутить.
            child: LayoutBuilder(builder: (context, box) {
              return SingleChildScrollView(
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: box.maxHeight),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(mainAxisSize: MainAxisSize.min, children: [
                        Text(
                          chapters == null
                              ? l.paywallV3DoorTitleAll(name)
                              : l.paywallV3DoorTitleSystem(chapters!, name),
                          textAlign: TextAlign.center,
                          style: AlmaType.displayL
                              .copyWith(fontSize: 28, height: 1.15),
                        ),
                        const SizedBox(height: 14),
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 300),
                          child: Text(
                            l.paywallV3DoorPitch,
                            textAlign: TextAlign.center,
                            // Довод набран светлым золотом, а не приглушённым
                            // серым: это довод, а не сноска.
                            style: AlmaType.body.copyWith(
                              fontSize: 13.5,
                              height: 1.6,
                              color: AlmaPalette.goldBright,
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ]),
                      Padding(
                        padding: EdgeInsets.only(
                          left: 4,
                          right: 4,
                          top: 16,
                          // Блок действий стоит на 74 от кромки кадра; на
                          // устройстве это безопасная зона плюс 40.
                          bottom: 40 + MediaQuery.paddingOf(context).bottom,
                        ),
                        child: Column(children: [
                          if (deal.loading)
                            Padding(
                              padding:
                                  const EdgeInsets.symmetric(vertical: 17),
                              child: Text(l.stateLoadingShort,
                                  style: AlmaType.meta),
                            )
                          else ...[
                            PaywallCta(
                              label: price == null || key == null
                                  ? null
                                  : l.paywallV3DoorCtaUnlock(price),
                              store: deal.store,
                              onTap: () {
                                if (key != null) deal.buy(key);
                              },
                            ),
                            if (price != null) ...[
                              const SizedBox(height: 11),
                              // Природа покупки стоит под ценой всегда: §5
                              // правило 5 — цена без длительности не бывает.
                              Text(
                                l.paywallV3DoorForever,
                                textAlign: TextAlign.center,
                                style: AlmaType.meta.copyWith(
                                  fontSize: 12.5,
                                  height: 1.5,
                                  color:
                                      AlmaPalette.body.withValues(alpha: 0.55),
                                ),
                              ),
                            ],
                          ],
                          PaywallNotice(store: deal.store),
                          const SizedBox(height: 14),
                          // **Единственная законная дорога с двери к
                          // лестнице.** Тихой ссылкой, а не второй кнопкой: у
                          // экрана один акцент, и он золотой.
                          PaywallQuietLink(
                            label: l.paywallV3PlansLink,
                            color: AlmaPalette.gold.withValues(alpha: 0.85),
                            onTap: () => openAllPlans(context),
                          ),
                        ]),
                      ),
                    ],
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}
