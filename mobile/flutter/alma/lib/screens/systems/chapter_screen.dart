import 'dart:math' as math;

import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../design/buttons.dart';
import '../../design/gilt_page.dart';
import '../../design/layout.dart';
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
  const ChapterScreen({
    super.key,
    required this.system,
    required this.chapter,
    this.partner,
  });

  final SystemSlug system;
  final String chapter;

  /// Кого сравнивать — для глав совместимости.
  ///
  /// **Экран обязан уметь это сказать, иначе он ломается на втором человеке.**
  /// Сервер подставляет партнёра сам, но только пока сохранённый человек ровно
  /// один; при двух и более он отвечает 422 `partner_required` — и тот, у кого
  /// людей уже двое, читал «добавь человека». `null` значит «не сказано», и
  /// тогда берётся тот же человек, против которого экран системы посчитал
  /// колесо ([_partnerId]): текст главы и рисунок над оглавлением обязаны быть
  /// про одну и ту же пару.
  final Profile? partner;

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

  /// Права на эту главу нет — на экране стена S26, и запроса не будет.
  ///
  /// **Здесь стоял `_preview`, и это отменённое правило.** Платная глава
  /// приезжала *написанной*: сервер сочинял её целиком, помечал ответ
  /// `preview`, экран показывал первый абзац и размывал остальные. Владелец
  /// снял правило — «мы не должны сразу писать всю главу, пока у человека нет
  /// подписки или купленного», — потому что за каждый такой показ платили мы,
  /// до всякого решения о покупке. Поэтому размытой пробы больше нет вовсе:
  /// текста не написано, и экран не должен делать вид, что он есть.
  ///
  /// Считается **до** запроса, из оглавления (`ChapterEntry.open`) — того
  /// самого, которое только что показал экран системы, — поэтому кнопка стоит
  /// на первом кадре, а не после ответа сервера.
  bool _locked = false;

  /// Право есть, текста ещё нет: сервер сейчас пишет главу.
  ///
  /// Отдельно от `_loading`, потому что ожиданий два и они разной длины.
  /// Оглавление — обычный GET на десятки миллисекунд, письмо — сорок-девяносто
  /// секунд. «Пишу эту главу…» с рисунком принадлежит второму; показывать его
  /// на первом значило обещать текст ещё до того, как выяснилось, положен ли
  /// он вообще.
  bool _writing = false;
  ChapterList? _list;
  AlmaError? _failure;
  bool _loading = true;

  double _pull = 0;
  bool _armed = false;

  /// Сколько главы прочитано — для нити у правого поля ([GiltThread]).
  ///
  /// **Отдельным сигналом, а не полем состояния.** Прокрутка сообщает о себе
  /// каждый кадр; `setState` на каждый кадр перестраивал бы всю страницу
  /// вместе со списком абзацев — то есть платил бы разбором текста за
  /// двухточечную полоску. Слушает её один узел.
  final ValueNotifier<double> _read = ValueNotifier(0);

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
    _read.dispose();
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_started) {
      _started = true;
      // **Право спрашивается до первого кадра, а не после первого ответа.**
      //
      // В главу заходят с экрана системы, который только что показал
      // оглавление; клиент помнит его (`AlmaClient.knownChapters`), и этого
      // достаточно, чтобы нарисовать стену сразу — так же, как эталон рисует
      // её на s26: заголовок, объяснение, одна кнопка. Раньше здесь начинался
      // запрос, экран показывал «Пишу эту главу…», и дверь появлялась только
      // после ответа сервера.
      final session = SessionScope.of(context);
      final known =
          session.client.knownChapters(widget.system, locale: session.locale);
      // Заодно шапка «4 / 16» встаёт правильной с первого кадра.
      if (known != null) _list = known;
      final right = _right(session);
      _locked = right == false;
      // Право известно и оно есть — значит, ждать действительно текста, и
      // «Пишу эту главу…» встаёт сразу, как вставало всегда. Пока право
      // неизвестно (оглавления не привозили), экран молчит: показывать
      // ожидание текста тому, кому текст, возможно, не положен, — то же
      // обещание, ради снятия которого всё это и делалось.
      _writing = right == true;
      _load();
    }
  }

  /// Открыта ли показываемая глава. `null` — пока неизвестно.
  ///
  /// **Права аккаунта спрашиваются первыми, и только на «да».** Открытая
  /// система открыта во всех своих главах — сервер собирает `unlocked` именно
  /// так и купленную в одиночку главу туда не кладёт, — а права обновляются
  /// покупкой сразу, тогда как оглавление в памяти могло быть привезено до
  /// неё. Порядок «сначала список» показывал бы стену тому, кто только что
  /// заплатил, и это худшая из возможных ошибок здесь.
  ///
  /// Обратное неверно: «система не куплена» ещё не значит «эта глава закрыта»
  /// — бесплатная глава платной системы открыта, — поэтому отрицательный ответ
  /// даёт только оглавление. В нём `open` считается тем же
  /// `entitlements.check`, что и стена в `POST /v1/readings`.
  bool? _right(AlmaSession session, {ChapterList? from}) {
    if (session.entitlements.opened(widget.system)) return true;
    final list = from ?? _list;
    if (list != null) {
      for (final entry in list.chapters) {
        if (entry.slug == _showing) return entry.open;
      }
    }
    return null;
  }

  /// [relist] — перечитать оглавление с сервера, а не верить памяти. Нужно
  /// после возврата с витрины: покупка меняет право, и старый список сказал бы
  /// «закрыто» тому, кто только что заплатил.
  Future<void> _load({bool relist = false}) async {
    final session = SessionScope.of(context);
    // Нить возвращается в начало вместе со страницей: следующая глава
    // прочитана на ноль, чем бы ни кончилась предыдущая.
    _read.value = 0;
    setState(() {
      _loading = true;
      _failure = null;
      _pull = 0;
      _armed = false;
    });
    try {
      // **Оглавление показывается, как только пришло, а не вместе с текстом.**
      //
      // Список глав — обычный GET и отвечает мгновенно; глава пишется 40–90
      // секунд. Пока оба ждали одного `setState`, `_entry` оставался пустым всю
      // эту минуту, и счётчик печатал запасную единицу: открытая седьмая глава
      // весь показ «Пишу эту главу…» держала в шапке «1 / 16». Снято на
      // симуляторе 13 августа 2026.
      final list = (relist || _list == null)
          ? await session.client.chapters(widget.system, locale: session.locale)
          : _list!;
      if (!mounted) return;
      setState(() {
        _list = list;
        _locked = _right(session, from: list) == false;
      });
      // **Закрытая глава не спрашивает сервер вовсе.** Не потому, что сервер
      // ответит отказом — он ответит, 402 `locked`, — а потому, что просить
      // текст, который решено не писать, значит ждать впустую на глазах у
      // человека, которому нужна кнопка.
      //
      // Признак перелистывания снимается здесь же: страница доехала, пусть и
      // до стены. Иначе протяжка в закрытую главу оставляла бы жест
      // заблокированным до следующего удачного чтения.
      if (_locked) {
        setState(() => _advancing = false);
        return;
      }
      setState(() => _writing = true);
      final response = await session.client.reading(
        system: widget.system,
        chapter: _showing,
        locale: session.locale,
        partnerProfileId: _partnerId(session),
      );
      if (mounted) {
        // Пергамент появляется вместе с текстом — и бар вместе с ним. Но
        // только если эта глава ещё наверху: пока она писалась, человек мог
        // уйти назад или открыть другую, и поднимать пергамент из-под чужой
        // страницы нельзя.
        final route = ModalRoute.of(context);
        if (route == null || route.isCurrent) readingNow.value = true;
        setState(() {
          _reading = response.reading;
          _advancing = false;
        });
      }
    } on AlmaError catch (error) {
      if (mounted) setState(() => _failure = error);
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
          _writing = false;
        });
      }
    }
  }

  /// Кого сравнивать в этой главе — и только для совместимости.
  ///
  /// **Первый сохранённый, а не «сервер разберётся».** Разберётся он ровно до
  /// второго человека: `_partner` в `readings.py` подставляет партнёра только
  /// при `len(others) == 1`, иначе 422. При этом экран системы считает колесо
  /// против `session.people.firstOrNull` — здесь то же правило слово в слово,
  /// потому что глава и рисунок над её оглавлением обязаны быть про одну пару.
  ///
  /// Пусто, когда людей нет вовсе: тогда 422 приходит по делу, и экран рисует
  /// дверь «добавить человека», а не молчит.
  String? _partnerId(AlmaSession session) {
    if (widget.system != SystemSlug.compatibility) return null;
    return (widget.partner ?? session.people.firstOrNull)?.id;
  }

  /// Вернулись с витрины. Право могло измениться — перечитываем оглавление у
  /// сервера и, если глава открылась, тем же путём идём за текстом: покупка
  /// это и есть то, после чего глава пишется целиком.
  Future<void> _afterOffer() async {
    if (mounted) await _load(relist: true);
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
    // Читается до `SafeArea`: внутри неё вырез уже съеден, и остатка не
    // вычислить.
    final safeTop = MediaQuery.paddingOf(context).top;

    return Scaffold(
      backgroundColor: AlmaPalette.night,
      // **Фон — нижний слой стопки, а не украшение на содержимом.**
      //
      // Ночным состояниям главы — ожиданию письма, стене закрытой системы,
      // отказу — полагается то же небо, что «Сегодня» и анкете: на s26 и s29 за
      // содержимым звёзды и туманность. Здесь была ровная заливка ночью, и
      // экран читался плоским рядом с любым соседним. Бумага неба не
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
            // **Глава лежит на золочёной бумаге, а не на пергаменте.**
            //
            // Пергамент — градиент `#EDE3CC→#DFD0AF` — стоял здесь с первого
            // дня порта и был верен старому холсту (`s5`). Свежий эталон
            // застилает открытие и чтение главы снимком листа в золочёной раме
            // (`s51`, `s52`), и это не смена оттенка: у рамы есть габарит, ради
            // которого у страницы появились поля 52/56 и посадка вклейки в
            // чистый центр. Правило расхождений холста однозначно — прав холст.
            const GiltPage()
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
                  // **На бумаге шапка стоит по холсту, на ночи — по общему
                  // полю.** Отсчёт у холста от верхнего края экрана (88), а
                  // `SafeArea` уже опустила содержимое на вырез, поэтому здесь
                  // остаток. `max` — для телефонов с высокой чёлкой: если
                  // безопасная зона глубже 83 точек, кнопка съезжает вниз
                  // вместе с ней, а не прячется под неё.
                  padding: EdgeInsets.fromLTRB(
                    onParchment ? GiltPage.side - GiltPage.headPad : AlmaMetrics.pad,
                    onParchment
                        ? math.max(10, GiltPage.headTop - GiltPage.headPad - safeTop)
                        : 10,
                    AlmaMetrics.pad,
                    0,
                  ),
                  child: onParchment
                      // Счётчика глав рядом со стрелкой на бумаге нет: холст
                      // печатает его вертикально под нитью прогресса у правого
                      // поля, и держать два счётчика на одной странице незачем.
                      ? GiltBack(onTap: () => Navigator.of(context).pop())
                      : Row(children: [
                          IconButton(
                            onPressed: () => Navigator.of(context).pop(),
                            icon: const Icon(Icons.arrow_back,
                                color: AlmaPalette.gold),
                            padding: EdgeInsets.zero,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            '$index / $total',
                            style: AlmaType.numeral,
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
                      child: onParchment ? _underMargin(_page(l)) : _page(l),
                    ),
                  ),
                ),
              ],
            ),
          ),
          // Нить прогресса — поверх содержимого и мимо безопасной зоны: она
          // стоит по середине высоты **экрана**, как на холсте, и вырез её не
          // сдвигает. Только на бумаге: прогресса чтения там, где текста ещё
          // нет, не бывает.
          if (onParchment) GiltThread(read: _read, counter: '$index / $total'),
        ],
      ),
    );
  }

  /// Верхнее поле страницы: строка уходит под него, а не режется об него.
  ///
  /// **Что было видно.** Прокрутка обрезается сразу под кнопкой возврата, и на
  /// срезе оставался ряд половинок букв — верхушки строчных, повисшие в
  /// сантиметре от кружка со стрелкой. На ночном небе такого не было: там
  /// текст уходил в тёмное и срез не читался. На золочёной бумаге фон светлый и
  /// подробный, и разрубленная строка на нём видна первой.
  ///
  /// Холст (`s51`, `s52`) держит верхние 142 точки чистой бумагой в обоих
  /// кадрах — там нет ни строки. Натив ответа не даёт вовсе: золочёной бумаги
  /// он не знает, глава там лежит на пергаменте. Значит прав холст, и поле
  /// должно быть полем.
  ///
  /// Гасим не фон, а сам текст: бумага лежит отдельным дном стопки, под
  /// прокруткой, поэтому прозрачность строки открывает лист, а не пустоту.
  /// Восемнадцать точек — высота одной строчной буквы этого кегля: меньше
  /// читается как обрезка, больше съедает живую строку.
  Widget _underMargin(Widget page) {
    return ShaderMask(
      shaderCallback: (rect) => const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0x00000000), Color(0xFF000000)],
        stops: [0.0, 1.0],
      ).createShader(Rect.fromLTWH(0, rect.top, rect.width, 18)),
      blendMode: BlendMode.dstIn,
      child: page,
    );
  }

  Widget _page(L l) {
    // Стена — раньше всего остального, включая ожидание: на закрытой главе
    // ждать нечего, а кнопка нужна сразу.
    if (_locked && _reading == null) {
      return _LockedWall(system: widget.system, onReturned: _afterOffer);
    }
    if (_writing && _reading == null) {
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
    //
    // Второй рубеж, а не первый: право теперь читается из оглавления до
    // запроса, и сюда попадает только случай, когда клиент считал главу
    // открытой, а сервер отказал, — право истекло между списком и запросом.
    if (failure is ServerRefused && failure.code == 'locked' && _reading == null) {
      return _LockedWall(system: widget.system, onReturned: _afterOffer);
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
    // ↑ дальше страница; поле верха ей ставит [_underMargin].

    return NotificationListener<ScrollNotification>(
      onNotification: (notification) {
        final metrics = notification.metrics;
        if (!metrics.hasContentDimensions || metrics.maxScrollExtent <= 0) {
          return false;
        }
        // Нить считает от того же дна, что и порог перелистывания, — и она
        // обязана дойти до конца ровно там, где страница кончилась, а не
        // раньше. Дотяжка за дно (`past`) в долю не входит: прочитано и так
        // всё.
        _read.value =
            (metrics.pixels / metrics.maxScrollExtent).clamp(0.0, 1.0);
        final past = metrics.pixels - metrics.maxScrollExtent;
        final byHand = notification is ScrollUpdateNotification &&
            notification.dragDetails != null;
        _onOverscroll(past > 0 ? past : 0, byHand: byHand);
        return false;
      },
      child: ListView(
        physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics()),
        // **Поля страницы — не общие 22, а габарит рамы.**
        //
        // Слева 52, справа 56: за этой чертой начинаются золотые завитки, на
        // которых буквы не читаются, а у правого края вдобавок стоит нить
        // прогресса со счётчиком. Числа с холста (`s51` — 50/50, `s52` —
        // 52/56); взята пара `s52`, потому что это кадр с самым длинным
        // текстом, то есть тот, на котором поля и проверяются.
        // **Низ считается от бара вкладок, а не общей отбивкой.**
        //
        // Здесь стоял `gapSection` (44) — и хвост «↓ Портрет · тяни дальше»
        // уезжал под полосу вкладок: она 52 плюс домашний индикатор, то есть
        // 86, и сорока четырёх не хватало. Проверено глазами на симуляторе:
        // вторая строка хвоста была срезана ровно посередине.
        //
        // Формула — та же, что у `screen_scaffold.dart`, вместе с её уроком:
        // отступ берётся от **окна**, а не от окружения. `Scaffold` с
        // `extendBody` уже кладёт полную высоту бара в `MediaQuery` тела, и
        // сложение с ней считает бар дважды. Воздух 22 — из холста: хвост там
        // стоит на 108 от нижнего края, а 108 − 86 = 22.
        padding: EdgeInsets.fromLTRB(
            GiltPage.side,
            GiltPage.headGap,
            GiltPage.sideRight,
            AlmaMetrics.tabBarHeight +
                MediaQueryData.fromView(View.of(context)).padding.bottom +
                22),
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
          //
          // **Посажена в чистый центр листа**, а не просто «по центру экрана»:
          // теперь у страницы есть поля, и центр колонки 52…56 приходится на
          // середину бумаги внутри рамы — там же, где вклейка стоит на `s51`.
          Center(
            child: PlateArch(
              store: SessionScope.of(context).plates,
              plate: AlmaPlates.name(widget.system, _showing),
              numeral: _entry?.numeral ?? '',
            ),
          ),
          const SizedBox(height: 16),
          // **Открытие главы выровнено по центру, а не по левому краю.**
          // Вклейка стоит посреди листа, и надзаголовок с титулом под ней
          // держат ту же ось — иначе картина висит по центру, а подпись к ней
          // уезжает влево (`s51`).
          Text(
            '${_entry?.numeral ?? ''} · ${_systemName(l)}'.toLowerCase(),
            textAlign: TextAlign.center,
            style: AlmaType.overline.copyWith(color: AlmaPalette.goldDeep),
          ),
          const SizedBox(height: 9),
          Text(reading.title,
              textAlign: TextAlign.center,
              style: AlmaType.displayL
                  .copyWith(color: AlmaPalette.ink, height: 1.14)),
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
            // Мета-строка держит ту же ось, что вклейка и титул, и не шире 280
            // точек: на холсте она стоит подписью под заголовком, а
            // растянутая во всю колонку разъезжается на «read from» слева и
            // «+2» у самого правого поля.
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 280),
                child:
                    _CitedLine(factors: reading.citedFactors, label: l.cabReadFrom),
              ),
            ),
          ],
          const SizedBox(height: 16),
          Container(
            height: 1,
            color: AlmaPalette.ink.withValues(alpha: 0.13),
          ),
          // Четыре, а не восемь: у каждого абзаца своя отбивка сверху в 14, и
          // от линейки до первой строки холст просит восемнадцать.
          const SizedBox(height: 4),
          // **Размытой пробы здесь больше нет — и это осознанная отмена.**
          //
          // Стояло так: платная глава приезжала написанной целиком, с флагом
          // `preview`; первый абзац читался, остальные шли под `ImageFilter.
          // blur(5.5)`, а под ними — «Разблокировать». Продающий замысел был
          // в том, что страница настоящей прозы о тебе убеждает сильнее
          // шестнадцати закрытых заголовков.
          //
          // Владелец отменил его ради денег за генерацию: сервер писал главу
          // сильной моделью до всякой покупки, то есть платили мы, а решал
          // потом человек. Теперь текста без права не существует, и размывать
          // нечего — а рисовать дымку поверх пустоты значило бы врать, что
          // написанное есть. Закрытая глава показывает стену (`_LockedWall`),
          // и она честна: заголовок, объяснение, одна кнопка.
          //
          // Сюда, на бумагу, попадает только оплаченный текст — целиком.
          //
          // **Кегль вернулся к общему 15.5.** Стояло 17 — число старого холста
          // (`s5`), где колонка была шириной 358 точек. Колонка сузилась до
          // 294, и 17 на ней даёт строку в семь-восемь слов: глаз теряет её
          // конец чаще, чем читает. Холст чтения (`s52`) печатает главу тем же
          // кеглем, что и весь остальной продукт, с чуть большим интерлиньяжем.
          for (final paragraph in reading.body)
            Padding(
              padding: const EdgeInsets.only(top: 14),
              child: Text(paragraph,
                  style: AlmaType.body
                      .copyWith(color: AlmaPalette.ink, height: 1.62)),
            ),
          if (reading.advice != null) ...[
            const SizedBox(height: 22),
            Container(
              padding: const EdgeInsets.only(left: 15),
              decoration: const BoxDecoration(
                border: Border(
                    left: BorderSide(color: AlmaPalette.goldDeep, width: 2)),
              ),
              child: Text(
                reading.advice!,
                style: AlmaType.voice
                    .copyWith(color: AlmaPalette.ink, fontSize: 18),
              ),
            ),
          ],
          // **Точка в конце главы.** Звёздочка между двумя гаснущими волосами
          // — последнее, что стоит на кадре чтения (`s52`): она говорит, что
          // текст кончился, а не оборвался на середине. Без неё абзац просто
          // упирается в подсказку о протяжке, и дочитавший не знает, дочитал
          // ли он.
          const SizedBox(height: 20),
          const _EndMark(),
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
  // Дверь на *закрытой* главе цела: стена `_LockedWall` рисует
  // «Разблокировать», и это единственный способ её купить. Убрано предложение
  // поверх уже прочитанного, а не путь к покупке.

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
    // **Свечение под хвостом — не украшение, а условие читаемости.**
    //
    // Хвост стоит у нижнего края, а нижний край золочёного листа — это уже
    // рама: завитки, блики, тёмный мрамор за ними. Серая строка попадает на
    // них и пропадает наполовину. Холст (`s51`, `s52`) решает это ровно так —
    // два ореола цвета бумаги под самими буквами, а не плашкой под строкой:
    // плашка на фотографии видна как наклейка.
    final glow = [
      Shadow(
          color: AlmaPalette.inkLight.withValues(alpha: 0.95), blurRadius: 10),
      Shadow(
          color: AlmaPalette.inkLight.withValues(alpha: 0.9), blurRadius: 4),
    ];
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
      Text('↓',
          style: AlmaType.meta
              .copyWith(color: AlmaPalette.inkMuted2, shadows: glow)),
      const SizedBox(height: 6),
      Text(next.title,
          textAlign: TextAlign.center,
          style: AlmaType.meta
              .copyWith(color: AlmaPalette.inkMuted, shadows: glow)),
      const SizedBox(height: 4),
      Text(l.cabPullToTurn,
          textAlign: TextAlign.center,
          style: AlmaType.meta
              .copyWith(color: AlmaPalette.inkMuted2, shadows: glow)),
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
    // Золото на ступень темнее пергаментного: `meta-line-spec.md` называет для
    // пергамента #A8873C, но пергамента под строкой больше нет — под ней
    // золочёная бумага, светлее и сама с золотом, и холст главы (`s51`)
    // печатает мета-строку именно #8A6F2E.
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
            // Режется только хвост дома — см. `AlmaShrink.fitMetaLine`.
            // Многоточие здесь съедало знак, то есть саму позицию.
            child: LayoutBuilder(
              builder: (context, box) => Text(
                AlmaShrink.fitMetaLine(
                  line: CabinetWordsMore.factor(l, widget.factors.first),
                  style: style,
                  maxWidth: box.maxWidth,
                  scaler: MediaQuery.textScalerOf(context),
                ),
                // Голосу — полная строка с именем знака и целым домом: у неё
                // нет ширины, и урезать её не за чем.
                semanticsLabel:
                    CabinetWordsMore.factorSpoken(l, widget.factors.first),
                style: style,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
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
              child: Text(CabinetWordsMore.factor(l, factor),
                  semanticsLabel: CabinetWordsMore.factorSpoken(l, factor),
                  style: style),
            ),
      ]),
    );
  }
}


