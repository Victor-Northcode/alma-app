import 'dart:math' as math;
import 'dart:ui' show ImageFilter;

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
import '../design/sky/night_sky.dart';
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
///
/// ## Три экрана в одном файле, и они не взаимозаменяемы
///
/// С 16 августа 2026 отсюда рисуются три разные поверхности, и путать их
/// нельзя:
///
/// * **`s46`, дверь чтения** — `system` задана, `journeyStep` не поднят. Тап по
///   закрытой главе. Карта над стеклянной панелью, одна золотая кнопка
///   «Unlock to read · $5.99», тихая ссылка «See the plans» и «не сейчас».
///   Лестницы нет, и это не упущение — см. [PaywallIntent];
/// * **`s37`, витрина под системой** — `system` задана, `journeyStep` поднят.
///   Шаг путешествия сразу после церемонии, **единственный автоматический показ
///   витрины в продукте**;
/// * **`s8`, лестница целиком** — `system` пуста. Открывается из настроек, из
///   листа «Вся Alma» и по ссылке «See the plans» с двери.
///
/// **Почему дверь не должна дорастать до витрины.** До этого дня роль `s46`
/// исполняла витрина `s37` с системой в заголовке, а `ladder.dart` дописывал ей
/// снизу недельную, месячную и годовую ступени — то есть человек, ткнувший в
/// одну закрытую главу, получал полный пейволл из пяти строк с ценами. Довод в
/// пользу такого слияния всегда один («раз уж смотрит на цену — покажем и
/// план»), и он всегда проигрывает: дверь и лестница отвечают на разные
/// вопросы. Дверь — на «сколько стоит вот это»; лестница — на «а что тут
/// вообще есть». Полный разбор записан один раз и в одном месте, в шапке
/// [PaywallIntent] — следующий, кто соберётся слить их обратно «чтобы
/// продавалось лучше», обязан сначала прочесть его.
class OfferScreen extends StatefulWidget {
  const OfferScreen({super.key, this.system, this.journeyStep = false});

  /// За какой дверью пришли. `null` — «Вся Alma», витрина целиком.
  final SystemSlug? system;

