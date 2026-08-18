import 'package:flutter/material.dart';

import '../billing/alma_store.dart';
import '../billing/ladder.dart';
import '../design/art.dart';
import '../design/buttons.dart';
import '../design/invitation_pill.dart' show AlmaStarMark, pillEmblemHeroTag;
import '../design/metrics.dart';
import '../design/palette.dart';
import '../design/typography.dart';
import '../l10n/alma_l10n.dart';
import '../billing/store_words.dart';
import 'paywall/paywall_router.dart';

/// Чем кончился шит «Вся Alma».
enum AllAlmaExit {
  /// Нажата золотая кнопка: человек идёт к лестнице планов.
  plans('cta'),

  /// Нажато «Не сейчас» — единственный ответ, который что-то запоминает.
  notNow('not_now'),

  /// Смах вниз.
  swipe('swipe'),

  /// Тап по скриму.
  scrim('scrim');

  const AllAlmaExit(this.wire);

  final String wire;
}

/// Открыть планы v3 (V8).
///
/// Вела на старую лестницу (`OfferScreen`, s8) прямым `Navigator.push` — мимо
/// роутера пейволлов и мимо сторожа §5, то есть в приложении жили две системы
/// монетизации разом. VR приговорил лестницу; пилюля осталась по слову
/// владельца («оставляй»), но ведёт теперь на витрину v3 тем же путём, каким
/// туда попадают все: `showPaywall` считает показ, шлёт воронку и подчиняется
/// сторожу. `proactive: false` — человек сам нажал пилюлю и сам нажал
/// золотую кнопку шита; проактивным был показ пилюли, и его считает она.
Future<void> openAlmaPlans(BuildContext context) => showPaywall(
      context,
      const PaywallIntent.plans(),
      trigger: 'all_alma_pill',
    );

/// Шит «Вся Alma» — то, во что превращается пилюля.
///
/// **Почему это `PageRoute`, а не `showModalBottomSheet`.** Звезда обязана
/// перелететь из пилюли в гнездо шита общим элементом, а `Hero` летает только
/// между `PageRoute`: `HeroController._maybeStartHeroTransition` выходит из
/// себя первой же строкой, если хоть одна из двух сторон не `PageRoute`, а
/// `ModalBottomSheetRoute` — `PopupRoute`. С листом Material перелёта не было
/// бы вовсе, и пришлось бы гонять звезду руками через `OverlayEntry`, угадывая
/// её место в ещё не разложенном шите.
///
/// Отсюда же и точность чисел: скрим доходит до 55% за 240 мс, шит поднимается
/// за 380, и ровно 380 длится перелёт — потому что `Hero` берёт длительность у
/// маршрута, а не у себя. С чужой длительностью звезда приезжала бы раньше
/// гнезда.
///
/// **`opaque: false` — не косметика.** Под шитом всегда «Сегодня» или система,
/// и экран не перезагружается ни при открытии, ни при закрытии: непрозрачный
/// маршрут увёл бы страницу под ним со сцены, а вместе с ней — пилюлю, из
/// которой звезда как раз вылетает.
class AllAlmaSheetRoute extends PageRoute<AllAlmaExit> {
  AllAlmaSheetRoute() : super(barrierDismissible: true);

  @override
  bool get opaque => false;

  @override
  bool get maintainState => true;

  @override
  Color get barrierColor => const Color(0x8C000000); // 55%

  @override
  String get barrierLabel =>
      MaterialLocalizations.of(navigator!.context).modalBarrierDismissLabel;

  /// Скрим набирает свои 55% за 240 мс из 380 — то есть заканчивает темнеть
  /// раньше, чем шит доезжает. Так и читается: сначала гаснет комната, потом
  /// приходит лист, а не наоборот.
  @override
  Curve get barrierCurve => const Interval(0, 240 / 380, curve: Curves.easeOut);

  @override
  Duration get transitionDuration => const Duration(milliseconds: 380);

  @override
  Duration get reverseTransitionDuration => const Duration(milliseconds: 260);

