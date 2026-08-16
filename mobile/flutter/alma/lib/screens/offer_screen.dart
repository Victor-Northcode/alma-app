import 'dart:math' as math;

import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';

import '../billing/alma_store.dart';
import '../billing/ladder.dart';
import '../design/arrival.dart';
import '../design/art.dart';
import '../design/buttons.dart';
import '../design/gold_texture.dart';
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
/// * ступени с подписью под каждой и пилюлей цены справа, без карточек и рамок;
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
///
/// ## Вид, а не только состав
///
/// До 16 августа 2026 здесь стоял правильный по составу экран и **никакой** по
/// виду: заголовок, простыня абзацев, ступени кружками-радиокнопками и цена
/// голым числом на голом небе. Владелец: «вот этот экран и прочие продажные
/// экраны вообще нормально не сделаны». Претензия не к словам — к тому, что
/// продающий экран продукта, у которого весь товар это написанный текст,
/// выглядел как настройки. Эталоны `s8`, `s37`, `s38`, `s42`, `s43` называют
/// три вещи, которых не было ни одной:
///
/// * **картина в раме** — витрина открывается предметом, а не абзацем
///   (`_ArtCard`, `_NamePlate`);
/// * **ступень-плашка** — у ступени своя рамка, и она же показывает выбор
///   (`_Rung`), поэтому кружок-радиокнопка убран;
/// * **пилюля цены** — число стоит на своей плашке и повторяет тот же выбор
///   (`_PricePill`).
///
/// Плюс свечение под золотой кнопкой (`_Glowing`) — из `s42`/`s43`.
///
/// ### Второй заход, тот же день
///
/// Первый заход арт добавил, но добавил **полосами**: широкий кадр ворот под
/// лидом и филигрань-разделитель между фактами и ценами. Владелец, глядя
/// третий раз: «тут всё не так, как в дизайне», «картинки вставлены сырыми
/// полосами», «в макете это витрина, у нас — документ». Что сделано и почему:
///
/// * полоса ворот и карта двери сведены в **одну пергаментную раму** `s43`
///   (170×240): в эталонах витрины фотографии без рамы нет ни одной, и рама —
///   это и есть разница между предметом на витрине и куском обоев;
/// * филигрань **убрана совсем**. Её нет ни на одном из эталонных экранов:
///   `art-divider` в разметке дизайн-проекта не встречается ни разу. Стояла она
///   между фактами и лестницей и читалась ровно тем, чем была, — куском чужой
///   фотографии посреди текста;
/// * ступени из строк, разделённых волосом, стали плашками `s38`. Причина не
///   косметическая: единственным указателем выбора была пилюля цены, а цену
///   печатает App Store, — и на молчащем магазине лестница выходила рядом голых
///   абзацев без всякого следа выбора.
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
  ///
  /// **Что здесь «первая», решает [ladderFor], а не этот экран.** С 16 августа
  /// 2026 лестница подписок стоит снизу вверх — неделя, месяц, год, — и
  /// предвыбранной оказывается неделя. Решение владельца, и оно отменяет
  /// прежний порядок с годом во главе: предвыбранный год — якорь-перевёртыш.
  /// Он не поднимает средний чек, а переворачивает вопрос с «сколько платить»
  /// на «платить ли вообще»; на этом якоре тонут Nebula и Pattern. Наша школа
  /// — маленький честный первый платёж, а год продаёт свою математику
  /// последним, когда цены недели и месяца уже названы. Разовая покупка
  /// («вся Alma, куплена однажды») лестницей подписок не является и стоит там
  /// же, где стояла. Целиком довод — в шапке `ladderFor`; переставлять порядок
  /// здесь, поверх результата лестницы, нельзя: это второе место, которое
  /// однажды разойдётся с первым.
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
          // **Картина стоит ровно здесь, а не под заголовком.** В эталоне
          // `s37` арт замерен на y=216 — то есть после вводного абзаца и до
          // перечня: сначала говорят, что продают, потом показывают.
          _Crown(door: door),
          // Что покупают — до всякой цены и до всякой ошибки. Владелец однажды
          // ткнул в закрытую главу на симуляторе без магазина и попал на
          // страницу, всё содержимое которой было «App Store не отвечает».
          _Facts(door: door != null),
          // `margin-top:10px` у блока лестницы в `s8`. Отбивать её от фактов
          // сильнее нечем: у ступеней теперь своя рамка, и она сама держит
          // расстояние.
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
            for (final key in rungs)
              _Rung(
                rung: key,
                price: _store.price(key),
                selected: key == chosen,
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
          for (final (i, line) in lines.indexed)
            Padding(
              // Семь точек между строками, но не после последней: в эталоне
              // `margin-bottom` стоит у всех, кроме неё, и лишний хвост сдвигал
              // весь следующий блок.
              padding: EdgeInsets.only(bottom: i == lines.length - 1 ? 0 : 7),
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

/// Ступень: плашка с именем и подписью, ценой справа.
///
/// **Выбор показывает сама плашка, а не кружок.** Кружок-радиокнопка стоял
/// слева от каждой строки и был первым, что владелец назвал вслух: ряд пустых
/// кружков на голом небе читается как анкета, а не как полка.
///
/// **И не одна пилюля цены.** Пилюля из `s43` осталась и по-прежнему говорит о
/// выборе, но нести его одна она не может: цену печатает App Store, а он
/// молчит и на симуляторе, и на отвалившейся сети, и до одобрения товаров. В
/// этом состоянии лестница выходила рядом голых строк, разделённых волосом, —
/// ровно то, что владелец увидел с третьего раза: «тут всё не так, как в
/// дизайне», «ступени — голые строки». Указатель выбора, исчезающий вместе с
/// ценой, — это отсутствующий указатель.
///
/// Форма взята у `s38`, где эталон выбирает одно из двух и у каждого варианта
/// заголовок с подписью: поле 16×20, скругление 18, промежуток 12; выбранное —
/// обводка `#C9AE6B` и заголовок `#E4D3A2`, невыбранное — обводка
/// `rgba(237,231,218,.1)` и заголовок `#F6F1E4`. Заливки нет ни у того, ни у
/// другого: витрина остаётся ночью с предметами на ней, а не панелью.
class _Rung extends StatelessWidget {
  const _Rung({
    required this.rung,
    required this.price,
    required this.selected,
    required this.onTap,
  });

  final LadderKey rung;

  /// `null` — магазин не ответил. Колонка остаётся пустой: единственное, что
  /// нельзя выдумывать, это число.
  final String? price;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Opacity(
          opacity: onTap == null ? 0.75 : 1,
          child: AnimatedContainer(
            duration: AlmaMotion.ui,
            curve: AlmaMotion.uiCurve,
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: selected ? AlmaPalette.gold : AlmaPalette.hairline,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        rung.title(l),
                        style: AlmaType.headingM.copyWith(
                          color: selected
                              ? AlmaPalette.goldBright
                              : AlmaPalette.inkLight,
                        ),
                      ),
                    ),
                    // Магазин молчит — колонки нет вовсе. Пустая пилюля обещала
                    // бы число, которого никто не называл.
                    if (price != null) ...[
                      const SizedBox(width: 12),
                      _PricePill(price: price!, selected: selected),
                    ],
                  ],
                ),
                // Подпись во всю ширину плашки, а не в колонку рядом с ценой:
                // зажатая пилюлей, она уходила в четыре строки и растила
                // ступень выше картины.
                const SizedBox(height: 3),
                Text(rung.note(l), style: AlmaType.meta),
              ],
            ),
          ),
        ),
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
        ] else ...[
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: _Glowing(
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
          ),
          // Разовая покупка получает свою строчку под кнопкой — как в `s42`,
          // где под «Open the Birth Card · $5.99» стоит «one payment · yours
          // permanently». У подписки над кнопкой уже стоит раскрытие об
          // автопродлении, и вторая мелкая строка спорила бы с ним.
          if (!chosen.isSubscription)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Text(
                l.paywallOneTimeFine,
                textAlign: TextAlign.center,
                style: AlmaType.meta.copyWith(
                    color: AlmaPalette.body.withValues(alpha: 0.55)),
              ),
            ),
        ],
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

