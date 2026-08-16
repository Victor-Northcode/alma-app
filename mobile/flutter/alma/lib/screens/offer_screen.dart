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
/// выглядел как настройки. Эталоны `s8`, `s37`, `s42`, `s43` называют три вещи,
/// которых не было ни одной:
///
/// * **кадрированный арт** — витрина открывается картиной, а не абзацем
///   (`_GateBand`, `_DoorCard`);
/// * **пилюли цен** — цена стоит на своей плашке и ею же показывает выбор
///   (`_PricePill`), поэтому кружок-радиокнопка убран: два указателя на один
///   выбор — это не вдвое понятнее;
/// * **парадная дверь** — за одной системой пришли к её собственной карте в
///   пергаментной раме, а не к общей картинке (`_DoorCard`).
///
/// Плюс свечение под золотой кнопкой (`_Glowing`) и филигранная линейка перед
/// ценами (`_Filigree`) — оба из `s42`/`s43`.
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
          // **Картина стоит ровно здесь, а не под заголовком.** В эталоне
          // `s37` арт замерен на y=216 — то есть после вводного абзаца и до
          // перечня: сначала говорят, что продают, потом показывают.
          _Crown(door: door),
          // Что покупают — до всякой цены и до всякой ошибки. Владелец однажды
          // ткнул в закрытую главу на симуляторе без магазина и попал на
          // страницу, всё содержимое которой было «App Store не отвечает».
          _Facts(door: door != null),
          // Филигрань закрывает рассказ и открывает цены — её место в `s43`
          // ровно между картиной и пилюлями (y=506, сразу над ними).
          if (!_loading && rungs.isNotEmpty) const _Filigree(),
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
/// разделены волосяной линией.
///
/// **Выбор показывает пилюля цены, а не кружок.** Кружок-радиокнопка стоял
/// слева от каждой строки и был первым, что владелец назвал вслух: ряд пустых
/// кружков на голом небе читается как анкета, а не как полка. В `s43` выбранный
/// план — пергаментная пилюля с ценой, невыбранный — та же пилюля обводкой; там
/// нет ни одного кружка. Пилюля и есть указатель: она стоит там же, куда и так
/// смотрят, — на цене. Два указателя на один выбор не делают его вдвое яснее,
/// поэтому кружок убран, а не оставлен рядом.
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
                Expanded(
                  // Невыбранная ступень приглушена на шаг — то же, что делает
                  // эталон (`opacity:.85` на невыбранных строках `s8`/`s37`).
                  child: AnimatedOpacity(
                    duration: AlmaMotion.ui,
                    curve: AlmaMotion.uiCurve,
                    opacity: selected ? 1 : 0.85,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(rung.title(l), style: AlmaType.headingM),
                        const SizedBox(height: 4),
                        Text(rung.note(l), style: AlmaType.meta),
                      ],
                    ),
                  ),
                ),
                // Магазин молчит — колонки нет вовсе. Пустая пилюля обещала бы
                // число, которого никто не называл.
                if (price != null) ...[
                  const SizedBox(width: 12),
                  _PricePill(price: price!, selected: selected),
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
/// за всем — стоят ворота: восемь чужих карт по очереди были бы каруселью, а
/// две выбранные («солнечное возвращение» и «астрокартография», как в замерах
/// `s43`) — обещанием именно этих двух из восьми.
class _Crown extends StatelessWidget {
  const _Crown({required this.door});

  /// `null` — витрина целиком.
  final SystemSlug? door;

  @override
  Widget build(BuildContext context) {
    final art = door == null ? const _GateBand() : _DoorCard(system: door!);
    return Padding(
      padding: const EdgeInsets.only(top: 18, bottom: 16),
      child: art,
    );
  }
}

/// Кадрированный арт: золотые ворота полосой.
///
/// Файл — портрет 402×603 (двери целиком, со ступенями). Эталон `s37` берёт из
/// него полосу 356×150, и это не экономия места: полоса на уровне светящегося
/// проёма — это дверь, которая **открывается**, а весь кадр целиком — это
/// фотография закрытой двери. Кадрируем по центру на 62% высоты — там проём,
/// луч и филигрань оклада; выше идут своды, ниже ступени и книги.
class _GateBand extends StatelessWidget {
  const _GateBand();

  static const _radius = 14.0;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(_radius),
      child: AspectRatio(
        aspectRatio: 356 / 150,
        child: Stack(fit: StackFit.expand, children: [
          Image.asset(
            AlmaArt.gates,
            fit: BoxFit.cover,
            // 62% высоты в системе Flutter, где −1 верх, а 1 низ.
            alignment: const Alignment(0, 0.24),
          ),
          // Кант и лёгкая тень по низу: без них кадр читается наклейкой поверх
          // неба, а не окном в него.
          DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(_radius),
              border:
                  Border.all(color: AlmaPalette.gold.withValues(alpha: 0.45)),
              gradient: const LinearGradient(
                begin: Alignment.center,
                end: Alignment.bottomCenter,
                colors: [Color(0x00070A16), Color(0x8C070A16)],
              ),
            ),
          ),
        ]),
      ),
    );
  }
}