  /// Экран показан шагом путешествия, а не тапом по закрытой главе.
  ///
  /// Различает `s37` и `s46` при одной и той же системе. Значение по
  /// умолчанию — дверь: тапом по закрытой главе сюда приходят из главы, из
  /// «Сегодня» и с экрана системы, а шагом путешествия — ровно из одного места,
  /// и пусть о своей особости заявляет оно.
  final bool journeyStep;

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
          // Витрине нужны строки прайса; `manage_url` с той же полки читают
          // настройки — здесь отменять нечего, здесь покупают.
          _shelf = shelf.plans;
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
    return widget.journeyStep
        ? PaywallIntent.showcase(system)
        : PaywallIntent.door(system);
  }

  /// Уйти отсюда. Отдельная ступень воронки, а не просто выход: человек,
  /// закрывший витрину, и человек, ушедший с неё назад, — разные события.
  void _decline(SystemSlug? door) {
    final session = SessionScope.of(context);
    session.client.track(
      FunnelStage.offerDeclined,
      meta: door == null ? null : {'product': door.slug},
    );
    Navigator.of(context).maybePop();
  }

  /// Тихая дверь с двери на лестницу: `s46` → `s8`.
  ///
  /// **Новым маршрутом, а не подменой содержимого.** Лестница — отдельный
  /// экран, и человек, посмотревший планы и передумавший, обязан вернуться к
  /// той самой двери, с которой ушёл, а не оказаться на ней заново с
  /// прокруткой в начале.
  void _openPlans() {
    Navigator.of(context, rootNavigator: true).push(
      CupertinoPageRoute(builder: (context) => const OfferScreen()),
    );
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

    // Дверь рисует себя целиком и каркасом витрины не пользуется: у неё нет ни
    // надзаголовка, ни прокручиваемой колонки — карта стоит на небе, а панель
    // прижата к нижнему краю.
    if (!intent.ladder && door != null) {
      return _ReadingDoor(
        door: door,
        rung: rungs.firstOrNull,
        store: _store,
        loading: _loading,
        onSeePlans: _openPlans,
        onDecline: () => _decline(door),
      );
    }

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
          // **Факты до цены — закон витрины.**
          //
          // Строка «каждый расчёт бесплатен» стояла в самом низу, под кнопкой и
          // под тремя буллетами: человек узнавал, что ему ничего не обязательно
          // покупать, уже перешагнув через все цены. Эталон держит её сразу под
          // подзаголовком, до первой цифры, и это же решение владельца.
          const SizedBox(height: 14),
          const _FreeLine(),
          const SizedBox(height: 14),
          // **Перечня обещаний на лестнице нет.** Три строки с точкой
          // («годовой открывает все восемь», «транзиты обновляются», «30
          // вопросов в месяц») повторяли то, что и так написано подписью под
          // каждым планом, и стоили 160 точек — больше, чем вся юридика с
          // кнопкой вместе. В перечне эталона их нет: шапка → бесплатность →
          // планы → юридика → кнопка → Restore и «не сейчас» → ссылки.
          // На двери (`s37`) перечень остаётся: там продают систему, и сказать
          // о ней больше нечем.
          if (door != null) _Facts(door: true),
          // **Картины здесь нет.** До 16 августа 2026 над лестницей стояли
          // ворота в пергаментной раме. В эталоне `s8` арта нет вообще: он
          // живёт на `s46` (дверь одной системы) и баннером 128 в шите `s32`.
          // Здесь рама съедала пол-экрана и уводила цены за сгиб — «эта
          // картина здесь съедает пол-экрана», решение владельца.
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
                  const SizedBox(height: 14),
                  // **И выход отсюда.** Кнопка «не сейчас» стояла только в
                  // блоке покупки, то есть у купившего всё её не было вовсе —
                  // единственным способом уйти оставался краевой смах iOS. На
                  // шаге путешествия это стало бы тупиком: человек, купивший
                  // прямо на `s37`, застревал перед кабинетом, которого ещё не
                  // видел.
                  Center(
                    child: AlmaButton(
                      kind: AlmaButtonKind.outline,
                      fills: false,
                      label: intent.isDoor ? l.paywallSkip : l.paywallNotNow,
                      onTap: () => _decline(door),
                    ),
                  ),
                ],
              ),
            )
          else ...[
            for (final (i, key) in rungs.indexed)
              _Rung(
                rung: key,
                price: _store.price(key),
                selected: key == chosen,
                first: i == 0,
                onTap: _store.busy != null
                    ? null
                    : () => setState(() => _chosen = key),
              ),
            if (chosen != null)
              _BuyArea(
                chosen: chosen,
                store: _store,
                intent: intent,
                onDecline: () => _decline(door),
              ),
          ],
        ],
      ),
    );
  }
}

/* ── s46: дверь чтения ───────────────────────────────────────────────────── */

/// Дверь: карта на небе и стеклянная панель под ней.
///
/// Порт `s46` — «Reading door — card above, glass panel below». Экран, который
/// человек встречает, ткнув в закрытую главу, и он **не витрина**: одна карта,
/// одно имя, одна золотая кнопка с ценой. Полный довод о том, почему дверь и
/// лестница — разные поверхности, записан в [PaywallIntent]; здесь только то,
/// что из него следует для разметки.
///
/// **Чего на двери нет и почему.**
///
/// * *Лестницы* — её отсекает [ladderFor], а не этот файл: правило обязано жить
///   в одном месте, иначе следующая продающая поверхность заведёт его заново.
/// * *Юридического подвала* — «Условия / Политика / Условия подписки» требует
///   Guideline 3.1.2 от экрана, **продающего подписку**. Дверь продаёт разовую
///   покупку одной системы, подписки на ней нет ни одной, а три ссылки мелким
///   под кнопкой — это ровно тот шум, ради удаления которого дверь и заводили.
///   Ссылка «See the plans» ведёт на `s8`, и подвал стоит там, где подписки
///   действительно продаются.
/// * *Надзаголовка «what it costs»* — он объявляет разговор о деньгах, то есть
///   витрину. Дверь этого разговора не начинает: она называет одну цену.
///
/// **Чего на карте нет.** В эталоне у карты две подписи — надзаголовок
/// «THE NATAL CHART · I» и табличка «The High Priestess». Обе принадлежат
/// **главе**: номер главы и имя её арканы. Дверь главы не знает — она приходит
/// сюда из главы, из «Сегодня» и с экрана системы, и всё, что ей передают, это
/// система. Печатать в оба места имя системы значило бы сказать одно слово
/// трижды, считая заголовок панели; поэтому карта здесь без подписи, а имя
/// системы стоит один раз — крупно, там, где эталон держит заголовок.
class _ReadingDoor extends StatelessWidget {
  const _ReadingDoor({
    required this.door,
    required this.rung,
    required this.store,
    required this.loading,
    required this.onSeePlans,
    required this.onDecline,
  });

