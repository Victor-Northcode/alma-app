import 'package:flutter/material.dart';

import 'design/metrics.dart';
import 'design/palette.dart';
import 'design/sky/night_sky.dart';
import 'design/tab_bar.dart';
import 'design/typography.dart';
import 'l10n/alma_l10n.dart';
import 'net/alma_client.dart';
import 'net/models.dart';
import 'screens/alma/alma_screen.dart';
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
    return Scaffold(
      backgroundColor: AlmaPalette.night,
      extendBody: true,
      body: switch (_tab) {
        CabinetTab.today => const TodayScreen(),
        // Свой навигатор у вкладки, чтобы бар оставался на месте под
        // открытыми экранами — как на iOS, где стек живёт внутри вкладки.
        CabinetTab.systems => Navigator(
            key: _systemsNav,
            onGenerateRoute: (settings) => MaterialPageRoute(
              builder: (context) => SystemsScreen(onOpenSystem: _openSystem),
            ),
          ),
        CabinetTab.alma => const AlmaScreen(),
        _ => _Placeholder(tab: _tab),
      },
      bottomNavigationBar: CabinetTabBar(
        current: _tab,
        onSelect: (tab) => setState(() => _tab = tab),
      ),
    );
  }
}

/// Временное место экрана. Живёт ровно до коммита, в котором приезжает
/// настоящий экран, и не разрастается.
class _Placeholder extends StatelessWidget {
  const _Placeholder({required this.tab});

  final CabinetTab tab;

  @override
  Widget build(BuildContext context) {
    final l = L.of(context);
    return NightSky(
      mood: SkyMood.cabinet,
      seed: 0x414C4D41 + tab.index * 7919,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AlmaMetrics.pad),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: AlmaMetrics.gapLarge),
              Text(tab.title(l), style: AlmaType.displayXl),
            ],
          ),
        ),
      ),
    );
  }
}