/// Парадная дверь: карта системы в пергаментной раме, парящая над ночью.
///
/// Порт `s42` — единственного эталона, прошедшего «charm pass». Числа оттуда,
/// пересчитанные от ширины рамы (в эталоне 224), чтобы рама не разъезжалась на
/// маленьком телефоне: поле 10, скругление 14, внутренний штрих с отступом 6 и
/// скруглением 10, четырёхлучевые звёзды 16 по углам с отступом 3.
///
/// Ширина — 48% колонки, но не больше 190 точек. В эталоне карта занимает 56%
/// ширины экрана, и там она **весь** экран; здесь под ней ещё лестница цен, и
/// герой в 300 точек высотой отправил бы первую цену за нижний край.
class _DoorCard extends StatelessWidget {
  const _DoorCard({required this.system});

  final SystemSlug system;

  /// Пропорция рамы эталона, не картинки: картинка 280×420 садится в неё
  /// `cover` и теряет по краю — рама важнее, её видно.
  static const _frame = 224 / 356;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, box) {
      final w = math.min(box.maxWidth * 0.48, 190.0);
      final k = w / 224; // всё остальное — доли эталонной ширины
      return Center(
        child: _Floating(
          child: SizedBox(
            width: w,
            height: w / _frame,
            child: Stack(fit: StackFit.expand, children: [
              Container(
                padding: EdgeInsets.all(10 * k),
                decoration: BoxDecoration(
                  color: AlmaPalette.inkLight,
                  borderRadius: BorderRadius.circular(14 * k),
                  border: Border.all(
                      color: AlmaPalette.gold.withValues(alpha: 0.4)),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.65),
                      blurRadius: 70 * k,
                      offset: Offset(0, 24 * k),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8 * k),
                  child: Image.asset(AlmaArt.card(system), fit: BoxFit.cover),
                ),
              ),
              // Штрих и звёзды — поверх картины: рама принадлежит карте, а не
              // тому, что на ней нарисовано.
              IgnorePointer(
                child: Padding(
                  padding: EdgeInsets.all(6 * k),
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(10 * k),
                      border: Border.all(
                          color: AlmaPalette.goldDeep.withValues(alpha: 0.45)),
                    ),
                  ),
                ),
              ),
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
                    child: CustomPaint(
                      size: Size.square(16 * k),
                      painter: const _CornerStar(),
                    ),
                  ),
                ),
            ]),
          ),
        ),
      );
    });
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

/// Филигранная линейка между рассказом и ценами.
///
/// Файл — снимок броши на синем бархате, **без альфы**. Маской его не положить,
/// как обещает `art.dart`, поэтому он кадрируется полосой 434×72 (в ней остаётся
/// сама филигрань, бархат уходит вверх и вниз) и гасится ко всем четырём краям.
///
/// **Гасить надо по обеим осям, а не только по горизонтали.** Со сглаженными
/// концами и резаными верхом-низом на небе оставались две тонкие горизонтальные
/// линии — край фотографии, который чуть светлее ночи. Видно это только на
/// снимке экрана рядом с эталоном, но видно каждый раз.
class _Filigree extends StatelessWidget {
  const _Filigree();

  /// Прозрачность по краям, непрозрачность в середине — один и тот же профиль
  /// для обеих осей, разница только в направлении.
  static Shader _fade(Rect rect, Alignment from, Alignment to, double edge) =>
      LinearGradient(
        begin: from,
        end: to,
        colors: const [
          Color(0x00000000),
          Color(0xFF000000),
          Color(0xFF000000),
          Color(0x00000000),
        ],
        stops: [0, edge, 1 - edge, 1],
      ).createShader(rect);

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Padding(
        padding: const EdgeInsets.only(top: 20, bottom: 2),
        child: Opacity(
          opacity: 0.9,
          child: ShaderMask(
            blendMode: BlendMode.dstIn,
            shaderCallback: (rect) =>
                _fade(rect, Alignment.centerLeft, Alignment.centerRight, 0.22),
            child: ShaderMask(
              blendMode: BlendMode.dstIn,
              shaderCallback: (rect) =>
                  _fade(rect, Alignment.topCenter, Alignment.bottomCenter, 0.16),
              child: AspectRatio(
                aspectRatio: 434 / 72,
                child: Image.asset(AlmaArt.divider, fit: BoxFit.cover),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Пилюля цены — она же указатель выбора.
///
/// Из `s43`: выбранное — пергаментная пилюля с чернильным числом, невыбранное —
/// та же форма золотой обводкой и слоновой костью внутри.
///
/// **Это не золотая кнопка и не может ею стать.** Дизайн-система запрещает
/// плоское золото с тёмной подписью (`gold_texture.dart`), и здесь его нет:
/// заливка — пергамент, единственная светлая поверхность продукта, а не
/// золотой градиент. Пилюля к тому же не глагол и вдвое ниже кнопки — спутать
/// её с «купить» не с чем.
class _PricePill extends StatelessWidget {
  const _PricePill({required this.price, required this.selected});

  final String price;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: AlmaMotion.ui,
      curve: AlmaMotion.uiCurve,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: selected ? AlmaPalette.parchment : Colors.transparent,
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
        style: AlmaType.button.copyWith(
          fontSize: 15,
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