  final SystemSlug door;

  /// Ступень, которую эта дверь открывает. `null` — сервер ещё не ответил или
  /// на полке её нет; кнопка тогда не рисуется вовсе.
  final LadderKey? rung;

  final AlmaStore store;
  final bool loading;
  final VoidCallback onSeePlans;
  final VoidCallback onDecline;

  /// Кадр эталона. Все доли ниже считаются от него.
  static const _frameW = 402.0;
  static const _frameH = 874.0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      body: NightSky(
        // Небо двери — читательское: приглушённое поле без кометы. Свет,
        // ходящий поперёк, спорил бы и с картой, и с ценой.
        mood: SkyMood.reading,
        seed: 0x0D004602,
        child: LayoutBuilder(builder: (context, box) {
          final w = box.maxWidth;
          final h = box.maxHeight;
          // Стекло стоит на 54% высоты — `top:472` из 874.
          final panelTop = h * (472 / _frameH);
          final cardTop = h * (104 / _frameH);
          // Ширина карты — 232 из 402, но не настолько, чтобы карта заехала под
          // стекло: на коротком экране (SE) доли высоты и ширины расходятся, и
          // побеждает та, что оставляет карту целой.
          final byWidth = w * (232 / _frameW);
          final byHeight = (panelTop - cardTop - 18) * (232 / 352);
          final cardW = math.min(byWidth, math.max(byHeight, 0.0));

          return Stack(children: [
            // Соседки по колоде, завалившиеся за главную карту. В эталоне это
            // две одинаковые карты; здесь — настоящие соседи системы по колоде:
            // два клона одной картинки слева и справа на живом продукте
            // читаются как сбой загрузки.
            _DeckNeighbour(
              system: SystemSlug.values[(door.index + 7) % 8],
              top: h * (150 / _frameH),
              side: w * (18 / _frameW),
              width: w * (88 / _frameW),
              height: h * (280 / _frameH),
              turn: -7 / 360,
              left: true,
            ),
            _DeckNeighbour(
              system: SystemSlug.values[(door.index + 1) % 8],
              top: h * (150 / _frameH),
              side: w * (18 / _frameW),
              width: w * (88 / _frameW),
              height: h * (280 / _frameH),
              turn: 7 / 360,
              left: false,
            ),
            Positioned(
              left: 0,
              right: 0,
              top: h * (52 / _frameH),
              child: Center(child: _Wand(width: w * (30 / _frameW))),
            ),
            Positioned(
              left: 0,
              right: 0,
              top: cardTop,
              child: Center(
                child: _Floating(child: _DoorCard(system: door, width: cardW)),
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              top: panelTop,
              bottom: 0,
              child: _DoorPanel(
                door: door,
                rung: rung,
                store: store,
                loading: loading,
                onSeePlans: onSeePlans,
                onDecline: onDecline,
              ),
            ),
          ]);
        }),
      ),
    );
  }
}

