import 'dart:ui' show ImageFilter;

import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../design/buttons.dart';
import '../../design/metrics.dart';
import '../../design/palette.dart';
import '../../design/plates.dart';
import '../../design/sky/night_sky.dart';
import '../../design/typography.dart';
import '../../l10n/alma_l10n.dart';
import '../../net/alma_client.dart';
import '../../net/models.dart';
import '../cabinet_words.dart';
import '../offer_screen.dart';
import 'people_screen.dart';
import 'writing_art.dart';
import '../../state/session.dart';

/// Одна глава, на единственной светлой поверхности продукта.
///
/// Порт `mobile/ios/Alma/Screens/Systems/ChapterScreen.swift`. Пергамент
/// заслужен буквально: лист появляется тогда же, когда глава. Пока Alma пишет,
/// экран остаётся ночью — читать нечего, значит и документа нет.
///
/// **Жест перелистывания — два порога, как на iOS и Android.** На 56 логических
/// точках дотягивания звучит тик и появляется имя следующей главы, на 130
/// страница переворачивается. Подтверждение — расстояние, а не таймер: таймер
/// на живом устройстве вставал ровно на грань схлопывания резинки и срабатывал
/// четыре раза из пяти, а жест, которому нельзя доверять, хуже неработающего.
///
/// Физика прокрутки принудительно упругая ([BouncingScrollPhysics]): дотяжка за
/// конец существует только у неё, и на iOS пороги мерились против такой же
/// задемпфированной резинки. Android-порт в своё время сравнивал те же метки с
/// сырой протяжкой — и то же движение руки листало там и не листало на iOS.
class ChapterScreen extends StatefulWidget {
  const ChapterScreen({super.key, required this.system, required this.chapter});

  final SystemSlug system;
  final String chapter;

  @override
  State<ChapterScreen> createState() => _ChapterScreenState();
}

class _ChapterScreenState extends State<ChapterScreen> {
  static const _nearMark = 56.0;
  static const _commitMark = 130.0;

  /// Зерно неба главы — «CHAP», буква в букву как в `ChapterScreen.swift`.
  ///
  /// **Одно на все сорок одну главу, а не своё у каждой.** Зерно у [NightSky]
  /// различает *экраны*, чтобы переход между ними был видимым переходом; глава
  /// — один экран, и перелистывание внутри него меняет текст, а не место, где
  /// его читают. Небо, пересобранное на каждой протяжке, читалось бы как
  /// подмена экрана посреди жеста, а не как следующая страница.
  static const _skySeed = 0x43484150;

  /// Какая глава показывается. Начинается с запрошенной; протяжка за конец
  /// заменяет её на следующую — **своим состоянием, не навигацией**: на iOS
  /// переход через стек навигации молча съедал анимацию, потому что стек сам
  /// владеет показом, и `transition` не спрашивался.
  late String _showing = widget.chapter;

  Reading? _reading;

  /// Глава пришла как **превью**: сервер написал её по-настоящему, но она
  /// платная, и читателю положен только вкус. Порт этот флаг не читал вовсе —
  /// платные главы показывались целиком и бесплатно.
  bool _preview = false;
  ChapterList? _list;
  AlmaError? _failure;
  bool _loading = true;

  double _pull = 0;
  bool _armed = false;

  /// Второй порог взят и ждёт, когда палец отпустят.
  bool _committed = false;
  bool _advancing = false;

  bool _started = false;

