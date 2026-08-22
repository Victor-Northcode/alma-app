import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show HapticFeedback;

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
import 'screens/journey/push_ask_screen.dart';
import 'screens/launch_screen.dart';
import 'screens/onboarding/coach_marks.dart';
import 'screens/settings/settings_screen.dart';
import 'screens/systems/chapter_screen.dart';
import 'screens/paywall/pair_bind_screen.dart';
import 'screens/systems/pair_add_screen.dart';
import 'screens/systems/system_screen.dart';
import 'screens/systems/systems_screen.dart';
import 'screens/today/today_screen.dart' show TodayScreen, noteLaunch;
import 'state/ask_alma.dart';
import 'state/locale_override.dart';
import 'state/onboarding_memory.dart';
import 'state/paywall_guard.dart';
import 'state/session.dart';

void main() {
  // Память сторожа §5 (отклонённые проактивные товары, 48 часов) живёт на
  // диске и поднимается до первого кадра: решение «показывать ли» синхронно,
  // и сторож, спрошенный раньше диска, разрешил бы то, что вчера отклонили.
  WidgetsFlutterBinding.ensureInitialized();
  PaywallGuard.restore();
  // Выбранный человеком язык — тем же приёмом, что память сторожа: старт не
  // ждёт диска, первый кадр может мигнуть языком телефона и перестроиться.
  LocaleOverride.restore();
  runApp(AlmaApp(
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
}

/// Открыт ли отладочный вход, объявленный сборкой.
///
/// **`bool.fromEnvironment` понимает только слово `true`.** Оба комментария в
/// этом файле обещают `--dart-define=ALMA_JOURNEY=1`, и ровно эта команда
/// молчала: `bool.fromEnvironment('ALMA_JOURNEY')` на значении `1` читает
/// «ничего не сказано» и возвращает умолчание, то есть `false`. Дверь для
/// проверки была нарисована на стене — найдено на симуляторе, когда тем же
/// способом не открылась обучалка.
///
/// Теперь дверь открывает любое значение, кроме тех, которыми её закрывают
/// вслух. Сборке, где ключ не назван, значение приходит пустым, и обе ветки
/// по-прежнему мертвы.
bool buildDoorOpen(String value) =>
    value.isNotEmpty && value != 'false' && value != '0';

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
    // Тап по пушу — последнее из четырёх событий §7. Ставится в корне: здесь
    // есть сессия, а разбор «живой тап или тап, открывший мёртвый процесс»
    // уже сделан в AlmaPush.listen. Тип пуша едет полем — по нему лестница
    // отвечает «с какого пуша пришли», не смешиваясь с daily_opened.
    AlmaPush.instance.onOpened = (payload) {
      _session.client.track(FunnelStage.pushOpened, meta: {
        'type': ?payload['type'],
      });
      // **И тап открывает то, на что указывает.** Раньше здесь всё и
      // кончалось: событие воронки записано, человек стоит там, где стоял, —
      // то есть уведомление, обещавшее показать сегодняшнюю заметку или
      // готовый отчёт пары, приводило на произвольную вкладку, а чаще на ту,
      // с которой ушли неделю назад. Открывает не корень, а оболочка: вкладки
      // и стек «Моих систем» знает она — см. [pushedOpen] о том, почему это
      // признак, а не вызов.
      pushedOpen.value = payload;
    };
    AlmaPush.instance.listen();
    // Счёт запусков для карточки «сохрани карту»: считается здесь, потому что
    // здесь и есть запуск. Внутри карточки это был бы счёт визитов на экран.
    noteLaunch();
  }

  @override
  Widget build(BuildContext context) {
    return SessionScope(
      session: _session,
      // Язык, выбранный в настройках, перестраивает приложение на месте:
      // `locale: null` — прежнее поведение, интерфейс следует за телефоном.
      child: ValueListenableBuilder<Locale?>(
        valueListenable: LocaleOverride.value,
        builder: (context, chosen, _) => MaterialApp(
        title: 'Alma',
        debugShowCheckedModeBanner: false,
        locale: chosen,
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

  /// Читалась ли глава на вкладке «Мои системы», когда с неё ушли.
  ///
  /// **Признак чтения принадлежит странице, а не приходу на вкладку.** Приход
  /// гасил его безусловно — включая возврат туда, где глава осталась открытой.
  /// Поднимает его сама глава, и только при перестройке; при возврате смахом
  /// `PageView` её не перестраивает, и она молчала. Владелец увидел следствие:
  /// «смахиваю на альму, возвращаюсь на главу — страница белая, а бар снизу
  /// синий».
  ///
  /// Поэтому уход с «Моих систем» состояние **запоминает**, а возврат его
  /// возвращает. Спрашивать саму главу отсюда нельзя: оболочка о её
  /// существовании не знает и знать не должна.
  bool _systemsWasReading = false;

  /// Какая страница была последней — чтобы уход было от чего отсчитать. Смах
  /// мимо `_goTo` не проходит, и только здесь видно, откуда ушли.
  late int _lastPage = _tab.index;

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
    // Пока мы на «Моих системах», запомненное состояние обязано быть зеркалом
    // настоящего: иначе закрытая глава оставит `true`, и возврат на вкладку
    // зажжёт пергаментную полосу над списком систем.
    readingNow.addListener(_mirrorReading);
    // Оплаченная и не привязанная проверка пары доезжает в любой момент —
    // чаще всего при запуске, когда магазин передоставляет незавершённую
    // транзакцию с прошлого раза. Долг гасится выбором человека, и продукт
    // обязан привести к нему сам: деньги уже взяты.
    AlmaStore.shared.addListener(_pairDebt);
    // Тап по уведомлению живого приложения — сразу; тап, открывший мёртвое,
    // подождёт кабинета (см. [_maybeOpenPushed] и [pushedOpen]).
    pushedOpen.addListener(_maybeOpenPushed);
  }

  /// Экран привязки уже стоит — второго не открывать: доставка покупки
  /// повторяется, а два одинаковых вопроса подряд читаются сбоем.
  bool _askingPairDebt = false;

  Future<void> _pairDebt() async {
    if (_askingPairDebt || AlmaStore.shared.unbound == null || !mounted) {
      return;
    }
    _askingPairDebt = true;
    await Navigator.of(context, rootNavigator: true).push(
      CupertinoPageRoute<void>(
          builder: (context) => const PairBindScreen()),
    );
    _askingPairDebt = false;
  }

  /// Открыт ли кабинет прямо сейчас. Пока нет — тапу некуда вести.
  ///
  /// Заставка, экран отказа сети и анкета возвращаются из [build] раньше
  /// вкладок: `PageView` не построен, `_pages` не привязан к нему, стек «Моих
  /// систем» не существует. Признак поднимает сам [build] в той единственной
  /// точке, за которой кабинет уже возвращается.
  bool _cabinetOpen = false;

  /// Тап по уведомлению — открыть то, на что он указывает.
  ///
  /// Зовут отсюда двое: слушатель [pushedOpen] (живой тап по открытому
  /// приложению) и [build] кабинета (тап, разбудивший процесс, — он приехал
  /// раньше, чем стало куда вести). Признак гасится **до** навигации: `build`
  /// зовётся на каждый кадр, и один тап обязан открыть одно место один раз.
  ///
  /// Кадром позже, а не сейчас: половина вызовов приходит из `build`, а
  /// навигация посреди построения дерева — это построение дерева во время
  /// построения дерева.
  void _maybeOpenPushed() {
    final payload = pushedOpen.value;
    if (payload == null || !_cabinetOpen) return;
    pushedOpen.value = null;
    WidgetsBinding.instance.addPostFrameCallback((_) => _openPushed(payload));
  }

  /// Куда ведёт какой пуш — закрытый список `docs/PUSH.md §2.3`.
  ///
  /// Список закрыт намеренно, и незнакомый тип **никуда не ведёт**: сборка
  /// старше сервера — обычное дело, а угаданное «наверное, это про день»
  /// увело бы человека не туда, чем ничего не сделать хуже.
  Future<void> _openPushed(Map<String, String> payload) async {
    if (!mounted) return;
    switch (payload['type']) {
      case 'daily':
        // Дневная заметка живёт на «Сегодня». `date` из пейлоада сюда не идёт:
        // экран показывает **сегодня** и другой даты не знает вовсе, а пуш
        // приходит в то самое утро. Выдумывать ему архив по одному полю пуша
        // значит обещать экран, которого нет.
        await _goTo(CabinetTab.today);
      case 'pair_ready':
        final partner = _pushPartner(payload['profile_id']);
        // Человека не нашли — стоим на месте. Совместимость «с кем-нибудь»
        // открыла бы отчёт про **другого**, а это хуже, чем не двинуться:
        // отчёт пары называет двоих поимённо. Осиротевший грант (профиль
        // удалён, отчёт оплачен) — известная дыра, у неё и на «Моих парах»
        // дороги нет; см. TODO(owner) там же.
        if (partner == null) return;
        // Перелёт дожидается конца, а не отдаётся и забывается: глава ляжет в
        // навигатор «Моих систем», а он рождается вместе со своей страницей —
        // см. [_goTo] и [_openPairChapter].
        await _goTo(CabinetTab.systems);
        if (!mounted) return;
        await _openPairChapter(partner);
      // Ни `default`, ни `_`: закрытый список — на то и закрытый.
    }
  }

  /// Партнёр пуша среди сохранённых людей — или `null`, если такого нет.
  Profile? _pushPartner(String? profileId) {
    if (profileId == null || profileId.isEmpty) return null;
    final people = SessionScope.of(context).people;
    return people.where((person) => person.id == profileId).firstOrNull;
  }

  /// Пока идёт смена вкладки, зеркало молчит.
  ///
  /// **Без этого починка ломала сама себя.** Уход с «Моих систем» сохраняет
  /// состояние и тут же гасит признак; гашение будит зеркало, а `_tab` в эту
  /// секунду ещё указывает на «Мои системы» — и только что сохранённое `true`
  /// затиралось обратно в `false`. Проверено на симуляторе: полоса оставалась
  /// ночной ровно так же, как до починки.
  bool _switching = false;

  void _mirrorReading() {
    if (_switching) return;
    if (_tab == CabinetTab.systems) _systemsWasReading = readingNow.value;
  }

  void _askedAlma() {
    if (almaDraft.value != null) _goTo(CabinetTab.alma);
  }

  @override
  void dispose() {
    almaDraft.removeListener(_askedAlma);
    readingNow.removeListener(_mirrorReading);
    AlmaStore.shared.removeListener(_pairDebt);
    pushedOpen.removeListener(_maybeOpenPushed);
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
  ///
  /// **Возвращает то, чем перелёт кончается**, и это не украшение подписи.
  ///
  /// Открывающему место по тапу с уведомления нужна не «команда отдана», а
  /// «страница есть»: `PageView` строит соседнюю по мере приближения, и её
  /// навигатора в секунду вызова ещё нет. Тем, кто просто переключает вкладку,
  /// ждать нечего, и `void` в их вызовах ничего не меняет.
  Future<void> _goTo(CabinetTab tab) async {
    if (tab == _tab) {
      // Тап по вкладке, на которой уже стоишь. Идти некуда — но на Alma это
      // единственный способ сказать бару «спасибо, показал»: он приходил
      // ответить на вопрос «куда я могу уйти», и ответ получен.
      _peek.hide();
      return;
    }
    // Уходящую вкладку бар не прогоняет: на трёх остальных он постоянный, и
    // нырок вниз с возвратом на месте назначения читался бы сбоем.
    //
    // Состояние запоминается **до** гашения: полосу на время перелёта надо
    // увести в ночь, а вернувшись на «Мои системы» — вернуть, если там открыта
    // глава. См. [_systemsWasReading].
    _switching = true;
    if (_tab == CabinetTab.systems) _systemsWasReading = readingNow.value;
    readingNow.value = false;
    _switching = false;
    await _pages.animateToPage(tab.index,
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
    // Людей ещё нет — кадр W2: ввод человека прямо в совместимости, без
    // списка. Список с выбором и удалением остаётся на экране людей; сюда
    // человек приходит завести первого, и форма — единственное, что ему нужно.
    final added = await navigator.push<Profile>(CupertinoPageRoute(
      builder: (context) => const PairAddScreen(),
    ));
    // Ушли, не сохранив, — и это нормальный исход: возвращаемся в колоду, а не
    // тащим человека в главу про пару, которой он не завёл.
    if (added == null) return;
    // **Завёл человека — остаёшься на деке, а не проваливаешься в первую главу.**
    // Раньше здесь был `_openPairChapter(added)`, и сразу после ввода человека
    // открывалась первая карта «открыть». Владелец: должно остаться на экране, где
    // выбираешь главу сам (22 авг). Открываем ту же систему, что и ветка с уже
    // заведёнными людьми, — небо на двоих и оглавление.
    navigator.push(CupertinoPageRoute(
      builder: (context) => SystemScreen(
        system: SystemSlug.compatibility,
        partner: added,
        onOpenChapter: _openChapter,
      ),
    ));
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
    if (!mounted) return;
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
    // **Навигатор спрашивается после запроса, а не до.** Спрошенный первой
    // строкой, он отвечал `null` всякому, кто пришёл сюда не с «Моих систем»:
    // `PageView` строит страницу по мере приближения, и в секунду вызова её
    // ещё нет. Пока звали только изнутри вкладки, это не было видно; тап по
    // уведомлению о готовом отчёте приходит откуда угодно, и там путь тихо
    // обрывался ничем.
    final navigator = _systemsNav.currentState;
    if (navigator == null) return;
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
    _systemsNav.currentState
        ?.push(CupertinoPageRoute(
          builder: (context) =>
              ChapterScreen(system: system, chapter: chapter, partner: partner),
        ))
        // **Пред-вопрос про уведомления — после первой закрытой главы.** Хвост
        // онбординга больше не спрашивает (владелец убрал его: «так неудобно
        // максимально»), а спросить когда-то надо — иначе системное окно не
        // покажется никогда. Момент выбран по его же словам: «потом чуть-чуть
        // подвигались, куда-то зашли — и предложили включить уведомления».
        // Закрытая глава — человек уже читал и вернулся, самое время.
        .then((_) => _maybePreAskPush());
  }

  /// Показать пред-вопрос уведомлений, если пора: один раз за жизнь установки
  /// и только когда разрешения ещё нет. Правила — в [AlmaPush.preAskDue].
  Future<void> _maybePreAskPush() async {
    if (!mounted || !_cabinetOpen) return;
    if (!await AlmaPush.instance.preAskDue()) return;
    // Пишется до показа, как OnboardingMemory: убитое на экране приложение не
    // должно спрашивать второй раз.
    await AlmaPush.instance.markPreAsked();
    if (!mounted) return;
    await Navigator.of(context, rootNavigator: true).push(
      CupertinoPageRoute<void>(builder: (context) => const PushAskScreen()),
    );
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

  /// Про обучалку уже спрашивали в этом запуске. Спрашивает `build`, а он
  /// зовётся на каждую смену вкладки, — без признака вопрос ушёл бы на диск
  /// десятки раз за минуту.
  bool _coachAsked = false;

  /// Дать кабинету осесть перед проводкой.
  ///
  /// Каскад прихода вкладки — 550 мс с лесенкой (`AlmaArrive`), и накладка,
  /// легшая поверх ещё летящих блоков, показала бы человеку затемнение раньше,
  /// чем сам продукт. Пауза — про то, что первый кадр кабинета принадлежит
  /// кабинету.
  static const _coachBreath = Duration(milliseconds: 900);

  /// Показать маленькую проводку — один раз в жизни установки.
  ///
  /// **Вход для проверки.** Обучалку видит только тот, кто только что прошёл
  /// анкету, — то есть один раз, и снять её рядом с макетом нечем.
  /// `--dart-define=ALMA_ONBOARDING=1` показывает её на каждом запуске, ровно
  /// как `ALMA_JOURNEY=1` показывает анкету; в обычной сборке константа пуста, и
  /// ветка мертва.
  void _maybeCoach() {
    if (_coachAsked) return;
    _coachAsked = true;
    final forced =
        buildDoorOpen(const String.fromEnvironment('ALMA_ONBOARDING'));
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      if (!forced && !await OnboardingMemory.due()) return;
      await Future<void>.delayed(_coachBreath);
      if (!mounted) return;
      // Отметка **до** показа: «один раз в жизни установки» обязано выполняться
      // и для того, кто закрыл проводку убийством приложения. Принудительный
      // показ отметку тоже ставит — и тоже её игнорирует.
      await OnboardingMemory.markSeen();
      if (!mounted) return;
      await showCoachMarks(
        context,
        goTo: (stop) => _goTo(switch (stop) {
          CoachStop.systems || CoachStop.firstChapter => CabinetTab.systems,
          CoachStop.today => CabinetTab.today,
          CoachStop.alma => CabinetTab.alma,
          CoachStop.morning => CabinetTab.settings,
        }),
      );
    });
  }

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
    final forced = buildDoorOpen(const String.fromEnvironment('ALMA_JOURNEY'));
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
        onDone: () {
          // **Обучалка взводится здесь и больше нигде.** Это единственная точка
          // в приложении, где известно, что человек только что прошёл анкету, —
          // а «маленькая проводка для нового» адресована ровно ему. Тому, кто
          // обновил приложение с уже построенной картой, кабинет знаком, и
          // накладка поверх знакомого экрана читалась бы поломкой.
          OnboardingMemory.arm();
          // **После анкеты человек попадает на «Мои системы», а не в главу.**
          // Раньше `_leave` вёл прямо в бесплатную главу натала; владелец назвал
          // это «максимально неудобно» (22 авг) — хочу на восемь карт, где первая
          // глава уже открыта, и оттуда сам. Кабинет строится этим же setState;
          // прыгаем на вкладку после кадра, когда у PageController есть клиент.
          _tab = CabinetTab.systems;
          setState(() => _journeyRunning = false);
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (_pages.hasClients) _pages.jumpToPage(CabinetTab.systems.index);
          });
        },
      );
    }
    // Кабинет действительно открывается — можно спрашивать про обучалку.
    // Строкой ниже всех `return` выше: ни поверх церемонии, ни поверх заставки,
    // ни поверх экрана отказа сети её быть не должно.
    _maybeCoach();
    // И по той же причине — ровно здесь — забирается тап по уведомлению,
    // разбудивший процесс: до этой строки вкладок нет, и вести ему некуда.
    _cabinetOpen = true;
    _maybeOpenPushed();
    // Клавиатура — здесь, выше Scaffold: он обнуляет `viewInsets` в теле, а этот
    // контекст видит её настоящую высоту и перестраивается, когда она открывается
    // и закрывается. По ней бар на вкладке Alma уходит вниз только на время письма.
    final keyboardUp = MediaQuery.viewInsetsOf(context).bottom > 0;
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
            // Тактильный щелчок на смене вкладки — как на нативе просил владелец.
            HapticFeedback.selectionClick();
            // **Клавиатуру снимаем при каждом переходе.** Alma держит фокус живым
            // (вкладка не размонтируется), и клавиатура уезжала с ней на «Сегодня»
            // и «Настройки» — там её было не закрыть. Снятие фокуса на переходе
            // закрывает её и не даёт таскаться за пальцем (найдено на устройстве).
            FocusManager.instance.primaryFocus?.unfocus();
            final systems = CabinetTab.systems.index;
            _switching = true;
            if (_lastPage == systems) {
              _systemsWasReading = readingNow.value || _systemsWasReading;
            }
            // Возврат на «Мои системы» возвращает то, что там было; приход на
            // любую другую вкладку гасит. Безусловное гашение оставляло белую
            // страницу главы под ночной полосой.
            readingNow.value = index == systems && _systemsWasReading;
            _lastPage = index;
            _switching = false;
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
      // **Бар стоит на всех четырёх вкладках, включая Alma, и прячется только
      // пока пишут.**
      //
      // Раньше на Alma бара не было вовсе: он уезжал вниз и вызывался грабером под
      // композером. Владелец сказал, что это читается как «меню пропало» — снято
      // на устройстве 22 авг. Теперь он ведёт себя как на остальных вкладках, а
      // уходит вниз только на время открытой клавиатуры, чтобы не встать между
      // ней и полем вопроса.
      //
      // **Он уезжает вниз, а не снимается — и это не украшение.** Scaffold кладёт
      // высоту `bottomNavigationBar` в `MediaQuery` тела, а тело здесь одно на все
      // четыре страницы `PageView`. Сняв бар, мы поменяли бы отступ снизу разом
      // всем четырём. Место в разметке бар держит всегда; меняется только то, где
      // он нарисован.
      bottomNavigationBar: AnimatedSlide(
        offset: Offset(0, _tab == CabinetTab.alma && keyboardUp ? 1 : 0),
        duration: AlmaMotion.sheet,
        curve: AlmaMotion.sheetCurve,
        child: CabinetTabBar(current: _tab, onSelect: _goTo),
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
