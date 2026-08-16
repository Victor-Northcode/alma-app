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