  // См. SystemScreen: SessionScope в initState недоступен.
  @override
  void dispose() {
    // Признак снимается вместе с экраном: бар возвращается к ночному, даже
    // если ушли жестом назад, а не кнопкой.
    readingNow.value = false;
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_started) {
      _started = true;
      _load();
    }
  }

  Future<void> _load() async {
    final session = SessionScope.of(context);
    setState(() {
      _loading = true;
      _failure = null;
      _pull = 0;
      _armed = false;
    });
    try {
      final list = _list ??
          await session.client.chapters(widget.system, locale: session.locale);
      // **Оглавление показывается, как только пришло, а не вместе с текстом.**
      //
      // Список глав — обычный GET и отвечает мгновенно; глава пишется 40–90
      // секунд. Пока оба ждали одного `setState`, `_entry` оставался пустым всю
      // эту минуту, и счётчик печатал запасную единицу: открытая седьмая глава
      // весь показ «Пишу эту главу…» держала в шапке «1 / 16». Снято на
      // симуляторе 13 августа 2026.
      if (mounted && _list == null) setState(() => _list = list);
      final response = await session.client.reading(
        system: widget.system,
        chapter: _showing,
        locale: session.locale,
      );
      if (mounted) {
        // Пергамент появляется вместе с текстом — и бар вместе с ним. Но
        // только если эта глава ещё наверху: пока она писалась, человек мог
        // уйти назад или открыть другую, и поднимать пергамент из-под чужой
        // страницы нельзя.
        final route = ModalRoute.of(context);
        if (route == null || route.isCurrent) readingNow.value = true;
        setState(() {
          _list = list;
          _reading = response.reading;
          _preview = response.preview ?? false;
          _advancing = false;
        });
      }
    } on AlmaError catch (error) {
      if (mounted) setState(() => _failure = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  ChapterEntry? get _entry {
    final list = _list;
    if (list == null) return null;
    for (final entry in list.chapters) {
      if (entry.slug == _showing) return entry;
    }
    return null;
  }

  /// Следующая глава, когда она есть и открыта.
  ChapterEntry? get _next {
    final list = _list;
    final current = _entry;
    if (list == null || current == null) return null;
    for (final entry in list.chapters) {
      if (entry.index == current.index + 1) return entry;
    }
    return null;
  }

  /// [byHand] — палец на стекле, а не инерция.
  ///
  /// **Различие, которое ловит тест, и тот же баг, что жил на телефоне.**
  /// Баллистика упругой прокрутки залетает за край глубже 130 точек, и резкий
  /// смах переворачивал страницу — «слишком легко перелистывается» слово в
  /// слово. На iOS это давил сам UIScrollView: его инерционный залёт мал, и
  /// порога хватало. Во Flutter у уведомления прокрутки есть `dragDetails` —
  /// прямой ответ, рука это или инерция, — поэтому подтверждение здесь
  /// буквально то, чем оно всегда было по замыслу: рука, дотянувшая до метки.
  /// Инерция рисует полосу, но не переворачивает.
  void _onOverscroll(double distance, {required bool byHand}) {
    if (_advancing || _next == null || _loading) return;
    setState(() => _pull = distance);
    if (!byHand) {
      // **Палец ушёл — вот тогда и переворачиваем.**
      //
      // Переворот срабатывал в момент пересечения порога, прямо под рукой:
      // страница уходила посреди движения, и это читалось как «всё сразу
      // пролистывается, если резко листнуть». Упор в том и состоит, что
      // глава держится, пока держат её, а меняется на отпускании.
      if (_committed) {
        _committed = false;
        _advance();
        return;
      }
      if (_armed && distance < _nearMark * 0.7) setState(() => _armed = false);
      return;
    }
    if (distance >= _nearMark && !_armed) {
      setState(() => _armed = true);
      HapticFeedback.selectionClick();
    } else if (distance < _nearMark * 0.7 && _armed) {
      setState(() {
        _armed = false;
        _committed = false;
      });
    }
    // Второй порог взят — тик тяжелее первого, чтобы рука почувствовала упор,
    // и дальше ждём отпускания.
    if (distance >= _commitMark && !_committed) {
      _committed = true;
      HapticFeedback.mediumImpact();
    }
  }

  void _advance() {
    final next = _next;
    if (next == null) return;
    setState(() {
      _advancing = true;
      _showing = next.slug;
      _reading = null;
      _pull = 0;
      _armed = false;
      _committed = false;
    });
    HapticFeedback.heavyImpact();
    _load();
  }

  @override
  Widget build(BuildContext context) {
    // Возврат на вкладку не проходит через загрузку, поэтому признак
    // восстанавливается здесь: пергамент на экране — бар пергаментный.
    //
    // **Но только у той главы, которая сейчас наверху.** Открыв вторую главу,
    // первая остаётся смонтированной под ней в стеке маршрутов и продолжает
    // перестраиваться — и её `build` снова поднимал признак, хотя на экране
    // уже другая страница, ещё пишущаяся и потому ночная. Побеждал тот, кто
    // написал последним, и бар вставал пергаментным поверх ночи: снято на
    // устройстве, экран «глава пишется, 1 / 3».
    final route = ModalRoute.of(context);
    final onTop = route == null || route.isCurrent;
    final onParchment = _reading != null;
    if (onTop && readingNow.value != onParchment) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) readingNow.value = onParchment;
      });
    }
    final l = L.of(context);
    final total = _list?.total ?? widget.system.chapterCount;
    // Индекс сервера уже с единицы: на первой главе натива стоит «1 / 16».
    // Прибавление единицы здесь печатало «2 / 16» на главе I — найдено
    // сравнением с нативным экраном.
    final index = _entry?.index ?? 1;

    return Scaffold(
      backgroundColor: AlmaPalette.night,
      // **Фон — нижний слой стопки, а не украшение на содержимом.**
      //
      // Ночным состояниям главы — ожиданию письма, стене закрытой системы,
      // отказу — полагается то же небо, что «Сегодня» и анкете: на s26 и s29 за
      // содержимым звёзды и туманность. Здесь была ровная заливка ночью, и
      // экран читался плоским рядом с любым соседним. Пергамент неба не
      // показывает — там документ, и звёзды под непрозрачным листом стоили бы
      // только кадров на самом длинном чтении продукта.
      //
      // Слоем, а не обёрткой вокруг содержимого: оборачивание меняло бы
      // глубину поддерева ровно в тот кадр, когда пергамент сменяется ночью, —
      // то есть на перелистывании, — и `AnimatedSwitcher` терял бы свой элемент
      // вместе с начатой анимацией. В стопке второй ребёнок всегда `SafeArea`,
      // и меняется только первый.
      body: Stack(
        fit: StackFit.expand,
        children: [
          if (onParchment)
            const DecoratedBox(
              decoration: BoxDecoration(gradient: AlmaGradient.parchment),
            )
          else
            // Настроение заведено ровно для этого экрана: поле приглушено и
            // кометы нет, потому что продукт здесь — слова, а свет, идущий
            // поперёк страницы, мешает их читать.
            const NightSky(
              mood: SkyMood.reading,
              seed: _skySeed,
              child: SizedBox.expand(),
            ),
          SafeArea(
            bottom: false,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(AlmaMetrics.pad, 10, AlmaMetrics.pad, 0),
                  child: Row(children: [
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: Icon(Icons.arrow_back,
                          color: onParchment ? AlmaPalette.inkMuted : AlmaPalette.gold),
                      padding: EdgeInsets.zero,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '$index / $total',
                      style: AlmaType.numeral.copyWith(
                        color: onParchment ? AlmaPalette.inkMuted : AlmaPalette.gold,
                      ),
                    ),
                  ]),
                ),
                Expanded(
                  // Смена главы — снизу вверх с затуханием, той же кривой turn,
                  // что на iOS: анимация заканчивает движение, начатое пальцем,
                  // и должна выглядеть оседающей страницей, а не новым экраном.
                  child: AnimatedSwitcher(
                    duration: AlmaMotion.turn,
                    switchInCurve: AlmaMotion.turnCurve,
                    switchOutCurve: AlmaMotion.turnCurve.flipped,
                    transitionBuilder: (child, animation) => FadeTransition(
                      opacity: animation,
                      child: SlideTransition(
                        position: Tween(
                          begin: const Offset(0, 0.12),
                          end: Offset.zero,
                        ).animate(animation),
                        child: child,
                      ),
                    ),
                    child: KeyedSubtree(
                      key: ValueKey(_showing),
                      child: _page(l),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _page(L l) {
    if (_loading && _reading == null) {
      // **Самое долгое ожидание в продукте — сорок-девяносто секунд.**
      //
      // На нативе здесь надпись о том, откуда берётся текст, и рисунок,
      // собирающий себя всё время письма (`WritingArt.swift`); в порте
      // сначала стояла одна серая строка посреди ночи, потом пара тонких дуг
      // на пустом небе — и то и другое читалось как зависшее приложение.
      // Теперь рисунок чертит себя целиком, по разметке s29: небо появляется
      // за 3.2 секунды, дальше по нему ходит перо и всё это медленно
      // поворачивается — семьдесят секунд на оборот.
      //
      // Порядок и отбивки — из макета: фраза курсивом 26/1.2, 36 точек,
      // рисунок 260, 24 точки, подпись состояния.
      return Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
            child: Text(
              l.cabFromYourPositions,
              textAlign: TextAlign.center,
              style: AlmaType.displayL.copyWith(
                fontSize: 26,
                height: 1.2,
                fontStyle: FontStyle.italic,
                color: AlmaPalette.inkLight,
              ),
            ),
          ),
          const SizedBox(height: 36),
          // Зерно — пара «система + глава». Небо у всех сорока одной главы
          // общее (это макет), семейство фигуры задаёт система — иначе восемь
          // ожиданий выглядят одной заставкой, — а экземпляр внутри семейства
          // задаёт сама глава: у натальной карты шестнадцать глав, и все
          // шестнадцать ждали под одной и той же картинкой по сорок-девяносто
          // секунд каждая. Зерно берётся из слага, а не из индекса с сервера:
          // индекс приезжает с оглавлением, то есть уже после первого кадра, и
          // рисунок сменился бы на глазах у ждущего.
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
            child: WritingArt(
              seed: widget.system.index,
              grain: chapterGrain(widget.system, _showing),
            ),
          ),
          const SizedBox(height: 24),
          Text(l.stateWriting, style: AlmaType.meta),
        ]),
      );
    }
    final failure = _failure;
    // **Стена говорит по-человечески.** Сервер отвечает «natal has not been
    // unlocked yet» — это для разработчика; читателю нужна причина и путь.
    if (failure is ServerRefused && failure.code == 'locked' && _reading == null) {
      return _LockedWall(system: widget.system);
    }
    // **Совместимости нужен второй человек — и дверь к нему, а не фраза в
    // пустоте.**
    //
    // Здесь на весь экран стояла одна серая строка. Сначала это была вообще
    // служебная строка сервера с именем поля API («send `partner_profile_id`»),
    // снятая владельцем на кадре; теперь сервер отвечает по-человечески, но
    // экран всё равно оставлял человека без единственного действия, которое
    // тут имеет смысл. На экране системы этот случай давно нарисован так —
    // рисунок, фраза, кнопка, — и глава обязана вести себя так же.
    if (failure is ServerRefused &&
        failure.code == 'partner_required' &&
        _reading == null) {
      return _NeedsPartner(
        system: widget.system,
        message: failure.message.isNotEmpty ? failure.message : l.cabCompatNeedsSecond,
        onAdded: _load,
      );
    }
    if (failure != null && _reading == null) {
      // **Отказ по потолку сам называет выход — значит, выход обязан быть на
      // экране.** Фраза кончается словами «или прямо сейчас, с подпиской», а
      // под ней не было ничего: ни двери, ни кнопки. Предложение, названное
      // текстом и не показанное, хуже отсутствующего — оно выглядит как
      // издёвка. Остальные отказы двери не получают: сеть и отказ письма
      // подпиской не лечатся.
      final capped = failure is ServerRefused &&
          const ['month_budget', 'budget_exceeded'].contains(failure.code) &&
          !SessionScope.of(context).isSubscriber;
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AlmaMetrics.pad),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                failure is ServerRefused && failure.message.isNotEmpty
                    ? failure.message
                    : l.stateUnavailable,
                style: AlmaType.meta,
                textAlign: TextAlign.center,
              ),
              if (capped) ...[
                const SizedBox(height: 20),
                AlmaButton(
                  kind: AlmaButtonKind.outline,
                  fills: false,
                  label: l.cabPlansCta,
                  onTap: () => _openOffer(context, null),
                ),
              ],
            ],
          ),
        ),
      );
    }
    final reading = _reading;
    if (reading == null) return const SizedBox.shrink();

    final next = _next;

    return NotificationListener<ScrollNotification>(
      onNotification: (notification) {
        final metrics = notification.metrics;
        if (!metrics.hasContentDimensions || metrics.maxScrollExtent <= 0) {
          return false;
        }
        final past = metrics.pixels - metrics.maxScrollExtent;
        final byHand = notification is ScrollUpdateNotification &&
            notification.dragDetails != null;
        _onOverscroll(past > 0 ? past : 0, byHand: byHand);
        return false;
      },
      child: ListView(
        physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics()),
        padding: const EdgeInsets.fromLTRB(
            AlmaMetrics.pad, 8, AlmaMetrics.pad, AlmaMetrics.gapSection),
        children: [
          // **Вклейка — первое, что видно в главе.**
          //
          // Виджет арки был собран ещё в нулевом этапе и жил только в
          // отладочной витрине: карта вклеек на все сорок одну главу есть,
          // эндпоинт есть, диск-кэш есть, — а на самой главе картины не было
          // ни одной. В эталоне (`s5`) она стоит над надзаголовком, 150×188,
          // по центру.
          //
          // Главы без арта показывают римскую цифру в той же раме, а не
          // пустоту: дыра в шесть картин известна и помечена, и подменять её
          // чужой картинкой нельзя — вклейка не про то, что человек читает,
          // на платной главе хуже, чем её отсутствие.
          Center(
            child: PlateArch(
              store: SessionScope.of(context).plates,
              plate: AlmaPlates.name(widget.system, _showing),
              numeral: _entry?.numeral ?? '',
            ),
          ),
          const SizedBox(height: 26),
          Text(
            '${_entry?.numeral ?? ''} · ${_systemName(l)}'.toLowerCase(),
            style: AlmaType.overline.copyWith(color: AlmaPalette.goldDeep),
          ),
          const SizedBox(height: 10),
          Text(reading.title,
              style: AlmaType.displayL.copyWith(color: AlmaPalette.ink)),
          // **Позиции — подпись под главой, а не двенадцать плашек над ней.**
          //
          // Список цитат печатался капсулами во всю ширину: на плотной карте
          // это дюжина английских строк вроде «transiting uranus retrograde □
          // natal saturn · orb 0.25°» между заголовком и первым абзацем, и
          // текст, ради которого главу открыли, уезжал за нижний край.
          // «Реально странное количество блоков, и непонятно, что это всё
          // значит». Первая позиция остаётся видимой — обещание продукта в
          // том, что глава прочитана из карты, — остальные прячутся за счёт.
          if (reading.citedFactors.isNotEmpty) ...[
            const SizedBox(height: 14),
            _CitedLine(factors: reading.citedFactors, label: l.cabReadFrom),
          ],
          const SizedBox(height: 18),
          Container(
            height: 1,
            color: AlmaPalette.ink.withValues(alpha: 0.12),
          ),
          const SizedBox(height: 8),
          // **Превью: первый абзац читается, остальное под дымкой.**
          //
          // Глава написана целиком и настоящая — сервер её действительно
          // сочинил из этой карты, — но она платная. Показывать всё значит
          // отдавать товар даром; показывать заглушку значит не показывать
          // ничего. Первый абзац открыт, дальше размытие и дверь.
          for (final (i, paragraph) in reading.body.indexed)
            Padding(
              padding: const EdgeInsets.only(top: 14),
              child: _preview && i > 0
                  ? ImageFiltered(
                      imageFilter: ImageFilter.blur(sigmaX: 5.5, sigmaY: 5.5),
                      child: Text(paragraph,
                          style: AlmaType.body.copyWith(
                              color: AlmaPalette.ink, fontSize: 17, height: 1.6)),
                    )
                  : Text(paragraph,
                      style: AlmaType.body.copyWith(
                          color: AlmaPalette.ink, fontSize: 17, height: 1.6)),
            ),
          if (_preview) ...[
            const SizedBox(height: 22),
            Text(l.cabLockedNote,
                textAlign: TextAlign.center,
                style: AlmaType.meta.copyWith(color: AlmaPalette.inkMuted)),
            const SizedBox(height: 14),
            // Золото — то самое, из дизайн-системы: тёмная текстура и подпись
            // слоновой костью. Здесь стояла своя кнопка, плоско залитая
            // `AlmaPalette.gold` с чернильной подписью, — ровно та заливка,
            // которую `GoldTexture` запрещает словом «никогда». `fills: false`
            // — как на нативе (`AlmaButtonStyle(kind: .gold, fills: false)`):
            // дверь обнимает своё слово, а не занимает строку.
            Center(
              child: AlmaButton(
                fills: false,
                label: l.cabUnlock,
                onTap: () => _openOffer(context, widget.system),
              ),
            ),
          ],
          if (reading.advice != null) ...[
            const SizedBox(height: 26),
            Container(
              padding: const EdgeInsets.only(left: 16),
              decoration: const BoxDecoration(
                border: Border(
                    left: BorderSide(color: AlmaPalette.goldDeep, width: 2)),
              ),
              child: Text(
                reading.advice!,
                style: AlmaType.voice.copyWith(color: AlmaPalette.ink),
              ),
            ),
          ],
          const SizedBox(height: 34),
          // Хвост: следующая глава и полоса подтверждения. Полоса наливается
          // от 56 до 130 — сколько ещё тянуть, видно, а не угадывается.
          if (next != null) _tail(l, next),
        ],
      ),
    );
  }

  // **Предложения в конце дочитанной главы больше нет.** Здесь стояла тихая
  // строка и золотая дверь «Открыть: Натальная карта» — в расчёте на минуту,
  // когда письмо только что доказало себя. На экране это работало иначе:
  // кнопка вставала ровно между концом текста и подсказкой протяжки к
  // следующей главе, и человек, дочитавший бесплатную главу, упирался в
  // покупку там, где ждал продолжения чтения. Владелец, увидев кадр: «она тут
  // вообще не нужна».
  //
  // Снято только в порте, по его же решению — на нативе `chapterEndOffer`
  // остаётся, и это сознательное расхождение, а не отставание порта.
  //
  // Дверь на *закрытой* главе цела: `_preview` выше рисует «Разблокировать»,
  // и это единственный способ её купить. Убрано предложение поверх уже
  // прочитанного, а не путь к покупке.

  String _systemName(L l) => switch (widget.system) {
        SystemSlug.natal => l.cabSystemNatal,
        SystemSlug.numerology => l.cabSystemNumerology,
        SystemSlug.birthCard => l.cabSystemBirthCard,
        SystemSlug.transits => l.cabSystemTransits,
        SystemSlug.solarReturn => l.cabSystemSolarReturn,
        SystemSlug.compatibility => l.cabSystemCompatibility,
        SystemSlug.astrocartography => l.cabSystemAstrocartography,
        SystemSlug.synthesis => l.cabSystemSynthesis,
      };

  Widget _tail(L l, ChapterEntry next) {
    final progress = (_pull / _commitMark).clamp(0.0, 1.0);
    return Column(children: [
      SizedBox(
        width: 64,
        child: Stack(children: [
          Container(height: 2, color: AlmaPalette.ink.withValues(alpha: 0.15)),
          FractionallySizedBox(
            widthFactor: progress,
            child: Container(height: 2, color: AlmaPalette.goldDeep),
          ),
        ]),
      ),
      const SizedBox(height: 12),
      Text('↓', style: AlmaType.meta.copyWith(color: AlmaPalette.inkMuted2)),
      const SizedBox(height: 6),
      Text(next.title,
          style: AlmaType.meta.copyWith(color: AlmaPalette.inkMuted)),
      const SizedBox(height: 4),
      Text(l.cabPullToTurn,
          style: AlmaType.meta.copyWith(color: AlmaPalette.inkMuted2)),
      const SizedBox(height: 40),
    ]);
  }
}