/// Стеклянная панель двери: имя, обещание и одна кнопка.
///
/// Числа `s46`: верх на 472 из 874, скругление 28 у верхних углов, золотой волос
/// по кромке на 30%, размытие подложки 14, заливка от `rgba(13,17,32,.88)` к
/// `rgba(7,10,22,.97)` на 60% высоты, поле 30.
class _DoorPanel extends StatelessWidget {
  const _DoorPanel({
    required this.door,
    required this.rung,
    required this.store,
    required this.loading,
    required this.onSeePlans,
    required this.onDecline,
  });

  final SystemSlug door;
  final LadderKey? rung;
  final AlmaStore store;
  final bool loading;
  final VoidCallback onSeePlans;
  final VoidCallback onDecline;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final bottom = MediaQuery.paddingOf(context).bottom;
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
              top: BorderSide(color: AlmaPalette.gold.withValues(alpha: 0.3)),
            ),
          ),
          child: Padding(
            padding: EdgeInsets.fromLTRB(30, 26, 30, bottom + 14),
            // **Панель прокручивается целиком, но по умолчанию не двигается.**
            //
            // Двумя частями — прижатым к верху текстом и прибитыми к низу
            // действиями — она была ровно до тех пор, пока магазин отвечал
            // ценой. Стоило ему замолчать (симулятор без конфигурации StoreKit,
            // отвалившаяся сеть, товары до одобрения), как на месте кнопки
            // вырастало объяснение в три строки с «попробовать ещё раз», и
            // обещание наверху обрезалось на полуслове — «never a» без
            // «template». Обрезанная фраза читается сломанным экраном, а не
            // экраном, который можно прокрутить.
            //
            // Рецепт: колонка из двух блоков с `spaceBetween` внутри
            // минимальной высоты во весь просвет. Помещается — имя вверху,
            // кнопка внизу, между ними воздух, как в эталоне; не помещается —
            // колонка перерастает просвет и прокручивается целиком.
            child: LayoutBuilder(builder: (context, box) {
              return SingleChildScrollView(
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: box.maxHeight),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(mainAxisSize: MainAxisSize.min, children: [
                        Text(
                          LadderKey.systemTitle(l, door),
                          textAlign: TextAlign.center,
                          style: AlmaType.displayL
                              .copyWith(fontSize: 30, height: 1.15),
                        ),
                        const SizedBox(height: 14),
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 300),
                          child: Text(
                            l.cabLockedNote,
                            textAlign: TextAlign.center,
                            style: AlmaType.body.copyWith(
                              fontSize: 13.5,
                              height: 1.6,
                              color: AlmaPalette.goldBright,
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ]),
                      // Блок действий уже панели на 10 с каждой стороны —
                      // `left:40` против поля панели 30 в эталоне.
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 10),
                        child: _DoorActions(
                          rung: rung,
                          store: store,
                          loading: loading,
                          onSeePlans: onSeePlans,
                          onDecline: onDecline,
                        ),
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

/// Кнопка двери и всё, что под ней.
///
/// Порядок сверху вниз — от самого громкого к самому тихому, и он же порядок
/// вероятности: купить, прочесть условие покупки, посмотреть планы, уйти,
/// вернуть купленное на новом телефоне.
class _DoorActions extends StatelessWidget {
  const _DoorActions({
    required this.rung,
    required this.store,
    required this.loading,
    required this.onSeePlans,
    required this.onDecline,
  });

  final LadderKey? rung;
  final AlmaStore store;
  final bool loading;
  final VoidCallback onSeePlans;
  final VoidCallback onDecline;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final key = rung;
    final price = key == null ? null : store.price(key);
    final busy = store.busy != null;
    return Column(children: [
      if (loading)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 17),
          child: Text(l.stateLoadingShort, style: AlmaType.meta),
        )
      else if (key == null || price == null) ...[
        // Магазин молчит — цены нет, значит нет и кнопки. Число на двери
        // выдумывать нельзя ни при каких обстоятельствах: цену печатает App
        // Store, и показанная должна совпасть со списанной.
        Text(l.paywallStoreUnavailable,
            textAlign: TextAlign.center, style: AlmaType.meta),
        const SizedBox(height: 14),
        AlmaButton(
          kind: AlmaButtonKind.outline,
          fills: false,
          label: l.stateRetry,
          onTap: store.load,
        ),
      ] else ...[
        _Glowing(
          child: AlmaButton(
            // «Unlock to read · $5.99» — подпись эталона слово в слово.
            label: busy ? l.stateLoadingShort : '${l.cabLocked} · $price',
            onTap: busy || store.restoring ? null : () => store.buy(key),
          ),
        ),
        const SizedBox(height: 10),
        Text(
          l.paywallOneTimeFine,
          textAlign: TextAlign.center,
          style: AlmaType.meta.copyWith(
              fontSize: 12,
              height: 1.5,
              color: AlmaPalette.body.withValues(alpha: 0.5)),
        ),
      ],
      if (store.notice != null)
        Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Text(
            _BuyArea._noticeText(l, store.notice!.message),
            textAlign: TextAlign.center,
            style: AlmaType.meta.copyWith(
              color: switch (store.notice!.tone) {
                StoreTone.good => AlmaPalette.agree,
                StoreTone.waiting => AlmaPalette.gold,
                StoreTone.bad => AlmaPalette.disagree,
              },
            ),
          ),
        ),
      // **Единственная дорога с двери на лестницу — и выход.**
      //
      // «See the plans» тихой ссылкой, а не второй кнопкой: у экрана один
      // акцент, и он золотой. Тот, кто пришёл за одной главой, планы не искал —
      // но тот, кто их ищет, обязан их найти, иначе лестница остаётся в
      // продукте экраном, до которого не дойти.
      //
      // Обе строки в один ряд, как «Restore purchases · Skip for now» на `s37`:
      // в столбик они съедали высоту у заголовка и обещания, и на коротком
      // экране прокручиваться начинало то, ради чего дверь открыли.
      const SizedBox(height: 12),
      Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        Flexible(
          child: _QuietLine(
            label: l.cabPlansCta,
            color: AlmaPalette.goldBright,
            onTap: onSeePlans,
          ),
        ),
        Flexible(
          child: _QuietLine(
            label: l.paywallNotNow,
            color: AlmaPalette.body.withValues(alpha: 0.85),
            onTap: onDecline,
          ),
        ),
      ]),
      // Подвал двери. Восстановление здесь строкой, а не кнопкой: Apple требует
      // его на каждой поверхности, где продают разовые покупки, а человеку оно
      // нужно ровно один раз в жизни — на новом телефоне.
      _QuietLine(
        label: store.restoring ? l.paywallRestoring : l.paywallRestore,
        color: AlmaPalette.body.withValues(alpha: 0.5),
        size: 12.5,
        onTap: store.restoring || store.busy != null ? null : store.restore,
      ),
    ]);
  }
}