/* ── картина витрины ─────────────────────────────────────────────────────── */

/// Что венчает витрину: общая дверь или та, за которой пришли.
///
/// **Одна картина на экран, и она обязана говорить про этот экран.** За одной
/// системой пришли — стоит её собственная карта: экран, продающий нумерологию
/// под общей картинкой ворот, не отличается от экрана, продающего всё. Пришли
/// за всем — стоят ворота.
///
/// **Обе картины — в одной раме, и рама здесь важнее картины.** До 16 августа
/// 2026 у двух случаев было два разных вида: дверь получала пергаментную карту
/// `s42`, а «вся Alma» — широкую полосу фотографии с золотым кантом. Владелец о
/// полосе: «картинки вставлены сырыми полосами, верхняя занимает четверть
/// экрана». И он прав по существу, а не по вкусу: кадр во всю колонку, кроме
/// скругления не имеющий формы, читается наклейкой поверх неба — тем более что
/// внутри у него фотография с собственной перспективой. В эталонах витрины
/// (`s42`, `s43`) фотографии «просто так» нет ни одной: арт **всегда** внутри
/// пергаментной рамы, и именно рама делает его предметом на витрине, а не
/// куском обоев. Поэтому рама одна на оба случая, а разное — только то, что в
/// ней лежит и как оно подписано.
class _Crown extends StatelessWidget {
  const _Crown({required this.door});