/// Строка цитат под заголовком главы: первая позиция и счёт остальных,
/// раскрывающийся по нажатию. Сестра такой же строки в беседе с Alma.
class _CitedLine extends StatefulWidget {
  const _CitedLine({required this.factors, required this.label});

  final List<String> factors;
  final String label;

  @override
  State<_CitedLine> createState() => _CitedLineState();
}

class _CitedLineState extends State<_CitedLine> {
  bool _open = false;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    final rest = widget.factors.length - 1;
    final style = AlmaType.numeral.copyWith(
      color: AlmaPalette.goldDeep,
      fontFamilyFallback: AlmaType.glyphFallback,
    );
    return GestureDetector(
      onTap: rest > 0 ? () => setState(() => _open = !_open) : null,
      behavior: HitTestBehavior.opaque,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text(widget.label.toUpperCase(),
              style: AlmaType.overline.copyWith(color: AlmaPalette.goldDeep)),
          const SizedBox(width: 12),
          Expanded(
            child: Text(CabinetWordsMore.factor(l, widget.factors.first),
                style: style, overflow: TextOverflow.ellipsis),
          ),
          if (rest > 0 && !_open) ...[
            const SizedBox(width: 8),
            Text('+$rest', style: style),
          ],
        ]),
        if (_open)
          for (final factor in widget.factors.skip(1))
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(CabinetWordsMore.factor(l, factor), style: style),
            ),
      ]),
    );
  }
}