/// Тихая строка-ссылка: поле для пальца, никакой рамки.
class _QuietLine extends StatelessWidget {
  const _QuietLine({
    required this.label,
    required this.color,
    required this.onTap,
    this.size = 15,
  });

  final String label;
  final Color color;
  final double size;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Opacity(
          opacity: onTap == null ? 0.5 : 1,
          child: Padding(
            // 12×20 — поле «Not now» в эталоне: строка мелкая, а палец нет.
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 18),
            child: Text(
              label,
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AlmaType.button.copyWith(fontSize: size, color: color),
            ),
          ),
        ),
      );
}

/// Карта двери: пергаментная рама 232×352 из `s46`.
///
/// Родня `_ArtCard`, но не она: там рама витрины 170×240 с табличкой под
/// нижним краем, здесь герой экрана — вдвое крупнее, с полем 10, скруглением 16
/// и звёздами только по верхним углам. Свести их в одну вещь с шестью
/// переключателями значило бы сделать нечитаемыми обе.
class _DoorCard extends StatelessWidget {
  const _DoorCard({required this.system, required this.width});

  final SystemSlug system;
  final double width;

  @override
  Widget build(BuildContext context) {
    final k = width / 232; // всё остальное — доли эталонной ширины
    return SizedBox(
      width: width,
      height: 352 * k,
      child: Stack(fit: StackFit.expand, children: [
        Container(
          padding: EdgeInsets.all(10 * k),
          decoration: BoxDecoration(
            color: AlmaPalette.inkLight,
            borderRadius: BorderRadius.circular(16 * k),
            border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.4)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.7),
                blurRadius: 80 * k,
                offset: Offset(0, 26 * k),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(10 * k),
            child: Image.asset(AlmaArt.card(system), fit: BoxFit.cover),
          ),
        ),
        IgnorePointer(
          child: Padding(
            padding: EdgeInsets.all(6 * k),
            child: DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12 * k),
                border: Border.all(
                    color: AlmaPalette.goldDeep.withValues(alpha: 0.45)),
              ),
            ),
          ),
        ),
        // Звёзды только сверху — так они стоят в `s46`. Внизу у эталона
        // табличка с именем арканы, и четыре угла спорили бы с ней.
        for (final corner in const [Alignment.topLeft, Alignment.topRight])
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
    );
  }
}

