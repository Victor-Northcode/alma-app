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

  void _openSystem(SystemSlug slug) {
    _systemsNav.currentState?.push(MaterialPageRoute(
      builder: (context) => SystemScreen(system: slug, onOpenChapter: _openChapter),
    ));
  }

  void _openChapter(SystemSlug system, String chapter) {
    _systemsNav.currentState?.push(MaterialPageRoute(
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
      body: IndexedStack(
        index: _tab.index,
        children: [
          const TodayScreen(),
          // Свой навигатор у вкладки, чтобы бар оставался на месте под
          // открытыми экранами — как на iOS, где стек живёт внутри вкладки.
          Navigator(
            key: _systemsNav,
            onGenerateRoute: (settings) => MaterialPageRoute(
              builder: (context) => SystemsScreen(onOpenSystem: _openSystem),
            ),
          ),
          const AlmaScreen(),
          const SettingsScreen(),
        ],
      ),
      bottomNavigationBar: CabinetTabBar(
        current: _tab,
        onSelect: (tab) => setState(() => _tab = tab),
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