  @override
  Widget buildPage(BuildContext context, Animation<double> animation,
          Animation<double> secondaryAnimation) =>
      const _AllAlmaSheet();

  @override
  Widget buildTransitions(BuildContext context, Animation<double> animation,
      Animation<double> secondaryAnimation, Widget child) {
    final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    if (still) return FadeTransition(opacity: animation, child: child);
    return SlideTransition(
      position: Tween<Offset>(begin: const Offset(0, 1), end: Offset.zero)
          .animate(CurvedAnimation(
        parent: animation,
        curve: AlmaMotion.sheetCurve,
        reverseCurve: AlmaMotion.sheetCurve.flipped,
      )),
      child: child,
    );
  }
}

class _AllAlmaSheet extends StatefulWidget {
  const _AllAlmaSheet();

  @override
  State<_AllAlmaSheet> createState() => _AllAlmaSheetState();
}

class _AllAlmaSheetState extends State<_AllAlmaSheet> {
  final AlmaStore _store = AlmaStore.shared;

  /// Сколько уже утянули вниз в текущем смахе.
  double _pulled = 0;

  @override
  void initState() {
    super.initState();
    _store.addListener(_priced);
    // Магазин мог ещё не отвечать: витрину на этом запуске могли не открывать.
    // Отказ проглатывается намеренно — молчащий App Store это состояние кнопки
    // («Посмотреть планы» без цены), а не повод уронить шит.
    if (_store.state != StoreState.ready) {
      _store.load().catchError((Object _) {});
    }
  }

  @override
  void dispose() {
    _store.removeListener(_priced);
    super.dispose();
  }

  void _priced() {
    if (mounted) setState(() {});
  }

  /// Цена самой дешёвой двери в планы — **только из каталога магазина**.
  ///
  /// `null` значит, что App Store молчит (так выглядит симулятор без
  /// конфигурации StoreKit), и тогда кнопка называется просто «Посмотреть
  /// планы»: единственное, что здесь нельзя выдумывать, — это число.
  String? get _from =>
      _store.cheapestOf(LadderKey.values.where((key) => key.isSubscription));