/// Карта-соседка: то, что видно за главной слева и справа.
///
/// Затемнена вдвое сильнее рамы и повёрнута на семь градусов — она не предмет
/// разговора, а глубина за ним.
class _DeckNeighbour extends StatelessWidget {
  const _DeckNeighbour({
    required this.system,
    required this.top,
    required this.side,
    required this.width,
    required this.height,
    required this.turn,
    required this.left,
  });

  final SystemSlug system;
  final double top;
  final double side;
  final double width;
  final double height;

  /// Поворот в оборотах, как его считает [Transform.rotate] через `Turns`.
  final double turn;
  final bool left;

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: top,
      left: left ? side : null,
      right: left ? null : side,
      child: Transform.rotate(
        angle: turn * 2 * math.pi,
        child: Container(
          width: width,
          height: height,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.4)),
          ),
          child: ColorFiltered(
            // `linear-gradient(rgba(10,13,28,.35), rgba(10,13,28,.35))` поверх
            // картинки — ровная вуаль цвета ночи, а не градиент.
            colorFilter: ColorFilter.mode(
                AlmaPalette.night.withValues(alpha: 0.35), BlendMode.srcOver),
            child: Image.asset(AlmaArt.card(system), fit: BoxFit.cover),
          ),
        ),
      ),
    );
  }
}

/// Золотой жезл над картой: ромб, точка, ромб. Путь `s46`, 30×44.
class _Wand extends StatelessWidget {
  const _Wand({required this.width});

  final double width;

  @override
  Widget build(BuildContext context) => CustomPaint(
        size: Size(width, width * 44 / 30),
        painter: const _WandPainter(),
      );
}

class _WandPainter extends CustomPainter {
  const _WandPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final k = size.width / 30;
    void lozenge(List<Offset> points, Color color) {
      final path = Path()
        ..moveTo(points.first.dx * k, points.first.dy * k);
      for (final p in points.skip(1)) {
        path.lineTo(p.dx * k, p.dy * k);
      }
      path.close();
      canvas.drawPath(path, Paint()..color = color);
    }

    lozenge(const [
      Offset(15, 0),
      Offset(18, 14),
      Offset(15, 22),
      Offset(12, 14),
    ], AlmaPalette.gold);
    canvas.drawCircle(Offset(15 * k, 27 * k), 2.4 * k,
        Paint()..color = AlmaPalette.goldBright);
    lozenge(const [
      Offset(15, 32),
      Offset(16.6, 38),
      Offset(15, 44),
      Offset(13.4, 38),
    ], AlmaPalette.gold.withValues(alpha: 0.6));
  }

  @override
  bool shouldRepaint(_WandPainter oldDelegate) => false;
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

