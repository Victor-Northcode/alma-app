import 'package:flutter/material.dart';
import 'package:intl/intl.dart' show DateFormat;
import 'package:shared_preferences/shared_preferences.dart';

import '../../billing/ladder.dart';
import '../../design/art.dart';
import '../../design/buttons.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../../state/session.dart';
import '../../state/reading_tally.dart';
import 'paywall_parts.dart';
import 'paywall_router.dart';
import 'paywall_shell.dart';

/// Предложить забрать разбор — если есть что забирать и если ещё не предлагали.
///
/// **Один раз за жизнь подписки.** Приёмочный сценарий ТЗ говорит это прямо:
/// повторный вход в отмену save-оффера не показывает. Признак привязан не к
/// установке, а к самой подписке (`granted_at` активного права): человек,
/// подписавшийся заново через полгода, — это новая жизнь подписки и новый
/// повод, а тот же самый человек, вошедший в отмену второй раз за вечер, уже
/// всё это читал, и второй показ был бы удержанием.
///
/// **Спасать нечего — не показываем вовсе.** Если все двери уже куплены или
/// куплен бандл, оффер предлагал бы купить купленное; если ни одной главы не
/// читали, «твоя самая читаемая» была бы неправдой в единственном месте, где
/// весь экран держится на правде. В обоих случаях [PaywallOutcome.blocked], и
/// вызывающий идёт прямо в настройки магазина.
Future<PaywallOutcome> offerToSave(BuildContext context) async {
  final session = SessionScope.of(context);
  final lifetime = _subscriptionLifetime(session);
  final prefs = await SharedPreferences.getInstance();
  if (prefs.getString(_shownKey) == lifetime) return PaywallOutcome.blocked;

  // Забрать можно только то, что подписка открывает временно: систему с
  // дверью, которой ещё не владеют навсегда.
  final owned = _ownedForever(session);
  final candidates = [
    for (final key in LadderKey.values)
      if (key.system != null && !owned.contains(key.system!.slug)) key.system!,
  ];
  final system = await ReadingTally.mostRead(candidates);
  if (system == null) return PaywallOutcome.blocked;
  final opens = await ReadingTally.opens(system);
  // Признак ставится до показа: экран, показанный и закрытый жестом в ту же
  // секунду, показан — «один раз за жизнь подписки» считает показы, а не
  // прочтения.
  await prefs.setString(_shownKey, lifetime);
  if (!context.mounted) return PaywallOutcome.blocked;
  return showPaywall(
    context,
    PaywallIntent.cancelSave(system),
    trigger: 'cancel_flow',
    opens: opens,
  );
}

const _shownKey = 'paywall.cancelSave.shown';

/// Чем эта жизнь подписки отличается от прошлой. Пусто — сервер не сказал;
/// тогда признак общий, и это честнее, чем показать оффер дважды.
String _subscriptionLifetime(AlmaSession session) {
  for (final row in session.entitlements.rows) {
    if (row['active'] == true && row['kind'] == 'monthly') {
      return (row['granted_at'] as String?) ?? 'active';
    }
  }
  return 'none';
}

/// Слаги систем, купленных навсегда: дверью или бандлом.
Set<String> _ownedForever(AlmaSession session) {
  if (session.entitlements.ownsArchive) {
    return {for (final key in LadderKey.values) ?key.system?.slug};
  }
  return {
    for (final row in session.entitlements.rows)
      if (row['active'] == true && row['kind'] == 'one_time')
        ?(row['system'] as String?),
  };
}

/// V9 · спасение от отмены: «Забери свой разбор с собой».
///
/// Поверхность **P8**. Показывается по тапу «Управлять подпиской» — **до**
/// редиректа в системные настройки магазина — и **один раз за жизнь
/// подписки**. Оба условия держит вызывающий (`settings_screen.dart`): экран,
/// решающий сам, показываться ли ему, однажды покажется дважды.
///
/// ## Две кнопки одинаковой силы — намеренно
///
/// Это единственное законное исключение из правила «одна золотая кнопка на
/// экране», и разница между ними ровно четыре точки высоты и заливка: 56
/// золотая против 52 контурной. Этого хватает, чтобы читалась иерархия, и мало,
/// чтобы читался тёмный паттерн. **«Просто отменить» не прячется, не
/// задерживается, не серая и не мелкая.** Если следующий читающий соберётся
/// «чуть-чуть приглушить» вторую кнопку — так и было задумано: это спасение, а
/// не воронка. Ни «точно уверены?», ни скидки, ни третьего экрана здесь нет и
/// быть не может.
///
/// ## Чего здесь нет
///
/// Слова «продление» — продаётся дверь, разовая и навсегда. Второй цены.
/// Удержания вроде «останься, дадим скидку»: скидок в каталоге нет, и v3 их не
/// заводит.
class CancelSaveScreen extends StatefulWidget {
  const CancelSaveScreen({
    super.key,
    required this.system,
    this.chapters,
    this.opens,
  });