  void _close(AllAlmaExit exit) {
    if (!mounted) return;
    Navigator.of(context).pop(exit);
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final price = _from;
    final bottom = MediaQuery.viewPaddingOf(context).bottom;

    return Align(
      alignment: Alignment.bottomCenter,
      child: GestureDetector(
        // Смах вниз — «спасибо, не надо». Расстояние, а не скорость на
        // отпускании: медленно поднятый палец Flutter броском не считает, и
        // шит не отвечал бы на самый обычный способ его закрыть — ровно та же
        // находка, что записана в `TabsPeek.pull`.
        onVerticalDragStart: (_) => _pulled = 0,
        onVerticalDragUpdate: (details) {
          _pulled += details.primaryDelta ?? 0;
          if (_pulled > 64) _close(AllAlmaExit.swipe);
        },
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: AlmaPalette.night,
            borderRadius:
                const BorderRadius.vertical(top: Radius.circular(22)),
            border: Border(
              top: BorderSide(color: AlmaPalette.gold.withValues(alpha: 0.3)),
            ),
          ),
          // **Material внутри, а не снаружи.**
          //
          // Без него Flutter рисует каждую строку жёлтой с двойным
          // подчёркиванием: у текста нет ни темы, ни поверхности, и он честно
          // сообщает об этом самым заметным способом. На вкладках эту опору
          // держит `Scaffold` кабинета, а маршрут поверх него её не наследует
          // — ровно та же находка, что записана в `offer_screen.dart`.
          // Прозрачный: цвет, скругление и кант рисует коробка выше.
          child: Material(
            type: MaterialType.transparency,
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                  AlmaMetrics.pad, 10, AlmaMetrics.pad, bottom + 18),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Center(child: _Grabber()),
                  const SizedBox(height: 16),
                  // Гнездо звезды: сюда она прилетает из пилюли. По центру и
                  // над баннером — там, где взгляд уже стоит после морфа.
                  const Center(
                    child: Hero(
                      tag: pillEmblemHeroTag,
                      child: _BreathingStar(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(14),
                    child: Image.asset(
                      AlmaArt.fan,
                      height: 128,
                      width: double.infinity,
                      fit: BoxFit.cover,
                    ),
                  ),
                  const SizedBox(height: 18),
                  Text(l.cabAllAlmaPill.toLowerCase(),
                      style: AlmaType.overline),
                  const SizedBox(height: 6),
                  Text(l.cabPlansTitle,
                      style: AlmaType.displayL.copyWith(fontSize: 26)),
                  const SizedBox(height: 10),
                  Text(l.pillSheetSub, style: AlmaType.body),
                  const SizedBox(height: 14),
                  // **Факты те же, что на лестнице.** Своих строк у шита здесь
                  // нет намеренно: две почти одинаковые тройки обещаний в
                  // каталоге через месяц разойдутся, и человек прочтёт разное
                  // об одном и том же на двух экранах подряд.
                  _Fact(l.paywallPitchPlan1),
                  _Fact(l.paywallPitchPlan2),
                  _Fact(l.paywallPitchPlan3),
                  const SizedBox(height: 20),
                  AlmaButton(
                    label: price == null
                        ? l.cabPlansCta
                        : l.pillSheetCta(price),
                    shortLabel: l.cabPlansCta,
                    onTap: () => _close(AllAlmaExit.plans),
                  ),
                  const SizedBox(height: 4),
                  Center(
                    child: GestureDetector(
                      onTap: () => _close(AllAlmaExit.notNow),
                      behavior: HitTestBehavior.opaque,
                      child: SizedBox(
                        // Не меньше 44 — иначе в неё не попасть пальцем.
                        height: 44,
                        child: Center(
                          widthFactor: 1,
                          child: Padding(
                            padding:
                                const EdgeInsets.symmetric(horizontal: 20),
                            child: Text(
                              l.paywallNotNow,
                              style: AlmaType.body.copyWith(
                                fontSize: 15,
                                color: AlmaPalette.muted2,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Center(
                    child: Text(
                      l.storeSheetFootnote,
                      textAlign: TextAlign.center,
                      style: AlmaType.meta
                          .copyWith(color: AlmaPalette.muted3, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Grabber extends StatelessWidget {
  const _Grabber();

  @override
  Widget build(BuildContext context) => Container(
        width: 36,
        height: 4,
        decoration: BoxDecoration(
          color: AlmaPalette.body.withValues(alpha: 0.28),
          borderRadius: BorderRadius.circular(2),
        ),
      );
}

/// Звезда, которая дышит: 1 → 1.06 за пять секунд туда и обратно.
///
/// Дыхание живёт **внутри** `Hero`, а не поверх него: снаружи оно меняло бы
/// размер коробки, из которой `Hero` берёт место назначения, и звезда целилась
/// бы в точку, которая к концу перелёта уже уехала.
class _BreathingStar extends StatefulWidget {
  const _BreathingStar();

  @override
  State<_BreathingStar> createState() => _BreathingStarState();
}

class _BreathingStarState extends State<_BreathingStar>
    with SingleTickerProviderStateMixin {
  late final AnimationController _breath = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 5000),
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final still = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
      if (!still) _breath.repeat(reverse: true);
    });
  }

  @override
  void dispose() {
    _breath.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _breath,
        builder: (context, child) => Transform.scale(
          scale: 1 + Curves.easeInOut.transform(_breath.value) * 0.06,
          child: child,
        ),
        child: const AlmaStarMark(size: 34),
      );
}

/// Строка факта: точка, отступ, проверяемое утверждение. Тот же приём, что на
/// лестнице, — там он называется `_Dotted`.
class _Fact extends StatelessWidget {
  const _Fact(this.line);

  final String line;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 7),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('·', style: AlmaType.numeral),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                line,
                style: AlmaType.body.copyWith(fontSize: 15, height: 1.5),
              ),
            ),
          ],
        ),
      );
}