/// Строка, ради которой витрина остаётся честной: считать бесплатно.
///
/// **Стоит до первой цены, а не под кнопкой.** Человек, который узнаёт, что
/// расчёт всех восьми систем ничего не стоит, уже перешагнув через три цены и
/// золотую кнопку, узнаёт это слишком поздно, чтобы поверить. Эталон держит её
/// сразу под подзаголовком.
///
/// Числа эталона: звезда золотом, подпись Golos 600 14/1.5 цветом `#E4D3A2`.
/// Шестисотое начертание — единственное на экране: строка не кричит размером,
/// она весит в наборе.
class _FreeLine extends StatelessWidget {
  const _FreeLine();

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 1),
          child: Text('\u2726',
              style: AlmaType.numeral.copyWith(fontSize: 13)),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            l.paywallFreeNote,
            style: AlmaType.body.copyWith(
              fontSize: 14,
              height: 1.5,
              fontWeight: FontWeight.w600,
              // Вариативному шрифту вес задаётся осью — иначе он молча
              // останется обычным. См. `typography.dart`.
              fontVariations: const [FontVariation('wght', 600)],
              color: AlmaPalette.goldBright,
            ),
          ),
        ),
      ],
    );
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

/// Ступень: **строка списка**, а не карточка.
///
/// **Рамки сняты по эталону.** До 16 августа 2026 каждая ступень была плашкой
/// со скруглением 18 и обводкой — форма, взятая у `s38`, где эталон выбирает
/// одно из двух. Лестница `s8` устроена иначе: это список, разделённый
/// волосом, и четыре рамки одна под другой раздували экран примерно вдвое —
/// цены уходили за сгиб, а весь экран переставал помещаться в 402×874. Владелец
/// на это: «планы — строки списка, а не карточки».
///
/// Числа эталона: радио-точка 8, заголовок Playfair 400 17.5/1.25, подпись
/// Golos 400 13/1.45 цветом слоновая кость .72, цена справа Playfair 400 14
/// золотом, поле 15 сверху и снизу, между строками волос 1 px
/// `rgba(237,231,218,.1)`.
///
/// **Кружок вернулся, и это не противоречие.** Он уже стоял здесь когда-то и
/// был снят: ряд пустых кружков на голом небе читался анкетой. Но там кружок
/// был единственным указателем выбора у строк **без рамки и без разделителя**;
/// в эталоне он часть списка, и вместе с волосом и золотом заголовка читается
/// выбором, а не полем ввода.
///
/// **Цена — из каталога локали, и только оттуда.** `null` значит, что App Store
/// не ответил: колонка остаётся пустой. Единственное, что здесь нельзя
/// выдумать и нельзя отформатировать самим, — это число: валюта, разделитель и
/// порядок знаков принадлежат магазину той страны, где стоит человек.
class _Rung extends StatelessWidget {
  const _Rung({
    required this.rung,
    required this.price,
    required this.selected,
    required this.first,
    required this.onTap,
  });

  final LadderKey rung;

  /// `null` — магазин не ответил.
  final String? price;
  final bool selected;

