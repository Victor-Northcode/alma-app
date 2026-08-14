import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'billing/alma_store.dart';
import 'design/metrics.dart';
import 'design/palette.dart';
import 'design/tab_bar.dart';
import 'design/typography.dart';
import 'l10n/alma_l10n.dart';
import 'net/alma_client.dart';
import 'net/models.dart';
import 'screens/alma/alma_screen.dart';
import 'screens/journey/journey_screen.dart';
import 'screens/launch_screen.dart';
import 'screens/offer_screen.dart';
import 'screens/settings/settings_screen.dart';
import 'screens/systems/chapter_screen.dart';
import 'screens/systems/system_screen.dart';
import 'screens/systems/systems_screen.dart';
import 'screens/today/today_screen.dart' show TodayScreen, noteLaunch;
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

  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  /// Нажатие на бар — то же движение, что смах: страница доезжает сама.
  void _goTo(CabinetTab tab) {
    if (tab == _tab) return;
    readingNow.value = false;
    _pages.animateToPage(tab.index,
        duration: const Duration(milliseconds: 320), curve: Curves.easeOutCubic);
  }

  void _openSystem(SystemSlug slug) {
    _systemsNav.currentState?.push(CupertinoPageRoute(
      builder: (context) => SystemScreen(system: slug, onOpenChapter: _openChapter),
    ));
  }

  void _openChapter(SystemSlug system, String chapter) {
    _systemsNav.currentState?.push(CupertinoPageRoute(
      builder: (context) => ChapterScreen(system: system, chapter: chapter),
    ));
  }

  /// Заставка отыграла и сессия ответила. Живёт в оболочке, а не внутри
  /// заставки: кабинет не должен строиться за ней — иначе откроется
  /// недорисованным, — а анкета не должна показываться поверх экрана, которого
  /// человек ещё не видел.
  bool _launched = false;

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
    if (forced || (session.ready && !session.hasBirthData)) {
      return JourneyScreen(onDone: () => setState(() {}));
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
      body: PageView(
        controller: _pages,
        onPageChanged: (index) {
          readingNow.value = false;
          setState(() => _tab = CabinetTab.values[index]);
        },
        children: const [
          _Alive(child: TodayScreen()),
          _Alive(child: _SystemsTab()),
          _Alive(child: AlmaScreen()),
          _Alive(child: SettingsScreen()),
        ],
      ),
      // **Приглашение приходит и уходит, а не стоит.**
      //
      // На нативе это золотая пилюля в углу «Сегодня» и «Моих систем»: не
      // баннер и не всплывающее окно, а маленькая печать. Но печать, которая
      // на экране всегда, перестаёт быть событием на второй минуте — глаз
      // научается её не видеть, и она превращается в мебель, которая вдобавок
      // закрывает угол содержимого. Владелец сказал это прямо: пусть всплывает
      // в нужный момент, иногда напоминает о себе движением и испаряется.
      //
      // Что она делает — в [_InvitationPill]. Здесь решается только одно: **кому
      // и когда её вообще показывать**. Заплатившему — никогда: звать
      // подписчика купить подписку значит показать, что мы не знаем, кто перед
      // нами. Над пергаментом — никогда: вкладка всё ещё «Мои системы», а экран
      // уже документ, и продавать поверх того, за что человек только что
      // заплатил вниманием, — худший момент из возможных.
      floatingActionButton: ValueListenableBuilder<bool>(
        valueListenable: readingNow,
        builder: (context, reading, _) {
          final invited = !session.isSubscriber &&
              session.hasBirthData &&
              !reading &&
              (_tab == CabinetTab.today || _tab == CabinetTab.systems);
          return Padding(
            padding: EdgeInsets.only(bottom: AlmaMetrics.tabBarHeight - 8),
            child: _InvitationPill(
              // Смена вкладки — новый момент: отсчёт начинается заново, и
              // приглашение приходит после того, как экран прочитан, а не
              // вместе с ним.
              moment: _tab,
              allowed: invited,
              onTap: () {
                Navigator.of(context).push(CupertinoPageRoute(
                    builder: (context) => const OfferScreen()));
              },
            ),
          );
        },
      ),
      bottomNavigationBar: CabinetTabBar(
        current: _tab,
        // Нажатие идёт тем же путём, что смах: одно движение на оба способа.
        onSelect: _goTo,
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
      onGenerateRoute: (settings) => CupertinoPageRoute(
        builder: (context) => SystemsScreen(onOpenSystem: shell._openSystem),
      ),
    );
  }
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


