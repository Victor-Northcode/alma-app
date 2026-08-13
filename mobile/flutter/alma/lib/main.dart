import 'package:flutter/cupertino.dart' show CupertinoPageRoute;
import 'package:flutter/material.dart';

import 'design/palette.dart';
import 'design/tab_bar.dart';
import 'design/typography.dart';
import 'l10n/alma_l10n.dart';
import 'net/alma_client.dart';
import 'net/models.dart';
import 'screens/alma/alma_screen.dart';
import 'screens/journey/journey_screen.dart';
import 'screens/settings/settings_screen.dart';
import 'screens/systems/chapter_screen.dart';
import 'screens/systems/system_screen.dart';
import 'screens/systems/systems_screen.dart';
import 'screens/today/today_screen.dart';
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

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
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
    // Без рождения кабинету нечего считать: новый человек попадает в
    // путешествие, как на iOS его встречает полноэкранная обложка. Пока
    // сессия не готова — ночь без всего, а не мигающий каркас.
    if (session.ready && !session.hasBirthData) {
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