  /// Первая строка списка волоса сверху не получает: он разделяет строки, а не
  /// отбивает список от того, что над ним.
  final bool first;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Opacity(
        opacity: onTap == null ? 0.75 : 1,
        child: Container(
          decoration: first
              ? null
              : BoxDecoration(
                  border: Border(top: BorderSide(color: AlmaPalette.hairline)),
                ),
          padding: const EdgeInsets.symmetric(vertical: 15),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Точка стоит на строке заголовка, а не по центру строки: у
              // двухстрочной подписи центр уезжает вниз, и кружок оказывался
              // напротив пустоты.
              Padding(
                padding: const EdgeInsets.only(top: 5),
                child: AnimatedContainer(
                  duration: AlmaMotion.ui,
                  curve: AlmaMotion.uiCurve,
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: selected ? AlmaPalette.gold : Colors.transparent,
                    border: Border.all(
                      color: selected ? AlmaPalette.gold : AlmaPalette.hairline,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      rung.title(l),
                      style: AlmaType.headingM.copyWith(
                        color: selected
                            ? AlmaPalette.goldBright
                            : AlmaPalette.inkLight,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(rung.note(l), style: AlmaType.meta),
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
        //
        // **Один абзац, а не простыня в четыре строки.** Здесь стоял
        // `paywallAutoRenewTerms` кеглем `meta` — три предложения, которые на
        // 375 точках разворачивались в четыре строки и выталкивали кнопку за
        // сгиб. Эталон держит три факта через точку-разделитель и набирает их
        // 12.5/1.5: списывают при подтверждении · продлевается, если не отменить
        // за 24 часа · отменить можно когда угодно.
        if (chosen.isSubscription)
          Padding(
            padding: const EdgeInsets.only(top: 18),
            child: Text(
              l.paywallRenewShort,
              style: AlmaType.meta.copyWith(
                fontSize: 12.5,
                height: 1.5,
                color: AlmaPalette.body.withValues(alpha: 0.78),
              ),
            ),
          ),
        if (price == null) ...[
          // Магазин молчит. Полка выше осталась на месте — что на ней лежит,
          // известно и без App Store, — а купить нельзя, и это сказано.
          // Телом 15.5/1.55, как всё на этом экране, и кнопка обычного роста:
          // офлайн — это состояние, а не отдельный жанр вёрстки.
          const SizedBox(height: 18),
          Text(l.paywallStoreUnavailable, style: AlmaType.body),
          const SizedBox(height: 16),
          Center(
            child: AlmaButton(
              kind: AlmaButtonKind.outline,
              fills: false,
              height: 50,
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
        // **Три буллета сняты с лестницы.** «Разовые покупки не продлеваются ·
        // Apple берёт деньги и присылает чек · отменяют в настройках Apple ID»
        // — это сноска разовой покупки (`s37`, `s43`), и рядом с подпиской она
        // говорила о продлении дважды и противоположными словами. Остаётся там,
        // где продают разовое.
        if (!chosen.isSubscription)
          Padding(
            padding: const EdgeInsets.only(top: 22),
            child: _Dotted(
              lines: [
                l.paywallHonestyOnce,
                l.paywallHonestySeller,
                l.paywallHonestyCancel,
              ],
              style: AlmaType.meta,
            ),
          ),
        // **Restore и «не сейчас» — в одну строку.**
        //
        // Две полноширинные плиты одна под другой занимали 50 + 14 + 54 = 118
        // точек и читались как два равных решения — при том что второе из них
        // «уйти». В эталоне это одна строка по центру: вуаль 48 и обводка 48,
        // одного роста (см. `AlmaButton.height`).
        const SizedBox(height: 18),
        // **`Wrap`, а не `Row`.** Строка из двух кнопок по содержимому на
        // английском занимает около 290 точек из 358 и стоит одной строкой —
        // как в эталоне. Но «Käufe wiederherstellen» рядом с «Jetzt nicht» в
        // 358 не влезает ни при каком кегле, и у `Row` это переполнение с
        // жёлто-чёрной лентой, а у `Flexible` — «Restore purch…». Ни то ни
        // другое не годится: закон эталона — подпись кнопки **не режется
        // никогда**. `Wrap` роняет вторую кнопку на следующую строку и
        // оставляет обе подписи целыми. Найдено тестом на узкой колонке.
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 12,
          runSpacing: 12,
          children: [
            // Apple отклоняет приложение, которое продаёт разовые покупки и не
            // умеет их вернуть. И это же единственное, что помогает человеку с
            // новым телефоном, — случай, который действительно случается.
            // **По содержимому, а не по половинам.** `Flexible` делил строку
            // поровну, и «Restore purchases» — подпись вдвое длиннее «Not
            // now» — выходила «Restore purch…». Ужимать её ступенями кегля
            // здесь нечем: короткого словарного варианта у этой строки нет ни
            // в одном из семи языков, а выдумывать его нельзя. Обе кнопки
            // берут свою ширину и встают по центру.
            _RestoreButton(store: store),
            AlmaButton(
              kind: AlmaButtonKind.outline,
              fills: false,
              height: 48,
              label: intent.isDoor ? l.paywallSkip : l.paywallNotNow,
              onTap: onDecline,
            ),
          ],
        ),
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
      // 48 и радиус 24 — числа эталона, и они же равняют её с «не сейчас»
      // рядом: обе кнопки в одной строке обязаны быть одного роста.
      height: 48,
      radius: 24,
      label: store.restoring ? l.paywallRestoring : l.paywallRestore,
      onTap: store.restoring || store.busy != null ? null : store.restore,
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