/// Знак конца главы: звёздочка между двумя волосами, гаснущими к краям.
///
/// Не разделитель `AlmaGradient.fadedRule`, хотя и похож: тот гаснет с обоих
/// концов и делит равных, а этот наливается **к середине** — оба волоса ведут
/// к звёздочке, потому что она тут главная. Разметка `s52`.
class _EndMark extends StatelessWidget {
  const _EndMark();

  @override
  Widget build(BuildContext context) {
    final faded = AlmaPalette.goldDeep.withValues(alpha: 0.5);
    return Row(children: [
      Expanded(
        child: Container(
          height: 1,
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [Colors.transparent, faded]),
          ),
        ),
      ),
      const SizedBox(width: 10),
      Text('✦',
          style: AlmaType.numeral
              .copyWith(fontSize: 9, color: AlmaPalette.goldDeep)),
      const SizedBox(width: 10),
      Expanded(
        child: Container(
          height: 1,
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [faded, Colors.transparent]),
          ),
        ),
      ),
    ]);
  }
}

/// Стена: система не открыта. Причина словами и путь дальше.
///
/// Прежде здесь стояла служебная строка сервера — «natal has not been unlocked
/// yet», по-английски и про внутренние понятия. Читателю нужно другое: что
/// именно закрыто, почему это стоит открыть и одна кнопка.
///
/// Разметка — s26 эталона, буква в букву: рисунок 200, отбивка 28, заголовок
/// 24 засечным, отбивка 12, объяснение, отбивка 24, кнопка. И ровно столько:
/// обещать на стене то, чего пока не написано, нельзя, поэтому ни строки
/// текста главы, ни дымки на её месте здесь нет.
class _LockedWall extends StatelessWidget {
  const _LockedWall({required this.system, required this.onReturned});

  final SystemSlug system;

  /// Витрину закрыли. Право могло измениться — экран обязан перепроверить его
  /// и, если глава куплена, идти за текстом. Без этого купивший возвращался
  /// на ту же стену, с которой ушёл платить.
  final Future<void> Function() onReturned;

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
              onTap: () async {
                await _openOffer(context, system);
                await onReturned();
              },
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
///
/// Ждёт закрытия витрины: вызывающему нужно знать, когда возвращаться к
/// вопросу о праве.
Future<void> _openOffer(BuildContext context, SystemSlug? system) =>
    Navigator.of(context, rootNavigator: true).push(
      CupertinoPageRoute(builder: (context) => OfferScreen(system: system)),
    );

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