  /// `null` — витрина целиком.
  final SystemSlug? door;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Padding(
      // Снизу больше, чем сверху: табличка свисает за нижний край рамы, и
      // 16 точек, которых хватало карте, она бы вынесла на первую ступень.
      padding: const EdgeInsets.only(top: 18, bottom: 26),
      child: _ArtCard(
        image: door == null ? AlmaArt.gates : AlmaArt.card(door!),
        // Ворота ничем не названы — им нужна табличка. Карту системы уже
        // назвал заголовок экрана, и вторая подпись была бы эхом.
        plate: door == null ? l.cabAllAlmaPill : null,
        // Звёзды по углам — приём карточной рамы `s42`, и он принадлежит
        // карте. У ворот вместо них табличка; два украшения на одной раме
        // спорят.
        stars: door != null,
      ),
    );
  }
}

/// Картина витрины в пергаментной раме.
///
/// Порт рамы `s43` — «full access, framed art»: 170×240, поле 8, скругление 12,
/// внутренний штрих с отступом 5 и скруглением 8 цветом `rgba(168,135,60,.45)`,
/// картинка со скруглением 6, тень `0 20px 55px rgba(0,0,0,.6)` и золотой волос
/// по контуру `rgba(201,174,107,.4)`. Всё пересчитано от ширины рамы, чтобы она
/// не разъезжалась на узком телефоне.
///
/// Ширина — 42.5% колонки, но не больше 170 точек эталона. В `s43` карта
/// занимает 42% ширины экрана и там она **весь** экран; здесь под ней ещё лид,
/// три факта и лестница цен, и рама в полный рост эталона отправила бы первую
/// цену за нижний край.
///
/// **Картинка садится `cover` и теряет по краю — так и надо.** Ворота
/// (402×603) и карты систем (280×420) обе портретные и обе почти той же
/// пропорции, что просвет рамы; кадрируется несколько процентов по высоте.
/// Полоса, которая стояла здесь раньше, выбрасывала из ворот две трети кадра.
class _ArtCard extends StatelessWidget {
  const _ArtCard({
    required this.image,
    required this.plate,
    required this.stars,
  });

  final String image;

  /// Табличка под нижним краем рамы. `null` — картину подписывать нечем.
  final String? plate;
  final bool stars;