/// Стена: система не открыта. Причина словами и путь дальше.
///
/// Прежде здесь стояла служебная строка сервера — «natal has not been unlocked
/// yet», по-английски и про внутренние понятия. Читателю нужно другое: что
/// именно закрыто, почему это стоит открыть и одна кнопка.
class _LockedWall extends StatelessWidget {
  const _LockedWall({required this.system});

  final SystemSlug system;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const WritingArt(size: 200),
            const SizedBox(height: 28),
            Text(l.cabLocked,
                textAlign: TextAlign.center,
                style: AlmaType.displayL.copyWith(fontSize: 24)),
            const SizedBox(height: 12),
            Text(l.cabLockedNote,
                textAlign: TextAlign.center, style: AlmaType.meta),
            const SizedBox(height: 24),
            AlmaButton(
              fills: false,
              label: l.cabUnlock,
              onTap: () => _openOffer(context, system),
            ),
          ],
        ),
      ),
    );
  }
}

/// Открыть витрину этой системы.
///
/// Отдельным маршрутом поверх всего, а не листом внутри вкладки: витрина —
/// это страница, на которую уходят и с которой возвращаются туда же, откуда
/// пришли, и глава под ней остаётся на своей странице.
void _openOffer(BuildContext context, SystemSlug? system) {
  Navigator.of(context, rootNavigator: true).push(
    CupertinoPageRoute(builder: (context) => OfferScreen(system: system)),
  );
}