  /// Что предлагаем забрать: самая читаемая система, у которой есть дверь.
  final SystemSlug system;

  /// Сколько в ней глав. `null` — оглавление ещё не приехало.
  final int? chapters;

  /// Сколько раз её открывали. `null` или 0 — статистики нет, и тогда фраза
  /// идёт без факта: выдуманное число здесь хуже отсутствующего, потому что
  /// весь экран держится на том, что факт настоящий.
  final int? opens;

  @override
  State<CancelSaveScreen> createState() => _CancelSaveScreenState();
}

class _CancelSaveScreenState extends State<CancelSaveScreen> {
  int? _chapters;
  bool _announced = false;

  @override
  void initState() {
    super.initState();
    _chapters = widget.chapters;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_announced) return;
    _announced = true;
    final session = SessionScope.of(context);
    // Поверхность обязательна, товар — по факту: у системы без двери его нет,
    // и подставлять сюда натал «чтобы поле было» значит испортить отчёт ровно
    // тем случаем, ради которого его читают.
    session.client.track(FunnelStage.saveOfferShown,
        meta: {'surface': 'p8', if (_door != null) 'sku': _door!.slug});
    if (_chapters == null) _loadChapters(session);
  }

  LadderKey? get _door => LadderKey.doorFor(widget.system);

  /// Число глав — из оглавления, а не из головы.
  ///
  /// Сначала из памяти запросчика: в «Мои системы» заходили, и список этой
  /// системы почти наверняка уже привозили. Не привозили — тихий запрос, и до
  /// его ответа фраза стоит без числа, а не с многоточием.
  Future<void> _loadChapters(AlmaSession session) async {
    final known =
        session.client.knownChapters(widget.system, locale: session.locale);
    if (known != null) {
      setState(() => _chapters = known.chapters.length);
      return;
    }
    try {
      final list =
          await session.client.chapters(widget.system, locale: session.locale);
      if (mounted) setState(() => _chapters = list.chapters.length);
    } on AlmaError {
      // Молча: экран умеет обойтись без числа.
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final name = LadderKey.systemTitle(l, widget.system);
    return PaywallShell(
      intent: PaywallIntent.cancelSave(widget.system),
      seed: 0x0D005609,
      builder: (context, deal) {
        final key = deal.first;
        final price = key == null ? null : deal.price(key);
        final chapters = _chapters;
        final opens = widget.opens ?? 0;
        return Column(children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(
                  AlmaMetrics.pad, 12, AlmaMetrics.pad, 12),
              child: Column(children: [
                PaywallHeader(
                  overline: l.paywallV3CancelHeader,
                  centred: true,
                  leading: PaywallBack(onTap: () => deal.close('back')),
                  onClose: () => deal.close('back'),
                ),
                const SizedBox(height: 30),
                LayoutBuilder(builder: (context, box) {
                  // 184 из 402 — доля кадра; на узком экране карта ужимается
                  // вместе с ним, а не вылезает за поле.
                  final width = (box.maxWidth * 184 / 358).clamp(120.0, 184.0);
                  return Center(
                    child: PaywallPlate(
                      image: AssetImage(AlmaArt.card(widget.system)),
                      width: width,
                      height: width * 250 / 184,
                      radius: 13,
                      edge: 1.5,
                      edgeColor:
                          AlmaPalette.goldBright.withValues(alpha: 0.55),
                      innerAlpha: 0.28,
                      scrimStart: 0.4,
                      scrimTo: 0.88,
                      alignment: Alignment.center,
                      shadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.6),
                          blurRadius: 56,
                          offset: const Offset(0, 22),
                        ),
                      ],
                      captionInset: 12,
                      captionBottom: 12,
                      caption: Column(children: [
                        Text(name,
                            textAlign: TextAlign.center,
                            style: AlmaType.headingM.copyWith(fontSize: 17)),
                        const SizedBox(height: 3),
                        Text(
                          l.paywallV3CancelCardCaption,
                          textAlign: TextAlign.center,
                          style: AlmaType.meta.copyWith(
                              fontSize: 11.5, color: AlmaPalette.gold),
                        ),
                      ]),
                    ),
                  );
                }),
                const SizedBox(height: 24),
                Text(
                  l.paywallV3CancelSaveTitle,
                  textAlign: TextAlign.center,
                  style:
                      AlmaType.displayL.copyWith(fontSize: 27, height: 1.16),
                ),
                // Абзац живёт вокруг цены — она стоит внутри предложения, — и
                // без цены его не бывает вовсе. Молчащий магазин виден ниже,
                // на месте кнопки; фраза с дырой вместо числа читалась бы
                // сломанной ровно там, где человек решает про деньги.
                if (price != null) ...[
                  const SizedBox(height: 14),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Text(
                      // Факт и цена стоят в одной фразе, и разрывать её нельзя:
                      // в половине локалей развалится согласование.
                      chapters == null || opens == 0
                          ? l.paywallV3CancelSaveFactPlain(price)
                          : l.paywallV3CancelSaveFact(chapters, opens, price),
                      textAlign: TextAlign.center,
                      style: AlmaType.body.copyWith(
                        fontSize: 14,
                        height: 1.6,
                        color: AlmaPalette.body.withValues(alpha: 0.78),
                      ),
                    ),
                  ),
                ],
              ]),
            ),
          ),
          PaywallBottom(
            bottom: 30,
            children: [
              if (deal.loading)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 17),
                  child: Text(l.stateLoadingShort, style: AlmaType.meta),
                )
              else
                PaywallCta(
                  label: price == null || key == null
                      ? null
                      : l.paywallV3CancelSaveCta(price),
                  store: deal.store,
                  onTap: () {
                    if (key != null) deal.buy(key);
                  },
                ),
              PaywallNotice(store: deal.store),
              const SizedBox(height: 11),
              // Вторая кнопка той же визуальной силы. 52 против 56 и контур
              // против золота — вся разница; подпись Golos 600 15.5 светлым
              // золотом, а не серым, и никакого «ты уверена».
              AlmaButton(
                kind: AlmaButtonKind.outline,
                height: 52,
                radius: 26,
                label: l.paywallV3CancelJustCancel,
                onTap: deal.busy
                    ? null
                    : () => deal.close('just_cancel',
                        outcome: PaywallOutcome.justCancel),
              ),
              const SizedBox(height: 10),
              Builder(builder: (context) {
                final until = _until(context, l);
                return Text(
                  // TODO(stores): и здесь Apple ID вшит — на холсте варианта
                  // для Play нет (спека, дыра №7).
                  until == null
                      ? l.paywallV3CancelNoteNoDate
                      : l.paywallV3CancelNote(until),
                  textAlign: TextAlign.center,
                  style: AlmaType.meta.copyWith(
                    fontSize: 11.5,
                    height: 1.45,
                    color: AlmaPalette.body.withValues(alpha: 0.55),
                  ),
                );
              }),
            ],
          ),
        ]);
      },
    );
  }

  /// До какого числа подписка ещё работает — из прав, а не из календаря.
  ///
  /// `null` — сервер даты не прислал; тогда фраза идёт без неё. Экран, который
  /// в этом месте покажет пустое место или «null», — это экран, на котором
  /// человек решает, доверять ли нам деньги.
  String? _until(BuildContext context, L l) {
    final session = SessionScope.of(context);
    for (final row in session.entitlements.rows) {
      if (row['active'] == true && row['kind'] == 'monthly') {
        final raw = row['expires_at'] as String?;
        if (raw == null) return null;
        final moment = DateTime.tryParse(raw);
        if (moment == null) return null;
        // Тем же форматом, что в настройках: два способа напечатать одну и ту
        // же дату в одном продукте — это два разных числа на глаз читателя.
        return DateFormat.yMMMMd(l.localeName).format(moment.toLocal());
      }
    }
    return null;
  }
}