  /// Рама эталона `s43`.
  static const _w = 170.0;
  static const _h = 240.0;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, box) {
      final w = math.min(box.maxWidth * 0.425, _w);
      final k = w / _w; // всё остальное — доли эталонной ширины
      return Center(
        child: _Floating(
          child: SizedBox(
            width: w,
            height: _h * k,
            // Табличка свисает ниже рамы — обрезать её нечем и незачем.
            child: Stack(clipBehavior: Clip.none, fit: StackFit.expand, children: [
              Container(
                padding: EdgeInsets.all(8 * k),
                decoration: BoxDecoration(
                  color: AlmaPalette.inkLight,
                  borderRadius: BorderRadius.circular(12 * k),
                  border: Border.all(
                      color: AlmaPalette.gold.withValues(alpha: 0.4)),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.6),
                      blurRadius: 55 * k,
                      offset: Offset(0, 20 * k),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(6 * k),
                  child: Image.asset(image, fit: BoxFit.cover),
                ),
              ),
              // Штрих и звёзды — поверх картины: рама принадлежит карте, а не
              // тому, что на ней нарисовано.
              IgnorePointer(
                child: Padding(
                  padding: EdgeInsets.all(5 * k),
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(8 * k),
                      border: Border.all(
                          color: AlmaPalette.goldDeep.withValues(alpha: 0.45)),
                    ),
                  ),
                ),
              ),
              if (stars)
                for (final corner in const [
                  Alignment.topLeft,
                  Alignment.topRight,
                  Alignment.bottomLeft,
                  Alignment.bottomRight,
                ])
                  Align(
                    alignment: corner,
                    child: Padding(
                      padding: EdgeInsets.all(3 * k),
                      // Звезда в `s42` — 16 точек на раме шириной 224, то есть
                      // 7.1% ширины. Держим долю, а не число: на раме 170 звезда
                      // в 16 точек стала бы кляксой в углу.
                      child: CustomPaint(
                        size: Size.square(w * 0.071),
                        painter: const _CornerStar(),
                      ),
                    ),
                  ),
              if (plate != null)
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: -16 * k,
                  child: Center(child: _NamePlate(label: plate!, k: k)),
                ),
            ]),
          ),
        ),
      );
    });
  }
}

/// Табличка под картиной — из `s42`, где ею подписана аркана.
///
/// Числа эталона: подложка `#04060E`, золотая обводка `rgba(201,174,107,.7)`,
/// скругление 6, поле 8×22, засечный 15; вокруг — кант в три точки цвета ночи и
/// ещё волос золота на 35%, то есть табличка вырезана из неба и обведена
/// дважды. Подпись **не внутри** картины, как в `s43`: там арт светлый снизу, а
/// наши ворота там темнее всего, и чернильная строка на них не читалась бы.
class _NamePlate extends StatelessWidget {
  const _NamePlate({required this.label, required this.k});

  final String label;
  final double k;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(3 * k),
      decoration: BoxDecoration(
        color: AlmaPalette.voidDark,
        borderRadius: BorderRadius.circular(9 * k),
        border:
            Border.all(color: AlmaPalette.gold.withValues(alpha: 0.35)),
      ),
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 22 * k, vertical: 8 * k),
        decoration: BoxDecoration(
          color: AlmaPalette.voidDark,
          borderRadius: BorderRadius.circular(6 * k),
          border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.7)),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AlmaType.headingM.copyWith(fontSize: 15 * k, height: 1.2),
        ),
      ),
    );
  }
}

/// Четырёхлучевая звезда угла рамы. Путь из `s42`, приведённый к квадрату 16.
class _CornerStar extends CustomPainter {
  const _CornerStar();

  @override
  void paint(Canvas canvas, Size size) {
    final k = size.width / 16;
    const points = [
      Offset(8, 0),
      Offset(9.6, 6.4),
      Offset(16, 8),
      Offset(9.6, 9.6),
      Offset(8, 16),
      Offset(6.4, 9.6),
      Offset(0, 8),
      Offset(6.4, 6.4),
    ];
    final path = Path()..moveTo(points.first.dx * k, points.first.dy * k);
    for (final p in points.skip(1)) {
      path.lineTo(p.dx * k, p.dy * k);
    }
    path.close();
    canvas.drawPath(path, Paint()..color = const Color(0xFFB3913F));
  }

