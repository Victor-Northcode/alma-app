import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';

import 'billing/alma_store.dart';
import 'design/invitation_pill.dart';
import 'design/metrics.dart';
import 'design/palette.dart';
import 'design/tab_bar.dart';
import 'design/typography.dart';
import 'l10n/alma_l10n.dart';
import 'net/alma_client.dart';
import 'net/models.dart';
import 'notify/push_devices.dart';
import 'screens/alma/alma_screen.dart';
import 'screens/journey/journey_screen.dart';
import 'screens/launch_screen.dart';
import 'screens/settings/settings_screen.dart';
import 'screens/systems/chapter_screen.dart';
import 'screens/systems/people_screen.dart';
import 'screens/systems/system_screen.dart';
import 'screens/systems/systems_screen.dart';
import 'screens/today/today_screen.dart' show TodayScreen, noteLaunch;
import 'state/ask_alma.dart';
import 'state/session.dart';

void main() => runApp(AlmaApp(
      client: AlmaClient(
        // База берётся из окружения сборки, как ALMA_API_BASE на нативных
        // сборках; по умолчанию — локальный сервер разработки. Захардкоженного
        // боевого адреса здесь нет и не будет: api.pazl.ai однажды уже уехал в
        // прошивку несуществующим.
        baseUrl: Uri.parse(const String.fromEnvironment(
          'ALMA_API_BASE',
          defaultValue: 'http://127.0.0.1:8018',
        )),
      ),
    ));

/// Корень. Порт `AlmaApp.swift` + `RootView.swift`.
class AlmaApp extends StatefulWidget {
  const AlmaApp({super.key, required this.client});

  final AlmaClient client;

  @override
  State<AlmaApp> createState() => _AlmaAppState();
}

class _AlmaAppState extends State<AlmaApp> {
  late final AlmaSession _session = AlmaSession(widget.client);

  @override
  void initState() {
    super.initState();
    _session.start();
    // **Слушать магазин всю жизнь приложения.**
    //
    // Одобренная «спросить у родителя» покупка, продление, возврат и покупка,
    // сделанная на другом устройстве, приходят в поток покупок в моменты, не
    // связанные ни с одним экраном. Пока это делалось только на витрине, всё
    // доставленное магазином асинхронно не доходило до нас, пока кто-нибудь не
    // откроет витрину; на нативе строчка стоит там же — в `RootView`, под
    // `.tint`, по той же причине.
    AlmaStore.shared.attach(_session);
    // **Уведомления здороваются на каждом запуске, а не однажды.**
    //
    // Строка устройства на сервере хранит `last_seen_at`, и та, которую никто
    // не подтвердил девяносто дней, сметается (`notify/tokens.py`) — то есть
    // подписчик, спросивший однажды и получивший разрешение, через три месяца
    // тихо перестал бы получать оплаченное. Тот же вызов чинит часовой пояс
    // тому, кто переехал, и снимает устройство с учёта, если разрешение
    // отозвали в настройках телефона. Ничего не спрашивает: системное окно
    // показывает только экран пред-вопроса.
    //
    // После `whenReady`, а не рядом с ним: до готовности сессии токена
    // аккаунта ещё нет, а запрос без токена сервер встретил бы новым гостем.
    _session.whenReady().then((_) => AlmaPush.instance.sync(widget.client));
    // Счёт запусков для карточки «сохрани карту»: считается здесь, потому что
    // здесь и есть запуск. Внутри карточки это был бы счёт визитов на экран.
    noteLaunch();
  }

  @override
  Widget build(BuildContext context) {
    return SessionScope(
      session: _session,
      child: MaterialApp(
        title: 'Alma',
        debugShowCheckedModeBanner: false,
        localizationsDelegates: L.localizationsDelegates,
        supportedLocales: L.supportedLocales,
        theme: ThemeData(
          useMaterial3: true,
          brightness: Brightness.dark,
          scaffoldBackgroundColor: AlmaPalette.night,
          colorScheme: const ColorScheme.dark(
            surface: AlmaPalette.night,
            primary: AlmaPalette.gold,
            onPrimary: AlmaPalette.inkOnGold,
          ),
        ),
        home: const CabinetShell(),
      ),
    );
  }
}

/// Кабинет: четыре вкладки под одним небом.
class CabinetShell extends StatefulWidget {
  const CabinetShell({super.key});