/// «Совместимости нужен второй человек» — с рисунком и дверью к нему.
///
/// Порт того же состояния с экрана системы, слово в слово: пустое небо над
/// одной серой строкой читается как сломанный экран, а рисунок, который ничего
/// не утверждает — две орбиты, ещё не встретившиеся, — читается как ожидание.
class _NeedsPartner extends StatelessWidget {
  const _NeedsPartner({
    required this.system,
    required this.message,
    required this.onAdded,
  });

  final SystemSlug system;
  final String message;
  final Future<void> Function() onAdded;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Зерно 0 — орбиты: две дуги, которые ещё не встретились. У
            // совместимости своё зерно даёт решётку, и пустая решётка на
            // экране «второго человека нет» читается как пустая таблица,
            // то есть как сломанный экран.
            const WritingArt(size: 200, seed: 0),
            const SizedBox(height: 24),
            // **Чернила — цвет пергамента, а не ночи.** Здесь стоял
            // `AlmaPalette.ink`, и фраза почти пропадала на тёмном: снято на
            // кадре. Пергамент появляется вместе с главой, а этой главы нет.
            Text(message,
                textAlign: TextAlign.center,
                style: AlmaType.body.copyWith(color: AlmaPalette.muted)),
            const SizedBox(height: 20),
            AlmaButton(
              fills: false,
              label: l.cabPeopleAdd,
              onTap: () async {
                await Navigator.of(context, rootNavigator: true).push(
                  CupertinoPageRoute(builder: (context) => const PeopleScreen()),
                );
                await onAdded();
              },
            ),
          ],
        ),
      ),
    );
  }
}