  @override
  bool shouldRepaint(_CornerStar oldDelegate) => false;
}

/// Медленное всплытие карты. `floatY` эталона — 7 секунд туда-обратно; ход в
/// шесть точек, потому что заметное движение на витрине отвлекает от цены.
///
/// При системном «меньше движения» карта неподвижна — то же правило, что у
/// `Breathing` и `RiseIn`.
class _Floating extends StatefulWidget {
  const _Floating({required this.child});

  final Widget child;

  @override
  State<_Floating> createState() => _FloatingState();
}

class _FloatingState extends State<_Floating>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 7000),
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      if (!still) _controller.repeat(reverse: true);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _controller,
        builder: (context, child) => Transform.translate(
          offset: Offset(
              0, -6 * Curves.easeInOut.transform(_controller.value)),
          child: child,
        ),
        child: widget.child,
      );
}

/// Пилюля цены — она же второй указатель выбора.
///
/// Числа `s43`, где стоят ровно две такие пилюли: выбранная — заливка
/// `#F6F1E4`, число `600 17px` чернилами `#1C1A17`, тень
/// `0 8px 22px rgba(0,0,0,.4)`; невыбранная — та же форма обводкой
/// `rgba(201,174,107,.4)` и число слоновой костью. Скругление 999 у обеих.
///
/// Поле по горизонтали 16 — своё: в эталоне пилюля тянется на половину экрана
/// (`flex:1`) и её поле задано только по вертикали, а здесь она обнимает число
/// в углу ступени.
///
/// **Это не золотая кнопка и не может ею стать.** Дизайн-система запрещает
/// плоское золото с тёмной подписью (`gold_texture.dart`), и здесь его нет:
/// заливка — светлая бумага, а не золотой градиент. Пилюля к тому же не глагол
/// и вдвое ниже кнопки — спутать её с «купить» не с чем.
class _PricePill extends StatelessWidget {
  const _PricePill({required this.price, required this.selected});

  final String price;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: AlmaMotion.ui,
      curve: AlmaMotion.uiCurve,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
      decoration: BoxDecoration(
        color: selected ? AlmaPalette.inkLight : Colors.transparent,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: selected
              ? Colors.transparent
              : AlmaPalette.gold.withValues(alpha: 0.4),
        ),
        boxShadow: selected
            ? [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.4),
                  blurRadius: 22,
                  offset: const Offset(0, 8),
                ),
              ]
            : null,
      ),
      child: Text(
        price,
        maxLines: 1,
        style: AlmaType.button.copyWith(
          fontSize: 17,
          color: selected ? AlmaPalette.ink : AlmaPalette.inkLight,
        ),
      ),
    );
  }
}

/// Тёплое свечение под золотой кнопкой.
///
/// Из `s42`/`s43`: пятно света в нижней половине кнопки, размытое и медленно
/// дышащее. Кнопка остаётся ровно той же `AlmaButton` — свечение стоит **за**
/// ней и не участвует в нажатии.
class _Glowing extends StatelessWidget {
  const _Glowing({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: [
        Positioned(
          // Пятно лежит по низу кнопки и **шире её тени наружу**: в эталоне
          // оно спрятано за самой кнопкой целиком и на кадре не читается вовсе.
          // Здесь размытие вынесено за края — светится ночь под ключом, а не
          // сам ключ, и это ровно то, что видно на `s42`.
          left: 44,
          right: 44,
          bottom: 0,
          height: 22,
          child: IgnorePointer(
            child: Breathing(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(11),
                  boxShadow: [
                    BoxShadow(
                      // Тот же тёплый тон, что у канта кнопки, — свет и металл
                      // обязаны быть одного огня.
                      color: GoldTexture.edge.withValues(alpha: 0.5),
                      blurRadius: 28,
                      spreadRadius: 4,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
        child,
      ],
    );
  }
}

extension _FirstOrNull<T> on List<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