/// Золотая пилюля «Вся Alma» — приглашение, которое приходит и уходит.
///
/// **Почему у неё есть жизнь, а не только вид.** Пилюля висела в углу
/// постоянно. Постоянное приглашение перестаёт быть приглашением: на второй
/// минуте глаз перестаёт его замечать, а угол экрана оно закрывать не
/// перестаёт. Владелец сформулировал задачу словами «всплывала в нужный
/// момент… иногда тряслась… и испарялась».
///
/// Отсюда три числа и один закон.
///
/// * **Шесть секунд молчания после прихода на экран.** Экран сначала читают.
///   Приглашение, появившееся вместе с содержимым, спорит с ним за первый
///   взгляд и проигрывает — а проиграв, воспринимается как помеха.
/// * **Одиннадцать секунд жизни.** Достаточно, чтобы заметить и дотянуться, и
///   мало, чтобы стать мебелью.
/// * **Полторы минуты тишины** между появлениями, и не больше трёх появлений
///   на один приход на вкладку. Четвёртое напоминание за две минуты — это уже
///   не напоминание.
///
/// Закон: **движение только на приходе**. Пилюля вздрагивает, когда появилась,
/// и ещё раз в середине жизни — так вздрагивает то, что хочет, чтобы его
/// заметили, а не то, что сломалось. Трясущийся элемент, который трясётся
/// всегда, читается как ошибка отрисовки.
///
/// Уходит она не исчезновением: гаснет, чуть уменьшается и поднимается — то
/// самое «испаряется». Появление зеркально.
class _InvitationPill extends StatefulWidget {
  const _InvitationPill({
    required this.moment,
    required this.allowed,
    required this.onTap,
  });

  /// Что считается «новым моментом». Меняется — цикл начинается заново.
  final Object moment;

  /// Можно ли звать вообще: подписчику и над пергаментом — нет.
  final bool allowed;

  final VoidCallback onTap;

  @override
  State<_InvitationPill> createState() => _InvitationPillState();
}

class _InvitationPillState extends State<_InvitationPill>
    with SingleTickerProviderStateMixin {
  static const _quiet = Duration(seconds: 6);
  static const _life = Duration(seconds: 11);
  static const _rest = Duration(seconds: 90);
  static const _times = 3;

  late final AnimationController _wobble = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 620),
  );

  bool _visible = false;
  int _shown = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _restart();
  }

  @override
  void didUpdateWidget(_InvitationPill old) {
    super.didUpdateWidget(old);
    if (old.moment != widget.moment) {
      _restart();
    } else if (old.allowed != widget.allowed && !widget.allowed) {
      _timer?.cancel();
      if (_visible) setState(() => _visible = false);
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _wobble.dispose();
    super.dispose();
  }

  void _restart() {
    _timer?.cancel();
    _shown = 0;
    if (_visible) _visible = false;
    _timer = Timer(_quiet, _appear);
  }

  void _appear() {
    if (!mounted || !widget.allowed || _shown >= _times) return;
    setState(() => _visible = true);
    _shown += 1;
    _wobble.forward(from: 0);
    // Второе вздрагивание в середине жизни: одно на приходе можно и
    // пропустить, глядя в другую часть экрана.
    _timer = Timer(_life ~/ 2, () {
      if (mounted && _visible) _wobble.forward(from: 0);
      _timer = Timer(_life ~/ 2, _vanish);
    });
  }

  void _vanish() {
    if (!mounted) return;
    setState(() => _visible = false);
    if (_shown >= _times) return;
    _timer = Timer(_rest, _appear);
  }

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return IgnorePointer(
      ignoring: !_visible || !widget.allowed,
      child: AnimatedOpacity(
        opacity: _visible && widget.allowed ? 1 : 0,
        duration: _visible ? AlmaMotion.ui : AlmaMotion.sheet,
        curve: AlmaMotion.uiCurve,
        child: AnimatedSlide(
          // Испарение — вверх и чуть меньше; приход — оттуда же обратно.
          offset: _visible ? Offset.zero : const Offset(0, -0.35),
          duration: _visible ? AlmaMotion.ui : AlmaMotion.sheet,
          curve: AlmaMotion.uiCurve,
          child: AnimatedScale(
            scale: _visible ? 1 : 0.92,
            duration: _visible ? AlmaMotion.ui : AlmaMotion.sheet,
            curve: AlmaMotion.uiCurve,
            child: AnimatedBuilder(
              animation: _wobble,
              builder: (context, child) {
                // Затухающее покачивание: две с половиной волны, амплитуда
                // тает к концу. Не тряска — кивок.
                final t = _wobble.value;
                final decay = (1 - t) * (1 - t);
                final angle = math.sin(t * math.pi * 5) * 0.055 * decay;
                return Transform.rotate(angle: angle, child: child);
              },
              child: Material(
                color: AlmaPalette.gold,
                borderRadius: BorderRadius.circular(999),
                elevation: 6,
                child: InkWell(
                  onTap: () {
                    HapticFeedback.selectionClick();
                    widget.onTap();
                  },
                  borderRadius: BorderRadius.circular(999),
                  child: Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    child: Text('✦ ${l.cabAllAlmaPill}',
                        style: AlmaType.meta
                            .copyWith(color: AlmaPalette.inkOnGold)),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