  @override
  State<CabinetShell> createState() => _CabinetShellState();
}

class _CabinetShellState extends State<CabinetShell> {
  CabinetTab _tab = CabinetTab.today;
  final _systemsNav = GlobalKey<NavigatorState>();

  /// Переход между вкладками. Мгновенная подмена читается как рывок, а на
  /// нативе вкладки меняются движением: новая приходит с той стороны, куда
  /// вёл палец, и проявляется. Держим стек живым — двигается только слой.
  late final PageController _pages = PageController(initialPage: _tab.index);

  /// Позван ли бар на вкладке Alma. Поднимает грабер внизу беседы, слушает
  /// оболочка — см. [TabsPeek] о том, почему признак живёт отдельной вещью.
  late final TabsPeek _peek = TabsPeek();

  /// Сколько уже протянули вниз по самому бару; порог — [TabsPeek.pull], там
  /// же и о том, почему считается расстояние, а не скорость на отпускании.
  double _pushed = 0;

  /// Связь между вкладкой и приглашением «Вся Alma». Что она решает и почему
  /// это отдельная вещь — в [PillDirector]; здесь только её кормят.
  final PillDirector _pill = PillDirector();

  @override
  void initState() {
    super.initState();
    // Кто-то ушёл в Alma с готовым вопросом — из читалки гороскопа (`R2`).
    // Оболочка отвечает за одно: довезти до вкладки. Текст в поле подставит
    // сам экран Alma, он же и погасит признак — см. [almaDraft] о порядке.
    almaDraft.addListener(_askedAlma);
  }

  void _askedAlma() {
    if (almaDraft.value != null) _goTo(CabinetTab.alma);
  }

  @override
  void dispose() {
    almaDraft.removeListener(_askedAlma);
    _pill.dispose();
    _peek.dispose();
    _pages.dispose();
    super.dispose();
  }

  /// Где мы сейчас с точки зрения приглашения.
  ///
  /// **Список мест, где звать можно, короче списка вкладок, и это решение.**
  /// Заплатившему — никогда: звать подписчика купить подписку значит показать,
  /// что мы не знаем, кто перед нами. Над пергаментом главы — никогда: вкладка
  /// всё ещё «Мои системы», а экран уже документ, и продавать поверх того, за
  /// что человек только что заплатил вниманием, — худший момент из возможных.
  /// Поверх шита, витрины или диалога — никогда: наверху чужой маршрут, и
  /// пилюля оказалась бы под ним или, хуже, над ним.
  PillSurface? _pillSurface(AlmaSession session, bool reading) {
    if (session.isSubscriber || !session.hasBirthData) return null;
    if (!(ModalRoute.of(context)?.isCurrent ?? true)) return null;
    return switch (_tab) {
      CabinetTab.today => PillSurface.today,
      CabinetTab.systems => reading ? null : PillSurface.systems,
      CabinetTab.alma || CabinetTab.settings => null,
    };
  }

  /// Сказать пилюле, где мы, — **после кадра**, а не посреди него.
  ///
  /// Прямо из `build` это был бы `setState` у чужого состояния во время
  /// построения дерева, то есть падение в отладке на первой же смене вкладки.
  void _aimPill(AlmaSession session, bool reading) {
    final surface = _pillSurface(session, reading);
    final bought = session.entitlements.unlocked.isNotEmpty ||
        session.entitlements.hasPlan;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _pill
        ..bought = bought
        ..surface = surface;
    });
  }

  /// Едет ли список под пилюлей.
  ///
  /// Горизонтальные уведомления сюда приходят от самого `PageView` — смах между
  /// вкладками это тоже прокрутка, — и считать их движением содержимого нельзя:
  /// иначе пилюля уезжала бы под бар на каждом переходе между вкладками.
  bool _watchScroll(ScrollNotification note) {
    if (note.metrics.axis != Axis.vertical) return false;
    if (note is ScrollStartNotification) {
      _pill.scrolling = true;
    } else if (note is ScrollEndNotification) {
      _pill.scrolling = false;
    }
    return false;
  }

  /// Нажатие на бар — то же движение, что смах: страница доезжает сама.
  void _goTo(CabinetTab tab) {
    if (tab == _tab) {
      // Тап по вкладке, на которой уже стоишь. Идти некуда — но на Alma это
      // единственный способ сказать бару «спасибо, показал»: он приходил
      // ответить на вопрос «куда я могу уйти», и ответ получен.
      _peek.hide();
      return;
    }
    // Уходящую вкладку бар не прогоняет: на трёх остальных он постоянный, и
    // нырок вниз с возвратом на месте назначения читался бы сбоем. Признак
    // гасится в `onPageChanged`, когда страница доехала.
    readingNow.value = false;
    _pages.animateToPage(tab.index,
        duration: const Duration(milliseconds: 320), curve: Curves.easeOutCubic);
  }

  void _openSystem(SystemSlug slug) {
    // Совместимость — единственная система, которой мало одного рождения, и
    // потому единственная, у которой вход не в систему, а в человека.
    if (slug == SystemSlug.compatibility) {
      _openPair();
      return;
    }
    _systemsNav.currentState?.push(CupertinoPageRoute(
      builder: (context) => SystemScreen(system: slug, onOpenChapter: _openChapter),
    ));
  }

  /// Вход в совместимость: сначала человек, потом небо на двоих.
  ///
  /// **Цен на этом пути нет ни одной** (`locked-chapter-spec.md` §1): расчёт
  /// бесплатен, платен только текст, и покупка стоит внутри главы — там, где
  /// уже написан абзац про эту пару. Экран, просящий деньги до того, как
  /// человек назвал, с кем сравнивать, продаёт кота в мешке.
  ///
  /// Развилка одна: пары ещё нет — просим человека и сразу ведём в главу I; пара
  /// есть — открываем систему, где нарисовано небо отношений и лежит оглавление.
  Future<void> _openPair() async {
    final navigator = _systemsNav.currentState;
    if (navigator == null) return;
    final session = SessionScope.of(context);
    if (session.people.isNotEmpty) {
      navigator.push(CupertinoPageRoute(
        builder: (context) => SystemScreen(
          system: SystemSlug.compatibility,
          // Кого сравниваем — сказано вслух, а не угадано экраном. Сервер
          // подставляет второго сам только пока он ровно один; при двоих
          // отвечает 422 `partner_required`.
          partner: session.people.first,
          onOpenChapter: _openChapter,
        ),
      ));
      return;
    }
    final added = await navigator.push<Profile>(CupertinoPageRoute(
      builder: (context) => const PeopleScreen(picking: true),
    ));
    // Ушли, не сохранив, — и это нормальный исход: возвращаемся в колоду, а не
    // тащим человека в главу про пару, которой он не завёл.
    if (added == null) return;
    await _openPairChapter(added);
  }

  /// Первая глава пары — про того, кого только что назвали.
  ///
  /// **Оглавление спрашивается до перехода, и это не лишний запрос.** Слаг
  /// первой главы знает сервер (`chapters.py`), и вписать сюда «attraction»
  /// значило бы завести вторую копию этого знания, которая молча разойдётся с
  /// первой при переименовании. Заодно ответ ложится в память клиента, и экран
  /// главы решает «открыта ли она» синхронно, на первом кадре: иначе паттерн
  /// залоченной главы появляется после ответа сервера, а не сразу.
  ///
  /// Оглавление не доехало — ведём на экран системы: там та же дорога к главам
  /// и объяснение, если что-то не так. Тупика не остаётся ни на одной ветке.
  Future<void> _openPairChapter(Profile partner) async {
    final navigator = _systemsNav.currentState;
    if (navigator == null || !mounted) return;
    final session = SessionScope.of(context);
    String? asked;
    try {
      final list = await session.client
          .chapters(SystemSlug.compatibility, locale: session.locale);
      asked = list.chapters.firstOrNull?.slug;
    } on AlmaError {
      asked = null;
    }
    if (!mounted) return;
    // Копия ради замыкания: `final` даёт продвижение типа внутри строителя,
    // который выполнится когда угодно позже.
    final first = asked;
    navigator.push(CupertinoPageRoute(
      builder: (context) => first == null
          ? SystemScreen(
              system: SystemSlug.compatibility,
              partner: partner,
              onOpenChapter: _openChapter,
            )
          : ChapterScreen(
              system: SystemSlug.compatibility,
              chapter: first,
              partner: partner,
            ),
    ));
  }

  /// [partner] — про кого глава, когда она про пару. Дальше него это знание не
  /// идёт: у остальных систем второго человека нет вовсе.
  void _openChapter(SystemSlug system, String chapter, {Profile? partner}) {
    _systemsNav.currentState?.push(CupertinoPageRoute(
      builder: (context) =>
          ChapterScreen(system: system, chapter: chapter, partner: partner),
    ));
  }

  /// Заставка отыграла и сессия ответила. Живёт в оболочке, а не внутри
  /// заставки: кабинет не должен строиться за ней — иначе откроется
  /// недорисованным, — а анкета не должна показываться поверх экрана, которого
  /// человек ещё не видел.
  bool _launched = false;

  /// Путешествие началось и ещё не отпустило.
  ///
  /// Анкета живёт дольше своего повода: рождение появляется в середине
  /// церемонии, а за церемонией идёт хвост из трёх экранов. Кто уходит — решает
  /// она сама; см. соображение у ветки, которая её показывает.
  bool _journeyRunning = false;

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    // **Отказ сети не ждёт церемонии.** Человеку с мёртвой сетью не к чему
    // приходить: 3,4 секунды красивого неба перед экраном ошибки — это
    // издевательство, а не приход.
    if (!_launched && !(session.ready && session.failure != null)) {
      return LaunchScreen(
        ready: session.ready,
        onDone: () => setState(() => _launched = true),
      );
    }
    // **Отказ сети — это не «рождения нет».**
    //
    // `start()` ловит AlmaError, ставит ready и оставляет профиль пустым, а
    // проверка ниже читает пустой профиль как нового человека. Значит в метро
    // или в самолёте тот, у кого карта давно построена, встречал анкету с
    // первым вопросом — приложение выглядело так, будто стёрло его вместе с
    // покупками. Натив на этом месте показывает `AlmaFailure` с повтором
    // (`RootView.swift`, ветка `.failed`), и по той же причине: пока неизвестно,
    // есть ли карта, предлагать завести новую — врать.
    if (session.ready && session.failure != null && !session.hasBirthData) {
      return _StartFailed(onRetry: () async {
        await session.start(force: true);
        if (mounted) setState(() {});
      });
    }
    // **Вход для проверки.** Анкету видит только человек без рождения, а
    // значит один раз в жизни установки — и её экраны нечем снять рядом с
    // нативным кадром. На нативе для этого есть `-AlmaJourneyStep` в
    // `UserDefaults` (`JourneyModel.swift`), здесь — то же самое сборкой:
    // `--dart-define=ALMA_JOURNEY=1`. В обычной сборке константа пуста, и
    // ветка мертва.
    const forced = bool.fromEnvironment('ALMA_JOURNEY');
    // Без рождения кабинету нечего считать: новый человек попадает в
    // путешествие, как на iOS его встречает полноэкранная обложка. Пока
    // сессия не готова — ночь без всего, а не мигающий каркас.
    //
    // **Уводит отсюда само путешествие, а не появившееся рождение.**
    //
    // Условие читалось «нет рождения — анкета», и оно же выбрасывало анкету в
    // ту секунду, когда профиль сохранился: `session.start(force: true)`
    // будит эту сборку, `hasBirthData` становится истиной, и всё поддерево
    // подменяется кабинетом. То есть церемония обрывалась ровно у тех, у кого
    // сервер ответил быстрее девяти с половиной секунд, а хвост путешествия —
    // витрина, пре-аск, вход — не имел бы шанса открыться вовсе: его снесло бы
    // вместе с экраном, который его показывает. Признак ниже держит анкету на
    // экране до её собственного `onDone`; сказать «я закончила» вправе только
    // она.
    if (forced || _journeyRunning || (session.ready && !session.hasBirthData)) {
      _journeyRunning = true;
      return JourneyScreen(
        onDone: () => setState(() => _journeyRunning = false),
      );
    }
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      extendBody: true,
      // **Все четыре вкладки живут одновременно, как на iOS.**
      //
      // `switch` пересоздавал экран при каждом переключении, и беседа с Alma
      // стиралась: ушёл на «Мои системы», вернулся — лента пуста. Найдено на
      // симуляторе. На нативе все четыре стека живут всю жизнь приложения —
      // это записано там же, в комментарии к перезагрузке «Сегодня» по смене
      // профиля. IndexedStack держит их так же.
      // **Страница едет за пальцем.**
      //
      // Смах менял вкладку скачком, и это читалось как перелистывание кадра, а
      // не как движение. `PageView` ведёт страницу вместе с пальцем и сам
      // доводит её до края, когда его отпускают, — отсюда и плавность, и то,
      // что промахнуться мимо соседней вкладки нельзя.
      //
      // Каждая вкладка обёрнута в `_Alive`: `PageView` держит живыми только
      // соседние страницы, а здесь все четыре обязаны жить всю жизнь
      // приложения — иначе беседа стирается при уходе на «Сегодня».
      body: ValueListenableBuilder<bool>(
        valueListenable: readingNow,
        builder: (context, reading, tabs) {
          // Приглашение узнаёт о месте здесь, потому что здесь сходятся все
          // три вещи, которые его решают: вкладка, пергамент и сессия.
          _aimPill(session, reading);
          return Listener(
            // Палец на экране — экран ещё не «уселся»: шесть секунд тишины
            // начинаются заново. Слушателем, а не жестом: этот палец
            // принадлежит содержимому, и отнимать его нельзя.
            behavior: HitTestBehavior.deferToChild,
            onPointerDown: (_) => _pill.stirred(),
            child: NotificationListener<ScrollNotification>(
              onNotification: _watchScroll,
              child: Stack(
                children: [
                  tabs!,
                  // **Пилюля — запись `Overlay` поверх вкладки, а не строка в
                  // её списке.** Положенная в прокрутку, она уехала бы вместе с
                  // текстом; положенная сюда — стоит над содержимым и **под**
                  // баром вкладок, потому что `bottomNavigationBar` рисуется
                  // после тела. Бар всегда главнее приглашения.
                  Positioned.fill(
                    child: Overlay(
                      initialEntries: [
                        OverlayEntry(
                          builder: (context) => PillLayer(director: _pill),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
        child: PageView(
          controller: _pages,
          onPageChanged: (index) {
            readingNow.value = false;
            // Приход на любую вкладку гасит зов бара. На трёх вкладках это
            // ничего не меняет — он там стоит всегда; на Alma это и есть «бара
            // нет»: приехал он в прошлый визит или нет, встречает беседа с
            // композером.
            _peek.hide();
            setState(() => _tab = CabinetTab.values[index]);
          },
          children: [
            const _Alive(child: TodayScreen()),
            const _Alive(child: _SystemsTab()),
            _Alive(child: AlmaScreen(tabs: _peek)),
            const _Alive(child: SettingsScreen()),
          ],
        ),
      ),
      // **На вкладке Alma бар не стоит, а приезжает.**
      //
      // Решение владельца, а не упущение вёрстки: беседа — комната письма, и
      // внизу неё поле вопроса главнее переключения вкладок. Бар приходит по
      // граберу под композером и уходит сам.
      //
      // **Он уезжает вниз, а не снимается — и это не украшение.** Scaffold
      // кладёт высоту `bottomNavigationBar` в `MediaQuery` тела, а тело здесь
      // одно на все четыре страницы `PageView`. Сняв бар на Alma, мы поменяли
      // бы отступ снизу разом всем четырём, и три остальные вкладки дёргались
      // бы на 52 точки в такт чужому жесту. Место в разметке бар держит
      // всегда; меняется только то, где он нарисован.
      bottomNavigationBar: ValueListenableBuilder<bool>(
        valueListenable: _peek,
        builder: (context, peeking, _) {
          final away = _tab == CabinetTab.alma && !peeking;
          Widget bar = CabinetTabBar(
            current: _tab,
            // Нажатие идёт тем же путём, что смах: одно движение на оба способа.
            onSelect: _goTo,
          );
          if (_tab == CabinetTab.alma) {
            bar = Listener(
              // Палец на баре продлевает жизнь: три секунды считаются от
              // последнего касания, а не от приезда.
              onPointerDown: (_) => _peek.keepAwake(),
              child: GestureDetector(
                // Смах вниз — «спасибо, не надо». Тапу по вкладке он не мешает:
                // пока палец стоит на месте, арену выигрывает нажатие.
                onVerticalDragStart: (_) => _pushed = 0,
                onVerticalDragUpdate: (details) {
                  _pushed += details.primaryDelta ?? 0;
                  if (_pushed >= TabsPeek.pull) _peek.hide();
                },
                child: bar,
              ),
            );
          }
          // Смещение долей собственной высоты: единица уводит бар ровно на
          // свой рост вместе с полосой домашнего индикатора, и за кромкой от
          // него не остаётся ни точки.
          return AnimatedSlide(
            offset: Offset(0, away ? 1 : 0),
            duration: AlmaMotion.sheet,
            curve: AlmaMotion.sheetCurve,
            child: bar,
          );
        },
      ),
    );
  }
}

/// Экран отказа на старте: сеть молчит, и мы не знаем, есть ли карта.
///
/// Порт `AlmaFailure` с натива, где у него та же роль и та же кнопка. Текст —
/// готовые `stateOffline` и `stateRetry` из каталога: строка про то, что здесь
/// ничего не выдумывают, пока Alma молчит, — ровно про этот случай.
class _StartFailed extends StatelessWidget {
  const _StartFailed({required this.onRetry});

  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  l.stateOffline,
                  textAlign: TextAlign.center,
                  style: AlmaType.body.copyWith(color: AlmaPalette.muted2),
                ),
                const SizedBox(height: 28),
                _RetryButton(label: l.stateRetry, onTap: onRetry),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RetryButton extends StatelessWidget {
  const _RetryButton({required this.label, required this.onTap});

  final String label;
  final Future<void> Function() onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(28),
      child: Container(
        height: 54,
        padding: const EdgeInsets.symmetric(horizontal: 34),
        decoration: BoxDecoration(
          border: Border.all(color: AlmaPalette.gold.withValues(alpha: 0.55)),
          borderRadius: BorderRadius.circular(28),
        ),
        child: Center(
          widthFactor: 1,
          child: Text(label,
              style: AlmaType.button.copyWith(color: AlmaPalette.goldBright)),
        ),
      ),
    );
  }
}


/// Вкладка «Мои системы» со своим стеком: бар остаётся на месте под открытыми
/// экранами, как на нативе.
class _SystemsTab extends StatelessWidget {
  const _SystemsTab();

  @override
  Widget build(BuildContext context) {
    final shell = context.findAncestorStateOfType<_CabinetShellState>()!;
    return Navigator(
      key: shell._systemsNav,
      // **Признак чтения гасит навигатор, а не пять условий в пяти файлах.**
      //
      // Пергаментным бар делает `readingNow`, и поднимает его страница главы.
      // Гасили его до сих пор в трёх разных местах — `dispose` главы,
      // перестройка каркаса, смена вкладки, — и всё равно оставался четвёртый
      // путь, на котором не гасил никто: прочесть написанную главу, вернуться
      // и открыть ночную. Список глав под снятой главой не перестраивается, и
      // светлый бар оставался поверх ночи. Владелец приносил этот баг четыре
      // раза в разных обличьях.
      //
      // Уход с главы — это всегда движение навигатора, и другого способа с неё
      // уйти нет. Поэтому наблюдатель гасит признак на любом переходе, а глава,
      // оставшаяся наверху с готовым текстом, поднимает его снова сама.
      observers: [_ChapterExit()],
      onGenerateRoute: (settings) => CupertinoPageRoute(
        builder: (context) => SystemsScreen(onOpenSystem: shell._openSystem),
      ),
    );
  }
}

/// Гасит признак чтения на любом движении навигатора вкладки «Мои системы».
///
/// Гасит, но не поднимает: поднять его вправе только страница главы, которая
/// знает, дочитан ли её текст. Наблюдатель отвечает ровно за одно — что при
/// уходе с главы бар перестаёт быть пергаментным, каким бы путём с неё ни
/// ушли.
class _ChapterExit extends NavigatorObserver {
  void _dim() => readingNow.value = false;

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previous) => _dim();

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previous) => _dim();

  @override
  void didRemove(Route<dynamic> route, Route<dynamic>? previous) => _dim();

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) => _dim();
}

/// Страница, которую `PageView` не выбрасывает, уехав от неё.
class _Alive extends StatefulWidget {
  const _Alive({required this.child});

  final Widget child;

  @override
  State<_Alive> createState() => _AliveState();
}

class _AliveState extends State<_Alive> with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return widget.child;
  }
}
